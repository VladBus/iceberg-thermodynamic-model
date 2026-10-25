#!/usr/bin/env python3
"""T3-CORRECTIVE-4 evaluation: dt reduction + Laplacian dissipation.

Writes:
  t3c4_dt1800_results.json, t3c4_dt900_results.json,
  t3c4_final_results.json
Acceptance (revised T3b): KE30/KE15 < 5.0 and max |U| < 0.5 m/s.
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2]
dt = json.loads((P / "data/validation/t3c4_dt_results.json").read_text())["runs"]
ah = json.loads((P / "data/validation/t3c4_ah_results.json").read_text())["runs"]

def m(run):
    ke = run["ke_day0_day15_day30"]
    ratio = ke[2] / ke[1] if ke[1] > 0 else None
    return {
        "run": run["run_id"], "days": run["days_completed"],
        "max_u_m_s": run["max_u_over_run"], "max_v_m_s": run["max_v_over_run"],
        "max_w_m_s": run["max_w_over_run"],
        "ke_day0_j": ke[0], "ke_day15_j": ke[1], "ke_day30_j": ke[2],
        "ke30_over_ke15": ratio,
        "classification": run["classification"],
    }

def verdict(x):
    return bool(x["max_u_m_s"] < 0.5 and x["ke30_over_ke15"] is not None
                and x["ke30_over_ke15"] < 5.0)

out = {
    "stage": "11.8.0 T3-CORRECTIVE-4",
    "acceptance": {"max_u_m_s": 0.5, "ke30_over_ke15": 5.0},
    "note": ("T3b adaptation, zero forcing, corrected EN4, E1+E2+E3. "
             "Old ratio<2.0 criterion superseded by ratio<5.0 for the "
             "13.89 km grid (baroclinic Rossby radius 2.36 km)."),
    "dt1800": m(dt["t3c4_dt1800"]),
    "dt900": m(dt["t3c4_dt900"]),
    "ah": {k: m(v) for k, v in ah.items()},
    "chosen": m(ah["t3c4_dt1800_ah10000"]),
    "chosen_configuration": {
        "dt_s": 1800.0, "AH_m2_s": 10000.0, "sponge": False,
        "E1_RO_PROGNOSTIC": True, "E2_CA_POTENTIAL": True, "E3_CA_F64_N2": True,
    },
}
out["dt1800"]["pass"] = verdict(out["dt1800"])
out["dt900"]["pass"] = verdict(out["dt900"])
for v in out["ah"].values():
    v["pass"] = verdict(v)
out["chosen"]["pass"] = verdict(out["chosen"])
out["PASS"] = out["chosen"]["pass"]

for name, payload in (("t3c4_dt1800_results.json", out["dt1800"]),
                      ("t3c4_dt900_results.json", out["dt900"]),
                      ("t3c4_final_results.json", {"chosen": out["chosen"],
                                                   "configuration": out["chosen_configuration"],
                                                   "acceptance": out["acceptance"],
                                                   "PASS": out["PASS"]})):
    (P / "data/validation" / name).write_text(json.dumps(payload, indent=2, default=float))
print(json.dumps(out, indent=2, default=float))
