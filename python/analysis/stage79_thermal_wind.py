#!/usr/bin/env python
"""
Stage 7.9 PHASE 2-7 — Thermal-wind, reference-level, and dynamic-height diagnostics

This script implements:
1. Thermal-wind relation with multiple reference levels
2. Dynamic height calculation
3. Velocity-SSH consistency check
4. Physical magnitude statistics

Key equations:
- Thermal wind: f·∂v/∂z = (g/ρ₀)·∂ρ/∂x
- Dynamic height: D(x,y) = -∫₀ᴴ (ρ(x,y,z)/ρ₀) dz
- SSH from geostrophy: v_geo = (g/f)·∂η/∂x
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
DX_M = DX_CM / 100.0
G_CM = 981.0
G_M = 9.81
ROC = 1.0  # g/cm^3 (model uses ro = rho - 1.02)
RHO0_CGS = 1.02  # g/cm^3
RHO0_SI = 1025.0  # kg/m^3
OMEGA = 7.29e-5
LAT_REF = 74.5

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
Z_M = Z_CM / 100.0

DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]
DZ_M = DZ_CM / 100.0


def eckart_density_anomaly(T, S):
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4():
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)
    S = ds["salinity_mass_fraction"].values.astype(np.float64)
    kt1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    lat = ds["lat"].values
    lon = ds["lon"].values
    return T, S, kt1, wet, lat, lon


def compute_density(T, S):
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_fku(lat, wet):
    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan
    return fku


def compute_density_gradient_si(ro, fku):
    """
    Compute horizontal density gradients at each level using the model's
    4-point stencil, converted to SI units.
    Returns grad_x, grad_y in (kg/m^3)/m at U-points.
    """
    grad_x = np.zeros((IS1, JS1, KS))
    grad_y = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        ro_si = ro[:, :, k] * 1000.0  # kg/m^3
        delta_ro_x = np.zeros((IS1, JS1))
        delta_ro_x[1:IS1, 1:JS1] = (
            ro_si[0:IS, 1:JS1]
            + ro_si[1:IS1, 1:JS1]
            - ro_si[0:IS, 0:JS]
            - ro_si[1:IS1, 0:JS]
        )
        delta_ro_y = np.zeros((IS1, JS1))
        delta_ro_y[1:IS1, 1:JS1] = (
            ro_si[0:IS, 0:JS]
            + ro_si[0:IS, 1:JS1]
            - ro_si[1:IS1, 0:JS]
            - ro_si[1:IS1, 1:JS1]
        )
        # 4-point stencil gives approximately 2*dx * gradient
        grad_x[:, :, k] = delta_ro_x / (2.0 * DX_M)
        grad_y[:, :, k] = delta_ro_y / (2.0 * DX_M)

    return grad_x, grad_y


def thermal_wind_with_reference(ro, fku, reference_level_k, u_ref=0.0, v_ref=0.0):
    """
    Compute absolute geostrophic velocity using thermal wind with
    a specified reference level.

    Thermal wind: f·∂v/∂z = (g/ρ₀)·∂ρ/∂x
                 f·∂u/∂z = -(g/ρ₀)·∂ρ/∂y

    v(z) = v(z_ref) + ∫_{z_ref}^{z} (g/(ρ₀·f))·∂ρ/∂x dz'
    u(z) = u(z_ref) - ∫_{z_ref}^{z} (g/(ρ₀·f))·∂ρ/∂y dz'

    In SI:
    """
    grad_x, grad_y = compute_density_gradient_si(ro, fku)
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]

    g_si = 9.81
    rho0_si = 1025.0

    U = np.zeros((IS1, JS1, KS))
    V = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        if k == reference_level_k:
            U[:, :, k] = u_ref
            V[:, :, k] = v_ref
        elif k < reference_level_k:
            # Integrate from k to reference_level_k (going down)
            dzs = np.array([DZ_M[m] for m in range(k, reference_level_k)])
            integral_x = np.sum(
                grad_x[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            integral_y = np.sum(
                grad_y[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            V[:, :, k] = v_ref + (g_si / (rho0_si * f_safe)) * integral_x
            U[:, :, k] = u_ref - (g_si / (rho0_si * f_safe)) * integral_y
        else:
            # k > reference_level_k: integrate from reference_level_k to k (going up)
            dzs = np.array([DZ_M[m] for m in range(reference_level_k + 1, k + 1)])
            integral_x = np.sum(
                grad_x[:, :, reference_level_k + 1 : k + 1]
                * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            integral_y = np.sum(
                grad_y[:, :, reference_level_k + 1 : k + 1]
                * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            V[:, :, k] = v_ref - (g_si / (rho0_si * f_safe)) * integral_x
            U[:, :, k] = u_ref + (g_si / (rho0_si * f_safe)) * integral_y

    return U, V


def compute_dynamic_height(ro, kt1, wet, reference_level_k=17):
    """
    Compute dynamic height anomaly D(x,y) relative to reference level.

    D(x,y) = -∫_{z_ref}^{surface} (ρ(x,y,z) - ρ_ref) / ρ₀ dz

    But for geostrophic balance, we need the gradient of D:
    ∂D/∂x = -∫ (1/ρ₀) ∂ρ/∂x dz

    And the geostrophic velocity:
    v_geo = (g/f) ∂D/∂x
    u_geo = -(g/f) ∂D/∂y

    Returns dynamic height in meters.
    """
    # Compute ∂ρ/∂x and ∂ρ/∂y at each level (SI units)
    grad_x, grad_y = compute_density_gradient_si(
        ro, np.ones((IS1, JS1))
    )  # fku not needed for gradient

    # Compute dynamic height gradient by vertical integration from surface to reference
    # D_grad_x(x,y) = -∫_0^z_ref (1/ρ₀) ∂ρ/∂x dz
    D_grad_x = np.zeros((IS1, JS1))
    D_grad_y = np.zeros((IS1, JS1))

    for k in range(reference_level_k + 1):
        dzs = DZ_M[k]
        D_grad_x -= grad_x[:, :, k] * dzs / RHO0_SI
        D_grad_y -= grad_y[:, :, k] * dzs / RHO0_SI

    return D_grad_x, D_grad_y


def compute_ssh_from_velocity(u_geo, v_geo, fku, DX_M, reference_level_k=17):
    """
    Compute SSH gradient from geostrophic velocity, then integrate to get SSH.

    v_geo = (g/f) ∂η/∂x  =>  ∂η/∂x = f·v_geo/g
    u_geo = -(g/f) ∂η/∂y  =>  ∂η/∂y = -f·u_geo/g

    Integrate to get SSH.
    """
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    g = 9.81

    ssh_grad_x = f_safe * v_geo[:, :, 0] / g  # at surface level
    ssh_grad_y = -f_safe * u_geo[:, :, 0] / g

    # Integrate SSH gradient to get SSH field
    # Simple integration: SSH(x,y) = ∫ ∂η/∂x dx
    # Use cumulative sum along j (x-direction)
    ssh = np.zeros((IS1, JS1))
    for j in range(1, JS1):
        ssh[:, j] = ssh[:, j - 1] + ssh_grad_x[:, j] * DX_M

    return ssh, ssh_grad_x, ssh_grad_y


def percentile_stats(arr, mask=None):
    if mask is not None:
        arr = arr[mask]
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {"max": 0.0, "p99": 0.0, "p90": 0.0, "p50": 0.0, "mean": 0.0, "rms": 0.0}
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "rms": float(np.sqrt(np.mean(arr**2))),
    }


def main():
    print("=" * 70)
    print("STAGE 7.9 PHASE 2-7 — THERMAL-WIND & REFERENCE-LEVEL DIAGNOSTICS")
    print("=" * 70)

    T, S, kt1, wet, lat, lon = load_en4()
    ro = compute_density(T, S)
    fku = compute_fku(lat, wet)

    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True
    mask = wet & interior_mask

    # Test A: Surface reference (u_ref=0, v_ref=0 at k=0)
    print("\n--- Test A: Surface reference (k_ref=0, u_ref=0, v_ref=0) ---")
    U_A, V_A = thermal_wind_with_reference(
        ro, fku, reference_level_k=0, u_ref=0.0, v_ref=0.0
    )
    speed_A = np.sqrt(U_A**2 + V_A**2)
    stats_A = percentile_stats(speed_A[:, :, -1], mask)
    print(
        f"  Full depth: max={stats_A['max']:.4f} P99={stats_A['p99']:.4f} P90={stats_A['p90']:.4f} mean={stats_A['mean']:.4f} m/s"
    )

    # Test B: Bottom reference (u_ref=0, v_ref=0 at k=17, 600m)
    print("\n--- Test B: Bottom reference (k_ref=17, u_ref=0, v_ref=0) ---")
    U_B, V_B = thermal_wind_with_reference(
        ro, fku, reference_level_k=17, u_ref=0.0, v_ref=0.0
    )
    speed_B = np.sqrt(U_B**2 + V_B**2)
    stats_B = percentile_stats(speed_B[:, :, -1], mask)
    print(
        f"  Full depth: max={stats_B['max']:.4f} P99={stats_B['p99']:.4f} P90={stats_B['p90']:.4f} mean={stats_B['mean']:.4f} m/s"
    )

    # Test C: Specified reference velocity (typical Barents Sea: u=0.05 m/s, v=0.02 m/s)
    print(
        "\n--- Test C: Specified realistic reference (k_ref=17, u_ref=0.05, v_ref=0.02) ---"
    )
    U_C, V_C = thermal_wind_with_reference(
        ro, fku, reference_level_k=17, u_ref=0.05, v_ref=0.02
    )
    speed_C = np.sqrt(U_C**2 + V_C**2)
    stats_C = percentile_stats(speed_C[:, :, -1], mask)
    print(
        f"  Full depth: max={stats_C['max']:.4f} P99={stats_C['p99']:.4f} P90={stats_C['p90']:.4f} mean={stats_C['mean']:.4f} m/s"
    )

    # Per-level statistics for Test B (bottom reference)
    print("\n--- Per-level statistics (Test B: bottom reference) ---")
    for k in [0, 5, 10, 15, 17]:
        stats_k = percentile_stats(speed_B[:, :, k], mask)
        print(
            f"  k={k+1} (z={Z_M[k]:.0f}m): max={stats_k['max']:.4f} P99={stats_k['p99']:.4f} P90={stats_k['p90']:.4f} m/s"
        )

    # Dynamic height calculation
    print("\n--- Dynamic height calculation ---")
    D_grad_x, D_grad_y = compute_dynamic_height(ro, kt1, wet, reference_level_k=17)
    D_grad_x_ms = percentile_stats(np.abs(D_grad_x), mask)
    D_grad_y_ms = percentile_stats(np.abs(D_grad_y), mask)
    print(f"  |∂D/∂x| max={D_grad_x_ms['max']:.6f} P99={D_grad_x_ms['p99']:.6f} m/m")
    print(f"  |∂D/∂y| max={D_grad_y_ms['max']:.6f} P99={D_grad_y_ms['p99']:.6f} m/m")

    # Compute SSH from dynamic height gradient
    # v_geo = (g/f) ∂D/∂x  =>  at reference level
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    v_from_D = 9.81 * D_grad_x / f_safe
    u_from_D = -9.81 * D_grad_y / f_safe
    print(f"\n  v from dynamic height: max={np.nanmax(np.abs(v_from_D[mask])):.4f} m/s")
    print(f"  u from dynamic height: max={np.nanmax(np.abs(u_from_D[mask])):.4f} m/s")

    # Compare with Test B at reference level
    v_testB_ref = V_B[:, :, 17]
    v_diff = v_from_D - v_testB_ref
    print(
        f"\n  v_testB at ref level: max={np.nanmax(np.abs(v_testB_ref[mask])):.4f} m/s"
    )
    print(f"  v_from_D - v_testB: max={np.nanmax(np.abs(v_diff[mask])):.6f} m/s")

    # Summary table
    print("\n=== Summary: Reference-Level Comparison ===")
    print(f"{'Reference':<40} {'max U (m/s)':<14} {'P99 U (m/s)':<14}")
    print("-" * 68)
    print(
        f"{'Surface (k=0), u=v=0':<40} {stats_A['max']:<14.4f} {stats_A['p99']:<14.4f}"
    )
    print(
        f"{'Bottom (k=17), u=v=0':<40} {stats_B['max']:<14.4f} {stats_B['p99']:<14.4f}"
    )
    print(
        f"{'Bottom (k=17), u=0.05, v=0.02':<40} {stats_C['max']:<14.4f} {stats_C['p99']:<14.4f}"
    )

    # Physical plausibility check
    print("\n=== Physical Plausibility ===")
    print(f"  Typical Barents Sea currents: 0.05-0.20 m/s")
    print(f"  Atlantic Water inflow: up to 0.5 m/s")
    print(f"  Test B (bottom ref, zero): max={stats_B['max']:.4f} m/s")
    print(f"  Test C (bottom ref, realistic): max={stats_C['max']:.4f} m/s")
    if stats_B["max"] < 0.5:
        print("  Test B velocities are physically plausible.")
    else:
        print(
            "  Test B velocities are still too large — interpolation artifacts dominate."
        )

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "test_A_surface_ref": stats_A,
        "test_B_bottom_ref": stats_B,
        "test_C_realistic_ref": stats_C,
        "dynamic_height_grad_x": D_grad_x_ms,
        "dynamic_height_grad_y": D_grad_y_ms,
    }
    with open(out_dir / "thermal_wind_reference_levels.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved thermal_wind_reference_levels.json")

    # Save velocity fields as NetCDF
    ds_out = xr.Dataset(
        {
            "U_surface_ref": (("i", "j", "k"), U_A),
            "V_surface_ref": (("i", "j", "k"), V_A),
            "U_bottom_ref": (("i", "j", "k"), U_B),
            "V_bottom_ref": (("i", "j", "k"), V_B),
            "U_realistic_ref": (("i", "j", "k"), U_C),
            "V_realistic_ref": (("i", "j", "k"), V_C),
            "D_grad_x": (("i", "j"), D_grad_x),
            "D_grad_y": (("i", "j"), D_grad_y),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "k": np.arange(KS),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
            "z_m": (("k",), Z_M),
        },
    )
    ds_out.to_netcdf(out_dir / "thermal_wind_reference_levels.nc")
    print(f"Saved thermal_wind_reference_levels.nc")


if __name__ == "__main__":
    main()
