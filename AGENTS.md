# AI Agent Guidelines for the AARI Iceberg Thermodynamic & Dynamics Model

## 1. Project Context

Modernized Fortran (2008/2018) reimplementation of the Dmitriev-Nesterov iceberg thermodynamic model (AARI, 1995–2001). Master's thesis at RSHU. Goal: stable modernized build via `fpm`, NetCDF I/O for ERA5 input and ParaView output, preserving original physics.

**Work driven by `promt.md` (full spec: physics rules, stages, forbidden changes) and tracked in `docs/wiki/ERA5_INTEGRATION_TODO.md`.** Read `promt.md` before changing any physics or forcing code.

## 2. Commands (gfortran 15, fpm 0.13)

```bash
# Build / run / test — ALWAYS needed: -I/usr/include
fpm build --flag "-I/usr/include"
fpm run    --flag "-I/usr/include"
fpm test   --flag "-I/usr/include"

# Strict debug run (bounds + FPE checks):
fpm run --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"
```

- `-I/usr/include` is required because `netcdf.mod` is installed at `/usr/include/netcdf.mod`, not in fpm's build tree. Omit it and compilation fails.
- `fpm test` runs 3 suites: `test/conv_test.f90` (15 checks), `test/eos_test.f90` (7 checks), and `test/check.f90` — a real validation suite that reads `data/runs/2020_Q1_test_heat_on/output/nc/results_day_final.nc` (default; optional CLI arg) and checks IEEE NaN/Inf, ERA5 fillValue (3.4028235e38) contamination, physical bounds, and wind/stress sign alignment. It SKIPs gracefully if the file is absent. It does NOT run the model itself.
- No CI, no lint, no formatter config beyond VS Code (`fprettify`/`fortls` extensions).
- Python tooling (ERA5 download) uses a conda env named `iceberg-thermodynamic-model` — see `docs/wiki/Python_environment.md`.

### Python Scripts (Key)

```bash
# ERA5 download (Barents domain default: "Barents Sea / Svalbard / Franz Josef Land iceberg-source domain", CDS area [90,10,70,70])
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py --year 2020 --month 1 --include-snowfall

# Historical Arctic-wide domain
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py --domain arctic --year 2020 --month 1

# Merge snowfall into instantaneous variables (separate CDS request)
conda run -n iceberg-thermodynamic-model python python/era5/merge_snowfall.py data/input/raw/era5/2020/2020_01/era5_2020_01.nc data/input/raw/era5/2020/2020_01/snowfall_2020_01.nc data/input/processed/era5/2020/2020_01/era5_2020_01_merged.nc

# Validate downloaded ERA5 file (reports lat/lon coverage vs domain/area)
conda run -n iceberg-thermodynamic-model python python/era5/check_era5.py data/input/raw/era5/2020/2020_01/era5_2020_01.nc
conda run -n iceberg-thermodynamic-model python python/era5/check_era5.py --domain arctic <file>

# Run manifest for a run (data/runs/<run_id>/); all analysis is run-aware
python python/analysis/run_manifest.py --run-id <run_id>

# Stage 5.5b output-integrity validation (calendar + canonical SI units)
python python/analysis/validate_q1_output.py --run-id 2020_Q1_test_heat_on

# Seasonal analysis (multi-month)
conda run -n iceberg-thermodynamic-model python python/analysis/seasonal_analysis.py --run-id 2020_Q1_test_heat_on

# Snowfall diagnostics
conda run -n iceberg-thermodynamic-model python python/analysis/snowfall_diagnostics.py --run-id 2020_Q1_test_heat_on

# Seasonal plots (from corrected CSVs)
conda run -n iceberg-thermodynamic-model python python/plotting/seasonal_plots.py --run-id 2020_Q1_test_heat_on

# SI round-trip unit test
conda run -n iceberg-thermodynamic-model python python/tests/test_units_roundtrip.py
```

## 3. Architecture & Entry Points

