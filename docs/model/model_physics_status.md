# Статус физических блоков модели (Model Physics Status)

**Дата:** 2026-09-09
**Physics baseline commit:** 136b2e5 "stage10.6: relative ocean flow and ocean-side heat transfer"
**Current repository stage:** Stage 10.6.1 — Ocean Heat Transfer Audit Complete
**FPM версия:** 0.13.0 (local & CI aligned)
**Test targets:** 50
**Tests PASS:** 50 / 50

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

| №   | Блок                           | Текущая формулировка                                        | Статус | Решение                   |
| --- | ------------------------------ | ----------------------------------------------------------- | ------ | ------------------------- |
| 1   | **Геометрия айсберга**         | L, W, H — прямоугольный параллелепипед                      | A      | Оставить                  |
| 2   | **Координаты и позиция**       | x, y (модельные координаты), lat/lon (географические)       | A      | Оставить                  |
| 3   | **Atmospheric forcing (ERA5)** | msl, u10, v10, t2m, d2m, tcc, sf — билинейная интерполяция  | A      | Оставить                  |
| 4   | **Ocean forcing (EN4)**        | T, S — интерполяция до черновика; **Tf = EOS-80 f(S,p)**    | C      | **Stage 10.5 ✅**         |
| 5   | **Ice initialization**         | Реальный лед из AMSR2 + IBCAO батиметрия                    | A      | Оставить                  |
| 6   | **Iceberg dynamics**           | Лагранжева динамика: m·du/dt = ΣF, m·dv/dt = ΣF             | A      | Оставить                  |
| 7   | **Wind drag**                  | Квадратичное сопротивление: τₐ = ρₐ·C_Dₐ·                   | A      | Оставить                  |
| 8   | **Water drag**                 | Метод A (layer-integrated) / Метод B (depth-averaged)       | A      | Оставить                  |
| 9   | **Coriolis**                   | Полунеявная схема (semi-implicit)                           | A      | Оставить                  |
| 10  | **Pressure-gradient force**    | Опционально, через ocean surface slope                      | A      | Оставить                  |
| 11  | **Froude-Krylov**              | Не реализован                                               | D      | Не планируется            |
| 12  | **Basal melt**                 | Q_basal = ρ_w·c_pw·γ_T·(T_w - T_f); γ_T = Nu·k/L_char; Nu = 0.037·Re^0.8·Pr^(1/3) | C      | **Stage 10.6 ✅** |
| 13  | **Lateral melt**               | Q_lateral = ρ_w·c_pw·C_LATERAL·⟨ΔT⟩\_D·A_lat (legacy)                            | B      | Модернизация в Stage 10.7 |
| 14  | **Surface energy (общий)**     | Q_net = Q_SW + Q_LW↓ + Q_LW↑ + Q_SH + Q_LH                  | B      | Модернизация поэтапно     |
| 15  | **Shortwave radiation**        | decl=0, hour_angle=0 (permanent equinox/noon)               | B      | **Stage 10.1**            |
| 16  | **Longwave radiation**         | LW_down = ε_a·σ·T_air⁴·(1+...), LW_up = -ε_i·σ·T_surf⁴      | B      | Модернизация в Stage 10.1 |
| 17  | **Sensible heat**              | Q_SH = ρₐ·C_H·U·(T_air - T_surf)                            | C      | **Stage 10.3 ✅**         |
| 18  | **Latent heat**                | Q_LH = ρₐ·L_S·C_E·U·Δq, ice sat, L_s, m_vapor = ρₐ·C_E·U·Δq | C      | **Stage 10.3 ✅**         |
| 19  | **Surface temperature**        | Prognostic T_surface, C_eff·dT/dt = Q_net_non_melt          | C      | **Stage 10.2 ✅**         |
| 20  | **Phase change (surface)**     | m_melt = Q_melt/(ρ·L_f), m_vapor = ρₐ·C_E·U·(q_air-q_sat)   | C      | **Stage 10.4 ✅**         |
| 21  | **Mass update**                | M = ρ_ice·L·W·H, budget closes 0.013%                       | A      | Оставить                  |
| 22  | **Boundary conditions**        | Land mask=8888.0, grounding logic, domain boundaries        | A      | Оставить                  |
| 23  | **Initial conditions**         | Real geometry + real ice + zero velocity                    | A      | Оставить                  |
| 24  | **Numerical integration**      | Δt=3600s, operator splitting, semi-implicit Coriolis        | A      | Оставить                  |
| 25  | **Interpolation**              | Bilinear (horizontal), linear (vertical)                    | A      | Оставить                  |
| 26  | **Diagnostics**                | NetCDF output, trajectory CSV, mass budget                  | A      | Оставить                  |

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

