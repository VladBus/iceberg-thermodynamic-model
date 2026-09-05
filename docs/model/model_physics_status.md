# Статус физических блоков модели (Model Physics Status)

**Дата:** 2026-09-05  
**Commit:** cef2a5a "Stage 9.4C.2 — Surface Energy Balance & Latent Heat Correction"  
**FPM версия:** 0.13.0-alpha  
**Test targets:** 41  
**Tests PASS:** 41 / 41

---

## Классификация статусов

| Код   | Значение                                                          |
| ----- | ----------------------------------------------------------------- |
| **A** | Оставить без изменений — физика подтверждена, работает корректно  |
| **B** | Legacy/приближение — работает, но требует модернизации в Stage 10 |
| **C** | Уже модернизировано — современная физика реализована              |
| **D** | Удалить — блок устарел или ошибочен                               |
| **E** | Новая физика — планируется к внедрению в Stage 10                 |

---

## Таблица статусов физических блоков

| №   | Блок                           | Текущая формулировка                                         | Статус | Решение                   |
| --- | ------------------------------ | ------------------------------------------------------------ | ------ | ------------------------- |
| 1   | **Геометрия айсберга**         | L, W, H — прямоугольный параллелепипед                       | A      | Оставить                  |
| 2   | **Координаты и позиция**       | x, y (модельные координаты), lat/lon (географические)        | A      | Оставить                  |
| 3   | **Atmospheric forcing (ERA5)** | msl, u10, v10, t2m, d2m, tcc, sf — билинейная интерполяция   | A      | Оставить                  |
| 4   | **Ocean forcing (EN4)**        | T, S — вертикальная интерполяция/экстраполяция до черновика  | B      | Модернизация в Stage 10.5 |
| 5   | **Ice initialization**         | Реальный лед из AMSR2 + IBCAO батиметрия                     | A      | Оставить                  |
| 6   | **Iceberg dynamics**           | Лагранжева динамика: m·du/dt = ΣF, m·dv/dt = ΣF              | A      | Оставить                  |
| 7   | **Wind drag**                  | Квадратичное сопротивление: τₐ = ρₐ·C_Dₐ·                    | A      | Оставить                  |
| 8   | **Water drag**                 | Метод A (layer-integrated) / Метод B (depth-averaged)        | A      | Оставить                  |
| 9   | **Coriolis**                   | Полунеявная схема (semi-implicit)                            | A      | Оставить                  |
| 10  | **Pressure-gradient force**    | Опционально, через ocean surface slope                       | A      | Оставить                  |
| 11  | **Froude-Krylov**              | Не реализован                                                | D      | Не планируется            |
| 12  | **Basal melt**                 | Q_basal = ρ_w·c_pw·C_BASAL·U_rel·(T_w - T_f)                 | B      | Модернизация в Stage 10.6 |
| 13  | **Lateral melt**               | Q_lateral = ρ_w·c_pw·C_LATERAL·⟨ΔT⟩\_D·A_lat                 | B      | Модернизация в Stage 10.7 |
| 14  | **Surface energy (общий)**     | Q_net = Q_SW + Q_LW↓ + Q_LW↑ + Q_SH + Q_LH                   | B      | Модернизация поэтапно     |
| 15  | **Shortwave radiation**        | decl=0, hour_angle=0 (permanent equinox/noon)                | B      | **Stage 10.1**            |
| 16  | **Longwave radiation**         | LW_down = ε_a·σ·T_air⁴·(1+...), LW_up = -ε_i·σ·T_surf⁴       | B      | Модернизация в Stage 10.1 |
| 17  | **Sensible heat**              | Q_SH = ρₐ·C_H·U·(T_air - T_surf)                             | B      | **Stage 10.3**            |
| 18  | **Latent heat**                | LH_COEFF=0.6650735, water saturation, L_v, fixed T_ICE       | B      | **Stage 10.3/10.4**       |
| 19  | **Surface temperature**        | T_ICE = -10.0°C (константа, нет прогностики)                 | B      | **Stage 10.2**            |
| 20  | **Phase change (surface)**     | m_surf = max(Q_net,0)/(ρ_ice·L_f) — нет разделения процессов | B      | **Stage 10.4**            |
| 21  | **Mass update**                | M = ρ_ice·L·W·H, budget closes 0.013%                        | A      | Оставить                  |
| 22  | **Boundary conditions**        | Land mask=8888.0, grounding logic, domain boundaries         | A      | Оставить                  |
| 23  | **Initial conditions**         | Real geometry + real ice + zero velocity                     | A      | Оставить                  |
| 24  | **Numerical integration**      | Δt=3600s, operator splitting, semi-implicit Coriolis         | A      | Оставить                  |
| 25  | **Interpolation**              | Bilinear (horizontal), linear (vertical)                     | A      | Оставить                  |
| 26  | **Diagnostics**                | NetCDF output, trajectory CSV, mass budget                   | A      | Оставить                  |

---

## Детальный статус критических surface-energy блоков

### 15. Shortwave radiation — **B (Stage 10.1)**

**Текущая формулировка:**

```
decl = 0.0
hour_angle = 0.0
cos_zenith = cos(latitude)
```

**Проблема:** Постоянное равноденствие/полдень. Зимой даёт ложный свет (polar night), летом недооценивает суточную интеграцию в 5–13 раз при 70–80°N.

**Решение:** Stage 10.1 — астрономическая солнечная геометрия (деклинация, часовой угол, суточная интеграция).

