#!/usr/bin/env python3
"""Summarise the six Stage 12.19 100^3 free-drift reference runs."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

R = 6371000.0
CASES = [
    ("FJL_A", "FJL", "data/validation/stage12.19/stage4/final/FJL_A"),
    ("NZ_A", "NZ", "data/validation/stage12.19/stage4/final/NZ_A"),
    ("NZ_B", "NZ", "data/validation/stage12.19/stage4/final/NZ_B"),
    ("D2", "SV-east", "data/validation/stage12.19/stage4/final/D2"),
    ("D4", "SV-north", "data/validation/stage12.19/stage4/final/D4"),
    ("D5", "Barents", "data/validation/stage12.19/stage4/final/D5"),
]


def cross(days, mass, frac):
    target = frac * mass[0]
    for i in range(1, len(mass)):
        if mass[i] <= target:
            if mass[i - 1] == mass[i]:
                return float(days[i])
            w = (mass[i - 1] - target) / (mass[i - 1] - mass[i])
            return float(days[i - 1] + w * (days[i] - days[i - 1]))
    return np.nan


def path_net(lat, lon):
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    seg = np.hypot(np.deg2rad(np.diff(lat)) * R,
                   np.deg2rad(np.diff(lon)) * R * np.cos(np.deg2rad((lat[1:] + lat[:-1]) / 2)))
    net = np.hypot(np.deg2rad(lat[-1] - lat[0]) * R,
                   np.deg2rad(lon[-1] - lon[0]) * R * np.cos(np.deg2rad((lat[-1] + lat[0]) / 2)))
    return float(seg.sum() / 1000), float(net / 1000)


def read_case(tag, source, root):
    p = Path(root) / "run.nc"
    if not p.exists():
        return None, None
    with xr.open_dataset(p) as ds:
        t = np.asarray(ds.time.values, float) / 86400.0
        # daily endpoint
        day = np.floor(t + 1e-9).astype(int)
        last = np.r_[np.where(np.diff(day))[0], len(day) - 1]
        days = t[last]
        mass = np.asarray(ds.mass.values, float)[last]
        lat = np.asarray(ds.latitude.values, float)[last]
        lon = np.asarray(ds.longitude.values, float)[last]
        g = np.asarray(ds.grounded.values, float)[last] if "grounded" in ds else np.zeros_like(days)
    path, net = path_net(lat, lon)
    status_file = Path(root) / "status.log"
    status = status_file.read_text().strip() if status_file.exists() else "running/incomplete"
    return {
        "tag": tag, "source": source, "days": float(days[-1]), "mass_initial_kg": float(mass[0]),
        "mass_final_kg": float(mass[-1]), "mass_loss_pct": float(100 * (1 - mass[-1] / mass[0])),
        "t50_days": cross(days, mass, .5), "t99_days": cross(days, mass, .01),
        "path_km": path, "net_km": net,
        "mean_speed_m_s": path * 1000 / max(days[-1] * 86400, 1),
        "first_60d_grounded": bool(np.any(g[days <= 60] > 0)),
        "status": status,
    }, (days, mass, lat, lon)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path("data/validation/stage12.19/stage4/final"))
    p.add_argument("--fig", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19/stage4_summary.png"))
    a = p.parse_args(); a.out_dir.mkdir(parents=True, exist_ok=True); a.fig.parent.mkdir(parents=True, exist_ok=True)
    rows, tracks = [], {}
    for tag, source, root in CASES:
        r, tr = read_case(tag, source, root)
        if r:
            rows.append(r); tracks[tag] = tr
    df = pd.DataFrame(rows); df.to_csv(a.out_dir / "summary.csv", index=False)
    print(df.to_string(index=False))
    if not df.empty:
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
        for tag, source, _ in CASES:
            if tag not in tracks: continue
            days, mass, lat, lon = tracks[tag]
            axes[0].plot(days, 100 * mass / mass[0], label=tag)
            axes[1].plot(lon, lat, label=tag)
        axes[0].set_xlabel("day"); axes[0].set_ylabel("remaining mass [%]")
        axes[0].set_title("100^3 free-drift reference runs"); axes[0].grid(alpha=.25); axes[0].legend(fontsize=7)
        axes[1].set_xlabel("longitude"); axes[1].set_ylabel("latitude")
        axes[1].set_title("tracks"); axes[1].grid(alpha=.25); axes[1].legend(fontsize=7)
        axes[1].set_aspect(1 / np.cos(np.deg2rad(78)))
        fig.tight_layout(); fig.savefig(a.fig, dpi=200, bbox_inches="tight"); plt.close(fig)
        print(a.fig)


if __name__ == "__main__":
    main()
