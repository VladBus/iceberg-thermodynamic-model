#!/usr/bin/env python3
"""Verify Copernicus Marine catalogue availability for Stage 12.

This script is a *catalogue probe only*: it runs `copernicusmarine describe`
and checks that the GLORYS12 primary product/dataset and its required
variables exist. It never downloads fields.

Usage:
    python python/reanalysis/copernicus_probe.py
    python python/reanalysis/copernicus_probe.py --json-out data/validation/reanalysis_catalog_probe.json

Exit codes:
    0 — primary product and all required variables found
    1 — catalogue/product/schema check failed
    2 — CLI missing or unparsable output
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any

PRIMARY_PRODUCT = "GLOBAL_MULTIYEAR_PHY_001_030"
PRIMARY_DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
STATIC_DATASET = "cmems_mod_glo_phy_my_0.083deg_static"
FALLBACK_PRODUCT = "ARCTIC_MULTIYEAR_PHY_002_003"
FALLBACK_DATASET = "cmems_mod_arc_phy_my_topaz4_P1D-m"

REQUIRED_PRIMARY_VARS = {"thetao", "so", "uo", "vo", "zos", "siconc", "sithick"}
REQUIRED_STATIC_VARS = {"deptho", "mask"}


def _cli() -> str:
    explicit = os.environ.get("COPERNICUSMARINE")
    if explicit and os.path.isfile(explicit):
        return explicit
    found = shutil.which("copernicusmarine")
    if found:
        return found
    raise RuntimeError(
        "copernicusmarine not found; use the project conda environment or set "
        "COPERNICUSMARINE to the executable"
    )


def _run(cli: str, args: list[str]) -> str:
    completed = subprocess.run(
        [cli, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{cli} {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()[-1000:]}"
        )
    return completed.stdout


def _describe(cli: str, product_id: str) -> dict[str, Any]:
    raw = _run(
        cli,
        [
            "describe",
            "-p",
            product_id,
            "--disable-progress-bar",
            "--log-level",
            "ERROR",
        ],
    )
    start = raw.find("{")
    if start < 0:
        raise RuntimeError(f"describe returned no JSON for {product_id}")
    return json.loads(raw[start:])


def _product(doc: dict[str, Any], product_id: str) -> dict[str, Any]:
    for product in doc.get("products", []):
        if product.get("product_id") == product_id:
            return product
    return {}


def _dataset(product: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    for dataset in product.get("datasets", []):
        if dataset.get("dataset_id") == dataset_id:
            return dataset
    return {}


def _variables(dataset: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for version in dataset.get("versions", []):
        for part in version.get("parts", []):
            for service in part.get("services", []):
                for variable in service.get("variables", []):
                    if variable.get("short_name"):
                        names.add(variable["short_name"])
    return names


def _version_label(dataset: dict[str, Any]) -> str | None:
    versions = dataset.get("versions") or []
    return versions[0].get("label") if versions else None


def summarize() -> dict[str, Any]:
    cli = _cli()
    version = _run(cli, ["--version"]).strip()
    primary_doc = _describe(cli, PRIMARY_PRODUCT)
    fallback_doc = _describe(cli, FALLBACK_PRODUCT)

    primary = _product(primary_doc, PRIMARY_PRODUCT)
    fallback = _product(fallback_doc, FALLBACK_PRODUCT)
    daily = _dataset(primary, PRIMARY_DATASET)
    static = _dataset(primary, STATIC_DATASET)
    fallback_daily = _dataset(fallback, FALLBACK_DATASET)

    daily_vars = _variables(daily)
    static_vars = _variables(static)
    fallback_vars = _variables(fallback_daily)

    checks = {
        "primary_product_present": bool(primary),
        "primary_daily_dataset_present": bool(daily),
        "primary_static_dataset_present": bool(static),
        "primary_required_variables_present": REQUIRED_PRIMARY_VARS <= daily_vars,
        "static_required_variables_present": REQUIRED_STATIC_VARS <= static_vars,
        "fallback_product_present": bool(fallback),
        "fallback_daily_dataset_present": bool(fallback_daily),
    }

    return {
        "stage": "12.0",
        "purpose": "catalogue availability only; no data downloaded",
        "cli_version": version,
        "primary": {
            "product_id": PRIMARY_PRODUCT,
            "title": primary.get("title"),
            "doi": primary.get("digital_object_identifier"),
            "dataset_id": PRIMARY_DATASET,
            "dataset_version": _version_label(daily),
            "variables_found": sorted(daily_vars),
            "missing_variables": sorted(REQUIRED_PRIMARY_VARS - daily_vars),
            "static_dataset_id": STATIC_DATASET,
            "static_version": _version_label(static),
            "static_variables_found": sorted(static_vars),
            "static_missing_variables": sorted(REQUIRED_STATIC_VARS - static_vars),
        },
        "fallback": {
            "product_id": FALLBACK_PRODUCT,
            "title": fallback.get("title"),
            "doi": fallback.get("digital_object_identifier"),
            "dataset_id": FALLBACK_DATASET,
            "dataset_version": _version_label(fallback_daily),
            "variables_found": sorted(fallback_vars),
        },
        "checks": checks,
        "ready_for_stage_12_1": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="optional path for the summary JSON (never a NetCDF download)",
    )
    args = parser.parse_args()

    try:
        summary = summarize()
    except Exception as exc:  # noqa: BLE001 - CLI failures are reported verbatim
        print(f"copernicus probe failed: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print(f"wrote {args.json_out}", file=sys.stderr)

    return 0 if summary["ready_for_stage_12_1"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
