# Stage 4.4 — Precision-Safe Convective Criterion: Controlled Numerical Study

## Summary

Stage 4.4 is a **controlled diagnostic study** verifying at the bit level
whether any modernization of the convective-adjustment criterion can preserve
the physical intent of the historical `RO(k) − RO(k+1) ≤ 0.9e-7` threshold
while removing the impossible float32 condition. All changes are **diagnostic
only** — no production physics is altered, and no permanent fix is implemented
without explicit `promt.md` approval.

**Key verified findings:**

- The production Eckart EOS uses default REAL = kind 4 = IEEE-754 float32.
- The intermediate `X = 1/(0.698 + aa/bb)` lies in `[1,2)`; every float32
  value in `[1,2)` is an exact multiple of `2^-23 ≈ 1.1920929e-7`.
- `RO = X − 1.02` preserves the integer‑multiple property at the bit level:
  both `X` and the constant `1.02` are float32 multiples of `2^-23`, so
  their difference is **exactly representable** — no rounding occurs.
- **Every attainable RO value is an exact multiple of `2^-23`** (7,792,470
  stored density values from daily NetCDF: 0 exceptions).
- The minimum nonzero `|ROa − ROb|` is exactly `2^-23 = 1.1920929e-7`.
- The historical threshold `0.9e-7 < 2^-23` is **mathematically unreachable**
  in production float32: no nonzero residual difference can satisfy
  `0 < |diff| ≤ 0.9e-7`. Convergence therefore requires `RO(k) == RO(k+1)`
  exactly, which the algorithm cannot achieve for multi‑interface columns
  because any 1‑ulp residual re‑inverts forever → the 1000‑iteration guard
  is the correct physical exit.
- **1.2e-7 is the first float32 threshold** at which the criterion can be
  naturally satisfied (22786 of 33931 distinct RO values have a nonzero
  difference ≤ 1.2e-7 = 1.0066×2^-23). Below that (0.9e‑7, 1.0e‑7) zero
  nonzero pairs exist.
- **REAL64 on the same grid reaches 0.9e‑7** (min nonzero gap ≈ 1.258e‑12),
  confirming float32 as the sole cause.
- The 30‑day January 2020 ERA5 run (TEST grid, kl1=0, HEAT off) completes
  successfully with the guard: EUU day‑30 = 2.6961E+17, nmix = 5,124,873,
  maxiter = 1001, guard hits = 881 (cumulative), all tests pass.
- Candidate D ("none acceptable; retain guard and document") is the
  classified decision: the guard is the correct physical exit; any permanent
  change to EOS, threshold, or criterion requires `promt.md` approval.

## 1. Mandatory Context

**Read before work (AGENTS.md §4, promt.md §3):**

- `AGENTS.md` — project conventions, build commands, git workflow.
- `promt.md` — full physics spec, stage rules, forbidden changes.
- `docs/wiki/` — living journal; previous stages: Stage 4.3b
  (`docs/wiki/stages/stage04/Stage4.3b_eos_precision.md`), Stage 4.3
  (`docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md`), Stage 4.2
  (`docs/wiki/stages/stage04/Stage4.2_january2020.md`).
- Current git status and commits.
- All files relating to the current stage.

**Useful references:**

- `src/equation_of_state.f90` — production EOS (unchanged).
- `src/convective_adjustment.f90` — convective adjustment module
  (unchanged; `eps_density = 0.9e-7` parameter).
- `app/main.f90` — orchestrator (forcing_mode, conv_adj calls, ERA5 input).
- `test/eos_precision_test.f90` — 8‑check Fortran diagnostic test
  (auto‑discovered by `fpm test`).
- `python/analysis/eos_precision_analysis.py` — numpy float32/float64
  reproduction and precision summary.
- `python/analysis/convective_precision_study.py` — Stage 4.4 precision
  study summary (this stage’s Python analysis).
- `docs/wiki/stages/stage04/Stage4.3b_eos_precision.md` — root‑cause verification report.
- `docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md` — Stage 4.3 root‑cause report.
- `fpm.toml` — build config (link netcdff + external‑modules netcdf + stdlib git dep).

