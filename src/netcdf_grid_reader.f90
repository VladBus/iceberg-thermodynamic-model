! ==============================================================================
! Модуль: netcdf_grid_reader
! Назначение: Stage 11.7E — чтение сетки/батИметрии из NetCDF вместо
!             legacy-файлов KOORD.DAT / hhh.bar (первый и самый низкорисковый
!             reader switch миграции 11.7).
!             ПОЛНОСТЬЮ ОПЦИОНАЛЕН — поведение по умолчанию бит-идентично
!             legacy (переключатель выключен → мгновенный возврат везде).
!
! Включается env (default OFF → legacy-путь, бит-идентично):
!   STAGE117E_NETCDF_GRID=true — читать коды KT1 + координаты FI/DL из
!                                data/input/processed/grid/grid.nc
!                                (путь — CWD-относительный, как у legacy).
!
! Архитектура switch (11.7E): подменяется ТОЛЬКО слой чтения файлов.
! Вся цепочка derivations (ht/mod/smooth/map1/kt1-counts/kk1/hu/hv/dz,
! IDX/IDY/кориолис) выполняется существующим кодом coup1() БЕЗ ИЗМЕНЕНИЙ
! в обоих путях — расхождение по построению невозможно, контроль
! эквивалентности измеряет только IO-слой (f64->f32 округление FI/DL).
! bathymetry.nc (ht/map1 finals) моделью НЕ читается на этом этапе
! (валидированный артефакт для поздних стадий).
!
! Откат: STAGE117E_NETCDF_GRID unset → legacy KOORD.DAT/hhh.bar.
! Отсутствующий grid.nc при ON → FATAL STOP (без silent fallback,
! конвенция KOORD-missing FATAL в coup1).
! Физика/EOS/scheduler/production-defaults НЕ меняются.
! ==============================================================================
module netcdf_grid_reader
    use param
    use netcdf
    implicit none

    logical, save :: s117e_nc = .false.
    character(len=*), parameter :: GRID_NC_PATH = &
        'data/input/processed/grid/grid.nc'

contains

    subroutine s117e_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE117E_NETCDF_GRID', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. &
             env_str .eq. '1')) then
            s117e_nc = .true.
        end if
        if (s117e_nc) then
            print *, 'STAGE117E: NetCDF grid input ON (grid.nc codes+coords)'
        end if
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
        print *, '  rollback: unset STAGE117E_NETCDF_GRID (legacy KOORD.DAT/hhh.bar)'
        stop 1
    end subroutine s117e_fatal

    ! Коды KT1 (raw, 8=land, 3..600) из grid.nc -> массив kt1 модели.
    ! Дальнейшая цепочка (ht/mod/smooth/map1/counts/kk1) — существующий
    ! код coup1(), идентично legacy-пути. int16-буфер соответствует
    ! NC_SHORT в файле (конверсии типов на чтении избегаем намеренно).
    ! ВАЖНО (11.7E, проверено побайтово): системный libnetcdff читает
    ! 2D-переменные этих NETCDF4-файлов ТРАНСПОНИРОВАННО — рабочий вызов
    ! читает весь массив в буфер (js1,is1) и транспонирует обратно;
    ! прямое чтение в (is1,js1) даёт EEDGE. Доказательство корректности:
    ! 0/13965 расхождений с независимым Python-прочтением + бит-identical
    ! OFF-vs-ON прогоны модели (см. отчёт 11.7E).
    subroutine s117e_read_codes()
        integer :: ncid, varid, st, i, j
        integer(kind=2) :: bufT(js1, is1)
        if (.not. s117e_nc) return
        st = nf90_open(GRID_NC_PATH, nf90_nowrite, ncid)
        if (st .ne. nf90_noerr) call s117e_fatal('nf90_open', st)
        st = nf90_inq_varid(ncid, 'kt1_raw', varid)
        if (st .ne. nf90_noerr) call s117e_fatal('kt1_raw var', st)
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
        st = nf90_get_var(ncid, varid, lonT)
        if (st .ne. nf90_noerr) call s117e_fatal('lon read', st)
        st = nf90_inq_varid(ncid, 'lat', varid)
        if (st .ne. nf90_noerr) call s117e_fatal('lat var', st)
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
