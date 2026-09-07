# Model Equation Ledger — Математическая спецификация текущей модели

**Дата:** 2026-09-07  
**Physics baseline commit:** a1fc859 "Correct Stage 10.2 analytical validation"  
**Current repository stage:** Stage 10.3 — corrective validation  
**Model version:** Stage 10.3 corrective validation (production physics from f82c527 + corrective fixes)

---

## 1. ГЕОМЕТРИЯ АЙСБЕРГА

### 1.1 Физический смысл

Айсберг моделируется как прямоугольный параллелепипед с горизонтальными размерами L (длина, x-направление) и W (ширина, y-направление), и вертикальной толщиной H.

### 1.2 Непрерывные уравнения

```
Объём:          V = L · W · H
Масса:          M = ρ_ice · V
Черновик:       D = H · ρ_ice / ρ_water
Нависающая часть: H_sail = H - D
Площадь основания:  A_base = L · W
Площадь боковой поверхности: A_lat = 2 · H · (L + W)
Площадь верхней поверхности: A_top = L · W
```

### 1.3 Дискретные уравнения

Те же, обновляются каждый timestep после расчёта таяния.

### 1.4 Переменные

| Переменная | Значение   | Единицы | Описание               |
| ---------- | ---------- | ------- | ---------------------- |
| L          | prognostic | m       | Длина (x-направление)  |
| W          | prognostic | m       | Ширина (y-направление) |
| H          | prognostic | m       | Толщина                |
| V          | diagnostic | m³      | Объём                  |
| M          | diagnostic | kg      | Масса                  |
| D          | diagnostic | m       | Черновик               |
| H_sail     | diagnostic | m       | Нависающая часть       |

### 1.5 Константы

| Константа | Значение | Единицы | Назначение             |
| --------- | -------- | ------- | ---------------------- |
| RHO_ICE   | 910.0    | kg/m³   | Плотность льда         |
| RHO_WATER | 1028.0   | kg/m³   | Плотность морской воды |

### 1.6 Численная схема

- Explicit update: L^(n+1) = L^n - ΔL_melt, аналогично W, H
- Timestep: Δt = 3600 s (1 час)
- Operator splitting: dynamics → thermodynamics → geometry update

### 1.7 Реализация

```
File: src/iceberg_geometry.f90
Module: iceberg_geometry
Subroutines: iceberg_update_geometry, iceberg_volume, iceberg_mass, iceberg_draft
```

### 1.8 Граничные условия

- L, W, H ≥ 0 (проверка в коде)
- Grounding: если D ≥ bathymetry → grounded = .true., velocity = 0

### 1.9 Начальные условия

- Из файла 1_k.ice (реальная геометрия) или синтетические значения

### 1.10 Проверка

- iceberg_test_1_hydrostatic (hydrostatic equilibrium)
- iceberg_test_10_mass_conservation (mass budget)

### 1.11 Ограничения

- Нет формы айсберга (всегда прямоугольник)
- Нет внутренней структуры температуры

---

## 2. КООРДИНАТЫ И ПОЗИЦИЯ

### 2.1 Физический смысл

Позиция айсберга в модельной сетке (x, y) и географических координатах (lat, lon).

### 2.2 Непрерывные уравнения

```
dx/dt = u
dy/dt = v
```

### 2.3 Дискретные уравнения (Explicit Euler)

```
x^(n+1) = x^n + u^n · Δt
y^(n+1) = y^n + v^n · Δt
```

### 2.4 Переменные

| Переменная | Значение   | Единицы | Описание                         |
| ---------- | ---------- | ------- | -------------------------------- |
| x          | prognostic | m       | Позиция X (модельные координаты) |
| y          | prognostic | m       | Позиция Y (модельные координаты) |
| lat        | diagnostic | deg     | Географическая широта            |
| lon        | diagnostic | deg     | Географическая долгота           |
| u          | prognostic | m/s     | Скорость по X                    |
| v          | prognostic | m/s     | Скорость по Y                    |

### 2.5 Константы

| Константа | Значение  | Единицы | Назначение         |
| --------- | --------- | ------- | ------------------ |
| DX        | 13890.0   | m       | Размер ячейки по X |
| DY        | 13890.0   | m       | Размер ячейки по Y |

### 2.6 Численная схема

- Explicit Euler для позиции
- Timestep: Δt = 3600 s
- Координатное преобразование: model_coords_to_indices (bilinear interpolation weights)

### 2.7 Реализация

```
File: src/iceberg.f90, src/iceberg_forcing.f90
Module: iceberg, iceberg_forcing
Subroutines: iceberg_step, model_coords_to_indices
```

### 2.8 Граничные условия

- Domain boundaries: отражение или остановка на границе
- Land mask: 8888.0 → grounded

### 2.9 Начальные условия

- Задаются при iceberg_init (x, y, lat, lon)

### 2.10 Проверка

- iceberg_test_coord_mapping
- iceberg_test_coord_roundtrip

