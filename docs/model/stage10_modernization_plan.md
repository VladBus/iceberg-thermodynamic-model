# Stage 10 — План физической модернизации модели айсберга

**Дата:** 2026-09-09
**Physics baseline commit:** 136b2e5 "stage10.6: relative ocean flow and ocean-side heat transfer"
**Current repository stage:** Stage 10.6.1 — Ocean Heat Transfer Audit Complete
**Статус:** Stage 10.6 complete with independent scientific audit

---

## Принципы модернизации

1. **Physics-first:** Каждое уравнение должно иметь физическое обоснование
2. **Minimum viable physics:** Не добавлять сложность без необходимости
3. **Traceability:** Каждый коэффициент — с единицей, источником, ограничениями
4. **Validation:** Независимые тесты для каждого блока
5. **No tuning:** Не подгонять параметры под TEST_11
6. **Legacy reference:** Старый TEST_11 сохраняется как исторический baseline

---

## 10.1.1 — SOLAR GEOMETRY (Астрономическая солнечная геометрия) ✅ COMPLETE

### Цель

Заменить legacy approximation:

```
decl = 0.0
hour_angle = 0.0
cos_zenith = cos(latitude)
```

на физически корректную астрономическую солнечную геометрию.

### Legacy блок

- `src/iceberg_thermodynamics.f90`: `compute_surface_melt` → солнечная геометрия
- Константы: `SOLAR_CONSTANT = 1353.0`

### Направление модернизации

1. **Solar declination δ** — формула Спенсера (1971) или NOAA:

   ```
   δ = 0.006918 - 0.399912·cos(Γ) + 0.070257·sin(Γ)
       - 0.006758·cos(2Γ) + 0.000907·sin(2Γ)
       - 0.002697·cos(3Γ) + 0.00148·sin(3Γ)
   где Γ = 2π·(day_of_year - 1)/365
   ```

2. **Hour angle H:**

   ```
   H = 15° · (local_solar_time - 12)
   local_solar_time = UTC + lon/15
   ```

3. **Solar zenith angle:**

   ```
   cos(θ_z) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(H)
   ```

4. **Daylight condition:**

   ```
   if cos(θ_z) <= 0: SW↓ = 0
   ```

5. **Instantaneous/timestep-averaged SW flux** для production forcing:
   - Вычислять cos(θ_z) на каждом timestep с текущими UTC и координатами
   - Polar day / polar night: cos(θ_z) ≤ 0 → SW↓ = 0
   - Daily integration — только для диагностики/валидации (суточный энергетический баланс)

### Необходимые данные

- Текущая дата (day of year) — из main timestep loop
- UTC время — из main timestep loop
- Географическая широта/долгота айсберга — `state%lat`, `state%lon`

### Необходимые тесты

1. Polar night (80°N, Dec 21) → SW = 0
2. Polar day (75°N, Jun 21) → 24h daylight integration
3. Equinox (70°N, Mar 21) → 12h day/night
4. Noon/midnight continuity
5. Daily integrated energy vs legacy
6. Latitude sweep: 70°N, 75°N, 80°N × 4 seasons

### Ограничения

- Не использовать ERA5 radiation fields (SSRD/STRD) пока не будет отдельного решения
- Shortwave расчёт через солнечную константу + атмосферная прозрачность
- `f_atm` (атмосферная прозрачность) — legacy эмпирика, оставить как есть в 10.1.1
- **Atmospheric attenuation / cloud parameterization** — отдельный вопрос (10.1.2), не менять в 10.1.1

---

## 10.1.2 — ATMOSPHERIC ATTENUATION / CLOUD PARAMETERIZATION (Атмосферное ослабление / облачность) ✅ COMPLETE

### Цель

Обеспечить физически обоснованную параметризацию атмосферной прозрачности для коротковолнового излучения.

### Legacy блок

- `src/iceberg_thermodynamics.f90`: `compute_surface_melt` → атмосферная прозрачность
- Константы: `CLOUD_COEFF = 0.6`, `rad_b1`, `rad_b2`, `e_vap` formulation

