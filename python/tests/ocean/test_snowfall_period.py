#!/usr/bin/env python3
"""
Stage 11.8.0.0 — Snowfall Accumulation Period Verification (SOURCE metadata)

Determines the ERA5 snowfall accumulation period from the SOURCE file
(GRIB attributes + source valid_time spacing), NOT from the processed
merged file's interpolated time axis.

Finding (2026-10-22):
- Source: data/input/raw/era5/2020/2020_01/snowfall_2020_01_fullcoverage.nc
- GRIB_stepType = "accum"
- Source valid_time spacing = 43200 s = 12 hours (62 times for January)
- sf units = "m of water equivalent"; max = 0.0039649 m per 12 h
=> Accumulation period = 12 h; divisor 43200 in merge_snowfall.py is CORRECT.

The processed merged file has 6-hourly time spacing because merge_snowfall.py
interpolates to the instantaneous ERA5 grid; that spacing is NOT the
accumulation period (the Stage 11.7E.4.1 finding of a "6 h mismatch" was
based on this artifact and is corrected here).

The divisor is NOT changed in this stage.

Output: data/validation/snowfall_period_result.json
"""

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT / "data" / "input" / "raw" / "era5" / "2020" / "2020_01"
PROCESSED = (
    PROJECT / "data" / "input" / "processed" / "era5" / "2020" / "2020_01"
    / "era5_2020_01_fullcoverage_merged.nc"
)
OUT = PROJECT / "data" / "validation" / "snowfall_period_result.json"
CLAIMED_DIVISOR = 43200  # seconds


def find_source_file():
    candidates = [
        RAW_DIR / "snowfall_2020_01_fullcoverage.nc",
        RAW_DIR / "snowfall_2020_01_barents_expanded.nc",
        RAW_DIR / "snowfall_2020_01.nc",
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = sorted(RAW_DIR.glob("snowfall_*.nc"))
    return matches[0] if matches else None


def read_source_metadata(path):
    with Dataset(path) as ds:
        if "sf" not in ds.variables:
            return {"error": "sf variable missing", "file": str(path)}
        sf = ds.variables["sf"]
        attrs = {a: sf.getncattr(a) for a in sf.ncattrs()}
        times = np.array(ds.variables["valid_time"][:]) if "valid_time" in ds.variables else None
        spacing = np.unique(np.diff(times)) if times is not None and len(times) > 1 else []
        result = {
            "file": str(path),
            "GRIB_stepType": attrs.get("GRIB_stepType"),
            "GRIB_stepUnits": attrs.get("GRIB_stepUnits"),
            "GRIB_startStep": attrs.get("GRIB_startStep", "NOT_PRESENT"),
            "GRIB_endStep": attrs.get("GRIB_endStep", "NOT_PRESENT"),
            "GRIB_stepRange": attrs.get("GRIB_stepRange", "NOT_PRESENT"),
            "units": attrs.get("units"),
            "GRIB_units": attrs.get("GRIB_units"),
            "n_times": int(len(times)) if times is not None else None,
            "valid_time_spacing_s": [int(x) for x in spacing],
            "sf_max_m": float(np.nanmax(sf[:])),
        }
    return result


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    source = find_source_file()
    result = {
        "test": "snowfall_period",
        "phase": "Phase 2 — source metadata verification",
        "claimed_divisor_seconds": CLAIMED_DIVISOR,
        "source_metadata_available": source is not None,
    }

    if source is None:
        result.update({
            "status": "UNCERTAIN",
            "determined_period_hours": None,
            "recommendation": "keep_divisor (source GRIB unavailable; verify with CDS request logs)",
            "error": "No raw snowfall file found under data/input/raw/era5/2020/2020_01",
        })
    else:
        src = read_source_metadata(source)
        result["source"] = src
        spacing = src.get("valid_time_spacing_s") or []
        step_type = src.get("GRIB_stepType")
        if spacing and len(spacing) == 1:
            period_h = spacing[0] / 3600.0
            result["determined_period_hours"] = period_h
            if step_type == "accum" and abs(period_h - 12.0) < 0.01:
                result["status"] = "CONFIRMED_12H"
                result["recommendation"] = "keep_divisor (43200 is correct)"
            elif step_type == "accum" and abs(period_h - 6.0) < 0.01:
                result["status"] = "CONFIRMED_6H"
                result["recommendation"] = "change_divisor_to_21600 (deferred to 11.8 T0)"
            elif step_type == "accum" and abs(period_h - 1.0) < 0.01:
                result["status"] = "CONFIRMED_1H"
                result["recommendation"] = "change_divisor_to_3600 (deferred to 11.8 T0)"
            else:
                result["status"] = "UNCERTAIN"
                result["recommendation"] = "verify with CDS request logs"
        else:
            result["status"] = "UNCERTAIN"
            result["determined_period_hours"] = None
            result["recommendation"] = "verify with CDS request logs"

    # Secondary cross-check: processed file spacing is interpolation, not accumulation.
    if PROCESSED.exists():
        with Dataset(PROCESSED) as ds:
            if "valid_time" in ds.variables:
                t = np.array(ds["valid_time"][:])
                if len(t) > 1:
                    sp = np.unique(np.diff(t))
                    result["processed_time_spacing_hours"] = [
                        float(x) / 3600.0 for x in sp
                    ]
                    result["processed_note"] = (
                        "Processed spacing reflects merge_snowfall interpolation, "
                        "NOT the source accumulation period."
                    )

    def _default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2, default=_default)

    print("=== SNOWFALL PERIOD TEST (SOURCE METADATA) ===")
    for key in ("source_metadata_available", "status", "determined_period_hours",
                "claimed_divisor_seconds", "recommendation",
                "processed_time_spacing_hours"):
        if key in result:
            print(f"{key}: {result[key]}")
    if "source" in result:
        src = result["source"]
        print(f"source file: {src['file']}")
        print(f"GRIB_stepType: {src['GRIB_stepType']}")
        print(f"valid_time_spacing_s: {src['valid_time_spacing_s']}")
        print(f"sf_max_m: {src['sf_max_m']}")
    print(f"Results written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())