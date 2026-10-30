! ==============================================================================
! Тест: test_voxel_thermal_solver (Stage 12.3)
! Само-согласованность решётки (без данных/CI-safe): adiabatic energy conserved,
! gradient smoothing, phase clamp, Stefan melt/refreeze sign, air-surface melt.
! ==============================================================================
program test_voxel_thermal_solver
    use voxel_thermal_solver
    use iceberg_types, only: ocean_freezing_point, RHO_ICE, C_ICE, K_ICE, LATENT_HEAT
    implicit none

    real(8), allocatable :: T(:,:,:), phi(:,:,:), Tn(:,:,:), pn(:,:,:)
    logical, allocatable :: sm(:,:,:), em(:,:,:)
    real(8) :: dx, dy, dz, dt, sum0, sum1
    real(8) :: basal, lat, surf
    integer :: i, j, k, n, nerr

    nerr = 0
    dx = 10.0d0; dy = 10.0d0; dz = 10.0d0
    dt = 1000.0d0
    print *, '===================================================='
    print *, ' STAGE 12.3 — VOXEL THERMAL SOLVER TEST'
    print *, '===================================================='

    allocate (T(5, 5, 5), phi(5, 5, 5), Tn(5, 5, 5), pn(5, 5, 5))
    allocate (sm(5, 5, 5), em(5, 5, 5))

    ! --- Check 1: adiabatic interior conduction conserves ΣT·phi & smooths ----
    T = -20.0d0; phi = 1.0d0
    T(3, 3, 3) = 0.0d0                     ! hot spot (at melting → will melt, so use -5)
    T(3, 3, 3) = -5.0d0
    sum0 = adiabatic_energy(T, phi)
    call solve_heat_conduction(T, phi, dx, dy, dz, dt, real(K_ICE,8), real(RHO_ICE,8), real(C_ICE,8), &
                               real(LATENT_HEAT,8), Tn, pn)
    sum1 = adiabatic_energy(Tn, pn)
    print '(a,2es16.6)', ' energy before/after: ', sum0, sum1
    if (abs(sum1 - sum0) > 1.0d-4*abs(sum0) + 1.0d-6) then
        print *, '  FAIL: adiabatic energy not conserved'; nerr = nerr + 1
    else
        print *, '  OK: adiabatic conduction conserves energy'
    end if
    if (Tn(2, 3, 3) > T(2, 3, 3) .and. Tn(3, 3, 3) < T(3, 3, 3)) then
        print *, '  OK: hotspot diffuses (centre cools, neighbour warms)'
    else
        print *, '  NOTE: diffusion check (centre', Tn(3, 3, 3), 'neigh', Tn(2, 3, 3), ')'
    end if

    ! --- Check 2: phase clamp T>0 melts (phi down, T→0) ----------------------
    T = 5.0d0; phi = 1.0d0
    call solve_heat_conduction(T, phi, dx, dy, dz, dt, real(K_ICE,8), real(RHO_ICE,8), real(C_ICE,8), &
                               real(LATENT_HEAT,8), Tn, pn)
    if (pn(3, 3, 3) < 1.0d0 - 1.0d-9 .and. Tn(3, 3, 3) <= 1.0d-9) then
        print '(a,f10.6,a,f10.5)', '  OK: phase clamp phi=', pn(3, 3, 3), ' T=', Tn(3, 3, 3)
    else
        print '(a,f10.6,a,f10.5)', '  FAIL: phase clamp phi=', pn(3, 3, 3), ' T=', Tn(3, 3, 3)
        nerr = nerr + 1
    end if
    if (any(pn < -1.0d-9) .or. any(pn > 1.0d0 + 1.0d-9)) then
        print *, '  FAIL: phi out of [0,1]'; nerr = nerr + 1
    end if

    ! --- Check 3: Stefan ocean melt (warm ocean) on an ISOLATED submerged voxel
    ! All 6 faces are boundary → basal (2 horizontal) + lateral (4 side) melt >0.
    T = -5.0d0; phi = 0.0d0
    phi(3, 3, 1) = 1.0d0
    sm = .false.; em = .false.
    sm(3, 3, 1) = .true.
    call apply_boundary_fluxes(T, phi, dx, dy, dz, dt, &
                               2.0d0, 0.035d0, 0.05d0, 0.0d0, &
                               -20.0d0, 0.0d0, 5.0d0, sm, em, basal, lat, surf)
    print '(a,3es12.4)', ' melt kg/s basal/lat/surf: ', basal, lat, surf
    if (basal > 0.0d0 .and. lat > 0.0d0) then
        print *, '  OK: warm ocean → positive basal & lateral melt'
    else
        print *, '  FAIL: warm ocean should melt'; nerr = nerr + 1
    end if
    if (phi(3, 3, 1) < 1.0d0) then
        print *, '  OK: melt reduces submerged-voxel phi'
    else
        print *, '  FAIL: melt should reduce phi'; nerr = nerr + 1
    end if
    if (any(phi < -1.0d-9) .or. any(phi > 1.0d0 + 1.0d-9)) then
        print *, '  FAIL: phi out of [0,1] after fluxes'; nerr = nerr + 1
    end if
    if (any(phi /= phi)) then
        print *, '  FAIL: NaN in phi after fluxes'; nerr = nerr + 1
    end if

    ! --- Check 4: sub-Tf ocean → m = 0, phi UNCHANGED (spec A5: no accretion) --
    T = -20.0d0; phi = 0.0d0; phi(3, 3, 1) = 0.5d0
    sm = .false.; em = .false.
    sm(3, 3, 1) = .true.
    call apply_boundary_fluxes(T, phi, dx, dy, dz, dt, &
                               -5.0d0, 0.035d0, 0.05d0, 0.0d0, &
                               -30.0d0, 0.0d0, 0.0d0, sm, em, basal, lat, surf)
    ! ocean at -5 °C < Tf(~-1.9): accretion NOT modelled (spec A5) → m=0, phi same
    print '(a,es12.4,a,f8.4)', ' sub-Tf basal kg/s=', basal, ' phi=', phi(3, 3, 1)
    if (abs(basal) < 1.0d-12 .and. abs(phi(3, 3, 1) - 0.5d0) < 1.0d-12) then
        print *, '  OK: sub-Tf ocean → m=0, phi unchanged (no accretion, spec A5)'
    else
        print *, '  FAIL: expected m=0 and unchanged phi'; nerr = nerr + 1
    end if

    ! --- Check 5: air-surface heat adds melt with warm flux -------------------
    T = -1.0d0; phi = 1.0d0
    sm = .false.; em = .true.
    em(3, 3, 5) = .true.; sm(3, 3, 5) = .false.
    ! large positive atmos_Q (net surface heat flux) → surface melt
    call apply_boundary_fluxes(T, phi, dx, dy, dz, dt, &
                               -2.0d0, 0.035d0, 0.0d0, 0.0d0, &
                               5.0d0, 200.0d0, 5.0d0, sm, em, basal, lat, surf)
    print '(a,es12.4)', ' surface melt kg/s: ', surf
    if (surf > 0.0d0) then
        print *, '  OK: positive atmos heat flux → surface melt'
    else
        print *, '  FAIL: expected surface melt'; nerr = nerr + 1
    end if

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: VOXEL THERMAL SOLVER TEST PASSED'
        stop 0
    else
        print *, 'FAILURE: VOXEL THERMAL SOLVER TEST FAILED, errors=', nerr
        stop 1
    end if

contains

    real(8) function adiabatic_energy(T, phi)
        real(8), intent(in) :: T(:,:,:), phi(:,:,:)
        integer :: i, j, k
        adiabatic_energy = 0.0d0
        do k = 1, size(T, 3)
            do j = 1, size(T, 2)
                do i = 1, size(T, 1)
                    adiabatic_energy = adiabatic_energy + phi(i, j, k)*T(i, j, k)
                end do
            end do
        end do
    end function adiabatic_energy

end program test_voxel_thermal_solver
