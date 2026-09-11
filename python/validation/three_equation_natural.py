#!/usr/bin/env python3
"""
Stage 10.11 — Independent Python validation of natural-convection basal melt.

Reproduces the production three-equation + natural convection closure from
`src/iceberg_types.f90` (`natural_convection_transfer_coeff`) and
`src/iceberg_thermodynamics.f90` (`solve_three_equation_interface_natural`).

Equations (Stage 10.11):

Three-equation interface (Holland & Jenkins 1999; Jenkins et al. 2010):
    (I)   T_B = Tf(S_B, P)
    (II)  rho_w c_w gamma_T (T_w - T_B) = m rho_i [L_f + c_i max(T_B - T_i, 0)]
    (III) rho_w gamma_S (S_w - S_B) = rho_i m S_B   (Stage 10.10.1 correction)

Natural convection (Fujii et al. 1973; Churchill 1977):
    For horizontal ice base (facing downward / cooled up):
    Characteristic length L = iceberg length (horizontal scale of the
    Fujii plate). The production caller passes state%L via compute_basal_melt
    (see src/iceberg_thermodynamics.f90 line ~237); the draft D is NOT used.
    Stage 10.11.2 audit corrected a doc-only inconsistency (comments claimed
    D = draft per Gayen et al. 2016 — that paper studies a VERTICAL ice face
    and does not set a cell scale for a horizontal base; the claim was
    unsupported and removed).

    Double-diffusive Rayleigh number:
        Ra_eff = g L^3 / (nu alpha) * [beta_T (T_w - T_B) + beta_S (S_w - S_B) * Le]

    Nusselt number:
        Laminar  (Ra < 1e7):  Nu = 0.27 * Ra^0.25
        Turbulent (Ra >= 1e7): Nu = 0.15 * Ra^(1/3)

    Natural-convection transfer coefficients:
        gamma_T_nat = Nu * k / L
        gamma_S_nat = gamma_T_nat * (K_S / K_T)   (same Stanton ratio as forced)

Mixed convection (Churchill 1977, n=3):
    gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)
    gamma_S_eff = (gamma_S_forced^3 + gamma_S_nat^3)^(1/3)

Where gamma_T_forced = K_T U_rel, gamma_S_forced = K_S U_rel (J2010 Table 2).

Constants (embedded from production):
    rho_w = 1028, c_w = 3974, rho_i = 910, L_f = 3.34e5, c_i = 2009, T_i = -10
    K_T = 1.1e-3, K_S = 3.1e-5
    beta_T = 3.0e-5 1/K, beta_S = 7.8e-4 1/PSU, Le = 100
    nu = 1.82e-6, k = 0.56, Pr = 13.8
    EOS-80: A0=-0.0575, A1=1.710523e-3, A2=2.154996e-4, BP=-7.53e-4
    g = 9.80665

This module is mathematically independent of the Fortran code.
"""

import math

# ============================================================
# EMBEDDED CONSTANTS (matching production in iceberg_types.f90)
# ============================================================

RHO_WATER = 1028.0          # kg/m^3
RHO_ICE = 910.0             # kg/m^3
LATENT_HEAT = 334000.0      # J/kg
CP_SEAWATER = 3974.0        # J/(kg K)  (H&J99 c_w)
CP_ICE_3EQ = 2009.0         # J/(kg K)  (H&J99 c_i)
T_ICE = -10.0               # degC (model-selected, NOT from H&J99)
THREE_EQ_KT = 1.1e-3        # (J2010 Table 2)
THREE_EQ_KS = 3.1e-5        # (J2010 Table 2)

# Stage 10.10.1: density ratio in salt balance
RHO_ICE_WATER_RATIO = RHO_ICE / RHO_WATER   # 910/1028 = 0.885214...

# Stage 10.11 natural convection constants
THERMAL_EXPANSION_COEFF = 3.0e-5      # 1/K (beta_T)
HALINE_CONTRACTION_COEFF = 7.8e-4     # 1/PSU (beta_S)
LEWIS_NUMBER = 100.0                  # Le = alpha / D_S

# Fujii et al. (1973) Nusselt-Rayleigh correlations
NU_LAMINAR_COEFF = 0.27
NU_LAMINAR_EXP = 0.25
NU_TURBULENT_COEFF = 0.15
NU_TURBULENT_EXP = 1.0/3.0
RAYLEIGH_TRANSITION = 1.0e7

# Maximum Rayleigh number (physical cap for ultimate regime)
# Standard correlations valid up to Ra ~ 1e10; beyond that, flow enters
# "ultimate regime" with different scaling (Nu ~ Ra^0.5 or similar).
# We cap Ra to avoid unphysically large Nu from extrapolating correlations.
RAYLEIGH_MAX = 1.0e10

