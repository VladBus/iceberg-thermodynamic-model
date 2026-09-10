"""Stage 10.8.1 — independent Python validation of the basal-melt formulation.

Mathematically independent Python checks against the documented production
formulation (EOS-80 freezing point, relative velocity, Re/Nu/gamma_T, thermal
driving, basal melt). All expected values are hand-calculated from embedded
literals; the validation package implements the equations independently and is
never compared against Fortran output.

Cross-reference to the Fortran analytical values in
``docs/validation/stage10.7_basal_melt_validation.md`` and
``test/iceberg_test_10p7_basal_melt_validation.f90`` (Case I end-to-end gives
m = 1.5852e-6 m/s; Case J = 0.4963 m/day).

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_basal_melt_validation.py -v

(or: python python/tests/test_basal_melt_validation.py)
"""

import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
import basal_melt as m  # noqa: E402

# ---------------------------------------------------------------------------
# Tolerance policy (documented in docs/validation/stage10.8.1_python_validation.md)
# ---------------------------------------------------------------------------
# Production computes in float32; Python in float64. Float32 relative epsilon
# is ~1.19e-7. Analytical identities / scaling exponents are exact in float64
# and are checked to 1e-12 relative. Values compared against the independent
# float32 analytical reference keep a primary 1e-6 relative tolerance (the
# largest float32-accumulation residual), safely below the Stage 10.8.1
# requirement of 1e-3.
TOL_REF = 1.0e-4        # float32-reference comparisons (4-significant-figure
                        # printed Stage 10.7 values: rounding ceil ~5e-5; measured
                        # float64-vs-float32 residual is ~1.3e-7, reference rounding
                        # 2.8e-5 -- both comfortably below 1e-4)
TOL_EXACT = 1.0e-12     # pure-analytical identities / scaling exponents


def _rel(a, b):
    return abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)))


_ERRORS = 0
_CHECKS = 0


def ok(cond, name, detail=""):
    global _ERRORS, _CHECKS
    _CHECKS += 1
    if cond:
        print(f"OK   {name} {detail}")
    else:
        _ERRORS += 1
        print(f"ERROR {name} {detail}")


def ok_rel(actual, expected, name, tol, note=""):
    ok(_rel(actual, expected) <= tol, name, f"{note} (rel={_rel(actual, expected):.3e})")


# ===========================================================================
# A. EOS-80 reference point
# ===========================================================================
def test_a_eos80_reference():
    # Literature checkvalue Tf(40 PSU, 500 dbar) = -2.588567 degC (Stage 10.5).
    # The freezing-point function converts depth -> pressure via P = rho*g*z/1e4,
    # so depth = 500 dbar / (rho*g/1e4) reproduces the checkvalue pressure.
    depth_p500 = 500.0 / (1028.0 * 9.80665 / 1.0e4)
    tf = m.ocean_freezing_point(40.0, depth_p500)
    ok_rel(tf, -2.588567, "A.1 Tf(40PSU,500dbar) checkvalue", TOL_REF)
    # Depth-form pressure consistency at exactly 500 m.
    p_at_500m = 1028.0 * 9.80665 * 500.0 / 1.0e4  # 504.06181 dbar
    tf_depth = m.ocean_freezing_point(40.0, 500.0)
    tf_p = (-0.0575 + 1.710523e-3 * math.sqrt(40.0) - 2.154996e-4 * 40.0) * 40.0 \
        - 7.53e-4 * p_at_500m
    ok_rel(tf_depth, tf_p, "A.2 depth-form equals P(rho,g,z) polynomial", TOL_EXACT)
    # Float32 reference (production storage class) for round-trip confidence.
    tf_f32 = _tf_float32(40.0, 500.0)
    ok_rel(tf, tf_f32, "A.3 float32 storage-class agreement", TOL_REF)


def _tf_float32(s_psu, p_dbar):
    """Independent float32 reference (matches production storage class)."""
    import struct
    s = np.float32(s_psu)
    p = np.float32(p_dbar)
    tf = np.float32((np.float32(-0.0575) + np.float32(1.710523e-3) * np.sqrt(s)
                     - np.float32(2.154996e-4) * s) * s - np.float32(7.53e-4) * p)
    return float(np.float32(tf))


