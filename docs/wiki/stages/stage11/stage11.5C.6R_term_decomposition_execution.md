# Stage 11.5C.6R — B200/B280 Term Decomposition EXECUTION (N=24 real trajectory)

Frozen (date). PURELY EXECUTION + VALIDATION + ANALYSIS of the existing
11.5C.6 diagnostic. No physics, EOS, CA, advection, ice-dynamics, or
numerical-scheme change; no guards/clamps; B200/B210/B280/advs/advt/CA/
EOS/txic/shal untouched; production defaults unchanged. ONE src change:
Fortran unit numbers 81–86 → 171–176 (11.5C.6R find: 81 collides with
s112 cfl_unit, 82 with CA ca_diag_unit, 86 with s112 events_unit →
foreign rows interleaved in term CSVs; first attempt's CSVs discarded
as contaminated; rerun clean). No physics lines touched.

## 1. Execution (April N=24, MM2=24, DT=3600, realistic EN4 INIT-OK)

Run `stage11.5C6R_AprN24b` (TRACE + B200/B280 TERMS + DIAG/FIRST_INVALID),
killed day 8 (days 1–7 flushed per-row; exceeds 2-day spec). All 6 term
CSVs + trace collected, 0 strays. Event d3s1 (112,17,9) — 9th
deterministic reproduction.

## 2. TASK 2 — Mirror validation: PASS

Worst |res/total| over finite rows: B200 1.1e-6/1.2e-6/7.2e-6
(seed1/seed2/quiet), B280 1.9e-7/1.2e-6/1.3e-6 — float32 regrouping noise
(2⁻²³ class), 6 orders below signals. Mirrors EXACT (incl. s22 conditional
path, bottom/land flags, dzz bottom formula). First rows match 11.5C.5
independently (B200 d1s1 DPX-led dU −0.09, DPY-led dV −1.46).

## 3. TASK 3 — Term analysis (seed1 day-1, n=24 passes)

B200 dU totals: TW −118 (24%), DPX −1.4 (0.3%), Cor −356 (72%),
Lap −4.6 (1%), solve −11.3 (2%), ice ≡ 0; total −492.
B200 dV totals: TW +80 (87%!), DPY −27, Cor +1.3, Lap +37, solve +1.3;
total +92.
B280 dU totals: btp +0.41 (<0.1%), bcl +496 (~100%); total +497.
B280 dV totals: btp +0.33, bcl −281.5.
E-weighted (2U·dU+2V·dV, seed1 day-1): TW −1.95e4, Cor −1.32e4,
Lap −7.0e3, solve −5.1e3, DPX +1.25e3 (ONLY positive term).
Seed2/quiet: ~0 (non-participating).
- Coriolis DOMINATES B200 dU magnitude but is ENERGY-REMOVING at seed
  (rotation + implicit solve = strong local damping, not a source).
- DPX/DPY: static background (−0.09→−0.025, H1-like), pass-1 kick leaders
  (dU −0.09 DPX-led, dV −1.46 DPY-led from rest), negligible thereafter.
- TW: second magnitude, grows 0.01→20 (1000×) through day-1 (H2).
- B280 growth is ENTIRELY the baroclinic-correction leg (btp flat
  ±0.2–0.7 all day); bcl −0.2→+0.4→+5.9→+78→+92 (H2) — conduit from
  growing barotropic mean to baroclinic U.
- At seed, B200 REMOVES E (−4.4e4) — seed is a B200 energy SINK;
  global +2e7 injection happens at UNSAMPLED cells (honest boundary:
  injection site unmapped at term level; maxU-cell targeting proposed).

## 4. Timeline (seed1 B200 dU): p1 DPX-led (−0.09) → p12 TW-led (−2.5) →
p23/p24 Cor+TW detonation (−81/−96; Cor ∝ grown V, TW ∝ grown sum).
H1 (constant accumulation): DPX background only. H2 (state-dependent
gain): TW (1000×), Cor (0→−75), bcl (450×). → H1+H2混合: static DPX
kicker + H2 growth of TW/Cor/bcl.

## 5. TASK 4 — Classification

- A (TW-driven): PARTIAL — TW grows (H2) and leads V, but E-removing at
  seed; global injector role unproven at term level (sampled cells sink).
- B (DPX-driven): INITIATOR only (pass-1 kick, static after) — not the
  growth engine.
- C (Coriolis-driven): REJECTED as source (dominant magnitude but
  E-removing; conserves + damps via implicit solve; amplifies only as
  V-follower).
- D (Laplacian): REJECTED (1%, E-removing).
- E (B280-btp): REJECTED (flat, <0.1%).
- F (B280-bcl): CONFIRMED seed-growth engine (100% of B280 injection,
  H2 growth).
- G (multi-term accumulation): PARTIAL (B200 removes / B280-bcl adds;
  net needs both + B210).
- H (multi-term gain): CONFIRMED for growing terms (TW/Cor/bcl H2;
  DPX H1 background).
- OVERALL: refined E+F — phase-1 = B280-bcl injection (H2) against
  B200-Coriolis local damping, DPX kick-start, B210 global damping;
  N1 never runs away (single pass). B200-global +2e7 term attribution:
  OPEN (needs maxU-cell targeting). N=1 term-level: not run (ONLY-N24
  constraint); operator-level N1 vs N24 from 11.5C.5 stands.

## 6. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. New precision: Coriolis is the largest B200 term yet a damper —
   "dominant term" ≠ "driver". B280-bcl is the seed-growth conduit;
   DPX/DPY only kick-starts from rest. Any future intervention must be
   E-weighted, not magnitude-weighted.
3. Next (diagnostic-only, proposed): maxU-cell term targeting (find
   B200's +2e7 injection site); B200-increment TW/DPX/Cor/Lap split
   already available via this module — rerun with cell list from
   day-1 maxU map.
4. Artifacts: run `stage11.5C6R_AprN24b` (killed d8); 6 term CSVs +
   trace; first (contaminated) attempt documented §0, discarded.
5. Files: unit-number fix in `src/stage115c6_terms.f90` (171–176; NO
   physics lines); this doc (NEW); INDEX 11.5C.6R row.
   Verification: Jan OFF rerun on final binary (30 d / 32 files)
   md5 vs `stage11.5C_janOFF`; full fpm battery (see commit).
