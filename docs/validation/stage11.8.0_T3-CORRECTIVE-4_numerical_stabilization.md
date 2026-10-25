# Stage 11.8.0 T3-CORRECTIVE-4 — Numerical Stabilization (dt + Laplacian dissipation)

**Status:** COMPLETE — **T3b PASS under the revised bounded-adjustment criterion**
**Date:** 2026-10-25
**Base:** `35bf3b7` (T3-CORRECTIVE-3)
**Scope:** numerical stabilization only. No grid change, no physics-formula
change, no EOS/scheduler change. `EOS_MODE=LEGACY` remains default.

---

## 1. Why this stage

T3-CORRECTIVE-2/3 established the fundamental limitation:

- grid spacing **Δx = 13.89 km**;
- first baroclinic Rossby radius from EN4 **R_d ≈ 2.36 km**;
- ratio **R_d/Δx ≈ 0.17** — the grid is ~6× coarser than the deformation
  radius, so baroclinic eddies cannot be resolved. The unresolved instability
  is numerical dispersion, not a single removable formula bug.

The T3-CORRECTIVE-3 fixes E1–E3 were implemented but did not stabilize the
30-day rest run (Umax 3.902 m/s, KE30/KE15 52.98). This stage uses the
allowed numerical levers: **smaller Δt** and **extra Laplacian dissipation**.

## 2. Phase 1 — Δt reduction

T3b setup: zero forcing, corrected EN4, E1+E2+E3 ON, LEGACY, 30 days.

| run | max \|U\| (m/s) | max \|V\| (m/s) | KE day 15 (J) | KE day 30 (J) | KE30/KE15 |
|---|---|---|---|---|---|
| Δt=3600 (T3-CORRECTIVE-3) | 3.902 | 5.410 | 1.641e14 | 8.696e15 | **52.98** |
| **Δt=1800** | **0.517** | **0.435** | **1.002e14** | **1.114e14** | **1.112** |
| **Δt=900** | **0.278** | **0.214** | **7.752e13** | **9.887e13** | **1.275** |

- Δt=1800 already brings the ratio from 52.98 to **1.112** (<5); max |U| is
  0.517, marginally above the old 0.5 m/s limit.
- Δt=900 also passes the ratio and the max-|U| limit.
- Outputs: `data/validation/t3c4_dt1800_results.json`,
  `t3c4_dt900_results.json`.

## 3. Phase 2 — Laplacian dissipation

New switches (default OFF): `STAGE118_LAPLACIAN_VISC` and `STAGE118_AH`
(units m²/s, default 10000). The extra term is added to the existing Block-200
Laplacian:

```
c3w = c3 + Ah_extra/dx²
auu = u + (f dt/2)v + dt·(-c1·SUM - DPX + c3w·LAPU)
avv = v - (f dt/2)u + dt·(-c1·SUM1 - DPY + c3w·LAPV)
```

Ah is in m²/s, converted to CGS (`×1e4`) before `dx²` (cm²). With Δt=1800 the
explicit 2-D stability factor `4·Ah·Δt/Δx²` is 0.37 for Ah=10000 and 0.75 for
Ah=20000; Ah=50000 would give 1.86 (>1) and is not used at Δt=1800.

| Ah (m²/s) | max \|U\| | max \|V\| | KE15 (J) | KE30 (J) | KE30/KE15 |
|---|---|---|---|---|---|
| 5000 | 0.188 | 0.125 | 5.155e13 | 3.144e13 | 0.610 |
| **10000 (chosen)** | **0.147** | **0.103** | **3.899e13** | **2.216e13** | **0.568** |
| 20000 | 0.114 | 0.079 | 2.862e13 | 1.599e13 | 0.559 |

All three pass; Ah=10000 is the requested starting value and retains more
large-scale signal than 20000. Output: `data/validation/t3c4_ah_results.json`.

## 4. Phase 3 — sponge layers

Not needed. The chosen Δt+Ah configuration already passes; no sponge was
activated. The pre-existing `STAGE118_BOUNDARY_SPONGE` remains OFF (tested in
T3-CORRECTIVE-3 and only masked the boundary peak).

## 5. Final T3b metrics (chosen configuration PASS)

**Configuration:** Δt=1800 s, Ah=10000 m²/s, no sponge; E1+E2+E3 ON;
zero forcing; corrected EN4; LEGACY.

| Metric | Value |
|---|---|
| max \|U\| | **0.147 m/s** |
| max \|V\| | **0.103 m/s** |
| max \|W\| | 9.25e-4 m/s |
| KE day 0 | 0 J |
| KE day 15 | **3.899e13 J** |
| KE day 30 | **2.216e13 J** |
| **KE30/KE15** | **0.568** |
| Acceptance (revised: <5.0, max \|U\|<0.5) | **PASS** |
| Classification | bounded adjustment (KE decays after day 15) |

`data/validation/t3c4_final_results.json`; output directory
`data/runs/t3c4_dt1800_ah10000`.

## 6. Acceptance-criteria revision

T3b is now:
- **T3a pure rest:** homogeneous T/S, real bathymetry; max |U| < 1e-6 m/s,
  no PGF.
- **T3b adaptation:** real EN4 T/S, zero forcing; **max |U| < 0.5 m/s and
  KE30/KE15 < 5.0** (was <2.0); no exponential growth.

Rationale: a 13.89 km grid cannot resolve 2.36 km baroclinic eddies; bounded
adjustment with weak decay is the realistic target, not a perfect rest state.

## 7. Fundamental limitation (documented)

- Grid: 13.89 km; first baroclinic Rossby radius: ~2.36 km; ratio ~0.17.
- The model cannot resolve baroclinic eddies; some dissipation and/or Δt
  reduction is **necessary**, not optional.
- The chosen configuration is a **compromise**: it damps physical eddies as
  well as numerical noise (KE decays after day 15); it is not a “correct”
  eddy-resolving solution.
- Users must not interpret the stabilized rest state as resolved baroclinic
  dynamics. A future eddy-resolving configuration would require a finer grid.

## 8. Regression and safety

| Check | Result |
|---|---|
| Full `fpm test` | **60/60**, exit 0 |
| Strict build | exit 0 |
| Default legacy bit-identity | 1-day rest md5 identical to baseline |
| ERA5 contract / snowfall | 120/120 / CONFIRMED_1H |
| EN4 T0 / T3-PREP / mask | CLEAN / CLEAN / CLEAN |
| T1/T2 suites | unchanged (T-23/H-2 still open) |
| `git diff --check` | clean |

All new switches are OFF by default; `EOS_MODE=LEGACY` remains default. No
grid/EOS/scheduler change; T-23/H-2 untouched; T4–T6 not started; no
`data/runs/` data deleted.

## 9. T4 decision

**Numerical stabilization gate: PASS.** **T4 implementation: NO-GO**, because
the explicitly excluded T4 prerequisites remain open: **H-2 (ERA5 wind not
rotated to the rotated grid; median 50.2°)** and **T-23 (ERA5 longitude
wrap)**. T4 may start only after those prerequisites are corrected; the
numerical T3b blocker is cleared.
