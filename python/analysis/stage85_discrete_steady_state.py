#!/usr/bin/env python3
"""
Stage 8.5: Discrete Steady-State Solver for Block 200

Implements the exact discrete steady-state velocity solver matching Block 200's
numerical operator. Solves the coupled linear system for U, V at each column.

Reference: Block 200 in app/main.f90 (lines 721-812)
Derivation: data/output/diagnostics/stage8.5/discrete_steady_state_derivation.md
"""

import numpy as np
import xarray as xr
from pathlib import Path
import sys

PROJ_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import load_model_grid

# Model constants (matching Fortran)
DT = 3600.0  # s
DX_CM = 1389000.0  # cm
C1 = 981.0  # g/rho0 in CGS
C3 = 7.5e6 / (DX_CM * DX_CM)  # Ah/dx^2 [1/s]
C8 = 0.25 / DX_CM  # 1/cm
G_SI = 9.81  # m/s^2
RHO0_SI = 1025.0  # kg/m^3
OMEGA = 7.292115e-5  # Earth rotation rate [rad/s]

# Model Z-levels in cm (from param.f90)
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
DZ_CM = np.diff(np.concatenate([[0], Z_CM]))  # layer thicknesses [cm]
DZ1_CM = np.concatenate(
    [[Z_CM[0] / 2], (Z_CM[1:] + Z_CM[:-1]) / 2]
)  # half-layer thicknesses [cm]

# Load model grid
grid = load_model_grid()
LAT = grid["lat"]  # (is1, js1)
LON = grid["lon"]
WET = grid["wet"]
DEPTH_CM = grid["water_depth_cm"]
IS1, JS1 = LAT.shape
IS = IS1 - 1
JS = JS1 - 1
KS = 18

# Compute KT1 (water column levels) from depth
KT1 = np.zeros((IS1, JS1), dtype=np.int32)
for i in range(IS1):
    for j in range(JS1):
        if DEPTH_CM is not None and DEPTH_CM[i, j] != 8888.0 and DEPTH_CM[i, j] > 0:
            KT1[i, j] = np.searchsorted(Z_CM, DEPTH_CM[i, j], side="right")
        else:
            KT1[i, j] = 0

# Coriolis parameter at U-points: fku = 2*Omega*sin(lat) [1/s]
FKU = 2.0 * 7.292115e-5 * np.sin(np.deg2rad(LAT))  # [1/s]

# Model Z-levels in meters
Z_M = Z_CM / 100.0  # meters


def compute_stencils(ro):
    """Compute horizontal density gradient stencils at U-points.

    Returns:
        stencil_x: ΔRO/∂x at U-points [g/cm³] (shape: IS1, JS1, KS)
        stencil_y: ΔRO/∂y at U-points [g/cm³] (shape: IS1, JS1, KS)
    """
    stencil_x = np.zeros((IS1, JS1, KS), dtype=np.float32)
    stencil_y = np.zeros((IS1, JS1, KS), dtype=np.float32)

    for k in range(KS):
        for j in range(1, JS):
            for i in range(1, IS):
                if WET[i, j]:
                    # stencil_x = ro(i-1,j) + ro(i,j) - ro(i-1,j-1) - ro(i,j-1)
                    stencil_x[i, j, k] = (
                        ro[i - 1, j, k]
                        + ro[i, j, k]
                        - ro[i - 1, j - 1, k]
                        - ro[i, j - 1, k]
                    )
                    # stencil_y = ro(i-1,j-1) + ro(i-1,j) - ro(i,j-1) - ro(i,j)
                    stencil_y[i, j, k] = (
                        ro[i - 1, j - 1, k]
                        + ro[i - 1, j, k]
                        - ro[i, j - 1, k]
                        - ro[i, j, k]
                    )
    return stencil_x, stencil_y


def compute_sums(stencil_x, stencil_y, kt1):
    """Compute vertical integrals sum_x, sum_y matching Block 200.

    sum_x(k) = Σ_{m=1..k} [stencil_x(m) + stencil_x(min(m+1,ki))] * c8 * Dz(m)
    sum_y(k) = Σ_{m=1..k} [stencil_y(m) + stencil_y(min(m+1,ki))] * c8 * Dz(m)
    """
    is1, js1, ks = stencil_x.shape
    sum_x = np.zeros((is1, js1, 18), dtype=np.float32)
    sum_y = np.zeros((is1, js1, 18), dtype=np.float32)

    for j in range(1, js1 - 1):
        for i in range(1, is1 - 1):
            ki = kt1[i, j]
            if ki == 0:
                continue

            # k=0 (first level)
            dzz = DZ_CM[0]
            a = (
                stencil_x[i - 1, j, 0]
                + stencil_x[i, j, 0]
                - stencil_x[i - 1, j - 1, 0]
                - stencil_x[i, j - 1, 0]
            )
            b = (
                stencil_y[i - 1, j - 1, 0]
                + stencil_y[i - 1, j, 0]
                - stencil_y[i, j - 1, 0]
                - stencil_y[i, j, 0]
            )
            if ki >= 2:
                a1 = (
                    stencil_x[i - 1, j, 1]
                    + stencil_x[i, j, 1]
                    - stencil_x[i - 1, j - 1, 1]
                    - stencil_x[i, j - 1, 1]
                )
                b1 = (
                    stencil_y[i - 1, j - 1, 1]
                    + stencil_y[i - 1, j, 1]
                    - stencil_y[i, j - 1, 1]
                    - stencil_y[i, j, 1]
                )
            else:
                a1 = a
                b1 = b
            cc_val = C8 * dzz
            sum_x[i, j, 0] = (a + a1) * cc_val
            sum_y[i, j, 0] = (b + b1) * cc_val

            # k=2..ki
            for k in range(1, ki):
                dzz = DZ_CM[k]
                a = (
                    stencil_x[i - 1, j, k]
                    + stencil_x[i, j, k]
                    - stencil_x[i - 1, j - 1, k]
                    - stencil_x[i, j - 1, k]
                )
                b = (
                    stencil_y[i - 1, j - 1, k]
                    + stencil_y[i - 1, j, k]
                    - stencil_y[i, j - 1, k]
                    - stencil_y[i, j, k]
                )
                if k < ki - 1:
                    a1 = (
                        stencil_x[i - 1, j, k + 1]
                        + stencil_x[i, j, k + 1]
                        - stencil_x[i - 1, j - 1, k + 1]
                        - stencil_x[i, j - 1, k + 1]
                    )
                    b1 = (
                        stencil_y[i - 1, j - 1, k + 1]
                        + stencil_y[i - 1, j, k + 1]
                        - stencil_y[i, j - 1, k + 1]
                        - stencil_y[i, j, k + 1]
                    )
                else:
                    a1 = a
                    b1 = b
                cc_val = C8 * dzz
                sum_x[i, j, k] = sum_x[i, j, k - 1] + (a + a1) * cc_val
                sum_y[i, j, k] = sum_y[i, j, k - 1] + (b + b1) * cc_val

    return sum_x, sum_y


