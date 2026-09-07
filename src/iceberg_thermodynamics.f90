! ==============================================================================
! Модуль: iceberg_thermodynamics
! Назначение: Термодинамика айсберга — базальное, боковое и поверхностное плавление.
! Физика: Stage 9.1 §10-15.
!   Базальное (дно):     m_b = C_BASAL * max(0, T(D) - Tf(D))                [м/с]
!   Боковое (стороны):   m_l = C_LATERAL * ⟨max(0, T - Tf)⟩_D                 [м/с]
!                         где ⟨...⟩_D = (1/D) ∫₀ᴰ max(0, T(z) - Tf(z)) dz
!   Поверхностное (верх): m_s = max(0, Q_net) / (ρ_ice * L_f)                [м/с]
!   Q_net = SW↓(1-α) + LW↓ - LW↑ + SH + LH  (адаптировано из legacy HEAT)
!   Tf = -54.0 * S  [°C], где S — массовая доля [кг/кг] (S=0.035 → Tf=-1.89°C)
!
! Исправления Stage 9.3:
!   - C_BASAL, C_LATERAL: были 1e-4 [м/с] с делением на (ρᵢ·L_f),
!     стало 1e-6 [м/(с·К)] с формулой m = C * ΔT (без деления).
!   - Физический смысл: γ_T = h/(ρᵢ·L_f), h ≈ 300 Вт/(м²·К) → γ_T ≈ 1e-6.
!
! Единицы: SI (м, с, кг, К/°C, Вт/м²).
! Точность: default real (float32).
! ==============================================================================

