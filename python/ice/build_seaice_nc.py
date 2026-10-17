#!/usr/bin/env python3
import pathlib
"""
Stage 11.7D — seaice_initial.nc builder (sea-ice initialization).

Reads legacy 1_1.ice through 1_5.ice files (category area fractions)
and writes data/input/processed/ice/seaice_initial.nc with CF-1.10
metadata.

Transcription rules (authoritative: src/ice_redis.f90 + app/main.f90):
  - 1_1.ice .. 1_5.ice: text format, 133 rows × 105 cols, per-row
    list-directed (an1(i,j,k), j=1..js1), i=1..is1, k=2..6.
    k=1: open water fraction; k=2..6: categories 1..5.
    9.99 → 0.0 (missing), ≥1.0 → 1.0 clamp; Σ an1 ≤ 1.
  - wice1 = HST × an1 (HST = [0.20, 0.40, 0.95, 1.60, 2.50] m).
  - redis() conservative redistribution called after init.
  - Category boundaries (HMAX): [0.3, 0.7, 1.2, 2.0, 50.0] m.
  - ngr = 5 categories; ngr2 = 4 boundaries.
  - Only January data exists (reused for other months — known gap).

Field ownership: seaice_initial.nc owns sic, sit, snow_depth.
CF-1.10 metadata, provenance, dimension names (cat, j, i).
"""

import argparse
import hashlib
import os
import subprocess
import time

import numpy as np
from netCDF4 import Dataset

IS1, JS1 = 133, 105
NGR = 5  # categories

# HST — characteristic thickness of 5 ice categories [m]
HST = np.array([0.20, 0.40, 0.95, 1.60, 2.50], dtype=np.float64)
# HMAX — upper thickness boundaries for category transition [m]
HMAX = np.array([0.3, 0.7, 1.2, 2.0, 50.0], dtype=np.float64)

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
REAL_GRID = os.path.join(PROJECT, "data", "input", "generated", "real_grid")
OUT_DIR = os.path.join(PROJECT, "data", "input", "processed", "ice")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_ice_files():
    """Read 1_1.ice .. 1_5.ice from real_grid directory."""
    an1 = np.zeros((NGR + 1, IS1, JS1), dtype=np.float64)  # k=0..5
    for k in range(1, NGR + 1):
        fpath = os.path.join(REAL_GRID, f"1_{k}.ice")
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Missing ice file: {fpath}")
        with open(fpath) as f:
            vals = f.read().split()
        if len(vals) != IS1 * JS1:
            raise ValueError(f"1_{k}.ice: expected {IS1*JS1} values, got {len(vals)}")
        arr = np.array(vals, dtype=np.float64).reshape((JS1, IS1)).T.copy()  # [i,j]
        an1[k, :, :] = arr
    return an1


def build_sic_sit(an1):
    """Compute sic (area fraction) and sit (thickness) from an1 and HST."""
    # an1[1..5, i, j] are category area fractions
    sic = an1[1:, :, :].astype(np.float32)  # [cat, i, j]
    # sit = hst * an1 (m), zero where an1 == 0
    sit = np.zeros((NGR, IS1, JS1), dtype=np.float32)
    for cat in range(NGR):
        sit[cat, :, :] = HST[cat] * an1[cat + 1, :, :].astype(np.float32)
    # Transpose to (cat, j, i) for NetCDF (cat, j, i) order
    return sic.transpose(0, 2, 1), sit.transpose(0, 2, 1)


