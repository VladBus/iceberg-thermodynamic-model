# Active Validation Workspace

This directory is reserved for **unfinished, current validation work**. It is
not a permanent report archive. Completed reports and their retained evidence
belong in `docs/wiki/stages/<stage>/`; obsolete working plans belong in
`docs/archive/`.

## Current work: Stage 12.9

Stage 12.9 has two distinct workstreams:

| Workstream | Status | Evidence |
| --- | --- | --- |
| 12.9a Daily-forcing acquisition (ERA5/GLORYS/WAM) | **IN PROGRESS**; resumed by explicit user request on 2026-11-04 and running month by month. Do not start additional downloads unless the user asks. | Acquisition manifests in this directory; Stage 12.8 remains the latest completed published validation. |
| 12.9b Thesis writing | **GO with fallback labeling**; can use Stage 12.8 exploratory results, but must not claim quantitative daily-forcing validation. | [`stage12.8`](../wiki/stages/stage12/stage12.8_barents2020_matrix.md), [`DECISIONS.md`](../DECISIONS.md) D-63. |

### Acquisition manifest policy

| Manifest | Git state | Meaning |
| --- | --- | --- |
| `stage12.9_glorys_manifest.json` | tracked | Versioned acquisition provenance for the GLORYS12 subset. |
| `stage12.9_wam_manifest.json` | tracked | Versioned acquisition provenance for the WAM subset. |
| `stage12.9_era5_manifest.json` | local/untracked while acquisition is active | Operational state for the in-progress monthly ERA5 acquisition. Commit it only after the acquisition is complete, verified, and explicitly closed. |

These manifests are provenance/operational records, not Stage 12 validation
reports. Do not present partial month counts as scientific results.

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
