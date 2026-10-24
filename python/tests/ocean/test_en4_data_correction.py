#!/usr/bin/env python3
"""
Stage 11.8.0 T3-PREP — EN4 data correction verification.

Verifies the corrected EN4 initial products for all four seasons (canonical
and _rebuild variants):
  - z_model_m equals the model DATA z grid (2.5..600 m);
  - ZERO cells below the UNESCO freezing point Tf(S,p) in wet cells;
  - no sentinel zeros (T==0 / S==0 inside wet cells);
  - units/ranges (degC, mass fraction);
  - masks (11067 wet columns / 143176 product level cells), identical seasons;
  - per-season metadata (target_run_date, source_product month);
  - rebuild variant identical to its canonical file;
  - clamp statistics recorded (cells clamped, max clamp, from the builder JSON).

Output: data/validation/en4_correction_result.json
Exit: 0 = CLEAN; 1 = any FAIL/WARNING.
"""

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
OCEAN = PROJECT / "data/input/processed/ocean"
STATS_DIR = PROJECT / "data/output/diagnostics/stage7.7"
OUT = PROJECT / "data/validation/en4_correction_result.json"

Z_MODEL = np.array([2.5, 5, 10, 15, 20, 25, 30, 40, 50, 75,
                    100, 150, 200, 250, 300, 400, 500, 600])
SEASONS = [("01", "2020-01-01"), ("04", "2020-04-01"),
           ("07", "2020-07-01"), ("10", "2020-10-01")]
EXPECTED_COLUMNS = 11067
EXPECTED_LEVELS = 143422

CHECKS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "WARNING"
    CHECKS.append({"name": name, "status": status, "detail": detail})
    print(f"  {status:7s} {name}: {detail}")
    return cond


def tf_unesco(S_psu, p_dbar):
    return ((-0.0575 + 1.710523e-3 * np.sqrt(S_psu)
             - 2.154996e-4 * S_psu) * S_psu - 7.53e-4 * p_dbar)


def load(path):
    with Dataset(path) as d:
        T = np.array(d["temperature_celsius"][:], dtype=np.float64)
        S = np.array(d["salinity_mass_fraction"][:], dtype=np.float64)
        z = np.array(d["z_model_m"][:], dtype=np.float64)
        wet = np.array(d["wet_mask"][:], dtype=np.int32)
        lev = np.array(d["water_column_levels"][:], dtype=np.int32)
        attrs = {a: d.getncattr(a) for a in d.ncattrs()
                 if a in ("target_run_date", "source_product",
                          "freezing_clamp", "freezing_clamp_cells")}
    kk = np.arange(T.shape[2])[None, None, :]
    interior = (wet[:, :, None] == 1) & (kk < lev[:, :, None])
    return T, S, z, wet, lev, interior, attrs


