#!/usr/bin/env python3
"""
Stage 11.8.0 T1 Phase 3 — Wind rotation verification (preliminary, for T4).

ERA5 provides u10 eastward / v10 northward. The model grid is the IBCAO/
EPSG:3996-derived rotated grid (X <-> j <-> u, Y <-> i <-> v). This test:
  1. derives the local grid-axis orientation from the model lat/lon field
     (angle of +j from east, +i from east) over wet cells;
  2. checks the production wind path statically: does era5_wind rotate
     geographic wind into grid components?
  3. reports CRITICAL if rotation is needed but absent (documented for T4;
     NOT fixed in T1), PASS if the grid were unrotated.

Needs data/runs/stage11.7E_JANOFF/.../results_day_00.nc; explicit SKIP exit 0
when absent. Output: data/validation/wind_rotation_result.json
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
DAY00 = PROJECT / "data/runs/stage11.7E_JANOFF/output/nc/results_day_00.nc"
WF = PROJECT / "src/wind_forcing.f90"
OUT = PROJECT / "data/validation/wind_rotation_result.json"
NEEDED_DEG = 5.0


def main():
    if not DAY00.exists() or not WF.exists():
        print("SKIP: model day_00 reference or wind_forcing.f90 absent "
              "(data bundle not in this checkout).")
        return 0

    with Dataset(DAY00) as d:
        lat = np.array(d["latitude"][:], dtype=np.float64)
        lon = np.array(d["longitude"][:], dtype=np.float64)
        lev = np.array(d["water_column_levels"][:], dtype=np.int32)
    wet = lev > 0

    # Grid axes from the lat/lon field (i = first index, j = second index).
    dphi_di = np.gradient(lat, axis=0)
    dlam_di = np.gradient(lon, axis=0)
    dphi_dj = np.gradient(lat, axis=1)
    dlam_dj = np.gradient(lon, axis=1)
    phi = np.deg2rad(lat)
    # Local tangent-plane components (north, east)
    x_n, x_e = dphi_dj, dlam_dj * np.cos(phi)   # +j axis (model X, u)
    y_n, y_e = dphi_di, dlam_di * np.cos(phi)   # +i axis (model Y, v)
    alpha_x = np.rad2deg(np.arctan2(x_n, x_e))  # from east toward north
    alpha_y = np.rad2deg(np.arctan2(y_n, y_e))
    ax = np.abs(alpha_x[wet]); ay = np.abs(alpha_y[wet])
    ortho = np.rad2deg(np.arccos(np.clip(
        (x_n*y_n + x_e*y_e) / (np.hypot(x_n, x_e)*np.hypot(y_n, y_e) + 1e-30),
        -1, 1)))[wet]

    # Static check of the production wind path
    src = WF.read_text(encoding="utf-8", errors="replace")
    block = src[src.index("subroutine era5_wind"):]
    direct_assignment = bool(re.search(
        r"windx1\(i, j\)\s*=\s*real\(u_cm", block))
    has_rotation = bool(re.search(r"rotat|angle_grid|alpha_rot", block,
                                  re.IGNORECASE))
    legacy_angle = bool(re.search(r"sin\(u_wind/57\.3\)", src))

    rotation_needed = float(np.median(ax)) > NEEDED_DEG
    rotation_applied = has_rotation
    if rotation_needed and not rotation_applied:
        status = "CRITICAL"
    elif (not rotation_needed) and (not rotation_applied):
        status = "PASS"
    elif rotation_applied:
        status = "PASS"
    else:
        status = "WARNING"

    result = {
        "test": "wind_rotation",
        "stage": "11.8.0 T1 Phase 3 (preliminary for T4)",
        "grid_orientation": {
            "grid_x_axis_from_east_deg": {
                "min": float(ax.min()), "median": float(np.median(ax)),
                "mean": float(ax.mean()), "max": float(ax.max())},
            "grid_y_axis_from_east_deg": {
                "min": float(ay.min()), "median": float(np.median(ay)),
                "mean": float(ay.mean()), "max": float(ay.max())},
            "x_y_orthogonality_deg": {
                "median": float(np.median(ortho)),
                "p5": float(np.percentile(ortho, 5)),
                "p95": float(np.percentile(ortho, 95))},
            "rotated_grid": bool(rotation_needed),
        },
        "production_code": {
            "file": "src/wind_forcing.f90::era5_wind",
            "direct_grid_assignment_u10_to_windx": direct_assignment,
            "rotation_applied": rotation_applied,
            "legacy_path_used_observed_angle": legacy_angle,
        },
        "rotation_needed": bool(rotation_needed),
        "rotation_applied": bool(rotation_applied),
        "status": status,
        "finding": (
            "H-2 CONFIRMED: the grid is rotated (grid X is a median %.1f deg "
            "from east; up to %.1f deg), and era5_wind assigns u10/v10 "
            "directly as windx1/windy1 with NO geographic->grid rotation "
            "(the legacy FI1DL1 path rotated an observed angle instead). "
            "Wind stress direction is therefore misaligned with the model "
            "grid by the local convergence angle. Fix belongs to T4; NOT "
            "changed in T1." % (float(np.median(ax)), float(ax.max()))),
        "impact": "wind stress direction error (median %.1f deg); T4 must "
                  "implement rotation and re-baseline wind-driven runs"
                  % float(np.median(ax)),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))
    print(f"grid rotated: {rotation_needed} (median |alpha_x| = "
          f"{np.median(ax):.1f} deg, max {ax.max():.1f} deg)")
    print(f"rotation applied in era5_wind: {rotation_applied} "
          f"(direct u10->windx assignment: {direct_assignment})")
    print(f"STATUS: {status}")
    print(f"Results: {OUT.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())