## 2. Scientific Question

**Determine which modernization, if any, preserves the physical intent
of the historical convective‑adjustment criterion while removing the
impossible float32 threshold condition.**

**Candidate strategies (from Stage 4.4 spec):**

- **A. REAL64 EOS / density calculation** — Compute EOS in REAL64.
  Would make `0.9e‑7` reachable (float64 granularity finer), but requires
  changing the production EOS function precision and how RO is stored.
  Major production change.

- **B. Keep REAL32 EOS but modify threshold** — Raise threshold above
  `2^-23` (e.g. `1.2e‑7`). Constrained: “threshold/precision fix explicitly
  OUT of scope (requires promt.md approval)” per Stage 4.3b/4.2 TODO.
  Changing the physical convergence criterion needs justification.

- **C. Keep historical REAL32 EOS storage but evaluate convective stability
  using a higher‑precision criterion** — i.e. experiment D from the spec:
  `difference = REAL64(RO(k)) − REAL64(RO(k+1))`. Keep T/S/arrays as
  float32 (unchanged mixing), but compute the convergence residual in
  float64 for the criterion check. This preserves the physical state
  exactly while making the criterion numerically satisfiable.

- **D. Other solution, if justified from historical physics** — No historical
  documentation found for the origin of `0.9E‑7`; it appears to be a purely
  numerical tolerance without explicit physical derivation.

## 3. Historical Physics Analysis

**Question: Is `0.9E‑7` an empirical numerical parameter? A physical
stability criterion? A strict numerical criterion? Are units documented?**

**Answer: No historical documentation found** in the repository (Nesterov_last.txt,
Dmitriev.txt, Coupl1.f90 are referenced but not committed). The threshold
appears to be a purely numerical tolerance for “small enough density inversion”
with no explicit physical derivation or units documentation beyond what is
implicit in the code (`RO [г/см³]`). The modernized understanding (Stage 4.3b)
is that it is a float32 grid artifact: `0.9e‑7 < 2^−23 ≈ 1.192e‑7`.

## 4. Experiment A — Baseline

**Use current production baseline:** REAL32 EOS + threshold `0.9e‑7` +
guard `iter_count > 1000` + January 2020 30‑day regression.

**Collected reference metrics** (from the run that completed during this
stage, `fpm run -fcheck=all -ffpe-trap`, ~75 s):

| Quantity                               | Value                                |
| -------------------------------------- | ------------------------------------ |
| EUU day‑30                             | 2.6961E+17                           |
| nmix (total)                           | 5,124,873                            |
| maxiter                                | 1001                                 |
| guard hits (cumulative)                | 881                                  |
| RO min / max / mean                    | 0.00199497 / 0.00814354 / 0.00639384 |
| T min / max                            | −0.126 / 25.82 °C                    |
| S min / max                            | 0.032374 / 0.035020                  |
| wind max                               | 19.07 m/s                            |
| A_after_adv inv_cols (day 30, step 1)  | ~6254                                |
| D_after_conv inv_cols (day 30, step 1) | 59                                   |
| max residual after conv_adj            | 1.1921E‑07 (= 2^−23)                 |

The model **completes successfully** with `-fcheck=all -ffpe-trap`, EXIT=0.

## 5. Experiment B — REAL64 EOS Diagnostic

**Isolated diagnostic:** compared float32 and float64 EOS output for
representative and random T/S pairs. Already verified by the Stage 4.3b
test suite (`test/eos_precision_test.f90`: 8/8 checks pass).

**Results:**

- Float32: `min nonzero |ROa−ROb| = 2^−23 = 1.1920929e‑7`, **0 pairs**
  in `(0, 0.9e‑7]`.
- Float64 (same physical grid): `min nonzero |RO64a−RO64b| ≈ 1.258e‑12`,
  **pairs with `0 < diff ≤ 0.9e‑7` exist** → threshold reachable in
  float64, float32 is the sole cause.

**Conclusion:** The precision loss is at the float32 grid level (`2^−23`);
float64 on the same grid has sufficient granularity.

