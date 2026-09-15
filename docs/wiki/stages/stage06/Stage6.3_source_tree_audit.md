# Stage 6.3 — Source Tree Audit & Cleanup Report

## Overview

Systematic cleanup of the repository source tree (app/, src/, test/, python/) after Stage 6.2 introduced run-based data architecture. Goal: make repository minimal, reproducible, and clearly organized without losing historically important physics or tests.

## Inventory & Classification

### App/ Audit

| File         | Type    | Role                        | Classification | Notes                                                                 |
| ------------ | ------- | --------------------------- | -------------- | --------------------------------------------------------------------- |
| app/main.f90 | Fortran | Main program / orchestrator | **PRODUCTION** | Sole executable entry point. Uses all production modules. No removal. |

### Src/ Audit (22 modules)

| Module                            | Used by main?                                                    | Used by tests?                             | Classification | Notes                                                       |
| --------------------------------- | ---------------------------------------------------------------- | ------------------------------------------ | -------------- | ----------------------------------------------------------- |
| advection_2d.f90                  | ✅ (adv2d)                                                       | ❌                                         | **PRODUCTION** | 2D scalar transport (FCT)                                   |
| advection_3d_s.f90                | ✅ (advs)                                                        | ❌                                         | **PRODUCTION** | 3D salt advection (FCT)                                     |
| advection_3d_t.f90                | ✅ (advt)                                                        | ❌                                         | **PRODUCTION** | 3D temperature advection (FCT)                              |
| barotropic_dynamics.f90           | ✅ (advsh)                                                       | ❌                                         | **PRODUCTION** | 2D barotropic dynamics (Leith-Richtmyer + FCT)              |
| convective_adjustment.f90         | ✅ (conv_adj, ca_reset, ca_stats, ca_probe_inversions)           | ✅ (conv_test)                             | **PRODUCTION** | Historical convective mixing with Stage 4.2/4.3 diagnostics |
| equation_of_state.f90             | ✅ (eos_diag)                                                    | ✅ (eos_test, thermo_input_test)           | **PRODUCTION** | Eckart EOS (density anomaly)                                |
| grid_coupling.f90                 | ✅ (coup1)                                                       | ❌                                         | **PRODUCTION** | Bathymetry, metrics, Coriolis                               |
| grid_masks.f90                    | ✅ (ikuv)                                                        | ❌                                         | **PRODUCTION** | Wet/dry masks for U/V points                                |
| ice_deform.f90                    | ✅ (deform)                                                      | ❌                                         | **PRODUCTION** | Ice deformation tensors                                     |
| ice_redis.f90                     | ✅ (redis)                                                       | ❌                                         | **PRODUCTION** | Ice thickness redistribution (Thorndike)                    |
| ice_stress.f90                    | ✅ (stress)                                                      | ❌                                         | **PRODUCTION** | Ice stress tensor (viscous-plastic)                         |
| initial_conditions.f90            | ✅ (init_ocean)                                                  | ❌                                         | **PRODUCTION** | Synthetic T/S/U/V/W initialization                          |
| netcdf_input.f90                  | ✅ (era5_open, era5_wind, era5_find_time_index, era5_bilinear2d) | ❌                                         | **PRODUCTION** | ERA5 NetCDF reading + bilinear interp                       |
| netcdf_output.f90                 | ✅ (write_nc)                                                    | ✅ (check)                                 | **PRODUCTION** | CF-1.10 diagnostic NetCDF export                            |
| param.f90                         | ✅ (all arrays, constants, run_id, era5_input_file)              | ✅ (all)                                   | **PRODUCTION** | Global state module                                         |
| run_config.f90                    | ✅ (setup_run_dirs)                                              | ❌                                         | **PRODUCTION** | Stage 6.2 run isolation & output dirs                       |
| shallow_water.f90                 | ✅ (shal)                                                        | ❌                                         | **PRODUCTION** | Barotropic time-split loop + free surface                   |
| smooth_filter.f90                 | ✅ (gladw via wind_forcing)                                      | ❌                                         | **PRODUCTION** | Laplacian smoothing of pressure                             |
| thermodynamics.f90                | ✅ (heat)                                                        | ✅ (cold_ice_snow_test, thermo_input_test) | **PRODUCTION** | Heat budget, phase changes, ice growth                      |
| tide_forcing.f90                  | ✅ (datte)                                                       | ❌                                         | **PRODUCTION** | Astronomical tidal harmonics (M2,S2,K1,O1)                  |
| wind_forcing.f90                  | ✅ (wind1, era5_wind)                                            | ❌                                         | **PRODUCTION** | Geostrophic wind + ERA5 wind + stress                       |
| convective_adjustment.f90.bak     | ❌                                                               | ❌                                         | **DELETED**    | Stale backup (pre-Stage 4.2 features)                       |
| src/convective_adjustment.f90.bak | —                                                                | —                                          | **DELETED**    | Removed in this stage                                       |

