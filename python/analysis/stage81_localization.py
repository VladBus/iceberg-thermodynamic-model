#!/usr/bin/env python3
"""Stage 8.1 Spatial Localization Analysis - Where does NaN first appear?"""

import xarray as xr
import numpy as np
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def analyze_nan_localization(run_dir):
    """Track where NaN first appears and how it propagates."""
    nc_dir = Path(run_dir) / "output" / "nc"

    # Load day 00 (initial) and day 01 (after 1 day)
    ds0 = xr.open_dataset(nc_dir / "results_day_00.nc")
    ds1 = xr.open_dataset(nc_dir / "results_day_01.nc")

    u0 = ds0["u_velocity"].values
    v0 = ds0["v_velocity"].values
    u1 = ds1["u_velocity"].values
    v1 = ds1["v_velocity"].values

    # Find cells that are valid on day 0 but NaN on day 1
    nan_new = (~np.isfinite(u1)) & np.isfinite(u0)
    nan_new_v = (~np.isfinite(v1)) & np.isfinite(v0)

    print(f"Cells becoming NaN (u): {nan_new.sum()}")
    print(f"Cells becoming NaN (v): {nan_new_v.sum()}")
    print(f"Total wet cells day 0: {np.isfinite(u0).sum()}")
    print(f"Total wet cells day 1: {np.isfinite(u1).sum()}")

    # Find locations of new NaN
    nan_locs = np.argwhere(nan_new)
    if len(nan_locs) > 0:
        print(f"\nFirst 20 cells becoming NaN (k, j, i):")
        for loc in nan_locs[:20]:
            k, j, i = loc
            print(f"  ({k}, {j}, {i}): u0={u0[k,j,i]:.6f}, v0={v0[k,j,i]:.6f}")

    # Check depth distribution
    if len(nan_locs) > 0:
        depths = nan_locs[:, 0]
        print(f"\nDepth distribution of new NaN (level index):")
        unique, counts = np.unique(depths, return_counts=True)
        for d, c in zip(unique, counts):
            print(f"  Level {d}: {c} cells")

    # Check horizontal distribution
    if len(nan_locs) > 0:
        print(f"\nHorizontal bounds of new NaN:")
        print(f"  i (x): {nan_locs[:, 2].min()} - {nan_locs[:, 2].max()}")
        print(f"  j (y): {nan_locs[:, 1].min()} - {nan_locs[:, 1].max()}")

    # Check if NaN appears near boundaries
    is1, js1 = 133, 105
    boundary_i = (nan_locs[:, 2] == 1) | (nan_locs[:, 2] == is1 - 2)  # i=1 or i=is-1
    boundary_j = (nan_locs[:, 1] == 1) | (nan_locs[:, 1] == js1 - 2)  # j=1 or j=js-1
    print(f"\nNew NaN at i-boundary: {boundary_i.sum()}")
    print(f"New NaN at j-boundary: {boundary_j.sum()}")

    # Check surviving cells (valid on both days)
    surviving = np.isfinite(u0) & np.isfinite(u1)
    surv_locs = np.argwhere(surviving)
    print(f"\nSurviving cells: {surviving.sum()}")
    if len(surv_locs) > 0:
        print(f"  i range: {surv_locs[:, 2].min()} - {surv_locs[:, 2].max()}")
        print(f"  j range: {surv_locs[:, 1].min()} - {surv_locs[:, 1].max()}")
        print(f"  k range: {surv_locs[:, 0].min()} - {surv_locs[:, 0].max()}")

    ds0.close()
    ds1.close()


