#!/usr/bin/env python3
"""Stage 12.9 GLORYS daily acquisition (CMEMS subset, sequential).

Months: 2020-01..12 and 2024-01/07. Output canonical monthly NetCDF, per-month
3 GB gate, tracked manifest with SHA-256. No NetCDF is committed.

Usage:
  python python/reanalysis/download_glorys_2024.py [--months 2020-02,...]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

OUT = Path("data/input/reanalysis/glorys")
MANIFEST = Path("docs/validation/stage12.9_glorys_manifest.json")
DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
VARS = ["thetao", "so", "uo", "vo", "zos", "siconc", "sithick", "usi", "vsi"]
GATE = 3.0e9
MONTHS = [f"2020-{m:02d}" for m in range(1, 13)] + ["2024-01", "2024-07"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def cmems_env() -> dict:
    env = os.environ.copy()
    p = Path.home()/".copernicusmarine/.copernicusmarine-credentials"
    if p.exists():
        raw = base64.b64decode(p.read_text().strip()).decode()
        d = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
        env.setdefault("COPERNICUSMARINE_SERVICE_USERNAME", d.get("username", ""))
        env.setdefault("COPERNICUSMARINE_SERVICE_PASSWORD", d.get("password", ""))
    return env


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--months", default="")
    a = p.parse_args()
    months = [m.strip() for m in a.months.split(",") if m.strip()] or MONTHS
    OUT.mkdir(parents=True, exist_ok=True)
    man = {"dataset_id": DATASET, "bbox": [63, 86, 5, 80],
           "depth_m": [0, 600], "variables": VARS, "months": {}}
    if MANIFEST.exists():
        man = json.loads(MANIFEST.read_text())
    env = cmems_env()
    for ym in months:
        y, m = ym.split("-")
        out = OUT / y / f"glorys12_barents_{y}_{m}.nc"
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and ym in man.get("months", {}):
            print(f"skip {ym} (manifest)", flush=True)
            continue
        import calendar
        nd = calendar.monthrange(int(y), int(m))[1]
        cmd = ["copernicusmarine", "subset", "-i", DATASET]
        for v in VARS:
            cmd += ["-v", v]
        cmd += ["--minimum-longitude", "5", "--maximum-longitude", "80",
                "--minimum-latitude", "63", "--maximum-latitude", "86",
                "--minimum-depth", "0", "--maximum-depth", "600",
                "--start-datetime", f"{y}-{m}-01T00:00:00",
                "--end-datetime", f"{y}-{m}-{nd:02d}T23:59:59",
                "--output-directory", str(out.parent),
                "--output-filename", out.name,
                "--netcdf-compression-level", "4", "--chunk-size-limit", "50", "--overwrite"]
        print(f"download {ym}", flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-500:]); print(r.stderr[-500:]); return r.returncode
        size = out.stat().st_size
        print(f"  {out} {size/1e6:.1f} MB", flush=True)
        if size > GATE:
            print(f"STOP: {ym} size {size/1e9:.3f} GB > 3 GB gate", flush=True)
            return 3
        man.setdefault("months", {})[ym] = {"path": str(out), "size_bytes": size,
                                            "sha256": sha256(out)}
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(man, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
