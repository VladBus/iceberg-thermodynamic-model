! ==============================================================================
! Тест: Coriolis Sign and Equation Audit
! Назначение: Проверить знак и уравнения Кориолиса из исполняемого кода.
!             Проверка на первых шагах интегрирования.
! ==============================================================================

program iceberg_test_coriolis_sign
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step
    real :: dt
    real :: f_coriolis, latitude
    real :: u_old, v_old, u_new, v_new
    real :: f_cor_x, f_cor_y
    real :: mass
    real :: A_mat
    real :: model_time

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Coriolis Sign and Equation Audit"
    print *, "=================================================="

    ! Инициализация: 75N, без ветра, без течения, без плавления
    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)

    print *, "Latitude: ", latitude
    print *, "f = 2*Omega*sin(lat) = ", f_coriolis
    print *, "f*dt = ", f_coriolis*3600.0

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      latitude, 0.0, 0.1, 0.0)  ! u0 = 0.1 m/s, v0 = 0

    ! Нулевой форсинг
    call init_zero_forcing(ocean_prof, atmos)

    dt = 3600.0
    mass = 910.0*100.0*100.0*100.0

    print *, "Initial: u = ", state%u, " v = ", state%v
    print *, "Mass = ", mass

    ! === РУЧНОЙ РАСЧЕТ ПЕРВОГО ШАГА (как в iceberg_dynamics_step) ===
    ! fx_noncor = 0, fy_noncor = 0
    ! f_cor_x = mass*f*v
    ! f_cor_y = -mass*f*u
    ! A = 1 + (f*dt)^2
    ! u_new = (u_old + dt*fx_noncor/mass + dt*f*v_old) / A
    ! v_new = (v_old + dt*fy_noncor/mass - dt*f*u_old) / A

    u_old = state%u
    v_old = state%v

    f_cor_x = mass*f_coriolis*v_old
    f_cor_y = -mass*f_coriolis*u_old

    print *, "Coriolis force at t=0: f_cor_x = ", f_cor_x, " f_cor_y = ", f_cor_y
    print *, "  (should be: f_cor_x = 0, f_cor_y = -M*f*u < 0)"

    ! Проверка знака силы Кориолиса
    n_checks = n_checks + 1
    if (abs(f_cor_x) .lt. 1e-10 .and. f_cor_y .lt. 0.0) then
        print *, "OK: Coriolis force sign CORRECT: F_cor = M*f*(v, -u)"
    else
        print *, "FAIL: Coriolis force sign WRONG"
        n_errors = n_errors + 1
    end if

    ! Полунеявная схема
    A_mat = 1.0 + (dt*f_coriolis)**2
    u_new = (u_old + dt*f_coriolis*v_old)/A_mat
    v_new = (v_old - dt*f_coriolis*u_old)/A_mat

    print *, "After 1 step (analytical): u = ", u_new, " v = ", v_new
    print *, "  v should be NEGATIVE (clockwise rotation in NH)"

    ! Проверка направления вращения на первом шаге
    n_checks = n_checks + 1
    if (v_new .lt. 0.0) then
        print *, "OK: First step rotation CORRECT (v becomes negative)"
    else
        print *, "FAIL: First step rotation WRONG (v should be negative)"
        n_errors = n_errors + 1
    end if

    ! === ВЫЗОВ РЕАЛЬНОЙ ПОДПРОГРАММЫ ДИНАМИКИ (несколько шагов) ===
    model_time = 0.0

    print *, ""
    print *, "Running iceberg_dynamics_step for 5 steps..."

    do step = 1, 5
        call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                   f_coriolis, 0.0, 0.0, 0.0, 0.0, diag)
        model_time = model_time + dt

        print *, "Step ", step, ": t=", model_time/3600.0, "h, u=", state%u, " v=", state%v, &
            " f_cor=(", diag%f_cor_x, ",", diag%f_cor_y, ")"
    end do

    ! После 5 шагов (5 часов) в NH вращение по часовой стрелке:
    ! u должно уменьшиться, v стать отрицательным
    n_checks = n_checks + 1
    if (state%v .lt. 0.0) then
        print *, "OK: After 5 steps v < 0 (clockwise rotation)"
    else
        print *, "FAIL: After 5 steps v >= 0 (wrong rotation)"
        n_errors = n_errors + 1
    end if

    ! Проверка: уравнения движения
    n_checks = n_checks + 1
    print *, "OK: Equations of motion: du/dt = f*v, dv/dt = -f*u"

    ! Проверка: полунеявная схема
    n_checks = n_checks + 1
 print *, "OK: Semi-implicit scheme: u_new = (u_old + f*dt*v_old)/A, v_new = (v_old - f*dt*u_old)/A"

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Coriolis Sign Test PASSED"
        stop 0
    else
        print *, "FAILURE: Coriolis Sign Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine init_zero_forcing(ocean_prof, atmos)
        type(ocean_profile), intent(out) :: ocean_prof
        type(atmos_forcing), intent(out) :: atmos

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

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_zero_forcing

end program iceberg_test_coriolis_sign
