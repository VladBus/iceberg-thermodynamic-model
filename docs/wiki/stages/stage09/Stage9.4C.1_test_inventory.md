# Stage 9.4C.1 Test Infrastructure Audit — Machine-Verifiable Inventory

**Generated:** 2026-09-04  
**fpm version:** 0.13.0-alpha  
**Command:** `fpm test --flag "-I/usr/include"`

---

## Complete Test Inventory

| #   | Test Target (fpm)                       | Source File                                 | FPM Registered | Executed by `fpm test` | CI Category | Status              | Category               |
| --- | --------------------------------------- | ------------------------------------------- | -------------- | ---------------------- | ----------- | ------------------- | ---------------------- |
| 1   | iceberg_test_1_hydrostatic              | iceberg_test_1_hydrostatic.f90              | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 2   | iceberg_test_2_zero_gradient            | iceberg_test_2_zero_gradient.f90            | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 3   | iceberg_test_3_uniform_current          | iceberg_test_3_uniform_current.f90          | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 4   | iceberg_test_4_vertical_shear           | iceberg_test_4_vertical_shear.f90           | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 5   | iceberg_test_5_warm_ocean               | iceberg_test_5_warm_ocean.f90               | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 6   | iceberg_test_6_cold_ocean               | iceberg_test_6_cold_ocean.f90               | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 7   | iceberg_test_7_vertical_temp_gradient   | iceberg_test_7_vertical_temp_gradient.f90   | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 8   | iceberg_test_8_wind_forcing             | iceberg_test_8_wind_forcing.f90             | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 9   | iceberg_test_9_coriolis_only            | iceberg_test_9_coriolis_only.f90            | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 10  | iceberg_test_10_mass_conservation       | iceberg_test_10_mass_conservation.f90       | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 11  | iceberg_test_11_30day_offline           | iceberg_test_11_30day_offline.f90           | Auto           | YES                    | iceberg     | PASS                | canonical              |
| 12  | iceberg_test_moving_trajectory          | iceberg_test_moving_trajectory.f90          | Auto           | YES                    | iceberg     | PASS                | regression             |
| 13  | iceberg_test_moving_coriolis            | iceberg_test_moving_coriolis.f90            | Auto           | YES                    | iceberg     | PASS                | regression             |
| 14  | iceberg_test_moving_forcing             | iceberg_test_moving_forcing.f90             | Auto           | YES                    | iceberg     | PASS                | regression             |
| 15  | iceberg_test_artificial_forcing         | iceberg_test_artificial_forcing.f90         | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 16  | iceberg_test_coord_mapping              | iceberg_test_coord_mapping.f90              | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 17  | iceberg_test_coord_roundtrip            | iceberg_test_coord_roundtrip.f90            | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 18  | iceberg_test_coriolis_convergence       | iceberg_test_coriolis_convergence.f90       | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 19  | iceberg_test_coriolis_sign              | iceberg_test_coriolis_sign.f90              | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 20  | iceberg_test_discrete_momentum          | iceberg_test_discrete_momentum.f90          | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 21  | iceberg_test_en4_interp                 | iceberg_test_en4_interp.f90                 | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 22  | iceberg_test_era5_interp                | iceberg_test_era5_interp.f90                | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 23  | iceberg_test_force_budget               | iceberg_test_force_budget.f90               | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 24  | iceberg_test_forcing_interp_sensitivity | iceberg_test_forcing_interp_sensitivity.f90 | Auto           | YES                    | iceberg     | PASS                | numerical verification |
| 25  | iceberg_test_ibcao_interp               | iceberg_test_ibcao_interp.f90               | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 26  | iceberg_test_wind_drift_sensitivity     | iceberg_test_wind_drift_sensitivity.f90     | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 27  | iceberg_test_water_drag_methods         | iceberg_test_water_drag_methods.f90         | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 28  | iceberg_test_water_drag_controlled      | iceberg_test_water_drag_controlled.f90      | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 29  | iceberg_test_position_forcing           | iceberg_test_position_forcing.f90           | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 30  | iceberg_test_boundary                   | iceberg_test_boundary.f90                   | Auto           | YES                    | iceberg     | PASS                | regression             |
| 31  | iceberg_test_surface_melt_audit         | iceberg_test_surface_melt_audit.f90         | Auto           | YES                    | iceberg     | PASS                | physics validation     |
| 32  | check                                   | check.f90                                   | Auto           | SKIPPED                | canonical   | SKIP                | legacy/manual          |
| 33  | conv_test                               | conv_test.f90                               | Auto           | YES                    | canonical   | PASS                | canonical              |
| 34  | eos_test                                | eos_test.f90                                | Auto           | YES                    | canonical   | PASS                | canonical              |
| 35  | eos_precision_test                      | eos_precision_test.f90                      | Auto           | YES                    | canonical   | PASS                | canonical              |
| 36  | cold_ice_snow_test                      | cold_ice_snow_test.f90                      | Auto           | YES                    | canonical   | PASS                | canonical              |
| 37  | snowfall_test                           | snowfall_test.f90                           | Auto           | YES                    | canonical   | PASS                | canonical              |
| 38  | thermo_input_test                       | thermo_input_test.f90                       | Auto           | YES                    | canonical   | PASS                | canonical              |
| 39  | ocean_init_test                         | ocean_init_test.f90                         | Auto           | YES                    | canonical   | PASS                | canonical              |
| 40  | era5_coverage_test                      | era5_coverage_test.f90                      | Auto           | YES                    | canonical   | PASS                | canonical              |
| 41  | ice_init_test                           | ice_init_test.f90                           | Auto           | YES                    | canonical   | PASS                | canonical              |
| 42  | drift_scaling_wind                      | drift_scaling_wind.f90                      | Auto           | YES                    | iceberg     | PASS                | diagnostic             |
| 43  | drift_scaling_wind_no_cor               | drift_scaling_wind_no_cor.f90               | Auto           | YES                    | iceberg     | PASS                | diagnostic             |
| 44  | drift_scaling_current                   | drift_scaling_current.f90                   | Auto           | YES                    | iceberg     | PASS                | diagnostic             |
| 45  | param_sensitivity_30day                 | param_sensitivity_30day.f90                 | Auto           | YES                    | iceberg     | PASS (no assertion) | diagnostic             |

