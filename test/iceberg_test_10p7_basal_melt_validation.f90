! ==============================================================================
! Тест: Stage 10.7 — Independent Scientific Validation of Basal Melt
! Назначение: Независимая научная проверка production-формулировки базального
!             таяния (Stage 10.6) без использования production-функций для
!             ОЖИДАЕМЫХ значений.
!
! Проверяемая цепочка (production):
!   U_rel(z) = sqrt((u_water - u_ice)^2 + (v_water - v_ice)^2)
!   Re        = U_rel * L_char / ν
!   Nu_lam    = 0.664 * Re^0.5 * Pr^(1/3)      (Re <  Re_crit = 5e5)
!   Nu_turb   = 0.037 * Re^0.8 * Pr^(1/3)      (Re >= Re_crit = 5e5)
!   γ_T       = Nu * k / L_char                [W/(m²·K)]
!   ΔT_b      = max(T(D) - Tf(D), 0)           (Tf = EOS-80)
!   m_basal   = γ_T * ΔT_b / (ρ_ice * L_f)     [m/s]
!
! ВСЕ ОЖИДАЕМЫЕ ЗНАЧЕНИЯ вычисляются независимо: аналитические формулы
! переписываются в этом файле с ЭМБЕДДИРОВАННЫМИ литералами констант
! (Pr=13.8, ν=1.82e-6, k=0.56, ρ_ice=910, L_f=3.34e5, EOS-80 коэффициенты),
! а НЕ импортируются из production-модулей. Production-функции вызываются
! ТОЛЬКО для получения фактического (проверяемого) результата.
! ==============================================================================