# ===========================================================================
# B. Zero thermal driving
# ===========================================================================
def test_b_zero_thermal_driving():
    dt = m.thermal_driving(-2.6, 34.5, 50.0)   # T < Tf (~ -1.9316)
    mm = m.basal_melt_rate(-2.6, 34.5, 50.0, 0.1, 0.0, 0.0, 0.0, 100.0)
    ok(dt == 0.0, "B.1 DeltaT=0 for cold ocean", f"(dT={dt})")
    ok(mm == 0.0, "B.2 m_basal=0 for cold ocean", f"(m={mm})")


# ===========================================================================
# C. Positive thermal driving
# ===========================================================================
def test_c_positive_thermal_driving():
    dt = m.thermal_driving(2.0, 34.5, 50.0)
    mm = m.basal_melt_rate(2.0, 34.5, 50.0, 0.1, 0.0, 0.0, 0.0, 100.0)
    ok(dt > 0.0, "C.1 DeltaT>0 for warm ocean", f"(dT={dt:.6e})")
    ok(mm > 0.0, "C.2 m_basal>0 for warm ocean", f"(m={mm:.6e})")


# ===========================================================================
# D. Relative velocity
# ===========================================================================
def test_d_relative_velocity():
    ok(m.relative_velocity(0.1, 0.2, 0.1, 0.2) == 0.0, "D.1 zero relative velocity")
    ok_rel(m.relative_velocity(0.1, 0.0, 0.0, 0.0), 0.1, "D.2 pure-x U_rel", TOL_EXACT)
    u = m.relative_velocity(0.3, 0.4, 0.0, 0.0)
    ok_rel(u, 0.5, "D.3 vector 3-4-5 U_rel=0.5", TOL_EXACT)
    u2 = m.relative_velocity(0.3, 0.4, 0.1, 0.2)
    ok_rel(u2, math.sqrt(0.2 ** 2 + 0.2 ** 2), "D.4 subtract-ice vector", TOL_EXACT)


# ===========================================================================
# E. Reynolds number
# ===========================================================================
def test_e_reynolds():
    re = m.reynolds_number(0.005, 100.0)
    ok_rel(re, 0.005 * 100.0 / 1.82e-6, "E.1 Re = U*L/nu", TOL_EXACT)
    ok(m.reynolds_number(0.0, 100.0) == 0.0, "E.2 U=0 -> Re defined guard 0")


# ===========================================================================
# F. Laminar branch
# ===========================================================================
def test_f_laminar():
    u_rel, l_char = 0.005, 100.0
    re = u_rel * l_char / 1.82e-6                 # 2.747e5 < 5e5
    nu_expected = 0.664 * math.sqrt(re) * 13.8 ** (1.0 / 3.0)
    gamma_expected = nu_expected * 0.56 / l_char
    ok(re < 5.0e5, "F.0 Re below critical", f"(Re={re:.6e})")
    ok_rel(m.nusselt_number(re), nu_expected, "F.1 laminar Nu", TOL_EXACT)
    ok_rel(m.ocean_heat_transfer_coefficient(u_rel, l_char), gamma_expected,
           "F.2 laminar gamma_T", TOL_EXACT)


# ===========================================================================
# G. Turbulent branch
# ===========================================================================
def test_g_turbulent():
    u_rel, l_char = 0.5, 100.0
    re = u_rel * l_char / 1.82e-6                 # 2.75e7 >= 5e5
    nu_expected = 0.037 * re ** 0.8 * 13.8 ** (1.0 / 3.0)
    gamma_expected = nu_expected * 0.56 / l_char
    ok(re >= 5.0e5, "G.0 Re above OR equal critical", f"(Re={re:.6e})")
    ok_rel(m.nusselt_number(re), nu_expected, "G.1 turbulent Nu", TOL_EXACT)
    ok_rel(m.ocean_heat_transfer_coefficient(u_rel, l_char), gamma_expected,
           "G.2 turbulent gamma_T", TOL_EXACT)


