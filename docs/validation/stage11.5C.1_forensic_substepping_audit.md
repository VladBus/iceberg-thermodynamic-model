# Stage 11.5C.1 — Forensic Ocean Substepping Instability Audit (N=24 first-invalid trace)

Frozen (date). PURELY FORENSIC + documentation correction. No physics,
EOS, CA, advection, ice-dynamics, or numerical-scheme change; no
MAX/MIN guards or NaN clamps; `shal()` hardcoded `dt1=120/mm3=30`
untouched; production defaults unchanged. Implementation: new module
`src/stage115c1_trace.f90` + 10 call sites in `app/main.f90` (all
env-gated, default OFF → early return; `use stage115c1_trace` only).

## 1. Corrections to 11.5C interpretation (Luna's audit, verified vs code)

- **C1 — N=1 `dt_ocean`:** `main.f90:242` → `dt_ocean = dt` (= DT = 3600 s).
  N=1 is the legacy single ocean pass/day with the legacy baroclinic step,
  NOT a "single 86400 s step". 11.5C doc fixed (§2 table, §3, §4).
- **C2 — `shal()` cadence:** `shal()` (`src/shallow_water.f90:97,102`)
  hardcodes `dt1=120`, `mm3=30` as LOCALS — every call integrates exactly
  3600 s barotropic, regardless of `dt_ocean`. Per-day totals: N=2 →
  baroclinic 86400 s vs shal 7200 s; N=4 → 86400 vs 14400; N=12 → 86400 vs
  43200; N=24 → 86400 vs 86400. ONLY N=24 consistent. N=2/4/12
  RECLASSIFIED as scheduler stress tests with cadence mismatch (not
  convergence cases); N=24 = only consistent full-substepping case.
- **C3 — W timing:** W-block precedes the gate, uses legacy `dt` — clean
  for N=24 (`dt_ocean == dt`), mismatched for N=2/4/12. Diagnostic note
  only, no code change.
- **C4 — EUU:** accumulates per `shal()` call over DIFFERENT physical times
  per N; raw EUU incomparable AND EUU/N normalization NOT physically
  correct (doc §1/§3 fixed; numbers kept qualitative only).
- **Revised conclusion:** "substepping per se destabilizes" was PREMATURE
  (B/C/D confounded by mismatch). N=24 (consistent) also fails → this
  forensic audit.

## 2. Instrumentation (diagnostic-only)

Env: `STAGE115C1_TRACE=true` (per-substep checkpoints), optional
`STAGE115C1_FREEZE_COUPLING=true` (hold `txic/tyic/ans` at first-substep-
of-day values for all later substeps — breaks intra-day ice→ocean stress
feedback; ice model itself recomputes freely). Both default OFF.
Sequence per ocean substep: START → AFTER_advs → AFTER_advt → AFTER_CA →
AFTER_B200 → AFTER_B210 → AFTER_shal → AFTER_B280 (the last two have no
s112 counterpart — `shal()` as generator now isolated). Each checkpoint:
min/max T2,S2,RO,U2,V2,W + coupling stats (txic/tyic/ans/skz/hices) →
`stage115c1_trace.csv` (day,iii,sub,label,…); first-NaN/Inf scan order
mirrors s112 (S1,T1,T2,S2,RO,U2,V2,W); on event: full 5×5×3 stencil
current-vs-prev-checkpoint (before/after) + event-cell operands + coupling.
Per-substep stdout summary on AFTER_B280 (1 line/substep).
Inertness PROVEN: April N=1 run with TRACE on ≡ 11.5C-AprA (no-trace
binary) bit-for-bit across all 31 NetCDF outputs (md5).

## 3. TASK 1 — N=24 first-invalid trace (April, MM2=24, DIAG+FIRST_INVALID+TRACE)

