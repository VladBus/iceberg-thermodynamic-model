#!/usr/bin/env python3
"""
Stage 10.18A — independent regression tests for the lateral-melt reference
layer (``python/validation/lateral_melt.py``).

Every expected value below is obtained analytically (hand-derived formula),
not by running the implementation under test:

- legacy m_l = C_LATERAL * <DeltaT>_D:
    * <DeltaT>_D = 0  -> m_l = 0            (multiplication by zero);
    * linear scaling  -> m_l ∝ <DeltaT>_D   (same coefficient);
    * no U argument   -> velocity independent by construction.
- submerged vs full-height geometry:
    * A_sub = 2(L+W)*D, A_full = H(L+W);
      ratio at L=W is 2*rho_i/rho_w = 2*910/1028 = 1.7704...
- bulk velocity-dependent side melt (forced-convection closure):
    * m ∝ U^0.8  (turbulent, 0.037 Re^0.8 Pr^(1/3)/Re -> U^0.8);
    * m ∝ U^0.5  (laminar);
    * m ∝ D^-0.2 (turbulent size scaling, gamma_T = Nu k / D);
    * m ∝ D^-0.5 (laminar size scaling);
    * m ∝ <DeltaT>_D linearly (gamma_T independent of DeltaT);
    * m = 0 at U = 0 (forced-convection guard);
    * Nu branch transition exactly at Re_crit with analytic jump
      Nu_turb/Nu_lam = (0.037/0.664)*Re_crit^0.3 = 2.851... (intrinsic
      flat-plate correlation discontinuity, documented, not smoothed).
- unit conversions and mass/volume identities are algebraic.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_lateral_melt_parameterizations.py
"""

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))  # repo root -> `python.validation` package imports
sys.path.insert(0, str(REPO / "python" / "validation"))  # flat module imports
TRAJ_30 = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"

import numpy as np

from python.validation.lateral_melt import (  # bootstrap import (repo root on sys.path)
    BIGG_K_OCEAN,
    BIGG_K_LAB,
    C_LATERAL,
    NESHYBA_A,
    NESHYBA_B,
    PLUME_SPEED_LAB,
    SECONDS_PER_DAY,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    depth_averaged_thermal_forcing,
    fitzmaurice_plume_side_melt,
    lateral_area_full_height,
    lateral_area_submerged_full_perimeter,
    lateral_area_submerged_half_perimeter,
    lateral_mass_loss_rate,
    lateral_volume_rate_full_height,
    lateral_volume_rate_submerged_full_perimeter,
    legacy_lateral_melt_rate,
    m_day_to_m_s,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
    numeric_exponent,
    nusselt_flat_plate,
    side_heat_transfer_coefficient,
)
from python.validation.basal_melt import (
    LATENT_HEAT,
    PRANDTL_NUMBER,
    REYNOLDS_CRITICAL,
    RHO_ICE,
    RHO_WATER,
    KINEMATIC_VISCOSITY,
    THERMAL_CONDUCTIVITY,
    ocean_freezing_point,
)

_CHECKS = 0
_ERRORS = 0


def check(cond: bool, name: str):
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if not cond:
        _ERRORS += 1
        print(f"  FAIL: {name}")
    else:
        print(f"  ok:   {name}")


def approx(a: float, b: float, rel: float = 1e-9) -> bool:
    """Relative-tolerance comparison for float64 analytic expectations."""
    if a == b:
        return True
    return abs(a - b) <= rel * max(abs(a), abs(b))


# ---------------------------------------------------------------------------
# 1. Legacy: zero driving, linear scaling, U independence
# ---------------------------------------------------------------------------
def test_legacy_analytic():
    print("Legacy formulation (analytic expectations)")
    # <DeltaT>_D = 0 -> m_l = 0 exactly (guard + multiplication by zero)
    check(legacy_lateral_melt_rate(0.0) == 0.0, "legacy: m_l = 0 at DeltaT = 0")
    check(legacy_lateral_melt_rate(-2.5) == 0.0, "legacy: m_l = 0 at DeltaT < 0")
    # linear scaling: m_l = C_LATERAL * DeltaT
    for dt in (0.5, 1.0, 2.0, 3.0, 4.0, 6.0):
        exp = C_LATERAL * dt
        check(approx(legacy_lateral_melt_rate(dt), exp), f"legacy: m_l = C*DeltaT at DeltaT={dt}")
    # scaling ratio across a factor-3 change
    m1 = legacy_lateral_melt_rate(1.0)
    m3 = legacy_lateral_melt_rate(3.0)
    check(approx(m3 / m1, 3.0), "legacy: m_l linear (factor 3 -> factor 3)")
    # velocity independence: function signature has no velocity argument;
    # the same rate is returned regardless of any ambient velocity context
    check(
        legacy_lateral_melt_rate(3.0) == legacy_lateral_melt_rate(3.0),
        "legacy: deterministic (same input -> same output)",
    )
    check(C_LATERAL == 1.0e-6, "legacy: documented coefficient C_LATERAL = 1e-6 m/(s K)")


