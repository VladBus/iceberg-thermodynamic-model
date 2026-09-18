#!/usr/bin/env python3
"""
Stage 10.18B — independent regression tests for the observational-constraint
layer (`python/validation/observational_constraint.py`) and the curated
observational dataset.

Every expected value is derived analytically (or verbatim from the cited
source), never by re-running the implementation under test:
- legacy prediction:  m = C_LATERAL*DeltaT  (C_LATERAL = 1e-6 m/(s K))
- bulk velocity-dependent at U=0 -> 0 (forced-convection guard)
- Bigg1997 at U=0 -> 0; analytic value at (U,dT,L)
- uncertainty propagation: z = (m_model - m_obs)/sigma
- geometry: volume-loss ratio submerged/full-height = 2*rho_i/rho_w
- unit conversions are algebraic (86400)
- dataset rule: numeric fields are either parsed values or NA; no value is
  fabricated (no mean-substitution anywhere)

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_observational_constraint.py
"""

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "python" / "validation"))

import numpy as np

from python.validation.observational_constraint import (
    NA,
    comparison_table,
    effective_c_lateral,
    implied_volume_loss,
    leave_one_source_out,
    load_cases,
    metrics,
    predict,
)
from python.validation.observational_constraint import ObservationalCase as OC
from python.validation.lateral_melt import (
    BIGG_K_OCEAN,
    C_LATERAL,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    legacy_lateral_melt_rate,
    m_day_to_m_s,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
)
from python.validation.basal_melt import RHO_ICE, RHO_WATER

DATASET = (REPO / "data" / "validation" / "observations"
           / "iceberg_lateral_melt_observations.csv")

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


def approx(a, b, rel=1e-9):
    if a == b:
        return True
    return abs(a - b) <= rel * max(abs(a), abs(b))


def _case(**kw):
    base = dict(case_id="X", source_id="S", year=2020, region="r",
                environment="LAB", delta_t_K=3.0, u_rel_m_s=0.1,
                L_m=100.0, D_m=88.5, melt_obs_m_day=0.2,
                melt_unc_m_day=NA, directness="DIRECT",
                melt_definition="side", measurement_method="m",
                averaging_period="d", wave_influenced="FALSE",
                comparability="DIRECTLY_COMPARABLE", notes="")
    base.update(kw)
    return OC(**base)


# ---------------------------------------------------------------------------
# 1. Dataset schema
# ---------------------------------------------------------------------------
def test_dataset_schema():
    print("Dataset schema")
    check(DATASET.exists(), "curated dataset file present")
    with open(DATASET, newline="", encoding="utf-8") as f:
        header = next(r for r in f if not r.lstrip().startswith("#"))
    required = ["case_id", "source_id", "delta_T_K", "u_rel_m_s", "L_m", "D_m",
                "melt_obs_m_day", "melt_unc_m_day", "directness",
                "melt_definition", "wave_influenced", "comparability"]
    for col in required:
        check(col in header, f"dataset has column '{col}'")
    rows = [r for r in open(DATASET, encoding="utf-8")
            if not r.lstrip().startswith("#")][1:]
    n = sum(1 for r in rows if r.strip())
    check(n >= 10, f"dataset has {n} case rows (>= 10)")
    # every case_id unique
    ids = [r.split(",")[0] for r in rows if r.strip()]
    check(len(ids) == len(set(ids)), "case_id values unique")


# ---------------------------------------------------------------------------
# 2. Missing-value handling
# ---------------------------------------------------------------------------
def test_missing_values():
    print("Missing-value handling")
    c = _case(delta_t_K=NA, u_rel_m_s=NA)
    check(math.isnan(predict(c, "LEGACY_FULL_HEIGHT")),
          "missing delta_T -> legacy prediction NA")
    c2 = _case(delta_t_K=3.0, u_rel_m_s=NA)
    check(math.isnan(predict(c2, "BULK_FORCED")),
          "missing U -> velocity-dependent prediction NA")
    check(math.isnan(predict(c2, "BIGG1997")), "missing U -> Bigg prediction NA")
    check(not math.isnan(predict(c2, "LEGACY_FULL_HEIGHT")),
          "legacy computable without U")
    c3 = _case(u_rel_m_s=NA)
    check(math.isnan(predict(c3, "FITZMAURICE_PLUME")),
          "missing U -> plume prediction NA")


# ---------------------------------------------------------------------------
# 3. Unit conversions
# ---------------------------------------------------------------------------
def test_units():
    print("Unit conversions")
    check(approx(m_s_to_m_day(1.0), 86400.0), "m/s -> m/day factor 86400")
    check(approx(m_day_to_m_s(86400.0), 1.0), "round-trip")
    check(approx(m_day_to_m_s(0.0434) * 86400.0, 0.0434), "RH80 value round-trip")
    # temperature/velocity parse
    from python.validation.observational_constraint import _f
    check(math.isnan(_f("NA")), "_f: 'NA' -> NaN")
    check(math.isnan(_f("")), "_f: '' -> NaN")
    check(approx(_f("3.5"), 3.5), "_f: numeric parse")