### 2.11 Ограничения

- Преобразование модельных координат в географические координаты через билинейную интерполяцию географической сетки модели (массивы FI/DL из KOORD.DAT)
- lat/lon не обновляются из x,y в time stepping (known limitation) — используются для диагностики, forcing интерполируется по текущим x,y

---

## 3. ATMOSPHERIC FORCING (ERA5)

### 3.1 Физический смысл

Интерполяция ERA5 реанализа на позицию айсберга.

### 3.2 Переменные forcing

| ERA5 переменная | Внутреннее имя | Единицы (ERA5) | Единицы (модель) | Конверсия |
| --------------- | -------------- | -------------- | ---------------- | --------- |
| msl             | atmos%msl      | Pa             | Pa               | ×1.0      |
| u10             | atmos%u10      | m/s            | cm/s             | ×100      |
| v10             | atmos%v10      | m/s            | cm/s             | ×100      |
| t2m             | atmos%t2m      | K              | °C               | -273.15   |
| d2m             | atmos%d2m      | K              | °C               | -273.15   |
| tcc             | atmos%tcc      | 0–1            | 0–1              | ×1.0      |
| sf              | atmos%snowfall | m/s            | m/s              | ×1.0      |

### 3.3 Интерполяция

- Горизонтальная: билинейная на 4 ближайших узлах ERA5 grid
- Вертикальная: не применяется (поверхностные поля)
- Временная: nearest neighbor (discrete 3-hourly slices)

### 3.4 Реализация

```
File: src/netcdf_input.f90, src/iceberg_forcing.f90
Module: netcdf_input, iceberg_forcing
Subroutines: read_era5_forcing, get_atmos_forcing, bilinear_interp
```

### 3.5 Проверка

- iceberg_test_era5_interp
- iceberg_test_forcing_interp_sensitivity

---

## 4. OCEAN FORCING (EN4)

### 4.1 Физический смысл

Температура и соленость океана, интерполированные на позицию и глубину айсберга.

### 4.2 Переменные forcing

| Переменная  | Единицы (EN4) | Единицы (модель)            | Интерполяция                                      |
| ----------- | ------------- | --------------------------- | ------------------------------------------------- |
| Temperature | °C            | °C                          | Вертикальная (linear) + горизонтальная (bilinear) |
| Salinity    | PSU           | mass fraction (0.033–0.035) | То же                                             |

### 4.3 Вертикальная интерполяция/экстраполяция

- EN4 уровни: до ~45 м (model levels)
- Черновик айсберга: до ~88 м
- Ниже EN4 max depth: экстраполяция последнего значения

### 4.4 Реализация

```
File: src/iceberg_forcing.f90, src/initial_ocean_reader.f90
Module: iceberg_forcing, initial_ocean_reader
Subroutines: get_ocean_profile, ocean_interp_vertical
```

### 4.5 Проверка

- iceberg_test_en4_interp
- iceberg_test_7_vertical_temp_gradient

---

## 5. ICEBERG DYNAMICS (MOMENTUM EQUATIONS)

### 5.1 Физический смысл

Лагранжева динамика айсберга под действием ветра, течения, Кориолиса и градиента давления.

### 5.2 Непрерывные уравнения

```
m · du/dt = F_wind_x + F_water_x + F_coriolis_x + F_pressure_x
m · dv/dt = F_wind_y + F_water_y + F_coriolis_y + F_pressure_y
```

где m = ρ_ice · L · W · H

### 5.3 Дискретные уравнения (Semi-implicit для Coriolis)

**Wind drag (Explicit):**

```
F_wind_x = 0.5 · ρ_air · C_D_a · A_sail · |V_a| · (u_a - u)
F_wind_y = 0.5 · ρ_air · C_D_a · A_sail · |V_a| · (v_a - v)
```

**Water drag — Method A (Layer-integrated, Explicit):**

```
F_water_x = -0.5 · ρ_water · C_D_w · A_wetted · |V_w - V_ice| · (u_w - u)
F_water_y = -0.5 · ρ_water · C_D_w · A_wetted · |V_w - V_ice| · (v_w - v)
```

**Water drag — Method B (Depth-averaged, Explicit):**

```
F_water_x = -0.5 · ρ_water · C_D_w · A_wetted · |Ū_w - V_ice| · (ū_w - u)
F_water_y = -0.5 · ρ_water · C_D_w · A_wetted · |Ū_w - V_ice| · (v̄_w - v)
```

**Coriolis (Semi-implicit):**

```
u^(n+1) = u^n + Δt/m · (F_x^n + f · v^(n+1))
v^(n+1) = v^n + Δt/m · (F_y^n - f · u^(n+1))

Решается аналитически:
u^(n+1) = (u^n + Δt/m·F_x^n + f·Δt/m·(v^n + Δt/m·F_y^n)) / (1 + (f·Δt/m)²)
v^(n+1) = (v^n + Δt/m·F_y^n - f·Δt/m·(u^n + Δt/m·F_x^n)) / (1 + (f·Δt/m)²)
```

