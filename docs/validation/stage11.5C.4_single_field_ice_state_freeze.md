# Stage 11.5C.4 — Single-Field Ice-State Freeze Forensics

Frozen (date). PURELY FORENSIC + diagnostic. No physics, EOS, CA,
advection, ice-dynamics, or numerical-scheme change; no MAX/MIN guards or
NaN clamps; B200/B210/advs/advt/CA/EOS/txic untouched; production defaults
unchanged. Implementation: NEW module `src/stage115c4_icefreeze.f90` +
3 call sites in `app/main.f90` (use/init/gate-entry; all env-gated,
default OFF → early return) + NEW unit test
`test/stage115c4_freeze_test.f90` (7/7 PASS).

## 1. Implementation (all OFF-default)

Env `STAGE115C4_FREEZE` = OFF|UV|HICE|ANS|HSNOW|UV_HICE:
- UV: u_ice, v_ice (is1,js1)
- HICE: hice (is1,js1,ngr), hices (is1,js1)
- ANS: ans (is1,js1), an1 (is1,js1,ngr1)
- HSNOW: hsnow (is1,js1,ngr), wices (is1,js1)
- UV_HICE: u,v + hice,hices
Snapshot at first gate-fire of day, restore each gate entry (ocean sees
day-start values; ice/heat recompute freely between passes; txic/tyic and
t1/s1 NOT touched — separate experiments). Plus `seed_ice_state.csv`
(day,iii,sub,cell,hices,ans,txic,tyic,u_ice,v_ice,hice_sum for both seed
cells, written post-restore): flat lines = engagement proof (used to
qualify EVERY Scenario claim below).
- Canary: `t115c4_magic` + range check in gate_entry; on mismatch print
  `STAGE115C4 WARNING` + re-read env (repair). Zero warnings in all 5
  freeze runs (see §2) = no silent-skip class of failure.
- Full diagnostics (TRACE+GAIN+REGRESSION+TEMPORAL_SEQ) enabled on all
  freeze runs for seed-cell per-substep data (RO, ΔRO, TW, B200 gain,
  txic, ans, hice, u/v).

## 2. Incident log (honest record, no data hidden)

- Two /tmp wipes mid-campaign (volatile /tmp): first batch ran partially
  on synthetic init; /tmp rebuilt twice via `build_initial_ts.py` (PASS)
  with `test -f` guards; ALL reported runs below are realistic-EN4-init
  (`INIT-OK` = "Realistic ocean T/S applied" in log).
- Concurrent-process trampling: an orphaned model (killed tree) co-wrote
  CWD CSVs → NUL bytes (sparse-hole from truncate+append race, mechanism
  identified) + mixed rows. Killed orphans (verified zero strays),
  deleted CWD CSVs, added pre-run stray-check + abort-on-synthetic to
  launcher. Compromised partials discarded; every number below is from
  solo, INIT-OK runs. Unit test (7/7) certifies module logic
  independently of run environment.

## 3. TASK 2 — Six-experiment matrix (April N=24, realistic EN4, all INIT-OK, 0 warnings)

| Exp | Freeze | Engagement | Day-end maxU (d1→d2→d3) | First event |
|---|---|---|---|---|
| A ctrl | none | n/a | 316 → 4.8e7 → zombie | d3s1 AFTER_CA RO=Inf (112,17,9) single cell (7th reproduction) |
| B UV | u,v | u flat d1 | 316 → 4.1e5 → zombie | d3s3 AFTER_CA RO (119,17,1) ninv=106 |
| C HICE | hice,hices | hices flat 0.01 | BIT-IDENTICAL to A (316/4.82e7, same event) | same as A |
| D ANS | ans,an1 | ans flat d1 | 316 → 507 → zombie | d2s20 AFTER_CA RO (112,14,1) ninv=100 |
| E HSNOW | hsnow,wices | indirect (trajectory differs → engaged; seed lacks hsnow cols — noted gap) | 316 → 522, RO SANE → zombie | d3s5 AFTER_B210 U2 (95,3,1) ninv=32498 (momentum-first kill!) |
| F UV_HICE | u,v+hice | u flat | BIT-IDENTICAL to B (316/4.1e5, same event) | same as B |

