#!/usr/bin/env python3
"""Stage 12.15: drift/melt maps from existing 100^3 annual run.nc files.

Reads only the small time-series NetCDF (not the 218 MB voxel snapshot).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import xarray as xr

R = 6371000.0
RHO_A, CD_A = 1.225, 1.5
RHO_W, CD_W = 1025.0, 1.0


def daily(ds):
    t = ds.time.values / 86400.0
    n = int(np.floor(t[-1]))
    rows = []
    for d in range(n + 1):
        m = (t >= d) & (t < d + 1)
        if not m.any():
            continue
        k = np.where(m)[0]
        rec = {"day": d, "lat": float(ds.latitude.values[k[-1]]),
               "lon": float(ds.longitude.values[k[-1]])}
        for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"):
            rec[v] = float(ds[v].values[k].sum()) if v in ds else 0.0
        rec["mass_loss_total"] = sum(rec[v] for v in
            ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"))
        rec["current_speed"] = float(np.hypot(ds.ocean_u_draft.values[k], ds.ocean_v_draft.values[k]).mean()) if "ocean_u_draft" in ds else np.nan
        rec["wind_speed"] = float(np.hypot(ds.air_u10.values[k], ds.air_v10.values[k]).mean()) if "air_u10" in ds else np.nan
        rec["a_wet"] = float(ds.a_wet.values[k].mean()) if "a_wet" in ds else np.nan
        rows.append(rec)
    return rows


def metrics(rows):
    lat = np.array([r["lat"] for r in rows]); lon = np.array([r["lon"] for r in rows])
    seg = np.hypot(np.deg2rad(np.diff(lat)) * R,
                   np.deg2rad(np.diff(lon)) * R * np.cos(np.deg2rad((lat[1:] + lat[:-1]) / 2)))
    net = np.hypot(np.deg2rad(lat[-1] - lat[0]) * R,
                   np.deg2rad(lon[-1] - lon[0]) * R * np.cos(np.deg2rad((lat[-1] + lat[0]) / 2)))
    f_w = np.array([RHO_A * CD_A * r["a_wet"] * r["wind_speed"]**2 for r in rows])
    f_o = np.array([RHO_W * CD_W * r["a_wet"] * r["current_speed"]**2 for r in rows])
    return {"path_km": float(seg.sum() / 1000), "net_km": float(net / 1000),
            "mean_drift_m_s": float(seg.sum() / (len(rows) * 86400.0)),
            "wind_force_proxy_sum": float(np.nansum(f_w)), "ocean_force_proxy_sum": float(np.nansum(f_o)),
            "force_note": "proxy using a_wet for both areas; exact force diagnostics were not stored"}


def plot_track(rows, depth, lat, lon, out, year):
    fig, ax = plt.subplots(figsize=(8, 7))
    z = np.ma.masked_invalid(depth)
    pm = ax.pcolormesh(lon, lat, z, shading="auto", cmap="Blues_r", alpha=.65)
    ax.contour(lon, lat, np.nan_to_num(depth, nan=-1), levels=[0.5], colors="k", linewidths=.5)
    fig.colorbar(pm, ax=ax, label="depth [m]", shrink=.8)
    sc = ax.scatter([r["lon"] for r in rows], [r["lat"] for r in rows],
                    c=[r["day"] for r in rows], cmap="viridis", s=12, zorder=3)
    ax.plot([r["lon"] for r in rows], [r["lat"] for r in rows], "k-", lw=.5, alpha=.5)
    ax.scatter(rows[0]["lon"], rows[0]["lat"], marker="*", s=140, c="red", label="start", zorder=4)
    ax.scatter(rows[-1]["lon"], rows[-1]["lat"], marker="X", s=80, c="black", label="end", zorder=4)
    fig.colorbar(sc, ax=ax, label="day of year", shrink=.8)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_title(f"{year} 100^3 drift trajectory")
    ax.legend(loc="lower left"); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def plot_loss(rows, depth, lat, lon, out, year):
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, key, title in zip(axes.ravel(),
        ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_total"),
        ("basal", "lateral", "surface", "total")):
        ax.pcolormesh(lon, lat, np.ma.masked_invalid(depth), shading="auto", cmap="Greys", alpha=.35)
        vals = np.maximum(np.array([r[key] for r in rows]), 1e-6)
        sc = ax.scatter([r["lon"] for r in rows], [r["lat"] for r in rows], c=vals,
                        cmap="YlOrRd", norm=LogNorm(vmin=max(vals.min(), 1e-3), vmax=vals.max()), s=14)
        fig.colorbar(sc, ax=ax, label="kg day-1", shrink=.8)
        ax.set_title(f"{year} {title}"); ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
        ax.set_aspect(1 / np.cos(np.deg2rad(78)))
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def main():
    p = argparse.ArgumentParser(); p.add_argument("--run", type=Path, required=True)
    p.add_argument("--year", type=int, required=True); p.add_argument("--outdir", type=Path, required=True)
    a = p.parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    ds = xr.open_dataset(a.run); rows = daily(ds); ds.close()
    st = xr.open_dataset("data/input/static/glorys_static_barents.nc")
    depth = np.asarray(st.deptho.values); lat = np.asarray(st.latitude.values); lon = np.asarray(st.longitude.values)
    st.close()
    plot_track(rows, depth, lat, lon, a.outdir / f"drift_track_{a.year}.png", a.year)
    plot_loss(rows, depth, lat, lon, a.outdir / f"melt_components_{a.year}.png", a.year)
    meta = {"year": a.year, **metrics(rows), "daily": rows}
    (a.outdir / f"summary_{a.year}.json").write_text(json.dumps(meta, indent=2) + "\n")
    with open(a.outdir / f"daily_{a.year}.csv", "w") as f:
        keys = list(rows[0])
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(str(r[k]) for k in keys) + "\n")
    print(json.dumps({k: meta[k] for k in ("path_km","net_km","mean_drift_m_s","wind_force_proxy_sum","ocean_force_proxy_sum")}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
