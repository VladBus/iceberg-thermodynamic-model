"""Stage 10.10 — independent Python three-equation ice-ocean interface layer.

This module re-implements, in pure Python, the three-equation ice-ocean
interface (Holland & Jenkins 1999; Jenkins et al. 2010) introduced to the
iceberg model at Stage 10.10. It is intentionally independent of the Fortran
implementation: it does not call the Fortran executable, import compiled
modules, or parse Fortran output. The equations and constants below are
reproduced from the documented production formulation
(``src/iceberg_types.f90``, ``src/iceberg_thermodynamics.f90``, equation
ledger ``docs/model/model_equation_ledger.md`` section 10.2) so that this
package may serve as a second, independently executable numerical reference
for cross-validation and later calibration work.

Equations reproduced (Stage 10.10 production formulation):

    Tf       = (A0 + A1*sqrt(S) - A2*S)*S + BP*P            [degC]
    S_B      = gamma_S * S_w / (m + gamma_S)                [Eq. III, S_i = 0]
    T_B      = Tf(S_B, P)                                   [Eq. I]
    gamma_T  = K_T * U_rel,  gamma_S = K_S * U_rel          [J2010 Table 2]
    F(m)     = rho_w*c_w*gamma_T*(T_w - T_B)
               - m*rho_i*(L_f + c_i*max(T_B - T_i, 0))      [Eq. II]
    F(0) > 0 for T_w > Tf(S_w)  =>  bisection on [0, m_hi]

The melt rate m in Eq. II is in the ice frame (m is a volume loss of ice),
which is why the ice density multiplies both the latent-heat and the
conduction terms. This matches the production closure.

Note: production code stores salinity as a mass fraction (kg/kg); the public
Python API uses the practical salinity in PSU (mass fraction * 1000), matching
the documented equations and the Stage 10.7/10.8 validation layers.

Units: all inputs/outputs SI (m, s, kg, degC, W/m^2), salinity in PSU,
melting rates in m/s. ``gamma_t``/``gamma_s`` are velocity-scale exchange
coefficients in [m/s].
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Production constants (embedded from src/iceberg_types.f90; Stage 10.10).
# Fortran compiles with float32; Python uses float64 -> tiny, documented
# differences at the last float32 digit are expected and tolerated.
# ---------------------------------------------------------------------------
RHO_ICE = 910.0             # ice density [kg/m^3]
RHO_WATER = 1028.0          # reference seawater density [kg/m^3]
LATENT_HEAT = 334000.0      # latent heat of fusion [J/kg]
GRAVITY = 9.80665           # gravitational acceleration [m/s^2]

# Stage 10.10 three-equation closure constants (H&J99 / J2010 Table 2)
CP_SEAWATER = 3974.0        # seawater heat capacity c_w [J/(kg K)] (H&J99)
CP_ICE_3EQ = 2009.0         # ice heat capacity c_i [J/(kg K)] (H&J99)
THREE_EQ_KT = 1.1e-3        # K_T = sqrt(C_d)*Gamma_T [-] (J2010 Table 2)
THREE_EQ_KS = 3.1e-5        # K_S = sqrt(C_d)*Gamma_S [-] (J2010 Table 2)
T_ICE = -10.0               # internal ice temperature [degC]

# EOS-80 / UNESCO 1983 (Fofonoff & Millard 1983; Gill 1982 Eq. 3.5.2)
EOS_FP_A0 = -0.0575             # [degC/PSU]
EOS_FP_A1 = 1.710523e-3         # [degC/PSU^(3/2)]
EOS_FP_A2 = 2.154996e-4         # [degC/PSU^2]
EOS_FP_BP = -7.53e-4            # [degC/dbar]

# Numerical-noise guard from production compute_basal_melt (applied, as in
# production, by the wrapper, not by the raw solver).
MELT_RATE_MIN = 1.0e-12         # [m/s]

# Bisection settings matching the production solver.
MAX_DOUBLE = 60
MAX_BISECT = 60


def ocean_freezing_point(salinity_psu: float, depth_m: float) -> float:
    """EOS-80 freezing point [degC] of seawater of practical salinity (PSU)."""
    p_dbar = RHO_WATER * GRAVITY * depth_m / 1.0e4
    return (
        (EOS_FP_A0 + EOS_FP_A1 * math.sqrt(salinity_psu) - EOS_FP_A2 * salinity_psu)
        * salinity_psu
        + EOS_FP_BP * p_dbar
    )


def transfer_coefficients(
    u_rel: float,
    k_t: float = THREE_EQ_KT,
    k_s: float = THREE_EQ_KS,
) -> tuple[float, float]:
    """Velocity-scale exchange coefficients gamma_T, gamma_S [m/s].

    J2010 Table 2: gamma_T = K_T * U_rel, gamma_S = K_S * U_rel where
    K_T = sqrt(C_d)*Gamma_T = 1.1e-3, K_S = sqrt(C_d)*Gamma_S = 3.1e-5.
    """
    return k_t * u_rel, k_s * u_rel


def solve_three_equation_interface(
    ocean_temperature_c: float,
    salinity_psu: float,
    depth_m: float,
    u_rel: float,
    gamma_t: float,
    gamma_s: float,
    t_ice: float = T_ICE,
    use_conduction: bool = True,
) -> tuple[float, float, float]:
    """Solve the three-equation ice-ocean interface.

    Parameters
    ----------
    ocean_temperature_c : float
        Far-field ocean temperature [degC].
    salinity_psu : float
        Far-field practical salinity [PSU].
    depth_m : float
        Depth of the interface [m] (for the pressure term of Eq. I).
    u_rel : float
        Relative ocean speed at the interface [m/s].
    gamma_t, gamma_s : float
        Velocity-scale transfer coefficients [m/s] (Eq. II, III).
    t_ice : float
        Internal ice temperature [degC]; used by the conduction term.
    use_conduction : bool
        Include the conductive heat flux into the ice interior (Eq. II).

    Returns
    -------
    m_basal : float
        Basal melt rate [m/s] (mass-equivalent ice volume loss rate).
    t_interface : float
        Interface temperature T_B [degC] (Eq. I).
    s_interface : float
        Interface salinity S_B [PSU] (Eq. III).

    Edge behaviour (mirrors production):
      * u_rel <= 0 or gamma_t <= 0 or T_w <= Tf(S_w, P):
        m = 0, S_B = S_w, T_B = Tf(S_w, P)  (no natural-convection branch).
      * S_w <= 0 (fresh water): heat-only balance with S_B = 0.
      * gamma_s <= 0: heat-only balance with S_B = S_w.
    """
    tf_w = ocean_freezing_point(salinity_psu, depth_m)

    # No-ocean-flux edge: m = 0, interface at the far-field freezing point.
    if u_rel <= 0.0 or gamma_t <= 0.0 or ocean_temperature_c <= tf_w:
        return 0.0, tf_w, salinity_psu

    # Fresh-water edge (S_w <= 0): no salt budget, heat-only.
    if salinity_psu <= 0.0:
        t_b = ocean_freezing_point(0.0, depth_m)
        latent = _latent_heat_latent(t_b, t_ice, use_conduction)
        flux = RHO_WATER * CP_SEAWATER * gamma_t * (ocean_temperature_c - t_b)
        if flux > 0.0 and latent > 0.0:
            return flux / latent, t_b, 0.0
        return 0.0, t_b, 0.0

    # gamma_s <= 0 edge: no freshening, S_B = S_w.
    if gamma_s <= 0.0:
        latent = _latent_heat_latent(tf_w, t_ice, use_conduction)
        flux = RHO_WATER * CP_SEAWATER * gamma_t * (ocean_temperature_c - tf_w)
        if flux > 0.0 and latent > 0.0:
            return flux / latent, tf_w, salinity_psu
        return 0.0, tf_w, salinity_psu

    # Main path: bisection on m in [0, m_hi].
    m_lo = 0.0
    m_est = (
        RHO_WATER
        * CP_SEAWATER
        * gamma_t
        * (ocean_temperature_c - tf_w)
        / (RHO_ICE * LATENT_HEAT)
    )
    m_hi = max(m_est, 1.0e-9)

    # Grow upper bound until F(m_hi) <= 0.
    iter_ = 0
    while True:
        s_b = _s_interface(gamma_s, salinity_psu, m_hi)
        t_b = ocean_freezing_point(s_b, depth_m)
        f_val = _f_residual(ocean_temperature_c, t_b, gamma_t, m_hi, t_ice, use_conduction)
        if f_val <= 0.0 or iter_ >= MAX_DOUBLE:
            break
        m_hi *= 2.0
        iter_ += 1

    # Bisection (60 iterations, float64-exact reproduces float32 result).
    for iter_ in range(MAX_BISECT):
        m_mid = 0.5 * (m_lo + m_hi)
        s_b = _s_interface(gamma_s, salinity_psu, m_mid)
        t_b = ocean_freezing_point(s_b, depth_m)
        f_val = _f_residual(ocean_temperature_c, t_b, gamma_t, m_mid, t_ice, use_conduction)
        if f_val > 0.0:
            m_lo = m_mid
        else:
            m_hi = m_mid

    m_basal = 0.5 * (m_lo + m_hi)
    s_interface = _s_interface(gamma_s, salinity_psu, m_basal)
    t_interface = ocean_freezing_point(s_interface, depth_m)
    return m_basal, t_interface, s_interface


def three_equation_basal_melt(
    ocean_temperature_c: float,
    salinity_psu: float,
    depth_m: float,
    u_water: float,
    v_water: float = 0.0,
    u_ice: float = 0.0,
    v_ice: float = 0.0,
    k_t: float = THREE_EQ_KT,
    k_s: float = THREE_EQ_KS,
    t_ice: float = T_ICE,
    use_conduction: bool = True,
) -> tuple[float, float, float]:
    """Production-equivalent end-to-end three-equation basal melt [m/s].

    Mirrors ``compute_basal_melt`` (scheme = THREE_EQUATION): applies the
    ``delta_t > 0`` gate and the MELT_RATE_MIN noise guard around the raw
    closure solution. Returns ``(m_basal, t_interface, s_interface)``.
    """
    tf_w = ocean_freezing_point(salinity_psu, depth_m)
    delta_t = ocean_temperature_c - tf_w
    if delta_t <= 0.0:
        return 0.0, tf_w, salinity_psu

    u_rel = math.hypot(u_water - u_ice, v_water - v_ice)
    gamma_t, gamma_s = transfer_coefficients(u_rel, k_t, k_s)

    m_basal, t_iface, s_iface = solve_three_equation_interface(
        ocean_temperature_c, salinity_psu, depth_m, u_rel, gamma_t, gamma_s,
        t_ice=t_ice, use_conduction=use_conduction,
    )
    if m_basal < MELT_RATE_MIN:
        return 0.0, tf_w, salinity_psu
    return m_basal, t_iface, s_iface


# ---------------------------------------------------------------------------
# Internal helpers (Eq. II/III algebra).
# ---------------------------------------------------------------------------
def _s_interface(gamma_s: float, s_w: float, m: float) -> float:
    """S_B from Eq. III: gamma_S*(S_w - S_B) = m*S_B  =>  S_B = gamma_S*S_w/(m+gamma_S)."""
    return gamma_s * s_w / (m + gamma_s)


def _latent_heat_latent(t_b: float, t_ice: float, use_conduction: bool) -> float:
    """Latent-heat denominator of Eq. II [J/m^3]: rho_i*(L_f + c_i*max(T_B-T_i,0))."""
    latent = RHO_ICE * LATENT_HEAT
    if use_conduction:
        latent += RHO_ICE * CP_ICE_3EQ * max(t_b - t_ice, 0.0)
    return latent


def _f_residual(
    t_w: float, t_b: float, gamma_t: float, m: float, t_ice: float, use_conduction: bool
) -> float:
    """Equilibrium residual F(m) of Eq. II [W/m^2]."""
    ocean_flux = RHO_WATER * CP_SEAWATER * gamma_t * (t_w - t_b)
    latent = _latent_heat_latent(t_b, t_ice, use_conduction)
    return ocean_flux - m * latent