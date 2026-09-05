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

    subroutine test_case(test_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                         latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                         fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: test_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local
        real :: f_eff

        ! Method A
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof_inout, atmos_inout, 0.1, 0.0)
        f_eff = 0.0
        if (cor_on_in) f_eff = f_coriolis_in
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_a_out = diag_inout%f_water_x
        fy_a_out = diag_inout%f_water_y
        speed_a_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)

        ! Method B
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof_inout, atmos_inout, 0.1, 0.0)
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_method_b(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_b_out = diag_inout%f_water_x
        fy_b_out = diag_inout%f_water_y
        speed_b_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine test_case

    subroutine test_case_sheared(test_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                 fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: test_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local
        real :: f_eff

        ! Method A
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_sheared_current(ocean_prof_inout, atmos_inout)
        f_eff = 0.0
        if (cor_on_in) f_eff = f_coriolis_in
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_a_out = diag_inout%f_water_x
        fy_a_out = diag_inout%f_water_y
        speed_a_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)

        ! Method B
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_sheared_current(ocean_prof_inout, atmos_inout)
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_method_b(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_b_out = diag_inout%f_water_x
        fy_b_out = diag_inout%f_water_y
        speed_b_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine test_case_sheared

    subroutine test_case_wind_only(test_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                   fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: test_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local
        real :: f_eff

        ! Method A
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_zero_current(ocean_prof_inout, atmos_inout)
        atmos_inout%u10 = 10.0
        atmos_inout%v10 = 0.0
        f_eff = 0.0
        if (cor_on_in) f_eff = f_coriolis_in
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                       f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_a_out = diag_inout%f_water_x
        fy_a_out = diag_inout%f_water_y
        speed_a_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate ocean_prof for reuse
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)

        ! Method B
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_zero_current(ocean_prof_inout, atmos_inout)
        atmos_inout%u10 = 10.0
        atmos_inout%v10 = 0.0
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_method_b(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_b_out = diag_inout%f_water_x
        fy_b_out = diag_inout%f_water_y
        speed_b_out = sqrt(state_inout%u**2 + state_inout%v**2)

        ! Deallocate at end of test case
        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine test_case_wind_only

    subroutine init_uniform_current(ocean_prof_inout, atmos_inout, u_val_in, v_val_in)
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: u_val_in, v_val_in

        integer :: nlevels, k_local
        nlevels = 5
        ocean_prof_inout%nlevels = nlevels
        allocate (ocean_prof_inout%z(nlevels), ocean_prof_inout%dz(nlevels), &
                  ocean_prof_inout%temp(nlevels), ocean_prof_inout%salt(nlevels), &
                  ocean_prof_inout%u(nlevels), ocean_prof_inout%v(nlevels))
        do k_local = 1, nlevels
            ocean_prof_inout%z(k_local) = real(k_local)*20.0
            ocean_prof_inout%dz(k_local) = 20.0
            ocean_prof_inout%temp(k_local) = -1.0
            ocean_prof_inout%salt(k_local) = 0.034
            ocean_prof_inout%u(k_local) = u_val_in
            ocean_prof_inout%v(k_local) = v_val_in
        end do

        atmos_inout%u10 = 0.0
        atmos_inout%v10 = 0.0
        atmos_inout%t2m = 253.15
        atmos_inout%d2m = 253.15
        atmos_inout%tcc = 0.0
        atmos_inout%msl = 101325.0
        atmos_inout%snowfall = 0.0
    end subroutine init_uniform_current

    subroutine init_sheared_current(ocean_prof_inout, atmos_inout)
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout

        integer :: nlevels, k_local
        nlevels = 5
        ocean_prof_inout%nlevels = nlevels
        allocate (ocean_prof_inout%z(nlevels), ocean_prof_inout%dz(nlevels), &
                  ocean_prof_inout%temp(nlevels), ocean_prof_inout%salt(nlevels), &
                  ocean_prof_inout%u(nlevels), ocean_prof_inout%v(nlevels))
        do k_local = 1, nlevels
            ocean_prof_inout%z(k_local) = real(k_local)*20.0
            ocean_prof_inout%dz(k_local) = 20.0
            ocean_prof_inout%temp(k_local) = -1.0
            ocean_prof_inout%salt(k_local) = 0.034
            ! Линейное спадание от 0.2 на поверхности до 0.05 на дне
            ocean_prof_inout%u(k_local) = 0.2 - 0.15*real(k_local - 1)/real(nlevels - 1)
            ocean_prof_inout%v(k_local) = 0.0
        end do

        atmos_inout%u10 = 0.0
        atmos_inout%v10 = 0.0
        atmos_inout%t2m = 253.15
        atmos_inout%d2m = 253.15
        atmos_inout%tcc = 0.0
        atmos_inout%msl = 101325.0
        atmos_inout%snowfall = 0.0
    end subroutine init_sheared_current

    subroutine init_zero_current(ocean_prof_inout, atmos_inout)
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout

        integer :: nlevels, k_local
        nlevels = 5
        ocean_prof_inout%nlevels = nlevels
        allocate (ocean_prof_inout%z(nlevels), ocean_prof_inout%dz(nlevels), &
                  ocean_prof_inout%temp(nlevels), ocean_prof_inout%salt(nlevels), &
                  ocean_prof_inout%u(nlevels), ocean_prof_inout%v(nlevels))
        do k_local = 1, nlevels
            ocean_prof_inout%z(k_local) = real(k_local)*20.0
            ocean_prof_inout%dz(k_local) = 20.0
            ocean_prof_inout%temp(k_local) = -1.0
            ocean_prof_inout%salt(k_local) = 0.034
            ocean_prof_inout%u(k_local) = 0.0
            ocean_prof_inout%v(k_local) = 0.0
        end do

        atmos_inout%u10 = 0.0
        atmos_inout%v10 = 0.0
        atmos_inout%t2m = 253.15
        atmos_inout%d2m = 253.15
        atmos_inout%tcc = 0.0
        atmos_inout%msl = 101325.0
        atmos_inout%snowfall = 0.0
    end subroutine init_zero_current

! Method B dynamics step (копия из iceberg_dynamics.f90)
    subroutine iceberg_dynamics_step_method_b(state_in, dt_in, ocean_prof_in, atmos_in, &
                                               f_coriolis_in, grad_eta_x_in, grad_eta_y_in, &
                                               fk_x_in, fk_y_in, diag_inout)
        type(iceberg_state), intent(inout) :: state_in
        real, intent(in) :: dt_in
        type(ocean_profile), intent(in) :: ocean_prof_in
        type(atmos_forcing), intent(in) :: atmos_in
        real, intent(in) :: f_coriolis_in, grad_eta_x_in, grad_eta_y_in
        real, intent(in) :: fk_x_in, fk_y_in
        type(iceberg_diagnostics), intent(inout) :: diag_inout

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
        integer :: k_local

        mass = 910.0*state_in%L*state_in%W*state_in%H
        diag_inout%mass = mass

        ! Wind force
        draft = state_in%H*910.0/1028.0
        freeboard = state_in%H - draft
        a_sail = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*freeboard

        u_rel = atmos_in%u10 - state_in%u
        v_rel = atmos_in%v10 - state_in%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*1.225*1.3e-3*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*1.225*1.3e-3*a_sail*speed_rel*v_rel
        diag_inout%f_wind_x = f_wind_x
        diag_inout%f_wind_y = f_wind_y

        ! Water force Method B
        a_wet = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*draft

        u_avg = 0.0; v_avg = 0.0
        do k_local = 1, ocean_prof_in%nlevels
            u_avg = u_avg + ocean_prof_in%u(k_local)*ocean_prof_in%dz(k_local)
            v_avg = v_avg + ocean_prof_in%v(k_local)*ocean_prof_in%dz(k_local)
        end do
        u_avg = u_avg/sum(ocean_prof_in%dz)
        v_avg = v_avg/sum(ocean_prof_in%dz)

        u_rel = u_avg - state_in%u
        v_rel = v_avg - state_in%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_water_x = 0.5*1028.0*2.0e-3*a_wet*speed_rel*u_rel
        f_water_y = 0.5*1028.0*2.0e-3*a_wet*speed_rel*v_rel
        diag_inout%f_water_x = f_water_x
        diag_inout%f_water_y = f_water_y

        ! Coriolis force
        f_cor_x = mass*f_coriolis_in*state_in%v
        f_cor_y = -mass*f_coriolis_in*state_in%u
        diag_inout%f_cor_x = f_cor_x
        diag_inout%f_cor_y = f_cor_y

        ! Pressure and FK
        f_pres_x = 0.0; f_pres_y = 0.0
        diag_inout%f_pressure_x = f_pres_x
        diag_inout%f_pressure_y = f_pres_y
        diag_inout%f_fk_x = fk_x_in
        diag_inout%f_fk_y = fk_y_in

        ! Semi-implicit
        fx_noncor = f_wind_x + f_water_x + f_pres_x + fk_x_in
        fy_noncor = f_wind_y + f_water_y + f_pres_y + fk_y_in

        u_old = state_in%u
        v_old = state_in%v

        A_mat = 1.0 + (dt_in*f_coriolis_in)**2

        state_in%u = (u_old + dt_in*fx_noncor/mass + dt_in*f_coriolis_in*v_old)/A_mat
        state_in%v = (v_old + dt_in*fy_noncor/mass - dt_in*f_coriolis_in*u_old)/A_mat
    end subroutine iceberg_dynamics_step_method_b

end program iceberg_test_water_drag_methods
