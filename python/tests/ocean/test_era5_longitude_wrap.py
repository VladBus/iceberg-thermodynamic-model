#!/usr/bin/env python3
"""
Stage 11.8.0 T2 Phase 0 — T-23 RED TEST: ERA5 longitude wrap returns the
wrong side for queries east of a narrow file.

The Fortran harness builds a narrow synthetic ERA5 file (longitude 10..70 E,
latitude 60..70 N, u10 == longitude) and calls the PRODUCTION
era5_bilinear2d:

    query 75 E  -> current actual 10.0  (WESTERN edge)   [BUG]
                   correct clamp 70.0  (EASTERN edge)
    query  5 E  -> current actual 10.0  (western edge, correct clamp)

Why: the +-360 normalization subtracts 360 once (75 -> -285), lands outside
the grid, the binary search pins column 1 and the weight clamp returns the
first column. Required fix (recorded, NOT applied in T2): replace the cyclic
wrap with EDGE-CLAMPING in era5_bilinear2d (or reject out-of-range as the
latitude branch already does).

This is a CHARACTERIZATION (red) test: it passes while the bug is present
(status RED_CONFIRMED) and also passes if the behaviour is fixed (FIXED);
an unexpected value is a hard failure.

Exit: 0 for RED_CONFIRMED / FIXED; 1 otherwise.
Stdlib only (runs in the fpm CI job).
"""

import glob
import json
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
    fjson = OUT_DIR / "era5_longitude_wrap_fortran.json"
    fjson.unlink(missing_ok=True)
    try:
        exe = ensure_built()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        return 1
    p = subprocess.run([str(exe)], cwd=PROJECT, capture_output=True, text=True)
    if not fjson.exists():
        print("FAIL: wrap JSON missing")
        print(p.stdout[-2000:] + p.stderr[-2000:])
        return 1
    raw = json.loads(fjson.read_text())

    east = float(raw["query_east_actual"])
    east_ok = bool(raw["query_east_ok"])
    correct = float(raw["query_east_correct_clamp"])
    west = float(raw["query_west_actual"])

    tol = 1e-9
    if abs(east - 10.0) < tol and abs(west - 10.0) < tol:
        status = "RED_CONFIRMED"
        note = ("T-23 CONFIRMED: an east-of-file query (75E, file 10..70E) "
                "returns the WESTERN edge (10.0) instead of the correct "
                "eastern clamp (70.0). Latent for today's domain but invalid "
                "production behaviour for any narrow/global forcing file.")
    elif abs(east - correct) < tol:
        status = "FIXED"
        note = ("The wrap branch now clamps to the eastern edge (70.0) - "
                "T-23 appears fixed; update this characterization test.")
    else:
        status = "UNEXPECTED"
        note = f"Unexpected east-edge value {east} (correct {correct})."

    result = {
        "test": "era5_longitude_wrap",
        "stage": "11.8.0 T2 Phase 0 (T-23)",
        "reader": raw.get("reader"),
        "file_lon_range": [raw.get("file_lon_min"), raw.get("file_lon_max")],
        "query_east": {"lon": raw.get("query_east_lon"), "ok": east_ok,
                       "actual": east, "correct_clamp": correct},
        "query_west_control": {"lon": raw.get("query_west_lon"),
                               "actual": west, "correct_clamp": 10.0},
        "status": status,
        "finding": note,
        "required_fix": ("Replace cyclic +-360 wrap with edge-clamping (or "
                         "out-of-range rejection) in era5_bilinear2d for "
                         "longitudes outside the file range; the current "
                         "wrap can return the opposite edge. Not fixed in "
                         "T2 (diagnostic); assigned to T1-corrective/T4."),
    }
    (OUT_DIR / "era5_longitude_wrap_result.json").write_text(
        json.dumps(result, indent=2))
    print(f"T-23 status: {status}")
    print(note)
    print(f"Results: {(OUT_DIR / 'era5_longitude_wrap_result.json').relative_to(PROJECT)}")
    return 0 if status in ("RED_CONFIRMED", "FIXED") else 1


if __name__ == "__main__":
    sys.exit(main())