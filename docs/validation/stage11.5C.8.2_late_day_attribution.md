# Stage 11.5C.8.2 — Late-Day Sustained First-Order Term Attribution (FINAL forensic stage)

Frozen (date). PURELY DIAGNOSTIC. No physics, EOS, CA, advection,
ice-dynamics, or numerical-scheme change; no guards/clamps;
B200/B210/B280/advs/advt/CA/EOS/txic/shal untouched; production defaults
unchanged. Implementation: EXTENDED `src/stage115c81_attr.f90` (new env
`STAGE115C81_PERPASS`; per-pass scalar accumulators + `late_day_attribution.csv`;
same bucket mirrors; existing hooks reused, no new call sites).

## 1. Execution (N24 April day-1, realistic EN4 INIT-OK, killed ~d13)

Run `stage11.5C82_AprN24` (TRACE + ATTR + PERPASS). All 7 target passes
(1,12,20,21,22,23,24) captured. (One launch ran with ATTR unset → pp
gated behind t81_on, no rows; relaunched with ATTR+PERPASS — documented
gate coupling, no physics impact.)

## 2. Growth table (global first-order per pass + exact control)

| Pass | B200-TW | B200-Cor | B200-DPX | B200-Lap | B200-solve | B200net | B280-btp | B280-bcl | B280net | B210 | 1stTot | Exact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | −1.3e4 | −5.8e4 | −1.4e4 | −1.9e4 | −1.6e4 | −1.2e5 | +3.1e5 | −8.4e5 | −5.4e5 | −5.2e4 | −7.1e5 | +2.78e6 |
| 12 | +2.0e4 | −3.7e5 | +5.5e4 | −5.4e4 | −2.1e5 | −5.6e5 | +6.0e5 | −1.3e6 | −7.3e5 | −6.5e5 | −1.9e6 | −2.6e4 |
| 20 | +7.6e4 | −1.6e6 | +5.3e4 | −6.3e5 | −8.6e5 | −3.0e6 | +8.8e5 | −4.0e6 | −3.1e6 | −6.6e5 | −6.7e6 | +2.3e6 |
| 21 | +8.2e4 | −2.0e6 | +6.0e4 | −8.2e5 | −1.0e6 | −3.7e6 | +7.7e5 | −5.0e6 | −4.2e6 | −8.0e5 | −8.7e6 | +3.0e6 |
| 22 | +9.5e4 | −2.5e6 | +5.7e4 | −1.1e6 | −1.3e6 | −4.7e6 | +7.6e5 | −6.2e6 | −5.5e6 | −9.3e5 | −1.1e7 | +4.1e6 |
| 23 | +9.6e4 | −3.1e6 | +4.6e4 | −1.4e6 | −1.6e6 | −6.0e6 | +7.9e5 | −8.0e6 | −7.2e6 | −1.1e6 | −1.4e7 | +5.4e6 |
| 24 | +1.0e5 | −3.9e6 | +1.7e4 | −1.8e6 | −2.1e6 | −7.7e6 | +8.4e5 | −1.0e7 | −9.4e6 | −1.3e6 | −1.8e7 | +7.2e6 |

- TW: −1.3e4 → +1.0e5 (flips + by p12, then 5× to p24). btp: +3.1e5 →
  +8.4e5 (positive throughout, 2.7×). Cor/solve/Lap/bcl/B210: negative
  and growing in magnitude (24–130×: damping scales with state).
- B200-net: −1.2e5 → −7.7e6 (NEVER positive — more negative every pass).
- Exact: +2.78e6 → +7.2e6 (2.6×, always positive except p12 ≈ 0).
  Exact/1st ratio: −3.9 (p1) → 0.01 (p12) → −0.39 (p24) — OPPOSITE SIGNS
  throughout: first-order net is net-DAMPING globally while exact grows
  via quadratic fill. Fill is NOT exhausted on day 1.

## 3. Scenario verdicts