**Pressure gradient (Optional):**

```
F_pressure_x = -A_base · ∂p/∂x
F_pressure_y = -A_base · ∂p/∂y
```

### 5.4 Переменные

| Переменная | Значение   | Единицы | Описание                        |
| ---------- | ---------- | ------- | ------------------------------- |
| u, v       | prognostic | m/s     | Скорость айсберга               |
| u_a, v_a   | forcing    | cm/s    | Ветра (переведено в m/s)        |
| u_w, v_w   | forcing    | cm/s    | Течения (переведено в m/s)      |
| f          | diagnostic | 1/s     | Параметр Кориолиса = 2Ωsin(lat) |
| m          | diagnostic | kg      | Масса айсберга                  |

### 5.5 Константы

| Константа | Значение  | Единицы | Назначение                                 |
| --------- | --------- | ------- | ------------------------------------------ |
| C_D_A     | 1.3e-3    | -       | Коэффициент лобового сопротивления воздуха |
| C_D_W     | 2.0e-3    | -       | Коэффициент лобового сопротивления воды    |
| OMEGA     | 7.2921e-5 | 1/s     | Угловая скорость Земли                     |

### 5.6 Численная схема

- Operator splitting: Wind + Water drag (Explicit) → Coriolis (Semi-implicit) → Position update
- Timestep: Δt = 3600 s
- Semi-implicit Coriolis: безусловно устойчива для линейного члена

### 5.7 Реализация

```
File: src/iceberg_dynamics.f90
Module: iceberg_dynamics
Subroutines: iceberg_dynamics_step, solve_coriolis_semi_implicit
```

### 5.8 Граничные условия

- Grounded: u = v = 0
- Domain boundaries: velocity damping

### 5.9 Начальные условия

- u = v = 0 (zero initial velocity)

### 5.10 Проверка

- iceberg_test_3_uniform_current
- iceberg_test_9_coriolis_only
- iceberg_test_coriolis_convergence
- iceberg_test_coriolis_sign
- iceberg_test_discrete_momentum
- iceberg_test_force_budget

### 5.11 Ограничения

- Coriolis period error ~8% при Δt=3600s (numerical damping)
- No Froude-Krylov force
- No added mass effect

---

## 6. BASAL MELT

### 6.1 Физический смысл

Таяние нижней границы айсберга от océanique теплового флюса.

### 6.2 Непрерывное уравнение

```
Q_basal = ρ_water · c_pw · C_BASAL · U_rel · (T_water - T_freeze)
dh/dt = -Q_basal / (ρ_ice · L_f)
```

### 6.3 Дискретное уравнение

```
ΔH_basal = -Q_basal · Δt / (ρ_ice · L_f)
```

### 6.4 Переменные

| Переменная | Значение   | Единицы | Описание                              |
| ---------- | ---------- | ------- | ------------------------------------- |
| T_water    | forcing    | °C      | Температура воды на глубине черновика |
| T_freeze   | diagnostic | °C      | Точка замерзания (зависит от S, p)    |
| U_rel      | diagnostic | m/s     | Относительная скорость вода-лёд       |
| Q_basal    | diagnostic | W/m²    | Тепловой флюс через основание         |

### 6.5 Константы

| Константа   | Значение | Единицы  | Назначение                    |
| ----------- | -------- | -------- | ----------------------------- |
| C_BASAL     | 1.0e-6   | m/(s·K)  | Коэффициент базального таяния |
| CP_WATER    | 3985.0   | J/(kg·K) | Теплоёмкость воды             |
| LATENT_HEAT | 3.34e5   | J/kg     | Латентная теплота плавления   |

### 6.6 Численная схема

- Explicit
- U_rel = |V_water - V_ice| на глубине черновика
- T_water интерполируется вертикально до D

### 6.7 Реализация

```
File: src/iceberg_thermodynamics.f90
Module: iceberg_thermodynamics
Subroutines: compute_basal_melt
```

### 6.8 Проверка

- iceberg_test_5_warm_ocean
- iceberg_test_6_cold_ocean

---

## 7. LATERAL MELT

### 7.1 Физический смысл

Боковое таяние вертикальных граней айсберга.

### 7.2 Непрерывное уравнение

```
Q_lateral = ρ_water · c_pw · C_LATERAL · ⟨ΔT⟩_D · A_lat
d(L+W)/dt = -Q_lateral / (ρ_ice · L_f · H)
```

где ⟨ΔT⟩\_D — глубинно-усредненная разница температур по черновику.

### 7.3 Дискретное уравнение

```
ΔL_lat = ΔW_lat = -Q_lateral · Δt / (ρ_ice · L_f · H · 2)
```

### 7.4 Переменные

