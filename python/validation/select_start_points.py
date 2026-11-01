#!/usr/bin/env python3
"""Select Barents 2020 start points from the model grid (IBCAO-derived).

The nominal points in the Stage 12.8 brief are too shallow for a 500 m cube
(actual grid depths ~210, 122, 83 m). We select the nearest wet cells with
depth >= 480 m so all four sizes (including S500, draft ~458 m) can run, and
record the deviation explicitly.

Output: docs/validation/stage12.8_start_points.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr

GRID = Path("data/input/processed/grid/grid.nc")
GLORYS = Path("data/input/raw/reanalysis/glorys12/2020/glorys12_barents_2020_2021_monthly.nc")
OUT = Path("docs/validation/stage12.8_start_points.json")
TARGETS = [
    ("Franz Victoria Trough (Novaya Zemlya)", 77.0, 55.0),
    ("Svalbard shelf edge", 77.5, 20.0),
    ("Central Basin (Franz Josef Land)", 80.0, 50.0),
]
MIN_DEPTH = 480.0  # m; S500 draft ~458 m + margin


def main() -> int:
    ds = xr.open_dataset(GRID)
    lat = ds.lat.values.astype(float)
    lon = ds.lon.values.astype(float)
    depth = ds.kt1_raw.values.astype(float)  # m, 8=land, 3..600 wet
    lev = ds.kt1_levels.values
    # GLORYS ocean mask: require a valid temperature at ~500 m, otherwise the
    # start point is land/ice shelf in the reanalysis even if IBCAO is deep.
    gl = xr.open_dataset(GLORYS, decode_times=False, mask_and_scale=True)
    glat = gl.latitude.values.astype(float)
    glon = gl.longitude.values.astype(float)
    dep = gl.depth.values.astype(float)
    t500 = gl.thetao.isel(time=0).sel(depth=500, method="nearest").values
    points = []
    for name, la, lo in TARGETS:
        mask = (depth >= MIN_DEPTH) & (lev > 0) & \
               (np.abs(lat - la) <= 8.0) & (np.abs(lon - lo) <= 8.0)
        if not mask.any():
            raise SystemExit(f"no wet cell >= {MIN_DEPTH} m near {name}")
        idx = np.argwhere(mask)
        best = None
        for ij in idx:
            i2 = tuple(ij)
            ii = int(np.abs(glat - lat[i2]).argmin())
            jj = int(np.abs(glon - lon[i2]).argmin())
            if not np.isfinite(t500[ii, jj]):
                continue
            dd = (lat[i2] - la)**2 + (lon[i2] - lo)**2
            if best is None or dd < best[0]:
                best = (dd, i2, ii, jj)
        if best is None:
            raise SystemExit(f"no cell >= {MIN_DEPTH} m valid in both grid and GLORYS near {name}")
        dd, i2, ii, jj = best
        nominal_depth = float(depth[np.unravel_index(
            np.nanargmin((lat - la)**2 + (lon - lo)**2), depth.shape)])
        points.append({
            "name": name,
            "nominal_lat": la, "nominal_lon": lo,
            "nominal_depth_m": nominal_depth,
            "lat": float(lat[i2]), "lon": float(lon[i2]),
            "depth_m": float(depth[i2]), "levels": int(lev[i2]),
            "glorys_lat": float(glat[ii]), "glorys_lon": float(glon[jj]),
            "distance_deg": float(np.sqrt(dd)),
        })
    out = {
        "source": str(GRID),
        "selection_rule": f"nearest wet grid cell with depth >= {MIN_DEPTH} m within 8 deg",
        "note": "Nominal brief coordinates are too shallow/land for S500 and some are land/ice shelf in GLORYS; actual points require depth >= 480 m and a valid GLORYS ~500 m profile.",
        "points": points,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for p in points:
        print(f"{p['name']}: {p['lat']:.3f}N {p['lon']:.3f}E "
              f"depth={p['depth_m']:.0f} m levels={p['levels']} "
              f"(nominal {p['nominal_lat']:.1f},{p['nominal_lon']:.1f} depth={p['nominal_depth_m']:.0f})")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
