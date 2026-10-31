#!/usr/bin/env python3
"""Antarctic GLORYS12 native S3 extractor for Stage 12.7a.

The CMEMS auth endpoint is geo/IP-blocked here (HTTP 403 "RBAC: access
denied"), but the public native S3 bucket is readable.  Native daily files
are ~1.28 GB each with HDF5 chunks (1,7,341,720); this script opens each file
remotely and reads only the chunks intersecting a site's bbox/depth, so peak
RSS stays ~100 MB (WSL2 8 GB; whole-file/whole-site loads are forbidden).

Source:
  https://s3.waw3-1.cloudferro.com/mdl-native-14/native/
  GLOBAL_MULTIYEAR_PHY_001_030/cmems_mod_glo_phy_my_0.083deg_P1D-m_202311/

Output per site (reader-ready packed int16):
  glorys12_<site>_daily.nc
  glorys12_<site>_static.nc
  MANIFEST.json

Usage:
  python python/reanalysis/download_cmems.py --csv <csv> --out-dir <dir> \
      [--max-interval 120] [--max-depth 800] [--sites BG,LG] \
      [--max-dates N] [--overwrite]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import fsspec
import h5py
import netCDF4 as nc
import numpy as np
import pandas as pd

BUCKET = "https://s3.waw3-1.cloudferro.com/mdl-native-14/"
PREFIX = ("native/GLOBAL_MULTIYEAR_PHY_001_030/"
          "cmems_mod_glo_phy_my_0.083deg_P1D-m_202311")
VARS = ["thetao", "so", "uo", "vo"]
FILL = np.int16(-32767)
DATE_RE = re.compile(r"_(\d{8})_R\d{8}\.nc$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--max-interval", type=float, default=120.0)
    p.add_argument("--max-depth", type=float, default=800.0)
    p.add_argument("--sites", default="")
    p.add_argument("--max-dates", type=int, default=0)
    p.add_argument("--date-start", default="")
    p.add_argument("--date-end", default="")
    p.add_argument("--suffix", default="")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def list_month(ym: str, cache: dict) -> dict[str, str]:
    if ym in cache:
        return cache[ym]
    prefix = f"{PREFIX}/{ym[:4]}/{ym[4:]}"
    url = f"{BUCKET}?list-type=2&prefix={prefix}/&max-keys=1000"
    out = {}
    root = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                root = ET.fromstring(r.read())
            break
        except Exception as e:
            print(f"  WARN list retry {attempt + 1}/5: {type(e).__name__}", flush=True)
            time.sleep(2.0 * (attempt + 1))
    if root is None:
        raise RuntimeError(f"cannot list {prefix}")
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    for c in root.findall("s:Contents", ns):
        key = c.find("s:Key", ns).text
        m = DATE_RE.search(key)
        if m:
            out[m.group(1)] = key
    cache[ym] = out
    return out


def open_remote(key: str, attempts: int = 6):
    last = None
    for i in range(attempts):
        try:
            fobj = fsspec.open(BUCKET + key, "rb", block_size=2**20).open()
            return fobj, h5py.File(fobj, "r")
        except Exception as e:  # transient S3 resets are common
            last = e
            print(f"    WARN open retry {i + 1}/{attempts}: {type(e).__name__}", flush=True)
            time.sleep(2.0 * (i + 1))
    raise last


def main() -> int:
    a = parse_args()
    df = pd.read_csv(a.csv)
    df["date_start"] = pd.to_datetime(df["date_start"].astype(str), format="%Y%m%d", errors="coerce")
    df["date_end"] = pd.to_datetime(df["date_end"].astype(str), format="%Y%m%d", errors="coerce")
    df["interval_days"] = (df["date_end"] - df["date_start"]).dt.total_seconds() / 86400.0
    sub = df[df["interval_days"] <= a.max_interval].copy()
    sites = [s.strip() for s in a.sites.split(",") if s.strip()]
    if sites:
        sub = sub[sub["site"].isin(sites)]
    if sub.empty:
        print("ERROR: no rows selected", file=sys.stderr)
        return 1

    a.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": BUCKET + PREFIX,
        "source_note": "public native S3; CMEMS auth endpoint geo-blocked on host",
        "created": pd.Timestamp.now('UTC').isoformat(),
        "max_interval_days": a.max_interval,
        "n_icebergs": int(len(sub)),
        "sites": {},
    }
    cache: dict[str, dict] = {}

    for site, g in sub.groupby("site", sort=True):
        dates = set()
        for _, r in g.iterrows():
            dates.update(pd.date_range(r.date_start, r.date_end + pd.Timedelta(days=1), freq="D").date)
        dates = sorted(dates)
        if a.date_start:
            d0 = date.fromisoformat(a.date_start)
            dates = [d for d in dates if d >= d0]
        if a.date_end:
            d1 = date.fromisoformat(a.date_end)
            dates = [d for d in dates if d <= d1]
        if a.max_dates > 0:
            dates = dates[:a.max_dates]
        if not dates:
            print(f"  SKIP {site}: empty date window", flush=True)
            continue
        lat_min = float(min(g.lat_i.min(), g.lat_f.min()) - 1.0)
        lat_max = float(max(g.lat_i.max(), g.lat_f.max()) + 1.0)
        lon_min = float(min(g.lon_i.min(), g.lon_f.min()) - 1.0)
        lon_max = float(max(g.lon_i.max(), g.lon_f.max()) + 1.0)
        max_depth = min(a.max_depth, float(np.ceil(g.draft.max() / 50.0) * 50.0 + 100.0))
        print(f"{site}: n={len(g)} dates={len(dates)} "
              f"bbox=({lat_min:.2f},{lat_max:.2f},{lon_min:.2f},{lon_max:.2f}) "
              f"depth<={max_depth:.0f}", flush=True)

        # Resolve date -> S3 key.
        keys: list[tuple[date, str]] = []
        for d in dates:
            ym = d.strftime("%Y%m")
            km = list_month(ym, cache)
            k = km.get(d.strftime("%Y%m%d"))
            if k is None:
                print(f"  WARN: no native file for {d}", flush=True)
            else:
                keys.append((d, k))
        if not keys:
            print(f"  SKIP {site}: no keys", flush=True)
            continue

        # Coordinates + variable attrs from the first file.
        fobj, f = open_remote(keys[0][1])
        lat = f["latitude"][:].astype("f8")
        lon = f["longitude"][:].astype("f8")
        dep = f["depth"][:].astype("f8")
        lat_i = np.where((lat >= lat_min) & (lat <= lat_max))[0]
        lon_i = np.where((lon >= lon_min) & (lon <= lon_max))[0]
        dep_i = np.where(dep <= max_depth + 50.0)[0]
        attrs = {v: {k: f[v].attrs[k] for k in ("scale_factor", "add_offset", "_FillValue")
                     if k in f[v].attrs} for v in VARS}
        # Surface mask from the first day.
        surf = f["thetao"][0, int(dep_i[0]), int(lat_i[0]):int(lat_i[-1]) + 1,
                           int(lon_i[0]):int(lon_i[-1]) + 1]
        mask = (surf != attrs["thetao"].get("_FillValue", FILL)).astype("i1")
        f.close(); fobj.close()

        daily = a.out_dir / f"glorys12_{site}{a.suffix}_daily.nc"
        static = a.out_dir / f"glorys12_{site}{a.suffix}_static.nc"
        if daily.exists() and not a.overwrite:
            print(f"  exists, skip: {daily}", flush=True)
            continue

        root = nc.Dataset(daily, "w", format="NETCDF4")
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
        for v in VARS:
            out = root.createVariable(v, "i2", ("time", "depth", "latitude", "longitude"),
                                      zlib=True, complevel=4, fill_value=FILL,
                                      chunksizes=(1, len(dep_i), len(lat_i), len(lon_i)))
            out.set_auto_maskandscale(False)
            out.scale_factor = float(np.asarray(attrs[v].get("scale_factor", 1.0)).item())
            out.add_offset = float(np.asarray(attrs[v].get("add_offset", 0.0)).item())

        t_start = time.time()
        for n, (d, key) in enumerate(keys):
            hours = (pd.Timestamp(d) - pd.Timestamp("1950-01-01")) / pd.Timedelta(hours=1)
            tv[n] = float(hours)
            read_ok = False
            for attempt in range(5):
                fobj = f = None
                try:
                    fobj, f = open_remote(key)
                    for v in VARS:
                        arr = f[v][0, int(dep_i[0]):int(dep_i[-1]) + 1,
                                   int(lat_i[0]):int(lat_i[-1]) + 1,
                                   int(lon_i[0]):int(lon_i[-1]) + 1]
                        root.variables[v][n, :, :, :] = arr
                        del arr
                    read_ok = True
                    break
                except Exception as e:
                    print(f"    WARN read retry {attempt + 1}/5: {type(e).__name__}", flush=True)
                    time.sleep(3.0 * (attempt + 1))
                finally:
                    if f is not None:
                        f.close()
                    if fobj is not None:
                        fobj.close()
            if not read_ok:
                root.close()
                raise RuntimeError(f"failed to read {d} after retries")
            if (n + 1) % 10 == 0 or n == len(keys) - 1:
                root.sync()
                print(f"    {n + 1}/{len(keys)} days, {time.time() - t_start:.0f}s", flush=True)
        root.close()
        print(f"  wrote {daily} ({daily.stat().st_size/1e6:.1f} MB)", flush=True)

        # Static mask (synthetic bathy, as the reader only uses mask/deptho).
        sroot = nc.Dataset(static, "w", format="NETCDF4")
        sroot.set_auto_maskandscale(False)
        sroot.createDimension("depth", 1)
        sroot.createDimension("latitude", len(lat_i))
        sroot.createDimension("longitude", len(lon_i))
        sd = sroot.createVariable("depth", "f4", ("depth",)); sd[:] = [0.0]
        sl = sroot.createVariable("latitude", "f4", ("latitude",)); sl[:] = lat[lat_i].astype("f4")
        so = sroot.createVariable("longitude", "f4", ("longitude",)); so[:] = lon[lon_i].astype("f4")
        sm = sroot.createVariable("mask", "i1", ("depth", "latitude", "longitude")); sm[:] = mask[None, :, :]
        sb = sroot.createVariable("deptho", "f4", ("latitude", "longitude")); sb[:] = 6000.0
        sroot.close()

        manifest["sites"][site] = {
            "n_icebergs": int(len(g)), "n_days": len(keys),
            "date_start": str(keys[0][0]), "date_end": str(keys[-1][0]),
            "bbox": [lat_min, lat_max, lon_min, lon_max],
            "max_depth_m": max_depth,
            "daily_file": daily.name, "daily_bytes": int(daily.stat().st_size),
            "static_file": static.name, "static_bytes": int(static.stat().st_size),
        }

    (a.out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    total = sum(v["daily_bytes"] + v["static_bytes"] for v in manifest["sites"].values())
    print(f"MANIFEST: {len(manifest['sites'])} sites, {manifest['n_icebergs']} icebergs, "
          f"{total/1e9:.3f} GB local", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
