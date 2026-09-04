! ==============================================================================
! Тест: Wind Drift Sensitivity Analysis
! Назначение: Исследование чувствительности дрейфа к CD_AIR и CD_WATER.
!             Контролируемые эксперименты с постоянным форсингом.
! ==============================================================================

program iceberg_test_wind_drift_sensitivity
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: i, j, step, nsteps
    integer :: unit, ios
    real :: dt, model_time
    real :: latitude, f_coriolis
    real :: u0, wind_speed
    real :: cd_air_vals(4), cd_water_vals(4)
    real :: terminal_u, terminal_v, terminal_speed
    real :: drift_ratio
    real :: mass
    real :: fx_wind, fx_water, fx_cor

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Wind Drift Sensitivity"
    print *, "=================================================="

    latitude = 75.0
    f_coriolis = 2.0*7.2921150e-5*sin(latitude/57.2957795)
    wind_speed = 10.0  ! m/s
    u0 = 0.0

    print *, "Latitude: ", latitude
    print *, "Wind speed: ", wind_speed, " m/s"
    print *, "f = ", f_coriolis
    print *, ""

    ! CD_AIR values to test
    cd_air_vals = [0.5e-3, 1.0e-3, 1.3e-3, 2.0e-3]
    ! CD_WATER values to test
    cd_water_vals = [1.0e-3, 2.0e-3, 3.0e-3, 4.0e-3]

    dt = 3600.0
    nsteps = 200  ! enough to reach terminal velocity

    ! Открыть файл для результатов
    open (unit, file='data/output/diagnostics/stage9.3/wind_drift_sensitivity.csv', &
          status='replace', iostat=ios)
    if (ios .eq. 0) then
        write(unit, '(A)') 'case,cd_air,cd_water,cor_on,terminal_u,terminal_v,terminal_speed,drift_ratio,wind_speed,fx_wind,fx_water,fx_cor'
    end if

    print *, "Case    CD_AIR    CD_WATER   Cor?  U_term    V_term    Speed    Drift%   Fx_wind  Fx_water  Fx_cor"

    ! =========================================================================
    ! CASE A: Coriolis OFF, varying CD_AIR, CD_WATER = 2e-3 (default)
    ! =========================================================================
    do i = 1, 4
        call run_case(unit, cd_air_vals(i), 2.0e-3, .false., &
                      latitude, f_coriolis, wind_speed, dt, nsteps, &
                      terminal_u, terminal_v, terminal_speed, drift_ratio, mass, &
                      fx_wind, fx_water, fx_cor)
        print '(A6,2F9.1,1X,L4,2F9.4,F9.4,F8.2,3F9.1)', &
            "A-"//char(64 + i), cd_air_vals(i)*1e3, 2.0, .false., &
            terminal_u, terminal_v, terminal_speed, drift_ratio*100, fx_wind, fx_water, fx_cor
    end do

    ! =========================================================================
    ! CASE B: Coriolis ON, varying CD_AIR, CD_WATER = 2e-3
    ! =========================================================================
    do i = 1, 4
        call run_case(unit, cd_air_vals(i), 2.0e-3, .true., &
                      latitude, f_coriolis, wind_speed, dt, nsteps, &
                      terminal_u, terminal_v, terminal_speed, drift_ratio, mass, &
                      fx_wind, fx_water, fx_cor)
        print '(A6,2F9.1,1X,L4,2F9.4,F9.4,F8.2,3F9.1)', &
            "B-"//char(64 + i), cd_air_vals(i)*1e3, 2.0, .true., &
            terminal_u, terminal_v, terminal_speed, drift_ratio*100, fx_wind, fx_water, fx_cor
    end do

    ! =========================================================================
    ! CASE C: Coriolis OFF, CD_AIR = 1.3e-3, varying CD_WATER
    ! =========================================================================
    do i = 1, 4
        call run_case(unit, 1.3e-3, cd_water_vals(i), .false., &
                      latitude, f_coriolis, wind_speed, dt, nsteps, &
                      terminal_u, terminal_v, terminal_speed, drift_ratio, mass, &
                      fx_wind, fx_water, fx_cor)
        print '(A6,2F9.1,1X,L4,2F9.4,F9.4,F8.2,3F9.1)', &
            "C-"//char(64 + i), 1.3, cd_water_vals(i)*1e3, .false., &
            terminal_u, terminal_v, terminal_speed, drift_ratio*100, fx_wind, fx_water, fx_cor
    end do

    ! =========================================================================
    ! CASE D: Coriolis ON, CD_AIR = 1.3e-3, varying CD_WATER
    ! =========================================================================
    do i = 1, 4
        call run_case(unit, 1.3e-3, cd_water_vals(i), .true., &
                      latitude, f_coriolis, wind_speed, dt, nsteps, &
                      terminal_u, terminal_v, terminal_speed, drift_ratio, mass, &
                      fx_wind, fx_water, fx_cor)
        print '(A6,2F9.1,1X,L4,2F9.4,F9.4,F8.2,3F9.1)', &
            "D-"//char(64 + i), 1.3, cd_water_vals(i)*1e3, .true., &
            terminal_u, terminal_v, terminal_speed, drift_ratio*100, fx_wind, fx_water, fx_cor
    end do

    if (ios .eq. 0) close (unit)

    print *, ""
    print *, "=================================================="
    print *, "Wind drift sensitivity test complete"
    print *, "Output: data/output/diagnostics/stage9.3/wind_drift_sensitivity.csv"
    print *, "=================================================="

    n_checks = n_checks + 1
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Wind Drift Sensitivity Test PASSED"
        stop 0
    else
        print *, "FAILURE: Wind Drift Sensitivity Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine run_case(unit, cd_air, cd_water, cor_on, &
                        latitude, f_coriolis, wind_speed, dt, nsteps, &
                        terminal_u, terminal_v, terminal_speed, drift_ratio, mass, &
                        fx_wind, fx_water, fx_cor)
        integer, intent(in) :: unit
        real, intent(in) :: cd_air, cd_water
        logical, intent(in) :: cor_on
        real, intent(in) :: latitude, f_coriolis, wind_speed, dt
        integer, intent(in) :: nsteps
        real, intent(out) :: terminal_u, terminal_v, terminal_speed, drift_ratio, mass
        real, intent(out) :: fx_wind, fx_water, fx_cor

        type(iceberg_state) :: state
        type(ocean_profile) :: ocean_prof
        type(atmos_forcing) :: atmos
        type(iceberg_diagnostics) :: diag

        integer :: step
        real :: model_time
        real :: f_eff

        call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude, 0.0, 0.0, 0.0)
        call init_zero_forcing(ocean_prof, atmos)

        ! Установить ветер
        atmos%u10 = wind_speed
        atmos%v10 = 0.0

        mass = 910.0*100.0*100.0*100.0

        model_time = 0.0
        f_eff = 0.0
        if (cor_on) f_eff = f_coriolis

        do step = 1, nsteps
            call iceberg_dynamics_step_custom(state, dt, ocean_prof, atmos, &
                                              f_eff, 0.0, 0.0, 0.0, 0.0, diag, &
                                              cd_air, cd_water)
            model_time = model_time + dt
        end do

        terminal_u = state%u
        terminal_v = state%v
        terminal_speed = sqrt(state%u**2 + state%v**2)
        drift_ratio = terminal_speed/wind_speed
        fx_wind = diag%f_wind_x
        fx_water = diag%f_water_x
        fx_cor = diag%f_cor_x
    end subroutine run_case

    subroutine init_zero_forcing(ocean_prof, atmos)
        type(ocean_profile), intent(out) :: ocean_prof
        type(atmos_forcing), intent(out) :: atmos

        integer :: nlevels
        nlevels = 1
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        ocean_prof%z(1) = 10.0
        ocean_prof%dz(1) = 10.0
        ocean_prof%temp(1) = -1.0
        ocean_prof%salt(1) = 0.034
        ocean_prof%u(1) = 0.0
        ocean_prof%v(1) = 0.0

        atmos%u10 = 0.0
        atmos%v10 = 0.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.0
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_zero_forcing

    ! Упрощенная версия iceberg_dynamics_step с кастомными CD
    subroutine iceberg_dynamics_step_custom(state, dt, ocean_prof, atmos, &
                                            f_coriolis, grad_eta_x, grad_eta_y, &
                                            fk_x, fk_y, diag, cd_air, cd_water)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        real, intent(in) :: f_coriolis, grad_eta_x, grad_eta_y
        real, intent(in) :: fk_x, fk_y
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(in) :: cd_air, cd_water

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

        ! Wind force with custom CD_AIR
        draft = state%H*910.0/1028.0
        freeboard = state%H - draft
        a_sail = state%L*state%W + 2.0*(state%L + state%W)*freeboard

        u_rel = atmos%u10 - state%u
        v_rel = atmos%v10 - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*1.225*cd_air*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*1.225*cd_air*a_sail*speed_rel*v_rel
        diag%f_wind_x = f_wind_x
        diag%f_wind_y = f_wind_y

        ! Water force with custom CD_WATER (depth-averaged)
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

        f_water_x = 0.5*1028.0*cd_water*a_wet*speed_rel*u_rel
        f_water_y = 0.5*1028.0*cd_water*a_wet*speed_rel*v_rel
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
    end subroutine iceberg_dynamics_step_custom

end program iceberg_test_wind_drift_sensitivity
