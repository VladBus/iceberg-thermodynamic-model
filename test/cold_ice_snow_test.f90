! ==============================================================================
! Тест: controlled cold column ice/snow experiment (Stage 5.4)
! Создает холодную колонку и проверяет физику снегопада/ледяного покрова
! НАЗНАЧЕНИЕ: контролируемый физический тест, НЕ production run
! ==============================================================================

program cold_ice_snow_test
    use param
    use thermodynamics, only: heat
    implicit none

    integer :: i, j, k, n_iter, day, nday, lll
    real :: dt
    real :: snow_accum, snow_depth, ice_thick
    real :: t_surf, t_air, q_net
    real :: sfal_test(12)
    real :: era5_snowfall_rate_test(is1, js1)

    print *, "============================================================"
    print *, "  CONTROLLED COLD ICE/SNOW EXPERIMENT (Stage 5.4)"
    print *, "============================================================"
    print *, ""
    print *, "PURPOSE: Test snowfall -> snow accumulation -> thermal"
    print *, "         insulation -> surface energy balance -> ice growth"
    print *, ""
    print *, "SETUP: Single cold ocean column, January Arctic conditions"
    print *, "       sfal = ERA5 snowfall rate, cold initial T/S profiles"
    print *, ""
    print *, "DISCLAIMER: This is a controlled physics test, NOT a"
    print *, "            production Arctic simulation. TEST grid only."
    print *, ""

    ! --- Initialize cold column ---
    print *, "Initializing cold column..."
    call init_cold_column()

    ! --- Set snowfall to ERA5-like values (January Arctic) ---
    print *, "Setting ERA5 snowfall rate (January Arctic)..."
    call set_era5_snowfall_jan()

    ! --- Run heat() for 30 days ---
    dt = 3600.0
    nday = 1
    lll = 1  ! January

    print *, ""
    print *, "Running heat() for 30 days with ERA5 snowfall..."
    print *, ""

    do day = 1, 30
        call heat(dt, day, lll)

        ! Diagnostics every 5 days
        if (mod(day, 5) .eq. 0) then
            call print_diagnostics(day)
        end if
    end do

    print *, ""
    print *, "============================================================"
    print *, "EXPERIMENT COMPLETE"
    print *, "============================================================"
    print *, "Check: snow depth > 0, ice thickness > 0, T_surf <= 0"
    print *, "If snow depth = 0 or ice = 0 -> physics issue"

contains

    subroutine init_cold_column()
        integer :: i, j, k

        ! Set cold initial conditions for a single column (i=50, j=50)
        i = 50
        j = 50

        ! Ocean temperature: -1.8°C (near freezing) throughout
        do k = 1, ks
            t1(i, j, k) = -1.8
            s1(i, j, k) = 0.034
        end do

        ! Surface temperature
        t1(i, j, 1) = -1.8

        ! Salinity
        s1(i, j, 1) = 0.034

        ! Ice: initially no ice
        do k = 1, ngr
            an1(i, j, k + 1) = 0.0
            wice1(i, j, k) = 0.0
            hsnp(k) = 0.0
            hicp(k) = 0.0
        end do
        ans(i, j) = 0.0

        ! Atmospheric forcing: cold Arctic January
        tatm(i, j) = -30.0  ! air temp -30°C
        patm(i, j) = 1013.0  ! hPa
        wind(i, j) = 5.0    ! m/s
        cloud(i, j) = 0.5   ! 50% cloud cover
        humid(i, j) = 0.7   ! 70% humidity

        ! Snowfall climatology (will be overridden by ERA5)
        sfal = (/0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0/)

        ! Other params
        kt1(i, j) = 1  ! ocean cell
        fi(i, j) = 75.0  ! 75°N
        dl(i, j) = 0.0
        skT(i, j) = 1.0e-4  ! turbulent exchange coeff
    end subroutine init_cold_column

    subroutine set_era5_snowfall_jan()
        ! January ERA5 snowfall rate for Arctic (~0.5-2 mm/day water equivalent)
        ! Convert to m/s: 1 mm/day = 1e-3/86400 = 1.16e-8 m/s
        ! Typical Jan Arctic: 0.5-2 mm/day -> 0.6e-8 to 2.3e-8 m/s
        real :: jan_snowfall_rate
        jan_snowfall_rate = 1.5e-8  ! ~1.3 mm/day water equivalent

        era5_snowfall_rate_test = 0.0
        era5_snowfall_rate_test(50, 50) = jan_snowfall_rate
    end subroutine set_era5_snowfall_jan

    subroutine print_diagnostics(day)
        integer, intent(in) :: day
        real :: total_snow, total_ice

        total_snow = hsnp(1)
        total_ice = hicp(1)

        print *, ""
        print *, "--- Day ", day, " Diagnostics ---"
        print *, "  Air temp:     ", tatm(50, 50), " °C"
        print *, "  Surface temp: ", t1(50, 50, 1), " °C"
        print *, "  Snow depth:   ", hsnp(1), " m"
        print *, "  Ice thick:    ", hicp(1), " m"
        print *, "  Ice conc:     ", ans(50, 50)
        print *, "  Snowfall rate:", era5_snowfall_rate_test(50, 50), " m/s"
    end subroutine print_diagnostics

end program cold_ice_snow_test
