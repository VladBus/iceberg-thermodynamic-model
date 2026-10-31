! ==============================================================================
! iceberg_run (Stage 12.6a, D-57)
! Минимальный автономный лагранжев прогон айсберга на реанализе GLORYS12
! (+опционально ERA5). Без океанской модели; one-way (D-51).
!
! Использование:
!   fpm run iceberg_run -- <lat0> <lon0> <L> <W> <H> <days> <dt> <out.nc> \
!                         [daily.nc] [static.nc] [era5.nc] [wave.nc]
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
    use iceberg, only: iceberg_init, iceberg_step, iceberg_step_prescribed, iceberg_set_latlon_mode
    use iceberg_forcing, only: ocean_forcing_configure, get_ocean_profile, &
                               get_atmos_forcing, latlon_to_model_coords, &
                               model_coords_to_indices
    use ocean_provider, only: SRC_REANALYSIS
    use netcdf_input, only: era5_open, era5_is_open
    use wave_forcing, only: wave_forcing_configure, wave_forcing_set_epoch
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
    real(8), allocatable :: rt(:), rlat(:), rlon(:), rmass(:), rdraft(:), rti(:), rmw(:), rwml(:)
    real(8), allocatable :: traj_t(:), traj_lat(:), traj_lon(:)
    character(len=512) :: out_nc, daily, static, era5f, wavef, trajf, arg
    integer :: nrec, irec, ncid, dimt, vt, vla, vlo, vma, vdr, vti, stt
    integer :: nargs, istat, ii, jj, iarg, pos_arg, ntraj, start_date, nsum
    logical :: ok, gok, have_era5, prescribed, warned_nearest
    real(8) :: epoch, lat_use, lon_use, sum_b, sum_l, sum_s, sum_v, sum_w, sum_a, sum_tf, vol0

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
    daily = DEF_DAILY; static = DEF_STATIC; era5f = ''; wavef = ''; trajf = ''
    epoch = EPOCH_2020; start_date = 20200101; pos_arg = 0
    iarg = 9
    do while (iarg <= nargs)
        call get_arg(iarg, arg)
        select case (trim(arg))
        case ('--prescribed_trajectory')
            iarg = iarg + 1
            if (iarg <= nargs) call get_arg(iarg, trajf)
        case ('--epoch')
            iarg = iarg + 1
            if (iarg <= nargs) then; call get_arg(iarg, arg); read (arg, *) epoch; end if
        case ('--start-date')
            iarg = iarg + 1
            if (iarg <= nargs) then; call get_arg(iarg, arg); read (arg, *) start_date; end if
        case default
            pos_arg = pos_arg + 1
            select case (pos_arg)
            case (1); daily = trim(arg)
            case (2); static = trim(arg)
            case (3); era5f = trim(arg)
            case (4); wavef = trim(arg)
            end select
        end select
        iarg = iarg + 1
    end do
    prescribed = len_trim(trajf) > 0

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
    nat(1) = start_date/10000; nat(2) = mod(start_date/100, 100); nat(3) = mod(start_date, 100); nat(4) = 0
    call ocean_forcing_configure(SRC_REANALYSIS, trim(daily), trim(static))
    call wave_forcing_set_epoch(EPOCH_2020)
    if (len_trim(wavef) > 0) then
        call wave_forcing_configure(trim(wavef))
        print *, 'iceberg_run: wave file = ', trim(wavef)
    end if
    call iceberg_set_latlon_mode(.true.)
    call iceberg_init(st, 0.0, 0.0, real(L0, 4), real(W0, 4), real(H0, 4), &
                      real(lat0, 4), real(lon0, 4), 0.0, 0.0)
    st%T_ice = -10.0d0
    if (prescribed) then
        call read_trajectory(trim(trajf), traj_t, traj_lat, traj_lon, ntraj)
        if (ntraj < 2) then
            print *, 'ERROR: trajectory needs >=2 rows: ', trim(trajf)
            stop 1
        end if
        print '(a,i0,a,a)', 'iceberg_run: prescribed trajectory rows=', ntraj, ' file=', trim(trajf)
    end if

    have_era5 = .false.
    if (len_trim(era5f) > 0) then
        call era5_open(trim(era5f), istat)
        have_era5 = (istat == 0) .and. era5_is_open
        if (.not. have_era5) print *, 'WARN: ERA5 not opened; using constant atmosphere'
    end if

    nrec = max(int(days*86400.0d0/dt) + 1, 1)
    allocate (rt(nrec), rlat(nrec), rlon(nrec), rmass(nrec), rdraft(nrec), rti(nrec), &
              rmw(nrec), rwml(nrec))
    sum_b = 0.0d0; sum_l = 0.0d0; sum_s = 0.0d0; sum_v = 0.0d0; sum_w = 0.0d0
    sum_a = 0.0d0; sum_tf = 0.0d0; nsum = 0; vol0 = st%volume; warned_nearest = .false.

    do irec = 1, nrec
        t = real(irec - 1, 8)*dt
        time_sec = epoch + t
        draft = st%H*real(RHO_ICE, 8)/real(RHO_WATER, 8)
        lat_use = st%latitude; lon_use = st%longitude
        if (prescribed) call traj_at(t, lat_use, lon_use)

        ! IBCAO depth at current lat/lon (nearest grid cell); prescribed mode skips it.
        depth = 1.0d6
        if (.not. prescribed) then
            depth = 1000.0d0
            call latlon_to_model_coords(real(st%latitude, 4), real(st%longitude, 4), &
                                        xm4, ym4, gok)
            if (gok) then
                call model_coords_to_indices(xm4, ym4, ii, jj, gok)
                if (gok .and. ii >= 1 .and. ii <= 133 .and. jj >= 1 .and. jj <= 105) then
                    if (abs(ht(ii, jj) - 8888.0) > 1.0e-8) depth = real(ht(ii, jj), 8)*0.01d0
                end if
            end if
        end if

        call get_ocean_profile(0.0d0, 0.0d0, lat_use, lon_use, draft, &
                               0.0d0, 0.0d0, prof, ok, time_sec)
        if (.not. ok) then
            ! Validation fallback: 1/12-degree GLORYS cells at the ice front
            ! can be land/NaN. Search the nearest wet cell within 0.5 deg.
            call nearest_wet_ocean(lat_use, lon_use, draft, time_sec, prof, ok)
            if (ok .and. .not. warned_nearest) then
                print *, 'WARN: nearest wet GLORYS cell used for validation at ', &
                    lat_use, lon_use
                warned_nearest = .true.
            end if
        end if
        if (.not. ok) then
            print *, 'STOP: no valid reanalysis ocean within 0.5 deg at:', lat_use, lon_use
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

        if (prescribed) then
            call iceberg_step_prescribed(st, real(dt, 4), prof, atmos, lat_use, lon_use, diag)
        else
            call iceberg_step(st, real(dt, 4), prof, atmos, real(depth, 4), diag=diag)
        end if
        sum_b = sum_b + real(diag%basal_mass_loss, 8)
        sum_l = sum_l + real(diag%lateral_mass_loss, 8)
        sum_s = sum_s + real(diag%surface_mass_loss, 8)
        sum_v = sum_v + real(diag%vapor_mass_loss, 8)
        sum_w = sum_w + real(diag%wave_mass_loss, 8)
        sum_a = sum_a + real(diag%a_wet, 8)
        sum_tf = sum_tf + real(diag%delta_t_ocean, 8)
        nsum = nsum + 1
        rt(irec) = t; rlat(irec) = st%latitude; rlon(irec) = st%longitude
        rmass(irec) = st%mass; rdraft(irec) = st%H*real(RHO_ICE, 8)/real(RHO_WATER, 8)
        rti(irec) = st%T_ice
        rmw(irec) = real(diag%m_wave, 8); rwml(irec) = real(diag%wave_mass_loss, 8)
        if (.not. st%active) then
            nrec = irec
            exit
        end if
    end do

    if (nrec < 1) then
        print *, 'ERROR: no valid records; no NetCDF written'
        stop 1
    end if
    print '(a,11(1x,es18.10))', 'HINDCAST_SUMMARY', st%volume, vol0, &
        sum_b, sum_l, sum_s, sum_v, sum_w, sum_a/max(nsum, 1), real((nrec - 1)*dt, 8), st%mass, &
        sum_tf/max(nsum, 1)
    call write_nc(trim(out_nc), nrec, rt, rlat, rlon, rmass, rdraft, rti, rmw, rwml)
    print '(a,i0,a,a)', 'iceberg_run: wrote ', nrec, ' records to ', trim(out_nc)
    print '(a,f10.5,a,f10.5,a,es12.4)', ' final lat/lon=', st%latitude, '/', &
        st%longitude, ' mass=', st%mass

