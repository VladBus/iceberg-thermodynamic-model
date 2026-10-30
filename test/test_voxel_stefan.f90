! ==============================================================================
! Тест: test_voxel_stefan (Stage 12.4, PART B) — CI-safe, синтетика, без .nc.
! B-T1 single-face Stefan vs brute-force bisection; B-T2 PDF §6.2 worked example;
! B-T3 salinity-unit guard; B-T4 pressure; B-T5 u_rel scaling + co-moving;
! B-T6 stratified profile; B-T7 no accretion; B-T8 integration + mass budget.
! ==============================================================================
program test_voxel_stefan
    use iceberg_types, only: ocean_profile, ocean_freezing_point, &
                             RHO_ICE, RHO_WATER, C_ICE, LATENT_HEAT, CP_SEAWATER, &
                             K_ICE, THREE_EQ_KT, THREE_EQ_KS
    use voxel_thermal_solver, only: three_equation_melt, profile_at
    use voxel_iceberg, only: voxel_iceberg_type, voxel_iceberg_init, &
                             voxel_iceberg_step_profile, voxel_iceberg_get_mass, &
                             voxel_iceberg_get_draft, voxel_iceberg_get_melt, &
                             voxel_iceberg_get_flush, voxel_iceberg_get_stefan
    implicit none

    real(8), parameter :: RW = 1028.0d0, RI = 910.0d0, CW = 3974.0d0
    real(8), parameter :: LF = 334000.0d0, KI = 2.2d0, KT = 1.1d-3, KS = 3.1d-5
    integer :: nerr

    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.4 — THREE-EQUATION STEFAN TESTS (PART B)'
    print *, '===================================================='

    call test_B1()
    call test_B2()
    call test_B3()
    call test_B4()
    call test_B5()
    call test_B6()
    call test_B7()
    call test_B8()

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: THREE-EQUATION STEFAN TESTS PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: THREE-EQUATION STEFAN TESTS FAILED, errors=', nerr
        stop 1
    end if

