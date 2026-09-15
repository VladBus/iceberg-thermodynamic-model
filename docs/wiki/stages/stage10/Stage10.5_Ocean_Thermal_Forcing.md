# Stage 10.5 — Ocean Thermal Forcing (Океанический тепловый форсинг)

**Дата:** 2026-09-08
**Ветка:** master
**Base commit:** ca8d7381fdd69212793c50fac9cbf63add6456c9 (Stage 10.4.2.1)
**Классификация:** C — модернизировано и независимо валидировано

---

## Резюме

Цепочка океанического форсинга (EN4 → черновик → базальное/боковое таяние) модернизирована:
точка замерзания морской воды переведена с legacy линейной аппроксимации Зубова `Tf = -54·S`
на уравнение состояния морской воды **EOS-80 (UNESCO 1983 / Fofonoff & Millard)**: `Tf = f(S, p)`,
с давлением `P = ρ_w·g·z`. Добавлен диагностический термоген `delta_t_ocean = T(D) - Tf(D)`.

Производственная физика модели айсберга **изменена** (не только диагностика).

---

## Физика

### Каноническая формула (src/iceberg_types.f90)

```
ocean_freezing_point(S_mass, depth_m):
  S_PSU = 1000 · S_mass
  P_dbar = ρ_w · g · depth_m / 1.0e4
  Tf = (EOS_FP_A0 + EOS_FP_A1·sqrt(S_PSU) - EOS_FP_A2·S_PSU) · S_PSU + EOS_FP_BP · P_dbar

EOS_FP_A0 = -0.0575        °C/PSU
EOS_FP_A1 =  1.710523e-3   °C/PSU^(3/2)
EOS_FP_A2 =  2.154996e-4   °C/PSU^2
EOS_FP_BP = -7.53e-4       °C/dbar
```

- **Источник:** Fofonoff & Millard 1983 (UNESCO TPMS 44, §5); Gill 1982 (Atmosphere–Ocean Dynamics, Eq. 3.5.2)
- **Литературный checkvalue:** Tf(S=40 PSU, P=500 dbar) = **-2.588567 °C** — воспроизведён (тест 10.5.6, float32: -2.5885675)
- **Единицы:** S — практическая солёность [PSU] = 1000·(массовая доля); P — гидростатическое давление [dbar] = ρ_w·g·z/10⁴ (ρ_w=1027.5, g=9.81)

### Точки применения (3 сайта)

1. `compute_basal_melt` (iceberg_thermodynamics.f90) — Tf на глубине черновика D: `tf_draft = ocean_freezing_point(s_draft, draft)`
2. `depth_averaged_thermal_forcing` (iceberg_forcing.f90) — послойно `Tf(z_k)` на центрах уровней + глубокий слой `Tf(salt_deep, max_z)`
3. Обёртка `freezing_point(S, 0)` — поверхностная Tf (p=0), legacy вызов совместим

### Диагностика

`diag%delta_t_ocean = T(D) - Tf(D)` — **необрезанная** (может быть ≤ 0), в отличие от `ΔT_b = max(0, T(D)-Tf(D))` для таяния.

### Отличие от legacy

|                                 | Legacy Zubov    | EOS-80 (Stage 10.5)                    |
| ------------------------------- | --------------- | -------------------------------------- |
| Формула                         | Tf = -54·S [°C] | (A0 + A1√S - A2·S)·S + BP·P            |
| S=0.0345 кг/кг @ пов.           | -1.863 °C       | **-1.894 °C** (на ~0.03 °C холоднее)   |
| Давление                        | нет             | -7.53e-4 °C/dbar (до -0.07 °C на 88 м) |
| Суммарный сдвиг при осадке 88 м | —               | **~-0.1 °C** ≈ 3% типичного ΔT ~3 °C   |

---

## Следствие для регрессий (ВАЖНО)

С давлением EOS точка замерзания на глубине:

- Tf(S=0.0345) ≈ -1.894 - 0.00076·z

При этом «холодный океан» тестов T=-1.9 °C оказывается **выше Tf ниже ~8 м** → спонтанное
базальное таяние, которого не должно быть. Порог всех «холодноокеанских» регрессий уточнён с
**-1.9 до -2.5 °C** (Tf(-2.5 @ 88 м) ≈ -2.56 °C — заведомо ниже). Затронуты 11 файлов:

- test/iceberg_test_2_zero_gradient.f90
- test/iceberg_test_3_uniform_current.f90
- test/iceberg_test_4_vertical_shear.f90 (2 профиля)
- test/iceberg_test_6_cold_ocean.f90
- test/iceberg_test_8_wind_forcing.f90
- test/iceberg_test_9_coriolis_only.f90
- test/drift_scaling_wind.f90
- test/drift_scaling_wind_no_cor.f90
- test/drift_scaling_current.f90
- test/iceberg_test_moving_trajectory.f90
- test/iceberg_test_ibcao_interp.f90

