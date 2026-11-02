#!/usr/bin/env python3
"""CI-safe tests for python/reanalysis/verify_manifest.py."""

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "verify_manifest", ROOT / "python/reanalysis/verify_manifest.py")
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)

import hashlib


def test_good_and_bad(tmp: Path) -> None:
    data = tmp / "m.nc"
    data.write_bytes(b"stage12.9-test")
    h = hashlib.sha256(data.read_bytes()).hexdigest()
    man = {"dataset_id": "test", "months": {"2020-01": {
        "path": str(data), "size_bytes": data.stat().st_size, "sha256": h}}}
    assert vm.verify_entries(man, tmp) == []
    man["months"]["2020-01"]["sha256"] = "0" * 64
    errs = vm.verify_entries(man, tmp)
    assert len(errs) == 1 and "sha256" in errs[0]
    man["months"]["2020-01"]["path"] = str(tmp / "missing.nc")
    errs = vm.verify_entries(man, tmp)
    assert any("missing" in e for e in errs)


def test_combine(tmp: Path) -> None:
    for i, name in enumerate(("a", "b")):
        (tmp / f"{name}.nc").write_bytes(b"x")
        (tmp / f"{name}.json").write_text(json.dumps({"months": {
            f"2020-0{i+1}": {"path": str(tmp / f"{name}.nc"),
                             "size_bytes": 1, "sha256": "z"}}}))
    out = tmp / "merged.json"
    m = vm.combine([tmp / "a.json", tmp / "b.json"], out)
    assert m["n_months"] == 2 and out.exists()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        test_good_and_bad(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_combine(Path(d))
    print("SUCCESS: verify_manifest tests passed")