program iceberg_test_10p7_basal_melt_validation
    use iceberg_types, only: ocean_profile, ocean_heat_transfer_coeff
    use iceberg_thermodynamics, only: compute_basal_melt
    implicit none

    integer :: n_errors, n_checks
    real :: u_rel, l_char, gamma_prod
    real :: expected_gamma, expected_re, expected_nu, expected_m
    real :: delta_t, m_basal
    real :: t_draft, s_draft, tf_draft
    real :: gamma_below, gamma_above, jump_ratio
    real :: g1, g2, ratio, ratio_expected
    real :: tf_draft_i, m_basal_i, delta_t_i

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.7 AUDIT: BASAL MELT INDEPENDENT VALIDATION"
    print *, "=================================================="

    ! ----------------------------------------------------------
    ! A. Zero thermal excess (T(D) <= Tf(D))  -->  m_basal = 0
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_cold_profile(n_errors, n_checks, m_basal)

    ! ----------------------------------------------------------
    ! B. Laminar regime (Re < 5e5), independent analytical
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    u_rel = 0.005
    l_char = 100.0
    expected_re = u_rel*l_char/1.82e-6
    expected_nu = 0.664*sqrt(expected_re)*(13.8**(1.0/3.0))
    expected_gamma = expected_nu*0.56/l_char
    call ocean_heat_transfer_coeff(u_rel, l_char, gamma_prod)
    if (abs(gamma_prod - expected_gamma)/abs(expected_gamma) .lt. 1.0e-4) then
        print *, "OK B.1: laminar Re=", expected_re, " gamma_T=", gamma_prod
    else
        print *, "ERROR B.1: gamma_prod=", gamma_prod, " expected=", expected_gamma
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! C. Turbulent regime (Re > 5e5), independent analytical
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    u_rel = 0.5
    l_char = 100.0
    expected_re = u_rel*l_char/1.82e-6
    expected_nu = 0.037*(expected_re**0.8)*(13.8**(1.0/3.0))
    expected_gamma = expected_nu*0.56/l_char
    call ocean_heat_transfer_coeff(u_rel, l_char, gamma_prod)
    if (abs(gamma_prod - expected_gamma)/abs(expected_gamma) .lt. 1.0e-4) then
        print *, "OK C.1: turbulent Re=", expected_re, " gamma_T=", gamma_prod
    else
        print *, "ERROR C.1: gamma_prod=", gamma_prod, " expected=", expected_gamma
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! D. Transition neighbourhood (Re just below / above 5e5)
    !    Laminar below, turbulent above. Discontinuity ~2.9x is
    !    inherent to the piecewise correlation and is documented.
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    l_char = 100.0
    call ocean_heat_transfer_coeff(0.0090, l_char, gamma_below)   ! Re ~ 4.945e5 (lam)
    call ocean_heat_transfer_coeff(0.0092, l_char, gamma_above)   ! Re ~ 5.055e5 (turb)
    expected_re = 0.0090*l_char/1.82e-6
    expected_gamma = (0.664*sqrt(expected_re)*(13.8**(1.0/3.0)))*0.56/l_char
    if (abs(gamma_below - expected_gamma)/abs(expected_gamma) .lt. 1.0e-4) then
        print *, "OK D.1: below transition (Re=", expected_re, ") laminar gamma=", gamma_below
    else
        print *, "ERROR D.1: gamma_below=", gamma_below, " expected=", expected_gamma
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    expected_re = 0.0092*l_char/1.82e-6
    expected_gamma = (0.037*(expected_re**0.8)*(13.8**(1.0/3.0)))*0.56/l_char
    if (abs(gamma_above - expected_gamma)/abs(expected_gamma) .lt. 1.0e-4) then
        print *, "OK D.2: above transition (Re=", expected_re, ") turbulent gamma=", gamma_above
    else
        print *, "ERROR D.2: gamma_above=", gamma_above, " expected=", expected_gamma
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    jump_ratio = gamma_above/gamma_below
    if (jump_ratio .gt. 2.0 .and. jump_ratio .lt. 4.0) then
        print *, "OK D.3: documented discontinuity at Re_crit, jump ratio=", jump_ratio
        print *, "     (piecewise correlation; smoothness not guaranteed)"
    else
        print *, "WARNING D.3: jump ratio=", jump_ratio, "outside 2..4 band"
    end if

    ! ----------------------------------------------------------
    ! E. Velocity scaling: gamma_T ~ U_rel^0.5 (lam), U_rel^0.8 (turb)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    l_char = 100.0
    call ocean_heat_transfer_coeff(0.002, l_char, g1)
    call ocean_heat_transfer_coeff(0.004, l_char, g2)
    ratio = g2/g1
    ratio_expected = (0.004/0.002)**0.5
    if (abs(ratio - ratio_expected)/ratio_expected .lt. 1.0e-4) then
        print *, "OK E.1: laminar U-scaling gamma ~ U^0.5, ratio=", ratio
    else
        print *, "ERROR E.1: laminar U-ratio=", ratio, " expected=", ratio_expected
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    call ocean_heat_transfer_coeff(0.2, l_char, g1)
    call ocean_heat_transfer_coeff(0.4, l_char, g2)
    ratio = g2/g1
    ratio_expected = (0.4/0.2)**0.8
    if (abs(ratio - ratio_expected)/ratio_expected .lt. 1.0e-4) then
        print *, "OK E.2: turbulent U-scaling gamma ~ U^0.8, ratio=", ratio
    else
        print *, "ERROR E.2: turbulent U-ratio=", ratio, " expected=", ratio_expected
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! F. Temperature-excess scaling: m ~ max(ΔT, 0)
    !    Uses production delta_t/m ratios (gamma cancels identically).
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_delta_scaling(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! G. Length scaling (CORRECT negative exponents from 40d4a3b):
    !    laminar gamma ~ L^(-0.5); turbulent gamma ~ L^(-0.2)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call ocean_heat_transfer_coeff(0.004, 50.0, g1)
    call ocean_heat_transfer_coeff(0.004, 100.0, g2)
    ratio = g2/g1
    ratio_expected = (100.0/50.0)**(-0.5)
    if (abs(ratio - ratio_expected)/ratio_expected .lt. 1.0e-4) then
        print *, "OK G.1: laminar L-scaling gamma ~ L^-0.5, ratio=", ratio
    else
        print *, "ERROR G.1: laminar L-ratio=", ratio, " expected=", ratio_expected
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    call ocean_heat_transfer_coeff(0.5, 50.0, g1)
    call ocean_heat_transfer_coeff(0.5, 100.0, g2)
    ratio = g2/g1
    ratio_expected = (100.0/50.0)**(-0.2)
    if (abs(ratio - ratio_expected)/ratio_expected .lt. 1.0e-4) then
        print *, "OK G.2: turbulent L-scaling gamma ~ L^-0.2, ratio=", ratio
    else
        print *, "ERROR G.2: turbulent L-ratio=", ratio, " expected=", ratio_expected
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! H. Zero relative flow: gamma_T = 0, m = 0 even for warm ocean.
    !    DOCUMENTED LIMITATION: natural convection is not represented,
    !    real iceberg melt does NOT vanish at U_rel = 0.
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call ocean_heat_transfer_coeff(0.0, 100.0, gamma_prod)
    if (gamma_prod .eq. 0.0) then
        print *, "OK H.1: U_rel=0 -> gamma_T=0 (forced convection closure)"
    else
        print *, "ERROR H.1: gamma_T=", gamma_prod, " expected 0.0"
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    call check_zero_flow_warm_ocean(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! I. End-to-end: production compute_basal_melt vs fully independent
    !    analytical chain (U_rel, Re, Nu, gamma, Tf EOS-80, ΔT, m).
    ! ----------------------------------------------------------
    call check_end_to_end(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! J. Literature magnitude band: observed submarine melt of icebergs
    !    ~ 0.01-1 m/day (Cenedese & Straneo 2023 review and refs therein).
    !    Production flat-plate must land inside for a canonical case.
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_magnitude_band(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! Summary
    ! ----------------------------------------------------------
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: STAGE 10.7 BASAL MELT INDEPENDENT VALIDATION PASSED"
        stop 0
    else
        print *, "FAILURE: STAGE 10.7 VALIDATION FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    ! Independent EOS-80 freezing point (Fofonoff & Millard 1983).
    pure real function tf_eos_s10p7(s_mass, depth_m) result(tf)
        real, intent(in) :: s_mass, depth_m
        real :: s_psu, p_dbar
        s_psu = s_mass*1000.0
        p_dbar = 1028.0*9.80665*depth_m/1.0e4
        tf = (-0.0575 + 1.710523e-3*sqrt(s_psu) - 2.154996e-4*s_psu)*s_psu &
             - 7.53e-4*p_dbar
    end function tf_eos_s10p7

    subroutine build_profile(t_val, u_rel_val, prof)
        type(ocean_profile), intent(out) :: prof
        real, intent(in) :: t_val, u_rel_val
        prof%nlevels = 3
        allocate(prof%z(3), prof%dz(3), prof%temp(3), prof%salt(3), &
                 prof%u(3), prof%v(3), prof%u_rel(3))
        prof%z = (/ 5.0, 50.0, 100.0 /)
        prof%dz = (/ 10.0, 50.0, 100.0 /)
        prof%temp = (/ t_val, t_val, t_val /)
        prof%salt = (/ 0.0345, 0.0345, 0.0345 /)
        prof%u = (/ 0.1, 0.1, 0.1 /)
        prof%v = (/ 0.0, 0.0, 0.0 /)
        prof%u_rel = (/ u_rel_val, u_rel_val, u_rel_val /)
    end subroutine build_profile

    subroutine check_cold_profile(n_errors, n_checks, m_basal)
        integer, intent(inout) :: n_errors, n_checks
        real, intent(out) :: m_basal
        type(ocean_profile) :: prof
        real :: t_draft, s_draft, tf_draft, delta_t
        call build_profile(-2.6, 0.1, prof)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal)
        if (m_basal .eq. 0.0) then
            print *, "OK A.1: T(D) < Tf(D) -> m_basal = 0 (m=", m_basal, ")"
        else
            print *, "ERROR A.1: cold ocean m_basal=", m_basal, " expected 0"
            n_errors = n_errors + 1
        end if
    end subroutine check_cold_profile

    subroutine check_delta_scaling(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof1, prof2, prof3
        real :: t1, s1, tf1, d1, m1
        real :: t2, s2, tf2, d2, m2
        real :: t3, s3, tf3, d3, m3
        real :: r1, r2
        call build_profile(-1.4, 0.5, prof1)
        call compute_basal_melt(prof1, 50.0, 100.0, 0.0, 0.0, t1, s1, tf1, d1, m1)
        call build_profile(1.6, 0.5, prof2)
        call compute_basal_melt(prof2, 50.0, 100.0, 0.0, 0.0, t2, s2, tf2, d2, m2)
        call build_profile(4.6, 0.5, prof3)
        call compute_basal_melt(prof3, 50.0, 100.0, 0.0, 0.0, t3, s3, tf3, d3, m3)
        r1 = (m2/m1)/(d2/d1)
        r2 = (m3/m1)/(d3/d1)
        if (m1 .gt. 0.0 .and. abs(r1 - 1.0) .lt. 1.0e-3 .and. abs(r2 - 1.0) .lt. 1.0e-3) then
            print *, "OK F.1: m ~ ΔT linear (m2/m1=", m2/m1, " d2/d1=", d2/d1, ")"
        else
            print *, "ERROR F.1: m/ΔT ratios r1=", r1, " r2=", r2
            n_errors = n_errors + 1
        end if
    end subroutine check_delta_scaling

    subroutine check_zero_flow_warm_ocean(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof
        real :: t_draft, s_draft, tf_draft, delta_t, m_basal
        call build_profile(2.0, 0.0, prof)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal)
        if (m_basal .eq. 0.0) then
            print *, "OK H.2: warm ocean but U_rel=0 -> m_basal=0 (documented limitation:"
            print *, "     forced-convection closure; natural convection not implemented)"
        else
            print *, "ERROR H.2: U_rel=0 warm ocean m_basal=", m_basal, " expected 0"
            n_errors = n_errors + 1
        end if
    end subroutine check_zero_flow_warm_ocean

    subroutine check_end_to_end(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof
        real :: t_draft, s_draft, tf_draft, delta_t, m_basal
        real :: u_rel, l_char, re, nu, gamma, tf_ind, dt_ind, m_ind
        call build_profile(2.0, 0.1, prof)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal)

        u_rel = 0.1
        l_char = 100.0
        re = u_rel*l_char/1.82e-6
        if (re .ge. 5.0e5) then
            nu = 0.037*(re**0.8)*(13.8**(1.0/3.0))
        else
            nu = 0.664*sqrt(re)*(13.8**(1.0/3.0))
        end if
        gamma = nu*0.56/l_char
        tf_ind = tf_eos_s10p7(0.0345, 50.0)
        dt_ind = 2.0 - tf_ind
        m_ind = gamma*dt_ind/(910.0*3.34e5)

        n_checks = n_checks + 1
        if (abs(tf_draft - tf_ind)/abs(tf_ind) .lt. 1.0e-4) then
            print *, "OK I.1: independent Tf=", tf_ind, " production=", tf_draft
        else
            print *, "ERROR I.1: Tf production=", tf_draft, " independent=", tf_ind
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (abs(delta_t - dt_ind)/abs(dt_ind) .lt. 1.0e-4) then
            print *, "OK I.2: independent dT=", dt_ind, " production=", delta_t
        else
            print *, "ERROR I.2: dT production=", delta_t, " independent=", dt_ind
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (abs(m_basal - m_ind)/abs(m_ind) .lt. 1.0e-4) then
            print *, "OK I.3: independent m=", m_ind, " production=", m_basal
            print *, "     (U=", u_rel, " L=100 Re=", re, " gamma=", gamma, ")"
        else
            print *, "ERROR I.3: m production=", m_basal, " independent=", m_ind
            n_errors = n_errors + 1
        end if
    end subroutine check_end_to_end

    subroutine check_magnitude_band(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof
        real :: t_draft, s_draft, tf_draft, delta_t, m_basal, m_per_day
        call build_profile(2.0, 0.5, prof)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal)
        m_per_day = m_basal*86400.0
        ! Observed submarine melt range ~0.01-1 m/day (Cenedese & Straneo 2023 review).
        if (m_per_day .ge. 0.01 .and. m_per_day .le. 1.0) then
            print *, "OK J.1: canonical case m=", m_per_day, " m/day within observed band"
            print *, "     (Cenedese & Straneo 2023: observed submarine melt 0.01-1 m/day)"
        else
            print *, "ERROR J.1: m=", m_per_day, " m/day outside observed band [0.01,1]"
            n_errors = n_errors + 1
        end if
    end subroutine check_magnitude_band

end program iceberg_test_10p7_basal_melt_validation