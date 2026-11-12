#!/usr/bin/env python3
"""Stage 12.16: recompute the prism/voxel footprint after layer-resolved drag.

Two diagnostics are reported:
  1. drag side area: sum of voxel layer projected areas from phi versus the
     prism Method A side areas W*draft and L*draft;
  2. waterline footprint: voxel waterline cell area versus prism L*W.
The first is the area actually used by the new dynamics; the second is the
Stage 12.14 footprint diagnostic (unchanged by the drag change).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr

EPS = 1e-12


def layer_areas(phi, dx, dy, dz, draft):
    nz, ny, nx = phi.shape
    axp = axn = ayp = ayn = 0.0
    for k in range(nz):
        zc = (k + 0.5) * dz
        if zc >= draft:
            continue
        ph = phi[k]
        solid = ph > EPS
        if not solid.any():
            continue
        # i is the last (x) axis; j is the middle (y) axis.
        axp += float(np.sum(ph[:, :-1] * (~solid[:, 1:]))) * dy * dz
        axp += float(np.sum(ph[:, -1])) * dy * dz
        axn += float(np.sum(ph[:, 1:] * (~solid[:, :-1]))) * dy * dz
        axn += float(np.sum(ph[:, 0])) * dy * dz
        ayp += float(np.sum(ph[:-1, :] * (~solid[1:, :]))) * dx * dz
        ayp += float(np.sum(ph[-1, :])) * dx * dz
        ayn += float(np.sum(ph[1:, :] * (~solid[:-1, :]))) * dx * dz
        ayn += float(np.sum(ph[0, :])) * dx * dz
    return axp, axn, ayp, ayn


def waterline_area(phi, dx, dy, dz, draft):
    nz, ny, nx = phi.shape
    if nz == 0:
        return 0.0
    k = 0
    for k in range(nz):
        zc = (k + 0.5) * dz
        if zc >= draft:
            break
    ph = phi[min(k, nz - 1)]
    return float(np.count_nonzero(ph > EPS)) * dx * dy


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path)
    p.add_argument("voxel", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    with xr.open_dataset(a.run) as ds:
        i = -1
        volume = float(ds["prism_volume"].values[i])
        draft = float(ds["prism_draft"].values[i])
        freeboard = float(ds["prism_freeboard"].values[i])
        mass = float(ds["mass"].values[i])
    h = draft + freeboard
    lw = volume / h if h > 0 else np.nan
    prism_side_x = np.sqrt(lw) * draft
    prism_side_y = np.sqrt(lw) * draft
    prism_waterline = lw

    with xr.open_dataset(a.voxel) as ds:
        phi = np.asarray(ds["phi"].values[-1], float)
        vox_draft = float(ds["draft"].values[-1])
        dx = float(ds.attrs.get("voxel_dx_m", ds["x"].values[1] - ds["x"].values[0]))
        dy = float(ds.attrs.get("voxel_dy_m", ds["y"].values[1] - ds["y"].values[0]))
        dz = float(ds.attrs.get("voxel_dz_m", ds["z"].values[1] - ds["z"].values[0]))

    axp, axn, ayp, ayn = layer_areas(phi, dx, dy, dz, vox_draft)
    vox_side_x = max(axp, axn)
    vox_side_y = max(ayp, ayn)
    vox_waterline = waterline_area(phi, dx, dy, dz, vox_draft)

    def pct(v, ref):
        return 100.0 * (v - ref) / ref if ref else np.nan

    out = {
        "mass_kg": mass,
        "prism_draft_m": draft,
        "voxel_draft_m": vox_draft,
        "prism_side_x_m2": prism_side_x,
        "prism_side_y_m2": prism_side_y,
        "voxel_layer_x_pos_m2": axp,
        "voxel_layer_x_neg_m2": axn,
        "voxel_layer_y_pos_m2": ayp,
        "voxel_layer_y_neg_m2": ayn,
        "drag_side_x_diff_pct": pct(vox_side_x, prism_side_x),
        "drag_side_y_diff_pct": pct(vox_side_y, prism_side_y),
        "prism_waterline_m2": prism_waterline,
        "voxel_waterline_m2": vox_waterline,
        "waterline_diff_pct": pct(vox_waterline, prism_waterline),
    }
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
