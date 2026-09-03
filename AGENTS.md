# AGENTS.md — AARI Iceberg Thermodynamic & Dynamics Model

Modernized Fortran 2008/2018 reimplementation of the Dmitriev-Nesterov iceberg model (AARI, 1995–2001). Master's thesis at RSHU.

## Commands

```bash
# ALWAYS use -I/usr/include (netcdf.mod lives at /usr/include, not in fpm tree)
fpm build --flag "-I/usr/include"
fpm run    --flag "-I/usr/include"
fpm test   --flag "-I/usr/include"

# Strict debug
fpm run --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"

# Individual test suites
fpm test --flag "-I/usr/include" eos_test            # 7 EOS checks
fpm test --flag "-I/usr/include" conv_test           # 15 convective checks
fpm test --flag "-I/usr/include" thermo_input_test   # 8 thermo input checks
fpm test --flag "-I/usr/include" snowfall_test       # 9 snowfall checks
fpm test --flag "-I/usr/include" cold_ice_snow_test  # cold ice/snow experiment
fpm test --flag "-I/usr/include" eos_precision_test  # float32 EOS precision
fpm test --flag "-I/usr/include" ocean_init_test     # 13 ocean init checks (Stage 7.7)
fpm test --flag "-I/usr/include" era5_coverage_test  # ERA5 forcing coverage
fpm test --flag "-I/usr/include" ice_init_test       # real ice initialization chain

# Iceberg model tests (Stage 9.3)
fpm test --flag "-I/usr/include" iceberg_test_1_hydrostatic      # Hydrostatic equilibrium
fpm test --flag "-I/usr/include" iceberg_test_2_zero_gradient    # Zero gradient env
fpm test --flag "-I/usr/include" iceberg_test_3_uniform_current  # Uniform current drift
fpm test --flag "-I/usr/include" iceberg_test_4_vertical_shear   # Vertical shear (Method A/B)
fpm test --flag "-I/usr/include" iceberg_test_5_warm_ocean       # Warm ocean melt (1000 days)
fpm test --flag "-I/usr/include" iceberg_test_6_cold_ocean       # Cold ocean no melt
fpm test --flag "-I/usr/include" iceberg_test_7_vertical_temp_gradient  # Vertical T gradient
fpm test --flag "-I/usr/include" iceberg_test_8_wind_forcing     # Wind forcing drift
fpm test --flag "-I/usr/include" iceberg_test_9_coriolis_only    # Coriolis inertial oscillation
fpm test --flag "-I/usr/include" iceberg_test_10_mass_conservation # Mass conservation budget
fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline   # 30-day real forcing (ERA5/EN4/IBCAO)
fpm test --flag "-I/usr/include" drift_scaling_wind              # Wind drift scaling
fpm test --flag "-I/usr/include" drift_scaling_wind_no_cor       # Wind drift no Coriolis
fpm test --flag "-I/usr/include" drift_scaling_current           # Current drift scaling
fpm test --flag "-I/usr/include" param_sensitivity_30day         # Parameter sensitivity framework
```

No CI, no lint, no formatter beyond VS Code (`fprettify`/`fortls`). Python tooling uses conda env `iceberg-thermodynamic-model`.

## Unit Systems (MIXED — would be missed)

| Domain         | Units         | Variables                                                                                                            |
| -------------- | ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Hydrodynamics  | **CGS**       | `dx` cm, `U/V` cm/s, `dt` s, `cof` dyn/cm²                                                                           |
| Thermodynamics | **SI**        | `T` °C, `S` mass fraction 0.033–0.035 (**NOT PSU**)                                                                  |
| NetCDF output  | **SI**        | `temperature` K, `salinity_mass_fraction` kg/kg, `density_anomaly` kg m⁻³ (ρ−1.02), `u/v/w` m/s, `tau` Pa, `dp` Pa/m |
| ERA5 input     | **converted** | u10/v10 m/s → ×100 → cm/s; msl Pa → ×0.01 → hPa; t2m K → −273.15 → °C                                                |

Conversions only at the NetCDF output boundary (`netcdf_output.f90`). Internal CGS/Celsius unchanged. Python converts to presentation units via `python/analysis/units.py`.

## Architecture

