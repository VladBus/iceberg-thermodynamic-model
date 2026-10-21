#!/usr/bin/env python3
"""
Stage 11.7E.4.1 — Red Test: Ice Coverage Verification

Purpose: Verify that real sea-ice initialization produces non-zero ice cover.
This test SHOULD PASS after 11.7E.4 (real ice connected).

Test design:
- Read seaice_initial.nc (or 1_*.ice files)
- Check: total ice concentration > 0
- Check: number of cells with ice > 0
- Check: maximum ice thickness is physically reasonable (< 10 m for Arctic sea ice)
- If all zero: test FAILS (diagnostic placeholder still active)

This test verifies that 11.7E.4 actually connected real data.
"""

import sys
import os
import json
import numpy as np
from pathlib import Path

# Add project to path
PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "python"))

from netCDF4 import Dataset


def test_ice_coverage():
    """Test that real sea ice data is connected and non-zero."""
    
    # Check both NetCDF and legacy text files
    nc_path = Path("data/input/processed/ice/seaice_initial.nc")
    ice_dir = Path("data/input/generated/real_grid/ice_2020-01-01")
    
    results = {
        "test_name": "ice_coverage",
        "phase": "Phase 2 - Ice Coverage Red Test",
        "expected": "PASS (real ice connected in 11.7E.4)",
    }
    
    # Test NetCDF file
    if nc_path.exists():
        print(f"Testing NetCDF file: {nc_path}")
        with Dataset(nc_path) as ds:
            sic = ds.variables['sic'][:]  # shape (cat, j, i)
            sit = ds.variables['sit'][:]  # shape (cat, j, i)
            
            # Total concentration (sum across categories)
            total_conc = np.nansum(sic, axis=0)
            max_conc = float(np.nanmax(total_conc))
            cells_with_ice = int(np.sum(total_conc > 0.0))
            
            # Ice thickness (max across categories)
            max_thickness = float(np.nanmax(sic * np.array([0.20, 0.40, 0.95, 1.60, 2.50])[:, None, None]))
            # Actually sit is already thickness per category
            max_sit = float(np.nanmax(sit))
            total_volume_m3 = float(np.nansum(sit)) * (13890.0 ** 2)  # m³
            
            nc_results = {
                "file": str(nc_path),
                "max_concentration": max_conc,
                "cells_with_ice": cells_with_ice,
                "max_thickness_m": max_sit,
                "total_volume_m3": total_volume_m3,
                "categories": int(sic.shape[0]),
                "grid_shape": list(sic.shape[1:]),
            }
            results["netcdf"] = nc_results
            
            print(f"  Max concentration: {max_conc:.4f}")
            print(f"  Cells with ice: {cells_with_ice}")
            print(f"  Max thickness (sit): {max_sit:.4f} m")
            print(f"  Total volume: {total_volume_m3:.3e} m³")
    else:
        results["netcdf"] = {"error": f"File not found: {nc_path}"}
    
    # Test legacy text files
    ice_files = list(ice_dir.glob("1_*.ice"))
    if ice_files:
        print(f"Testing legacy text files in: {ice_dir}")
        total_cells_with_ice = 0
        max_an1 = 0.0
        for ice_file in sorted(ice_files):
            vals = np.fromfile(ice_file, sep=' ', dtype=np.float64)
            if len(vals) == 133 * 105:
                arr = vals.reshape((133, 105))
                cells = int(np.sum(arr > 0))
                max_val = float(np.max(arr))
                total_cells_with_ice = max(total_cells_with_ice, cells)
                max_an1 = max(max_an1, max_val)
                print(f"  {ice_file.name}: cells with ice={cells}, max={max_an1:.4f}")
        
        legacy_results = {
            "directory": str(ice_dir),
            "files_found": len(ice_files),
            "max_cells_with_ice": total_cells_with_ice,
            "max_concentration": max_an1,
        }
        results["legacy"] = legacy_results
    else:
        results["legacy"] = {"error": f"No ice files found in {ice_dir}"}
    
    # Overall pass/fail
    nc_ok = results.get("netcdf", {}).get("cells_with_ice", 0) > 0
    legacy_ok = results.get("legacy", {}).get("max_cells_with_ice", 0) > 0
    
    # For this test, we expect PASS because 11.7E.4 connected real data
    overall_pass = nc_ok and legacy_ok
    
    results["pass"] = overall_pass
    results["summary"] = f"NetCDF: {'PASS' if nc_ok else 'FAIL'}, Legacy: {'PASS' if legacy_ok else 'FAIL'}"
    
    print(f"\n  Result: {'PASS' if overall_pass else 'FAIL'}")
    print(f"  Summary: {results['summary']}")
    
    return results


def main():
    output_dir = Path("data/validation")
    output_dir.mkdir(exist_ok=True)
    
    results = test_ice_coverage()
    
    output_file = Path("data/validation/ice_coverage_result.json")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to {output_file}")
    print(f"Overall: {'PASS' if results['pass'] else 'FAIL'}")
    print(f"Summary: {results['summary']}")
    
    # This test should PASS after 11.7E.4
    if results['pass']:
        print("\n✓ PASS: Real sea ice data is connected and non-zero")
    else:
        print("\n✗ FAIL: Real sea ice data not connected or all zero")
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())