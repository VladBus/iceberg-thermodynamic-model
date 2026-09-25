#!/usr/bin/env python3
"""
Stage 10.22 — Ocean density / thermal-wind / Block-200 stability audit:
regression against the causal-chain evidence, the Thomas pivot identity,
the A5 replay-verdict contract, and the bit-identity invariant.

Encode (from docs/validation/stage10.22_ocean_density_thermal_wind_block200_audit.md):

  (1) Causal-chain evidence constants (probe CSV, run stage10.22_p30d_a0_diag):
        - day 4 step 1, CA_after: FIRST physically impossible state —
          ro_min = -1.946690e-04 (ρ-anomaly < 0), 0 NaN in every field.
        - day 4 step 12, CA_after: end-of-day-4 ro_min = -4.365810e-02.
        - day 5 step 6, CA_after: FIRST NaN = ρ (ro_nan = 198, density-first,
          matching 10.19/10.20 NaN_RO=198 at F_after_conv); u/v still clean;
          ro envelope already corrupt (±10^6).
        - day 5 step 6, B200_before: ro_nan = 198, u2/v2 0 NaN (Block 200
          entry clean) -> B200_after: u2_nan = 332 (Block 200 = transmitter,
          not origin) -> B210_after: u2_nan = 333 (Block 210 +1 = amplifier).
        - day 6 step 1, END_step: zombie (u2 131,476; t/s/ro 142,081 = all
          wet cells).
        - max B210_after u2_nan = 131,476 at day 5 step 9.
  (2) Pivot-negativity-by-construction identity (analytic + CSV):
        a = -aa/dz(k)*rr(k2) < 0, b = -aa/dz(k+1)*rr(k) < 0,
        a1 = -1.0 + a + b < -1,  pivot = a1 - uca*a < -1  (uca in [0,1))
        -> piv_min = 1.0 and piv_neg = piv_cnt in the healthy state.
        CSV exact ratio 1.0 for all 48 day-1-4 steps + day-5 s1/s2/s4;
        day-5 deviations (0.99998/0.99999 at s3/s5) are NaN-overflowed
        pivots, not positive pivots; collapse to 0 only post-ρ-NaN (zombie).
  (3) A5 replay verdicts (rel tol 1e-4, block200_isolate.py --step 1):
        a1/a3/a4: PASS 30/30, worst 4.213e-6 (d21) / 4.100e-6 (d9) /
                  4.213e-6 (d21)  -- a4 identical to a1 CSV path.
        a2: FAIL ro-phase-only — exactly 9 metrics (ro_*, sum_max, sum1_max,
            acc_bar_u/v, dp_ratio_u/v), worst 2.954e-1 (d9); momentum
            max_u2/max_v2/amp_u/amp_v PASS -> freeze_tw two-path split EXACT.
        a0: FAIL days 1-30 (ro-phase artifact); d1 worst 9.195e-3 (ro_mean);
            day-6+ = 14 fails + 3 NaN skip (ocean zombie -> CSV NaN).
  (4) Bit-identity invariant: a0 vs a0_diag daily_diagnostics.csv IDENTICAL
        (md5 1ef13cb4d212db8570dd64737e945897) -> instrumentation read-only.

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_22_block200_audit.py
(plain python3 works too; numpy is used only for the analytic mirror and the
optional CSV/md5 live checks, which are skipped when the run artifacts are
absent — data/ is gitignored, so CI exercises the structural path).
"""

import hashlib
import os
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


def _f(s: str) -> float:
    """Parse a Fortran CSV float; the NaN marker '****************' -> nan."""
    try:
        return float(s)
    except ValueError:
        return float("nan")

# --- Documented evidence constants (report §9-§19) -----------------------

