# Stage 12 — Voxel Iceberg on Reanalysis Forcing

Stage 12 is the current scientific stage. This directory stores completed
stage reports and their evidence; it is not the working directory for unfinished
tasks. Stage 12.9a acquisition, Stage 12.10 voxel thermodynamics, the Stage 12.11/12.12/12.13 audits, the Stage 12.14 100^3 audit, the Stage 12.15 current-code Enderlin/drift-map rerun, and the Stage 12.16 drift/ensemble/layer-drag/energy audit are complete;
the acquisition manifests remain in `docs/validation/` as canonical provenance.
Stage 12.9b thesis writing is the active workstream.

> **Path note:** older planning notes in this directory preserve their original
> wording and paths. Use this README and `docs/validation/INDEX.md` for current
> locations and work status.

## Completed reports

| Stage | Report | Main result |
| --- | --- | --- |
| 12.1 | [`stage12.1_glorys12_validation.md`](stage12.1_glorys12_validation.md) | GLORYS12 Barents reconnaissance |
| 12.2 | [`stage12.2_reanalysis_reader.md`](stage12.2_reanalysis_reader.md) | Reanalysis reader and ocean provider |
| 12.3 | [`stage12.3_voxel_thermal_core.md`](stage12.3_voxel_thermal_core.md) | Voxel thermal core |
| 12.4 | [`stage12.4_crank_nicolson_stefan.md`](stage12.4_crank_nicolson_stefan.md) | Crank–Nicolson and three-equation interface |
| 12.5 | [`stage12.5_voxel_geometry_drift.md`](stage12.5_voxel_geometry_drift.md) | Voxel geometry drives iceberg drift |
| 12.6a | [`stage12.6a_drift_latlon_iceberg_run.md`](stage12.6a_drift_latlon_iceberg_run.md) | Latitude/longitude drift and `iceberg_run` |
| 12.6b | [`stage12.6b_wave_erosion.md`](stage12.6b_wave_erosion.md) | Wave erosion and optional Stokes drift |
| 12.7.audit | [`stage12.7.audit_voxel_melt.md`](stage12.7.audit_voxel_melt.md) | Voxel geometry/mass mapping audit |
| 12.7a | [`stage12.7a_enderlin23_hindcast.md`](stage12.7a_enderlin23_hindcast.md) | Prescribed Enderlin23 hindcast |
| 12.7b | [`stage12.7b_autonomous_air.md`](stage12.7b_autonomous_air.md) | Autonomous voxel air balance |
| 12.7c | [`stage12.7c_free_convection.md`](stage12.7c_free_convection.md) | Free-convection closure and remaining deficit |
| 12.8 | [`stage12.8_barents2020_matrix.md`](stage12.8_barents2020_matrix.md) | Exploratory 24-run Barents matrix with fallback forcing |
| 12.9a | [`stage12.9a_daily_forcing_acquisition.md`](stage12.9a_daily_forcing_acquisition.md) | Completed 24-month ERA5/GLORYS/WAM acquisition with provenance |
| 12.10 | [`stage12.10_voxel_thermodynamics_improvement.md`](stage12.10_voxel_thermodynamics_improvement.md) | Face-specific thermal BCs, cavity classification, 3D output and short real-data experiments |
| 12.11 | [`stage12.11_final_audit_2020_2024.md`](stage12.11_final_audit_2020_2024.md) | Final audit, visualization/freeboard corrections, data audit and 2020/2024 readiness |
| 12.12 | [`stage12.12_resolution_geometry_audit.md`](stage12.12_resolution_geometry_audit.md) | Resolution recovery, geometry correction, voxel/prism audit and fallback transparency |
| 12.13 | [`stage12.13_voxel_prism_convergence_annual_readiness.md`](stage12.13_voxel_prism_convergence_annual_readiness.md) | Voxel-authoritative prism sync, vertical compaction, convergence/sensitivity audit, palettes/S plots and no annual promotion |
| 12.14 | [`stage12.14_hindcast_convergence_annual_100cube.md`](stage12.14_hindcast_convergence_annual_100cube.md) | Enderlin blocked by missing site data; Richardson p=0.711; 100^3 2020/2024 strict-ocean 365-day runs; footprint/energy diagnostics |
| 12.15 | [`stage12.15_enderlin_current_and_drift_maps.md`](stage12.15_enderlin_current_and_drift_maps.md) | Current-code Enderlin 190/190 (median ratio 0.540, Spearman 0.156); 2020/2024 drift maps; force-diagnostic CSV |
| 12.16 | [`stage12.16_drift_diagnostics_ensemble_energy.md`](stage12.16_drift_diagnostics_ensemble_energy.md) | Drift-force audit (no bug), Enderlin baselines, 12-start 2024 ensemble, layer-resolved drag, energy ledger |

The 12.8 drift and lifetime results are lower bounds from monthly GLORYS and
constant-atmosphere fallbacks; they are not daily-forcing validation. No stage
report currently claims quantitative daily-forcing performance.

