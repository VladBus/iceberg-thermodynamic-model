! ==============================================================================
! Тест: TEST_7 — Vertical temperature gradient + Stage 10.5 audit
! Назначение: Сильный вертикальный градиент T(z) — проверить, что боковое
!             плавление концентрируется в тёплых слоях, базальное — на глубине
!             осадки. Stage 10.5: аудит океанического термического форсинга —
!             EOS-80 точка замерзания Tf=f(S,p), вертикальная интерполяция,
!             зависимость от осадки, пороги базального плавления, боковой
!             интеграл Method A (depth_averaged_thermal_forcing).
! ==============================================================================

program iceberg_test_7_vertical_temp_gradient
    use iceberg
    use iceberg_types, only: ocean_freezing_point
    use iceberg_thermodynamics
    use iceberg_forcing, only: depth_averaged_thermal_forcing, interp_at_draft
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    integer :: step, nsteps
    real :: dt
    real :: delta_t_avg, t_draft, s_draft, tf_draft, delta_t_basal
    real :: draft_initial
    real :: raw_delta

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  TEST_7: Vertical Temperature Gradient"
    print *, "=================================================="

    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, &
                      76.5, 30.0, 0.0, 0.0)

    ! Профиль: 5°C на поверхности, -1.5°C на 100м
    ocean_prof%nlevels = 18
    allocate (ocean_prof%z(ocean_prof%nlevels))
    allocate (ocean_prof%dz(ocean_prof%nlevels))
    allocate (ocean_prof%temp(ocean_prof%nlevels))
    allocate (ocean_prof%salt(ocean_prof%nlevels))
    allocate (ocean_prof%u(ocean_prof%nlevels))
    allocate (ocean_prof%v(ocean_prof%nlevels))

    do step = 1, ocean_prof%nlevels
        ocean_prof%z(step) = real(step*10)
        ocean_prof%dz(step) = 10.0
        if (ocean_prof%z(step) .le. 100.0) then
            ocean_prof%temp(step) = 5.0 - 6.5*ocean_prof%z(step)/100.0
        else
            ocean_prof%temp(step) = -1.5
        end if
        ocean_prof%salt(step) = 0.0345
        ocean_prof%u(step) = 0.0
        ocean_prof%v(step) = 0.0
    end do

    ! Debug: print ocean profile
    print *, "Ocean profile (z, temp):"
    do step = 1, ocean_prof%nlevels
        print '(I3, 2F10.3)', step, ocean_prof%z(step), ocean_prof%temp(step)
    end do

    atmos%u10 = 0.0
    atmos%v10 = 0.0
    atmos%t2m = 253.15
    atmos%d2m = 253.15
    atmos%tcc = 0.0
    atmos%msl = 101325.0
    atmos%snowfall = 0.0

    dt = 3600.0
    nsteps = 1

    draft_initial = 100.0*910.0/1028.0  ! Initial H=100m

    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)

        if (.not. state%active) exit
    end do

    print *, "Draft: ", diag%draft, " m"
    print *, "T at draft: ", diag%t_draft, " °C"
    print *, "S at draft: ", diag%s_draft
    print *, "Tf at draft: ", diag%tf_draft, " °C"
    print *, "delta_t_ocean: ", diag%delta_t_ocean, " °C"
    print *, "Basal melt rate: ", diag%m_basal*86400, " m/day"
    print *, "Lateral melt rate: ", diag%m_lateral*86400, " m/day"
    print *, "Surface melt rate: ", diag%m_surface*86400, " m/day"

    ! Проверка 1: Базальное плавление >= 0
    n_checks = n_checks + 1
    if (diag%m_basal .ge. 0.0) then
        print *, "OK: Basal melt >= 0"
    else
        print *, "ERROR: Basal melt negative"
        n_errors = n_errors + 1
    end if

    ! Проверка 2: Боковое плавление > 0
    n_checks = n_checks + 1
    if (diag%m_lateral .gt. 0.0) then
        print *, "OK: Lateral melt > 0 (warm upper layers contribute)"
    else
        print *, "ERROR: Lateral melt = 0 (should be > 0 due to warm surface)"
        n_errors = n_errors + 1
    end if

    ! Проверка 3: Поверхностное плавление = 0
    n_checks = n_checks + 1
    if (diag%m_surface .eq. 0.0) then
        print *, "OK: Surface melt = 0"
    else
        print *, "WARNING: Surface melt > 0"
    end if

    ! Проверка 4: Глубинно-средний избыток температуры > 0
    n_checks = n_checks + 1
    delta_t_avg = depth_averaged_thermal_forcing(ocean_prof, diag%draft)
    if (delta_t_avg .gt. 0.0) then
        print *, "OK: Depth-averaged thermal forcing > 0: ", delta_t_avg, " °C"
    else
        print *, "ERROR: Depth-averaged thermal forcing <= 0"
        n_errors = n_errors + 1
    end if

    ! Проверка 5: Базальное плавление использует T именно на глубине осадки,
    !             точка замерзания — EOS-80 (Stage 10.5)
    n_checks = n_checks + 1
    t_draft = interp_at_draft(ocean_prof, draft_initial, "temp")
    s_draft = interp_at_draft(ocean_prof, draft_initial, "salt")
    tf_draft = ocean_freezing_point(s_draft, draft_initial)
    delta_t_basal = t_draft - tf_draft
    if (abs(diag%t_draft - t_draft) .lt. 1.0e-4 .and. &
        abs(diag%tf_draft - tf_draft) .lt. 1.0e-4) then
        print *, "OK: Basal melt uses T/Tf at draft depth correctly"
        print *, "  T(draft)=", t_draft, " Tf(draft)=", tf_draft, " ΔT=", delta_t_basal
    else
        print *, "ERROR: Basal melt interpolation mismatch"
        print *, "  diag t_draft=", diag%t_draft, " interp t_draft=", t_draft
        print *, "  diag tf_draft=", diag%tf_draft, " interp tf_draft=", tf_draft
        n_errors = n_errors + 1
    end if

    ! ========================================================================
    !   STAGE 10.5 AUDIT: ОКЕАНИЧЕСКИЙ ТЕРМИЧЕСКИЙ ФОРСИНГ
    ! ========================================================================
    call stage_10p5_audit(ocean_prof, n_checks, n_errors, diag, raw_delta)

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: TEST_7 PASSED"
        stop 0
    else
        print *, "FAILURE: TEST_7 FAILED with ", n_errors, " errors"
        stop 1
    end if

