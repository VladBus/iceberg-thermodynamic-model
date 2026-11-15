#!/usr/bin/env python3
"""Stage 12.20 A1: connectivity / detached-mass scan for saved snapshots."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from scipy.ndimage import label, generate_binary_structure

RHO_ICE = 916.7
STRUCT = generate_binary_structure(3, 1)
RUNS50 = {
    "FJL1_2020": "data/validation/stage12.19/FJL1_2020_fixed_N6",
    "FJL2_2020": "data/validation/stage12.19/FJL2_2020_fixed_N6",
    "FJL2_2024": "data/validation/stage12.19/FJL2_2024_fixed_N6",
}
RUNS100 = {
    "FJL_A": "data/validation/stage12.19/stage4/final/FJL_A",
    "NZ_A": "data/validation/stage12.19/stage4/final/NZ_A",
    "NZ_B": "data/validation/stage12.19/stage4/final/NZ_B",
    "Barents_1": "data/validation/stage12.19/stage4/final/D2",
    "Barents_2": "data/validation/stage12.19/stage4/final/D4",
    "Barents_3": "data/validation/stage12.19/stage4/final/D5",
}
THRESHOLDS = (0.01, 0.1, 0.3, 0.5)


def one(phi, threshold, dx, dy, dz):
    solid = np.asarray(phi, float) >= threshold
    lab, n = label(solid, structure=STRUCT)
    if n == 0:
        return 0, 0.0, 0.0
    counts = np.bincount(lab.ravel())
    counts[0] = 0
    main = int(counts.argmax())
    mass_cell = RHO_ICE * dx * dy * dz
    total = float(np.asarray(phi, float)[solid].sum() * mass_cell)
    detached = float(np.asarray(phi, float)[solid & (lab != main)].sum() * mass_cell)
    return int(n), detached, total


def scan_series(run_dir, thresholds=THRESHOLDS):
    files = sorted(Path(run_dir).glob("run.nc_snap_*.nc"))
    rows = []
    if not files:
        return rows
    for f in files:
        with xr.open_dataset(f) as ds:
            phi = ds.phi.values
            day = float(ds.time.values[0] / 86400.0) if "time" in ds else float(f.stem.split("_")[-1])
            x = ds.x.values; y = ds.y.values; z = ds.z.values
        dx = float(x[1] - x[0]); dy = float(y[1] - y[0]); dz = float(z[1] - z[0])
        for th in thresholds:
            n, det, total = one(phi, th, dx, dy, dz)
            rows.append({"run": Path(run_dir).name, "day": day, "phi_conn": th,
                         "n_components": n, "detached_mass_kg": det,
                         "total_mass_kg": total,
                         "detached_fraction": det / total if total else np.nan})
    return rows


def scan_100(run_dir, thresholds=THRESHOLDS):
    p = Path(run_dir) / "run.nc_voxel.nc"
    if not p.exists():
        return []
    rows = []
    with xr.open_dataset(p) as ds:
        times = ds.time.values / 86400.0
        phi = ds.phi.values
        x = ds.x.values; y = ds.y.values; z = ds.z.values
        dx = float(x[1] - x[0]); dy = float(y[1] - y[0]); dz = float(z[1] - z[0])
        for k, day in enumerate(times):
            for th in thresholds:
                n, det, total = one(phi[k], th, dx, dy, dz)
                rows.append({"run": Path(run_dir).name, "day": float(day), "phi_conn": th,
                             "n_components": n, "detached_mass_kg": det,
                             "total_mass_kg": total,
                             "detached_fraction": det / total if total else np.nan})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/validation/stage12.20/connectivity_scan.csv"))
    a = p.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, root in RUNS50.items():
        for r in scan_series(root):
            r["run"] = tag; r["grid"] = "50^3"; rows.append(r)
    for tag, root in RUNS100.items():
        for r in scan_100(root):
            r["run"] = tag; r["grid"] = "100^3"; rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(a.out, index=False)
    # output one summary row per run/threshold
    g = df.groupby(["run", "grid", "phi_conn"]).agg(
        first_day=("day", "min"),
        last_day=("day", "max"),
        max_components=("n_components", "max"),
        last_components=("n_components", "last"),
        max_detached_kg=("detached_mass_kg", "max"),
        max_detached_fraction=("detached_fraction", "max"),
    ).reset_index()
    first = (df[df.detached_mass_kg > 0]
             .groupby(["run", "grid", "phi_conn"]).day.min()
             .rename("first_detached_day").reset_index())
    g = g.merge(first, on=["run", "grid", "phi_conn"], how="left")
    print(g.to_string(index=False))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
