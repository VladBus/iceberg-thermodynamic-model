"""Stage 10.8.2 — independent observational validation of the basal-melt closure.

Checks A-O against the curated observational dataset
(``data/validation/observations/iceberg_basal_melt_observations.csv``) and the
production closure reproduced in ``python/validation/observational_validation.py``
and ``python/validation/basal_melt.py``.

The expected values used here are hand-computed from embedded literals
(EOS-80 coefficients, flat-plate Nu, RH80 power law, yearly conversions);
nothing is compared against Fortran output. This is validation, not
calibration — no coefficient is adjusted.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_observational_validation.py -v

(or: python python/tests/test_observational_validation.py)
"""

import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
import basal_melt as bm  # noqa: E402
import observational_validation as ov  # noqa: E402

TOL_EXACT = 1.0e-12         # pure identities / unit conversions (float64)
TOL_REF = 1.0e-6            # values derived from the CSV transcription
DAY_S = 86400.0

_ERRORS = 0
_CHECKS = 0


def _rel(a, b):
    return abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)), 1e-300)


def ok(cond, name, detail=""):
    global _ERRORS, _CHECKS
    _CHECKS += 1
    if cond:
        print(f"OK   {name} {detail}")
    else:
        _ERRORS += 1
        print(f"ERROR {name} {detail}")


def ok_rel(actual, expected, name, tol, note=""):
    ok(_rel(actual, expected) <= tol, name, f"{note} (rel={_rel(actual, expected):.3e})")


def try_mpl():
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        return False


# ===========================================================================
# A. Dataset integrity
# ===========================================================================
def test_a_dataset_integrity():
    rows = ov.load_observations()
    ok(10 <= len(rows) <= 25, "A.1 dataset size", f"(n={len(rows)})")
    ids = [r["record_id"] for r in rows]
    ok(len(ids) == len(set(ids)), "A.2 unique record_id")
    for col in (
        "record_id", "source_key", "region", "period", "method", "tier",
        "melt_component", "T_degC", "S_psu", "u_rel_m_s", "L_char_m",
        "obs_m_per_s", "obs_m_per_day", "obs_unc_m_per_day",
        "include_in_metrics",
    ):
        ok(all(col in r for r in rows), f"A.3 column present: {col}")
    ok(all(r["obs_m_per_day"] >= 0 for r in rows), "A.4 obs_m_per_day >= 0")
    ok(all(not math.isnan(r["obs_m_per_day"]) for r in rows), "A.5 obs_m_per_day defined")
    n_true = sum(1 for r in rows if r["include_in_metrics"])
    ok(1 <= n_true <= 6, "A.6 include_in_metrics count sane", f"(n_true={n_true})")
    ok(any(not r["include_in_metrics"] for r in rows), "A.7 some rows excluded")
    try:
        ov.load_observations(Path("/nonexistent_file.csv"))
        ok(False, "A.8 missing file raises FileNotFoundError")
    except FileNotFoundError:
        ok(True, "A.8 missing file raises FileNotFoundError")


# ===========================================================================
# B. Numeric consistency (unit conversion, uncertainty)
# ===========================================================================
def test_b_numeric_consistency():
    rows = ov.load_observations()
    for r in rows:
        day = float(r["obs_m_per_day"])
        sec = float(r["obs_m_per_s"])
        ok_rel(sec, day / DAY_S, f"B.1 {r['record_id']} m/s = m/day/86400", 1e-6)
        u = float(r["obs_unc_m_per_day"])
        if not math.isnan(u):
            ok(u > 0.0, f"B.2 {r['record_id']} uncertainty positive")
    for r in rows:
        if not math.isnan(float(r["S_psu"])):
            ok(30.0 <= float(r["S_psu"]) <= 42.0, f"B.3 {r['record_id']} S in [30,42]")
        if not math.isnan(float(r["T_degC"])):
            ok(-3.0 <= float(r["T_degC"]) <= 20.0, f"B.4 {r['record_id']} T in [-3,20]")
        ok(0.0 <= float(r["obs_m_per_day"]) <= 2.0, f"B.5 {r['record_id']} obs in [0,2] m/day")