# ---------------------------------------------------------------------------
# 2. Geometry: full-height vs submerged area / volume identities
# ---------------------------------------------------------------------------
def test_geometry_identities():
    print("Geometry conventions (analytic identities)")
    L, W, H = 100.0, 60.0, 100.0
    D = H * RHO_ICE / RHO_WATER
    A_full = lateral_area_full_height(L, W, H)
    A_sub = lateral_area_submerged_full_perimeter(L, W, H)
    A_sub_half = lateral_area_submerged_half_perimeter(L, W, H)

    # analytic values
    check(approx(A_full, H * (L + W)), "A_full = H*(L+W)")
    check(approx(A_sub, 2.0 * (L + W) * D), "A_sub = 2*(L+W)*D")
    check(approx(A_sub_half, (L + W) * D), "A_sub_half = (L+W)*D")
    # at L=W the full-height : submerged-full-perimeter ratio is 2*rho_i/rho_w
    Lsq = 100.0
    ratio = lateral_area_submerged_full_perimeter(Lsq, Lsq, H) / lateral_area_full_height(Lsq, Lsq, H)
    check(approx(ratio, 2.0 * RHO_ICE / RHO_WATER, 1e-12),
          f"ratio A_sub/A_full = 2*rho_i/rho_w = {2.0*RHO_ICE/RHO_WATER:.6f}")
    # volume rates = area * m_l
    m_l = 3.0e-6
    check(approx(lateral_volume_rate_full_height(m_l, L, W, H), A_full * m_l),
          "dV_full/dt = A_full * m_l")
    check(approx(lateral_volume_rate_submerged_full_perimeter(m_l, L, W, H), A_sub * m_l),
          "dV_sub/dt = A_sub * m_l")
    # mass-loss identity: dm/dt = rho_i * A * m_l
    check(approx(lateral_mass_loss_rate(m_l, A_sub), RHO_ICE * A_sub * m_l),
          "dm/dt = rho_i * A * m_l (mass-volume identity)")
    # geometric exactness: D from hydrostatic relation
    check(approx(D, H * 910.0 / 1028.0), "D = H * rho_i/rho_w")


