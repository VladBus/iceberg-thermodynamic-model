# Stage 11.6 — EOS-80 Production Integration & Re-baseline

Frozen (date). EOS-80 pathway validation: independent reference tests +
integration audit (+1 diagnostic-consistency fix) + 4-config controlled
matrix (April kill-d8 + Jan regression). No physics changed (CA/B200/B210/
B280/shal/advection/ice/thermo/coefficients untouched); no temporal-default
change (legacy N=1 remains reference, D-22); no NetCDF (11.7); no skt
closure (D-25); no new freezes; Stage 12 NOT started. EOS-80 stays
OPTIONAL (decision §8).

## 0. Preflight + source audit

- Base `1e3e430`, clean tree, no strays. RULES/AGENTS/roadmap/physics/
  decisions/issues + 11.4 (`stage11.4_eos80_experiment.md`) + 11.4.1 read.
- Implementation: `src/eos80_unesco.f90` (pure f64 UNESCO 1983: `unesco_rho`,
  `unesco_freezing_point`, FD `unesco_drho_dT/dS`; coefficients match the
  published A–M series); dispatcher `src/equation_of_state.f90`
  (`eos80_mode`, `eos_density` f32 / `eos_density_f64`, anomaly
  rho/1000−1.02 preserved, S×1000→PSU, p passed by caller);
  `EOS_MODE` env (`EOS80`/`eos80`/`true`/`1` → ON + print, else LEGACY +
  print); `eos80_configure()` at `main:577` before first `eos_diag` (665).
- Doc corrections (this stage, no report rewrites): ROADMAP stale
  "Current status" block → 11.6 CURRENT pointer; INDEX 11.4-planning row
  appended with HISTORICAL-PLAN-SUPERSEDED note (11.6=EOS-80 now).

## 1. Phase 1 — independent reference tests (NEW `test/eos80_reference.f90`, 28/28 PASS)

