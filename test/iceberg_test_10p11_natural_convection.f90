! ==============================================================================
! Тест: Stage 10.11.2 — Independent Scientific Validation of the
!       Natural-Convection Basal Melt Closure (Fortran audit test)
! Назначение: независимая проверка production-реализации натурально-
!             конвективного замыкания трёхчленного интерфейса лёд-океан
!             (Stage 10.11: Fujii et al. 1973 горизонтальная пластина,
!             обращённая вниз; Churchill 1977 смешанная конвекция n=3;
!             солевой баланс Stage 10.10.1 с плотностным отношением).
!             ВСЕ ОЖИДАЕМЫЕ ЗНАЧЕНИЯ вычисляются независимо с
!             ЭМБЕДДИРОВАННЫМИ литералами (паттерн Stage 10.7 / 10.10):
!               g=9.80665, ν=1.82e-6, k=0.56, ρ_w=1028, c_w=3974,
!               ρ_i=910, L_f=3.34e5, c_i=2009, T_i=−10,
!               β_T=3.0e-5, β_S=7.8e-4 [1/PSU], Le=100,
!               K_T=1.1e-3, K_S=3.1e-5, Ra_max=1e10, Ra_tr=1e7,
!               C_lam=0.27 (exp 1/4), C_turb=0.15 (exp 1/3), n=3,
!               EOS-80 коэффициенты Tf.
!             Production-функции вызываются ТОЛЬКО для фактического
!             (проверяемого) результата.
!
! Проверяемая формула (production, Stage 10.11):
!   Ra_eff = g·L³/(ν·α)·[β_T·(T_w−T_B) + β_S·(S_w−S_B)[PSU]·Le]
!   Nu = 0.27·Ra^0.25  (Ra < 1e7);  Nu = 0.15·Ra^(1/3)  (Ra ≥ 1e7)
!   Ra ограничивается сверху Ra_max = 1e10 (Nu → 0.15·(1e10)^(1/3) ≈ 323)
!   γ_T_nat = Nu·k/(L·ρ_w·c_w);  γ_S_nat = γ_T_nat·(K_S/K_T)
!   γ_eff = (γ_forced³ + γ_nat³)^(1/3)   (Churchill 1977, n=3)
!   Интерфейс: T_B = Tf(S_B,P); ρ_w c_w γ_T (T_w−T_B) = m(ρ_i L_f + ρ_i c_i (T_B−T_i));
!              S_B = γ_S S_w/(γ_S + (ρ_i/ρ_w)·m)
! ==============================================================================

