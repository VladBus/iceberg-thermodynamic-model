#!/usr/bin/env python3
"""ERA5 forcing coverage check against the real model grid (Stage 7.6C.2).

Deterministic coverage test that mirrors the Fortran forcing interpolation
(era5_wind / era5_bilinear2d in src/wind_forcing.f90 / netcdf_input.f90):

- The model interpolates ERA5 fields at EVERY node i=1..is1(133), j=1..js1(105)
  using the model's own geographic coordinates FI(i,j) / DL(i,j).
- ERA5 latitude must strictly bracket every queried point
  (era5_bilinear2d returns ok=.false. -> forcing zeroed with a WARNING when
  lat is outside the file range). This is the ONLY hard coverage failure.
- ERA5 longitude is treated as cyclic (wrap by +-360); however points whose
  longitude lies outside the file's longitude span are edge-clamped (equivalent
  to silent extrapolation), so such points are also reported as uncovered.

The authoritative model ocean mask is the coup1()-consistent HT field
(land == kt1==0), replicated from hhh.bar exactly as grid_coupling.f90 does.

Usage
-----
    python python/era5/model_coverage.py ERA5_FILE \
        [--out-json PATH] [--verbose]

Exit code: 0 if 100% coverage of required forcing points, 1 otherwise.

Writes, when --out-json is given, a machine-readable coverage report.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import xarray as xr

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
GRID_FILE = PROJ_ROOT / "data/input/processed/grid/ibcao_model_grid.nc"

sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))
from build_initial_ice import read_hhhbar, coup1_ht  # noqa: E402


def load_model_geometry():
    """Return model node lat/lon (2D FI/DL) and the coup1-consistent wet mask."""
    ds = xr.open_dataset(GRID_FILE)
    lat = ds["lat"].values  # FI (is1, js1) degrees_north
    lon = ds["lon"].values  # DL (is1, js1) degrees_east
    ds.close()
    is1, js1 = lat.shape

    hhbfile = PROJ_ROOT / "hhh.bar"
    if not hhbfile.exists():
        hhbfile = PROJ_ROOT / "data/input/generated/real_grid" / "hhh.bar"
    if hhbfile.exists():
        kt = read_hhhbar(hhbfile)
        ht = coup1_ht(kt)
        wet = ht != 8888.0
    else:
        raise FileNotFoundError("hhh.bar not found; cannot build coup1 wet mask")
    return lat, lon, wet


def era5_extent(ds):
    """File lat/lon extent (Fortran-convention: lat increasing after flip)."""
    lat = ds["latitude"].values
    lon = ds["longitude"].values
    if lat[0] > lat[-1]:
        lat = lat[::-1]
    lat_min, lat_max = float(np.min(lat)), float(np.max(lat))
    lon_min, lon_max = float(np.min(lon)), float(np.max(lon))
    # ERA5 lon is 0..360 or -180..180; model lon is 0..360-style degrees_east.
    # Normalise both to 0..360 for comparison.
    lon_min = ((lon_min % 360.0) + 360.0) % 360.0
    lon_max = ((lon_max % 360.0) + 360.0) % 360.0
    return lat_min, lat_max, lon_min, lon_max


def covered_point(lat, lon, lat_min, lat_max, lon_min, lon_max):
    """Point-wise coverage, mirroring era5_bilinear2d acceptance.

    Latitude: must lie within [lat_min, lat_max] (hard Fortran failure if not).
    Longitude: file lon span is taken as a blocking interval (cyclic wrap is a
    separate valid path only when the file is global; for a partial-domain file
    an out-of-span longitude is edge-clamped = extrapolation, so it counts as
    uncovered).
    """
    if not (lat_min <= lat <= lat_max):
        return False
    lon_w = ((lon % 360.0) + 360.0) % 360.0
    return lon_min <= lon_w <= lon_max


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("era5_file", help="Processed/raw ERA5 NetCDF to test")
    ap.add_argument("--out-json", default=None, help="Write coverage JSON report")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    era5_file = pathlib.Path(args.era5_file)
    if not era5_file.exists():
        print(f"ERROR: {era5_file} not found")
        return 2

    lat, lon, wet = load_model_geometry()
    is1, js1 = lat.shape

    with xr.open_dataset(era5_file) as ds:
        lat_min, lat_max, lon_min, lon_max = era5_extent(ds)
        ntime = ds.sizes["valid_time"]

    # Active computational domain (i<=is=132, j<=js=104), as coup1/ikuv use it.
    active = np.zeros_like(wet, dtype=bool)
    active[:132, :104] = True
    req = wet & active  # required forcing points = active wet cells
    full_nodes = np.ones(lat.shape, dtype=bool)

    def aggregate(points, label):
        tot = int(points.sum())
        lat_ok = (lat[points] >= lat_min) & (lat[points] <= lat_max)
        lon_w = (((lon[points]) % 360.0) + 360.0) % 360.0
        lon_ok = (lon_w >= lon_min) & (lon_w <= lon_max)
        cov = lat_ok & lon_ok
        return {
            "label": label,
            "total_points": tot,
            "covered": int(cov.sum()),
            "uncovered": int((~cov).sum()),
            "uncovered_lat": int((~lat_ok).sum()),
            "uncovered_lon": int((~lon_ok).sum()),
            "coverage_pct": 100.0 * cov.sum() / tot if tot else 100.0,
        }

    full = aggregate(full_nodes, "full_model_nodes_133x105")
    reqa = aggregate(req, "required_active_wet_cells")

    print(f"ERA5 file : {era5_file}")
    print(f"ERA5 lat  : {lat_min:.3f} .. {lat_max:.3f}")
    print(f"ERA5 lon  : {lon_min:.3f} .. {lon_max:.3f}")
    print(f"model lat : {float(lat.min()):.3f} .. {float(lat.max()):.3f}")
    print(f"model lon : {float(lon.min()):.3f} .. {float(lon.max()):.3f}")
    print(f"ntime     : {ntime}")
    for agg in (reqa, full):
        print(
            f"{agg['label']}: total={agg['total_points']} "
            f"covered={agg['covered']} uncovered={agg['uncovered']} "
            f"(lat {agg['uncovered_lat']} / lon {agg['uncovered_lon']}) "
            f"{agg['coverage_pct']:.3f}%"
        )

    report = {
        "era5_file": str(era5_file),
        "era5_lat": [lat_min, lat_max],
        "era5_lon": [lon_min, lon_max],
        "model_lat": [float(lat.min()), float(lat.max())],
        "model_lon": [float(lon.min()), float(lon.max())],
        "ntime": int(ntime),
        "required": reqa,
        "full_nodes": full,
        "result": "PASS" if reqa["uncovered"] == 0 else "FAIL",
    }
    if args.out_json:
        pathlib.Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"report written: {args.out_json}")

    if args.verbose:
        print(json.dumps(report, indent=2))

    return 0 if reqa["uncovered"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
