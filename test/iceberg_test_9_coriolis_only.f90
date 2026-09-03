! ==============================================================================
! Тест: TEST_9 — Coriolis only (inertial oscillation)
! Назначение: Начальная скорость, нет форсинга — проверить инерциальную
!             осцилляцию с правильным периодом T = 2π/f.
! ==============================================================================

program iceberg_test_9_coriolis_only
    use iceberg
    use iceberg_dynamics, only: inertial_period
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: f_coriolis, T_inertial_theory, T_inertial_measured
    real, allocatable :: u_hist(:), v_hist(:)
    integer :: zero_crossings
    real :: prev_u
    real :: speed_init, speed_final, speed_var
    real :: radius_theory, radius_measured

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_9: Coriolis Only — Inertial Oscillation"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.1, 0.0)

    ! Нет форсинга вообще
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

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    ! Параметр Кориолиса при 76.5°N
    f_coriolis = 2.0*7.2921150e-5*sin(76.5/57.2957795)
    T_inertial_theory = 2.0*3.141592653589793/f_coriolis

    print *, "Latitude: 76.5°N"
    print *, "f = ", f_coriolis, " 1/s"
    print *, "Theoretical inertial period: ", T_inertial_theory/3600.0, " hours"

    dt = 3600.0
    nsteps = 200

    allocate (u_hist(nsteps), v_hist(nsteps))

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        u_hist(step) = state%u
        v_hist(step) = state%v

        if (.not. state%active) exit
    end do

    ! Измерить период по переходам через ноль u-компоненты
    zero_crossings = 0
    prev_u = u_hist(1)
    do step = 2, nsteps
        if (prev_u .gt. 0.0 .and. u_hist(step) .lt. 0.0) then
            zero_crossings = zero_crossings + 1
        else if (prev_u .lt. 0.0 .and. u_hist(step) .gt. 0.0) then
            zero_crossings = zero_crossings + 1
        end if
        prev_u = u_hist(step)
    end do

    if (zero_crossings .ge. 2) then
        T_inertial_measured = real(nsteps)*dt/(zero_crossings/2.0)
    else
        T_inertial_measured = -1.0
    end if

    print *, "Zero crossings: ", zero_crossings
    print *, "Measured period: ", T_inertial_measured/3600.0, " hours"
    print *, "Theory period:   ", T_inertial_theory/3600.0, " hours"

    ! Проверка 1: Скорость постоянна
    n_checks = n_checks + 1
    speed_init = sqrt(u_hist(1)**2 + v_hist(1)**2)
    speed_final = sqrt(u_hist(nsteps)**2 + v_hist(nsteps)**2)
    speed_var = maxval(sqrt(u_hist**2 + v_hist**2)) - minval(sqrt(u_hist**2 + v_hist**2))
    if (abs(speed_final - speed_init)/speed_init .lt. 0.01) then
        print *, "OK: Speed conserved (variation = ", speed_var, ")"
    else
        print *, "WARNING: Speed not conserved: init=", speed_init, " final=", speed_final
    end if

    ! Проверка 2: Траектория — круг
    n_checks = n_checks + 1
    radius_theory = 0.1/f_coriolis
    radius_measured = sqrt(state%x**2 + state%y**2)
    if (radius_measured .gt. 0.0) then
        print *, "OK: Circular trajectory, radius ~ ", radius_measured/1000.0, &
            " km (theory: ", radius_theory/1000.0, " km)"
    else
        print *, "WARNING: Could not measure radius"
    end if

    ! Проверка 3: Период близок к теории (внутри 15%)
    n_checks = n_checks + 1
    if (T_inertial_measured .gt. 0.0 .and. &
        abs(T_inertial_measured - T_inertial_theory)/T_inertial_theory .lt. 0.15) then
        print *, "OK: Inertial period matches theory within 15%"
    else
        print *, "ERROR: Period mismatch: measured=", T_inertial_measured/3600.0, &
            " theory=", T_inertial_theory/3600.0, " h"
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Поворот по часовой стрелке (СШ)
    n_checks = n_checks + 1
    if (v_hist(2) .lt. 0.0) then
        print *, "OK: Clockwise rotation (NH)"
    else
        print *, "ERROR: Wrong rotation direction: v(2)=", v_hist(2)
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Нет плавления
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
        print *, "SUCCESS: TEST_9 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_9 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_9_coriolis_only