def build_snow_depth():
    """Snow depth per category — currently all zero (no snow data)."""
    return np.zeros((NGR, JS1, IS1), dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(
        description="Build seaice_initial.nc from 1_1.ice..1_5.ice")
    parser.add_argument("--out", type=pathlib.Path, required=True,
                        help="Output seaice_initial.nc path")
    parser.add_argument("--json", type=pathlib.Path,
                        help="Optional JSON stats output")
    args = parser.parse_args()

    an1 = read_ice_files()
    sic, sit = build_sic_sit(an1)
    snow = build_snow_depth()

    os.makedirs(OUT_DIR, exist_ok=True)
    out = args.out

    # Validation stats
    wet = (np.sum(an1[1:, :, :], axis=0) > 0).sum()
    total_ice_vol = np.sum(sit).item()
    print(f"wet cells: {wet}; total ice volume: {total_ice_vol:.3e} m^3")

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "unknown"

    with Dataset(args.out, "w") as ds:
        ds.createDimension("cat", NGR)
        ds.createDimension("j", JS1)
        ds.createDimension("i", IS1)

        # sic: sea ice concentration per category
        v = ds.createVariable("sic", "f4", ("cat", "j", "i"), fill_value=np.nan)
        v.units = "1"
        v.long_name = "sea ice concentration per category"
        v[:] = sic

        # sit: sea ice thickness per category
        v = ds.createVariable("sit", "f4", ("cat", "j", "i"), fill_value=np.nan)
        v.units = "m"
        v.long_name = "sea ice thickness per category"
        v[:] = sit

        # snow_depth: snow thickness per category
        v = ds.createVariable("snow_depth", "f4", ("cat", "j", "i"), fill_value=np.nan)
        v.units = "m"
        v.long_name = "snow thickness per category"
        v[:] = snow

        # Category bounds
        v = ds.createVariable("hst", "f8", ("cat",))
        v.units = "m"
        v.long_name = "characteristic thickness of ice categories"
        v[:] = HST

        v = ds.createVariable("hmax", "f8", ("cat",))
        v.units = "m"
        v.long_name = "upper thickness bound of ice categories"
        v[:] = HMAX

        ds.Conventions = "CF-1.10"
        ds.title = "Sea-ice initial state: concentration, thickness, snow"
        ds.index_mapping = ("dimensions are MODEL INDICES (CF cell indices): "
                            "cat<->category (5), j<->Fortran j (105), i<->Fortran i (133); "
                            "elementwise correspondence, NO transpose")
        ds.source_files = ", ".join([f"1_{k}.ice" for k in range(1, NGR + 1)])
        ds.builder_git_sha, ds.created = sha, time.strftime("%Y-%m-%dT%H:%M:%S")
        # Source from EXPLICIT manifest (11.7E Phase 0.1) — NEVER inferred
        # from data values. Manifest: python/ice/seaice_source_manifest.json.
        manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "seaice_source_manifest.json")
        try:
            import json
            with open(manifest_path) as mf:
                manifest = json.load(mf)
            stype = manifest.get("source_type", "")
            if stype == "diagnostic_placeholder":
                ds.source = "DIAGNOSTIC_PLACEHOLDER"
                ds.sea_ice_status = "DIAGNOSTIC"
            elif stype == "scientific":
                ds.source = "%s %s %s" % (manifest.get("dataset_name", "?"),
                                          manifest.get("version", "?"),
                                          manifest.get("date", "?"))
                ds.sea_ice_status = "SCIENTIFIC"
            else:
                ds.source = "UNKNOWN"
                ds.sea_ice_status = "UNKNOWN"
            ds.source_manifest = str(manifest)
        except Exception:
            ds.source = "UNKNOWN"
            ds.sea_ice_status = "UNKNOWN"
        ds.history = ("built by python/ice/build_seaice_nc.py (Stage 11.7D); "
                      "legacy 1_1.ice..1_5.ice stay production inputs")
        ds.ice_note = ("Only January data available; other months reuse "
                       "January init (known gap, 11.7A).")

    print("seaice_initial.nc written:", args.out)

    if args.json:
        import json
        stats = {
            "wet_cells": int(np.sum(sic > 0)),
            "total_ice_volume_m3": float(np.sum(sit)),
        }
        with open(args.json, "w") as f:
            json.dump(stats, f, indent=2)


if __name__ == "__main__":
    import pathlib
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()