#!/usr/bin/env python3
"""
Stage 10.13 Phase B — analytical tests for the low-flow closure prototype.

Independent checks of python/validation/low_flow.py against embedded literals
and asymptotic behavior. Covers the required blocks A–K:

  A. zero thermal driving   B. zero velocity          C. small-U continuity
  D. sublayer growth        E. positive melt          F. zero/negative dT
  G. enhancement bounds     H. forced preservation    I. transition continuity
  J. parameter sensitivity  K. dimensional checks

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_low_flow.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))

import low_flow as lf  # noqa: E402
import basal_melt as bm  # noqa: E402

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


def ok_rel(actual: float, expected: float, label: str, tol: float = 1e-9,
           detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    rel = abs(actual - expected) / max(abs(expected), 1e-300)
    if rel < tol:
        print(f"OK   {label} (rel={rel:.2e})" + (f" ({detail})" if detail else ""))
    else:
        print(f"ERROR {label}: actual={actual:.6e} expected={expected:.6e} rel={rel:.2e}")
        _ERRORS += 1


P = lf.LowFlowParams()  # baseline parameters

# ---------------------------------------------------------------------------
# A. Zero thermal driving
# ---------------------------------------------------------------------------
def test_a_zero_driving() -> None:
    rho, dT, dS, warn = lf.compute_density_ratio(2.0, 2.0, 34.5, 34.0, P)
    ok(rho == 0.0, "A.1 R_rho = 0 at dT = 0")
    m_d = lf.compute_diffusive_melt_rate(2.0, 2.0, 0.011384, P)
    ok(m_d == 0.0, "A.2 m_diffusive = 0 at dT = 0")
    res = lf.compute_hybrid_low_flow(2.0, 2.0, 34.5, 34.0, 0.0, P)
    ok(res.m_low_flow_m_s == 0.0, "A.3 m_low_flow = 0 at dT = 0")
    ok(res.regime == "invalid_or_out_of_scope", "A.4 regime out-of-scope at dT=0")
    ok(all(math.isfinite(x) for x in (rho, m_d, res.m_low_flow_m_s)),
       "A.5 no NaN/Inf at dT=0")
    res2 = lf.compute_hybrid_low_flow(1.5, 2.0, 34.5, 34.0, 0.0, P)
    ok(res2.m_low_flow_m_s == 0.0, "A.6 dT<0 -> 0 melt, no hidden negative")


# ---------------------------------------------------------------------------
# B. Zero velocity
# ---------------------------------------------------------------------------
def test_b_zero_velocity() -> None:
    res = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, P)
    ok(res.m_low_flow_m_s > 0.0, "B.1 finite melt at U=0", f"(m={res.m_low_flow_m_s:.3e} m/s)")
    ok(res.re_b >= 0.0 and math.isfinite(res.re_b), "B.2 Re_b finite at U=0")
    ok(res.ri_star >= 0.0 and math.isfinite(res.ri_star), "B.3 Ri* finite at U=0")
    ok(res.r_rho > 0.0, "B.4 R_rho defined at U=0")
    m_hyb, low, m_f, w, gt, gs = lf.compute_hybrid_melt_rate(
        2.0, 34.5, 0.0, 100.0, 50.0, P)
    ok(w == 0.0, "B.5 blend w=0 at U=0")
    ok_rel(m_hyb, low.m_low_flow_m_s, "B.6 hybrid = low_flow at U=0", 1e-12)
    # No velocity floor in the melt path: at U=0 the dissipation estimate is
    # exactly 0 -> Re_b = 0 and the DC criterion is not floor-contaminated.
    ok(low.re_b == 0.0, "B.7 Re_b = 0 at U=0 (no floor regularization)")
    res0 = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, P)
    ok_rel(res0.m_low_flow_m_s, res0.m_diffusive_m_s * res0.enhancement_factor,
           "B.8 m_low = f*m_d at U=0 (no hidden melt source)", 1e-12)


# ---------------------------------------------------------------------------
# C. Small-velocity continuity (no unphysical jump)
# ---------------------------------------------------------------------------
def test_c_small_u_continuity() -> None:
    us = (0.0, 1e-8, 1e-7, 1e-6, 1e-5)
    ms = [lf.compute_hybrid_melt_rate(2.0, 34.5, u, 100.0, 50.0, P)[0] for u in us]
    for i in range(1, len(ms)):
        jump = abs(math.log10(ms[i] + 1e-300) - math.log10(ms[i - 1] + 1e-300))
        ok(jump < 0.5, f"C.{i} no order-of-magnitude jump U={us[i-1]:.0e}->{us[i]:.0e}",
           f"(log10-jump={jump:.3f})")
    ok(all(math.isfinite(m) for m in ms), "C.6 no NaN/Inf at small U")


# ---------------------------------------------------------------------------
# D. Sublayer growth
# ---------------------------------------------------------------------------
def test_d_sublayer_growth() -> None:
    d1, _ = lf.compute_diffusive_sublayer(86400.0, P)
    d10, _ = lf.compute_diffusive_sublayer(10 * 86400.0, P)
    ok_rel(d1, math.sqrt(P.kappa_s * 86400.0), "D.1 delta_S = sqrt(kappa_s t), 1 d")
    ok(d10 > d1, "D.2 delta_S grows with t")
    ok_rel(d10 / d1, math.sqrt(10.0), "D.3 sqrt scaling", 1e-6)
    dmin, warn = lf.compute_diffusive_sublayer(-1.0, P)
    ok(dmin == P.delta_s_min and len(warn) == 1, "D.4 t<=0 -> delta_min + warning")
    m1 = lf.compute_diffusive_melt_rate(2.0, -1.9, d1, P)
    m10 = lf.compute_diffusive_melt_rate(2.0, -1.9, d10, P)
    ok(m10 < m1, "D.5 melt decays as sublayer grows")
    ok_rel(m1 * d1, m10 * d10, "D.6 m*d = const (k_w dT/(rho L))", 1e-9)
    # cap behavior
    p_cap = lf.replace(P, delta_s_cap=0.005)
    dc, warnc = lf.compute_diffusive_sublayer(86400.0, p_cap)
    ok(dc == 0.005 and len(warnc) == 1, "D.7 staircase cap applied + warning")


# ---------------------------------------------------------------------------
# E. Positive melt rate for warm salty ocean
# ---------------------------------------------------------------------------
def test_e_positive() -> None:
    res = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, P)
    ok(res.m_diffusive_m_s > 0.0, "E.1 m_diffusive > 0")
    ok(res.delta_s_m > 0.0, "E.2 delta_S > 0")
    ok(res.enhancement_factor >= 1.0, "E.3 f >= 1")
    ok(res.m_low_flow_m_s >= 0.0, "E.4 m_low_flow >= 0")
    ok(res.m_low_flow_m_per_day > 0.01, "E.5 quiescent melt in observed band",
       f"({res.m_low_flow_m_per_day:.4f} m/day)")


# ---------------------------------------------------------------------------
# F. Zero/negative thermal contrast — defined behavior
# ---------------------------------------------------------------------------
def test_f_thermal_contrast() -> None:
    res = lf.compute_hybrid_low_flow(-1.0, 0.0, 34.5, 34.0, 0.0, P)
    ok(res.m_low_flow_m_s == 0.0 and res.regime == "invalid_or_out_of_scope",
       "F.1 dT<0 -> 0, out-of-scope marker")
    m_hyb, low, m_f, w, _, _ = lf.compute_hybrid_melt_rate(
        -1.0, 34.5, 0.01, 100.0, 50.0, P)
    ok(m_hyb >= 0.0, "F.2 hybrid >= 0 even with negative driving (forced guard)")
    ok(math.isfinite(m_hyb), "F.3 no NaN")


# ---------------------------------------------------------------------------
# G. Enhancement bounds
# ---------------------------------------------------------------------------
def test_g_enhancement_bounds() -> None:
    f1, b1 = lf.compute_ddc_enhancement(0.001, 0.1, 5.0, P)   # R_rho below threshold
    ok(f1 == 1.0 and len(b1) == 1, "G.1 DC inactive -> f=1 with diagnostic",
       f"({b1[0] if b1 else ''})")
    f2, b2 = lf.compute_ddc_enhancement(100.0, 5.0, 5.0, P)   # Re_b above threshold
    ok(f2 == 1.0 and len(b2) == 1, "G.2 turbulent sublayer -> f=1 with diagnostic")
    f3, b3 = lf.compute_ddc_enhancement(100.0, 0.1, 5.0, P)   # DC active
    ok_rel(f3, P.f_dc, "G.3 DC active -> f = f_dc", 1e-12)
    ok(f3 <= P.f_dc_max and f3 >= 1.0, "G.4 f bounded [1, f_dc_max]")
    # ri_star mode bounded
    p_ri = lf.replace(P, enhancement_mode="ri_star")
    f4, b4 = lf.compute_ddc_enhancement(100.0, 0.1, 1e6, p_ri)
    ok(f4 == 1.0 and f4 >= 1.0, "G.5 ri_star mode: strong shield -> f->1",
       f"(f={f4:.3f})")
    f5, _ = lf.compute_ddc_enhancement(100.0, 0.1, 1e-6, p_ri)
    ok(f5 <= P.f_dc_max, "G.6 ri_star mode capped at f_dc_max", f"(f={f5:.3f})")


# ---------------------------------------------------------------------------
# H. Forced branch preservation
# ---------------------------------------------------------------------------
def test_h_forced_preservation() -> None:
    u = 0.5  # well above u_trans_hi
    m_hyb, low, m_f, w, _, _ = lf.compute_hybrid_melt_rate(
        2.0, 34.5, u, 100.0, 50.0, P)
    ok(w == 1.0, "H.1 w=1 in forced regime")
    ok_rel(m_hyb, m_f, "H.2 hybrid == forced at high U", 1e-12)
    ok(m_f > 0.0, "H.3 forced branch active", f"(m_f={m_f:.3e} m/s)")
    ref = bm.basal_melt_rate(ocean_temperature=2.0, salinity_psu=34.5, depth_m=50.0,
                             u_water=u, v_water=0.0, u_ice=0.0, v_ice=0.0,
                             length_m=100.0)
    ok_rel(m_f, ref, "H.4 forced branch == basal_melt reference", 1e-12)


# ---------------------------------------------------------------------------
# I. Transition continuity
# ---------------------------------------------------------------------------
def test_i_transition() -> None:
    us = [i * 2.0e-4 for i in range(0, 101)]  # 0 .. 0.02 m/s, 100 steps
    prev = None
    max_jump = 0.0
    for u in us:
        m, _, _, _, _, _ = lf.compute_hybrid_melt_rate(2.0, 34.5, u, 100.0, 50.0, P)
        ok(m >= 0.0 and math.isfinite(m), "I.x m finite/non-negative", f"(U={u})")
        if prev is not None:
            jump = abs(math.log10(m + 1e-300) - math.log10(prev + 1e-300))
            max_jump = max(max_jump, jump)
        prev = m
    ok(max_jump < 1.0, "I.1 no order-of-magnitude jump across transition",
       f"(max log10-jump={max_jump:.3f})")
    # monotonic-consistency: hybrid is between forced and low_flow at mid-transition
    u_mid = (P.u_trans_lo + P.u_trans_hi) / 2.0
    m_mid, low, m_f, w, _, _ = lf.compute_hybrid_melt_rate(2.0, 34.5, u_mid, 100.0, 50.0, P)
    ok(0.0 < w < 1.0, "I.2 blend strictly inside transition", f"(w={w:.3f})")
    lo = min(m_f, low.m_low_flow_m_s)
    hi = max(m_f, low.m_low_flow_m_s)
    ok(lo - 1e-12 <= m_mid <= hi + 1e-12, "I.3 hybrid between branches")


# ---------------------------------------------------------------------------
# J. Parameter sensitivity (finite, monotone where physical)
# ---------------------------------------------------------------------------
def test_j_sensitivity() -> None:
    # Le sensitivity: wider Le -> lower kappa_S/kappa_T threshold (no crash)
    for le in (93.0, 100.0, 110.0):
        p = lf.replace(P, kappa_s=P.kappa_t / le)
        m, _, _, _, _, _ = lf.compute_hybrid_melt_rate(2.0, 34.5, 0.0, 100.0, 50.0, p)
        ok(math.isfinite(m) and m > 0.0, f"J.1 Le={le:.0f} finite positive")
    # K_S/K_T sensitivity (effective gamma)
    for kskt in (0.01, 0.0282, 0.05):
        p = lf.replace(P, k_s_over_k_t=kskt)
        m, low, _, _, gt, gs = lf.compute_hybrid_melt_rate(2.0, 34.5, 0.0, 100.0, 50.0, p)
        ok_rel(gs, gt * kskt, f"J.2 gamma_S = gamma_T*(K_S/K_T) at {kskt:.4f}", 1e-12)
    # delta_S parameter sensitivity: larger delta_min -> smaller melt
    # (use 0.02 m > delta_S(1 d)=0.0114 m so the floor actually binds)
    m_small = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0,
                                         lf.replace(P, delta_s_min=1e-4)).m_low_flow_m_s
    m_big = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0,
                                       lf.replace(P, delta_s_min=2e-2)).m_low_flow_m_s
    ok(m_big < m_small, "J.3 thicker floor -> smaller melt")
    # f_dc bound sensitivity
    p_lo = lf.replace(P, f_dc=2.0)
    res_lo = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, p_lo)
    ok(res_lo.enhancement_factor == 2.0, "J.4 f_dc parameter respected", f"(f={res_lo.enhancement_factor})")
    # time scale sensitivity
    m_1h = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, P,
                                      time_scale_s=3600.0).m_low_flow_m_s
    m_10d = lf.compute_hybrid_low_flow(2.0, -1.9, 34.5, 34.0, 0.0, P,
                                       time_scale_s=10 * 86400.0).m_low_flow_m_s
    ok(m_1h > m_10d, "J.5 shorter time -> thinner sublayer -> faster melt")


# ---------------------------------------------------------------------------
# K. Dimensional checks
# ---------------------------------------------------------------------------
def test_k_dimensions() -> None:
    m_hyb, low, m_f, w, gt, gs = lf.compute_hybrid_melt_rate(
        2.0, 34.5, 0.0, 100.0, 50.0, P)
    # m in m/s (plausible 1e-10..1e-4)
    ok(1e-10 < m_hyb < 1e-4, "K.1 m_hybrid in m/s range", f"({m_hyb:.3e})")
    ok(1e-4 <= low.delta_s_m <= 1e-1, "K.2 delta_S in m range", f"({low.delta_s_m:.4f})")
    # gamma in m/s
    ok(0.0 < gt < 1e-3, "K.3 gamma_T_low in m/s range", f"({gt:.3e})")
    ok(0.0 < gs < 1e-3, "K.4 gamma_S_low in m/s range", f"({gs:.3e})")
    # dimensionless groups
    for name, val in (("R_rho", low.r_rho), ("Ri*", low.ri_star), ("Re_b", low.re_b)):
        ok(val >= 0.0 and math.isfinite(val), f"K.5 {name} dimensionless & finite",
           f"({val:.4e})")
    # heat flux W/m^2: q = k_w dT / delta_S
    q = P.k_w * (2.0 - (-1.9)) / low.delta_s_m
    ok(1.0 < q < 1e4, "K.6 diffusive heat flux in W/m^2 range", f"({q:.2f})")
    # dimensional self-consistency: m_d * delta_S * rho_i L_f / k_w == dT
    m_d = low.m_diffusive_m_s
    t_b_eff = bm.ocean_freezing_point(34.5, 50.0)   # what the hybrid used
    dT_expected = 2.0 - t_b_eff
    dT_back = m_d * low.delta_s_m * lf.RHO_ICE * lf.LATENT_HEAT / P.k_w
    ok_rel(dT_back, dT_expected, "K.7 m*d*rho*L/k_w == dT (unit closure)", 1e-9)
    # R_rho recomputed from definition
    rho_manual = P.alpha_t * (2.0 - (-1.9)) / (P.beta_s * 0.5)  # S_B=34.0
    res_manual = lf.compute_density_ratio(2.0, -1.9, 34.5, 34.0, P)[0]
    ok_rel(res_manual, rho_manual, "K.8 R_rho matches definition", 1e-12)


def main() -> None:
    test_a_zero_driving()
    test_b_zero_velocity()
    test_c_small_u_continuity()
    test_d_sublayer_growth()
    test_e_positive()
    test_f_thermal_contrast()
    test_g_enhancement_bounds()
    test_h_forced_preservation()
    test_i_transition()
    test_j_sensitivity()
    test_k_dimensions()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.13 low-flow prototype validation PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.13 low-flow prototype validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()