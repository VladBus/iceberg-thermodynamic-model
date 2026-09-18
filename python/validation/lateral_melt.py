#!/usr/bin/env python3
"""
Stage 10.18A — Independent lateral-melt reference layer.

Independent re-implementations of the lateral (side) melt formulations
relevant to the production iceberg model, kept separate from the Fortran
production code (`src/iceberg*.f90`). The production physics is NOT imported
or modified; this module exists to quantify sensitivity of the lateral-melt
contribution to formulation and geometry convention.

Formulations implemented
------------------------
1. ``legacy_full_height``
   The production legacy formula (Stage 9.1 section 14, Method A):

       m_l = C_LATERAL * <DeltaT>_D            [m/s],  C_LATERAL = 1e-6 m/(s K)

   with the depth-averaged thermal driving

       <DeltaT>_D = (1/D) * int_0^D max(0, T(z) - Tf(z)) dz.

   Geometry (production update in ``iceberg_update_geometry``): the horizontal
   dimensions shrink at the melt rate, L and W both decreasing by m_l*dt, so the
   lateral volume-loss rate is  H*(L + W)*m_l  (full height, half-perimeter
   convention; each of the pair of perpendicular faces seen through dL, dW).

2. ``legacy_submerged``
   Same melt rate m_l but with the "submerged full-perimeter" area convention
   of the model's own (currently unused) helpers ``compute_mass_budget`` /
   ``melt_volume_rates``:

       A_lat = 2*(L + W)*D,   D = H*rho_i/rho_w     m³/s:  2*(L+W)*D*m_l.

   The depth-only variant (half-perimeter, submerged only) is provided as
   ``legacy_submerged_halfperimeter``:  (L+W)*D*m_l, isolating the H-vs-D
   depth convention from the perimeter convention.

3. ``bulk_velocity_dependent``
   Research (literature-based) side melt using the same forced-convection bulk
   closure the model already applies for basal melt (Weeks & Campbell 1973;
   Eckert & Drake 1959; Martin & Adcroft 2010), applied to the side with the
   model's own stated characteristic length for lateral melt, L_char = D:

       m_side = gamma_T * <DeltaT>_D / (rho_i * L_f)
       gamma_T = Nu * k / D
       Re = U_rel * D / nu
       Nu = 0.037 Re^0.8 Pr^(1/3)   (Re >= Re_crit, turbulent)
       Nu = 0.664 Re^0.5 Pr^(1/3)   (Re <  Re_crit, laminar)

   This reproduces the U^0.8 / U^0.5 scaling for side melt measured in
   laboratory studies of iceberg side melting (FitzMaurice, Cenedese &
   Straneo 2016 GRL). Known limitation, identical to the basal closure:
   forced convection gives zero melt at U_rel = 0 (buoyant/plume convection is
   not represented here); the analysis stage quantifies the consequence.

4. Wave erosion
   Assessed separately; the available forcing (ERA5 Q1 2020) contains no wave
   fields, so wave erosion is recorded as NOT TESTABLE with current forcing
   (documented reference only in the analysis stage, not a production formula
   here).

All functions accept and return plain floats/NumPy arrays; unit conversions
are provided by ``m_s_to_m_day`` / ``m_day_to_m_s``.

Run:  python python/tests/test_lateral_melt_parameterizations.py
"""

from __future__ import annotations

import math

import numpy as np

from .basal_melt import (
    LATENT_HEAT,
    PRANDTL_NUMBER,
    REYNOLDS_CRITICAL,
    RHO_ICE,
    RHO_WATER,
    KINEMATIC_VISCOSITY,
    THERMAL_CONDUCTIVITY,
    GRAVITY,
    ocean_freezing_point,
)

# ---------------------------------------------------------------------------
# Module constants (independent copies; documented provenance)
# ---------------------------------------------------------------------------
C_LATERAL = 1.0e-6          # legacy lateral melt coefficient [m/(s K)]
SECONDS_PER_DAY = 86400.0   # [s/day]

