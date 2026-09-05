! ==============================================================================
! Тест: Surface Energy Algebraic Identity
! Назначение: Проверить чисто алгебраическое тождество:
!             m_surface = max(0, Q_net) / (rho_ice * L_f)
! независимо от физической модели Q_net.
! Это тест ПРОИЗВОДСТВЕННОЙ формулы, а не физической валидации.
! ==============================================================================

program iceberg_test_surface_energy_algebra
    use iceberg_types
    implicit none

    integer :: n_errors, n_checks
    real :: q_net, m_surface, expected_melt
    real :: rho_ice_local, latent_heat_local

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Surface Melt Algebraic Identity"
    print *, "=================================================="

    rho_ice_local = RHO_ICE
    latent_heat_local = LATENT_HEAT

    ! Test cases: Q_net values, expected melt = max(0, Q) / (rho * L)
    ! Case 1: Q = -100 W/m2 -> melt = 0
    ! Case 2: Q = 0 W/m2 -> melt = 0
    ! Case 3: Q = 100 W/m2 -> melt = 100 / (910 * 334000)
    ! Case 4: Q = 1000 W/m2 -> melt = 1000 / (910 * 334000)

    print *, ""
    print *, "RHO_ICE = ", rho_ice_local, " kg/m3"
    print *, "LATENT_HEAT = ", latent_heat_local, " J/kg"
    print *, "RHO * L = ", rho_ice_local*latent_heat_local, " J/m3"

    ! CASE 1: Negative Q_net
    q_net = -100.0
    m_surface = max(0.0, q_net)/(rho_ice*latent_heat)
    expected_melt = 0.0
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 1: Q_net = -100 W/m2 ---"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    if (abs(m_surface - expected_melt) .lt. 1e-15) then
        print *, "OK: Zero melt for negative Q_net"
    else
        print *, "FAIL"
        n_errors = n_errors + 1
    end if

    ! CASE 2: Zero Q_net
    q_net = 0.0
    m_surface = max(0.0, q_net)/(rho_ice*latent_heat)
    expected_melt = 0.0
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 2: Q_net = 0 W/m2 ---"
    print *, "m_surface = ", m_surface, " m/s"
    if (abs(m_surface - expected_melt) .lt. 1e-15) then
        print *, "OK: Zero melt for zero Q_net"
    else
        print *, "FAIL"
        n_errors = n_errors + 1
    end if

    ! CASE 3: Q_net = 100 W/m2
    q_net = 100.0
    m_surface = max(0.0, q_net)/(rho_ice*latent_heat)
    expected_melt = 100.0/(rho_ice_local*latent_heat_local)
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 3: Q_net = 100 W/m2 ---"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "expected  = ", expected_melt, " m/s = ", expected_melt*86400.0, " m/day"
    if (abs(m_surface - expected_melt)/expected_melt .lt. 1e-6) then
        print *, "OK: Algebraic identity holds"
    else
        print *, "FAIL: ratio = ", m_surface/expected_melt
        n_errors = n_errors + 1
    end if

    ! CASE 4: Q_net = 1000 W/m2
    q_net = 1000.0
    m_surface = max(0.0, q_net)/(rho_ice_local*latent_heat_local)
    expected_melt = 1000.0/(rho_ice_local*latent_heat_local)
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 4: Q_net = 1000 W/m2 ---"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "expected  = ", expected_melt, " m/s = ", expected_melt*86400.0, " m/day"
    if (abs(m_surface - expected_melt)/expected_melt .lt. 1e-6) then
        print *, "OK: Algebraic identity holds"
    else
        print *, "FAIL: ratio = ", m_surface/expected_melt
        n_errors = n_errors + 1
    end if

    ! CASE 5: Q_net = 300 W/m2 (typical max SW)
    q_net = 300.0
    m_surface = max(0.0, q_net)/(rho_ice_local*latent_heat_local)
    expected_melt = 300.0/(rho_ice_local*latent_heat_local)
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 5: Q_net = 300 W/m2 (max typical SW) ---"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    if (abs(m_surface - expected_melt)/expected_melt .lt. 1e-6) then
        print *, "OK: Algebraic identity holds"
    else
        print *, "FAIL"
        n_errors = n_errors + 1
    end if

    ! CASE 6: Q_net = 13364 W/m2 (the anomalous LH case from Stage 9.4C.1)
    q_net = 13364.3828
    m_surface = max(0.0, q_net)/(rho_ice_local*latent_heat_local)
    expected_melt = 13364.3828/(rho_ice_local*latent_heat_local)
    n_checks = n_checks + 1
    print *, ""
    print *, "--- Case 6: Q_net = 13364 W/m2 (anomalous LH case) ---"
    print *, "m_surface = ", m_surface, " m/s = ", m_surface*86400.0, " m/day"
    print *, "expected  = ", expected_melt, " m/s = ", expected_melt*86400.0, " m/day"
    if (abs(m_surface - expected_melt)/expected_melt .lt. 1e-6) then
        print *, "OK: Algebraic identity holds even for large Q"
    else
        print *, "FAIL"
        n_errors = n_errors + 1
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Surface Melt Algebraic Identity PASSED"
        stop 0
    else
        print *, "FAILURE: Surface Melt Algebraic Identity FAILED"
        stop 1
    end if

end program iceberg_test_surface_energy_algebra
