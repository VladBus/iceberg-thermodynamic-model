#!/usr/bin/env python3
"""Export iceberg_run time series and voxel snapshots to CSV.

Usage: python python/analysis/export_voxel_csv.py RUN.nc VOXEL.nc --outdir DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_nc")
    parser.add_argument("voxel_nc")
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    run = xr.open_dataset(args.run_nc)
    vox = xr.open_dataset(args.voxel_nc)
    try:
        run.to_dataframe().to_csv(out / "time_series.csv")
        rows = []
        for s in range(vox.sizes["snapshot"]):
            phi = np.asarray(vox.phi.isel(snapshot=s).values, dtype=float)
            T = np.asarray(vox.T.isel(snapshot=s).values, dtype=float)
            active = phi > 0.01
            rows.append({
                "snapshot": s,
                "time_s": float(vox.time.isel(snapshot=s)),
                "mass_kg": float(vox.mass.isel(snapshot=s)),
                "draft_m": float(vox.draft.isel(snapshot=s)),
                "active_voxels": int(active.sum()),
                "phi_sum": float(phi.sum()),
                "T_min_C": float(np.min(T[active])) if active.any() else np.nan,
                "T_max_C": float(np.max(T[active])) if active.any() else np.nan,
                "T_mean_C": float(np.mean(T[active])) if active.any() else np.nan,
            })
        pd.DataFrame(rows).to_csv(out / "snapshots.csv", index=False)
    finally:
        run.close()
        vox.close()
    print(f"wrote CSV diagnostics to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