def solve_discrete_steady_state(ro, fku, u_ref=0.0, v_ref=0.0, ref_level_k=2):
    """
    Solve the exact discrete steady-state system for Block 200.

    Uses the exact discrete steady-state factor 2*C1/f (not C1/f).
    """
    # Compute stencils and sums
    stencil_x, stencil_y = compute_stencils(ro)
    sum_x, sum_y = compute_sums(stencil_x, stencil_y, KT1)

    # Allocate output
    is1, js1, ks = ro.shape
    U = np.zeros((is1, js1, 18), dtype=np.float32)
    V = np.zeros((is1, js1, 18), dtype=np.float32)

    for j in range(1, JS):
        for i in range(1, IS):
            ki = KT1[i, j]
            if ki == 0:
                continue

            f_val = fku[i, j]
            if abs(f_val) < 1e-12:
                U[i, j, :ki] = u_ref * 100.0
                V[i, j, :ki] = v_ref * 100.0
                continue

            # DISCRETE FACTOR: 2*C1/f (not C1/f!)
            factor = 2.0 * 981.0 / f_val

            # V_geo = factor * sum_x, U_geo = -factor * sum_y
            for k in range(ki):
                V[i, j, k] = factor * sum_x[i, j, k]
                U[i, j, k] = -factor * sum_y[i, j, k]

            # Apply reference level shift
            ref_k = min(ref_level_k - 1, ki - 1)  # 0-indexed
            if ref_k >= 0 and ref_k < ki:
                V_ref = V[i, j, ref_k]
                U_ref = U[i, j, ref_k]
                for k in range(ki):
                    V[i, j, k] = V[i, j, k] - V_ref + v_ref * 100.0
                    U[i, j, k] = U[i, j, k] - U_ref + u_ref * 100.0
            else:
                for k in range(ki):
                    V[i, j, k] = v_ref * 100.0
                    U[i, j, k] = u_ref * 100.0

            # Below bottom: zero
            for k in range(ki, KS):
                U[i, j, k] = 0.0
                V[i, j, k] = 0.0

    # Apply boundary conditions
    U, V = apply_velocity_bc(U, V)

    return U, V


def apply_velocity_bc(u_arr, v_arr):
    """Apply boundary conditions matching Fortran apply_velocity_bc."""
    u_arr[:, 0, :] = u_arr[:, 1, :]
    u_arr[:, -1, :] = u_arr[:, -2, :]
    v_arr[0, :, :] = v_arr[1, :, :]
    u_arr[0, :, :] = u_arr[1, :, :]
    u_arr[-1, :, :] = u_arr[-2, :, :]
    v_arr[:, 0, :] = v_arr[:, 1, :]
    v_arr[:, -1, :] = v_arr[:, -2, :]
    return u_arr, v_arr


def load_ro_from_netcdf(nc_file):
    """Load density anomaly from NetCDF file."""
    ds = xr.open_dataset(nc_file)
    ro = ds["density_anomaly_gcm3"].values  # (is1, js1, ks)
    ds.close()
    return ro


def test_solver():
    """Test the discrete steady-state solver."""
    # Load EN4 density
    ro = load_ro_from_netcdf(
        "/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model/data/input/processed/ocean/initial_ts_2020-01-01.nc"
    )

    # Solve discrete steady state
    U, V = solve_discrete_steady_state(ro, FKU)

    # Diagnostics
    print("=== Discrete Steady-State Solver Test ===")
    print(f"U shape: {U.shape}")
    print(f"V shape: {V.shape}")
    print(f"U range: {U.min():.4f} to {U.max():.4f} cm/s")
    print(f"V range: {V.min():.4f} to {V.max():.4f} cm/s")
    print(f"U max (m/s): {U.max()/100:.4f}")
    print(f"V max (m/s): {V.max()/100:.4f}")

    # Check NaN
    print(f"NaN in U: {np.isnan(U).sum()}")
    print(f"NaN in V: {np.isnan(V).sum()}")

    return U, V


if __name__ == "__main__":
    test_solver()
