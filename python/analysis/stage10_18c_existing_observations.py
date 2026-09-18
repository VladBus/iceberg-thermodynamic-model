#!/usr/bin/env python3
"""
Stage 10.18C — Existing Observations Reanalysis and Velocity-Resolved Melt
Constraint.

Reads the versioned Stage 10.18C observational dataset
(data/validation/observations/stage10.18c/observations.csv) and produces:
- independence summary (independent groups, not inflated row counts);
- comparison matrix (6 Stage 10.18A parameterizations vs corrected
  observational subsets, with explicit comparison_status);
- velocity-resolved subset (cases with simultaneous melt + delta_T + U_rel);
- separate effective-coefficient diagnostics: C_eff_lab_lateral (RH80 fit
  evaluations, curve evaluation only) and C_eff_submarine (field);
- temperature-dependence diagnostics (RH80 fit exponent by construction;
  Enderlin23 submarine thermal sensitivity, kept submarine);
- observational gap matrix (variable x source: YES/PARTIAL/NO);
- figures (10) and machine-readable outputs (summary.json, log).

Methodological corrections applied (vs Stage 10.18B):
  * RH80 rows = PUBLISHED_FIT_EVALUATION, independent_case=FALSE;
  * field melt = SUBMARINE_TOTAL (never lateral); u_ice is never U_rel;
  * no mixed C_eff distribution; no RMSE over dependent observations.

Outputs (gitignored): data/output/stage10.18c/

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/analysis/stage10_18c_existing_observations.py
"""

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
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

DATA = REPO / "data" / "validation" / "observations" / "stage10.18c" / "observations.csv"
OUT = REPO / "data" / "output" / "stage10.18c"
PLOTS = OUT / "plots"

MODELS = ["LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED", "BULK_FORCED",
          "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"]

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


# ---------------------------------------------------------------------------
# Independence summary
# ---------------------------------------------------------------------------
def independence_summary(rows: list[dict]) -> dict:
    groups = {}
    for r in rows:
        g = r["independence_group"]
        if r["observation_type"] == "VELOCITY_REFERENCE":
            continue  # not a melt observation
        groups.setdefault(g, {"source": r["source_id"], "n_rows": 0,
                              "n_units_note": ""})
        groups[g]["n_rows"] += 1
    # unit counts: RH80 = 1 fit; ENDERLIN14 = 1 aggregate (10 bergs per paper);
    # SCHILD21 = 2 icebergs; ENDERLIN23 = 4 region aggregates (individual
    # dataset identified at USAP-DC 10.15784/601679 but not anonymously
    # retrievable in this session -> region aggregates retained).
    units = {
        "RH80_SINGLE_FIT": ("RH80", 1, "single published laboratory fit"),
        "ENDERLIN14_REGION": ("ENDERLIN14", 1, "aggregate over 10 icebergs (paper-level)"),
        "SCHILD21_ICEBERG_A": ("SCHILD21", 1, "one independent iceberg"),
        "SCHILD21_ICEBERG_B": ("SCHILD21", 1, "one independent iceberg"),
        "ENDERLIN23_REGION_WAP": ("ENDERLIN23", 1, "regional aggregate (max); individual data at USAP-DC not retrieved"),
        "ENDERLIN23_REGION_WAIS": ("ENDERLIN23", 1, "regional aggregate (max)"),
        "ENDERLIN23_REGION_EAIS": ("ENDERLIN23", 1, "regional aggregate (max)"),
        "ENDERLIN23_REGION_EAP": ("ENDERLIN23", 1, "regional aggregate (max)"),
    }
    return {
        "independent_groups": len(units),
        "independent_observational_units": sum(1 for _, (_, n, _) in units.items() if n == 1),
        "groups": {g: {"source": s, "n_rows": groups[g]["n_rows"], "note": note}
                   for g, (s, _, note) in units.items()},
    }


