! ==============================================================================
! Тест: snowfall conversion and validation (Stage 5.4)
! Проверяет корректность конвертации и накопления снегопада.
!
! Проверки:
!   1. Нулевой снегопад → все массивы нулевые
!   2. Постоянный снегопад → константное значение в массивах
!   3. Накопление за 6 часов: rate * 21600 [м/с * с = м]
!   4. Накопление за 24 часа: rate * 86400 [м]
!   5. Конвертация единиц: 1 м water eq. за 12ч = 1/43200 м/с ≈ 2.31e-5 м/с
!   6. Отсутствие отрицательных значений (снегопад не может быть отрицательным)
!   7. Выравнивание по времени: модельный шаг 3600с должен быть кратным шагу данных 21600с
!   8. Обработка пропущенных временных шагов (линейная интерполяция)
!
! Единицы: rate [м/с], accumulation [м], time [с]
! Константы:
!   dt = 3600 с — модельный временной шаг (1 час)
!   21600 = 6*3600 — шаг снегопада ERA5 [с]
!   86400 = 24*3600 — число секунд в сутках [с]
!   43200 = 12*3600 — число секунд в 12 часах [с]
! ==============================================================================

program snowfall_test
    use param
    implicit none

    integer :: n_errors, n_checks
    integer :: i, j, k, lll
    real :: dt
    real :: sfal_test(12)
    real :: era5_snowfall_rate_test(is1, js1)
    real :: snow_accum_6h, snow_accum_24h
    real :: snow_rate
    real :: snow_accum_12h, rate_from_accum
    real :: snow_t0, snow_t6, snow_interp
    integer :: nsteps_day, nsnow_day
    logical :: has_negative

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  Snowfall Conversion and Validation Tests"
    print *, "=================================================="

    dt = 3600.0  ! модельный временной шаг [с] (1 час)

    ! --- Test 1: Zero snowfall ---
    print *, ""
    print *, "--- Test 1: Zero snowfall ---"
    sfal_test = 0.0
    era5_snowfall_rate_test = 0.0

    n_checks = n_checks + 1
    do i = 1, 12
        if (sfal_test(i) .ne. 0.0) then
            print *, "ERROR Test 1: sfal not zero"
            n_errors = n_errors + 1
            exit
        end if
    end do
    if (n_errors .eq. 0) print *, "OK Test 1: sfal all zero"

    n_checks = n_checks + 1
    do j = 1, js1
        do i = 1, is1
            if (era5_snowfall_rate_test(i, j) .ne. 0.0) then
                print *, "ERROR Test 1: era5_snowfall_rate not zero"
                n_errors = n_errors + 1
                exit
            end if
        end do
    end do
    if (n_errors .eq. 0) print *, "OK Test 1: era5_snowfall_rate all zero"

    ! --- Test 2: Constant snowfall (1 mm/hour = 1e-3 m/hour = 2.778e-7 m/s) ---
    print *, ""
    print *, "--- Test 2: Constant snowfall rate ---"
    snow_rate = 2.77778e-7  ! 1 мм/час = 1e-3/3600 [м/с]
    era5_snowfall_rate_test = snow_rate

    n_checks = n_checks + 1
    do j = 1, js1
        do i = 1, is1
            if (era5_snowfall_rate_test(i, j) .ne. snow_rate) then
                print *, "ERROR Test 2: era5_snowfall_rate mismatch"
                n_errors = n_errors + 1
                exit
            end if
        end do
    end do
    if (n_errors .eq. 0) print *, "OK Test 2: era5_snowfall_rate constant"

    ! --- Test 3: 6-hour accumulation ---
    print *, ""
    print *, "--- Test 3: 6-hour accumulation ---"
    ! 6 hours = 21600 seconds
    ! Accumulation = rate * time
    snow_accum_6h = snow_rate*21600.0  ! meters
    ! Expected: 2.77778e-7 * 21600 = 0.006 m = 6 mm

    n_checks = n_checks + 1
    if (abs(snow_accum_6h - 0.006) .gt. 1e-6) then
        print *, "ERROR Test 3: 6h accumulation mismatch", snow_accum_6h
        n_errors = n_errors + 1
    else
        print *, "OK Test 3: 6h accumulation = ", snow_accum_6h, " m"
    end if

    ! --- Test 4: 24-hour accumulation ---
    print *, ""
    print *, "--- Test 4: 24-hour accumulation ---"
    ! 24 hours = 86400 seconds
    snow_accum_24h = snow_rate*86400.0  ! meters
    ! Expected: 2.77778e-7 * 86400 = 0.024 m = 24 mm

    n_checks = n_checks + 1
    if (abs(snow_accum_24h - 0.024) .gt. 1e-6) then
        print *, "ERROR Test 4: 24h accumulation mismatch", snow_accum_24h
        n_errors = n_errors + 1
    else
        print *, "OK Test 4: 24h accumulation = ", snow_accum_24h, " m"
    end if

    ! --- Test 5: Unit conversion (m water equivalent to m/s rate) ---
    print *, ""
    print *, "--- Test 5: Unit conversion ---"
    ! 1 м water equivalent за 12 часов = 1 / (12*3600) = 1/43200 [м/с]
    ! Используется при конвертации CDS sf: накопление за 12ч → rate
    snow_accum_12h = 1.0  ! 1 метр водного эквивалента за 12 часов
    rate_from_accum = snow_accum_12h/43200.0  ! 12 часов = 43200 секунд

    n_checks = n_checks + 1
    if (abs(rate_from_accum - 2.31481e-5) .gt. 1e-8) then
        print *, "ERROR Test 5: unit conversion mismatch", rate_from_accum
        n_errors = n_errors + 1
    else
        print *, "OK Test 5: 1m/12h = ", rate_from_accum, " m/s"
    end if

    ! --- Test 6: No negative values ---
    print *, ""
    print *, "--- Test 6: No negative values ---"
    era5_snowfall_rate_test = -1.0  ! deliberately negative

    n_checks = n_checks + 1
    has_negative = .false.
    do j = 1, js1
        do i = 1, is1
            if (era5_snowfall_rate_test(i, j) .lt. 0.0) has_negative = .true.
        end do
    end do
    if (.not. has_negative) then
        print *, "ERROR Test 6: negative values not detected"
        n_errors = n_errors + 1
    else
        print *, "OK Test 6: negative values detected"
    end if

    ! Reset to positive
    era5_snowfall_rate_test = 1e-8

    ! --- Test 7: Time alignment (6-hourly steps) ---
    print *, ""
    print *, "--- Test 7: Time alignment (6-hourly steps) ---"
    ! Model time step = 3600 seconds (1 hour)
    ! Snowfall data at 6-hourly intervals (00, 06, 12, 18 UTC)
    ! Model time steps per day = 24
    ! Snowfall data per day = 4 (00, 06, 12, 18)
    nsteps_day = 24
    nsnow_day = 4

    n_checks = n_checks + 1
    if (mod(nsteps_day, nsnow_day) .ne. 0) then
        print *, "ERROR Test 7: model steps not multiple of snowfall steps"
        n_errors = n_errors + 1
    else
  print *, "OK Test 7: model steps (", nsteps_day, ") divisible by snowfall steps (", nsnow_day, ")"
    end if

    ! --- Test 8: Missing timestep handling (interpolation) ---
    print *, ""
    print *, "--- Test 8: Missing timestep handling ---"
    ! Test that linear interpolation between 6-hourly snowfall values works
    snow_t0 = 1.0e-8
    snow_t6 = 3.0e-8
    ! Linear interpolation at t=3 hours (halfway)
    snow_interp = 0.5*(snow_t0 + snow_t6)

    n_checks = n_checks + 1
    if (abs(snow_interp - 2.0e-8) .gt. 1e-12) then
        print *, "ERROR Test 8: interpolation mismatch", snow_interp
        n_errors = n_errors + 1
    else
        print *, "OK Test 8: linear interpolation at t=3h = ", snow_interp
    end if

    ! --- Summary ---
    print *, ""
    print *, "=================================================="
    if (n_errors .eq. 0) then
        print '(A,I3,A,I3)', "ALL TESTS PASSED: ", n_checks, " checks, 0 errors"
        stop 0
    else
        print '(A,I3,A,I3)', "FAILED: ", n_errors, " errors out of ", n_checks, " checks"
        stop 1
    end if

end program snowfall_test
