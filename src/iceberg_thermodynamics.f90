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
    real, parameter :: CLOUD_COEFF = 0.6        ! Коэффициент затухания от облаков
    real, parameter :: LW_EMISS = 5.4999e-8  ! Эффективная эмиссивность атмосферы [Вт/(м²·К⁴)]
    real, parameter :: LW_CLOUD_FACTOR = 0.275      ! Фактор облачности для LW
    real, parameter :: LW_HUMID_COEFF = 0.261      ! Коэффициент влажности для LW
    real, parameter :: LW_HUMID_EXP = 7.77e-4    ! Показатель влажности для LW
    real, parameter :: SH_COEFF = 1.7068     ! Коэффициент явного теплообмена (Stanton)
    real, parameter :: LH_COEFF = 0.6650735  ! Коэффициент скрытого теплообмена (Dalton)
    real, parameter :: LATENT_VAP = 2.5e6      ! Удельная теплота парообразования воды [Дж/кг]
    real, parameter :: GAS_CONST_AIR = 287.0      ! Газовая постоянная сухого воздуха [Дж/(кг·К)]
    real, parameter :: SAT_VAPOR_0 = 610.78     ! Насыщенное парциальное давление при 0°C [Па]
    real, parameter :: TETENS_A = 8.61503    ! Константа Тетенса для e_sat
    real, parameter :: WATER_ALBEDO = 0.06       ! Альбедо воды
    real, parameter :: WATER_EMISS = 0.97       ! Эмиссивность воды

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
    !   state       - состояние айсберга (intent(in))
    !   dt          - шаг по времени [с] (intent(in))
    !   ocean_prof  - профиль океана (intent(in))
    !   atmos       - атмосферный форсинг (intent(in))
    !   diag        - диагностики (intent(inout), обновляются m_*, q_net)
    ! ========================================================================
    subroutine iceberg_thermodynamics_step(state, dt, ocean_prof, atmos, diag)
        type(iceberg_state), intent(in) :: state
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
        call compute_surface_melt(state, atmos, diag, q_net, m_surface, &
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
    !   ПОВЕРХНОСТНОЕ ПЛАВЛЕНИЕ (Stage 9.1 §15 + Stage 10.1.1 solar geometry)
    ! ========================================================================
    ! m_s = max(0, Q_net) / (ρ_ice * L_f)
    ! Q_net = SW_absorbed + LW_down + LW_up + SH + LH
    !
    ! Компоненты Q_net [Вт/м²]:
    !   1. SW_absorbed = SW_down * (1 - α_ice)   — поглощённая коротковолновая
    !      SW_down = SOLAR_CONST * cos²(zenith) * (1 - CLOUD_COEFF*tcc³) / (rad_b1*e_vap + rad_b2)
    !      cos(zenith) вычисляется через астрономическую солнечную геометрию (Stage 10.1.1)
    !   2. LW_down = LW_EMISS * t_air⁴ * (1 + LW_CLOUD_FACTOR*tcc) *
    !                (1 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15-t_air)²))
    !   3. LW_up = -ε_ice * σ * t_surf⁴          — исходящая длинноволновая
    !   4. SH = ρ_air * SH_COEFF * |V_wind| * (t_air - t_surf)  — явное тепло
    !   5. LH = ρ_air * LH_COEFF * |V_wind| * L_v * (q_air - q_sat) — скрытое тепло
    !
    ! t_surf = T_ICE + 273.15 = 263.15 К
    ! ρ_air = p_atm / (R_air * t_air)
    ! q_air = 0.622 * e_vap / p_atm
    ! q_sat = 0.622 * e_sat(t_surf) / p_atm
    !
    ! Аргументы:
    !   state       - состояние (latitude, longitude, time для солнечной геометрии)
    !   atmos       - атмосферный форсинг
    !   diag        - диагностики (обновляется q_net_surface)
    !   q_net       - чистый тепловой поток [Вт/м²] (выход)
    !   m_surface   - поверхностная скорость плавления [м/с] (выход)
    !   year, month, day, hour - референс-дата (UTC) начала моделирования
    ! ========================================================================
    subroutine compute_surface_melt(state, atmos, diag, q_net, m_surface, &
                                    year, month, day, hour)
        type(iceberg_state), intent(in) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: q_net, m_surface
        integer, intent(in) :: year, month, day, hour

        real :: t_air_k, t_surf_k, t_dew_k
        real :: p_atm, rho_air_local, q_air, q_sat
        real :: wind_speed
        real :: sw_down, lw_down, lw_up, sh_flux, lh_flux
        real :: cos_zenith
        real :: rad_b1, rad_b2, e_vap
        real :: albedo
        real :: e_sat_air, e_sat_dew, rh
        real :: sw_absorbed

        ! Входные параметры
        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m
        t_surf_k = T_ICE + 273.15  ! 263.15 К

        p_atm = atmos%msl
        rho_air_local = p_atm/(GAS_CONST_AIR*t_air_k)  ! ρ_air = p/(R*T) [кг/м³]

        wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

        ! === КОРОТКОВОЛНОВАЯ РАДИАЦИЯ (Shortwave) ===
        ! Солнечная геометрия (Stage 10.1.1): астрономическая формула
        call solar_geometry(year, month, day, hour, &
                            state%time, &
                            state%latitude, state%longitude, &
                            cos_zenith)

        ! Polar night/day handling: cos_zenith <= 0 -> no solar radiation
        if (cos_zenith .le. 0.0) then
            sw_down = 0.0
        else
            ! Входящая коротковолновая радиация с облачностью
            sw_down = SOLAR_CONSTANT*cos_zenith**2*(1.0 - CLOUD_COEFF*atmos%tcc**3)

            ! Эмпирическая коррекция атмосферной пропускания (legacy HEAT)
            rad_b1 = (cos_zenith + 2.7)*1.0e-5
            rad_b2 = 1.085*cos_zenith + 0.1

            ! Парциальное давление водяного пара
            e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
            e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
            rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))  ! относительная влажность [0-1]
            e_vap = rh*e_sat_air

            sw_down = sw_down/(rad_b1*e_vap + rad_b2)  ! итоговое SW_down
        end if

        albedo = ALBEDO_ICE
        sw_absorbed = sw_down*(1.0 - albedo)  ! поглощённая SW

        ! === ДЛИННОВОЛНОВАЯ РАДИАЦИЯ (Longwave) ===
        ! Входящая LW: эмпирическая формула (legacy HEAT)
        lw_down = LW_EMISS*t_air_k**4* &
                  (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
                  (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

        ! Исходящая LW: чёрное тело с эмиссивностью льда
        lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4

        ! === ЯВНОЕ ТЕПЛО (Sensible Heat) ===
        ! SH = ρ_air * C_H * |V| * (T_air - T_surf)
        sh_flux = rho_air_local*SH_COEFF*wind_speed*(t_air_k - t_surf_k)

        ! === СКРЫТОЕ ТЕПЛО (Latent Heat) ===
        ! q = 0.622 * e / p
        q_air = 0.622*e_vap/p_atm
        q_sat = 0.622*(SAT_VAPOR_0*10.0**(TETENS_A*(t_surf_k - 273.15)/t_surf_k))/p_atm
        ! LH = ρ_air * C_E * |V| * L_v * (q_air - q_sat)
        lh_flux = rho_air_local*LH_COEFF*wind_speed*LATENT_VAP*(q_air - q_sat)

        ! === ЧИСТЫЙ ТЕПЛОВОЙ ПОТОК ===
        q_net = sw_absorbed + lw_down + lw_up + sh_flux + lh_flux

        if (q_net .gt. 0.0) then
            m_surface = q_net/(RHO_ICE*LATENT_HEAT)
        else
            m_surface = 0.0
        end if
    end subroutine compute_surface_melt

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
