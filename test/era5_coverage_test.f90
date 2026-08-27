! ==============================================================================
! Тест: полное покрытие модели расширенными данными ERA5 (Stage 7.6C.2)
!
! Проверяет, что реальный канал чтения+интерполяции ERA5 (era5_open /
! era5_bilinear2d из netcdf_input.f90) покрывает ВСЕ требуемые точки форсинга
! нового расширенного файла:
!
!   data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc
!
! Требуемые точки = активные влажные ячейки (i<=is, j<=js, kt1/=0) — тот же
! набор, который посещает era5_wind в main.f90. Точка считается покрытой,
! если era5_bilinear2d возвращает ok=.true. (широта внутри диапазона файла;
! вариант "точка вне широты" -> обнуление — главный случай экстраполяции).
!
! Проверяемые инварианты:
!   1. Файл открывается; размерности = 109 lat, 283 lon, >=13 time.
!   2. era5_lat после чтения — возрастающая (63 -> 90), lon возрастающая.
!   3. Покрытие: 0 точек вне диапазона широты среди активных влажных ячеек.
!   4. Файл не содержит NaN/Inf (эпоха minval != maxval при наличии).
! ==============================================================================

program era5_coverage_test
    use param
    use grid_coupling
    use grid_masks
    use netcdf_input
    implicit none

    integer :: i, j, ios, tidx, nbad, n_req, n_err
    real(8) :: value
    real :: lat, lon
    logical :: ok
    character(len=256) :: era5_file

    n_err = 0
    print *, "===================================================="
    print *, "  ERA5 COVERAGE TEST (Stage 7.6C.2)"
    print *, "===================================================="

    ! --- Сетка реального бассейна (fi/dl из KOORD.DAT, kt1 из hhh.bar) ---
    call coup1()
    call ikuv()

    era5_file = 'data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc'
    call era5_open(trim(era5_file), ios)
    if (ios .ne. 0) then
        print *, "SKIP: ERA5 file not open (run download_era5.py + merge_snowfall.py first)."
        stop 0
    end if
    print *, "ERA5 read OK: ntime=", era5_ntime, " nlat=", era5_nlat, " nlon=", era5_nlon

    ! --- 1. Размерности ---
    if (era5_nlat .ne. 109 .or. era5_nlon .ne. 283) then
        print *, "ERROR: unexpected ERA5 dimensions", era5_nlat, era5_nlon
        n_err = n_err + 1
    end if
    if (era5_ntime .lt. 13) then
        print *, "ERROR: too few ERA5 time steps for a 3-day run", era5_ntime
        n_err = n_err + 1
    end if

    ! --- 2. Координатные соглашения (после переворота) ---
    if (era5_lat(1) .ge. era5_lat(era5_nlat)) then
        print *, "ERROR: era5_lat not increasing after flip."
        n_err = n_err + 1
    else
        print '("ERA5 lat increasing: ", F7.2, " .. ", F7.2)', &
            era5_lat(1), era5_lat(era5_nlat)
    end if
    if (era5_lon(1) .ge. era5_lon(era5_nlon)) then
        print *, "ERROR: era5_lon not increasing."
        n_err = n_err + 1
    else
        print '("ERA5 lon increasing: ", F7.2, " .. ", F7.2)', &
            era5_lon(1), era5_lon(era5_nlon)
    end if

    ! --- 3. Покрытие всех требуемых точек форсинга ---
    tidx = 1
    nbad = 0
    n_req = 0
    do j = 1, js1
        do i = 1, is1
            ! Активная влажная ячейка (i<=is, j<=js, kt1/=0)
            if (i .gt. is .or. j .gt. js) cycle
            if (kt1(i, j) .eq. 0) cycle
            n_req = n_req + 1
            lat = real(fi(i, j), 4)
            lon = real(dl(i, j), 4)
            ok = era5_bilinear2d(era5_msl(:, :, tidx), real(lat, 8), real(lon, 8), value)
            if (.not. ok) nbad = nbad + 1
        end do
    end do
    print '("Required forcing points = ", I6)', n_req
    print '("Uncovered (lat out of range) = ", I6)', nbad
    if (nbad .ne. 0 .or. n_req .ne. 10966) then
        print *, "ERROR: forcing coverage incomplete (expect 10966 required, 0 uncovered)."
        n_err = n_err + 1
    end if

    ! --- 4. Отсутствие NaN/Inf в первом срезе msl/t2m (численная эпоха) ---
    if (minval(era5_msl(:, :, tidx)) .ne. minval(era5_msl(:, :, tidx))) then
        print *, "ERROR: NaN detected in msl field."
        n_err = n_err + 1
    end if
    if (minval(era5_t2m(:, :, tidx)) .ne. minval(era5_t2m(:, :, tidx))) then
        print *, "ERROR: NaN detected in t2m field."
        n_err = n_err + 1
    end if
    call era5_diag()

    print *, "===================================================="
    if (n_err .eq. 0) then
        print *, "SUCCESS: Full ERA5 forcing coverage validated!"
    else
        print *, "FAILURE: Total validation errors: ", n_err
        stop 1
    end if
    print *, "===================================================="

end program era5_coverage_test