- `app/main.f90` — orchestrator. **`forcing_mode` is set to `forcing_mode_era5` at main.f90:77** (param.f90:160 defaults it to `forcing_mode_legacy`); `wind1()`/`era5_wind()` are branched by it (main.f90:263, 294), and `era5_open(trim(era5_input_file))` falls back to legacy if it fails (main.f90:233–250). **Run isolation (Stage 6.2):** CLI args `fpm run -- <run_id> [era5_file]` (main.f90:68–80); `src/run_config.f90:setup_run_dirs` builds `data/runs/<run_id>/output/{nc,csv,txt,logs,figures}` and sets `run_id`/`era5_input_file` (defaults: `run_id='2020_Q1_test_heat_on'`, `era5_input_file='data/input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc'`, param.f90).
- **`kl1 = 0` (main.f90:74) gates `heat()` off** — thermodynamics never runs (ERA5 test file has no d2m/tcc/precip; `humid`/`cloud`/`sfal` are declared in param.f90 but never assigned, so they stay 0). Do NOT set `kl1=1` without providing those fields.
- Exit at `nday1 == 42` (main.f90:273). Writes `data/runs/<run_id>/output/nc/results_day_00.nc` at start (main.f90:223), per-day `results_day_01.nc … NN.nc` inside the day loop (main.f90:742–744), and the final state to `results_day_final.nc` (main.f90:754). Per-day diagnostics appended to `daily_diagnostics.csv` in the run csv dir (main.f90:744, `write_daily_diagnostics` at main.f90:770).
- ERA5 run length auto-limits to available slices: `nperday` from `era5_time(1..2)` spacing, `mm1 = min(mm1, (era5_ntime - 1)/max(nperday, 1))` (main.f90:244–245). `era5_2020_01.nc` = 124 six-hourly slices → 30 model days.
- `src/param.f90` — global state: grid dims, all shared arrays, constants, forcing/grid mode switches. Modules access it via `use param` (no long argument lists).
- Grid dims: `is=132, js=104, ks=18`, `is1=133, js1=105, ks1=19`, `is3=134, js3=106`, `ngr=5`. Land mask value **`8888.0`**.
- Key modules: `netcdf_input` (ERA5 open/read/bilinear interp/time-index), `netcdf_output` (CF-1.10 diagnostic export incl. forcing fields), `wind_forcing` (`wind1` legacy geostrophic + `era5_wind`; smooths p via `smooth_filter`), `advection_2d`/`advection_3d_t/s` (FCT), `barotropic_dynamics` (advsh), `shallow_water` (barotropic time-split loop), `ice_stress`, `ice_deform`, `ice_redis`, `thermodynamics` (HEAT), `tide_forcing`, `grid_coupling`, `grid_masks`, `initial_conditions`.

## 4. Coding Standards

1. Modern Fortran only: no `GOTO`, no statement labels, no arithmetic `IF`; `implicit none`; `::` declarations; lower-case.
2. Every `.f90` file begins with a Russian documentation header: Module Name, Purpose, Physics, Dependencies.
3. **No direct real equality** — always epsilon: `if (abs(x - 8888.0) < 1e-8)`. Direct `==` on reals triggers `-Wcompare-reals`.
4. Use `use module, only: ...` to avoid collisions — e.g. `use shallow_water, only: shal, jjq, euu` (as in main.f90:26).
5. Dependencies go in `fpm.toml`: `[build]` needs both `link = ["netcdff"]` **and** `external-modules = ["netcdf"]`; stdlib is a git dependency (`stdlib.git` + `stdlib.branch = "stdlib-fpm"`, downloaded into `build/dependencies/`). Do not drop the `netcdff`/`netcdf` pair.
6. Before touching physics follow promt.md procedure items 5–6 (find historical algorithm, map arrays, verify units/dimensions, place in time loop, check module impact; never change equations just to pass tests). Document any new assumption/unit conversion inline.

## 5. Build & Runtime Quirks