| Переменная | Значение   | Единицы | Описание                                |
| ---------- | ---------- | ------- | --------------------------------------- |
| ⟨ΔT⟩\_D    | diagnostic | °C      | Глубинно-усредненное ΔT                 |
| A_lat      | diagnostic | m²      | Площадь боковой поверхности = 2·H·(L+W) |
| Q_lateral  | diagnostic | W/m²    | Тепловой флюс через боковые грани       |

### 7.5 Константы

| Константа | Значение | Единицы | Назначение                  |
| --------- | -------- | ------- | --------------------------- |
| C_LATERAL | 1.0e-6   | m/(s·K) | Коэффициент бокового таяния |

### 7.6 Численная схема

- Explicit
- Глубинное усреднение по уровням EN4 до D
- Симметричное уменьшение L и W

### 7.7 Реализация

```
File: src/iceberg_thermodynamics.f90
Module: iceberg_thermodynamics
Subroutines: compute_lateral_melt
```

### 7.8 Проверка

- iceberg_test_5_warm_ocean

---

## 8. SURFACE ENERGY BALANCE (CURRENT LEGACY FORMULATION)

### 8.1 Физический смысл

Энергетический баланс верхней поверхности айсберга, определяющий поверхностное таяние.

### 8.2 Непрерывные уравнения (Stage 10.1.1 + 10.1.2)

**Shortwave (SW) — Astronomical geometry (Stage 10.1.1) + Atmospheric attenuation (Stage 10.1.2):**

```
SW↓ = S₀ · cos(θ_z) · T_clear · T_cloud
SW_abs = SW↓ · (1 - α_ice)

где:
  S₀ = SOLAR_CONSTANT = 1353 W/m²
  cos(θ_z) = sin(φ)sin(δ) + cos(φ)cos(δ)cos(H)  ! астрономическая геометрия (Stage 10.1.1)
  δ = 0.006918 - 0.399912·cos(Γ) + 0.070257·sin(Γ) - ...  ! Спенсер (1971)
  Γ = 2π·(day_of_year - 1)/365
  H = 15°·(local_solar_time - 12)  ! часовой угол
  local_solar_time = UTC + lon/15 + eq_time/60
  eq_time = 229.18·(0.000075 + 0.001868·cos(Γ) - 0.032077·sin(Γ) - ...)  ! Спенсер (1971)
  Polar night/day: cos(θ_z) ≤ 0 → SW↓ = 0

  ! Atmospheric attenuation (Stage 10.1.2):
  T_clear = T_rayleigh · T_water_vapor · T_aerosol
  T_rayleigh = exp(-τ_rayleigh · m)
  τ_rayleigh = 0.09 · (p_atm / 101325 Pa)  ! sea-level optical depth
  m = 1 / cos(θ_z)  ! air mass (capped at 40)
  T_water_vapor = 1 - 0.077 · w^0.3  ! Lacis & Hansen (1974) broadband
  w [cm] = 0.1 · (e_vap / 100) · (101325 / p_atm)  ! precipitable water from surface e_vap
  T_aerosol = 0.93  ! Arctic background (empirical, legacy)
  T_cloud = 1 - 0.75 · tcc  ! linear cloud transmittance (overcast → 25% of clear)

  All transmittances bounded to [0, 1]. SW↓ ≤ S₀ · max(cos(θ_z), 0).
```

**Legacy SW (replaced in Stage 10.1.2):**
```
SW↓_legacy = S₀ · cos²(θ_z) · (1 - 0.6·tcc³) / ((cos_zenith+2.7)·1e-5·e_vap + 1.085·cos_zenith+0.1)
```

**Longwave (LW):**

```
LW↓ = ε_a · σ · T_air⁴ · (1 + LW_cloud · tcc) · (1 - LW_humid · exp(-LW_humid_exp · (273.15 - T_air)²))
LW↑ = -ε_ice · σ · T_surf⁴
```

**Sensible Heat (SH) — Stage 10.3 Modern Bulk Formulation:**

```
ρ_air = p_atm / (R_air · T_air)
Q_SH = ρ_air · CP_AIR · C_H · |V_a| · (T_air - T_surf)

C_H = C_H_NEUTRAL = 1.5e-3  ! Fixed neutral bulk transfer coefficient (model parameter)
CP_AIR = 1004.0 J/(kg·K)    ! Specific heat of dry air
Sign: Q_SH > 0 -> atmosphere heats surface
```

**Latent Heat (LH) — Stage 10.3 Modern Bulk Formulation:**