# Bulk heat-transfer constants (identical values to production, see
# python/validation/basal_melt.py for provenance).
_PR = PRANDTL_NUMBER
_NU = KINEMATIC_VISCOSITY
_K = THERMAL_CONDUCTIVITY
_RE_CRIT = REYNOLDS_CRITICAL
_TURB_COEF = 0.037
_LAM_COEF = 0.664


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------
def m_s_to_m_day(m_s: float) -> float:
    """Convert a melt rate from [m/s] to [m/day]."""
    return m_s * SECONDS_PER_DAY


def m_day_to_m_s(m_day: float) -> float:
    """Convert a melt rate from [m/day] to [m/s]."""
    return m_day / SECONDS_PER_DAY


# ---------------------------------------------------------------------------
# Depth-averaged thermal driving <DeltaT>_D
# ---------------------------------------------------------------------------
def depth_averaged_thermal_forcing(
    prof_temp_c: np.ndarray,
    prof_salt_psu: np.ndarray,
    prof_depth_m: np.ndarray,
    prof_dz_m: np.ndarray,
    draft_m: float,
) -> float:
    """Depth-averaged thermal driving <DeltaT>_D over the draft [degC].

    Independent NumPy re-implementation of the production
    ``depth_averaged_thermal_forcing`` (iceberg_forcing.f90):

        <DeltaT>_D = (1/D) * sum_k max(0, T_k - Tf_k) * dz_k
                     (+ deepest-level constant extrapolation below the
                        deepest model level, down to the draft)

    with the EOS-80 freezing point Tf_k = ocean_freezing_point(S_k, z_k).
    The model levels are treated as piecewise-constant slabs of thickness
    ``dz_k`` centred on ``z_k`` (trapezoid-free, matching production).

    Parameters
    ----------
    prof_temp_c : array_like
        Temperature [degC] at each model level.
    prof_salt_psu : array_like
        Practical salinity [PSU] at each model level.
    prof_depth_m : array_like
        Mid-level depth [m] of each model level.
    prof_dz_m : array_like
        Layer thickness [m] of each model level.
    draft_m : float
        Draft [m]; the integral runs from the surface to the draft.

    Returns
    -------
    delta_t_avg : float
        Depth-averaged thermal driving [degC] (0.0 if no layer is inside
        the draft).
    """
    t = np.asarray(prof_temp_c, dtype=np.float64)
    s = np.asarray(prof_salt_psu, dtype=np.float64)
    z = np.asarray(prof_depth_m, dtype=np.float64)
    dz = np.asarray(prof_dz_m, dtype=np.float64)

    if t.ndim != 1 or len(t) == 0:
        raise ValueError("profile arrays must be non-empty 1D")

    # Clip each level to the draft (production: skip if level top >= draft).
    z_top = z - 0.5 * dz
    z_bot = np.minimum(z + 0.5 * dz, draft_m)
    inside = (z_top < draft_m) & (z_bot > z_top)
    if not np.any(inside):
        return 0.0

    dz_layer = np.where(inside, z_bot - z_top, 0.0)
    tf = np.array(
        [ocean_freezing_point(ss, zz) for ss, zz in zip(s, z)],
        dtype=np.float64,
    )
    delta_t = np.where(inside, np.maximum(t - tf, 0.0), 0.0)

    integral = float(np.sum(delta_t * dz_layer))
    total_depth = float(np.sum(dz_layer))

    # Constant extrapolation below the deepest level (production behaviour).
    max_z = float(z[-1])
    if draft_m > max_z:
        tf_deep = ocean_freezing_point(float(s[-1]), max_z)
        dT_deep = max(float(t[-1]) - tf_deep, 0.0)
        dz_ext = draft_m - max_z
        integral += dT_deep * dz_ext
        total_depth += dz_ext

    return integral / total_depth if total_depth > 0.0 else 0.0


# ---------------------------------------------------------------------------
# Legacy constant-coefficient formulation
# ---------------------------------------------------------------------------
def legacy_lateral_melt_rate(delta_t_avg_c: float, c_lateral: float = C_LATERAL) -> float:
    """Legacy lateral melt rate ``m_l = C_LATERAL * <DeltaT>_D`` [m/s].

    Returns exactly 0.0 for ``<DeltaT>_D <= 0`` (production guard).
    """
    if delta_t_avg_c <= 0.0:
        return 0.0
    return c_lateral * delta_t_avg_c


