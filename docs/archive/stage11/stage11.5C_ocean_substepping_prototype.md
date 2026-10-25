# Stage 11.5C — Controlled Ocean Substepping Prototype

Frozen (date). EXPERIMENTAL scheduler, OFF bit-identical. Implementation
(`app/main.f90` ONLY, physics lines untouched): env `STAGE115C_OCEAN_SUBSTEPS`
(default 1); `ostep = mm2/N`; ocean tail (s112-vert → … → B3.3) moved inside
`iii` behind `if (mod(iii,ostep)==0)` with `dt/c2/c4/c5` save-swap-restore
(`dt_ocean` = DT = 3600 s when N=1 — i.e. the legacy single ocean
pass/day with the legacy baroclinic step — and 86400/N when N>1); old iii `end do` relocated
after the gate; iceberg_step + daily output stay outside. Tail contains no
day-loop control flow (only an inner k-loop `cycle`, verified) — move safe.
OFF validation: Jan default-path run bit-identical per-variable to D32
across all 32 outputs (md5 incomparable — 11.4.1 alpha/beta vars added).

## 1. Dependency audit (coupling map)

- advs(S,U,V,W→S), advt(T,U,V,W→T), CA(T,S→T,S+ro): ocean-only.
- B200(u1,ro,dpx→u2), B210(u2,tx/tx*,txic→u2), shal(eta,U/V), B280(u2,up2):
  ocean-only. W(u1/v1→w): recomputed per-iii (inputs static across iii).
- Ice→ocean: txic/tyic (last microstep) + ice-conc average `a1` (B210 wind
  weighting) + skz→skt (turbulent exchange for heat fw).
- Ocean→ice: u2/v2 (drag), t1/s1 (heat), skt (fw).
- EUU accounting flaw found: `euu` ACCUMULATES per `shal()` call
  (`euu+=up²`, reset once/day) — and `shal()` always integrates 3600 s per
  call while the baroclinic tail integrates 86400/N s per call, so different
  N accumulate over DIFFERENT physical times. Cross-N EUU incomparable raw;
  EUU/N normalization NOT physically correct either (corrected 11.5C.1).

## 2. Matrix (April, MM2=24, DIAG+FIRST_INVALID)

