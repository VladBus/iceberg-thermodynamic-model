#!/usr/bin/env python3
"""Stage 12.18 figure fixes (evolved from the 12.17 per-run script).

Track/time-series figures and 3D snapshots/GIFs for a single run. 3D axes are
labelled in metres with fixed full-domain limits; T uses surface voxels plus
central x-z/y-z slices; S_B is shown on the boundary shell only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd
import xarray as xr
from PIL import Image
from scipy.ndimage import binary_erosion, generate_binary_structure

R_EARTH = 6371000.0
RHO_ICE = 916.7
FRAME_DIR = Path("data/validation/stage12.18/frames")
FRAME_DIR.mkdir(parents=True, exist_ok=True)


def block_mean(a, target):
    a = np.asarray(a, float)
    f = [max(1, int(np.ceil(n / target))) for n in a.shape]
    pad = [(-n) % f[i] for i, n in enumerate(a.shape)]
    if any(pad):
        a = np.pad(a, ((0, pad[0]), (0, pad[1]), (0, pad[2])), mode="constant")
    nz, ny, nx = a.shape
    return a.reshape(nz // f[0], f[0], ny // f[1], f[1], nx // f[2], f[2]).mean(axis=(1, 3, 5))


def downsample(phi, T=None, S=None, target=32):
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
        rec = {
            "day": d, "lat": float(ds.latitude.values[k[-1]]), "lon": float(ds.longitude.values[k[-1]]),
            "mass": float(ds.mass.values[k[-1]]), "draft": float(ds.draft.values[k[-1]]),
            "freeboard": float(ds.freeboard.values[k[-1]]),
            "a_wet": float(np.nanmean(ds.a_wet.values[k])),
            "T_w": float(np.nanmean(ds.ocean_T_draft.values[k])),
            "S_w": float(np.nanmean(ds.ocean_S_draft.values[k])),
            "u_w": float(np.nanmean(ds.ocean_u_draft.values[k])),
            "v_w": float(np.nanmean(ds.ocean_v_draft.values[k])),
            "wind": float(np.nanmean(np.hypot(ds.air_u10.values[k], ds.air_v10.values[k]))),
            "grounded": int(ds.grounded.values[k[-1]]) if "grounded" in ds else 0,
        }
        for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"):
            rec[v] = float(np.nansum(ds[v].values[k])) if v in ds else 0.0
        rec["mass_loss_total"] = sum(rec[v] for v in ("mass_loss_basal", "mass_loss_lateral", "mass_loss_surface", "mass_loss_vapor"))
        rec["melt_rate_m_day"] = rec["mass_loss_total"] / (RHO_ICE * rec["a_wet"]) if rec["a_wet"] > 0 else np.nan
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
    mask = np.asarray(st.mask.values[0]); st.close()
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.pcolormesh(lon, lat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.55)
    ax.contour(lon, lat, mask, levels=[0.5], colors="k", linewidths=.5)
    c = np.array([r[color_key] for r in rows])
    good = np.isfinite(c)
    if log and good.any():
        cmin = max(np.nanpercentile(c[good], 5), 1e-5); cmax = max(np.nanpercentile(c[good], 95), cmin * 1.1)
        norm = LogNorm(vmin=cmin, vmax=cmax)
    else:
        norm = None
    drift = np.array([r["grounded"] == 0 for r in rows])
    if good.any():
        sc = ax.scatter(np.array([r["lon"] for r in rows])[good & drift],
                        np.array([r["lat"] for r in rows])[good & drift],
                        c=c[good & drift], cmap=cmap, norm=norm, s=14, zorder=3, label="drift")
        if (good & ~drift).any():
            ax.scatter(np.array([r["lon"] for r in rows])[good & ~drift],
                       np.array([r["lat"] for r in rows])[good & ~drift],
                       c=c[good & ~drift], cmap=cmap, norm=norm, s=22, marker="x", zorder=4,
                       label="grounded in place")
    # line style: dashed for grounded segments
    for i in range(1, len(rows)):
        style = "--" if (rows[i]["grounded"] or rows[i - 1]["grounded"]) else "-"
        ax.plot([rows[i - 1]["lon"], rows[i]["lon"]], [rows[i - 1]["lat"], rows[i]["lat"]],
                color="k", lw=.5, ls=style, alpha=.55)
    ax.scatter(rows[0]["lon"], rows[0]["lat"], marker="*", s=150, c="red", label="start", zorder=5)
    if len(rows) > 1:
        ax.scatter(rows[-1]["lon"], rows[-1]["lat"], marker="X", s=85, c="black", label="end", zorder=5)
    if norm is not None:
        fig.colorbar(sc, ax=ax, label=label, shrink=.8)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_title(title)
    ax.legend(loc="lower left", fontsize=8); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
    fig.tight_layout(); fig.savefig(out, dpi=220); plt.close(fig)


def plot_series(rows, out, name):
    t = np.array([r["day"] for r in rows], float); m0 = rows[0]["mass"]
    fig, ax = plt.subplots(3, 2, figsize=(13, 10))
    ax[0, 0].plot(t, [100 * (1 - r["mass"] / m0) for r in rows], "k-")
    ax[0, 0].set_ylabel("mass loss [%]"); ax[0, 0].set_title("Mass")
    ax[0, 1].plot(t, [r["draft"] for r in rows], label="draft")
    ax[0, 1].plot(t, [r["freeboard"] for r in rows], label="freeboard")
    ax[0, 1].set_ylabel("m"); ax[0, 1].legend(); ax[0, 1].set_title("Geometry")
    for v, lab in (("mass_loss_basal", "basal"), ("mass_loss_lateral", "lateral"), ("mass_loss_surface", "surface")):
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


def snapshot_mass(ds, run_mass, day, m0):
    if "mass" in ds:
        return float(ds.mass.values[0])
    return run_mass.get(int(round(day)), m0)


def set_axes(ax, nx, ny, nz, dx, dy, dz):
    ax.set_xlim(0, nx); ax.set_ylim(0, ny); ax.set_zlim(0, nz)
    ax.set_xticks([0, nx / 2, nx]); ax.set_yticks([0, ny / 2, ny]); ax.set_zticks([0, nz / 2, nz])
    ax.set_xticklabels([0, f"{nx*dx/2:.0f}", f"{nx*dx:.0f}"])
    ax.set_yticklabels([0, f"{ny*dy/2:.0f}", f"{ny*dy:.0f}"])
    ax.set_zticklabels([0, f"{nz*dz/2:.0f}", f"{nz*dz:.0f}"])
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
    ax.set_box_aspect((nx * dx, ny * dy, nz * dz))


def load_snapshot(f, target):
    with xr.open_dataset(f) as ds:
        phi = np.asarray(ds.phi.values, float)
        T = np.asarray(ds.T.values, float)
        S = np.asarray(ds.S_B.values, float)
        x = np.asarray(ds.x.values, float); y = np.asarray(ds.y.values, float); z = np.asarray(ds.z.values, float)
        mass = float(ds.mass.values[0]) if "mass" in ds else np.nan
        tval = float(ds.time.values[0])
    ph, Td, Sd = downsample(phi, T, S, target=target)
    return ph, Td, Sd, x, y, z, mass, tval


def plot_snapshots(run_dir, out, name, target=32):
    files = snapshot_files(run_dir)
    if not files:
        return
    days = [0, 90, 180, 270, 365]
    chosen = [nearest_snapshot(files, d) for d in days]
    data = []
    for f in chosen:
        data.append(load_snapshot(f, target) if f else None)
    valid = [d for d in data if d is not None]
    if not valid:
        return
    _, _, _, x, y, z, _, _ = valid[0]
    Lx, Ly, Lz = float(x[-1] + (x[1] - x[0]) / 2), float(y[-1] + (y[1] - y[0]) / 2), float(z[-1] + (z[1] - z[0]) / 2)
    Ts = np.concatenate([d[1][d[0] > 0.05] for d in valid if d[1] is not None])
    Ss = np.concatenate([d[2][d[0] > 0.05] for d in valid if d[2] is not None])
    tnorm = Normalize(np.nanpercentile(Ts, 2), np.nanpercentile(Ts, 98)) if len(Ts) else Normalize(-10, 0)
    snorm = Normalize(np.nanpercentile(Ss, 2), np.nanpercentile(Ss, 98)) if len(Ss) else Normalize(0, 0.035)
    fig = plt.figure(figsize=(18, 14))
    axes = fig.subplots(4, 5, subplot_kw={"projection": "3d"})
    structure = generate_binary_structure(3, 1)
    for col, (day, d) in enumerate(zip(days, data)):
        if d is None:
            continue
        ph, Td, Sd, x, y, z, _, _ = d
        nz, ny, nx = ph.shape
        pht = ph.transpose(2, 1, 0); Tt = Td.transpose(2, 1, 0); St = Sd.transpose(2, 1, 0)
        dx = (x[1] - x[0]) * (len(x) / nx); dy = (y[1] - y[0]) * (len(y) / ny); dz = (z[1] - z[0]) * (len(z) / nz)
        solid = pht > 0.05
        surface = solid & ~binary_erosion(solid, structure=structure, border_value=0)
        cut = ~((np.arange(nx)[:, None, None] > nx // 2) & (np.arange(ny)[None, :, None] > ny // 2))
        ax = axes[0, col]; ax.voxels(pht > 0.15, facecolors=plt.cm.Blues(0.25 + 0.75 * pht), edgecolor="none")
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.set_title(f"phi full day {int(day)}", fontsize=9); ax.view_init(22, -60)
        ax = axes[1, col]; ax.voxels((pht > 0.15) & cut, facecolors=plt.cm.Blues(0.25 + 0.75 * pht), edgecolor="none")
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.set_title(f"phi cut-away day {int(day)}", fontsize=9); ax.view_init(22, -60)
        ax = axes[2, col]
        ax.voxels(surface, facecolors=plt.cm.YlOrRd(tnorm(Tt)), edgecolor="none")
        Xg, Zg = np.meshgrid(np.arange(nx), np.arange(nz), indexing="ij")
        ax.plot_surface(Xg, np.full_like(Xg, ny // 2), Zg, facecolors=plt.cm.YlOrRd(tnorm(Tt[:, ny // 2, :])), shade=False, rstride=1, cstride=1)
        Yg, Zg2 = np.meshgrid(np.arange(ny), np.arange(nz), indexing="ij")
        ax.plot_surface(np.full_like(Yg, nx // 2), Yg, Zg2, facecolors=plt.cm.YlOrRd(tnorm(Tt[nx // 2, :, :])), shade=False, rstride=1, cstride=1)
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.set_title(f"T surface + slices day {int(day)}", fontsize=9); ax.view_init(22, -60)
        ax = axes[3, col]; ax.voxels(surface, facecolors=plt.cm.Greens(snorm(St)), edgecolor="none")
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.set_title(f"S_B shell day {int(day)}", fontsize=9); ax.view_init(22, -60)
    for r in range(4):
        sm = ScalarMappable(norm=Normalize(0, 1) if r < 2 else (tnorm if r == 2 else snorm),
                            cmap="Blues" if r < 2 else ("YlOrRd" if r == 2 else "Greens"))
        sm.set_array([])
        fig.colorbar(sm, ax=axes[r, :].ravel().tolist(), orientation="horizontal", fraction=0.018, pad=0.01,
                     label="phi" if r < 2 else ("T [C]" if r == 2 else "S_B [kg/kg]"))
    fig.suptitle(name); fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)


def run_year(run_dir):
    for part in reversed(run_dir.name.split("_")):
        if part.isdigit() and len(part) == 4:
            return int(part)
    return 2020


def make_gif(run_dir, static, out_prefix, name, target=24):
    files = snapshot_files(run_dir)
    if not files:
        return
    year = run_year(run_dir)
    start = datetime(year, 1, 1)
    with xr.open_dataset(run_dir / "run.nc") as ds:
        run_mass = {int(round(float(t) / 86400.0)): float(m) for t, m in zip(ds.time.values, ds.mass.values)}
    m0 = run_mass.get(0, next(iter(run_mass.values())))
    frames_phi, frames_T = [], []
    for f in files:
        ph, Td, Sd, x, y, z, mass, tval = load_snapshot(f, target=target)
        day = int(round(tval / 86400.0))
        mass = mass if np.isfinite(mass) else run_mass.get(day, m0)
        pct = 100.0 * mass / m0 if m0 else np.nan
        date = (start + timedelta(days=day)).strftime("%Y-%m-%d")
        nz, ny, nx = ph.shape
        pht = ph.transpose(2, 1, 0); Tt = Td.transpose(2, 1, 0)
        dx = (x[1] - x[0]) * (len(x) / nx); dy = (y[1] - y[0]) * (len(y) / ny); dz = (z[1] - z[0]) * (len(z) / nz)
        fig = plt.figure(figsize=(4.8, 4.4)); ax = fig.add_subplot(111, projection="3d")
        ax.voxels(pht > 0.25, facecolors=plt.cm.Blues(0.25 + 0.75 * pht), edgecolor="none")
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.view_init(22, -60)
        ax.set_title(f"phi  {date}  mass {pct:.1f}%", fontsize=9)
        fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.90)
        fig.savefig(str(FRAME_DIR / f"s1218_phi_{day:03d}.png"), dpi=110); plt.close(fig)
        frames_phi.append(Image.open(str(FRAME_DIR / f"s1218_phi_{day:03d}.png")).convert("P", palette=Image.ADAPTIVE))
        solid = pht > 0.05
        surface = solid & ~binary_erosion(solid, structure=generate_binary_structure(3, 1), border_value=0)
        fig = plt.figure(figsize=(4.8, 4.4)); ax = fig.add_subplot(111, projection="3d")
        ax.voxels(surface, facecolors=plt.cm.YlOrRd(Normalize(-10.0, 0.0)(Tt)), edgecolor="none")
        set_axes(ax, nx, ny, nz, dx, dy, dz); ax.view_init(22, -60)
        ax.set_title(f"T  {date}  mass {pct:.1f}%", fontsize=9)
        fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.90)
        fig.savefig(str(FRAME_DIR / f"s1218_T_{day:03d}.png"), dpi=110); plt.close(fig)
        frames_T.append(Image.open(str(FRAME_DIR / f"s1218_T_{day:03d}.png")).convert("P", palette=Image.ADAPTIVE))
    if frames_phi:
        frames_phi[0].save(str(out_prefix) + "_phi.gif", save_all=True, append_images=frames_phi[1:], duration=250, loop=0, optimize=True)
    if frames_T:
        frames_T[0].save(str(out_prefix) + "_T.gif", save_all=True, append_images=frames_T[1:], duration=250, loop=0, optimize=True)


def plot_track_gif(rows, static, out, name):
    st = xr.open_dataset(static)
    dep = np.asarray(st.deptho.values); lat = np.asarray(st.latitude.values); lon = np.asarray(st.longitude.values)
    mask = np.asarray(st.mask.values[0]); st.close()
    frames = []; step = max(1, len(rows) // 36)
    for i in range(step, len(rows) + step, step):
        ii = min(i, len(rows))
        fig, ax = plt.subplots(figsize=(5.2, 4.8))
        ax.pcolormesh(lon, lat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.55)
        ax.contour(lon, lat, mask, levels=[0.5], colors="k", linewidths=.5)
        for j in range(1, ii):
            style = "--" if (rows[j]["grounded"] or rows[j - 1]["grounded"]) else "-"
            ax.plot([rows[j - 1]["lon"], rows[j]["lon"]], [rows[j - 1]["lat"], rows[j]["lat"]], "r", lw=1.0, ls=style)
        ax.scatter(rows[0]["lon"], rows[0]["lat"], marker="*", c="red", s=70)
        ax.set_xlim(min(r["lon"] for r in rows) - 4, max(r["lon"] for r in rows) + 4)
        ax.set_ylim(min(r["lat"] for r in rows) - 2, max(r["lat"] for r in rows) + 2)
        ax.set_title(f"{name} day {rows[ii-1]['day']}", fontsize=9)
        ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.set_aspect(1 / np.cos(np.deg2rad(78)))
        fig.tight_layout(); fig.savefig(str(FRAME_DIR / f"s1218_track_{ii:04d}.png"), dpi=110); plt.close(fig)
        frames.append(Image.open(str(FRAME_DIR / f"s1218_track_{ii:04d}.png")).convert("P", palette=Image.ADAPTIVE))
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