### Направление модернизации

1. **Atmospheric transmissivity** — заменить эмпирическую формулу на документально обоснованную параметризацию (например, Bird & Riordan 1986, или простая линейная зависимость от tcc с документированным коэффициентом)
2. **Cloud optical depth** — связать tcc с коэффициентом пропускания SW
3. **Water vapor absorption** — физическая зависимость от e_vap, а не эмпирическая

### Ограничения

- Не использовать ERA5 radiation fields (SSRD/STRD) пока не будет отдельного решения
- Краткосрочно: оставить legacy эмпирику с пометкой "legacy", документировать коэффициенты
- Долгосрочно: отдельный этап после валидации солнечной геометрии

---

## 10.2 — PROGNOSTIC SURFACE TEMPERATURE (Прогностическая температура поверхности)

### Цель

Устранить постоянную `T_ICE = -10°C` и ввести прогностическую `T_surface`.

### Legacy блок

- `src/iceberg_types.f90`: `T_ICE = -10.0` (parameter)
- Используется в: `q_sat`, `LW_up`, `SH`, `LH`

### Направление модернизации

**Минимальная физически защищённая модель:**

```
C_eff · dT_surface/dt = Q_net_non_melt
```

где:

- `C_eff = ρ_ice · c_ice · h_eff` — эффективная теплоёмкость поверхностного слоя
- `h_eff` — эффективная толщина активного слоя (параметр, ~0.1–1 m)
- `c_ice = 2100 J/(kg·K)` — удельная теплоёмкость льда
- `Q_net_non_melt = Q_SW + Q_LW + Q_SH + Q_LH` (при T_surface < T_melt)

**Phase change condition:**

```
if T_surface >= T_melt:
    excess_energy = Q_net_non_melt - C_eff·(T_melt - T_surface)/Δt
    m_surface = excess_energy / (ρ_ice · L_f)
    T_surface = T_melt
else:
    T_surface_new = T_surface + Q_net_non_melt · Δt / C_eff
    m_surface = 0
```

### Параметры

| Параметр | Значение | Единицы  | Источник                                  |
| -------- | -------- | -------- | ----------------------------------------- |
| c_ice    | 2100     | J/(kg·K) | Стандартная теплоёмкость льда             |
| h_eff    | 0.5      | m        | Эффективная толщина (tunable, documented) |
| T_melt   | 0.0      | °C       | Точка плавления (approx)                  |

### Необходимые тесты

1. Cold surface (-20°C) → warming under positive Q_net
2. Near-melt surface (-0.5°C) → melt onset
3. Surface at T_melt → melt proportional to excess energy
4. Negative Q_net → cooling
5. Stability at different Δt
6. Conservation: energy in = energy stored + melt energy

### Изменения в state vector

Добавить в `iceberg_state`:

```
real :: T_surface  ! Прогностическая температура поверхности [°C]
```

---

## 10.3 — MODERN TURBULENT HEAT AND MOISTURE EXCHANGE (Турбулентный тепло- и влагообмен) ✅ COMPLETE

### Цель

Заменить legacy коэффициенты:

- `LH_COEFF = 0.6650735`
- `SH_COEFF = 1.7068`

на современную bulk formulation.

### Legacy блок

- `src/iceberg_thermodynamics.f90`: `compute_surface_melt`
- Legacy значения: `SH_COEFF = 1.7068`, `LH_COEFF = 0.6650735`

### Направление модернизации — ВЫПОЛНЕНО

**Sensible heat (Q_SH):**

```
Q_SH = ρ_air · c_p_air · C_H · U · (T_air - T_surface)
```

**Latent heat (Q_LH):**

```
Q_LH = ρ_air · L_s · C_E · U · (q_air - q_surface)
```

**Transfer coefficients (neutral bulk):**

```
C_H = C_E = κ² / [ln(z/z0)]²  (theoretical logarithmic formulation)
```

где:

- κ = 0.4 (функция Кармана)
- z = 10 m (высота измерения ветра)
- z_0 = 1e-4 m (roughness length для гладкого льда, Andreas et al. 2010)
- Theoretical value: C = 0.4² / ln(10/1e-4)² ≈ 1.21e-3

