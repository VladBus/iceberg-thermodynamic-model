#!/usr/bin/env python3
"""Merge monthly GLORYS subsets into an annual reader file.

Preserves packed int16 variables and scale/offset; time concatenated.
Usage: python python/reanalysis/merge_glorys_annual.py --year 2024
"""
from pathlib import Path
import argparse
import hashlib
import json
import netCDF4 as nc
import numpy as np

VARS3 = ["thetao", "so", "uo", "vo"]
VARS2 = ["zos", "siconc", "sithick", "usi", "vsi"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, choices=(2020, 2024), default=2020)
    args = parser.parse_args()
    year = args.year
    base = Path("data/input/reanalysis/glorys") / str(year)
    out_path = base / f"glorys12_barents_{year}_daily.nc"
    files = [base / f"glorys12_barents_{year}_{m:02d}.nc" for m in range(1, 13)]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise SystemExit(f"missing monthly files: {missing}")
    srcs = []
    for f in files:
        d = nc.Dataset(f)
        d.set_auto_maskandscale(False)
        srcs.append(d)
    d0 = srcs[0]
    if out_path.exists():
        out_path.unlink()
    root = nc.Dataset(out_path, "w", format="NETCDF4")
    root.set_auto_maskandscale(False)
    root.createDimension("time", None)
    for name in ("depth", "latitude", "longitude"):
        root.createDimension(name, len(d0.dimensions[name]))
    tv = root.createVariable("time", "f8", ("time",))
    tv.units = d0.variables["time"].units; tv.calendar = "gregorian"
    for name in ("depth", "latitude", "longitude"):
        v = root.createVariable(name, "f4", (name,))
        v.units = d0.variables[name].units
        if name == "depth": v.positive = "down"
        v[:] = d0.variables[name][:]
    for name in VARS3 + VARS2:
        a = d0.variables[name]
        dims = ("time", "depth", "latitude", "longitude") if name in VARS3 else \
               ("time", "latitude", "longitude")
        var = root.createVariable(name, "i2", dims, zlib=True, complevel=4,
                                  fill_value=np.int16(-32767),
                                  chunksizes=(1,) + tuple(root.dimensions[x].size for x in dims[1:]))
        var.set_auto_maskandscale(False)
        var.scale_factor = float(a.scale_factor); var.add_offset = float(a.add_offset)
    pos = 0
    chunk = 5
    for d in srcs:
        n = len(d.variables["time"][:])
        for t0 in range(0, n, chunk):
            t1 = min(n, t0 + chunk)
            tv[pos + t0:pos + t1] = d.variables["time"][t0:t1]
            for name in VARS3 + VARS2:
                root.variables[name][pos + t0:pos + t1, ...] = d.variables[name][t0:t1, ...]
        pos += n
        d.close()
    root.close()
    print(f"wrote {out_path} {out_path.stat().st_size/1e9:.3f} GB, {pos} records")
    # update manifest if present
    manp = Path("docs/validation/stage12.9_glorys_manifest.json")
    if manp.exists():
        m = json.loads(manp.read_text())
        h = hashlib.sha256()
        with out_path.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        m[f"annual_{year}"] = {"path": str(out_path), "size_bytes": out_path.stat().st_size,
                               "sha256": h.hexdigest(), "records": pos}
        manp.write_text(json.dumps(m, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
