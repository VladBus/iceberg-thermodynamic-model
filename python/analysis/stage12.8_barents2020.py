#!/usr/bin/env python3
"""Stage 12.8 Barents 2020 matrix analysis and figures.

Reads data/runs/barents2020/*.nc (24 voxel runs) and produces:
  docs/validation/figures/barents2020/drift_map_Jan.png
  docs/validation/figures/barents2020/drift_map_Jul.png
  docs/validation/figures/barents2020/volume_Jan.png
  docs/validation/figures/barents2020/volume_Jul.png
  docs/validation/figures/barents2020/melt_budget_Jan.png
  docs/validation/figures/barents2020/melt_budget_Jul.png
  docs/validation/figures/barents2020/lifetime_heatmap.png
  docs/validation/stage12.8_results.csv
  docs/validation/stage12.8_summary.json
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

RUNS = Path("data/runs/barents2020")
FIGS = Path("docs/validation/figures/barents2020")
SIZES = [50, 100, 200, 500]
SEASONS = ["Jan", "Jul"]
POINTS = [1, 2, 3]
R_EARTH = 6371.0


def gc_km(lat1, lon1, lat2, lon2):
    p1 = np.deg2rad(lat1); p2 = np.deg2rad(lat2)
    dp = p2 - p1; dl = np.deg2rad(lon2 - lon1)
    a = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2.0*R_EARTH*np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def thresholds(days, vol, v0):
    frac = vol/v0
    out = {}
    for q, name in ((0.5, "t50"), (0.1, "t90")):
        idx = np.where(frac <= q)[0]
        if len(idx) == 0:
            out[name] = np.nan
        else:
            k = idx[0]
            if k == 0:
                out[name] = days[0]
            else:
                f0, f1 = frac[k-1], frac[k]
                w = (q - f0)/(f1 - f0) if f1 != f0 else 0.0
                out[name] = days[k-1] + w*(days[k] - days[k-1])
    return out


def load_runs():
    data = {}
    for size in SIZES:
        for season in SEASONS:
            for p in POINTS:
                rid = f"S{size}_{season}_P{p}"
                f = RUNS / f"{rid}.nc"
                if not f.exists():
                    continue
                ds = xr.open_dataset(f)
                data[rid] = ds
    return data


def plot_maps(data):
    grid = xr.open_dataset("data/input/processed/grid/grid.nc")
    glat = grid.lat.values; glon = grid.lon.values
    depth = grid.kt1_raw.values.astype(float)
    sic = xr.open_dataset("data/input/raw/reanalysis/glorys12/2020/"
                          "glorys12_barents_2020_2021_monthly.nc",
                          decode_times=False, mask_and_scale=True)
    for season, it in (("Jan", 0), ("Jul", 6)):
        fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
        for ax in axes:
            z = np.ma.masked_where((depth >= 600) | (depth == 8), depth)
            ax.contourf(glon, glat, z, levels=np.linspace(0, 600, 13),
                        cmap="Blues_r", alpha=0.55)
            ax.contour(glon, glat, z, levels=[150, 300, 450],
                       colors="0.4", linewidths=0.5)
            ax.contour(sic.longitude.values, sic.latitude.values,
                       sic.siconc.isel(time=it).values, levels=[0.15],
                       colors="k", linestyles=":", linewidths=1.0)
            ax.set_xlim(5, 85); ax.set_ylim(65, 86)
            ax.set_xlabel("Longitude, °E"); ax.set_ylabel("Latitude, °N")
            ax.set_title(f"{season}: " + ("trajectory colored by day" if ax is axes[0]
                                         else "trajectory colored by speed"))
            ax.grid(alpha=0.2)
        sm_day = plt.cm.ScalarMappable(norm=plt.Normalize(0, 365), cmap="viridis")
        speeds = []
        for size in SIZES:
            for p in POINTS:
                rid = f"S{size}_{season}_P{p}"
                if rid not in data:
                    continue
                ds = data[rid]
                lat = ds.latitude.values; lon = ds.longitude.values
                t = ds.time.values/86400.0
                sp = np.zeros_like(t)
                if len(t) > 1:
                    d = gc_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
                    dt = np.diff(t)*86400.0
                    sp[1:] = d*1000.0/np.maximum(dt, 1.0)
                speeds.append(np.nanmax(sp))
                axes[0].scatter(lon, lat, c=t, cmap="viridis", s=3, alpha=0.85)
                axes[0].plot(lon[0], lat[0], "^", color="k", ms=5)
                axes[0].plot(lon[-1], lat[-1], "x", color="k", ms=5)
        vmax = max(speeds) if speeds else 0.1
        sm_sp = plt.cm.ScalarMappable(norm=plt.Normalize(0, max(vmax, 0.02)), cmap="plasma")
        for size in SIZES:
            for p in POINTS:
                rid = f"S{size}_{season}_P{p}"
                if rid not in data:
                    continue
                ds = data[rid]
                lat = ds.latitude.values; lon = ds.longitude.values
                t = ds.time.values/86400.0
                sp = np.zeros_like(t)
                if len(t) > 1:
                    d = gc_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
                    dt = np.diff(t)*86400.0
                    sp[1:] = d*1000.0/np.maximum(dt, 1.0)
                axes[1].scatter(lon, lat, c=sp, cmap="plasma", vmin=0, vmax=max(vmax, 0.02),
                                s=3, alpha=0.85)
                axes[1].plot(lon[0], lat[0], "^", color="k", ms=5)
                axes[1].plot(lon[-1], lat[-1], "x", color="k", ms=5)
        fig.colorbar(sm_day, ax=axes[0], label="day")
        fig.colorbar(sm_sp, ax=axes[1], label="speed, m/s")
        fig.tight_layout()
        fig.savefig(FIGS / f"drift_map_{season}.png", dpi=160)
        plt.close(fig)


def plot_volume(data):
    for season in SEASONS:
        fig, axes = plt.subplots(1, 4, figsize=(18, 4.2), sharey=True)
        for ax, size in zip(axes, SIZES):
            for p in POINTS:
                rid = f"S{size}_{season}_P{p}"
                if rid not in data:
                    continue
                ds = data[rid]
                t = ds.time.values/86400.0
                v0 = float(ds.volume.values[0])
                frac = ds.volume.values/v0
                ax.plot(t, frac, lw=1.4, label=f"P{p}")
                th = thresholds(t, ds.volume.values, v0)
                if np.isfinite(th["t50"]):
                    ax.axvline(th["t50"], color="0.7", ls=":", lw=0.6)
                if np.isfinite(th["t90"]):
                    ax.axvline(th["t90"], color="0.4", ls="--", lw=0.6)
            ax.axhline(0.5, color="0.7", ls=":", lw=0.6)
            ax.axhline(0.1, color="0.4", ls="--", lw=0.6)
            ax.set_title(f"S{size}"); ax.set_xlabel("days")
            ax.set_ylim(0, 1.02); ax.grid(alpha=0.2)
        axes[0].set_ylabel("V(t)/V0")
        axes[0].legend(fontsize=8)
        fig.suptitle(f"{season} 2020 — volume evolution")
        fig.tight_layout()
        fig.savefig(FIGS / f"volume_{season}.png", dpi=160)
        plt.close(fig)


def plot_budget(data):
    for season in SEASONS:
        fig, axes = plt.subplots(1, 3, figsize=(16, 4.2), sharey=True)
        for ax, p in zip(axes, POINTS):
            rid = f"S100_{season}_P{p}"
            if rid not in data:
                continue
            ds = data[rid]
            t = ds.time.values/86400.0
            comp = {}
            for name, var in (("basal", "mass_loss_basal"),
                              ("lateral", "mass_loss_lateral"),
                              ("surface", "mass_loss_surface"),
                              ("wave", "mass_loss_wave")):
                comp[name] = np.cumsum(ds[var].values)/1e9  # Gg
            ax.stackplot(t, comp["basal"], comp["lateral"], comp["surface"], comp["wave"],
                         labels=["basal", "lateral", "surface", "wave"],
                         colors=["tab:blue", "tab:cyan", "tab:orange", "tab:purple"],
                         alpha=0.85)
            ax.set_title(f"S100 {season} P{p}"); ax.set_xlabel("days")
            ax.grid(alpha=0.2)
        axes[0].set_ylabel("cumulative mass loss, Gg")
        axes[0].legend(fontsize=8)
        fig.suptitle(f"{season} 2020 — S100 melt budget")
        fig.tight_layout()
        fig.savefig(FIGS / f"melt_budget_{season}.png", dpi=160)
        plt.close(fig)


def plot_lifetime(data, summary):
    for q in ("t90",):
        arr = np.full((len(SIZES), len(SEASONS)), np.nan)
        for i, size in enumerate(SIZES):
            for j, season in enumerate(SEASONS):
                vals = []
                for p in POINTS:
                    rid = f"S{size}_{season}_P{p}"
                    if rid in data:
                        v = summary[rid][q]
                        vals.append(365.0 if not np.isfinite(v) else v)
                if vals:
                    arr[i, j] = np.mean(vals)
        fig, ax = plt.subplots(figsize=(6, 4.2))
        im = ax.imshow(arr, cmap="YlOrRd", origin="lower", aspect="auto",
                       vmin=0, vmax=365)
        ax.set_xticks(range(len(SEASONS))); ax.set_xticklabels(SEASONS)
        ax.set_yticks(range(len(SIZES))); ax.set_yticklabels([f"S{s}" for s in SIZES])
        for i in range(len(SIZES)):
            for j in range(len(SEASONS)):
                if np.isfinite(arr[i, j]):
                    ax.text(j, i, f"{arr[i,j]:.0f}", ha="center", va="center", fontsize=10)
        fig.colorbar(im, ax=ax, label="time to 90% melt, days (365 = not reached)")
        ax.set_title("Barents 2020: t90 heatmap (mean of 3 points)")
        fig.tight_layout()
        fig.savefig(FIGS / "lifetime_heatmap.png", dpi=160)
        plt.close(fig)


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    data = load_runs()
    if not data:
        print("no runs found")
        return 2
    summary = {}
    rows = []
    for rid, ds in data.items():
        t = ds.time.values/86400.0
        v0 = float(ds.volume.values[0])
        v = ds.volume.values
        lat = ds.latitude.values; lon = ds.longitude.values
        th = thresholds(t, v, v0)
        bl = float(np.sum(ds.mass_loss_basal.values))
        ll = float(np.sum(ds.mass_loss_lateral.values))
        sl = float(np.sum(ds.mass_loss_surface.values))
        wl = float(np.sum(ds.mass_loss_wave.values))
        sub = bl + ll + wl
        summary[rid] = {
            "drift_km": float(gc_km(lat[0], lon[0], lat[-1], lon[-1])),
            "path_km": float(np.sum(gc_km(lat[:-1], lon[:-1], lat[1:], lon[1:]))),
            "final_fraction": float(v[-1]/v0),
            "t50": th["t50"], "t90": th["t90"],
            "basal_fraction": bl/sub if sub > 0 else np.nan,
            "lateral_fraction": ll/sub if sub > 0 else np.nan,
            "surface_fraction": sl/sub if sub > 0 else np.nan,
            "wave_fraction": wl/sub if sub > 0 else np.nan,
        }
        parts = rid.split("_")
        rows.append({"run_id": rid, "size_m": int(parts[0][1:]),
                     "season": parts[1], "point": int(parts[2][1:]), **summary[rid]})
    pd.DataFrame(rows).to_csv("docs/validation/stage12.8_results.csv", index=False)
    Path("docs/validation/stage12.8_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    plot_maps(data)
    plot_volume(data)
    plot_budget(data)
    plot_lifetime(data, summary)
    print(f"wrote 7 figures to {FIGS}")
    print(pd.DataFrame(rows).groupby(["season", "size_m"]).agg(
        n=("run_id", "size"), drift_km=("drift_km", "mean"),
        final_fraction=("final_fraction", "mean"),
        t90=("t90", "mean"), lateral=("lateral_fraction", "mean")).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
