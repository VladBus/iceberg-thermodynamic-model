! ==============================================================================
! Тест: Stage 10.12 — Independent Scientific Validation of Prognostic
!       Internal Thermal Evolution
! Назначение: Независимая научная проверка production-реализации прогностической
!             внутренней температуры льда (Stage 10.12).
!             ВСЕ ОЖИДАЕМЫЕ ЗНАЧЕНИЯ вычисляются независимо с
!             ЭМБЕДДИРОВАННЫМИ литералами (паттерн Stage 10.7 / 10.10):
!               ρ_i=910, c_i=2100, H_EFF=0.5, H_MIN_INT=0.5,
!               K_ICE=2.2, T_ICE_INIT=-10.0, T_ICE_MIN=-100.0, T_ICE_MAX=0.0,
!               T_MELT=0.0.
!             Production-функции вызываются ТОЛЬКО для фактического
!             (проверяемого) результата.
!
! Проверяемая формула (Stage 10.12):
!   q_cond = 2 * K_ICE * (T_surface - T_ice) / H
!   C_int = ρ_i * C_ICE * H_int, где H_int = max(H - H_EFF, H_MIN_INT)
!   dT_ice/dt = (q_cond - q_bot) / C_int
!   q_bot = m_basal * ρ_i * CP_ICE_3EQ * max(T_B - T_ice, 0)
!   T_ice^{n+1} = T_ice + dt * (q_cond - q_bot) / C_int
!   clamp: T_ice ∈ [T_ICE_MIN, T_ICE_MAX]
! ==============================================================================

