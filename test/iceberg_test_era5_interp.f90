! ==============================================================================
! Тест: ERA5 Interpolation Test
! Назначение: Проверка билинейной интерполяции ERA5 полей,
!             включая обработку долготы (0..360 vs -180..180) и порядка широты
! ==============================================================================

program iceberg_test_era5_interp
    use netcdf_input, only: era5_open, era5_bilinear2d, era5_is_open, &
                            era5_find_time_index, era5_u10, era5_v10, &
                            era5_t2m, era5_d2m, era5_tcc, era5_msl, &
                            era5_snowfall, era5_lat, era5_lon, era5_time
    implicit none

    integer :: n_errors, n_checks
    integer :: ios, tidx
    real(8) :: lat8, lon8, time_sec8, val8
    logical :: interp_ok

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  ERA5 INTERPOLATION TEST"
    print *, "=================================================="

    ! 1. Открытие ERA5 файла
    print *, "Opening ERA5 forcing..."
    call era5_open('data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc', ios)
    if (ios .ne. 0) then
        print *, "ERROR: Failed to open ERA5 file"
        stop 1
    end if

    print *, "ERA5 lat range: ", era5_lat(1), " .. ", era5_lat(size(era5_lat))
    print *, "ERA5 lon range: ", era5_lon(1), " .. ", era5_lon(size(era5_lon))
    print *, "ERA5 time range: ", era5_time(1), " .. ", era5_time(size(era5_time))

    ! 2. Тест 1: Точка внутри домена (Баренцево море)
    print *, ""
    print *, "Test 1: Point inside domain (Barents Sea ~75N, 30E)"
    lat8 = 75.0_8
    lon8 = 30.0_8
    time_sec8 = era5_time(1)

    call era5_find_time_index(time_sec8, tidx)
    print *, "  Time index: ", tidx

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_v10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: v10 interpolation failed"
        n_errors = n_errors + 1
    else
        print *, "  v10 = ", val8, " m/s"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_t2m(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: t2m interpolation failed"
        n_errors = n_errors + 1
    else
        print *, "  t2m = ", val8, " K (", val8 - 273.15_8, " C)"
    end if
    n_checks = n_checks + 1

    ! 3. Тест 2: Долгота -180° (должна работать через wrap-around)
    print *, ""
    print *, "Test 2: Longitude -180° (equivalent to 180°)"
    lat8 = 70.0_8
    lon8 = -180.0_8
    time_sec8 = era5_time(1)

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed at lon=-180"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s (OK)"
    end if
    n_checks = n_checks + 1

    ! 4. Тест 3: Долгота 180°
    print *, ""
    print *, "Test 3: Longitude 180°"
    lat8 = 70.0_8
    lon8 = 180.0_8

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed at lon=180"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s (OK)"
    end if
    n_checks = n_checks + 1

    ! 5. Тест 4: Долгота 0°
    print *, ""
    print *, "Test 4: Longitude 0° (Prime Meridian)"
    lat8 = 70.0_8
    lon8 = 0.0_8

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed at lon=0"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s (OK)"
    end if
    n_checks = n_checks + 1

    ! 6. Тест 5: Долгота 359.9° (near dateline)
    print *, ""
    print *, "Test 5: Longitude 359.9° (near dateline)"
    lat8 = 70.0_8
    lon8 = 359.9_8

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed at lon=359.9"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s (OK)"
    end if
    n_checks = n_checks + 1

    ! 7. Тест 6: Долгота -0.1° (just west of prime meridian)
    print *, ""
    print *, "Test 6: Longitude -0.1° (just west of prime meridian)"
    lat8 = 70.0_8
    lon8 = -0.1_8

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        print *, "  ERROR: u10 interpolation failed at lon=-0.1"
        n_errors = n_errors + 1
    else
        print *, "  u10 = ", val8, " m/s (OK)"
    end if
    n_checks = n_checks + 1

    ! 8. Тест 7: Широта вне диапазона (должна вернуть .false.)
    print *, ""
    print *, "Test 7: Latitude outside domain (should fail gracefully)"
    lat8 = 50.0_8  ! ниже 63°N (мин в ERA5 файле)
    lon8 = 30.0_8

    interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
    if (interp_ok) then
        print *, "  ERROR: Expected failure for lat=50, got interp_ok=.true."
        n_errors = n_errors + 1
    else
        print *, "  OK: Correctly returned .false. for out-of-range latitude"
    end if
    n_checks = n_checks + 1

    ! 9. Тест 8: Проверка порядка широты (ERA5 хранит убывающую, мы переворачиваем)
    print *, ""
    print *, "Test 8: Latitude ordering verification"
    print *, "  era5_lat(1) = ", era5_lat(1), " (should be min, increasing)"
    print *, "  era5_lat(end) = ", era5_lat(size(era5_lat)), " (should be max)"
    if (era5_lat(1) .lt. era5_lat(size(era5_lat))) then
        print *, "  OK: Latitude array is monotonically increasing"
    else
        print *, "  ERROR: Latitude array not increasing"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! 10. Тест 9: Все переменные интерполируются
    print *, ""
    print *, "Test 9: All ERA5 variables interpolate at test point"
    lat8 = 75.0_8
    lon8 = 30.0_8

    interp_ok = era5_bilinear2d(era5_t2m(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        n_errors = n_errors + 1
        print *, "  t2m FAIL"
    else
        print *, "  t2m OK"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_d2m(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        n_errors = n_errors + 1
        print *, "  d2m FAIL"
    else
        print *, "  d2m OK"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_tcc(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        n_errors = n_errors + 1
        print *, "  tcc FAIL"
    else
        print *, "  tcc OK"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_msl(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        n_errors = n_errors + 1
        print *, "  msl FAIL"
    else
        print *, "  msl OK"
    end if
    n_checks = n_checks + 1

    interp_ok = era5_bilinear2d(era5_snowfall(:, :, tidx), lat8, lon8, val8)
    if (.not. interp_ok) then
        n_errors = n_errors + 1
        print *, "  snowfall FAIL"
    else
        print *, "  snowfall OK"
    end if
    n_checks = n_checks + 1

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: ERA5 INTERPOLATION TEST PASSED"
        stop 0
    else
        print *, "FAILURE: ERA5 INTERPOLATION TEST FAILED"
        stop 1
    end if

end program iceberg_test_era5_interp
