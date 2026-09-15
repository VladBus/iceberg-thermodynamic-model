# Stage 10.4.2 — Independent Monotonicity Validation

- **Classification: C** — Independent controlled validation of the Stage 10.4.1 latent-heat monotonicity. No production physics changed.
- **Date:** 2026-09-08
- **Scope:** `compute_surface_melt` energy partition; the old Stage 10.4.9 monotonicity test had an uncontrolled Q_nonlatent and its claim was not justified.

## Objective

Prove, from a _controlled_ experiment, that the Stage 10.4.1 partition satisfies:

```
Q_LH(sub)  <  Q_LH(zero)  <  Q_LH(dep)      (latent flux ordering)
Q_surface(sub) <= Q_surface(zero) <= Q_surface(dep)
Q_melt(sub)    <= Q_melt(zero)    <= Q_melt(dep)
m_sub <= m_zero <= m_dep
```

with the expected ordering derived **independently from the controlled inputs**,
not from re-running the implementation's own arithmetic (anti-tautology rule).

## Why the old TEST 10.4.9 was uncontrolled

TEST 10.4.9 ran in **polar day** (`time = 172 d`, lat 75). In `compute_surface_melt`
the condensation branch computes `e_vap -> precipitable_water_cm -> SW_down`
(SW attenuation depends on water vapour). So changing `d2m` changed **both**:

- `Q_LH` (desired), and
- `SW_down` (NOT controlled) via precipitable water.

Therefore `Q_nonlatent` was NOT identical between the three cases, and the observed
`m_sub=0`, `m_base=2.37e-7`, `m_dep=6.59e-8` numbers (base > dep) were dominated by
the SW response, not a latent-heat monotonicity check. The Stage 10.4.1 summary's
"m_sub < m_base < m_dep" claim was therefore not demonstrated by that test.

## Controlled design: polar night (SW == 0)

In **polar night** (lat 90, `time=0`, cos_zenith = −0.392 < 0) the `cos_zenith > 0`
branch is skipped entirely:

```
Q_nonlatent = LW_down(T_air, tcc, p) + LW_up(T_surface) + SH(rho, T_air, T_surface, U)
```

None of these terms depend on `d2m`. Only `Q_LH = m_vapor * L_S` depends on `d2m`
through `q_air`:

```
m_vapor = rho_air * C_E * U * (q_air(d2m) - q_sat_ice)
q_air   = 0.622 * e_vap(d2m) / p          (Tetens e_sat monotonic in d2m)
```

Since `e_sat(Tetens)` is strictly monotonic in `d2m` and `rh = min(1, e_sat_dew/e_sat_air)`,
`q_air(d2m)` is monotonic, hence `m_vapor`, `Q_LH`, `Q_surface = Q_nonlatent + Q_LH`,
`Q_melt = max(Q_surface,0)`, and `m_surface` are all monotonic in `d2m`.
The expected ordering is derived from **input monotonicity + sign conventions**,
independently of the implementation's arithmetic.

## Experiment parameters (identical except `d2m`)

Polar night, lat 90, `T_surface = 0` (melt branch), `t2m = 283.15 K`,
`tcc = 0`, `msl = 101325 Pa`, `u10 = 10 m/s`, `v10 = 0`.

| Case | `d2m` [K] | q_air vs q_sat_ice    | m_vapor [kg/m²s] | Q_LH [W/m²] | Q_surface [W/m²] | m_surface [m/s] |
| ---- | --------- | --------------------- | ---------------- | ----------- | ---------------- | --------------- |
| SUB  | 263.15    | q_air < q_sat (dry)   | −3.72e−5         | −105.4      | 44.4             | 1.46e−7         |
| ZERO | 273.158   | q_air ≈ q_sat (tuned) | −5.2e−11         | ≈ 0         | 149.7            | 4.93e−7         |
| DEP  | 283.15    | q_air > q_sat (humid) | +7.11e−5         | +201.6      | 351.4            | 1.16e−6         |

- `d2m_zero` solved so `e_sat_dew(Tetens) = e_sat_ice(Murphy-Koop) at 273.15 K`
  ⇒ `m_vapor ~ 0` (here −5.2e−11).
- `Q_nonlatent` computed independently for each case = **149.742706 W/m² in all three** ⇒ control verified.

## All 59 audit checks PASS

New Stage 10.4.2 checks (13 new PASS within the 59-check surface melt audit):

1. **Polar night precondition** — cos_zenith ≤ 0, SW = 0.
2. **Q_nonlatent controlled identical** across SUB/ZERO/DEP (|Δ| < 1e−3 W/m²).
3. **Vapor sign conventions** — m_sub < 0 (sublimation), m_zero ≈ 0, m_dep > 0 (deposition).
4. **m_vapor and Q_LH strictly monotonic** with `d2m`.
5. **Q_surface monotonic** (sub ≤ zero ≤ dep).
6. **Q_melt monotonic, all melting** (sub>0, dep > zero).
7. **m_surface strictly monotonic** (sub < zero < dep).
8. **Zero-latent ⇒ Q_surface = Q_nonlatent** within 1 W/m².
9. **Sublimation quench** — stronger sink (d2m=243 K) cannot increase melt
   (m = 0, T drops to −0.12 °C).
10. **Deposition boost** — stronger source (t2m=d2m=285 K) cannot decrease melt.
11. **Latent identity** — `Q_LH = m_vapor * L_S` = 201.645966 W/m² matches independent
    `rho*C_E*U*(q_air−q_sat)` to < 1e−3 (actually exact in float32).
12. **Below-freezing monotonicity** — T_surface = −10 °C:
    cold-dry → −10.654 °C (cool), cold-saturated → −10.603 °C (less cool),
    warm-humid → −7.378 °C (warming), all m_surface = 0; negative cools, positive warms.
13. **Crossing 0 °C** — T pinned at 0 °C, melt from excess energy only;
    independent analytic `m_expect = max(Q_surface − c_eff·ΔT/dt, 0)/(ρ·L)` =
    2.89023e−7 vs model 2.89023e−7; dep ≥ sub (monotonic).
14. **Geometry mass budget with vapor** — `dH/dt = −m_surface + m_vapor/ρ_ice`
    (iceberg.f90:377); dH_model −3.883e−3 vs dH_expect −3.881e−3.

## Regression

- `fpm test --flag "-I/usr/include"` — full suite exit 0 (43 SUCCESS/PASSED markers),
  14/14 canonical + iceberg suite unchanged.
- Only modified file: `test/iceberg_test_surface_melt_audit.f90` (added Stage 10.4.2 block).
- No production source changed.

## Limitations

- Validation is limited to the 273–289 K / polar-night regime tested; daytime
  SW−vapour coupling is excluded by design (that coupling is a separate, physical
  latitude/time effect, not part of the latent partition).
- Exact arithmetic reproduced in the test mirrors production formulas; the
  _primary_ verdict uses ordering + sign + zero-latent identity, not
  `expected = Q_nonlatent + Q_LH` re-derived in the same float32 sequence.

## Files changed

- `test/iceberg_test_surface_melt_audit.f90` — Stage 10.4.2 block (checks 10.4.2.1–13).
- `docs/wiki/stages/stage10/Stage10.4.2_Independent_monotonicity_validation.md` — this report.

## Next

- None from this stage; production unchanged. Proceed to calibrating drag
  coefficients (Stage 9.4) or the latent/melt model extensions already on TODO.