**All 21 production modules retained.** No physics modules removed.

### Test/ Audit (7 test programs)

| Test                   | Type                      | Classification | Notes                                                                                               |
| ---------------------- | ------------------------- | -------------- | --------------------------------------------------------------------------------------------------- |
| check.f90              | NetCDF validation         | **CORE**       | Validates IEEE NaN/Inf, fillValue, bounds, wind/stress alignment. Default reads run dir final file. |
| conv_test.f90          | Convective adjustment     | **CORE**       | 15 checks: mixing, conservation, stability.                                                         |
| eos_test.f90           | Equation of state         | **CORE**       | 7 checks: Eckart EOS reference values + physical ranges.                                            |
| eos_precision_test.f90 | IEEE-754 float32 analysis | **DIAGNOSTIC** | Stage 4.3b: float32 quantization root cause. Standalone, no physics changes.                        |
| cold_ice_snow_test.f90 | Controlled physics test   | **DIAGNOSTIC** | Stage 5.4: cold column ice/snow experiment. NOT production.                                         |
| snowfall_test.f90      | Snowfall conversions      | **CORE**       | 9 checks: accumulation, units, non-negativity, time alignment.                                      |
| thermo_input_test.f90  | Thermodynamic ERA5 input  | **CORE**       | 8 checks: humidity (d2m+t2m), cloud (tcc), snowfall (sfal).                                         |
| experiment_b.f90.bak   | Experimental precision    | **DELETED**    | Stale backup, no corresponding .f90. Removed.                                                       |

**All 7 active tests retained.** Backup file removed.

### Python/ Audit

#### python/era5/ (3 scripts) — **KEEP ALL**

| Script            | Role                                      | Status     |
| ----------------- | ----------------------------------------- | ---------- |
| download_era5.py  | CDS download with --domain barents/arctic | **ACTIVE** |
| check_era5.py     | Validate NetCDF + domain coverage         | **ACTIVE** |
| merge_snowfall.py | Merge sf into instantaneous vars          | **ACTIVE** |

#### python/analysis/ (11 active + 3 legacy)

| Script                        | Role                                       | Classification         |
| ----------------------------- | ------------------------------------------ | ---------------------- |
| run_context.py                | Run path resolution (--run-id/--manifest)  | **ACTIVE SUPPORT**     |
| run_manifest.py               | Generate/validate run manifests            | **ACTIVE SUPPORT**     |
| units.py                      | SI <-> presentation unit conversions       | **ACTIVE SUPPORT**     |
| validate_q1_output.py         | Calendar + SI units + bounds validation    | **ACTIVE**             |
| seasonal_analysis.py          | Multi-month daily/monthly summaries        | **ACTIVE**             |
| heat_diagnostics.py           | HEAT ON diagnostics + comparison           | **ACTIVE**             |
| snowfall_diagnostics.py       | Snowfall rate/depth/heat flux analysis     | **ACTIVE**             |
| profiles.py                   | Vertical T/S/U/V/W/RO profiles             | **ACTIVE**             |
| convective_analysis.py        | Stage 4.3 guard cycling analysis           | **ACTIVE**             |
| eos_precision_analysis.py     | Float32/64 EOS bit-level verification      | **DIAGNOSTIC**         |
| convective_precision_study.py | Experiments A-D precision study            | **DIAGNOSTIC**         |
| diagnostics.py                | Per-day summary from daily_diagnostics.csv | **LEGACY** → `legacy/` |
| statistics.py                 | Monthly stats from daily_summary.csv       | **LEGACY** → `legacy/` |
| generate_report.py            | Assemble monthly_report.txt                | **LEGACY** → `legacy/` |