# ---------------------------------------------------------------------------
# 4. Uncertainty propagation
# ---------------------------------------------------------------------------
def test_uncertainty():
    print("Uncertainty propagation")
    c = _case(melt_obs_m_day=0.2, melt_unc_m_day=0.05, delta_t_K=3.0)
    pred = predict(c, "LEGACY_FULL_HEIGHT")
    rows = comparison_table([c])
    r = [x for x in rows if x["model_name"] == "LEGACY_FULL_HEIGHT"][0]
    z = (pred - 0.2) / 0.05
    check(approx(r["normalized_error"], z), "z = (m_model - m_obs)/sigma")
    check(r["within_uncertainty"] == (abs(pred - 0.2) <= 0.05),
          "within_uncertainty flag consistent")
    c2 = _case(melt_unc_m_day=NA)
    rows2 = comparison_table([c2])
    r2 = [x for x in rows2 if x["model_name"] == "LEGACY_FULL_HEIGHT"][0]
    check(math.isnan(r2["normalized_error"]), "no sigma -> normalized error NA")


# ---------------------------------------------------------------------------
# 5. Model prediction analytic values
# ---------------------------------------------------------------------------
def test_predictions_analytic():
    print("Model predictions (analytic)")
    dT, U, L, D = 3.0, 0.1, 100.0, 88.5
    c = _case(delta_t_K=dT, u_rel_m_s=U, L_m=L, D_m=D)
    # legacy
    check(approx(predict(c, "LEGACY_FULL_HEIGHT"),
                 m_s_to_m_day(legacy_lateral_melt_rate(dT))),
          "legacy = C*DeltaT*86400")
    check(approx(predict(c, "LEGACY_FULL_HEIGHT"),
                 C_LATERAL * dT * 86400.0), "legacy numeric")
    # legacy submerged same rate
    check(approx(predict(c, "LEGACY_SUBMERGED"),
                 predict(c, "LEGACY_FULL_HEIGHT")),
          "LEGACY_SUBMERGED rate identical to LEGACY_FULL_HEIGHT")
    # bulk
    check(approx(predict(c, "BULK_FORCED"),
                 m_s_to_m_day(bulk_velocity_dependent_side_melt(dT, U, D))),
          "bulk analytic")
    # bigg
    check(approx(predict(c, "BIGG1997"),
                 m_s_to_m_day(bigg1997_forced_convection_melt_rate(U, dT, L))),
          "bigg analytic")
    # bigg+buoy
    check(approx(predict(c, "BIGG_PLUS_BUOY"),
                 m_s_to_m_day(bigg1997_forced_convection_melt_rate(U, dT, L)
                              + neshyba_josberger_buoyant_melt_rate(dT))),
          "bigg+buoy analytic")
    # zero-velocity boundaries
    c0 = _case(delta_t_K=dT, u_rel_m_s=0.0, L_m=L, D_m=D)
    check(predict(c0, "BULK_FORCED") == 0.0, "bulk: 0 at U=0")
    check(predict(c0, "BIGG1997") == 0.0, "bigg: 0 at U=0")
    check(predict(c0, "BIGG_PLUS_BUOY") > 0.0, "bigg+buoy: >0 at U=0 (buoyant term)")
    check(predict(c0, "FITZMAURICE_PLUME") > 0.0,
          "plume: >0 at U=0 (attached-plume branch)")
    # zero delta_T
    cz = _case(delta_t_K=0.0, u_rel_m_s=U, L_m=L, D_m=D)
    for m in ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED", "BULK_FORCED",
              "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"):
        check(predict(cz, m) == 0.0, f"{m}: 0 at DeltaT=0")
    # non-negative / finite
    for m in ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED", "BULK_FORCED",
              "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"):
        v = predict(c, m)
        check(not math.isnan(v) and v >= 0.0 and math.isfinite(v),
              f"{m}: finite & non-negative")


# ---------------------------------------------------------------------------
# 6. Geometry transformation (volume-loss conventions)
# ---------------------------------------------------------------------------
def test_geometry():
    print("Geometry transformation")
    c = _case(L_m=100.0, D_m=88.5, melt_obs_m_day=0.26)
    iv = implied_volume_loss(c, 0.26)
    ratio = iv["submerged_m3"] / iv["full_height_m3"]
    check(approx(ratio, 2.0 * RHO_ICE / RHO_WATER, 1e-12),
          f"volume-loss ratio submerged/full-height = 2*rho_i/rho_w = {ratio:.4f}")
    check(iv["full_height_m3"] > 0 and iv["submerged_m3"] > 0,
          "implied volume loss positive")
    cn = _case(L_m=NA, D_m=NA)
    ivn = implied_volume_loss(cn, 0.26)
    check(math.isnan(ivn["full_height_m3"]), "missing geometry -> volume loss NA")


