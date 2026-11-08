#!/usr/bin/env python3
"""Merge monthly daily-mean ERA5 files into one annual file.

Usage: python python/era5/merge_era5_annual.py --year 2020
No downloads; reads only local monthly files.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/input/reanalysis/era5"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, choices=(2020, 2024), required=True)
    args = parser.parse_args()
    year = args.year
    files = [BASE / str(year) / f"era5_{year}_{m:02d}_daily.nc" for m in range(1, 13)]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise SystemExit(f"missing monthly files: {missing}")
    out = BASE / str(year) / f"era5_{year}_daily.nc"
    ds = xr.open_mfdataset(
        files,
        combine="by_coords",
        data_vars="minimal",
        coords="minimal",
        compat="override",
    )
    ds = ds.sortby("time")
    encoding = {
        v: {"zlib": True, "complevel": 4, "dtype": "float32"}
        for v in ds.data_vars
    }
    ds.to_netcdf(out, encoding=encoding)
    ds.close()
    print(f"wrote {out} {out.stat().st_size/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