```
q_air = 0.622 · e_vap / p_atm
q_sat_ice = 0.622 · e_sat_ice(T_surf) / p_atm  ! ICE saturation (Murphy & Koop 2005)
Q_LH = ρ_air · L_S · C_E · |V_a| · (q_air - q_sat_ice)

C_E = C_E_NEUTRAL = 1.5e-3   ! Fixed neutral bulk transfer coefficient (model parameter)
L_S = 2.835e6 J/kg           ! Latent heat of sublimation at 0°C
e_sat_ice = exp(A - B/T + C·ln(T) - D·T)  ! Murphy & Koop (2005), Eq. 10
    A = 9.550426, B = 5723.265, C = 3.53068, D = 0.00728332
    T in [K], e_sat in [Pa], valid 50-273 K
Sign: Q_LH > 0 -> vapor flux supplies energy to surface (condensation/deposition)
      Q_LH < 0 -> vapor flux removes energy from surface (sublimation)
Stage 10.3: Q_LH is ENERGY FLUX ONLY; no mass change from sublimation/deposition
```

**Theoretical context (not used directly in production):**
```
Neutral bulk transfer coefficient from logarithmic law:
  C_H = C_E = κ² / [ln(z/z₀)]²
  κ = 0.4 (von Karman constant)
  z = 10 m (measurement height)
  z₀ = 1e-4 m (roughness length for smooth ice, Andreas et al. 2010)
  → C = 0.4² / ln(10/1e-4)² ≈ 1.21e-3
```
This theoretical value (≈1.21e-3) differs from the production fixed coefficient (1.5e-3).
The logarithmic relation is retained as theoretical context only.
No stability correction (Monin-Obukhov) is implemented in Stage 10.3.

**Legacy SH/LH (retained for reference):**
```
Q_SH_legacy = ρ_air · SH_COEFF · |V_a| · (T_air - T_surf)
    SH_COEFF = 1.7068  ! Stanton number (dimensionless)
Q_LH_legacy = ρ_air · LH_COEFF · |V_a| · L_v · (q_air - q_sat_water)
    LH_COEFF = 0.6650735  ! ~443x standard C_E
    L_v = 2.5e6 J/kg  ! Vaporization (not sublimation)
    q_sat_water = water saturation at ice surface (5-18% error at T < 0°C)
```

**Net & Melt (Stage 10.4.1 — Corrective Energy Partition):**

```
Q_nonlatent = SW_abs + LW↓ + LW↑ + Q_SH           ! Non-latent energy fluxes
q_air = 0.622 · e_vap / p_atm
q_sat_ice = 0.622 · e_sat_ice(T_surf) / p_atm     ! ICE saturation (Murphy & Koop 2005)
m_vapor = ρ_air · C_E · |V_a| · (q_air - q_sat_ice)  [kg/(m²·s)]  ! vapor mass flux
Q_LH = m_vapor · L_S  [W/m²]                       ! latent heat flux, consistent with Stage 10.3
Q_surface = Q_nonlatent + Q_LH                     ! Total energy available at surface

Sign convention:
  m_vapor < 0 -> sublimation -> Q_LH < 0 -> energy SINK
  m_vapor > 0 -> deposition  -> Q_LH > 0 -> energy SOURCE

Q_melt = max(Q_surface, 0)  [W/m²]  ! energy available for melting at T_surface = 0°C
m_melt = Q_melt / (ρ_ice · L_f)  [m/s]  ! surface melt rate (liquid water)

Q_net = Q_surface - m_melt · ρ_ice · L_f / Δt  [W/m²]  ! residual flux for diagnostics
```

**Phase Change Logic (Corrected Stage 10.4.1):**

```
if T_surface < T_melt:
    dT = Q_surface · Δt / C_eff
    T_surface_new = T_surface + dT
    if T_surface_new ≥ T_melt:
        ! Crossed melting point: partition timestep energy
        excess_energy = Q_surface - C_eff · (T_melt - T_surface) / Δt
        Q_melt = max(excess_energy, 0)
        m_melt = Q_melt / (ρ_ice · L_f)
        T_surface = T_melt
    else:
        m_melt = 0
else:  ! T_surface ≥ T_melt
    T_surface = T_melt
    Q_melt = max(Q_surface, 0)
    m_melt = Q_melt / (ρ_ice · L_f)

Vapor mass flux (sublimation/deposition):
m_vapor = ρ_air · C_E · |V_a| · (q_air - q_sat_ice)  [kg/(m²·s)]
Sign: m_vapor < 0 -> sublimation (mass loss, energy sink)
      m_vapor > 0 -> deposition (mass gain, energy source)
Mass change from vapor: ΔM_vapor = m_vapor · A_top · Δt

Note: Vapor mass flux and latent heat flux are two representations
of the SAME phase-change process, NOT two independent energy sources.
Q_LH = m_vapor · L_S  and  ΔM_vapor = m_vapor · A_top · Δt
use identical m_vapor.
```

### 8.3 Дискретные уравнения

Те же, вычисляются каждый timestep в compute_surface_melt.

### 8.4 Переменные

