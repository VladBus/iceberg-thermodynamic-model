#!/usr/bin/env python
"""
Stage 7.9 PHASE 8-9 — Barotropic Transport and Block 280 Consistency

Computes:
1. Barotropic transport from 3D velocity field: UP2 = Σ u2 * DZ1, VP2 = Σ v2 * DZ1
2. Block 280 consistency check: after Block 280, depth-integrated U2 should match UP2/HHT
3. Transport conservation check
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

DZ_CM = np.zeros(18)
DZ_CM[0] = Z_CM[0]
for k in range(1, 18):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]

DZ1_CM = np.zeros(18)
DZ1_CM[0] = 0.5 * (Z_CM[1] + Z_CM[0])
for k in range(1, 17):
    DZ1_CM[k] = 0.5 * (Z_CM[k + 1] - Z_CM[k - 1])
DZ1_CM[17] = 0.5 * (Z_CM[17] - Z_CM[16])


def eckart_density_anomaly(T, S):
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_product():
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)  # [°C], (133, 105, 18)
    S = ds["salinity_mass_fraction"].values.astype(np.float64)  # [frac]
    kt1 = ds["water_column_levels"].values.astype(np.int32)
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


def compute_barotropic_transport(u2, v2, kt1, map1_cm):
    """
    Compute barotropic transports UP2, VP2 from 3D velocity.

    UP2(i,j) = Σ_{k=1..ki} U2(i,j,k) * DZ1(k)  [cm^2/s]
    VP2(i,j) = Σ_{k=1..ki} V2(i,j,k) * DZ1(k)

    where ki = kk1(i,j) = number of wet levels at U/V point (i,j)
    DZ1 is the half-layer thickness.
    For bottom layer: DZ1(k=ki) = HHT - 0.5*(z(ki) + z(ki-1))
    """
    IS1 = kt1.shape[0]
    JS1 = kt1.shape[1]
    UP2 = np.zeros((IS1, JS1))
    VP2 = np.zeros((IS1, JS1))

    for j in range(1, JS1):
        for i in range(1, IS1):
            ki = kt1[i, j]
            if ki == 0:
                continue
            hht = map1_cm[i, j]
            if abs(hht - 8888.0) < 1e-8:
                continue

            u_sum = 0.0
            v_sum = 0.0
            for k in range(ki):
                k1 = k + 1  # 1-based
                if k == ki - 1:  # bottom layer (0-based)
                    if ki > 1:
                        dzz = hht - 0.5 * (Z_CM[ki - 1] + Z_CM[ki - 2])
                    else:
                        dzz = hht
                else:
                    dzz = DZ1_CM[k]
                u_sum += u2[i, j, k] * dzz
                v_sum += v2[i, j, k] * dzz

            UP2[i, j] = u_sum
            VP2[i, j] = v_sum

    # Boundary conditions
    UP2[:, 0] = UP2[:, 1]
    UP2[:, -1] = UP2[:, -2]
    UP2[0, :] = UP2[1, :]
    UP2[-1, :] = UP2[-2, :]
    VP2[:, 0] = VP2[:, 1]
    VP2[:, -1] = VP2[:, -2]
    VP2[0, :] = VP2[1, :]
    VP2[-1, :] = VP2[-2, :]

    return UP2, VP2


def apply_block280_correction(u2, v2, UP2, VP2, kt1, map1_cm):
    """
    Apply Block 280 correction: add constant to each level so that
    depth-averaged U2/V2 matches UP2/VP2 / HHT.

    sum = [-Σ U2(k)*DZ1(k) + 0.5*(UP2(I,J)+UP2(I-1,J))] / HHT
    U2(i,j,k) = U2(i,j,k) + sum
    """
    IS1 = kt1.shape[0]
    JS1 = kt1.shape[1]

    u2_corr = u2.copy()
    v2_corr = v2.copy()

    for j in range(1, JS1):
        for i in range(1, IS1):
            ki = kt1[i, j]
            if ki == 0:
                continue
            i2 = i - 1
            hht = map1_cm[i, j]
            if abs(hht - 8888.0) < 1e-8:
                continue

            # Compute depth-integrated U2 and V2
            u_sum = 0.0
            v_sum = 0.0
            for k in range(ki):
                k1 = k + 1
                if k == ki - 1:
                    if ki > 1:
                        dzz = hht - 0.5 * (Z_CM[ki - 1] + Z_CM[ki - 2])
                    else:
                        dzz = hht
                else:
                    dzz = DZ1_CM[k]
                u_sum += u2[i, j, k] * dzz
                v_sum += v2[i, j, k] * dzz

            # Barotropic transport at U-point (average of two adjacent T-points)
            up2_avg = 0.5 * (UP2[i, j] + UP2[i - 1, j])
            vp2_avg = 0.5 * (VP2[i, j] + VP2[i, j - 1])

            # Correction
            sum_u = (-u_sum + up2_avg) / hht
            sum_v = (-v_sum + VP2[i, j]) / hht  # Note: VP2 uses j-1 for V-point

            for k in range(ki):
                u2[i, j, k] += sum_u
                v2[i, j, k] += sum_v

    return u2, v2


def check_block280_consistency(u2, v2, UP2, VP2, kt1, map1_cm):
    """
    Check Block 280 conservation: depth-integrated U2 should equal UP2/HHT.
    Returns max relative error.
    """
    errors_u = []
    errors_v = []

    for j in range(1, kt1.shape[1]):
        for i in range(1, kt1.shape[0]):
            ki = kt1[i, j]
            if ki == 0:
                continue
            i2 = i - 1
            hht = map1_cm[i, j]
            if abs(hht - 8888.0) < 1e-8:
                continue

            u_sum = 0.0
            v_sum = 0.0
            for k in range(kt1[i, j]):
                k1 = k + 1
                if k == ki - 1:
                    if ki > 1:
                        dzz = map1_cm[i, j] - 0.5 * (Z_CM[ki - 1] + Z_CM[ki - 2])
                    else:
                        dzz = map1_cm[i, j]
                else:
                    dzz = DZ1_CM[k]
                u_sum += u2[i, j, k] * dzz
                v_sum += v2[i, j, k] * dzz

            up2_avg = 0.5 * (UP2[i, j] + UP2[i - 1, j])
            vp2_avg = 0.5 * (VP2[i, j] + VP2[i, j - 1])

            u_mean = u_sum / map1_cm[i, j]
            v_mean = v_sum / map1_cm[i, j]

            up2_mean = 0.5 * (UP2[i, j] + UP2[i - 1, j]) / hht
            vp2_mean = 0.5 * (VP2[i, j] + VP2[i, j - 1]) / hht

            if abs(u_mean) > 1e-10:
                errors_u.append(abs(u_mean - up2_mean) / abs(u_mean))
            if abs(v_mean) > 1e-10:
                errors_v.append(abs(v_mean - vp2_mean) / abs(v_mean))

    return {
        "max_rel_error_u": max(errors_u) if errors_u else 0.0,
        "max_rel_error_v": max(errors_v) if errors_v else 0.0,
        "mean_rel_error_u": np.mean(errors_u) if errors_u else 0.0,
        "mean_rel_error_v": np.mean(errors_v) if errors_v else 0.0,
    }


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
    print("STAGE 7.9 PHASE 8-9 — BAROTROPIC TRANSPORT & BLOCK 280 CONSISTENCY")
    print("=" * 70)

    T, S, kt1, wet, lat, lon = load_en4_product()

    # Compute density
    ro = compute_density(T, S)

    # Load velocity fields from thermal-wind diagnostic
    ds_vel = xr.open_dataset(
        "data/output/diagnostics/stage7.9/thermal_wind_reference_levels.nc"
    )
    U_bottom = ds_vel["U_bottom_ref"].values  # (133, 105, 18)
    V_bottom = ds_vel["V_bottom_ref"].values

    # Need map1 (HHT) - load from hhh.bar or approximate from kt1
    # For now, approximate map1 from kt1 * layer thickness
    map1_cm = np.zeros((133, 105))
    for i in range(133):
        for j in range(105):
            ki = kt1[i, j]
            if ki > 0:
                map1_cm[i, j] = Z_CM[ki - 1]  # approximate bottom depth
            else:
                map1_cm[i, j] = 8888.0

    # Test with bottom-reference velocity (Test B)
    u2 = ds_vel["U_bottom_ref"].values  # (i, j, k) = (133, 105, 18)
    v2 = ds_vel["V_bottom_ref"].values

    print("=" * 70)
    print("STAGE 7.9 PHASE 8-9 — BAROTROPIC TRANSPORT & BLOCK 280")
    print("=" * 70)

    # Compute barotropic transport from 3D velocity
    print("\n--- Computing barotropic transport ---")
    UP2, VP2 = compute_barotropic_transport(u2, v2, kt1, map1_cm)

    # Stats
    interior = np.zeros((133, 105), dtype=bool)
    interior[2:133, 2:105] = True
    mask = (kt1 > 0) & (np.arange(133)[:, None] > 0) & (np.arange(105) > 0)

    up2_stats = {}
    vp2_stats = {}
    for name, arr in [("UP2", UP2), ("VP2", VP2)]:
        stats = {}
        vals = arr[kt1 > 0]
        vals = vals[np.isfinite(vals)]
        stats["max"] = float(np.max(np.abs(vals)))
        stats["mean"] = float(np.mean(np.abs(vals)))
        stats["p99"] = float(np.percentile(np.abs(vals), 99))
        print(
            f"  {name}: max={stats['max']:.2e} P99={np.percentile(np.abs(vals), 99):.2e} cm^2/s"
        )

    # Apply Block 280 correction
    print("\n--- Applying Block 280 correction ---")
    u2_corr, v2_corr = apply_block280_correction(
        u2.copy(), v2.copy(), UP2, VP2, kt1, map1_cm
    )

    # Check consistency before correction
    print("\n--- Block 280 consistency check ---")
    before = check_block280_consistency(u2, v2, UP2, VP2, kt1, map1_cm)

    # Apply Block 280 correction
    print("\n--- Applying Block 280 correction ---")
    u2_after, v2_after = apply_block280_correction(
        u2.copy(), v2.copy(), UP2, VP2, kt1, map1_cm
    )

    # Check consistency after correction
    after = check_block280_consistency(u2_after, v2_after, UP2, VP2, kt1, map1_cm)

    # Recompute after correction
    u2_corr_t = np.transpose(u2_after, (1, 2, 0))
    v2_corr_t = np.transpose(v2_after, (1, 2, 0))
    # Actually we need to recompute UP2/VP2 from corrected velocities
    # and check if the correction worked

    print("\n--- Consistency Results ---")
    print(
        f"  Before correction: max rel error U={before['max_rel_error_u']:.2e}, V={before['max_rel_error_v']:.2e}"
    )

    # Recompute transport from corrected velocity
    UP2_after, VP2_after = compute_barotropic_transport(
        u2_after, v2_after, kt1, map1_cm
    )
    after = check_block280_consistency(
        u2_after, v2_after, UP2_after, VP2_after, kt1, map1_cm
    )
    print(
        f"  After correction:  max rel error U={after['max_rel_error_u']:.2e}, V={after['max_rel_error_v']:.2e}"
    )

    # Transport statistics
    print("\n--- Transport Statistics ---")
    for name, arr in [
        ("UP2_before", UP2),
        ("UP2_after", UP2_after),
        ("VP2_before", VP2),
        ("VP2_after", VP2_after),
    ]:
        vals = arr[kt1 > 0]
        vals = vals[np.isfinite(vals)]
        print(
            f"  {name}: max={np.max(np.abs(arr[kt1 > 0])):.2e} mean={np.mean(np.abs(arr[kt1 > 0])):.2e} cm^2/s"
        )

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "transport_before": {
            "UP2_max": float(np.max(np.abs(UP2[kt1 > 0]))),
            "VP2_max": float(np.max(np.abs(VP2[kt1 > 0]))),
        },
        "consistency_before": before,
        "consistency_after": after,
    }

    with open("data/output/diagnostics/stage7.9/block280_consistency.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved block280_consistency.json")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
