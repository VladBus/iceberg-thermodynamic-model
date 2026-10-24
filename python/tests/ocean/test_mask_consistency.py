#!/usr/bin/env python3
"""T3-CORRECTIVE: EN4 product/runtime wet-mask consistency test.
Verifies all 8 products carry water_column_levels == the authoritative runtime
kt1 (build/grid_dump_kt1.dat), no (T=0,S=0) unfilled pairs and no S<=0 in wet
cells. SKIP without data. Output: data/validation/mask_consistency_result.json
"""
import json, sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
OCEAN = PROJECT / "data/input/processed/ocean"
DUMP = PROJECT / "build/grid_dump_kt1.dat"
OUT = PROJECT / "data/validation/mask_consistency_result.json"
SEASONS = ["2020-01-01", "2020-04-01", "2020-07-01", "2020-10-01"]
Z = [2.5,5,10,15,20,25,30,40,50,75,100,150,200,250,300,400,500,600]

def main():
    products = [OCEAN / f"initial_ts_{d}{s}.nc" for d in SEASONS for s in ("", "_rebuild")]
    if not DUMP.exists() or not all(p.exists() for p in products):
        print("SKIP: products or runtime mask dump absent (data bundle not in CI).")
        return 0
    kt = np.loadtxt(DUMP, skiprows=1)
    if kt.shape == (105, 133):
        kt = kt.T
    checks = []
    files = {}
    for p in products:
        d = Dataset(p)
        lev = np.asarray(d["water_column_levels"][:], dtype=np.int64)
        T = np.asarray(d["temperature_celsius"][:], dtype=np.float64)
        S = np.asarray(d["salinity_mass_fraction"][:], dtype=np.float64)
        z = np.asarray(d["z_model_m"][:], dtype=np.float64)
        attrs = {a: d.getncattr(a) for a in d.ncattrs() if a in ("mask_source","freezing_clamp","freezing_clamp_cells")}
        d.close()
        shape_ok = lev.shape == kt.shape
        lev_ok = shape_ok and bool(np.array_equal(lev, kt))
        kk = np.arange(T.shape[2])[None, None, :]
        m = (lev[:, :, None] > 0) & (kk < lev[:, :, None])
        pairs = int(np.sum(m & (T == 0.0) & (S == 0.0)))
        sbad = int(np.sum(m & (S <= 0.0)))
        checks.append({"file": p.name, "shape_ok": shape_ok, "lev_match": lev_ok,
                       "lev_sum": int(lev.sum()), "unfilled_pairs": pairs,
                       "S_nonpositive_wet": sbad, "z_match": bool(np.allclose(z, Z, atol=1e-6)),
                       "mask_source": attrs.get("mask_source")})
        files[p.name] = checks[-1]
        print(f"{p.name}: lev_match={lev_ok} sum={int(lev.sum())} pairs={pairs} S<=0={sbad} z={checks[-1]['z_match']}")
    bad = [c for c in checks if not (c["shape_ok"] and c["lev_match"] and c["unfilled_pairs"] == 0
                                     and c["S_nonpositive_wet"] == 0 and c["z_match"])]
    out = {"test": "mask_consistency", "stage": "11.8.0 T3-CORRECTIVE",
           "runtime_level_cells": int(kt.sum()), "files": files,
           "status": "CLEAN" if not bad else "ISSUES_FOUND"}
    OUT.write_text(json.dumps(out, indent=2))
    print(f"OVERALL: {out['status']} ({len(checks)-len(bad)}/{len(checks)} products clean)")
    return 0 if not bad else 1

if __name__ == "__main__":
    sys.exit(main())
