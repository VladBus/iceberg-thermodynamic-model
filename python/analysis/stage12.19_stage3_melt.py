#!/usr/bin/env python3
"""Stage 12.19 Stage 3: stationary 100 m bulk-melt map, 30 d, winter/summer.

Uses the documented bulk basal-melt closure in python/validation/basal_melt.py
at the 92 m level (100 m cube draft 90 m) with U_ice=0.  It is a stationary
diagnostic, not a prognostic voxel run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd
import xarray as xr

from validation.basal_melt import basal_melt_rate_vectorized

DAYS = 30
DEPTH_M = 90.0


def season_mean(ds, k, sl):
    t = ds.thetao.isel(depth=k, time=sl).mean("time").values.astype(float)
    s = ds.so.isel(depth=k, time=sl).mean("time").values.astype(float)
    u = ds.uo.isel(depth=k, time=sl).mean("time").values.astype(float)
    v = ds.vo.isel(depth=k, time=sl).mean("time").values.astype(float)
    return t, s, u, v


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, default=Path("data/input/reanalysis/glorys"))
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--out-dir", type=Path, default=Path("data/validation/stage12.19/stage3_offline"))
    p.add_argument("--fig", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19/stage3_melt_stationary.png"))
    a = p.parse_args(); a.out_dir.mkdir(parents=True, exist_ok=True); a.fig.parent.mkdir(parents=True, exist_ok=True)
    with xr.open_dataset(a.static) as st:
        slat = st.latitude.values; slon = st.longitude.values
        depth = st.deptho.values; mask = st.mask.values[0] > 0
    fields = {}
    rows = []
    for year in (2020, 2024):
        ds = xr.open_dataset(a.base / str(year) / f"glorys12_barents_{year}_daily.nc")
        k = int(np.argmin(np.abs(ds.depth.values - DEPTH_M)))
        z = float(ds.depth.values[k])
        for name, sl in (("winter", slice(0, 30)), ("summer", slice(181, 211))):
            t, s, u, v = season_mean(ds, k, sl)
            m = basal_melt_rate_vectorized(t, s, np.full_like(t, z), u, v, length_m=100.0)
            m30 = m * 86400.0 * DAYS
            good = mask & (depth >= 100.0)
            m30 = np.where(good, m30, np.nan)
            fields[(year, name)] = (m30, t, s, np.hypot(u, v))
            q = np.nanpercentile(m30, [1, 5, 50, 95, 99])
            rows.append({"year": year, "season": name, "level_m": z,
                         "p01": q[0], "p05": q[1], "median": q[2], "p95": q[3], "p99": q[4],
                         "mean": float(np.nanmean(m30)), "max": float(np.nanmax(m30))})
        ds.close()
    tab = pd.DataFrame(rows); tab.to_csv(a.out_dir / "melt_seasonal.csv", index=False)
    vmax = float(np.nanpercentile([np.nanpercentile(fields[k][0], 99) for k in fields], 99))
    norm = Normalize(0, max(vmax, 1e-3))
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True, sharey=True)
    im = None
    for i, year in enumerate((2020, 2024)):
        for j, name in enumerate(("winter", "summer")):
            ax = axes[i, j]
            m30 = fields[(year, name)][0]
            im = ax.pcolormesh(slon, slat, np.ma.masked_invalid(m30), shading="auto",
                               cmap="YlOrRd", norm=norm)
            ax.set_title(f"{year} {name}: 30 d bulk basal melt")
            ax.set_aspect(1 / np.cos(np.deg2rad(78)))
            if j == 0: ax.set_ylabel("latitude")
            if i == 1: ax.set_xlabel("longitude")
    fig.colorbar(im, ax=axes, label="melt over 30 d [m]", shrink=.8)
    fig.suptitle("Stationary 100 m cube, bulk basal melt: winter (Jan) and summer (Jul)")
    fig.savefig(a.fig, dpi=200, bbox_inches="tight"); plt.close(fig)
    print(tab.to_string(index=False)); print(a.fig)


if __name__ == "__main__":
    main()