- **`app/main.f90`** — orchestrator. `forcing_mode = forcing_mode_era5` (line 111). `kl1 = 1` (line 108) enables `heat()`. Exit at `nday1 == 91` (line 320). CLI: `fpm run -- <run_id> [era5_file]`.
- **`src/param.f90`** — global state: all shared arrays, constants, grid dims (`is=132, js=104, ks=18`, `is1=133, js1=105`, `ngr=5`). Land mask = **`8888.0`** (use epsilon: `abs(x-8888.0) < 1e-8`, never `==`).
- **ERA5 path:** `era5_input_file` defaults to `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc`. Falls back to legacy if absent.
- **Grid modes:** `grid_mode_real` (default) reads KOORD.DAT + hhh.bar, `STOP`s if missing. `grid_mode_test` generates synthetic grid TEST ONLY.
- **Axis conventions:** X ↔ `j` ↔ `u`; Y ↔ `i` ↔ `v`; Y-axis inverted (north at `j=1`).
- **Key modules:** `netcdf_input` (ERA5 read/bilinear interp), `netcdf_output` (CF-1.10 export), `wind_forcing` (legacy + ERA5), `advection_2d/3d_t/3d_s` (FCT), `barotropic_dynamics`, `shallow_water`, `ice_stress/deform/redis`, `thermodynamics`, `grid_coupling`, `initial_ocean_reader` (Stage 7.7 EN4 reader), `initial_conditions`.

### Iceberg Model Architecture (Stage 9.3)

- **`src/iceberg_types.f90`** — types, constants (ρᵢ, ρ_w, C_Dₐ, C_D_w, C_BASAL, C_LATERAL, L_f, etc.), state vector.
- **`src/iceberg.f90`** — main orchestrator: `iceberg_init`, `iceberg_step`, `iceberg_update_geometry`.
- **`src/iceberg_geometry.f90`** — volume, mass, draft, areas, buoyancy check, grounding, mass budget partitioning.
- **`src/iceberg_forcing.f90`** — horizontal bilinear interp (model grid), vertical interp/extrapolation to draft, ERA5 atmos interp, Method A/B current integration.
- **`src/iceberg_thermodynamics.f90`** — basal melt (C_BASAL·ΔT), lateral melt (C_LATERAL·⟨ΔT⟩\_D), surface melt (Q_net/(ρᵢ·L_f)).
- **`src/iceberg_dynamics.f90`** — wind/water drag (Method A: layer-integrated, Method B: depth-averaged), semi-implicit Coriolis, pressure gradient (optional).
- **Forcing:** OFFLINE/PRESCRIBED only. ERA5 (atmos), EN4 (ocean T/S), IBCAO (bathymetry). No two-way coupling.
- **State vector:** `[x, y, u, v, L, W, H]` (7 prognostic). Diagnostic: D, M, areas, draft, sail/wetted.
- **Key constants (compile-time in iceberg_types.f90):** C_BASAL=1e-6, C_LATERAL=1e-6 m/(s·K), C_Dₐ=1.3e-3, C_D_w=2e-3.

## Constraints (DO NOT)

- ❌ Do not omit `-I/usr/include` — compilation fails.
- ❌ Do not `==` on reals — always epsilon (`abs(x-y) < 1e-8`).
- ❌ Do not raise the `0.9e-7` convective threshold or switch EOS to double — root cause is float32 `2⁻²³` quantization; needs promt.md procedure + approval.
- ❌ Do not "fix" FCT anti-diffusion (`CDY*0` in `barotropic_dynamics.f90`) — causes blowup.
- ❌ Do not use `grid_mode=TEST` basin for production claims.
- ❌ Do not set `kl1=1` without providing ERA5 d2m/tcc/precip fields.
- ❌ Before committing, check `.gitignore` — it blocks: `opencode.jsonc`, `.opencode/`, `docs/wiki/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`.
- ❌ Do not delete root-level symlinks: `KOORD.DAT`, `hhh.bar`, `1_k.ice` — required by model, gitignored, point to `data/input/generated/real_grid/`.

### Iceberg Model Constraints (Stage 9.3)

