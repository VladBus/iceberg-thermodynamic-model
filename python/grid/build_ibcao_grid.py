#!/usr/bin/env python3
"""Stage 7.6A: IBCAO V5.2 -> real geographic model grid (132x104 cells, 133x105 nodes).

Reconstructs a modern diagnostic model grid in the native IBCAO polar
stereographic projection (EPSG:3996) with the fixed model spacing
DX = 13,890 m, aggregates the 400 m bathymetry onto node-centred boxes,
derives land/sea mask and depth fields, converts coordinates to lat/lon,
and writes a CF-style NetCDF diagnostic product plus validation plots.

Model grid conventions (derived from src/grid_coupling.f90):
  - scalar T-points (ht, kt1, fi, dl) at every (i,j), i=1..133 (rows),
    j=1..105 (columns);
  - model X axis runs along array j (u-faces hu staggered between j-1,j);
  - model Y axis runs along array i (v-faces hv staggered between i-1,i);
  - therefore longitude varies with j (east) and latitude with i (north).

Aggregation method: pixel-centre assignment into node-centred 13.89 km
boxes (exact partition of the plane; handles the non-integer 34.725
source-pixels-per-cell ratio naturally). Processing is done in
horizontal source strips so peak memory stays far below the 808 MB file.

Usage:
  conda run -n iceberg-thermodynamic-model python python/grid/build_ibcao_grid.py
"""

import json
import os
import resource
import sys
import time

import numpy as np
import rasterio
from pyproj import CRS, Transformer

# ---------------------------------------------------------------- constants
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_TIFF = os.path.join(REPO, "data/input/raw/ibcao/ibcao_v5_2_2026_depth_400m.tiff")
OUT_DIR = os.path.join(REPO, "data/input/processed/grid")
OUT_NC = os.path.join(OUT_DIR, "ibcao_model_grid.nc")
OUT_JSON = os.path.join(OUT_DIR, "grid_validation.json")
PLOT_DIR = os.path.join(OUT_DIR, "plots")

DX_M = 13890.0  # model horizontal step [m] (dxx = 13.89e5 cm)
NI_NODES = 133  # rows    (= is1, includes ghost ring)
NJ_NODES = 105  # columns (= js1, includes ghost ring)
NI_CELLS = 132  # active rows (= is)
NJ_CELLS = 104  # active cols (= js)

CENTRAL_LAT = 74.5  # domain centre (see report §7 for rationale)
CENTRAL_LON = 38.0

WET_FRACTION_THRESHOLD = 0.5  # majority-wet rule for the mask

STRIP_ROWS = 16  # destination node-rows processed per chunk


def build_node_axes(crs: CRS):
    """Regular node axes centred on the projected domain centre."""
    tr = Transformer.from_crs(CRS.from_epsg(4326), crs, always_xy=True)
    cx, cy = tr.transform(CENTRAL_LON, CENTRAL_LAT)
    x = cx + DX_M * (np.arange(NJ_NODES) - (NJ_NODES - 1) / 2.0)  # along j (east)
    y = cy + DX_M * (np.arange(NI_NODES) - (NI_NODES - 1) / 2.0)  # along i (north)
    return x, y


