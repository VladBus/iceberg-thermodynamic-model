#!/usr/bin/env python3
"""Stage 12.7.audit: three-case voxel melt-deficiency diagnostic.

Runs iceberg_run with VOXEL_ENABLED=true, VOXEL_DEBUG_MELT=true for the
small/medium/large representative Enderlin cases selected from the Stage 12.7a
results, at VOXEL_KT_SCALE = 1, 5, 10.  Also runs the bulk model for reference.

Outputs:
  <out-dir>/audit.json
  <out-dir>/audit.csv
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

RHO_ICE = 916.7


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path,
                   default=Path("docs/validation/stage12.7a_trajectory_manifest.csv"))
    p.add_argument("--results", type=Path,
                   default=Path("docs/validation/stage12.7a_results.csv"))
    p.add_argument("--glorys-dir", type=Path,
                   default=Path("data/input/raw/reanalysis/glorys12/antarctic"))
    p.add_argument("--out-dir", type=Path,
                   default=Path("data/validation/results/audit_voxel"))
    p.add_argument("--iceberg-run", type=Path, default=None)
    p.add_argument("--scales", default="1,5,10")
    p.add_argument("--timeout", type=int, default=600)
    return p.parse_args()


def find_binary(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    cands = sorted(Path("build").glob("*/app/iceberg_run"), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise SystemExit("iceberg_run not found; build first")
    return cands[-1]


def select_cases(man: pd.DataFrame, res: pd.DataFrame) -> list[dict]:
    d = man.merge(res[["case_id", "ratio_bulk", "ratio_voxel", "mean_delta_t_bulk"]],
                  on="case_id", how="inner")
    d["sqrtA"] = np.sqrt(d.surface_area)
    picks = []
    small = d[(d.sqrtA < 100) & (d.mean_delta_t_bulk > 2)].sort_values(
        "mean_delta_t_bulk", ascending=False)
    med = d[(d.sqrtA >= 100) & (d.sqrtA <= 300) &
            d.mean_delta_t_bulk.between(1, 2)].copy()
    med["score"] = (med.mean_delta_t_bulk - 1.5).abs()
    med = med.sort_values("score")
    large = d[(d.sqrtA > 300) & (d.mean_delta_t_bulk < 1)].sort_values(
        "mean_delta_t_bulk")
    for label, frame in (("small", small), ("medium", med), ("large", large)):
        if frame.empty:
            raise SystemExit(f"no representative {label} case found")
        picks.append({"label": label, **frame.iloc[0].to_dict()})
    return picks


def parse_summary(stdout: str) -> dict | None:
    for line in stdout.splitlines():
        if line.startswith("HINDCAST_SUMMARY"):
            v = [float(x.replace("D", "E")) for x in line.split()[1:]]
            if len(v) < 10:
                return None
            return {
                "final_volume": v[0], "initial_volume": v[1],
                "basal": v[2], "lateral": v[3], "surface": v[4],
                "vapor": v[5], "wave": v[6], "mean_a_wet": v[7],
                "seconds": v[8], "mass": v[9],
                "mean_delta_t": v[10] if len(v) > 10 else np.nan,
            }
    return None


def parse_debug(stdout: str) -> dict:
    out: dict = {}
    for line in stdout.splitlines():
        if line.startswith("VOXEL_DEBUG_FACE2"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 5:
                out.update(gamma_t=v[0], gamma_s=v[1], t_voxel=v[2], h_norm=v[3],
                           draft_debug=v[4])
        elif line.startswith("VOXEL_DEBUG_FACE"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 10:
                out.update(t_w=v[0], s_w=v[1], u_rel=v[2], depth=v[3], t_f=v[4],
                           kt_u=v[5], ks_u=v[6], t_b=v[7], s_b=v[8], m=v[9])
        elif line.startswith("VOXEL_DEBUG_STATE"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 10:
                out.update(state_L=v[0], state_W=v[1], state_H=v[2],
                           vox_L=v[3], vox_W=v[4], vox_H=v[5],
                           area_state=v[6], area_state_vox=v[7],
                           mass_state_vox=v[8], draft_state=v[9])
        elif line.startswith("VOXEL_DEBUG_MEAN"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 3:
                out.update(mean_u_rel=v[0], mean_tb=v[1], mean_sb=v[2])
        elif line.startswith("VOXEL_DEBUG_TOTAL"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 10:
                out.update(area_voxel=v[0], area_analytical=v[1],
                           basal_kg_s=v[2], lateral_kg_s=v[3], surface_kg_s=v[4],
                           draft=v[5], L_vox=v[6], W_vox=v[7], H_vox=v[8],
                           mass_vox=v[9])
    return out


def traj_speed(path: Path) -> dict:
    d = pd.read_csv(path)
    if len(d) < 2:
        return {"u_mean": 0.0, "v_mean": 0.0, "speed_mean": 0.0}
    t = d.time_s.to_numpy(float); lat = d.lat.to_numpy(float); lon = d.lon.to_numpy(float)
    dt = np.diff(t)
    ok = dt > 0
    dlat = np.diff(lat)[ok]; dlon = np.diff(lon)[ok]; dt = dt[ok]
    R = 6371.0e3
    v = dlat*R*np.pi/180.0/dt
    u = dlon*R*np.cos(np.deg2rad(lat[:-1]))*np.pi/180.0/dt
    return {"u_mean": float(np.mean(u)), "v_mean": float(np.mean(v)),
            "speed_mean": float(np.mean(np.hypot(u, v)))}


def run_case(binary: Path, row: pd.Series, out_nc: Path, daily: Path, static: Path,
             voxel: bool, kt_scale: float, timeout: int) -> dict:
    env = os.environ.copy()
    env["VOXEL_ENABLED"] = "true" if voxel else "false"
    env["VOXEL_DEBUG_MELT"] = "true" if voxel else "false"
    env["VOXEL_KT_SCALE"] = str(kt_scale)
    cmd = [
        str(binary), str(row.lat_i), str(row.lon_i), str(row.L0), str(row.W0),
        str(row.H0), str(row.duration_days), "3600", str(out_nc),
        str(daily), str(static), "", "",
        "--prescribed_trajectory", str(row.trajectory),
        "--epoch", str(int(row.epoch)),
        "--start-date", str(row.date_start).replace("-", ""),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    if p.returncode != 0:
        return {"ok": False, "rc": p.returncode, "stderr": p.stderr[-500:]}
    s = parse_summary(p.stdout)
    if s is None:
        return {"ok": False, "rc": 0, "stderr": "no HINDCAST_SUMMARY"}
    submarine = (s["basal"] + s["lateral"] + s["wave"]) / RHO_ICE
    rate = submarine / (s["mean_a_wet"] * s["seconds"]) * 86400.0
    ts = traj_speed(Path(str(row.trajectory)))
    return {"ok": True, "rate": rate,
            "ratio": rate / float(row.melt_rate) if row.melt_rate > 0 else np.nan,
            "summary": s, "debug": parse_debug(p.stdout), "traj_speed": ts}


def main() -> int:
    a = args()
    man = pd.read_csv(a.manifest)
    res = pd.read_csv(a.results)
    binary = find_binary(a.iceberg_run)
    scales = [float(x) for x in a.scales.split(",")]
    a.out_dir.mkdir(parents=True, exist_ok=True)
    cases = select_cases(man, res)
    out = {"binary": str(binary), "cases": [], "scales": scales,
           "H4_note": "wave erosion not tested: no WAM product; synthetic Hs=2 is unit-test only"}
    rows = []
    for c in cases:
        row = man[man.case_id == c["case_id"]].iloc[0]
        daily = a.glorys_dir / f"glorys12_{row.site}_daily.nc"
        static = a.glorys_dir / f"glorys12_{row.site}_static.nc"
        entry = {
            "label": c["label"], "case_id": c["case_id"], "region": row.region,
            "sqrtA": float(c["sqrtA"]), "mean_delta_t": float(c["mean_delta_t_bulk"]),
            "observed_melt": float(row.melt_rate), "H0": float(row.H0),
            "H0_rule": row.H0_rule, "runs": {},
        }
        if daily.exists() and static.exists():
            bulk = run_case(binary, row, a.out_dir / f"{row.case_id}_bulk.nc",
                            daily, static, False, 1.0, a.timeout)
            entry["runs"]["bulk"] = bulk
            if bulk.get("ok"):
                rows.append({"case": c["case_id"], "label": c["label"], "model": "bulk",
                             "kt_scale": 1.0, "ratio": bulk["ratio"],
                             **{f"dbg_{k}": v for k, v in bulk["debug"].items()}})
            for s in scales:
                r = run_case(binary, row, a.out_dir / f"{row.case_id}_voxel_kt{s:g}.nc",
                             daily, static, True, s, a.timeout)
                entry["runs"][f"voxel_kt{s:g}"] = r
                if r.get("ok"):
                    rows.append({"case": c["case_id"], "label": c["label"], "model": "voxel",
                                 "kt_scale": s, "ratio": r["ratio"],
                                 **{f"dbg_{k}": v for k, v in r["debug"].items()}})
        else:
            entry["runs"]["error"] = "GLORYS site file missing"
        out["cases"].append(entry)
    (a.out_dir / "audit.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    pd.DataFrame(rows).to_csv(a.out_dir / "audit.csv", index=False)
    for c in out["cases"]:
        print(f"{c['label']:6s} {c['case_id']} sqrtA={c['sqrtA']:.1f} "
              f"TF={c['mean_delta_t']:.2f} obs={c['observed_melt']:.5f}")
        for name, r in c["runs"].items():
            if isinstance(r, dict) and r.get("ok"):
                d = r["debug"]
                print(f"  {name:12s} ratio={r['ratio']:.4f} "
                      f"area_vox={d.get('area_voxel', float('nan')):.0f} "
                      f"area_an={d.get('area_analytical', float('nan')):.0f} "
                      f"u_rel={d.get('u_rel', float('nan')):.4f} "
                      f"m={d.get('m', float('nan')):.3e}")
            else:
                print(f"  {name:12s} FAILED")
    print(f"wrote {a.out_dir/'audit.json'} and audit.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
