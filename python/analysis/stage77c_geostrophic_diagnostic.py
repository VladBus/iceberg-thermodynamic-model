#!/usr/bin/env python
"""
Stage 7.7C — Geostrophic velocity diagnostic using the EXACT model Block 200 formulation.

This computes the geostrophic velocity that satisfies the model's discrete equations:
f * V_geo = 2 * C1 * sum_x / f
f * U_geo = -2 * C1 * sum_y / f

where sum_x, sum_y are the baroclinic pressure integrals from Block 200.
"""

import numpy as np
import xarray as xr
import json
import os
from pathlib import Path

# Model parameters (from param.f90 and main.f90)
IS = 132
JS = 104
IS1 = IS + 1  # 133
JS1 = JS + 1  # 105
KS = 18
DX_CM = 1389000.0  # cm
G_CM = 981.0  # cm/s^2
ROC = 1.0  # g/cm^3
C1 = G_CM / ROC  # 981
C8 = 0.25 / DX_CM  # 1/cm

# Coriolis
OMEGA = 7.29e-5  # rad/s
LAT_REF = 74.5
F_REF = 2 * OMEGA * np.sin(np.deg2rad(LAT_REF))

# Z levels (centers, from param.f90 DATA statement)
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
)  # cm

# Layer thicknesses DZ
DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]

# DZ1 (half-layer thicknesses)
DZ1_CM = np.zeros(KS)
DZ1_CM[0] = 0.5 * (Z_CM[1] + Z_CM[0])
for k in range(1, KS - 1):
    DZ1_CM[k] = 0.5 * (Z_CM[k + 1] - Z_CM[k - 1])
DZ1_CM[KS - 1] = 0.5 * (Z_CM[KS - 1] - Z_CM[KS - 2])


def eckart_density_anomaly(T, S):
    """Exact Eckart EOS from equation_of_state.f90"""
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_product():
    """Load the canonical EN4 product"""
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)  # [°C]
    S = ds["salinity_mass_fraction"].values.astype(np.float64)  # [frac]
    kt1 = ds["water_column_levels"].values  # (133, 105)
    wet = ds["wet_mask"].values.astype(bool)  # (133, 105)
    lat = ds["lat"].values
    lon = ds["lon"].values
    return T, S, kt1, wet, lat, lon, ds


def compute_density(T, S):
    """Compute density anomaly using model EOS"""
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_model_baroclinic_integrals(ro, kt1, wet):
    """
    Compute the model's baroclinic pressure integrals (sum_x, sum_y)
    exactly as in Block 200 of main.f90.

    In Block 200, the sums are accumulated vertically from surface to bottom:
    sum(k) = c8 * Σ_{m=1..k} DZ(m) * ΔRO_x(m)
    sum1(k) = c8 * Σ_{m=1..k} DZ(m) * ΔRO_y(m)

    where at each level m:
    ΔRO_x = RO(i-1,j,m) + RO(i,j,m) - RO(i-1,j-1,m) - RO(i,j-1,m)
    ΔRO_y = RO(i-1,j-1,m) + RO(i-1,j,m) - RO(i,j-1,m) - RO(i,j,m)

    These are computed at U-points (i=2..IS, j=2..JS) for the interior.
    """
    sum_x = np.zeros((IS1, JS1, KS), dtype=np.float64)
    sum_y = np.zeros((IS1, JS1, KS), dtype=np.float64)

    # Only compute at interior U-points (i=2..IS, j=2..JS)
    for k in range(KS):
        # ΔRO_x at U-point (i,j) - between T-points (i,j) and (i,j-1)
        # Using the model's 4-point stencil
        ro_im1_j = ro[0:IS, 1:JS1, k]  # i-1, j
        ro_i_j = ro[1:IS1, 1:JS1, k]  # i, j
        ro_im1_jm1 = ro[0:IS, 0:JS, k]  # i-1, j-1
        ro_i_jm1 = ro[1:IS1, 0:JS, k]  # i, j-1

        delta_ro_x = ro_im1_j + ro_i_j - ro_im1_jm1 - ro_i_jm1

        # ΔRO_y at U-point (i,j) - between T-points (i,j) and (i-1,j)
        ro_i_jm1 = ro[1:IS1, 0:JS, k]  # i, j-1
        ro_im1_jm1 = ro[0:IS, 0:JS, k]  # i-1, j-1
        ro_im1_j = ro[0:IS, 1:JS1, k]  # i-1, j
        ro_i_j = ro[1:IS1, 1:JS1, k]  # i, j

        delta_ro_y = ro_im1_jm1 + ro_im1_j - ro_i_jm1 - ro_i_j

        # Accumulate with layer thickness
        sum_x[1:IS1, 1:JS1, k] = C8 * DZ_CM[k] * delta_ro_x
        sum_y[1:IS1, 1:JS1, k] = C8 * DZ_CM[k] * delta_ro_y

    # Cumulative vertical integral (sum from surface down to level k)
    sum_x_cum = np.cumsum(sum_x, axis=2)  # (IS1, JS1, KS)
    sum_y_cum = np.cumsum(sum_y, axis=2)

    # Also return total integral
    sum_x_int = sum_x_cum[:, :, -1]
    sum_y_int = sum_y_cum[:, :, -1]

    return sum_x_int, sum_y_int, sum_x_cum, sum_y_cum, sum_x, sum_y


