#!/usr/bin/env python3
"""
Stage 10.18D — Velocity-Resolved / Per-Iceberg Observational Upgrade
(per-iceberg Enderlin23 population analysis).

Reads the retrieved Enderlin23 per-iceberg dataset
(data/validation/observations/stage10.18d/enderlin23_per_iceberg.csv,
743 individual icebergs, USAP-DC 10.15784/601679, MD5-verified) and:

1. reproduces the paper's regional statistics (max melt rate per region vs
   the published ~50/~40/~5/~5 m/a for WAP/WAIS/EAIS/EAP);
2. tests the Thwaites thermal-forcing relationship (melt ~ 24 m/a per degC
   of depth-averaged thermal forcing, R^2=0.80) per iceberg by inverting the
   published fit and checking the inferred TF against the paper's observed
   TF range (0.2-1.6 degC);
3. quantifies the draft dependence of melt rate (median melt-rate increase
   per m of draft) per site and region and compares with the paper's values;
4. compares the per-iceberg melt-rate population against the model closures:
   legacy C_LATERAL at representative thermal forcings, and the literature
   velocity-dependent variants (bulk, Bigg1997, plume, buoyant) evaluated at
   the observed (draft-dependent) temperature forcing;
5. computes the per-iceberg effective submarine coefficient C_eff_submarine
   distribution and compares with the production lateral constant;
6. writes figures (10) and machine-readable summary (summary.json, log).

Velocity-resolved status: the per-iceberg dataset contains NO ocean velocity
(U_rel); the velocity-resolved upgrade remains a campaign-design deliverable
(ADCP-equipped Schild21-style package, see report section).

Outputs (gitignored): data/output/stage10.18d/

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/analysis/stage10_18d_per_iceberg.py
"""

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "python" / "validation"))

from python.validation.lateral_melt import (
    C_LATERAL,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    fitzmaurice_plume_side_melt,
    legacy_lateral_melt_rate,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
)

DATA = REPO / "data" / "validation" / "observations" / "stage10.18d" / "enderlin23_per_iceberg.csv"
OUT = REPO / "data" / "output" / "stage10.18d"
PLOTS = OUT / "plots"

# Paper Enderlin23 region max melt rates [m/a] (abstract / text)
PAPER_REGION_MAX = {"WAP": 50.0, "WAIS": 40.0, "EAIS": 5.0, "EAP": 5.0}
# Thwaites published sensitivity: melt [m/a] = 24 * TF [degC]  (R^2=0.80, RMSE 3.7 m/a/degC)
THWAITES_SLOPE = 24.0
THWAITES_TF_RANGE = (0.2, 1.6)
# Representative depth-averaged thermal forcing per region (paper text):
#   WAP: ~1-2 degC (rarely >2; only 4/115 icebergs draft > 100 m)
#   Thwaites (WAIS): 0.2-1.6 degC depth-dependent
#   Totten/Mertz (EAIS): ~0.6 degC; Weddell (Edgeworth/Filchner): <= 0.3 degC
REGION_TF = {"WAP": 1.5, "WAIS": 0.9, "EAIS": 0.6, "EAP": 0.3}
REGION_TF_RANGE = {"WAP": (1.0, 2.0), "WAIS": (0.2, 1.6), "EAIS": (0.3, 0.6), "EAP": (0.1, 0.3)}

DAYS_PER_YEAR = 365.25

LOG: list[str] = []


def log(msg: str):
    LOG.append(msg)
    print(f"  [{datetime.now(UTC).strftime('%H:%M:%S')}] {msg}")


