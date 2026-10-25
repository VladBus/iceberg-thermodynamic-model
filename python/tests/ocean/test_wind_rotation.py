#!/usr/bin/env python3
"""H-2 verification: ERA5 geographic wind -> rotated model-grid wind.

Reads the real grid orientation from KOORD.DAT (FI, DL), computes the local
grid-X angle alpha from the geographic east/north components, loads ERA5
u10/v10, and verifies the rotation algebra:

    dir_grid = atan2(v_grid, u_grid) == dir_geo - alpha  (mod 360)

Mean/max alpha over wet cells should reproduce the documented H-2 values
(~50.2 deg median / ~81 deg maximum).

Output: data/validation/wind_rotation_verification.json.
"""
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
KOORD = PROJECT / "KOORD.DAT"
ERA5 = PROJECT / "data/input/raw/era5/2020/2020_01/era5_2020_01_fullcoverage.nc"
RUN_NC = PROJECT / "data/runs/t3c_legacy_canonical/output/nc/results_day_00.nc"
OUT = PROJECT / "data/validation/wind_rotation_verification.json"


def grid_alpha():
    raw = np.loadtxt(KOORD)
    fi = raw[0].reshape(105, 133)   # (j, i): x=i, y=j in output order
    dl = raw[1].reshape(105, 133)
    dlon = np.gradient(dl, axis=1)  # grid-X direction is i (axis 1)
    dlat = np.gradient(fi, axis=1)
    east = dlon*np.cos(np.deg2rad(fi))
    north = dlat
    alpha = np.arctan2(north, east)  # radians, grid X from geographic east
    return fi, dl, alpha


def wet_mask():
    if RUN_NC.exists():
        with Dataset(RUN_NC) as d:
            return np.array(d["water_column_levels"][:]) > 0
    return np.ones((105, 133), dtype=bool)


def nearest_era5(u10, v10, lat, lon, elat, elon):
    ilat = int(np.argmin(np.abs(elat - lat)))
    # ERA5 longitude may be 0..360 or -180..180; handle both
    lon = lon % 360.0
    elon = elon % 360.0
    ilon = int(np.argmin(np.abs(elon - lon)))
    return float(u10[0, ilat, ilon]), float(v10[0, ilat, ilon])


def ang_diff(a, b):
    return float((a - b + 180.0) % 360.0 - 180.0)


def main():
    if not KOORD.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"status": "SKIP", "reason": "KOORD.DAT absent"}, indent=2))
        print("SKIP: KOORD.DAT absent")
        return 0
    fi, dl, alpha = grid_alpha()
    mask = wet_mask()
    a_deg = np.rad2deg(alpha)
    result = {
        "test": "wind_rotation_H2",
        "stage": "11.8.0 T4-PREP",
        "grid": "KOORD.DAT (FI, DL)",
        "formula": "u_grid = u_geo*cos(a) + v_geo*sin(a); v_grid = -u_geo*sin(a) + v_geo*cos(a)",
        "alpha_mean_deg_wet": float(np.mean(a_deg[mask])),
        "alpha_median_deg_wet": float(np.median(a_deg[mask])),
        "alpha_min_deg_wet": float(np.min(a_deg[mask])),
        "alpha_max_deg_wet": float(np.max(a_deg[mask])),
        "expected_median_deg": 50.2,
        "expected_max_deg": 81.3,
    }
    if not ERA5.exists():
        result["status"] = "SKIP_NO_ERA5"
        OUT.write_text(json.dumps(result, indent=2))
        print("SKIP: ERA5 file absent")
        return 0
    with Dataset(ERA5) as d:
        u10 = np.array(d["u10"][:], dtype=np.float64)
        v10 = np.array(d["v10"][:], dtype=np.float64)
        elat = np.array(d["latitude"][:], dtype=np.float64)
        elon = np.array(d["longitude"][:], dtype=np.float64)

    # Sample several wet cells with nonzero wind.
    jj, ii = np.where(mask)
    order = np.argsort(np.abs(jj - 52) + np.abs(ii - 66))[:20]
    errs = []
    samples = []
    for idx in order:
        j, i = int(jj[idx]), int(ii[idx])
        ug, vg = nearest_era5(u10, v10, fi[j, i], dl[j, i], elat, elon)
        if abs(ug) + abs(vg) < 1e-12:
            continue
        a = alpha[j, i]
        ur = ug*np.cos(a) + vg*np.sin(a)
        vr = -ug*np.sin(a) + vg*np.cos(a)
        dir_geo = np.rad2deg(np.arctan2(vg, ug))
        dir_grid = np.rad2deg(np.arctan2(vr, ur))
        err = ang_diff(dir_grid, dir_geo - np.rad2deg(a))
        errs.append(abs(err))
        if len(samples) < 5:
            samples.append({
                "j": j + 1, "i": i + 1,
                "lat": float(fi[j, i]), "lon": float(dl[j, i]),
                "alpha_deg": float(np.rad2deg(a)),
                "dir_geo_deg": float(dir_geo),
                "dir_grid_deg": float(dir_grid),
                "angular_error_deg": float(err),
            })
    result["samples"] = samples
    result["max_abs_angular_error_deg"] = float(max(errs)) if errs else None
    result["n_checked"] = len(errs)
    result["status"] = (
        "PASS" if errs and max(errs) < 1e-9
        and abs(result["alpha_median_deg_wet"] - 50.2) < 2.0
        and abs(result["alpha_max_deg_wet"] - 81.3) < 3.0
        else "FAIL"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
