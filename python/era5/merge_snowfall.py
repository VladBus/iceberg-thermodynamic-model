#!/usr/bin/env python3
"""Merge ERA5 snowfall (hourly accumulation) with instantaneous variables.

ERA5 single-level snowfall (``sf``) is an **hourly accumulation over the hour
ending at the validity time** (ECMWF convention; T-19 v2 CDS probe: the 12:00
field is 1.009x the mean of all 24 hourly fields, not 12x).  The model's
atmosphere is 6-hourly, so:

* hourly raw records are summed over each 6-hour window ``(t-6h, t]`` and
  divided by 21600 s to obtain a 6-hour mean rate;
* coarser sampled artifacts (e.g. 00/12 UTC only) are converted with the
  **hourly divisor 3600 s** and linearly interpolated to the model times.

Units: m of water equivalent -> m s-1.

Usage (Stage 6.2 run-based data layout):

    python python/era5/merge_snowfall.py \
        data/input/raw/era5/2020/2020_01/era5_2020_01.nc \
        data/input/raw/era5/2020/2020_01/snowfall_2020_01.nc \
        data/input/processed/era5/2020/2020_01/era5_2020_01_merged.nc

The Fortran reader expects the merged snowfall variable named ``sf`` (units
m s-1) in the output file.
"""

import argparse
import pathlib
import sys

import numpy as np
import xarray as xr

from scipy import interpolate

# T-19 v2: ECMWF hourly accumulations are over the hour ending at valid_time.
SNOWFALL_ACCUMULATION_PERIOD_S = 3600.0
MODEL_STEP_S = 21600.0  # 6-hourly atmospheric forcing


def accumulation_to_rate(accumulation, period_s=SNOWFALL_ACCUMULATION_PERIOD_S):
    """Convert accumulated snowfall [m water equivalent] to rate [m s-1]."""
    if period_s <= 0:
        raise ValueError("accumulation period must be positive")
    return np.asarray(accumulation) / float(period_s)


def aggregate_hourly_to_model_steps(snow_accum, snow_time_sec, target_time_sec,
                                    period_s=SNOWFALL_ACCUMULATION_PERIOD_S,
                                    step_s=MODEL_STEP_S):
    """Aggregate hourly accumulations into model-step mean rates.

    For each target time, sum the raw accumulations whose validity times fall
    in ``(target - step_s, target]`` and divide by ``step_s``.  This is the
    correct treatment when the raw file is hourly; it avoids treating a single
    hourly accumulation as a 6-hour total.
    """
    out = np.zeros((len(target_time_sec),) + snow_accum.shape[1:], dtype=np.float32)
    for n, t in enumerate(target_time_sec):
        sel = (snow_time_sec > t - step_s) & (snow_time_sec <= t)
        if not np.any(sel):
            continue
        out[n] = np.sum(snow_accum[sel], axis=0) / float(step_s)
    return out


