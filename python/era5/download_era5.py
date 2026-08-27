"""Download ERA5 reanalysis data using the CDS API.

Usage examples
--------------
Full month (defaults, Barents research domain):

    python python/era5/download_era5.py

    python python/era5/download_era5.py --year 2020 --month 1

Historic Arctic-wide domain:

    python python/era5/download_era5.py --year 2020 --month 1 --domain arctic

Custom area / time step:

    python python/era5/download_era5.py --year 2020 --month 1 \
        --area 90 -180 65 180 --time 00:00 06:00 12:00 18:00 \
        --output data/input/raw/era5/2020/2020_01/era5_2020_01.nc

Notes
-----
- Uses the Copernicus CDS API (cdsapi). Credentials are read by cdsapi from
  ~/.cdsapirc (NOT stored in the repository, never commit secrets).
- Output is a raw ERA5 NetCDF in native units (u10/v10 [m s-1], t2m [K],
  msl [Pa]). The Fortran model reads this file and performs its own
  interpolation onto the model grid.
- Raw data are stored under data/input/raw/era5/YYYY/YYYY_MM/ (Stage 6.2
  run-based data architecture) and are NOT committed to Git.
- Named domain 'barents' (default): "Barents Sea / Svalbard / Franz Josef Land
  iceberg-source domain", CDS area [90, 10, 70, 70] (north/west/south/east).
  The model grid is NOT changed by the ERA5 domain; it remains grid_mode=TEST.
"""

import argparse
import calendar
import pathlib

import cdsapi

DATASET = "reanalysis-era5-single-levels"

# CDS API parameter names for instantaneous variables (ERA5 single-levels reanalysis)
# These are available at analysis times (00, 06, 12, 18 UTC)
INSTANTANEOUS_PARAMS = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "2m_dewpoint_temperature",
    "mean_sea_level_pressure",
    "total_cloud_cover",
]

# Snowfall is an ACCUMULATED forecast variable requiring 'step' parameter
# (forecast hours 1-24 from 00/12 UTC analyses). It cannot be combined with
# instantaneous variables in a single CDS request.
ACCUMULATED_PARAMS = [
    "snowfall",  # CDS variable 'sf', units: m of water equivalent
]

# Human-readable variable names for documentation
VARIABLES = INSTANTANEOUS_PARAMS + ACCUMULATED_PARAMS

# Named spatial domains. Each entry: CDS area [north, west, south, east] and a
# human-readable description recorded in the run manifest / documentation.
# - 'barents' (default, Stage 6.2): the Barents Sea / Svalbard / Franz Josef Land
#   iceberg-source domain covering Barents Sea, Svalbard archipelago, Franz Josef
#   Land, Novaya Zemlya and adjacent Arctic waters.
# - 'arctic': historic full Arctic strip 65-90 N used for the Q1 2020 runs.
DOMAINS = {
    "barents": {
        "area": [90, 10, 70, 70],
        "description": "Barents Sea / Svalbard / Franz Josef Land iceberg-source domain",
    },
    "arctic": {
        "area": [90, -180, 65, 180],
        "description": "Arctic-wide strip 65-90 N (historical Q1 2020)",
    },
}
DEFAULT_DOMAIN = "barents"

# Default temporal resolution (matches the historically validated request).
DEFAULT_TIMES = ["00:00", "06:00", "12:00", "18:00"]


def build_request(year, month, area, times, accumulated=False, days=None):
    """Construct the CDS request dict (preserves the validated structure).

    Args:
        days: optional iterable of day numbers (1-based, inclusive) to request.
              Defaults to the full month (backward compatible).
    """
    ndays = calendar.monthrange(year, month)[1]
    if days is None:
        days = range(1, ndays + 1)
    day_list = [f"{d:02d}" for d in days]
    if accumulated:
        # Snowfall: forecast accumulation from 00/12 UTC analyses, steps 1-24h
        return {
            "product_type": ["reanalysis"],
            "variable": ACCUMULATED_PARAMS,
            "year": [f"{year}"],
            "month": [f"{month:02d}"],
            "day": day_list,
            "time": ["00:00", "12:00"],  # Analysis times for forecasts
            "step": [str(h) for h in range(1, 25)],  # 1-24 hour forecasts
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": area,
        }
    else:
        # Instantaneous variables: analysis times (00, 06, 12, 18 UTC)
        return {
            "product_type": ["reanalysis"],
            "variable": INSTANTANEOUS_PARAMS,
            "year": [f"{year}"],
            "month": [f"{month:02d}"],
            "day": day_list,
            "time": times,
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": area,
        }


