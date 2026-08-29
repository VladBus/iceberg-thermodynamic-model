#!/usr/bin/env python
"""
Stage 7.9 PHASE 4 — EN4 Interpolation Sensitivity Analysis

Tests how the 1° EN4 data interpolation onto the 13.89 km model grid
affects the density gradients and the diagnosed thermal-wind velocity.

Methods:
1. Nearest-neighbour (current default in initial_ocean_reader.f90)
2. Bilinear
3. Gaussian-smoothed bilinear (sigma=2, 5 grid points)
4. Conservative/area-weighted (if feasible)

The goal is to quantify how much the "geostrophic velocity" depends on
interpolation artifacts vs. true physical signal.
"""

import numpy as np
import xarray as xr
import json
from pathlib import Path
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator

# Model parameters
IS = 132
JS = 104
IS1 = IS + 1
JS1 = JS + 1
KS = 18
DX_CM = 1389000.0
DX_M = DX_CM / 100.0
G_M = 9.81
RHO0_SI = 1025.0
OMEGA = 7.29e-5

Z_M = np.array(
    [
        2.5,
        5.0,
        7.5,
        12.5,
        17.5,
        25.0,
        40.0,
        50.0,
        62.5,
        75.0,
        100.0,
        125.0,
        175.0,
        225.0,
        275.0,
        350.0,
        450.0,
        550.0,
    ]
)

DZ_M = np.zeros(18)
DZ_M[0] = Z_M[0]
for k in range(1, 18):
    DZ_M[k] = Z_M[k] - Z_M[k - 1]


def eckart_density_anomaly(T, S):
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_native():
    """Load raw EN4 data at native 1° resolution"""
    # The EN4 file should exist at this path
    ds = xr.open_dataset("data/input/raw/en4/en4.2.2.g10.202001.nc")
    # Variables: temperature, salinity, depth, lat, lon
    return ds


def load_model_grid():
    """Load model grid (lat/lon at T-points) from EN4 product"""
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    lat = ds["lat"].values
    lon = ds["lon"].values
    kt1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    return lat, lon, kt1, wet


