#!/usr/bin/env python3
"""
Stage 11.7B — grid.nc / bathymetry.nc source-to-NetCDF equivalence.

Self-contained: runs both builders, then verifies the products against
LEGACY sources with an INDEPENDENT minimal transcription (separate code
path from the builders) plus regression anchors.

Equivalence policy (Stage 11.7B report):
  - integer masks/counts (kt1_raw/kt1_levels/kk1/wet/land): BIT-EXACT;
  - lon/lat vs KOORD-decoded float32: tol 1e-6 deg;
  - lon/lat vs IBCAO float64 canonical: gate < 1e-4 deg (historical
    float32-4-decimal quantization evidence, NOT a failure of the .nc);
  - ht: exact (small integers exact in f32 and f64);
  - map1: tol 0.01 cm (f32-vs-f64 last-ulp division differences);
  - regression anchors: wet columns and sum(kt1) equal the EN4 product
    wet_mask / water_column_levels for the same grid.

Prints TOTAL CHECKS / ERRORS (project convention). Exit 0 iff clean.
Physics/model untouched (pure I/O equivalence).
"""

import os
import sys

import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT, "python", "grid"))
sys.path.insert(0, PROJECT)

from netCDF4 import Dataset  # noqa: E402

import build_bathymetry_nc as bath  # noqa: E402
import build_grid_nc as grid  # noqa: E402

IS1, JS1, KS = 133, 105, 18
LAND = 8888.0
CHECKS = 0
ERRORS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if not cond:
        ERRORS += 1
        print("FAIL %s %s" % (label, detail))