# ===========================================================================
# C. No fabricated forcing on remote-sensing rows
# ===========================================================================
def test_c_missing_field_honesty():
    rows = ov.load_observations()
    rs = [r for r in rows if r["tier"] == "rs-derived"]
    for r in rs:
        ok(math.isnan(float(r["T_degC"])), f"C.1 {r['record_id']} T NaN (not invented)")
        ok(math.isnan(float(r["u_rel_m_s"])), f"C.2 {r['record_id']} u_rel NaN")
        ok(math.isnan(float(r["S_psu"])), f"C.3 {r['record_id']} S NaN")
        ok(math.isnan(float(r["L_char_m"])), f"C.4 {r['record_id']} L_char NaN")
        ok(not r["include_in_metrics"], f"C.5 {r['record_id']} excluded from metrics")
    comp = [r for r in rows if r["include_in_metrics"]]
    for r in comp:
        for col in ("T_degC", "S_psu", "u_rel_m_s", "L_char_m"):
            ok(not math.isnan(float(r[col])), f"C.6 {r['record_id']} {col} defined")
        ok(float(r["u_rel_m_s"]) > 0.0, f"C.7 {r['record_id']} u_rel > 0")


# ===========================================================================
# D. Natural-convection gap (quiescent lab rows)
# ===========================================================================
def test_d_natural_convection_gap():
    ok(ov.FLOOR_M_PER_S == bm.MELT_RATE_MIN, "D.1 floor constant mirrors production guard")
    rows = ov.load_observations()
    gaps = ov.gap_test(rows)
    n_lab = sum(1 for r in rows if r["tier"] == "lab-primary")
    ok(len(gaps) == n_lab, "D.2 gap test covers lab rows", f"(n={len(gaps)}, lab={n_lab})")
    for g in gaps:
        ok(g["model_m_per_day"] == 0.0, f"D.3 {g['record_id']} model value 0 at U=0")
        ok(0.04 <= g["obs_m_per_day"] <= 1.6, f"D.4 {g['record_id']} obs in 0.04..1.6 m/day")
        ok(g["gap_orders"] >= 5.0, f"D.5 {g['record_id']} gap >= 5 orders",
           f"({g['gap_orders']:.2f})")
    lab = [r for r in rows if r["tier"] == "lab-primary"]
    ok(all(ov.model_melt_m_per_day(r) == 0.0 for r in lab),
       "D.6 closure gives 0 for every quiescent lab row")
    ok(all(bm.basal_melt_rate(T, S, z, 0.0, 0.0, 0.0, 0.0, L) == 0.0
           for T, S, z, L in [(2.0, 35.0, 1.0, 1.0), (18.0, 35.0, 1.0, 1.0)]),
       "D.7 production closure returns 0 at rest")


# ===========================================================================
# E. Russell & Head 1980 power law reproduces the CSV rows
# ===========================================================================
def test_e_russellhead_power_law():
    rows = ov.load_observations()
    lab = [r for r in rows if r["tier"] == "lab-primary"]
    ok(len(lab) == 5, "E.1 five RH80 rows")
    for r in lab:
        t = float(r["T_degC"])
        expected = 1.8e-2 * (t + 1.8) ** 1.5  # m/day (independent literal)
        ok_rel(float(r["obs_m_per_day"]), expected,
               f"E.2 {r['record_id']} R=1.8e-2(T+1.8)^1.5", 1e-6)
    r18 = float(lab[4]["obs_m_per_day"])
    r0 = float(lab[0]["obs_m_per_day"])
    ok(r18 >= 1.0, "E.3 RH80 melt at 18 degC > 1 m/day", f"({r18:.4f})")
    ok_rel(r18 / r0, (19.8 / 1.8) ** 1.5, "E.4 RH80 18/0 ratio = (19.8/1.8)^1.5", 1e-6)


