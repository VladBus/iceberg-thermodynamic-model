# Stage 11.8.0 T3-CORRECTIVE-2 — T-03 Root-Cause Diagnosis

**Status:** COMPLETE — **root cause identified: CA density-writeback → baroclinic
pressure-gradient feedback**, seeded by the unbalanced zero-velocity rest
initialization, localised by the reflective SW boundary, and numerically
amplified at Δt = 3600 s.
**Date:** 2026-10-25
**Base:** `b843dc8` (T3-CORRECTIVE)
**Scope:** diagnostic only. No physics, EOS, scheduler or numerical operator
was changed; `EOS_MODE=LEGACY` remains the default.

---

## 0. Executive result

The exponential rest-state growth is **not** a pressure-gradient stencil error,
not a boundary-only artefact, and not primarily an EOS-precision effect.

**Controlled experiments isolate the necessary ingredient:**

| 30-day rest run (LEGACY) | Umax day 30 (m/s) | KE day 30 (J) | Classification |
|---|---|---|---|
| baseline (CA writes RO) | **3.924** | **8.09e15** | UNSTABLE |
| `STAGE1022_FREEZE_TS=true` (no T/S advection + no CA) | **0.205** | **6.52e13** | bounded |
| `STAGE1022_FREEZE_RO=true` (CA mixes T/S but **does not write RO**) | **0.205** | **6.52e13** | bounded |
| `STAGE1022_FREEZE_THERMAL_WIND=true` (baroclinic PGF off) | **0.000** | 0 | at rest |
| `STAGE113_DT=1800` (half time step) | **0.528** | **1.18e14** | bounded |
| EOS-80 baseline | **4.713** | **6.84e15** | UNSTABLE |
| EOS-80 `FREEZE_RO` | **0.201** | **6.12e13** | bounded |

`FREEZE_RO` leaves the same CA mixing (4.38e6 mixings on day 30, versus 5.40e6
in the baseline) and the same initial imbalance, but removes only the
**convective-adjustment density writeback**. The flow then stays bounded at
~0.2 m/s. EOS-80 converges (guard 0, 24,793 mixings/day) yet behaves the same
way, so **CA convergence does not exonerate the density writeback**.

**Root cause chain:**

1. EN4 T/S are not balanced with `u=v=0`; the thermal-wind state has
   **0.283 m/s** currents and **86 m²/s** depth-integrated transport. The T3
   rest gate zeros velocities and transports, leaving a baroclinic PGF but no
   balanced flow.
2. The initial adjustment produces ~0.08–0.28 m/s currents and advects T/S.
3. Convective adjustment mixes columns and **writes the mixed density back to
   `RO`**; `RO` is otherwise not prognostic (recomputed only at init/final), so
   this writeback is the only density evolution in the rest run.
4. The CA-induced `RO` anomalies (up to **8.26 kg/m³**) generate a growing
   baroclinic PGF. The **CA-induced share of PGF work rises from 7.9 % (day 1)
   to 99.6 % (day 30)**.
5. The growing signal is trapped/localised at the **south-western 600-m
   boundary/topography** (max speed 3 cells from the boundary; 33 % of KE within
   5 cells, 64 % within 10; 71 % in the SW quadrant).
6. At Δt = 3600 s the CA→RO impulse is numerically amplified; halving the step
   to 1800 s bounds the growth (0.53 m/s, 1.2e14 J), and 7200 s violates
   stability (FPE). This is an operator-splitting/numerical amplifier, not a
   converged physical instability.

**T4 remains NO-GO.** **T3-CORRECTIVE-3 (fix) is GO**, but it requires the
D-33 physics decision because the fix must touch the CA/density coupling.

---

## 1. Phase 0 — Spatial diagnosis (where/when/what)

Baseline: `data/runs/t3c_legacy_canonical` (30 days, zero forcing, corrected
EN4, `EOS_MODE=LEGACY`). KE from the daily NetCDF (T-31: the printed `EUU` is
hardcoded 0 and was not used).

