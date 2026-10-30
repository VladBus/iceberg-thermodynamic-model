! ==============================================================================
! Тест: test_voxel_iceberg (Stage 12.3)
! Геометрия/самосогласованность (CI-safe, без данных): масса аналитически,
! Архимедова осадка, площади, сохранение массы при нулевом форсинге, фазовое
! плавление, удаление ячеек phi<phi_min, адаптация ватерлейна.
! ==============================================================================
program test_voxel_iceberg
    use voxel_iceberg
    use iceberg_types, only: RHO_ICE, RHO_WATER
    implicit none

    type(voxel_iceberg_type) :: vox
    real(8) :: m0, m1, draft0, draft1, wa, sa, ea, exp_mass, mass_tol, draft_exp
    real(8) :: basal, lat, surf
    integer :: i, j, k, nerr, ischeme

    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.3 — VOXEL ICEBERGEOMETRY TEST'
    print *, '===================================================='

    ! --- Check 1: init mass/draft/areas (analytic) --------------------------
    call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
    call voxel_iceberg_get_mass(vox, m0)
    exp_mass = 10.0d0*10.0d0*10.0d0 * (10.0d0**3) * real(RHO_ICE, 8)  ! 1000 vox × 1000 m³ × rho
    print '(a,es16.6)', ' mass = ', m0
    if (abs(m0 - exp_mass) > 1.0d-3*exp_mass) then
        print '(a,es14.6)', '  FAIL: mass vs analytic ', exp_mass; nerr = nerr + 1
    else
        print *, '  OK: mass matches analytic ρ_ice·V'
    end if

    call voxel_iceberg_get_draft(vox, draft0)
    draft_exp = 100.0d0*real(RHO_ICE, 8)/real(RHO_WATER, 8)   ! = 88.5 m (prism)
    print '(a,f8.3,a,f8.3)', ' draft = ', draft0, ' expected ≈', draft_exp
    if (abs(draft0 - draft_exp) > 6.0d0) then   ! voxel-waterline straddling tolerance
        print *, '  FAIL: draft vs Archimedes'; nerr = nerr + 1
    else
        print *, '  OK: draft matches Archimedes (ρ_i/ρ_w·H)'
    end if

    call voxel_iceberg_get_areas(vox, wa, sa, ea)
    print '(a,3f12.1)', ' waterline/submerged/exposed area = ', wa, sa, ea
    ! полный куб 100 м: площадь = 6·100·100 = 60000; ватерлейн-сечение ≈ 10000
    if (abs((sa + ea) - 60000.0d0) > 2000.0d0) then
        print *, '  FAIL: submerged+exposed area != total surface'; nerr = nerr + 1
    else
        print *, '  OK: external face area ≈ total cube surface'
    end if
    if (wa < 9000.0d0 .or. wa > 11000.0d0) then
        print *, '  FAIL: waterline_area not ~10000'; nerr = nerr + 1
    else
        print *, '  OK: waterline_area ≈ cross-section'
    end if

    ! --- Check 2: mass conservation, zero forcing ---------------------------
    m0 = vox%total_mass
    do k = 1, 100
        call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                                -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
    end do
    call voxel_iceberg_get_mass(vox, m1)
    mass_tol = abs(m1 - m0)/m0
    print '(a,es12.4)', ' mass drift after 100 zero-forcing steps: ', mass_tol
    if (mass_tol > 1.0d-6) then
        print *, '  FAIL: mass not conserved under zero forcing'; nerr = nerr + 1
    else
        print *, '  OK: mass conserved under zero forcing'
    end if

    ! --- Check 3: melting (warm ocean + current) reduces mass ---------------
    call voxel_iceberg_init(vox, 10, 10, 10, 10.0d0, 10.0d0, 10.0d0, -5.0d0, 1.0d0)
    m0 = vox%total_mass
    draft0 = vox%draft
    do k = 1, 10
        call voxel_iceberg_step(vox, 3600.0d0, 2.0d0, 0.035d0, 0.1d0, 0.0d0, &
                                -2.0d0, 50.0d0, 5.0d0, basal, lat, surf)
    end do
    call voxel_iceberg_get_mass(vox, m1)
    call voxel_iceberg_get_draft(vox, draft1)
    print '(a,es14.6,a,es14.6)', ' melting: mass ', m0, ' -> ', m1
    print '(a,f8.3,a,f8.3)', '        draft ', draft0, ' -> ', draft1
    if (m1 < m0 .and. draft1 < draft0) then
        print *, '  OK: warm forcing melts → mass & draft decrease'
    else
        print *, '  FAIL: expected melting (mass & draft down)'; nerr = nerr + 1
    end if
    if (any(vox%phi < -1.0d-9) .or. any(vox%phi > 1.0d0 + 1.0d-9)) then
        print *, '  FAIL: phi out of [0,1]'; nerr = nerr + 1
    end if

    ! --- Check 4: voxel removal (phi<phi_min) -------------------------------
    call voxel_iceberg_init(vox, 6, 6, 6, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
    vox%phi(3, 3, 3) = 0.005d0                    ! ниже phi_min=0.01
    call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                            -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
    if (vox%phi(3, 3, 3) == 0.0d0) then
        print *, '  OK: voxel with phi<phi_min removed'
    else
        print '(a,f8.4)', '  FAIL: low-phi voxel not removed, phi=', vox%phi(3, 3, 3)
        nerr = nerr + 1
    end if

    ! --- Check 5: waterline responds to mass loss (draft adjust) ------------
    call voxel_iceberg_init(vox, 8, 8, 8, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
    draft0 = vox%draft
    ! убрать верхний слой (только твёрдый сверху) → легче; пересчёт
    do j = 1, 8
        do i = 1, 8
            vox%phi(i, j, 8) = 0.0d0
        end do
    end do
    call voxel_iceberg_compute_state(vox)
    draft1 = vox%draft
    print '(a,f8.2,a,f8.2)', ' draft after removing top layer: ', draft0, ' -> ', draft1
    if (draft1 < draft0) then
        print *, '  OK: draft recomputed after mass change'
    else
        print *, '  FAIL: draft should adjust with mass'; nerr = nerr + 1
    end if

    ! --- Check 6 (A-T9): key physics under BOTH schemes ---------------------
    do ischeme = 1, 2
        ! melting under warm forcing
        call voxel_iceberg_init(vox, 8, 8, 8, 10.0d0, 10.0d0, 10.0d0, -5.0d0, 1.0d0, &
                                scheme=ischeme)
        m0 = vox%total_mass
        do k = 1, 5
            call voxel_iceberg_step(vox, 3600.0d0, 2.0d0, 0.035d0, 0.1d0, 0.0d0, &
                                    -2.0d0, 50.0d0, 5.0d0, basal, lat, surf)
        end do
        call voxel_iceberg_get_mass(vox, m1)
        if (m1 < m0) then
            print '(a,i0,a)', '  OK: scheme ', ischeme, ' melts under warm forcing'
        else
            print '(a,i0,a)', '  FAIL: scheme ', ischeme, ' did not melt'; nerr = nerr + 1
        end if
        ! removal
        call voxel_iceberg_init(vox, 6, 6, 6, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0, &
                                scheme=ischeme)
        vox%phi(3, 3, 3) = 0.005d0
        call voxel_iceberg_step(vox, 3600.0d0, 0.0d0, 0.035d0, 0.0d0, 0.0d0, &
                                -10.0d0, 0.0d0, 0.0d0, basal, lat, surf)
        if (vox%phi(3, 3, 3) == 0.0d0) then
            print '(a,i0,a)', '  OK: scheme ', ischeme, ' removes phi<phi_min voxel'
        else
            print '(a,i0,a)', '  FAIL: scheme ', ischeme, ' removal'; nerr = nerr + 1
        end if
    end do

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: VOXEL ICEBERG TEST PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: VOXEL ICEBERG TEST FAILED, errors=', nerr
        stop 1
    end if
end program test_voxel_iceberg