- ❌ Do not modify canonical ocean/sea-ice physics (Block 200/210/280, barotropic solver, EOS, grid, ERA5, bathymetry, thermodynamics).
- ❌ Iceberg forcing must remain OFFLINE/PRESCRIBED. No two-way coupling.
- ❌ No advanced physics (internal 3D temperature, wave erosion, sea-ice capture, rollover, fracture, multi-iceberg) until minimal model verified.
- ❌ Melt coefficients are compile-time constants in `iceberg_types.f90` — require rebuild to change.
- ❌ Vertical interpolation uses model levels (max 45m) — draft up to 88m requires extrapolation (handled in `iceberg_forcing.f90`).
- ❌ Position lat/lon not updated from x,y in time stepping — forcing evaluated at initial position (known limitation).
- ❌ Semi-implicit Coriolis solver has 8% period error at Δt=3600s — numerical damping; convergence study needed.

## Calendar Semantics

Day `d` (1-indexed) = `start_date + d days`, NOT `start_date + (d-1) days`:

- `day_00` = initial state, `day_01` = after 1 integration day, `day_90` = 2020-03-31 (Q1)
- `results_day_final.nc` = duplicate of `day_90`

ERA5 auto-limits: `mm1 = min(mm1, (era5_ntime-1)/nperday)`. Jan 2020 = 124 slices → 30 model days.

## Post-Processing

**Never glob `data/runs/*/output/nc` without a run manifest** — picks up stale files. Always:

1. `python python/analysis/run_manifest.py --run-id <run_id>`
2. Pass `--manifest` to analysis scripts.

Snowfall variable in merged ERA5 NetCDF: `sf` (not `era5_snowfall_rate`). Merge script writes `sf` with units `m s-1`.

## Regeneration

```bash
# After fresh clone, regenerate grid inputs from IBCAO bathymetry:
python python/grid/build_real_grid_inputs.py
# Creates: KOORD.DAT, hhh.bar, 1_k.ice → data/input/generated/real_grid/
# Symlinked to project root (gitignored)
```

ERA5 download: `conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py --year 2020 --month 1 --include-snowfall`

## Active Constraints Worth Preserving

- **Convective adjustment:** 1000-iteration guard. Root cause: EOS float32 quantization `2⁻²³ ≈ 1.19e-7` vs threshold `0.9e-7`. Monitored via `ca_reset`/`ca_stats` counters.
- **Ice-ocean drag singularity:** `hht ∼ 0.01 m` causes positive feedback. Guard `hht<0.01 → u=v=0` interrupts it. See `docs/wiki/Stage7.3_stability_investigation.md`.
- **ERA5 coverage gap:** 5.2% of wet cells (591/11,330) outside forcing domain. Fixable by expanding download to ≥64°N, ≥77°E.
- **FCT anti-diffusion intentionally disabled** in `advsh` — zeroed X-block intermediates + `CDY*0`.
- **`grid_mode=TEST`** synthetic grid is NOT a real basin.
- **Missing input files are normal:** `GRM2`, `FI1DL1.DAT`, `DAV4_5.98`, `1_k.ice` absent; code falls back to synthetic fields.
- **Thomas algorithm vertical viscosity:** Can reach 8.5×10⁵ cm²/s at k=2 with realistic EN4 init → matrix ill-conditioning → blowup. Do not "fix" without physics review.
- **Stage 7.7B finding:** Realistic EN4 initialization is dynamically incompatible with zero-initial-velocity state. Requires 3D geostrophic initialization or controlled spin-up (Stage 7.8+).

## Development Workflow (from promt.md)

### Before starting work, ALWAYS:

1. Read: `AGENTS.md`, `docs/wiki/`, current git status, recent commits, all sources related to current stage
2. Use existing TODO as main project plan — don't create new plan from scratch. Sync TODO with actual repo state. TODO is a living project journal.
3. Use available tools: repo-wide search, historical sources, version comparison, git diff, diagnostics, test runs, static analysis, docs.
4. Before changing physics: find historical algorithm, match with current arrays, check units, check dimensions, determine place in time loop, check impact on existing modules.
5. Don't change physics equations just to pass tests.

### After completing a stage:

- Update `docs/wiki/`
- Mark completed items
- Add new tasks/risks found
- Create brief report
- Run mandatory build/run/test
- Check git diff
- Make separate commit
- Push only if it matches current workflow

### Conflict resolution (code vs historical vs docs vs previous decisions):

Don't choose silently. Record conflict, source of each variant, and decision made.

### Stage completion report format:

