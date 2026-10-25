# Stage 11.5C.5 — Phase-1 Ocean Increment Decomposition (N=1 vs N=24)

Frozen (date). PURELY FORENSIC + diagnostic. No physics, EOS, CA,
advection, ice-dynamics, or numerical-scheme change; no MAX/MIN guards or
NaN clamps; B200/B210/B280/advs/advt/CA/EOS/txic/shal untouched;
production defaults unchanged. Implementation: NEW module
`src/stage115c5_optrace.f90` + 10 call sites in `app/main.f90` (use/init/
8×trace; all env-gated, default OFF → early return).

## 1. Instrumentation (all OFF-default)

Env `STAGE115C5_OPERATOR_TRACE=true`: after each of 9 checkpoints per
substep (START + AFTER_advs/advt/CA/B200/B210/shal/B280), record seed
cells (112,17,9)+(112,18,9): U,V before/after (previous-point chaining),
dU,dV,E,dE,RO,dRO,TW-proxy,DPX/DPY±d,txic,tyic,ans →
`operator_trace_*.csv`; global E=Σ(U²+V²)±ninv →
`energy_trace_global.csv`. Flush per row (kill-safe collection).
- KNOWN DEFECT (honest, analysis-corrected): substep counter increments
  per TRACE CALL (copied rollover idiom from gate-entry modules), so
  `sub` is valid only on START rows; analysis keys on (day, iii)
  (for N24 ostep=1 → iii IS the substep; for N1 single fire).
  Before/after chaining itself is intact (verified: advs/advt/CA/shal
  dE≡0 exactly — operators that never touch U2/V2).
- Runs completed FULL April (kill-at-day-3 abandoned: pace ~20 s/day).

## 2. TASK 3 — N=1 vs N=24 (April, realistic EN4, both INIT-OK)

N24 event d3s1 (112,17,9) — 8th deterministic reproduction. N1 clean
29 d (zero invalid). Day-1 global E: N24 3.1e6→3.24e7 (10×/day) vs N1
flat 1.33e6. N1 shows NO phase-1 growth (maxU ~27–30 all days).

## 3. TASK 4 — Operator contributions (day-1 totals)

| Op | N24 global dE (24 passes) | N1 global dE (1 pass) | N24 seed-cell dE |
|---|---|---|---|
| advs/advt/CA/shal | 0 (exact) | 0 | 0 (exact) |
| B200 | +2.0e7 | +1.7e5 | −9.8e3 (damps locally!) |
| B210 | −1.0e6 (damps) | +1.0e6 (spin-up transient) | −669 (damps) |
| B280 | +1.3e7 | −1.9e5 | +4.5e4 (SOLE adder at seed) |

- Phase-1 injection = B200 + B280 ONLY (3.3e7 ≈ total growth 2.9e7);
  B210 net-damping post-spin-up; adv/CA/shal structurally zero.
- Per-pass evolution (N24 global): passes 1–3 spin-up transient
  (B210 +2.8/+2.0/+0.8e6 fills u2 from rest, B200 +2–3.5e5); pass 12
  quasi-steady (B200 +2.8e5, B210/B280 damping); passes 23–24 feedback
  (B200 +3–4e6, B280 +3–4e6 — 10× midday rate). N1's single pass
  (≈pass-1 class transient) never reaches runaway.
- Seed cell: grows ONLY via B280 imprint (+4.5e4 ≈ |U| 0→210) while
  B200/B210 damp it — barotropic imprint, not local generation.
- Per-pass increments are NOT N1-like ×24 (N24 avg B200/pass 8.4e5 vs
  N1 1.7e5, growing through the day) → repetition + amplification.

## 4. TASK 5 — Classification

- A (B280→B200 cascade): SUPPORTED locally (seed grows via B280 while
  B200 damps it; B200 detonates only after TW-threshold) but B200 also
  injects globally independent of seed — A is the seed-cell story, not
  the whole.
- B (B200 self-amplification): day-1 NO (RO flat; increments
  quasi-steady); day-2 YES (gain explosion) — B is the phase-2 story.
- C (TW-driven): NO for phase-1 (TW flat day-1); YES as phase-2 gate
  (TW~0.5 threshold, 11.5C.3).
- D (DPX/DPY-driven): component only (DPX static, part of quasi-steady
  increment; no correlation evidence; honest boundary — decomposing
  B200's increment into TW/DPX/Coriolis/Laplacian needs code
  instrumentation beyond this stage).
- E (multi-operator accumulation): YES — {B200, B280} co-inject;
  {advs,advt,CA,shal} exactly zero; B210 damps. Minimal true set.
- F (N24-specific repetition): YES as cadence enabler (N1 flat, N24
  10×/day) but NOT pure repetition (per-pass increments grow) → F+E
  combined: two operators' quasi-steady increments ×24 passes, with
  late-day feedback amplification.
- VERDICT: **E+F (two-operator co-injection at 24× cadence with
  late-day feedback)**, A locally at seed, B/C as phase-2 gating.
  Phase-1 needs no instability, no ice evolution, no RO anomaly —
  just 24 repeated quasi-steady B200+B280 increments that N1 applies
  once (absorbed).

## 5. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Phase-1 is now MECHANICALLY CLOSED: repeated quasi-steady
   B200 (thermal-wind/DPX/Coriolis on static EN4 gradients) + B280
   (barotropic imprint) increments, 24×/day, late-day feedback.
   No fix needed IN the operators (all behave quasi-steadily on day 1)
   — the defect is architectural (ocean advanced 24×/day while
   calibrated/validated for 1 pass/day: legacy balances the single
   increment against 24 heat updates; N24 compounds before damping).
3. Structural directions (NOT approved): co-stepping design (ocean pass
   cadence matched to damping cadence), CA-per-day, B200-increment
   audit per RULES if operators themselves are touched.
4. Artifacts: runs `stage11.5C5_AprN24/AprN1` (+`stage11.5C5_janOFF`);
   per-run operator_trace×2 + energy_trace_global + 115c1 trace CSVs.
5. Follow-up hygiene: fix substep counter idiom for per-checkpoint
   callers (key on iii); keep flush-per-row + INIT-OK gate + stray-check.

## 6. Files changed (this stage)

- NEW `src/stage115c5_optrace.f90` (9-point same-cell + global-E trace;
  OFF → early return).
- `app/main.f90`: `use`, `s115c5_init()`, 8× `s115c5_trace()` (additive
  calls only; physics untouched).
- Docs: this file (NEW); `docs/validation/INDEX.md` (11.5C.5 row);
  `docs/PROJECT_ROADMAP.md` (11.5C.5 status).
- Verification: Jan OFF (`stage11.5C5_janOFF`, 30 d / 32 files)
  md5-identical to `stage11.5C_janOFF` across ALL 32 outputs (final
  binary, no env); full fpm battery (see commit validation).
