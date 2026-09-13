#!/usr/bin/env python3
"""
Stage 10.11.3 — Sensitivity analysis of the natural-convection basal melt closure.

Independent, *parameterized* implementation of the Stage 10.11 production
formulation (Fujii et al. 1973 horizontal-plate correlation + Churchill 1977
mixed convection, applied to the three-equation ice-ocean interface).

Purpose
-------
Quantify the sensitivity of the natural-convection branch to every free
parameter and to the Rayleigh-number cap, and expose the regime structure
(cap dominance, haline dominance, branch discontinuity, crossover velocity).

This is an AUDIT / SENSITIVITY tool. It does not run the Fortran model and
never modifies production physics. The production baseline is replicated in
Section B (sanity check vs embedded stage-10.11 anchors).

Method
------
Everything is computed from embedded constants (identical to the production
values in `src/iceberg_types.f90`) with *parameterized* core functions, so a
single parameter (e.g. RAYLEIGH_MAX, Le, beta_S, Churchill n) can be swept
while keeping the rest at production values. The three-equation interface is
solved with the same explicit bisection structure as
`solve_three_equation_interface_natural` in `src/iceberg_thermodynamics.f90`.

Tables produced (stdout; CSV optional via --out-dir):
  A  Ra-cap sweep          RAYLEIGH_MAX = 1e7..1e13, inf -> Nu, gamma_T_nat, m
  B  Baseline replica      anchor cross-check (gamma_T_nat=4.43e-7, m=1.638e-8)
  C  Length sweep          L = 10..400 m -> Ra, capped?, Nu, gamma, m, gamma*L
  D  U_rel sweep           U = 0..1 m/s -> forced/nat/eff gamma, excess, m
  E  Delta-T sweep         T_w - Tf = 0.5..4 K -> gamma (fixed?), m, m/dT
  F  Salinity sweep        S_w = 30..35 PSU -> Tf, S_B, gamma, m
  G  Haline/Le diagnostic  production(+Le=100) vs Le=0 vs NEGATIVE-SIGN variant
                           (the negative variant is EXPLICITLY NON-PRODUCTION,
                           exploratory physics only)
  H  beta_T / beta_S +-1 order   (expect invariance in capped regime)
  I  Churchill exponent n   n = 1..5 at U_rel=0.1 -> eff gamma, excess
  J  Crossover velocity     U* = gamma_T_nat / K_T vs L (nat == forced)

Run:
    conda run -n iceberg-thermodynamic-model python \
        python/analysis/stage10_11_3_natural_convection_sensitivity.py
    # optional CSV output:
    ... --out-dir python/analysis/results/stage10_11_3
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# ============================================================
# EMBEDDED PRODUCTION CONSTANTS (src/iceberg_types.f90, Stage 10.11)
# ============================================================

RHO_WATER = 1028.0            # kg/m^3
RHO_ICE = 910.0               # kg/m^3
LATENT_HEAT = 334000.0        # J/kg
CP_SEAWATER = 3974.0          # J/(kg K)
CP_ICE_3EQ = 2009.0           # J/(kg K)
T_ICE = -10.0                 # degC (model-selected)
THREE_EQ_KT = 1.1e-3          # m/s  (J2010 Table 2)
THREE_EQ_KS = 3.1e-5          # m/s  (J2010 Table 2)
RHO_ICE_WATER_RATIO = RHO_ICE / RHO_WATER

THERMAL_EXPANSION_COEFF = 3.0e-5      # 1/K (beta_T)
HALINE_CONTRACTION_COEFF = 7.8e-4     # 1/PSU (beta_S)
LEWIS_NUMBER = 100.0                  # Le = alpha / D_S

NU_LAMINAR_COEFF = 0.27
NU_LAMINAR_EXP = 0.25
NU_TURBULENT_COEFF = 0.15
NU_TURBULENT_EXP = 1.0 / 3.0
RAYLEIGH_TRANSITION = 1.0e7
RAYLEIGH_MAX = 1.0e10

MIXED_CONVECTION_EXP = 3.0

KINEMATIC_VISCOSITY = 1.82e-6        # m^2/s
THERMAL_CONDUCTIVITY = 0.56          # W/(m K)
GRAVITY = 9.80665                    # m/s^2

# EOS-80 freezing point (Stage 10.5)
EOS_FP_A0 = -0.0575
EOS_FP_A1 = 1.710523e-3
EOS_FP_A2 = 2.154996e-4
EOS_FP_BP = -7.53e-4

ANCHOR_T_W = 2.0
ANCHOR_S_W = 0.0345                 # 34.5 PSU (mass fraction)
ANCHOR_DEPTH = 50.0                 # m
ANCHOR_L = 100.0                    # m (iceberg length)


# ============================================================
# PARAMETERIZED CORE (production formula with tunable constants)
# ============================================================

class NCParams:
    """Natural-convection parameter bundle (production defaults)."""

    def __init__(self, *, beta_t=THERMAL_EXPANSION_COEFF,
                 beta_s=HALINE_CONTRACTION_COEFF, lewis=LEWIS_NUMBER,
                 nu_lam_c=NU_LAMINAR_COEFF, nu_lam_e=NU_LAMINAR_EXP,
                 nu_turb_c=NU_TURBULENT_COEFF, nu_turb_e=NU_TURBULENT_EXP,
                 ra_trans=RAYLEIGH_TRANSITION, ra_max=RAYLEIGH_MAX,
                 mixed_exp=MIXED_CONVECTION_EXP,
                 haline_sign=+1.0, label="production"):
        self.beta_t = beta_t
        self.beta_s = beta_s
        self.lewis = lewis
        self.nu_lam_c = nu_lam_c
        self.nu_lam_e = nu_lam_e
        self.nu_turb_c = nu_turb_c
        self.nu_turb_e = nu_turb_e
        self.ra_trans = ra_trans
        self.ra_max = ra_max
        self.mixed_exp = mixed_exp
        self.haline_sign = haline_sign   # +1 production; -1 = exploratory stabilising haline
        self.label = label


def ocean_freezing_point(salinity_mass: float, depth_m: float) -> float:
    s_psu = salinity_mass * 1000.0
    p_dbar = RHO_WATER * GRAVITY * depth_m / 1.0e4
    return (EOS_FP_A0 + EOS_FP_A1 * math.sqrt(s_psu) - EOS_FP_A2 * s_psu) * s_psu \
           + EOS_FP_BP * p_dbar


def thermal_diffusivity() -> float:
    return THERMAL_CONDUCTIVITY / (RHO_WATER * CP_SEAWATER)


def rayleigh_eff(t_w: float, s_w: float, t_b: float, s_b: float,
                 l_char: float, p: NCParams) -> float:
    """Effective double-diffusive Rayleigh number (production formula)."""
    delta_t = t_w - t_b
    delta_s_psu = (s_w - s_b) * 1000.0
    if delta_t > 0.0 or delta_s_psu > 0.0:
        ra = (GRAVITY * l_char ** 3 / (KINEMATIC_VISCOSITY * thermal_diffusivity()) *
              (p.beta_t * delta_t + p.haline_sign * p.beta_s * delta_s_psu * p.lewis))
    else:
        ra = 0.0
    return ra


def nusselt_from_ra(ra: float, p: NCParams) -> float:
    """Fujii et al. 1973 Nu-Ra correlation with cap (production structure)."""
    if ra <= 0.0:
        return 0.0
    ra_capped = min(ra, p.ra_max)
    if ra_capped < p.ra_trans:
        return p.nu_lam_c * (ra_capped ** p.nu_lam_e)
    return p.nu_turb_c * (ra_capped ** p.nu_turb_e)


def natural_gamma(t_w: float, s_w: float, t_b: float, s_b: float,
                  l_char: float, u_rel: float, p: NCParams) -> tuple[float, float]:
    """Effective (forced+natural) transfer coefficients [m/s]."""
    gam_t_forced = THREE_EQ_KT * u_rel
    gam_s_forced = THREE_EQ_KS * u_rel
    if l_char <= 0.0:
        return gam_t_forced, gam_s_forced
    ra = rayleigh_eff(t_w, s_w, t_b, s_b, l_char, p)
    nu = nusselt_from_ra(ra, p)
    gam_t_nat = nu * THERMAL_CONDUCTIVITY / (l_char * RHO_WATER * CP_SEAWATER)
    gam_s_nat = gam_t_nat * (THREE_EQ_KS / THREE_EQ_KT)
    if gam_t_forced > 0.0 and gam_t_nat > 0.0:
        n = p.mixed_exp
        gam_t = (gam_t_forced ** n + gam_t_nat ** n) ** (1.0 / n)
        gam_s = (gam_s_forced ** n + gam_s_nat ** n) ** (1.0 / n)
    elif gam_t_forced > 0.0:
        gam_t, gam_s = gam_t_forced, gam_s_forced
    else:
        gam_t, gam_s = gam_t_nat, gam_s_nat
    return gam_t, gam_s


def solve_three_equation(t_w: float, s_w: float, depth_m: float, u_rel: float,
                         l_char: float, p: NCParams) -> tuple[float, float, float]:
    """Solve the three-equation + natural convection interface (production structure).

    Returns (m_basal [m/s], t_interface [degC], s_interface [kg/kg]).
    """
    tf_w = ocean_freezing_point(s_w, depth_m)
    if t_w <= tf_w:
        return 0.0, tf_w, s_w
    if s_w <= 0.0:
        s_b = 0.0
        t_b = ocean_freezing_point(0.0, depth_m)
        gam_t, _ = natural_gamma(t_w, s_w, t_b, s_b, l_char, u_rel, p)
        l_heat = RHO_ICE * LATENT_HEAT + RHO_ICE * CP_ICE_3EQ * max(t_b - T_ICE, 0.0)
        m = RHO_WATER * CP_SEAWATER * gam_t * (t_w - t_b) / l_heat if (gam_t > 0.0 and l_heat > 0.0) else 0.0
        return m, t_b, s_b

    gam_t, gam_s = natural_gamma(t_w, s_w, tf_w, s_w, l_char, u_rel, p)
    m_hi = max(RHO_WATER * CP_SEAWATER * gam_t * (t_w - tf_w) / (RHO_ICE * LATENT_HEAT), 1.0e-9)

    def eval_interface(m: float) -> tuple[float, float, float, float]:
        s_b = gam_s * s_w / (gam_s + RHO_ICE_WATER_RATIO * m)
        t_b = ocean_freezing_point(s_b, depth_m)
        g_t, g_s = natural_gamma(t_w, s_w, t_b, s_b, l_char, u_rel, p)
        return t_b, s_b, g_t, g_s

    for _ in range(60):                       # upper-bound expansion
        t_b, s_b, gam_t, gam_s = eval_interface(m_hi)
        l_heat = RHO_ICE * LATENT_HEAT + RHO_ICE * CP_ICE_3EQ * max(t_b - T_ICE, 0.0)
        f = RHO_WATER * CP_SEAWATER * gam_t * (t_w - t_b) - m_hi * l_heat
        if f <= 0.0:
            break
        m_hi *= 2.0

    m_lo = 0.0
    for _ in range(60):                       # bisection
        m_mid = 0.5 * (m_lo + m_hi)
        t_b, s_b, gam_t, gam_s = eval_interface(m_mid)
        l_heat = RHO_ICE * LATENT_HEAT + RHO_ICE * CP_ICE_3EQ * max(t_b - T_ICE, 0.0)
        f = RHO_WATER * CP_SEAWATER * gam_t * (t_w - t_b) - m_mid * l_heat
        if f > 0.0:
            m_lo = m_mid
        else:
            m_hi = m_mid

    m = 0.5 * (m_lo + m_hi)
    t_b, s_b, _, _ = eval_interface(m)
    return m, t_b, s_b


def gamma_parts(t_w: float, s_w: float, t_b: float, s_b: float, l_char: float,
                u_rel: float, p: NCParams) -> dict:
    """Decompose into forced / natural / capped / uncapped components."""
    ra = rayleigh_eff(t_w, s_w, t_b, s_b, l_char, p)
    ra_cap = min(ra, p.ra_max)
    nu = nusselt_from_ra(ra, p)
    g_t_nat = nu * THERMAL_CONDUCTIVITY / (l_char * RHO_WATER * CP_SEAWATER)
    # uncapped counterpart (diagnostic)
    if ra > 0.0:
        if ra < p.ra_trans:
            nu_u = p.nu_lam_c * ra ** p.nu_lam_e
        else:
            nu_u = p.nu_turb_c * ra ** p.nu_turb_e
    else:
        nu_u = 0.0
    g_t_nat_u = nu_u * THERMAL_CONDUCTIVITY / (l_char * RHO_WATER * CP_SEAWATER)
    g_t_for = THREE_EQ_KT * u_rel
    return dict(ra=ra, ra_cap=ra_cap, nu=nu, nu_u=nu_u,
                g_t_nat=g_t_nat, g_t_nat_u=g_t_nat_u, g_t_for=g_t_for)


# ============================================================
# TABLE HELPERS
# ============================================================

def fmt(x: float, w: int = 12, nd: int = 6) -> str:
    if x == 0.0:
        return f"{0.0:>{w}.{nd}g}"
    if abs(x) >= 1e4 or abs(x) < 1e-3:
        return f"{x:>{w}.{3}e}"
    return f"{x:>{w}.{6}f}"


def header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def mday(m: float) -> float:
    return m * 86400.0


# ============================================================
# TABLES
# ============================================================

def table_b_baseline() -> dict:
    """Section B — baseline replica of the Stage 10.11 anchors."""
    p = NCParams()
    gamma_t, _ = natural_gamma(ANCHOR_T_W, ANCHOR_S_W, ocean_freezing_point(ANCHOR_S_W, ANCHOR_DEPTH), ANCHOR_S_W,
                               ANCHOR_L, 0.0, p)
    m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
    g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.0, p)
    return dict(gamma_t_nat=g["g_t_nat"], m=m, t_b=t_b, s_b=s_b, ra=g["ra"],
                ra_cap=g["ra_cap"], nu=g["nu"],
                g_t_nat=g["g_t_nat"], g_t_nat_u=g["g_t_nat_u"])


def table_a_cap_sweep(base: dict) -> None:
    header("TABLE A — Rayleigh-cap sweep  (anchor: T_w=2 C, S_w=34.5 PSU, L=100 m, D=50 m, U=0)")
    print(f"{'ra_max':>10} {'Ra_uncapped':>12} {'capped':>6} {'Nu':>12} {'gamma_T_nat':>12} "
          f"{'gamma_nat/L':>12} {'m [m/s]':>12} {'m [m/day]':>12}")
    caps = [1.0e7, 1.0e8, 5.0e8, 1.0e9, 1.0e10, 1.0e11, 1.0e12, 1.0e13, float("inf")]
    for cap in caps:
        p = NCParams(ra_max=cap, label=f"ra_max={cap:.0e}")
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.0, p)
        capped = "Y" if g["ra"] > cap else "N"
        print(f"{cap:>10.0e} {g['ra']:>12.3e} {capped:>6} {g['nu']:>12.4f} {g['g_t_nat']:>12.3e} "
              f"{g['g_t_nat']*ANCHOR_L:>12.3e} {m:>12.3e} {mday(m):>12.5f}")


def table_c_length_sweep(base: dict) -> None:
    header("TABLE C — Length sweep (L = iceberg length; anchor otherwise; U=0)")
    print(f"{'L [m]':>8} {'Ra_uncapped':>12} {'capped':>6} {'Nu':>12} {'gamma_T_nat':>12} "
          f"{'gamma*L':>12} {'m [m/s]':>12} {'m [m/day]':>12}")
    for L in [10.0, 20.0, 40.0, 50.0, 100.0, 200.0, 400.0]:
        p = NCParams()
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, L, 0.0, p)
        capped = "Y" if g["ra"] > p.ra_max else "N"
        print(f"{L:>8.0f} {g['ra']:>12.3e} {capped:>6} {g['nu']:>12.4f} {g['g_t_nat']:>12.3e} "
              f"{g['g_t_nat']*L:>12.3e} {m:>12.3e} {mday(m):>12.5f}")


def table_d_urel_sweep(base: dict) -> None:
    header("TABLE D — U_rel sweep (anchor T/S/L/D; U varying)")
    print(f"{'U [m/s]':>9} {'gam_for':>12} {'gam_nat':>12} {'gam_eff':>12} {'eff/for-1':>12} "
          f"{'m [m/s]':>12} {'m [m/day]':>12}")
    for U in [0.0, 1.0e-4, 4.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0]:
        p = NCParams()
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, U, ANCHOR_L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, U, p)
        gam_for = THREE_EQ_KT * U
        gam_eff, _ = natural_gamma(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, U, p)
        excess = (gam_eff / gam_for - 1.0) if gam_for > 0.0 else float("nan")
        print(f"{U:>9.4g} {gam_for:>12.3e} {g['g_t_nat']:>12.3e} {gam_eff:>12.3e} {excess:>12.3e} "
              f"{m:>12.3e} {mday(m):>12.5f}")


def table_e_dt_sweep(base: dict) -> None:
    header("TABLE E — Delta-T sweep (S_w=34.5 PSU, L=100 m, D=50 m, U=0)")
    tf_w = ocean_freezing_point(ANCHOR_S_W, ANCHOR_DEPTH)
    print(f"Tf(S=34.5, D=50) = {tf_w:.4f} C")
    print(f"{'T_w [C]':>9} {'dT=T_w-Tf':>11} {'gamma_T_nat':>12} {'m [m/s]':>12} {'m [m/day]':>12} "
          f"{'m/dT [m/s/K]':>13}")
    for T_w in [tf_w + 0.5, tf_w + 1.0, tf_w + 2.0, tf_w + 3.0, tf_w + 4.0]:
        p = NCParams()
        m, t_b, s_b = solve_three_equation(T_w, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
        g = gamma_parts(T_w, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.0, p)
        print(f"{T_w:>9.3f} {T_w-tf_w:>11.3f} {g['g_t_nat']:>12.3e} {m:>12.3e} {mday(m):>12.5f} "
              f"{m/(T_w-tf_w):>13.3e}")


def table_f_salinity_sweep(base: dict) -> None:
    header("TABLE F — Salinity sweep (T_w=2 C, L=100 m, D=50 m, U=0)")
    print(f"{'S_w [PSU]':>10} {'Tf [C]':>9} {'S_B [PSU]':>10} {'gamma_T_nat':>12} "
          f"{'m [m/s]':>12} {'m [m/day]':>12}")
    for S_psu in [30.0, 32.0, 33.0, 34.0, 34.5, 35.0]:
        s_w = S_psu / 1000.0
        p = NCParams()
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, s_w, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
        g = gamma_parts(ANCHOR_T_W, s_w, t_b, s_b, ANCHOR_L, 0.0, p)
        print(f"{S_psu:>10.1f} {ocean_freezing_point(s_w, ANCHOR_DEPTH):>9.4f} {s_b*1000.0:>10.3f} "
              f"{g['g_t_nat']:>12.3e} {m:>12.3e} {mday(m):>12.5f}")


def table_g_haline_diagnostic(base: dict) -> None:
    header("TABLE G — Haline / Lewis-number diagnostic (anchor; U=0; last two rows are "
           "EXPLICITLY NON-PRODUCTION exploratory variants)")
    print(f"{'variant':>46} {'Ra_uncapped':>12} {'Nu':>12} {'gamma_T_nat':>12} {'m [m/s]':>12} "
          f"{'m [m/day]':>12}")
    variants = [
        NCParams(label="production: +beta_S*dS*Le, Le=100"),
        NCParams(lewis=0.0, label="thermal only: Le=0 (haline term dropped)"),
        NCParams(lewis=1.0, label="haline no-Le: +beta_S*dS, Le=1"),
        NCParams(haline_sign=-1.0, label="NON-PROD haline stabilising: -beta_S*dS*Le"),
    ]
    for p in variants:
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.0, p)
        print(f"{p.label:>46} {g['ra']:>12.3e} {g['nu']:>12.4f} {g['g_t_nat']:>12.3e} "
              f"{m:>12.3e} {mday(m):>12.5f}")


def table_h_beta_sweep(base: dict) -> None:
    header("TABLE H — beta_T / beta_S sensitivity (+-1 order; anchor; U=0)")
    print(f"{'beta_T':>10} {'beta_S':>10} {'Ra_uncapped':>12} {'capped':>6} {'gamma_T_nat':>12} "
          f"{'m [m/s]':>12}")
    for b_t in [3.0e-6, 3.0e-5, 3.0e-4]:
        for b_s in [7.8e-5, 7.8e-4, 7.8e-3]:
            p = NCParams(beta_t=b_t, beta_s=b_s)
            m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, ANCHOR_L, p)
            g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.0, p)
            capped = "Y" if g["ra"] > p.ra_max else "N"
            print(f"{b_t:>10.1e} {b_s:>10.1e} {g['ra']:>12.3e} {capped:>6} {g['g_t_nat']:>12.3e} "
                  f"{m:>12.3e}")


def table_i_churchill_sweep(base: dict) -> None:
    header("TABLE I — Churchill mixed-convection exponent n (anchor; U_rel=0.1 m/s)")
    print(f"{'n':>4} {'gam_for':>12} {'gam_nat':>12} {'gam_eff':>12} {'eff/for-1':>12} "
          f"{'m [m/s]':>12} {'m [m/day]':>12}")
    for n in [1.0, 2.0, 3.0, 4.0, 5.0]:
        p = NCParams(mixed_exp=n)
        m, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.1, ANCHOR_L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.1, p)
        gam_eff, _ = natural_gamma(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, ANCHOR_L, 0.1, p)
        gam_for = THREE_EQ_KT * 0.1
        excess = gam_eff / gam_for - 1.0
        print(f"{n:>4.0f} {gam_for:>12.3e} {g['g_t_nat']:>12.3e} {gam_eff:>12.3e} {excess:>12.3e} "
              f"{m:>12.3e} {mday(m):>12.5f}")


def table_j_crossover(base: dict) -> None:
    header("TABLE J — Natural/forced crossover velocity U* = gamma_T_nat / K_T  (anchor T/S/D)")
    print(f"{'L [m]':>8} {'gamma_T_nat':>12} {'U* [m/s]':>12} {'note':>24}")
    for L in [10.0, 20.0, 40.0, 100.0, 200.0, 400.0]:
        p = NCParams()
        _, t_b, s_b = solve_three_equation(ANCHOR_T_W, ANCHOR_S_W, ANCHOR_DEPTH, 0.0, L, p)
        g = gamma_parts(ANCHOR_T_W, ANCHOR_S_W, t_b, s_b, L, 0.0, p)
        u_star = g["g_t_nat"] / THREE_EQ_KT
        print(f"{L:>8.0f} {g['g_t_nat']:>12.3e} {u_star:>12.3e} {'nat > forced below U*':>24}")


def summary(base: dict) -> None:
    header("SUMMARY — key audit numbers (production baseline)")
    g = base
    dT = ANCHOR_T_W - g["t_b"]
    dS = (ANCHOR_S_W - g["s_b"]) * 1000.0
    th = THERMAL_EXPANSION_COEFF * dT
    hal = HALINE_CONTRACTION_COEFF * dS * LEWIS_NUMBER
    print(f"anchor melt m(U=0)           = {g['m']:.4e} m/s = {mday(g['m']):.6f} m/day")
    print(f"interface T_B / S_B          = {g['t_b']:.4f} C / {g['s_b']*1000:.3f} PSU")
    print(f"delta T / delta S            = {dT:.4f} K / {dS:.4f} PSU")
    print(f"beta_T*dT                    = {th:.4e}   (thermal buoyancy)")
    print(f"beta_S*dS*Le                 = {hal:.4e}   (haline buoyancy, Le=100)")
    print(f"haline/thermal ratio         = {hal/th:.2e}")
    print(f"Ra uncapped (L=100)          = {g['ra']:.4e}  vs cap {RAYLEIGH_MAX:.0e}")
    print(f"cap multiplier on gamma      = {g['g_t_nat_u']/g['g_t_nat']:.1f}x  "
          f"(uncapped gamma_T_nat = {g['g_t_nat_u']:.4e})")
    print(f"Fujii transition discont.    = 0.27*(1e7)^.25 vs 0.15*(1e7)^(1/3): "
          f"{0.27*1e7**0.25:.3f} vs {0.15*1e7**(1/3):.3f} (ratio {0.15*1e7**(1/3)/(0.27*1e7**0.25):.3f})")
    print(f"L for cap (haline-only)      = {(RAYLEIGH_MAX/(GRAVITY/(KINEMATIC_VISCOSITY*thermal_diffusivity())*hal))**(1/3):.4f} m")
    print(f"L for cap (thermal-only)     = {(RAYLEIGH_MAX/(GRAVITY/(KINEMATIC_VISCOSITY*thermal_diffusivity())*th))**(1/3):.4f} m")


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=str, default=None,
                    help="optional directory for CSV dumps (default: stdout only)")
    args = ap.parse_args()

    base = table_b_baseline()
    print("=" * 100)
    print("Stage 10.11.3 — natural-convection sensitivity analysis (production replica)")
    print("=" * 100)
    print(f"Baseline sanity (expected production anchors):")
    print(f"  gamma_T_nat = {base['gamma_t_nat']:.6e}   (production test anchor: 4.429877e-7)")
    print(f"  m(U=0)      = {base['m']:.4e} m/s  (production test anchor: 1.638e-8)")
    print(f"  T_B         = {base['t_b']:.4f} C   S_B = {base['s_b']*1000:.3f} PSU")

    table_a_cap_sweep(base)
    table_c_length_sweep(base)
    table_d_urel_sweep(base)
    table_e_dt_sweep(base)
    table_f_salinity_sweep(base)
    table_g_haline_diagnostic(base)
    table_h_beta_sweep(base)
    table_i_churchill_sweep(base)
    table_j_crossover(base)
    summary(base)

    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "baseline_stage10_11_3.txt").write_text(
            f"gamma_T_nat={base['gamma_t_nat']:.10e}\n"
            f"m_basal={base['m']:.10e}\n"
            f"T_B={base['t_b']:.10f}\nS_B={base['s_b']:.10f}\n"
            f"Ra_uncapped={base['ra']:.10e}\nRa_capped={base['ra_cap']:.10e}\nNu={base['nu']:.10f}\n")
        print(f"\n[CSV/baseline written to {out}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())