module iceberg_thermodynamics
    use iceberg_types
    use iceberg_forcing, only: interp_at_draft, depth_averaged_thermal_forcing
    use param, only: nat
    implicit none

    ! ========================================================================
    !   КОНСТАНТЫ ДЛЯ ПОВЕРХНОСТНОГО ТЕПЛОВОГО БАЛАНСА (адаптированы из legacy HEAT)
    ! ========================================================================
    real, parameter :: SOLAR_CONSTANT = 1353.0     ! Солнечная постоянная [Вт/м²]
    real, parameter :: CLOUD_COEFF = 0.6        ! Коэффициент затухания от облаков (legacy)
    real, parameter :: LW_EMISS = 5.4999e-8  ! Эффективная эмиссивность атмосферы [Вт/(м²·К⁴)]
    real, parameter :: LW_CLOUD_FACTOR = 0.275      ! Фактор облачности для LW
    real, parameter :: LW_HUMID_COEFF = 0.261      ! Коэффициент влажности для LW
    real, parameter :: LW_HUMID_EXP = 7.77e-4    ! Показатель влажности для LW

    ! Legacy SH/LH coefficients (HEAT model) — retained for reference/compatibility
    ! SH_COEFF = 1.7068  (behaves like Stanton number, dimensionless)
    ! LH_COEFF = 0.6650735  (~443x standard bulk C_E ≈ 0.0015)
    ! LATENT_VAP = 2.5e6  (vaporization; used for ice-vapor exchange in legacy)
    ! SAT_VAPOR_0 = 610.78, TETENS_A = 8.61503  (Tetens water saturation)
    ! T_ICE = -10.0°C (fixed surface temp, no feedback)
    ! Water saturation formula at ice surface -> 5-18% q_sat error at T < 0°C
    ! L_v instead of L_s -> -13% energy error for sublimation/deposition
    ! Net legacy LH = 327-403x standard bulk formula

    ! Modern bulk coefficients (Stage 10.3) — used in compute_surface_melt
    ! Theoretical neutral bulk: C_H = C_E = kappa^2 / ln(z/z0)^2
    !   kappa = 0.4, z = 10 m, z0 = 1e-4 m -> theoretical C ≈ 1.21e-3
    ! Production uses fixed neutral bulk coefficients:
    !   C_H = C_E = 1.5e-3  (documented model parameter)
    !   NOT derived from kappa^2/ln(z/z0)^2 with z0=1e-4 m
    ! CP_AIR = 1004.0 J/(kg·K), L_S = 2.835e6 J/kg (sublimation at 0°C)
    ! Ice saturation: Murphy & Koop (2005) formulation
    ! Sign convention: Q_SH > 0 = atmosphere heats iceberg
    !                 Q_LH > 0 = vapor flux supplies energy to surface
    ! Stage 10.3: Q_LH is ENERGY FLUX ONLY; no mass change from sublimation/deposition

    real, parameter :: SH_COEFF = 1.7068     ! Legacy: Stanton number (dimensionless)
    real, parameter :: LH_COEFF = 0.6650735  ! Legacy: Dalton number (dimensionless)
    real, parameter :: LATENT_VAP = 2.5e6      ! Legacy: latent heat of vaporization [Дж/кг]
    real, parameter :: GAS_CONST_AIR = 287.0      ! Газовая постоянная сухого воздуха [Дж/(кг·К)]
    real, parameter :: SAT_VAPOR_0 = 610.78     ! Насыщенное парциальное давление при 0°C [Па]
    real, parameter :: TETENS_A = 8.61503    ! Константа Тетенса для e_sat
    real, parameter :: WATER_ALBEDO = 0.06       ! Альбедо воды
    real, parameter :: WATER_EMISS = 0.97       ! Эмиссивность воды

    ! ========================================================================
    !   АТМОСФЕРНАЯ ПРОПУСКАЮЩАЯ СПОСОБНОСТЬ КОРОТКОВОЛНОВОЙ РАДИАЦИИ (Stage 10.1.2)
    ! ========================================================================
    ! Broadband parameterization using ERA5 inputs (tcc, t2m, d2m, msl).
    ! Based on simple physical approximations (Rayleigh, water vapor, aerosol).
    ! Cloud transmittance: linear in tcc.
    ! NOT using ERA5 SSRD/STRD — offline parameterization only.
    ! Coefficients documented below; legacy empirical values marked.
    ! ========================================================================
    real, parameter :: TAU_RAYLEIGH_0 = 0.09        ! Оптическая толщина Релея на уровне моря (p=1013.25 hPa)
    real, parameter :: AEROSOL_TRANS_ARCTIC = 0.93  ! Атмосферная прозрачность от аэрозолей (Arctic background, legacy empirical)
    real, parameter :: CLOUD_TRANS_COEFF = 0.75     ! Коэффициент облачной пропускания: T_cloud = 1 - C*tcc (overcast ~25% of clear)
    real, parameter :: WV_ABSORP_COEFF = 0.077      ! Коэффициент поглощения водяным паром (Lacis & Hansen 1974 approx)
    real, parameter :: WV_ABSORP_EXP = 0.3          ! Показатель для водяного пара (Lacis & Hansen 1974)
    real, parameter :: PRECIP_WATER_SCALE = 0.1     ! Масштаб для оценки выпадаемой воды из e_vap [cm/(hPa)] (empirical)

    ! ========================================================================
    !   АСТРОНОМИЧЕСКИЕ КОНСТАНТЫ (Stage 10.1.1)
    ! ========================================================================
    real, parameter :: DEG2RAD = 0.017453292519943295  ! π/180
    real, parameter :: RAD2DEG = 57.29577951308232     ! 180/π
    real, parameter :: SECONDS_PER_DAY = 86400.0
    real, parameter :: HOURS_PER_DAY = 24.0
    real, parameter :: DEG_PER_HOUR = 15.0             ! 360°/24h

