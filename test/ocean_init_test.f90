! ==============================================================================
! Тест: чтение реалистичных начальных полей океана (Stage 7.7)
!
! Проверяет модуль initial_ocean_reader на продукте
!   data/input/processed/ocean/initial_ts_2020-01-01.nc
! (построен python/ocean/build_initial_ts.py из EN4.2.2 2020-01).
!
! Инварианты:
!   1. Файл существует с размерностями (i=133, j=105, k=18) == модели.
!   2. Все влажные ячейки (kt1>0, k<=kt1) получают конечные, физичные T/S;
!      прочитано ровно sum(kt1) ячеек (счётчик самого reader) == 143422
!      (регрессионный якорь сетки coup1 + продукта 2020-01-01).
!   3. Влажных колонок (kt1>0) == 11067 (все), 10966 (активные i<=132,j<=104).
!   4. Суша (kt1==0) и ячейки ниже дна = 0.0 (никогда NaN).
!   5. Регрессионные якоря: значения нескольких (i,j,k) совпадают с эталоном,
!      зафиксированным при сборке файла.
! Если файл отсутствует — SKIP (stop 0), как в era5_coverage_test.f90.
! ==============================================================================

program ocean_init_test
    use param
    use grid_coupling
    use grid_masks
    use initial_ocean_reader
    implicit none

    real, allocatable :: t1t(:, :, :), t2t(:, :, :), s1t(:, :, :), s2t(:, :, :)
    integer :: i, j, k, n_err, nloaded, n_active_loaded, n_wet_all, n_wet_active
    integer :: n_land_bad, n_wet_bad_range
    logical :: ok, fexists
    real :: eps

    n_err = 0
    eps = 5.0e-4
    print *, "===================================================="
    print *, "  OCEAN INIT TEST (Stage 7.7 realistic T/S)"
    print *, "===================================================="

    call coup1()
    call ikuv()

    allocate (t1t(is1, js1, ks), t2t(is1, js1, ks))
    allocate (s1t(is1, js1, ks), s2t(is1, js1, ks))
    t1t = 0.0; t2t = 0.0; s1t = 0.0; s2t = 0.0

    inquire (file=trim(realistic_ocean_file), exist=fexists)
    if (.not. fexists) then
        print *, "SKIP: realistic ocean file not present"
        print *, "      (run python/ocean/build_initial_ts.py first; gitignored)"
        stop 0
    end if

    call read_initial_ts(t1t, t2t, s1t, s2t, kt1, ok)
    if (.not. ok) then
        print *, "ERROR: read_initial_ts returned ok=.false."
        stop 1
    end if

    ! --- 1. Размерности (проверены внутри reader, фиксируем косвенно) ---
    print '("Model dims: is1=", I0, " js1=", I0, " ks=", I0)', is1, js1, ks

    ! --- 2/3. Wet заполнены, земля нули, диапазоны ---
    nloaded = 0
    n_active_loaded = 0
    n_wet_all = 0
    n_wet_active = 0
    n_land_bad = 0
    n_wet_bad_range = 0
    do j = 1, js1
        do i = 1, is1
            if (kt1(i, j) .gt. 0) then
                n_wet_all = n_wet_all + 1
                if (i .le. is .and. j .le. js) n_wet_active = n_wet_active + 1
            end if
        end do
    end do
    do k = 1, ks
        do j = 1, js1
            do i = 1, is1
                if (kt1(i, j) .gt. 0 .and. k .le. kt1(i, j)) then
                    nloaded = nloaded + 1
                    if (i .le. is .and. j .le. js) n_active_loaded = n_active_loaded + 1
                    if (t1t(i, j, k) .lt. -10.0 .or. t1t(i, j, k) .gt. 40.0 &
                        .or. s1t(i, j, k) .lt. 0.0 .or. s1t(i, j, k) .gt. 0.1) then
                        n_wet_bad_range = n_wet_bad_range + 1
                    end if
                    ! NaN-эпоха: значение должно быть равно самому себе
                    if (t1t(i, j, k) .ne. t1t(i, j, k)) n_wet_bad_range = n_wet_bad_range + 1
                    if (t1t(i, j, k) .ne. t2t(i, j, k)) n_land_bad = n_land_bad + 1
                    if (s1t(i, j, k) .ne. s2t(i, j, k)) n_land_bad = n_land_bad + 1
                else
                    if (t1t(i, j, k) .ne. 0.0 .or. t2t(i, j, k) .ne. 0.0 .or. &
                       s1t(i, j, k) .ne. 0.0 .or. s2t(i, j, k) .ne. 0.0) n_land_bad = n_land_bad + 1
                end if
            end do
        end do
    end do
    print '("Wet columns (all)     = ", I0, " (expect 11067)")', n_wet_all
    print '("Wet columns (active)  = ", I0, " (expect 10966)")', n_wet_active
    print '("Loaded wet cells      = ", I0, " (expect 143422 = sum coup1 kt1)")', nloaded
    print '("Loaded cells (active) = ", I0, " (expect 142081)")', n_active_loaded
    print '("Range/NaN violations  = ", I0)', n_wet_bad_range
    print '("Land-below-bottom bad = ", I0)', n_land_bad
    if (n_wet_all .ne. 11067 .or. n_wet_active .ne. 10966) then
        print *, "ERROR: wet column counts differ from expected"
        n_err = n_err + 1
    end if
    if (nloaded .ne. 143422 .or. n_active_loaded .ne. 142081) then
        print *, "ERROR: unexpected number of loaded T/S cells"
        n_err = n_err + 1
    end if
    if (n_wet_bad_range .ne. 0 .or. n_land_bad .ne. 0) then
        print *, "ERROR: T/S range or land/below-bottom violations"
        n_err = n_err + 1
    end if

    ! --- 4. Регрессионные якоря из эталонного файла (s_exp=-999: skip S check) ---
    call anchor(60, 45, 1, 2.24990, 0.034974, t1t, s1t, n_err, eps, eps, "a1")
    call anchor(30, 80, 1, 1.24920, 0.034870, t1t, s1t, n_err, eps, eps, "a2")
    call anchor(30, 80, 10, 1.90230, -999.0, t1t, s1t, n_err, eps, -999.0, "a3")
    call anchor(10, 10, 1, 6.03257, 0.035064, t1t, s1t, n_err, eps, eps, "a4")
    call anchor(100, 55, 1, -0.55611, 0.034909, t1t, s1t, n_err, eps, eps, "a5")
    call anchor(70, 20, 1, 3.15059, 0.034950, t1t, s1t, n_err, eps, eps, "a6")

    print *, "===================================================="
    if (n_err .eq. 0) then
        print *, "SUCCESS: Realistic ocean T/S initialization validated!"
    else
        print *, "FAILURE: Total validation errors:", n_err
        stop 1
    end if
    print *, "===================================================="

