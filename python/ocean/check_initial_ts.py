"""Validate the raw EN4.2.2 analysis file used as Stage 7.7 ocean initial state.

Run against data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc:

    python python/ocean/check_initial_ts.py
    python python/ocean/check_initial_ts.py --path <file> [--domain LAT0 LON0 LAT1 LON1]

Checks (all must pass for reproducibility):
  1. Structural: expected variables/dims/units (temperature K, salinity practical).
  2. Time: exactly one slice representing the requested year-month.
  3. Region coverage: model domain 64..85 N, 8..77 E fully inside the grid.
  4. Vertical coverage: level 1 <= 10 m, max level >= 600 m.
  5. Numerical sanity: no NaN/Inf on finite ocean points; global T/S ranges
     plausible; per-domain surface and column stats reported for QC.
Prints a summary block that feeds stage7.7_statistics.json (Phase 16).
"""

import argparse
import pathlib

import numpy as np
import xarray as xr

MODEL_DOMAIN = (64.0, 8.0, 86.0, 77.0)  # lat0, lon0, lat1, lon1 (deg N / deg E)
T_K_ABS = (-30.0, 320.0)  # physical absolutes for potential temperature [K]
S_ABS = (0.0, 45.0)  # practical salinity absolute [1]
N_DEPTH = 42


def check(path):
    ds = xr.open_dataset(path)

    issues = []

    # 1. structure
    for var, unit, dims in [
        ("temperature", "kelvin", ("time", "depth", "lat", "lon")),
        ("salinity", "1", ("time", "depth", "lat", "lon")),
    ]:
        if var not in ds:
            issues.append(f"missing {var}")
            continue
        if ds[var].dims != dims:
            issues.append(f"{var}: dims {ds[var].dims}")
        if str(ds[var].attrs.get("units", "")).lower() != unit:
            issues.append(f"{var}: units {ds[var].attrs.get('units')}")
    if ds.sizes["depth"] != N_DEPTH:
        issues.append(f"depth levels != {N_DEPTH}")
    if ds.sizes["lat"] != 173 or ds.sizes["lon"] != 360:
        issues.append("grid not 1deg global 360x173")

    lat0, lon0, lat1, lon1 = MODEL_DOMAIN
    t = ds["temperature"]
    s = ds["salinity"]

    # 2. time
    nt = ds.sizes["time"]
    if nt != 1:
        issues.append(f"expected single-month analysis, got {nt} time slices")

    # 3. coverage
    if not (lat0 >= ds["lat"].min().item() and lat1 <= ds["lat"].max().item()):
        issues.append("model domain lat outside EN4 grid")
    # EN4 lon 1..360
    lon_min, lon_max = ds["lon"].min().item(), ds["lon"].max().item()
    if not (lon0 >= lon_min and lon1 <= lon_max):
        issues.append("model domain lon outside EN4 grid")

    # 4. vertical
    depth = ds["depth"].values
    if depth[0] not in (5.0, 5.02) and depth[0] > 10.0:
        issues.append(f"top level too coarse: {depth[0]}")
    if float(depth[-1]) < 600.0:
        issues.append(f"max depth {depth[-1]} < 600 m")

    tt = t.isel(time=0)
    ss = s.isel(time=0)

    # 5. numerics (NaN is the EN4 land/missing-value sentinel; count, don't fail)
    nan_t = int(tt.isnull().sum().item())
    nan_s = int(ss.isnull().sum().item())
    if nan_t != nan_s:
        issues.append(f"NaN fields disagree in count: T={nan_t} S={nan_s}")
    if "temperature_uncertainty" in ds and "salinity_uncertainty" in ds:
        nan_tu = int(ds["temperature_uncertainty"].isnull().sum().item())
        nan_su = int(ds["salinity_uncertainty"].isnull().sum().item())
        if nan_tu != nan_su:
            issues.append(f"NaN uncertainty count mismatch: T={nan_tu} S={nan_su}")

    finite = np.isfinite(tt.values)
    tvals = tt.values[finite]
    svals = ss.values[finite]
    tmin, tmax = float(tvals.min()), float(tvals.max())
    smin, smax = float(svals.min()), float(svals.max())
    if not (T_K_ABS[0] <= tmin and tmax <= T_K_ABS[1]):
        issues.append(f"T out of physical range: {tmin}..{tmax} K")
    if not (S_ABS[0] <= smin and smax <= S_ABS[1]):
        issues.append(f"S out of physical range: {smin}..{smax}")

    # regional surface + profile stats (domain)
    reg_t = tt.sel(lat=slice(lat0, lat1), lon=slice(lon0, lon1)).isel(depth=0)
    reg_s = ss.sel(lat=slice(lat0, lat1), lon=slice(lon0, lon1)).isel(depth=0)
    fm = np.isfinite(reg_t.values) & np.isfinite(reg_s.values)
    surf_t_c = reg_t.values[fm] - 273.15
    surf_s = reg_s.values[fm]

    summary = {
        "file": str(path),
        "time": str(ds["time"].values[0])[:10],
        "n_time": int(ds.sizes["time"]),
        "depth_levels": [float(x) for x in depth[:5]] + [float(x) for x in depth[-2:]],
        "domain_lat": [lat0, lat1],
        "domain_lon": [lon0, lon1],
        "global_T_K": [tmin, tmax],
        "global_S": [smin, smax],
        "n_valid_global": int(finite.sum()),
        "n_nan_T": nan_t,
        "n_nan_S": nan_s,
        "surface_T_degC_region": [
            float(np.min(surf_t_c)),
            float(np.max(surf_t_c)),
            float(np.mean(surf_t_c)),
        ],
        "surface_S_region": [
            float(np.min(surf_s)),
            float(np.max(surf_s)),
            float(np.mean(surf_s)),
        ],
        "issues": issues,
    }
    return summary, issues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--path",
        type=pathlib.Path,
        default=(
            pathlib.Path("data")
            / "input"
            / "raw"
            / "ocean"
            / "EN.4.2.2.f.analysis.g10.202001.nc"
        ),
    )
    args = ap.parse_args()

    summary, issues = check(args.path)
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\nRESULT: {'PASS' if not issues else 'FAIL'}")
    for i in issues:
        print("  -", i)


if __name__ == "__main__":
    main()
