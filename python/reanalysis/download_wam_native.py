#!/usr/bin/env python3
"""Native 3 km WAM monthly extractor (Stage 12.9, option 1).

Two workers alternate months. Each monthly file keeps the native rotated
polar-stereographic grid (rlat/rlon), packs VHM0/VSDX/VSDY to int16 with
Hs <= 0.01 m and Stokes <= 0.001 m/s, compression level 4, and writes a
per-month manifest with SHA-256. Existing completed months are skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import fsspec
import h5py
import netCDF4 as nc
import numpy as np

BASE = ("https://s3.waw3-1.cloudferro.com/mdl-native-10/native/"
        "ARCTIC_MULTIYEAR_WAV_002_013/cmems_mod_arc_wav_my_3km_PT1H-i_202511")
OUT = Path("data/input/reanalysis/wam")
VARS = ["VHM0", "VSDX", "VSDY"]
FILL = np.int16(-32767)


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", required=True, choices=["A", "B"])
    p.add_argument("--lat-min", type=float, default=63.0)
    p.add_argument("--lat-max", type=float, default=86.0)
    p.add_argument("--lon-min", type=float, default=5.0)
    p.add_argument("--lon-max", type=float, default=80.0)
    p.add_argument("--max-months", type=int, default=0)
    p.add_argument("--months", default="")
    return p.parse_args()


def worker_months(worker: str) -> list[str]:
    m2020 = [f"2020-{m:02d}" for m in range(1, 13)]
    a = [m for m in m2020 if int(m[-2:]) % 2 == 1] + ["2024-01"]
    b = [m for m in m2020 if int(m[-2:]) % 2 == 0] + ["2024-07"]
    return a if worker == "A" else b


def url(ym: str) -> str:
    y, m = ym.split("-")
    return f"{BASE}/{y}/{m}/{y}{m}01_MyWam3km_hindcast-cmems.nc"


def open_remote(url: str, attempts: int = 6):
    last = None
    for i in range(attempts):
        try:
            of = fsspec.open(url, "rb", block_size=2**20, timeout=60).open()
            return of, h5py.File(of, "r")
        except Exception as e:
            last = e
            print(f"    WARN open retry {i+1}/{attempts}: {type(e).__name__}", flush=True)
            time.sleep(2.0*(i+1))
    raise last


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    a = args()
    months = [m.strip() for m in a.months.split(",") if m.strip()] if a.months else worker_months(a.worker)
    if a.max_months:
        months = months[:a.max_months]
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / f"wam_manifest_worker{a.worker}.json"
    manifest = {"worker": a.worker, "parallelism": 2, "months": {},
                "subset_service_error": "No service available for dataset with command subset",
                "dataset_id": "cmems_mod_arc_wav_my_3km_PT1H-i",
                "version": "202511", "variables": VARS,
                "skipped": {"VTPK": "read-but-unused", "VMDR": "read-but-unused"}}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    # Coordinates/projection/mask from the first existing day of this month.
    for ym in months:
        out = OUT / ym[:4] / f"wam_{ym}.nc"
        key = ym
        if out.exists() and key in manifest["months"]:
            print(f"{a.worker}: skip completed {ym}", flush=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        y, m = ym.split("-")
        # Find first day file (all months have day 01).
        u0 = f"{BASE}/{y}/{m}/{y}{m}01_MyWam3km_hindcast-cmems.nc"
        of, f = open_remote(u0)
        lat = f["lat"][:]; lon = f["lon"][:]; rlat = f["rlat"][:]; rlon = f["rlon"][:]
        mask = (lat >= a.lat_min) & (lat <= a.lat_max) & (lon >= a.lon_min) & (lon <= a.lon_max)
        ri = np.where(mask.any(axis=1))[0]; rj = np.where(mask.any(axis=0))[0]
        proj = np.array([])
        if "projection_stere" in f:
            _p = f["projection_stere"]
            proj = _p[()] if _p.shape == () else _p[:]
        proj_attrs = {k: str(v) for k, v in f["projection_stere"].attrs.items()} if "projection_stere" in f else {}
        tunits = f["time"].attrs.get("units", "hours since 1950-01-01")
        f.close(); of.close()

        root = nc.Dataset(out, "w", format="NETCDF4")
        root.set_auto_maskandscale(False)
        root.createDimension("time", None)
        root.createDimension("rlat", len(ri))
        root.createDimension("rlon", len(rj))
        tv = root.createVariable("time", "f8", ("time",)); tv.units = tunits
        rv = root.createVariable("rlat", "f4", ("rlat",)); rv[:] = rlat[ri]
        rvv = root.createVariable("rlon", "f4", ("rlon",)); rvv[:] = rlon[rj]
        lav = root.createVariable("lat", "f4", ("rlat", "rlon")); lav[:] = lat[ri[0]:ri[-1]+1, rj[0]:rj[-1]+1]
        lov = root.createVariable("lon", "f4", ("rlat", "rlon")); lov[:] = lon[ri[0]:ri[-1]+1, rj[0]:rj[-1]+1]
        root.setncattr("dataset_id", "cmems_mod_arc_wav_my_3km_PT1H-i")
        root.setncattr("version", "202511")
        root.setncattr("subset_service_error", "No service available for dataset with command subset")
        root.setncattr("projection_stere_attrs", json.dumps(proj_attrs))
        root.setncattr("grid", "native rotated polar stereographic; rlat/rlon bbox subset")
        root.setncattr("variables_note", "VHM0/VSDX/VSDY; VTPK/VMDR intentionally skipped")
        scales = {"VHM0": (20.0/30000.0, 0.0), "VSDX": (2.0/30000.0, 0.0),
                  "VSDY": (2.0/30000.0, 0.0)}
        for v in VARS:
            sc, off = scales[v]
            var = root.createVariable(v, "i2", ("time", "rlat", "rlon"),
                                      zlib=True, complevel=4, fill_value=FILL,
                                      chunksizes=(24, min(256, len(ri)), min(256, len(rj))))
            var.set_auto_maskandscale(False)
            var.scale_factor = sc; var.add_offset = off
            var.precision_note = "Hs<=0.01 m; Stokes<=0.001 m/s"
        # Days in month
        import calendar
        ndays = calendar.monthrange(int(y), int(m))[1]
        pos = 0
        t0 = time.time()
        for day in range(1, ndays + 1):
            ud = f"{BASE}/{y}/{m}/{y}{m}{day:02d}_MyWam3km_hindcast-cmems.nc"
            okday = False
            for attempt in range(5):
                try:
                    of, f = open_remote(ud)
                    tv[pos:pos + 24] = f["time"][:]
                    for v in VARS:
                        arr = f[v][0:24, ri[0]:ri[-1] + 1, rj[0]:rj[-1] + 1].astype("f4")
                        sc, off = scales[v]
                        q = np.clip(np.round((arr - off)/sc), -32766, 32767).astype("i2")
                        q[~np.isfinite(arr)] = FILL
                        root.variables[v][pos:pos + 24, :, :] = q
                        del arr, q
                    f.close(); of.close()
                    okday = True
                    break
                except Exception as e:
                    print(f"    WARN day {ym}-{day:02d} retry {attempt+1}/5: {type(e).__name__}", flush=True)
                    time.sleep(3.0*(attempt+1))
            if not okday:
                root.close(); raise RuntimeError(f"failed day {ym}-{day:02d}")
            pos += 24
            if day % 5 == 0:
                root.sync()
                print(f"{a.worker}: {ym} day {day}/{ndays}", flush=True)
        root.close()
        size = out.stat().st_size
        entry = {"path": str(out), "size_bytes": size, "sha256": sha256(out),
                 "days": ndays, "rlat": len(ri), "rlon": len(rj),
                 "wall_s": round(time.time() - t0, 1),
                 "throughput_mb_s": round(size/1e6/max(time.time() - t0, 1), 2)}
        manifest["months"][key] = entry
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"{a.worker}: wrote {out} {size/1e6:.1f} MB", flush=True)
        if size > 3.5e9:
            print(f"{a.worker}: STOP gate >3.5 GB", flush=True)
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
