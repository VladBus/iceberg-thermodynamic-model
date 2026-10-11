#!/usr/bin/env python3
"""
Stage 11.7B — grid.nc builder (coordinates + masks + level counts).

Reads legacy KOORD.DAT + hhh.bar (+ vertical DATA z, transcribed from
src/param.f90:310-313) and writes data/input/processed/grid/grid.nc.

Transcription rules (authoritative: src/grid_coupling.f90:coup1 + writer
python/grid/build_real_grid_inputs.py):
  - KOORD.DAT: 2 list-directed records (FI=lat °N, DL=lon °E), each
    133x105 float32 4-decimal, Fortran column-major (i fastest).
    Q1 RESOLVED (writer lines 119-120,144-145 + round-trip 310-328).
  - hhh.bar: 7 blocks x (header + 133 lines x 15I5), KT1 codes
    (8=land, 3..600 = depth metres, from IBCAO depth round+clip[3,600]).
  - ht ladder: ht=real(kt1); borders land (incl. ht[0:15,93]);
    kt1==8 -> 8888.0; land cycles the mod loop; wet: 5<HT<=10 -> 10,
    HT<=3 -> 3, x100 -> cm.
  - kt1-final (AUTHORITATIVE second pass, grid_coupling:317-329):
    0 default; land (8888.0) stays 0; wet max{k: z(k)<=HT}.
  - kk1-01 (grid_coupling:238-246): 1 iff all 4 T-neighbours' RAW kt1 != 8
    (i=2..is, j=2..js 1-indexed); kk1-min (:410-428): min of 4 kt1-final,
    borders 0.
  - z DATA (cm, centers, surface->bottom): 250,500,1000,1500,2000,2500,
    3000,4000,5000,7500,10000,15000,20000,25000,30000,40000,50000,60000.

Field ownership: grid.nc owns coordinates + integer codes/counts/masks.
Depths (ht/map1) live in bathymetry.nc (build_bathymetry_nc.py).
Index mapping: netCDF dim x<->Fortran i (133), y<->Fortran j (105);
arrays stored (x,y) C-order == elementwise model correspondence
(NO transpose: file (i,j) layout matches model (i,j)).

NO model code is touched by this builder. Legacy files stay production
inputs until the approved dual-read transition (later 11.7 substage).
"""

import hashlib
import os
import subprocess
import time

import numpy as np
from netCDF4 import Dataset

IS1, JS1, KS = 133, 105, 18
LAND = 8888.0
LAND_CODE = 8

# Transcribed from src/param.f90:310-313 (DATA z, cm, centers top->bottom).
Z_CM = np.array([250., 500., 1000., 1500., 2000., 2500., 3000., 4000.,
                 5000., 7500., 10000., 15000., 20000., 25000.,
                 30000., 40000., 50000., 60000.], dtype=np.float64)

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
REAL_GRID = os.path.join(PROJECT, "data", "input", "generated", "real_grid")
OUT_DIR = os.path.join(PROJECT, "data", "input", "processed", "grid")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_koord(path):
    """Two list-directed records of 133x105 reals, Fortran order (i fastest)."""
    with open(path) as f:
        tokens = f.read().split()
    vals = np.array(tokens, dtype=np.float64)
    assert vals.size == 2 * IS1 * JS1, vals.size
    fi = vals[:IS1 * JS1].reshape((JS1, IS1)).T.copy()  # [i,j] == fi(i,j)
    dl = vals[IS1 * JS1:].reshape((JS1, IS1)).T.copy()
    return fi, dl


def read_hhh(path):
    """7 blocks: header line + 133 lines of 15I5; block b -> j1..j2 (0-idx)."""
    kt1 = np.zeros((IS1, JS1), dtype=np.int32)
    with open(path) as f:
        lines = f.read().split("\n")
    pos = 0
    for b in range(7):
        pos += 1  # header line
        j1, j2 = b * 15, b * 15 + 15
        for i in range(IS1):
            row = [int(x) for x in lines[pos].split()]
            assert len(row) == 15, (b, i, len(row))
            kt1[i, j1:j2] = row
            pos += 1
    return kt1


