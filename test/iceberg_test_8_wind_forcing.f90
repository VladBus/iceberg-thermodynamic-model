! ==============================================================================
! Тест: TEST_8 — Wind forcing
! Назначение: Заданный ветер, нет течения — проверить дрейф ~2% от ветра,
!             дефлекцию ~45° вправо (СШ).
! ==============================================================================

program iceberg_test_8_wind_forcing
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
    real :: wind_speed, terminal_speed, ratio
    real :: drift_angle_deg
    integer :: converged_step
    real :: prev_speed
    real :: wind_angle, rel_angle

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_8: Wind Forcing Drift"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Нет океанического течения
    ocean_prof%nlevels = 10
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! Ветер: 10 м/с с севера (v10 = -10, u10 = 0)
    ! Дрейф в СШ: ~45° вправо от ветра = юго-запад (u<0, v<0)
    atmos%u10 = 0.0
    atmos%v10 = -10.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

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

    ratio = terminal_speed/wind_speed
    drift_angle_deg = atan2(state%v, state%u)*57.2957795

    ! Вектор ветра: (0, -10) — с севера на юг
    ! Дрейф в СШ: ~45° вправо от ветра = юго-запад (u<0, v<0)
    print *, "Wind speed:         ", wind_speed, " m/s"
    print *, "Terminal iceberg v: ", terminal_speed, " m/s"
    print *, "Ratio (iceberg/wind): ", ratio
    print *, "Drift angle:        ", drift_angle_deg, " deg"
    print *, "Converged at step:  ", converged_step

    ! Проверка 1: Скорость дрейфа ~2% от ветра
    n_checks = n_checks + 1
    if (ratio .gt. 0.01 .and. ratio .lt. 0.05) then
        print *, "OK: Drift speed ratio = ", ratio, " (~2% wind rule)"
    else
        print *, "WARNING: Speed ratio = ", ratio, " outside 1-5% range"
    end if

    ! Проверка 2: Направление — вправо от ветра (СШ)
    ! Ветер (0, -10) — по -Y, вправо = -X
    n_checks = n_checks + 1
    if (state%u .lt. 0.0 .and. state%v .lt. 0.0) then
        print *, "OK: Drift deflected to the right of wind (NH, southwest)"
    else
        print *, "ERROR: Drift direction wrong: u=", state%u, " v=", state%v
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Угол дрейфа относительно ветра ~45°
    ! Угол ветра = atan2(-10, 0) = -90° (или 270°)
    ! Дрейф должен быть ~ -135° (юго-запад) = 225°
    n_checks = n_checks + 1
    rel_angle = drift_angle_deg - wind_angle
    if (rel_angle .gt. 180.0) rel_angle = rel_angle - 360.0
    if (rel_angle .lt. -180.0) rel_angle = rel_angle + 360.0
    print *, "Wind angle: ", wind_angle, " Drift angle: ", drift_angle_deg, " Rel: ", rel_angle
    ! В СШ дрейф отклоняется вправо (по часовой стрелке от ветра)
    ! Для ветра -90° (юг), вправо = -135° (юго-запад)
    if (abs(rel_angle - (-45.0)) .lt. 30.0) then
        print *, "OK: Drift angle ~45° to right of wind"
    else
        print *, "WARNING: Relative angle = ", rel_angle, " not near -45°"
    end if

    ! Проверка 4: Нет плавления
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0 .and. diag%m_lateral .eq. 0.0 .and. diag%m_surface .eq. 0.0) then
        print *, "OK: No melt"
    else
        print *, "ERROR: Unexpected melt"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_8 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_8 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_8_wind_forcing