**Actual production coefficients (Stage 10.3):**

```
C_H = C_E = 1.5e-3  (fixed neutral bulk coefficients — model parameters)
```

These are documented model parameters for the neutral bulk formulation. They are NOT the direct result of κ²/ln(z/z₀)² with z₀=1e-4 m (which gives ~1.21e-3). The logarithmic relation is retained only as theoretical context. No stability correction is implemented in Stage 10.3.

**Stability correction:** Не включено в Stage 10.3 (требует Monin-Obukhov length, не доступен без итераций). Оставлено для будущих стадий.

**Surface humidity (КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ):**

```
q_surface = q_sat_ice(T_surface, p_atm)
```

Использовать **насыщение над льдом** (Murphy & Koop 2005).

**Latent heat constant:**

```
L = L_s = 2.835e6 J/kg  (sublimation/deposition at 0°C)
```

Для melting используется отдельно `L_f = 3.34e5 J/kg`.

### Необходимые тесты — ВСЕ ПРОЙДЕНЫ (после corrective validation)

1. ✅ Zero wind (U = 0 -> SH = 0, LH = 0)
2. ✅ Sensible heat sign (T_air > T_surface -> SH > 0; T_air < T_surface -> SH < 0)
3. ✅ Latent heat sign (q_air > q_surface -> LH > 0; q_air < q_surface -> LH < 0)
4. ✅ Ice vs water saturation (q_sat_ice < q_sat_water при T < 0°C, ratio ~0.90)
5. ✅ Wind scaling (analytical SH/LH scale linearly with U; ratio = 2.0)
6. ✅ Transfer-coefficient scaling (algebraic: flux proportional to C_H/C_E)
7. ✅ Analytical validation (independent SH/LH formulas self-consistent)
8. ✅ Surface-temperature coupling (T_surface change affects total q_net)
9. ✅ Cold/dry case (sublimation-like vapor deficit, negative LH)
10. ✅ Humid case (q_air > q_sat, positive LH)
11. ✅ Nighttime regression (SW = 0, all finite)
12. ✅ Full regression (all existing Stage 10.1.1/10.1.2/10.2 tests PASS)
13. ✅ Energy conservation (independent Stage 10.3 formulas, tolerance 10 J/m²)

### Выбранная формулировка

Fixed neutral bulk coefficients C_H = C_E = 1.5e-3 (model parameters for Stage 10.3).

Theoretical logarithmic neutral formulation (context only):

- κ = 0.4 (von Karman constant)
- z = 10 m (ERA5 measurement height)
- z₀ = 1e-4 m (roughness length for smooth ice, Andreas et al. 2010, Arctic sea ice)
- Theoretical C = κ² / ln(z/z₀)² = 0.4² / ln(10/1e-4)² ≈ 1.21e-3

**Источники:**

- Andreas et al. (2010) "Parameterizing turbulent exchange over summer sea ice" — literature context for Arctic sea ice bulk exchange
- Murphy & Koop (2005) "Review of vapour pressures of ice and supercooled water", QJRMS 131, 1539-1565
- Standard bulk aerodynamic formulation (e.g., Garratt 1992, "The Atmospheric Boundary Layer")

**Отвергнутые альтернативы:**

- Stability correction (Monin-Obukhov) — требует итераций и Monin-Obukhov length, недоступен без неявной схемы
- Fixed coefficients from literature without derivation — менее прозрачно
- ERA5 surface fluxes (SSHF/SSHF) — не используются, офлайн параметризация

### Ограничения

- Neutral bulk coefficients only (no stability correction)
- Q_LH — energy flux only, no mass change (Stage 10.3)
- L_s = 2.835e6 J/kg fixed (no T-dependence)
- Ice saturation: Murphy & Koop (2005), range 50–273 K
- C_H/C_E = 1.5e-3 are fixed model parameters, NOT derived from κ²/ln(z/z₀)² with z₀=1e-4 m