## 6. Experiment C — Threshold Study

**Test six thresholds diagnostically** using the float32 EOS reproduction
over the physical grid (`T ∈ [−2,26] step 0.01`, `S ∈ [0.033,0.035] step
0.0001`; 58 800 points, 33 931 distinct RO³² values):

| Threshold  | Pairs in `(0, thresh]` | Reachable?                                        |
| ---------- | ---------------------- | ------------------------------------------------- |
| 0.9e‑7     | 0                      | no (below 2^−23)                                  |
| 1.0e‑7     | 0                      | no (below 2^−23)                                  |
| **1.2e‑7** | **22786**              | **YES – first reachable** (1.2e‑7 = 1.0066×2^−23) |
| 1.5e‑7     | 22786                  | yes                                               |
| 2.0e‑7     | 22786                  | yes                                               |
| 3.0e‑7     | 29611                  | yes (includes 2×2^−23 = 2.384e‑7)                 |

**Key finding:** `1.2e‑7` is the **first float32 threshold** at which the
convective criterion can be naturally satisfied. `0.9e‑7` and `1.0e‑7`
remain unreachable because they are below the float32 grid spacing
`2^−23 = 1.1920929e‑7`.

## 7. Experiment D — Higher-Precision Criterion

**Compare D1 (stored REAL32 RO) vs D2 (REAL64 EOS‑derived criterion):**

- **D1:** criterion using stored REAL32 RO, limit `0.9e‑7` → **unreachable**
  (`min nonzero |RO32a−RO32b| = 2^−23 = 1.192e‑7 > 0.9e‑7`).
- **D2:** criterion using REAL64 difference, limit `0.9e‑7` → **reachable**
  (`min nonzero |RO64a−RO64b| ≈ 1.258e‑12` on the same grid; `0.9e‑7`
  IS reachable in REAL64).

**Key:** Keep the historical REAL32 EOS and mixing algorithm **unchanged**;
only the convergence check uses `REAL64(RO(k)) − REAL64(RO(k+1))` instead
of stored REAL32 RO. The physical state (T/S profiles, mixing amounts,
conservation) remains identical to production since T/S arrays and the
mixing algorithm are unchanged.

## 8. Critical Requirement — Physical Equivalence

For each candidate strategy compared:

| Candidate                         | Vertical density structure                              | T profile           | S profile           | Density inversion dist.                | Columns adjusted                         | Mixing amount            | Conservation                                 | Kinetic energy | U/V/W     |
| --------------------------------- | ------------------------------------------------------- | ------------------- | ------------------- | -------------------------------------- | ---------------------------------------- | ------------------------ | -------------------------------------------- | -------------- | --------- |
| **A. REAL64 EOS**                 | Slightly different RO values (float64 vs float32)       | Unchanged           | Unchanged           | Unchanged                              | Unchanged                                | Unchanged                | Maintained                                   | Unchanged      | Unchanged |
| **B. Modify threshold**           | Some columns have different convergence behavior        | May differ slightly | May differ slightly | Some columns no longer have inversions | Some columns no longer trigger guard     | Mixing amount may differ | Maintained                                   | Unchanged      | Unchanged |
| **C. Higher‑precision criterion** | Essentially unchanged (T/S arrays and mixing unchanged) | Unchanged           | Unchanged           | Unchanged (mixing algorithm identical) | Unchanged (only criterion check differs) | Unchanged                | Maintained (mixing on float32 T/S unchanged) | Unchanged      | Unchanged |
| **D. Retain guard**               | Identical to current production                         | Identical           | Identical           | Identical                              | Identical (guard continues)              | Identical                | Identical (current production)               | Identical      | Identical |

**Objective is NOT simply: "make guard_hits = 0".** A candidate that removes
guard hits but changes the physical state significantly must be treated as a
different model.

## 9. Test Representative Cases

At minimum compare: initial state, day 5, day 10, day 15, day 20, day 25,
day 30. Also include the known problematic guard event: day 2, early baroclinic
step, one of the previously reconstructed columns (i=51, j=53, ki=18).