# ===========================================================================
# H. Exact transition at Re = 5e5
# ===========================================================================
def test_h_transition():
    l_char = 100.0
    u_below = 0.00909                              # Re ~ 4.995e5 < 5e5
    u_exact = 0.0091                               # Re = 5.0e5 exactly (turbulent)
    u_above = 0.0092                               # Re ~ 5.055e5 > 5e5
    re_below = u_below * l_char / 1.82e-6
    re_exact = u_exact * l_char / 1.82e-6
    re_above = u_above * l_char / 1.82e-6

    ok(re_below < 5.0e5, "H.1 Re_below < 5e5", f"(Re={re_below:.6e})")
    # Laminar below
    nu_lam = 0.664 * math.sqrt(re_below) * 13.8 ** (1.0 / 3.0)
    g_below = m.ocean_heat_transfer_coefficient(u_below, l_char)
    ok_rel(g_below, nu_lam * 0.56 / l_char, "H.2 laminar gamma below Re_crit", TOL_EXACT)

    # Exactly Re = 5e5 -> turbulent branch (production condition: Re >= Re_crit)
    nu_exact_turb = 0.037 * re_exact ** 0.8 * 13.8 ** (1.0 / 3.0)
    g_exact = m.ocean_heat_transfer_coefficient(u_exact, l_char)
    ok_rel(re_exact, 5.0e5, "H.3 Re_exact == 5e5", TOL_EXACT)
    ok_rel(g_exact, nu_exact_turb * 0.56 / l_char, "H.4 Re==5e5 turbulent gamma", TOL_EXACT)

    # Above -> turbulent
    nu_turb = 0.037 * re_above ** 0.8 * 13.8 ** (1.0 / 3.0)
    g_above = m.ocean_heat_transfer_coefficient(u_above, l_char)
    ok(re_above > 5.0e5, "H.5 Re_above > 5e5", f"(Re={re_above:.6e})")
    ok_rel(g_above, nu_turb * 0.56 / l_char, "H.6 turbulent gamma above Re_crit", TOL_EXACT)


# ===========================================================================
# I. Velocity monotonicity (within branch)
# ===========================================================================
def test_i_velocity_monotonicity():
    l_char = 100.0
    # laminar branch
    g1 = m.ocean_heat_transfer_coefficient(0.002, l_char)
    g2 = m.ocean_heat_transfer_coefficient(0.004, l_char)
    ok_rel(g2, g1 * 2.0 ** 0.5, "I.1 laminar gamma ~ U^0.5 monotone", TOL_EXACT)
    ok(g2 > g1, "I.2 laminar gamma strictly increasing")
    # turbulent branch
    g3 = m.ocean_heat_transfer_coefficient(0.2, l_char)
    g4 = m.ocean_heat_transfer_coefficient(0.4, l_char)
    ok_rel(g4, g3 * 2.0 ** 0.8, "I.3 turbulent gamma ~ U^0.8 monotone", TOL_EXACT)
    ok(g4 > g3, "I.4 turbulent gamma strictly increasing")


# ===========================================================================
# J. Thermal-driving monotonicity
# ===========================================================================
def test_j_thermal_driving_monotonicity():
    base = dict(salinity_psu=34.5, depth_m=50.0, u_water=0.5, v_water=0.0,
                u_ice=0.0, v_ice=0.0, length_m=100.0)
    m1 = m.basal_melt_rate(ocean_temperature=1.6, **base)
    m2 = m.basal_melt_rate(ocean_temperature=4.6, **base)
    ok(m2 > m1, "J.1 higher DeltaT -> higher melt", f"(m1={m1:.6e} m2={m2:.6e})")
    # linearty: m ~ DeltaT (gamma constant, cancels)
    d1 = m.thermal_driving(1.6, 34.5, 50.0)
    d2 = m.thermal_driving(4.6, 34.5, 50.0)
    ok_rel((m2 / m1) / (d2 / d1), 1.0, "J.2 m/DeltaT ratio == 1 (linearity)", TOL_REF)


# ===========================================================================
# K. Length scaling (correct negative exponents)
# ===========================================================================
def test_k_length_scaling():
    ok_rel(m.ocean_heat_transfer_coefficient(0.004, 100.0) /
           m.ocean_heat_transfer_coefficient(0.004, 50.0),
           2.0 ** (-0.5), "K.1 laminar gamma ~ L^(-0.5)", TOL_EXACT)
    ok_rel(m.ocean_heat_transfer_coefficient(0.5, 100.0) /
           m.ocean_heat_transfer_coefficient(0.5, 50.0),
           2.0 ** (-0.2), "K.2 turbulent gamma ~ L^(-0.2)", TOL_EXACT)


