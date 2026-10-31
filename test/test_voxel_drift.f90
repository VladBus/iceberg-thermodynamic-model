! ==============================================================================
! Тест: test_voxel_drift (Stage 12.5) — CI-safe, синтетика, без .nc.
! Проверяет проекционную фронтальную площадь (PDF 13.2), уменьшение при
! таянии, интеграцию с профилем, метацентрическую устойчивость и gated-
! интерфейс воксельной геометрии для дрейфа.
! ==============================================================================
program test_voxel_drift
    use iceberg_types, only: ocean_profile
    use voxel_iceberg, only: voxel_iceberg_type, voxel_iceberg_init, &
                             voxel_iceberg_step_profile, voxel_iceberg_get_mass, &
                             voxel_iceberg_get_draft, voxel_iceberg_get_areas, &
                             voxel_iceberg_get_frontal_area, voxel_iceberg_get_stability, &
                             voxel_iceberg_compute_state
    use iceberg_thermodynamics, only: voxel_geometry_active, voxel_geometry_mass, &
                                      voxel_geometry_draft, voxel_geometry_drag_areas, &
                                      voxel_geometry_stability, voxel_geometry_test_enable
    implicit none

    integer :: nerr
    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.5 — VOXEL GEOMETRY / DRIFT TESTS'
    print *, '===================================================='

    ! Enable voxel geometry for the drift-interface checks (TEST-ONLY hook;
    ! production default OFF uses the bulk prism path unchanged).
    call voxel_geometry_test_enable()

    call test_frontal_cubic()
    call test_frontal_diagonal()
    call test_frontal_melted()
    call test_integration_geometry()
    call test_stability()
    call test_drift_interface()

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: VOXEL GEOMETRY / DRIFT TESTS PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: VOXEL GEOMETRY / DRIFT TESTS FAILED, errors=', nerr
        stop 1
    end if

