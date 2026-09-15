! ==============================================================================
! Тест: Stage 10.13 — Low-Flow Closure (diffusion-limited + double-diffusive)
! Назначение: Focused tests production-интеграции low-flow закрытия:
!   A. Legacy OFF: low_flow_closure_enabled=.false. → результат == legacy 3eq
!   B. Активация при U=0 → конечный m в наблюдаемой полосе, режим DC
!   C. Переход U≈1e-3..1e-2 → гладкость (нет NaN/neg, log10-jump < 1)
!   D. Forced-сохранение: при высоком U результат == baseline
!   E. DDC: f=2.5 при активном критерии, 1 иначе (pure-функция)
!   F. Границы: delta_s мин/кап, U=0, ΔT=0 → без NaN/отрицательных m
!   G. 3eq-согласованность: T_B == Tf(S_B) в пределах допуска
!   H. Сравнение с Python-референсом (вывод CMP-строк для low_flow_fortran_comparison.py)
!   I. Детерминизм: повторный вызов даёт идентичный результат
! ==============================================================================

program iceberg_test_10p13_low_flow
    use iceberg_thermodynamics, only: compute_basal_melt, &
                                      solve_three_equation_interface
    use iceberg_types, only: ocean_profile, ocean_freezing_point, &
                             iceberg_state, iceberg_diagnostics, &
                             RHO_ICE, RHO_WATER, LATENT_HEAT, &
                             THREE_EQ_KT, THREE_EQ_KS, &
                             LEWIS_NUMBER, THERMAL_CONDUCTIVITY, CP_SEAWATER, &
                             LOW_FLOW_TIME_SCALE_S, LOW_FLOW_DELTA_MIN_M, &
                             LOW_FLOW_DELTA_MAX_M, LOW_FLOW_F_DC, &
                             LOW_FLOW_REGIME_DOUBLE_DIFFUSIVE, &
                             LOW_FLOW_REGIME_HYBRID_TRANSITION, &
                             LOW_FLOW_REGIME_FORCED, &
                             set_low_flow_closure, low_flow_closure_enabled, &
                             set_basal_melt_scheme, BASAL_MELT_SCHEME_THREE_EQUATION, &
                             low_flow_delta_s, low_flow_enhancement, &
                             low_flow_blend_weight, low_flow_regime_value
    implicit none

    integer :: n_errors, n_checks
    integer :: i
    real :: m_off, m_on_hi, m_on, m_ref
    real :: t_iface, s_iface, m_prev, m_cur
    real :: delta_s_lit, kappa_t_lit, kappa_s_lit, k_w_lit, m_low_lit
    real :: u_grid(7)
    type(ocean_profile) :: prof
    type(iceberg_state) :: state
    type(iceberg_diagnostics) :: diag
    real :: m_grid(7)
    logical :: ok_det
    real :: t_d, s_d, tf_d, dt_d

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.13 AUDIT: LOW-FLOW CLOSURE"
    print *, "=================================================="

    call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)
    call set_low_flow_closure(.false.)

    ! --- Инициализация состояния (паттерн Stage 10.12) ---
    state%T_ice = -10.0
    state%T_surface = -10.0
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

    ! --- A. LEGACY OFF: m == reference 3eq (forced) ---
    call build_profile(2.0, 0.035, 0.1, prof)
    call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, dt_d, m_off, &
                            t_iface, s_iface, diag)
    ! Ручной reference: solve_three_equation_interface с γ = K·U
    call solve_three_equation_interface(2.0, 0.035, 50.0, 0.1, &
                                        THREE_EQ_KT*0.1, THREE_EQ_KS*0.1, &
                                        -10.0, .true., t_iface, s_iface, m_ref)
    n_checks = n_checks + 1
    if (abs(m_off - m_ref)/max(m_off, 1.0e-20) .lt. 1.0e-6) then
        print *, "OK A.1: OFF == legacy 3eq (rel<1e-6)"
    else
        print *, "ERROR A.1: m_off=", m_off, " ref=", m_ref
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (.not. diag%low_flow_enabled .and. diag%low_flow_regime .eq. 0) then
        print *, "OK A.2: OFF -> diag defined (enabled=F, regime=0)"
    else
        print *, "ERROR A.2: diag enabled=", diag%low_flow_enabled, &
            " regime=", diag%low_flow_regime
        n_errors = n_errors + 1
    end if

    ! --- D. Forced-сохранение: ON при высоком U == OFF ---
    call set_low_flow_closure(.true.)
    call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, dt_d, m_on_hi, &
                            t_iface, s_iface, diag)
    n_checks = n_checks + 1
    if (m_on_hi .eq. m_off) then
        print *, "OK D.1: high-U ON == OFF (bit-identical)"
    else
        print *, "ERROR D.1: m_on_hi=", m_on_hi, " m_off=", m_off
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%low_flow_regime .eq. LOW_FLOW_REGIME_FORCED) then
        print *, "OK D.2: high-U regime = forced"
    else
        print *, "ERROR D.2: regime=", diag%low_flow_regime
        n_errors = n_errors + 1
    end if

    ! --- Embedded-literal δ_S и m_low (U=0, T=2, S=35, depth=50) ---
    kappa_t_lit = THERMAL_CONDUCTIVITY/(RHO_WATER*CP_SEAWATER)
    kappa_s_lit = kappa_t_lit/LEWIS_NUMBER
    delta_s_lit = max(LOW_FLOW_DELTA_MIN_M, min(sqrt(kappa_s_lit*LOW_FLOW_TIME_SCALE_S), &
                                                LOW_FLOW_DELTA_MAX_M))
    k_w_lit = RHO_WATER*CP_SEAWATER*kappa_t_lit
    m_low_lit = LOW_FLOW_F_DC*k_w_lit*(2.0 - ocean_freezing_point(0.035, 50.0))/ &
                (delta_s_lit*RHO_ICE*LATENT_HEAT)

    ! --- B. Активация при U=0: конечный m, режим DC, в полосе ---
    call build_profile(2.0, 0.035, 0.0, prof)
    call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, dt_d, m_on, &
                            t_iface, s_iface, diag)
    n_checks = n_checks + 1
    if (m_on .gt. 0.0 .and. m_on .lt. 1.0e-4) then
        print *, "OK B.1: U=0 -> finite m (", m_on*86400.0, " m/day)"
    else
        print *, "ERROR B.1: m=", m_on
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (m_on*86400.0 .gt. 0.01 .and. m_on*86400.0 .lt. 1.0) then
        print *, "OK B.2: U=0 m in observed band 0.01-1 m/day"
    else
        print *, "ERROR B.2: m=", m_on*86400.0, " m/day"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%low_flow_regime .eq. LOW_FLOW_REGIME_DOUBLE_DIFFUSIVE) then
        print *, "OK B.3: U=0 regime = double-diffusive"
    else
        print *, "ERROR B.3: regime=", diag%low_flow_regime
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(diag%low_flow_delta_s - delta_s_lit)/delta_s_lit .lt. 1.0e-5 .and. &
        abs(diag%low_flow_f - LOW_FLOW_F_DC) .lt. 1.0e-5) then
        print *, "OK B.4: delta_S и f совпадают с литералами"
    else
        print *, "ERROR B.4: delta_S=", diag%low_flow_delta_s, &
            " f=", diag%low_flow_f
        n_errors = n_errors + 1
    end if
    ! U=0 m не превышает бессвеженный предел m_low_lit (интерфейсное опреснение
    ! уменьшает m) и составляет его существенную долю (>30%)
    n_checks = n_checks + 1
    if (m_on .gt. 0.3*m_low_lit .and. m_on .lt. m_low_lit) then
        print *, "OK B.5: 0.3*m_low_lit < m(U=0) < m_low_lit (interface freshening)"
    else
        print *, "ERROR B.5: m=", m_on, " m_low_lit=", m_low_lit
        n_errors = n_errors + 1
    end if

    ! --- C. Переход: гладкость по U ---
    u_grid = (/0.0, 1.0e-4, 1.0e-3, 3.0e-3, 8.5e-3, 1.0e-2, 0.1/)
    do i = 1, 7
        call build_profile(2.0, 0.035, u_grid(i), prof)
        call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                                t_d, s_d, tf_d, dt_d, m_grid(i), &
                                t_iface, s_iface, diag)
        n_checks = n_checks + 1
        if (m_grid(i) .ge. 0.0 .and. m_grid(i) .eq. m_grid(i)) then
            ! OK
        else
            print *, "ERROR C.x: NaN/neg at U=", u_grid(i), " m=", m_grid(i)
            n_errors = n_errors + 1
        end if
    end do
    ! C.1: непрерывность на МЕЛКОЙ сетке внутри окна перехода (0.1x..3x
    ! диапазона [u_low, u_hi]) — как в Python-свипе; грубая сетка через
    ! форсированную декаду (U=1e-2..0.1) содержит законный 10x рост m.
    n_checks = n_checks + 1
    ok_det = .true.
    do i = 0, 59
        call build_profile(2.0, 0.035, 1.0e-4*(300.0)**(real(i)/59.0), prof)
        call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                                t_d, s_d, tf_d, dt_d, m_cur, &
                                t_iface, s_iface, diag)
        if (i .gt. 0) then
            if (abs(log10(m_cur + 1.0e-300) - log10(m_prev + 1.0e-300)) .ge. 0.2) ok_det = .false.
        end if
        m_prev = m_cur
    end do
    if (ok_det) then
        print *, "OK C.1: max log10 jump < 0.2 on fine grid (transition smooth)"
    else
        print *, "ERROR C.1: discontinuous jump in transition window"
        n_errors = n_errors + 1
    end if

    ! --- E. DDC pure-функция ---
    n_checks = n_checks + 1
    if (low_flow_enhancement(10.0, 0.5) .eq. LOW_FLOW_F_DC .and. &
        low_flow_enhancement(0.001, 0.5) .eq. 1.0 .and. &
        low_flow_enhancement(10.0, 5.0) .eq. 1.0) then
        print *, "OK E.1: enhancement criterion (R_rho>1/Le & Re_b<1)"
    else
        print *, "ERROR E.1: enhancement"
        n_errors = n_errors + 1
    end if

    ! --- F. Границы pure-функций ---
    n_checks = n_checks + 1
    if (low_flow_delta_s(0.0) .eq. LOW_FLOW_DELTA_MIN_M .and. &
        low_flow_delta_s(1.0e12) .eq. LOW_FLOW_DELTA_MAX_M) then
        print *, "OK F.1: delta_s min/cap bounds"
    else
        print *, "ERROR F.1: delta_s bounds"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (low_flow_blend_weight(0.0) .eq. 0.0 .and. &
        low_flow_blend_weight(1.0e-2) .eq. 1.0 .and. &
        abs(low_flow_blend_weight(5.5e-3) - 0.5) .lt. 1.0e-3) then
        print *, "OK F.2: blend weight endpoints and midpoint"
    else
        print *, "ERROR F.2: blend weight"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (low_flow_regime_value(1.0, 2.5, 2.0) .eq. LOW_FLOW_REGIME_FORCED .and. &
        low_flow_regime_value(0.5, 2.5, 2.0) .eq. LOW_FLOW_REGIME_HYBRID_TRANSITION .and. &
        low_flow_regime_value(0.0, 2.5, 2.0) .eq. LOW_FLOW_REGIME_DOUBLE_DIFFUSIVE .and. &
        low_flow_regime_value(0.0, 1.0, -1.0) .eq. 5) then
        print *, "OK F.3: regime classification"
    else
        print *, "ERROR F.3: regime"
        n_errors = n_errors + 1
    end if

    ! --- G. 3eq-согласованность: T_B == Tf(S_B) ---
    n_checks = n_checks + 1
    if (abs(t_iface - ocean_freezing_point(s_iface, 50.0)) .lt. 1.0e-3) then
        print *, "OK G.1: T_B == Tf(S_B, depth) within 1e-3"
    else
        print *, "ERROR G.1: T_B=", t_iface, " Tf(S_B)=", ocean_freezing_point(s_iface, 50.0)
        n_errors = n_errors + 1
    end if

    ! --- I. Детерминизм (два вызова при одном профиле) ---
    call build_profile(2.0, 0.035, 0.1, prof)
    call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, dt_d, m_cur, &
                            t_iface, s_iface, diag)
    m_prev = m_cur
    call compute_basal_melt(state, prof, 50.0, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, dt_d, m_cur, &
                            t_iface, s_iface, diag)
    n_checks = n_checks + 1
    if (m_cur .eq. m_prev) then
        print *, "OK I.1: repeated execution identical"
    else
        print *, "ERROR I.1: m_a=", m_prev, " m_b=", m_cur
        n_errors = n_errors + 1
    end if

    ! --- H. CMP-вывод для Python-сравнения (10 точек) ---
    call cmp_point(1, 2.0, 0.035, 0.0, 50.0)
    call cmp_point(2, 2.0, 0.035, 1.0e-4, 50.0)
    call cmp_point(3, 2.0, 0.035, 1.0e-3, 50.0)
    call cmp_point(4, 2.0, 0.035, 3.0e-3, 50.0)
    call cmp_point(5, 2.0, 0.035, 8.5e-3, 50.0)
    call cmp_point(6, 2.0, 0.035, 1.0e-2, 50.0)
    call cmp_point(7, 2.0, 0.035, 0.1, 50.0)
    call cmp_point(8, 4.0, 0.035, 0.0, 50.0)
    call cmp_point(9, 1.0, 0.030, 0.0, 50.0)
    call cmp_point(10, 6.0, 0.035, 0.0, 50.0)

    print *, "=================================================="
    print *, "  Total checks: ", n_checks, "  Errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: Stage 10.13 low-flow closure validation PASSED"
        stop 0
    else
        print *, "FAILURE: Stage 10.13 low-flow closure validation FAILED"
        stop 1
    end if