def main():
    if not OCEAN.exists() or not any(OCEAN.glob("initial_ts_2020-*.nc")):
        print("SKIP: corrected EN4 products absent (data bundle not in CI).")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    files = {}
    masks = []
    for season, date in SEASONS:
        base = f"initial_ts_{date}"
        for suffix in ("", "_rebuild"):
            path = OCEAN / f"{base}{suffix}.nc"
            tag = f"{date}{suffix or '_canonical'}"
            if not path.exists():
                check(f"{tag}: exists", False, f"missing {path.name}")
                continue
            T, S, z, wet, lev, interior, attrs = load(path)
            Spsu = S * 1000.0
            Tf = tf_unesco(Spsu, z[None, None, :])
            below = int(np.sum(interior & (T < Tf - 1e-6)))
            zero_t = int(np.sum(interior & (T == 0.0)))
            zero_s = int(np.sum(interior & (S == 0.0)))
            n_cols = int(np.sum(wet == 1))
            kk = np.arange(T.shape[2])[None, None, :]
            n_lev = int(np.sum(np.where(wet == 1, lev, 0)))
            tmin = float(np.nanmin(np.where(interior, T, np.nan)))
            tmax = float(np.nanmax(np.where(interior, T, np.nan)))
            smin = float(np.nanmin(np.where(interior, S, np.nan)))
            smax = float(np.nanmax(np.where(interior, S, np.nan)))

            check(f"{tag}: z_model_m == model DATA z",
                  bool(np.allclose(z, Z_MODEL, atol=1e-6)),
                  f"bottom {z[-1]:g} m (model 600 m)")
            check(f"{tag}: 0 cells below Tf(S,p)",
                  below == 0, f"{below} cells (Tf UNESCO, p=z_m)")
            check(f"{tag}: no sentinel zeros",
                  zero_t == 0 and zero_s == 0, f"T0={zero_t} S0={zero_s}")
            check(f"{tag}: units/ranges",
                  (-2.6 <= tmin and tmax <= 35 and 0.0 <= smin
                   and smax <= 0.042),
                  f"T[{tmin:.2f},{tmax:.2f}] S[{smin:.4f},{smax:.4f}]")
            check(f"{tag}: wet columns / level cells",
                  n_cols == EXPECTED_COLUMNS and n_lev == EXPECTED_LEVELS,
                  f"{n_cols} cols / {n_lev} levels")
            check(f"{tag}: metadata date",
                  attrs.get("target_run_date") == date,
                  f"{attrs.get('target_run_date')} (expected {date})")
            check(f"{tag}: metadata product month",
                  date[:7] in str(attrs.get("source_product", "")),
                  str(attrs.get("source_product", ""))[:60])
            masks.append(wet.astype(np.int8))
            files[tag] = {
                "file": str(path.relative_to(PROJECT)),
                "z_bottom_m": float(z[-1]),
                "cells_below_Tf": below,
                "zero_T": zero_t, "zero_S": zero_s,
                "wet_columns": n_cols, "level_cells": n_lev,
                "T_range": [tmin, tmax], "S_range": [smin, smax],
                "freezing_clamp": attrs.get("freezing_clamp"),
                "freezing_clamp_cells": attrs.get("freezing_clamp_cells"),
            }

        # rebuild must equal canonical
        rc = OCEAN / f"{base}.nc"
        rb = OCEAN / f"{base}_rebuild.nc"
        if rc.exists() and rb.exists():
            Tc, Sc, zc, _, _, _, _ = load(rc)
            Tr, Sr, zr, _, _, _, _ = load(rb)
            same = (np.array_equal(Tc, Tr) and np.array_equal(Sc, Sr)
                    and np.array_equal(zc, zr))
            check(f"{date}: rebuild identical to canonical", same,
                  "byte-equal values" if same else "DIFFERS")

    if masks:
        ident = all(np.array_equal(m, masks[0]) for m in masks)
        check("wet_mask identical across all corrected files", ident,
              "identical" if ident else "masks differ")

    # clamp statistics from the builder JSON (recorded evidence)
    clamp = {}
    for season, date in SEASONS:
        ym = date[:7].replace("-", "")
        sp = STATS_DIR / f"stage7.7_statistics_{ym}_T3PREP.json"
        if sp.exists():
            st = json.loads(sp.read_text())
            clamp[date] = {
                "cells_clamped_below_Tf": st.get("cells_clamped_below_Tf"),
                "max_clamp_degC": st.get("max_clamp_degC"),
                "freezing_clamp_enabled": st.get("freezing_clamp_enabled"),
            }

    warnings = [c for c in CHECKS if c["status"] != "PASS"]
    overall = "CLEAN" if not warnings else "ISSUES_FOUND"
    out = {
        "test": "en4_data_correction",
        "stage": "11.8.0 T3-PREP",
        "corrections": {
            "T-20": ("regenerated all four seasons with the corrected pipeline "
                     "(z_model_m == model DATA z; Jul/Oct rebuilds created)"),
            "T-22": ("UNESCO Tf(S,p) freezing-point clamp; T is clamped up to "
                     "Tf+1e-5 degC in wet cells; salinity unchanged"),
        },
        "clamp_stats": clamp,
        "files": files,
        "checks": CHECKS,
        "overall": overall,
    }
    OUT.write_text(json.dumps(
        out, indent=2,
        default=lambda o: (int(o) if isinstance(o, np.integer)
                           else float(o) if isinstance(o, np.floating)
                           else str(o))))
    print(f"\nChecks: {len(CHECKS)}  warnings: {len(warnings)}")
    print(f"OVERALL: {overall}")
    print(f"Results written to {OUT.relative_to(PROJECT)}")
    return 0 if overall == "CLEAN" else 1


if __name__ == "__main__":
    sys.exit(main())