| day | max speed (m/s) | location (k, y, x) | lat / lon | KE (J) | KE in 5-cell boundary band | SW quadrant |
|---|---|---|---|---|---|---|
| 1 | 0.082 | k=18 (bottom), y=19, x=6 | 69.52 N, 14.83 E | 1.10e13 | 19.2 % | 78 % |
| 2 | 0.155 | k=1, y=26, x=34 | 72.55 N, 20.59 E | 3.26e13 | 16.4 % | 76 % |
| 5 | 0.277 | k=1, y=26, x=34 | 72.55 N, 20.59 E | 1.06e14 | 15.2 % | 75 % |
| 10 | 0.263 | k=17, y=19, x=5 | 69.40 N, 14.74 E | 6.50e13 | 14.7 % | 68 % |
| 15 | 0.834 | k=17, y=19, x=5 | 69.40 N, 14.74 E | 1.69e14 | 19.7 % | 68 % |
| 20 | 2.267 | k=1, y=19, x=5 | 69.40 N, 14.74 E | 7.06e14 | 27.1 % | 70 % |
| 25 | 4.307 | k=1, y=19, x=5 | 69.40 N, 14.74 E | 2.52e15 | 33.4 % | 72 % |
| 30 | **6.715** | **k=1, y=18, x=4** | **69.31 N, 14.32 E** | **8.09e15** | **33.1 %** | **71 %** |

- **When:** adjustment on days 1–5 (bottom → surface, 0.08 → 0.28 m/s), a
  reorganisation/dip by day 10, then exponential growth after day 15
  (KE day 15 → 30 = **×47.8**, e-folding ≈ 3.8–4.6 days).
- **Where:** the final hot spot is the **south-western deep basin** (600 m,
  69.3 N, 14.3 E), **3 cells from the boundary**. The top 1 % speed cells sit
  in water of mean depth **362 m** versus **231 m** for the domain (slope
  **6.8e-3** versus **2.2e-3**, 3.1×).
- **Depth:** at day 30, KE is 2.8 % at k=1, 15.2 % at k=17, 11.5 % at k=16 and
  8.2 % at k=9; bottom k=18 holds only 1.1 %. Wmax is only 0.043 m/s — the
  growth is horizontal shear, not vertical motion.
- **T/S drift:** day-30 RMS drift 0.337 °C / 0.432 PSU (surface S drift
  0.56 PSU, deep T drift 0.48 °C) — T/S evolve while the flow grows.
- **Instability type:** **baroclinic/shear, CA-driven, boundary-amplified,
  grid-scale**. Richardson number falls from 0.0051 (day 1) to **1.27e-5**
  (day 30); the fraction of velocity variance at high horizontal wavenumbers is
  **44 % (surface) / 36 % (deep)** — the signal is not a smooth large-scale
  mode. The first baroclinic Rossby radius from the mean EN4 stratification is
  **2.36 km**, only **0.17 × the 13.89 km grid**.

Outputs: `docs/wiki/stages/stage11/evidence/t3c2_spatial_diagnosis.json`,
`docs/wiki/stages/stage11/figures/t3c2/*.png`.

## 2. Phase 1 — Geostrophic balance check

Reproduced the model's thermal-wind stencil (`RO` in g/cm³, `c8=0.25/dx`,
reference level 600 m = k18, U/V zero at the reference):

| quantity | value |
|---|---|
| initial velocity in the rest run | **0.000 m/s** |
| thermal-wind speed from initial T/S | **0.283 m/s** (model log 0.2596; 9 % diagnostic difference from the `KK1` edge treatment) |
| max U / V | 0.283 / 0.178 m/s |
| max depth-integrated transport | **86.2 m²/s** (U), 46.0 m²/s (V) |
| max barotropic-equivalent speed | **0.144 m/s** (U), 0.077 m/s (V) |
| max initial baroclinic PGF acceleration | **4.23e-5 m/s²** |
| one-step velocity change if unopposed | **0.152 m/s** |
| one-day change if unopposed | **3.66 m/s** |

**Conclusion: the initial state is UNBALANCED** (0.283 m/s ≫ 0.01 m/s), and the
rest gate also removes the balanced barotropic transport (0.144 m/s). The
initial PGF is therefore a real seed. However, this alone does **not** explain
4–6 m/s: with `RO` frozen (`FREEZE_RO` or `FREEZE_TS`), the same initial
imbalance produces only a **bounded 0.20–0.28 m/s** adjustment. Pattern
correlation between the initial thermal-wind speed and the day-1 speed is 0.42;
by day 30 it is 0.03 — the later growth is no longer the initial adjustment.

## 3. Phase 2 — Pressure-gradient discretisation and density coupling

### Block 200 (3-D momentum)

For each wet U/V column, level k:

