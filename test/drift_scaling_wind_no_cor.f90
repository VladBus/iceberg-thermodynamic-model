! ==============================================================================
! Тест: Drift scaling experiment — Wind only, NO CORIOLIS
! Назначение: Изолировать баланс ветровое/водное трение без Кориолиса
! ==============================================================================

program drift_scaling_wind_no_cor
    use iceberg
    use iceberg_dynamics
    use iceberg_types
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: step, nsteps
    real :: dt
    real :: wind_speeds(3)
    real :: terminal_speed, ratio
    real :: drift_angle, wind_angle, rel_angle
    integer :: i

    ! Wind speeds to test (m/s)
    wind_speeds = [5.0, 10.0, 15.0]

    print *, "=================================================="
    print *, "  DRIFT SCALING: Wind Only (NO CORIOLIS)"
    print *, "=================================================="
    print *, "Iceberg: 100x100x100m at equator (f=0)"
    print *, "No current, no melt"
    print *, ""

    ! No ocean current
    ocean_prof%nlevels = 10
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))
    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! Cold atmosphere (no surface melt)
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 200

    print *, "Wind_speed  Terminal_v  Ratio(v/U)  Angle"
    print *, "(m/s)       (m/s)"

    do i = 1, 3
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          0.0, 0.0, 0.0, 0.0)  ! Equator: lat=0

        ! Wind from North (v10 = -wind_speed)
        atmos%u10 = 0.0
        atmos%v10 = -wind_speeds(i)

        ! Run to terminal velocity
        do step = 1, nsteps
            call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                              0.0, 0.0, (/0.0, 0.0/), diag)
            if (.not. state%active) exit
        end do

        terminal_speed = sqrt(state%u**2 + state%v**2)
        ratio = terminal_speed/wind_speeds(i)

        wind_angle = 270.0
        drift_angle = atan2(state%v, state%u)*57.2957795
        rel_angle = drift_angle - wind_angle
        if (rel_angle .gt. 180.0) rel_angle = rel_angle - 360.0
        if (rel_angle .lt. -180.0) rel_angle = rel_angle + 360.0

        print '(F6.1, 2X, F10.6, 2X, F10.4, 2X, F8.1)', &
            wind_speeds(i), terminal_speed, ratio, rel_angle
    end do

    print *, ""
    print *, "Expected (no Coriolis): Ratio ~0.05-0.10 (5-10%), Angle = 0° (downwind)"
    print *, "=================================================="

end program drift_scaling_wind_no_cor
