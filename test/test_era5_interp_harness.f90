! ==============================================================================
! test_era5_interp_harness.f90 — T1 verification of the PRODUCTION ERA5 reader
!
! Calls netcdf_input's production API (era5_open / era5_bilinear2d /
! era5_find_time_index) on self-generated synthetic ERA5-like files:
!   File A: times t0, +6h, +12h; latitude 70..60 DECREASING (flip test);
!           longitude -180..135 step 45 (global circular axis).
!           u10 = 10 + 0.5*lat + 0.1*lon (linear -> bilinear exact)
!           v10 = 180 at lon=-180, 135 at lon=135 (dateline wrap probe)
!   File B: times t0, +6h, +24h (24-hour gap test).
!
! JSON: data/validation/era5_{spatial,temporal}_interp_fortran.json
! ==============================================================================
program test_era5_interp_harness
    use netcdf
    use netcdf_input, only: era5_open, era5_bilinear2d, era5_find_time_index, &
                            era5_time, era5_ntime, era5_lat, era5_lon, era5_nlon, era5_u10, era5_v10
    use stage118_physics_switches, only: s118_init, s118_lon_clamp
    implicit none

    integer, parameter :: NT = 3, NLAT = 6, NLON = 8
    real(8), parameter :: T0 = 1577836800.0_8
    real(8), parameter :: DT6 = 21600.0_8
    character(len=256), parameter :: fA = 'build/t1_synthetic_era5.nc'
    character(len=256), parameter :: fB = 'build/t1_synthetic_era5_gap.nc'
    character(len=256), parameter :: fC = 'build/t2_era5_narrow_wrap.nc'
    integer :: ios

    call s118_init()
    call build_synthetic(trim(fA), .false.)
    call build_synthetic(trim(fB), .true.)
    call build_narrow(trim(fC))
    call run_spatial(trim(fA))
    call run_temporal(trim(fA), trim(fB))
    call run_wrap_redtest(trim(fC))
    print *, '=== T1 ERA5 interpolation harness complete ==='
    stop 0