## 10.4 — PHASE CHANGE AND SURFACE ABLATION (Фазовые переходы и поверхностная абразия)

### Цель

Разделить процессы:

1. **Melting** (плавление: ice → liquid water)
2. **Sublimation** (сублимация: ice → vapor)
3. **Deposition/Condensation** (осаждение/конденсация: vapor → ice)

### Legacy блок

- `src/iceberg_thermodynamics.f90`: `m_surface = max(Q_net, 0) / (ρ_ice · L_f)`

### Направление модернизации — Stage 10.4 (INCORRECT) → Stage 10.4.1 (CORRECTIVE)

**Stage 10.4 (incorrect — cancelled Q_LH):**

```
Q_available = Q_SW + Q_LW↓ + Q_LW↑ + Q_SH + Q_LH
Q_melt = max(Q_available - Q_LH, 0)  ! WRONG: Q_LH cancelled, wrong sign for sublimation
```

**Stage 10.4.1 (corrective — proper energy partition):**

```
Q_nonlatent = Q_SW + Q_LW↓ + Q_LW↑ + Q_SH       ! Non-latent fluxes (NO LH)
m_vapor = ρ_air · C_E · U · (q_air - q_sat_ice) [kg/(m²·s)]
Q_LH = m_vapor · L_S                            ! Latent heat flux
Q_surface = Q_nonlatent + Q_LH                  ! Total surface energy

Sign convention:
  m_vapor < 0 -> sublimation -> Q_LH < 0 -> ENERGY SINK
  m_vapor > 0 -> deposition  -> Q_LH > 0 -> ENERGY SOURCE

Case 1: T_surface < T_melt
  dT = Q_surface · Δt / C_eff
  T_surface_new = T_surface + dT
  if T_surface_new ≥ T_melt:
      excess_energy = Q_surface - C_eff · (T_melt - T_surface) / Δt
      Q_melt = max(excess_energy, 0)
  else:
      Q_melt = 0

Case 2: T_surface = T_melt
  Q_melt = max(Q_surface, 0)

m_melt = Q_melt / (ρ_ice · L_f)

Vapor mass flux (sublimation/deposition):
m_vapor = ρ_air · C_E · U · (q_air - q_sat_ice)  [kg/(m²·s)]
Sign: m_vapor < 0 -> sublimation (mass loss, energy sink)
      m_vapor > 0 -> deposition (mass gain, energy source)

Mass update:
ΔM = -M_melt - M_vapor
```

### Необходимые тесты — ALL PASS (Stage 10.4.1 corrective validation)

1. ✅ Zero LH baseline
2. ✅ Sublimation: q_air < q_sat_ice, Q_LH < 0, Q_melt LOWER than zero-LH case
3. ✅ Deposition: q_air > q_sat_ice, Q_LH > 0, Q_melt HIGHER than zero-LH case
4. ✅ Latent energy identity: Q_LH = m_vapor · L_S
5. ⚠️ Energy monotonicity: Q_melt_sub < Q_melt_zero < Q_melt_dep — **REPLACED by Stage 10.4.2** (old test was uncontrolled)
6. ✅ Below-freezing surface: negative Q_surface cools T_surface, zero melt
7. ✅ Crossing 0°C: sensible heating + residual phase-change energy partition
8. ✅ At 0°C: positive Q_surface -> melt; negative Q_surface -> cooling; zero -> no change
9. ✅ Mass/energy consistency: vapor mass and latent energy use same m_vapor, L_S
10. ✅ Regression: all existing Stage 10.1.1, 10.1.2, 10.2, 10.3 tests PASS

### Stage 10.4.2 — Independent monotonicity validation (✅ ALL PASS)

**Why re-validated:** old TEST 10.4.9 ran in polar day ⇒ changing `d2m` also changed
`SW_down` (precipitable-water attenuation), so Q_nonlatent was NOT controlled and the
observed `m_base=2.37e-7 > m_dep=6.59e-8` contradicted the claimed ordering.

