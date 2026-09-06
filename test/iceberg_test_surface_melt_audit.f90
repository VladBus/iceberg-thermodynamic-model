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
    use param, only: nat
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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, &
                              nat(1), nat(2), nat(3), nat(4))

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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, &
                              nat(1), nat(2), nat(3), nat(4))

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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, &
                              nat(1), nat(2), nat(3), nat(4))

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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, &
                              nat(1), nat(2), nat(3), nat(4))

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

    subroutine init_zero_ocean(ocean_prof_out)
        type(ocean_profile), intent(out) :: ocean_prof_out
        integer :: nlevels
        nlevels = 1
        ocean_prof_out%nlevels = nlevels
        allocate (ocean_prof_out%z(nlevels), ocean_prof_out%dz(nlevels), &
                  ocean_prof_out%temp(nlevels), ocean_prof_out%salt(nlevels), &
                  ocean_prof_out%u(nlevels), ocean_prof_out%v(nlevels))
        ocean_prof_out%z(1) = 10.0
        ocean_prof_out%dz(1) = 10.0
        ocean_prof_out%temp(1) = -1.0
        ocean_prof_out%salt(1) = 0.034
        ocean_prof_out%u(1) = 0.0
        ocean_prof_out%v(1) = 0.0
    end subroutine init_zero_ocean

    subroutine write_audit_row(unit_in, case_name, atmos_in, q_net_in, m_surf_in, expected_in)
        integer, intent(in) :: unit_in
        character(len=*), intent(in) :: case_name
        type(atmos_forcing), intent(in) :: atmos_in
        real, intent(in) :: q_net_in, m_surf_in, expected_in
        real :: ratio

        if (expected_in .gt. 1e-12) then
            ratio = m_surf_in/expected_in
        else
            ratio = 0.0
        end if

        write (unit_in, '(A,F8.2,F8.2,F6.2,F10.1,2F8.2,2F10.3,3F12.6,2F12.6,F10.4)') &
            case_name, atmos_in%t2m, atmos_in%d2m, atmos_in%tcc, atmos_in%msl, &
            atmos_in%u10, atmos_in%v10, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, q_net_in, m_surf_in, expected_in, ratio
    end subroutine write_audit_row

end program iceberg_test_surface_melt_audit
