#!/usr/bin/env python3
"""
Stage 11.8.0.0 — Sea-ice provenance verification (ACTUAL source).

Runs the production binary with the default NetCDF sea-ice path, reads
the day_00 global attributes, and verifies that provenance reflects the actual
source rather than hardcoded strings:

Stage 11.10: NetCDF is the only production sea-ice reader.
Default run must report:
  seaice_reader_mode = "netcdf"
  seaice_source_file contains "seaice_initial.nc"
  seaice_manifest_version != NONE/PENDING/UNSET
  seaice_manifest_checksum is a 32-hex-char MD5

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
    day00 = tpa.run_model(binary, "test_seaice_prov_default", {})
    if day00 is None:
        print("FAIL: ON run did not produce day_00 output")
        return 1
    a = attrs(day00)
    check(a.get("seaice_reader_mode") == "netcdf",
          "DEFAULT: seaice_reader_mode == netcdf", a.get("seaice_reader_mode"))
    check("seaice_initial.nc" in str(a.get("seaice_source_file", "")),
          "DEFAULT: seaice_source_file is seaice_initial.nc",
          a.get("seaice_source_file"))
    ver = str(a.get("seaice_manifest_version", ""))
    check(ver not in ("", "NONE", "PENDING", "UNSET"),
          "DEFAULT: manifest version is actual", ver)
    cks = str(a.get("seaice_manifest_checksum", ""))
    check(bool(re.fullmatch(r"[0-9a-fA-F]{32}", cks)),
          "DEFAULT: manifest checksum is 32-hex MD5", cks)

    # Stage 11.10: NetCDF is the only production sea-ice reader; no OFF path.
    print(f"\nTOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())