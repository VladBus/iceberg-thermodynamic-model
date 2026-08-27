#!/usr/bin/env python3
"""Stage 7.6C.2: ERA5 forcing statistics + interpolated-field diagnostics.

Produces:
  data/input/processed/era5/stage7.6C.2_statistics.json   (machine-readable)
  data/output/diagnostics/stage7.6C.2/*.png               (compact summary maps)

The interpolation used below mirrors the Fortran forcing path exactly:
  - ERA5 lat flipped to increasing; lon monotonic increasing;
  - bilinear weights from the bracketing grid nodes;
  - cyclic longitude wrap for the right neighbour;
  - points outside latitude range are rejected (uncovered), never extrapolated.

Run:
  conda run -n iceberg-thermodynamic-model \
      python python/era5/stage7_6c2_forcing_stats.py
"""

import datetime
import json
import pathlib
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "era5"))
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import coup1_ht, read_hhhbar  # noqa: E402
from model_coverage import covered_point, era5_extent  # noqa: E402

NEW_FILE = (
    PROJ_ROOT
    / "data/input/processed/era5/2020/2020_01"
    / "era5_2020_01_fullcoverage_d1_4_merged.nc"
)
OLD_FILE = (
    PROJ_ROOT
    / "data/input/processed/era5/2020/2020_Q1"
    / "era5_2020_0103_barents_expanded_merged.nc"
)
GRID_FILE = PROJ_ROOT / "data/input/processed/grid/ibcao_model_grid.nc"
STATS_JSON = PROJ_ROOT / "data/input/processed/era5/stage7.6C.2_statistics.json"
DIAG_DIR = PROJ_ROOT / "data/output/diagnostics/stage7.6C.2"

RTOL = 1e-8
LAND = 8888.0


def model_geometry():
    ds = xr.open_dataset(GRID_FILE)
    lat = ds["lat"].values
    lon = ds["lon"].values
    ds.close()
    hhbfile = PROJ_ROOT / "hhh.bar"
    if not hhbfile.exists():
        hhbfile = PROJ_ROOT / "data/input/generated/real_grid" / "hhh.bar"
    kt = read_hhhbar(hhbfile)
    wet = coup1_ht(kt) != LAND
    active = np.zeros_like(wet, dtype=bool)
    active[:132, :104] = True
    return lat, lon, wet & active


def bilinear_field(field2d, lat_g, lon_g, lat0, lon0):
    """Fortran-style bilinear interpolation (era5_bilinear2d) on a snapshot.

    field2d is (lat, lon) with lat increasing (already flipped). Returns
    (model point value, ok) where ok=False for any point outside latitude
    range (the same accept/reject rule as the Fortran routine).
    """
    nlat, nlon = field2d.shape
    out = np.full(lat_g.shape, np.nan, dtype=np.float64)
    ok = np.ones(lat_g.shape, dtype=bool)

    lo_lat = np.arange(nlat)
    for (i, j), (la, ln) in _iter_nodes(lat_g, lon_g):
        if not (lat0[0] <= la <= lat0[-1]):
            ok[i, j] = False
            continue
        ilat = int(np.searchsorted(lat0, la, side="right")) - 1
        ilat = max(0, min(ilat, nlat - 2))
        ilat1 = ilat + 1
        lon_w = ((ln % 360.0) + 360.0) % 360.0
        jlon = int(np.searchsorted(lon0, lon_w, side="right")) - 1
        jlon = max(0, min(jlon, nlon - 1))
        jlon1 = jlon + 1
        if jlon1 >= nlon:
            jlon1 = 0
        lat_a, lat_b = lat0[ilat], lat0[ilat1]
        lon_a, lon_b = lon0[jlon], lon0[jlon1] if jlon1 != 0 else lon0[jlon] + 360.0
        wlat = (la - lat_a) / (lat_b - lat_a) if lat_b > lat_a else 0.0
        lon_b = lon_b + 360.0 if lon_b < lon_a else lon_b
        wlon = min(max((lon_w - lon_a) / (lon_b - lon_a), 0.0), 1.0)
        v = (
            (1 - wlat) * (1 - wlon) * field2d[ilat, jlon]
            + wlat * (1 - wlon) * field2d[ilat1, jlon]
            + (1 - wlat) * wlon * field2d[ilat, jlon1]
            + wlat * wlon * field2d[ilat1, jlon1]
        )
        out[i, j] = v
    return out, ok


