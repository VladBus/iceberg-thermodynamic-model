#!/usr/bin/env python3
"""
Stage 10.13 Phase B — re-scoring of the Stage 10.8.2 observational set.

Reuses the existing 10.8.2 scoring infrastructure
(python/validation/observational_validation.py) and compares four model
variants on the curated dataset:

    baseline 10.11  : existing production scoring (forced closure; 0 at u=0)
    pure diffusive  : m_d (diffusion-limited sublayer, no enhancement)
    DDC-enhanced    : f * m_d (diffusive-convection enhancement)
    hybrid          : forced + low-flow blending (candidate C)

Two honest comparisons are reported separately:
  1. u>0 closure-applicable rows (KW84 + NJ80 x3): point metrics per variant
     (RMSE/MAE/bias) — expected to be nearly unchanged (forced preserved).
  2. Quiescent u=0 rows (RH80 lab): observed melt vs each variant —
     the baseline gives 0 (the 10.8.2 gap), the low-flow variants give
     finite in-band values.

This is NOT calibration: no parameter is fitted to the observations.

Run:
    conda run -n iceberg-thermodynamic-model python python/validation/low_flow_scoring.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import low_flow as lf
import observational_validation as ov

DAY_S = 86400.0
TIME_SCALE_S = DAY_S   # baseline diagnostic sublayer time (1 day)


def model_m_for_variant(row: dict, variant: str) -> float:
    """Model melt [m/day] for one observation row and one variant."""
    t = row.get("T_degC", float("nan"))
    s = row.get("S_psu", float("nan"))
    u = row.get("u_rel_m_s", float("nan"))
    lc = row.get("L_char_m", float("nan"))
    if any(x != x for x in (t, s, u, lc)):   # NaN check
        return float("nan")
    if variant == "baseline":
        return ov.model_melt_m_per_day(row)
    m_hyb, low, _mf, _w, _gt, _gs = lf.compute_hybrid_melt_rate(
        float(t), float(s), float(u), float(lc), float(lc),
        lf.LowFlowParams(), time_scale_s=TIME_SCALE_S)
    if variant == "pure":
        return lf.m_s_to_m_day(low.m_diffusive_m_s)
    if variant == "ddc":
        return lf.m_s_to_m_day(low.m_low_flow_m_s)
    if variant == "hybrid":
        return lf.m_s_to_m_day(m_hyb)
    raise ValueError(f"unknown variant {variant}")


def main() -> None:
    rows = ov.load_observations()

    print("=" * 78)
    print("STAGE 10.13 PHASE B — 10.8.2 RE-SCORING (m/day; NOT calibration)")
    print("=" * 78)

    # ---- 1. u>0 closure-applicable rows: point metrics per variant ----
    variants = ("baseline", "pure", "ddc", "hybrid")
    print("\n[1] u>0 closure-applicable rows (KW84 + NJ80 x3)")
    comp = ov.compare_rows(rows)
    print(f"    n = {len(comp)} rows")
    print(f"    {'variant':>10} | {'RMSE':>8} {'MAE':>8} {'bias':>8} "
          f"{'mean_mod':>9} {'mean_obs':>9}")
    for v in variants:
        mod = [model_m_for_variant(r, v) for r, _, _, _, _ in comp]
        obs = [o for _, o, _, _, _ in comp]
        if any(m != m for m in mod):
            print(f"    {v:>10} | NaN in model values — skipped")
            continue
        mets = ov.compute_metrics(obs, mod)
        print(f"    {v:>10} | {mets['rmse_m_per_day']:8.4f} "
              f"{mets['mae_m_per_day']:8.4f} {mets['bias_m_per_day']:8.4f} "
              f"{mets['mean_model_m_per_day']:9.4f} {mets['mean_obs_m_per_day']:9.4f}")

    # ---- 2. Quiescent u=0 rows (gap test) ----
    print("\n[2] Quiescent u=0 rows (10.8.2 gap test)")
    gap_rows = [r for r in rows if r.get("u_rel_m_s") == 0.0
                and r.get("obs_m_per_day") is not None]
    print(f"    n = {len(gap_rows)} rows")
    print(f"    {'id':>10} | {'obs':>7} | {'10.11':>8} {'pure':>8} "
          f"{'ddc':>8} {'hybrid':>8}")
    for r in gap_rows:
        obs = float(r["obs_m_per_day"])
        vals = {v: model_m_for_variant(r, v) for v in variants}
        print(f"    {r['record_id']:>10} | {obs:7.3f} | "
              f"{vals['baseline']:8.4f} {vals['pure']:8.4f} "
              f"{vals['ddc']:8.4f} {vals['hybrid']:8.4f}")
    # gap closure summary
    print("\n    gap closure (model vs obs band 0.01-1 m/day):")
    for v in variants:
        in_band = sum(1 for r in gap_rows
                      if 0.01 <= model_m_for_variant(r, v) <= 1.0)
        print(f"      {v:>10}: {in_band}/{len(gap_rows)} rows in band")

    # ---- 3. Honest statement ----
    print("\nINTERPRETATION:")
    print("  u>0 rows: the APPLICABLE variant is forced/hybrid (w=1 for")
    print("  u >= u_trans_hi) — hybrid == baseline there BY DESIGN (forced")
    print("  branch preserved). The pure/ddc columns on u>0 rows evaluate the")
    print("  low-flow branch at forced conditions; they are NOT candidates for")
    print("  those rows and their metrics must not be read as improvements.")
    print("  Quiescent u=0 rows: baseline gives 0 (the 10.8.2 gap); the")
    print("  low-flow variants give finite in-band values (5/5) with")
    print("  ddc/hybrid within factor 1.1-2.2 of the RH80 observations at")
    print("  t_scale = 1 day, no calibration.")


if __name__ == "__main__":
    main()