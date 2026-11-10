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
                               model_coords_to_indices, interp_at_draft
    use iceberg_thermodynamics, only: voxel_geometry_active, voxel_geometry_mass, &
                                      voxel_geometry_draft, voxel_geometry_freeboard, voxel_model_get_grid, &
                                      voxel_model_get_cumulative_losses, voxel_model_get_solver, &
                                      voxel_model_get_fields, voxel_model_get_energy
    use ocean_provider, only: SRC_REANALYSIS
    use netcdf_input, only: era5_open, era5_is_open
    use wave_forcing, only: wave_forcing_configure, wave_forcing_set_epoch
    implicit none

    character(len=*), parameter :: DEF_DAILY = &
        'data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc'
    character(len=*), parameter :: DEF_STATIC = &
        'data/input/static/glorys_static_barents.nc'
    real(8), parameter :: EPOCH_2020 = 1577836800.0d0   ! 2020-01-01T00:00:00Z

    type(iceberg_state) :: st
    type(iceberg_diagnostics) :: diag
    type(ocean_profile) :: prof
    type(atmos_forcing) :: atmos
    real(8) :: lat0, lon0, L0, W0, H0, days, dt
    real(8) :: t, depth, draft, time_sec
    real(4) :: xm4, ym4
    real(8), allocatable :: rt(:), rlat(:), rlon(:), rmass(:), rdraft(:), rti(:), rmw(:), rwml(:)
    real(8), allocatable :: rvol(:), rawet(:), rsic(:), rbl(:), rll(:), rsl(:), rvl(:), rwl(:)
    real(8), allocatable :: renergy(:), rflush(:), rfreeboard(:)
    real(8), allocatable :: rvb(:), rvlat(:), rvs(:), rvf(:)
    real(8), allocatable :: rtd(:), rsd(:), ru(:), rv(:), rat(:), rau(:), rav(:)
    real(8), allocatable :: rpm(:), rpv(:), rpd(:), rpf(:), rcg(:), rres(:)
    real(8), allocatable :: fbt(:), fblat(:), fblon(:), fsel_lat(:), fsel_lon(:)
    real(8), allocatable :: fbr(:), fbd(:), fbtm(:), fbs(:), fbu(:), fbv(:)
    real(8), allocatable :: traj_t(:), traj_lat(:), traj_lon(:)
    integer, parameter :: MAXSNAP = 3
    real(8), allocatable :: snap_time(:), snap_mass(:), snap_draft(:)
    real(8), allocatable :: snap_T(:,:,:,:), snap_phi(:,:,:,:), snap_sb(:,:,:,:), snap_tb(:,:,:,:,:)
    logical, allocatable :: snap_open(:,:,:,:)
    integer :: nsnap, vnx, vny, vnz, last_snap_irec
    real(8) :: vdx, vdy, vdz
    character(len=512) :: out_nc, vox_nc, daily, static, era5f, wavef, trajf, arg
    integer :: nrec, irec, ncid, dimt, vt, vla, vlo, vma, vdr, vti, stt, nfb
    integer :: nargs, istat, ii, jj, iarg, pos_arg, ntraj, start_date, nsum, cg, clips, rl
    logical :: ok, gok, have_era5, prescribed, warned_nearest, strict_ocean
    logical :: stop_on_grounding
    real(8) :: epoch, lat_use, lon_use, sum_b, sum_l, sum_s, sum_v, sum_w, sum_a, sum_tf, vol0
    real(8) :: e8, f8, f_lat, f_lon, f_dist

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
    strict_ocean = .false.; stop_on_grounding = .false.
    iarg = 9
    do while (iarg <= nargs)
        call get_arg(iarg, arg)
        select case (trim(arg))
        case ('--strict-ocean')
            strict_ocean = .true.
        case ('--stop-on-grounding')
            stop_on_grounding = .true.
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
              rmw(nrec), rwml(nrec), rvol(nrec), rawet(nrec), rsic(nrec), rbl(nrec), &
              rll(nrec), rsl(nrec), rvl(nrec), rwl(nrec), renergy(nrec), rflush(nrec), rfreeboard(nrec), &
              rvb(nrec), rvlat(nrec), rvs(nrec), rvf(nrec), rtd(nrec), rsd(nrec), ru(nrec), rv(nrec), &
              rat(nrec), rau(nrec), rav(nrec), rpm(nrec), rpv(nrec), rpd(nrec), rpf(nrec), rcg(nrec), rres(nrec))
    allocate (fbt(nrec), fblat(nrec), fblon(nrec), fsel_lat(nrec), fsel_lon(nrec), &
              fbr(nrec), fbd(nrec), fbtm(nrec), fbs(nrec), fbu(nrec), fbv(nrec))
    nfb = 0
    sum_b = 0.0d0; sum_l = 0.0d0; sum_s = 0.0d0; sum_v = 0.0d0; sum_w = 0.0d0
    sum_a = 0.0d0; sum_tf = 0.0d0; nsum = 0; vol0 = st%volume; warned_nearest = .false.
    nsnap = 0; last_snap_irec = 0; vnx = 0; vny = 0; vnz = 0
    vdx = 0.0d0; vdy = 0.0d0; vdz = 0.0d0

    do irec = 1, nrec
        t = real(irec - 1, 8)*dt
        time_sec = epoch + t
        draft = st%H*real(RHO_ICE, 8)/real(RHO_WATER, 8)
        if (voxel_geometry_active()) draft = real(voxel_geometry_draft(), 8)
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
            if (strict_ocean) then
                print *, 'STOP: primary ocean profile unavailable; strict-ocean is active at ', &
                    lat_use, lon_use
                nrec = irec - 1
                exit
            end if
            ! Validation fallback: 1/12-degree GLORYS cells at the ice front
            ! can be land/NaN. Search the nearest wet cell within 0.5 deg.
            call nearest_wet_ocean(lat_use, lon_use, draft, time_sec, prof, ok, &
                                    f_lat, f_lon, f_dist)
            if (ok) then
                nfb = nfb + 1
                fbt(nfb) = time_sec; fblat(nfb) = lat_use; fblon(nfb) = lon_use
                fsel_lat(nfb) = f_lat; fsel_lon(nfb) = f_lon
                fbr(nfb) = f_dist; fbd(nfb) = draft
                fbtm(nfb) = real(interp_at_draft(prof, real(draft, 4), 'temp'), 8)
                fbs(nfb) = real(interp_at_draft(prof, real(draft, 4), 'salt'), 8)
                fbu(nfb) = real(interp_at_draft(prof, real(draft, 4), 'u'), 8)
                fbv(nfb) = real(interp_at_draft(prof, real(draft, 4), 'v'), 8)
                if (.not. warned_nearest) then
                    print *, 'WARN: nearest wet GLORYS cell used for validation at ', &
                        lat_use, lon_use
                    warned_nearest = .true.
                end if
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
        rfreeboard(irec) = max(0.0d0, real(st%H, 8) - rdraft(irec))
        if (voxel_geometry_active()) then
            rmass(irec) = real(voxel_geometry_mass(), 8)
            rdraft(irec) = real(voxel_geometry_draft(), 8)
            rfreeboard(irec) = real(voxel_geometry_freeboard(), 8)
        end if
        rti(irec) = st%T_ice
        rmw(irec) = real(diag%m_wave, 8); rwml(irec) = real(diag%wave_mass_loss, 8)
        if (voxel_geometry_active()) then
            rvol(irec) = real(voxel_geometry_mass(), 8)/real(RHO_ICE, 8)
        else
            rvol(irec) = st%volume
        end if
        rawet(irec) = real(diag%a_wet, 8)
        rsic(irec) = real(prof%siconc, 8)
        rbl(irec) = real(diag%basal_mass_loss, 8); rll(irec) = real(diag%lateral_mass_loss, 8)
        rsl(irec) = real(diag%surface_mass_loss, 8); rvl(irec) = real(diag%vapor_mass_loss, 8)
        rwl(irec) = real(diag%wave_mass_loss, 8)
        renergy(irec) = 0.0d0; rflush(irec) = 0.0d0
        rvb(irec) = 0.0d0; rvlat(irec) = 0.0d0; rvs(irec) = 0.0d0; rvf(irec) = 0.0d0
        rtd(irec) = real(diag%t_draft, 8); rsd(irec) = real(diag%s_draft, 8)
        rpv(irec) = real(st%L, 8)*real(st%W, 8)*real(st%H, 8)
        rpm(irec) = real(RHO_ICE, 8)*rpv(irec)
        rpd(irec) = real(diag%draft, 8)
        rpf(irec) = real(diag%freeboard, 8)
        rcg(irec) = 0.0d0; rres(irec) = 0.0d0
        ru(irec) = real(interp_at_draft(prof, real(draft, 4), 'u'), 8)
        rv(irec) = real(interp_at_draft(prof, real(draft, 4), 'v'), 8)
        rat(irec) = real(atmos%t2m, 8); rau(irec) = real(atmos%u10, 8); rav(irec) = real(atmos%v10, 8)
        if (voxel_geometry_active()) then
            call voxel_model_get_energy(e8, f8)
            renergy(irec) = e8; rflush(irec) = f8
            call voxel_model_get_cumulative_losses(rvb(irec), rvlat(irec), rvs(irec), rvf(irec))
            call voxel_model_get_solver(cg, rres(irec), clips, rl)
            rcg(irec) = real(cg, 8)
        end if
        if (voxel_geometry_active() .and. &
            (irec == 1 .or. irec == max(nrec/2, 1))) call save_snapshot(rt(irec), irec)
        if (.not. st%active) then
            nrec = irec
            exit
        end if
        if (diag%grounded .and. stop_on_grounding .and. .not. prescribed) then
            nrec = irec
            print '(a,f10.5,a,f10.5,a,f10.5,a)', 'STOP: iceberg grounded at lat/lon ', &
                st%latitude, '/', st%longitude, '; draft=', diag%draft, ' m'
            exit
        end if
    end do

    if (nrec < 1) then
        print *, 'ERROR: no valid records; no NetCDF written'
        stop 1
    end if
    if (voxel_geometry_active() .and. nsnap < MAXSNAP .and. &
        last_snap_irec /= nrec) call save_snapshot(rt(nrec), nrec)
    print '(a,11(1x,es18.10))', 'HINDCAST_SUMMARY', rvol(nrec), vol0, &
        sum_b, sum_l, sum_s, sum_v, sum_w, sum_a/max(nsum, 1), real((nrec - 1)*dt, 8), rmass(nrec), &
        sum_tf/max(nsum, 1)
    call write_nc(trim(out_nc), nrec, rt, rlat, rlon, rmass, rdraft, rti, rmw, rwml, &
                  rvol, rawet, rsic, rbl, rll, rsl, rvl, rwl, renergy, rflush, rfreeboard, &
                  rvb, rvlat, rvs, rvf, rtd, rsd, ru, rv, rat, rau, rav, rpm, rpv, rpd, rpf, rcg, rres)
    if (nsnap > 0) then
        vox_nc = trim(out_nc)//'_voxel.nc'
        call write_voxel_nc(trim(vox_nc), nsnap)
        print '(a,i0,a,a)', 'iceberg_run: wrote ', nsnap, ' voxel snapshots to ', trim(vox_nc)
    end if
    if (nfb > 0) then
        call write_fallback_csv(trim(out_nc)//'_fallback.csv', nfb)
        print '(a,i0,a,a)', 'iceberg_run: wrote ', nfb, ' fallback events to ', &
            trim(out_nc)//'_fallback.csv'
    end if
    print '(a,i0,a,a)', 'iceberg_run: wrote ', nrec, ' records to ', trim(out_nc)
    print '(a,f10.5,a,f10.5,a,es12.4)', ' final lat/lon=', st%latitude, '/', &
        st%longitude, ' mass=', rmass(nrec)

contains


    subroutine nearest_wet_ocean(lat0, lon0, draft_in, t_in, prof, found, &
                                  found_lat, found_lon, found_dist)
        real(8), intent(in) :: lat0, lon0, draft_in, t_in
        type(ocean_profile), intent(out) :: prof
        logical, intent(out) :: found
        real(8), intent(out), optional :: found_lat, found_lon, found_dist
        integer :: ring, k
        real(8), parameter :: STEP = 1.0d0/12.0d0, PI = 3.141592653589793d0
        real(8) :: ang, dlat, dlon, la, lo, dist
        logical :: okt
        found = .false.; found_lat = lat0; found_lon = lon0; found_dist = 0.0d0
        do ring = 1, 6
            do k = 0, 7
                ang = 2.0d0*PI*real(k, 8)/8.0d0
                dlat = real(ring, 8)*STEP*cos(ang)
                dlon = real(ring, 8)*STEP*sin(ang)/max(cos(lat0*PI/180.0d0), 0.1d0)
                la = lat0 + dlat; lo = lon0 + dlon
                call get_ocean_profile(0.0d0, 0.0d0, la, lo, draft_in, 0.0d0, 0.0d0, prof, okt, t_in)
                if (okt) then
                    found = .true.
                    found_lat = la; found_lon = lo
                    found_dist = sqrt((la - lat0)**2 + &
                         ((lo - lon0)*cos(lat0*PI/180.0d0))**2)
                    return
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

    subroutine write_fallback_csv(path, n)
        character(len=*), intent(in) :: path
        integer, intent(in) :: n
        integer :: u, i
        open (newunit=u, file=trim(path), status="replace", action="write")
        write (u, '(a)') 'time_s,iceberg_lat,iceberg_lon,selected_lat,selected_lon,distance_deg,draft_m,T_draft_C,S_draft,u_draft_m_s,v_draft_m_s,reason'
        do i = 1, n
            write (u, '(es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",es20.12,",",a)') &
                fbt(i), fblat(i), fblon(i), fsel_lat(i), fsel_lon(i), fbr(i), fbd(i), &
                fbtm(i), fbs(i), fbu(i), fbv(i), 'primary profile unavailable; nearest wet cell used'
        end do
        close (u)
    end subroutine write_fallback_csv

    subroutine write_nc(path, n, tt, la, lo, ma, dr, ti, mw, wml, vol, awet, sic, &
                        bl, ll, sl, vl, wl, en, fl, fr, vb, vv, vs, vf, td, sd, uu, vv2, at, au, av, pm, pv, pd, pf, cgv, resv)
        character(len=*), intent(in) :: path
        integer, intent(in) :: n
        real(8), intent(in) :: tt(:), la(:), lo(:), ma(:), dr(:), ti(:), mw(:), wml(:)
        real(8), intent(in) :: vol(:), awet(:), sic(:), bl(:), ll(:), sl(:), vl(:), wl(:)
        real(8), intent(in) :: en(:), fl(:), fr(:), vb(:), vv(:), vs(:), vf(:)
        real(8), intent(in) :: td(:), sd(:), uu(:), vv2(:), at(:), au(:), av(:)
        real(8), intent(in) :: pm(:), pv(:), pd(:), pf(:), cgv(:), resv(:)
        integer :: ncid, dimid, st
        integer :: v(36)
        st = nf90_create(trim(path), nf90_clobber, ncid)
        if (st /= nf90_noerr) then
            print *, 'ERROR: cannot create ', trim(path), ': ', nf90_strerror(st)
            return
        end if
        st = nf90_def_dim(ncid, 'time', n, dimid)
        st = nf90_def_var(ncid, 'time', nf90_double, (/dimid/), v(1))
        st = nf90_def_var(ncid, 'latitude', nf90_double, (/dimid/), v(2))
        st = nf90_def_var(ncid, 'longitude', nf90_double, (/dimid/), v(3))
        st = nf90_def_var(ncid, 'mass', nf90_double, (/dimid/), v(4))
        st = nf90_def_var(ncid, 'draft', nf90_double, (/dimid/), v(5))
        st = nf90_def_var(ncid, 'T_ice', nf90_double, (/dimid/), v(6))
        st = nf90_def_var(ncid, 'm_wave', nf90_double, (/dimid/), v(7))
        st = nf90_def_var(ncid, 'wave_mass_loss', nf90_double, (/dimid/), v(8))
        st = nf90_def_var(ncid, 'volume', nf90_double, (/dimid/), v(9))
        st = nf90_def_var(ncid, 'a_wet', nf90_double, (/dimid/), v(10))
        st = nf90_def_var(ncid, 'siconc', nf90_double, (/dimid/), v(11))
        st = nf90_def_var(ncid, 'mass_loss_basal', nf90_double, (/dimid/), v(12))
        st = nf90_def_var(ncid, 'mass_loss_lateral', nf90_double, (/dimid/), v(13))
        st = nf90_def_var(ncid, 'mass_loss_surface', nf90_double, (/dimid/), v(14))
        st = nf90_def_var(ncid, 'mass_loss_vapor', nf90_double, (/dimid/), v(15))
        st = nf90_def_var(ncid, 'mass_loss_wave', nf90_double, (/dimid/), v(16))
        st = nf90_def_var(ncid, 'sensible_energy', nf90_double, (/dimid/), v(17))
        st = nf90_def_var(ncid, 'flushed_energy', nf90_double, (/dimid/), v(18))
        st = nf90_def_var(ncid, 'freeboard', nf90_double, (/dimid/), v(19))
        st = nf90_def_var(ncid, 'voxel_mass_loss_basal', nf90_double, (/dimid/), v(20))
        st = nf90_def_var(ncid, 'voxel_mass_loss_lateral', nf90_double, (/dimid/), v(21))
        st = nf90_def_var(ncid, 'voxel_mass_loss_surface', nf90_double, (/dimid/), v(22))
        st = nf90_def_var(ncid, 'voxel_mass_loss_flush', nf90_double, (/dimid/), v(23))
        st = nf90_def_var(ncid, 'ocean_T_draft', nf90_double, (/dimid/), v(24))
        st = nf90_def_var(ncid, 'ocean_S_draft', nf90_double, (/dimid/), v(25))
        st = nf90_def_var(ncid, 'ocean_u_draft', nf90_double, (/dimid/), v(26))
        st = nf90_def_var(ncid, 'ocean_v_draft', nf90_double, (/dimid/), v(27))
        st = nf90_def_var(ncid, 'air_T', nf90_double, (/dimid/), v(28))
        st = nf90_def_var(ncid, 'air_u10', nf90_double, (/dimid/), v(29))
        st = nf90_def_var(ncid, 'air_v10', nf90_double, (/dimid/), v(30))
        st = nf90_def_var(ncid, 'prism_mass', nf90_double, (/dimid/), v(31))
        st = nf90_def_var(ncid, 'prism_volume', nf90_double, (/dimid/), v(32))
        st = nf90_def_var(ncid, 'prism_draft', nf90_double, (/dimid/), v(33))
        st = nf90_def_var(ncid, 'prism_freeboard', nf90_double, (/dimid/), v(34))
        st = nf90_def_var(ncid, 'cg_iters', nf90_double, (/dimid/), v(35))
        st = nf90_def_var(ncid, 'cg_resid', nf90_double, (/dimid/), v(36))
        st = nf90_enddef(ncid)
        st = nf90_put_var(ncid, v(1), tt(1:n))
        st = nf90_put_var(ncid, v(2), la(1:n))
        st = nf90_put_var(ncid, v(3), lo(1:n))
        st = nf90_put_var(ncid, v(4), ma(1:n))
        st = nf90_put_var(ncid, v(5), dr(1:n))
        st = nf90_put_var(ncid, v(6), ti(1:n))
        st = nf90_put_var(ncid, v(7), mw(1:n))
        st = nf90_put_var(ncid, v(8), wml(1:n))
        st = nf90_put_var(ncid, v(9), vol(1:n))
        st = nf90_put_var(ncid, v(10), awet(1:n))
        st = nf90_put_var(ncid, v(11), sic(1:n))
        st = nf90_put_var(ncid, v(12), bl(1:n))
        st = nf90_put_var(ncid, v(13), ll(1:n))
        st = nf90_put_var(ncid, v(14), sl(1:n))
        st = nf90_put_var(ncid, v(15), vl(1:n))
        st = nf90_put_var(ncid, v(16), wl(1:n))
        st = nf90_put_var(ncid, v(17), en(1:n))
        st = nf90_put_var(ncid, v(18), fl(1:n))
        st = nf90_put_var(ncid, v(19), fr(1:n))
        st = nf90_put_var(ncid, v(20), vb(1:n))
        st = nf90_put_var(ncid, v(21), vv(1:n))
        st = nf90_put_var(ncid, v(22), vs(1:n))
        st = nf90_put_var(ncid, v(23), vf(1:n))
        st = nf90_put_var(ncid, v(24), td(1:n))
        st = nf90_put_var(ncid, v(25), sd(1:n))
        st = nf90_put_var(ncid, v(26), uu(1:n))
        st = nf90_put_var(ncid, v(27), vv2(1:n))
        st = nf90_put_var(ncid, v(28), at(1:n))
        st = nf90_put_var(ncid, v(29), au(1:n))
        st = nf90_put_var(ncid, v(30), av(1:n))
        st = nf90_put_var(ncid, v(31), pm(1:n))
        st = nf90_put_var(ncid, v(32), pv(1:n))
        st = nf90_put_var(ncid, v(33), pd(1:n))
        st = nf90_put_var(ncid, v(34), pf(1:n))
        st = nf90_put_var(ncid, v(35), cgv(1:n))
        st = nf90_put_var(ncid, v(36), resv(1:n))
        st = nf90_close(ncid)
    end subroutine write_nc

    subroutine save_snapshot(tval, irec)
        real(8), intent(in) :: tval
        integer, intent(in) :: irec
        real(8), allocatable :: T(:, :, :), phi(:, :, :), tb(:, :, :, :), sb(:, :, :)
        logical, allocatable :: open(:, :, :)
        if (nsnap >= MAXSNAP .or. last_snap_irec == irec) return
        call voxel_model_get_grid(vnx, vny, vnz, vdx, vdy, vdz)
        if (vnx <= 0 .or. vny <= 0 .or. vnz <= 0) return
        call voxel_model_get_fields(T, phi, open, tb, sb)
        if (.not. allocated(T)) return
        if (nsnap == 0) then
            allocate (snap_time(MAXSNAP), snap_mass(MAXSNAP), snap_draft(MAXSNAP))
            allocate (snap_T(vnx, vny, vnz, MAXSNAP), snap_phi(vnx, vny, vnz, MAXSNAP))
            allocate (snap_sb(vnx, vny, vnz, MAXSNAP))
            allocate (snap_open(vnx, vny, vnz, MAXSNAP))
            allocate (snap_tb(vnx, vny, vnz, 6, MAXSNAP))
        end if
        nsnap = nsnap + 1
        snap_time(nsnap) = tval
        snap_T(:, :, :, nsnap) = T
        snap_phi(:, :, :, nsnap) = phi
        snap_sb(:, :, :, nsnap) = sb
        snap_open(:, :, :, nsnap) = open
        snap_tb(:, :, :, :, nsnap) = tb
        snap_mass(nsnap) = real(voxel_geometry_mass(), 8)
        snap_draft(nsnap) = real(voxel_geometry_draft(), 8)
        last_snap_irec = irec
        deallocate (T, phi, open, tb, sb)
    end subroutine save_snapshot

    subroutine write_voxel_nc(path, ns)
        character(len=*), intent(in) :: path
        integer, intent(in) :: ns
        integer :: ncid, dimx, dimy, dimz, dimf, dimt
        integer :: vid(11), st, is
        integer, allocatable :: mask(:, :, :)
        integer :: start4(4), count4(4), start5(5), count5(5)
        real(8) :: xc(vnx), yc(vny), zc(vnz)

        st = nf90_create(trim(path), nf90_clobber, ncid)
        if (st /= nf90_noerr) then
            print *, 'WARN: cannot create voxel file ', trim(path), ': ', nf90_strerror(st)
            return
        end if
        st = nf90_def_dim(ncid, 'snapshot', ns, dimt)
        st = nf90_def_dim(ncid, 'nx', vnx, dimx)
        st = nf90_def_dim(ncid, 'ny', vny, dimy)
        st = nf90_def_dim(ncid, 'nz', vnz, dimz)
        st = nf90_def_dim(ncid, 'face', 6, dimf)
        st = nf90_def_var(ncid, 'x', nf90_double, (/dimx/), vid(1))
        st = nf90_def_var(ncid, 'y', nf90_double, (/dimy/), vid(2))
        st = nf90_def_var(ncid, 'z', nf90_double, (/dimz/), vid(3))
        st = nf90_def_var(ncid, 'time', nf90_double, (/dimt/), vid(4))
        st = nf90_def_var(ncid, 'T', nf90_double, (/dimx, dimy, dimz, dimt/), vid(5))
        st = nf90_def_var(ncid, 'phi', nf90_double, (/dimx, dimy, dimz, dimt/), vid(6))
        st = nf90_def_var(ncid, 'open_mask', nf90_int, (/dimx, dimy, dimz, dimt/), vid(7))
        st = nf90_def_var(ncid, 'tb_face', nf90_double, &
                          (/dimx, dimy, dimz, dimf, dimt/), vid(8))
        st = nf90_def_var(ncid, 'S_boundary', nf90_double, &
                          (/dimx, dimy, dimz, dimt/), vid(11))
        st = nf90_def_var(ncid, 'mass', nf90_double, (/dimt/), vid(9))
        st = nf90_def_var(ncid, 'draft', nf90_double, (/dimt/), vid(10))
        st = nf90_put_att(ncid, nf90_global, 'voxel_nx', vnx)
        st = nf90_put_att(ncid, nf90_global, 'voxel_ny', vny)
        st = nf90_put_att(ncid, nf90_global, 'voxel_nz', vnz)
        st = nf90_put_att(ncid, nf90_global, 'voxel_dx_m', vdx)
        st = nf90_put_att(ncid, nf90_global, 'voxel_dy_m', vdy)
        st = nf90_put_att(ncid, nf90_global, 'voxel_dz_m', vdz)
        st = nf90_put_att(ncid, nf90_global, 'body_L_m', real(vnx, 8)*vdx)
        st = nf90_put_att(ncid, nf90_global, 'body_W_m', real(vny, 8)*vdy)
        st = nf90_put_att(ncid, nf90_global, 'body_H_m', real(vnz, 8)*vdz)
        st = nf90_enddef(ncid)

        xc = (real([(is, is=1, vnx)], 8) - 0.5_8)*vdx
        yc = (real([(is, is=1, vny)], 8) - 0.5_8)*vdy
        zc = (real([(is, is=1, vnz)], 8) - 0.5_8)*vdz
        st = nf90_put_var(ncid, vid(1), xc)
        st = nf90_put_var(ncid, vid(2), yc)
        st = nf90_put_var(ncid, vid(3), zc)
        st = nf90_put_var(ncid, vid(4), snap_time(1:ns))
        st = nf90_put_var(ncid, vid(9), snap_mass(1:ns))
        st = nf90_put_var(ncid, vid(10), snap_draft(1:ns))
        start4 = (/1, 1, 1, 1/); count4 = (/vnx, vny, vnz, 1/)
        start5 = (/1, 1, 1, 1, 1/); count5 = (/vnx, vny, vnz, 6, 1/)
        do is = 1, ns
            start4(4) = is
            st = nf90_put_var(ncid, vid(5), snap_T(:, :, :, is), start=start4, count=count4)
            st = nf90_put_var(ncid, vid(6), snap_phi(:, :, :, is), start=start4, count=count4)
            allocate (mask(vnx, vny, vnz))
            mask = merge(1, 0, snap_open(:, :, :, is))
            st = nf90_put_var(ncid, vid(7), mask, start=start4, count=count4)
            deallocate (mask)
            start5(5) = is
            st = nf90_put_var(ncid, vid(8), snap_tb(:, :, :, :, is), &
                              start=start5, count=count5)
            st = nf90_put_var(ncid, vid(11), snap_sb(:, :, :, is), &
                              start=start4, count=count4)
        end do
        st = nf90_close(ncid)
    end subroutine write_voxel_nc

end program iceberg_run