```
AUU = U1 + (f dt/2) V1 + dt (-C1·SUM  - DPX + C3·LAPU)
AVV = V1 - (f dt/2) U1 + dt (-C1·SUM1 - DPY + C3·LAPV)
SUM  = Σ_m [Δ_x RO(m) + Δ_x RO(m+1)] · c8 · dz(m)   (trapezoid)
SUM1 = Σ_m [Δ_y RO(m) + Δ_y RO(m+1)] · c8 · dz(m)
C1 = g/ρ0 = 981 (CGS), c8 = 0.25/dx, RO in g/cm³
```

- **Stencil:** 2×2 C-grid averaging, `Δ_x = RO(i-1,j)+RO(i,j)-RO(i-1,j-1)-RO(i,j-1)`
  and the corresponding `Δ_y`; `X↔j↔U`, `Y↔i↔V` (model convention).
- **Units:** CGS internally; `RO` is the EOS density anomaly, not the full
  density. The output `density_anomaly` is `ro × 1000` kg/m³ and masks dry
  cells with 0; the diagnostic therefore restricted the stencil to four wet
  neighbours and used `KK1 = min(kt1 of the 2×2 stencil)`, matching the model's
  U/V wet-level count.
- **Surface-layer double count:** Block 200 initialises `a` with level 1 and
  then uses `a1` = level 1 at k=1, so the first trapezoid is 2×level 1; the
  thermal-wind initialization uses level 1 + level 2. The difference is real
  but **negligible**: max |ΔPGF| = **6.31e-10 m/s²** = **1.49e-5** of the PGF
  (4.23e-5 m/s²). It is not the driver.
- **Dry-level/topographic stencil:** using `KK1` (the U/V wet-level count)
  removes any dry-neighbour/zero-density gradient; raw and bottom-filled PGF
  maxima are identical (4.2327e-5 m/s²). No topographic PGF bug was found.
- **No sign or Coriolis error:** the daily Coriolis work is ≤ 5.5e-7 W
  (numerically zero); the PGF/Coriolis signs are consistent with the thermal
  wind relation.

### Thermal-wind initialization (`src/thermal_wind_init.f90`)

- `reference_level` (default) uses **600 m (k=18)**, sets `u=v=0` at/below the
  reference, and sets **all velocities to zero for columns with `ki < 18`**.
- It does **not** initialise SSH `y2` in `reference_level` mode (only
  `dynamic_height` does); it does call `init_barotropic_transports()`, but the
  T3 rest gate immediately zeros `u/v/w/up/vp`.
- Consequently the rest state has a **baroclinic PGF with zero velocity and
  zero SSH/barotropic transport** — a deliberately unbalanced state.

### Key architectural finding: `RO` is not prognostic

`eos_diag()` is called at initialization and at the final write only (plus the
optional predictor-corrector). During the normal step, **`RO` is updated only
by the convective-adjustment writeback**; T/S advection and heat do not refresh
the density used by Block 200. This is why `FREEZE_TS` (no CA, no advection) and
`FREEZE_RO` (CA mixes T/S but does not write RO) give **identical bounded
velocities**: only the CA density writeback can change the pressure field.

## 4. Phase 3 — Energy budget

Daily KE budget (diagnostic; PGF is the Block-200 baroclinic term; horizontal
Laplacian work uses A_h=750 m²/s; vertical friction/advection/boundary fluxes
are not separable from the output):

| day | dKE/dt (W) | PGF work (W) | Coriolis (W) | Laplacian (W) | residual (W) | CA share of PGF work |
|---|---|---|---|---|---|---|
| 1 | 1.27e8 | 2.71e9 | 2.8e-9 | -2.01e8 | -2.38e9 | 7.9 % |
| 5 | 2.25e8 | 4.07e9 | 8.0e-10 | -1.75e9 | -2.10e9 | 13.5 % |
| 10 | -1.95e8 | -5.56e9 | 1.8e-8 | -1.23e9 | 6.60e9 | (CA positive 2.16e9) |
| 15 | 6.28e8 | 1.56e10 | -2.4e-8 | -4.01e9 | -1.09e10 | 73.8 % |
| 20 | 1.79e9 | 4.36e10 | 4.4e-7 | -1.62e10 | -2.56e10 | — |
| 25 | 6.66e9 | 1.60e11 | 2.0e-6 | -5.79e10 | -9.56e10 | — |
| 30 | 1.79e10 | 4.23e11 | 5.5e-7 | -1.69e11 | -2.37e11 | **99.6 %** |

- **Dominant source: PGF work**, positive and growing by three orders of
  magnitude. The CA-induced part of that work (PGF from `RO_baseline −
  RO_FREEZE_RO`) grows from 7.9 % to **99.6 %**.
