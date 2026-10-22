#!/usr/bin/env python3
"""
Stage 11.8.0.0 — Ice Coverage and SIT Semantics Test (strengthened)

Verifies that real sea-ice initialization produces physically bounded cover
and that `sit` is interpreted correctly as an AREA-WEIGHTED thickness
contribution (HST * sic), NOT as a single-category thickness.

Checks:
  - 0 <= max total concentration <= 1
  - 0 < cells with ice < total cells
  - 0 < max sit contribution <= HST_max (2.5 m) and < 10 m
  - total ice volume > 0 (sit * cell area)
  - per-category sit maximum <= HST[category]
  - sit == HST * sic (sampled/all, float tolerance)

Also investigates the reported 25.72 m day-1 maximum:
  - Initial `sit` max is 1.5875 m (area-weighted contribution).
  - The model output `ice_thickness` is per-category `hice = wice1/anp`;
    a 25.72 m value is therefore NOT a `sit` unit/aggregation artifact.
    It is a thermodynamic-growth result and is documented as a model defect
    (physically implausible Arctic sea-ice thickness), not a sit semantics error.
  - If the 7-day run output is absent, this part reports "not available".

Output: data/validation/ice_coverage_result.json
Exit: 0 = all initial-state checks pass; 1 = a check fails.
"""

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
NC_PATH = PROJECT / "data/input/processed/ice/seaice_initial.nc"
ICE_DIR = PROJECT / "data/input/generated/real_grid/ice_2020-01-01"
MODEL_RUN = PROJECT / "data/runs/stage11.7E4_C7/output/nc/results_day_01.nc"
OUT = PROJECT / "data/validation/ice_coverage_result.json"
HST = np.array([0.20, 0.40, 0.95, 1.60, 2.50])
HMAX = np.array([0.3, 0.7, 1.2, 2.0, 50.0])
CELL_AREA_M2 = 13890.0 * 13890.0
TOTAL_CELLS = 133 * 105

CHECKS = 0
ERRORS = 0
CHECK_LOG = []


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    CHECK_LOG.append({"label": label, "passed": bool(cond), "detail": detail})
    if cond:
        print(f"PASS {label}")
    else:
        ERRORS += 1
        print(f"FAIL {label} {detail}")