### 17. Sensible heat — **C (Stage 10.3 ✅)**

**Современная формулировка (Stage 10.3):**

```
Q_SH = ρ_air · CP_AIR · C_H · U · (T_air - T_surf)
ρ_air = p_atm / (R_air · T_air)
CP_AIR = 1004.0 J/(kg·K)
C_H = C_H_NEUTRAL = 1.5e-3  ! Fixed neutral bulk coefficient (model parameter)
Sign: Q_SH > 0 -> atmosphere heats iceberg
```

**Theoretical context (not direct derivation):**

```
Neutral bulk from logarithmic law: C_H = κ² / ln(z/z₀)²
κ = 0.4, z = 10 m, z₀ = 1e-4 m → C ≈ 1.21e-3
Production uses fixed C_H = 1.5e-3 (documented parameter)
```

**Legacy (retained for reference):**

```
SH_COEFF = 1.7068  ! Stanton number (dimensionless), Q_SH = ρ·SH_COEFF·U·ΔT
```

**Решено в Stage 10.3:** Bulk formulation с современным C_H.

---

### 18. Latent heat — **C (Stage 10.3 ✅)**

**Современная формулировка (Stage 10.3):**

```
Q_LH = ρ_air · L_S · C_E · U · (q_air - q_sat_ice)
ρ_air = p_atm / (R_air · T_air)
q_air = 0.622 · e_vap / p_atm  (from ERA5 d2m/t2m)
q_sat_ice = 0.622 · e_sat_ice(T_surf) / p_atm  ! ICE saturation
e_sat_ice = Murphy & Koop (2005), Eq. 10, valid 50–273 K
L_S = 2.835e6 J/kg  ! Latent heat of sublimation at 0°C
C_E = C_E_NEUTRAL = 1.5e-3  ! Fixed neutral bulk coefficient (model parameter)
Sign: Q_LH > 0 -> vapor flux supplies energy (condensation/deposition)
      Q_LH < 0 -> vapor flux removes energy (sublimation)
Stage 10.3: Q_LH is ENERGY FLUX ONLY; no mass change from sublimation/deposition
```

**Theoretical context (not direct derivation):**

```
Neutral bulk from logarithmic law: C_E = κ² / ln(z/z₀)²
κ = 0.4, z = 10 m, z₀ = 1e-4 m → C ≈ 1.21e-3
Production uses fixed C_E = 1.5e-3 (documented parameter)
```

**Legacy (retained for reference):**

```
LH_COEFF = 0.6650735  ! ~443× standard C_E
L_v = 2.5e6 J/kg      ! Vaporization (not sublimation)
q_sat = water_saturation  ! 5–18% error at T < 0°C
```

**Решено в Stage 10.3:** Modern bulk с C_E, ice saturation (Murphy & Koop 2005), L_s.

---

### 19. Surface temperature — **C (Stage 10.2 ✅ / Stage 10.4.1 corrected)**

**Современная формулировка (Stage 10.2 + 10.4.1 corrective):**

```
T_surface — prognostic
C_eff = ρ_ice · c_ice · h_eff = 955500 J/(m²·K)

Q_nonlatent = SW_abs + LW_down + LW_up + SH
Q_LH = m_vapor · L_S
Q_surface = Q_nonlatent + Q_LH

T_surface < T_melt:
    dT/dt = Q_surface / C_eff
    if T_surface_new ≥ T_melt:
        excess_energy = Q_surface - C_eff · (T_melt - T_surface) / Δt
        Q_melt = max(excess_energy, 0)
        T_surface = T_melt
    else:
        Q_melt = 0

T_surface ≥ T_melt:
    T_surface = T_melt
    Q_melt = max(Q_surface, 0)
    m_melt = Q_melt / (ρ_ice · L_f)
```

**Решено в Stage 10.2:** Prognostic T_surface с C_eff·dT/dt = Q_surface.
**Исправлено в Stage 10.4.1:** Q_surface включает Q_LH (не вычитает его).

---

### 20. Phase change (surface) — **C (Stage 10.4 ✅)**

**Современная формулировка (Stage 10.4.1 — CORRECTIVE):**

