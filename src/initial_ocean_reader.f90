! ==============================================================================
! Модуль: initial_ocean_reader (Stage 7.7)
! Назначение: Чтение реалистичных начальных полей T/S океана из файла
!         data/input/processed/ocean/initial_ts_2020-01-01.nc (продукт
!         python/ocean/build_initial_ts.py на основе EN4.2.2 за 2020-01).
! Единицы: температура [°C], соленость [массовая доля] — те же, что модель.
!         Суша/дно в файле = 0.0 (никогда NaN); wet_mask=1 — вода.
!         Размерности файла: (i=is1, j=js1, k=ks) с ординатой-независимым
!         ПОРЯДКОМ осей (файл пишется xarray в (k,j,i); читаем универсально
!         через dimids) — результат всегда канонический (i,j,k)-массив.
! Переменная окружения: ICEBERG_OCEAN_INIT_FILE — переопределяет путь к файлу
!         (удобно для чувствительных экспериментов без перекомпиляции).
! Поведение при ошибке: ok=.false. (вызывающий init_ocean() откатывается на
! синтетические поля — поведение Stage 7.6C.2 и ранее сохраняется).
! ==============================================================================

module initial_ocean_reader
    use iso_fortran_env, only: real32
    use netcdf
    implicit none

    character(len=*), parameter :: realistic_ocean_file = &
                                   "data/input/processed/ocean/initial_ts_2020-01-01.nc"

contains

    !> Заполнить t1/t2/s1/s2 реалистичными T/S на влажных ячейках (kt>0, k<=kt).
    !> Если файл недоступен или размерности не совпадают — ok=.false.,
    !> массивы НЕ меняются (вызывающий решает про fallback).
    subroutine read_initial_ts(t1o, t2o, s1o, s2o, kt, ok)
        real, intent(inout) :: t1o(:, :, :), t2o(:, :, :)
        real, intent(inout) :: s1o(:, :, :), s2o(:, :, :)
        integer, intent(in) :: kt(:, :)
        logical, intent(out) :: ok

        integer :: ncid, dimid
        integer :: dimid_i, dimid_j, dimid_k
        integer :: ni_file, nj_file, nk_file
        integer :: i, j, k, nloaded
        real(real32), allocatable :: t_arr(:, :, :), s_arr(:, :, :)
        real :: tmin, tmax, smin, smax
        logical :: fexists
        character(len=512) :: env_path

        ok = .false.

        ! Переменная окружения для переопределения пути к файлу
        call get_environment_variable('ICEBERG_OCEAN_INIT_FILE', env_path)
        if (len_trim(env_path) .gt. 0) then
            if (.not. check(nf90_open(trim(env_path), nf90_nowrite, ncid), "nf90_open env")) then
                return
            end if
            print *, "INFO initial_ocean_reader: using ICEBERG_OCEAN_INIT_FILE = ", trim(env_path)
        else
            inquire (file=trim(realistic_ocean_file), exist=fexists)
            if (.not. fexists) then
                print *, "WARN initial_ocean_reader: file not found: ", &
                    trim(realistic_ocean_file), " (synthetic fallback)"
                return
            end if
            if (.not. check(nf90_open(trim(realistic_ocean_file), nf90_nowrite, ncid), &
                            "nf90_open")) return
        end if

        if (.not. check(nf90_inq_dimid(ncid, 'i', dimid_i), "dim i")) then
            call close_nc(ncid); return
        end if
        if (.not. check(nf90_inquire_dimension(ncid, dimid_i, len=ni_file), "dim i len")) then
            call close_nc(ncid); return
        end if
        if (.not. check(nf90_inq_dimid(ncid, 'j', dimid_j), "dim j")) then
            call close_nc(ncid); return
        end if
        if (.not. check(nf90_inquire_dimension(ncid, dimid_j, len=nj_file), "dim j len")) then
            call close_nc(ncid); return
        end if
        if (.not. check(nf90_inq_dimid(ncid, 'k', dimid_k), "dim k")) then
            call close_nc(ncid); return
        end if
        if (.not. check(nf90_inquire_dimension(ncid, dimid_k, len=nk_file), "dim k len")) then
            call close_nc(ncid); return
        end if

        if (ni_file .ne. size(kt, 1) .or. nj_file .ne. size(kt, &
                                                            2) .or. nk_file .ne. size(t1o, 3)) then
            print *, "WARN initial_ocean_reader: dims mismatch file(", &
                ni_file, ", ", nj_file, ", ", nk_file, ") vs model(", &
                size(kt, 1), ", ", size(kt, 2), ", ", size(t1o, 3), ")"
            call close_nc(ncid)
            return
        end if

        allocate (t_arr(ni_file, nj_file, nk_file))
        allocate (s_arr(ni_file, nj_file, nk_file))

        if (.not. check(get_var(ncid, 'temperature_celsius', dimid_i, dimid_j, &
                                dimid_k, ni_file, nj_file, nk_file, t_arr), "get t")) then
            call close_nc(ncid); deallocate (t_arr, s_arr); return
        end if
        if (.not. check(get_var(ncid, 'salinity_mass_fraction', dimid_i, dimid_j, &
                                dimid_k, ni_file, nj_file, nk_file, s_arr), "get s")) then
            call close_nc(ncid); deallocate (t_arr, s_arr); return
        end if

        call close_nc(ncid)

        ! Численная эпоха: NaN/Inf в файле недопустимы (NaN /= NaN)
        if (minval(t_arr) .ne. minval(t_arr) .or. minval(s_arr) .ne. minval(s_arr)) then
            print *, "WARN initial_ocean_reader: NaN in file (synthetic fallback)"
            deallocate (t_arr, s_arr)
            return
        end if
        tmin = minval(t_arr); tmax = maxval(t_arr)
        smin = minval(s_arr); smax = maxval(s_arr)
        if (tmin .lt. -10.0 .or. tmax .gt. 40.0 .or. smin .lt. -0.002 .or. smax .gt. 0.1) then
            print *, "WARN initial_ocean_reader: out-of-range T/S range ", tmin, tmax, &
                smin, smax, " (synthetic fallback)"
            deallocate (t_arr, s_arr)
            return
        end if

        ! Заполнение: вода — из файла, суша/ниже дна — 0.0 (конвенция модели)
        nloaded = 0
        do k = 1, size(t1o, 3)
            do j = 1, size(t1o, 2)
                do i = 1, size(t1o, 1)
                    if (kt(i, j) .gt. 0 .and. k .le. kt(i, j)) then
                        t1o(i, j, k) = t_arr(i, j, k)
                        t2o(i, j, k) = t_arr(i, j, k)
                        s1o(i, j, k) = s_arr(i, j, k)
                        s2o(i, j, k) = s_arr(i, j, k)
                        nloaded = nloaded + 1
                    else
                        t1o(i, j, k) = 0.0
                        t2o(i, j, k) = 0.0
                        s1o(i, j, k) = 0.0
                        s2o(i, j, k) = 0.0
                    end if
                end do
            end do
        end do
        print '("INFO initial_ocean_reader: read ", I0, " wet T/S cells from ", A)', &
            nloaded, trim(realistic_ocean_file)
        print '("     T range [C]   : ", F9.4, " .. ", F9.4)', tmin, tmax
        print '("     S range [frac] : ", F9.6, " .. ", F9.6)', smin, smax

        deallocate (t_arr, s_arr)
        ok = .true.
    end subroutine read_initial_ts