contains

    ! --- Test 1: cubic, flow_angle=0 -> A_perp = 10000 ---------------------
    subroutine test_frontal_cubic()
        type(voxel_iceberg_type) :: vox
        real(8) :: ap, asub
        call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
        call voxel_iceberg_get_frontal_area(vox, 0.0d0, ap, asub)
        print '(a,f12.2,a,f12.2)', ' T1 A_perp=', ap, ' A_sub_proj=', asub
        if (abs(ap - 10000.0d0) > 0.01d0*10000.0d0) then
            print *, '  FAIL: A_perp != 10000 (1%)'; nerr = nerr + 1
        else
            print *, '  OK: A_perp = projected face (10000 m^2)'
        end if
        if (asub <= 0.0d0 .or. asub > ap + 1.0d-9) then
            print *, '  FAIL: A_sub_proj not in (0, A_perp]'; nerr = nerr + 1
        else
            print *, '  OK: A_sub_proj positive and <= A_perp'
        end if
    end subroutine test_frontal_cubic

    ! --- Test 2: 45 deg -> true silhouette 10000*(cos+sin) = 14142 ----------
    subroutine test_frontal_diagonal()
        type(voxel_iceberg_type) :: vox
        real(8) :: ap, asub, expected
        call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
        call voxel_iceberg_get_frontal_area(vox, 0.25d0*3.141592653589793d0, ap, asub)
        expected = 10000.0d0*(cos(0.25d0*3.141592653589793d0) + &
                              sin(0.25d0*3.141592653589793d0))   ! 14142
        print '(a,f12.2,a,f12.2)', ' T2 A_perp(45)=', ap, ' expected=', expected
        ! NOTE: the prompt's 7071 is the single-face projection; the physical
        ! silhouette of a cube at 45 deg includes the orthogonal face (14142).
        if (abs(ap - expected) > 0.01d0*expected) then
            print *, '  FAIL: A_perp(45) != 14142 (1%)'; nerr = nerr + 1
        else
            print *, '  OK: A_perp(45) = full projected silhouette (14142 m^2)'
        end if
    end subroutine test_frontal_diagonal

    ! --- Test 3: melted half-width -> A_perp halves -------------------------
    subroutine test_frontal_melted()
        type(voxel_iceberg_type) :: vox
        real(8) :: ap0, ap, asub
        integer :: j
        call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
        call voxel_iceberg_get_frontal_area(vox, 0.0d0, ap0, asub)
        do j = 6, 10
            vox%phi(:, j, :) = 0.0d0
        end do
        call voxel_iceberg_compute_state(vox)
        call voxel_iceberg_get_frontal_area(vox, 0.0d0, ap, asub)
        print '(a,f12.2,a,f12.2)', ' T3 A_perp full=', ap0, ' half-width=', ap
        if (abs(ap - 0.5d0*ap0) > 0.02d0*ap0) then
            print *, '  FAIL: A_perp did not halve after removing half width'; nerr = nerr + 1
        else
            print *, '  OK: A_perp decreases with removed voxels (halved)'
        end if
    end subroutine test_frontal_melted

    ! --- Test 4: integration with profile forcing --------------------------
    subroutine test_integration_geometry()
        type(voxel_iceberg_type) :: vox
        type(ocean_profile) :: prof
        real(8) :: dt, m0, m1, d0, d1, ap0, ap1, asub, wa, sa, ea
        real(8) :: basal, lat, surf
        integer :: it
        dt = 3600.0d0
        prof%nlevels = 5
        allocate (prof%z(5), prof%dz(5), prof%temp(5), prof%salt(5), prof%u(5), prof%v(5), &
                  prof%u_rel(5))
        prof%z = (/ 1.0, 10.0, 50.0, 100.0, 300.0 /)
        prof%dz = 10.0
        prof%temp = (/ 2.0, 1.5, 0.5, 0.0, -1.0 /)
        prof%salt = 0.035
        prof%u = 0.1; prof%v = 0.0; prof%u_rel = 0.1
        call voxel_iceberg_init(vox, 8, 8, 8, 10.0d0, 10.0d0, 10.0d0, -5.0d0, 1.0d0)
        m0 = vox%total_mass; d0 = vox%draft
        call voxel_iceberg_get_frontal_area(vox, 0.0d0, ap0, asub)
        do it = 1, 10
            call voxel_iceberg_step_profile(vox, dt, prof, 0.0d0, 0.0d0, &
                                            -5.0d0, 0.0d0, 5.0d0, basal, lat, surf)
        end do
        m1 = vox%total_mass; d1 = vox%draft
        call voxel_iceberg_get_frontal_area(vox, 0.0d0, ap1, asub)
        call voxel_iceberg_get_areas(vox, wa, sa, ea)
        print '(a,f10.1,a,f10.1)', ' T4 A_perp=', ap0, ' -> ', ap1
        print '(a,es12.4,a,es12.4)', '    mass ', m0, ' -> ', m1
        print '(a,f8.2,a,f8.2,a,es12.4)', '    draft ', d0, ' -> ', d1, ' A_sail=', ea
        if (any(vox%phi /= vox%phi) .or. any(vox%T /= vox%T)) then
            print *, '  FAIL: NaN'; nerr = nerr + 1
        else if (.not. (m1 < m0 .and. d1 < d0)) then
            print *, '  FAIL: no melt/geometry response'; nerr = nerr + 1
        else if (.not. (ap1 > 0.0d0) .or. ap1 /= ap1) then
            print *, '  FAIL: A_perp invalid'; nerr = nerr + 1
        else
            print *, '  OK: no NaN; mass & draft decrease; A_perp positive/finite'
        end if
    end subroutine test_integration_geometry

    ! --- Metacentric stability (documented estimate) -----------------------
    subroutine test_stability()
        type(voxel_iceberg_type) :: vox
        real(8) :: gm, bm, bg, iwp, vsub
        call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
        call voxel_iceberg_get_stability(vox, gm, bm, bg, iwp, vsub)
        print '(a,3f10.4,a,es12.4)', ' T5 GM/BM/BG=', gm, bm, bg, ' V_sub=', vsub
        if (vsub <= 0.0d0 .or. iwp <= 0.0d0 .or. any((/gm, bm, bg/) /= (/gm, bm, bg/))) then
            print *, '  FAIL: invalid stability metric'; nerr = nerr + 1
        else
            print *, '  OK: GM/BM/BG finite (no capsize dynamics; documented)'
        end if
    end subroutine test_stability

    ! --- Gated drift interface (voxel_geometry_*) --------------------------
    subroutine test_drift_interface()
        real :: m, d, asub, asail, gm, bm, bg
        logical :: active
        active = voxel_geometry_active()
        m = voxel_geometry_mass()
        d = voxel_geometry_draft()
        call voxel_geometry_drag_areas(0.0, asub, asail)
        call voxel_geometry_stability(gm, bm, bg)
        print '(a,l1,a,es12.4,a,f8.2,a,es12.4,a,es12.4)', ' T6 active=', active, &
            ' mass=', m, ' draft=', d, ' A_sub=', asub, ' A_sail=', asail
        if (.not. active) then
            print *, '  FAIL: VOXEL_ENABLED=true but geometry inactive'; nerr = nerr + 1
        else if (m <= 0.0 .or. asub <= 0.0 .or. asail <= 0.0) then
            print *, '  FAIL: voxel mass/areas not positive'; nerr = nerr + 1
        else
            print *, '  OK: voxel geometry interface active (drift uses it when ON)'
        end if
    end subroutine test_drift_interface

end program test_voxel_drift
