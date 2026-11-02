#!/usr/bin/env python3
"""Verify tracked reanalysis manifests against local NetCDF files.

Manifest schema (Stage 12.9):
  {"dataset_id": ..., "version": ..., "months": {
      "2020-01": {"path": "...", "size_bytes": N, "sha256": "..."}, ...}}

Usage:
  python python/reanalysis/verify_manifest.py --manifest docs/validation/stage12.9_wam_manifest.json
  python python/reanalysis/verify_manifest.py --combine a.json b.json \
      --output docs/validation/stage12.9_wam_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def verify_entries(manifest: dict, root: Path, check_hash: bool = True) -> list[str]:
    errors: list[str] = []
    for key, entry in manifest.get("months", {}).items():
        path = Path(entry["path"])
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            errors.append(f"{key}: missing {path}")
            continue
        size = path.stat().st_size
        if "size_bytes" in entry and size != int(entry["size_bytes"]):
            errors.append(f"{key}: size {size} != {entry['size_bytes']}")
        if check_hash and entry.get("sha256"):
            got = sha256(path)
            if got != entry["sha256"]:
                errors.append(f"{key}: sha256 {got} != {entry['sha256']}")
    return errors


def combine(manifests: list[Path], output: Path) -> dict:
    merged = None
    for p in manifests:
        d = load_manifest(p)
        if merged is None:
            merged = {k: v for k, v in d.items() if k != "months"}
            merged["months"] = {}
        merged["months"].update(d.get("months", {}))
    if merged is None:
        raise SystemExit("no manifests supplied")
    merged["n_months"] = len(merged["months"])
    merged["total_bytes"] = sum(int(v.get("size_bytes", 0)) for v in merged["months"].values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merged, indent=2) + "\n")
    return merged


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--combine", type=Path, nargs="+")
    p.add_argument("--output", type=Path)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--no-hash", action="store_true")
    a = p.parse_args()
    if a.combine:
        if not a.output:
            raise SystemExit("--output is required with --combine")
        merged = combine(a.combine, a.output)
        print(f"wrote {a.output}: {merged['n_months']} months, "
              f"{merged['total_bytes']/1e9:.3f} GB")
        return 0
    if not a.manifest:
        raise SystemExit("--manifest or --combine required")
    man = load_manifest(a.manifest)
    errors = verify_entries(man, a.root, check_hash=not a.no_hash)
    if errors:
        print("MANIFEST VERIFICATION FAILED")
        for e in errors:
            print("  " + e)
        return 1
    print(f"OK: {len(man.get('months', {}))} months verified "
          f"({sum(int(v.get('size_bytes', 0)) for v in man['months'].values())/1e9:.3f} GB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