# ---------------------------------------------------------------------------
# Comparison matrix (corrected statuses)
# ---------------------------------------------------------------------------
def predict_rate(r: dict, model: str) -> float:
    dT = _f(r["delta_T"])
    if math.isnan(dT) or math.isnan(_f(r["melt_rate"])):
        return float("nan")
    if model in ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED"):
        return m_s_to_m_day(legacy_lateral_melt_rate(dT))
    u = _f(r["u_rel_speed"])
    if math.isnan(u):
        return float("nan")
    L, D = _f(r["length"]), _f(r["draft"])
    if model == "BULK_FORCED":
        return float("nan") if math.isnan(D) else m_s_to_m_day(bulk_velocity_dependent_side_melt(dT, u, D))
    if model == "BIGG1997":
        return float("nan") if math.isnan(L) else m_s_to_m_day(bigg1997_forced_convection_melt_rate(u, dT, L))
    if model == "BIGG_PLUS_BUOY":
        if math.isnan(L):
            return float("nan")
        return m_s_to_m_day(bigg1997_forced_convection_melt_rate(u, dT, L)
                            + neshyba_josberger_buoyant_melt_rate(dT))
    if model == "FITZMAURICE_PLUME":
        if math.isnan(L) or math.isnan(D):
            return float("nan")
        return m_s_to_m_day(fitzmaurice_plume_side_melt(u, dT, L, D))
    return float("nan")