def aggregate(src_path: str, x: np.ndarray, y: np.ndarray):
    """Aggregate source elevation onto node-centred boxes, strip by strip.

    Returns dict of 2-D arrays shaped (NI_NODES, NJ_NODES).
    """
    half = DX_M / 2.0
    n_total = np.zeros((NI_NODES, NJ_NODES))
    sum_elev = np.zeros((NI_NODES, NJ_NODES))
    n_wet = np.zeros((NI_NODES, NJ_NODES))
    sum_wet = np.zeros((NI_NODES, NJ_NODES))

    with rasterio.open(src_path) as ds:
        a, b, c, d_aff, e, f_aff = (
            ds.transform.a,
            ds.transform.b,
            ds.transform.c,
            ds.transform.d,
            ds.transform.e,
            ds.transform.f,
        )
        px, py = a, e  # +400, -400 (north-up)
        ymax = f_aff
        width = ds.width

        for i0 in range(0, NI_NODES, STRIP_ROWS):
            i1 = min(i0 + STRIP_ROWS, NI_NODES)

            # source rows covering this destination block; row centres:
            # y(row) = ymax + py*(row + 0.5), py = -400 (north-up)
            def src_rows_for(yv):
                lo = (ymax - (yv + half)) / (-py) - 0.5
                hi = (ymax - (yv - half)) / (-py) - 0.5
                return max(int(np.ceil(lo)), 0), min(int(np.floor(hi)) + 1, ds.height)

            r_blocks = [src_rows_for(y[ii]) for ii in range(i0, i1)]
            r0 = min(r for r, _ in r_blocks)
            r1 = max(r for _, r in r_blocks)
            if r1 <= r0:
                continue
            win = rasterio.windows.Window(0, r0, width, r1 - r0)
            strip = ds.read(1, window=win).astype(np.float32)  # (rows, 14550)

            wet_strip = strip < 0.0
            for ii in range(i0, i1):
                sr0, sr1 = r_blocks[ii - i0]
                if sr1 <= sr0:
                    continue
                loc = strip[sr0 - r0 : sr1 - r0, :]
                lwet = wet_strip[sr0 - r0 : sr1 - r0, :]
                for jj in range(NJ_NODES):
                    xc = x[jj]
                    c_lo = (xc - half - c) / px - 0.5
                    c_hi = (xc + half - c) / px - 0.5
                    sc0 = max(int(np.ceil(c_lo)), 0)
                    sc1 = min(int(np.floor(c_hi)) + 1, width)
                    if sc1 <= sc0:
                        continue
                    cell = loc[:, sc0:sc1]
                    cwet = lwet[:, sc0:sc1]
                    n = cell.size
                    nw = int(cwet.sum())
                    n_total[ii, jj] += n
                    sum_elev[ii, jj] += float(cell.sum(dtype=np.float64))
                    n_wet[ii, jj] += nw
                    sum_wet[ii, jj] += float(cell[cwet].sum(dtype=np.float64))

    valid = n_total > 0
    mean_elev = np.full((NI_NODES, NJ_NODES), np.nan)
    mean_elev[valid] = sum_elev[valid] / n_total[valid]
    mean_wet_elev = np.full((NI_NODES, NJ_NODES), np.nan)
    hwet = n_wet > 0
    mean_wet_elev[hwet] = sum_wet[hwet] / n_wet[hwet]
    wet_fraction = np.zeros((NI_NODES, NJ_NODES))
    wet_fraction[valid] = n_wet[valid] / n_total[valid]
    mask = (wet_fraction >= WET_FRACTION_THRESHOLD).astype(np.int8)
    depth_m = np.where(mask == 1, -mean_wet_elev, np.nan)  # positive down

    return {
        "mean_elev": mean_elev,
        "mean_wet_elev": mean_wet_elev,
        "wet_fraction": wet_fraction,
        "mask": mask,
        "depth_m": depth_m,
        "n_valid_cells": int(valid.sum()),
        "n_empty_cells": int((~valid).sum()),
    }


