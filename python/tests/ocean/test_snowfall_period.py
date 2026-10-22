#!/usr/bin/env python3
"""
Stage 11.8.0.0.1 — Snowfall accumulation period: SOURCE metadata re-examination

Status hierarchy (Stage 11.8.0.0.1; supersedes the 11.8.0.0 "CONFIRMED_12H"):
  1. CONFIRMED_XH only if per-record GRIB step-range attributes
     (GRIB_startStep / GRIB_endStep / GRIB_stepRange) are present and numeric.
  2. INFERRED_XH from the strongest available structural evidence:
       GRIB_dataType='fc' + GRIB_stepType='accum' + exactly 2 records per day
       at 12-hour spacing (the only self-consistent reading: two 12-h
       windows covering the day).
  3. UNCERTAIN otherwise.
  No source file => explicit "SKIP: source metadata absent" (exit 0).

Documented uncertainty (why this is NOT confirmed):
  - The step-range attributes were stripped by the cfgrib CDS encoding
    (history records only {"stream": ["oper"], "stepType": ["accum"]}).
  - python/era5/download_era5.py requests steps 1..24 (HOURLY accumulations)
    at synoptic times 00/12 — but every delivered file contains exactly two
    12-hourly records per day. Script and artifacts DISAGREE; no request log
    survives to settle what the CDS API returned.
  - If each record were a 1-hour accumulation (ECMWF ERA5 hourly convention),
    the divisor 43200 would understate the rate by 12x; if it is a 12-hour
    window (consistent with 2/day coverage of the full day), 43200 is right.
  - Manual verification with CDS/ECMWF is REQUIRED before changing anything.

The divisor 43200 is NOT changed in this stage.

Output: data/validation/snowfall_period_result.json (relative paths only).
"""

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT / "data/input/raw/era5/2020/2020_01"
PROCESSED_REL = ("data/input/processed/era5/2020/2020_01/"
                 "era5_2020_01_fullcoverage_merged.nc")
OUT = PROJECT / "data/validation/snowfall_period_result.json"
CLAIMED_DIVISOR = 43200  # seconds (merge_snowfall.py)


def find_source_file():
    preferred = [
        RAW_DIR / "snowfall_2020_01_fullcoverage.nc",
        RAW_DIR / "snowfall_2020_01_barents_expanded.nc",
    ]
    for path in preferred:
        if path.exists():
            return path
    matches = sorted(RAW_DIR.glob("snowfall_*.nc"))
    return matches[0] if matches else None


def inspect_source(path):
    with Dataset(path) as ds:
        sf = ds.variables["sf"]
        attrs = {a: sf.getncattr(a) for a in sf.ncattrs()}
        times = np.array(ds.variables["valid_time"][:])
        spacing_s = sorted(set(int(x) for x in np.diff(times))) if len(times) > 1 else []
        sf_max = float(np.nanmax(sf[:]))
        history = str(ds.getncattr("history"))[:400] if "history" in ds.ncattrs() else None
    return {
        "file": str(path.relative_to(PROJECT)),
        "GRIB_dataType": attrs.get("GRIB_dataType"),
        "GRIB_stepType": attrs.get("GRIB_stepType"),
        "GRIB_stepUnits": attrs.get("GRIB_stepUnits"),
        "GRIB_startStep": attrs.get("GRIB_startStep", "NOT_PRESENT"),
        "GRIB_endStep": attrs.get("GRIB_endStep", "NOT_PRESENT"),
        "GRIB_stepRange": attrs.get("GRIB_stepRange", "NOT_PRESENT"),
        "units": attrs.get("units"),
        "n_times": int(len(times)),
        "valid_time_spacing_s": spacing_s,
        "sf_max_m": sf_max,
        "history": history,
    }


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    source = find_source_file()
    result = {
        "test": "snowfall_period",
        "phase": "Phase 2 — source metadata re-examination (11.8.0.0.1)",
        "claimed_divisor_seconds": CLAIMED_DIVISOR,
        "source_metadata_available": source is not None,
    }

    if source is None:
        result.update({
            "status": "SKIP",
            "determined_period_hours": None,
            "recommendation": "SKIP — raw ERA5 snowfall file not present; "
                              "cannot evaluate accumulation period",
        })
        print("SKIP: raw ERA5 snowfall source file absent "
              "(data bundle not in this checkout); period cannot be evaluated.")
    else:
        src = inspect_source(source)
        result["source"] = src

        start, end = src["GRIB_startStep"], src["GRIB_endStep"]
        rng = src["GRIB_stepRange"]
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            period_h = float(end) - float(start)
            result["status"] = f"CONFIRMED_{int(period_h)}H"
            result["determined_period_hours"] = period_h
        else:
            spacing = src["valid_time_spacing_s"]
            is_12h_layout = (src["GRIB_stepType"] == "accum"
                             and src["GRIB_dataType"] == "fc"
                             and len(spacing) == 1 and spacing[0] == 43200
                             and src["n_times"] in (56, 58, 59, 60, 61, 62))
            if is_12h_layout:
                result["status"] = "INFERRED_12H"
                result["determined_period_hours"] = 12.0
            else:
                result["status"] = "UNCERTAIN"
                result["determined_period_hours"] = None

        result["uncertainty"] = (
            "Step-range attributes (GRIB_startStep/endStep/stepRange) are NOT "
            "present: cfgrib folded the single accumulation step per record into "
            "valid_time and dropped the step coordinate. The download script "
            "requests hourly steps 1..24 at 00/12 UTC, yet the delivered files "
            "carry exactly two 12-hourly records per day — an unresolved "
            "script/data discrepancy. If records were 1-hour accumulations, the "
            "43200 divisor would understate snowfall by 12x; 2-records-per-day "
            "coverage of the full day is only self-consistent with 12-hour "
            "windows. Manual verification against CDS request logs or a fresh "
            "small CDS download is required before any divisor change."
        )
        result["recommendation"] = (
            "keep_divisor_pending_manual_verification (divisor NOT changed in "
            "this stage; flag recorded in KNOWN_ISSUES and 11.8 T0)"
        )

        # Secondary observation only — NOT used to infer the period.
        processed = PROJECT / PROCESSED_REL
        if processed.exists():
            with Dataset(processed) as ds:
                if "valid_time" in ds.variables:
                    t = np.array(ds.variables["valid_time"][:])
                    if len(t) > 1:
                        result["processed_file"] = {
                            "file": PROCESSED_REL,
                            "time_spacing_hours": sorted(
                                {float(x) / 3600.0 for x in np.diff(t)}),
                            "note": "processed spacing is merge interpolation; "
                                    "used ONLY as a cross-check, NOT for period "
                                    "inference",
                        }
        print(f"Status: {result['status']}")
        print(f"period_hours: {result['determined_period_hours']}")
        print(f"step attrs: start={src['GRIB_startStep']!r} end={src['GRIB_endStep']!r} "
              f"range={src['GRIB_stepRange']!r}")
        print(f"source: {src['file']} spacing={src['valid_time_spacing_s']}s "
              f"n={src['n_times']} sf_max={src['sf_max_m']}")

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2, default=_default)
    print(f"Results written to {OUT.relative_to(PROJECT)}")
    print("Divisor NOT changed.")
    return 0  # finding reported; failures are check violations, not this


if __name__ == "__main__":
    sys.exit(main())