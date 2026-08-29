#!/usr/bin/env python3
"""Stage 8.1 Geostrophic Balance Residual Analysis."""

import xarray as xr
import numpy as np
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def analyze_geostrophic_balance(run_dir, run_name):
    """Analyze geostrophic balance residual: f*v + ∂p/∂x, -f*u + ∂p/∂y."""
    nc_dir = Path(run_dir) / "output" / "nc"

    # Load day 00 (initial state)
    ds0 = xr.open_dataset(nc_dir / "results_day_00.nc")

    u = ds0["u_velocity"].values  # m/s
    v = ds0["v_velocity"].values
    ro = ds0["density_anomaly"].values  # kg/m3 (anomaly)

    # Model parameters
    dx = 13890.0  # m
    g = 9.81  # m/s2
    rho0 = 1025.0  # kg/m3

    # Coriolis parameter (approximate for Barents Sea ~75°N)
    # f = 2*Omega*sin(lat) = 2*7.292e-5*sin(75°) ≈ 1.41e-4 s-1
    # The model has FKU array, but we'll use a representative value
    f = 1.4e-4  # s-1

    wet = ds0["wet_mask"].values.astype(bool) if "wet_mask" in ds0 else None

    print(f"\n=== {run_name} Geostrophic Balance (Day 0) ===")
    print(f"  u range: {np.nanmin(u):.4f} - {np.nanmax(u):.4f} m/s")
    print(f"  v range: {np.nanmin(v):.4f} - {np.nanmax(v):.4f} m/s")
    print(f"  ro range: {np.nanmin(ro):.6f} - {np.nanmax(ro):.6f} kg/m3")

    # Compute pressure gradient from density anomaly
    # ∂p/∂x = g * ∫ ∂ρ/∂x dz (hydrostatic)
    # We'll compute the horizontal pressure gradient at each level
    dro_dx = np.zeros_like(ro)
    dro_dy = np.zeros_like(ro)

    for k in range(ro.shape[2]):
        for j in range(1, ro.shape[1] - 1):
            for i in range(1, ro.shape[0] - 1):
                if wet is None or wet[i, j]:
                    dro_dx[i, j, k] = (ro[i, j + 1, k] - ro[i, j - 1, k]) / (2 * dx)
                    dro_dy[i, j, k] = (ro[i + 1, j, k] - ro[i - 1, j, k]) / (2 * dx)

    # Geostrophic balance residual
    # R_u = f*v + (1/ρ0)*∂p/∂x = f*v + g*∂ρ/∂x * (depth_scale)
    # R_v = -f*u + (1/ρ0)*∂p/∂y = -f*u + g*∂ρ/∂y * (depth_scale)

    # For a single level, the geostrophic balance is:
    # f*v_geo = -g/ρ0 * ∂p/∂x
    # f*u_geo =  g/ρ0 * ∂p/∂y

    # But the model uses density ANOMALY, so ∂p/∂x = g * ρ0 * ∂(ρ'/ρ0)/∂x * H
    # where ρ' = ro, H is depth scale

    # Let's compute the thermal wind shear from density and compare to actual velocity shear
    print(f"  Max |∂ρ/∂x|: {np.nanmax(np.abs(dro_dx[wet])):.2e} kg/m4")
    print(f"  Max |∂ρ/∂y|: {np.nanmax(np.abs(dro_dy[wet])):.2e} kg/m4")

    # Thermal wind: f * ∂v/∂z = g/ρ0 * ∂ρ/∂x
    # ∂v/∂z = g/(f*ρ0) * ∂ρ/∂x
    dv_dz_tw = g / (f * rho0) * dro_dx
    du_dz_tw = -g / (f * rho0) * dro_dy

    print(f"  Thermal wind ∂v/∂z max: {np.nanmax(np.abs(dv_dz_tw[wet])):.2e} s-1")
    print(f"  Thermal wind ∂u/∂z max: {np.nanmax(np.abs(du_dz_tw[wet])):.2e} s-1")

    # Actual velocity shear from initial u/v
    dv_dz_actual = np.zeros_like(v)
    du_dz_actual = np.zeros_like(u)
    for k in range(u.shape[2] - 1):
        dv_dz_actual[:, :, k] = (
            v[:, :, k + 1] - v[:, :, k]
        ) / 100.0  # levels ~100m apart?
        du_dz_actual[:, :, k] = (u[:, :, k + 1] - u[:, :, k]) / 100.0

    print(f"  Actual ∂v/∂z max: {np.nanmax(np.abs(dv_dz_actual[wet])):.2e} s-1")
    print(f"  Actual ∂u/∂z max: {np.nanmax(np.abs(du_dz_actual[wet])):.2e} s-1")

    # Residual
    res_v = dv_dz_actual - dv_dz_tw
    res_u = du_dz_actual - du_dz_tw

    print(f"  Residual ∂v/∂z max: {np.nanmax(np.abs(res_v[wet])):.2e} s-1")
    print(f"  Residual ∂u/∂z max: {np.nanmax(np.abs(res_u[wet])):.2e} s-1")

    ds0.close()


def analyze_day1_acceleration(run_dir, run_name):
    """Analyze Day 1 acceleration from B3.3 diagnostic output."""
    # This would need parsing the model stdout
    # For now, use the known values:
    # realistic_ref: III=1 maxU2=1319 cm/s, III=2 maxU2=576 cm/s, III=3-12 maxU2=0
    # All runs show identical pattern regardless of initial velocity
    pass


def main():
    print("=" * 80)
    print("STAGE 8.1 GEOSTROPHIC BALANCE RESIDUAL ANALYSIS")
    print("=" * 80)

    runs = [
        ("stage81_forensic_3d", "realistic_ref"),
        ("stage81_ref_zero", "reference_level (u=v=0)"),
        ("stage81_dyn_height", "dynamic_height (SSH from DH)"),
    ]

    for run_dir, run_name in runs:
        full_path = PROJ_ROOT / "data" / "runs" / run_dir
        analyze_geostrophic_balance(full_path, run_name)


if __name__ == "__main__":
    main()