```
Q_nonlatent = Q_SW + Q_LW + Q_SH            ! Non-latent fluxes (NO LH)
Q_LH = m_vapor · L_S                        ! Latent heat flux
m_vapor = ρ_air · C_E · U · (q_air - q_sat_ice)  [kg/(m²·s)]
Q_surface = Q_nonlatent + Q_LH              ! Total surface energy

Sign convention:
  m_vapor < 0 -> sublimation -> Q_LH < 0 -> ENERGY SINK
  m_vapor > 0 -> deposition  -> Q_LH > 0 -> ENERGY SOURCE

Q_melt = max(Q_surface, 0)  [W/m²]  (at T_surface = T_melt)
m_melt = Q_melt / (ρ_ice · L_f)  [m/s]

Sublimation: m_vapor < 0 (q_air < q_sat_ice) -> mass loss, energy sink
Deposition: m_vapor > 0 (q_air > q_sat_ice) -> mass gain, energy source
Melting: m_melt > 0 (T_surface = 0°C, Q_melt > 0) -> mass loss

Height change: dH/dt = -(m_melt + m_vapor/ρ_ice)
Mass change: ΔM = -(M_melt + M_vapor)

Note: Vapor mass flux and latent heat flux are TWO REPRESENTATIONS
of the SAME phase-change process, NOT two independent energy sources.
Q_LH = m_vapor · L_S  and  ΔM_vapor = m_vapor · A_top · Δt
use identical m_vapor.
```

**Решено в Stage 10.4.1:** Corrective energy partitioning — Q_nonlatent + Q_LH = Q_surface (no double counting). Sublimation is energy sink, deposition is energy source. Melting uses full Q_surface.

**Проверено в Stage 10.4.2 (independent monotonicity validation):** old TEST 10.4.9 was uncontrolled (polar day ⇒ d2m also changed SW_down via precipitable water). Re-validated in **polar night** (SW=0 ⇒ Q_nonlatent = LW_down+LW_up+SH is d2m-invariant analytically). With t2m=283.15 K, tcc=0, msl=101325 Pa, U=10 m/s, T=0 °C and only d2m varied: Q_nonlatent = 149.743 W/m² across all cases; m_vapor = −3.72e−5 / −5.2e−11 / +7.11e−5 kg/m²·s (sub/zero/dep); m_surface = 1.46e−7 / 4.93e−7 / 1.16e−6 m/s — strictly monotonic sub < zero < dep. Zero-latent (d2m=273.158 K tuned so e_sat_dew(Tetens)=e_sat_ice(Murphy-Koop)) gives Q_surface = Q_nonlatent within 1 W/m². Sublimation quench (m→0, T<0) and deposition boost verified; crossing-0°C excess-energy partition matches independent analytic; geometry budget dH/dt = −m_surface + m_vapor/ρ_ice confirmed. Report: `docs/wiki/Stage10.4.2_Independent_monotonicity_validation.md`.

**Stage 10.4.2.1 (independent Q_surface OUTPUT validation):** Stage 10.4.2 reconstructed Q_surface from m_surface; it never verified the production flux. 10.4.2.1 exposes the production Q_surface/Q_LH diagnostically (`diag%q_surface`, `diag%q_lh` in `compute_surface_melt`; physics numerics unchanged — previously `q_surface` was a local, and `q_net` = residual after melt ≈ 0 while melting) and verifies DIRECTLY: `Q_surface_production == Q_nonlatent_independent + m_vapor_production·L_S` for SUB/ZERO/DEP in the same polar-night controlled experiment. Errors ≤ 7.6e−6 W/m² (float32 rounding); production Q_surface strictly monotonic (44.37 < 149.74 < 351.39) and latent identity Q_LH = m_vapor·L_S confirmed (201.645966 W/m² DEP vs independent literals). Q_nonlatent = 149.742706 W/m² identical across cases. Audit now 66 checks / 0 errors; all 49 fpm programs PASS. Report: `docs/wiki/Stage10.4.2.1_Independent_Q_surface_output_validation.md`.

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
| iceberg_test_surface_melt_audit       | Full audit (26 checks)           | PASS   |

**Все 41 тестов PASS.** Infrastructure готова для Stage 10 validation.

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

| Environment | FPM Version | Test Discovery    |
| ----------- | ----------- | ----------------- |
| Local       | 0.13.0      | Auto (41 targets) |
| CI (GitHub) | 0.13.0      | Auto (41 targets) |

**Status:** ✅ Aligned — CI updated to FPM 0.13.0.

---

## Production Physics Changed in Stage 10.4

