#!/usr/bin/env python3
"""Stage 12.16: ensemble of 12 Barents 2024 starts (50^3).

Reads the per-start run.nc time series, derives annual mass loss, t90 (time to
10% remaining mass), path/net drift and daily melt rate, then writes a CSV and
two maps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd
import xarray as xr

R_EARTH = 6371000.0
RHO_ICE = 916.7


def daily_series(ds):
    t = np.asarray(ds.time.values, float)
    n = int(np.floor(t[-1] / 86400.0))
    rows = []
    for d in range(n + 1):
        m = (t >= d * 86400.0) & (t < (d + 1) * 86400.0)
        if not m.any():
            continue
        k = np.where(m)[0]
        rec = {
            "day": d,
            "lat": float(ds.latitude.values[k[-1]]),
            "lon": float(ds.longitude.values[k[-1]]),
            "mass": float(ds.mass.values[k[-1]]),
            "a_wet": float(np.nanmean(ds.a_wet.values[k])),
        }
        for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"):
            rec[v] = float(np.nansum(ds[v].values[k])) if v in ds else 0.0
        rec["mass_loss_total"] = sum(
            rec[v] for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor")
        )
        dt_day = 86400.0
        rec["melt_rate_m_day"] = (
            rec["mass_loss_total"] / (RHO_ICE * rec["a_wet"] * dt_day)
            if rec["a_wet"] > 0 else np.nan
        )
        rows.append(rec)
    return rows


def path_km(lat, lon):
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    seg = np.hypot(np.deg2rad(np.diff(lat)) * R_EARTH,
                   np.deg2rad(np.diff(lon)) * R_EARTH * np.cos(np.deg2rad((lat[1:] + lat[:-1]) / 2)))
    net = np.hypot(np.deg2rad(lat[-1] - lat[0]) * R_EARTH,
                   np.deg2rad(lon[-1] - lon[0]) * R_EARTH * np.cos(np.deg2rad((lat[-1] + lat[0]) / 2)))
    return float(seg.sum() / 1000), float(net / 1000)


def t90_days(days, mass, m0, fraction=0.1):
    days = np.asarray(days, float); mass = np.asarray(mass, float)
    target = fraction * m0
    for i in range(1, len(mass)):
        if mass[i] <= target:
            if mass[i - 1] == mass[i]:
                return float(days[i])
            w = (mass[i - 1] - target) / (mass[i - 1] - mass[i])
            return float(days[i - 1] + w * (days[i] - days[i - 1]))
    return np.nan


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path,
                   default=Path("data/validation/stage12.16/ensemble_2024_50cube"))
    p.add_argument("--static", type=Path,
                   default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--out-dir", type=Path,
                   default=Path("data/validation/stage12.16"))
    p.add_argument("--fig-dir", type=Path,
                   default=Path("docs/wiki/stages/stage12/figures/stage12.16"))
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.fig_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    tracks = {}
    for d in sorted(a.root.glob("P*")):
        f = d / "run.nc"
        if not f.exists():
            continue
        with xr.open_dataset(f) as ds:
            days = daily_series(ds)
            src = ds.attrs.get("source", "")
        if not days:
            continue
        m0 = days[0]["mass"]
        mf = days[-1]["mass"]
        lat = np.array([r["lat"] for r in days]); lon = np.array([r["lon"] for r in days])
        path, net = path_km(lat, lon)
        t90 = t90_days([r["day"] for r in days], [r["mass"] for r in days], m0)
        t10 = t90_days([r["day"] for r in days], [r["mass"] for r in days], m0, fraction=0.9)
        logtxt = (d / "run.log").read_text(errors="ignore")
        grounded = "STOP: iceberg grounded" in logtxt
        strict_stop = "STOP: primary ocean profile unavailable" in logtxt
        ndays = float(days[-1]["day"] + 1)
        rec = {
            "point": d.name,
            "lat0": float(lat[0]), "lon0": float(lon[0]),
            "lat_final": float(lat[-1]), "lon_final": float(lon[-1]),
            "days": ndays,
            "complete_year": bool(ndays >= 365.0),
            "strict_ocean_stop": bool(strict_stop),
            "mass_initial_kg": float(m0), "mass_final_kg": float(mf),
            "mass_loss_pct": float(100.0 * (m0 - mf) / m0),
            "t90_days": t90,
            "t10_days": t10,
            "path_km": path, "net_km": net,
            "mean_speed_m_s": float(path * 1000.0 / (days[-1]["day"] * 86400.0)) if days[-1]["day"] > 0 else np.nan,
            "grounded": bool(grounded),
        }
        rows.append(rec)
        tracks[d.name] = days

    table = pd.DataFrame(rows).sort_values("point")
    table.to_csv(a.out_dir / "ensemble_2024_50cube.csv", index=False)
    (a.out_dir / "ensemble_2024_50cube.json").write_text(json.dumps(rows, indent=2) + "\n")

    st = xr.open_dataset(a.static)
    dep = np.asarray(st.deptho.values); glat = np.asarray(st.latitude.values); glon = np.asarray(st.longitude.values)
    st.close()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    for ax, key, title, cmap in [
        (axes[0], "mass_loss_pct", "annual mass loss [%]", "YlOrRd"),
        (axes[1], "t90_days", "time to 10% remaining mass [days]", "viridis"),
    ]:
        ax.pcolormesh(glon, glat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.5)
        vals = table[key].to_numpy(float)
        good = np.isfinite(vals)
        sc = None
        if good.any():
            sc = ax.scatter(table.loc[good, "lon0"], table.loc[good, "lat0"], c=vals[good],
                            cmap=cmap, s=90, edgecolor="k", zorder=3)
            partial = good & (~table["complete_year"].to_numpy(bool))
            if partial.any():
                ax.scatter(table.loc[partial, "lon0"], table.loc[partial, "lat0"],
                           c=vals[partial], cmap=cmap, s=110, marker="X",
                           edgecolor="k", zorder=5, label="stopped before 365 d")
        for _, r in table.iterrows():
            ax.annotate(r["point"], (r["lon0"], r["lat0"]), xytext=(4, 4),
                        textcoords="offset points", fontsize=8, zorder=4)
        if (~good).any():
            ax.scatter(table.loc[~good, "lon0"], table.loc[~good, "lat0"], marker="x",
                       c="grey", s=80, zorder=4, label="not reached")
            ax.legend(loc="lower left", fontsize=8)
        if sc is not None:
            fig.colorbar(sc, ax=ax, label=title, shrink=.8)
        ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
        ax.set_title(title + " (X = stopped before 365 d)")
        ax.set_aspect(1 / np.cos(np.deg2rad(79)))
    fig.tight_layout()
    fig.savefig(a.fig_dir / "ensemble_2024_50cube_summary.png", dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.pcolormesh(glon, glat, np.ma.masked_invalid(dep), shading="auto", cmap="Greys", alpha=.4)
    all_rates = np.concatenate([[r["melt_rate_m_day"] for r in tr] for tr in tracks.values()])
    vmax = float(np.nanmax(all_rates)) if np.isfinite(all_rates).any() else 1.0
    if not np.isfinite(vmax) or vmax <= 0.0:
        vmax = 1.0
    vmin = max(1e-9, vmax * 1e-3)
    sc = None
    for name, tr in tracks.items():
        lat = [r["lat"] for r in tr]; lon = [r["lon"] for r in tr]
        vals = np.maximum([r["melt_rate_m_day"] for r in tr], vmin)
        ax.plot(lon, lat, color="k", lw=.5, alpha=.5)
        sc = ax.scatter(lon, lat, c=vals, cmap="YlOrRd", norm=LogNorm(vmin=vmin, vmax=vmax), s=6, zorder=3)
        ax.scatter(lon[0], lat[0], marker="^", c="C0", s=50, zorder=4)
    if sc is not None:
        fig.colorbar(sc, ax=ax, label="daily melt rate [m/day]", shrink=.8)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title("2024 50^3 ensemble: melt rate along tracks")
    ax.set_aspect(1 / np.cos(np.deg2rad(79)))
    fig.tight_layout()
    fig.savefig(a.fig_dir / "ensemble_2024_50cube_tracks.png", dpi=170)
    plt.close(fig)

    print(table.to_string(index=False))
    print(f"wrote {a.out_dir} and {a.fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
