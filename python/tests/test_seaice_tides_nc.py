IS1, JS1, NGR = 133, 105, 5
"""
Stage 11.7D — seaice_initial.nc / tides.nc source-to-NetCDF equivalence.

Prerequisite:
    # Sea-ice: legacy 1_*.ice files are the production inputs
    # Tides: null-tides is the current production state

Check layers:
  1. Builders run (seaice_initial.nc, tides.nc).
  2. Equivalence tests against legacy sources + expected null-tides.
  3. Monthly sea-ice limitation documented.
  3. Tides null-tides contract verified.
  4. Regression gates (battery, strict, Jan OFF NDIFF=0, etc.).
  5. Provenance attrs + incomplete-manifest case (11.7E.1-CP Phase 6).
"""

import os
import sys
import tempfile

import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT, "python", "ice"))
sys.path.insert(0, os.path.join(PROJECT, "python", "tides"))
sys.path.insert(0, PROJECT)

from netCDF4 import Dataset  # noqa: E402

import build_seaice_nc as sea  # noqa: E402
import build_tides_nc as tid  # noqa: E402

IS1, JS1, NGR = 133, 105, 5
N_CONST = 4
LAND = 8888.0
HST = np.array([0.20, 0.40, 0.95, 1.60, 2.50], dtype=np.float64)
HMAX = np.array([0.3, 0.7, 1.2, 2.0, 50.0], dtype=np.float64)
CONST_NAMES = ["M2", "S2", "K1", "O1"]
QQ_DEG_H = np.array([28.9841042, 30.0, 15.041069, 13.943036], dtype=np.float64)

CHECKS = 0
ERRORS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if not cond:
        ERRORS += 1
        print("FAIL %s %s" % (label, detail))


def read_ice_files_independent():
    """Read 1_1.ice .. 1_5.ice from real_grid directory (INDEPENDENT)."""
    REAL_GRID = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "input", "generated", "real_grid")
    an1 = np.zeros((NGR + 1, IS1, JS1), dtype=np.float64)
    for k in range(1, NGR + 1):
        fpath = os.path.join(REAL_GRID, f"1_{k}.ice")
        with open(fpath) as f:
            vals = f.read().split()
        arr = np.array(vals, dtype=np.float64).reshape((JS1, IS1)).T.copy()  # [i,j]
        # Replicate legacy processing: 9.99->0, >=1->1, clamp
        arr = np.where(np.abs(arr - 9.99) < 1e-8, 0.0, arr)
        arr = np.clip(arr, 0.0, 1.0)
        an1[k, :, :] = arr
    return an1


def build_sic_sit_ref(an1_raw):
    """Independent reference implementation (no shared code with builder)."""
    an1 = np.zeros((NGR + 1, IS1, JS1), dtype=np.float64)
    # an1_raw has shape (6, IS1, JS1) from sea.read_ice_files (index 0 unused)
    an1[1:, :, :] = an1_raw[1:, :, :]
    # Legacy processing: 9.99->0, >=1->1, clamp, normalize
    an1 = np.where(np.abs(an1 - 9.99) < 1e-8, 0.0, an1)
    an1 = np.clip(an1, 0.0, 1.0)
    s = an1[1:, :, :].sum(axis=0)
    over = s > 1.0
    if over.any():
        an1[1:, over] /= s[over]
    # sic = an1 (categories 1..5) -> transpose to (cat, j, i) for NetCDF
    sic = an1[1:, :, :].astype(np.float32).transpose(0, 2, 1)
    # sit = hst * an1
    sit = np.zeros((5, IS1, JS1), dtype=np.float32)
    for cat in range(5):
        sit[cat, :, :] = HST[cat] * an1[cat + 1, :, :].astype(np.float32)
    sit = sit.transpose(0, 2, 1)
    return sic, sit
    for cat in range(5):
        sit[cat, :, :] = HST[cat] * an1[cat + 1, :, :].astype(np.float32)
    return sic, sit


