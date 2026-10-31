#!/usr/bin/env python3
"""Generate prescribed Enderlin23 trajectories for Stage 12.7a.

Reads the curated per-iceberg CSV, filters to the first-validation sample
(observation interval <= 120 days; expected 190 rows: WAP 125 + WAIS 65),
and writes one CSV per iceberg plus a manifest.

Trajectory CSV: ``time_s,lat,lon`` (linear interpolation between the observed
start/end positions; time relative to the start epoch).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path,
                   default=Path("data/validation/observations/enderlin23/enderlin23_per_iceberg.csv"))
    p.add_argument("--out-dir", type=Path,
                   default=Path("data/validation/trajectories/enderlin23"))
    p.add_argument("--manifest", type=Path,
                   default=Path("docs/validation/stage12.7a_trajectory_manifest.csv"))
    p.add_argument("--max-interval", type=float, default=120.0)
    return p.parse_args()


def main() -> int:
    a = args()
    df = pd.read_csv(a.csv)
    df["date_start"] = pd.to_datetime(df["date_start"].astype(str), format="%Y%m%d", errors="coerce")
    df["date_end"] = pd.to_datetime(df["date_end"].astype(str), format="%Y%m%d", errors="coerce")
    df["interval_days"] = (df["date_end"] - df["date_start"]).dt.total_seconds() / 86400.0
    if "time_separation_days" in df:
        duration = df["time_separation_days"].astype(float)
    else:
        duration = df["interval_days"]
    sub = df[df["interval_days"] <= a.max_interval].copy()
    sub["duration_days"] = duration[sub.index]
    sub = sub.dropna(subset=["lat_i", "lon_i", "lat_f", "lon_f", "surface_area",
                             "volume_i", "melt_rate", "duration_days"])
    if sub.empty:
        print("ERROR: no rows after filtering", flush=True)
        return 1

    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.manifest.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, r in sub.iterrows():
        duration_s = float(r.duration_days) * 86400.0
        # Daily samples plus the exact final time; lat/lon linear in time.
        n = max(int(np.ceil(duration_s / 86400.0)), 1)
        t = np.linspace(0.0, duration_s, n + 1)
        frac = t / duration_s if duration_s > 0 else np.zeros_like(t)
        lat = float(r.lat_i) + frac * (float(r.lat_f) - float(r.lat_i))
        lon = float(r.lon_i) + frac * (float(r.lon_f) - float(r.lon_i))
        fname = f"{r.case_id}.csv"
        path = a.out_dir / fname
        pd.DataFrame({"time_s": t, "lat": lat, "lon": lon}).to_csv(
            path, index=False, float_format="%.10f")
        area = float(r.surface_area)
        L0 = np.sqrt(area)
        h_va = float(r.volume_i) / area
        h_draft = float(r.draft) * 1025.0 / 916.7
        ratio = h_va / h_draft if h_draft > 0 else np.inf
        # 49/190 Enderlin rows (CG 2016/2018) have Volume_i inconsistent
        # with SurfaceArea_mean and MedianDraft_mean (H=V/A up to 53 km).
        # Use V/A only when it is physically compatible with the observed
        # draft; otherwise use the draft-derived thickness.
        if 0.5 <= ratio <= 2.0:
            H0 = h_va; rule = "V/A"
        else:
            H0 = h_draft; rule = "draft"
        epoch = int(pd.Timestamp(r.date_start).timestamp())
        rows.append({
            "case_id": r.case_id, "site": r.site, "region": r.region,
            "date_start": r.date_start.strftime("%Y-%m-%d"),
            "date_end": r.date_end.strftime("%Y-%m-%d"),
            "epoch": epoch, "duration_days": float(r.duration_days),
            "lat_i": float(r.lat_i), "lon_i": float(r.lon_i),
            "lat_f": float(r.lat_f), "lon_f": float(r.lon_f),
            "L0": L0, "W0": L0, "H0": H0, "H0_rule": rule, "H_V_over_A": h_va, "H_draft": h_draft,
            "volume_i": float(r.volume_i), "surface_area": area,
            "submerged_area": float(r.submerged_area), "melt_rate": float(r.melt_rate),
            "draft": float(r.draft), "trajectory": str(path),
        })
    man = pd.DataFrame(rows)
    man.to_csv(a.manifest, index=False)
    print(f"wrote {len(man)} trajectories to {a.out_dir}")
    print(f"manifest: {a.manifest}")
    print(man.groupby("region").size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
