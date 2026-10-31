! ==============================================================================
! Модуль: wave_forcing (Stage 12.6b, D-58)
! Чтение волнового реанализа (Arctic WAM subset) и формулы волновой эрозии.
!
! Bigg et al. (1997), как в NEMO-ICB icbthm.F90:
!   zMe = MAX( 1/12 * (SST+2) * Ss * (1 + cos(pi*c^3)), 0 ) / day   [m/s]
! (проверено по NEMO release-4.0 icbthm.F90; c=0 → фактор 2 (открытая вода),
!  c=1 → 0 (сплошной лёд) — ФИЗИЧЕСКИ ВЕРНО; в ТЗ Test-2 знаки перепутаны).
!
! Ss (sea state): в NEMO из ветра (1.5*sqrt(U)+0.1*U); здесь — Douglas scale
! из Hs (переходный документ §6.5). Это задокументированное отличие.
!
! Файл: регулярная lat/lon-сетка (подмножество), переменные Hs, Tp, dir,
! u_stokes, v_stokes c размерностями (time, latitude, longitude).
! Время: как у GLORYS — часы с 1950-01-01 (проверяется по диапазону).
! Отсутствие файла/переменной/вне домена → ok=.false.
!
! TEST-ONLY hooks (CI): wave_forcing_set_constant, wave_forcing_test_enable.
! ==============================================================================
module wave_forcing
    use iso_fortran_env, only: real64
    use netcdf
    implicit none

    private
    public :: wave_forcing_configure, get_wave_forcing
    public :: hs_to_sea_state, bigg_wave_melt
    public :: wave_forcing_set_constant, wave_forcing_clear_constant
    public :: wave_forcing_is_configured, wave_forcing_epoch
    public :: wave_forcing_set_epoch
    public :: wave_erosion_enabled, stokes_drift_enabled
    public :: wave_forcing_set_erosion_enabled, wave_forcing_set_stokes_enabled

    real(8), parameter :: SEC_PER_HOUR = 3600.0_8
    real(8), parameter :: HOURS_1950_TO_1970 = 175320.0_8
    real(8), parameter :: PI = 3.141592653589793_8

    integer, save :: ncid = -1
    integer, save :: nlat = 0, nlon = 0, ntime = 0
    integer, save :: did_lat = -1, did_lon = -1, did_tim = -1
    real(8), allocatable, save :: lat(:), lon(:), time_unix(:)
    real(8), save :: epoch_unix = 0.0_8
    logical, save :: configured = .false.
    logical, save :: use_constant = .false.
    logical, save :: ero_flag = .false., stk_flag = .false., gate_checked = .false.
    real(8), save :: c_hs = 0.0_8, c_tp = 0.0_8, c_dir = 0.0_8, c_ust = 0.0_8, c_vs = 0.0_8

