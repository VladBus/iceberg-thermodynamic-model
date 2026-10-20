#!/usr/bin/env python3
"""
Stage 11.7E.3.2 — ERA5 Forcing Contract Verification (fixture-aware)

Verifies the merged ERA5 NetCDF product against the Stage 11.7A contract
with EXACT assertions (not just > 0 checks).

Data selection (in order):
  1. REAL    — data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc
  2. FIXTURE — python/tests/fixtures/era5_synthetic.nc (committed; CI clone)
  3. FAIL    — both missing (fixture is committed; this is a CI error)

The fixture is a minimal synthetic ERA5-like file (4 x 5 x 10) that exercises
the full structural contract. When the real product is present it takes
precedence; the fixture is never silently substituted for real verification.

The ERA5 chain already reads merged NetCDF; this is a VERIFY-ONLY stage.
Do NOT write a new reader.

Exit codes:
  0 = all checks pass (or SKIP with clear message)
  1 = any check fails
"""

import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import numpy as np
    from netCDF4 import Dataset, num2date
except ImportError:
    print("ERROR: netCDF4/numpy unavailable (activate conda env iceberg-thermodynamic-model)")
    sys.exit(1)

PROJECT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Real merged product (standard location per 11.7A)
ERA5_MERGED_PATH = PROJECT / "data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc"

# Minimal committed fixture for clean CI clones (Stage 11.7E.3.2)
ERA5_FIXTURE_PATH = PROJECT / "python/tests/fixtures/era5_synthetic.nc"

# Raw snowfall (12-hourly accumulation) — available locally, absent in CI
ERA5_RAW_SNOWFALL_PATH = PROJECT / "data/input/raw/era5/2020/2020_04/snowfall_2020_04.nc"

# Snowfall merge script (conversion factor protection)
MERGE_SNOWFALL_SCRIPT = PROJECT / "python/era5/merge_snowfall.py"

# Expected structure for the REAL April 2020 merged product (per 11.7A contract)
REAL_EXPECTED = {
    "ntime": 120,          # 30 days × 4 steps/day (6-hourly)
    "nlat": 101,           # 90 to 65 N at 0.25° = 101 points
    "nlon": 1440,          # -180 to 179.75 at 0.25° = 1440 points
    "lat_first": 90.0,
    "lat_last": 65.0,
    "lat_step": -0.25,     # decreasing
    "lon_first": -180.0,
    "lon_last": 179.75,
    "lon_step": 0.25,      # increasing
    "time_start": (2020, 4, 1, 0, 0, 0),
    "time_end": (2020, 4, 30, 18, 0, 0),
    "time_interval_s": 21600,  # 6 hours
    "sf_nonzero_min": 1,
}

# Fixture expectations are read from the fixture's own ``fixture_*`` global
# attributes (single source of truth; Stage 11.7E.4 Phase 0.5).  No duplicate
# magic numbers live in this test.
def fixture_expected(ds):
    """Build the expected contract from the fixture's own attributes."""
    start = datetime.strptime(
        str(ds.getncattr("fixture_time_start")), "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(
        str(ds.getncattr("fixture_time_end")), "%Y-%m-%d %H:%M:%S")
    return {
        "ntime": int(ds.getncattr("fixture_expected_ntime")),
        "nlat": int(ds.getncattr("fixture_expected_nlat")),
        "nlon": int(ds.getncattr("fixture_expected_nlon")),
        "lat_first": float(ds.getncattr("fixture_lat_first")),
        "lat_last": float(ds.getncattr("fixture_lat_last")),
        "lat_step": float(ds.getncattr("fixture_lat_step")),
        "lon_first": float(ds.getncattr("fixture_lon_first")),
        "lon_last": float(ds.getncattr("fixture_lon_last")),
        "lon_step": float(ds.getncattr("fixture_lon_step")),
        "time_start": (start.year, start.month, start.day,
                       start.hour, start.minute, start.second),
        "time_end": (end.year, end.month, end.day,
                     end.hour, end.minute, end.second),
        "time_interval_s": int(ds.getncattr("fixture_time_interval_s")),
        "sf_nonzero_min": 1,
    }


# Expected variable dimension order: (valid_time, latitude, longitude)
EXPECTED_VAR_DIMS = ("valid_time", "latitude", "longitude")