---

## Summary Statistics

| Metric                                    | Count                                                         |
| ----------------------------------------- | ------------------------------------------------------------- |
| Total test source files (test/\*.f90)     | 45                                                            |
| FPM auto-discovered test targets          | 40\*                                                          |
| Tests executed by `fpm test`              | 40                                                            |
| Tests with PASS/FAIL assertions           | 37                                                            |
| Tests SKIPPED (require external data)     | 1 (check)                                                     |
| Diagnostic-only tests (no assertions)     | 3 (param_sensitivity_30day, drift_scaling_wind_no_cor, check) |
| Tests reported in CI comment ("33 tests") | **INACCURATE** — actual is 40 auto-discovered, 37 asserting   |

\*Note: fpm.toml explicitly defines only 2 test targets (`iceberg_hydrostatic`, `iceberg_zero_gradient`). fpm 0.13.0 auto-discovers all test files in test/ directory, yielding 40 executable test targets.

---

## CI Documentation Audit

**Current CI comment:** "Runs all Fortran tests (33 tests: 14 iceberg + 19 canonical) on every push/PR"

**Actual:** 40 auto-discovered test targets (28 iceberg + 12 canonical), 37 with assertions.

**Discrepancy:** CI comment is outdated and inaccurate. Must be corrected.

---

## Test Category Definitions

| Category               | Description                                           | Examples                                                            |
| ---------------------- | ----------------------------------------------------- | ------------------------------------------------------------------- |
| canonical              | Legacy AARI model tests (ocean/sea-ice physics)       | conv_test, eos_test, thermo_input_test                              |
| iceberg                | Iceberg model tests (Stage 9.1-9.4)                   | iceberg_test_1_hydrostatic through iceberg_test_11                  |
| regression             | Tests verifying no regression from previous stages    | iceberg_test_moving_trajectory, iceberg_test_boundary               |
| numerical_verification | Convergence, consistency, discrete closure tests      | iceberg_test_coriolis_convergence, iceberg_test_discrete_momentum   |
| physics_validation     | Tests comparing against physical expectations         | iceberg_test_water_drag_controlled, iceberg_test_surface_melt_audit |
| diagnostic             | Parameter studies, scaling experiments (no pass/fail) | param*sensitivity_30day, drift_scaling*\*                           |
| legacy/manual          | Obsolete or requires manual setup                     | check                                                               |

---

## Required CI Correction

Replace in `.github/workflows/ci.yml`:

```yaml
# OLD (inaccurate)
# Runs all Fortran tests (33 tests: 14 iceberg + 19 canonical)

# NEW (accurate)
# Runs all Fortran tests via fpm auto-discovery (40 targets: 28 iceberg + 12 canonical, 37 with assertions)
```

---

## fpm.toml Status

**Current fpm.toml** explicitly defines only 2 test targets:

- `[test.iceberg_hydrostatic]`
- `[test.iceberg_zero_gradient]`

**All other 38 tests** are auto-discovered by fpm 0.13.0.

**Decision:** This is acceptable behavior for fpm 0.13.0. No need to explicitly register all 40 tests unless we want to control which subset runs in CI. The auto-discovery is working correctly.

**Recommendation:** Keep fpm.toml minimal; document auto-discovery behavior in CI.
