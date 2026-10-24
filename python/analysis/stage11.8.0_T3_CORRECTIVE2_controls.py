#!/usr/bin/env python3
"""
Stage 11.8.0 T3-CORRECTIVE-2 — controlled CA/RO experiments.

Diagnostic only.  Compares the 30-day rest runs:
  baseline (CA writes RO), freeze_TS (no T/S+CA), freeze_RO (CA mixes T/S but
  does not write RO), freeze_TW (baroclinic PGF disabled), dt=1800, and the
  EOS-80 equivalents.

Outputs data/validation/t3c2_controls_analysis.json.
"""

import json
import re
from importlib.machinery import SourceFileLoader
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
DIAG = SourceFileLoader(
    "t3c2diag",
    str(PROJECT / "python/analysis/stage11.8.0_T3_CORRECTIVE2_diagnosis.py"),
).load_module()

RUNS = {
    "baseline_legacy": "t3c_legacy_canonical",
    "freeze_ts_legacy": "t3c2_ts_30",
    "freeze_ro_legacy": "t3c2_ro_30",
    "freeze_tw_legacy": "t3c2_tw_30",
    "dt1800_legacy": "t3c2_dt1800",
    "baseline_eos80": "t3c_eos80_canonical",
    "freeze_ro_eos80": "t3c2_eos80_ro_30",
    "freeze_ts_eos80": "t3c2_eos80_ts_30",
}
DAYS = (1, 5, 10, 15, 30)


def parse_ca(run):
    path = PROJECT / "data/runs" / run / "stdout.log"
    out = {}
    if not path.exists():
        return out
    for ln in path.read_text(errors="replace").splitlines():
        m = re.match(r".*daily diag day=\s*(\d+).*nmix=\s*(\d+).*maxiter=\s*(\d+).*guard=\s*(\S+)", ln)
        if m:
            out[int(m.group(1))] = {
                "nmix": int(m.group(2)),
                "maxiter": int(m.group(3)),
                "guard": m.group(4),
            }
    return out


def run_metrics(run):
    nc = PROJECT / "data/runs" / run / "output/nc"
    if not (nc / "results_day_00.nc").exists():
        return None
    d0 = DIAG.load_day(nc, 0)
    ca = parse_ca(run)
    out = {"run": run, "days": 0, "daily": {}}
    day = 0
    while (nc / f"results_day_{day:02d}.nc").exists():
        day += 1
    out["days"] = day - 1
    for day in DAYS:
        if day > out["days"]:
            continue
        d = DIAG.load_day(nc, day)
        m = d["mask"]
        ke = float(np.nansum(np.where(m, 0.5 * 1027.0 * (d["u"] ** 2 + d["v"] ** 2)
                                   * d["vol"], 0.0)))
        ca_d = ca.get(day)
        out["daily"][str(day)] = {
            "ke_j": ke,
            "umax": float(np.nanmax(np.where(m, np.abs(d["u"]), np.nan))),
            "vmax": float(np.nanmax(np.where(m, np.abs(d["v"]), np.nan))),
            "ca": ca_d,
        }
    # CA-induced RO change vs the frozen-RO run (LEGACY) / initial for EOS80
    out["ro_change"] = {}
    for day in DAYS:
        if day > out["days"]:
            continue
        d = DIAG.load_day(nc, day)
        if "eos80" in run:
            ref = d0
        else:
            ref = DIAG.load_day(PROJECT / "data/runs/t3c2_ro_30/output/nc", day)
        dro = d["ro"] - ref["ro"]
        m = d["mask"]
        x = np.where(m, np.abs(dro), np.nan)
        k, j, i = np.unravel_index(np.nanargmax(x), x.shape)
        sp = np.hypot(d["u"], d["v"])
        grad = np.hypot(np.gradient(dro, DIAG.DX, axis=2),
                        np.gradient(dro, DIAG.DX, axis=1))
        a = np.where(m, sp, np.nan).ravel()
        c = np.where(m, grad, np.nan).ravel()
        ok = np.isfinite(a) & np.isfinite(c)
        out["ro_change"][str(day)] = {
            "max_abs_ro_change_kg_m3": float(np.nanmax(x)),
            "k": k + 1, "y": j + 1, "x": i + 1,
            "lat": float(d["lat"][j, i]), "lon": float(d["lon"][j, i]),
            "max_ro_gradient_kg_m4": float(np.nanmax(np.where(m, grad, np.nan))),
            "corr_speed_gradient": (
                float(np.corrcoef(a[ok], c[ok])[0, 1])
                if ok.sum() > 10 and np.nanstd(a[ok]) > 1e-12 and np.nanstd(c[ok]) > 1e-12
                else None),
        }
    return out


def main():
    results = {}
    for name, run in RUNS.items():
        r = run_metrics(run)
        if r:
            results[name] = r
            print(f"{name:20s} {run:28s} days={r['days']:3d} "
                  f"KE30={r['daily'].get('30', {}).get('ke_j', 0):.3e} "
                  f"Umax30={r['daily'].get('30', {}).get('umax', 0):.3f} "
                  f"CA_nmix30={(r['daily'].get('30', {}).get('ca') or {}).get('nmix')}")

    # PGF work decomposition: baseline vs freeze_RO (LEGACY)
    base = PROJECT / "data/runs/t3c_legacy_canonical/output/nc"
    frozen = PROJECT / "data/runs/t3c2_ro_30/output/nc"
    pgf_ca = {}
    for day in DAYS:
        b = DIAG.load_day(base, day)
        f = DIAG.load_day(frozen, day)
        au_b, av_b = DIAG.pgf_block200(b)
        au_f, av_f = DIAG.pgf_block200(f)
        au_ca, av_ca = au_b - au_f, av_b - av_f
        m = b["mask"]
        w_tot = float(np.nansum(np.where(m, 1027.0 * (b["u"] * au_b + b["v"] * av_b)
                                          * b["vol"], 0.0)))
        w_ca = float(np.nansum(np.where(m, 1027.0 * (b["u"] * au_ca + b["v"] * av_ca)
                                         * b["vol"], 0.0)))
        pgf_ca[str(day)] = {
            "pgf_work_total_w": w_tot,
            "pgf_work_ca_induced_w": w_ca,
            "ca_fraction": (w_ca / w_tot) if w_tot else None,
        }

    # double-counting of the surface layer in Block 200
    d0 = DIAG.load_day(base, 0)
    au1, av1 = DIAG.pgf_block200(d0, double_count=True)
    au2, av2 = DIAG.pgf_block200(d0, double_count=False)
    mask = d0["mask"]
    diff = np.hypot(au1 - au2, av1 - av2)
    tot = np.hypot(au2, av2)
    dc = {
        "max_pgf_model_m_s2": float(np.nanmax(np.where(mask, tot, np.nan))),
        "max_double_count_difference_m_s2": float(np.nanmax(np.where(mask, diff, np.nan))),
        "relative": float(np.nanmax(np.where(mask, diff, np.nan))
                          / np.nanmax(np.where(mask, tot, np.nan))),
    }

    out = {
        "stage": "11.8.0 T3-CORRECTIVE-2",
        "runs": results,
        "pgf_ca_decomposition_legacy": pgf_ca,
        "block200_double_count": dc,
    }
    path = PROJECT / "data/validation/t3c2_controls_analysis.json"
    path.write_text(json.dumps(out, indent=2, default=float))
    print(f"Results: {path}")


if __name__ == "__main__":
    main()