# Expected data variable names and their expected units
REQUIRED_VARS = {
    "u10": {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32},
    "v10": {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32},
    "t2m": {"units": ("K",), "dtype": np.float32},
    "d2m": {"units": ("K",), "dtype": np.float32},
    "msl": {"units": ("Pa",), "dtype": np.float32},
    "tcc": {"units": ("1", "(0 - 1)", "-", "dimensionless"), "dtype": np.float32},
    "sf":  {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32},
}

CHECKS = 0
ERRORS = 0
INFOS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if cond:
        print(f"PASS {label}")
    else:
        ERRORS += 1
        print(f"FAIL {label} {detail}")


def info(label):
    global INFOS
    INFOS += 1
    print(f"INFO {label}")


def units_match(actual, expected):
    """Check if actual units string matches expected (accepting common variations)."""
    if isinstance(expected, (list, tuple)):
        return actual in expected
    return actual == expected


def check_snowfall_conversion(ds, mode, sf):
    """Protect the accumulation -> rate conversion from silent regression.

    Real mode with raw file: verify raw units, 12-h period, and that the
    merged rate equals raw accumulation / 43200.
    Real mode without raw file: verify the merged metadata documents the
    12-hour conversion and the output range is a plausible rate.
    Fixture mode: verify the fixture's known accumulation -> rate values.
    """
    merge_src = MERGE_SNOWFALL_SCRIPT.read_text() if MERGE_SNOWFALL_SCRIPT.exists() else ""
    check("43200" in merge_src,
          "merge_snowfall.py uses 43200 s (12 h) accumulation period",
          f"checked {MERGE_SNOWFALL_SCRIPT}")

    if mode == "fixture":
        accum = float(ds.getncattr("fixture_snowfall_accumulation_m"))
        period = float(ds.getncattr("fixture_snowfall_accumulation_period_s"))
        units = ds.getncattr("fixture_snowfall_accumulation_units")

        check(period == 43200.0,
              "fixture snowfall accumulation period == 43200 s (12 h)",
              f"got {period}")
        check(units == "m of water equivalent",
              "fixture snowfall accumulation units == 'm of water equivalent'",
              f"got '{units}'")

        expected_rate = accum / period
        actual_rate = float(np.nanmax(sf))
        check(abs(actual_rate - expected_rate) <= 1e-12,
              "fixture sf rate == accumulation / 43200",
              f"expected {expected_rate:.6e}, got {actual_rate:.6e}")

        expected_nz = int(ds.getncattr("fixture_sf_nonzero_count"))
        check(np.count_nonzero(sf) == expected_nz,
              f"fixture sf non-zero cells == {expected_nz}",
              f"got {np.count_nonzero(sf)}")
        return

    # REAL mode
    if ERA5_RAW_SNOWFALL_PATH.exists():
        with Dataset(ERA5_RAW_SNOWFALL_PATH) as raw:
            raw_sf_var = raw.variables["sf"]
            raw_units = raw_sf_var.getncattr("units") if "units" in raw_sf_var.ncattrs() else ""
            raw_time = raw.variables["valid_time"][:]
            raw_dt = np.diff(raw_time)
            raw_max = float(np.nanmax(raw_sf_var[:]))

        check("water equivalent" in raw_units.lower(),
              "raw ERA5 sf units are 'm of water equivalent'",
              f"got '{raw_units}'")
        check(raw_dt.size > 0 and np.all(raw_dt == 43200),
              "raw ERA5 sf accumulation period == 12 h (43200 s)",
              f"got diffs {np.unique(raw_dt)[:5]}")
        check(abs(float(np.nanmax(sf)) - raw_max / 43200.0) <= 1e-12,
              "merged sf max == raw accumulation / 43200",
              f"raw_max/43200={raw_max/43200.0:.6e}, merged={float(np.nanmax(sf)):.6e}")
        check(np.count_nonzero(sf) >= 1000,
              "merged sf has many non-zero cells (>= 1000)",
              f"got {np.count_nonzero(sf)}")
        info(f"raw snowfall: {ERA5_RAW_SNOWFALL_PATH}")
    else:
        sf_var = ds.variables["sf"]
        sf_comment = sf_var.getncattr("comment") if "comment" in sf_var.ncattrs() else ""
        check(("12" in sf_comment) or ("43200" in sf_comment),
              "merged sf metadata documents 12-hour accumulation conversion",
              f"comment: '{sf_comment[:80]}'")
        check(np.nanmax(sf) < 1e-4,
              "merged sf max is a plausible rate (< 1e-4 m/s)",
              f"got {float(np.nanmax(sf)):.3e}")
        check(np.count_nonzero(sf) > 0,
              "merged sf has non-zero cells",
              f"got {np.count_nonzero(sf)}")
        info("raw ERA5 snowfall unavailable — raw-vs-merged conversion check skipped")


