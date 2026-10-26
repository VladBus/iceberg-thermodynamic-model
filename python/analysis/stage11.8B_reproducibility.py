"""Stage 11.8B — matrix reproducibility audit (existing data, no model run)."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/validation/reproducibility_audit.json"

CASES = [
    ("Jan", "LEGACY", "legacy_fallback_verify", "matrix_jan_legacy_n1"),
    ("Jan", "EOS80", "default_eos80_verify", "matrix_jan_eos80_n1"),
    ("Apr", "EOS80", "repro_apr_eos80", "matrix_apr_eos80_n1"),
    ("Jul", "LEGACY", "repro_jul_legacy", "matrix_jul_legacy_n1"),
    ("Oct", "EOS80", "repro_oct_eos80", "matrix_oct_eos80_n1"),
]

def hashes(run: str) -> dict:
    d = ROOT / "data/runs" / run / "output/nc"
    out = {}
    for p in sorted(d.glob("results_day_*.nc")):
        out[p.name] = hashlib.md5(p.read_bytes()).hexdigest()
    return out

def main() -> None:
    cases = []
    for season, eos, rerun, matrix in CASES:
        a, b = hashes(rerun), hashes(matrix)
        cases.append({
            "season": season,
            "eos": eos,
            "rerun": rerun,
            "matrix": matrix,
            "nc_files": len(a),
            "all_md5_identical": a == b,
            "day01_md5": a.get("results_day_01.nc"),
            "day30_md5": a.get("results_day_30.nc") or a.get("results_day_final.nc"),
        })
    result = {
        "stage": "11.8B",
        "scope": "One representative cell per season: Jan LEGACY, Apr EOS80, "
                 "Jul LEGACY, Oct EOS80; plus Jan EOS80 default check.",
        "cases": cases,
        "all_identical": all(c["all_md5_identical"] for c in cases),
        "tolerance": "bit-identical (MD5 of every results_day_*.nc); no tolerance accepted",
        "note": "Re-runs used the same standard protective config and input files; "
                "no production scheduler cells.",
        "PASS": all(c["all_md5_identical"] for c in cases),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
