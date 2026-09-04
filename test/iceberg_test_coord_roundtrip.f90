! ==============================================================================
! Тест: Coordinate Round-Trip Test
! Назначение: Проверка обратного преобразования координат:
!             lat/lon → x/y → lat/lon должно давать исходные значения
!             с точностью < 1e-6 градуса (или физически обоснованный tolerance)
! ==============================================================================

program iceberg_test_coord_roundtrip
    use iceberg_forcing, only: latlon_to_model_coords, model_coords_to_latlon
    use grid_coupling, only: coup1
    use param, only: is, js, is1, js1, fi, dl, ht
    implicit none

    integer :: n_errors, n_checks
    real :: lat_in, lon_in, x_model, y_model, lat_out, lon_out
    real :: lat_err, lon_err
    logical :: ok
    integer :: test_idx

    ! Тестовые точки (lat, lon) в градусах — ВНУТРИ домена модели (Баренцево море ~66-82N, 30-63E)
    real, dimension(4, 2) :: test_points
    real :: max_lat_err, max_lon_err

    n_errors = 0
    n_checks = 0
    max_lat_err = 0.0
    max_lon_err = 0.0

    print *, "=================================================="
    print *, "  COORDINATE ROUND-TRIP TEST"
    print *, "=================================================="

    ! 1. Инициализация модельной сетки
    print *, "Initializing model grid..."
    call coup1()

    ! Тестовые точки (lat, lon) в градусах — внутри домена модели
    test_points(1, :) = (/70.0, 30.0/)     ! Баренцево море
    test_points(2, :) = (/75.0, 30.0/)     ! TEST_11 позиция
    test_points(3, :) = (/76.0, 40.0/)     ! Северо-восток Баренцева моря
    test_points(4, :) = (/72.0, 35.0/)     ! Центральная часть

    do test_idx = 1, 4
        lat_in = test_points(test_idx, 1)
        lon_in = test_points(test_idx, 2)

        print *, "Test point ", test_idx, ": lat_in=", lat_in, " lon_in=", lon_in

        ! Forward: lat/lon → x/y
        call latlon_to_model_coords(lat_in, lon_in, x_model, y_model, ok)
        if (.not. ok) then
            print *, "  ERROR: latlon_to_model_coords failed"
            n_errors = n_errors + 1
            cycle
        end if

        ! Inverse: x/y → lat/lon
        call model_coords_to_latlon(x_model, y_model, lat_out, lon_out, ok)
        if (.not. ok) then
            print *, "  ERROR: model_coords_to_latlon failed"
            n_errors = n_errors + 1
            cycle
        end if

        lat_err = abs(lat_out - lat_in)
        lon_err = abs(lon_out - lon_in)

        ! Нормализация ошибки долготы (учёт периодичности 360°)
        if (lon_err .gt. 180.0) lon_err = 360.0 - lon_err

        print *, "  x_model=", x_model, " y_model=", y_model
        print *, "  lat_out=", lat_out, " lon_out=", lon_out
        print *, "  lat_err=", lat_err, " lon_err=", lon_err

        max_lat_err = max(max_lat_err, lat_err)
        max_lon_err = max(max_lon_err, lon_err)

        n_checks = n_checks + 1
        ! Tolerance: учитываем, что forward projection (lat/lon→x/y) использует
        ! nearest-neighbor на модели (~13.9 км шаг), поэтому ошибка ~0.1 deg.
        ! inverse projection (x/y→lat/lon) через билинейную интерполяцию точна до ~1e-6.
        ! Ожидаемая ошибка round-trip доминируется forward projection.
        if (lat_err .lt. 0.1 .and. lon_err .lt. 0.2) then
            print *, "  OK: Round-trip error within model grid resolution"
        else
            print *, "  WARNING: Round-trip error exceeds model grid resolution"
            n_errors = n_errors + 1
        end if
    end do

    print *, "=================================================="
    print *, "MAX LAT ERROR: ", max_lat_err, " deg"
    print *, "MAX LON ERROR: ", max_lon_err, " deg"
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: COORD ROUND-TRIP TEST PASSED"
        stop 0
    else
        print *, "FAILURE: COORD ROUND-TRIP TEST FAILED"
        stop 1
    end if

end program iceberg_test_coord_roundtrip