contains

    ! ========================================================================
    !   СОЛНЕЧНАЯ ГЕОМЕТРИЯ (Stage 10.1.1)
    ! ========================================================================
    ! Вычисляет солнечную геометрию для заданного времени и позиции.
    ! Использует формулу Спенсера (1971) для склонения Солнца.
    !
    ! Аргументы:
    !   year, month, day, hour  - референс-дата (UTC) начала моделирования
    !   model_time_sec          - модельное время [с] от референс-даты
    !   latitude_deg, longitude_deg - географическая позиция [°]
    !   cos_zenith              - cos(солнечный зенитный угол) (выход)
    !   declination_rad         - солнечное склонение [рад] (выход, optional)
    !   hour_angle_rad          - часовой угол [рад] (выход, optional)
    ! ========================================================================
    subroutine solar_geometry(year, month, day, hour, &
                              model_time_sec, &
                              latitude_deg, longitude_deg, &
                              cos_zenith, &
                              declination_rad, hour_angle_rad)
        integer, intent(in) :: year, month, day, hour
        real, intent(in) :: model_time_sec
        real, intent(in) :: latitude_deg, longitude_deg
        real, intent(out) :: cos_zenith
        real, intent(out), optional :: declination_rad, hour_angle_rad

        real :: current_time_sec
        integer :: day_of_year
        real :: gamma, decl_rad, eq_time_min
        real :: utc_hour, local_solar_time, hour_angle_deg, hour_angle_rad_local
        real :: lat_rad
        integer :: days_in_month(12)
        integer :: m_local, d_local
        real :: total_days

        ! Дни в месяцах (невисокосный год, корректировка для високосных ниже)
        days_in_month = (/31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31/)

        ! Текущее абсолютное время в секундах от начала референс-дня
        current_time_sec = real(hour)*3600.0 + model_time_sec

        ! Вычисление дня года (1-365/366)
        ! Учитываем полные дни, прошедшие от референс-даты
        total_days = current_time_sec/SECONDS_PER_DAY
        day_of_year = day + int(total_days)

        ! Корректировка для високосного года
        if (mod(year, 4) .eq. 0 .and. (mod(year, 100) .ne. 0 .or. mod(year, 400) .eq. 0)) then
            days_in_month(2) = 29
        end if

        ! Нормализация day_of_year в диапазон 1..365(366)
        do while (day_of_year .gt. 365 + (days_in_month(2) - 28))
            day_of_year = day_of_year - 365 - (days_in_month(2) - 28)
        end do
        do while (day_of_year .lt. 1)
            day_of_year = day_of_year + 365 + (days_in_month(2) - 28)
        end do

        ! Угол Γ = 2π * (day_of_year - 1) / 365
        gamma = 2.0*3.141592653589793*real(day_of_year - 1)/365.0

        ! Склонение Солнца по Спенсеру (1971) [рад]
        decl_rad = 0.006918 - 0.399912*cos(gamma) + 0.070257*sin(gamma) &
                   - 0.006758*cos(2.0*gamma) + 0.000907*sin(2.0*gamma) &
                   - 0.002697*cos(3.0*gamma) + 0.00148*sin(3.0*gamma)

        ! Уравнение времени (минуты) - приближение Спенсера
        eq_time_min = 229.18*(0.000075 + 0.001868*cos(gamma) - 0.032077*sin(gamma) &
                              - 0.014615*cos(2.0*gamma) - 0.040849*sin(2.0*gamma))

        ! UTC час с дробной частью
        utc_hour = real(hour) + mod(current_time_sec, SECONDS_PER_DAY)/3600.0

        ! Местное солнечное время = UTC + longitude/15 + eq_time/60
        ! longitude > 0 на востоке
        local_solar_time = utc_hour + longitude_deg/DEG_PER_HOUR + eq_time_min/60.0

        ! Часовой угол H = 15° * (local_solar_time - 12) [градусы]
        hour_angle_deg = DEG_PER_HOUR*(local_solar_time - 12.0)

        ! Нормализация часового угла в [-180, 180]
        do while (hour_angle_deg .gt. 180.0)
            hour_angle_deg = hour_angle_deg - 360.0
        end do
        do while (hour_angle_deg .lt. -180.0)
            hour_angle_deg = hour_angle_deg + 360.0
        end do

        hour_angle_rad_local = hour_angle_deg*DEG2RAD
        lat_rad = latitude_deg*DEG2RAD

        ! cos(zenith) = sin(φ)sin(δ) + cos(φ)cos(δ)cos(H)
      cos_zenith = sin(lat_rad)*sin(decl_rad) + cos(lat_rad)*cos(decl_rad)*cos(hour_angle_rad_local)

        ! Clamp к [-1, 1] для числовой стабильности
        cos_zenith = max(-1.0, min(1.0, cos_zenith))

        ! Опциональные выходы
        if (present(declination_rad)) declination_rad = decl_rad
        if (present(hour_angle_rad)) hour_angle_rad = hour_angle_rad_local
    end subroutine solar_geometry

    ! ========================================================================
    !   ГЛАВНАЯ ПОДПРОГРАММА ТЕРМОДИНАМИКИ
    ! ========================================================================
    ! Вызывает три компонента плавления и сохраняет результаты в diag.
    !
    ! Аргументы:
    !   state       - состояние айсберга (intent(inout), T_surface обновляется)
    !   dt          - шаг по времени [с] (intent(in))
    !   ocean_prof  - профиль океана (intent(in))
    !   atmos       - атмосферный форсинг (intent(in))
    !   diag        - диагностики (intent(inout), обновляются m_*, q_net, t_surface)
    ! ========================================================================
    subroutine iceberg_thermodynamics_step(state, dt, ocean_prof, atmos, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag

        real :: t_draft, s_draft, tf_draft
        real :: delta_t_basal, delta_t_lateral_avg
        real :: m_basal, m_lateral, m_surface
        real :: q_net

        ! 1. Базальное плавление
        call compute_basal_melt(ocean_prof, diag%draft, &
                                t_draft, s_draft, tf_draft, &
                                delta_t_basal, m_basal)

        diag%t_draft = t_draft
        diag%s_draft = s_draft
        diag%tf_draft = tf_draft
        diag%m_basal = m_basal

        ! 2. Боковое плавление
        call compute_lateral_melt(ocean_prof, diag%draft, &
                                  delta_t_lateral_avg, m_lateral)

        diag%m_lateral = m_lateral

        ! 3. Поверхностное плавление
        call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                                  nat(1), nat(2), nat(3), nat(4))

        diag%q_net_surface = q_net
        diag%m_surface = m_surface
    end subroutine iceberg_thermodynamics_step

    ! ========================================================================
    !   БАЗАЛЬНОЕ ПЛАВЛЕНИЕ (Stage 9.1 §13)
    ! ========================================================================
    ! m_b = C_BASAL * max(0, T(D) - Tf(D))
    ! T(D), S(D) — интерполяция профиля на глубине осадки D.
    ! Tf = -54.0 * S(D)
    !
    ! Аргументы:
    !   prof        - профиль океана (intent(in))
    !   draft       - осадка [м] (intent(in))
    !   t_draft     - температура на осадке [°C] (выход)
    !   s_draft     - соленость на осадке [кг/кг] (выход)
    !   tf_draft    - точка замерзания на осадке [°C] (выход)
    !   delta_t     - T - Tf [°C] (выход)
    !   m_basal     - базальная скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine compute_basal_melt(prof, draft, t_draft, s_draft, tf_draft, &
                                  delta_t, m_basal)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real, intent(out) :: t_draft, s_draft, tf_draft
        real, intent(out) :: delta_t, m_basal

        t_draft = interp_at_draft(prof, draft, "temp")
        s_draft = interp_at_draft(prof, draft, "salt")

        tf_draft = -54.0*s_draft

        delta_t = t_draft - tf_draft

        if (delta_t .gt. 0.0) then
            m_basal = C_BASAL*delta_t
        else
            m_basal = 0.0
            delta_t = 0.0
        end if
    end subroutine compute_basal_melt

    ! ========================================================================
    !   БОКОВОЕ ПЛАВЛЕНИЕ (Stage 9.1 §14, Method A)
    ! ========================================================================
    ! m_l = C_LATERAL * ⟨max(0, T - Tf)⟩_D
    ! Глубинно-усреднённое термическое задействование вычисляется через
    ! depth_averaged_thermal_forcing (интеграл по осадке с экстраполяцией).
    !
    ! Аргументы:
    !   prof            - профиль океана (intent(in))
    !   draft           - осадка [м] (intent(in))
    !   delta_t_avg     - ⟨ΔT⟩_D [°C] (выход)
    !   m_lateral       - боковая скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine compute_lateral_melt(prof, draft, delta_t_avg, m_lateral)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real, intent(out) :: delta_t_avg, m_lateral

        delta_t_avg = depth_averaged_thermal_forcing(prof, draft)

        if (delta_t_avg .gt. 0.0) then
            m_lateral = C_LATERAL*delta_t_avg
        else
            m_lateral = 0.0
            delta_t_avg = 0.0
        end if
    end subroutine compute_lateral_melt

