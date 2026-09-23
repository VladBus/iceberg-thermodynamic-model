#!/usr/bin/env python3
"""
Stage 10.21 — Convective adjustment column regression against the ladder of
experiments (A0 legacy / EXP-B15 / EXP-B24 / EXP-A / EXP-C):

  A0 (legacy)      : f32 EOS, eps_density = 0.9e-7  -> guard fires at 1000
                     iterations, residual pinned at 2^-23 = 1.192e-07
                     (the float32 quantum of the O(1) Eckart intermediate).
  EXP-B15          : f32 EOS, eps_density = 1.5e-7  -> 1-ULP residuals pass,
                     2-ULP residuals (2^-22 = 2.384e-07) still fail -> guard
                     fires on 2-ULP columns (partial, matches 12-35/day).
  EXP-B24          : f32 EOS, eps_density = 2.4e-7  -> covers 2-ULP, converges.
  EXP-A (f64 EOS)  : float64 EOS, f32 mixing -> converges below 0.9e-7.
  EXP-C (f64 all)  : float64 EOS + f64 mixing arithmetic -> converges.
                      Mixing arithmetic attribution: EXP-A vs EXP-C differ
                      only in the last f32 rounding bits (< 1e-8 rel).

The kernel below is an operation-by-operation mirror of the Fortran
convect_column / convect_column_f64 (src/convective_adjustment.f90):
every f32-path arithmetic step rounds to float32 as in Fortran, so the
guard/residual behaviour reproduces production exactly.

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_21_convective_adjustment.py
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


F32 = np.float32
EPS32 = np.finfo(np.float32).eps  # 2^-23 = 1.1920928955078125e-07

# --- Fortran-faithful mirrors -------------------------------------------


def density_anomaly_f32(t: float, s: float) -> float:
    """Eckart EOS evaluated in float32, rounding after every operation."""
    t32 = F32(t)
    s32 = F32(s)
    aa = F32(F32(1779.5) + F32(F32(11.25) - F32(F32(0.0745) * t32)) * t32
             - F32(F32(3800.0) + F32(10.0) * t32) * s32)
    bb = F32(F32(5891.0) + F32(3000.0) * s32 + F32(F32(38.0) - F32(F32(0.375) * t32)) * t32)
    return float(F32(F32(1.0) / F32(F32(0.698) + F32(aa / bb)) - F32(1.02)))


def density_anomaly_f64(t: float, s: float) -> float:
    aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
    bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
    return 1.0 / (0.698 + aa / bb) - 1.02


def convect_column(ct: list, cs: list, cdz1: list, eps: float,
                   f64_mode: bool = False, f64_mix: bool = False):
    """Mirror of Fortran convect_column / convect_column_f64.

    Returns (ct, cs, nmix, iter_count, guard_hit, resid_out).
    """
    ki = len(ct)
    if f64_mode:
        cr = [density_anomaly_f64(ct[k], cs[k]) for k in range(ki)]
    else:
        cr = [density_anomaly_f32(ct[k], cs[k]) for k in range(ki)]
    if ki <= 1:
        return list(ct), list(cs), 0, 0, False, 0.0
    nmix = 0
    iter_count = 0
    guard_hit = False

    def fconv(x: float) -> float:
        return float(x) if f64_mode else float(F32(x))

    dzz = fconv(cdz1[0])
    while True:
        iter_count += 1
        ki2 = ki - 1
        a1 = 0
        for k in range(ki2):
            k1 = k + 1
            dzz1 = fconv(cdz1[k1])
            dz1z = dzz + dzz1
            a = cr[k] - cr[k1]
            if a <= eps:
                dzz = dzz1
                continue
            a1 += 1
            if f64_mode and f64_mix:
                t_new = (ct[k] * dzz + ct[k1] * dzz1) / dz1z
                s_new = (cs[k] * dzz + cs[k1] * dzz1) / dz1z
                ct[k] = float(t_new)
                cs[k] = float(s_new)
            else:
                ct[k] = float(F32(F32(F32(ct[k]) * F32(dzz)) + F32(F32(ct[k1]) * F32(dzz1))) / F32(dz1z))
                cs[k] = float(F32(F32(F32(cs[k]) * F32(dzz)) + F32(F32(cs[k1]) * F32(dzz1))) / F32(dz1z))
            ct[k1] = ct[k]
            cs[k1] = cs[k]
            if f64_mode:
                cr[k] = density_anomaly_f64(ct[k], cs[k])
            else:
                cr[k] = density_anomaly_f32(ct[k], cs[k])
            cr[k1] = cr[k]
            dzz = dzz1
        nmix += a1
        if a1 == 0:
            break
        if iter_count > 1000:
            guard_hit = True
            break
    rmax = -1e300
    for k in range(ki - 1):
        resid = cr[k] - cr[k + 1]
        if resid > rmax:
            rmax = resid
    resid_out = float(rmax) if rmax > eps else 0.0
    return ct, cs, nmix, iter_count, guard_hit, resid_out


# --- fixtures (found by deterministic search, /tmp/opencode/stage1021) ---
# Fixture A (4 levels): legacy A0 guard with residual = 1 ULP (2^-23).
FIX_A_T = [0.5, 0.48, 0.46, 0.44]
FIX_A_S = [0.033, 0.03298, 0.03296, 0.03294]
FIX_A_DZ = [200.0, 400.0, 400.0, 200.0]
# Fixture B (5 levels): EXP-B15 partial failure with residual = 2 ULP (2^-22).
FIX_B_T = [2.0, 1.985, 1.97, 1.955, 1.94]
FIX_B_S = [0.034, 0.0338, 0.0336, 0.0334, 0.0332]
FIX_B_DZ = [200.0, 300.0, 300.0, 300.0, 200.0]


def sums_ts(ct, cs, dz):
    return sum(ct[k] * dz[k] for k in range(len(ct))), sum(cs[k] * dz[k] for k in range(len(ct)))


def is_stable(cr, eps):
    return all(cr[k] - cr[k + 1] <= eps for k in range(len(cr) - 1))


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Fixture A: the four production convergence regimes
    # ------------------------------------------------------------------
    r_legacy = convect_column(list(FIX_A_T), list(FIX_A_S), list(FIX_A_DZ), 0.9e-7)
    ok(r_legacy[4] is True,
       "CA1. A0 legacy f32 eps=0.9e-7: guard fires (1000-iter limit)",
       f"iters={r_legacy[3]}, nmix={r_legacy[2]}")
    ok(abs(r_legacy[5] - 2 ** -23) < 1e-12,
       "CA2. A0 residual pinned at exactly 2^-23 (f32 quantum)",
       f"resid={r_legacy[5]:.12e}")
    ok(r_legacy[2] > 1000,
       "CA3. A0 still actively mixing when guard fires (far from converged)",
       f"nmix={r_legacy[2]} across {r_legacy[3]} passes")

    r_b24 = convect_column(list(FIX_A_T), list(FIX_A_S), list(FIX_A_DZ), 2.4e-7)
    ok(r_b24[4] is False and r_b24[5] == 0.0,
       "CA4. EXP-B24 eps=2.4e-7: converges, zero residual",
       f"iters={r_b24[3]}, nmix={r_b24[2]}")

    r_a = convect_column(list(FIX_A_T), list(FIX_A_S), list(FIX_A_DZ), 0.9e-7,
                         f64_mode=True, f64_mix=False)
    ok(r_a[4] is False and r_a[5] == 0.0,
       "CA5. EXP-A f64 EOS (f32 mixing): converges below 0.9e-7",
       f"iters={r_a[3]}, nmix={r_a[2]}")

    r_c = convect_column(list(FIX_A_T), list(FIX_A_S), list(FIX_A_DZ), 0.9e-7,
                         f64_mode=True, f64_mix=True)
    ok(r_c[4] is False and r_c[5] == 0.0,
       "CA6. EXP-C f64 EOS + f64 mixing: converges",
       f"iters={r_c[3]}, nmix={r_c[2]}")

    # ------------------------------------------------------------------
    # 2. Fixture A: conservation and final stability
    # ------------------------------------------------------------------
    sum_t0, sum_s0 = sums_ts(FIX_A_T, FIX_A_S, FIX_A_DZ)
    sum_t1, sum_s1 = sums_ts(r_legacy[0], r_legacy[1], FIX_A_DZ)
    ok(abs(sum_t1 - sum_t0) / sum_t0 < 1e-7 and abs(sum_s1 - sum_s0) / sum_s0 < 1e-7,
       "CA7. A0 f32 mixing conserves integral T/S to f32 rounding (rel < 1e-7)",
       f"rel dT={abs(sum_t1 - sum_t0) / sum_t0:.2e}, rel dS={abs(sum_s1 - sum_s0) / sum_s0:.2e}")

    sum_t2, sum_s2 = sums_ts(r_c[0], r_c[1], FIX_A_DZ)
    ok(abs(sum_t2 - sum_t0) < 1e-12 and abs(sum_s2 - sum_s0) < 1e-12,
       "CA8. EXP-C f64 mixing conserves integral T/S to machine precision",
       f"dT={sum_t2 - sum_t0:.2e}, dS={sum_s2 - sum_s0:.2e}")

    cr_c = [density_anomaly_f64(r_c[0][k], r_c[1][k]) for k in range(4)]
    rmax_c = max(cr_c[k] - cr_c[k + 1] for k in range(3))
    ok(is_stable(cr_c, 0.9e-7),
       "CA9. EXP-C converged column satisfies the Fortran eps_density=0.9e-7 "
       "convergence criterion",
       f"max residual={rmax_c:.2e} (<= 0.9e-7)")

    # ------------------------------------------------------------------
    # 3. Fixture A: EXP-A vs EXP-C mixing-arithmetic attribution
    # ------------------------------------------------------------------
    max_dt = max(abs(r_a[0][k] - r_c[0][k]) for k in range(4))
    ok(max_dt < 1e-8,
       "CA10. EXP-A (f32 mix) vs EXP-C (f64 mix): same physics, differs only "
       "in f32 rounding bits",
       f"max|dT|={max_dt:.2e}")

    # ------------------------------------------------------------------
    # 4. Fixture B: EXP-B15 partial failure (2-ULP residual) vs EXP-B24
    # ------------------------------------------------------------------
    r_b15 = convect_column(list(FIX_B_T), list(FIX_B_S), list(FIX_B_DZ), 1.5e-7)
    ok(r_b15[4] is True,
       "CA11. EXP-B15 f32 eps=1.5e-7: STILL guards on 2-ULP columns",
       f"iters={r_b15[3]}, nmix={r_b15[2]}")
    ok(abs(r_b15[5] - 2 ** -22) < 1e-12,
       "CA12. B15 residual pinned at 2^-22 = 2x2^-23 (2-ULP, above 1.5e-7)",
       f"resid={r_b15[5]:.12e}")

    r_b24b = convect_column(list(FIX_B_T), list(FIX_B_S), list(FIX_B_DZ), 2.4e-7)
    ok(r_b24b[4] is False and r_b24b[5] == 0.0,
       "CA13. Same column, eps=2.4e-7 (EXP-B24): converges",
       f"iters={r_b24b[3]}, nmix={r_b24b[2]}")

    r_b64 = convect_column(list(FIX_B_T), list(FIX_B_S), list(FIX_B_DZ), 0.9e-7,
                           f64_mode=True, f64_mix=True)
    ok(r_b64[4] is False and r_b64[5] == 0.0,
       "CA14. Same column, f64 (EXP-C): converges",
       f"iters={r_b64[3]}, nmix={r_b64[2]}")

    # 2-ULP separation: the residual 2^-22 is exactly the analytical threshold
    # boundary between EXP-B15 (fail) and EXP-B24 (pass).
    ok(1.5e-7 < 2 ** -22 < 2.4e-7,
       "CA15. 1.5e-7 < 2^-22 < 2.4e-7: B15 below 2-ULP, B24 above it")

    # ------------------------------------------------------------------
    # 5. Degenerate and edge cases
    # ------------------------------------------------------------------
    r_single = convect_column([0.5], [0.033], [200.0], 0.9e-7)
    ok(r_single[3] == 0 and r_single[4] is False,
       "CA16. Single-layer column: no iterations, no guard")

    r_stable = convect_column([0.44, 0.46, 0.48, 0.5], [0.03294, 0.03296, 0.03298, 0.033],
                              list(FIX_A_DZ), 0.9e-7)
    ok(r_stable[3] == 1 and r_stable[2] == 0 and r_stable[5] == 0.0,
       "CA17. Already-stable column: one check pass, zero mixes",
       f"iters={r_stable[3]}, nmix={r_stable[2]}")

    # f32 EOS identity per column level set (determinism)
    d1 = density_anomaly_f32(0.5, 0.033)
    d2 = density_anomaly_f32(0.5, 0.033)
    ok(d1 == d2,
       "CA18. EOS f32 deterministic (bit-identical repeat evaluation)",
       f"RO={d1:.10f}")

    # ------------------------------------------------------------------
    print("-" * 60)
    print(f"Total checks: {_CHECKS}  errors: {_ERRORS}")
    if _ERRORS == 0:
        print("SUCCESS: STAGE 10.21 CONVECTIVE ADJUSTMENT REGRESSION PASSED")
        sys.exit(0)
    print("FAILURE: STAGE 10.21 CONVECTIVE ADJUSTMENT REGRESSION FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()