# ===========================================================================
# F. Neshyba & Josberger 1980 synthesis conversions + monotonicity
# ===========================================================================
def test_f_nj80_conversions():
    rows = ov.load_observations()
    nj = [r for r in rows if r["record_id"].startswith("NJ80")]
    nj = sorted(nj, key=lambda r: float(r["obs_m_per_day"]))
    yearly = (5.0, 17.0, 55.0)  # m/yr at dT = 2, 4, 8 degC
    for r, yr in zip(nj, yearly):
        ok_rel(float(r["obs_m_per_day"]), yr / 365.0,
               f"F.1 {r['record_id']} {yr} m/yr conversion", 1e-6)
    obs = [float(r["obs_m_per_day"]) for r in nj]
    ok(obs[0] < obs[1] < obs[2], "F.2 NJ80 monotonic increase with dT")
    tfs = [bm.ocean_freezing_point(35.0, 50.0) for _ in range(3)]
    dts = [float(r["T_degC"]) - tfs[0] for r in nj]
    ok(_rel(dts[2], 8.0) < 1e-6, "F.3 dT=8 row consistent", f"(dT={dts[2]:.4f})")


# ===========================================================================
# G. Keys & Williams 1984 order-of-magnitude agreement
# ===========================================================================
def test_g_kw84_order1_agreement():
    rows = ov.load_observations()
    kw = next(r for r in rows if r["record_id"] == "KW84_DUrville")
    model = ov.model_melt_m_per_day(kw)
    obs = float(kw["obs_m_per_day"])
    ok(obs / 4.0 <= model <= 4.0 * obs,
       "G.1 model within factor 4 of KW84 observation", f"(model={model:.4f} obs={obs:.4f})")
    # Independent literal check of the closure at the KW84 forcing.
    t = -1.0
    s = 34.0
    depth = 20.0
    u = 0.1
    p = bm.RHO_WATER * bm.GRAVITY * depth / 1.0e4
    tfc = (bm.EOS_FP_A0 + bm.EOS_FP_A1 * math.sqrt(s) - bm.EOS_FP_A2 * s) * s + bm.EOS_FP_BP * p
    dt = t - tfc
    re = u * depth / bm.KINEMATIC_VISCOSITY
    nu_n = (
        0.037 * re**0.8 * bm.PRANDTL_NUMBER ** (1.0 / 3.0)
        if re >= bm.REYNOLDS_CRITICAL
        else 0.664 * math.sqrt(re) * bm.PRANDTL_NUMBER ** (1.0 / 3.0)
    )
    gamma = nu_n * bm.THERMAL_CONDUCTIVITY / depth
    m_lit = gamma * dt / (bm.RHO_ICE * bm.LATENT_HEAT) * DAY_S
    ok_rel(model, m_lit, "G.2 KW84 model matches independent literal closure", 1e-6)


# ===========================================================================
# H. Metric identities
# ===========================================================================
def test_h_metrics_identities():
    cmp = ov.compare_rows()
    ok(1 <= len(cmp) <= 6, "H.1 comparable rows count", f"(n={len(cmp)})")
    obs = [o for _, o, _, _, _ in cmp]
    mod = [m for _, _, m, _, _ in cmp]
    met = ov.compute_metrics(obs, mod)
    ok(met["rmse_m_per_day"] >= abs(met["bias_m_per_day"]), "H.2 RMSE >= |bias|")
    ok(met["mae_m_per_day"] >= abs(met["bias_m_per_day"]), "H.3 MAE >= |bias|")
    ok(met["rmse_m_per_day"] >= met["mae_m_per_day"], "H.4 RMSE >= MAE")
    ok(met["min_rel_err"] >= -1.0, "H.5 min rel err >= -1 (model/obs >= 0)")
    exp_mean = sum(math.log10(m / o) for m, o in zip(mod, obs)) / len(obs)
    ok_rel(met["mean_log10_ratio"], exp_mean, "H.6 mean log10 ratio consistent", 1e-12)


