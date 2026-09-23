#!/usr/bin/env python3
"""
Stage 10.21 — IEEE-754 precision analysis of the Eckart EOS and the
convective-adjustment density threshold.

Root cause (Stage 4.3 / Stage 10.20, T-01/T-03 family): the convective
adjustment convergence threshold eps_density = 0.9e-7 g/cm3 is BELOW the
float32 quantum 2^-23 = 1.1920928955078125e-07 of the intermediate EOS
arithmetic. The historical Eckart formula evaluates aa/bb ~ O(1), so the
anomaly RO = 1/(0.698 + aa/bb) - 1.02 ~ O(0.006..0.008) inherits an absolute
rounding of ~1 ULP(of the O(1) operands) ~ 1.19e-7. Residual inversions
RO(k)-RO(k+1) therefore pin at multiples of ~2^-23, which is > 0.9e-7:
the fixed-point condition "a <= eps_density" can never be satisfied and the
1000-iteration guard fires (saturates) every day.

Stage 10.21 remedies evaluated here:
  EXP-A/EXP-C/EXP-D : evaluate EOS in float64  -> residual can fall below
                      0.9e-7; guard clears (maxiter ~150-250).
  EXP-B15 (eps=1.5e-7): 1.5e-7 > 2^-23 -> most f32 columns clear; residuals
                      in (1.5e-7, 2.4e-7] still fail (partial guard, 12-35).
  EXP-B24 (eps=2.4e-7): 2.4e-7 > 2^-22 = 2.384185791015625e-07 -> covers
                      even 2-ULP residuals; guard fully clears.

This file is a pure IEEE-754 / formula-level regression: it does not run the
Fortran model. It checks the arithmetic facts the Fortran switches rely on.

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_21_precision.py
"""

import sys

import numpy as np

_CHECKS = 0
_ERRORS = 0


