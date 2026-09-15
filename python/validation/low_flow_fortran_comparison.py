#!/usr/bin/env python3
"""
Stage 10.13 Phase C — Python-vs-Fortran comparison of the low-flow closure.

Runs the focused Fortran test (iceberg_test_10p13_low_flow), parses its
machine-readable CMP lines, and compares against the Phase-B Python reference
(python/validation/low_flow.py) at 10 representative points.

Checks:
  1. f (DDC enhancement) — exact match (both use the same criterion form;
     borderline points are reported, not asserted).
  2. regime — exact match (Fortran int 0..5 vs Python string).
  3. delta_S — rel diff within 10% (systematic difference: the repository
     derives kappa_S = kappa_T/Le with Le=100, kappa_T from
     THERMAL_CONDUCTIVITY; the Python reference used kappa_S = 1.5e-9).
  4. m at low-flow points (U <= 1e-3) — absolute diff within 0.05 m/day
     (systematic difference: the Fortran three-equation interface freshens
     S_B, reducing the interfacial dT vs the far-field dT used by the
     Python m_low; both effects documented in stage10.13_phase_c_results.md).
  5. high-U (0.1 m/s): Fortran-ON == Fortran-OFF is verified inside the
     Fortran test (forced preservation); here we only report the Python
     hybrid value for context (different forced formulation: bulk vs 3eq).

Run:
    conda run -n iceberg-thermodynamic-model python python/validation/low_flow_fortran_comparison.py
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import low_flow as lf

REPO_ROOT = Path(__file__).resolve().parents[2]
DAY_S = 86400.0

# (id, T_w, S_w_psu, U) for the 10 comparison points (matches the Fortran test)
POINTS = [
    (1, 2.0, 35.0, 0.0),
    (2, 2.0, 35.0, 1.0e-4),
    (3, 2.0, 35.0, 1.0e-3),
    (4, 2.0, 35.0, 3.0e-3),
    (5, 2.0, 35.0, 8.5e-3),
    (6, 2.0, 35.0, 1.0e-2),
    (7, 2.0, 35.0, 0.1),
    (8, 4.0, 35.0, 0.0),
    (9, 1.0, 30.0, 0.0),
    (10, 6.0, 35.0, 0.0),
]

DEPTH_M = 50.0
L_CHAR_M = 100.0

REGIME_MAP = {"off": 0, "forced": 1, "diffusion_limited": 2,
              "double_diffusive": 3, "hybrid_transition": 4,
              "invalid_or_out_of_scope": 5}


def run_fortran_cmp() -> list[dict]:
    """Run the Fortran focused test and parse CMP lines."""
    cmd = ["fpm", "test", "iceberg_test_10p13_low_flow",
           "--flag", "-I/usr/include"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print("WARNING: Fortran test exited", proc.returncode, "(compile issue?)")
    out = []
    for line in proc.stdout.splitlines():
        if not line.startswith("C"):
            continue
        parts = line.split()
        if len(parts) != 14 or parts[0] != "C":
            continue
        out.append({
            "id": int(parts[1]),
            "m_mday": float(parts[2]),
            "delta_s": float(parts[3]),
            "f": float(parts[4]),
            "gamma_t": float(parts[5]),
            "gamma_s": float(parts[6]),
            "re_b": float(parts[7]),
            "regime": int(parts[8]),
            "converged": parts[9] == "T",
            "r_rho": float(parts[10]),
            "ri_star": float(parts[11]),
            "u_rel": float(parts[12]),
            "delta_t": float(parts[13]),
        })
    return out


def python_reference(t_w: float, s_w: float, u: float) -> dict:
    """Python Phase-B reference at the same point (full hybrid incl. blending).

    Uses compute_hybrid_melt_rate so the regime includes the w-blend
    (hybrid_transition / forced), matching the Fortran classification.
    """
    import basal_melt as bm
    t_b = bm.ocean_freezing_point(s_w, DEPTH_M)
    s_b = s_w - lf.LowFlowParams().dS_floor_psu
    m_hyb, low, m_f, w, gt, gs = lf.compute_hybrid_melt_rate(
        t_w, s_w, u, L_CHAR_M, DEPTH_M, lf.LowFlowParams(),
        time_scale_s=DAY_S, t_b=t_b, s_b=s_b)
    return {
        "m_low_mday": lf.m_s_to_m_day(low.m_low_flow_m_s),
        "delta_s": low.delta_s_m,
        "f": low.enhancement_factor,
        "regime": low.regime,
        "r_rho": low.r_rho,
        "re_b": low.re_b,
        "ri_star": low.ri_star,
    }


def main() -> None:
    f_lines = run_fortran_cmp()
    if not f_lines:
        print("ERROR: no CMP lines parsed from Fortran test output")
        sys.exit(1)

    n_checks = 0
    n_errors = 0

    def ok(cond: bool, label: str, detail: str = "") -> None:
        nonlocal n_checks, n_errors
        n_checks += 1
        if cond:
            print(f"OK   {label}" + (f" ({detail})" if detail else ""))
        else:
            print(f"ERROR {label}" + (f" ({detail})" if detail else ""))
            n_errors += 1

    print("=" * 78)
    print("STAGE 10.13 PHASE C — PYTHON vs FORTRAN COMPARISON (low-flow closure)")
    print("=" * 78)
    print(f"{'id':>3} {'U[m/s]':>9} | {'Fortran m':>10} {'Py m_low':>10} "
          f"{'delta_s F/P':>12} {'f F/P':>8} {'reg F/P':>12}")
    for pid, t_w, s_w, u in POINTS:
        f_line = next((x for x in f_lines if x["id"] == pid), None)
        if f_line is None:
            ok(False, f"P{pid}: Fortran CMP line missing")
            continue
        py = python_reference(t_w, s_w, u)
        print(f"{pid:>3} {u:9.4g} | {f_line['m_mday']:10.5f} {py['m_low_mday']:10.5f} "
              f"{f_line['delta_s']:11.5f}/{py['delta_s']:6.5f} "
              f"{f_line['f']:3.1f}/{py['f']:3.1f} "
              f"{f_line['regime']:3d}/{REGIME_MAP[py['regime']]:3d}")

        # 1. f enhancement
        ok(f_line["f"] == py["f"],
           f"P{pid} f matches", f"F={f_line['f']} Py={py['f']}")
        # 2. regime
        ok(f_line["regime"] == REGIME_MAP[py["regime"]],
           f"P{pid} regime matches", f"F={f_line['regime']} Py={py['regime']}")
        # 3. delta_S within 10% (kappa_S convention difference)
        rel = abs(f_line["delta_s"] - py["delta_s"]) / py["delta_s"]
        ok(rel < 0.10, f"P{pid} delta_S within 10%", f"(rel={rel:.2e})")
        # 4. m at low-flow points within 0.05 m/day absolute
        if u <= 1.0e-3:
            ok(abs(f_line["m_mday"] - py["m_low_mday"]) < 0.05,
               f"P{pid} m within 0.05 m/day abs", 
               f"(F={f_line['m_mday']:.4f} Py={py['m_low_mday']:.4f})")
        # 5. diagnostics sanity
        ok(f_line["r_rho"] > 0.0 and f_line["ri_star"] > 0.0 and
           f_line["re_b"] >= 0.0,
           f"P{pid} dimensionless diagnostics sane")
        ok(f_line["converged"], f"P{pid} Fortran iteration converged")

    print("----------------------------------------------")
    print(f"TOTAL CHECKS: {n_checks}  ERRORS: {n_errors}")
    print("NOTE: m at U=0.1 not compared across languages: the Fortran uses the")
    print("three-equation forced branch; the Python reference hybrid uses the")
    print("bulk forced closure (different validated formulations). Forced")
    print("preservation (Fortran ON == OFF) is asserted inside the Fortran test.")
    if n_errors == 0:
        print("SUCCESS: Stage 10.13 Python-vs-Fortran comparison PASSED")
        sys.exit(0)
    else:
        print("FAILURE: Stage 10.13 Python-vs-Fortran comparison FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()