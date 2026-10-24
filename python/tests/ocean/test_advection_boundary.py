#!/usr/bin/env python3
"""T3-CORRECTIVE (T-29): run the Fortran advection-boundary regression and
propagate its verdict. SKIP if the executable cannot be built/found."""
import glob, json, subprocess, sys
from pathlib import Path
PROJECT = Path(__file__).resolve().parents[3]
J = PROJECT / "data/validation/advection_boundary_result.json"
def main():
    hits = glob.glob(str(PROJECT/"build"/"gfortran_*"/"test"/"test_advection_boundary"))
    if not hits:
        p = subprocess.run(["fpm","build","--flag","-I/usr/include"], cwd=PROJECT,
                           capture_output=True, text=True)
        if p.returncode != 0:
            print("SKIP: cannot build test_advection_boundary"); return 0
        hits = glob.glob(str(PROJECT/"build"/"gfortran_*"/"test"/"test_advection_boundary"))
        if not hits:
            print("SKIP: executable not found"); return 0
    exe = Path(sorted(hits)[-1]); J.unlink(missing_ok=True)
    p = subprocess.run([str(exe)], cwd=PROJECT, capture_output=True, text=True)
    print(p.stdout[-800:])
    if not J.exists():
        print("FAIL: JSON missing"); return 1
    d = json.loads(J.read_text())
    print(f"interior={d.get('interior_violations')} boundary={d.get('boundary_violations')} status={d.get('status')}")
    return 0 if (d.get("status") == "PASS" and p.returncode == 0) else 1
if __name__ == "__main__":
    sys.exit(main())
