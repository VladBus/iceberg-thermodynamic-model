"""Stage 10.10 + 10.10.1 — independent Python validation of the three-equation
interface.

Checks A-T against the production closure reproduced in
``python/validation/three_equation.py``. The expected values are hand-computed
from embedded literals (EOS-80 coefficients, rho_w=1028, c_w=3974, rho_i=910,
L_f=3.34e5, c_i=2009, T_i=-10, K_T=1.1e-3, K_S=3.1e-5, H&J99 Table 1
gamma_T=1e-4, gamma_S=5.05e-7); nothing is compared against Fortran output
except two documented cross-language contract anchors (blocks C and L) that
quote the values produced by the Stage 10.10.1 Fortran test.

Block U is the Stage 10.10.1 mass/salt-convention correction: the salt budget
carries the ice/ocean density ratio rho_i/rho_w so that the meltwater flux
seen by the ocean is F_fw = (rho_i/rho_w)*m:

    rho_w*gamma_S*(S_w - S_B) = rho_i*m*S_B  =>  S_B = gamma_S*S_w/(gamma_S + r*m)

(reducing to the Stage 10.10 equal-density form only for rho_i/rho_w -> 1).
This is the MOM6 mom_ice_shelf / PISM / H&J99(Eq.4) convention.

This is validation, not calibration - no coefficient is adjusted.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_three_equation.py

"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))

import three_equation as te  # noqa: E402

DAY_S = 86400.0

_ERRORS = 0
_CHECKS = 0


def _rel(a, b):
    return abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)), 1e-300)


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
# A. EOS-80 freezing-point sanity (independent literals)
# ===========================================================================
def test_a_eos():
    p500_m = 500.0 * 1.0e4 / (te.RHO_WATER * te.GRAVITY)  # depth giving P=500 dbar
    tf = te.ocean_freezing_point(40.0, p500_m)
    ok_rel(tf, -2.588567, "A.1 UNESCO 500 dbar checkvalue", 1.0e-6)
    ok(abs(te.ocean_freezing_point(0.0, 0.0)) < 1.0e-12, "A.2 fresh water Tf=0")
    ok(te.ocean_freezing_point(35.0, 0.0) < te.ocean_freezing_point(30.0, 0.0),
       "A.3 Tf decreases with salinity")
    p_dbar = te.RHO_WATER * te.GRAVITY * 100.0 / 1.0e4
    df = te.ocean_freezing_point(34.5, 100.0) - te.ocean_freezing_point(34.5, 0.0)
    ok_rel(df, te.EOS_FP_BP * p_dbar, "A.4 depth pressure term", 1.0e-6,
           f"(BP*P={te.EOS_FP_BP * p_dbar:.6f})")


# ===========================================================================
# B. Transfer coefficients (J2010 Table 2)
# ===========================================================================
def test_b_transfer():
    u = 0.1
    gt, gs = te.transfer_coefficients(u)
    ok_rel(gt, te.THREE_EQ_KT * u, "B.1 gamma_T = K_T*U", 1.0e-12)
    ok_rel(gs, te.THREE_EQ_KS * u, "B.2 gamma_S = K_S*U", 1.0e-12)
    ok_rel(te.THREE_EQ_KT / te.THREE_EQ_KS, 1.1e-3 / 3.1e-5,
           "B.3 K_T/K_S ratio", 1.0e-12)
    ok_rel(te.THREE_EQ_KT, math.sqrt(0.0097) * 0.011,
           "B.4 sqrt(Cd)*Gamma_T consistency", 2.0e-2)
    ok(gs < gt, "B.5 gamma_S << gamma_T")


# ===========================================================================
# C. H&J99 canonical anchor (T_w=-1.85, S_w=34.5, gamma_T=1e-4, gamma_S=5.05e-7)
# ===========================================================================
def test_c_canonical():
    m, t_b, s_b = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7, t_ice=-10.0, use_conduction=True)
    ok(0.0 < m < 1.0e-7, "C.1 magnitude band", f"(m={m:.3e})")
    ok_rel(m, 1.043812814e-8, "C.2 cross-language contract with Fortran test", 1.0e-3)
    ok_rel(s_b, 33.880096396, "C.3 interface salinity (PSU)", 1.0e-3)
    ok_rel(t_b, -1.858146177, "C.4 interface temperature (degC)", 1.0e-3)
    tf_sw = te.ocean_freezing_point(34.5, 0.0)
    ok(tf_sw < t_b < -1.85, "C.5 T_B between Tf(S_w) and T_w")
    ok(0.0 < s_b < 34.5, "C.6 freshening: 0 < S_B < S_w")
    # Raw balance: |F(m)| << ocean flux (Eq. II residual)
    f_root = te._f_residual(-1.85, t_b, 1.0e-4, m, -10.0, True)
    flux = te.RHO_WATER * te.CP_SEAWATER * 1.0e-4 * (-1.85 - t_b)
    ok(abs(f_root) / max(abs(flux), 1.0e-12) < 1.0e-9,
       "C.7 heat-balance residual", f"(|F|/flux={abs(f_root)/flux:.2e})")
    # Salt balance Eq. III
    ok_rel(te._s_interface(5.05e-7, 34.5, m), s_b, "C.8 salt-balance identity", 1.0e-9)


# ===========================================================================
# D. Edges: no-flux / sub-freezing / zero gamma
# ===========================================================================
def test_d_edges():
    tf = te.ocean_freezing_point(34.5, 0.0)
    m, t_b, s_b = te.solve_three_equation_interface(-1.85, 34.5, 0.0, 0.0, 1.0e-4, 5.05e-7)
    ok(m == 0.0 and abs(t_b - tf) < 1e-9 and s_b == 34.5, "D.1 U_rel=0 -> m=0")
    m, t_b, s_b = te.solve_three_equation_interface(-1.85, 34.5, 0.0, 0.1, 0.0, 5.05e-7)
    ok(m == 0.0 and abs(t_b - tf) < 1e-9 and s_b == 34.5, "D.2 gamma_T=0 -> m=0")
    m, t_b, s_b = te.solve_three_equation_interface(tf - 0.5, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    ok(m == 0.0 and abs(t_b - tf) < 1e-9 and s_b == 34.5, "D.3 T_w<Tf -> m=0")


# ===========================================================================
# E. Fresh water (S_w=0) and no-salt-budget edges
# ===========================================================================
def test_e_fresh_gamma_s_zero():
    m, t_b, s_b = te.solve_three_equation_interface(1.0, 0.0, 0.0, 0.1, 1.0e-4, 5.05e-7)
    ok(m > 0.0 and s_b == 0.0 and abs(t_b) < 1e-9, "E.1 fresh water heat-only",
       f"(m={m:.3e})")
    m, t_b, s_b = te.solve_three_equation_interface(1.0, 34.5, 0.0, 0.1, 1.0e-4, 0.0)
    lat = te.RHO_ICE * (te.LATENT_HEAT + te.CP_ICE_3EQ * max(t_b - te.T_ICE, 0.0))
    m_exp = (te.RHO_WATER * te.CP_SEAWATER * 1.0e-4 * (1.0 - t_b)) / lat
    ok_rel(m, m_exp, "E.2 gamma_S=0 heat-only closed form", 1.0e-9)
    ok(s_b == 34.5, "E.3 gamma_S=0 keeps S_B=S_w")


# ===========================================================================
# F. Conduction term
# ===========================================================================
def test_f_conduction():
    m_on, _, _ = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7, t_ice=-10.0, use_conduction=True)
    m_off, _, _ = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7, t_ice=-10.0, use_conduction=False)
    ok(0.0 < m_on < m_off, "F.1 conduction reduces melt",
       f"(on={m_on:.3e} off={m_off:.3e})")
    ok(0.90 < m_on / m_off <= 1.0, "F.2 conduction effect size (~1% near-freezing)",
       f"(ratio={m_on/m_off:.3f})")


# ===========================================================================
# G. Scaling and bracketing
# ===========================================================================
def test_g_scaling():
    m1, _, _ = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    m2, _, _ = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.2, 2.0e-4, 1.01e-6)
    ok_rel(m1 / m2, 0.5, "G.1 linear U-scaling m(U)/m(2U)=0.5", 1.0e-6)
    # root bracketing: F must change sign across m
    f_lo = te._f_residual(-1.85, te.ocean_freezing_point(te._s_interface(5.05e-7, 34.5, 0.0), 0.0),
                          1.0e-4, 1e-12, -10.0, True)
    f_hi = te._f_residual(-1.85, te.ocean_freezing_point(te._s_interface(5.05e-7, 34.5, 1e-6), 0.0),
                          1.0e-4, 1e-3, -10.0, True)
    ok((f_lo > 0.0) != (f_hi > 0.0), "G.2 root bracketed by F(m)", f"({f_lo:.3e},{f_hi:.3e})")


# ===========================================================================
# H. Freezing-edge grind
# ===========================================================================
def test_h_freezing_edge():
    tf = te.ocean_freezing_point(34.5, 0.0)
    m, t_b, s_b = te.solve_three_equation_interface(tf, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    ok(m == 0.0, "H.1 T_w=Tf -> m=0")
    m, _, _ = te.solve_three_equation_interface(tf + 1.0e-4, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    ok(1.0e-12 < m < 1.0e-7, "H.2 T_w=Tf+1e-4 -> small positive m", f"(m={m:.3e})")


# ===========================================================================
# I. Pressure / depth monotonicity
# ===========================================================================
def test_i_depth():
    m0, _, _ = te.solve_three_equation_interface(0.0, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    m100, _, _ = te.solve_three_equation_interface(0.0, 34.5, 100.0, 0.1, 1.0e-4, 5.05e-7)
    m500, _, _ = te.solve_three_equation_interface(0.0, 34.5, 500.0, 0.1, 1.0e-4, 5.05e-7)
    ok(0.0 < m0 < m100 < m500, "I.1 melt increases with depth (fixed T: deeper Tf colder)")
    tf0 = te.ocean_freezing_point(34.5, 0.0)
    tf500 = te.ocean_freezing_point(34.5, 500.0)
    p500 = te.RHO_WATER * te.GRAVITY * 500.0 / 1.0e4
    ok_rel(tf0 - tf500, -te.EOS_FP_BP * p500, "I.2 Tf depth drop", 1.0e-6)


# ===========================================================================
# J. Warm-ocean band (production-scale)
# ===========================================================================
def test_j_warm_band():
    m, _, _ = te.three_equation_basal_melt(
        2.0, 34.5, 50.0, u_water=0.1)
    m_day = m * DAY_S
    ok(0.01 <= m_day <= 1.0, "J.1 warm-ocean in observed band (0.01-1 m/day)",
       f"(m={m_day:.3f} m/day)")


# ===========================================================================
# K. Wrapper vs raw solver consistency + guards
# ===========================================================================
def test_k_wrapper():
    # Wrapper matches raw solver for the warm end-to-end case
    m_raw, t_b, s_b = te.solve_three_equation_interface(2.0, 34.5, 50.0, 0.1, 1.1e-4, 3.1e-6)
    m_wrap, t_w, s_w = te.three_equation_basal_melt(2.0, 34.5, 50.0, u_water=0.1)
    ok_rel(m_raw, m_wrap, "K.1 wrapper == raw solve (warm)", 1.0e-6)
    ok(t_b > te.ocean_freezing_point(34.5, 50.0), "K.2 T_B above far-field Tf",
       f"(T_B={t_b:.4f}, Tf={te.ocean_freezing_point(34.5, 50.0):.4f})")
    # Thermal gate: sub-freezing -> guard returns exactly (0, Tf, S_w)
    tf = te.ocean_freezing_point(34.5, 50.0)
    m, t_b, s_b = te.three_equation_basal_melt(tf - 1.0, 34.5, 50.0, u_water=0.1)
    ok(m == 0.0 and abs(t_b - tf) < 1e-9 and s_b == 34.5, "K.3 sub-freezing gate")
    # MELT_RATE_MIN: tiny flux clipped to zero by wrapper
    m_tiny, _, _ = te.solve_three_equation_interface(tf + 1.0e-8, 34.5, 50.0, 0.1, 1.1e-4, 3.1e-6)
    ok(0.0 < m_tiny < te.MELT_RATE_MIN, "K.4 solver returns tiny positive below guard")
    m_c, t_c, s_c = te.three_equation_basal_melt(tf + 1.0e-8, 34.5, 50.0, u_water=0.1)
    ok(m_c == 0.0, "K.5 wrapper clips tiny melt to zero")


# ===========================================================================
# L. Cross-language production contract (L case of Fortran test)
#   T_w=2.0, S_w=34.5, depth=50, U_rel=0.1 -> m=3.99846886E-06
# ===========================================================================
def test_l_contract():
    m, t_b, s_b = te.three_equation_basal_melt(2.0, 34.5, 50.0, u_water=0.1)
    ok_rel(m, 4.067408105e-6, "L.1 production-end contract m (Fortran test L.2)", 1.0e-3)
    ok_rel(s_b, 15.961431974, "L.2 interface salinity S_B (PSU)", 1.0e-3)
    ok_rel(t_b, -0.901562565, "L.3 interface temperature T_B (degC)", 1.0e-3)
    tf = te.ocean_freezing_point(34.5, 50.0)
    ok(t_b > tf and 0.0 < s_b < 34.5 and m > 0.0, "L.4 freshening + supercooling-free interface")


# ===========================================================================
# M. Regime separation (baseline bulk vs three-equation are different closures)
# ===========================================================================
def test_m_regime_separation():
    from basal_melt import basal_melt_rate  # independent Stage 10.8.1 closure

    m3eq, _, _ = te.three_equation_basal_melt(2.0, 34.5, 50.0, u_water=0.1)
    mbulk = basal_melt_rate(2.0, 34.5, 50.0, 0.1, 0.0, 0.0, 0.0, 100.0)
    ok(m3eq > 0.0 and mbulk > 0.0, "M.1 both closures produce melt")
    ok(_rel(m3eq, mbulk) > 5.0e-2, "M.2 closures differ (different coefficients)",
       f"(m3eq={m3eq:.3e} mbulk={mbulk:.3e})")


# ===========================================================================
# N. Interface identity across conduction/pressure combos (regression guard)
# ===========================================================================
def test_n_regression_matrix():
    n_ok = True
    for t in (-1.2, 0.0, 1.5):
        for s in (28.0, 34.5, 35.0):
            for z in (0.0, 50.0, 200.0):
                for cond in (True, False):
                    gt, gs = te.transfer_coefficients(0.15)
                    m, t_b, s_b = te.solve_three_equation_interface(
                        t, s, z, 0.15, gt, gs, t_ice=-10.0, use_conduction=cond)
                    if not (math.isfinite(m) and math.isfinite(t_b) and math.isfinite(s_b)):
                        n_ok = False
                    if m > 0.0:
                        if not (0.0 < s_b < s and t_b > te.ocean_freezing_point(s, z)):
                            n_ok = False
    ok(n_ok, "N.1 3x3x2 grid: finite, bounded, freshened solutions")


# ===========================================================================
# O. Rapidity / determinism (validated closure is independent of grid)
# ===========================================================================
def test_o_determinism():
    args = (-1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7)
    m1 = te.solve_three_equation_interface(*args)
    m2 = te.solve_three_equation_interface(*args)
    ok(all(x == y for x, y in zip(m1, m2)), "O.1 deterministic solution")


# ===========================================================================
# T. Fresh-water convection floor note (documented limitation)
# ===========================================================================
def test_t_documented_limitation():
    m, t_b, s_b = te.solve_three_equation_interface(2.0, 34.5, 50.0, 0.0, 1e-4, 3.1e-6)
    ok(m == 0.0, "T.1 U_rel=0 -> no melt (natural convection NOT implemented)",
       "documented model limitation")


# ===========================================================================
# U. Stage 10.10.1: density-weighted salt budget
#    rho_w*gamma_S*(S_w - S_B) = rho_i*m*S_B  =>  S_B = gamma_S*S_w/(gamma_S + r*m)
#    with r = rho_i/rho_w = 910/1028 = 0.885214... (MOM6/PISM/H&J99 Eq.4)
# ===========================================================================
def test_u_mass_salt_convention():
    r = te.RHO_ICE_WATER_RATIO
    ok_rel(r, 910.0 / 1028.0, "U.1 density ratio rho_i/rho_w", 1.0e-12)
    ok(-1.0 < r < 1.0, "U.2 ice lighter than water: 0 < r < 1", f"(r={r:.6f})")

    # Analytic S_B from the corrected reduction satisfies the MASS salt budget.
    gamma_s = 5.05e-7
    s_w = 34.5
    for m_val in (1.0e-9, 1.0e-8, 1.0e-7, 4.0e-6):
        s_b = te._s_interface(gamma_s, s_w, m_val)
        lhs = te.RHO_WATER * gamma_s * (s_w - s_b)     # kg-salt/m2/s toward interface
        rhs = te.RHO_ICE * m_val * s_b                 # kg-salt/m2/s removed by meltwater
        ok_rel(lhs, rhs, "U.3 mass salt identity rho_w gS(Sw-SB)=rho_i m SB",
               1.0e-9, f"(m={m_val:.1e})")
        ok_rel(gamma_s * (s_w - s_b), r * m_val * s_b,
               "U.4 freshwater-flux form gS(Sw-SB)=F_fw*SB", 1.0e-9)

    # Bounding and monotonicity.
    s_b = te._s_interface(gamma_s, s_w, 1.0e-8)
    ok(0.0 < s_b < s_w, "U.5 fresh-water bounded: 0 < S_B < S_w", f"(S_B={s_b:.4f})")
    s_small = te._s_interface(gamma_s, s_w, 1.0e-16)
    ok(abs(s_small - s_w) / s_w < 1.0e-9, "U.6 m->0 limit: S_B->S_w")
    s_large = te._s_interface(gamma_s, s_w, 1.0e5)
    ok(s_large < 1.0e-9, "U.7 m>>gamma_S limit: S_B->0", f"(S_B={s_large:.2e})")
    m_seq = (1.0e-9, 1.0e-8, 1.0e-7, 1.0e-6)
    sbs = [te._s_interface(gamma_s, s_w, m_i) for m_i in m_seq]
    ok(all(a > b for a, b in zip(sbs, sbs[1:])), "U.8 S_B strictly decreasing in m")

    # Equal-density limit: rho_ratio=1 recovers the Stage 10.10 reduction.
    s_equal = te._s_interface(gamma_s, s_w, 1.0e-8, rho_ratio=1.0)
    ok_rel(s_equal, gamma_s * s_w / (gamma_s + 1.0e-8),
           "U.9 rho_ratio=1 recovers equal-density S_B", 1.0e-12)

    # Correction reduces freshening at a given m (r<1 -> S_B closer to S_w).
    s_corr = te._s_interface(gamma_s, s_w, 1.0e-8)
    ok(s_corr > s_equal, "U.10 density correction raises S_B vs equal-density",
       f"(S_B_corr={s_corr:.5f} S_B_equal={s_equal:.5f})")

    # Solved point automatically respects the corrected identity.
    m, t_b, s_b = te.solve_three_equation_interface(
        -1.85, 34.5, 0.0, 0.1, 1.0e-4, 5.05e-7, t_ice=-10.0, use_conduction=True)
    lhs = te.RHO_WATER * 5.05e-7 * (34.5 - s_b)
    rhs = te.RHO_ICE * m * s_b
    ok_rel(lhs, rhs, "U.11 solved canonical satisfies corrected salt budget", 1.0e-3)
    f_root = te._f_residual(-1.85, t_b, 1.0e-4, m, -10.0, True)
    flux = te.RHO_WATER * te.CP_SEAWATER * 1.0e-4 * (-1.85 - t_b)
    ok(abs(f_root) / max(abs(flux), 1.0e-12) < 1.0e-9,
       "U.12 heat balance Eq. II intact under correction", f"(|F|/flux={abs(f_root)/flux:.2e})")

    # Production end-to-end also satisfies the corrected budget.
    m_p, _, s_bp = te.three_equation_basal_melt(2.0, 34.5, 50.0, u_water=0.1)
    lhs_p = te.RHO_WATER * 3.1e-6 * (34.5 - s_bp)
    rhs_p = te.RHO_ICE * m_p * s_bp
    ok_rel(lhs_p, rhs_p, "U.13 end-to-end satisfies corrected salt budget", 1.0e-3)


def main():
    for f in (
        test_a_eos, test_b_transfer, test_c_canonical, test_d_edges,
        test_e_fresh_gamma_s_zero, test_f_conduction, test_g_scaling,
        test_h_freezing_edge, test_i_depth, test_j_warm_band, test_k_wrapper,
        test_l_contract, test_m_regime_separation, test_n_regression_matrix,
        test_o_determinism, test_t_documented_limitation,
        test_u_mass_salt_convention,
    ):
        f()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.10/10.10.1 three-equation validation PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.10/10.10.1 three-equation validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()