# Stage 10.4.2.1 — Independent Q_surface Output Validation

- **Classification: C** — Independent validation of the production Q_surface output.
  Production physics unchanged; one diagnostic-only API addition.
- **Date:** 2026-09-08
- **Scope:** direct verification of the _production_ `Q_surface = Q_nonlatent + Q_LH`
  value against `Q_nonlatent_independent + m_vapor_production · L_S`.
  Stage 10.4.2 validated downstream monotonicity; Stage 10.4.2.1 independently
  validates the actual production Q_surface output.

## Objective

Stage 10.4.2 reconstructed Q*surface from the \_downstream* melt rate
(`Q_surface = m_surface · ρ_ice · L_f`, or `q_net` fallback when not melting).
That is a single-route, post-melt reconstruction and does NOT prove the
production total-surface-flux calculation is correct.

Stage 10.4.2.1 obtains the production output **directly** (new diagnostic
`diag%q_surface`) and verifies, for each controlled case:

```
Q_surface_expected = Q_nonlatent_independent + Q_LH_expected
Q_LH_expected      = m_vapor_production · L_S
error              = Q_surface_production − Q_surface_expected
```

Independence rule: Q_nonlatent computed from a separate formula (LW_down + LW_up

- SH evaluated from the atmospheric inputs); Q_LH takes the production vapor mass
  flux diagnostic (`diag%m_vapor`, itself independently verified in Stage 10.4.2,
  check 10.4.2.10) times the fixed `L_S`. Q_surface is compared only at the end.

**NOT done** (Stage 10.4.2 limitation, now removed):
`Q_surface = m_surface · ρ_ice · L_f` single reconstruction, or deriving
Q_nonlatent by subtracting Q_LH from production Q_surface.

## Why production Q_surface was not previously retrievable

In `src/iceberg_thermodynamics.f90` (`compute_surface_melt`):

- `q_surface = q_nonlatent + q_lh` (line 560) was a **local variable**; never
  stored in diagnostics.
- `diag%q_net_surface` (line 254) = `q_net = q_surface − m_surface·ρ_ice·L_f/dt`
  (line 602). While melting, m*surface consumes all of Q_surface, so
  `q_net = 0` — the \_residual after melt*, NOT Q_surface.
- `diag%m_surface` is the melt-only mass flux `Q_melt/(ρ_ice·L_f)`.

Therefore a **diagnostic-only** production change was required and permitted:

1. `src/iceberg_types.f90` — added to `iceberg_diagnostics`:
   - `q_surface` = Q_nonlatent + Q_LH (total energy available at surface) [W/m²]
   - `q_lh` = m_vapor · L_S (latent heat flux) [W/m²]
2. `src/iceberg_thermodynamics.f90` — `compute_surface_melt` now assigns
   `diag%q_surface = q_surface` and `diag%q_lh = q_lh` next to the existing
   `diag%m_vapor`/`diag%t_surface`.

Numerics of melt/T_surface/physics untouched: the assignments merely expose the
exact values the melt and mass-budget physics were computed with.

## Controlled experiment

Identical to Stage 10.4.2 (polar night, SW ≡ 0, Q_nonlatent d2m-invariant):

- lat 90 (cos_zenith < 0 ⇒ no solar branch), `T_surface = 0` (melt branch),
  `t2m = 283.15 K`, `tcc = 0`, `msl = 101325 Pa`, `u10 = 10 m/s`, `v10 = 0`,
  zero-ocean profile, identical geometry (100×100×100), `dt = 3600 s`.
- Only `d2m` varies:
  - SUB = 263.15 K (dry air, sublimation)
  - ZERO = `d2m_zero ≈ 273.158 K` (e_sat_dew(Tetens) = e_sat_ice(Murphy-Koop);
    q_air ≈ q_sat_ice ⇒ zero latent)
  - DEP = 283.15 K (humid air, deposition)

## Numerical results (float32)

| Case | Q_nonlatent_indep [W/m²] | m_vapor_prod [kg/m²s] | Q_LH = m_vapor·L_S [W/m²] | Q_surface_expected [W/m²] | Q_surface PRODUCTION [W/m²] | **error** [W/m²] |
| ---- | ------------------------ | --------------------- | ------------------------- | ------------------------- | --------------------------- | ---------------- |
| SUB  | 149.742706               | −3.7177e−5            | −105.374290               | 44.368416                 | 44.368423                   | **+7.6e−6**      |
| ZERO | 149.742706               | −5.2e−11              | −1.48e−4                  | 149.742554                | 149.742554                  | **0.0**          |
| DEP  | 149.742706               | +7.1127e−5            | +201.645966               | 351.388672                | 351.388672                  | **0.0**          |

