#!/usr/bin/env python3
"""
Stage 10.12 — Independent Python validation of prognostic internal thermal
evolution of the iceberg.

Independent float64 replica in python/validation/internal_thermal.py vs
embedded literals; production Fortran code is NOT invoked here. Cross-language
contract checks pin the float32 anchors produced by the passing Fortran test
`iceberg_test_10p12_thermal_evolution` (17/17 OK):
    C_int(H=50)  float32 = 94594496.0   (float64 exact 94594500.0, ulp=8)
    q_cond(B.1)          = 0.44 W/m^2
    C.5 clamp            = -100.0 degC with bound flag True

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_internal_thermal_evolution.py
"""

import math
import sys
from pathlib import Path

# Portable import bootstrap: python/tests + ../validation, robust in a clean
# GitHub Actions checkout (no reliance on developer PYTHONPATH or cwd).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))

import internal_thermal as s1012  # noqa: E402

# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

_CHECKS = 0
_ERRORS = 0


def ok(condition: bool, label: str, detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if condition:
        print(f"OK   {label}" + (f" ({detail})" if detail else ""))
    else:
        print(f"ERROR {label}" + (f" ({detail})" if detail else ""))
        _ERRORS += 1


def ok_rel(actual: float, expected: float, label: str, tol: float = 1.0e-6, detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if expected == 0.0:
        rel = abs(actual)
    else:
        rel = abs(actual - expected) / abs(expected)
    if rel < tol:
        print(f"OK   {label} (rel={rel:.2e})" + (f" ({detail})" if detail else ""))
    else:
        print(
            f"ERROR {label}: actual={actual:.6e} expected={expected:.6e} rel={rel:.2e}"
            + (f" ({detail})" if detail else "")
        )
        _ERRORS += 1


# ============================================================
# A. THERMAL CAPACITY:  H_int = max(H - H_EFF, H_MIN_INT),
#                       C_int = rho_i * c_i * H_int
# ============================================================

def test_a_capacity() -> None:
    # A.1: H=50 -> H_int=49.5, C_int = 910*2100*49.5 = 94594500.0 (float64)
    c_int, h_int = s1012.compute_thermal_capacity(50.0)
    ok_rel(h_int, 49.5, "A.1 H_int = H - H_EFF")
    ok_rel(c_int, 94594500.0, "A.1 C_int = rho_i*c_i*H_int (float64 exact)")
    # Cross-language contract: Fortran float32 anchor 94594496.0
    # (94594500 is exactly halfway between float32 ulp=8 multiples; IEEE
    # round-to-even gives 94594496). Tolerance 1e-6 covers the 4.23e-8 diff.
    ok_rel(c_int, 94594496.0, "A.1b cross-language float32 anchor", 1.0e-6)

    # A.2: H=1.0 -> H_int = max(0.5, 0.5) = 0.5, C_int = 910*2100*0.5 = 955500
    c_int, h_int = s1012.compute_thermal_capacity(1.0)
    ok_rel(h_int, 0.5, "A.2 H=1.0 -> H_int = H_EFF boundary")
    ok_rel(c_int, 955500.0, "A.2 C_int(H=1.0) = 955500")

    # A.3: H=0.1 -> H_int clamped to H_MIN_INT = 0.5 (never negative)
    c_int, h_int = s1012.compute_thermal_capacity(0.1)
    ok(h_int == s1012.H_MIN_INT, "A.3 H=0.1 -> H_int clamped to H_MIN_INT",
       f"(H_int={h_int})")
    ok(c_int == 910.0 * 2100.0 * 0.5, "A.3b C_int on clamp branch")

    # A.4: monotone in H (larger berg -> larger capacity)
    ok(s1012.compute_thermal_capacity(100.0)[0] > s1012.compute_thermal_capacity(50.0)[0],
       "A.4 C_int monotone in H")


# ============================================================
# B. CONDUCTIVE COUPLING:  q_cond = 2*K_ICE*(T_s - T_i)/H
# ============================================================

def test_b_conductive() -> None:
    # B.1: anchor from Fortran B.1: T_s=-5, T_i=-10, H=50 -> 0.44 W/m^2
    q = s1012.compute_conductive_coupling(-5.0, -10.0, 50.0)
    ok_rel(q, 0.44, "B.1 q_cond anchor 0.44 W/m^2")

    # B.2: T_s == T_i -> q_cond = 0
    ok(s1012.compute_conductive_coupling(-10.0, -10.0, 50.0) == 0.0,
       "B.2 q_cond=0 when T_surface = T_ice")

    # B.3: sign: colder surface -> negative (cooling)
    q = s1012.compute_conductive_coupling(-15.0, -10.0, 50.0)
    ok_rel(q, -0.44, "B.3 q_cond sign (cold surface)")

    # B.4: 1/H scaling: doubling H halves |q_cond|
    q100 = s1012.compute_conductive_coupling(-5.0, -10.0, 100.0)
    ok_rel(q100, 0.22, "B.4 q_cond proportional to 1/H")

    # B.5: linearity in the temperature difference
    qa = s1012.compute_conductive_coupling(-4.0, -10.0, 50.0)
    ok_rel(qa, 2.0 * s1012.K_ICE * 6.0 / 50.0, "B.5 q_cond linear in dT")

    # B.6: literal-identity form (embedded literals only)
    q = s1012.compute_conductive_coupling(-5.0, -10.0, 50.0)
    ok_rel(q, 2.0 * 2.2 * 5.0 / 50.0, "B.6 literal identity 2*2.2*5/50")


# ============================================================
# C. EXPLICIT EULER UPDATE + CLAMPS
# ============================================================

def test_c_update() -> None:
    dt = 3600.0
    H = 50.0

    # C.1: zero fluxes -> T_ice constant, bound False
    t, dT, c, h, bound = s1012.update_internal_temperature(-10.0, H, dt, 0.0, 0.0)
    ok(t == -10.0 and dT == 0.0 and not bound, "C.1 zero fluxes -> constant")

    # C.2: positive q_cond -> warming (sign convention)
    t, dT, c, h, bound = s1012.update_internal_temperature(-10.0, H, dt, 1000.0, 0.0)
    ok(t > -10.0 and dT > 0.0, "C.2 positive q_cond -> warming", f"(T={t:.4f})")

    # C.3: q_bot > 0 -> cooling
    t, dT, c, h, bound = s1012.update_internal_temperature(-10.0, H, dt, 0.0, 1000.0)
    ok(t < -10.0 and dT < 0.0, "C.3 q_bot>0 -> cooling", f"(T={t:.4f})")

    # C.4: upper bound clamp at 0 degC with bound flag
    t, dT, c, h, bound = s1012.update_internal_temperature(-1.0, H, dt, 30000.0, 0.0)
    ok(t == s1012.T_ICE_MAX and bound, "C.4 upper clamp to 0 degC, bound=True",
       f"(T={t})")

    # C.5: lower bound clamp at -100 degC with bound flag
    # dT = -30000*3600/94594500 = -1.1421 K -> T_new = -100.142 < -100
    t, dT, c, h, bound = s1012.update_internal_temperature(-99.0, H, dt, -30000.0, 0.0)
    ok(t == s1012.T_ICE_MIN and bound, "C.5 lower clamp to -100 degC, bound=True",
       f"(T={t})")

    # C.6: dt=0 -> no change (production early-return)
    t, dT, c, h, bound = s1012.update_internal_temperature(-15.0, H, 0.0, 1000.0, 0.0)
    ok(t == -15.0 and dT == 0.0 and not bound, "C.6 dt=0 -> no change")

    # C.6b: negative dt -> no change (production guard dt <= 0)
    t, dT, c, h, bound = s1012.update_internal_temperature(-15.0, H, -1.0, 1000.0, 0.0)
    ok(t == -15.0 and dT == 0.0 and not bound, "C.6b dt<0 -> no change (guard)")

    # C.7: large dt stable (no NaN/Inf), clamps at the limit
    t, dT, c, h, bound = s1012.update_internal_temperature(-10.0, H, 1.0e12, -1.0e6, 0.0)
    ok(math.isfinite(t) and t == s1012.T_ICE_MIN and bound,
       "C.7 large dt stable, clamped", f"(T={t})")

    # C.8: repeatability — same inputs, same outputs
    r1 = s1012.update_internal_temperature(-20.0, 30.0, 7200.0, 250.0, 50.0)
    r2 = s1012.update_internal_temperature(-20.0, 30.0, 7200.0, 250.0, 50.0)
    ok(r1 == r2, "C.8 repeatability")

    # C.9: energy conservation for a non-clamped step:
    #      C_int * (T_new - T_ice) == (q_cond - q_bot) * dt
    q_cond, q_bot, dt9 = 250.0, 50.0, 7200.0
    t, dT, c, h, bound = s1012.update_internal_temperature(-20.0, 30.0, dt9, q_cond, q_bot)
    ok(not bound and abs(c * (t - (-20.0)) - (q_cond - q_bot) * dt9) < 1.0e-6,
       "C.9 energy conservation C_int*dT = (q_cond-q_bot)*dt")


# ============================================================
# D. BASAL HEAT FLUX COUPLING
# ============================================================

def test_d_basal_flux() -> None:
    # D.1: T_B <= T_ice -> q_bot = 0 (no energy sink when interface not warmer)
    ok(s1012.basal_heat_flux(1.0e-6, -5.0, -5.0) == 0.0, "D.1 T_B = T_ice -> q_bot=0")
    ok(s1012.basal_heat_flux(1.0e-6, -6.0, -5.0) == 0.0, "D.1b T_B < T_ice -> q_bot=0")

    # D.2: q_bot > 0 only when T_B > T_ice; linear in m_basal
    q1 = s1012.basal_heat_flux(1.0e-6, -1.0, -10.0)
    q2 = s1012.basal_heat_flux(2.0e-6, -1.0, -10.0)
    ok(q1 > 0.0, "D.2 T_B > T_ice -> q_bot > 0", f"(q_bot={q1:.3e})")
    ok_rel(q2, 2.0 * q1, "D.2b q_bot linear in m_basal")

    # D.3: literal identity: m*rho_i*CP_ICE_3EQ*max(T_B - T_i, 0)
    q = s1012.basal_heat_flux(4.067e-6, -1.9, -10.0)
    expected = 4.067e-6 * 910.0 * 2009.0 * 8.1
    ok_rel(q, expected, "D.3 literal identity m*rho_i*c_i*dT")

    # D.4: magnitude plausibility: q_bot in O(1-100) W/m^2 for observed melts
    # 4.067e-6 m/s (Stage 10.10 end-to-end anchor) with dT=8.1 K -> ~60 W/m^2
    ok(0.1 < q < 1.0e4, "D.4 q_bot magnitude plausible", f"(q_bot={q:.1f} W/m^2)")


# ============================================================
# E. CROSS-LANGUAGE CONTRACTS + UNIT PLAUSIBILITY
# ============================================================

def test_e_contracts() -> None:
    # E.1: per-hour temperature change is tiny for realistic surface gradient
    # (same premise as Fortran C.5 root-cause finding)
    dT_hour = 1000.0 * 3600.0 / 94594500.0
    ok(1.0e-3 < dT_hour < 0.1, "E.1 realistic dT per hour is small", f"({dT_hour:.2e} K)")

    # E.2: full-chain contract vs Fortran anchors: warm surface scenario
    # T_s=0 (melting surface), T_i=-10, H=50, dt=3600:
    #   q_cond = 2*2.2*10/50 = 0.88; dT/dt = 0.88/94594500
    q = s1012.compute_conductive_coupling(0.0, -10.0, 50.0)
    ok_rel(q, 0.88, "E.2 q_cond(T_s=0, T_i=-10, H=50) = 0.88 W/m^2")
    t, dT, c, h, bound = s1012.update_internal_temperature(-10.0, 50.0, 3600.0, q, 0.0)
    expected_t = -10.0 + 0.88 * 3600.0 / 94594500.0
    ok_rel(t, expected_t, "E.2b full-chain T_new matches analytic", 1.0e-9)
    ok(not bound, "E.2c realistic step does not clamp")

    # E.3: units — C_int in J/(K m^2): rho[kg/m^3]*c[J/(kg K)]*h[m]
    c, h = s1012.compute_thermal_capacity(30.0)
    ok_rel(c, 910.0 * 2100.0 * (30.0 - 0.5), "E.3 C_int dimensional composition")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    test_a_capacity()
    test_b_conductive()
    test_c_update()
    test_d_basal_flux()
    test_e_contracts()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.12 internal thermal evolution validation PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.12 internal thermal evolution validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
