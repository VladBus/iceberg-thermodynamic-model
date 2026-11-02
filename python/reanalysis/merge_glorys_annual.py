#!/usr/bin/env python3
"""Merge monthly GLORYS subsets into the 2020 annual reader file.

Preserves packed int16 variables and scale/offset; time concatenated.
Output: data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc
"""
from pathlib import Path
import json
import netCDF4 as nc
import numpy as np

MONTHS = [f"2020-{m:02d}" for m in range(1, 13)]
BASE = Path("data/input/reanalysis/glorys/2020")
OUT = BASE / "glorys12_barents_2020_daily.nc"
VARS3 = ["thetao", "so", "uo", "vo"]
VARS2 = ["zos", "siconc", "sithick", "usi", "vsi"]


def main() -> int:
    files = [BASE / f"glorys12_barents_2020_{m:02d}.nc" for m in range(1, 13)]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise SystemExit(f"missing monthly files: {missing}")
    srcs = []
    for f in files:
        d = nc.Dataset(f)
        d.set_auto_maskandscale(False)
        srcs.append(d)
    d0 = srcs[0]
    if OUT.exists():
        OUT.unlink()
    root = nc.Dataset(OUT, "w", format="NETCDF4")
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
    for d in srcs:
        n = len(d.variables["time"][:])
        tv[pos:pos + n] = d.variables["time"][:]
        for name in VARS3 + VARS2:
            root.variables[name][pos:pos + n, ...] = d.variables[name][:]
        pos += n; d.close()
    root.close()
    print(f"wrote {OUT} {OUT.stat().st_size/1e9:.3f} GB, {pos} records")
    # update manifest if present
    manp = Path("docs/validation/stage12.9_glorys_manifest.json")
    if manp.exists():
        m = json.loads(manp.read_text())
        import hashlib
        h = hashlib.sha256()
        with OUT.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        m["annual_2020"] = {"path": str(OUT), "size_bytes": OUT.stat().st_size,
                            "sha256": h.hexdigest(), "records": pos}
        manp.write_text(json.dumps(m, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