- Q_nonlatent identical (149.742706 W/m²) across all cases ⇒ control verified.
- Q_surface production matches `Q_nonlatent_independent + m_vapor_production·L_S`
  to **≤ 7.6e−6 W/m²** (float32 rounding only; 0.003% of 350).

## Test results (7 new checks → audit now 66 checks / 0 errors)

1. **10.4.2.1.1 Direct Q_surface identity** — production `diag%q_surface` equals
   `Q_nonlatent_ind + m_vapor_prod·L_S` for SUB, ZERO, DEP (tolerance 1e−2 W/m²,
   justified: ~10 float32 ops on operands ≤ 350 ⇒ worst-case accumulation
   ~10·2⁻²³·350 ≈ 4e−4; 1e−2 = 25× margin). **PASS** (max error 7.6e−6).
2. **10.4.2.1.2 Q_nonlatent control** — independent values identical across cases
   (< 1e−3). **PASS**.
3. **10.4.2.1.3 Latent identity** — production `diag%q_lh` equals
   `m_vapor_production · L_S` for all cases (< 1e−2). **PASS**.
4. **10.4.2.1.4 Production Q_surface monotonic** — SUB < ZERO < DEP (strict).
   **PASS** (44.37 < 149.74 < 351.39).
5. **10.4.2.1.5 Melt monotonic (secondary)** — m_surface SUB ≤ ZERO ≤ DEP.
   **PASS**.
6. **10.4.2.1.6 Sign conventions** — m_vapor and Q_LH: SUB < 0, ZERO ≈ 0, DEP > 0.
   **PASS**.
7. **10.4.2.1.7 Regression of 10.4.2 test-side bug** — DEP case configured with
   explicit d2m = 283.15 K; independent Q_LH recomputed from literals
   283.15/283.15 K equals production `diag%q_lh` = 201.645966 W/m² (< 1e−3). No
   stale atmosphere values. **PASS**.

## Tolerance justification

- Q_surface identity: production sums ~5 terms of magnitude ≤ 350 + Q_LH.
  float32 eps = 2⁻²³ ≈ 1.19e−7; ~10 partial-sum roundings ⇒ ≤ ~10·eps·350 ≈ 4e−4 W/m²
  worst case. Tolerance 1e−2 W/m² is 25× this bound and 0.003% of the 350 W/m² scale.
- Latent identity: product-form `m_vapor·L_S` vs production
  `ρ·L_S·C_E·U·Δq` differ only by multiplication grouping ⇒ 1e−2 W/m²; measured
  errors exact to float32 in all cases.
- No calibration or tolerance tuning was used to force agreement; observed errors
  are pure float32 rounding at the 1e−5 W/m² level.

## Why this is not tautological

- Q_nonlatent_expected is evaluated from its own formula (longwave + SH) using
  the controlled atmospheric inputs and initial surface temperature — it never
  reads production fluxes.
- Q*LH_expected uses the production \_vapor mass flux* diagnostic × fixed `L_S`
  (a product identity, independently anchored by 10.4.2 check 10.4.2.10); note
  this is the definition requested, keeping the dependence on the production
  vapor diagnostic explicit.
- The production total flux is compared only at the end, in its intended output
  location (`diag%q_surface`), never reconstructed from `m_surface`.

## Regression

- `fpm test --flag "-I/usr/include"` — full suite: exit 0; all 49 test programs
  pass, no non-zero stops.
- Surface Melt Audit: 66 checks, 0 errors (59 prior + 7 new).
- Canonical ocean/sea-ice physics untouched; iceberg validation-only.

## Files changed

- `src/iceberg_types.f90` — diagnostics type: added `q_surface`, `q_lh` fields.
- `src/iceberg_thermodynamics.f90` — `compute_surface_melt`: diagnostic-only
  assignment of `diag%q_surface`, `diag%q_lh` (physics numerics unchanged).
- `test/iceberg_test_surface_melt_audit.f90` — Stage 10.4.2.1 block
  (checks 10.4.2.1.1–10.4.2.1.7).
- `docs/wiki/stages/stage10/Stage10.4.2.1_Independent_Q_surface_output_validation.md` — this report.

## Limitations

- Validation limited to the polar-night melt regime (273–289 K, SW = 0) tested;
  the SW-vapour coupling path (precipitable-water attenuation of SW) is a
  separate physical effect, excluded here by design.
- Q_LH_expected carries the production `m_vapor` diagnostic (product-form identity,
  per task definition) rather than a fully independent vapor computation; the
  independent anchoring is check 10.4.2.10 from the prior stage.
- Only the surface energy partition is validated; no external data comparison
  (that would be Post-Stage 9.4 calibration work).

## Classification

**C** — Production physics unchanged; diagnostic-only API addition (q_surface/q_lh
exposure); the production Q_surface output is now directly and independently
validated against Q_nonlatent_independent + m_vapor·L_S.
