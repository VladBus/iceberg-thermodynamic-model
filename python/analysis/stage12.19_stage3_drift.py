#!/usr/bin/env python3
"""Stage 12.19 Stage 3: offline drift-only diagnostic for 100 m icebergs.

This is deliberately *not* a thermodynamic model run.  It integrates 20
starts per source region with a documented diagnostic velocity

    U_ice = 0.855 * U_GLORYS(0.5 m) + 0.0145 * U_ERA5(10 m)

using 6-hour steps, 2020/2024 daily forcing, depth >= 200 m and >= 8 grid
cells from land.  Stops at land, shallow water (< 90 m draft), or the domain
boundary.  The factors are the Stage 12.17 100 m-cube values; no Coriolis,
thermodynamics, waves, or sea ice are included.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt

R_EARTH = 6371000.0
DRAFT_M = 90.0
ALPHA_C = 0.855
ALPHA_W = 0.0145
SOURCES = {"FJL": (81.0, 55.0), "NZ": (76.0, 57.5), "SV": (76.5, 20.5)}


def select_seeds(static: Path, n=20, radius=1.5):
    with xr.open_dataset(static) as st:
        lat = st.latitude.values.astype(float)
        lon = st.longitude.values.astype(float)
        depth = st.deptho.values.astype(float)
        mask = st.mask.values[0] > 0
    dist = distance_transform_edt(mask)
    rows = []
    for name, (la, lo) in SOURCES.items():
        ii, jj = np.meshgrid(np.arange(lon.size), np.arange(lat.size))
        valid = mask & (depth >= 200.0) & (dist >= 8.0)
        valid &= (np.abs(lat[:, None] - la) <= radius) & (np.abs(lon[None, :] - lo) <= radius)
        cand = np.argwhere(valid)
        if len(cand) < n:
            raise SystemExit(f"{name}: only {len(cand)} seeds within {radius} deg")
        # deterministic farthest-point sampling in local degree space
        d2 = ((lat[cand[:, 0]] - la) * np.cos(np.deg2rad(la))) ** 2 + (lon[cand[:, 1]] - lo) ** 2
        chosen = [int(np.argmin(d2))]
        while len(chosen) < n:
            best = None
            for k in range(len(cand)):
                if k in chosen:
                    continue
                dmin = min((lat[cand[k, 0]] - lat[cand[j, 0]]) ** 2 +
                           ((lon[cand[k, 1]] - lon[cand[j, 1]]) * np.cos(np.deg2rad(la))) ** 2
                           for j in chosen)
                if best is None or dmin > best[1]:
                    best = (k, dmin)
            chosen.append(best[0])
        for k in chosen:
            j, i = cand[k]
            rows.append({"source": name, "lat0": float(lat[j]), "lon0": float(lon[i]),
                         "depth_m": float(depth[j, i])})
    return pd.DataFrame(rows), lat, lon, depth, mask


def load_year(year: int, base: Path):
    g = base / f"glorys/{year}/glorys12_barents_{year}_daily.nc"
    e = base / f"era5/{year}/era5_{year}_daily.nc"
    with xr.open_dataset(g) as ds:
        u = ds.uo.isel(depth=0).values.astype(np.float32)
        v = ds.vo.isel(depth=0).values.astype(np.float32)
        lat = ds.latitude.values.astype(float)
        lon = ds.longitude.values.astype(float)
    with xr.open_dataset(e) as ds:
        uw = ds.u10.values.astype(np.float32)
        vw = ds.v10.values.astype(np.float32)
        elat = ds.latitude.values.astype(float)[::-1]
        elon = ds.longitude.values.astype(float)
        uw = uw[:, ::-1, :]; vw = vw[:, ::-1, :]
    return (np.nan_to_num(u), np.nan_to_num(v), lat, lon,
            np.nan_to_num(uw), np.nan_to_num(vw), elat, elon)


def integrate(year: int, base: Path, seeds: pd.DataFrame, static_lat, static_lon, depth, mask):
    u, v, lat, lon, uw, vw, elat, elon = load_year(year, base)
    nsteps = 365 * 4
    dt = 6.0 * 3600.0
    active = np.ones(len(seeds), bool)
    x = seeds.lon0.to_numpy(float).copy(); y = seeds.lat0.to_numpy(float).copy()
    days = np.zeros(len(seeds)); path = np.zeros(len(seeds)); reason = np.array(["365 d"] * len(seeds), dtype=object)
    tracks = [[(float(xx), float(yy))] for xx, yy in zip(x, y)]
    for k in range(nsteps):
        td = min(k // 4, u.shape[0] - 1)
        if k % 4 == 0:
            iu = RegularGridInterpolator((lat, lon), u[td], bounds_error=False, fill_value=np.nan)
            iv = RegularGridInterpolator((lat, lon), v[td], bounds_error=False, fill_value=np.nan)
            iau = RegularGridInterpolator((elat, elon), uw[td], bounds_error=False, fill_value=np.nan)
            iav = RegularGridInterpolator((elat, elon), vw[td], bounds_error=False, fill_value=np.nan)
        idx = np.where(active)[0]
        if not len(idx):
            break
        pts = np.column_stack([y[idx], x[idx]])
        uc = iu(pts); vc = iv(pts); ua = iau(pts); va = iav(pts)
        bad = ~np.isfinite(uc) | ~np.isfinite(vc) | ~np.isfinite(ua) | ~np.isfinite(va)
        if bad.any():
            active[idx[bad]] = False; reason[idx[bad]] = "forcing gap"
        good = idx[~bad]
        if not len(good):
            break
        ui = ALPHA_C * uc[~bad] + ALPHA_W * ua[~bad]
        vi = ALPHA_C * vc[~bad] + ALPHA_W * va[~bad]
        xn = x[good] + ui * dt / (R_EARTH * np.cos(np.deg2rad(y[good]))) * 180.0 / np.pi
        yn = y[good] + vi * dt / R_EARTH * 180.0 / np.pi
        outside = (xn < lon[0]) | (xn > lon[-1]) | (yn < lat[0]) | (yn > lat[-1])
        # nearest static depth and land check
        jj = np.clip(np.rint((yn - static_lat[0]) / (static_lat[1] - static_lat[0])).astype(int), 0, len(static_lat) - 1)
        ii = np.clip(np.rint((xn - static_lon[0]) / (static_lon[1] - static_lon[0])).astype(int), 0, len(static_lon) - 1)
        shallow = (~outside) & ((~mask[jj, ii]) | (depth[jj, ii] < DRAFT_M))
        stop = outside | shallow
        seg = np.hypot(np.deg2rad(yn - y[good]) * R_EARTH,
                       np.deg2rad(xn - x[good]) * R_EARTH * np.cos(np.deg2rad((yn + y[good]) / 2.0)))
        path[good] += seg
        days[good] += 0.25
        # keep last valid position for stopped points; paths still counted to boundary
        for j, gg in enumerate(good):
            if not stop[j]:
                x[gg] = xn[j]; y[gg] = yn[j]; tracks[gg].append((float(xn[j]), float(yn[j])))
            else:
                reason[gg] = "boundary" if outside[j] else "grounding/land"
        active[good] = ~stop
        if not active.any():
            break
    rows = []
    for i, r in seeds.iterrows():
        rows.append({**r.to_dict(), "year": year, "days": float(days[i]),
                     "path_km": float(path[i] / 1000.0),
                     "net_km": float(np.hypot((x[i] - r.lon0) * np.cos(np.deg2rad(r.lat0)), y[i] - r.lat0) * 111.0),
                     "mean_speed_m_s": float(path[i] / max(days[i] * 86400.0, 1.0)),
                     "stop": str(reason[i]), "lon_final": float(x[i]), "lat_final": float(y[i])})
    return pd.DataFrame(rows), tracks


def plot_map(df, tracks, out, depth, lat, lon):
    colors = {"FJL": "C0", "NZ": "C1", "SV": "C2"}
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), sharey=True)
    for ax, year in zip(axes, (2020, 2024)):
        z = np.ma.masked_invalid(depth)
        ax.pcolormesh(lon, lat, z, shading="auto", cmap="Blues_r", alpha=.55)
        subset = df[df.year == year].reset_index(drop=True)
        for i, r in subset.iterrows():
            tr = np.asarray(tracks[year][i])
            ax.plot(tr[:, 0], tr[:, 1], color=colors[r.source], lw=.65, alpha=.75)
            ax.scatter(tr[0, 0], tr[0, 1], marker="o", s=11, color=colors[r.source], edgecolor="k", lw=.2)
            ax.scatter(tr[-1, 0], tr[-1, 1], marker="X", s=18, color=colors[r.source], edgecolor="k", lw=.2)
        ax.set_xlim(5, 80); ax.set_ylim(63, 86); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
        ax.set_xlabel("longitude"); ax.set_title(f"{year}: 100 m drift-only, 365 d")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("latitude")
    handles = [Line2D([0], [0], color=c, label=k) for k, c in colors.items()]
    axes[1].legend(handles=handles, loc="lower left", fontsize=8, title="source")
    fig.tight_layout(); fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, default=Path("data/input/reanalysis"))
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--out-dir", type=Path, default=Path("data/validation/stage12.19/stage3_offline"))
    p.add_argument("--fig-dir", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19"))
    a = p.parse_args(); a.out_dir.mkdir(parents=True, exist_ok=True); a.fig_dir.mkdir(parents=True, exist_ok=True)
    seeds, lat, lon, depth, mask = select_seeds(a.static)
    seeds.to_csv(a.out_dir / "starts.csv", index=False)
    allrows = {}; alltracks = {}
    for year in (2020, 2024):
        df, tr = integrate(year, a.base, seeds, lat, lon, depth, mask)
        allrows[year] = df; alltracks[year] = tr
        df.to_csv(a.out_dir / f"drift_{year}.csv", index=False)
        print(f"{year}: {len(df)} trajectories, mean path {df.path_km.mean():.1f} km, mean speed {df.mean_speed_m_s.mean():.4f} m/s")
    both = pd.concat(allrows.values(), ignore_index=True)
    both.to_csv(a.out_dir / "drift_all.csv", index=False)
    plot_map(both, alltracks, a.fig_dir / "stage3_drift_map.png", depth, lat, lon)
    print(a.out_dir)


if __name__ == "__main__":
    main()
