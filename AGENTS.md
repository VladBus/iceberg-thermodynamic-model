# AGENTS.md — AARI Iceberg Thermodynamic & Dynamics Model

This file is the short repository entry point for agents. Detailed process rules
are in `RULES.md`; style conventions are in `STYLE.md`; current limitations are
in `KNOWN_ISSUES.md`; the documentation map is `docs/README.md`.

## Current project state

- **Stage 11 is frozen** as a research artifact. Do not present it as a
  production-validated prognostic ocean; see
  `docs/wiki/stages/stage11/STAGE11_FREEZE.md`.
- **Stage 12 is active.** Stage 12.8's 24-run Barents matrix is the latest
  completed published validation. Stage 12.9a daily-forcing acquisition is
  complete (24/24 months for ERA5, GLORYS12, and WAM; 2026-11-07); do not start
  additional downloads. Stage 12.10 voxel thermal-boundary improvements and 3D
  output are complete (2026-11-08); Stage 12.11 final audit and
  2020/2024 readiness check are complete, and Stage 12.12 recovered the 1 m
  reference grid and audited geometry/voxel-prism consistency, with annual-quality
  caveats. Stage 12.13 synchronized voxel/prism mass and draft/freeboard, added vertical
  layer compaction, tested 70^3 convergence, and confirmed that no lower
  resolution meets <1%. Stage 12.14 blocked the Enderlin rerun on missing
  Antarctic site forcing, obtained p=0.711 (100^3 error 3.75%), and ran strict
  100^3 2020/2024 experiments to 365.0 d of requested 366 d. Stage 12.9b thesis
  writing is the active workstream. See `docs/validation/INDEX.md` and
  `docs/references/reanalysis_data_plan.md`.
- Check `docs/model/model_physics_status.md`, `docs/DECISIONS.md`, and
  `KNOWN_ISSUES.md` before making claims about physics, switches, or open issues.

## Before starting work

1. Read `AGENTS.md`, `docs/README.md`, current `git status`, and the relevant
   stage index before opening a new report.
2. Search `KNOWN_ISSUES.md` and `docs/DECISIONS.md` for the issue or topic; if it
   is already recorded, update or close that entry instead of creating a
   duplicate document.
3. Open the linked stage report, test, or decision to see what was actually
   verified. Do not infer results from file names or old summaries.
4. If a new document is still needed, follow the placement rules below and add
   it to the existing index; do not create a second navigation tree.

## Knowledge reuse decision tree

| Situation | Action |
| --- | --- |
| Information is documented and current | Use the authoritative source; do not create another report. |
| Information is documented but outdated | Verify against code/tests/newer reports; update the authoritative document; preserve history; record a decision if scientific applicability changes. |
| Information exists only in a historical report | Update the current source of truth, link to the historical report, and do not copy it wholesale. |
| Information is genuinely new | Choose the correct document category, create one document only when justified, and update indexes/incoming links. |
| Evidence is insufficient | State exactly what is missing, investigate only that gap, and never invent a result or assume an unverified conclusion. |

## Documentation routing

| Need | Read |
| --- | --- |
| Full map and document roles | [`docs/README.md`](docs/README.md) |
| Development, verification, commit, and documentation rules | [`RULES.md`](RULES.md) |
| Code and Markdown style | [`STYLE.md`](STYLE.md) |
| Current issues and constraints | [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) |
| Current physics and switches | [`docs/model/model_physics_status.md`](docs/model/model_physics_status.md) |
| Equations and conventions | [`docs/model/model_equation_ledger.md`](docs/model/model_equation_ledger.md) |
| Active work status | [`docs/validation/INDEX.md`](docs/validation/INDEX.md) |
| Stage 11 freeze | [`docs/wiki/stages/stage11/STAGE11_FREEZE.md`](docs/wiki/stages/stage11/STAGE11_FREEZE.md) |
| Stage 12 data contract | [`docs/references/reanalysis_data_plan.md`](docs/references/reanalysis_data_plan.md) |
| Completed stage reports | [`docs/wiki/INDEX.md`](docs/wiki/INDEX.md) and each stage `README.md` |
| Superseded plans/provenance | [`docs/archive/README.md`](docs/archive/README.md) |
| Decisions | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Data products and provenance | [`docs/references/data_sources.md`](docs/references/data_sources.md) |

