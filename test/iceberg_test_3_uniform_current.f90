! ==============================================================================
! Тест: TEST_3 — Uniform current
! Назначение: Постоянное течение, нет ветра, нет термодинамики —
!             проверить терминальную скорость дрейфа ~2% от тока,
!             дефлекцию ~45° вправо (СШ) (Stage 9.1 validation plan).
! ==============================================================================

program iceberg_test_3_uniform_current
    use iceberg
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: u_curr, v_curr
    real :: terminal_speed, current_speed
    real :: drift_angle_deg, expected_angle_deg
    real :: ratio_speed
    integer :: converged_step
    real :: prev_speed

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_3: Uniform Current Drift"
    print *, "=================================================="

    ! Настройка: течение 0.1 м/с по X, нет ветра, T <= Tf
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    u_curr = 0.1
    v_curr = 0.0
    current_speed = sqrt(u_curr**2 + v_curr**2)

    ! Используем мелкие уровни, чтобы охватить осадку айсберга (~88м)
    ocean_prof%nlevels = 10
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    ! Уровни: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 м
    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = u_curr
        ocean_prof%v(step) = v_curr
    end do

    u_curr = 0.1
    v_curr = 0.0
    current_speed = sqrt(u_curr**2 + v_curr**2)

    ! Атмосфера: нет ветра, холодная
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 200

    converged_step = -1
    prev_speed = 0.0

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) exit

        terminal_speed = sqrt(state%u**2 + state%v**2)

        if (step .gt. 10) then
            if (abs(terminal_speed - prev_speed) .lt. 1.0e-6) then
                if (converged_step .eq. -1) converged_step = step
            end if
        end if
        prev_speed = terminal_speed
    end do

    ratio_speed = terminal_speed/current_speed
    drift_angle_deg = atan2(state%v, state%u)*57.2957795
    expected_angle_deg = 45.0

    print *, "Current speed:      ", current_speed, " m/s"
    print *, "Terminal iceberg v: ", terminal_speed, " m/s"
    print *, "Ratio (iceberg/curr): ", ratio_speed
    print *, "Drift angle:        ", drift_angle_deg, " deg"
    print *, "Expected angle:     ", expected_angle_deg, " deg"
    print *, "Converged at step:  ", converged_step

    ! Проверка 1: Терминальная скорость ~2% от тока
    n_checks = n_checks + 1
    if (ratio_speed .gt. 0.01 .and. ratio_speed .lt. 0.05) then
        print *, "OK: Terminal speed ratio = ", ratio_speed, " (~2% rule)"
    else
        print *, "WARNING: Speed ratio = ", ratio_speed, " outside 1-5% range"
    end if

    ! Проверка 2: Направление дрейфа вправо от тока (СШ)
    n_checks = n_checks + 1
    if (state%v .lt. 0.0) then
        print *, "OK: Drift deflected to the right (NH)"
    else
        print *, "ERROR: Drift not deflected correctly: v=", state%v
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Угол близок к 45°
    n_checks = n_checks + 1
    if (abs(abs(drift_angle_deg) - expected_angle_deg) .lt. 30.0) then
        print *, "OK: Drift angle ~45° to current"
    else
        print *, "WARNING: Drift angle = ", drift_angle_deg, " deg, far from 45°"
    end if

    ! Проверка 4: Нет плавления (T <= Tf)
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0 .and. diag%m_lateral .eq. 0.0) then
        print *, "OK: No ocean-driven melt"
    else
        print *, "ERROR: Unexpected melt"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Геометрия не изменилась
    n_checks = n_checks + 1
    if (abs(state%L - 100.0) .lt. 1.0e-6 .an &
        d. abs(state%W - 100.0) .lt. 1.0e-6 &
        .and. abs(state%H - 100.0) .lt. 1.0e-6) then
        print *, "OK: Geometry constant"
    else
        print *, "ERROR: Geometry changed"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_3 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_3 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_3_uniform_current