def compute_geostrophic_velocity_model(sum_x_cum, sum_y_cum, fku):
    """
    Compute geostrophic velocity from model's baroclinic integrals at each level.

    From steady-state of semi-implicit Coriolis (Block 200):
    f * V_geo(k) = 2 * C1 * sum_x(k)
    f * U_geo(k) = -2 * C1 * sum_y(k)

    Units: sum in [g/cm^3 * cm] = [g/cm^2]
           C1 in [cm/s^2 / (g/cm^3)] = [cm^4/g/s^2]
           C1*sum in [cm^2/s^2] = acceleration
           V_geo = 2*C1*sum/f in [cm/s]
    """
    # U and V at U-points (i=2..IS, j=2..JS) for each level
    # fku is at U-points (IS1, JS1) - broadcast to 3D

    # Avoid division by zero
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]  # broadcast to levels

    U_geo = -2.0 * C1 * sum_y_cum / f_safe_3d  # cm/s
    V_geo = 2.0 * C1 * sum_x_cum / f_safe_3d  # cm/s

    return U_geo, V_geo


def compute_hydrostatic_pressure(ro, kt1, wet):
    """
    Compute hydrostatic pressure from density at each level.
    p(x,y,z) = g * ∫_z^H ρ(x,y,z') dz'
    Returns pressure at T-points [dyn/cm^2]
    """
    # Convert ro to full density: rho = 1.02 + ro [g/cm^3]
    rho = 1.02 + ro  # g/cm^3

    # Pressure at T-points (cell centers)
    p = np.zeros_like(ro)

    for k in range(KS - 1, -1, -1):  # bottom to top
        if k == KS - 1:
            # Bottom layer: p = g * rho * dz/2 (pressure at center of bottom layer)
            mask = wet & (kt1 > k)
            p[:, :, k][mask] = G_CM * rho[:, :, k][mask] * DZ_CM[k] * 0.5
        else:
            # p(k) = p(k+1) + g * rho(k+1) * DZ(k+1) + g * rho(k) * DZ(k) * 0.5
            # Actually: integrate from bottom up
            mask = wet & (kt1 > k)
            p[:, :, k][mask] = (
                p[:, :, k + 1][mask]
                + G_CM * rho[:, :, k + 1][mask] * DZ_CM[k + 1]
                + G_CM * rho[:, :, k][mask] * DZ_CM[k] * 0.5
            )

    return p


def percentile_stats(arr, mask=None):
    """Compute percentile statistics."""
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
        "min": float(np.min(arr)),
    }


