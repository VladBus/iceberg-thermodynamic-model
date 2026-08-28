#!/usr/bin/env python
"""
Stage 7.9 PHASE 21-22 — Zero-Gradient and Linear Density Analytic Tests

These are validation tests for the thermal-wind implementation.

Test A: Zero density gradient
- ρ = constant everywhere
- Expected: thermal-wind shear = 0
- With u_ref=0, v_ref=0: u=0, v=0 everywhere
- With u_ref=0.1, v_ref=0.05: u=0.1, v=0.05 everywhere

Test B: Linear density field
- ρ = ρ₀ + ax + by + cz
- Expected thermal-wind:
  ∂v/∂z = (g/(ρ₀·f)) · a
  ∂u/∂z = -(g/(ρ₀·f)) · b
"""

import numpy as np
import json
from pathlib import Path

# Model parameters
IS = 132
JS = 104
IS1 = IS + 1
JS1 = JS + 1
KS = 18
DX_M = 13890.0
G_M = 9.81
RHO0_SI = 1025.0
OMEGA = 7.29e-5

Z_M = np.array(
    [
        2.5,
        5.0,
        7.5,
        12.5,
        17.5,
        25.0,
        40.0,
        50.0,
        62.5,
        75.0,
        100.0,
        125.0,
        175.0,
        225.0,
        275.0,
        350.0,
        450.0,
        550.0,
    ]
)

DZ_M = np.zeros(KS)
DZ_M[0] = Z_M[0]
for k in range(1, KS):
    DZ_M[k] = Z_M[k] - Z_M[k - 1]


def eckart_density_anomaly(T, S):
    """Eckart EOS (not used in analytic tests, but for consistency)"""
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def compute_fku_uniform(lat_val=74.5):
    """Compute uniform Coriolis parameter"""
    return 2 * OMEGA * np.sin(np.deg2rad(lat_val))


def compute_density_gradient_si(ro_3d):
    """Compute horizontal density gradients using 4-point stencil"""
    grad_x = np.zeros((IS1, JS1, KS))
    grad_y = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        ro_si = ro_3d[:, :, k] * 1000.0  # Convert to kg/m^3
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
        grad_x[:, :, k] = delta_ro_x / (2.0 * DX_M)
        grad_y[:, :, k] = delta_ro_y / (2.0 * DX_M)

    return grad_x, grad_y


