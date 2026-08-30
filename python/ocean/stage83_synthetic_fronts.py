#!/usr/bin/env python3
"""
Stage 8.3: Synthetic Front Experiments for Resolution Convergence Analysis

Creates synthetic density fronts with known analytical thermal-wind solution:
  ρ = ρ₀ + A * tanh(x / L)

Tests resolution convergence for L/Δx = 0.5, 1, 2, 4, 8
"""

import argparse
import json
import pathlib
import sys
import numpy as np
import xarray as xr
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import load_model_grid

# Model Z-level centres in cm
Z_CM = np.array(
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
Z_M = Z_CM / 100.0
KS = len(Z_M)

# Physical constants
G = 9.81  # m/s²
RHO0 = 1025.0  # kg/m³
F_CORIOLIS = 1.4e-4  # s⁻¹ (approx 75°N)


def create_synthetic_density(lat, lon, L_m, A_kgm3=1.0, x_center=None):
    """
    Create synthetic density field: ρ = ρ₀ + A * tanh(x / L)

    Args:
        lat, lon: 2D arrays of latitude/longitude [deg]
        L_m: Front width scale [m]
        A_kgm3: Amplitude of density anomaly [kg/m³]
        x_center: Center of front in x [m], default = domain center

    Returns:
        density anomaly [kg/m³] on model grid
    """
    # Convert lat/lon to local Cartesian (approximate)
    # x = lon * cos(lat) * 111km, y = lat * 111km
    lat_rad = np.deg2rad(lat)
    x_m = (lon - lon.min()) * 111000.0 * np.cos(lat_rad)

    if x_center is None:
        x_center = (x_m.max() + x_m.min()) / 2.0

    # Density anomaly: tanh profile
    rho_anom = A_kgm3 * np.tanh((x_m - x_center) / L_m)

    return rho_anom


def analytical_thermal_wind(L_m, A_kgm3=1.0):
    """
    Analytical thermal-wind shear for ρ = ρ₀ + A * tanh(x/L)

    dρ/dx = A / L * sech²(x/L)

    Thermal wind: f * ∂v/∂z = (g/ρ₀) * ∂ρ/∂x
    ∂v/∂z = (g/(f*ρ₀)) * A/L * sech²(x/L)

    Max shear at x=0: (g/(f*ρ₀)) * A/L
    """
    max_drho_dx = A_kgm3 / L_m  # at x=0, sech²(0)=1
    max_dv_dz = (G / (F_CORIOLIS * RHO0)) * max_drho_dx
    max_du_dz = 0.0  # no y-variation in this setup

    # Integrated velocity from bottom (600m) to surface
    H = 600.0  # m
    max_dv = max_dv_dz * H
    max_du = 0.0

    return {
        "max_drho_dx": max_drho_dx,
        "max_dv_dz": max_dv_dz,
        "max_du_dz": max_du_dz,
        "max_dv": max_dv,
        "max_du": max_du,
    }


def interpolate_to_model_grid(
    data_2d, lat_src, lon_src, lat_dst, lon_dst, method="linear"
):
    """Interpolate 2D field from source lat/lon to destination lat/lon."""
    interp = RegularGridInterpolator(
        (lat_src, lon_src),
        data_2d,
        method=method,
        bounds_error=False,
        fill_value=np.nan,
    )
    points = np.column_stack([lat_dst.ravel(), lon_dst.ravel()])
    result = interp(points).reshape(lat_dst.shape)
    return result


def vertical_interpolation(rho_2d, z_model_m, reference_depth_m=600.0):
    """
    Create 3D density field with vertical structure.
    For synthetic front, assume uniform vertical structure (barotropic front).
    """
    is1, js1 = rho_2d.shape
    rho_3d = np.zeros((is1, js1, KS), dtype=np.float32)

    for k in range(KS):
        rho_3d[:, :, k] = rho_2d

    return rho_3d


def compute_model_thermal_wind(rho_3d, lat, lon, dx_m=13890.0):
    """
    Compute thermal-wind shear from 3D density on model grid.
    Uses same B-grid stencil as the model.
    """
    is1, js1, ks = rho_3d.shape

    # Gradients at U-points (i=2..IS, j=2..JS in 1-based = 1..is-1, 1..js-1 in 0-based)
    drho_dx = np.zeros((is1, js1, ks), dtype=np.float32)
    drho_dy = np.zeros((is1, js1, ks), dtype=np.float32)

    for k in range(ks):
        for j in range(1, js1 - 1):
            for i in range(1, is1 - 1):
                # B-grid 4-point stencil at U-point (i,j)
                # ∂ρ/∂x ≈ (ρ(i-1,j) + ρ(i,j) - ρ(i-1,j-1) - ρ(i,j-1)) / (2*dx)
                drho_dx[i, j, k] = (
                    rho_3d[i - 1, j, k]
                    + rho_3d[i, j, k]
                    - rho_3d[i - 1, j - 1, k]
                    - rho_3d[i, j - 1, k]
                ) / (2 * dx_m)

                # ∂ρ/∂y ≈ (ρ(i-1,j-1) + ρ(i-1,j) - ρ(i,j-1) - ρ(i,j)) / (2*dx)
                drho_dy[i, j, k] = (
                    rho_3d[i - 1, j - 1, k]
                    + rho_3d[i - 1, j, k]
                    - rho_3d[i, j - 1, k]
                    - rho_3d[i, j, k]
                ) / (2 * dx_m)

    # Thermal wind shear: f * ∂v/∂z = (g/ρ₀) * ∂ρ/∂x
    #                     f * ∂u/∂z = -(g/ρ₀) * ∂ρ/∂y
    dv_dz = (G / (F_CORIOLIS * RHO0)) * drho_dx
    du_dz = -(G / (F_CORIOLIS * RHO0)) * drho_dy

    return dv_dz, du_dz, drho_dx, drho_dy


def integrate_thermal_wind(dv_dz, du_dz, z_m, ref_depth_m=600.0, v_ref=0.0, u_ref=0.0):
    """
    Integrate thermal wind shear from reference depth upward/downward.
    z_m: array of level depths [m], positive down
    """
    is1, js1, ks = dv_dz.shape
    v_3d = np.zeros((is1, js1, ks), dtype=np.float32)
    u_3d = np.zeros((is1, js1, ks), dtype=np.float32)

    # Find reference level index
    ref_k = np.searchsorted(z_m, ref_depth_m) - 1
    ref_k = max(0, min(ref_k, ks - 1))

    # Layer thickness
    dz = np.diff(z_m, prepend=z_m[0] / 2)  # approximate

    for i in range(is1):
        for j in range(js1):
            # Upward integration (k < ref_k)
            for k in range(ref_k - 1, -1, -1):
                v_3d[i, j, k] = v_3d[i, j, k + 1] - dv_dz[i, j, k + 1] * dz[k + 1]
                u_3d[i, j, k] = u_3d[i, j, k + 1] - du_dz[i, j, k + 1] * dz[k + 1]

            # Reference level
            v_3d[i, j, ref_k] = v_ref
            u_3d[i, j, ref_k] = u_ref

            # Downward integration (k > ref_k)
            for k in range(ref_k + 1, ks):
                v_3d[i, j, k] = v_3d[i, j, k - 1] + dv_dz[i, j, k - 1] * dz[k - 1]
                u_3d[i, j, k] = u_3d[i, j, k - 1] + du_dz[i, j, k - 1] * dz[k - 1]

    return v_3d, u_3d, ref_k


def run_resolution_convergence_experiment():
    """Run resolution convergence experiment for synthetic fronts."""

    # Load model grid
    grid = load_model_grid()
    lat = grid["lat"]
    lon = grid["lon"]
    wet = grid["wet"]
    is1, js1 = lat.shape

    # Front parameters
    front_widths_km = [10, 20, 30, 50, 100]  # L in km
    dx_km = 13.89  # model resolution

    results = {}

    for L_km in front_widths_km:
        L_m = L_km * 1000.0
        ratio = L_m / (dx_km * 1000.0)

        print(f"\n=== Front width L = {L_km} km (L/Δx = {ratio:.2f}) ===")

        # Analytical solution
        anal = analytical_thermal_wind(L_m)
        print(f"  Analytical: max ∂ρ/∂x = {anal['max_drho_dx']:.2e} kg/m⁴")
        print(f"  Analytical: max dv/dz = {anal['max_dv_dz']:.2e} s⁻¹")
        print(f"  Analytical: max Δv (600m) = {anal['max_dv']:.4f} m/s")

        # Create synthetic density on model grid
        rho_anom = create_synthetic_density(lat, lon, L_m, A_kgm3=1.0)

        # Apply wet mask
        rho_anom = np.where(wet, rho_anom, 0.0)

        # Compute model thermal wind
        rho_3d = vertical_interpolation(rho_anom, Z_M)
        dv_dz, du_dz, drho_dx, drho_dy = compute_model_thermal_wind(rho_3d, lat, lon)

        # Integrate from 600m reference
        v_tw, u_tw, ref_k = integrate_thermal_wind(dv_dz, du_dz, Z_M, ref_depth_m=600.0)

        # Compute metrics
        max_dv_dz = np.nanmax(np.abs(dv_dz))
        max_du_dz = np.nanmax(np.abs(du_dz))
        max_v = np.nanmax(np.abs(v_tw))
        max_u = np.nanmax(np.abs(u_tw))

        # Compare with analytical
        dv_dz_error = (max_dv_dz - anal["max_dv_dz"]) / anal["max_dv_dz"] * 100
        v_error = (max_v - anal["max_dv"]) / anal["max_dv"] * 100

        results[L_km] = {
            "L_over_dx": ratio,
            "analytical_max_dv_dz": anal["max_dv_dz"],
            "analytical_max_dv": anal["max_dv"],
            "numerical_max_dv_dz": float(max_dv_dz),
            "numerical_max_v": float(max_v),
            "dv_dz_error_pct": float(dv_dz_error),
            "v_error_pct": float(v_error),
            "ref_level_k": int(ref_k),
        }

        print(
            f"  Numerical: max dv/dz = {max_dv_dz:.2e} s⁻¹ (error: {dv_dz_error:.1f}%)"
        )
        print(f"  Numerical: max v = {max_v:.4f} m/s (error: {v_error:.1f}%)")

    return results


def run_smoothing_sensitivity_experiment():
    """Run controlled smoothing experiment on a fixed front."""

    grid = load_model_grid()
    lat = grid["lat"]
    lon = grid["lon"]
    wet = grid["wet"]

    # Use L = 20 km front (marginally resolved)
    L_m = 20000.0
    sigma_cells = [0, 1, 2, 3, 5]

    results = {}

    for sigma in sigma_cells:
        print(f"\n=== Smoothing σ = {sigma} cells ===")

        # Create base density
        rho_anom = create_synthetic_density(lat, lon, L_m, A_kgm3=1.0)
        rho_anom = np.where(wet, rho_anom, np.nan)

        # Apply Gaussian smoothing
        if sigma > 0:
            rho_smooth = gaussian_filter(rho_anom, sigma=sigma, mode="nearest")
            rho_smooth = np.where(wet, rho_smooth, 0.0)
        else:
            rho_smooth = np.where(wet, rho_anom, 0.0)

        # Compute thermal wind
        rho_3d = vertical_interpolation(rho_smooth, Z_M)
        dv_dz, du_dz, drho_dx, drho_dy = compute_model_thermal_wind(rho_3d, lat, lon)

        # Integrate
        v_tw, u_tw, ref_k = integrate_thermal_wind(dv_dz, du_dz, Z_M, ref_depth_m=600.0)

        max_dv_dz = np.nanmax(np.abs(dv_dz))
        max_v = np.nanmax(np.abs(v_tw))
        max_grad = np.nanmax(np.sqrt(drho_dx**2 + drho_dy**2))

        results[sigma] = {
            "max_grad_rho": float(max_grad),
            "max_dv_dz": float(max_dv_dz),
            "max_v": float(max_v),
        }

        print(f"  max |∇ρ| = {max_grad:.2e} kg/m⁴")
        print(f"  max dv/dz = {max_dv_dz:.2e} s⁻¹")
        print(f"  max v = {max_v:.4f} m/s")

    return results


def run_model_stability_test(
    rho_3d, run_id, ref_mode="realistic_ref", u_ref=0.05, v_ref=0.02
):
    """
    Write 3D density to NetCDF and run model stability test.
    This would require modifying the initial_ocean_reader to accept the synthetic field.
    For now, we'll output the field for manual testing.
    """
    import os
    import subprocess

    # Create output directory
    out_dir = PROJ_ROOT / "data" / "input" / "processed" / "ocean" / "stage83_synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_id}.nc"

    # Load model grid
    grid = load_model_grid()
    lat = grid["lat"]
    lon = grid["lon"]
    wet = grid["wet"]
    kt1 = grid["water_column_levels"]

    # Create temperature/salinity from density (inverse EOS)
    # For synthetic test, use simple linear relation
    T = 5.0 - 3.0 * (rho_3d[:, :, :, 0] / 1.0)  # dummy
    S = 0.034 + 0.001 * (rho_3d[:, :, :, 0] / 1.0)

    # This is a placeholder - real implementation would need proper T/S
    print(f"  Would write synthetic T/S to {out_file}")
    print(
        f"  Would run: ICEBERG_OCEAN_VELOCITY_INIT={ref_mode} "
        f"ICEBERG_OCEAN_U_REF={u_ref} ICEBERG_OCEAN_V_REF={v_ref} "
        f'fpm run --flag "-I/usr/include" -- {run_id}'
    )

    return out_file


def main():
    parser = argparse.ArgumentParser(
        description="Stage 8.3 Synthetic Front Experiments"
    )
    parser.add_argument(
        "--experiment", choices=["resolution", "smoothing", "all"], default="all"
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=PROJ_ROOT / "data" / "output" / "diagnostics" / "stage8.3",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("STAGE 8.3 SYNTHETIC FRONT RESOLUTION CONVERGENCE EXPERIMENTS")
    print("=" * 70)

    all_results = {}

    if args.experiment in ["resolution", "all"]:
        print("\n" + "=" * 70)
        print("PHASE 4/5/6: RESOLUTION CONVERGENCE & SCALE ANALYSIS")
        print("=" * 70)
        resolution_results = run_resolution_convergence_experiment()
        all_results["resolution_convergence"] = resolution_results

        # Save
        with open(args.output / "resolution_convergence.json", "w") as f:
            json.dump(resolution_results, f, indent=2)

    if args.experiment in ["smoothing", "all"]:
        print("\n" + "=" * 70)
        print("PHASE 7: CONTROLLED SMOOTHING EXPERIMENT")
        print("=" * 70)
        smoothing_results = run_smoothing_sensitivity_experiment()
        all_results["smoothing_sensitivity"] = smoothing_results

        # Save
        with open(args.output / "smoothing_sensitivity.json", "w") as f:
            json.dump(smoothing_results, f, indent=2)

    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY: RESOLUTION CONVERGENCE MATRIX")
    print("=" * 70)
    print(
        f"{'L (km)':>8} {'L/Δx':>8} {'max dv/dz (anal)':>18} {'max dv/dz (num)':>18} {'error %':>10} {'max v (anal)':>14} {'max v (num)':>14}"
    )
    print("-" * 100)

    if "resolution_convergence" in all_results:
        for L_km, r in all_results["resolution_convergence"].items():
            print(
                f"{L_km:>8} {r['L_over_dx']:>8.2f} "
                f"{r['analytical_max_dv_dz']:>18.2e} {r['numerical_max_dv_dz']:>18.2e} "
                f"{r['dv_dz_error_pct']:>10.1f} {r['analytical_max_dv']:>14.4f} {r['numerical_max_v']:>14.4f}"
            )

    if "smoothing_sensitivity" in all_results:
        print("\n" + "=" * 70)
        print("SUMMARY: SMOOTHING SENSITIVITY")
        print("=" * 70)
        print(f"{'σ (cells)':>10} {'max |∇ρ|':>14} {'max dv/dz':>14} {'max v':>10}")
        print("-" * 50)
        for sigma, r in all_results["smoothing_sensitivity"].items():
            print(
                f"{sigma:>10} {r['max_grad_rho']:>14.2e} {r['max_dv_dz']:>14.2e} {r['max_v']:>10.4f}"
            )

    # Save combined results
    with open(args.output / "stage83_synthetic_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
