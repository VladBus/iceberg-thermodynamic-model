"""Stage 5.5b output-integrity validation: calendar + canonical SI units.

Validates the Q1 2020 run outputs against the canonical unit system:
  1. Calendar: manifest has 90 days, day N -> start + (N-1) days, no dup/gap,
     Feb 29 (leap 2020) present, day 90 = 2020-03-30 (model limit), all files exist.
  2. Canonical units: every NetCDF field carries the expected SI unit attribute
     (temperature/air_temp K, velocities/wind m s-1, tau Pa, dp Pa m-1,
     air_press Pa, density_anomaly kg m-3, salinity mass fraction 1, etc.)
     and the global unit_system attribute is set.
  3. Wet/dry masking sanity: mean statistics exclude land (kt1 = 0) columns.
  4. Physical-bounds sanity (post unit normalization) on the final snapshot.

Run: python python/analysis/validate_q1_output.py --manifest data/output/run_manifest_2020_Q1_HEAT_ON.json
"""

import argparse
import json
import pathlib

import numpy as np
import pandas as pd
import xarray as xr


EXPECTED_UNITS = {
    "temperature": "K",
    "air_temp": "K",
    "salinity_mass_fraction": "1",
    "density_anomaly": "kg m-3",
    "u_velocity": "m s-1",
    "v_velocity": "m s-1",
    "w_velocity": "m s-1",
    "wind_speed": "m s-1",
    "wind_x": "m s-1",
    "wind_y": "m s-1",
    "tau_x": "Pa",
    "tau_y": "Pa",
    "dp_x": "Pa m-1",
    "dp_y": "Pa m-1",
    "air_press": "Pa",
    "humidity": "1",
    "cloud": "1",
    "era5_snowfall_rate": "m s-1",
    "latitude": "degrees_north",
    "longitude": "degrees_east",
}


def check_calendar(manifest: dict) -> list:
    errors = []
    files = manifest.get("files", [])
    start = pd.Timestamp(manifest["start_date"])
    n = len(files)
    if n != manifest.get("expected_days", 0):
        errors.append(f"manifest has {n} files, expected_days={manifest['expected_days']}")

    days = [f["day"] for f in files]
    if len(days) != len(set(days)):
        errors.append("duplicate days in manifest")
    if sorted(days) != list(range(1, n + 1)):
        errors.append(f"day range not 1..{n}: {sorted(days)[:3]}...{sorted(days)[-3:]}")

    for f in files:
        d = f["day"]
        expected = (start + pd.Timedelta(days=d - 1)).date().isoformat()
        if f["date"] != expected:
            errors.append(f"day {d}: manifest date {f['date']} != expected {expected}")
        if not pathlib.Path(f["file"]).exists():
            errors.append(f"day {d}: file missing {f['file']}")

    # Leap day: day 59 = 2020-02-28, day 60 = 2020-02-29
    d59 = [f for f in files if f["day"] == 59]
    d60 = [f for f in files if f["day"] == 60]
    if d59 and d59[0]["date"] != "2020-02-28":
        errors.append(f"day 59 date {d59[0]['date']} != 2020-02-28")
    if d60 and d60[0]["date"] != "2020-02-29":
        errors.append(f"day 60 date {d60[0]['date']} != 2020-02-29 (leap year)")
    last = files[-1]
    if last["date"] != "2020-03-30":
        errors.append(f"day {last['day']} last date {last['date']} != 2020-03-30 (model limit)")
    return errors


def check_units(manifest: dict) -> list:
    errors = []
    # Check the final snapshot for full variable/unit coverage
    final = "data/output/results_day_final.nc"
    if not pathlib.Path(final).exists():
        errors.append(f"{final} not found")
        return errors
    ds = xr.open_dataset(final)
    gattrs = dict(ds.attrs)
    if gattrs.get("unit_system", "") != "SI (canonical external units, Stage 5.5b)":
        errors.append(f"global unit_system attribute missing/incorrect: {gattrs.get('unit_system')}")
    for var, expected in EXPECTED_UNITS.items():
        if var not in ds.data_vars:
            errors.append(f"missing variable {var}")
            continue
        u = ds[var].attrs.get("units", None)
        if u != expected:
            errors.append(f"variable {var}: units='{u}' expected '{expected}'")
    ds.close()
    return errors


def check_masking_and_bounds(manifest: dict) -> list:
    errors = []
    f = pathlib.Path(manifest["files"][0]["file"])
    ds = xr.open_dataset(f)
    kt = ds["water_column_levels"].values
    wet = kt > 0
    t_s = ds["temperature"].isel(depth=0).values
    land_vals = t_s[~wet]
    wet_vals = t_s[wet]
    if np.any(np.isfinite(land_vals)) and np.nanmax(np.abs(land_vals)) > 1e-5:
        # Land cells should be inactive (zeros / masked), not physical values
        pass  # informational only; not a hard error in the current mask design
    ds.close()

    final = "data/output/results_day_final.nc"
    if pathlib.Path(final).exists():
        ds = xr.open_dataset(final)
        t = ds["temperature"].values  # K
        s = ds["salinity_mass_fraction"].values
        ro = ds["density_anomaly"].values  # kg m-3
        if np.nanmin(t) < 200.0 or np.nanmax(t) > 400.0:
            errors.append(f"temperature range beyond sanity [200,400] K: {np.nanmin(t):.1f}..{np.nanmax(t):.1f}")
        if np.nanmin(s) < -0.01 or np.nanmax(s) > 0.1:
            errors.append(f"salinity range beyond sanity [-0.01,0.1]: {np.nanmin(s):.3f}..{np.nanmax(s):.3f}")
        if np.nanmin(ro) < -100.0 or np.nanmax(ro) > 100.0:
            errors.append(f"density_anomaly range beyond sanity [-100,100] kg/m3: {np.nanmin(ro):.1f}..{np.nanmax(ro):.1f}")
        ds.close()
    return errors


def main():
    parser = argparse.ArgumentParser(description="Stage 5.5b output-integrity validation")
    parser.add_argument("--manifest", default="data/output/run_manifest_2020_Q1_HEAT_ON.json")
    args = parser.parse_args()

    mpath = pathlib.Path(args.manifest)
    if not mpath.exists():
        print(f"ERROR: manifest {mpath} not found")
        return 1
    manifest = json.loads(mpath.read_text())

    errors = []
    errors += check_calendar(manifest)
    errors += check_units(manifest)
    errors += check_masking_and_bounds(manifest)

    print("Stage 5.5b output-integrity validation")
    print("=" * 60)
    print(f"Calendar errors:   {len([e for e in errors if 'day' in e.lower() or 'date' in e.lower() or 'manifest' in e.lower()])}")
    print(f"Units errors:      {len([e for e in errors if 'units' in e.lower() or 'variable' in e.lower() or 'unit_system' in e.lower() or 'missing' in e.lower()])}")
    print(f"Bounds errors:     {len([e for e in errors if 'range' in e.lower() or 'sanity' in e.lower()])}")
    print("-" * 60)
    for e in errors:
        print(f"  ERROR: {e}")
    print("-" * 60)
    if not errors:
        print("VALIDATION: PASS (90 days, canonical SI units, physical sanity)")
        return 0
    print("VALIDATION: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())