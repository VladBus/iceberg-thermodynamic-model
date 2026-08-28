#!/usr/bin/env python
"""
Stage 7.8 — Energy budget analysis.

Compares the initial kinetic energy for different initialization modes:
- Canonical drift (0.002 m/s)
- Stage 7.7C geostrophic (up to 60 m/s)
- Geostrophic with sigma=5 smoothing (~6 m/s)

Shows the excess energy injected by unphysical initializations.
"""

import numpy as np
import xarray as xr
import json
from pathlib import Path
from scipy.ndimage import gaussian_filter

# Model parameters
IS = 132
JS = 104
IS1 = IS + 1
JS1 = JS + 1
KS = 18
DX_CM = 1389000.0
G_CM = 981.0
ROC = 1.0
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

DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]

# Density of seawater
RHO_WATER = 1.02  # g/cm^3


def eckart_density_anomaly(T, S):
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def compute_density(T, S):
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_kinetic_energy_per_unit_area(u2_cms, v2_cms, map1_cm, kt1):
    """
    Compute total kinetic energy per unit area [erg/cm^2 = 0.1 J/m^2].
    KE = 0.5 * rho * integral(U^2 + V^2) dV
    Per unit area: KE/A = 0.5 * rho * integral(U^2 + V^2) dz
    """
    IS1, JS1, KS = u2_cms.shape
    ke = 0.0
    for j in range(2, JS + 1):
        for i in range(2, IS + 1):
            ki = kt1[i, j]
            if ki == 0:
                continue
            hht = map1_cm[i, j]
            if abs(hht - 8888.0) < 1e-8:
                continue
            for k in range(1, ki + 1):
                kk = k - 1  # 0-based index
                u2 = u2_cms[i, j, kk] ** 2  # cm^2/s^2
                v2 = v2_cms[i, j, kk] ** 2
                # Layer thickness
                if k == ki:
                    if ki > 1:
                        dz = hht - 0.5 * (Z_CM[ki - 1] + Z_CM[ki - 2])
                    else:
                        dz = hht
                else:
                    dz = DZ_CM[k - 1] if k > 1 else Z_CM[0]
                # Guard against negative dz
                if dz < 0:
                    dz = DZ_CM[kk] if kk < KS else Z_CM[0]
                ke += 0.5 * RHO_WATER * (u2 + v2) * dz  # erg/cm^2 per cell

    return ke  # erg/cm^2 total


def compute_geostrophic_velocity(ro, fku, smooth_sigma=0):
    """Compute model-style geostrophic velocity with optional smoothing."""
    if smooth_sigma > 0:
        for k in range(KS):
            mask_k = np.ones((IS1, JS1), dtype=bool)
            ro[:, :, k] = gaussian_filter(ro[:, :, k] * mask_k, sigma=smooth_sigma)

    sum_x_cum = np.zeros((IS1, JS1, KS))
    sum_y_cum = np.zeros((IS1, JS1, KS))
    c8 = 0.25 / DX_CM

    for k in range(KS):
        delta_ro_x = np.zeros((IS1, JS1))
        delta_ro_x[1:IS1, 1:JS1] = (
            ro[0:IS, 1:JS1, k]
            + ro[1:IS1, 1:JS1, k]
            - ro[0:IS, 0:JS, k]
            - ro[1:IS1, 0:JS, k]
        )
        delta_ro_y = np.zeros((IS1, JS1))
        delta_ro_y[1:IS1, 1:JS1] = (
            ro[0:IS, 0:JS, k]
            + ro[0:IS, 1:JS1, k]
            - ro[1:IS1, 0:JS, k]
            - ro[1:IS1, 1:JS1, k]
        )
        if k == 0:
            sum_x_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_y
        else:
            sum_x_cum[:, :, k] = sum_x_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = sum_y_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_y

    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -2.0 * G_CM / ROC * sum_y_cum / f_safe[:, :, np.newaxis]
    V_geo = 2.0 * G_CM / ROC * sum_x_cum / f_safe[:, :, np.newaxis]

    # Replace NaN with 0
    U_geo = np.nan_to_num(U_geo, nan=0.0)
    V_geo = np.nan_to_num(V_geo, nan=0.0)

    return U_geo, V_geo