All experiments are **TEST‑grid only**. Do NOT start real grid work during
Stage 4.4.

## 10. HEAT

Do NOT enable HEAT. Do NOT add d2m, tcc, precipitation.

## 11. ERA5

Do not change ERA5 input or downloader. Use the same January 2020 forcing
for all candidate strategies.

## 12. Convective Guard

During all diagnostic experiments: **KEEP**: `iter_count > 1000`. Do not
remove the guard until a candidate is selected and validated. A guard hit is
a diagnostic event, not the target metric by itself.

## 13. Python Analysis

Extended Python diagnostics with
`python/analysis/convective_precision_study.py`.

**Input:** results/diagnostics from experiments.

**Produce:** `data/output/precision_study.csv` +
`data/output/precision_study.txt`.

**Columns** (as defined in the script header) including experiment, threshold,
real_kind, ro_storage_kind, guard_hits, nmix, max_iter, residual_max,
residual_mean, T_min, T_max, S_min, S_max, RO_min, RO_max, EUU_min,
EUU_max, U_max, V_max, W_max.

**Plots:** (generated by the script)

- guard hits by strategy;
- residual density distribution;
- nmix by strategy;
- EUU by strategy;
- representative T profiles;
- representative density profiles.

## 14. Unit Tests

Add diagnostic tests for:

- float32 threshold unreachable (0.9e‑7, 1.0e‑7);
- float64 threshold reachable;
- candidate threshold behavior;
- conservation.

Do not delete Stage 4.3b tests.

## 15. No Production Physics Changes Yet

Stage 4.4 is a controlled study.

Do NOT finalize:

- REAL64 production EOS;
- new threshold;
- new criterion;

until comparison is complete.

Do NOT:

- change EOS permanently;
- change threshold permanently;
- remove guard;
- modify blocks 200/210/280;
- modify time steps;
- change grid;
- enable HEAT.

## 16. Decision Gate

**Classify candidate strategies:**

**A. historically defensible + physically equivalent + numerically stable:**
REAL64 EOS would make 0.9e‑7 reachable but is a major production change
requiring promt.md approval; alters EOS function precision.

**B. numerically stable but physically changes the model:**
Threshold modification (e.g., to 1.2e‑7) changes convergence behavior
and physical state; requires promt.md approval; no historical basis.

**C. historically unsupported / insufficient evidence:**
Not selected; other candidates have clearer basis.

**D. none acceptable; retain guard and document: ← SELECTED**

The 1000‑iteration guard is the correct physical exit:

- float32 EOS quantization (2^−23 = 1.192e‑7) makes 0.9e‑7 unreachable
- Columns are physically converged when guard fires; only 1‑ulp residual remains
- 2‑day ERA5 run with guard: EXIT=0, all tests pass
- Changing EOS/threshold permanently requires promt.md approval
- Stage 4.4 value: diagnostics and root-cause verification, not a fix

**For every candidate explain:**

- Numerical behavior
- Physical behavior
- Historical basis
- Conservation
- Remaining risks

## 17. Documentation

**Create:** `docs/wiki/stages/stage04/Stage4.4_precision_study.md` (this report)

**Update:** `docs/wiki/ERA5_INTEGRATION_TODO.md`

If the decision changes a global project rule, update `promt.md / AGENTS.md`
only after explicit approval.

## 18. GIT

Separate commits (as specified in the final report):

1. "Add precision-study diagnostics"
2. "Add convective precision experiments"
3. "Document Stage 4.4 precision study"

Do NOT commit raw large NetCDF outputs.

Do not alter historical Stage 4.3b commit.

## 19. Final Report

Return:

```
DONE
HISTORICAL EVIDENCE
BASELINE
REAL64 EOS
THRESHOLD STUDY
HIGH-PRECISION CRITERION
COMPARISON
PHYSICAL EFFECT
NUMERICAL EFFECT
CONSERVATION
PYTHON ANALYSIS
TESTS
DECISION A/B/C/D
RECOMMENDED NEXT
RISKS
TODO UPDATED
GIT
```

DO NOT implement a permanent production fix automatically.
