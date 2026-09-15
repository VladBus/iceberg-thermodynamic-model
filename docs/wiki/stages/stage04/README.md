# Stage 4 — ERA5-интеграция, конвективный цикл, точность EOS

Интеграция ERA5-форсинга, корневая причина конвективного цикла (float32-квантование EOS), прецизионное исследование.

## Отчёты (5)

ERA5 на TEST-сетке (4.1), январь 2020 (4.2), корневая причина конвективного цикла (4.3), float-точность EOS (4.3b), прецизионный критерий (4.4).

| Файл                                | Отчёт                                                                       |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `Stage4.1_monthly_era5_test.md`     | Stage 4.1 — Monthly ERA5 Integration on TEST Grid                           |
| `Stage4.2_january2020.md`           | Stage 4.2 — January 2020 ERA5 Integration + Python Analysis Workflow        |
| `Stage4.3_convective_root_cause.md` | Stage 4.3 — Root-Cause Analysis: Convective-Adjustment Guard Cycling        |
| `Stage4.3b_eos_precision.md`        | Stage 4.3b — IEEE-754 / Float-Precision Verification of the EOS Root Cause  |
| `Stage4.4_precision_study.md`       | Stage 4.4 — Precision-Safe Convective Criterion: Controlled Numerical Study |

## Статус

- **ARCHIVED** — материалы стадии завершены и не редактируются задним числом.
- Актуальное состояние модели см. в `../../../model/`; решения — в `../../../DECISIONS.md`.
- Общая навигация: `../../README.md` → `../../INDEX.md`.