def build_ht_raw(kt1_raw):
    """ht after the mod loop (grid_coupling.f90:96-114), pre-smoothing.

    ht=real(kt1); forced-land borders (:82-85: segment 0-indexed [0:15,93],
    j=0/j=104 rows, i=0 col; the i=132 col is NOT forced and stays wet);
    kt1==8 -> 8888.0; land cycles; wet 5<HT<=10 -> 10, HT<=3 -> 3, x100->cm.
    """
    ht = kt1_raw.astype(np.float64)
    ht[0:15, 93] = LAND
    ht[:, 0] = LAND
    ht[:, JS1 - 1] = LAND
    ht[0, :] = LAND
    land = kt1_raw == LAND_CODE
    ht[land] = LAND
    wet = ~np.isclose(ht, LAND)
    shallow = wet & (ht > 5.0) & (ht <= 10.0)
    ht[shallow] = 10.0
    low = wet & (ht <= 3.0)
    ht[low] = 3.0
    ht[wet] *= 100.0
    return ht


def build_ht_smooth(ht_raw, kt1_raw):
    """ht smoothing (grid_coupling.f90:143-236, float64 transcription).

    hu/hv face means from ht_raw (wet-wet pairs only, else 8888; edges
    zeroed); then ht(i,j) = mean of valid faces for i=0..131, j=0..103,
    SKIPPING cells whose stale-block kt1 == 8. The stale-hht block
    (:180-196) sets land kt1=8 and all wet cells to one uniform garbage
    count C (same uninitialized hht for every cell); observed model
    behaviour (map1 wet ~10957, not ~0) PROVES C != 8, hence the skip
    fires exactly on land — i.e. all wet cells are smoothed. (If C were
    8, kk1/map1 would be near-empty, contradicting the running model.)
    Land cells keep 8888.0 (all 4 adjacent faces involve the land cell
    itself, so valid_count is always 0).
    """
    wet = ~np.isclose(ht_raw, LAND)
    hu = np.full((IS1, JS1), LAND)
    hv = np.full((IS1, JS1), LAND)
    # hu(i,j) = mean(ht(i,j), ht(i,j-1)): j-adjacent (0-indexed j>=1)
    a = wet[:, 1:] & wet[:, :-1]
    hu[:, 1:][a] = 0.5 * (ht_raw[:, 1:][a] + ht_raw[:, :-1][a])
    # hv(i,j) = mean(ht(i,j), ht(i-1,j)): i-adjacent (0-indexed i>=1)
    b = wet[1:, :] & wet[:-1, :]
    hv[1:, :][b] = 0.5 * (ht_raw[1:, :][b] + ht_raw[:-1, :][b])
    hu[:, 0] = LAND
    hu[:, JS1 - 1] = LAND
    hv[0, :] = LAND
    hv[IS1 - 1, :] = LAND
    ht = ht_raw.copy()
    region = np.zeros((IS1, JS1), dtype=bool)
    region[0:IS1 - 1, 0:JS1 - 1] = True
    # Fortran hu(i,j)/(i,j-1) and hv(i,j)/(i-1,j) neighbour layout in
    # 0-indexed (i,j): faces hu[i,j], hu[i,j+1], hv[i,j], hv[i+1,j].
    tot = np.zeros((IS1, JS1))
    cnt = np.zeros((IS1, JS1), dtype=np.int32)
    for face in (hu,
                 np.roll(hu, -1, axis=1),
                 hv,
                 np.roll(hv, -1, axis=0)):
        ok = ~np.isclose(face, LAND)
        tot += np.where(ok, face, 0.0)
        cnt += ok.astype(np.int32)
    do = region & wet & (cnt > 0)
    ht[do] = tot[do] / cnt[do]
    return ht


def build_kt1_final(ht):
    """Authoritative second pass (grid_coupling:317-329)."""
    kt1 = np.zeros((IS1, JS1), dtype=np.int16)
    wet = ~np.isclose(ht, LAND)
    for k in range(KS):
        kt1[wet & (Z_CM[k] <= ht)] = k + 1
    return kt1


def build_kk1(kt1_final, ht_raw):
    """Two-stage kk1 (grid_coupling.f90:238-246 + :410-428).

    Stage 1 (:238 gate): kk1=1 for interior cells whose FOUR first-pass
    counts are all != 8. First-pass counts: land -> 8 (stale-block else),
    wet -> uniform garbage C. Observed model behaviour PROVES C != 8
    (map1 wet ~10957 cells; C==8 would zero kk1/map1 almost everywhere),
    hence the gate is exactly the land gate: all four ht_raw neighbours
    wet (!=8888.0). Documented, not assumed silently.
    Stage 2 (:410 min): where gate passed, kk1 = min of the 4 FINAL kt1
    neighbours; borders (i/j edges) forced 0 (:425-428).
    """
    wet = ~np.isclose(ht_raw, LAND)
    gate = np.zeros((IS1, JS1), dtype=bool)
    gate[1:IS1 - 1, 1:JS1 - 1] = (
        wet[1:IS1 - 1, 1:JS1 - 1] & wet[0:IS1 - 2, 1:JS1 - 1]
        & wet[1:IS1 - 1, 0:JS1 - 2] & wet[0:IS1 - 2, 0:JS1 - 2])
    kk1 = np.zeros((IS1, JS1), dtype=np.int16)
    ki = kt1_final.astype(np.int32)
    kmin = np.minimum(np.minimum(ki, np.roll(ki, 1, axis=0)),
                      np.minimum(np.roll(ki, 1, axis=1),
                                 np.roll(np.roll(ki, 1, axis=0), 1, axis=1)))
    kk1[gate] = kmin[gate]
    return kk1, gate


