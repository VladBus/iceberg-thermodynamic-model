#!/usr/bin/env python3
"""Merge ERA5 snowfall (accumulated forecast) with instantaneous variables.

ERA5 snowfall (variable 'sf') is an accumulated forecast variable:
- Available at analysis times (00:00 and 12:00 UTC)
- Each value represents 12-hour accumulation ending at that analysis time
- Units: m of water equivalent

This script merges snowfall into the instantaneous variables NetCDF file,
interpolating to the model's 6-hourly time steps.
"""

import argparse
import pathlib
import sys

import numpy as np
import xarray as xr

from scipy import interpolate


def merge_snowfall(instantaneous_nc, snowfall_nc, output_nc):
    """Merge snowfall into instantaneous variables file.

    Args:
        instantaneous_nc: Path to ERA5 instantaneous variables (u10, v10, t2m, d2m, msl, tcc)
        snowfall_nc: Path to ERA5 snowfall (accumulated, 12-hourly at 00/12 UTC)
        output_nc: Output merged NetCDF path
    """
    print(f"Reading instantaneous variables from {instantaneous_nc}")
    ds_inst = xr.open_dataset(instantaneous_nc)

    print(f"Reading snowfall from {snowfall_nc}")
    ds_snow = xr.open_dataset(snowfall_nc)

    # Verify snowfall structure
    print(f"Snowfall shape: {ds_snow['sf'].shape}")
    print(f"Snowfall time steps: {len(ds_snow.valid_time)}")
    print(f"Snowfall time range: {ds_snow.valid_time[0].values} to {ds_snow.valid_time[-1].values}")

    # The snowfall is at 00:00 and 12:00 UTC (analysis times)
    # Each value = 12-hour accumulation ending at that analysis time
    # We need to interpolate to the instantaneous file's 6-hourly times (00, 06, 12, 18 UTC)

    # Use the instantaneous file's time axis as the target
    target_times = ds_inst.valid_time.values
    target_time_sec = np.array([np.datetime64(t, 's').astype('int64') for t in target_times])

    # Snowfall time axis
    snow_times = ds_snow.valid_time.values
    snow_time_sec = np.array([np.datetime64(t, 's').astype('int64') for t in snow_times])

    print(f"Target (instantaneous) time steps: {len(target_times)}")
    print(f"Target time range: {target_times[0]} to {target_times[-1]}")
    print(f"Snowfall time steps: {len(snow_times)}")
    print(f"Snowfall time range: {snow_times[0]} to {snow_times[-1]}")

    # The snowfall is at 00:00 and 12:00 UTC (analysis times)
    # Each value = 12-hour accumulation ending at that analysis time
    # Convert snowfall accumulations to rates [m/s]
    # Each accumulation is over 12 hours = 43200 seconds
    snow_accum = ds_snow['sf'].values  # [time, lat, lon] in m water equivalent
    snow_rate = snow_accum / 43200.0  # m/s

    # Interpolate snowfall rate to target times
    nlat, nlon = snow_accum.shape[1], snow_accum.shape[2]
    snow_rate_interp = np.zeros((len(target_times), nlat, nlon), dtype=np.float32)

    print("Interpolating snowfall rate to 6-hourly times...")
    for i in range(nlat):
        for j in range(nlon):
            # Skip land points (where snowfall is always 0)
            if np.all(snow_rate[:, i, j] == 0):
                continue
            f = interpolate.interp1d(snow_time_sec, snow_rate[:, i, j],
                                     kind='linear', bounds_error=False, fill_value=0.0)
            snow_rate_interp[:, i, j] = f(target_time_sec)

    # Create new dataset with merged variables
    # Start with instantaneous variables and add snowfall
    ds_out = ds_inst.copy()

    # Add snowfall as new variable with distinct name
    ds_out['era5_snowfall_rate'] = xr.DataArray(
        snow_rate_interp,
        dims=('valid_time', 'latitude', 'longitude'),
        coords={
            'valid_time': target_times,
            'latitude': ds_snow.latitude,
            'longitude': ds_snow.longitude,
        },
        attrs={
            'units': 'm s-1',
            'long_name': 'Snowfall rate',
            'standard_name': 'snowfall_flux',
            'comment': 'Interpolated from ERA5 12-hourly accumulated snowfall (sf) at 00/12 UTC analyses. '
                       'Original units: m water equivalent per 12 hours. Converted to m/s rate.'
        }
    )

    # Select only the variables we need (instantaneous + snowfall)
    # The model expects: u10, v10, t2m, d2m, msl, tcc, sf
    required_vars = ['u10', 'v10', 't2m', 'd2m', 'msl', 'tcc', 'era5_snowfall_rate']
    for var in list(ds_out.data_vars.keys()):
        if var not in required_vars:
            ds_out = ds_out.drop_vars(var)

    # Write output with proper time encoding (seconds since 1970-01-01)
    # to match the original CDS format expected by the Fortran model
    encoding = {
        'valid_time': {
            'units': 'seconds since 1970-01-01',
            'calendar': 'proleptic_gregorian',
            'dtype': 'int64'
        }
    }
    # Apply same encoding to all time-dependent variables
    for var in ds_out.data_vars:
        if 'valid_time' in ds_out[var].dims:
            encoding[var] = {'zlib': True, 'complevel': 4}

    print(f"Writing merged file to {output_nc}")
    ds_out.to_netcdf(output_nc, format='NETCDF4', encoding=encoding)
    print("Done!")

    ds_inst.close()
    ds_snow.close()


def main():
    parser = argparse.ArgumentParser(
        description="Merge ERA5 snowfall with instantaneous variables."
    )
    parser.add_argument(
        "instantaneous_nc",
        help="Path to instantaneous variables NetCDF (u10, v10, t2m, d2m, msl, tcc)"
    )
    parser.add_argument(
        "snowfall_nc",
        help="Path to snowfall NetCDF (accumulated, 12-hourly at 00/12 UTC)"
    )
    parser.add_argument(
        "output_nc",
        help="Output merged NetCDF path"
    )
    args = parser.parse_args()

    for path in [args.instantaneous_nc, args.snowfall_nc]:
        if not pathlib.Path(path).exists():
            print(f"ERROR: {path} not found")
            return 1

    merge_snowfall(args.instantaneous_nc, args.snowfall_nc, args.output_nc)
    return 0


if __name__ == "__main__":
    sys.exit(main())