# ===========================================================================
# I. Inverse-U analysis
# ===========================================================================
def test_i_inverse_u():
    m_obs = 0.39 / DAY_S  # END14_Sermilik
    u2, ok2 = ov.required_u_rel(m_obs, delta_t_degC=2.0, length_m=50.0)
    ok(ok2, "I.1 END14 dT=2 converges")
    ok(0.1 < u2 < 5.0, "I.2 END14 dT=2 required U in (0.1, 5)", f"(U={u2:.3f})")
    dt_set = (1.0, 2.0, 4.0)
    us = [ov.required_u_rel(m_obs, dt, 50.0)[0] for dt in dt_set]
    ok(us[0] > us[1] > us[2], "I.3 required U decreases with dT", f"({us[0]:.2f}>{us[1]:.2f}>{us[2]:.2f})")
    tmp = bm.ocean_freezing_point(35.0, 50.0) + 2.0
    m_check = bm.basal_melt_rate(tmp, 35.0, 50.0, u2, 0.0, 0.0, 0.0, 50.0)
    ok_rel(m_check, m_obs, "I.4 root reproduces observed melt", 1e-6)
    u_hi, ok_hi = ov.required_u_rel(1.5 / DAY_S, 0.5, 50.0)
    ok(not ok_hi, "I.5 OPEN 1.5 m/day at dT=0.5 unreachable within U<=20")
    tbl = ov.inverse_u_table()
    ok(all(e["record_id"].startswith(("END14", "END16", "END23")) for e in tbl),
       "I.6 inverse-U table covers remote-sensing rows", f"(n={len(tbl)})")


# ===========================================================================
# J. Exact model-vs-model consistency with the Stage 10.8.1 layer
# ===========================================================================
def test_j_model_consistency():
    rows = ov.load_observations()
    kw = next(r for r in rows if r["record_id"] == "KW84_DUrville")
    via_ov = ov.model_melt_m_per_day(kw)
    direct = bm.basal_melt_rate(
        ocean_temperature=float(kw["T_degC"]),
        salinity_psu=float(kw["S_psu"]),
        depth_m=float(kw["L_char_m"]),
        u_water=float(kw["u_rel_m_s"]),
        v_water=0.0,
        u_ice=0.0,
        v_ice=0.0,
        length_m=float(kw["L_char_m"]),
    ) * DAY_S
    ok(via_ov == direct, "J.1 observational layer == basal_melt closure")
    ok(via_ov > 0.0, "J.2 KW84 model positive")
    ok(_rel(via_ov, direct) < TOL_EXACT, "J.3 identity within float64 exact tolerances")


# ===========================================================================
# K. EOS-80 freezing points used for the comparisons
# ===========================================================================
def test_k_freezing_points():
    ok_rel(bm.ocean_freezing_point(34.0, 20.0), -1.8801847,
           "K.1 Tf(34 PSU, 20 m)", TOL_REF)
    ok_rel(bm.ocean_freezing_point(35.0, 50.0), -1.9602572,
           "K.2 Tf(35 PSU, 50 m)", TOL_REF)
    tfc = bm.ocean_freezing_point(34.0, 20.0)
    ok(tfc < -1.0, "K.3 KW84 Tf below -1 degC (T=-1 above-freezing driving)")


# ===========================================================================
# L. Regime classification
# ===========================================================================
def test_l_regime_classification():
    ok(ov.regime_name(bm.reynolds_number(0.1, 20.0)) == "turbulent",
       "L.1 KW84 (U=0.1, L=20) turbulent")
    ok(ov.regime_name(bm.reynolds_number(0.01, 1.0)) == "laminar",
       "L.2 slow/small laminar")
    ok(ov.regime_name(bm.REYNOLDS_CRITICAL) == "turbulent",
       "L.3 exactly at Re_crit selects turbulent branch (production rule)")
    cmp = ov.compare_rows()
    ok(all(re >= bm.REYNOLDS_CRITICAL for _, _, _, _, re in cmp),
       "L.4 all comparable observations lie in the turbulent regime")