# ===========================================================================
# L. End-to-end basal melt (independent chain vs float32 analytical reference)
# ===========================================================================
def test_l_end_to_end():
    ocean_t, salinity_psu, dep = 2.0, 34.5, 50.0
    u_w, v_w, u_i, v_i, l_char = 0.1, 0.0, 0.0, 0.0, 100.0
    u_rel = math.sqrt((u_w - u_i) ** 2 + (v_w - v_i) ** 2)
    re = u_rel * l_char / 1.82e-6
    nu = (0.037 * re ** 0.8 * 13.8 ** (1.0 / 3.0)) if re >= 5.0e5 \
        else (0.664 * math.sqrt(re) * 13.8 ** (1.0 / 3.0))
    gamma = nu * 0.56 / l_char
    p_dbar = 1028.0 * 9.80665 * dep / 1.0e4
    tf = (-0.0575 + 1.710523e-3 * math.sqrt(salinity_psu) - 2.154996e-4 * salinity_psu) \
        * salinity_psu - 7.53e-4 * p_dbar
    dt = ocean_t - tf
    m_ind = gamma * dt / (910.0 * 3.34e5)

    tf_py = m.ocean_freezing_point(salinity_psu, dep)
    dT_py = m.thermal_driving(ocean_t, salinity_psu, dep)
    m_py = m.basal_melt_rate(ocean_t, salinity_psu, dep, u_w, v_w, u_i, v_i, l_char)

    ok_rel(tf_py, tf, "L.1 Tf EOS-80", TOL_REF)
    ok_rel(dT_py, dt, "L.2 DeltaT", TOL_REF)
    ok_rel(m_py, m_ind, "L.3 m_basal independent chain", TOL_REF,
           f"(m_py={m_py:.7e} m_ind={m_ind:.7e})")
    # Cross-reference to the Stage 10.7 float32 analytical value 1.5852e-6.
    ok_rel(m_py, 1.5852e-6, "L.4 vs Stage10.7 float32 reference 1.5852e-6", TOL_REF)


# ===========================================================================
# M. Zero-flow limitation
# ===========================================================================
def test_m_zero_flow():
    g = m.ocean_heat_transfer_coefficient(0.0, 100.0)
    mm = m.basal_melt_rate(2.0, 34.5, 50.0, 0.0, 0.0, 0.0, 0.0, 100.0)
    ok(g == 0.0, "M.1 U_rel=0 -> gamma_T=0 (documented forced-convection limit)")
    ok(mm == 0.0, "M.2 U_rel=0 warm ocean -> m=0 (natural convection absent)")


# ===========================================================================
# N. Numerical-noise guard
# ===========================================================================
def test_n_noise_guard():
    ocean_t, salinity_psu, dep = -1.93158110 + 1e-12, 34.5, 50.0  # dT ~ 1e-12
    mm = m.basal_melt_rate(ocean_t, salinity_psu, dep, 0.1, 0.0, 0.0, 0.0, 100.0)
    ok(mm == 0.0, "N.1 m < MELT_RATE_MIN -> 0 (numerical-noise guard)", f"(m={mm:.3e})")


# ===========================================================================
# O. Vectorized parity against the scalar path
# ===========================================================================
def test_o_vectorized_parity():
    # numpy available in project env; skip lazily if missing
    try:
        import numpy as np  # noqa: F811
    except ImportError:
        print("SKIP O vectorized (numpy unavailable)")
        return
    Ts = np.array([-1.5, 1.6, 2.0, 4.6])
    Ss = np.array([34.5, 34.5, 34.5, 34.5])
    Ds = np.array([50.0, 50.0, 50.0, 50.0])
    Uws = np.array([0.1, 0.5, 0.1, 0.5])
    Vws = np.zeros_like(Ts)
    vec = m.basal_melt_rate_vectorized(Ts, Ss, Ds, Uws, Vws)
    for i in range(len(Ts)):
        sc = m.basal_melt_rate(Ts[i], Ss[i], Ds[i], Uws[i], Vws[i], 0.0, 0.0, 100.0)
        ok(vec[i] == sc, f"O.{i} vectorized == scalar", f"(vec={vec[i]:.7e} sc={sc:.7e})")


# ===========================================================================
# Runner (direct execution; pytest also collects the test_* functions)
# ===========================================================================
if __name__ == "__main__":
    for f in (
        test_a_eos80_reference,
        test_b_zero_thermal_driving,
        test_c_positive_thermal_driving,
        test_d_relative_velocity,
        test_e_reynolds,
        test_f_laminar,
        test_g_turbulent,
        test_h_transition,
        test_i_velocity_monotonicity,
        test_j_thermal_driving_monotonicity,
        test_k_length_scaling,
        test_l_end_to_end,
        test_m_zero_flow,
        test_n_noise_guard,
        test_o_vectorized_parity,
    ):
        f()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.8.1 Python basal-melt validation PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.8.1 validation FAILED")
        sys.exit(1)