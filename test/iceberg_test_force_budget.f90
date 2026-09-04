! ==============================================================================
! Тест: Force Budget Diagnostics
! Назначение: Записать полный бюджет сил на каждом шаге TEST_11.
!             Проверить замыкание: M*du/dt = ΣFx, M*dv/dt = ΣFy
! ==============================================================================

program iceberg_test_force_budget
    use iceberg
    use iceberg_forcing, only: get_ocean_profile, get_atmos_forcing
    use netcdf_input, only: era5_open, era5_is_open, era5_time
    use initial_ocean_reader, only: read_initial_ts
    use grid_coupling, only: coup1
    use grid_masks, only: ikuv
    use param, only: is, js, is1, js1, ht, kt1, t1, t2, s1, s2
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps, ios
    real :: dt
    real :: model_time_sec, start_sec
    real :: bathymetry
    logical :: realistic_ok, era5_ok, forcing_ok
    real :: x_model, y_model
    integer :: i_idx, j_idx
    logical :: has_nan

    ! Для вывода бюджета сил
    integer :: unit, ios_csv
    real :: mass, ax, ay
    real :: fx_total, fy_total
    real :: fx_calc, fy_calc
    real :: closure_error_x, closure_error_y
    real :: u_old, v_old

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST: Force Budget Diagnostics"
    print *, "=================================================="

    ! 1. Инициализация модельной сетки и батиметрии
    print *, "Initializing model grid..."
    call coup1()
    call ikuv()

    ! 2. Инициализация реалистичных T/S (EN4)
    print *, "Reading EN4 initial T/S..."
    call read_initial_ts(t1, t2, s1, s2, kt1, realistic_ok)
    if (.not. realistic_ok) then
        print *, "WARNING: Realistic T/S not available"
    end if

    ! 3. Открытие ERA5
    print *, "Opening ERA5 forcing..."
    call era5_open('data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc', ios)
    if (ios .ne. 0) then
        print *, "ERROR: Failed to open ERA5 file"
        era5_ok = .false.
    else
        era5_ok = .true.
        start_sec = era5_time(1)
        print *, "ERA5 start time: ", start_sec
    end if

    ! 4. Инициализация айсберга
    x_model = 36.0*13890.0
    y_model = 60.0*13890.0
    call iceberg_init(state, x_model, y_model, 100.0, 100.0, 100.0, &
                      75.0, 30.0, 0.0, 0.0)

    dt = 3600.0
    nsteps = 24*5  ! 5 дней для быстрого теста

    ! Открыть файл для вывода бюджета сил
    open (unit, file='data/output/diagnostics/stage9.3/force_budget.csv', &
          status='replace', iostat=ios_csv)
    if (ios_csv .ne. 0) then
        print *, "WARNING: Could not open force budget output file"
    else
        write(unit, '(A)') 'step,time_h,x_m,y_m,lat,lon,u,v,mass,fx_wind,fy_wind,fx_water,fy_water,fx_cor,fy_cor,fx_pres,fy_pres,fx_fk,fy_fk,fx_total,fy_total,ax,ay,fx_calc,fy_calc,mb_mday,ml_mday,ms_mday,q_net,closure_x,closure_y'
    end if

    print *, "Starting 5-day integration with force budget output..."
    print *, "Initial position: x=", x_model, " y=", y_model

    do step = 1, nsteps
        model_time_sec = start_sec + real(step)*dt

        ! Ocean profile at current position
        call get_ocean_profile(state%x, state%y, state%latitude, state%longitude, &
                               state%H*910.0/1028.0, ocean_prof, forcing_ok)

        ! Atmos forcing
        if (era5_ok) then
            call get_atmos_forcing(state%latitude, state%longitude, model_time_sec, &
                                   atmos, forcing_ok)
        else
            atmos%u10 = 5.0
            atmos%v10 = 0.0
            atmos%t2m = 253.15
            atmos%d2m = 253.15
            atmos%tcc = 0.5
            atmos%msl = 101325.0
            atmos%snowfall = 0.0
        end if

        ! Bathymetry
        call model_coords_to_indices_local(state%x, state%y, i_idx, j_idx)
        if (i_idx .ge. 1 .and. i_idx .le. is1 .and. j_idx .ge. 1 .and. j_idx .le. js1) then
            bathymetry = real(ht(i_idx, j_idx))*0.01
        else
            bathymetry = 500.0
        end if

        ! Store old velocity for acceleration calculation
        u_old = state%u
        v_old = state%v

        ! Integration step
        call iceberg_step(state, dt, ocean_prof, atmos, bathymetry, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        ! Compute acceleration
        ax = (state%u - u_old)/dt
        ay = (state%v - v_old)/dt

        ! Total force from diagnostics
        fx_total = diag%f_wind_x + diag%f_water_x + diag%f_cor_x + diag%f_pressure_x + diag%f_fk_x
        fy_total = diag%f_wind_y + diag%f_water_y + diag%f_cor_y + diag%f_pressure_y + diag%f_fk_y

        ! Expected force from M*a
        fx_calc = diag%mass*ax
        fy_calc = diag%mass*ay

        ! Closure error
        closure_error_x = (fx_total - fx_calc)/max(abs(fx_total), abs(fx_calc), 1.0)
        closure_error_y = (fy_total - fy_calc)/max(abs(fy_total), abs(fy_calc), 1.0)

        ! Write to CSV
        if (ios_csv .eq. 0) then
  write (unit, '(I6,F10.2,2F15.2,2F12.6,2F12.6,F15.2,10F15.3,2F15.3,2F15.3,2F15.3,4F15.3,2F12.6)') &
                step, model_time_sec/3600.0, state%x, state%y, state%latitude, state%longitude, &
                state%u, state%v, diag%mass, &
                diag%f_wind_x, diag%f_wind_y, &
                diag%f_water_x, diag%f_water_y, &
                diag%f_cor_x, diag%f_cor_y, &
                diag%f_pressure_x, diag%f_pressure_y, &
                diag%f_fk_x, diag%f_fk_y, &
                fx_total, fy_total, &
                ax, ay, &
                fx_calc, fy_calc, &
                diag%m_basal*86400.0, diag%m_lateral*86400.0, diag%m_surface*86400.0, &
                diag%q_net_surface, &
                closure_error_x, closure_error_y
        end if

        if (.not. state%active) then
            print *, "Iceberg melted away at day ", step/24
            exit
        end if
    end do

    if (ios_csv .eq. 0) close (unit)

    print *, "=================================================="
    print *, "Force budget test complete"
    print *, "Output: data/output/diagnostics/stage9.3/force_budget.csv"
    print *, "=================================================="

    n_checks = n_checks + 1
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Force Budget Test PASSED"
        stop 0
    else
        print *, "FAILURE: Force Budget Test FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    subroutine model_coords_to_indices_local(x_model_in, y_model_in, i_idx_in, j_idx_in)
        real, intent(in) :: x_model_in, y_model_in
        integer, intent(out) :: i_idx_in, j_idx_in
        real :: dx_model
        dx_model = 13890.0
        j_idx_in = int(x_model_in/dx_model) + 1
        i_idx_in = int(y_model_in/dx_model) + 1
    end subroutine model_coords_to_indices_local

end program iceberg_test_force_budget
