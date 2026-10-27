! ==============================================================================
! Модуль: netcdf_grid_reader
! Назначение: Stage 11.7E — чтение сетки/батИметрии из NetCDF вместо
!             legacy-файлов KOORD.DAT / hhh.bar (первый и самый низкорисковый
!             reader switch миграции 11.7).
!             NetCDF is the ONLY production grid reader from Stage 11.10.
!             Legacy KOORD.DAT/hhh.bar remain only as offline regression
!             fixtures; no production env gate.
!
! Source of truth: data/input/processed/grid/grid.nc
! (kt1_raw + lon/lat; CWD-relative).
!
! Architecture: the file-read layer is NetCDF; legacy branches below are
! retained solely for offline regression and are unreachable in production.
! Вся цепочка derivations (ht/mod/smooth/map1/kt1-counts/kk1/hu/hv/dz,
! IDX/IDY/кориолис) выполняется существующим кодом coup1() БЕЗ ИЗМЕНЕНИЙ
! в обоих путях — расхождение по построению невозможно, контроль
! эквивалентности измеряет только IO-слой (f64->f32 округление FI/DL).
! bathymetry.nc (ht/map1 finals) моделью НЕ читается на этом этапе
! (валидированный артефакт для поздних стадий).
!
! Missing grid.nc → FATAL STOP (no silent fallback).
! Измерения переменных проверяются явно (T-18, 11.7E.1-CP):
! несовпадение имён/длин → FATAL, форма буфера не угадывается.
! Физика/EOS/scheduler/production-defaults НЕ меняются.
! ==============================================================================
module netcdf_grid_reader
    use param
    use netcdf
    implicit none

    logical, save :: s117e_nc = .true.
    character(len=*), parameter :: GRID_NC_PATH = &
        'data/input/processed/grid/grid.nc'

