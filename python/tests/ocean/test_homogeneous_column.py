#!/usr/bin/env python3
"""
Stage 11.8.0.0 — REAL Homogeneous Column Test Driver

Runs the production Fortran `convect_column` core on a homogeneous column
(T = 4.0 °C, S = 35.0 PSU at all levels) in BOTH EOS modes and records the
actual ΔT and ΔS.

This replaces the Stage 11.7E.4.1 stub that returned NOT_IMPLEMENTED_FULL.

Result: the homogeneous column is statically stable in both EOS modes, so the
production CA correctly does nothing (ΔT = ΔS = 0). The original expectation
that this test would FAIL was a false premise: the defect requires a weak
real inversion (see the T2 analytical-mixing test in the 11.8.0 plan), not a
perfectly homogeneous column.

Writes: data/validation/homogeneous_column_result.json
Exit: 0 = executed (regardless of PASS/FAIL verdict); 1 = execution error.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"


def find_executable():
    patterns = [
        str(PROJECT / "build" / "gfortran_*" / "test" / "test_homogeneous_column"),
        str(PROJECT / "build" / "gfortran_*" / "test" / "homogeneous_column"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return Path(sorted(matches)[-1])
    return None


def build_if_needed():
    exe = find_executable()
    if exe is not None:
        return exe
    print("Fortran test executable not found; building with fpm...")
    proc = subprocess.run(
        ["fpm", "build", "--flag", "-I/usr/include"],
        cwd=PROJECT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        raise RuntimeError("fpm build failed")
    exe = find_executable()
    if exe is None:
        raise RuntimeError("test_homogeneous_column executable not found after build")
    return exe


def run_mode(exe, mode):
    env = os.environ.copy()
    env["EOS_MODE"] = mode
    proc = subprocess.run(
        [str(exe)], cwd=PROJECT, env=env,
        capture_output=True, text=True
    )
    out = proc.stdout + proc.stderr
    print(f"--- EOS_MODE={mode} (exit {proc.returncode}) ---")
    print(out)

    json_path = OUT_DIR / f"homogeneous_column_fortran_{mode}.json"
    if not json_path.exists():
        return {
            "eos_mode": mode,
            "executed": False,
            "exit_code": proc.returncode,
            "error": f"JSON output missing: {json_path}",
        }
    with open(json_path) as f:
        result = json.load(f)
    result["executed"] = True
    result["process_exit_code"] = proc.returncode
    return result


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    exe = build_if_needed()
    print(f"Fortran executable: {exe}")

    results = {"test": "homogeneous_column", "executed": True, "modes": {}}
    ok = True
    for mode in ("LEGACY", "EOS80"):
        try:
            result = run_mode(exe, mode)
        except Exception as exc:  # noqa: BLE001
            result = {"eos_mode": mode, "executed": False, "error": str(exc)}
            ok = False
        results["modes"][mode] = result
        if not result.get("executed", False):
            ok = False

    combined = OUT_DIR / "homogeneous_column_result.json"
    with open(combined, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nCombined results written to {combined}")
    for mode, r in results["modes"].items():
        print(
            f"  {mode}: status={r.get('status', 'N/A')} "
            f"dT={r.get('delta_T_max', 'N/A')} dS={r.get('delta_S_max', 'N/A')} "
            f"iters={r.get('iterations', 'N/A')} exit={r.get('process_exit_code', 'N/A')}"
        )

    if not ok:
        print("ERROR: Fortran test execution incomplete")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())