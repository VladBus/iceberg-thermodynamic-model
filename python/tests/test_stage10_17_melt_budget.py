#!/usr/bin/env python3
"""
Stage 10.17 — regression tests for the iceberg melt and thermodynamic budget audit.

Independent analytical checks against:
  - the extended 30-day TEST_11 trajectory
    (data/output/diagnostics/stage9.3/test11_trajectory.csv, 24 columns);
  - the 90-day diagnostic run (data/output/stage10.17/test11_90day_...csv);
  - the controlled-experiment tables written by
    test/iceberg_test_10p17_melt_budget.f90.

Analytical expectations (independent float64 implementations):
  bulk basal melt:        m = Nu*k*delta_T/(L*rho_i*L_f),
                          Nu = 0.037*Re^0.8*Pr^(1/3)  (Re >= 5e5, turbulent)
                          Nu = 0.664*Re^0.5*Pr^(1/3)  (Re <  5e5, laminar)
  lateral (legacy):       m_l = C_LATERAL * <dT>_D,  C_LATERAL = 1e-6 m/(s K)
  surface:                m_s = q_surface/(rho_i*L_f) at T_surface = T_melt
  mass consistency:       M == rho_i*L*W*H
  budget closure:         sum(components) == dM_observed

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_17_melt_budget.py
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "output" / "stage10.17"
TRAJ_30 = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
TRAJ_90 = OUT / "test11_90day_stage10.17_trajectory.csv"

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


def skip(label: str, reason: str) -> None:
    global _CHECKS
    _CHECKS += 1
    print(f"SKIP {label} ({reason})")


# --- model constants (mirror iceberg_types.f90) ---
RHO_ICE = 910.0
RHO_WATER = 1028.0
LATENT_HEAT = 334000.0
C_LATERAL = 1.0e-6
K_ICE = 2.2
CP_ICE = 2100.0
H_EFF = 0.5
T_MELT = 0.0
PRANDTL = 13.8
NU = 1.82e-6
K_THERMAL = 0.56
RE_CRIT = 5.0e5
DT_S = 3600.0
S_PER_D = 86400.0

# EOS-80 freezing point (independent float64 implementation)
A0, A1, A2, BP = -0.0575, 1.710523e-3, 2.154996e-4, -7.53e-4


def tf_eos(s_psu: float, depth_m: float) -> float:
    p_dbar = RHO_WATER * 9.80665 * depth_m / 1.0e4
    return (A0 + A1 * math.sqrt(s_psu) - A2 * s_psu) * s_psu + BP * p_dbar


def bulk_basal_melt(u_rel: float, l_char: float, delta_t: float,
                    s_psu: float = 34.8, depth_m: float = 100.0 * 910.0 / 1028.0) -> float:
    """Independent float64 bulk-formula basal melt rate [m/s]."""
    re = u_rel * l_char / NU
    if re >= RE_CRIT:
        nu_n = 0.037 * re**0.8 * PRANDTL ** (1.0 / 3.0)
    else:
        nu_n = 0.664 * re**0.5 * PRANDTL ** (1.0 / 3.0)
    gamma_t = nu_n * K_THERMAL / l_char
    return gamma_t * delta_t / (RHO_ICE * LATENT_HEAT)


def load_traj(path: Path) -> pd.DataFrame:
    with open(path) as f:
        header = f.readline().strip().split(",")
    return pd.read_csv(path, sep=r"\s+", skiprows=1, names=header)


def component_losses(df: pd.DataFrame) -> dict:
    L, W, H = df["L_m"].values, df["W_m"].values, df["H_m"].values
    mb = (df["mb_mday"] / S_PER_D).values
    ml = (df["ml_mday"] / S_PER_D).values
    ms = (df["ms_mday"] / S_PER_D).values
    mv = df["m_vapor_kgm2s"].values if "m_vapor_kgm2s" in df.columns else np.zeros(len(df))
    return {
        "basal": RHO_ICE * L * W * DT_S * mb,
        "lateral": RHO_ICE * (H * W + L * H) * DT_S * ml,
        "surface": RHO_ICE * L * W * DT_S * ms,
        "vapor": -L * W * DT_S * mv,
    }


def main() -> None:
    global _CHECKS, _ERRORS
    print("=" * 60)
    print("  STAGE 10.17 MELT BUDGET REGRESSION TESTS")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. 30-day real-forcing trajectory: internal consistency
    # ------------------------------------------------------------------
    if not TRAJ_30.exists():
        skip("T1..T10", f"missing {TRAJ_30}")
    else:
        df = load_traj(TRAJ_30)
        ok(len(df) == 720, "T1. trajectory has 720 rows", f"rows={len(df)}")
        m = df["M_kg"].values
        v_geom = df["L_m"].values * df["W_m"].values * df["H_m"].values
        m_geom = RHO_ICE * v_geom
        rel = np.abs(m - m_geom) / m
        ok(rel.max() < 2.0e-5, "T2. reported mass == rho_ice*L*W*H (float32 print precision)",
           f"max rel diff = {rel.max():.3e}")
        ok((np.diff(m) <= 0).all(), "T3. mass monotonically non-increasing")
        ok((df[["L_m", "W_m", "H_m"]].values > 0).all(), "T4. geometry strictly positive")
        ok((df[["mb_mday", "ml_mday", "ms_mday"]].values >= 0).all(), "T5. melt rates non-negative")
        ok((df["t_ice_degC"] >= -100.0).all() and (df["t_ice_degC"] <= 0.0).all(),
           "T6. internal temperature bounded [T_ICE_MIN, T_ICE_MAX]")
        # budget closure: component sum vs observed dM (reconstruction sampling ~0.1%)
        comp = component_losses(df)
        total_comp = sum(comp.values()).sum()
        d_m_obs = m[0] - m[-1]
        ok(abs(total_comp - d_m_obs) / d_m_obs < 1.0e-2,
           "T7. component budget closes vs observed dM", f"residual rel = {abs(total_comp - d_m_obs) / d_m_obs:.3e}")
        frac = {k: v.sum() / total_comp for k, v in comp.items()}
        ok(frac["lateral"] > 0.9, "T8. lateral melt dominates (>90%)", f"lateral fraction = {frac['lateral']:.4f}")
        ok(frac["basal"] < 0.1, "T9. basal melt minor (<10%)", f"basal fraction = {frac['basal']:.4f}")
        # energy closure at melting surface steps (steady melting: previous step melts too;
        # crossing steps legitimately use part of the flux for warming to T_melt)
        melting = df[df["ms_mday"] > 0.0]
        if len(melting) > 0:
            lhs = (melting["ms_mday"] / S_PER_D * RHO_ICE * LATENT_HEAT).values
            rhs = melting["q_surface_Wm2"].values
            ok((lhs <= rhs + 0.1).all(), "T10a. melt flux never exceeds available surface flux")
            # steady melting: the previous step also melted (excludes T_melt crossing steps)
            idx = np.where(melting.index > 0, melting.index - 1, 0)
            is_steady = df["ms_mday"].values[idx] > 0.0
            if is_steady.sum() > 0:
                lhs_s = lhs[is_steady]
                rhs_s = rhs[is_steady]
                ok(np.abs(lhs_s - rhs_s).max() / max(np.abs(rhs_s).max(), 1.0) < 1.0e-3,
                   "T10b. steady-state surface energy closure m_s*rho*Lf == q_surface",
                   f"n_steady={int(is_steady.sum())}")
            else:
                skip("T10b", "no steady melt steps")
        else:
            skip("T10", "no surface-melt steps")

    # ------------------------------------------------------------------
    # 2. Controlled experiments: bulk basal melt against independent float64
    # ------------------------------------------------------------------
    vel_csv = OUT / "velocity_sensitivity.csv"
    if not vel_csv.exists():
        skip("T11..T14", "velocity_sensitivity.csv missing (run Fortran test)")
    else:
        vel = pd.read_csv(vel_csv)
        # reference: U=0.1, dT=2, L=100 (case B row of synthetic experiments)
        ref_m = bulk_basal_melt(0.1, 100.0, 2.0) * S_PER_D  # m/day
        exp_csv = OUT / "synthetic_melt_experiments.csv"
        if exp_csv.exists():
            exp = pd.read_csv(exp_csv)
            row_b = exp[exp["exp"] == "B"]
            if len(row_b) == 1:
                ok(abs(row_b["mb_mday"].iloc[0] - ref_m) / ref_m < 5.0e-4,
                   "T11. case B basal melt matches independent float64 formula",
                   f"model={row_b['mb_mday'].iloc[0]:.6f} ref={ref_m:.6f} m/day")
            else:
                skip("T11", "no case-B row")
        # velocity exponents from the sensitivity table
        vel = vel.sort_values("U_ms")
        if len(vel) >= 3:
            turb = vel[vel["U_ms"] >= 0.02]
            if len(turb) >= 2:
                r = turb["m_basal_mday"].iloc[1] / turb["m_basal_mday"].iloc[0]
                u_ratio = turb["U_ms"].iloc[1] / turb["U_ms"].iloc[0]
                ok(abs(r - u_ratio**0.8) / u_ratio**0.8 < 1.0e-3,
                   "T12. turbulent scaling m ~ U^0.8", f"measured={r:.5f} exp={u_ratio**0.8:.5f}")
            lam = vel[vel["U_ms"] < 0.02]
            if len(lam) >= 2:
                r = lam["m_basal_mday"].iloc[1] / lam["m_basal_mday"].iloc[0]
                u_ratio = lam["U_ms"].iloc[1] / lam["U_ms"].iloc[0]
                ok(abs(r - u_ratio**0.5) / u_ratio**0.5 < 1.0e-3,
                   "T13. laminar scaling m ~ U^0.5", f"measured={r:.5f} exp={u_ratio**0.5:.5f}")
            # absolute values vs independent formula
            for _, row in vel.iterrows():
                exp_m = bulk_basal_melt(row["U_ms"], 100.0, 2.0) * S_PER_D
                ok(abs(row["m_basal_mday"] - exp_m) / exp_m < 5.0e-4,
                   f"T14. m(U={row['U_ms']}) matches independent formula",
                   f"model={row['m_basal_mday']:.6f} ref={exp_m:.6f}")
        else:
            skip("T12..T14", "not enough velocity rows")

    # ------------------------------------------------------------------
    # 3. Temperature scaling (ocean linearity + air threshold)
    # ------------------------------------------------------------------
    temp_csv = OUT / "temperature_sensitivity.csv"
    if not temp_csv.exists():
        skip("T15..T19", "temperature_sensitivity.csv missing")
    else:
        temp = pd.read_csv(temp_csv)
        ocean = temp[temp["kind"] == "ocean"].sort_values("value_degC")
        if len(ocean) >= 3:
            ratios = ocean["m_basal_mday"].values
            ok(abs(ratios[1] / ratios[0] - 2.0) < 1.0e-3, "T15. basal m ~ dT linear (1K->2K)")
            ok(abs(ratios[2] / ratios[1] - 2.0) < 1.0e-3, "T16. basal m ~ dT linear (2K->4K)")
            ok(abs(ocean["m_lateral_mday"].iloc[1] / ocean["m_lateral_mday"].iloc[0] - 2.0) < 1.0e-3,
               "T17. lateral m ~ dT linear")
            # absolute lateral: C_LATERAL * dT
            ok(abs(ocean["m_lateral_mday"].iloc[0] - C_LATERAL * 1.0 * S_PER_D) / (C_LATERAL * S_PER_D) < 1.0e-4,
               "T18. lateral m == C_LATERAL*dT", f"model={ocean['m_lateral_mday'].iloc[0]:.6f}")
        air = temp[temp["kind"] == "air"].sort_values("value_degC")
        if len(air) >= 5:
            ms = air["m_surface_mday"].values
            ok(ms[0] == 0.0 and ms[1] == 0.0 and ms[2] == 0.0,
               "T19. no surface melt below threshold (250/260/270 K)")
            ok((np.diff(ms) >= 0).all(), "T20. surface melt monotone non-decreasing with T_air")
            ok(ms[-1] > 0.0 and ms[-2] > 0.0, "T21. surface melt active at warm air (280/285 K)")

    # ------------------------------------------------------------------
    # 4. Size scaling
    # ------------------------------------------------------------------
    size_csv = OUT / "size_sensitivity.csv"
    if not size_csv.exists():
        skip("T22..T24", "size_sensitivity.csv missing")
    else:
        sz = pd.read_csv(size_csv).sort_values("L_m")
        ok(len(sz) >= 3, "T22. at least 3 sizes")
        if len(sz) >= 3:
            l_big, l_small = sz["L_m"].iloc[-1], sz["L_m"].iloc[-2]
            r = sz["m_basal_mday"].iloc[-1] / sz["m_basal_mday"].iloc[-2]
            exp_r = (l_big / l_small) ** -0.2
            ok(abs(r - exp_r) / exp_r < 2.0e-3, "T23. basal m ~ L^-0.2 (turbulent)",
               f"measured={r:.5f} exp={exp_r:.5f}")
            ok(abs(sz["m_lateral_mday"].iloc[0] - sz["m_lateral_mday"].iloc[-1]) / sz["m_lateral_mday"].iloc[-1] < 1.0e-3,
               "T24. lateral m size-independent")
            frac = sz["dM_frac_day"].values
            ok(abs(frac[-1] * sz["L_m"].iloc[-1] - frac[-2] * sz["L_m"].iloc[-2])
               / (frac[-2] * sz["L_m"].iloc[-2]) < 5.0e-2,
               "T25. fractional mass loss ~ 1/L (lateral-dominated, 200 vs 100 m)")

    # ------------------------------------------------------------------
    # 5. Timestep sensitivity
    # ------------------------------------------------------------------
    ts_csv = OUT / "timestep_sensitivity.csv"
    if not ts_csv.exists():
        skip("T26..T27", "timestep_sensitivity.csv missing")
    else:
        ts = pd.read_csv(ts_csv)
        base = ts[ts["dt_s"] == 3600.0]["dM_kg"].iloc[0]
        for dt in (1800.0, 7200.0):
            row = ts[ts["dt_s"] == dt]
            if len(row):
                ok(abs(row["dM_kg"].iloc[0] - base) / base < 2.0e-2,
                   f"T26. dM(dt={dt:.0f}) within 2% of dM(dt=3600)")
        ok((ts["budget_err_rel"] < 1.0e-3).all(), "T27. budget closure < 1e-3 at all dt")

    # ------------------------------------------------------------------
    # 6. 90-day diagnostic run
    # ------------------------------------------------------------------
    if not TRAJ_90.exists():
        skip("T28..T31", "90-day trajectory missing")
    else:
        d90 = load_traj(TRAJ_90)
        ok(len(d90) == 2160, "T28. 90-day trajectory has 2160 rows")
        m90 = d90["M_kg"].values
        ok((np.diff(m90) <= 0).all(), "T29. 90-day mass monotonically non-increasing")
        ok((d90[["L_m", "W_m", "H_m"]].values > 0).all(), "T30. 90-day geometry positive")
        frac90 = (m90[0] - m90[-1]) / m90[0]
        ok(0.30 < frac90 < 0.55, "T31. 90-day fractional loss in diagnostic range",
           f"frac={frac90:.4f}")
        l_final = d90["L_m"].iloc[-1]
        ok(abs(l_final - (100.0 - 0.259 * 90.0)) < 1.0, "T32. L(90d) ~ 100 - ml*90 days",
           f"L={l_final:.2f} exp~{100.0 - 0.259 * 90.0:.2f}")

    # ------------------------------------------------------------------
    # 7. Zero-forcing experiment (case A)
    # ------------------------------------------------------------------
    exp_csv = OUT / "synthetic_melt_experiments.csv"
    if exp_csv.exists():
        exp = pd.read_csv(exp_csv)
        row_a = exp[exp["exp"] == "A"]
        if len(row_a) == 1:
            ok(row_a["mb_mday"].iloc[0] == 0.0 and row_a["ml_mday"].iloc[0] == 0.0
               and row_a["ms_mday"].iloc[0] == 0.0,
               "T33. zero thermal forcing -> zero melt (case A)")
        row_d = exp[exp["exp"] == "D"]
        if len(row_d) == 1:
            ok(row_d["mb_mday"].iloc[0] == 0.0 and row_d["ml_mday"].iloc[0] > 0.0,
               "T34. U_rel=0 -> basal=0, lateral>0 (case D)")

    # ------------------------------------------------------------------
    print("-" * 60)
    print(f"Total checks: {_CHECKS}  errors: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: STAGE 10.17 MELT BUDGET REGRESSION PASSED")
        sys.exit(0)
    print("FAILURE: STAGE 10.17 MELT BUDGET REGRESSION FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()