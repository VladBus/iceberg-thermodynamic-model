#!/usr/bin/env python3
"""Stage 12.7a Enderlin23 hindcast driver.

Runs ``iceberg_run`` in prescribed-trajectory mode for each manifest row, for
the bulk and/or voxel thermodynamic model, and compares the modeled submarine
melt rate with the Enderlin23 observation.

The Antarctic GLORYS site files must exist in ``--glorys-dir`` as
``glorys12_<site>_daily.nc`` / ``_static.nc``.  If they are absent the row is
reported as ``SKIP_NO_DATA`` and no result is fabricated.

Modeled submarine melt rate:
  (basal + lateral + wave mass loss) / rho_i
  / (mean wetted area * simulated duration)   [m/day]
Surface/vapour losses are kept separate (Enderlin23 melt_rate is
SUBMARINE_TOTAL = side + basal).

Usage:
  python python/validation/enderlin23_hindcast.py \
    --glorys-dir data/input/raw/reanalysis/glorys12/antarctic \
    --output-dir data/validation/results/enderlin23 \
    --voxel-enabled both --wave-enabled false
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RHO_ICE = 916.7  # kg m-3, model constant


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path,
                   default=Path("docs/validation/stage12.7a_trajectory_manifest.csv"))
    p.add_argument("--trajectory-dir", type=Path,
                   default=Path("data/validation/trajectories/enderlin23"))
    p.add_argument("--glorys-dir", type=Path,
                   default=Path("data/input/raw/reanalysis/glorys12/antarctic"))
    p.add_argument("--output-dir", type=Path,
                   default=Path("data/validation/results/enderlin23"))
    p.add_argument("--iceberg-run", type=Path, default=None)
    p.add_argument("--voxel-enabled", choices=["true", "false", "both"], default="both")
    p.add_argument("--wave-enabled", choices=["true", "false"], default="false")
    p.add_argument("--dt", type=float, default=3600.0)
    p.add_argument("--max-icebergs", type=int, default=0)
    p.add_argument("--timeout", type=int, default=900)
    return p.parse_args()


def find_binary(explicit: Path | None) -> Path:
    if explicit:
        if explicit.exists():
            return explicit
        raise SystemExit(f"iceberg_run not found: {explicit}")
    cands = sorted(Path("build").glob("*/app/iceberg_run"), key=lambda p: p.stat().st_mtime)
    if cands:
        return cands[-1]
    found = shutil.which("iceberg_run")
    if found:
        return Path(found)
    raise SystemExit("iceberg_run not found; build first (`fpm build --flag '-I/usr/include'`)")


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
                "seconds": v[8], "final_mass": v[9],
                "mean_delta_t": v[10] if len(v) > 10 else np.nan,
            }
    return None


def main() -> int:
    a = args()
    man = pd.read_csv(a.manifest)
    if a.max_icebergs > 0:
        man = man.head(a.max_icebergs)
    binary = find_binary(a.iceberg_run)
    a.output_dir.mkdir(parents=True, exist_ok=True)

    models = ["bulk", "voxel"] if a.voxel_enabled == "both" else \
             ["bulk" if a.voxel_enabled == "false" else "voxel"]

    rows = []
    n_skip = 0
    for _, r in man.iterrows():
        case = str(r.case_id)
        daily = a.glorys_dir / f"glorys12_{r.site}_daily.nc"
        static = a.glorys_dir / f"glorys12_{r.site}_static.nc"
        traj = Path(str(r.trajectory))
        if not traj.exists():
            traj = a.trajectory_dir / f"{case}.csv"
        rec = {
            "case_id": case, "site": r.site, "region": r.region,
            "date_start": r.date_start, "date_end": r.date_end,
            "interval_days": float(r.duration_days),
            "observed_melt_rate": float(r.melt_rate),
            "modeled_melt_rate_bulk": np.nan, "ratio_bulk": np.nan,
            "modeled_melt_rate_voxel": np.nan, "ratio_voxel": np.nan,
            "mean_delta_t_bulk": np.nan, "mean_delta_t_voxel": np.nan,
            "mass_loss_basal_bulk": np.nan, "mass_loss_lateral_bulk": np.nan,
            "mass_loss_surface_bulk": np.nan, "mass_loss_wave_bulk": np.nan,
            "status": "OK",
        }
        if not daily.exists() or not static.exists() or not traj.exists():
            rec["status"] = "SKIP_NO_DATA"
            n_skip += 1
            rows.append(rec)
            continue

        for model in models:
            env = os.environ.copy()
            env["VOXEL_ENABLED"] = "true" if model == "voxel" else "false"
            env["ICEBERG_WAVE_EROSION"] = a.wave_enabled
            out = a.output_dir / f"{case}_{model}.nc"
            cmd = [
                str(binary), str(r.lat_i), str(r.lon_i),
                str(r.L0), str(r.W0), str(r.H0), str(r.duration_days),
                str(a.dt), str(out), str(daily), str(static), "", "",
                "--prescribed_trajectory", str(traj),
                "--epoch", str(int(r.epoch)),
                "--start-date", str(r.date_start).replace("-", ""),
            ]
            try:
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   env=env, timeout=a.timeout)
            except subprocess.TimeoutExpired:
                rec["status"] = f"TIMEOUT_{model}"
                continue
            if p.returncode != 0:
                print(f"FAIL {case} {model}: rc={p.returncode}\n{p.stderr[-400:]}", flush=True)
                rec["status"] = f"FAIL_{model}"
                continue
            s = parse_summary(p.stdout)
            if s is None:
                rec["status"] = f"NO_SUMMARY_{model}"
                continue
            submarine = (s["basal"] + s["lateral"] + s["wave"]) / RHO_ICE
            if s["mean_a_wet"] > 0 and s["seconds"] > 0:
                rate = submarine / (s["mean_a_wet"] * s["seconds"]) * 86400.0
            else:
                rate = np.nan
            rec[f"modeled_melt_rate_{model}"] = rate
            rec[f"ratio_{model}"] = rate / rec["observed_melt_rate"] if rec["observed_melt_rate"] > 0 else np.nan
            rec[f"mean_delta_t_{model}"] = s["mean_delta_t"]
            if model == "bulk":
                rec["mass_loss_basal_bulk"] = s["basal"]
                rec["mass_loss_lateral_bulk"] = s["lateral"]
                rec["mass_loss_surface_bulk"] = s["surface"]
                rec["mass_loss_wave_bulk"] = s["wave"]
        rows.append(rec)

    out_csv = a.output_dir / "enderlin23_hindcast_results.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    n_ok = sum(1 for r in rows if r["status"] == "OK")
    print(f"wrote {out_csv}: {n_ok}/{len(rows)} OK, {n_skip} skipped (no GLORYS site data)")
    if n_ok == 0:
        print("BLOCKED: no rows had GLORYS site files; see "
              "docs/validation/stage12.7a_enderlin23_hindcast.md", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