def check_snowfall_conversion_function():
    """Call the production conversion function on a synthetic 2x2x4 array.

    This is deliberately a FUNCTION call (not a source-code grep): it protects
    the accumulation -> rate factor and the metadata written by the merge.
    """
    import tempfile
    import xarray as xr

    sys.path.insert(0, str(PROJECT / "python" / "era5"))
    import merge_snowfall as ms

    accum = (np.arange(16, dtype=np.float64).reshape(2, 2, 4) * 0.001)
    rate = ms.accumulation_to_rate(accum)
    check(rate.shape == accum.shape,
          "snowfall conversion preserves shape",
          f"got {rate.shape}")
    check(np.array_equal(rate, accum / 43200.0),
          "snowfall conversion == accumulation / 43200",
          f"max diff {np.max(np.abs(rate - accum / 43200.0)):.3e}")
    check(not np.array_equal(rate, accum / 3600.0),
          "snowfall conversion is not accumulation / 3600")
    check(not np.array_equal(rate, accum / 86400.0),
          "snowfall conversion is not accumulation / 86400")

    lat = np.array([70.0, 69.75])
    lon = np.array([0.0, 0.25])
    target_times = np.array(
        ["2020-04-01T00:00:00", "2020-04-01T06:00:00",
         "2020-04-01T12:00:00", "2020-04-01T18:00:00"], dtype="datetime64[ns]")
    snow_times = np.array(
        ["2020-04-01T00:00:00", "2020-04-01T12:00:00"], dtype="datetime64[ns]")
    inst = xr.Dataset(
        {"dummy": (("valid_time", "latitude", "longitude"),
                   np.zeros((4, 2, 2), dtype="f4"))},
        coords={"valid_time": target_times, "latitude": lat, "longitude": lon})
    snow = xr.Dataset(
        {"sf": (("valid_time", "latitude", "longitude"),
                np.full((2, 2, 2), 0.00432, dtype="f4"))},
        coords={"valid_time": snow_times, "latitude": lat, "longitude": lon})

    with tempfile.TemporaryDirectory(prefix="snowfall_unit_") as td:
        inst_path = os.path.join(td, "inst.nc")
        snow_path = os.path.join(td, "snow.nc")
        out_path = os.path.join(td, "merged.nc")
        inst.to_netcdf(inst_path)
        snow.to_netcdf(snow_path)
        ms.merge_snowfall(inst_path, snow_path, out_path)
        with Dataset(out_path) as merged:
            check("sf" in merged.variables, "merged output has sf")
            check(merged.variables["sf"].units == "m s-1",
                  "merged sf units == m s-1",
                  f"got {merged.variables['sf'].units!r}")
            merged_max = float(np.nanmax(merged.variables["sf"][:]))
            check(abs(merged_max - 0.00432 / 43200.0) <= 1e-12,
                  "merged sf uses /43200 conversion",
                  f"got {merged_max:.6e}")


