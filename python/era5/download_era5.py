"""Download ERA5 reanalysis data using the CDS API.

Usage examples
--------------
Full month (defaults):

    python python/era5/download_era5.py

    python python/era5/download_era5.py --year 2020 --month 1

Custom area / time step:

    python python/era5/download_era5.py --year 2020 --month 1 \
        --area 90 -180 65 180 --time 00:00 06:00 12:00 18:00 \
        --output data/input/raw/era5/era5_2020_01.nc

Notes
-----
- Uses the Copernicus CDS API (cdsapi). Credentials are read by cdsapi from
  ~/.cdsapirc (NOT stored in the repository, never commit secrets).
- Output is a raw ERA5 NetCDF in native units (u10/v10 [m s-1], t2m [K],
  msl [Pa]). The Fortran model reads this file and performs its own
  interpolation onto the model grid.
- Raw data are stored under data/input/raw/era5/ and are NOT committed to Git.
"""

import argparse
import calendar
import pathlib

import cdsapi

DATASET = "reanalysis-era5-single-levels"

VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "mean_sea_level_pressure",
]

# Default spatial area [north, west, south, east]: Arctic strip 65-90 N.
DEFAULT_AREA = [90, -180, 65, 180]

# Default temporal resolution (matches the historically validated request).
DEFAULT_TIMES = ["00:00", "06:00", "12:00", "18:00"]


def build_request(year, month, area, times):
    """Construct the CDS request dict (preserves the validated structure)."""
    ndays = calendar.monthrange(year, month)[1]
    return {
        "product_type": ["reanalysis"],
        "variable": VARIABLES,
        "year": [f"{year}"],
        "month": [f"{month:02d}"],
        "day": [f"{d:02d}" for d in range(1, ndays + 1)],
        "time": times,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": area,
    }


def default_output(year, month):
    """Default raw output path data/input/raw/era5/era5_YYYY_MM.nc."""
    return (
        pathlib.Path("data")
        / "input"
        / "raw"
        / "era5"
        / f"era5_{year:04d}_{month:02d}.nc"
    )


def main():
    """Download ERA5 single-level fields from the Copernicus CDS archive."""
    parser = argparse.ArgumentParser(
        description="Download ERA5 single-level fields (u10, v10, t2m, msl) "
        "from the Copernicus CDS archive."
    )
    parser.add_argument("--year", type=int, default=2020, help="Year (default: 2020)")
    parser.add_argument("--month", type=int, default=1, help="Month 1-12 (default: 1)")
    parser.add_argument(
        "--area",
        type=float,
        nargs=4,
        default=DEFAULT_AREA,
        metavar=("NORTH", "WEST", "SOUTH", "EAST"),
        help="Spatial area, default: full Arctic strip [90, -180, 65, 180]",
    )
    parser.add_argument(
        "--time",
        nargs="+",
        default=DEFAULT_TIMES,
        help="Hourly slices, default: 6-hourly 00/06/12/18",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output .nc path (default: data/input/raw/era5/era5_YYYY_MM.nc)",
    )
    args = parser.parse_args()

    out = (
        args.output
        if args.output is not None
        else default_output(args.year, args.month)
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    request = build_request(args.year, args.month, list(args.area), list(args.time))
    print("Dataset :", DATASET)
    print("Request :", request)
    print("Output  :", out)

    client = cdsapi.Client()
    client.retrieve(DATASET, request).download(str(out))
    print("Download finished:", out)


if __name__ == "__main__":
    main()