**Controlled design — polar night (SW ≡ 0):** Q_nonlatent = LW_down + LW_up + SH is
analytically d2m-invariant. Only Q_LH responds to d2m via q_air (Tetens monotonic).
Fixed: t2m=283.15 K, tcc=0, msl=101325 Pa, U=10 m/s, T_surface=0 °C, lat 90.

| Case | d2m [K] | m_vapor [kg/m²s] | Q_LH [W/m²] | Q_surface [W/m²] | m_surface [m/s] |
| ---- | ------- | ---------------- | ----------- | ---------------- | --------------- |
| SUB  | 263.15  | −3.72e−5         | −105.4      | 44.4             | 1.46e−7         |
| ZERO | 273.158 | −5.2e−11         | ≈0          | 149.7            | 4.93e−7         |
| DEP  | 283.15  | +7.11e−5         | +201.6      | 351.4            | 1.16e−6         |

Q_nonlatent identical = 149.743 W/m² across all cases. Strict monotonicity
sub < zero < dep verified for m_vapor, Q_LH, Q_surface, Q_melt, m_surface.
Zero-latent ⇒ Q_surface = Q_nonlatent (within 1 W/m²); sublimation quench
(m→0, T<0); deposition boost; crossing-0°C excess partition vs independent
analytic; geometry mass budget dH/dt = −m_surface + m_vapor/ρ_ice.
Report: `docs/wiki/Stage10.4.2_Independent_monotonicity_validation.md`.

### Stage 10.4.2.1 — Independent Q_surface output validation (✅ ALL PASS)

**Why:** Stage 10.4.2 reconstructed Q_surface from m_surface; it never verified
the PRODUCTION Q_surface calculation. This stage validates the actual product
directly: `diag%q_surface` (NEW diagnostic-only exposure of the local
`q_surface = Q_nonlatent + Q_LH`) vs `Q_nonlatent_independent + m_vapor_production·L_S`.

Production change is diagnostic-only (no numerics change): `diag%q_surface`,
`diag%q_lh` assigned in `compute_surface_melt`; `q_surface`/`q_lh` were local
before, and `diag%q_net_surface` = residual after melt (≈ 0 while melting) is
NOT Q_surface.

| Case | Q_nonlatent_ind [W/m²] | Q_LH = m_vapor·L_S [W/m²] | Q_surface_expected [W/m²] | Q_surface PRODUCTION [W/m²] | error [W/m²] |
| ---- | ---------------------- | ------------------------- | ------------------------- | --------------------------- | ------------ |
| SUB  | 149.742706             | −105.374290               | 44.368416                 | 44.368423                   | +7.6e−6      |
| ZERO | 149.742706             | −1.48e−4                  | 149.742554                | 149.742554                  | 0.0          |
| DEP  | 149.742706             | +201.645966               | 351.388672                | 351.388672                  | 0.0          |

All 7 checks PASS (direct identity 3 cases, Q_nonlatent control, latent identity
Q_LH = m_vapor·L_S, production Q_surface monotonic sub<zero<dep, melt monotonic,
sign conventions, 10.4.2 test-side-bug regression with explicit 283.15/283.15).
Audit: 66 checks / 0 errors. All 49 fpm programs PASS.
Report: `docs/wiki/Stage10.4.2.1_Independent_Q_surface_output_validation.md`.

---

## 10.5 — OCEAN THERMAL FORCING (Океанический тепловый форсинг)

### Цель

Физически интерпретируемое использование EN4 T/S профилей.

### Legacy блок

- `src/iceberg_forcing.f90`: вертикальная интерполяция/экстраполяция
- `src/iceberg_thermodynamics.f90`: `compute_basal_melt`, `compute_lateral_melt`

### Направление модернизации

1. **Interpolation to draft depth:** T/S на глубине D (черновик)
2. **Submerged surface temperature:** T_water на глубинах [0, D] для lateral melt
3. **Freezing point:** T_f = f(S, p) — уравнение состояние морской воды
4. **Relative velocity:** U_rel = |V_water - V_ice| на соответствующих глубинах

### Статус: ✅ ЗАВЕРШЕНО

Реализованы пункты 1–3 плана (пункт 4 — U_rel — перенесён в Stage 10.6):

