# Stage 11.5C.2 — Ocean Substepping Coupling Forensics (Heat Control + Operator Gain Audit)

Frozen (date). PURELY FORENSIC + diagnostic. No physics, EOS, CA,
advection, ice-dynamics, or numerical-scheme change; no MAX/MIN guards or
NaN clamps; B200/B210/txic/shal/CA/EOS untouched; production defaults
unchanged. Implementation: NEW module `src/stage115c2_gain.f90` + 10 call
sites in `app/main.f90` (all env-gated, default OFF → early return).

## 1. Instrumentation

- `STAGE115C2_FREEZE_HEAT=true`: snapshot thermo/ice state
  (t1,s1,hice,hsnow,an1,ans,wices,hices,ice-u,ice-v — the full set heat(),
  redis() and the ice microloop write and the ocean tail reads: advs reads
  s1, advt reads t1, B210 reads ans/txic; skt is never written = dead
  input, excluded) at first gate-fire of day; restore at every gate entry
  (ocean always sees day-start thermo/ice state; heat/redis/dynamics
  recompute freely between passes). txic/tyic NOT touched (that's 11.5C.1
  exp B, kept separate).
- `STAGE115C2_OPERATOR_GAIN=true`: per-operator before/after audit of B200,
  B210, shal, B280. Seed cells (112,17,9) [11.5C.1 N24 event] + (112,18,9)
  [11.5C.1 freeze event]: U,V, ΔU, ΔV, gain=|V_after|/|V_before|
  (denom<1e-6 → 0; non-finite pair → -1) → `operator_gain_112_17_9.csv`
  (one added `cell` column vs spec — documented). Global E=Σ(U²+V²) over
  wet cells before/after each operator → `energy_checkpoint.csv`
  (+ ninv_before/ninv_after — needed for zombie phase, documented).
  shal dE≡0 by construction (never touches U2/V2) — recorded as control.

## 2. Init-provenance incident (honest record)