contains

    logical function wave_erosion_enabled()
        character(len=64) :: ev
        if (.not. gate_checked) then
            ev = ''
            call get_environment_variable('ICEBERG_WAVE_EROSION', ev)
            ero_flag = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
            ev = ''
            call get_environment_variable('ICEBERG_STOKES_DRIFT', ev)
            stk_flag = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
            gate_checked = .true.
        end if
        wave_erosion_enabled = ero_flag
    end function wave_erosion_enabled

    logical function stokes_drift_enabled()
        character(len=64) :: ev
        if (.not. gate_checked) then
            ev = ''
            call get_environment_variable('ICEBERG_WAVE_EROSION', ev)
            ero_flag = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
            ev = ''
            call get_environment_variable('ICEBERG_STOKES_DRIFT', ev)
            stk_flag = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
            gate_checked = .true.
        end if
        stokes_drift_enabled = stk_flag
    end function stokes_drift_enabled

    subroutine wave_forcing_set_erosion_enabled(flag)
        logical, intent(in) :: flag
        ero_flag = flag; gate_checked = .true.
    end subroutine wave_forcing_set_erosion_enabled

    subroutine wave_forcing_set_stokes_enabled(flag)
        logical, intent(in) :: flag
        stk_flag = flag; gate_checked = .true.
    end subroutine wave_forcing_set_stokes_enabled

    subroutine wave_forcing_set_epoch(epoch)
        real(8), intent(in) :: epoch
        epoch_unix = epoch
    end subroutine wave_forcing_set_epoch

    real(8) function wave_forcing_epoch() result(e)
        e = epoch_unix
    end function wave_forcing_epoch

    logical function wave_forcing_is_configured()
        wave_forcing_is_configured = configured .or. use_constant
    end function wave_forcing_is_configured

    ! TEST-ONLY: постоянные волновые условия (без файла).
    subroutine wave_forcing_set_constant(hs, tp, dirw, ust, vs)
        real(8), intent(in) :: hs, tp, dirw, ust, vs
        use_constant = .true.
        c_hs = hs; c_tp = tp; c_dir = dirw; c_ust = ust; c_vs = vs
    end subroutine wave_forcing_set_constant

    subroutine wave_forcing_clear_constant()
        use_constant = .false.
    end subroutine wave_forcing_clear_constant

    ! ==========================================================================
    subroutine wave_forcing_configure(wave_nc_file)
        character(len=*), intent(in) :: wave_nc_file
        logical :: ex
        integer :: st, d
        real(8), allocatable :: thrs(:)
        integer :: i

        inquire (file=trim(wave_nc_file), exist=ex)
        if (.not. ex) return
        st = nf90_open(trim(wave_nc_file), nf90_nowrite, ncid)
        if (st /= nf90_noerr) return
        if (.not. rdim('latitude', did_lat, nlat)) return
        if (.not. rdim('longitude', did_lon, nlon)) return
        if (.not. rdim('time', did_tim, ntime)) return
        allocate (lat(nlat), lon(nlon), time_unix(ntime))
        if (.not. r1d('latitude', lat)) return
        if (.not. r1d('longitude', lon)) return
        allocate (thrs(ntime))
        if (.not. r1d('time', thrs)) then
            deallocate (thrs); return
        end if
        do i = 1, ntime
            time_unix(i) = (thrs(i) - HOURS_1950_TO_1970)*SEC_PER_HOUR
        end do
        deallocate (thrs)
        configured = .true.
    end subroutine wave_forcing_configure

    ! ==========================================================================
    subroutine get_wave_forcing(lat0, lon0, time_sec, Hs, Tp, dir_w, u_stokes, v_stokes, ok)
        real(8), intent(in) :: lat0, lon0, time_sec
        real(8), intent(out) :: Hs, Tp, dir_w, u_stokes, v_stokes
        logical, intent(out) :: ok
        real(8) :: t, vals(5)
        integer :: i_lo, j_lo, t_lo, t_cnt, nv
        real(8) :: yl, yn, tf
        character(len=*), parameter :: names(5) = &
            (/ 'Hs        ', 'Tp        ', 'dir       ', 'u_stokes  ', 'v_stokes  ' /)

        ok = .false.
        Hs = 0.0_8; Tp = 0.0_8; dir_w = 0.0_8; u_stokes = 0.0_8; v_stokes = 0.0_8
        if (use_constant) then
            Hs = c_hs; Tp = c_tp; dir_w = c_dir; u_stokes = c_ust; v_stokes = c_vs
            if (Hs >= 0.0_8) ok = .true.
            return
        end if
        if (.not. configured) return
        if (lat0 < lat(1) .or. lat0 > lat(nlat)) return
        if (lon0 < lon(1) .or. lon0 > lon(nlon)) return
        if (time_sec < time_unix(1) .or. time_sec > time_unix(ntime)) return

        i_lo = lower(lat, nlat, lat0); yl = frac(lat, nlat, i_lo, lat0)
        j_lo = lower(lon, nlon, lon0); yn = frac(lon, nlon, j_lo, lon0)
        if (time_sec <= time_unix(1)) then
            t_lo = 1; t_cnt = 1; tf = 0.0_8
        else if (time_sec >= time_unix(ntime)) then
            t_lo = ntime; t_cnt = 1; tf = 0.0_8
        else
            t_lo = lower(time_unix, ntime, time_sec); t_cnt = 2
            tf = frac(time_unix, ntime, t_lo, time_sec)
        end if

        do nv = 1, 5
            if (.not. read_block(trim(names(nv)), j_lo, i_lo, t_lo, t_cnt, yl, yn, tf, vals(nv))) return
        end do
        Hs = vals(1); Tp = vals(2); dir_w = vals(3); u_stokes = vals(4); v_stokes = vals(5)
        ok = .true.
    end subroutine get_wave_forcing

    logical function read_block(varname, j_lo, i_lo, t_lo, t_cnt, yl, yn, tf, val)
        character(len=*), intent(in) :: varname
        integer, intent(in) :: j_lo, i_lo, t_lo, t_cnt
        real(8), intent(in) :: yl, yn, tf
        real(8), intent(out) :: val
        integer :: varid, st, cnt(3), strt(3)
        real(8), allocatable :: b(:,:,:)
        real(8) :: h1, h2
        read_block = .false.
        st = nf90_inq_varid(ncid, trim(varname), varid)
        if (st /= nf90_noerr) return
        cnt = (/ 2, 2, t_cnt /)
        strt = (/ j_lo, i_lo, t_lo /)
        allocate (b(2, 2, t_cnt))
        st = nf90_get_var(ncid, varid, b, start=strt, count=cnt)
        if (st /= nf90_noerr) then
            deallocate (b); return
        end if
        ! b(jlon, ilat, itime); yl=lat fraction (i), yn=lon fraction (j)
        h1 = (1.0_8 - yl)*(1.0_8 - yn)*b(1, 1, 1) + (1.0_8 - yl)*yn*b(2, 1, 1) + &
             yl*(1.0_8 - yn)*b(1, 2, 1) + yl*yn*b(2, 2, 1)
        if (t_cnt == 2) then
            h2 = (1.0_8 - yl)*(1.0_8 - yn)*b(1, 1, 2) + (1.0_8 - yl)*yn*b(2, 1, 2) + &
                 yl*(1.0_8 - yn)*b(1, 2, 2) + yl*yn*b(2, 2, 2)
            val = (1.0_8 - tf)*h1 + tf*h2
        else
            val = h1
        end if
        read_block = .true.
        deallocate (b)
    end function read_block

    integer function lower(arr, n, x) result(k)
        real(8), intent(in) :: arr(:), x
        integer, intent(in) :: n
        if (x <= arr(1)) then; k = 1; return; end if
        if (x >= arr(n)) then; k = n - 1; return; end if
        k = 1
        do while (k < n - 1 .and. arr(k + 1) <= x)
            k = k + 1
        end do
    end function lower

    real(8) function frac(arr, n, k, x) result(f)
        real(8), intent(in) :: arr(:), x
        integer, intent(in) :: n, k
        f = 0.0_8
        if (k < n) f = (x - arr(k))/(arr(k + 1) - arr(k))
        f = max(0.0_8, min(1.0_8, f))
    end function frac

    ! ==========================================================================
    ! Douglas Sea Scale из Hs (переходный документ §6.5; WMO 3700).
    ! ==========================================================================
    pure integer function hs_to_sea_state(hs) result(ss)
        real(8), intent(in) :: hs
        if (hs < 0.1_8) then
            ss = 0
        else if (hs < 0.5_8) then
            ss = 1
        else if (hs < 1.25_8) then
            ss = 2
        else if (hs < 2.5_8) then
            ss = 3
        else if (hs < 4.0_8) then
            ss = 4
        else if (hs < 6.0_8) then
            ss = 5
        else if (hs < 9.0_8) then
            ss = 6
        else if (hs < 14.0_8) then
            ss = 7
        else
            ss = 8
        end if
    end function hs_to_sea_state

    ! Bigg 1997 / NEMO icbthm.F90 eqn M.A8: m_wave [m/s], c=ice concentration.
    ! c=0 → (1+cos 0)=2 (open water, max); c=1 → (1+cos π)=0 (full cover).
    pure real(8) function bigg_wave_melt(ss, c_ice, t_w) result(m)
        real(8), intent(in) :: ss, c_ice, t_w
        real(8) :: cc
        cc = max(0.0_8, min(1.0_8, c_ice))
        m = max(0.0_8, (1.0_8/12.0_8)*(t_w + 2.0_8)*ss* &
                       (1.0_8 + cos(PI*cc**3)))/86400.0_8
    end function bigg_wave_melt

    logical function rdim(name, did, n)
        character(len=*), intent(in) :: name
        integer, intent(out) :: did, n
        integer :: st
        st = nf90_inq_dimid(ncid, trim(name), did)
        if (st /= nf90_noerr) then; rdim = .false.; return; end if
        st = nf90_inquire_dimension(ncid, did, len=n)
        rdim = (st == nf90_noerr)
    end function rdim

    logical function r1d(name, out)
        character(len=*), intent(in) :: name
        real(8), intent(out) :: out(:)
        integer :: varid, st
        st = nf90_inq_varid(ncid, trim(name), varid)
        if (st /= nf90_noerr) then; r1d = .false.; return; end if
        st = nf90_get_var(ncid, varid, out)
        r1d = (st == nf90_noerr)
    end function r1d

end module wave_forcing