- **Module import conflicts:** `param` exposes many names. Use `use module, only: ...` to avoid collisions.
- **Units:** CGS for hydrodynamics (`dx` in cm, `U/V` in cm/s, `dt` in s), SI for thermodynamics (`T` °C, `S` as **mass fraction 0.033–0.035**, not PSU). **External NetCDF interface is canonical SI (Stage 5.5b):** `temperature`/`air_temp` K, `salinity_mass_fraction` 1 (kg/kg), `density_anomaly` kg m-3 (anomaly ρ−1.02, NOT absolute), u/v/w/wind_x/y m s-1, tau_x/y Pa, dp_x/y Pa m-1, air_press Pa, `unit_system` global attr. Conversions only at the output boundary; internal CGS/Celsius unchanged. Python converts to presentation units via `python/analysis/units.py`.
- **ERA5 units:** u10/v10 m/s → windx1/windy1 cm/s (×100); msl Pa → p1/patm hPa (×0.01); t2m K → tatm °C (−273.15); stress `cof=(1.1+0.04·V·1e-2)·V²·1.29e-6` dyn/cm². Wind direction from actual u10/v10 (not geostrophic); pressure gradient `dpx=(p1(i,j+1)−p1(i,j))·1e3/dxx`, `dxx=13.89e5 cm`.
- **ERA5 input path (Stage 6.2, run-based):** `main.f90` opens `trim(era5_input_file)` (default `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc`, overridable via `fpm run -- <run_id> <era5_file>`). ERA5 forcing IS active on a plain `fpm run` when that file is present; otherwise the model logs `WARNING: ERA5 input failed, falling back to legacy forcing.`
- **Grid modes (param.f90:165–167):** `grid_mode_test` (default) = synthetic FI/DL 66–82°N / 30–63°E marked TEST ONLY; `grid_mode_real` reads KOORD.DAT and `STOP`s if missing (grid_coupling.f90:396). The Stage 6.2 ERA5 Barents domain (`--domain barents`, CDS area [90,10,70,70]) does NOT change the model grid.
- **Axis conventions:** X ↔ `j` ↔ `u`; Y ↔ `i` ↔ `v`; Y-axis inverted (north at `j=1`).
- **Missing input files are normal:** `GRM2`, `hhh.bar`, `FI1DL1.DAT`, `DAV4_5.98`, `1_k.ice` absent; code logs warnings and falls back to synthetic basin fields.
- **`.gitignore` ignores `AGENTS.md`, `promt.md`, `opencode.jsonc`, `.opencode/`, `docs/wiki/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`** — intentionally untracked. `src/convective_adjustment.f90.bak` is a stale identical copy; ignore it.

## 6. Current State & Next Stages

### Completed Stages (merged to `main`)

| Stage      | Description                                                                                                                                                | Key Commits                                |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **1**      | Barotropic → 3D velocity coupling (`u2=up2/hu`)                                                                                                            | `fffa04d`                                  |
| **3.1**    | Eckart EOS + unit tests                                                                                                                                    | `3c26f0b`                                  |
| **3.2**    | Convective adjustment + unit tests                                                                                                                         | `56ddc04`                                  |
| **3.3**    | Blocks 200/210/280 (3D momentum, vertical viscosity, barotropic coupling)                                                                                  | `45a472c`                                  |
| **3.3a**   | Convective adjustment root cause analysis (cyclic mixing on ki=18)                                                                                         | `24d04b3`                                  |
| **3.3a-2** | Formal stop-state verification: physically converged / algorithmically cyclic                                                                              | documentation                              |
| **3.4**    | Baroclinic–barotropic coupling verification (block 280 math verified)                                                                                      | —                                          |
| **4.1**    | Monthly ERA5 integration on TEST grid (2-day run, diagnostics, report)                                                                                     | `9405ec3`                                  |
| **4.2**    | January 2020 ERA5 (hourly) + daily output + Python analysis/plotting/report                                                                                | `2ee3dfe`, `71d3312`, `a2c981b`, `28ebd59` |
| **4.3**    | Convective guard-cycling ROOT CAUSE (float32 `2^-23` EOS quantization vs threshold `0.9e-7`); monitoring-only event log + probes + analysis                | (Stage 4.3 commits)                        |
| fmt        | Bulk formatting pass (15 files)                                                                                                                            | `8391892`                                  |
| **5.1**    | HEAT input audit (22 variables, ERA5 mapping, risks, kl1=0 remains)                                                                                        | documentation                              |
| **5.2**    | ERA5 d2m/tcc/snowfall integration, humidity/cloud mapping, NetCDF output                                                                                   | `79c5322`                                  |
| **5.3**    | 30-day Jan 2020 HEAT ON, heat budget, OFF vs ON comparison, decision A                                                                                     | `98b1234`                                  |
| **5.4**    | ERA5 snowfall acquisition (step parameter), merge, diagnostics, unit tests                                                                                 | `fa5afe9`                                  |
| **5.5**    | 91-day Jan–Mar 2020 HEAT ON, month-boundary continuity, heat budget                                                                                        | `c5cc3d2`                                  |
| **5.5a**   | Post-processing integrity: run manifest, dedup diagnostics, snowfall fix, plots                                                                            | `fa5afe9`                                  |
| **5.5b**   | Q1 output & unit audit: calendar, canonical SI NetCDF interface, EOS-verified extremes                                                                     | (Stage 5.5b commits)                       |
| **6.2**    | Barents research-domain config (CDS area [90,10,70,70]), run-based data architecture, output isolation, run-aware Python, data cleanup, SI round-trip test | (Stage 6.2 commits)                        |
| **6.3**    | Source tree cleanup, reproducible project layout, dependency graph, FPM audit                                                                              | `1e565db`, `54d9b18`, `84123a8`            |
| **6.3b**   | Run/calendar semantics audit & fix (leap year, day N = start + N days)                                                                                     | `0101957`                                  |