# ---------------------------------------------------------------------------
# Geometry: area / volume-loss conventions
# ---------------------------------------------------------------------------
def _draft(H_m: float, rho_ice: float = RHO_ICE, rho_w: float = RHO_WATER) -> float:
    """Hydrostatic draft D = H * rho_i / rho_w [m]."""
    return H_m * rho_ice / rho_w


def lateral_area_full_height(L_m: float, W_m: float, H_m: float) -> float:
    """Production-equivalent lateral area ``A = H*(L + W)`` [m²].

    This is the area that, multiplied by m_l, gives the volume loss of the
    production geometry update (L and W both shrink at m_l):
    ``dV = H*L*m_l*dt + H*W*m_l*dt = H*(L+W)*m_l*dt``.
    """
    return H_m * (L_m + W_m)


def lateral_area_submerged_full_perimeter(
    L_m: float, W_m: float, H_m: float,
    rho_ice: float = RHO_ICE, rho_w: float = RHO_WATER,
) -> float:
    """Submerged full-perimeter lateral area ``A = 2*(L+W)*D`` [m²].

    Convention of the model's (unused) helpers ``compute_mass_budget`` /
    ``melt_volume_rates`` (iceberg_geometry.f90).
    """
    return 2.0 * (L_m + W_m) * _draft(H_m, rho_ice, rho_w)


def lateral_area_submerged_half_perimeter(
    L_m: float, W_m: float, H_m: float,
    rho_ice: float = RHO_ICE, rho_w: float = RHO_WATER,
) -> float:
    """Submerged half-perimeter lateral area ``A = (L+W)*D`` [m²].

    Isolates the depth (H vs D) convention from the perimeter convention.
    """
    return (L_m + W_m) * _draft(H_m, rho_ice, rho_w)


def lateral_volume_rate_full_height(
    m_l: float, L_m: float, W_m: float, H_m: float,
) -> float:
    """Lateral volume-loss rate, full-height production convention [m³/s].

    ``dV/dt = H*(L + W) * m_l`` (matches ``iceberg_update_geometry``).
    """
    return lateral_area_full_height(L_m, W_m, H_m) * m_l


def lateral_volume_rate_submerged_full_perimeter(
    m_l: float, L_m: float, W_m: float, H_m: float,
    rho_ice: float = RHO_ICE, rho_w: float = RHO_WATER,
) -> float:
    """Lateral volume-loss rate, submerged full-perimeter convention [m³/s].

    ``dV/dt = 2*(L+W)*D * m_l`` (helper convention in iceberg_geometry.f90).
    """
    return lateral_area_submerged_full_perimeter(L_m, W_m, H_m, rho_ice, rho_w) * m_l


def lateral_volume_rate_submerged_half_perimeter(
    m_l: float, L_m: float, W_m: float, H_m: float,
    rho_ice: float = RHO_ICE, rho_w: float = RHO_WATER,
) -> float:
    """Lateral volume-loss rate, submerged half-perimeter convention [m³/s].

    ``dV/dt = (L+W)*D * m_l``.
    """
    return lateral_area_submerged_half_perimeter(L_m, W_m, H_m, rho_ice, rho_w) * m_l


def lateral_mass_loss_rate(
    m_l: float, area_m2: float, rho_ice: float = RHO_ICE,
) -> float:
    """Lateral mass-loss rate ``dm/dt = rho_i * A * m_l`` [kg/s]."""
    return rho_ice * area_m2 * m_l


# ---------------------------------------------------------------------------
# Bulk velocity-dependent side melt (research, literature-based closure)
# ---------------------------------------------------------------------------
def nusselt_flat_plate(reynolds: float) -> float:
    """Flat-plate Nusselt number [dimensionless].

    Turbulent (``reynolds >= Re_crit``): 0.037 Re^0.8 Pr^(1/3);
    laminar (``reynolds < Re_crit``): 0.664 Re^0.5 Pr^(1/3).
    ``reynolds <= 0`` returns 0.0 (forced-convection closure not defined).
    """
    if reynolds <= 0.0:
        return 0.0
    if reynolds >= _RE_CRIT:
        return _TURB_COEF * reynolds**0.8 * _PR ** (1.0 / 3.0)
    return _LAM_COEF * math.sqrt(reynolds) * _PR ** (1.0 / 3.0)


