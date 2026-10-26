"""Stage 11.8B — default EOS-80 and explicit LEGACY fallback verification."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import netCDF4 as nc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/validation/default_eos80_verification.json"

def digest(p: Path) -> str:
    h = hashlib.md5()
    h.update(p.read_bytes())
    return h.hexdigest()

def nc_hashes(run: str) -> dict:
    d = ROOT / "data/runs" / run / "output/nc"
    files = sorted(d.glob("results_day_*.nc"))
    return {p.name: digest(p) for p in files}

def attrs(run: str) -> dict:
    p = ROOT / "data/runs" / run / "output/nc/results_day_00.nc"
    with nc.Dataset(p) as d:
        return {a: d.getncattr(a) for a in d.ncattrs()
                if a in ("eos_mode", "scheduler_mode")}

def main() -> None:
    default = "default_eos80_verify"
    explicit = "explicit_eos80_verify"
    matrix_eos = "matrix_jan_eos80_n1"
    legacy = "legacy_fallback_verify"
    matrix_legacy = "matrix_jan_legacy_n1"
    dh, eh, mh, lh, mlh = (nc_hashes(r) for r in (default, explicit, matrix_eos, legacy, matrix_legacy))
    result = {
        "stage": "11.8B",
        "default_run": default,
        "explicit_eos80_run": explicit,
        "legacy_fallback_run": legacy,
        "metadata": {
            default: attrs(default),
            explicit: attrs(explicit),
            legacy: attrs(legacy),
        },
        "comparisons": {
            "default_vs_explicit_eos80": {
                "nc_files": len(dh),
                "all_md5_identical": dh == eh,
                "day01_md5": dh.get("results_day_01.nc"),
            },
            "default_vs_matrix_jan_eos80": {
                "nc_files": len(dh),
                "all_md5_identical": dh == mh,
                "day01_md5": dh.get("results_day_01.nc"),
            },
            "legacy_fallback_vs_matrix_jan_legacy": {
                "nc_files": len(lh),
                "all_md5_identical": lh == mlh,
                "day01_md5": lh.get("results_day_01.nc"),
            },
        },
        "verdict": {
            "default_uses_eos80": attrs(default).get("eos_mode") == "EOS80",
            "explicit_eos80_uses_eos80": attrs(explicit).get("eos_mode") == "EOS80",
            "legacy_fallback_uses_legacy": attrs(legacy).get("eos_mode") == "LEGACY",
            "default_bit_identical_to_explicit": dh == eh,
            "default_bit_identical_to_matrix_eos80": dh == mh,
            "legacy_bit_identical_to_matrix_legacy": lh == mlh,
        },
        "note": "All outputs compared by MD5 over every results_day_*.nc file; "
                "the three 30-day confirmations used the standard Jan protective config.",
    }
    result["PASS"] = all(result["verdict"].values())
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
