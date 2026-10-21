#!/usr/bin/env python3
"""
Stage 11.7E.4.1 — Red Test: Snowfall Accumulation Period Verification

Purpose: Verify the snowfall accumulation period assumption used in
merge_snowfall.py (divisor = 43200).

This test checks METADATA, not model behavior.

Test design:
- Read raw ERA5 snowfall file (if available) or merged product
- Check GRIB attributes:
  * GRIB_stepType (should be "accum")
  * GRIB_startStep, GRIB_endStep (if present)
  * stepRange (if present)
- Check valid_time spacing in the NetCDF
- Compute: what is the actual accumulation period?
- Compare with the divisor used in merge_snowfall.py (43200)

Interpretation:
- If metadata says hourly accumulation but divisor is 43200: MISMATCH, likely error (should be 3600)
- If metadata says 12-hour accumulation and divisor is 43200: CONSISTENT
- If metadata is ambiguous: document uncertainty, recommend checking CDS request parameters

This test does NOT change the divisor. It only reports the finding.
The actual fix (if needed) is deferred to 11.8.
"""

import sys
import json
import numpy as np
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "python"))

from netCDF4 import Dataset


def check_snowfall_metadata():
    """Check snowfall accumulation period from ERA5 metadata."""
    
    results = {
        "test_name": "snowfall_period",
        "phase": "Phase 3 - Snowfall Period Red Test",
        "purpose": "Verify snowfall accumulation period divisor (43200) matches ERA5 metadata",
    }
    
    # Check merged ERA5 files for snowfall variable metadata
    era5_dir = Path("data/input/processed/era5/2020/2020_01")
    merged_files = list(era5_dir.glob("*merged*.nc"))
    
    if not merged_files:
        results["error"] = "No merged ERA5 files found"
        return results
    
    # Use the full coverage file
    merged_file = None
    for f in merged_files:
        if "fullcoverage" in f.name:
            merged_file = f
            break
    
    if merged_file is None:
        merged_file = merged_files[0]
    
    print(f"Examining: {merged_file}")
    results["file_examined"] = str(merged_file)
    
    with Dataset(merged_file) as ds:
        # Check snowfall variable
        if 'sf' in ds.variables:
            sf_var = ds.variables['sf']
            results["sf_variable_found"] = True
            results["sf_dims"] = list(sf_var.shape)
            results["sf_units"] = sf_var.units if hasattr(sf_var, 'units') else 'MISSING'
            
            # Check all attributes
            attrs = {}
            for attr in sf_var.ncattrs():
                attrs[attr] = sf_var.getncattr(attr)
            results["sf_attributes"] = attrs
            
            print(f"  sf units: {attrs.get('units', 'MISSING')}")
            print(f"  sf attributes: {attrs}")
        else:
            results["sf_variable_found"] = False
            results["error"] = "sf variable not found in merged file"
        
        # Check time dimension
        if 'valid_time' in ds.variables:
            time_var = ds.variables['valid_time']
            times = time_var[:]
            results["time_steps"] = len(times)
            
            if len(times) >= 2:
                # Check time spacing
                dt = np.diff(times)
                unique_dt = np.unique(dt)
                results["time_spacing_seconds"] = unique_dt.tolist()
                results["time_spacing_hours"] = (np.array(unique_dt) / 3600).tolist()
                
                print(f"  Time steps: {len(times)}")
                print(f"  Time spacing: {list(unique_dt)} seconds ({float(unique_dt[0])/3600:.1f} hours)")
                
                # Check if consistent with 12-hour accumulation
                if len(unique_dt) == 1:
                    spacing_hours = float(unique_dt[0]) / 3600
                    if abs(spacing_hours - 12.0) < 0.1:
                        results["accumulation_period_hours"] = spacing_hours
                        results["divisor_consistency"] = "CONSISTENT" if spacing_hours == 12 else "CHECK_NEEDED"
                    else:
                        results["accumulation_period_hours"] = spacing_hours
                        results["divisor_consistency"] = "MISMATCH"
                else:
                    results["divisor_consistency"] = "IRREGULAR_SPACING"
            else:
                results["divisor_consistency"] = "INSUFFICIENT_TIME_STEPS"
        
        # Check for GRIB metadata attributes on the variable
        if 'sf' in ds.variables:
            sf_var = ds.variables['sf']
            grib_attrs = {}
            for attr in sf_var.ncattrs():
                if 'grib' in attr.lower() or 'step' in attr.lower() or 'accum' in attr.lower():
                    grib_attrs[attr] = sf_var.getncattr(attr)
            results["grib_related_attributes"] = grib_attrs
    
    # Interpretation
    divisor_used = 43200  # seconds
    expected_hours = divisor_used / 3600
    
    results["divisor_used_in_code"] = divisor_used
    results["expected_accumulation_hours"] = expected_hours
    
    # Interpretation logic
    if "accumulation_period_hours" in results:
        actual_hours = results["accumulation_period_hours"]
        if abs(actual_hours - expected_hours) < 0.1:
            results["finding"] = f"CONSISTENT: ERA5 accumulation period ({actual_hours:.1f}h) matches divisor ({expected_hours:.0f}h)"
            results["severity"] = "OK"
        else:
            results["finding"] = f"MISMATCH: ERA5 accumulation period ({actual_hours:.1f}h) != divisor ({expected_hours:.0f}h)"
            results["severity"] = "MISMATCH"
            if actual_hours == 1.0:
                results["recommendation"] = "ERA5 snowfall is hourly accumulation; divisor should be 3600, not 43200"
            elif actual_hours == 6.0:
                results["recommendation"] = "ERA5 snowfall is 6-hour accumulation; divisor should be 21600"
            elif actual_hours == 12.0:
                results["recommendation"] = "ERA5 snowfall is 12-hour accumulation; divisor 43200 is correct"
            else:
                results["recommendation"] = f"Unexpected accumulation period {actual_hours}h; verify CDS request parameters"
    else:
        results["finding"] = "Could not determine accumulation period from metadata"
        results["severity"] = "UNCERTAIN"
        results["recommendation"] = "Check CDS request parameters for snowfall accumulation period"
    
    return results


def main():
    output_dir = Path("data/validation")
    output_dir.mkdir(exist_ok=True)
    
    def convert_to_serializable(obj):
        """Convert numpy types to Python native types for JSON serialization."""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_to_serializable(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(convert_to_serializable(v) for v in obj)
        return obj
    
    print("Checking snowfall accumulation period metadata...")
    results = check_snowfall_metadata()
    results = convert_to_serializable(results)
    
    output_file = Path("data/validation/snowfall_period_result.json")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to {output_file}")
    
    # Print summary
    print(f"\n=== SNOWFALL PERIOD TEST RESULT ===")
    print(f"File examined: {results.get('file_examined', 'N/A')}")
    print(f"Divisor used in code: {results.get('divisor_used_in_code', 'N/A')} s ({results.get('expected_accumulation_hours', 'N/A'):.0f}h)")
    print(f"Accumulation period from metadata: {results.get('accumulation_period_hours', 'UNKNOWN')} hours")
    print(f"Consistency: {results.get('divisor_consistency', 'UNKNOWN')}")
    print(f"Finding: {results.get('finding', 'UNKNOWN')}")
    if 'recommendation' in results:
        print(f"Recommendation: {results['recommendation']}")
    
    print(f"\nResults written to {output_dir}/snowfall_period_result.json")
    
    # This test reports finding, doesn't pass/fail
    print("\n=== TEST STATUS ===")
    print("This test reports metadata finding. No pass/fail - it informs 11.8.")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())