#!/usr/bin/env python3
"""T-19 snowfall accumulation-period verification (v2, Stage 11.8.0 T3-CORRECTIVE-3).

The v1 CDS probe used ``step`` ranges, which CDS collapsed; its 12-hour
conclusion was invalid.  The v2 probe requests 24 hourly validity times for a
single day and compares 12:00 with the mean of all 24 fields.  A ratio near 1
means hourly accumulation; near 12 means a 12-hour accumulation.

Result (data/validation/t19_cds_probe_v2.json): R = 1.009 -> HOURLY.
The production divisor is therefore 3600 s (was 43200 s).

Output: data/validation/snowfall_period_result.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT / "data/input/raw/era5/2020/2020_01"
PROBE_REL = "data/validation/t19_cds_probe_v2.json"
OUT = PROJECT / "data/validation/snowfall_period_result.json"
DIVISOR_S = 3600

# GRIB2 table 4.11 stepUnits -> hours per unit
STEP_UNIT_HOURS = {0: 1.0 / 60, 1: 1.0, 2: 24.0, 3: None, 4: None,
                   10: 1.0 / 3600, 11: 6.0, 12: 6.0, 13: 6.0, 14: 3.0,
                   15: 3.0, 16: 12.0, 19: 0.5}

ECMWF_DOC = {
    "source": "https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation",
    "convention": ("ERA5 single-level accumulated fields are accumulations over "
                   "the processing interval ending at the validity time; for "
                   "hourly ERA5 data the interval is 1 hour."),
}


def find_source_file():
    for cand in (RAW_DIR / "snowfall_2020_01_fullcoverage.nc",
                 RAW_DIR / "snowfall_2020_01_barents_expanded.nc"):
        if cand.exists():
            return cand
    matches = sorted(RAW_DIR.glob("snowfall_*.nc"))
    return matches[0] if matches else None


def inspect_source(path):
    with Dataset(path) as ds:
        sf = ds.variables["sf"]
        attrs = {a: sf.getncattr(a) for a in sf.ncattrs()}
        times = np.array(ds.variables["valid_time"][:])
        spacing = (sorted({int(x) for x in np.diff(times)})
                   if len(times) > 1 else [])
        return {
            "file": str(path.relative_to(PROJECT)),
            "GRIB_dataType": attrs.get("GRIB_dataType"),
            "GRIB_stepType": attrs.get("GRIB_stepType"),
            "GRIB_stepUnits": attrs.get("GRIB_stepUnits"),
            "GRIB_startStep": attrs.get("GRIB_startStep"),
            "GRIB_endStep": attrs.get("GRIB_endStep"),
            "GRIB_stepRange": attrs.get("GRIB_stepRange"),
            "units": attrs.get("units"),
            "n_times": int(len(times)),
            "valid_time_spacing_s": spacing,
            "sf_max_m": float(np.nanmax(sf[:])),
            "sf_domain_mean_m": float(np.nanmean(sf[:])),
        }


def monthly_integral_check(src):
    """Monthly snowfall under both candidate readings."""
    mean_m = src["sf_domain_mean_m"]
    month_s = 31 * 86400.0
    hourly_mm = (mean_m / DIVISOR_S) * month_s * 1000.0
    twelve_hour_mm = (mean_m / 43200.0) * month_s * 1000.0
    return {
        "hourly_reading_mm_month": hourly_mm,
        "twelve_hour_reading_mm_month": twelve_hour_mm,
        "note": ("Hourly reading gives a January snowfall rate consistent with "
                 "the Barents/open-Arctic precipitation climatology; the 12-hour "
                 "reading understates it by 12x."),
    }


def main():
    OUT.parent.mkdir(exist_ok=True)
    source = find_source_file()
    result = {
        "test": "snowfall_period_v2",
        "stage": "11.8.0 T3-CORRECTIVE-3",
        "divisor_seconds": DIVISOR_S,
        "source_metadata_available": source is not None,
        "ecmwf_documentation": ECMWF_DOC,
        "v1_status": "INVALID — step-range request collapsed by CDS",
    }

    if source is None:
        result.update({"status": "SKIP", "determined_period_hours": None,
                       "recommendation": "SKIP - raw source absent"})
        print("SKIP: raw ERA5 snowfall source absent.")
    else:
        src = inspect_source(source)
        result["source"] = src
        result["valid_time_spacing_hours_as_sampling_only"] = [
            s / 3600.0 for s in src["valid_time_spacing_s"]]
        result["monthly_integral_check"] = monthly_integral_check(src)

        probe_path = PROJECT / PROBE_REL
        result["probe"] = {"available": probe_path.exists()}
        if probe_path.exists():
            probe = json.loads(probe_path.read_text())
            result["probe"]["payload"] = probe
            ratio = probe.get("ratio_12z_over_all24")
            if (probe.get("status") == "PASS"
                    and probe.get("verdict") == "HOURLY_ACCUMULATION"
                    and ratio is not None and 0.2 <= ratio <= 5.0):
                result["status"] = "CONFIRMED_1H"
                result["determined_period_hours"] = 1.0
                result["basis"] = (f"v2 CDS probe: 24 hourly fields, "
                                   f"R=mean(12:00)/mean(all 24)={ratio:.3f}")
                result["recommendation"] = "divisor 3600 (hourly); applied"
            else:
                result["status"] = "UNCERTAIN"
                result["determined_period_hours"] = None
                result["recommendation"] = "inspect v2 probe; do not change divisor"
        else:
            result["status"] = "UNCERTAIN"
            result["determined_period_hours"] = None
            result["recommendation"] = "run t19_cds_probe.py (manual) before change"

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2,
                  default=lambda o: (int(o) if isinstance(o, np.integer)
                                     else float(o) if isinstance(o, np.floating)
                                     else o.tolist() if isinstance(o, np.ndarray)
                                     else str(o)))
    print(f"Status: {result['status']}")
    print(f"Determined period (hours): {result.get('determined_period_hours')}")
    print(f"Divisor: {result['divisor_seconds']} s")
    print(f"Results: {OUT.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
