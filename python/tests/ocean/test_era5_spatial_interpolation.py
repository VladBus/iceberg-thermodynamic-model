#!/usr/bin/env python3
"""
Stage 11.8.0 T1 Phase 1 — ERA5 spatial interpolation driver.

Runs the Fortran harness test_era5_interp_harness (which self-generates a
synthetic ERA5-like NetCDF and calls the PRODUCTION era5_bilinear2d), then
reads data/validation/era5_spatial_interp_fortran.json and combines it into
data/validation/era5_spatial_interp_result.json.

Exit: 0 if the harness executed and the interior/edge checks PASS
      (a WARNING wrap result is allowed and reported); 1 on FAIL/execution error.
Stdlib only (runs in the fpm CI job).
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"
TARGET = "test_era5_interp_harness"


def find_exe():
    hits = glob.glob(str(PROJECT / "build" / "gfortran_*" / "test" / TARGET))
    return Path(sorted(hits)[-1]) if hits else None


def ensure_built():
    exe = find_exe()
    if exe:
        return exe
    print("Harness not built; running fpm build ...")
    p = subprocess.run(["fpm", "build", "--flag", "-I/usr/include"],
                       cwd=PROJECT, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout[-2000:]); print(p.stderr[-2000:])
        raise RuntimeError("fpm build failed")
    exe = find_exe()
    if not exe:
        raise RuntimeError("harness executable not found after build")
    return exe


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fjson = OUT_DIR / "era5_spatial_interp_fortran.json"
    fjson.unlink(missing_ok=True)
    try:
        exe = ensure_built()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        return 1
    print(f"Harness: {exe.relative_to(PROJECT)}")
    p = subprocess.run([str(exe)], cwd=PROJECT, capture_output=True, text=True)
    print(p.stdout + p.stderr)

    if not fjson.exists():
        print("FAIL: spatial JSON missing")
        return 1
    raw = json.loads(fjson.read_text())
    checks = []
    ok = True
    for key in ("interior_max_abs_err", "interior_status", "wrap_expected",
                "wrap_actual", "wrap_abs_err", "wrap_status",
                "lat_outside_high_rejected", "lat_outside_low_rejected",
                "lat_edge_nodes_accepted", "edges_status", "status"):
        if key in raw:
            checks.append({"name": key, "value": raw[key]})
    if raw.get("interior_status") != "PASS":
        ok = False
    if raw.get("edges_status") != "PASS":
        ok = False
    if raw.get("status") == "FAIL":
        ok = False

    out = {
        "test": "era5_spatial_interpolation",
        "stage": "11.8.0 T1 Phase 1",
        "reader": raw.get("reader"),
        "method": raw.get("method"),
        "checks": checks,
        "wrap_finding": (
            "L-1 LATENT BUG (documented, NOT fixed in T1): longitude "
            "normalization subtracts/ adds 360 at most once and can land "
            "outside the grid; the weight is then clamped, so a query east of "
            "the last node returns the first-node value instead of "
            "interpolating across the wrap. Production impact: NONE for the "
            "current domain (0 model cells outside the ERA5 longitude range, "
            "T0), but global/wrap-adjacent queries are wrong."),
        "status": raw.get("status", "FAIL"),
        "executed": True,
        "process_exit_code": p.returncode,
    }
    (OUT_DIR / "era5_spatial_interp_result.json").write_text(
        json.dumps(out, indent=2))
    print(f"Spatial status: {out['status']} "
          f"(interior {raw.get('interior_status')}, edges {raw.get('edges_status')}, "
          f"wrap {raw.get('wrap_status')})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())