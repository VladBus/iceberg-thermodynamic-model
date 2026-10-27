#!/usr/bin/env python3
"""Stage 11.10 — data/runs cleanup.

Default is DRY RUN. Pass --execute to delete/trim.
No files outside data/runs are touched. No archive is created unless
--archive is supplied (not used by default).

KEEP:
  - matrix_{jan,apr,jul,oct}_{legacy,eos80}_n1
  - t5_90day*, t5c*_90day*
  - default_eos80_verify, explicit_eos80_verify, legacy_fallback_verify
  - repro_apr_eos80, repro_jul_legacy, repro_oct_eos80
  - t3c4_dt1800_ah10000, t4_wind_forcing, t5_30day_apr30,
    t6s_jul_legacy, t6s_oct_legacy, t6s_jan_production
For kept runs retain config.env, *.log, *.csv, results_day_00.nc and the
last results_day_*.nc; delete all intermediate NC and non-kept run dirs.
"""
from __future__ import annotations
import argparse, json, os, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"

KEEP_PATTERNS = [
    re.compile(r"^matrix_(jan|apr|jul|oct)_(legacy|eos80)_n1$"),
    re.compile(r"^t5_90day"),
    re.compile(r"^t5c.*_90day"),
]
KEEP_EXACT = {
    "default_eos80_verify", "explicit_eos80_verify", "legacy_fallback_verify",
    "repro_apr_eos80", "repro_jul_legacy", "repro_oct_eos80",
    "t3c4_dt1800_ah10000", "t4_wind_forcing", "t5_30day_apr30",
    "t6s_jul_legacy", "t6s_oct_legacy", "t6s_jan_production",
}

def should_keep(name: str) -> bool:
    return name in KEEP_EXACT or any(p.search(name) for p in KEEP_PATTERNS)

def size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

def keep_file(p: Path) -> bool:
    if p.name == "config.env" or p.suffix == ".log" or p.suffix == ".csv":
        return True
    if p.name == "results_day_00.nc" or p.name == "results_day_final.nc":
        return True
    return False

def trim_run(run: Path, execute: bool) -> tuple[int, int]:
    """Return (files_deleted, bytes_deleted); keep first/last NC + logs/CSV."""
    nc = sorted((run / "output" / "nc").glob("results_day_*.nc"))
    keep_nc = set()
    if nc:
        keep_nc.add(nc[0].name)
        last = run / "output" / "nc" / "results_day_final.nc"
        keep_nc.add(last.name if last.exists() else nc[-1].name)
    deleted = 0
    freed = 0
    for p in run.rglob("*"):
        if not p.is_file():
            continue
        parent_rel = p.relative_to(run)
        if p.name == "config.env":
            continue
        if p.suffix in (".log", ".csv"):
            continue
        if "output/nc" in parent_rel.as_posix():
            if p.name in keep_nc:
                continue
        # remove intermediate NC and any non-kept forensic file
        freed += p.stat().st_size
        deleted += 1
        if execute:
            p.unlink()
    # remove empty subdirs except output/logs, output/csv, output/nc
    return deleted, freed

def write_config(run: Path, execute: bool) -> None:
    cfg = run / "config.env"
    if cfg.exists():
        return
    text = (
        f"# Stage 11.10 retained run metadata\n"
        f"RUN_ID={run.name}\n"
        f"RETAINED_AT=2026-10-27\n"
        f"POLICY=first_last_netcdf_plus_logs_csv\n"
        f"NOTE=Full daily NC removed by scripts/cleanup_runs.py; daily CSV retained.\n"
    )
    if execute:
        cfg.write_text(text)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--archive", action="store_true", help="unused; deletion is the default")
    args = ap.parse_args()
    before = size(RUNS)
    dirs = sorted([p for p in RUNS.iterdir() if p.is_dir()], key=lambda p: p.name)
    keep = [p for p in dirs if should_keep(p.name)]
    drop = [p for p in dirs if not should_keep(p.name)]
    print(f"DRY-RUN={not args.execute} before={before/1e9:.3f} GB dirs={len(dirs)} keep={len(keep)} drop={len(drop)}")
    print("KEEP:")
    for p in keep:
        print(f"  {p.name} {size(p)/1e9:.3f} GB")
    print("DROP count", len(drop))
    if not args.execute:
        print("Run with --execute to apply.")
        return
    freed_drop = 0
    for p in drop:
        freed_drop += size(p)
        shutil.rmtree(p)
    freed_trim = 0
    for p in keep:
        write_config(p, True)
        d, b = trim_run(p, True)
        freed_trim += b
        print(f"trim {p.name}: files={d} freed={b/1e9:.3f} GB size_now={size(p)/1e9:.3f} GB")
    after = size(RUNS)
    manifest = {
        "before_gb": before / 1e9,
        "after_gb": after / 1e9,
        "dropped_dirs": len(drop),
        "kept_dirs": len(keep),
        "freed_drop_gb": freed_drop / 1e9,
        "freed_trim_gb": freed_trim / 1e9,
        "kept": [p.name for p in keep],
        "executed": True,
        "policy": "first/last NC + config.env + logs + CSV; no outside data/runs changes",
    }
    (RUNS / "KEEP_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
