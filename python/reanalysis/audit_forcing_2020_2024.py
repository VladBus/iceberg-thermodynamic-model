#!/usr/bin/env python3
"""Audit local ERA5/GLORYS forcing for the Stage 12.11 2020/2024 runs.

Read-only: no downloads, no data modification. Opens metadata/time coordinates
only; it does not load the full 3D fields.
"""
from __future__ import annotations

import argparse
import calendar
import json
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
ERA5 = ROOT / "data/input/reanalysis/era5"
GLORYS = ROOT / "data/input/reanalysis/glorys"
WAM = ROOT / "data/input/reanalysis/wam"
YEARS = (2020, 2024)
ERA5_VARS = ("u10", "v10", "t2m", "d2m", "tcc", "msl", "sf")
GLORYS_VARS = ("thetao", "so", "uo", "vo", "zos", "siconc", "sithick", "usi", "vsi")


def time_check(ds: xr.Dataset, year: int, month: int | None) -> dict:
    if "time" not in ds.coords:
        return {"ok": False, "error": "missing time coordinate"}
    t = np.asarray(ds["time"].values)
    if t.size == 0 or np.any(np.isnat(t)):
        return {"ok": False, "error": "empty or NaT time"}
    expected = calendar.monthrange(year, month)[1] if month else (366 if calendar.isleap(year) else 365)
    diffs = np.diff(t.astype("datetime64[s]").astype("int64"))
    return {
        "ok": t.size == expected and np.all(diffs > 0) and len(np.unique(t)) == t.size,
        "records": int(t.size),
        "expected": expected,
        "monotonic": bool(np.all(diffs > 0)),
        "unique": bool(len(np.unique(t)) == t.size),
        "start": str(t[0].astype("datetime64[D]")),
        "end": str(t[-1].astype("datetime64[D]")),
    }


def check_coverage(ds: xr.Dataset, lat_name="latitude", lon_name="longitude") -> dict:
    if lat_name not in ds or lon_name not in ds:
        return {"ok": False, "error": "missing lat/lon coordinates"}
    lat = np.asarray(ds[lat_name].values, dtype=float)
    lon = np.asarray(ds[lon_name].values, dtype=float)
    return {
        "ok": bool(lat.size > 1 and lon.size > 1 and
                   lat.min() <= 63.0 and lat.max() >= 80.0 and
                   lon.min() <= 5.0 and lon.max() >= 80.0),
        "lat_min": float(lat.min()), "lat_max": float(lat.max()),
        "lon_min": float(lon.min()), "lon_max": float(lon.max()),
    }


def check_vars(ds: xr.Dataset, expected: tuple[str, ...]) -> dict:
    missing = [v for v in expected if v not in ds.data_vars]
    units = {v: ds[v].attrs.get("units") for v in expected if v in ds.data_vars}
    return {"ok": not missing, "missing": missing, "units": units}


def audit_era5(year: int) -> dict:
    result = {"product": "ERA5", "year": year, "months": {}}
    for month in range(1, 13):
        path = ERA5 / str(year) / f"era5_{year}_{month:02d}_daily.nc"
        if not path.exists():
            result["months"][f"{year}-{month:02d}"] = {"ok": False, "error": "missing file"}
            continue
        with xr.open_dataset(path, decode_times=True) as ds:
            result["months"][f"{year}-{month:02d}"] = {
                "path": str(path.relative_to(ROOT)),
                "file_size": path.stat().st_size,
                "time": time_check(ds, year, month),
                "coverage": check_coverage(ds),
                "variables": check_vars(ds, ERA5_VARS),
            }
    result["ok"] = all(v.get("time", {}).get("ok") and
                       v.get("coverage", {}).get("ok") and
                       v.get("variables", {}).get("ok")
                       for v in result["months"].values())
    annual = ERA5 / str(year) / f"era5_{year}_daily.nc"
    if annual.exists():
        with xr.open_dataset(annual, decode_times=True) as ds:
            result["annual_daily"] = {
                "path": str(annual.relative_to(ROOT)),
                "file_size": annual.stat().st_size,
                "time": time_check(ds, year, None),
                "coverage": check_coverage(ds),
                "variables": check_vars(ds, ERA5_VARS),
            }
    else:
        result["annual_daily"] = {"ok": False, "error": "missing annual daily file"}
    return result


def audit_glorys(year: int) -> dict:
    result = {"product": "GLORYS12", "year": year, "months": {}}
    for month in range(1, 13):
        path = GLORYS / str(year) / f"glorys12_barents_{year}_{month:02d}.nc"
        if not path.exists():
            result["months"][f"{year}-{month:02d}"] = {"ok": False, "error": "missing file"}
            continue
        with xr.open_dataset(path, decode_times=True) as ds:
            result["months"][f"{year}-{month:02d}"] = {
                "path": str(path.relative_to(ROOT)),
                "file_size": path.stat().st_size,
                "time": time_check(ds, year, month),
                "coverage": check_coverage(ds),
                "variables": check_vars(ds, GLORYS_VARS),
                "depth_levels": int(ds.sizes.get("depth", 0)),
            }
    result["ok"] = all(v.get("time", {}).get("ok") and
                       v.get("coverage", {}).get("ok") and
                       v.get("variables", {}).get("ok")
                       for v in result["months"].values())
    annual = GLORYS / str(year) / f"glorys12_barents_{year}_daily.nc"
    if annual.exists():
        with xr.open_dataset(annual, decode_times=True) as ds:
            result["annual_daily"] = {
                "path": str(annual.relative_to(ROOT)),
                "file_size": annual.stat().st_size,
                "time": time_check(ds, year, None),
                "coverage": check_coverage(ds),
                "variables": check_vars(ds, GLORYS_VARS),
            }
    else:
        result["annual_daily"] = {"ok": False, "error": "missing annual daily file"}
    return result


def audit_wam() -> dict:
    out = {}
    for year in YEARS:
        path = WAM / str(year) / f"wam_{year}-01.nc"
        if not path.exists():
            out[str(year)] = {"ok": False, "error": "missing sample"}
            continue
        with xr.open_dataset(path, decode_times=True) as ds:
            out[str(year)] = {
                "path": str(path.relative_to(ROOT)),
                "dimensions": dict(ds.sizes),
                "variables": list(ds.data_vars),
                "rotated_grid": "rlat" in ds.coords and "rlon" in ds.coords,
                "compatible_with_wave_forcing": False,
                "reason": "native rotated grid and Hs/Stokes variable mapping not implemented",
            }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    report = {
        "years": list(YEARS),
        "era5": {str(y): audit_era5(y) for y in YEARS},
        "glorys": {str(y): audit_glorys(y) for y in YEARS},
        "wam": audit_wam(),
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
