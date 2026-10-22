#!/usr/bin/env python3
"""
Stage 11.7E.2.3 — Provenance Attributes Verification

Verifies that NetCDF output contains correct provenance metadata attributes
written at day_00 (initial state output).

Four scenarios tested:
  1. Default path, STRICT mode (OCEAN_INIT_MODE=STRICT, no override)
  2. Override path, STRICT mode (ICEBERG_OCEAN_INIT_FILE set to different path)
  3. FORCE_SYNTHETIC mode (OCEAN_INIT_MODE=FORCE_SYNTHETIC)
  4. EOS-80 mode (EOS_MODE=EOS80)

The test runs the model binary with a short timeout (enough for day_00 output),
reads the global attributes from results_day_00.nc, and verifies them.

Exit codes:
  0 = all checks pass (or SKIP with clear message)
  1 = any check fails
"""

import os
import sys
import glob
import subprocess
import time
import shutil
from pathlib import Path

try:
    from netCDF4 import Dataset
except ImportError:
    print("ERROR: netCDF4 unavailable (activate conda env iceberg-thermodynamic-model)")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_EN4_FILE_REL = "data/input/processed/ocean/initial_ts_2020-01-01.nc"
DEFAULT_EN4_FILE = PROJECT_ROOT / DEFAULT_EN4_FILE_REL
KOORD_DAT = PROJECT_ROOT / "KOORD.DAT"
HHH_BAR = PROJECT_ROOT / "hhh.bar"

CHECKS = 0
ERRORS = 0
INFOS = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if cond:
        print(f"PASS {label}")
    else:
        ERRORS += 1
        print(f"FAIL {label} {detail}")


def info(label):
    global INFOS
    INFOS += 1
    print(f"INFO {label}")


def find_binary():
    """Find the built model executable."""
    for path in glob.glob(str(PROJECT_ROOT / "build" / "*" / "app" / "iceberg-thermodynamic-model")):
        return Path(path)
    return None


def check_prerequisites():
    """Verify all required products and files exist."""
    binary = find_binary()
    if not binary:
        info("SKIP: model binary not found (run 'fpm build' first)")
        return None, False

    if not KOORD_DAT.exists():
        info("SKIP: KOORD.DAT not found (run grid generation first)")
        return binary, False

    if not HHH_BAR.exists():
        info("SKIP: hhh.bar not found (run grid generation first)")
        return binary, False

    if not DEFAULT_EN4_FILE.exists():
        info("SKIP: default EN4 file not found (build via python/ocean/build_initial_ts.py)")
        return binary, False

    return binary, True


