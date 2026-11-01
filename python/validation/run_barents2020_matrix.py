#!/usr/bin/env python3
"""Stage 12.8 Barents 2020 matrix runner (voxel).

4 sizes x 2 seasons x 3 start points = 24 runs, 365 days, dt=3600.
Uses the monthly-mean GLORYS fallback (2020-01..2021-06) because daily CMEMS
access is blocked; constant atmosphere (full-year ERA5 unavailable).  The
manifest records this explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import pandas as pd

SIZES = [50, 100, 200, 500]
SEASONS = {"Jan": ("20200101", 1577836800), "Jul": ("20200701", 1593561600)}


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("data/runs/barents2020"))
    p.add_argument("--glorys", type=Path,
                   default=Path("data/input/raw/reanalysis/glorys12/2020/"
                                "glorys12_barents_2020_2021_monthly.nc"))
    p.add_argument("--static", type=Path,
                   default=Path("data/input/raw/reanalysis/glorys12/2020/"
                                "glorys12_barents_2020_2021_static.nc"))
    p.add_argument("--start-points", type=Path,
                   default=Path("docs/validation/stage12.8_start_points.json"))
    p.add_argument("--iceberg-run", type=Path, default=None)
    p.add_argument("--days", type=float, default=365.0)
    p.add_argument("--dt", type=float, default=3600.0)
    p.add_argument("--max-runs", type=int, default=0)
    p.add_argument("--timeout", type=int, default=900)
    return p.parse_args()


def find_binary(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    cands = sorted(Path("build").glob("*/app/iceberg_run"), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise SystemExit("iceberg_run not found; build first")
    return cands[-1]


def parse_summary(stdout: str) -> dict | None:
    for line in stdout.splitlines():
        if line.startswith("HINDCAST_SUMMARY"):
            v = [float(x) for x in line.split()[1:]]
            if len(v) >= 10:
                return {"final_volume": v[0], "initial_volume": v[1],
                        "basal": v[2], "lateral": v[3], "surface": v[4],
                        "vapor": v[5], "wave": v[6], "mean_a_wet": v[7],
                        "seconds": v[8], "mass": v[9],
                        "mean_delta_t": v[10] if len(v) > 10 else float("nan")}
    return None


def main() -> int:
    a = args()
    pts = json.loads(a.start_points.read_text())["points"]
    binary = find_binary(a.iceberg_run)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for size in SIZES:
        for season, (date, epoch) in SEASONS.items():
            for pi, pt in enumerate(pts, start=1):
                rid = f"S{size}_{season}_P{pi}"
                out = a.out_dir / f"{rid}.nc"
                runs.append((rid, size, season, pi, pt, date, epoch, out))
    if a.max_runs:
        runs = runs[:a.max_runs]

    rows = []
    for n, (rid, size, season, pi, pt, date, epoch, out) in enumerate(runs, start=1):
        print(f"[{n}/{len(runs)}] {rid} ({pt['lat']:.2f}N {pt['lon']:.2f}E)", flush=True)
        env = os.environ.copy()
        env.update(VOXEL_ENABLED="true", VOXEL_KT_SCALE="1",
                   ICEBERG_WAVE_EROSION="false")
        cmd = [str(binary), str(pt["lat"]), str(pt["lon"]),
               str(size), str(size), str(size), str(a.days), str(a.dt), str(out),
               str(a.glorys), str(a.static), "", "",
               "--start-date", date, "--epoch", str(epoch)]
        t0 = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                               timeout=a.timeout)
            rc = p.returncode
            stdout = p.stdout
            err = p.stderr[-500:]
        except subprocess.TimeoutExpired:
            rc = 124; stdout = ""; err = "timeout"
        s = parse_summary(stdout) if rc == 0 else None
        rows.append({
            "run_id": rid, "size_m": size, "season": season, "point": pi,
            "lat0": pt["lat"], "lon0": pt["lon"], "depth0_m": pt["depth_m"],
            "start_date": date, "days": a.days, "rc": rc,
            "status": "OK" if s else ("TIMEOUT" if rc == 124 else "FAIL"),
            "wall_s": round(time.time() - t0, 1),
            "final_volume": s["final_volume"] if s else float("nan"),
            "initial_volume": s["initial_volume"] if s else float("nan"),
            "basal_mass_loss": s["basal"] if s else float("nan"),
            "lateral_mass_loss": s["lateral"] if s else float("nan"),
            "surface_mass_loss": s["surface"] if s else float("nan"),
            "wave_mass_loss": s["wave"] if s else float("nan"),
            "mean_delta_t": s["mean_delta_t"] if s else float("nan"),
            "error": err if rc != 0 else "",
        })
        if rc != 0:
            print(f"  FAIL rc={rc}: {err}", flush=True)
        else:
            print(f"  OK V={s['final_volume']:.3e} / {s['initial_volume']:.3e} m3", flush=True)

    man = a.out_dir / "matrix_manifest.csv"
    pd.DataFrame(rows).to_csv(man, index=False)
    print(f"wrote {man}: {sum(r['status']=='OK' for r in rows)}/{len(rows)} OK")
    return 0 if all(r["status"] == "OK" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