CORRECTION (11.5C.1, Luna's audit — verified against code): the DT_ocean
column below is the *baroclinic* step only. `shal()` (`src/shallow_water.f90:
97,102`) hardcodes `dt1=120`, `mm3=30` as LOCALS — every `shal()` call
integrates exactly 30×120 = 3600 s of barotropic evolution regardless of
`dt_ocean`. Actual integrated times per model day:

| Case | N | baroclinic/day | shal (barotropic)/day | consistent? |
|---|---|---|---|---|
| A | 1 | 1×3600 = 3600 s | 1×3600 = 3600 s | yes (legacy) |
| B | 2 | 2×43200 = 86400 s | 2×3600 = 7200 s | NO — cadence mismatch |
| C | 4 | 4×21600 = 86400 s | 4×3600 = 14400 s | NO — cadence mismatch |
| D | 12 | 12×7200 = 86400 s | 12×3600 = 43200 s | NO — cadence mismatch |
| E | 24 | 24×3600 = 86400 s | 24×3600 = 86400 s | yes (only consistent N>1) |

Consequences: B/C/D are scheduler stress tests with baroclinic/barotropic
cadence mismatch — NOT valid temporal-convergence cases. E (N=24) is the
ONLY physically consistent full-substepping case. W is computed BEFORE the
gate with legacy `dt` (main.f90 W-block precedes the gate) — for N=2/4/12
also inconsistent with the baroclinic step; for N=24 `dt_ocean == dt`, clean.
Raw EUU is not comparable across N (accumulates per `shal()` call over
*different physical times*); even EUU/N normalization is NOT physically
correct. `shal()` was deliberately NOT modified (stage prohibition).

| Case | N | DT_ocean (baroclinic) | Days | FIRST_INVALID | EUU end (raw, incomparable) | CA nmix (maxiter) | Final state |
|---|---|---|---|---|---|---|---|
| A | 1 | 3600 (= DT, legacy) | 29 | none | 2.103e15 | 8,876,752 (1001) | clean; ice 1079/446 |
| B | 2 | 43200 (mismatch, see above) | 29 | Day2 RO=Inf AFTER_conv_adj | 6.916e15 | OVERFLOW (1001) | full NaN; ice ghost pandemic (area 10966, vol 0) |
| C | 4 | 21600 (mismatch) | 29 | Day2 RO=Inf AFTER_conv_adj | 6.527e15 | OVERFLOW (1001) | full NaN; same ghost pandemic |
| D | 12 | 7200 (mismatch) | 29 | Day2 RO=Inf AFTER_conv_adj (rerun; first attempt: 17 d, no event, EUU 6× — run-to-run variance, see §4) | 8.322e15 | OVERFLOW (1001) | full NaN |
| E | 24 | 3600 (consistent) | 29 | Day3 RO=Inf AFTER_conv_adj | 7.718e15 | OVERFLOW, cols 263184 (1001) | full NaN |

(Matrix complete; D rerun finalized. Corrections §2–§4 applied 11.5C.1.)

## 3. Analysis (A–D; E pending)

- N=1 (legacy single ocean pass/day, baroclinic dt = DT = 3600 s) is STABLE:
  FCT + strong damping absorb the step; cross-check: 11.5C-A ≡ 11.5B-B
  bit-for-bit (EUU digits, ice totals) — the gate move itself preserves
  behavior exactly. (Earlier draft called this a "single 86400 s step" —
  WRONG; corrected 11.5C.1: N=1 uses dt_ocean = DT = 3600 s.)
- N=2/4 (baroclinic dt 12 h/6 h): RO=Infinity on Day 2 (conv_adj scan point;
  generator upstream in B200/B210/adv with dt-scaled coefficients —
  unisolated to a line, honest boundary). RECLASSIFIED 11.5C.1: cadence
  mismatch (baroclinic 86400 s/day vs shal 7200/14400 s/day) — instability
  here may be mismatch-driven, NOT substepping-driven; cannot be read as
  convergence tests.
- N=12 (baroclinic dt 2 h): rerun → RO=Inf Day 2 (first attempt: 17 d no-event,
  EUU 6×; run-to-run variance consistent with uninitialized-state sensitivity,
  D26 — verdict unchanged). RECLASSIFIED 11.5C.1: cadence mismatch
  (baroclinic 86400 s/day vs shal 43200 s/day) — same caveat as N=2/4.
- EUU cross-N incomparable raw (accumulation artifact §1) AND EUU/N
  normalization is NOT physically correct either (shal integrates different
  physical times per N — corrected 11.5C.1); per-substep numbers
  (A 2.10e15, B 3.46e15, C 1.63e15) are accounting-mixed, read qualitatively
  only — B/C still anomalous (instability growth real, not just accounting).
- Ice ghost pandemic in B/C finals (an1=1/wice=0 everywhere): ice model
  collapses onto the D28 ghost signature globally once ocean forcing
  goes NaN — same mechanism, domain-wide.

## 4. Convergence / recommendation (COMPLETE matrix)

- N=1 (legacy, dt=3600 s) stable; N≥2 ALL singular: B/C/D RO=Inf Day 2,
  E RO=Inf Day 3. REVISED 11.5C.1: the earlier conclusion "substepping per se
  destabilizes — NOT dt size" is PREMATURE. B/C/D carry baroclinic/barotropic
  cadence mismatch and cannot isolate substepping; E (N=24, the ONLY
  consistent case: baroclinic 86400 s/day + shal 86400 s/day, dt_ocean == DT)
  ALSO fails — but the generator is unisolated. Forensic first-invalid audit
  of N=24 required → Stage 11.5C.1 ( Tasks: per-operator trace, N=1 vs N=24
  divergence, frozen-coupling control, mechanism A/B/C/D classification).
- Scheduler verified (dist rows 29/58/116/196/696; MM2=24 prints).
- LEADING HYPOTHESIS (unisolated): tighter EXPLICIT ice–ocean coupling
  destabilizes — per-substep u1 snapshot, txic/eta feedback at 24×/day, CA
  re-mixing fresh states. Classic explicit-coupling instability signature
  (slow multi-day growth). Ruled OUT: dt magnitude (E≡baseline dt), FCT/CFL
  (bounded ops), the gate move itself (A≡11.5B-B bit-for-bit).
- EUU cross-N incomparable raw (shal accumulation artifact §1); normalized
  growth real in B/C/E.
- 11.5D promotion criteria: NOT MET for any N>1. Redirect 11.5D to
  coupling-point audit (u1 cadence, txic staleness, ym1 handling, shal
  mm3×dt1 timescale per call); candidate mitigations: implicit coupling,
  substep-aware eta bookkeeping, CA-per-day option.