def run_model(binary, run_id, env_overrides, timeout_sec=90):
    """
    Run the model with given environment overrides.
    Waits for results_day_00.nc to appear, then terminates.
    Returns path to day_00 nc file or None on failure.
    """
    env = os.environ.copy()
    # Clear potentially interfering env vars
    for key in ['OCEAN_INIT_MODE', 'ICEBERG_OCEAN_INIT_FILE', 'EOS_MODE', 'STAGE115H_PRODUCTION_MODE']:
        env.pop(key, None)
    # Apply scenario overrides
    env.update(env_overrides)

    run_dir = PROJECT_ROOT / "data" / "runs" / run_id
    output_dir = run_dir / "output" / "nc"
    day00_path = output_dir / "results_day_00.nc"

    # Clean any previous run
    if run_dir.exists():
        shutil.rmtree(run_dir)

    # Run the binary directly (not via fpm) to avoid rebuild delays
    # cwd must be project root for relative paths (KOORD.DAT, etc.)
    proc = subprocess.Popen(
        [str(binary), run_id],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Poll for day_00 output with readability check
    start = time.time()
    day00_found = False
    max_wait = min(timeout_sec, 10)  # Cap at 10s for day_00 readiness
    while time.time() - start < timeout_sec:
        if day00_path.exists():
            # Verify file is readable by netCDF4
            try:
                with Dataset(day00_path, 'r') as _:
                    pass
                day00_found = True
                break
            except Exception:
                # File exists but not ready yet
                pass
        if proc.poll() is not None:
            # Process exited early
            stdout, _ = proc.communicate(timeout=2)
            print(f"  Process exited early (code={proc.returncode}):")
            for line in stdout.splitlines()[-10:]:
                print(f"    {line}")
            break
        time.sleep(0.25)
        # After max_wait, if file exists but unreadable, treat as failure
        if time.time() - start > max_wait and day00_path.exists():
            try:
                with Dataset(day00_path, 'r') as _:
                    day00_found = True
                    break
            except Exception:
                pass

    if not day00_found:
        # Timeout - kill and check if file appeared
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    # Read any remaining output for debugging
    try:
        stdout, _ = proc.communicate(timeout=2)
        if stdout:
            print(f"  Model stdout (last 8 lines):")
            for line in stdout.splitlines()[-8:]:
                print(f"    {line}")
    except:
        pass

    if day00_path.exists():
        return day00_path
    return None


def verify_attributes(nc_path, expected, scenario_name):
    """Verify global attributes in the NetCDF file match expected values."""
    print(f"\n--- Verifying {scenario_name} ({nc_path}) ---")
    with Dataset(nc_path) as ds:
        attrs = ds.ncattrs()
        for attr_name, expected_val in expected.items():
            label = f"{scenario_name}: {attr_name}"
            if attr_name in attrs:
                actual = ds.getncattr(attr_name)
                check(actual == expected_val, label, f"expected '{expected_val}', got '{actual}'")
            else:
                check(False, label, f"attribute missing (available: {attrs})")


def scenario_default_strict(binary):
    """Scenario 1: Default path, STRICT mode."""
    env = {
        'OCEAN_INIT_MODE': 'STRICT',
    }
    day00 = run_model(binary, "test_prov_attr_1_default_strict", env)
    if day00 is None:
        return False

    expected = {
        'initialization_source': 'EN4',
        'initialization_file': DEFAULT_EN4_FILE_REL,
        'initialization_attempted_file': DEFAULT_EN4_FILE_REL,
        'initialization_mode_actual': 'EN4_REAL',
        'eos_mode': 'LEGACY',
        'scheduler_mode': 'N1_LEGACY',
        'seaice_reader_mode': 'legacy',
        'seaice_source_file': 'legacy_1_*.ice',
        'seaice_manifest_version': 'NONE',
        'seaice_manifest_checksum': 'NONE',
    }
    verify_attributes(day00, expected, "scenario_1_default_strict")
    return True


def scenario_override_strict(binary):
    """Scenario 2: Override path, STRICT mode.

    Uses a symlink with a different name to verify the recorded path
    is the override, not the default constant.
    """
    # Create a symlink with a different name pointing to the same file
    override_rel = "data/input/processed/ocean/initial_ts_2020-01-01_override.nc"
    override_path = PROJECT_ROOT / override_rel
    if override_path.exists() or override_path.is_symlink():
        override_path.unlink()
    override_path.symlink_to(DEFAULT_EN4_FILE)
    try:
        env = {
            'OCEAN_INIT_MODE': 'STRICT',
            'ICEBERG_OCEAN_INIT_FILE': override_rel,
        }
        day00 = run_model(binary, "test_prov_attr_2_override_strict", env)
        if day00 is None:
            return False

        expected = {
            'initialization_source': 'EN4',
            'initialization_file': override_rel,
            'initialization_attempted_file': override_rel,
            'initialization_mode_actual': 'EN4_REAL',
            'eos_mode': 'LEGACY',
            'scheduler_mode': 'N1_LEGACY',
        }
        verify_attributes(day00, expected, "scenario_2_override_strict")
        return True
    finally:
        if override_path.exists() or override_path.is_symlink():
            override_path.unlink()


def scenario_force_synthetic(binary):
    """Scenario 3: FORCE_SYNTHETIC mode."""
    env = {
        'OCEAN_INIT_MODE': 'FORCE_SYNTHETIC',
    }
    day00 = run_model(binary, "test_prov_attr_3_force_synthetic", env)
    if day00 is None:
        return False

    expected = {
        'initialization_source': 'SYNTHETIC',
        'initialization_file': 'NONE',
        'initialization_attempted_file': 'SKIPPED_BY_MODE',
        'initialization_mode_actual': 'SYNTHETIC',
        'eos_mode': 'LEGACY',
        'scheduler_mode': 'N1_LEGACY',
    }
    verify_attributes(day00, expected, "scenario_3_force_synthetic")
    return True


def scenario_eos80(binary):
    """Scenario 4: EOS-80 mode (default initialization)."""
    env = {
        'EOS_MODE': 'EOS80',
    }
    day00 = run_model(binary, "test_prov_attr_4_eos80", env)
    if day00 is None:
        return False

    expected = {
        'initialization_source': 'EN4',
        'initialization_file': DEFAULT_EN4_FILE_REL,
        'initialization_attempted_file': DEFAULT_EN4_FILE_REL,
        'initialization_mode_actual': 'EN4_REAL',
        'eos_mode': 'EOS80',
        'scheduler_mode': 'N1_LEGACY',
    }
    verify_attributes(day00, expected, "scenario_4_eos80")
    return True


def main():
    global CHECKS, ERRORS, INFOS

    print("=" * 72)
    print("Stage 11.7E.2.3 — Provenance Attributes Verification")
    print("=" * 72)

    binary, ok = check_prerequisites()
    if not ok or binary is None:
        print("=" * 72)
        print(f"SKIP: prerequisites not met (binary={binary is not None})")
        print(f"TOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}  INFO: {INFOS}")
        print("=" * 72)
        return 0  # SKIP = exit 0

    print(f"Using binary: {binary}")
    print(f"Default EN4 file: {DEFAULT_EN4_FILE}")
    print()

    # Run all scenarios
    scenarios = [
        ("Scenario 1: Default STRICT", scenario_default_strict),
        ("Scenario 2: Override STRICT", scenario_override_strict),
        ("Scenario 3: FORCE_SYNTHETIC", scenario_force_synthetic),
        ("Scenario 4: EOS-80", scenario_eos80),
    ]

    for name, func in scenarios:
        print(f"\n>>> Running {name}...")
        try:
            ok = func(binary)
            if not ok:
                ERRORS += 1
                print(f"FAIL {name}: scenario returned False (likely day_00.nc missing or unreadable)")
        except Exception as e:
            ERRORS += 1
            print(f"FAIL {name}: exception {type(e).__name__}: {e}")

    print("\n" + "=" * 72)
    print(f"TOTAL CHECKS: {CHECKS}  PASSED: {CHECKS - ERRORS}  FAILED: {ERRORS}  INFO: {INFOS}")
    print("=" * 72)

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())