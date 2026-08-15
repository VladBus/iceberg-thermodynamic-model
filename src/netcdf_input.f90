! ==============================================================================
! Модуль: netcdf_input
! Назначение: Чтение атмосферного форсинга ERA5 из NetCDF-файлов (CDS).
!             Отвечает за открытие файла, проверку метаданных, чтение
!             координат/времени и переменных u10/v10/msl/t2m.
! Физика: Чистый слой ввода данных. НЕ выполняет физической интерполяции на
!         модельную сетку и НЕ конвертирует единицы в массивы модели —
!         это делают последующие модули (wind_forcing, thermodynamics).
!         Единственная функция модуля — доставить исходные ERA5-поля в память.
! Ответственность: Валидация NetCDF-файла (размерности, единицы, порядок
!                  координат), чтение данных, диагностический вывод диапазонов,
!                  подготовка временного интерфейса.
! Единицы: Внутри модуля сохраняются ИСХОДНЫЕ единицы ERA5:
!          u10/v10 [m s-1], t2m [K], msl [Pa], time [s since 1970-01-01].
!          Преобразование в СГС/смешанную систему модели происходит вне модуля.
! ==============================================================================

module netcdf_input
    use netcdf
    implicit none

    ! ERA5-поля в исходных единицах. Размеры определяются по факту из файла.
    integer :: era5_ntime = 0, era5_nlat = 0, era5_nlon = 0
    real(8), allocatable :: era5_time(:)       ! [s since 1970-01-01]
    real(8), allocatable :: era5_lat(:)        ! [degrees_north]
    real(8), allocatable :: era5_lon(:)        ! [degrees_east]
    real(4), allocatable :: era5_u10(:, :, :)  ! [m s-1] (nlat, nlon, ntime)
    real(4), allocatable :: era5_v10(:, :, :)  ! [m s-1]
    real(4), allocatable :: era5_t2m(:, :, :)  ! [K]
    real(4), allocatable :: era5_msl(:, :, :)  ! [Pa]
    real(4) :: era5_fill = 3.4028235e38        ! заполнитель/нет данных (ERA5 GRIB missing)
    logical :: era5_lat_decreasing = .false.   ! флаг направления координаты latitude
    logical :: era5_is_open = .false.          ! открыт ли файл