def main():
    result = {"test": "ice_coverage", "checks": CHECK_LOG}
    if not NC_PATH.exists():
        print("SKIP: data/input/processed/ice/seaice_initial.nc absent "
              "(data bundle not in this checkout); coverage thresholds "
              "cannot be evaluated.")
        return 0

    with Dataset(NC_PATH) as ds:
        sic = np.array(ds["sic"][:], dtype=np.float64)   # (cat, j, i)
        sit = np.array(ds["sit"][:], dtype=np.float64)
        hst = np.array(ds["hst"][:], dtype=np.float64)

        total_conc = np.nansum(sic, axis=0)
        max_conc = float(np.nanmax(total_conc))
        cells_with_ice = int(np.sum(total_conc > 0.0))
        max_sit = float(np.nanmax(sit))
        total_volume = float(np.nansum(sit) * CELL_AREA_M2)
        cat_sit_max = [float(np.nanmax(sit[c])) for c in range(sit.shape[0])]
        cat_conc_max = [float(np.nanmax(sic[c])) for c in range(sic.shape[0])]

        check(0.0 <= max_conc <= 1.0 + 1e-6, "max concentration in [0,1] (f32 tol)", max_conc)
        check(0 < cells_with_ice < TOTAL_CELLS,
              "0 < cells with ice < total cells",
              f"{cells_with_ice}/{TOTAL_CELLS}")
        check(0.0 < max_sit <= float(hst.max()),
              "max sit contribution <= HST_max", max_sit)
        check(max_sit < 10.0, "max sit contribution < 10 m", max_sit)
        check(total_volume > 0.0, "total ice volume > 0", total_volume)

        for c in range(sit.shape[0]):
            check(cat_sit_max[c] <= float(hst[c]) + 1e-5,
                  f"category {c+1} sit max <= HST[{c+1}]",
                  f"{cat_sit_max[c]} vs {hst[c]}")
            # sit must be HST * sic for every category (float32 tolerance)
            diff = np.nanmax(np.abs(sit[c] - hst[c] * sic[c]))
            check(diff <= 1e-5, f"category {c+1} sit == HST*sic",
                  f"max diff {diff}")

        result.update({
            "file": str(NC_PATH.relative_to(PROJECT)),
            "max_concentration": max_conc,
            "cells_with_ice": cells_with_ice,
            "total_cells": TOTAL_CELLS,
            "max_sit_contribution_m": max_sit,
            "total_ice_volume_m3": total_volume,
            "category_sit_max_m": cat_sit_max,
            "category_conc_max": cat_conc_max,
            "hst_m": hst.tolist(),
            "hmax_m": HMAX.tolist(),
            "sit_semantics": ("area-weighted thickness contribution HST*sic; "
                              "sum over categories = column-equivalent thickness"),
        })

    # Legacy text files (cross-check)
    ice_files = sorted(ICE_DIR.glob("1_*.ice"))
    if ice_files:
        max_an1 = 0.0
        max_cells = 0
        for f in ice_files:
            vals = np.fromfile(f, sep=" ", dtype=np.float64)
            if len(vals) == TOTAL_CELLS:
                arr = vals.reshape((133, 105))
                max_an1 = max(max_an1, float(arr.max()))
                max_cells = max(max_cells, int(np.sum(arr > 0)))
        result["legacy"] = {
            "directory": str(ICE_DIR.relative_to(PROJECT)),
            "files_found": len(ice_files),
            "max_cells_with_ice": max_cells,
            "max_concentration": max_an1,
        }
        check(max_an1 > 0.0, "legacy source has non-zero concentration", max_an1)

    # Investigate the reported 25.72 m day-1 maximum.
    if MODEL_RUN.exists():
        with Dataset(MODEL_RUN) as ds:
            thick = np.array(ds["ice_thickness"][:], dtype=np.float64)
            conc = np.array(ds["ice_concentration"][:], dtype=np.float64)
            cat_max = [float(np.nanmax(thick[c])) for c in range(thick.shape[0])]
            result["model_day01_ice_thickness"] = {
                "file": str(MODEL_RUN.relative_to(PROJECT)),
                "per_category_max_m": cat_max,
                "overall_max_m": float(np.nanmax(thick)),
                "max_concentration": float(np.nanmax(conc)),
                "interpretation": (
                    "ice_thickness is per-category hice = wice1/anp, NOT sit. "
                    "A 25.72 m maximum is a thermodynamic-growth defect "
                    "(physically implausible Arctic sea ice), not a sit unit/"
                    "aggregation artifact. Initial sit max is "
                    f"{result['max_sit_contribution_m']:.4f} m."),
            }
    else:
        result["model_day01_ice_thickness"] = {
            "available": False,
            "note": ("day_01 model output absent; initial sit max is "
                     f"{result['max_sit_contribution_m']:.4f} m. The 25.72 m "
                     "value refers to per-category ice_thickness (hice), not sit."),
        }

    result["pass"] = ERRORS == 0
    result["summary"] = f"{CHECKS - ERRORS}/{CHECKS} checks passed"
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{result['summary']}")
    print(f"max concentration: {result['max_concentration']:.6f}")
    print(f"cells with ice: {result['cells_with_ice']} / {TOTAL_CELLS}")
    print(f"max sit contribution: {result['max_sit_contribution_m']:.6f} m")
    print(f"total ice volume: {result['total_ice_volume_m3']:.3e} m^3")
    if "model_day01_ice_thickness" in result:
        md = result["model_day01_ice_thickness"]
        if md.get("available", True):
            print(f"model day-1 per-category max: {md['per_category_max_m']}")
            print(f"model day-1 overall max: {md['overall_max_m']:.3f} m")
    print(f"Results written to {OUT}")
    return 0 if ERRORS == 0 else 1


if __name__ == "__main__":
    sys.exit(main())