#!/usr/bin/env python3
"""
Stage 11.8.0 T2 Phase 3 driver — CA compressibility (in-situ vs potential).

Runs the Fortran test test_ca_compressibility twice (EOS_MODE=LEGACY and
EOS80). The column is potential-density unstable but in-situ stable at 50 dbar
separation when pressure dependence is active.

Expected:
  LEGACY : CA mixes the column (control) -> CONTROL_PASS;
  EOS80  : CA does NOT mix (it compares in-situ density at local pressure)
           -> CRITICAL_CONFIRMED (Sonnet A-1 false stability).

This is a diagnostic finding, NOT a failure: exit 0 when the expected
critical behaviour is confirmed, 1 if the construction is invalid or the
behaviour is unexpected.

Writes data/validation/ca_compressibility_result.json. Stdlib only.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT / "data" / "validation"
TARGET = "test_ca_compressibility"


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
        raise RuntimeError("compressibility executable not found after build")
    return exe


def run_mode(exe, mode):
    jpath = OUT_DIR / f"ca_compressibility_fortran_{mode}.json"
    jpath.unlink(missing_ok=True)
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
    return d


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        exe = ensure_built()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        return 1
    print(f"Executable: {exe.relative_to(PROJECT)}")

    legacy = run_mode(exe, "LEGACY")
    eos80 = run_mode(exe, "EOS80")

    legacy_ok = legacy.get("status") == "CONTROL_PASS"
    critical = (eos80.get("status") == "CRITICAL_CONFIRMED"
                and bool(eos80.get("potential_unstable"))
                and bool(eos80.get("in_situ_stable"))
                and eos80.get("nmix_production_f32") == 0
                and eos80.get("nmix_production_f64core") == 0)
    if critical and legacy_ok:
        status = "CRITICAL_CONFIRMED"
    elif eos80.get("status") == "NOT_CONFIRMED_CA_MIXED":
        status = "NOT_CONFIRMED_CA_MIXED"
    else:
        status = "UNEXPECTED"

    out = {
        "test": "ca_compressibility",
        "stage": "11.8.0 T2 Phase 3 (Sonnet A-1)",
        "setup": ("L1 T=3.0/S=0.0345 at 25 m over L2 T=3.6/S=0.0345 at 75 m; "
                  "50 dbar separation -> compression ~2.3e-4 g/cm3 exceeds "
                  "thermal contrast ~1.2e-4"),
        "criterion": ("src/convective_adjustment.f90 compares IN-SITU density "
                      "eos_density(T,S,z*0.01 dbar) at each level; there is no "
                      "potential-density (sigma_0) criterion"),
        "modes": {"LEGACY": legacy, "EOS80": eos80},
        "status": status,
        "finding": (
            "CA uses IN-SITU density at the local depth. Under EOS-80, "
            "compressibility over 50 dbar can exceed the thermal "
            "destabilisation, so a column that is genuinely convective in "
            "potential density is classified as stable and left unmixed. "
            "This is the A-1 defect (false stability). It is documented for "
            "the CA/EOS fix; NOT changed in T2."),
    }
    (OUT_DIR / "ca_compressibility_result.json").write_text(
        json.dumps(out, indent=2))
    print(f"LEGACY: {legacy.get('status')} (nmix "
          f"{legacy.get('nmix_production_f32')}/{legacy.get('nmix_production_f64core')})")
    print(f"EOS80 : {eos80.get('status')} (potential_unstable="
          f"{eos80.get('potential_unstable')}, in_situ_stable="
          f"{eos80.get('in_situ_stable')}, nmix "
          f"{eos80.get('nmix_production_f32')}/{eos80.get('nmix_production_f64core')})")
    print(f"OVERALL: {status}")
    return 0 if status in ("CRITICAL_CONFIRMED", "NOT_CONFIRMED_CA_MIXED") else 1


if __name__ == "__main__":
    sys.exit(main())