**YES** — Production physics ИЗМЕНЕНА в Stage 10.4:

- Latent heat: Q_LH = ρ·L_S·C_E·U·Δq with explicit vapor mass flux m_vapor = ρ·C_E·U·Δq
- Phase change partitioning: Q_melt = max(Q_net_non_melt - Q_LH, 0)
- Sublimation/deposition mass flux: m_vapor = ρ_air·C_E·U·(q_air - q_sat_ice)
- Melting: m_melt = Q_melt / (ρ_ice·L_f)
- Height update: dH/dt = -(m_melt + m_vapor/ρ_ice)
- Mass budget includes vapor mass change: ΔM = -(M_melt + M_vapor)

Previous Stage 10.3 changes retained:

- Sensible heat: Q_SH = ρ·CP_AIR·C_H·U·ΔT (CP_AIR=1004, C_H=1.5e-3)
- Latent heat: Q_LH = ρ·L_S·C_E·U·Δq (L_S=2.835e6, C_E=1.5e-3, ice saturation)
- Ice saturation: Murphy & Koop (2005) formulation
- Prognostic T_surface used for all surface fluxes

---

## Stage 10.5 — Ocean Thermal Forcing (Детальный статус)

### 4. Ocean forcing (EN4) — **C (Stage 10.5 ✅)**

Модернизированы пункты 1–3 плана 10.5 (пункт 4 — U_rel — перенесён в Stage 10.6):

1. **Interpolation to draft depth:** `interp_at_draft` — линейная интерполяция c клэмпами, T/S на черновике D.
2. **Submerged surface temperature:** `depth_averaged_thermal_forcing` — ⟨ΔT⟩\_D = (1/D)·∫max(0,T(z)−Tf(z))dz по [0,D] (Method A, legacy), для lateral melt.
3. **Freezing point EOS-80:** каноническая функция `ocean_freezing_point(S, depth)` в `iceberg_types.f90`:
   ```
   Tf = (A0 + A1·√S − A2·S)·S + BP·P     [°C]
   A0 = −0.0575, A1 = 1.710523e-3, A2 = 2.154996e-4, BP = −7.53e-4
   S [PSU] = 1000·S_kg · P [дбар] = ρ_w·g·z/10⁴
   ```
   Источник: Fofonoff & Millard 1983 (UNESCO TPMS 44 §5), Gill 1982 Eq. 3.5.2. Check value −2.588567 °C PASS (10.5.6).
   Применена в 3 точках: `compute_basal_melt` (Tf на D), `depth_averaged_thermal_forcing` (послойно + глубокий слой), `freezing_point(S, 0)`.
4. **Relative velocity (U_rel):** не менялась — глубинная зависимость перенесена в Stage 10.6.

**Диагностика:** `diag%delta_t_ocean = T(D) − Tf(D)` (необрезанная, может быть ≤ 0).

**Тесты:** `iceberg_test_7_vertical_temp_gradient` — audit 10.5.1–10.5.19 (24 проверки) PASS.
**Регрессии (EOS давление):** холодный океан T=−1.9 → −2.5 °C в test*2/3/4/6/8/9, drift_scaling*\*, moving_trajectory, ibcao_interp.

---

## Stage 10.6.1 — Ocean Heat Transfer Audit (Детальный статус)

### 12. Basal melt — **C (Stage 10.6 ✅ / Stage 10.6.1 аудит пройден)**

Реализована bulk-формулировка теплообмена океан-статья по Eckert & Drake (1959) / Weeks & Campbell (1973):

```
U_rel = sqrt((u_water(D) - u_ice)^2 + (v_water(D) - v_ice)^2)
Re = U_rel * L_char / ν
Nu = 0.037 * Re^0.8 * Pr^(1/3)          (турбулентный режим, Re ≥ 5·10⁵)
Nu = 0.664 * Re^0.5 * Pr^(1/3)          (ламинарный режим, Re < 5·10⁵)
γ_T = Nu * k / L_char                    [W/(m²·K)]
Q_basal = γ_T * (T(D) - Tf(D))          [W/m²]
m_basal = Q_basal / (ρ_ice * L_f)       [m/s]
```

Где:
- k = THERMAL_CONDUCTIVITY = 0.56 W/(m·K)
- Pr = PRANDTL_NUMBER = 13.8
- ν = KINEMATIC_VISCOSITY = 1.82e-6 m²/s
- L_char = state%L (длина в направлении X). **ОГРАНИЧЕНИЕ**: модель не имеет прогностической ориентации, state%L всегда вдоль X. Корректно только если U_rel || X.
- Tf = EOS-80 freezing point (Stage 10.5)

