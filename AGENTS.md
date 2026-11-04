# AGENTS.md — AARI Iceberg Thermodynamic & Dynamics Model

This file is the short repository entry point for agents. Detailed process rules
are in `RULES.md`; style conventions are in `STYLE.md`; current limitations are
in `KNOWN_ISSUES.md`; the documentation map is `docs/README.md`.

## Current project state

- **Stage 11 is frozen** as a research artifact. Do not present it as a
  production-validated prognostic ocean; see
  `docs/wiki/stages/stage11/STAGE11_FREEZE.md`.
- **Stage 12 is active.** Stage 12.8's 24-run Barents matrix is the latest
  completed stage in the published validation index. Daily-forcing acquisition
  was explicitly resumed on 2026-11-04 and is running sequentially; do not start
  additional downloads unless explicitly requested. See
  `docs/validation/INDEX.md` and `docs/references/reanalysis_data_plan.md`.
- Check `docs/model/model_physics_status.md`, `docs/DECISIONS.md`, and
  `KNOWN_ISSUES.md` before making claims about physics, switches, or open issues.

## Documentation routing

| Need | Read |
| --- | --- |
| Full map and document roles | `docs/README.md` |
| Development, verification, commit, and documentation rules | `RULES.md` |
| Code and Markdown style | `STYLE.md` |
| Current issues and constraints | `KNOWN_ISSUES.md` |
| Current physics and switches | `docs/model/model_physics_status.md` |
| Equations and conventions | `docs/model/model_equation_ledger.md` |
| Active work status | `docs/validation/INDEX.md` |
| Stage 11 freeze | `docs/wiki/stages/stage11/STAGE11_FREEZE.md` |
| Stage 12 data contract | `docs/references/reanalysis_data_plan.md` |
| Completed stage reports | `docs/wiki/INDEX.md` and `docs/wiki/stages/<stage>/README.md` |
| Superseded plans/provenance | `docs/archive/README.md` |
| Decisions | `docs/DECISIONS.md` |
| Data products and provenance | `docs/references/data_sources.md` |

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
