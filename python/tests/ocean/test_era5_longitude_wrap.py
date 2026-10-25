#!/usr/bin/env python3
"""T-23 verification: ERA5 longitude edge clamp vs legacy cyclic wrap.

The Fortran harness builds a narrow file (10..70 E) and calls the production
era5_bilinear2d three times through env switches:
  * STAGE118_LON_CLAMP=false (legacy): 75E -> 10E (wrong side)
  * STAGE118_LON_CLAMP=true  (fix):    75E -> 70E (east edge)
  * 5E control -> 10E in both modes.

Outputs:
  data/validation/era5_longitude_wrap_result.json
  data/validation/lon_clamp_verification.json
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
FJSON = OUT_DIR / "era5_longitude_wrap_fortran.json"


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


def run(exe, clamp):
    env = dict(os.environ)
    env["STAGE118_LON_CLAMP"] = "true" if clamp else "false"
    FJSON.unlink(missing_ok=True)
    p = subprocess.run([str(exe)], cwd=PROJECT, capture_output=True, text=True, env=env)
    if not FJSON.exists():
        raise RuntimeError(f"wrap JSON missing (clamp={clamp}): {p.stdout[-1000:]}{p.stderr[-1000:]}")
    return json.loads(FJSON.read_text())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        exe = ensure_built()
        off = run(exe, False)
        on = run(exe, True)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        return 1

    e_off = float(off["query_east_actual"])
    w_off = float(off["query_west_actual"])
    e_on = float(on["query_east_actual"])
    w_on = float(on["query_west_actual"])
    tol = 1e-9
    if abs(e_on - 70.0) < tol and abs(w_on - 10.0) < tol and abs(e_off - 10.0) < tol:
        status = "FIXED"
        note = ("T-23 FIXED: legacy wrap returns 10E for a 75E query; "
                "STAGE118_LON_CLAMP=true returns the eastern edge 70E; "
                "the 5E control remains 10E.")
    elif abs(e_off - 10.0) < tol and abs(e_on - 10.0) < tol:
        status = "RED_CONFIRMED"
        note = "Clamp switch did not change the out-of-range behaviour."
    else:
        status = "UNEXPECTED"
        note = f"off east={e_off}, on east={e_on}, on west={w_on}"

    result = {
        "test": "era5_longitude_wrap",
        "stage": "11.8.0 T4-PREP (T-23)",
        "reader": on.get("reader"),
        "file_lon_range": [on.get("file_lon_min"), on.get("file_lon_max")],
        "legacy_wrap": {"query_east_75E": e_off, "query_west_5E": w_off},
        "clamp_on": {"query_east_75E": e_on, "query_west_5E": w_on},
        "expected_clamp_east": 70.0,
        "status": status,
        "finding": note,
    }
    (OUT_DIR / "era5_longitude_wrap_result.json").write_text(json.dumps(result, indent=2))
    (OUT_DIR / "lon_clamp_verification.json").write_text(json.dumps(result, indent=2))
    print(f"T-23 status: {status}")
    print(note)
    return 0 if status == "FIXED" else 1


if __name__ == "__main__":
    sys.exit(main())