First 3-run batch ran on SYNTHETIC ocean init: /tmp/stage114_check was
wiped between 11.5C.1 (Oct 2 02:08) and 11.5C.2 (Oct 2 14:56) →
ICEBERG_OCEAN_INIT_FILE dangling → synthetic fallback (log: "realistic
ocean T/S unavailable"). That batch (runs `AprA_gain/B/C`, kept on disk)
is internally controlled (identical init) but NOT comparable to 11.5C.1.
All results below are RERUNS (`*2`) after rebuild
(`python/ocean/build_initial_ts.py` Jan+Apr → /tmp, both PASS) with
`test -f` guard. Synthetic batch retained as init-sensitivity side data
(same fast-blowup family, different seed cells — mechanism not
init-specific).

## 3. TASK 1/3 — Three-experiment comparison (April N=24, realistic EN4 init)

| Exp | Freeze | First event | Day-end E (d1→d5) | maxU d1→d3 |
|---|---|---|---|---|
| A2 normal | none | d3 s1 AFTER_CA, RO=Inf (112,17,9) single cell — EXACT 11.5C.1 reproduction (deterministic) | 3.24e7 → 3.3e16 → zombie | 316 → 4.8e7 → zombie |
| B2 coupling | txic/tyic/ans | d2 s22 AFTER_CA, RO=Inf (112,18,9) — EXACT 11.5C.1-freeze reproduction | 3.30e7 → 4.5e15 → zombie (≡A to 3 digits d1) | ≡A |
| C2 heat | thermo/ice set | d4 s1 S01_START, S1=NaN (122,24,1) single cell, neighbors pristine — heat-generated, momentum bounded | 2.06e6 → 2.94e6 → 5.37e6 → 3.76e6 → 1.92e6 (bounded thru d6!) | 24 → 34 → 43 → 45 (bounded!) |

- 5-day criterion: C2 STABLE (zero invalid d1–d3; momentum bounded thru
  d6) while A2/B2 zombie by d3 → **heat/thermodynamic evolution is
  NECESSARY for the fast 3-day momentum blowup (Scenario 1 CONFIRMED)**.
- C2 d4 S1 event classified freeze-artifact: single-cell heat NaN at k=1
  in open-water cell (hices=0, sane skz=74/txic) with all ocean fields
  bounded — consistent with melt-out division under frozen thickness
  (heat:407–414 pattern), unisolated to a line; NOT the ocean-core
  blowup (momentum never explodes).
- Synthetic-batch C (heat-freeze): flat E d1–d8 (2–9e6), ocean blowup d9
  (E 3e15) → slow ocean-core residual mode exists independent of heat
  (Scenario 6 admixture for the SLOW mode; fast mode = Scenario 1).
- T/S ordering (A2 trace): d1 T/S pristine while maxU 38→316; T/S corrupt
  only d2 second half (advected by blown U); CA→RO=Inf d3. Momentum
  LEADS, thermodynamics FOLLOWS — except the loop needs evolving t1/s1
  (frozen pristine fields starve the advective-corruption leg).

## 4. TASK 2 — Operator dominance (realistic init, spun-up d1s24 dE/pass)

| Op | A2 dE | B2 dE | C2 dE |
|---|---|---|---|
| B200 | +3.92e6 | +3.93e6 (≡A) | +1.9e5 (20× less) |
| B210 | −9.1e5 (damps) | −8.2e5 | −1.0e5 |
| shal | 0 (control) | 0 | 0 |
| B280 | +4.17e6 | +4.21e6 (≡A) | −2.3e5 (FLIPS to damping) |

- **Scenario 4 (B200) CONFIRMED co-primary**: thermal-wind injection
  dominates; heat-freeze cuts it 20× (needs evolving RO anomalies).
- Barotropic-imprint path (shal→UP2→B280) co-injects +4.2e6 in A/B, flips
  to damping under heat-freeze → dependent on the same thermo loop, not
  independent driver. Scenario 5 (shal per se) RULED OUT (dE≡0).
- Scenario 3 (B210) RULED OUT globally (net damping every pass; early
  max-cell amplification in 11.5C.1 is a local spin-up transient).
- Seed cell (112,17,9) A2: d1–d2s12 B200/B210 gains <1 (local damping!),
  growth via B280 ×1.3–1.8 (barotropic imprint); d2s24 B200 ×12641
  (0→4.57e6 — thermal wind on corrupted RO neighborhood), B210 ×13.4
  (→6.1e7); d3s1 B200 takes 2.2e7→Inf (spreads CA's RO=Inf into U).
  Generator sequence: B280-fed growth → B200 local explosion on
  corrupted RO → B210 secondary ×13 → CA→RO=Inf → B200→U=Inf.
- B2 ≡ A2 operator-by-operator (coupling freeze changes nothing
  quantitatively) — second independent rule-out of ice-stress feedback.

## 5. TASK 4 — Classification

- Fast (3-day) blowup: **Scenario 1 (heat evolution necessary) +
  Scenario 4 (B200 thermal-wind generator)**, with barotropic-imprint
  (B280) co-amplification. B/C/D-primary ruled out (11.5C.1 + B2≡A).
- Slow (9-day, synthetic C) residual: **Scenario 6** (multi-operator /
  splitting drift, ocean-core) — unisolated, needs heat-freeze+T/S
  follow-up, NOT 11.5D-blocking for the fast mode.
- Refined loop: evolving t1/s1 → advective T/S drift → RO anomalies →
  B200 thermal-wind U injection (+B280 barotropic imprint) → blown U →
  stronger advective corruption → CA/EOS RO=Inf → B200 spreads Inf to U.
  Legacy N=1 survives by integrating 1/24 of the ocean dynamics per day
  (heat interleaving damps the single pass).

## 6. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24: full-day ocean integration is self-unstable via
   the thermo-advective-B200 loop.
2. Next forensic (diagnostic-only): T/S-held control (freeze s1/t1 ONLY,
   let ice evolve) to isolate the advectand leg from ice-state legs;
   per-mode B200 gain vs RO-anomaly regression (quantify the +14%/pass).
3. Candidate directions (NOT approved, NOT executed): CA-per-day option,
   substep-aware advective bookkeeping, B200 thermal-wind limiter review
   (RULES procedure + approval — touches physics).
4. Artifacts: runs `stage11.5C2_AprA_gain2/B2/C2` (+ synthetic
   `AprA_gain/B/C` side batch, `stage11.5C2_janOFF2`); per-run
   `operator_gain_112_17_9.csv` + `energy_checkpoint.csv` +
   `stage115c1_trace.csv`; env: STAGE113_MM2=24 DIAG+FIRST_INVALID,
   SUBSTEPS=24, TRACE+GAIN [+CPLFREEZE/+HEATFREEZE].

## 7. Files changed (this stage)

- NEW `src/stage115c2_gain.f90` (FREEZE_HEAT + OPERATOR_GAIN; OFF →
  early return).
- `app/main.f90`: `use stage115c2_gain`, `s115c2_init()`,
  `s115c2_gate_entry`, 8× `s115c2_op` before/after B200/B210/shal/B280
  (additive calls only; B200/B210/shal/CA/EOS/txic untouched).
- Docs: this file (NEW); `docs/validation/INDEX.md` (11.5C.2 row).
- Verification: Jan OFF rerun (`stage11.5C2_janOFF2`, 30 d / 32 files)
  md5-identical to `stage11.5C_janOFF` across ALL 32 outputs (final
  binary, no env); full fpm battery (see commit validation).
