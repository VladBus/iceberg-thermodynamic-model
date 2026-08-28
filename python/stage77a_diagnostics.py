#!/usr/bin/env python
"""
Stage 7.7A — Dynamic Imbalance & Stability Forensic Audit
Diagnostic script to analyze initial conditions, density gradients,
pressure gradients, geostrophic velocities, and CFL conditions.
"""

import numpy as np
import xarray as xr
import json
import os
from pathlib import Path

# Model parameters (from param.f90)
IS = 132
JS = 104
IS1 = IS + 1  # 133
JS1 = JS + 1  # 105
KS = 18
DX_CM = 1389000.0  # cm
DX_M = DX_CM / 100.0  # m
DT1 = 120.0  # s
DT = 3600.0  # s
MM3 = 30
AH = 7.5e6  # cm^2/s
G = 981.0  # cm/s^2
ROC = 1.0  # g/cm^3
C1 = G / ROC  # 981
C3 = AH / (DX_CM * DX_CM)  # 3.89e-6 1/s
C10 = DT1 / DX_CM  # 8.64e-5 s/cm

# Coriolis at reference latitude (mean of domain ~74.5N)
OMEGA = 7.29e-5  # rad/s
F_REF = 2 * OMEGA * np.sin(np.deg2rad(74.5))  # ~1.4e-4 1/s

# Z-levels (centers, from param.f90 DATA statement)
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
Z_M = Z_CM / 100.0  # m

# Layer thicknesses
DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]
DZ_M = DZ_CM / 100.0  # m

DZ1_CM = np.zeros(KS)
DZ1_CM[0] = 0.5 * (Z_CM[1] + Z_CM[0])
for k in range(1, KS - 1):
    DZ1_CM[k] = 0.5 * (Z_CM[k + 1] - Z_CM[k - 1])
DZ1_CM[KS - 1] = 0.5 * (Z_CM[KS - 1] - Z_CM[KS - 2])
DZ1_M = DZ1_CM / 100.0  # m


def eckart_density_anomaly(T, S):
    """Eckart EOS from equation_of_state.f90: RO = 1/(0.698 + aa/bb) - 1.02"""
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_initial_conditions():
    """Load EN4 initial conditions and model grid."""
    # Load EN4 product
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")

    T = ds["temperature_celsius"].values.astype(
        np.float32
    )  # [°C], shape (133, 105, 18)
    S = ds["salinity_mass_fraction"].values.astype(
        np.float32
    )  # [frac], shape (133, 105, 18)
    kt1 = ds["water_column_levels"].values.astype(np.int32)  # shape (133, 105)
    wet = ds["wet_mask"].values.astype(bool)  # shape (133, 105)
    lat = ds["lat"].values  # (133, 105)
    lon = ds["lon"].values  # (133, 105)

    # Load grid geometry from hhh.bar / KOORD.DAT (reconstruct from model)
    # We'll also load the model's kt1 from the grid coupling to verify

    return T, S, kt1, wet, lat, lon, ds


def load_synthetic_initial_conditions():
    """Load synthetic initial conditions for comparison."""
    # The synthetic init is: T = 15 - 13*depth_ratio, S = 0.033 + 0.002*depth_ratio
    T_syn = np.zeros((IS1, JS1, KS), dtype=np.float32)
    S_syn = np.zeros((IS1, JS1, KS), dtype=np.float32)

    for k in range(KS):
        depth_ratio = float(k) / max(1.0, float(KS - 1))
        T_syn[:, :, k] = 15.0 - 13.0 * depth_ratio
        S_syn[:, :, k] = 0.033 + 0.002 * depth_ratio

    return T_syn, S_syn


