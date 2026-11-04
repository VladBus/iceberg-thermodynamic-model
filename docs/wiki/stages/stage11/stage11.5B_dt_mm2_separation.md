# Stage 11.5B — DT × MM2 Separation Experiment (2D sensitivity matrix)

Frozen 2026-09-30. Code (measurement only): `STAGE113_MM2` override in
`app/main.f90` (decoupled ice cadence; precedence MM2-set → as-is, else
86400/DT, else legacy 12; actual s/day printed). No physics/scheme change.
Runs `stage11.5B_AprA–I` (April, DIAG+FIRST_INVALID, logs saved).
Method note: the 86400 s/day constraint is deliberately NOT enforced —
enforcement would collapse the 2D design space; printed s/day keeps
semantics auditable. (Implementation note: first attempt placed the MM2 read
before legacy `mm2 = 12`, which clobbered it — all-mm2=12 void batch
discarded; fixed by reading after legacy assignments, verified via prints.)

## 1. Matrix (all 29 d, EXIT 0, no FIRST-INVALID, 21–70 s each)

| Case | DT | MM2 | s/day | EUU end | CA nmix (maxiter) | ro bounds | iceArea/Vol |
|---|---|---|---|---|---|---|---|
| A | 3600 | 12 | 43200 | 2.087e15 | 9,070,170 (1001) | [−0.00087, 0.00821] | 1082 / 358 |
| B | 3600 | 24 | 86400 | 2.103e15 | 8,876,752 (1001) | same max | 1079 / 446 |
| C | 3600 | 48 | 172800 | 2.093e15 | 8,495,206 (1001) | min −0.01500 | 1567 / 674 |
| D | 1800 | 12 | 21600 | 2.124e15 | 6,621,240 (1001) | [−0.00089, 0.00821] | 788 / 179 |
| E | 1800 | 24 | 43200 | 2.169e15 | 6,651,244 (1001) | same | 714 / 235 |
| F | 1800 | 48 | 86400 | 2.183e15 | 6,564,309 (1001) | same | 688 / 279 |
| G | 900 | 12 | 10800 | 2.145e15 | 4,915,800 (1001) | [−0.00094, 0.00821] | 529 / 88 |
| H | 900 | 24 | 21600 | 2.194e15 | 4,915,998 (1001) | same | 478 / 126 |
| I | 900 | 48 | 43200 | 2.222e15 | 4,849,961 (1001) | same | 415 / 166 |

CFL maxima depend ONLY on DT (Cx 1.06/0.13/0.07, Cz 4.5/0.42/0.08 per row;
identical across MM2 — ocean pass untouched by ice cadence). CA saturated
(1001) in all 9 (DT/MM2-independent floor). ro max identical everywhere.

## 2. DT sensitivity (fixed MM2)

EUU +1.8/+1.0% (A→D→G), +3.1/+0.6% (B→E→F), +2.3/+1.3% (C→H→I) per DT
halving; nmix −27%/−26% per halving; CFL strictly improves. DT drives the
OCEAN response monotonically.

## 3. MM2 sensitivity (fixed DT)

Ocean EUU: +0.7/−0.5% (A→B→C), +2.1/+0.6% (D→E→F), +2.3/+1.3% (G→H→I) —
weak at DT=3600, growing at finer DT (COUPLED: ice-state feedback via
txic/A into B210 matters more when ocean dt is finer). Ice VOLUME grows
with MM2 at all DT (+25–90% per doubling — trivially: more ice-integration
time); ice AREA non-monotonic across DT. CA nmix ±few %.

## 4. Convergence / cost

No plateau in either axis (EUU keeps rising) → convergence NOT demonstrated;
response stable + bounded everywhere. Cost scales with mm2 (ice loop:
A32/B31/C70 s), NOT with DT (ocean once/day) — DT refinement is nearly
free, MM2 doubling ~2×. Cost-effectiveness favors DT refinement; MM2
increases buy mostly ice-time, not accuracy.

## 5. Interpretation (TASK 4 answers)

- DT sensitivity >> MM2 sensitivity for OCEAN state; MM2 dominates ICE
  state (via total integration time, partly trivial).
- Effects are COUPLED (MM2 leverage grows as DT falls), not independent —
  but separable in attribution above.
- Current architecture acceptable for process studies at reference cadence;
  NOT converged; trajectory validation still outstanding (11.5A finding).
- EOS-80/NetCDF/voxel designs unaffected (orthogonal choices).

## 6. Recommendation for 11.5B.1

Proceed to 11.5C prototype (ocean pass inside `iii` behind env flag):
the decisive experiment is substepped-vs-daily ocean at FIXED ice cadence
(DT=3600, MM2=24) — the one comparison this matrix cannot make. Keep
FIRST_INVALID + battery + EUU/ro/CA acceptance from this matrix as the
reference envelope.
