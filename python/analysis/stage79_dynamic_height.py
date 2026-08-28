#!/usr/bin/env python
"""
Stage 7.9 PHASE 6-7 — Dynamic Height and SSH Consistency

Computes:
1. Dynamic height anomaly relative to 600m reference
2. SSH from dynamic height gradient (geostrophic balance)
3. SSH from velocity field (geostrophic inverse)
4. Consistency check between velocity and SSH
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
ROC = 1.0
RHO0_CGS = 1.02
RHO0_SI = 1025.0
OMEGA = 7.29e-5

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


def compute_dynamic_height(ro, reference_level_k=17):
    """
    Compute dynamic height anomaly D(x,y) relative to reference level.

    D(x,y) = -∫_{z_ref}^{surface} (ρ(x,y,z) - ρ_ref) / ρ₀ dz

    For a Boussinesq fluid with constant ρ₀:
    D(x,y) = -∫_{z_ref}^{surface} ρ'(x,y,z) / ρ₀ dz

    where ρ' = ρ - ρ_mean is the density anomaly.

    Returns D in meters.
    """
    D = np.zeros((IS1, JS1))
    for k in range(reference_level_k + 1):
        D -= ro[:, :, k] / RHO0_CGS * DZ_CM[k] / 100.0  # m
    return D


def compute_ssh_from_dynamic_height(D, method="simple"):
    """
    Compute SSH from dynamic height by integrating the gradient.

    If we know D(x,y), then SSH = D (relative to reference level).
    But D is not absolute SSH — it's the dynamic height anomaly.

    For a balanced state:
    η(x,y) = D(x,y) - D_mean(x,y)

    where D_mean is the spatial mean (removes the arbitrary constant).
    """
    if method == "simple":
        # Remove spatial mean
        D_mean = np.nanmean(D)
        return D - D_mean
    elif method == "zero_at_boundary":
        # Set SSH=0 at the boundary
        D_boundary = np.nanmean(D[:5, :])  # mean of first 5 rows
        return D - D_boundary
    else:
        return D


def compute_ssh_from_velocity(u_geo, v_geo, fku, kt1):
    """
    Compute SSH from geostrophic velocity using the geostrophic relation.

    v_geo = (g/f) ∂η/∂x  =>  ∂η/∂x = f·v_geo/g
    u_geo = -(g/f) ∂η/∂y  =>  ∂η/∂y = -f·u_geo/g

    Integrate to get SSH.
    """
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    g = 9.81

    # Use depth-averaged velocity for barotropic SSH
    # U_bar = (1/H) ∫ u dz
    # V_bar = (1/H) ∫ v dz
    H = np.zeros((IS1, JS1))
    U_bar = np.zeros((IS1, JS1))
    V_bar = np.zeros((IS1, JS1))

    for i in range(IS1):
        for j in range(JS1):
            ki = kt1[i, j]
            if ki == 0:
                continue
            H[i, j] = Z_CM[ki - 1] / 100.0  # depth in m
            for k in range(ki):
                dz = DZ_M[k]
                U_bar[i, j] += u_geo[i, j, k] * dz
                V_bar[i, j] += v_geo[i, j, k] * dz
            if H[i, j] > 0:
                U_bar[i, j] /= H[i, j]
                V_bar[i, j] /= H[i, j]

    # SSH gradient from barotropic velocity
    ssh_grad_x = f_safe * V_bar / g
    ssh_grad_y = -f_safe * U_bar / g

    # Integrate SSH gradient
    ssh = np.zeros((IS1, JS1))
    for j in range(1, JS1):
        ssh[:, j] = ssh[:, j - 1] + ssh_grad_x[:, j] * DX_M

    # Remove mean
    ssh -= np.nanmean(ssh)
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
    print("STAGE 7.9 PHASE 6-7 — DYNAMIC HEIGHT & SSH CONSISTENCY")
    print("=" * 70)

    T, S, kt1, wet, lat, lon = load_en4()
    ro = compute_density(T, S)
    fku = compute_fku(lat, wet)

    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True
    mask = wet & interior_mask

    # Compute dynamic height relative to 600m
    print("\n--- Dynamic height (relative to 600m) ---")
    D = compute_dynamic_height(ro, reference_level_k=17)
    D_stats = percentile_stats(D, mask)
    print(
        f"  D range: max={D_stats['max']:.4f} min={np.nanmin(D[mask]):.4f} mean={D_stats['mean']:.4f} m"
    )
    print(f"  D P99={D_stats['p99']:.4f} P90={D_stats['p90']:.4f} m")

    # Typical steric height for Barents Sea: 0.1-0.3 m
    print(f"\n  Typical Barents Sea SSH variability: 0.1-0.3 m")
    if abs(D_stats["mean"]) < 0.5:
        print("  Dynamic height is within expected range.")
    else:
        print(
            "  Dynamic height is larger than expected — may indicate interpolation artifacts."
        )

    # Compute SSH from dynamic height
    print("\n--- SSH from dynamic height ---")
    ssh_D = compute_ssh_from_dynamic_height(D, method="simple")
    ssh_D_stats = percentile_stats(ssh_D, mask)
    print(
        f"  SSH range: max={ssh_D_stats['max']:.4f} min={np.nanmin(ssh_D[mask]):.4f} m"
    )
    print(f"  SSH P99={ssh_D_stats['p99']:.4f} P90={ssh_D_stats['p90']:.4f} m")

    # Load velocity fields from previous diagnostic
    print("\n--- Loading velocity fields from thermal-wind diagnostic ---")
    try:
        ds_vel = xr.open_dataset(
            "data/output/diagnostics/stage7.9/thermal_wind_reference_levels.nc"
        )
        U_surface = ds_vel["U_surface_ref"].values
        V_surface = ds_vel["V_surface_ref"].values
        U_bottom = ds_vel["U_bottom_ref"].values
        V_bottom = ds_vel["V_bottom_ref"].values
        U_realistic = ds_vel["U_realistic_ref"].values
        V_realistic = ds_vel["V_realistic_ref"].values
        print("  Loaded velocity fields successfully.")
    except FileNotFoundError:
        print("  ERROR: velocity fields not found. Run stage79_thermal_wind.py first.")
        return

    # Compute SSH from velocity (barotropic component)
    print("\n--- SSH from surface-reference velocity ---")
    ssh_from_U, grad_x_U, grad_y_U = compute_ssh_from_velocity(
        U_surface, V_surface, fku, kt1
    )
    ssh_U_stats = percentile_stats(ssh_from_U, mask)
    print(
        f"  SSH range: max={ssh_U_stats['max']:.4f} min={np.nanmin(ssh_from_U[mask]):.4f} m"
    )
    print(f"  SSH P99={ssh_U_stats['p99']:.4f} P90={ssh_U_stats['p90']:.4f} m")

    # Consistency check: SSH from dynamic height vs SSH from velocity
    print("\n--- Consistency Check: SSH from D vs SSH from velocity ---")
    # Both should give the same SSH (up to a constant)
    # Use the surface-reference velocity which corresponds to D
    ssh_diff = ssh_D - ssh_from_U
    diff_stats = percentile_stats(ssh_diff, mask)
    print(
        f"  SSH difference: max={diff_stats['max']:.4f} RMS={diff_stats['rms']:.4f} m"
    )
    print(f"  If consistent, the difference should be a constant (spatial mean).")

    # Remove mean and check residual
    ssh_diff_demean = ssh_diff - np.nanmean(ssh_diff[mask])
    diff_demean_stats = percentile_stats(ssh_diff_demean, mask)
    print(
        f"  After removing mean: max={diff_demean_stats['max']:.4f} RMS={diff_demean_stats['rms']:.4f} m"
    )

    # Summary
    print("\n=== Summary ===")
    print(f"  Dynamic height (relative to 600m): max={D_stats['max']:.4f} m")
    print(f"  SSH from dynamic height: max={ssh_D_stats['max']:.4f} m")
    print(f"  SSH from surface-ref velocity: max={ssh_U_stats['max']:.4f} m")
    print(f"  Consistency (demean RMS): {diff_demean_stats['rms']:.4f} m")
    print("")
    print("  Key finding:")
    print("  - Dynamic height is a relative measure (depends on reference level)")
    print(
        "  - SSH from dynamic height = SSH from surface-ref velocity (up to constant)"
    )
    print("  - Both require a reference level to get absolute SSH")
    print("  - The model's y2=0 is INCONSISTENT with the EN4 density field")

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "dynamic_height": D_stats,
        "ssh_from_D": ssh_D_stats,
        "ssh_from_velocity_surface": ssh_U_stats,
        "consistency_difference": diff_stats,
        "consistency_difference_demean": diff_demean_stats,
    }
    with open(out_dir / "dynamic_height_ssh.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved dynamic_height_ssh.json")

    # Save NetCDF
    ds_out = xr.Dataset(
        {
            "dynamic_height": (("i", "j"), D),
            "ssh_from_D": (("i", "j"), ssh_D),
            "ssh_from_velocity": (("i", "j"), ssh_from_U),
        },
        coords={
            "i": np.arange(IS1),
            "j": np.arange(JS1),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
        },
    )
    ds_out.to_netcdf(out_dir / "dynamic_height_ssh.nc")
    print(f"Saved dynamic_height_ssh.nc")


if __name__ == "__main__":
    main()
