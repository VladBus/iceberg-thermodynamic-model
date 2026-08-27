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
- **Key modules:** `netcdf_input` (ERA5 read/bilinear interp), `netcdf_output` (CF-1.10 export), `wind_forcing` (legacy + ERA5), `advection_2d/3d_t/3d_s` (FCT), `barotropic_dynamics`, `shallow_water`, `ice_stress/deform/redis`, `thermodynamics`, `grid_coupling`.

## Constraints (DO NOT)

- ❌ Do not omit `-I/usr/include` — compilation fails.
- ❌ Do not `==` on reals — always epsilon (`abs(x-y) < 1e-8`).
- ❌ Do not raise the `0.9e-7` convective threshold or switch EOS to double — root cause is float32 `2⁻²³` quantization; needs promt.md procedure + approval.
- ❌ Do not "fix" FCT anti-diffusion (`CDY*0` in `barotropic_dynamics.f90`) — causes blowup.
- ❌ Do not use `grid_mode=TEST` basin for production claims.
- ❌ Do not set `kl1=1` without providing ERA5 d2m/tcc/precip fields.
- ❌ Before committing, check `.gitignore` — it blocks: `opencode.jsonc`, `.opencode/`, `docs/wiki/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`.

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
