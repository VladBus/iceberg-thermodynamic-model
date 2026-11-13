! ==============================================================================
! Test: drift force balance with literature form/skin drag (Stage 12.17)
!
! Wind-only (100 m cube, no current, Coriolis ON): the model must reach
! ~1-3% of the wind, matching the continuous root of
!   F_wind = U sqrt((k_w U)^2 + (M f)^2),
! where k_w includes form drag on vertical sides and skin drag on the bottom.
!
! Current-only: the 50 m cube must reach >=90% of the current; the 100 m cube
! is compared with the exact 2D steady solution (about 85.6% for Cw=0.9).
! Without Coriolis the 100 m cube must approach the current.
!
! The test uses the prism path and synthetic cold forcing, with no external
! data and no file output.
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
    real, parameter :: LAT = 76.5, LON = 30.0, DT = 3600.0
    real(8) :: f_cor, mass, draft, freeboard, a_form, a_top, a_side, a_bottom
    real(8) :: f_wind, k_water, u_exact, u_model, ratio_wind, residual
    real(8) :: u_curr_exact, v_curr_exact, speed_curr_exact, speed_curr_model
    real(8) :: u_nocor
    real :: wind_speeds(2)
    integer :: i, nsteps, L

    n_errors = 0
    n_checks = 0

    if (voxel_geometry_active()) then
        print *, 'SKIP: VOXEL_ENABLED is active; this analytic test uses the prism path'
        stop 0
    end if

    f_cor = 2.0_8*real(OMEGA, 8)*sin(real(LAT, 8)/57.2957795_8)
    print *, '=================================================='
    print *, '  DRIFT FORCE BALANCE WITH FORM + SKIN DRAG (12.17)'
    print *, '=================================================='
    print '(a,f12.2,a,es12.4)', ' mass [kg] = ', RHO_ICE*1.0e6, '   f [1/s] = ', f_cor

    ! --- Wind-only, 100 m cube -------------------------------------------
    L = 100
    mass = real(RHO_ICE, 8)*real(L, 8)**3
    draft = real(L, 8)*real(RHO_ICE, 8)/real(RHO_WATER, 8)
    freeboard = real(L, 8) - draft
    a_form = real(L, 8)*freeboard
    a_top = real(L, 8)**2
    a_side = real(L, 8)*draft
    a_bottom = real(L, 8)**2
    k_water = 0.5_8*real(RHO_WATER, 8)*(real(CD_WATER_FORM, 8)*a_side + &
              real(CD_WATER_SKIN, 8)*a_bottom)
    wind_speeds = [7.0, 15.0]
    do i = 1, 2
        call make_ocean(ocean_prof, 0.0, 0.0)
        call make_atmos(atmos, wind_speeds(i), 0.0)
        call iceberg_init(state, 0.0, 0.0, real(L), real(L), real(L), LAT, LON, 0.0, 0.0)
        f_wind = 0.5_8*real(RHO_AIR, 8)*(real(CD_AIR_FORM, 8)*a_form + &
                 real(CD_AIR_SKIN, 8)*a_top)*real(wind_speeds(i), 8)**2
        u_exact = wind_equilibrium(f_wind, k_water, mass*f_cor)
        do nsteps = 1, 30*24
            call iceberg_dynamics_step(state, DT, ocean_prof, atmos, real(f_cor, 4), &
                                       0.0, 0.0, 0.0, 0.0, diag)
        end do
        u_model = sqrt(real(state%u, 8)**2 + real(state%v, 8)**2)
        ratio_wind = u_model/real(wind_speeds(i), 8)
        residual = abs(sqrt(real(diag%f_wind_x, 8)**2 + real(diag%f_wind_y, 8)**2) + &
                   sqrt(real(diag%f_water_x, 8)**2 + real(diag%f_water_y, 8)**2)*0.0_8 + &
                   real(diag%f_cor_x, 8)**2*0.0_8)
        print '(a,f6.1,a,f10.6,a,f10.6,a,f9.6)', ' wind ', wind_speeds(i), &
            ' m/s: model ', u_model, '  analytic ', u_exact, '  u/wind ', ratio_wind
        n_checks = n_checks + 1
        if (abs(u_model - u_exact) <= 0.05_8*max(u_exact, 1.0e-9)) then
            print *, ' OK: model matches the form/skin drag + Coriolis root'
        else
            print *, ' ERROR: model differs from analytic root by >5%'
            n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (ratio_wind >= 0.01_8 .and. ratio_wind <= 0.03_8) then
            print *, ' OK: wind drift is 1-3% of wind'
        else
            print *, ' ERROR: wind drift outside 1-3%'
            n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (force_residual(diag) <= 0.10*real(abs(diag%f_wind_x)+abs(diag%f_wind_y), 8)) then
            print *, ' OK: wind, water and Coriolis forces balance at steady state'
        else
            print *, ' ERROR: force budget does not balance'
            n_errors = n_errors + 1
        end if
    end do

    ! --- Current-only, 100 m cube (exact 2D steady solution) -------------
    call make_ocean(ocean_prof, 0.1, 0.0)
    call make_atmos(atmos, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, real(L), real(L), real(L), LAT, LON, 0.0, 0.0)
    call current_equilibrium(0.1_8, k_water, mass*f_cor, u_curr_exact, v_curr_exact)
    speed_curr_exact = sqrt(u_curr_exact**2 + v_curr_exact**2)
    do nsteps = 1, 30*24
        call iceberg_dynamics_step(state, DT, ocean_prof, atmos, real(f_cor, 4), &
                                   0.0, 0.0, 0.0, 0.0, diag)
    end do
    speed_curr_model = sqrt(real(state%u, 8)**2 + real(state%v, 8)**2)
    print '(a,f10.6,a,f10.6,a,f9.6)', ' current 0.1 m/s, 100 m: model ', &
        speed_curr_model, '  exact ', speed_curr_exact, '  u/U ', speed_curr_model/0.1_8
    n_checks = n_checks + 1
    if (abs(speed_curr_model - speed_curr_exact) <= 0.02_8*max(speed_curr_exact, 1.0e-9)) then
        print *, ' OK: 100 m current response matches the exact Coriolis-limited solution'
    else
        print *, ' ERROR: 100 m current response differs by >2%'
        n_errors = n_errors + 1
    end if

    ! --- Current-only, 50 m cube: >=90% of current -----------------------
    L = 50
    mass = real(RHO_ICE, 8)*real(L, 8)**3
    draft = real(L, 8)*real(RHO_ICE, 8)/real(RHO_WATER, 8)
    a_side = real(L, 8)*draft
    a_bottom = real(L, 8)**2
    k_water = 0.5_8*real(RHO_WATER, 8)*(real(CD_WATER_FORM, 8)*a_side + &
              real(CD_WATER_SKIN, 8)*a_bottom)
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, real(L), real(L), real(L), LAT, LON, 0.0, 0.0)
    call current_equilibrium(0.1_8, k_water, mass*f_cor, u_curr_exact, v_curr_exact)
    speed_curr_exact = sqrt(u_curr_exact**2 + v_curr_exact**2)
    do nsteps = 1, 30*24
        call iceberg_dynamics_step(state, DT, ocean_prof, atmos, real(f_cor, 4), &
                                   0.0, 0.0, 0.0, 0.0, diag)
    end do
    speed_curr_model = sqrt(real(state%u, 8)**2 + real(state%v, 8)**2)
    print '(a,f10.6,a,f10.6,a,f9.6)', ' current 0.1 m/s, 50 m: model ', &
        speed_curr_model, '  exact ', speed_curr_exact, '  u/U ', speed_curr_model/0.1_8
    n_checks = n_checks + 1
    if (speed_curr_model >= 0.90_8*0.1_8 .and. &
        abs(speed_curr_model - speed_curr_exact) <= 0.02_8*max(speed_curr_exact, 1.0e-9)) then
        print *, ' OK: 50 m cube reaches >=90% of the current'
    else
        print *, ' ERROR: 50 m current response is below 90% or off the exact value'
        n_errors = n_errors + 1
    end if

    ! --- Current-only, 100 m, no Coriolis --------------------------------
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 0.0, LON, 0.0, 0.0)
    do nsteps = 1, 60*24
        call iceberg_dynamics_step(state, DT, ocean_prof, atmos, 0.0, &
                                   0.0, 0.0, 0.0, 0.0, diag)
    end do
    u_nocor = sqrt(real(state%u, 8)**2 + real(state%v, 8)**2)
    print '(a,f10.6,a,f9.6)', ' current 0.1 m/s, no Coriolis, 60 d: model ', u_nocor, &
        '  u/U ', u_nocor/0.1_8
    n_checks = n_checks + 1
    if (u_nocor >= 0.95_8*0.1_8) then
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

    real(8) function wind_equilibrium(f0, k, mf) result(u)
        real(8), intent(in) :: f0, k, mf
        real(8) :: lo, hi, mid, fmid
        integer :: iter
        lo = 0.0_8; hi = 10.0_8
        do iter = 1, 100
            mid = 0.5_8*(lo + hi)
            fmid = mid*sqrt((k*mid)**2 + mf**2) - f0
            if (fmid > 0.0_8) then
                hi = mid
            else
                lo = mid
            end if
        end do
        u = 0.5_8*(lo + hi)
    end function wind_equilibrium

    subroutine current_equilibrium(uo, k, mf, u, v)
        real(8), intent(in) :: uo, k, mf
        real(8), intent(out) :: u, v
        real(8) :: x(2), f(2), jac(2,2), det, dx(2), wx, wy, w
        integer :: it
        x = [uo, 0.0_8]
        do it = 1, 80
            wx = x(1) - uo; wy = x(2); w = sqrt(wx**2 + wy**2)
            f(1) = -k*w*wx - mf*wy
            f(2) = -k*w*wy + mf*x(1)
            if (sqrt(f(1)**2 + f(2)**2) < 1.0e-9) exit
            jac(1,1) = -k*(w + wx*wx/max(w, 1.0e-12))
            jac(1,2) = -k*wx*wy/max(w, 1.0e-12) - mf
            jac(2,1) = -k*wy*wx/max(w, 1.0e-12) + mf
            jac(2,2) = -k*(w + wy*wy/max(w, 1.0e-12))
            det = jac(1,1)*jac(2,2) - jac(1,2)*jac(2,1)
            if (abs(det) < 1.0e-30) exit
            dx(1) = (-f(1)*jac(2,2) + f(2)*jac(1,2))/det
            dx(2) = (-f(2)*jac(1,1) + f(1)*jac(2,1))/det
            x = x + dx
        end do
        u = x(1); v = x(2)
    end subroutine current_equilibrium

    real(8) function force_residual(dg) result(r)
        type(iceberg_diagnostics), intent(in) :: dg
        real(8) :: fx, fy
        fx = real(dg%f_wind_x + dg%f_water_x + dg%f_cor_x + dg%f_pressure_x + dg%f_fk_x, 8)
        fy = real(dg%f_wind_y + dg%f_water_y + dg%f_cor_y + dg%f_pressure_y + dg%f_fk_y, 8)
        r = sqrt(fx*fx + fy*fy)
    end function force_residual

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