def main():
    koord = os.path.join(REAL_GRID, "KOORD.DAT")
    hhh = os.path.join(REAL_GRID, "hhh.bar")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "grid.nc")

    fi, dl = read_koord(koord)
    kt1_raw = read_hhh(hhh)
    ht_raw = build_ht_raw(kt1_raw)
    ht = build_ht_smooth(ht_raw, kt1_raw)
    kt1 = build_kt1_final(ht)
    kk1, kk1_gate = build_kk1(kt1, ht_raw)
    wet_mask = (kt1 > 0).astype(np.int8)
    land_mask = (kt1 == 0).astype(np.int8)

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "unknown"

    with Dataset(out, "w") as ds:
        ds.createDimension("i", IS1)
        ds.createDimension("j", JS1)
        ds.createDimension("k", KS)
        v = ds.createVariable("lon", "f8", ("i", "j"))
        v.units, v.long_name = "degrees_east", "longitude (DL, 0-indexed [x=i,y=j])"
        v[:] = dl
        v = ds.createVariable("lat", "f8", ("i", "j"))
        v.units, v.long_name = "degrees_north", "latitude (FI, 0-indexed [x=i,y=j])"
        v[:] = fi
        v = ds.createVariable("kt1_raw", "i2", ("i", "j"))
        v.long_name = "hhh.bar integer codes (8=land, 3..600=depth m)"
        v[:] = kt1_raw
        v = ds.createVariable("kt1_levels", "i1", ("i", "j"))
        v.long_name = "final wet vertical-level count (0=land), authoritative 2nd pass"
        v[:] = kt1.astype(np.int8)
        v = ds.createVariable("kk1", "i1", ("i", "j"))
        v.long_name = "velocity-cell active levels = min of 4 kt1 (0 if any land)"
        v[:] = kk1.astype(np.int8)
        v = ds.createVariable("wet_mask", "i1", ("i", "j"))
        v.long_name = "1 where kt1_levels>0"
        v[:] = wet_mask
        v = ds.createVariable("land_mask", "i1", ("i", "j"))
        v.long_name = "1 where kt1_levels==0"
        v[:] = land_mask
        v = ds.createVariable("z_levels", "f8", ("k",))
        v.units, v.long_name = "cm", "Z-level centers surface->bottom (transcribed param.f90 DATA z)"
        v[:] = Z_CM
        ds.Conventions = "CF-1.10"
        ds.title = "Model grid: coordinates, masks, level counts (Stage 11.7B)"
        ds.index_mapping = "dimensions are MODEL INDICES (CF cell indices, not physical axes): i<->Fortran i (133), j<->Fortran j (105), k<->Fortran k (18); elementwise correspondence, NO transpose. Physical axes: model X runs along j (east), model Y runs along i (north)"
        ds.land_convention = "land = 8888.0 with epsilon abs(x-8888)<1e-8 (never ==); stored masks are authoritative"
        ds.crs = "IBCAO Polar Stereographic, DX=DY=1389000 cm"
        ds.source_koord, ds.source_hhh = koord, hhh
        ds.source_koord_md5, ds.source_hhh_md5 = md5(koord), md5(hhh)
        ds.builder_git_sha, ds.created = sha, time.strftime("%Y-%m-%dT%H:%M:%S")
        ds.history = "built by python/grid/build_grid_nc.py (Stage 11.7B); legacy KOORD.DAT/hhh.bar stay production inputs"
        ds.eos_note = "EOS-agnostic (grid carries no EOS state); legacy EOS default untouched"

    print("grid.nc written: %s" % out)
    print("  wet columns (kt1>0): %d; 3D wet levels sum(kt1): %d" %
          (int(wet_mask.sum()), int(kt1.sum())))
    print("  lon range: %.4f .. %.4f; lat range: %.4f .. %.4f" %
          (dl.min(), dl.max(), fi.min(), fi.max()))


if __name__ == "__main__":
    main()