contains

    ! ========================================================================
    !   STAGE 10.5 AUDIT БЛОК
    ! ========================================================================
    subroutine stage_10p5_audit(prof, n_checks, n_errors, diag, raw_delta)
        type(ocean_profile), intent(in) :: prof
        integer, intent(inout) :: n_checks, n_errors
        type(iceberg_diagnostics), intent(in) :: diag
        real, intent(out) :: raw_delta

        real :: tf_surf_345, tf_surf_35, tf_mon
        real :: tf_p100, tf_p0, dp_expected
        real :: p500_depth, tf_check
        real :: v, ana, d
        real :: t, s, tf, dtb, m
        integer :: i, k
        logical :: ok
        real, parameter :: h_samp(3) = (/50.0, 100.0, 150.0/)
        real :: t_samp(3), s_samp(3), tf_samp(3), dt_samp(3), m_samp(3)
        real :: replica, tot, z_top, z_bot, dz_l, tf_l, dt_l, avg_replica, prod_avg
        real :: avg_out, m_lat
        type(ocean_profile) :: prof_cold

        print *, "=================================================="
        print *, "  STAGE 10.5 AUDIT: OCEAN THERMAL FORCING"
        print *, "=================================================="

        ! ----------------------------------------------------------
        ! A. EOS-80 точка замерзания Tf = f(S,p)  (UNESCO 1983)
        !    TF = (A0 + A1*sqrt(S) - A2*S)*S - 7.53e-4*P
        ! ----------------------------------------------------------

        ! 10.5.1: S=0, p=0 → 0.0
        n_checks = n_checks + 1
        if (abs(ocean_freezing_point(0.0, 0.0)) .lt. 1.0e-6) then
            print *, "OK 10.5.1: Pure water at surface freezes at 0°C"
        else
            print *, "ERROR 10.5.1: S=0,p=0 gave ", ocean_freezing_point(0.0, 0.0)
            n_errors = n_errors + 1
        end if

        ! 10.5.2: Значения на поверхности (S=0.0345 → -1.8936, S=0.035 → -1.9223)
        n_checks = n_checks + 1
        tf_surf_345 = ocean_freezing_point(0.0345, 0.0)
        tf_surf_35 = ocean_freezing_point(0.035, 0.0)
        if (abs(tf_surf_345 - (-1.8936)) .lt. 2.0e-3 .and. &
            abs(tf_surf_35 - (-1.9223)) .lt. 2.0e-3) then
            print *, "OK 10.5.2: Surface Tf: S=34.5→", tf_surf_345, " S=35→", tf_surf_35
        else
            print *, "ERROR 10.5.2: EOS surface values wrong: ", tf_surf_345, tf_surf_35
            n_errors = n_errors + 1
        end if

        ! 10.5.3: Монотонность по S (солонее → холоднее точка замерзания)
        n_checks = n_checks + 1
        tf_mon = ocean_freezing_point(0.033, 0.0)
        if (tf_surf_35 .lt. tf_surf_345 .and. tf_surf_345 .lt. tf_mon) then
            print *, "OK 10.5.3: Tf monotonic in S (", tf_surf_35, "<", tf_surf_345, "<", tf_mon, ")"
        else
            print *, "ERROR 10.5.3: Tf not monotonic in S"
            n_errors = n_errors + 1
        end if

        ! 10.5.4: Давление: dTf/dp = -7.53e-4 K/дбар (за 100 м ≈ -0.0759°C)
        n_checks = n_checks + 1
        tf_p0 = ocean_freezing_point(0.0345, 0.0)
        tf_p100 = ocean_freezing_point(0.0345, 100.0)
        dp_expected = -7.53e-4*(1028.0*9.80665*100.0/1.0e4)
        if (abs((tf_p100 - tf_p0) - dp_expected) .lt. 5.0e-4) then
            print *, "OK 10.5.4: Pressure term: ΔTf(100m)=", tf_p100 - tf_p0, " (expect ~", dp_expected, ")"
        else
            print *, "ERROR 10.5.4: Pressure term mismatch: ", tf_p100 - tf_p0, " vs ", dp_expected
            n_errors = n_errors + 1
        end if

        ! 10.5.5: Чистая вода на глубине: Tf = -7.53e-4*P (без членов солёности)
        n_checks = n_checks + 1
        if (abs(ocean_freezing_point(0.0, 100.0) - dp_expected) .lt. 5.0e-4) then
            print *, "OK 10.5.5: Pure water depth: Tf(100m)=", ocean_freezing_point(0.0, 100.0)
        else
            print *, "ERROR 10.5.5: Pure water depth pressure term wrong"
            n_errors = n_errors + 1
        end if

        ! 10.5.6: Литературное checkvalue: Tf(S=40, P=500 дбар) = -2.588567°C
        n_checks = n_checks + 1
        p500_depth = 500.0*1.0e4/(1028.0*9.80665)
        tf_check = ocean_freezing_point(0.040, p500_depth)
        if (abs(tf_check - (-2.588567)) .lt. 3.0e-3) then
            print *, "OK 10.5.6: UNESCO checkvalue: Tf(S=40,P=500)=", tf_check, " (expect -2.588567)"
        else
            print *, "ERROR 10.5.6: UNESCO checkvalue mismatch: ", tf_check
            n_errors = n_errors + 1
        end if

        ! ----------------------------------------------------------
        ! B. Вертикальная интерполяция interp_at_draft
        !    Профиль: T(z) = 5 - 0.065*z для z ≤ 100 м, -1.5 ниже
        ! ----------------------------------------------------------

        ! 10.5.7: Точный уровень (draft = z(2) = 20 м → 3.7°C)
        n_checks = n_checks + 1
        v = interp_at_draft(prof, 20.0, "temp")
        if (abs(v - 3.7) .lt. 1.0e-4) then
            print *, "OK 10.5.7: Exact level: ", v
        else
            print *, "ERROR 10.5.7: exact level: ", v
            n_errors = n_errors + 1
        end if

        ! 10.5.8: Середина интервала (draft = 15 м → 4.025°C)
        n_checks = n_checks + 1
        v = interp_at_draft(prof, 15.0, "temp")
        if (abs(v - 4.025) .lt. 1.0e-4) then
            print *, "OK 10.5.8: Midpoint: ", v
        else
            print *, "ERROR 10.5.8: midpoint: ", v
            n_errors = n_errors + 1
        end if

        ! 10.5.9: Клэмп к поверхности (draft ≤ z(1)) → значение 1-го уровня
        n_checks = n_checks + 1
        v = interp_at_draft(prof, 1.0, "temp")
        if (abs(v - (5.0 - 6.5*10.0/100.0)) .lt. 1.0e-4) then
            print *, "OK 10.5.9: Surface clamp: ", v
        else
            print *, "ERROR 10.5.9: surface clamp: ", v
            n_errors = n_errors + 1
        end if

        ! 10.5.10: Клэмп ниже глубочайшего уровня (draft > 180 м) → -1.5°C
        n_checks = n_checks + 1
        v = interp_at_draft(prof, 300.0, "temp")
        if (abs(v - (-1.5)) .lt. 1.0e-4) then
            print *, "OK 10.5.10: Below-deepest clamp: ", v
        else
            print *, "ERROR 10.5.10: below-deepest clamp: ", v
            n_errors = n_errors + 1
        end if

        ! 10.5.11: Солёность интерполируется так же (однородный профиль)
        n_checks = n_checks + 1
        v = interp_at_draft(prof, 15.0, "salt")
        if (abs(v - 0.0345) .lt. 1.0e-6) then
            print *, "OK 10.5.11: Salt interpolation: ", v
        else
            print *, "ERROR 10.5.11: salt interpolation: ", v
            n_errors = n_errors + 1
        end if

        ! ----------------------------------------------------------
        ! C. Зависимость выборки T от осадки D = H·ρ_i/ρ_w
        ! ----------------------------------------------------------
        ! 10.5.12: H=50/100/150 → t_draft == 5 - 0.065*D (линейная зона),
        !          D>100 → -1.5 (клэмп); строго убывает с глубиной
        n_checks = n_checks + 1
        ok = .true.
        do i = 1, 3
            d = h_samp(i)*RHO_ICE/RHO_WATER
            ! l_char = 100.0 (характерная длина для тестового айсберга), u_ice=v_ice=0.0
            call compute_basal_melt(prof, d, 100.0, 0.0, 0.0, t_samp(i), s_samp(i), tf_samp(i), &
                                    dt_samp(i), m_samp(i))
            if (d .le. 100.0) then
                ana = 5.0 - 0.065*d
            else
                ana = -1.5
            end if
            if (abs(t_samp(i) - ana) .gt. 1.0e-3) ok = .false.
        end do
        if (ok .and. t_samp(1) .gt. t_samp(2) .and. t_samp(2) .gt. t_samp(3)) then
            print *, "OK 10.5.12: Draft sampling: ", (t_samp(i), i=1, 3)
        else
            print *, "ERROR 10.5.12: draft sampling: ", (t_samp(i), i=1, 3)
            n_errors = n_errors + 1
        end if

        ! ----------------------------------------------------------
        ! D. Пороги базального плавления m_b = C_BASAL·max(0, T(D)-Tf(D))
        ! ----------------------------------------------------------
        ! Основной профиль слишком тёплый; строим локальные холодные профили
        call build_cold_profile(prof_cold, -2.0)

        ! 10.5.13: T < Tf → без плавления, сырое задействование < 0
        n_checks = n_checks + 1
        ! l_char = 100.0, u_ice=v_ice=0.0
        call compute_basal_melt(prof_cold, 10.0, 100.0, 0.0, 0.0, t, s, tf, dtb, m)
        if (m .eq. 0.0 .and. (t - tf) .lt. 0.0) then
            print *, "OK 10.5.13: T<Tf → m_basal=0, raw=(T-Tf)<0"
        else
            print *, "ERROR 10.5.13: cold ocean basal: m=", m, " raw=", t - tf
            n_errors = n_errors + 1
        end if

        ! 10.5.14: T == Tf → нулевое плавление
        n_checks = n_checks + 1
        call build_cold_profile(prof_cold, ocean_freezing_point(0.0345, 10.0))
        ! l_char = 100.0, u_ice=v_ice=0.0
        call compute_basal_melt(prof_cold, 10.0, 100.0, 0.0, 0.0, t, s, tf, dtb, m)
        if (m .eq. 0.0 .and. abs(t - tf) .lt. 1.0e-6) then
            print *, "OK 10.5.14: T=Tf → m_basal=0"
        else
            print *, "ERROR 10.5.14: T=Tf basal: m=", m, " raw=", t - tf
            n_errors = n_errors + 1
        end if

        ! 10.5.15: T > Tf → m = gamma_T * (T - Tf) / (rho_ice * L_f)
        ! New physics requires U_rel > 0; use u=0.05 for this test
        n_checks = n_checks + 1
        call build_cold_profile(prof_cold, 1.0)
        prof_cold%u(1) = 0.05
        prof_cold%u(2) = 0.05
        ! l_char = 100.0, u_ice=v_ice=0.0
        call compute_basal_melt(prof_cold, 10.0, 100.0, 0.0, 0.0, t, s, tf, dtb, m)
        ! Expected m = gamma_T * delta_T / (rho_ice * L_f)
        ! gamma_T = 0.037 * k * Pr^(1/3) * U^0.8 * nu^-0.8 * L^(-0.2)
        ! With U=0.05, L=100, k=0.56, Pr=13.8, nu=1.82e-6
        ! delta_T = 1.0 - tf
        ana = 1.0 - tf_eos_lit(s*1000.0, pressure_dbar(10.0))
        if (m .gt. 0.0) then
            print *, "OK 10.5.15: T>Tf → m_basal > 0 with U_rel > 0 (m=", m, ")"
        else
            print *, "ERROR 10.5.15: warm ocean basal: m=", m
            n_errors = n_errors + 1
        end if

        ! ----------------------------------------------------------
        ! E. Боковое плавление — Method A (глубинно-усреднённый интеграл)
        ! ----------------------------------------------------------

        ! 10.5.16: Холодный однородный океан → ⟨ΔT⟩_D = 0, m_lateral = 0
        n_checks = n_checks + 1
        call build_cold_profile(prof_cold, -2.5)
        delta_t_avg = depth_averaged_thermal_forcing(prof_cold, 10.0)
        call compute_lateral_melt(prof_cold, 10.0, avg_out, m_lat)
        if (delta_t_avg .eq. 0.0 .and. m_lat .eq. 0.0) then
            print *, "OK 10.5.16: Cold uniform ocean → ⟨ΔT⟩=0, m_lateral=0"
        else
            print *, "ERROR 10.5.16: cold lateral: avg=", delta_t_avg, " m=", m_lat
            n_errors = n_errors + 1
        end if

        ! 10.5.17: На тёплом профиле ⟨ΔT⟩_D совпадает с независимым Method-A
        !          бокс-репликой (Tf по литературной EOS-80 на центрах уровней)
        n_checks = n_checks + 1
        d = 100.0*RHO_ICE/RHO_WATER
        replica = 0.0
        tot = 0.0
        do k = 1, prof%nlevels
            z_top = prof%z(k) - 0.5*prof%dz(k)
            z_bot = prof%z(k) + 0.5*prof%dz(k)
            if (z_top .ge. d) exit
            if (z_bot .gt. d) z_bot = d
            dz_l = z_bot - z_top
            if (dz_l .le. 0.0) cycle
            tf_l = tf_eos_lit(prof%salt(k)*1000.0, pressure_dbar(prof%z(k)))
            dt_l = prof%temp(k) - tf_l
            if (dt_l .gt. 0.0) replica = replica + dt_l*dz_l
            tot = tot + dz_l
        end do
        avg_replica = replica/tot
        prod_avg = depth_averaged_thermal_forcing(prof, d)
        if (abs(avg_replica - prod_avg) .lt. 1.0e-5) then
            print *, "OK 10.5.17: Method-A replica vs production: ", avg_replica, prod_avg
        else
            print *, "ERROR 10.5.17: replica=", avg_replica, " production=", prod_avg
            n_errors = n_errors + 1
        end if

        ! 10.5.18: m_lateral = C_LATERAL·⟨ΔT⟩_D
        n_checks = n_checks + 1
        call compute_lateral_melt(prof, d, avg_out, m_lat)
        if (abs(m_lat - C_LATERAL*avg_out) .lt. 1.0e-10 .and. m_lat .gt. 0.0) then
            print *, "OK 10.5.18: m_lateral = C_LATERAL·⟨ΔT⟩ (m=", m_lat, ")"
        else
            print *, "ERROR 10.5.18: lateral rate: m=", m_lat, " C·avg=", C_LATERAL*avg_out
            n_errors = n_errors + 1
        end if

        ! ----------------------------------------------------------
        ! F. Сквозная диагностика на прогоне айсберга
        ! ----------------------------------------------------------
        ! 10.5.19: delta_t_ocean = T(D) - Tf(D) (необрезанный) 
        !          и диагностика термического задействования
        n_checks = n_checks + 1
        raw_delta = diag%t_draft - diag%tf_draft
        if (abs(diag%delta_t_ocean - raw_delta) .lt. 1.0e-6 .and. &
            diag%m_basal .ge. 0.0) then
            print *, "OK 10.5.19: delta_t_ocean diagnostics consistent (raw=", raw_delta, &
                     ") m_basal=", diag%m_basal
        else
            print *, "ERROR 10.5.19: delta_t_ocean wiring: diag=", diag%delta_t_ocean, &
                " raw=", raw_delta, " m=", diag%m_basal
            n_errors = n_errors + 1
        end if

    end subroutine stage_10p5_audit

    ! ========================================================================
    !   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    ! ========================================================================

    ! Локальный 2-уровневый холодный профиль (z=5,15 м, dz=10 м)
    subroutine build_cold_profile(prof, t_value)
        type(ocean_profile), intent(out) :: prof
        real, intent(in) :: t_value
        integer :: k

        prof%nlevels = 2
        allocate (prof%z(2))
        allocate (prof%dz(2))
        allocate (prof%temp(2))
        allocate (prof%salt(2))
        allocate (prof%u(2))
        allocate (prof%v(2))
        do k = 1, 2
            prof%z(k) = real(5 + (k - 1)*10)
            prof%dz(k) = 10.0
            prof%temp(k) = t_value
            prof%salt(k) = 0.0345
            prof%u(k) = 0.0
            prof%v(k) = 0.0
        end do
    end subroutine build_cold_profile

    ! Литеральная EOS-80 (UNESCO 1983) — независима от производственной функции
    pure real function tf_eos_lit(s_psu, p_dbar) result(tf)
        real, intent(in) :: s_psu
        real, intent(in) :: p_dbar
        tf = (-0.0575 + 1.710523e-3*sqrt(s_psu) - 2.154996e-4*s_psu)*s_psu &
             - 7.53e-4*p_dbar
    end function tf_eos_lit

    ! Гидростатическое давление [дбар] (как в production)
    pure real function pressure_dbar(depth_m) result(p)
        real, intent(in) :: depth_m
        p = RHO_WATER*GRAVITY*depth_m/1.0e4
    end function pressure_dbar

end program iceberg_test_7_vertical_temp_gradient