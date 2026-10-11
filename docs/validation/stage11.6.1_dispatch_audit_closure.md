# Stage 11.6.1 — EOS-80 Dispatch Audit Closure & Result-Interpretation Correction

Frozen (date). Narrow closure of three external-audit findings on 11.6.
No physics changed (EOS formulas, CA algorithm/threshold, B200/B210/B280,
shal, advection, ice/thermo/skt/coefficients untouched); no defaults
changed (LEGACY default, OFF bit-identical); no NetCDF (11.7); no new
freezes; Stage 12 NOT started. Only source change = `eos_diag` branch
reorder (EOS80-first) + NEW `test/eos_dispatch.f90`.

## 0. Phase 0 — dispatch audit (READ-ONLY; table, all density call sites × 4 combos)

Combos: LEGACY/EOS80 × f32/f64-precision. Expected: ro follows the SELECTED EOS.

| Call site | leg+f32 | leg+f64 | eos80+f32 | eos80+f64 |
|---|---|---|---|---|
| `eos_diag` (eq_of_state, init + per-fire) | legacy ✓ | legacy-f64 ✓ | EOS80 ✓ | LEGACY-f64 ✗ **GAP** |
| CA f32 (CA:167/199, `eos_density`+p) | legacy ✓ | legacy ✓ | EOS80 ✓ | EOS80 ✓ |
| CA f64 (CA:299/341/463-469, `eos_density_f64`+p) | leg-f64 ✓ | leg-f64 ✓ | EOS80-f64 ✓ | EOS80-f64 ✓ |
| `ca_probe` (11.6-routed via dispatcher) | legacy ✓ | leg-f64 ✓ | EOS80 ✓ | EOS80-f64 ✓ |
| NetCDF alpha/beta (`eos_density_f64`) | leg-f64 ✓ | leg-f64 ✓ | EOS80 ✓ | EOS80 ✓ |

GAP documented, not smoothed: `eos_diag` checked `eos_f64_mode` (10.21
precision switch) BEFORE `eos80_mode`, so EOS80+f64 computed LEGACY-f64
density — precision switch acted as hidden EOS selector. (Bites only when
both experimental switches combine; all 11.4/11.6 runs used default f32
precision → published results unaffected.) No other defects found; nothing
else fixed (audit mandate).

## 1. Phase 1 — dispatch fix (D-30 explicit rule, code + docs, not silent wiring)

`eos_diag` branches reordered EOS80-first. Explicit rule (D-30):
**`eos80_mode` selects the FORMULA and implies f64 evaluation in
`eos_diag`; `eos_f64_mode` is a precision switch for the LEGACY formula
only.** Resulting paths: leg+f32 → `density_anomaly` (identical);
leg+f64 → `density_anomaly_f64` (identical); eos80+f32 → `eos_density_f64`
(identical — was already f64); eos80+f64 → `eos_density_f64` (FIXED;
was legacy-f64). Every resulting path was already exercised
(legacy runs / 10.21 / 11.4-11.6 B/D) — no new untested path introduced.

## 2. Phase 2 — dispatch regression test + legacy bit-identity

- NEW `test/eos_dispatch.f90` (14/14 PASS): one wet cell, 2 levels
  (p=10/30 dbar via z), all 4 combos assert formula actually used
  (|EOS80−legacy| > 1e-6 separation), dispatcher agreement (1e-12),
  pressure enters under EOS80, legacy bit-identity vs direct calls.
  Combo eos80+f64 FAILS pre-fix by construction (legacy value differs
  ~1e-4 ≫ 1e-9 tol) — true regression coverage.
- Legacy reruns on fixed binary: Jan OFF ≡ janOFF (NDIFF=0); April OFF ≡
  AprLegacy (days 0/1/7) — fix is state-neutral when EOS80 OFF.
- Existing tests kept, none weakened: eos_test 7/7, eos80_verify 8/8,
  eos80_reference 28/28 (battery).

## 3. Phase 3 — interaction quantification + wording corrections (11.6 report)

Day-7 numbers (11.6 §3.1, unchanged): A_H=4.3715, B_H=4.3940, C_H=3.4503,
D_H=4.1593 (×1e28); A_I=215.02, B_I=291.51, C_I=776.80, D_I=1228.7.
- EOS effect at N1: heat +0.0225e28 (+0.5%), ice +76.49 (+35.6%).
- EOS effect at STALE: heat +0.7090e28 (+20.5%), ice +451.9 (+58.2%).
- INTERACTION = (effect at STALE) − (effect at N1): **heat +0.6865e28
  (15.7% of A), ice +375.41 (174.6% of A)** — symmetric via scheduler
  effects (937.19 − 561.78 = +375.41 ✓). Dominates the N1 EOS main effect
  (30× heat, 5× ice). Effects do NOT factorize.
- Plausible cause: compressible vs pressure-blind stratification interacts
  nonlinearly with coupling regime — resolvable EOS-80 gradients suppress
  spurious CA mixing, and under 24×/day STALE coupling the preserved cold
  surface amplifies basal freezing multiplicatively.
- 11.6 report corrected (results untouched): factorization claim WITHDRAWN
  (§3 interaction paragraph); run-length header split (April A/B/D full
  29 d + C kill-d8; Jan JA/JB/JD full + JC short); stability claims say
  "stated intervals" (no full-29 d data claimed for C); N-14 line fixed.
  INDEX 11.6 row interaction wording fixed (this stage).

## 4. Phase 4 — docs, battery, commit

- ROADMAP: 11.5H-RC COMPLETE, 11.6.1 CURRENT→COMPLETE (this stage); §11.6.1
  entry; 11.7 NEXT.
- DECISIONS: D-30 appended (dispatcher rule + fix + interaction correction).
- KNOWN_ISSUES: no NEW issues (gap fixed; interaction is a corrected
  interpretation, not a new defect; STAGE1021×EOS80 model-scale combos
  beyond eos_diag untested — recorded as limitation below, not an issue).
- INDEX: this 11.6.1 row.
- Battery PASS (50 SUCCESS, 0 failures; dispatch 14/14 + trio in-battery);
  strict `-Wall -Wextra` clean from rebuild; diff-check clean.

## 5. Files + verification + limitations

- Code: `src/equation_of_state.f90` (`eos_diag` reorder + D-30 comment) +
  NEW `test/eos_dispatch.f90` (14/14).
- Docs: this file (NEW); 11.6 report (wording only); ROADMAP; INDEX (11.6
  row fix + this row); DECISIONS (D-30).
- Verification: dispatch 14/14; eos trio green (battery); Jan/Apr OFF
  bit-identical; battery PASS; strict clean; diff-check clean; NO physics/
  defaults changes.
- Limitations (found, not fixed — out of scope): STAGE1021 f64 switches ×
  EOS80 exercised together only in the eos_diag unit test, not at full
  model scale; per-cell EOS80 velocity-impact maps still unavailable
  (11.3B gap); interaction mechanism is interpretation, not proof.
