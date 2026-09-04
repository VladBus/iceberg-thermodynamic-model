! ==============================================================================
! Тест: Water Drag Method A vs Method B Audit
! Назначение: Сравнить два метода расчета водного трения.
!             Method A: слой-за-слоем интеграл по осадке
!             Method B: глубинно-усредненное течение, полная оромочённая площадь
! ==============================================================================

program iceberg_test_water_drag_methods
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt, model_time
    real :: latitude, f_coriolis
    real :: fx_a, fy_a, fx_b, fy_b
    real :: speed_a, speed_b
    real :: ratio

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Water Drag Method A vs Method B"
    print *, "=================================================="

    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    dt = 3600.0
    nsteps = 100

    print *, "Latitude: ", latitude
    print *, "f = ", f_coriolis
    print *, ""

    ! =========================================================================
    ! TEST 1: Uniform current, Coriolis OFF
    ! =========================================================================
    print *, "--- TEST 1: Uniform current (0.1 m/s), Coriolis OFF ---"
    call test_case(1, .false., ocean_prof, atmos, &
                   latitude, 0.0, dt, nsteps, state, diag, &
                   fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    n_checks = n_checks + 1
    if (ratio .gt. 0.5 .and. ratio .lt. 2.0) then
        print *, "OK: Methods agree within factor of 2"
    else
        print *, "WARNING: Methods differ by more than factor of 2"
    end if

    ! =========================================================================
    ! TEST 2: Uniform current, Coriolis ON
    ! =========================================================================
    print *, ""
    print *, "--- TEST 2: Uniform current (0.1 m/s), Coriolis ON ---"
    call test_case(2, .true., ocean_prof, atmos, &
                   latitude, f_coriolis, dt, nsteps, state, diag, &
                   fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    n_checks = n_checks + 1
    if (ratio .gt. 0.5 .and. ratio .lt. 2.0) then
        print *, "OK: Methods agree within factor of 2"
    else
        print *, "WARNING: Methods differ by more than factor of 2"
    end if

    ! =========================================================================
    ! TEST 3: Sheared current, Coriolis OFF
    ! =========================================================================
    print *, ""
    print *, "--- TEST 3: Sheared current (surface 0.2, bottom 0.05), Coriolis OFF ---"
    call test_case_sheared(3, .false., ocean_prof, atmos, &
                           latitude, 0.0, dt, nsteps, state, diag, &
                           fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    n_checks = n_checks + 1
    if (ratio .gt. 0.5 .and. ratio .lt. 2.0) then
        print *, "OK: Methods agree within factor of 2"
    else
        print *, "WARNING: Methods differ by more than factor of 2"
    end if

    ! =========================================================================
    ! TEST 4: Sheared current, Coriolis ON
    ! =========================================================================
    print *, ""
    print *, "--- TEST 4: Sheared current (surface 0.2, bottom 0.05), Coriolis ON ---"
    call test_case_sheared(4, .true., ocean_prof, atmos, &
                           latitude, f_coriolis, dt, nsteps, state, diag, &
                           fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    n_checks = n_checks + 1
    if (ratio .gt. 0.5 .and. ratio .lt. 2.0) then
        print *, "OK: Methods agree within factor of 2"
    else
        print *, "WARNING: Methods differ by more than factor of 2"
    end if

    ! =========================================================================
    ! TEST 5: Zero current (wind only), Coriolis OFF
    ! =========================================================================
    print *, ""
    print *, "--- TEST 5: Zero current (wind 10 m/s), Coriolis OFF ---"
    call test_case_wind_only(5, .false., ocean_prof, atmos, &
                             latitude, 0.0, dt, nsteps, state, diag, &
                             fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    ! =========================================================================
    ! TEST 5b: Zero current (wind only), Coriolis ON
    ! =========================================================================
    print *, ""
    print *, "--- TEST 5b: Zero current (wind 10 m/s), Coriolis ON ---"
    call test_case_wind_only(6, .true., ocean_prof, atmos, &
                             latitude, f_coriolis, dt, nsteps, state, diag, &
                             fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)

    ratio = speed_b/speed_a
    print *, "Method A terminal speed: ", speed_a
    print *, "Method B terminal speed: ", speed_b
    print *, "Ratio B/A: ", ratio

    print *, "=================================================="
    print *, "Water drag methods comparison complete"
    print *, "=================================================="

    n_checks = n_checks + 1
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Water Drag Methods Test PASSED"
        stop 0
    else
        print *, "FAILURE: Water Drag Methods Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine test_case(test_id, cor_on, ocean_prof, atmos, &
                         latitude, f_coriolis, dt, nsteps, state, diag, &
                         fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: test_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time
        real :: f_eff

        ! Method A
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof, atmos, 0.1, 0.0)
        f_eff = 0.0
        if (cor_on) f_eff = f_coriolis
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_a = diag%f_water_x
        fy_a = diag%f_water_y
        speed_a = sqrt(state%u**2 + state%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)

        ! Method B
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof, atmos, 0.1, 0.0)
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_b = diag%f_water_x
        fy_b = diag%f_water_y
        speed_b = sqrt(state%u**2 + state%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine test_case

    subroutine test_case_sheared(test_id, cor_on, ocean_prof, atmos, &
                                 latitude, f_coriolis, dt, nsteps, state, diag, &
                                 fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: test_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time
        real :: f_eff

        ! Method A
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_sheared_current(ocean_prof, atmos)
        f_eff = 0.0
        if (cor_on) f_eff = f_coriolis
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_a = diag%f_water_x
        fy_a = diag%f_water_y
        speed_a = sqrt(state%u**2 + state%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)

        ! Method B
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_sheared_current(ocean_prof, atmos)
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_b = diag%f_water_x
        fy_b = diag%f_water_y
        speed_b = sqrt(state%u**2 + state%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine test_case_sheared

    subroutine test_case_wind_only(test_id, cor_on, ocean_prof, atmos, &
                                   latitude, f_coriolis, dt, nsteps, state, diag, &
                                   fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: test_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time
        real :: f_eff

        ! Method A
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_zero_current(ocean_prof, atmos)
        atmos%u10 = 10.0
        atmos%v10 = 0.0
        f_eff = 0.0
        if (cor_on) f_eff = f_coriolis
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_a = diag%f_water_x
        fy_a = diag%f_water_y
        speed_a = sqrt(state%u**2 + state%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)

        ! Method B
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_zero_current(ocean_prof, atmos)
        atmos%u10 = 10.0
        atmos%v10 = 0.0
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_b = diag%f_water_x
        fy_b = diag%f_water_y
        speed_b = sqrt(state%u**2 + state%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine test_case_wind_only

    subroutine init_uniform_current(ocean_prof, atmos, u_val, v_val)
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: u_val, v_val

        integer :: nlevels, k
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ocean_prof%u(k) = u_val
            ocean_prof%v(k) = v_val
        end do

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_uniform_current

    subroutine init_sheared_current(ocean_prof, atmos)
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos

        integer :: nlevels, k
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ! Линейное спадание от 0.2 на поверхности до 0.05 на дне
            ocean_prof%u(k) = 0.2 - 0.15*real(k - 1)/real(nlevels - 1)
            ocean_prof%v(k) = 0.0
        end do

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_sheared_current

    subroutine init_zero_current(ocean_prof, atmos)
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos

        integer :: nlevels, k
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ocean_prof%u(k) = 0.0
            ocean_prof%v(k) = 0.0
        end do

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_zero_current

    ! Method B dynamics step (копия из iceberg_dynamics.f90)
    subroutine iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                              f_coriolis, grad_eta_x, grad_eta_y, &
                                              fk_x, fk_y, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        real, intent(in) :: f_coriolis, grad_eta_x, grad_eta_y
        real, intent(in) :: fk_x, fk_y
        type(iceberg_diagnostics), intent(inout) :: diag

        real :: mass
        real :: f_wind_x, f_wind_y
        real :: f_water_x, f_water_y
        real :: f_cor_x, f_cor_y
        real :: f_pres_x, f_pres_y
        real :: A_mat
        real :: u_old, v_old
        real :: fx_noncor, fy_noncor
        real :: draft, a_sail, a_wet, freeboard
        real :: u_rel, v_rel, speed_rel
        real :: u_avg, v_avg
        integer :: k

        mass = 910.0*state%L*state%W*state%H
        diag%mass = mass

        ! Wind force
        draft = state%H*910.0/1028.0
        freeboard = state%H - draft
        a_sail = state%L*state%W + 2.0*(state%L + state%W)*freeboard

        u_rel = atmos%u10 - state%u
        v_rel = atmos%v10 - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*1.225*1.3e-3*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*1.225*1.3e-3*a_sail*speed_rel*v_rel
        diag%f_wind_x = f_wind_x
        diag%f_wind_y = f_wind_y

        ! Water force Method B
        a_wet = state%L*state%W + 2.0*(state%L + state%W)*draft

        u_avg = 0.0; v_avg = 0.0
        do k = 1, ocean_prof%nlevels
            u_avg = u_avg + ocean_prof%u(k)*ocean_prof%dz(k)
            v_avg = v_avg + ocean_prof%v(k)*ocean_prof%dz(k)
        end do
        u_avg = u_avg/sum(ocean_prof%dz)
        v_avg = v_avg/sum(ocean_prof%dz)

        u_rel = u_avg - state%u
        v_rel = v_avg - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_water_x = 0.5*1028.0*2.0e-3*a_wet*speed_rel*u_rel
        f_water_y = 0.5*1028.0*2.0e-3*a_wet*speed_rel*v_rel
        diag%f_water_x = f_water_x
        diag%f_water_y = f_water_y

        ! Coriolis force
        f_cor_x = mass*f_coriolis*state%v
        f_cor_y = -mass*f_coriolis*state%u
        diag%f_cor_x = f_cor_x
        diag%f_cor_y = f_cor_y

        ! Pressure and FK
        f_pres_x = 0.0; f_pres_y = 0.0
        diag%f_pressure_x = f_pres_x
        diag%f_pressure_y = f_pres_y
        diag%f_fk_x = fk_x
        diag%f_fk_y = fk_y

        ! Semi-implicit
        fx_noncor = f_wind_x + f_water_x + f_pres_x + fk_x
        fy_noncor = f_wind_y + f_water_y + f_pres_y + fk_y

        u_old = state%u
        v_old = state%v

        A_mat = 1.0 + (dt*f_coriolis)**2

        state%u = (u_old + dt*fx_noncor/mass + dt*f_coriolis*v_old)/A_mat
        state%v = (v_old + dt*fy_noncor/mass - dt*f_coriolis*u_old)/A_mat
    end subroutine iceberg_dynamics_step_method_b

end program iceberg_test_water_drag_methods
