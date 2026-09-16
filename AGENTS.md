# AGENTS.md — AARI Iceberg Thermodynamic & Dynamics Model

Current information for AI agents and developers: behavioral rules, critical
constraints, commands, units, and documentation routing. Process rules — in
`RULES.md`, style — in `STYLE.md`, history — in `CHANGELOG.md`, documentation
map — in `docs/README.md`.

## Documentation routing (read before working)

| Question                           | Document                                   |
| ---------------------------------- | ------------------------------------------ |
| Full documentation map             | `docs/README.md`                           |
| Development process rules          | `RULES.md`                                 |
| Code and documentation style       | `STYLE.md`                                 |
| Current constraints and debt       | `KNOWN_ISSUES.md`                          |
| History of significant changes     | `CHANGELOG.md`                             |
| Model description                  | `docs/model/model_description.md`          |
| Physics status (A/B/C, switches)   | `docs/model/model_physics_status.md`       |
| Equations and conventions          | `docs/model/model_equation_ledger.md`      |
| Stage 10 modernization plan        | `docs/model/stage10_modernization_plan.md` |
| Active validation reports          | `docs/validation/INDEX.md`                 |
| Historical archive (stages 3–10)   | `docs/wiki/INDEX.md`                       |
| Key decisions                      | `docs/DECISIONS.md`                        |
| Bibliography and literature matrix | `docs/references/README.md`                |

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
fpm test --flag "-I/usr/include" iceberg_test_10p10_three_equation  # Stage 10.10 three-equation (25 checks)
fpm test --flag "-I/usr/include" iceberg_test_10p11_natural_convection  # Stage 10.11.2 natural-convection audit (23 checks)
fpm test --flag "-I/usr/include" iceberg_test_10p12_thermal_evolution   # Stage 10.12 internal thermal (21 checks)
fpm test --flag "-I/usr/include" iceberg_test_10p13_low_flow            # Stage 10.13 low-flow closure (23 checks)
python python/tests/test_three_equation.py                        # Stage 10.10/10.10.1 Python (65 checks)
python python/tests/test_three_equation_natural.py                # Stage 10.11 Python (70 checks)
python python/tests/test_internal_thermal_evolution.py            # Stage 10.12 Python (35 checks)
python python/tests/test_low_flow.py                              # Stage 10.13 Python prototype (167 checks)
python python/validation/low_flow_fortran_comparison.py           # Stage 10.13 Fortran/Python comparison (56 checks)
```

fpm 0.13.0-alpha: `fpm build` compiles only sources reachable from targets;
iceberg modules compile as part of `fpm test`. **Always `rm -rf build` before
`fpm test`** (clean rebuild, protection against stale libraries).

No lint, no formatter beyond VS Code (`fprettify`/`fortls`). CI: GitHub
Actions (`.github/workflows/ci.yml`) runs the full fpm test battery (54
targets) and Python validation checks. Python tooling uses conda env
`iceberg-thermodynamic-model`.

## Unit Systems (MIXED — would be missed)

| Domain         | Units         | Variables                                                                                                            |
| -------------- | ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Hydrodynamics  | **CGS**       | `dx` cm, `U/V` cm/s, `dt` s, `cof` dyn/cm²                                                                           |
| Thermodynamics | **SI**        | `T` °C, `S` mass fraction 0.033–0.035 (**NOT PSU**)                                                                  |
| NetCDF output  | **SI**        | `temperature` K, `salinity_mass_fraction` kg/kg, `density_anomaly` kg m⁻³ (ρ−1.02), `u/v/w` m/s, `tau` Pa, `dp` Pa/m |
| ERA5 input     | **converted** | u10/v10 m/s → ×100 → cm/s; msl Pa → ×0.01 → hPa; t2m K → −273.15 → °C                                                |

Conversions only at the NetCDF output boundary (`netcdf_output.f90`). Internal CGS/Celsius unchanged. Python converts to presentation units via `python/analysis/units.py`.

## Architecture

- **`app/main.f90`** — orchestrator. `forcing_mode = forcing_mode_era5` (line 131). `kl1 = 1` (line 128) enables `heat()`. Exit at `nday1 == 91` (line 404). CLI: `fpm run -- <run_id> [era5_file]`.
- **`src/param.f90`** — global state: all shared arrays, constants, grid dims (`is=132, js=104, ks=18`, `is1=133, js1=105`, `ngr=5`). Land mask = **`8888.0`** (use epsilon: `abs(x-8888.0) < 1e-8`, never `==`).
- **ERA5 path:** `era5_input_file` defaults to `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc`. Falls back to legacy if absent.
- **Grid modes:** `grid_mode_real` (default) reads `KOORD.DAT` (FATAL STOP if missing) and `hhh.bar` (synthetic-basin fallback if missing). `grid_mode_test` generates synthetic grid TEST ONLY.
- **Axis conventions:** X ↔ `j` ↔ `u`; Y ↔ `i` ↔ `v`; Y-axis inverted (north at `j=1`).
- **Key modules:** `netcdf_input` (ERA5 read/bilinear interp), `netcdf_output` (CF-1.10 export), `wind_forcing` (legacy + ERA5), `advection_2d/3d_t/3d_s` (FCT), `barotropic_dynamics`, `shallow_water`, `ice_stress/deform/redis`, `thermodynamics`, `grid_coupling`, `initial_ocean_reader` (Stage 7.7 EN4 reader), `initial_conditions`.

### Iceberg Model Architecture (Stage 9.3)

- **`src/iceberg_types.f90`** — types, constants (ρᵢ, ρ_w, C_Dₐ, C_D_w, C_BASAL, C_LATERAL, L_f, etc.), state vector, switches (thermal evolution, low-flow closure, basal-melt scheme).
- **`src/iceberg.f90`** — main orchestrator: `iceberg_init`, `iceberg_step`, `iceberg_update_geometry`, lat/lon update each step (`model_coords_to_latlon`).
- **`src/iceberg_geometry.f90`** — volume, mass, draft, areas, buoyancy check, grounding, mass budget partitioning.
- **`src/iceberg_forcing.f90`** — horizontal bilinear interp (model grid), vertical interp/extrapolation to draft, ERA5 atmos interp, Method A/B current integration.
- **`src/iceberg_thermodynamics.f90`** — surface melt (atmospheric energy partition), basal melt (bulk / three-equation / three-equation+natural / low-flow paths), internal thermal evolution.
- **`src/iceberg_dynamics.f90`** — wind/water drag (Method A: layer-integrated, Method B: depth-averaged), semi-implicit Coriolis, pressure gradient (optional).
- **Forcing:** OFFLINE/PRESCRIBED only. ERA5 (atmos), EN4 (ocean T/S), IBCAO (bathymetry). No two-way coupling.
- **State vector:** `[x, y, u, v, L, W, H]` (7 prognostic). Diagnostic: D, M, areas, draft, sail/wetted.
- **Melt coefficients:** compile-time constants in `iceberg_types.f90` — require rebuild to change.

## Constraints (DO NOT)

- ❌ Do not omit `-I/usr/include` — compilation fails.
- ❌ Do not `==` on reals — always epsilon (`abs(x-y) < 1e-8`).
- ❌ Do not raise the `0.9e-7` convective threshold or switch EOS to double — root cause is float32 `2⁻²³` quantization; needs RULES.md procedure + approval.
- ❌ Do not "fix" FCT anti-diffusion (`CDY*0` in `barotropic_dynamics.f90`) — causes blowup.
- ❌ Do not use `grid_mode=TEST` basin for production claims.
- ❌ Do not set `kl1=1` without providing ERA5 d2m/tcc/precip fields.
- ❌ Do not modify canonical ocean/sea-ice physics (Block 200/210/280, barotropic solver, EOS, grid, ERA5, bathymetry, thermodynamics).
- ❌ Iceberg forcing must remain OFFLINE/PRESCRIBED. No two-way coupling.
- ❌ No advanced physics (internal 3D temperature, wave erosion, sea-ice capture, rollover, fracture, multi-iceberg) without a dedicated stage.
- ❌ Melt coefficients are compile-time constants — require rebuild to change.
- ❌ Do not reintroduce an arbitrary velocity floor to avoid numerical issues (Stage 10.13 policy).
- ❌ Before committing, check `.gitignore` — it blocks: `opencode.jsonc`, `.opencode/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`. **Exceptions:** the curated Stage 10.8.2 observational dataset is versioned (`data/validation/observations/` is un-ignored); `docs/wiki/` is tracked (archive) except `docs/wiki/ERA5_INTEGRATION_TODO.md` (explicitly ignored, live local TODO).
- ❌ Do not delete root-level input files: `KOORD.DAT`, `hhh.bar` (real grid) and `1_1.ice`..`1_5.ice` (ice initialization, read from the working directory) — required by the model, gitignored; the grid files point to `data/input/generated/real_grid/`.
- ❌ Do not commit/push unless the user explicitly requests it.

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
# Creates: KOORD.DAT, hhh.bar, reconstruction_metadata.json
#          (+ diagnostic 1_1.ice .. 1_5.ice) → data/input/generated/real_grid/
# NOTE: root-level KOORD.DAT / hhh.bar are NOT created automatically —
# create symlinks (or copies) to data/input/generated/real_grid/ before
# running in grid_mode_real (FATAL STOP without KOORD.DAT).
```