| Переменная | Значение   | Единицы | Описание                       |
| ---------- | ---------- | ------- | ------------------------------ |
| T_air      | forcing    | °C      | Температура воздуха (t2m)      |
| T_dew      | forcing    | °C      | Точка росы (d2m)               |
| T_surf     | parameter  | °C      | T_ICE = -10.0°C (CONSTANT)     |
| p_atm      | forcing    | Pa      | Давление (msl)                 |
| tcc        | forcing    | 0–1     | Облачность                     |
| V_a        | forcing    | m/s     | Скорость ветра                 |
| Q_net      | diagnostic | W/m²    | Чистый энергетический флюс     |
| m_surface  | diagnostic | m/s     | Скорость поверхностного таяния |

### 8.5 Константы (Legacy)

| Константа       | Значение  | Единицы   | Назначение                              |
| --------------- | --------- | --------- | --------------------------------------- |
| SOLAR_CONSTANT         | 1353.0    | W/m²      | Солнечная константа                              |
| ALBEDO_ICE             | 0.6       | -         | Альбедо льда                                     |
| EMISSIVITY             | 0.97      | -         | Эмиссивность льда                                |
| STEFAN_BOLTZ           | 5.67e-8   | W/(m²·K⁴) | Константа Стефана-Больцмана                      |
| C_CLOUD                | 0.75      | -         | Cloud coefficient (SW, legacy)                   |
| LW_EMISS               | 0.78      | -         | Атмосферная эмиссивность (LW)                    |
| LW_CLOUD_FACTOR        | 0.25      | -         | Cloud factor (LW)                                |
| LW_HUMID_COEFF         | 0.25      | -         | Humidity correction (LW)                         |
| LW_HUMID_EXP           | 0.06      | -         | Humidity exponent (LW)                           |
| SH_COEFF               | 1.5e-3    | -         | Sensible heat transfer coeff                     |
| LH_COEFF               | 0.6650735 | -         | **Legacy latent heat coeff**                     |
| LATENT_VAP             | 2.5e6     | J/kg      | Латентная теплота испарения (L_v)                |
| SAT_VAPOR_0            | 610.78    | Pa        | Насыщенное парциальное давление при 0°C          |
| TETENS_A               | 8.61503   | -         | Коэффициент Тетенса                              |
| GAS_CONST_AIR          | 287.0     | J/(kg·K)  | Газовая постоянная сухого воздуха                |
| EPSILON                | 0.622     | -         | Молекулярное соотношение H₂O/air                 |
| ! Stage 10.1.2: Atmospheric attenuation constants
| TAU_RAYLEIGH_0         | 0.09      | -         | Rayleigh optical depth at sea level (p=1013.25 hPa) |
| AEROSOL_TRANS_ARCTIC   | 0.93      | -         | Arctic background aerosol transmittance (empirical) |
| CLOUD_TRANS_COEFF      | 0.75      | -         | Cloud transmittance coefficient (T_cloud = 1 - C*tcc) |
| WV_ABSORP_COEFF        | 0.077     | -         | Water vapor absorption coefficient (Lacis & Hansen 1974) |
| WV_ABSORP_EXP          | 0.3       | -         | Water vapor absorption exponent (Lacis & Hansen 1974) |
| PRECIP_WATER_SCALE     | 0.1       | cm/(hPa)  | Precipitable water scale from surface e_vap (empirical) |
| ! Stage 10.3: Modern turbulent exchange
| CP_AIR                 | 1004.0    | J/(kg·K)  | Specific heat of dry air                          |
| L_S                    | 2.835e6   | J/kg      | Latent heat of sublimation at 0°C                 |
| C_H_NEUTRAL            | 1.5e-3    | -         | Fixed neutral bulk coefficient (model parameter; literature-context documented) |
| C_E_NEUTRAL            | 1.5e-3    | -         | Fixed neutral bulk coefficient; same formulation  |
| VON_KARMAN             | 0.4       | -         | Von Karman constant                               |
| Z0_ICE                 | 1.0e-4    | m         | Roughness length for smooth ice (Andreas et al. 2010) |
| MURPHY_KOOP_A          | 9.550426  | -         | Murphy & Koop (2005) ice saturation A             |
| MURPHY_KOOP_B          | 5723.265  | K         | Murphy & Koop (2005) ice saturation B             |
| MURPHY_KOOP_C          | 3.53068   | -         | Murphy & Koop (2005) ice saturation C             |
| MURPHY_KOOP_D          | 0.00728332| 1/K       | Murphy & Koop (2005) ice saturation D             |

### 8.6 Численная схема

- Explicit evaluation каждый timestep
- T_surf = state%T_surface (prognostic, Stage 10.2)
- Solar geometry: астрономическая (Stage 10.1.1) — declination δ, hour angle H, cos(θ_z) каждый timestep
- Polar night/day: cos(θ_z) ≤ 0 → SW↓ = 0
- max(0, Q_net) предотвращает отрицательное таяние
- SW atmospheric attenuation: T_clear = T_rayleigh·T_water_vapor·T_aerosol; T_cloud = 1 - 0.75·tcc (Stage 10.1.2)
- SH/LH: Modern bulk formulation with ice saturation (Stage 10.3)
- L_S = 2.835e6 J/kg used for vapor exchange energy flux (no mass change in Stage 10.3)

