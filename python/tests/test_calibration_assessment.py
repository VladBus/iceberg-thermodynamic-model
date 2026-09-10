"""Stage 10.9 — calibration assessment of the basal-melt coefficient.

Checks A-T against the curated dataset and the independent Python closure:

    A production-formula reproduction        K C_gamma linearity (c regime-invariant)
    B EOS-80 freezing point                  L zero-flow = 0 with finite C_gamma
    C U_rel                                  M source-aware grouping / effective n
    D Reynolds number                        N NJ80 is one source, not n=3
    E laminar Nu                             O leave-one-source-out reproducibility
    F turbulent Nu + Stanton                 P missing forcing excluded
    G exact Re=5e5 transition                Q NaN honesty / no invented forcing
    H U monotonicity (exponents)             R no invented observations
    I dT monotonicity (linear)               S provenance consistency
    J L scaling                              T deterministic results

All expected values are embedded literals computed from the documented
equations (EOS-80, flat-plate Nusselt) and the 10.8.1/10.8.2 reference layers;
nothing is compared against Fortran output. This is an assessment of
identifiability, not a calibration:

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_calibration_assessment.py -v

(or: python python/tests/test_calibration_assessment.py)
"""

import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
import basal_melt as bm  # noqa: E402
import observational_validation as ov  # noqa: E402
import calibration_assessment as ca  # noqa: E402

TOL_EXACT = 1.0e-12         # pure identities (float64)
TOL_REF = 1.0e-6            # values derived from the CSV/equation transcript
TOL_MDAY = 1.0e-3           # per-row model melt rates (10.8.2 transcript)
TOL_PERM = 2.0e-2           # measured exponents / ratios (literature-robust)
DAY_S = 86400.0

_ERRORS = 0
_CHECKS = 0


def ok(cond, name, detail=""):
    global _ERRORS, _CHECKS
    _CHECKS += 1
    if cond:
        print(f"OK   {name} {detail}")
    else:
        _ERRORS += 1
        print(f"ERROR {name} {detail}")


def ok_rel(actual, expected, name, tol, note=""):
    ok(
        abs(float(actual) - float(expected)) / max(abs(float(expected)), 1e-300) <= tol,
        name,
        f"{note} (rel={abs(float(actual) - float(expected)) / max(abs(float(expected)), 1e-300):.3e})",
    )


def comparable_ids():
    return sorted(r["record_id"] for r in ca.comparable_rows())


# ===========================================================================
# A. Production-formula reproduction (10.8.1 closure, bit-level)
# ===========================================================================
def test_a_production_reproduction():
    for r in ca.comparable_rows():
        u = float(r["u_rel_m_s"])
        lc = float(r["L_char_m"])
        inline = bm.basal_melt_rate(
            ocean_temperature=float(r["T_degC"]),
            salinity_psu=float(r["S_psu"]),
            depth_m=lc,
            u_water=u, v_water=0.0, u_ice=0.0, v_ice=0.0,
            length_m=lc,
        ) * DAY_S
        a = ca.per_row_analysis(r)
        ok(inline == a["model_m_per_day"], f"A.1 {r['record_id']} inline == per_row_analysis")
    literals = {
        "NJ80_dT2": 0.0800302575,
        "NJ80_dT4": 0.1600605150,
        "NJ80_dT8": 0.3201210300,
        "KW84_DUrville": 0.0423044459,
    }
    for r in ca.comparable_rows():
        a = ca.per_row_analysis(r)
        ok_rel(a["model_m_per_day"], literals[a["record_id"]], f"A.2 {a['record_id']} m/day literal", TOL_MDAY)
    ok(ca.model_melt_m_per_day(ca.comparable_rows()[0]) ==
       ov.model_melt_m_per_day(ca.comparable_rows()[0]),
       "A.3 module delegates 10.8.2 model value")