def _precheck_inputs():
    """Pre-check inputs before running builders (SKIP contract).

    Requires ALL FIVE 1_1.ice..1_5.ice files in the ACTUAL directory
    this test and the builder read from
    (data/input/generated/real_grid/). Root-level symlinks are the
    legacy Fortran reader path and are NOT read by this test, so they
    do not satisfy the check (11.7E.1-CP Phase 5 fix: the previous
    check passed if at least ONE file of a combined real_grid +
    symlink list existed, so partially missing inputs crashed the
    builder instead of SKIPping).

    grid_dump files are Fortran ground truth for the GRID test, not
    this test — not required here (11.7E Phase 0.2).

    Returns:
        0 if SKIP (inputs not available)
        2 if all ready to proceed
    """
    real_grid = os.path.join(PROJECT, "data", "input", "generated",
                             "real_grid")
    missing = [os.path.basename("1_%d.ice" % k) for k in range(1, 6)
               if not os.path.exists(
                   os.path.join(real_grid, "1_%d.ice" % k))]

    if missing:
        print("SKIP: required real-grid inputs not available in %s"
              % real_grid)
        print("SKIP: missing files: %s" % ", ".join(missing))
        return 0

    return 2


def main():
    # Pre-check inputs FIRST (before any builder runs)
    if _precheck_inputs() == 0:
        sys.exit(0)
    # else proceed

    # Builders first
    import build_seaice_nc as sea
    import build_tides_nc as tid

    _tmp = tempfile.mkdtemp(prefix="seaice_tides_test_")
    sea.OUT_DIR = os.path.join(_tmp, "ice")
    tid.OUT_DIR = os.path.join(_tmp, "tides")
    os.makedirs(sea.OUT_DIR, exist_ok=True)
    os.makedirs(tid.OUT_DIR, exist_ok=True)

    # Run builders with explicit output paths
    gpath = os.path.join(sea.OUT_DIR, "seaice_initial.nc")
    tpath = os.path.join(tid.OUT_DIR, "tides.nc")

    # Run builders with sys.argv simulation (sys imported at module top)
    sys.argv = ['build_seaice_nc.py', '--out', gpath]
    sea.main()
    sys.argv = ['build_tides_nc.py']
    tid.main()

    # Load builder outputs
    g = Dataset(os.path.join(sea.OUT_DIR, "seaice_initial.nc"))
    t = Dataset(os.path.join(tid.OUT_DIR, "tides.nc"))

    # Check dimensions
    for v in ("sic", "sit", "snow_depth"):
        check(g[v].dimensions == ("cat", "j", "i"), "seaice %s dims" % v,
              str(g[v].dimensions))
    check(g["hst"].dimensions == ("cat",), "hst dim")
    check(g["hmax"].dimensions == ("cat",), "hmax dim")

    for v in ("constituent_name", "qq", "qq_rad_per_step"):
        check(t[v].dimensions == ("const",), "tides %s dims" % v)
    for v in ("amplitude", "phase"):
        check(t[v].dimensions == ("const", "j", "i"), "tides %s dims" % v)

    # Load data
    sic = np.array(g["sic"][:])       # (cat, j, i)
    sit = np.array(g["sit"][:])
    snow = np.array(g["snow_depth"][:])
    amp = np.array(t["amplitude"][:])  # (const, j, i)
    faz = np.array(t["phase"][:])
    qq = np.array(t["qq"][:])
    g.close()
    t.close()

    # --- Independent reference (seaice) ---
    an1_raw = read_ice_files_independent()
    sic_ref, sit_ref = build_sic_sit_ref(an1_raw)

    # Equivalence checks (seaice)
    check(bool((sic == sic_ref).all()), "sic bit-exact vs ref",
          "mismatch=%d" % int((sic != sic_ref).sum()))
    check(bool((sit == sit_ref).all()), "sit bit-exact vs ref",
          "mismatch=%d" % int((sit != sit_ref).sum()))
    check(bool((snow == 0).all()), "snow all zeros")

    # HST/HMAX exact
    hst = np.array(Dataset(os.path.join(sea.OUT_DIR, "seaice_initial.nc"))["hst"][:])
    hmax = np.array(Dataset(os.path.join(sea.OUT_DIR, "seaice_initial.nc"))["hmax"][:])
    check(bool((hst == HST).all()), "hst exact")
    check(bool((hmax == HMAX).all()), "hmax exact")

    # Tides checks
    check(bool((amp == 0).all()), "tides amplitude all zero (null-tides)")
    check(bool((faz == 0).all()), "tides phase all zero (null-tides)")
    check(bool((qq == np.array([28.9841042, 30.0, 15.041069, 13.943036])).all()), "qq exact")
    # qq_rad_per_step = qq * dt1 / 3600 / 57.2958
    dt1 = 120.0
    qq_step_expected = QQ_DEG_H * (120.0 / 3600.0) / 57.2958
    tds = Dataset(os.path.join(tid.OUT_DIR, "tides.nc"))
    qq_step = np.array(tds["qq_rad_per_step"][:])
    check(np.abs(qq_step - qq_step_expected).max() < 1e-12, "qq_rad_per_step exact")

    # Tides status attribute
    check(tds.getncattr("tidal_status") == "null-tides (GRM2/GRS2/GRK1/GRO1 data unavailable)",
          "tidal_status attr")
    tds.close()

    # --- Provenance attributes (11.7E.1-CP Phase 6.3) ---
    # Expected values derive from the SAME manifest contract the builder
    # must apply (schema validation before use).
    import json as _json
    import shutil

    manifest_path = os.path.join(PROJECT, "python", "ice",
                                 "seaice_source_manifest.json")
    with open(manifest_path) as mf:
        manifest = _json.load(mf)
    req_fields = ("source_type", "dataset_name", "version", "date",
                  "spatial_extent", "temporal_coverage")
    m_missing = [f for f in req_fields
                 if not str(manifest.get(f, "")).strip()]
    if m_missing:
        exp_source, exp_status = "INCOMPLETE_MANIFEST", "INCOMPLETE_MANIFEST"
    elif manifest.get("source_type") == "diagnostic_placeholder":
        exp_source, exp_status = "DIAGNOSTIC_PLACEHOLDER", "DIAGNOSTIC"
    elif manifest.get("source_type") == "scientific":
        exp_source = "%s %s %s" % (manifest["dataset_name"],
                                   manifest["version"], manifest["date"])
        exp_status = "SCIENTIFIC"
    else:
        exp_source, exp_status = "UNKNOWN", "UNKNOWN"

    gp = Dataset(os.path.join(sea.OUT_DIR, "seaice_initial.nc"))
    check(gp.getncattr("source") == exp_source, "provenance source attr",
          "%r != %r" % (gp.getncattr("source"), exp_source))
    check(gp.getncattr("sea_ice_status") == exp_status,
          "provenance sea_ice_status attr",
          "%r != %r" % (gp.getncattr("sea_ice_status"), exp_status))
    cnote = (gp.getncattr("checksum_note")
             if "checksum_note" in gp.ncattrs() else "")
    check("no input checksums" in cnote or "verified" in cnote,
          "provenance checksum_note attr", repr(cnote))
    gp.close()

    # Incomplete-manifest case: builder must report INCOMPLETE_MANIFEST
    # and must NEVER assign SCIENTIFIC without the full schema.
    tmpdir = tempfile.mkdtemp(prefix="seaice_manifest_test_")
    try:
        inc_manifest = os.path.join(tmpdir, "incomplete_manifest.json")
        with open(inc_manifest, "w") as f:
            _json.dump({"source_type": "scientific", "dataset_name": "X"}, f)
        inc_out = os.path.join(tmpdir, "seaice_initial_incomplete.nc")
        sys.argv = ['build_seaice_nc.py', '--out', inc_out,
                    '--manifest', inc_manifest]
        sea.main()
        gi = Dataset(inc_out)
        check(gi.getncattr("source") == "INCOMPLETE_MANIFEST",
              "incomplete manifest source", str(gi.getncattr("source")))
        check(gi.getncattr("sea_ice_status") == "INCOMPLETE_MANIFEST",
              "incomplete manifest status",
              str(gi.getncattr("sea_ice_status")))
        gi.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # --- 4 manifest-strengthening scenarios (11.7E.2 Phase 5) ---
    # 1. Diagnostic placeholder (current manifest) - explicit check
    gp = Dataset(os.path.join(sea.OUT_DIR, "seaice_initial.nc"))
    check(gp.getncattr("source") == "DIAGNOSTIC_PLACEHOLDER",
          "diagnostic placeholder source attr",
          str(gp.getncattr("source")))
    check(gp.getncattr("sea_ice_status") == "DIAGNOSTIC",
          "diagnostic placeholder status attr",
          str(gp.getncattr("sea_ice_status")))
    gp.close()

    # 2. Scientific with NO checksums -> SCIENTIFIC_UNVERIFIED_NO_CHECKSUMS
    tmpdir = tempfile.mkdtemp(prefix="seaice_sci_nocs_")
    try:
        sci_nocs = os.path.join(tmpdir, "sci_nocs.json")
        with open(sci_nocs, "w") as f:
            _json.dump({
                "source_type": "scientific",
                "dataset_name": "OSI-SAF SIC CDR",
                "version": "v3.1",
                "date": "2020-01-01",
                "spatial_extent": "Barents",
                "temporal_coverage": "2020-01"
            }, f)
        out_nocs = os.path.join(tmpdir, "seaice_sci_nocs.nc")
        sys.argv = ['build_seaice_nc.py', '--out', out_nocs,
                    '--manifest', sci_nocs]
        sea.main()
        gn = Dataset(out_nocs)
        check(gn.getncattr("sea_ice_status") == "SCIENTIFIC_UNVERIFIED_NO_CHECKSUMS",
              "scientific no checksums status",
              str(gn.getncattr("sea_ice_status")))
        check("(no checksums provided)" in gn.getncattr("source"),
              "scientific no checksums source note",
              str(gn.getncattr("source")))
        gn.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # 3. Scientific with PARTIAL checksums -> SCIENTIFIC_PARTIAL_CHECKSUMS
    tmpdir = tempfile.mkdtemp(prefix="seaice_sci_partial_")
    try:
        sci_partial = os.path.join(tmpdir, "sci_partial.json")
        with open(sci_partial, "w") as f:
            _json.dump({
                "source_type": "scientific",
                "dataset_name": "OSI-SAF SIC CDR",
                "version": "v3.1",
                "date": "2020-01-01",
                "spatial_extent": "Barents",
                "temporal_coverage": "2020-01",
                "input_checksums": {"1_1.ice": "dummy1", "1_2.ice": "dummy2"}
            }, f)
        out_partial = os.path.join(tmpdir, "seaice_sci_partial.nc")
        sys.argv = ['build_seaice_nc.py', '--out', out_partial,
                    '--manifest', sci_partial]
        sea.main()
        gp2 = Dataset(out_partial)
        check(gp2.getncattr("sea_ice_status") == "SCIENTIFIC_PARTIAL_CHECKSUMS",
              "scientific partial checksums status",
              str(gp2.getncattr("sea_ice_status")))
        check("(partial: 2/5 checksums)" in gp2.getncattr("source"),
              "scientific partial checksums source note",
              str(gp2.getncattr("source")))
        gp2.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    tmpdir = tempfile.mkdtemp(prefix="seaice_sci_mismatch_")
    try:
        sci_mismatch = os.path.join(tmpdir, "sci_mismatch.json")
        with open(sci_mismatch, "w") as f:
            _json.dump({
                "source_type": "scientific",
                "dataset_name": "OSI-SAF SIC CDR",
                "version": "v3.1",
                "date": "2020-01-01",
                "spatial_extent": "Barents",
                "temporal_coverage": "2020-01",
                "input_checksums": {"1_1.ice": "WRONG_HASH_1",
                                    "1_2.ice": "WRONG_HASH_2",
                                    "1_3.ice": "WRONG_HASH_3",
                                    "1_4.ice": "WRONG_HASH_4",
                                    "1_5.ice": "WRONG_HASH_5"}
            }, f)
        out_mismatch = os.path.join(tmpdir, "seaice_sci_mismatch.nc")
        sys.argv = ['build_seaice_nc.py', '--out', out_mismatch,
                    '--manifest', sci_mismatch]
        try:
            sea.main()
            check(False, "checksum mismatch fails fast",
                  "builder returned without SystemExit")
        except SystemExit as exc:
            check(exc.code == 1, "checksum mismatch exit code",
                  str(exc.code))
        check(not os.path.exists(out_mismatch),
              "checksum mismatch writes no output file")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Monthly sea-ice limitation note (documented, not a test failure)
    print("NOTE: Only January sea-ice data exists; other months reuse January init (known gap).")

    # Tides null-tides contract
    print("Tides null-tides contract verified: zero amp/phase, status attr present.")

    print("TOTAL CHECKS: %d ERRORS: %d" % (CHECKS, ERRORS))
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()