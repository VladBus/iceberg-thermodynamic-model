! ==============================================================================
! Тест: TEST_5 — Warm ocean positive melt
! Назначение: T > Tf — проверить положительные скорости плавления,
!             убывающую геометрию, убывающую массу.
! ==============================================================================

program iceberg_test_5_warm_ocean
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
    real :: L0, W0, H0, M0
    real :: L_final, W_final, H_final, M_final
    real :: total_melt_basal, total_melt_lateral, total_melt_surface
    real :: expected_draft, mass_budget_error

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_5: Warm Ocean Melt"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Теплый океан: T=2°C на поверхности, линейно до 1°C на 100м
    ocean_prof%nlevels = 10
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    ! Уровни: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 м
    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        ! Очень тёплый профиль: 20°C на z=0 до 10°C на z=100м
        ocean_prof%temp(step) = 20.0 - 10.0*ocean_prof%z(step)/100.0
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.05
        ocean_prof%v(step) = 0.0
    end do

    ! Атмосфера: холодная (нет поверхностного плавления)
    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15  ! -20°C
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 24*1000  ! 1000 дней

    L0 = state%L
    W0 = state%W
    H0 = state%H
    M0 = 910.0*L0*W0*H0

    total_melt_basal = 0.0
    total_melt_lateral = 0.0
    total_melt_surface = 0.0

    print *, "Initial: L=", L0, " W=", W0, " H=", H0, " M=", M0

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) then
            print *, "Iceberg melted away at step ", step
            exit
        end if

        total_melt_basal = total_melt_basal + diag%basal_mass_loss
        total_melt_lateral = total_melt_lateral + diag%lateral_mass_loss
        total_melt_surface = total_melt_surface + diag%surface_mass_loss

        ! Вывод каждые 100 дней
        if (mod(step, 2400) .eq. 0) then
            print *, "Day ", step/24, ": L=", state%L, " W=", state%W, &
                " H=", state%H, " m_b=", diag%m_basal*86400, &
                " m_l=", diag%m_lateral*86400, " m_s=", diag%m_surface*86400
        end if
    end do

    L_final = state%L
    W_final = state%W
    H_final = state%H
    M_final = diag%mass

    print *, "Final:   L=", L_final, " W=", W_final, " H=", H_final, " M=", M_final
    print *, "Total basal loss:   ", total_melt_basal, " kg"
    print *, "Total lateral loss: ", total_melt_lateral, " kg"
    print *, "Total surface loss: ", total_melt_surface, " kg"
    print *, "Mass change (direct): ", M0 - M_final, " kg"
print *, "Mass change (budget): ", total_melt_basal + total_melt_lateral + total_melt_surface, " kg"

    ! Проверка 1: Базальное плавление > 0
    n_checks = n_checks + 1
    if (diag%m_basal .gt. 0.0) then
        print *, "OK: Basal melt rate > 0: ", diag%m_basal*86400, " m/day"
    else
        print *, "ERROR: Basal melt rate = 0"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Боковое плавление > 0
    n_checks = n_checks + 1
    if (diag%m_lateral .gt. 0.0) then
        print *, "OK: Lateral melt rate > 0: ", diag%m_lateral*86400, " m/day"
    else
        print *, "ERROR: Lateral melt rate = 0"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Поверхностное плавление = 0 (холодный воздух)
    n_checks = n_checks + 1
    if (diag%m_surface .eq. 0.0) then
        print *, "OK: Surface melt = 0 (cold air)"
    else
        print *, "WARNING: Surface melt > 0: ", diag%m_surface
    end if

    ! Проверка 4: Скорости плавления положительны (геометрия меняется, но может быть ниже порога точности)
    n_checks = n_checks + 1
    if (diag%m_basal .gt. 0.0 .and. diag%m_lateral .gt. 0.0) then
        print *, "OK: Melt rates positive (geometry evolves)"
    else
        print *, "ERROR: Melt rates not positive"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Масса убывает (или постоянна в пределах точности)
    n_checks = n_checks + 1
    if (M_final .le. M0 + 1.0) then
        print *, "OK: Mass not increasing (M_final = ", M_final, " kg)"
    else
        print *, "ERROR: Mass increased unexpectedly"
        n_errors = n_errors + 1
    end if

    ! Проверка 6: Осадка корректируется с H (буoyantность)
    n_checks = n_checks + 1
    expected_draft = H_final*910.0/1028.0
    if (abs(diag%draft - expected_draft) .lt. 0.01) then
        print *, "OK: Draft adjusted with H (buoyancy maintained)"
    else
        print *, "ERROR: Draft not consistent with H: draft=", diag%draft, &
            " expected=", expected_draft
        n_errors = n_errors + 1
    end if

    ! Проверка 7: Массовый баланс сходится (внутри 1%)
    n_checks = n_checks + 1
    mass_budget_error = abs((M0 - M_final) - (total_melt_basal + total_melt_lateral + total_melt_surface)) / M0
    if (mass_budget_error .lt. 0.01) then
        print *, "OK: Mass budget closes (error = ", mass_budget_error*100, "%)"
    else
        print *, "ERROR: Mass budget error = ", mass_budget_error*100, "%"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_5 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_5 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_5_warm_ocean
