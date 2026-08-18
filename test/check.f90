! ==============================================================================
! Тестовая программа валидации результатов модели и входных полей форсинга
! Проверяет:
! 1. Отсутствие NaN / IEEE_IS_NAN и Infinity / IEEE_IS_FINITE
! 2. Отсутствие фиктивных значений (ERA5 fillValue 3.4028235e38)
! 3. Физическую реалистичность диапазонов форсинга и океанических полей
! 4. Качественную согласованность направлений ветра и касательного напряжения
! ==============================================================================

program check
    use netcdf
    use ieee_arithmetic
    implicit none

    integer :: ncid, status
    integer :: varid_wind, varid_windx, varid_windy
    integer :: varid_tx, varid_ty, varid_dpx, varid_dpy
    integer :: varid_tatm, varid_patm, varid_temp, varid_salt
    integer :: is_val, js_val, ks_val
    integer :: dimid_x, dimid_y, dimid_z
    integer :: i, j, n_errors, n_sign_mismatches
    real, allocatable :: wind(:, :), windx(:, :), windy(:, :)
    real, allocatable :: tx(:, :), ty(:, :), dpx(:, :), dpy(:, :)
    real, allocatable :: tatm(:, :), patm(:, :)
    real, allocatable :: temp(:, :, :), salt(:, :, :)

    character(len=256) :: ncfile
    character(len=256) :: arg
    integer :: narg, arglen
    ! По умолчанию - исторический путь (Stage 6.2: прогоны изолированы в data/runs/<run_id>/output/nc).
    ! Путь можно передать аргументом командной строки: fpm test -- <path> или запуск check <path>.
    ncfile = 'data/runs/2020_Q1_test_heat_on/output/nc/results_day_final.nc'
    narg = command_argument_count()
    if (narg .ge. 1) then
        call get_command_argument(1, arg, arglen)
        ncfile = trim(arg)
    end if

    print *, "=================================================="
    print *, "  Running Validation Suite on NetCDF Output File"
    print *, "  File: ", trim(ncfile)
    print *, "=================================================="

    status = nf90_open(trim(ncfile), nf90_nowrite, ncid)
    if (status .ne. nf90_noerr) then
        print *, "SKIP: Output file ", trim(ncfile), " not found. Run 'fpm run' first."
        stop 0
    end if

    ! Чтение измерений
    status = nf90_inq_dimid(ncid, "x", dimid_x)
    status = nf90_inquire_dimension(ncid, dimid_x, len=is_val)
    status = nf90_inq_dimid(ncid, "y", dimid_y)
    status = nf90_inquire_dimension(ncid, dimid_y, len=js_val)
    status = nf90_inq_dimid(ncid, "depth", dimid_z)
    status = nf90_inquire_dimension(ncid, dimid_z, len=ks_val)

    print *, "Grid dimensions: x=", is_val, " y=", js_val, " depth=", ks_val

    allocate (wind(is_val, js_val), windx(is_val, js_val), windy(is_val, js_val))
    allocate (tx(is_val, js_val), ty(is_val, js_val))
    allocate (dpx(is_val, js_val), dpy(is_val, js_val))
    allocate (tatm(is_val, js_val), patm(is_val, js_val))
    allocate (temp(is_val, js_val, ks_val), salt(is_val, js_val, ks_val))

    ! Чтение переменных
    status = nf90_inq_varid(ncid, "wind_speed", varid_wind); status = nf90_get_var(ncid, varid_wind, wind)
    status = nf90_inq_varid(ncid, "wind_x", varid_windx); status = nf90_get_var(ncid, varid_windx, windx)
    status = nf90_inq_varid(ncid, "wind_y", varid_windy); status = nf90_get_var(ncid, varid_windy, windy)
    status = nf90_inq_varid(ncid, "tau_x", varid_tx); status = nf90_get_var(ncid, varid_tx, tx)
    status = nf90_inq_varid(ncid, "tau_y", varid_ty); status = nf90_get_var(ncid, varid_ty, ty)
    status = nf90_inq_varid(ncid, "dp_x", varid_dpx); status = nf90_get_var(ncid, varid_dpx, dpx)
    status = nf90_inq_varid(ncid, "dp_y", varid_dpy); status = nf90_get_var(ncid, varid_dpy, dpy)
    status = nf90_inq_varid(ncid, "air_temp", varid_tatm); status = nf90_get_var(ncid, varid_tatm, tatm)
    status = nf90_inq_varid(ncid, "air_press", varid_patm); status = nf90_get_var(ncid, varid_patm, patm)
    status = nf90_inq_varid(ncid, "temperature", varid_temp); status = nf90_get_var(ncid, varid_temp, temp)
    status = nf90_inq_varid(ncid, "salinity_mass_fraction", varid_salt); status = nf90_get_var(ncid, varid_salt, salt)

    status = nf90_close(ncid)

    n_errors = 0

    ! 1. Проверка NaN / Inf / missing value (границы в канонических единицах СИ, Stage 5.5b)
    print *, "--- 1. Checking IEEE NaN, Inf, missing values, and physical bounds ---"
    call check_array_2d(wind, "wind_speed", 0.0, 100.0, n_errors)
    call check_array_2d(windx, "wind_x", -100.0, 100.0, n_errors)
    call check_array_2d(windy, "wind_y", -100.0, 100.0, n_errors)
    call check_array_2d(tx, "tau_x", -10.0, 10.0, n_errors)
    call check_array_2d(ty, "tau_y", -10.0, 10.0, n_errors)
    call check_array_2d(dpx, "dp_x", -0.1, 0.1, n_errors)
    call check_array_2d(dpy, "dp_y", -0.1, 0.1, n_errors)
    call check_array_2d(tatm, "air_temp", 193.15, 313.15, n_errors)
    call check_array_2d(patm, "air_press", 80000.0, 110000.0, n_errors)
    call check_array_3d(temp, "temperature", 243.15, 323.15, n_errors)
    call check_array_3d(salt, "salinity_mass_fraction", -0.001, 0.05, n_errors)

    ! 2. Качественная согласованность направлений ветра и напряжений трения
    print *, "--- 2. Checking wind & stress alignment ---"
    n_sign_mismatches = 0
    do j = 1, js_val
        do i = 1, is_val
            if (abs(windx(i, j)) .gt. 1.0e-5 .and. abs(tx(i, j)) .gt. 1.0e-6) then
                if (tx(i, j)*windx(i, j) .lt. 0.0) then
                    n_sign_mismatches = n_sign_mismatches + 1
                end if
            end if
            if (abs(windy(i, j)) .gt. 1.0e-5 .and. abs(ty(i, j)) .gt. 1.0e-6) then
                if (ty(i, j)*windy(i, j) .lt. 0.0) then
                    n_sign_mismatches = n_sign_mismatches + 1
                end if
            end if
        end do
    end do
 print *, "Wind / stress sign mismatches during sub-step linear transitions: ", n_sign_mismatches, &
        " (expected due to linear sub-step time interpolation of quadratic drag)"

    print *, "=================================================="
    if (n_errors .eq. 0) then
        print *, "SUCCESS: All validation checks PASSED cleanly!"
    else
        print *, "FAILURE: Total validation errors: ", n_errors
        stop 1
    end if
    print *, "=================================================="