---

## Изменённые файлы

- **src/iceberg_types.f90** — константы `EOS_FP_*`, каноническая pure-функция `ocean_freezing_point`,
  поле `delta_t_ocean` в `iceberg_diagnostics`, заголовок версии → Stage 10.5
- **src/iceberg_thermodynamics.f90** — `compute_basal_melt` (Tf на D), `freezing_point` wrapper → `ocean_freezing_point(S, 0)`,
  установка `diag%delta_t_ocean` в `iceberg_thermodynamics_step`, комментарии
- **src/iceberg_forcing.f90** — `depth_averaged_thermal_forcing`: послойный Tf(z_k) + глубокий слой
- **12 тестовых файлов** (см. выше + iceberg_test_7 переписан)
- **Документация** — model_equation_ledger.md (§4.5–4.7), model_physics_status.md (строка 4 → C),
  stage10_modernization_plan.md (§10.5 ✅), AGENTS.md (устаревшие утверждения про 45 м и lat/lon исправлены)

---

## Тесты

### Stage 10.5 audit (тест 7, iceberg_test_7_vertical_temp_gradient)

| №       | Проверка                                                    | Результат |
| ------- | ----------------------------------------------------------- | --------- |
| 10.5.1  | Чистая вода у поверхности замерзает при 0 °C                | OK        |
| 10.5.2  | Tf поверхности: S=34.5 → -1.8936, S=35 → -1.9223 °C         | OK        |
| 10.5.3  | Tf монотонно растёт с S                                     | OK        |
| 10.5.4  | Давление: ΔTf(100 м) = -0.0759 °C (≈ -7.53e-4·P)            | OK        |
| 10.5.5  | Чистая вода на 100 м: -0.0759 °C (давление)                 | OK        |
| 10.5.6  | **UNESCO checkvalue: Tf(40, 500 dbar) = -2.588567 °C**      | OK        |
| 10.5.7  | Интерполяция, точный узел (3.7 @ 20 м)                      | OK        |
| 10.5.8  | Интерполяция, середина (4.025 @ 15 м)                       | OK        |
| 10.5.9  | Клэмп выше верхнего уровня (4.35 @ 1 м)                     | OK        |
| 10.5.10 | Клэмп глубже нижнего уровня (-1.5 @ 300 м)                  | OK        |
| 10.5.11 | Интерполяция солёности (0.0345)                             | OK        |
| 10.5.12 | Выборка на черновике H=50/100/150 (линейный профиль)        | OK        |
| 10.5.13 | T < Tf → m_basal = 0                                        | OK        |
| 10.5.14 | T = Tf → m_basal = 0                                        | OK        |
| 10.5.15 | T > Tf → m_basal = C_BASAL·ΔT                               | OK        |
| 10.5.16 | Холодный однородный океан → ⟨ΔT⟩\_D = 0, m_lateral = 0      | OK        |
| 10.5.17 | Реплика Method-A (box-модель) = производство                | OK        |
| 10.5.18 | m_lateral = C_LATERAL·⟨ΔT⟩\_D                               | OK        |
| 10.5.19 | delta_t_ocean = T(D) - Tf(D) консистентно (raw = 1.2069 °C) | OK        |

Итого: **24 проверки, 0 ошибок**, SUCCESS.

### Полный набор

- **49/49 тестовых программ PASS** (exit 0), включая регрессии тестов 2/3/4/6/8/9, drift*scaling*\*, moving_trajectory, ibcao_interp, moving_forcing, era5, en4 и всех surface-тестов 10.1–10.4.
- `-Wall -Wextra` — 0 предупреждений, exit 0.
- `git diff --check` — чисто.

---

## Ограничения / допущения

1. **U_rel по глубине НЕ реализован** (план 10.5 п.4) — перенесён в Stage 10.6; таяние использует |U_ice|
   (скорость относительного потока как скорость льда).
2. **Каноническая океанская модель `thermodynamics.f90` не тронута** — её Zubov `-54·S` остаётся (только айсберговые модули получили EOS-80). Это соответствует AGENTS.md (не трогать Block 200/210/280).
3. Базальное/боковое таяние (коэффициенты C_BASAL/C_LATERAL, трёхравновесная модель) — Stage 10.6/10.7, **вне** 10.5.
4. Горизонтальная билинейная интерполяция не менялась (покрыта регрессиями moving_forcing / ibcao_interp / era5_interp); `bilinear_interp_3d` в коде не существует.
5. `kt1 = min(kt1_i)` по 4 углам: суша любого угла → `kt1=0` → FORCING ERROR (наследие, не менялось).
6. float32: константы БПФ хранятся в real(kind=ik1); checkvalue -2.588567 воспроизводится до точности float32 (7 значащих цифр).

---

## Next

- Stage 10.6 — базальное таяние: U_rel(T) по глубине, трёхравновесная модель, γ_T.
- Stage 10.7 — боковое таяние.