---

### 16. Longwave radiation — **B (Stage 10.1)**

**Текущая формулировка:** Эмпирическая формула HEAT model с cloud factor и humidity correction.

**Проблема:** Legacy эмпирика, не независимо валидирована.

**Решение:** Stage 10.1 — современная параметризация LW_down/LW_up с учётом T_surface.

---

### 17. Sensible heat — **B (Stage 10.3)**

**Текущая формулировка:**

```
Q_SH = rho_air * SH_COEFF * U * (T_air - T_surf)
```

где `SH_COEFF` — legacy коэффициент.

**Проблема:** Коэффициент не имеет современной интерпретации.

**Решение:** Stage 10.3 — bulk formulation с C_H.

---

### 18. Latent heat — **B (Stage 10.3/10.4)**

**Текущая формулировка:**

```
LH_COEFF = 0.6650735           ! legacy, нет цитирования
q_sat = water_saturation(T_surf)  ! water formula at ice surface
L_v = 2.5e6 J/kg                  ! vaporization, не sublimation
T_ICE = -10.0°C (const)           ! нет обратной связи
```

**Факторы экстремальности:**

- LH_COEFF ≈ 443× стандартного C_E (0.0015)
- Fixed T_ICE блокирует condensation heating feedback
- Water saturation переоценивает q_sat на 5–18% при T < 0°C
- L_v вместо L_s даёт -13% к энергии

**Независимый бенчмарк:** Model LH = 327–403× standard bulk formula.

**Решение:** Stage 10.3 — modern bulk с C_E, ice saturation, L_s. Stage 10.4 — разделение sublimation/deposition/melting.

---

### 19. Surface temperature — **B (Stage 10.2)**

**Текущая формулировка:**

```
T_ICE = -10.0°C (parameter.f90, константа)
```

**Роль:** Используется в q_sat, LW_up, SH, LH как температура поверхности.

**Проблема:** Нет прогностики — melt не меняет T_surface. Нет heat capacity.

**Решение:** Stage 10.2 — prognostic T_surface с C_eff·dT/dt = Q_net_non_melt.

---

### 20. Phase change (surface melting) — **B (Stage 10.4)**

**Текущая формулировка:**

```
m_surface = max(Q_net, 0) / (rho_ice * L_f)
```

**Проблема:** Любой положительный Q_net → melt. Нет разделения на:

- Melting (phase change ice→water)
- Sublimation (ice→vapor)
- Deposition (vapor→ice)

**Решение:** Stage 10.4 — energy-consistent partitioning.

---

### 12-13. Basal/Lateral melt — **B (Stage 10.6/10.7)**

**Текущая формулировка:**

- Basal: C_BASAL = 1e-6 m/(s·K), ΔT = T_water - T_f
- Lateral: C_LATERAL = 1e-6 m/(s·K), depth-averaged ΔT

**Проблема:** Коэффициенты compile-time constants, не имеют modern provenance.

**Решение:** Stage 10.6/10.7 — физически обоснованные параметризации.

---

## Независимые тесты (Validation Infrastructure)

| Тест                                  | Тип                              | Статус |
| ------------------------------------- | -------------------------------- | ------ |
| iceberg_test_surface_energy_algebra   | Algebraic identity               | PASS   |
| iceberg_test_surface_latent_reference | Reference benchmark (diagnostic) | PASS   |
| iceberg_test_solar_radiation_geometry | Geometry comparison              | PASS   |
| iceberg_test_surface_energy_balance   | Flux closure                     | PASS   |

**Все 4 новых теста PASS.** Infrastructure готова для Stage 10 validation.

---

## TEST_11 — Legacy Reference

| Параметр         | Значение                   |
| ---------------- | -------------------------- |
| Final position   | 75.176°N, 29.657°E         |
| Final L/W/H      | 93.807 / 93.807 / 28.124 m |
| Mass loss        | 75.3%                      |
| Budget error     | 0.013%                     |
| Max surface melt | 12.2 m/day                 |

**Статус:** Сохранён как **legacy regression/reference experiment**. Совпадение с ним НЕ является критерием физической корректности Stage 10.

---

## FPM/CI Reproducibility

| Environment | FPM Version  | Test Discovery           |
| ----------- | ------------ | ------------------------ |
| Local       | 0.13.0-alpha | Auto (41 targets)        |
| CI (GitHub) | 0.12.0       | Требует explicit listing |

**Action required:** Обновить CI на FPM 0.13.0+ или добавить explicit test list в fpm.toml.

---

## Production Physics Changed in Stage 9.4C.2

**NO** — Production physics НЕ изменена. Добавлены только:

- 4 независимых теста
- Документация (Stage 9.4C.2 report)

---

## Stage 10 Entry Readiness

| Requirement              | Status                     |
| ------------------------ | -------------------------- |
| Baseline frozen          | ✅ cef2a5a                 |
| Equation Ledger          | 🔄 Creating (this stage)   |
| Physics Status           | 🔄 Creating (this file)    |
| Modernization Plan       | 🔄 Creating (this stage)   |
| CI/FPM aligned           | ❌ Pending                 |
| Independent tests        | ✅ 4 new tests PASS        |
| TEST_11 baseline         | ✅ Documented              |
| Legacy blocks identified | ✅ All B-blocks catalogued |

**Stage 10 readiness:** READY после завершения документации и CI alignment.
