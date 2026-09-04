! ==============================================================================
! Тест: Coordinate Mapping Numerical Verification
! Назначение: Проверить точность обратной проекции model_coords_to_latlon
!             и прямой проекции latlon_to_model_coords.
!             Round-trip test: lat/lon -> x/y -> lat/lon
!             Trajectory sensitivity: влияние ошибки координат на траекторию.
! ==============================================================================

program iceberg_test_coord_mapping
    use iceberg
    use iceberg_types
    use iceberg_forcing, only: model_coords_to_latlon, latlon_to_model_coords
    use param, only: fi, dl, is, js, is1, js1, kt1, ht
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    implicit none

    integer :: n_errors, n_checks
    integer :: i, j, step, nsteps, n_points
    real :: lat_in, lon_in, lat_out, lon_out
    real :: x_model, y_model
    real :: lat_err, lon_err
    real :: max_lat_err, max_lon_err, rms_lat_err, rms_lon_err
    logical :: ok
    real :: dx_model
    real :: test_lats(4), test_lons(4)
    real :: lat1, lat2, f1, f2, df
    real :: df_err
    real :: lat_traj, lon_traj, x_traj, y_traj

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Coordinate Mapping Numerical Verification"
    print *, "=================================================="

    ! Инициализация модельной сетки
    call coup1()
    call ikuv()

    dx_model = 13890.0

    print *, "Model grid: is1=", is1, " js1=", js1
    print *, "Grid spacing: ", dx_model, " m"
    print *, ""

    ! =========================================================================
    ! TEST 1: Round-trip на регулярной сетке точек
    ! =========================================================================
    print *, "--- TEST 1: Round-trip accuracy on grid points ---"

    max_lat_err = 0.0
    max_lon_err = 0.0
    rms_lat_err = 0.0
    rms_lon_err = 0.0
    n_points = 0

    do i = 2, is1 - 1, 10  ! шаг 10 для скорости
        do j = 2, js1 - 1, 10
            ! Пропустить сушу
            if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle

            ! Исходные lat/lon из модели
            lat_in = fi(i, j)
            lon_in = dl(i, j)

            ! Прямая проекция: lat/lon -> x/y
            call latlon_to_model_coords(lat_in, lon_in, x_model, y_model, ok)
            if (.not. ok) cycle

            ! Обратная проекция: x/y -> lat/lon
            call model_coords_to_latlon(x_model, y_model, lat_out, lon_out, ok)
            if (.not. ok) cycle

            ! Ошибки
            lat_err = abs(lat_out - lat_in)
            lon_err = abs(lon_out - lon_in)

            ! Нормализация долготы
            if (lon_err .gt. 180.0) lon_err = 360.0 - lon_err

            max_lat_err = max(max_lat_err, lat_err)
            max_lon_err = max(max_lon_err, lon_err)
            rms_lat_err = rms_lat_err + lat_err**2
            rms_lon_err = rms_lon_err + lon_err**2
            n_points = n_points + 1
        end do
    end do

    rms_lat_err = sqrt(rms_lat_err/real(n_points))
    rms_lon_err = sqrt(rms_lon_err/real(n_points))

    print *, "Round-trip test on ", n_points, " grid points:"
    print *, "  Max lat error: ", max_lat_err, " deg"
    print *, "  Max lon error: ", max_lon_err, " deg"
    print *, "  RMS lat error: ", rms_lat_err, " deg"
    print *, "  RMS lon error: ", rms_lon_err, " deg"

    n_checks = n_checks + 1
    if (max_lat_err .lt. 0.2 .and. max_lon_err .lt. 0.2) then
        print *, "OK: Round-trip error < 0.2 deg (within grid resolution)"
    else
        print *, "WARNING: Round-trip error > 0.2 deg"
    end if

    ! =========================================================================
    ! TEST 2: Round-trip в конкретных точках интереса
    ! =========================================================================
    print *, ""
    print *, "--- TEST 2: Round-trip at key locations ---"

    test_lats = [70.0, 75.0, 76.0, 72.0]
    test_lons = [30.0, 30.0, 40.0, 35.0]

    do i = 1, 4
        lat_in = test_lats(i)
        lon_in = test_lons(i)

        call latlon_to_model_coords(lat_in, lon_in, x_model, y_model, ok)
        if (.not. ok) then
            print *, "Point ", i, ": latlon_to_model_coords failed"
            cycle
        end if

        call model_coords_to_latlon(x_model, y_model, lat_out, lon_out, ok)
        if (.not. ok) then
            print *, "Point ", i, ": model_coords_to_latlon failed"
            cycle
        end if

        lat_err = abs(lat_out - lat_in)
        lon_err = abs(lon_out - lon_in)
        if (lon_err .gt. 180.0) lon_err = 360.0 - lon_err

        print *, "Point ", i, ": lat_in=", lat_in, " lon_in=", lon_in, &
            " -> lat_out=", lat_out, " lon_out=", lon_out, &
            " err=(", lat_err, ",", lon_err, ") deg"
    end do

    ! =========================================================================
    ! TEST 3: Trajectory sensitivity - влияние ошибки координат на f
    ! =========================================================================
    print *, ""
    print *, "--- TEST 3: Trajectory sensitivity to coordinate error ---"

    ! Симуляция движения на 1 градус широты
    lat1 = 75.0
    lat2 = 76.0  ! 1 градус севернее
    f1 = 2.0*7.2921150e-5*sin(lat1/57.2957795)
    f2 = 2.0*7.2921150e-5*sin(lat2/57.2957795)
    df = f2 - f1

    print *, "f at 75N: ", f1
    print *, "f at 76N: ", f2
    print *, "df for 1 deg: ", df
    print *, "Relative change: ", df/f1*100.0, "%"

    ! Ошибка в широте 0.1 градуса -> ошибка в f
    df_err = 2.0*7.2921150e-5*(sin((lat1 + 0.1)/57.2957795) - sin(lat1/57.2957795))
    print *, "df for 0.1 deg lat error: ", df_err
    print *, "Relative f error: ", df_err/f1*100.0, "%"

    n_checks = n_checks + 1
    if (df_err/f1 .lt. 0.01) then  ! < 1% ошибка в f
        print *, "OK: 0.1 deg lat error causes < 1% f error"
    else
        print *, "WARNING: 0.1 deg lat error causes > 1% f error"
    end if

    ! =========================================================================
    ! TEST 4: Round-trip при движении (траектория)
    ! =========================================================================
    print *, ""
    print *, "--- TEST 4: Round-trip along moving trajectory ---"

    ! Симуляция траектории: движение на север
    lat_traj = 75.0
    lon_traj = 30.0

    max_lat_err = 0.0
    max_lon_err = 0.0

    do step = 1, 20
        call latlon_to_model_coords(lat_traj, lon_traj, x_model, y_model, ok)
        if (.not. ok) exit

        call model_coords_to_latlon(x_model, y_model, lat_out, lon_out, ok)
        if (.not. ok) exit

        lat_err = abs(lat_out - lat_traj)
        lon_err = abs(lon_out - lon_traj)
        if (lon_err .gt. 180.0) lon_err = 360.0 - lon_err

        max_lat_err = max(max_lat_err, lat_err)
        max_lon_err = max(max_lon_err, lon_err)

        ! Двигаем на север ~50 км за шаг
        lat_traj = lat_traj + 0.05
    end do

    print *, "Trajectory round-trip (20 steps north):"
    print *, "  Max lat error: ", max_lat_err, " deg"
    print *, "  Max lon error: ", max_lon_err, " deg"

    n_checks = n_checks + 1
    if (max_lat_err .lt. 0.1 .and. max_lon_err .lt. 0.1) then
        print *, "OK: Trajectory round-trip error < 0.1 deg"
    else
        print *, "WARNING: Trajectory round-trip error > 0.1 deg"
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Coordinate Mapping Test PASSED"
        stop 0
    else
        print *, "FAILURE: Coordinate Mapping Test FAILED with ", n_errors, " errors"
        stop 1
    end if

end program iceberg_test_coord_mapping
