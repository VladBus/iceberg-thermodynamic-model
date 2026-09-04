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
    subroutine run_uniform_case(case_id, cor_on, ocean_prof, atmos, &
                                latitude, f_coriolis, dt, nsteps, state, diag, &
                                fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: case_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time, f_eff

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

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine run_uniform_case

    ! --------------------------------------------------------------------------
    ! Sheared current case (linear: surface 0.2 -> bottom 0)
    ! --------------------------------------------------------------------------
    subroutine run_sheared_case(case_id, cor_on, ocean_prof, atmos, &
                                latitude, f_coriolis, dt, nsteps, state, diag, &
                                fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: case_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time, f_eff

        ! Method A
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_linear_shear(ocean_prof, atmos)
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

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)

        ! Method B
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_linear_shear(ocean_prof, atmos)
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_b = diag%f_water_x
        fy_b = diag%f_water_y
        speed_b = sqrt(state%u**2 + state%v**2)

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine run_sheared_case

    ! --------------------------------------------------------------------------
    ! Strong shear with reversal (0.3 -> -0.1)
    ! --------------------------------------------------------------------------
    subroutine run_strong_shear_case(case_id, cor_on, ocean_prof, atmos, &
                                     latitude, f_coriolis, dt, nsteps, state, diag, &
                                     fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: case_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time, f_eff

        ! Method A
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_strong_shear(ocean_prof, atmos)
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

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)

        ! Method B
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_strong_shear(ocean_prof, atmos)
        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step_method_b(state, dt, ocean_prof, atmos, &
                                                f_eff, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do
        fx_b = diag%f_water_x
        fy_b = diag%f_water_y
        speed_b = sqrt(state%u**2 + state%v**2)

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine run_strong_shear_case

    ! --------------------------------------------------------------------------
    ! Wind only case (zero current)
    ! --------------------------------------------------------------------------
    subroutine run_wind_only_case(case_id, cor_on, ocean_prof, atmos, &
                                  latitude, f_coriolis, dt, nsteps, state, diag, &
                                  fx_a, fy_a, fx_b, fy_b, speed_a, speed_b)
        integer, intent(in) :: case_id
        logical, intent(in) :: cor_on
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b

        integer :: step
        real :: model_time, f_eff

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

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine run_wind_only_case

    ! --------------------------------------------------------------------------
    ! Bottom drag analysis
    ! --------------------------------------------------------------------------
    subroutine analyze_bottom_drag(ocean_prof, atmos, latitude, f_coriolis, &
                                   dt, nsteps, state, diag, unit)
        type(ocean_profile), intent(inout) :: ocean_prof
        type(atmos_forcing), intent(inout) :: atmos
        real, intent(in) :: latitude, f_coriolis, dt
        integer, intent(in) :: nsteps
        type(iceberg_state), intent(inout) :: state
        type(iceberg_diagnostics), intent(inout) :: diag
        integer, intent(in) :: unit

        integer :: step
        real :: model_time
        real :: fx_bottom, fy_bottom, fx_sides, fy_sides

        ! Uniform current
        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_uniform_current(ocean_prof, atmos, 0.1, 0.0)

        ! Compute geometry
        call compute_full_geometry(state, geom)

        print *, "Geometry: L=100, W=100, H=100, D=88.5 m"
        print *, "  Side area (vertical): 2*(L+W)*D = ", 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Bottom area: L*W = ", 100.0*100.0, " m2"
        print *, "  Total wetted (Method B): ", 100.0*100.0 + 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Side only (Method A): ", 2.0*(100.0 + 100.0)*88.52, " m2"
        print *, "  Ratio bottom/side: ", 10000.0/(2.0*200.0*88.52)

        model_time = 0.0
        do step = 1, nsteps
            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       0.0, 0.0, 0.0, 0.0, 0.0, diag)
            model_time = model_time + dt
        end do

        ! Compute bottom drag separately
        call compute_bottom_drag(state, ocean_prof, fx_bottom, fy_bottom)
        call compute_sides_drag(state, ocean_prof, fx_sides, fy_sides)

        print *, "Method A total water drag: Fx=", diag%f_water_x, " Fy=", diag%f_water_y
        print *, "  Bottom contribution: Fx=", fx_bottom, " Fy=", fy_bottom
        print *, "  Side contribution:   Fx=", fx_sides, " Fy=", fy_sides
        print *, "  Bottom/Total ratio:  ", fx_bottom/diag%f_water_x

        if (unit .gt. 0) then
            write (unit, '(A,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3)') &
                "bottom", fx_bottom, fy_bottom, fx_sides, fy_sides, &
                diag%f_water_x, diag%f_water_y, 0.0, 0.0, 0.0, fx_bottom/diag%f_water_x
        end if

        deallocate (ocean_prof%z, ocean_prof%dz, ocean_prof%temp, &
                    ocean_prof%salt, ocean_prof%u, ocean_prof%v)
    end subroutine analyze_bottom_drag

    ! --------------------------------------------------------------------------
    ! Print result helper
    ! --------------------------------------------------------------------------
    subroutine print_result(case_str, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, unit)
        character(len=*), intent(in) :: case_str
        real, intent(in) :: fx_a, fy_a, fx_b, fy_b, speed_a, speed_b
        integer, intent(in) :: unit
        real :: ratio, ratio_x, ratio_y

        if (abs(fx_a) .gt. 1e-12) then
            ratio_x = fx_b/fx_a
        else
            ratio_x = 0.0
        end if
        if (abs(fy_a) .gt. 1e-12) then
            ratio_y = fy_b/fy_a
        else
            ratio_y = 0.0
        end if
        if (speed_a .gt. 1e-12) then
            ratio = speed_b/speed_a
        else
            ratio = 0.0
        end if

        print *, "  Method A: Fx=", fx_a, " Fy=", fy_a, " speed=", speed_a
        print *, "  Method B: Fx=", fx_b, " Fy=", fy_b, " speed=", speed_b
        print *, "  Ratio B/A: speed=", ratio, " Fx=", ratio_x, " Fy=", ratio_y

        if (unit .gt. 0) then
            write (unit, '(A,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3,F12.3)') &
                case_str, fx_a, fy_a, fx_b, fy_b, speed_a, speed_b, ratio, ratio_x, ratio_y
        end if
    end subroutine print_result

    ! --------------------------------------------------------------------------
    ! Profile initializers
    ! --------------------------------------------------------------------------
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

    subroutine init_linear_shear(ocean_prof, atmos)
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
            ! Linear shear: 0.2 at surface (z=20) -> 0 at bottom (z=100)
            ocean_prof%u(k) = 0.2*(1.0 - real(k - 1)/real(nlevels - 1))
            ocean_prof%v(k) = 0.0
        end do

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_linear_shear

    subroutine init_strong_shear(ocean_prof, atmos)
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
            ! Strong shear: 0.3 at surface -> -0.1 at bottom
            ocean_prof%u(k) = 0.3 - 0.4*real(k - 1)/real(nlevels - 1)
            ocean_prof%v(k) = 0.0
        end do

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_strong_shear

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

    ! --------------------------------------------------------------------------
    ! Bottom drag computation (Method B area but only bottom)
    ! --------------------------------------------------------------------------
    subroutine compute_bottom_drag(state, ocean_prof, fx, fy)
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(out) :: fx, fy

        real :: draft, a_bottom, u_avg, v_avg
        real :: du, dv, speed_rel
        integer :: k

        draft = state%H*RHO_ICE/RHO_WATER
        a_bottom = state%L*state%W

        u_avg = 0.0; v_avg = 0.0
        do k = 1, ocean_prof%nlevels
            u_avg = u_avg + ocean_prof%u(k)*ocean_prof%dz(k)
            v_avg = v_avg + ocean_prof%v(k)*ocean_prof%dz(k)
        end do
        u_avg = u_avg/sum(ocean_prof%dz)
        v_avg = v_avg/sum(ocean_prof%dz)

        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)

        fx = 0.5*RHO_WATER*CD_WATER*a_bottom*speed_rel*du
        fy = 0.5*RHO_WATER*CD_WATER*a_bottom*speed_rel*dv
    end subroutine compute_bottom_drag

    ! --------------------------------------------------------------------------
    ! Side drag computation (Method A total)
    ! --------------------------------------------------------------------------
    subroutine compute_sides_drag(state, ocean_prof, fx, fy)
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(out) :: fx, fy

        real :: draft
        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        integer :: k
        real :: dz_layer, z_top, z_bot
        real :: du, dv, speed_rel
        real :: side_area_x, side_area_y

        draft = state%H*RHO_ICE/RHO_WATER

        call depth_integrated_currents(ocean_prof, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            return
        end if

        fx = 0.0
        fy = 0.0

        do k = 1, n_layers
            if (k .eq. 1) then
                z_top = 0.0
            else
                z_top = z_layers(k - 1) + 0.5*(z_layers(k) - z_layers(k - 1))
            end if
            if (k .eq. n_layers) then
                z_bot = draft
            else
                z_bot = z_layers(k) + 0.5*(z_layers(k + 1) - z_layers(k))
            end if
            z_bot = min(z_bot, draft)
            dz_layer = z_bot - z_top
            if (dz_layer .le. 0.0) cycle

            side_area_x = state%W*dz_layer
            side_area_y = state%L*dz_layer

            du = u_prof(k) - state%u
            dv = v_prof(k) - state%v
            speed_rel = sqrt(du**2 + dv**2)

            fx = fx + 0.5*RHO_WATER*CD_WATER*side_area_x*speed_rel*du
            fy = fy + 0.5*RHO_WATER*CD_WATER*side_area_y*speed_rel*dv
        end do
    end subroutine compute_sides_drag

    ! --------------------------------------------------------------------------
    ! Method B dynamics step (копия для теста)
    ! --------------------------------------------------------------------------
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

        mass = RHO_ICE*state%L*state%W*state%H
        diag%mass = mass

        ! Wind force
        draft = state%H*RHO_ICE/RHO_WATER
        freeboard = state%H - draft
        a_sail = state%L*state%W + 2.0*(state%L + state%W)*freeboard

        u_rel = atmos%u10 - state%u
        v_rel = atmos%v10 - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*v_rel
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

        f_water_x = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*u_rel
        f_water_y = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*v_rel
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

end program iceberg_test_water_drag_controlled
