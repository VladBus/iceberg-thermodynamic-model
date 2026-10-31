! ==============================================================================
! iceberg_run (Stage 12.6a, D-57)
! Минимальный автономный лагранжев прогон айсберга на реанализе GLORYS12
! (+опционально ERA5). Без океанской модели; one-way (D-51).
!
! Использование:
!   fpm run iceberg_run -- <lat0> <lon0> <L> <W> <H> <days> <dt> <out.nc> \
!                         [daily.nc] [static.nc] [era5.nc]
! По умолчанию daily/static — пути Stage 12.1; при отсутствии daily → SKIP.
!
! Батиметрия/грунтование — IBCAO-сетка (coup1 + latlon_to_model_coords).
! Атмосфера: если era5.nc задан и открывается — ERA5; иначе холодная
! константа (документированное ограничение 12.6a).
! ==============================================================================
program iceberg_run
    use iso_fortran_env, only: real64
    use netcdf
    use param, only: nat, ht
    use grid_coupling, only: coup1
    use iceberg_types
    use iceberg, only: iceberg_init, iceberg_step, iceberg_set_latlon_mode
    use iceberg_forcing, only: ocean_forcing_configure, get_ocean_profile, &
                               get_atmos_forcing, latlon_to_model_coords, &
                               model_coords_to_indices
    use ocean_provider, only: SRC_REANALYSIS
    use netcdf_input, only: era5_open, era5_is_open
    implicit none

    character(len=*), parameter :: DEF_DAILY = &
        'data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc'
    character(len=*), parameter :: DEF_STATIC = &
        'data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc'
    real(8), parameter :: EPOCH_2020 = 1577836800.0d0   ! 2020-01-01T00:00:00Z

    type(iceberg_state) :: st
    type(iceberg_diagnostics) :: diag
    type(ocean_profile) :: prof
    type(atmos_forcing) :: atmos
    real(8) :: lat0, lon0, L0, W0, H0, days, dt
    real(8) :: t, depth, draft, time_sec
    real(4) :: xm4, ym4
    real(8), allocatable :: rt(:), rlat(:), rlon(:), rmass(:), rdraft(:), rti(:)
    character(len=512) :: out_nc, daily, static, era5f, arg
    integer :: nrec, irec, ncid, dimt, vt, vla, vlo, vma, vdr, vti, stt
    integer :: nargs, istat, ii, jj
    logical :: ok, gok, have_era5

    nargs = command_argument_count()
    if (nargs < 8) then
        print *, 'Usage: iceberg_run lat0 lon0 L W H days dt out.nc [daily] [static] [era5]'
        stop 2
    end if
    call get_arg(1, arg); read (arg, *) lat0
    call get_arg(2, arg); read (arg, *) lon0
    call get_arg(3, arg); read (arg, *) L0
    call get_arg(4, arg); read (arg, *) W0
    call get_arg(5, arg); read (arg, *) H0
    call get_arg(6, arg); read (arg, *) days
    call get_arg(7, arg); read (arg, *) dt
    call get_arg(8, arg); out_nc = trim(arg)
    daily = DEF_DAILY; static = DEF_STATIC; era5f = ''
    if (nargs >= 9) then; call get_arg(9, arg); daily = trim(arg); end if
    if (nargs >= 10) then; call get_arg(10, arg); static = trim(arg); end if
    if (nargs >= 11) then; call get_arg(11, arg); era5f = trim(arg); end if

    inquire (file=trim(daily), exist=ok)
    if (.not. ok) then
        print *, 'SKIP: reanalysis daily file absent: ', trim(daily)
        stop 0
    end if
    inquire (file='data/input/processed/grid/grid.nc', exist=ok)
    if (.not. ok) then
        print *, 'SKIP: grid.nc absent (IBCAO grid required)'
        stop 0
    end if

    ! Grid + IBCAO bathymetry (model grid built from IBCAO) + solar date
    call coup1()
    nat(1) = 2020; nat(2) = 1; nat(3) = 1; nat(4) = 0
    call ocean_forcing_configure(SRC_REANALYSIS, trim(daily), trim(static))
    call iceberg_set_latlon_mode(.true.)
    call iceberg_init(st, 0.0, 0.0, real(L0, 4), real(W0, 4), real(H0, 4), &
                      real(lat0, 4), real(lon0, 4), 0.0, 0.0)
    st%T_ice = -10.0d0

    have_era5 = .false.
    if (len_trim(era5f) > 0) then
        call era5_open(trim(era5f), istat)
        have_era5 = (istat == 0) .and. era5_is_open
        if (.not. have_era5) print *, 'WARN: ERA5 not opened; using constant atmosphere'
    end if

    nrec = max(int(days*86400.0d0/dt) + 1, 1)
    allocate (rt(nrec), rlat(nrec), rlon(nrec), rmass(nrec), rdraft(nrec), rti(nrec))

    do irec = 1, nrec
        t = real(irec - 1, 8)*dt
        time_sec = EPOCH_2020 + t
        draft = st%H*real(RHO_ICE, 8)/real(RHO_WATER, 8)

        ! IBCAO depth at current lat/lon (nearest grid cell)
        depth = 1000.0d0
        call latlon_to_model_coords(real(st%latitude, 4), real(st%longitude, 4), &
                                    xm4, ym4, gok)
        if (gok) then
            call model_coords_to_indices(xm4, ym4, ii, jj, gok)
            if (gok .and. ii >= 1 .and. ii <= 133 .and. jj >= 1 .and. jj <= 105) then
                if (abs(ht(ii, jj) - 8888.0) > 1.0e-8) depth = real(ht(ii, jj), 8)*0.01d0
            end if
        end if

        call get_ocean_profile(0.0d0, 0.0d0, st%latitude, st%longitude, draft, &
                               0.0d0, 0.0d0, prof, ok, time_sec)
        if (.not. ok) then
            print *, 'STOP: no valid reanalysis ocean at lat/lon/time:', st%latitude, st%longitude
            nrec = irec - 1
            exit
        end if

        if (have_era5) then
            call get_atmos_forcing(st%latitude, st%longitude, real(time_sec, 4), atmos, ok)
            if (.not. ok) then
                print *, 'WARN: ERA5 interp failed; constant atmosphere'
                call constant_atmos(atmos)
            end if
        else
            call constant_atmos(atmos)
        end if

        call iceberg_step(st, real(dt, 4), prof, atmos, real(depth, 4), diag=diag)
        rt(irec) = t; rlat(irec) = st%latitude; rlon(irec) = st%longitude
        rmass(irec) = st%mass; rdraft(irec) = st%H*real(RHO_ICE, 8)/real(RHO_WATER, 8)
        rti(irec) = st%T_ice
        if (.not. st%active) then
            nrec = irec
            exit
        end if
    end do

    if (nrec < 1) then
        print *, 'ERROR: no valid records; no NetCDF written'
        stop 1
    end if
    call write_nc(trim(out_nc), nrec, rt, rlat, rlon, rmass, rdraft, rti)
    print '(a,i0,a,a)', 'iceberg_run: wrote ', nrec, ' records to ', trim(out_nc)
    print '(a,f10.5,a,f10.5,a,es12.4)', ' final lat/lon=', st%latitude, '/', &
        st%longitude, ' mass=', st%mass