## Evidence and figures

- `evidence/` — Stage 12.7 and 12.8 manifests, result tables, and summaries.
- `evidence/stage12.16/` — drift test log, Enderlin baseline/correlation/site tables, ensemble CSV/JSON, and energy/footprint closure JSONs (Stage 12.16).
- `figures/enderlin23/` — plots from Stage 12.7a.
- `figures/barents2020/` — plots from Stage 12.8.
- `figures/voxel_demo/` — spatial fields and diagnostics from Stage 12.10.
- `figures/stage12.11/` — control and annual diagnostics for 2020/2024 (Stage 12.11).
- `figures/stage12.12/` — resolution convergence, 100^3 fields and voxel/prism consistency (Stage 12.12).
- `figures/stage12.13/` — updated palettes, salinity/cut-away, face profiles, convergence and prism-sync diagnostics (Stage 12.13).
- `figures/stage12.14/` — 100^3 annual fields, convergence, face profiles and footprint diagnostics (Stage 12.14).
- `figures/stage12.15/` — current-code Enderlin scatter/metrics and 2020/2024 drift/melt maps (Stage 12.15).
- `figures/stage12.16/` — Enderlin ratio drivers and 2024 12-start ensemble maps (Stage 12.16).
- `STAGE12_PREPARATION.md` and `transition_analysis.md` — archived planning
  records, not active work plans.

## Current status

Stage 12.9 separates into two workstreams:

| Workstream | Status |
| --- | --- |
| 12.9a Daily-forcing acquisition | **COMPLETE (2026-11-07)**; 24/24 months for ERA5, GLORYS12, and WAM. No further downloads are needed. |
| 12.9b Thesis writing | **GO with fallback labeling**; Stage 12.8 results are exploratory, not daily-forcing validation. |

**12.11 audit status:** the 2020 annual run is a 365-day run with 3,154
land/no-data forcing fallback warnings; the 2024 run melts out at 268.8 days.
Neither is a publication-quality full-year comparison. See
[`stage12.11_final_audit_2020_2024.md`](stage12.11_final_audit_2020_2024.md).

**12.12 audit status:** the 1 m / 100^3 science grid is restored as the target;
8^3 is a test grid only. The 100^3 30-day test took 480 s and 799 MB RSS, but
resolution is not fully converged and no annual 100^3 run was performed. See
[`stage12.12_resolution_geometry_audit.md`](stage12.12_resolution_geometry_audit.md).

**12.13 audit status:** voxel/prism mass and draft/freeboard are synchronized; the
100^3 30-day run took about 495 s and 782 MB RSS. The 70^3 30-day mass loss
differs from 100^3 by 1.04%, so no lower resolution meets <1%. The 2020/2024
annual runs were **not** promoted; the 2020 fallback-free candidate is
`78N, 30E` in short tests, but no annual run was made. See
[`stage12.13_voxel_prism_convergence_annual_readiness.md`](stage12.13_voxel_prism_convergence_annual_readiness.md).

**12.14 audit status:** Enderlin rerun is blocked by absent Antarctic site forcing; 30-day order is `p=0.711` with a `3.75%` 100^3 error; 100^3 2020/2024 strict-ocean runs reached 365.0 d of requested 366 d with no fallback. See [`stage12.14_hindcast_convergence_annual_100cube.md`](stage12.14_hindcast_convergence_annual_100cube.md).

**12.16 status:** the drift audit confirms the wind force is applied and
Coriolis-limited (7/15 m/s analytical test matches the discrete equilibrium;
ensemble mean speeds 0.003–0.026 m/s), not a missing-wind/sea-ice/unit bug.
Twelve 2024 50^3 starts give 26.8–97.0% mass loss for the nine long runs, with
P08/P11 grounding early and P10 leaving ocean data at day 41; only P04 reaches
10% remaining mass (t90 = 311 d). Layer-resolved voxel drag replaces the
prism side-area integral for active voxel runs; the 30-day energy residual is
0.067% (50^3) and 0.664% (100^3) of latent after adding the melted-mass
sensible enthalpy. See
[`stage12.16_drift_diagnostics_ensemble_energy.md`](stage12.16_drift_diagnostics_ensemble_energy.md).

**12.15 status:** with the site forcing present, the Enderlin23 hindcast
completed 190/190 on the current code: median ratio 0.540, mean 1.081,
Spearman 0.156, MAE 0.0287 m/day, bias −0.0219 m/day; median ratios by size
are 1.248 (≤100 m), 0.832 (100–300 m), 0.407 (>300 m). The 8^3 test grid was
used, so this is not a resolution-converged result. The 2020/2024 100^3
trajectories are 192.0/168.2 km with mean speeds 0.00607/0.00532 m/s, the
documented Coriolis-limited drift regime. See
[`stage12.15_enderlin_current_and_drift_maps.md`](stage12.15_enderlin_current_and_drift_maps.md).

Check `docs/validation/INDEX.md` for active work and
`docs/references/reanalysis_data_plan.md` for the data contract.
