#!/usr/bin/env python3
"""
Stage 11.8.0.0.1 — T2 smoke-test driver (both EOS modes)

Runs the production Fortran `convect_column` homogeneous-column test twice
(EOS_MODE=LEGACY and EOS_MODE=EOS80), verifies the JSON verdict and the
process exit code, and propagates any failure (exit non-zero).

The homogeneous column is a SMOKE control (stable by construction, CA must
not touch it). The weak-inversion core test lives in test_weak_inversion.py.

Writes: data/validation/homogeneous_column_result.json
Exit: 0 = both modes executed AND status == PASS with |dT|,|dS| <= 1e-6;
      1 = any missing JSON, FAIL status, tolerance breach, or bad exit code.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"
TOL = 1.0e-6
TARGET = "test_homogeneous_column"


def find_executable():
    for pattern in (
        str(PROJECT / "build" / "gfortran_*" / "test" / TARGET),
    ):
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
        cwd=PROJECT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        raise RuntimeError("fpm build failed")
    exe = find_executable()
    if exe is None:
        raise RuntimeError(f"{TARGET} executable not found after build")
    return exe


def run_mode(exe, mode):
    json_path = OUT_DIR / f"homogeneous_column_fortran_{mode}.json"
    json_path.unlink(missing_ok=True)  # guarantee fresh evidence per run
    env = os.environ.copy()
    env["EOS_MODE"] = mode
    proc = subprocess.run([str(exe)], cwd=PROJECT, env=env,
                          capture_output=True, text=True)
    print(f"--- EOS_MODE={mode} (exit {proc.returncode}) ---")
    print(proc.stdout + proc.stderr)

    if not json_path.exists():
        return {"eos_mode": mode, "executed": False,
                "process_exit_code": proc.returncode,
                "error": f"JSON output missing: {json_path}"}
    with open(json_path) as f:
        r = json.load(f)
    r["executed"] = True
    r["process_exit_code"] = proc.returncode

    ok = (
        proc.returncode == 0
        and r.get("status") == "PASS"
        and float(r.get("delta_T_max", 1e9)) <= TOL
        and float(r.get("delta_S_max", 1e9)) <= TOL
        and r.get("status_f64") == "PASS"
        and float(r.get("delta_T_max_f64", 1e9)) <= 1e-14
        and float(r.get("delta_S_max_f64", 1e9)) <= 1e-14
    )
    r["driver_ok"] = ok
    return r


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        exe = build_if_needed()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 1
    print(f"Fortran executable: {exe.relative_to(PROJECT)}")

    results = {"test": "homogeneous_column", "kind": "smoke_control",
               "tolerance": TOL, "modes": {}}
    all_ok = True
    for mode in ("LEGACY", "EOS80"):
        r = run_mode(exe, mode)
        results["modes"][mode] = r
        if not r.get("driver_ok", False):
            all_ok = False

    results["status"] = "PASS" if all_ok else "FAIL"
    with open(OUT_DIR / "homogeneous_column_result.json", "w") as f:
        json.dump(results, f, indent=2)

    for mode, r in results["modes"].items():
        print(f"{mode}: status={r.get('status', 'N/A')} "
              f"dT={r.get('delta_T_max', 'N/A')} dS={r.get('delta_S_max', 'N/A')} "
              f"dT64={r.get('delta_T_max_f64', 'N/A')} dS64={r.get('delta_S_max_f64', 'N/A')} "
              f"iters={r.get('iterations', 'N/A')} proc_exit={r.get('process_exit_code', 'N/A')}")
    print(f"OVERALL: {results['status']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())