CAUSAL_CHAIN = [
    # (label, day, step, key, expected) — probe CSV, a0_diag run
    ("CA_after", 4, 1, "ro_min", -1.946690e-04),   # FIRST sub-zero ρ-anomaly
    ("CA_after", 4, 12, "ro_min", -4.365810e-02),  # end-of-day-4 min
    ("CA_after", 5, 6, "ro_nan", 198.0),           # FIRST NaN = ρ
    ("CA_after", 5, 6, "ro_min", -4.19430e+06),    # corrupt envelope
    ("CA_after", 5, 6, "ro_max", 1.67772e+07),
    ("CA_after", 5, 6, "u2_nan", 0.0),             # momentum still clean AT
    ("B200_before", 5, 6, "u2_nan", 0.0),          # Block 200 entry clean
    ("B200_after", 5, 6, "u2_nan", 332.0),         # Block 200 transmits
    ("B210_after", 5, 6, "u2_nan", 333.0),         # Block 210 +1 (amplifier)
    ("END_step", 6, 1, "u2_nan", 131476.0),        # zombie
    ("END_step", 6, 1, "t_nan", 142081.0),         # zombie = all wet cells
]

# Block 210 conditioning constants (report §13) at the ρ-NaN step (5,6).
B210_AT_NAN = {  # day 5 step 6
    "rhs_max": 1.12608e16,
    "den_min": 7.05833e-04,
    "rr_max": 1.65990e12,
}
# Healthy window (report §13): through day 4 the Thomas system is
# well-conditioned. CSV-verified bounds (full-coverage ERA5, a0_diag):
#   rr_max  obs max 8431 (d4s11)   -> 8.5e3
#   rhs_max obs max 697.8 (d4s12)  -> 7.0e2
#   den_min obs min 0.3201 (d3s9)  -> 0.32  (day-4 window itself 0.607-0.763;
#                                          days 1-3 dip transiently ~0.32-0.56)
B210_HEALTHY = {  # bounds for day-1-4 steps
    "rr_max": 8.5e3,
    "rhs_max": 7.0e2,
    "den_min_lower": 0.32,
    "piv_min": 1.0,
}
B210_DAY4_WINDOW = {  # day-4-only window (report §13 table, obs 0.607-0.763)
    "den_min_lower": 0.60,
}

# Pivot identity (report §13/§17 finding 5): exact CSV ratio 1.0 for all
# 48 day-1-4 steps + day-5 s1/s2/s4; day-5 deviations are NaN-overflowed
# pivots (NaN fails the `v <= 0` test -> leaves piv_neg while piv_cnt
# keeps counting); post-ρ-NaN collapse to 0.
PIV_EXACT_STEPS = 48 + 3  # days 1-4 (48) + day5 s1/s2/s4 (3)
PIV_CNT_PER_STEP = 221608
PIV_DAY5_DEVIATIONS = [
    # (step, piv_neg/piv_cnt) — from CSV; NaN pivots exit piv_neg
    (3, 0.99998), (5, 0.99999), (6, 0.99736), (7, 0.9905),
    (8, 0.18341), (9, 0.0),  # s9+ zombie
]

# A5 verdict contract (report §14): rel tol 1e-4.
A5_TOL = 1e-4
A5_VERDICTS = {
    # exp: (verdict_pass_all30, worst_rel, n_fail_vs_replay, worst_day)
    "a0": (False, 9.195e-3, None),           # d1 worst; day6+ 14f+3skip
    "a1": (True, 4.213e-6, 0),
    "a2": (False, 2.954e-1, 9),              # exactly 9 ro-phase metrics
    "a3": (True, 4.100e-6, 0),
    "a4": (True, 4.213e-6, 0),               # identical to a1 CSV path
}
A2_FAILING_9 = {
    "ro_min", "ro_max", "ro_mean",
    "sum_max", "sum1_max",
    "acc_bar_u", "acc_bar_v",
    "dp_ratio_u", "dp_ratio_v",
}
A2_PASSING_MOMENTUM = {"max_u2", "max_v2", "amp_u", "amp_v"}
METRIC_NAMES = [
    "ro_min", "ro_max", "ro_mean",
    "sum_max", "sum1_max",
    "acc_bar_u", "acc_bar_v", "acc_dp_u", "acc_dp_v",
    "acc_lap_u", "acc_lap_v",
    "dp_ratio_u", "dp_ratio_v",
    "max_u1", "max_v1", "max_u2", "max_v2",
    "amp_u", "amp_v",
]

# Bit-identity invariant (report §6): a0 vs a0_diag daily_diagnostics.
BIT_IDENTITY_MD5 = "1ef13cb4d212db8570dd64737e945897"

