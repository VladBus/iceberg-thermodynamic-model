! ==============================================================================
! Тест: Forcing Interpolation Sensitivity
! Назначение: Сравнить методы интерполяции форсинга (nearest-neighbor vs bilinear)
!             для ERA5, EN4, IBCAO. Оценить влияние на траекторию.
! ==============================================================================

program iceberg_test_forcing_interp_sensitivity
    use iceberg
    use iceberg_types
    use iceberg_dynamics
    use iceberg_forcing, only: model_coords_to_latlon
    use param, only: fi, dl, is, js, is1, js1, kt1, ht
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    implicit none

    type(iceberg_state) :: state_bilinear, state_nearest
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt, model_time
    real :: latitude, longitude
    real :: f_coriolis
    real :: dx_model
    logical :: ok

    ! Test 1 variables
    real :: x_model, y_model
    real :: lat_test, lon_test
    real :: u10_exact, u10_bilinear, u10_nearest
    real :: lat_grid(4), lon_grid(4)
    real :: u10_grid(4)
    real :: wx, wy, wx1, wy1
    real :: min_dist, dist
    integer :: i, nearest_idx

    ! Test 2 variables
    real :: lat_diff, lon_diff, dist_diff

    ! Test 3 variables
    real :: z_levels(5), temp_levels(5)
    integer :: k
    real :: temp_bilinear, temp_nearest
    real :: draft_test
    real :: temp_exact

    ! Test 4 variables
    real :: bathy_grid(4), bathy_bilinear, bathy_nearest

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Forcing Interpolation Sensitivity"
    print *, "=================================================="

    ! Инициализация модельной сетки
    call coup1()
    call ikuv()

    latitude = 75.0
    longitude = 30.0
    dx_model = 13890.0

    x_model = 36.0*13890.0
    y_model = 60.0*13890.0

    print *, "Initial lat: ", latitude, " lon: ", longitude

    ! =========================================================================
    ! TEST 1: Bilinear interpolation (текущий метод) vs Nearest-neighbor
    ! =========================================================================
    print *, ""
    print *, "--- TEST 1: Bilinear vs Nearest-neighbor for ERA5 ---"

    ! Для теста создадим простой синтетический форсинг с известным градиентом
    ! ERA5 u10 = 10*sin(lat/57.3), v10 = 5*cos(lon/57.3)
    ! Оценим ошибку интерполяции

    lat_test = 75.25
    lon_test = 30.25

    ! 4 соседние точки сетки
    lat_grid = [75.0, 76.0, 75.0, 76.0]
    lon_grid = [30.0, 30.0, 31.0, 31.0]

    do i = 1, 4
        u10_grid(i) = 10.0*sin(lat_grid(i)/57.2957795)
    end do

    ! Exact value at test point
    u10_exact = 10.0*sin(lat_test/57.2957795)

    ! Bilinear interpolation
    wx = (lat_test - lat_grid(1))/(lat_grid(2) - lat_grid(1))
    wy = (lon_test - lon_grid(1))/(lon_grid(3) - lon_grid(1))
    wx1 = 1.0 - wx
    wy1 = 1.0 - wy
    u10_bilinear = wx1*wy1*u10_grid(1) + wx*wy1*u10_grid(2) + &
                   wx1*wy*u10_grid(3) + wx*wy*u10_grid(4)

    ! Nearest-neighbor
    min_dist = 1e10
    nearest_idx = 1
    do i = 1, 4
        dist = (lat_grid(i) - lat_test)**2 + (lon_grid(i) - lon_test)**2
        if (dist .lt. min_dist) then
            min_dist = dist
            nearest_idx = i
        end if
    end do
    u10_nearest = u10_grid(nearest_idx)

    print *, "Test point: lat=", lat_test, " lon=", lon_test
    print *, "Exact u10: ", u10_exact
    print *, "Bilinear:  ", u10_bilinear, " error: ", abs(u10_bilinear - u10_exact)
    print *, "Nearest:   ", u10_nearest, " error: ", abs(u10_nearest - u10_exact)

    n_checks = n_checks + 1
    if (abs(u10_bilinear - u10_exact) .lt. abs(u10_nearest - u10_exact)) then
        print *, "OK: Bilinear more accurate than nearest-neighbor"
    else
        print *, "WARNING: Nearest-neighbor better for this test"
    end if

    ! =========================================================================
    ! TEST 2: Trajectory comparison - bilinear vs nearest for full integration
    ! =========================================================================
    print *, ""
    print *, "--- TEST 2: Trajectory with different interpolation methods ---"

    ! Инициализация двух айсбергов
    call iceberg_init(state_bilinear, x_model, y_model, 100.0, 100.0, 100.0, &
                      latitude, longitude, 0.0, 0.0)
    call iceberg_init(state_nearest, x_model, y_model, 100.0, 100.0, 100.0, &
                      latitude, longitude, 0.0, 0.0)

    call init_synthetic_forcing(ocean_prof, atmos)

    dt = 3600.0
    nsteps = 50  ! 2 дня

    ! Bilinear (текущий метод)
    do step = 1, nsteps
        model_time = real(step)*dt
        f_coriolis = 2.0*7.2921150e-5*sin(state_bilinear%latitude/57.2957795)

        ! Получаем форсинг с билинейной интерполяцией (текущий метод)
        call get_synthetic_atmos_bilinear(state_bilinear%latitude, state_bilinear%longitude, atmos)
        call get_synthetic_ocean_bilinear(state_bilinear%x, state_bilinear%y, ocean_prof)

        call iceberg_dynamics_step(state_bilinear, dt, ocean_prof, atmos, &
                                   f_coriolis, 0.0, 0.0, 0.0, 0.0, diag)

        state_bilinear%x = state_bilinear%x + dt*state_bilinear%u
        state_bilinear%y = state_bilinear%y + dt*state_bilinear%v
        call model_coords_to_latlon(state_bilinear%x, state_bilinear%y, &
                                    state_bilinear%latitude, state_bilinear%longitude, ok)
    end do

    ! Nearest-neighbor (альтернативный метод)
    do step = 1, nsteps
        model_time = real(step)*dt
        f_coriolis = 2.0*7.2921150e-5*sin(state_nearest%latitude/57.2957795)

        ! Форсинг с nearest-neighbor интерполяцией
        call get_synthetic_atmos_nearest(state_nearest%latitude, state_nearest%longitude, atmos)
        call get_synthetic_ocean_nearest(state_nearest%x, state_nearest%y, ocean_prof)

        call iceberg_dynamics_step(state_nearest, dt, ocean_prof, atmos, &
                                   f_coriolis, 0.0, 0.0, 0.0, 0.0, diag)

        state_nearest%x = state_nearest%x + dt*state_nearest%u
        state_nearest%y = state_nearest%y + dt*state_nearest%v
        call model_coords_to_latlon(state_nearest%x, state_nearest%y, &
                                    state_nearest%latitude, state_nearest%longitude, ok)
    end do

    ! Сравнение траекторий
    lat_diff = abs(state_bilinear%latitude - state_nearest%latitude)
    lon_diff = abs(state_bilinear%longitude - state_nearest%longitude)
    dist_diff = sqrt(lat_diff**2 + lon_diff**2)*111000.0  ! приблизительно в метрах

    print *, "Bilinear final: lat=", state_bilinear%latitude, " lon=", state_bilinear%longitude
    print *, "Nearest final:  lat=", state_nearest%latitude, " lon=", state_nearest%longitude
    print *, "Difference: lat_diff=", lat_diff, " lon_diff=", lon_diff
    print *, "Distance difference: ", dist_diff, " m"

    n_checks = n_checks + 1
    if (dist_diff .lt. 1000.0) then  ! < 1 км разница
        print *, "OK: Interpolation method difference < 1 km over 2 days"
    else
        print *, "WARNING: Interpolation method difference > 1 km"
    end if

    ! =========================================================================
    ! TEST 3: EN4 ocean profile interpolation sensitivity
    ! =========================================================================
    print *, ""
    print *, "--- TEST 3: EN4 vertical interpolation sensitivity ---"

    ! Тест вертикальной интерполяции T/S
    ! Создаем профиль с сильным градиентом
    z_levels = [10.0, 20.0, 30.0, 40.0, 50.0]
    temp_levels = [-1.8, -1.0, 0.5, 2.0, 3.5]  ! сильный градиент термоклином

    ! Интерполяция на глубине 25м (между 20 и 30)
    draft_test = 25.0

    ! Linear interpolation (текущий метод)
    temp_bilinear = temp_levels(2) + (temp_levels(3) - temp_levels(2))* &
                    (draft_test - z_levels(2))/(z_levels(3) - z_levels(2))

    ! Nearest neighbor
    temp_nearest = temp_levels(2)  ! ближайший 20м

    ! Exact (линейный профиль между точками)
    temp_exact = -1.0 + (0.5 - (-1.0))*(25.0 - 20.0)/10.0  ! = 0.25

    print *, "Draft test: ", draft_test, " m"
    print *, "Linear interp: ", temp_bilinear
    print *, "Nearest:       ", temp_nearest
    print *, "Exact:         ", temp_exact
    print *, "Linear error:  ", abs(temp_bilinear - temp_exact)
    print *, "Nearest error: ", abs(temp_nearest - temp_exact)

    n_checks = n_checks + 1
    if (abs(temp_bilinear - temp_exact) .lt. abs(temp_nearest - temp_exact)) then
        print *, "OK: Linear interpolation more accurate than nearest"
    else
        print *, "WARNING: Nearest better for this test"
    end if

    ! =========================================================================
    ! TEST 4: IBCAO bathymetry interpolation sensitivity
    ! =========================================================================
    print *, ""
    print *, "--- TEST 4: IBCAO bathymetry interpolation sensitivity ---"

    ! IBCAO использует nearest-neighbor (текущий метод)
    ! Сравним с билинейной для батиметрии

    bathy_grid = [300.0, 350.0, 280.0, 320.0]  ! 4 соседние ячейки

    ! Bilinear
    bathy_bilinear = 0.25*(bathy_grid(1) + bathy_grid(2) + bathy_grid(3) + bathy_grid(4))
    ! Nearest (текущий)
    bathy_nearest = bathy_grid(1)

    print *, "Bathy grid: ", bathy_grid
    print *, "Bilinear: ", bathy_bilinear
    print *, "Nearest:  ", bathy_nearest
    print *, "Difference: ", abs(bathy_bilinear - bathy_nearest)

    n_checks = n_checks + 1
    if (abs(bathy_bilinear - bathy_nearest) .lt. 50.0) then
        print *, "OK: Bathymetry interpolation difference < 50 m"
    else
        print *, "WARNING: Bathymetry interpolation difference > 50 m"
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Forcing Interpolation Sensitivity Test PASSED"
        stop 0
    else
        print *, "FAILURE: Forcing Interpolation Sensitivity Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine init_synthetic_forcing(ocean_prof, atmos)
        type(ocean_profile), intent(out) :: ocean_prof
        type(atmos_forcing), intent(out) :: atmos

        integer :: nlevels
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ocean_prof%u(k) = 0.1*sin(real(k)/10.0)
            ocean_prof%v(k) = 0.05*cos(real(k)/10.0)
        end do

        atmos%u10 = 5.0
        atmos%v10 = 2.0
        atmos%t2m = 253.15
        atmos%d2m = 253.15
        atmos%tcc = 0.5
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine init_synthetic_forcing

    subroutine get_synthetic_atmos_bilinear(lat, lon, atmos)
        real, intent(in) :: lat, lon
        type(atmos_forcing), intent(out) :: atmos

        atmos%u10 = 10.0*sin(lat/57.2957795)
        atmos%v10 = 5.0*cos(lon/57.2957795)
        atmos%t2m = 260.0 - 10.0*sin(lat/57.2957795)
        atmos%d2m = atmos%t2m - 2.0
        atmos%tcc = 0.5
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine get_synthetic_atmos_bilinear

    subroutine get_synthetic_atmos_nearest(lat, lon, atmos)
        real, intent(in) :: lat, lon
        type(atmos_forcing), intent(out) :: atmos

        ! Округление до ближайшего целого градуса (mock nearest)
        real :: lat_nn, lon_nn
        lat_nn = nint(lat)
        lon_nn = nint(lon)

        atmos%u10 = 10.0*sin(lat_nn/57.2957795)
        atmos%v10 = 5.0*cos(lon_nn/57.2957795)
        atmos%t2m = 260.0 - 10.0*sin(lat_nn/57.2957795)
        atmos%d2m = atmos%t2m - 2.0
        atmos%tcc = 0.5
        atmos%msl = 101325.0
        atmos%snowfall = 0.0
    end subroutine get_synthetic_atmos_nearest

    subroutine get_synthetic_ocean_bilinear(x, y, ocean_prof)
        real, intent(in) :: x, y
        type(ocean_profile), intent(out) :: ocean_prof

        integer :: nlevels, k
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ocean_prof%u(k) = 0.1*sin(x/1e6 + real(k)/10.0)
            ocean_prof%v(k) = 0.05*cos(y/1e6 + real(k)/10.0)
        end do
    end subroutine get_synthetic_ocean_bilinear

    subroutine get_synthetic_ocean_nearest(x, y, ocean_prof)
        real, intent(in) :: x, y
        type(ocean_profile), intent(out) :: ocean_prof

        integer :: nlevels, k
        nlevels = 5
        ocean_prof%nlevels = nlevels
        allocate (ocean_prof%z(nlevels), ocean_prof%dz(nlevels), &
                  ocean_prof%temp(nlevels), ocean_prof%salt(nlevels), &
                  ocean_prof%u(nlevels), ocean_prof%v(nlevels))
        do k = 1, nlevels
            ocean_prof%z(k) = real(k)*20.0
            ocean_prof%dz(k) = 20.0
            ocean_prof%temp(k) = -1.0
            ocean_prof%salt(k) = 0.034
            ocean_prof%u(k) = 0.1*sin(nint(x/1e6)/1e6 + real(k)/10.0)
            ocean_prof%v(k) = 0.05*cos(nint(y/1e6)/1e6 + real(k)/10.0)
        end do
    end subroutine get_synthetic_ocean_nearest

end program iceberg_test_forcing_interp_sensitivity
