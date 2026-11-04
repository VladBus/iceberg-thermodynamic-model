# Stage 11.3C.1 — Numerical Stability Semantics Correction & Vertical CFL Audit

Frozen 2026-09-30. Code changes (measurement/diagnostic ONLY, no physics):
`STAGE113` env block in `app/main.f90` (mm2/mm3 scaling + init print),
`s112_cfl_dist` + percentile helper + CSV in `src/stage112_cfl_diagnostics.f90`,
one call site. Runs `stage11.3C1_AprA–E` (April, env `STAGE113_DT/DT1`).

## 1. Timestep semantics fix

`mm2`/`mm3` now scale ONLY when the matrix override is active
(`STAGE113_DT`/`DT1` set): `mm2 = 86400/DT` (24/48/96), `mm3 = DT/DT1`
(30/60/120), with init print (`STAGE113: DT=… mm2=… s/day=…`). Default path
(no env) keeps legacy `mm2=12/mm3=30` bit-identically (Jan OFF 32/32 md5-MATCH
vs D32). Legacy flaw corrected: fixed `mm2=12` simulated 12 h (DT=3600),
6 h (DT=1800), 3 h (DT=900) per "day" — old matrix compared different
physical times.

## 2. Loop-architecture discovery (reframes D24–D33 substep language)

The `iii`-loop (`main.f90:624`, closed line 909) covers ONLY the ice block
(heat/redis/dynamics/adv2d/redis). W/advs/advt/CA/Block200/Block210/shal run
ONCE PER DAY with stale `iii = mm2+1` (Fortran loop exit value). Hence D24's
"Day-1 iii=13" and B3.3 "III=25" were post-loop stale labels, not substeps;
heat/dynamics `iii` references (D27–D31) remain genuine (inside the loop).
Consequence: DT scales the once-daily ocean pass; mm2 scales ice substeps
(ice-dynamics microsteps/day = mm2·mm3 = 86400/DT1, DT-independent). True
ocean timestep-convergence testing would require ocean substepping (absent by
architecture — documented, not changed). `s112_cfl_dist` therefore records
daily aggregates (`iii=0` label).

## 3. CFL distribution (daily, wet cells; new `cfl_distribution.csv`)

April baseline A, 29 d: Cx p50/p99/max = 4.3e-3/4.4e-2/1.06 (frac>1: 2.7e-6);
Cz p50/p99/max = 4.4e-3/7.6e-2/4.50 (frac>1: 4.5e-4, frac>0.5: 1.7e-3).
Cz>1 is a thin-layer artifact: persistent max location (23,17,7) with
physical w = −0.029 cm/s (small dz(k=7) inflates the ratio); bulk P99 ≪ 1.
Exps B/C: strictly <1 everywhere. D/E: identical to A (DT1-independent).
FCT-Z absorbs the 0.045% overshoot cells — stable, no blowup.

## 4. Vertical advection verdict: EXPLICIT (structural proof)

`advection_3d_t.f90:150-165` / `advection_3d_s.f90:128-139`: single forward
sweep `cd(k) = tt(k) − dt·[upwind flux divergence over t2_old]`; all RHS reads
are old-state (`t2`/`s2`), writes go to `cd` (new). No tridiagonal system is
assembled, no forward/backward pass exists — mathematically incapable of being
implicit. Code comments claiming "implicit Thomas" (advt:20/83/139-144,
advs:13/121) are FALSE documentation (code untouched, audit-only).
Dedicated single-step unit test deferred as redundant (structure decisive).

## 5. Corrected matrix (April, physical days, all EXIT 0, no FIRST-INVALID)

| Exp | DT/DT1/mm2/mm3 | Days | EUU end | CA maxiter | ro bounds |
|---|---|---|---|---|---|
| A | 3600/120/24/30 | 29 | 2.103e15 | 1001 (saturated) | [−0.00096, 0.00822] |
| B | 1800/120/48/30 | 29 | 2.183e15 | 1001 (saturated) | same |
| C | 900/120/96/30 | 29 | 2.239e15 | 1001 (saturated) | same |
| D | 3600/60/24/60 | 29 | 2.10319e15 | 1001 (saturated) | same |
| E | 3600/30/24/120 | 29 | 2.10308e15 | 1001 (saturated) | same |

Convergence: EUU rises monotonically as DT falls (+3.8%, +2.6% — reduced
numerical damping, no oscillation/divergence); D/E ≡ A to 0.02% (barotropic
already converged; DT1 irrelevant). CA saturation is DT-independent
(float32-quantization floor, T-01). Caveat: s112 Cwave probe hardcodes 120 s
— blind to DT1 (instrumentation note).
Safe DT range: [900, 3600] all stable; Cz>1 confined, FCT-absorbed — not a
problem. Envelope for EOS-80 experiments: use A as reference; B/C available
for damping-sensitivity bracketing.
