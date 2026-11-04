# Stage 12 — Voxel Iceberg on Reanalysis Forcing

Stage 12 is the current scientific stage. This directory stores completed
stage reports and their evidence; it is not the working directory for unfinished
tasks. Current Stage 12.9 acquisition work remains in `docs/validation/` and is
in progress.

> **Path note:** older planning notes in this directory preserve their original
> wording and paths. Use this README and `docs/validation/INDEX.md` for current
> locations and work status.

## Completed reports

| Stage | Report | Main result |
| --- | --- | --- |
| 12.1 | `stage12.1_glorys12_validation.md` | GLORYS12 Barents reconnaissance |
| 12.2 | `stage12.2_reanalysis_reader.md` | Reanalysis reader and ocean provider |
| 12.3 | `stage12.3_voxel_thermal_core.md` | Voxel thermal core |
| 12.4 | `stage12.4_crank_nicolson_stefan.md` | Crank–Nicolson and three-equation interface |
| 12.5 | `stage12.5_voxel_geometry_drift.md` | Voxel geometry drives iceberg drift |
| 12.6a | `stage12.6a_drift_latlon_iceberg_run.md` | Latitude/longitude drift and `iceberg_run` |
| 12.6b | `stage12.6b_wave_erosion.md` | Wave erosion and optional Stokes drift |
| 12.7.audit | `stage12.7.audit_voxel_melt.md` | Voxel geometry/mass mapping audit |
| 12.7a | `stage12.7a_enderlin23_hindcast.md` | Prescribed Enderlin23 hindcast |
| 12.7b | `stage12.7b_autonomous_air.md` | Autonomous voxel air balance |
| 12.7c | `stage12.7c_free_convection.md` | Free-convection closure and remaining deficit |
| 12.8 | `stage12.8_barents2020_matrix.md` | Exploratory 24-run Barents matrix with fallback forcing |

The 12.8 drift and lifetime results are lower bounds from monthly GLORYS and
constant-atmosphere fallbacks; they are not daily-forcing validation. No stage
report currently claims quantitative daily-forcing performance.

## Evidence and figures

- `evidence/` — Stage 12.7 and 12.8 manifests, result tables, and summaries.
- `figures/enderlin23/` — plots from Stage 12.7a.
- `figures/barents2020/` — plots from Stage 12.8.
- `STAGE12_PREPARATION.md` and `transition_analysis.md` — archived planning
  records, not active work plans.

## Current status

Stage 12.9 daily-forcing acquisition was resumed by explicit request on
2026-11-04 and is running sequentially. Do not start additional downloads unless
the user asks. Check `docs/validation/INDEX.md` for active work and
`docs/references/reanalysis_data_plan.md` for the data contract.
