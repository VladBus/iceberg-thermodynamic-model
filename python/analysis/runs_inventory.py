#!/usr/bin/env python3
"""Inventory data/runs/ (sizes + classification + recommendations). NO deletion."""
import json, re, subprocess
from pathlib import Path
PROJECT = Path(__file__).resolve().parents[2]
RUNS = PROJECT / "data/runs"
OUT_VAL = PROJECT / "data/validation/runs_inventory_result.json"
OUT_RAW = PROJECT / "data/runs_inventory.json"

def size_mb(p):
    out = subprocess.run(["du","-sm",str(p)], capture_output=True, text=True).stdout
    return float(out.split()[0]) if out else 0.0

def classify(name):
    if re.match(r"t3(c)?_", name) or name.startswith("t3_"):
        return "CRITICAL"
    if re.match(r"stage11\.8", name):
        return "CRITICAL"
    if re.match(r"stage11\.7E4", name):
        return "CRITICAL"
    if re.match(r"(test_|t3_smoke|t3c_smoke|probe|tmp)", name):
        return "TEMPORARY"
    return "ARCHIVE"

def main():
    if not RUNS.exists():
        print("SKIP: data/runs absent"); return 0
    rows = []
    for p in sorted(RUNS.iterdir()):
        if not p.is_dir(): continue
        rows.append({"name": p.name, "size_mb": size_mb(p), "class": classify(p.name)})
    total = sum(r["size_mb"] for r in rows)
    by = {c: [r for r in rows if r["class"] == c] for c in ("CRITICAL","ARCHIVE","TEMPORARY")}
    summary = {c: {"count": len(v), "size_mb": round(sum(r["size_mb"] for r in v), 1)} for c,v in by.items()}
    # recommendations: archive compress ~3x (save 2/3), temporary delete (save 100%)
    savings = round(sum(r["size_mb"] for r in by["ARCHIVE"])*2/3 + sum(r["size_mb"] for r in by["TEMPORARY"]), 1)
    out = {"total_mb": round(total,1), "total_gb": round(total/1024,2),
           "summary": summary, "estimated_savings_mb": savings,
           "estimate_note": "archive ~3x gzip; temporary deleted fully; NOT executed",
           "runs": rows}
    OUT_VAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_VAL.write_text(json.dumps(out, indent=2)); OUT_RAW.write_text(json.dumps(out, indent=2))
    print(f"total {out['total_gb']} GB ({out['total_mb']} MB);", summary)
    print(f"estimated savings {savings} MB (recommendation only, nothing deleted)")
    print(f"Results: {OUT_VAL}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