def main() -> int:
    t_start = time.time()

    with rasterio.open(SRC_TIFF) as ds:
        src_crs = CRS.from_wkt(ds.crs.to_wkt())

    x, y = build_node_axes(src_crs)
    print(
        f"Domain centre (projected): x={x[NJ_NODES // 2]:.1f} m, "
        f"y={y[NI_NODES // 2]:.1f} m"
    )

    agg = aggregate(SRC_TIFF, x, y)

    # ---- coordinate conversion to geographic ------------------------------
    tr_fwd = Transformer.from_crs(src_crs, CRS.from_epsg("4326"), always_xy=True)
    XX, YY = np.meshgrid(x, y)  # (i, j): x varies with j, y with i
    LON, LAT = tr_fwd.transform(XX, YY)

    # ---- quantitative validation ------------------------------------------
    dx_diffs = np.diff(x)
    dy_diffs = np.diff(y)
    wet = agg["mask"] == 1
    interior = np.s_[1 : NI_NODES - 1, 1 : NJ_NODES - 1]
    depth_int = agg["depth_m"][interior][wet[interior]]
    wf_coastal = (agg["wet_fraction"][interior] > 0.05) & (
        agg["wet_fraction"][interior] < 0.95
    )
    depth_hist_edges = [0, 100, 200, 300, 400, 500, 600, 1000, 5000]
    depth_hist, _ = np.histogram(depth_int, bins=depth_hist_edges)
    deep_i, deep_j = np.where(wet[interior] & (agg["depth_m"][interior] > 600.0))
    stats = {
        "dx_m_design": DX_M,
        "dx_actual_min_max": [float(dx_diffs.min()), float(dx_diffs.max())],
        "dy_actual_min_max": [float(dy_diffs.min()), float(dy_diffs.max())],
        "dims_nodes": [NI_NODES, NJ_NODES],
        "dims_active_cells": [NI_CELLS, NJ_CELLS],
        "lat_range_deg": [float(LAT.min()), float(LAT.max())],
        "lon_range_deg": [float(LON.min()), float(LON.max())],
        "lat_monotonic_increasing_with_i": bool(np.all(np.diff(LAT[:, 0]) > 0)),
        "lon_monotonic_increasing_with_j": bool(np.all(np.diff(LON[0, :]) > 0)),
        "depth_min_m": float(depth_int.min()) if depth_int.size else None,
        "depth_max_m": float(depth_int.max()) if depth_int.size else None,
        "n_wet_interior": int(wet[interior].sum()),
        "n_land_interior": int((~wet[interior]).sum()),
        "pct_wet_interior": round(float(wet[interior].mean() * 100.0), 2),
        "cells_outside_source": agg["n_empty_cells"],
        "nodata_declared_in_source": None,
        "deep_cells_gt600m": int((depth_int > 600.0).sum()) if depth_int.size else 0,
        "depth_histogram_cells": {
            f"{depth_hist_edges[k]}-{depth_hist_edges[k + 1]} m": int(depth_hist[k])
            for k in range(len(depth_hist))
        },
        "coastal_cells_5_95pct_wet": int(wf_coastal.sum()),
        "deep_cell_index_range_i_j": (
            [int(deep_i.min()), int(deep_i.max())] if deep_i.size else None,
            [int(deep_j.min()), int(deep_j.max())] if deep_j.size else None,
        ),
        "mean_depth_wet_cells_m": (
            round(float(depth_int.mean()), 1) if depth_int.size else None
        ),
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))

    # ---- NetCDF product ----------------------------------------------------
    from netCDF4 import Dataset

    if os.path.exists(OUT_NC):
        os.remove(OUT_NC)
    with Dataset(OUT_NC, "w", format="NETCDF4") as nc:
        nc.createDimension("i", NI_NODES)
        nc.createDimension("j", NJ_NODES)
        nc.title = "IBCAO V5.2 reconstructed model grid (Stage 7.6A diagnostic)"
        nc.institution = "RSHU thesis project - iceberg thermodynamic model"
        nc.source = (
            "Aggregated from ibcao_v5_2_2026_depth_400m.tiff " "(EPSG:3996, 400 m)"
        )
        nc.history = f"created {time.strftime('%Y-%m-%dT%H:%M:%S')} by python/grid/build_ibcao_grid.py"
        nc.Conventions = "CF-1.10"
        nc.grid_spacing_m = DX_M
        nc.model_dims_active = f"{NI_CELLS}x{NJ_CELLS}"
        nc.model_dims_nodes = f"{NI_NODES}x{NJ_NODES}"
        nc.axis_convention = (
            "model X along j (east), model Y along i (north); "
            "B-grid: u between j-1..j, v between i-1..i"
        )
        nc.aggregation_method = (
            "pixel-centre assignment into node-centred "
            "13890 m boxes; mask = wet_fraction >= 0.5; "
            "depth = -(mean ocean-only elevation)"
        )

        v = nc.createVariable("proj_x", "f8", ("j",))
        v.units = "m"
        v.standard_name = "projection_x_coordinate"
        v[:] = x
        v = nc.createVariable("proj_y", "f8", ("i",))
        v.units = "m"
        v.standard_name = "projection_y_coordinate"
        v[:] = y
        v = nc.createVariable("lat", "f8", ("i", "j"))
        v.units = "degrees_north"
        v.standard_name = "latitude"
        v[:] = LAT
        v = nc.createVariable("lon", "f8", ("i", "j"))
        v.units = "degrees_east"
        v.standard_name = "longitude"
        v[:] = LON
        v = nc.createVariable(
            "depth", "f4", ("i", "j"), fill_value=np.float32(9.96921e36)
        )
        v.units = "m"
        v.positive = "down"
        v.long_name = "model bathymetric depth (ocean pixels only)"
        v.comment = "NaN-equivalent fill over land cells"
        d32 = agg["depth_m"].astype(np.float32)
        d32[np.isnan(d32)] = np.float32(9.96921e36)
        v[:] = d32
        v = nc.createVariable("mask", "i1", ("i", "j"))
        v.flag_values = np.array([0, 1], dtype=np.int8)
        v.flag_meanings = "land wet"
        v.long_name = "land/sea mask (majority-wet rule)"
        v[:] = agg["mask"]
        v = nc.createVariable("wet_fraction", "f4", ("i", "j"))
        v.units = "1"
        v.valid_min = 0.0
        v.valid_max = 1.0
        v.long_name = (
            "fraction of IBCAO source pixels with elevation < 0 per model node box"
        )
        v[:] = agg["wet_fraction"].astype(np.float32)
        crs_var = nc.createVariable("crs", "i4", ())
        crs_var.grid_mapping_name = "polar_stereographic"
        crs_var.crs_wkt = src_crs.to_wkt()
        crs_var.epsg_code = src_crs.to_epsg()
        crs_var.latitude_of_projection_origin = 90.0
        crs_var.standard_parallel = 75.0
        crs_var.straight_vertical_longitude_from_pole = 0.0
        for name in ("lat", "lon", "depth", "mask", "wet_fraction"):
            nc.variables[name].grid_mapping = "crs"
        nc.variables["lat"].coordinates = "lon lat"
    print(f"NetCDF written: {OUT_NC}")

    # ---- diagnostic plots ---------------------------------------------------
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1. source overview (decimated window around the domain)
    with rasterio.open(SRC_TIFF) as ds:
        inv = ~ds.transform
        xs = [
            inv * (xx + 0, yy + 0)
            for xx, yy in [(XX.min(), YY.min()), (XX.max(), YY.max())]
        ]
        cols = sorted(c for c, _ in xs)
        rows = sorted(r for _, r in xs)
        w = rasterio.windows.Window(
            cols[0], rows[0], cols[-1] - cols[0], rows[-1] - rows[0]
        )
        scale = 20
        ov = ds.read(
            1,
            window=w,
            out_shape=(max(int(w.height / scale), 1), max(int(w.width / scale), 1)),
        )
        ext = [
            cols[0] * 400 - 2910000,
            cols[-1] * 400 - 2910000,
            2910000 - rows[-1] * 400,
            2910000 - rows[0] * 400,
        ]

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(ov, cmap="viridis", extent=ext, origin="upper", vmin=-500, vmax=500)
    ax.plot(XX[::10, ::10], YY[::10, ::10], "r.", ms=1)
    ax.set_title("IBCAO V5.2 (domain window) + model node footprint")
    ax.set_xlabel("x EPSG:3996 [m]")
    ax.set_ylabel("y EPSG:3996 [m]")
    fig.colorbar(im, ax=ax, label="elevation [m] (<0 ocean)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "01_source_window.png"), dpi=120)
    plt.close(fig)

    # 2-4. model products
    fig, axs = plt.subplots(1, 3, figsize=(17, 5))
    im0 = axs[0].pcolormesh(agg["depth_m"], cmap="viridis")
    axs[0].set_title("model depth [m], positive down")
    fig.colorbar(im0, ax=axs[0])
    im1 = axs[1].imshow(agg["mask"], cmap="Blues", vmin=-0.2, vmax=1.2)
    axs[1].set_title("land/sea mask (1=wet)")
    fig.colorbar(im1, ax=axs[1])
    im2 = axs[2].pcolormesh(agg["wet_fraction"], cmap="RdBu", vmin=0, vmax=1)
    axs[2].set_title("wet fraction per node box")
    fig.colorbar(im2, ax=axs[2])
    for ax in axs:
        ax.set_xlabel("j (east)")
        ax.set_ylabel("i (north)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "02_model_products.png"), dpi=120)
    plt.close(fig)

    # 5. geographic overlay
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.pcolormesh(
        LON, LAT, agg["mask"], cmap="Blues", vmin=-0.2, vmax=1.2, shading="auto"
    )
    step_i, step_j = 8, 8
    for ii in range(0, NI_NODES, step_i):
        ax.plot(LON[ii, :], LAT[ii, :], "k-", lw=0.3)
    for jj in range(0, NJ_NODES, step_j):
        ax.plot(LON[:, jj], LAT[:, jj], "k-", lw=0.3)
    ax.set_title("reconstructed grid on lat/lon (mask shaded)")
    ax.set_xlabel("longitude [degE]")
    ax.set_ylabel("latitude [degN]")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "03_geographic_overlay.png"), dpi=120)
    plt.close(fig)
    print(f"Plots written: {PLOT_DIR}")

    elapsed = time.time() - t_start
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"elapsed: {elapsed:.1f} s | peak RSS: {peak_mb:.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
