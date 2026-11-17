#!/usr/bin/env python3
"""Stage 12.21: forcing/region figures from existing reanalysis only.

The script never modifies the model or launches a model run.  GLORYS12 and
ERA5 monthly files are opened one month at a time; no full-year cube is held
in memory.  ``--block`` selects 0/A/B/V/G and ``--lang`` selects labels.
"""
from __future__ import annotations

import argparse
import calendar
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "docs/wiki/stages/stage12/figures/stage12.21"
DATA = ROOT / "data/input/reanalysis"
STATIC = ROOT / "data/input/static/glorys_static_barents.nc"
YEARS = (2020, 2024)
SEASONS = {"annual": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
           "winter": (1, 2, 3), "summer": (7, 8, 9)}
REGIONS = {
    "BARENTS": (63.0, 86.0, 5.0, 80.0),
    # track envelope plus 2.5 deg, see manifest
    "FJL": (74.0, 83.5, 25.0, 68.0),
    "NZ": (71.0, 83.0, 40.0, 71.0),
}
RUNS = {
    "FJL_A_2020": ("FJL", 2020, ROOT / "data/validation/stage12.20/final/FJL_A_2020/run.nc"),
    "NZ_A_2020": ("NZ", 2020, ROOT / "data/validation/stage12.20/final/NZ_A_2020/run.nc"),
    "NZ_B_2020": ("NZ", 2020, ROOT / "data/validation/stage12.20/final/NZ_B_2020/run.nc"),
    "FJL_A_2024": ("FJL", 2024, ROOT / "data/validation/stage12.20/final/FJL_A_2024/run.nc"),
    "NZ_A_2024": ("NZ", 2024, ROOT / "data/validation/stage12.20/final/NZ_A_2024/run.nc"),
    "NZ_B_2024": ("NZ", 2024, ROOT / "data/validation/stage12.20/final/NZ_B_2024/run.nc"),
}
POINTS = {"FJL_A": (80.5, 45.0), "NZ_A": (75.0, 53.583),
          "NZ_B": (78.0, 55.0), "Barents_1": (76.0, 40.0)}
LABELS = {
    "en": dict(longitude="longitude", latitude="latitude", depth="depth [m]",
               days="days", year="Year", season="Season", annual="Annual",
               winter="Winter (Jan–Mar)", summer="Summer (Jul–Sep)", temperature="T [°C]", salinity="S [psu]",
               speed="speed [m s$^{-1}$]", u="u [m s$^{-1}$]", v="v [m s$^{-1}$]",
               ice="sea-ice concentration", start="start", end="end",
               melt="melt-out", grounded="grounding", strict="strict ocean limit",
               t50="t50", region="Region", depth_km="Depth [m]"),
    "ru": dict(longitude="долгота", latitude="широта", depth="глубина [м]",
               days="сутки", year="Год", season="Сезон", annual="Год",
               winter="Зима (янв–мар)", summer="Лето (июл–сен)", temperature="T [°C]", salinity="S [psu]",
               speed="скорость [м/с]", u="u [м/с]", v="v [м/с]",
               ice="концентрация льда", start="старт", end="конец",
               melt="таяние", grounded="посадка", strict="strict ocean",
               t50="t50", region="Район", depth_km="Глубина [м]"),
}
LANG = "en"
MANIFEST = FIG / "figures_manifest.csv"


def L(key):
    return LABELS[LANG].get(str(key).lower(), str(key))


def set_lang(lang):
    global LANG
    LANG = lang



def ocean_mask_on(lat, lon):
    with xr.open_dataset(STATIC) as ds:
        glat = ds.latitude.values; glon = ds.longitude.values
        dep = ds.deptho.values
    ii = np.array([int(np.argmin(abs(glat - x))) for x in lat])
    jj = np.array([int(np.argmin(abs(glon - x))) for x in lon])
    return (dep[np.ix_(ii, jj)] > 0)

def glorys_path(year, month):
    return DATA / "glorys" / str(year) / f"glorys12_barents_{year}_{month:02d}.nc"


def era5_path(year, month):
    return DATA / "era5" / str(year) / f"era5_{year}_{month:02d}_daily.nc"


def ensure_dirs(*parts):
    d = FIG.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def check_png(path):
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB"))
    b = np.concatenate([a[:3].ravel(), a[-3:].ravel(), a[:, :3].ravel(), a[:, -3:].ravel()])
    if np.any(b < 245):
        raise RuntimeError(f"non-white border: {path}")



def check_text(fig, path):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text().strip() or t.get_clip_on():
            continue
        b = t.get_window_extent(renderer=r)
        if b.x0 < -40 or b.y0 < -40 or b.x1 > W + 40 or b.y1 > H + 40:
            print("OUTSIDE", repr(t.get_text()), b.bounds, "canvas", W, H, flush=True)
            raise RuntimeError(f"text outside {path}: {t.get_text()}")


