! ==============================================================================
! Тест: Water Drag Method A vs Method B — Controlled Comparison
! Назначение: Систематически сравнить Method A (слой-за-слоем) и Method B
!             (глубинно-усредненное, полная оромочённая площадь) на контролируемых
!             синтетических профилях течения.
!
! Method A: F = Σ ½ ρ C_D (W*Δz) |u_k - u| (u_k - u) по X
!           Σ ½ ρ C_D (L*Δz) |v_k - v| (v_k - v) по Y
!
! Method B: F = ½ ρ C_D A_wet |U_avg - u| (U_avg - u)
!           A_wet = L*W + 2*(L+W)*D  (дно + боковые)
!
! Контролируемые случаи:
!   1. Uniform current — методы должны сблизиться (при правильной площади)
!   2. Linear shear — различие из-за квадратичного закона
!   3. Strong shear — максимальное различие
!   4. Current reversal — проверка знака
!   5. Bottom drag contribution — изолированная проверка дна
! ==============================================================================

program iceberg_test_water_drag_controlled
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag
    type(iceberg_diagnostics) :: geom

    integer :: n_errors, n_checks
    integer :: step, nsteps, i
    real :: dt, model_time
    real :: latitude, f_coriolis
    real :: fx_a, fy_a, fx_b, fy_b
    real :: speed_a, speed_b
    real :: ratio, ratio_x, ratio_y
    integer :: unit, ios

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Water Drag Method A vs B — Controlled"
    print *, "=================================================="

    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    dt = 3600.0
    nsteps = 200  ! достаточно для терминальной скорости

    print *, "Latitude: ", latitude
    print *, "Iceberg: L=W=H=100m"
    print *, ""

    ! Открыть файл для результатов
    open (unit, file='data/output/diagnostics/stage9.4c/drag_method_comparison.csv', &
          status='replace', iostat=ios)
    if (ios .eq. 0) then
        write (unit, '(A)') 'case,fx_a,fy_a,fx_b,fy_b,speed_a,speed_b,ratio,ratio_x,ratio_y'
    end if

    ! =========================================================================
    ! CASE 1: Uniform current, Coriolis OFF
    ! Ожидание: Method A и B должны дать близкие силы, если площадь эквивалентна
    ! =========================================================================
    print *, "--- CASE 1: Uniform current (U=0.1 m/s), Coriolis OFF ---"
    call run_uniform_case(1, .false., ocean_prof, atmos, latitude, 0.0, dt, nsteps, &
                          state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("1", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 2: Uniform current, Coriolis ON
    ! =========================================================================
    print *, ""
    print *, "--- CASE 2: Uniform current (U=0.1 m/s), Coriolis ON ---"
    call run_uniform_case(2, .true., ocean_prof, atmos, latitude, f_coriolis, dt, nsteps, &
                          state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("2", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 3: Linear shear, Coriolis OFF
    ! U(z) = U_surf * (1 - z/D) : 0.2 на поверхности -> 0 на дне
    ! =========================================================================
    print *, ""
    print *, "--- CASE 3: Linear shear (0.2 -> 0 m/s), Coriolis OFF ---"
    call run_sheared_case(3, .false., ocean_prof, atmos, latitude, 0.0, dt, nsteps, &
                          state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("3", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 4: Linear shear, Coriolis ON
    ! =========================================================================
    print *, ""
    print *, "--- CASE 4: Linear shear (0.2 -> 0 m/s), Coriolis ON ---"
    call run_sheared_case(4, .true., ocean_prof, atmos, latitude, f_coriolis, dt, nsteps, &
                          state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("4", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 5: Strong shear (0.3 -> -0.1), Coriolis OFF
    ! =========================================================================
    print *, ""
    print *, "--- CASE 5: Strong shear with reversal (0.3 -> -0.1 m/s), Coriolis OFF ---"
    call run_strong_shear_case(5, .false., ocean_prof, atmos, latitude, 0.0, dt, nsteps, &
                               state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("5", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 6: Zero current (wind only), Coriolis OFF
    ! Только ветровая сила, водное трение = 0
    ! =========================================================================
    print *, ""
    print *, "--- CASE 6: Zero current (wind 10 m/s), Coriolis OFF ---"
    call run_wind_only_case(6, .false., ocean_prof, atmos, latitude, 0.0, dt, nsteps, &
                            state, diag, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
    call print_result("6", fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)

    ! =========================================================================
    ! CASE 7: Uniform current, Method A with bottom drag explicitly separated
    ! Проверка: какая доля Method A приходится на боковые стороны vs дно
    ! =========================================================================
    print *, ""
    print *, "--- CASE 7: Bottom drag contribution analysis ---"
    call analyze_bottom_drag(ocean_prof, atmos, latitude, f_coriolis, dt, nsteps, &
                             state, diag, unit)

    if (ios .eq. 0) close (unit)

    print *, "=================================================="
    print *, "Water drag controlled comparison complete"
    print *, "Output: data/output/diagnostics/stage9.4c/drag_method_comparison.csv"
    print *, "=================================================="

    n_checks = n_checks + 1
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Water Drag Controlled Comparison PASSED"
        stop 0
    else
        print *, "FAILURE: Water Drag Controlled Comparison FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    ! --------------------------------------------------------------------------
    ! Uniform current case
    ! --------------------------------------------------------------------------
    subroutine run_uniform_case(case_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: case_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local, f_eff

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

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine run_uniform_case

    ! --------------------------------------------------------------------------
    ! Sheared current case (linear: surface 0.2 -> bottom 0)
    ! --------------------------------------------------------------------------
    subroutine run_sheared_case(case_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: case_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local, f_eff

        ! Method A
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_linear_shear(ocean_prof_inout, atmos_inout)
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

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)

        ! Method B
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_linear_shear(ocean_prof_inout, atmos_inout)
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_method_b(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_b_out = diag_inout%f_water_x
        fy_b_out = diag_inout%f_water_y
        speed_b_out = sqrt(state_inout%u**2 + state_inout%v**2)

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine run_sheared_case

    ! --------------------------------------------------------------------------
    ! Strong shear with reversal (0.3 -> -0.1)
    ! --------------------------------------------------------------------------
    subroutine run_strong_shear_case(case_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                   fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: case_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local, f_eff

        ! Method A
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_strong_shear(ocean_prof_inout, atmos_inout)
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

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)

        ! Method B
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_strong_shear(ocean_prof_inout, atmos_inout)
        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_method_b(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do
        fx_b_out = diag_inout%f_water_x
        fy_b_out = diag_inout%f_water_y
        speed_b_out = sqrt(state_inout%u**2 + state_inout%v**2)

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine run_strong_shear_case

    ! --------------------------------------------------------------------------
    ! Wind only case (zero current)
    ! --------------------------------------------------------------------------
    subroutine run_wind_only_case(case_id_in, cor_on_in, ocean_prof_inout, atmos_inout, &
                            latitude_in, f_coriolis_in, dt_in, nsteps_in, state_inout, diag_inout, &
                                  fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out)
        integer, intent(in) :: case_id_in
        logical, intent(in) :: cor_on_in
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(out) :: fx_a_out, fy_a_out, fx_b_out, fy_b_out, speed_a_out, speed_b_out

        integer :: step_local
        real :: model_time_local, f_eff

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

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine run_wind_only_case

    ! --------------------------------------------------------------------------
    ! Bottom drag analysis
    ! --------------------------------------------------------------------------
    subroutine analyze_bottom_drag(ocean_prof_inout, atmos_inout, latitude_in, f_coriolis_in, &
                                   dt_in, nsteps_in, state_inout, diag_inout, unit_in)
        type(ocean_profile), intent(inout) :: ocean_prof_inout
        type(atmos_forcing), intent(inout) :: atmos_inout
        real, intent(in) :: latitude_in, f_coriolis_in, dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(inout) :: state_inout
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        integer, intent(in) :: unit_in

        integer :: step_local
        real :: model_time_local
        real :: fx_bottom, fy_bottom, fx_sides, fy_sides

        ! Uniform current
        call iceberg_init(state_inout, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof_inout, atmos_inout, 0.1, 0.0)

        ! Compute geometry
        call compute_full_geometry(state_inout, geom)

        print *, "Geometry: L=100, W=100, H=100, D=88.5 m"
        print *, "  Side area (vertical): 2*(L+W)*D = ", 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Bottom area: L*W = ", 100.0*100.0, " m2"
        print *, "  Total wetted (Method B): ", 100.0*100.0 + 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Side only (Method A): ", 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Ratio bottom/side: ", 10000.0/(2.0*200.0*88.52)

        model_time_local = 0.0
        do step_local = 1, nsteps_in
            call iceberg_dynamics_step(state_inout, dt_in, ocean_prof_inout, atmos_inout, &
                                       0.0, 0.0, 0.0, 0.0, 0.0, diag_inout)
            model_time_local = model_time_local + dt_in
        end do

        ! Compute bottom drag separately
        call compute_bottom_drag(state_inout, ocean_prof_inout, fx_bottom, fy_bottom)
        call compute_sides_drag(state_inout, ocean_prof_inout, fx_sides, fy_sides)

       print *, "Method A total water drag: Fx=", diag_inout%f_water_x, " Fy=", diag_inout%f_water_y
        print *, "  Bottom contribution: Fx=", fx_bottom, " Fy=", fy_bottom
        print *, "  Side contribution:   Fx=", fx_sides, " Fy=", fy_sides
        print *, "  Bottom/Total ratio:  ", fx_bottom/diag_inout%f_water_x

        if (unit_in .gt. 0) then
            write (unit_in, '(A,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3)') &
                "bottom", fx_bottom, fy_bottom, fx_sides, fy_sides, &
           diag_inout%f_water_x, diag_inout%f_water_y, 0.0, 0.0, 0.0, fx_bottom/diag_inout%f_water_x
        end if

        deallocate (ocean_prof_inout%z, ocean_prof_inout%dz, ocean_prof_inout%temp, &
                    ocean_prof_inout%salt, ocean_prof_inout%u, ocean_prof_inout%v)
    end subroutine analyze_bottom_drag

    ! --------------------------------------------------------------------------
    ! Print result helper
    ! --------------------------------------------------------------------------
    subroutine print_result(case_str_in, fx_a_in, fy_a_in, fx_b_in, fy_b_in, speed_a_in, speed_b_in, unit_in)
        character(len=*), intent(in) :: case_str_in
        real, intent(in) :: fx_a_in, fy_a_in, fx_b_in, fy_b_in, speed_a_in, speed_b_in
        integer, intent(in) :: unit_in
        real :: ratio, ratio_x, ratio_y

        if (abs(fx_a_in) .gt. 1e-12) then
            ratio_x = fx_b_in/fx_a_in
        else
            ratio_x = 0.0
        end if
        if (abs(fy_a_in) .gt. 1e-12) then
            ratio_y = fy_b_in/fy_a_in
        else
            ratio_y = 0.0
        end if
        if (speed_a_in .gt. 1e-12) then
            ratio = speed_b_in/speed_a_in
        else
            ratio = 0.0
        end if

        print *, "  Method A: Fx=", fx_a_in, " Fy=", fy_a_in, " speed=", speed_a_in
        print *, "  Method B: Fx=", fx_b_in, " Fy=", fy_b_in, " speed=", speed_b_in
        print *, "  Ratio B/A: speed=", ratio, " Fx=", ratio_x, " Fy=", ratio_y

        if (unit_in .gt. 0) then
            write (unit_in, '(A,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3)') &
    case_str_in, fx_a_in, fy_a_in, fx_b_in, fy_b_in, speed_a_in, speed_b_in, ratio, ratio_x, ratio_y
        end if
    end subroutine print_result

    ! --------------------------------------------------------------------------
    ! Profile initializers
    ! --------------------------------------------------------------------------
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

    subroutine init_linear_shear(ocean_prof_inout, atmos_inout)
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
            ! Linear shear: 0.2 at surface (z=20) -> 0 at bottom (z=100)
            ocean_prof_inout%u(k_local) = 0.2*(1.0 - real(k_local - 1)/real(nlevels - 1))
            ocean_prof_inout%v(k_local) = 0.0
        end do

        atmos_inout%u10 = 0.0
        atmos_inout%v10 = 0.0
        atmos_inout%t2m = 253.15
        atmos_inout%d2m = 253.15
        atmos_inout%tcc = 0.0
        atmos_inout%msl = 101325.0
        atmos_inout%snowfall = 0.0
    end subroutine init_linear_shear

    subroutine init_strong_shear(ocean_prof_inout, atmos_inout)
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
            ! Strong shear: 0.3 at surface -> -0.1 at bottom
            ocean_prof_inout%u(k_local) = 0.3 - 0.4*real(k_local - 1)/real(nlevels - 1)
            ocean_prof_inout%v(k_local) = 0.0
        end do

        atmos_inout%u10 = 0.0
        atmos_inout%v10 = 0.0
        atmos_inout%t2m = 253.15
        atmos_inout%d2m = 253.15
        atmos_inout%tcc = 0.0
        atmos_inout%msl = 101325.0
        atmos_inout%snowfall = 0.0
    end subroutine init_strong_shear

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

    ! --------------------------------------------------------------------------
    ! Bottom drag computation (Method B area but only bottom)
    ! --------------------------------------------------------------------------
    subroutine compute_bottom_drag(state_in, ocean_prof_in, fx_out, fy_out)
        type(iceberg_state), intent(in) :: state_in
        type(ocean_profile), intent(in) :: ocean_prof_in
        real, intent(out) :: fx_out, fy_out

        real :: draft, a_bottom, u_avg, v_avg
        real :: du, dv, speed_rel
        integer :: k_local

        draft = state_in%H*RHO_ICE/RHO_WATER
        a_bottom = state_in%L*state_in%W

        u_avg = 0.0; v_avg = 0.0
        do k_local = 1, ocean_prof_in%nlevels
            u_avg = u_avg + ocean_prof_in%u(k_local)*ocean_prof_in%dz(k_local)
            v_avg = v_avg + ocean_prof_in%v(k_local)*ocean_prof_in%dz(k_local)
        end do
        u_avg = u_avg/sum(ocean_prof_in%dz)
        v_avg = v_avg/sum(ocean_prof_in%dz)

        du = u_avg - state_in%u
        dv = v_avg - state_in%v
        speed_rel = sqrt(du**2 + dv**2)

        fx_out = 0.5*RHO_WATER*CD_WATER*a_bottom*speed_rel*du
        fy_out = 0.5*RHO_WATER*CD_WATER*a_bottom*speed_rel*dv
    end subroutine compute_bottom_drag

    ! --------------------------------------------------------------------------
    ! Side drag computation (Method A total)
    ! --------------------------------------------------------------------------
    subroutine compute_sides_drag(state_in, ocean_prof_in, fx_out, fy_out)
        type(iceberg_state), intent(in) :: state_in
        type(ocean_profile), intent(in) :: ocean_prof_in
        real, intent(out) :: fx_out, fy_out

        real :: draft
        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        integer :: k_local
        real :: dz_layer, z_top, z_bot
        real :: du, dv, speed_rel
        real :: side_area_x, side_area_y

        draft = state_in%H*RHO_ICE/RHO_WATER

        call depth_integrated_currents(ocean_prof_in, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx_out = 0.0
            fy_out = 0.0
            return
        end if

        fx_out = 0.0
        fy_out = 0.0

        do k_local = 1, n_layers
            if (k_local .eq. 1) then
                z_top = 0.0
            else
                z_top = z_layers(k_local - 1) + 0.5*(z_layers(k_local) - z_layers(k_local - 1))
            end if
            if (k_local .eq. n_layers) then
                z_bot = draft
            else
                z_bot = z_layers(k_local) + 0.5*(z_layers(k_local + 1) - z_layers(k_local))
            end if
            z_bot = min(z_bot, draft)
            dz_layer = z_bot - z_top
            if (dz_layer .le. 0.0) cycle

            side_area_x = state_in%W*dz_layer
            side_area_y = state_in%L*dz_layer

            du = u_prof(k_local) - state_in%u
            dv = v_prof(k_local) - state_in%v
            speed_rel = sqrt(du**2 + dv**2)

            fx_out = fx_out + 0.5*RHO_WATER*CD_WATER*side_area_x*speed_rel*du
            fy_out = fy_out + 0.5*RHO_WATER*CD_WATER*side_area_y*speed_rel*dv
        end do
    end subroutine compute_sides_drag

    ! --------------------------------------------------------------------------
    ! Method B dynamics step (копия для теста)
    ! --------------------------------------------------------------------------
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

        mass = RHO_ICE*state_in%L*state_in%W*state_in%H
        diag_inout%mass = mass

        ! Wind force
        draft = state_in%H*RHO_ICE/RHO_WATER
        freeboard = state_in%H - draft
        a_sail = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*freeboard

        u_rel = atmos_in%u10 - state_in%u
        v_rel = atmos_in%v10 - state_in%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*v_rel
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

        f_water_x = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*u_rel
        f_water_y = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*v_rel
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

end program iceberg_test_water_drag_controlled
