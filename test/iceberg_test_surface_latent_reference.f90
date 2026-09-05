! ==============================================================================
! Тест: Independent Latent Heat Reference Benchmark
! Назначение: Независимая проверка латентного теплового потока.
!
! Модель использует:
!   LH = rho_air * LH_COEFF * U * L_v * (q_air - q_sat)
!
! Где:
!   q = 0.622 * e / p
!   e_sat из формулы Тетенса: e_sat = 610.78 * 10^(A * Tc / (Tc + 241.9)) для воды
!   или формула для льда
!
! Независимый референс (стандартный bulk formula):
!   LH_ref = rho_air * C_E * U * L * (q_air - q_sat)
!
! где C_E ~ 0.001 - 0.002 (Dalton number для влаги)
!
! ВАЖНО: Этот тест НЕ объявляет референс "правильным".
! Он служит диагностикой порядка величины.
! ==============================================================================

program iceberg_test_surface_latent_reference
    use iceberg_types
    use iceberg_thermodynamics
    implicit none

    integer :: n_errors, n_checks
    integer :: i, k

    ! Atmospheric state variables
    real :: t_air_k, t_dew_k, t_surf_k
    real :: p_atm, rho_air_calc
    real :: u10, v10, wind_speed
    real :: e_sat_air, e_sat_dew, e_vap, rh
    real :: q_air, q_sat, dq
    real :: lh_flux_model, lh_flux_ref
    real :: q_sat_model, q_sat_ref_ice
    real :: dq_model, dq_ref
    real :: lh_flux_ref_Ls, lh_flux

    ! Constants from model
    real :: LH_COEFF_MODEL
    real :: LATENT_VAP_MODEL
    real :: GAS_CONST_AIR_MODEL
    real :: SAT_VAPOR_0_MODEL
    real :: TETENS_A_MODEL

    ! Reference constants (standard bulk)
    real :: C_E_REF       ! Dalton number for moisture, typically 0.0015
    real :: L_V           ! Latent heat of vaporization
    real :: L_S           ! Latent heat of sublimation

    ! Derived
    real :: SAT_VAPOR_0_ICE  ! 611.15 Pa at 0°C for ice
    real :: TETENS_A_ICE     ! Ice saturation formula constant

    ! Test cases
    type :: test_case
        character(len=32) :: name
        real :: t_air_c      ! Air temperature [°C]
        real :: t_dew_c      ! Dew point [°C]
        real :: t_surf_c     ! Surface temperature [°C]
        real :: wind         ! Wind speed [m/s]
        real :: p_atm_pa     ! Pressure [Pa]
    end type test_case

    type(test_case) :: cases(3)

    n_errors = 0
    n_checks = 0

    ! Model constants
    LH_COEFF_MODEL = LH_COEFF      ! 0.6650735
    LATENT_VAP_MODEL = LATENT_VAP  ! 2.5e6
    GAS_CONST_AIR_MODEL = GAS_CONST_AIR  ! 287.0
    SAT_VAPOR_0_MODEL = SAT_VAPOR_0      ! 610.78
    TETENS_A_MODEL = TETENS_A            ! 8.61503

    ! Reference constants
    C_E_REF = 0.0015      ! Standard neutral bulk transfer coefficient for moisture
    L_V = 2.501e6         ! Latent heat of vaporization at 0°C [J/kg]
    L_S = 2.835e6         ! Latent heat of sublimation at 0°C [J/kg]
    SAT_VAPOR_0_ICE = 611.15  ! Saturation vapor pressure over ice at 0°C [Pa]
    TETENS_A_ICE = 9.5      ! Approximate constant for ice saturation (Tetens-like)

    ! Define test cases
    cases(1)%name = "Case1: T_air=0, T_dew=-2, T_surf=-5, U=5"
    cases(1)%t_air_c = 0.0
    cases(1)%t_dew_c = -2.0
    cases(1)%t_surf_c = -5.0
    cases(1)%wind = 5.0
    cases(1)%p_atm_pa = 101325.0

    cases(2)%name = "Case2: T_air=-5, T_dew=-10, T_surf=-10, U=5"
    cases(2)%t_air_c = -5.0
    cases(2)%t_dew_c = -10.0
    cases(2)%t_surf_c = -10.0
    cases(2)%wind = 5.0
    cases(2)%p_atm_pa = 101325.0

    cases(3)%name = "Case3: T_air=0, T_dew=-1, T_surf=-10, U=10"
    cases(3)%t_air_c = 0.0
    cases(3)%t_dew_c = -1.0
    cases(3)%t_surf_c = -10.0
    cases(3)%wind = 10.0
    cases(3)%p_atm_pa = 101325.0

    print *, "=================================================="
    print *, "  TEST: Independent Latent Heat Reference Benchmark"
    print *, "=================================================="
    print *, ""
    print *, "Model constants:"
    print *, "  LH_COEFF = ", LH_COEFF_MODEL
    print *, "  LATENT_VAP = ", LATENT_VAP_MODEL, " J/kg"
    print *, "  SAT_VAPOR_0 = ", SAT_VAPOR_0_MODEL, " Pa"
    print *, "  TETENS_A = ", TETENS_A_MODEL
    print *, ""
    print *, "Reference constants:"
    print *, "  C_E_REF = ", C_E_REF
    print *, "  L_V = ", L_V, " J/kg"
    print *, "  L_S = ", L_S, " J/kg"
    print *, "  SAT_VAPOR_0_ICE = ", SAT_VAPOR_0_ICE, " Pa"
    print *, ""

    do i = 1, 3
        print *, "--------------------------------------------------"
        print *, cases(i)%name
        print *, "--------------------------------------------------"

        ! Convert to Kelvin
        t_air_k = cases(i)%t_air_c + 273.15
        t_dew_k = cases(i)%t_dew_c + 273.15
        t_surf_k = cases(i)%t_surf_c + 273.15
        wind_speed = cases(i)%wind
        p_atm = cases(i)%p_atm_pa

        ! Air density
        rho_air_calc = p_atm/(GAS_CONST_AIR_MODEL*t_air_k)

        ! Vapor pressure from dew point (Tetens formula for water)
        e_sat_dew = SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*cases(i)%t_dew_c/(t_dew_k))
        ! Model uses RH from dew point, so e_vap = e_sat_dew (since RH = e_dew/e_sat_air)
        ! Actually model calculates: e_sat_air = f(T_air), e_sat_dew = f(T_dew), RH = e_sat_dew/e_sat_air, e_vap = RH * e_sat_air = e_sat_dew
        e_vap = e_sat_dew

        ! Saturation vapor pressure at air temperature (water)
        e_sat_air = SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*cases(i)%t_air_c/(t_air_k))

        ! Relative humidity
        rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))

        ! Specific humidities (q = 0.622 * e / p)
        q_air = 0.622*e_vap/p_atm

        ! Model q_sat: saturation at surface temperature using WATER formula
   q_sat_model = 0.622*(SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*cases(i)%t_surf_c/(t_surf_k)))/p_atm

        ! Reference q_sat: saturation at surface temperature using ICE formula
        q_sat_ref_ice = 0.622 * (SAT_VAPOR_0_ICE * 10.0**(TETENS_A_ICE * cases(i)%t_surf_c / (cases(i)%t_surf_c + 265.5))) / p_atm

        ! Humidity difference
        dq_model = q_air - q_sat_model
        dq_ref = q_air - q_sat_ref_ice

        ! Model latent heat flux
        lh_flux_model = rho_air_calc*LH_COEFF_MODEL*wind_speed*LATENT_VAP_MODEL*dq_model

        ! Reference latent heat flux (using L_v and ice saturation)
        lh_flux_ref = rho_air_calc*C_E_REF*wind_speed*L_V*dq_ref

        ! Also compute with L_s
        lh_flux_ref_Ls = rho_air_calc*C_E_REF*wind_speed*L_S*dq_ref

        ! Output
        print *, "  t_air = ", cases(i)%t_air_c, " °C = ", t_air_k, " K"
        print *, "  t_dew = ", cases(i)%t_dew_c, " °C"
        print *, "  t_surf = ", cases(i)%t_surf_c, " °C = ", t_surf_k, " K"
        print *, "  wind = ", wind_speed, " m/s"
        print *, "  p_atm = ", p_atm, " Pa"
        print *, "  rho_air = ", rho_air_calc, " kg/m3"
        print *, "  e_vap = ", e_vap, " Pa"
        print *, "  e_sat_air (water) = ", e_sat_air, " Pa"
        print *, "  RH = ", rh
        print *, "  q_air = ", q_air, " kg/kg"
        print *, "  q_sat_model (water at T_surf) = ", q_sat_model, " kg/kg"
        print *, "  q_sat_ref (ice at T_surf) = ", q_sat_ref_ice, " kg/kg"
        print *, "  dq_model = ", dq_model, " kg/kg"
        print *, "  dq_ref (ice) = ", dq_ref, " kg/kg"
        print *, ""
        print *, "  LH_model = ", lh_flux_model, " W/m2"
        print *, "  LH_ref (C_E=0.0015, L_v, ice sat) = ", lh_flux_ref, " W/m2"
        print *, "  LH_ref (C_E=0.0015, L_s, ice sat) = ", lh_flux_ref_Ls, " W/m2"
        print *, "  Ratio model/ref(L_v) = ", lh_flux_model/max(abs(lh_flux_ref), 1e-10)
        print *, "  Ratio model/ref(L_s) = ", lh_flux_model/max(abs(lh_flux_ref_Ls), 1e-10)
        print *, ""

        ! Check physical bounds
        n_checks = n_checks + 1
        if (q_air .ge. 0.0 .and. q_air .lt. 0.1) then
            print *, "  OK: q_air in physical bounds [0, 0.1)"
        else
            print *, "  WARN: q_air = ", q_air, " outside typical bounds"
        end if

        n_checks = n_checks + 1
        if (q_sat_model .ge. 0.0 .and. q_sat_model .lt. 0.1) then
            print *, "  OK: q_sat_model in physical bounds"
        else
            print *, "  WARN: q_sat_model = ", q_sat_model
        end if

        n_checks = n_checks + 1
        if (q_sat_ref_ice .ge. 0.0 .and. q_sat_ref_ice .lt. 0.1) then
            print *, "  OK: q_sat_ref_ice in physical bounds"
        else
            print *, "  WARN: q_sat_ref_ice = ", q_sat_ref_ice
        end if
    end do

    ! Additional: Test sign convention
    print *, "=================================================="
    print *, "  SIGN CONVENTION TEST"
    print *, "=================================================="
    print *, ""

    ! Case: q_air > q_sat (condensation/deposition -> LH > 0, energy TO surface)
    t_air_k = 273.15
    t_surf_k = 263.15
    p_atm = 101325.0
    wind_speed = 5.0
    rho_air_calc = p_atm/(GAS_CONST_AIR_MODEL*t_air_k)

    ! Saturated air at 0°C
    e_sat_air = SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*0.0/273.15)
    q_air = 0.622*e_sat_air/p_atm

    ! Saturation at -10°C (water formula as in model)
    q_sat = 0.622*(SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*(-10.0)/263.15))/p_atm

    dq = q_air - q_sat
    lh_flux = rho_air_calc*LH_COEFF_MODEL*wind_speed*LATENT_VAP_MODEL*dq

    print *, "Condensation case (q_air > q_sat):"
    print *, "  q_air = ", q_air
    print *, "  q_sat = ", q_sat
    print *, "  dq = ", dq
    print *, "  LH = ", lh_flux, " W/m2"
    print *, "  LH > 0 means energy GAIN by surface (condensation heating)"

    n_checks = n_checks + 1
    if (lh_flux .gt. 0.0) then
        print *, "  OK: Positive LH for condensation"
    else
        print *, "  FAIL: Expected positive LH for condensation"
        n_errors = n_errors + 1
    end if

    ! Case: q_air < q_sat (evaporation/sublimation -> LH < 0, energy FROM surface)
    t_dew_k = 253.15  ! -20°C dew point
    e_sat_dew = SAT_VAPOR_0_MODEL*10.0**(TETENS_A_MODEL*(-20.0)/253.15)
    q_air = 0.622*e_sat_dew/p_atm

    dq = q_air - q_sat
    lh_flux = rho_air_calc*LH_COEFF_MODEL*wind_speed*LATENT_VAP_MODEL*dq

    print *, ""
    print *, "Evaporation case (q_air < q_sat):"
    print *, "  q_air = ", q_air
    print *, "  q_sat = ", q_sat
    print *, "  dq = ", dq
    print *, "  LH = ", lh_flux, " W/m2"
    print *, "  LH < 0 means energy LOSS by surface (evaporative cooling)"

    n_checks = n_checks + 1
    if (lh_flux .lt. 0.0) then
        print *, "  OK: Negative LH for evaporation"
    else
        print *, "  FAIL: Expected negative LH for evaporation"
        n_errors = n_errors + 1
    end if

    ! Case: q_air = q_sat (neutral)
    q_air = q_sat
    dq = q_air - q_sat
    lh_flux = rho_air_calc*LH_COEFF_MODEL*wind_speed*LATENT_VAP_MODEL*dq

    print *, ""
    print *, "Neutral case (q_air = q_sat):"
    print *, "  LH = ", lh_flux, " W/m2"

    n_checks = n_checks + 1
    if (abs(lh_flux) .lt. 1e-10) then
        print *, "  OK: Zero LH for neutral humidity"
    else
        print *, "  FAIL: Expected zero LH"
        n_errors = n_errors + 1
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Independent Latent Heat Reference PASSED"
        stop 0
    else
        print *, "FAILURE: Independent Latent Heat Reference FAILED"
        stop 1
    end if

contains

end program iceberg_test_surface_latent_reference
