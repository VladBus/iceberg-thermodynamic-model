"""Check the contents of a downloaded ERA5 NetCDF file.

Usage
-----
    python python/era5/check_era5.py
    python python/era5/check_era5.py data/input/raw/era5/2020/2020_01/era5_2020_01.nc
    python python/era5/check_era5.py --domain barents <file>
    python python/era5/check_era5.py --area 90 10 70 70 <file>

Performs basic validation: dimensions, coordinates, variable presence, units,
fill values (NaN/Inf), physical min/max ranges, and (Stage 6.2) checks the file
spatial coverage against a named domain / requested CDS area.
"""

import argparse
import datetime as _dt
import pathlib
import sys

import numpy as np
import xarray as xr

# Reuse the named domain table from download_era5 (must stay in sync).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from download_era5 import DOMAINS, DEFAULT_DOMAIN  # noqa: E402

DEFAULT_FILE = "data/input/raw/era5/2020/2020_01/era5_2020_01.nc"

VARIABLES = {
    "u10": ("m s-1", -200.0, 200.0),
    "v10": ("m s-1", -200.0, 200.0),
    "t2m": ("K", 150.0, 340.0),
    "msl": ("Pa", 50000.0, 110000.0),
    "d2m": ("K", 150.0, 340.0),
    "tcc": ("1", 0.0, 1.0),
    "sf": ("m", 0.0, 5.0),  # ERA5 raw snowfall: m of water equivalent (accumulated)
    "era5_snowfall_rate": ("m s-1", 0.0, 1e-4),  # Merged file: snowfall rate in m/s
}


def check_domain(lat, lon, domain, area):
    """Check file spatial coverage against a named domain / requested area.

    The ERA5 download uses CDS area [north, west, south, east]. A valid file
    must cover the whole requested box: all four boundaries inside/on the file
    latitude/longitude ranges (with tolerance for grid discretization).
    """
    tol = 0.5  # degrees, grid discretization tolerance
    if area is None and domain is not None:
        area = DOMAINS[domain]["area"]
    if area is None:
        return []
    north, west, south, east = area
    problems = []
    lat_min, lat_max = float(np.min(lat)), float(np.max(lat))
    lon_min, lon_max = float(np.min(lon)), float(np.max(lon))
    if north - tol > lat_max or south + tol < lat_min:
        problems.append(
            f"domain lat [{south:.1f}..{north:.1f}] outside file lat [{lat_min:.1f}..{lat_max:.1f}]"
        )
    # Longitude may wrap across the dateline (west > east in -180..180 space),
    # e.g. [90, 10, 70, 70] for the Barents domain (west=10 < east=70) does NOT
    # wrap; only custom areas like [90, 170, 65, -170] would.
    if west > east:
        # wrap case: file must reach east (near +180 side) and west (near -180 side)
        if not (lon_max >= east - tol and lon_min <= west + tol):
            problems.append(
                f"domain lon [{west:.1f}..{east:.1f}] (wrap) not covered by file "
                f"lon [{lon_min:.1f}..{lon_max:.1f}]"
            )
    else:
        if (west - tol > lon_min) or (east + tol < lon_max):
            problems.append(
                f"domain lon [{west:.1f}..{east:.1f}] outside file lon [{lon_min:.1f}..{lon_max:.1f}]"
            )
    return problems


# pylint: disable=too-many-locals
def main():
    """Inspect a downloaded ERA5 NetCDF file and validate its contents."""
    parser = argparse.ArgumentParser(
        description="Inspect a downloaded ERA5 NetCDF file."
    )
    parser.add_argument(
        "file", nargs="?", default=DEFAULT_FILE, help="Path to ERA5 .nc file"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        choices=list(DOMAINS.keys()),
        help=f"Named domain to verify coverage against (default: {DEFAULT_DOMAIN}). "
        "Overridden by --area.",
    )
    parser.add_argument(
        "--area",
        type=float,
        nargs=4,
        default=None,
        metavar=("NORTH", "WEST", "SOUTH", "EAST"),
        help="Requested CDS area to verify coverage against (overrides --domain).",
    )
    args = parser.parse_args()

    path = pathlib.Path(args.file)
    if not path.exists():
        print(f"ERROR: {path} not found.")
        return 1

    ds = xr.open_dataset(path)

    print(f"\n=== FILE: {path} ===")
    print("=== DIMENSIONS ===")
    for name, size in ds.sizes.items():
        print(f"  {name}: {size}")

    print("\n=== TIME AXIS ===")
    times = ds["valid_time"].values if "valid_time" in ds.coords else None
    if times is not None:
        print(f"  start : {times[0]}")
        print(f"  end   : {times[-1]}")
        n = len(times)
        if n > 1:
            dt = _dt.datetime.fromisoformat(str(times[1])) - _dt.datetime.fromisoformat(
                str(times[0])
            )
            print(f"  step  : {dt}")
            print(f"  count : {n}")

    print("\n=== SPATIAL COVERAGE ===")
    lat = ds["latitude"].values
    lon = ds["longitude"].values
    lat_min, lat_max = float(np.min(lat)), float(np.max(lat))
    lon_min, lon_max = float(np.min(lon)), float(np.max(lon))
    print(f"  latitude : {lat_min:.2f} .. {lat_max:.2f} (decreasing={lat[0] > lat[-1]})")
    print(f"  longitude: {lon_min:.2f} .. {lon_max:.2f}")

    if args.area is not None:
        domain_name = "custom"
        domain_desc = f"area {list(args.area)}"
    elif args.domain is not None:
        domain_name = args.domain
        domain_desc = DOMAINS[args.domain]["description"]
    else:
        domain_name = DEFAULT_DOMAIN
        domain_desc = DOMAINS[DEFAULT_DOMAIN]["description"]
    domain_problems = check_domain(lat, lon, domain_name, args.area)
    print(
        f"  expected domain: {domain_name} [{domain_desc}] "
        f"(CDS area {DOMAINS.get(domain_name, {}).get('area', args.area)})"
    )
    if domain_problems:
        print("  DOMAIN MISMATCH:")
        for p in domain_problems:
            print(f"    - {p}")
    else:
        print("  domain coverage: OK")

    print("\n=== VARIABLES ===")
    n_errors = 0
    for name, var in ds.data_vars.items():
        if name not in VARIABLES:
            print(f"  {name}: shape={var.shape} dtype={var.dtype} (unchecked)")
            continue
        units, vmin, vmax = VARIABLES[name]
        data = var.values
        finite = np.isfinite(data).all()
        print(f"\n  {name}: shape={var.shape} dims={var.dims} dtype={var.dtype}")
        print(f"    units: {var.attrs.get('units', 'n/a')} (expected {units})")
        print(f"    finite (no NaN/Inf): {finite}")
        if data.size and finite:
            print(
                f"    min={np.nanmin(data):.4f} max={np.nanmax(data):.4f} "
                f"mean={np.nanmean(data):.4f}"
            )
            if np.nanmin(data) < vmin or np.nanmax(data) > vmax:
                print(f"    WARNING: outside expected physical range [{vmin}, {vmax}]")
                n_errors += 1

    ds.close()
    if n_errors or domain_problems:
        print(f"\nWARNING: {n_errors} variable(s) outside expected ranges; "
              f"{len(domain_problems)} domain coverage issue(s).")
        return 1
    print("\nOK: ERA5 file passed validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