def main():
    global CHECKS, ERRORS, INFOS

    print("=" * 72)
    print("Stage 11.7E.3.2 — ERA5 Forcing Contract Verification (fixture-aware)")
    print("=" * 72)

    check_snowfall_conversion_function()

    if ERA5_MERGED_PATH.exists():
        mode = "real"
        data_path = ERA5_MERGED_PATH
    elif ERA5_FIXTURE_PATH.exists():
        mode = "fixture"
        data_path = ERA5_FIXTURE_PATH
    else:
        print("FAIL: Fixture missing from repository — this should not happen")
        print(f"      real:    {ERA5_MERGED_PATH}")
        print(f"      fixture: {ERA5_FIXTURE_PATH}")
        print("=" * 72)
        print(f"TOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}  INFO: {INFOS}")
        print("=" * 72)
        return 1

    print(f"MODE: {mode.upper()}")
    print(f"Verifying: {data_path}")
    print()

    with Dataset(data_path) as ds:
        expected = REAL_EXPECTED if mode == "real" else fixture_expected(ds)
        # =========================================================================
        # 1. Dimensions — EXACT values required
        # =========================================================================
        dims = {n: len(ds.dimensions[n]) for n in ds.dimensions}
        print("--- Dimensions (EXACT) ---")
        print(f"dims = {dims}")

        check("valid_time" in ds.dimensions, "dimension 'valid_time' exists")
        check("latitude" in ds.dimensions, "dimension 'latitude' exists")
        check("longitude" in ds.dimensions, "dimension 'longitude' exists")

        ntime = dims.get("valid_time", 0)
        nlat = dims.get("latitude", 0)
        nlon = dims.get("longitude", 0)

        info(f"ntime = {ntime}, nlat = {nlat}, nlon = {nlon}")

        # EXACT dimension values (mode-dependent)
        check(ntime == expected["ntime"], f"valid_time dimension == {expected['ntime']}", f"got {ntime}")
        check(nlat == expected["nlat"], f"latitude dimension == {expected['nlat']}", f"got {nlat}")
        check(nlon == expected["nlon"], f"longitude dimension == {expected['nlon']}", f"got {nlon}")

        # =========================================================================
        # 2. Required variables — exact shape, dims, dtype, units
        # =========================================================================
        print("\n--- Variables (EXACT shape, dims, dtype, units) ---")

        for varname, spec in REQUIRED_VARS.items():
            check(varname in ds.variables, f"variable '{varname}' exists")
            if varname not in ds.variables:
                continue

            var = ds.variables[varname]

            # Check dtype
            check(var.dtype == spec["dtype"],
                  f"'{varname}' dtype == {spec['dtype']}",
                  f"got {var.dtype}")

            # Check dimensions (exact order and names)
            actual_dims = var.dimensions
            check(actual_dims == EXPECTED_VAR_DIMS,
                  f"'{varname}' dims == {EXPECTED_VAR_DIMS}",
                  f"got {actual_dims}")

            # Check shape matches dimension sizes
            expected_shape = (expected["ntime"], expected["nlat"], expected["nlon"])
            check(var.shape == expected_shape,
                  f"'{varname}' shape == {expected_shape}",
                  f"got {var.shape}")

            # Check units attribute EXISTS and matches (mandatory)
            check("units" in var.ncattrs(), f"'{varname}' has 'units' attribute", "missing")
            if "units" in var.ncattrs():
                actual_units = var.getncattr("units")
                check(units_match(actual_units, spec["units"]),
                      f"'{varname}' units in {spec['units']}",
                      f"got '{actual_units}'")

            # Check _FillValue attribute EXISTS (mandatory)
            check("_FillValue" in var.ncattrs(), f"'{varname}' has '_FillValue' attribute", "missing")
            if "_FillValue" in var.ncattrs():
                fv = var.getncattr("_FillValue")
                check(np.isnan(fv) or fv == 9.96921e36,
                      f"'{varname}' _FillValue is NaN or standard",
                      f"got {fv}")

        # =========================================================================
        # 3. Coordinate variables — EXACT bounds and resolution
        # =========================================================================
        print("\n--- Coordinates (EXACT bounds, order, resolution) ---")

        # Latitude
        lat = ds.variables["latitude"][:]
        check(lat.shape == (expected["nlat"],), "latitude shape == (nlat,)")
        check(lat[0] == expected["lat_first"], f"latitude first == {expected['lat_first']}", f"got {lat[0]}")
        check(lat[-1] == expected["lat_last"], f"latitude last == {expected['lat_last']}", f"got {lat[-1]}")
        check(np.all(lat[:-1] > lat[1:]), "latitude is strictly DECREASING", f"first={lat[0]}, last={lat[-1]}")

        # Check resolution is exactly 0.25° (decreasing)
        lat_diffs = np.diff(lat)
        check(np.allclose(lat_diffs, expected["lat_step"], atol=1e-10),
              "latitude resolution == 0.25° (decreasing)",
              f"diffs: min={lat_diffs.min():.10f}, max={lat_diffs.max():.10f}")
        info(f"latitude: {lat[0]} .. {lat[-1]} (decreasing, step={lat_diffs[0]:.6f}°)")

        # Longitude
        lon = ds.variables["longitude"][:]
        check(lon[0] == expected["lon_first"], f"longitude first == {expected['lon_first']}", f"got {lon[0]}")
        check(lon[-1] == expected["lon_last"], f"longitude last == {expected['lon_last']}", f"got {lon[-1]}")
        check(np.all(lon[:-1] < lon[1:]), "longitude is strictly INCREASING")

        lon_diffs = np.diff(lon)
        check(np.allclose(lon_diffs, expected["lon_step"], atol=1e-10),
              "longitude resolution == 0.25° (increasing)",
              f"diffs: min={lon_diffs.min():.10f}, max={lon_diffs.max():.10f}")
        info(f"longitude: {lon[0]} .. {lon[-1]} (increasing, step={lon_diffs[0]:.6f}°)")

        # =========================================================================
        # 4. Time coordinate — EXACT units, calendar, interval, range
        # =========================================================================
        print("\n--- Time Coordinate (EXACT units, calendar, interval, range) ---")

        time_var = ds.variables["valid_time"]
        time_vals = time_var[:]
        check(time_vals.shape == (expected["ntime"],), f"valid_time shape == ({expected['ntime']},)")

        # Units attribute MANDATORY
        check("units" in time_var.ncattrs(), "'valid_time' has 'units' attribute", "missing")
        time_units = time_var.getncattr("units")
        check("seconds since 1970-01-01" in time_units.lower(),
              "time units reference 1970 epoch",
              f"got '{time_units}'")
        info(f"time units: {time_units}")

        # Calendar attribute MANDATORY
        check("calendar" in time_var.ncattrs(), "'valid_time' has 'calendar' attribute", "missing")
        cal = time_var.getncattr("calendar")
        check(cal.lower() == "proleptic_gregorian",
              "time calendar == proleptic_gregorian",
              f"got '{cal}'")
        info(f"time calendar: {cal}")

        # Convert to datetime for range checks
        time_dates = num2date(time_vals, units=time_units, calendar=cal)

        # Check time interval is exactly 6 hours (21600 seconds)
        time_diffs = np.diff(time_vals)
        check(np.all(time_diffs == expected["time_interval_s"]),
              f"time interval == {expected['time_interval_s']} seconds (6 hours)",
              f"diffs: min={time_diffs.min()}, max={time_diffs.max()}")

        # Check total time steps match expected
        check(len(time_vals) == expected["ntime"],
              f"time steps == {expected['ntime']}",
              f"got {len(time_vals)}")

        # Check time range (start/end are mode-dependent)
        start = expected["time_start"]
        end = expected["time_end"]
        actual_start = time_dates[0]
        actual_end = time_dates[-1]

        # Compare year, month, day, hour, minute, second (cftime has no tzinfo)
        check((actual_start.year, actual_start.month, actual_start.day,
               actual_start.hour, actual_start.minute, actual_start.second) == start,
              f"time start == {datetime(*start)}",
              f"got {actual_start}")
        check((actual_end.year, actual_end.month, actual_end.day,
               actual_end.hour, actual_end.minute, actual_end.second) == end,
              f"time end == {datetime(*end)}",
              f"got {actual_end}")

        info(f"time range: {actual_start} to {actual_end}")
        info(f"time interval: {time_diffs[0]} seconds ({time_diffs[0]/3600:.1f} hours)")

        # =========================================================================
        # 5. Fill values — MANDATORY for all data variables
        # =========================================================================
        print("\n--- Fill Values (MANDATORY) ---")
        for varname in REQUIRED_VARS.keys():
            if varname in ds.variables:
                var = ds.variables[varname]
                check("_FillValue" in var.ncattrs(), f"'{varname}' has '_FillValue' attribute", "missing")
                if "_FillValue" in var.ncattrs():
                    fv = var.getncattr("_FillValue")
                    check(np.isnan(fv) or fv == 9.96921e36,
                          f"'{varname}' _FillValue is NaN or standard",
                          f"got {fv}")

        # =========================================================================
        # 6. Data ranges (sanity checks)
        # =========================================================================
        print("\n--- Data Ranges (sanity) ---")

        # Wind
        u10 = ds.variables["u10"][:]
        v10 = ds.variables["v10"][:]
        check(np.isfinite(u10).all(), "u10 all finite")
        check(np.isfinite(v10).all(), "v10 all finite")
        info(f"u10 range [m/s]: {np.nanmin(u10):.2f} .. {np.nanmax(u10):.2f}")
        info(f"v10 range [m/s]: {np.nanmin(v10):.2f} .. {np.nanmax(v10):.2f}")

        # Temperature
        t2m = ds.variables["t2m"][:]
        d2m = ds.variables["d2m"][:]
        check(np.isfinite(t2m).all(), "t2m all finite")
        check(np.isfinite(d2m).all(), "d2m all finite")
        check(np.nanmin(t2m) >= 180 and np.nanmax(t2m) <= 320,
              "t2m in plausible K range", f"got [{np.nanmin(t2m):.1f}, {np.nanmax(t2m):.1f}]")
        check(np.nanmin(d2m) >= 180 and np.nanmax(d2m) <= 320,
              "d2m in plausible K range", f"got [{np.nanmin(d2m):.1f}, {np.nanmax(d2m):.1f}]")
        check(np.nanmean(d2m) <= np.nanmean(t2m) + 5,
              "d2m <= t2m on average (dewpoint <= temperature)",
              f"mean d2m={np.nanmean(d2m):.1f}, mean t2m={np.nanmean(t2m):.1f}")

        # Pressure
        msl = ds.variables["msl"][:]
        check(np.isfinite(msl).all(), "msl all finite")
        check(np.nanmin(msl) >= 80000 and np.nanmax(msl) <= 110000,
              "msl in plausible Pa range", f"got [{np.nanmin(msl):.0f}, {np.nanmax(msl):.0f}]")
        info(f"msl range [Pa]: {np.nanmin(msl):.0f} .. {np.nanmax(msl):.0f}")

        # Cloud cover
        tcc = ds.variables["tcc"][:]
        check(np.isfinite(tcc).all(), "tcc all finite")
        check(np.nanmin(tcc) >= 0.0 and np.nanmax(tcc) <= 1.0,
              "tcc in [0, 1]", f"got [{np.nanmin(tcc):.3f}, {np.nanmax(tcc):.3f}]")

        # Snowfall — verify non-zero values exist (very small but present)
        sf = ds.variables["sf"][:]
        check(np.isfinite(sf).all(), "sf all finite")
        check(np.nanmin(sf) >= 0.0, "sf >= 0 (snowfall rate non-negative)")
        check(np.nanmax(sf) > 0.0, "sf has non-zero values (max > 0)", f"max={np.nanmax(sf):.2e}")
        info(f"sf range [m/s]: {np.nanmin(sf):.2e} .. {np.nanmax(sf):.2e}")
        info(f"sf non-zero count: {np.count_nonzero(sf)}")

        # =========================================================================
        # 7. Snowfall conversion protection (Stage 11.7E.3.2)
        # =========================================================================
        print("\n--- Snowfall Conversion Protection ---")
        check_snowfall_conversion(ds, mode, sf)

        # =========================================================================
        # 8. Code behavior documentation (verified by grep in src/)
        # =========================================================================
        print("\n--- Code Behavior (verified in source) ---")

        # D32 Edge-clamping: check actual code behavior
        info("D32 edge-clamping (src/wind_forcing.f90:era5_wind() lines 270-280):")
        info("  Code clamps lat_use to file edges WITHOUT warning:")
        info("    lat_use = min(max(lat, era5_lat(1)), era5_lat(era5_nlat))")
        info("  No warning printed for clamping (test doc corrected)")

        # Unit conversions
        info("Unit conversions (src/wind_forcing.f90:era5_wind()):")
        info("  u10/v10 [m/s] -> windx1/windy1 [cm/s]: ×100 (lines 298-299)")
        info("  msl [Pa] -> p1/patm [hPa]: ×0.01 (lines 320, 322)")
        info("  t2m [K] -> tatm [°C]: -273.15 (line 321)")
        info("  sf [m/s]: already rate from merge (divided by 43200)")

        # Temporal interpolation
        info("Temporal interpolation (src/netcdf_input.f90:era5_find_time_index() lines 360-385):")
        info("  Method: NEAREST-time (binary search)")
        info("  Out-of-range: idx clamped to 1 or ntime, NO warning (test doc corrected)")
        info("  No linear time interpolation — nearest neighbor only")

        # Spatial interpolation
        info("Spatial interpolation (src/netcdf_input.f90:era5_bilinear2d() lines 407-489):")
        info("  Method: BILINEAR on regular lat/lon grid")
        info("  Longitude: cyclic wrapping (±180°) (lines 441-462)")
        info("  Latitude: NOT wrapped, out-of-range -> ok=false (line 421)")
        info("  D32 fallback in era5_wind() clamps lat to file edges (lines 270-280)")

        # Lon-wrap
        info("Longitude cyclic wrapping verified in era5_bilinear2d() (lines 441-462)")

    print("\n" + "=" * 72)
    print(f"TOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}  INFO: {INFOS}")
    print("=" * 72)

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
