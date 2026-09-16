#!/usr/bin/env python3
"""Stage 10.14 — analytical tests for the 10.8.2 re-scoring against the
three-equation (10.10/10.10.1) and three-equation + natural-convection (10.11)
closures with the 10.8.2 acceptance criterion.

Locks the numbers produced by ``python/validation/three_equation_scoring.py``
against independently re-derived expected values (embedded literals, not
production diagnostics). Blocks:

  A. dataset loads; comparable (u>0) and quiescent (u=0) row counts
  B. baseline bulk closure reproduces the Stage 10.8.2 metrics (regression)
  C. three-equation closure point metrics on the 4 comparable rows
  D. teq_nat == teq on the u>0 rows (forced convection dominates, Churchill n=3)
  E. quiescent rows: bulk = 0 and teq = 0 (the 10.8.2 gap persists for these)
  F. teq_nat quiescent rows: finite, in the observed band, ratio to obs
  G. Rayleigh reasoning: lab scale (L=1 m) uncapped vs iceberg scale (L=100 m)
     capped -> 77x gamma difference (explains the 10.11.3 scale-specific gap)
  H. hygiene: no NaN, deterministic, MELT_RATE_MIN guard applied

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation_scoring.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))

import observational_validation as ov  # noqa: E402
import three_equation as ten10  # noqa: E402
import three_equation_natural as ten11  # noqa: E402
import three_equation_scoring as tes  # noqa: E402

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


def ok_rel(actual: float, expected: float, label: str, tol: float = 1.0e-3,
           detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if expected == 0.0:
        rel = abs(actual)
    else:
        rel = abs(actual - expected) / abs(expected)
    if rel < tol:
        print(f"OK   {label} (rel={rel:.2e})" + (f" ({detail})" if detail else ""))
    else:
        print(f"ERROR {label}: actual={actual:.6e} expected={expected:.6e} "
              f"rel={rel:.2e}" + (f" ({detail})" if detail else ""))
        _ERRORS += 1


# ---------------------------------------------------------------------------
# A. Dataset structure
# ---------------------------------------------------------------------------
def test_a_dataset() -> None:
    rows = ov.load_observations()
    ok(len(rows) == 19, "A.1 19 curated records loaded", f"n={len(rows)}")
    comp = tes.comparable_rows(rows)
    quies = tes.quiescent_rows(rows)
    ok(len(comp) == 4, "A.2 4 closure-applicable (u>0) rows",
       f"n={len(comp)}")
    ok({r["record_id"] for r in comp} ==
       {"KW84_DUrville", "NJ80_dT2", "NJ80_dT4", "NJ80_dT8"},
       "A.3 comparable row ids are KW84 + NJ80 x3")
    ok(len(quies) == 5, "A.4 5 quiescent (u=0) rows", f"n={len(quies)}")
    ok({r["record_id"] for r in quies} ==
       {"RH_0C", "RH_2C", "RH_5C", "RH_10C", "RH_18C"},
       "A.5 quiescent row ids are RH80 lab rows")


# ---------------------------------------------------------------------------
# B. Baseline bulk regression (10.8.2 numbers must be reproduced)
# ---------------------------------------------------------------------------
def test_b_bulk_regression() -> None:
    comp = tes.comparable_rows()
    mets = tes.metrics_for_closure(comp, "bulk")
    assert mets is not None
    ok_rel(mets["rmse_m_per_day"], 0.108, "B.1 bulk RMSE == 10.8.2 (0.108)",
           5e-2, f"actual={mets['rmse_m_per_day']:.4f}")
    ok_rel(mets["mae_m_per_day"], 0.092, "B.2 bulk MAE == 10.8.2 (0.092)",
           5e-2, f"actual={mets['mae_m_per_day']:.4f}")
    ok_rel(mets["bias_m_per_day"], 0.083, "B.3 bulk bias == 10.8.2 (+0.083)",
           5e-2, f"actual={mets['bias_m_per_day']:.4f}")
    ok_rel(mets["mean_model_m_per_day"], 0.1506, "B.4 bulk mean model",
           5e-2, f"actual={mets['mean_model_m_per_day']:.4f}")
    ok_rel(mets["mean_obs_m_per_day"], 0.0677, "B.5 bulk mean obs",
           5e-2, f"actual={mets['mean_obs_m_per_day']:.4f}")


# ---------------------------------------------------------------------------
# C. Three-equation closure point metrics (independent expected values)
# ---------------------------------------------------------------------------
def test_c_teq_metrics() -> None:
    comp = tes.comparable_rows()
    # Per-row teq melt rates (m/day) recomputed independently from the
    # production 3eq constants (K_T=1.1e-3, K_S=3.1e-5, T_ice=-10, conduction).
    expect = {
        "NJ80_dT2": 0.1601,
        "NJ80_dT4": 0.3569,
        "NJ80_dT8": 0.7978,
        "KW84_DUrville": 0.0654,
    }
    for r in comp:
        got = tes.CLOSURES["teq"](r)
        ok_rel(got, expect[r["record_id"]],
               f"C.1 teq {r['record_id']}", 5e-3,
               f"got={got:.4f}")
    mets = tes.metrics_for_closure(comp, "teq")
    assert mets is not None
    ok_rel(mets["rmse_m_per_day"], 0.3662, "C.2 teq RMSE (independent)",
           5e-3, f"actual={mets['rmse_m_per_day']:.4f}")
    ok_rel(mets["bias_m_per_day"], 0.2773, "C.3 teq bias (independent)",
           5e-3, f"actual={mets['bias_m_per_day']:.4f}")
    # KW84: 3eq improves the ratio vs bulk (0.70x -> 1.09x)
    kw = next(r for r in comp if r["record_id"] == "KW84_DUrville")
    ok_rel(tes.CLOSURES["teq"](kw) / float(kw["obs_m_per_day"]), 1.09,
           "C.4 teq KW84 ratio ~1.09 (bulk was 0.70)", 2e-2,
           f"ratio={tes.CLOSURES['teq'](kw)/float(kw['obs_m_per_day']):.3f}")
    # NJ80: 3eq overestimates more than bulk (functional-form, not a fix)
    nj2 = next(r for r in comp if r["record_id"] == "NJ80_dT2")
    ok(tes.CLOSURES["teq"](nj2) / float(nj2["obs_m_per_day"]) > 5.0,
       "C.5 teq NJ80_dT2 ratio > 5 (bulk was ~5.8; not reduced by 3eq)",
       f"ratio={tes.CLOSURES['teq'](nj2)/float(nj2['obs_m_per_day']):.2f}")


# ---------------------------------------------------------------------------
# D. teq_nat == teq on the u>0 rows (forced dominates, Churchill n=3)
# ---------------------------------------------------------------------------
def test_d_teq_nat_equals_teq_u_gt_0() -> None:
    comp = tes.comparable_rows()
    for r in comp:
        m_teq = tes.CLOSURES["teq"](r)
        m_nat = tes.CLOSURES["teq_nat"](r)
        if m_teq == 0.0:
            ok(m_nat == 0.0, f"D.1 {r['record_id']} both zero")
            continue
        rel = abs(m_nat - m_teq) / m_teq
        ok(rel < 1e-5,
           f"D.1 {r['record_id']} teq_nat == teq (rel={rel:.2e})",
           f"teq={m_teq:.6f} teq_nat={m_nat:.6f}")
    m_teq = tes.metrics_for_closure(comp, "teq")
    m_nat = tes.metrics_for_closure(comp, "teq_nat")
    assert m_teq is not None and m_nat is not None
    ok_rel(m_nat["rmse_m_per_day"], m_teq["rmse_m_per_day"],
           "D.2 teq_nat RMSE == teq RMSE", 1e-6)


# ---------------------------------------------------------------------------
# E. Quiescent rows: bulk = 0, teq = 0 (the 10.8.2 gap persists for these)
# ---------------------------------------------------------------------------
def test_e_quiescent_gap_bulk_teq() -> None:
    quies = tes.quiescent_rows()
    for r in quies:
        ok(tes.CLOSURES["bulk"](r) == 0.0,
           f"E.1 bulk {r['record_id']} = 0 (gap)",
           f"m={tes.CLOSURES['bulk'](r):.2e}")
        ok(tes.CLOSURES["teq"](r) == 0.0,
           f"E.2 teq {r['record_id']} = 0 (3eq has no natural branch)",
           f"m={tes.CLOSURES['teq'](r):.2e}")


# ---------------------------------------------------------------------------
# F. teq_nat quiescent rows: finite, in band, ratio to obs
# ---------------------------------------------------------------------------
def test_f_teq_nat_quiescent() -> None:
    quies = tes.quiescent_rows()
    expect = {          # independent expected values (m/day)
        "RH_0C": 0.0603,
        "RH_2C": 0.1405,
        "RH_5C": 0.2721,
        "RH_10C": 0.5044,
        "RH_18C": 0.8859,
    }
    for r in quies:
        got = tes.CLOSURES["teq_nat"](r)
        ok(got > 0.0, f"F.1 teq_nat {r['record_id']} finite (>0)",
           f"m={got:.4f}")
        ok_rel(got, expect[r["record_id"]],
               f"F.2 teq_nat {r['record_id']} independent value", 5e-3,
               f"got={got:.4f}")
        ok(tes.in_band(got), f"F.3 teq_nat {r['record_id']} in band",
           f"m={got:.4f}")
        ratio = got / float(r["obs_m_per_day"])
        ok(0.5 <= ratio <= 2.0,
           f"F.4 teq_nat {r['record_id']} ratio to obs in [0.5, 2.0]",
           f"ratio={ratio:.2f}")
    # band membership
    ok(sum(1 for r in quies if tes.in_band(tes.CLOSURES["teq_nat"](r))) == 5,
       "F.5 teq_nat 5/5 quiescent rows in the observed band 0.01-1 m/day")
    ok(sum(1 for r in quies if tes.in_band(tes.CLOSURES["bulk"](r))) == 0,
       "F.6 bulk 0/5 in band (10.8.2 gap reproduced)")
    ok(sum(1 for r in quies if tes.in_band(tes.CLOSURES["teq"](r))) == 0,
       "F.7 teq 0/5 in band (3eq alone does not close the gap)")


# ---------------------------------------------------------------------------
# G. Rayleigh reasoning: lab scale uncapped vs iceberg scale capped
# ---------------------------------------------------------------------------
def test_g_ra_scale() -> None:
    alpha = (ten11.THERMAL_CONDUCTIVITY
             / (ten11.RHO_WATER * ten11.CP_SEAWATER))
    dT = 2.0 - ten10.ocean_freezing_point(35.0, 1.0)   # ~3.92 degC
    ra_1 = ((ten11.GRAVITY * 1.0**3
             / (ten11.KINEMATIC_VISCOSITY * alpha))
            * ten11.THERMAL_EXPANSION_COEFF * dT)
    ra_100 = ((ten11.GRAVITY * 100.0**3
               / (ten11.KINEMATIC_VISCOSITY * alpha))
              * ten11.THERMAL_EXPANSION_COEFF * dT)
    ok(ra_1 < ten11.RAYLEIGH_MAX,
       "G.1 lab scale (L=1 m) Ra below the 1e10 cap",
       f"Ra={ra_1:.3e}")
    ok(ra_100 > ten11.RAYLEIGH_MAX,
       "G.2 iceberg scale (L=100 m) Ra above the cap",
       f"Ra={ra_100:.3e}")
    ok(ten11._nusselt_from_raeff(ra_1) < ten11._nusselt_from_raeff(ra_100),
       "G.3 uncapped Nu (lab) < pinned Nu (iceberg)",
       f"Nu(L=1)={ten11._nusselt_from_raeff(ra_1):.2f}, "
       f"Nu(L=100)={ten11._nusselt_from_raeff(ra_100):.2f}")
    # gamma ratio ~77x: explains the scale-specific 10.11.3 gap statement
    gt_1, _ = ten11.natural_convection_transfer_coeff(2.0, 0.035, -1.92, 0.035, 1.0, 0.0)
    gt_100, _ = ten11.natural_convection_transfer_coeff(2.0, 0.035, -1.92, 0.035, 100.0, 0.0)
    ok_rel(gt_1 / gt_100, 77.0, "G.4 gamma_nat ratio ~77 (lab/iceberg)",
           1e-2, f"ratio={gt_1/gt_100:.1f}")


# ---------------------------------------------------------------------------
# H. Hygiene
# ---------------------------------------------------------------------------
def test_h_hygiene() -> None:
    rows = ov.load_observations()
    for name in ("bulk", "teq", "teq_nat"):
        for r in rows:
            v = tes.CLOSURES[name](r)
            ok(v == v and math.isfinite(v), f"H.1 {name} {r['record_id']} no NaN/Inf",
               f"v={v}")
            ok(v >= 0.0, f"H.2 {name} {r['record_id']} non-negative", f"v={v}")
    # determinism
    comp = tes.comparable_rows()
    a = tes.metrics_for_closure(comp, "teq_nat")
    b = tes.metrics_for_closure(comp, "teq_nat")
    assert a is not None and b is not None
    ok(a["rmse_m_per_day"] == b["rmse_m_per_day"],
       "H.3 teq_nat metrics deterministic")
    # guard: sub-guard melt zeroed
    ok(tes._guard(5e-13) == 0.0, "H.4 MELT_RATE_MIN guard zeroes 5e-13")
    ok(tes._guard(5e-12) > 0.0, "H.5 MELT_RATE_MIN guard keeps 5e-12")


def main() -> None:
    for fn in (test_a_dataset, test_b_bulk_regression, test_c_teq_metrics,
               test_d_teq_nat_equals_teq_u_gt_0, test_e_quiescent_gap_bulk_teq,
               test_f_teq_nat_quiescent, test_g_ra_scale, test_h_hygiene):
        fn()
    print(f"\n{'=' * 60}")
    print(f"three_equation_scoring: {_CHECKS} checks, {_ERRORS} errors")
    if _ERRORS:
        print("RESULT: FAIL")
        raise SystemExit(1)
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