def main():
    print("=" * 60)
    print("STAGE 7.7C — GEOSTROPHIC VELOCITY DIAGNOSTIC (MODEL FORMULATION)")
    print("=" * 60)

    # Load EN4 product
    print("Loading EN4 product...")
    T, S, kt1, wet, lat, lon, ds = load_en4_product()

    # Compute density
    print("Computing density with Eckart EOS...")
    ro = compute_density(T, S)

    # Create wet mask for 3D
    wet_3d = wet[:, :, np.newaxis] & (
        np.arange(KS)[np.newaxis, np.newaxis, :] < kt1[:, :, np.newaxis]
    )

    print(f"T range: {np.nanmin(T[wet_3d]):.4f} .. {np.nanmax(T[wet_3d]):.4f} °C")
    print(f"S range: {np.nanmin(S[wet_3d]):.6f} .. {np.nanmax(S[wet_3d]):.6f} frac")
    print(f"ro range: {np.nanmin(ro[wet_3d]):.6f} .. {np.nanmax(ro[wet_3d]):.6f} g/cm³")

    # Load fku from model grid (or compute it)
    # For now compute from latitude
    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan

    # Compute model's baroclinic pressure integrals
    print("\nComputing model baroclinic pressure integrals (Block 200)...")
    sum_x_int, sum_y_int, sum_x_cum, sum_y_cum, sum_x_3d, sum_y_3d = (
        compute_model_baroclinic_integrals(ro, kt1, wet)
    )

    # Compute geostrophic velocity using model formulation (at each level)
    print("Computing geostrophic velocity (model formulation)...")
    U_geo_3d, V_geo_3d = compute_geostrophic_velocity_model(sum_x_cum, sum_y_cum, fku)
    speed_geo_3d = np.sqrt(U_geo_3d**2 + V_geo_3d**2) / 100.0  # m/s

    # Also compute depth-integrated for comparison
    U_geo = -2.0 * C1 * sum_y_int / np.where(np.abs(fku) > 1e-12, fku, np.nan)
    V_geo = 2.0 * C1 * sum_x_int / np.where(np.abs(fku) > 1e-12, fku, np.nan)
    speed_geo = np.sqrt(U_geo**2 + V_geo**2) / 100.0

    # Statistics - only interior U-points (i=2..IS, j=2..JS) that are wet
    # U-points are at (i,j) for i=1..IS1, j=1..JS1 but the model computes at i=2..IS, j=2..JS
    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True

    print("\n--- GEOSTROPHIC VELOCITY (model formulation, m/s) ---")
    results = {
        "model_formulation_max": 0.0,
        "model_formulation_per_level": {},
    }

    for k in range(KS):
        # Mask for wet U-points at this level
        mask = wet & (kt1 > k) & interior_mask
        if not np.any(mask):
            continue

        # U_geo_3d is at U-points (IS1, JS1, KS)
        U_k = U_geo_3d[:, :, k] / 100.0  # m/s
        V_k = V_geo_3d[:, :, k] / 100.0
        speed_k = np.sqrt(U_k**2 + V_k**2)
        stats = percentile_stats(speed_k, mask)

        print(
            f"  Level {k+1} (z={Z_CM[k]/100:.0f}m): |U_geo| max={stats['max']:.2f} P99={stats['p99']:.2f} P90={stats['p90']:.2f} P50={stats['p50']:.2f}"
        )

        results["model_formulation_per_level"][f"level_{k+1}"] = {
            "max": stats["max"],
            "p99": stats["p99"],
            "p90": stats["p90"],
            "p50": stats["p50"],
        }

    # Overall max - using the deepest level (full depth integral)
    mask = wet & interior_mask & (kt1 > 0)
    if np.any(mask):
        speed_deep = speed_geo_3d[:, :, -1]  # deepest level = full integral
        overall_max = np.nanmax(speed_deep[mask])
        results["model_formulation_max"] = float(overall_max)
        print(f"\nOverall max |U_geo| (full depth): {overall_max:.2f} m/s")

        # Find max location
        speed_masked = np.where(mask, speed_deep, -np.inf)
        idx = np.nanargmax(speed_masked)
        i_max, j_max = np.unravel_index(idx, speed_deep.shape)
        print(f"Max at i={i_max} (0-indexed), j={j_max}")
        print(f"  1-indexed: i={i_max+1}, j={j_max+1}")
        print(f"  lat={lat[i_max, j_max]:.4f}, lon={lon[i_max, j_max]:.4f}")
        print(
            f"  U_geo={U_geo_3d[i_max, j_max, -1]/100:.2f} m/s, V_geo={V_geo_3d[i_max, j_max, -1]/100:.2f} m/s"
        )
        print(f"  |U_geo|={speed_deep[i_max, j_max]:.2f} m/s")

    # Also compute standard geostrophic for comparison
    print("\n--- STANDARD GEOSTROPHIC (continuous, surface) ---")
    # Standard: f*v = g * ∂ρ/∂x, f*u = -g * ∂ρ/∂y
    # At surface level
    k = 0
    mask_surf = wet & (kt1 > k)
    dro_dx = np.zeros((IS1, JS1))
    dro_dy = np.zeros((IS1, JS1))

    # Centered differences at T-points
    dro_dx[1:-1, 1:-1] = (ro[2:, 1:-1, k] - ro[:-2, 1:-1, k]) / (2.0 * DX_CM)
    dro_dy[1:-1, 1:-1] = (ro[1:-1, 2:, k] - ro[1:-1, :-2, k]) / (2.0 * DX_CM)

    # Interpolate to U-points (average in j) and V-points (average in i)
    # U-points: (i,j) between T-points (i,j) and (i,j-1) in j-direction
    # Actually U is at (i, j) between T (i, j) and (i, j-1)
    f_surf = np.where(mask_surf, 2 * OMEGA * np.sin(np.deg2rad(lat)), np.nan)

    # At U-points (i=2..IS, j=2..JS)
    dro_dx_u = 0.5 * (dro_dx[1:IS1, 1:JS1] + dro_dx[1:IS1, 0:JS])
    dro_dy_u = 0.5 * (dro_dy[1:IS1, 1:JS1] + dro_dy[1:IS1, 0:JS])
    f_u = fku[1:IS1, 1:JS1]

    v_geo_std = G_CM * dro_dx_u / f_u  # cm/s
    u_geo_std = -G_CM * dro_dy_u / f_u  # cm/s

    speed_std = np.sqrt(u_geo_std**2 + v_geo_std**2) / 100.0
    mask_u = mask_surf[1:IS1, 1:JS1]
    print(f"  Surface max |U_geo|: {np.nanmax(speed_std[mask_u]):.2f} m/s")

    # Save diagnostic outputs
    print("\nSaving diagnostic outputs...")
    out_dir = Path("data/output/diagnostics/stage7.7C")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save geostrophic velocity at each level NetCDF
    out_ds = xr.Dataset(
        {
            "u_geo": (("i", "j", "k"), U_geo_3d / 100.0),  # m/s
            "v_geo": (("i", "j", "k"), V_geo_3d / 100.0),
            "speed_geo": (("i", "j", "k"), speed_geo_3d),
            "sum_x": (("i", "j", "k"), sum_x_cum),
            "sum_y": (("i", "j", "k"), sum_y_cum),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "k": np.arange(KS),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
            "kt1": (("i", "j"), kt1),
            "wet": (("i", "j"), wet.astype(int)),
            "z_cm": (("k",), Z_CM),
        },
    )
    out_ds.to_netcdf(out_dir / "geostrophic_velocity.nc")
    print("   Saved geostrophic_velocity.nc")

    # Save pressure gradient diagnostics
    out_ds2 = xr.Dataset(
        {
            "sum_x_level": (("i", "j", "k"), sum_x_3d),
            "sum_y_level": (("i", "j", "k"), sum_y_3d),
            "sum_x_cum": (("i", "j", "k"), sum_x_cum),
            "sum_y_cum": (("i", "j", "k"), sum_y_cum),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "k": np.arange(KS),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
            "z_cm": (("k",), Z_CM),
        },
    )
    out_ds2.to_netcdf(out_dir / "pressure_gradient_integrals.nc")
    print("   Saved pressure_gradient_integrals.nc")

    # Save depth-integrated geostrophic (for barotropic initialization)
    U_geo_bt = -2.0 * C1 * sum_y_int / np.where(np.abs(fku) > 1e-12, fku, np.nan)
    V_geo_bt = 2.0 * C1 * sum_x_int / np.where(np.abs(fku) > 1e-12, fku, np.nan)
    speed_bt = np.sqrt(U_geo_bt**2 + V_geo_bt**2) / 100.0

    out_ds3 = xr.Dataset(
        {
            "u_geo_bt": (("i", "j"), U_geo_bt / 100.0),
            "v_geo_bt": (("i", "j"), V_geo_bt / 100.0),
            "speed_geo_bt": (("i", "j"), speed_bt),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
        },
    )
    out_ds3.to_netcdf(out_dir / "geostrophic_barotropic.nc")
    print("   Saved geostrophic_barotropic.nc")

    # Save statistics
    with open(out_dir / "geostrophic_statistics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("   Saved geostrophic_statistics.json")

    print("\n=== Diagnostic Complete ===")


if __name__ == "__main__":
    main()
