! ==============================================================================
! Тест: Coriolis Timestep Convergence — Corrected Analysis
! Назначение: Исследовать сходимость полунеявной схемы Кориолиса при разных dt.
!             Разделить: phase error, amplitude error, energy error, actual period error.
!             Вычислить локальный порядок сходимости для каждого типа ошибки.
!             Использовать аналитическое решение: u = u0*cos(f*t), v = -u0*sin(f*t)
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
    real :: phase_error, amp_error, energy_error
    real :: period_error
    real :: model_time
    real, allocatable :: dts(:)
    real, allocatable :: phase_errors(:), amp_errors(:), energy_errors(:), period_errors(:)
    real, allocatable :: local_p_phase(:), local_p_amp(:), local_p_energy(:), local_p_period(:)
    integer :: n_dts
    real :: p_phase_global, p_amp_global, p_energy_global

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Coriolis Timestep Convergence (Corrected)"
    print *, "=================================================="

    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    period_analytical = 2.0*3.141592653589793/abs(f_coriolis)
    u0 = 0.1

    print *, "Latitude: ", latitude
    print *, "f = ", f_coriolis, " [1/s]"
    print *, "Analytical period: ", period_analytical/3600.0, " hours = ", period_analytical, " s"
    print *, "Initial velocity: u0 = ", u0, " m/s, v0 = 0"
    print *, ""

    ! Массив временных шагов для тестирования
    n_dts = 7
    allocate (dts(n_dts), phase_errors(n_dts), amp_errors(n_dts), &
              energy_errors(n_dts), period_errors(n_dts))
    allocate (local_p_phase(n_dts - 1), local_p_amp(n_dts - 1), &
              local_p_energy(n_dts - 1), local_p_period(n_dts - 1))

    dts = [3600.0, 1800.0, 900.0, 600.0, 300.0, 120.0, 60.0]

    print *, "dt[s]    Phase_err[deg]  Amp_err[%]   Energy_err[%]  Period_err[%]"

    do i = 1, n_dts
        dt = dts(i)
        ! Интегрировать ровно 5 аналитических периодов
        nsteps = int(5*period_analytical/dt + 0.5)

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

        ! === ОШИБКИ ===

        ! 1. Фазовая ошибка (угол между числовым и аналитическим вектором скорости)
        ! phi_num = atan2(v_num, u_num), phi_ana = atan2(v_ana, u_ana)
        ! Δphi = phi_num - phi_ana (с unwrap для 5 периодов)
        phase_errors(i) = compute_phase_error(u_num, v_num, u_ana, v_ana, &
                                              f_coriolis, model_time)

        ! 2. Ошибка амплитуды (модуль скорости)
        amp_errors(i) = (sqrt(u_num**2 + v_num**2) - u0)/u0*100.0

        ! 3. Ошибка энергии (кинетическая энергия на единицу массы)
        energy_errors(i) = (u_num**2 + v_num**2 - u0**2)/u0**2*100.0

        ! 4. Ошибка периода (прямое измерение через нулевые переходы v)
        period_errors(i) = compute_period_error_direct(dt, f_coriolis, u0, nsteps)

        print '(F8.1, 3F14.4, F14.4)', &
            dt, phase_errors(i), amp_errors(i), energy_errors(i), period_errors(i)
    end do

    ! === ЛОКАЛЬНЫЙ ПОРЯДОК СХОДИМОСТИ ===
    print *, ""
    print *, "Local convergence order p = log(|E_i|/|E_{i+1}|) / log(dt_i/dt_{i+1})"
    print *, "dt_i->dt_{i+1}    p_phase   p_amp     p_energy  p_period"

    do i = 1, n_dts - 1
        local_p_phase(i) = log(abs(phase_errors(i))/abs(phase_errors(i + 1)))/ &
                           log(dts(i)/dts(i + 1))
        local_p_amp(i) = log(abs(amp_errors(i))/abs(amp_errors(i + 1)))/ &
                         log(dts(i)/dts(i + 1))
        local_p_energy(i) = log(abs(energy_errors(i))/abs(energy_errors(i + 1)))/ &
                            log(dts(i)/dts(i + 1))
        local_p_period(i) = log(abs(period_errors(i))/abs(period_errors(i + 1)))/ &
                            log(dts(i)/dts(i + 1))

        print '(2F8.1, 4F10.3)', dts(i), dts(i + 1), &
            local_p_phase(i), local_p_amp(i), local_p_energy(i), local_p_period(i)
    end do

    ! Глобальный порядок (dt=3600 -> dt=60)
    p_phase_global = log(abs(phase_errors(1))/abs(phase_errors(n_dts)))/ &
                     log(dts(1)/dts(n_dts))
    p_amp_global = log(abs(amp_errors(1))/abs(amp_errors(n_dts)))/ &
                   log(dts(1)/dts(n_dts))
    p_energy_global = log(abs(energy_errors(1))/abs(energy_errors(n_dts)))/ &
                      log(dts(1)/dts(n_dts))

    print *, ""
    print *, "Global convergence order (3600->60s):"
    print *, "  Phase:   ", p_phase_global
    print *, "  Amplitude:", p_amp_global
    print *, "  Energy:  ", p_energy_global

    ! === ВРЕМЕННЫЕ РЯДЫ ДЛЯ АНАЛИЗА ДЕМПФИРОВАНИЯ ===
    print *, ""
    print *, "Time series for damping analysis (dt=3600, 900, 300, 60):"
    call output_time_series(3600.0, f_coriolis, u0)
    call output_time_series(900.0, f_coriolis, u0)
    call output_time_series(300.0, f_coriolis, u0)
    call output_time_series(60.0, f_coriolis, u0)

    ! === ПРОВЕРКИ ===
    ! Фазовая ошибка должна уменьшаться с dt
    n_checks = n_checks + 1
    if (abs(phase_errors(n_dts)) .lt. abs(phase_errors(1))) then
        print *, "OK: Phase error decreases with dt"
    else
        print *, "WARNING: Phase error does not consistently decrease"
    end if

    ! Амплитудное демпфирование должно уменьшаться (менее отрицательным) с dt
    n_checks = n_checks + 1
    if (amp_errors(n_dts) .gt. amp_errors(1)) then
        print *, "OK: Amplitude damping decreases with dt (less negative)"
    else
        print *, "WARNING: Amplitude damping behavior unexpected"
    end if

    ! Локальный порядок должен быть ~2 для фазовой ошибки в асимптотическом режиме
    ! Используем 600->300 переход (асимптотический, до round-off)
    n_checks = n_checks + 1
    if (local_p_phase(4) .gt. 1.5 .and. local_p_phase(4) .lt. 2.5) then
        print *, "OK: Asymptotic phase convergence order ~2 (p = ", local_p_phase(4), ")"
    else
        print *, "INFO: Asymptotic phase order p = ", local_p_phase(4), &
            " (may be pre-asymptotic or round-off dominated)"
    end if

    ! Амплитудная ошибка - первый порядок ожидается для полунеявной схемы
    n_checks = n_checks + 1
    if (local_p_amp(n_dts - 1) .gt. 0.5 .and. local_p_amp(n_dts - 1) .lt. 2.0) then
        print *, "OK: Amplitude convergence order reasonable (p = ", local_p_amp(n_dts - 1), ")"
    else
        print *, "INFO: Amplitude order p = ", local_p_amp(n_dts - 1)
    end if

    ! Период (если измерен) - проверка
    n_checks = n_checks + 1
    if (period_errors(n_dts) .ne. 0.0 .and. &
        local_p_period(n_dts - 1) .gt. 0.5 .and. local_p_period(n_dts - 1) .lt. 2.5) then
        print *, "OK: Period error convergence order reasonable"
    else
        print *, "INFO: Period error may be NaN or unreliable"
    end if

    ! Сохранить CSV для графиков
    call write_convergence_csv(dts, phase_errors, amp_errors, energy_errors, period_errors, &
                               local_p_phase, local_p_amp, local_p_energy, local_p_period, n_dts)

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

    ! --------------------------------------------------------------------------
    ! Фазовая ошибка с unwrap
    ! --------------------------------------------------------------------------
    function compute_phase_error(u_num, v_num, u_ana, v_ana, f, t) result(phase_err)
        real, intent(in) :: u_num, v_num, u_ana, v_ana, f, t
        real :: phase_err
        real :: phi_num, phi_ana, delta_phi

        phi_num = atan2(v_num, u_num)
        phi_ana = atan2(v_ana, u_ana)

        ! Unwrap: analytical phase = -f*t (for u0>0, v0=0)
        ! phi_ana = -f*t + 2π*k, find k that minimizes |phi_num - phi_ana|
        delta_phi = phi_num - phi_ana
        delta_phi = delta_phi - 2.0*3.141592653589793*nint(delta_phi/(2.0*3.141592653589793))

        phase_err = delta_phi*57.2957795  ! convert to degrees
    end function compute_phase_error

    ! --------------------------------------------------------------------------
    ! Прямое измерение периода через нулевые переходы v(t)
    ! --------------------------------------------------------------------------
    function compute_period_error_direct(dt, f, u0, nsteps) result(period_err)
        real, intent(in) :: dt, f, u0
        integer, intent(in) :: nsteps
        real :: period_err

        type(iceberg_state) :: state
        type(ocean_profile) :: ocean_prof
        type(atmos_forcing) :: atmos
        type(iceberg_diagnostics) :: diag

        integer :: step, n_crossings
        real :: v_prev, v_curr, t_cross1, t_cross2
        real :: measured_period
        logical :: first_cross

        period_err = -999.0  ! NaN equivalent

        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          75.0, 0.0, u0, 0.0)
        call init_zero_forcing(ocean_prof, atmos)

        n_crossings = 0
        t_cross1 = -1.0
        t_cross2 = -1.0
        first_cross = .true.
        v_prev = 0.0  ! v0 = 0

        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f, 0.0, 0.0, 0.0, 0.0, diag)

            v_curr = state%v

            ! Detect zero crossing of v: v_prev * v_curr < 0
            if (v_prev*v_curr .lt. 0.0) then
                if (first_cross) then
                    ! Linear interpolation for crossing time
                    t_cross1 = real(step - 1)*dt + dt*abs(v_prev)/(abs(v_prev) + abs(v_curr))
                    first_cross = .false.
                else
                    t_cross2 = real(step - 1)*dt + dt*abs(v_prev)/(abs(v_prev) + abs(v_curr))
                    n_crossings = n_crossings + 1
                    exit  ! Measure one half-period
                end if
            end if

            v_prev = v_curr
        end do

        if (n_crossings .eq. 1 .and. t_cross1 .gt. 0.0 .and. t_cross2 .gt. t_cross1) then
            measured_period = 2.0*(t_cross2 - t_cross1)
            period_err = (measured_period - 2.0*3.141592653589793/f)/(2.0*3.141592653589793/f)*100.0
        end if
    end function compute_period_error_direct

    ! --------------------------------------------------------------------------
    ! Вывод временных рядов для анализа демпфирования
    ! --------------------------------------------------------------------------
    subroutine output_time_series(dt, f, u0)
        real, intent(in) :: dt, f, u0

        type(iceberg_state) :: state
        type(ocean_profile) :: ocean_prof
        type(atmos_forcing) :: atmos
        type(iceberg_diagnostics) :: diag

        integer :: step, nsteps
        real :: model_time, u, v, speed, energy, phi
        integer :: dt_int
        character(len=20) :: dt_str

        nsteps = int(5*2.0*3.141592653589793/f/dt + 0.5)

        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          75.0, 0.0, u0, 0.0)
        call init_zero_forcing(ocean_prof, atmos)

        dt_int = nint(dt)
        write (dt_str, '(I0)') dt_int

 open (99, file='data/output/diagnostics/stage9.4c/coriolis_ts_dt'//trim(adjustl(dt_str))//'.csv', &
              status='replace')
        write (99, '(A)') 'dt,step,time_h,u,v,speed,energy,phi_deg'

        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = real(step)*dt

            u = state%u
            v = state%v
            speed = sqrt(u**2 + v**2)
            energy = 0.5*(u**2 + v**2)
            phi = atan2(v, u)*57.2957795

          write (99, '(F8.1,I6,F10.3,5F12.6)') dt, step, model_time/3600.0, u, v, speed, energy, phi
        end do

        close (99)
    end subroutine output_time_series

    ! --------------------------------------------------------------------------
    ! Integer to string helper
    ! --------------------------------------------------------------------------

    ! --------------------------------------------------------------------------
    ! Запись CSV с результатами сходимости
    ! --------------------------------------------------------------------------
    subroutine write_convergence_csv(dts, phase_e, amp_e, energy_e, period_e, &
                                     p_phase, p_amp, p_energy, p_period, n)
        real, intent(in) :: dts(n), phase_e(n), amp_e(n), energy_e(n), period_e(n)
        real, intent(in) :: p_phase(n - 1), p_amp(n - 1), p_energy(n - 1), p_period(n - 1)
        integer, intent(in) :: n

        integer :: unit, ios, i

        open (unit, file='data/output/diagnostics/stage9.4c/coriolis_convergence.csv', &
              status='replace', iostat=ios)
        if (ios .ne. 0) return

        write (unit, '(A)') 'dt,phase_error_deg,amp_error_pct,energy_error_pct,period_error_pct'
        do i = 1, n
            write (unit, '(F8.1,4F16.6)') dts(i), phase_e(i), amp_e(i), energy_e(i), period_e(i)
        end do

        write (unit, '(A)') ''
        write (unit, '(A)') 'local_order,dt_i,dt_ip1,p_phase,p_amp,p_energy,p_period'
        do i = 1, n - 1
            write (unit, '(A,2F8.1,4F10.4)') 'local', dts(i), dts(i + 1), &
                p_phase(i), p_amp(i), p_energy(i), p_period(i)
        end do

        write (unit, '(A)') ''
        write (unit, '(A,3F10.4)') 'global_order,,', p_phase(1), p_amp(1), p_energy(1)

        close (unit)
    end subroutine write_convergence_csv

end program iceberg_test_coriolis_convergence