def interpolate_en4_to_model(en4_ds, var_name, method="nearest"):
    """
    Interpolate EN4 variable to model grid using RegularGridInterpolator
    to avoid memory explosion from cross-product.
    """
    model_lat, model_lon, kt1, wet = load_model_grid()

    # Get EN4 coordinates
    en4_lat = en4_ds.lat.values
    en4_lon = en4_ds.lon.values
    en4_depth = en4_ds.depth.values  # 42 levels

    # Get EN4 data for January 2020 (first time step)
    en4_var = en4_ds[var_name].isel(time=0).values  # (depth, lat, lon)

    # Create interpolators for each depth level
    model_data_3d = np.zeros((18, 133, 105))  # (z, i, j)

    # Model grid
    model_lat_2d = model_lat  # (133, 105)
    model_lon_2d = model_lon  # (133, 105)

    # For each depth level, create 2D interpolator
    interp_all_depths = np.zeros((len(en4_depth), 133, 105))
    for d in range(len(en4_depth)):
        en4_slice = en4_ds[var_name].isel(time=0, depth=d).values  # (173, 360)

        # Create 2D interpolator
        if method == "nearest":
            interp_2d = RegularGridInterpolator(
                (en4_lat, en4_lon),
                en4_slice,
                method="nearest",
                bounds_error=False,
                fill_value=np.nan,
            )
        elif method in ("bilinear", "gaussian_sigma2", "gaussian_sigma5"):
            interp_2d = RegularGridInterpolator(
                (en4_lat, en4_lon),
                en4_slice,
                method="linear",
                bounds_error=False,
                fill_value=np.nan,
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        # Evaluate on model grid (vectorized)
        points = np.column_stack([model_lat_2d.ravel(), model_lon_2d.ravel()])
        interp_values = interp_2d(points).reshape(133, 105)

        if method in ("gaussian_sigma2", "gaussian_sigma5"):
            sigma = 2 if method == "gaussian_sigma2" else 5
            interp_values = gaussian_filter(interp_values, sigma=sigma)

        # Store for vertical interpolation later
        if d == 0:
            interp_all_depths = np.zeros((len(en4_depth), 133, 105))
        interp_all_depths[d] = interp_values

    # Now interpolate vertically to model's 18 levels
    Z_M = np.array(
        [
            2.5,
            5.0,
            7.5,
            12.5,
            17.5,
            25.0,
            40.0,
            50.0,
            62.5,
            75.0,
            100.0,
            125.0,
            175.0,
            225.0,
            275.0,
            350.0,
            450.0,
            550.0,
        ]
    )

    model_data_3d = np.zeros((18, 133, 105))
    for k in range(18):
        z_target = Z_M[k]
        depth_idx = np.searchsorted(en4_depth, z_target)
        if depth_idx == 0:
            model_data_3d[k] = interp_all_depths[0]
        elif depth_idx >= len(en4_depth):
            model_data_3d[k] = interp_all_depths[-1]
        else:
            w = (z_target - en4_depth[depth_idx - 1]) / (
                en4_depth[depth_idx] - en4_depth[depth_idx - 1]
            )
            model_data_3d[k] = (1 - w) * interp_all_depths[
                depth_idx - 1
            ] + w * interp_all_depths[depth_idx]

    return model_data_3d  # (KS, IS1, JS1)


def compute_density(T, S):
    """Compute density anomaly from T [°C] and S [frac]"""
    ro = np.zeros((18, 133, 105))
    for k in range(18):
        for i in range(133):
            for j in range(105):
                ro[k, i, j] = eckart_density_anomaly(T[k, i, j], S[k, i, j])
    return ro


def compute_model_geostrophic(ro, kt1, fku):
    """Compute model-style geostrophic velocity at full depth (factor 1)"""
    sum_x_cum = np.zeros((133, 105, 18))
    sum_y_cum = np.zeros((133, 105, 18))
    c8 = 0.25 / 1389000.0  # 1/cm
    DX_CM = 1389000.0
    C1 = 981.0

    for k in range(18):
        delta_ro_x = np.zeros((133, 105))
        delta_ro_x[1:133, 1:105] = (
            ro[:, 0:132, k] + ro[:, 1:133, k] - ro[:, 0:132, k] - ro[:, 1:133, k]
        )  # need to transpose
        # Fix: ro is (k, i, j) but we need (i, j, k)
        ro_ijk = np.transpose(ro, (1, 2, 0))  # (i, j, k)
        delta_ro_x[1:133, 1:105] = (
            ro_ijk[0:132, 1:105, k]
            + ro_ijk[1:133, 1:105, k]
            - ro_ijk[0:132, 0:104, k]
            - ro_ijk[1:133, 0:104, k]
        )
        delta_ro_y = np.zeros((133, 105))
        delta_ro_y[1:133, 1:105] = (
            ro_ijk[0:132, 0:104, k]
            + ro_ijk[0:132, 1:105, k]
            - ro_ijk[1:133, 0:104, k]
            - ro_ijk[1:133, 1:105, k]
        )

        if k == 0:
            sum_x_cum[:, :, k] = c8 * 100.0 * DZ_M[k] * delta_ro_x
            sum_y_cum[:, :, k] = c8 * 100.0 * DZ_M[k] * delta_ro_y
        else:
            sum_x_cum[:, :, k] = (
                sum_x_cum[:, :, k - 1] + c8 * 100.0 * DZ_M[k] * delta_ro_x
            )
            sum_y_cum[:, :, k] = (
                sum_y_cum[:, :, k - 1] + c8 * 100.0 * DZ_M[k] * delta_ro_y
            )

    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -C1 * sum_y_cum / f_safe[:, :, np.newaxis]
    V_geo = C1 * sum_x_cum / f_safe[:, :, np.newaxis]
    return U_geo, V_geo


def percentile_stats(arr, mask=None):
    if mask is not None:
        arr = arr[mask]
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {"max": 0.0, "p99": 0.0, "p90": 0.0, "p50": 0.0, "mean": 0.0}
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def main():
    print("=" * 70)
    print("STAGE 7.9 PHASE 4 — EN4 INTERPOLATION SENSITIVITY")
    print("=" * 70)

    # Check if EN4 raw data exists
    en4_path = "data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc"
    import os

    if not os.path.exists(en4_path):
        print(f"  EN4 raw data not found at {en4_path}")
        print("  Skipping interpolation sensitivity analysis.")
        print("  (Run EN4 download script first)")
        return

    print("Loading EN4 raw data...")
    en4_ds = xr.open_dataset(en4_path)

    print("Loading model grid...")
    model_lat, model_lon, kt1, wet = load_model_grid()

    interior_mask = np.zeros((133, 105), dtype=bool)
    interior_mask[2:133, 2:105] = True
    mask = wet & interior_mask

    # Compute fku
    fku = np.zeros((133, 105))
    for i in range(133):
        for j in range(105):
            if wet[i, j]:
                fku[i, j] = 2 * 7.29e-5 * np.sin(np.deg2rad(model_lat[i, j]))
            else:
                fku[i, j] = np.nan

    methods = ["nearest", "bilinear", "gaussian_sigma2", "gaussian_sigma5"]
    results = {}

    for method in methods:
        print(f"\n--- Interpolation method: {method} ---")
        try:
            T = interpolate_en4_to_model(en4_ds, "temperature", method)
            S = interpolate_en4_to_model(en4_ds, "salinity", method)
            ro = compute_density(T, S)
            U_geo, V_geo = compute_model_geostrophic(ro, kt1, fku)
            speed = np.sqrt(U_geo**2 + V_geo**2) / 100.0  # m/s
            stats = percentile_stats(speed[:, :, -1], mask)
            print(
                f"  Full depth: max={stats['max']:.2f} P99={stats['p99']:.2f} P90={stats['p90']:.2f} m/s"
            )

            # Compute density gradient stats
            ro_ijk = np.transpose(ro, (1, 2, 0))
            grad_max = 0.0
            for k in range(18):
                delta_ro = np.zeros((133, 105))
                delta_ro[1:133, 1:105] = (
                    ro_ijk[0:132, 1:105, k]
                    + ro_ijk[1:133, 1:105, k]
                    - ro_ijk[0:132, 0:104, k]
                    - ro_ijk[1:133, 0:104, k]
                )
                grad = np.abs(delta_ro / (2.0 * 13890.0)) * 100.0  # g/cm^3 per m
                grad_max = max(grad_max, np.nanmax(grad[mask]))
            print(f"  Max |d(ro)/dx|: {grad_max:.2e} g/cm^3/m")

            results[method] = {"full_depth": stats, "max_grad": float(grad_max)}
        except Exception as e:
            print(f"  ERROR: {e}")
            results[method] = {"error": str(e)}

    # Summary
    print("\n=== Summary ===")
    print(f"{'Method':<25} {'max U (m/s)':<14} {'max grad':<14}")
    print("-" * 55)
    for method, res in results.items():
        if "error" not in res:
            print(
                f"{method:<25} {res['full_depth']['max']:<14.2f} {res['max_grad']:<14.2e}"
            )
        else:
            print(f"{method:<25} ERROR: {res['error']}")

    # Save
    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "interpolation_sensitivity.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved interpolation_sensitivity.json")


if __name__ == "__main__":
    main()