def side_heat_transfer_coefficient(
    u_rel: float, char_len_m: float,
) -> float:
    """Side ocean-side heat-transfer coefficient gamma_T [W/(m² K)].

    ``gamma_T = Nu * k / L_char`` with Re = U_rel * L_char / nu. Returns 0.0
    for ``u_rel <= 0`` or ``char_len_m <= 0`` (forced-convection guard,
    mirroring the production basal closure).
    """
    if u_rel <= 0.0 or char_len_m <= 0.0:
        return 0.0
    re = u_rel * char_len_m / _NU
    nu = nusselt_flat_plate(re)
    return nu * _K / char_len_m


def bulk_velocity_dependent_side_melt(
    delta_t_avg_c: float,
    u_rel: float,
    char_len_m: float,
    rho_ice: float = RHO_ICE,
    latent_heat: float = LATENT_HEAT,
) -> float:
    """Research velocity-dependent side melt [m/s].

    ``m_side = gamma_T * <DeltaT>_D / (rho_i * L_f)`` with ``gamma_T`` from
    the flat-plate forced-convection closure (L_char = draft D for the side,
    per the model's Weeks & Campbell 1973 convention).

    Returns 0.0 for ``<DeltaT>_D <= 0`` or ``u_rel <= 0`` (forced convection
    absent; natural/free convection is not represented — an explicit,
    documentable limitation of this research variant).
    """
    if delta_t_avg_c <= 0.0:
        return 0.0
    g_t = side_heat_transfer_coefficient(u_rel, char_len_m)
    return g_t * delta_t_avg_c / (rho_ice * latent_heat)


# ---------------------------------------------------------------------------
# Literature-based formulations (verified sources, see module docstring and
# docs/validation/stage10.18a_lateral_melt_parameterization_audit.md §4)
#
#   Bigg-type forced convection (Bigg et al. 1997; coefficient K quoted by
#   FitzMaurice, Cenedese & Straneo 2017 GRL):
#       M_b = K * U_rel^0.8 * DeltaT / L^0.2           [m/day with K ~ 0.58]
#   Buoyant convection (Neshyba & Josberger 1980 empirical fit, quoted in
#   Cenedese & Straneo 2023 Annu. Rev. Fluid Mech.):
#       M_v = a*DeltaT + b*DeltaT^2                     [m/day]
#       a = 7.62e-3 m/day/degC, b = 1.29e-3 m/day/degC^2
#   FitzMaurice-Cenedese-Straneo (2017 GRL) plume regime split (attached:
#   plume-speed scaling with draft; detached: free-stream scaling with L).
# ---------------------------------------------------------------------------
BIGG_K_OCEAN = 0.58          # [-] Bigg-type forced-convection coefficient
BIGG_K_LAB = 0.75            # [-] laboratory setting (FitzMaurice et al. 2017)
NESHYBA_A = 7.62e-3          # [m/day per degC] buoyant-convection linear coeff
NESHYBA_B = 1.29e-3          # [m/day per degC^2] buoyant-convection quadratic coeff
PLUME_SPEED_LAB = 0.025      # [m/s] laboratory plume speed |w| (FitzMaurice 2017)


def bigg1997_forced_convection_melt_rate(
    u_rel: float, delta_t_c: float, L_m: float, k_coeff: float = BIGG_K_OCEAN,
) -> float:
    """Bigg-type forced-convection side melt [m/s].

    ``M_b = K * U_rel^0.8 * DeltaT / L^0.2`` (literature form reports m/day;
    converted to m/s here). Coefficients: K = 0.58 (ocean, FitzMaurice et al.
    2017); K = 0.75 (laboratory). Returns 0.0 for ``delta_t_c <= 0`` or
    ``u_rel <= 0`` (forced convection absent).
    """
    if delta_t_c <= 0.0 or u_rel <= 0.0:
        return 0.0
    return m_day_to_m_s(k_coeff * u_rel**0.8 * delta_t_c / L_m**0.2)