# ===========================================================================
# B. EOS-80 freezing point
# ===========================================================================
def test_b_freezing_point():
    # UNESCO 1983 / Gill 1982 check value: Tf(40 PSU, P=500 dbar) = -2.588567
    S, P = 40.0, 500.0
    tf_check = (bm.EOS_FP_A0 + bm.EOS_FP_A1 * math.sqrt(S) - bm.EOS_FP_A2 * S) * S + bm.EOS_FP_BP * P
    ok_rel(tf_check, -2.588567, "B.1 UNESCO Tf(40,500 dbar) checkvalue", 1e-5)
    ok_rel(bm.ocean_freezing_point(35.0, 50.0), -1.960257, "B.2 Tf(35,50 m)", TOL_REF)
    ok_rel(bm.ocean_freezing_point(34.0, 20.0), -1.880185, "B.3 Tf(34,20 m)", TOL_REF)
    s_hi = bm.ocean_freezing_point(36.0, 50.0)
    s_lo = bm.ocean_freezing_point(34.0, 50.0)
    ok(s_hi < s_lo, "B.4 Tf decreases with salinity")
    z_hi = bm.ocean_freezing_point(35.0, 200.0)
    z_lo = bm.ocean_freezing_point(35.0, 50.0)
    ok(z_hi < z_lo, "B.5 Tf decreases with depth (pressure term)")


# ===========================================================================
# C. U_rel
# ===========================================================================
def test_c_relative_velocity():
    ok_rel(bm.relative_velocity(2.0, 3.0, 0.0, 0.0), math.sqrt(13.0), "C.1 analytic", TOL_EXACT)
    for r in ca.comparable_rows():
        u = float(r["u_rel_m_s"])
        ok_rel(bm.relative_velocity(u, 0.0, 0.0, 0.0), u, f"C.2 {r['record_id']}", TOL_EXACT)


# ===========================================================================
# D. Reynolds number
# ===========================================================================
def test_d_reynolds():
    ok_rel(bm.reynolds_number(0.1, 20.0), 1098901.098901, "D.1 Re(0.1,20)", TOL_REF)
    ok_rel(bm.reynolds_number(0.1, 50.0), 2747252.747253, "D.2 Re(0.1,50)", TOL_REF)
    ok(bm.reynolds_number(0.0, 50.0) == 0.0, "D.3 Re guard u<=0")
    ok(bm.reynolds_number(0.1, 0.0) == 0.0, "D.4 Re guard L<=0")


# ===========================================================================
# E. Laminar Nusselt
# ===========================================================================
def test_e_laminar_nusselt():
    ok_rel(bm.nusselt_number(1e5), 503.648767, "E.1 Nu_lam(Re=1e5)", 1e-5)
    re_small = 10.0
    expected = 0.664 * math.sqrt(re_small) * 13.8 ** (1.0 / 3.0)
    ok_rel(bm.nusselt_number(re_small), expected, "E.2 Nu_lam analytic identity", TOL_EXACT)


# ===========================================================================
# F. Turbulent Nusselt + Stanton convention
# ===========================================================================
def test_f_turbulent_nusselt_and_stanton():
    ok_rel(bm.nusselt_number(1e6), 5599.65692, "F.1 Nu_turb(Re=1e6)", 1e-5)
    re_big = 1e7
    expected = 0.037 * re_big**0.8 * 13.8 ** (1.0 / 3.0)
    ok_rel(bm.nusselt_number(re_big), expected, "F.2 Nu_turb analytic identity", TOL_EXACT)
    # gamma_T = Nu k / L identity
    for r in ca.comparable_rows():
        a = ca.per_row_analysis(r)
        re = bm.reynolds_number(float(r["u_rel_m_s"]), float(r["L_char_m"]))
        gamma_expect = bm.nusselt_number(re) * bm.THERMAL_CONDUCTIVITY / float(r["L_char_m"])
        ok_rel(a["gamma_T_W_per_m2K"], gamma_expect, f"F.3 {r['record_id']} gamma_T", TOL_EXACT)
    # Stanton numbers: production flat-plate model ~3-4e-4, obs-implied ~6e-5..6e-4
    st_table = {
        "NJ80_dT2": (3.436e-4, 5.882e-5),
        "NJ80_dT4": (3.436e-4, 9.999e-5),
        "NJ80_dT8": (3.436e-4, 1.617e-4),
        "KW84_DUrville": (4.127e-4, 5.854e-4),
    }
    for r in ca.comparable_rows():
        a = ca.per_row_analysis(r)
        sm, so = st_table[a["record_id"]]
        ok_rel(a["stanton_model"], sm, f"F.4 {a['record_id']} St_model", 1e-2)
        ok_rel(a["stanton_implied_by_obs"], so, f"F.5 {a['record_id']} St_obs", 1e-2)
    # melt-driven glaciological anchor (Jenkins et al. 2010) far above flat-plate shear St
    ok(ca.ST_MELTWATER_JENKINS > 10 * max(sm for r in ca.comparable_rows()
                                          for sm, _ in [st_table[r["record_id"]]]),
       "F.6 melt-driven St >> flat-plate shear St")


