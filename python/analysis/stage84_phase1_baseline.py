#!/usr/bin/env python3
"""
Stage 8.4 Phase 1: Forensic baseline - reproduce the 13.2 m/s spike
and capture the exact temporal sequence.
"""

import subprocess
import os
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def run_baseline_diagnostic():
    """Run the baseline configuration and capture first-step diagnostics."""
    env = os.environ.copy()
    env.update(
        {
            "ICEBERG_OCEAN_VELOCITY_INIT": "realistic_ref",
            "ICEBERG_OCEAN_U_REF": "0.05",
            "ICEBERG_OCEAN_V_REF": "0.02",
        }
    )

    cmd = ["fpm", "run", "--flag", "-I/usr/include", "--", "stage84_phase1_baseline"]

    print("Running baseline diagnostic...")
    result = subprocess.run(
        cmd, cwd=PROJ_ROOT, env=env, capture_output=True, text=True, timeout=300
    )
    return result


def run_zero_atmos_pressure():
    """Run with zero atmospheric pressure gradient to test if dpx/dpy cause the spike."""
    # We need to modify the model or input to zero out dpx/dpy
    # For now, just run baseline and we'll analyze the output
    pass


def main():
    print("=" * 80)
    print("STAGE 8.4 PHASE 1: FORENSIC BASELINE REPRODUCTION")
    print("=" * 80)

    # Check git status
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJ_ROOT, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    print(f"Commit: {commit}")

    result = subprocess.run(
        ["git", "status"], cwd=PROJ_ROOT, capture_output=True, text=True
    )
    print(f"Git status:\n{result.stdout}")

    # Run baseline
    result = run_baseline_diagnostic()

    print("Return code:", result.returncode)
    if result.returncode != 0:
        print("STDOUT (last 200 lines):")
        print("\n".join(result.stdout.split("\n")[-200:]))
        print("STDERR (last 100 lines):")
        print("\n".join(result.stderr.split("\n")[-100:]))

    # Save output
    with open(
        PROJ_ROOT
        / "data"
        / "output"
        / "diagnostics"
        / "stage8.4"
        / "phase1_baseline_stdout.txt",
        "w",
    ) as f:
        f.write(result.stdout)
    with open(
        PROJ_ROOT
        / "data"
        / "output"
        / "diagnostics"
        / "stage8.4"
        / "phase1_baseline_stderr.txt",
        "w",
    ) as f:
        f.write(result.stderr)


if __name__ == "__main__":
    main()