FIRST TRACE EVENT: **day 3, iii=1, substep 1, checkpoint S01_AFTER_CA**
(prev checkpoint S01_AFTER_advt clean; ninv_total=1 — single cell):
- var **RO** (id 6) at **i=112, j=17, k=9**, value **Infinity**.
- Event-cell BEFORE (after advt): T2=-55245.6 (!), S2=4466.6 (!!),
  RO=-0.025 (finite), U2=-1.12e7, V2=1.91e7, W=-48584 — momentum and T/S
  already astronomically pathological BEFORE CA; CA (EOS) only converts
  finite-insane T/S into RO=Inf. Generator is UPSTREAM of CA.
- Event-cell AFTER (after CA): T2=-101945.7, S2=3437.4, RO=Inf (U/V/W
  untouched by CA, as expected).
- RO stencil (k=8..10): neighborhood already ±O(0.01–2800) vs normal
  ~0.008 — pathology grown over days, CA merely the detector.
- Coupling at event cell: txic=5.89e10 (!!), tyic=-5.79e10, ans=0,
  skz=4130, hices=0 — ice-water drag law `a=c17·|Vrel|/hht` transmitting
  blown ocean U into stress (FOLLOWER, see §5: txic tracks U with
  substep lag; formula `main.f90:771,775`).

## 4. Growth timeline (N=24 AFTER_B280 per substep; RO normal ~0.008)

