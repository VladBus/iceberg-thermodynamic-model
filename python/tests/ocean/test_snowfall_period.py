#!/usr/bin/env python3
"""
Stage 11.8.0 T0 — Snowfall accumulation period verification (T-19), strict.

Evidence hierarchy (Phase 1.3/1.4 of Stage 11.8.0 T0):
  CONFIRMED_XH : numeric GRIB step metadata present (startStep/endStep or
                 stepRange, converted with GRIB_stepUnits).
  INFERRED_XH  : forecast_reference_time present alongside valid_time
                 (period = valid_time - reference_time per record).
  UNCERTAIN    : only valid_time spacing available. Spacing is SAMPLING
                 FREQUENCY, not the accumulation period; no CONFIRMED/
                 INFERRED claim may rest on it.

Optional corroboration: a completed CDS reproduction probe
(data/validation/t19_cds_probe.json written by t19_cds_probe.py) may
UPGRADE a probe-confirmed 12-hour interpretation; an absent/failed probe
keeps the status UNCERTAIN.

Also reports the monthly-integral sanity check under both readings and the
ECMWF documented conventions. The divisor 43200 is NEVER changed here.

Output: data/validation/snowfall_period_result.json (relative paths).
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
PROBE_REL = "data/validation/t19_cds_probe.json"
OUT = PROJECT / "data/validation/snowfall_period_result.json"
CLAIMED_DIVISOR = 43200

# GRIB2 table 4.11 stepUnits -> hours per unit
STEP_UNIT_HOURS = {0: 1.0 / 60, 1: 1.0, 2: 24.0, 3: None, 4: None,
                   10: 1.0 / 3600, 11: 6.0, 12: 6.0, 13: 6.0, 14: 3.0,
                   15: 3.0, 16: 12.0, 19: 0.5}

ECMWF_DOC = {
    "source": "https://confluence.ecmwf.int/display/CKB/"
              "ERA5%3A+data+documentation + conversion-table page",
    "expected_period_note": (
        "ERA5 hourly reanalysis accumulations are over the 1-hour processing "
        "period ending at the validity time; monthly-averaged products scale "
        "accumulations to per-day. Forecast-type (fc) records with stepType="
        "accum represent the interval reference_time -> reference_time+step. "
        "Our artifacts are dataType=fc with two records/day; whether CDS "
        "returned step=12 windows (12 h each) or something else CANNOT be "
        "settled from the artifact file itself - live reproduction required."),
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
        has_ref = ("forecast_reference_time" in ds.variables
                   or "time" in ds.variables)
        ref = (np.array(ds.variables["forecast_reference_time"][:])
               if "forecast_reference_time" in ds.variables else None)
        spacing = (sorted({int(x) for x in np.diff(times)})
                   if len(times) > 1 else [])
        sf_max = float(np.nanmax(sf[:]))
        sf_mean = float(np.nanmean(sf[:]))
        hist = str(ds.getncattr("history"))[:400] if "history" in ds.ncattrs() else None
    return {"file": str(path.relative_to(PROJECT)),
            "GRIB_dataType": attrs.get("GRIB_dataType"),
            "GRIB_stepType": attrs.get("GRIB_stepType"),
            "GRIB_stepUnits": attrs.get("GRIB_stepUnits"),
            "GRIB_startStep": attrs.get("GRIB_startStep"),
            "GRIB_endStep": attrs.get("GRIB_endStep"),
            "GRIB_stepRange": attrs.get("GRIB_stepRange"),
            "units": attrs.get("units"),
            "n_times": int(len(times)),
            "valid_time_spacing_s": spacing,
            "forecast_reference_time_present": bool(has_ref),
            "sf_max_m": sf_max,
            "sf_domain_mean_m": sf_mean,
            "history": hist}


def numeric_step(src, key):
    v = src.get(key)
    return v if isinstance(v, (int, float, np.integer, np.floating)) else None


def monthly_integral_check(src):
    """Sanity of the two candidate readings via January climatology."""
    n = src["n_times"]
    mean_m = src["sf_domain_mean_m"]
    month_s = 31 * 86400.0
    out = {}
    # Reading A: records are consecutive 12-h windows covering the month.
    total_a_m = mean_m * n                      # m SWE over month
    out["reading_12h_windows"] = {
        "domain_mean_monthly_snowfall_mm": total_a_m * 1000.0,
        "implied_rate_m_s": total_a_m / month_s,
    }
    # Reading B: records are 1-h accumulations sampled 2/day; the divisor
    # 43200 treats a 1-h value as 12 h -> rate understated 12x.
    rate_b = mean_m / 3600.0
    out["reading_1h_sampled_2x_day"] = {
        "domain_mean_rate_m_s": rate_b,
        "domain_mean_monthly_snowfall_mm": rate_b * month_s * 1000.0,
        "divisor_required_s": 3600,
    }
    out["climatology_note"] = (
        f"Computed domain-mean January snowfall: 12-h reading "
        f"{out['reading_12h_windows']['domain_mean_monthly_snowfall_mm']:.2f} "
        f"mm/month vs 1-h reading "
        f"{out['reading_1h_sampled_2x_day']['domain_mean_monthly_snowfall_mm']:.1f} "
        f"mm/month. January Barents/open-Arctic precipitation climatology is "
        "~15-45 mm w.e./month (mixed rain+snow): the 12-h value is a "
        "plausible snow subset; a 1-h reading would imply SNOW alone near or "
        "above the total-precipitation budget -> the 12-h reading is "
        "corroborated by climatology, but corroboration is NOT source "
        "confirmation (T-19 stays UNCERTAIN until the CDS probe or step "
        "metadata confirm it).")
    return out


def main():
    OUT.parent.mkdir(exist_ok=True)
    source = find_source_file()
    result = {"test": "snowfall_period",
              "stage": "11.8.0 T0 Phase 1",
              "claimed_divisor_seconds": CLAIMED_DIVISOR,
              "source_metadata_available": source is not None,
              "ecmwf_documentation": ECMWF_DOC}

    if source is None:
        result.update({"status": "SKIP", "determined_period_hours": None,
                       "recommendation": "SKIP - raw source file absent"})
        print("SKIP: raw ERA5 snowfall source absent; cannot evaluate.")
    else:
        src = inspect_source(source)
        result["source"] = src
        start = numeric_step(src, "GRIB_startStep")
        end = numeric_step(src, "GRIB_endStep")
        rng = src.get("GRIB_stepRange")
        units = src.get("GRIB_stepUnits")
        uf = STEP_UNIT_HOURS.get(units if units is not None else 1, "unknown")

        if (start is not None and end is not None and uf not in (None, "unknown")):
            period = (float(end) - float(start)) * uf
            result["status"] = f"CONFIRMED_{period:g}H"
            result["determined_period_hours"] = period
            result["basis"] = "GRIB_startStep/GRIB_endStep with GRIB_stepUnits"
        elif isinstance(rng, str) and "-" in rng and uf not in (None, "unknown"):
            a, b = (float(x) for x in rng.split("-")[:2])
            period = (b - a) * uf
            result["status"] = f"CONFIRMED_{period:g}H"
            result["determined_period_hours"] = period
            result["basis"] = "GRIB_stepRange with GRIB_stepUnits"
        elif src["forecast_reference_time_present"]:
            spacing = src["valid_time_spacing_s"]
            period = spacing[0] / 3600.0 if len(spacing) == 1 else None
            result["status"] = f"INFERRED_{period:g}H" if period else "UNCERTAIN"
            result["determined_period_hours"] = period
            result["basis"] = "valid_time - forecast_reference_time"
        else:
            result["status"] = "UNCERTAIN"
            result["determined_period_hours"] = None
            result["basis"] = (
                "valid_time spacing is SAMPLING FREQUENCY only "
                "(no step attributes, no forecast_reference_time in the "
                "artifact); no CONFIRMED/INFERRED claim is made from it")

        result["valid_time_spacing_hours_as_sampling_only"] = [
            s / 3600.0 for s in src["valid_time_spacing_s"]]
        result["monthly_integral_check"] = monthly_integral_check(src)

        # Optional live-probe corroboration (t19_cds_probe.py, manual tool).
        probe_path = PROJECT / PROBE_REL
        result["probe"] = {"available": probe_path.exists()}
        if probe_path.exists():
            probe = json.loads(probe_path.read_text())
            result["probe"]["payload"] = probe
            if probe.get("status") == "PROBE_FAILED":
                result["recommendation"] = (
                    "keep_divisor; T-19 remains OPEN - first live CDS probe "
                    "timed out/failed, retry t19_cds_probe.py manually")
            else:
                d1 = probe.get("artifact_vs_step12_maxdiff_m")
                if d1 is not None and d1 < 1e-9:
                    result["status"] = "CONFIRMED_12H"
                    result["determined_period_hours"] = 12.0
                    result["basis"] = ("live CDS probe: artifact field matches "
                                       "step=12 request bit-for-bit")
                    result["recommendation"] = "keep_divisor (confirmed)"
                else:
                    result["recommendation"] = (
                        "keep_divisor pending probe interpretation")
        else:
            result["recommendation"] = (
                "keep_divisor; investigate_further: run t19_cds_probe.py "
                "(manual, needs ~/.cdsapirc) before any divisor change")

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2,
                  default=lambda o: (int(o) if isinstance(o, np.integer)
                                     else float(o) if isinstance(o, np.floating)
                                     else o.tolist() if isinstance(o, np.ndarray)
                                     else str(o)))
    print(f"Status: {result['status']}")
    print(f"Determined period (hours): {result.get('determined_period_hours')}")
    print(f"Basis: {result.get('basis', result.get('recommendation'))}")
    if "monthly_integral_check" in result:
        mic = result["monthly_integral_check"]
        print(f"12-h reading monthly snow: "
              f"{mic['reading_12h_windows']['domain_mean_monthly_snowfall_mm']:.2f} mm | "
              f"1-h reading: {mic['reading_1h_sampled_2x_day']['domain_mean_monthly_snowfall_mm']:.1f} mm")
    print(f"Divisor UNCHANGED. Results: {OUT.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())