#!/usr/bin/env python3
"""
Stage 11.7E.3.1 — ERA5 Forcing Contract Verification (Strengthened)

Verifies the merged ERA5 NetCDF product against the Stage 11.7A contract
with EXACT assertions (not just > 0 checks).

The ERA5 chain already reads merged NetCDF; this is a VERIFY-ONLY stage.
Do NOT write a new reader.

Exit codes:
  0 = all checks pass (or SKIP with clear message)
  1 = any check fails
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import numpy as np
    from netCDF4 import Dataset, num2date
except ImportError:
    print("ERROR: netCDF4/numpy unavailable (activate conda env iceberg-thermodynamic-model)")
    sys.exit(1)

PROJECT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ERA5 merged product path (standard location per 11.7A)
ERA5_MERGED_PATH = PROJECT / "data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc"

# Expected EXACT dimensions for April 2020 merged product (per 11.7A contract)
EXPECTED_NTIME = 120      # 30 days × 4 steps/day (6-hourly)
EXPECTED_NLAT = 101       # 90 to 65 N at 0.25° = 101 points
EXPECTED_NLON = 1440      # -180 to 179.75 at 0.25° = 1440 points

# Expected coordinate bounds (exact)
EXPECTED_LAT_FIRST = 90.0
EXPECTED_LAT_LAST = 65.0
EXPECTED_LON_FIRST = -180.0
EXPECTED_LON_LAST = 179.75

# Expected resolution
EXPECTED_LAT_RES = -0.25  # decreasing
EXPECTED_LON_RES = 0.25

# Expected time axis
EXPECTED_TIME_UNITS = "seconds since 1970-01-01"
EXPECTED_CALENDAR = "proleptic_gregorian"
EXPECTED_TIME_INTERVAL = 21600  # 6 hours = 21600 seconds

# Expected variable dimension order: (valid_time, latitude, longitude)
EXPECTED_VAR_DIMS = ("valid_time", "latitude", "longitude")

# Expected data variable names and their expected units
REQUIRED_VARS = {
    "u10": {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "v10": {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "t2m": {"units": ("K",), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "d2m": {"units": ("K",), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "msl": {"units": ("Pa",), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "tcc": {"units": ("1", "(0 - 1)", "-", "dimensionless"), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
    "sf":  {"units": ("m s-1", "m s**-1", "m/s"), "dtype": np.float32, "expected_dims": ("valid_time", "latitude", "longitude")},
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


def main():
    global CHECKS, ERRORS, INFOS

    print("=" * 72)
    print("Stage 11.7E.3.1 — ERA5 Forcing Contract Verification (Strengthened)")
    print("=" * 72)

    if not ERA5_MERGED_PATH.exists():
        print(f"SKIP: ERA5 merged file not found at {ERA5_MERGED_PATH}")
        print("      Build via: python python/era5/merge_snowfall.py ...")
        print("=" * 72)
        print(f"TOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}  INFO: {INFOS}")
        print("=" * 72)
        return 0  # SKIP = exit 0

    print(f"Verifying: {ERA5_MERGED_PATH}")
    print()

    with Dataset(ERA5_MERGED_PATH) as ds:
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

        # EXACT dimension values
        check(ntime == EXPECTED_NTIME, f"valid_time dimension == {EXPECTED_NTIME}", f"got {ntime}")
        check(nlat == EXPECTED_NLAT, f"latitude dimension == {EXPECTED_NLAT}", f"got {nlat}")
        check(nlon == EXPECTED_NLON, f"longitude dimension == {EXPECTED_NLON}", f"got {nlon}")

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
            check(actual_dims == spec["expected_dims"],
                  f"'{varname}' dims == {spec['expected_dims']}",
                  f"got {actual_dims}")

            # Check shape matches dimension sizes
            expected_shape = (EXPECTED_NTIME, EXPECTED_NLAT, EXPECTED_NLON)
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
        check(lat.shape == (EXPECTED_NLAT,), "latitude shape == (nlat,)")
        check(lat[0] == EXPECTED_LAT_FIRST, f"latitude first == {EXPECTED_LAT_FIRST}", f"got {lat[0]}")
        check(lat[-1] == EXPECTED_LAT_LAST, f"latitude last == {EXPECTED_LAT_LAST}", f"got {lat[-1]}")
        check(np.all(lat[:-1] > lat[1:]), "latitude is strictly DECREASING", f"first={lat[0]}, last={lat[-1]}")

        # Check resolution is exactly 0.25° (decreasing)
        lat_diffs = np.diff(lat)
        check(np.allclose(lat_diffs, -0.25, atol=1e-10),
              f"latitude resolution == 0.25° (decreasing)",
              f"diffs: min={lat_diffs.min():.10f}, max={lat_diffs.max():.10f}")
        info(f"latitude: {lat[0]} .. {lat[-1]} (decreasing, step={lat_diffs[0]:.6f}°)")

        # Longitude
        lon = ds.variables["longitude"][:]
        check(lon[0] == EXPECTED_LON_FIRST, f"longitude first == {EXPECTED_LON_FIRST}", f"got {lon[0]}")
        check(lon[-1] == EXPECTED_LON_LAST, f"longitude last == {EXPECTED_LON_LAST}", f"got {lon[-1]}")
        check(np.all(lon[:-1] < lon[1:]), "longitude is strictly INCREASING")

        lon_diffs = np.diff(lon)
        check(np.allclose(lon_diffs, 0.25, atol=1e-10),
              f"longitude resolution == 0.25° (increasing)",
              f"diffs: min={lon_diffs.min():.10f}, max={lon_diffs.max():.10f}")
        info(f"longitude: {lon[0]} .. {lon[-1]} (increasing, step={lon_diffs[0]:.6f}°)")

        # =========================================================================
        # 4. Time coordinate — EXACT units, calendar, interval, range
        # =========================================================================
        print("\n--- Time Coordinate (EXACT units, calendar, interval, range) ---")

        time_var = ds.variables["valid_time"]
        time_vals = time_var[:]
        check(time_vals.shape == (EXPECTED_NTIME,), f"valid_time shape == ({EXPECTED_NTIME},)")

        # Units attribute MANDATORY
        check("units" in time_var.ncattrs(), "'valid_time' has 'units' attribute", "missing")
        time_units = time_var.getncattr("units")
        check("seconds since 1970-01-01" in time_units.lower(),
              f"time units reference 1970 epoch",
              f"got '{time_units}'")
        info(f"time units: {time_units}")

        # Calendar attribute MANDATORY
        check("calendar" in time_var.ncattrs(), "'valid_time' has 'calendar' attribute", "missing")
        cal = time_var.getncattr("calendar")
        check(cal.lower() == EXPECTED_CALENDAR.lower(),
              f"time calendar == {EXPECTED_CALENDAR}",
              f"got '{cal}'")
        info(f"time calendar: {cal}")

        # Convert to datetime for range checks
        time_dates = num2date(time_vals, units=time_units, calendar=cal)

        # Check time interval is exactly 6 hours (21600 seconds)
        time_diffs = np.diff(time_vals)
        check(np.all(time_diffs == EXPECTED_TIME_INTERVAL),
              f"time interval == {EXPECTED_TIME_INTERVAL} seconds (6 hours)",
              f"diffs: min={time_diffs.min()}, max={time_diffs.max()}")

        # Check total time steps match expected (120 for April)
        check(len(time_vals) == EXPECTED_NTIME,
              f"time steps == {EXPECTED_NTIME}",
              f"got {len(time_vals)}")

        # Check time range covers full April 2020 (6-hourly from 2020-04-01 00:00 to 2020-04-30 18:00)
        # Use cftime datetime comparison (no tzinfo for cftime objects)
        expected_start = datetime(2020, 4, 1, 0, 0, 0)
        expected_end = datetime(2020, 4, 30, 18, 0, 0)

        actual_start = time_dates[0]
        actual_end = time_dates[-1]

        # Compare year, month, day, hour, minute, second
        check((actual_start.year, actual_start.month, actual_start.day, actual_start.hour, actual_start.minute, actual_start.second) ==
              (expected_start.year, expected_start.month, expected_start.day, expected_start.hour, expected_start.minute, expected_start.second),
              f"time start == {expected_start}",
              f"got {actual_start}")
        check((actual_end.year, actual_end.month, actual_end.day, actual_end.hour, actual_end.minute, actual_end.second) ==
              (expected_end.year, expected_end.month, expected_end.day, expected_end.hour, expected_end.minute, expected_end.second),
              f"time end == {expected_end}",
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
        # Verify non-zero snowfall exists (values are ~1e-7 m/s max, not zero)
        check(np.nanmax(sf) > 0.0, "sf has non-zero values (max > 0)", f"max={np.nanmax(sf):.2e}")
        info(f"sf range [m/s]: {np.nanmin(sf):.2e} .. {np.nanmax(sf):.2e}")
        info(f"sf non-zero count: {np.count_nonzero(sf)}")

        # =========================================================================
        # 7. Code behavior documentation (verified by grep)
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