ERA5 download: `conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py --year 2020 --month 1 --include-snowfall`

## Active Constraints Worth Preserving

- **Convective adjustment:** 1000-iteration guard. Root cause: EOS float32 quantization `2⁻²³ ≈ 1.19e-7` vs threshold `0.9e-7`. Monitored via `ca_reset`/`ca_stats` counters. Details: `docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md`, `docs/wiki/stages/stage04/Stage4.4_precision_study.md`.
- **Ice-ocean drag singularity:** `hht ∼ 0.01 m` causes positive feedback. Guard `hht<0.01 → u=v=0` interrupts it. See `docs/wiki/stages/stage07/Stage7.3_stability_investigation.md`.
- **ERA5 coverage:** fully covered after the Stage 7.6C.2 domain expansion
  [64.21–85.04 °N, 8.33–76.32 °E] — 100% of the 10,966 required cells, 0
  uncovered (`era5_coverage_test`). Historical gap (5.2%, 591/11,330 cells,
  Stage 6.5) is resolved. See
  `docs/wiki/stages/stage07/Stage7.6C.2_ERA5_forcing_expansion_and_hot_run.md`.
- **FCT anti-diffusion intentionally disabled** in `advsh` — zeroed X-block intermediates + `CDY*0`.
- **`grid_mode=TEST`** synthetic grid is NOT a real basin.
- **Missing input files are normal:** `GRM2`, `FI1DL1.DAT`, `DAV4_5.98`, `1_k.ice` absent; code falls back to synthetic fields. See `docs/wiki/stages/stage06/Stage6.4_missing_historical_files.md`.
- **Thomas algorithm vertical viscosity:** Can reach 8.5×10⁵ cm²/s at k=2 with realistic EN4 init → matrix ill-conditioning → blowup. Do not "fix" without physics review.
- **Coriolis:** semi-implicit solver has 8% period error at Δt=3600s — numerical damping; convergence study needed. See `docs/wiki/stages/stage09/Stage9.3_Scientific_Verification_and_Calibration.md`.
- **Wind drift ratio** 0.08% (with Coriolis) vs literature 1–2% — needs C_D calibration. Same report.