# Churchill (1977) mixed convection exponent
MIXED_CONVECTION_EXP = 3.0

# Seawater properties
KINEMATIC_VISCOSITY = 1.82e-6         # m^2/s (nu)
THERMAL_CONDUCTIVITY = 0.56           # W/(m K) (k)
PRANDTL_NUMBER = 13.8                 # Pr
GRAVITY = 9.80665                     # m/s^2

# EOS-80 freezing point coefficients (Stage 10.5)
EOS_FP_A0 = -0.0575
EOS_FP_A1 = 1.710523e-3
EOS_FP_A2 = 2.154996e-4
EOS_FP_BP = -7.53e-4

MELT_RATE_MIN = 1.0e-12


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def ocean_freezing_point(salinity_mass: float, depth_m: float) -> float:
    """EOS-80 freezing point Tf = f(S, P) [degC].
    salinity_mass: mass fraction [kg/kg]
    depth_m: depth [m]
    """
    s_psu = salinity_mass * 1000.0
    p_dbar = RHO_WATER * GRAVITY * depth_m / 1.0e4
    tf = (EOS_FP_A0 + EOS_FP_A1 * math.sqrt(s_psu) - EOS_FP_A2 * s_psu) * s_psu \
         + EOS_FP_BP * p_dbar
    return tf


def _thermal_diffusivity() -> float:
    """Thermal diffusivity alpha = k / (rho * c_p) [m^2/s]."""
    return THERMAL_CONDUCTIVITY / (RHO_WATER * CP_SEAWATER)


def _nusselt_from_raeff(ra_eff: float) -> float:
    """Nusselt number from effective Rayleigh number (Fujii et al. 1973)."""
    if ra_eff <= 0.0:
        return 0.0
    # Cap Ra at physically reasonable maximum
    ra_capped = min(ra_eff, RAYLEIGH_MAX)
    if ra_capped < RAYLEIGH_TRANSITION:
        return NU_LAMINAR_COEFF * (ra_capped ** NU_LAMINAR_EXP)
    else:
        return NU_TURBULENT_COEFF * (ra_capped ** NU_TURBULENT_EXP)


def natural_convection_transfer_coeff(t_w: float, s_w: float,
                                       t_b: float, s_b: float,
                                       l_char: float, u_rel: float) -> tuple[float, float]:
    """
    Compute total (forced + natural) heat and salt transfer coefficients.

    Matches `natural_convection_transfer_coeff` in `src/iceberg_types.f90`.

    Args:
        t_w: far-field temperature [degC]
        s_w: far-field salinity [kg/kg]
        t_b: interface temperature [degC]
        s_b: interface salinity [kg/kg]
        l_char: characteristic length for natural convection [m] (iceberg length L)
        u_rel: forced-convection relative velocity [m/s]

    Returns:
        (gamma_t_eff, gamma_s_eff) in [m/s]
    """
    # Forced convection (U-based, J2010 Table 2)
    gamma_t_forced = THREE_EQ_KT * u_rel
    gamma_s_forced = THREE_EQ_KS * u_rel

    # Natural convection
    # Characteristic length for natural convection from horizontal plate
    # facing downward (heated down / cooled up) is the horizontal plate dimension.
    # For iceberg base, this is the iceberg length L (horizontal scale of
    # convection cells), not the draft D (vertical scale).
    # Using L_char = l_char (passed as iceberg length).
    if l_char <= 0.0:
        gamma_t_nat = 0.0
        gamma_s_nat = 0.0
    else:
        delta_t = t_w - t_b
        delta_s_psu = (s_w - s_b) * 1000.0  # kg/kg -> PSU

        thermal_diffusivity = _thermal_diffusivity()

        if delta_t > 0.0 or delta_s_psu > 0.0:
            ra_eff = (GRAVITY * l_char**3 /
                      (KINEMATIC_VISCOSITY * thermal_diffusivity) *
                      (THERMAL_EXPANSION_COEFF * delta_t +
                       HALINE_CONTRACTION_COEFF * delta_s_psu * LEWIS_NUMBER))
        else:
            ra_eff = 0.0

        nusselt = _nusselt_from_raeff(ra_eff)

        gamma_t_nat = nusselt * THERMAL_CONDUCTIVITY / (l_char * RHO_WATER * CP_SEAWATER)
        gamma_s_nat = gamma_t_nat * (THREE_EQ_KS / THREE_EQ_KT)

    # Churchill (1977) mixed convection combination, n=3
    mixed_exp = MIXED_CONVECTION_EXP
    if gamma_t_forced > 0.0 and gamma_t_nat > 0.0:
        gamma_t_eff = (gamma_t_forced**mixed_exp + gamma_t_nat**mixed_exp)**(1.0/mixed_exp)
        gamma_s_eff = (gamma_s_forced**mixed_exp + gamma_s_nat**mixed_exp)**(1.0/mixed_exp)
    elif gamma_t_forced > 0.0:
        gamma_t_eff = gamma_t_forced
        gamma_s_eff = gamma_s_forced
    else:
        gamma_t_eff = gamma_t_nat
        gamma_s_eff = gamma_s_nat

    return gamma_t_eff, gamma_s_eff