### 8.7 Реализация

```
File: src/iceberg_thermodynamics.f90
Module: iceberg_thermodynamics
Subroutines: compute_surface_melt, saturation_vapor_pressure, ...
```

### 8.8 Граничные условия

- Polar night: legacy даёт cos_zenith > 0 (FALSE DAYLIGHT)
- No melt if Q_net ≤ 0

### 8.9 Начальные условия

- Не требуются (diagnostic каждый шаг)

### 8.10 Проверка

- iceberg_test_surface_energy_algebra (algebraic identity)
- iceberg_test_surface_latent_reference (benchmark vs bulk)
- iceberg_test_solar_radiation_geometry (legacy vs astronomy)
- iceberg_test_surface_energy_balance (flux closure)
- iceberg_test_surface_melt_audit (self-referential)

### 8.11 Ограничения (КРИТИЧЕСКИЕ — Stage 10 targets)

1. **Solar geometry:** FIXED in Stage 10.1.1 — astronomical δ, H, cos(θ_z) now time-dependent
2. **Atmospheric attenuation (SW):** PARTIALLY FIXED in Stage 10.1.2 — broadband parameterization with documented coefficients; CLOUD_TRANS_COEFF=0.75, AEROSOL_TRANS_ARCTIC=0.93 (empirical legacy), PRECIP_WATER_SCALE=0.1 (empirical). NOT using ERA5 SSRD/STRD.
3. **SH/LH coefficients:** C_H = C_E = 1.5e-3 fixed neutral bulk coefficients (model parameters). NOT derived from kappa²/ln²(z/z₀) with z₀=1e-4 m (which gives ~1.21e-3). Theoretical logarithmic relation retained as context only.
4. **Stability correction:** NOT implemented (no Monin-Obukhov length, requires implicit scheme).
5. **T_ICE:** Fixed -10°C → нет condensation heating feedback (replaced by prognostic T_surface in Stage 10.2)
6. **q_sat:** FIXED in Stage 10.3 — now uses ice saturation (Murphy & Koop 2005).
7. **L_v vs L_s:** FIXED in Stage 10.3 — now uses L_s = 2.835e6 J/kg for sublimation/deposition energy flux.
8. **No phase partitioning:** Stage 10.3 — Q_LH is energy flux only; no mass change from sublimation/deposition (Stage 10.4).

---

## 9. SURFACE MELT → GEOMETRY UPDATE (Stage 10.4 updated)

### 9.1 Непрерывное уравнение

```
dH/dt = -(m_melt + m_vapor/ρ_ice)
```

where m_vapor = ρ_air · C_E · |V_a| · (q_air - q_sat_ice) [kg/(m²·s)]
Q_LH = m_vapor · L_S
Sign convention:
  m_vapor < 0 -> sublimation (mass loss, thickness decreases, Q_LH < 0 energy sink)
  m_vapor > 0 -> deposition (mass gain, thickness increases, Q_LH > 0 energy source)

Q_surface = Q_nonlatent + Q_LH  ! total surface energy
Q_melt = max(Q_surface, 0)  at T_surface = T_melt
m_melt = Q_melt / (ρ_ice · L_f)

### 9.2 Дискретное уравнение

```
H^(n+1) = H^n - (m_melt + m_vapor/ρ_ice) · Δt
```

### 9.3 Массовый баланс

```
M_budget = M_geometry = ρ_ice · L · W · H
Mass_loss = M_basal + M_lateral + M_surface + M_vapor
Error = |M_geometry - M_budget| / M_initial < 0.013%
```

### 9.4 Реализация

```
File: src/iceberg_geometry.f90
Subroutines: iceberg_update_geometry
```

### 9.5 Проверка

- iceberg_test_10_mass_conservation
- iceberg_test_11_30day_offline

---

## 10. MASS CONSERVATION (Stage 10.4 updated)

### 10.1 Уравнение

```
M^(n+1) = M^n - (M_basal + M_lateral + M_surface + M_vapor) · Δt
```

where M_vapor = m_vapor · A_top · Δt
m_vapor = ρ_air · C_E · |V_a| · (q_air - q_sat_ice) [kg/(m²·s)]

### 10.2 Диагностика

```
M_geometry = ρ_ice · L · W · H
M_budget = M_initial - Σ(M_melt_components) - M_vapor
Relative_error = |M_geometry - M_budget| / M_initial
```

---

## 11. ЧИСЛЕННЫЕ МЕТОДЫ (SUMMARY)

### 11.1 State Variables & Update Order