!> Прочитать переменную в канонический (i,j,k)-массив независимо от порядка
    !> осей в файле (xarray пишет (k,j,i); другие источники могут писать иначе).
    !> Возвращает статус netcdf (nf90_noerr = 0 при успехе).
    integer function get_var(ncid, varname, dimid_i, dimid_j, dimid_k, &
                             ni, nj, nk, arr) result(st)
        integer, intent(in) :: ncid
        character(len=*), intent(in) :: varname
        integer, intent(in) :: dimid_i, dimid_j, dimid_k
        integer, intent(in) :: ni, nj, nk
        real(real32), intent(out) :: arr(:, :, :)

        integer :: varid, nd
        integer :: vidims(4), lengths(4), pos(4)
        integer :: i, j, k, p
        real(real32), allocatable :: buf(:, :, :)

        st = nf90_inq_varid(ncid, trim(varname), varid)
        if (st .ne. nf90_noerr) return
        st = nf90_inquire_variable(ncid, varid, ndims=nd, dimids=vidims)
        if (st .ne. nf90_noerr .or. nd .ne. 3) then
            if (st .eq. nf90_noerr) st = nf90_ebaddim
            return
        end if
        do p = 1, nd
            st = nf90_inquire_dimension(ncid, vidims(p), len=lengths(p))
            if (st .ne. nf90_noerr) return
            pos(p) = 0
            if (vidims(p) .eq. dimid_i) pos(p) = 1
            if (vidims(p) .eq. dimid_j) pos(p) = 2
            if (vidims(p) .eq. dimid_k) pos(p) = 3
        end do
        if (any(pos .eq. 0)) then
            st = nf90_ebaddim                       ! все 3 оси обязаны быть
            return
        end if
        if (lengths(pos(1)) .ne. ni .or. lengths(pos(2)) .ne. nj .or. &
            lengths(pos(3)) .ne. nk) then
            st = nf90_ebaddim
            return
        end if

        allocate (buf(lengths(1), lengths(2), lengths(3)))
        st = nf90_get_var(ncid, varid, buf)
        if (st .ne. nf90_noerr) then
            deallocate (buf)
            return
        end if

        ! перенос buf(f1,f2,f3) -> arr(i,j,k), где f-индекс каждой файловой оси
        ! равен каноническому индексу своей оси (pos): pos==1 -> i, 2 -> j, 3 -> k
        do k = 1, nk
            do j = 1, nj
                do i = 1, ni
                    arr(i, j, k) = buf(cindex(pos(1), i, j, k), &
                                       cindex(pos(2), i, j, k), &
                                       cindex(pos(3), i, j, k))
                end do
            end do
        end do
        deallocate (buf)
        st = nf90_noerr
    end function get_var

    !> Канонический индекс оси p (1=i, 2=j, 3=k).
    pure integer function cindex(p, i, j, k) result(c)
        integer, intent(in) :: p, i, j, k
        select case (p)
        case (1); c = i
        case (2); c = j
        case (3); c = k
        case default; c = 1
        end select
    end function cindex

    !> Проверка статуса netcdf c печатью ошибки.
    logical function check(st, what) result(r)
        integer, intent(in) :: st
        character(len=*), intent(in) :: what
        if (st .ne. nf90_noerr) then
            print *, "WARN initial_ocean_reader: ", trim(what), ": ", nf90_strerror(st)
            r = .false.
        else
            r = .true.
        end if
    end function check

    subroutine close_nc(ncid)
        integer, intent(in) :: ncid
        integer :: st
        st = nf90_close(ncid)
    end subroutine close_nc

end module initial_ocean_reader
