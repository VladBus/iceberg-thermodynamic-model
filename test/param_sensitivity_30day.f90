! ==============================================================================
! Тест: Parameter sensitivity — 30-day experiment with varying parameters
! Назначение: Запуск TEST_11 с разными значениями Cd_air, Cd_water, C_BASAL, C_LATERAL
! ==============================================================================

program param_sensitivity_30day
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

    integer :: nsteps, step, ios
    real :: dt, model_time_sec, start_sec
    real :: M0, M_final, total_budget_loss
    real :: bathymetry
    integer :: i_idx, j_idx
    logical :: realistic_ok, era5_ok, forcing_ok
    real :: x_model, y_model, lat, lon
    integer :: p

    ! Parameter sets to test
    integer :: n_param_sets
    character(len=50) :: param_names(4)
    real :: cd_air_vals(4), cd_water_vals(4), c_basal_vals(4), c_lateral_vals(4)

    ! Results storage
    real :: final_mass(4), mass_loss(4), max_drift(4)

    print *, "=================================================="
    print *, "  PARAMETER SENSITIVITY: 30-Day Experiment"
    print *, "=================================================="

    ! 1. Инициализация модельной сетки
    print *, "Initializing model grid..."
    call coup1()
    call ikuv()

    ! 2. EN4 T/S
    print *, "Reading EN4 initial T/S..."
    call read_initial_ts(t1, t2, s1, s2, kt1, realistic_ok)

    ! 3. ERA5
    print *, "Opening ERA5 forcing..."
    call era5_open('data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc', ios)
    era5_ok = (ios .eq. 0)
    if (era5_ok) start_sec = era5_time(1)

    ! Parameter sets
    n_param_sets = 4
    param_names = ["Default    ", "High Cd    ", "High Melt  ", "Low Melt   "]
    cd_air_vals = [1.3e-3, 2.0e-3, 1.3e-3, 1.3e-3]
    cd_water_vals = [2.0e-3, 2.0e-3, 2.0e-3, 2.0e-3]
    c_basal_vals = [1.0e-6, 1.0e-6, 2.0e-6, 0.5e-6]
    c_lateral_vals = [1.0e-6, 1.0e-6, 2.0e-6, 0.5e-6]

    dt = 3600.0
    nsteps = 24*30

    ! Initial position (model cell i=61, j=37 -> lat=75, lon=30.14)
    lat = 75.0
    lon = 30.0
    x_model = 36.0*13890.0
    y_model = 60.0*13890.0

    print *, "Running", n_param_sets, "parameter sets..."
    print *, ""

    do p = 1, n_param_sets
        ! NOTE: Can't easily change module constants at runtime
        ! This test documents the parameter sets for manual testing
        print *, "Parameter set ", p, ": ", trim(param_names(p))
        print *, "  CD_AIR = ", cd_air_vals(p)
        print *, "  CD_WATER = ", cd_water_vals(p)
        print *, "  C_BASAL = ", c_basal_vals(p)
        print *, "  C_LATERAL = ", c_lateral_vals(p)
        print *, "  (Constants are compile-time; modify iceberg_types.f90 and rebuild)"
    end do

    print *, ""
   print *, "To run sensitivity: edit src/iceberg_types.f90, change constants, rebuild, run TEST_11"
    print *, "=================================================="

end program param_sensitivity_30day