## Stage summary map (actuality = model docs, not here)

| Stage                 | Summary                                                                                              | Report (details)                                                                                                                                                                                                           |
| --------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3–8                   | Model restoration, ERA5, real grid, ocean initialization                                             | `docs/wiki/INDEX.md` (stage03–stage08)                                                                                                                                                                                     |
| 9                     | Minimal Lagrangian iceberg model: verification 11/11, TEST_11 (74.5% mass loss, 0.013% budget error) | `docs/wiki/stages/stage09/`                                                                                                                                                                                                |
| 10.1–10.6             | Solar geometry, surface T, fluxes, phase partition, EOS-80, heat transfer                            | `docs/model/stage10_modernization_plan.md` (Completed stages)                                                                                                                                                              |
| 10.7–10.9             | Basal-melt validation, Python layer, observations, calibration assessment (not calibrated)           | `docs/validation/stage10.7_basal_melt_validation.md`, `docs/validation/stage10.8.1_python_validation.md`, `docs/validation/stage10.8.2_observational_validation.md`, `docs/validation/stage10.9_calibration_assessment.md` |
| 10.10/10.10.1         | Three-equation interface (H&J99/J2010), mass/salt correction; 25 Fortran + 65 Python checks          | `docs/validation/stage10.10_three_equation_interface.md`                                                                                                                                                                   |
| 10.11/10.11.2/10.11.3 | Natural convection (selectable); audit: cap always active, 10.8.2 gap not closed; 23 + 70 checks     | `docs/validation/stage10.11_natural_convection.md`, `docs/validation/stage10.11.2_natural_convection_audit.md`, `docs/validation/stage10.11.3_natural_convection_physics_audit.md`                                         |
| 10.12                 | Internal temperature (two-node lumped, switch fully gates); 21 + 35 checks                           | `docs/validation/stage10.12_internal_thermal_evolution.md`                                                                                                                                                                 |
| 10.13 (A–C)           | Low-flow closure: research parameterization behind an OFF-by-default switch; 23 + 56 + 167 checks    | `docs/validation/stage10.13_diffusion_limited_low_flow_design_note.md`, `docs/validation/stage10.13_phase_b_results.md`, `docs/validation/stage10.13_phase_c_results.md`                                                   |