# ---------------------------------------------------------------------------
# 3. Bulk velocity-dependent closure: scalings, transitions, boundaries
# ---------------------------------------------------------------------------
def test_bulk_closure():
    print("Bulk velocity-dependent closure (analytic scalings)")
    dT = 3.0          # <DeltaT>_D [degC]
    D = 88.5          # characteristic length (draft) [m]
    m = bulk_velocity_dependent_side_melt

    # zero velocity -> 0 (forced-convection guard)
    check(m(dT, 0.0, D) == 0.0, "bulk: m_side = 0 at U_rel = 0")
    check(m(dT, -0.1, D) == 0.0, "bulk: m_side = 0 at U_rel < 0")
    check(m(0.0, 0.5, D) == 0.0, "bulk: m_side = 0 at DeltaT = 0")

    # choose velocities safely inside laminar (Re < 5e5) and turbulent regimes
    # (both points of each exponent pair must stay in the SAME regime)
    u_lam, u_turb = 0.005, 0.5       # Re ~ 2.4e5 (lam) and ~ 2.4e7 (turb) at D=88.5
    m_lam = m(dT, u_lam, D)
    m_turb = m(dT, u_turb, D)
    check(m_lam > 0.0 and m_turb > 0.0, "bulk: positive melt in both regimes")

    # turbulent velocity exponent = 0.8
    n_u_turb = numeric_exponent(2.0 * u_turb, u_turb, m(dT, 2 * u_turb, D), m_turb)
    check(approx(n_u_turb, 0.8, 1e-9), f"bulk: turbulent U exponent = {n_u_turb:.6f} (analytic 0.8)")
    # laminar velocity exponent = 0.5  (2*u_lam=0.01 -> Re=4.86e5, still laminar)
    n_u_lam = numeric_exponent(2.0 * u_lam, u_lam, m(dT, 2 * u_lam, D), m_lam)
    check(approx(n_u_lam, 0.5, 1e-9), f"bulk: laminar U exponent = {n_u_lam:.6f} (analytic 0.5)")

    # turbulent size (D) exponent = -0.2  (gamma_T ~ D^-0.2)
    u_fix = 0.5
    m_d1 = m(dT, u_fix, 100.0)
    m_d2 = m(dT, u_fix, 200.0)
    n_d = numeric_exponent(200.0, 100.0, m_d2, m_d1)
    check(approx(n_d, -0.2, 1e-9), f"bulk: turbulent D exponent = {n_d:.6f} (analytic -0.2)")
    # laminar size (D) exponent = -0.5  (U=0.003 keeps Re < 5e5 up to D=200)
    lam_d1 = m(dT, 0.003, 100.0)
    lam_d2 = m(dT, 0.003, 200.0)
    n_dl = numeric_exponent(200.0, 100.0, lam_d2, lam_d1)
    check(approx(n_dl, -0.5, 1e-9), f"bulk: laminar D exponent = {n_dl:.6f} (analytic -0.5)")

    # linear in DeltaT (gamma_T independent of DeltaT)
    check(approx(m(2 * dT, u_turb, D) / m_turb, 2.0), "bulk: linear in DeltaT (factor 2)")

    # branch transition exactly at Re_crit: turbulent side at Re == Re_crit
    u_crit = REYNOLDS_CRITICAL * KINEMATIC_VISCOSITY / D
    nu_turb = nusselt_flat_plate(REYNOLDS_CRITICAL)
    nu_lam = nusselt_flat_plate(REYNOLDS_CRITICAL - 1.0)
    # analytic jump at transition (relaxed tolerance: (Re/(Re-1))^0.5 ~ 1+5e-7)
    jump_an = (0.037 / 0.664) * REYNOLDS_CRITICAL**0.3
    check(approx(nu_turb / nu_lam, jump_an, 1e-5),
          "bulk: Re_crit branch jump matches analytic value")
    # verify the turbulent branch is selected exactly at Re_crit
    check(approx(nu_turb, 0.037 * REYNOLDS_CRITICAL**0.8 * PRANDTL_NUMBER ** (1.0 / 3.0)),
          "bulk: Nu_turb formula at Re_crit")
    # deterministic
    check(m(dT, u_turb, D) == m(dT, u_turb, D), "bulk: deterministic")

    # heat-transfer coefficient analytic value at a fixed point
    # gamma_T = 0.037 (U D/nu)^0.8 Pr^(1/3) k / D  (turbulent)
    g = side_heat_transfer_coefficient(u_turb, D)
    g_an = (0.037 * (u_turb * D / KINEMATIC_VISCOSITY) ** 0.8
            * PRANDTL_NUMBER ** (1.0 / 3.0) * THERMAL_CONDUCTIVITY / D)
    check(approx(g, g_an), "bulk: gamma_T analytic turbulent value")