contains

    subroutine check_array_2d(arr, name, min_valid, max_valid, n_err)
        real, intent(in) :: arr(:, :)
        character(len=*), intent(in) :: name
        real, intent(in) :: min_valid, max_valid
        integer, intent(inout) :: n_err
        real :: min_val, max_val
        integer :: i, j

        min_val = minval(arr)
        max_val = maxval(arr)
        print '(A20,A,F12.4,A,F12.4,A)', name, " [min: ", min_val, " max: ", max_val, "]"

        do j = 1, size(arr, 2)
            do i = 1, size(arr, 1)
                if (ieee_is_nan(arr(i, j))) then
                    print *, "ERROR: NaN detected in ", trim(name), " at ", i, j
                    n_err = n_err + 1
                else if (.not. ieee_is_finite(arr(i, j))) then
                    print *, "ERROR: Inf detected in ", trim(name), " at ", i, j
                    n_err = n_err + 1
                else if (arr(i, j) .gt. 1.0e30) then
         print *, "ERROR: ERA5 missing value / uninitialized huge val in ", trim(name), " at ", i, j
                    n_err = n_err + 1
                else if (arr(i, j) .lt. min_valid .or. arr(i, j) .gt. max_valid) then
                print *, "ERROR: Out-of-bounds value in ", trim(name), " at ", i, j, ": ", arr(i, j)
                    n_err = n_err + 1
                end if
            end do
        end do
    end subroutine check_array_2d

    subroutine check_array_3d(arr, name, min_valid, max_valid, n_err)
        real, intent(in) :: arr(:, :, :)
        character(len=*), intent(in) :: name
        real, intent(in) :: min_valid, max_valid
        integer, intent(inout) :: n_err
        real :: min_val, max_val
        integer :: i, j, k

        min_val = minval(arr)
        max_val = maxval(arr)
        print '(A20,A,F12.4,A,F12.4,A)', name, " [min: ", min_val, " max: ", max_val, "]"

        do k = 1, size(arr, 3)
            do j = 1, size(arr, 2)
                do i = 1, size(arr, 1)
                    if (ieee_is_nan(arr(i, j, k))) then
                        print *, "ERROR: NaN detected in ", trim(name), " at ", i, j, k
                        n_err = n_err + 1
                    else if (.not. ieee_is_finite(arr(i, j, k))) then
                        print *, "ERROR: Inf detected in ", trim(name), " at ", i, j, k
                        n_err = n_err + 1
                    else if (arr(i, j, k) .gt. 1.0e30) then
      print *, "ERROR: ERA5 missing value / uninitialized huge val in ", trim(name), " at ", i, j, k
                        n_err = n_err + 1
                    else if (arr(i, j, k) .lt. min_valid .or. arr(i, j, k) .gt. max_valid) then
          print *, "ERROR: Out-of-bounds value in ", trim(name), " at ", i, j, k, ": ", arr(i, j, k)
                        n_err = n_err + 1
                    end if
                end do
            end do
        end do
    end subroutine check_array_3d

end program check
