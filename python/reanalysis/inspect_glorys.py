#!/usr/bin/env python3
"""Inspect a GLORYS12 NetCDF subset for Stage 12.1 validation.

Reports the grid structure (regular vs curvilinear), coordinate arrays,
depth levels, time axis, per-variable units/shape/NaN/range statistics, and
(for the static file) the land-sea mask values. It is the reconnaissance tool
that must be run BEFORE any Fortran reader is written, so the reader contract
is fixed from the observed structure rather than guessed.

Usage:
    python python/reanalysis/inspect_glorys.py <netcdf_file> [--full-stats]

--full-stats: compute min/max/mean/NaN over the entire (month) array.
OFF by default: stats are taken from the first and last time slice only, to
bound memory on multi-GB files. The reconnaissance gate only needs a
representative range and the NaN/mask structure, so a two-slice sample is
enough; use --full-stats when a precise seasonal range is required.
"""

from __future__ import annotations

import argparse
import json
import sys

import dask.array as da
import numpy as np
import xarray as xr


def _finite_range(var: xr.DataArray) -> tuple[float | None, float | None, float | None]:
    """Return (min, max, mean) over finite values, None if all-NaN."""
    arr = var.values
    finite = np.isfinite(arr)
    if not finite.any():
        return None, None, None
    vals = arr[finite]
    return float(vals.min()), float(vals.max()), float(vals.mean())


def _stat_sample(var: xr.DataArray, full: bool) -> xr.DataArray:
    if full or var.ndim == 0:
        return var
    if "time" in var.dims and var.sizes["time"] > 2:
        return var.isel(time=[0, -1])
    return var


def _coord_info(ds: xr.Dataset, name: str) -> dict | None:
    if name not in ds.coords:
        return None
    c = ds[name]
    info = {
        "dims": list(c.dims),
        "shape": list(c.shape),
        "ndim": c.ndim,
        "dtype": str(c.dtype),
        "units": c.attrs.get("units", "MISSING"),
        "standard_name": c.attrs.get("standard_name", "MISSING"),
    }
    if name in ("latitude", "longitude") and c.ndim == 1:
        vals = c.values
        info["first"] = float(vals[0])
        info["last"] = float(vals[-1])
        if len(vals) >= 2:
            info["step"] = float(round(abs(vals[1] - vals[0]), 6))
    if name == "depth":
        vals = c.values
        info["n_levels"] = int(len(vals))
        info["first_10"] = [float(round(float(x), 4)) for x in vals[:10]]
        info["min"] = float(vals.min())
        info["max"] = float(vals.max())
    return info


def _time_info(ds: xr.Dataset) -> dict | None:
    if "time" not in ds.coords:
        return None
    t = ds["time"]
    enc = t.encoding or {}
    return {
        "n_steps": int(t.size),
        "storage_units": enc.get("units", "MISSING"),
        "first": str(t.values[0]),
        "last": str(t.values[-1]),
    }


def _grid_type(ds: xr.Dataset) -> str:
    lat = ds.coords.get("latitude")
    lon = ds.coords.get("longitude")
    if lat is not None and lon is not None:
        if lat.ndim == 1 and lon.ndim == 1:
            return "regular_1d_lat_lon"
        if lat.ndim == 2 and lon.ndim == 2:
            return "curvilinear_2d"
    return "unknown"


def inspect_file(filepath: str, full: bool) -> dict:
    ds = xr.open_dataset(filepath)
    info = {
        "file": filepath,
        "grid_type": _grid_type(ds),
        "dimensions": {str(k): int(v) for k, v in ds.sizes.items()},
        "coordinate_vars": list(ds.coords),
        "coordinates": {
            name: _coord_info(ds, name)
            for name in ("latitude", "longitude", "depth", "time")
        },
        "time": _time_info(ds),
        "global_attrs": {k: str(v) for k, v in ds.attrs.items()},
        "variables": {},
    }

    for var_name in ds.data_vars:
        var = ds[var_name]
        entry = {
            "dims": list(var.dims),
            "shape": list(var.shape),
            "dtype": str(var.dtype),
            "units": var.attrs.get("units", "MISSING"),
            "long_name": var.attrs.get("long_name", "MISSING"),
            "standard_name": var.attrs.get("standard_name", "MISSING"),
            "_FillValue": _scalar(var.attrs.get("_FillValue")),
            "valid_min": _scalar(var.attrs.get("valid_min")),
            "valid_max": _scalar(var.attrs.get("valid_max")),
            "stats_sample": "full" if full else _sample_label(var),
        }
        sample = _stat_sample(var, full)
        nan_count = int(sample.isnull().sum().compute())
        total = int(sample.size)
        vmin, vmax, vmean = _finite_range(sample)
        entry.update(
            {
                "nan_count": nan_count,
                "sample_points": total,
                "nan_fraction": round(nan_count / total, 6) if total else None,
                "min": vmin,
                "max": vmax,
                "mean": vmean,
            }
        )
        if var_name == "mask":
            uniq = np.unique(sample.values.astype("int8"))
            entry["unique_values"] = [int(u) for u in uniq]
        info["variables"][var_name] = entry

    ds.close()
    return info


def _scalar(value):
    if value is None:
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _sample_label(var: xr.DataArray) -> str:
    if "time" in var.dims and var.sizes.get("time", 0) > 2:
        return "time_slice[0,-1]"
    return "full"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netcdf_file")
    parser.add_argument(
        "--full-stats",
        action="store_true",
        help="compute statistics over the whole array (more memory)",
    )
    args = parser.parse_args()

    info = inspect_file(args.netcdf_file, args.full_stats)
    print(json.dumps(info, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
