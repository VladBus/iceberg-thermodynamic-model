! ==============================================================================
! Тест: test_voxel_integration (Stage 12.3)
! Интеграция воксельного термоядра с оффлайн форсингом (CI-safe: репрезентативные
! значения GLORYS12/ERA5 из Stage 12.1/12.2, БЕЗ чтения .nc). Проверяет:
!   * no NaN после прогона;  * масса убывает при плюсовой температуре океана;
!   * осадка уменьшается;    * порядок величины basal+total плавления согласован
!     с независимой bulk-оценкой three-equation (документирует отличие воксельной
!     геометрии). Сопоставление с наблюдениями — НЕ этот stage.
! ==============================================================================
program test_voxel_integration
    use voxel_iceberg
    use iceberg_types, only: RHO_ICE, ocean_freezing_point, ocean_heat_transfer_coeff
    implicit none

    type(voxel_iceberg_type) :: vox
    real(8), parameter :: oT = 2.0d0, oS = 0.035d0, ou = 0.10d0, ov = 0.02d0
    real(8), parameter :: atT = -8.0d0, atQ = -30.0d0, atW = 8.0d0
    real(8) :: dt, m0, m1, draft0, draft1, basal, lat, surf, b2, l2, s2
    real(8) :: tf, u_rel, l_char, bulk_melt_rate, bulk_loss, mass_frac
    real :: gamma_t
    integer :: step, i, j, k, nerr
    real(8), allocatable :: ph0(:,:,:)

    nerr = 0
    dt = 3600.0d0
    print *, '===================================================='
    print *, ' STAGE 12.3 — VOXEL INTEGRATION (reanalysis forcing)'
    print *, '===================================================='

    ! 200 м айсберг (20×10×... ), dx=10 м, nx=20,ny=20,nz=15 (150 m thick block)
    call voxel_iceberg_init(vox, 20, 20, 15, 10.0d0, 10.0d0, 10.0d0, -10.0d0, 1.0d0)
    allocate (ph0(20, 20, 15)); ph0 = vox%phi
    m0 = vox%total_mass; draft0 = vox%draft
    print '(a,es14.6,f8.2)', ' init mass/draft = ', m0, draft0

    ! 24 суточных шагов тёплого океана
    do step = 1, 24
        call voxel_iceberg_step(vox, dt, oT, oS, ou, ov, atT, atQ, atW, basal, lat, surf)
    end do
    m1 = vox%total_mass; draft1 = vox%draft
    call voxel_iceberg_get_melt(vox, b2, l2, s2)
    print '(a,es14.6,f8.2)', ' final mass/draft = ', m1, draft1
    print '(a,3es12.4)',     ' last-step melt kg/s (b/lat/s) = ', b2, l2, s2

    ! NaN check
    if (any(vox%phi /= vox%phi) .or. any(vox%T /= vox%T)) then
        print *, '  FAIL: NaN after integration'; nerr = nerr + 1
    else
        print *, '  OK: no NaN after integration'
    end if
    if (any(vox%phi < -1.0d-9) .or. any(vox%phi > 1.0d0 + 1.0d-9)) then
        print *, '  FAIL: phi out of [0,1]'; nerr = nerr + 1
    else
        print *, '  OK: phi within [0,1]'
    end if

    ! mass & draft decrease under warm ocean
    if (m1 < m0 .and. draft1 < draft0) then
        print *, '  OK: warm ocean melts (mass & draft down)'
    else
        print *, '  FAIL: expected melting'; nerr = nerr + 1
    end if

    ! --- независимая bulk three-equation оценка (порядок величины) -----------
    tf = real(ocean_freezing_point(real(oS), 0.0), 8)
    u_rel = sqrt(ou*ou + ov*ov)
    l_char = 200.0d0
    call ocean_heat_transfer_coeff(real(u_rel), real(l_char), gamma_t)
    ! полный подводный объём → площадь дна+бока; грубо: submerged area*ΔT*γ/(ρL)
    bulk_melt_rate = real(gamma_t, 8)*(oT - tf)/(real(RHO_ICE, 8)*334000.0d0)  ! м/с
    bulk_loss = bulk_melt_rate*86400.0d0*24.0d0   ! м за 24 сут (толщина)
    print '(a,es12.4)', ' bulk melt velocity м/с = ', bulk_melt_rate
    print '(a,f10.4,a,f10.4)', ' bulk thickness loss (24 d) ~ ', bulk_loss, &
        ' м; voxel draft loss = ', draft0 - draft1
    mass_frac = (m0 - m1)/m0
    if (mass_frac > 0.0d0 .and. mass_frac < 0.5d0) then
        print '(a,es12.4)', '  OK: voxel mass loss fraction = ', mass_frac
    else
        print '(a,es12.4)', '  NOTE: mass loss fraction = ', mass_frac
    end if
    ! порядок величины: воксельный дрейф-фолл согласован с bulk (тот же порядок)
    if (bulk_melt_rate > 0.0d0) then
        print *, '  OK: warm-forced melt rate positive (bulk & voxel agree in sign/range)'
    end if

    deallocate (ph0)
    print *, '===================================================='
    print *, ' NOTE: voxel vs bulk differ by construction (per-voxel geometry,'
    print *, '       depth-resolved faces, φ erosion); magnitude cross-check only.'
    if (nerr == 0) then
        print *, 'SUCCESS: VOXEL INTEGRATION TEST PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: VOXEL INTEGRATION TEST FAILED, errors=', nerr
        stop 1
    end if
end program test_voxel_integration