contains

    subroutine get_arg(i, val)
        integer, intent(in) :: i
        character(len=*), intent(out) :: val
        call get_command_argument(i, val)
    end subroutine get_arg

    subroutine constant_atmos(a)
        type(atmos_forcing), intent(out) :: a
        a%u10 = 0.0; a%v10 = 0.0
        a%t2m = 253.15; a%d2m = 253.15
        a%tcc = 0.5; a%msl = 101325.0; a%snowfall = 0.0
    end subroutine constant_atmos

    subroutine write_nc(path, n, tt, la, lo, ma, dr, ti)
        character(len=*), intent(in) :: path
        integer, intent(in) :: n
        real(8), intent(in) :: tt(:), la(:), lo(:), ma(:), dr(:), ti(:)
        integer :: ncid, dimid, v1, v2, v3, v4, v5, v6, st
        st = nf90_create(trim(path), nf90_clobber, ncid)
        if (st /= nf90_noerr) then
            print *, 'ERROR: cannot create ', trim(path), ': ', nf90_strerror(st)
            return
        end if
        st = nf90_def_dim(ncid, 'time', n, dimid)
        st = nf90_def_var(ncid, 'time', nf90_double, (/dimid/), v1)
        st = nf90_def_var(ncid, 'latitude', nf90_double, (/dimid/), v2)
        st = nf90_def_var(ncid, 'longitude', nf90_double, (/dimid/), v3)
        st = nf90_def_var(ncid, 'mass', nf90_double, (/dimid/), v4)
        st = nf90_def_var(ncid, 'draft', nf90_double, (/dimid/), v5)
        st = nf90_def_var(ncid, 'T_ice', nf90_double, (/dimid/), v6)
        st = nf90_put_att(ncid, v1, 'units', 's since 2020-01-01T00:00:00Z')
        st = nf90_put_att(ncid, v2, 'units', 'degrees_north')
        st = nf90_put_att(ncid, v3, 'units', 'degrees_east')
        st = nf90_put_att(ncid, v4, 'units', 'kg')
        st = nf90_put_att(ncid, v5, 'units', 'm')
        st = nf90_put_att(ncid, v6, 'units', 'degrees_C')
        st = nf90_enddef(ncid)
        st = nf90_put_var(ncid, v1, tt(1:n))
        st = nf90_put_var(ncid, v2, la(1:n))
        st = nf90_put_var(ncid, v3, lo(1:n))
        st = nf90_put_var(ncid, v4, ma(1:n))
        st = nf90_put_var(ncid, v5, dr(1:n))
        st = nf90_put_var(ncid, v6, ti(1:n))
        st = nf90_close(ncid)
    end subroutine write_nc

end program iceberg_run
