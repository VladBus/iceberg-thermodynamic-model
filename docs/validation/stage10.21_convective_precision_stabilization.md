# Stage 10.21 — Convective Adjustment Precision & EOS float32 Stabilization Attempt

**Date:** 2026-09-23
**Status:** COMPLETE — closed as **necessary-but-not-sufficient** (negative result; CA-guard root cause confirmed and eliminated in experiments, day-5 ocean divergence persists in ALL closures)
**Baseline:** `16a4c65` (Stage 10.20); **this stage commit:** pending
**Classification target:** C/D — physics-level stabilization attempt behind env-gated switches (EOS f64 evaluation, CA f64 residual, CA epsilon ladder); source behavior bit-identical when OFF
**Production decision target:** **KEEP_CURRENT physics** (all switches default OFF); residual ocean instability is NOT the CA residual floor — root cause remains the Block-200 geostrophic spike + Thomas vertical-viscosity blowup (T-03 family, Stage 10.19/10.20 CASE D); next-stage target = ocean-init / preconditioned-solver study

---

## 1. Objective

Resolve the residual instability characterized at Stage 10.20: the convective-
adjustment (CA) 1000-iteration guard saturates from day 1 (maxiter=1001 every
daily diagnostic; residual inversions pinned at `resid_inv = 1.1921E-07` =
2⁻²³ float32 EOS quantization), slowly corrupting T/S/ρ until a density-first
divergence kills the ocean mid-day-5 (zombie state from day 6, 30-day gate
`steps executed : 55`, **acceptance 360 NOT met**).

The 10.20 report's required "approved physics stage (EOS precision / CA
threshold / guard policy per RULES.md)" is implemented **behind env-gated
switches** (Stage 10.21), with three specific questions:

1. **Root cause:** is the CA guard saturation actually CAUSING the day-5
   divergence, or is it a symptom of an upstream instability?
2. **Efficacy:** does eliminating the guard (via f64 EOS/CA arithmetic or an
   epsilon above the 2⁻²³ quantization) keep the ocean clean through day 30?
3. **Cost:** what is the operational cost (maxiter, nmix, guard hits, EUU
   trajectory) of each closure?

**Constraints (per RULES.md and AGENTS.md):** all new behavior is behind
runtime switches, default OFF → legacy bit-identical. Entity physics (EOS
formula, CA algorithm structure, Block 200/210/280, barotropic solver) is
UNCHANGED. The Thomas vertical-viscosity ill-conditioning is classified OUT
OF SCOPE for 10.21 (Stage 10.19/10.20 CASE D; documented, not fixed).

## 2. Baseline

Stage 10.20 (committed `16a4c65`) established:

- CA guard saturation is mathematically forced in float32: the residual
  inversion floor is `2⁻²³ = 1.1920928955078125E-07` while the convergence
  epsilon is `eps_density = 0.9E-07 < 2⁻²³` → the CA loop can never converge
  below the threshold → burns all 1000 iterations every column every step.
- Corrupt-but-non-NaN days 1–4 (−45…+50 °C, S<0, ρ −43.7…+9.5), density-
  first divergence mid-day-5 (`NaN_RO=198` at `F_after_conv`), zombie from
  day 6, 30-day gate `steps executed : 55`, acceptance (360) NOT met.
- Root cause of the day-5 death was NOT conclusively attributed: candidate =
  CA residual floor (T-01/T-03 family) vs upstream geostrophic spike (Block
  200, T-03 family) feeding Thomas vertical-viscosity blowup.

## 3. Method

### 3.1 Hypothesis

The EOS anomaly `ρ_anom = 1/(0.698 + aa/bb) − 1.02` evaluates to
`X = 0.698 + aa/bb ∈ [0.972462, 0.974607]` over the production T/S domain
(T ∈ [−2, 5] °C, S ∈ [0.033, 0.035] kg/kg) → `RO = 1/X − 1.02 ∈
[0.006055, 0.008318]` (NOT ~0.025 as the module doc-header claims). The
reciprocal `1/X ≈ 1.027` lies in the **[1, 2) binade** → float32 ULP =
2⁻²³ → **the CA residual inherits an absolute floor of 2⁻²³ regardless of
the operand magnitude**. Raising `eps_density` above 2⁻²³ (1.5e-7 / 2.4e-7)
or evaluating the inversion in float64 must therefore allow CA convergence.

