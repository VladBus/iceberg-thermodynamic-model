#!/usr/bin/env python3
"""
Stage 11.8.0 T1 Phase 2 — ERA5 temporal interpolation driver.

Runs the Fortran harness test_era5_interp_harness (which self-generates the
synthetic files and calls the PRODUCTION era5_find_time_index) and combines
data/validation/era5_temporal_interp_fortran.json into
data/validation/era5_temporal_interp_result.json.

Documented behaviour (verified numerically):
  exact timestamps -> exact record;
  between timestamps -> nearest record; exact 3 h tie -> earlier record;
  outside range -> clamped to first/last record;
  24 h data gap -> nearest record across the gap (no interpolation);
  time axis strictly increasing, seconds since 1970-01-01.

Exit: 0 on PASS; 1 on FAIL/execution error. Stdlib only.
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
    fjson = OUT_DIR / "era5_temporal_interp_fortran.json"
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
        print("FAIL: temporal JSON missing")
        return 1
    raw = json.loads(fjson.read_text())
    ok = (raw.get("status") == "PASS"
          and raw.get("basic_status") == "PASS"
          and raw.get("gap_status") == "PASS"
          and raw.get("axis_status") == "PASS")

    out = {
        "test": "era5_temporal_interpolation",
        "stage": "11.8.0 T1 Phase 2",
        "reader": raw.get("reader"),
        "method": raw.get("method"),
        "checks": raw,
        "notes": {
            "tie_break": "exact midpoint selects the EARLIER record",
            "outside_range": "clamped to first/last record (no error)",
            "gap_handling": "nearest record across a gap; no temporal "
                            "interpolation between 6-hourly analyses",
        },
        "status": raw.get("status", "FAIL"),
        "executed": True,
        "process_exit_code": p.returncode,
    }
    (OUT_DIR / "era5_temporal_interp_result.json").write_text(
        json.dumps(out, indent=2))
    print(f"Temporal status: {out['status']} "
          f"(basic {raw.get('basic_status')}, gap {raw.get('gap_status')}, "
          f"axis {raw.get('axis_status')})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())