! ========================================================================
    !   ПОВЕРХНОСТНОЕ ПЛАВЛЕНИЕ С ПРОГНОСТИЧЕСКОЙ ТЕМПЕРАТУРОЙ (Stage 10.2)
    ! ========================================================================
    ! C_eff dT_surface/dt = Q_net_non_melt
    ! C_eff = rho_ice * c_ice * h_eff
    ! Q_net_non_melt = SW_abs + LW_down + LW_up + SH + LH
    !
    ! Phase change logic:
    !   if T_surface < T_melt:
    !       dT = Q_net_non_melt * dt / C_eff
    !       T_surface_new = T_surface + dT
    !       if T_surface_new >= T_melt:
    !           excess_energy = Q_net_non_melt - C_eff * (T_melt - T_surface) / dt
    !           m_surface = max(excess_energy, 0) / (rho_ice * L_f)
    !           T_surface = T_melt
    !       else:
    !           m_surface = 0
    !   else:  ! T_surface >= T_melt
    !       T_surface = T_melt
    !       m_surface = max(Q_net_non_melt, 0) / (rho_ice * L_f)
    !
    ! Components:
    !   SW_abs = SW_down * (1 - albedo)
    !   LW_down = LW_EMISS * t_air^4 * (1 + LW_CLOUD_FACTOR*tcc) * ...
    !   LW_up = -ε_ice * σ * t_surf^4
    !   SH = rho_air * SH_COEFF * |V| * (t_air - t_surf)
    !   LH = rho_air * LH_COEFF * |V| * L_v * (q_air - q_sat)
    !   t_surf = state%T_surface [°C], converted to K for radiation
    !
    ! Arguments:
    !   state       - state with T_surface [°C] (intent(inout), updated)
    !   atmos       - atmospheric forcing
    !   diag        - diagnostics (updated q_net_surface, t_surface)
    !   q_net       - net heat flux [W/m²] (output)
    !   m_surface   - surface melt rate [m/s] (output)
    !   year, month, day, hour - reference date (UTC)
    ! ========================================================================
    subroutine compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                                    year, month, day, hour)
        type(iceberg_state), intent(inout) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: q_net, m_surface
        real, intent(in) :: dt
        integer, intent(in) :: year, month, day, hour

        real :: t_air_k, t_surf_k, t_dew_k
        real :: p_atm, rho_air_local, q_air, q_sat
        real :: wind_speed
        real :: sw_down, lw_down, lw_up, sh_flux, lh_flux
        real :: cos_zenith
        real :: albedo
        real :: e_sat_air, e_sat_dew, rh, e_vap
        real :: sw_absorbed
        ! --- Stage 10.1.2: SW atmospheric attenuation diagnostics ---
        real :: sw_toa
        real :: air_mass, tau_rayleigh
        real :: t_rayleigh, t_water_vap, t_aerosol, t_clear, t_cloud
        real :: precipitable_water_cm
        ! --- Stage 10.2: prognostic surface temperature ---
        real :: c_eff, q_net_non_melt, excess_energy
        real :: t_surf_new

        ! Входные параметры
        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m

        p_atm = atmos%msl
        rho_air_local = p_atm/(GAS_CONST_AIR*t_air_k)  ! ρ_air = p/(R*T) [кг/м³]

        wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

        ! Effective heat capacity of surface layer
        c_eff = RHO_ICE*C_ICE*H_EFF  ! J/(m² K)

        ! === КОРОТКОВОЛНОВАЯ РАДИАЦИЯ (Shortwave) ===
        ! Солнечная геометрия (Stage 10.1.1): астрономическая формула
        call solar_geometry(year, month, day, hour, &
                            state%time, &
                            state%latitude, state%longitude, &
                            cos_zenith)

        ! === ATMOSPHERIC VAPOR PRESSURE (always needed for LH, independent of solar geometry) ===
        ! Compute e_vap, rh, q_air before SW branch so they are valid day and night
        e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
        e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
        rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))  ! relative humidity [0-1]
        e_vap = rh*e_sat_air  ! [Pa]
        q_air = 0.622*e_vap/p_atm

        ! Polar night/day handling: cos_zenith <= 0 -> no solar radiation
        if (cos_zenith .le. 0.0) then
            sw_down = 0.0
            sw_toa = 0.0
            t_clear = 0.0
            t_cloud = 0.0
        else
            ! === ATMOSPHERIC ATTENUATION (Stage 10.1.2) ===
            ! Broadband parameterization: SW_down = S0 * cos_zenith * T_clear * T_cloud
            ! where:
            !   S0 * cos_zenith       = TOA solar flux on horizontal surface
            !   T_clear               = clear-sky atmospheric transmittance
            !   T_cloud               = cloud transmittance (function of tcc)
            !
            ! Clear-sky transmittance components:
            !   T_rayleigh  = exp(-tau_rayleigh * air_mass)  ! Rayleigh scattering
            !   T_water_vap = 1 - WV_ABSORP_COEFF * w^WV_ABSORP_EXP  ! Water vapor absorption
            !   T_aerosol   = AEROSOL_TRANS_ARCTIC  ! Background aerosol (empirical)
            !   T_clear = T_rayleigh * T_water_vap * T_aerosol
            !
            ! Cloud transmittance:
            !   T_cloud = 1 - CLOUD_TRANS_COEFF * tcc
            !   overcast (tcc=1) -> ~25% of clear-sky flux
            !
            ! All transmittances bounded to [0, 1].
            ! Final SW_down bounded to <= TOA flux.

            ! Top-of-atmosphere solar flux on horizontal surface
            sw_toa = SOLAR_CONSTANT*cos_zenith

            ! Air mass (Kasten & Young 1989 approximation for large zenith angles)
            ! m = 1 / (cos_zenith + 0.50572 * (96.07995 - zenith_deg)^-1.6364)
            ! For simplicity, use m = 1/cos_zenith with cap at 40 (zenith ~88.5 deg)
            air_mass = 1.0/cos_zenith
            if (air_mass .gt. 40.0) air_mass = 40.0

            ! Rayleigh scattering transmittance
            ! tau_rayleigh scales with surface pressure
            tau_rayleigh = TAU_RAYLEIGH_0*(p_atm/101325.0)
            t_rayleigh = exp(-tau_rayleigh*air_mass)
            t_rayleigh = max(0.0, min(1.0, t_rayleigh))

            ! Water vapor absorption (Lacis & Hansen 1974 broadband approximation)
            ! Precipitable water w [cm] estimated from surface vapor pressure
            ! w = PRECIP_WATER_SCALE * (e_vap / 100.0) * (101325.0 / p_atm)
            ! where e_vap [Pa] -> hPa via /100
            precipitable_water_cm = PRECIP_WATER_SCALE*(e_vap/100.0)*(101325.0/p_atm)
            precipitable_water_cm = max(0.0, precipitable_water_cm)

            ! T_water_vap = 1 - WV_ABSORP_COEFF * w^WV_ABSORP_EXP
            t_water_vap = 1.0 - WV_ABSORP_COEFF*(precipitable_water_cm**WV_ABSORP_EXP)
            t_water_vap = max(0.0, min(1.0, t_water_vap))

            ! Aerosol transmittance (Arctic background, empirical)
            t_aerosol = AEROSOL_TRANS_ARCTIC

            ! Clear-sky transmittance
            t_clear = t_rayleigh*t_water_vap*t_aerosol
            t_clear = max(0.0, min(1.0, t_clear))

            ! Cloud transmittance: linear in tcc
            t_cloud = 1.0 - CLOUD_TRANS_COEFF*atmos%tcc
            t_cloud = max(0.0, min(1.0, t_cloud))

            ! Final downward SW at surface
            sw_down = sw_toa*t_clear*t_cloud

            ! Bound check: SW_down cannot exceed TOA flux
            sw_down = min(sw_down, sw_toa)
            sw_down = max(0.0, sw_down)
        end if

        albedo = ALBEDO_ICE
        sw_absorbed = sw_down*(1.0 - albedo)  ! поглощённая SW

        ! Current surface temperature in Kelvin for radiation calculations
        t_surf_k = state%T_surface + 273.15

        ! === ДЛИННОВОЛНОВАЯ РАДИАЦИЯ (Longwave) ===
        ! Входящая LW: эмпирическая формула (legacy HEAT)
        lw_down = LW_EMISS*t_air_k**4* &
                  (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
                  (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

        ! Исходящая LW: чёрное тело с эмиссивностью льда
        lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4

        ! === ЯВНОЕ ТЕПЛО (Sensible Heat) ===
        ! Stage 10.3: Modern bulk formulation
        ! Q_SH = rho_air * CP_AIR * C_H * U * (T_air - T_surface)
        ! C_H = C_H_NEUTRAL = 1.5e-3 (Andreas et al. 2010, Arctic sea ice)
        ! Sign: Q_SH > 0 -> atmosphere heats iceberg
        sh_flux = rho_air_local*CP_AIR*C_H_NEUTRAL*wind_speed*(t_air_k - t_surf_k)

        ! === СКРЫТОЕ ТЕПЛО (Latent Heat) ===
        ! Stage 10.3: Modern bulk formulation with ice saturation
        ! Q_LH = rho_air * L_S * C_E * U * (q_air - q_sat_ice)
        ! C_E = C_E_NEUTRAL = 1.5e-3
        ! L_S = 2.835e6 J/kg (latent heat of sublimation at 0°C)
        ! q_sat_ice = saturation specific humidity over ICE (Murphy & Koop 2005)
        ! q_air = 0.622 * e_vap / p_atm (from ERA5 d2m/t2m, computed before solar branch)
        ! Sign: Q_LH > 0 -> vapor flux supplies energy to surface (condensation/deposition)
        !       Q_LH < 0 -> vapor flux removes energy from surface (sublimation)
        ! Stage 10.3: Q_LH is ENERGY FLUX ONLY; no mass change from sublimation/deposition
        ! (Stage 10.4 will partition Q_LH into mass fluxes)
        q_sat = saturation_vapor_pressure_ice(t_surf_k) / p_atm * 0.622
        lh_flux = rho_air_local*L_S*C_E_NEUTRAL*wind_speed*(q_air - q_sat)

        ! === NET NON-MELT HEAT FLUX ===
        q_net_non_melt = sw_absorbed + lw_down + lw_up + sh_flux + lh_flux

        ! === PROGNOSTIC SURFACE TEMPERATURE WITH PHASE CHANGE (Stage 10.2) ===
        if (state%T_surface .lt. T_MELT) then
            ! Surface below melting point: temperature evolution
            t_surf_new = state%T_surface + q_net_non_melt*dt/c_eff

            if (t_surf_new .ge. T_MELT) then
                ! Crossed melting point within timestep
                ! Energy used to reach T_melt
                excess_energy = q_net_non_melt - c_eff*(T_MELT - state%T_surface)/dt
                state%T_surface = T_MELT
                if (excess_energy .gt. 0.0) then
                    m_surface = excess_energy/(RHO_ICE*LATENT_HEAT)
                else
                    m_surface = 0.0
                end if
            else
                ! Still below melting point
                state%T_surface = t_surf_new
                m_surface = 0.0
            end if
        else
            ! Surface at or above melting point
            if (q_net_non_melt .gt. 0.0) then
                ! Positive energy -> melt, surface stays at T_MELT
                state%T_surface = T_MELT
                m_surface = q_net_non_melt/(RHO_ICE*LATENT_HEAT)
            else
                ! Negative energy -> surface cools below T_MELT
                ! (no melt, temperature drops)
                t_surf_new = state%T_surface + q_net_non_melt*dt/c_eff
                state%T_surface = min(T_MELT, t_surf_new)
                m_surface = 0.0
            end if
        end if

        ! Total net flux for diagnostics (includes melt energy)
        q_net = q_net_non_melt - m_surface*RHO_ICE*LATENT_HEAT/dt

        diag%t_surface = state%T_surface
    end subroutine compute_surface_melt

    ! ========================================================================
    !   НАСЫЩЕННОЕ ПАРЦИАЛЬНОЕ ДАВЛЕНИЕ НАД ЛЁДОМ (Murphy & Koop 2005)
    ! ========================================================================
    ! Формула Мерфи и Купа (2005) для насыщенного парциального давления
    ! водяного пара над плоским интерфейсом лед-воздух.
    ! Диапазон применимости: 50–273 K (для Арктики: 180–273 K).
    ! Источник: Murphy D.M., Koop T. (2005) "Review of the vapour pressures
    ! of ice and supercooled water for atmospheric applications"
    ! QJRMS, 131, 1539-1565. Equation (10).
    !
    ! ln(e_sat_ice) = A - B/T + C*ln(T) - D*T
    ! где:
    !   A = 9.550426
    !   B = 5723.265
    !   C = 3.53068
    !   D = 0.00728332
    ! e_sat в [Па], T в [К]
    !
    ! Аргументы:
    !   T_k - температура [К] (intent(in))
    !   e_sat_ice - насыщенное парциальное давление над льдом [Па] (выход)
    ! ========================================================================
    pure real function saturation_vapor_pressure_ice(T_k) result(e_sat_ice)
        real, intent(in) :: T_k

        e_sat_ice = exp(MURPHY_KOOP_A - MURPHY_KOOP_B/T_k &
                        + MURPHY_KOOP_C*log(T_k) - MURPHY_KOOP_D*T_k)
    end function saturation_vapor_pressure_ice

    ! ========================================================================
    !   ТОЧКА ЗАМЕРЗАНИЯ (Legacy HEAT formula)
    ! ========================================================================
    ! Tf = -54.0 * S  [°C], S — массовая доля [кг/кг]
    ! Эквивалентно Tf = -0.054 * S_PSU [°C], так как S_mass = S_PSU/1000.
    ! Для S=35 PSU = 0.035 кг/кг: Tf = -1.89°C.
    !
    ! Аргументы:
    !   salinity - соленость [кг/кг] (intent(in))
    !   tf       - точка замерзания [°C] (выход)
    ! ========================================================================
    pure real function freezing_point(salinity) result(tf)
        real, intent(in) :: salinity
        tf = -54.0*salinity
    end function freezing_point

end module iceberg_thermodynamics
