# Numerical Scheme Inventory — authoritative (Stage 11.3C forensic audit)

Frozen 2026-09-29. Method: read ACTUAL Fortran code, not comments. Where code
and comments disagree, CODE wins (flagged HISTORICAL NOTE). No scheme was
changed in this audit.

## Summary table

| Block | File | PDE | Spatial | Temporal | Stability constraint |
|---|---|---|---|---|---|
| `advt`/`advs` horizontal | advection_3d_t/s.f90 | ∂T/∂t+u·∇T=0 | explicit 1st-order upwind + Zalesak FCT corrector | explicit | Cx≤~1 (measured max 1.06 stable via FCT) |
| `advt`/`advs` vertical | advection_3d_t.f90:150-165, advection_3d_s.f90:128-139 | ∂T/∂t+w·∂T/∂z=0 | explicit 1st-order upwind | explicit | Cz≤~1 (measured max 4.63 stable via FCT-Z) |
| `adv2d` (ice) | advection_2d.f90 | ∂A/∂t+u·∇A=0 | upwind + FCT | explicit | ice CFL (velocities ~0) |
| `advsh` (barotropic) | barotropic_dynamics.f90:61-384 | momentum advection | Lax–Richtmyer predictor; FCT DISABLED (apx2/apy2=0, CDY×0 — intentional, do not "fix") | explicit | c10=dt1/dx |
| Block 200 momentum | main.f90:986-1072 | 3D U/V with Coriolis+baroclinic+DPX+Laplacian | centered/face-averaged explicit forcing | semi-implicit Coriolis (analytic 2×2: asa1=f·dt/2, asa=1+asa1²) + explicit rest | f·DT≤~0.5 (measured 0.52) |
| Block 210 viscosity | main.f90:1105-1242 | ∂U/∂t=∂_z(ν∂_zU) | centered 2nd-order | IMPLICIT (genuine Thomas forward/backward sweep, uca/unu/vca/vnu) | unconditional (pivots negative by construction, 10.22) |
| `shal()` barotropic | shallow_water.f90 | eta + U/V shallow water | centered | explicit subcycled (mm3=30) | Cwave≈0.66 (measured) |
| W continuity | main.f90:790+ | ∂W/∂z=−∇·U | centered differences | explicit diagnostic | — |
| Ice dynamics | main.f90:656-749 | ice momentum + VP rheology (stress/deform) | centered + hht-guard | explicit + semi-implicit friction 2×2 (aa=a1²+b1²≥1, structurally safe) | hht≥0.01 guard |
| `heat()`/`conv_adj()` | thermodynamics.f90 | energy balance + CA | column physics | explicit per-step (Newton local iter; CA 1000-iter guard) | — |

## HISTORICAL NOTE (false documentation, code unchanged)

`advection_3d_t.f90:20,83,139-144` and `advection_3d_s.f90:13,121` claim an
"implicit Thomas" vertical solve. The code performs a single explicit upwind
sweep (`cd = tt − dt·flux(t2_old)`); no tridiagonal system is assembled, no
forward/backward sweep exists. Vertical T/S advection is EXPLICIT and
CFL-limited (measured Cz max 4.63 over 29 d April baseline without blowup —
FCT-Z absorbs overshoot). Likewise `main.f90` B200 comments mix "implicit"
and "explicit" labels for Coriolis (line ~1053 vs ~1058); the code is
semi-implicit Coriolis + explicit forcing. Comments left untouched (audit-only
stage); this inventory is the authoritative reference.

## Timestep sensitivity (11.3C matrix, April 30 d, `STAGE113_DT/DT1`)

| Exp | DT/DT1 | Days | FIRST_INVALID | Cx/Cy/Cz max | EUU end | CA maxiter | ro bounds |
|---|---|---|---|---|---|---|---|
| A | 3600/120 | 29 | none | 1.06/0.99/4.63 | 2.087e15 | 1001 (saturated) | [−0.00096, 0.00822] |
| B | 1800/120 | 29 | none | 0.13/0.07/0.42 | 2.124e15 | 1001 (saturated) | same |
| C | 900/120 | 29 | none | 0.07/0.04/0.08 | 2.145e15 | 1001 (saturated) | same |
| D | 3600/60 | 29 | none | =A (baroclinic cols) | 2.089e15 | 1001 (saturated) | same |
| E | 3600/30 | 29 | none | =A (baroclinic cols) | 2.089e15 | 1001 (saturated) | same |

Envelope: stable for DT∈[900,3600], DT1∈[30,120]; CA guard saturation is
DT-independent (float32-quantization floor, T-01 family — not a timestep
issue). Caveats: `mm2=12` fixed ⇒ simulated hours/day scale with DT
(documented, not calendar-equivalent runs); `s112` barotropic-CFL probe uses
hardcoded 120 s (`main.f90:1245`), so the Cwave column does not reflect DT1
changes (instrumentation note for 11.3C-follow-up, not a physics issue).