**3 legacy scripts moved to `python/analysis/legacy/`** (replaced by run-aware seasonal_analysis.py, heat_diagnostics.py, snowfall_diagnostics.py).

#### python/plotting/ (3 scripts) — **KEEP ALL**

| Script              | Role                                                              |
| ------------------- | ----------------------------------------------------------------- |
| plots.py            | Standardized daily figures (surface maps, EUU, vertical profiles) |
| seasonal_plots.py   | Seasonal time series + vertical profiles + heat fluxes            |
| convective_plots.py | Stage 4.3 guard cycling diagnostic figures                        |

#### python/tests/ (1 test) — **KEEP**

| Test                    | Role                                           |
| ----------------------- | ---------------------------------------------- |
| test_units_roundtrip.py | SI → presentation → SI round-trip verification |

### Generated Artifacts Removed

| Location                               | Count        | Action                                                    |
| -------------------------------------- | ------------ | --------------------------------------------------------- |
| python/plotting/figures/ (all subdirs) | 25 PNG files | **DELETED** — moved to data/runs/<run_id>/output/figures/ |
| python/plotting/figures/ directory     | 1            | **DELETED**                                               |

### Backup Files Removed

| File                              | Reason                                         |
| --------------------------------- | ---------------------------------------------- |
| src/convective_adjustment.f90.bak | Stale backup missing Stage 4.2/4.3 diagnostics |
| test/experiment_b.f90.bak         | Stale backup with no corresponding .f90        |

### Dependency Graph (Main Program Flow)

```
main.f90
├── param (global state)
├── run_config (run isolation)
├── grid_coupling → grid_masks
├── initial_conditions
├── netcdf_input (ERA5)
├── equation_of_state (EOS)
├── wind_forcing → smooth_filter + netcdf_input
├── ice_stress → ice_deform
├── ice_redis
├── ice_deform
├── advection_2d (ice concentration/mass)
├── thermodynamics (HEAT, gated by kl1=0)
├── advection_3d_s (salt)
├── advection_3d_t (temperature)
├── convective_adjustment → equation_of_state
├── barotropic_dynamics (advsh)
├── shallow_water → barotropic_dynamics
├── tide_forcing
└── netcdf_output
```

### Test Dependencies

| Test               | Modules Used                                           |
| ------------------ | ------------------------------------------------------ |
| check              | netcdf, ieee_arithmetic, netcdf_input (for validation) |
| conv_test          | equation_of_state, convective_adjustment               |
| eos_test           | equation_of_state                                      |
| eos_precision_test | (standalone, reproduces EOS in numpy)                  |
| cold_ice_snow_test | param, thermodynamics                                  |
| snowfall_test      | param                                                  |
| thermo_input_test  | equation_of_state                                      |

### FPM Configuration Audit

fpm.toml verified:

- ✅ `link = ["netcdff"]`
- ✅ `external-modules = ["netcdf"]`
- ✅ stdlib git dependency (stdlib-fpm branch)
- ✅ No deleted files referenced
- ✅ No obsolete executables or test targets

### Git Tracking Audit

All generated artifacts removed from tracking:

- ✅ `*.mod`, `*.smod`, `*.o`, `*.a`, `*.so`, `*.exe` covered by .gitignore
- ✅ `*.nc`, `*.vtk`, `*.dat`, `*.bak` covered by .gitignore
- ✅ `python/plotting/figures/` (25 PNGs) removed from tracking
- ✅ `data/output/` empty and ignored
- ✅ `data/` directory ignored
- ✅ `docs/wiki/ERA5_INTEGRATION_TODO.md` untracked (local only), .gitignore updated

