! ==============================================================================
! Тест: TEST_1 — Hydrostatic cube equilibrium
! Назначение: Проверить буoyantность и осадку для кубического айсберга
!             в стоячей воде (Stage 9.1 validation plan).
! Ожидается: D ≈ 88.52 м, буoyantность = вес (внутри 1%), нет дрейфа, нет плавления.
! ==============================================================================

program iceberg_test_1_hydrostatic
    use iceberg
    use iceberg_geometry
    implicit none

    type(iceberg_state) :: state
    type(iceberg_diagnostics) :: geom
    real :: buoyancy_res
    integer :: n_errors, n_checks
    real :: expected_draft
    real :: v_total, v_sub

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_1: Hydrostatic Cube Equilibrium"
    print *, "=================================================="

    ! Инициализация: L=W=H=100 м, rho_ice=910, rho_water=1028
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Вычисление геометрии
    call iceberg_compute_geometry(state, geom)
    call iceberg_compute_buoyancy(state, buoyancy_res)

    print *, "Mass:       ", geom%mass, " kg"
    print *, "Draft:      ", geom%draft, " m"
    print *, "Freeboard:  ", geom%freeboard, " m"
    print *, "A_waterline:", geom%a_waterline, " m2"
    print *, "A_wet:      ", geom%a_wet, " m2"
    print *, "A_sail:     ", geom%a_sail, " m2"
    print *, "Buoyancy residual: ", buoyancy_res

    ! Проверка 1: Осадка D = H * rho_ice / rho_water = 100 * 910 / 1028 = 88.5214 м
    expected_draft = 100.0*910.0/1028.0
    n_checks = n_checks + 1
    if (abs(geom%draft - expected_draft) .lt. 0.01) then
        print *, "OK: Draft = ", geom%draft, " m (expected ", expected_draft, " m)"
    else
        print *, "ERROR: Draft = ", geom%draft, " m, expected ", expected_draft, " m"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Буoyantность = вес (внутри 1%)
    n_checks = n_checks + 1
    if (buoyancy_res .lt. 0.01) then
        print *, "OK: Buoyancy residual = ", buoyancy_res, " (< 1%)"
    else
        print *, "ERROR: Buoyancy residual = ", buoyancy_res, " (>= 1%)"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Объемы
    v_total = state%L*state%W*state%H
    v_sub = state%L*state%W*geom%draft
    n_checks = n_checks + 1
    if (abs(v_sub - v_total*910.0/1028.0)/v_total .lt. 1.0e-6) then
        print *, "OK: Submerged volume consistent"
    else
        print *, "ERROR: Submerged volume inconsistent"
        n_errors = n_errors + 1
    end if

    ! Проверка 4: Масса
    n_checks = n_checks + 1
    if (abs(geom%mass - 910.0*100.0**3) .lt. 1.0) then
        print *, "OK: Mass = ", geom%mass, " kg"
    else
        print *, "ERROR: Mass mismatch"
        n_errors = n_errors + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_1 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_1 FAILED with ", n_errors, " errors"
        stop 1
    end if
end program iceberg_test_1_hydrostatic