def analyze_initial_density_gradients():
    """Analyze the initial density field for large gradients."""
    ds = xr.open_dataset(
        PROJ_ROOT / "data/input/processed/ocean/initial_ts_2020-01-01.nc"
    )
    ro = ds["density_anomaly_gcm3"].values  # g/cm3
    wet = ds["wet_mask"].values.astype(bool)

    print(f"\n=== Initial Density Field Analysis ===")
    print(f"Shape: {ro.shape}")
    print(f"Wet cells: {wet.sum()}")
    print(f"ro range: {np.nanmin(ro):.6f} - {np.nanmax(ro):.6f} g/cm3")

    # Compute horizontal gradients on wet cells
    # dρ/dx (along j, U-points)
    dro_dx = np.zeros_like(ro)
    dro_dy = np.zeros_like(ro)

    for k in range(ro.shape[2]):
        for j in range(1, ro.shape[1] - 1):
            for i in range(1, ro.shape[0] - 1):
                if wet[i, j]:
                    dro_dx[i, j, k] = ro[i, j + 1, k] - ro[i, j - 1, k]  # 2*dx
                    dro_dy[i, j, k] = ro[i + 1, j, k] - ro[i - 1, j, k]  # 2*dx

    # Scale by 1/(2*dx) where dx = 1389000 cm
    dx_cm = 1389000.0
    dro_dx = dro_dx / (2 * dx_cm)
    dro_dy = dro_dy / (2 * dx_cm)

    # Max gradients on wet cells
    wet_3d = np.repeat(wet[:, :, np.newaxis], ro.shape[2], axis=2)
    grad_mag = np.sqrt(dro_dx**2 + dro_dy**2)
    grad_mag_wet = grad_mag[wet_3d]

    print(f"Max |∇ρ|: {np.nanmax(grad_mag_wet):.2e} g/cm3/cm")
    print(f"Mean |∇ρ|: {np.nanmean(grad_mag_wet):.2e} g/cm3/cm")
    print(f"P99 |∇ρ|: {np.nanpercentile(grad_mag_wet, 99):.2e} g/cm3/cm")

    # Find locations of max gradient
    max_idx = np.nanargmax(grad_mag_wet)
    # Convert flat index to 3D
    flat_wet_idx = np.where(wet_3d.ravel())[0]
    idx_3d = np.unravel_index(flat_wet_idx[max_idx], ro.shape)
    print(f"Max gradient at (i={idx_3d[0]}, j={idx_3d[1]}, k={idx_3d[2]})")
    print(f"  dro/dx: {dro_dx[idx_3d]:.2e}")
    print(f"  dro/dy: {dro_dy[idx_3d]:.2e}")
    print(f"  ro: {ro[idx_3d]:.6f}")

    # Vertical gradients
    dro_dz = np.zeros_like(ro)
    for k in range(ro.shape[2] - 1):
        for j in range(ro.shape[1]):
            for i in range(ro.shape[0]):
                if wet[i, j] and k + 1 < ro.shape[2]:
                    dro_dz[i, j, k] = ro[i, j, k + 1] - ro[i, j, k]

    dz = (
        np.array(
            [
                250,
                500,
                1000,
                1500,
                2000,
                2500,
                3000,
                4000,
                5000,
                7500,
                10000,
                15000,
                20000,
                25000,
                30000,
                40000,
                50000,
                60000,
            ]
        )
        * 100
    )  # cm
    dro_dz_scaled = dro_dz / dz[:, np.newaxis, np.newaxis]  # g/cm3/cm
    dro_dz_wet = dro_dz_scaled[wet_3d]
    print(f"\nMax |∂ρ/∂z|: {np.nanmax(np.abs(dro_dz_wet)):.2e} g/cm3/cm")
    print(f"Mean |∂ρ/∂z|: {np.nanmean(np.abs(dro_dz_wet)):.2e} g/cm3/cm")

    ds.close()


def main():
    print("=" * 80)
    print("STAGE 8.1 SPATIAL LOCALIZATION ANALYSIS")
    print("=" * 80)

    # Analyze realistic_ref run
    print("\n--- realistic_ref run ---")
    analyze_nan_localization(PROJ_ROOT / "data" / "runs" / "stage81_forensic_3d")

    # Analyze reference_level run
    print("\n--- reference_level run ---")
    analyze_nan_localization(PROJ_ROOT / "data" / "runs" / "stage81_ref_zero")

    # Analyze initial density gradients
    analyze_initial_density_gradients()


if __name__ == "__main__":
    main()
