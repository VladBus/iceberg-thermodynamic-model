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

DEFAULT_MANIFEST = "data/output/run_manifest_2020_Q1_HEAT_ON.json"
DEFAULT_OUT = "data/output/vertical_profiles.csv"


def load_manifest(manifest_path):
    """Load the run manifest (files + days), or fall back to legacy glob."""
    p = pathlib.Path(manifest_path)
    if p.exists():
        manifest = json.loads(p.read_text())
        files = [pathlib.Path(f["file"]) for f in manifest.get("files", [])]
        if files:
            return files
    # Legacy fallback (no manifest): exclude day_00 / final explicitly.
    import glob
    return [pathlib.Path(f) for f in sorted(
        glob.glob("data/output/results_day_[0-9][0-9].nc"))
        if not f.endswith("_00.nc")]


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
    parser.add_argument(
        "--manifest", default=DEFAULT_MANIFEST, help="Run manifest JSON (preferred)"
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output CSV path")
    args = parser.parse_args()

    files = load_manifest(args.manifest)
    if not files:
        print(f"ERROR: no files in {args.manifest} (or matching legacy glob). Run the Fortran model first.")
        return 1

    all_rows = []
    for f in files:
        all_rows.extend(daily_profile(f))

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["day", "depth_m"]).reset_index(drop=True)
    df.to_csv(args.out, index=False)

    print(
        f"Vertical profiles written to {args.out} ({len(df)} rows, {df['day'].nunique()} days)"
    )
    print("\nSample (day 1):")
    print(df[df["day"] == df["day"].min()].head(6).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
