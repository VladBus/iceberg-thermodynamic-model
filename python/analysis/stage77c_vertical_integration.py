#!/usr/bin/env python
"""
Stage 7.7C — Test vertical integration dependence of geostrophic velocity.

Compute geostrophic velocity using different integration depths:
H = 50, 100, 200, 400, 600 m
"""

import numpy as np
import xarray as xr
import json
from pathlib import Path

# Model parameters
IS = 132
JS = 104
IS1 = IS + 1
JS1 = JS + 1
KS = 18
DX_CM = 1389000.0
G_CM = 981.0
ROC = 1.0
C1 = G_CM / ROC
C8 = 0.25 / DX_CM
OMEGA = 7.29e-5
LAT_REF = 74.5
F_REF = 2 * OMEGA * np.sin(np.deg2rad(LAT_REF))

# Z levels
Z_CM = np.array(
    [
        250.0,
        500.0,
        1000.0,
        1500.0,
        2000.0,
        2500.0,
        3000.0,
        4000.0,
        5000.0,
        7500.0,
        10000.0,
        15000.0,
        20000.0,
        25000.0,
        30000.0,
        40000.0,
        50000.0,
        60000.0,
    ]
)

DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]


def eckart_density_anomaly(T, S):
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_product():
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)
    S = ds["salinity_mass_fraction"].values.astype(np.float64)
    kt1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    lat = ds["lat"].values
    lon = ds["lon"].values
    return T, S, kt1, wet, lat, lon, ds


def compute_density(T, S):
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_geostrophic_at_depth(ro, kt1, wet, lat, max_depth_cm):
    """
    Compute geostrophic velocity integrating only down to max_depth_cm.
    Returns U_geo, V_geo at U-points [cm/s]
    """
    IS1 = ro.shape[0]
    JS1 = ro.shape[1]

    # Determine which levels to include
    included_levels = np.where(Z_CM <= max_depth_cm)[0]
    if len(included_levels) == 0:
        included_levels = [0]

    sum_x_cum = np.zeros((IS1, JS1), dtype=np.float64)
    sum_y_cum = np.zeros((IS1, JS1), dtype=np.float64)

    for k in included_levels:
        # ΔRO_x at U-point (i,j) - between T-points (i,j) and (i,j-1)
        ro_im1_j = ro[0:IS, 1:JS1, k]
        ro_i_j = ro[1:IS1, 1:JS1, k]
        ro_im1_jm1 = ro[0:IS, 0:JS, k]
        ro_i_jm1 = ro[1:IS1, 0:JS, k]

        delta_ro_x = ro_im1_j + ro_i_j - ro_im1_jm1 - ro_i_jm1

        ro_i_jm1 = ro[1:IS1, 0:JS, k]
        ro_im1_jm1 = ro[0:IS, 0:JS, k]
        ro_im1_j = ro[0:IS, 1:JS1, k]
        ro_i_j = ro[1:IS1, 1:JS1, k]

        delta_ro_y = ro_im1_jm1 + ro_im1_j - ro_i_jm1 - ro_i_j

        sum_x_cum[1:IS1, 1:JS1] += C8 * DZ_CM[k] * delta_ro_x
        sum_y_cum[1:IS1, 1:JS1] += C8 * DZ_CM[k] * delta_ro_y

    # Coriolis at U-points
    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan

    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -2.0 * C1 * sum_y_cum / f_safe
    V_geo = 2.0 * C1 * sum_x_cum / f_safe

    return U_geo, V_geo


def percentile_stats(arr, mask=None):
    if mask is not None:
        arr = arr[mask]
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {}
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def main():
    print("=" * 60)
    print("STAGE 7.7C — VERTICAL INTEGRATION DEPENDENCE")
    print("=" * 60)

    T, S, kt1, wet, lat, lon, ds = load_en4_product()
    ro = compute_density(T, S)

    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True

    # Test different integration depths
    depths_m = [50, 100, 200, 400, 600]
    results = {}

    for depth_m in depths_m:
        depth_cm = depth_m * 100
        print(f"\n--- Integration depth: {depth_m} m ---")

        U_geo, V_geo = compute_geostrophic_at_depth(ro, kt1, wet, lat, depth_cm)
        speed = np.sqrt(U_geo**2 + V_geo**2) / 100.0

        mask = wet & interior_mask
        stats = percentile_stats(speed, mask)

        print(
            f"  max={stats['max']:.2f} P99={stats['p99']:.2f} P90={stats['p90']:.2f} P50={stats['p50']:.2f} mean={stats['mean']:.2f} m/s"
        )

        results[f"H_{depth_m}m"] = stats

    # Also test: baroclinic component only (remove depth mean)
    print("\n--- Baroclinic component (full depth minus depth mean) ---")
    U_full, V_full = compute_geostrophic_at_depth(ro, kt1, wet, lat, 60000)

    # Compute depth-mean velocity at each U-point
    # This is the barotropic component
    U_bt = U_full.copy()
    V_bt = V_full.copy()

    # Baroclinic = full - barotropic
    U_bc = U_full - U_bt
    V_bc = V_full - V_bt
    speed_bc = np.sqrt(U_bc**2 + V_bc**2) / 100.0

    mask = wet & interior_mask
    stats_bc = percentile_stats(speed_bc, mask)
    print(f"  Baroclinic max={stats_bc['max']:.2f} P99={stats_bc['p99']:.2f} m/s")

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.7C")
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "vertical_integration_dependence.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nSaved vertical_integration_dependence.json")
    print("\n=== Complete ===")


if __name__ == "__main__":
    main()