- **1. Interpolation to draft depth:** существующая `interp_at_draft` (линейная + клэмпы, Stage 9.3) подтверждена тестами 10.5.7–10.5.12.
- **2. Submerged surface T:** действующая Method-A интеграция `depth_averaged_thermal_forcing` подтверждена репликой 10.5.17–10.5.18.
- **3. Freezing point EOS-80:** каноническая `ocean_freezing_point(S, d)` в `iceberg_types.f90` заменяет legacy линейную Tf = −54·S в 3 местах: `compute_basal_melt` (Tf на черновике D), `depth_averaged_thermal_forcing` (послойно + глубокий слой), обёртка `freezing_point(S, 0)`.
  - Формула: Fofonoff & Millard 1983 (UNESCO TPMS 44 §5) / Gill 1982 Eq. 3.5.2. Check value −2.588567 °C PASS (тест 10.5.6).
  - Legacy −54·S давал Tf теплее EOS-80 на ~0.03 °C у поверхности и игнорировал давление (−0.07 °C на осадке 88 м); суммарно ~0.1 °C ≈ 3% типичного ΔT ≈ 3 °C.
  - **Следствие:** во всех регрессиях «холодного океана» T=−1.9 °C оказалась выше Tf ниже ~8 м (EOS давление) → порог уточнён до −2.5 °C (test*2/3/4/6/8/9, drift_scaling*\*, moving_trajectory, ibcao_interp).
- **3.1 Diagnostics:** `delta_t_ocean = T(D) − Tf(D)` (необрезанная) добавлена в `iceberg_diagnostics`, устанавливается в `iceberg_thermodynamics_step`.
- **Тесты:** audit 10.5.1–10.5.19 (24 проверки) в `iceberg_test_7_vertical_temp_gradient` — PASS; полный набор 50/50 PASS; `-Wall -Wextra` — 0 предупреждений, clean exit.
- **Не входит в 10.5:** пункт 4 (U_rel = |V_water − V_ice| на соответствующих глубинах) → Stage 10.6.

---

## 10.6 — BASAL MELTING MODERNIZATION (Модернизация базального таяния)

### Цель

Заменить `C_BASAL = 1e-6` на физически обоснованную параметризацию.

### Направление модернизации — ВЫПОЛНЕНО (Stage 10.6 + 10.6.1)

**Bulk formulation (Eckert & Drake 1959; Weeks & Campbell 1973):**

```
U_rel = sqrt((u_water(D) - u_ice)^2 + (v_water(D) - v_ice)^2)
Re = U_rel * L_char / ν
Nu = 0.037 * Re^0.8 * Pr^(1/3)          (турбулентный режим, Re ≥ 5·10⁵)
Nu = 0.664 * Re^0.5 * Pr^(1/3)          (ламинарный режим, Re < 5·10⁵)
γ_T = Nu * k / L_char                    [W/(m²·K)]
Q_basal = γ_T * (T(D) - Tf(D))          [W/m²]
m_basal = Q_basal / (ρ_ice * L_f)       [m/s]
```

**Stage 10.6.1 — Independent Scientific Audit (ВЫПОЛНЕНО):**
- 18 независимых аналитических проверок PASS (`iceberg_test_10p6_ocean_heat_transfer`)
- Flat plate formula validated: ratio = 1.000000 vs analytical
- Константы задокументированы с источниками
- Известные ограничения задокументированы (L_char = state%L без ориентации, U_rel=0 → m=0, W&C discrepancy ~5x)

### Реализованные константы (в `iceberg_types.f90`):

| Константа               | Значение | Единицы | Источник                         |
| ----------------------- | -------- | ------- | -------------------------------- |
| PRANDTL_NUMBER          | 13.8     | -       | Seawater at 0°C                  |
| KINEMATIC_VISCOSITY     | 1.82e-6  | m²/s    | Seawater at 0°C, S=34.8          |
| THERMAL_CONDUCTIVITY    | 0.56     | W/(m·K) | Seawater at 0°C                  |
| REYNOLDS_CRITICAL       | 5.0e5    | -       | Flat plate transition (Eckert&Drake) |
| MELT_RATE_MIN           | 1.0e-12  | m/s     | Numerical floor                  |