- Phase-1 (day-1 28→316) occurs in ALL six — NO single freeze suppresses
  it. HICE freeze is proven non-vacuous (unfrozen hices evolves 0.01→0.10
  day 1 at seed cells) yet bit-identical → thickness evolution genuinely
  irrelevant.
- Phase-2 rate knobs: ANS pins B210's a1-weighting ((1−a1)·tx+a1·txic) →
  5 orders slower (507 vs 4.8e7); HSNOW acts via heat→redis→ans evolution
  → same path (RO stays sane through day 2; kill flips to
  momentum-first U2 at B210); UV mildly slows (2 orders, txic magnitude).
  All three still zombie by day 3 — rate, not switch.
- F ≡ B exactly → UV_HICE adds nothing over UV.

## 4. TASK 3 — Classification

- Scenario 1 (UV-driven phase-1): RULED OUT (B phase-1 intact; freeze
  engaged, u flat).
- Scenario 2 (HICE-driven): RULED OUT (C bit-identical to control with
  non-vacuous freeze).
- Scenario 3 (ANS-driven phase-1): RULED OUT as trigger (D phase-1
  intact); ANS CONFIRMED as phase-2 rate amplifier (5 orders).
- Scenario 4 (UV+HICE joint): RULED OUT (F ≡ B).
- Scenario 6 (multiple parallel paths): PARTIAL — ANS + HSNOW independently
  slow phase-2 (via ans→B210 path), UV mildly; but none touches phase-1.
- **Scenario 5 for the phase-1 trigger**: NO freeze (single or UV_HICE
  pair) suppresses the day-1 ramp → the trigger is NOT in any single
  ice-state component. Combined with 11.5C.2-C2 (FULL joint freeze
  bounds phase-1: 24 vs 316): bounding needs the FULL day-start
  joint-consistency; freezing SUBSETS leaves inconsistent hybrids that
  blow identically. → Return to ocean-core/operator-sequence audit for
  phase-1 (standing candidate: repeated quasi-steady B200 thermal-wind +
  B280 imprint increments at 24×/day cadence on static EN4 gradients —
  a forcing-cadence ramp needing no instability and no ice evolution).

## 5. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Single-point ice fixes predicted INSUFFICIENT (all singles tested;
   only full-joint hold works). ANS→B210 path is the best-characterized
   phase-2 rate lever (pinning a1-weighting buys 5 orders) — candidate
   structural direction, NOT approved.
3. Next forensic (diagnostic-only, proposed): phase-1 ocean-side test —
   day-1 B200-increment decomposition (thermal-wind vs DPX vs Laplacian
   per pass) to confirm the quasi-steady-ramp candidate; T2/S2-held runs
   remain MEANINGLESS (freeze the ocean itself).
4. Artifacts: runs `stage11.5C4_AprA_ctrl/Apr_{UV,HICE,ANS,HSNOW,UV_HICE}`
   (+`stage11.5C4_janOFF`); per-run trace/gain/energy/regression×2/
   temporal×2/seed CSVs; unit test `test/stage115c4_freeze_test.f90`.
5. Process lessons (kept): /tmp volatility → rebuild+guard+INIT-OK gate;
   one-model-at-a-time (stray-check); CWD-CSV trampling mode (NUL
   sparse holes); engagement proof (seed-flatness) required before ANY
   Scenario claim; canary pattern for silent-skip failures.

## 6. Files changed (this stage)

- NEW `src/stage115c4_icefreeze.f90` (5 freeze modes + seed CSV +
  canary/repair; OFF → early return).
- NEW `test/stage115c4_freeze_test.f90` (7/7 PASS: mode/snap/restore/
  counter/rollover/canary-repair).
- `app/main.f90`: `use`, `s115c4_init()`, `s115c4_gate_entry()`
  (additive calls only; physics untouched).
- Docs: this file (NEW); `docs/validation/INDEX.md` (11.5C.4 row);
  `docs/PROJECT_ROADMAP.md` (11.5C.4 status).
- Verification: Jan OFF (`stage11.5C4_janOFF`, 30 d / 32 files)
  md5-identical to `stage11.5C_janOFF` across ALL 32 outputs (final
  binary, no env); full fpm battery (see commit validation).
