#!/usr/bin/env python3
"""
Stage 10.13 Phase B — independent research prototype: diffusion-limited /
double-diffusive low-flow basal-melt closure (candidate C, hybrid).

This module is an INDEPENDENT RESEARCH PROTOTYPE. It is NOT production code,
does not touch Fortran, and is not part of the model pipeline. It implements
the hybrid closure recommended in the Phase A design note
(``docs/validation/stage10.13_diffusion_limited_low_flow_design_note.md``,
sections 5-7) and exposes the mechanism separation explicitly:

    A. pure diffusion-limited contribution      (m_d, delta_S)
    B. double-diffusive / diffusive-convection enhancement (f)
    C. hybrid combination with forced transfer  (blending w)
    D. existing Stage 10.11 natural-convection baseline (NOT reimplemented
       here; the forced branch reuses ``basal_melt`` — the validated Stage
       10.8.1 independent closure, which is the 10.8.2 scoring reference)

Mechanism summary (design note 5.1-5.3, 6-7):

    delta_S(t) = max(delta_min, sqrt(kappa_S * t))        [m]  (growing saline
        sublayer; optional staircase cap delta_cap; [source] Keitzl16/Middleton21)
    m_d  = k_w * max(T_w - T_B, 0) / (delta_S * rho_i * L_f)   [m/s]  [analytic]
    k_w  = rho_w * c_w * kappa_T                                [W/(m K)]  [analytic]
    R_rho = alpha_T * dT / (beta_S * dS)          (Middleton convention)
        DC active when R_rho > kappa_S/kappa_T AND Re_b < 1      [source] Middleton21
    Re_b = eps/(nu N^2),  eps = u_*^3/(k_vK delta_S),  u_* = sqrt(C_Dw) U,
        N^2 = g beta_S dS / delta_S                             [inferred] diagnostic
    w*   = (g alpha_T kappa_T dT)^(1/3)                         [analytic] convective
    Ri*  = g beta_S dS delta_S / w*^2                           [analytic] diagnostic
    f    = 1 + (f_dc - 1) * I[DC active]        bounded [1, f_dc_max]  [source/inferred]
        (alternative conjecture mode: f = clip(f_dc (Ri*/ri_ref)^-0.42, 1, f_dc_max))
    m_low_flow = f * m_d                                         [m/s]  [analytic]
    m_hybrid   = w(U) m_forced + (1 - w(U)) m_low_flow,  w smoothstep [u_lo, u_hi]
        [analytic] continuous transition; forced branch reference-compatible

Regimes (explicit classification): "forced" | "diffusion_limited" |
"double_diffusive" | "hybrid_transition" | "invalid_or_out_of_scope".

All unresolved parameters are EXPLICIT dataclass fields with documented
baselines and are sensitivity-tested in the sweep; nothing is silently fixed.

Epistemic labels: [source] = established from verified publication;
[repo] = production-consistent value; [analytic] = derived here;
[inferred] = reasonable interpretation, not directly proven;
[unresolved] = open question (explicit parameter).

Units: SI throughout (m, s, K, kg, W). Melt rates are m/s; a single
conversion helper provides m/day.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Optional

# Local import: validated independent forced closure (Stage 10.8.1) — the
# reference-compatible forced branch used by the 10.8.2 scoring pipeline.
import basal_melt as bm

# ---------------------------------------------------------------------------
# Physical constants (production-consistent where they exist) [repo]
# ---------------------------------------------------------------------------
RHO_ICE: float = 910.0           # kg/m^3        [repo: iceberg_types.f90]
RHO_WATER: float = 1028.0        # kg/m^3        [repo: iceberg_types.f90]
LATENT_HEAT: float = 334000.0    # J/kg          [repo: iceberg_types.f90]
CP_WATER: float = 3974.0         # J/(kg K)      [repo: 3eq c_w]
GRAVITY: float = 9.80665         # m/s^2         [repo: iceberg_types.f90]
CP_ICE_3EQ: float = 2009.0       # J/(kg K)      [repo: H&J99 c_i]

KAPPA_T: float = 1.4e-7          # m^2/s  molecular heat diffusivity [inferred, standard]
KAPPA_S: float = 1.5e-9          # m^2/s  molecular salt diffusivity [inferred, standard]
ALPHA_T: float = 3.0e-5          # 1/K    thermal expansion [repo: 10.11 beta_T]
BETA_S: float = 7.8e-4           # 1/PSU  haline contraction [repo: 10.11 beta_S]
NU: float = 1.82e-6              # m^2/s  kinematic viscosity [repo: 10.7 value]
C_D_WATER: float = 2.0e-3        # -      water drag coeff [repo: iceberg_types.f90]
VON_KARMAN: float = 0.4          # -      von Karman constant [standard]

THREE_EQ_KT: float = 1.1e-3      # -      J2010 Table 2 [repo: three_equation_natural]
THREE_EQ_KS: float = 3.1e-5      # -      J2010 Table 2 [repo: three_equation_natural]

K_W: float = RHO_WATER * CP_WATER * KAPPA_T      # ~0.572 W/(m K) [analytic]
DAY_S: float = 86400.0                           # s/day
M_PER_S_TO_M_PER_DAY: float = DAY_S


def m_s_to_m_day(x: float) -> float:
    """Single unit-conversion point: m/s -> m/day."""
    return x * M_PER_S_TO_M_PER_DAY


# ---------------------------------------------------------------------------
# Parameter container: every unresolved quantity is an explicit field
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LowFlowParams:
    """Explicit parameters of the low-flow prototype.

    Baselines and rationale are documented field-by-field; ranges are the
    sensitivity window used in the Phase B sweep.
    """

    le: float = 100.0            # Lewis number baseline [repo]; range 93-110 [unresolved]
    kappa_t: float = KAPPA_T     # m^2/s [inferred]
    kappa_s: float = KAPPA_S     # m^2/s [inferred]
    alpha_t: float = ALPHA_T     # 1/K constant approx [repo]; EOS-80 variant unresolved
    beta_s: float = BETA_S       # 1/PSU constant approx [repo]
    nu: float = NU               # m^2/s
    c_d_w: float = C_D_WATER     # -
    kappa_von: float = VON_KARMAN  # -

    # --- diffusion-limited sublayer [unresolved] ---
    delta_s_min: float = 1.0e-4      # m   floor thickness
    delta_s_cap: Optional[float] = 5.0e-2   # m   staircase cap (MK77 layers O(cm));
                                           # None disables the cap [inferred]
    time_scale_s: float = DAY_S     # s   baseline diagnostic time (1 day)
    dS_floor_psu: float = 1.0e-2    # PSU regularization for R_rho / N^2 [inferred]

    # --- DDC enhancement [source/inferred] ---
    f_dc: float = 2.5               # baseline enhancement (MK77 ~2-2.5; Keitzl 3.1) [source]
    f_dc_max: float = 3.1           # upper bound (Keitzl at 4.33 C) [source]
    enhancement_mode: str = "constant"   # "constant" | "ri_star" [inferred]
    ri_ref: float = 100.0           # reference Ri* for the ri_star conjecture [inferred]

    # --- diagnostics ---
    # No velocity floor is used anywhere in the melt path or diagnostics:
    # the dissipation estimate eps = u_*^3/(k_vK delta_S) with
    # u_* = sqrt(c_d_w) * U goes to 0 at U=0 without regularization, so
    # Re_b -> 0 naturally and the DC criterion is not contaminated by a
    # numerical floor [analytic decision; sensitivity-checked in tests].

    # --- forced/low-flow transition blending [inferred] ---
    u_trans_lo: float = 1.0e-3      # m/s start of transition
    u_trans_hi: float = 1.0e-2      # m/s end of transition (forced dominates)

    # --- salt-transfer convention [unresolved] ---
    k_s_over_k_t: float = THREE_EQ_KS / THREE_EQ_KT   # 0.0282 [repo convention]

    # --- internal ice temp for effective gamma (Eq. II conduction term) ---
    t_ice_degc: float = -10.0       # degC model-selected initial interior [repo 10.12]

    @property
    def k_w(self) -> float:
        return RHO_WATER * CP_WATER * self.kappa_t

    @property
    def kappa_s_over_kappa_t(self) -> float:
        return self.kappa_s / self.kappa_t


# ---------------------------------------------------------------------------
# Diagnostics dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LowFlowResult:
    """Full low-flow diagnostics (SI units; regimes classified explicitly)."""

    m_diffusive_m_s: float
    enhancement_factor: float
    m_low_flow_m_s: float
    delta_s_m: float
    r_rho: float
    ri_star: float
    re_b: float
    regime: str
    bounds_triggered: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def m_low_flow_m_per_day(self) -> float:
        return m_s_to_m_day(self.m_low_flow_m_s)


# ---------------------------------------------------------------------------
# 1. Density ratio  R_rho = alpha_T dT / (beta_S dS)   (Middleton convention)
# ---------------------------------------------------------------------------
def compute_density_ratio(
    t_w: float,
    t_b: float,
    s_w: float,
    s_b: float,
    params: LowFlowParams,
) -> tuple[float, float, float, tuple[str, ...]]:
    """Density (stability) ratio, Middleton convention.

    R_rho = alpha_T * max(T_w - T_B, 0) / (beta_S * max(S_w - S_B, dS_floor))

    Returns (r_rho, dT_eff, dS_eff, warnings).

    Signs: thermal contribution in the numerator is DESTABILIZING (cooling
    near the base -> top-heavy); haline in the denominator is STABILIZING
    (fresh meltwater). DC (diffusive convection) is active for
    R_rho > kappa_S/kappa_T (~1/Le) [source: Middleton21]. At dT <= 0 the
    ratio is defined as 0.0 (no thermal driving). At dS <= 0 the denominator
    is floored at params.dS_floor_psu and a warning is emitted.
    """
    warnings: list[str] = []
    dT = t_w - t_b
    dS = s_w - s_b
    if not (math.isfinite(dT) and math.isfinite(dS)):
        raise ValueError("compute_density_ratio: non-finite T_w/T_B/S_w/S_B")
    dT_eff = max(dT, 0.0)
    dS_eff = max(dS, params.dS_floor_psu)
    if dS <= 0.0:
        warnings.append("S_w <= S_B: dS floored at dS_floor_psu")
    if dT_eff <= 0.0:
        return 0.0, 0.0, dS_eff, tuple(warnings)
    r_rho = params.alpha_t * dT_eff / (params.beta_s * dS_eff)
    return r_rho, dT_eff, dS_eff, tuple(warnings)


# ---------------------------------------------------------------------------
# 2. Convective velocity scale and Richardson star
# ---------------------------------------------------------------------------
def compute_convective_velocity(t_w: float, t_b: float, params: LowFlowParams) -> float:
    """Free-convection velocity scale across the sublayer [analytic].

    w* = (g alpha_T kappa_T max(T_w-T_B,0))^(1/3)   [m/s]

    Derived from w*^3 = g alpha_T q/(rho_w c_w) H with q = k_w dT/H at the
    sublayer scale (design note 6). Well-behaved: w* -> 0 as dT -> 0.
    """
    dT = max(t_w - t_b, 0.0)
    return (GRAVITY * params.alpha_t * params.kappa_t * dT) ** (1.0 / 3.0)


def compute_richardson_star(
    t_w: float,
    t_b: float,
    s_w: float,
    s_b: float,
    delta_s_m: float,
    params: LowFlowParams,
    u_rel: Optional[float] = None,
) -> tuple[float, float, tuple[str, ...]]:
    """Richardson star: shield buoyancy vs convective/mixed-layer velocity.

    Ri* = g beta_S dS_eff delta_S / w*^2      (dimensionless) [analytic,
    Keitzl16 structure; our w* definition is [analytic])

    The velocity entering Ri* is the CONVECTIVE scale w* (not U_rel) —
    buoyancy-driven even at U=0. ``u_rel`` is accepted only as an optional
    diagnostic mixer (max(w*, u_rel)) to expose sensitivity; by default the
    pure convective scale is used. The regularization ``u_floor`` is NEVER
    applied here (it would manufacture an Ri* trend at U=0); it is used only
    in ``compute_reynolds_b`` diagnostics.
    """
    r_rho, dT_eff, dS_eff, warn = compute_density_ratio(t_w, t_b, s_w, s_b, params)
    w_star = compute_convective_velocity(t_w, t_b, params)
    if w_star <= 0.0:
        return 0.0, 0.0, warn
    if u_rel is not None and u_rel > w_star:
        w_star = u_rel
    ri_star = GRAVITY * params.beta_s * dS_eff * delta_s_m / (w_star * w_star)
    return ri_star, w_star, warn


# ---------------------------------------------------------------------------
# 3. Bulk/diagnostic Reynolds (buoyancy-Reynolds analogue)
# ---------------------------------------------------------------------------
def compute_reynolds_b(
    u_rel: float,
    s_w: float,
    s_b: float,
    delta_s_m: float,
    params: LowFlowParams,
) -> float:
    """Diagnostic buoyancy Reynolds number.

    Re_b = eps / (nu N^2)                     (dimensionless) [inferred]
    eps  = u_*^3 / (k_vK delta_S),  u_* = sqrt(c_d_w) * max(U, 0)
    N^2  = g beta_S dS_eff / delta_S

    Diagnostic only — NOT proof of a regime. Re_b < 1 marks a laminar
    sublayer where DDC can act (Middleton criterion). No velocity floor is
    used: eps = 0 at U = 0, so Re_b -> 0 naturally (see LowFlowParams).
    """
    u_eff = max(u_rel, 0.0)
    dS_eff = max(s_w - s_b, params.dS_floor_psu)
    u_star = math.sqrt(params.c_d_w) * u_eff
    eps = u_star**3 / (params.kappa_von * delta_s_m)
    n2 = GRAVITY * params.beta_s * dS_eff / delta_s_m
    if n2 <= 0.0:
        return 0.0
    return eps / (params.nu * n2)


# ---------------------------------------------------------------------------
# 4. Diffusive sublayer thickness
# ---------------------------------------------------------------------------
def compute_diffusive_sublayer(
    time_scale_s: float,
    params: LowFlowParams,
) -> tuple[float, tuple[str, ...]]:
    """Diagnostic saline sublayer thickness [m].

    delta_S = clip(max(delta_min, sqrt(kappa_S * time_scale_s)),
                   None, delta_cap)

    [source] growth law from Middleton21 (saline sublayer growing as
    (kappa_S t)^(1/2)); [inferred] the floor delta_min and the staircase cap
    delta_cap (MK77 layers O(cm)). Never negative; delta_S = delta_min for
    t <= 0 (with warning); time_scale_s is an EXPLICIT parameter — no hidden
    timescale. The cap is a quasi-steady (staircase) limit [inferred].
    """
    warnings: list[str] = []
    if not math.isfinite(time_scale_s):
        raise ValueError("compute_diffusive_sublayer: non-finite time_scale_s")
    if time_scale_s <= 0.0:
        warnings.append("time_scale_s <= 0: delta_S = delta_s_min")
        return params.delta_s_min, tuple(warnings)
    delta = max(params.delta_s_min, math.sqrt(params.kappa_s * time_scale_s))
    if params.delta_s_cap is not None:
        if delta > params.delta_s_cap:
            warnings.append("delta_S hit delta_s_cap (staircase limit)")
        delta = min(delta, params.delta_s_cap)
    return delta, tuple(warnings)


# ---------------------------------------------------------------------------
# 5. Pure diffusion-limited melt rate
# ---------------------------------------------------------------------------
def compute_diffusive_melt_rate(
    t_w: float,
    t_b: float,
    delta_s_m: float,
    params: LowFlowParams,
) -> float:
    """Diffusion-limited contribution to basal melt [m/s].

    m_d = k_w * max(T_w - T_B, 0) / (delta_S * rho_i * L_f)    [analytic]

    Asymptotics: m_d -> 0 as dT -> 0 (exactly 0 for dT<=0); finite at U=0;
    never negative; k_w = rho_w c_w kappa_T in W/(m K). Raises on non-finite
    inputs (deterministic fail-fast).
    """
    if not all(math.isfinite(x) for x in (t_w, t_b, delta_s_m)):
        raise ValueError("compute_diffusive_melt_rate: non-finite input")
    dT = max(t_w - t_b, 0.0)
    if dT <= 0.0 or delta_s_m <= 0.0:
        return 0.0
    return params.k_w * dT / (delta_s_m * RHO_ICE * LATENT_HEAT)


# ---------------------------------------------------------------------------
# 6. DDC enhancement factor
# ---------------------------------------------------------------------------
def compute_ddc_enhancement(
    r_rho: float,
    re_b: float,
    ri_star: float,
    params: LowFlowParams,
) -> tuple[float, tuple[str, ...]]:
    """Double-diffusive (diffusive-convection) enhancement factor f.

    Baseline mode "constant": f = f_dc when the DC criterion is met, else 1.
    DC criterion [source: Middleton21]: R_rho > kappa_S/kappa_T AND Re_b < 1.
    Bounded: f in [1, f_dc_max] (f_dc_max = 3.1, Keitzl at 4.33 C [source]).
    Bounds are applied with explicit diagnostics; they cannot mask a
    dimensional error (all inputs dimensionless here).

    Alternative mode "ri_star" [inferred, Keitzl16 conjecture]:
    f = clip(f_dc * (Ri*/ri_ref)^(-0.42), 1, f_dc_max). This mode is a
    conjecture and is sensitivity-tested; the constant mode is the baseline.
    """
    bounds: list[str] = []
    if params.enhancement_mode == "ri_star":
        if ri_star <= 0.0:
            f = 1.0
        else:
            f = params.f_dc * (ri_star / params.ri_ref) ** (-0.42)
            f = min(f, params.f_dc_max)
            f = max(f, 1.0)
        if f >= params.f_dc_max:
            bounds.append("f at f_dc_max")
        if f <= 1.0:
            bounds.append("f at 1.0")
        return f, tuple(bounds)

    dc_active = r_rho > params.kappa_s_over_kappa_t and re_b < 1.0
    if not dc_active:
        if not (r_rho > params.kappa_s_over_kappa_t):
            bounds.append("DC inactive: R_rho <= kappa_S/kappa_T")
        if not (re_b < 1.0):
            bounds.append("DC inactive: Re_b >= 1 (turbulent sublayer)")
        return 1.0, tuple(bounds)
    f = min(params.f_dc, params.f_dc_max)
    if f >= params.f_dc_max:
        bounds.append("f at f_dc_max")
    return f, tuple(bounds)


# ---------------------------------------------------------------------------
# 7. Hybrid low-flow result (diffusive + DC, no forced branch)
# ---------------------------------------------------------------------------
def compute_hybrid_low_flow(
    t_w: float,
    t_b: float,
    s_w: float,
    s_b: float,
    u_rel: float,
    params: LowFlowParams,
    time_scale_s: Optional[float] = None,
) -> LowFlowResult:
    """Low-flow branch (mechanisms A+B) with full diagnostics.

    Returns LowFlowResult; regime is classified as
    "invalid_or_out_of_scope" (dT<=0), "double_diffusive" (DC active),
    or "diffusion_limited" (DC inactive).
    """
    t_scale = params.time_scale_s if time_scale_s is None else time_scale_s
    r_rho, dT_eff, dS_eff, warn_rho = compute_density_ratio(t_w, t_b, s_w, s_b, params)
    delta_s, warn_d = compute_diffusive_sublayer(t_scale, params)
    m_d = compute_diffusive_melt_rate(t_w, t_b, delta_s, params)

    if dT_eff <= 0.0:
        return LowFlowResult(
            m_diffusive_m_s=0.0, enhancement_factor=1.0, m_low_flow_m_s=0.0,
            delta_s_m=delta_s, r_rho=0.0, ri_star=0.0, re_b=0.0,
            regime="invalid_or_out_of_scope",
            warnings=("dT <= 0: no thermal driving (out of scope)",),
        )

    ri_star, w_star, warn_ri = compute_richardson_star(
        t_w, t_b, s_w, s_b, delta_s, params
    )
    re_b = compute_reynolds_b(u_rel, s_w, s_b, delta_s, params)
    f, bounds = compute_ddc_enhancement(r_rho, re_b, ri_star, params)

    warnings = tuple(warn_rho + warn_d + warn_ri)
    regime = "double_diffusive" if f > 1.0 else "diffusion_limited"
    m_low = f * m_d
    return LowFlowResult(
        m_diffusive_m_s=m_d,
        enhancement_factor=f,
        m_low_flow_m_s=m_low,
        delta_s_m=delta_s,
        r_rho=r_rho,
        ri_star=ri_star,
        re_b=re_b,
        regime=regime,
        bounds_triggered=bounds,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 8. Hybrid melt rate: forced branch + low-flow branch, continuous blending
# ---------------------------------------------------------------------------
def _smoothstep(u: float, u_lo: float, u_hi: float) -> float:
    """Continuous blending weight w in [0,1]; 0 below u_lo, 1 above u_hi.

    w = 0.5 - 0.5*cos(pi * clamp((u-u_lo)/(u_hi-u_lo), 0, 1))   (cosine ramp)
    [analytic] — chosen for C1-continuity; width (u_lo,u_hi) is an explicit
    parameter (transition zone), NOT an arbitrary patch.
    """
    if u_hi <= u_lo:
        raise ValueError("_smoothstep: u_hi must exceed u_lo")
    if u <= u_lo:
        return 0.0
    if u >= u_hi:
        return 1.0
    t = (u - u_lo) / (u_hi - u_lo)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def compute_effective_gammas(
    result: LowFlowResult,
    t_w: float,
    t_b: float,
    params: LowFlowParams,
) -> tuple[float, float, tuple[str, ...]]:
    """Effective low-flow transfer coefficients gamma_T_low, gamma_S_low [m/s].

    gamma_T_low = m_low * rho_i * (L_f + c_i*max(T_B - T_i,0))
                  / (rho_w c_w max(T_w - T_B, 0))        [analytic, inverts Eq. II]
    gamma_S_low = gamma_T_low * (K_S/K_T)                [repo convention;
                                                           flux-ratio alternative
                                                           [unresolved]]

    Returns (gamma_T_low, gamma_S_low, warnings). These coefficients plug into
    the unchanged three-equation framework (design note 7); the framework
    equations themselves are NOT modified here.
    """
    dT = max(t_w - t_b, 0.0)
    if dT <= 0.0 or result.m_low_flow_m_s <= 0.0:
        return 0.0, 0.0, ("dT<=0 or m_low<=0: gamma_low=0",)
    cond = LATENT_HEAT + CP_ICE_3EQ * max(t_b - params.t_ice_degc, 0.0)
    gamma_t = result.m_low_flow_m_s * RHO_ICE * cond / (RHO_WATER * CP_WATER * dT)
    gamma_s = gamma_t * params.k_s_over_k_t
    return gamma_t, gamma_s, ()


def compute_hybrid_melt_rate(
    t_w: float,
    s_w: float,
    u_rel: float,
    l_char_m: float,
    depth_m: float,
    params: LowFlowParams,
    time_scale_s: Optional[float] = None,
    t_b: Optional[float] = None,
    s_b: Optional[float] = None,
) -> tuple[float, LowFlowResult, float, float, float, float]:
    """Hybrid melt rate combining forced + low-flow branches [m/s].

    Returns (m_hybrid, low_result, m_forced, w_blend, gamma_T_low, gamma_S_low).

    Forced branch: ``basal_melt.basal_melt_rate`` — reference-compatible with
    the Stage 10.8.2 scoring pipeline [repo]. Interface values T_B/S_B, when
    not supplied, default to the quiescent-limit estimates
    T_B = Tf(S_w, depth) and S_B = S_w - dS_floor_psu [inferred];
    the full 3eq iteration with gamma_low is deferred to Phase C.

    Blending: m = w*U m_forced + (1-w) m_low_flow with w = _smoothstep over
    [u_trans_lo, u_trans_hi] [analytic]. No double counting: the low-flow
    branch and the forced branch are mutually exclusive weightings of two
    separate mechanisms (diffusion-limited/DC vs turbulent forced).
    """
    if not all(math.isfinite(x) for x in (t_w, s_w, u_rel, l_char_m, depth_m)):
        raise ValueError("compute_hybrid_melt_rate: non-finite input")
    u_rel = max(u_rel, 0.0)  # physical: no negative relative speed [analytic]

    t_b_eff = t_b if t_b is not None else bm.ocean_freezing_point(s_w, depth_m)
    s_b_eff = s_b if s_b is not None else s_w - params.dS_floor_psu

    low = compute_hybrid_low_flow(t_w, t_b_eff, s_w, s_b_eff, u_rel, params,
                                  time_scale_s)

    m_forced = bm.basal_melt_rate(
        ocean_temperature=t_w, salinity_psu=s_w, depth_m=depth_m,
        u_water=u_rel, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=l_char_m,
    )
    if m_forced < 0.0:
        m_forced = 0.0

    w = _smoothstep(u_rel, params.u_trans_lo, params.u_trans_hi)
    m_hybrid = w * m_forced + (1.0 - w) * low.m_low_flow_m_s

    regime = low.regime
    if w > 0.0 and w < 1.0 and regime not in ("invalid_or_out_of_scope",):
        regime = "hybrid_transition"
    elif w >= 1.0:
        regime = "forced"

    low = replace(low, regime=regime)
    gamma_t, gamma_s, _ = compute_effective_gammas(low, t_w, t_b_eff, params)
    return m_hybrid, low, m_forced, w, gamma_t, gamma_s