### Active / Pending

- **Stage 3.5/6.1:** Real grid/bathymetry transition — DEFERRED until `KOORD.DAT` and `hhh.bar` provided. Model remains in validated `grid_mode=TEST`.
- **Convective adjustment:** 1000-iteration guard (`iter_count > 1000`) preserved as correct workaround. **Root cause (Stage 4.3):** EOS `RO = 1.0/(0.698+aa/bb) − 1.02` is float32-quantized on the `2^-23 ≈ 1.19e-7` grid (intermediate `X ∈ [1,2)`); threshold `0.9e-7 < 2^-23` ⇒ convergence requires RO(k)==RO(k+1) exactly; 1-ulp residuals re-invert forever. Do NOT raise the threshold or switch EOS to double precision without promt.md procedure + approval. Stage 4.2 adds **monitoring only** (`ca_reset`/`ca_stats` counters, `daily_diagnostics.csv`); Stage 4.3 adds guard-event CSV (`convective_guard_events.csv`, cap 100/day) + `ca_probe_inversions` (A after advection / D after conv_adj).
- **Thermodynamics (`heat()`):** gated by `kl1=0`; enabling requires ERA5 d2m/tcc/precip fields or documented TEST assumption.
- **Full-month ERA5 run:** DONE for January 2020 (30 model days limited by slice coupling, not 31). Other months: use `python/era5/download_era5.py` and run with `fpm run -- <run_id> <era5_file>`.
- **Barents-domain ERA5 download (Stage 6.2):** configuration/validator/defaults ready (`--domain barents`, area [90,10,70,70]); actual download pending CDS queue. `data/input/raw/era5/era5_test.nc` preserved for regression.
- **Stage 6.4:** ERA5 Barents domain download (CDS queue pending).

### Calendar Semantics (Fixed in Stage 6.3b)

**Critical:** Model integration day `d` (1-indexed) = `start_date + d days`, NOT `start_date + (d-1) days`.

- `day_00` = initial state at `start_date`
- `day_01` = after 1 integration day → `start_date + 1 day`
- `day_90` = after 90 integration days → `start_date + 90 days` (2020-03-31 for Q1 2020)
- `results_day_final.nc` = duplicate of `day_90`

All Python analysis scripts (`run_manifest.py`, `validate_q1_output.py`, `seasonal_analysis.py`) now use this semantics. The old hardcoded month boundaries in `seasonal_analysis.py` (leap year bug) were replaced with calendar-aware `datetime` arithmetic.

### Known Limitations

