#!/usr/bin/env python3
"""Monthly-mean Barents GLORYS12 fallback for Stage 12.8.

Daily CMEMS subset access is blocked here (auth 403).  Native monthly files
(2020-01 .. 2021-06) are public on S3 and are streamed by HDF5 chunk, not
downloaded whole.  The output is a reader-ready packed-int16 NetCDF with the
same Barents bbox as the existing daily Jan-2020 file.  This is a documented
fallback: it is monthly-mean forcing, not daily.

Usage:
  python python/reanalysis/download_barents_monthly.py \
    --out data/input/raw/reanalysis/glorys12/2020/glorys12_barents_2020_2021_monthly.nc
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import fsspec
import h5py
import netCDF4 as nc
import numpy as np
import pandas as pd

BASE = ("https://s3.waw3-1.cloudferro.com/mdl-native-14/native/"
        "GLOBAL_MULTIYEAR_PHY_001_030/"
        "cmems_mod_glo_phy_my_0.083deg_P1M-m_202311")
VARS3 = ["thetao", "so", "uo", "vo"]
VARS2 = ["zos", "siconc", "sithick"]
FILL = np.int16(-32767)


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path,
                   default=Path("data/input/raw/reanalysis/glorys12/2020/"
                                "glorys12_barents_2020_2021_monthly.nc"))
    p.add_argument("--start", default="2020-01")
    p.add_argument("--end", default="2021-06")
    p.add_argument("--max-months", type=int, default=0)
    p.add_argument("--lat-min", type=float, default=63.0)
    p.add_argument("--lat-max", type=float, default=86.0)
    p.add_argument("--lon-min", type=float, default=5.0)
    p.add_argument("--lon-max", type=float, default=80.0)
    p.add_argument("--max-depth", type=float, default=600.0)
    return p.parse_args()


def months(start: str, end: str) -> list[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y += 1; m = 1
    return out


def url(ym: str) -> str:
    y, m = ym.split("-")
    return f"{BASE}/{y}/mercatorglorys12v1_gl12_mean_{y}{m}.nc"


def main() -> int:
    a = args()
    mons = months(a.start, a.end)
    if a.max_months:
        mons = mons[:a.max_months]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if a.out.exists():
        a.out.unlink()

    fobj = fsspec.open(url(mons[0]), "rb", block_size=2**20).open()
    f = h5py.File(fobj, "r")
    lat = f["latitude"][:].astype("f8")
    lon = f["longitude"][:].astype("f8")
    dep = f["depth"][:].astype("f8")
    lat_i = np.where((lat >= a.lat_min) & (lat <= a.lat_max))[0]
    lon_i = np.where((lon >= a.lon_min) & (lon <= a.lon_max))[0]
    dep_i = np.where(dep <= a.max_depth)[0]
    attrs = {v: {k: f[v].attrs[k] for k in ("scale_factor", "add_offset")
                 if k in f[v].attrs} for v in VARS3 + VARS2}
    t0 = float(f["time"][0])
    f.close(); fobj.close()
    print(f"{len(mons)} months, grid {len(lat_i)}x{len(lon_i)}x{len(dep_i)}, t0={t0}")

    root = nc.Dataset(a.out, "w", format="NETCDF4")
    root.set_auto_maskandscale(False)
    root.createDimension("time", None)
    root.createDimension("depth", len(dep_i))
    root.createDimension("latitude", len(lat_i))
    root.createDimension("longitude", len(lon_i))
    tv = root.createVariable("time", "f8", ("time",))
    tv.units = "hours since 1950-01-01"; tv.calendar = "gregorian"
    dv = root.createVariable("depth", "f4", ("depth",)); dv.units = "m"; dv.positive = "down"
    dv[:] = dep[dep_i].astype("f4")
    lav = root.createVariable("latitude", "f4", ("latitude",)); lav.units = "degrees_north"
    lav[:] = lat[lat_i].astype("f4")
    lov = root.createVariable("longitude", "f4", ("longitude",)); lov.units = "degrees_east"
    lov[:] = lon[lon_i].astype("f4")
    for v in VARS3 + VARS2:
        dims = ("time", "depth", "latitude", "longitude") if v in VARS3 else \
               ("time", "latitude", "longitude")
        var = root.createVariable(v, "i2", dims, zlib=True, complevel=4,
                                  fill_value=FILL,
                                  chunksizes=(1,) + tuple(root.dimensions[d].size for d in dims[1:]))
        var.set_auto_maskandscale(False)
        var.scale_factor = float(np.asarray(attrs[v].get("scale_factor", 1.0)).item())
        var.add_offset = float(np.asarray(attrs[v].get("add_offset", 0.0)).item())

    for n, ym in enumerate(mons):
        fobj = fsspec.open(url(ym), "rb", block_size=2**20).open()
        f = h5py.File(fobj, "r")
        # Monthly means are assigned to the first day of the month so a
        # Jan-1/Jul-1 run start is inside the reader time interval.
        tv[n] = float((pd.Timestamp(f"{ym}-01") - pd.Timestamp("1950-01-01")) / pd.Timedelta(hours=1))
        for v in VARS3:
            arr = f[v][0, int(dep_i[0]):int(dep_i[-1]) + 1,
                       int(lat_i[0]):int(lat_i[-1]) + 1,
                       int(lon_i[0]):int(lon_i[-1]) + 1]
            root.variables[v][n, :, :, :] = arr
            del arr
        for v in VARS2:
            arr = f[v][0, int(lat_i[0]):int(lat_i[-1]) + 1,
                       int(lon_i[0]):int(lon_i[-1]) + 1]
            root.variables[v][n, :, :] = arr
            del arr
        f.close(); fobj.close()
        root.sync()
        print(f"  {ym} ({n + 1}/{len(mons)})", flush=True)
    root.close()
    print(f"wrote {a.out} ({a.out.stat().st_size/1e6:.1f} MB)")

    static = Path("data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc")
    out_static = a.out.with_name("glorys12_barents_2020_2021_static.nc")
    if static.exists():
        shutil.copy(static, out_static)
        print(f"static copied: {out_static}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