### 3.2 Switch contract (env-gated, default OFF → bit-identical legacy)

Implemented in `src/equation_of_state.f90` + `src/convective_adjustment.f90`
+ `app/main.f90`:

| Env var                  | Values        | Effect                                                                 |
| ------------------------ | ------------- | ---------------------------------------------------------------------- |
| `STAGE1021_CA_F64`       | `true`        | f64 EOS evaluation + f64 residual in the CA column kernel              |
| `STAGE1021_CA_MIX`       | `true`        | f64 arithmetic for the T/S mixing sweep (requires `_F64=true`)         |
| `STAGE1021_CA_SCOPE`     | `all`         | RO writeback also in f64 (requires `_F64=true`)                        |
| `STAGE1021_CA_EPS`       | `1.5e-7`,`2.4e-7` | override `eps_density` above the 2⁻²³ floor                         |
| `STAGE1021_PRECISION`    | —             | informational (reports the active EOS mode at startup)                 |

All switches default OFF/FALSE → the production binary is bit-identical to
the pre-10.21 legacy path (verified, §4.1).

### 3.3 Experiment matrix (production binary, `ICEBERG_PRODUCTION=true`)

| Exp   | Config                                             | Intended closure                            |
| ----- | -------------------------------------------------- | ------------------------------------------- |
| A0    | all OFF (legacy float32, eps=0.9e-7)               | bit-identity anchor, reproduces 10.20       |
| EXP-A | `_CA_F64=true`                                     | f64 residual only; isolates the f32 mixing  |
| EXP-B15| `_CA_EPS=1.5e-7`                                  | epsilon just above 2⁻²³ (partial guard)     |
| EXP-B24| `_CA_EPS=2.4e-7`                                  | epsilon above 2⁻²² (full clean)             |
| EXP-C | `_CA_F64=true` + `_CA_MIX=true` + `_CA_SCOPE=all`  | full f64 path (EOS+residual+mix+writeback)  |
| EXP-D | `_CA_F64=true` + `_CA_MIX=true`                    | f64 inside `conv_adj`; external f32 writeback |

### 3.4 Gates (all with `ICEBERG_PRODUCTION=true`)

| Run family | ERA5 file | Duration |
| ---------- | --------- | -------- |
| `stage10.21_p30d_*` | `era5_2020_01_fullcoverage_merged.nc` (124 sl.) | 30 days (acceptance) |
| `stage10.21_p7d_*`  | `era5_2020_01_fullcoverage_gate7d.nc`            | 7 days               |
| `stage10.21_g3d_*`  | `era5_2020_01_fullcoverage_d1_4_merged.nc` (16 sl.) | 3 days            |
| `stage10.21_g1d_*`  | 1-day gate                                        | 1 day                |
| `stage10.21_bitidem_gate3d` | full coverage | 3 days (bit-identity proof, legacy OFF) |

### 3.5 Python validation layer (independent, self-contained)

Two new test modules mirror the Fortran kernels exactly (formula-identical,
float32/float64 bit-faithful):

- `python/tests/test_stage10_21_precision.py` — 13 checks (P1–P13): the
  `0.9e-7 < 2⁻²³` ordering, the epsilon ladder, EOS f32/f64 quantization
  (max |RO_f64 − RO_f32| = 1.389e-07 over a 351×101 grid), binade-ULP
  statement, fixture reproduction.
- `python/tests/test_stage10_21_convective_adjustment.py` — 18 checks
  (CA1–CA18): guard-at-2⁻²³ reproduction, convergence at 1.5e-7/2.4e-7 and
  in f64, conservation budgets (f32 rel dT=1.86e-08, dS=7.36e-08), ORIGINAL
  run reproducibility (EXP-A vs EXP-C max|dT|=2.33e-09), edge cases.

## 4. Results

### 4.1 Bit-identity (A0 = legacy, switches OFF)

