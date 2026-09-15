# Validation Index — активная валидация Stage 10

Это индекс отчётов текущей работы над модернизацией термодинамики айсберга
(Stage 10). Материалы Stage 10 остаются здесь, пока Stage 10 в целом не
завершена; затем они будут архивированы в `docs/wiki/stages/stage10/`
(содержимое не переписывается, ссылки обновляются).

Статусы:

- **ACTIVE** — стадия/фаза продолжается, документ актуален для текущей работы;
- **COMPLETED** — стадия завершена, отчёт закрыт, но ещё не архивирован;
- **DRAFT** — черновик/промежуточный документ.

| Документ                                               | Стадия          | Статус                  | Назначение                                                                                                                                                  |
| ------------------------------------------------------ | --------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stage10.7_basal_melt_validation.md`                   | 10.7            | COMPLETED (B)           | Независимая аналитическая валидация базального таяния (17 checks), литературная полоса 0.01–1 m/day                                                         |
| `stage10.8.1_python_validation.md`                     | 10.8.1          | COMPLETED (B)           | Независимый Python-слой валидации (`python/validation/`, 44 checks)                                                                                         |
| `stage10.8.2_observational_validation.md`              | 10.8.2          | COMPLETED (C)           | Наблюдательная валидация базального таяния (19 записей, 229 checks); систематические ограничения задокументированы                                          |
| `stage10.9_calibration_assessment.md`                  | 10.9            | COMPLETED (C)           | Оценка калибруемости коэффициента базального таяния (212 checks); скалярная калибровка не идентифицируется — калибровка НЕ проводилась                      |
| `stage10.10_three_equation_interface.md`               | 10.10 / 10.10.1 | COMPLETED (C)           | Трёхкомпонентный интерфейс лёд–океан (H&J99/J2010); включает коррекцию массово-солевой конвенции 10.10.1 (19+6 Fortran, 46+19 Python)                       |
| `stage10.11_natural_convection.md`                     | 10.11           | COMPLETED (C)           | Естественная конвекция у базальной грани (Ra/Nu, Churchill n=3) — selectable схема                                                                          |
| `stage10.11.2_natural_convection_audit.md`             | 10.11.2         | COMPLETED (B)           | Аудит + поставка Fortran-теста (23 checks); исправлены ошибочные утверждения                                                                                |
| `stage10.11.3_natural_convection_physics_audit.md`     | 10.11.3         | COMPLETED (B)           | Глубокий научный аудит: Ra-кап всегда активен, haline-член инертен, нулевой поток 1.4e-3 m/day не закрывает наблюдательный разрыв; производство НЕ менялось |
| `stage10.12_internal_thermal_evolution.md`             | 10.12           | COMPLETED (C)           | Прогностическая внутренняя температура (двухузловая), switch `thermal_evolution_enabled`; Fortran 21 + Python 35 checks                                     |
| `stage10.12_internal_thermal_evolution_design_note.md` | 10.12           | COMPLETED (design note) | Дизайн-нота Phase A: варианты двухузловой модели и выбор Variant C                                                                                          |
| `stage10.13_diffusion_limited_low_flow_design_note.md` | 10.13           | ACTIVE (Phase A)        | Научная формулировка и литературный аудит low-flow закрытия (MK77 / Keitzl16 / Middleton21)                                                                 |
| `stage10.13_phase_b_results.md`                        | 10.13           | ACTIVE (Phase B)        | Исследовательский прототип `python/validation/low_flow.py`: 167 checks, sweep 246/270 в наблюдательной полосе, 10.8.2 re-scoring                            |
| `stage10.13_phase_c_results.md`                        | 10.13           | ACTIVE (Phase C)        | Производственная интеграция за переключателем `low_flow_closure_enabled` (OFF по умолчанию); Fortran 23 + comparison 56 checks; полная батарея exit 0       |

## Связь с актуальной документацией

- Статус физики: `../model/model_physics_status.md`
- Уравнения: `../model/model_equation_ledger.md`
- Описание модели: `../model/model_description.md`
- План модернизации Stage 10: `../model/stage10_modernization_plan.md`
- Решения: `../DECISIONS.md`
- Архив завершённых стадий: `../wiki/INDEX.md`

## Правила

- Отчёты здесь не переписываются после завершения стадии (исключение —
  технические навигационные правки).
- После завершения всей Stage 10 каталог будет архивирован в
  `docs/wiki/stages/stage10/` с обновлением ссылок и индексов.