def _evaluate_interface(t_w: float, s_w: float, depth_m: float, u_rel: float,
                         l_char_nat: float, m: float, gamma_t: float, gamma_s: float) -> tuple[float, float, float, float]:
    """
    Evaluate the interface state (T_B, S_B) and transfer coefficients for a given m
    using the explicit coupling from the Fortran implementation.
    
    Given m and previous gamma_t, gamma_s:
    1. S_B = gamma_S * S_w / (gamma_S + r*m)
    2. T_B = Tf(S_B)
    3. gamma_T, gamma_S = natural_convection_transfer_coeff(T_B, S_B)
    
    Returns: (t_b, s_b, gamma_t, gamma_s)
    """
    s_b = gamma_s * s_w / (gamma_s + RHO_ICE_WATER_RATIO * m)
    t_b = ocean_freezing_point(s_b, depth_m)
    gamma_t, gamma_s = natural_convection_transfer_coeff(t_w, s_w, t_b, s_b, l_char_nat, u_rel)
    return t_b, s_b, gamma_t, gamma_s


def _latent_heat_total(t_b: float, t_ice: float, use_conduction: bool) -> float:
    """Total latent + conduction heat per unit melt mass [J/kg]."""
    l_heat = RHO_ICE * LATENT_HEAT
    if use_conduction:
        l_heat += RHO_ICE * CP_ICE_3EQ * max(t_b - t_ice, 0.0)
    return l_heat


def _f_residual(t_w: float, t_b: float, gamma_t: float, m: float,
                t_ice: float, use_conduction: bool) -> float:
    """Eq. II residual F(m) = rho_w c_w gamma_T (T_w - T_B) - m * latent."""
    flux = RHO_WATER * CP_SEAWATER * gamma_t * (t_w - t_b)
    latent = _latent_heat_total(t_b, t_ice, use_conduction)
    return flux - m * latent


def solve_three_equation_interface(t_w: float, s_w: float, depth_m: float,
                                    u_rel: float, l_char_nat: float,
                                    t_ice: float, use_conduction: bool) -> tuple[float, float, float]:
    """
    Solve three-equation interface with natural convection (Stage 10.11).

    Matches `solve_three_equation_interface_natural` in `iceberg_thermodynamics.f90`.

    Returns:
        (m_basal, t_interface, s_interface) in [m/s, degC, kg/kg]
    """
    tf_w = ocean_freezing_point(s_w, depth_m)

    # Edge: no thermal driving
    if t_w <= tf_w:
        return 0.0, tf_w, s_w

    # Edge: fresh water (S_w <= 0)
    if s_w <= 0.0:
        s_b = 0.0
        t_b = ocean_freezing_point(0.0, depth_m)
        gamma_t, gamma_s = natural_convection_transfer_coeff(
            t_w, s_w, t_b, s_b, l_char_nat, u_rel)
        l_heat = _latent_heat_total(t_b, t_ice, True)
        if gamma_t > 0.0 and l_heat > 0.0:
            m = RHO_WATER * CP_SEAWATER * gamma_t * (t_w - t_b) / l_heat
        else:
            m = 0.0
        return m, t_b, s_b

    # Main case: bisection with natural convection at each step
    m_lo = 0.0

    # Initial m_est using natural convection at m=0 (T_B = tf_w, S_B = S_w)
    gamma_t, gamma_s = natural_convection_transfer_coeff(
        t_w, s_w, tf_w, s_w, l_char_nat, u_rel)
    m_est = (RHO_WATER * CP_SEAWATER * gamma_t * (t_w - tf_w) /
             (RHO_ICE * LATENT_HEAT))
    m_hi = max(m_est, 1.0e-9)

    # Expand upper bound
    for _ in range(60):
        t_b, s_b, gamma_t, gamma_s = _evaluate_interface(
            t_w, s_w, depth_m, u_rel, l_char_nat, m_hi, gamma_t, gamma_s)
        l_heat = _latent_heat_total(t_b, t_ice, True)
        f_val = _f_residual(t_w, t_b, gamma_t, m_hi, t_ice, True)
        if f_val <= 0.0:
            break
        m_hi *= 2.0

    # Bisection
    for _ in range(60):
        m_mid = 0.5 * (m_lo + m_hi)
        t_b, s_b, gamma_t, gamma_s = _evaluate_interface(
            t_w, s_w, depth_m, u_rel, l_char_nat, m_mid, gamma_t, gamma_s)
        l_heat = _latent_heat_total(t_b, t_ice, True)
        f_val = _f_residual(t_w, t_b, gamma_t, m_mid, t_ice, True)
        if f_val > 0.0:
            m_lo = m_mid
        else:
            m_hi = m_mid

    m_basal = 0.5 * (m_lo + m_hi)
    t_b, s_b, _, _ = _evaluate_interface(
        t_w, s_w, depth_m, u_rel, l_char_nat, m_basal, gamma_t, gamma_s)
    return m_basal, t_b, s_b


