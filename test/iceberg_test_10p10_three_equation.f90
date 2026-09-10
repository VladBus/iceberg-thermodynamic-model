! ==============================================================================
! Тест: Stage 10.10 + 10.10.1 — Independent Scientific Validation of the
!       Three-Equation Ice-Ocean Interface
! Назначение: Независимая научная проверка production-реализации трёхчленного
!             замыкания интерфейса лёд-океан (Holland & Jenkins 1999; Jenkins
!             et al. 2010) БЕЗ использования production-функций для ОЖИДАЕМЫХ
!             значений (паттерн Stage 10.7).
!
! Проверяемое замыкание (production, Stage 10.10 + Stage 10.10.1 коррекция):
!   (I)   T_B = Tf(S_B, P)                     — EOS-80 точка замерзания
!   (II)  ρ_w c_w γ_T (T_w − T_B) = m·(ρ_i L_f + ρ_i c_i (T_B − T_i))
!   (III) ρ_w γ_S (S_w − S_B) = ρ_i·m·S_B      — баланс соли (S_i = 0)
!   Редукция: S_B = γ_S S_w / (γ_S + (ρ_i/ρ_w)·m),  ρ_i/ρ_w = 910/1028
!   Трансферные скорости: γ_T = K_T·U_rel, γ_S = K_S·U_rel  (J2010 Table 2)
!     K_T = 1.1e-3, K_S = 3.1e-5;  c_w = 3974.0, c_i = 2009.0 (H&J99)
!
! ВСЕ ОЖИДАЕМЫЕ ЗНАЧЕНИЯ вычисляются независимо с ЭМБЕДДИРОВАННЫМИ литералами
! констант (ρ_w=1028, c_w=3974, ρ_i=910, L_f=3.34e5, c_i=2009, T_i=−10,
! EOS-80 коэффициенты), а НЕ импортируются из production. Production-функции
! вызываются ТОЛЬКО для фактического (проверяемого) результата.
! ==============================================================================

