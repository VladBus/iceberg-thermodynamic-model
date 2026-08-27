#!/usr/bin/env python3
"""Regrid the raw EN4.2.2 January-2020 ocean analysis onto the model grid
(Stage 7.7 realistic initial ocean T/S).

Pipeline (documented in docs/wiki/Stage7.7_Realistic_Ocean_Initialisation.md):

  horizontal  nearest-neighbour (in lat/lon degrees) from EN4 *wet* points to
              every model wet T-node (is1 x js1). No interpolation across land:
              the source set is only points with at least one finite T/S sample,
              so coasts of 1-deg cells are never bridged into the ocean.
  vertical    per model column, piecewise-linear between finite EN4 depth
              samples; level 1 (2.5 m) uses the 0-10 m EN4 layer value
              (no extrapolation above the shallowest sample);
              deepest-finite value is used when the model column is deeper than
              the EN4 column bottom (reported, not silently extrapolated);
              model columns over product land (EN4 column all-NaN) are flagged
              and left 0 (reported).
  units       T: K -> deg-C (potential temperature treated as the model's
              in-situ-like state variable - documented in Phase 2); S: practical
              -> mass fraction (/1000).

Outputs
-------
  data/input/processed/ocean/initial_ts_2020-01-01.nc   (model-format)
  stage7.7 statistics JSON (data/output/diagnostics/stage7.7/)

Usage
-----
    python python/ocean/build_initial_ts.py
    python python/ocean/build_initial_ts.py --raw <file> --out <file> --json <file>
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import xarray as xr
from scipy.spatial import cKDTree

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import load_model_grid  # noqa: E402

# Model Z-level centres in cm (src/param.f90 data z / ...). Positive down.
Z_CM = np.array(
    [
        250,
        500,
        1000,
        1500,
        2000,
        2500,
        3000,
        4000,
        5000,
        7500,
        10000,
        15000,
        20000,
        25000,
        30000,
        40000,
        50000,
        60000,
    ]
)
Z_M = Z_CM / 100.0

DEFAULT_RAW = PROJ_ROOT / "data/input/raw/ocean" / "EN.4.2.2.f.analysis.g10.202001.nc"
DEFAULT_OUT = PROJ_ROOT / "data/input/processed/ocean" / "initial_ts_2020-01-01.nc"
DEFAULT_JSON = (
    PROJ_ROOT / "data/output/diagnostics/stage7.7" / "stage7.7_statistics.json"
)


def eckart_ro(t_c, s_frac, dtype=np.float32):
    """Eckart density anomaly ro = rho - 1.02 [g/cm3] (float32, model-faithful).

    src/equation_of_state.f90:55-68 with S as mass fraction (0.033-0.035).
    """
    t = np.asarray(t_c, dtype=dtype)
    s = np.asarray(s_frac, dtype=dtype)
    aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
    bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
    return 1.0 / (0.698 + aa / bb) - 1.02


def synthetic_baseline(wet, kk1):
    """Reconstruct init_ocean()'s synthetic T/S (initial_conditions.f90:20-86)."""
    is1, js1 = wet.shape
    ks = len(Z_CM)
    t = np.zeros((is1, js1, ks), dtype=np.float32)
    s = np.zeros((is1, js1, ks), dtype=np.float32)
    for k in range(ks):
        dr = k / (ks - 1)
        t[:, :, k] = 15.0 - 13.0 * dr
        s[:, :, k] = 0.033 + 0.002 * dr
    hot = np.zeros((is1, js1), dtype=bool)
    hot[51:79, 41:59] = True
    for k in range(min(5, ks)):
        t[:, :, k] += np.where(hot, 8.0, 0.0)
    lvl = np.arange(1, ks + 1)[None, None, :]
    m = wet[:, :, None] & (lvl <= kk1[:, :, None])
    t = np.where(m, t, 0.0).astype(np.float32)
    s = np.where(m, s, 0.0).astype(np.float32)
    return t, s