contains

    ! ==========================================================================
    ! Открытие файла, чтение размерностей, координат, времени и всех переменных.
    ! При любой ошибке печатает понятное сообщение и возвращает status != 0.
    ! ==========================================================================
    subroutine era5_open(filename, status)
        character(len=*), intent(in) :: filename
        integer, intent(out) :: status

        integer :: ncid, varid, dimid
        integer :: ntime, nlat, nlon
        integer :: i
        real(8), allocatable :: lat_tmp(:), lon_tmp(:)
        integer :: nf_status

        status = 0

        ! --- Открытие файла ---
        nf_status = nf90_open(trim(filename), nf90_nowrite, ncid)
        if (.not. nc_input_ok(nf_status, 'open', filename=filename)) then
            status = 1
            return
        end if

        ! --- Чтение размерностей ---
        nf_status = nf90_inq_dimid(ncid, 'valid_time', dimid)
        if (nf_status .ne. nf90_noerr) nf_status = nf90_inq_dimid(ncid, 'time', dimid)
        if (.not. nc_input_ok(nf_status, 'inquire time dimension', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_inquire_dimension(ncid, dimid, len=ntime)
        if (.not. nc_input_ok(nf_status, 'read time dimension size', filename=filename)) then
            status = 1
            goto 999
        end if

        nf_status = nf90_inq_dimid(ncid, 'latitude', dimid)
        if (.not. nc_input_ok(nf_status, 'inquire latitude dimension', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_inquire_dimension(ncid, dimid, len=nlat)
        if (.not. nc_input_ok(nf_status, 'read latitude dimension size', filename=filename)) then
            status = 1
            goto 999
        end if

        nf_status = nf90_inq_dimid(ncid, 'longitude', dimid)
        if (.not. nc_input_ok(nf_status, 'inquire longitude dimension', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_inquire_dimension(ncid, dimid, len=nlon)
        if (.not. nc_input_ok(nf_status, 'read longitude dimension size', filename=filename)) then
            status = 1
            goto 999
        end if

        if (ntime .le. 0 .or. nlat .le. 0 .or. nlon .le. 0) then
            print *, "NetCDF ERROR: file = ", trim(filename), &
                     " has non-positive dimensions: ", ntime, nlat, nlon
            status = 1
            goto 999
        end if

        era5_ntime = ntime
        era5_nlat = nlat
        era5_nlon = nlon

        ! --- Выделение памяти ---
        if (allocated(era5_time)) deallocate (era5_time)
        if (allocated(era5_lat)) deallocate (era5_lat)
        if (allocated(era5_lon)) deallocate (era5_lon)
        if (allocated(era5_u10)) deallocate (era5_u10)
        if (allocated(era5_v10)) deallocate (era5_v10)
        if (allocated(era5_t2m)) deallocate (era5_t2m)
        if (allocated(era5_msl)) deallocate (era5_msl)
        allocate (era5_time(ntime), era5_lat(nlat), era5_lon(nlon), &
                  era5_u10(nlat, nlon, ntime), era5_v10(nlat, nlon, ntime), &
                  era5_t2m(nlat, nlon, ntime), era5_msl(nlat, nlon, ntime))
        allocate (lat_tmp(nlat), lon_tmp(nlon))

        ! --- Чтение времени ---
        nf_status = nf90_inq_varid(ncid, 'valid_time', varid)
        if (nf_status .ne. nf90_noerr) nf_status = nf90_inq_varid(ncid, 'time', varid)
        if (.not. nc_input_ok(nf_status, 'inquire time variable', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_get_var(ncid, varid, era5_time)
        if (.not. nc_input_ok(nf_status, 'read time values', filename=filename)) then
            status = 1
            goto 999
        end if
        ! Файлы CDS хранят время как int64; фортранный nf90_get_var сам конвертит
        ! в real(8). Диапазон значений (~1.58e9 s) представим в real(8) точно.

        ! --- Чтение координат latitude ---
        nf_status = nf90_inq_varid(ncid, 'latitude', varid)
        if (.not. nc_input_ok(nf_status, 'inquire latitude variable', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_get_var(ncid, varid, lat_tmp)
        if (.not. nc_input_ok(nf_status, 'read latitude values', filename=filename)) then
            status = 1
            goto 999
        end if
        ! ERA5 хранит latitude как убывающую (90..-90). Интерполяция в дальнейшем
        ! работает по возрастающей координате, поэтому при необходимости переворачиваем.
        if (lat_tmp(1) .gt. lat_tmp(nlat)) then
            era5_lat_decreasing = .true.
            do i = 1, nlat
                era5_lat(i) = lat_tmp(nlat - i + 1)
            end do
        else
            era5_lat_decreasing = .false.
            era5_lat = lat_tmp
        end if

        ! --- Чтение координат longitude ---
        nf_status = nf90_inq_varid(ncid, 'longitude', varid)
        if (.not. nc_input_ok(nf_status, 'inquire longitude variable', filename=filename)) then
            status = 1
            goto 999
        end if
        nf_status = nf90_get_var(ncid, varid, lon_tmp)
        if (.not. nc_input_ok(nf_status, 'read longitude values', filename=filename)) then
            status = 1
            goto 999
        end if
        if (lon_tmp(1) .gt. lon_tmp(nlon)) then
            print *, "NetCDF ERROR: longitude not monotonically increasing, cannot handle."
            status = 1
            goto 999
        end if
        era5_lon = lon_tmp

        ! --- Чтение переменных (с проверкой присутствия) ---
        call era5_read_var(ncid, 'u10', era5_u10, status, filename)
        if (status .ne. 0) goto 999
        call era5_read_var(ncid, 'v10', era5_v10, status, filename)
        if (status .ne. 0) goto 999
        call era5_read_var(ncid, 't2m', era5_t2m, status, filename)
        if (status .ne. 0) goto 999
        call era5_read_var(ncid, 'msl', era5_msl, status, filename)
        if (status .ne. 0) goto 999

        era5_is_open = .true.
        nf_status = nf90_close(ncid)
        if (.not. nc_input_ok(nf_status, 'close', filename=filename)) then
            status = 1
            return
        end if

        deallocate (lat_tmp, lon_tmp)
        print *, "ERA5 OK: ", trim(filename), " ntime=", era5_ntime, &
                 " nlat=", era5_nlat, " nlon=", era5_nlon
        return

999     continue
        nf_status = nf90_close(ncid)
        status = 1
        if (allocated(lat_tmp)) deallocate (lat_tmp)
        if (allocated(lon_tmp)) deallocate (lon_tmp)
        return
    end subroutine era5_open

    ! ==========================================================================
    ! Чтение одной переменной целиком в массив (nlat, nlon, ntime).
    ! Учитывает переворот latitude: файл хранит время первым измерением,
    ! поэтому читаем через временную копию и разворачиваем lat.
    ! ==========================================================================
    subroutine era5_read_var(ncid, varname, arr, status, filename)
        integer, intent(in) :: ncid
        character(len=*), intent(in) :: varname
        real(4), intent(out) :: arr(:, :, :)
        integer, intent(out) :: status
        character(len=*), intent(in) :: filename

        integer :: varid, nf_status, i
        real(4), allocatable :: tmp(:, :, :)  ! (nlon, nlat, ntime) - как в файле

        status = 0
        nf_status = nf90_inq_varid(ncid, varname, varid)
        if (nf_status .ne. nf90_noerr) then
            print *, "NetCDF ERROR: file = ", trim(filename), &
                     ", variable = ", trim(varname), &
                     ", status = ", trim(nf90_strerror(nf_status))
            status = 1
            return
        end if

        allocate (tmp(era5_nlon, era5_nlat, era5_ntime))
        nf_status = nf90_get_var(ncid, varid, tmp)
        if (.not. nc_input_ok(nf_status, 'read '//trim(varname), filename=filename, &
                              variable=varname)) then
            deallocate (tmp)
            status = 1
            return
        end if

        ! Перенос (nlon,nlat,ntime) -> (nlat,nlon,ntime) с учётом переворота latitude.
        do i = 1, era5_nlat
            if (era5_lat_decreasing) then
                arr(era5_nlat - i + 1, :, :) = tmp(:, i, :)
            else
                arr(i, :, :) = tmp(:, i, :)
            end if
        end do
        deallocate (tmp)
    end subroutine era5_read_var

    ! ==========================================================================
    ! Диагностика: мин/макс всех прочитанных переменных и координат.
    ! Служит для контроля корректности чтения (Этап 3).
    ! ==========================================================================
    subroutine era5_diag()
        if (.not. era5_is_open) then
            print *, "ERA5 DIAG: no file open"
            return
        end if

        print *, "--- ERA5 diagnostic ---"
        print *, "time   min/max [s]:", minval(era5_time), maxval(era5_time)
        print *, "lat    min/max [degN]:", minval(era5_lat), maxval(era5_lat), &
                 " (decreasing=", era5_lat_decreasing, ")"
        print *, "lon    min/max [degE]:", minval(era5_lon), maxval(era5_lon)
        print *, "u10 min/max [m s-1]:", minval(era5_u10), maxval(era5_u10)
        print *, "v10 min/max [m s-1]:", minval(era5_v10), maxval(era5_v10)
        print *, "t2m min/max [K]:   ", minval(era5_t2m), maxval(era5_t2m)
        print *, "msl min/max [Pa]:  ", minval(era5_msl), maxval(era5_msl)
        print *, "fill value (assumed):", era5_fill
        print *, "--- end ERA5 diagnostic ---"
    end subroutine era5_diag

    ! ==========================================================================
    ! Проверка кода возврата NetCDF. Вместо тихих ошибок печатает контекст.
    ! ==========================================================================
    logical function nc_input_ok(nf_status, operation, filename, variable)
        integer, intent(in) :: nf_status
        character(len=*), intent(in) :: operation
        character(len=*), intent(in), optional :: filename
        character(len=*), intent(in), optional :: variable

        nc_input_ok = (nf_status .eq. nf90_noerr)
        if (.not. nc_input_ok) then
            print *, "NetCDF ERROR:"
            if (present(filename)) print *, "  file     = ", trim(filename)
            if (present(variable)) print *, "  variable = ", trim(variable)
            print *, "  operation = ", trim(operation)
            print *, "  status   = ", trim(nf90_strerror(nf_status))
        end if
    end function nc_input_ok

end module netcdf_input
