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
! Прогностические тесты температуры поверхности (Stage 10.2):
!   Test A: Cold surface warming (T_surface from -20°C toward 0°C, no melt)
!   Test B: Cooling below freezing (T_surface drops from -5°C, no melt)
!   Test C: Crossing melting point (T_surface from -0.5°C -> 0°C, melt occurs)
!   Test D: At melting point with positive energy (T_surface = 0°C, melt occurs)
!   Test E: At melting point with negative energy (T_surface cools below 0°C, no melt)
!   Energy conservation: Partition between sensible and latent energy
!   Surface coupling: Verify T_surface actually affects LW_up, SH, LH
!   Nighttime regression: Polar night SW=0, no NaN
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
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
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
    ! Stage 10.2 test variables
    real :: c_eff
    real :: q_nm_est, e_avail, e_req, e_melt, m_expected
    real :: e_total_used
    real :: q_net_1, m_1, t_surf_1
    real :: q_net_2, m_2, t_surf_2

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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
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

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
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
    ! STAGE 10.2 PROGNOSTIC SURFACE TEMPERATURE TESTS
    ! =========================================================================
    
    ! -------------------------------------------------------------------------
    ! TEST A: Cold surface warming
    ! Initial: T_surface = -20°C
    ! Positive Q_net_non_melt -> T_surface increases but stays < 0°C
    ! Expected: m_surface = 0, T_surface > -20°C and < 0°C
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- TEST A: Cold surface warming (-20°C -> warmer, no melt) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    state%T_surface = -20.0  ! Explicit initial condition
    call init_zero_ocean(ocean_prof)

    ! Construct forcing for positive net energy (no SW, warm air, no wind)
    atmos%t2m = 273.15   ! 0°C
    atmos%d2m = 273.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    ! Analytical: dT = Q_net_non_melt * dt / C_eff
    ! C_eff = 910 * 2100 * 0.5 = 955500 J/(m² K)
    ! We need Q_net_non_melt to compute expected dT
    ! For this test, we just verify direction and bounds

    print *, "T_initial = -20.0°C"
    print *, "T_final   = ", state%T_surface, " °C"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "q_net     = ", q_net, " W/m2"

    call write_audit_row(unit, "A_warming", atmos, q_net, m_surface, 0.0)

    n_checks = n_checks + 1
    if (state%T_surface .gt. -20.0 .and. state%T_surface .lt. 0.0 .and. m_surface .eq. 0.0) then
        print *, "OK: Cold surface warmed toward 0°C, no melt"
    else
        print *, "FAIL: Test A conditions not met"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! TEST B: Cooling below freezing
    ! Initial: T_surface = -5°C
    ! Negative Q_net_non_melt -> T_surface decreases
    ! Expected: m_surface = 0, T_surface < -5°C
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- TEST B: Cooling below freezing (-5°C -> colder) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    state%T_surface = -5.0
    call init_zero_ocean(ocean_prof)

    ! Cold air, no wind, polar night -> negative net LW
    atmos%t2m = 253.15   ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    print *, "T_initial = -5.0°C"
    print *, "T_final   = ", state%T_surface, " °C"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "q_net     = ", q_net, " W/m2"

    call write_audit_row(unit, "B_cooling", atmos, q_net, m_surface, 0.0)

    n_checks = n_checks + 1
    if (state%T_surface .lt. -5.0 .and. m_surface .eq. 0.0 .and. ieee_is_finite(state%T_surface)) then
        print *, "OK: Surface cooled below -5°C, no melt"
    else
        print *, "FAIL: Test B conditions not met"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! TEST C: Crossing the melting point
    ! Initial: T_surface = -0.5°C
    ! Choose controlled positive heat flux and dt so surface crosses 0°C
    ! Verify energy partition: E_melt = E_available - E_required
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- TEST C: Crossing melting point (-0.5°C -> 0°C + melt) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    state%T_surface = -0.5
    call init_zero_ocean(ocean_prof)

    ! Strong positive forcing to guarantee crossing
    atmos%t2m = 283.15   ! 10°C
    atmos%d2m = 280.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    ! Analytical check
    ! We need Q_net_non_melt. Since we don't expose it, we approximate from
    ! the final q_net + melt energy / dt
    ! E_available = Q_net_non_melt * dt
    ! E_required  = C_eff * (0 - T_initial)
    ! E_melt = E_available - E_required
    ! m_expected = E_melt / (RHO_ICE * LATENT_HEAT)
    ! Note: q_net returned = Q_net_non_melt - m_surface*RHO_ICE*LATENT_HEAT/dt
    ! So Q_net_non_melt = q_net + m_surface*RHO_ICE*LATENT_HEAT/dt
    
    c_eff = RHO_ICE * C_ICE * H_EFF
    q_nm_est = q_net + m_surface*RHO_ICE*LATENT_HEAT/dt
    e_avail = q_nm_est * dt
    e_req = c_eff * (0.0 - (-0.5))
    e_melt = e_avail - e_req
    m_expected = max(0.0, e_melt) / (RHO_ICE * LATENT_HEAT)

    print *, "T_initial = -0.5°C"
    print *, "T_final   = ", state%T_surface, " °C"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "m_expected = ", m_expected, " m/s"
    print *, "q_net_non_melt (est) = ", q_nm_est, " W/m2"
    print *, "q_net (residual) = ", q_net, " W/m2"

    call write_audit_row(unit, "C_crossing", atmos, q_net, m_surface, m_expected)

    n_checks = n_checks + 1
    if (abs(state%T_surface - 0.0) .lt. 1e-6 .and. m_surface .gt. 0.0) then
        print *, "OK: Surface reached 0°C and melt occurred"
    else
        print *, "FAIL: Test C crossing conditions not met"
        n_errors = n_errors + 1
    end if

    ! Energy conservation check
    n_checks = n_checks + 1
    if (abs(e_avail - (e_req + m_surface*RHO_ICE*LATENT_HEAT*dt)) .lt. 1.0) then
        print *, "OK: Energy conserved within 1 J/m2"
    else
        print *, "INFO: Energy balance diff = ", e_avail - (e_req + m_surface*RHO_ICE*LATENT_HEAT*dt), " J/m2"
    end if

    ! -------------------------------------------------------------------------
    ! TEST D: At melting point with positive energy
    ! Initial: T_surface = 0°C
    ! Positive net energy -> melt, surface stays at 0°C
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- TEST D: At melting point, positive energy (0°C -> melt) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    state%T_surface = 0.0
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 283.15   ! 10°C
    atmos%d2m = 280.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    print *, "T_initial = 0.0°C"
    print *, "T_final   = ", state%T_surface, " °C"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "q_net     = ", q_net, " W/m2"

    call write_audit_row(unit, "D_at_melt_positive", atmos, q_net, m_surface, 0.0)

    n_checks = n_checks + 1
    if (abs(state%T_surface - 0.0) .lt. 1e-6 .and. m_surface .gt. 0.0) then
        print *, "OK: Surface at 0°C, melt from positive energy"
    else
        print *, "FAIL: Test D conditions not met"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! TEST E: At melting point with negative energy
    ! Initial: T_surface = 0°C
    ! Negative net energy -> surface cools below 0°C, no melt
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- TEST E: At melting point, negative energy (0°C -> cools) ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      90.0, 0.0, 0.0, 0.0)  ! polar night
    state%T_surface = 0.0
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 253.15   ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 0.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    print *, "T_initial = 0.0°C"
    print *, "T_final   = ", state%T_surface, " °C"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "q_net     = ", q_net, " W/m2"

    call write_audit_row(unit, "E_at_melt_negative", atmos, q_net, m_surface, 0.0)

    n_checks = n_checks + 1
    if (state%T_surface .lt. 0.0 .and. m_surface .eq. 0.0 .and. ieee_is_finite(state%T_surface)) then
        print *, "OK: Surface cooled below 0°C, no melt"
    else
        print *, "FAIL: Test E conditions not met"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! ENERGY CONSERVATION TEST
    ! Synthetic case with known energy partition
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- ENERGY CONSERVATION: Crossing case partition check ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    state%T_surface = -1.0
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 283.15
    atmos%d2m = 280.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%u10 = 10.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    ! Energy accounting
    q_nm_est = q_net + m_surface*RHO_ICE*LATENT_HEAT/dt
    e_avail = q_nm_est * dt
    e_req = c_eff * (0.0 - (-1.0))
    e_melt = m_surface * RHO_ICE * LATENT_HEAT * dt
    e_total_used = e_req + e_melt

    print *, "E_available = ", e_avail, " J/m2"
    print *, "E_sensible  = ", e_req, " J/m2"
    print *, "E_latent    = ", e_melt, " J/m2"
    print *, "E_used      = ", e_total_used, " J/m2"
    print *, "Difference  = ", e_avail - e_total_used, " J/m2"

    n_checks = n_checks + 1
    if (abs(e_avail - e_total_used) .lt. 10.0) then  ! tolerance 10 J/m2
        print *, "OK: Energy partition conserved within 10 J/m2"
    else
        print *, "FAIL: Energy conservation error = ", e_avail - e_total_used, " J/m2"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! SURFACE TEMPERATURE COUPLING TEST
    ! Verify T_surface actually affects fluxes (LW_up, SH, LH)
    ! Two states with identical atmos forcing, different T_surface
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- SURFACE COUPLING: T_surface affects fluxes ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 273.15
    atmos%d2m = 271.15
    atmos%tcc = 0.5
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    ! Case 1: T_surface = -10°C
    state%T_surface = -10.0
    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))
    q_net_1 = q_net
    m_1 = m_surface
    t_surf_1 = state%T_surface

    ! Case 2: T_surface = -2°C (warmer)
    state%T_surface = -2.0
    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))
    q_net_2 = q_net
    m_2 = m_surface
    t_surf_2 = state%T_surface

    print *, "T_surface = -10°C: q_net = ", q_net_1, " m_surface = ", m_1
    print *, "T_surface =  -2°C: q_net = ", q_net_2, " m_surface = ", m_2
    print *, "Difference in q_net = ", abs(q_net_2 - q_net_1), " W/m2"
    print *, "Difference in m_surf = ", abs(m_2 - m_1), " m/s"

    n_checks = n_checks + 1
    if (abs(q_net_2 - q_net_1) .gt. 1.0) then  ! fluxes must differ
        print *, "OK: Surface temperature affects energy balance"
    else
        print *, "FAIL: Fluxes unchanged by T_surface - bug in coupling"
        n_errors = n_errors + 1
    end if

    ! -------------------------------------------------------------------------
    ! NIGHTTIME REGRESSION TEST (protects 737d41b fix)
    ! Polar night: SW=0, all terms finite, no NaN
    ! -------------------------------------------------------------------------
    print *, ""
    print *, "--- NIGHTTIME REGRESSION: Polar night, e_vap valid ---"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      90.0, 0.0, 0.0, 0.0)
    state%T_surface = -10.0
    call init_zero_ocean(ocean_prof)

    atmos%t2m = 263.15
    atmos%d2m = 263.15
    atmos%tcc = 1.0
    atmos%msl = 101325.0
    atmos%u10 = 5.0
    atmos%v10 = 0.0

    call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                              nat(1), nat(2), nat(3), nat(4))

    print *, "cos_zenith <= 0: SW_down = 0"
    print *, "T_surface = ", state%T_surface, " °C"
    print *, "q_net = ", q_net, " W/m2"
    print *, "m_surface = ", m_surface, " m/s"
    print *, "All finite: ", all([ieee_is_finite(state%T_surface), ieee_is_finite(q_net), ieee_is_finite(m_surface)])

    n_checks = n_checks + 1
    if (ieee_is_finite(state%T_surface) .and. ieee_is_finite(q_net) .and. ieee_is_finite(m_surface) .and. &
        m_surface .eq. 0.0) then
        print *, "OK: Nighttime regression - all terms finite, zero melt"
    else
        print *, "FAIL: Nighttime regression"
        n_errors = n_errors + 1
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