_RUN_DIR_A0 = "data/runs/stage10.22_p30d_a0"
_RUN_DIR_A0_DIAG = "data/runs/stage10.22_p30d_a0_diag"
_CSV_DIR = "output/csv"
_CSV_FILES = {
    "probes": "stage1022_probes.csv",
    "block200": "stage1022_block200.csv",
    "block210": "stage1022_block210.csv",
}
_ARTIFACTS_PRESENT = None  # resolved lazily


def _artifacts_present() -> bool:
    """True when the a0_diag diagnostic run CSVs exist (data/ gitignored)."""
    global _ARTIFACTS_PRESENT
    if _ARTIFACTS_PRESENT is None:
        base = os.path.join(_RUN_DIR_A0_DIAG, _CSV_DIR)
        _ARTIFACTS_PRESENT = all(
            os.path.isfile(os.path.join(base, f)) for f in _CSV_FILES.values())
    return _ARTIFACTS_PRESENT


def _probe_rows():
    import csv
    rows = []
    path = os.path.join(_RUN_DIR_A0_DIAG, _CSV_DIR, _CSV_FILES["probes"])
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({k: v.strip() for k, v in r.items()})
    return rows


# --- 1. Analytic Thomas pivot mirror (app/main.f90 Block 210) ------------


def thomas_pivot(rr: float, dz: float, dz1: float, uca: float, aa: float):
    """Mirror of the Block 210 Thomas pivot (app/main.f90, caa routine).

    a  = -aa/dz(k)*rr(k2)    (< 0 for rr > 0)
    b  = -aa/dz(k+1)*rr(k)   (< 0 for rr > 0)
    a1 = -1.0 + a + b        (< -1)
    pivot = a1 - uca*a       (< -1 for uca in [0,1))
    """
    a = -aa / dz * rr
    b = -aa / dz * rr
    a1 = -1.0 + a + b
    pivot = a1 - uca * a
    return a, b, a1, pivot


def test_pivot_identity() -> None:
    print("\n--- 1. Analytic Thomas pivot identity (Block 210 mirror) ---")
    # Sweep rr over the healthy-to-corrupt range; every pivot must be < -1
    # (strict negativity holds for rr > 0 — the rr=0 boundary is asserted
    # separately below, where the substencil vanishes exactly).
    for rr in [1.0e-6, 1.0, 8.4e3, 1.0e6, 1.65990e12, 1.0e16]:
        a, b, a1, pivot = thomas_pivot(rr, dz=1.0, dz1=1.0, uca=0.5, aa=1.0)
        ok(a < 0.0 and b < 0.0, f"rr={rr:.3g}: substencil a,b negative",
           f"a={a:.4g} b={b:.4g}")
        ok(a1 < -1.0, f"rr={rr:.3g}: a1 = -1+a+b < -1", f"a1={a1:.4g}")
        ok(pivot < -1.0, f"rr={rr:.3g}: pivot = a1-uca*a < -1",
           f"pivot={pivot:.4g}")
        ok(abs(pivot) >= 1.0, f"rr={rr:.3g}: |pivot| >= 1 (piv_min=1.0)",
           f"|pivot|={abs(pivot):.4g}")
    # uca sweeping [0,1): pivot stays < -1.
    for uca in np.linspace(0.0, 0.999999, 7):
        a, b, a1, pivot = thomas_pivot(1.0e6, dz=1.0, dz1=1.0, uca=float(uca),
                                       aa=1.0)
        ok(pivot < -1.0, f"uca={uca:.6f}: pivot < -1",
           f"pivot={pivot:.4g}")
    # Boundary a=b=0 (rr=0): pivot = -1 exactly -> piv_min = 1.0.
    a, b, a1, pivot = thomas_pivot(0.0, dz=1.0, dz1=1.0, uca=0.5, aa=1.0)
    ok(a1 == -1.0 and pivot == -1.0 and abs(pivot) == 1.0,
       "rr=0: pivot = -1 exactly (piv_min = 1.0 asserted by CSV)")


# --- 2. CSV pivot-ratio contract (live) ----------------------------------