# ===========================================================================
# G. Exact laminar/turbulent transition at Re=5e5
# ===========================================================================
def test_g_transition():
    ok(bm.nusselt_number(4.9999e5) == bm.nusselt_number(4.9999e5) < bm.nusselt_number(5.0e5),
       "G.1 jump at exactly Re=5e5")
    ok(bm.reynolds_number(0.1, 50.0) >= bm.REYNOLDS_CRITICAL, "G.2 comparable rows turbulent")
    ok(bm.reynolds_number(0.01, 10.0) < bm.REYNOLDS_CRITICAL, "G.3 small-flow row laminar")
    jump = bm.nusselt_number(5.0e5) / bm.nusselt_number(4.9999e5)
    ok_rel(jump, 2.8558, "G.4 transition jump ratio", 1e-3)
    ok(all(ca.per_row_analysis(r)["regime"] == "turbulent" for r in ca.comparable_rows()),
       "G.5 all comparable rows classified turbulent")


# ===========================================================================
# H. U monotonicity (exponent 0.8 turbulent / 0.5 laminar)
# ===========================================================================
def test_h_u_monotonicity():
    # turbulent: fixed dT, L=50 m, S=35
    def turb(u):
        return bm.basal_melt_rate(
            ocean_temperature=bm.ocean_freezing_point(35.0, 50.0) + 4.0,
            salinity_psu=35.0, depth_m=50.0,
            u_water=u, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=50.0,
        )
    ok_rel(turb(0.1) / turb(0.05), 2.0**0.8, "H.1 turbulent m ~ U^0.8", TOL_PERM)
    # laminar: L=1 m -> Re < 5e5 for U<=0.01
    def lam(u):
        return bm.basal_melt_rate(
            ocean_temperature=bm.ocean_freezing_point(35.0, 1.0) + 2.0,
            salinity_psu=35.0, depth_m=1.0,
            u_water=u, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=1.0,
        )
    ok(bm.reynolds_number(0.01, 1.0) < 5e5, "H.2 laminar base state in regime")
    ok_rel(lam(0.02) / lam(0.01), 2.0**0.5, "H.3 laminar m ~ U^0.5", TOL_PERM)
    ok(turb(0.2) > turb(0.1) > turb(0.05), "H.4 monotone increasing in U")


# ===========================================================================
# I. dT monotonicity (linear in dT) and freezing clamp
# ===========================================================================
def test_i_dT_monotonicity():
    def melt_dt(dt):
        return bm.basal_melt_rate(
            ocean_temperature=bm.ocean_freezing_point(35.0, 50.0) + dt,
            salinity_psu=35.0, depth_m=50.0,
            u_water=0.1, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=50.0,
        )
    ok_rel(melt_dt(4.0) / melt_dt(2.0), 2.0, "I.1 closure linear in dT (4/2)", 1e-6)
    ok_rel(melt_dt(8.0) / melt_dt(4.0), 2.0, "I.2 closure linear in dT (8/4)", 1e-6)
    ok(melt_dt(-1.0) == 0.0, "I.3 freezing clamp -> 0")
    ok(ca.thermal_driving_degC(ca.comparable_rows()[0]) >= 0.0, "I.4 dT never negative")
    ok(ca.identifiability_summary()["linear_dT_model"], "I.5 model dT exponent = 1.0")