def vertical_regrid(t_c, s_f, d_en4, ilat, ilon, need):
    """Map EN4 columns (already converted units) to model levels for all cells.

    need: bool (is1, js1, ks) - cells a value is required for (wet & k<=kk1).
    Returns t_out, s_out (float32), flag (int8 per cell):
      0 interpolated piecewise-linear
      1 shallowest-finite (top layer / above shallowest sample)
      2 deepest-finite (model column deeper than EN4 column bottom)
      3 product-land column (EN4 column all-NaN) - output left 0
    """
    is1, js1, ks = need.shape
    nz = d_en4.shape[0]
    t_out = np.zeros((is1, js1, ks), dtype=np.float32)
    s_out = np.zeros((is1, js1, ks), dtype=np.float32)
    flag = np.zeros((is1, js1, ks), dtype=np.int8)

    tcol = np.moveaxis(t_c[:, ilat, ilon], 0, -1)  # (is1, js1, nz)
    scol = np.moveaxis(s_f[:, ilat, ilon], 0, -1)
    for i in range(is1):
        for j in range(js1):
            tv = tcol[i, j]
            sv = scol[i, j]
            mf = np.isfinite(tv) & np.isfinite(sv)
            idx = np.where(mf)[0]
            if idx.size == 0:
                flag[i, j, :] = 3  # product-land column -> sentinel 0
                continue
            zf = d_en4[idx]
            tvf, svf = tv[idx], sv[idx]
            for k in range(ks):
                if not need[i, j, k]:
                    continue
                zm = Z_M[k]
                if zf[0] >= zm:
                    # top layer: model level at/below shallowest EN4 sample
                    t_out[i, j, k], s_out[i, j, k] = tvf[0], svf[0]
                    flag[i, j, k] = 1
                    continue
                lo = int(np.searchsorted(zf, zm, side="right") - 1)
                if lo < 0:
                    t_out[i, j, k], s_out[i, j, k] = tvf[0], svf[0]
                    flag[i, j, k] = 1
                elif lo >= idx.size - 1:
                    t_out[i, j, k], s_out[i, j, k] = tvf[-1], svf[-1]
                    flag[i, j, k] = 2
                else:
                    w = (zm - zf[lo]) / (zf[lo + 1] - zf[lo])
                    t_out[i, j, k] = (1 - w) * tvf[lo] + w * tvf[lo + 1]
                    s_out[i, j, k] = (1 - w) * svf[lo] + w * svf[lo + 1]
                    flag[i, j, k] = 0
    return t_out, s_out, flag


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=pathlib.Path, default=DEFAULT_RAW)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = ap.parse_args()

    g = load_model_grid()
    lat, lon = g["lat"], g["lon"]
    wet = g["wet"]
    ht_cm = g["water_depth_cm"]
    is1, js1 = lat.shape
    ks = len(Z_CM)

    kk1 = np.zeros((is1, js1), dtype=np.int64)
    kk1[wet] = np.searchsorted(Z_CM, ht_cm[wet], side="right")
    lvl = np.arange(1, ks + 1)[None, None, :]
    need = wet[:, :, None] & (lvl <= kk1[:, :, None])

    with xr.open_dataset(args.raw) as ds:
        t_k = ds["temperature"].isel(time=0).values  # (depth, nlat, nlon) K
        s_p = ds["salinity"].isel(time=0).values
        d_en4 = ds["depth"].values
        en4_lat = ds["lat"].values
        en4_lon = ds["lon"].values
    t_c = (t_k - 273.15).astype(np.float32)
    s_f = (s_p / 1000.0).astype(np.float32)

    en4_wet = np.any(np.isfinite(t_k), axis=0)
    print(
        f"EN4 wet grid points : {int(en4_wet.sum())} / "
        f"{t_k.shape[1] * t_k.shape[2]}"
    )

    en4_rc = np.argwhere(en4_wet)  # (ilat, ilon) rows/cols
    en4_pts = np.column_stack([en4_lat[en4_rc[:, 0]], en4_lon[en4_rc[:, 1]]])
    tree = cKDTree(en4_pts, compact_nodes=True, balanced_tree=True)
    model_pts = np.column_stack([lat.ravel(), lon.ravel()])
    dist, ind = tree.query(model_pts, k=1, workers=-1)
    dist = dist.reshape(is1, js1)
    ilat = en4_rc[ind, 0].reshape(is1, js1)
    ilon = en4_rc[ind, 1].reshape(is1, js1)
    print(
        f"NN horizontal distance(deg): min={dist[wet].min():.3f} "
        f"mean={dist[wet].mean():.3f} max={dist[wet].max():.3f}"
    )

    t_out, s_out, flag = vertical_regrid(t_c, s_f, d_en4, ilat, ilon, need)

    bad = ~np.isfinite(t_out) | ~np.isfinite(s_out)
    n_bad = int(bad.sum())

    active = np.zeros_like(wet)
    active[:132, :104] = True
    wet_active = wet & active

    flag_label = {
        0: "interp",
        1: "shallowest_finite",
        2: "deepest_finite",
        3: "product_land_column",
    }
    flag_counts = {}
    for f, name in flag_label.items():
        flag_counts[name] = int((flag == f).sum())
    n_col_pld = int(np.any(flag == 3, axis=2)[wet_active].sum())
    n_col_deep = int(np.any(flag == 2, axis=2)[wet_active].sum())
    n_uncovered = n_col_pld
    n_low_conf = int((dist > 1.5)[wet_active].sum())

    ro = eckart_ro(t_out, s_out)
    n_bad_ro = int(np.count_nonzero(~np.isfinite(ro)))

    stats_levels = {}
    for k in [0, 4, 9, 17]:
        m = wet_active & (kk1 >= k + 1)
        stats_levels[f"level{k + 1:02d}_z{Z_M[k]:g}m"] = {
            "n_cells": int(m.sum()),
            "T_degC": [
                float(np.min(t_out[:, :, k][m])),
                float(np.max(t_out[:, :, k][m])),
                float(np.mean(t_out[:, :, k][m])),
            ],
            "S_frac": [
                float(np.min(s_out[:, :, k][m])),
                float(np.max(s_out[:, :, k][m])),
                float(np.mean(s_out[:, :, k][m])),
            ],
            "ro_gcm3": [
                float(np.min(ro[:, :, k][m])),
                float(np.max(ro[:, :, k][m])),
                float(np.mean(ro[:, :, k][m])),
            ],
        }

    t_syn, s_syn = synthetic_baseline(wet, kk1)
    m = wet_active[:, :, None] & need
    dT = np.abs(t_out - t_syn)[m]
    dS = np.abs(s_out - s_syn)[m]

    # static stability check (model threshold 0.9e-7 g/cm3 on float32 ro)
    inv_count = 0
    inv_cols = 0
    for k in range(ks - 1):
        m2 = wet_active & (kk1 >= k + 2)
        if m2.any():
            d = ro[:, :, k] - ro[:, :, k + 1]
            unstable = d < -0.9e-7
            inv_count += int(np.count_nonzero(unstable & m2))
            inv_cols += int(np.count_nonzero(np.any(unstable & m2, axis=0)))

    stats = {
        "stage": "7.7",
        "target_date": "2020-01-01",
        "source_file": str(args.raw),
        "source_time_mid": "2020-01-16",
        "method": "NN-wet horizontal + piecewise-linear vertical (see build doc)",
        "grid_is1_js1_ks": [is1, js1, ks],
        "z_model_m": [float(x) for x in Z_M],
        "wet_cells": int(wet.sum()),
        "active_wet_cells": int(wet_active.sum()),
        "en4_wet_points": int(en4_wet.sum()),
        "nn_dist_deg_min_mean_max": [
            float(dist[wet].min()),
            float(dist[wet].mean()),
            float(dist[wet].max()),
        ],
        "h_low_confidence_gt_1p5deg": n_low_conf,
        "columns_product_land_flag3": n_col_pld,
        "uncovered_active_wet_cells": n_uncovered,
        "columns_deeper_than_en4_flag2": n_col_deep,
        "flag_counts": flag_counts,
        "n_nan_inf_output": n_bad,
        "n_nan_inf_ro": n_bad_ro,
        "static_instability_interfaces": inv_count,
        "static_instability_columns_active": inv_cols,
        "levels_1_5_10_18": stats_levels,
        "mean_abs_diff_vs_synthetic_T_degC": float(np.mean(dT)),
        "mean_abs_diff_vs_synthetic_S_frac": float(np.mean(dS)),
        "result": (
            "PASS"
            if (n_bad == 0 and n_bad_ro == 0 and n_uncovered == 0 and n_low_conf == 0)
            else "WARN"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    ds = xr.Dataset(
        data_vars={
            "temperature_celsius": (("i", "j", "k"), t_out),
            "salinity_mass_fraction": (("i", "j", "k"), s_out),
            "density_anomaly_gcm3": (("i", "j", "k"), ro),
            "regrid_flag": (("i", "j", "k"), flag),
            "water_column_levels": (("i", "j"), kk1),
            "wet_mask": (("i", "j"), wet.astype(np.int8)),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
        },
        coords={
            "k": ("k", np.arange(ks) + 1),
            "z_model_m": ("k", Z_M),
            "i": np.arange(is1) + 1,
            "j": np.arange(js1) + 1,
        },
        attrs={
            "title": "Realistic initial ocean temperature/salinity (Stage 7.7)",
            "target_run_date": "2020-01-01",
            "source": str(args.raw),
            "source_product": "EN4.2.2 objective analysis (g10), 2020-01, "
            "Met Office Hadley Centre",
            "conversion": "T_degC = T_K - 273.15; S_frac = S_psu / 1000",
            "regridding": "horizontal NN over EN4 wet points (no cross-land); "
            "vertical piecewise-linear over finite EN4 samples; "
            "top model level = 0-10 m EN4 layer; deepest-finite "
            "below EN4 bottom; product-land column = 0",
            "regrid_flag_labels": "0=interp 1=shallowest-finite 2=deepest-finite "
            "3=product-land-column",
            "model_land_convention": "wet_mask==1; land cells contain 0 (never NaN)",
            "eos": "Eckart (src/equation_of_state.f90) float32; anomaly rho-1.02",
            "licence": "EN4: Non-Commercial Government Licence v2 (research)",
        },
    )
    ds.to_netcdf(args.out)
    print(f"wrote {args.out}")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"wrote {args.json}")

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