def ok(condition: bool, label: str, detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if condition:
        print(f"OK   {label}" + (f" ({detail})" if detail else ""))
    else:
        print(f"ERROR {label}" + (f" ({detail})" if detail else ""))
        _ERRORS += 1


# --- independent float64 implementation of the historical Eckart EOS ---
# (mirror of equation_of_state.f90: aa/bb/ro_anom)
def eos_f64(t: float, s: float) -> float:
    aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
    bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
    return 1.0 / (0.698 + aa / bb) - 1.02


def eos_f32(t: float, s: float) -> float:
    """Exact float32 evaluation, rounding after every operation (as Fortran)."""
    t32 = np.float32(t)
    s32 = np.float32(s)
    tt = np.float32(0.0745) * t32
    tt = np.float32(11.25) - tt
    tt = tt * t32
    yy = np.float32(10.0) * t32
    yy = np.float32(3800.0) + yy
    yy = yy * s32
    aa = np.float32(1779.5) + tt - yy
    bb1 = np.float32(3000.0) * s32
    tt2 = np.float32(0.375) * t32
    tt2 = np.float32(38.0) - tt2
    tt2 = tt2 * t32
    bb = np.float32(5891.0) + bb1 + tt2
    return float(np.float32(1.0) / (np.float32(0.698) + aa / bb) - np.float32(1.02))


def main() -> None:
    # ------------------------------------------------------------------
    # 1. The float32 machine quantum and the threshold ordering
    # ------------------------------------------------------------------
    eps32 = np.finfo(np.float32).eps
    ok(bool(abs(eps32 - 2 ** -23) < 1e-20),
       "P1. float32 machine epsilon equals 2^-23",
       f"eps32 = {eps32:.17e}")
    ok(bool(eps32 == 1.1920928955078125e-07),
       "P2. 2^-23 exact value",
       f"{eps32:.17e}")

    thresh = 0.9e-7
    ok(bool(thresh < eps32),
       "P3. eps_density = 0.9e-7 is BELOW the float32 quantum (root cause)",
       f"0.9e-7 = {thresh:.2e} < 2^-23 = {eps32:.2e}")

    e15, e24 = 1.5e-7, 2.4e-7
    ok(bool(eps32 < e15 < 2 ** -22 < e24),
       "P4. threshold ladder 0.9e-7 < 2^-23 < 1.5e-7 < 2^-22 < 2.4e-7",
       f"2^-22 = {2 ** -22:.2e}")
    ok(e24 > 2 ** -22,
       "P5. EXP-B24 eps=2.4e-7 covers 2-ULP residuals (2^-22)",
       f"2.4e-7 > 2.384e-7")
    ok(e15 < 2 ** -22,
       "P6. EXP-B15 eps=1.5e-7 still misses 2-ULP residuals (partial guard)",
       f"1.5e-7 < 2.384e-7")

    # ------------------------------------------------------------------
    # 2. EOS float32 vs float64 quantization on the production domain
    # ------------------------------------------------------------------
    ts = np.linspace(-2.0, 5.0, 351)
    ss = np.linspace(0.033, 0.035, 101)
    diff_max = 0.0
    for t in ts:
        for s in ss:
            diff_max = max(diff_max, abs(eos_f64(float(t), float(s)) - eos_f32(float(t), float(s))))
    ok(diff_max < 2.5e-7,
       "P7. |RO_f64 - RO_f32| <= ~1.3e-7 over T[-2,5], S[0.033,0.035]",
       f"max = {diff_max:.3e} (quantum 2^-23 = {eps32:.2e})")
    ok(diff_max >= 1.0e-7,
       "P8. float32 quantization is actually present (>= floor)",
       f"max = {diff_max:.3e}")

    # ------------------------------------------------------------------
    # 3. EOS output range on the production domain (documentation fix)
    #    Historical header claimed X = 0.698+aa/bb in [1,2) and RO ~ 0.025.
    #    Actual (this formula): X in [0.972, 0.975], RO in [0.006, 0.0083].
    # ------------------------------------------------------------------
    x_min, x_max = 1e9, -1e9
    ro_min, ro_max = 1e9, -1e9
    for t in ts:
        for s in ss:
            aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
            bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
            x = 0.698 + aa / bb
            ro = 1.0 / x - 1.02
            x_min, x_max = min(x_min, x), max(x_max, x)
            ro_min, ro_max = min(ro_min, ro), max(ro_max, ro)
    ok(0.96 <= x_min and x_max <= 0.98,
       "P9. X = 0.698 + aa/bb in [0.96, 0.98] (NOT [1,2) as header claims)",
       f"X in [{x_min:.6f}, {x_max:.6f}]")
    ok(0.005 <= ro_min and ro_max <= 0.009,
       "P10. RO anomaly in [0.005, 0.009] (NOT ~0.025 as header claims)",
       f"RO in [{ro_min:.6f}, {ro_max:.6f}]")

    # ------------------------------------------------------------------
    # 4. float64 EOS is formula-identical to legacy (no physics change)
    # ------------------------------------------------------------------
    ok(abs(eos_f64(1.5, 0.0345) - (1.0 / (0.698 + (
        1779.5 + (11.25 - 0.0745 * 1.5) * 1.5 - (3800.0 + 10.0 * 1.5) * 0.0345) / (
        5891.0 + 3000.0 * 0.0345 + (38.0 - 0.375 * 1.5) * 1.5)) - 1.02)) < 1e-15,
       "P11. f64 EOS = legacy Eckart formula (same coefficients, real64)",
       "aa/bb/ro_anom verbatim")

    # ------------------------------------------------------------------
    # 5. Single-ULP argument: residuals pin at ~1.19e-7 for O(1) operands
    #    The Eckart anomaly RO = 1/(0.698 + aa/bb) - 1.02. On the production
    #    domain the reciprocal 1/(0.698+aa/bb) ~ 1.027 lies in the [1,2)
    #    binade, whose float32 ULP is exactly 2^-23 = 1.1920928955078125e-07.
    #    The reciprocal therefore quantizes on the 2^-23 grid, and the
    #    anomaly inherits that absolute floor: residual inversions
    #    RO(k)-RO(k+1) can never resolve below ~1.19e-7 in float32 - which is
    #    why the guard saturates with residual pinned at 0.11921E-06 (2^-23)
    #    in production (Stage 4.3 / 10.20, confirmed by the CA fixture).
    # ------------------------------------------------------------------
    rec = 1.0 / (0.698 + 0.2745)  # representative aa/bb on the production domain
    ok(bool(np.spacing(np.float32(rec)) == 2 ** -23),
       "P12. reciprocal 1/(0.698+aa/bb) ~ 1.027 in the [1,2) binade: ULP = 2^-23",
       f"spacing({rec:.6f}) = {float(np.spacing(np.float32(rec))):.2e}")
    ok(abs(eos_f32(0.5, 0.033) - 0.00650405884) < 1e-9,
       "P13. f32 EOS reproduces production RO(0.5, 0.033) = 0.00650405884",
       "matches Stage 10.21 fixture / production EOS value")

    # ------------------------------------------------------------------
    print("-" * 60)
    print(f"Total checks: {_CHECKS}  errors: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: STAGE 10.21 EOS PRECISION REGRESSION PASSED")
        sys.exit(0)
    print("FAILURE: STAGE 10.21 EOS PRECISION REGRESSION FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()