def default_output(year, month):
    """Default raw output path data/input/raw/era5/YYYY/YYYY_MM/era5_YYYY_MM.nc."""
    return (
        pathlib.Path("data")
        / "input"
        / "raw"
        / "era5"
        / f"{year:04d}"
        / f"{year:04d}_{month:02d}"
        / f"era5_{year:04d}_{month:02d}.nc"
    )


def main():
    """Download ERA5 single-level fields from the Copernicus CDS archive."""
    parser = argparse.ArgumentParser(
        description="Download ERA5 single-level fields (u10, v10, t2m, msl, d2m, tcc, snowfall) "
        "from the Copernicus CDS archive."
    )
    parser.add_argument("--year", type=int, default=2020, help="Year (default: 2020)")
    parser.add_argument("--month", type=int, default=1, help="Month 1-12 (default: 1)")
    parser.add_argument(
        "--domain",
        type=str,
        choices=list(DOMAINS.keys()),
        default=DEFAULT_DOMAIN,
        help=f"Named spatial domain (default: {DEFAULT_DOMAIN} = "
        f"{DOMAINS[DEFAULT_DOMAIN]['description']}). Overridden by --area.",
    )
    parser.add_argument(
        "--area",
        type=float,
        nargs=4,
        default=None,
        metavar=("NORTH", "WEST", "SOUTH", "EAST"),
        help="Custom spatial area [north west south east] (overrides --domain). "
        "Default follows --domain.",
    )
    parser.add_argument(
        "--time",
        nargs="+",
        default=DEFAULT_TIMES,
        help="Hourly slices for instantaneous vars, default: 6-hourly 00/06/12/18",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output .nc path (default: data/input/raw/era5/YYYY/YYYY_MM/era5_YYYY_MM.nc)",
    )
    parser.add_argument(
        "--start-day",
        type=int,
        default=1,
        help="First day of month to request (inclusive, default 1)",
    )
    parser.add_argument(
        "--end-day",
        type=int,
        default=None,
        help="Last day of month to request (inclusive, default = month length)",
    )
    parser.add_argument(
        "--include-snowfall",
        action="store_true",
        help="Also download snowfall (accumulated forecast, separate request)",
    )
    args = parser.parse_args()

    if args.area is not None:
        area = list(args.area)
        domain_desc = f"custom area {area}"
    else:
        area = list(DOMAINS[args.domain]["area"])
        domain_desc = f"{args.domain} ({DOMAINS[args.domain]['description']})"

    out = (
        args.output
        if args.output is not None
        else default_output(args.year, args.month)
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    ndays = calendar.monthrange(args.year, args.month)[1]
    end_day = args.end_day if args.end_day is not None else ndays
    if not (1 <= args.start_day <= end_day <= ndays):
        print(
            f"ERROR: invalid day range {args.start_day}..{end_day} "
            f"(month has {ndays} days)"
        )
        return 1
    days = range(args.start_day, end_day + 1)

    # Download instantaneous variables
    request = build_request(
        args.year, args.month, area, list(args.time), accumulated=False, days=days
    )
    print("Dataset :", DATASET)
    print(f"Domain  : {domain_desc}")
    print(f"Days    : {list(days)}")
    print("Request (instantaneous):", request)
    print("Output  :", out)

    client = cdsapi.Client()
    client.retrieve(DATASET, request).download(str(out))
    print("Download finished (instantaneous):", out)

    # Optionally download snowfall (accumulated, separate request)
    if args.include_snowfall:
        snow_out = out.with_name("snowfall_" + out.stem.removeprefix("era5_") + ".nc")
        snow_request = build_request(
            args.year, args.month, area, list(args.time), accumulated=True, days=days
        )
        print("\nRequest (snowfall, accumulated):", snow_request)
        print("Output  :", snow_out)
        client.retrieve(DATASET, snow_request).download(str(snow_out))
        print("Download finished (snowfall):", snow_out)
        print(
            "\nNOTE: Snowfall is in a separate file (accumulated forecast, requires 'step' parameter)."
        )
        print(
            "      It cannot be combined with instantaneous variables in a single CDS request."
        )
        print("      Use python/era5/merge_snowfall.py to merge if needed.")


if __name__ == "__main__":
    main()