### Data Directory Verification

```
data/
  input/
    raw/era5/           # Raw ERA5 downloads (YYYY/YYYY_MM/)
    processed/era5/     # Merged ERA5 + snowfall (YYYY/YYYY_MM/, 2020_Q1/)
  runs/
    2020_Q1_test_heat_on/  # Run-isolated output (nc, csv, txt, logs, figures, manifest)
  archive/
    legacy/             # Reserved
    test/era5_test.nc   # Regression dataset (KEPT)
    pre_cleanup/        # Obsolete artifacts
  output/               # EMPTY (ignored)
```

### ERA5 Test Regression Data

- **era5_test.nc** preserved at `data/input/raw/era5/era5_test.nc` and `data/archive/test/era5_test.nc`
- 12 time steps, 101 lat (65-90N), 1440 lon, vars: u10, v10, t2m, msl
- Used for smoke testing and regression validation

### Validation Results

| Check                                                 | Result                                 |
| ----------------------------------------------------- | -------------------------------------- |
| `fpm build -Wall -Wextra`                             | ✅ PASS                                |
| `fpm test` (all suites)                               | ✅ PASS (22 checks + validation suite) |
| `fpm run -fcheck=all -ffpe-trap` (smoke)              | ✅ Clean EXIT=0                        |
| `validate_q1_output.py --run-id 2020_Q1_test_heat_on` | ✅ PASS                                |
| `run_manifest.py --run-id 2020_Q1_test_heat_on`       | ✅ PASS (90 files)                     |
| All run-aware analysis scripts                        | ✅ PASS                                |
| All run-aware plotting scripts                        | ✅ PASS                                |
| SI round-trip unit test                               | ✅ PASS                                |
| Python plotting output → data/runs/.../figures/       | ✅ Verified                            |

### Deleted Files Summary

| Path                                 | Reason                                           | Replacement                        | Verification                      |
| ------------------------------------ | ------------------------------------------------ | ---------------------------------- | --------------------------------- |
| src/convective_adjustment.f90.bak    | Stale backup (pre-Stage 4.2)                     | Current convective_adjustment.f90  | Build passes                      |
| test/experiment_b.f90.bak            | Stale backup, no .f90 counterpart                | eos_precision_test.f90             | Tests pass                        |
| python/analysis/diagnostics.py       | Legacy, replaced by seasonal_analysis.py         | seasonal_analysis.py               | Run-aware scripts work            |
| python/analysis/statistics.py        | Legacy, replaced by seasonal_analysis.py monthly | seasonal_analysis.py               | Run-aware scripts work            |
| python/analysis/generate_report.py   | Legacy, replaced by run-aware reporting          | seasonal_analysis.py               | Run-aware scripts work            |
| python/plotting/figures/\* (25 PNGs) | Generated artifacts, wrong location              | data/runs/<run_id>/output/figures/ | Plotting scripts write to run dir |

### Archived Files (Retained for Provenance)

| Path                                      | Original Location                  | Reason                    |
| ----------------------------------------- | ---------------------------------- | ------------------------- |
| python/analysis/legacy/diagnostics.py     | python/analysis/diagnostics.py     | Legacy pipeline component |
| python/analysis/legacy/statistics.py      | python/analysis/statistics.py      | Legacy pipeline component |
| python/analysis/legacy/generate_report.py | python/analysis/generate_report.py | Legacy pipeline component |

### Next Steps

1. **Stage 6.4+** — ERA5 Barents domain download (CDS queue pending)
2. **Stage 3.5/6.1** — Real grid/bathymetry (KOORD.DAT/hhh.bar still missing)
3. **Physics** — No changes made; all protection constraints honored

---

**Stage 6.3 Complete** — Repository is now minimal, run-aware, and reproducible with clear separation between production code, diagnostics, legacy archive, and generated outputs.