- `grid_mode=TEST` synthetic grid is NOT a real basin — never use for production claims.
- FCT anti-diffusion in `advsh` intentionally disabled (zeroed X-block intermediates + `CDY*0`); "restoring" causes blowup.
- `heat()` never runs without `kl1=1` + d2m/tcc/precip fields.
- Thermodynamics unit `S` is mass fraction 0.033–0.035, not PSU.
- ERA5 forcing is active only when the run's `era5_input_file` is present (default `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc`); otherwise legacy fallback.
- January 2020 run covers 30 model days (slice-coupling limit `(era5_ntime-1)/nperday`), not 31.
- Convective adjustment guard hits grow with time (5,467/month, max_iter=1001) — root cause: float32 `2^-23` EOS quantization vs threshold `0.9e-7` below the grid (Stage 4.3). Monitored, NOT fixed (see §8 constraints).

### Validation (All Pass)

| Check                                          | Result                                                                |
| ---------------------------------------------- | --------------------------------------------------------------------- |
| `fpm build -Wall -Wextra`                      | ✅ Pass                                                               |
| `fpm test` (EOS 7/7)                           | ✅ Pass                                                               |
| `fpm test` (convective 15/15)                  | ✅ Pass                                                               |
| `fpm test` (NetCDF, `results_day_final.nc`)    | ✅ Pass                                                               |
| `fpm run -fcheck=all -ffpe-trap` (30-day ERA5) | ✅ Clean, no FPE/NaN/Inf                                              |
| January 2020 ERA5 run                          | ✅ Completes, writes `results_day_01..30.nc` + `results_day_final.nc` |
| Q1 2020 HEAT ON (90 days)                      | ✅ Completes, all validation PASS                                     |
| SI round-trip unit test                        | ✅ Pass                                                               |

## 7. How to Investigate

**Read sources in order:**

1. `promt.md` — full physics spec, stage rules, forbidden changes
2. `docs/wiki/Stage3.3_mapping.md` — historical → current mapping table
3. `docs/wiki/Stage3.3_validation.md` — validation report
4. `docs/wiki/Stage3.3_convective_convergence.md` — convective adj root cause + stop-state verification
5. `docs/wiki/Stage4.3_convective_root_cause.md` — float32 quantization root cause (Stage 4.3)
6. `docs/wiki/Stage3.4_coupling_verification.md` — block 280 math verification
7. `docs/wiki/Stage3.5_real_grid.md` — real grid status and file search results
8. `docs/wiki/Stage4.1_monthly_era5_test.md` — monthly integration report
9. `docs/wiki/Stage4.2_january2020.md` — January 2020 ERA5 + Python workflow report
10. `docs/wiki/ERA5_INTEGRATION_TODO.md` — live TODO tracking
11. `docs/wiki/Fortran_dependencies.md` — NetCDF-Fortran + stdlib deps
12. `AGENTS.md` — this file (current guidance)
13. `fpm.toml` — build config (netcdff/link + external-modules/netcdf + stdlib)
14. `src/param.f90` — global state, grid mode switches, constants
15. `app/main.f90` — orchestrator, forcing_mode branching, exit at nday1==42

**If architecture unclear:** Inspect representative files — `main.f90`, `param.f90`, `netcdf_input.f90`, `wind_forcing.f90` — to find entrypoints and execution flow.

**Prefer executable sources over prose:** `fpm test`, `fpm run`, and build artifacts are the ground truth. If docs conflict with build/test results, trust the executable source.

## 8. What NOT Do (Constraints Honor)