- Day 1: maxU 27.9 → 316 (monotonic, 11×/day); RO normal; txicmax
  3.57 → 16.8. Per-operator day-1: advs/advt/CA never change maxU
  (don't touch U); sub 1: B200 27.9→22.9 (damps), **B210 22.9→38.5
  (amplifies)**; sub 24: B200 280→406 (amplifies), B210 ~flat.
  Surface-intensified (day-1 max at k=1). BOTH B200 and B210 compound
  the mode at different stages; shal/B280 only redistribute.
- Day 2: maxU 351 → 4.82e7; ROmin collapses sub 22–24
  (-0.245, -5.36, -1.08e4); txicmax → 1.16e3 (lagging U).
- Day 3 sub 1: RO=Inf event (§3) → zombie (full-NaN + ice ghost pandemic).
- No sudden trigger: smooth exponential-style growth from substep 1.

## 5. TASK 2 — N=1 vs N=24 divergence

N=1 trace: zero FIRST_INVALID (clean 29 d); day-end maxU 26.8 / 29.9 / 46.3
(days 1/2/3); txic ~2.5. N=24: 316 / 4.8e7 / zombie. Same start
(N24 sub-1 START maxU 27.9 ≈ N1 26.8 — identical initial state), divergence
WITHIN day-1 substeps. Note the structural confound: N=1 integrates
3600 s ocean/day, N=24 integrates 86400 s/day (24 full-dt passes); heat/ice
run 24×/day in BOTH. So N=24 ≠ "same interval, finer steps" — it advances
the ocean 24× further per day. The freeze control (§6) separates
"more integration" from "tighter feedback".

## 6. TASK 3 — Frozen-coupling control (N=24 + TRACE + FREEZE)

Freeze verified working: txicmax pinned at 3.57 across ALL day-1 substeps
(unfrozen: 3.57→16.8). Result: **UNSTABLE** — day-1 end maxU 316.2
(≡ unfrozen 316 to 3 digits — day-1 growth coupling-INDEPENDENT);
first event **day 2, sub 22, S22_AFTER_CA, RO at (112,18,9)** — adjacent
cell, same checkpoint, same single-cell signature, ~3 substeps EARLIER
than unfrozen (within observed run-to-run variance class, cf. D
partial-vs-rerun; direction noted honestly). Days 3+: identical zombie.
Breaking the intra-day ice→ocean stress/concentration feedback changes
NOTHING on day 1 and does not prevent blowup.

## 7. TASK 4 — Mechanism classification: **A (ocean self-instability)**

- **A — CONFIRMED as primary:** blowup persists with ice→ocean feedback
  broken (identical day-1 curve, same generator neighborhood/checkpoint).
  Driver is in the ocean-dynamics loop (B200+B210 compounding a mode at
  24 passes/day; heat interleaving damps insufficiently — cf. N=1's
  1 pass/day stability). Boundary: heat still ran (T/S updated each iii);
  ocean-ALONE (frozen T/S) NOT tested — proposed 11.5D follow-up.
- **B (ice→ocean) — RULED OUT as primary:** txic demonstrably FOLLOWS U
  (START-of-substep txic reflects previous substep's U; frozen-txic run
  grows identically); 5.9e10 txic is transmitted blowup, not cause.
  Secondary amplification via B210 surface BC possible but not driving.
- **C (ocean→ice first) — RULED OUT:** first invalid is ocean RO; ice
  ghost pandemic appears only in zombie AFTERMATH (D28 signature
  domain-wide), never before.
- **D (explicit feedback, no clear generator) — RULED OUT as primary:**
  freeze breaks the ocean→ice→ocean loop within the day, yet blowup
  proceeds unchanged. (D-style slow multi-day growth morphology remains
  true descriptively; the loop that matters is ocean-internal +
  heat-interleaving, not ice-coupled.)

## 8. Implications for 11.5D (promotion still BLOCKED)

1. N=24 full-day ocean integration at dt=3600 is self-unstable; legacy
   survives by integrating only 3600 s ocean/day. 11.5D must NOT simply
   "promote N=24".
2. Next forensic (approved, diagnostic-only): heat-freeze control (hold
   T/S/S1/T1 across substeps) to separate ocean-ALONE vs
   ocean+heat-interleaving; per-mode growth-rate measurement (which
   operator's gain >1 on day 1: B200 thermal-wind vs B210 surface-BC —
   both implicated, stages differ).
3. Candidate directions (NOT approved, NOT executed): substep-aware
   eta bookkeeping, CA-per-day option, implicit coupling, reduced
   ocean dt with proportionally-adjusted shal cadence (requires
   touching shal locals — RULES procedure + approval).
4. Artifacts: runs `stage11.5C1_AprN24trace` (event day3s1),
   `stage11.5C1_AprN1trace` (clean, ≡AprA), `stage11.5C1_AprN24freeze`
   (event day2s22); CSVs `stage115c1_trace.csv` per run. Rerun env:
   STAGE113_MM2=24 STAGE112_CFL_DIAG=true STAGE112_FIRST_INVALID=true +
   STAGE115C_OCEAN_SUBSTEPS={1,24} + STAGE115C1_TRACE=true [+FREEZE],
   ICEBERG_OCEAN_INIT_FILE=/tmp/stage114_check/initial_ts_2020-04-01_rebuild.nc,
   ERA5 `2020/2020_04/era5_2020_04_merged.nc`; Jan OFF rerun (default path,
   no STAGE env) vs `stage11.5C_janOFF` — see §10.

## 10. Default-path OFF verification (this stage's binary)

- Jan default-path rerun with the 11.5C.1 binary (no STAGE env at all;
  ERA5 `2020_01/era5_2020_01_fullcoverage_merged.nc`, init
  `initial_ts_2020-01-01_rebuild.nc`, run `stage11.5C1_janOFF3`, 30 d /
  32 files) is **md5-identical per-variable to `stage11.5C_janOFF`**
  (11.5C binary, no trace module) across **all 32 outputs** — the new
  module + call sites are proven inert when env is unset (early return
  before any state touch; `use` only).
- TRACE-on inertness: `stage11.5C1_AprN1trace` ≡ `stage11.5C_AprA` across
  all 31 April outputs (md5) — checkpoint scanning/CSV I/O perturb
  nothing even when enabled without an event.

## 9. Files changed (this stage)

- NEW `src/stage115c1_trace.f90` (forensic module; OFF → early return).
- `app/main.f90`: `use stage115c1_trace`, `s115c1_init()` at s112_init,
  `s115c1_gate_entry` + 8 checkpoints in the gated tail (additive calls
  only; no physics line touched; `shal()` untouched).
- Docs: this file (NEW); 11.5C report corrections (§2 table + C1–C4,
  N reclassification, EUU, revised conclusion); `docs/validation/INDEX.md`
  (11.5C.1 row); `docs/PROJECT_ROADMAP.md` (11.5A/B/C COMPLETE, 11.5C.1
  CURRENT, 11.5D blocked).
