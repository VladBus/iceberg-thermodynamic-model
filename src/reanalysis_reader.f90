! ==============================================================================
! Модуль: reanalysis_reader (Stage 12.2)
! Назначение: Чтение GLORYS12 реанализа (NetCDF) и интерполяция океанского
!             состояния в точку (time, lat, lon, depth) — OFFLINE/PRESCRIBED.
!             Заменяет прогностический океан Stage 11 для форсинга айсберга
!             (D-51). Односторонняя связь: океан НЕ чувствует айсберг.
!
! Источник (Stage 12.1, data/validation/stage12.1_glorys12_validation.md):
!   daily  : (time, depth, latitude, longitude), packed int16 + scale_factor/
!            add_offset, _FillValue=-32767. ЧТЕНИЕ В real(8) → libnetcdf сам
!            применяет scale/offset и конвертирует _FillValue→NaN.
!   static : mask(depth,latitude,longitude) int8 (1=sea,0=land); deptho m.
!   Сетка: РЕГУЛЯРНАЯ 1-D latitude/longitude (не криволинейная ORCA).
!
! netCDF-Fortran (T-18): CDL (time,depth,lat,lon) виден из Fortran-API как
!   (lon,lat,depth,time) — ОБРАТНЫЙ порядок измерений. Позиции осей определяются
!   явно через dimids (не по жёсткому предположению).
!
! Единицы выхода (SI, совместимо с ocean_profile Stage 9/10):
!   T [°C]; S [масс. доля кг/кг] = so_raw(PSU-like)/1000; u,v [м/с]; zos [м];
!   siconc [0..1 clipped]; sithick [м].
! Время вход: UNIX-секунды с 1970-01-01 (совпадает с model_time_sec/era5_time).
!   GLORYS time = hours since 1950-01-01 → переводится при init.
! Границы: без экстраполяции. lat/lon/time вне диапазона → ok=.false.;
!   depth вне диапазона → clamp к граничному уровню; суша во всех углах →
!   ok=.false.; частично суша — веса перенормируются по морским углам.
! ==============================================================================
module reanalysis_reader
    use iso_fortran_env, only: real32, real64, int64
    use netcdf
    implicit none

    private
    public :: reanalysis_reader_type, reanalysis_reader_init
    public :: reanalysis_reader_get, reanalysis_reader_close
    public :: reanalysis_reader_ready, reanalysis_reader_ndepth
    public :: reanalysis_reader_depth_values

    real(8), parameter :: HOURS_1950_TO_1970 = 175320.0_8   ! 7305 сут * 24
    real(8), parameter :: SEC_PER_HOUR = 3600.0_8

    type :: reanalysis_reader_type
        integer :: ncid_daily = -1
        integer :: ncid_static = -1
        integer :: nlat = 0, nlon = 0, ntime = 0, ndepth = 0
        integer :: dimid_lat = -1, dimid_lon = -1, dimid_dep = -1, dimid_tim = -1
        real(8), allocatable :: lat(:)        ! [deg N]  возрастающая
        real(8), allocatable :: lon(:)        ! [deg E]  возрастающая
        real(8), allocatable :: depth(:)      ! [m]      возрастающая
        real(8), allocatable :: time_unix(:)  ! [s since 1970-01-01]
        real(8), allocatable :: mask_surface(:,:) ! (lat,lon): >=0.5 sea, <0.5 land
        ! Пакетирование GLORYS: packed int16 + scale_factor/add_offset/_FillValue.
        ! netCDF-Fortran НЕ применяет их автоматически (в отличие от C) → читаем
        ! raw int16 и декодируем явно. Индекс: 1..7 = thetao,so,uo,vo,zos,siconc,sithick.
        real(8) :: sf(7) = 1.0_8, ao(7) = 0.0_8
        integer(kind=2) :: fillv(7) = -32767_2
        logical :: ready = .false.
        integer :: time_idx_lo = 0, time_idx_hi = 0, depth_idx_lo = 0, depth_idx_hi = 0
        real(8) :: time_frac = 0.0_8, depth_frac = 0.0_8
    end type reanalysis_reader_type