contains

    subroutine s117e_init()
        s117e_nc = .true.
        print *, 'Stage 11.10: NetCDF grid input DEFAULT (grid.nc codes+coords)'
    end subroutine s117e_init

    logical function s117e_grid_active()
        s117e_grid_active = s117e_nc
    end function s117e_grid_active

    subroutine s117e_fatal(what, code)
        character(len=*), intent(in) :: what
        integer, intent(in) :: code
        print *, 'FATAL: STAGE117E NetCDF grid read failed: ', trim(what)
        print *, '  nf90: ', trim(nf90_strerror(code)), ' (code=', code, ')'
        print *, '  file: ', GRID_NC_PATH
        print *, '  production requires grid.nc; legacy .DAT/.bar are offline regression only'
        stop 1
    end subroutine s117e_fatal

    ! FATAL с произвольным сообщением (ошибки валидации, не nf90).
    subroutine s117e_fatal_msg(msg)
        character(len=*), intent(in) :: msg
        print *, 'FATAL: STAGE117E NetCDF grid validation failed: ', trim(msg)
        print *, '  file: ', GRID_NC_PATH
        print *, '  production requires grid.nc; legacy .DAT/.bar are offline regression only'
        stop 1
    end subroutine s117e_fatal_msg

    ! Строгая проверка измерений 2D-переменной (Stage 11.7E.1-CP, T-18).
    ! Конвенция netCDF-Fortran — обратный порядок измерений относительно
    ! CDL (стандартное поведение интерфейса, НЕ баг библиотеки; пробы
    ! 11.7E.1-CP на libnetcdff 4.9.3): CDL-переменная (i,j) видна из
    ! Fortran-API как (j,i) = (js1,is1), весь массив читается в буфер
    ! формы (js1,is1). Любое отклонение имён/длин → FATAL.
    subroutine s117e_check_dims(ncid, varid, varname)
        integer, intent(in) :: ncid, varid
        character(len=*), intent(in) :: varname
        integer :: ndims, dimids(2), len1, len2, st
        character(len=nf90_max_name) :: name1, name2
        character(len=256) :: emsg

        st = nf90_inquire_variable(ncid, varid, ndims=ndims, dimids=dimids)
        if (st .ne. nf90_noerr) call s117e_fatal('inquire '//trim(varname), st)
        if (ndims .ne. 2) then
            write (emsg, *) 'dimension check ', trim(varname), &
                ': expected ndims=2, found ', ndims
            call s117e_fatal_msg(trim(emsg))
        end if
        st = nf90_inquire_dimension(ncid, dimids(1), name=name1, len=len1)
        if (st .ne. nf90_noerr) call s117e_fatal('inquire dim1 '//trim(varname), st)
        st = nf90_inquire_dimension(ncid, dimids(2), name=name2, len=len2)
        if (st .ne. nf90_noerr) call s117e_fatal('inquire dim2 '//trim(varname), st)
        if (name1 .ne. 'j' .or. name2 .ne. 'i' .or. &
            len1 .ne. js1 .or. len2 .ne. is1) then
            write (emsg, *) 'dimension check ', trim(varname), &
                ': Fortran view=(', trim(name1), '=', len1, ', ', &
                trim(name2), '=', len2, '), expected (j=', js1, ', i=', is1, ')'
            call s117e_fatal_msg(trim(emsg))
        end if
    end subroutine s117e_check_dims

    ! Коды KT1 (raw, 8=land, 3..600) из grid.nc -> массив kt1 модели.
    ! Дальнейшая цепочка (ht/mod/smooth/map1/counts/kk1) — существующий
    ! код coup1(), идентично legacy-пути. int16-буфер соответствует
    ! NC_SHORT в файле (конверсии типов на чтении избегаем намеренно).
    ! ВАЖНО (T-18, уточнено 11.7E.1-CP): видимая из Fortran-API
    ! транспонированность — СТАНДАРТНАЯ конвенция netCDF-Fortran
    ! (порядок измерений CDL обращён в Fortran-API), НЕ баг библиотеки
    ! (пробы на libnetcdff 4.9.3): CDL-переменная (i,j) видна как
    ! (j,i) = (js1,is1), весь массив читается в буфер (js1,is1) с
    ! обратной транспозицией; прямое чтение в (is1,js1) даёт EEDGE.
    ! Перед чтением измерения проверяются явно (s117e_check_dims).
    ! Доказательство корректности: 0/13965 расхождений с независимым
    ! Python-прочтением + бит-идентичные OFF-vs-ON прогоны
    ! (отчёты 11.7E и 11.7E.1-CP).
    subroutine s117e_read_codes()
        integer :: ncid, varid, st, i, j
        integer(kind=2) :: bufT(js1, is1)
        if (.not. s117e_nc) return
        st = nf90_open(GRID_NC_PATH, nf90_nowrite, ncid)
        if (st .ne. nf90_noerr) call s117e_fatal('nf90_open', st)
        st = nf90_inq_varid(ncid, 'kt1_raw', varid)
        if (st .ne. nf90_noerr) call s117e_fatal('kt1_raw var', st)
        call s117e_check_dims(ncid, varid, 'kt1_raw')
        st = nf90_get_var(ncid, varid, bufT)
        if (st .ne. nf90_noerr) call s117e_fatal('kt1_raw read', st)
        st = nf90_close(ncid)
        if (st .ne. nf90_noerr) call s117e_fatal('nf90_close', st)
        do j = 1, js1
            do i = 1, is1
                kt1(i, j) = int(bufT(j, i))
            end do
        end do
        print *, 'STAGE117E: kt1 raw codes loaded from grid.nc'
    end subroutine s117e_read_codes

    ! Координаты FI/DL из grid.nc (float64 lon/lat -> f32 FI/DL).
    ! Единственное место с f64->f32 округлением (контролируется
    ! эквивалентностью OFF vs ON); вся дальнейшая цепочка идентична.
    subroutine s117e_read_coords()
        integer :: ncid, varid, st, i, j
        real(kind=8) :: lonT(js1, is1), latT(js1, is1)
        if (.not. s117e_nc) return
        st = nf90_open(GRID_NC_PATH, nf90_nowrite, ncid)
        if (st .ne. nf90_noerr) call s117e_fatal('nf90_open', st)
        st = nf90_inq_varid(ncid, 'lon', varid)
        if (st .ne. nf90_noerr) call s117e_fatal('lon var', st)
        call s117e_check_dims(ncid, varid, 'lon')
        st = nf90_get_var(ncid, varid, lonT)
        if (st .ne. nf90_noerr) call s117e_fatal('lon read', st)
        st = nf90_inq_varid(ncid, 'lat', varid)
        if (st .ne. nf90_noerr) call s117e_fatal('lat var', st)
        call s117e_check_dims(ncid, varid, 'lat')
        st = nf90_get_var(ncid, varid, latT)
        if (st .ne. nf90_noerr) call s117e_fatal('lat read', st)
        st = nf90_close(ncid)
        if (st .ne. nf90_noerr) call s117e_fatal('nf90_close', st)
        do j = 1, js1
            do i = 1, is1
                fi(i, j) = real(latT(j, i))
                dl(i, j) = real(lonT(j, i))
            end do
        end do
        print *, 'STAGE117E: FI/DL loaded from grid.nc (f64->f32)'
    end subroutine s117e_read_coords

end module netcdf_grid_reader