contains

    ! ==========================================================================
    subroutine build_synthetic(path, gap)
        character(len=*), intent(in) :: path
        logical, intent(in) :: gap
        integer :: ncid, dv, dla, dlo, vu, vv, vtime, vla, vlo, vt2, vd2, vm, vc, vs
        integer :: dl(3)
        real(8) :: times(NT), latv(NLAT), lonv(NLON)
        real(4), allocatable :: buf(:, :, :)
        integer :: i, j, k

        latv = (/70.0_8, 68.0_8, 66.0_8, 64.0_8, 62.0_8, 60.0_8/)
        lonv = (/-180.0_8, -135.0_8, -90.0_8, -45.0_8, 0.0_8, 45.0_8, 90.0_8, 135.0_8/)
        times(1) = T0
        times(2) = T0 + DT6
        times(3) = merge(T0 + 2.0_8*DT6, T0 + 86400.0_8, .not. gap)

        call chk(nf90_create(trim(path), NF90_CLOBBER, ncid), 'create '//trim(path))
        call chk(nf90_def_dim(ncid, 'valid_time', NT, dv), 'def valid_time')
        call chk(nf90_def_dim(ncid, 'latitude', NLAT, dla), 'def latitude')
        call chk(nf90_def_dim(ncid, 'longitude', NLON, dlo), 'def longitude')
        dl = (/dlo, dla, dv/)   ! Fortran order: C file becomes (time,lat,lon)
        call chk(nf90_def_var(ncid, 'valid_time', NF90_DOUBLE, (/dv/), vtime), 'def t')
        call chk(nf90_def_var(ncid, 'latitude', NF90_DOUBLE, (/dla/), vla), 'def la')
        call chk(nf90_def_var(ncid, 'longitude', NF90_DOUBLE, (/dlo/), vlo), 'def lo')
        call chk(nf90_def_var(ncid, 'u10', NF90_REAL, dl, vu), 'def u10')
        call chk(nf90_def_var(ncid, 'v10', NF90_REAL, dl, vv), 'def v10')
        call chk(nf90_def_var(ncid, 't2m', NF90_REAL, dl, vt2), 'def t2m')
        call chk(nf90_def_var(ncid, 'd2m', NF90_REAL, dl, vd2), 'def d2m')
        call chk(nf90_def_var(ncid, 'msl', NF90_REAL, dl, vm), 'def msl')
        call chk(nf90_def_var(ncid, 'tcc', NF90_REAL, dl, vc), 'def tcc')
        call chk(nf90_def_var(ncid, 'sf', NF90_REAL, dl, vs), 'def sf')
        call chk(nf90_enddef(ncid), 'enddef')

        call chk(nf90_put_var(ncid, vtime, times), 'put time')
        call chk(nf90_put_var(ncid, vla, latv), 'put lat')
        call chk(nf90_put_var(ncid, vlo, lonv), 'put lon')

        allocate (buf(NLON, NLAT, NT))
        do k = 1, NT
            do j = 1, NLAT
                do i = 1, NLON
                    buf(i, j, k) = real(10.0_8 + 0.5_8*latv(j) + 0.1_8*lonv(i), 4)
                end do
            end do
        end do
        call chk(nf90_put_var(ncid, vu, buf), 'put u10')
        do k = 1, NT
            do j = 1, NLAT
                do i = 1, NLON
                    if (lonv(i) == -180.0_8) then
                        buf(i, j, k) = 180.0_4
                    else if (lonv(i) == 135.0_8) then
                        buf(i, j, k) = 135.0_4
                    else
                        buf(i, j, k) = 0.0_4
                    end if
                end do
            end do
        end do
        call chk(nf90_put_var(ncid, vv, buf), 'put v10')
        buf = 280.0_4;    call chk(nf90_put_var(ncid, vt2, buf), 'put t2m')
        buf = 270.0_4;    call chk(nf90_put_var(ncid, vd2, buf), 'put d2m')
        buf = 100000.0_4; call chk(nf90_put_var(ncid, vm, buf), 'put msl')
        buf = 0.5_4;      call chk(nf90_put_var(ncid, vc, buf), 'put tcc')
        buf = 0.0_4;      call chk(nf90_put_var(ncid, vs, buf), 'put sf')
        deallocate (buf)
        call chk(nf90_close(ncid), 'close')
    end subroutine build_synthetic

    ! ==========================================================================
    ! Narrow-span file for the T-23 red test: longitude 10..70 E only.
    subroutine build_narrow(path)
        character(len=*), intent(in) :: path
        integer, parameter :: NL = 7
        integer :: ncid, dv, dla, dlo, vu, vv, vt2, vd2, vm, vc, vs, vtime, vla, vlo
        integer :: dl(3)
        real(8) :: times(1), latv(NLAT), lonv(NL)
        real(4), allocatable :: buf(:, :, :)
        integer :: i, j

        latv = (/70.0_8, 68.0_8, 66.0_8, 64.0_8, 62.0_8, 60.0_8/)
        lonv = (/10.0_8, 20.0_8, 30.0_8, 40.0_8, 50.0_8, 60.0_8, 70.0_8/)
        times(1) = T0

        call chk(nf90_create(trim(path), NF90_CLOBBER, ncid), 'create '//trim(path))
        call chk(nf90_def_dim(ncid, 'valid_time', 1, dv), 'def valid_time')
        call chk(nf90_def_dim(ncid, 'latitude', NLAT, dla), 'def latitude')
        call chk(nf90_def_dim(ncid, 'longitude', NL, dlo), 'def longitude')
        dl = (/dlo, dla, dv/)
        call chk(nf90_def_var(ncid, 'valid_time', NF90_DOUBLE, (/dv/), vtime), 'def t')
        call chk(nf90_def_var(ncid, 'latitude', NF90_DOUBLE, (/dla/), vla), 'def la')
        call chk(nf90_def_var(ncid, 'longitude', NF90_DOUBLE, (/dlo/), vlo), 'def lo')
        call chk(nf90_def_var(ncid, 'u10', NF90_REAL, dl, vu), 'def u10')
        call chk(nf90_def_var(ncid, 'v10', NF90_REAL, dl, vv), 'def v10')
        call chk(nf90_def_var(ncid, 't2m', NF90_REAL, dl, vt2), 'def t2m')
        call chk(nf90_def_var(ncid, 'd2m', NF90_REAL, dl, vd2), 'def d2m')
        call chk(nf90_def_var(ncid, 'msl', NF90_REAL, dl, vm), 'def msl')
        call chk(nf90_def_var(ncid, 'tcc', NF90_REAL, dl, vc), 'def tcc')
        call chk(nf90_def_var(ncid, 'sf', NF90_REAL, dl, vs), 'def sf')
        call chk(nf90_enddef(ncid), 'enddef')
        call chk(nf90_put_var(ncid, vtime, times), 'put time')
        call chk(nf90_put_var(ncid, vla, latv), 'put lat')
        call chk(nf90_put_var(ncid, vlo, lonv), 'put lon')
        allocate (buf(NL, NLAT, 1))
        do j = 1, NLAT
            do i = 1, NL
                buf(i, j, 1) = real(lonv(i), 4)   ! value == longitude node
            end do
        end do
        call chk(nf90_put_var(ncid, vu, buf), 'put u10')
        buf = 0.0_4
        call chk(nf90_put_var(ncid, vv, buf), 'put v10')
        buf = 280.0_4;    call chk(nf90_put_var(ncid, vt2, buf), 'put t2m')
        buf = 270.0_4;    call chk(nf90_put_var(ncid, vd2, buf), 'put d2m')
        buf = 100000.0_4; call chk(nf90_put_var(ncid, vm, buf), 'put msl')
        buf = 0.5_4;      call chk(nf90_put_var(ncid, vc, buf), 'put tcc')
        buf = 0.0_4;      call chk(nf90_put_var(ncid, vs, buf), 'put sf')
        deallocate (buf)
        call chk(nf90_close(ncid), 'close')
    end subroutine build_narrow

    ! ==========================================================================
    ! T-23 RED TEST: query EAST of a narrow file (10..70 E) at 75 E.
    ! Correct behaviour (future fix): CLAMP to the eastern edge -> 70.
    ! Current behaviour (wrap bug): +-360 normalization lands at -285, the
    ! binary search/weight clamp then returns the WESTERN edge -> 10.
    subroutine run_wrap_redtest(path)
        character(len=*), intent(in) :: path
        integer :: ios, unit
        real(8) :: v_east, v_west
        logical :: ok_e, ok_w

        call era5_open(trim(path), ios)
        if (ios /= 0) call die('era5_open narrow')

        v_east = -999.0_8
        ok_e = era5_bilinear2d(era5_u10(:, :, 1), 65.0_8, 75.0_8, v_east)
        v_west = -999.0_8
        ok_w = era5_bilinear2d(era5_u10(:, :, 1), 65.0_8, 5.0_8, v_west)

        unit = 73
        open (unit, file='data/validation/era5_longitude_wrap_fortran.json', &
              status='replace', action='write')
        call jopen(unit)
        call js_str(unit, 'test', 'era5_longitude_wrap_T23')
        call js_str(unit, 'reader', 'src/netcdf_input.f90::era5_bilinear2d')
        call js_real(unit, 'file_lon_min', 10.0_8)
        call js_real(unit, 'file_lon_max', 70.0_8)
        call js_real(unit, 'query_east_lon', 75.0_8)
        call js_bool(unit, 'query_east_ok', ok_e)
        call js_real(unit, 'query_east_actual', v_east)
        call js_real(unit, 'query_east_correct_clamp', 70.0_8)
        call js_real(unit, 'query_west_lon', 5.0_8)
        call js_bool(unit, 'query_west_ok', ok_w)
        call js_real(unit, 'query_west_actual', v_west)
        call js_real(unit, 'query_west_correct_clamp', 10.0_8)
        call js_last(unit, 'status', 'RED_CONFIRMED')
        call jclose(unit)
        close (unit)

        print *, '[wrap-T23] 75E -> actual ', v_east, &
                 ' (correct clamp 70.0); 5E -> actual ', v_west, ' (correct 10.0)'
    end subroutine run_wrap_redtest

    ! ==========================================================================
    subroutine run_spatial(path)
        character(len=*), intent(in) :: path
        real(8) :: plat(4), plon(4), expect(4), val, maxerr, wval, werr, wexp
        logical :: ok, out_hi, out_lo, edge_hi, edge_lo
        integer :: i, ios, unit
        character(len=8) :: st_interior, st_wrap, st_edges, overall

        plat = (/68.0_8, 65.0_8, 62.0_8, 66.0_8/)
        plon = (/-170.0_8, -20.0_8, 90.0_8, 130.0_8/)
        do i = 1, 4
            expect(i) = 10.0_8 + 0.5_8*plat(i) + 0.1_8*plon(i)
        end do

        call era5_open(trim(path), ios)
        if (ios /= 0) call die('era5_open '//trim(path))
        if (abs(era5_lat(1) - 60.0_8) > 1e-6_8 .or. &
            abs(era5_lat(NLAT) - 70.0_8) > 1e-6_8) &
            call die('reader did not flip decreasing latitude')

        maxerr = 0.0_8
        do i = 1, 4
            ok = era5_bilinear2d(era5_u10(:, :, 1), plat(i), plon(i), val)
            if (.not. ok) call die('interior probe rejected')
            maxerr = max(maxerr, abs(val - expect(i)))
        end do
        st_interior = status_of(maxerr < 1.0e-4_8)

        ! dateline probe. Legacy cyclic axis expects 170 (wrap); with
        ! STAGE118_LON_CLAMP=true the east edge (135) is the correct clamp.
        wval = -9999.0_8
        ok = era5_bilinear2d(era5_v10(:, :, 1), 65.0_8, 170.0_8, wval)
        if (s118_lon_clamp) then
            wexp = era5_lon(era5_nlon)
        else
            wexp = 170.0_8
        end if
        werr = abs(wval - wexp)
        if (.not. ok) werr = huge(1.0_8)
        st_wrap = 'WARNING '
        if (werr < 1.0e-4_8) st_wrap = 'PASS    '

        out_hi = era5_bilinear2d(era5_u10(:, :, 1), 80.0_8, 0.0_8, val)
        out_lo = era5_bilinear2d(era5_u10(:, :, 1), 55.0_8, 0.0_8, val)
        edge_hi = era5_bilinear2d(era5_u10(:, :, 1), 70.0_8, 0.0_8, val)
        edge_lo = era5_bilinear2d(era5_u10(:, :, 1), 60.0_8, 0.0_8, val)
        st_edges = status_of((.not. out_hi) .and. (.not. out_lo) .and. &
                             edge_hi .and. edge_lo)

        overall = 'PASS    '
        if (trim(st_wrap) /= 'PASS') overall = 'WARNING '
        if (trim(st_interior) /= 'PASS' .or. trim(st_edges) /= 'PASS') &
            overall = 'FAIL    '

        unit = 71
        open (unit, file='data/validation/era5_spatial_interp_fortran.json', &
              status='replace', action='write')
        call jopen(unit)
        call js_str(unit, 'test', 'era5_spatial_interp')
        call js_str(unit, 'reader', 'src/netcdf_input.f90::era5_bilinear2d')
        call js_str(unit, 'method', 'bilinear_on_regular_latlon')
        call js_real(unit, 'interior_max_abs_err', maxerr)
        call js_str(unit, 'interior_status', trim(st_interior))
        call js_real(unit, 'wrap_expected', wexp)
        call js_real(unit, 'wrap_actual', wval)
        call js_real(unit, 'wrap_abs_err', werr)
        call js_str(unit, 'wrap_status', trim(st_wrap))
        call js_bool(unit, 'lat_outside_high_rejected', .not. out_hi)
        call js_bool(unit, 'lat_outside_low_rejected', .not. out_lo)
        call js_bool(unit, 'lat_edge_nodes_accepted', edge_hi .and. edge_lo)
        call js_str(unit, 'edges_status', trim(st_edges))
        call js_last(unit, 'status', trim(overall))
        call jclose(unit)
        close (unit)

        print *, '[spatial] interior max err = ', maxerr, ' status=', trim(st_interior)
        print *, '[spatial] wrap 170E expected', wexp, ': actual=', wval, &
                 ' err=', werr, ' status=', trim(st_wrap)
        print *, '[spatial] edges=', trim(st_edges), ' overall=', trim(overall)
    end subroutine run_spatial

    ! ==========================================================================
    subroutine run_temporal(pathA, pathB)
        character(len=*), intent(in) :: pathA, pathB
        integer :: ios, i1, i2, i3, ib1, ib4, itie, ibefore, iafter
        integer :: g12, g15, g21, i, unit
        logical :: monot
        character(len=8) :: st_basic, st_gap, st_axis, overall

        call era5_open(trim(pathA), ios)
        if (ios /= 0) call die('era5_open A')
        call era5_find_time_index(T0, i1)
        call era5_find_time_index(T0 + DT6, i2)
        call era5_find_time_index(T0 + 2.0_8*DT6, i3)
        call era5_find_time_index(T0 + 3600.0_8, ib1)
        call era5_find_time_index(T0 + 14400.0_8, ib4)
        call era5_find_time_index(T0 + 10800.0_8, itie)
        call era5_find_time_index(T0 - 3600.0_8, ibefore)
        call era5_find_time_index(T0 + 2.0_8*DT6 + 3600.0_8, iafter)
        st_basic = status_of(i1 == 1 .and. i2 == 2 .and. i3 == 3 .and. &
                             ib1 == 1 .and. ib4 == 2 .and. itie == 1 .and. &
                             ibefore == 1 .and. iafter == 3)

        monot = .true.
        do i = 1, era5_ntime - 1
            if (era5_time(i + 1) <= era5_time(i)) monot = .false.
        end do
        st_axis = status_of(monot .and. abs(era5_time(1) - T0) < 1e-6_8)

        call era5_open(trim(pathB), ios)
        if (ios /= 0) call die('era5_open B')
        call era5_find_time_index(T0 + 12.0_8*3600.0_8, g12)
        call era5_find_time_index(T0 + 15.0_8*3600.0_8, g15)
        call era5_find_time_index(T0 + 21.0_8*3600.0_8, g21)
        st_gap = status_of(g12 == 2 .and. g15 == 2 .and. g21 == 3)

        overall = 'PASS    '
        if (trim(st_basic) /= 'PASS' .or. trim(st_gap) /= 'PASS' .or. &
            trim(st_axis) /= 'PASS') overall = 'FAIL    '

        unit = 72
        open (unit, file='data/validation/era5_temporal_interp_fortran.json', &
              status='replace', action='write')
        call jopen(unit)
        call js_str(unit, 'test', 'era5_temporal_interp')
        call js_str(unit, 'reader', 'src/netcdf_input.f90::era5_find_time_index')
        call js_str(unit, 'method', 'nearest_time_with_clamping')
        call js_int(unit, 'exact_0h', i1)
        call js_int(unit, 'exact_6h', i2)
        call js_int(unit, 'exact_12h', i3)
        call js_int(unit, 'between_1h', ib1)
        call js_int(unit, 'between_4h', ib4)
        call js_int(unit, 'tie_3h', itie)
        call js_int(unit, 'before_range_clamped', ibefore)
        call js_int(unit, 'after_range_clamped', iafter)
        call js_int(unit, 'gap_12h', g12)
        call js_int(unit, 'gap_15h_tie', g15)
        call js_int(unit, 'gap_21h', g21)
        call js_str(unit, 'basic_status', trim(st_basic))
        call js_str(unit, 'gap_status', trim(st_gap))
        call js_str(unit, 'axis_status', trim(st_axis))
        call js_last(unit, 'status', trim(overall))
        call jclose(unit)
        close (unit)

        print *, '[temporal] basic=', trim(st_basic), ' gap=', trim(st_gap), &
                 ' axis=', trim(st_axis), ' overall=', trim(overall)
    end subroutine run_temporal

    ! ---------------- tiny JSON helpers (quotes via achar(34)) ---------------
    pure function qq() result(s)
        character(len=1) :: s
        s = achar(34)
    end function qq

    function status_of(cond) result(s)
        logical, intent(in) :: cond
        character(len=8) :: s
        s = 'FAIL    '
        if (cond) s = 'PASS    '
    end function status_of

    subroutine jopen(unit)
        integer, intent(in) :: unit
        write (unit, '(A)') '{'
    end subroutine jopen

    subroutine jclose(unit)
        integer, intent(in) :: unit
        write (unit, '(A)') '}'
    end subroutine jclose

    subroutine js_str(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()//','
    end subroutine js_str

    subroutine js_last(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()
    end subroutine js_last

    subroutine js_real(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        real(8), intent(in) :: val
        write (unit, '(A,ES18.10,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_real

    subroutine js_int(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        integer, intent(in) :: val
        write (unit, '(A,I0,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_int

    subroutine js_bool(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        logical, intent(in) :: val
        character(len=5) :: s
        s = 'false'
        if (val) s = 'true '
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//s//','
    end subroutine js_bool

    subroutine chk(status, what)
        integer, intent(in) :: status
        character(len=*), intent(in) :: what
        if (status /= NF90_NOERR) call die(trim(what)//': '//trim(nf90_strerror(status)))
    end subroutine chk

    subroutine die(msg)
        character(len=*), intent(in) :: msg
        print *, 'FATAL harness: ', trim(msg)
        error stop 1
    end subroutine die

end program test_era5_interp_harness