contains

    logical function reanalysis_reader_ready(reader)
        type(reanalysis_reader_type), intent(in) :: reader
        reanalysis_reader_ready = reader%ready
    end function reanalysis_reader_ready

    integer function reanalysis_reader_ndepth(reader)
        type(reanalysis_reader_type), intent(in) :: reader
        reanalysis_reader_ndepth = reader%ndepth
    end function reanalysis_reader_ndepth

    subroutine reanalysis_reader_depth_values(reader, dep)
        type(reanalysis_reader_type), intent(in) :: reader
        real(8), intent(out) :: dep(:)
        integer :: k
        dep = 0.0_8
        do k = 1, min(reader%ndepth, size(dep))
            dep(k) = reader%depth(k)
        end do
    end subroutine reanalysis_reader_depth_values

    ! ==========================================================================
    subroutine reanalysis_reader_init(reader, daily_path, static_path, ok)
        type(reanalysis_reader_type), intent(out) :: reader
        character(len=*), intent(in) :: daily_path, static_path
        logical, intent(out) :: ok

        integer :: st, ncid
        logical :: fexists

        ok = .false.
        reader%ready = .false.

        inquire (file=trim(daily_path), exist=fexists)
        if (.not. fexists) then
            print *, 'reanalysis_reader: daily file absent (SKIP in CI): ', trim(daily_path)
            return
        end if
        inquire (file=trim(static_path), exist=fexists)
        if (.not. fexists) then
            print *, 'reanalysis_reader: static file absent (SKIP in CI): ', trim(static_path)
            return
        end if

        st = nf90_open(trim(daily_path), nf90_nowrite, ncid)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: cannot open daily: ', trim(nf90_strerror(st))
            return
        end if
        reader%ncid_daily = ncid

        if (.not. read_dim(ncid, 'latitude', reader%dimid_lat, reader%nlat)) return
        if (.not. read_dim(ncid, 'longitude', reader%dimid_lon, reader%nlon)) return
        if (.not. read_dim(ncid, 'depth', reader%dimid_dep, reader%ndepth)) return
        if (.not. read_dim(ncid, 'time', reader%dimid_tim, reader%ntime)) return
        if (reader%nlat < 2 .or. reader%nlon < 2 .or. reader%ndepth < 1 .or. &
            reader%ntime < 1) return

        allocate (reader%lat(reader%nlat), reader%lon(reader%nlon), &
                  reader%depth(reader%ndepth), reader%time_unix(reader%ntime))
        if (.not. read_1d(ncid, 'latitude', reader%lat)) return
        if (.not. read_1d(ncid, 'longitude', reader%lon)) return
        if (.not. read_1d(ncid, 'depth', reader%depth)) return
        block
            real(8), allocatable :: thrs(:)
            integer :: i
            allocate (thrs(reader%ntime))
            if (.not. read_1d(ncid, 'time', thrs)) then
                deallocate (thrs)
                return
            end if
            do i = 1, reader%ntime
                reader%time_unix(i) = (thrs(i) - HOURS_1950_TO_1970)*SEC_PER_HOUR
            end do
            deallocate (thrs)
        end block

        ! Кэш scale_factor/add_offset/_FillValue для пакетированных int16-полей.
        call init_field_scaling(reader%ncid_daily, reader)

        st = nf90_open(trim(static_path), nf90_nowrite, ncid)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: cannot open static: ', trim(nf90_strerror(st))
            return
        end if
        reader%ncid_static = ncid
        if (.not. read_surface_mask(ncid, reader)) return

        reader%ready = .true.
        ok = .true.
        print '("reanalysis_reader: GLORYS12 ready — lat ",I0,", lon ",I0,", depth ",I0,", time ",I0)', &
            reader%nlat, reader%nlon, reader%ndepth, reader%ntime
    end subroutine reanalysis_reader_init

    ! ==========================================================================
    subroutine reanalysis_reader_get(reader, time, lat, lon, depth, &
                                     T, S, u, v, zos, siconc, sithick, ok)
        type(reanalysis_reader_type), intent(inout) :: reader
        real(8), intent(in) :: time, lat, lon, depth
        real(8), intent(out) :: T, S, u, v, zos, siconc, sithick
        logical, intent(out) :: ok

        integer :: i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt
        real(8) :: ylat, ylon, df, tf
        real(8) :: fld4(2, 2, 2, 2)
        real(8) :: fld3(2, 2, 2)
        real(8) :: vT, vS, vU, vV, vZ, vC, vH
        logical :: rok

        ok = .false.
        T = 0.0_8; S = 0.0_8; u = 0.0_8; v = 0.0_8
        zos = 0.0_8; siconc = 0.0_8; sithick = 0.0_8
        if (.not. reader%ready) return

        if (lat < reader%lat(1) .or. lat > reader%lat(reader%nlat)) return
        if (lon < reader%lon(1) .or. lon > reader%lon(reader%nlon)) return
        if (time < reader%time_unix(1) .or. time > reader%time_unix(reader%ntime)) return

        call horiz_bracket(reader, lat, lon, i_lo, j_lo, ylat, ylon)
        call time_bracket_cached(reader, time, t_lo, t_cnt, tf)
        call depth_bracket_cached(reader, depth, d_lo, d_cnt, df)

        ! --- 3-D: thetao, so, uo, vo ---
        if (.not. read_3d_block(reader, 'thetao', i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt, fld4)) return
        call reduce_3d(reader, i_lo, j_lo, ylat, ylon, df, tf, d_cnt, t_cnt, fld4, vT, rok)
        if (.not. rok) return
        if (.not. read_3d_block(reader, 'so', i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt, fld4)) return
        call reduce_3d(reader, i_lo, j_lo, ylat, ylon, df, tf, d_cnt, t_cnt, fld4, vS, rok)
        if (.not. rok) return
        if (.not. read_3d_block(reader, 'uo', i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt, fld4)) return
        call reduce_3d(reader, i_lo, j_lo, ylat, ylon, df, tf, d_cnt, t_cnt, fld4, vU, rok)
        if (.not. rok) return
        if (.not. read_3d_block(reader, 'vo', i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt, fld4)) return
        call reduce_3d(reader, i_lo, j_lo, ylat, ylon, df, tf, d_cnt, t_cnt, fld4, vV, rok)
        if (.not. rok) return

        ! --- 2-D: zos (optional; 0 если недоступно) ---
        vZ = 0.0_8
        if (read_2d_block(reader, 'zos', i_lo, j_lo, t_lo, t_cnt, fld3)) then
            if (.not. reduce_2d(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, fld3, vZ)) vZ = 0.0_8
        end if

        ! --- 2-D ice: siconc (clip [0,1]), sithick (>=0); missing ice -> 0 ---
        vC = 0.0_8; vH = 0.0_8
        if (read_2d_block(reader, 'siconc', i_lo, j_lo, t_lo, t_cnt, fld3)) &
            vC = reduce_2d_ice(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, fld3)
        if (read_2d_block(reader, 'sithick', i_lo, j_lo, t_lo, t_cnt, fld3)) &
            vH = reduce_2d_ice(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, fld3)

        T = vT
        S = vS/1000.0_8                       ! so (PSU-like) → mass fraction
        u = vU
        v = vV
        zos = vZ
        siconc = max(0.0_8, min(1.0_8, vC))   ! CLIP [0,1]
        sithick = max(0.0_8, vH)
        ok = .true.
    end subroutine reanalysis_reader_get

    subroutine reanalysis_reader_close(reader)
        type(reanalysis_reader_type), intent(inout) :: reader
        if (reader%ncid_daily >= 0) call ignore_close(nf90_close(reader%ncid_daily))
        if (reader%ncid_static >= 0) call ignore_close(nf90_close(reader%ncid_static))
        reader%ncid_daily = -1
        reader%ncid_static = -1
        reader%ready = .false.
        if (allocated(reader%lat)) deallocate (reader%lat)
        if (allocated(reader%lon)) deallocate (reader%lon)
        if (allocated(reader%depth)) deallocate (reader%depth)
        if (allocated(reader%time_unix)) deallocate (reader%time_unix)
        if (allocated(reader%mask_surface)) deallocate (reader%mask_surface)
    end subroutine reanalysis_reader_close

    ! ==========================================================================
    !  Чтение блоков
    ! ==========================================================================
    logical function read_3d_block(reader, varname, i_lo, j_lo, d_lo, d_cnt, &
                                   t_lo, t_cnt, fld)
        type(reanalysis_reader_type), intent(in) :: reader
        character(len=*), intent(in) :: varname
        integer, intent(in) :: i_lo, j_lo, d_lo, d_cnt, t_lo, t_cnt
        real(8), intent(out) :: fld(2, 2, 2, 2)

        integer :: varid, st, nd, latp, lonp, depp, timp, fi_idx
        integer :: vidims(4), cnt(4), strt(4), pos(4)
        integer :: a, b, d, t
        real(8) :: sf, off
        integer(kind=2) :: fill
        integer(kind=2), allocatable :: buf(:, :, :, :)

        read_3d_block = .false.
        fld = nan8const()
        fi_idx = field_index(varname)
        if (fi_idx == 0) return
        sf = reader%sf(fi_idx); off = reader%ao(fi_idx); fill = reader%fillv(fi_idx)

        st = nf90_inq_varid(reader%ncid_daily, trim(varname), varid)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: var not found ', trim(varname)
            return
        end if
        st = nf90_inquire_variable(reader%ncid_daily, varid, ndims=nd, dimids=vidims)
        if (st /= nf90_noerr .or. nd /= 4) return
        call axis_positions(vidims, nd, reader, latp, lonp, depp, timp)
        if (latp == 0 .or. lonp == 0 .or. depp == 0 .or. timp == 0) return

        cnt = 1; cnt(latp) = 2; cnt(lonp) = 2; cnt(depp) = d_cnt; cnt(timp) = t_cnt
        strt = 1; strt(latp) = i_lo; strt(lonp) = j_lo; strt(depp) = d_lo; strt(timp) = t_lo
        allocate (buf(cnt(1), cnt(2), cnt(3), cnt(4)))
        st = nf90_get_var(reader%ncid_daily, varid, buf, start=strt, count=cnt)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: get_var ', trim(varname), ' ', trim(nf90_strerror(st))
            deallocate (buf)
            return
        end if
        do t = 1, t_cnt
            do d = 1, d_cnt
                do b = 1, 2
                    do a = 1, 2
                        pos = 1
                        pos(latp) = a; pos(lonp) = b; pos(depp) = d; pos(timp) = t
                        fld(a, b, d, t) = decode_raw(buf(pos(1), pos(2), pos(3), pos(4)), &
                                                     sf, off, fill)
                    end do
                end do
            end do
        end do
        deallocate (buf)
        read_3d_block = .true.
    end function read_3d_block

    logical function read_2d_block(reader, varname, i_lo, j_lo, t_lo, t_cnt, fld)
        type(reanalysis_reader_type), intent(in) :: reader
        character(len=*), intent(in) :: varname
        integer, intent(in) :: i_lo, j_lo, t_lo, t_cnt
        real(8), intent(out) :: fld(2, 2, 2)

        integer :: varid, st, nd, latp, lonp, depp, timp, fi_idx
        integer :: vidims(3), cnt(3), strt(3), pos(3)
        integer :: a, b, t
        real(8) :: sf, off
        integer(kind=2) :: fill
        integer(kind=2), allocatable :: buf(:, :, :)

        read_2d_block = .false.
        fld = nan8const()
        fi_idx = field_index(varname)
        if (fi_idx == 0) return
        sf = reader%sf(fi_idx); off = reader%ao(fi_idx); fill = reader%fillv(fi_idx)

        st = nf90_inq_varid(reader%ncid_daily, trim(varname), varid)
        if (st /= nf90_noerr) return
        st = nf90_inquire_variable(reader%ncid_daily, varid, ndims=nd, dimids=vidims)
        if (st /= nf90_noerr .or. nd /= 3) return
        call axis_positions(vidims, nd, reader, latp, lonp, depp, timp)
        if (latp == 0 .or. lonp == 0 .or. timp == 0) return

        cnt = 1; cnt(latp) = 2; cnt(lonp) = 2; cnt(timp) = t_cnt
        strt = 1; strt(latp) = i_lo; strt(lonp) = j_lo; strt(timp) = t_lo
        allocate (buf(cnt(1), cnt(2), cnt(3)))
        st = nf90_get_var(reader%ncid_daily, varid, buf, start=strt, count=cnt)
        if (st /= nf90_noerr) then
            deallocate (buf)
            return
        end if
        do t = 1, t_cnt
            do b = 1, 2
                do a = 1, 2
                    pos = 1
                    pos(latp) = a; pos(lonp) = b; pos(timp) = t
                    fld(a, b, t) = decode_raw(buf(pos(1), pos(2), pos(3)), sf, off, fill)
                end do
            end do
        end do
        deallocate (buf)
        read_2d_block = .true.
    end function read_2d_block

    ! ==========================================================================
    !  Интерполяция
    ! ==========================================================================
    subroutine reduce_3d(reader, i_lo, j_lo, ylat, ylon, df, tf, d_cnt, t_cnt, &
                         fld, val, ok)
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(in) :: i_lo, j_lo, d_cnt, t_cnt
        real(8), intent(in) :: ylat, ylon, df, tf
        real(8), intent(in) :: fld(2, 2, 2, 2)
        real(8), intent(out) :: val
        logical, intent(out) :: ok

        real(8) :: hd(2)
        logical :: od(2)
        integer :: d

        ok = .false.
        val = 0.0_8
        do d = 1, d_cnt
            call time_bilinear(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, &
                               fld(:, :, d, 1), fld(:, :, d, 2), hd(d), od(d))
        end do
        if (d_cnt == 1) then
            if (od(1)) then
                val = hd(1)
                ok = .true.
            end if
        else if (od(1) .and. od(2)) then
            val = (1.0_8 - df)*hd(1) + df*hd(2)
            ok = .true.
        else if (od(1)) then
            val = hd(1)
            ok = .true.
        else if (od(2)) then
            val = hd(2)
            ok = .true.
        end if
    end subroutine reduce_3d

    logical function reduce_2d(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, fld, val)
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(in) :: i_lo, j_lo, t_cnt
        real(8), intent(in) :: ylat, ylon, tf
        real(8), intent(in) :: fld(2, 2, 2)
        real(8), intent(out) :: val
        logical :: ok

        reduce_2d = .false.
        call time_bilinear(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, &
                           fld(:, :, 1), fld(:, :, 2), val, ok)
        reduce_2d = ok
    end function reduce_2d

    real(8) function reduce_2d_ice(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, fld) result(val)
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(in) :: i_lo, j_lo, t_cnt
        real(8), intent(in) :: ylat, ylon, tf
        real(8), intent(in) :: fld(2, 2, 2)

        real(8) :: fc(2, 2), base(2, 2), w(2, 2), tot, fa, fb
        integer :: a, b

        do b = 1, 2
            do a = 1, 2
                fa = ice_val(fld(a, b, 1))
                if (t_cnt == 2) then
                    fb = ice_val(fld(a, b, 2))
                    fc(a, b) = (1.0_8 - tf)*fa + tf*fb
                else
                    fc(a, b) = fa
                end if
            end do
        end do

        base(1, 1) = (1.0_8 - ylat)*(1.0_8 - ylon)
        base(1, 2) = (1.0_8 - ylat)*ylon
        base(2, 1) = ylat*(1.0_8 - ylon)
        base(2, 2) = ylat*ylon
        tot = 0.0_8
        val = 0.0_8
        do b = 1, 2
            do a = 1, 2
                if (reader%mask_surface(i_lo + a - 1, j_lo + b - 1) >= 0.5_8) then
                    w(a, b) = base(a, b)
                else
                    w(a, b) = 0.0_8
                end if
                tot = tot + w(a, b)
                val = val + w(a, b)*fc(a, b)
            end do
        end do
        if (tot > 0.0_8) val = val/tot
    end function reduce_2d_ice

    subroutine time_bilinear(reader, i_lo, j_lo, ylat, ylon, tf, t_cnt, f1, f2, val, ok)
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(in) :: i_lo, j_lo, t_cnt
        real(8), intent(in) :: ylat, ylon, tf
        real(8), intent(in) :: f1(2, 2), f2(2, 2)
        real(8), intent(out) :: val
        logical, intent(out) :: ok

        real(8) :: h1, h2
        logical :: o1, o2

        call corner_bilinear(reader, i_lo, j_lo, ylat, ylon, f1, h1, o1)
        if (t_cnt == 2) then
            call corner_bilinear(reader, i_lo, j_lo, ylat, ylon, f2, h2, o2)
        else
            h2 = h1
            o2 = o1
        end if
        if (o1 .and. o2) then
            val = (1.0_8 - tf)*h1 + tf*h2
            ok = .true.
        else if (o1) then
            val = h1
            ok = .true.
        else if (o2) then
            val = h2
            ok = .true.
        else
            val = 0.0_8
            ok = .false.
        end if
    end subroutine time_bilinear

    subroutine corner_bilinear(reader, i_lo, j_lo, ylat, ylon, f, val, ok)
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(in) :: i_lo, j_lo
        real(8), intent(in) :: ylat, ylon
        real(8), intent(in) :: f(2, 2)
        real(8), intent(out) :: val
        logical, intent(out) :: ok

        real(8) :: base(2, 2), w(2, 2), tot
        integer :: a, b

        base(1, 1) = (1.0_8 - ylat)*(1.0_8 - ylon)
        base(1, 2) = (1.0_8 - ylat)*ylon
        base(2, 1) = ylat*(1.0_8 - ylon)
        base(2, 2) = ylat*ylon
        tot = 0.0_8
        val = 0.0_8
        do b = 1, 2
            do a = 1, 2
                if (is_nan(f(a, b)) .or. &
                    reader%mask_surface(i_lo + a - 1, j_lo + b - 1) < 0.5_8) then
                    w(a, b) = 0.0_8
                else
                    w(a, b) = base(a, b)
                end if
                tot = tot + w(a, b)
                val = val + w(a, b)*f(a, b)
            end do
        end do
        if (tot <= 0.0_8) then
            ok = .false.
            val = 0.0_8
        else
            val = val/tot
            ok = .true.
        end if
    end subroutine corner_bilinear

    ! ==========================================================================
    !  Скобки
    ! ==========================================================================
    subroutine horiz_bracket(reader, lat, lon, i_lo, j_lo, ylat, ylon)
        type(reanalysis_reader_type), intent(in) :: reader
        real(8), intent(in) :: lat, lon
        integer, intent(out) :: i_lo, j_lo
        real(8), intent(out) :: ylat, ylon
        integer :: idx
        idx = lower_index(reader%lat, reader%nlat, lat)
        i_lo = min(max(idx, 1), reader%nlat - 1)
        ylat = (lat - reader%lat(i_lo))/(reader%lat(i_lo + 1) - reader%lat(i_lo))
        ylat = max(0.0_8, min(1.0_8, ylat))
        idx = lower_index(reader%lon, reader%nlon, lon)
        j_lo = min(max(idx, 1), reader%nlon - 1)
        ylon = (lon - reader%lon(j_lo))/(reader%lon(j_lo + 1) - reader%lon(j_lo))
        ylon = max(0.0_8, min(1.0_8, ylon))
    end subroutine horiz_bracket

    subroutine time_bracket_cached(reader, time, t_lo, t_cnt, tf)
        type(reanalysis_reader_type), intent(inout) :: reader
        real(8), intent(in) :: time
        integer, intent(out) :: t_lo, t_cnt
        real(8), intent(out) :: tf
        integer :: idx
        if (time <= reader%time_unix(1)) then
            t_lo = 1; t_cnt = 1; tf = 0.0_8
        else if (time >= reader%time_unix(reader%ntime)) then
            t_lo = reader%ntime; t_cnt = 1; tf = 0.0_8
        else
            idx = lower_index(reader%time_unix, reader%ntime, time)
            t_lo = idx; t_cnt = 2
            tf = (time - reader%time_unix(idx))/ &
                 (reader%time_unix(idx + 1) - reader%time_unix(idx))
            tf = max(0.0_8, min(1.0_8, tf))
        end if
        reader%time_idx_lo = t_lo
        reader%time_idx_hi = min(t_lo + t_cnt - 1, reader%ntime)
        reader%time_frac = tf
    end subroutine time_bracket_cached

    subroutine depth_bracket_cached(reader, depth, d_lo, d_cnt, df)
        type(reanalysis_reader_type), intent(inout) :: reader
        real(8), intent(in) :: depth
        integer, intent(out) :: d_lo, d_cnt
        real(8), intent(out) :: df
        integer :: idx
        if (depth <= reader%depth(1)) then
            d_lo = 1; d_cnt = 1; df = 0.0_8
        else if (depth >= reader%depth(reader%ndepth)) then
            d_lo = reader%ndepth; d_cnt = 1; df = 0.0_8
        else
            idx = lower_index(reader%depth, reader%ndepth, depth)
            d_lo = idx; d_cnt = 2
            df = (depth - reader%depth(idx))/(reader%depth(idx + 1) - reader%depth(idx))
            df = max(0.0_8, min(1.0_8, df))
        end if
        reader%depth_idx_lo = d_lo
        reader%depth_idx_hi = min(d_lo + d_cnt - 1, reader%ndepth)
        reader%depth_frac = df
    end subroutine depth_bracket_cached

    integer function lower_index(arr, n, x)
        integer, intent(in) :: n
        real(8), intent(in) :: arr(:), x
        integer :: lo, mid, hi
        if (x <= arr(1)) then
            lower_index = 1
            return
        end if
        if (x >= arr(n)) then
            lower_index = n - 1
            return
        end if
        lo = 1; hi = n
        do while (hi - lo > 1)
            mid = (lo + hi)/2
            if (arr(mid) <= x) then
                lo = mid
            else
                hi = mid
            end if
        end do
        lower_index = lo
    end function lower_index

    ! ==========================================================================
    !  Утилиты NetCDF/типов
    ! ==========================================================================
    subroutine axis_positions(vidims, nd, reader, latp, lonp, depp, timp)
        integer, intent(in) :: vidims(:), nd
        type(reanalysis_reader_type), intent(in) :: reader
        integer, intent(out) :: latp, lonp, depp, timp
        integer :: p
        latp = 0; lonp = 0; depp = 0; timp = 0
        do p = 1, nd
            if (vidims(p) == reader%dimid_lat) latp = p
            if (vidims(p) == reader%dimid_lon) lonp = p
            if (vidims(p) == reader%dimid_dep) depp = p
            if (vidims(p) == reader%dimid_tim) timp = p
        end do
    end subroutine axis_positions

    logical function read_dim(ncid, name, dimid, dlen)
        integer, intent(in) :: ncid
        character(len=*), intent(in) :: name
        integer, intent(out) :: dimid, dlen
        integer :: st
        st = nf90_inq_dimid(ncid, trim(name), dimid)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: dim not found ', trim(name), ' ', trim(nf90_strerror(st))
            read_dim = .false.
            return
        end if
        st = nf90_inquire_dimension(ncid, dimid, len=dlen)
        read_dim = (st == nf90_noerr)
    end function read_dim

    logical function read_1d(ncid, name, out)
        integer, intent(in) :: ncid
        character(len=*), intent(in) :: name
        real(8), intent(out) :: out(:)
        integer :: varid, st
        st = nf90_inq_varid(ncid, trim(name), varid)
        if (st /= nf90_noerr) then
            read_1d = .false.
            return
        end if
        st = nf90_get_var(ncid, varid, out)
        read_1d = (st == nf90_noerr)
    end function read_1d

    logical function read_surface_mask(ncid, reader)
        integer, intent(in) :: ncid
        type(reanalysis_reader_type), intent(inout) :: reader
        integer :: varid, st, nd, latp, lonp, depp, i, j
        integer :: vidims(3), cnt(3), strt(3), pos(3)
        real(8), allocatable :: buf(:, :, :)

        read_surface_mask = .false.
        st = nf90_inq_varid(ncid, 'mask', varid)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: static mask var not found'
            return
        end if
        st = nf90_inquire_variable(ncid, varid, ndims=nd, dimids=vidims)
        if (st /= nf90_noerr .or. nd /= 3) then
            print *, 'reanalysis_reader: static mask not 3-D'
            return
        end if
        latp = dimpos_by_name(ncid, vidims, nd, 'latitude')
        lonp = dimpos_by_name(ncid, vidims, nd, 'longitude')
        depp = dimpos_by_name(ncid, vidims, nd, 'depth')
        if (latp == 0 .or. lonp == 0 .or. depp == 0) then
            print *, 'reanalysis_reader: static mask axes not resolvable'
            return
        end if
        cnt = 1; cnt(latp) = reader%nlat; cnt(lonp) = reader%nlon; cnt(depp) = 1
        strt = 1
        allocate (buf(cnt(1), cnt(2), cnt(3)))
        st = nf90_get_var(ncid, varid, buf, start=strt, count=cnt)
        if (st /= nf90_noerr) then
            print *, 'reanalysis_reader: static mask read failed ', trim(nf90_strerror(st))
            deallocate (buf)
            return
        end if
        allocate (reader%mask_surface(reader%nlat, reader%nlon))
        do j = 1, reader%nlon
            do i = 1, reader%nlat
                pos = 1; pos(latp) = i; pos(lonp) = j
                reader%mask_surface(i, j) = buf(pos(1), pos(2), pos(3))
            end do
        end do
        deallocate (buf)
        read_surface_mask = .true.
    end function read_surface_mask

    integer function dimpos_by_name(ncid, vidims, nd, name) result(p)
        integer, intent(in) :: ncid, vidims(:), nd
        character(len=*), intent(in) :: name
        integer :: q, dlen
        character(len=nf90_max_name) :: dname
        p = 0
        do q = 1, nd
            if (nf90_inquire_dimension(ncid, vidims(q), name=dname, len=dlen) == nf90_noerr) then
                if (trim(dname) == trim(name)) then
                    p = q
                    return
                end if
            end if
        end do
    end function dimpos_by_name

    pure logical function is_nan(x)
        real(8), intent(in) :: x
        is_nan = (x /= x)
    end function is_nan

    real(8) pure function ice_val(x) result(r)
        real(8), intent(in) :: x
        if (x /= x) then
            r = 0.0_8
        else
            r = x
        end if
    end function ice_val

    real(8) function nan8const() result(n)
        integer(int64) :: bits
        bits = int(z'7FF8000000000000', int64)   ! IEEE-754 quiet NaN (bit pattern, без traps)
        n = transfer(bits, 1.0_8)
    end function nan8const

    ! Индекс пакетированного поля (1..7) по имени; 0 — неизвестно.
    integer pure function field_index(varname)
        character(len=*), intent(in) :: varname
        integer :: i
        character(len=8), parameter :: names(7) = &
            (/ 'thetao  ', 'so      ', 'uo      ', 'vo      ', &
               'zos     ', 'siconc  ', 'sithick ' /)
        field_index = 0
        do i = 1, 7
            if (trim(names(i)) == trim(varname)) then
                field_index = i
                return
            end if
        end do
    end function field_index

    ! Декод packed int16 → physical real(8): raw*scale + offset; fill → NaN.
    real(8) pure function decode_raw(rv, sf, off, fill) result(v)
        integer(kind=2), intent(in) :: rv, fill
        real(8), intent(in) :: sf, off
        integer(int64) :: bits
        if (rv == fill) then
            bits = int(z'7FF8000000000000', int64)
            v = transfer(bits, 1.0_8)
        else
            v = real(rv, 8)*sf + off
        end if
    end function decode_raw

    ! Прочитать scale_factor/add_offset/_FillValue для 7 полей в кэш reader'а.
    subroutine init_field_scaling(ncid, reader)
        integer, intent(in) :: ncid
        type(reanalysis_reader_type), intent(inout) :: reader
        integer :: i, varid, st, idx
        character(len=8) :: nm(7)
        nm(1) = 'thetao'; nm(2) = 'so'; nm(3) = 'uo'; nm(4) = 'vo'
        nm(5) = 'zos'; nm(6) = 'siconc'; nm(7) = 'sithick'
        reader%sf = 1.0_8; reader%ao = 0.0_8; reader%fillv = -32767_2
        do i = 1, 7
            st = nf90_inq_varid(ncid, trim(nm(i)), varid)
            if (st /= nf90_noerr) cycle
            idx = field_index(trim(nm(i)))
            if (idx == 0) cycle
            st = nf90_get_att(ncid, varid, 'scale_factor', reader%sf(idx))
            st = nf90_get_att(ncid, varid, 'add_offset', reader%ao(idx))
            st = nf90_get_att(ncid, varid, '_FillValue', reader%fillv(idx))
        end do
    end subroutine init_field_scaling

    subroutine ignore_close(st)
        integer, intent(in) :: st
    end subroutine ignore_close

end module reanalysis_reader
