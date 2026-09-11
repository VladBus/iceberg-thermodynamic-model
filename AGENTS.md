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
fpm test --flag "-I/usr/include" iceberg_test_10p10_three_equation  # Stage 10.10 three-equation (19 checks)
fpm test --flag "-I/usr/include" iceberg_test_10p10_three_equation  # Stage 10.10.1 three-equation correction (25 checks)
# NOTE: Stage 10.11 Fortran unit test (iceberg_test_10p11_natural_convection) was NOT
# delivered in 6a0014e; natural-convection validation currently rests on the Python
# suite below (70 checks) + compile-time integration. Fortran test pending Stage 10.11 audit.
python python/tests/test_three_equation.py                        # Stage 10.10/10.10.1 Python (65 checks)
python python/tests/test_three_equation_natural.py                # Stage 10.11 Python (70 checks)
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
- ❌ Before committing, check `.gitignore` — it blocks: `opencode.jsonc`, `.opencode/`, `docs/wiki/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`. **Exception:** the curated Stage 10.8.2 observational dataset is versioned (`data/validation/observations/` is un-ignored in `.gitignore`).
- ❌ Do not delete root-level symlinks: `KOORD.DAT`, `hhh.bar`, `1_k.ice` — required by model, gitignored, point to `data/input/generated/real_grid/`.

### Iceberg Model Constraints (Stage 9.3)

- ❌ Do not modify canonical ocean/sea-ice physics (Block 200/210/280, barotropic solver, EOS, grid, ERA5, bathymetry, thermodynamics).
- ❌ Iceberg forcing must remain OFFLINE/PRESCRIBED. No two-way coupling.
- ❌ No advanced physics (internal 3D temperature, wave erosion, sea-ice capture, rollover, fracture, multi-iceberg) until minimal model verified.
- ❌ Melt coefficients are compile-time constants in `iceberg_types.f90` — require rebuild to change.
- ❌ Vertical interpolation: EN4→model = 18 levels 2.5–550 m (`python/ocean/build_initial_ts.py`); `interp_at_draft` = linear + surface/deep clamps; extrapolation only in shallow columns where draft below deepest defined level/ht (handled in `iceberg_forcing.f90`).
- ❌ Position: x,y AND lat/lon updated each step (`model_coords_to_latlon` in `iceberg.f90`); forcing re-sampled at current x,y every step (`get_ocean_profile`/`era5_bilinear2d`). Forcing stays OFFLINE/PRESCRIBED — no two-way feedback.
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

## OpenCode Environment

OpenCode version: **1.18.30**

### Plugins

| Plugin | Purpose |
|---|---|
| oh-my-opencode | OpenCode agent orchestration / skill utilities |
| opencode-dynamic-context-pruning | context-window management (pruning) during long sessions |
| opencode-git-master | git operations integration (commits, history, rebase) |
| opencode-supermemory | persistent memory (project/user knowledge recall) |

### Roles

OpenCode provides three complementary execution/planning roles. Select by task
complexity — most tasks use one role, not all three.

| Role | Kind | Use for |
|---|---|---|
| Prometheus | Plan Builder | decomposition of complex tasks; stage planning; dependency/risk identification; preparation before implementation |
| Hephaestus | Deep Agent | deep implementation; complex debugging; detailed repository work; multi-step technical execution |
| Sisyphus | Ultraworker | intensive multi-step execution; integration; persistence across a complex task; bringing implementation through verification to completion |

## Skills and MCP Tools (MANDATORY)

The project defines **8 skills** (`.opencode/skills/`) and the OpenCode environment
exposes **12 MCP servers** (`opencode.jsonc` + global config) plus **2 security
skills** (`/security-review`, `/security-research`). Models MUST load the relevant
skill and prefer the MCP tools over ad-hoc/generic implementations for the tasks
below. Do not hand-roll equivalents of an available skill/MCP; loading the skill
is part of normal workflow.

### Skills (load via the `skill` tool when the task matches)