# ===========================================================================
# J. L scaling (turbulent L^-0.2) + measured exponents
# ===========================================================================
def test_j_l_scaling():
    def melt_l(L):
        return bm.basal_melt_rate(
            ocean_temperature=bm.ocean_freezing_point(35.0, L) + 4.0,
            salinity_psu=35.0, depth_m=L,
            u_water=0.1, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=L,
        )
    m202 = melt_l(20.0) * 20.0**0.2
    m502 = melt_l(50.0) * 50.0**0.2
    m1002 = melt_l(100.0) * 100.0**0.2
    ok_rel(m202 / m502, 1.0, "J.1 m*L^0.2 const (20 vs 50)", TOL_PERM)
    ok_rel(m202 / m1002, 1.0, "J.2 m*L^0.2 const (20 vs 100)", TOL_PERM)
    ok_rel(melt_l(20.0) / melt_l(100.0), 5.0**0.2, "J.3 m(20)/m(100) = 5^0.2", TOL_PERM)
    et = ca.sensitivity_exponents("turbulent")
    el = ca.sensitivity_exponents("laminar")
    ok_rel(et["a_U"], 0.8, "J.4 turbulent a_U", 1e-4)
    ok_rel(et["a_L"], -0.2, "J.5 turbulent a_L", 1e-4)
    ok_rel(et["a_dT"], 1.0, "J.6 turbulent a_dT", 1e-4)
    ok(et["a_C"] > 0.999, "J.7 turbulent a_C ~ 1", f"(a_C={et['a_C']:.5f})")
    ok_rel(el["a_U"], 0.5, "J.8 laminar a_U", 1e-4)
    ok_rel(el["a_L"], -0.5, "J.9 laminar a_L", 1e-4)


# ===========================================================================
# K. C_gamma linearity (a pure scale factor, identical across regimes)
# ===========================================================================
def test_k_c_gamma_linearity():
    for r in ca.comparable_rows():
        base = ca.per_row_analysis(r)["model_m_per_day"]
        for c in (0.25, 0.5, 1.0, 2.0, 4.0, 3.7):
            ok_rel(ca.c_gamma_grid_model(r, c), c * base, f"K.1 {r['record_id']} C={c}", TOL_EXACT)
        ok(ca.c_gamma_grid_model(r, 0.0) == 0.0, f"K.2 {r['record_id']} C=0 -> 0")
    # the grid bounds are per spec
    ok(ca.C_GAMMA_LO == 0.25 and ca.C_GAMMA_HI == 4.0, "K.3 spec grid bounds")


# ===========================================================================
# L. Zero flow = 0 with any finite C_gamma (structural, not calibratable)
# ===========================================================================
def test_l_zero_flow():
    rows = ca.load_rows()
    rh = [r for r in rows if r["record_id"] == "RH_0C"][0]
    ok(float(rh["u_rel_m_s"]) == 0.0, "L.1 RH_0C is quiescent")
    ok(ca.model_melt_m_per_day(rh) == 0.0, "L.2 closure -> 0 at rest")
    ok(ca.c_gamma_grid_model(rh, 1000.0) == 0.0, "L.3 zero-flow stays 0 for C=1000")
    gaps = ca.natural_convection_gap(rows)
    ok(len(gaps) == 5, "L.4 five quiescent lab rows")
    for g, exp in zip(gaps, (5.7, 6.2, 6.6, 6.9, 7.3)):
        ok(abs(g["orders_above_model_floor"] - exp) < 0.05,
           f"L.5 {g['record_id']} orders ~ {exp}", f"(got {g['orders_above_model_floor']:.2f})")


# ===========================================================================
# M. Source-aware grouping / effective sample size
# ===========================================================================
def test_m_source_aware_grouping():
    eff = ca.effective_sample_size()
    ok(eff["n_rows"] == 4, "M.1 rows = 4", f"(n={eff['n_rows']})")
    ok(eff["n_sources"] == 2, "M.2 effective sources = 2", f"(n={eff['n_sources']})")
    ok("neshybaEstimationAntarcticIceberg1980" in eff["sources"] and
       "keysWilliamsFieldMeasurementsSubmarine1984" in eff["sources"], "M.3 source keys")
    ok(eff["row_source_counts"]["neshybaEstimationAntarcticIceberg1980"] == 3, "M.4 NJ80 grouped as 3 rows/1 source")
    ok(eff["row_source_counts"]["keysWilliamsFieldMeasurementsSubmarine1984"] == 1, "M.5 KW84 1 row")