# ===========================================================================
# M. Sensitivity of the closure to the reference U/L assumptions
# ===========================================================================
def test_m_sensitivity():
    # At NJ80 forcing (S=35, depth 50, dT=4): turbulent regime U^0.8 L^-0.2.
    t = bm.ocean_freezing_point(35.0, 50.0) + 4.0
    m_base = bm.basal_melt_rate(t, 35.0, 50.0, 0.1, 0.0, 0.0, 0.0, 50.0)
    m_dl = bm.basal_melt_rate(t, 35.0, 50.0, 0.1, 0.0, 0.0, 0.0, 100.0)
    m_du = bm.basal_melt_rate(t, 35.0, 50.0, 0.2, 0.0, 0.0, 0.0, 50.0)
    r_l = m_dl / m_base
    r_u = m_du / m_base
    ok(0.7 <= r_l <= 1.0, "M.1 L:50->100 scales ~ L^-0.2 (factor in [0.7,1.0])", f"({r_l:.3f})")
    ok(1.5 <= r_u <= 2.0, "M.2 U:0.1->0.2 scales ~ U^0.8 (factor in [1.5,2.0])", f"({r_u:.3f})")
    ok_rel(r_l, 0.5 ** 0.2, "M.3 L ratio exponent check", 1e-6)
    ok_rel(r_u, 2.0 ** 0.8, "M.4 U ratio exponent check", 1e-6)


# ===========================================================================
# N. Plot generation (<= 6 figures, non-trivial files)
# ===========================================================================
def test_n_plots():
    ok(len(ov.PLOT_NAMES) == 6, "N.1 exactly six figures specified")
    rows = ov.load_observations()
    if not try_mpl():
        print("SKIP N.2..N.5 (matplotlib unavailable)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        saved = ov.make_plots(rows, outdir=tmp)
        ok(len(saved) == 6, "N.2 six figures generated", f"(n={len(saved)})")
        for s in saved:
            p = Path(s)
            ok(p.stat().st_size > 500, f"N.3 {p.name} non-trivial size",
               f"({p.stat().st_size} bytes)")
        ok(Path(sorted(saved)[0]).parent == Path(tmp), "N.4 figures written to requested dir")
        ok(all(Path(s).name == n for s, n in zip(sorted(saved), sorted(ov.PLOT_NAMES))),
           "N.5 figure names match PLOT_NAMES")


# ===========================================================================
# O. Sensitivity table helper
# ===========================================================================
def test_o_sensitivity_table():
    t = bm.ocean_freezing_point(35.0, 50.0) + 4.0
    tab = ov.sensitivity_sweep(t, 35.0, 50.0)
    ok(len(tab) == 9, "O.1 3x3 U x L grid", f"(n={len(tab)})")
    ok(0.0 < tab[(0.1, 50.0)] < 1.0, "O.2 central cell in plausible band",
       f"({tab[(0.1, 50.0)]:.4f} m/day)")
    ok(tab[(0.2, 50.0)] > tab[(0.1, 50.0)], "O.3 increasing in U")
    ok(tab[(0.1, 50.0)] > tab[(0.1, 100.0)], "O.4 decreasing in L")
    ok(all(v > 0.0 for v in tab.values()), "O.5 all cells positive")


# ===========================================================================
# Runner
# ===========================================================================
if __name__ == "__main__":
    for f in (
        test_a_dataset_integrity,
        test_b_numeric_consistency,
        test_c_missing_field_honesty,
        test_d_natural_convection_gap,
        test_e_russellhead_power_law,
        test_f_nj80_conversions,
        test_g_kw84_order1_agreement,
        test_h_metrics_identities,
        test_i_inverse_u,
        test_j_model_consistency,
        test_k_freezing_points,
        test_l_regime_classification,
        test_m_sensitivity,
        test_n_plots,
        test_o_sensitivity_table,
    ):
        f()

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {_CHECKS}  ERRORS: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.8.2 observational validation PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.8.2 observational validation FAILED")
        sys.exit(1)