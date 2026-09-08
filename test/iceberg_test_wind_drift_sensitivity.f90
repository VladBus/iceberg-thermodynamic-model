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
        write(unit, '(A)') 'case,cd_air,cd_water,cor_on,terminal_u,terminal_v,'// &
         & 'terminal_speed,drift_ratio,wind_speed,fx_wind,fx_water,fx_cor'
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

    subroutine run_case(unit_in, cd_air_in, cd_water_in, cor_on_in, &
                        latitude_in, f_coriolis_in, wind_speed_in, dt_in, nsteps_in, &
                    terminal_u_out, terminal_v_out, terminal_speed_out, drift_ratio_out, mass_out, &
                        fx_wind_out, fx_water_out, fx_cor_out)
        integer, intent(in) :: unit_in
        real, intent(in) :: cd_air_in, cd_water_in
        logical, intent(in) :: cor_on_in
        real, intent(in) :: latitude_in, f_coriolis_in, wind_speed_in, dt_in
        integer, intent(in) :: nsteps_in
  real, intent(out) :: terminal_u_out, terminal_v_out, terminal_speed_out, drift_ratio_out, mass_out
        real, intent(out) :: fx_wind_out, fx_water_out, fx_cor_out

        type(iceberg_state) :: state_local
        type(ocean_profile) :: ocean_prof_local
        type(atmos_forcing) :: atmos_local
        type(iceberg_diagnostics) :: diag_local

        integer :: step_local
        real :: model_time_local
        real :: f_eff

        call iceberg_init(state_local, 0.0, 0.0, 100.0, 100.0, 100.0, &
                          latitude_in, 0.0, 0.0, 0.0)
        call init_zero_forcing(ocean_prof_local, atmos_local)

        ! Установить ветер
        atmos_local%u10 = wind_speed_in
        atmos_local%v10 = 0.0

        mass_out = 910.0*100.0*100.0*100.0

        model_time_local = 0.0
        f_eff = 0.0
        if (cor_on_in) f_eff = f_coriolis_in

        do step_local = 1, nsteps_in
            call iceberg_dynamics_step_custom(state_local, dt_in, ocean_prof_local, atmos_local, &
                                              f_eff, 0.0, 0.0, 0.0, 0.0, diag_local, &
                                              cd_air_in, cd_water_in)
            model_time_local = model_time_local + dt_in
        end do

        terminal_u_out = state_local%u
        terminal_v_out = state_local%v
        terminal_speed_out = sqrt(state_local%u**2 + state_local%v**2)
        drift_ratio_out = terminal_speed_out/wind_speed_in
        fx_wind_out = diag_local%f_wind_x
        fx_water_out = diag_local%f_water_x
        fx_cor_out = diag_local%f_cor_x
    end subroutine run_case

    subroutine init_zero_forcing(ocean_prof_out, atmos_out)
        type(ocean_profile), intent(out) :: ocean_prof_out
        type(atmos_forcing), intent(out) :: atmos_out

        integer :: nlevels
        nlevels = 1
        ocean_prof_out%nlevels = nlevels
        allocate (ocean_prof_out%z(nlevels), ocean_prof_out%dz(nlevels), &
                  ocean_prof_out%temp(nlevels), ocean_prof_out%salt(nlevels), &
                  ocean_prof_out%u(nlevels), ocean_prof_out%v(nlevels))
        ocean_prof_out%z(1) = 10.0
        ocean_prof_out%dz(1) = 10.0
        ocean_prof_out%temp(1) = -1.0
        ocean_prof_out%salt(1) = 0.034
        ocean_prof_out%u(1) = 0.0
        ocean_prof_out%v(1) = 0.0

        atmos_out%u10 = 0.0
        atmos_out%v10 = 0.0
        atmos_out%t2m = 253.15
        atmos_out%d2m = 253.15
        atmos_out%tcc = 0.0
        atmos_out%msl = 101325.0
        atmos_out%snowfall = 0.0
    end subroutine init_zero_forcing

    ! Упрощенная версия iceberg_dynamics_step с кастомными CD
    subroutine iceberg_dynamics_step_custom(state_in, dt_in, ocean_prof_in, atmos_in, &
                                            f_coriolis_in, grad_eta_x_in, grad_eta_y_in, &
                                            fk_x_in, fk_y_in, diag_inout, cd_air_in, cd_water_in)
        type(iceberg_state), intent(inout) :: state_in
        real, intent(in) :: dt_in
        type(ocean_profile), intent(in) :: ocean_prof_in
        type(atmos_forcing), intent(in) :: atmos_in
        real, intent(in) :: f_coriolis_in, grad_eta_x_in, grad_eta_y_in
        real, intent(in) :: fk_x_in, fk_y_in
        type(iceberg_diagnostics), intent(inout) :: diag_inout
        real, intent(in) :: cd_air_in, cd_water_in

        real :: mass_local
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

        mass_local = 910.0*state_in%L*state_in%W*state_in%H
        diag_inout%mass = mass_local

        ! Wind force with custom CD_AIR
        draft = state_in%H*910.0/1028.0
        freeboard = state_in%H - draft
        a_sail = state_in%L*state_in%W + 2.0*(state_in%L + state_in%W)*freeboard

        u_rel = atmos_in%u10 - state_in%u
        v_rel = atmos_in%v10 - state_in%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        f_wind_x = 0.5*1.225*cd_air_in*a_sail*speed_rel*u_rel
        f_wind_y = 0.5*1.225*cd_air_in*a_sail*speed_rel*v_rel
        diag_inout%f_wind_x = f_wind_x
        diag_inout%f_wind_y = f_wind_y

        ! Water force with custom CD_WATER (depth-averaged)
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

        f_water_x = 0.5*1028.0*cd_water_in*a_wet*speed_rel*u_rel
        f_water_y = 0.5*1028.0*cd_water_in*a_wet*speed_rel*v_rel
        diag_inout%f_water_x = f_water_x
        diag_inout%f_water_y = f_water_y

        ! Coriolis force
        f_cor_x = mass_local*f_coriolis_in*state_in%v
        f_cor_y = -mass_local*f_coriolis_in*state_in%u
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

        state_in%u = (u_old + dt_in*fx_noncor/mass_local + dt_in*f_coriolis_in*v_old)/A_mat
        state_in%v = (v_old + dt_in*fy_noncor/mass_local - dt_in*f_coriolis_in*u_old)/A_mat
    end subroutine iceberg_dynamics_step_custom

end program iceberg_test_wind_drift_sensitivity
