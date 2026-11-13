#!/usr/bin/env python3
"""Stage 12.17 final-run figures.

Per run: track/day map, track/melt-rate map, time series, 3D snapshots,
phi/T GIFs and a track GIF. Summary: 6-run mass-loss/t50 map and a validation
panel (convergence, Enderlin, energy closure).
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
from PIL import Image

R_EARTH = 6371000.0
RHO_ICE = 916.7
LAT0, LON0 = 63.0, 5.0


def block_mean(a, target):
    a = np.asarray(a, float)
    if a.ndim != 3:
        raise ValueError("expected (nz,ny,nx)")
    f = [max(1, int(np.ceil(n / target))) for n in a.shape]
    pad = [(-n) % f[i] for i, n in enumerate(a.shape)]
    if any(pad):
        a = np.pad(a, ((0, pad[0]), (0, pad[1]), (0, pad[2])), mode="constant")
    nz, ny, nx = a.shape
    return a.reshape(nz // f[0], f[0], ny // f[1], f[1], nx // f[2], f[2]).mean(axis=(1, 3, 5))


def downsample(phi, T=None, S=None, target=24):
    ph = block_mean(phi, target)
    out = [ph]
    for a in (T, S):
        if a is None:
            out.append(None)
            continue
        num = block_mean(np.asarray(a, float) * np.asarray(phi, float), target)
        out.append(num / np.maximum(ph, 1.0e-6))
    return out


def daily_frame(ds):
    t = np.asarray(ds.time.values, float)
    n = int(np.floor(t[-1] / 86400.0))
    rows = []
    for d in range(n + 1):
        m = (t >= d * 86400.0) & (t < (d + 1) * 86400.0)
        if not m.any():
            continue
        k = np.where(m)[0]
        rec = {"day": d, "lat": float(ds.latitude.values[k[-1]]), "lon": float(ds.longitude.values[k[-1]]),
               "mass": float(ds.mass.values[k[-1]]), "draft": float(ds.draft.values[k[-1]]),
               "freeboard": float(ds.freeboard.values[k[-1]]),
               "a_wet": float(np.nanmean(ds.a_wet.values[k])),
               "T_w": float(np.nanmean(ds.ocean_T_draft.values[k])),
               "S_w": float(np.nanmean(ds.ocean_S_draft.values[k])),
               "u_w": float(np.nanmean(ds.ocean_u_draft.values[k])),
               "v_w": float(np.nanmean(ds.ocean_v_draft.values[k])),
               "wind": float(np.nanmean(np.hypot(ds.air_u10.values[k], ds.air_v10.values[k])))}
        for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"):
            rec[v] = float(np.nansum(ds[v].values[k])) if v in ds else 0.0
        rec["mass_loss_total"] = sum(rec[v] for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"))
        rec["melt_rate_m_day"] = rec["mass_loss_total"] / (RHO_ICE * rec["a_wet"]) if rec["a_wet"] > 0 else np.nan
        rec["speed"] = 0.0
        rows.append(rec)
    lat = np.array([r["lat"] for r in rows]); lon = np.array([r["lon"] for r in rows])
    seg = np.hypot(np.deg2rad(np.diff(lat)) * R_EARTH,
                   np.deg2rad(np.diff(lon)) * R_EARTH * np.cos(np.deg2rad((lat[1:] + lat[:-1]) / 2)))
    for i, r in enumerate(rows):
        r["path_km"] = float(seg[:i].sum() / 1000.0) if i else 0.0
        r["speed"] = float(seg[i - 1] / 86400.0) if i > 0 else 0.0
    return rows


def plot_track(rows, static, out, color_key, title, label, cmap, log=False):
    st = xr.open_dataset(static)
    dep = np.asarray(st.deptho.values); lat = np.asarray(st.latitude.values); lon = np.asarray(st.longitude.values)
    mask = np.asarray(st.mask.values[0])
    st.close()
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.pcolormesh(lon, lat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.55)
    ax.contour(lon, lat, mask, levels=[0.5], colors="k", linewidths=.5)
    c = np.array([r[color_key] for r in rows])
    if log:
        good = np.isfinite(c) & (c > 0)
        norm = LogNorm(vmin=max(np.nanpercentile(c[good], 5), 1e-5), vmax=np.nanpercentile(c[good], 95)) if good.any() else None
    else:
        norm = None
    sc = ax.scatter([r["lon"] for r in rows], [r["lat"] for r in rows], c=c, cmap=cmap, norm=norm, s=14, zorder=3)
    ax.plot([r["lon"] for r in rows], [r["lat"] for r in rows], "k-", lw=.4, alpha=.5)
    ax.scatter(rows[0]["lon"], rows[0]["lat"], marker="*", s=140, c="red", label="start", zorder=4)
    if len(rows) > 1:
        ax.scatter(rows[-1]["lon"], rows[-1]["lat"], marker="X", s=80, c="black", label="end", zorder=4)
    fig.colorbar(sc, ax=ax, label=label, shrink=.8)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_title(title)
    ax.legend(loc="lower left"); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
    fig.tight_layout(); fig.savefig(out, dpi=220); plt.close(fig)


def plot_series(rows, out, name):
    t = np.array([r["day"] for r in rows], float)
    m0 = rows[0]["mass"]
    fig, ax = plt.subplots(3, 2, figsize=(13, 10))
    ax[0, 0].plot(t, [100 * (1 - r["mass"] / m0) for r in rows], "k-")
    ax[0, 0].set_ylabel("mass loss [%]"); ax[0, 0].set_title("Mass")
    ax[0, 1].plot(t, [r["draft"] for r in rows], label="draft")
    ax[0, 1].plot(t, [r["freeboard"] for r in rows], label="freeboard")
    ax[0, 1].set_ylabel("m"); ax[0, 1].legend(); ax[0, 1].set_title("Geometry")
    for v, lab in (("mass_loss_basal", "basal"), ("mass_loss_lateral", "lateral"),
                   ("mass_loss_surface", "surface")):
        ax[1, 0].plot(t, np.cumsum([r[v] for r in rows]) / m0 * 100, label=lab)
    ax[1, 0].set_ylabel("% of initial mass"); ax[1, 0].legend(); ax[1, 0].set_title("Melt components")
    ax[1, 1].plot(t, [r["T_w"] for r in rows], label="T water")
    ax[1, 1].plot(t, [r["S_w"] * 1000 for r in rows], label="S water [g/kg]")
    ax[1, 1].set_ylabel("T [C] / S [g/kg]"); ax[1, 1].legend(); ax[1, 1].set_title("Water at draft")
    ax[2, 0].plot(t, [r["speed"] for r in rows], label="drift")
    ax[2, 0].plot(t, [np.hypot(r["u_w"], r["v_w"]) for r in rows], label="current")
    ax[2, 0].set_ylabel("m/s"); ax[2, 0].legend(); ax[2, 0].set_title("Drift")
    ax[2, 1].plot(t, [r["wind"] for r in rows], "C3")
    ax[2, 1].set_ylabel("m/s"); ax[2, 1].set_title("Wind")
    for a in ax.ravel():
        a.grid(alpha=.25); a.set_xlabel("day")
    fig.suptitle(name); fig.tight_layout(); fig.savefig(out, dpi=220); plt.close(fig)


def snapshot_files(run_dir):
    return sorted(run_dir.glob("run.nc_snap_*.nc"))


def nearest_snapshot(files, day):
    best = None
    for f in files:
        try:
            with xr.open_dataset(f) as ds:
                d = float(ds.time.values[0]) / 86400.0
        except Exception:
            continue
        if best is None or abs(d - day) < abs(best[0] - day):
            best = (d, f)
    return best[1] if best else None


def plot_snapshots(run_dir, out, name, target=20):
    files = snapshot_files(run_dir)
    if not files:
        return
    days = [0, 90, 180, 270, 365]
    chosen = [nearest_snapshot(files, d) for d in days]
    fig = plt.figure(figsize=(18, 11))
    variables = ["phi", "T", "S_B"]
    for row, var in enumerate(variables):
        for col, (day, f) in enumerate(zip(days, chosen)):
            if f is None:
                continue
            with xr.open_dataset(f) as ds:
                phi = np.asarray(ds.phi.values, float)
                T = np.asarray(ds.T.values, float)
                S = np.asarray(ds.S_B.values, float)
                x = np.asarray(ds.x.values, float); y = np.asarray(ds.y.values, float); z = np.asarray(ds.z.values, float)
            ph, Td, Sd = downsample(phi, T, S, target=target)
            nz, ny, nx = ph.shape
            X, Y, Z = np.meshgrid(x[:nx], y[:ny], z[:nz], indexing="ij")
            cut = ~((X > x[nx // 2]) & (Y > y[ny // 2]))
            ax = fig.add_subplot(3, 5, row * 5 + col + 1, projection="3d")
            pht = ph.transpose(2, 1, 0)
            if var == "phi":
                mask = (pht > 0.25) & cut
                colors = plt.cm.Blues(0.35 + 0.65 * pht)
                ax.voxels(mask, facecolors=colors, edgecolor="none")
            else:
                field = (Td if var == "T" else Sd).transpose(2, 1, 0)
                good = (pht > 0.05) & cut
                cmap = "YlOrRd" if var == "T" else "Greens"
                ax.scatter(X[good], Y[good], Z[good], c=field[good], cmap=cmap, s=2, alpha=.7)
            ax.set_title(f"{var} day {int(day)}", fontsize=9)
            ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
            ax.view_init(elev=22, azim=-60)
    fig.suptitle(name); fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def make_gif(run_dir, static, out_prefix, name, target=24):
    files = snapshot_files(run_dir)
    if not files:
        return
    import matplotlib
    matplotlib.use("Agg")
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    frames_phi, frames_T = [], []
    for f in files:
        with xr.open_dataset(f) as ds:
            phi = np.asarray(ds.phi.values, float); T = np.asarray(ds.T.values, float)
            x = np.asarray(ds.x.values, float); y = np.asarray(ds.y.values, float); z = np.asarray(ds.z.values, float)
            day = int(float(ds.time.values[0]) / 86400.0)
        ph, Td, _ = downsample(phi, T, None, target=target)
        nz, ny, nx = ph.shape
        X, Y, Z = np.meshgrid(x[:nx], y[:ny], z[:nz], indexing="ij")
        cut = ~((X > x[nx // 2]) & (Y > y[ny // 2]))
        pht = ph.transpose(2, 1, 0)
        fig = plt.figure(figsize=(4.8, 4.2)); ax = fig.add_subplot(111, projection="3d")
        mask = (pht > 0.25) & cut
        ax.voxels(mask, facecolors=plt.cm.Blues(0.35 + 0.65 * pht), edgecolor="none")
        ax.set_title(f"phi day {day}", fontsize=9); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
        ax.view_init(elev=22, azim=-60); fig.tight_layout()
        fig.savefig(f"/tmp/opencode/s1217_phi_{day:03d}.png", dpi=110); plt.close(fig)
        frames_phi.append(Image.open(f"/tmp/opencode/s1217_phi_{day:03d}.png").convert("P", palette=Image.ADAPTIVE))

        fig = plt.figure(figsize=(4.8, 4.2)); ax = fig.add_subplot(111, projection="3d")
        good = (pht > 0.05) & cut
        ax.scatter(X[good], Y[good], Z[good], c=Td.transpose(2, 1, 0)[good], cmap="YlOrRd", s=3, alpha=.7)
        ax.set_title(f"T day {day}", fontsize=9); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
        ax.view_init(elev=22, azim=-60); fig.tight_layout()
        fig.savefig(f"/tmp/opencode/s1217_T_{day:03d}.png", dpi=110); plt.close(fig)
        frames_T.append(Image.open(f"/tmp/opencode/s1217_T_{day:03d}.png").convert("P", palette=Image.ADAPTIVE))
    if frames_phi:
        frames_phi[0].save(str(out_prefix) + "_phi.gif", save_all=True, append_images=frames_phi[1:], duration=250, loop=0, optimize=True)
    if frames_T:
        frames_T[0].save(str(out_prefix) + "_T.gif", save_all=True, append_images=frames_T[1:], duration=250, loop=0, optimize=True)


def plot_track_gif(rows, static, out, name):
    st = xr.open_dataset(static)
    dep = np.asarray(st.deptho.values); lat = np.asarray(st.latitude.values); lon = np.asarray(st.longitude.values)
    mask = np.asarray(st.mask.values[0]); st.close()
    frames = []
    step = max(1, len(rows) // 36)
    for i in range(step, len(rows) + step, step):
        ii = min(i, len(rows))
        fig, ax = plt.subplots(figsize=(5.2, 4.8))
        ax.pcolormesh(lon, lat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.55)
        ax.contour(lon, lat, mask, levels=[0.5], colors="k", linewidths=.5)
        ax.plot([r["lon"] for r in rows[:ii]], [r["lat"] for r in rows[:ii]], "r-", lw=1.0)
        ax.scatter(rows[0]["lon"], rows[0]["lat"], marker="*", c="red", s=70)
        ax.set_xlim(min(r["lon"] for r in rows) - 4, max(r["lon"] for r in rows) + 4)
        ax.set_ylim(min(r["lat"] for r in rows) - 2, max(r["lat"] for r in rows) + 2)
        ax.set_title(f"{name} day {rows[ii-1]['day']}", fontsize=9)
        ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
        fig.tight_layout(); fig.savefig(f"/tmp/opencode/s1217_track_{ii:04d}.png", dpi=110); plt.close(fig)
        frames.append(Image.open(f"/tmp/opencode/s1217_track_{ii:04d}.png").convert("P", palette=Image.ADAPTIVE))
    if frames:
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=200, loop=0, optimize=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--name", default="")
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    run_nc = a.run_dir / "run.nc"
    if not run_nc.exists():
        raise SystemExit(f"missing {run_nc}")
    with xr.open_dataset(run_nc) as ds:
        rows = daily_frame(ds)
    name = a.name or a.run_dir.name
    plot_track(rows, a.static, a.out_dir / "track_day.png", "day", f"{name} track", "day", "viridis")
    plot_track(rows, a.static, a.out_dir / "track_melt.png", "melt_rate_m_day",
               f"{name} melt rate", r"melt rate [m day$^{-1}$]", "YlOrRd", log=True)
    plot_series(rows, a.out_dir / "time_series.png", name)
    plot_snapshots(a.run_dir, a.out_dir / "snapshots_3d.png", name)
    make_gif(a.run_dir, a.static, a.out_dir / "evolution", name)
    plot_track_gif(rows, a.static, a.out_dir / "track.gif", name)
    print(f"wrote figures to {a.out_dir}")


if __name__ == "__main__":
    main()