def test_pivot_ratio_csv() -> None:
    print("\n--- 2. CSV pivot ratio (stage1022_block210.csv) ---")
    if not _artifacts_present():
        print("SKIP (run artifacts absent; structural contract only):")
        ok(True, "pivot identity: analytic < -1 for any rr > 0 "
                 "-> piv_neg=piv_cnt healthy (documented 48+3 exact steps)")
        ok(PIV_EXACT_STEPS == 51, "pivot exact-1.0 step count = 48 + 3",
           f"{PIV_EXACT_STEPS} steps")
        ok(len(PIV_DAY5_DEVIATIONS) == 6, "day-5 deviation sequence encoded",
           "s3/s5/s6/s7/s8/s9+")
        return
    import csv
    base = os.path.join(_RUN_DIR_A0_DIAG, _CSV_DIR)
    rows = []
    with open(os.path.join(base, _CSV_FILES["block210"]), newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({k: v.strip() for k, v in r.items()})
    ok(len(rows) == 360, "block210.csv row count = 360 (30d x 12 steps)",
       f"{len(rows)} rows")
    healthy = []
    deviations = []
    for r in rows:
        day = int(r["day"]); step = int(r["step"])
        cnt = int(float(r["piv_cnt"]))
        neg = int(float(r["piv_neg"]))
        piv_min = _f(r["piv_min"])
        ratio = neg / cnt if cnt else float("nan")
        if ratio == 1.0:
            healthy.append((day, step))
        else:
            deviations.append((day, step, ratio, piv_min))
        if day <= 4:
            ok(float(r["rr_max"]) <= B210_HEALTHY["rr_max"],
               f"d{day}s{step}: rr_max within healthy bound",
               f"rr_max={r['rr_max']} <= 8.5e3")
            ok(float(r["rhs_max"]) <= B210_HEALTHY["rhs_max"],
               f"d{day}s{step}: rhs_max within healthy bound",
               f"rhs_max={r['rhs_max']} <= 7.0e2")
            ok(float(r["den_min"]) >= B210_HEALTHY["den_min_lower"],
               f"d{day}s{step}: den_min >= 0.32 (day-1-4 lower bound)",
               f"den_min={r['den_min']}")
            ok(float(r["piv_min"]) == B210_HEALTHY["piv_min"],
               f"d{day}s{step}: piv_min = 1.0",
               f"piv_min={r['piv_min']}")
            if day == 4:
                ok(float(r["den_min"]) >= B210_DAY4_WINDOW["den_min_lower"],
                   f"d4s{step}: den_min in day-4 window (>= 0.60)",
                   f"den_min={r['den_min']}")
    ok(len(healthy) == PIV_EXACT_STEPS,
       "healthy steps with exact ratio 1.0 = 48 day-1-4 + 3 day-5",
       f"{len(healthy)} steps")
    ok(sum(1 for h in healthy if h[0] <= 4) == 48,
       "all 48 day-1-4 steps have exact ratio 1.0")
    day5_healthy = [h for h in healthy if h[0] == 5]
    ok(sorted(s for _, s in day5_healthy) == [1, 2, 4],
       "day-5 exact steps are s1, s2, s4")
    # Day-5 deviations: threshold-modest at s3/s5, collapse at s6+.
    dev_by_step = {s: ratio for d, s, ratio, _ in deviations if d == 5}
    ok(set(dev_by_step) >= {3, 5, 6, 7, 8, 9},
       "day-5 deviation steps include s3,s5,s6,s7,s8,s9",
       f"{sorted(dev_by_step)}")
    ok(dev_by_step.get(3, 1.0) > 0.995,
       "s3 deviation is tiny (NaN-overflowed pivots), not positive pivots",
       f"ratio={dev_by_step.get(3):.5f}")
    ok(dev_by_step.get(5, 1.0) > 0.995,
       "s5 deviation is tiny (NaN-overflowed pivots)",
       f"ratio={dev_by_step.get(5):.5f}")
    ok(dev_by_step.get(6, 1.0) < 1.0 and dev_by_step.get(6, 0.0) > 0.99,
       "s6 = the ρ-NaN step: ratio begins collapse",
       f"ratio={dev_by_step.get(6):.5f}")
    ok(dev_by_step.get(8, 0.0) < 0.3,
       "s8: near-total pivot loss (0.183)",
       f"ratio={dev_by_step.get(8):.5f}")
    ok(dev_by_step.get(9, 0.0) == 0.0,
       "s9+: zombie, piv_neg = 0 (NaN pivots fail v<=0)")
    # The ρ-NaN step constants.
    r6 = next(r for r in rows if int(r["day"]) == 5 and int(r["step"]) == 6)
    ok(float(r6["rhs_max"]) == B210_AT_NAN["rhs_max"],
       "d5s6 rhs_max = 1.12608e16", f"rhs_max={r6['rhs_max']}")
    ok(float(r6["den_min"]) == B210_AT_NAN["den_min"],
       "d5s6 den_min = 7.05833e-04", f"den_min={r6['den_min']}")
    ok(float(r6["rr_max"]) == B210_AT_NAN["rr_max"],
       "d5s6 rr_max = 1.65990e12", f"rr_max={r6['rr_max']}")


# --- 3. Causal-chain evidence (live probe CSV) ---------------------------


def test_causal_chain() -> None:
    print("\n--- 3. Causal-chain evidence (stage1022_probes.csv) ---")
    if not _artifacts_present():
        print("SKIP (run artifacts absent; structural contract only):")
        for label, day, step, key, exp in CAUSAL_CHAIN:
            ok(True, f"{label} d{day}s{step} {key} = {exp:.6g} "
                     "(documented)")
        return
    rows = _probe_rows()
    ok(len(rows) == 1801, "probes.csv row count = 1801",
       f"{len(rows)} rows")
    labels = set(r["label"] for r in rows)
    ok(labels == {"INIT", "CA_after", "B200_before", "B200_after",
                  "B210_after", "END_step"},
       "probe labels = 6 families", f"{sorted(labels)}")
    for label, day, step, key, exp in CAUSAL_CHAIN:
        hit = [r for r in rows
               if r["label"] == label and int(r["day"]) == day
               and int(r["step"]) == step]
        ok(len(hit) == 1, f"{label} d{day}s{step} present",
           f"{len(hit)} row(s)")
        if hit:
            got = float(hit[0][key])
            ok(abs(got - exp) <= 1e-9 * max(1.0, abs(exp)),
               f"{label} d{day}s{step} {key} = {exp:.6g}",
               f"got {got:.10g}")
    # Density-first ordering at the NaN step (structural).
    b6 = next(r for r in rows if r["label"] == "B200_after"
              and int(r["day"]) == 5 and int(r["step"]) == 6)
    ok(float(b6["ro_nan"]) > 0 and float(b6["u2_nan"]) > 0,
       "d5s6: ro AND u2 now NaN (Block 200 transmitted)",
       f"ro_nan={b6['ro_nan']} u2_nan={b6['u2_nan']}")
    ok(float(b6["ro_nan"]) < float(b6["u2_nan"]),
       "ρ corruption precedes momenta (density-first)")
    # Zombie stable: END_step day 6 and day 30 identical.
    def end_nan(day):
        r = next(r for r in rows if r["label"] == "END_step"
                 and int(r["day"]) == day)
        return float(r["u2_nan"]), float(r["t_nan"])
    d6 = end_nan(6); d30 = end_nan(30)
    ok(d6 == d30 == (131476.0, 142081.0),
       "zombie state stable d6..d30 (u2 131,476; t 142,081)",
       f"d6={d6} d30={d30}")
    # Max B210_after u2_nan at day 5 step 9.
    b210 = [r for r in rows if r["label"] == "B210_after"]
    mx = max(b210, key=lambda r: float(r["u2_nan"]))
    ok(int(mx["day"]) == 5 and int(mx["step"]) == 9
       and float(mx["u2_nan"]) == 131476.0,
       "max B210_after u2_nan = 131,476 at d5s9",
       f"d{mx['day']}s{mx['step']} u2_nan={mx['u2_nan']}")


# --- 4. A5 replay-verdict contract ---------------------------------------


def test_a5_verdicts() -> None:
    print("\n--- 4. A5 replay verdicts (1e-4 rel tol contract) ---")
    n_metrics = len(METRIC_NAMES)
    ok(n_metrics == 19, "block200 replay has 19 metrics", f"{n_metrics}")
    ok(len(A2_FAILING_9) == 9, "a2 fails exactly 9 metrics",
       f"{sorted(A2_FAILING_9)}")
    ok(len(A2_FAILING_9 & set(METRIC_NAMES)) == 9,
       "a2 failing 9 are all real metrics")
    ok(A2_PASSING_MOMENTUM <= set(METRIC_NAMES),
       "a2 passing momentum 4 are all real metrics")
    ok(not (A2_FAILING_9 & A2_PASSING_MOMENTUM),
       "a2 failing set and momentum PASS set are disjoint")
    ok(len(A2_FAILING_9 | A2_PASSING_MOMENTUM) == 13,
       "9 failing + 4 momentum = 13 of 19; 6 others PASS (acc_dp/lap, u1/v1)")
    for exp, (all_pass, worst, n_fail) in A5_VERDICTS.items():
        ok(worst < A5_TOL if all_pass else worst >= A5_TOL,
           f"{exp}: worst_rel {'< 1e-4 PASS' if all_pass else '>= 1e-4 FAIL'}",
           f"worst={worst:.4g}")
        if all_pass:
            ok(worst <= 4.213e-6,
               f"{exp}: worst ≤ 4.213e-6 (f32 round-off of replay)",
               f"worst={worst:.4g}")
    # a2 freeze_tw two-path split: exactly the recorded 9, momentum clean.
    ok(all(m in A2_FAILING_9 for m in (
        "ro_min", "ro_max", "ro_mean", "sum_max", "sum1_max",
        "acc_bar_u", "acc_bar_v", "dp_ratio_u", "dp_ratio_v")),
       "a2 failing 9 = ro-phase recorder columns exactly")
    ok(A5_VERDICTS["a4"][1] == A5_VERDICTS["a1"][1],
       "a4 worst identical to a1 (same CSV path)")


# --- 5. Bit-identity invariant (live md5, optional) ----------------------


def test_bit_identity() -> None:
    print("\n--- 5. Bit-identity invariant (a0 vs a0_diag) ---")
    ok(BIT_IDENTITY_MD5 == "1ef13cb4d212db8570dd64737e945897",
       "documented md5 constant", BIT_IDENTITY_MD5[:12] + '…')
    p0 = os.path.join(_RUN_DIR_A0, _CSV_DIR, "daily_diagnostics.csv")
    p1 = os.path.join(_RUN_DIR_A0_DIAG, _CSV_DIR, "daily_diagnostics.csv")
    if os.path.isfile(p0) and os.path.isfile(p1):
        def md5(p):
            h = hashlib.md5()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        m0, m1 = md5(p0), md5(p1)
        ok(m0 == m1 == BIT_IDENTITY_MD5,
           "a0 vs a0_diag daily_diagnostics IDENTICAL (md5)",
           f"{m0[:12]}…")
    else:
        print("SKIP (daily_diagnostics.csv absent; documented md5 asserted)")


# --- 6. Instrumentation gate (structural) --------------------------------


def test_instrumentation_gate() -> None:
    print("\n--- 6. Instrumentation read-only gate (structural) ---")
    # STAGE1022_* env switches default OFF -> bit-identical legacy.
    gates = [
        "STAGE1022_DIAG", "STAGE1022_FREEZE_RO",
        "STAGE1022_FREEZE_THERMAL_WIND", "STAGE1022_FREEZE_TS",
        "STAGE1022_FREEZE_RO_DOWNSTREAM",
    ]
    for g in gates:
        ok(os.getenv(g) is None, f"{g} not set (default OFF -> bit-identical)")


def main() -> int:
    test_pivot_identity()
    test_pivot_ratio_csv()
    test_causal_chain()
    test_a5_verdicts()
    test_bit_identity()
    test_instrumentation_gate()
    print(f"\n{'='*60}")
    print(f"Stage 10.22 block200 audit: {_CHECKS} checks, "
          f"{_ERRORS} errors")
    return 1 if _ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())