contains


    subroutine nearest_wet_ocean(lat0, lon0, draft_in, t_in, prof, found)
        real(8), intent(in) :: lat0, lon0, draft_in, t_in
        type(ocean_profile), intent(out) :: prof
        logical, intent(out) :: found
        integer :: ring, k
        real(8), parameter :: STEP = 1.0d0/12.0d0, PI = 3.141592653589793d0
        real(8) :: ang, dlat, dlon, la, lo
        logical :: okt
        found = .false.
        do ring = 1, 6
            do k = 0, 7
                ang = 2.0d0*PI*real(k, 8)/8.0d0
                dlat = real(ring, 8)*STEP*cos(ang)
                dlon = real(ring, 8)*STEP*sin(ang)/max(cos(lat0*PI/180.0d0), 0.1d0)
                la = lat0 + dlat; lo = lon0 + dlon
                call get_ocean_profile(0.0d0, 0.0d0, la, lo, draft_in, 0.0d0, 0.0d0, prof, okt, t_in)
                if (okt) then
                    found = .true.; return
                end if
            end do
        end do
    end subroutine nearest_wet_ocean

    subroutine read_trajectory(path, tt, la, lo, n)
        character(len=*), intent(in) :: path
        real(8), allocatable, intent(out) :: tt(:), la(:), lo(:)
        integer, intent(out) :: n
        integer :: u, ios, k
        character(len=256) :: line
        real(8) :: a, b, c
        real(8) :: tmp(3, 20000)
        n = 0
        open (newunit=u, file=trim(path), status='old', action='read', iostat=ios)
        if (ios /= 0) then
            print *, 'ERROR: cannot open trajectory ', trim(path)
            stop 1
        end if
        do
            read (u, '(a)', iostat=ios) line
            if (ios /= 0) exit
            line = adjustl(line)
            if (len_trim(line) == 0) cycle
            if (line(1:1) == '#' .or. line(1:4) == 'time') cycle
            read (line, *, iostat=ios) a, b, c
            if (ios /= 0) cycle
            n = n + 1
            if (n > size(tmp, 2)) then
                print *, 'ERROR: trajectory too long'
                stop 1
            end if
            tmp(1, n) = a; tmp(2, n) = b; tmp(3, n) = c
        end do
        close (u)
        allocate (tt(n), la(n), lo(n))
        do k = 1, n
            tt(k) = tmp(1, k); la(k) = tmp(2, k); lo(k) = tmp(3, k)
        end do
    end subroutine read_trajectory

    subroutine traj_at(t, lat, lon)
        real(8), intent(in) :: t
        real(8), intent(out) :: lat, lon
        integer :: k
        real(8) :: w
        if (t <= traj_t(1)) then
            lat = traj_lat(1); lon = traj_lon(1); return
        end if
        if (t >= traj_t(ntraj)) then
            lat = traj_lat(ntraj); lon = traj_lon(ntraj); return
        end if
        k = 1
        do while (k < ntraj - 1 .and. traj_t(k + 1) < t)
            k = k + 1
        end do
        w = (t - traj_t(k))/(traj_t(k + 1) - traj_t(k))
        lat = traj_lat(k) + w*(traj_lat(k + 1) - traj_lat(k))
        lon = traj_lon(k) + w*(traj_lon(k + 1) - traj_lon(k))
    end subroutine traj_at

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

    subroutine write_nc(path, n, tt, la, lo, ma, dr, ti, mw, wml)
        character(len=*), intent(in) :: path
        integer, intent(in) :: n
        real(8), intent(in) :: tt(:), la(:), lo(:), ma(:), dr(:), ti(:), mw(:), wml(:)
        integer :: ncid, dimid, v1, v2, v3, v4, v5, v6, v7, v8, st
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
        st = nf90_def_var(ncid, 'm_wave', nf90_double, (/dimid/), v7)
        st = nf90_def_var(ncid, 'wave_mass_loss', nf90_double, (/dimid/), v8)
        st = nf90_put_att(ncid, v1, 'units', 's since run start')
        st = nf90_put_att(ncid, v2, 'units', 'degrees_north')
        st = nf90_put_att(ncid, v3, 'units', 'degrees_east')
        st = nf90_put_att(ncid, v4, 'units', 'kg')
        st = nf90_put_att(ncid, v5, 'units', 'm')
        st = nf90_put_att(ncid, v6, 'units', 'degrees_C')
        st = nf90_put_att(ncid, v7, 'units', 'm s-1')
        st = nf90_put_att(ncid, v8, 'units', 'kg')
        st = nf90_enddef(ncid)
        st = nf90_put_var(ncid, v1, tt(1:n))
        st = nf90_put_var(ncid, v2, la(1:n))
        st = nf90_put_var(ncid, v3, lo(1:n))
        st = nf90_put_var(ncid, v4, ma(1:n))
        st = nf90_put_var(ncid, v5, dr(1:n))
        st = nf90_put_var(ncid, v6, ti(1:n))
        st = nf90_put_var(ncid, v7, mw(1:n))
        st = nf90_put_var(ncid, v8, wml(1:n))
        st = nf90_close(ncid)
    end subroutine write_nc

end program iceberg_run