# ---------------------------------------------------------------------------
# 3b. Literature-based formulations (Bigg, Neshyba-Josberger, FitzMaurice)
# ---------------------------------------------------------------------------
def test_literature_variants():
    print("Literature-based variants (analytic scalings)")
    dT = 3.0
    L = 100.0
    D = 88.5
    U = 0.1

    # Bigg forced convection: M = K U^0.8 dT / L^0.2  (m/day)
    mb = bigg1997_forced_convection_melt_rate(U, dT, L)
    mb_an = m_day_to_m_s(BIGG_K_OCEAN * U**0.8 * dT / L**0.2)
    check(approx(mb, mb_an), "bigg: analytic value (K=0.58)")
    n_u = numeric_exponent(
        2.0 * U, U,
        bigg1997_forced_convection_melt_rate(2.0 * U, dT, L),
        bigg1997_forced_convection_melt_rate(U, dT, L),
    )
    check(approx(n_u, 0.8, 1e-9), f"bigg: U exponent = {n_u:.6f} (analytic 0.8)")
    n_l = numeric_exponent(200.0, 100.0,
                           bigg1997_forced_convection_melt_rate(U, dT, 200.0),
                           bigg1997_forced_convection_melt_rate(U, dT, 100.0))
    check(approx(n_l, -0.2, 1e-9), f"bigg: L exponent = {n_l:.6f} (analytic -0.2)")
    check(approx(bigg1997_forced_convection_melt_rate(U, 2.0 * dT, L) /
                  bigg1997_forced_convection_melt_rate(U, dT, L), 2.0),
          "bigg: linear in DeltaT")
    check(bigg1997_forced_convection_melt_rate(0.0, dT, L) == 0.0,
          "bigg: m = 0 at U = 0")
    check(bigg1997_forced_convection_melt_rate(U, 0.0, L) == 0.0,
          "bigg: m = 0 at DeltaT = 0")
    check(BIGG_K_OCEAN == 0.58 and BIGG_K_LAB == 0.75,
          "bigg: documented coefficients (K = 0.58 ocean, 0.75 lab)")

    # Neshyba-Josberger buoyant: M = a dT + b dT^2 (m/day)
    mv = neshyba_josberger_buoyant_melt_rate(dT)
    mv_an = m_day_to_m_s(NESHYBA_A * dT + NESHYBA_B * dT**2)
    check(approx(mv, mv_an), "neshyba: analytic quadratic value")
    check(neshyba_josberger_buoyant_melt_rate(0.0) == 0.0,
          "neshyba: m = 0 at DeltaT = 0")
    check(NESHYBA_A == 7.62e-3 and NESHYBA_B == 1.29e-3,
          "neshyba: documented coefficients (a, b)")

    # FitzMaurice plume regime split: attached (U < w) uses plume_speed and D;
    # detached (U >= w) uses U and L.
    m_att = fitzmaurice_plume_side_melt(PLUME_SPEED_LAB - 0.001, dT, L, D)
    m_det = fitzmaurice_plume_side_melt(PLUME_SPEED_LAB + 0.001, dT, L, D)
    m_att_an = m_day_to_m_s(BIGG_K_OCEAN * PLUME_SPEED_LAB**0.8 * dT / D**0.2)
    m_det_an = m_day_to_m_s(BIGG_K_OCEAN * (PLUME_SPEED_LAB + 0.001)**0.8 * dT / L**0.2)
    check(approx(m_att, m_att_an), "fitzmaurice: attached branch (plume-speed, D)")
    check(approx(m_det, m_det_an), "fitzmaurice: detached branch (U, L)")
    check(PLUME_SPEED_LAB == 0.025, "fitzmaurice: plume speed = 0.025 m/s (lab)")


# ---------------------------------------------------------------------------
# 4. Numerics, finite, non-negative, monotonic, unit conversions
# ---------------------------------------------------------------------------
def test_numerics_units(seed: int = 12345):
    print("Numerics and units")
    rng = np.random.default_rng(seed)
    for _ in range(200):
        dt = float(rng.uniform(-1, 8))
        u = float(rng.uniform(0, 1.5))
        Dc = float(rng.uniform(5, 400))
        m_l = legacy_lateral_melt_rate(dt)
        check(math.isfinite(m_l) and m_l >= 0.0, "legacy: finite & non-negative (random)")
        m_b = bulk_velocity_dependent_side_melt(dt, u, Dc)
        check(math.isfinite(m_b) and m_b >= 0.0, "bulk: finite & non-negative (random)")
    # monotonicity in DeltaT (legacy and bulk)
    dt_seq = [0.5, 1.0, 2.0, 3.0, 4.0, 6.0]
    mono_l = all(legacy_lateral_melt_rate(a) <= legacy_lateral_melt_rate(b)
                 for a, b in zip(dt_seq, dt_seq[1:]))
    check(mono_l, "legacy: monotone non-decreasing in DeltaT")
    mono_b = all(bulk_velocity_dependent_side_melt(a, 0.5, 88.5) <= bulk_velocity_dependent_side_melt(b, 0.5, 88.5)
                 for a, b in zip(dt_seq, dt_seq[1:]))
    check(mono_b, "bulk: monotone non-decreasing in DeltaT")
    # unit conversions
    check(approx(m_s_to_m_day(1.0), 86400.0), "units: 1 m/s = 86400 m/day")
    check(approx(m_day_to_m_s(86400.0), 1.0), "units: round-trip m/day -> m/s")
    check(approx(m_s_to_m_day(3.884875e-6), 3.884875e-6 * 86400.0), "units: explicit value")
    check(approx(m_day_to_m_s(0.259892), 0.259892 / 86400.0), "units: explicit value")