Current physics status and switches — ALWAYS check
`docs/model/model_physics_status.md` and `docs/DECISIONS.md`, not this file
and not old reports.

## OpenCode Environment

OpenCode version: **1.18.30**

### Plugins

| Plugin                           | Purpose                                                  |
| -------------------------------- | -------------------------------------------------------- |
| oh-my-opencode                   | OpenCode agent orchestration / skill utilities           |
| opencode-dynamic-context-pruning | context-window management (pruning) during long sessions |
| opencode-git-master              | git operations integration (commits, history, rebase)    |
| opencode-supermemory             | persistent memory (project/user knowledge recall)        |

### Roles

| Role       | Kind         | Use for                                                                                                                                    |
| ---------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Prometheus | Plan Builder | decomposition of complex tasks; stage planning; dependency/risk identification; preparation before implementation                          |
| Hephaestus | Deep Agent   | deep implementation; complex debugging; detailed repository work; multi-step technical execution                                           |
| Sisyphus   | Ultraworker  | intensive multi-step execution; integration; persistence across a complex task; bringing implementation through verification to completion |

## Skills and MCP Tools (MANDATORY)

The project defines **8 skills** (`.opencode/skills/`) and the OpenCode environment
exposes **12 MCP servers** (`opencode.jsonc` + global config) plus **2 security
skills** (`/security-review`, `/security-research`). Models MUST load the relevant
skill and prefer the MCP tools over ad-hoc/generic implementations for the tasks
below. Do not hand-roll equivalents of an available skill/MCP; loading the skill
is part of normal workflow.

### Skills (load via the `skill` tool when the task matches)