contains

    real(8) function f_ref(m, tw, sw, urel, depth, hn, tv) result(f)
        real(8), intent(in) :: m, tw, sw, urel, depth, hn, tv
        real(8) :: gt, gs, sb, tb
        gt = KT*urel; gs = KS*urel
        sb = RW*gs*sw/(RW*gs + RI*m)
        tb = real(ocean_freezing_point(real(sb,4), real(depth,4)), 8)
        f = RW*CW*gt*(tw - tb) - RI*LF*m - (2.0d0*KI/hn)*(tb - tv)
    end function f_ref

    ! --- B-T1: single-face vs brute-force bisection ------------------------
    subroutine test_B1()
        real(8) :: m, tb, sb, tw, sw, urel, depth, hn, tv
        real(8) :: lo, hi, mid, f0, fm, ref
        integer :: it
        logical :: ok
        tw = 2.0d0; sw = 0.035d0; urel = 0.1d0; depth = 20.0d0; hn = 1.0d0; tv = -10.0d0
        call three_equation_melt(tw, sw, urel, depth, hn, tv, m, tb, sb, ok)
        print '(a,f12.6,a,f10.6,a,f10.6)', ' B-T1 m=', m, ' SB=', sb, ' TB=', tb
        if (.not. ok) then
            print *, '  FAIL: solver returned ok=false'; nerr = nerr + 1; return
        end if
        ! brute-force reference: 200 bisection iterations on [0, 1e-3]
        lo = 0.0d0; hi = 1.0d-3
        f0 = f_ref(0.0d0, tw, sw, urel, depth, hn, tv)
        if (f0 <= 0.0d0) then
            ref = 0.0d0
        else
            do it = 1, 200
                mid = 0.5d0*(lo + hi)
                if (f_ref(mid, tw, sw, urel, depth, hn, tv) > 0.0d0) then
                    lo = mid
                else
                    hi = mid
                end if
            end do
            ref = 0.5d0*(lo + hi)
        end if
        print '(a,es14.6,a,es14.6)', '      m_ref=', ref, ' diff=', abs(m - ref)
        if (abs(m - ref) > 1.0d-10) then
            print *, '  FAIL: m != brute-force reference (1e-10)'; nerr = nerr + 1
        else
            print *, '  OK: matches brute-force bisection to 1e-10'
        end if
        if (sb < sw) then
            print *, '  OK: SB < Sw'
        else
            print *, '  FAIL: SB >= Sw'; nerr = nerr + 1
        end if
        if (tb > real(ocean_freezing_point(real(sw,4), real(depth,4)), 8) .and. tb < 0.0d0) then
            print *, '  OK: Tf(Sw,P) < TB < 0'
        else
            print *, '  FAIL: TB not in (Tf(Sw,P), 0)'; nerr = nerr + 1
        end if
    end subroutine test_B1

    ! --- B-T2: PDF §6.2 worked example within 20% --------------------------
    subroutine test_B2()
        real(8) :: tw, sw, urel, depth, hn, tv, m, tb, sb, m_ref
        logical :: ok
        sw = 0.035d0; depth = 0.0d0; hn = 0.5d0; tv = -10.0d0; urel = 0.1d0
        tw = real(ocean_freezing_point(real(sw,4), 0.0), 8) + 3.0d0   ! Tw - Tf = 3 K
        call three_equation_melt(tw, sw, urel, depth, hn, tv, m, tb, sb, ok)
        m_ref = 0.25d0/86400.0d0    ! 0.25 m/day
        print '(a,f12.6,a,f10.6,a,f10.6)', ' B-T2 m=', m, ' SB=', sb, ' TB=', tb
        print '(a,f12.6,a,f8.4)', '      m_ref(0.25 m/day)=', m_ref, ' ratio=', m/m_ref
        if (.not. ok .or. m/m_ref < 0.8d0 .or. m/m_ref > 1.2d0) then
            print *, '  FAIL: m outside 20% of PDF §6.2 example'; nerr = nerr + 1
        else
            print *, '  OK: m within 20% of 0.25 m/day'
        end if
        if (sb*1000.0d0 < 0.8d0*19.0d0 .or. sb*1000.0d0 > 1.2d0*19.0d0) then
            print *, '  FAIL: SB outside 20% of ~19 PSU'; nerr = nerr + 1
        else
            print *, '  OK: SB ~ 19 PSU (20%)'
        end if
        if (tb < -1.04d0*1.2d0 .or. tb > -1.04d0*0.8d0) then
            print *, '  FAIL: TB outside 20% of ~-1.04 C'; nerr = nerr + 1
        else
            print *, '  OK: TB ~ -1.04 C (20%)'
        end if
    end subroutine test_B2

    ! --- B-T3: salinity-unit guard -----------------------------------------
    subroutine test_B3()
        real(8) :: tf_ok, tf_wrong
        tf_ok = real(ocean_freezing_point(0.035, 0.0), 8)
        tf_wrong = real(ocean_freezing_point(0.000035, 0.0), 8)   ! kg/kg fed as if PSU
        print '(a,f10.5,a,f10.5)', ' B-T3 Tf(35 PSU)=', tf_ok, ' Tf(0.035 PSU)=', tf_wrong
        if (abs(tf_ok - (-1.922d0)) > 1.0d-3) then
            print *, '  FAIL: Tf(35 PSU) != -1.922'; nerr = nerr + 1
        else
            print *, '  OK: correct Tf ~ -1.922 C'
        end if
        if (abs(tf_wrong) > 0.05d0) then
            print *, '  FAIL: wrong units not detected'; nerr = nerr + 1
        else
            print *, '  OK: kg/kg-as-PSU gives |Tf|<0.05 (order-of-magnitude guard)'
        end if
    end subroutine test_B3

    ! --- B-T4: pressure correction -----------------------------------------
    subroutine test_B4()
        real(8) :: d, m1, m300, tb1, tb300, sb1, sb300, sw, tw, urel, hn, tv
        logical :: ok
        d = real(ocean_freezing_point(0.035, 300.0), 8) - &
            real(ocean_freezing_point(0.035, 0.0), 8)
        print '(a,f10.5)', ' B-T4 dTf(300 m) = ', d
        if (abs(d - (-0.226d0)) > 5.0d-3) then
            print *, '  FAIL: dTf(300m) != -0.226 +/- 0.005'; nerr = nerr + 1
        else
            print *, '  OK: pressure correction -0.226 C'
        end if
        sw = 0.035d0; tw = 2.0d0; urel = 0.1d0; hn = 1.0d0; tv = -10.0d0
        call three_equation_melt(tw, sw, urel, 1.0d0, hn, tv, m1, tb1, sb1, ok)
        call three_equation_melt(tw, sw, urel, 300.0d0, hn, tv, m300, tb300, sb300, ok)
        print '(a,es12.4,a,es12.4)', '      m(1m)=', m1, ' m(300m)=', m300
        ! PDF eq 8.1: Tf falls with P -> stronger thermal forcing -> MORE melt.
        ! (The prompt's "melt decreases with depth" contradicts eq 8.1; doc wins.)
        if (m300 > m1) then
            print *, '  OK: melt increases with depth for identical Tw (Tf falls with P)'
        else
            print *, '  FAIL: expected m300 > m1 (PDF eq 8.1)'; nerr = nerr + 1
        end if
    end subroutine test_B4

    ! --- B-T5: u_rel scaling + co-moving ------------------------------------
    subroutine test_B5()
        real(8) :: sw, tw, depth, hn, tv, m1, m2, ratio, tb, sb
        logical :: ok
        sw = 0.035d0; tw = 2.0d0; depth = 20.0d0; hn = 1.0d0; tv = -10.0d0
        call three_equation_melt(tw, sw, 0.1d0, depth, hn, tv, m1, tb, sb, ok)
        call three_equation_melt(tw, sw, 0.2d0, depth, hn, tv, m2, tb, sb, ok)
        ratio = m2/m1
        print '(a,f8.3)', ' B-T5 m(0.2)/m(0.1) = ', ratio
        if (ratio < 1.3d0 .or. ratio > 2.5d0) then
            print *, '  FAIL: u_rel scaling ratio outside [1.3,2.5]'; nerr = nerr + 1
        else
            print *, '  OK: melt scales with u_rel'
        end if
        call three_equation_melt(tw, sw, 0.0d0, depth, hn, tv, m1, tb, sb, ok)
        if (m1 == 0.0d0) then
            print *, '  OK: co-moving (u_rel=0) -> m=0'
        else
            print *, '  FAIL: u_rel=0 should give m=0'; nerr = nerr + 1
        end if
    end subroutine test_B5

    ! --- B-T6: stratified profile ------------------------------------------
    subroutine test_B6()
        type(ocean_profile) :: prof
        real(8) :: tw, sw, uw, vw, mtop, mdeep, t, s, u, v, tb, sb
        logical :: ok
        prof%nlevels = 5
        allocate (prof%z(5), prof%dz(5), prof%temp(5), prof%salt(5), prof%u(5), prof%v(5), &
                  prof%u_rel(5))
        prof%z = (/ 1.0, 10.0, 50.0, 100.0, 300.0 /)
        prof%dz = 10.0
        prof%temp = (/ 2.0, 1.5, 0.0, -0.7, -1.5 /)
        prof%salt = 0.035
        prof%u = 0.1; prof%v = 0.0; prof%u_rel = 0.1
        call profile_at(prof, 10.0d0, t, s, u, v)
        call three_equation_melt(t, s, 0.1d0, 10.0d0, 1.0d0, -5.0d0, mtop, tb, sb, ok)
        call profile_at(prof, 250.0d0, t, s, u, v)
        call three_equation_melt(t, s, 0.1d0, 250.0d0, 1.0d0, -5.0d0, mdeep, tb, sb, ok)
        print '(a,es12.4,a,es12.4)', ' B-T6 m_top=', mtop, ' m_deep=', mdeep
        if (mtop > 3.0d0*mdeep) then
            print *, '  OK: top submerged voxel melts > 3x deeper (profile used)'
        else
            print *, '  FAIL: stratified profile not reflected'; nerr = nerr + 1
        end if
    end subroutine test_B6

    ! --- B-T7: no accretion (Tw below local Tf) ----------------------------
    subroutine test_B7()
        real(8) :: m, tb, sb, tf
        logical :: ok
        tf = real(ocean_freezing_point(0.035, 20.0), 8)
        call three_equation_melt(tf - 1.0d0, 0.035d0, 0.1d0, 20.0d0, 1.0d0, &
                                 -10.0d0, m, tb, sb, ok)
        print '(a,es12.4)', ' B-T7 sub-Tf m = ', m
        if (ok .and. abs(m) < 1.0d-15) then
            print *, '  OK: no accretion (m=0, spec A5)'
        else
            print *, '  FAIL: sub-Tf should give m=0'; nerr = nerr + 1
        end if
    end subroutine test_B7

    ! --- B-T8: integration + mass budget -----------------------------------
    subroutine test_B8()
        type(voxel_iceberg_type) :: vox
        type(ocean_profile) :: prof
        real(8) :: dt, m0, m1, d0, d1, basal, lat, surf, mb, sum_melt, fmass, fenergy
        real(8) :: mtb, msb, murel, dtb, wtb
        real(8) :: best, worst
        integer :: it, nfaces, cg, clips, rl
        logical :: ok
        dt = 3600.0d0
        prof%nlevels = 5
        allocate (prof%z(5), prof%dz(5), prof%temp(5), prof%salt(5), prof%u(5), prof%v(5), &
                  prof%u_rel(5))
        prof%z = (/ 1.0, 10.0, 50.0, 100.0, 300.0 /)
        prof%dz = 10.0
        prof%temp = (/ 2.0, 1.5, 0.0, -0.7, -1.5 /)
        prof%salt = 0.035
        prof%u = 0.1; prof%v = 0.0; prof%u_rel = 0.1

        call voxel_iceberg_init(vox, 8, 8, 8, 10.0d0, 10.0d0, 10.0d0, -5.0d0, 1.0d0)
        m0 = vox%total_mass; d0 = vox%draft
        sum_melt = 0.0d0
        do it = 1, 24
            call voxel_iceberg_step_profile(vox, dt, prof, 0.0d0, 0.0d0, &
                                            -5.0d0, 0.0d0, 5.0d0, basal, lat, surf)
            sum_melt = sum_melt + (basal + lat + surf)*dt
        end do
        m1 = vox%total_mass; d1 = vox%draft
        call voxel_iceberg_get_flush(vox, fmass, fenergy)
        call voxel_iceberg_get_stefan(vox, mtb, msb, murel, dtb, wtb, nfaces)
        print '(a,es14.6,a,es14.6)', ' B-T8 mass ', m0, ' -> ', m1
        print '(a,f8.2,a,f8.2)', '      draft ', d0, ' -> ', d1
        print '(a,es12.4,a,es12.4,a,i0)', '      sum_melt=', sum_melt, ' flushed=', fmass, &
            ' faces=', nfaces
        print '(a,f9.5,a,f9.6,a,f9.4)', '      mean TB=', mtb, ' SB=', msb, ' urel=', murel
        if (any(vox%phi /= vox%phi) .or. any(vox%T /= vox%T)) then
            print *, '  FAIL: NaN'; nerr = nerr + 1
        else if (any(vox%phi < -1.0d-9) .or. any(vox%phi > 1.0d0 + 1.0d-9)) then
            print *, '  FAIL: phi out of [0,1]'; nerr = nerr + 1
        else if (.not. (m1 < m0 .and. d1 < d0)) then
            print *, '  FAIL: no melt'; nerr = nerr + 1
        else
            print *, '  OK: no NaN, phi in range, mass & draft decrease'
        end if
        ! mass budget: dM = sum(melt rates)*dt + flushed mass
        best = abs((m0 - m1) - sum_melt - fmass)/m0
        print '(a,es12.4)', '      mass-budget rel = ', best
        if (best > 1.0d-6) then
            print *, '  FAIL: mass budget > 1e-6'; nerr = nerr + 1
        else
            print *, '  OK: mass budget closes (<1e-6)'
        end if
    end subroutine test_B8

end program test_voxel_stefan