```
State vector: [x, y, u, v, L, W, H] (7 prognostic)

Timestep loop (Δt = 3600 s):
1. Forcing interpolation (atmos + ocean) at current position
2. Dynamics:
   a. Wind drag (Explicit)
   b. Water drag (Explicit, Method A or B)
   c. Coriolis (Semi-implicit analytical solve)
   d. Pressure gradient (Optional, Explicit)
   e. Update u, v
3. Position update (Explicit Euler): x, y
4. Thermodynamics:
   a. Basal melt (Explicit)
   b. Lateral melt (Explicit)
   c. Surface energy balance (Explicit):
      i. Compute Q_SW, Q_LW, Q_SH, Q_LH
      ii. Compute Q_nonlatent = SW_abs + LW_down + LW_up + SH
      iii. Compute m_vapor = ρ_air · C_E · |V_a| · (q_air - q_sat_ice)
      iv. Compute Q_LH = m_vapor · L_S
      v. Compute Q_surface = Q_nonlatent + Q_LH
      vi. Prognostic T_surface update:
          if T_surface < T_melt:
              dT = Q_surface · Δt / C_eff
              T_surface_new = T_surface + dT
              if T_surface_new ≥ T_melt:
                  excess_energy = Q_surface - C_eff · (T_melt - T_surface) / Δt
                  Q_melt = max(excess_energy, 0)
              else:
                  Q_melt = 0
          else:
              Q_melt = max(Q_surface, 0)
      vii. Compute m_melt = Q_melt / (ρ_ice · L_f)
      viii. m_surface = m_melt
   d. Update H (from m_surface + m_vapor/ρ_ice)
   e. Update L, W (from lateral melt)
   f. Update geometry (mass, draft, areas)
5. Diagnostics output
```

### 11.2 Interpolation Schemes

- Horizontal (ERA5/EN4): Bilinear
- Vertical (EN4): Linear + extrapolation
- Time (ERA5): Nearest neighbor (3-hourly)

### 11.3 Timestep

- Δt = 3600 s (1 hour) — production
- Тестирована стабильность: 60–3600 s

---

## 12. BOUNDARY CONDITIONS

| Boundary               | Treatment                                             |
| ---------------------- | ----------------------------------------------------- |
| Domain edges           | Land mask (8888.0) → grounded, velocity = 0           |
| Iceberg grounding      | D ≥ bathymetry → grounded = .true., u=v=0             |
| Forcing outside domain | Nearest valid value / zero gradient                   |
| Velocity               | No-slip at land, free-slip at open boundary           |
| Thermodynamic          | No flux through land, ocean forcing only at wet cells |

---

## 13. INITIAL CONDITIONS

| Component                      | Source                                      |
| ------------------------------ | ------------------------------------------- |
| Iceberg geometry (L,W,H)       | 1_k.ice (real) / synthetic (test)           |
| Iceberg position (x,y,lat,lon) | 1_k.ice / specified                         |
| Iceberg velocity (u,v)         | 0, 0                                        |
| SIC/SIT                        | AMSR2 + IBCAO (real) / synthetic (test)     |
| Ocean T/S                      | EN4 Jan 2020 (real) / zero gradient (test)  |
| Atmosphere                     | ERA5 Jan-Mar 2020 (real) / synthetic (test) |

---

## 14. CODE LOCATIONS (QUICK REFERENCE)

| Physics Block     | Primary File               | Module                 |
| ----------------- | -------------------------- | ---------------------- |
| Geometry          | iceberg_geometry.f90       | iceberg_geometry       |
| Dynamics          | iceberg_dynamics.f90       | iceberg_dynamics       |
| Thermodynamics    | iceberg_thermodynamics.f90 | iceberg_thermodynamics |
| Forcing           | iceberg_forcing.f90        | iceberg_forcing        |
| ERA5 Input        | netcdf_input.f90           | netcdf_input           |
| EN4 Input         | initial_ocean_reader.f90   | initial_ocean_reader   |
| Main Orchestrator | app/main.f90               | (program)              |
| Types/Constants   | iceberg_types.f90          | iceberg_types          |

---

## 15. КЛЮЧЕВЫЕ LEGACY APPROXIMATIONS (FOR STAGE 10 REFERENCE)

| Block              | Legacy Formula   | Modern Target                          |
| ------------------ | ---------------- | -------------------------------------- |
| Solar geometry     | decl=0, hour=0   | Astronomical δ, H; daily integration for diagnostics |
| LH coefficient     | 0.6650735        | C_E (neutral/stability-dependent)      |
| Surface temp       | Fixed -10°C      | Prognostic T_surface                   |
| q_sat              | Water saturation | Ice saturation (Murphy-Koop)           |
| Latent heat        | L_v = 2.5e6      | L_s = 2.835e6 for sublimation          |
| Phase change       | max(Q_net,0)     | Partition: melt/sublimation/deposition |
| Basal melt coeff   | 1e-6 m/(s·K)     | Physics-based γ_T                      |
| Lateral melt coeff | 1e-6 m/(s·K)     | Physics-based γ_T                      |

---

_Этот документ является математической спецификацией текущей (Stage 9.4C.2) production модели. Все уравнения отражают фактический код, а не желаемую физику._