| Skill                   | Use when                                                                                                                                          | Purpose                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| academic-paper          | writing/editing an academic paper, abstracts, lit-review, citations, LaTeX/DOCX/PDF                                                               | 12-agent paperwriting pipeline (plan/outline/revision/formats) |
| academic-paper-reviewer | reviewing a manuscript, referee report, re-review                                                                                                 | 5-persona peer review (EIC/peers/Devil's Advocate)             |
| academic-pipeline       | end-to-end research → paper → integrity → review → finalize                                                                                       | orchestration of deep-research + academic-paper + reviewer     |
| deep-research           | literature review, fact-check, systematic review, meta-analysis, 3W scan                                                                          | 13-agent research pipeline with source verification            |
| data-scientist          | analytics, ML, statistical modeling, business intelligence                                                                                        | advanced data analysis                                         |
| math-modeling           | math-modelling competitions (MCM/ICM/美赛/国赛), problem decomposition                                                                            | modeling workflow to LaTeX paper                               |
| coding-agent            | programmatically running Codex/Claude Code/OpenCode/Pi agents                                                                                     | external coding-agent control                                  |
| humanizer               | de-AIing prose (review/revise for "AI tells")                                                                                                     | rewrite AI-sounding text                                       |
| /security-review        | security review of source code, dependency/configuration risks, CI/CD security, unsafe file/process/network behavior, secrets/credential exposure | team-mode security audit of the codebase                       |
| /security-research      | researching security advisories, CVEs, dependency vulnerabilities, external security guidance, current security info requiring web research       | web-based security threat research                             |

### MCP servers (invoke the matching tool set)

| Server              | Use for                                                                           | Examples                                         |
| ------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------ |
| websearch           | real-time web search (auto/fast/deep)                                             | current events, recent data, web facts           |
| context7            | current library/framework/API docs (resolve id → query docs)                      | Fortran/fpm/gfortran/netcdf, CLI tooling         |
| firecrawl           | web research: search, scrape, map, crawl; `firecrawl_research_*` scan paper index | literature/DOI verification, data-source checks  |
| fetch               | plain URL content retrieval (markdown/text)                                       | single static pages                              |
| grep_app            | GitHub code search over public repos (grep.app index)                             | real-world usage examples                        |
| github              | GitHub API: issues, PRs, branches, commits                                        | repo management, CI status, pull requests        |
| lsp                 | language server diagnostics / symbols / references / rename                       | editor-grade code analysis                       |
| codegraph           | code graph / codebase insight                                                     | **Disabled in configuration**                    |
| TestSprite          | UI/API test generation and execution against a running app                        | frontend/backend test plans and runs             |
| playwright          | browser automation on live pages                                                  | download flows, web UI verification, screenshots |
| sequential-thinking | structured multi-step reasoning / planning                                        | decomposing complex problems                     |
| filesystem          | repo file access: read/write/tree/search                                          | standard file operations inside the workspace    |

Rules:

- Load exactly one skill per matched task (reload not needed between steps of the same task).
- Prefer MCP tools over generic web fetch/bash hacks (e.g., use `firecrawl_*`/`context7` instead of guessing URLs).
- If a skill/MCP is unavailable or fails, note the blocker explicitly and fall back to minimal standard tools; never claim MCP coverage that did not run.

## Python / ERA5 Environment

### Conda

Project Python environment: `iceberg-thermodynamic-model`
Expected location: `/home/vlad/miniconda3/envs/iceberg-thermodynamic-model`
Activate: `conda activate iceberg-thermodynamic-model`
Do NOT create venv/.venv/env inside the repo.

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

### Python Validation Layer

Independent Python reference models and cross-language comparisons live in
`python/validation/` (three_equation.py, three_equation_natural.py,
internal_thermal.py, low_flow.py, low_flow_fortran_comparison.py,
basal_melt.py, observational_validation.py, calibration_assessment.py);
tests in `python/tests/`. Tests use bootstrap imports — LSP "could not be
resolved" for `import <module>` is a known false positive.

### Key Data Paths

| Purpose            | Path                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| EN4 initial T/S    | `data/input/processed/ocean/initial_ts_2020-01-01.nc`                                                                           |
| ERA5 forcing       | `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc`                                               |
| Real grid inputs   | `data/input/generated/real_grid/` (KOORD.DAT, hhh.bar; root-level copies/symlinks NOT created automatically — see Regeneration) |
| Ice data           | `data/input/generated/real_grid/ice_2020-01-01/`                                                                                |
| Diagnostics output | `data/output/diagnostics/stage7.7A/`, `stage7.7B/`, `stage9.3/`                                                                 |
| Run outputs        | `data/runs/<run_id>/output/nc/`                                                                                                 |

## Development Workflow

Full process (before starting work, after completing a stage, conflict
resolution, stage-report format, commit rules) — in `RULES.md`.
Briefly: before work read `AGENTS.md`, `docs/README.md`, git status and
relevant sources; use the existing roadmap as the plan; do not change
physics to pass tests; after a stage — report, full test battery,
`git diff --check`, separate commit (only on user request).

Important notes that might be lost due to context limits — write them to
`docs/wiki/` (archive) or the appropriate living document. CDS credentials
(`~/.cdsapirc`) — never in Git.
