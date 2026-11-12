! ==============================================================================
! Test: analytic drift force balance for a 100 m cube (Stage 12.16, item 1a)
!
! Wind-only cases (7 and 15 m/s, no current, Coriolis ON):
!   the continuous Coriolis-limited equilibrium is
!       u_eq = F_wind / (M f),
!   the semi-implicit discrete equilibrium adds sqrt(1 + (f dt)^2):
!       u_eq = F_wind / (M f sqrt(1 + (f dt)^2)).
!   At this speed the water drag is negligible and the wind force is balanced
!   by Coriolis; the model is expected to reproduce the discrete value.
!
! Current-only case (0.1 m/s, no wind, Coriolis ON):
!   the same balance gives u_eq = F_water / (M f), i.e. a small fraction of
!   the current, not full advection. Without Coriolis the iceberg accelerates
!   toward the current.
!
! The test uses the prism (non-voxel) drag path and synthetic cold forcing;
! it writes no files and requires no external data.
! ==============================================================================
program iceberg_test_drift_force_balance
    use iceberg, only: iceberg_init
    use iceberg_dynamics, only: iceberg_dynamics_step
    use iceberg_thermodynamics, only: voxel_geometry_active
    use iceberg_types
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    real, parameter :: L = 100.0, W = 100.0, H = 100.0
    real, parameter :: LAT = 76.5, LON = 30.0
    real, parameter :: DT = 3600.0
    integer, parameter :: NDAYS = 30
    real :: f_cor, mass, draft, freeboard, a_sail, a_side
    real :: f_wind, u_cont, u_disc, u_model, ratio_wind
    real :: f_water, u_curr_disc, u_curr_model, u_nocor_model
    real :: wind_speeds(2)
    integer :: i, nsteps

    n_errors = 0
    n_checks = 0

    if (voxel_geometry_active()) then
        print *, 'SKIP: VOXEL_ENABLED is active; this analytic test uses the prism path'
        stop 0
    end if

    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 0.0, 0.0)

    f_cor = 2.0*OMEGA*sin(LAT/57.2957795)
    mass = RHO_ICE*L*W*H
    draft = H*RHO_ICE/RHO_WATER
    freeboard = H - draft
    a_sail = L*W + 2.0*(L + W)*freeboard
    a_side = W*draft
    nsteps = NDAYS*24

    print *, '=================================================='
    print *, '  ANALYTIC DRIFT FORCE BALANCE (12.16 item 1a)'
    print *, '=================================================='
    print '(a,f12.2,a,es12.4)', ' mass [kg] = ', mass, '   f [1/s] = ', f_cor
    print '(a,f10.3,a,f10.3,a,f12.2)', ' draft [m] = ', draft, &
        '   freeboard [m] = ', freeboard, '   A_sail [m2] = ', a_sail
    print '(a,f12.2)', ' A_side (Method A, per direction) [m2] = ', a_side
    print *, ''

    ! Wind-only cases
    wind_speeds = [7.0, 15.0]
    do i = 1, 2
        call make_ocean(ocean_prof, 0.0, 0.0)
        call make_atmos(atmos, wind_speeds(i), 0.0)
        call iceberg_init(state, 0.0, 0.0, L, W, H, LAT, LON, 0.0, 0.0)

        f_wind = 0.5*RHO_AIR*CD_AIR*a_sail*wind_speeds(i)**2
        u_cont = f_wind/(mass*f_cor)
        u_disc = f_wind/(mass*f_cor*sqrt(1.0 + (f_cor*DT)**2))

        do nsteps = 1, NDAYS*24
            call iceberg_dynamics_step(state, DT, ocean_prof, atmos, f_cor, &
                                       0.0, 0.0, 0.0, 0.0, diag)
        end do
        u_model = sqrt(state%u**2 + state%v**2)
        ratio_wind = u_model/wind_speeds(i)

        print '(a,f6.1,a,f10.6,a,f10.6,a,f10.6,a,f9.6)', &
            ' wind ', wind_speeds(i), ' m/s: model ', u_model, &
            '  continuous ', u_cont, '  discrete ', u_disc, &
            '  u/wind ', ratio_wind

        n_checks = n_checks + 1
        if (abs(u_model - u_disc) <= 0.05*max(u_disc, 1.0e-9)) then
            print *, ' OK: model matches discrete Coriolis-limited equilibrium'
        else
            print *, ' ERROR: model differs from discrete equilibrium by >5%'
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (abs(diag%f_wind_x) > 10.0*abs(diag%f_water_x) .and. &
            abs(diag%f_wind_x) > 0.5*abs(diag%f_cor_x)) then
            print *, ' OK: wind is balanced by Coriolis; water drag is negligible'
        else
            print *, ' ERROR: force partition is not wind/Coriolis dominated'
            n_errors = n_errors + 1
        end if
    end do

    ! Current-only, Coriolis ON
    call make_ocean(ocean_prof, 0.1, 0.0)
    call make_atmos(atmos, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, L, W, H, LAT, LON, 0.0, 0.0)
    f_water = 0.5*RHO_WATER*CD_WATER*a_side*0.1**2
    u_curr_disc = f_water/(mass*f_cor*sqrt(1.0 + (f_cor*DT)**2))
    do nsteps = 1, NDAYS*24
        call iceberg_dynamics_step(state, DT, ocean_prof, atmos, f_cor, &
                                   0.0, 0.0, 0.0, 0.0, diag)
    end do
    u_curr_model = sqrt(state%u**2 + state%v**2)
    print '(a,f10.6,a,f10.6,a,f9.6)', ' current 0.1 m/s (Coriolis): model ', &
        u_curr_model, '  discrete ', u_curr_disc, '  u/U ', u_curr_model/0.1
    n_checks = n_checks + 1
    if (abs(u_curr_model - u_curr_disc) <= 0.10*max(u_curr_disc, 1.0e-9)) then
        print *, ' OK: current response is Coriolis-limited, matching analytic'
    else
        print *, ' ERROR: current response differs from Coriolis-limited analytic'
        n_errors = n_errors + 1
    end if

    ! Current-only, Coriolis OFF: the iceberg must approach the current
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, L, W, H, 0.0, LON, 0.0, 0.0)
    do nsteps = 1, 60*24
        call iceberg_dynamics_step(state, DT, ocean_prof, atmos, 0.0, &
                                   0.0, 0.0, 0.0, 0.0, diag)
    end do
    u_nocor_model = sqrt(state%u**2 + state%v**2)
    print '(a,f10.6,a,f9.6)', ' current 0.1 m/s (no Coriolis, 60 d): model ', &
        u_nocor_model, '  u/U ', u_nocor_model/0.1
    n_checks = n_checks + 1
    if (u_nocor_model > 0.8*0.1) then
        print *, ' OK: without Coriolis the iceberg approaches the current'
    else
        print *, ' ERROR: without Coriolis current-following is too slow'
        n_errors = n_errors + 1
    end if

    print *, ''
    print '(a,i0,a,i0)', 'TOTAL CHECKS: ', n_checks, ' ERRORS: ', n_errors
    if (n_errors == 0) then
        print *, 'SUCCESS: drift force balance test PASSED'
        stop 0
    else
        print *, 'FAILURE: drift force balance test FAILED'
        stop 1
    end if

contains

    subroutine make_ocean(prof, u0, v0)
        type(ocean_profile), intent(out) :: prof
        real, intent(in) :: u0, v0
        integer :: k
        prof%nlevels = 10
        allocate (prof%z(10), prof%dz(10), prof%temp(10), prof%salt(10), prof%u(10), prof%v(10))
        do k = 1, 10
            prof%z(k) = real(k*10)
            prof%dz(k) = 10.0
            prof%temp(k) = -2.5
            prof%salt(k) = 0.0345
            prof%u(k) = u0
            prof%v(k) = v0
        end do
    end subroutine make_ocean

    subroutine make_atmos(at, u10, v10)
        type(atmos_forcing), intent(out) :: at
        real, intent(in) :: u10, v10
        at%u10 = u10
        at%v10 = v10
        at%t2m = 253.15
        at%d2m = 253.15
        at%tcc = 0.0
        at%msl = 101325.0
        at%snowfall = 0.0
    end subroutine make_atmos

end program iceberg_test_drift_force_balance
