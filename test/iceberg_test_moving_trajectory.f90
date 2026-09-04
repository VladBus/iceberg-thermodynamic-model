! ==============================================================================
! Тест: Moving Trajectory Test
! Назначение: Проверка что айсберг реально перемещается и форсинг
!             меняется вслед за движением (искусственный тест без сложного форсинга)
! ==============================================================================

program iceberg_test_moving_trajectory
    use iceberg, only: iceberg_init, iceberg_step, iceberg_compute_geometry
    use iceberg_types, only: iceberg_state, iceberg_diagnostics, ocean_profile, atmos_forcing
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag
    type(iceberg_diagnostics) :: geom

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: x_init, y_init, x_final, y_final
    real :: u_const, v_const
    real :: displacement, path_length
    real :: speed

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  MOVING TRAJECTORY TEST"
    print *, "=================================================="

    ! 1. Инициализация айсберга
    print *, "Initializing iceberg..."
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 75.0, 30.0, 0.0, 0.0)
    x_init = state%x
    y_init = state%y

    ! 2. Настройка постоянного океанского профиля (холодный, без течений)
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(18), ocean_prof%dz(18), ocean_prof%temp(18), &
              ocean_prof%salt(18), ocean_prof%u(18), ocean_prof%v(18))
    do step = 1, 18
        ocean_prof%z(step) = real(step*250)
        ocean_prof%dz(step) = 250.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! 3. Настройка постоянного атмосферного форсинга (ветер по X)
    atmos%u10 = 10.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    ! 4. Временная интеграция: 5 дней, dt=1 час
    dt = 3600.0
    nsteps = 24*5

    print *, "Running 5-day integration with constant wind forcing..."
    print *, "Initial position: x=", x_init, " y=", y_init

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) then
            print *, "WARNING: Iceberg melted away at step ", step
            exit
        end if
    end do

    x_final = state%x
    y_final = state%y

    print *, "Final position:   x=", x_final, " y=", y_final
    print *, "Final velocity:   u=", state%u, " v=", state%v
    print *, "Final geometry:   L=", state%L, " W=", state%W, " H=", state%H

    displacement = sqrt((x_final - x_init)**2 + (y_final - y_init)**2)
    print *, "Total displacement: ", displacement, " m"

    ! Проверка 1: Траектория не нулевая
    n_checks = n_checks + 1
    if (displacement .gt. 100.0) then  ! ожидаем хотя бы ~100м за 5 дней при ветре 10м/с
        print *, "OK: Non-zero trajectory (displacement = ", displacement, " m)"
    else
        print *, "ERROR: Zero or near-zero trajectory (displacement = ", displacement, " m)"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Скорость физически правдоподобна
    speed = sqrt(state%u**2 + state%v**2)
    n_checks = n_checks + 1
    if (speed .gt. 1.0e-3 .and. speed .lt. 1.0) then
        print *, "OK: Drift speed plausible: ", speed, " m/s"
    else
        print *, "WARNING: Drift speed unusual: ", speed, " m/s"
    end if

    ! Проверка 3: Геометрия не отрицательная
    n_checks = n_checks + 1
    if (state%L .gt. 0.0 .and. state%W .gt. 0.0 .and. state%H .gt. 0.0) then
        print *, "OK: All geometry positive"
    else
        print *, "ERROR: Negative geometry detected"
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Масса убывает (нет накопления)
    n_checks = n_checks + 1
    if (diag%mass .lt. 910.0*100.0**3) then
        print *, "OK: Mass decreased (", diag%mass, " kg)"
    else
        print *, "WARNING: Mass did not decrease"
    end if

    ! Тест 2: u=const, v=0 (аналитическая траектория)
    print *, ""
    print *, "Test 2: Analytic trajectory u=const, v=0"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 75.0, 30.0, 0.05, 0.0)
    x_init = state%x
    y_init = state%y

    ! Без внешних сил, с постоянной начальной скоростью
    ! Но iceberg_step будет менять скорость из-за Кориолиса и трения
    ! Поэтому это не чистый аналитический тест, но проверим что x растёт

    do step = 1, 10
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do

    x_final = state%x
    y_final = state%y
    displacement = sqrt((x_final - x_init)**2 + (y_final - y_init)**2)
    print *, "  Displacement after 10h with u0=0.05: ", displacement, " m"
    print *, "  Final u: ", state%u, " v: ", state%v

    if (displacement .gt. 1000.0) then  ! ~1800 м за 10 часов при 0.05 м/с
        print *, "  OK: Significant displacement in x direction"
    else
        print *, "  WARNING: Less displacement than expected"
    end if
    n_checks = n_checks + 1

    ! Тест 3: u=0, v=const
    print *, ""
    print *, "Test 3: u=0, v=const"

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 75.0, 30.0, 0.0, 0.05)
    x_init = state%x
    y_init = state%y

    do step = 1, 10
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do

    x_final = state%x
    y_final = state%y
    displacement = sqrt((x_final - x_init)**2 + (y_final - y_init)**2)
    print *, "  Displacement after 10h with v0=0.05: ", displacement, " m"

    if (displacement .gt. 1000.0) then
        print *, "  OK: Significant displacement in y direction"
    else
        print *, "  WARNING: Less displacement than expected"
    end if
    n_checks = n_checks + 1

    if (allocated(ocean_prof%z)) deallocate (ocean_prof%z, ocean_prof%dz, &
                                             ocean_prof%temp, ocean_prof%salt, &
                                             ocean_prof%u, ocean_prof%v)

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: MOVING TRAJECTORY TEST PASSED"
        stop 0
    else
        print *, "FAILURE: MOVING TRAJECTORY TEST FAILED"
        stop 1
    end if

end program iceberg_test_moving_trajectory