- ❌ Do not set `kl1=1` without providing ERA5 d2m/tcc/precip fields
- ❌ Do not use `grid_mode=TEST` basin for production claims
- ❌ Do not "fix" FCT anti-diffusion (`CDY*0` in `barotropic_dynamics.f90`) — causes blowup
- ❌ Do not directly `==` real values — always use epsilon (`abs(x-y) < 1e-8`)
- ❌ Do not modify `convective_adjustment` iteration limit without proper convergence proof
- ❌ Do not raise the `0.9e-7` threshold or switch EOS to double precision — root cause is float32 `2^-23` quantization (Stage 4.3); any fix needs promt.md procedure + approval
- ❌ Do not omit `-I/usr/include` — compilation will fail
- ❌ Do not add fields "just in case" without promt.md justification
- ❌ **Before committing, always check `.gitignore`** — it explicitly blocks: `docs/wiki/`, `AGENTS.md`, `promt.md`, `opencode.jsonc`, `.opencode/`, `docs/wiki/ERA5_INTEGRATION_TODO.md`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`. Do NOT commit these.

## 8b. Post-Processing Integrity (Stage 5.5a)

**Critical:** Never use `glob("data/output/results_day_*.nc")` without a run manifest — it picks up stale `results_day_00.nc`, `results_day_final.nc`, and outputs from previous runs.

**Always:**

1. Generate a run manifest: `python python/analysis/run_manifest.py`
2. Validate it: `python python/analysis/run_manifest.py` (must PASS)
3. Pass manifest path to analysis: `--manifest data/output/run_manifest_2020_Q1_HEAT_ON.json`

**Snowfall variable name:** The Fortran reader expects `sf` in the merged ERA5 NetCDF (not `era5_snowfall_rate`). The merge script `python/era5/merge_snowfall.py` writes `sf` with units `m s-1`.

**Run manifest:** Always regenerate after a model run: `python python/analysis/run_manifest.py` (validates 90 days, checks for duplicates/gaps, excludes `results_day_00.nc` and `results_day_final.nc`).

## 9. Repository Structure (Top-Level)

```
AGENTS.md          <- this file (verified useful, preserved)
promt.md           <- full physics spec (read before changes)
fpm.toml           <- build config (link netcdff + external-modules netcdf + stdlib git dep)
README.md          <- short project overview
environment.yml    <- conda env (iceberg-thermodynamic-model)
requirements.txt   <- pip deps (cdsapi, netCDF4, xarray, ...)
docs/wiki/
  Stage3.3_mapping.md      <- historical→current mapping
  Stage3.3_validation.md   <- validation report
  Stage3.3_convective_convergence.md  <- convective adj root cause
  Stage3.4_coupling_verification.md   <- block 280 math verification
  Stage3.5_real_grid.md     <- real grid deferral status
  Stage4.1_monthly_era5_test.md <- monthly integration report
  Stage4.2_january2020.md  <- January 2020 ERA5 + Python workflow report
  Stage4.3_convective_root_cause.md <- float32 quantization root cause (Stage 4.3)
  Stage5.1_heat_input_audit.md      <- HEAT input audit report
  Stage5.2_heat_enablement.md       <- HEAT enablement report
  Stage5.3_monthly_heat_validation.md <- 30-day heat validation
  Stage5.4_snowfall.md              <- snowfall integration report
  Stage5.5_multimonth_integration.md <- 91-day integration report
  Stage5.5a_postprocessing_integrity.md <- post-processing integrity report
  Stage5.5b_units.md              <- full unit inventory (canonical SI external)
  Stage5.5b_q1_output_and_units_audit.md <- Q1 calendar + units + extremes audit report
  Stage6.1_real_grid.md     <- real grid deferral status
  Stage6.2_barents_domain.md      <- Barents domain configuration
  Stage6.2_data_cleanup.md        <- data reorganization details
  Stage6.3b_run_calendar_semantics.md <- calendar semantics audit & fix
  ERA5_INTEGRATION_TODO.md <- live integration tracking
  ERA5_download.md          <- CDS API + raw data location
  Python_environment.md     <- conda env setup
  Fortran_dependencies.md   <- NetCDF-Fortran + stdlib deps
src/
  equation_of_state.f90  <- EOS module (Stage 3.1)
  convective_adjustment.f90  <- convective adj module (Stages 3.2+3.3)
  param.f90              <- global state, grid mode, constants
  netcdf_input.f90       <- ERA5 open/read/interp
  netcdf_output.f90      <- CF-1.10 diagnostic export
  wind_forcing.f90       <- wind1 + era5_wind
  smooth_filter.f90      <- Laplacian smoothing of p fields
  advection_2d.f90       <- FCT scheme
  advection_3d_t.f90     <- 3D advection
  advection_3d_s.f90     <- 3D advection (s)
  barotropic_dynamics.f90 <- blocks 200/210/280
  shallow_water.f90      <- barotropic time-split loop
  ice_stress.f90         <- ice stress
  ice_deform.f90         <- ice deformation
  ice_redis.f90          <- ice redeposition
  initial_conditions.f90 <- initial state setup
  run_config.f90         <- run isolation (run dirs, defaults)
