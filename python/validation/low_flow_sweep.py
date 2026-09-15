#!/usr/bin/env python3
"""
Stage 10.13 Phase B — coarse parameter sweep of the low-flow closure.

Compares four melt-rate variants over a coarse but physically justified grid:

    1. Stage 10.11 baseline   (three-equation + natural convection, cap floor)
    2. pure diffusion-limited (m_d)
    3. DDC-enhanced low flow  (f * m_d)
    4. recommended hybrid     (forced + low-flow blending)

Grid: T_w in [1,2,4,6,8] C; S_w in [30,33,35] PSU; U in [0,1e-4,1e-3,1e-2,5e-2,1e-1] m/s;
      t_scale in [1 h, 1 d, 10 d]. Depth (draft) = 50 m, L_char = 100 m (representative).

Checks: NaN/Inf/negative across the whole grid; regime counts; observed-band
coverage [0.01, 1] m/day; continuity (max log10 jump vs U) for every T,S,t.

Outputs (generated, gitignored under data/):
    data/output/diagnostics/stage10.13/sweep.csv
    data/output/diagnostics/stage10.13/fig_*.png   (matplotlib, optional)

Run:
    conda run -n iceberg-thermodynamic-model python python/validation/low_flow_sweep.py
"""

from __future__ import annotations

import csv
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import low_flow as lf
import three_equation_natural as ten11

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "output" / "diagnostics" / "stage10.13"

DAY_S = 86400.0
TW_GRID = (1.0, 2.0, 4.0, 6.0, 8.0)
SW_GRID_PSU = (30.0, 33.0, 35.0)
U_GRID = (0.0, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1)
T_GRID_S = (3600.0, DAY_S, 10.0 * DAY_S)
DEPTH_M = 50.0
L_CHAR_M = 100.0

OBS_BAND = (0.01, 1.0)   # m/day, quiescent band from Stage 10.8.2


def baseline_natural_m(t_w: float, s_w_psu: float, u: float) -> float:
    """Stage 10.11 baseline melt [m/s] via the natural-convection solver.

    NOTE: the solver returns (m, t_b, s_b) — verified by direct call
    (the module's __main__ docstring example showing (t_b, s_b, m) is
    incorrect; recorded as a found doc bug in the Phase B report).
    """
    m, _t_b, _s_b = ten11.three_equation_basal_melt_natural(
        t_w, s_w_psu / 1000.0, DEPTH_M, u, L_CHAR_M)
    return m


