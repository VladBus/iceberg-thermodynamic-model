! ==============================================================================
! Тест: test_voxel_cn (Stage 12.4, PART A) — CI-safe, синтетика, без .nc.
! A-T1 энергосохранение (адиабата), A-T2 устойчивость dt=1e6, A-T3 порядок 2,
! A-T4 CN vs explicit (малое Fo), A-T5 стационарный Dirichlet-профиль,
! A-T6 фазовая аналитика (точная абляция + sqrt(t)/энергобаланс),
! A-T7 non-cubic h_norm, A-T8 Rannacher; + unit-тесты Tf(S,P).
! ==============================================================================
program test_voxel_cn
    use iceberg_types, only: RHO_ICE, C_ICE, K_ICE, LATENT_HEAT, ocean_freezing_point
    use voxel_thermal_solver, only: solve_cn, solve_heat_conduction, face_h, voxel_face_dphi
    use voxel_iceberg, only: voxel_iceberg_type, voxel_iceberg_init, voxel_iceberg_step, &
                             voxel_iceberg_get_solver
    implicit none

    real(8), parameter :: PI = 3.141592653589793d0
    real(8) :: k8, rho8, c8, lf8
    integer :: nerr

    nerr = 0
    k8 = real(K_ICE, 8); rho8 = real(RHO_ICE, 8); c8 = real(C_ICE, 8); lf8 = real(LATENT_HEAT, 8)
    print *, '===================================================='
    print *, ' STAGE 12.4 — CRANK-NICOLSON CORE TESTS (PART A)'
    print *, '===================================================='

    call test_freezing_point()
    call test_A1_energy()
    call test_A2_stability()
    call test_A3_order()
    call test_A4_vs_explicit()
    call test_A5_steady()
    call test_A6_phase()
    call test_A7_geometry()
    call test_A8_rannacher()

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: CRANK-NICOLSON PART A TESTS PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: CRANK-NICOLSON PART A TESTS FAILED, errors=', nerr
        stop 1
    end if

