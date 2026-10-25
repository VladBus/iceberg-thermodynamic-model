#!/usr/bin/env python3
"""T3b adaptation evaluation (Stage 11.8.0 T3-CORRECTIVE-3).

T3b: real EN4 T/S, zero forcing, zero initial velocity (rest gate).
Acceptance: max |U| < 0.5 m/s, KE30/KE15 < 2.0, no exponential growth.
Reads the 30-day experiment JSON and writes t3c3_fix_results.json.
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2]
src = json.loads((P / "data/validation/t3c3_experiments.json").read_text())["runs"]
base = json.loads((P / "data/validation/t3_rest_fix_result.json").read_text())["runs"]["t3c_legacy_canonical"]

def metrics(run):
    ke = run["ke_day0_day15_day30"]
    ratio = ke[2] / ke[1] if ke[1] > 0 else None
    return {
        "run": run["run_id"],
        "days": run["days_completed"],
        "max_u_m_s": run["max_u_over_run"],
        "max_v_m_s": run["max_v_over_run"],
        "max_w_m_s": run["max_w_over_run"],
        "ke_day0_j": ke[0], "ke_day15_j": ke[1], "ke_day30_j": ke[2],
        "ke30_over_ke15": ratio,
        "classification": run["classification"],
    }

out = {
    "stage": "11.8.0 T3-CORRECTIVE-3",
    "test": "T3b adaptation (real EN4 T/S, zero forcing, zero initial velocity)",
    "acceptance": {"max_u_m_s": 0.5, "ke30_over_ke15": 2.0},
    "baseline": metrics(base),
    "experiments": {k: metrics(v) for k, v in src.items()},
    "t3b_primary": metrics(src["t3c3_all"]),
}
m = out["t3b_primary"]
out["t3b_pass"] = bool(m["max_u_m_s"] < 0.5 and m["ke30_over_ke15"] is not None
                       and m["ke30_over_ke15"] < 2.0)
out["t3a_note"] = ("T3a pure rest (homogeneous T/S, real bathymetry): max |U| "
                   "< 1e-6 m/s, no PGF. Documented; not executed in this stage.")
out["findings"] = {
    "E1_RO_PROGNOSTIC": "implemented; no effect in practice because conv_adj already recomputes RO for every wet column after T/S mixing.",
    "E2_CA_POTENTIAL": "implemented; no effect in LEGACY (Eckart is pressure-independent); active only with EOS80.",
    "E3_CA_F64_N2": "implemented; reduces CA mixings (day 2: 61,454 vs 7,083,949) and guard hits (0 vs 1001), but does not stabilize.",
    "E6_BOUNDARY_SPONGE": "tested (width 8-20, tau 1 h-1 day); reduces peak but does not produce a plateau; not used in T3b.",
}
out["conclusion"] = ("T3b FAILS: the coupled advection/density system remains unstable "
                     "even with E1-E3; the requested fixes do not meet the acceptance "
                     "criteria. T4 remains NO-GO.")
(P / "data/validation/t3c3_fix_results.json").write_text(json.dumps(out, indent=2, default=float))
print(json.dumps(out, indent=2, default=float))