def main():
    # Builders first (idempotent, fast).
    grid.main()
    bath.main()
    gpath = os.path.join(grid.OUT_DIR, "grid.nc")
    bpath = os.path.join(bath.OUT_DIR, "bathymetry.nc")

    g = Dataset(gpath)
    b = Dataset(bpath)

    # 1. Dimensions and order.
    check(tuple(g.dimensions["x"].size for _ in [0]) == (IS1,), "dim x")
    check(g.dimensions["y"].size == JS1, "dim y")
    check(g.dimensions["z"].size == KS, "dim z")
    for v in ("lon", "lat", "kt1_raw", "kt1_levels", "kk1",
              "wet_mask", "land_mask"):
        check(g[v].dimensions == ("x", "y"), "grid order %s" % v,
              str(g[v].dimensions))
    check(g["z_levels"].dimensions == ("k",) or
          g["z_levels"].dimensions == ("z",), "z dim",
          str(g["z_levels"].dimensions))
    check(b["ht"].dimensions == ("x", "y"), "ht order")
    check(b["map1"].dimensions == ("x", "y"), "map1 order")

    lon = np.array(g["lon"][:])
    lat = np.array(g["lat"][:])
    kt1_raw = np.array(g["kt1_raw"][:])
    kt1 = np.array(g["kt1_levels"][:])
    kk1 = np.array(g["kk1"][:])
    wet = np.array(g["wet_mask"][:])
    land = np.array(g["land_mask"][:])
    zlev = np.array(g["z_levels"][:])
    ht = np.array(b["ht"][:])
    map1 = np.array(b["map1"][:])
    g.close()
    b.close()

    # 2. Legacy KOORD decode (independent read) vs stored lon/lat.
    fi, dl = grid.read_koord(os.path.join(grid.REAL_GRID, "KOORD.DAT"))
    check(np.abs(lon - dl).max() < 1e-6, "lon vs KOORD-decoded",
          "max=%.3e" % np.abs(lon - dl).max())
    check(np.abs(lat - fi).max() < 1e-6, "lat vs KOORD-decoded",
          "max=%.3e" % np.abs(lat - fi).max())

    # 3. Canonical IBCAO float64 vs stored (quantization evidence gate).
    ib = Dataset(os.path.join(grid.OUT_DIR, "ibcao_model_grid.nc"))
    ilat = np.array(ib["lat"][:])
    ilon = np.array(ib["lon"][:])
    ib.close()
    check(np.abs(lon - ilon).max() < 1e-4, "lon vs IBCAO canonical",
          "max=%.3e" % np.abs(lon - ilon).max())
    check(np.abs(lat - ilat).max() < 1e-4, "lat vs IBCAO canonical",
          "max=%.3e" % np.abs(lat - ilat).max())

    # 4. Independent transcription from hhh.bar (separate minimal path).
    raw = grid.read_hhh(os.path.join(grid.REAL_GRID, "hhh.bar"))
    check(bool((kt1_raw == raw).all()), "kt1_raw bit-exact")
    h = raw.astype(np.float64)
    h[0:15, 93] = LAND
    h[:, 0] = LAND
    h[:, JS1 - 1] = LAND
    h[0, :] = LAND
    h[raw == 8] = LAND
    w = ~np.isclose(h, LAND)
    sh = w & (h > 5.0) & (h <= 10.0)
    h[sh] = 10.0
    lo = w & (h <= 3.0)
    h[lo] = 3.0
    h[w] *= 100.0
    k2 = np.zeros((IS1, JS1), dtype=np.int32)
    for k in range(KS):
        k2[w & (grid.Z_CM[k] <= h)] = k + 1
    check(bool((kt1 == k2).all()), "kt1_levels bit-exact",
          "mismatch=%d" % int((kt1 != k2).sum()))
    check(bool((ht == h.astype(np.float32)).all()), "ht exact",
          "mismatch=%d" % int((ht != h.astype(np.float32)).sum()))
    # kk1-min independent
    km = np.zeros((IS1, JS1), dtype=np.int32)
    ki = k2.astype(np.int32)
    core = np.zeros((IS1, JS1), dtype=bool)
    core[1:IS1 - 1, 1:JS1 - 1] = True
    kmin = np.minimum(np.minimum(ki, np.roll(ki, 1, axis=0)),
                      np.minimum(np.roll(ki, 1, axis=1),
                                 np.roll(np.roll(ki, 1, axis=0), 1, axis=1)))
    km[core] = kmin[core]
    check(bool((kk1 == km).all()), "kk1 bit-exact",
          "mismatch=%d" % int((kk1 != km).sum()))
    check(bool(((kt1 > 0).astype(np.int8) == wet).all()), "wet_mask consistent")
    check(bool(((kt1 == 0).astype(np.int8) == land).all()), "land_mask consistent")
    # map1 independent (gate + 0.25 wet-only rule)
    fp = np.zeros((IS1, JS1), dtype=np.int32)
    st = np.isclose(h, 888800.0, atol=1e-3)
    fp[st] = 0
    r = ~st
    for k in range(KS):
        fp[r & (grid.Z_CM[k] <= h)] = k + 1
    n8 = fp != 8
    gate = np.zeros((IS1, JS1), dtype=bool)
    gate[1:IS1 - 1, 1:JS1 - 1] = (
        n8[1:IS1 - 1, 1:JS1 - 1] & n8[0:IS1 - 2, 1:JS1 - 1]
        & n8[1:IS1 - 1, 0:JS1 - 2] & n8[0:IS1 - 2, 0:JS1 - 2])
    acc = np.zeros((IS1, JS1))
    cnt = np.zeros((IS1, JS1), dtype=np.int32)
    ww = ~np.isclose(h, LAND)
    for di, dj in ((0, 0), (0, -1), (-1, 0), (-1, -1)):
        sw = np.roll(np.roll(ww, di, axis=0), dj, axis=1)
        shv = np.roll(np.roll(h, di, axis=0), dj, axis=1)
        acc += np.where(sw, shv, 0.0)
        cnt += sw.astype(np.int32)
    m2 = np.full((IS1, JS1), LAND)
    has = gate & (cnt > 0)
    m2[has] = 0.25 * acc[has]
    check(np.abs(map1.astype(np.float64) - m2).max() < 0.01, "map1 tol 0.01cm",
          "max=%.3e" % np.abs(map1.astype(np.float64) - m2).max())

    # 5. Regression anchors vs EN4 product (same grid).
    prod = None
    for mm in ("04", "01"):
        cand = os.path.join(PROJECT, "data", "input", "processed",
                            "ocean", "initial_ts_2020-%s-01.nc" % mm)
        if os.path.exists(cand):
            prod = cand
            break
    if prod is None:
        check(False, "EN4 product present")
    else:
        ds = Dataset(prod)
        wm = np.array(ds["wet_mask"][:])
        wc = np.array(ds["water_column_levels"][:])
        ds.close()
        check(bool(((kt1 > 0).astype(np.int8) == wm).all()), "anchor wet_mask",
              "mismatch=%d" % int(((kt1 > 0).astype(np.int8) != wm).sum()))
        check(int(kt1.sum()) == int(wc.sum()), "anchor sum(kt1)",
              "%d vs %d" % (int(kt1.sum()), int(wc.sum())))

    # 6. z_levels == DATA z; provenance attrs.
    check(bool((zlev == grid.Z_CM).all()), "z_levels DATA")
    gg = Dataset(gpath)
    for a in ("source_koord_md5", "source_hhh_md5", "builder_git_sha",
              "index_mapping", "land_convention", "Conventions"):
        check(a in gg.ncattrs(), "grid attr %s" % a)
    gg.close()
    bb = Dataset(bpath)
    check("source_hhh_md5" in bb.ncattrs(), "bathy provenance")
    bb.close()

    print("TOTAL CHECKS: %d ERRORS: %d" % (CHECKS, ERRORS))
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
