"""Stage 10.8.1 — independent Python basal-melt validation layer.

This module re-implements, in pure Python, the mathematical formulation of
the production basal-melt chain of the iceberg model. It is intentionally
independent of the Fortran implementation: it does not call the Fortran
executable, import compiled modules, or parse Fortran output. The equations
and constants below are reproduced from the documented production formulation
(``src/iceberg_types.f90``, ``src/iceberg_thermodynamics.f90`` and the
equation ledger ``docs/model/model_equation_ledger.md``, sections 9-10) so that
this package may serve as a second, independently executable numerical
reference for cross-validation, sensitivity analysis, plotting and later
uncertainty work.

Equations reproduced (production formulation, NOT modified):

    Tf       = (A0 + A1*sqrt(S) - A2*S)*S + BP*P            [degC]
    S        = practical salinity [PSU]; P = rho_w*g*z/1e4  [dbar]
    U_rel    = sqrt((u_water - u_ice)^2 + (v_water - v_ice)^2)
    Re       = U_rel * L_char / nu
    Nu       = 0.664 * Re^0.5 * Pr^(1/3)     Re <  Re_crit   (laminar)
    Nu       = 0.037 * Re^0.8 * Pr^(1/3)     Re >= Re_crit   (turbulent)
    gamma_T  = Nu * k / L_char
    DeltaT   = max(T(D) - Tf(D), 0)
    m_basal  = gamma_T * DeltaT / (rho_ice * L_f)            [m/s]

Note: production code stores salinity as a mass fraction (kg/kg); the public
Python API uses the practical salinity in PSU (mass fraction * 1000), matching
the documented equations and the Stage 10.8.1 specification.

Units: all inputs/outputs SI (m, s, kg, K/degC, W, Pa), salinity in PSU.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Production constants (embedded from src/iceberg_types.f90, lines 34-119).
# Compiled with float32 in Fortran; Python uses float64 -> tiny, documented
# differences at the last float32 digit are expected and tolerated.
# ---------------------------------------------------------------------------
RHO_ICE = 910.0             # ice density [kg/m^3]
RHO_WATER = 1028.0          # reference seawater density [kg/m^3]
LATENT_HEAT = 334000.0      # latent heat of fusion [J/kg]
GRAVITY = 9.80665           # gravitational acceleration [m/s^2]

# EOS-80 / UNESCO 1983 (Fofonoff & Millard 1983; Gill 1982 Eq. 3.5.2)
EOS_FP_A0 = -0.0575            # [degC/PSU]
EOS_FP_A1 = 1.710523e-3        # [degC/PSU^(3/2)]
EOS_FP_A2 = 2.154996e-4        # [degC/PSU^2]
EOS_FP_BP = -7.53e-4           # [degC/dbar]

# Ocean-side heat transfer (Stage 10.6): PRANDTL_NUMBER, KINEMATIC_VISCOSITY,
# THERMAL_CONDUCTIVITY, REYNOLDS_CRITICAL from src/iceberg_types.f90.
PRANDTL_NUMBER = 13.8          # [-]
KINEMATIC_VISCOSITY = 1.82e-6  # [m^2/s]
THERMAL_CONDUCTIVITY = 0.56    # [W/(m K)]
REYNOLDS_CRITICAL = 5.0e5      # laminar/turbulent transition (flat plate)

# Numerical-noise guard from production compute_basal_melt.
MELT_RATE_MIN = 1.0e-12        # [m/s]


def ocean_freezing_point(salinity_psu: float, depth_m: float) -> float:
    """EOS-80 freezing point [degC].

    Parameters
    ----------
    salinity_psu : float
        Practical salinity in PSU (mass fraction * 1000).
    depth_m : float
        Depth below the surface [m].

    Returns
    -------
    Tf : float
        Freezing temperature [degC].
    """
    p_dbar = RHO_WATER * GRAVITY * depth_m / 1.0e4
    return (
        (EOS_FP_A0 + EOS_FP_A1 * math.sqrt(salinity_psu) - EOS_FP_A2 * salinity_psu)
        * salinity_psu
        + EOS_FP_BP * p_dbar
    )


def relative_velocity(
    u_water: float, v_water: float, u_ice: float, v_ice: float
) -> float:
    """Relative ocean-velocity magnitude at a point [m/s]."""
    return math.sqrt((u_water - u_ice) ** 2 + (v_water - v_ice) ** 2)


def reynolds_number(u_rel: float, length_m: float, nu: float = KINEMATIC_VISCOSITY) -> float:
    """Reynolds number Re = U_rel * L_char / nu [-].

    If ``u_rel <= 0`` or ``length_m <= 0`` the Reynolds number is not defined
    for the forced-convection closure and 0.0 is returned (matches the
    production guard in ``ocean_heat_transfer_coeff``).
    """
    if u_rel <= 0.0 or length_m <= 0.0:
        return 0.0
    return u_rel * length_m / nu


def nusselt_number(
    reynolds: float, prandtl: float = PRANDTL_NUMBER, re_crit: float = REYNOLDS_CRITICAL
) -> float:
    """Flat-plate Nusselt number [-].

    Laminar (``reynolds < re_crit``): ``Nu = 0.664 Re^0.5 Pr^(1/3)``;
    turbulent (``reynolds >= re_crit``): ``Nu = 0.037 Re^0.8 Pr^(1/3)``.
    The transition condition matches production: exactly ``reynolds ==
    re_crit`` selects the turbulent branch.
    """
    if reynolds < re_crit:
        return 0.664 * math.sqrt(reynolds) * prandtl ** (1.0 / 3.0)
    return 0.037 * reynolds**0.8 * prandtl ** (1.0 / 3.0)


def ocean_heat_transfer_coefficient(
    u_rel: float,
    length_m: float,
    prandtl: float = PRANDTL_NUMBER,
    nu: float = KINEMATIC_VISCOSITY,
    k: float = THERMAL_CONDUCTIVITY,
    re_crit: float = REYNOLDS_CRITICAL,
) -> float:
    """Ocean-side heat-transfer coefficient gamma_T [W/(m^2 K)].

    ``gamma_T = Nu * k / L_char`` with the piecewise laminar/turbulent Nu.
    Returns 0.0 for ``u_rel <= 0`` or ``length_m <= 0``, reproducing the
    production guard. Known limitation: the forced-convection closure gives
    zero transfer at rest; natural convection is not represented.
    """
    if u_rel <= 0.0 or length_m <= 0.0:
        return 0.0
    re = reynolds_number(u_rel, length_m, nu)
    nu_n = nusselt_number(re, prandtl, re_crit)
    return nu_n * k / length_m


def thermal_driving(ocean_temperature: float, salinity_psu: float, depth_m: float) -> float:
    """Non-negative thermal driving DeltaT = max(T(D) - Tf(D), 0) [degC]."""
    return max(ocean_temperature - ocean_freezing_point(salinity_psu, depth_m), 0.0)


def basal_melt_rate(
    ocean_temperature: float,
    salinity_psu: float,
    depth_m: float,
    u_water: float,
    v_water: float,
    u_ice: float,
    v_ice: float,
    length_m: float,
    rho_ice: float = RHO_ICE,
    latent_heat: float = LATENT_HEAT,
) -> float:
    """Basal melt rate of an idealized iceberg [m/s].

    Full production chain:

        1.  Tf  = ocean_freezing_point(S, depth)
        2.  dT  = max(T(D) - Tf(D), 0)
        3.  if dT <= 0: return 0.0
        4.  U_rel = relative_velocity(...)
        5.  gamma_T = ocean_heat_transfer_coefficient(U_rel, L_char)
        6.  m_basal = gamma_T * dT / (rho_ice * L_f)
        7.  if m_basal < MELT_RATE_MIN: m_basal = 0.0  (numerical-noise guard)

    Returns the melt rate in [m/s]. No empirical calibration is applied.
    """
    delta_t = thermal_driving(ocean_temperature, salinity_psu, depth_m)
    if delta_t <= 0.0:
        return 0.0

    u_rel = relative_velocity(u_water, v_water, u_ice, v_ice)
    gamma_t = ocean_heat_transfer_coefficient(u_rel, length_m)

    m_basal = gamma_t * delta_t / (rho_ice * latent_heat)
    if m_basal < MELT_RATE_MIN:
        return 0.0
    return m_basal


# ---------------------------------------------------------------------------
# Optional convenience helpers (secondary; do not change the physics above).
# ---------------------------------------------------------------------------
def basal_melt_rate_vectorized(
    ocean_temperature,
    salinity_psu,
    depth_m,
    u_water,
    v_water,
    u_ice=0.0,
    v_ice=0.0,
    length_m=100.0,
    rho_ice=RHO_ICE,
    latent_heat=LATENT_HEAT,
):
    """Vectorized basal melt rate using NumPy broadcasting.

    Elementwise equivalent to :func:`basal_melt_rate`; accepts scalars or
    arrays (broadcast together). Useful for later sensitivity/parameter
    sweeps. Requires ``numpy`` (present in the project conda environment).
    """
    import numpy as np

    t = np.asarray(ocean_temperature, dtype=np.float64)
    s = np.asarray(salinity_psu, dtype=np.float64)
    z = np.asarray(depth_m, dtype=np.float64)
    uw = np.asarray(u_water, dtype=np.float64)
    vw = np.asarray(v_water, dtype=np.float64)
    ui = np.asarray(u_ice, dtype=np.float64)
    vi = np.asarray(v_ice, dtype=np.float64)
    ll = np.asarray(length_m, dtype=np.float64)

    p_dbar = RHO_WATER * GRAVITY * z / 1.0e4
    tf = (EOS_FP_A0 + EOS_FP_A1 * np.sqrt(s) - EOS_FP_A2 * s) * s + EOS_FP_BP * p_dbar
    delta_t = np.maximum(t - tf, 0.0)

    u_rel = np.sqrt((uw - ui) ** 2 + (vw - vi) ** 2)
    re = np.where((u_rel > 0.0) & (ll > 0.0), u_rel * ll / KINEMATIC_VISCOSITY, 0.0)
    nu_n = np.where(
        re < REYNOLDS_CRITICAL,
        0.664 * np.sqrt(re) * PRANDTL_NUMBER ** (1.0 / 3.0),
        0.037 * re**0.8 * PRANDTL_NUMBER ** (1.0 / 3.0),
    )
    gamma_t = np.where((u_rel > 0.0) & (ll > 0.0), nu_n * THERMAL_CONDUCTIVITY / ll, 0.0)

    m = gamma_t * delta_t / (rho_ice * latent_heat)
    return np.where(m < MELT_RATE_MIN, 0.0, m)