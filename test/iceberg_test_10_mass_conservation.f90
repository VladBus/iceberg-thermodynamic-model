! ==============================================================================
! Тест: TEST_10 — Mass conservation
! Назначение: Проверить, что потеря массы равна интегрированному плавленному
!             потоку за время.
! ==============================================================================

program iceberg_test_10_mass_conservation
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
    real :: M0, M_final
    real :: total_budget_loss, total_direct_loss
    real :: budget_error
    real :: mass_from_geometry

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_10: Mass Conservation Budget"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Тёплый океан с плавлением
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
        if (ocean_prof%z(step) .le. 100.0) then
            ocean_prof%temp(step) = 2.0 - 1.0*ocean_prof%z(step)/100.0
        else
            ocean_prof%temp(step) = 1.0
        end if
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.05
        ocean_prof%v(step) = 0.0
    end do

    ! Умеренно тёплый воздух для поверхностного плавления
    atmos%u10 = 5.0
    atmos%v10 = 0.0
    atmos%t2m = 273.15  ! 0°C
    atmos%d2m = 270.0
    atmos%tcc = 0.5
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 24*10  ! 10 дней

    M0 = 910.0*100.0**3
    total_budget_loss = 0.0

    print *, "Initial mass: ", M0, " kg"

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) then
            print *, "Iceberg melted away at step ", step
            exit
        end if

        total_budget_loss = total_budget_loss + diag%total_mass_loss
    end do

    M_final = diag%mass
    total_direct_loss = M0 - M_final
    budget_error = abs(total_direct_loss - total_budget_loss)/M0

    print *, "Final mass: ", M_final, " kg"
    print *, "Direct mass loss: ", total_direct_loss, " kg"
    print *, "Budget mass loss: ", total_budget_loss, " kg"
    print *, "Relative budget error: ", budget_error*100.0, "%"

    ! Проверка 1: Бюджет сходится внутри 0.1%
    n_checks = n_checks + 1
    if (budget_error .lt. 0.001) then
        print *, "OK: Mass budget closes (error = ", budget_error*100, "%)"
    else
        print *, "ERROR: Mass budget error = ", budget_error*100, "% (target < 0.1%)"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Все компоненты потерь неотрицательны
    n_checks = n_checks + 1
    if (diag%basal_mass_loss .ge. 0.0 .and. &
        diag%lateral_mass_loss .ge. 0.0 .and. &
        diag%surface_mass_loss .ge. 0.0) then
        print *, "OK: All mass loss components non-negative"
    else
        print *, "ERROR: Negative mass loss component"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Масса убывает
    n_checks = n_checks + 1
    if (M_final .lt. M0) then
        print *, "OK: Mass decreasing"
    else
        print *, "ERROR: Mass not decreasing"
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Масса = rho_ice * L * W * H (диагностическая)
    n_checks = n_checks + 1
    mass_from_geometry = 910.0*state%L*state%W*state%H
    if (abs(diag%mass - mass_from_geometry)/mass_from_geometry .lt. 1.0e-10) then
        print *, "OK: Diagnostic mass = geometric mass"
    else
        print *, "ERROR: Mass diagnostic mismatch: diag=", diag%mass, &
            " geom=", mass_from_geometry
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_10 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_10 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_10_mass_conservation