| Skill | Use when | Purpose |
|---|---|---|
| academic-paper | writing/editing an academic paper, abstracts, lit-review, citations, LaTeX/DOCX/PDF | 12-agent paperwriting pipeline (plan/outline/revision/formats) |
| academic-paper-reviewer | reviewing a manuscript, referee report, re-review | 5-persona peer review (EIC/peers/Devil's Advocate) |
| academic-pipeline | end-to-end research → paper → integrity → review → finalize | orchestration of deep-research + academic-paper + reviewer |
| deep-research | literature review, fact-check, systematic review, meta-analysis, 3W scan | 13-agent research pipeline with source verification |
| data-scientist | analytics, ML, statistical modeling, business intelligence | advanced data analysis |
| math-modeling | math-modelling competitions (MCM/ICM/美赛/国赛), problem decomposition | modeling workflow to LaTeX paper |
| coding-agent | programmatically running Codex/Claude Code/OpenCode/Pi agents | external coding-agent control |
| humanizer | de-AIing prose (review/revise for "AI tells") | rewrite AI-sounding text |
| /security-review | security review of source code, dependency/configuration risks, CI/CD security, unsafe file/process/network behavior, secrets/credential exposure | team-mode security audit of the codebase |
| /security-research | researching security advisories, CVEs, dependency vulnerabilities, external security guidance, current security info requiring web research | web-based security threat research |

### MCP servers (invoke the matching tool set)

| Server | Use for | Examples |
|---|---|---|
| websearch | real-time web search (auto/fast/deep) | current events, recent data, web facts |
| context7 | current library/framework/API docs (resolve id → query docs) | Fortran/fpm/gfortran/netcdf, CLI tooling |
| firecrawl | web research: search, scrape, map, crawl; `firecrawl_research_*` scan paper index | literature/DOI verification, data-source checks |
| fetch | plain URL content retrieval (markdown/text) | single static pages |
| grep_app | GitHub code search over public repos (grep.app index) | real-world usage examples |
| github | GitHub API: issues, PRs, branches, commits | repo management, CI status, pull requests |
| lsp | language server diagnostics / symbols / references / rename | editor-grade code analysis |
| codegraph | code graph / codebase insight | **Disabled in configuration** |
| TestSprite | UI/API test generation and execution against a running app | frontend/backend test plans and runs |
| playwright | browser automation on live pages | download flows, web UI verification, screenshots |
| sequential-thinking | structured multi-step reasoning / planning | decomposing complex problems |
| filesystem | repo file access: read/write/tree/search | standard file operations inside the workspace |

Rules:

- Load exactly one skill per matched task (reload not needed between steps of the same task).
- Prefer MCP tools over generic web fetch/bash hacks (e.g., use `firecrawl_*`/`context7` instead of guessing URLs).
- If a skill/MCP is unavailable or fails, note the blocker explicitly and fall back to minimal standard tools; never claim MCP coverage that did not run.

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

## Stage 10.3 Summary (Modern Turbulent Heat & Moisture Exchange)

- **Classification:** C -- Modern bulk formulation implemented and independently validated (with corrective validation).
- **Physics:** Sensible/latent heat now use neutral bulk aerodynamic formulation with C_H = C_E = 1.5e-3.
- **Key changes:**
  1. SH: Q_SH = rho*CP_AIR*C_H*U*dT (replaces legacy SH_COEFF = 1.7068 Stanton number)
  2. LH: Q_LH = rho*L_S*C_E*U*dq with ice saturation (Murphy & Koop 2005), L_S = 2.835e6 J/kg
  3. Surface humidity: q_sat_ice replaces water saturation (5-18% correction at T < 0 deg C)
  4. Stage 10.3: Q_LH is energy flux only; mass changes from sublimation/deposition deferred to Stage 10.4
- **Transfer coefficients:** C_H = C_E = 1.5e-3 (fixed neutral bulk coefficients — model parameters).
  Theoretical logarithmic formulation: C = kappa^2/ln(z/z0)^2 with kappa=0.4, z=10m, z0=1e-4m gives ~1.21e-3.
  Production uses fixed 1.5e-3 (documented parameter). Andreas et al. 2010 cited as literature context.
- **Stability correction:** Not implemented (requires Monin-Obukhov length, deferred)
- **Tests:** 9 new analytical tests PASS (zero wind, sign conventions, ice vs water saturation, wind scaling, coefficient scaling, dimensional validation, cold/dry, humid, nighttime regression)
- **Energy conservation:** Independent analytical validation with Stage 10.3 formulas (tolerance 10 J/m²)
- **All 41 fpm tests PASS** including regression of Stage 10.1/10.2.
- **Files changed:** src/iceberg_types.f90 (constants), src/iceberg_thermodynamics.f90 (compute_surface_melt), test/iceberg_test_surface_melt_audit.f90 (Stage 10.3 tests)
- **Documentation updated:** model_equation_ledger.md, model_physics_status.md, stage10_modernization_plan.md

## Stage 10.4 Summary (Phase Change Partitioning)

- **Classification:** C -- Phase change partitioning implemented and validated.
- **Physics:** Latent heat flux Q_LH partitioned into vapor mass flux and melt energy.
- **Key changes:**
  1. m*vapor = rho_air * C*E * U \* (q_air - q_sat_ice) [kg/(m2 s)]
  2. Q_LH = m_vapor \* L_S [W/m2]
  3. Q_melt = max(Q_net_non_melt - Q_LH, 0) [W/m2]
  4. m_melt = Q_melt / (rho_ice \* L_f) [m/s]
  5. dH/dt = -(m_melt + m_vapor/rho_ice)
  6. Mass budget includes vapor mass change
- **Tests:** 8 new Stage 10.4 analytical tests PASS (sublimation, deposition, melt, energy/mass conservation, vapor latent/mass consistency)
- **All 41 fpm tests PASS** including regression of Stage 10.1-10.3.
- **Files changed:** src/iceberg_types.f90 (vapor diagnostics), src/iceberg_thermodynamics.f90 (phase change logic), src/iceberg.f90 (mass budget), src/iceberg_geometry.f90 (mass budget), test/iceberg_test_surface_melt_audit.f90 (8 new tests)
- **Documentation updated:** model_equation_ledger.md, model_physics_status.md, stage10_modernization_plan.md

## Stage 10.4.1 Summary (Corrective Energy Partition)

- **Classification:** C -- Corrective energy partitioning of latent heat.
- **Critical bug fixed:** Previous Stage 10.4 had `Q_net_non_melt = SW + LW + SH + LH` then `Q_melt = max(Q_net_non_melt - LH, 0)`, which cancelled LH and inverted sublimation energy sign.
- **Correct physics (Stage 10.4.1):**
  1. Q_nonlatent = SW_abs + LW_down + LW_up + SH (NO LH)
  2. m*vapor = rho_air * C*E * U \* (q_air - q_sat_ice) [kg/(m2 s)]
  3. Q_LH = m_vapor \* L_S [W/m2]
  4. Q_surface = Q_nonlatent + Q_LH
  5. Sign: m_vapor < 0 -> sublimation -> Q_LH < 0 -> ENERGY SINK
     m_vapor > 0 -> deposition -> Q_LH > 0 -> ENERGY SOURCE
  6. T*surface < T_melt: dT = Q_surface * dt / C*eff
     If crossing T_melt: excess_energy = Q_surface - C_eff*(T_melt - T_surface)/dt
     Q_melt = max(excess_energy, 0)
  7. T_surface = T_melt: Q_melt = max(Q_surface, 0)
  8. m_melt = Q_melt / (rho_ice \* L_f)
  9. dH/dt = -(m_melt + m_vapor/rho_ice)
  10. Mass budget includes vapor mass change
- **Vapor mass flux and latent heat flux are TWO REPRESENTATIONS of the SAME phase-change process** (not two independent energy sources).
- **Tests:** 10 new Stage 10.4.1 corrective validation tests PASS (zero LH, sublimation, deposition, monotonicity, latent identity, below-freezing, crossing 0°C, at 0°C, mass/energy consistency, regression).
- **All 41 fpm tests PASS** including regression of Stage 10.1-10.4.
- **Files changed:** src/iceberg_thermodynamics.f90 (compute_surface_melt energy partition), docs/model/model_equation_ledger.md, docs/model/model_physics_status.md, docs/model/stage10_modernization_plan.md, docs/PROJECT_ROADMAP.md, AGENTS.md

## Stage 10.4.2 Summary (Independent Monotonicity Validation)

- **Classification:** C -- Independent controlled validation of the Stage 10.4.1 latent-heat monotonicity. No production physics changed.
- **Why re-validated:** old TEST 10.4.9 ran in **polar day**, where changing `d2m` also changed `SW_down` (precipitable-water attenuation), so Q_nonlatent was NOT controlled; observed `m_base=2.37e-7 > m_dep=6.59e-8` contradicted the claimed ordering. The old "monotonicity" claim was not demonstrated.
- **Controlled design — polar night (SW ≡ 0):** Q_nonlatent = LW_down + LW_up + SH is analytically d2m-invariant. Only Q_LH responds to d2m via q_air (Tetens monotonic).
- **Controlled run** (lat 90, t2m=283.15 K, tcc=0, msl=101325 Pa, U=10 m/s, T=0°C; only d2m varies):
  - SUB d2m=263.15 K: m_vapor=−3.72e−5 kg/m²s, Q_surface=44.4 W/m², m=1.46e−7 m/s
  - ZERO d2m=273.158 K (e_sat_dew=e_sat_ice): m_vapor≈0, Q_surface=149.7, m=4.93e−7
  - DEP d2m=283.15 K: m_vapor=+7.11e−5, Q_surface=351.4, m=1.16e−6
  - Q_nonlatent identical (149.743 W/m²) across all cases; m_vapor/Q_LH/Q_surface/Q_melt/m_surface strictly monotonic sub < zero < dep.
- **Additional checks:** zero-latent ⇒ Q_surface=Q_nonlatent (within 1 W/m²); strong sublimation quenches melt (m→0, T<0); strong deposition cannot decrease melt; Q_LH=m_vapor·L_S (independent, tight); below-freezing monotonic cooling/warming with no melt; crossing 0°C excess-energy partition matches independent analytic; geometry budget dH/dt=−m_surface+m_vapor/ρ_ice.
- **Tests:** 13 new Stage 10.4.2 checks inside `iceberg_test_surface_melt_audit` (total 59 checks, 0 errors).
- **All fpm tests PASS** (49 auto-discovered test programs, exit 0) including regression of Stage 10.1-10.4.1.
- **Files changed:** test/iceberg_test_surface_melt_audit.f90 (Stage 10.4.2 block), docs/model/model_physics_status.md, docs/model/model_equation_ledger.md, docs/model/stage10_modernization_plan.md, docs/wiki/Stage10.4.2_Independent_monotonicity_validation.md, AGENTS.md

## Stage 10.4.2.1 Summary (Independent Q_surface Output Validation)

- **Classification:** C -- Direct validation of the production Q_surface output. Production physics unchanged; one diagnostic-only API addition.
- **Why:** Stage 10.4.2 reconstructed Q_surface from downstream m_surface (`Q_surface = m_surface·ρ·L_f` or `q_net` fallback) — it never verified the production total-surface-flux calculation. `q_surface`/`q_lh` were LOCAL in `compute_surface_melt` (line 560); `diag%q_net_surface` = residual AFTER melt (≈ 0 while melting), NOT Q_surface.
- **Production change (diagnostic-only, no numerics change):**
  1. `src/iceberg_types.f90` — `iceberg_diagnostics` gains `q_surface`, `q_lh`.
  2. `src/iceberg_thermodynamics.f90` — `compute_surface_melt` assigns `diag%q_surface = q_surface`, `diag%q_lh = q_lh` (the exact values melt/mass-budget were computed with).
- **Direct validation** (polar-night controlled exp, only d2m varies): `Q_surface_production == Q_nonlatent_independent + m_vapor_production·L_S`.
  - SUB d2m=263.15 K: 44.368423 vs 44.368416 expected → error +7.6e−6 W/m²
  - ZERO d2m=273.158 K: 149.742554 vs 149.742554 → 0.0
  - DEP d2m=283.15 K: 351.388672 vs 351.388672 → 0.0
  - Q_nonlatent independent = 149.742706 W/m² identical across cases; production Q_surface strictly monotonic sub < zero < dep; latent identity Q_LH = m_vapor·L_S confirmed (DEP 201.645966 W/m² vs independent literals 283.15/283.15 K).
- **Tests:** 7 new Stage 10.4.2.1 checks inside `iceberg_test_surface_melt_audit` (total 66 checks, 0 errors).
- **All fpm tests PASS** (49 auto-discovered test programs, exit 0) including regression of Stage 10.1-10.4.2.
- **Files changed:** src/iceberg_types.f90 (q_surface/q_lh fields), src/iceberg_thermodynamics.f90 (diag assignments), test/iceberg_test_surface_melt_audit.f90 (10.4.2.1 block), docs/model/model_physics_status.md, docs/model/model_equation_ledger.md, docs/model/stage10_modernization_plan.md, docs/wiki/Stage10.4.2.1_Independent_Q_surface_output_validation.md, AGENTS.md

## Stage 10.5 Summary (Ocean Thermal Forcing)

- **Classification:** C -- Ocean T/S forcing chain modernized to EOS-80 freezing point and validated. Production physics changed (Tf = f(S,p) replaces Zubov linear -54·S; new diagnostic).
- **Physics:**
  1. `Tf(S,p) = (A0 + A1·sqrt(S) - A2·S)·S + BP·P`, A0=-0.0575, A1=1.710523e-3, A2=2.154996e-4, BP=-7.53e-4, S [PSU]=1000·S_kg, P [dbar]=ρ_w·g·z/10⁴ (Fofonoff & Millard 1983 / UNESCO TPMS 44 §5; Gill 1982 Eq. 3.5.2). **Literature checkvalue Tf(40 PSU, 500 dbar) = -2.588567 °C reproduced.**
  2. Canonical `ocean_freezing_point` (pure) in `iceberg_types.f90`, applied at 3 sites: `compute_basal_melt` (Tf at draft D), `depth_averaged_thermal_forcing` (per-layer Tf(z_k) + deep layer), `freezing_point(S, 0)` wrapper.
  3. New diagnostic `delta_t_ocean = T(D) - Tf(D)` (unclamped, may be ≤ 0); set in `iceberg_thermodynamics_step`.
- **Regression consequence (EOS pressure term):** legacy "cold ocean" T=-1.9 °C was ABOVE Tf below ~8 m → spurious melt. Porthed threshold to -2.5 °C in 11 files (test_2/3/4/6/8/9, drift_scaling_wind, drift_scaling_wind_no_cor, drift_scaling_current, moving_trajectory, ibcao_interp).
- **Tests:** test_7 rewritten with independent Stage 10.5 audit (checks 10.5.1-10.5.19, 24 total): EOS surface values/monotonicity, pressure term (−7.53e-4·P over 100 m), pure water depth, UNESCO 500 dbar checkvalue, interp node/midpoint/clamps, draft sampling (H=50/100/150), basal regimes T<Tf/T=Tf/T>Tf, lateral Method-A box-model replica, C_LATERAL·⟨ΔT⟩, delta_t_ocean wiring.
- **All fpm tests PASS** (49 auto-discovered, exit 0), zero mismatches; `-Wall -Wextra` build clean (0 warnings), exit 0; `git diff --check` clean.
- **Files changed:** src/iceberg*types.f90 (EOS_FP*\* constants, ocean_freezing_point, delta_t_ocean, v10.5 header), src/iceberg_thermodynamics.f90 (compute_basal_melt/basal wrapper, delta_t_ocean diag), src/iceberg_forcing.f90 (depth_averaged_thermal_forcing per-layer + deep), 12 test files, docs/model/model_equation_ledger.md (§4.5-4.7), docs/model/model_physics_status.md (row 4 → C), docs/model/stage10_modernization_plan.md (§10.5 ✅), docs/wiki/Stage10.5_Ocean_Thermal_Forcing.md, AGENTS.md.
- **Not in scope:** depth-dependent U_rel (Stage 10.6), basal/lateral melting modernization (10.6/10.7), canonical ocean model `thermodynamics.f90` untouched (its -54·S Zubov Tf remains).

## Stage 10.6.1 Summary (Ocean Heat Transfer Audit)

- **Classification:** B — PASS WITH LIMITATIONS. Production physics unchanged; documentation corrected.
- **Formulation audited:** `ocean_heat_transfer_coeff` (src/iceberg_types.f90:421-448): Re=U_rel·L_char/ν; laminar Nu=0.664·Re^0.5·Pr^(1/3); turbulent Nu=0.037·Re^0.8·Pr^(1/3); γ_T=Nu·k/L_char; transition at Re≥5e5.
- **Precision:** 10p6 airtight audit matches canonical ±1e-7 (laminar) / −1.09e-5 (turbulent) on R4 hardcoded reference.
- **Doc correction (commit `40d4a3b`):** exponents L_char^0.2/0.5 → L_char^(-0.2)/(-0.5) (dimensionally correct).

## Stage 10.7 Summary (Independent Basal Melt Validation)

- **Classification:** B — PASS WITH LIMITATIONS. Audit only; production Fortran NOT changed (no bug found).
- **Test:** `applications/iceberg_test_10p7_basal_melt_validation` (17 checks, STOP 0): ALL expected values computed from embedded literals (Pr=13.8, ν=1.82e-6, k=0.56, ρ_ice=910, L_f=3.34e5, EOS-80 coefficients); production functions called only for actual output.
- **Cases A–J:** cold ocean m=0 · laminar/turbulent γ_T analytic · transition just below/above 5e5 (jump ratio 2.897) · U-scaling U^0.5/U^0.8 · ΔT linearity (m/ΔT const to 1e-3) · L-scaling L^(-0.5)/L^(-0.2) · zero flow γ_T=0 (documented natural-convection limitation) · end-to-end chain I (Tf=−1.93158, ΔT=3.93158, m=1.5852e-6 m/s, float32-exact match) · literature magnitude band J (0.4963 m/day ∈ [0.01,1] m/day, Cenedese & Straneo 2023).
- **Literature cross-check:** three-equation estimate (St·u*, St=0.011 commented) at U=0.1 m/s → factor ≈1.8 agreement with flat-plate; both closures reproduce observed band.
- **All fpm tests PASS** (51 auto-discovered, exit 0); `-Wall -Wextra` build clean; `git diff --check` clean.
- **Files changed:** test/iceberg_test_10p7_basal_melt_validation.f90 (new), docs/validation/stage10.7_basal_melt_validation.md (new), docs/model/model_physics_status.md, docs/model/stage10_modernization_plan.md, docs/references/literature_matrix.md, docs/references/citation_map.md, docs/PROJECT_ROADMAP.md, AGENTS.md.
- **Network blocker documented:** external web/bib verification unavailable (search/firecrawl/fetch failures) — in-repo bibliography primary; Γ_T Stanton convention is an open risk for Stage 10.8. (Resolved in Stage 10.9: all seven named DOI anchors verified via Crossref.)

## Stage 10.8.2 Summary (Observational Validation of Basal Melt)

- **Classification:** C — validation pass complete with documented systematic limitations; **production physics NOT changed** (no coefficient/parameter edits).
- **Dataset:** `data/validation/observations/iceberg_basal_melt_observations.csv` (19 records, 16 cols; **versioned** — un-ignored in `.gitignore` because the test suite and CI depend on it) + provenance md. Tiers: lab-primary (Russell & Head 1980), field-primary (Keys & Williams 1984), synthesis (Neshyba & Josberger 1980), rs-derived (Enderlin & Hamilton 2014; Enderlin et al. 2016/2023) + 1 context row. Rignot calving-face rates EXCLUDED (not submarine melt). All DOIs Crossref-verified.
- **Code:** `python/validation/observational_validation.py` (loader, metrics, natural-convection gap test, inverse-U bisection, regimes, sensitivity sweep, 6 figures); `python/tests/test_observational_validation.py` (15 blocks, **229 checks**).
- **Results:** 4 forcing-anchored rows — RMSE 0.108, MAE 0.092, bias +0.083 m/day; KW84 within range (ratio 0.70 at L=draft); NJ80 synthesis overestimated factor 2.1→5.8 (dT 8→2 °C) — later shown (10.9) to be a dT-power-law shape mismatch, not a scale offset. Natural-convection gap 5.7–7.3 orders (no quiescent branch). Inverse-U: fjord rates reproducible at plausible U_rel 0.1–1.0 m/s (dT 2–4 °C). All comparable obs are turbulent (Re>5e5); laminar branch has no field anchor.
- **Metrics are computed on 4 rows only** (`include_in_metrics=True`: KW84 + NJ80×3); RH rows = gap test, RS rows = inverse-U, OPEN = context-only.
- **Verification:** `python python/tests/test_observational_validation.py` must print `TOTAL CHECKS: 229 ERRORS: 0`; regression `test_basal_melt_validation.py` (44) still under CI.
- **Bib:** 8 new verified entries in `docs/references/references.bib` (enderin x3, josberger, keys, neshyba, orheim, schild); legacy key `russefl-headMELTINGFREEDRIFTINGICEBERGS` KEPT (citation compatibility) but record corrected (author Russell-Head, journal Annals of Glaciology, vol 1, DOI 10.3189/S0260305500017092).
- **Report:** `docs/validation/stage10.8.2_observational_validation.md` (12 sections; claims #7/#8 corrected and #1/#2/#4 qualified in Stage 10.9).
- **Corrected claims (Stage 10.9):** "basal plane dominating; side melt second" is aspect-ratio-dependent (side ~ basal for D/L~0.2); "submarine ≈ basal" is not universal; the KW84 0.70x anchor only holds at L=draft (production L = berg length gives 0.55–0.62x).

## Stage 10.10 Summary (Three-Equation Ice-Ocean Interface)

- **Classification:** C -- modern three-equation ice-ocean interface implemented and independently validated. Production physics ADDED on a separately selectable path; bulk baseline unchanged (bulk path statements identical; re-indented into the scheme else-branch with diagnostic-only additions).
- **Physics:** `set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)` + `solve_three_equation_interface` in `src/iceberg_thermodynamics.f90`. Holland & Jenkins 1999 / Jenkins et al. 2010 Table 2: gamma_T=K_T·U_rel, gamma_S=K_S·U_rel (K_T=1.1e-3, K_S=3.1e-5); Eq. I T_B=Tf(S_B,P); Eq. II rho_w·c_w·gamma_T·(T_w−T_B)=m·rho_i·(L_f+c_i·max(T_B−T_i,0)); Eq. III S_B=gamma_S·S_w/(m+gamma_S); bisection with doubling upper bound (60+60, float32). Constants rho_w=1028, c_w=3974, c_i=2009, T_i=−10 (H&J99).
- **Real bug found & fixed during implementation:** local `latent_heat` shadowed module constant `LATENT_HEAT` (Fortran case-insensitive) -> uninitialised read -> m=Infinity in production while an isolated copy converged. Renamed local to `l_heat`. Diagnostics: `t_interface`, `s_interface` added to `iceberg_diagnostics`.
- **Validation:** Fortran `iceberg_test_10p10_three_equation` (19 checks, 0 errors) + Python `python/validation/three_equation.py` / `python/tests/test_three_equation.py` (46 checks, 0 errors). Cross-language contracts: H&J99 anchor m=9.4457e-9 m/s and production end-to-end m=3.998e-6 m/s (rel < 1e-4 Fortran float32 vs Python float64). Warm-ocean 0.345 m/day within observed 0.01–1 m/day band. All 52 fpm tests pass; strict `-Wall -Wextra` clean; Python suites 229/212/44/46 all 0 errors.
- **Documented limitations:** constant T_i conduction (internal thermal evolution future); natural-convection floor NOT implemented (U_rel=0 -> m=0, same as bulk); K_T/K_S are the U-based J2010 convention — melt-driven u*-Stanton St=0.011 remains an open convention question (10.9).
- **Files changed:** src/iceberg_types.f90 (scheme constants/switch/setter, 3eq constants, diag fields), src/iceberg_thermodynamics.f90 (solver + branch + diag), test/iceberg_test_10p10_three_equation.f90 (new), python/validation/three_equation.py (new), python/tests/test_three_equation.py (new), docs/model/* (ledger §10.2, physics status row, plan §10.10), docs/PROJECT_ROADMAP.md, docs/references/*, docs/validation/stage10.10_three_equation_interface.md (new), AGENTS.md, .github/workflows/ci.yml.
- **Next (Stage 10.11 proposed):** natural-convection floor, then internal thermal evolution, then re-scoring the 10.8.2 set against the 3eq closure.

## Stage 10.10.1 Summary (Mass/Salt Convention Correction in Three-Equation Interface)

- **Classification:** C -- mass/salt convention correction in the three-equation ice-ocean interface implemented and independently validated. Production physics UPDATED on the selectable three-equation path; bulk baseline unchanged.
- **Physics:** Corrected Eq. III from equal-density reduction `gamma_S (S_w - S_B) = m S_B` to mass-conserving `rho_w gamma_S (S_w - S_B) = rho_i m S_B`, reducing to `S_B = gamma_S S_w / (gamma_S + (rho_i/rho_w) m)` with `rho_i/rho_w = 910/1028 = 0.8852...`. Matches MOM6 `mom_ice_shelf`, PISM basal-melt, MITgcm shelfice, and H&J99 Eq. 4 (brine salt flux `rho_i M wB (S_I - S_B)`). Stage 10.10 implicitly set `rho_i/rho_w = 1`.
- **Production changes:** `src/iceberg_types.f90` (new constant `RHO_ICE_WATER_RATIO`, public); `src/iceberg_thermodynamics.f90` (three reduction expressions in `solve_three_equation_interface` + solver doc block rewritten with MOM6/PISM/MITgcm/H&J99 Eq.4 references); `python/validation/three_equation.py` (module docstring, `_s_interface` with optional `rho_ratio` defaulting to new constant).
- **Effect:** canonical H&J99 anchor m increases from 9.4457e-9 to 1.0438e-8 m/s (+10.5%, amplified by near-zero thermal drive); production end-to-end m increases from 3.998e-6 to 4.067e-6 m/s (+1.7%); warm band 0.351 m/day (inside 0.01-1 m/day). `T_i = -10` degC attribution corrected: model-selected constant internal temperature, NOT from H&J99 (H&J99 solve conduction explicitly).
- **Validation:** Fortran test extended to 25 checks (19+6 new density-reduction identity/limit/monotonicity checks); Python suite extended to 65 checks (46+19 new Stage 10.10.1 checks including salt-flux identity, freshwater-flux identity, limits, monotonicity, cross-language contract). All tests PASS. Strict `-Wall -Wextra -fcheck=all` build clean. `git diff --check` clean.
- **Files changed:** src/iceberg_types.f90, src/iceberg_thermodynamics.f90, test/iceberg_test_10p10_three_equation.f90, python/validation/three_equation.py, python/tests/test_three_equation.py, docs/model/model_equation_ledger.md, docs/model/model_physics_status.md, docs/model/stage10_modernization_plan.md, docs/PROJECT_ROADMAP.md, docs/references/literature_matrix.md, docs/references/citation_map.md, AGENTS.md, .github/workflows/ci.yml.
- **Next:** natural-convection floor, then internal thermal evolution, then re-scoring the 10.8.2 set against the corrected 3eq closure.

## Stage 10.11 Summary (Natural Convection Basal Melt / Low-Flow Closure)

- **Classification:** C -- physically-motivated natural-convection closure for the three-equation ice-ocean interface implemented and independently validated. Production physics UPDATED on the selectable three-equation path; bulk baseline unchanged.
- **Physics:** Natural convection from a horizontal ice base (facing downward) driven by combined thermal and haline buoyancy. Double-diffusive Rayleigh number:
  `Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]`
  with `beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`.
  Characteristic length = iceberg length L (horizontal scale of convection cells; Gayen et al. 2016 LES).
  Nusselt number (Fujii et al. 1973, horizontal plate facing downward):
  - Laminar (`Ra < 1e7`): `Nu = 0.27 * Ra^0.25`
  - Turbulent (`Ra >= 1e7`): `Nu = 0.15 * Ra^(1/3)`
  Natural-convection transfer coefficients:
  `gamma_T_nat = Nu * k / (L * rho_w * c_w)`,
  `gamma_S_nat = gamma_T_nat * (K_S / K_T)`.

- **Mixed convection:** Churchill (1977) combination with exponent n=3:
  `gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)`
  `gamma_S_eff = (gamma_S_forced^3 + gamma_S_nat^3)^(1/3)`
  where `gamma_T_forced = K_T * U_rel`, `gamma_S_forced = K_S * U_rel`.

- **Rayleigh number cap:** `Ra_max = 1e10` to avoid unphysical extrapolation beyond the Fujii correlation validity range.

- **Selectable scheme:** `BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL` (runtime switch). The three-equation salt balance retains the Stage 10.10.1 density-weighted correction.

- **Effect:** At `U_rel = 0`, finite melt rate `~1.6e-8 m/s` (0.001 m/day) for typical Arctic conditions (`T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). At `U_rel = 0.1 m/s`, natural convection adds ~0.1% to forced convection. At `U_rel = 1 m/s`, forced convection dominates (>99.9%).

- **Validation:** Python `test_three_equation_natural.py` (70 checks) including zero-flow, low-flow continuity, mixed-convection regime, Ra/Nu scaling, salt/heat balance identities, and cross-language contract (`m = 1.638e-8 m/s` at `U_rel=0`, `T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). Natural-convection Fortran code compiles and is integrated (scheme selector + solver), but the claimed Fortran unit test `iceberg_test_10p11_natural_convection` was NOT delivered in 6a0014e — it is pending the Stage 10.11 audit. Strict `-Wall -Wextra -fcheck=all` build clean.

- **Files changed:** src/iceberg_types.f90 (new constants, natural convection function), src/iceberg_thermodynamics.f90 (new solver `solve_three_equation_interface_natural` with explicit coupling); python/validation/three_equation_natural.py (new), python/tests/test_three_equation_natural.py (new); docs/model/* (ledger §10.3, physics status row, plan §10.11), docs/PROJECT_ROADMAP.md, docs/references/*, docs/validation/stage10.11_natural_convection.md (new), AGENTS.md, .github/workflows/ci.yml.

- **Next:** internal thermal evolution, then re-scoring the 10.8.2 set against the 3eq+natural convection closure.

## Stage 10.9 Summary (Calibration Assessment of the Basal-Melt Coefficient)

- **Classification:** C — validation insufficient for robust calibration; **production physics NOT changed** (no coefficient fits; `git diff -- src/` EMPTY).
- **Module:** `python/validation/calibration_assessment.py` (pure-Python; imports `basal_melt` + `observational_validation`, no Fortran); test `python/tests/test_calibration_assessment.py` (20 blocks, **212 checks**, A–T).
- **Conclusion — NO scalar coefficient identifiable:** inferred required C_gamma spans **8.29x (0.918 decades)** between the two independent sources — NJ80 per-source geomean 0.286 (3 rows, 1 source), KW84 1.418 (1 row); pooled geomean 0.427; effective n = 2 sources. Leave-one-source-out: KW84-fit → NJ80 over 8.29/4.87/3.01; NJ80-fit → KW84 0.202.
- **Functional-form, not scale:** NJ80 obs ~ dT^1.73 and RH80 tank law ~ (T+1.8)^1.50 vs closure exactly dT^1.0 (a scalar cannot absorb a power-law mismatch); JPL-Re set all turbulent (Re ≥ 1.1e6).
- **Sensitivity exponents (measured):** turbulent U^+0.800·L^-0.200·dT^+1.000·C^+1.000; laminar U^+0.500·L^-0.500. L_char geometry: using production L = berg length (40–100 m) drops KW84 ratio 0.705 → 0.55–0.62; NJ80 ratios 4.10/3.44/3.02/2.68 for L=20/50/100/200 m.
- **Stanton:** model flat-plate St 3.4–4.1e-4 vs obs-implied 5.9e-5–5.9e-4 vs melt-driven glaciological anchor St=0.011 (Jenkins et al. 2010) — convention-level disagreement, not a coefficient offset.
- **Uncalibratable by design:** natural-convection branch is model×0 = 0 for ANY finite C_gamma (5.7–7.3 orders gap persists; a free-convection floor is new physics).
- **Literature:** seven named sources (weeksCampbell 1973, bigg 1997, hollandJenkins 1999, jenkinsNicholls 2010, fitzmauriceStern 2018, cenedese 2023, martinAdcroft 2010) DOI-verified via Crossref (network restored); no new bib keys.
- **Verification:** `python python/tests/test_calibration_assessment.py` must print `TOTAL CHECKS: 212 ERRORS: 0`; 10.8.2 (229) and 10.8.1 (44) regression suites still under CI.
- **Report:** `docs/validation/stage10.9_calibration_assessment.md` (15 sections, Q1–Q10).
- **Next (Stage 10.10):** three-equation ice-ocean interface (Holland & Jenkins 1999; melt-driven Stanton; buoyancy-informed per FitzMaurice & Stern 2018) + natural-convection floor, re-scoring the 10.8.2 set as the acceptance criterion. Scalar calibration explicitly NOT recommended.