```
DONE
CHANGED
PHYSICS
TESTS
DIAGNOSTICS
ASSUMPTIONS
RISKS
TODO UPDATED
GIT
NEXT
```

### Important notes:

- Don't create local Python environments (venv/.venv/env/) inside repo. Conda env lives outside.
- CDS credentials in `~/.cdsapirc` — MUST NOT be committed to Git.
- Important notes that might be lost due to context limits → write to `docs/wiki/` or appropriately named .md file.

## Python / ERA5 Environment

### Conda

Project Python environment: `iceberg-thermodynamic-model`
Expected location: `/home/vlad/miniconda3/envs/iceberg-thermodynamic-model`
Activate: `conda activate iceberg-thermodynamic-model`

### LSP / Development Tools

- **fortls** — Fortran Language Server (for VS Code `fortls` extension)
- **fprettify** — Fortran code formatter (for VS Code `fprettify` integration)

### Python Analysis Scripts

All analysis scripts are in `python/analysis/`:

- `run_manifest.py` — required for post-processing
- `units.py` — unit conversions
- `run_context.py` — run context utilities
- `legacy/` — generic utilities (diagnostics, statistics, report generation)
- Stage-specific diagnostics now in `data/output/diagnostics/stage9.3/`

### Key Data Paths

| Purpose            | Path                                                                              |
| ------------------ | --------------------------------------------------------------------------------- |
| EN4 initial T/S    | `data/input/processed/ocean/initial_ts_2020-01-01.nc`                             |
| ERA5 forcing       | `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc` |
| Real grid inputs   | `data/input/generated/real_grid/` (symlinked to root)                             |
| Ice data           | `data/input/generated/real_grid/ice_2020-01-01/`                                  |
| Diagnostics output | `data/output/diagnostics/stage7.7A/`, `stage7.7B/`, `stage9.3/`                   |
| Run outputs        | `data/runs/<run_id>/output/nc/`                                                   |

## Stage 7.7B Summary (Stabilization Attempt)

- **Problem:** Realistic EN4 Jan 2020 T/S causes blowup Day 2 (U_max ~ 5,740 m/s → NaN Day 3)
- **Root cause:** Barotropic adjustment to geostrophic imbalance (50–100×) → vertical viscosity solver failure at ~500m
- **Tested:** dt1=15–120s, Ah=7.5e6–5e7, geostrophic UP2/VP2 init — all fail
- **Classification:** C (mechanism understood; no stable config within allowed params)
- **Report:** `docs/wiki/Stage7.7B_Realistic_Ocean_Stabilization.md`
- **Next:** 3D geostrophic init + controlled spin-up + viscosity clipping (Stage 7.8+)

## Stage 9.3 Summary (Iceberg Model Verification)

- **Classification:** A — Minimal Lagrangian iceberg model scientifically verified and real-forcing TEST_11 completed.
- **Tests:** 11/11 iceberg tests PASS, 14/14 canonical regression PASS (unchanged).
- **TEST_11:** 30-day offline run with ERA5/EN4/IBCAO forcing at 75°N, 30°E — 74.5% mass loss, mass budget error 0.013%.
- **Major fixes:**
  1. Melt coefficient dimensional error (C_BASAL/C_LATERAL: 1e-4→1e-6 m/(s·K), removed /(ρᵢ·L_f) factor)
  2. Vertical extrapolation below 45m model top for draft ~88m
  3. Mass budget uses pre-melt geometry (error 56%→0.013%)
  4. TEST_4 upgraded with 5m vertical resolution in 0-100m (Method A/B ratio = 1.28)
  5. TEST_11 enabled with real forcing
- **Known anomalies:**
  - Wind drift ratio 0.08% (with Coriolis) vs literature 1–2% — needs Cd calibration
  - Coriolis period error 8% at Δt=3600s — numerical damping
  - Lat/lon fixed in TEST_11 — forcing at initial position
- **Diagnostics:** `data/output/diagnostics/stage9.3/` (11 JSON + trajectory CSV)
- **Report:** `docs/wiki/Stage9.3_Scientific_Verification_and_Calibration.md`
- **Next (Stage 9.4):** Calibrate drag coefficients, add wave erosion, sea-ice capture, internal temperature diffusion, rollover criterion, update lat/lon from x,y, Coriolis convergence study.
