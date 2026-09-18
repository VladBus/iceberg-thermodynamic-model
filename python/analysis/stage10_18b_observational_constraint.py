#!/usr/bin/env python3
"""
Stage 10.18B — Observational Constraint and Parameterization Discrimination.

Reads:
    data/validation/observations/iceberg_lateral_melt_observations.csv
    data/validation/observations/iceberg_lateral_melt_observational_sources.csv
Writes (all gitignored under data/output/stage10.18b/):
    observational_dataset_normalized.csv   SI-normalized cases
    observational_provenance.csv           per-case traceability
    literature_parameterizations.csv       parameterization metadata
    parameterization_regime_matrix.csv     regime applicability
    model_observation_comparison.csv       per-case per-model residuals
    statistics_summary.csv                 metrics per filtered dataset
    leave_one_source_out.csv
    effective_c_lateral.csv                C_eff distribution
    parameterization_constraint_matrix.csv scientific summary matrix
    summary.json
    reproducibility.log
    plots/fig01..fig10.png

Every operation (filtering, conversion, exclusion) is logged to
reproducibility.log. No value is fabricated; NA fields propagate.

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/analysis/stage10_18b_observational_constraint.py
"""

import csv
import json
import math
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
sys.path.insert(0, str(REPO))  # repo root -> `python.validation` package imports
sys.path.insert(0, str(REPO / "python" / "validation"))  # flat module imports

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from python.validation.observational_constraint import (
    MODELS,
    comparison_table,
    effective_c_lateral,
    implied_volume_loss,
    leave_one_source_out,
    load_cases,
    metrics,
    metrics_filtered,
    predict,
    regime_of,
)
from python.validation.lateral_melt import (
    BIGG_K_OCEAN,
    C_LATERAL,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    fitzmaurice_plume_side_melt,
    legacy_lateral_melt_rate,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
)

RAW = REPO / "data" / "validation" / "observations" / "iceberg_lateral_melt_observations.csv"
SOURCES = REPO / "data" / "validation" / "observations" / "iceberg_lateral_melt_observational_sources.csv"
OUT = REPO / "data" / "output" / "stage10.18b"
PLOTS = OUT / "plots"

LOG: list[str] = []


def log(msg: str):
    LOG.append(msg)
    print(f"  [{datetime.now(UTC).strftime('%H:%M:%S')}] {msg}")


