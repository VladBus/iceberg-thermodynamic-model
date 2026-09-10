"""Stage 10.8.2 — independent observational validation of the basal-melt closure.

Loads the curated observational dataset
(``data/validation/observations/iceberg_basal_melt_observations.csv``), runs the
production basal-melt closure from :mod:`basal_melt` against the
model-comparable observations, and reports:

  * point metrics on rows where the closure is fully specified and ``u_rel > 0``
    (4 rows: KW84 + Neshyba & Josberger 1980 x3);
  * the natural-convection gap test on the quiescent laboratory rows
    (production closure gives ~0 while observed melt is 0.04-1.6 m/day);
  * an inverse-U ("required U_rel") analysis for the remote-sensing rows that
    carry no ocean forcing;
  * regime classification (laminar/turbulent) and L_char / u_rel sensitivity.

This is **validation, not calibration**: the coefficients come from the
production formulation and are never adjusted here. Plotting is optional and
disabled when matplotlib is unavailable, so the checks run in a minimal
environment.

Run directly to print a summary (also exercises all analysis paths):

    python python/validation/observational_validation.py
"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from typing import Any

# Local import: reuse the already-validated independent closure (Stage 10.8.1).
import basal_melt as bm

DAY_S = 86400.0                     # seconds per day
FLOOR_M_PER_S = 1.0e-12             # production numerical-noise guard (m/s)
FLOOR_M_PER_DAY = FLOOR_M_PER_S * DAY_S   # ~8.64e-8 m/day (marker for plots)
RE_CRIT = bm.REYNOLDS_CRITICAL      # 5e5 laminar/turbulent transition

_REPO_ROOT = Path(__file__).resolve().parents[2]
OBS_CSV = (
    _REPO_ROOT
    / "data"
    / "validation"
    / "observations"
    / "iceberg_basal_melt_observations.csv"
)
DEFAULT_PLOT_DIR = (
    _REPO_ROOT / "data" / "output" / "diagnostics" / "stage10.8.2"
)

PLOT_NAMES = (
    "fig1_model_obs_loglog.png",
    "fig2_dT_sweep.png",
    "fig3_required_Urel.png",
    "fig4_regime_map.png",
    "fig5_observed_uncertainties.png",
    "fig6_log_ratio_bias.png",
)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------
def _num(value: str) -> float:
    """Convert a CSV cell to float; empty/'NaN'/invalid -> NaN."""
    s = value.strip()
    if not s or s.upper() in ("NAN", "NA", "NONE"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def load_observations(path: str | os.PathLike | None = None) -> list[dict]:
    """Parse the CSV into a list of dict rows with numeric conversion.

    Comment lines (starting with ``#``) and the header line are skipped.
    Numeric columns are converted to floats (NaN when missing); strings are
    stripped. ``include_in_metrics`` is converted to a Python bool.
    """
    src = Path(path) if path is not None else OBS_CSV
    if not src.is_file():
        raise FileNotFoundError(f"observations CSV not found: {src}")

    with src.open(newline="") as fh:
        raw = list(csv.reader(fh))

    header = next(r for r in raw if r and r[0].strip() == "record_id")
    header = [c.strip() for c in header]
    numeric_cols = {
        "T_degC", "S_psu", "u_rel_m_s", "L_char_m",
        "obs_m_per_s", "obs_m_per_day", "obs_unc_m_per_day",
    }

    rows = []
    for r in raw:
        if not r or not r[0].strip() or r[0].strip().startswith("#"):
            continue
        if r[0].strip() == "record_id":
            continue
        cells = [c.strip() for c in r]
        if len(cells) != len(header):
            raise ValueError(f"column mismatch in row {cells!r}")
        row: dict[str, Any] = {}
        for key, value in zip(header, cells):
            row[key] = _num(value) if key in numeric_cols else value
        row["include_in_metrics"] = (
            str(row.get("include_in_metrics", "False")).strip().lower() == "true"
        )
        rows.append(row)
    return rows


def closure_applicable(row: dict) -> bool:
    """True when the forced-convection closure is fully specified and u_rel > 0."""
    if row.get("include_in_metrics") is False:
        return False
    for key in ("T_degC", "S_psu", "u_rel_m_s", "L_char_m"):
        v = row.get(key, float("nan"))
        if isinstance(v, float) and math.isnan(v):
            return False
    return float(row["u_rel_m_s"]) > 0.0


# ---------------------------------------------------------------------------
# Production closure applied to observations
# ---------------------------------------------------------------------------
def model_melt_m_per_day(row: dict) -> float:
    """Production basal-melt rate [m/day] for an observation row.

    depth_m is taken equal to L_char_m (draft = characteristic length), the
    documented production choice. Returns 0.0 when any forcing field is
    missing / NaN or when u_rel <= 0 (closure returns the 0 guard), i.e. the
    natural-convection gap is exposed as a model value of 0.
    """
    t = row.get("T_degC", float("nan"))
    s = row.get("S_psu", float("nan"))
    u = row.get("u_rel_m_s", float("nan"))
    lc = row.get("L_char_m", float("nan"))
    if any(math.isnan(x) for x in (t, s, u, lc)) or u <= 0.0:
        return 0.0
    rate = bm.basal_melt_rate(
        ocean_temperature=float(t),
        salinity_psu=float(s),
        depth_m=float(lc),
        u_water=float(u),
        v_water=0.0,
        u_ice=0.0,
        v_ice=0.0,
        length_m=float(lc),
    )
    return rate * DAY_S


def compare_rows(rows: list[dict] | None = None) -> list[tuple]:
    """Return (row, obs_m_day, model_m_day, dT, Re) for closure-applicable rows."""
    rows = rows if rows is not None else load_observations()
    out = []
    for row in rows:
        if not closure_applicable(row):
            continue
        obs = float(row["obs_m_per_day"])
        model = model_melt_m_per_day(row)
        dT = row["T_degC"] - bm.ocean_freezing_point(row["S_psu"], row["L_char_m"])
        re = bm.reynolds_number(row["u_rel_m_s"], row["L_char_m"])
        out.append((row, obs, model, max(dT, 0.0), re))
    return out


# ---------------------------------------------------------------------------
# Metrics (on the closure-applicable set)
# ---------------------------------------------------------------------------
def compute_metrics(obs_mday, model_mday):
    """Standard point metrics; all arrays same length (model defined)."""
    n = len(obs_mday)
    e = [m - o for m, o in zip(model_mday, obs_mday)]
    e_rel = [m / o - 1.0 for m, o in zip(model_mday, obs_mday)]
    logr = [math.log10(m / o) for m, o in zip(model_mday, obs_mday)]
    rmse = math.sqrt(sum(x * x for x in e) / n)
    mae = sum(abs(x) for x in e) / n
    bias = sum(e) / n
    mean_obs = sum(obs_mday) / n
    mean_model = sum(model_mday) / n
    return {
        "n": n,
        "rmse_m_per_day": rmse,
        "mae_m_per_day": mae,
        "bias_m_per_day": bias,
        "mean_obs_m_per_day": mean_obs,
        "mean_model_m_per_day": mean_model,
        "mean_abs_rel_err": sum(abs(x) for x in e_rel) / n,
        "min_rel_err": min(e_rel),
        "max_rel_err": max(e_rel),
        "mean_log10_ratio": sum(logr) / n,
    }


# ---------------------------------------------------------------------------
# Natural-convection gap test
# ---------------------------------------------------------------------------
def gap_test(rows: list[dict] | None = None, floor_m_per_day: float = FLOOR_M_PER_DAY):
    """Lab/quiescent rows: observed melt vs the (guarded) model value of 0."""
    rows = rows if rows is not None else load_observations()
    res = []
    for row in rows:
        if row["u_rel_m_s"] == 0.0:
            obs = float(row["obs_m_per_day"])
            res.append(
                {
                    "record_id": row["record_id"],
                    "obs_m_per_day": obs,
                    "model_m_per_day": 0.0,
                    "gap_orders": math.log10(obs / floor_m_per_day),
                }
            )
    return res


# ---------------------------------------------------------------------------
# Inverse-U analysis for remote-sensing rows without ocean forcing
# ---------------------------------------------------------------------------
def required_u_rel(
    m_obs_m_per_s: float,
    delta_t_degC: float,
    length_m: float,
    salinity_psu: float = 35.0,
    lo: float = 1.0e-5,
    hi: float = 20.0,
    tol: float = 1.0e-10,
) -> tuple[float, bool]:
    """Bisect U_rel s.t. model melt == observed melt for a given dT and L.

    The closure is strictly monotone increasing in U_rel on the forced-convection
    branches, so the root is unique. Returns (U_rel, converged); when even the
    largest U_rel cannot reach the observed melt, ``converged=False`` is
    returned with U_rel = hi (lower bound on the required speed).
    """
    t = bm.ocean_freezing_point(salinity_psu, length_m) + delta_t_degC

    def resid(u):
        return bm.basal_melt_rate(
            ocean_temperature=t,
            salinity_psu=salinity_psu,
            depth_m=length_m,
            u_water=u,
            v_water=0.0,
            u_ice=0.0,
            v_ice=0.0,
            length_m=length_m,
        ) - m_obs_m_per_s

    if resid(hi) < 0.0:
        return hi, False
    if resid(lo) >= 0.0:
        return lo, False
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if abs(hi - lo) < tol * max(1.0, lo) or resid(mid) == 0.0:
            return mid, True
        if resid(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), True


def inverse_u_table(
    rows: list[dict] | None = None,
    delta_ts=(1.0, 2.0, 4.0),
    length_m=50.0,
    salinity_psu=35.0,
):
    """Required U_rel [m/s] per rs-derived row for a set of thermal drivings."""
    rows = rows if rows is not None else load_observations()
    out = []
    for row in rows:
        if row["tier"] != "rs-derived":
            continue
        if row["record_id"] == "OPEN_SO_context":
            continue
        m_s = float(row["obs_m_per_s"])
        entry = {"record_id": row["record_id"], "obs_m_per_day": float(row["obs_m_per_day"])}
        for dt in delta_ts:
            u, ok = required_u_rel(m_s, dt, length_m, salinity_psu)
            entry[f"u_rel_dT{int(dt):d}"] = u if ok else float("nan")
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Regime classification and sensitivity
# ---------------------------------------------------------------------------
def regime_name(reynolds: float) -> str:
    return "turbulent" if reynolds >= RE_CRIT else "laminar"


def sensitivity_sweep(
    ocean_temperature: float,
    salinity_psu: float,
    depth_m: float,
    base_u: float = 0.1,
    base_l: float = 50.0,
    u_rels=(0.05, 0.1, 0.2),
    lengths=(20.0, 50.0, 100.0),
):
    """Model melt [m/day] over a U_rel x L_char grid (document-range sweep)."""
    table = {}
    for u in u_rels:
        for lc in lengths:
            rate = bm.basal_melt_rate(
                ocean_temperature=ocean_temperature,
                salinity_psu=salinity_psu,
                depth_m=depth_m,
                u_water=u,
                v_water=0.0,
                u_ice=0.0,
                v_ice=0.0,
                length_m=lc,
            )
            table[(u, lc)] = rate * DAY_S
    return table


# ---------------------------------------------------------------------------
# Plotting (optional; matplotlib may be unavailable)
# ---------------------------------------------------------------------------
def make_plots(
    rows: list[dict] | None = None,
    outdir: str | os.PathLike | None = None,
) -> list[str]:
    """Generate the six Stage 10.8.2 figures; returns saved paths (or [])."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover - environment-dependent
        return []

    rows = rows if rows is not None else load_observations()
    out = Path(outdir) if outdir is not None else DEFAULT_PLOT_DIR
    out.mkdir(parents=True, exist_ok=True)
    saved = []

    def save(fig, name):
        path = out / name
        fig.savefig(path, dpi=140, bbox_inches="tight")
        saved.append(str(path))
        plt.close(fig)

    comparable = [r for r in rows if closure_applicable(r)]
    rs = [r for r in rows if r["tier"] == "rs-derived" and r["record_id"] != "OPEN_SO_context"]
    quiescent = [r for r in rows if r["u_rel_m_s"] == 0.0]

    obs_day = [float(r["obs_m_per_day"]) for r in comparable]
    model_day = [model_melt_m_per_day(r) for r in comparable]

    # ---- fig1: model vs obs (log-log) ------------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    mm = min(obs_day + [m for m in model_day if m > 0] + [3e-3])
    xx = max(obs_day + model_day + [1.0])
    ax.loglog([mm, 10 * xx], [mm, 10 * xx], "k--", lw=1, label="1:1")
    cleaned = [(o, m) for o, m in zip(obs_day, model_day) if m > 0]
    ax.plot(
        [o for o, _ in cleaned], [m for _, m in cleaned], "o",
        ms=7, color="#1f77b4", label="model-comparable (KW84, NJ80)",
    )
    for r, o, m in zip(comparable, obs_day, model_day):
        if m <= 0:
            ax.plot(o, FLOOR_M_PER_DAY, "v", ms=8, color="#d62728")
            ax.annotate("model=0\n(U=0)", (o, FLOOR_M_PER_DAY),
                        textcoords="offset points", xytext=(6, 6), fontsize=7)
    for r in quiescent:
        ax.plot(float(r["obs_m_per_day"]), FLOOR_M_PER_DAY, "v", ms=8,
                mfc="none", mec="#d62728",
                label="quiescent lab (model=0)" if r is quiescent[0] else None)
    for r in rs:
        ax.plot(float(r["obs_m_per_day"]), 1e-4, "s", ms=7, mfc="none", mec="#ff7f0e")
    ax.set_xlabel("observed melt rate [m/day]")
    ax.set_ylabel("production model melt rate [m/day]")
    ax.set_title("Stage 10.8.2 — basal melt: observation vs model")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7, loc="upper left")
    save(fig, PLOT_NAMES[0])

    # ---- fig2: melt vs thermal driving ------------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    _tf351 = bm.ocean_freezing_point(35.0, 50.0)
    dts = [0.5 + 0.1 * i for i in range(96)]  # 0.5..10 degC
    for u in (0.05, 0.1, 0.2, 0.5):
        curve = []
        for dt in dts:
            m = bm.basal_melt_rate(_tf351 + dt, 35.0, 50.0, u, 0.0, 0.0, 0.0, 50.0)
            curve.append(m * DAY_S)
        ax.plot(dts, curve, lw=1.5, label=f"model U={u} m/s, L=50 m")
    for r in rows:
        if r["record_id"].startswith("NJ80"):
            ax.plot(float(r["T_degC"]) - _tf351, float(r["obs_m_per_day"]),
                    "o", ms=7, color="#2ca02c",
                    label="NJ80 obs (synthesis)" if r is next(
                        (x for x in rows if x["record_id"].startswith("NJ80")), None
                    ) else None)
    for r in quiescent:
        ax.plot(float(r["T_degC"]) + 1.8, float(r["obs_m_per_day"]),
                "^", ms=7, mfc="none", mec="#d62728",
                label="RH80 quiescent lab" if r is quiescent[0] else None)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("thermal driving dT = T - Tf [degC]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Stage 10.8.2 — melt rate vs thermal driving")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7)
    save(fig, PLOT_NAMES[1])

    # ---- fig3: inverse-U for rs rows ---------------------------------------
    inv = inverse_u_table(rows)
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    labels = [e["record_id"] for e in inv]
    for dt in (1, 2, 4):
        y = []
        for e in inv:
            v = e.get(f"u_rel_dT{dt:d}")
            y.append(v if v == v else float("nan"))
        ax.semilogy(labels, y, marker="o", ms=6, lw=1.5, label=f"required U_rel, dT={dt} degC")
        for rid, v in zip(labels, y):
            if v != v:
                ax.semilogy([rid], [2.0], marker="+", ms=10, color="#d62728")
    ax.axhline(0.1, color="k", ls=":", lw=1)
    ax.annotate("typical 0.1", (0.02, 0.105), fontsize=7)
    ax.set_ylabel("required U_rel [m/s] to reproduce observed melt (L=50 m, S=35)")
    ax.set_title("Stage 10.8.2 — inverse-U analysis (remote-sensing rows)")
    ax.grid(True, which="major", alpha=0.3)
    ax.tick_params(axis="x", labelrotation=20, labelsize=7)
    ax.legend(fontsize=7)
    save(fig, PLOT_NAMES[2])

    # ---- fig4: regime map (Re vs dT) ---------------------------------------
    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    axes_data = []
    for r in comparable:
        dT = float(r["T_degC"]) - bm.ocean_freezing_point(float(r["S_psu"]), float(r["L_char_m"]))
        re = bm.reynolds_number(float(r["u_rel_m_s"]), float(r["L_char_m"]))
        axes_data.append((re, max(dT, 0.0), r["record_id"]))
    xmax = max([re for re, _, _ in axes_data]) * 1.5
    ax.axvspan(RE_CRIT, xmax, color="#1f77b4", alpha=0.12)
    ax.axvline(RE_CRIT, color="k", ls="--", lw=1)
    ax.annotate("Re_crit = 5e5\n(laminar left of line)", (RE_CRIT, 0.2), fontsize=7)
    for re, dt, rid in axes_data:
        ax.semilogy(re, dt, "o", ms=8)
        ax.annotate(rid, (re, dt), textcoords="offset points", xytext=(6, -2), fontsize=7)
    ax.set_xlim(1e4, xmax)
    ax.set_ylim(0.2, max([dt for _, dt, _ in axes_data]) * 1.25)
    ax.set_xlabel("Reynolds number Re = U_rel L / nu")
    ax.set_ylabel("thermal driving dT [degC]")
    ax.set_title("Stage 10.8.2 — parameter regime of comparable observations")
    ax.grid(True, which="both", alpha=0.25)
    save(fig, PLOT_NAMES[3])

    # ---- fig5: observed values with uncertainty bands ----------------------
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    by_obs = sorted(rows, key=lambda r: float(r["obs_m_per_day"]))
    xs = range(len(by_obs))
    for i, r in enumerate(by_obs):
        o = float(r["obs_m_per_day"])
        u = float(r["obs_unc_m_per_day"])
        color = "#1f77b4" if closure_applicable(r) else "#7f7f7f"
        ax.plot(i, o, "o", ms=6, color=color)
        if u == u:  # not NaN
            ax.plot([i, i], [max(o - u, 1e-4 * o), o + u], color=color, lw=1.2)
    model_x = [i for i, r in enumerate(by_obs) if closure_applicable(r)]
    model_y = [model_melt_m_per_day(r) for r in by_obs if closure_applicable(r)]
    ax.scatter(model_x, model_y, marker="x", s=50, color="#d62728",
               label="production model (comparable rows)")
    ax.set_yscale("log")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([r["record_id"] for r in by_obs], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("observed melt rate [m/day]")
    ax.set_title("Stage 10.8.2 — observed melt rates (uncertainty where reported)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7)
    save(fig, PLOT_NAMES[4])

    # ---- fig6: log10(model/obs) bias ---------------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    labels = [r["record_id"] for r in comparable]
    ratio = [math.log10(m / o) for o, m in zip(obs_day, model_day) if m > 0]
    rlabels = [lab for lab, m in zip(labels, model_day) if m > 0]
    ax.bar(rlabels, ratio, color="#1f77b4")
    ax.axhline(0.0, color="k", lw=1)
    ax.axhline(math.log10(2.0), color="#d62728", ls=":", lw=1)
    ax.axhline(math.log10(0.5), color="#d62728", ls=":", lw=1)
    ax.annotate("factor 2 band", (0.0, math.log10(2.0) + 0.02), fontsize=7)
    ax.set_ylabel("log10(model/obs)")
    ax.set_title("Stage 10.8.2 — model/observation bias (comparable rows)")
    ax.grid(True, alpha=0.25)
    save(fig, PLOT_NAMES[5])

    return saved


# ---------------------------------------------------------------------------
# Human-readable summary (CLI)
# ---------------------------------------------------------------------------
def render_summary(rows: list[dict] | None = None) -> str:
    rows = rows if rows is not None else load_observations()
    lines = []
    lines.append("Stage 10.8.2 observational basal-melt validation")
    lines.append("=" * 60)
    by_tier = {}
    for r in rows:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
    lines.append(f"dataset: {len(rows)} records")
    for k in sorted(by_tier):
        lines.append(f"  {k}: {by_tier[k]}")
    comparable = [r for r in rows if closure_applicable(r)]
    lines.append(f"closure-applicable (metrics) rows: {len(comparable)} "
                 f"({', '.join(r['record_id'] for r in comparable)})")

    cmp = compare_rows(rows)
    obs = [o for _, o, _, _, _ in cmp]
    mod = [m for _, _, m, _, _ in cmp]
    mets = compute_metrics(obs, mod)
    lines.append("metrics (m/day):")
    for k, v in mets.items():
        lines.append(f"  {k}: {v:.6g}")

    gaps = gap_test(rows)
    if gaps:
        lines.append("natural-convection gap (quiescent lab rows, model=0):")
        for g in gaps:
            lines.append(f"  {g['record_id']}: obs {g['obs_m_per_day']:.4f} m/day "
                         f"({g['gap_orders']:.1f} orders above model floor)")
    inv = inverse_u_table(rows)
    if inv:
        lines.append("inverse-U (required U_rel, m/s; L=50 m, S=35):")
        for e in inv:
            us = " ".join(f"dT{d}:{e.get(f'u_rel_dT{d:d}', float('nan')):.3g}"
                          for d in (1, 2, 4))
            lines.append(f"  {e['record_id']}: {e['obs_m_per_day']:.4f} m/day -> {us}")
    return "\n".join(lines)


def main(argv=None) -> int:
    rows = load_observations()
    print(render_summary(rows))
    saved = make_plots(rows)
    if saved:
        print(f"saved {len(saved)} figures to "
              f"{Path(saved[0]).parent}")
        for s in saved:
            print(f"  {Path(s).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())