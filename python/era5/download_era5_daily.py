#!/usr/bin/env python3
"""Stage 12.9 ERA5 hourly CDS -> daily means (approved path).

The CDS `reanalysis-era5-single-levels-daily-means` product returns 404, so we
download hourly ERA5 and aggregate locally:
  - u10/v10/t2m/d2m/tcc/msl: arithmetic mean of 24 hourly values;
  - sf: daily total / 86400 -> m/s water equivalent.
The output uses the variable names/time convention required by netcdf_input.f90.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import cdsapi
import numpy as np
import pandas as pd
import xarray as xr

OUT = Path("data/input/reanalysis/era5")
MANIFEST = Path("docs/validation/stage12.9_era5_manifest.json")
DATASET = "reanalysis-era5-single-levels"
VARS = {
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "2m_temperature": "t2m",
    "2m_dewpoint_temperature": "d2m",
    "total_cloud_cover": "tcc",
    "mean_sea_level_pressure": "msl",
    "snowfall": "sf",
}
MONTHS = [f"2020-{m:02d}" for m in range(1, 13)] + ["2024-01", "2024-07"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def aggregate(ds: xr.Dataset) -> xr.Dataset:
    tname = "valid_time" if "valid_time" in ds.coords else "time"
    ds = ds.rename({tname: "time"})
    # Require 24-hour completeness for every day.
    counts = ds.time.dt.floor("D").to_series().value_counts()
    if (counts != 24).any():
        bad = counts[counts != 24]
        raise RuntimeError(f"ERA5 hourly window incomplete: {bad.to_dict()}")
    out = xr.Dataset()
    for cds_name, short in VARS.items():
        key = cds_name if cds_name in ds else short
        if key not in ds:
            raise RuntimeError(f"ERA5 variable missing: {cds_name}/{short}")
        a = ds[key]
        if short == "sf":
            # hourly accumulation [m] -> daily total [m] -> m/s
            a = (a.resample(time="1D").sum() / 86400.0).astype("float32")
            a.attrs["units"] = "m s-1"
            a.attrs["long_name"] = "snowfall rate (water equivalent)"
        else:
            a = a.resample(time="1D").mean().astype("float32")
        out[short] = a
    # netcdf_input expects seconds since 1970-01-01.
    out = out.assign_coords(time=(
        "time",
        ((out.time.values - np.datetime64("1970-01-01T00:00:00")) /
         np.timedelta64(1, "s")).astype("float64"),
        {"units": "seconds since 1970-01-01", "calendar": "gregorian"}))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--months", default="")
    p.add_argument("--area", default="86,5,63,80")
    p.add_argument("--offpeak-only", action="store_true")
    a = p.parse_args()
    months = [m.strip() for m in a.months.split(",") if m.strip()] or MONTHS
    area = [float(x) for x in a.area.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)
    man = {"dataset_id": DATASET, "cds_daily_means_attempt": {
               "dataset": "reanalysis-era5-single-levels-daily-means",
               "status": "404 process not found"},
           "aggregation": "hourly 00-23 UTC -> daily arithmetic mean; sf total/86400",
           "area": area, "months": {}}
    if MANIFEST.exists():
        man = json.loads(MANIFEST.read_text())
    c = cdsapi.Client()
    for ym in months:
        y, m = ym.split("-")
        outdir = OUT / y
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"era5_{y}_{m}_daily.nc"
        if out.exists() and ym in man.get("months", {}):
            print(f"skip {ym}", flush=True)
            continue
        nd = calendar.monthrange(int(y), int(m))[1]
        raw = Path(f"/tmp/era5_hourly_{y}_{m}.nc")
        req = {"product_type": ["reanalysis"],
               "variable": list(VARS),
               "year": [y], "month": [m],
               "day": [f"{d:02d}" for d in range(1, nd + 1)],
               "time": [f"{h:02d}:00" for h in range(24)],
               "area": area, "data_format": "netcdf",
               "download_format": "unarchived"}
        if a.offpeak_only:
            now = datetime.now(timezone.utc)
            if now.hour >= 8:
                nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                wait = (nxt - now).total_seconds()
                print(f"OFF-PEAK wait {wait/3600:.2f} h before {ym}", flush=True)
                time.sleep(wait)
        print(f"CDS {ym}", flush=True)
        c.retrieve(DATASET, req, raw)
        srcs = []
        extracted = []
        if zipfile.is_zipfile(raw):
            with zipfile.ZipFile(raw) as z:
                names = [n for n in z.namelist() if n.endswith('.nc')]
                if not names:
                    raise RuntimeError(f"no NetCDF in CDS zip: {raw}")
                z.extractall(path=raw.parent)
                extracted = [raw.parent / n for n in names]
                srcs = extracted
        else:
            srcs = [raw]
        dss = [xr.open_dataset(s) for s in srcs]
        ds = dss[0] if len(dss) == 1 else xr.merge(dss, compat='override')
        daily = aggregate(ds)
        daily.to_netcdf(out, encoding={v: {"zlib": True, "complevel": 4}
                                      for v in daily.data_vars})
        for d in dss:
            d.close()
        raw.unlink(missing_ok=True)
        for e in extracted:
            e.unlink(missing_ok=True)
        man.setdefault("months", {})[ym] = {
            "path": str(out), "size_bytes": out.stat().st_size,
            "sha256": sha256(out), "source": DATASET,
            "aggregation": "hourly 00-23 UTC; mean except sf total/86400"}
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(man, indent=2) + "\n")
        print(f"  {out} {out.stat().st_size/1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
