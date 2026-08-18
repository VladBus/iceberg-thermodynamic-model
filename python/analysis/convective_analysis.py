"""Root-cause analysis of convective-adjustment guard cycling (Stage 4.3).

Reads
-----
- ``data/output/convective_guard_events.csv`` - per-column guard events logged
  by the Fortran model (``ca_log_guard_event`` in
  ``src/convective_adjustment.f90``; capped at ``ca_guard_evt_cap = 100``
  events/day). Columns: day,step,i,j,ki,iter_count,nmix,k_problem,resid_inv,
  tdz_before/after,dtdz,rel_t,sdz_before/after,dsdz,rel_s.
- ``data/output/daily_diagnostics.csv`` - per-day scalars from
  ``write_daily_diagnostics`` (euu, ro_max, t_min, wind_max, ca_guard_hits,
  ca_nmix, ca_affected_cols).
- Daily NetCDF snapshots ``data/output/results_day_XX.nc`` (T/S/RO profiles at
  guard columns).

Produces
--------
- ``convective_analysis.csv`` - one row per representative day with T/S/RO
  profile statistics at a typical and a guard-cycled column.
- ``convective_analysis.txt`` - human-readable report.

This script only AGGREGATES data already produced by the Fortran model; it
does not recompute EOS, mixing, or any physics (see promt.md / AGENTS.md).

Usage
-----
    python python/analysis/convective_analysis.py
"""

import argparse
import pathlib

import numpy as np
import pandas as pd
import xarray as xr

from units import temperature_k_to_c, density_anomaly_kgm3_to_gcm3

DEFAULT_EVENTS = "data/output/convective_guard_events.csv"
DEFAULT_DAILY = "data/output/daily_diagnostics.csv"
DEFAULT_PROF = "data/output/results_day_[0-9][0-9].nc"
DEFAULT_OUT_CSV = "data/output/convective_analysis.csv"
DEFAULT_OUT_TXT = "data/output/convective_analysis.txt"

REPR_DAYS = [1, 5, 10, 15, 20, 25, 30]


def load_column_profile(path, i, j):
    """Return T/S/RO/depth arrays for one column from a daily snapshot.

    NetCDF x/y are 0-based; the Fortran event log i/j are 1-based.
    """
    ds = xr.open_dataset(path)
    # NetCDF axis x <-> Fortran index i (size is1=133), y <-> index j (js1=105);
    # xarray exposes (depth, y, x), so j selects axis 1, i selects axis 2.
    ki = int(ds["water_column_levels"].values[j - 1, i - 1])
    # NetCDF canonical units: T in K, RO anomaly in kg m-3. Convert to degC and
    # g cm-3 so the 0.9e-7 threshold (model internal g/cm3) stays consistent.
    t = temperature_k_to_c(ds["temperature"].values[:ki, j - 1, i - 1])
    s = ds["salinity_mass_fraction"].values[:ki, j - 1, i - 1]
    ro = density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].values[:ki, j - 1, i - 1])
    depth = ds["depth"].values[:ki]
    ds.close()
    return depth, t, s, ro


def column_inv(ro):
    """Count inverted interfaces and max residual (1-based levels)."""
    n_inv = 0
    inv_max = 0.0
    k_max = 0
    for k in range(len(ro) - 1):
        a = ro[k] - ro[k + 1]
        if a > 0.9e-7:
            n_inv += 1
            if a > inv_max:
                inv_max = a
                k_max = k + 1
    return n_inv, inv_max, k_max


# pylint: disable=too-many-locals,too-many-statements
def representative_day_rows(day, events, prof_glob):
    """One CSV row per representative day with typical + guard-column profiles."""
    ev = events[events["day"] == day]
    n_guard = len(ev)
    file = pathlib.Path(prof_glob.replace("[0-9][0-9]", f"{day:02d}"))
    if not file.exists() or n_guard == 0:
        return None

    # Typical column: last event of the day (already sorted by insertion).
    i_t = ev["i"].iloc[-1]
    j_t = ev["j"].iloc[-1]
    _, t_t, s_t, ro_t = load_column_profile(file, i_t, j_t)
    n_inv_t, inv_max_t, k_max_t = column_inv(ro_t)

    # Max nmix column of the day.
    im = ev["nmix"].idxmax()
    i_m = ev["i"].loc[im]
    j_m = ev["j"].loc[im]
    _, t_m, s_m, ro_m = load_column_profile(file, i_m, j_m)
    n_inv_m, inv_max_m, k_max_m = column_inv(ro_m)

    row = {
        "day": day,
        "n_guard_events": n_guard,
        "typ_col_i": i_t,
        "typ_col_j": j_t,
        "typ_ki": len(ro_t),
        "typ_n_inv": n_inv_t,
        "typ_inv_max": inv_max_t,
        "typ_inv_k": k_max_t,
        "typ_t_min": float(t_t.min()),
        "typ_t_max": float(t_t.max()),
        "typ_t_range": float(t_t.max() - t_t.min()),
        "typ_s_min": float(s_t.min()),
        "typ_s_max": float(s_t.max()),
        "typ_ro_min": float(ro_t.min()),
        "typ_ro_max": float(ro_t.max()),
        "typ_ro_range": float(ro_t.max() - ro_t.min()),
        "mx_col_i": i_m,
        "mx_col_j": j_m,
        "mx_ki": len(ro_m),
        "mx_n_inv": n_inv_m,
        "mx_inv_max": inv_max_m,
        "mx_inv_k": k_max_m,
        "mx_t_range": float(t_m.max() - t_m.min()),
        "mx_s_range": float(s_m.max() - s_m.min()),
        "mx_ro_range": float(ro_m.max() - ro_m.min()),
    }
    return row


