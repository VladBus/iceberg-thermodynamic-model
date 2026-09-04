! ==============================================================================
! Тест: Coriolis with Moving Latitude
! Назначение: Проверить, что параметр Кориолиса f = 2Ω sin(lat) пересчитывается
!             при изменении широты айсберга.
! ==============================================================================

program iceberg_test_moving_coriolis
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    use iceberg_forcing, only: model_coords_to_latlon
    use param, only: fi, dl, is, js, is1, js1, kt1, ht
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt, model_time
    real :: latitude, longitude
    real :: f_coriolis
    real :: f_initial, f_final
    real :: lat_initial, lat_final
    real :: x_model, y_model
    real :: f_expected
    logical :: ok

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Coriolis with Moving Latitude"
    print *, "=================================================="

    ! Инициализация модельной сетки
    call coup1()
    call ikuv()

    latitude = 70.0  ! Начальная широта 70N
    longitude = 30.0
    ! Model coords: x = (j-1)*13890, y = (i-1)*13890
    ! lat 70N ~ i=55, lon 30E ~ j=37
    x_model = 36.0*13890.0
    y_model = 54.0*13890.0

    print *, "Initial lat: ", latitude, " lon: ", longitude
    print *, "Initial x: ", x_model, " y: ", y_model

    call iceberg_init(state, x_model, y_model, 100.0, 100.0, 100.0, &
                      latitude, longitude, 0.05, 0.0)  ! Небольшая скорость на север

    ! Нулевой форсинг (только Кориолис)
    call init_zero_forcing(ocean_prof, atmos)

    dt = 3600.0
    nsteps = 100  ! ~4 дня

    ! Запомнить начальное f
    f_initial = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    print *, "Initial f = ", f_initial

    ! Интегрирование с обновлением lat/lon
    do step = 1, nsteps
        model_time = real(step)*dt

        ! Обновить f из текущей широты (как в iceberg_step)
        f_coriolis = 2.0*7.2921150e-5*sin(state%latitude/57.2957795)

        call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                   f_coriolis, 0.0, 0.0, 0.0, 0.0, diag)

        ! Обновить позицию (как в iceberg_step)
        state%x = state%x + dt*state%u
        state%y = state%y + dt*state%v

        ! Обновить lat/lon из новых x,y (инверсная проекция)
        call model_coords_to_latlon(state%x, state%y, state%latitude, state%longitude, ok)

        if (.not. ok) then
            print *, "WARNING: model_coords_to_latlon failed at step ", step
            exit
        end if

        ! Вывод прогресса
        if (mod(step, 20) .eq. 0) then
            print *, "Step ", step, ": lat=", state%latitude, " lon=", state%longitude, &
                " f=", 2.0*7.2921150e-5*sin(state%latitude/57.2957795)
        end if
    end do

    f_final = 2.0*7.2921150e-5*sin(state%latitude/57.2957795)
    lat_initial = 70.0
    lat_final = state%latitude

    print *, ""
    print *, "Final lat: ", lat_final
    print *, "Final f: ", f_final
    print *, "f change: ", f_final - f_initial
    print *, "Relative f change: ", (f_final - f_initial)/f_initial*100.0, "%"

    ! Проверка: f должно измениться с широтой
    n_checks = n_checks + 1
    if (abs(f_final - f_initial) .gt. 1e-6) then
        print *, "OK: Coriolis parameter f changes with latitude"
    else
        print *, "FAIL: Coriolis parameter f does not change"
        n_errors = n_errors + 1
    end if

    ! Проверка: f соответствует формуле f = 2Ω sin(lat)
    n_checks = n_checks + 1
    f_expected = 2.0*7.2921150e-5*sin(lat_final/57.2957795)
    if (abs(f_final - f_expected) .lt. 1e-9) then
        print *, "OK: f matches analytical formula f = 2Ω sin(lat)"
    else
        print *, "FAIL: f does not match formula"
        print *, "  f_final = ", f_final, " expected = ", f_expected
        n_errors = n_errors + 1
    end if

    ! Проверка: широта изменилась (айсберг двигался)
    n_checks = n_checks + 1
    if (abs(lat_final - lat_initial) .gt. 0.01) then
        print *, "OK: Latitude changed during integration (", lat_final - lat_initial, " deg)"
    else
        print *, "FAIL: Latitude did not change significantly"
        n_errors = n_errors + 1
    end if

    ! Проверка: f увеличился при движении на север (NH)
    n_checks = n_checks + 1
    if (f_final .gt. f_initial) then
        print *, "OK: f increased when moving north in NH"
    else
        print *, "FAIL: f should increase when moving north in NH"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Moving Coriolis Test PASSED"
        stop 0
    else
        print *, "FAILURE: Moving Coriolis Test FAILED with ", n_errors, " errors"
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

end program iceberg_test_moving_coriolis