**Константы Stage 10.6:**

| Константа | Значение | Единицы | Источник |
|-----------|----------|---------|----------|
| PRANDTL_NUMBER | 13.8 | - | Seawater at 0°C |
| KINEMATIC_VISCOSITY | 1.82e-6 | m²/s | Seawater at 0°C, S=34.8 |
| THERMAL_CONDUCTIVITY | 0.56 | W/(m·K) | Seawater at 0°C |
| REYNOLDS_CRITICAL | 5.0e5 | - | Flat plate transition |
| MELT_RATE_MIN | 1.0e-12 | m/s | Numerical floor |

**Three-equation constants (H&J99, J10) — НЕ ИСПОЛЬЗУЮТСЯ:**
- CD_ICE_OCEAN, STANTON_THERMAL, STANTON_HALINE — сохранены в коде как комментарии для возможного будущего перехода к three-equation.

**Аудит Stage 10.6.1 (iceberg_test_10p6_ocean_heat_transfer — 18 независимых проверок):**
- Константы A.1–A.4: значения соответствуют литературе ✅
- Ламинарный режим B.1–B.2: Nu = 0.664·Re^0.5·Pr^(1/3) ✅
- Турбулентный режим C.1–C.3: Nu = 0.037·Re^0.8·Pr^(1/3) ✅
- Монотоничность по U_rel: m увеличивается с U_rel ✅
- Монотоничность по L_char: m убывает как L^(-0.2) (flat plate) ✅
- Монотоничность по ΔT: m линейно растёт с ΔT ✅
- U_rel = 0 → γ_T = 0, m = 0 (known limitation: нет натурной конвекции) ✅
- Холодный океан (ΔT < 0) → m = 0 ✅
- Размерностная проверка: m ~ 10⁻⁷ m/s для типичных арктических значений ✅
- Независимая валидация flat plate формулы: ratio = 1.000000 ✅
- Консистентность с production compute_basal_melt ✅

**Известные ограничения:**
1. **Характерная длина**: L_char = state%L (X-размер). Модель не имеет ориентации. Физически верно только если U_rel направлен вдоль X.
2. **Режим течения**: Используется flat plate корреляция. Для Re < 5e5 — ламинарная, для Re ≥ 5e5 — турбулентная. Реальные айсберги могут иметь сложную геометрию.
3. **U_rel = 0**: Возвращает m_basal = 0. Натуральная конвекция/проводимость не реализована (Stage 10.7+).
4. **W&C discrepancy**: Flat plate даёт m ~ L^(-0.2) (убывает с L), W&C iceberg параметризация даёт m ~ L^0.2 (растёт с L). Фактор ~5 разница (FitzMaurice & Stern 2018). Bulk-формула применима для L < радиуса деформации (~15 км).
5. **Боковое плавление**: Остаётся legacy (C_LATERAL) до Stage 10.7.

**Тесты:** `iceberg_test_10p6_ocean_heat_transfer` (18 проверок) PASS, `iceberg_test_7_vertical_temp_gradient` (24 проверки Stage 10.5) PASS, `iceberg_test_5_warm_ocean` PASS, `iceberg_test_6_cold_ocean` PASS.

---

### 13. Lateral melt — **B (Stage 10.7)**

Остаётся legacy C_LATERAL. Инфраструктура U_rel(z) готова в ocean_profile%u_rel. Характерная длина для бокового плавления по Weeks & Campbell (1973): L_char = D (черновик).

---

## Stage 10 Readiness (post Stage 10.6.1 completion)

| Requirement              | Status                     |
| ------------------------ | -------------------------- |
| Physics baseline frozen  | ✅ 136b2e5                 |
| Current repo stage       | ✅ Stage 10.6.1 complete   |
| Equation Ledger          | ✅ Complete (Stage 10.6)   |
| Physics Status           | ✅ Complete (this file)    |
| Modernization Plan       | ✅ Complete (Stage 10.6)   |
| CI/FPM aligned           | ✅ 0.13.0 both             |
| Independent tests        | ✅ 50 tests PASS           |
| TEST_11 baseline         | ✅ Documented              |
| Legacy blocks identified | ✅ All B-blocks catalogued |

**Stage 10 readiness:** Stage 10.6 (Basal melting modernization + audit) complete. Ready for Stage 10.7 (Lateral melting modernization).
