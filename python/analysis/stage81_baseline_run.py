#!/usr/bin/env python3
"""Stage 8.1 Baseline reproduction and high-frequency diagnostics.

Reproduces the Stage 8.0 successful configuration:
- Bilinear EN4 interpolation
- realistic_ref mode (u_ref=0.05, v_ref=0.02 m/s at 600m)
- Dynamic height SSH initialization
- Factor 1 geostrophic balance

Runs 3-day and 10-day simulations with high-frequency output.
"""

import subprocess
import json
import os
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def run_model(run_id, days=3, extra_env=None):
    """Run the model with specified configuration."""
    env = os.environ.copy()
    env.update(
        {
            "ICEBERG_OCEAN_VELOCITY_INIT": "realistic_ref",
            "ICEBERG_OCEAN_U_REF": "0.05",
            "ICEBERG_OCEAN_V_REF": "0.02",
        }
    )
    if extra_env:
        env.update(extra_env)

    # Build the run command
    cmd = ["fpm", "run", "--flag", "-I/usr/include", "--", run_id]

    print(f"Running: {' '.join(cmd)}")
    print(f"Env: ICEBERG_OCEAN_VELOCITY_INIT={env['ICEBERG_OCEAN_VELOCITY_INIT']}")
    print(f"Env: ICEBERG_OCEAN_U_REF={env['ICEBERG_OCEAN_U_REF']}")
    print(f"Env: ICEBERG_OCEAN_V_REF={env['ICEBERG_OCEAN_V_REF']}")

    result = subprocess.run(
        cmd, cwd=PROJ_ROOT, env=env, capture_output=True, text=True, timeout=7200
    )
    return result


def parse_daily_diagnostics(run_dir):
    """Parse the daily_diagnostics.csv file."""
    import pandas as pd

    csv_path = Path(run_dir) / "output" / "csv" / "daily_diagnostics.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df
    return None


def main():
    print("=" * 80)
    print("STAGE 8.1 BASELINE REPRODUCTION")
    print("=" * 80)

    # Check current commit
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJ_ROOT, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    print(f"Commit: {commit}")

    # Run 3-day baseline
    print("\n--- 3-Day Baseline Run ---")
    run_id = "stage81_baseline_3d"
    result = run_model(run_id, days=3)

    if result.returncode != 0:
        print("ERROR: 3-day run failed!")
        print("STDOUT:", result.stdout[-5000:])
        print("STDERR:", result.stderr[-5000:])
        return

    print("3-day run completed successfully")

    # Parse diagnostics
    run_dir = PROJ_ROOT / "data" / "runs" / run_id
    df = parse_daily_diagnostics(run_dir)
    if df is not None:
        print("\nDaily Diagnostics:")
        print(df.to_string())
        df.to_json(
            PROJ_ROOT
            / "data"
            / "output"
            / "diagnostics"
            / "stage8.1"
            / "baseline_3d_diagnostics.json",
            orient="records",
        )

    # Run 10-day baseline
    print("\n--- 10-Day Baseline Run ---")
    run_id_10 = "stage81_baseline_10d"
    env_10 = {"mm1": "91"}  # Override mm1 for 10 days? Actually mm1=91 is Q1
    result = run_model(run_id_10, days=10)

    if result.returncode != 0:
        print("ERROR: 10-day run failed!")
        print("STDOUT:", result.stdout[-5000:])
        print("STDERR:", result.stderr[-5000:])
    else:
        print("10-day run completed successfully")
        df10 = parse_daily_diagnostics(PROJ_ROOT / "data" / "runs" / run_id_10)
        if df10 is not None:
            print("\n10-Day Diagnostics:")
            print(df10.to_string())
            df10.to_json(
                PROJ_ROOT
                / "data"
                / "output"
                / "diagnostics"
                / "stage8.1"
                / "baseline_10d_diagnostics.json",
                orient="records",
            )

    print("\nBaseline reproduction complete!")


if __name__ == "__main__":
    main()
