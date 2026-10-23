#!/usr/bin/env python3
"""
Stage 11.8.0 T2 Phase 2 driver — weak-inversion conservation (both EOS modes).

Runs the Fortran test test_weak_inversion_conservation twice (EOS_MODE=LEGACY
and EOS80) and verifies:
  - the genuine inversion is mixed (nmix >= 1 in the production f32 and
    f64-core paths);
  - the EXACT float64 reference conserves heat and salt to < 1e-12 relative;
  - the stable control column is left untouched (nmix == 0);
  - the production float32 storage limitation is recorded (reported, not a
    failure: convect_column_f64 writes T/S back to REAL(4)).

Writes data/validation/weak_inversion_conservation_result.json.
Exit: 0 = all expected behaviours; 1 = violation/execution error.
Stdlib only (runs in the fpm CI job).
"""

import glob
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"
TARGET = "test_weak_inversion_conservation"


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
        raise RuntimeError("weak-inversion executable not found after build")
    return exe


def run_mode(exe, mode):
    jpath = OUT_DIR / f"weak_inversion_conservation_fortran_{mode}.json"
    jpath.unlink(missing_ok=True)
    import os
    env = os.environ.copy(); env["EOS_MODE"] = mode
    p = subprocess.run([str(exe)], cwd=PROJECT, env=env,
                       capture_output=True, text=True)
    print(f"--- {mode} (exit {p.returncode}) ---")
    print(p.stdout + p.stderr)
    if not jpath.exists():
        return {"eos_mode": mode, "executed": False,
                "process_exit_code": p.returncode}
    d = json.loads(jpath.read_text())
    d["executed"] = True
    d["process_exit_code"] = p.returncode
    d["ok"] = (
        p.returncode == 0
        and d.get("status") == "PASS"
        and d.get("nmix_production_f32", 0) >= 1
        and d.get("nmix_production_f64core", 0) >= 1
        and d.get("nmix_exact_reference", 0) >= 1
        and float(d.get("heat_rel_err_exact_reference", 1)) < 1e-12
        and float(d.get("salt_rel_err_exact_reference", 1)) < 1e-12
        and d.get("nmix_stable_control") == 0
    )
    return d


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        exe = ensure_built()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        return 1
    print(f"Executable: {exe.relative_to(PROJECT)}")
    modes = {}
    all_ok = True
    for mode in ("LEGACY", "EOS80"):
        r = run_mode(exe, mode)
        modes[mode] = r
        if not r.get("ok", False):
            all_ok = False
    out = {
        "test": "weak_inversion_conservation",
        "stage": "11.8.0 T2 Phase 2",
        "tolerance_relative": 1e-12,
        "modes": modes,
        "storage_note": ("convect_column_f64 computes in real64 but stores "
                         "T/S back into REAL(4) arrays; production conservation "
                         "is float32-limited (~1e-7 rel). The exact float64 "
                         "reference (same algorithm, real64 state) conserves "
                         "to <=1e-12, proving the algorithm itself is "
                         "conservative."),
        "status": "PASS" if all_ok else "FAIL",
    }
    (OUT_DIR / "weak_inversion_conservation_result.json").write_text(
        json.dumps(out, indent=2))
    for m, r in modes.items():
        print(f"{m}: status={r.get('status')} nmix(f32/f64/ref)="
              f"{r.get('nmix_production_f32')}/{r.get('nmix_production_f64core')}/"
              f"{r.get('nmix_exact_reference')} "
              f"heat_rel_ref={r.get('heat_rel_err_exact_reference')} "
              f"salt_rel_ref={r.get('salt_rel_err_exact_reference')}")
    print(f"OVERALL: {out['status']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())