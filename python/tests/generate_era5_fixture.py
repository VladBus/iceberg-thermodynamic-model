#!/usr/bin/env python3
"""Generate a minimal synthetic ERA5-like NetCDF fixture for CI.

Stage 11.7E.3.2 — CI fixture.

Why this exists
---------------
The ERA5 contract test (`test_stage11_7e3_era5_contract.py`) verifies the
*real* merged ERA5 product at
`data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc`.
That file lives under `data/` and is gitignored, so a clean CI clone has no
ERA5 product and the test SKIPs. This fixture gives CI a small, valid,
deterministic ERA5-like file so the FULL structural contract is exercised on
every run.

The fixture is NOT a substitute for real-data verification: when the real
product exists the test uses it. The fixture only covers the contract shape
(dimensions, variables, attrs, monotonic coords, time axis, fill values) and
known synthetic values.

Dimensions / values (deliberately tiny but structurally valid)
--------------------------------------------------------------
    valid_time = 4      (2020-04-01 00:00 .. 18:00, 6-hourly)
    latitude   = 5      (70.00 .. 69.00, decreasing, 0.25 deg)
    longitude  = 10     (0.00 .. 2.25, increasing, 0.25 deg)

Variables (all float32, `_FillValue = NaN`):
    u10, v10 [m s-1], t2m, d2m [K], msl [Pa], tcc [1], sf [m s-1]

Snowfall is built from a known hourly accumulation so the conversion
protection in the test has an exact expected value:

    sf_rate = 0.00432 m / 3600 s = 1.2e-6 m s-1

Known expected values are stored as global attributes (`fixture_*`) so the
test does not have to duplicate magic numbers.

Usage
-----
    conda run -n iceberg-thermodynamic-model python python/tests/generate_era5_fixture.py

The generated file is committed to Git:
    python/tests/fixtures/era5_synthetic.nc
"""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "fixtures"
FIXTURE_PATH = FIXTURE_DIR / "era5_synthetic.nc"

# --- Fixed dimensions -------------------------------------------------------
NTIME = 4
NLAT = 5
NLON = 10

# --- Coordinate axes --------------------------------------------------------
LAT_FIRST = 70.0
LAT_LAST = 69.0
LAT_STEP = -0.25

LON_FIRST = 0.0
LON_LAST = 2.25
LON_STEP = 0.25

TIME_START = datetime(2020, 4, 1, 0, 0, 0)
TIME_INTERVAL_S = 21600  # 6 hours

# --- Snowfall conversion (must match python/era5/merge_snowfall.py) ---------
SNOW_ACCUM_M = 0.00432          # 4.32 mm water equivalent per hour
SNOW_ACCUM_PERIOD_S = 3600      # hourly accumulation (T-19 v2)
SNOW_RATE = SNOW_ACCUM_M / SNOW_ACCUM_PERIOD_S  # 1.2e-6 m/s

EPOCH = datetime(1970, 1, 1, 0, 0, 0)


def _create_var(ds, name, units, long_name, data):
    var = ds.createVariable(name, "f4", ("valid_time", "latitude", "longitude"),
                            fill_value=np.float32(np.nan))
    var.units = units
    var.long_name = long_name
    var[:] = data.astype(np.float32)
    return var


def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    lat = np.array([LAT_FIRST + LAT_STEP * i for i in range(NLAT)], dtype="f8")
    lon = np.array([LON_FIRST + LON_STEP * i for i in range(NLON)], dtype="f8")
    time_s = np.array(
        [(TIME_START + timedelta(seconds=TIME_INTERVAL_S * i) - EPOCH).total_seconds()
         for i in range(NTIME)],
        dtype="i8",
    )

    with Dataset(FIXTURE_PATH, "w", format="NETCDF4") as ds:
        ds.createDimension("valid_time", NTIME)
        ds.createDimension("latitude", NLAT)
        ds.createDimension("longitude", NLON)

        tv = ds.createVariable("valid_time", "i8", ("valid_time",))
        tv.units = "seconds since 1970-01-01"
        tv.calendar = "proleptic_gregorian"
        tv[:] = time_s

        la = ds.createVariable("latitude", "f8", ("latitude",))
        la.units = "degrees_north"
        la[:] = lat

        lo = ds.createVariable("longitude", "f8", ("longitude",))
        lo.units = "degrees_east"
        lo[:] = lon

        # Deterministic 3-D fields; ranges satisfy the real-data sanity checks.
        shape = (NTIME, NLAT, NLON)
        ti = np.arange(NTIME, dtype="f4")[:, None, None]
        la_i = np.arange(NLAT, dtype="f4")[None, :, None]
        lo_i = np.arange(NLON, dtype="f4")[None, None, :]

        _create_var(ds, "u10", "m s-1", "10 metre U wind component",
                    5.0 + 0.1 * ti + 0.01 * la_i)
        _create_var(ds, "v10", "m s-1", "10 metre V wind component",
                    -2.0 + 0.05 * ti + 0.01 * lo_i)
        _create_var(ds, "t2m", "K", "2 metre temperature",
                    270.0 + 0.5 * ti + np.zeros(shape, dtype="f4"))
        _create_var(ds, "d2m", "K", "2 metre dewpoint temperature",
                    265.0 + 0.5 * ti + np.zeros(shape, dtype="f4"))
        _create_var(ds, "msl", "Pa", "Mean sea level pressure",
                    101000.0 + 10.0 * ti + np.zeros(shape, dtype="f4"))
        _create_var(ds, "tcc", "1", "Total cloud cover",
                    0.5 + np.zeros(shape, dtype="f4"))
        _create_var(ds, "sf", "m s-1", "Snowfall rate",
                    SNOW_RATE + np.zeros(shape, dtype="f4"))

        # Known expected values for test assertions (no magic numbers in test)
        ds.fixture_description = "Stage 11.7E.3.2 minimal synthetic ERA5 fixture"
        ds.fixture_expected_ntime = NTIME
        ds.fixture_expected_nlat = NLAT
        ds.fixture_expected_nlon = NLON
        ds.fixture_lat_first = LAT_FIRST
        ds.fixture_lat_last = LAT_LAST
        ds.fixture_lat_step = LAT_STEP
        ds.fixture_lon_first = LON_FIRST
        ds.fixture_lon_last = LON_LAST
        ds.fixture_lon_step = LON_STEP
        ds.fixture_time_start = TIME_START.strftime("%Y-%m-%d %H:%M:%S")
        ds.fixture_time_end = (TIME_START + timedelta(
            seconds=TIME_INTERVAL_S * (NTIME - 1))).strftime("%Y-%m-%d %H:%M:%S")
        ds.fixture_time_interval_s = TIME_INTERVAL_S
        ds.fixture_snowfall_accumulation_m = SNOW_ACCUM_M
        ds.fixture_snowfall_accumulation_period_s = SNOW_ACCUM_PERIOD_S
        ds.fixture_snowfall_accumulation_units = "m of water equivalent"
        ds.fixture_sf_rate = SNOW_RATE
        ds.fixture_sf_nonzero_count = NTIME * NLAT * NLON

    print(f"Wrote {FIXTURE_PATH}")
    print(f"  dims: valid_time={NTIME}, latitude={NLAT}, longitude={NLON}")
    print(f"  time: {TIME_START} .. {TIME_START + timedelta(seconds=TIME_INTERVAL_S*(NTIME-1))}")
    print(f"  sf rate: {SNOW_RATE:.3e} m/s "
          f"({SNOW_ACCUM_M} m / {SNOW_ACCUM_PERIOD_S} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