- **Coriolis work is zero** to numerical precision → no Coriolis sign error.
- **Friction is negative** (Laplacian ≈ 40 % of PGF) → no friction sign error.
- The residual is large because vertical friction, advection, boundary fluxes
  and the non-conservative CA adjustment are not separable; the budget is a
  source attribution, not a closed energy balance.
- **Potential energy:** PE = −∫ρgz dV becomes **less negative by 6.4e19 J** from
  day 0 to day 30 (CA mixing raises PE), while KE rises by 8.1e15 J. The APE
  proxy also rises (8.68e20 → 9.90e20 J). This is not a closed baroclinic
  conversion: the non-conservative CA adjustment is redistributing/adding
  potential energy that the PGF then converts to KE.

## 5. Phase 4 — Boundary conditions

From `src/shallow_water.f90` / `src/thermal_wind_init.f90`:

- Three lateral edges have **η clamped every barotropic micro-step** to the
  tidal amplitudes (`y2(i,1)`, `y2(1,i)`, `y2(i,js)`). `GRM2` is absent, so the
  amplitudes are zero → **η = 0, no radiation condition**.
- Velocity boundaries are **no-gradient copies** (`apply_velocity_bc`); the
  interior loops run `i=2..is, j=2..js`; the bottom level is set to zero.
- The fourth edge is not assigned in the same block; the effective lateral
  boundary is reflective/clamped rather than open/radiating.

**Localisation:** the day-30 maximum is **3 cells** from the boundary; **33.1 %
of KE is within 5 cells** and **64.4 % within 10 cells**; **70.8 %** is in the
SW quadrant. The hot spot is a 600-m deep basin on a slope 3.1× the domain
mean. CA-induced `RO` variance is **22 %** within 5 cells on day 1 rising to
**27 %** on day 30; the correlation between speed and the CA-induced density
gradient rises from 0.06 to **0.62**.

**Interpretation:** the clamped/reflective SW boundary and the deep-basin
topography **trap and focus** the CA-generated signal; they are a strong
amplifier, but not the source: `FREEZE_RO` has the same boundaries and remains
bounded.

## 6. Phase 5 — Hypotheses, evidence, ranking

| # | Hypothesis | Evidence | Confidence | Required fix (if confirmed) |
|---|---|---|---|---|
| **H6** | **CA density writeback → baroclinic PGF feedback (new)** | `FREEZE_RO` (CA mixes T/S, no RO write) is bounded in LEGACY (0.205 m/s, 6.52e13 J) and EOS-80 (0.201 m/s, 6.12e13 J); baseline is unstable in both; CA-induced PGF work 7.9 → 99.6 %; CA-induced ΔRO 8.26 kg/m³ at the hot spot; correlation 0.62 | **HIGH** | CA/RO coupling: make RO consistent with T/S (prognostic/after advection), and/or test potential-density CA (T-25); requires D-33 |
| **H1** | Initial T/S unbalanced with u=v=0 → geostrophic adjustment | thermal wind 0.283 m/s vs 0; transport 0.144 m/s; day-1 0.082 m/s; geo/day-1 pattern correlation 0.42; fixed-RO run bounded at 0.20–0.28 m/s | **HIGH (seed) / LOW (growth)** | Rest test should start from a balanced state, or the test must not zero the balanced transports |
| **H5** | Time-splitting/CA cadence numerical amplification | dt=3600: 3.924 m/s; dt=1800: **0.528 m/s, 1.18e14 J (bounded)**; dt=7200: FPE; CA mixings/day similar (3.98e6 vs 5.40e6); high-wavenumber fraction 44 %/36 %; Ri → 1.27e-5 | **MEDIUM-HIGH (amplifier)** | Sub-cycle/limit CA density change; time-step convergence study; requires D-33 |
| **H4** | Boundary reflection amplifies internal waves | max 3 cells from boundary; 33 %/64 % KE in 5/10-cell bands; 71 % SW; clamped η, no radiation; CA ΔRO boundary variance 27 % | **MEDIUM (amplifier)** | Radiation/open boundary or sponge; separate approved stage |
| **H2** | Pressure-gradient discretisation error | surface double count 1.49e-5 of PGF; no dry-level gradient under `KK1`; Coriolis work 0; fixed-RO bounded | **LOW** | None required for T-03; clean up the k=1 trapezoid in a later numerics review |
| **H3** | Thermal-wind initialization inconsistent with dynamics | reference level 600 m; shallow columns zeroed; SSH/transports zeroed by the rest gate; initial imbalance confirmed | **LOW-MEDIUM (seed)** | Balanced rest initialization; T3-CORRECTIVE-3 input design |