# ---------------------------------------------------------------------------
# 7. Filtering by source quality / directness
# ---------------------------------------------------------------------------
def test_filtering():
    print("Filtering and direct/indirect separation")
    cases = [
        _case(case_id="D1", directness="DIRECT", delta_t_K=3.0, melt_obs_m_day=0.2),
        _case(case_id="I1", directness="INDIRECT", delta_t_K=3.0, melt_obs_m_day=0.2),
        _case(case_id="M1", directness="MODEL_DERIVED", delta_t_K=3.0, melt_obs_m_day=0.2),
        _case(case_id="U1", directness="UNVERIFIED", delta_t_K=3.0, melt_obs_m_day=0.2),
    ]
    rows = comparison_table(cases)
    m = metrics(rows, "LEGACY_FULL_HEIGHT")
    check(m["N"] == 2, f"metrics excludes MODEL_DERIVED/UNVERIFIED (N={m['N']})")
    # deterministic
    m2 = metrics(rows, "LEGACY_FULL_HEIGHT")
    check(m["RMSE"] == m2["RMSE"], "metrics deterministic")


# ---------------------------------------------------------------------------
# 8. Synthetic cases with pre-computed analytic expectations
# ---------------------------------------------------------------------------
def test_synthetic_cases():
    print("Synthetic cases (analytic expectations, independent)")
    # case: DeltaT=2 K, U=0.01 m/s, D=100 m (laminar: Re=5.5e5? no:
    # Re = 0.01*100/1.82e-6 = 5.49e5 > 5e5 -> turbulent! choose U=0.005 for
    # laminar, Re=2.75e5)
    dT, U, L, D = 2.0, 0.005, 100.0, 100.0
    # legacy: 1e-6*2*86400 = 0.1728 m/day
    check(approx(predict(_case(delta_t_K=dT, u_rel_m_s=U, L_m=L, D_m=D),
                         "LEGACY_FULL_HEIGHT"), 0.1728),
          "synthetic legacy: C*2*86400 = 0.1728 m/day")
    # bulk laminar: gamma_T = 0.664 Re^0.5 Pr^(1/3) k / D
    pr = 13.8
    nu = 1.82e-6
    k = 0.56
    re = U * D / nu
    gam = 0.664 * math.sqrt(re) * pr ** (1 / 3) * k / D
    m_bulk = gam * dT / (RHO_ICE * 334000.0)
    check(approx(predict(_case(delta_t_K=dT, u_rel_m_s=U, L_m=L, D_m=D),
                         "BULK_FORCED"), m_s_to_m_day(m_bulk), 1e-6),
          f"synthetic bulk laminar: {m_s_to_m_day(m_bulk):.6f} m/day")
    # Bigg: K*U^0.8*dT/L^0.2 with K=0.58 (m/day)
    m_bigg = BIGG_K_OCEAN * U ** 0.8 * dT / L ** 0.2
    check(approx(predict(_case(delta_t_K=dT, u_rel_m_s=U, L_m=L, D_m=D),
                         "BIGG1997"), m_bigg, 1e-12),
          f"synthetic Bigg: {m_bigg:.6f} m/day")


# ---------------------------------------------------------------------------
# 9. C_eff distribution sanity (no fabrication)
# ---------------------------------------------------------------------------
def test_c_eff():
    print("Effective C_LATERAL")
    cases = [
        _case(case_id="A", delta_t_K=2.0, melt_obs_m_day=0.2, wave_influenced="FALSE"),
        _case(case_id="B", delta_t_K=4.0, melt_obs_m_day=0.4, wave_influenced="FALSE"),
        _case(case_id="C", delta_t_K=8.0, melt_obs_m_day=0.8, wave_influenced="FALSE"),
    ]
    dist = effective_c_lateral(cases)
    check(dist["N"] == 3, "C_eff uses applicable cases only")
    # each C_eff = m_obs/delta_T/86400 exactly
    check(approx(dist["median"], (0.2 / 2.0) / 86400.0), "C_eff median = m/dT/86400")
    check(dist["min"] <= dist["median"] <= dist["max"], "C_eff ordering")


def main():
    test_dataset_schema()
    test_missing_values()
    test_units()
    test_uncertainty()
    test_predictions_analytic()
    test_geometry()
    test_filtering()
    test_synthetic_cases()
    test_c_eff()
    print(f"\nobs-constraint: {_CHECKS} checks, {_ERRORS} failures")
    if _ERRORS:
        raise SystemExit(1)
    print("All observational-constraint checks passed.")


if __name__ == "__main__":
    main()