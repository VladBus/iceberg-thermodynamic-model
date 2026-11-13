# Active Validation Workspace

This directory is reserved for **unfinished, current validation work**. It is
not a permanent report archive. Completed reports and their retained evidence
belong in `docs/wiki/stages/<stage>/`; obsolete working plans belong in
`docs/archive/`.

## Stage 12.9 status

Stage 12.9 has two distinct workstreams:

| Workstream | Status | Evidence |
| --- | --- | --- |
| 12.9a Daily-forcing acquisition (ERA5/GLORYS/WAM) | **COMPLETE (2026-11-07)**; all 24 months for 2020 and 2024 acquired. No further downloads are needed. | [`stage12.9a`](../wiki/stages/stage12/stage12.9a_daily_forcing_acquisition.md); acquisition manifests in this directory. |
| 12.9b Thesis writing | **GO with fallback labeling**; can use Stage 12.8 exploratory results, but must not claim quantitative daily-forcing validation. | [`stage12.8`](../wiki/stages/stage12/stage12.8_barents2020_matrix.md), [`DECISIONS.md`](../DECISIONS.md) D-63. |

Stage 12.10 (voxel thermal-boundary improvement and short real-data
experiments), Stage 12.11 (final audit, visualization/freeboard corrections, data
readiness, and 2020/2024 experiments), Stage 12.12 (resolution recovery and
geometry audit) and Stage 12.13 (voxel/prism sync, convergence and annual
readiness), Stage 12.14 (100^3 annual, convergence, tail and footprint audit),
and Stage 12.15 (current-code Enderlin rerun and 2020/2024 drift maps) and
Stage 12.16 (drift audit, ensemble, layer drag, energy ledger) are complete;
the reports are in
[`stage12.10`](../wiki/stages/stage12/stage12.10_voxel_thermodynamics_improvement.md)
and [`stage12.11`](../wiki/stages/stage12/stage12.11_final_audit_2020_2024.md)
and [`stage12.12`](../wiki/stages/stage12/stage12.12_resolution_geometry_audit.md)
and [`stage12.13`](../wiki/stages/stage12/stage12.13_voxel_prism_convergence_annual_readiness.md)
and [`stage12.14`](../wiki/stages/stage12/stage12.14_hindcast_convergence_annual_100cube.md)
and [`stage12.15`](../wiki/stages/stage12/stage12.15_enderlin_current_and_drift_maps.md)
and [`stage12.16`](../wiki/stages/stage12/stage12.16_drift_diagnostics_ensemble_energy.md)
and [`stage12.17`](../wiki/stages/stage12/stage12.17_final_runs_and_figures.md)
and [`stage12.18`](../wiki/stages/stage12/stage12.18_final_runs_and_figures.md).

### Acquisition manifests

| Manifest | Git state | Meaning |
| --- | --- | --- |
| `stage12.9_glorys_manifest.json` | tracked | Versioned acquisition provenance for the completed GLORYS12 subset. |
| `stage12.9_wam_manifest.json` | tracked | Versioned acquisition provenance for the completed WAM subset. |
| `stage12.9_era5_manifest.json` | tracked | Versioned acquisition provenance for the completed ERA5 subset. |

The Stage 12.11 local data audit is
[`stage12.11_data_audit.json`](stage12.11_data_audit.json). The manifests remain
in this directory because the acquisition tools use these paths as their
canonical provenance location. They are provenance records, not
Stage 12 validation reports; do not present partial month counts as scientific
results.

## Completion and archival rule

When a stage is complete, prepare a report with results, methods, inputs,
provenance, limitations, and verification status. Move the report and curated
stage evidence to `docs/wiki/stages/<stage>/`, update that stage's `README.md`
and `docs/wiki/INDEX.md`, and remove only temporary files that are verified to
be regenerable. Preserve source data and provenance. Current model status belongs
in `docs/model/`; current assumptions and data sources belong in
`docs/references/`.

## Historical reports

Stage 11 reports have been moved to `docs/wiki/stages/stage11/`. Completed Stage
12 reports and evidence are under `docs/wiki/stages/stage12/`. Historical
provenance records are in `docs/archive/provenance_archive/`.
