#!/usr/bin/env python3
"""Stage 12.18 summary: mass loss, t50/t99 and stop reasons for 12 runs."""
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import xarray as xr

R_EARTH = 6371000.0


def daily(ds):
    t = np.asarray(ds.time.values, float); n = int(np.floor(t[-1] / 86400.0)); out = []
    for d in range(n + 1):
        m = (t >= d * 86400.0) & (t < (d + 1) * 86400.0)
        if m.any():
            k = np.where(m)[0]
            out.append((float(d), float(ds.mass.values[k[-1]]), float(ds.latitude.values[k[-1]]),
                        float(ds.longitude.values[k[-1]])))
    return out


def crossing(rows, frac):
    m0 = rows[0][1]; target = frac * m0
    for i in range(1, len(rows)):
        if rows[i][1] <= target:
            d0, m0i = rows[i - 1][0], rows[i - 1][1]; d1, m1 = rows[i][0], rows[i][1]
            return d1 if m0i == m1 else d0 + (m0i - target) / (m0i - m1) * (d1 - d0)
    return np.nan


def stop_reason(log, days):
    if days >= 365.0:
        return "end of forcing"
    if "melted away" in log:
        return "melted"
    if "GROUNDED_IN_PLACE" in log:
        return "grounded-in-place"
    if "STOP: iceberg grounded" in log:
        return "grounded"
    if "STOP: no valid reanalysis ocean" in log:
        return "no-ocean"
    if "STOP: primary ocean profile unavailable" in log:
        return "strict-ocean"
    return "stopped"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("data/validation/stage12.18"))
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    p.add_argument("--out-dir", type=Path, default=Path("data/validation/stage12.18"))
    p.add_argument("--fig-dir", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.18"))
    a = p.parse_args(); a.out_dir.mkdir(parents=True, exist_ok=True); a.fig_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in sorted(a.root.glob("*_*")):
        f = d / "run.nc"
        if not f.exists():
            continue
        tag, year = d.name.rsplit("_", 1)
        try:
            year = int(year)
        except ValueError:
            continue
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
        log = (d / "run.log").read_text(errors="ignore")
        days = dd[-1][0] + 1
        rows.append(dict(source=tag, year=year, days=days,
                         mass_loss_pct=100 * (1 - mf / m0),
                         t50_days=crossing(dd, 0.5), t99_days=crossing(dd, 0.01),
                         path_km=float(seg.sum() / 1000),
                         lat0=lat0, lon0=lon0, lat_final=latf, lon_final=lonf,
                         stop=stop_reason(log, days)))
    table = pd.DataFrame(rows).sort_values(["source", "year"])
    table.to_csv(a.out_dir / "final_summary.csv", index=False)
    if table.empty:
        print("no runs yet"); return
    st = xr.open_dataset(a.static)
    dep = np.asarray(st.deptho.values); glat = np.asarray(st.latitude.values); glon = np.asarray(st.longitude.values)
    st.close()

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    markers = {"end of forcing": "o", "melted": "*", "grounded-in-place": "P", "grounded": "X", "no-ocean": "D", "strict-ocean": "s", "stopped": "x"}
    panels = [(0, 0, 2020, "mass_loss_pct", "mass loss by end of run [%]"),
              (0, 1, 2024, "mass_loss_pct", "mass loss by end of run [%]"),
              (1, 0, 2020, "t99_days", "time to 99% mass loss [d]"),
              (1, 1, 2024, "t99_days", "time to 99% mass loss [d]")]
    for i, j, year, key, title in panels:
        ax = axes[i, j]
        ax.pcolormesh(glon, glat, np.ma.masked_invalid(dep), shading="auto", cmap="Blues_r", alpha=.45)
        sub = table[table.year == year]
        vals = sub[key].to_numpy(float); good = np.isfinite(vals)
        vmin = np.nanmin(vals[good]) if good.any() else 0.0; vmax = np.nanmax(vals[good]) if good.any() else 1.0
        if vmax <= vmin: vmax = vmin + 1.0
        norm = plt.Normalize(vmin, vmax)
        cmap = "YlOrRd" if key == "mass_loss_pct" else "viridis"
        sc = None
        for _, r in sub.iterrows():
            ax.scatter(r.lon0, r.lat0, marker="*", s=140, c="red", edgecolor="k", zorder=5)
            mk = markers.get(r.stop, "o")
            sc = ax.scatter(r.lon_final, r.lat_final, marker=mk, s=120,
                            c=[r[key]] if np.isfinite(r[key]) else ["grey"],
                            cmap=cmap if np.isfinite(r[key]) else None, norm=norm if np.isfinite(r[key]) else None,
                            edgecolor="k", zorder=6)
            ax.annotate(f"{r.source} ({r.days:.0f} d)", (r.lon_final, r.lat_final), xytext=(5, 4),
                        textcoords="offset points", fontsize=8)
        if good.any():
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            fig.colorbar(sm, ax=ax, shrink=.75, label=title)
        ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
        ax.set_title(f"{year}: {title}")
        ax.set_aspect(1 / np.cos(np.deg2rad(79)))
        ax.legend(handles=[Line2D([0], [0], marker="*", color="w", markerfacecolor="red", markersize=10, label="start")] +
                  [Line2D([0], [0], marker=m, color="w", markerfacecolor="grey", markeredgecolor="k", markersize=8, label=k)
                   for k, m in markers.items()], loc="lower left", fontsize=7)
    fig.suptitle("Stage 12.18: 50 m cube, 2020/2024 (end marker = stop reason)")
    fig.tight_layout(); fig.savefig(a.fig_dir / "final_summary_map.png", dpi=220); plt.close(fig)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