def compute_density(T, S):
    """Compute density anomaly using model EOS."""
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_horizontal_gradients(field, dx_m=DX_M):
    """Compute horizontal gradients using centered differences.

    field shape: (133, 105, 18) or (133, 105)
    Returns: d_dx, d_dy with same shape, NaN at boundaries and land
    """
    # X-gradient (along j, axis=1): (f[i,j+1] - f[i,j-1]) / (2*dx)
    # Y-gradient (along i, axis=0): (f[i+1,j] - f[i-1,j]) / (2*dx)

    d_dx = np.full_like(field, np.nan)
    d_dy = np.full_like(field, np.nan)

    if field.ndim == 3:
        # Interior points
        d_dx[:, 1:-1, :] = (field[:, 2:, :] - field[:, :-2, :]) / (2.0 * dx_m)
        d_dy[1:-1, :, :] = (field[2:, :, :] - field[:-2, :, :]) / (2.0 * dx_m)
    else:
        d_dx[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2.0 * dx_m)
        d_dy[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2.0 * dx_m)

    return d_dx, d_dy


def compute_geostrophic_velocity(ro, dx_m=DX_M, f_coriolis=F_REF):
    """Compute geostrophic velocity from density anomaly.

    f v = (1/rho0) * dp/dx = g * d(rho)/dx  (using hydrostatic balance)
    f u = -(1/rho0) * dp/dy = -g * d(rho)/dy

    ro = rho - 1.02 [g/cm^3]
    rho0 = 1.02 g/cm^3
    g = 981 cm/s^2

    Pressure gradient: dp/dx = g * integral( d(rho)/dx * dz )
    But for baroclinic geostrophic: f v = g * d/dx(integral(rho dz))

    In the model (block 200): sum = c8 * dz * (RO differences)
    c8 = 0.25/dx

    For diagnostic, compute geostrophic velocity at each level:
    f v_geo = g * d(rho)/dx  (using local density gradient)
    f u_geo = -g * d(rho)/dy

    But more accurately: integrate baroclinic pressure gradient.
    """
    # Compute horizontal gradients of density anomaly
    dro_dx, dro_dy = compute_horizontal_gradients(ro, dx_m)

    # Geostrophic velocity [m/s]
    # f v = g * dro_dx  (rho in g/cm^3, need to convert to kg/m^3: 1 g/cm^3 = 1000 kg/m^3)
    # But ro is anomaly in g/cm^3, rho = 1.02 + ro g/cm^3
    # g = 9.81 m/s^2
    # f v = (g/rho0) * d(rho)/dx = g * d(ro)/dx (since rho0=1.02, ro=rho-1.02)
    # d(ro)/dx in g/cm^3 / m = 1000 kg/m^3 / m
    # So: f v = 9.81 * (dro_dx * 1000)  [m/s^2] -> v = 9.81 * dro_dx * 1000 / f [m/s]

    g_si = 9.81  # m/s^2

    # dro_dx in g/cm^3 per m -> convert to kg/m^3 per m: *1000
    v_geo = g_si * dro_dx * 1000.0 / f_coriolis  # [m/s]
    u_geo = -g_si * dro_dy * 1000.0 / f_coriolis  # [m/s]

    return u_geo, v_geo


def compute_pressure_gradient_acceleration(ro, dx_m=DX_M):
    """Compute baroclinic pressure gradient acceleration from density.

    From block 200 in main.f90:
    sum = c8 * dz * (RO differences)
    where c8 = 0.25/dx [1/cm]

    The pressure gradient term in momentum eq: -c1 * sum - dpx
    c1 = g/rho0 = 981
    sum = c8 * dz * (RO_x + RO_y differences)

    Acceleration from baroclinic pressure: a_bc = -c1 * sum / dt ?
    Actually in block 200: auu = uij + asa1*vij + dt*(-c1*sum - dpx + c3*slapu)

    So pressure acceleration = -c1 * sum [cm/s^2]
    """
    # c8 = 0.25/dx [1/cm] = 0.25 / 1389000 = 1.80e-7 1/cm
    c8 = 0.25 / DX_CM
    c1 = 981.0

    # Compute baroclinic pressure gradient acceleration at each level
    # sum_x = c8 * sum_k (dro_dx * dz_k)
    # a_x = -c1 * sum_x [cm/s^2]
    # a_y = -c1 * sum_y [cm/s^2]

    dro_dx, dro_dy = compute_horizontal_gradients(ro, DX_CM)  # in cm units

    # dro_dx is per cm, multiply by dz in cm
    sum_x = np.zeros_like(ro)
    sum_y = np.zeros_like(ro)

    for k in range(KS):
        sum_x[:, :, k] = dro_dx[:, :, k] * DZ_CM[k]
        sum_y[:, :, k] = dro_dy[:, :, k] * DZ_CM[k]

    # Vertical integral (cumulative sum from surface down)
    sum_x_int = np.cumsum(sum_x, axis=2)
    sum_y_int = np.cumsum(sum_y, axis=2)

    # Acceleration [cm/s^2]
    ax_bc = -c1 * c8 * sum_x_int
    ay_bc = -c1 * c8 * sum_y_int

    return ax_bc, ay_bc


