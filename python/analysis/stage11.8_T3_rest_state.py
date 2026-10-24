#!/usr/bin/env python3
"""
Stage 11.8.0 T3 — rest-state analysis (ocean without forcing).

Reads run outputs for the given run IDs (results_day_00..30) and computes:
  - max |U|, |V|, |W| per day; kinetic energy (0.5*rho*(u^2+v^2) integrated);
  - T/S RMS drift from day 0; min density anomaly; min N^2;
  - volume / heat / salt conservation (relative drift day 0 -> last day);
  - CA statistics parsed from the run stdout (nmix, maxiter, guard);
  - spurious-current location (max speed cell) and its neighbourhood;
  - interface-defect markers: day-0 T=0 wet cells (product/model mask gap),
    day-1 boundary-column (i=is1) T=S=0 cells.
Outputs data/validation/t3_rest_result.json.

Usage:
  python python/analysis/stage11.8_T3_rest_state.py \
      --run t3_legacy_canonical --run t3_eos80_canonical \
      --run t3_legacy_rebuild --out data/validation/t3_rest_result.json
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[2]
AREA = 13890.0 * 13890.0
RHO0 = 1027.0
G = 9.81


def load_day(run_dir, day):
    path = run_dir / f"results_day_{day:02d}.nc"
    with Dataset(path) as d:
        u = np.array(d["u_velocity"][:], dtype=np.float64)
        v = np.array(d["v_velocity"][:], dtype=np.float64)
        w = np.array(d["w_velocity"][:], dtype=np.float64)
        T = np.array(d["temperature"][:], dtype=np.float64) - 273.15
        S = np.array(d["salinity_mass_fraction"][:], dtype=np.float64)
        ro = np.array(d["density_anomaly"][:], dtype=np.float64)
        lev = np.array(d["water_column_levels"][:], dtype=np.int32)
        z = np.array(d["depth"][:], dtype=np.float64)
        dw = np.array(d["depth_w"][:], dtype=np.float64)
    kk = np.arange(T.shape[0])[:, None, None]
    mask = (lev[None, :, :] > 0) & (kk < lev[None, :, :])
    thick = (dw[1:] - dw[:-1])[:, None, None] * AREA
    return dict(u=u, v=v, w=w, T=T, S=S, ro=ro, lev=lev, z=z,
                mask=mask, vol=thick)


def parse_ca(log_path):
    out = {}
    if not log_path.exists():
        return out
    for ln in log_path.read_text(errors="replace").splitlines():
        m = re.match(r".*daily diag day=\s*(\d+).*nmix=\s*(\d+).*maxiter=\s*(\d+).*guard=\s*(\S+)", ln)
        if m:
            out[int(m.group(1))] = {
                "nmix": int(m.group(2)), "maxiter": int(m.group(3)),
                "guard": m.group(4),
            }
    return out


def classify(rows):
    last = rows[-1]
    nan_any = any(r["nan"] > 0 for r in rows)
    ke = [r["ke"] for r in rows]
    ke_growth = (ke[-1] / ke[1]) if len(ke) > 1 and ke[1] > 0 else float("inf")
    if nan_any:
        return "UNSTABLE", "NaN appears"
    if last["umax"] > 0.5 or last["vmax"] > 0.5 or ke_growth > 10.0:
        return "UNSTABLE", (f"currents/KE grow (Umax {last['umax']:.3f} m/s, "
                            f"KE growth x{ke_growth:.1f})")
    if last["umax"] > 0.01 or last["drift_T"] > 0.01 or last["drift_S_psu"] > 1e-3:
        return "DRIFTING", "above rest tolerance but bounded"
    return "STABLE", "within rest tolerance"


def analyse_run(run_id):
    run_root = PROJECT / "data/runs" / run_id
    nc_dir = run_root / "output/nc"
    if not nc_dir.exists():
        return None
    d0 = load_day(nc_dir, 0)
    T0, S0 = d0["T"], d0["S"]
    n_days = 0
    while (nc_dir / f"results_day_{n_days + 1:02d}.nc").exists():
        n_days += 1
    ca = parse_ca(run_root / "stdout.log")
    rows = []
    for day in range(0, n_days + 1):
        d = d0 if day == 0 else load_day(nc_dir, day)
        mask = d["mask"]
        u, v, T, S, ro = d["u"], d["v"], d["T"], d["S"], d["ro"]
        nan = int(np.isnan(u).sum() + np.isnan(v).sum() + np.isnan(T).sum()
                  + np.isnan(S).sum())
        umax = float(np.nanmax(np.abs(u[mask]))) if mask.any() else 0.0
        vmax = float(np.nanmax(np.abs(v[mask]))) if mask.any() else 0.0
        wm = np.isfinite(d["w"])
        wmax = float(np.nanmax(np.abs(d["w"][wm]))) if wm.any() else 0.0
        ke = float(np.nansum(np.where(mask, 0.5 * RHO0 * (u * u + v * v) * d["vol"], 0.0)))
        vol = float(np.nansum(np.where(mask, d["vol"], 0.0)))
        heat = float(np.nansum(np.where(mask, T * d["vol"], 0.0)))
        salt = float(np.nansum(np.where(mask, S * d["vol"], 0.0)))
        dT = float(np.sqrt(np.nanmean(np.where(mask, (T - T0) ** 2, np.nan))))
        dS = float(np.sqrt(np.nanmean(np.where(mask, (S - S0) ** 2, np.nan)))) * 1000.0
        romin = float(np.nanmin(np.where(mask, ro, np.nan)))
        # N^2 from density anomaly
        dzv = np.diff(d["z"])[:, None, None]
        m2 = mask[:-1] & mask[1:]
        N2 = -(G / RHO0) * (ro[1:] - ro[:-1]) / dzv
        n2min = float(np.nanmin(np.where(m2, N2, np.nan)))
        rows.append(dict(day=day, nan=nan, umax=umax, vmax=vmax, wmax=wmax,
                         ke=ke, volume=vol, heat=heat, salt=salt,
                         drift_T=dT, drift_S_psu=dS, ro_min=romin,
                         N2_min=n2min, ca=ca.get(day)))

    r0, rN = rows[0], rows[-1]
    conservation = {
        "volume_rel": abs(rN["volume"] - r0["volume"]) / abs(r0["volume"]),
        "heat_rel": abs(rN["heat"] - r0["heat"]) / abs(r0["heat"]),
        "salt_rel": abs(rN["salt"] - r0["salt"]) / abs(r0["salt"]),
    }
    status, why = classify(rows)

    # spurious current location at the last day
    last = load_day(nc_dir, n_days)
    spd = np.sqrt(last["u"] ** 2 + last["v"] ** 2)
    if np.isfinite(spd).any() and last["mask"].any():
        spd_masked = np.where(last["mask"], spd, np.nan)
        k, y, x = map(int, np.unravel_index(np.nanargmax(spd_masked), spd.shape))
        loc = {"k": k + 1, "y": y + 1, "x": x + 1,
               "speed_m_s": float(np.nanmax(spd_masked))}
    else:
        loc = None

    # interface defect markers
    day1 = load_day(nc_dir, min(1, n_days)) if n_days >= 1 else d0
    boundary_s0 = int(np.sum((day1["S"] == 0.0) & day1["mask"]
                             & (np.arange(133)[None, None, :] == 132)))
    t0_gap = int(np.sum((np.abs(d0["T"]) < 1e-5) & d0["mask"]))

    return {
        "run_id": run_id,
        "days_completed": n_days,
        "classification": status,
        "classification_reason": why,
        "max_u_over_run": max(r["umax"] for r in rows),
        "max_v_over_run": max(r["vmax"] for r in rows),
        "max_w_over_run": max(r["wmax"] for r in rows),
        "ke_day0_day15_day30": [rows[0]["ke"],
                                rows[min(15, n_days)]["ke"],
                                rows[n_days]["ke"]],
        "drift_T_rms_day30": rows[n_days]["drift_T"],
        "drift_S_rms_psu_day30": rows[n_days]["drift_S_psu"],
        "conservation": conservation,
        "ro_min_day30": rows[n_days]["ro_min"],
        "N2_min_day30": rows[n_days]["N2_min"],
        "ca": {"nmix_last": rows[n_days]["ca"]["nmix"] if rows[n_days]["ca"] else None,
               "maxiter_last": rows[n_days]["ca"]["maxiter"] if rows[n_days]["ca"] else None,
               "guard_last": rows[n_days]["ca"]["guard"] if rows[n_days]["ca"] else None,
               "nmix_total": sum((r["ca"] or {}).get("nmix", 0) for r in rows)},
        "max_current_location_last": loc,
        "interface_defects": {
            "day0_T_zero_wet_cells": t0_gap,
            "day1_boundary_column_S_zero_cells": boundary_s0,
        },
        "daily": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--out", type=Path,
                    default=PROJECT / "data/validation/t3_rest_result.json")
    args = ap.parse_args()
    results = {}
    for run in args.run:
        r = analyse_run(run)
        if r is None:
            print(f"SKIP {run}: no output")
            continue
        results[run] = r
        print(f"{run}: {r['days_completed']} days, {r['classification']} "
              f"({r['classification_reason']}); Umax={r['max_u_over_run']:.3f} "
              f"Vmax={r['max_v_over_run']:.3f}; KE={r['ke_day0_day15_day30']}")
        print(f"   conservation {r['conservation']}; CA {r['ca']}; "
              f"defects {r['interface_defects']}")
    out = {"test": "t3_rest_state", "stage": "11.8.0 T3",
           "runs": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, default=float))
    print(f"Results: {args.out.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()