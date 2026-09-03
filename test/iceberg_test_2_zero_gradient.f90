! ==============================================================================
! Тест: TEST_2 — Zero-gradient environment
! Назначение: Единый холодный океан, нет ветра — айсберг не должен плавиться
!             и не должен дрейфовать (Stage 9.1 validation plan).
! ==============================================================================

program iceberg_test_2_zero_gradient
    use iceberg
    use iceberg_thermodynamics
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: L0, W0, H0
    real :: L_final, W_final, H_final
    real :: pos_x_final, pos_y_final

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_2: Zero-Gradient Environment"
    print *, "=================================================="

    ! Настройка: T <= Tf везде, U=V=0, ветер=0
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Океанский профиль: T = -1.9°C, S = 0.0345, U=V=0
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*250)
        ocean_prof%dz(step) = 250.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! Атмосфера: холодная, без ветра
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15  ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    ! Временная интеграция: 30 дней, dt=1 час
    dt = 3600.0
    nsteps = 24*30  ! 30 дней

    L0 = state%L
    W0 = state%W
    H0 = state%H

    print *, "Initial: L=", L0, " W=", W0, " H=", H0

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) then
            print *, "WARNING: Iceberg melted away at step ", step
            exit
        end if
    end do

    L_final = state%L
    W_final = state%W
    H_final = state%H
    pos_x_final = state%x
    pos_y_final = state%y

    print *, "Final:   L=", L_final, " W=", W_final, " H=", H_final
    print *, "         u=", state%u, " v=", state%v
    print *, "         pos=(", pos_x_final, ",", pos_y_final, ")"

    ! Проверка 1: Геометрия не изменилась (внутри 1 мм)
    n_checks = n_checks + 1
    if (abs(L_final - L0) .lt. 0.001 .and. &
        abs(W_final - W0) .lt. 0.001 .and. &
        abs(H_final - H0) .lt. 0.001) then
        print *, "OK: Geometry unchanged (within 1 mm)"
    else
   print *, "ERROR: Geometry changed: dL=", L_final - L0, " dW=", W_final - W0, " dH=", H_final - H0
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Позиция не изменилась
    n_checks = n_checks + 1
    if (abs(pos_x_final) .lt. 1.0e-6 .and. abs(pos_y_final) .lt. 1.0e-6) then
        print *, "OK: Position unchanged (stationary)"
    else
        print *, "ERROR: Position drifted: x=", pos_x_final, " y=", pos_y_final
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Скорость нулевая
    n_checks = n_checks + 1
    if (abs(state%u) .lt. 1.0e-10 .and. abs(state%v) .lt. 1.0e-10) then
        print *, "OK: Velocity zero"
    else
        print *, "ERROR: Non-zero velocity: u=", state%u, " v=", state%v
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Скорости плавления нулевые
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0 .and. diag%m_lateral .eq. 0.0 .and. diag%m_surface .eq. 0.0) then
        print *, "OK: All melt rates zero"
    else
        print *, "ERROR: Non-zero melt rates: m_b=", diag%m_basal, &
            " m_l=", diag%m_lateral, " m_s=", diag%m_surface
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Масса постоянна
    n_checks = n_checks + 1
    if (abs(diag%mass - 910.0*100.0**3) .lt. 1.0) then
        print *, "OK: Mass conserved"
    else
        print *, "ERROR: Mass changed: ", diag%mass
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_2 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_2 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_2_zero_gradient
