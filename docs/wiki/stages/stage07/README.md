# Stage 7 — снег/лёд, устойчивость, IBCAO-сетка, инициализация льда и океана

Пространственный снегопад, баланс массы, устойчивость динамики льда, реконструкция реальной сетки из IBCAO, реальная инициализация льда и океана, стабилизация (7.7A–7.9).

## Отчёты (18)

Снегопад и баланс массы (7.1–7.2), устойчивость динамики (7.3–7.4), реальная сетка и инициализация льда (7.5–7.6C), океан: форензика, выбор данных, стабилизация (7.7–7.7C), спин-ап и геострофия (7.8–7.9).

| Файл                                                      | Отчёт                                                                                               |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `Stage7.1_spatial_snowfall_forcing.md`                    | Stage 7.1 — Spatially Distributed ERA5 Snowfall Forcing                                             |
| `Stage7.2_mass_balance_validation.md`                     | Stage 7.2 — Snow/Ice Mass-Balance & Observational Validation Report                                 |
| `Stage7.3_stability_investigation.md`                     | Stage 7.3 — Ice Dynamics Stability Investigation Report                                             |
| `Stage7.4_stability_resolution.md`                        | Stage 7.4 — Ice Dynamics Stability Resolution Report                                                |
| `Stage7.5_real_grid_initial_ice_investigation.md`         | Stage 7.5 — Real Grid and Initial Ice Data Investigation                                            |
| `Stage7.6A.1_Fortran_grid_compatibility_audit.md`         | Stage 7.6A.1 — Fortran Grid Compatibility Audit                                                     |
| `Stage7.6A_IBCAO_real_grid_reconstruction.md`             | Stage 7.6A — IBCAO V5.2 → Real Geographic Model Grid Reconstruction                                 |
| `Stage7.6B_Real_grid_input_reconstruction.md`             | Stage 7.6B: Real Grid Input Reconstruction & Diagnostic Run                                         |
| `Stage7.6C.1_Real_ice_initialization.md`                  | Stage 7.6C.1: Real Ice Initialization — OSI-SAF SIC + C3S SIT → 1_k.ice                             |
| `Stage7.6C.2_ERA5_forcing_expansion_and_hot_run.md`       | Stage 7.6C.2: ERA5 Forcing-Domain Expansion & Real-Ice Hot Run                                      |
| `Stage7.7A_Dynamic_Imbalance_Stability_Forensic_Audit.md` | Stage 7.7A — Dynamic Imbalance & Stability Forensic Audit                                           |
| `Stage7.7B_Realistic_Ocean_Stabilization.md`              | Stage 7.7B — Realistic Ocean Initialization Stabilization: Final Report                             |
| `Stage7.7C_Dynamically_Balanced_Ocean_Initialization.md`  | Stage 7.7C — Dynamically Balanced Realistic Ocean Initialization: Final Report                      |
| `Stage7.7_Initial_Ocean_Forensic_Audit.md`                | Stage 7.7 — Phase 1: Initial Ocean T/S Forensic Audit                                               |
| `Stage7.7_Ocean_Dataset_Selection.md`                     | Stage 7.7 — Phase 2: Dataset Selection for Realistic Initial Ocean T/S                              |
| `Stage7.7_Realistic_Ocean_Initialisation.md`              | Stage 7.7 — Realistic Ocean Initial Conditions: Final Report                                        |
| `Stage7.8_Numerical_Compatibility_and_Balanced_Spinup.md` | Stage 7.8 — Numerical Compatibility and Balanced Spin-Up for Realistic Arctic Ocean State           |
| `Stage7.9_Reference_Level_and_Dynamic_Height.md`          | Stage 7.9 — Reference-Level Geostrophic Initialization and Dynamic-Height Consistency: Final Report |

## Статус

- **ARCHIVED** — материалы стадии завершены и не редактируются задним числом.
- Актуальное состояние модели см. в `../../../model/`; решения — в `../../../DECISIONS.md`.
- Общая навигация: `../../README.md` → `../../INDEX.md`.