def one_point(t_w: float, s_w: float, u: float, t_scale: float):
    """Return dict with all four variants (m in m/s) + diagnostics."""
    m_base = baseline_natural_m(t_w, s_w, u)
    m_hyb, low, m_f, w, gt, gs = lf.compute_hybrid_melt_rate(
        t_w, s_w, u, L_CHAR_M, DEPTH_M, lf.LowFlowParams(), time_scale_s=t_scale)
    return {
        "T_w": t_w, "S_w_psu": s_w, "U_m_s": u, "t_s": t_scale,
        "m_baseline_m_s": m_base,
        "m_pure_diff_m_s": low.m_diffusive_m_s,
        "m_ddc_m_s": low.m_low_flow_m_s,
        "m_hybrid_m_s": m_hyb,
        "m_forced_m_s": m_f,
        "w_blend": w,
        "f_enhance": low.enhancement_factor,
        "delta_S_m": low.delta_s_m,
        "R_rho": low.r_rho,
        "Ri_star": low.ri_star,
        "Re_b": low.re_b,
        "regime": low.regime,
        "bounds": ";".join(low.bounds_triggered),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    n_nan = n_neg = 0
    for t_w in TW_GRID:
        for s_w in SW_GRID_PSU:
            for t_scale in T_GRID_S:
                for u in U_GRID:
                    r = one_point(t_w, s_w, u, t_scale)
                    for key in ("m_baseline_m_s", "m_pure_diff_m_s",
                                "m_ddc_m_s", "m_hybrid_m_s"):
                        v = r[key]
                        if not math.isfinite(v):
                            n_nan += 1
                        elif v < 0.0:
                            n_neg += 1
                    rows.append(r)

    with open(OUT_DIR / "sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Summary statistics per variant (m/day)
    print("=" * 78)
    print("STAGE 10.13 PHASE B — COARSE SWEEP SUMMARY (m/day)")
    print("=" * 78)
    print(f"grid: {len(rows)} points "
          f"(T_w {TW_GRID}, S_w {SW_GRID_PSU}, U {U_GRID}, t {T_GRID_S})")
    print(f"NaN/Inf: {n_nan},  negative: {n_neg}")
    for var, key in (("baseline 10.11", "m_baseline_m_s"),
                     ("pure diffusive", "m_pure_diff_m_s"),
                     ("DDC-enhanced", "m_ddc_m_s"),
                     ("hybrid", "m_hybrid_m_s")):
        vals = [lf.m_s_to_m_day(r[key]) for r in rows]
        in_band = sum(1 for v in vals if OBS_BAND[0] <= v <= OBS_BAND[1])
        print(f"  {var:>16}: min={min(vals):.4e}  median={sorted(vals)[len(vals)//2]:.4e}  "
              f"max={max(vals):.4e}  in-band={in_band}/{len(vals)}")

    # Regime counts (hybrid)
    reg = {}
    for r in rows:
        reg[r["regime"]] = reg.get(r["regime"], 0) + 1
    print("hybrid regimes:", reg)

    # Continuity: max log10 jump in m_hybrid across a FINE U sub-grid
    # (0.1x..10x of the transition window), per (T,S,t) — the coarse grid
    # alone cannot distinguish a smooth ramp from a step.
    max_jump = 0.0
    _p = lf.LowFlowParams()
    u_fine = [_p.u_trans_lo * 0.1 * (200.0) ** (i / 60.0) for i in range(61)]
    for t_w in TW_GRID:
        for s_w in SW_GRID_PSU:
            for t_scale in T_GRID_S:
                ms = [lf.m_s_to_m_day(one_point(t_w, s_w, u, t_scale)["m_hybrid_m_s"])
                      for u in u_fine]
                for a, b in zip(ms, ms[1:]):
                    jump = abs(math.log10(b + 1e-300) - math.log10(a + 1e-300))
                    max_jump = max(max_jump, jump)
    print(f"continuity: max log10 jump in m_hybrid (fine U grid) = {max_jump:.3f} "
          f"({'OK (< 1)' if max_jump < 1.0 else 'FAIL'})")

    # Plots (optional)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib unavailable — plots skipped")
        return

    dT_vals = [t - ten11.ocean_freezing_point(s / 1000.0, DEPTH_M)
               for t in TW_GRID for s in (35.0,)]
    dT_vals = sorted({round(v, 3) for v in dT_vals})

    # fig1: m(U) for several dT (S=35, t=1d)
    plt.figure(figsize=(7, 5))
    for t_w in (1.0, 2.0, 4.0, 8.0):
        us = [1e-5 * 10 ** (i / 8) for i in range(41)]
        ms = [lf.compute_hybrid_melt_rate(t_w, 35.0, u, L_CHAR_M, DEPTH_M,
                                          lf.LowFlowParams())[0] * DAY_S for u in us]
        plt.semilogx(us, ms, label=f"T_w={t_w:.0f} C")
    plt.axhline(0.01, color="gray", ls=":", label="obs band 0.01-1 m/day")
    plt.axhline(1.0, color="gray", ls=":")
    plt.axhline(1.4e-3, color="r", ls="--", label="10.11 floor 0.0014")
    plt.xlabel("U_rel [m/s]"); plt.ylabel("m [m/day]")
    plt.title("hybrid m(U)"); plt.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(OUT_DIR / "fig1_m_U.png", dpi=110)

    # fig2: m(dT) at U=0, small U, forced U
    plt.figure(figsize=(7, 5))
    for u in (0.0, 1e-3, 0.1):
        ms = [lf.compute_hybrid_melt_rate(t, 35.0, u, L_CHAR_M, DEPTH_M,
                                          lf.LowFlowParams())[0] * DAY_S
              for t in TW_GRID]
        plt.plot(TW_GRID, ms, marker="o", label=f"U={u:g} m/s")
    plt.axhline(0.01, color="gray", ls=":"); plt.axhline(1.0, color="gray", ls=":")
    plt.xlabel("T_w [C]"); plt.ylabel("m [m/day]"); plt.legend()
    plt.title("hybrid m(T_w)"); plt.tight_layout()
    plt.savefig(OUT_DIR / "fig2_m_dT.png", dpi=110)

    # fig3: m(t) and delta_S(t)
    ts = [3600 * 1.5 ** i for i in range(19)]
    ds = [lf.compute_diffusive_sublayer(t, lf.LowFlowParams())[0] for t in ts]
    ms = [lf.compute_hybrid_low_flow(2.0, -1.9, 35.0, 34.99, 0.0,
                                     lf.LowFlowParams(), time_scale_s=t)
          .m_low_flow_m_s * DAY_S for t in ts]
    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax1.semilogx([t / 3600 for t in ts], ms, label="m_low_flow")
    ax1.set_xlabel("t [h]"); ax1.set_ylabel("m [m/day]", color="b")
    ax2 = ax1.twinx()
    ax2.semilogx([t / 3600 for t in ts], [d * 1000 for d in ds], "r-",
                 label="delta_S [mm]")
    ax2.set_ylabel("delta_S [mm]", color="r")
    plt.title("m(t) and delta_S(t) at U=0"); plt.tight_layout()
    plt.savefig(OUT_DIR / "fig3_m_t.png", dpi=110)

    # fig4: regime map U x dT
    us = [0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
    reg_map = []
    for u in us:
        row = []
        for t_w in TW_GRID:
            r = lf.compute_hybrid_low_flow(t_w, -1.9, 35.0, 34.99, u,
                                           lf.LowFlowParams())
            row.append("DC" if r.regime == "double_diffusive" else
                       "dif" if r.regime == "diffusion_limited" else "?")
        reg_map.append(row)
    print("regime map (rows U: 0..0.1, cols T_w 1..8):")
    for u, row in zip(us, reg_map):
        print(f"  U={u:>6}: {row}")

    print(f"\nCSV: {OUT_DIR / 'sweep.csv'}")
    print(f"PNG: {OUT_DIR / 'fig_*.png'}")


if __name__ == "__main__":
    main()