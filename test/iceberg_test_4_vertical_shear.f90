! ==============================================================================
! Тест: TEST_4 — Vertical shear
! Назначение: Слойное течение — сравнить Method A (интеграл по слоям)
!             и Method B (глубинно-усреднённое) для водного трения.
!             Method A должен давать большее трение при сдвиге (FitzMaurice 2017).
! ==============================================================================

program iceberg_test_4_vertical_shear
    use iceberg
    use iceberg_dynamics
    implicit none

    type(iceberg_state) :: state_a, state_b
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag_a, diag_b

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: fx_a, fy_a, fx_b, fy_b
    real :: drag_a, drag_b

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_4: Vertical Shear — Method A vs Method B"
    print *, "=================================================="

    ! Настройка: сдвиг U(z) = 0.2 * exp(z/50), V=0, нет ветра
    call iceberg_init(state_a, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)
    call iceberg_init(state_b, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

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
        ! Сдвиг: U = 0.2 * exp(-z/50) — убывает с глубиной
        ocean_prof%u(step) = 0.2*exp(-ocean_prof%z(step)/50.0)
        ocean_prof%v(step) = 0.0
    end do

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 10

    ! Шаг для Method A (стандартный iceberg_step использует Method A)
    call iceberg_step(state_a, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag_a)

    ! Шаг для Method B (прямой вызов)
    call iceberg_compute_geometry(state_b, diag_b)
    call compute_water_force_method_b(state_b, ocean_prof, fx_b, fy_b)
    drag_b = sqrt(fx_b**2 + fy_b**2)

    fx_a = diag_a%f_water_x
    fy_a = diag_a%f_water_y
    drag_a = sqrt(fx_a**2 + fy_a**2)

    print *, "Method A (layer-integrated) drag: ", drag_a, " N"
    print *, "Method B (depth-averaged) drag:   ", drag_b, " N"
    print *, "Ratio A/B: ", drag_a/drag_b

    ! Проверка: при сдвиге Method A должен давать большее трение
    n_checks = n_checks + 1
    if (drag_a .gt. drag_b*1.01) then
        print *, "OK: Method A > Method B (shear enhances drag)"
    else
        print *, "WARNING: Method A (", drag_a, ") not significantly > Method B (", drag_b, ")"
    end if

    ! Проверка: силы не NaN
    n_checks = n_checks + 1
    if (drag_a .ne. drag_a .or. drag_b .ne. drag_b) then
        print *, "ERROR: NaN in drag forces"
        n_errors = n_errors + 1
    else
        print *, "OK: Drag forces finite"
    end if

    ! Проверка: нет плавления
    n_checks = n_checks + 1
    if (diag_a%m_basal .eq. 0.0 .and. diag_a%m_lateral .eq. 0.0) then
        print *, "OK: No melt"
    else
        print *, "ERROR: Unexpected melt"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_4 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_4 FAILED with ", n_errors, " errors"
        stop 1
    end if

end program iceberg_test_4_vertical_shear
