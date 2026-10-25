# Stage 11.5D.2 — Controlled Temporal-Factor Isolation

Frozen (date). Factor isolation (dt vs total ocean time vs shal cadence)
+ conservation baseline. No physics change (EOS, CA threshold,
B200/B210/B280/shal/advs/advt/CA/EOS/ice equations, EN4/ERA5/grid/
coefficients untouched); no guards/clamps; Family B NOT implemented
(only the diagnostic D subloop, which is a scheduler experiment, not
production); production defaults unchanged.

## 1. Conservation/closure baseline (N=1 legacy April, days 0–7, offline integrals)

From `stage11.5D1_AprLegacy` daily outputs (18 levels, dx=13.89 km,
ρ=1.028, cp=4.19e7; wet cells constant 251370; volume static by
construction — fixed levels):
- Salt: d0 1.992785e19 → d1 1.970452e19 (−1.12% day-0→1 init-adjustment
  transient) → d7 1.970060e19. Days 1–7 drift: −0.020%/7d (closure EXCELLENT).
- Heat: d0 4.416064e28 → d1 4.388940e28 (−0.62%) → d7 4.371490e28.
  Days 1–7: −0.40%/7d ≈ −0.06%/day — consistent with April surface
  cooling fluxes (physical forcing response, NOT a conservation error;
  forcing-side closure not audited — honest boundary).
- Volume: static (fixed z-levels; eta variations not in output volume).
- EUU (log daily-diag): N1 d1 6.58e14 → d29 2.25e15 (slow prognostic
  drift family, pre-existing per 11.1).
- CA: maxiter=1001 saturated every day (T-01 float32 family, pre-existing);
  CFL P95<1 at dt≤3600 (11.5B/11.2).

## 2. Matrix (April MM2=24, realistic EN4, all INIT-OK)

| Exp | N | dt_sub | Ocean/day | shal | Verdict |
|---|---|---|---|---|---|
| A (11.5D.1 N24) | 24 | 150 | 3600 | 1× | STABLE 29 d, EXIT 0, zero events |
| B (NEW) | 24 | 3600 | 86400 | 1× | UNSTABLE: first-invalid d3s1 AFTER_CA RO (106,9,2) ninv=2; maxU d2 9.1e6→1.4e11; zombie d4–21 (run died with host reboot; verdict secure) |
| C (11.5C-E rerun, final binary) | 24 | 3600 | 86400 | 24× | UNSTABLE: d3s1 AFTER_CA RO (112,17,9) ninv=1 — 12th deterministic reproduction; 11.5C path unchanged by D1/D2 edits |
| D (NEW) | 576 | 150 | 86400 | 1× | STABLE 7 d: EUU 6.59→6.15→6.19→6.51e14 (d1–5, ≡ control); maxU d1 24, d2 28; outputs d2/d4/d6 maxU 0.28/0.34/0.35 m/s, ZERO NaN; killed d7+ |

B200 dE day-1 (GAIN, B only): not collected (CSVs lost in reboot; verdict
does not need it — stability verdict is binary and secure from stdout).

## 3. Factor-isolation analysis

- B vs A (same shal 1×; dt 3600 vs 150; total 86400 vs 3600):
  B unstable, A stable → dt and/or total.
- C vs B (same dt + total; shal 24× vs 1×): BOTH unstable (same d3
  AFTER_CA RO family; C (112,17,9), B (106,9,2) — site variance class,
  cf. D-partial) → shal cadence is NOT decisive. (Also rules out the
  11.5C shal-mismatch as the SOLE cause — mismatch exists in C but B
  fails without it.)
- D vs B (same total 86400 + shal 1×; dt 150 vs 3600; N 576 vs 24):
  D stable 7 d, B blows d3 → DT IS THE LEVER. Total integration time
  alone does NOT destabilize (full-day stable at dt=150).
- CONCLUSION: per-pass dt is the PRIMARY factor; total ocean time is
  NOT independently destabilizing; shal cadence is NOT decisive.
  Mechanism reading (consistent with 11.5C.8.2): per-pass TW/btp
  increments scale with dt; at dt=3600 the sustained first-order
  feedback crosses runaway threshold within ~48 passes; at dt=150 it
  stays sub-threshold (bounded; EUU ≡ control). Interaction note: dt
  and total are not FULLY separable (B-vs-A differs in both; D-vs-B
  isolates dt at fixed total — the decisive pair).

## 4. Family B implications

Family B (full-day ocean) is VIABLE as many-small-steps: D proves
86400 s/day stable at dt=150 (cost ≈ 7× N24/day — ice dominates
runtime, not 24×). The dt stability threshold is UNMAPPED (somewhere
150 < dt* < 3600): propose a dt-threshold scan (N=48/96/192/384 at
86400 s/day → dt=1800/900/450/225) to find the largest stable dt
(cost-optimal Family B) — 11.5D follow-up, NOT started. No Family B
production implementation in this stage (D subloop is a diagnostic
experiment behind env default-OFF).

## 5. Implementation (`app/main.f90` ONLY, +~70 lines, no physics)

- `STAGE115D2_EXP=B`: N=24 fires, dt_ocean=3600 (=DT, swap no-op),
  shal-once (reuse generalized condition), MM2≥24 guard; precedence
  over FAMILY_A/115C (documented).
- `STAGE115D2_EXP=D`: 24 fires × `do ss_d2=1,24` internal loop
  (`d2_npass`; default 1 = single pass, behavior-identical for all
  other paths) wrapping advs→B280; shal additionally gated on
  ss_d2==d2_npass; dt_ocean=150. No goto/exit/stop in wrapped range
  (verified); inner `cycle`s unaffected. Diagnostics inside loop are
  env-gated (D ran with NONE except B3.3 days 1–2 + EUU + outputs).
- 11.5C path preserved: preswap condition extended (115C branch
  untouched); shal condition reduces to legacy for inactive paths;
  C-rerun reproduces E bit-for-bit at event level (proof).
- Incidents: host reboot mid-stage (B lost at d21 — verdict already
  secure; CSVs lost, stdout survived); /tmp wiped ×7 total (rebuild
  PASS routine); no trampling (single runs, stray-checks).

## 6. Files + verification

- `app/main.f90` (D2 env + D internal loop + generalized shal/preswap).
- Docs: this file (NEW); INDEX 11.5D.2 row; ROADMAP (11.5D.1 COMPLETE,
  11.5D.2 status).
- Verification: Jan OFF (`stage11.5D2_janOFF`, final binary, no env;
  EXIT 0, INIT-OK, 30 d / 32 files) md5-identical to `stage11.5C_janOFF`
  across ALL 32 outputs; full fpm battery PASS (no failures/errors);
  `git diff --check` clean.
