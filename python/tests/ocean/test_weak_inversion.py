#!/usr/bin/env python3
"""
Stage 11.8.0.0.1 — T2 core driver: weak inversion (both EOS modes)

Runs the production Fortran `convect_column` weak-inversion test twice
(EOS_MODE=LEGACY and EOS_MODE=EOS80), verifies the JSON verdict and process
exit code, and propagates failures (exit non-zero).

Physics being verified (Stage 11.8.0.0.1 finding):
  LEGACY (Eckart, no pressure dependence): CA detects the single inversion at
    interface 2/3, mixes exactly levels 2-3, conserves heat/salt, converges.
  EOS80 (UNESCO): in-situ density masks the inversion (pressure-densification
    ~1.2e-4 g/cm3 per 25 m dominates the ~1e-5 thermal contrast), so CA must
    perform NO mixing — mode-dependent masking is an 11.8 candidate fix
    (potential-density criterion), NOT fixed in this stage.

Writes: data/validation/weak_inversion_result.json
Exit: 0 = both modes executed AND status == PASS; 1 = any failure.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"
TARGET = "test_weak_inversion"


def find_executable():
    matches = glob.glob(str(PROJECT / "build" / "gfortran_*" / "test" / TARGET))
    return Path(sorted(matches)[-1]) if matches else None


def build_if_needed():
    exe = find_executable()
    if exe is not None:
        return exe
    print("Fortran test executable not found; building with fpm...")
    proc = subprocess.run(["fpm", "build", "--flag", "-I/usr/include"],
                          cwd=PROJECT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        raise RuntimeError("fpm build failed")
    exe = find_executable()
    if exe is None:
        raise RuntimeError(f"{TARGET} executable not found after build")
    return exe


def run_mode(exe, mode):
    json_path = OUT_DIR / f"weak_inversion_fortran_{mode}.json"
    json_path.unlink(missing_ok=True)
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

    heat_ok = float(r.get("heat_rel_err", 1e9)) < 1e-5
    salt_ok = float(r.get("salt_abs_err", 1e9)) < 1e-9
    stable_ok = (not r.get("guard_hit", True)) and float(r.get("resid_inv", 1e9)) <= 0.0
    if mode == "LEGACY":
        mixing_ok = r.get("nmix", -1) >= 1 and r.get("changed_levels") == [2, 3]
    else:  # EOS80: in-situ criterion must find no instability to mix
        mixing_ok = r.get("nmix", -1) == 0 and r.get("changed_levels") == []
    ok = (proc.returncode == 0 and r.get("status") == "PASS"
          and heat_ok and salt_ok and stable_ok and mixing_ok)
    r["driver_ok"] = ok
    r["conservation_ok"] = heat_ok and salt_ok
    return r


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        exe = build_if_needed()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 1
    print(f"Fortran executable: {exe.relative_to(PROJECT)}")

    results = {"test": "weak_inversion", "kind": "t2_core", "modes": {}}
    all_ok = True
    for mode in ("LEGACY", "EOS80"):
        r = run_mode(exe, mode)
        results["modes"][mode] = r
        if not r.get("driver_ok", False):
            all_ok = False
    results["status"] = "PASS" if all_ok else "FAIL"
    results["heat_salt_conservation"] = {
        m: bool(r.get("conservation_ok", False)) for m, r in results["modes"].items()
    }
    with open(OUT_DIR / "weak_inversion_result.json", "w") as f:
        json.dump(results, f, indent=2)

    for mode, r in results["modes"].items():
        print(f"{mode}: status={r.get('status', 'N/A')} nmix={r.get('nmix', 'N/A')} "
              f"changed={r.get('changed_levels', 'N/A')} "
              f"heat_rel={r.get('heat_rel_err', 'N/A')} "
              f"salt_abs={r.get('salt_abs_err', 'N/A')} "
              f"proc_exit={r.get('process_exit_code', 'N/A')}")
    print(f"OVERALL: {results['status']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())