| Artifact                  | A0 vs 10.20 anchor (`stage10.20_gate30d_fullcov`) |
| ------------------------- | ------------------------------------------------- |
| `results_day_00..04.nc`   | **IDENTICAL** (byte-for-byte, 5/5)                |
| `convective_guard_events.csv` | **IDENTICAL** (3001 lines each)               |
| `daily_diagnostics.csv`   | unique rows **IDENTICAL** (md5 `92a873ad…`; anchor has a day-1 duplicate row = append artifact) |
| Iceberg offline path      | `TEST_11` family untouched (no source change to iceberg modules) |

### 4.2 Gate results — final iceberg steps executed

| Exp    | 1-day | 3-day | 7-day | 30-day | 30-day acceptance (360) |
| ------ | ----- | ----- | ----- | ------ | ----------------------- |
| A0     | 12    | 36    | 55    | 55     | NOT met (zombie mid-day-5) |
| EXP-A  | 12    | 36    | 57    | 57     | NOT met (zombie mid-day-5) |
| EXP-B15| 12    | 36    | 57    | 57     | NOT met                  |
| EXP-B24| 12    | 36    | 51    | 51     | NOT met                  |
| EXP-C  | 12    | 36    | 56    | 56     | NOT met                  |
| EXP-D  | 12    | 36    | 52    | 52     | NOT met                  |

All gates EXIT 0 (guarded, no crash). 1-day gates all clean (12/12 steps,
0 NaN). 3-day gates all clean (36/36, 0 NaN) — the 10.20 CLEAN days-1–3
status is preserved in every closure. **No closure reaches day 6.** The
divergence is density-first mid-day-5 in ALL experiments (EOS min/max NaN,
n=142,081 wet cells), i.e. **eliminating the CA guard does NOT fix the
ocean death** → the guard saturation was a symptom, not the cause.

### 4.3 Per-day CA diagnostics (production 30-day runs)

Columns: `day, euu(+16), ca_nmix, ca_max_iter, ca_guard_hits, ca_affected_cols`.

| Exp  | Day | maxiter | guard hits | affected cols | nmix |
| ---- | --- | ------- | ---------- | ------------- | ---- |
| A0   | 1–4 | 1001 (every day) | 49 291–67 919 | ~128 500 | 1.79–2.22e8 |
| A0   | 5   | 1001    | 81 440      | 128 608       | 7.36e8 |
| A0   | 6+  | 1001    | 131 592    | 131 592 (max) | 1.57e9 |
| EXP-A| 1–4 | 147–238 | **0**       | ~121 000–126 900 | 3.15–3.90e7 |
| EXP-A| 5   | 1001    | 30 970     | 125 856       | 3.97e8 |
| EXP-B15|1–4 | 1001    | **12–35** (partial) | ~122 000–127 000 | 2.53–3.34e7 |
| EXP-B15|5  | 1001    | 30 984     | 126 002       | 3.93e8 |
| EXP-B24|1–4 | 125–209| **0**       | ~121 000–126 500 | 1.93–2.78e7 |
| EXP-B24|5  | 1001    | 96 755     | 129 198       | 1.16e9 |
| EXP-C| 1–4 | 146–243 | **0**       | ~121 000–127 000 | 3.15–3.90e7 |
| EXP-C| 5   | 1001    | 41 811     | 126 461       | 5.23e8 |
| EXP-D| 1–4 | 146–256 | **0**       | ~121 000–127 000 | 3.15–3.90e7 |
| EXP-D| 5   | 1001    | 85 646     | 128 528       | 1.03e9 |

Days 1–4 (ocean NOT yet NaN):

- **Guard eliminated**: EXP-A/B24/C/D guard hits = 0, maxiter drops from
  1001 to 125–256 → the CA closure converges once the residual floor is
  lifted (f64 or epsilon > 2⁻²³). nmix drops ~5–8×.
- **EXP-B15 partial guard (12–35/day)**: with eps=1.5e-7, the ~10⁴–10⁵
  inverted columns split — the vast majority now converge, but a small
  fraction still exceed 1.5e-7 because their residual lands on 2⁻²² =
  2.384e-7 (2×2⁻²³, the next binade step) — exactly reproduced by the
  standalone fixture B search (see §5). This is the "partial mode" that
  cannot be fully cleared without going above 2⁻²².