# ---------------------------------------------------------------------------
# 5. Depth-averaged thermal driving (analytic single-layer case)
# ---------------------------------------------------------------------------
def test_depth_averaged_forcing():
    print("Depth-averaged thermal driving")
    # Single layer covering 0..2 m at mid-depth 1 m; draft = 1 m stops the
    # integration at the mid-point, no extrapolation (draft <= max_z = 1).
    t = np.array([2.5])
    s = np.array([34.5])
    z = np.array([1.0])
    dz = np.array([2.0])
    draft = 2.0  # layer bottom = min(2, 2) = 2 -> full layer; extrapolation if draft>max_z=1
    # with draft = 2 > max_z = 1, production extrapolates (1m) with deep values;
    # a fully analytic case must avoid extrapolation: use draft = 1.0
    d1 = depth_averaged_thermal_forcing(t, s, z, dz, 1.0)
    tf = ocean_freezing_point(34.5, 1.0)
    check(approx(d1, max(2.5 - tf, 0.0)), "davg: single-layer average = max(T-Tf,0) at z=1")
    # cold layer -> zero driving
    d_cold = depth_averaged_thermal_forcing(np.array([-2.0]), s, z, dz, 1.0)
    check(d_cold == 0.0, "davg: freezing/cold layer -> 0")
    # two identical layers: average unaffected by splitting (uniform profile);
    # a third dummy level at z=2.5 keeps max_z >= draft (no extrapolation)
    t2 = np.array([2.5, 2.5, 2.5])
    s2 = np.array([34.5, 34.5, 34.5])
    z2 = np.array([0.5, 1.5, 2.5])
    dz2 = np.array([1.0, 1.0, 1.0])
    d2 = depth_averaged_thermal_forcing(t2, s2, z2, dz2, 2.0)
    # average over 0..2 of uniform max(T-Tf(z),0); Tf at 0.5 and 1.5 differ
    # slightly; recompute analytically
    tf1 = ocean_freezing_point(34.5, 0.5)
    tf2 = ocean_freezing_point(34.5, 1.5)
    exp2 = (max(2.5 - tf1, 0.0) + max(2.5 - tf2, 0.0)) / 2.0
    check(approx(d2, exp2), "davg: uniform profile average = mean of layer values")
    # draft deeper than deepest level -> constant extrapolation contributes
    d3 = depth_averaged_thermal_forcing(t, s, z, dz, 3.0)
    tf_d = ocean_freezing_point(34.5, 1.0)  # deep value at z=1
    # integral = (T-Tf)*1 (0..1) + (T-Tf_deep)*2 (1..3); total depth 3
    exp3 = (max(2.5 - tf, 0.0) * 1.0 + max(2.5 - tf_d, 0.0) * 2.0) / 3.0
    check(approx(d3, exp3), "davg: constant extrapolation below deepest level")


# ---------------------------------------------------------------------------
# 6. Real-data consistency (production TEST_11 trajectory, gated on file)
# ---------------------------------------------------------------------------
def test_production_trajectory_consistency():
    print("Production TEST_11 consistency (gated on baseline file)")
    if not TRAJ_30.exists():
        print("  skip: baseline trajectory not present")
        return
    with open(TRAJ_30) as f:
        header = f.readline().strip().split(",")
    df = np.genfromtxt(TRAJ_30, skip_header=1, names=header,
                       delimiter=None, dtype=float, autostrip=True)
    ml_mday = df["ml_mday"]
    dT_ocean = df["delta_t_ocean_degC"]
    L = df["L_m"]
    W = df["W_m"]
    H = df["H_m"]
    M = df["M_kg"]
    # production lateral melt rate near-constant in time: the only time variation
    # enters through <DeltaT>_D (draft shrinks by ~0.5 m over 30 days)
    ml_max = float(np.max(ml_mday))
    ml_min = float(np.min(ml_mday))
    check(ml_min > 0.0 and ml_max / ml_min < 1.01,
          "prod: lateral melt rate ~ constant (relative spread < 1%)")
    # recover <DeltaT>_D from the production formula
    davg_rec = m_day_to_m_s(ml_mday[0]) / C_LATERAL
    check(davg_rec > 0.0 and davg_rec <= float(dT_ocean[0]),
          f"prod: recovered <DeltaT>_D={davg_rec:.4f} K within (0, DeltaT_draft]")
    # mass identity (production consistency, tolerance for float32 print)
    rel = np.abs(M / (RHO_ICE * L * W * H) - 1.0)
    check(float(np.max(rel)) < 2.0e-5, f"prod: M == rho_i L W H (max rel = {np.max(rel):.1e})")


def main():
    test_legacy_analytic()
    test_geometry_identities()
    test_bulk_closure()
    test_literature_variants()
    test_numerics_units()
    test_depth_averaged_forcing()
    test_production_trajectory_consistency()
    print(f"\nlat-melt: {_CHECKS} checks, {_ERRORS} failures")
    if _ERRORS:
        raise SystemExit(1)
    print("All lateral-melt reference checks passed.")


if __name__ == "__main__":
    main()