program iceberg_test_10p11_natural_convection
    use iceberg_types, only: ocean_profile, set_basal_melt_scheme, &
                             BASAL_MELT_SCHEME_THREE_EQUATION, &
                             BASAL_MELT_SCHEME_FORCED_CONVECTION, &
                             BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL, &
                             natural_convection_transfer_coeff
    use iceberg_thermodynamics, only: compute_basal_melt, &
                             solve_three_equation_interface, &
                             solve_three_equation_interface_natural
    implicit none

    integer :: n_errors, n_checks
    real :: m_prod, t_iface, s_iface, m_ind, t_ind, s_ind
    real :: m_prod2, t_iface2, s_iface2
    real :: t_w, s_w, u_rel, l_char
    real :: gam_t_a, gam_s_a, gam_t_b, gam_s_b
    real :: gam_t_f, gam_t_mix, ratio
    real :: m_basal, t_draft, s_draft, tf_draft, delta_t
    real :: tf_ref, m_day
    real :: m_default

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.11.2 AUDIT: NATURAL-CONVECTION BASAL MELT"
    print *, "  Three-equation interface (Fujii 1973 + Churchill 1977)"
    print *, "=================================================="

    ! Стандартный сценарий (аналогично Python-контракту 10.11):
    ! T_w=+2°C, S_w=34.5 PSU, осадка D=50 м, длина L=100 м
    t_w = 2.0
    s_w = 0.0345
    tf_ref = tf_eos_ind(s_w, 50.0)

    ! ----------------------------------------------------------
    ! A. Холодный океан при U=0 (T_w < Tf): плавления нет, S_B=S_w
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface_natural(tf_ref - 0.5, s_w, 50.0, 0.0, &
                                                100.0, -10.0, .true., &
                                                t_iface, s_iface, m_prod)
    if (m_prod .eq. 0.0 .and. abs(s_iface - s_w) .lt. 1.0e-6) then
        print *, "OK A.1: cold ocean U=0: m=0, S_B=S_w=", s_iface
    else
        print *, "ERROR A.1: m=", m_prod, " S_B=", s_iface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(t_iface - tf_ref) .lt. 1.0e-4) then
        print *, "OK A.2: T_B = Tf(S_w): T_B=", t_iface, " Tf=", tf_ref
    else
        print *, "ERROR A.2: T_B=", t_iface, " Tf=", tf_ref
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! B. Zero-flow anchor: U=0, T_w=2°C, S_w=34.5 PSU, L=100 м
    !    m ≈ 1.638e-8 м/с = 1.4e-3 м/сут (Python cross-language contract)
    !    Сверка с независимой редукцией (литералы), 60+60 бисекция
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 0.0, 100.0, &
                                                -10.0, .true., &
                                                t_iface, s_iface, m_prod)
    call independent_reduction_natural(t_w, s_w, 50.0, 0.0, 100.0, &
                                       m_ind, s_ind, t_ind)
    if (abs(m_prod - m_ind)/max(abs(m_ind), 1.0e-12) .lt. 5.0e-3) then
        print *, "OK B.1: zero-flow m=", m_prod, " (ind=", m_ind, ")"
    else
        print *, "ERROR B.1: m=", m_prod, " m_ind=", m_ind
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    m_day = m_prod*86400.0
    if (m_day .ge. 1.0e-3 .and. m_day .le. 2.0e-3) then
        print *, "OK B.2: zero-flow m=", m_day, " m/day (Python anchor band)"
    else
        print *, "ERROR B.2: m=", m_day, " m/day outside [1e-3, 2e-3]"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(s_iface - s_ind)/max(abs(s_ind), 1.0e-12) .lt. 5.0e-3 .and. &
        abs(t_iface - t_ind) .lt. 5.0e-3) then
        print *, "OK B.3: interface state S_B=", s_iface, " T_B=", t_iface
    else
        print *, "ERROR B.3: S_B=", s_iface, " (ind ", s_ind, &
                 ") T_B=", t_iface, " (ind ", t_ind, ")"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (m_prod .gt. 1.0e-10 .and. m_prod .lt. 1.0e-6) then
        print *, "OK B.4: finite, non-vanishing melt (no NaN/zero) m=", m_prod
    else
        print *, "ERROR B.4: m=", m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! C. Ламинарная ветвь (Ra < 1e7): γ_T_nat ∝ L^(-1/4)
    !    Термический вклад только (ΔS=0): T_w=2, T_B=Tf, S_B=S_w
    !    γ(0.05)/γ(0.1) = 2^(1/4) ≈ 1.189207
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, s_w, &
                                           0.1, 0.0, gam_t_a, gam_s_a)
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, s_w, &
                                           0.05, 0.0, gam_t_b, gam_s_b)
    ratio = gam_t_b/gam_t_a
    if (abs(ratio - 1.189207) .lt. 1.0e-3) then
        print *, "OK C.1: laminar scaling gamma(L)^0.05/0.1=", ratio, &
                 " (expect 2^0.25=", 1.189207, ")"
    else
        print *, "ERROR C.1: ratio=", ratio
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(gam_t_a - 1.717408e-5)/1.717408e-5 .lt. 1.0e-3) then
        print *, "OK C.2: laminar gamma_T_nat(L=0.1)=", gam_t_a, &
                 " (ind 1.7174e-5)"
    else
        print *, "ERROR C.2: gamma_T_nat=", gam_t_a
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! D. Турбулентная ветвь (1e7 ≤ Ra ≤ 1e10, без капа): γ_T_nat ∝ L^(0)
    !    Галинный вклад: S_B = S_w − 1 PSU (ΔS_PSU = 1)
    !    γ(0.05)/γ(0.1) = 1.0
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, 0.0335, &
                                           0.1, 0.0, gam_t_a, gam_s_a)
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, 0.0335, &
                                           0.05, 0.0, gam_t_b, gam_s_b)
    ratio = gam_t_b/gam_t_a
    if (abs(ratio - 1.0) .lt. 1.0e-3) then
        print *, "OK D.1: turbulent gamma(0.05)/gamma(0.1)=", ratio, &
                 " (expect 1.0)"
    else
        print *, "ERROR D.1: ratio=", ratio
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(gam_t_a - 2.988611e-4)/2.988611e-4 .lt. 1.0e-3) then
        print *, "OK D.2: turbulent gamma_T_nat(L=0.1)=", gam_t_a, &
                 " (ind 2.9886e-4)"
    else
        print *, "ERROR D.2: gamma_T_nat=", gam_t_a
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! E. Кап Ra_max=1e10: Nu = 0.15·(1e10)^(1/3) ≈ 323.165, γ_T_nat ∝ 1/L
    !    Ra(L=100, ΔS=1 PSU) ≈ 3.07e12 > 1e10 -> каппируется
    !    γ(50)/γ(100) = 2.0;  γ(100) = 323.165·k/(100·ρ_w·c_w) ≈ 4.43e-7
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, 0.0335, &
                                           100.0, 0.0, gam_t_a, gam_s_a)
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, 0.0335, &
                                           50.0, 0.0, gam_t_b, gam_s_b)
    ratio = gam_t_b/gam_t_a
    if (abs(ratio - 2.0) .lt. 1.0e-3) then
        print *, "OK E.1: capped gamma(50)/gamma(100)=", ratio, &
                 " (expect 2.0, Nu pinned)"
    else
        print *, "ERROR E.1: ratio=", ratio
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(gam_t_a - 4.429877e-7)/4.429877e-7 .lt. 1.0e-3) then
        print *, "OK E.2: capped gamma_T_nat(L=100)=", gam_t_a, &
                 " (ind 4.43e-7)"
    else
        print *, "ERROR E.2: gamma_T_nat=", gam_t_a
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! F. Смешанная конвекция (Churchill, n=3): при U=0.1 м/с
    !    γ_forced = K_T·U = 1.1e-4; натуральный вклад ≪ 0.1%
    !    γ_eff/γ_forced − 1 ≈ 2.18e-8 (float64 реплика)
    !    Проверяем: γ_eff ∈ [0.999·γ_f, 1.001·γ_f] (натуральная не
    !    подавляет форсированную; численно неразличима на float32)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    gam_t_f = 1.1e-3*0.1
    call natural_convection_transfer_coeff(t_w, s_w, tf_ref, 0.0335, &
                                           100.0, 0.1, gam_t_mix, gam_s_a)
    if (gam_t_mix .ge. 0.999*gam_t_f .and. gam_t_mix .le. 1.001*gam_t_f) then
        print *, "OK F.1: mixed U=0.1: gamma_eff=", gam_t_mix, &
                 " gamma_forced=", gam_t_f, &
                 " (natural adds < 0.1%, float32-resolved)"
    else
        print *, "ERROR F.1: gamma_eff=", gam_t_mix, " gamma_f=", gam_t_f
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! G. Монотонность по U: m(0) < m(1e-3) < m(0.1) < m(1.0)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 0.0, 100.0, &
                                                -10.0, .true., &
                                                t_iface, s_iface, m_prod)
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 1.0e-3, 100.0, &
                                                -10.0, .true., &
                                                t_iface2, s_iface2, m_prod2)
    if (m_prod2 .gt. m_prod) then
        print *, "OK G.1: monotone 0<U: m(0)=", m_prod, " < m(1e-3)=", m_prod2
    else
        print *, "ERROR G.1: m(0)=", m_prod, " m(1e-3)=", m_prod2
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 0.1, 100.0, &
                                                -10.0, .true., &
                                                t_iface, s_iface, m_prod)
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 1.0, 100.0, &
                                                -10.0, .true., &
                                                t_iface2, s_iface2, m_prod2)
    if (m_prod2 .gt. m_prod) then
        print *, "OK G.2: monotone U: m(0.1)=", m_prod, " < m(1.0)=", m_prod2
    else
        print *, "ERROR G.2: m(0.1)=", m_prod, " m(1.0)=", m_prod2
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! H. Линейный режим при больших U (натуральный вклад < 0.1%):
    !    m(0.2)/m(0.1) ≈ 2 (следует из γ_T ∝ U)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 0.1, 100.0, &
                                                -10.0, .true., &
                                                t_iface, s_iface, m_prod)
    call solve_three_equation_interface_natural(t_w, s_w, 50.0, 0.2, 100.0, &
                                                -10.0, .true., &
                                                t_iface2, s_iface2, m_prod2)
    ratio = m_prod2/m_prod
    if (abs(ratio - 2.0)/2.0 .lt. 5.0e-3) then
        print *, "OK H.1: linear U-scaling m(0.2)/m(0.1)=", ratio, &
                 " (expect 2)"
    else
        print *, "ERROR H.1: ratio=", ratio
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! I. PRODUCTION end-to-end: compute_basal_melt в схеме
    !    THREE_EQUATION_NATURAL, U=0 (схема через set_basal_melt_scheme)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_production_chain(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! J. Селектор схем: baseline (FORCED) при U=0 даёт m=0 — натуральная
    !    конвекция активна ТОЛЬКО на пути THREE_EQUATION_NATURAL
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call set_basal_melt_scheme(BASAL_MELT_SCHEME_FORCED_CONVECTION)
    call singular_basal_melt(t_w, s_w, 50.0, 100.0, 0.0, 0.0, &
                             m_prod, t_iface, s_iface)
    if (m_prod .eq. 0.0) then
        print *, "OK J.1: baseline FORCED at U=0: m=0 (unchanged)"
    else
        print *, "ERROR J.1: baseline m=", m_prod
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)
    call singular_basal_melt(t_w, s_w, 50.0, 100.0, 0.1, 0.0, &
                             m_prod, t_iface, s_iface)
    call independent_reduction_forced(t_w, s_w, 50.0, 0.1, m_ind, s_ind)
    if (abs(m_prod - m_ind)/max(abs(m_ind), 1.0e-12) .lt. 1.0e-3) then
        print *, "OK J.2: THREE_EQUATION regression m(U=0.1)=", m_prod, &
                 " (ind=", m_ind, ")"
    else
        print *, "ERROR J.2: m=", m_prod, " m_ind=", m_ind
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL)
    call singular_basal_melt(t_w, s_w, 50.0, 100.0, 0.1, 0.0, &
                             m_prod, t_iface, s_iface)
    if (m_prod .gt. 0.0 .and. m_prod/m_default .gt. 0.0) then
        print *, "OK J.3: NATURAL at U=0.1 finite m=", m_prod
    else
        print *, "ERROR J.3: m=", m_prod
        n_errors = n_errors + 1
    end if

    ! Восстановление baseline-схемы (как в производственном init)
    call set_basal_melt_scheme(BASAL_MELT_SCHEME_FORCED_CONVECTION)

    ! ==========================================================
    print *, "=================================================="
    print *, "  TOTAL CHECKS: ", n_checks, " ERRORS: ", n_errors
    print *, "=================================================="
    if (n_errors .gt. 0) stop 1

