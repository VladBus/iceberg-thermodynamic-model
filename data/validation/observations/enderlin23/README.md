# Enderlin23 Per-Iceberg Dataset — Stage 12 Validation Copy

This directory is a **stable validation copy** of the Stage 10.18D per-iceberg
dataset. The canonical source of the derivation is
`data/validation/observations/stage10.18d/`; this copy is staged for Stage 12
so the voxel-model validation does not depend on a stage-specific folder name.

## Contents

| File | Purpose |
|---|---|
| `enderlin23_per_iceberg.csv` | 743 per-iceberg observations, 15 Antarctic sites, 2011–2022 |
| `provenance.md` | row-by-row transformation and limitations (copied verbatim) |
| `sources.csv` | citation and retrieval metadata |
| `SHA256SUMS` | integrity check for this copy |

The raw USAP-DC archive and its 54 extracted CSVs are **not duplicated here**;
they remain under `stage10.18d/raw/` (gitignored). Re-fetch instructions are in
`stage10.18d/provenance.md` and `docs/data_sources.md`.

## Provenance summary

- **Paper:** Enderlin et al. (2023), *Journal of Glaciology* 69(278),
  doi:10.1017/jog.2023.54.
- **Dataset:** USAP-DC 601679, doi:10.15784/601679, CC BY 4.0.
- **Derived CSV:** 743 rows (header + 743 observations); submarine-total melt
  (`VolumeChangeRate / SubmergedArea_mean`), not lateral-only melt.
- **No ocean velocity:** `U_rel` is not observed; velocity-resolved validation
  remains a separate campaign requirement.

## Validation use

Use `independence_group` (15 site clusters), not 743 independent units. Do not
compare this Antarctic dataset directly to Barents drift; use it for
thermodynamic/melt checks only.

## Integrity

`enderlin23_per_iceberg.csv` MD5:
`43817b0c3b1f7a4939182453727e4d79`

Verify the whole directory with:

```bash
cd data/validation/observations/enderlin23
sha256sum -c SHA256SUMS
```
