! ==============================================================================
! Тест: Surface Energy Balance Closure
! Назначение: Проверить Q_net = SW + LW + SH + LH независимо от melt conversion.
! ==============================================================================

program iceberg_test_surface_energy_balance
    use iceberg
    use iceberg_thermodynamics
    implicit none

    integer :: n_errors, n_checks
    integer :: i

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    real :: q_net_prod, m_surf_prod
    real :: q_net_sum
    real :: sw_abs, lw_down, lw_up, sh_flux, lh_flux
    real :: expected_melt

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Surface Energy Balance Closure"
    print *, "=================================================="
    print *, ""

    ! Test Case 1: Arctic summer conditions
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 273.15
    atmos%d2m = 270.15
    atmos%tcc = 0.5
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0
    atmos%snowfall = 0.0

    ! Get production Q_net and components via the internal decomposition
    call decompose_surface_flux_prod(state, atmos, diag, &
                                     sw_abs, lw_down, lw_up, sh_flux, lh_flux, &
                                     q_net_prod, m_surf_prod)

    ! Sum components independently
    q_net_sum = sw_abs + lw_down + lw_up + sh_flux + lh_flux

    print *, "Case 1: Arctic summer (0°C, 50% cloud, 5 m/s)"
    print *, "  SW_abs   = ", sw_abs
    print *, "  LW_down  = ", lw_down
    print *, "  LW_up    = ", lw_up
    print *, "  SH       = ", sh_flux
    print *, "  LH       = ", lh_flux
    print *, "  Sum      = ", q_net_sum
    print *, "  Prod Q   = ", q_net_prod
    print *, "  Diff     = ", q_net_sum - q_net_prod

    n_checks = n_checks + 1
    if (abs(q_net_sum - q_net_prod) .lt. 1e-4) then
        print *, "  OK: Energy balance closes"
    else
        print *, "  FAIL: Balance error = ", q_net_sum - q_net_prod
        n_errors = n_errors + 1
    end if

    ! Check melt conversion
    expected_melt = max(0.0, q_net_prod)/(RHO_ICE*LATENT_HEAT)
    print *, "  m_surf prod = ", m_surf_prod, " m/s"
    print *, "  m_surf expected = ", expected_melt, " m/s"
    n_checks = n_checks + 1
    if (abs(m_surf_prod - expected_melt)/max(expected_melt, 1e-12) .lt. 1e-6) then
        print *, "  OK: Melt conversion correct"
    else
        print *, "  FAIL: Melt conversion error"
        n_errors = n_errors + 1
    end if

    ! Test Case 2: Cold, clear, no wind
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      80.0, 0.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 253.15  ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call decompose_surface_flux_prod(state, atmos, diag, &
                                     sw_abs, lw_down, lw_up, sh_flux, lh_flux, &
                                     q_net_prod, m_surf_prod)

    q_net_sum = sw_abs + lw_down + lw_up + sh_flux + lh_flux

    print *, ""
    print *, "Case 2: Cold clear (-20°C, no wind)"
    print *, "  SW_abs   = ", sw_abs
    print *, "  LW_down  = ", lw_down
    print *, "  LW_up    = ", lw_up
    print *, "  SH       = ", sh_flux
    print *, "  LH       = ", lh_flux
    print *, "  Sum      = ", q_net_sum
    print *, "  Prod Q   = ", q_net_prod

    n_checks = n_checks + 1
    if (abs(q_net_sum - q_net_prod) .lt. 1e-4) then
        print *, "  OK: Energy balance closes"
    else
        print *, "  FAIL: Balance error = ", q_net_sum - q_net_prod
        n_errors = n_errors + 1
    end if

    ! Test Case 3: Humid, windy
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      70.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 275.15  ! 2°C
    atmos%d2m = 274.15  ! 1°C dew
    atmos%tcc = 0.8
    atmos%msl = 100000.0
    atmos%u10 = 15.0
    atmos%v10 = 5.0

    call decompose_surface_flux_prod(state, atmos, diag, &
                                     sw_abs, lw_down, lw_up, sh_flux, lh_flux, &
                                     q_net_prod, m_surf_prod)

    q_net_sum = sw_abs + lw_down + lw_up + sh_flux + lh_flux

    print *, ""
    print *, "Case 3: Humid windy (2°C, 80% cloud, 15 m/s)"
    print *, "  SW_abs   = ", sw_abs
    print *, "  LW_down  = ", lw_down
    print *, "  LW_up    = ", lw_up
    print *, "  SH       = ", sh_flux
    print *, "  LH       = ", lh_flux
    print *, "  Sum      = ", q_net_sum
    print *, "  Prod Q   = ", q_net_prod

    n_checks = n_checks + 1
    if (abs(q_net_sum - q_net_prod) .lt. 1e-4) then
        print *, "  OK: Energy balance closes"
    else
        print *, "  FAIL: Balance error = ", q_net_sum - q_net_prod
        n_errors = n_errors + 1
    end if

    ! Test Case 4: Zero net flux -> zero melt
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      90.0, 0.0, 0.0, 0.0)  ! North pole
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 263.15  ! -10°C = T_ICE
    atmos%d2m = 263.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call decompose_surface_flux_prod(state, atmos, diag, &
                                     sw_abs, lw_down, lw_up, sh_flux, lh_flux, &
                                     q_net_prod, m_surf_prod)

    print *, ""
    print *, "Case 4: Polar night, T_air = T_ICE (-10°C)"
    print *, "  Q_net = ", q_net_prod
    print *, "  m_surf = ", m_surf_prod

    n_checks = n_checks + 1
    if (m_surf_prod .eq. 0.0) then
        print *, "  OK: Zero melt for Q_net <= 0"
    else
        print *, "  FAIL: Non-zero melt for Q_net <= 0"
        n_errors = n_errors + 1
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Surface Energy Balance Closure PASSED"
        stop 0
    else
        print *, "FAILURE: Surface Energy Balance Closure FAILED"
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

    ! Replicate production compute_surface_melt logic to extract components
    subroutine decompose_surface_flux_prod(state, atmos, diag, &
                                           sw_abs, lw_down, lw_up, sh_flux, lh_flux, &
                                           q_net, m_surf)
        type(iceberg_state), intent(in) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: sw_abs, lw_down, lw_up, sh_flux, lh_flux
        real, intent(out) :: q_net, m_surf

        real :: t_air_k, t_surf_k, t_dew_k
        real :: p_atm, rho_air_local
        real :: wind_speed
        real :: cz, decl, hour_angle, cos_zenith
        real :: rad_b1, rad_b2, e_vap
        real :: albedo
        real :: lat_rad, dec_rad
        real :: e_sat_air, e_sat_dew, rh
        real :: q_air, q_sat

        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m
        t_surf_k = T_ICE + 273.15

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

        sw_abs = SOLAR_CONSTANT*cos_zenith**2*(1.0 - CLOUD_COEFF*atmos%tcc**3)

        rad_b1 = (cos_zenith + 2.7)*1.0e-5
        rad_b2 = 1.085*cos_zenith + 0.1

        e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
        e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
        rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))
        e_vap = rh*e_sat_air

        sw_abs = sw_abs/(rad_b1*e_vap + rad_b2)

        albedo = ALBEDO_ICE
        sw_abs = sw_abs*(1.0 - albedo)

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
        q_net = sw_abs + lw_down + lw_up + sh_flux + lh_flux

        if (q_net .gt. 0.0) then
            m_surf = q_net/(RHO_ICE*LATENT_HEAT)
        else
            m_surf = 0.0
        end if
    end subroutine decompose_surface_flux_prod

end program iceberg_test_surface_energy_balance
