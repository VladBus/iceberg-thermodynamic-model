! ==============================================================================
! Тест: TEST_7 — Vertical temperature gradient
! Назначение: Сильный вертикальный градиент T(z) — проверить, что боковое
!             плавление концентрируется в тёплых слоях, базальное — на глубине осадки.
! ==============================================================================

program iceberg_test_7_vertical_temp_gradient
    use iceberg
    use iceberg_thermodynamics
    use iceberg_forcing, only: depth_averaged_thermal_forcing, interp_at_draft
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: delta_t_avg, t_draft, s_draft, tf_draft, delta_t_basal

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_7: Vertical Temperature Gradient"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Профиль: 5°C на поверхности, -1.5°C на 100м
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        if (ocean_prof%z(step) .le. 100.0) then
            ocean_prof%temp(step) = 5.0 - 6.5*ocean_prof%z(step)/100.0
        else
            ocean_prof%temp(step) = -1.5
        end if
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! Debug: print ocean profile
    print *, "Ocean profile (z, temp):"
    do step = 1, ocean_prof%nlevels
        print '(I3, 2F10.3)', step, ocean_prof%z(step), ocean_prof%temp(step)
    end do

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 10

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) exit
    end do

    print *, "Draft: ", diag%draft, " m"
    print *, "T at draft: ", diag%t_draft, " °C"
    print *, "S at draft: ", diag%s_draft
    print *, "Tf at draft: ", diag%tf_draft, " °C"
    print *, "Basal melt rate: ", diag%m_basal*86400, " m/day"
    print *, "Lateral melt rate: ", diag%m_lateral*86400, " m/day"
    print *, "Surface melt rate: ", diag%m_surface*86400, " m/day"

    ! Проверка 1: Базальное плавление >= 0
    n_checks = n_checks + 1
    if (diag%m_basal .ge. 0.0) then
        print *, "OK: Basal melt >= 0"
    else
        print *, "ERROR: Basal melt negative"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Боковое плавление > 0
    n_checks = n_checks + 1
    if (diag%m_lateral .gt. 0.0) then
        print *, "OK: Lateral melt > 0 (warm upper layers contribute)"
    else
        print *, "ERROR: Lateral melt = 0 (should be > 0 due to warm surface)"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Поверхностное плавление = 0
    n_checks = n_checks + 1
    if (diag%m_surface .eq. 0.0) then
        print *, "OK: Surface melt = 0"
    else
        print *, "WARNING: Surface melt > 0"
    end if

    ! Проверка 4: Глубинно-средний избыток температуры > 0
    n_checks = n_checks + 1
    delta_t_avg = depth_averaged_thermal_forcing(ocean_prof, diag%draft)
    if (delta_t_avg .gt. 0.0) then
        print *, "OK: Depth-averaged thermal forcing > 0: ", delta_t_avg, " °C"
    else
        print *, "ERROR: Depth-averaged thermal forcing <= 0"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Базальное плавление использует T именно на глубине осадки
    n_checks = n_checks + 1
    t_draft = interp_at_draft(ocean_prof, diag%draft, "temp")
    s_draft = interp_at_draft(ocean_prof, diag%draft, "salt")
    tf_draft = -54.0*s_draft
    delta_t_basal = t_draft - tf_draft
    if (abs(diag%t_draft - t_draft) .lt. 1.0e-6 .an &
        d. abs(diag%tf_draft - tf_draft) .lt. 1.0e-6) then
        print *, "OK: Basal melt uses T at draft depth correctly"
        print *, "  T(draft)=", t_draft, " Tf(draft)=", tf_draft, " ΔT=", delta_t_basal
    else
        print *, "ERROR: Basal melt interpolation mismatch"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_7 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_7 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_7_vertical_temp_gradient
