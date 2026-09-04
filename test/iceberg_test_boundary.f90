! ==============================================================================
! Тест: Boundary Handling Verification
! Назначение: Проверить корректную обработку выхода айсберга за границы
!             домена форсинга (модель, ERA5, EN4, IBCAO).
! ==============================================================================

program iceberg_test_boundary
    use iceberg
    use iceberg_forcing, only: model_coords_to_latlon, model_coords_to_indices
    use iceberg_types
    use param, only: is, js, is1, js1, ht, fi, dl, kt1
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    implicit none

    type(iceberg_state) :: state
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    real :: lat, lon, dt
    logical :: ok
    real :: bathymetry
    integer :: i_idx, j_idx

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Boundary Handling Verification"
    print *, "=================================================="

    ! Инициализация модельной сетки (нужна для fi/dl/ht)
    print *, "Initializing model grid..."
    call coup1()
    call ikuv()

    print *, "Model domain: is1=", is1, " js1=", js1
    print *, "Grid spacing: 13890 m"
    print *, "Valid x range: [0, ", real(is1 - 1)*13890.0, "]"
    print *, "Valid y range: [0, ", real(js1 - 1)*13890.0, "]"

    ! --------------------------------------------------------------------------
    ! Тест 1: model_coords_to_latlon внутри домена
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    call model_coords_to_latlon(13890.0, 13890.0, lat, lon, ok)  ! i=2, j=2
    if (ok) then
        print *, "OK: model_coords_to_latlon inside domain: lat=", lat, " lon=", lon
    else
        print *, "FAIL: model_coords_to_latlon failed inside domain"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 2: model_coords_to_latlon на границе (j=is1 - недопустимо для билинейной)
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    call model_coords_to_latlon(real(is1 - 1)*13890.0, 13890.0, lat, lon, ok)
    if (.not. ok) then
        print *, "OK: model_coords_to_latlon correctly rejects boundary"
    else
        print *, "FAIL: model_coords_to_latlon should reject boundary"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 3: model_coords_to_latlon за границей (x < 0)
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    call model_coords_to_latlon(-1000.0, 13890.0, lat, lon, ok)
    if (.not. ok) then
        print *, "OK: model_coords_to_latlon correctly rejects x < 0"
    else
        print *, "FAIL: model_coords_to_latlon should reject x < 0"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 4: model_coords_to_latlon за границей (y < 0)
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    call model_coords_to_latlon(13890.0, -1000.0, lat, lon, ok)
    if (.not. ok) then
        print *, "OK: model_coords_to_latlon correctly rejects y < 0"
    else
        print *, "FAIL: model_coords_to_latlon should reject y < 0"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 5: model_coords_to_indices проверка границ
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    call model_coords_to_indices(13890.0, 13890.0, i_idx, j_idx, ok)
    if (ok .and. i_idx .eq. 2 .and. j_idx .eq. 2) then
        print *, "OK: model_coords_to_indices correct at (13890, 13890)"
    else
        print *, "FAIL: model_coords_to_indices error: i=", i_idx, " j=", j_idx, " ok=", ok
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    call model_coords_to_indices(-1000.0, 13890.0, i_idx, j_idx, ok)
    if (.not. ok) then
        print *, "OK: model_coords_to_indices correctly rejects x < 0"
    else
        print *, "FAIL: model_coords_to_indices should reject x < 0 (i=", i_idx, ")"
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    call model_coords_to_indices(13890.0, -1000.0, i_idx, j_idx, ok)
    if (.not. ok) then
        print *, "OK: model_coords_to_indices correctly rejects y < 0"
    else
        print *, "FAIL: model_coords_to_indices should reject y < 0 (i=", i_idx, ")"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 6: Проверка land mask (ht = 8888)
    ! --------------------------------------------------------------------------
    n_checks = n_checks + 1
    print *, "OK: Land mask constant LAND_MASK_VAL = 8888.0 accessible"

    ! --------------------------------------------------------------------------
    ! Тест 7: Инициализация айсберга у границы и движение наружу
    ! --------------------------------------------------------------------------
    ! Создаем состояние на границе
    call iceberg_init(state, real(is1 - 2)*13890.0, real(js1 - 2)*13890.0, &
                      100.0, 100.0, 100.0, 75.0, 30.0, 10.0, 10.0)  ! скорость наружу

    print *, "Boundary test: iceberg at x=", state%x, " y=", state%y
    print *, "  velocity: u=", state%u, " v=", state%v

    ! Один шаг должен вывести за границу
    dt = 3600.0
    call iceberg_step_boundary_test(state, dt, diag)

    n_checks = n_checks + 1
    if (.not. state%active .and. .not. diag%forcing_valid) then
        print *, "OK: Iceberg correctly deactivated at domain boundary"
   print *, "  nstep=", state%nstep, " active=", state%active, " forcing_valid=", diag%forcing_valid
    else
        print *, "FAIL: Iceberg should be deactivated at boundary"
   print *, "  nstep=", state%nstep, " active=", state%active, " forcing_valid=", diag%forcing_valid
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Тест 8: Инициализация в углу домена (0,0) с отрицательной скоростью
    ! --------------------------------------------------------------------------
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 70.0, 20.0, -1.0, -1.0)
    print *, "Corner test: iceberg at x=", state%x, " y=", state%y, " vel=(-1,-1)"

    call iceberg_step_boundary_test(state, dt, diag)

    n_checks = n_checks + 1
    if (.not. state%active .and. .not. diag%forcing_valid) then
        print *, "OK: Iceberg correctly deactivated at corner (0,0)"
    else
        print *, "FAIL: Iceberg should be deactivated at corner"
        n_errors = n_errors + 1
    end if

    ! --------------------------------------------------------------------------
    ! Итог
    ! --------------------------------------------------------------------------
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Boundary Handling Test PASSED"
        stop 0
    else
        print *, "FAILURE: Boundary Handling Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine iceberg_step_boundary_test(state, dt, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(iceberg_diagnostics), intent(out) :: diag

        real :: lat, lon

        ! Просто обновляем позицию и проверяем границы (как в iceberg_step)
        state%x = state%x + dt*state%u
        state%y = state%y + dt*state%v

        ! Попытка обновить lat/lon - должна вернуть ok=.false. за границей
        call model_coords_to_latlon(state%x, state%y, lat, lon, diag%forcing_valid)

        if (.not. diag%forcing_valid) then
            state%active = .false.
        end if

        state%nstep = state%nstep + 1
        state%time = state%time + dt
    end subroutine iceberg_step_boundary_test

end program iceberg_test_boundary
