#!/usr/bin/env python3
"""
Stage 10.18B — observational constraint engine for lateral-melt
parameterizations.

Independent prediction/comparison layer: reads the curated observational
dataset (normalized), evaluates every Stage 10.18A lateral-melt formulation
against each case, and produces residual/statistics tables. The production
Fortran is NOT imported and NOT modified.

Dataset files (curated, in `data/output/stage10.18b/`):
    observational_sources.csv           source metadata
    observational_dataset.csv           raw case-level observations
    observational_dataset_normalized.csv  normalized (SI) cases

Parameterizations (formulas in `python/validation/lateral_melt.py`):
    LEGACY_FULL_HEIGHT  m = C_LATERAL*DeltaT            (rate only)
    LEGACY_SUBMERGED    same rate (geometry affects volume, not rate)
    BULK_FORCED         gamma_T(U_rel,D)*DeltaT/(rho_i L_f)
    BIGG1997            K*U_rel^0.8*DeltaT/L^0.2  (K=0.58, m/day)
    BIGG_PLUS_BUOY      Bigg + Neshyba-Josberger a*DeltaT+b*DeltaT^2
    FITZMAURICE_PLUME   plume-regime piecewise (T_p proxy = ambient DeltaT,
                        documented approximation)

Rule: if a formulation's required inputs are missing for a case, the
prediction is NA (no default values are substituted).

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/analysis/stage10_18b_observational_constraint.py
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .lateral_melt import (
    BIGG_K_OCEAN,
    C_LATERAL,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    fitzmaurice_plume_side_melt,
    legacy_lateral_melt_rate,
    m_day_to_m_s,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
)
from .basal_melt import RHO_ICE, RHO_WATER, ocean_freezing_point

MODELS = [
    "LEGACY_FULL_HEIGHT",
    "LEGACY_SUBMERGED",
    "BULK_FORCED",
    "BIGG1997",
    "BIGG_PLUS_BUOY",
    "FITZMAURICE_PLUME",
]

NA = float("nan")


# ---------------------------------------------------------------------------
# Case record
# ---------------------------------------------------------------------------
@dataclass
class ObservationalCase:
    """One normalized observational case (SI; melt in m/day)."""

    case_id: str
    source_id: str
    year: int
    region: str
    environment: str
    delta_t_K: float            # thermal driving used by the source (NaN if unknown)
    u_rel_m_s: float            # ice-ocean relative velocity (NaN if unknown)
    L_m: float
    D_m: float
    melt_obs_m_day: float
    melt_unc_m_day: float       # symmetric +- uncertainty (NaN if not reported)
    directness: str             # DIRECT / INDIRECT / MODEL_DERIVED / UNVERIFIED
    melt_definition: str        # side / basal+side / total / volume-loss / retreat
    measurement_method: str
    averaging_period: str
    wave_influenced: str        # TRUE / FALSE / UNKNOWN
    comparability: str          # DIRECTLY_COMPARABLE / COMPARABLE_AFTER_NORMALIZATION /
                                # QUALITATIVE_ONLY / NOT_COMPARABLE
    notes: str = ""

    def has_delta_t(self) -> bool:
        return not math.isnan(self.delta_t_K)

    def has_u_rel(self) -> bool:
        return not math.isnan(self.u_rel_m_s)

    def has_geometry(self) -> bool:
        return not math.isnan(self.L_m) and not math.isnan(self.D_m)

    def has_uncertainty(self) -> bool:
        return not math.isnan(self.melt_unc_m_day)


# ---------------------------------------------------------------------------
# Dataset I/O
# ---------------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(row for row in f if not row.lstrip().startswith("#"))
        return [dict(r) for r in reader]


def _f(v: str) -> float:
    """Parse a numeric field; NA for empty/NA/NaN values."""
    s = (v or "").strip()
    if s == "" or s.upper() in ("NA", "NAN", "NONE", "NULL", "-"):
        return NA
    try:
        return float(s)
    except ValueError:
        return NA


def load_cases(path: Path) -> list[ObservationalCase]:
    """Load the normalized observational dataset."""
    cases: list[ObservationalCase] = []
    for row in _read_csv(path):
        cases.append(ObservationalCase(
            case_id=row.get("case_id", "").strip(),
            source_id=row.get("source_id", "").strip(),
            year=_f(row.get("year", "")),
            region=row.get("region", "").strip(),
            environment=row.get("environment", "").strip(),
            delta_t_K=_f(row.get("delta_T_K", "")),
            u_rel_m_s=_f(row.get("u_rel_m_s", "")),
            L_m=_f(row.get("L_m", "")),
            D_m=_f(row.get("D_m", "")),
            melt_obs_m_day=_f(row.get("melt_obs_m_day", "")),
            melt_unc_m_day=_f(row.get("melt_unc_m_day", "")),
            directness=row.get("directness", "").strip(),
            melt_definition=row.get("melt_definition", "").strip(),
            measurement_method=row.get("measurement_method", "").strip(),
            averaging_period=row.get("averaging_period", "").strip(),
            wave_influenced=row.get("wave_influenced", "").strip(),
            comparability=row.get("comparability", "").strip(),
            notes=row.get("notes", "").strip(),
        ))
    return cases


# ---------------------------------------------------------------------------
# Model prediction
# ---------------------------------------------------------------------------
def predict(case: ObservationalCase, model: str) -> float:
    """Predicted lateral melt rate [m/day] for one case/model.

    Returns NA when a required input is missing. Geometry variants
    (LEGACY_FULL_HEIGHT vs LEGACY_SUBMERGED) share the same rate; the
    geometry convention affects the *volume* loss, handled separately in
    `implied_volume_loss`.
    """
    if not case.has_delta_t() or math.isnan(case.melt_obs_m_day):
        return NA
    dT = case.delta_t_K
    if model == "LEGACY_FULL_HEIGHT" or model == "LEGACY_SUBMERGED":
        return m_s_to_m_day(legacy_lateral_melt_rate(dT))
    if not case.has_u_rel():
        return NA
    u = case.u_rel_m_s
    if model == "BULK_FORCED":
        if not case.has_geometry():
            return NA
        return m_s_to_m_day(bulk_velocity_dependent_side_melt(dT, u, case.D_m))
    if model == "BIGG1997":
        if not case.has_geometry():
            return NA
        return m_s_to_m_day(bigg1997_forced_convection_melt_rate(u, dT, case.L_m))
    if model == "BIGG_PLUS_BUOY":
        if not case.has_geometry():
            return NA
        m_b = bigg1997_forced_convection_melt_rate(u, dT, case.L_m)
        m_v = neshyba_josberger_buoyant_melt_rate(dT)
        return m_s_to_m_day(m_b + m_v)
    if model == "FITZMAURICE_PLUME":
        if not case.has_geometry():
            return NA
        return m_s_to_m_day(fitzmaurice_plume_side_melt(u, dT, case.L_m, case.D_m))
    raise ValueError(f"unknown model {model}")


def implied_volume_loss(case: ObservationalCase, m_day: float, days: float = 1.0) -> dict:
    """Volume loss [m3] over `days` for a given melt rate under each area
    convention. Uses the case geometry (L, D, and H = D*rho_w/rho_i inferred
    hydrostatically when missing)."""
    if math.isnan(m_day) or not case.has_geometry():
        return {"full_height_m3": NA, "submerged_m3": NA}
    L, D = case.L_m, case.D_m
    H = D * RHO_WATER / RHO_ICE
    W = L  # horizontal cross-section assumed square when width not reported
    m_s = m_day_to_m_s(m_day) * days
    a_full = H * (L + W)
    a_sub = 2.0 * (L + W) * D
    return {"full_height_m3": a_full * m_s, "submerged_m3": a_sub * m_s}


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------
def comparison_table(cases: list[ObservationalCase]) -> list[dict]:
    rows = []
    for c in cases:
        for m in MODELS:
            pred = predict(c, m)
            row = {
                "case_id": c.case_id,
                "source_id": c.source_id,
                "environment": c.environment,
                "directness": c.directness,
                "melt_definition": c.melt_definition,
                "wave_influenced": c.wave_influenced,
                "comparability": c.comparability,
                "observed_melt_m_day": c.melt_obs_m_day,
                "observed_unc_m_day": c.melt_unc_m_day,
                "model_name": m,
                "predicted_melt_m_day": pred,
            }
            if not math.isnan(pred) and not math.isnan(c.melt_obs_m_day):
                row["absolute_error_m_day"] = pred - c.melt_obs_m_day
                row["relative_error"] = (pred - c.melt_obs_m_day) / c.melt_obs_m_day
                if c.has_uncertainty():
                    row["normalized_error"] = (pred - c.melt_obs_m_day) / c.melt_unc_m_day
                else:
                    row["normalized_error"] = NA
                row["within_uncertainty"] = (
                    bool(c.has_uncertainty())
                    and abs(pred - c.melt_obs_m_day) <= c.melt_unc_m_day
                )
            else:
                row["absolute_error_m_day"] = NA
                row["relative_error"] = NA
                row["normalized_error"] = NA
                row["within_uncertainty"] = ""
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Statistics (N-weighted; never applied to incomparable cases)
# ---------------------------------------------------------------------------
def _usable(rows: list[dict], model: str, comparability: str = "DIRECTLY_COMPARABLE") -> list[dict]:
    out = []
    for r in rows:
        if r["model_name"] != model:
            continue
        if math.isnan(r["predicted_melt_m_day"]):
            continue
        if r["comparability"] != comparability:
            continue
        if r["directness"] not in ("DIRECT", "INDIRECT"):
            continue
        out.append(r)
    return out


def metrics(rows: list[dict], model: str, comparability: str = "DIRECTLY_COMPARABLE") -> dict:
    """RMSE / MAE / median / bias / coverage for one model over usable rows."""
    sub = _usable(rows, model, comparability)
    if not sub:
        return {"N": 0, "RMSE": NA, "MAE": NA, "median_err": NA, "median_abs": NA,
                "bias": NA, "coverage": NA, "n_with_unc": 0}
    errs = np.array([r["absolute_error_m_day"] for r in sub], dtype=float)
    preds = np.array([r["predicted_melt_m_day"] for r in sub], dtype=float)
    obs = np.array([r["observed_melt_m_day"] for r in sub], dtype=float)
    cov = np.array([r["within_uncertainty"] for r in sub if isinstance(r["within_uncertainty"], bool)],
                   dtype=bool)
    return {
        "N": len(sub),
        "RMSE": float(np.sqrt(np.mean(errs**2))),
        "MAE": float(np.mean(np.abs(errs))),
        "median_err": float(np.median(errs)),
        "median_abs": float(np.median(np.abs(errs))),
        "bias": float(np.mean(preds - obs)),
        "coverage": float(np.mean(cov)) if len(cov) else NA,
        "n_with_unc": int(len(cov)),
    }


def metrics_filtered(rows: list[dict]) -> dict:
    """Metrics per model for datasets A (DIRECT only) and B (DIRECT+INDIRECT)."""
    out = {}
    for dataset, dset in (("A_DIRECT", ("DIRECT",)), ("B_DIRECT_INDIRECT", ("DIRECT", "INDIRECT"))):
        for m in MODELS:
            sub = [r for r in rows if r["model_name"] == m
                   and not math.isnan(r["predicted_melt_m_day"])
                   and r["comparability"] == "DIRECTLY_COMPARABLE"
                   and r["directness"] in dset]
            if not sub:
                out[f"{dataset}_{m}"] = {"N": 0}
                continue
            errs = np.array([r["absolute_error_m_day"] for r in sub], dtype=float)
            out[f"{dataset}_{m}"] = {
                "N": len(sub),
                "RMSE": float(np.sqrt(np.mean(errs**2))),
                "MAE": float(np.mean(np.abs(errs))),
                "median_abs": float(np.median(np.abs(errs))),
                "bias": float(np.mean(errs)),
            }
    return out


def leave_one_source_out(rows: list[dict], sources: list[str]) -> dict:
    """Per-model RMSE/MAE after dropping each source (N>=3 usable rows per
    model required)."""
    out = {}
    for m in MODELS:
        base = _usable(rows, m)
        if len(base) < 4:  # need at least 3 rows after dropping one source
            out[m] = {"N": len(base), "note": "NOT APPLICABLE (N too small)"}
            continue
        res = {}
        for src in sources:
            rest = [r for r in base if r["source_id"] != src]
            if len(rest) < 3:
                continue
            errs = np.array([r["absolute_error_m_day"] for r in rest], dtype=float)
            res[src] = {"N": len(rest),
                        "RMSE": float(np.sqrt(np.mean(errs**2))),
                        "MAE": float(np.mean(np.abs(errs)))}
        out[m] = res
    return out


# ---------------------------------------------------------------------------
# Effective C_LATERAL from observations
# ---------------------------------------------------------------------------
def effective_c_lateral(cases: list[ObservationalCase], max_delta_t_K: float = 8.0) -> dict:
    """C_eff = m_obs / DeltaT for cases where the legacy linear-in-DeltaT
    interpretation is applicable (rate-based side melt, known DeltaT, not
    wave-influenced). Returns the distribution (percentiles) and N."""
    vals = []
    for c in cases:
        if not c.has_delta_t():
            continue
        if c.delta_t_K <= 0.0 or c.delta_t_K > max_delta_t_K:
            continue
        if c.wave_influenced == "TRUE":
            continue
        if "total" in c.melt_definition.lower() or "basal" in c.melt_definition.lower():
            continue
        vals.append(m_day_to_m_s(c.melt_obs_m_day) / c.delta_t_K)
    if len(vals) < 3:
        return {"N": len(vals), "note": "insufficient sample"}
    v = np.array(vals)
    return {
        "N": len(v),
        "mean": float(np.mean(v)),
        "median": float(np.median(v)),
        "p10": float(np.percentile(v, 10)),
        "p25": float(np.percentile(v, 25)),
        "p75": float(np.percentile(v, 75)),
        "p90": float(np.percentile(v, 90)),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "C_LATERAL_production": C_LATERAL,
        "median_over_production": float(np.median(v) / C_LATERAL),
    }


# ---------------------------------------------------------------------------
# Regime classification (source-derived thresholds, exploratory labels)
# ---------------------------------------------------------------------------
def regime_of(case: ObservationalCase) -> dict:
    """Classify U and DeltaT regimes with explicit, literature-derived
    thresholds (exploratory)."""
    u_regime = "UNKNOWN"
    if case.has_u_rel():
        u = case.u_rel_m_s
        if u < 0.03:
            u_regime = "LOW_U"
        elif u < 0.3:
            u_regime = "MODERATE_U"
        else:
            u_regime = "HIGH_U"
    dT_regime = "UNKNOWN"
    if case.has_delta_t():
        dT = case.delta_t_K
        if dT < 1.0:
            dT_regime = "LOW_DELTAT"
        elif dT < 5.0:
            dT_regime = "MODERATE_DELTAT"
        else:
            dT_regime = "HIGH_DELTAT"
    return {"u_regime": u_regime, "dT_regime": dT_regime}


__all__ = [
    "MODELS",
    "NA",
    "ObservationalCase",
    "comparison_table",
    "effective_c_lateral",
    "implied_volume_loss",
    "leave_one_source_out",
    "load_cases",
    "metrics",
    "metrics_filtered",
    "predict",
    "regime_of",
]