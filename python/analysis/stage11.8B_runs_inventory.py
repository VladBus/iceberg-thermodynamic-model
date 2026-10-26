"""Stage 11.8B — data/runs inventory and cleanup classification (NO deletion).

Classifies each top-level run directory by operational role:
  CRITICAL  current baselines, current matrix, T3/T4/T5/T6 validation, 11.7E4
  ARCHIVE   historical stage 11.0-11.7 runs
  TEMPORARY tests/probes/smokes/default checks/preliminary matrix runs
  DUPLICATES curated re-run candidates (keep newest; approval required)

Output: data/validation/runs_inventory_final.json
No files are deleted, moved, compressed, or archived by this script.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "runs"
OUT = ROOT / "data" / "validation" / "runs_inventory_final.json"

# Re-runs with the same experiment family whose later copy should be kept.
DUPLICATE_CANDIDATES = {
    "stage11.5C2_AprA_gain2": "stage11.5C2_AprA_gain",
    "stage11.5C2_AprB_cplfreeze2": "stage11.5C2_AprB_cplfreeze",
    "stage11.5C2_AprC_heatfreeze2": "stage11.5C2_AprC_heatfreeze",
    "stage11.5C2_janOFF2": "stage11.5C2_janOFF",
    "stage11.5C6R_AprN24b": "stage11.5C6R_AprN24",
    "stage11.5C1_janOFF3": "stage11.5C1_janOFF2",
}

def size_bytes(p: Path) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(p):
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total

def classify(name: str) -> tuple[str, str]:
    if name in DUPLICATE_CANDIDATES:
        return "DUPLICATES", f"rerun of {DUPLICATE_CANDIDATES[name]}; keep newest"
    if name.endswith("_prelim") or "prelim" in name:
        return "TEMPORARY", "preliminary matrix/extrapolation run; not a matrix cell"
    if name.startswith("test_") or "default_check" in name or "smoke" in name \
       or "probe" in name or name == "scripts":
        return "TEMPORARY", "test/probe/smoke/default-check run"
    if name.startswith(("matrix_",)):
        return "CRITICAL", "current 11.8A matrix cell"
    if name.startswith(("repro_", "default_eos80_verify", "explicit_eos80_verify",
                        "legacy_fallback_verify")):
        return "CRITICAL", "11.8B runtime/reproducibility evidence"
    if name.startswith(("t3", "t4", "t5", "t6s_")):
        return "CRITICAL", "T3/T4/T5/T6 validation evidence"
    if name.startswith("stage11.7E4"):
        return "CRITICAL", "11.7E4 sea-ice provenance/validation baseline"
    if name.startswith(("stage11.", "stage11_", "stage117", "stage116",
                        "stage115", "stage114", "stage113", "stage112",
                        "stage111", "e2_")):
        return "ARCHIVE", "historical stage 11.0-11.7 run"
    return "TEMPORARY", "unclassified/forensic run; review before cleanup"

def main() -> None:
    dirs = [p for p in RUNS.iterdir() if p.is_dir()]
    entries = []
    for p in sorted(dirs, key=lambda x: x.name):
        b = size_bytes(p)
        cls, reason = classify(p.name)
        entries.append({
            "name": p.name,
            "size_mb": round(b / 1e6, 3),
            "size_gb": round(b / 1e9, 6),
            "class": cls,
            "reason": reason,
        })
    root_files = sum(p.stat().st_size for p in RUNS.iterdir() if p.is_file())
    total = sum(e["size_gb"] for e in entries) + root_files / 1e9
    summary = {}
    for cls in ("CRITICAL", "ARCHIVE", "TEMPORARY", "DUPLICATES"):
        sel = [e for e in entries if e["class"] == cls]
        summary[cls] = {
            "count": len(sel),
            "size_gb": round(sum(e["size_gb"] for e in sel), 6),
            "runs": sel,
        }
    archive = summary["ARCHIVE"]
    temp = summary["TEMPORARY"]
    dup = summary["DUPLICATES"]
    archive_compressed = archive["size_gb"] / 3.0
    savings = archive["size_gb"] * (2.0 / 3.0) + temp["size_gb"] + dup["size_gb"]
    result = {
        "stage": "11.8B",
        "total_size_gb": round(total, 6),
        "total_runs": len(entries),
        "root_files_mb": round(root_files / 1e6, 3),
        "classification_policy": {
            "CRITICAL": "current baselines, current matrix, T3/T4/T5/T6 validation, 11.7E4",
            "ARCHIVE": "historical stage 11.0-11.7 runs (compress recommendation)",
            "TEMPORARY": "tests/probes/smokes/default checks/preliminary runs",
            "DUPLICATES": "curated rerun candidates; keep newest after approval",
        },
        "critical": summary["CRITICAL"],
        "archive": {**archive, "estimated_compressed_gb": round(archive_compressed, 6)},
        "temporary": temp,
        "duplicates": dup,
        "estimated_space_savings_gb": round(savings, 6),
        "recommendations": [
            "ARCHIVE: tar + gzip (assume ~3x; estimated compressed size shown); requires user approval.",
            "TEMPORARY: delete after user review; no deletion performed in this stage.",
            "DUPLICATES: keep the newest, delete older rerun after user approval.",
            "CRITICAL: retain active; do not delete/archive.",
            "No data/runs files were deleted, moved, compressed, or archived.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: {"count": v["count"], "size_gb": v["size_gb"]}
                      for k, v in summary.items()}, indent=2))
    print("total_gb", result["total_size_gb"], "savings_gb", result["estimated_space_savings_gb"])

if __name__ == "__main__":
    main()
