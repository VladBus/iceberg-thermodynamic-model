# iceberg-thermodynamic-model

Master's thesis project on modernizing and supplementing the Thermodynamic
Model of Icebergs for modeling processes in the Arctic Ocean (original model
by Dmitrev, 1995).

The repository contains a **Lagrangian iceberg module** embedded in a legacy
Eulerian ocean/sea-ice modeling framework. The iceberg is represented as a
rectangular prism whose position, velocity, and dimensions evolve in time
under atmospheric, oceanic, bathymetric, and sea-ice forcing.

## Project status

- **Current stage:** Stage 10.14 — re-scoring of the 10.8.2 observational set
  against the three-equation / 3eq+natural-convection closures (verification
  only; no calibration, no production change).
- **Physics status and switches:** `docs/model/model_physics_status.md`
- **Stage plan and status:** `docs/PROJECT_ROADMAP.md`

## Repository components

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

## Quick start

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

## Documentation navigation

```
README.md ──→ docs/README.md ──→ docs/model/README.md
                                  ├─ model_physics_status.md (physics status)
                                  ├─ model_equation_ledger.md (equations)
                                  └─ model_description.md (narrative)
                    docs/validation/INDEX.md (active validation, Stage 10)
                    docs/wiki/INDEX.md (historical stage reports 3–10)
                    docs/DECISIONS.md (key decisions)
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

## References

- License: `LICENSE`
- Key decisions: `docs/DECISIONS.md`
- Full documentation map: `docs/README.md`