def compute_cfl(u, v, dx_m=DX_M, dt1=DT1):
    """Compute CFL numbers for given velocity field.

    CFL = U * dt1 / dx
    """
    speed = np.sqrt(u**2 + v**2)
    cfl = speed * dt1 / dx_m
    return cfl


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
    print("=== Stage 7.7A Forensic Audit: Initial Condition Analysis ===\n")

    # Load data
    T, S, kt1, wet, lat, lon, ds = load_initial_conditions()

    # Compute density
    ro = compute_density(T, S)

    # Create wet mask for 3D
    wet_3d = wet[:, :, np.newaxis] & (
        np.arange(KS)[np.newaxis, np.newaxis, :] < kt1[:, :, np.newaxis]
    )

    print("1. INITIAL CONDITION BALANCE AUDIT")
    print(
        f"   T shape: {T.shape}, range: {np.nanmin(T[wet_3d]):.4f} .. {np.nanmax(T[wet_3d]):.4f} °C"
    )
    print(
        f"   S shape: {S.shape}, range: {np.nanmin(S[wet_3d]):.6f} .. {np.nanmax(S[wet_3d]):.6f} frac"
    )
    print(
        f"   RO range: {np.nanmin(ro[wet_3d]):.6f} .. {np.nanmax(ro[wet_3d]):.6f} g/cm³"
    )
    print(f"   Wet cells: {np.sum(wet_3d)} / {IS1*JS1*KS}")
    print(f"   Active wet columns: {np.sum(wet)}")

    # u, v initial values (from init_ocean: 0.20, 0.10 cm/s on wet cells)
    u_init = np.zeros((IS1, JS1, KS), dtype=np.float32)
    v_init = np.zeros((IS1, JS1, KS), dtype=np.float32)
    u_init[wet_3d] = 0.20  # cm/s
    v_init[wet_3d] = 0.10  # cm/s
    print(f"   u init: 0.20 cm/s on wet cells")
    print(f"   v init: 0.10 cm/s on wet cells")

    # SSH (ym2) initial: 0
    print(f"   SSH (ym2) init: 0.0 cm")
    print(
        f"   Pressure (ro) initialized: NOT initially (eos_diag called after init_ocean)"
    )

    # Compute horizontal gradients of T, S, RO
    print("\n2. HORIZONTAL GRADIENTS (surface level, k=0)")
    for k in [0, 5, 10, 17]:
        print(f"\n   Level {k+1} (z={Z_M[k]:.0f}m):")
        dT_dx, dT_dy = compute_horizontal_gradients(T[:, :, k])
        dS_dx, dS_dy = compute_horizontal_gradients(S[:, :, k])
        dro_dx, dro_dy = compute_horizontal_gradients(ro[:, :, k])

        # Only valid wet cells
        mask = wet & (kt1 > k)
        for name, dx, dy in [
            ("dT", dT_dx, dT_dy),
            ("dS", dS_dx, dS_dy),
            ("dro", dro_dx, dro_dy),
        ]:
            stats_dx = percentile_stats(dx, mask)
            stats_dy = percentile_stats(dy, mask)
            print(
                f"     {name}/dx: P50={stats_dx['p50']:.2e}, P90={stats_dx['p90']:.2e}, P99={stats_dx['p99']:.2e}, max={stats_dx['max']:.2e}"
            )
            print(
                f"     {name}/dy: P50={stats_dy['p50']:.2e}, P90={stats_dy['p90']:.2e}, P99={stats_dy['p99']:.2e}, max={stats_dy['max']:.2e}"
            )

    # Geostrophic velocity
    print("\n3. GEOSTROPHIC VELOCITY DIAGNOSTIC")
    u_geo, v_geo = compute_geostrophic_velocity(ro)
    speed_geo = np.sqrt(u_geo**2 + v_geo**2)

    for k in [0, 5, 10, 17]:
        mask = wet & (kt1 > k)
        stats = percentile_stats(speed_geo[:, :, k], mask)
        print(
            f"   Level {k+1} (z={Z_M[k]:.0f}m): |U_geo| P50={stats['p50']:.4f}, P90={stats['p90']:.4f}, P99={stats['p99']:.4f}, max={stats['max']:.4f} m/s"
        )

    # Pressure gradient acceleration
    print("\n4. BAROCLINIC PRESSURE GRADIENT ACCELERATION (model formulation)")
    ax_bc, ay_bc = compute_pressure_gradient_acceleration(ro)
    accel_bc = np.sqrt(ax_bc**2 + ay_bc**2)

    for k in [0, 5, 10, 17]:
        mask = wet & (kt1 > k)
        stats = percentile_stats(accel_bc[:, :, k], mask)
        print(
            f"   Level {k+1}: |a_bc| P50={stats['p50']:.2e}, P90={stats['p90']:.2e}, P99={stats['p99']:.2e}, max={stats['max']:.2e} cm/s²"
        )

    # Initial CFL
    print("\n5. INITIAL CFL")
    cfl_init = compute_cfl(u_init, v_init)
    stats = percentile_stats(cfl_init[wet_3d])
    print(f"   CFL(dt1=120s, U=0.20cm/s, V=0.10cm/s): max={stats['max']:.2e}")

    # CFL at various velocity scales
    print("\n6. CFL AT VARIOUS VELOCITY SCALES")
    for U_ms in [0.002, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0]:
        U_cms = U_ms * 100.0
        cfl = U_cms * DT1 / DX_CM
        dt_req = DX_CM / U_cms if U_cms > 0 else np.inf
        print(
            f"   U={U_ms:.1f} m/s ({U_cms:.1f} cm/s): CFL={cfl:.4f}, dt_required={dt_req:.1f} s"
        )

    # Find maximum gradient locations
    print("\n7. MAXIMUM GRADIENT LOCATIONS")
    dT_dx, dT_dy = compute_horizontal_gradients(T[:, :, 0])
    dS_dx, dS_dy = compute_horizontal_gradients(S[:, :, 0])
    dro_dx, dro_dy = compute_horizontal_gradients(ro[:, :, 0])

    mask_surf = wet & (kt1 > 0)

    for name, dx, dy in [
        ("dT", dT_dx, dT_dy),
        ("dS", dS_dx, dS_dy),
        ("dro", dro_dx, dro_dy),
    ]:
        mag = np.sqrt(dx**2 + dy**2)
        idx = np.nanargmax(mag[mask_surf])
        flat_idx = np.where(mask_surf.ravel())[0][idx]
        i, j = np.unravel_index(flat_idx, (IS1, JS1))
        print(
            f"   {name} max at i={i}, j={j}: lat={lat[i,j]:.4f}, lon={lon[i,j]:.4f}, mag={mag[i,j]:.2e}"
        )

    # Rossby radius estimate
    print("\n8. ROSSBY RADIUS / BAROCLINIC SCALE")
    # N^2 = -(g/rho0) * d(rho)/dz
    # Compute N^2 at surface
    # Use first differences in z
    N2 = np.zeros((IS1, JS1, KS))
    for k in range(KS - 1):
        drho_dz = (ro[:, :, k + 1] - ro[:, :, k]) / (
            Z_M[k + 1] - Z_M[k]
        )  # g/cm^3 per m
        N2[:, :, k] = -9.81 * drho_dz * 1000.0 / 1025.0  # 1/s^2 (rho0 ~ 1025 kg/m^3)
    N2[:, :, -1] = N2[:, :, -2]  # extrapolate bottom

    # First baroclinic Rossby radius: R = c1 / f, c1 = sqrt(g' * H)
    # where g' = g * Delta_rho / rho0
    # Use representative stratification
    # For first mode: R ~ (NH) / (pi * f)
    H_mean = 500.0  # m (approx)
    for k in [0, 5, 10, 17]:
        N = np.sqrt(np.maximum(N2[:, :, k], 0))
        mask = wet & (kt1 > k)
        N_avg = np.mean(N[mask])
        R = N_avg * H_mean / (np.pi * F_REF)
        print(f"   Level {k+1}: N={N_avg:.2e} 1/s, R={R/1000:.1f} km")

    print(f"   Model grid spacing: {DX_M/1000:.2f} km")
    print(
        f"   Resolution vs Rossby radius: {'resolved' if DX_M < R/2 else 'marginal' if DX_M < R else 'unresolved'}"
    )

    # Synthetic vs realistic comparison
    print("\n9. SYNTHETIC vs REALISTIC COMPARISON")
    T_syn, S_syn = load_synthetic_initial_conditions()
    ro_syn = compute_density(T_syn, S_syn)

    for k in [0, 5, 10, 17]:
        mask = wet & (kt1 > k)
        # T gradient
        dT_syn_dx, dT_syn_dy = compute_horizontal_gradients(T_syn[:, :, k])
        dT_real_dx, dT_real_dy = compute_horizontal_gradients(T[:, :, k])
        dS_syn_dx, dS_syn_dy = compute_horizontal_gradients(S_syn[:, :, k])
        dS_real_dx, dS_real_dy = compute_horizontal_gradients(S[:, :, k])
        dro_syn_dx, dro_syn_dy = compute_horizontal_gradients(ro_syn[:, :, k])
        dro_real_dx, dro_real_dy = compute_horizontal_gradients(ro[:, :, k])

        for name, real_dx, real_dy, syn_dx, syn_dy in [
            ("dT", dT_real_dx, dT_real_dy, dT_syn_dx, dT_syn_dy),
            ("dS", dS_real_dx, dS_real_dy, dS_syn_dx, dS_syn_dy),
            ("dro", dro_real_dx, dro_real_dy, dro_syn_dx, dro_syn_dy),
        ]:
            real_mag = np.sqrt(real_dx**2 + real_dy**2)
            syn_mag = np.sqrt(syn_dx**2 + syn_dy**2)
            real_max = np.nanmax(real_mag[mask])
            syn_max = (
                np.nanmax(syn_mag[mask]) if np.any(np.isfinite(syn_mag[mask])) else 0
            )
            ratio = real_max / syn_max if syn_max > 0 else np.inf
            print(
                f"   {name} level {k+1}: real_max={real_max:.2e}, syn_max={syn_max:.2e}, ratio={ratio:.1f}x"
            )

    # Save diagnostic outputs
    print("\n10. SAVING DIAGNOSTIC OUTPUTS")

    # Save initial density gradients NetCDF
    out_ds = xr.Dataset(
        {
            "dT_dx": (("i", "j", "k"), compute_horizontal_gradients(T)[0]),
            "dT_dy": (("i", "j", "k"), compute_horizontal_gradients(T)[1]),
            "dS_dx": (("i", "j", "k"), compute_horizontal_gradients(S)[0]),
            "dS_dy": (("i", "j", "k"), compute_horizontal_gradients(S)[1]),
            "dro_dx": (("i", "j", "k"), compute_horizontal_gradients(ro)[0]),
            "dro_dy": (("i", "j", "k"), compute_horizontal_gradients(ro)[1]),
            "u_geo": (("i", "j", "k"), compute_geostrophic_velocity(ro)[0]),
            "v_geo": (("i", "j", "k"), compute_geostrophic_velocity(ro)[1]),
            "ax_bc": (("i", "j", "k"), compute_pressure_gradient_acceleration(ro)[0]),
            "ay_bc": (("i", "j", "k"), compute_pressure_gradient_acceleration(ro)[1]),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "k": np.arange(KS),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
            "z_m": (("k",), Z_M),
            "kt1": (("i", "j"), kt1),
            "wet": (("i", "j"), wet.astype(int)),
        },
    )
    out_ds.to_netcdf("data/output/diagnostics/stage7.7A/initial_density_gradient.nc")
    print("   Saved initial_density_gradient.nc")

    # Save pressure gradient diagnostics
    ax_bc, ay_bc = compute_pressure_gradient_acceleration(ro)
    out_ds2 = xr.Dataset(
        {
            "ax_bc": (("i", "j", "k"), ax_bc),
            "ay_bc": (("i", "j", "k"), ay_bc),
            "accel_mag": (("i", "j", "k"), np.sqrt(ax_bc**2 + ay_bc**2)),
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
    out_ds2.to_netcdf(
        "data/output/diagnostics/stage7.7A/pressure_gradient_diagnostics.nc"
    )
    print("   Saved pressure_gradient_diagnostics.nc")

    # Save velocity growth / CFL diagnostics
    cfl_data = {}
    for U_ms in [0.002, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0, 1000.0]:
        U_cms = U_ms * 100.0
        cfl_data[f"cfl_U{U_ms}"] = U_cms * DT1 / DX_CM
        cfl_data[f"dt_req_U{U_ms}"] = DX_CM / U_cms if U_cms > 0 else np.inf

    with open("data/output/diagnostics/stage7.7A/cfl_diagnostics.json", "w") as f:
        json.dump(cfl_data, f, indent=2, default=str)
    print("   Saved cfl_diagnostics.json")

    # Save instability location (placeholder for velocity growth tracking)
    # This will be populated after running diagnostic model runs

    # Save synthetic vs realistic comparison
    comparison = {}
    for k in range(KS):
        mask = wet & (kt1 > k)
        dT_syn_dx, dT_syn_dy = compute_horizontal_gradients(T_syn[:, :, k])
        dT_real_dx, dT_real_dy = compute_horizontal_gradients(T[:, :, k])
        dS_syn_dx, dS_syn_dy = compute_horizontal_gradients(S_syn[:, :, k])
        dS_real_dx, dS_real_dy = compute_horizontal_gradients(S[:, :, k])
        dro_syn_dx, dro_syn_dy = compute_horizontal_gradients(ro_syn[:, :, k])
        dro_real_dx, dro_real_dy = compute_horizontal_gradients(ro[:, :, k])

        for name, real_dx, real_dy, syn_dx, syn_dy in [
            ("dT", dT_real_dx, dT_real_dy, dT_syn_dx, dT_syn_dy),
            ("dS", dS_real_dx, dS_real_dy, dS_syn_dx, dS_syn_dy),
            ("dro", dro_real_dx, dro_real_dy, dro_syn_dx, dro_syn_dy),
        ]:
            real_mag = np.sqrt(real_dx**2 + real_dy**2)
            syn_mag = np.sqrt(syn_dx**2 + syn_dy**2)
            comparison[f"{name}_level_{k+1}"] = {
                "real_max": float(np.nanmax(real_mag[mask])),
                "syn_max": (
                    float(np.nanmax(syn_mag[mask]))
                    if np.any(np.isfinite(syn_mag[mask]))
                    else 0.0
                ),
                "real_mean": float(np.nanmean(real_mag[mask])),
                "syn_mean": (
                    float(np.nanmean(syn_mag[mask]))
                    if np.any(np.isfinite(syn_mag[mask]))
                    else 0.0
                ),
            }

    with open(
        "data/output/diagnostics/stage7.7A/synthetic_vs_realistic_comparison.json", "w"
    ) as f:
        json.dump(comparison, f, indent=2, default=str)
    print("   Saved synthetic_vs_realistic_comparison.json")

    print("\n=== Initial Condition Analysis Complete ===")


if __name__ == "__main__":
    main()
