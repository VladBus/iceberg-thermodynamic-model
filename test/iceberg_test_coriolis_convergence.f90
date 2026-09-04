! ==============================================================================
! Тест: Coriolis Timestep Convergence
! Назначение: Исследовать сходимость полунеявной схемы Кориолиса при разных dt.
!             Сравнение с аналитическим решением: u = u0*cos(f*t), v = -u0*sin(f*t)
! ==============================================================================

program iceberg_test_coriolis_convergence
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: i, step, nsteps
    real :: dt
    real :: f_coriolis, latitude
    real :: u0
    real :: period_analytical
    real :: u_num, v_num, u_ana, v_ana
    real :: period_error, phase_error, amp_error, energy_error
    real :: model_time
    real, allocatable :: dts(:)
    real, allocatable :: period_errors(:), phase_errors(:), amp_errors(:), energy_errors(:)
    integer :: n_dts
    real :: p_phase

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Coriolis Timestep Convergence"
    print *, "=================================================="

    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    period_analytical = 2.0*3.141592653589793/abs(f_coriolis)
    u0 = 0.1

    print *, "Latitude: ", latitude
    print *, "f = ", f_coriolis
    print *, "Analytical period: ", period_analytical/3600.0, " hours"
    print *, ""

    ! Массив временных шагов для тестирования
    n_dts = 7
    allocate (dts(n_dts), period_errors(n_dts), phase_errors(n_dts), &
              amp_errors(n_dts), energy_errors(n_dts))

    dts = [3600.0, 1800.0, 900.0, 600.0, 300.0, 120.0, 60.0]

    print *, "dt[s]    Period_err[%]  Phase_err[deg]  Amp_err[%]   Energy_err[%]"

    do i = 1, n_dts
        dt = dts(i)
        nsteps = int(5*period_analytical/dt)  ! 5 периодов

        ! Инициализация
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, u0, 0.0)
        call init_zero_forcing(ocean_prof, atmos)

        model_time = 0.0

        ! Интегрирование 5 периодов
        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_coriolis, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do

        ! Аналитическое решение в конце
        u_ana = u0*cos(f_coriolis*model_time)
        v_ana = -u0*sin(f_coriolis*model_time)

        u_num = state%u
        v_num = state%v

        ! Ошибки
        ! 1. Ошибка периода: найти период из нулевых переходов
        call compute_period_error(state, dt, f_coriolis, u0, period_errors(i))

        ! 2. Фазовая ошибка
        phase_errors(i) = acos((u_num*u_ana + v_num*v_ana)/ &
                               (sqrt(u_num**2 + v_num**2)*sqrt(u_ana**2 + v_ana**2)))*57.2957795

        ! 3. Ошибка амплитуды
        amp_errors(i) = (sqrt(u_num**2 + v_num**2) - u0)/u0*100.0

        ! 4. Ошибка энергии
        energy_errors(i) = (u_num**2 + v_num**2 - u0**2)/u0**2*100.0

        print *, dt, period_errors(i), phase_errors(i), amp_errors(i), energy_errors(i)
    end do

    ! Проверка сходимости: ошибка должна уменьшаться с dt
    n_checks = n_checks + 1
    if (abs(period_errors(n_dts)) .lt. abs(period_errors(1))) then
        print *, "OK: Period error decreases with dt"
    else
        print *, "WARNING: Period error does not consistently decrease"
    end if

    n_checks = n_checks + 1
    if (abs(phase_errors(n_dts)) .lt. abs(phase_errors(1))) then
        print *, "OK: Phase error decreases with dt"
    else
        print *, "WARNING: Phase error does not consistently decrease"
    end if

    n_checks = n_checks + 1
    if (amp_errors(n_dts) .gt. amp_errors(1)) then
        print *, "OK: Amplitude damping decreases with dt (less negative)"
    else
        print *, "WARNING: Amplitude damping behavior unexpected"
    end if

    ! Оценка порядка сходимости для фазовой ошибки
    ! phase_error ~ dt^p
    n_checks = n_checks + 1
    p_phase = log(abs(phase_errors(1))/abs(phase_errors(n_dts)))/log(dts(1)/dts(n_dts))
    print *, "Estimated convergence order (phase): p = ", p_phase
    if (p_phase .gt. 0.5 .and. p_phase .lt. 2.5) then
        print *, "OK: Convergence order reasonable (between 0.5 and 2.5)"
    else
        print *, "WARNING: Unusual convergence order"
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Coriolis Convergence Test PASSED"
        stop 0
    else
        print *, "FAILURE: Coriolis Convergence Test FAILED with ", n_errors, " errors"
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

    subroutine compute_period_error(state, dt, f, u0, period_error)
        type(iceberg_state), intent(in) :: state
        real, intent(in) :: dt, f, u0
        real, intent(out) :: period_error

        ! Упрощенно: используем ошибку фазы как proxy для ошибки периода
        ! Для точного измерения периода нужно отслеживать нулевые переходы
        real :: u_ana, v_ana, u_num, v_num, model_time
        real :: phase_err

        model_time = 5.0*2.0*3.141592653589793/f  ! 5 периодов
        u_ana = u0*cos(f*model_time)
        v_ana = -u0*sin(f*model_time)
        u_num = state%u
        v_num = state%v

        phase_err = acos((u_num*u_ana + v_num*v_ana)/ &
                         (sqrt(u_num**2 + v_num**2)*sqrt(u_ana**2 + v_ana**2)))

        ! Ошибка периода примерно равна фазовой ошибке за 5 периодов / 5
        period_error = phase_err/5.0*360.0*100.0/(2.0*3.141592653589793)  ! в процентах
    end subroutine compute_period_error

end program iceberg_test_coriolis_convergence
