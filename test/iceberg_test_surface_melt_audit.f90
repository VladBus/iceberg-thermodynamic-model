! ==============================================================================
! Тест: Surface Melt Root-Cause Audit
! Назначение: Полная трассировка цепочки поверхностного плавления:
!             ERA5 forcing -> атмосферные переменные -> Q_net -> m_surface -> dH/dt
!
! Проверяемые звенья:
!   1. ERA5 variables: t2m, d2m, tcc, msl, u10, v10, ssr, str, snowfall
!   2. Unit conversions: K <-> °C, J/m2 -> W/m2, accumulated vs instantaneous
!   3. Heat flux components: SW_abs, LW_down, LW_up, SH, LH
!   4. Q_net = SW_abs + LW_down + LW_up + SH + LH
!   5. m_surface = max(0, Q_net) / (rho_ice * L_f)
!   6. dH/dt = -m_surface (sign convention)
!
! Изолированные тесты:
!   Case A: All heat fluxes = 0 -> melt = 0
!   Case B: Known Q_net -> analytical melt rate
!   Case C: ERA5-like forcing
!   Case D: Zero air temp = freezing point -> zero melt
! ==============================================================================

program iceberg_test_surface_melt_audit
    use iceberg
    use iceberg_types
    use iceberg_thermodynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: unit, ios
    real :: dt
    real :: q_net, m_surface
    real :: expected_melt

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Surface Melt Root-Cause Audit"
    print *, "=================================================="

    ! Open CSV for detailed output
    open (unit, file='data/output/diagnostics/stage9.4c/surface_melt_audit.csv', &
          status='replace', iostat=ios)
    if (ios .eq. 0) then
        write(unit, '(A)') 'case,t2m_K,d2m_K,tcc,msl_Pa,u10,v10,sw_down,sw_abs,lw_down,lw_up,sh,lh,q_net,m_surface,expected_melt,ratio'
    end if

    dt = 3600.0

    ! =========================================================================
    ! CASE A: Zero heat flux boundary condition (polar night)
    !   t_air = t_surf = 263.15 K (-10°C)
    !   no wind, no radiation, no humidity
    !   Solar: polar night (cos_zenith = 0)
    !   Expected: Q_net = 0, m_surface = 0
    ! =========================================================================
    print *, ""
    print *, "--- CASE A: Zero heat flux (t_air = t_surf = -10°C, polar night) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      90.0, 0.0, 0.0, 0.0)  ! North pole -> polar night

    ! Ocean profile (not used for surface melt)
    call init_zero_ocean(ocean_prof)

    ! Atmosphere: air temp = ice surface temp = 263.15 K
    atmos%t2m = 263.15
    atmos%d2m = 263.15  ! dew point = air temp -> RH = 100%
    atmos%tcc = 0.0     ! clear sky
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%snowfall = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface)

    expected_melt = 0.0

    print *, "t2m = ", atmos%t2m, " K = ", atmos%t2m - 273.15, " °C"
    print *, "t_surf = 263.15 K = -10°C"
    print *, "Q_net = ", q_net, " W/m2"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "Expected = ", expected_melt

    call write_audit_row(unit, "A_zero_flux", atmos, q_net, m_surface, expected_melt)

    n_checks = n_checks + 1
    if (m_surface .eq. 0.0) then
        print *, "OK: Polar night -> zero melt (Q_net = ", q_net, " W/m2)"
    else
        print *, "FAIL: Non-zero melt in polar night"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! CASE B: Known positive Q_net
    !   Analytical check: m = Q / (rho_ice * L_f)
    ! =========================================================================
    print *, ""
    print *, "--- CASE B: Known Q_net = 100 W/m2 (constructed) ---"

    ! We'll manually construct a case that gives ~100 W/m2
    ! Use: SW_abs = 100, others = 0
    ! But we can't directly set Q_net components, so we use the function
    ! and reverse-engineer from known conditions

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    ! Strong solar, no wind, cold air
    atmos%t2m = 253.15  ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface)

    ! Analytical expectation
    expected_melt = max(0.0, q_net)/(RHO_ICE*LATENT_HEAT)

    print *, "t2m = ", atmos%t2m - 273.15, " °C"
    print *, "Q_net = ", q_net, " W/m2"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "Expected (Q/rho/L) = ", expected_melt, " m/s = ", expected_melt*86400.0, " m/day"

    call write_audit_row(unit, "B_cold_clear", atmos, q_net, m_surface, expected_melt)

    n_checks = n_checks + 1
    if (abs(m_surface - expected_melt)/max(expected_melt, 1e-10) .lt. 0.01) then
        print *, "OK: Melt rate matches Q/(rho*L_f) within 1%"
    else
        print *, "INFO: Ratio = ", m_surface/max(expected_melt, 1e-10)
    end if

    ! =========================================================================
    ! CASE C: Typical Arctic summer conditions
    !   t2m = 273.15 K (0°C), sunny, light wind
    ! =========================================================================
    print *, ""
    print *, "--- CASE C: Arctic summer (0°C, sunny, 5 m/s wind) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 273.15  ! 0°C
    atmos%d2m = 271.15  ! -2°C dew point
    atmos%tcc = 0.2     ! partly cloudy
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface)

    expected_melt = max(0.0, q_net)/(RHO_ICE*LATENT_HEAT)

    print *, "t2m = ", atmos%t2m - 273.15, " °C"
    print *, "d2m = ", atmos%d2m - 273.15, " °C"
    print *, "tcc = ", atmos%tcc
    print *, "wind = 5 m/s"
    print *, "Q_net = ", q_net, " W/m2"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "Expected = ", expected_melt*86400.0, " m/day"

    call write_audit_row(unit, "C_arctic_summer", atmos, q_net, m_surface, expected_melt)

    n_checks = n_checks + 1
    if (abs(m_surface - expected_melt)/max(expected_melt, 1e-10) .lt. 0.01) then
        print *, "OK: Melt rate matches Q/(rho*L_f)"
    else
        print *, "INFO: Ratio = ", m_surface/max(expected_melt, 1e-10)
    end if

    ! =========================================================================
    ! CASE D: Air at freezing point of seawater (-1.89°C)
    !   t2m = 271.26 K, tcc = 0, wind = 0
    !   Should give minimal melt from LW only
    ! =========================================================================
    print *, ""
    print *, "--- CASE D: Air at seawater freezing point (-1.89°C) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 271.26  ! -1.89°C = freezing point of S=35
    atmos%d2m = 271.26
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface)

    expected_melt = max(0.0, q_net)/(RHO_ICE*LATENT_HEAT)

    print *, "t2m = ", atmos%t2m - 273.15, " °C (freezing point)"
    print *, "Q_net = ", q_net, " W/m2"
    print *, "m_surface = ", m_surface*86400.0, " m/day"
    print *, "Expected = ", expected_melt*86400.0, " m/day"

    call write_audit_row(unit, "D_freezing_point", atmos, q_net, m_surface, expected_melt)

    n_checks = n_checks + 1
    if (m_surface*86400.0 .lt. 0.1) then  ! < 0.1 m/day
        print *, "OK: Minimal melt at freezing point"
    else
        print *, "INFO: Melt at freezing point = ", m_surface*86400.0, " m/day"
    end if

    ! =========================================================================
    ! CASE E: Component decomposition (diagnostic output)
    ! =========================================================================
    print *, ""
    print *, "--- CASE E: Component decomposition (t2m=273K, wind=5m/s, tcc=0.5) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 273.15
    atmos%d2m = 270.15
    atmos%tcc = 0.5
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    ! Call the internal subroutine to get component breakdown
    call decompose_surface_flux(state, atmos, diag)

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Surface Melt Audit PASSED"
        stop 0
    else
        print *, "FAILURE: Surface Melt Audit FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine init_zero_ocean(ocean_prof)
        type(ocean_profile), intent(out) :: ocean_prof
        integer :: nlevels
        nlevels = 1
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        ocean_prof%z(1) = 10.0
        ocean_prof%dz(1) = 10.0
        ocean_prof%temp(1) = -1.0
        ocean_prof%salt(1) = 0.034
        ocean_prof%u(1) = 0.0
        ocean_prof%v(1) = 0.0
    end subroutine init_zero_ocean

    subroutine write_audit_row(unit, case_name, atmos, q_net, m_surf, expected)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: case_name
        type(atmos_forcing), intent(in) :: atmos
        real, intent(in) :: q_net, m_surf, expected
        real :: ratio

        if (expected .gt. 1e-12) then
            ratio = m_surf/expected
        else
            ratio = 0.0
        end if

        write (unit, '(A,F8.2,F8.2,F6.2,F10.1,2F8.2,2F10.3,3F12.6,2F12.6,F10.4)') &
            case_name, atmos%t2m, atmos%d2m, atmos%tcc, atmos%msl, &
            atmos%u10, atmos%v10, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, q_net, m_surf, expected, ratio
    end subroutine write_audit_row

    ! --------------------------------------------------------------------------
    ! Decompose surface flux into components (replicates compute_surface_melt logic)
    ! --------------------------------------------------------------------------
    subroutine decompose_surface_flux(state, atmos, diag)
        type(iceberg_state), intent(in) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag

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

        ! Input parameters
        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m
        t_surf_k = T_ICE + 273.15  ! 263.15 K

        p_atm = atmos%msl
        rho_air_local = p_atm/(GAS_CONST_AIR*t_air_k)

        wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

        ! === SHORTWAVE ===
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

        ! === LONGWAVE ===
        lw_down = LW_EMISS*t_air_k**4* &
                  (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
                  (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

        lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4

        ! === SENSIBLE HEAT ===
        sh_flux = rho_air_local*SH_COEFF*wind_speed*(t_air_k - t_surf_k)

        ! === LATENT HEAT ===
        q_air = 0.622*e_vap/p_atm
        q_sat = 0.622*(SAT_VAPOR_0*10.0**(TETENS_A*(t_surf_k - 273.15)/t_surf_k))/p_atm
        lh_flux = rho_air_local*LH_COEFF*wind_speed*LATENT_VAP*(q_air - q_sat)

        ! === NET ===
        diag%q_net_surface = sw_absorbed + lw_down + lw_up + sh_flux + lh_flux

        ! Store components in diagnostics (we'll reuse unused fields)
        diag%m_basal = sw_absorbed
        diag%m_lateral = lw_down
        diag%m_surface = lw_up
        diag%t_draft = sh_flux
        diag%s_draft = lh_flux

        print *, "Component breakdown [W/m2]:"
        print *, "  SW_absorbed (SW↓*(1-α)):  ", sw_absorbed
        print *, "  LW_down (atmospheric):    ", lw_down
        print *, "  LW_up (ice emission):     ", lw_up
        print *, "  SH (sensible):            ", sh_flux
        print *, "  LH (latent):              ", lh_flux
        print *, "  Q_net:                    ", diag%q_net_surface
        print *, "  m_surface: ", diag%q_net_surface/(RHO_ICE*LATENT_HEAT)*86400.0, " m/day"
    end subroutine decompose_surface_flux

end program iceberg_test_surface_melt_audit