**Ranking:** **H6 ≫ H1 (seed) ≳ H5 (numerical amplifier) > H4 (boundary
amplifier) ≫ H2 ≈ H3.** Root cause is narrowed to **H6 + H5**, with H1 as the
seed and H4 as the localiser.

### Revision of the T-25 inference from T3-CORRECTIVE

T3-CORRECTIVE concluded “T-25 is not the primary driver because EOS-80 CA
converges”. T3-CORRECTIVE-2 shows this inference was **too strong**:

- EOS-80 CA does converge (guard 0), but still writes density back to `RO` and
  still produces CA-induced ΔRO up to **7.82 kg/m³**, with the same PGF-work
  growth.
- Removing only the RO writeback (`FREEZE_RO`) is sufficient to bound the flow
  in **both** EOS modes.
- Therefore **the CA density writeback is necessary**; whether the underlying
  defect is T-25 (in-situ rather than potential density), the CA mixing
  algorithm, or the non-prognostic RO is the subject of T3-CORRECTIVE-3.
  T-25 remains **CRITICAL** and is the leading candidate, not exonerated.

## 7. GO/NO-GO

**T3-CORRECTIVE-3 (fix): GO** — diagnostic target is now specific:

1. Make the density used by Block 200 consistent with the evolving T/S
   (recompute `RO` after advection/heat/CA, or document and justify the
   non-prognostic design).
2. Test the **potential-density CA** criterion (T-25) and/or limit the CA
   density writeback; compare LEGACY/EOS-80.
3. Test **CA sub-cycling / time-step convergence** at Δt=1800 (already bounded)
   and a bounded CA density increment.
4. Keep the boundary amplification in scope (radiation/sponge), but do not
   attribute the root cause to the boundary.
5. Any of (1)–(3) is a physics/architecture change and must pass the **D-33
   gate**; no production physics change in this diagnostic stage.

**T4: NO-GO.** Rest acceptance is still unmet (|U|,|V| ≪ 0.01 m/s, no KE
growth, conservation < 1e-4). T-23 (wrap) and H-2 (wind rotation) also remain T4
prerequisites.

## 8. Regression and reproducibility

| Check | Result |
|---|---|
| Full `fpm test` | exit 0 — **60/60**, 0 failures |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=...`) | exit 0 |
| ERA5 / sea-ice / provenance | 120/120, 33/33, 28/28 |
| Ice coverage / sea-ice provenance | 16/16, 8/8 |
| Snowfall / EN4 T0 / T3-PREP / mask | CONFIRMED_12H / CLEAN / CLEAN / CLEAN (8/8) |
| ERA5 coverage / spatial / temporal / wrap | ISSUES (T-21/H-2 expected) / WARNING / PASS / RED_CONFIRMED (T-23) |
| T2 homogeneous/weak/conservation/compressibility | PASS / PASS / PASS / CRITICAL_CONFIRMED |
| Advection boundary | PASS |
| `git diff --check` | clean |

New diagnostic scripts:

- `python/analysis/stage11.8.0_T3_CORRECTIVE2_diagnosis.py` →
  `docs/wiki/stages/stage11/evidence/t3c2_spatial_diagnosis.json` + 7 figures.
- `python/analysis/stage11.8.0_T3_CORRECTIVE2_controls.py` →
  `docs/wiki/stages/stage11/evidence/t3c2_controls_analysis.json`.
- Supporting outputs: `t3c2_controls_30d.json`, `t3c2_freeze_results.json`,
  `t3c2_eos80_controls.json`, `t3c2_dt_sensitivity.json`.

## 9. Confirmations

- No physics formula, EOS, scheduler or numerical operator was changed;
  `EOS_MODE=LEGACY` remains the default.
- T-25, T-23 and H-2 were **not** fixed. T-25’s status is updated with the
  revised diagnosis.
- T4–T6 were not started.
- No `data/runs/` data was deleted; the diagnostic runs are additions only.
- Diagnostic env switches used (all pre-existing, default OFF):
  `STAGE118_T3_REST_MODE`, `STAGE1022_FREEZE_TS/_RO/_RO_DOWNSTREAM/_THERMAL_WIND`,
  `STAGE113_DT=1800/7200`.