def save_fig(fig, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    check_text(fig, out)
    fig.savefig(out.with_suffix(".png"), dpi=300)
    for coll in fig.findobj(matplotlib.collections.Collection):
        coll.set_rasterized(True)
    fig.savefig(out.with_suffix(".pdf"), dpi=300)
    check_png(out.with_suffix(".png"))
    for ext in (".png", ".pdf"):
        if not out.with_suffix(ext).exists() or out.with_suffix(ext).stat().st_size == 0:
            raise RuntimeError(f"missing/empty {out.with_suffix(ext)}")
    plt.close(fig)


def manifest_add(file, variable, source, period, level, aggregation, region):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        pd.DataFrame(columns=["file", "variable", "source", "period",
                              "level", "aggregation", "region"]).to_csv(MANIFEST, index=False)
    row = pd.DataFrame([dict(file=str(Path(file).relative_to(ROOT)), variable=variable,
                             source=source, period=period, level=level,
                             aggregation=aggregation, region=region)])
    row.to_csv(MANIFEST, mode="a", header=False, index=False)


def panel(ax, letter, x=.02, y=.96):
    ax.text(x, y, f"({letter})", transform=ax.transAxes, va="top",
            fontsize=8, fontweight="bold", zorder=10,
            bbox=dict(fc="white", ec="none", alpha=.78, pad=.4))


def scale_bar(ax, lon0, lat0, length_km=100):
    dlon = length_km / (111.0 * np.cos(np.deg2rad(lat0)))
    ax.plot([lon0 - dlon, lon0], [lat0, lat0], color="k", lw=2)
    ax.text(lon0 - dlon / 2, lat0 + 0.22, f"{length_km:g} km", ha="center", fontsize=8)



def flow_vectors(u, v, lat):
    """Keep geographic arrow direction while preserving the speed magnitude."""
    sp = np.hypot(u, v)
    coslat = np.cos(np.deg2rad(lat))
    ux = u / np.maximum(sp, 1e-12)
    vy = (v / np.maximum(sp, 1e-12)) / np.maximum(coslat, 1e-3)
    norm = np.hypot(ux, vy)
    ux = ux / np.maximum(norm, 1e-12) * sp
    vy = vy / np.maximum(norm, 1e-12) * sp
    return np.where(sp >= .05, ux, np.nan), np.where(sp >= .05, vy, np.nan)

def bathymetry(ax, lon, lat, depth):
    z = np.ma.masked_invalid(depth)
    ax.pcolormesh(lon, lat, np.ma.masked_where(z <= 0, z), shading="auto",
                  cmap="Blues_r", alpha=.16)
    c100 = ax.contour(lon, lat, np.nan_to_num(depth, nan=0.0),
                      levels=[100], colors="0.25", linestyles="dashed", linewidths=.5)
    c500 = ax.contour(lon, lat, np.nan_to_num(depth, nan=0.0),
                      levels=[500], colors="0.25", linestyles="solid", linewidths=.8)
    for t in ax.clabel(c100, fmt="%d m", fontsize=6, inline=True):
        t.set_clip_on(True); t.set_clip_path(ax.patch)
    for t in ax.clabel(c500, fmt="%d m", fontsize=6, inline=True):
        t.set_clip_on(True); t.set_clip_path(ax.patch)


def tracks(ax, region, year):
    colors = {"FJL_A": "#1b9e77", "NZ_A": "#d95f02", "NZ_B": "#7570b3"}
    for tag, (source, yr, path) in RUNS.items():
        if str(year) != str(yr): continue
        base = tag.rsplit("_", 1)[0]
        color = colors.get(base, "k")
        style = "-" if int(year) == 2020 else "--"
        with xr.open_dataset(path) as ds:
            lon = ds.longitude.values; lat = ds.latitude.values
        ax.plot(lon, lat, color="white", lw=2.0, zorder=4)
        ax.plot(lon, lat, color=color, lw=.85, ls=style, zorder=5)
        ax.scatter(lon[0], lat[0], marker="o", s=24, color=color,
                   edgecolor="white", linewidth=.7, zorder=6)
        status_path = Path(path).parent / "status.log"
        st = status_path.read_text() if status_path.exists() else ""
        marker = "*" if "MELTED" in st else ("X" if "GROUNDED" in st else ("^" if "STRICT" in st else "X"))
        ax.scatter(lon[-1], lat[-1], marker=marker, s=35, color=color,
                   edgecolor="white", linewidth=.7, zorder=6)


def region_axes(ax, region, coastline=True):
    x0, x1, y0, y1 = region[2], region[3], region[0], region[1]
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_xlabel(L("longitude")); ax.set_ylabel(L("latitude"))
    ax.set_facecolor("#d9d9d9"); ax.grid(alpha=.18)
    ax.tick_params(labelsize=8)
    if coastline:
        with xr.open_dataset(STATIC) as ds:
            depth = ds.deptho.values; lon = ds.longitude.values; lat = ds.latitude.values
        bathymetry(ax, lon, lat, depth)
        scale_bar(ax, x1 - .04 * (x1 - x0), y0 + .04 * (y1 - y0),
                  500.0 if (x1 - x0) > 60 else 100.0)


def field_stats(field, lon, lat, stride=8):
    out = []
    for i in range(0, field.shape[0], stride):
        for j in range(0, field.shape[1], stride):
            v = field[i, j]
            if np.isfinite(v):
                out.append((lat[i], lon[j], float(v)))
    return out


# --- Block A -----------------------------------------------------------------
def load_monthly_fields():
    """Load depth slices and monthly means, one monthly file at a time."""
    fields = {}
    meta = None
    for year in YEARS:
        for m in range(1, 13):
            with xr.open_dataset(glorys_path(year, m)) as ds:
                if meta is None:
                    meta = {"lon": ds.longitude.values.astype(float),
                            "lat": ds.latitude.values.astype(float),
                            "depth": ds.depth.values.astype(float)}
                    meta["idx05"] = int(np.argmin(abs(meta["depth"] - .5)))
                    meta["idx100"] = int(np.argmin(abs(meta["depth"] - 100.0)))
                for var in ("thetao", "so", "uo", "vo"):
                    for name, idx in (("05", meta["idx05"]), ("100", meta["idx100"])):
                        key = (year, var, name)
                        fields.setdefault(key, {})[m] = ds[var].isel(depth=idx).mean("time").values.astype("float32")
                if "siconc" in ds:
                    fields.setdefault((year, "siconc", "05"), {})[m] = ds.siconc.mean("time").values.astype("float32")
    return fields, meta


def month_days(year, month):
    return calendar.monthrange(int(year), int(month))[1]


def season_mean(fields, year, var, depth, season):
    months = [m for m in SEASONS[season] if m in fields[(year, var, depth)]]
    arr = np.stack([fields[(year, var, depth)][m] for m in months])
    w = np.asarray([month_days(year, m) for m in months], float)
    return np.average(arr, axis=0, weights=w)


def block_a(lang):
    set_lang(lang)
    root = ensure_dirs("A")
    fields, meta = load_monthly_fields()
    lon, lat = meta["lon"], meta["lat"]
    with xr.open_dataset(STATIC) as ds:
        deptho = ds.deptho.values

    specs = [("speed", "speed"), ("thetao", "temperature"), ("so", "salinity")]
    for var, label in specs:
        for depth in ("05", "100"):
            for region_name, region in REGIONS.items():
                fig, axs = plt.subplots(3, 2, figsize=(7.1, 8.6), squeeze=False)
                for r, season in enumerate(("annual", "winter", "summer")):
                    for c, year in enumerate(YEARS):
                        ax = axs[r, c]
                        if var == "speed":
                            u = season_mean(fields, year, "uo", depth, season)
                            v = season_mean(fields, year, "vo", depth, season)
                            val = np.hypot(u, v)
                        else:
                            val = season_mean(fields, year, var, depth, season)
                        region_axes(ax, region)
                        ext = "both"
                        if var == "speed":
                            cmap = "viridis"; vmin, vmax = 0, .5; lab = L("speed"); ext = "max"
                        elif var == "thetao":
                            cmap = "RdYlBu_r"; vmin, vmax = -2, 12 if depth == "05" else 8
                            lab = L("temperature"); ext = "max"
                        else:
                            cmap = "Greens"
                            vmin, vmax = (31, 35.5) if depth == "05" else (34, 35.3)
                            lab = L("salinity")
                        m = ax.pcolormesh(lon, lat, np.ma.masked_invalid(val),
                                          shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
                        if var == "speed":
                            nvec = 12 if region_name == "BARENTS" else 14
                            ii = np.linspace(0, len(lat)-1, nvec).astype(int)
                            jj = np.linspace(0, len(lon)-1, nvec).astype(int)
                            yy, xx = np.meshgrid(lat[ii], lon[jj], indexing="ij")
                            uu = u[np.ix_(ii, jj)]; vv = v[np.ix_(ii, jj)]
                            uu, vv = flow_vectors(uu, vv, yy)
                            q = ax.quiver(xx, yy, uu, vv,
                                          color="white", scale=2.0, width=.0025, alpha=.95)
                            if r == 0 and c == 0:
                                ax.quiverkey(q, X=.55, Y=.04, U=.2, label="0.2 m s$^{-1}$",
                                             labelpos="E", fontproperties={"size": 7},
                                             labelcolor="k")
                        if c > 0:
                            ax.set_ylabel(""); ax.tick_params(labelleft=False)
                        if r < 2: ax.set_xlabel("")
                        if region_name != "BARENTS":
                            tracks(ax, region, year)
                        panel(ax, "abcdef"[r * 2 + c])
                        ax.text(.98, .98, f"{year} · {L(season)}", transform=ax.transAxes,
                                ha="right", va="top", fontsize=8,
                                bbox=dict(fc="white", ec="none", alpha=.7))
                fig.subplots_adjust(left=.08, right=.82, bottom=.05, top=.97, wspace=.05, hspace=.10)
                cax = fig.add_axes([.86, .22, .022, .56])
                cb = fig.colorbar(m, cax=cax, extend=ext); cb.set_label(lab)
                axs[0, 0].text(.02, .02, "100 m isobath (≈ 88 m draft)\n500 m isobath",
                               transform=axs[0, 0].transAxes, fontsize=6.5, va="bottom",
                               bbox=dict(fc="white", ec="none", alpha=.8))
                if region_name != "BARENTS":
                    from matplotlib.lines import Line2D
                    hh = []
                    for tag, (_, yr, _) in RUNS.items():
                        base = tag.rsplit("_", 1)[0]
                        hh.append(Line2D([0], [0], color={"FJL_A":"#1b9e77","NZ_A":"#d95f02","NZ_B":"#7570b3"}.get(base,"k"),
                                         ls="-" if int(yr)==2020 else "--", lw=1.0, label=tag))
                    fig.legend(handles=hh, loc="lower center", ncol=3, fontsize=6,
                               frameon=False, bbox_to_anchor=(.5, .005))
                    fig.subplots_adjust(bottom=.12)
                out = root / f"A_{var}_{depth}m_{region_name}"
                save_fig(fig, out)
                rows = []
                for season in ("annual", "winter", "summer"):
                    for year in YEARS:
                        if var == "speed":
                            u = season_mean(fields, year, "uo", depth, season)
                            v = season_mean(fields, year, "vo", depth, season)
                            val = np.hypot(u, v)
                        else:
                            val = season_mean(fields, year, var, depth, season)
                        for la, lo, vv in field_stats(val, lon, lat):
                            rows.append(dict(year=year, season=season, latitude=la,
                                             longitude=lo, value=vv))
                pd.DataFrame(rows).to_csv(out.with_suffix(".csv"), index=False)
                manifest_add(out.with_suffix(".png"), var,
                             "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 202311",
                             "2020, 2024", f"{depth} m (native level)",
                             "annual / Winter (Jan–Mar) / Summer (Jul–Sep); monthly means day-weighted", region_name)

    if ("2020", "siconc", "05") in fields or (2020, "siconc", "05") in fields:
        for region_name, region in REGIONS.items():
            fig, axs = plt.subplots(3, 2, figsize=(7.1, 8.6), squeeze=False)
            m = None
            for r, season in enumerate(("annual", "winter", "summer")):
                for c, year in enumerate(YEARS):
                    ax = axs[r, c]; region_axes(ax, region)
                    val = season_mean(fields, year, "siconc", "05", season)
                    val = np.where(deptho > 0, np.nan_to_num(val, nan=0.0), np.nan)
                    m = ax.pcolormesh(lon, lat, np.ma.masked_invalid(val), shading="auto",
                                      cmap="Blues", vmin=0, vmax=1)
                    if c > 0: ax.set_ylabel(""); ax.tick_params(labelleft=False)
                    if r < 2: ax.set_xlabel("")
                    if region_name != "BARENTS": tracks(ax, region, year)
                    panel(ax, "abcdef"[r * 2 + c])
                    ax.text(.98, .98, f"{year} · {L(season)}", transform=ax.transAxes,
                            ha="right", va="top", fontsize=8,
                            bbox=dict(fc="white", ec="none", alpha=.7))
            fig.subplots_adjust(left=.08, right=.82, bottom=.05, top=.97, wspace=.05, hspace=.10)
            cax = fig.add_axes([.86, .22, .022, .56]); cb = fig.colorbar(m, cax=cax)
            cb.set_label(L("ice"))
            axs[0, 0].text(.02, .02, "100 m isobath (≈ 88 m draft)\n500 m isobath",
                           transform=axs[0, 0].transAxes, fontsize=6.5, va="bottom",
                           bbox=dict(fc="white", ec="none", alpha=.8))
            if region_name != "BARENTS":
                hh = []
                for tag, (_, yr, _) in RUNS.items():
                    base = tag.rsplit("_", 1)[0]
                    hh.append(Line2D([0], [0], color={"FJL_A":"#1b9e77","NZ_A":"#d95f02","NZ_B":"#7570b3"}.get(base,"k"),
                                     ls="-" if int(yr)==2020 else "--", lw=1.0, label=tag))
                fig.legend(handles=hh, loc="lower center", ncol=3, fontsize=6,
                           frameon=False, bbox_to_anchor=(.5, .005))
                fig.subplots_adjust(bottom=.12)
            out = root / f"A_siconc_{region_name}"
            save_fig(fig, out)
            manifest_add(out.with_suffix(".png"), "siconc",
                         "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 202311",
                         "2020, 2024", "surface", "annual / Winter / Summer", region_name)


# --- Block B -----------------------------------------------------------------
def eos80_rho(t, s_psu):
    """UNESCO EOS-80 in-situ density at p=0 [kg m-3]; project EOS-80."""
    t = np.asarray(t, float); s = np.asarray(s_psu, float)
    a0, a1, a2, a3, a4, a5 = 999.842594, 6.793952e-2, -9.095290e-3, 1.001685e-4, -1.120083e-6, 6.536332e-9
    b0, b1, b2, b3, b4 = .824493, -4.0899e-3, 7.6438e-5, -8.2467e-7, 5.3875e-9
    c0, c1, c2, d0 = -5.72466e-3, 1.0227e-4, -1.6546e-6, 4.8314e-4
    return (a0 + (a1 + (a2 + (a3 + (a4 + a5*t)*t)*t)*t)*t
            + (b0 + (b1 + (b2 + (b3 + b4*t)*t)*t)*t)*s
            + (c0 + (c1 + c2*t)*t)*s*np.sqrt(np.maximum(s, 0))
            + d0*s*s)


def sigma0(t, s):
    return eos80_rho(t, s) - 1000.0



def weighted_quantile(v, w, q):
    v = np.asarray(v, float); w = np.asarray(w, float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    v = v[ok]; w = w[ok]
    if v.size == 0: return np.nan
    order = np.argsort(v); v = v[order]; w = w[order]
    c = np.cumsum(w) / np.sum(w)
    return float(np.interp(q, c, v))

def section_array(year, month, var, which):
    with xr.open_dataset(glorys_path(year, month)) as ds:
        da = ds[var]
        if which == "meridional":
            da = da.sel(longitude=40.0, method="nearest").sel(latitude=slice(70.0, 82.0))
            x = da.latitude.values
        else:
            da = da.sel(latitude=76.0, method="nearest").sel(longitude=slice(15.0, 65.0))
            x = da.longitude.values
        z = da.depth.values
        keep = z <= 500.0
        return x, z[keep], da.isel(depth=np.where(keep)[0]).mean("time").values



def nearest_wet(ds, la, lo, max_cells=8):
    surf = ds.thetao.isel(depth=0, time=0).values
    lat = ds.latitude.values; lon = ds.longitude.values
    i0 = int(np.argmin(abs(lat-la))); j0 = int(np.argmin(abs(lon-lo)))
    best = None
    for r in range(max_cells+1):
        for i in range(max(0,i0-r), min(len(lat),i0+r+1)):
            for j in range(max(0,j0-r), min(len(lon),j0+r+1)):
                if np.isfinite(surf[i,j]):
                    d = (lat[i]-la)**2 + (lon[j]-lo)**2
                    if best is None or d < best[0]: best = (d,i,j)
        if best is not None: return best[1],best[2],float(lat[best[1]]),float(lon[best[2]])
    return i0,j0,float(lat[i0]),float(lon[j0])

def block_b(lang):
    set_lang(lang)
    root = ensure_dirs("B")
    for which, xlabel in (("meridional", "latitude [°N]"), ("zonal", "longitude [°E]")):
        for var, cmap, clim, lab in (("thetao", "RdYlBu_r", (-2, 8), L("temperature")),
                                     ("so", "Greens", (30, 36), L("salinity"))):
            fig, axs = plt.subplots(2, 2, figsize=(7.1, 6.2))
            rows = []
            for r, (year, month) in enumerate(((2020, 1), (2020, 7), (2024, 1), (2024, 7))):
                ax = axs.ravel()[r]
                x, z, val = section_array(year, month, var, which)
                m = ax.pcolormesh(x, z, np.ma.masked_invalid(val), shading="auto",
                                  cmap=cmap, vmin=clim[0], vmax=clim[1])
                if var == "thetao":
                    ax.contour(x, z, np.nan_to_num(val, nan=clim[0]),
                               levels=[0.0], colors="k", linewidths=.6)
                ax.set_ylim(500, 0); ax.set_xlabel(xlabel); ax.set_ylabel(L("depth"))
                ax.set_facecolor("#d9d9d9")
                if r in (1, 3): ax.set_ylabel(""); ax.tick_params(labelleft=False)
                ax.grid(alpha=.15); ax.tick_params(labelsize=8)
                panel(ax, "abcd"[r])
                ax.text(.02, .03, f"{year}-{month:02d}", transform=ax.transAxes,
                        ha="left", va="bottom", fontsize=8,
                        bbox=dict(fc="white", ec="none", alpha=.9))
                rows.append(pd.DataFrame({"x": np.repeat(x, len(z)),
                                          "depth": np.tile(z, len(x)),
                                          "value": np.asarray(val).T.ravel(),
                                          "year": year, "month": month}))
            fig.subplots_adjust(left=.09, right=.82, bottom=.10, top=.96, wspace=.18, hspace=.20)
            cax = fig.add_axes([.86, .25, .022, .50])
            cb = fig.colorbar(m, cax=cax, extend="max" if var == "thetao" else "both")
            cb.set_label(lab)
            if var == "thetao":
                fig.text(.12, .02, "0 °C isotherm", fontsize=7)
            out = root / f"B1_{which}_{var}"
            save_fig(fig, out)
            pd.concat(rows).to_csv(out.with_suffix(".csv"), index=False)
            manifest_add(out.with_suffix(".png"), var,
                         "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 202311",
                         "January and July 2020/2024", "native levels 0–500 m",
                         "monthly mean; no vertical interpolation", "BARENTS")

    # B2 profiles at starts
    for point, (la, lo) in POINTS.items():
        profiles = {}
        samples = {}
        for year in YEARS:
            # Select one wet column per point/year and reuse it for both seasons.
            with xr.open_dataset(glorys_path(year, 1)) as ds:
                ii, jj, latw, lonw = nearest_wet(ds, la, lo)
                samples[year] = (latw, lonw, float(ds.depth.values[-1]))
            for season in ("winter", "summer"):
                vals = []
                for m in SEASONS[season]:
                    with xr.open_dataset(glorys_path(year, m)) as ds:
                        t = ds.thetao.isel(latitude=ii, longitude=jj)
                        so = ds["so"].isel(latitude=ii, longitude=jj)
                        z = t.depth.values; keep = z <= 300.0
                        vals.append((t.isel(depth=np.where(keep)[0]).mean("time").values,
                                     so.isel(depth=np.where(keep)[0]).mean("time").values))
                w = np.asarray([month_days(year, m) for m in SEASONS[season]], float)
                profiles[(year, season)] = (z[keep],
                                            np.average([v[0] for v in vals], axis=0, weights=w),
                                            np.average([v[1] for v in vals], axis=0, weights=w))
        fig, axs = plt.subplots(2, 3, figsize=(7.1, 6.4), sharey=True)
        for r, year in enumerate(YEARS):
            for c, kind in enumerate(("T", "S", "sigma")):
                ax = axs[r, c]
                for season, color in (("winter", "C0"), ("summer", "C3")):
                    z, t, s = profiles[(year, season)]
                    if kind == "T": y = t; lab = L("temperature")
                    elif kind == "S": y = s; lab = L("salinity")
                    else: y = sigma0(t, s); lab = "σ₀ [kg m$^{-3}$]"
                    ax.plot(y, z, color=color, label=L(season))
                ax.set_ylim(300, 0); ax.set_xlabel(lab); ax.grid(alpha=.2)
                ax.xaxis.set_major_locator(plt.MaxNLocator(3))
                if c == 0: ax.set_ylabel(L("depth"))
        # Shared x range in each S/sigma column across 2020 and 2024.
        for c in (1, 2):
            lo_x = min(axs[r, c].get_xlim()[0] for r in range(2))
            hi_x = max(axs[r, c].get_xlim()[1] for r in range(2))
            for r in range(2): axs[r, c].set_xlim(lo_x, hi_x)
        for i, ax in enumerate(axs.ravel()): panel(ax, "abcdef"[i])
        fig.text(.025, .72, "2020", rotation=90, va="center", ha="center", fontsize=9)
        fig.text(.025, .25, "2024", rotation=90, va="center", ha="center", fontsize=9)
        handles, labels = axs[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8, frameon=False)
        fig.subplots_adjust(left=.16, right=.88, bottom=.19, top=.96, wspace=.24, hspace=.25)
        out = root / f"B2_profile_{point}"
        save_fig(fig, out)
        rows = []
        for (year, season), (z, t, s) in profiles.items():
            for zz, tt, ss in zip(z, t, s):
                rows.append(dict(year=year, season=season, depth=zz, T=tt, S=ss,
                                 sigma0=float(sigma0(tt, ss)),
                                 sample_latitude=samples[year][0], sample_longitude=samples[year][1]))
        pd.DataFrame(rows).to_csv(out.with_suffix(".csv"), index=False)
        pd.DataFrame([dict(year=y, latitude=s[0], longitude=s[1], depth=s[2])
                      for y, s in samples.items()]).to_csv(root / f"B2_sample_{point}.csv", index=False)
        manifest_add(out.with_suffix(".png"), "thetao, so, sigma0",
                     "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 202311",
                     "Winter/Summer 2020, 2024",
                     "0–300 m; nearest wet column " + "; ".join(
                         f"{y}: {v[0]:.4f}N {v[1]:.4f}E" for y, v in samples.items()),
                     "monthly mean profiles; fixed wet column per year", point)

    # B3 Barents mean profiles / percentiles
    print("B3 start", flush=True)
    for var in ("thetao", "so"):
        print("B3", var, flush=True)
        data = {}
        for year in YEARS:
            vals = []
            for m in range(1, 13):
                with xr.open_dataset(glorys_path(year, m)) as ds:
                    z = ds.depth.values; lat = ds.latitude.values; keep = z <= 300.0
                    a = ds[var].isel(depth=np.where(keep)[0]).mean("time").values.astype("float32")
                    vals.append(a)
            stack = np.stack(vals, axis=0)
            wlat = np.cos(np.deg2rad(lat))[None, :, None]
            wdays = np.asarray([month_days(year, m) for m in range(1, 13)], float)[:, None, None]
            ww = wlat * wdays
            means, q10, q90 = [], [], []
            for k in range(stack.shape[1]):
                v = stack[:, k, :, :].ravel()
                w = np.broadcast_to(ww, stack[:, k, :, :].shape).ravel()
                ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
                vv = v[ok]; wv = w[ok]
                means.append(float(np.average(vv, weights=wv)) if vv.size else np.nan)
                q10.append(weighted_quantile(vv, wv, .10))
                q90.append(weighted_quantile(vv, wv, .90))
            data[year] = (z[keep], np.asarray(means), np.asarray(q10), np.asarray(q90))
        fig, ax = plt.subplots(figsize=(4.2, 4.2))
        for year, color in zip(YEARS, ("C0", "C3")):
            z, mean, lo, hi = data[year]
            ax.fill_betweenx(z, lo, hi, color=color, alpha=.15)
            ax.plot(mean, z, color=color, label=str(year))
        ax.set_ylim(300, 0); ax.set_xlabel(L("temperature") if var == "thetao" else L("salinity"))
        ax.set_ylabel(L("depth")); ax.legend(fontsize=8); ax.grid(alpha=.2)
        panel(ax, "a")
        fig.subplots_adjust(left=.20,right=.86,bottom=.15,top=.95)
        out = root / f"B3_BARENTS_{var}"
        save_fig(fig, out)
        pd.DataFrame({"depth": data[2020][0], "mean_2020": data[2020][1],
                      "p10_2020": data[2020][2], "p90_2020": data[2020][3],
                      "mean_2024": data[2024][1], "p10_2024": data[2024][2],
                      "p90_2024": data[2024][3]}).to_csv(out.with_suffix(".csv"), index=False)
        manifest_add(out.with_suffix(".png"), var,
                     "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 202311",
                     "2020, 2024", "0–300 m native levels",
                     "annual mean and 10–90 percentiles over BARENTS", "BARENTS")


# --- Block V -----------------------------------------------------------------
def track_daily(path):
    with xr.open_dataset(path) as ds:
        t = np.asarray(ds.time.values, float) / 86400.0
        day = np.floor(t + 1e-9).astype(int)
        last = np.r_[np.where(np.diff(day))[0], len(day) - 1]
        return pd.DataFrame(dict(day=t[last], lat=ds.latitude.values[last],
                                 lon=ds.longitude.values[last]))


def sample_forcing():
    rows = {}
    for tag, (source, year, path) in RUNS.items():
        df = track_daily(path)
        t = df.day.values; date = pd.Timestamp(f"{year}-01-01") + pd.to_timedelta(t, unit="D")
        df["date"] = date
        for m in range(1, 13):
            mm = df[df.date.dt.month == m]
            if mm.empty: continue
            with xr.open_dataset(era5_path(year, m)) as e:
                for i, r in mm.iterrows():
                    t2 = float(e.t2m.sel(time=np.datetime64(r.date), latitude=r.lat,
                                          longitude=r.lon, method="nearest")) - 273.15
                    u = float(e.u10.sel(time=np.datetime64(r.date), latitude=r.lat,
                                         longitude=r.lon, method="nearest"))
                    v = float(e.v10.sel(time=np.datetime64(r.date), latitude=r.lat,
                                         longitude=r.lon, method="nearest"))
                    p = float(e.msl.sel(time=np.datetime64(r.date), latitude=r.lat,
                                         longitude=r.lon, method="nearest")) / 100.0
                    df.loc[i, ["t2m", "wind", "msl"]] = [t2, np.hypot(u, v), p]
            with xr.open_dataset(glorys_path(year, m)) as o:
                for i, r in mm.iterrows():
                    kw = dict(latitude=r.lat, longitude=r.lon, method="nearest")
                    T = float(o.thetao.sel(time=np.datetime64(r.date), depth=0.494025, **kw))
                    S = float(o["so"].sel(time=np.datetime64(r.date), depth=0.494025, **kw))
                    uu = float(o.uo.sel(time=np.datetime64(r.date), depth=0.494025, **kw))
                    vv = float(o.vo.sel(time=np.datetime64(r.date), depth=0.494025, **kw))
                    df.loc[i, ["Tw", "Sw", "current"]] = [T, S, np.hypot(uu, vv)]
        rows[tag] = df
    return rows


def block_v(lang):
    set_lang(lang)
    root = ensure_dirs("V")
    rows = sample_forcing()
    cols = ["t2m", "wind", "msl", "Tw", "Sw", "current"]
    heads = ["T$_{2m}$ [°C]", "wind [m s$^{-1}$]", "MSL [hPa]",
             "T water [°C]", "S water [psu]", "current [m s$^{-1}$]"]
    frames = []
    for tag, df in rows.items():
        d = df[["day", "t2m", "wind", "msl", "Tw", "Sw", "current"]].copy()
        d.insert(0, "run", tag); frames.append(d)
        d.to_csv(root / f"V1_{tag}.csv", index=False)
    pd.concat(frames).to_csv(root / "V1_all.csv", index=False)

    for name, ccols, cheads in (
        ("atmosphere", ["t2m", "wind", "msl"], ["T$_{2m}$ [°C]", "wind [m s$^{-1}$]", "sea-level pressure [hPa]"]),
        ("ocean", ["Tw", "Sw", "current"], ["T water [°C]", "S water [psu]", "current [m s$^{-1}$]"]),
    ):
        fig, axs = plt.subplots(6, 3, figsize=(7.1, 10.5), sharex="col", squeeze=False)
        for r, (tag, df) in enumerate(rows.items()):
            for c, (col, head) in enumerate(zip(ccols, cheads)):
                ax = axs[r, c]
                ax.plot(df.day, df[col], color="C0", lw=.8)
                ax.grid(alpha=.2); ax.tick_params(labelsize=8)
                if r == 0: ax.set_title(head, fontsize=8)
                if c == 0: ax.set_ylabel(tag, fontsize=8)
                if r == 5: ax.set_xlabel(L("days"), fontsize=8)
                panel(ax, "abcdefghijklmnopqr"[r * 3 + c])
        fig.subplots_adjust(left=.17, right=.90, bottom=.08, top=.93, wspace=.35, hspace=.14)
        out = root / f"V1_track_forcing_{name}"
        save_fig(fig, out)
        manifest_add(out.with_suffix(".png"), ",".join(ccols),
                     "ERA5 daily; GLORYS12 monthly surface",
                     "along 2020/2024 runs", "2 m/10 m/surface 0.494 m",
                     "nearest track sample", "BARENTS")
    # remove the old 6x6 artifact from the collection
    old = root / "V1_track_forcing.png"
    if old.exists(): old.unlink()
    old = root / "V1_track_forcing.pdf"
    if old.exists(): old.unlink()

    # V2 area mean annual cycle
    years = {}
    for year in YEARS:
        mrows = []
        for m in range(1, 13):
            with xr.open_dataset(era5_path(year, m)) as e:
                # cos(latitude) area weights; ERA5 latitude is descending
                w = np.cos(np.deg2rad(e.latitude))
                mask = ocean_mask_on(e.latitude.values, e.longitude.values)
                t2 = float(e.t2m.where(mask).weighted(w).mean()) - 273.15
                wind = float(np.hypot(e.u10, e.v10).where(mask).weighted(w).mean())
            with xr.open_dataset(glorys_path(year, m)) as o:
                w = np.cos(np.deg2rad(o.latitude))
                T = float(o.thetao.isel(depth=0).weighted(w).mean())
            mrows.append(dict(month=m, t2m=t2, wind=wind, Tw=T))
        years[year] = pd.DataFrame(mrows)
    fig, axs = plt.subplots(3, 2, figsize=(7.1, 6.2), sharex=True)
    for c, year in enumerate(YEARS):
        d = years[year]
        for r, (col, lab) in enumerate((("t2m", "T$_{2m}$ [°C]"),
                                        ("wind", "wind [m s$^{-1}$]"),
                                        ("Tw", "T water [°C]"))):
            ax = axs[r, c]; ax.plot(d.month, d[col], "o-", ms=3, color="C0")
            ax.set_ylabel(lab); ax.grid(alpha=.2); ax.tick_params(labelsize=8)
            ax.text(.98, .08, str(year), transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=8)
            panel(ax, "abcdef"[r * 2 + c])
            if r == 2: ax.set_xlabel("month")
            ax.set_xticks(range(1, 13))
            ax.set_xticklabels(list("JFMAMJJASOND"), fontsize=8)
    # shared y limits for each variable row
    for r in range(3):
        lo = min(axs[r, c].get_ylim()[0] for c in range(2))
        hi = max(axs[r, c].get_ylim()[1] for c in range(2))
        for c in range(2): axs[r, c].set_ylim(lo, hi)
    fig.subplots_adjust(left=.12, right=.92, bottom=.15, top=.96, wspace=.32, hspace=.28)
    out = root / "V2_BARENTS_annual_cycle"
    save_fig(fig, out)
    for year in YEARS: years[year].to_csv(root / f"V2_{year}.csv", index=False)
    manifest_add(out.with_suffix(".png"), "t2m,wind,thetao", "ERA5; GLORYS12",
                 "2020, 2024", "2 m/10 m/surface", "monthly ocean-cell area mean, 63–86N 5–80E", "BARENTS")

    # V3 maps mean wind and Tair winter/summer
    for var, cmap, clim, lab in (("wind", "viridis", (2, 12), "wind [m s$^{-1}$]"),
                                 ("t2m", "RdYlBu_r", (-30, 12), "T$_{2m}$ [°C]")):
        fig, axs = plt.subplots(2, 2, figsize=(7.1, 6.2))
        vrows = []
        for i, (season, year) in enumerate((("winter", 2020), ("summer", 2020),
                                            ("winter", 2024), ("summer", 2024))):
            ax = axs.ravel()[i]
            vals = []; uvals = []; vvals = []
            for m in SEASONS[season]:
                with xr.open_dataset(era5_path(year, m)) as e:
                    lon = e.longitude.values; lat = e.latitude.values
                    w = np.cos(np.deg2rad(e.latitude))
                    if var == "wind":
                        vals.append(np.hypot(e.u10, e.v10).weighted(w).mean("time").values)
                        uvals.append(e.u10.weighted(w).mean("time").values)
                        vvals.append(e.v10.weighted(w).mean("time").values)
                    else:
                        vals.append((e.t2m.weighted(w).mean("time") - 273.15).values)
            ww = np.asarray([month_days(year, m) for m in SEASONS[season]], float)
            v = np.average(np.stack(vals), axis=0, weights=ww)
            mesh = ax.pcolormesh(lon, lat, v, shading="auto", cmap=cmap, vmin=clim[0], vmax=clim[1])
            if var == "wind":
                step_lat = max(1, len(lat)//12); step_lon = max(1, len(lon)//12)
                yy, xx = np.meshgrid(lat[::step_lat], lon[::step_lon], indexing="ij")
                uu = np.average(np.stack(uvals), axis=0, weights=ww)[::step_lat, ::step_lon]
                vv = np.average(np.stack(vvals), axis=0, weights=ww)[::step_lat, ::step_lon]
                uu, vv = flow_vectors(uu, vv, yy)
                q = ax.quiver(xx, yy, uu, vv, color="k", scale=18,
                              width=.002, alpha=.8)
                if i == 0:
                    ax.quiverkey(q, X=.18, Y=.04, U=5.0, label="5 m s$^{-1}$", labelpos="E",
                                 fontproperties={"size": 7}, labelcolor="k")
            for la, lo, vv in field_stats(v, lon, lat):
                vrows.append(dict(year=year, season=season, latitude=la, longitude=lo, value=vv))
            ax.set_xlim(5, 80); ax.set_ylim(63, 86); ax.set_xlabel(L("longitude"))
            ax.set_ylabel(L("latitude")); ax.tick_params(labelsize=8); ax.grid(alpha=.15)
            ax.set_facecolor("#d9d9d9")
            with xr.open_dataset(STATIC) as st:
                glon = st.longitude.values; glat = st.latitude.values; gdep = st.deptho.values
            ax.contour(glon, glat, np.nan_to_num(gdep, nan=0.0), levels=[0.5],
                       colors="0.25", linewidths=.4)
            ax.contour(glon, glat, np.nan_to_num(gdep, nan=0.0), levels=[100],
                       colors="0.25", linestyles="dashed", linewidths=.4)
            ax.contour(glon, glat, np.nan_to_num(gdep, nan=0.0), levels=[500],
                       colors="0.25", linestyles="solid", linewidths=.7)
            scale_bar(ax, 78, 64.5, 500.0)
            if i % 2:
                ax.set_ylabel(""); ax.tick_params(labelleft=False)
            panel(ax, "abcd"[i]); ax.text(.98, .98, f"{year} · {L(season)}",
                                          transform=ax.transAxes, ha="right", va="top",
                                          fontsize=8, bbox=dict(fc="white", ec="none", alpha=.7))
        fig.subplots_adjust(left=.08, right=.82, bottom=.15, top=.96, wspace=.15, hspace=.20)
        cax = fig.add_axes([.86, .28, .022, .44]); cb = fig.colorbar(mesh, cax=cax, extend="max" if var == "wind" else "both"); cb.set_label(lab)
        out = root / f"V3_{var}_BARENTS"
        save_fig(fig, out)
        pd.DataFrame(vrows).to_csv(out.with_suffix(".csv"), index=False)
        manifest_add(out.with_suffix(".png"), var, "ERA5",
                     "2020, 2024", "2 m/10 m", "Winter/Summer mean", "BARENTS")


# --- Block G -----------------------------------------------------------------
def block_g(lang):
    set_lang(lang)
    root = ensure_dirs("G")
    frames = []
    for tag, (_, year, path) in RUNS.items():
        csv = FIG / "V" / f"V1_{tag}.csv"
        if csv.exists():
            d = pd.read_csv(csv)
            if "run" not in d: d.insert(0, "run", tag)
            if "year" not in d: d.insert(1, "year", year)
            frames.append(d)
    if not frames:
        raise RuntimeError("run V first: V1 CSVs are required for block G")
    df = pd.concat(frames, ignore_index=True)
    specs = [("Tw", "T water 0.5 m [°C]"), ("current", "current 0.5 m [m s$^{-1}$]"),
             ("wind", "wind 10 m [m s$^{-1}$]")]
    fig, axs = plt.subplots(3, 2, figsize=(7.1, 6.4), squeeze=False)
    for r, (col, lab) in enumerate(specs):
        allv = pd.concat([df.loc[df.year == year, col] for year in YEARS]).dropna()
        bins = np.histogram_bin_edges(allv, bins=24)
        for c, year in enumerate(YEARS):
            ax = axs[r, c]
            v = df.loc[df.year == year, col].dropna()
            ax.hist(v, bins=bins, color="C0", alpha=.8,
                    weights=np.full(len(v), 100.0/len(v)))
            ax.set_xlabel(lab); ax.set_ylabel("frequency [%]"); ax.grid(alpha=.2)
            ax.tick_params(labelsize=8)
            panel(ax, "abcdef"[r * 2 + c])
            ax.text(.98, .95, str(year), transform=ax.transAxes, ha="right", va="top",
                    fontsize=8)
            ax.text(.98, .88, f"N={len(v)}", transform=ax.transAxes, ha="right", va="top",
                    fontsize=7)
    for r in range(3):
        lo = min(axs[r, c].get_ylim()[0] for c in range(2))
        hi = max(axs[r, c].get_ylim()[1] for c in range(2))
        for c in range(2): axs[r, c].set_ylim(lo, hi)
    fig.subplots_adjust(left=.14, right=.94, bottom=.16, top=.96, wspace=.30, hspace=.38)
    out = root / "G1_track_histograms"
    save_fig(fig, out)
    manifest_add(out.with_suffix(".png"), "Tw,current,wind", "V1 track samples",
                 "2020, 2024", "water/current 0.5 m; wind 10 m", "relative frequency over track points", "BARENTS")

    rows = []
    for year in YEARS:
        for col, lab in (("Tw", "T_water_C"), ("current", "current_m_s"),
                         ("wind", "wind_m_s")):
            v = df.loc[df.year == year, col].dropna()
            rows.append(dict(year=year, variable=lab, mean=v.mean(), min=v.min(),
                             max=v.max(), std=v.std(), n=len(v)))
    stats = pd.DataFrame(rows); stats.to_csv(root / "G2_track_statistics.csv", index=False)
    cols = ["year", "variable", "mean", "min", "max", "std", "n"]
    lines = [r"\begin{tabular}{r l r r r r r}", r"\hline",
             r"Year & Variable & Mean & Min & Max & SD & N \\", r"\hline"]
    for _, row in stats.iterrows():
        lines.append(f"{int(row['year'])} & {row['variable']} & {row['mean']:.3f} & "
                     f"{row['min']:.3f} & {row['max']:.3f} & {row['std']:.3f} & {int(row['n'])} \\\\")
    lines += [r"\hline", r"\end{tabular}", ""]
    (root / "G2_track_statistics.tex").write_text("\n".join(lines))


# --- Block 0 -----------------------------------------------------------------
def block0(lang):
    """English copy of the Stage 12.20 panel; Russian originals stay in final/ru."""
    set_lang(lang)
    final = ROOT / "docs/wiki/stages/stage12/figures/stage12.20/final"
    ru = final / "ru"
    if not ru.exists():
        shutil.copytree(final, ru)
    # English re-render is delegated to the Stage 12.20 plotter, which owns the
    # data and the exact panel layout.  It is invoked with a temporary argv so
    # this script remains the single Stage 12.21 entry point.
    import importlib.util
    p = ROOT / "python/analysis/stage12.20_figures.py"
    spec = importlib.util.spec_from_file_location("s1220_en", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.LANG = "en"
    old = sys.argv
    try:
        sys.argv = ["stage12.21", "--fig-dir", str(final)]
        m.main_all()
    finally:
        sys.argv = old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", required=True, choices=["0", "A", "B", "V", "G"])
    ap.add_argument("--lang", default="en", choices=["en", "ru"])
    a = ap.parse_args()
    {"0": block0, "A": block_a, "B": block_b, "V": block_v, "G": block_g}[a.block](a.lang)


if __name__ == "__main__":
    main()
