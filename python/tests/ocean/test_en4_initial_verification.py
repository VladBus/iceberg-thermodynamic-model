#!/usr/bin/env python3
"""
Stage 11.8.0 T0 Phase 2 — EN4 initial T/S verification (data & units).

For every seasonal initial product (shipped + rebuild variants present):
  metadata : dims (133,105,18), required variables, unit-bearing names;
  zeros    : T==0 / S==0 inside WET columns only (land convention is 0);
  supercooling: T < Tf_legacy(S) = -54*S(mass fraction)  [model formula];
  inversions : float32 Eckart ro, count k/k+1 interfaces with
               ro(k)-ro(k+1) > 0.9e-7 (production eps_density);
  units    : T roughly [-2.5,35] degC, S roughly [0.030,0.041] fraction;
  z grid   : z_model_m == model Z (2.5..600 m from src/param.f90 DATA);
  masks    : wet_mask columns == 11067 (grid gate), level cells == 143422,
             cross-season identity of wet_mask.

Statuses: PASS / WARNING / FAIL per check; overall CLEAN or ISSUES_FOUND.
Findings only - no file is modified. Output:
data/validation/en4_initial_result.json (relative paths).
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
OCEAN_DIR = PROJECT / "data/input/processed/ocean"
OUT = PROJECT / "data/validation/en4_initial_result.json"

# Model canonical Z [m] (src/param.f90 DATA z, cm /100)
Z_MODEL = np.array([2.5, 5, 10, 15, 20, 25, 30, 40, 50, 75,
                    100, 150, 200, 250, 300, 400, 500, 600])
KS = 18
EXPECTED_WET_COLUMNS = 11067
# Documented 11.7B.1/11.7E.2 distinction: the PRODUCT counts level cells
# pre-smoothing (143176); the MODEL's smoothed runtime mask reads 143422.
EXPECTED_PRODUCT_LEVELS = 143176
EXPECTED_MODEL_LEVELS = 143422
EPS_DENSITY = 0.9e-7


def eckart_ro(T, S):
    """Model float32 Eckart density anomaly [g/cm3]."""
    T = T.astype(np.float32)
    S = S.astype(np.float32)
    aa = np.float32(1779.5) + (np.float32(11.25) - np.float32(0.0745) * T) * T \
        - (np.float32(3800.0) + np.float32(10.0) * T) * S
    bb = np.float32(5891.0) + np.float32(3000.0) * S \
        + (np.float32(38.0) - np.float32(0.375) * T) * T
    return np.float32(1.0) / (np.float32(0.698) + aa / bb) - np.float32(1.02)


class Acc:
    def __init__(self):
        self.checks = []

    def add(self, name, status, detail):
        self.checks.append({"name": name, "status": status, "detail": detail})
        print(f"  {status:7s} {name}: {detail}")


def verify_file(path, acc):
    rel = str(path.relative_to(PROJECT))
    info = {"file": rel}
    with Dataset(path) as d:
        vars_needed = {"temperature_celsius", "salinity_mass_fraction",
                       "wet_mask", "water_column_levels", "z_model_m"}
        missing = vars_needed - set(d.variables)
        acc.add(f"{path.name}: required variables",
                "PASS" if not missing else "FAIL",
                "all present" if not missing else f"missing {missing}")
        if missing:
            return info
        T = np.array(d["temperature_celsius"][:], dtype=np.float32)
        S = np.array(d["salinity_mass_fraction"][:], dtype=np.float32)
        wet = np.array(d["wet_mask"][:], dtype=np.int32)
        lev = np.array(d["water_column_levels"][:], dtype=np.int32)
        zm = np.array(d["z_model_m"][:], dtype=np.float64)

        shape_ok = (T.shape == (133, 105, KS))
        acc.add(f"{path.name}: dims", "PASS" if shape_ok else "FAIL",
                str(T.shape))
        n_cols = int(np.sum(wet == 1))
        n_lev = int(np.sum(np.where(wet == 1, lev, 0)))
        acc.add(f"{path.name}: wet columns",
                "PASS" if n_cols == EXPECTED_WET_COLUMNS else "WARNING",
                f"{n_cols} (expected {EXPECTED_WET_COLUMNS})")
        acc.add(f"{path.name}: wet level cells (product pre-smoothing count)",
                "PASS" if n_lev == EXPECTED_PRODUCT_LEVELS else "WARNING",
                f"{n_lev} (product expected {EXPECTED_PRODUCT_LEVELS}; "
                f"model post-smoothing reads {EXPECTED_MODEL_LEVELS})")

        # wet interior mask (exclude land-filled zeros)
        kk = np.arange(KS)[None, None, :]
        interior = (wet[:, :, None] == 1) & (kk < lev[:, :, None])

        tz = int(np.sum((T == 0.0) & interior))
        sz = int(np.sum((S == 0.0) & interior))
        z_lim = max(1, int(round(0.01 * EXPECTED_PRODUCT_LEVELS)))
        acc.add(f"{path.name}: zero-T in wet cells",
                "PASS" if tz <= z_lim else "WARNING",
                f"{tz} (1% budget {z_lim})")
        acc.add(f"{path.name}: zero-S in wet cells",
                "PASS" if sz <= z_lim else "WARNING",
                f"{sz}")

        tf = np.float32(-54.0) * S                      # model Zubov-style Tf
        sc = int(np.sum((T < tf) & interior))
        sc_hard = int(np.sum((tf - T > np.float32(0.5)) & interior))
        acc.add(f"{path.name}: supercooling T<Tf",
                "PASS" if sc_hard == 0 else "WARNING",
                f"{sc} cells beyond Tf ({sc_hard} by >0.5 degC)")

        ro = eckart_ro(T, S)
        inv = 0
        max_res = np.float32(0.0)
        Ttr = np.where(interior, T, np.nan)
        Snonmono = 0
        for k in range(KS - 1):
            a = ro[:, :, k]
            b = ro[:, :, k + 1]
            both = interior[:, :, k] & interior[:, :, k + 1]
            res = np.where(both, a - b, np.float32(0.0))
            hit = res > np.float32(EPS_DENSITY)
            inv += int(np.sum(hit))
            if res.size:
                max_res = max(max_res, np.nanmax(res))
        for k in range(KS - 1):
            ta = np.where(interior[:, :, k], Ttr[:, :, k], np.nan)
            tb = np.where(interior[:, :, k + 1], Ttr[:, :, k + 1], np.nan)
            dT = tb - ta
            nonmono = np.abs(np.nansum(np.maximum(dT, 0))) > 0
            Snonmono += int(np.sum((dT > 0.05) & np.isfinite(dT)))
        acc.add(f"{path.name}: density inversions (>eps)",
                "PASS" if inv == 0 else "WARNING",
                f"{inv} interfaces, max residual {float(max_res):.3e}")
        acc.add(f"{path.name}: T increasing with depth (>0.05 degC steps)",
                "PASS" if Snonmono == 0 else "INFO",
                f"{Snonmono} level-pairs (informational; stable if salty deep)")

        tmin = float(np.nanmin(np.where(interior, T, np.nan)))
        tmax = float(np.nanmax(np.where(interior, T, np.nan)))
        smin = float(np.nanmin(np.where(interior, S, np.nan)))
        smax = float(np.nanmax(np.where(interior, S, np.nan)))
        unit_slip = abs(tmax) > 100 or 0.3 < smax < 40   # K or PSU confusion
        status = "FAIL" if unit_slip else (
            "PASS" if -2.6 <= tmin and tmax <= 35 and 0.0 <= smin and smax <= 0.042
            else "WARNING")
        detail = f"T[{tmin:.2f},{tmax:.2f}] S[{smin:.4f},{smax:.4f}]"
        if status == "WARNING":
            detail += " | below -2.6 degC: EN4 sub-freezing values (clamp "                       "variants exist for Jan; T<Tf handled by CA)"
        acc.add(f"{path.name}: units/ranges (degC; mass fraction)", status, detail)

        zmatch = bool(np.allclose(zm, Z_MODEL, atol=1e-6))
        acc.add(f"{path.name}: z_model_m == model Z grid",
                "PASS" if zmatch else "WARNING",
                "matches src/param.f90 DATA z" if zmatch else
                f"LEGACY shadowed grid (bottom {zm[-1]:g} m vs 600 m); "
                "reader ignores z_model_m and reads levels by index -> "
                "metadata mislabels actual depths (T0 finding)")

        info.update({"wet_columns": n_cols, "wet_level_cells": n_lev,
                     "zero_T": tz, "zero_S": sz, "supercooling": sc,
                     "supercooling_gt_0p5C": sc_hard,
                     "density_inversions": inv, "z_grid_matches_model": zmatch,
                     "T_range": [tmin, tmax], "S_range": [smin, smax]})
    return info


def main():
    files = sorted(OCEAN_DIR.glob("initial_ts_2020-*.nc"))
    if not files:
        print("SKIP: no EN4 initial products present (data bundle absent).")
        return 0
    acc = Acc()
    infos = {}
    for p in files:
        print(f"--- {p.name} ---")
        infos[p.name] = verify_file(p, acc)

    canonical = ["initial_ts_2020-01-01.nc", "initial_ts_2020-04-01.nc",
                 "initial_ts_2020-07-01.nc", "initial_ts_2020-10-01.nc"]
    for c in canonical:
        acc.add(f"seasonal availability {c}",
                "PASS" if (OCEAN_DIR / c).exists() else "WARNING",
                "present" if (OCEAN_DIR / c).exists() else "MISSING for 11.8A")
    for season in ("07", "10"):
        rb = OCEAN_DIR / f"initial_ts_2020-{season}-01_rebuild.nc"
        acc.add(f"rebuild variant {season}",
                "PASS" if rb.exists() else "WARNING",
                "present" if rb.exists() else
                "NO rebuilt product (correct 600 m grid) exists for this "
                "season; shipped product carries the legacy shadowed z grid")

    # cross-season mask identity (canonical files)
    masks = {}
    for c in canonical:
        p = OCEAN_DIR / c
        if p.exists():
            with Dataset(p) as d:
                masks[c] = np.array(d["wet_mask"][:], dtype=np.int8)
    if masks:
        ref = next(iter(masks.values()))
        ident = all(np.array_equal(m, ref) for m in masks.values())
        acc.add("wet_mask identity across seasons",
                "PASS" if ident else "WARNING",
                "identical grids" if ident else "masks differ by season")

    statuses = [c["status"] for c in acc.checks]
    overall = "ISSUES_FOUND" if any(s in ("FAIL", "WARNING") for s in statuses) else "CLEAN"
    out = {"test": "en4_initial_verification", "stage": "11.8.0 T0 Phase 2",
           "overall": overall, "files": infos, "checks": acc.checks}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nChecks: {len(acc.checks)}  "
          f"PASS={statuses.count('PASS')} WARNING={statuses.count('WARNING')} "
          f"INFO={statuses.count('INFO')} FAIL={statuses.count('FAIL')}")
    print(f"OVERALL: {overall}")
    print(f"Results: {OUT.relative_to(PROJECT)}")
    return 0  # T0 is diagnostic; findings recorded, exit stays 0


if __name__ == "__main__":
    sys.exit(main())