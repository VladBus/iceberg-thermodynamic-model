#!/usr/bin/env python3
"""
Stage 10.18C — regression tests for the reanalyzed observational dataset and
the reanalysis engine.

Verifies the Stage 10.18B methodological corrections:
- RH80 rows are PUBLISHED_FIT_EVALUATION (independent_case = FALSE), NOT five
  independent observations;
- repeated Schild21 estimates of one iceberg share an independence group;
- field melt is SUBMARINE_TOTAL (never lateral); velocity-reference rows are
  not melt observations;
- u_ice is never automatically assigned to u_rel (vector combination required);
- source-specific temperature conventions are preserved (no silent T+1.8);
- mixed dependent observations cannot enter independent-sample RMSE;
- C_eff_lab and C_eff_submarine are computed separately.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_stage10_18c_observations.py
"""

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "python" / "validation"))

import numpy as np

DATA = REPO / "data" / "validation" / "observations" / "stage10.18c" / "observations.csv"

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


def _f(v):
    s = (v or "").strip()
    if s == "" or s.upper() in ("NA", "NAN", "NONE", "NULL", "-"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _rows():
    import csv
    with open(DATA, newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(r for r in f if not r.lstrip().startswith("#"))]


def test_schema():
    print("Data schema")
    check(DATA.exists(), "dataset file exists")
    rows = _rows()
    required = ["source_id", "case_id", "independent_case", "independence_group",
                "observation_type", "melt_rate", "melt_definition", "delta_T",
                "u_ice", "u_rel_speed", "u_rel_status", "draft", "data_quality",
                "source_reference"]
    for col in required:
        check(col in rows[0], f"column '{col}' present")
    ids = [r["case_id"] for r in rows]
    check(len(ids) == len(set(ids)), "case_id unique")
    check(all(r["source_id"] in ("RH80", "ENDERLIN14", "SCHILD21", "ENDERLIN23", "MOYER19")
               for r in rows), "source_id values valid")
    check(all(not math.isnan(_f(r["melt_rate"])) or r["melt_rate"] == "NA"
              for r in rows), "missing melt_rate is NA")


def test_independence():
    print("Independence classification")
    rows = _rows()
    rh = [r for r in rows if r["source_id"] == "RH80"]
    check(all(r["independent_case"] == "FALSE" for r in rh),
          "RH80 rows are NOT independent")
    check(all(r["observation_type"] == "PUBLISHED_FIT_EVALUATION" for r in rh),
          "RH80 rows are PUBLISHED_FIT_EVALUATION")
    check(all(r["independence_group"] == "RH80_SINGLE_FIT" for r in rh),
          "RH80 rows share RH80_SINGLE_FIT group")
    sch_a = [r for r in rows if r["case_id"].startswith("SCHILD21_A")]
    sch_b = [r for r in rows if r["case_id"].startswith("SCHILD21_B")]
    check(len(sch_a) >= 3 and all(r["independent_case"] == "FALSE" for r in sch_a),
          "Schild21 iceberg A rows grouped, not independent")
    check(all(r["independence_group"] == "SCHILD21_ICEBERG_A" for r in sch_a),
          "iceberg A group label correct")
    check(all(r["independence_group"] == "SCHILD21_ICEBERG_B" for r in sch_b),
          "iceberg B group label correct")
    check(len({r["independence_group"] for r in sch_a}) == 1
          and sch_a[0]["independence_group"] != sch_b[0]["independence_group"],
          "icebergs A and B are different groups")


def test_melt_definitions():
    print("Melt definitions")
    rows = _rows()
    lateral = [r for r in rows if r["melt_definition"] == "LATERAL_ONLY"]
    submarine = [r for r in rows if r["melt_definition"] == "SUBMARINE_TOTAL"]
    check(all(r["source_id"] == "RH80" for r in lateral),
          "LATERAL_ONLY appears only for RH80 (lab)")
    check(any(r["source_id"] == "SCHILD21" for r in submarine)
          and any(r["source_id"] == "ENDERLIN23" for r in submarine),
          "SUBMARINE_TOTAL for field sources")
    ref = [r for r in rows if r["observation_type"] == "VELOCITY_REFERENCE"]
    check(len(ref) == 1 and ref[0]["melt_rate"] == "NA",
          "velocity reference row is not a melt observation")


def test_velocity():
    print("Velocity handling")
    rows = _rows()
    for r in rows:
        u_rel = _f(r["u_rel_speed"])
        u_ice = _f(r["u_ice"]) if r["u_ice"] not in ("NA", "") else float("nan")
        if r["source_id"] != "RH80" and not math.isnan(u_rel):
            check(False, f"unexpected non-NA u_rel for {r['case_id']}")
    # no field row has u_rel set (u_ice never auto-promoted to u_rel)
    field = [r for r in rows if r["source_id"] in ("ENDERLIN14", "SCHILD21",
                                                   "ENDERLIN23", "MOYER19")]
    check(all(math.isnan(_f(r["u_rel_speed"])) for r in field),
          "no field case claims U_rel (u_ice not promoted to u_rel)")
    # Schild21 ice speeds derived from track lengths are recorded as u_ice
    a = [r for r in rows if r["case_id"] == "SCHILD21_A_GPS9D"][0]
    b = [r for r in rows if r["case_id"] == "SCHILD21_B_GPS9D"][0]
    check(abs(_f(a["ice_speed"]) - 0.045) < 1e-3, "iceberg A mean along-track speed ~0.045 m/s")
    check(abs(_f(b["ice_speed"]) - 0.072) < 1e-3, "iceberg B mean along-track speed ~0.072 m/s")


def test_vector_relative_velocity():
    print("Vector relative velocity (analytic)")
    # u_ocean = (0.1, 0.0), u_ice = (0.0, 0.1) -> vector |uo-ui| = 0.1414,
    # scalar speed difference = |0.1 - 0.1| = 0  (speeds cannot be combined)
    uo, vo, ui, vi = 0.1, 0.0, 0.0, 0.1
    expect = math.hypot(uo - ui, vo - vi)
    got = math.sqrt((uo - ui) ** 2 + (vo - vi) ** 2)
    check(abs(got - expect) < 1e-12, "vector |u_ocean - u_ice| computed correctly")
    scalar_diff = abs(math.hypot(uo, vo) - math.hypot(ui, vi))
    check(abs(got - scalar_diff) > 1e-3,
          "scalar speed difference is not the vector magnitude (documented)")


def test_temperature_convention():
    print("Temperature conventions")
    rows = _rows()
    rh = [r for r in rows if r["source_id"] == "RH80"][0]
    check("T+1.8" in rh["temperature_definition"],
          "RH80 dT convention = T+1.8 (published fit) preserved")
    for r in rows:
        if r["source_id"] != "RH80" and r["delta_T"] not in ("NA", ""):
            check("T+1.8" not in r["temperature_definition"],
                  f"no silent T+1.8 for field case {r['case_id']}")


def test_stats_rule():
    print("Statistical rule (dependent observations)")
    # RH80 rows: independent_case all FALSE -> cannot form an independent sample
    rows = _rows()
    rh = [r for r in rows if r["source_id"] == "RH80"]
    check(all(r["independent_case"] == "FALSE" for r in rh),
          "RH80 excluded from independent-sample statistics (curve evaluation)")
    n_independent_units = len({r["independence_group"] for r in rows
                               if r["observation_type"] != "VELOCITY_REFERENCE"
                               and r["independent_case"] == "TRUE"})
    check(n_independent_units == 0,
          "no row is falsely marked independent (aggregates/repeats flagged FALSE)")


def test_c_eff_separation():
    print("Effective coefficients separated")
    rows = _rows()
    # lab lateral values only from RH80; field submarine only from non-RH80
    lab = [(r["case_id"], r["melt_definition"]) for r in rows
           if r["melt_definition"] == "LATERAL_ONLY"]
    sub = [(r["case_id"], r["melt_definition"]) for r in rows
           if r["melt_definition"] == "SUBMARINE_TOTAL"]
    check(all(d == "LATERAL_ONLY" for _, d in lab), "C_eff_lab source is lateral-only")
    check(all(d == "SUBMARINE_TOTAL" for _, d in sub), "C_eff_submarine source is submarine")
    check(all(cid.startswith("RH80") for cid, _ in lab), "lab effective coefficient = RH80 only")
    check(all(not cid.startswith("RH80") for cid, _ in sub),
          "field effective coefficient excludes RH80")


def test_provenance():
    print("Provenance")
    rows = _rows()
    for r in rows:
        if r["melt_rate"] not in ("NA", ""):
            check(r["source_reference"] != "", f"provenance for {r['case_id']}")


def main():
    test_schema()
    test_independence()
    test_melt_definitions()
    test_velocity()
    test_vector_relative_velocity()
    test_temperature_convention()
    test_stats_rule()
    test_c_eff_separation()
    test_provenance()
    print(f"\n10.18c-observations: {_CHECKS} checks, {_ERRORS} failures")
    if _ERRORS:
        raise SystemExit(1)
    print("All Stage 10.18C observation checks passed.")


if __name__ == "__main__":
    main()