**Three-equation constants (H&J99, J10) — НЕ ИСПОЛЬЗУЮТСЯ, сохранены как комментарии:**
- CD_ICE_OCEAN, STANTON_THERMAL, STANTON_HALINE — для возможного будущего перехода

### Тесты:
- `iceberg_test_10p6_ocean_heat_transfer` — 18 независимых проверок PASS
- `iceberg_test_7_vertical_temp_gradient` — 24 проверки Stage 10.5 PASS
- `iceberg_test_5_warm_ocean` / `iceberg_test_6_cold_ocean` PASS

---

## 10.7 — LATERAL MELTING MODERNIZATION (Модернизация бокового таяния)

### Цель

Физически определить боковое таяние.

### Направление модернизации

```
Q_lateral = ρ_water · c_pw · γ_T · U_rel · ⟨T_water - T_freeze⟩_D · A_lat
```

где:

- `A_lat = 2 · H · (L + W)` — боковая площадь
- `⟨·⟩_D` — усреднение по глубине черновика
- `U_rel` — относительная скорость на глубинах [0, D]

**Geometry update:**

```
ΔL = ΔW = -m_lateral · Δt
```

при сохранении соотношения сторон или пропорционально периметру.

---

## 10.8 — INTEGRATED THERMODYNAMIC COUPLING (Интегрированная термодинамическая связка)

### Цель

Определить точный порядок операций внутри timestep.

### Порядок операций (proposed)

```
1. Interpolate forcing (atmos + ocean) at current position
2. Solar geometry: δ, H, cos(θ_z), daylight check
3. Radiation: Q_SW, Q_LW↓, Q_LW↑(T_surface)
4. Atmospheric turbulent fluxes:
   a. Q_SH(T_surface)
   b. Q_LH(T_surface, q_sat_ice)
5. Update T_surface:
   Q_net_non_melt = Q_SW + Q_LW + Q_SH + Q_LH
   if T_surface < T_melt:
       T_surface_new = T_surface + Q_net_non_melt · Δt / C_eff
       m_surface_melt = 0
   else:
       excess = Q_net_non_melt - C_eff·(T_melt - T_surface)/Δt
       m_surface_melt = max(0, excess) / (ρ_ice · L_f)
       T_surface = T_melt
   Partition Q_LH → sublimation/deposition
6. Basal melt: m_basal(T_water(D), U_rel(D))
7. Lateral melt: m_lateral(⟨T_water⟩_D, U_rel)
8. Geometry update:
   H_new = H - (m_surface_melt + m_basal) · Δt
   L_new = L - m_lateral · Δt
   W_new = W - m_lateral · Δt
   M_new = ρ_ice · L_new · W_new · H_new
9. Draft update: D_new = H_new · ρ_ice / ρ_water
10. Dynamics step (wind, water, Coriolis)
11. Position update
```

### Numerical schemes

- T_surface: semi-implicit или explicit с ограничителем
- Geometry: explicit
- Coriolis: semi-implicit (unchanged)

---

## 10.9 — INTEGRATED PHYSICAL VALIDATION (Комплексная физическая валидация)

### Validation Experiments

| Exp                   | Forcing                  | Expected                 |
| --------------------- | ------------------------ | ------------------------ |
| 1. Zero forcing       | All zero                 | No drift, no melt        |
| 2. Pure SH            | T_air > T_surf, others 0 | Warming → melt at T_melt |
| 3. Pure LH            | Dry air, cold surf       | Sublimation, mass loss   |
| 4. Pure SW            | Daytime, clear sky       | Diurnal cycle, seasonal  |
| 5. Pure LW            | T_air, cloud             | LW balance               |
| 6. T_surface feedback | Vary T_air               | T_surface responds       |
| 7. Sublimation        | RH=0%, cold              | Mass loss without melt   |
| 8. Melting            | T_air > 0, T_surf=0      | Melt rate = Q/(ρL)       |
| 9. Basal melt         | T_water > T_f            | Basal thinning           |
| 10. Lateral melt      | T_water > T_f, U>0       | L/W reduction            |
| 11. Full realistic    | ERA5+EN4+IBCAO           | Regression vs legacy     |

