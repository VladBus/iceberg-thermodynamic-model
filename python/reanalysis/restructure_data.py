#!/usr/bin/env python3
"""Stage 12.9 Phase 0: canonical data layout + provenance-preserving cleanup.

- Creates data/input/{reanalysis,static,observations}.
- Protects observations (symlink to data/validation/observations).
- Copies static grid + GLORYS static into data/input/static/.
- Archives SHA-256/size for every old experimental reanalysis/ERA5 NetCDF,
  writes docs/validation/provenance_archive/stage12.9_deleted_inputs.csv,
  then deletes only those files.
- Leaves Stage 11 initial-condition/ocean/ice inputs untouched.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

ROOT = Path(".")
ARCHIVE = Path("docs/validation/provenance_archive")
OLD_GLO = Path("data/input/raw/reanalysis/glorys12")
OLD_ERA5_RAW = Path("data/input/raw/era5")
OLD_ERA5_PROC = Path("data/input/processed/era5")
CANON = Path("data/input/reanalysis")
STATIC = Path("data/input/static")
OBS = Path("data/input/observations")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for d in (CANON / "glorys" / "2020", CANON / "glorys" / "2024",
              CANON / "era5", CANON / "wam", STATIC):
        d.mkdir(parents=True, exist_ok=True)

    # Static inputs: keep copies in canonical static/.
    grid_src = Path("data/input/processed/grid/grid.nc")
    if grid_src.exists() and not (STATIC / "grid.nc").exists():
        shutil.copy2(grid_src, STATIC / "grid.nc")
    static_src = OLD_GLO / "static" / "glorys12_static_barents.nc"
    if static_src.exists() and not (STATIC / "glorys_static_barents.nc").exists():
        shutil.copy2(static_src, STATIC / "glorys_static_barents.nc")

    # Observations: protected; canonical symlink only.
    if not OBS.exists():
        OBS.symlink_to(Path("../../validation/observations"))

    # Collect old experimental NetCDF (never observations/static/ocean init).
    old = []
    old += sorted((OLD_GLO / "2020").glob("*.nc")) if (OLD_GLO / "2020").exists() else []
    old += sorted((OLD_GLO / "antarctic").glob("*.nc")) if (OLD_GLO / "antarctic").exists() else []
    old += sorted(OLD_ERA5_RAW.rglob("*.nc")) if OLD_ERA5_RAW.exists() else []
    old += sorted(OLD_ERA5_PROC.rglob("*.nc")) if OLD_ERA5_PROC.exists() else []
    # Never include static/observation files.
    old = [p for p in old if "static" not in p.parts and "observations" not in p.parts]

    rows = []
    for p in old:
        rows.append({"path": str(p), "size_bytes": p.stat().st_size,
                     "sha256": sha256(p), "reason": "Stage 12.9 cleanup: old experimental reanalysis/ERA5 input"})
    manifest = ARCHIVE / "stage12.9_deleted_inputs.csv"
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "size_bytes", "sha256", "reason"])
        w.writeheader(); w.writerows(rows)
    total = sum(r["size_bytes"] for r in rows)
    (ARCHIVE / "README.md").write_text(
        "# Provenance archive\n\n"
        "Deleted inputs are listed in `stage12.9_deleted_inputs.csv` with size and "
        "SHA-256 before deletion. Observations and static inputs were preserved.\n")
    print(f"archived {len(rows)} files, {total/1e9:.3f} GB -> {manifest}")
    for r in rows:
        print(f"  {r['size_bytes']/1e6:8.1f} MB  {r['path']}")

    for p in old:
        p.unlink()
    # Remove now-empty old directories, but keep legacy compatibility symlinks.
    for d in (OLD_GLO / "antarctic", OLD_GLO / "2020"):
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    if OLD_ERA5_PROC.exists():
        shutil.rmtree(OLD_ERA5_PROC)
        OLD_ERA5_PROC.symlink_to(Path("../../reanalysis/era5"))
    if OLD_ERA5_RAW.exists():
        shutil.rmtree(OLD_ERA5_RAW)
        OLD_ERA5_RAW.symlink_to(Path("../reanalysis/era5"))
    # Legacy compatibility: scripts still referring to old paths resolve to canon.
    if OLD_GLO.exists() and not (OLD_GLO / "2020").exists():
        (OLD_GLO / "2020").symlink_to(Path("../../../reanalysis/glorys/2020"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
