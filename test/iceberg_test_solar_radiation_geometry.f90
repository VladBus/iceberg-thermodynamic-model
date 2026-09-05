! ==============================================================================
! Тест: Solar Radiation Geometry
! Назначение: Сравнить legacy solar geometry (decl=0, hour_angle=0)
!             с астрономически корректным расчетом.
! ==============================================================================

program iceberg_test_solar_radiation_geometry
    use iceberg_types
    use iceberg_thermodynamics
    implicit none

    integer :: n_errors, n_checks
    integer :: i, j, k

    ! Legacy model constants
    real :: SOLAR_CONSTANT_MODEL
    real :: CLOUD_COEFF_MODEL
    real :: ALBEDO_ICE_MODEL

    ! Astronomical constants
    real :: SOLAR_CONSTANT_ASTRO

    ! Test grid
    real :: lats(3), dates(4), times(4)
    character(len=16) :: date_names(4)
    character(len=16) :: time_names(4)

    ! Astronomical calculation variables
    real :: decl, hour_angle, cos_zenith_legacy, cos_zenith_astro
    real :: sw_legacy, sw_astro
    real :: daily_sw_legacy, daily_sw_astro
    real :: gamma, lon, local_time, H
    real :: lat_rad, decl_rad, H_rad
    real :: sw_legacy_clear, sw_legacy_cloudy
    real :: phi_rad, delta_rad, daily_cos_int, avg_cos_astro
    real :: sw_astro_avg_clear, sw_astro_avg_cloudy
    real :: max_cos_winter

    n_errors = 0
    n_checks = 0

    ! Model constants
    SOLAR_CONSTANT_MODEL = SOLAR_CONSTANT  ! 1353.0
    CLOUD_COEFF_MODEL = CLOUD_COEFF        ! 0.6
    ALBEDO_ICE_MODEL = ALBEDO_ICE          ! 0.7

    SOLAR_CONSTANT_ASTRO = 1361.0  ! Modern value [W/m2]

    ! Test latitudes
    lats(1) = 70.0
    lats(2) = 75.0
    lats(3) = 80.0

    ! Test dates (day of year): Mar 21, Jun 21, Sep 21, Dec 21
    dates(1) = 80.0    ! Mar 21
    dates(2) = 172.0   ! Jun 21
    dates(3) = 264.0   ! Sep 21
    dates(4) = 355.0   ! Dec 21
    date_names(1) = "Mar21"
    date_names(2) = "Jun21"
    date_names(3) = "Sep21"
    date_names(4) = "Dec21"

    ! Test times (UTC hours): 0, 6, 12, 18
    times(1) = 0.0
    times(2) = 6.0
    times(3) = 12.0
    times(4) = 18.0
    time_names(1) = "00UTC"
    time_names(2) = "06UTC"
    time_names(3) = "12UTC"
    time_names(4) = "18UTC"

    print *, "=================================================="
    print *, "  TEST: Solar Radiation Geometry Comparison"
    print *, "=================================================="
    print *, ""
    print *, "Legacy model: decl=0, hour_angle=0 (permanent equinox noon)"
    print *, "Astronomical: real declination & hour angle"
    print *, ""

    ! Legacy calculation (fixed)
    ! At latitude phi with decl=0, hour=0: cos_zenith = cos(phi)
    do i = 1, 3
        print *, "--------------------------------------------------"
        print *, "Latitude: ", lats(i), "°N"
        print *, "--------------------------------------------------"

        ! Legacy cos_zenith at this latitude (decl=0, hour=0)
        cos_zenith_legacy = cos(lats(i)/57.2957795)
        cos_zenith_legacy = max(0.0, cos_zenith_legacy)

        ! Daily average legacy (continuous noon)
        daily_sw_legacy = SOLAR_CONSTANT_MODEL * cos_zenith_legacy**2 * (1.0 - CLOUD_COEFF_MODEL * 0.5**3) * 86400.0 / 1.0

        print *, "Legacy (continuous noon):"
        print *, "  cos_zenith = ", cos_zenith_legacy
        print *, "  SW_down (clear) = ", SOLAR_CONSTANT_MODEL*cos_zenith_legacy**2, " W/m2"
        print *, "  SW_abs (clear) = ", SOLAR_CONSTANT_MODEL * cos_zenith_legacy**2 * (1.0 - ALBEDO_ICE_MODEL), " W/m2"
        print *, "  Daily SW_abs (50% cloud) = ", daily_sw_legacy/1e6, " MJ/m2/day"
    end do

    print *, ""
    print *, "=================================================="
    print *, "  ASTRONOMICAL CALCULATIONS"
    print *, "=================================================="

    do i = 1, 3
        print *, ""
        print *, "--------------------------------------------------"
        print *, "Latitude: ", lats(i), "°N"
        print *, "--------------------------------------------------"

        daily_sw_astro = 0.0

        do j = 1, 4
            ! Solar declination (Spencer 1971 approximation)
            gamma = 2.0*3.14159265*(dates(j) - 1.0)/365.0
            decl = 0.006918 - 0.399912*cos(gamma) + 0.070257*sin(gamma) &
                   - 0.006758*cos(2.0*gamma) + 0.000907*sin(2.0*gamma) &
                   - 0.002697*cos(3.0*gamma) + 0.00148*sin(3.0*gamma)

            ! Hour angle: H = 15° * (local_solar_time - 12)
            ! For UTC times, need longitude. Use 30°E as representative.
            ! Local solar time = UTC + longitude/15
            lon = 30.0  ! 30°E
            do k = 1, 4
                local_time = times(k) + lon/15.0
                H = 15.0*(local_time - 12.0)  ! degrees

                ! Cosine of zenith angle
                lat_rad = lats(i)/57.2957795
                decl_rad = decl
                H_rad = H/57.2957795

               cos_zenith_astro = sin(lat_rad)*sin(decl_rad) + cos(lat_rad)*cos(decl_rad)*cos(H_rad)
                cos_zenith_astro = max(0.0, cos_zenith_astro)

                ! Shortwave (clear sky, no atmospheric attenuation for comparison)
                sw_astro = SOLAR_CONSTANT_ASTRO*cos_zenith_astro

                print *, "  ", date_names(j), " ", time_names(k), ": decl=", decl*57.2957795, "° H=", H, "° cosZ=", cos_zenith_astro, " SW=", sw_astro, " W/m2"

                ! Accumulate daily (6-hour intervals)
                daily_sw_astro = daily_sw_astro + sw_astro*6.0*3600.0/1e6
            end do
        end do

        print *, "  Daily integrated SW (clear) = ", daily_sw_astro, " MJ/m2"
    end do

    ! Now compare with atmospheric attenuation
    print *, ""
    print *, "=================================================="
    print *, "  COMPARISON WITH ATMOSPHERIC ATTENUATION"
    print *, "=================================================="
    print *, ""

    do i = 1, 3
        ! Legacy at this latitude
        cos_zenith_legacy = cos(lats(i)/57.2957795)
        cos_zenith_legacy = max(0.0, cos_zenith_legacy)

        ! Legacy SW with cloud (50%)
        sw_legacy_clear = SOLAR_CONSTANT_MODEL*cos_zenith_legacy**2
       sw_legacy_cloudy = SOLAR_CONSTANT_MODEL*cos_zenith_legacy**2*(1.0 - CLOUD_COEFF_MODEL*0.5**3)

        ! Astronomical daily average at solstice (Jun 21)
        ! At latitude phi on summer solstice (δ=23.44°), sun doesn't set if phi > 66.56°
        ! cos_zenith = sin(phi)sin(delta) + cos(phi)cos(delta)cos(H)
        ! Daily integral = ∫ cos_zenith dH from -π to π = 2π * sin(phi)sin(delta)
        phi_rad = lats(i)/57.2957795
        delta_rad = 23.44/57.2957795
        daily_cos_int = 2.0*3.14159265*sin(phi_rad)*sin(delta_rad)
        ! Average cos_zenith over 24h
        avg_cos_astro = daily_cos_int/(2.0*3.14159265)

        sw_astro_avg_clear = SOLAR_CONSTANT_ASTRO*avg_cos_astro
        sw_astro_avg_cloudy = SOLAR_CONSTANT_ASTRO*avg_cos_astro*(1.0 - CLOUD_COEFF_MODEL*0.5**3)

        print *, "Latitude ", lats(i), "°N:"
        print *, "  Legacy (continuous noon):"
        print *, "    cosZ = ", cos_zenith_legacy
        print *, "    SW_clear = ", sw_legacy_clear, " W/m2"
        print *, "    SW_50%cloud = ", sw_legacy_cloudy, " W/m2"
        print *, "  Astronomical (Jun 21 daily avg):"
        print *, "    avg_cosZ = ", avg_cos_astro
        print *, "    SW_clear = ", sw_astro_avg_clear, " W/m2"
        print *, "    SW_50%cloud = ", sw_astro_avg_cloudy, " W/m2"
        print *, "  Ratio Legacy/Astro (clear) = ", sw_legacy_clear/sw_astro_avg_clear
        print *, "  Ratio Legacy/Astro (50% cloud) = ", sw_legacy_cloudy/sw_astro_avg_cloudy
    end do

    ! Polar night test
    print *, ""
    print *, "=================================================="
    print *, "  POLAR NIGHT TEST"
    print *, "=================================================="

    ! At 80°N on Dec 21: polar night
    phi_rad = 80.0/57.2957795
    delta_rad = -23.44/57.2957795
    ! Sun is below horizon all day
    ! cos_zenith = sin(80)*sin(-23.44) + cos(80)*cos(-23.44)*cos(H)
    ! Max when cos(H)=1: sin(80)*sin(-23.44) + cos(80)*cos(23.44) = cos(80+23.44) = cos(103.44) < 0
    max_cos_winter = sin(phi_rad)*sin(delta_rad) + cos(phi_rad)*cos(delta_rad)
    print *, "80°N Dec 21: max cos_zenith = ", max_cos_winter
    if (max_cos_winter .le. 0.0) then
        print *, "  OK: Polar night correctly gives zero/negative cos_zenith"
        n_checks = n_checks + 1
    else
        print *, "  FAIL: Should be polar night"
        n_errors = n_errors + 1
    end if

    ! Legacy at 80°N: cos_zenith = cos(80°) = 0.1736 > 0 -> WRONG
    cos_zenith_legacy = cos(80.0/57.2957795)
    print *, "Legacy at 80°N: cos_zenith = ", cos_zenith_legacy, " (WRONG - gives daylight in polar night)"

    n_checks = n_checks + 1
    if (cos_zenith_legacy .gt. 0.0) then
        print *, "  CONFIRMED: Legacy gives false daylight in polar night"
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Solar Radiation Geometry Test PASSED"
        stop 0
    else
        print *, "FAILURE: Solar Radiation Geometry Test FAILED"
        stop 1
    end if

contains

end program iceberg_test_solar_radiation_geometry
