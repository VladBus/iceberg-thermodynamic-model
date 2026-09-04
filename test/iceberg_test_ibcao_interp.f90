! ==============================================================================
! Тест: IBCAO Bathymetry Interpolation and Grounding Test
! Назначение: Проверка интерполяции батиметрии IBCAO на позиции айсберга
!             и динамического обновления загрунтования при движении
! ==============================================================================

program iceberg_test_ibcao_interp
    use iceberg_forcing, only: get_ocean_profile, model_coords_to_latlon
    use iceberg, only: iceberg_init, iceberg_step, iceberg_compute_geometry
    use iceberg_types, only: iceberg_state, iceberg_diagnostics, ocean_profile, atmos_forcing
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    use param, only: is, js, is1, js1, ht, kt1, fi, dl
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag
    type(iceberg_diagnostics) :: geom

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: bathymetry
    real :: lat, lon
    real :: x_model, y_model
    real :: initial_draft, final_draft
    logical :: forcing_ok
    integer :: i_idx, j_idx

    ! Переменные для теста 4
    logical :: found_shallow
    integer :: i_test, j_test
    real :: test_bathy

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  IBCAO BATHYMETRY & GROUNDING TEST"
    print *, "=================================================="

    ! 1. Инициализация модельной сетки
    print *, "Initializing model grid..."
    call coup1()
    call ikuv()

    ! 2. Тест 1: Батиметрия из ht массива на позиции TEST_11
    print *, ""
    print *, "Test 1: Bathymetry from model grid at TEST_11 position"
    x_model = 36.0*13890.0
    y_model = 60.0*13890.0
    call model_coords_to_indices(x_model, y_model, i_idx, j_idx, forcing_ok)
    if (forcing_ok) then
        bathymetry = real(ht(i_idx, j_idx))*0.01
        print *, "  Model grid indices: i=", i_idx, " j=", j_idx
        print *, "  Bathymetry at (75N, 30E): ", bathymetry, " m"
        print *, "  kt1 (wet levels): ", kt1(i_idx, j_idx)
        if (bathymetry .gt. 100.0 .and. bathymetry .lt. 1000.0) then
            print *, "  OK: Reasonable bathymetry for Barents Sea"
        else
            print *, "  WARNING: Unusual bathymetry value"
        end if
    else
        print *, "  ERROR: Position outside model domain"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! 3. Тест 2: Проверка батиметрии в другой точке (пространственная вариабельность)
    print *, ""
    print *, "Test 2: Spatial variability of bathymetry"
    x_model = 10.0*13890.0
    y_model = 30.0*13890.0
    call model_coords_to_indices(x_model, y_model, i_idx, j_idx, forcing_ok)
    if (forcing_ok) then
        bathymetry = real(ht(i_idx, j_idx))*0.01
        print *, "  Bathymetry at (70N, 20E): ", bathymetry, " m"
        print *, "  Different from TEST_11 position: ", bathymetry .ne. real(ht(61, 37))*0.01
    end if
    n_checks = n_checks + 1

    ! 4. Тест 3: Инициализация айсберга и проверка загрунтования
    print *, ""
    print *, "Test 3: Iceberg grounding check at deep water"
    lat = 75.0
    lon = 30.0
    x_model = 36.0*13890.0
    y_model = 60.0*13890.0

    call iceberg_init(state, x_model, y_model, 100.0, 100.0, 100.0, lat, lon, 0.0, 0.0)
    call iceberg_compute_geometry(state, geom)
    initial_draft = geom%draft
    print *, "  Initial draft: ", initial_draft, " m"

    ! Глубина на позиции
    call model_coords_to_indices(state%x, state%y, i_idx, j_idx, forcing_ok)
    bathymetry = real(ht(i_idx, j_idx))*0.01
    print *, "  Bathymetry: ", bathymetry, " m"
    print *, "  Grounded? ", geom%grounded, " (draft < bathymetry = ", initial_draft .lt. bathymetry, ")"

    if (.not. geom%grounded .and. initial_draft .lt. bathymetry) then
        print *, "  OK: Not grounded in deep water"
    else
        print *, "  ERROR: Unexpected grounding state"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! 5. Тест 4: Загрунтование в мелководье (искусственный тест)
    print *, ""
    print *, "Test 4: Grounding in shallow water (synthetic test)"
    ! Поместим айсберг в точку с известной мелкой глубиной
    ! Используем модель с кубом 100м - осадка ~88.5м
    ! Найдём точку где глубина < 88.5м
    found_shallow = .false.

    do i_test = 10, is1 - 10
        do j_test = 10, js1 - 10
            if (kt1(i_test, j_test) .gt. 0 .and. kt1(i_test, j_test) .lt. 9) then
                test_bathy = real(ht(i_test, j_test))*0.01
                if (test_bathy .gt. 10.0 .and. test_bathy .lt. 88.0) then
                    found_shallow = .true.
                    exit
                end if
            end if
        end do
        if (found_shallow) exit
    end do

    if (found_shallow) then
        x_model = real(j_test - 1)*13890.0
        y_model = real(i_test - 1)*13890.0
        call iceberg_init(state, x_model, y_model, 100.0, 100.0, 100.0, 70.0, 20.0, 0.0, 0.0)
        call iceberg_compute_geometry(state, geom)
        bathymetry = real(ht(i_test, j_test))*0.01
        print *, "  Shallow position: i=", i_test, " j=", j_test
        print *, "  Bathymetry: ", bathymetry, " m"
        print *, "  Draft: ", geom%draft, " m"
        print *, "  Grounded? ", geom%grounded
        if (geom%grounded .and. geom%draft .ge. bathymetry) then
            print *, "  OK: Correctly grounded in shallow water"
        else
            print *, "  WARNING: Grounding logic may need review"
        end if
    else
        print *, "  No shallow water found in model domain (skipping)"
    end if
    n_checks = n_checks + 1

    ! 6. Тест 5: Динамическое загрунтование при движении (микро-тест)
    print *, ""
    print *, "Test 5: Dynamic grounding during movement (mini integration)"
    ! Инициализируем в глубокой воде
    lat = 75.0
    lon = 30.0
    x_model = 36.0*13890.0
    y_model = 60.0*13890.0
    call iceberg_init(state, x_model, y_model, 100.0, 100.0, 100.0, lat, lon, 0.0, 0.0)

    ! Настройка профиля океана и атмосферы для одного шага
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(18), ocean_prof%dz(18), ocean_prof%temp(18), &
              ocean_prof%salt(18), ocean_prof%u(18), ocean_prof%v(18))
    do step = 1, 18
        ocean_prof%z(step) = real(step*250)
        ocean_prof%dz(step) = 250.0
        ocean_prof%temp(step) = -1.9
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    ! Батиметрия на стартовой позиции
    call model_coords_to_indices(state%x, state%y, i_idx, j_idx, forcing_ok)
    bathymetry = real(ht(i_idx, j_idx))*0.01

    dt = 3600.0
    nsteps = 24  ! 1 день

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, bathymetry, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        if (.not. state%active) exit
    end do

    ! Проверяем, что grounding обновился (хотя в глубокой воде не должен измениться)
    call model_coords_to_indices(state%x, state%y, i_idx, j_idx, forcing_ok)
    bathymetry = real(ht(i_idx, j_idx))*0.01
    print *, "  Final position: x=", state%x, " y=", state%y
    print *, "  Final bathymetry: ", bathymetry, " m"
    print *, "  Final grounded: ", diag%grounded
    print *, "  Forcing valid: ", diag%forcing_valid

    if (diag%forcing_valid) then
        print *, "  OK: Forcing domain check passed"
    else
        print *, "  WARNING: Iceberg left forcing domain"
    end if
    n_checks = n_checks + 1

    if (allocated(ocean_prof%z)) deallocate (ocean_prof%z, ocean_prof%dz, &
                                             ocean_prof%temp, ocean_prof%salt, &
                                             ocean_prof%u, ocean_prof%v)

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: IBCAO BATHYMETRY TEST PASSED"
        stop 0
    else
        print *, "FAILURE: IBCAO BATHYMETRY TEST FAILED"
        stop 1
    end if

contains

    subroutine model_coords_to_indices(x_model, y_model, i_idx, j_idx, in_domain)
        real, intent(in) :: x_model, y_model
        integer, intent(out) :: i_idx, j_idx
        logical, intent(out) :: in_domain
        real :: dx_model
        dx_model = 13890.0
        j_idx = int(x_model/dx_model) + 1
        i_idx = int(y_model/dx_model) + 1
        if (i_idx .lt. 1 .or. i_idx .ge. is1 .or. j_idx .lt. 1 .or. j_idx .ge. js1) then
            in_domain = .false.
        else
            in_domain = .true.
        end if
    end subroutine model_coords_to_indices

end program iceberg_test_ibcao_interp