def thermal_wind_with_reference(ro_3d, f_val, reference_level_k, u_ref=0.0, v_ref=0.0):
    """Thermal wind with reference level (SI units)"""
    grad_x, grad_y = compute_density_gradient_si(ro_3d)
    f_safe = f_val if abs(f_val) > 1e-12 else np.nan

    U = np.zeros((IS1, JS1, KS))
    V = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        if k == reference_level_k:
            U[:, :, k] = u_ref
            V[:, :, k] = v_ref
        elif k < reference_level_k:
            dzs = np.array([DZ_M[m] for m in range(k, reference_level_k)])
            integral_x = np.sum(
                grad_x[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            integral_y = np.sum(
                grad_y[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            V[:, :, k] = v_ref + (G_M / (RHO0_SI * f_safe)) * integral_x
            U[:, :, k] = u_ref - (G_M / (RHO0_SI * f_safe)) * integral_y
        else:
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
            V[:, :, k] = v_ref - (G_M / (RHO0_SI * f_safe)) * integral_x
            U[:, :, k] = u_ref + (G_M / (RHO0_SI * f_safe)) * integral_y

    return U, V


def main():
    print("=" * 70)
    print("STAGE 7.9 PHASE 21-22 — ANALYTIC VALIDATION TESTS")
    print("=" * 70)

    f_val = compute_fku_uniform()

    # ===== Test A: Zero density gradient =====
    print("\n--- Test A: Zero density gradient ---")
    ro_zero = np.zeros((IS1, JS1, KS))  # ρ = 0 everywhere (constant)

    # With u_ref=0, v_ref=0
    U_A, V_A = thermal_wind_with_reference(
        ro_zero, f_val, reference_level_k=10, u_ref=0.0, v_ref=0.0
    )
    max_u_A = np.max(np.abs(U_A))
    max_v_A = np.max(np.abs(V_A))
    print(f"  u_ref=0, v_ref=0: max|U|={max_u_A:.2e}, max|V|={max_v_A:.2e} m/s")
    test_A1 = max_u_A < 1e-10 and max_v_A < 1e-10
    print(f"  PASS: {test_A1}")

    # With u_ref=0.1, v_ref=0.05
    U_A2, V_A2 = thermal_wind_with_reference(
        ro_zero, f_val, reference_level_k=10, u_ref=0.1, v_ref=0.05
    )
    max_u_A2 = np.max(np.abs(U_A2 - 0.1))
    max_v_A2 = np.max(np.abs(V_A2 - 0.05))
    print(
        f"  u_ref=0.1, v_ref=0.05: max|u-0.1|={max_u_A2:.2e}, max|v-0.05|={max_v_A2:.2e} m/s"
    )
    test_A2 = max_u_A2 < 1e-10 and max_v_A2 < 1e-10
    print(f"  PASS: {test_A2}")

    # ===== Test B: Linear density field =====
    print("\n--- Test B: Linear density field ρ = ρ₀ + ax + by + cz ---")
    # Create linear density field
    a = 1e-7  # kg/m^3 per m (x-gradient)
    b = 2e-7  # kg/m^3 per m (y-gradient)
    c = -1e-6  # kg/m^3 per m (z-gradient, stable)

    ro_linear = np.zeros((IS1, JS1, KS))
    for k in range(KS):
        for i in range(IS1):
            for j in range(JS1):
                x = j * DX_M
                y = i * DX_M
                z = Z_M[k]
                # ro in g/cm^3: ro = (a*x + b*y + c*z) / 1000
                ro_linear[i, j, k] = (a * x + b * y + c * z) / 1000.0

    # Expected thermal wind:
    # ∂v/∂z = (g/(ρ₀·f)) · a
    # ∂u/∂z = -(g/(ρ₀·f)) · b
    dv_dz_expected = (G_M / (RHO0_SI * f_val)) * a
    du_dz_expected = -(G_M / (RHO0_SI * f_val)) * b
    print(f"  Expected dv/dz = {dv_dz_expected:.2e} 1/s")
    print(f"  Expected du/dz = {du_dz_expected:.2e} 1/s")

    # Compute with reference at k=0
    U_B, V_B = thermal_wind_with_reference(
        ro_linear, f_val, reference_level_k=0, u_ref=0.0, v_ref=0.0
    )

    # Check vertical shear
    dv_dz_numerical = np.diff(V_B[:, :, :], axis=2) / np.diff(
        Z_M[np.newaxis, np.newaxis, :], axis=2
    )
    du_dz_numerical = np.diff(U_B[:, :, :], axis=2) / np.diff(
        Z_M[np.newaxis, np.newaxis, :], axis=2
    )

    # Average over interior points
    interior = np.zeros((IS1, JS1), dtype=bool)
    interior[2 : IS + 1, 2 : JS + 1] = True
    # dv_dz_numerical shape: (IS1, JS1, KS-1) = (133, 105, 17)
    # Create 3D mask
    mask_3d = np.broadcast_to(interior[:, :, np.newaxis], dv_dz_numerical.shape)
    dv_dz_masked = dv_dz_numerical[mask_3d]
    du_dz_masked = du_dz_numerical[mask_3d]
    dv_dz_mean = np.mean(dv_dz_masked[: 5 * interior.sum()])  # first 5 levels
    du_dz_mean = np.mean(du_dz_masked[: 5 * interior.sum()])
    print(f"  Numerical dv/dz (mean, first 5 levels) = {dv_dz_mean:.2e} 1/s")
    print(f"  Numerical du/dz (mean, first 5 levels) = {du_dz_mean:.2e} 1/s")

    # Relative error
    dv_dz_error = abs(dv_dz_mean - dv_dz_expected) / abs(dv_dz_expected) * 100
    du_dz_error = abs(du_dz_mean - du_dz_expected) / abs(du_dz_expected) * 100
    print(f"  Relative error dv/dz: {dv_dz_error:.2f}%")
    print(f"  Relative error du/dz: {du_dz_error:.2f}%")

    test_B = dv_dz_error < 5.0 and du_dz_error < 5.0
    print(f"  PASS (< 5% error): {test_B}")

    # ===== Summary =====
    print("\n=== Summary ===")
    results = {
        "test_A_zero_gradient": {
            "u_ref_0": bool(test_A1),
            "u_ref_01": bool(test_A2),
        },
        "test_B_linear_density": {
            "dv_dz_error_pct": float(dv_dz_error),
            "du_dz_error_pct": float(du_dz_error),
            "pass": bool(test_B),
        },
    }

    out_dir = Path("data/output/diagnostics/stage7.9")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "analytic_validation.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved analytic_validation.json")

    if test_A1 and test_A2 and test_B:
        print("\n  ALL ANALYTIC TESTS PASS")
    else:
        print("\n  SOME ANALYTIC TESTS FAIL")


if __name__ == "__main__":
    main()
