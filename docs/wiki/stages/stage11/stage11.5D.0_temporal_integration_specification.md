# Stage 11.5D.0 — Controlled Temporal Integration Architecture Specification

Frozen (date). DESIGN + DOCUMENTATION ONLY. No source-code changes, no
physics changes, no implementation. Line references: `app/main.f90` at
`e94ffc5` (11.5C.8.2); `src/shallow_water.f90:97,102`;
`src/thermodynamics.f90` (`heat`); `src/advection_3d_{s,t}.f90`;
`src/convective_adjustment.f90`.

## 1. Forensic synthesis (why this spec exists)

N=1 (single ocean pass/day, dt=3600) is stable 29 d (maxU ~27–30,
RO∈[−0.001,0.008]); N=24 (24 passes/day, dt=3600 each) blows up day 2–3
(maxU 28→316 day 1 → 4.8e7 day 2 → RO=Inf day 3 at (112,17,9), 11
deterministic reproductions). Both use the SAME per-pass dt — the
difference is purely cadence/count, not step size (11.5B/11.5C).

Runaway anatomy, fully closed (11.5C.1→C8.2):
- Phase 1 (day 1, all fields sane): repeated quasi-steady B200
  (thermal-wind/DPX/Coriolis on static EN4 gradients, +2.0e7/day
  globally) + B280 (barotropic imprint, +1.3e7/day) increments, 24×/day;
  B210 net-damping (−1e6); adv/CA/shal structurally zero dE. N1 applies
  the same increments ONCE (absorbed). Three intra-day regimes: spin-up
  (B210 fills u2 from rest), quasi-steady midday, late-day 10× feedback.
- Seed cells grow ONLY via B280 (+4.5e4) while B200/B210 damp them
  locally; B200's global injection is deep (k13–16) and distributed.
- Phase 2 (day 2): advective T/S corruption (U-blown Courant numbers) →
  RO anomalies → B200 gain ×12641 at TW-threshold (~0.5) → CA turns
  insane T/S into RO=Inf → B200 spreads Inf to U (11.5C.1/11.5C.3:
  Variant D two-phase B→A).
- Term level (11.5C.6R/7/8.1/8.2): B200-dU is Coriolis-dominated (72%)
  yet energy-REMOVING (rotation + implicit solve = damping); TW (24%)
  is the sole sustained-positive B200 term, growing 60–1000×/day (H2);
  DPX/DPY only kick-start from rest (H1 static); B280 grows via the
  baroclinic-correction leg (conduit from growing barotropic mean),
  barotropic leg flat. Day-1 exact (+3.2e7) is dominated by one-time
  quadratic spin-up fill; the DANGER is sustained first-order TW/btp
  feedback continuing past day 1. Global first-order net is NEGATIVE
  (damping wins globally) — runaway is LOCAL pockets + spreading, NOT
  global instability.
- Ice side: NO single ice field controls phase-1 (UV/HICE/ANS/HSNOW/
  UV_HICE freezes all leave day-1 316 intact; HICE bit-identical;
  11.5C.4 → Scenario 5). ANS/HSNOW slow phase-2 ~5 orders (rate knobs
  via B210 a1-weighting). Only FULL joint ice+thermo hold bounds
  phase-1 (11.5C.2-C2) → splitting-structure origin, single-point ice
  fixes predicted INSUFFICIENT.
- Structural root (11.5A): legacy ocean integrates 3600 s/day of its
  own dynamics vs ice 86400 s/day (dynamically young ocean; INVERTED vs
  NEMO/MITgcm/MOM6/CICE where ocean/ice co-step). All validations to
  date share this property (self-consistent, never trajectory-validated).

## 2. Formal temporal-integration contract

### 2.1 Operator cadence table (CURRENT, N=1, MM2=24, DT=3600)

| Operator | Fires/day | dt used [s] | Reads | Writes | Integrated/day |
|---|---|---|---|---|---|
| era5_wind (forcing) | 1 (per kkk) | n/a (daily slice) | ERA5 file | tx/ty/tatm/... | 1 slice/day (tatm etc. daily-frozen; wind stress interp per-iii) |
| heat (thermo) | 24 (per iii) | 3600 | t1/s1, ice, skz, forcing | t1/s1(k=1), hice/hsnow/an1 | 86400 |
| ice dynamics (stress microloop) | 24 (per iii) | DT1-class | u/v, hices, u2 (drag) | u/v, txic/tyic | 86400 (ice time) |
| adv2d + redis | 24 (per iii) | 3600-class | an1/ice | ans/wices/hices | 86400 (ice time) |
| W recompute | 24 (per iii, pre-gate) | legacy dt (3600) | u1/v1, ym | w, ym1 | n/a (diagnostic rate) |
| advs/advt | 1 (gate) | 3600 | S2/T2 (+S1/T1 scratch) | S2/T1→S1/T1 | 3600 |
| conv_adj | 1 (gate) | n/a (iterative) | T2/S2/RO | T2/S2/RO | 3600 (state) |
| B200 | 1 (gate) | 3600 | u1, RO, dpx/dpy | u2/v2 | 3600 |
| B210 | 1 (gate) | 3600 | u2, tx/txic, ans | u2/v2, skz | 3600 |
| shal | 1 (gate) | 30×120 = 3600 FIXED (hardcoded locals dt1/mm3, shal:97,102) | ym/up/vp | ym2/up2/vp2 | 3600 (always, any N) |
| B280 | 1 (gate) | n/a (algebraic) | u2, up2 | u2/v2 | 3600 (state) |
| iceberg_step | 1 (gate) | 3600 | t2/s2/u2/v2, ERA5 | ib_state | 3600 |
| write_nc | 1 (gate) | n/a | all | file | 1/day |

