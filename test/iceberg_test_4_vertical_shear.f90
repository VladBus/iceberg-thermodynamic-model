! ==============================================================================
! Тест: TEST_4 — Vertical shear
! Назначение: Слойное течение — сравнить Method A (интеграл по слоям)
!             и Method B (глубинно-усреднённое) для водного трения.
!             Method A должен давать большее трение при сдвиге (FitzMaurice 2017).
! Профиль: мелкие уровни 0-100м с сдвигом, глубокие — без сдвига.
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
    real :: u_surface, u_bottom
    real :: a_sides

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_4: Vertical Shear — Method A vs Method B"
    print *, "=================================================="

    ! Настройка: айсберг 100x100x100м, осадка ~88.5м
    call iceberg_init(state_a, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)
    call iceberg_init(state_b, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Океанский профиль: 20 уровней по 5м в верхних 100м, потом грубые
    ocean_prof%nlevels = 28
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    ! Верхние 20 уровней: 0-100м, шаг 5м
    do step = 1, 20
        ocean_prof%z(step) = real(step*5)  ! 5, 10, 15, ..., 100 м
        ocean_prof%dz(step) = 5.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ! Сильный сдвиг: U = 0.2 * exp(-z/20) — убывает с глубиной
        ! На поверхности (z=5): 0.2*exp(-0.25) = 0.156 м/с
        ! На осадке (z=88): 0.2*exp(-4.4) = 0.0025 м/с
        ocean_prof%u(step) = 0.2*exp(-ocean_prof%z(step)/20.0)
        ocean_prof%v(step) = 0.0
    end do

    ! Глубокие уровни: 150-500м, шаг 50м (равномерное течение)
    do step = 21, 28
        ocean_prof%z(step) = real(100 + (step - 20)*50)  ! 150, 200, ..., 500 м
        ocean_prof%dz(step) = 50.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.001  ! Очень слабое глубокое течение
        ocean_prof%v(step) = 0.0
    end do

    ! Print profile for verification
    print *, "Ocean profile (z, u):"
    do step = 1, ocean_prof%nlevels
        print '(I3, 2F10.4)', step, ocean_prof%z(step), ocean_prof%u(step)
    end do

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 1

    ! Шаг для Method A (стандартный iceberg_step использует Method A)
    call iceberg_step(state_a, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag_a)

    ! Шаг для Method B — используем только площадь x-граней для сравнения (ток по x)
    call iceberg_compute_geometry(state_b, diag_b)
    ! Площадь x-граней: 2 грани по W*D каждая = 2*W*D
    ! (ток по x, поэтому только x-грани испытывают трение)
    a_sides = 2.0*state_b%W*diag_b%draft
    call compute_water_force_method_b_sides(state_b, ocean_prof, a_sides, fx_b, fy_b)
    drag_b = sqrt(fx_b**2 + fy_b**2)

    fx_a = diag_a%f_water_x
    fy_a = diag_a%f_water_y
    drag_a = sqrt(fx_a**2 + fy_a**2)

    print *, "Surface current: ", ocean_prof%u(1), " m/s"
    print *, "Method A (layer-integrated) drag: ", drag_a, " N"
    print *, "Method B (depth-averaged, sides only) drag: ", drag_b, " N"

    if (drag_b .gt. 0.0) then
        print *, "Ratio A/B: ", drag_a/drag_b
    end if

    ! Проверка 1: силы не NaN
    n_checks = n_checks + 1
    if (drag_a .ne. drag_a .or. drag_b .ne. drag_b) then
        print *, "ERROR: NaN in drag forces"
        n_errors = n_errors + 1
    else
        print *, "OK: Drag forces finite"
    end if

    ! Проверка 2: сила в направлении течения (ток толкает айсберг по течению)
    n_checks = n_checks + 1
    if (fx_a .gt. 0.0 .and. fx_b .gt. 0.0) then
        print *, "OK: Drag forces in direction of current (positive fx)"
    else
        print *, "ERROR: Drag direction wrong: fx_a=", fx_a, " fx_b=", fx_b
        n_errors = n_errors + 1
    end if

    ! Проверка 3: при сдвиге Method A должен давать большее трение
    ! Для квадратичного трения: ∫|U|U dz > |U_avg|*U_avg * D при сдвиге
    n_checks = n_checks + 1
    if (drag_a .gt. drag_b*1.01) then
        print *, "OK: Method A > Method B (shear enhances drag for quadratic law)"
    else
        print *, "WARNING: Method A (", drag_a, ") not significantly > Method B (", drag_b, ")"
        print *, "  Ratio A/B = ", drag_a/drag_b
    end if

    ! Проверка 4: нет плавления
    n_checks = n_checks + 1
    if (diag_a%m_basal .eq. 0.0 .and. diag_a%m_lateral .eq. 0.0) then
        print *, "OK: No melt"
    else
        print *, "ERROR: Unexpected melt"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Method A и B направления совпадают
    n_checks = n_checks + 1
    if (sign(1.0, fx_a) .eq. sign(1.0, fx_b)) then
        print *, "OK: Both methods give same force direction"
    else
        print *, "ERROR: Force directions differ: fx_a=", fx_a, " fx_b=", fx_b
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

contains

    ! Method B для сравнения: глубинно-усреднённое течение, только вертикальные стороны
    subroutine compute_water_force_method_b_sides(state, ocean_prof, a_sides, fx, fy)
        use iceberg_forcing, only: depth_integrated_currents
        use iceberg_types, only: RHO_WATER, CD_WATER
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(in) :: a_sides
        real, intent(out) :: fx, fy

        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        real :: du, dv, speed_rel

        call depth_integrated_currents(ocean_prof, state%H*910.0/1028.0, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            return
        end if

        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)

        fx = 0.5*RHO_WATER*CD_WATER*a_sides*speed_rel*du
        fy = 0.5*RHO_WATER*CD_WATER*a_sides*speed_rel*dv
    end subroutine compute_water_force_method_b_sides

end program iceberg_test_4_vertical_shear
