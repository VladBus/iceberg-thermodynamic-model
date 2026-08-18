"""Compute vertical profiles from daily 3D model snapshots.

Reads
-----
- ``data/output/results_day_XX.nc`` NetCDF daily snapshots (written by the
  Fortran model via write_nc). Spatial averaging is done over the model
  wet columns (masked by ``water_column_levels`` / kt1) for each depth
  level - this is pure aggregation, no physics.

Produces
--------
- ``vertical_profiles.csv`` - one row per (day, depth) with the horizontally
  averaged T, S, U, V, W and RO. RO is read from the model output
  (the model computes EOS; Python does NOT recompute density).
"""

import argparse
import json
import pathlib

import numpy as np
import pandas as pd
import xarray as xr

from units import temperature_k_to_c, velocity_mps_to_cmps, density_anomaly_kgm3_to_gcm3
from run_context import resolve_run, add_run_args

DEFAULT_OUT = "vertical_profiles.csv"


def load_manifest(manifest_path):
    """Load the run manifest (files + days)."""
    p = pathlib.Path(manifest_path)
    if not p.exists():
        raise FileNotFoundError(f"manifest not found: {p}")
    manifest = json.loads(p.read_text())
    files = [pathlib.Path(f["file"]) for f in manifest.get("files", [])]
    if not files:
        raise ValueError(f"manifest has no files: {p}")
    return files


def daily_profile(path):
    """Horizontally averaged vertical profiles for one daily snapshot."""
    p = pathlib.Path(path)
    ds = xr.open_dataset(p)
    nlev = ds.sizes["depth"]
    kt1 = ds["water_column_levels"].values  # (x, y)

    # RO/density anomaly variable (added by the model in Stage 4.2); if absent, NaN.
    has_ro = "density_anomaly" in ds.data_vars

    depths = ds["depth"].values  # m
    rows = []
    for k in range(nlev):
        mask = kt1 > k  # level k active (0-based)
        if not mask.any():
            continue
        row = {
            "day": int(p.stem.split("_")[2]),
            "depth_m": float(depths[k]),
            "t": float(temperature_k_to_c(ds["temperature"].isel(depth=k).values[mask]).mean()),
            "s": float(ds["salinity_mass_fraction"].isel(depth=k).values[mask].mean()),
            "u": float(velocity_mps_to_cmps(ds["u_velocity"].isel(depth=k).values[mask]).mean()),
            "v": float(velocity_mps_to_cmps(ds["v_velocity"].isel(depth=k).values[mask]).mean()),
        }
        # W uses depth_w dimension (ks1 = ks + 1); keep it only if present.
        if "w_velocity" in ds.data_vars and k < ds.sizes["depth_w"]:
            row["w"] = float(velocity_mps_to_cmps(ds["w_velocity"].isel(depth_w=k).values[mask]).mean())
        if has_ro:
            row["ro"] = float(density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].isel(depth=k).values[mask]).mean())
        rows.append(row)
    ds.close()
    return rows


def main():
    """Compute horizontal-mean vertical profiles and write the CSV."""
    parser = argparse.ArgumentParser(
        description="Compute horizontal-mean vertical profiles from daily snapshots."
    )
    add_run_args(parser, default_run_id="2020_Q1_test_heat_on")
    parser.add_argument("--out", default=None, help="Output CSV path (default: run csv dir)")
    args = parser.parse_args()

    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
        files = load_manifest(ctx.manifest)
    except Exception as e:
        print(f"ERROR: Failed to resolve run/manifest: {e}")
        return 1

    out = pathlib.Path(args.out) if args.out else ctx.csv_dir / DEFAULT_OUT

    all_rows = []
    for f in files:
        all_rows.extend(daily_profile(f))

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["day", "depth_m"]).reset_index(drop=True)
    df.to_csv(out, index=False)

    print(
        f"Vertical profiles written to {out} ({len(df)} rows, {df['day'].nunique()} days)"
    )
    print("\nSample (day 1):")
    print(df[df["day"] == df["day"].min()].head(6).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