- Two-level references: (A) published UNESCO TP44 anchors —
  rho(0,5,0)=999.9668, rho(35,5,0)=1027.6755 (tol 1e-3 ≈ 1e-6 rel ✓),
  Tf(35,0)=−1.9223 (tol 1e-4 ✓); (B) independent Python transcription
  (naive polynomial form, separate coder) at 6 spec conditions +
  4 boundaries (tol 1e-6 abs ≈ 1e-9 rel — catches coefficient typos,
  the dominant risk class per 11.4's i/j/m memory-correction story).
- Results: transcription confirms anchors to 3–5e-5; module matches
  transcription (density ≤1e-6, Tf exact to ~1e-13 — the test caught MY
  rounded transcription constants at 3.4e-7, module was right);
  alpha(35,5,0)=1.136e-4, beta=7.72e-4 (tol 1% ✓, literature-plausible);
  signs/monotonicity/compressibility invariants hold; no NaN at
  T∈{−2,+30}, S∈{0,40}, P∈{0,5000}; anomaly convention exact.
  (Existing `eos80_verify` 8/8 + `eos_test` 7/7 still PASS — kept as-is.)
- Separation: reference-correctness (this phase) vs model-wide
  observational validation (NOT claimed — sea-ice gate pending, D-27).

## 2. Phase 2 — integration audit (chain map + 1 diagnostic fix)

- Density chain: T/S → dispatcher → ro → CA → thermal wind → B200 →
  B210 → B280 → U/V. All 5 CA sites via dispatcher with p=z[cm]×0.01
  (CA:167/199 f32, 299/341/463-469 f64); `eos_diag` (init + per-fire)
  dispatched; thermal-wind init consumes ro[] (no bypass);
  NetCDF alpha/beta via `eos_density_f64` (diagnostic); no other Eckart
  copies repo-wide (no `0.698` outside `equation_of_state`).
- Units: legacy f(T,S) mass-fraction, no P; EOS-80 f(T,S,P), S×1000→PSU,
  p=z×0.01 dbar, out anomaly g/cm³ — consistent at every site.
- Ordering: `eos80_configure()` (577) before first `eos_diag` (665) ✓.
- FIX (diagnostic-only, legacy bit-identical by dispatcher contract):
  `ca_probe_inversions` (CA:586-593) used legacy `density_anomaly`
  directly → under EOS80 the probe disagreed with the model's own RO.
  Routed via `eos_density`/`eos_density_f64` (+p). Verified: config-A
  April bit-identical to pre-fix legacy (days 0/1/7); full-model
  state-neutral (config-C ≡ pre-fix ProdApr bit-for-bit, §3).
- Deferred (not EOS-80 defects): shal dt1/mm3 (D-26), skt/fw≡0 (D-25),
  CA 0.9e-7/float32 floor (T-01).

## 3. Phase 3 — controlled matrix (April kill-d8, same build; only EOS_MODE + scheduler differ)

| Metric (April d7) | A leg×N1 | B eos80×N1 | C leg×STALE | D eos80×STALE |
|---|---|---|---|---|
| Heat | 4.3715e28 | 4.3940e28 (+0.5%) | 3.4503e28 | 4.1593e28 (−5.8%; C-vs-D ΔEOS) |
| Icevol | 215.02 | 291.51 (+35.6%) | 776.80 | 1228.7 (+58.2% vs C) |
| maxU / maxV | 0.532 / 0.578 | 0.552 / 0.569 | 0.283 / 0.330 | 0.276 / 0.334 |
| EUU d7 | 7.5930e14 | 7.4088e14 (−2.4%) | 7.7253e14 | 7.4068e14 (−4.1% vs C) |
| CA maxiter / nmix | 1001 / 4.84M | 23 / 11.9k | 1001 / overflow | 20 / 5.45M (guard 0) |
| Salt d1→d7 | −1.99e-04 | −1.91e-04 | −1.29e-04 | −0.99e-05 (10× better) |
| NaN | 0 (29 d, exit 0) | 0 (29 d, exit 0) | 0 (kill d8) | 0 (29 d, exit 0) |
| Wall-clock | 30 s / 29 d | 24 s / 29 d | ~2073 s / 9 d | 1025 s / 29 d (~35 s/d) |
| April d29 ice / heat / NaN | 358 / 4.2755e28 / 0 | 703 (+96%) / 4.3796e28 (+2.4%) / 0 | — (kill d8) | 2400 / 3.8085e28 (−13.7%) / 0 |

- A≡AprLegacy bit-for-bit (days 0/1/7) — probe fix state-neutral.
- C≡ProdApr bit-for-bit (days 0/1/7) — same-build confirmation.
- A-vs-B (EOS effect, N=1): heat +0.5%, EUU −2.4%, salt same; ICE +35.6%
  (292 vs 215) — coherent mechanism: EOS-80 compressibility → resolvable
  stratification → CA mixes 400× less (nmix 11.9k vs 4.8M) → cold surface
  preserved → more basal freezing (conduction, fw≡0); interpretation,
  not proof. No NaN in 29-day full runs (both exit 0).
- C-vs-D (EOS effect, STALE): heat −22%→−5.8% (EOS-80 much closer to
  legacy heat!), ice +58% (777→1229), salt 10× better (−1.29e-04→−0.99e-05),
  EUU −4.1%, CA maxiter 1001→20 (guard 0). Same mechanism amplified:
  less spurious mixing → surface cold (more ice) + deep warm (less vented).
- B-vs-D (scheduler effect, EOS-80): ice 292→1229 (4.2×) — same
  scheduler-driven amplification as legacy pair A→C (215→777, 3.6×):
  scheduler and EOS effects FACTORIZE (no interaction surprise).
- Cost: EOS-80 ≈ free at N=1 (24 s vs 30 s full April); at STALE EOS-80 is
  6.5× FASTER than legacy (35 vs 230 s/day — the CA 1000-iter guard cost
  vanishes when CA converges: maxiter 20 vs 1001).

## 4. Stability assessment

- All 4 April configs: 0 NaN/Inf (A/B/D full 29 d exit 0; C kill-d8 clean).
- Conservation: salt d1→d7 O(1e-4) legacy / O(1e-5) EOS-80-STALE — no
  regime-dependent mass error; best conservation under EOS-80.
- CFL: analytic 11.2 bounds (all ≪1, dt=150 scales advective 24× down);
  unchanged by EOS (velocities same order all configs).
- CA: legacy saturates guard (1001) both schedulers; EOS-80 converges
  (maxiter 20–23, guard 0) both schedulers — EOS effect, robust.
- Jan 4-config regression: JA (leg×N1) bit-identical to janOFF (NDIFF=0);
  JB (eos80×N1) full 30 d exit 0, 0 NaN, CA maxiter 23; JC (leg×STALE)
  kill-d9, 0 NaN, CA 1001 (legacy behavior); JD (eos80×STALE) full 30 d
  exit 0, 0 NaN, CA maxiter 29, EUU d7 1.0956e15. All 4 stable.

## 5. Decision D-29 (EOS-80: OPTIONAL, not default)

EOS-80 stays OPTIONAL (`EOS_MODE=EOS80` opt-in; default LEGACY untouched).
Rationale under the corrected criterion (correctness + reference tests +
stability + impact):
- FOR: physical correctness (UNESCO compressibility vs pressure-blind
  Eckart); reference tests 28/28; stability (4/4 green, 29 d, guard 0);
  impact coherent (CA converges, salt 10× better, heat nearer legacy at
  STALE, 6.5× faster at STALE).
- AGAINST default: ice response large (+36% N1 / +58% STALE at d7, +96%
  at d29 N1) and UNVALIDATED vs observations — the sea-ice gate (D-27)
  must adjudicate the EOS dimension together with the scheduler
  dimension; April −7% EUU process review (11.4) still open; per-cell
  velocity maps unavailable (11.3B output-contract gap).
Re-decide at 11.8A with gate evidence. Matches 11.4's recommendation.

## 6. Implications (11.7 / 11.8)

- 11.7 migrates whichever EOS the dispatcher selects (config-gated I/O
  must record EOS_MODE per run — output contract note).
- 11.8A matrix runs BOTH EOS (A/B regime pair already green 29 d);
  sea-ice gate adjudicates EOS dimension together with scheduler dimension.
- skt/fw≡0 orthogonal to EOS (both EOS share the dead channel).

## 7. Files + verification

- Code: NEW `test/eos80_reference.f90` (28/28); `src/convective_adjustment.f90`
  probe → dispatcher (diagnostic-only).
- Docs: this file (NEW); INDEX 11.6 row (this stage); ROADMAP (11.5H-RC
  COMPLETE, 11.6 CURRENT→COMPLETE); physics_status EOS line; D-29;
  KNOWN_ISSUES (only if new issues — none so far).
- Verification: eos_test 7/7, eos80_verify 8/8, eos80_reference 28/28;
  A≡legacy (days 0/1/7), C≡ProdApr (days 0/1/7); JA≡janOFF (NDIFF=0);
  JB/JD full-Jan exit 0, JC kill-d9 clean; full fpm battery PASS
  (50 SUCCESS, 0 failures); strict `-Wall -Wextra` clean from rebuild;
  `git diff --check` clean; NO physics/production-defaults changes
  (EOS dispatcher default LEGACY untouched; single diagnostic probe fix).
