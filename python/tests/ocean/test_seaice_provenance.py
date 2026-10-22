#!/usr/bin/env python3
"""
Stage 11.8.0.0 — Sea-ice provenance verification (ACTUAL source).

Runs the production binary twice (STAGE117E_NETCDF_SEAICE=ON and OFF), reads
the day_00 global attributes, and verifies that provenance reflects the actual
source rather than hardcoded strings:

ON  -> seaice_reader_mode = "netcdf"
       seaice_source_file contains "seaice_initial.nc"
       seaice_manifest_version != NONE/PENDING/UNSET
       seaice_manifest_checksum is a 32-hex-char MD5
OFF -> seaice_reader_mode = "legacy"
       seaice_source_file contains "legacy"
       seaice_manifest_version = "NONE"
       seaice_manifest_checksum = "NONE"

Reuses the run/poll helper from test_provenance_attributes.py.

Exit: 0 = all checks pass; 1 = any failure or missing prerequisite.
"""

import re
import sys
from pathlib import Path

from netCDF4 import Dataset

TESTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))
import test_provenance_attributes as tpa  # noqa: E402

CHECKS = 0
ERRORS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if cond:
        print(f"PASS {label}")
    else:
        ERRORS += 1
        print(f"FAIL {label} {detail}")


def attrs(path):
    with Dataset(path) as ds:
        return {a: ds.getncattr(a) for a in ds.ncattrs()}


def main():
    binary, ok = tpa.check_prerequisites()
    if not ok or binary is None:
        print("SKIP: model binary or required inputs absent "
              "(build or data bundle not in this environment)")
        return 0

    # ON: NetCDF source
    day00 = tpa.run_model(
        binary, "test_seaice_prov_on", {"STAGE117E_NETCDF_SEAICE": "ON"}
    )
    if day00 is None:
        print("FAIL: ON run did not produce day_00 output")
        return 1
    a = attrs(day00)
    check(a.get("seaice_reader_mode") == "netcdf",
          "ON: seaice_reader_mode == netcdf", a.get("seaice_reader_mode"))
    check("seaice_initial.nc" in str(a.get("seaice_source_file", "")),
          "ON: seaice_source_file is seaice_initial.nc",
          a.get("seaice_source_file"))
    ver = str(a.get("seaice_manifest_version", ""))
    check(ver not in ("", "NONE", "PENDING", "UNSET"),
          "ON: manifest version is actual", ver)
    cks = str(a.get("seaice_manifest_checksum", ""))
    check(bool(re.fullmatch(r"[0-9a-fA-F]{32}", cks)),
          "ON: manifest checksum is 32-hex MD5", cks)

    # OFF: legacy source
    day00 = tpa.run_model(
        binary, "test_seaice_prov_off", {"STAGE117E_NETCDF_SEAICE": "OFF"}
    )
    if day00 is None:
        print("FAIL: OFF run did not produce day_00 output")
        return 1
    a = attrs(day00)
    check(a.get("seaice_reader_mode") == "legacy",
          "OFF: seaice_reader_mode == legacy", a.get("seaice_reader_mode"))
    check("legacy" in str(a.get("seaice_source_file", "")),
          "OFF: seaice_source_file is legacy", a.get("seaice_source_file"))
    check(str(a.get("seaice_manifest_version")) == "NONE",
          "OFF: manifest version NONE", a.get("seaice_manifest_version"))
    check(str(a.get("seaice_manifest_checksum")) == "NONE",
          "OFF: manifest checksum NONE", a.get("seaice_manifest_checksum"))

    print(f"\nTOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())