contains

    subroutine anchor(i, j, k, t_exp, s_exp, tp, sp, nerr, tol_t, tol_s, tag)
        integer, intent(in) :: i, j, k
        real, intent(in) :: t_exp, s_exp
        real, intent(in) :: tp(is1, js1, ks), sp(is1, js1, ks)
        integer, intent(inout) :: nerr
        real, intent(in) :: tol_t, tol_s
        character(len=*), intent(in) :: tag
        logical :: t_ok, s_ok
        t_ok = abs(tp(i, j, k) - t_exp) .le. tol_t
        s_ok = (s_exp .lt. -990.0) .or. (abs(sp(i, j, k) - s_exp) .le. tol_s)
        if (.not. (t_ok .and. s_ok)) then
            print '("ERROR: anchor ", A, " at (", I0, ",", I0, ",", I0, &
&              ") T=", F9.5, " (exp ", F9.5, ") S=", F9.6, " (exp ", F9.6, ")")', &
                tag, i, j, k, tp(i, j, k), t_exp, sp(i, j, k), s_exp
            nerr = nerr + 1
        else
            print '("anchor ", A, " (", I0, ",", I0, ",", I0, ") OK  T=", F9.5, " S=", F9.6)', &
                tag, i, j, k, tp(i, j, k), sp(i, j, k)
        end if
    end subroutine anchor

end program ocean_init_test
