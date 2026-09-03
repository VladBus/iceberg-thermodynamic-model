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

contains

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
        call compute_surface_melt(state, atmos, diag, q_net, m_surface)

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
    !   ПОВЕРХНОСТНОЕ ПЛАВЛЕНИЕ (Stage 9.1 §15)
    ! ========================================================================
    ! m_s = max(0, Q_net) / (ρ_ice * L_f)
    ! Q_net = SW_absorbed + LW_down + LW_up + SH + LH
    !
    ! Компоненты Q_net [Вт/м²]:
    !   1. SW_absorbed = SW_down * (1 - α_ice)   — поглощённая коротковолновая
    !      SW_down = SOLAR_CONST * cos²(zenith) * (1 - CLOUD_COEFF*tcc³) / (rad_b1*e_vap + rad_b2)
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
    !   state       - состояние (latitude для солнечного зенита)
    !   atmos       - атмосферный форсинг
    !   diag        - диагностики (обновляется q_net_surface)
    !   q_net       - чистый тепловой поток [Вт/м²] (выход)
    !   m_surface   - поверхностная скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine compute_surface_melt(state, atmos, diag, q_net, m_surface)
        type(iceberg_state), intent(in) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: q_net, m_surface

        real :: t_air_k, t_surf_k, t_dew_k
        real :: p_atm, rho_air_local, q_air, q_sat
        real :: wind_speed
        real :: sw_down, lw_down, lw_up, sh_flux, lh_flux
        real :: cz, decl, hour_angle, cos_zenith
        real :: rad_b1, rad_b2, e_vap
        real :: albedo
        real :: lat_rad, dec_rad
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
        lat_rad = state%latitude/57.2957795  ! градусы → радианы
        decl = 0.0                           ! склонение Солнца (упрощение: экватор)
        dec_rad = decl/57.2957795

        hour_angle = 0.0  ! локальный полдень (упрощение)
        ! cos(zenith) = sin(φ)sin(δ) + cos(φ)cos(δ)cos(h)
        cos_zenith = sin(lat_rad)*sin(dec_rad) + cos(lat_rad)*cos(dec_rad)*cos(hour_angle)
        cos_zenith = max(0.0, cos_zenith)  ! только дневное

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
