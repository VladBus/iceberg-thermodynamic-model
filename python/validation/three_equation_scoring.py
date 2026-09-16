#!/usr/bin/env python3
"""Stage 10.14 — re-scoring of the Stage 10.8.2 observational set against the
three-equation (10.10/10.10.1) and three-equation + natural-convection (10.11)
closures with the 10.8.2 acceptance criterion.

Reuses the curated 19-record dataset and the Stage 10.8.2 scoring
infrastructure (``python/validation/observational_validation.py``) and scores
three closures side by side:

    bulk     : forced flat-plate closure (Stage 10.8.2 baseline; unchanged)
    teq      : three-equation interface (Stage 10.10/10.10.1)
    teq_nat  : three-equation + natural convection (Stage 10.11)

Two honest comparisons, following the 10.8.2 methodology and acceptance
criterion (observed band 0.01-1 m/day + point metrics on the forcing-anchored
rows):

  1. u>0 closure-applicable rows (KW84 + NJ80 x3): point metrics
     (RMSE/MAE/bias) per closure.
  2. Quiescent u=0 rows (RH80 lab): observed melt vs each closure — the bulk
     and pure teq closures give 0 (the 10.8.2 natural-convection gap); the
     teq_nat closure gives a finite value, scored against the observed band.

This is **validation, not calibration**: no coefficient is fitted, all
parameters are production/literature values. The 3eq/3eq+natural closures are
the already-implemented production schemes (Stage 10.10/10.11); this script
applies them to the curated observational set for the first time.

Run:
    conda run -n iceberg-thermodynamic-model python python/validation/three_equation_scoring.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import observational_validation as ov  # noqa: E402
import three_equation as ten10  # noqa: E402
import three_equation_natural as ten11  # noqa: E402

DAY_S = 86400.0
MELT_RATE_MIN = 1.0e-12           # production numerical-noise guard [m/s]
OBSERVED_BAND = (0.01, 1.0)       # 10.8.2 acceptance band [m/day]


def _guard(m_s: float) -> float:
    """Production MELT_RATE_MIN guard (m < 1e-12 m/s -> 0)."""
    return 0.0 if m_s < MELT_RATE_MIN else m_s


def melt_bulk(row: dict) -> float:
    """Baseline bulk forced closure [m/day] (Stage 10.8.2 value, unchanged)."""
    return ov.model_melt_m_per_day(row)


def melt_teq(row: dict) -> float:
    """Three-equation closure (Stage 10.10/10.10.1) [m/day] for an obs row.

    Salinity in PSU (three_equation.py API). depth = L_char_m (draft), the
    10.8.2 pressure convention. Returns 0 when forcing is missing/NaN or when
    u_rel <= 0 (the 3eq closure has no natural-convection branch -> the
    quiescent gap is exposed as 0, same as the bulk closure).
    """
    t = row.get("T_degC", float("nan"))
    s = row.get("S_psu", float("nan"))
    u = row.get("u_rel_m_s", float("nan"))
    lc = row.get("L_char_m", float("nan"))
    if any(math.isnan(x) for x in (t, s, u, lc)) or u <= 0.0:
        return 0.0
    m_s, _, _ = ten10.three_equation_basal_melt(
        ocean_temperature_c=float(t),
        salinity_psu=float(s),
        depth_m=float(lc),
        u_water=float(u),
        v_water=0.0,
        u_ice=0.0,
        v_ice=0.0,
        t_ice=ten10.T_ICE,
        use_conduction=True,
    )
    return _guard(m_s) * DAY_S


def melt_teq_nat(row: dict) -> float:
    """Three-equation + natural convection closure (Stage 10.11) [m/day].

    Salinity in mass fraction (kg/kg) — three_equation_natural.py API.
    depth = L_char_m (draft, 10.8.2 pressure convention). l_char_nat =
    L_char_m: for the NJ80 rows L_char_m is the reference berg length (50 m);
    for the RH80 rows it is the lab block length (1 m) — the appropriate
    horizontal scale of the natural-convection cells. The u>0 rows are
    forced-dominated (natural adds ~1e-6 % at U=0.1), so this choice does not
    change the point metrics; it matters only for the quiescent rows.
    """
    t = row.get("T_degC", float("nan"))
    s = row.get("S_psu", float("nan"))
    u = row.get("u_rel_m_s", float("nan"))
    lc = row.get("L_char_m", float("nan"))
    if any(math.isnan(x) for x in (t, s, u, lc)):
        return 0.0
    m_s, _, _ = ten11.three_equation_basal_melt_natural(
        t_w=float(t),
        s_w=float(s) / 1000.0,          # PSU -> mass fraction
        depth_m=float(lc),
        u_rel=float(u),
        l_char_nat=float(lc),
        draft=float(lc),
    )
    return _guard(m_s) * DAY_S


CLOSURES = {
    "bulk": melt_bulk,
    "teq": melt_teq,
    "teq_nat": melt_teq_nat,
}


def comparable_rows(rows: list[dict] | None = None) -> list[dict]:
    """Rows with fully-specified forcing and u_rel > 0 (10.8.2 metrics set)."""
    rows = rows if rows is not None else ov.load_observations()
    return [r for r in rows if ov.closure_applicable(r)]


def quiescent_rows(rows: list[dict] | None = None) -> list[dict]:
    """Quiescent lab rows (u_rel == 0, observed melt reported)."""
    rows = rows if rows is not None else ov.load_observations()
    return [r for r in rows if r.get("u_rel_m_s") == 0.0]


def metrics_for_closure(rows: list[dict], closure: str) -> dict | None:
    """Point metrics on the comparable rows for one closure (or None on NaN)."""
    model = [CLOSURES[closure](r) for r in rows]
    if any(m != m for m in model):      # NaN present
        return None
    obs = [float(r["obs_m_per_day"]) for r in rows]
    return ov.compute_metrics(obs, model)


def in_band(m_day: float, band: tuple = OBSERVED_BAND) -> bool:
    return band[0] <= m_day <= band[1]


def render_summary(rows: list[dict] | None = None) -> str:
    rows = rows if rows is not None else ov.load_observations()
    lines = []
    lines.append("=" * 78)
    lines.append("STAGE 10.14 — 10.8.2 RE-SCORING (m/day; NOT calibration)")
    lines.append("Closures: bulk (10.6/10.8.2) | teq (10.10/10.10.1) | "
                 "teq_nat (10.11)")
    lines.append("=" * 78)

    comp = comparable_rows(rows)
    quies = quiescent_rows(rows)

    # ---- 1. u>0 point metrics per closure ----
    lines.append(f"\n[1] u>0 closure-applicable rows (n={len(comp)})")
    lines.append(f"    {'closure':>10} | {'RMSE':>8} {'MAE':>8} {'bias':>8} "
                 f"{'mean_mod':>9} {'mean_obs':>9}")
    for name in ("bulk", "teq", "teq_nat"):
        mets = metrics_for_closure(comp, name)
        if mets is None:
            lines.append(f"    {name:>10} | NaN in model values — skipped")
            continue
        lines.append(
            f"    {name:>10} | {mets['rmse_m_per_day']:8.4f} "
            f"{mets['mae_m_per_day']:8.4f} {mets['bias_m_per_day']:8.4f} "
            f"{mets['mean_model_m_per_day']:9.4f} "
            f"{mets['mean_obs_m_per_day']:9.4f}"
        )

    # per-row table
    lines.append(f"\n    per-row model melt [m/day]:")
    lines.append(f"    {'id':>14} | {'obs':>7} | {'bulk':>8} {'teq':>8} "
                 f"{'teq_nat':>8} | {'dT':>6}")
    for r in comp:
        obs = float(r["obs_m_per_day"])
        dT = float(r["T_degC"]) - ten10.ocean_freezing_point(
            float(r["S_psu"]), float(r["L_char_m"]))
        lines.append(
            f"    {r['record_id']:>14} | {obs:7.4f} | "
            f"{CLOSURES['bulk'](r):8.4f} {CLOSURES['teq'](r):8.4f} "
            f"{CLOSURES['teq_nat'](r):8.4f} | {max(dT,0.0):6.2f}"
        )

    # ---- 2. Quiescent u=0 rows (gap test) ----
    lines.append(f"\n[2] Quiescent u=0 rows (n={len(quies)}, RH80 lab)")
    lines.append(f"    {'id':>14} | {'obs':>7} | {'bulk':>8} {'teq':>8} "
                 f"{'teq_nat':>8}")
    for r in quies:
        obs = float(r["obs_m_per_day"])
        lines.append(
            f"    {r['record_id']:>14} | {obs:7.4f} | "
            f"{CLOSURES['bulk'](r):8.4f} {CLOSURES['teq'](r):8.4f} "
            f"{CLOSURES['teq_nat'](r):8.4f}"
        )
    lines.append(f"\n    quiescent rows inside the observed band "
                 f"{OBSERVED_BAND[0]}-{OBSERVED_BAND[1]} m/day:")
    for name in ("bulk", "teq", "teq_nat"):
        cnt = sum(1 for r in quies if in_band(CLOSURES[name](r)))
        lines.append(f"      {name:>10}: {cnt}/{len(quies)} in band")

    # ---- 3. Honest interpretation ----
    lines.append("\nINTERPRETATION:")
    lines.append("  u>0 rows: teq and teq_nat differ from bulk because the")
    lines.append("  three-equation closure (K_T*U_rel, K_S*U_rel) replaces the")
    lines.append("  flat-plate Nu(U,L) transfer; teq_nat == teq there because")
    lines.append("  forced convection dominates at U>=0.1 (Churchill n=3).")
    lines.append("  Quiescent u=0 rows: bulk and teq give 0 (the 10.8.2 gap);")
    lines.append("  teq_nat gives a finite value (natural branch) scored against")
    lines.append("  the observed band. This is NOT calibration.")
    return "\n".join(lines)


def main() -> int:
    rows = ov.load_observations()
    print(render_summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