### 2.2 State ownership

- Ocean prognostic (T2/S2/RO/U2/V2/W): owned by ocean tail (advs/advt/
  CA/B200/B210/shal/B280/W); read by ice (drag/txic, heat fw via skz)
  and iceberg. advs WRITES S2, CA operates ON T2/S2 (11.5C.3 audit).
- Scratch/thermo (T1/S1): written by heat (k=1) + advs/advt; freezing
  them is a proven no-op (11.5C.3) — NOT coupling state.
- Ice state (hice/hsnow/an1/ans/wices/hices/u/v/txic/tyic): owned by
  heat/redis/dynamics; read by B210 (ans, txic/tyic) and heat (skz).
- Forcing (tx/ty/tatm/...): owned by era5_wind (daily) + per-iii wind-
  stress interp; read by ice + B210.
- Barotropic (ym2/up2/vp2): owned by shal; read by B280 + W + ice (ym).

### 2.3 Coupling points (current)

- Ice→ocean: sampled at gate fire (txic/tyic/ans = last-iii values;
  11.5C.1: staleness confirmed, freezing them changes nothing).
- Ocean→ice: live arrays each iii (u2/v2/t1/s1/skz evolve only at gate;
  effectively daily-frozen within the day).
- Forcing→all: daily (kkk); output: daily (write_nc).

### 2.4 Temporal invariant (TARGET)

Every prognostic subsystem must advance exactly 86400 s per physical
model day at ANY resolution N. LEGACY VIOLATES THIS (ocean 3600 s/day) —
the invariant is therefore a DESIGN TARGET, not a description. Two
families below; the invariant binds Family B fully and Family A in the
refinement sense (same totals as legacy, split finer).

## 3. Why old N=2/4/12 were invalid (11.5C.1 corrections, binding)

Per-day integrated times (baroclinic N×86400/N = 86400 s ALWAYS vs
shal N×3600 s): N=2 → 86400 vs 7200; N=4 → 86400 vs 14400;
N=12 → 86400 vs 43200; ONLY N=24 → 86400 vs 86400. N=2/4/12 were
scheduler stress tests with baroclinic/barotropic cadence mismatch, NOT
convergence cases. Additionally: W pre-gate with legacy dt (mismatched
for N≠24... wait — W uses dt=3600 always; for N=24 dt_ocean==dt so
consistent); EUU accumulates per shal() call over different physical
times (raw and EUU/N both incomparable); N=1 dt_ocean = DT = 3600
(not 86400 — corrected). Any future N MUST specify shal handling
explicitly (it cannot follow dt_ocean without code change).

## 4. Candidate schedulers

### Family A — legacy-total-preserving (RECOMMENDED FIRST, 11.5D.1)

Ocean integrates 3600 s/day TOTAL (bit-compatible limit with legacy).
N ocean substeps/day, dt_sub = 3600/N per operator (advs/advt/CA/B200/
B210 with dt_sub; c2/c4/c5 recomputed — same swap mechanism as 11.5C
prototype, verified). shal: UNCHANGED code but called ONCE per day
(outside the substep loop — 3600 s total preserved; calling it N×
would integrate N×3600 s and reintroduce mismatch). W: recomputed per
substep with dt_sub (moved inside gate — placement change only, formula
untouched; W is diagnostic input to advs). CA: per substep (same
threshold/procedure). Ice/thermo/forcing/output: UNCHANGED (24×/day
iii cadence, daily forcing, daily output). Coupling points unchanged
(gate-sampled ice state; ocean state fresh per substep for ice drag —
documented as the ONLY coupling semantic change vs legacy, and the
quantity under test).
- N=1: identical to legacy (bit-identity gate, as 11.5C-A proved).
- N=2: 2×1800 s; N=4: 4×900 s; N=6: 6×600 s; N=12: 12×300 s;
  N=24: 24×150 s.
