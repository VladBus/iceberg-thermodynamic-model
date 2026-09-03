! ==============================================================================
! Тест: TEST_6 — Cold ocean no melt
! Назначение: T <= Tf везде — проверить нулевое плавление.
! ==============================================================================

program iceberg_test_6_cold_ocean
    use iceberg
    use iceberg_thermodynamics
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_6: Cold Ocean — No Melt"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Холодный океан: T = -1.9°C везде (Tf ≈ -1.86°C при S=0.0345)
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*250)
        ocean_prof%dz(step) = 250.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.1
        ocean_prof%v(step) = 0.0
    end do

    ! Атмосфера: холодная
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 24*30

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) then
            print *, "WARNING: Iceberg melted away at step ", step
            exit
        end if
    end do

    print *, "Final melt rates: m_basal=", diag%m_basal, " m_lateral=", diag%m_lateral, &
        " m_surface=", diag%m_surface
    print *, "Final geometry: L=", state%L, " W=", state%W, " H=", state%H

    ! Проверка 1: Базальное плавление = 0
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0) then
        print *, "OK: Basal melt = 0"
    else
        print *, "ERROR: Basal melt = ", diag%m_basal, " (should be 0)"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Боковое плавление = 0
    n_checks = n_checks + 1
    if (diag%m_lateral .eq. 0.0) then
        print *, "OK: Lateral melt = 0"
    else
        print *, "ERROR: Lateral melt = ", diag%m_lateral, " (should be 0)"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Поверхностное плавление = 0
    n_checks = n_checks + 1
    if (diag%m_surface .eq. 0.0) then
        print *, "OK: Surface melt = 0"
    else
        print *, "ERROR: Surface melt = ", diag%m_surface, " (should be 0)"
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Геометрия постоянна
    n_checks = n_checks + 1
    if (abs(state%L - 100.0) .lt. 1.0e-6 .an &
        d. abs(state%W - 100.0) .lt. 1.0e-6 &
        .and. abs(state%H - 100.0) .lt. 1.0e-6) then
        print *, "OK: Geometry constant"
    else
        print *, "ERROR: Geometry changed"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Масса постоянна
    n_checks = n_checks + 1
    if (abs(diag%mass - 910.0*100.0**3) .lt. 1.0) then
        print *, "OK: Mass conserved"
    else
        print *, "ERROR: Mass changed"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_6 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_6 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_6_cold_ocean
