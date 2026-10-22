#!/usr/bin/env python3
"""
Stage 11.8.0 T0 Phase 3 — ERA5 coverage / edges / time / rotation checks.

Checks (all read-only diagnostics):
  A. Spatial margin (>=1 deg) of each merged ERA5 product against the MODEL
     water-cell bounding box taken from stage11.7E_JANOFF day_00
     (latitude/longitude on model grid).
  B. Longitude edge handling: are any model cells outside the file lon range
     (i.e. does the wrap code actually run)? Documents reader behavior:
     +-360 normalization + cyclic dateline node (netcdf_input.f90).
  C. Latitude out-of-range count -> exercises the Stage 11.4-D32 nearest-edge
     clamp (wind_forcing.f90); counts cells per file that rely on it.
  D. Time axis: uniform spacing (no gaps) + nearest-time selection documented
     (era5_find_time_index).
  E. Wind rotation PRELIMINARY (H-2): static check whether era5_wind rotates
     geographic u10/v10 into grid axes. Finding is recorded for T4; NO fix.

Statuses PASS/WARNING/FAIL; overall CLEAN / ISSUES_FOUND.
Output: data/validation/era5_coverage_result.json (relative paths).
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
DAY00 = PROJECT / "data/runs/stage11.7E_JANOFF/output/nc/results_day_00.nc"
MERGED = {
    "jan_fullcoverage": "data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc",
    "apr_merged": "data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc",
}
NWC = PROJECT / "src/netcdf_input.f90"
WF = PROJECT / "src/wind_forcing.f90"
OUT = PROJECT / "data/validation/era5_coverage_result.json"
REQUIRED_MARGIN_DEG = 1.0


class Acc:
    def __init__(self):
        self.checks = []

    def add(self, name, status, detail):
        self.checks.append({"name": name, "status": status, "detail": detail})
        print(f"  {status:7s} {name}: {detail}")


def model_domain():
    with Dataset(DAY00) as d:
        lat = np.array(d["latitude"][:], dtype=np.float64)
        lon = np.array(d["longitude"][:], dtype=np.float64)
        lev = np.array(d["water_column_levels"][:], dtype=np.int32)
    wet = lev > 0
    return (float(lat[wet].min()), float(lat[wet].max()),
            float(lon[wet].min()), float(lon[wet].max()),
            np.where(wet, lat, np.nan), np.where(wet, lon, np.nan))


def main():
    if not DAY00.exists():
        print("SKIP: model day_00 reference absent (data bundle not here).")
        return 0
    acc = Acc()
    latmin, latmax, lonmin, lonmax, wat, wlon = model_domain()
    print(f"Model wet-cell domain: lat[{latmin:.2f},{latmax:.2f}] "
          f"lon[{lonmin:.2f},{lonmax:.2f}]")

    era5 = {}
    for tag, rel in MERGED.items():
        p = PROJECT / rel
        if not p.exists():
            acc.add(f"{tag}: file present", "SKIP-INFO",
                    f"{rel} absent in this checkout")
            continue
        with Dataset(p) as d:
            lat = np.array(d["latitude"][:], dtype=np.float64)
            lon = np.array(d["longitude"][:], dtype=np.float64)
            t = np.array(d["valid_time"][:], dtype=np.int64)
        era5[tag] = {"file": rel,
                     "lat": (float(lat.min()), float(lat.max())),
                     "lon": (float(lon.min()), float(lon.max())),
                     "n_times": int(len(t)),
                     "time_spacing_s": sorted({int(x) for x in np.diff(t)})}
        la_lo, la_hi = era5[tag]["lat"]
        lo_lo, lo_hi = era5[tag]["lon"]
        global_lon = (lo_hi - lo_lo) >= 359.0
        # Positive margin = FILE edge extends BEYOND the model edge (covered
        # with slack); negative/insufficient -> audit margin unmet there.
        margin_south = latmin - la_lo
        margin_north = la_hi - latmax
        if global_lon:
            margin_west = margin_east = float("inf")   # global lon covers all
        else:
            margin_west = lonmin - lo_lo
            margin_east = lo_hi - lonmax
        margins = {"south": round(margin_south, 3), "north": round(margin_north, 3),
                   "west": (margin_west if margin_west == float("inf")
                            else round(margin_west, 3)),
                   "east": (margin_east if margin_east == float("inf")
                            else round(margin_east, 3))}
        worst = min(margin_south, margin_north, margin_west, margin_east)
        acc.add(f"{tag}: coverage margin >= {REQUIRED_MARGIN_DEG} deg",
                "PASS" if worst >= REQUIRED_MARGIN_DEG else "WARNING",
                f"margins_deg {margins} (global lon: {global_lon}); "
                "negative = file edge inside model domain (cells beyond it "
                "rely on the D32 nearest-edge clamp)")

        n_out_lat = int(np.nansum((wat < la_lo) | (wat > la_hi)))
        n_out_lon = int(np.nansum((wlon < lo_lo) | (wlon > lo_hi))) \
            if not global_lon else 0
        acc.add(f"{tag}: model cells outside file latitude range",
                "PASS" if n_out_lat == 0 else "WARNING",
                f"{n_out_lat} cells -> rely on D32 nearest-edge clamp")
        acc.add(f"{tag}: model cells outside file longitude range",
                "PASS" if n_out_lon == 0 else "WARNING",
                f"{n_out_lon} cells -> rely on +-360 wrap (none expected; "
                "domain 8-77E)")

        sp = era5[tag]["time_spacing_s"]
        uniform = len(sp) == 1
        acc.add(f"{tag}: uniform time axis (no forcing gaps)",
                "PASS" if uniform and sp[0] in (3600, 21600) else "WARNING",
                f"spacing {sp} s over {era5[tag]['n_times']} steps")

    # Static reader-behaviour documentation
    if NWC.exists() and WF.exists():
        nwc = NWC.read_text(encoding="utf-8", errors="replace")
        wf = WF.read_text(encoding="utf-8", errors="replace")
        acc.add("netcdf_input: cyclic-longitude handling present",
                "PASS" if "lon_wrap" in nwc and "jlon1 = 1" in nwc else "FAIL",
                "+-360 normalization + dateline neighbour node")
        acc.add("netcdf_input: out-of-range latitude returns not-ok",
                "PASS" if ".lt. era5_lat(1) .or." in nwc else "FAIL",
                "no extrapolation; handled by D32 clamp in era5_wind")
        acc.add("wind_forcing: D32 nearest-edge clamp documented",
                "PASS" if "lat_use = min(max(" in wf else "FAIL",
                "Stage 11.4-D32")
        acc.add("time selection: nearest-time (era5_find_time_index)",
                "PASS" if "era5_find_time_index" in nwc + wf else "FAIL",
                "documented assumption; no temporal interpolation between "
                "6-hourly analyses (H-4 note for T1/T5)")
        # wind rotation preliminary: ERA5 path maps u10->windx, v10->windy raw
        rotated = bool(re.search(r"rotat", wf, re.IGNORECASE))
        acc.add("H-2 wind rotation PRELIMINARY (ERA5 path)",
                "WARNING",
                "era5_wind copies u10/v10 (x100) into windx1/windy1 as grid "
                "components WITHOUT geographic->grid (EPSG:3996) rotation; "
                "legacy path used observed-angle sin/cos (different basis). "
                "Documented for T4; NOT fixed in T0")
    else:
        acc.add("source files for static checks", "SKIP-INFO", "not found")

    statuses = [c["status"] for c in acc.checks]
    overall = ("ISSUES_FOUND" if any(s in ("FAIL", "WARNING") for s in statuses)
               else "CLEAN")
    out = {"test": "era5_coverage_verification",
           "stage": "11.8.0 T0 Phase 3",
           "model_domain": {"lat": [latmin, latmax], "lon": [lonmin, lonmax]},
           "era5_products": era5, "overall": overall, "checks": acc.checks}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nChecks: {len(acc.checks)}  "
          f"PASS={statuses.count('PASS')} WARNING={statuses.count('WARNING')} "
          f"FAIL={statuses.count('FAIL')}")
    print(f"OVERALL: {overall}")
    print(f"Results: {OUT.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())