program iceberg_test_10p12_thermal_evolution
    use iceberg_types, only: ocean_profile, iceberg_state, iceberg_diagnostics, &
                             atmos_forcing, &
                             T_ICE_INIT, T_ICE_MIN, T_ICE_MAX, &
                             C_ICE, H_EFF, H_MIN_INT, K_ICE, RHO_ICE, &
                             C_ICE, CP_ICE_3EQ, LATENT_HEAT, T_MELT, &
                             RHO_ICE, CP_ICE_3EQ, LATENT_HEAT, T_MELT, &
                             compute_iceberg_thermal_capacity, &
                             compute_iceberg_conductive_coupling, &
                             update_iceberg_internal_temperature, &
                             set_thermal_evolution, &
                             thermal_evolution_enabled
    use iceberg_thermodynamics, only: iceberg_thermodynamics_step, &
                                      compute_surface_melt
    use param, only: nat
    implicit none

    integer :: n_errors, n_checks
    real :: q_cond, q_bot, c_eff_int, h_int, dT_dt, T_new
    real :: m_basal, T_B, T_ice, T_surface, H, dt
    type(iceberg_state) :: state
    type(iceberg_diagnostics) :: diag
    type(ocean_profile) :: prof_off
    type(atmos_forcing) :: atmos_off
    type(iceberg_state) :: state_a, state_b, state_c
    type(iceberg_diagnostics) :: diag_a, diag_b, diag_c
    real :: q_net_ref, m_ref
    integer :: k_off

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.12 AUDIT: PROGNOSTIC INTERNAL THERMAL EVOLUTION"
    print *, "=================================================="

    ! Initialize state
    state%T_ice = T_ICE_INIT
    state%T_surface = T_ICE_INIT
    state%L = 100.0
    state%W = 50.0
    state%H = 50.0
    state%x = 0.0
    state%y = 0.0
    state%u = 0.0
    state%v = 0.0
    state%latitude = 0.0
    state%longitude = 0.0
    state%nstep = 0
    state%time = 0.0
    state%active = .true.
    state%grounded = .false.

    ! ----------------------------------------------------------
    ! A. Thermal capacity calculation
    ! ----------------------------------------------------------
    ! H = 50.0, H_EFF = 0.5, H_MIN_INT = 0.5
    ! H_int = max(50.0 - 0.5, 0.5) = 49.5
    ! C_int = 910 * 2100 * 49.5 = 9.44505e7 J/(m²·K)
    n_checks = n_checks + 1
    call compute_iceberg_thermal_capacity(state, c_eff_int, h_int)
    if (abs(h_int - 49.5) .lt. 1.0e-6 .and. &
        abs(c_eff_int - 910.0*2100.0*49.5) / (910.0*2100.0*49.5) .lt. 1.0e-6) then
        print *, "OK A.1: H_int=49.5, C_int=", c_eff_int
    else
        print *, "ERROR A.1: H_int=", h_int, " C_int=", c_eff_int
        n_errors = n_errors + 1
    end if

    ! H = 1.0 (thin iceberg)
    ! H_int = max(1.0 - 0.5, 0.5) = 0.5
    state%H = 1.0
    n_checks = n_checks + 1
    call compute_iceberg_thermal_capacity(state, c_eff_int, h_int)
    if (abs(h_int - 0.5) .lt. 1.0e-6 .and. &
        abs(c_eff_int - 910.0*2100.0*0.5) / (910.0*2100.0*0.5) .lt. 1.0e-6) then
        print *, "OK A.2: H=1.0 -> H_int=0.5, C_int=", c_eff_int
    else
        print *, "ERROR A.2: H_int=", h_int, " C_int=", c_eff_int
        n_errors = n_errors + 1
    end if

    ! H = 0.1 (very thin, below H_MIN_INT)
    ! H_int = max(0.1 - 0.5, 0.5) = 0.5 (clamped)
    state%H = 0.1
    n_checks = n_checks + 1
    call compute_iceberg_thermal_capacity(state, c_eff_int, h_int)
    if (abs(h_int - 0.5) .lt. 1.0e-6) then
        print *, "OK A.3: H=0.1 -> H_int clamped to H_MIN_INT=0.5"
    else
        print *, "ERROR A.3: H_int=", h_int, " expected 0.5"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! B. Conductive coupling (q_cond)
    ! q_cond = 2 * K_ICE * (T_surface - T_ice) / H
    ! K_ICE = 2.2
    ! ----------------------------------------------------------
    state%H = 50.0
    state%T_surface = -5.0
    state%T_ice = -10.0
    n_checks = n_checks + 1
    call compute_iceberg_conductive_coupling(state, q_cond)
    ! q_cond = 2 * 2.2 * (-5 - (-10)) / 50 = 4.4 * 5 / 50 = 0.44
    if (abs(q_cond - 0.44) / 0.44 .lt. 1.0e-6) then
        print *, "OK B.1: q_cond=0.44 W/m² (T_s=-5, T_i=-10, H=50)"
    else
        print *, "ERROR B.1: q_cond=", q_cond, " expected 0.44"
        n_errors = n_errors + 1
    end if

    ! T_surface = T_ice -> q_cond = 0
    state%T_surface = -10.0
    state%T_ice = -10.0
    n_checks = n_checks + 1
    call compute_iceberg_conductive_coupling(state, q_cond)
    if (abs(q_cond) .lt. 1.0e-12) then
        print *, "OK B.2: q_cond=0 when T_surface = T_ice"
    else
        print *, "ERROR B.2: q_cond=", q_cond, " expected 0"
        n_errors = n_errors + 1
    end if

    ! Negative q_cond (T_surface < T_ice)
    state%T_surface = -15.0
    state%T_ice = -10.0
    n_checks = n_checks + 1
    call compute_iceberg_conductive_coupling(state, q_cond)
    ! q_cond = 2 * 2.2 * (-15 - (-10)) / 50 = 4.4 * (-5) / 50 = -0.44
    if (abs(q_cond - (-0.44)) / 0.44 .lt. 1.0e-6) then
        print *, "OK B.3: q_cond=-0.44 W/m² (T_s=-15, T_i=-10, H=50)"
    else
        print *, "ERROR B.3: q_cond=", q_cond, " expected -0.44"
        n_errors = n_errors + 1
    end if

    ! H dependency: q_cond ∝ 1/H
    state%T_surface = -5.0
    state%T_ice = -10.0
    state%H = 100.0
    n_checks = n_checks + 1
    call compute_iceberg_conductive_coupling(state, q_cond)
    ! q_cond = 2 * 2.2 * 5 / 100 = 0.22 (half of H=50 case)
    if (abs(q_cond - 0.22) / 0.22 .lt. 1.0e-6) then
        print *, "OK B.4: q_cond ∝ 1/H (H=100 -> 0.22, H=50 -> 0.44)"
    else
        print *, "ERROR B.4: q_cond=", q_cond, " expected 0.22"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! C. Internal temperature update
    ! dT/dt = (q_cond - q_bot) / C_int
    ! ----------------------------------------------------------
    ! Test 1: Zero fluxes -> T constant
    state%H = 50.0
    state%T_surface = -10.0
    state%T_ice = -10.0
    q_cond = 0.0
    q_bot = 0.0
    dt = 3600.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (abs(state%T_ice - (-10.0)) .lt. 1.0e-12 .and. &
        abs(diag%dT_ice_dt) .lt. 1.0e-12) then
        print *, "OK C.1: zero fluxes -> T_ice constant"
    else
        print *, "ERROR C.1: T_ice=", state%T_ice, " dT/dt=", diag%dT_ice_dt
        n_errors = n_errors + 1
    end if

    ! Test 2: Positive q_cond, zero q_bot -> warming
    state%T_ice = -10.0
    state%T_surface = -5.0
    state%H = 50.0
    call compute_iceberg_conductive_coupling(state, q_cond)
    q_bot = 0.0
    dt = 3600.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    ! dT/dt = q_cond / C_int = 0.44 / 9.445e7 = 4.66e-9 K/s
    ! ΔT = 4.66e-9 * 3600 = 1.68e-5 K
    if (state%T_ice .gt. -10.0 .and. state%T_ice .lt. -9.9999) then
        print *, "OK C.2: positive q_cond -> warming"
    else
        print *, "ERROR C.2: T_ice=", state%T_ice
        n_errors = n_errors + 1
    end if

    ! Test 3: q_bot > 0 (basal sensible heat) -> cooling
    state%T_ice = -5.0
    q_cond = 0.0
    q_bot = 100.0  ! 100 W/m²
    dt = 3600.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    ! dT/dt = -100 / C_int
    ! C_int for H=50 is ~9.4e7
    ! dT/dt = -1.06e-6 K/s -> ΔT = -0.0038 K in 1 hour
    if (state%T_ice .lt. -5.0 .and. state%T_ice .gt. -5.01) then
        print *, "OK C.3: q_bot > 0 -> cooling"
    else
        print *, "ERROR C.3: T_ice=", state%T_ice
        n_errors = n_errors + 1
    end if

    ! Test 4: Upper bound clamp (T_ice <= 0)
    state%T_ice = -0.001
    q_cond = 1000.0  ! strong heating
    q_bot = 0.0
    dt = 3600.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (state%T_ice .eq. 0.0 .and. diag%t_ice_bound) then
        print *, "OK C.4: upper bound clamp at 0°C"
    else
        print *, "ERROR C.4: T_ice=", state%T_ice, " bound=", diag%t_ice_bound
        n_errors = n_errors + 1
    end if

    ! Test 5: Lower bound clamp (T_ice >= -100)
    state%T_ice = -99.0
    ! Усиленный диагностический поток (НЕ реалистичный атмосферный режим):
    ! C_int ~ 9.46e7 J/(K*m^2) при dt=3600 c требует q ~ -2.6e4 W/m^2,
    ! чтобы dT ~ -1.14 K пересёк нижнюю границу. Цель C.5 — срабатывание
    ! clamp, а не физическая реалистичность сценария.
    q_cond = -30000.0
    q_bot = 0.0
    dt = 3600.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (state%T_ice .eq. T_ICE_MIN .and. diag%t_ice_bound) then
        print *, "OK C.5: lower bound clamp at -100°C"
    else
        print *, "ERROR C.5: T_ice=", state%T_ice, " expected -100, bound=", diag%t_ice_bound
        n_errors = n_errors + 1
    end if

    ! Test 6: Zero dt -> no change
    state%T_ice = -15.0
    q_cond = 100.0
    q_bot = 0.0
    dt = 0.0
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (abs(state%T_ice - (-15.0)) .lt. 1.0e-12 .and. diag%dT_ice_dt == 0.0) then
        print *, "OK C.6: dt=0 -> no change"
    else
        print *, "ERROR C.6: T_ice=", state%T_ice, " dT/dt=", diag%dT_ice_dt
        n_errors = n_errors + 1
    end if

    ! Test 7: Large dt stability
    state%T_ice = -10.0
    state%T_surface = -5.0
    state%H = 50.0
    call compute_iceberg_conductive_coupling(state, q_cond)
    q_bot = 0.0
    dt = 86400.0  ! 1 day
    n_checks = n_checks + 1
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (state%T_ice .gt. -10.0 .and. state%T_ice .le. 0.0 .and. &
        .not. diag%t_ice_bound) then
        print *, "OK C.7: large dt stable (no NaN/Inf)"
    else
        print *, "ERROR C.7: T_ice=", state%T_ice, " bound=", diag%t_ice_bound
        n_errors = n_errors + 1
    end if

    ! Test 7: Repeatability
    state%T_ice = -10.0
    state%T_surface = -5.0
    state%H = 50.0
    q_cond = 0.44
    q_bot = 0.0
    dt = 3600.0
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    T_new = state%T_ice
    state%T_ice = -10.0
    call update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
    if (abs(state%T_ice - T_new) .lt. 1.0e-12) then
        print *, "OK C.8: repeatability"
    else
        print *, "ERROR C.8: not repeatable"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! D. Thermal evolution switch
    ! ----------------------------------------------------------
    call set_thermal_evolution(.false.)
    n_checks = n_checks + 1
    if (.not. thermal_evolution_enabled) then
        print *, "OK D.1: thermal_evolution_enabled = .false."
    else
        print *, "ERROR D.1: thermal_evolution_enabled should be .false."
        n_errors = n_errors + 1
    end if

    call set_thermal_evolution(.true.)
    n_checks = n_checks + 1
    if (thermal_evolution_enabled) then
        print *, "OK D.2: thermal_evolution_enabled = .true."
    else
        print *, "ERROR D.2: thermal_evolution_enabled should be .true."
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! E. Units and signs check
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    ! C_eff units: J/(m²·K)
    ! q units: W/m² = J/(m²·s)
    ! dT/dt = q/C -> K/s
    ! T units: °C
    if (c_eff_int .gt. 0.0 .and. q_cond .ge. -1e3 .and. q_cond .le. 1e3) then
        print *, "OK E.1: units and sign ranges plausible"
    else
        print *, "ERROR E.1: units implausible"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! F. OFF-switch legacy invariance (Stage 10.12 gate)
    ! ----------------------------------------------------------
    ! thermal_evolution_enabled = .false. => full legacy path:
    ! interior not updated, q_cond NOT subtracted from the surface
    ! budget (q_internal_exchange not passed), all 10.12 diagnostics
    ! defined. Surface verified bitwise against a direct
    ! compute_surface_melt call without the optional argument.
    prof_off%nlevels = 2
    allocate (prof_off%z(2), prof_off%dz(2), prof_off%temp(2), &
              prof_off%salt(2), prof_off%u(2), prof_off%v(2))
    do k_off = 1, 2
        prof_off%z(k_off) = real(5 + (k_off - 1)*10)
        prof_off%dz(k_off) = 10.0
        prof_off%temp(k_off) = -1.0
        prof_off%salt(k_off) = 0.0345
        prof_off%u(k_off) = 0.0
        prof_off%v(k_off) = 0.0
    end do

    atmos_off%u10 = 0.0
    atmos_off%v10 = 0.0
    atmos_off%t2m = 253.15
    atmos_off%d2m = 253.15
    atmos_off%tcc = 0.0
    atmos_off%msl = 101325.0
    atmos_off%snowfall = 0.0

    state_a%T_ice = -5.0
    state_a%T_surface = -2.0
    state_a%L = 100.0
    state_a%W = 50.0
    state_a%H = 50.0
    state_a%x = 0.0
    state_a%y = 0.0
    state_a%u = 0.0
    state_a%v = 0.0
    state_a%latitude = 0.0
    state_a%longitude = 0.0
    state_a%nstep = 0
    state_a%time = 0.0
    state_a%active = .true.
    state_a%grounded = .false.
    state_b = state_a
    state_c = state_a

    diag_a%draft = 50.0*910.0/1028.0
    diag_b%draft = diag_a%draft
    diag_c%draft = diag_a%draft

    dt = 3600.0

    call set_thermal_evolution(.false.)
    call iceberg_thermodynamics_step(state_a, dt, prof_off, atmos_off, diag_a)

    ! F.1: interior update skipped at OFF
    n_checks = n_checks + 1
    if (state_a%T_ice .eq. -5.0) then
        print *, "OK F.1: OFF -> state%T_ice unchanged"
    else
        print *, "ERROR F.1: state%T_ice=", state_a%T_ice, " expected -5.0"
        n_errors = n_errors + 1
    end if

    ! F.2: 10.12 diagnostics defined at OFF (legacy values)
    n_checks = n_checks + 1
    if (diag_a%t_ice .eq. -5.0 .and. diag_a%dT_ice_dt .eq. 0.0 .and. &
        .not. diag_a%t_ice_bound .and. diag_a%c_eff_int .eq. RHO_ICE*C_ICE*H_EFF) then
        print *, "OK F.2: OFF -> diag defined (t_ice, dT=0, bound=F, c_eff_int=skin legacy)"
    else
        print *, "ERROR F.2: diag t_ice=", diag_a%t_ice, " dT=", diag_a%dT_ice_dt, &
                 " c=", diag_a%c_eff_int, " bound=", diag_a%t_ice_bound
        n_errors = n_errors + 1
    end if

    ! F.3: bitwise legacy surface budget — step at OFF must equal a
    ! direct compute_surface_melt call WITHOUT q_internal_exchange
    call compute_surface_melt(state_b, atmos_off, diag_b, q_net_ref, m_ref, &
                              dt, nat(1), nat(2), nat(3), nat(4))
    n_checks = n_checks + 1
    if (abs(diag_a%q_net_surface - q_net_ref) .lt. 1.0e-6 .and. &
        abs(diag_a%m_surface - m_ref) .lt. 1.0e-12) then
        print *, "OK F.3: OFF -> surface budget == legacy (no q_cond subtraction)"
    else
        print *, "ERROR F.3: q_net step=", diag_a%q_net_surface, " ref=", q_net_ref, &
                 " m step=", diag_a%m_surface, " ref=", m_ref
        n_errors = n_errors + 1
    end if

    ! F.4: switch ON toggles behavior (q_cond subtracted, interior updated)
    call set_thermal_evolution(.true.)
    call iceberg_thermodynamics_step(state_c, dt, prof_off, atmos_off, diag_c)
    n_checks = n_checks + 1
    if (abs(diag_c%q_net_surface - q_net_ref) .gt. 0.1 .and. state_c%T_ice .ne. -5.0) then
        print *, "OK F.4: ON -> q_cond subtracted and interior updated"
    else
        print *, "ERROR F.4: q_net ON=", diag_c%q_net_surface, " ref=", q_net_ref, &
                 " T_ice=", state_c%T_ice
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! Summary
    ! ----------------------------------------------------------
    print *, ""
    print *, "=================================================="
    print *, "  Total checks: ", n_checks, "  Errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Stage 10.12 thermal evolution validation PASSED"
        stop 0
    else
        print *, "FAILURE: Stage 10.12 thermal evolution validation FAILED"
        stop 1
    end if

end program iceberg_test_10p12_thermal_evolution