app/
  main.f90               <- orchestrator (forcing_mode, blocks, exit nday1==42)
test/
  eos_test.f90           <- EOS unit tests (7 checks)
  conv_test.f90          <- convective adj unit tests (15 checks)
  check.f90              <- NetCDF validation suite
  thermo_input_test.f90  <- thermodynamic input unit tests (8 checks)
  snowfall_test.f90      <- snowfall conversion unit tests (9 checks)
python/
  era5/download_era5.py  <- CDS API downloader (--domain barents default, new layout)
  era5/check_era5.py     <- xarray inspection + domain coverage validation
  era5/merge_snowfall.py <- merges snowfall accumulations into instantaneous file (writes `sf`)
  analysis/run_context.py  <- RunContext, resolve_run(), add_run_args()
  analysis/run_manifest.py <- run-aware manifest generation/validation
  analysis/validate_q1_output.py <- Q1 output integrity (calendar + SI units)
  analysis/units.py      <- SI → presentation unit conversions
  analysis/seasonal_analysis.py <- multi-month (leap-year fixed)
  analysis/heat_diagnostics.py, snowfall_diagnostics.py, profiles.py
  analysis/convective_analysis.py, eos_precision_analysis.py
  plotting/plots.py, seasonal_plots.py, convective_plots.py
  tests/test_units_roundtrip.py  <- SI round-trip unit test
data/
  input/raw/era5/2020/2020_01/  <- raw + snowfall (per month)
  input/raw/era5/2020/2020_02/  <- raw + snowfall
  input/raw/era5/2020/2020_03/  <- raw + snowfall
  input/raw/era5/era5_test.nc   <- regression dataset (12 steps)
  input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc  <- Q1 merged
  runs/<run_id>/output/{nc,csv,txt,logs,figures}/  <- run-isolated outputs
  archive/{legacy,test,pre_cleanup}/  <- moved legacy data
  output/  <- empty (legacy, not used)
```

## 10. Quick Test Reference

```bash
# Single fastest verification
fpm test --flag "-I/usr/include"  # 22 unit checks (15 conv + 7 EOS) + NetCDF suite

# Strict build
fpm build --flag "-I/usr/include -Wall -Wextra"

# Strict run (FPE + NaN/Inf bounds)
fpm run --flag "-I/usr/include -fcheck=all -ffpe-trap=invalid,zero,overflow"

# ERA5 run (input path already set to data/input/raw/era5/era5_2020_01.nc; no copy needed)
fpm run --flag "-I/usr/include"  # with timeout, watch output

# Run specific test suites
fpm test --flag "-I/usr/include" eos_test      # 7 EOS checks
fpm test --flag "-I/usr/include" conv_test     # 15 convective checks
fpm test --flag "-I/usr/include" thermo_input_test  # 8 thermo input checks
fpm test --flag "-I/usr/include" snowfall_test    # 9 snowfall checks

# Seasonal analysis (multi-month)
conda run -n iceberg-thermodynamic-model python python/analysis/seasonal_analysis.py --run-id 2020_Q1_test_heat_on

# Snowfall diagnostics
conda run -n iceberg-thermodynamic-model python python/analysis/snowfall_diagnostics.py --run-id 2020_Q1_test_heat_on

# Seasonal plots (from corrected CSVs)
conda run -n iceberg-thermodynamic-model python python/plotting/seasonal_plots.py --run-id 2020_Q1_test_heat_on

# Run manifest generation/validation
python python/analysis/run_manifest.py --run-id 2020_Q1_test_heat_on

# Q1 output integrity validation (calendar + canonical SI units)
python python/analysis/validate_q1_output.py --run-id 2020_Q1_test_heat_on

# SI round-trip unit test
conda run -n iceberg-thermodynamic-model python python/tests/test_units_roundtrip.py
```