def _iter_nodes(lat, lon):
    for i in range(lat.shape[0]):
        for j in range(lat.shape[1]):
            yield (i, j), (lat[i, j], lon[i, j])


def domain_stats(file, ds_grid):
    with xr.open_dataset(file) as ds:
        ext = era5_extent(ds)
    lat, lon, req = ds_grid
    n = int(req.sum())
    cov = 0
    for i, j in np.argwhere(req):
        if covered_point(lat[i, j], lon[i, j], *ext):
            cov += 1
    return {
        "era5_lat": ext[:2],
        "era5_lon": ext[2:],
        "total_required": n,
        "covered": cov,
        "uncovered": n - cov,
        "coverage_pct": 100.0 * cov / n,
    }


def main():
    t0 = time.time()
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    grid = model_geometry()
    lat, lon, req = grid

    ds = xr.open_dataset(NEW_FILE)
    lat0 = ds["latitude"].values[::-1].astype(np.float64)  # -> increasing (90..63)
    lon0 = ds["longitude"].values.astype(np.float64)
    ntime = ds.sizes["valid_time"]
    times = ds["valid_time"].values
    varmap = {v: (v, ds[v].attrs.get("units")) for v in ds.data_vars}
    # per-variable global stats (all timesteps)
    var_stats = {}
    for v in ds.data_vars:
        d = ds[v].values.astype(np.float64)
        var_stats[v] = {
            "min": float(np.nanmin(d)),
            "max": float(np.nanmax(d)),
            "mean": float(np.nanmean(d)),
            "nan_count": int(np.isnan(d).sum()),
            "inf_count": int(np.isinf(d).sum()),
            "units": str(ds[v].attrs.get("units")),
        }
        if not np.isfinite(d).all():
            print(f"WARNING: {v} contains NaN/Inf!")
    t1 = time.time()

    # Coverage before/after
    before = domain_stats(OLD_FILE, grid)
    after = domain_stats(NEW_FILE, grid)
    t2 = time.time()

    # Interpolated snapshots on the representative first timestep (for maps+validation)
    snap = ds.isel(valid_time=0)
    fields = {}
    interp_stats = {}
    for v in ("msl", "t2m", "u10", "v10", "sf"):
        if v in snap:
            f, ok = bilinear_field(
                snap[v].values.astype(np.float64), lat, lon, lat0, lon0
            )
            fields[v] = f
            m = np.isfinite(f) & req
            interp_stats[v] = {
                "model_min": float(np.min(f[m])) if m.any() else None,
                "model_max": float(np.max(f[m])) if m.any() else None,
                "model_mean": float(np.mean(f[m])) if m.any() else None,
                "n_interpolated": int(m.sum()),
                "n_uncovered": int((~ok).sum()),
            }
    interp_stats["representative_time"] = str(times[0])
    t3 = time.time()

    # ---------------- plots ----------------
    cmap_c = "RdBu_r"
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    # 1. ERA5 source domain (lat/lon box) + model wet points overlay
    ax = axes[0, 0]
    ax.axhspan(
        after["era5_lat"][0],
        after["era5_lat"][1],
        xmin=0,
        xmax=1,
        color="#d8f0d8",
        zorder=0,
    )
    ax.set_xlim(after["era5_lon"][0] - 2, after["era5_lon"][1] + 2)
    ax.set_ylim(after["era5_lat"][0] - 2, after["era5_lat"][1] + 2)
    ax.plot(lon[req], lat[req], ".", ms=1.5, color="#2255aa", alpha=0.5, zorder=3)
    ax.axhline(after["era5_lat"][0], color="k", lw=1.2, ls="--")
    ax.axhline(after["era5_lat"][1], color="k", lw=1.2, ls="--")
    ax.axvline(after["era5_lon"][0], color="k", lw=1.2, ls="--")
    ax.axvline(after["era5_lon"][1], color="k", lw=1.2, ls="--")
    ax.set_title("1. ERA5 domain (dashed) over model wet grid")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    # 2. Model grid over ERA5 domain
    ax = axes[0, 1]
    ax.imshow(
        np.zeros_like(lat),
        extent=(
            after["era5_lon"][0],
            after["era5_lon"][1],
            after["era5_lat"][0],
            after["era5_lat"][1],
        ),
        cmap="Greys",
        aspect="auto",
    )
    ax.plot(lon[req][::37], lat[req][::37], ".", ms=0.6, color="#cc5522", alpha=0.6)
    ax.set_title("2. Model grid subset (1/37 sampling)")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    # 3. Coverage mask (new domain -> all covered)
    ax = axes[0, 2]
    sc = ax.scatter(
        lon[req],
        lat[req],
        c=[1.0] * int(req.sum()),
        s=6,
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        marker="s",
    )
    ax.set_title("3. Coverage mask (new ERA5): all covered")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    # 4. Interpolated MSL (first step)
    ax = axes[1, 0]
    m = np.isfinite(fields["msl"]) & req
    sc = ax.scatter(lon[m], lat[m], c=fields["msl"][m], s=4, cmap=cmap_c)
    plt.colorbar(sc, ax=ax, label="hPa")
    ax.set_title(f"4. Interp. MSL {times[0]} (Pa->hPa/100)")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    # 5. Interpolated T2M
    ax = axes[1, 1]
    m = np.isfinite(fields["t2m"]) & req
    sc = ax.scatter(lon[m], lat[m], c=fields["t2m"][m] - 273.15, s=4, cmap=cmap_c)
    plt.colorbar(sc, ax=ax, label="degC")
    ax.set_title(f"5. Interp. T2M {times[0]} (K->degC)")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    # 6. Wind speed + direction samples
    ax = axes[1, 2]
    spd = (
        np.hypot(
            fields.get("u10", np.zeros_like(lat)), fields.get("v10", np.zeros_like(lat))
        )
        * 100.0
    )
    m = np.isfinite(spd) & req
    ax.scatter(lon[m], lat[m], c=spd[m], s=4, cmap="viridis")
    step = 9
    ii = np.argwhere(req)[::step]
    ax.quiver(
        lon[ii[:, 0], ii[:, 1]],
        lat[ii[:, 0], ii[:, 1]],
        fields.get("u10", np.zeros_like(lat))[ii[:, 0], ii[:, 1]],
        fields.get("v10", np.zeros_like(lat))[ii[:, 0], ii[:, 1]],
        color="k",
        scale=35,
        width=0.005,
    )
    ax.set_title(f"6. Interp. wind m/s {times[0]}")
    ax.set_xlabel("lon E")
    ax.set_ylabel("lat N")
    fig.tight_layout()
    fig.savefig(DIAG_DIR / "forcing_diagnostics.png", dpi=110)
    plt.close(fig)

    ds.close()
    t4 = time.time()

    # ---------------- stats JSON ----------------
    stats = {
        "stage": "7.6C.2",
        "source_dataset": "reanalysis-era5-single-levels",
        "variables": list(varmap.keys()),
        "dates": {"start": str(times[0]), "end": str(times[-1])},
        "source_resolution": "0.25 x 0.25 deg",
        "temporal_resolution": "6-hourly (00/06/12/18 UTC)",
        "source_domain": {"lat": after["era5_lat"], "lon": after["era5_lon"]},
        "model_domain": {
            "lat": [float(lat.min()), float(lat.max())],
            "lon": [float(lon.min()), float(lon.max())],
        },
        "coverage_before": before,
        "coverage_after": after,
        "coverage_file": "data/input/processed/era5/stage7.6C.2_coverage.json",
        "per_variable": var_stats,
        "interpolated_first_step": interp_stats,
        "processing_time_s": round(t4 - t0, 2),
        "file_sizes_bytes": {
            "raw_instant": None,
            "raw_snowfall": None,
            "merged": None,
        },
    }
    raw_dir = PROJ_ROOT / "data/input/raw/era5/2020/2020_01"
    for name, path in [
        ("raw_instant", raw_dir / "era5_2020_01_fullcoverage_d1_4.nc"),
        ("raw_snowfall", raw_dir / "snowfall_2020_01_fullcoverage_d1_4.nc"),
        ("merged", NEW_FILE),
    ]:
        if path.exists():
            stats["file_sizes_bytes"][name] = path.stat().st_size

    STATS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_JSON, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"statistics written: {STATS_JSON}")
    print(
        f"before: {before['covered']}/{before['total_required']} "
        f"({before['coverage_pct']:.3f}%)"
    )
    print(
        f"after : {after['covered']}/{after['total_required']} "
        f"({after['coverage_pct']:.3f}%)"
    )
    print(
        f"operations: {t1-t0:.1f}s read+stats, {t2-t1:.1f}s coverage, "
        f"{t3-t2:.1f}s interpolation, {t4-t3:.1f}s plots"
    )


if __name__ == "__main__":
    main()