---

## Dependencies Between Stages

```
10.1.1 (Solar geometry) ──────┐
                               ├──→ 10.2 (T_surface needs Q_SW, Q_LW)
10.1.2 (Atmospheric atten.) ──┘       │
10.3 (Turbulent) ─────────────────────┘       │
                                              ├──→ 10.4 (Phase change needs T_surface, Q_SH, Q_LH)
10.5 (Ocean forcing) ────────────────────────┤
                                              ├──→ 10.6 (Basal melt needs ocean T, U_rel)
10.7 (Lateral melt) ←────────────────────────┘
                                              ↓
10.8 (Integrated coupling) ←── all above
                                              ↓
10.9 (Validation) ←──────────── all above
```

---

## Parameter Provenance Requirements

Для КАЖДОГО нового коэффициента в Stage 10:
| Parameter | Required Documentation |
|-----------|----------------------|
| Value | Численное значение |
| Units | SI units |
| Physical meaning | Что представляет |
| Source | Paper, textbook, measurement |
| Applicability range | T, U, stability range |
| Uncertainty | Если известна |

**Запрещено:** "looks reasonable", "similar to legacy", "tuned to match".

---

## Documentation Deliverables per Substage

Каждый подэтап 10.x должен обновить:

1. `docs/model/model_equation_ledger.md` — новые уравнения
2. `docs/model/model_physics_status.md` — статус блока: B → C
3. Production code с русскими комментариями
4. Независимые тесты в `test/`
5. Git commit с сообщением `stage10.x: ...`

---

## CI/FPM Alignment (Prerequisite)

Перед Stage 10.1:

- [ ] CI: FPM 0.13.0 (update `.github/workflows/ci.yml`)
- [ ] Local: FPM 0.13.0 (already)
- [ ] Test discovery: auto (41+ targets)
- [ ] CI run: green

---

## Stage 10 Entry Criteria (Checklist)

- [x] Baseline frozen (cef2a5a)
- [x] Equation Ledger created
- [x] Physics Status created
- [x] Modernization Plan created (this file)
- [ ] CI/FPM aligned
- [x] Independent surface-energy tests PASS
- [x] TEST_11 legacy baseline documented
- [x] All B-blocks catalogued

---

## Success Criteria for Stage 10 Completion

1. ✅ Solar geometry modernized (10.1.1) — astronomical δ, H, cos(θ_z) time-dependent
2. ✅ Atmospheric attenuation modernized (10.1.2) — broadband SW parameterization, documented coefficients
3. ✅ Surface temperature prognostic (10.2)
4. ✅ Turbulent sensible heat documented (10.3)
5. ✅ Turbulent moisture exchange documented (10.3)
6. ✅ Ice saturation vapor pressure used (10.3)
7. ✅ Sublimation/deposition separated from melting (10.4)
8. ✅ Surface melt energy-consistent (10.4)
9. ✅ Basal melt documented (10.6)
10. ⬜ Lateral melt documented (10.7)
11. ✅ Ocean thermal forcing documented (10.5)
12. ⬜ Mass conservation passes (10.8)
13. ⬜ Energy consistency where applicable (10.8)
14. ⬜ Numerical stability passes (10.8)
15. ✅ All equations in Equation Ledger
16. ✅ All constants have units and provenance
17. ✅ Production code has Russian scientific comments
18. ✅ Independent tests exist
19. ✅ TEST_11 legacy reference preserved
20. ✅ Modern TEST_11 result documented
21. ✅ Local and CI FPM reproducible
22. ✅ No arbitrary tuning
23. ✅ No unexplained magic numbers in modernized physics
24. ✅ Stage 10.6.1 independent audit complete (basal melt)

---

_Этот план является roadmap'ом. Реализация начинается ТОЛЬКО после завершения Stage 9.4C.3 commit и CI alignment._
