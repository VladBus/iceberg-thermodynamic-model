#!/usr/bin/env python3
"""
Stage 11.7B — bathymetry.nc builder (physical + derived depths).

Reads legacy hhh.bar (+ vertical DATA z, transcribed from
src/param.f90:310-313) and writes
data/input/processed/grid/bathymetry.nc.

Transcription (authoritative: src/grid_coupling.f90:coup1):
  - ht ladder: ht=real(kt1); borders land (incl. ht[0:15,93]);
    kt1==8 -> 8888.0; land cycles the mod loop; wet: 5<HT<=10 -> 10,
    HT<=3 -> 3, x100 -> cm. (Same code path as build_grid_nc.py;
    duplicated deliberately so each builder is self-contained.)
  - map1 (grid_coupling:250-288): 8888.0 default; interior
    (0-indexed i=1..131, j=1..103) with ANY wet ht member among the 4
    T-neighbours (i,j),(i,j-1),(i-1,j),(i-1,j-1): 0.25*sum of WET
    members ONLY (land members SKIPPED, NO renormalization).
    NOTE: not a plain mean — partial wet cells keep 0.25 weighting.

Field ownership: bathymetry.nc owns ht + map1 (+ provenance).
Masks/counts/coords live in grid.nc. hu/hv face means stay
runtime-derived (documented, not stored).

NO model code is touched. Legacy hhh.bar stays production input until
the approved dual-read transition (later 11.7 substage).
"""

import hashlib
import os
import subprocess
import time

import numpy as np
from netCDF4 import Dataset

IS1, JS1 = 133, 105
Z_CM = np.array([250., 500., 1000., 1500., 2000., 2500., 3000., 4000.,
                 5000., 7500., 10000., 15000., 20000., 25000.,
                 30000., 40000., 50000., 60000.], dtype=np.float64)
KS = 18
LAND = 8888.0
LAND_CODE = 8
EPS = 1e-8

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
REAL_GRID = os.path.join(PROJECT, "data", "input", "generated", "real_grid")
OUT_DIR = os.path.join(PROJECT, "data", "input", "processed", "grid")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_hhh(path):
    kt1 = np.zeros((IS1, JS1), dtype=np.int32)
    with open(path) as f:
        lines = f.read().split("\n")
    pos = 0
    for b in range(7):
        pos += 1
        j1, j2 = b * 15, b * 15 + 15
        for i in range(IS1):
            row = [int(x) for x in lines[pos].split()]
            assert len(row) == 15, (b, i, len(row))
            kt1[i, j1:j2] = row
            pos += 1
    return kt1


def build_ht_raw(kt1_raw):
    """ht after the mod loop (grid_coupling.f90:96-114). See build_grid_nc."""
    ht = kt1_raw.astype(np.float64)
    ht[0:15, 93] = LAND
    ht[:, 0] = LAND
    ht[:, JS1 - 1] = LAND
    ht[0, :] = LAND
    ht[kt1_raw == LAND_CODE] = LAND
    wet = ~np.isclose(ht, LAND)
    shallow = wet & (ht > 5.0) & (ht <= 10.0)
    ht[shallow] = 10.0
    low = wet & (ht <= 3.0)
    ht[low] = 3.0
    ht[wet] *= 100.0
    return ht


def build_ht_smooth(ht_raw):
    """ht smoothing (grid_coupling.f90:143-236). See build_grid_nc.

    hu(i,j)=mean(ht(i,j),ht(i,j-1)) j-adjacent; hv(i,j)=mean(ht(i,j),
    ht(i-1,j)) i-adjacent; wet-wet pairs only; edges zeroed. Then
    ht(i,j)=mean of valid faces for 0-indexed i=0..131, j=0..103.
    The ==8 skip fires on land only (stale-block counts uniform C!=8,
    proven by map1 wet count). Land keeps 8888.0.
    """
    wet = ~np.isclose(ht_raw, LAND)
    hu = np.full((IS1, JS1), LAND)
    hv = np.full((IS1, JS1), LAND)
    a = wet[:, 1:] & wet[:, :-1]
    hu[:, 1:][a] = 0.5 * (ht_raw[:, 1:][a] + ht_raw[:, :-1][a])
    b = wet[1:, :] & wet[:-1, :]
    hv[1:, :][b] = 0.5 * (ht_raw[1:, :][b] + ht_raw[:-1, :][b])
    hu[:, 0] = LAND
    hu[:, JS1 - 1] = LAND
    hv[0, :] = LAND
    hv[IS1 - 1, :] = LAND
    ht = ht_raw.copy()
    tot = np.zeros((IS1, JS1))
    cnt = np.zeros((IS1, JS1), dtype=np.int32)
    for face in (hu,
                 np.roll(hu, -1, axis=1),
                 hv,
                 np.roll(hv, -1, axis=0)):
        ok = ~np.isclose(face, LAND)
        tot += np.where(ok, face, 0.0)
        cnt += ok.astype(np.int32)
    do = np.zeros((IS1, JS1), dtype=bool)
    do[0:IS1 - 1, 0:JS1 - 1] = True
    do &= wet & (cnt > 0)
    ht[do] = tot[do] / cnt[do]
    return ht


