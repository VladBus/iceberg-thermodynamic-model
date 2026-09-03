! ==============================================================================
! Модуль: iceberg_thermodynamics
! Назначение: Термодинамика айсберга — базальное, боковое и поверхностное плавление.
! Физика: Stage 9.1 §10-15.
!   Базальное: m_b = Cb * max(0, T(D) - Tf(D)) / (rho_ice * Lf)  [m/s]
!   Боковое:   m_l = Cl * <T - Tf>_D / (rho_ice * Lf)           [m/s]
!              где <...>_D = (1/D) ∫_0^D max(0, T(z) - Tf(z)) dz
!   Поверхностное: m_s = max(0, Q_net) / (rho_ice * Lf)         [m/s]
!   Q_net = SW↓(1-α) + LW↓ - LW↑ + SH + EL  (адаптировано из legacy HEAT)
! Единицы: SI (м, с, кг, К/°C, Вт/м²).
! Точность: default real (float32).
! ==============================================================================

module iceberg_thermodynamics
    use iceberg_types
    use iceberg_forcing, only: interp_at_draft, depth_averaged_thermal_forcing
    implicit none

    ! Константы для поверхностного баланса (адаптированы из legacy HEAT)
    real, parameter :: SOLAR_CONSTANT = 1353.0
    real, parameter :: CLOUD_COEFF = 0.6
    real, parameter :: LW_EMISS = 5.4999e-8
    real, parameter :: LW_CLOUD_FACTOR = 0.275
    real, parameter :: LW_HUMID_COEFF = 0.261
    real, parameter :: LW_HUMID_EXP = 7.77e-4
    real, parameter :: SH_COEFF = 1.7068
    real, parameter :: LH_COEFF = 0.6650735
    real, parameter :: LATENT_VAP = 2.5e6
    real, parameter :: GAS_CONST_AIR = 287.0
    real, parameter :: SAT_VAPOR_0 = 610.78
    real, parameter :: TETENS_A = 8.61503
    real, parameter :: WATER_ALBEDO = 0.06
    real, parameter :: WATER_EMISS = 0.97

contains

    ! ========================================================================
    !   ГЛАВНАЯ ПОДПРОГРАММА ТЕРМОДИНАМИКИ (переименована)
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

        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m
        t_surf_k = T_ICE + 273.15

        p_atm = atmos%msl
        rho_air_local = p_atm/(GAS_CONST_AIR*t_air_k)

        wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

        ! === КОРОТКОВОЛНОВАЯ РАДИАЦИЯ ===
        lat_rad = state%latitude/57.2957795
        decl = 0.0
        dec_rad = decl/57.2957795

        hour_angle = 0.0
        cos_zenith = sin(lat_rad)*sin(dec_rad) + cos(lat_rad)*cos(dec_rad)*cos(hour_angle)
        cos_zenith = max(0.0, cos_zenith)

        sw_down = SOLAR_CONSTANT*cos_zenith**2*(1.0 - CLOUD_COEFF*atmos%tcc**3)

        rad_b1 = (cos_zenith + 2.7)*1.0e-5
        rad_b2 = 1.085*cos_zenith + 0.1

        e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
        e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
        rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))
        e_vap = rh*e_sat_air

        sw_down = sw_down/(rad_b1*e_vap + rad_b2)

        albedo = ALBEDO_ICE
        sw_absorbed = sw_down*(1.0 - albedo)

        ! === ДЛИННОВОЛНОВАЯ РАДИАЦИЯ ===
        lw_down = LW_EMISS*t_air_k**4* &
                  (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
                  (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

        lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4

        ! === ЯВНОЕ ТЕПЛО ===
        sh_flux = rho_air_local*SH_COEFF*wind_speed*(t_air_k - t_surf_k)

        ! === СКРЫТОЕ ТЕПЛО ===
        q_air = 0.622*e_vap/p_atm
        q_sat = 0.622*(SAT_VAPOR_0*10.0**(TETENS_A*(t_surf_k - 273.15)/t_surf_k))/p_atm
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
    pure real function freezing_point(salinity) result(tf)
        real, intent(in) :: salinity
        tf = -54.0*salinity
    end function freezing_point

end module iceberg_thermodynamics