- Purpose: pure splitting-error/cadence measurement at fixed physics
  totals. Pass criteria: all gates (§6) AND day-1 E within noise of
  legacy (no new dynamics — totals identical by construction).

### Family B — full-day co-stepped (AFTER A passes + stabilization review)

Every subsystem advances 86400 s/day. Ocean N substeps of dt=86400/N
(24/12/6/4/2/1 → 3600/7200/14400/21600/43200/86400 s). REQUIRES (flagged,
RULES-procedure changes, NOT approved here): shal dt-aware microstep
count (mm3 = dt_sub/120 with dt1=120 fixed — changes shal LOCALS from
hardcoded to parameterized; behavior change gated); W per-substep with
dt_sub; CA per substep (accepted: same procedure, more calls);
ice/thermo: UNCHANGED 24×/day (for N=24 cadences coincide; for N<24 ice
runs its own mm2 cadence — coupling sync specified per N below);
forcing daily (unchanged); output daily + optional per-substep EUU
(normalized per second — NOT raw accumulation).
- N=24: 24×3600 s (= 11.5C-E, PROVEN UNSTABLE — first Family-B test must
  reproduce the blowup as a sanity check, then show what tames it; DO
  NOT expect stability).
- N=12/6/4/2/1: dt_sub = 7200/14400/21600/43200/86400 s (CFL grows ∝
  dt — gate on CFL P95; 86400 s single-step is legacy-violating by
  design and expected to fail first).
- Purpose: true temporal architecture (modern-practice cadence).
  Requires full re-baseline + re-validation (all stage-11 baselines
  were produced in the dynamically-young regime).

### Per-N coupling sync (both families)

- N=24 & MM2=24: ice and ocean cadences coincide — ice state fresh per
  ocean substep (the 11.5C-E configuration; Family A dt=150 s).
- N<24: ice runs mm2=24×/day regardless; ocean substep k consumes the
  latest ice state (documented staleness ≤ 24/N iii-steps); ocean state
  for ice drag refreshes per ocean substep (finer than legacy daily).
- Forcing: daily for all N (Stage 11.5 scope; diurnal forcing is OUT).
- Output: daily NetCDF (unchanged) + per-substep EUU-per-second +
  FIRST_INVALID (existing diagnostics cover all N).

## 5. Acceptance metrics (all N, all gates)

5.1 Stability: first-invalid day/substep/location/var (s112, already
instrumented); max|U|,|V|,|W| per day; max TW-proxy; max|RO|; hard caps
for gate PASS: |U|<10 m/s, |RO|<0.01.
5.2 Energy: EUU-per-second (NOT raw EUU) day 1/7/29; per-op dE/day via
11.5C.8 modules (B200/B210/B280 exact + first-order); boundedness (no
exponential day-over-day growth >2× after spin-up).
5.3 CA: maxiter/day (<500 for pass), guard-hit columns/day, residual
distribution (existing ca_probe).
5.4 CFL: max + P95/day (existing s112 distributions); gate requires
P95 < 1 for the stepped dt.
5.5 Conservation: mass/salt/energy closure error/day from daily outputs
(<1%/day for pass; NOTE 11.5A: no closure audit exists yet — method:
global integrals of T/S/volume from results_day_*.nc; establishing the
N=1 baseline closure is a prerequisite task of 11.5D.1).

## 6. Gating strategy (per candidate scheduler)

6.1 3-day gate: EXIT 0, zero NaN/Inf (s112 clean), |U|<10 m/s,
|RO|<0.01, EUU-per-second bounded (day3/day1 < 2), CA maxiter ≤ 1001-row
behavior unchanged-or-better vs N=1 baseline.
6.2 7-day gate: all 3-day metrics hold to day 7; CA maxiter < 500 sustained;
conservation errors < 1%/day; no systematic drift vs N=1.
6.3 29/30-day gate: full April clean; solution physically reasonable vs
N=1 baseline (pattern correlation of T/S/U fields, not bit-identity);
conservation drift-free; EUU-per-second steady.
6.4 Promotion rule: Family A N=24 must pass ALL gates before ANY Family
B experiment is launched; Family B N=24 must reproduce-then-tame (blowup
reproduction as sanity, then mitigation) before N<24 Family B runs.
11.5D.1 scope = Family A implementation + gates ONLY.

## 7. Design-only statement

This is DESIGN ONLY. No scheduler is implemented in 11.5D.0; no source
line changed; no physics changed. Implementation belongs to 11.5D.1
(Family A + gates, §6.4). Temporal architecture as root cause REMAINS
the leading TESTABLE hypothesis (NOT proven): forensics closed the
mechanism (localized TW/btp feedback + spreading under 24× compounding)
but a stabilized full-day integration has never been demonstrated —
11.5D.1's Family A will test whether cadence alone (at fixed totals)
is benign, which the hypothesis predicts.