- **EUU identical through day 4** (8.653e15 → 4.457e16), i.e. the resolved
  CA arithmetic does not perturb the resolved ocean hydrodynamics; the
  divergence trigger is NOT CA-driven.

Day 5 (the divergence): every closure flips to maxiter=1001 and guard
explodes (30 970–96 755) together with the density-first NaN cascade
(`NaNflag` nonzero in U/V after `NaN_RO` at `F_after_conv`) — the CA guard
saturates AGAIN because the ocean fields arriving at the CA are already
nonphysical garbage from the upstream geostrophic spike / Thomas blowup
(T-03 family), not because of the 2⁻²³ floor. The spike's first NaN
appears in Block 210 (vertical viscosity) after the Block 200 geostrophic
spike — consistent with Stage 10.19/10.20 CASE D, INDEPENDENT of the CA
closure.

### 4.4 Total-kinetic-energy (EUU) trajectory

All closures share the same EUU trajectory through day 4 (8.65e15 →
4.46e16), then diverge only where the zombie NaN cascade begins (day 5–6).
No closure reduces the day-5 peak; the instability is pre-existing in the
received ocean state.

## 5. Python validation layer — results

Both modules run clean (`SUCCESS:` headers), 31/31 checks:

```bash
/home/vlad/miniconda3/envs/iceberg-thermodynamic-model/bin/python \
    python/tests/test_stage10_21_precision.py            # 13/13 PASS
/home/vlad/miniconda3/envs/iceberg-thermodynamic-model/bin/python \
    python/tests/test_stage10_21_convective_adjustment.py# 18/18 PASS
```

Key validated results:

1. **Root-cause number** (P1–P3): `0.9e-7 < 2⁻²³ = 1.1920928955078125e-07 <
   1.5e-7 < 2⁻²² = 2.384185791015625e-07 < 2.4e-7` — the legacy epsilon
   cannot ever be satisfied in float32.
2. **Quantization** (P4–P8): max |RO_f64 − RO_f32| = 1.389e-07 ≈ 2⁻²³ over
   the 351×101 production-domain grid; the divergence is uniform (an absolute
   floor, not relative).
3. **Binade** (P12): `np.spacing(np.float32(1/(0.698+0.2745))) == 2⁻²³` —
   the reciprocal lands in the [1,2) binade, hardening the floor.
4. **Fixture A** (4-level column, f32/0.9e-7): guard captured, resid_inv =
   1.192092895508e-07 = 2⁻²³ EXACTLY, nmix=2007, 1001 iters. At 1.5e-7 /
   2.4e-7 / f64: converges (6–7 iters, nmix 14–17).
5. **Fixture B** (5-level B15-partial, f32/1.5e-7): guard STILL captures,
   resid_inv = 2⁻²² = 2.384e-7 (above 1.5e-7) — the EXP-B15 partial-mode
   mechanism. At 2.4e-7 / f64: converges (15–17 iters, nmix 53–61).
6. **A0 vs experiments** (CA7–CA10): f32 conservation rel-dT=1.86e-08,
   rel-dS=7.36e-08 (< 1e-7); f64 conservation exact (reordering-consistent
   3.8e-09); EXP-A vs EXP-C closure difference max|dT|=2.33e-09 — the f64
   mixing alone (EXP-D) vs writeback (EXP-C) split is negligible.

## 6. Physics interpretation

- **The 10.20 characterization is confirmed and hardened.** The CA guard
  saturation is the float32 EOS quantization floor (2⁻²³) colliding with an
  epsilon (0.9e-7) set below it — a pure precision artifact, now proven by
  (a) the exact residual value 1.1921e-07=2⁻²³, (b) the binade argument,
  (c) convergence at 1.5e-7/2.4e-7/f64 on every fixture and in every
  production experiment.