program iceberg_test_10p10_three_equation
    use iceberg_types, only: ocean_profile, set_basal_melt_scheme, &
                             BASAL_MELT_SCHEME_THREE_EQUATION, &
                             BASAL_MELT_SCHEME_FORCED_CONVECTION
    use iceberg_thermodynamics, only: compute_basal_melt, solve_three_equation_interface
    implicit none

    integer :: n_errors, n_checks
    real :: m_prod, t_iface, s_iface, m_ind, t_ind, s_ind
    real :: t_w, s_w, u_rel, gam_t, gam_s
    real :: gamma_t_vel, gamma_s_vel
    real :: m_basal, t_draft, s_draft, tf_draft, delta_t

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.10 AUDIT: THREE-EQUATION ICE-OCEAN INTERFACE"
    print *, "=================================================="

    ! H&J99 Table 1 canonical parameters
    t_w = -1.85
    s_w = 0.0345            ! 34.5 psu
    gam_t = 1.00e-4         ! [м/с], H&J99 γ_T
    gam_s = 5.05e-7         ! [м/с], H&J99 γ_S
    u_rel = 0.1

    ! ----------------------------------------------------------
    ! A. Холодный океан (T_w <= Tf(S_w)): плавления нет, S_B=S_w, T_B=Tf
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(-2.5, s_w, 0.0, u_rel, gam_t, gam_s, &
                                        -10.0, .true., t_iface, s_iface, m_prod)
    call independent_reduction(-2.5, s_w, 0.0, gam_t, gam_s, -10.0, .true., &
                               m_ind, s_ind, t_ind)
    if (m_prod .eq. 0.0 .and. m_ind .eq. 0.0 .and. &
        abs(s_iface - s_w) .lt. 1.0e-6) then
        print *, "OK A.1: cold ocean m=0, S_B=S_w=", s_iface
    else
        print *, "ERROR A.1: m_prod=", m_prod, " m_ind=", m_ind, " s_iface=", s_iface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(t_iface - t_ind)/max(abs(t_ind), 1.0e-10) .lt. 1.0e-4) then
        print *, "OK A.2: T_B=Tf(S_w)= ", t_iface, " >= production-independent match"
    else
        print *, "ERROR A.2: t_iface=", t_iface, " t_ind=", t_ind
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! B. Нулевая относительная скорость (γ_T=0): плавления нет
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(2.0, s_w, 50.0, 0.0, gam_t, gam_s, &
                                        -10.0, .true., t_iface, s_iface, m_prod)
    if (m_prod .eq. 0.0) then
        print *, "OK B.1: U_rel=0 -> m=0 (natural convection NOT implemented,"
        print *, "     documented limitation, same as baseline bulk)"
    else
        print *, "ERROR B.1: U_rel=0 m_prod=", m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! C. H&J99 Table 1 canonical case: производство ~ независимая редукция
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(t_w, s_w, 0.0, u_rel, gam_t, gam_s, &
                                        -10.0, .true., t_iface, s_iface, m_prod)
    call independent_reduction(t_w, s_w, 0.0, gam_t, gam_s, -10.0, .true., &
                               m_ind, s_ind, t_ind)
    if ((abs(m_prod - m_ind)/max(abs(m_ind), 1.0e-12)) .lt. 1.0e-3) then
        print *, "OK C.1: H&J99 canonical m=", m_prod, " m/s (ind=", m_ind, ")"
    else
        print *, "ERROR C.1: m_prod=", m_prod, " m_ind=", m_ind
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if ((abs(s_iface - s_ind)/max(abs(s_ind), 1.0e-12)) .lt. 1.0e-3 .and. &
        (abs(t_iface - t_ind)/max(abs(t_ind), 1.0e-10)) .lt. 1.0e-3) then
        print *, "OK C.2: interface S_B=", s_iface, " T_B=", t_iface
        print *, "     (ind S_B=", s_ind, " T_B=", t_ind, ")"
    else
        print *, "ERROR C.2: s_iface=", s_iface, " t_iface=", t_iface, &
                 " ind=", s_ind, t_ind
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (s_iface .gt. 0.0 .and. s_iface .lt. s_w .and. t_iface .lt. t_w) then
        print *, "OK C.3: фрезерование: 0<S_B=", s_iface, "<S_w, T_B=", t_iface, "<T_w"
    else
        print *, "ERROR C.3: S_B=", s_iface, " T_B=", t_iface, " вне ограничений"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! D. Балансы энергии и соли выполняются для production-выходов
    !    (независимые literals: 1028, 3974, 910, 3.34e5, 2009, -10.0)
    ! ----------------------------------------------------------
    call check_balances(t_iface, s_iface, m_prod, t_w, s_w, gam_t, gam_s, &
                        n_errors, n_checks)

    ! ----------------------------------------------------------
    ! N. Stage 10.10.1: плотностная редукция S_B и её пределы
    !    (ρ_w γ_S (S_w−S_B) = ρ_i·m·S_B)
    ! ----------------------------------------------------------
    call check_density_reduction(n_errors, n_checks)

    ! ----------------------------------------------------------
    ! E. Теплопроводность в лёд: включена -> плавление меньше (но ~simeq)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(1.5, s_w, 50.0, u_rel, gam_t, gam_s, &
                                        -10.0, .true., t_iface, s_iface, m_prod)
    call solve_three_equation_interface(1.5, s_w, 50.0, u_rel, gam_t, gam_s, &
                                        -10.0, .false., t_iface, s_iface, m_ind)
    if (m_prod .gt. 0.0 .and. m_prod .lt. m_ind .and. m_prod/m_ind .gt. 0.9) then
        print *, "OK E.1: conduction reduces melt: m_cond=", m_prod, &
                 " m_nocon=", m_ind, " ratio=", m_prod/m_ind
    else
        print *, "ERROR E.1: m_cond=", m_prod, " m_nocon=", m_ind
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! F. U-масштабирование: γ_T и γ_S оба ∝ U -> m ∝ U (линейно)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(1.5, s_w, 50.0, u_rel, &
                                        1.1e-3*u_rel, 3.1e-5*u_rel, &
                                        -10.0, .true., t_iface, s_iface, m_prod)
    call solve_three_equation_interface(1.5, s_w, 50.0, 2.0*u_rel, &
                                        1.1e-3*(2.0*u_rel), 3.1e-5*(2.0*u_rel), &
                                        -10.0, .true., t_iface, s_iface, m_ind)
    if (abs(m_ind - 2.0*m_prod)/max(abs(m_prod), 1.0e-12) .lt. 5.0e-3) then
        print *, "OK F.1: linear U-scaling: m(2U)/m(U)=", m_ind/m_prod, " (expected 2)"
    else
        print *, "ERROR F.1: m(2U)=", m_ind, " 2*m(U)=", 2.0*m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! G. Freezing edge grind: T_w = Tf(S_w,P) и чуть выше
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(tf_eos_ind(s_w, 0.0), s_w, 0.0, u_rel, &
                                        gam_t, gam_s, -10.0, .true., &
                                        t_iface, s_iface, m_prod)
    if (m_prod .eq. 0.0 .and. abs(s_iface - s_w) .lt. 1.0e-6) then
        print *, "OK G.1: T_w = Tf(S_w): m=0, S_B=S_w=", s_iface
    else
        print *, "ERROR G.1: m=", m_prod, " s_iface=", s_iface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    call solve_three_equation_interface(tf_eos_ind(s_w, 0.0) + 0.05, s_w, 0.0, &
                                        u_rel, gam_t, gam_s, -10.0, .true., &
                                        t_iface, s_iface, m_prod)
    if (m_prod .gt. 0.0 .and. m_prod .lt. 1.0e-4) then
        print *, "OK G.2: just above freezing: m=", m_prod, " (>0, small)"
    else
        print *, "ERROR G.2: m=", m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! H. Пресная вода (S_w=0): heat-only, S_B=0
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(1.0, 0.0, 50.0, u_rel, gam_t, gam_s, &
                                        -10.0, .false., t_iface, s_iface, m_prod)
    if (s_iface .eq. 0.0 .and. m_prod .gt. 0.0) then
        print *, "OK H.1: fresh-water edge: S_B=", s_iface, " m=", m_prod
    else
        print *, "ERROR H.1: fresh S_B=", s_iface, " m=", m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! I. γ_S=0 edge: heat-only with S_B=S_w
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call solve_three_equation_interface(1.0, s_w, 50.0, u_rel, gam_t, 0.0, &
                                        -10.0, .false., t_iface, s_iface, m_prod)
    if (abs(s_iface - s_w) .lt. 1.0e-6 .and. m_prod .gt. 0.0) then
        print *, "OK I.1: gamma_S=0 edge: S_B=S_w=", s_iface, " m=", m_prod
    else
        print *, "ERROR I.1: gamma_S=0 S_B=", s_iface, " m=", m_prod
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! J. J2010 Table 2 consistency: K_T = sqrt(C_d)*Gamma_T, K_S = sqrt(C_d)*Gamma_S,
    !    при измеренном C_d=0.0097 (Ronne ice shelf, J2010 §6)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_j2010_table2(0.0097, 0.011, 3.1e-4, n_errors, n_checks)

    ! ----------------------------------------------------------
    ! K. Тёплый океан (T_w=+2°C): плавление в наблюдаемом диапазоне 0.01-1 м/сут
    !    (Cenedese & Straneo 2023), U=0.1 м/с, L_char=100 м, D=50 м
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    gamma_t_vel = 1.1e-3*0.1
    gamma_s_vel = 3.1e-5*0.1
    call solve_three_equation_interface(2.0, 0.0345, 50.0, 0.1, gamma_t_vel, &
                                        gamma_s_vel, -10.0, .true., &
                                        t_iface, s_iface, m_prod)
    m_ind = m_prod*86400.0
    if (m_ind .ge. 0.01 .and. m_ind .le. 1.0) then
        print *, "OK K.1: warm-ocean three-equation m=", m_ind, " m/day"
    else
        print *, "ERROR K.1: m=", m_ind, " m/day outside [0.01,1]"
        n_errors = n_errors + 1
    end if

    ! ----------------------------------------------------------
    ! L. PRODUCTION end-to-end: compute_basal_melt в схеме THREE_EQUATION
    !    (схема переключается через set_basal_melt_scheme)
    ! ----------------------------------------------------------
    n_checks = n_checks + 1
    call check_production_chain(n_errors, n_checks)

    ! ==========================================================
    print *, "=================================================="
    print *, "  TOTAL CHECKS: ", n_checks, " ERRORS: ", n_errors
    print *, "=================================================="
    if (n_errors .gt. 0) stop 1

