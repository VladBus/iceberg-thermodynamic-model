#!/usr/bin/env python3
"""Stage 12.22: Enderlin23 model/observation validation (no model runs).

The script post-processes the existing Stage 12.15 prescribed-trajectory
Enderlin23 hindcast.  It never changes model physics or coefficients and never
launches ``iceberg_run``.  The validation target is the observed submarine
melt rate, in m/day; the model quantity is the same submarine total
(basal+lateral+wave), divided by ice density, mean wetted area and duration.

Outputs
-------
- docs/wiki/stages/stage12/evidence/stage12.22/matched_cases.csv
- docs/wiki/stages/stage12/evidence/stage12.22/metrics.csv
- docs/wiki/stages/stage12/evidence/stage12.22/metrics_by_region.csv
- docs/wiki/stages/stage12/figures/stage12.22/*.png
- data/validation/stage12.22/journal_pdf_vectors.zip (PDF vectors, outside git)
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
OBS = ROOT / "data/validation/observations/enderlin23/enderlin23_per_iceberg.csv"
RES = ROOT / "data/validation/stage12.15/enderlin_current2/enderlin23_hindcast_results.csv"
RUNS = ROOT / "data/validation/stage12.15/enderlin_current2"
MAN = ROOT / "data/validation/stage12.15/enderlin_trajectory_manifest.csv"
FIG = ROOT / "docs/wiki/stages/stage12/figures/stage12.22"
EVID = ROOT / "docs/wiki/stages/stage12/evidence/stage12.22"
PDF = ROOT / "data/validation/stage12.22/pdf"
ARCHIVE = ROOT / "data/validation/stage12.22/journal_pdf_vectors.zip"
SEED = 122022
NBOOT = 5000
RHO_ICE = 910.0  # must match src/iceberg_types.f90
REGIONS = ("WAP", "WAIS")
SITE_LABEL = {"BG": "BG", "CG": "CG", "HG": "HG", "LG": "LG",
              "SG": "SG", "TG": "TG", "WG": "WG"}
# All cases + two regions + five largest sites = 8 Taylor points.
TAYLOR_KEYS = ("All", "WAP", "WAIS", "CG", "HG", "SG", "TG", "WG")


def submarine_rate(basal, lateral, wave, mean_wet_area, seconds, rho=RHO_ICE):
    """Submarine melt rate [m/day] from total component masses [kg]."""
    return (np.asarray(basal, float) + np.asarray(lateral, float) + np.asarray(wave, float)) / float(rho) / (
        np.asarray(mean_wet_area, float) * np.asarray(seconds, float)) * 86400.0


def taylor_xy(r, sigma_ratio):
    """Cartesian Taylor coordinates: sigma*r, sigma*sqrt(1-r^2)."""
    r = np.clip(np.asarray(r, float), -1.0, 1.0)
    s = np.asarray(sigma_ratio, float)
    return s * r, s * np.sqrt(np.maximum(0.0, 1.0 - r * r))


def ensure_dirs():
    for p in (FIG, EVID, PDF):
        p.mkdir(parents=True, exist_ok=True)


def load_data():
    obs = pd.read_csv(OBS)
    obs["independent_case"] = obs["independent_case"].astype(bool)
    obs = obs[(obs.independent_case) & (obs.time_separation_days <= 120.0)].copy()
    res = pd.read_csv(RES)
    man = pd.read_csv(MAN)
    if len(obs) != 190:
        raise RuntimeError(f"expected 190 duration-filtered cases, got {len(obs)}")
    if len(res) != 190:
        raise RuntimeError(f"expected 190 hindcast rows, got {len(res)}")
    cols = ["case_id", "site", "region", "date_start", "date_end", "time_separation_days",
            "independence_group", "site_name", "melt_definition", "melt_rate",
            "volume_change_rate", "volume_change_uncert", "draft", "surface_area",
            "submerged_area"]
    d = res.merge(obs[cols], on="case_id", how="inner", suffixes=("_res", ""))
    if len(d) != 190:
        raise RuntimeError(f"merge lost cases: {len(d)}")
    if not (d.site_res == d.site).all() or not (d.region_res == d.region).all():
        raise RuntimeError("result/observation site or region mismatch")
    d = d.drop(columns=["site_res", "region_res"])
    m = man.set_index("case_id")
    d["H0_rule"] = d.case_id.map(m.H0_rule)
    d["obs_rate"] = d.melt_rate.astype(float)
    d["obs_unc"] = d.volume_change_uncert.abs() / d.submerged_area
    d["obs_rate_check"] = d.volume_change_rate / d.submerged_area
    # Recompute from the mass-loss components with the Fortran density.
    # The old modeled_melt_rate_voxel column used 916.7 kg/m3 and is retained
    # only as provenance; it is not the validation value.
    d["model_rate_legacy_9167"] = d.modeled_melt_rate_voxel.astype(float)
    d["model_rate"] = submarine_rate(d.mass_loss_basal_voxel, d.mass_loss_lateral_voxel,
                                     d.mass_loss_wave_voxel, d.mean_a_wet_voxel,
                                     d.seconds_voxel)
    d["model_rate_check"] = d.model_rate
    d["ratio"] = d.model_rate / d.obs_rate
    d["log10_ratio"] = np.log10(d.ratio)
    d["delta_t"] = d.mean_delta_t_voxel.astype(float)
    d["duration_days"] = d.time_separation_days.astype(float)
    d["size_m"] = np.sqrt(d.surface_area.astype(float))
    d["final_mass_pct"] = np.nan
    d["early_stop"] = d.status.ne("OK")
    for i, row in d.iterrows():
        p = RUNS / f"{row.case_id}_voxel.nc"
        if not p.exists():
            continue
        with xr.open_dataset(p) as ds:
            mass = np.asarray(ds.mass.values, float)
        if len(mass) >= 2 and mass[0] > 0:
            d.at[i, "final_mass_pct"] = 100.0 * mass[-1] / mass[0]
            if d.at[i, "final_mass_pct"] < 1.0:
                d.at[i, "early_stop"] = True
    # Numeric integrity checks against the stored hindcast outputs.
    if not np.allclose(d.obs_rate, d.obs_rate_check, rtol=1e-10, atol=1e-12):
        raise RuntimeError("observed melt_rate is not volume_change_rate/submerged_area")
    if not np.allclose(d.model_rate, d.model_rate_check, rtol=1e-8, atol=1e-12, equal_nan=True):
        raise RuntimeError("model melt_rate does not reproduce from stored mass losses")
    if not d.melt_definition.eq("SUBMARINE_TOTAL").all():
        raise RuntimeError("unexpected observation melt definition")
    d["case_id"] = d.case_id.astype(str)
    d["group"] = d.independence_group.astype(str).str.replace("ENDERLIN23_", "", regex=False)
    return d


def base_stats(o, m, sig):
    o = np.asarray(o, float); m = np.asarray(m, float); sig = np.asarray(sig, float)
    good = np.isfinite(o) & np.isfinite(m) & np.isfinite(sig) & (o > 0) & (m > 0)
    o, m, sig = o[good], m[good], sig[good]
    n = int(len(o))
    if n < 3:
        return {"n": n, "ci_status": "insufficient"}, o, m, sig
    lo = np.log10(o); lm = np.log10(m)
    out = {"n": n}
    out["obs_median"] = float(np.median(o)); out["model_median"] = float(np.median(m))
    out["obs_mean"] = float(np.mean(o)); out["model_mean"] = float(np.mean(m))
    out["bias"] = float(np.mean(m - o))
    out["median_ratio"] = float(np.median(m / o))
    out["mean_log10_ratio"] = float(np.mean(lm - lo))
    out["sd_log10_ratio"] = float(np.std(lm - lo, ddof=1))
    out["mae"] = float(np.mean(np.abs(m - o)))
    out["rmse"] = float(np.sqrt(np.mean((m - o) ** 2)))
    out["mae_log10"] = float(np.mean(np.abs(lm - lo)))
    out["rmse_log10"] = float(np.sqrt(np.mean((lm - lo) ** 2)))
    out["pearson_linear"] = float(stats.pearsonr(m, o).statistic)
    out["pearson_log10"] = float(stats.pearsonr(lm, lo).statistic)
    out["spearman"] = float(stats.spearmanr(m, o).statistic)
    out["kendall"] = float(stats.kendalltau(m, o).statistic)
    so = np.std(o, ddof=1); smo = np.std(m, ddof=1)
    slo = np.std(lo, ddof=1); slm = np.std(lm, ddof=1)
    out["sigma_model_over_obs"] = float(smo / so) if so > 0 else np.nan
    out["sigma_model_over_obs_log10"] = float(slm / slo) if slo > 0 else np.nan
    out["crmse_over_sigma_obs"] = float(np.sqrt(np.mean(((m - m.mean()) - (o - o.mean())) ** 2)) / so)
    out["crmse_over_sigma_obs_log10"] = float(np.sqrt(np.mean(((lm - lm.mean()) - (lo - lo.mean())) ** 2)) / slo)
    out["obs_sigma"] = float(so); out["model_sigma"] = float(smo)
    out["obs_sigma_log10"] = float(slo); out["model_sigma_log10"] = float(slm)
    return out, o, m, sig


def noise_ceiling(o, sig, log10_space):
    """Reliability ceiling from independent additive observation errors.

    This is *not* a strict upper bound for a real model: it assumes
    independent Gaussian errors with the supplied 1-sigma magnitudes and no
    correlated/representativeness error.  It answers how much of the observed
    variance is reproducible in principle under those assumptions.

    linear: sqrt(max(0, 1 - mean(sigma**2) / var(obs)))
    log10:  sigma_log = sigma/(obs*ln(10)), then the same formula on log10(obs).
    """
    o = np.asarray(o, float); sig = np.asarray(sig, float)
    good = np.isfinite(o) & np.isfinite(sig) & (o > 0)
    o, sig = o[good], sig[good]
    if len(o) < 3:
        return np.nan
    if log10_space:
        x = np.log10(o); sx = sig / (o * np.log(10.0))
    else:
        x = o; sx = sig
    v = float(np.var(x, ddof=1))
    if not np.isfinite(v) or v <= 0:
        return np.nan
    return float(np.sqrt(max(0.0, 1.0 - float(np.mean(sx * sx)) / v)))


def bootstrap_stats(o, m, sig, groups, seed, nboot=NBOOT):
    groups = np.asarray(groups, dtype=object)
    uniq = np.array(sorted(set(groups.tolist())), dtype=object)
    out = {"n_groups": int(len(uniq)), "ci_status": "ok" if len(uniq) > 1 else "single_cluster"}
    if len(uniq) < 2:
        return out
    idx = {g: np.where(groups == g)[0] for g in uniq}
    rng = np.random.default_rng(seed)
    keys = ["bias", "median_ratio", "mean_log10_ratio", "sd_log10_ratio", "mae", "rmse",
            "mae_log10", "rmse_log10", "pearson_linear", "pearson_log10", "spearman",
            "kendall", "sigma_model_over_obs", "sigma_model_over_obs_log10",
            "crmse_over_sigma_obs", "crmse_over_sigma_obs_log10"]
    draws = {k: [] for k in keys}
    taylor_log = []
    taylor_linear = []
    for _ in range(nboot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ix = np.concatenate([idx[g] for g in pick])
        b, _, _, _ = base_stats(o[ix], m[ix], sig[ix])
        if b.get("n", 0) < 3:
            continue
        for k in keys:
            draws[k].append(b.get(k, np.nan))
        sl = b["sigma_model_over_obs_log10"]; rl = b["pearson_log10"]
        taylor_log.append((sl * rl, sl * np.sqrt(max(0.0, 1.0 - rl ** 2))))
        s0 = b["sigma_model_over_obs"]; r0 = b["pearson_linear"]
        taylor_linear.append((s0 * r0, s0 * np.sqrt(max(0.0, 1.0 - r0 ** 2))))
    for k in keys:
        a = np.asarray(draws[k], float)
        out[f"ci_low_{k}"] = float(np.nanpercentile(a, 2.5)) if np.isfinite(a).any() else np.nan
        out[f"ci_high_{k}"] = float(np.nanpercentile(a, 97.5)) if np.isfinite(a).any() else np.nan
    for label, vals in (("taylor_log", taylor_log), ("taylor_linear", taylor_linear)):
        tx = np.asarray([x for x, _ in vals], float); ty = np.asarray([y for _, y in vals], float)
        out[f"ci_low_{label}_x"] = float(np.nanpercentile(tx, 2.5)) if np.isfinite(tx).any() else np.nan
        out[f"ci_high_{label}_x"] = float(np.nanpercentile(tx, 97.5)) if np.isfinite(tx).any() else np.nan
        out[f"ci_low_{label}_y"] = float(np.nanpercentile(ty, 2.5)) if np.isfinite(ty).any() else np.nan
        out[f"ci_high_{label}_y"] = float(np.nanpercentile(ty, 97.5)) if np.isfinite(ty).any() else np.nan
    return out


def compute_stratum(name, d, seed):
    b, o, m, sig = base_stats(d.obs_rate.values, d.model_rate.values, d.obs_unc.values)
    if b.get("n", 0) < 3:
        b["stratum"] = name; b["ci_status"] = "insufficient"; return b
    b.update(bootstrap_stats(o, m, sig, d.independence_group.values, seed))
    b["noise_ceiling_linear"] = noise_ceiling(o, sig, False)
    b["noise_ceiling_log10"] = noise_ceiling(o, sig, True)
    b["stratum"] = name
    return b


def long_rows(name, s):
    rows = []
    for space, suffix in (("linear", ""), ("log10", "_log10")):
        metrics = {
            "bias": ("bias", ""),
            "median_ratio": ("median_ratio", ""),
            "mean_log10_ratio": ("mean_log10_ratio", ""),
            "sd_log10_ratio": ("sd_log10_ratio", ""),
            "mae": ("mae", ""), "rmse": ("rmse", ""),
            "mae_log10": ("mae_log10", ""), "rmse_log10": ("rmse_log10", ""),
            "pearson": ("pearson_linear" if space == "linear" else "pearson_log10", ""),
            "spearman": ("spearman", ""), "kendall": ("kendall", ""),
            "sigma_ratio": ("sigma_model_over_obs" if space == "linear" else "sigma_model_over_obs_log10", ""),
            "crmse_over_sigma_obs": ("crmse_over_sigma_obs" if space == "linear" else "crmse_over_sigma_obs_log10", ""),
        }
        for metric, (key, _) in metrics.items():
            if key not in s:
                continue
            rows.append({"stratum": name, "space": space, "n": s.get("n"),
                         "n_groups": s.get("n_groups"), "metric": metric,
                         "value": s.get(key), "ci_low": s.get(f"ci_low_{key}"),
                         "ci_high": s.get(f"ci_high_{key}"), "ci_status": s.get("ci_status", "ok")})
    for space, key in (("linear", "noise_ceiling_linear"), ("log10", "noise_ceiling_log10")):
        rows.append({"stratum": name, "space": space, "n": s.get("n"),
                     "n_groups": s.get("n_groups"), "metric": "noise_ceiling",
                     "value": s.get(key), "ci_low": np.nan, "ci_high": np.nan,
                     "ci_status": "analytic_reliability"})
    return rows


def plot_taylor(stats_by, space, out_stem):
    suffix = "log10" if space == "log10" else "linear"
    rkey = "pearson_log10" if space == "log10" else "pearson_linear"
    skey = "sigma_model_over_obs_log10" if space == "log10" else "sigma_model_over_obs"
    maxr = max(1.25, max([1.0] + [abs(s.get(skey, np.nan)) for s in stats_by.values() if np.isfinite(s.get(skey, np.nan))]) * 1.12)
    fig, ax = plt.subplots(figsize=(7.0, 6.5))
    ax.set_aspect("equal")
    # radial sigma circles
    th = np.linspace(0, np.pi, 360)
    for sr in np.arange(.25, maxr + .01, .25):
        ax.plot(sr * np.cos(th), sr * np.sin(th), color="0.85", lw=.6, zorder=0)
        if sr <= maxr * .98:
            ax.text(sr * np.cos(1.45), sr * np.sin(1.45), f"{sr:g}", color="0.45",
                    fontsize=6.5, ha="center", va="center")
    # correlation rays and labels on the outer arc
    for rr in (-.8, -.6, -.4, -.2, 0, .2, .4, .6, .8, .9, 1.0):
        ang = np.arccos(np.clip(rr, -1, 1))
        ax.plot([0, maxr * np.cos(ang)], [0, maxr * np.sin(ang)], color="0.92", lw=.5, zorder=0)
        ax.text(maxr * 1.04 * np.cos(ang), maxr * 1.04 * np.sin(ang), f"{rr:g}",
                fontsize=6.5, color="0.35", ha="center", va="center")
    # normalized CRMSE contours (centered RMS difference)
    sg = np.linspace(0, maxr, 220); an = np.linspace(0, np.pi, 220)
    S, A = np.meshgrid(sg, an)
    E = np.sqrt(1.0 + S ** 2 - 2.0 * S * np.cos(A))
    cs = ax.contour(S * np.cos(A), S * np.sin(A), E, levels=[.25, .5, .75, 1.0, 1.5, 2.0],
                    colors="0.55", linewidths=.55, linestyles=":")
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.2g")
    colors = plt.cm.tab10(np.linspace(0, .95, len(TAYLOR_KEYS)))
    markers = ["o", "s", "^", "v", "D", "P", "X", "*"]
    handles = []
    for i, key in enumerate(TAYLOR_KEYS):
        s = stats_by.get(key)
        if not s or not np.isfinite(s.get(rkey, np.nan)) or not np.isfinite(s.get(skey, np.nan)):
            continue
        sn = s[skey]; r = np.clip(s[rkey], -1, 1)
        x, y = taylor_xy(r, sn)
        ax.scatter([x], [y], s=55, marker=markers[i % len(markers)], color=colors[i],
                   edgecolor="white", linewidth=.5, zorder=5)
        tkey = "taylor_log" if space == "log10" else "taylor_linear"
        lo_x, hi_x = s.get(f"ci_low_{tkey}_x"), s.get(f"ci_high_{tkey}_x")
        lo_y, hi_y = s.get(f"ci_low_{tkey}_y"), s.get(f"ci_high_{tkey}_y")
        if all(v is not None and np.isfinite(v) for v in (lo_x, hi_x, lo_y, hi_y)):
            ax.errorbar([x], [y], xerr=[[max(0, x - lo_x)], [max(0, hi_x - x)]],
                        yerr=[[max(0, y - lo_y)], [max(0, hi_y - y)]],
                        fmt="none", ecolor=colors[i], elinewidth=.8, capsize=2, zorder=4)
        handles.append(Line2D([0], [0], marker=markers[i % len(markers)], color="none",
                              markerfacecolor=colors[i], markeredgecolor="white",
                              markersize=6, label=f"{key} (n={s.get('n')})"))
    # observed point on the axis
    ax.scatter([1], [0], marker="*", s=180, color="k", zorder=6, label="Observed")
    # Reliability ceiling: a constant-correlation ray, not a constant-radius arc.
    nc = stats_by["All"].get("noise_ceiling_log10" if space == "log10" else "noise_ceiling_linear", np.nan)
    if np.isfinite(nc):
        ang = np.arccos(np.clip(nc, -1, 1))
        ax.plot([0, maxr * 1.02 * np.cos(ang)], [0, maxr * 1.02 * np.sin(ang)],
                "k--", lw=.9, zorder=2)
        ax.text(maxr * .50, maxr * .50, f"reliability r={nc:.2f}", fontsize=6.5,
                rotation=np.degrees(ang), ha="center", va="center")
    ax.set_xlim(-maxr * 1.05, maxr * 1.05); ax.set_ylim(-.02, maxr * 1.1)
    # Taylor coordinates are sigma*cos(theta), sigma*sin(theta); do not duplicate
    # the radial sigma label on both Cartesian axes.
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(maxr * .98, .06, "σ$_{model}$/σ$_{obs}$", fontsize=7, ha="right",
            va="bottom")
    ax.text(-maxr * 1.00, .06, "marginal 95% CI", fontsize=6.2, ha="left", va="bottom")
    ax.grid(False)
    ax.legend(handles=handles + [Line2D([0], [0], marker="*", color="none", markerfacecolor="k",
                                         markersize=10, label="Observed")],
              loc="center left", bbox_to_anchor=(1.02, .5), fontsize=7, frameon=False)
    fig.subplots_adjust(left=.09, right=.73, bottom=.11, top=.93)
    save_fig(fig, out_stem)
    return out_stem


def cluster_replicate_indices(groups, rng):
    """Indices of a whole-group bootstrap replicate.

    Every selected group contributes *all* of its rows, including rows that
    belong to other B3 bins.  A group selected more than once contributes its
    rows once per selection (standard cluster bootstrap).
    """
    groups = np.asarray(groups, dtype=object)
    uniq = np.array(sorted(set(groups.tolist())), dtype=object)
    by_group = {g: np.where(groups == g)[0] for g in uniq}
    picked = rng.choice(uniq, size=len(uniq), replace=True)
    return np.concatenate([by_group[g] for g in picked]), picked


def cluster_bin_medians(x, y, groups, nboot=NBOOT, seed=SEED + 101):
    """Binned medians with whole-group bootstrap CIs.

    Bin edges are fixed once on the original sample.  A bootstrap replicate
    first resamples whole independence groups from the full group set, then
    selects rows in the requested bin.  A bin with fewer than two source groups
    gets no CI.  Empty replicate bins are skipped.
    """
    x = np.asarray(x, float); y = np.asarray(y, float)
    groups = np.asarray(groups, dtype=object)
    bins = pd.qcut(pd.Series(x), 4, duplicates="drop")
    rng = np.random.default_rng(seed)
    rows = []
    categories = bins.cat.categories if hasattr(bins, "cat") else bins.dtype.categories
    for b in categories:
        in_bin = (bins == b).to_numpy()
        if not in_bin.any():
            continue
        xb = x[in_bin]; yb = y[in_bin]; gb = groups[in_bin]
        ug = sorted(set(gb.tolist()))
        med = float(np.median(yb))
        rec = {"bin_left": float(b.left), "bin_right": float(b.right),
               "n": int(len(yb)), "n_groups": int(len(ug)),
               "median": med, "ci_low": np.nan, "ci_high": np.nan,
               "ci_status": "single_cluster" if len(ug) < 2 else "ok"}
        if len(ug) >= 2:
            draws = []
            for _ in range(nboot):
                idx, _ = cluster_replicate_indices(groups, rng)
                bmask = (x[idx] > b.left) & (x[idx] <= b.right)
                if not bmask.any():
                    continue
                draws.append(float(np.median(y[idx][bmask])))
            if draws:
                rec["ci_low"], rec["ci_high"] = [float(v) for v in
                                                  np.percentile(draws, [2.5, 97.5])]
            else:
                rec["ci_status"] = "empty_replicates"
        rows.append(rec)
    return pd.DataFrame(rows)


def bias_bins(ax, x, y, groups, color, label):
    """Plot binned medians; CIs use whole independence groups."""
    res = cluster_bin_medians(x, y, groups)
    for _, r in res.iterrows():
        xc = .5 * (r.bin_left + r.bin_right)
        if np.isfinite(r.ci_low) and np.isfinite(r.ci_high):
            ax.errorbar([xc], [r["median"]],
                        yerr=[[max(0, r["median"] - r.ci_low)],
                              [max(0, r.ci_high - r["median"])]],
                        fmt="o-", color=color, lw=1, ms=4, capsize=2)
        else:
            ax.plot([xc], [r["median"]], "o", color=color, ms=4)
    if label is not None:
        ax.plot([], [], "o-", color=color, lw=1, label=label)
    return res


def save_fig(fig, stem):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    fig.savefig(stem.with_suffix(".png"), dpi=300, facecolor="white", bbox_inches="tight")
    # Vector PDFs are written outside git; the archive is created below.
    PDF.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF / (stem.stem + ".pdf"), dpi=300, facecolor="white", bbox_inches="tight")
    for coll in fig.findobj(matplotlib.collections.Collection):
        coll.set_rasterized(True)
    plt.close(fig)


def make_figures(d, stats_by, overall):
    # T1/T2
    t1 = FIG / "T1_taylor_log10.png"; t2 = FIG / "T2_taylor_linear.png"
    plot_taylor(stats_by, "log10", t1)
    plot_taylor(stats_by, "linear", t2)

    # B1 log-log scatter
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    reg_colors = {"WAP": "C0", "WAIS": "C3"}
    for reg in REGIONS:
        q = d[d.region == reg]
        if q.empty:
            continue
        sz = 18 + 55 * np.clip(q.obs_unc / q.obs_rate, 0, 3)
        ax.scatter(q.obs_rate, q.model_rate, s=sz, alpha=.65, color=reg_colors[reg],
                   edgecolor="none", label=f"{reg} (n={len(q)})")
    lim = [max(1e-4, min(d.obs_rate.min(), d.model_rate.min()) * .6),
           max(d.obs_rate.max(), d.model_rate.max()) * 1.4]
    ax.plot(lim, lim, "k-", lw=1.2, label="1:1")
    for fac, ls in ((2, "--"), (10, ":"), (.5, "--"), (.1, ":")):
        ax.plot(lim, [fac * x for x in lim], color="0.35", ls=ls, lw=.8,
                label=f"×{fac:g}" if fac in (2, 10) else None)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Observed submarine melt [m d$^{-1}$]")
    ax.set_ylabel("Modeled submarine melt [m d$^{-1}$]")
    ax.grid(alpha=.2, which="both")
    ci_status = overall.get("ci_status")
    text = (f"N = {overall['n']}\nmedian ratio = {overall['median_ratio']:.3f}"
            f" [{overall.get('ci_low_median_ratio', np.nan):.3f}, {overall.get('ci_high_median_ratio', np.nan):.3f}]"
            f"\nr(log10) = {overall['pearson_log10']:.3f}"
            f" [{overall.get('ci_low_pearson_log10', np.nan):.3f}, {overall.get('ci_high_pearson_log10', np.nan):.3f}]"
            f"\nSpearman = {overall['spearman']:.3f}"
            f" [{overall.get('ci_low_spearman', np.nan):.3f}, {overall.get('ci_high_spearman', np.nan):.3f}]")
    fig.text(.12, .018, text, fontsize=7, va="bottom", ha="left")
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    fig.subplots_adjust(left=.12, right=.97, bottom=.25, top=.92)
    save_fig(fig, FIG / "B1_scatter_loglog.png")

    # B2 ratio distribution + ECDF + regional boxplot
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.4), gridspec_kw={"width_ratios": [1.1, 1.1, 1.3]})
    lr = d.log10_ratio.values
    axs[0].hist(lr, bins=28, color="0.45", edgecolor="white", alpha=.9)
    axs[0].axvline(0, color="k", lw=1)
    axs[0].axvline(np.median(lr), color="C1", lw=1.3)
    axs[0].set_xlabel("log10(model/observed)"); axs[0].set_ylabel("count")
    axs[0].text(.04, .92, "(a)", transform=axs[0].transAxes, fontsize=8, fontweight="bold")
    axs[0].text(.03, .84,
                f"median log10 = {np.median(lr):.3f}\n"
                f"median ratio = {overall['median_ratio']:.3f} "
                f"[{overall.get('ci_low_median_ratio', np.nan):.3f}, "
                f"{overall.get('ci_high_median_ratio', np.nan):.3f}]",
                transform=axs[0].transAxes, va="top", fontsize=6.8)
    x = np.sort(lr); y = np.arange(1, len(x) + 1) / len(x)
    axs[1].step(x, y, where="post", color="C0", lw=1.3)
    axs[1].axvline(0, color="k", lw=1); axs[1].axvline(np.median(lr), color="C1", lw=1.1)
    axs[1].set_xlabel("log10(model/observed)"); axs[1].set_ylabel("ECDF")
    axs[1].text(.04, .92, "(b)", transform=axs[1].transAxes, fontsize=8, fontweight="bold")
    groups = [d.loc[d.region == r, "log10_ratio"].values for r in REGIONS]
    axs[2].boxplot(groups, tick_labels=list(REGIONS), widths=.5, patch_artist=True,
                   boxprops=dict(facecolor="0.85"), medianprops=dict(color="C1"))
    axs[2].axhline(0, color="k", lw=1)
    axs[2].set_ylabel("log10(model/observed)"); axs[2].text(.04, .92, "(c)", transform=axs[2].transAxes, fontsize=8, fontweight="bold")
    axs[2].grid(alpha=.2, axis="y")
    fig.subplots_adjust(left=.07, right=.98, bottom=.14, top=.88, wspace=.30)
    save_fig(fig, FIG / "B2_ratio_distribution.png")

    # B3 bias diagnostics
    fig, axs = plt.subplots(2, 2, figsize=(10, 8))
    for ax, xcol, lab, title in (
        (axs[0, 0], "delta_t", "T$_w$ − T$_f$ [°C]", "(a) thermal forcing"),
        (axs[0, 1], "size_m", "√surface area [m]", "(b) size"),
        (axs[1, 0], "duration_days", "duration [d]", "(c) duration")):
        for reg in REGIONS:
            q = d[d.region == reg]
            ax.scatter(q[xcol], q.log10_ratio, s=13, alpha=.35,
                       color=reg_colors[reg], label=reg)
        bias_bins(ax, d[xcol].values, d.log10_ratio.values,
                  d.independence_group.values, "0.25", None)
        ax.axhline(0, color="k", lw=.9)
        ax.set_xlabel(lab); ax.set_ylabel("log10(model/observed)")
        ax.text(.03, .94, title.split(" ")[0], transform=ax.transAxes, fontsize=8, fontweight="bold")
        ax.grid(alpha=.2)
    axs[0, 0].scatter([], [], s=12, color="0.45", alpha=.5, label="individual")
    axs[0, 0].plot([], [], "o-", color="0.25", ms=4, label="binned median; 95% group CI")
    axs[0, 0].legend(fontsize=6, frameon=False, loc="lower left")
    axs[1, 1].boxplot([d.loc[d.region == r, "log10_ratio"].values for r in REGIONS],
                      tick_labels=list(REGIONS), widths=.5, patch_artist=True,
                      boxprops=dict(facecolor="0.85"), medianprops=dict(color="C1"))
    axs[1, 1].axhline(0, color="k", lw=.9)
    axs[1, 1].set_ylabel("log10(model/observed)")
    axs[1, 1].text(.03, .94, "(d)", transform=axs[1, 1].transAxes, fontsize=8, fontweight="bold")
    axs[1, 1].grid(alpha=.2, axis="y")
    fig.subplots_adjust(left=.09, right=.97, bottom=.10, top=.93, wspace=.28, hspace=.32)
    save_fig(fig, FIG / "B3_bias_diagnostics.png")

    # B4 group means
    g = d.groupby("independence_group").agg(
        n=("case_id", "size"), obs=("obs_rate", "mean"), model_mean=("model_rate", "mean")).reset_index()
    g["label"] = g.independence_group.str.replace("ENDERLIN23_", "", regex=False)
    x = np.arange(len(g)); w = .36
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(x - w / 2, g.obs, w, label="observed", color="0.65")
    ax.bar(x + w / 2, g.model_mean, w, label="model", color="C0")
    ax.set_xticks(x); ax.set_xticklabels([f"{r}\n(n={n})" for r, n in zip(g.label, g.n)], fontsize=7)
    ax.set_ylabel("mean submarine melt [m d$^{-1}$]")
    ax.grid(alpha=.2, axis="y"); ax.legend(frameon=False)
    fig.subplots_adjust(left=.10, right=.98, bottom=.17, top=.90)
    save_fig(fig, FIG / "B4_group_means.png")

    # Manifest
    rows = [
        ("T1", "Taylor diagram, log10 submarine melt", t1),
        ("T2", "Taylor diagram, linear submarine melt", t2),
        ("B1", "log-log model/observation scatter", FIG / "B1_scatter_loglog.png"),
        ("B2", "model/observation ratio distribution and ECDF", FIG / "B2_ratio_distribution.png"),
        ("B3", "bias versus forcing, size, duration and region", FIG / "B3_bias_diagnostics.png"),
        ("B4", "Descriptive observed and modeled mean submarine melt by independence group (no CI)", FIG / "B4_group_means.png"),
    ]
    man = pd.DataFrame([{
        "figure": k, "description": desc, "n_cases": int(overall["n"]),
        "n_groups": int(overall.get("n_groups", 0)),
        "png": str(Path(png).relative_to(ROOT)),
        "pdf": f"journal_pdf_vectors.zip::{Path(png).name.replace('.png', '.pdf')}",
        "source": "Stage 12.15 Enderlin23 hindcast; observed Enderlin23 per-iceberg table",
        "space": "log10" if k == "T1" else ("linear" if k == "T2" else "mixed")
    } for k, desc, png in rows])
    man.to_csv(FIG / "figures_manifest.csv", index=False)

    # PDF archive outside git
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for _, _, png in rows:
            p = PDF / (Path(png).name.replace(".png", ".pdf"))
            if not p.exists():
                raise RuntimeError(f"missing vector PDF: {p}")
            z.write(p, arcname=p.name)
    print("wrote", ARCHIVE, ARCHIVE.stat().st_size)


def main():
    ensure_dirs()
    d = load_data()
    d.to_csv(EVID / "matched_cases.csv", index=False)
    strata = [("All", d), ("WAP", d[d.region == "WAP"]), ("WAIS", d[d.region == "WAIS"])]
    for site, q in d.groupby("site"):
        if len(q) >= 8:
            strata.append((site, q))
    stats_by = {}
    rows = []
    for i, (name, q) in enumerate(strata):
        s = compute_stratum(name, q, SEED + 1000 * i)
        stats_by[name] = s
        rows.extend(long_rows(name, s))
    metrics = pd.DataFrame(rows)
    metrics.loc[metrics.stratum == "All"].to_csv(EVID / "metrics.csv", index=False)
    metrics.loc[metrics.stratum != "All"].to_csv(EVID / "metrics_by_region.csv", index=False)
    make_figures(d, {k: stats_by[k] for k in TAYLOR_KEYS}, stats_by["All"])
    stage0 = {
        "observations_total_rows": int(pd.read_csv(OBS).shape[0]),
        "observations_independent_true": int(pd.read_csv(OBS).independent_case.astype(bool).sum()),
        "hindcast_cases": int(len(d)),
        "independent_groups": int(d.independence_group.nunique()),
        "regions": d.region.value_counts().to_dict(),
        "sites": d.site.value_counts().to_dict(),
        "early_stop_cases": int(d.early_stop.sum()),
        "final_mass_pct_min": float(d.final_mass_pct.min()),
        "final_mass_pct_max": float(d.final_mass_pct.max()),
        "delta_t_min": float(d.delta_t.min()), "delta_t_max": float(d.delta_t.max()),
        "metric_definition": "observed: volume_change_rate/submerged_area [m/day]; model: (basal+lateral+wave)/rho_ice/(mean_wet_area*seconds)*86400 [m/day]",
        "bootstrap_replicates": NBOOT, "noise_method": "analytic reliability: 1 - mean(sigma^2)/var(obs); log10 sigma/(obs ln10)", "seed": SEED,
    }
    (EVID / "stage0_recon.json").write_text(json.dumps(stage0, indent=2) + "\n")
    print(json.dumps(stage0, indent=2))
    print("figures:", sorted(p.name for p in FIG.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