# ===========================================================================
# N. NJ80 is one source, NOT three independent observations
# ===========================================================================
def test_n_nj80_not_n3():
    eff = ca.effective_sample_size()
    ok(eff["n_sources"] < eff["n_rows"], "N.1 n_sources < n_rows")
    ps = ca.per_source_geomean()
    ok(len(ps) == 2, "N.2 exactly two source-fit entries")
    ok_rel(ps["neshybaEstimationAntarcticIceberg1980"]["geometric_mean"], 0.286209, "N.3 NJ80 geomean", 1e-4)
    ok_rel(ps["keysWilliamsFieldMeasurementsSubmarine1984"]["geometric_mean"], 1.418291, "N.4 KW84 geomean", 1e-4)
    nj80_ids = [a["record_id"] for r in ca.comparable_rows()
                if r["record_id"].startswith("NJ80")
                for a in [ca.per_row_analysis(r)]]
    ok(len(nj80_ids) == 3 and len(set(ca.effective_sample_size()["sources"])) == 2,
       "N.5 the 3 NJ80 rows collapse to one source")


# ===========================================================================
# O. Leave-one-source-out reproducibility and numbers
# ===========================================================================
def test_o_leave_one_source_out():
    loso1 = ca.leave_one_source_out()
    loso2 = ca.leave_one_source_out()
    ok(str(sorted(loso1)) == str(sorted(loso2)), "O.1 LOOSO deterministic (two runs equal)")
    nj80 = "neshybaEstimationAntarcticIceberg1980"
    kw84 = "keysWilliamsFieldMeasurementsSubmarine1984"
    # keys name the LEFT-OUT source; training-set fit is shown for the other source
    ok_rel(loso1[nj80]["fit_multiplier"], 1.4183, "O.2 KW84-only fit C", 1e-3)
    held_nj = {h["record_id"]: h["model_over_obs_at_refit"] for h in loso1[nj80]["held_out"]}
    ok_rel(held_nj["NJ80_dT2"], 8.286, "O.3 NJ80_dT2 held-out model/obs (KW84 fit)", 1e-2)
    ok_rel(held_nj["NJ80_dT4"], 4.874, "O.4 NJ80_dT4 held-out model/obs (KW84 fit)", 1e-2)
    ok_rel(held_nj["NJ80_dT8"], 3.013, "O.5 NJ80_dT8 held-out model/obs (KW84 fit)", 1e-2)
    ok_rel(loso1[kw84]["fit_multiplier"], 0.2862, "O.6 NJ80-only fit C", 1e-3)
    held_kw = [h["model_over_obs_at_refit"] for h in loso1[kw84]["held_out"]]
    ok_rel(held_kw[0], 0.202, "O.7 KW84 held-out model/obs (NJ80 fit)", 1e-2)
    # no refit reproduces both sources near 1 -> identifiability failure signature
    ok(all(abs(h["residual_log10"]) > 0.4 for src in loso1 for h in loso1[src]["held_out"]),
       "O.8 every held-out source shows a >2.5x residual")


# ===========================================================================
# P. Missing forcing excluded from the calibration basis
# ===========================================================================
def test_p_missing_forcing():
    ids = comparable_ids()
    ok(ids == sorted(["NJ80_dT2", "NJ80_dT4", "NJ80_dT8", "KW84_DUrville"]),
       "P.1 comparable set is exactly the 4 metric rows", f"({ids})")
    for r in ca.load_rows():
        if r["tier"] == "rs-derived" and r["record_id"] != "OPEN_SO_context":
            ok(r["record_id"] not in ids, f"P.2 rs row {r['record_id']} excluded")
            ok(r["record_id"] not in [a["record_id"] for x in ca.comparable_rows()
                                      for a in [ca.per_row_analysis(x)]],
               f"P.3 {r['record_id']} never enters per-row analysis")


# ===========================================================================
# Q. NaN honesty / no invented forcing
# ===========================================================================
def test_q_nan_honesty():
    import math as _m
    for r in ca.load_rows():
        for col in ("T_degC", "S_psu", "u_rel_m_s", "L_char_m"):
            v = r.get(col)
            nan = isinstance(v, float) and _m.isnan(v)
            if r["tier"] == "rs-derived" and r["record_id"] != "OPEN_SO_context":
                ok(nan, f"Q.1 {r['record_id']} forcing {col} honestly NaN")
            elif r["include_in_metrics"]:
                ok(not nan, f"Q.2 {r['record_id']} {col} defined")
    # pooled fit uses only comparable rows
    sp = ca.inferred_multiplier_spread()
    ok(len(sp["rows"]) == 4, "Q.3 spread computed over 4 comparable rows only")


