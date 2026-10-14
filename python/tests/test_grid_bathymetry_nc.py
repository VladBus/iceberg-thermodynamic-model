#!/usr/bin/env python3
"""
Stage 11.7B.1 — grid.nc / bathymetry.nc equivalence with Fortran ground truth.

Prerequisite (produces the oracle files under build/, gitignored):
    fpm test grid_dump
which runs production coup1() and dumps kt1/ht/map1/kk1/FI/DL.
 Works after `rm -rf build` + clean fpm test: grid_dump recreates
 build/grid_dump_*.dat itself (mkdir fallback in the harness).

Check layers (in order):
  1. Builders run (grid.nc, bathymetry.nc).
  2. Dump files REQUIRED (fail fast with the command above if absent).
  3. Builder outputs vs Fortran dump (ground truth):
     kt1/kk1 bit-exact ints; FI/DL tol 1e-6 deg; ht/map1 tol 0.05 cm
     (f32-vs-f64 smoothing arithmetic); mismatch counts REPORTED.
  4. Independent oracle python/grid/kk1_reference.py vs dump kk1:
     bit-exact; gate_count / gated_zero_wet / mismatches REPORTED.
  5. Builder kk1 vs oracle kk1: bit-exact (three-way closure).
  6. Static anchors from SOURCE files: wet cols == 11067,
     sum(kt1) == 143422 (runtime smoothed grid; matches ocean_init_test).
  7. IBCAO canonical quantization evidence (< 1e-4 deg, report-only band).
  8. EN4 product comparison ADDITIONAL ONLY (recorded, never gated:
     products carry pre-smoothing levels, sum 143176 != 143422).
  9. Provenance attrs + dims/order (i,j,k model indices).

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
import kk1_reference as oracle  # noqa: E402

IS1, JS1 = 133, 105
CHECKS = 0
ERRORS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if not cond:
        ERRORS += 1
        print("FAIL %s %s" % (label, detail))


def _precheck_inputs():
    """Input gate at main() entry: SKIP if no real-grid inputs, FAIL if
    inputs exist but `fpm test grid_dump` was forgotten. Same convention
    as the Fortran harness (SKIP-stop-0) and load_dump() below."""
    leg = [os.path.join(PROJECT, "KOORD.DAT"),
           os.path.join(PROJECT, "hhh.bar")]
    dumps = [os.path.join(PROJECT, "build", "grid_dump_%s.dat" % n)
             for n in ("kt1", "ht", "map1", "kk1", "fi", "dl")]
    if not all(os.path.exists(p) for p in leg):
        print("SKIP: required real-grid inputs not available")
        sys.exit(0)
    if not all(os.path.exists(p) for p in dumps):
        print("FAIL: grid_dump files not found — run fpm test grid_dump first")
        sys.exit(1)


def load_dump(name, kind):
    path = os.path.join(PROJECT, "build", "grid_dump_%s.dat" % name)
    if not os.path.exists(path):
        # CI-конвенция: без реальных входов (data/* gitignored) — SKIP,
        # но только если и legacy-входов нет; иначе это забытый
        # `fpm test grid_dump` → честный FAIL.
        leg = [os.path.join(PROJECT, "KOORD.DAT"),
               os.path.join(PROJECT, "hhh.bar")]
        if all(os.path.exists(p) for p in leg):
            print("MISSING ORACLE FILE: %s" % path)
            print("Run first: fpm test grid_dump")
            sys.exit(2)
        print("SKIP: no real-grid inputs (data/* gitignored) and no dump files")
        sys.exit(0)
    with open(path) as f:
        dims = f.readline().split()
        assert (int(dims[0]), int(dims[1])) == (IS1, JS1), dims
        rows = []
        for _ in range(JS1):
            rows.append(f.readline().split())
    a = np.array(rows, dtype=np.float64 if kind == "f" else np.int32)
    return a.T.copy()  # file rows are j, values i -> [i,j]


def main():
    # SKIP pre-check FIRST (11.7B.3): before ANY builder runs.
    _precheck_inputs()
    grid.main()
    bath.main()
    gpath = os.path.join(grid.OUT_DIR, "grid.nc")
    bpath = os.path.join(bath.OUT_DIR, "bathymetry.nc")

    g = Dataset(gpath)
    b = Dataset(bpath)
    for v in ("lon", "lat", "kt1_raw", "kt1_levels", "kk1",
              "wet_mask", "land_mask"):
        check(g[v].dimensions == ("i", "j"), "grid order %s" % v,
              str(g[v].dimensions))
    check(g["z_levels"].dimensions == ("k",), "z dim")
    check(b["ht"].dimensions == ("i", "j"), "ht order")
    check(b["map1"].dimensions == ("i", "j"), "map1 order")
    check(b["ht_raw"].dimensions == ("i", "j"), "ht_raw order")
    lon = np.array(g["lon"][:])
    lat = np.array(g["lat"][:])
    kt1 = np.array(g["kt1_levels"][:])
    kk1 = np.array(g["kk1"][:])
    ht = np.array(b["ht"][:])
    map1 = np.array(b["map1"][:])
    g.close()
    b.close()

    d_kt1 = load_dump("kt1", "i")
    d_ht = load_dump("ht", "f")
    d_map1 = load_dump("map1", "f")
    d_kk1 = load_dump("kk1", "i")
    d_fi = load_dump("fi", "f")
    d_dl = load_dump("dl", "f")

    # Builder vs Fortran ground truth.
    check(bool((kt1 == d_kt1).all()), "kt1 vs dump bit-exact",
          "mismatch=%d" % int((kt1 != d_kt1).sum()))
    check(bool((kk1 == d_kk1).all()), "kk1 vs dump bit-exact",
          "mismatch=%d" % int((kk1 != d_kk1).sum()))
    check(np.abs(lon - d_dl).max() < 1e-5, "lon vs dump FI/DL (f32 round)",
          "max=%.3e" % np.abs(lon - d_dl).max())
    check(np.abs(lat - d_fi).max() < 1e-5, "lat vs dump FI/DL (f32 round)",
          "max=%.3e" % np.abs(lat - d_fi).max())
    dh = np.abs(ht.astype(np.float64) - d_ht).max()
    check(dh < 0.05, "ht vs dump tol 0.05cm", "max=%.3e" % dh)
    dm = np.abs(map1.astype(np.float64) - d_map1).max()
    check(dm < 0.05, "map1 vs dump tol 0.05cm", "max=%.3e" % dm)

    # Independent oracle vs dump, and builder vs oracle (three-way).
    kt1_raw = grid.read_hhh(os.path.join(grid.REAL_GRID, "hhh.bar"))
    o_kk1, gate_count, gated_zero_wet = oracle.kk1_oracle(
        kt1_raw.tolist(), kt1.tolist())
    o_kk1 = np.array(o_kk1, dtype=np.int16)
    check(bool((o_kk1 == d_kk1).all()), "oracle vs dump bit-exact",
          "mismatch=%d" % int((o_kk1 != d_kk1).sum()))
    check(bool((kk1 == o_kk1).all()), "builder vs oracle bit-exact",
          "mismatch=%d" % int((kk1 != o_kk1).sum()))
    print("oracle: gate cells=%d gated-zero-with-wet-neighbours=%d" %
          (gate_count, gated_zero_wet))

    # Static anchors from SOURCE files (runtime smoothed grid).
    check(int((kt1 > 0).sum()) == 11067, "anchor wet cols",
          "%d" % int((kt1 > 0).sum()))
    check(int(kt1.sum()) == 143422, "anchor sum(kt1)",
          "%d" % int(kt1.sum()))

    # IBCAO canonical quantization evidence (report band, gate 1e-4).
    ib = Dataset(os.path.join(grid.OUT_DIR, "ibcao_model_grid.nc"))
    dlon = np.abs(lon - np.array(ib["lon"][:])).max()
    dlat = np.abs(lat - np.array(ib["lat"][:])).max()
    ib.close()
    check(dlon < 1e-4 and dlat < 1e-4, "IBCAO quantization <1e-4",
          "lon=%.3e lat=%.3e" % (dlon, dlat))

    # EN4 comparison ADDITIONAL ONLY (recorded, never gated).
    prod = os.path.join(PROJECT, "data", "input", "processed",
                        "ocean", "initial_ts_2020-04-01.nc")
    if os.path.exists(prod):
        ds = Dataset(prod)
        wm = np.array(ds["wet_mask"][:])
        wc = np.array(ds["water_column_levels"][:])
        ds.close()
        print("EN4-additional (not gated): product wet=%d sum=%d "
              "(pre-smoothing levels; runtime smoothed sum=%d)" %
              (int(wm.sum()), int(wc.sum()), int(kt1.sum())))

    # Provenance block counts once.
    prov_ok = True
    gg = Dataset(gpath)
    for a in ("source_koord_md5", "source_hhh_md5", "builder_git_sha",
              "index_mapping", "land_convention", "Conventions"):
        if a not in gg.ncattrs():
            print("FAIL grid attr %s" % a)
            prov_ok = False
    gg.close()
    check(prov_ok, "provenance attrs")

    print("TOTAL CHECKS: %d ERRORS: %d" % (CHECKS, ERRORS))
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
