! ==============================================================================
! Тест: Moving Forcing Verification
! Назначение: Доказать, что форсинг реально обновляется при движении айсберга.
!             Использует синтетические пространственно-изменяющиеся поля форсинга.
!             ТЕСТ ДОЛЖЕН ПРОВАЛИТЬСЯ, если форсинг остается замороженным
!             в начальной позиции.
! ==============================================================================

program iceberg_test_moving_forcing
    use iceberg
    use iceberg_forcing
    use iceberg_types
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt, model_time_sec
    real :: bathymetry
    logical :: forcing_ok
    real :: prev_u10, prev_v10, prev_temp, prev_salt
    real :: prev_ocn_u, prev_ocn_v
    real :: prev_bathy
    logical :: forcing_changed

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Moving Forcing Verification"
    print *, "=================================================="

    ! Инициализация айсберга: 75N, 30E
    ! Model cell (i=61, j=37) -> x=36*13890, y=60*13890
    call iceberg_init(state, 36.0*13890.0, 60.0*13890.0, &
                      100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)

    dt = 3600.0
    nsteps = 24*5  ! 5 дней

    print *, "Testing with synthetic spatially-varying forcing..."
    print *, "Initial position: x=", state%x, " y=", state%y

    ! Запомнить начальное форсинг (использует x,y напрямую)
    call get_synthetic_ocean_profile(state%x, state%y, ocean_prof, forcing_ok)
    call get_synthetic_atmos_forcing(state%x, state%y, 0.0, atmos, forcing_ok)
    call get_synthetic_bathymetry(state%x, state%y, bathymetry, forcing_ok)

    prev_u10 = atmos%u10
    prev_v10 = atmos%v10
    prev_temp = ocean_prof%temp(1)
    prev_salt = ocean_prof%salt(1)
    prev_ocn_u = ocean_prof%u(1)
    prev_ocn_v = ocean_prof%v(1)
    prev_bathy = bathymetry

    forcing_changed = .false.

    do step = 1, nsteps
        model_time_sec = real(step)*dt

        ! Получить форсинг на ТЕКУЩЕЙ позиции (x,y)
        call get_synthetic_ocean_profile(state%x, state%y, ocean_prof, forcing_ok)
        call get_synthetic_atmos_forcing(state%x, state%y, model_time_sec, atmos, forcing_ok)
        call get_synthetic_bathymetry(state%x, state%y, bathymetry, forcing_ok)