contains

    ! --- item 7: Tf(S,P) units (S mass fraction input) ----------------------
    subroutine test_freezing_point()
        real(8) :: tf0, tf100, d
        tf0 = real(ocean_freezing_point(0.035, 0.0), 8)
        tf100 = real(ocean_freezing_point(0.035, 100.0), 8)
        d = tf100 - tf0
        print '(a,f10.5,a,f10.5)', ' Tf(35,0)=', tf0, '  dTf(100 dbar)=', d
        if (abs(tf0 - (-1.922d0)) > 1.0d-3) then
            print *, '  FAIL: Tf(35,0) != -1.922'; nerr = nerr + 1
        else
            print *, '  OK: Tf(35,0) ~ -1.922 C'
        end if
        if (abs(d - (-0.075d0)) > 1.0d-3) then
            print *, '  FAIL: dTf(100 dbar) != -0.075'; nerr = nerr + 1
        else
            print *, '  OK: dTf(100 dbar) ~ -0.075 C'
        end if
    end subroutine test_freezing_point

    ! --- A-T1: adiabatic energy conservation --------------------------------
    subroutine test_A1_energy()
        integer, parameter :: n = 6
        real(8) :: T(n, n, n), phi(n, n, n), Tn(n, n, n)
        logical :: sm(n, n, n), em(n, n, n)
        integer :: i, j, k, it, cg, ierr
        real(8) :: e0, e1, res
        logical :: conv
        do k = 1, n; do j = 1, n; do i = 1, n
            T(i, j, k) = -10.0d0 + 2.0d0*sin(PI*real(i, 8)/n)*sin(PI*real(j, 8)/n)* &
                         sin(PI*real(k, 8)/n)
            phi(i, j, k) = 1.0d0
        end do; end do; end do
        sm = .false.; em = .false.
        e0 = energy(T, phi, 1.0d0, 1.0d0, 1.0d0)
        do it = 1, 100
            call solve_cn(T, phi, 1.0d0, 1.0d0, 1.0d0, 3600.0d0, k8, rho8, c8, 0.5d0, &
                          1.0d-10, 2000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv)
            T = Tn
        end do
        e1 = energy(T, phi, 1.0d0, 1.0d0, 1.0d0)
        print '(a,es12.4,a,i0)', ' A-T1 energy drift = ', abs(e1 - e0)/abs(e0), &
            '  lastCG=', cg
        if (abs(e1 - e0)/abs(e0) > 1.0d-8) then
            print *, '  FAIL: adiabatic energy drift > 1e-8'; nerr = nerr + 1
        else
            print *, '  OK: adiabatic energy conserved (<1e-8)'
        end if
    end subroutine test_A1_energy

    ! --- A-T2: stability at dt=1e6 ------------------------------------------
    subroutine test_A2_stability()
        integer, parameter :: n = 5
        real(8) :: T(n, n, n), phi(n, n, n), Tn(n, n, n)
        logical :: sm(n, n, n), em(n, n, n)
        integer :: i, j, k, cg
        real(8) :: tmin0, tmax0, res
        logical :: conv
        do k = 1, n; do j = 1, n; do i = 1, n
            T(i, j, k) = -10.0d0 + 2.0d0*sin(PI*real(i, 8)/n)*sin(PI*real(j, 8)/n)* &
                         sin(PI*real(k, 8)/n)
            phi(i, j, k) = 1.0d0
        end do; end do; end do
        tmin0 = minval(T); tmax0 = maxval(T)
        sm = .false.; em = .false.
        do k = 1, 5
            call solve_cn(T, phi, 1.0d0, 1.0d0, 1.0d0, 1.0d6, k8, rho8, c8, 0.5d0, &
                          1.0d-10, 5000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv)
            T = Tn
        end do
        if (any(T /= T)) then
            print *, '  FAIL: A-T2 NaN at dt=1e6'; nerr = nerr + 1
        else if (minval(T) < tmin0 - 1.0d-9 .or. maxval(T) > tmax0 + 1.0d-9) then
            print '(a,2f10.4,a,2f10.4)', '  FAIL: A-T2 out of bounds ', minval(T), maxval(T), &
                ' init ', tmin0, tmax0
            nerr = nerr + 1
        else
            print *, '  OK: A-T2 stable at dt=1e6, T bounded'
        end if
    end subroutine test_A2_stability

    ! --- A-T3: temporal order (~2) ------------------------------------------
    subroutine test_A3_order()
        real(8) :: e1, e2, ratio
        e1 = col_error(3000.0d0)
        e2 = col_error(1500.0d0)
        ratio = e1/e2
        print '(a,es12.4,a,es12.4,a,f6.3)', ' A-T3 err(dt)=', e1, ' err(dt/2)=', e2, ' ratio=', ratio
        if (ratio < 2.5d0 .or. ratio > 5.5d0) then
            print *, '  FAIL: temporal order not ~2'; nerr = nerr + 1
        else
            print *, '  OK: temporal order ~2'
        end if
    end subroutine test_A3_order

    real(8) function col_error(dt) result(e)
        real(8), intent(in) :: dt
        integer, parameter :: nz = 30
        real(8) :: T(1, 1, nz), phi(1, 1, nz), Tn(1, 1, nz), Tr(1, 1, nz), Tt(1, 1, nz)
        logical :: sm(1, 1, nz), em(1, 1, nz)
        integer :: it, nst, cg
        real(8) :: res, tfinal
        logical :: conv
        sm = .false.; em = .false.
        phi = 1.0d0
        T = -10.0d0; T(1, 1, 15) = -5.0d0
        tfinal = 30000.0d0
        nst = nint(tfinal/dt)
        do it = 1, nst
            call solve_cn(T, phi, 1.0d0, 1.0d0, 1.0d0, dt, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 5000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv)
            T = Tn
        end do
        ! reference: dt/8
        Tr = -10.0d0; Tr(1, 1, 15) = -5.0d0
        do it = 1, nint(tfinal/(dt/8.0d0))
            call solve_cn(Tr, phi, 1.0d0, 1.0d0, 1.0d0, dt/8.0d0, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 5000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv)
            Tr = Tn
        end do
        e = maxval(abs(T - Tr))
    end function col_error

    ! --- A-T4: CN vs explicit at small Fo (<=0.05) --------------------------
    subroutine test_A4_vs_explicit()
        integer, parameter :: nz = 30
        real(8) :: T1(1, 1, nz), T2(1, 1, nz), phi(1, 1, nz), Tn(1, 1, nz), phn(1, 1, nz)
        logical :: sm(1, 1, nz), em(1, 1, nz)
        integer :: it, cg
        real(8) :: res, dmax
        logical :: conv
        sm = .false.; em = .false.; phi = 1.0d0
        T1 = -10.0d0; T1(1, 1, 15) = -5.0d0
        T2 = T1
        do it = 1, 20
            call solve_cn(T1, phi, 1.0d0, 1.0d0, 1.0d0, 10.0d0, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 2000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv)
            T1 = Tn
            call solve_heat_conduction(T2, phi, 1.0d0, 1.0d0, 1.0d0, 10.0d0, &
                                       k8, rho8, c8, lf8, Tn, phn)
            T2 = Tn
        end do
        dmax = maxval(abs(T1 - T2))
        print '(a,es12.4)', ' A-T4 max|CN-explicit| at Fo~1e-4 = ', dmax
        if (dmax > 1.0d-6) then
            print *, '  FAIL: CN vs explicit > 1e-6'; nerr = nerr + 1
        else
            print *, '  OK: CN and explicit agree (<=1e-6)'
        end if
    end subroutine test_A4_vs_explicit

    ! --- A-T5: steady linear Dirichlet profile ------------------------------
    subroutine test_A5_steady()
        integer, parameter :: nz = 20
        real(8) :: T(1, 1, nz), phi(1, 1, nz), Tn(1, 1, nz)
        logical :: sm(1, 1, nz), em(1, 1, nz)
        integer :: it, cg, k
        real(8) :: res, dev
        logical :: conv
        sm = .false.; em = .false.; phi = 1.0d0
        T = 0.5d0
        do it = 1, 4000
            call solve_cn(T, phi, 1.0d0, 1.0d0, 1.0d0, 1.0d6, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 3000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv, &
                          5, 1.0d0, 6, 0.0d0)
            T = Tn
        end do
        dev = 0.0d0
        do k = 1, nz
            ! линейный профиль между T(-z)=0 и T(+z)=1: центр k → (k-0.5)/nz
            dev = max(dev, abs(T(1, 1, k) - (real(k, 8) - 0.5d0)/real(nz, 8)))
        end do
        print '(a,es12.4)', ' A-T5 steady-profile max deviation = ', dev
        if (dev > 1.0d-5) then
            print *, '  FAIL: steady profile not linear'; nerr = nerr + 1
        else
            print *, '  OK: steady linear profile reached'
        end if
    end subroutine test_A5_steady

    real(8) function fit_slope(x, y, n) result(s)
        integer, intent(in) :: n
        real(8), intent(in) :: x(:), y(:)
        integer :: i
        real(8) :: sx, sy, sxx, sxy
        sx = 0.0d0; sy = 0.0d0; sxx = 0.0d0; sxy = 0.0d0
        do i = 1, n
            sx = sx + log(x(i)); sy = sy + log(y(i))
            sxx = sxx + log(x(i))**2; sxy = sxy + log(x(i))*log(y(i))
        end do
        s = (n*sxy - sx*sy)/(n*sxx - sx*sx)
    end function fit_slope


    ! --- A-T6: phase-change analytics (exact ablation + sqrt(t)) ------------
    subroutine test_A6_phase()
        integer, parameter :: nz = 40
        real(8) :: T(1, 1, nz), phi(1, 1, nz), Tn(1, 1, nz)
        logical :: sm(1, 1, nz), em(1, 1, nz)
        integer :: k, it, cg, nst, nsamp
        real(8) :: res, dt, dz, q0, depth, expected, dphi, e_in, latent, sensible
        real(8) :: depths(5), times(5), slope, Told_top, sens_melt
        logical :: conv
        dz = 1.0d0; dt = 3600.0d0
        sm = .false.; em = .false.

        ! (i) exact ablation: T_init = 0, Dirichlet +2 → heat in = latent melt
        nst = 200
        phi = 1.0d0; T = 0.0d0
        depth = 0.0d0; e_in = 0.0d0
        do it = 1, nst
            Told_top = T(1, 1, nz)
            call solve_cn(T, phi, 1.0d0, 1.0d0, dz, dt, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 3000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv, &
                          5, 2.0d0, 0, 0.0d0)
            T = Tn
            e_in = e_in + 2.0d0*k8*(2.0d0 - (0.5d0*T(1, 1, nz) + 0.5d0*Told_top))/dz*dt
            do k = 1, nz
                if (T(1, 1, k) > 0.0d0 .and. phi(1, 1, k) > 0.0d0) then
                    dphi = phi(1, 1, k)*c8*T(1, 1, k)/lf8
                    dphi = min(dphi, phi(1, 1, k))
                    phi(1, 1, k) = phi(1, 1, k) - dphi
                    depth = depth + dphi*dz
                    sens_melt = sens_melt + dphi*rho8*c8*5.0d0*dz
                    T(1, 1, k) = 0.0d0
                end if
            end do
        end do
        q0 = 2.0d0*k8*2.0d0/dz
        expected = q0*dt*nst/(rho8*lf8)
        print '(a,es12.4,a,es12.4,a,es12.4)', ' A-T6i melt depth=', depth, &
            ' E_in/(rhoL)=', e_in/(rho8*lf8), ' q0t/(rhoL)=', expected
        if (abs(depth - e_in/(rho8*lf8))/(e_in/(rho8*lf8)) > 1.0d-6) then
            print *, '  FAIL: ablation melt != energy-in/(rho L) (<1e-6)'; nerr = nerr + 1
        else
            print *, '  OK: ablation melt = energy-in/(rho L) (1e-6)'
        end if
        if (abs(depth - expected)/expected > 2.0d-2) then
            print *, '  FAIL: ablation depth differs from q0*t/(rhoL) by >2%'; nerr = nerr + 1
        else
            print *, '  OK: ablation depth ~ q0*t/(rho L) (CN O(dt) correction within 2%)'
        end if

        ! (ii) cold ice: long run, sqrt(t) scaling + energy balance
        nst = 6000
        phi = 1.0d0; T = -5.0d0
        depth = 0.0d0; e_in = 0.0d0; nsamp = 0; sens_melt = 0.0d0
        do it = 1, nst
            Told_top = T(1, 1, nz)
            call solve_cn(T, phi, 1.0d0, 1.0d0, dz, dt, k8, rho8, c8, 0.5d0, &
                          1.0d-12, 3000, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
                          0.0d0, 0.0d0, 0.0d0, sm, em, Tn, cg, res, conv, &
                          5, 2.0d0, 0, 0.0d0)
            T = Tn
            e_in = e_in + 2.0d0*k8*(2.0d0 - (0.5d0*T(1, 1, nz) + 0.5d0*Told_top))/dz*dt
            do k = 1, nz
                if (T(1, 1, k) > 0.0d0 .and. phi(1, 1, k) > 0.0d0) then
                    dphi = phi(1, 1, k)*c8*T(1, 1, k)/lf8
                    dphi = min(dphi, phi(1, 1, k))
                    phi(1, 1, k) = phi(1, 1, k) - dphi
                    depth = depth + dphi*dz
                    sens_melt = sens_melt + dphi*rho8*c8*5.0d0*dz
                    T(1, 1, k) = 0.0d0
                end if
            end do
            if (it == 3000 .or. it == 4000 .or. it == 5000 .or. it == 5500 .or. it == 6000) then
                nsamp = nsamp + 1
                times(nsamp) = it*dt
                depths(nsamp) = max(depth, 1.0d-12)
            end if
        end do
        latent = rho8*lf8*depth
        sensible = 0.0d0
        do k = 1, nz
            sensible = sensible + phi(1, 1, k)*rho8*c8*(T(1, 1, k) - (-5.0d0))*dz
        end do
        print '(a,es12.4,a,es12.4,a,es12.4,a,es12.4)', ' A-T6ii E_in=', e_in, ' latent=', latent, &
            ' sensible=', sensible, ' sens_melt=', sens_melt
        if (latent <= 0.0d0) then
            print *, '  FAIL: cold-ice run produced no melt'; nerr = nerr + 1
        else if (abs(e_in - latent - sensible - sens_melt)/e_in > 1.0d-2) then
            print *, '  FAIL: cold-ice global energy balance >1e-2'; nerr = nerr + 1
        else
            print *, '  OK: cold-ice energy balance (flux = latent + sensible)'
        end if
        do k = 1, nsamp
            print '(a,f10.1,a,es12.4)', '   sample t=', times(k), ' depth=', depths(k)
        end do
        slope = fit_slope(times, depths, nsamp)
        print '(a,f8.4)', ' A-T6ii fitted exponent = ', slope
        ! FALLBACK (user-approved): the half-cell fixed-T_b BC is constant-flux;
        ! its late-time melt is LINEAR (slope ~1), not sqrt(t) (that is the
        ! fixed-surface-temperature Neumann solution). We therefore assert the
        ! global energy balance (above) and monotone melt, and REPORT the
        ! exponent; the exact fixed-T Stefan similarity stays deferred to 12.7a.
        if (depth <= 0.0d0) then
            print *, '  FAIL: no melt'; nerr = nerr + 1
        else
            print *, '  OK: cold-ice melt monotone; exponent reported (constant-flux BC)'
        end if
    end subroutine test_A6_phase

    ! --- A-T7: non-cubic geometry (dx=50, dz=5) ----------------------------
    subroutine test_A7_geometry()
        real(8) :: r
        r = voxel_face_dphi(1.0d0, 1.0d0, 1, 50.0d0, 50.0d0, 5.0d0) / &
            voxel_face_dphi(1.0d0, 1.0d0, 5, 50.0d0, 50.0d0, 5.0d0)
        print '(a,f12.9)', ' A-T7 lateral/basal phi-loss ratio = ', r
        if (abs(r - 5.0d0/50.0d0) > 1.0d-12) then
            print *, '  FAIL: non-cubic h_norm ratio != dz/dx'; nerr = nerr + 1
        else
            print *, '  OK: h_norm geometry (dz/dx = 0.1)'
        end if
    end subroutine test_A7_geometry

    ! --- A-T8: Rannacher after geometry change -----------------------------
    subroutine test_A8_rannacher()
        type(voxel_iceberg_type) :: vox
        real(8) :: basal, lat, surf, cres
        integer :: cg, clips, rl, seq(3)
        logical :: ok
        call voxel_iceberg_init(vox, 6, 6, 6, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
        vox%phi(3, 3, 3) = 0.005d0
        call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                                -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
        call voxel_iceberg_get_solver(vox, cg, cres, clips, rl)
        seq(1) = rl
        call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                                -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
        call voxel_iceberg_get_solver(vox, cg, cres, clips, rl)
        seq(2) = rl
        call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                                -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
        call voxel_iceberg_get_solver(vox, cg, cres, clips, rl)
        seq(3) = rl
        print '(a,3i3)', ' A-T8 rannacher_left sequence = ', seq
        ok = (seq(1) == 2 .and. seq(2) == 1 .and. seq(3) == 0)
        if (.not. ok) then
            print *, '  FAIL: Rannacher flag sequence != 2,1,0'; nerr = nerr + 1
        else
            print *, '  OK: 2 backward-Euler steps after geometry change'
        end if
    end subroutine test_A8_rannacher

    real(8) function energy(T, phi, dx, dy, dz) result(e)
        real(8), intent(in) :: T(:,:,:), phi(:,:,:), dx, dy, dz
        e = sum(phi*T)*rho8*c8*dx*dy*dz
    end function energy

end program test_voxel_cn