def _f(v):
    s = (v or "").strip()
    if s == "" or s.upper() in ("NA", "NAN", "NONE", "NULL", "-"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def load() -> list[dict]:
    with open(DATA, newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(r for r in f if not r.lstrip().startswith("#"))]


def melt_ma(r: dict) -> float:
    return _f(r["melt_rate"]) * DAYS_PER_YEAR


def median(xs) -> float:
    xs = [x for x in xs if x == x]
    if not xs:
        return float("nan")
    return float(np.median(xs))


def percentile(xs, p) -> float:
    xs = [x for x in xs if x == x]
    if not xs:
        return float("nan")
    return float(np.percentile(xs, p))


# ---------------------------------------------------------------------------
# 1. Regional statistics vs paper
# ---------------------------------------------------------------------------
def regional_stats(rows: list[dict]) -> dict:
    out = {}
    for region in ["WAP", "WAIS", "EAIS", "EAP"]:
        rs = [r for r in rows if r["region"] == region]
        melts = [melt_ma(r) for r in rs]
        drafts = [_f(r["draft"]) for r in rs]
        out[region] = {
            "n": len(rs),
            "melt_max_ma": max(melts) if melts else float("nan"),
            "melt_med_ma": median(melts),
            "melt_p95_ma": percentile(melts, 95),
            "draft_med": median(drafts),
            "draft_max": max(drafts) if drafts else float("nan"),
            "paper_max_ma": PAPER_REGION_MAX[region],
            "max_within_paper_factor": (
                max(melts) / PAPER_REGION_MAX[region] if melts else float("nan")),
        }
    return out


# ---------------------------------------------------------------------------
# 2. Thwaites thermal-forcing inversion
# ---------------------------------------------------------------------------
def thwaites_tf_test(rows: list[dict]) -> dict:
    tg = [r for r in rows if r["site"] == "TG"]
    melts_ma = [melt_ma(r) for r in tg]
    tf_inferred = [m / THWAITES_SLOPE for m in melts_ma]
    lo, hi = THWAITES_TF_RANGE
    in_range = sum(1 for t in tf_inferred if lo <= t <= hi)
    return {
        "n": len(tg),
        "melt_med_ma": median(melts_ma),
        "melt_max_ma": max(melts_ma) if melts_ma else float("nan"),
        "tf_inferred_med": median(tf_inferred),
        "tf_inferred_p95": percentile(tf_inferred, 95),
        "tf_inferred_max": max(tf_inferred) if tf_inferred else float("nan"),
        "paper_tf_range": list(THWAITES_TF_RANGE),
        "n_within_paper_tf_range": in_range,
        "frac_within_paper_tf_range": in_range / len(tf_inferred) if tf_inferred else float("nan"),
        "slope_ma_per_c": THWAITES_SLOPE,
    }


# ---------------------------------------------------------------------------
# 3. Draft dependence (median melt-rate increase per m of draft)
# ---------------------------------------------------------------------------
def draft_dependence(rows: list[dict]) -> dict:
    # per-site linear slope of melt [m/a] vs draft [m] (paper reports the
    # median increase in melt rate with draft, e.g. ~0.008-0.016 m/a per m at
    # Edgeworth, 0.02+/-0.007 at Ronne western margin)
    out = {}
    sites = sorted({r["site"] for r in rows})
    for s in sites:
        rs = [(float(_f(r["draft"])), melt_ma(r)) for r in rows if r["site"] == s]
        rs = [(d, m) for d, m in rs if d == d and m == m and d > 0]
        if len(rs) < 5:
            out[s] = {"n": len(rs), "slope": float("nan"), "r2": float("nan")}
            continue
        d = np.array([x[0] for x in rs], dtype=float)
        m = np.array([x[1] for x in rs], dtype=float)
        slope, intercept = np.polyfit(d, m, 1)
        resid = m - (slope * d + intercept)
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((m - m.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        out[s] = {"n": len(rs), "slope": float(slope), "intercept": float(intercept), "r2": float(r2)}
    return out


# ---------------------------------------------------------------------------
# 4. Model comparison at per-iceberg conditions
# ---------------------------------------------------------------------------
def model_comparison(rows: list[dict]) -> dict:
    # Compare per-iceberg observed submarine melt (m/day) with model closures
    # evaluated at representative regional thermal forcing. Literature
    # velocity-dependent variants need U_rel which is NOT observed -> evaluate
    # at the paper's inferred shear/velocity context: use U=0 (buoyant/quiescent)
    # for the buoyant variant and a nominal U_rel = 0.02 m/s (observed
    # translational speed scale, Moyer19) for the forced-convection variants.
    # This is explicitly a SCALING CONTEXT, not a velocity-resolved validation.
    u_nominal = 0.02  # m/s, Sermilik iceberg translational scale (Moyer19)
    char_len = 150.0   # m, representative draft (median per-iceberg draft)
    per_region = {}
    for region in ["WAP", "WAIS", "EAIS", "EAP"]:
        rs = [r for r in rows if r["region"] == region]
        obs = [float(_f(r["melt_rate"])) for r in rs]
        tf = REGION_TF[region]
        legacy = m_s_to_m_day(legacy_lateral_melt_rate(tf))
        # velocity-dependent variants at u_nominal and tf
        bulk = m_s_to_m_day(bulk_velocity_dependent_side_melt(tf, u_nominal, char_len))
        bigg = m_s_to_m_day(bigg1997_forced_convection_melt_rate(u_nominal, tf, char_len))
        buoy = m_s_to_m_day(neshyba_josberger_buoyant_melt_rate(tf))
        plume = m_s_to_m_day(fitzmaurice_plume_side_melt(u_nominal, tf, char_len, char_len))
        per_region[region] = {
            "n": len(rs),
            "tf_c": tf,
            "obs_med_m_day": median(obs),
            "obs_p95_m_day": percentile(obs, 95),
            "obs_max_m_day": max(obs) if obs else float("nan"),
            "legacy_m_day": legacy,
            "bulk_u02_m_day": bulk,
            "bigg_u02_m_day": bigg,
            "buoy_u0_m_day": buoy,
            "plume_u02_m_day": plume,
        }
    # global legacy exceedance: fraction of per-iceberg melt below legacy at
    # representative TF (i.e. how much legacy over-predicts per-iceberg rates)
    all_obs = [float(_f(r["melt_rate"])) for r in rows]
    exceed = {}
    for tf_name, tf in [("tf_1.5", 1.5), ("tf_0.6", 0.6), ("tf_0.3", 0.3)]:
        legacy = m_s_to_m_day(legacy_lateral_melt_rate(tf))
        exceed[tf_name] = {
            "legacy_m_day": legacy,
            "frac_obs_below_legacy": sum(1 for o in all_obs if o < legacy) / len(all_obs),
            "median_ratio_legacy_over_obs": median([legacy / o for o in all_obs]) if all_obs else float("nan"),
        }
    return {"per_region": per_region, "legacy_exceedance": exceed,
            "u_nominal_m_s": u_nominal}


# ---------------------------------------------------------------------------
# 5. Effective submarine coefficient distribution
# ---------------------------------------------------------------------------
def effective_coefficient(rows: list[dict]) -> dict:
    # C_eff_submarine [m/(s K)] = melt_rate [m/day] / thermal_forcing [K] / 86400
    # (submarine total, separate from lab lateral coefficient per 10.18C).
    # Per-iceberg TF is not observed -> use regional representative TF with
    # documented uncertainty.
    out = {"production_C_LATERAL": C_LATERAL, "per_region": {}}
    all_eff = []
    for region in ["WAP", "WAIS", "EAIS", "EAP"]:
        rs = [r for r in rows if r["region"] == region]
        tf = REGION_TF[region]
        effs = [float(_f(r["melt_rate"])) / tf / 86400.0 for r in rs]
        effs = [e for e in effs if e == e]
        all_eff.extend(effs)
        out["per_region"][region] = {
            "n": len(effs),
            "c_eff_med": median(effs),
            "c_eff_p25": percentile(effs, 25),
            "c_eff_p75": percentile(effs, 75),
            "tf_c": tf,
        }
    out["all_n"] = len(all_eff)
    out["all_c_eff_med"] = median(all_eff)
    out["all_c_eff_p25"] = percentile(all_eff, 25)
    out["all_c_eff_p75"] = percentile(all_eff, 75)
    out["ratio_med_to_production"] = median(all_eff) / C_LATERAL if all_eff else float("nan")
    return out


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def make_figures(rows: list[dict], reg: dict, tf_test: dict, draft: dict,
                 model: dict, ceff: dict):
    PLOTS.mkdir(parents=True, exist_ok=True)

    # fig01: regional melt-rate distributions (m/a), log scale
    fig, ax = plt.subplots(figsize=(8, 5))
    regions = ["WAP", "WAIS", "EAIS", "EAP"]
    data = [[melt_ma(r) for r in rows if r["region"] == rg and melt_ma(r) == melt_ma(r)]
            for rg in regions]
    ax.boxplot(data, tick_labels=regions, showfliers=False)
    for i, rg in enumerate(regions, start=1):
        ax.scatter([i] * len(data[i - 1]), data[i - 1], s=4, alpha=0.15, color="0.4")
        ax.axhline(PAPER_REGION_MAX[rg], color="C1", ls="--", lw=1)
        ax.text(i + 0.18, PAPER_REGION_MAX[rg] * 1.08, f"paper max {PAPER_REGION_MAX[rg]:.0f}",
                fontsize=8, color="C1")
    ax.set_yscale("log")
    ax.set_ylabel("submarine melt rate [m/a]")
    ax.set_title("Enderlin23 per-iceberg melt rates by region (n=743)")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig01_regional_melt_distribution.png", dpi=150)
    plt.close(fig)

    # fig02: Thwaites melt vs draft, colored by inferred TF
    tg = [r for r in rows if r["site"] == "TG"]
    d = np.array([_f(r["draft"]) for r in tg], dtype=float)
    m = np.array([melt_ma(r) for r in tg], dtype=float)
    tf = m / THWAITES_SLOPE
    fig, ax = plt.subplots(figsize=(8, 5))
    sc = ax.scatter(d, m, c=tf, cmap="viridis", s=12)
    cb = fig.colorbar(sc, ax=ax, label=f"inferred TF = melt / {THWAITES_SLOPE:.0f} [degC]")
    ax.set_xlabel("draft [m]")
    ax.set_ylabel("melt rate [m/a]")
    ax.set_title(f"Thwaites per-iceberg melt vs draft (n={len(tg)}); paper TF range 0.2-1.6 degC")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig02_thwaites_melt_draft_tf.png", dpi=150)
    plt.close(fig)

    # fig03: melt vs draft per site with linear fits
    fig, axes = plt.subplots(3, 5, figsize=(18, 9))
    sites = sorted(draft.keys())
    for ax, s in zip(axes.ravel(), sites):
        rs = [(float(_f(r["draft"])), melt_ma(r)) for r in rows if r["site"] == s]
        rs = [(x, y) for x, y in rs if x == x and y == y]
        if not rs:
            ax.set_visible(False)
            continue
        ds = [x[0] for x in rs]
        ms = [x[1] for x in rs]
        ax.scatter(ds, ms, s=6, alpha=0.4)
        info = draft[s]
        if info["n"] >= 5 and info["slope"] == info["slope"]:
            xl = np.linspace(min(ds), max(ds), 2)
            ax.plot(xl, info["slope"] * xl + info["intercept"], "C1-", lw=1)
            ax.set_title(f"{s}: {info['slope']:.4f} m/a per m (R2={info['r2']:.2f})", fontsize=8)
        else:
            ax.set_title(f"{s}: n={len(rs)}", fontsize=8)
        ax.set_xlabel("draft [m]", fontsize=7)
        ax.set_ylabel("melt [m/a]", fontsize=7)
        ax.tick_params(labelsize=6)
    for ax in axes.ravel()[len(sites):]:
        ax.set_visible(False)
    fig.suptitle("Per-site melt vs draft (Enderlin23 per-iceberg)")
    fig.tight_layout()
    fig.savefig(PLOTS / "fig03_per_site_melt_draft.png", dpi=150)
    plt.close(fig)

    # fig04: model comparison per region (legacy vs obs)
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(4)
    w = 0.25
    regions = ["WAP", "WAIS", "EAIS", "EAP"]
    obs_med = [model["per_region"][rg]["obs_med_m_day"] for rg in regions]
    legacy = [model["per_region"][rg]["legacy_m_day"] for rg in regions]
    bulk = [model["per_region"][rg]["bulk_u02_m_day"] for rg in regions]
    ax.bar(x - w, obs_med, w, label="observed median (per-iceberg)")
    ax.bar(x, legacy, w, label="legacy C_LATERAL at region TF", color="C3", alpha=0.7)
    ax.bar(x + w, bulk, w, label="bulk U=0.02 m/s", color="C2", alpha=0.7)
    ax.set_xticks(x, regions)
    ax.set_yscale("log")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Observed per-iceberg vs model closures (representative TF; NOT velocity-resolved)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(PLOTS / "fig04_model_comparison_regions.png", dpi=150)
    plt.close(fig)

    # fig05: legacy exceedance vs TF
    fig, ax = plt.subplots(figsize=(7, 5))
    tfs = [0.3, 0.6, 1.5]
    fracs = [model["legacy_exceedance"][f"tf_{t}"]["frac_obs_below_legacy"] for t in tfs]
    ratios = [model["legacy_exceedance"][f"tf_{t}"]["median_ratio_legacy_over_obs"] for t in tfs]
    ax.plot(tfs, fracs, "o-", label="fraction of icebergs with obs melt < legacy")
    ax.set_xlabel("thermal forcing [degC]")
    ax.set_ylabel("fraction below legacy")
    ax.set_title("Legacy C_LATERAL exceedance over per-iceberg observed melt")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig05_legacy_exceedance.png", dpi=150)
    plt.close(fig)

    # fig06: C_eff_submarine per region vs production constant
    fig, ax = plt.subplots(figsize=(8, 5))
    regions = ["WAP", "WAIS", "EAIS", "EAP"]
    meds = [ceff["per_region"][rg]["c_eff_med"] for rg in regions]
    p25 = [ceff["per_region"][rg]["c_eff_p25"] for rg in regions]
    p75 = [ceff["per_region"][rg]["c_eff_p75"] for rg in regions]
    ax.bar(np.arange(4), meds, yerr=[np.array(meds) - np.array(p25), np.array(p75) - np.array(meds)],
           capsize=4, alpha=0.8, label="C_eff_submarine per region (at region TF)")
    ax.axhline(C_LATERAL, color="C3", ls="--", label=f"production C_LATERAL = {C_LATERAL:.1e}")
    ax.set_xticks(np.arange(4), regions)
    ax.set_ylabel("C_eff [m/(s K)]")
    ax.set_title("Per-iceberg effective submarine coefficient (TF = representative regional)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig06_c_eff_regions.png", dpi=150)
    plt.close(fig)

    # fig07: melt vs draft global color by region
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"WAP": "C0", "WAIS": "C1", "EAIS": "C2", "EAP": "C3"}
    for rg in regions:
        rs = [(float(_f(r["draft"])), melt_ma(r)) for r in rows if r["region"] == rg]
        rs = [(x, y) for x, y in rs if x == x and y == y]
        if rs:
            ax.scatter([x[0] for x in rs], [x[1] for x in rs], s=5, alpha=0.25,
                       color=colors[rg], label=rg)
    ax.set_xlabel("draft [m]")
    ax.set_ylabel("melt rate [m/a]")
    ax.set_title("All per-iceberg melt vs draft (region colors)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig07_all_melt_draft.png", dpi=150)
    plt.close(fig)

    # fig08: inferred TF histogram (Thwaites)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(tf, bins=30, alpha=0.7)
    for bound in THWAITES_TF_RANGE:
        ax.axvline(bound, color="C3", ls="--", lw=1)
    ax.set_xlabel("inferred TF = melt/24 [degC]")
    ax.set_ylabel("icebergs")
    ax.set_title("Thwaites inferred thermal forcing (paper observed range 0.2-1.6 degC)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig08_thwaites_tf_histogram.png", dpi=150)
    plt.close(fig)

    # fig09: draft distribution per region
    fig, ax = plt.subplots(figsize=(8, 5))
    dd = [[float(_f(r["draft"])) for r in rows if r["region"] == rg and _f(r["draft"]) == _f(r["draft"])]
          for rg in regions]
    ax.boxplot(dd, tick_labels=regions, showfliers=False)
    for i, rg in enumerate(regions, start=1):
        ax.scatter([i] * len(dd[i - 1]), dd[i - 1], s=4, alpha=0.12, color="0.4")
    ax.set_ylabel("draft [m]")
    ax.set_title("Per-iceberg draft by region")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig09_draft_distribution.png", dpi=150)
    plt.close(fig)

    # fig10: temporal coverage (observations per year)
    fig, ax = plt.subplots(figsize=(8, 5))
    years = {}
    for r in rows:
        y = int(r["date_start"][:4])
        years[y] = years.get(y, 0) + 1
    ys = sorted(years)
    ax.bar([y for y in ys], [years[y] for y in ys])
    ax.set_xlabel("observation start year")
    ax.set_ylabel("per-iceberg observations")
    ax.set_title("Temporal coverage of per-iceberg observations (2011-2022)")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(PLOTS / "fig10_temporal_coverage.png", dpi=150)
    plt.close(fig)

    log(f"figures written to {PLOTS}")


# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load()
    log(f"loaded {len(rows)} per-iceberg observations")

    reg = regional_stats(rows)
    tf_test = thwaites_tf_test(rows)
    draft = draft_dependence(rows)
    model = model_comparison(rows)
    ceff = effective_coefficient(rows)
    make_figures(rows, reg, tf_test, draft, model, ceff)

    summary = {
        "stage": "10.18D",
        "dataset": str(DATA),
        "n_per_iceberg": len(rows),
        "regional_stats": reg,
        "thwaites_tf_test": tf_test,
        "draft_dependence": draft,
        "model_comparison": model,
        "effective_coefficient": ceff,
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(OUT / "log.txt", "w") as f:
        f.write("\n".join(LOG))
    log(f"summary.json written ({len(rows)} icebergs)")


if __name__ == "__main__":
    main()