## Documentation placement (mandatory)

Before creating or editing a document, classify it:

1. **Current model physics, mathematics, equations, or switches** → `docs/model/`.
   This directory contains no stage plans and no stage reports.
2. **Literature, scientific premises, data sources, or provenance** →
   `docs/references/`.
3. **Completed stage/commit report and its curated evidence** →
   `docs/wiki/stages/<stage>/`. Update that stage's `README.md` and
   `docs/wiki/INDEX.md` in the same change.
4. **Unfinished current validation work** → `docs/validation/` only. It is a
   temporary workspace; move the report and evidence out when the stage closes.
5. **Superseded plans, local operational notes, or old provenance** →
   `docs/archive/`.

Never create a parallel top-level documentation tree, a second index for the
same fact, or a new report when a current source already covers the topic.
Link to the authoritative report, test, or decision instead of copying its
contents. The detailed rules are in `RULES.md`; the map and read order are in
`docs/README.md`.

## Resource discipline

The user's WSL2 instance currently has **8 GB allocated RAM** (user-reported on
2026-11-03; CPU allocation is not measured). Run expensive builds, test
batteries, analyses, and data transfers **sequentially**, not as parallel jobs.
Do not launch multiple downloads or broad repository scans together. Prefer a
targeted command and bounded output; stop a run before starting another if
memory usage is uncertain. Do not start additional data downloads unless
explicitly requested.

## Build and test commands

Always pass `-I/usr/include` because `netcdf.mod` is installed there. With
fpm 0.13.0-alpha, remove `build/` before a test run to avoid stale libraries.

```bash
fpm build --flag "-I/usr/include"
fpm run --flag "-I/usr/include"
rm -rf build
fpm test --flag "-I/usr/include"
```

Fortran strict diagnostics:

```bash
fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"
```

Python uses the external conda environment `iceberg-thermodynamic-model`; do not
create a virtual environment inside the repository.

## Model conventions

- Hydrodynamics use CGS; thermodynamics use SI with temperature in °C and
  salinity as mass fraction (about 0.033–0.035, not PSU). NetCDF output is SI;
  conversions belong at I/O boundaries. See `docs/model/model_equation_ledger.md`.
- The land mask is `8888.0`; compare reals with an epsilon, never `==`.
- Grid axes: X ↔ `j` ↔ `u`; Y ↔ `i` ↔ `v`; the Y axis is inverted.
- Calendar day `d` is `start_date + d days`: day 00 is the initial state and
  day 01 is after one integration day.
- Post-processing must use a run manifest; never glob all run outputs.

## Non-negotiable scientific constraints

- Do not change canonical ocean/sea-ice physics, EOS precision, the
  `0.9e-7` convective threshold, FCT anti-diffusion (`CDY*0`), or the
  `hht<0.01` guard without the documented scientific review and approval in
  `RULES.md`.
- Do not use `grid_mode=TEST` for production claims.
- Do not enable heat (`kl1=1`) without the required ERA5 humidity, cloud, and
  precipitation fields.
- Iceberg forcing remains one-way and offline/prescribed. Do not add two-way
  coupling or unapproved physics.
- Melt coefficients are compile-time constants and require a rebuild.
- Production grid and sea-ice inputs are NetCDF. Legacy grid/ice files are
  offline regression fixtures; do not restore root-level legacy symlinks.
- Never commit credentials, generated data, or run outputs. Check `.gitignore`
  and `RULES.md` before staging. Do not commit or push unless explicitly asked.
