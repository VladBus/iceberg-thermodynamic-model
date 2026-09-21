<div style="text-align: center;">
  <a>
    <img src="docs/assets/readme/banner.jpg" alt="Banner_image">
  </a>
</div>

<h1 align="center">Iceberg Thermodynamic Model</h1>

![Fortran Version](https://img.shields.io/badge/fortran-gfortran-purple.svg)
![Python Version](https://img.shields.io/badge/python-3.12.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Last Commit](https://img.shields.io/github/last-commit/VladBus/iceberg-thermodynamic-model)
![Repo Size](https://img.shields.io/github/repo-size/VladBus/iceberg-thermodynamic-model)
![Code Size](https://img.shields.io/github/languages/code-size/VladBus/iceberg-thermodynamic-model)
![Top Language](https://img.shields.io/github/languages/top/VladBus/iceberg-thermodynamic-model)
![Activity](https://img.shields.io/badge/activity-high-green)
![Code Style](https://img.shields.io/badge/fortran%20style-fprettify-purple)
![Code Style](https://img.shields.io/badge/python%20style-pep8-blue)
![Stars](https://img.shields.io/github/stars/VladBus/iceberg-thermodynamic-model)
![Watchers](https://img.shields.io/github/watchers/VladBus/iceberg-thermodynamic-model)

<hr>

## 📋 Description

Master's thesis project on modernizing and supplementing the Thermodynamic
Model of Icebergs for modeling processes in the Arctic Ocean (original model
by Dmitrev, 1995).

The repository contains a **Lagrangian iceberg module** embedded in a legacy
Eulerian ocean/sea-ice modeling framework. The iceberg is represented as a
rectangular prism whose position, velocity, and dimensions evolve in time
under atmospheric, oceanic, bathymetric, and sea-ice forcing.

## 📑 Project status

- **Current stage:** Stage 10.18D — velocity-resolved / per-iceberg
  observational upgrade (completed: Enderlin23 per-iceberg dataset of 743
  icebergs retrieved and analyzed — legacy exceeds 99.6 % of observed
  per-iceberg melt at TF = 1.5 °C, per-iceberg C_eff_submarine median 0.16×
  production; ADCP-equipped Schild21-style campaign designed; velocity
  dependence still NOT IDENTIFIABLE; production unchanged).
- **Physics status and switches:** `docs/model/model_physics_status.md`
- **Stage plan and status:** `docs/PROJECT_ROADMAP.md`

## 🔧 Repository components

| Component                                          | Purpose                                                                               |
| -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `src/`                                             | Model source code (Fortran): ocean/ice framework, `iceberg_*.f90` — Lagrangian module |
| `app/main.f90`                                     | Orchestrator: time loop, forcing, output                                              |
| `test/`                                            | Fortran tests (fpm)                                                                   |
| `python/validation/`                               | Independent Python reference models and cross-language comparisons                    |
| `python/tests/`                                    | Python tests for the validation layer                                                 |
| `python/analysis/`, `python/era5/`, `python/grid/` | Analysis, ERA5 download, real-grid generation                                         |
| `data/`                                            | Input data (ERA5, EN4, IBCAO, observations) and run outputs (gitignored)              |
| `docs/`                                            | Documentation: model, validation, stage archive                                       |

## 🚀 Quick start

```bash
# Build and test (always with -I/usr/include; rm -rf build before fpm test)
fpm test --flag "-I/usr/include"

# Strict build
fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"

# Run
fpm run --flag "-I/usr/include" -- <run_id> [era5_file]

# After a fresh clone, regenerate the real-grid inputs:
python python/grid/build_real_grid_inputs.py
```

Python: conda environment `iceberg-thermodynamic-model`
(`conda activate iceberg-thermodynamic-model`).

## 🗺️ Documentation navigation

```
README.md ──→ docs/
               ├─ /model/
               |    ├─ model_physics_status.md (physics status)
               |    ├─ model_equation_ledger.md (equations)
               |    ├─ model_description.md (narrative)
               |    └─ README.md
               ├─ /references/
               |    ├─ citation_map.md
               |    ├─ literature_matrix.md
               |    ├─ references.bib
               |    └─ README.md
               ├─ /validation/INDEX.md (active validation, Stage 10)
               ├─ /wiki/
               |    ├─ INDEX.md (historical stage reports 3–10)
               |    └─ README.md
               ├─ DECISIONS.md (key decisions)
               ├─ PROJECT_ROADMAP.md (stages plan)
               └─ README.md
```

| Looking for                      | Go to                                |
| -------------------------------- | ------------------------------------ |
| AI-agent operating rules         | `AGENTS.md`                          |
| Development process              | `RULES.md`                           |
| Code and documentation style     | `STYLE.md`                           |
| Current known issues             | `KNOWN_ISSUES.md`                    |
| Change history                   | `CHANGELOG.md`                       |
| Physics status                   | `docs/model/model_physics_status.md` |
| Active validation                | `docs/validation/INDEX.md`           |
| Historical archive (stages 3–10) | `docs/wiki/INDEX.md`                 |

## 🔗 References

- License: `LICENSE`
- Key decisions: `docs/DECISIONS.md`
- Full documentation map: `docs/README.md`

<hr>

⭐ **If you find this project useful, please give it a star!**