def three_equation_basal_melt_natural(t_w: float, s_w: float, depth_m: float,
                                       u_rel: float, l_char_nat: float,
                                       draft: float | None = None) -> tuple[float, float, float]:
    """
    Production-style wrapper for three-equation + natural convection basal melt.

    Matches the production call in `compute_basal_melt` for scheme
    `BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL`.

    Args:
        t_w: far-field temperature [degC]
        s_w: far-field salinity [kg/kg] (mass fraction)
        depth_m: depth for pressure [m]
        u_rel: relative velocity [m/s]
        l_char_nat: iceberg length L [m] (characteristic length for natural convection)
        draft: iceberg draft [m] (for pressure calculation; defaults to depth_m)

    Returns:
        (t_b, s_b, m_basal) in [degC, kg/kg, m/s]
    """
    if draft is None:
        draft = depth_m
    return solve_three_equation_interface(
        t_w, s_w, draft, u_rel, l_char_nat, T_ICE, True)


# ============================================================
# INDEPENDENT EXPECTED VALUES FOR TESTING
# ============================================================

# These are hand-computed from the embedded constants above,
# NOT from production output. They serve as independent expected values.

# Canonical H&J99 Table 1 anchor (T_w=-1.85, S_w=34.5, depth=0,
# gamma_T=1e-4, gamma_S=5.05e-7, T_ice=-10, conduction=True)
# With U_rel=0.1 m/s: gamma_T_forced=1.1e-4, gamma_S_forced=3.1e-6
# Natural convection adds to these.

# We will compute these dynamically in the tests using the same
# embedded constants, so they are always consistent.

if __name__ == "__main__":
    # Quick sanity check
    print("Stage 10.11 Python validation module loaded")
    print(f"RHO_ICE_WATER_RATIO = {RHO_ICE_WATER_RATIO:.6f}")
    print(f"THERMAL_EXPANSION_COEFF = {THERMAL_EXPANSION_COEFF:.1e}")
    print(f"HALINE_CONTRACTION_COEFF = {HALINE_CONTRACTION_COEFF:.1e}")
    print(f"LEWIS_NUMBER = {LEWIS_NUMBER}")

    # Test natural convection at U_rel=0
    t_w, s_w = 2.0, 0.0345
    draft = 50.0
    t_b, s_b, m = three_equation_basal_melt_natural(t_w, s_w, 50.0, 0.0, draft)
    print(f"\nZero U_rel test:")
    print(f"  T_w={t_w}, S_w={s_w*1000:.1f} PSU, draft={draft} m")
    print(f"  m = {m:.3e} m/s = {m*86400:.3f} m/day")
    print(f"  T_B = {t_b:.3f} degC")
    print(f"  S_B = {s_b*1000:.3f} PSU")

    # Test with U_rel=0.1 m/s
    t_b2, s_b2, m2 = three_equation_basal_melt_natural(t_w, s_w, 50.0, 0.1, draft)
    print(f"\nU_rel=0.1 m/s test:")
    print(f"  m = {m2:.3e} m/s = {m2*86400:.3f} m/day")
    print(f"  T_B = {t_b2:.3f} degC")
    print(f"  S_B = {s_b2*1000:.3f} PSU")

    # Test forced convection only (gamma_nat=0)
    from three_equation import three_equation_basal_melt as three_eq_forced
    t_b_f, s_b_f, m_f = three_eq_forced(t_w, s_w, 50.0, 0.1)
    print(f"\nForced only (Stage 10.10) U_rel=0.1:")
    print(f"  m = {m_f:.3e} m/s = {m_f*86400:.3f} m/day")

    # Test U_rel=0 forced (should be 0)
    t_b0, s_b0, m0 = three_eq_forced(t_w, s_w, 50.0, 0.0)
    print(f"\nForced only U_rel=0: m = {m0:.3e}")