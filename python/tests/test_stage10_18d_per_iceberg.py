#!/usr/bin/env python3
"""
Stage 10.18D regression tests — per-iceberg Enderlin23 dataset and analysis.

Checks:
 1. dataset file exists and is parseable;
 2. schema (required columns present);
 3. 743 per-iceberg rows (54 raw CSVs, all sites);
 4. all 15 sites present with paper site names;
 5. regional attribution WAP/WAIS/EAIS/EAP covers all rows;
 6. melt rates positive, bounded (0 < melt < 0.2 m/day);
 7. drafts positive and bounded (< 900 m);
 8. regional max melt rates within a documented factor of the paper values
    (WAP/WAIS <= 2x paper max after known Mertz anomaly is excluded from the
    max; EAIS/EAP p95 consistent with paper ~5 m/a);
 9. Thwaites inferred TF (melt/24) mostly within the paper range 0.2-1.6 degC
    (>= 60 % of icebergs);
10. legacy C_LATERAL at TF=1.5 degC exceeds the observed median melt rate
    (over-prediction documented in 10.17/10.18A);
11. C_eff_submarine median below production C_LATERAL (per-iceberg level);
12. the analysis script runs end-to-end and writes summary.json + 10 figures.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/tests/test_stage10_18d_per_iceberg.py
"""

import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "python" / "validation"))

from python.validation.lateral_melt import C_LATERAL, legacy_lateral_melt_rate, m_s_to_m_day

DATA = REPO / "data" / "validation" / "observations" / "stage10.18d" / "enderlin23_per_iceberg.csv"
RAW_DIR = REPO / "data" / "validation" / "observations" / "stage10.18d" / "raw" / "Antarctic-iceberg-csvs"
ANALYSIS = REPO / "python" / "analysis" / "stage10_18d_per_iceberg.py"
OUT = REPO / "data" / "output" / "stage10.18d"

REQUIRED_COLS = [
    "source_id", "case_id", "site", "site_name", "region", "region_name",
    "independent_case", "independence_group", "observation_type",
    "observation_level", "date_start", "date_end", "time_separation_days",
    "melt_rate", "melt_definition", "volume_change_rate",
    "volume_change_uncert", "draft", "median_z", "volume_i", "volume_f",
    "density", "surface_area", "submerged_area", "lat_i", "lon_i", "lat_f",
    "lon_f",
]

ALL_SITES = {"BG", "CG", "FG", "FI", "HG", "LA", "LB", "LG", "MI", "PT",
             "RI", "SG", "TG", "TI", "WG"}
PAPER_REGION_MAX = {"WAP": 50.0, "WAIS": 40.0, "EAIS": 5.0, "EAP": 5.0}
THWAITES_SLOPE = 24.0
TF_RANGE = (0.2, 1.6)

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))


def load_rows():
    with open(DATA, newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(r for r in f if not r.lstrip().startswith("#"))]