contains

    ! Равномерный океанский профиль: T=T_val, S=s_val, u=u_val на всех уровнях
    subroutine build_profile(t_val, s_val, u_val, prof)
        real, intent(in) :: t_val, s_val, u_val
        type(ocean_profile), intent(out) :: prof
        integer :: k
        prof%nlevels = 3
        allocate (prof%z(3), prof%dz(3), prof%temp(3), prof%salt(3), &
                  prof%u(3), prof%v(3))
        do k = 1, 3
            prof%z(k) = real(5 + (k - 1)*50)
            prof%dz(k) = 50.0
            prof%temp(k) = t_val
            prof%salt(k) = s_val
            prof%u(k) = u_val
            prof%v(k) = 0.0
        end do
    end subroutine build_profile

    ! CMP-строка для Python-сравнения (машиночитаемая)
    subroutine cmp_point(id, t_w, s_w, u_val, depth)
        integer, intent(in) :: id
        real, intent(in) :: t_w, s_w, u_val, depth
        type(ocean_profile) :: p
        real :: m_out, t_d, s_d, tf_d, dt_d
        call build_profile(t_w, s_w, u_val, p)
        call compute_basal_melt(state, p, depth, 100.0, 0.0, 0.0, &
                                t_d, s_d, tf_d, dt_d, m_out, &
                                t_iface, s_iface, diag)
        print '(A1,I3,1X,F12.6,1X,F12.6,1X,F12.6,1X,F12.6,1X,F12.6,1X,F12.6,1X,I3,1X,L1,1X,F12.6,1X,F12.6,1X,F12.6,1X,F12.6)', &
            'C', id, m_out*86400.0, diag%low_flow_delta_s, diag%low_flow_f, &
            diag%low_flow_gamma_t, diag%low_flow_gamma_s, &
            diag%low_flow_re_b, diag%low_flow_regime, diag%low_flow_converged, &
            diag%low_flow_r_rho, diag%low_flow_ri_star, diag%low_flow_u_rel, &
            diag%low_flow_delta_t
    end subroutine cmp_point

end program iceberg_test_10p13_low_flow