def build_map1(ht, ht_raw):
    """Transcription of grid_coupling.f90:238-288 (float64).

    ht = SMOOTHED depths (map1 runs after smoothing); ht_raw = pre-
    smoothing depths for the land gate. Gate = all 4 ht_raw neighbours
    wet (!=8888.0), interior 0-indexed i=1..131, j=1..103 — this is what
    the :238 kk1 pre-pass tests (first-pass counts: land=8, wet=uniform
    C!=8 proven by map1 wet count; see build_grid_nc.build_kk1).
    Value = 0.25 * sum of WET (smoothed-ht) members only; 8888.0 default.
    (11.7B's "count-8 skip" reading was WRONG — corrected 11.7B.1 after
    re-tracing the stale-hht block.)
    """
    wet_raw = ~np.isclose(ht_raw, LAND, atol=EPS)
    gate = np.zeros((IS1, JS1), dtype=bool)
    gate[1:IS1 - 1, 1:JS1 - 1] = (
        wet_raw[1:IS1 - 1, 1:JS1 - 1]
        & wet_raw[0:IS1 - 2, 1:JS1 - 1]
        & wet_raw[1:IS1 - 1, 0:JS1 - 2]
        & wet_raw[0:IS1 - 2, 0:JS1 - 2])
    wet = ~np.isclose(ht, LAND, atol=EPS)
    m = np.full((IS1, JS1), LAND)
    acc = np.zeros((IS1, JS1))
    cnt = np.zeros((IS1, JS1), dtype=np.int32)
    # Members (i,j),(i,j-1),(i-1,j),(i-1,j-1): BACKWARD neighbours, i.e.
    # +1 rolls (roll(a,+1)[i,j] == a[i-1 or j-1]). Forward rolls here were
    # the 11.7B map1 defect (caught by the Fortran dump in 11.7B.1).
    for di, dj in ((0, 0), (0, 1), (1, 0), (1, 1)):
        shifted_wet = np.roll(np.roll(wet, di, axis=0), dj, axis=1)
        shifted_ht = np.roll(np.roll(ht, di, axis=0), dj, axis=1)
        acc += np.where(shifted_wet, shifted_ht, 0.0)
        cnt += shifted_wet.astype(np.int32)
    # gate already excludes borders; wrapped roll values unused there
    has = gate & (cnt > 0)
    m[has] = 0.25 * acc[has]
    return m


def main():
    hhh = os.path.join(REAL_GRID, "hhh.bar")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "bathymetry.nc")

    kt1_raw = read_hhh(hhh)
    ht_raw = build_ht_raw(kt1_raw)
    ht = build_ht_smooth(ht_raw)
    map1 = build_map1(ht, ht_raw)

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "unknown"

    with Dataset(out, "w") as ds:
        ds.createDimension("i", IS1)
        ds.createDimension("j", JS1)
        v = ds.createVariable("ht_raw", "f4", ("i", "j"), fill_value=np.nan)
        v.units = "cm"
        v.long_name = ("pre-smoothing T-point depth (mod-loop output; hu/hv "
                       "face means derive from this; future readers must "
                       "replicate hu/hv from ht_raw, not ht)")
        v[:] = ht_raw.astype(np.float32)
        v = ds.createVariable("ht", "f4", ("i", "j"), fill_value=np.nan)
        v.units, v.long_name = "cm", "T-point depth post-smoothing (8888.0 = land, epsilon rule)"
        v[:] = ht.astype(np.float32)
        v = ds.createVariable("map1", "f4", ("i", "j"), fill_value=np.nan)
        v.units = "cm"
        v.long_name = ("mean depth for cells (0.25*sum of WET members only, "
                       "8888.0 default incl. borders)")
        v[:] = map1.astype(np.float32)
        ds.Conventions = "CF-1.10"
        ds.title = "Model bathymetry: physical + derived depths (Stage 11.7B)"
        ds.index_mapping = "dimensions are MODEL INDICES (CF cell indices, not physical axes): i<->Fortran i (133), j<->Fortran j (105), k<->Fortran k (18); elementwise correspondence, NO transpose. Physical axes: model X runs along j (east), model Y runs along i (north)"
        ds.land_convention = "8888.0 with epsilon abs(x-8888)<1e-8 (never ==)"
        ds.source_hhh, ds.source_hhh_md5 = hhh, md5(hhh)
        ds.builder_git_sha, ds.created = sha, time.strftime("%Y-%m-%dT%H:%M:%S")
        ds.history = ("built by python/grid/build_bathymetry_nc.py (Stage 11.7B); "
                      "legacy hhh.bar stays production input")
        ds.eos_note = "EOS-agnostic (bathymetry carries no EOS state); legacy EOS default untouched"

    wet = ~np.isclose(ht, LAND)
    print("bathymetry.nc written: %s" % out)
    print("  wet T-cells: %d; ht wet range: %.1f .. %.1f cm" %
          (int(wet.sum()), ht[wet].min(), ht[wet].max()))
    print("  map1 wet cells: %d" % int((~np.isclose(map1, LAND)).sum()))


if __name__ == "__main__":
    main()