# ===========================================================================
# R. No invented observations
# ===========================================================================
def test_r_no_invented_observations():
    rows = ca.load_rows()
    ok(len(rows) == 19, "R.1 19 curated records", f"(n={len(rows)})")
    ok(all(abs(x["obs_m_per_day"] - x["obs_m_per_s"] * DAY_S) / x["obs_m_per_day"] < 1e-6
           for x in rows),
       "R.2 every obs_m_per_day == obs_m_per_s*86400 (CSV presentation rounding)")
    ok(all(x["obs_m_per_day"] > 0 for x in rows), "R.3 obs melt positive")
    ids = [x["record_id"] for x in rows]
    ok(len(ids) == len(set(ids)), "R.4 record_id unique")
    prov = (Path(ca._REPO_ROOT) / "data" / "validation" / "observations"
            / "iceberg_basal_melt_observations_provenance.md")
    ok(prov.is_file(), "R.5 provenance doc present")


# ===========================================================================
# S. Provenance consistency (tiers, coverage)
# ===========================================================================
def test_s_provenance_consistency():
    rows = ca.load_rows()
    tiers = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    ok(tiers.get("lab-primary") == 5, "S.1 lab-primary 5")
    ok(tiers.get("synthesis-derived") == 3, "S.2 synthesis-derived 3")
    ok(tiers.get("field-primary") == 1, "S.3 field-primary 1")
    ok(tiers.get("rs-derived") == 10, "S.4 rs-derived 10")
    ok(sum(tiers.values()) == 19, "S.5 total 19")
    ok(all(r["melt_component"] in ("basal", "submarine") for r in ca.comparable_rows()),
       "S.6 comparable rows carry documented melt_component")
    # melt-room honesty: rs rows are submarine, KW84/RH are basal (documented in CSV)


# ===========================================================================
# T. Deterministic results / headline identifiability findings
# ===========================================================================
def test_t_deterministic_and_headline():
    s1 = ca.identifiability_summary()
    s2 = ca.identifiability_summary()
    ok(str(s1["inferred_c_gamma_spread"]) == str(s2["inferred_c_gamma_spread"]),
       "T.1 summary deterministic")
    ok(str(ca.best_fit_c_gamma()) == str(ca.best_fit_c_gamma()), "T.2 best-fit deterministic")
    sp = s1["inferred_c_gamma_spread"]
    ok_rel(sp["max_over_min"], 8.286, "T.3 inferred C_gamma spans 8.29x", 1e-3)
    ok_rel(sp["geometric_mean"], 0.42703, "T.4 pooled geomean", 1e-3)
    ok_rel(sp["log10_decades"], 0.918, "T.5 ~0.92 decades", 1e-3)
    ok_rel(s1["nj80_obs_dT_exponent"], 1.7297, "T.6 NJ80 obs ~ dT^1.73", 1e-3)
    ok_rel(s1["rh80_obs_T_exponent"], 1.50, "T.7 RH80 obs ~ T^1.50", 1e-3)
    ok(s1["closure_dT_exponent"] == 1.0, "T.8 closure linear in dT")
    ok(s1["conclusion"].startswith("Calibration of a scalar multiplier"), "T.9 conclusion header")
    # number derived from the three individual claims
    ok(0.42 < sp["geometric_mean"] < 0.43, "T.10 headline multiplier, not ~1 or ~5")


# Runner
# ===========================================================================
if __name__ == "__main__":
    for f in (
        test_a_production_reproduction,
        test_b_freezing_point,
        test_c_relative_velocity,
        test_d_reynolds,
        test_e_laminar_nusselt,
        test_f_turbulent_nusselt_and_stanton,
        test_g_transition,
        test_h_u_monotonicity,
        test_i_dT_monotonicity,
        test_j_l_scaling,
        test_k_c_gamma_linearity,
        test_l_zero_flow,
        test_m_source_aware_grouping,
        test_n_nj80_not_n3,
        test_o_leave_one_source_out,
        test_p_missing_forcing,
        test_q_nan_honesty,
        test_r_no_invented_observations,
        test_s_provenance_consistency,
        test_t_deterministic_and_headline,
    ):
        f()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.9 calibration assessment PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.9 calibration assessment FAILED")
        sys.exit(1)