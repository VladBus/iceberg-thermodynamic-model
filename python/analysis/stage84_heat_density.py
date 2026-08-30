#!/usr/bin/env python3
"""
Stage 8.4 Phase 2: Heat density change analysis.
Capture T, S, RO before and after heat() on first step.
"""

import xarray as xr
import numpy as np
import subprocess
import os
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def run_first_step_diagnostic():
    """
    Run the model for just the first baroclinic step with detailed diagnostics.
    We'll need to modify the model to output intermediate states.
    For now, let's analyze the existing output.
    """
    # Check multiple runs
    runs = ["stage84_short", "stage84_phase1_baseline"]

    for run in runs:
        nc_dir = PROJ_ROOT / "data" / "runs" / run / "output" / "nc"
        ds0_path = nc_dir / "results_day_00.nc"
        ds1_path = nc_dir / "results_day_01.nc"

        if not ds0_path.exists() or not ds1_path.exists():
            print(f"Run {run}: missing output files")
            continue

        ds0 = xr.open_dataset(ds0_path)
        ds1 = xr.open_dataset(ds1_path)

        # Temperature (K)
        T0 = ds0["temperature"].values
        T1 = ds1["temperature"].values

        # Salinity (mass fraction)
        S0 = ds0["salinity_mass_fraction"].values
        S1 = ds1["salinity_mass_fraction"].values

        # Density anomaly (kg/m3)
        RO0 = ds0["density_anomaly"].values
        RO1 = ds1["density_anomaly"].values

        # Wet mask - water_column_levels is (js1, is1) = (105, 133)
        # Data arrays in NetCDF are (depth, y, x) = (18, 105, 133) = (ks, js1, is1)
        kt1 = ds0["water_column_levels"].values  # (js1, is1) = (105, 133)
        wet_2d = kt1 > 0  # (js1, is1) = (105, 133)
        wet_3d = np.broadcast_to(wet_2d[None, :, :], (18, 105, 133))  # (ks, js1, is1)

        print(f"\n=== Run: {run} ===")
        print(f"Wet cells: {wet_2d.sum()}")

        # Print changes
        for var_name, v0, v1 in [
            ("T (K)", T0, T1),
            ("S", S0, S1),
            ("RO (kg/m3)", RO0, RO1),
        ]:
            diff = v1 - v0
            finite = np.isfinite(diff)
            if finite.any():
                print(f"\n{var_name}:")
                print(f"  min diff: {np.nanmin(diff):.6f}")
                print(f"  max diff: {np.nanmax(diff):.6f}")
                print(f"  mean diff: {np.nanmean(diff):.6f}")
                print(f"  RMS diff: {np.sqrt(np.nanmean(diff**2)):.6f}")
                print(f"  P99 abs diff: {np.nanpercentile(np.abs(diff), 99):.6f}")

        # Check if RO is actually being updated
        ro_same = np.allclose(RO0[wet_3d], RO1[wet_3d], equal_nan=True)
        print(f"\nRO identical (Day 0 vs Day 1): {ro_same}")

        if not ro_same:
            diff_ro = RO1 - RO0
            finite_ro = np.isfinite(diff_ro) & wet_3d
            if finite_ro.any():
                print(
                    f"RO diff stats: min={np.nanmin(diff_ro):.6f}, max={np.nanmax(diff_ro):.6f}, mean={np.nanmean(diff_ro):.6f}"
                )

        # Check T2/S2 vs T1/S1 if available
        ds0.close()
        ds1.close()


def check_ro_in_conv_adj():
    """Check if RO is updated in convective adjustment."""
    print("\n=== Checking RO update mechanism ===")
    print("RO is updated in convective_adjustment.f90 line 251:")
    print("  ro(i, j, k) = density_anomaly(ct(k), cs(k))")
    print("This is called AFTER advection, during convective adjustment.")
    print()
    print("Sequence on first step:")
    print("  1. Initialization: eos_diag() -> RO from initial T2/S2")
    print("  2. Thermal-wind init: U2/V2 balanced with this RO")
    print("  3. Day 1, III=1:")
    print("     a. heat() -> modifies T1/S1 (surface fluxes, ice melt)")
    print("     b. advs/advt -> advect T2/S2 using U2/V2 (thermal-wind balanced)")
    print("     c. conv_adj -> mixes T2/S2, updates RO from new T2/S2")
    print("     d. Block 200 -> uses NEW RO with OLD U2/V2 (imbalance!)")


if __name__ == "__main__":
    run_first_step_diagnostic()
    check_ro_in_conv_adj()
