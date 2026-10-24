#!/usr/bin/env python3
"""
Stage 11.8.0 T3 — rest-state analysis verification.

Regenerates data/validation/t3_rest_result.json from the T3 run outputs (when
present) and verifies the analysis structure: 30 days per run, daily series
length 31, conservation keys, classification, and no missing metrics.

SKIP (exit 0) when the run outputs are absent (clean CI checkout).
Exit 1 only if the analysis is malformed.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
RUNS = ["t3_legacy_canonical", "t3_eos80_canonical", "t3_legacy_rebuild"]
RUN_ROOT = PROJECT / "data/runs"
OUT = PROJECT / "data/validation/t3_rest_result.json"
ANALYSIS = PROJECT / "python/analysis/stage11.8_T3_rest_state.py"


def main():
    if not (RUN_ROOT / RUNS[0] / "output/nc/results_day_00.nc").exists():
        print("SKIP: T3 run outputs absent (data bundle not in CI).")
        return 0
    cmd = [sys.executable, str(ANALYSIS)]
    for r in RUNS:
        cmd += ["--run", r]
    cmd += ["--out", str(OUT)]
    p = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True)
    print(p.stdout[-3000:])
    if p.returncode != 0:
        print("FAIL: analysis script failed")
        print(p.stderr[-2000:])
        return 1
    data = json.loads(OUT.read_text())
    issues = []
    for r in RUNS:
        v = data["runs"].get(r)
        if not v:
            issues.append(f"{r}: missing from analysis")
            continue
        if v["days_completed"] != 30:
            issues.append(f"{r}: days_completed={v['days_completed']} (expected 30)")
        if len(v.get("daily", [])) != 31:
            issues.append(f"{r}: daily series {len(v.get('daily', []))} (expected 31)")
        if v["classification"] not in ("STABLE", "DRIFTING", "UNSTABLE"):
            issues.append(f"{r}: bad classification {v['classification']}")
        for key in ("volume_rel", "heat_rel", "salt_rel"):
            if key not in v["conservation"]:
                issues.append(f"{r}: missing conservation {key}")
        if v["max_u_over_run"] is None or v["max_v_over_run"] is None:
            issues.append(f"{r}: missing max velocities")
        print(f"{r}: {v['days_completed']} d, {v['classification']}, "
              f"Umax={v['max_u_over_run']:.3f}, Vmax={v['max_v_over_run']:.3f}, "
              f"heat_rel={v['conservation']['heat_rel']:.2e}, "
              f"salt_rel={v['conservation']['salt_rel']:.2e}")
    if issues:
        for i in issues:
            print("FAIL:", i)
        return 1
    print("T3 analysis verified (structure complete; classification is diagnostic).")
    return 0


if __name__ == "__main__":
    sys.exit(main())