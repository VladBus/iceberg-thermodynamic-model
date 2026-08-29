#!/usr/bin/env python3
"""Stage 8.1 Forensic Diagnostics - High-frequency analysis of model state evolution.

This script runs the model with modified output frequency to capture
the detailed evolution of velocity, energy, and instability.
"""

import subprocess
import os
import json
import numpy as np
import xarray as xr
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def run_model_with_debug(run_id, max_days=3, output_interval=1):
    """Run model with high-frequency diagnostic output."""
    env = os.environ.copy()
    env.update(
        {
            "ICEBERG_OCEAN_VELOCITY_INIT": "realistic_ref",
            "ICEBERG_OCEAN_U_REF": "0.05",
            "ICEBERG_OCEAN_V_REF": "0.02",
        }
    )

    # We'll need to modify the model to output more frequently
    # For now, run standard model and parse daily diagnostics
    cmd = ["fpm", "run", "--flag", "-I/usr/include", "--", run_id]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=PROJ_ROOT, env=env, capture_output=True, text=True, timeout=7200
    )
    return result


def analyze_netcdf_series(run_dir, max_day=10):
    """Analyze the NetCDF time series for velocity evolution."""
    nc_dir = Path(run_dir) / "output" / "nc"

    results = {
        "days": [],
        "u_max": [],
        "u_mean": [],
        "u_nan_frac": [],
        "v_max": [],
        "v_mean": [],
        "v_nan_frac": [],
        "speed_max": [],
        "speed_mean": [],
        "ke": [],
        "ssh_max": [],
        "ssh_min": [],
    }

    for day in range(max_day + 1):
        fname = nc_dir / f"results_day_{day:02d}.nc"
        if not fname.exists():
            break

        ds = xr.open_dataset(fname)
        u = ds["u_velocity"].values  # m/s
        v = ds["v_velocity"].values

        # Mask land (NaN)
        u_finite = np.isfinite(u)
        v_finite = np.isfinite(v)

        if u_finite.any():
            results["u_max"].append(float(np.nanmax(u)))
            results["u_mean"].append(float(np.nanmean(u)))
            results["u_nan_frac"].append(float(1 - u_finite.mean()))
        else:
            results["u_max"].append(np.nan)
            results["u_mean"].append(np.nan)
            results["u_nan_frac"].append(1.0)

        if v_finite.any():
            results["v_max"].append(float(np.nanmax(v)))
            results["v_mean"].append(float(np.nanmean(v)))
            results["v_nan_frac"].append(float(1 - v_finite.mean()))
        else:
            results["v_max"].append(np.nan)
            results["v_mean"].append(np.nan)
            results["v_nan_frac"].append(1.0)

        speed = np.sqrt(u**2 + v**2)
        if np.isfinite(speed).any():
            results["speed_max"].append(float(np.nanmax(speed)))
            results["speed_mean"].append(float(np.nanmean(speed)))
        else:
            results["speed_max"].append(np.nan)
            results["speed_mean"].append(np.nan)

        # SSH
        if "ssh" in ds:
            ssh = ds["ssh"].values
            results["ssh_max"].append(float(np.nanmax(ssh)))
            results["ssh_min"].append(float(np.nanmin(ssh)))
        else:
            results["ssh_max"].append(np.nan)
            results["ssh_min"].append(np.nan)

        results["days"].append(day)
        ds.close()

    return results


def parse_daily_diagnostics(run_dir):
    """Parse the daily_diagnostics.csv file."""
    import pandas as pd

    csv_path = Path(run_dir) / "output" / "csv" / "daily_diagnostics.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df
    return None


def analyze_convective_adjustment(run_dir):
    """Analyze convective adjustment statistics."""
    import pandas as pd

    csv_path = Path(run_dir) / "output" / "csv" / "daily_diagnostics.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return {
            "ca_nmix": df["ca_nmix"].tolist(),
            "ca_max_iter": df["ca_max_iter"].tolist(),
            "ca_guard_hits": df["ca_guard_hits"].tolist(),
            "ca_affected_cols": df["ca_affected_cols"].tolist(),
        }
    return None


def main():
    print("=" * 80)
    print("STAGE 8.1 FORENSIC DIAGNOSTICS - Baseline Run")
    print("=" * 80)

    # Check current commit
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJ_ROOT, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    print(f"Commit: {commit}")

    # Run 3-day baseline with current configuration
    run_id = "stage81_forensic_3d"
    print(f"\n--- Running {run_id} ---")
    result = run_model_with_debug(run_id, max_days=3)

    if result.returncode != 0:
        print("ERROR: Run failed!")
        print("STDOUT:", result.stdout[-3000:])
        print("STDERR:", result.stderr[-3000:])
        return

    print("Run completed successfully")

    # Analyze results
    run_dir = PROJ_ROOT / "data" / "runs" / run_id

    print("\n--- NetCDF Time Series Analysis ---")
    nc_results = analyze_netcdf_series(run_dir, max_day=3)
    for key, val in nc_results.items():
        if key != "days":
            print(f"  {key}: {val}")

    # Save NetCDF analysis
    out_file = (
        PROJ_ROOT
        / "data"
        / "output"
        / "diagnostics"
        / "stage8.1"
        / "netcdf_timeseries.json"
    )
    with open(out_file, "w") as f:
        json.dump(nc_results, f, indent=2)
    print(f"Saved: {out_file}")

    print("\n--- Daily Diagnostics ---")
    df = parse_daily_diagnostics(run_dir)
    if df is not None:
        print(df.to_string())
        df.to_json(
            PROJ_ROOT
            / "data"
            / "output"
            / "diagnostics"
            / "stage8.1"
            / "daily_diagnostics.json",
            orient="records",
        )

    print("\n--- Convective Adjustment ---")
    ca = analyze_convective_adjustment(run_dir)
    if ca:
        for key, val in ca.items():
            print(f"  {key}: {val}")
        with open(
            PROJ_ROOT
            / "data"
            / "output"
            / "diagnostics"
            / "stage8.1"
            / "convective_adjustment.json",
            "w",
        ) as f:
            json.dump(ca, f, indent=2)

    print("\nForensic diagnostics complete!")


if __name__ == "__main__":
    main()