- A (TW+b​tp sustained positive feedback): CONFIRMED — TW positive from
  p12 and growing 5×; btp positive throughout growing 2.7×. They are the
  only sustained-positive terms.
- B (TW grows, btp saturates): REJECTED (btp grows, no saturation).
- C (both saturate): REJECTED.
- D (B200-net turns positive): REJECTED (monotonically more negative).
- REFINED MECHANISM (final): global first-order = net damping
  (Coriolis/solve/Lap/bcl/B210 scale with state and win globally);
  exact growth = quadratic spin-up fill; runaway = LOCAL TW/btp
  pockets (deep TW sites per 11.5C.7, +60×/day) that detonate at
  TW-threshold (11.5C.3) and spread. Day-2+ explosion is first-order-
  dominated LOCALLY (U huge → 2U·dU huge at pockets) while global
  first-order stays negative — localized source + spreading, NOT
  global instability. 11.5D must break the LOCAL TW/btp feedback
  cadence (24 passes/day compounding before damping/CA can respond).

## 4. Full 11.5C forensic chain summary (C1→C8.2, CLOSE)

- C1: first-invalid trace (d3s1 RO-Inf (112,17,9); CA=detector; txic-freeze
  fails → Mechanism A ocean-side).
- C2: heat-freeze STABLE-5d (heat necessary); coupling-freeze fails;
  B200/B210/B280 per-op dE; 11.5C doc corrections (dt/cadence/EUU).
- C3: T/S(t1/s1)-freeze ≡ control (wrong fields; T2/S2 prognostic);
  B200-regression + temporal order (U-first globally, RO-threshold locally
  → Variant D two-phase B→A).
- C4: single-field ice freezes — NONE stops phase-1 (Sc.1/2/4 OUT);
  ANS/HSNOW slow phase-2 only (rate knobs); Scenario 5 (joint-hold).
- C5: 9-point same-cell + global E: B200+B280 co-inject ×24 (E+F);
  B210 damps; adv/CA/shal ≡ 0; N1 flat (E+F + architectural defect).
- C6: B200/B280 term mirrors validated (res ~1e-6); unit-collision
  incident → 171–176.
- C6R: seed terms — Cor 72% magnitude yet E-removing (damping);
  TW 24% but sole E-positive driver at depth; DPX kick-start only;
  B280-bcl seed engine; dominant-≠-driver.
- C7: max migrates surface→(5,19)→seed-neighborhood; deep-TW injectors
  ((5,19,17) +3.5e5, (111,17,15) +1.3e5); A-primary + B + C-migration.
- C8: budget CLOSED (+3.21e7 exact): B200-deep +2.0e7 / B210-neutral
  −0.1e7 / B280-shallow +1.3e7; top-1000 = 64%.
- C8.1: first-order vs exact split — exact = one-time spin-up fill;
  sustained = TW/btp H2; btp 81–94% broad / bcl extreme-20 only.
- C8.2 (this): per-pass growth — TW/btp sustained-positive growing;
  B200-net never positive; exact/1st opposite signs (fill dominates
  day-1 exact); runaway is LOCAL-first-order + spreading.
- FORENSIC PHASE 11.5C IS NOW COMPLETE. NEXT: 11.5D (temporal-architecture
  fix targeting sustained TW/btp feedback cadence — proposal stage only).

## 5. Files + verification

- `src/stage115c81_attr.f90`: PERPASS extension (+~200 lines; same
  mirrors; no physics lines). `app/main.f90`: NO new hooks (existing
  6 reused).
- Docs: this file (NEW); INDEX 11.5C.8.2 row; ROADMAP (11.5C COMPLETE,
  11.5D NEXT).
- Verification: Jan OFF (`stage11.5C82_janOFF`, final binary, no env;
  EXIT 0, INIT-OK, 30 d / 32 files) md5-identical to `stage11.5C_janOFF`
  across ALL 32 outputs; full fpm battery PASS (no failures/errors);
  `git diff --check` clean.