contains

    ! ==========================================================
    !   EOS-80 ТОЧКА ЗАМЕРЗАНИЯ (независимые литералы)
    ! ==========================================================
    pure real function tf_eos_ind(s_mass, depth_m)
        real, intent(in) :: s_mass, depth_m
        real :: s_psu, p_dbar
        s_psu = s_mass*1000.0
        p_dbar = 1028.0*9.80665*depth_m/1.0e4
        tf_eos_ind = (-0.0575 + 1.710523e-3*sqrt(s_psu) &
                      - 2.154996e-4*s_psu)*s_psu - 7.53e-4*p_dbar
    end function tf_eos_ind

    ! ==========================================================
    !   НЕЗАВИСИМЫЙ КОЭФФИЦИЕНТ НАТУРАЛЬНОЙ КОНВЕКЦИИ
    !   (embedded literals, идентичная формула production)
    ! ==========================================================
    pure subroutine nat_coeff_ind(t_w, s_w, t_b, s_b, l_char, u_rel, &
                                  gamma_t, gamma_s)
        real, intent(in) :: t_w, s_w, t_b, s_b, l_char, u_rel
        real, intent(out) :: gamma_t, gamma_s

        real :: dt, ds_psu, ther_dif, ra, nu_num
        real :: gt_f, gs_f, gt_nat, gs_nat

        gt_f = 1.1e-3*u_rel
        gs_f = 3.1e-5*u_rel
        if (l_char .le. 0.0) then
            gamma_t = gt_f
            gamma_s = gs_f
            return
        end if
        dt = t_w - t_b
        ds_psu = (s_w - s_b)*1000.0
        ther_dif = 0.56/(1028.0*3974.0)
        if (dt .gt. 0.0 .or. ds_psu .gt. 0.0) then
            ra = 9.80665*l_char**3/(1.82e-6*ther_dif)* &
                 (3.0e-5*dt + 7.8e-4*ds_psu*100.0)
        else
            ra = 0.0
        end if
        if (ra .gt. 1.0e10) ra = 1.0e10
        if (ra .gt. 0.0) then
            if (ra .lt. 1.0e7) then
                nu_num = 0.27*ra**0.25
            else
                nu_num = 0.15*ra**(1.0/3.0)
            end if
        else
            nu_num = 0.0
        end if
        gt_nat = nu_num*0.56/(l_char*1028.0*3974.0)
        gs_nat = gt_nat*(3.1e-5/1.1e-3)
        if (gt_f .gt. 0.0 .and. gt_nat .gt. 0.0) then
            gamma_t = (gt_f**3 + gt_nat**3)**(1.0/3.0)
            gamma_s = (gs_f**3 + gs_nat**3)**(1.0/3.0)
        else if (gt_f .gt. 0.0) then
            gamma_t = gt_f
            gamma_s = gs_f
        else
            gamma_t = gt_nat
            gamma_s = gs_nat
        end if
    end subroutine nat_coeff_ind

    ! ==========================================================
    !   НЕЗАВИСИМАЯ РЕДУКЦИЯ (NATURAL, embedded literals)
    !   Зеркалит производственную последовательность
    !   solve_three_equation_interface_natural: 60+60 бисекция с
    !   пересчётом коэффициентов на каждом шаге.
    ! ==========================================================
    subroutine independent_reduction_natural(t_w_in, s_w_in, depth_in, &
                                             u_rel_in, l_char_in, &
                                             m_out, s_b_out, t_b_out)
        real, intent(in) :: t_w_in, s_w_in, depth_in, u_rel_in, l_char_in
        real, intent(out) :: m_out, s_b_out, t_b_out

        real :: tf_sw, m_lo, m_hi, m_mid, f_val, l_heat
        real :: s_b, t_b, gt, gs
        integer :: iter

        tf_sw = tf_eos_ind(s_w_in, depth_in)
        if (t_w_in .le. tf_sw) then
            m_out = 0.0
            s_b_out = s_w_in
            t_b_out = tf_sw
            return
        end if

        m_lo = 0.0
        call nat_coeff_ind(t_w_in, s_w_in, tf_sw, s_w_in, l_char_in, &
                           u_rel_in, gt, gs)
        m_hi = max(1028.0*3974.0*gt*(t_w_in - tf_sw)/(910.0*3.34e5), 1.0e-9)

        iter = 0
        do while (.true.)
            s_b = gs*s_w_in/(gs + (910.0/1028.0)*m_hi)
            t_b = tf_eos_ind(s_b, depth_in)
            l_heat = 910.0*3.34e5 + 910.0*2009.0*max(t_b - (-10.0), 0.0)
            call nat_coeff_ind(t_w_in, s_w_in, t_b, s_b, l_char_in, &
                               u_rel_in, gt, gs)
            f_val = 1028.0*3974.0*gt*(t_w_in - t_b) - m_hi*l_heat
            if (f_val .le. 0.0 .or. iter .ge. 60) exit
            m_hi = m_hi*2.0
            iter = iter + 1
        end do

        do iter = 1, 60
            m_mid = 0.5*(m_lo + m_hi)
            s_b = gs*s_w_in/(gs + (910.0/1028.0)*m_mid)
            t_b = tf_eos_ind(s_b, depth_in)
            l_heat = 910.0*3.34e5 + 910.0*2009.0*max(t_b - (-10.0), 0.0)
            call nat_coeff_ind(t_w_in, s_w_in, t_b, s_b, l_char_in, &
                               u_rel_in, gt, gs)
            f_val = 1028.0*3974.0*gt*(t_w_in - t_b) - m_mid*l_heat
            if (f_val .gt. 0.0) then
                m_lo = m_mid
            else
                m_hi = m_mid
            end if
        end do

        m_out = 0.5*(m_lo + m_hi)
        s_b_out = gs*s_w_in/(gs + (910.0/1028.0)*m_out)
        t_b_out = tf_eos_ind(s_b_out, depth_in)
    end subroutine independent_reduction_natural

    ! ==========================================================
    !   НЕЗАВИСИМАЯ РЕДУКЦИЯ (FORCED, embedded literals)
    !   Контроль регрессии пути THREE_EQUATION (Stage 10.10.1)
    ! ==========================================================
    subroutine independent_reduction_forced(t_w_in, s_w_in, depth_in, &
                                            u_rel_in, m_out, s_b_out)
        real, intent(in) :: t_w_in, s_w_in, depth_in, u_rel_in
        real, intent(out) :: m_out, s_b_out

        real :: tf_sw, m_lo, m_hi, m_mid, f_val, l_heat
        real :: s_b, t_b, gt, gs
        integer :: iter

        tf_sw = tf_eos_ind(s_w_in, depth_in)
        if (t_w_in .le. tf_sw .or. u_rel_in .le. 0.0) then
            m_out = 0.0
            s_b_out = s_w_in
            return
        end if
        gt = 1.1e-3*u_rel_in
        gs = 3.1e-5*u_rel_in
        m_lo = 0.0
        m_hi = max(1028.0*3974.0*gt*(t_w_in - tf_sw)/(910.0*3.34e5), 1.0e-9)
        do iter = 1, 60
            m_mid = 0.5*(m_lo + m_hi)
            s_b = gs*s_w_in/(gs + (910.0/1028.0)*m_mid)
            t_b = tf_eos_ind(s_b, depth_in)
            l_heat = 910.0*3.34e5 + 910.0*2009.0*max(t_b - (-10.0), 0.0)
            f_val = 1028.0*3974.0*gt*(t_w_in - t_b) - m_mid*l_heat
            if (f_val .gt. 0.0) then
                m_lo = m_mid
            else
                m_hi = m_mid
            end if
        end do
        m_out = 0.5*(m_lo + m_hi)
        s_b_out = gs*s_w_in/(gs + (910.0/1028.0)*m_out)
    end subroutine independent_reduction_forced

    ! ==========================================================
    !   PRODUCTION END-TO-END (текущая схема, U через профиль)
    ! ==========================================================
    subroutine singular_basal_melt(t_val, s_val, draft, l_char, u_val, &
                                   v_val, m_out, t_if, s_if)
        real, intent(in) :: t_val, s_val, draft, l_char, u_val, v_val
        real, intent(out) :: m_out, t_if, s_if
        type(ocean_profile) :: prof

        call build_profile(t_val, s_val, u_val, v_val, prof)
        call compute_basal_melt(prof, draft, l_char, u_val, v_val, &
                                t_draft, s_draft, tf_draft, delta_t, &
                                m_out, t_if, s_if)
    end subroutine singular_basal_melt

    subroutine check_production_chain(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof
        real :: m_exp, s_b_exp, t_b_exp, u_rel_d
        real :: m_bulk

        ! (a) Ноль-поток anchor через production-путь
        call build_profile(t_w, s_w, 0.0, 0.0, prof)
        call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal, &
                                t_iface, s_iface)
        call independent_reduction_natural(t_draft, s_draft, 50.0, 0.0, 100.0, &
                                           m_exp, s_b_exp, t_b_exp)
        if (abs(m_basal - m_exp)/max(abs(m_exp), 1.0e-12) .lt. 5.0e-3) then
            print *, "OK I.1: production end-to-end U=0 m=", m_basal, &
                     " (ind=", m_exp, ")"
        else
            print *, "ERROR I.1: m_basal=", m_basal, " m_exp=", m_exp
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (m_basal .gt. 0.0 .and. t_iface .gt. tf_draft .and. &
            s_iface .lt. s_draft) then
            print *, "OK I.2: interface freshening: T_B=", t_iface, &
                     " > Tf=", tf_draft, ", S_B=", s_iface, " < S_w=", s_draft
        else
            print *, "ERROR I.2: T_B=", t_iface, " Tf=", tf_draft, &
                     " S_B=", s_iface, " S_w=", s_draft
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_bulk)
        if (m_bulk .eq. 0.0 .and. m_basal .gt. 0.0) then
            print *, "OK I.3: scheme switch effective: NATURAL m=", m_basal, &
                     " vs THREE_EQUATION(U=0) m=", m_bulk
        else
            print *, "ERROR I.3: m_bulk=", m_bulk, " m_natural=", m_basal
            n_errors = n_errors + 1
        end if

        ! Сохраняем значение для проверки J.3 (конечность при U=0.1)
        m_default = m_basal
        u_rel_d = 0.1
        call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL)
        call build_profile(t_w, s_w, u_rel_d, 0.0, prof)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal, &
                                t_iface, s_iface)
        call independent_reduction_natural(t_draft, s_draft, 50.0, u_rel_d, &
                                           100.0, m_exp, s_b_exp, t_b_exp)
        n_checks = n_checks + 1
        if (abs(m_basal - m_exp)/max(abs(m_exp), 1.0e-12) .lt. 5.0e-3) then
            print *, "OK I.4: production end-to-end U=0.1 m=", m_basal, &
                     " (ind=", m_exp, ")"
        else
            print *, "ERROR I.4: m_basal=", m_basal, " m_exp=", m_exp
            n_errors = n_errors + 1
        end if
    end subroutine check_production_chain

    subroutine build_profile(t_val, s_val, u_val, v_val, prof)
        real, intent(in) :: t_val, s_val, u_val, v_val
        type(ocean_profile), intent(out) :: prof

        integer :: k
        integer, parameter :: n = 18

        prof%nlevels = n
        allocate (prof%z(n), prof%dz(n), prof%temp(n), prof%salt(n))
        allocate (prof%u(n), prof%v(n), prof%u_rel(n))

        prof%z = (/2.5, 7.5, 12.5, 17.5, 25.0, 35.0, 45.0, 55.0, 70.0, &
                   90.0, 120.0, 160.0, 210.0, 260.0, 320.0, 390.0, 460.0, 550.0/)
        prof%dz = (/5.0, 5.0, 5.0, 5.0, 10.0, 10.0, 10.0, 10.0, 20.0, 20.0, &
                    30.0, 40.0, 50.0, 50.0, 60.0, 70.0, 70.0, 100.0/)

        do k = 1, n
            prof%temp(k) = t_val
            prof%salt(k) = s_val
            prof%u(k) = u_val
            prof%v(k) = v_val
            prof%u_rel(k) = sqrt(u_val**2 + v_val**2)
        end do
    end subroutine build_profile

end program iceberg_test_10p11_natural_convection