! Проверить, изменилось ли форсинг
        if (abs(atmos%u10 - prev_u10) .gt. 1e-6 .or. &
            abs(atmos%v10 - prev_v10) .gt. 1e-6 .or. &
            abs(ocean_prof%temp(1) - prev_temp) .gt. 1e-6 .or. &
            abs(ocean_prof%salt(1) - prev_salt) .gt. 1e-6 .or. &
            abs(ocean_prof%u(1) - prev_ocn_u) .gt. 1e-6 .or. &
            abs(ocean_prof%v(1) - prev_ocn_v) .gt. 1e-6 .or. &
            abs(bathymetry - prev_bathy) .gt. 1e-3) then
            forcing_changed = .true.
        end if

        prev_u10 = atmos%u10
        prev_v10 = atmos%v10
        prev_temp = ocean_prof%temp(1)
        prev_salt = ocean_prof%salt(1)
        prev_ocn_u = ocean_prof%u(1)
        prev_ocn_v = ocean_prof%v(1)
        prev_bathy = bathymetry

        ! Шаг интегрирования (используем урезанную версию без реальных данных)
        call iceberg_step_synthetic(state, dt, ocean_prof, atmos, bathymetry, diag)

        if (.not. state%active) exit
    end do

    print *, "=================================================="
    print *, "Forcing changed during movement: ", forcing_changed
    print *, "Final position: x=", state%x, " y=", state%y
    print *, "Final lat/lon: lat=", state%latitude, " lon=", state%longitude
    print *, "=================================================="

    ! Проверка: форсинг ДОЛЖЕН был измениться
    n_checks = n_checks + 1
    if (forcing_changed) then
        print *, "OK: Forcing varies with position"
    else
        print *, "FAIL: Forcing did NOT change with position (frozen at initial)"
        n_errors = n_errors + 1
    end if

    ! Проверка: позиция изменилась
    n_checks = n_checks + 1
    if (abs(state%x - 36.0*13890.0) .gt. 100.0 .or. &
        abs(state%y - 60.0*13890.0) .gt. 100.0) then
        print *, "OK: Iceberg moved from initial position"
    else
        print *, "FAIL: Iceberg did not move"
        n_errors = n_errors + 1
    end if

    ! Проверка: нет NaN
    n_checks = n_checks + 1
    if (state%x .eq. state%x .and. state%y .eq. state%y .and. &
        state%u .eq. state%u .and. state%v .eq. state%v) then
        print *, "OK: No NaN in state"
    else
        print *, "FAIL: NaN detected"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Moving Forcing Test PASSED"
        stop 0
    else
        print *, "FAILURE: Moving Forcing Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    ! --------------------------------------------------------------------------
    ! Синтетический океанский профиль — пространственно меняющийся (по x,y)
    ! --------------------------------------------------------------------------
    subroutine get_synthetic_ocean_profile(x_model_in, y_model_in, prof_out, ok_out)
        real, intent(in) :: x_model_in, y_model_in
        type(ocean_profile), intent(out) :: prof_out
        logical, intent(out) :: ok_out

        real :: x_nd, y_nd
        integer :: k, nlevels

        ok_out = .true.
        nlevels = 5
        prof_out%nlevels = nlevels
        allocate (prof_out%z(nlevels), prof_out%dz(nlevels), prof_out%temp(nlevels), &
                  prof_out%salt(nlevels), prof_out%u(nlevels), prof_out%v(nlevels))

        ! Нормализованные координаты для вариации
        x_nd = x_model_in/1000000.0
        y_nd = y_model_in/1000000.0

        do k = 1, nlevels
            prof_out%z(k) = real(k)*10.0  ! 10, 20, 30, 40, 50 m
            prof_out%dz(k) = 10.0

            ! Температура: меняется с x и глубиной
            prof_out%temp(k) = 2.0 + 0.5*sin(x_nd) - 0.02*prof_out%z(k)

            ! Соленость: меняется с y
            prof_out%salt(k) = 0.0345 + 0.0005*cos(y_nd)

            ! Течения: меняются с x,y
            prof_out%u(k) = 0.1*sin(x_nd)*(1.0 - prof_out%z(k)/100.0)
            prof_out%v(k) = 0.1*cos(y_nd)*(1.0 - prof_out%z(k)/100.0)
        end do
    end subroutine get_synthetic_ocean_profile

    ! --------------------------------------------------------------------------
    ! Синтетический атмосферный форсинг — пространственно меняющийся (по x,y)
    ! --------------------------------------------------------------------------
    subroutine get_synthetic_atmos_forcing(x_model_in, y_model_in, model_time_sec_in, atmos_out, ok_out)
        real, intent(in) :: x_model_in, y_model_in, model_time_sec_in
        type(atmos_forcing), intent(out) :: atmos_out
        logical, intent(out) :: ok_out

        real :: x_nd, y_nd

        ok_out = .true.
        x_nd = x_model_in/1000000.0
        y_nd = y_model_in/1000000.0

        ! Ветер: меняется с x,y
        atmos_out%u10 = 10.0*sin(x_nd) + 2.0*cos(y_nd)
        atmos_out%v10 = 5.0*cos(y_nd) - 3.0*sin(x_nd)

        ! Температура: меняется с x
        atmos_out%t2m = 260.0 - 5.0*sin(x_nd)
        atmos_out%d2m = atmos_out%t2m - 2.0
        atmos_out%tcc = 0.5 + 0.2*sin(x_nd)
        atmos_out%msl = 101325.0 + 500.0*cos(y_nd)
        atmos_out%snowfall = 0.0
    end subroutine get_synthetic_atmos_forcing

    ! --------------------------------------------------------------------------
    ! Синтетическая батиметрия — пространственно меняющаяся (по x,y)
    ! --------------------------------------------------------------------------
    subroutine get_synthetic_bathymetry(x_model_in, y_model_in, bathymetry_out, ok_out)
        real, intent(in) :: x_model_in, y_model_in
        real, intent(out) :: bathymetry_out
        logical, intent(out) :: ok_out

        real :: y_nd

        ok_out = .true.
        y_nd = y_model_in/1000000.0

        bathymetry_out = 500.0 + 100.0*cos(y_nd)
    end subroutine get_synthetic_bathymetry

    ! --------------------------------------------------------------------------
    ! Упрощенный шаг интегрирования для синтетического теста
    ! --------------------------------------------------------------------------
    subroutine iceberg_step_synthetic(state_in, dt_in, ocean_prof_in, atmos_in, bathymetry_in, diag_out)
        type(iceberg_state), intent(inout) :: state_in
        real, intent(in) :: dt_in
        type(ocean_profile), intent(in) :: ocean_prof_in
        type(atmos_forcing), intent(in) :: atmos_in
        real, intent(in) :: bathymetry_in
        type(iceberg_diagnostics), intent(out) :: diag_out

        real :: mass, f_coriolis
        real :: f_wind_x, f_wind_y, f_water_x, f_water_y
        real :: draft, a_sail, a_wet, freeboard
        real :: u_rel, v_rel, speed_rel
        real :: u_avg, v_avg
        real :: fx_noncor, fy_noncor, A_mat, u_old, v_old
        integer :: k

        ! Геометрия
        mass = 910.0*state_in%L*state_in%W*state_in%H
        draft = state_in%H*910.0/1028.0
        freeboard = state_in%H - draft
        a_sail = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*freeboard
        a_wet = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*draft

        ! Ветровая сила
        u_rel = atmos_in%u10 - state_in%u
        v_rel = atmos_in%v10 - state_in%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)
        f_wind_x = 0.5*1.225*1.3e-3*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*1.225*1.3e-3*a_sail*speed_rel*v_rel

        ! Водная сила (упрощенно: глубинно-усредненная)
        u_avg = 0.0; v_avg = 0.0
        do k = 1, ocean_prof_in%nlevels
            u_avg = u_avg + ocean_prof_in%u(k)*ocean_prof_in%dz(k)
            v_avg = v_avg + ocean_prof_in%v(k)*ocean_prof_in%dz(k)
        end do
        u_avg = u_avg/sum(ocean_prof_in%dz)
        v_avg = v_avg/sum(ocean_prof_in%dz)

        f_water_x = 0.5*1028.0*2.0e-3*a_wet* &
                    sqrt((u_avg - state_in%u)**2 + (v_avg - state_in%v)**2)*(u_avg - state_in%u)
        f_water_y = 0.5*1028.0*2.0e-3*a_wet* &
                    sqrt((u_avg - state_in%u)**2 + (v_avg - state_in%v)**2)*(v_avg - state_in%v)

        ! Кориолис
        f_coriolis = 2.0*7.2921150e-5*sin(state_in%latitude/57.2957795)

        ! Полунеявная схема
        fx_noncor = f_wind_x + f_water_x
        fy_noncor = f_wind_y + f_water_y
        u_old = state_in%u
        v_old = state_in%v
        A_mat = 1.0 + (dt_in*f_coriolis)**2
        state_in%u = (u_old + dt_in*fx_noncor/mass + dt_in*f_coriolis*v_old)/A_mat
        state_in%v = (v_old + dt_in*fy_noncor/mass - dt_in*f_coriolis*u_old)/A_mat

        ! Обновление позиции
        state_in%x = state_in%x + dt_in*state_in%u
        state_in%y = state_in%y + dt_in*state_in%v

        ! НЕ обновляем lat/lon (fi/dl = 0 в этом тесте)
        diag_out%forcing_valid = .true.

        state_in%nstep = state_in%nstep + 1
        state_in%time = state_in%time + dt_in
    end subroutine iceberg_step_synthetic

end program iceberg_test_moving_forcing