# pylint: disable=too-many-locals,too-many-statements
def main():
    """Build the Stage 4.3 convective-cycling report (CSV + text)."""
    parser = argparse.ArgumentParser(
        description="Stage 4.3 convective-adjustment guard cycling analysis."
    )
    parser.add_argument("--events", default=DEFAULT_EVENTS)
    parser.add_argument("--daily", default=DEFAULT_DAILY)
    parser.add_argument("--profiles", default=DEFAULT_PROF)
    parser.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-txt", default=DEFAULT_OUT_TXT)
    args = parser.parse_args()

    events = pd.read_csv(args.events)
    daily = pd.read_csv(args.daily)

    lines = []

    def p(s=""):
        lines.append(s)

    p("=" * 78)
    p("Stage 4.3 - Convective-adjustment guard cycling analysis")
    p("=" * 78)

    p()
    p("1. EVENT SAMPLE")
    p("-" * 40)
    p(f"  Guard events logged:      {len(events)} (capped {100}/day)")
    p(f"  Total guard hits:         {daily['ca_guard_hits'].sum():.0f}")
    p(f"  Unique columns affected:  {events[['i','j']].drop_duplicates().shape[0]}")
    p(f"  Days with events:         {events['day'].nunique()}")
    p(f"  ki of all events:         {events['ki'].unique()}")
    p(f"  iter_count of all:        {events['iter_count'].unique()} (guard)")
    p(
        f"  resid_inv values:         {[f'{v:.3e}' for v in sorted(events['resid_inv'].unique())]}"
    )
    ulp23 = 2**-23
    n_ulp1 = int((np.abs(events["resid_inv"] - ulp23) < 1e-12).sum())
    n_ulp2 = int((np.abs(events["resid_inv"] - 2 * ulp23) < 1e-12).sum())
    p(
        f"  resid_inv == 2^-23 (1 ulp):   {n_ulp1} / {len(events)} ({100.0*n_ulp1/len(events):.1f}%)"
    )
    p(
        f"  resid_inv == 2*2^-23 (2 ulp): {n_ulp2} / {len(events)} ({100.0*n_ulp2/len(events):.1f}%)"
    )
    p(f"  nmix / iteration:         mean {events['nmix'].mean()/1001:.3f}")
    p("  k_problem distribution (interface level):")
    for k, n in events["k_problem"].value_counts().sort_index().items():
        p(f"      k={k}: {n}")

    p()
    p("2. CONSERVATION (T*DZ1 / S*DZ1 across the guard)")
    p("-" * 40)
    p(
        f"  |rel_t|  max {events['rel_t'].abs().max():.3e}  mean {events['rel_t'].abs().mean():.3e}"
    )
    p(
        f"  |rel_s|  max {events['rel_s'].abs().max():.3e}  mean {events['rel_s'].abs().mean():.3e}"
    )
    p(f"  |dtdz|   max {events['dtdz'].abs().max():.3e}")
    p(f"  |dsdz|   max {events['dsdz'].abs().max():.3e}")

    p()
    p("3. TEMPORAL EVOLUTION (guard hits by day)")
    p("-" * 40)
    day_counts = events.groupby("day").size()
    for d in range(2, daily["day"].max() + 1):
        full = int(daily.loc[daily["day"] == d, "ca_guard_hits"].iloc[0])
        p(f"  day {d:2d}: full={full:4d}  logged={day_counts.get(d, 0):3d}")

    p()
    p("4. REPRESENTATIVE-DAY COLUMN PROFILES")
    p("-" * 40)
    rows = []
    for d in REPR_DAYS:
        r = representative_day_rows(d, events, args.profiles)
        if r is not None:
            rows.append(r)
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv(args.out_csv, index=False)
        p(f"  See {args.out_csv} ({len(df)} rows)")
        p()
        cols = [
            "day",
            "n_guard_events",
            "typ_ki",
            "typ_n_inv",
            "typ_inv_max",
            "typ_inv_k",
            "typ_ro_range",
            "mx_ki",
            "mx_n_inv",
            "mx_inv_max",
            "mx_ro_range",
        ]
        p(df[cols].to_string(index=False))
    else:
        p("  No representative columns available.")

    p()
    p("5. CORRELATIONS OF guard_hits WITH SCALARS (Pearson)")
    p("-" * 40)
    cols = [
        "euu",
        "ro_max",
        "ro_mean",
        "t_min",
        "t_max",
        "u_max",
        "v_max",
        "w_max",
        "wind_max",
        "ca_nmix",
        "ca_affected_cols",
    ]
    sub = daily[["ca_guard_hits"] + cols].dropna()
    for c in cols:
        r = np.corrcoef(sub["ca_guard_hits"], sub[c])[0, 1]
        p(f"  guard_hits ~ {c:<14s}: r = {r:+.3f}")
    p()
    p("  NOTE: correlation != causation; 30 points, no significance test.")

    with open(args.out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\nReport written to {args.out_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
