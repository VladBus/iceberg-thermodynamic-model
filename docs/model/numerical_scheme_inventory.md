# Numerical Scheme Inventory — authoritative (Stage 11.3C forensic audit)

Frozen 2026-09-29. Method: read ACTUAL Fortran code, not comments. Where code
and comments disagree, CODE wins (flagged HISTORICAL NOTE). No scheme was
changed in this audit.

> **Scope note (2026-11-05):** Sections 1–3 describe the **Stage 11 frozen**
> prognostic ocean and its timestep audit. Stage 12 (D-51) drives the iceberg
> from **GLORYS12 + ERA5 reanalysis** (offline/prescribed) and does not reuse
> this prognostic ocean. The Stage 12 voxel, reanalysis, and wave schemes are
> listed in the final section; they are implemented and gated separately from
> the Stage 11 ocean reference.

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

## Stage 12 — voxel iceberg, reanalysis forcing, and wave schemes

These schemes are implemented in the Stage 12 code path and are **gated**; they
do not change the Stage 11 ocean reference. Reports are in
`docs/wiki/stages/stage12/`.

| Block | Implementation | Method | Default / switch | Verification | Limitations |
| --- | --- | --- | --- | --- | --- |
| Voxel heat conduction | `src/voxel_thermal_solver.f90` | Finite-volume conduction on state-scaled voxels; explicit path retained | `VOXEL_THERMAL_SCHEME=explicit` | Stage 12.3/12.4 synthetic tests | No cavity exchange; grid-rotation neglected |
| Crank–Nicolson core | `src/voxel_thermal_solver.f90` | θ-scheme with `θ=ICEBERG_THETA=0.5`; symmetric 7-diagonal system solved by PCG+Jacobi (`ICEBERG_CG_TOL=1e-10`) | Default `cn` | A‑T1…A‑T9; temporal order ~2 (ratio 3.996), energy drift ~1.6e−10 | BC linearisation and melt-cap choices are model assumptions |
| Rannacher smoothing | `src/voxel_thermal_solver.f90` | Two backward-Euler steps after any geometry change, then return to CN | Automatic after removal | A‑T8 | Added for stability, not calibrated |
| Stefan / three-equation boundary | `src/voxel_thermal_solver.f90` | Per-face `F(m)` bisection; `S_B(m)`, `T_B=Tf(S_B,P_f)`; `m≥0`, no accretion | Voxel submerged faces | B‑T1…B‑T8; mass budget closes to 8.96e−16 | K_T/K_S uncalibrated; no accretion; per-face assumptions |
| Free-convection floor | `src/voxel_thermal_solver.f90` | `gamma_T=max(K_T u_rel, 1e-5)`, `gamma_S=max(K_S u_rel, 1e-6)` | `VOXEL_ENABLED=ON` voxel path | Stage 12.7c 3-case rerun | Large/low-ΔT under-melt remains; full 190 not rerun |
| Voxel geometry / drift | `src/voxel_iceberg.f90`, `src/iceberg_dynamics.f90` | Voxel mass, Archimedes draft, projected submerged area `A_sub_proj`, exposed sail area `A_sail`; `GM` diagnostic | `VOXEL_ENABLED=ON` | Stage 12.5 tests T1–T6 | Uniform flow direction; no capsize; concave silhouettes approximated |
| Wave erosion | `src/wave_forcing.f90` | Bigg/NEMO rate `m_wave=max((1/12)(T_w+2)S_s[1+cos(pi c^3)],0)/day`; Douglas `Hs→S_s` | `ICEBERG_WAVE_EROSION` default OFF | Stage 12.6b formula/switch tests | No real WAM validation; `Tp`/direction unused; no sea-ice drag/tides |
| Optional Stokes drift | `src/wave_forcing.f90`, `src/iceberg_dynamics.f90` | Adds Stokes velocity to water drag | `ICEBERG_STOKES_DRIFT` default OFF | Stage 12.6b switch tests | Optional/offline; not validated against drifter data |
| Reanalysis ocean reader | `src/reanalysis_reader.f90`, `src/ocean_provider.f90` | Packed-int16 decode; bilinear lat/lon; linear depth and time; NaN=land | `OCEAN_SOURCE=reanalysis` (default `model`) | Stage 12.2 tests 9/9 + 4/4 + 4/4 | Coastal currents coarse; no two-way coupling |
| ERA5 atmosphere | `src/netcdf_input.f90`, `src/wind_forcing.f90` | Bilinear spatial interpolation; nearest-time selection; D32 edge clamp | Existing Stage 11 path | ERA5 contract tests | 3-hourly step forcing; no temporal interpolation |
| Lat/lon drift | `src/iceberg.f90`, `src/iceberg_run.f90` | `dlat=v·dt/R`, `dlon=u·dt/(R cosφ)`; first-order update | `OCEAN_SOURCE=reanalysis` | Stage 12.6a tests | First-order; grid rotation neglected |