def comparison_matrix(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        if r["observation_type"] in ("VELOCITY_REFERENCE", "MODEL_DERIVED_REFERENCE"):
            continue
        obs = _f(r["melt_rate"])
        for m in MODELS:
            pred = predict_rate(r, m)
            status = "INSUFFICIENT_INPUTS"
            if not math.isnan(pred) and not math.isnan(obs):
                status = "DIRECT_COMPARABLE" if r["melt_definition"] == "LATERAL_ONLY" else "BOUNDED"
            elif not math.isnan(pred):
                status = "QUALITATIVE"
            out.append({
                "model": m, "source_id": r["source_id"], "case_id": r["case_id"],
                "melt_definition": r["melt_definition"],
                "observation_type": r["observation_type"],
                "independent_case": r["independent_case"],
                "delta_T_available": not math.isnan(_f(r["delta_T"])),
                "U_rel_available": not math.isnan(_f(r["u_rel_speed"])),
                "geometry_available": not math.isnan(_f(r["draft"])),
                "comparison_status": status,
                "prediction_m_day": pred,
                "observed_m_day": obs if not math.isnan(obs) else None,
                "residual_m_day": pred - obs if (not math.isnan(pred) and not math.isnan(obs)) else None,
            })
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Velocity-resolved subset (melt + delta_T + U_rel simultaneously)
# ---------------------------------------------------------------------------
def velocity_resolved(rows: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cases with melt + delta_T + U_rel simultaneously available.

    Returns (all, field_only). The RH80 laboratory rows qualify (U=0 known by
    experiment); no FIELD case qualifies (no paired relative velocity)."""
    all_rows = []
    for r in rows:
        if r["observation_type"] in ("VELOCITY_REFERENCE", "MODEL_DERIVED_REFERENCE"):
            continue
        if (not math.isnan(_f(r["melt_rate"]))
                and not math.isnan(_f(r["delta_T"]))
                and not math.isnan(_f(r["u_rel_speed"]))):
            all_rows.append(r)
    field = [r for r in all_rows if r["source_id"] != "RH80"]
    return pd.DataFrame(all_rows), pd.DataFrame(field)


# ---------------------------------------------------------------------------
# Effective coefficients — SEPARATE
# ---------------------------------------------------------------------------
def c_eff_lab_lateral(rows: list[dict]) -> dict:
    """RH80 fit evaluations ONLY: C_eff = m_lateral/delta_T. Curve evaluation,
    not independent-sample statistics."""
    vals = []
    for r in rows:
        if r["observation_type"] != "PUBLISHED_FIT_EVALUATION":
            continue
        dT = _f(r["delta_T"])
        m = _f(r["melt_rate"])
        if math.isnan(dT) or math.isnan(m) or dT <= 0:
            continue
        vals.append((m / 86400.0) / dT)
    if not vals:
        return {"N_points": 0}
    v = np.array(vals)
    return {
        "N_points": len(v),
        "kind": "curve evaluation of one published fit (RH80), NOT independent",
        "median_m_per_s_K": float(np.median(v)),
        "min": float(np.min(v)), "max": float(np.max(v)),
        "median_over_production": float(np.median(v) / C_LATERAL),
    }


def c_eff_submarine(rows: list[dict]) -> dict:
    """Field submarine (side+basal) melt effective coefficient = m_submarine/
    delta_T. NOT a lateral coefficient."""
    vals = []
    for r in rows:
        if r["observation_type"] not in ("INDIRECT_SUBMARINE", "DIRECT_SUBMARINE"):
            continue
        dT = _f(r["delta_T"])
        m = _f(r["melt_rate"])
        if math.isnan(dT) or math.isnan(m) or dT <= 0:
            continue
        vals.append((m / 86400.0) / dT)
    if not vals:
        return {"N": 0, "note": "no field submarine cases with delta_T"}
    v = np.array(vals)
    return {
        "N": len(v),
        "kind": "SUBMARINE_TOTAL_EFFECTIVE_COEFFICIENT (side+basal), NOT lateral",
        "median_m_per_s_K": float(np.median(v)),
        "min": float(np.min(v)), "max": float(np.max(v)),
        "median_over_production": float(np.median(v) / C_LATERAL),
    }


# ---------------------------------------------------------------------------
# Gap matrix
# ---------------------------------------------------------------------------
def gap_matrix(rows: list[dict]) -> pd.DataFrame:
    sources = ["RH80", "ENDERLIN14", "SCHILD21", "ENDERLIN23", "MOYER19"]
    variables = {
        "lateral melt": lambda r: "YES" if r["melt_definition"] == "LATERAL_ONLY" else "NO",
        "submarine melt": lambda r: "YES" if r["melt_definition"] == "SUBMARINE_TOTAL" else "NO",
        "delta_T": lambda r: "YES" if not math.isnan(_f(r["delta_T"])) else "NO",
        "U_ice": lambda r: "YES" if not math.isnan(_f(r["ice_speed"])) else ("PARTIAL" if r["u_ice"] not in ("NA", "") else "NO"),
        "U_ocean": lambda r: "YES" if not math.isnan(_f(r["ocean_speed"])) else "NO",
        "U_rel": lambda r: "YES" if not math.isnan(_f(r["u_rel_speed"])) else "NO",
        "depth-resolved T": lambda r: "PARTIAL" if r["source_id"] == "SCHILD21" else "NO",
        "depth-resolved U": lambda r: "NO",
        "draft": lambda r: "YES" if not math.isnan(_f(r["draft"])) else "NO",
        "full geometry": lambda r: "PARTIAL" if r["source_id"] in ("SCHILD21",) else "NO",
        "side/basal separation": lambda r: "NO",
        "wave data": lambda r: "NO",
        "uncertainty": lambda r: "YES" if not math.isnan(_f(r["melt_uncertainty"])) else "NO",
    }
    out = {}
    for var, fn in variables.items():
        row = {}
        for s in sources:
            sub = [r for r in rows if r["source_id"] == s]
            row[s] = "YES" if any(fn(r) == "YES" for r in sub) else (
                "PARTIAL" if any(fn(r) == "PARTIAL" for r in sub) else "NO")
        out[var] = row
    return pd.DataFrame(out).T


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def make_figures(rows, cm, gap, n_vr_field, c_lab, c_sub):
    # fig01: source map (lat/lon with NA -> synthetic placement)
    fig, ax = plt.subplots(figsize=(8, 5))
    seen = {}
    for r in rows:
        s = r["source_id"]
        lat, lon = _f(r["latitude"]), _f(r["longitude"])
        if math.isnan(lat) or math.isnan(lon):
            continue
        ax.scatter(lon, lat, s=40, label=s if s not in seen else None)
        ax.annotate(s, (lon, lat), fontsize=7)
        seen[s] = True
    ax.set_xlabel("longitude [deg]")
    ax.set_ylabel("latitude [deg]")
    ax.set_title("Fig 1. Observational source map (RH80 lab not plotted)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.savefig(PLOTS / "fig01_source_map.png")
    plt.close(fig)

    # fig02: melt by source/environment, distinguishing lateral/submarine/fit
    fig, ax = plt.subplots(figsize=(9, 5))
    style = {"PUBLISHED_FIT_EVALUATION": ("o", "tab:blue", "lateral (lab fit)"),
             "INDIRECT_SUBMARINE": ("s", "tab:green", "submarine total (field)")}
    for r in rows:
        if r["observation_type"] not in style:
            continue
        m = _f(r["melt_rate"])
        if math.isnan(m):
            continue
        mk, col, lab = style[r["observation_type"]]
        ax.scatter(r["source_id"] + ":" + r["case_id"], m, marker=mk, color=col,
                   s=45, label=lab if lab not in ax.get_legend_handles_labels()[1] else None)
    ax.set_yscale("log")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 2. Melt rate by source (lateral vs submarine total vs fit)")
    ax.tick_params(axis="x", rotation=60, labelsize=6)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig02_melt_by_source.png")
    plt.close(fig)

    # fig03: RH80 m vs dT with the published fit (curve, not independent pts)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    rh = [r for r in rows if r["observation_type"] == "PUBLISHED_FIT_EVALUATION"]
    dts = [_f(r["delta_T"]) for r in rh]
    ms = [_f(r["melt_rate"]) for r in rh]
    ax.plot(dts, ms, "o", color="tab:blue", ms=5, label="RH80 fit evaluations")
    d = np.linspace(1, 21, 100)
    ax.plot(d, 1.8e-2 * d ** 1.5, "-", color="tab:orange",
            label="published fit R=1.8e-2*dT^1.5")
    ax.set_xlabel("dT = T+1.8 [K]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 3. RH80 lab: m vs dT (ONE published fit, not independent points)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig03_rh80_fit.png")
    plt.close(fig)

    # fig04: field submarine melt vs delta_T
    fig, ax = plt.subplots(figsize=(7, 4.5))
    field = [r for r in rows if r["observation_type"] == "INDIRECT_SUBMARINE"]
    for r in field:
        dT, m = _f(r["delta_T"]), _f(r["melt_rate"])
        unc = _f(r["melt_uncertainty"])
        if math.isnan(dT) or math.isnan(m):
            continue
        ax.errorbar(dT, m, yerr=unc if not math.isnan(unc) else None,
                    fmt="s", ms=5, capsize=3, label=r["case_id"])
    ax.set_xlabel("delta_T [K] (reported-range midpoints, documented)")
    ax.set_ylabel("submarine melt [m/day]")
    ax.set_title("Fig 4. Field submarine (side+basal) melt vs delta_T")
    ax.legend(fontsize=6)
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig04_field_submarine.png")
    plt.close(fig)

    # fig05: velocity-resolved availability diagnostic (no U_rel cases expected)
    fig, ax = plt.subplots(figsize=(8, 4))
    n_vr = n_vr_field
    ax.text(0.5, 0.6, f"velocity-resolved cases (melt+dT+U_rel): {n_vr}",
            ha="center", transform=ax.transAxes, fontsize=12)
    ax.text(0.5, 0.35,
            "no field case provides simultaneous melt, thermal forcing and\n"
            "relative velocity from the existing public datasets ->\n"
            "velocity dependence NOT IDENTIFIABLE quantitatively",
            ha="center", transform=ax.transAxes, fontsize=9)
    ax.axis("off")
    ax.set_title("Fig 5. Velocity-resolved data availability")
    fig.savefig(PLOTS / "fig05_velocity_availability.png")
    plt.close(fig)

    # fig06: depth-resolved dT(z) for Schild21 (qualitative hydrography)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.text(0.5, 0.5,
            "Schild21: 13 CTD casts (16-21 Jul 2017); Polar Water ~10-150 m,\n"
            "Atlantic Water below ~150 m, warming below ~250 m (qualitative,\n"
            "Figure 2 of the paper; no numeric profile table recovered).\n"
            "Depth-resolved dT(z) and U(z) NOT quantitatively recoverable.",
            ha="center", va="center", transform=ax.transAxes, fontsize=9)
    ax.axis("off")
    ax.set_title("Fig 6. Depth-resolved thermal forcing — Schild21")
    fig.savefig(PLOTS / "fig06_depth_forcing.png")
    plt.close(fig)

    # fig07: draft / area / melt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for r in rows:
        d = _f(r["draft"]); m = _f(r["melt_rate"])
        if math.isnan(d) or math.isnan(m):
            continue
        ax.scatter(d, m, s=40, label=r["case_id"])
        ax.annotate(r["case_id"], (d, m), fontsize=6, textcoords="offset points",
                    xytext=(3, 3))
    ax.set_xlabel("draft [m]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Fig 7. Melt rate vs draft (Schild21: 2 points; field aggregates lack per-iceberg draft)")
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig07_draft_melt.png")
    plt.close(fig)

    # fig08: model vs corrected subsets (only DIRECT_COMPARABLE / BOUNDED)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    usable = cm[cm["comparison_status"].isin(["DIRECT_COMPARABLE", "BOUNDED"])]
    x = np.arange(len(MODELS))
    for i, m in enumerate(MODELS):
        sub = usable[usable["model"] == m]
        if len(sub):
            ax.scatter([i] * len(sub), sub["residual_m_day"].astype(float),
                       s=30, label=m)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(MODELS, rotation=20, fontsize=7)
    ax.set_ylabel("prediction - observation [m/day]")
    ax.set_title("Fig 8. Residuals vs corrected observational subsets\n"
                 "(DIRECT_COMPARABLE = RH80 lateral lab; BOUNDED = Enderlin23 submarine)")
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig08_residuals_corrected.png")
    plt.close(fig)

    # fig09: constraint matrix
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    rows_tbl = [
        ["quantity", "constrained?", "evidence"],
        ["lateral melt (lab)", "YES (lab only)", "RH80 fit"],
        ["submarine melt", "YES (bounds)", "Enderlin14/23, Schild21"],
        ["temperature dependence", "PARTIAL", "RH80 dT^1.5; Enderlin23 slope (submarine)"],
        ["velocity dependence", "NOT IDENTIFIABLE", "no paired U_rel"],
        ["depth dependence", "QUALITATIVE", "Schild21 hydrography"],
        ["geometry (full vs submerged)", "NOT CONSTRAINED", "no vertical melt distribution"],
        ["side vs basal", "NOT CONSTRAINED", "all field melt is submarine total"],
        ["wave erosion", "NOT CONSTRAINED", "no wave data"],
    ]
    tbl = ax.table(cellText=rows_tbl, loc="center", cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.5)
    ax.set_title("Fig 9. Observational constraint matrix (Stage 10.18C)")
    fig.savefig(PLOTS / "fig09_constraint_matrix.png")
    plt.close(fig)

    # fig10: gap matrix heatmap
    fig, ax = plt.subplots(figsize=(9, 6))
    g = gap.astype(str)
    code = g.replace({"YES": 1.0, "PARTIAL": 0.5, "NO": 0.0}).astype(float)
    im = ax.imshow(code.values, cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(g.columns)))
    ax.set_xticklabels(g.columns, rotation=30, fontsize=8)
    ax.set_yticks(range(len(g.index)))
    ax.set_yticklabels(g.index, fontsize=8)
    for i in range(len(g.index)):
        for j in range(len(g.columns)):
            ax.text(j, i, g.values[i, j], ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="YES=1, PARTIAL=0.5, NO=0")
    ax.set_title("Fig 10. Observational gap matrix (variable x source)")
    fig.savefig(PLOTS / "fig10_gap_matrix.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    log(f"# Stage 10.18C analysis — {datetime.now(UTC).isoformat()}")
    log(f"dataset: {DATA}")

    rows = load()
    if not rows:
        raise SystemExit("FAIL: observational dataset is empty — required source data missing")
    log(f"loaded {len(rows)} rows from {DATA.name}")

    indep = independence_summary(rows)
    log(f"independent groups: {indep['independent_groups']}; "
        f"independent observational units: {indep['independent_observational_units']}")
    pd.DataFrame(indep["groups"]).T.to_csv(OUT / "independence_groups.csv")

    cm = comparison_matrix(rows)
    cm.to_csv(OUT / "comparison_matrix.csv", index=False)
    n_direct = len(cm[cm["comparison_status"] == "DIRECT_COMPARABLE"])
    n_bounded = len(cm[cm["comparison_status"] == "BOUNDED"])
    log(f"comparison matrix: {len(cm)} rows; DIRECT_COMPARABLE cells={n_direct}, "
        f"BOUNDED cells={n_bounded}")

    vr, vr_field = velocity_resolved(rows)
    vr.to_csv(OUT / "velocity_resolved_observations.csv", index=False)
    log(f"velocity-resolved cases (melt+dT+U_rel): total={len(vr)} "
        f"(all RH80 lab, U=0), FIELD={len(vr_field)}")

    c_lab = c_eff_lab_lateral(rows)
    c_sub = c_eff_submarine(rows)
    log(f"C_eff_lab_lateral (RH80 fit evals): {c_lab}")
    log(f"C_eff_submarine (field): {c_sub}")

    # temperature dependence
    rh = [r for r in rows if r["observation_type"] == "PUBLISHED_FIT_EVALUATION"]
    fit_exponent = 1.5  # RH80 published relationship exponent (by construction)
    end23 = [r for r in rows if r["source_id"] == "ENDERLIN23"]
    submarine_slope_m_per_day_per_K = 24.0 / 365.0  # 24 m/a per degC (Thwaites)
    temp_dep = {
        "RH80_fit_exponent": fit_exponent,
        "RH80_fit_note": "exponent from the published relationship, NOT fitted here",
        "ENDERLIN23_thwaites_slope_m_per_day_per_K": submarine_slope_m_per_day_per_K,
        "ENDERLIN23_slope_kind": "SUBMARINE_TOTAL thermal sensitivity, NOT lateral",
        "slope_over_legacy_m_per_day_per_K": submarine_slope_m_per_day_per_K / (C_LATERAL * 86400.0),
    }

    gap = gap_matrix(rows)
    gap.to_csv(OUT / "observational_gap_matrix.csv")

    make_figures(rows, cm, gap, len(vr_field), c_lab, c_sub)

    summary = {
        "stage": "10.18C",
        "generated_utc": datetime.now(UTC).isoformat(),
        "production_physics_changed": False,
        "n_rows": len(rows),
        "independence": indep,
        "comparison_matrix_cells": {
            "DIRECT_COMPARABLE": int(n_direct), "BOUNDED": int(n_bounded)},
        "velocity_resolved_cases_total": int(len(vr)),
        "velocity_resolved_cases_FIELD": int(len(vr_field)),
        "c_eff_lab_lateral": c_lab,
        "c_eff_submarine": c_sub,
        "temperature_dependence": temp_dep,
        "uq1_independent_icebergs": sum(1 for g, v in indep["groups"].items()
                                        if "ICEBERG" in g),
        "uq2_direct_lateral_cases": sum(1 for r in rows
                                        if r["melt_definition"] == "LATERAL_ONLY"),
        "uq3_submarine_cases": sum(1 for r in rows
                                   if r["melt_definition"] == "SUBMARINE_TOTAL"),
        "uq4_melt_dT_Urel_simultaneous": int(len(vr)),
        "uq4_melt_dT_Urel_simultaneous_FIELD": int(len(vr_field)),
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    (OUT / "reproducibility.log").write_text("\n".join(LOG) + "\n")
    log(f"figures: {len(list(PLOTS.glob('fig*.png')))}")
    log("Stage 10.18C analysis complete.")


if __name__ == "__main__":
    main()