def main():
    print("=" * 70)
    print("STAGE 7.8 — ENERGY BUDGET ANALYSIS")
    print("=" * 70)

    # Load EN4
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)
    S = ds["salinity_mass_fraction"].values.astype(np.float64)
    kt1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    lat = ds["lat"].values

    # Load map1 (depth) from KOORD.DAT
    # Approximate: use hhh.bar
    map1_cm = np.full((IS1, JS1), 10000.0)  # default 100m
    try:
        with open("hhh.bar", "r") as f:
            lines = f.readlines()
        idx = 0
        for jjj in range(7):
            header = lines[idx]
            idx += 1
            data_lines = lines[idx : idx + 7]
            idx += 7
            for il, line in enumerate(data_lines):
                vals = [int(line[k : k + 5]) for k in range(0, 75, 5)]
                for jc, v in enumerate(vals):
                    j = jjj * 15 + jc + 1  # 1-indexed
                    i = il + 1
                    if i < IS1 and j < JS1:
                        if v == 8:
                            map1_cm[i, j] = 8888.0
                        else:
                            map1_cm[i, j] = v * 100.0
    except FileNotFoundError:
        print("Warning: hhh.bar not found, using default depth")

    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan

    ro = compute_density(T, S)

    results = {}

    # 1. Canonical drift
    print("\n--- Mode 1: Canonical drift (u=0.20, v=0.10 cm/s) ---")
    u2_drift = np.zeros((IS1, JS1, KS))
    v2_drift = np.zeros((IS1, JS1, KS))
    for j in range(1, JS1):
        for i in range(1, IS1):
            if kt1[i, j] > 0:
                for k in range(min(KS, kt1[i, j])):
                    u2_drift[i, j, k] = 0.20  # cm/s
                    v2_drift[i, j, k] = 0.10

    speed_max = np.sqrt(u2_drift**2 + v2_drift**2).max() / 100.0
    ke = compute_kinetic_energy_per_unit_area(u2_drift, v2_drift, map1_cm, kt1)
    print(f"  max U = {speed_max:.4f} m/s")
    print(f"  Total KE = {ke:.2e} erg/cm^2 = {ke*0.1:.2e} J/m^2")
    results["canonical_drift"] = {
        "max_U_m_s": float(speed_max),
        "total_KE_erg_cm2": float(ke),
        "total_KE_J_m2": float(ke * 0.1),
    }

    # 2. Stage 7.7C geostrophic (full, no smoothing)
    print("\n--- Mode 2: Stage 7.7C geostrophic (full depth) ---")
    U_geo, V_geo = compute_geostrophic_velocity(ro.copy(), fku, smooth_sigma=0)
    speed_max = np.sqrt(U_geo**2 + V_geo**2).max() / 100.0
    ke = compute_kinetic_energy_per_unit_area(U_geo, V_geo, map1_cm, kt1)
    print(f"  max U = {speed_max:.2f} m/s")
    print(f"  Total KE = {ke:.2e} erg/cm^2 = {ke*0.1:.2e} J/m^2")
    results["geostrophic_full"] = {
        "max_U_m_s": float(speed_max),
        "total_KE_erg_cm2": float(ke),
        "total_KE_J_m2": float(ke * 0.1),
    }

    # 3. Geostrophic with sigma=2 smoothing
    print("\n--- Mode 3: Geostrophic with sigma=2 smoothing ---")
    U_geo_s2, V_geo_s2 = compute_geostrophic_velocity(ro.copy(), fku, smooth_sigma=2)
    speed_max = np.sqrt(U_geo_s2**2 + V_geo_s2**2).max() / 100.0
    ke = compute_kinetic_energy_per_unit_area(U_geo_s2, V_geo_s2, map1_cm, kt1)
    print(f"  max U = {speed_max:.2f} m/s")
    print(f"  Total KE = {ke:.2e} erg/cm^2 = {ke*0.1:.2e} J/m^2")
    results["geostrophic_sigma2"] = {
        "max_U_m_s": float(speed_max),
        "total_KE_erg_cm2": float(ke),
        "total_KE_J_m2": float(ke * 0.1),
    }

    # 4. Geostrophic with sigma=5 smoothing
    print("\n--- Mode 4: Geostrophic with sigma=5 smoothing ---")
    U_geo_s5, V_geo_s5 = compute_geostrophic_velocity(ro.copy(), fku, smooth_sigma=5)
    speed_max = np.sqrt(U_geo_s5**2 + V_geo_s5**2).max() / 100.0
    ke = compute_kinetic_energy_per_unit_area(U_geo_s5, V_geo_s5, map1_cm, kt1)
    print(f"  max U = {speed_max:.2f} m/s")
    print(f"  Total KE = {ke:.2e} erg/cm^2 = {ke*0.1:.2e} J/m^2")
    results["geostrophic_sigma5"] = {
        "max_U_m_s": float(speed_max),
        "total_KE_erg_cm2": float(ke),
        "total_KE_J_m2": float(ke * 0.1),
    }

    # Summary
    print("\n=== Energy Budget Summary ===")
    print(f"{'Mode':<30} {'max U (m/s)':<14} {'KE (J/m^2)':<14}")
    print("-" * 60)
    for name, r in results.items():
        print(f"{name:<30} {r['max_U_m_s']:<14.2f} {r['total_KE_J_m2']:<14.2e}")

    # Key finding
    print("\n=== Key Finding ===")
    ke_ratio = results["geostrophic_full"]["total_KE_J_m2"] / max(
        results["canonical_drift"]["total_KE_J_m2"], 1e-30
    )
    print(
        f"  Stage 7.7C geostrophic injects {ke_ratio:.0e} times more KE than canonical drift"
    )
    print(f"  This excess energy must be dissipated by the model's diffusion,")
    print(f"  which is not designed to handle such large initial gradients.")
    print(f"")
    print(f"  With sigma=5 smoothing (removing interpolation artifacts),")
    print(
        f"  the excess is reduced to {results['geostrophic_sigma5']['total_KE_J_m2'] / results['canonical_drift']['total_KE_J_m2']:.0e} times."
    )

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.8")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "energy_budget.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved energy_budget.json")


if __name__ == "__main__":
    main()