def merge_snowfall(instantaneous_nc, snowfall_nc, output_nc):
    """Merge snowfall into instantaneous variables file.

    Args:
        instantaneous_nc: Path to ERA5 instantaneous variables (u10, v10, t2m, d2m, msl, tcc)
        snowfall_nc: Path to ERA5 snowfall (hourly accumulations, m water eq.)
        output_nc: Output merged NetCDF path
    """
    print(f"Reading instantaneous variables from {instantaneous_nc}")
    ds_inst = xr.open_dataset(instantaneous_nc)

    print(f"Reading snowfall from {snowfall_nc}")
    ds_snow = xr.open_dataset(snowfall_nc)

    print(f"Snowfall shape: {ds_snow['sf'].shape}")
    print(f"Snowfall time steps: {len(ds_snow.valid_time)}")
    print(
        f"Snowfall time range: {ds_snow.valid_time[0].values} to {ds_snow.valid_time[-1].values}"
    )

    target_times = ds_inst.valid_time.values
    target_time_sec = np.array(
        [np.datetime64(t, "s").astype("int64") for t in target_times]
    )
    snow_times = ds_snow.valid_time.values
    snow_time_sec = np.array(
        [np.datetime64(t, "s").astype("int64") for t in snow_times]
    )

    print(f"Target (instantaneous) time steps: {len(target_times)}")
    print(f"Target time range: {target_times[0]} to {target_times[-1]}")
    print(f"Snowfall time steps: {len(snow_times)}")
    print(f"Snowfall time range: {snow_times[0]} to {snow_times[-1]}")

    snow_accum = ds_snow["sf"].values  # [time, lat, lon] in m water equivalent
    dt_snow = np.diff(snow_time_sec)
    median_dt = float(np.median(dt_snow)) if dt_snow.size else np.inf
    nlat, nlon = snow_accum.shape[1], snow_accum.shape[2]

    if median_dt <= 3600.0 and len(snow_times) >= 2:
        # Hourly raw file: sum the six hourly accumulations per model step.
        print("Hourly snowfall detected: aggregating to 6-hourly model steps "
              "(sum / 21600 s).")
        snow_rate_interp = aggregate_hourly_to_model_steps(
            snow_accum, snow_time_sec, target_time_sec)
    else:
        # Coarse sampled artifact (e.g. 00/12 UTC): each record is an hourly
        # accumulation at the validity time.  Convert with /3600 and interpolate.
        print("Coarse snowfall sampling detected: hourly accumulation -> rate "
              "(/3600 s) and linear interpolation to model times.")
        snow_rate = accumulation_to_rate(snow_accum)  # m/s
        snow_rate_interp = np.zeros(
            (len(target_times), nlat, nlon), dtype=np.float32)
        for i in range(nlat):
            for j in range(nlon):
                if np.all(snow_rate[:, i, j] == 0):
                    continue
                f = interpolate.interp1d(
                    snow_time_sec,
                    snow_rate[:, i, j],
                    kind="linear",
                    bounds_error=False,
                    fill_value=0.0,
                )
                snow_rate_interp[:, i, j] = f(target_time_sec)

    ds_out = ds_inst.copy()
    ds_out["sf"] = xr.DataArray(
        snow_rate_interp,
        dims=("valid_time", "latitude", "longitude"),
        coords={
            "valid_time": target_times,
            "latitude": ds_snow.latitude,
            "longitude": ds_snow.longitude,
        },
        attrs={
            "units": "m s-1",
            "long_name": "Snowfall rate",
            "standard_name": "snowfall_flux",
            "comment": ("ERA5 hourly snowfall accumulation (m water equivalent "
                        "over the hour ending at valid_time); divided by 3600 s "
                        "and, when hourly records are available, summed over each "
                        "6-hour model window (/21600 s)."),
        },
    )

    required_vars = ["u10", "v10", "t2m", "d2m", "msl", "tcc", "sf"]
    for var in list(ds_out.data_vars.keys()):
        if var not in required_vars:
            ds_out = ds_out.drop_vars(var)

    encoding = {
        "valid_time": {
            "units": "seconds since 1970-01-01",
            "calendar": "proleptic_gregorian",
            "dtype": "int64",
        }
    }
    for var in ds_out.data_vars:
        if "valid_time" in ds_out[var].dims:
            encoding[var] = {"zlib": True, "complevel": 4}

    print(f"Writing merged file to {output_nc}")
    ds_out.to_netcdf(output_nc, format="NETCDF4", encoding=encoding)
    print("Done!")

    ds_inst.close()
    ds_snow.close()


def main():
    parser = argparse.ArgumentParser(
        description="Merge ERA5 snowfall with instantaneous variables."
    )
    parser.add_argument(
        "instantaneous_nc",
        help="Path to instantaneous variables NetCDF (u10, v10, t2m, d2m, msl, tcc)",
    )
    parser.add_argument(
        "snowfall_nc",
        help="Path to ERA5 snowfall NetCDF (hourly accumulations, m water eq.)",
    )
    parser.add_argument("output_nc", help="Output merged NetCDF path")
    args = parser.parse_args()

    for path in [args.instantaneous_nc, args.snowfall_nc]:
        if not pathlib.Path(path).exists():
            print(f"ERROR: {path} not found")
            return 1

    merge_snowfall(args.instantaneous_nc, args.snowfall_nc, args.output_nc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