def neshyba_josberger_buoyant_melt_rate(
    delta_t_c: float,
    a: float = NESHYBA_A, b: float = NESHYBA_B,
) -> float:
    """Neshyba-Josberger buoyant-convection side melt [m/s].

    ``M_v = a*DeltaT + b*DeltaT^2`` (m/day in the literature; converted to
    m/s here). Velocity-independent representation of the free-convection
    (meltwater-plume) term. Returns 0.0 for ``delta_t_c <= 0``.
    """
    if delta_t_c <= 0.0:
        return 0.0
    return m_day_to_m_s(a * delta_t_c + b * delta_t_c**2)


def fitzmaurice_plume_side_melt(
    u_rel: float, delta_t_c: float, L_m: float, draft_m: float,
    k_coeff: float = BIGG_K_OCEAN, plume_speed: float = PLUME_SPEED_LAB,
    plume_delta_t_c: float | None = None,
) -> float:
    """FitzMaurice-Cenedese-Straneo (2017 GRL) plume-regime side melt [m/s].

    Attached plumes (``u_rel < plume_speed``):  M = K*w^0.8*dT_p/D^0.2
    Detached plumes (``u_rel >= plume_speed``): M = K*U_rel^0.8*dT/L^0.2

    ``plume_delta_t_c`` is the plume driving temperature (T_p - T_i); when
    omitted it defaults to ``delta_t_c`` (ambient driving) — a documented
    approximation because the plume temperature is not a model state. Both
    piecewise branches are thermal melt (no mechanical erosion).
    """
    if delta_t_c <= 0.0:
        return 0.0
    dT_p = delta_t_c if plume_delta_t_c is None else plume_delta_t_c
    if u_rel < plume_speed:
        return m_day_to_m_s(k_coeff * plume_speed**0.8 * dT_p / max(draft_m, 1e-3) ** 0.2)
    return m_day_to_m_s(k_coeff * u_rel**0.8 * delta_t_c / max(L_m, 1e-3) ** 0.2)


# ---------------------------------------------------------------------------
# Scaling diagnostics (numeric, independent of assumed exponents)
# ---------------------------------------------------------------------------
def numeric_exponent(x_hi: float, x_lo: float, y_hi: float, y_lo: float) -> float:
    """Exponent ``n`` such that ``y ~ x**n`` between two points.

    n = log(y_hi / y_lo) / log(x_hi / x_lo). Raises if x or y are non-positive
    or equal (log undefined).
    """
    if x_hi <= 0.0 or x_lo <= 0.0 or y_hi <= 0.0 or y_lo <= 0.0:
        raise ValueError("numeric_exponent requires strictly positive inputs")
    return math.log(y_hi / y_lo) / math.log(x_hi / x_lo)


__all__ = [
    "BIGG_K_OCEAN",
    "BIGG_K_LAB",
    "C_LATERAL",
    "NESHYBA_A",
    "NESHYBA_B",
    "PLUME_SPEED_LAB",
    "SECONDS_PER_DAY",
    "bigg1997_forced_convection_melt_rate",
    "bulk_velocity_dependent_side_melt",
    "depth_averaged_thermal_forcing",
    "fitzmaurice_plume_side_melt",
    "lateral_area_full_height",
    "lateral_area_submerged_full_perimeter",
    "lateral_area_submerged_half_perimeter",
    "lateral_mass_loss_rate",
    "lateral_volume_rate_full_height",
    "lateral_volume_rate_submerged_full_perimeter",
    "lateral_volume_rate_submerged_half_perimeter",
    "legacy_lateral_melt_rate",
    "m_day_to_m_s",
    "m_s_to_m_day",
    "neshyba_josberger_buoyant_melt_rate",
    "numeric_exponent",
    "nusselt_flat_plate",
    "side_heat_transfer_coefficient",
]