- **But it was NOT the cause of the day-5 ocean death.** With the guard
  eliminated (EXP-A/B24/C/D: guard=0, maxiter≤256, nmix −5–8×), the ocean
  still diverges density-first mid-day-5, at the same EUU state, with the
  same first-NaN signature (Block 210 after the Block 200 geostrophic
  spike). The re-saturation on day 5 is a downstream symptom: the CA
  receives already-nonphysical fields.
- **Therefore**: the residual instability's driving mechanism is the
  Block-200 geostrophic spike (EN4 thermal-wind init) feeding the Thomas
  vertical-viscosity ill-conditioning (hht∼10⁻², matrix conditioning) —
  T-03 family, OUT OF SCOPE for 10.21 (classified at Stage 10.19). The
  next viable physics target is a preconditioned-solver / init-spike study
  per RULES.md, NOT further CA precision work.

## 7. Out of scope / not done (explicit)

- Thomas vertical-viscosity solver: **NOT touched** (CASE D, documented
  ill-conditioning; requires its own stage).
- Block 200 geostrophic init / EN4 thermal-wind: **NOT touched**.
- EOS formula / CA algorithm structure: **NOT changed** (only precision
  path and epsilon, behind switches).
- `grid_mode=TEST` / offline TEST_11 family: **untouched**, no claims.
- Multi-iceberg / wave erosion / rollover / fracture (AGENTS.md barrier):
  **not attempted**.

## 8. Decision (D-19)

- **KEEP_CURRENT physics** — all Stage 10.21 switches remain default OFF;
  the production binary is bit-identical to legacy (verified §4.1).
- The env-gated precision machinery (f64 path, epsilon ladder, exp matrix)
  is **retained in source behind switches** — it is a proven diagnostic and
  a ready lever for a future approved stage; it costs nothing when OFF.
- The two documentation defects surfaced by this stage are corrected:
  (1) `src/equation_of_state.f90` doc-header RO range (claims ~0.025;
  actual 0.006055–0.008318) and X range; (2) `src/param.f90:67-69`
  z-coordinate comment (×100 mismatch) — comment-only fixes, no behavior.
- Acceptance of the online-coupled production path remains OPEN: 30-day
  gate `steps executed : 360` requires the upstream ocean-init/spike
  stabilization.

## 9. Reproducible commands

```bash
# f64-experiment 30-day acceptance gate (guarded; zombie diagnosed, no crash)
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- \
  stage10.21_p30d_expA data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc
# epsilon experiments
ICEBERG_PRODUCTION=true STAGE1021_CA_EPS=1.5e-7 fpm run --flag "-I/usr/include" -- \
  stage10.21_p30d_expB15 ...
ICEBERG_PRODUCTION=true STAGE1021_CA_EPS=2.4e-7 fpm run --flag "-I/usr/include" -- \
  stage10.21_p30d_expB24 ...
# A0 bit-identity anchor
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.21_p30d_a0 ...
# Python layer
/home/vlad/miniconda3/envs/iceberg-thermodynamic-model/bin/python \
  python/tests/test_stage10_21_precision.py
/home/vlad/miniconda3/envs/iceberg-thermodynamic-model/bin/python \
  python/tests/test_stage10_21_convective_adjustment.py
```

## 10. Files changed (this stage, uncommitted)

- `src/equation_of_state.f90` — `eos_configure(f64_mode)`, `density_anomaly_f64`, doc-header fix.
- `src/convective_adjustment.f90` — `ca_configure`, `convect_column_f64`, `ca_f64_mode/mix/scope`, `ca_f64_eps` override; comment block documenting A0/EXP-A/C/D contract.
- `app/main.f90` — env-var parsing (`STAGE1021_CA_*`, `STAGE1021_PRECISION`), switch application at startup, informational mode banner.
- `python/tests/test_stage10_21_precision.py` (new, 13 checks).
- `python/tests/test_stage10_21_convective_adjustment.py` (new, 18 checks).

Full test battery: `rm -rf build && fpm test --flag "-I/usr/include"` — PASS
(55 SUCCESS, all STOP 0, incl. `All EOS checks PASSED cleanly!` and
`All convective adjustment checks PASSED cleanly!`), log
`/tmp/opencode/stage1021/fpm_test_battery.log`.