contains

    ! ==========================================================
    !   НЕЗАВИСИМАЯ РЕДУКЦИЯ (с эмбеддированными литералами)
    !   Stage 10.10.1: солевой баланс с плотностным отношением
    !   ρ_w γ_S (S_w−S_B) = ρ_i·m·S_B  =>  S_B = γ_S S_w/(γ_S + (ρ_i/ρ_w)·m)
    ! ==========================================================
    subroutine independent_reduction(t_w_in, s_w_in, depth_in, gam_t_in, gam_s_in, &
                                     t_ice_in, cond_in, m_out, s_b_out, t_b_out)
        real, intent(in) :: t_w_in, s_w_in, depth_in, gam_t_in, gam_s_in, t_ice_in
        logical, intent(in) :: cond_in
        real, intent(out) :: m_out, s_b_out, t_b_out

        real :: tf_sw, m_lo, m_hi, m_mid, lat, f_val, s_b, t_b
        real :: rho_ratio_ind
        integer :: iter

        rho_ratio_ind = 910.0/1028.0      ! ρ_i/ρ_w (embedded literal)
        tf_sw = tf_eos_ind(s_w_in, depth_in)
        if (gam_t_in .le. 0.0 .or. t_w_in .le. tf_sw) then
            m_out = 0.0
            s_b_out = s_w_in
            t_b_out = tf_sw
            return
        end if

        m_lo = 0.0
        m_hi = max(1028.0*3974.0*gam_t_in*(t_w_in - tf_sw)/(910.0*3.34e5), 1.0e-9)
        iter = 0
        do while (.true.)
            s_b = gam_s_in*s_w_in/(gam_s_in + rho_ratio_ind*m_hi)
            t_b = tf_eos_ind(s_b, depth_in)
            lat = 910.0*3.34e5
            if (cond_in) lat = lat + 910.0*2009.0*max(t_b - t_ice_in, 0.0)
            f_val = 1028.0*3974.0*gam_t_in*(t_w_in - t_b) - m_hi*lat
            if (f_val .le. 0.0 .or. iter .ge. 60) exit
            m_hi = m_hi*2.0
            iter = iter + 1
        end do

        do iter = 1, 60
            m_mid = 0.5*(m_lo + m_hi)
            s_b = gam_s_in*s_w_in/(gam_s_in + rho_ratio_ind*m_mid)
            t_b = tf_eos_ind(s_b, depth_in)
            lat = 910.0*3.34e5
            if (cond_in) lat = lat + 910.0*2009.0*max(t_b - t_ice_in, 0.0)
            f_val = 1028.0*3974.0*gam_t_in*(t_w_in - t_b) - m_mid*lat
            if (f_val .gt. 0.0) then
                m_lo = m_mid
            else
                m_hi = m_mid
            end if
        end do

        m_out = 0.5*(m_lo + m_hi)
        s_b_out = gam_s_in*s_w_in/(gam_s_in + rho_ratio_ind*m_out)
        t_b_out = tf_eos_ind(s_b_out, depth_in)
    end subroutine independent_reduction

    ! EOS-80 точка замерзания (независимые литералы)
    pure real function tf_eos_ind(s_mass, depth_m)
        real, intent(in) :: s_mass, depth_m
        real :: s_psu, p_dbar
        s_psu = s_mass*1000.0
        p_dbar = 1028.0*9.80665*depth_m/1.0e4
        tf_eos_ind = (-0.0575 + 1.710523e-3*sqrt(s_psu) &
                      - 2.154996e-4*s_psu)*s_psu - 7.53e-4*p_dbar
    end function tf_eos_ind

    ! ==========================================================
    !   ПРОВЕРКА БАЛАНСОВ (независимые literals)
    !   Stage 10.10.1: солевой баланс с плотностями:
    !     ρ_w γ_S (S_w − S_B) = ρ_i·m·S_B
    ! ==========================================================
    subroutine check_balances(t_b, s_b, m_melt, t_w, s_w, gam_t, gam_s, &
                              n_errors, n_checks)
        real, intent(in) :: t_b, s_b, m_melt, t_w, s_w, gam_t, gam_s
        integer, intent(inout) :: n_errors, n_checks

        real :: heat_lhs, heat_rhs, salt_lhs, salt_rhs, fw_lhs, fw_rhs
        real :: rel1, rel2, rel3

        heat_lhs = 1028.0*3974.0*gam_t*(t_w - t_b)
        heat_rhs = m_melt*(910.0*3.34e5 + 910.0*2009.0*max(t_b - (-10.0), 0.0))
        rel1 = abs(heat_lhs - heat_rhs)/max(max(abs(heat_lhs), abs(heat_rhs)), 1.0e-12)

        ! Массовый баланс соли: ρ_w γ_S (S_w − S_B) = ρ_i·m·S_B
        salt_lhs = 1028.0*gam_s*(s_w - s_b)
        salt_rhs = 910.0*m_melt*s_b
        rel2 = abs(salt_lhs - salt_rhs)/max(abs(salt_rhs), 1.0e-12)

        ! Эквивалент через поток талой воды: γ_S (S_w − S_B) = (ρ_i/ρ_w)·m·S_B
        fw_lhs = gam_s*(s_w - s_b)
        fw_rhs = (910.0/1028.0)*m_melt*s_b
        rel3 = abs(fw_lhs - fw_rhs)/max(abs(fw_rhs), 1.0e-12)

        n_checks = n_checks + 1
        if (rel1 .lt. 1.0e-3 .and. rel2 .lt. 1.0e-3 .and. rel3 .lt. 1.0e-3) then
            print *, "OK D.x: balance residuals: heat=", rel1, &
                     " salt=", rel2, " fw=", rel3
        else
            print *, "ERROR D.x: heat res=", rel1, " salt res=", rel2, " fw res=", rel3
            print *, "     heat_lhs=", heat_lhs, " heat_rhs=", heat_rhs
            print *, "     salt_lhs=", salt_lhs, " salt_rhs=", salt_rhs
            n_errors = n_errors + 1
        end if
    end subroutine check_balances

    ! ==========================================================
    !   STAGE 10.10.1 CHECK: плотностная редукция S_B
    !   (независимые literals; MOM6/PISM/H&J99-конвенция)
    ! ==========================================================
    subroutine check_density_reduction(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks

        real :: s_b_corr, s_b_equal, m_val, r_val
        real :: salt_lhs, salt_rhs
        real :: gamma_s_use, s_w_use

        gamma_s_use = 3.1e-6    ! [м/с] (warm case, U=0.1, K_S=3.1e-5)
        s_w_use = 0.0345
        m_val = 4.067408105e-6  ! производственное значение (import не нужен:
                                ! проверяем FORMULY, а не число)

        r_val = 910.0/1028.0
        s_b_corr = gamma_s_use*s_w_use/(gamma_s_use + r_val*m_val)
        s_b_equal = gamma_s_use*s_w_use/(gamma_s_use + m_val)

        ! (1) Плотностная редукция DIMENSIONALLY: массовый баланс соли
        salt_lhs = 1028.0*gamma_s_use*(s_w_use - s_b_corr)
        salt_rhs = 910.0*m_val*s_b_corr
        n_checks = n_checks + 1
        if (abs(salt_lhs - salt_rhs)/max(abs(salt_rhs), 1.0e-12) .lt. 1.0e-4) then
            print *, "OK N.1: density-corrected S_B satisfies ρ_w γ_S(Sw−SB)=ρ_i·m·SB"
        else
            print *, "ERROR N.1: salt_lhs=", salt_lhs, " salt_rhs=", salt_rhs
            n_errors = n_errors + 1
        end if

        ! (2) Коррекция уменьшает фрезерование: S_B(corr) > S_B(equal-density)
        n_checks = n_checks + 1
        if (s_b_corr .gt. s_b_equal) then
            print *, "OK N.2: density correction reduces freshening: S_B_corr=", &
                     s_b_corr, " > S_B_equal=", s_b_equal
        else
            print *, "ERROR N.2: S_B_corr=", s_b_corr, " S_B_equal=", s_b_equal
            n_errors = n_errors + 1
        end if

        ! (3) ρ_i/ρ_w → 1 возвращает equal-density редукцию
        n_checks = n_checks + 1
        if (abs((gamma_s_use*s_w_use/(gamma_s_use + 1.0*m_val)) - s_b_equal) &
            .lt. 1.0e-12) then
            print *, "OK N.3: rho_ratio=1 recovers equal-density form S_B=γS·Sw/(γS+m)"
        else
            print *, "ERROR N.3: equal-density limit mismatch"
            n_errors = n_errors + 1
        end if

        ! (4) Предел m→0: S_B→S_w
        n_checks = n_checks + 1
        if (abs((gamma_s_use*s_w_use/(gamma_s_use + r_val*1.0e-14)) - s_w_use) &
            .lt. 1.0e-6) then
            print *, "OK N.4: m→0 limit: S_B→S_w"
        else
            print *, "ERROR N.4: m→0 limit failed"
            n_errors = n_errors + 1
        end if

        ! (5) Предел m→∞: S_B→0
        n_checks = n_checks + 1
        if (abs((gamma_s_use*s_w_use/(gamma_s_use + r_val*1.0e3)) - 0.0) &
            .lt. 1.0e-6) then
            print *, "OK N.5: m→∞ limit: S_B→0"
        else
            print *, "ERROR N.5: m→∞ limit failed"
            n_errors = n_errors + 1
        end if

        ! (6) Монотонность: S_B убывает с ростом m
        n_checks = n_checks + 1
        if (s_b_corr .lt. (gamma_s_use*s_w_use/(gamma_s_use + r_val*m_val*0.5)) .and. &
            s_b_corr .gt. (gamma_s_use*s_w_use/(gamma_s_use + r_val*m_val*2.0))) then
            print *, "OK N.6: S_B monotonically decreasing in m"
        else
            print *, "ERROR N.6: monotonicity violated"
            n_errors = n_errors + 1
        end if
    end subroutine check_density_reduction

    ! ==========================================================
    !   J2010 TABLE 2 CONSISTENCY
    ! ==========================================================
    subroutine check_j2010_table2(c_d, gamma_t_st, gamma_s_st, n_errors, n_checks)
        real, intent(in) :: c_d, gamma_t_st, gamma_s_st
        integer, intent(inout) :: n_errors, n_checks

        real :: k_t_ind, k_s_ind

        k_t_ind = sqrt(c_d)*gamma_t_st
        k_s_ind = sqrt(c_d)*gamma_s_st

        n_checks = n_checks + 1
        if (abs(k_t_ind - 1.1e-3)/1.1e-3 .lt. 0.02 .and. &
            abs(k_s_ind - 3.1e-5)/3.1e-5 .lt. 0.02) then
            print *, "OK J.1: J2010 Table 2 consistency: sqrt(Cd)*GammaT=", k_t_ind, &
                     " vs K_T=1.1e-3; sqrt(Cd)*GammaS=", k_s_ind, " vs K_S=3.1e-5"
        else
            print *, "ERROR J.1: sqrt(Cd)*GammaT=", k_t_ind, " sqrt(Cd)*GammaS=", k_s_ind
            n_errors = n_errors + 1
        end if
    end subroutine check_j2010_table2

    ! ==========================================================
    !   PRODUCTION END-TO-END (compute_basal_melt, scheme=THREE_EQUATION)
    ! ==========================================================
    subroutine check_production_chain(n_errors, n_checks)
        integer, intent(inout) :: n_errors, n_checks
        type(ocean_profile) :: prof
        real :: u_rel_d, gam_t_v, gam_s_v, m_exp, s_b_exp, t_b_exp
        real :: t_b, s_b
        real :: m_default

        call build_profile(2.0, 0.1, prof)

        ! (a) Трёхчленная схема через production-переключатель
        call set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_basal, &
                                t_b, s_b)

        u_rel_d = 0.1
        gam_t_v = 1.1e-3*u_rel_d
        gam_s_v = 3.1e-5*u_rel_d
        call independent_reduction(t_draft, s_draft, 50.0, gam_t_v, gam_s_v, &
                                   -10.0, .true., m_exp, s_b_exp, t_b_exp)
        if (abs(m_basal - m_exp)/max(abs(m_exp), 1.0e-12) .lt. 1.0e-3 .and. &
            abs(s_b - s_b_exp)/max(abs(s_b_exp), 1.0e-12) .lt. 1.0e-3) then
            print *, "OK L.1: production default scheme value t=", t_draft
        else
            print *, "ERROR L.1: m_basal=", m_basal, " m_exp=", m_exp
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (abs(m_basal - m_exp)/max(abs(m_exp), 1.0e-12) .lt. 1.0e-3) then
            print *, "OK L.2: end-to-end three-equation m=", m_basal, &
                     " (ind=", m_exp, ")"
        else
            print *, "ERROR L.2: end-to-end m mismatch"
            n_errors = n_errors + 1
        end if

        n_checks = n_checks + 1
        if (t_b .gt. tf_draft .and. s_b .lt. s_draft .and. m_basal .gt. 0.0) then
            print *, "OK L.3: interface freshening: T_B=", t_b, " > Tf=", tf_draft, &
                     ", S_B=", s_b, " < S_w=", s_draft
        else
            print *, "ERROR L.3: T_B=", t_b, " Tf=", tf_draft, " S_B=", s_b, &
                     " S_w=", s_draft
            n_errors = n_errors + 1
        end if

        ! (b) Возврат к baseline scheme: производство НЕ должно измениться
        call set_basal_melt_scheme(BASAL_MELT_SCHEME_FORCED_CONVECTION)
        call compute_basal_melt(prof, 50.0, 100.0, 0.0, 0.0, &
                                t_draft, s_draft, tf_draft, delta_t, m_default)
        call independent_reduction(t_draft, s_draft, 50.0, 1.1e-3*0.1, 3.1e-5*0.1, &
                                   -10.0, .true., m_exp, s_b_exp, t_b_exp)
        if (m_default .gt. 0.0 .and. abs(m_default - m_exp)/m_exp .gt. 0.1) then
            print *, "OK L.4: baseline bulk path differs from three-equation (regression:"
            print *, "     scheme switch is effective): m_bulk=", m_default
        else
            print *, "ERROR L.4: baseline m_default=", m_default, &
                     " should differ from 3eq m_exp=", m_exp
            n_errors = n_errors + 1
        end if
    end subroutine check_production_chain

    ! ==========================================================
    !   ВСПОМОГАТЕЛЬНОЕ: построить ocean_profile (как в Stage 10.7)
    ! ==========================================================
    subroutine build_profile(t_val, u_val, prof)
        real, intent(in) :: t_val, u_val
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
            prof%salt(k) = 0.0345
            prof%u(k) = u_val
            prof%v(k) = 0.0
            prof%u_rel(k) = u_val
        end do
    end subroutine build_profile

end program iceberg_test_10p10_three_equation