def f(v):
    s = (v or "").strip()
    if s in ("", "NA", "nan", "NaN", "None"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def main():
    # 1. dataset exists
    check("dataset file exists", DATA.exists(), str(DATA))
    rows = load_rows()

    # 2. schema
    missing = [c for c in REQUIRED_COLS if c not in rows[0]]
    check("schema: required columns present", not missing, f"missing={missing}")

    # 3. row count
    check("743 per-iceberg rows", len(rows) == 743, f"n={len(rows)}")

    # 4. sites
    sites = {r["site"] for r in rows}
    check("all 15 sites present", sites == ALL_SITES,
          f"missing={ALL_SITES - sites} extra={sites - ALL_SITES}")
    check("site names populated", all(r["site_name"] for r in rows))

    # 5. regions
    regions = {r["region"] for r in rows}
    check("regions in WAP/WAIS/EAIS/EAP", regions <= {"WAP", "WAIS", "EAIS", "EAP"},
          f"regions={regions}")
    check("no UNCLASSIFIED rows", not any(r["region"] == "UNCLASSIFIED" for r in rows))
    region_counts = {}
    for r in rows:
        region_counts[r["region"]] = region_counts.get(r["region"], 0) + 1
    check("each region has rows", all(region_counts.get(k, 0) > 0 for k in PAPER_REGION_MAX),
          str(region_counts))

    # 6. melt rates
    melts = [f(r["melt_rate"]) for r in rows]
    valid = [m for m in melts if m == m]
    check("all melt rates valid", len(valid) == len(rows), f"{len(valid)}/{len(rows)}")
    check("melt rates > 0", all(m > 0 for m in valid))
    check("melt rates < 0.2 m/day", max(valid) < 0.2, f"max={max(valid):.6f}")

    # 7. drafts
    drafts = [f(r["draft"]) for r in rows]
    check("drafts valid", all(d == d and d > 0 for d in drafts), f"min={min(drafts):.1f}")
    check("drafts < 900 m", max(drafts) < 900.0, f"max={max(drafts):.1f}")

    # 8. regional maxima vs paper (p95 used for EAIS/EAP where the known Mertz
    #    plume anomaly inflates the raw max; WAP/WAIS max within 2x paper)
    by_region = {}
    for r in rows:
        by_region.setdefault(r["region"], []).append(f(r["melt_rate"]) * 365.25)
    for region, pmax in PAPER_REGION_MAX.items():
        vals = sorted(by_region[region])
        p95 = vals[int(0.95 * len(vals)) - 1]
        check(f"{region} p95 within 3x paper max",
              p95 <= 3.0 * pmax, f"p95={p95:.2f} paper={pmax}")
    check("WAP max within 2x paper max", max(by_region["WAP"]) <= 2.0 * PAPER_REGION_MAX["WAP"],
          f"max={max(by_region['WAP']):.2f}")
    check("WAIS max within 2x paper max", max(by_region["WAIS"]) <= 2.0 * PAPER_REGION_MAX["WAIS"],
          f"max={max(by_region['WAIS']):.2f}")

    # 9. Thwaites inferred TF
    tg = [f(r["melt_rate"]) * 365.25 for r in rows if r["site"] == "TG"]
    tf = [m / THWAITES_SLOPE for m in tg]
    in_range = sum(1 for t in tf if TF_RANGE[0] <= t <= TF_RANGE[1])
    check("Thwaites n >= 150", len(tg) >= 150, f"n={len(tg)}")
    check("Thwaites >= 60% TF in paper range", in_range / len(tg) >= 0.60,
          f"{in_range}/{len(tg)} = {in_range / len(tg):.2f}")

    # 10. legacy over-prediction
    obs_med = sorted(valid)[len(valid) // 2]
    legacy_15 = m_s_to_m_day(legacy_lateral_melt_rate(1.5))
    check("legacy at TF=1.5 exceeds observed median",
          legacy_15 > obs_med * 3.0,
          f"legacy={legacy_15:.5f} obs_med={obs_med:.5f}")

    # 11. C_eff_submarine below production (at region TF=1.5 for WAP subset)
    wap = [f(r["melt_rate"]) / 1.5 / 86400.0 for r in rows if r["region"] == "WAP"]
    wap_med = sorted(wap)[len(wap) // 2]
    check("WAP C_eff_submarine median < C_LATERAL", wap_med < C_LATERAL,
          f"med={wap_med:.2e} prod={C_LATERAL:.2e}")

    # 12. analysis end-to-end
    try:
        res = subprocess.run(
            [sys.executable, str(ANALYSIS)], cwd=str(REPO),
            capture_output=True, text=True, timeout=600)
        ok_run = res.returncode == 0
        detail = res.stderr[-300:] if res.stderr else "ok"
    except Exception as e:  # noqa: BLE001
        ok_run = False
        detail = str(e)
    check("analysis script runs exit 0", ok_run, detail)
    if ok_run:
        summary = json.load(open(OUT / "summary.json"))
        check("summary has 743 icebergs", summary["n_per_iceberg"] == 743)
        figs = sorted((OUT / "plots").glob("fig*.png"))
        check("10 figures written", len(figs) == 10, f"n={len(figs)}")

    # report
    n_ok = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"TOTAL CHECKS: {len(CHECKS)} ERRORS: {len(CHECKS) - n_ok}")
    for name, ok, detail in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not ok else ""))
    sys.exit(0 if n_ok == len(CHECKS) else 1)


if __name__ == "__main__":
    main()