#!/usr/bin/env python3
"""Stage 12.17 final-run summary table and map (mass loss, t50)."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

R_EARTH = 6371000.0


def daily(ds):
    t = np.asarray(ds.time.values, float)
    n = int(np.floor(t[-1] / 86400.0))
    out = []
    for d in range(n + 1):
        m = (t >= d * 86400.0) & (t < (d + 1) * 86400.0)
        if m.any():
            k = np.where(m)[0]
            out.append((float(d), float(ds.mass.values[k[-1]]),
                        float(ds.latitude.values[k[-1]]), float(ds.longitude.values[k[-1]])))
    return out


def crossing(rows, frac):
    m0 = rows[0][1]
    target = frac * m0
    for i in range(1, len(rows)):
        if rows[i][1] <= target:
            d0, m0i = rows[i - 1][0], rows[i - 1][1]
            d1, m1 = rows[i][0], rows[i][1]
            if m0i == m1:
                return d1
            w = (m0i - target) / (m0i - m1)
            return d0 + w * (d1 - d0)
    return np.nan


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("data/validation/stage12.17/final"))
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--out-dir", type=Path, default=Path("data/validation/stage12.17"))
    p.add_argument("--fig-dir", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.17"))
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.fig_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in sorted(a.root.glob("*_*")):
        f = d / "run.nc"
        if not f.exists():
            continue
        tag, year = d.name.rsplit("_", 1)
        with xr.open_dataset(f) as ds:
            dd = daily(ds)
            lat0 = float(ds.latitude.values[0]); lon0 = float(ds.longitude.values[0])
            latf = float(ds.latitude.values[-1]); lonf = float(ds.longitude.values[-1])
        if not dd:
            continue
        m0 = dd[0][1]; mf = dd[-1][1]
        lat = np.array([r[2] for r in dd]); lon = np.array([r[3] for r in dd])
        seg = np.hypot(np.deg2rad(np.diff(lat)) * R_EARTH,
                       np.deg2rad(np.diff(lon)) * R_EARTH * np.cos(np.deg2rad((lat[1:] + lat[:-1]) / 2)))
        logtxt = (d / "run.log").read_text(errors="ignore")
        rows.append({
            "source": tag, "year": int(year), "days": dd[-1][0] + 1,
            "mass_loss_pct": 100 * (1 - mf / m0), "t50_days": crossing(dd, 0.5),
            "path_km": float(seg.sum() / 1000), "net_km": float(np.hypot(
                np.deg2rad(latf - lat0) * R_EARTH,
                np.deg2rad(lonf - lon0) * R_EARTH * np.cos(np.deg2rad((latf + lat0) / 2))) / 1000),
            "lat0": lat0, "lon0": lon0, "lat_final": latf, "lon_final": lonf,
            "grounded": "STOP: iceberg grounded" in logtxt,
            "strict_stop": "STOP: primary ocean profile unavailable" in logtxt,
        })
    table = pd.DataFrame(rows).sort_values(["source", "year"])
    table.to_csv(a.out_dir / "final_summary.csv", index=False)
    if table.empty:
        print("no final runs yet")
        return
    st = xr.open_dataset(a.static)
    dep = np.asarray(st.deptho.values); glat = np.asarray(st.latitude.values); glon = np.asarray(st.longitude.values)
    st.close()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    for ax, key, title, cmap in [(axes[0], "mass_loss_pct", "annual mass loss [%]", "YlOrRd"),
                                 (axes[1], "t50_days", "time to 50% remaining mass [days]", "viridis")]:
        ax.pcolormesh(glon, glat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.5)
        vals = table[key].to_numpy(float); good = np.isfinite(vals)
        norm = plt.Normalize(np.nanmin(vals[good]), np.nanmax(vals[good])) if good.any() else None
        for year, marker in [(2020, "o"), (2024, "s")]:
            sub = table[table["year"] == year]
            g = np.isfinite(sub[key].to_numpy(float))
            if g.any():
                ax.scatter(sub.loc[g, "lon0"], sub.loc[g, "lat0"], c=sub.loc[g, key],
                           cmap=cmap, norm=norm, marker=marker, s=110, edgecolor="k", zorder=3)
            if (~g).any():
                ax.scatter(sub.loc[~g, "lon0"], sub.loc[~g, "lat0"], marker=marker, s=110,
                           facecolor="none", edgecolor="grey", zorder=4)
        for _, r in table.iterrows():
            ax.annotate(f"{r['source']} {r['year']}", (r["lon0"], r["lat0"]),
                        xytext=(5, 4), textcoords="offset points", fontsize=8)
        if norm is not None:
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            fig.colorbar(sm, ax=ax, shrink=.8, label=key)
        ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_title(title)
        ax.set_aspect(1 / np.cos(np.deg2rad(79)))
    fig.suptitle("2020/2024 final 100^3 runs (circle=2020, square=2024; grey=not reached)")
    fig.tight_layout(); fig.savefig(a.fig_dir / "final_summary_map.png", dpi=220); plt.close(fig)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
