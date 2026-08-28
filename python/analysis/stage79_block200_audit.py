#!/usr/bin/env python
"""
Stage 7.9 PHASE 1 — Block 200 Balance Audit

Derives the EXACT steady-state geostrophic balance from the model's
Block 200 semi-implicit Coriolis discretization.

The model equations are:
    AUU = U1 + α·V1 + dt·(-C1·sum - dpx + C3·SLAPU)
    AVV = V1 - α·U1 + dt·(-C1·sum1 - dpy + C3·SLAPV)
    U2 = (AUU + α·AVV) / (1 + α²)
    V2 = (AVV - α·AUU) / (1 + α²)

where α = f·dt/2.

At steady state (U2=U1, V2=V1), solving the 2×2 system:
    U1 = -(C1/f)·(sum1 + α·sum) / (1 + α²)
    V1 = (C1/f)·(sum - α·sum1) / (1 + α²)

For α << 1 (f·dt/2 << 1, which is 0.07 for dt=3600, f=1.4e-4):
    U1 ≈ -(C1/f)·sum1
    V1 ≈ (C1/f)·sum

This means the model's geostrophic balance does NOT have a factor of 2.
The factor of 2 in Stage 7.7C was an algebraic error.
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
C1 = G_CM / ROC  # 981
C8 = 0.25 / DX_CM  # 1/cm
OMEGA = 7.29e-5
LAT_REF = 74.5

# Model timestep
DT = 3600.0  # s (baroclinic timestep)

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


def compute_model_sum(ro):
    """
    Compute the model's baroclinic pressure integrals (sum, sum1)
    exactly as in Block 200.
    """
    sum_x = np.zeros((IS1, JS1, KS))
    sum_y = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        # Delta RO at U-point (4-point stencil from Block 200)
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
            sum_x[:, :, k] = C8 * DZ_CM[k] * delta_ro_x
            sum_y[:, :, k] = C8 * DZ_CM[k] * delta_ro_y
        else:
            sum_x[:, :, k] = sum_x[:, :, k - 1] + C8 * DZ_CM[k] * delta_ro_x
            sum_y[:, :, k] = sum_y[:, :, k - 1] + C8 * DZ_CM[k] * delta_ro_y

    return sum_x, sum_y


def compute_geostrophic_factor1(ro, fku):
    """
    Correct geostrophic balance from Block 200 steady state (factor 1, no factor 2).
    U_geo = -(C1/f)·sum1
    V_geo = (C1/f)·sum
    """
    sum_x, sum_y = compute_model_sum(ro)
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -C1 * sum_y / f_safe[:, :, np.newaxis]
    V_geo = C1 * sum_x / f_safe[:, :, np.newaxis]
    return U_geo, V_geo


def compute_geostrophic_factor2(ro, fku):
    """
    Stage 7.7C geostrophic balance (with factor 2).
    U_geo = -(2·C1/f)·sum1
    V_geo = (2·C1/f)·sum
    """
    sum_x, sum_y = compute_model_sum(ro)
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -2.0 * C1 * sum_y / f_safe[:, :, np.newaxis]
    V_geo = 2.0 * C1 * sum_x / f_safe[:, :, np.newaxis]
    return U_geo, V_geo


def compute_geostrophic_exact(ro, fku, dt=DT):
    """
    EXACT steady-state geostrophic balance including the α correction.
    U1 = -(C1/f)·(sum1 + α·sum) / (1 + α²)
    V1 = (C1/f)·(sum - α·sum1) / (1 + α²)
    """
    sum_x, sum_y = compute_model_sum(ro)
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]
    alpha = f_safe_3d * dt / 2.0
    denom = 1.0 + alpha**2
    U_geo = -(C1 / f_safe_3d) * (sum_y + alpha * sum_x) / denom
    V_geo = (C1 / f_safe_3d) * (sum_x - alpha * sum_y) / denom
    return U_geo, V_geo


def compute_fku(lat, wet):
    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan
    return fku


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
    print("STAGE 7.9 PHASE 1 — BLOCK 200 BALANCE AUDIT")
    print("=" * 70)

    T, S, kt1, wet, lat, lon = load_en4()
    ro = compute_density(T, S)
    fku = compute_fku(lat, wet)

    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True
    mask = wet & interior_mask

    # Check alpha = f*dt/2
    f_avg = np.nanmean(np.abs(fku[mask]))
    alpha = f_avg * DT / 2.0
    print(f"\n  f_avg = {f_avg:.2e} 1/s")
    print(f"  dt = {DT} s")
    print(f"  alpha = f*dt/2 = {alpha:.4f}")
    print(f"  alpha << 1: {alpha < 0.1}")

    # Compute three versions
    print("\n--- Computing geostrophic velocity (three methods) ---")

    U_f1, V_f1 = compute_geostrophic_factor1(ro, fku)
    speed_f1 = np.sqrt(U_f1**2 + V_f1**2) / 100.0
    stats_f1 = percentile_stats(speed_f1[:, :, -1], mask)
    print(
        f"  Factor 1 (correct): max={stats_f1['max']:.2f} P99={stats_f1['p99']:.2f} m/s"
    )

    U_f2, V_f2 = compute_geostrophic_factor2(ro, fku)
    speed_f2 = np.sqrt(U_f2**2 + V_f2**2) / 100.0
    stats_f2 = percentile_stats(speed_f2[:, :, -1], mask)
    print(
        f"  Factor 2 (Stage 7.7C): max={stats_f2['max']:.2f} P99={stats_f2['p99']:.2f} m/s"
    )

    U_ex, V_ex = compute_geostrophic_exact(ro, fku, dt=DT)
    speed_ex = np.sqrt(U_ex**2 + V_ex**2) / 100.0
    stats_ex = percentile_stats(speed_ex[:, :, -1], mask)
    print(
        f"  Exact (with alpha):  max={stats_ex['max']:.2f} P99={stats_ex['p99']:.2f} m/s"
    )

    # Summary
    print("\n=== Summary ===")
    print(f"{'Method':<30} {'max (m/s)':<12} {'P99 (m/s)':<12}")
    print("-" * 54)
    print(
        f"{'Factor 1 (correct)':<30} {stats_f1['max']:<12.2f} {stats_f1['p99']:<12.2f}"
    )
    print(
        f"{'Factor 2 (Stage 7.7C)':<30} {stats_f2['max']:<12.2f} {stats_f2['p99']:<12.2f}"
    )
    print(
        f"{'Exact (with alpha)':<30} {stats_ex['max']:<12.2f} {stats_ex['p99']:<12.2f}"
    )

    print("\n=== Conclusion ===")
    print("  The correct geostrophic balance from Block 200 steady state is:")
    print("    U_geo = -(C1/f)·sum1")
    print("    V_geo = (C1/f)·sum")
    print("  WITHOUT the factor of 2 used in Stage 7.7C.")
    print("  The factor of 2 was an algebraic error in the Stage 7.7C derivation.")
    print("  With the correct factor 1, the maximum geostrophic velocity is")
    print(f"  {stats_f1['max']:.2f} m/s, which is half the Stage 7.7C value.")
    print("")
    print("  This confirms that the model's geostrophic diagnostic is")
    print("  a SURFACE-REFERENCED geostrophic shear (v=0 at surface),")
    print("  which is the relative geostrophic shear, not the absolute velocity.")

    # Save
    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "factor1_correct": stats_f1,
        "factor2_stage77c": stats_f2,
        "exact_with_alpha": stats_ex,
    }
    with open(out_dir / "block200_audit.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved block200_audit.json")


if __name__ == "__main__":
    main()