# ---------------------------------------------------------------------------
# Normalization (raw -> SI-normalized dataset)
# ---------------------------------------------------------------------------
def normalize(raw_path: Path, out_path: Path):
    """Convert raw rows to the SI-normalized schema. All conversions are
    documented; NA propagates."""
    rows = []
    with open(raw_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(r for r in f if not r.lstrip().startswith("#"))
        for r in reader:
            rows.append({
                "case_id": r["case_id"],
                "source_id": r["source_id"],
                "year": r["year"],
                "region": r["region"],
                "environment": r["environment"],
                "delta_T_K": r["delta_T_K"],
                "u_rel_m_s": r["u_rel_m_s"],
                "L_m": r["L_m"],
                "D_m": r["D_m"],
                "melt_obs_m_day": r["melt_obs_m_day"],
                "melt_unc_m_day": r["melt_unc_m_day"],
                "directness": r["directness"],
                "melt_definition": r["melt_definition"],
                "measurement_method": r["measurement_method"],
                "averaging_period": r["averaging_period"],
                "wave_influenced": r["wave_influenced"],
                "comparability": r["comparability"],
                "normalization_confidence": (
                    "HIGH" if r["comparability"] == "DIRECTLY_COMPARABLE"
                    else "MEDIUM" if r["comparability"] == "COMPARABLE_AFTER_NORMALIZATION"
                    else "QUALITATIVE"
                ),
                "notes": r["notes"],
            })
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    log(f"normalized dataset: {len(df)} rows -> {out_path.name}")


def build_provenance(raw_path: Path, out_path: Path):
    """Per-case traceability: original quantity -> transformation -> final."""
    rows = []
    with open(raw_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(r for r in f if not r.lstrip().startswith("#"))
        for r in reader:
            rows.append({
                "case_id": r["case_id"],
                "source_id": r["source_id"],
                "original_quantity": r["melt_obs_m_day"],
                "original_units": "m/day (or m/a for ENDERLIN23 -> /365)",
                "original_location": r["measurement_method"],
                "extraction_method": "verbatim from fetched full text / published fit",
                "transformation": "m/a->m/day for ENDERLIN23; delta_T = T+1.8 for RH80; else as reported",
                "final_quantity": r["melt_obs_m_day"],
                "notes": r["notes"],
            })
    pd.DataFrame(rows).to_csv(out_path, index=False)
    log(f"provenance: {len(rows)} rows -> {out_path.name}")


# ---------------------------------------------------------------------------
# Literature parameterization metadata
# ---------------------------------------------------------------------------
def literature_parameterizations(out_path: Path):
    rows = [
        {"parameterization": "LEGACY_FULL_HEIGHT",
         "source_id": "STAGE9.1 (model legacy)",
         "equation": "m = C_LATERAL*<dT>_D",
         "coefficient": "C_LATERAL = 1e-6 m/(s K)",
         "units": "m/s",
         "velocity_dependence": "none",
         "temperature_dependence": "linear",
         "geometry_dependence": "none (rate); full-height area in update",
         "regime": "any (no regime gating)",
         "observational_basis": "none (legacy simplification, Stage 9.1 sec 14)",
         "uncertainty": "NA",
         "validity_range": "unspecified",
         "source_quality": "MODEL_DERIVED",
         "notes": "equivalent to forced-convection side melt at U_eq ~0.30 m/s (Stage 10.18A)"},
        {"parameterization": "LEGACY_SUBMERGED",
         "source_id": "STAGE10.18A (geometry variant)",
         "equation": "m = C_LATERAL*<dT>_D (rate); volume via 2(L+W)*D",
         "coefficient": "C_LATERAL = 1e-6 m/(s K)",
         "units": "m/s",
         "velocity_dependence": "none",
         "temperature_dependence": "linear",
         "geometry_dependence": "submerged full-perimeter",
         "regime": "any",
         "observational_basis": "none",
         "uncertainty": "NA",
         "validity_range": "unspecified",
         "source_quality": "MODEL_DERIVED",
         "notes": "same rate as legacy; area convention differs by factor 2*rho_i/rho_w = 1.77"},
        {"parameterization": "BULK_FORCED",
         "source_id": "WEEKS_CAMPBELL1973 framework; model basal closure",
         "equation": "m = gamma_T*dT/(rho_i*L_f), gamma_T = Nu*k/D, Nu flat-plate",
         "coefficient": "0.037 Re^0.8 Pr^(1/3) turb / 0.664 Re^0.5 Pr^(1/3) lam; Pr=13.8, k=0.56, nu=1.82e-6",
         "units": "m/s",
         "velocity_dependence": "U^0.8 (turb) / U^0.5 (lam)",
         "temperature_dependence": "linear",
         "geometry_dependence": "L_char = D",
         "regime": "forced convection; U -> 0 gives 0",
         "observational_basis": "flat-plate heat transfer (Eckert & Drake 1959); U^0.8 scaling consistent with lab side-melt (FitzMaurice et al. 2017)",
         "uncertainty": "NA",
         "validity_range": "Re 5e5 transition; U > 0",
         "source_quality": "PRIMARY_DIRECT (lab scaling) / MODEL_DERIVED (coefficients)",
         "notes": "identical closure to the model's basal melt applied to the side"},
        {"parameterization": "BIGG1997",
         "source_id": "BIGG1997 (K quoted by FITZMAURICE17)",
         "equation": "M = K*U_rel^0.8*dT/L^0.2",
         "coefficient": "K = 0.58 (ocean, m/day units)",
         "units": "m/day",
         "velocity_dependence": "U^0.8",
         "temperature_dependence": "linear",
         "geometry_dependence": "L^-0.2",
         "regime": "forced convection; U -> 0 gives 0",
         "observational_basis": "standard forced-convection form (Bigg et al. 1997); K=0.58 quoted in FitzMaurice et al. 2017; original 1997 notation not independently verified",
         "uncertainty": "NA",
         "validity_range": "forced regime",
         "source_quality": "MODEL_DERIVED",
         "notes": "K=0.75 for laboratory setting (FitzMaurice17)"},
        {"parameterization": "BIGG_PLUS_BUOY",
         "source_id": "BIGG1997 + NESHYBA_JOSBERGER1980 (via CS2023)",
         "equation": "M = K*U^0.8*dT/L^0.2 + a*dT + b*dT^2",
         "coefficient": "K=0.58; a=7.62e-3, b=1.29e-3 m/day per degC (m/day)",
         "units": "m/day",
         "velocity_dependence": "U^0.8 forced + velocity-independent buoyant",
         "temperature_dependence": "linear + quadratic",
         "geometry_dependence": "L^-0.2",
         "regime": "forced + buoyant convection",
         "observational_basis": "Neshyba-Josberger empirical fit (Antarctic synthesis, quoted in CS2023); Russell-Head lab temperature dependence ~ dT^1.5 qualitatively consistent with nonlinear buoyant term",
         "uncertainty": "NA",
         "validity_range": "unspecified",
         "source_quality": "MODEL_DERIVED",
         "notes": "buoyant term is the only nonzero contribution at U=0"},
        {"parameterization": "FITZMAURICE_PLUME",
         "source_id": "FITZMAURICE17 (lab-derived)",
         "equation": "M = K*w^0.8*(T_p-T_i)/D^0.2 (attached, U<w); M = K*U^0.8*(T_a-T_i)/L^0.2 (detached)",
         "coefficient": "K=0.58 (0.75 lab); w ~ 2.5 cm/s (lab)",
         "units": "m/day",
         "velocity_dependence": "w or U^0.8",
         "temperature_dependence": "linear",
         "geometry_dependence": "D^-0.2 (attached) / L^-0.2 (detached)",
         "regime": "plume attached/detached split",
         "observational_basis": "laboratory side-melt experiments (FitzMaurice et al. 2017 GRL); plume temperature T_p not measured here -> ambient proxy (documented)",
         "uncertainty": "NA",
         "validity_range": "lab-derived; applied to Sermilik (attached regime mean 0.06-0.10 m/day)",
         "source_quality": "PRIMARY_DIRECT (lab) / MODEL_DERIVED (application)",
         "notes": "T_p proxy = ambient DeltaT in this study"},
    ]
    pd.DataFrame(rows).to_csv(out_path, index=False)
    log(f"literature parameterizations: {len(rows)} rows -> {out_path.name}")


# ---------------------------------------------------------------------------
# Regime matrix
# ---------------------------------------------------------------------------
def regime_matrix(cases, out_path: Path):
    rows = []
    for c in cases:
        rg = regime_of(c)
        rows.append({"case_id": c.case_id, "environment": c.environment,
                     "u_regime": rg["u_regime"], "dT_regime": rg["dT_regime"]})
    pd.DataFrame(rows).to_csv(out_path, index=False)
    log(f"regime matrix -> {out_path.name}")


# ---------------------------------------------------------------------------
# Bounded comparison (lateral <= submarine total is the physical requirement)
# ---------------------------------------------------------------------------
def bounded_comparison(rows: list[dict]) -> dict:
    """For COMPARABLE_AFTER_NORMALIZATION / QUALITATIVE_ONLY submarine cases
    with known delta_T, test whether the model's LATERAL-only prediction stays
    at or below the observed SUBMARINE (side+basal) melt."""
    out = {}
    for m in MODELS:
        viol = []
        used = 0
        for r in rows:
            if r["model_name"] != m or math.isnan(r["predicted_melt_m_day"]):
                continue
            if r["comparability"] not in ("COMPARABLE_AFTER_NORMALIZATION",
                                          "QUALITATIVE_ONLY"):
                continue
            if "submarine" not in r["melt_definition"]:
                continue
            used += 1
            if r["predicted_melt_m_day"] > r["observed_melt_m_day"]:
                viol.append({"case_id": r["case_id"],
                             "pred": r["predicted_melt_m_day"],
                             "obs": r["observed_melt_m_day"],
                             "ratio": r["predicted_melt_m_day"] / r["observed_melt_m_day"]})
        out[m] = {"N_usable": used, "N_violations": len(viol),
                  "violations": viol}
    return out


# ---------------------------------------------------------------------------
# Effective C_LATERAL distribution (per-case C_eff = m_obs / delta_T)
# ---------------------------------------------------------------------------
def c_eff_table(cases) -> list[dict]:
    """C_eff = m_obs/delta_T in m/(s K) for rate-based cases with known delta_T
    (RH80 lab + ENDERLIN23 shelf), plus the Thwaites slope constraint."""
    rows = []
    for c in cases:
        if not c.has_delta_t() or c.delta_t_K <= 0.0:
            continue
        if c.wave_influenced == "TRUE":
            continue
        if "total" in c.melt_definition.lower() or "velocity" in c.melt_definition.lower():
            continue
        c_eff = (c.melt_obs_m_day / 86400.0) / c.delta_t_K
        rows.append({"case_id": c.case_id, "delta_T_K": c.delta_t_K,
                     "melt_m_day": c.melt_obs_m_day,
                     "C_eff_m_per_s_K": c_eff,
                     "C_eff_over_production": c_eff / C_LATERAL})
    return rows


def c_eff_stats(rows: list[dict]) -> dict:
    vals = np.array([r["C_eff_m_per_s_K"] for r in rows])
    return {
        "N": len(vals),
        "median": float(np.median(vals)),
        "p10": float(np.percentile(vals, 10)),
        "p25": float(np.percentile(vals, 25)),
        "p75": float(np.percentile(vals, 75)),
        "p90": float(np.percentile(vals, 90)),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
        "C_LATERAL_production": C_LATERAL,
        "median_over_production": float(np.median(vals) / C_LATERAL),
    }


# ---------------------------------------------------------------------------
# Constraint matrix
# ---------------------------------------------------------------------------
def constraint_matrix(rows: list[dict], bounded: dict) -> pd.DataFrame:
    comp = {m: metrics(rows, m) for m in MODELS}
    rows_out = []
    for m in MODELS:
        mtr = comp[m]
        b = bounded[m]
        rows_out.append({
            "parameterization": m,
            "observational_support": (
                "lab-quiescent: over-predicts low-T, matches high-T" if m in
                ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED")
                else "lab-quiescent: 0 at U=0 (fails quiescent cases)" if m in
                ("BULK_FORCED", "BIGG1997")
                else "lab-quiescent: under-predicts; nonzero at U=0" if m == "BIGG_PLUS_BUOY"
                else "lab-quiescent: brackets RH80 within ~2x (plume branch)"),
            "direct_evidence": "RH80 lab (N=5)" if mtr["N"] else "none usable",
            "indirect_evidence": "Sermilik + Antarctic submarine ranges (qualitative)" ,
            "velocity_dependency_supported": "no (U^0)" if m in
                ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED") else "yes (U^0.8/U^0.5; lab scaling + Antarctic shear statement)",
            "geometry_supported": "not constrained by observations",
            "temperature_supported": "linear; RH80 lab shows dT^1.5 (nonlinear)" if m in
                ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED") else "linear (+quadratic buoyant)",
            "wave_dependency_supported": "no wave observations separable",
            "applicable_environment": "lab / shelf / fjord (rate-level only)",
            "sample_size": mtr["N"],
            "uncertainty_quality": "NA for most cases (only ENDERLIN14 has +-)",
            "main_limitation": "no velocity-resolved field observations; mixed melt definitions",
            "production_ready": "FALSE",
            "confidence": "INSUFFICIENT_DATA" if mtr["N"] < 3 else "LOW",
        })
    return pd.DataFrame(rows_out)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def make_figures(cases, rows, c_eff_rows, cmp_df, bounded, test11_pred):
    # fig01: m vs U_rel (rate cases), overlays of parameterizations
    fig, ax = plt.subplots(figsize=(8, 5))
    for c in cases:
        if math.isnan(c.melt_obs_m_day):
            continue
        u = c.u_rel_m_s if c.has_u_rel() else 0.0
        lbl = c.case_id
        ax.errorbar(u, c.melt_obs_m_day,
                    yerr=c.melt_unc_m_day if c.has_uncertainty() else None,
                    fmt="o", ms=5, capsize=3, label=lbl)
    us = np.logspace(-3, 0.6, 100)
    for dT in (1.8, 3.8, 6.8):
        ax.plot(us, [m_s_to_m_day(legacy_lateral_melt_rate(dT))] * len(us),
                ls="--", lw=1, label=f"LEGACY dT={dT} K")
        ax.plot(us, [m_s_to_m_day(bulk_velocity_dependent_side_melt(dT, u, 88.5)) for u in us],
                ls="-", lw=1, label=f"BULK dT={dT}")
        ax.plot(us, [m_s_to_m_day(bigg1997_forced_convection_melt_rate(u, dT, 100.0)) for u in us],
                ls=":", lw=1, label=f"BIGG dT={dT}")
    ax.set_xscale("log")
    ax.set_xlabel("U_rel [m/s]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 1. Observed melt vs parameterizations (U_rel)")
    ax.legend(fontsize=6, ncol=2)
    ax.grid(alpha=0.3, which="both")
    fig.savefig(PLOTS / "fig01_obs_vs_U.png")
    plt.close(fig)

    # fig02: m vs delta_T
    fig, ax = plt.subplots(figsize=(8, 5))
    for c in cases:
        if math.isnan(c.melt_obs_m_day) or not c.has_delta_t():
            continue
        ax.errorbar(c.delta_t_K, c.melt_obs_m_day,
                    yerr=c.melt_unc_m_day if c.has_uncertainty() else None,
                    fmt="o", ms=5, capsize=3, label=c.case_id)
    dts = np.linspace(0.1, 20, 100)
    ax.plot(dts, [m_s_to_m_day(legacy_lateral_melt_rate(d)) for d in dts],
            "--", label="LEGACY")
    ax.plot(dts, [m_s_to_m_day(neshyba_josberger_buoyant_melt_rate(d)) for d in dts],
            "-.", label="NESHYBA-JOSBERGER (buoyant)")
    ax.plot(dts, 1.8e-2 * (dts) ** 1.5, "-", label="RH80 fit 1.8e-2*dT^1.5")
    ax.set_xlabel("delta_T [K]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 2. Observed melt vs thermal driving")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig02_obs_vs_deltaT.png")
    plt.close(fig)

    # fig03: model/observation ratio per model (usable direct cases)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(MODELS))
    ratios = {}
    for m in MODELS:
        sub = [r for r in rows if r["model_name"] == m
               and not math.isnan(r["predicted_melt_m_day"])
               and r["comparability"] == "DIRECTLY_COMPARABLE"]
        ratios[m] = ([r["predicted_melt_m_day"] / r["observed_melt_m_day"] for r in sub]
                     if sub else [])
    for i, m in enumerate(MODELS):
        r = ratios[m]
        if r:
            ax.scatter([i] * len(r), r, s=25, label=m)
            ax.hlines(1, i - 0.3, i + 0.3, color="grey", lw=0.6)
    ax.axhline(1, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(MODELS, rotation=20, fontsize=7)
    ax.set_ylabel("model / observation")
    ax.set_title("Fig 3. Model/observation ratio (directly comparable cases)")
    ax.set_yscale("log")
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig03_model_over_obs.png")
    plt.close(fig)

    # fig04: residuals
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for m in MODELS:
        sub = [r for r in rows if r["model_name"] == m
               and not math.isnan(r["absolute_error_m_day"])
               and r["comparability"] == "DIRECTLY_COMPARABLE"]
        if sub:
            ax.scatter([m] * len(sub), [r["absolute_error_m_day"] for r in sub], s=25, label=m)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("m_model - m_obs [m/day]")
    ax.set_title("Fig 4. Residuals (directly comparable cases)")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig04_residuals.png")
    plt.close(fig)

    # fig05: normalized residual (sigma) - only ENDERLIN14 has sigma but is not
    # directly comparable; show per-case z where sigma exists
    fig, ax = plt.subplots(figsize=(7, 4))
    have_z = False
    for m in MODELS:
        sub = [r for r in rows if r["model_name"] == m
               and not math.isnan(r["normalized_error"])]
        if sub:
            have_z = True
            ax.scatter([m] * len(sub), [r["normalized_error"] for r in sub], s=30, label=m)
    if not have_z:
        ax.text(0.5, 0.5, "no sigma-bearing comparable cases\n(normalized residual not computable)",
                ha="center", va="center", transform=ax.transAxes)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("(m_model - m_obs)/sigma")
    ax.set_title("Fig 5. Normalized residuals")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig05_normalized_residuals.png")
    plt.close(fig)

    # fig06: geometry - volume-loss conventions vs observed volume flux
    # (Sermilik cases have volume-loss info; show implied volume loss per area
    # convention for a representative observed rate)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    schild = [c for c in cases if c.case_id.startswith("SCHILD21")]
    for c in schild:
        if math.isnan(c.melt_obs_m_day):
            continue
        iv = implied_volume_loss(c, c.melt_obs_m_day)
        ax.bar([c.case_id + " FULL-H", c.case_id + " SUBM"],
               [iv["full_height_m3"], iv["submerged_m3"]], width=0.6)
    ax.set_ylabel("implied volume loss [m3/day]")
    ax.set_title("Fig 6. Geometry conventions: implied volume loss\n"
                 "(full-height H(L+W) vs submerged 2(L+W)D, same rate)")
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig06_geometry.png")
    plt.close(fig)

    # fig07: environment separation
    fig, ax = plt.subplots(figsize=(8, 4.5))
    env_colors = {"LAB": "tab:blue", "FJORD": "tab:green", "SHELF": "tab:orange",
                  "OPEN_OCEAN": "tab:red"}
    for c in cases:
        if math.isnan(c.melt_obs_m_day):
            continue
        u = c.u_rel_m_s if c.has_u_rel() else 0.0
        ax.scatter(u, c.melt_obs_m_day, color=env_colors.get(c.environment, "grey"),
                   s=40, label=c.environment if c.environment not in
                   [x.get_label() for x in ax.collections] else "")
        ax.annotate(c.case_id, (u, c.melt_obs_m_day), fontsize=5,
                    textcoords="offset points", xytext=(3, 3))
    ax.set_xlabel("U_rel [m/s] (0 for unknown)")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 7. Environment separation")
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", ls="", color=c, label=k)
               for k, c in env_colors.items()]
    ax.legend(handles=handles, fontsize=7)
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig07_environment.png")
    plt.close(fig)

    # fig08: velocity regime
    fig, ax = plt.subplots(figsize=(8, 4))
    for c in cases:
        if math.isnan(c.melt_obs_m_day):
            continue
        rg = regime_of(c)
        u = c.u_rel_m_s if c.has_u_rel() else float("nan")
        color = "tab:red" if rg["u_regime"] == "HIGH_U" else (
            "tab:orange" if rg["u_regime"] == "MODERATE_U" else
            "tab:blue" if rg["u_regime"] == "LOW_U" else "grey")
        ax.scatter(u, c.melt_obs_m_day, color=color, s=40)
        ax.annotate(c.case_id, (u, c.melt_obs_m_day), fontsize=5,
                    textcoords="offset points", xytext=(3, 3))
    ax.axvline(0.03, color="grey", ls=":", lw=1)
    ax.axvline(0.3, color="grey", ls=":", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("U_rel [m/s] (0.001 placeholder for unknown)")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 8. Velocity regime (LOW <0.03, MOD 0.03-0.3, HIGH >0.3 m/s)")
    ax.grid(alpha=0.3, which="both")
    fig.savefig(PLOTS / "fig08_velocity_regime.png")
    plt.close(fig)

    # fig09: observed ranges vs TEST_11 model ranges (clearly separated)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    obs_groups = [
        ("Sermilik GPS (Schild21)", [0.09, 0.18], "tab:green"),
        ("Sermilik drone (Schild21)", [0.15, 0.27], "tab:green"),
        ("Sermilik DEM (Enderlin14)", [0.22, 0.59], "tab:green"),
        ("Antarctic shelf (Enderlin23)", [0.014, 0.137], "tab:orange"),
    ]
    for i, (name, (lo, hi), col) in enumerate(obs_groups):
        ax.barh(i, hi - lo, left=lo, color=col, alpha=0.7, label="OBS " + name)
    test11 = [
        ("T11 LEGACY_FULL", 0.2599), ("T11 LEGACY_SUBM", 0.4599),
        ("T11 BULK", 0.0126), ("T11 BIGG", 0.0169),
        ("T11 BIGG+BUOY", 0.0515), ("T11 PLUME", 0.0372),
    ]
    for i, (name, v) in enumerate(test11):
        ax.plot(v, 4.5 + i * 0.8, "s", color="tab:red", ms=5)
        ax.text(v, 4.5 + i * 0.8 + 0.25, name, fontsize=5.5, color="tab:red")
    ax.axhline(4.4, color="grey", lw=0.8)
    ax.text(0.6, 4.55, "MODEL: TEST_11 30-day mean (Jan 2020 experiment, NOT an observation)",
            fontsize=7, color="tab:red")
    ax.set_xlabel("melt rate [m/day]")
    ax.set_xlim(0, 0.8)
    ax.set_yticks([])
    ax.set_title("Fig 9. Observed lateral/submarine melt ranges vs TEST_11 model means")
    ax.legend(fontsize=6, loc="lower right")
    ax.grid(alpha=0.3, axis="x")
    fig.savefig(PLOTS / "fig09_obs_vs_test11.png")
    plt.close(fig)

    # fig10: parameterization constraint matrix (heatmap)
    cm = constraint_matrix(rows, bounded)
    cell = [[str(x) for x in row] for row in cm[["parameterization", "direct_evidence",
                                                  "velocity_dependency_supported",
                                                  "sample_size", "production_ready",
                                                  "confidence"]].values]
    col_lab = ["parameterization", "direct evidence", "velocity support",
               "N", "prod-ready", "confidence"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis("off")
    tbl = ax.table(cellText=cell, colLabels=col_lab, loc="center", cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    tbl.scale(1, 1.6)
    ax.set_title("Fig 10. Parameterization constraint matrix (10.18B)")
    fig.savefig(PLOTS / "fig10_constraint_matrix.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    log(f"# Stage 10.18B analysis — {datetime.now(UTC).isoformat()}")
    log(f"raw dataset: {RAW}")

    normalize(RAW, OUT / "observational_dataset_normalized.csv")
    build_provenance(RAW, OUT / "observational_provenance.csv")
    literature_parameterizations(OUT / "literature_parameterizations.csv")

    cases = load_cases(OUT / "observational_dataset_normalized.csv")
    regime_matrix(cases, OUT / "parameterization_regime_matrix.csv")
    log(f"loaded {len(cases)} normalized cases")

    rows = comparison_table(cases)
    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(OUT / "model_observation_comparison.csv", index=False)
    log(f"comparison table: {len(rows)} rows (6 models x {len(cases)} cases)")

    # statistics
    stats = {m: metrics(rows, m) for m in MODELS}
    filtered = metrics_filtered(rows)
    stat_rows = []
    for m in MODELS:
        mtr = stats[m]
        stat_rows.append({"dataset": "DIRECTLY_COMPARABLE", "model": m, **mtr})
    for k, v in filtered.items():
        ds, m = k.split("_", 1)
        stat_rows.append({"dataset": ds, "model": m, **v})
    pd.DataFrame(stat_rows).to_csv(OUT / "statistics_summary.csv", index=False)
    log("statistics summary written")

    sources = sorted({r["source_id"] for r in rows})
    loso = leave_one_source_out(rows, sources)
    loso_rows = [{"model": m, **v} if isinstance(v, dict) else {"model": m, "note": str(v)}
                 for m, v in loso.items()]
    pd.DataFrame(loso_rows).to_csv(OUT / "leave_one_source_out.csv", index=False)
    log(f"leave-one-source-out: {loso}")

    # C_eff
    c_eff_rows = c_eff_table(cases)
    pd.DataFrame(c_eff_rows).to_csv(OUT / "effective_c_lateral.csv", index=False)
    c_eff_stats_out = c_eff_stats(c_eff_rows)
    log(f"C_eff: N={c_eff_stats_out['N']}, median={c_eff_stats_out['median']:.2e} "
        f"m/(s K) ({c_eff_stats_out['median_over_production']:.2f}x production)")

    # bounded comparison
    bounded = bounded_comparison(rows)
    log(f"bounded comparison (lateral <= submarine): "
        f"{ {m: (b['N_usable'], b['N_violations']) for m, b in bounded.items()} }")

    # constraint matrix
    cm = constraint_matrix(rows, bounded)
    cm.to_csv(OUT / "parameterization_constraint_matrix.csv", index=False)

    make_figures(cases, rows, c_eff_rows, cmp_df, bounded,
                 test11_pred=None)

    summary = {
        "stage": "10.18B",
        "generated_utc": datetime.now(UTC).isoformat(),
        "n_cases": len(cases),
        "n_sources": len(sources),
        "sources": sources,
        "direct_cases": sum(1 for c in cases if c.directness == "DIRECT"),
        "indirect_cases": sum(1 for c in cases if c.directness == "INDIRECT"),
        "directly_comparable_cases": sum(1 for c in cases
                                         if c.comparability == "DIRECTLY_COMPARABLE"),
        "statistics": stats,
        "filtered_metrics": filtered,
        "effective_c_lateral": c_eff_stats_out,
        "bounded_comparison": {m: {"N_usable": b["N_usable"],
                                   "N_violations": b["N_violations"]}
                               for m, b in bounded.items()},
        "production_physics_changed": False,
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    (OUT / "reproducibility.log").write_text("\n".join(LOG) + "\n")
    log(f"figures: {len(list(PLOTS.glob('fig*.png')))}")
    log("Stage 10.18B analysis complete.")


if __name__ == "__main__":
    main()