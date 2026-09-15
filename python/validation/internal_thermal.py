#!/usr/bin/env python3
"""
Stage 10.12 — Independent Python validation of prognostic internal thermal
evolution of the iceberg.

Reproduces the production implementation from `src/iceberg_types.f90`:

    compute_iceberg_thermal_capacity      (lines ~509-516)
    compute_iceberg_conductive_coupling   (lines ~523-537)
    update_iceberg_internal_temperature   (lines ~556-594)

and the basal heat-flux coupling from `src/iceberg_thermodynamics.f90`
(`iceberg_thermodynamics_step`, Stage 10.12 block).

Equations (Stage 10.12, two-layer lumped model):

    Surface layer (thickness H_EFF = 0.5 m):
        heat flux into internal layer from surface
        q_cond = 2 * K_ICE * (T_surface - T_ice) / H
        (2 = harmonic factor for two half-thicknesses H/2 each,
         mean distance between layer centres; K_ICE = 2.2 W/(m K))

    Internal layer (thickness H_int = max(H - H_EFF, H_MIN_INT)):
        C_int = rho_i * c_i * H_int                [J/(K m^2)]
        dT_ice/dt = (q_cond - q_bot) / C_int       [K/s]

    Basal heat flux (from three-equation interface, sensible part):
        q_bot = m_basal * rho_i * CP_ICE_3EQ * max(T_B - T_ice, 0)   [W/m^2]

    Explicit Euler update with numerical guards:
        T_ice^{n+1} = clamp(T_ice + dt * (q_cond - q_bot) / C_int,
                            T_ICE_MIN, T_ICE_MAX)
        t_ice_bound = .true. iff the clamp was applied

    Early return (no change, bound = False, dT/dt = 0) when
    C_int <= 0 or dt <= 0.

Constants (production values, src/iceberg_types.f90 lines 43-52, 178):
    RHO_ICE     = 910.0   [kg/m^3]
    C_ICE       = 2100.0  [J/(kg K)]      (lumped internal layer)
    CP_ICE_3EQ  = 2009.0  [J/(kg K)]      (H&J99 c_i, three-equation)
    H_EFF       = 0.5     [m]
    H_MIN_INT   = 0.5     [m]
    K_ICE       = 2.2     [W/(m K)]
    T_ICE_INIT  = -10.0   [degC]
    T_ICE_MIN   = -100.0  [degC] (numerical guard)
    T_ICE_MAX   = 0.0     [degC] (melting point)

All units here are the production thermodynamic units: temperature degC,
length m, time s, flux W/m^2.
"""

from __future__ import annotations

# Production constants (src/iceberg_types.f90, lines 43-52, 178).
RHO_ICE: float = 910.0
C_ICE: float = 2100.0
CP_ICE_3EQ: float = 2009.0
H_EFF: float = 0.5
H_MIN_INT: float = 0.5
K_ICE: float = 2.2
T_ICE_INIT: float = -10.0
T_ICE_MIN: float = -100.0
T_ICE_MAX: float = 0.0


def compute_thermal_capacity(H: float) -> tuple[float, float]:
    """Replica of compute_iceberg_thermal_capacity (src/iceberg_types.f90).

    Returns (c_eff_int, h_int):
        h_int    = max(H - H_EFF, H_MIN_INT)                [m]
        c_eff_int = RHO_ICE * C_ICE * h_int                 [J/(K m^2)]
    """
    h_int = max(H - H_EFF, H_MIN_INT)
    c_eff_int = RHO_ICE * C_ICE * h_int
    return c_eff_int, h_int


def compute_conductive_coupling(T_surface: float, T_ice: float, H: float) -> float:
    """Replica of compute_iceberg_conductive_coupling.

    q_cond = 2 * K_ICE * (T_surface - T_ice) / H        [W/m^2]
    Sign convention: q_cond > 0 -> surface warmer than interior -> warming.
    """
    return 2.0 * K_ICE * (T_surface - T_ice) / H


def basal_heat_flux(m_basal: float, T_B: float, T_ice: float) -> float:
    """Basal sensible heat flux coupling (src/iceberg_thermodynamics.f90).

    q_bot = m_basal * RHO_ICE * CP_ICE_3EQ * max(T_B - T_ice, 0)  [W/m^2]

    q_bot >= 0 by construction: meltwater interface warmer than the
    interior is an energy SINK for the internal layer (cooling).
    """
    return m_basal * RHO_ICE * CP_ICE_3EQ * max(T_B - T_ice, 0.0)


def update_internal_temperature(
    T_ice: float,
    H: float,
    dt: float,
    q_cond: float,
    q_bot: float,
) -> tuple[float, float, float, float, bool]:
    """Replica of update_iceberg_internal_temperature.

    Explicit Euler step with clamping to [T_ICE_MIN, T_ICE_MAX]:

        dT_dt = (q_cond - q_bot) / C_int
        T_new = clamp(T_ice + dt * dT_dt, T_ICE_MIN, T_ICE_MAX)

    Returns (T_new, dT_dt, c_eff_int, h_int, bound).

    bound is True iff the clamp was applied (T crossed a limit).
    Early return (T_new = T_ice, dT_dt = 0, bound = False) when
    C_int <= 0 or dt <= 0 — mirrors the production guard.
    """
    c_eff_int, h_int = compute_thermal_capacity(H)

    if c_eff_int <= 0.0 or dt <= 0.0:
        return T_ice, 0.0, c_eff_int, h_int, False

    dT_dt = (q_cond - q_bot) / c_eff_int
    T_new = T_ice + dT_dt * dt

    bound = False
    if T_new > T_ICE_MAX:
        T_new = T_ICE_MAX
        bound = True
    elif T_new < T_ICE_MIN:
        T_new = T_ICE_MIN
        bound = True

    return T_new, dT_dt, c_eff_int, h_int, bound
