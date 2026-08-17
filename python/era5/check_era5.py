"""Check the contents of a downloaded ERA5 NetCDF file.

Usage
-----
    python python/era5/check_era5.py
    python python/era5/check_era5.py data/input/raw/era5/era5_2020_01.nc

Performs basic validation: dimensions, coordinates, variable presence, units,
fill values (NaN/Inf), and physical min/max ranges.
"""

import argparse
import datetime as _dt
import pathlib

import numpy as np
import xarray as xr

DEFAULT_FILE = "data/input/raw/era5/era5_2020_01.nc"

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


# pylint: disable=too-many-locals
def main():
    """Inspect a downloaded ERA5 NetCDF file and validate its contents."""
    parser = argparse.ArgumentParser(
        description="Inspect a downloaded ERA5 NetCDF file."
    )
    parser.add_argument(
        "file", nargs="?", default=DEFAULT_FILE, help="Path to ERA5 .nc file"
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
    print(
        f"  latitude : {lat.min():.2f} .. {lat.max():.2f} (decreasing={lat[0] > lat[-1]})"
    )
    print(f"  longitude: {lon.min():.2f} .. {lon.max():.2f}")

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
    if n_errors:
        print(f"\nWARNING: {n_errors} variable(s) outside expected ranges.")
    else:
        print("\nOK: ERA5 file passed validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
