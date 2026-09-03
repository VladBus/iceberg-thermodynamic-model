! ==============================================================================
! Тест: Drift scaling experiment — Current only
! Назначение: Проверить масштабирование дрейфа при разных скоростях течения
! ==============================================================================

program drift_scaling_current
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
    real :: curr_speeds(4)
    real :: terminal_speed, ratio
    integer :: i

    ! Current speeds to test (m/s)
    curr_speeds = [0.02, 0.05, 0.10, 0.20]

    print *, "=================================================="
    print *, "  DRIFT SCALING: Current Only"
    print *, "=================================================="
    print *, "Iceberg: 100x100x100m at 76.5N"
    print *, "No wind, no melt"
    print *, ""

    ! No wind
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 200

    print *, "Current_speed  Terminal_v  Ratio(v/U)  Angle"
    print *, "(m/s)          (m/s)"

    do i = 1, 4
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          76.5, 30.0, 0.0, 0.0)

        ! Uniform current in +x direction
        ocean_prof%nlevels = 10
        if (allocated(ocean_prof%z)) deallocate (ocean_prof%z, ocean_prof%dz, &
                                       ocean_prof%temp, ocean_prof%salt, ocean_prof%u, ocean_prof%v)
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
            ocean_prof%u(step) = curr_speeds(i)
            ocean_prof%v(step) = 0.0
        end do

        ! Run to terminal velocity
        do step = 1, nsteps
            call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                              0.0, 0.0, (/0.0, 0.0/), diag)
            if (.not. state%active) exit
        end do

        terminal_speed = sqrt(state%u**2 + state%v**2)
        ratio = terminal_speed/curr_speeds(i)

        print '(F6.2, 2X, F10.6, 2X, F10.4)', curr_speeds(i), terminal_speed, ratio
    end do

    print *, ""
    print *, "Expected (theory): Ratio ~0.02-0.05 (2-5%), Angle ~45° right in NH"
    print *, "=================================================="

end program drift_scaling_current
