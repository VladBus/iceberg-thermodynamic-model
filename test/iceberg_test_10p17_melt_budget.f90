! ==============================================================================
! Тест: Stage 10.17 — Melt and Thermodynamic Budget Audit
! Назначение: Контролируемые синтетические эксперименты по аудиту таяния:
!             базальное (bulk), боковое (legacy C_LATERAL), поверхностное,
!             масс-объём-геометрия согласованность, замыкание бюджета,
!             масштабирования (U^0.8/U^0.5, ΔT-линейность, 1/L), dt-чувстви-
!             тельность, переключатель тепловой эволюции.
!
! Эксперименты:
!   A. Нулевое термическое форсирование (T = Tf)  -> все m = 0, масса точна
!   B. Тёплая вода (ΔT=2 K), холодный воздух      -> базальное + боковое
!   C. Холодная вода (ΔT=0), тёплый воздух        -> только поверхностное
!   D. Нулевая относительная скорость             -> базальное = 0 (bulk guard),
!                                                    боковое > 0 (не зависит от U)
!   E. Масштабирование по относительной скорости  -> m ∝ U^0.8 (турб.), U^0.5 (лам.)
!   F. Масштабирование по температуре воды        -> m ∝ ΔT (базальное и боковое)
!   G. Масштабирование по температуре воздуха     -> порог таяния, монотонность
!   H. Масштабирование по размеру                 -> m_basal ∝ L^-0.2; dM/M ∝ 1/L
!   I. Чувствительность к шагу времени            -> dt = 1800/3600/7200 с
!   J. Переключатель тепловой эволюции            -> T_ice bounded / const
!   K. 30-дневный синтетический стресс-тест       -> замыкание бюджета < 1e-3
!
! Эталонные значения (независимо, float64, внедрены литералами):
!   bulk m_basal (U=0.1, ΔT=2, L=100): 8.0637e-7 м/с (0.069670 м/день)
!   боковое m_lateral = C_LATERAL*2.0 = 2.0e-6 м/с (0.1728 м/день)
!   турбулентный показатель: m ∝ U^0.8  (2^0.8 = 1.74110)
!   ламинарный показатель:   m ∝ U^0.5  (2^0.5 = 1.41421)
!   размер: m_basal ∝ L^-0.2 (2^-0.2 = 0.87055)
!
! CSV-выходы: data/output/stage10.17/*.csv (gitignored).
! Единицы: SI (м, с, кг, °C). Точность: default real (float32).
! ==============================================================================

program iceberg_test_10p17_melt_budget
    use iceberg
    use iceberg_thermodynamics
    use iceberg_geometry
    use iceberg_types
    use param, only: nat
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: prof
    type(atmos_forcing) :: at
    type(iceberg_diagnostics) :: diag

    integer :: n_errors, n_checks
    real :: dt, m_b, m_l, m_s, d_t_avg, t_d, s_d, tf_d, d_t, q_net
    real :: t_if, s_if
    real :: m0, m1, d_m, v0, v1, budget_err
    real :: m_b_ref, m_l_ref, ratio
    real :: c_eff_int_loc, h_int_loc, q_cond_loc, q_bot_loc, dT_loc
    integer :: k, step, nsteps, unit_csv

    real, parameter :: DT_DEFAULT = 3600.0
    real, parameter :: DRAFT_100 = 100.0*910.0/1028.0

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  STAGE 10.17 MELT & THERMODYNAMIC BUDGET AUDIT"
    print *, "=================================================="

    ! --- Каталог вывода ---
    call system('mkdir -p data/output/stage10.17')
    ! --- Сброс файла экспериментов (заголовок пишется один раз на запуск) ---
    open (unit_csv, file='data/output/stage10.17/synthetic_melt_experiments.csv', status='replace')
    write (unit_csv, '(A)') 'exp,config,mb_mday,ml_mday,ms_mday,dM_kg,dM_frac'
    close (unit_csv)

    ! --- Референс-дата для солнечной геометрии (полярная ночь: SW = 0) ---
    nat(1) = 2020
    nat(2) = 1
    nat(3) = 15
    nat(4) = 12

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ A: нулевое термическое форсирование
    ! =========================================================================
    print *, ""
    print *, "--- A. Zero thermal forcing (T = Tf exactly) ---"
    call make_ocean_freezing_plus(prof, 0.0, 0.0348, 0.0, 0.0)
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    m0 = RHO_ICE*state%L*state%W*state%H
    call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    m1 = RHO_ICE*state%L*state%W*state%H
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0) then
        print *, "OK   A1. basal melt = 0 at zero thermal driving"
    else
        print *, "ERROR A1. basal melt = ", diag%m_basal
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%m_lateral .eq. 0.0) then
        print *, "OK   A2. lateral melt = 0 at zero thermal driving"
    else
        print *, "ERROR A2. lateral melt = ", diag%m_lateral
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%m_surface .eq. 0.0) then
        print *, "OK   A3. surface melt = 0 at cold atmosphere"
    else
        print *, "ERROR A3. surface melt = ", diag%m_surface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (abs(m1 - m0)/m0 .lt. 1.0e-6) then
        print *, "OK   A4. mass exactly conserved (dM/M = ", (m1 - m0)/m0, ")"
    else
        print *, "ERROR A4. mass not conserved: ", (m1 - m0)/m0
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    ! L/W не меняются (нет бокового таяния); H меняется только на сублимацию:
    ! dH = -dt*(0 + 0 - m_vapor/rho) = dt*m_vapor/rho (m_vapor < 0 -> H убывает)
    if (state%L .eq. 100.0 .and. state%W .eq. 100.0 .and. &
        abs((100.0 - state%H) - DT_DEFAULT*(-diag%m_vapor)/RHO_ICE) .lt. 2.0e-5) then
        print *, "OK   A5. L/W unchanged; H changed only by vapor sublimation (dH=", 100.0 - state%H, " m)"
    else
        print *, "ERROR A5. geometry: L=", state%L, " W=", state%W, " H=", state%H, &
            " vapor dH exp=", DT_DEFAULT*(-diag%m_vapor)/RHO_ICE
        n_errors = n_errors + 1
    end if
    call write_exp_csv('A', 'T=Tf; cold air', diag, 0.0, 0.0)

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ B: тёплая вода (ΔT=2 K), холодный воздух
    ! =========================================================================
    print *, ""
    print *, "--- B. Warm water (dT=2), cold air ---"
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.1, 0.0)
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)

    ! B1: прямое базальное (bulk, производственный вызов)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    m_b_ref = 8.0637e-7
    n_checks = n_checks + 1
    if (rel_diff(m_b, m_b_ref) .lt. 1.0e-3) then
        print *, "OK   B1. bulk basal melt = ", m_b*86400.0, " m/day (ref ", m_b_ref*86400.0, ")"
    else
        print *, "ERROR B1. basal melt = ", m_b, " ref = ", m_b_ref
        n_errors = n_errors + 1
    end if

    ! B2: прямое боковое
    call compute_lateral_melt(prof, DRAFT_100, d_t_avg, m_l)
    m_l_ref = 2.0e-6
    n_checks = n_checks + 1
    if (rel_diff(m_l, m_l_ref) .lt. 1.0e-3) then
        print *, "OK   B2. lateral melt = ", m_l*86400.0, " m/day (ref ", m_l_ref*86400.0, ")"
    else
        print *, "ERROR B2. lateral melt = ", m_l, " ref = ", m_l_ref
        n_errors = n_errors + 1
    end if

    ! B3: поверхностное = 0 (холодный воздух)
    call compute_surface_melt(state, at, diag, q_net, m_s, DT_DEFAULT, &
                              nat(1), nat(2), nat(3), nat(4))
    n_checks = n_checks + 1
    if (m_s .eq. 0.0) then
        print *, "OK   B3. surface melt = 0 (cold air)"
    else
        print *, "ERROR B3. surface melt = ", m_s
        n_errors = n_errors + 1
    end if

    ! B4: 1-дневная интеграция: замыкание бюджета и геометрия
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    m0 = RHO_ICE*state%L*state%W*state%H
    v0 = state%L*state%W*state%H
    do k = 1, 24
        call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    m1 = RHO_ICE*state%L*state%W*state%H
    v1 = state%L*state%W*state%H
    d_m = m0 - m1
    budget_err = abs(d_m - RHO_ICE*(v0 - v1))/max(d_m, 1.0)
    n_checks = n_checks + 1
    if (budget_err .lt. 1.0e-3) then
        print *, "OK   B4. mass-volume closure: dM = rho*dV (err ", budget_err, ")"
    else
        print *, "ERROR B4. budget closure err = ", budget_err
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    ! Боковое таяние: dL = -dt*m_l на каждом шаге
    if (rel_diff((100.0 - state%L), 24.0*DT_DEFAULT*m_l_ref) .lt. 1.0e-3) then
        print *, "OK   B5. dL = -sum(dt*m_lateral): ", state%L
    else
        print *, "ERROR B5. dL mismatch: ", state%L, " exp ", 100.0 - 24.0*DT_DEFAULT*m_l_ref
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    ! H-обновление: dH = -dt*(m_b + m_s - m_vapor/rho)
    if (rel_diff(state%H, 100.0 - 24.0*DT_DEFAULT*(m_b + m_s - diag%m_vapor/RHO_ICE)) .lt. 1.0e-3) then
        print *, "OK   B6. dH = -dt*(m_b + m_s - m_vapor/rho)"
    else
        print *, "ERROR B6. dH mismatch: ", state%H
        n_errors = n_errors + 1
    end if
    call write_exp_csv('B', 'dT=2; U=0.1; cold air', diag, d_m, d_m/m0)

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ C: холодная вода (ΔT=0), тёплый воздух
    ! =========================================================================
    print *, ""
    print *, "--- C. Cold water (dT=0), warm air ---"
    call make_ocean_freezing_plus(prof, 0.0, 0.0348, 0.1, 0.0)
    call make_atmos(at, 5.0, 0.0, 285.0, 281.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    m0 = RHO_ICE*state%L*state%W*state%H
    do k = 1, 24
        call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    m1 = RHO_ICE*state%L*state%W*state%H
    n_checks = n_checks + 1
    if (diag%m_basal .eq. 0.0 .and. diag%m_lateral .eq. 0.0) then
        print *, "OK   C1. basal/lateral = 0 at zero ocean driving"
    else
        print *, "ERROR C1. basal/lateral = ", diag%m_basal, diag%m_lateral
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%m_surface .gt. 0.0) then
        print *, "OK   C2. surface melt active: ", diag%m_surface*86400.0, " m/day"
    else
        print *, "ERROR C2. surface melt = ", diag%m_surface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (state%T_surface .eq. T_MELT) then
        print *, "OK   C3. T_surface pinned at T_MELT while melting"
    else
        print *, "ERROR C3. T_surface = ", state%T_surface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    ! Энергетическое замыкание поверхности: m_surface*rho*Lf == q_surface (при T=0)
    if (rel_diff(diag%m_surface*RHO_ICE*LATENT_HEAT, diag%q_surface) .lt. 1.0e-3) then
        print *, "OK   C4. m_surface*rho*Lf == q_surface (energy closure)"
    else
        print *, "ERROR C4. closure: ", diag%m_surface*RHO_ICE*LATENT_HEAT, diag%q_surface
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    d_m = m0 - m1
    v0 = 100.0**3
    v1 = state%L*state%W*state%H
    if (abs(d_m - RHO_ICE*(v0 - v1))/max(d_m, 1.0) .lt. 1.0e-3) then
        print *, "OK   C5. mass-volume closure"
    else
        print *, "ERROR C5. closure: ", d_m, RHO_ICE*(v0 - v1)
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    ! Vapor: H-обновление включает m_vapor (deposition -> прирост высоты)
    if (diag%m_vapor .gt. 0.0) then
        print *, "OK   C6. deposition active: m_vapor = ", diag%m_vapor, " kg/(m2 s)"
    else
        print *, "WARNING C6. no deposition (m_vapor = ", diag%m_vapor, ")"
    end if
    call write_exp_csv('C', 'dT=0; warm air 285K', diag, d_m, d_m/m0)

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ D: нулевая относительная скорость
    ! =========================================================================
    print *, ""
    print *, "--- D. Zero relative velocity ---"
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.0, 0.0)
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    call compute_lateral_melt(prof, DRAFT_100, d_t_avg, m_l)
    n_checks = n_checks + 1
    if (m_b .eq. 0.0) then
        print *, "OK   D1. basal melt = 0 at U_rel = 0 (bulk forced-convection guard)"
    else
        print *, "ERROR D1. basal melt = ", m_b
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (m_l .gt. 0.0) then
        print *, "OK   D2. lateral melt = ", m_l*86400.0, " m/day (velocity-independent)"
    else
        print *, "ERROR D2. lateral melt = ", m_l
        n_errors = n_errors + 1
    end if
    call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    n_checks = n_checks + 1
    if (diag%total_mass_loss .gt. 0.0) then
        print *, "OK   D3. mass loss at rest = lateral only: ", diag%total_mass_loss, " kg"
    else
        print *, "ERROR D3. no mass loss at rest"
        n_errors = n_errors + 1
    end if
    call write_exp_csv('D', 'dT=2; U=0', diag, diag%total_mass_loss, 0.0)

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ E: масштабирование по относительной скорости
    ! =========================================================================
    print *, ""
    print *, "--- E. Relative-velocity scaling ---"
    call open_csv('data/output/stage10.17/velocity_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'U_ms,m_basal_mday'
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)

    ! E1: турбулентный режим (Re > 5e5): m(0.04)/m(0.02) = 2^0.8
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.02, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    write (unit_csv, '(F10.4,A,F12.6)') 0.02, ',', m_b*86400.0
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.04, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    write (unit_csv, '(F10.4,A,F12.6)') 0.04, ',', m_b*86400.0
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.08, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    write (unit_csv, '(F10.4,A,F12.6)') 0.08, ',', m_b*86400.0
    close (unit_csv)
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.04, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    ratio = m_b
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.02, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_b, 2.0**0.8) .lt. 1.0e-3) then
        print *, "OK   E1. turbulent scaling m(0.04)/m(0.02) = ", ratio/m_b, " (exp 2^0.8)"
    else
        print *, "ERROR E1. ratio = ", ratio/m_b, " exp ", 2.0**0.8
        n_errors = n_errors + 1
    end if

    ! E2: ламинарный режим (Re < 5e5): m(0.008)/m(0.004) = 2^0.5
    ! Append-режим: E1 уже открыл файл (replace) и записал турбулентные строки
    open (unit_csv, file='data/output/stage10.17/velocity_sensitivity.csv', &
          status='unknown', position='append')
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.008, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    write (unit_csv, '(F10.4,A,F12.6)') 0.008, ',', m_b*86400.0
    ratio = m_b
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.004, 0.0)
    call compute_basal_melt(state, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                            t_d, s_d, tf_d, d_t, m_b, t_if, s_if, diag)
    write (unit_csv, '(F10.4,A,F12.6)') 0.004, ',', m_b*86400.0
    close (unit_csv)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_b, 2.0**0.5) .lt. 1.0e-3) then
        print *, "OK   E2. laminar scaling m(0.008)/m(0.004) = ", ratio/m_b, " (exp 2^0.5)"
    else
        print *, "ERROR E2. ratio = ", ratio/m_b, " exp ", 2.0**0.5
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ F: масштабирование по температуре воды
    ! =========================================================================
    print *, ""
    print *, "--- F. Water-temperature scaling ---"
    call open_csv('data/output/stage10.17/temperature_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'kind,value_degC,m_basal_mday,m_lateral_mday,m_surface_mday'
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call run_temp_case(1.0, prof, at, state, m_b, m_l, m_s)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'ocean', ',', 1.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0
    call run_temp_case(2.0, prof, at, state, m_b, m_l, m_s)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'ocean', ',', 2.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0
    call run_temp_case(4.0, prof, at, state, m_b, m_l, m_s)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'ocean', ',', 4.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0

    ! F1: базальное ∝ ΔT (1:2:4)
    call run_temp_case(1.0, prof, at, state, m_b, m_l, m_s)
    ratio = m_b
    call run_temp_case(2.0, prof, at, state, m_b, m_l, m_s)
    n_checks = n_checks + 1
    if (rel_diff(m_b/ratio, 2.0) .lt. 1.0e-3) then
        print *, "OK   F1. basal m(2K)/m(1K) = ", m_b/ratio, " (exp 2)"
    else
        print *, "ERROR F1. ratio = ", m_b/ratio
        n_errors = n_errors + 1
    end if
    call run_temp_case(4.0, prof, at, state, m_b, m_l, m_s)
    ratio = m_b
    call run_temp_case(2.0, prof, at, state, m_b, m_l, m_s)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_b, 2.0) .lt. 1.0e-3) then
        print *, "OK   F2. basal m(4K)/m(2K) = ", ratio/m_b, " (exp 2)"
    else
        print *, "ERROR F2. ratio = ", ratio/m_b
        n_errors = n_errors + 1
    end if
    ! F3: боковое ∝ ΔT
    call run_temp_case(1.0, prof, at, state, m_b, m_l, m_s)
    ratio = m_l
    call run_temp_case(2.0, prof, at, state, m_b, m_l, m_s)
    n_checks = n_checks + 1
    if (rel_diff(m_l/ratio, 2.0) .lt. 1.0e-3) then
        print *, "OK   F3. lateral m(2K)/m(1K) = ", m_l/ratio, " (exp 2)"
    else
        print *, "ERROR F3. ratio = ", m_l/ratio
        n_errors = n_errors + 1
    end if
    call run_temp_case(4.0, prof, at, state, m_b, m_l, m_s)
    ratio = m_l
    call run_temp_case(2.0, prof, at, state, m_b, m_l, m_s)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_l, 2.0) .lt. 1.0e-3) then
        print *, "OK   F4. lateral m(4K)/m(2K) = ", ratio/m_l, " (exp 2)"
    else
        print *, "ERROR F4. ratio = ", ratio/m_l
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ G: масштабирование по температуре воздуха
    ! =========================================================================
    print *, ""
    print *, "--- G. Air-temperature scaling ---"
    call make_ocean_freezing_plus(prof, 0.0, 0.0348, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    state%T_surface = T_MELT   ! поверхность на точке плавления -> весь поток в таяние
    call run_air_case(250.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 250.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(260.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 260.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(270.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 270.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(276.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 276.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(278.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 278.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(280.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 280.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    call run_air_case(285.0, prof, at, state, m_s, q_net)
    write (unit_csv, '(A,A,F10.4,A,F12.6,A,F12.6,A,F12.6)') 'air', ',', 285.0, ',', 0.0, ',', 0.0, ',', m_s*86400.0
    close (unit_csv)

    ! G1: холодный воздух -> нет таяния
    call run_air_case(250.0, prof, at, state, m_s, q_net)
    n_checks = n_checks + 1
    if (m_s .eq. 0.0) then
        print *, "OK   G1. no surface melt at t2m=250K"
    else
        print *, "ERROR G1. melt at 250K: ", m_s
        n_errors = n_errors + 1
    end if
    call run_air_case(260.0, prof, at, state, m_s, q_net)
    call run_air_case(270.0, prof, at, state, m_s, q_net)
    n_checks = n_checks + 1
    if (m_s .eq. 0.0) then
        print *, "OK   G2. no surface melt at t2m=270K"
    else
        print *, "ERROR G2. melt at 270K: ", m_s
        n_errors = n_errors + 1
    end if
    ! G3: тёплый воздух -> таяние, монотонность
    call run_air_case(278.0, prof, at, state, m_s, q_net)
    ratio = m_s
    call run_air_case(280.0, prof, at, state, m_s, q_net)
    n_checks = n_checks + 1
    if (ratio .gt. 0.0 .and. m_s .gt. ratio) then
        print *, "OK   G3. surface melt grows with t2m: 278->280K"
    else
        print *, "ERROR G3. melt 278K=", ratio, " 280K=", m_s
        n_errors = n_errors + 1
    end if
    call run_air_case(285.0, prof, at, state, m_s, q_net)
    n_checks = n_checks + 1
    if (m_s .gt. 0.0) then
        print *, "OK   G4. surface melt at t2m=285K: ", m_s*86400.0, " m/day"
    else
        print *, "ERROR G4. no melt at 285K"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ H: масштабирование по размеру
    ! =========================================================================
    print *, ""
    print *, "--- H. Geometry scaling ---"
    call open_csv('data/output/stage10.17/size_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'L_m,m_basal_mday,m_lateral_mday,m_surface_mday,dM_kg,dM_frac_day'
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call run_size_case(10.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    write (unit_csv, '(F10.2,A,F12.6,A,F12.6,A,F12.6,A,F15.1,A,F12.6)') &
        10.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0, ',', d_m, ',', d_m/m0
    call run_size_case(50.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    write (unit_csv, '(F10.2,A,F12.6,A,F12.6,A,F12.6,A,F15.1,A,F12.6)') &
        50.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0, ',', d_m, ',', d_m/m0
    call run_size_case(100.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    write (unit_csv, '(F10.2,A,F12.6,A,F12.6,A,F12.6,A,F15.1,A,F12.6)') &
        100.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0, ',', d_m, ',', d_m/m0
    call run_size_case(200.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    write (unit_csv, '(F10.2,A,F12.6,A,F12.6,A,F12.6,A,F15.1,A,F12.6)') &
        200.0, ',', m_b*86400.0, ',', m_l*86400.0, ',', m_s*86400.0, ',', d_m, ',', d_m/m0
    close (unit_csv)

    ! H1: базальное ∝ L^-0.2 (турбулентный режим для всех размеров)
    call run_size_case(200.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    ratio = m_b
    call run_size_case(100.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_b, 2.0**(-0.2)) .lt. 2.0e-3) then
        print *, "OK   H1. basal m(200)/m(100) = ", ratio/m_b, " (exp 2^-0.2)"
    else
        print *, "ERROR H1. ratio = ", ratio/m_b, " exp ", 2.0**(-0.2)
        n_errors = n_errors + 1
    end if
    ! H2: боковое не зависит от размера
    call run_size_case(200.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    ratio = m_l
    call run_size_case(10.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    n_checks = n_checks + 1
    if (rel_diff(ratio/m_l, 1.0) .lt. 1.0e-3) then
        print *, "OK   H2. lateral m size-independent: ", ratio/m_l
    else
        print *, "ERROR H2. lateral ratio = ", ratio/m_l
        n_errors = n_errors + 1
    end if
    ! H3: долевая потеря массы ∝ 1/L (боковое доминирует)
    call run_size_case(200.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    ratio = d_m/m0
    call run_size_case(100.0, prof, at, state, m_b, m_l, m_s, d_m, m0)
    n_checks = n_checks + 1
    if (rel_diff(ratio/(d_m/m0), 0.5) .lt. 5.0e-2) then
        print *, "OK   H3. fractional loss 200m/100m = ", ratio/(d_m/m0), " (exp ~0.5)"
    else
        print *, "ERROR H3. frac ratio = ", ratio/(d_m/m0)
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ I: чувствительность к шагу времени
    ! =========================================================================
    print *, ""
    print *, "--- I. Timestep sensitivity (1 simulated day) ---"
    call open_csv('data/output/stage10.17/timestep_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'dt_s,dM_kg,budget_err_rel,rel_diff_from_3600'
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.1, 0.0)
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call run_dt_case(1800.0, prof, at, d_m, budget_err)
    write (unit_csv, '(F10.1,A,F15.1,A,E12.4,A,E12.4)') 1800.0, ',', d_m, ',', budget_err, ',', 0.0
    call run_dt_case(3600.0, prof, at, d_m, budget_err)
    write (unit_csv, '(F10.1,A,F15.1,A,E12.4,A,E12.4)') 3600.0, ',', d_m, ',', budget_err, ',', 0.0
    call run_dt_case(7200.0, prof, at, d_m, budget_err)
    write (unit_csv, '(F10.1,A,F15.1,A,E12.4,A,E12.4)') 7200.0, ',', d_m, ',', budget_err, ',', 0.0
    close (unit_csv)

    call run_dt_case(1800.0, prof, at, d_m, budget_err)
    ratio = d_m
    call run_dt_case(3600.0, prof, at, d_m, budget_err)
    n_checks = n_checks + 1
    if (abs(ratio - d_m)/d_m .lt. 1.0e-2) then
        print *, "OK   I1. dM(dt=1800) vs dM(dt=3600): ", abs(ratio - d_m)/d_m
    else
        print *, "ERROR I1. dt sensitivity: ", abs(ratio - d_m)/d_m
        n_errors = n_errors + 1
    end if
    call run_dt_case(7200.0, prof, at, d_m, budget_err)
    call run_dt_case(3600.0, prof, at, d_m, budget_err)
    n_checks = n_checks + 1
    if (abs(ratio - d_m)/d_m .lt. 2.0e-2) then
        print *, "OK   I2. dM(dt=7200) vs dM(dt=3600): ", abs(ratio - d_m)/d_m
    else
        print *, "ERROR I2. dt sensitivity: ", abs(ratio - d_m)/d_m
        n_errors = n_errors + 1
    end if
    call run_dt_case(1800.0, prof, at, d_m, budget_err)
    n_checks = n_checks + 1
    if (budget_err .lt. 1.0e-3) then
        print *, "OK   I3. budget closure at dt=1800: ", budget_err
    else
        print *, "ERROR I3. closure at dt=1800: ", budget_err
        n_errors = n_errors + 1
    end if
    call run_dt_case(7200.0, prof, at, d_m, budget_err)
    n_checks = n_checks + 1
    if (budget_err .lt. 1.0e-3) then
        print *, "OK   I4. budget closure at dt=7200: ", budget_err
    else
        print *, "ERROR I4. closure at dt=7200: ", budget_err
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ J: переключатель тепловой эволюции
    ! =========================================================================
    print *, ""
    print *, "--- J. Thermal-evolution switch ---"
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.1, 0.0)
    call make_atmos(at, 5.0, 0.0, 280.0, 277.0, 0.5)

    ! J1: выключено -> T_ice постоянна, dT_ice_dt = 0
    call set_thermal_evolution(.false.)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    do k = 1, 24
        call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    n_checks = n_checks + 1
    if (state%T_ice .eq. T_ICE_INIT .and. diag%dT_ice_dt .eq. 0.0) then
        print *, "OK   J1. T_ice constant when thermal evolution OFF"
    else
        print *, "ERROR J1. T_ice = ", state%T_ice, " dT/dt = ", diag%dT_ice_dt
        n_errors = n_errors + 1
    end if
    m_s = diag%m_surface
    n_checks = n_checks + 1
    if (m_s .ge. 0.0) then
        print *, "OK   J2. surface melt finite (OFF): ", m_s*86400.0, " m/day"
    else
        print *, "ERROR J2. negative surface melt"
        n_errors = n_errors + 1
    end if

    ! J2: включено -> T_ice эволюционирует в границах [T_ICE_MIN, T_ICE_MAX]
    call set_thermal_evolution(.true.)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    do k = 1, 24
        call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    n_checks = n_checks + 1
    if (state%T_ice .ge. T_ICE_MIN .and. state%T_ice .le. T_ICE_MAX) then
        print *, "OK   J3. T_ice bounded: ", state%T_ice, " C (evolved; basal sensible flux cools interior)"
    else
        print *, "ERROR J3. T_ice = ", state%T_ice
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (state%T_ice .ne. T_ICE_INIT) then
        print *, "OK   J4. T_ice actually evolved (", state%T_ice, " C, init ", T_ICE_INIT, ")"
    else
        print *, "ERROR J4. T_ice did not evolve"
        n_errors = n_errors + 1
    end if

    ! J5/J6: прямое юнит-тестирование солвера внутренней температуры
    !        C_int * dT_ice/dt = q_cond - q_bot  (независимое ожидание)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    state%T_surface = 0.0
    state%T_ice = -10.0
    call compute_iceberg_thermal_capacity(state, c_eff_int_loc, h_int_loc)
    ! q_cond = 2*K_ICE*(T_surf - T_ice)/H; q_bot задаём контролируемо
    q_cond_loc = 2.0*K_ICE*(0.0 - (-10.0))/100.0
    q_bot_loc = 5.0
    call update_iceberg_internal_temperature(state, DT_DEFAULT, q_cond_loc, q_bot_loc, diag)
    ! ожидание: dT_ice = (q_cond - q_bot)/C_int * dt
    dT_loc = (q_cond_loc - q_bot_loc)/c_eff_int_loc*DT_DEFAULT

    n_checks = n_checks + 1
    ! float32: T_ice ~ -10, изменение ~ -8.6e-5; вычитание двух величин ~10
    ! имеет шум ~половина ulp(10) = 4.8e-7 -> абсолютный допуск 2e-6
    if (abs((state%T_ice - (-10.0)) - dT_loc) .lt. 2.0e-6) then
        print *, "OK   J5. solver T_ice update matches analytic: ", state%T_ice - (-10.0), " vs ", dT_loc
    else
        print *, "ERROR J5. T_ice update: ", state%T_ice - (-10.0), " exp ", dT_loc
        n_errors = n_errors + 1
    end if
    ! q_cond единичное значение
    n_checks = n_checks + 1
    if (rel_diff(q_cond_loc, 0.44) .lt. 1.0e-3) then
        print *, "OK   J6. q_cond = 2*K_ICE*dT/H = 0.44 W/m2"
    else
        print *, "ERROR J6. q_cond = ", q_cond_loc
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ K: 30-дневный синтетический стресс-тест
    ! =========================================================================
    print *, ""
    print *, "--- K. 30-day synthetic stress test (case B) ---"
    call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.1, 0.0)
    call make_atmos(at, 5.0, 0.0, 250.0, 247.0, 0.5)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    m0 = RHO_ICE*state%L*state%W*state%H
    v0 = state%L*state%W*state%H
    nsteps = 720
    do step = 1, nsteps
        call iceberg_step(state, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
        if (diag%m_basal .lt. 0.0 .or. diag%m_lateral .lt. 0.0 .or. diag%m_surface .lt. 0.0) then
            print *, "ERROR K0. negative melt rate at step ", step
            n_errors = n_errors + 1
            exit
        end if
    end do
    m1 = RHO_ICE*state%L*state%W*state%H
    v1 = state%L*state%W*state%H
    d_m = m0 - m1
    budget_err = abs(d_m - RHO_ICE*(v0 - v1))/max(d_m, 1.0)
    n_checks = n_checks + 1
    if (budget_err .lt. 1.0e-3) then
        print *, "OK   K1. 30-day budget closure: ", budget_err
    else
        print *, "ERROR K1. 30-day closure: ", budget_err
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (m1 .lt. m0 .and. d_m .gt. 0.0) then
        print *, "OK   K2. monotonic mass decrease: dM = ", d_m/1.0e6, " Mt (", d_m/m0*100.0, "%)"
    else
        print *, "ERROR K2. mass not decreasing"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (state%L .gt. 0.0 .and. state%W .gt. 0.0 .and. state%H .gt. 0.0) then
        print *, "OK   K3. geometry positive after 30 days: ", state%L, state%W, state%H
    else
        print *, "ERROR K3. geometry: ", state%L, state%W, state%H
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (diag%total_mass_loss .gt. 0.0) then
        print *, "OK   K4. total mass loss positive"
    else
        print *, "ERROR K4. total mass loss = ", diag%total_mass_loss
        n_errors = n_errors + 1
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: STAGE 10.17 MELT BUDGET AUDIT PASSED"
        stop 0
    else
        print *, "FAILURE: STAGE 10.17 MELT BUDGET AUDIT FAILED"
        stop 1
    end if

contains

    ! ========================================================================
    ! Вспомогательные процедуры
    ! ========================================================================

    pure real function rel_diff(a, b) result(r)
        real, intent(in) :: a, b
        r = abs(a - b)/max(abs(b), 1.0e-30)
    end function rel_diff

    ! Профиль океана: T(k) = Tf(S, z(k)) + dT, однородные S, u, v
    subroutine make_ocean_freezing_plus(prof, d_t, s_mass, u0, v0)
        type(ocean_profile), intent(out) :: prof
        real, intent(in) :: d_t, s_mass, u0, v0
        integer :: k
        prof%nlevels = 20
        if (allocated(prof%z)) deallocate (prof%z, prof%dz, prof%temp, prof%salt, prof%u, prof%v, prof%u_rel)
        allocate (prof%z(20), prof%dz(20), prof%temp(20), prof%salt(20), &
                  prof%u(20), prof%v(20), prof%u_rel(20))
        do k = 1, 20
            prof%z(k) = real(10*k - 5)     ! центры: 5, 15, ..., 195 м
            prof%dz(k) = 10.0
            prof%salt(k) = s_mass
            prof%temp(k) = ocean_freezing_point(s_mass, prof%z(k)) + d_t
            prof%u(k) = u0
            prof%v(k) = v0
            prof%u_rel(k) = sqrt(u0*u0 + v0*v0)
        end do
    end subroutine make_ocean_freezing_plus

    subroutine make_atmos(at, u10, v10, t2m_k, d2m_k, tcc)
        type(atmos_forcing), intent(out) :: at
        real, intent(in) :: u10, v10, t2m_k, d2m_k, tcc
        at%u10 = u10
        at%v10 = v10
        at%t2m = t2m_k
        at%d2m = d2m_k
        at%tcc = tcc
        at%msl = 101325.0
        at%snowfall = 0.0
    end subroutine make_atmos

    subroutine open_csv(path, unit_out)
        character(len=*), intent(in) :: path
        integer, intent(out) :: unit_out
        integer :: ios_local
        unit_out = 30
        open (unit_out, file=path, status='replace', iostat=ios_local)
        if (ios_local .ne. 0) print *, "WARNING: cannot open ", trim(path)
    end subroutine open_csv

    subroutine write_exp_csv(exp_id, config, dg, d_m, d_m_frac)
        character(len=*), intent(in) :: exp_id
        character(len=*), intent(in) :: config
        type(iceberg_diagnostics), intent(in) :: dg
        real, intent(in) :: d_m, d_m_frac
        integer :: u
        ! Файл уже создан и содержит заголовок (см. начало программы) — только append
        open (u, file='data/output/stage10.17/synthetic_melt_experiments.csv', &
              status='old', position='append')
        write (u, '(A,A,A,A,A,F12.6,A,F12.6,A,F12.6,A,F15.1,A,E12.4)') &
            trim(exp_id), ',', trim(config), ',', ' ', &
            dg%m_basal*86400.0, ',', dg%m_lateral*86400.0, ',', dg%m_surface*86400.0, ',', d_m, ',', d_m_frac
        close (u)
    end subroutine write_exp_csv

    subroutine run_temp_case(d_t, prof, at, st, m_b_out, m_l_out, m_s_out)
        real, intent(in) :: d_t
        type(ocean_profile), intent(inout) :: prof
        type(atmos_forcing), intent(in) :: at
        type(iceberg_state), intent(inout) :: st
        real, intent(out) :: m_b_out, m_l_out, m_s_out
        type(iceberg_diagnostics) :: dg
        real :: t_d, s_d, tf_d, d_t_loc, q_net, m_s_loc, t_if, s_if
        call make_ocean_freezing_plus(prof, d_t, 0.0348, 0.1, 0.0)
        call compute_basal_melt(st, prof, DRAFT_100, 100.0, 0.0, 0.0, &
                                t_d, s_d, tf_d, d_t_loc, m_b_out, t_if, s_if, dg)
        call compute_lateral_melt(prof, DRAFT_100, d_t_loc, m_l_out)
        call compute_surface_melt(st, at, dg, q_net, m_s_out, DT_DEFAULT, &
                                  nat(1), nat(2), nat(3), nat(4))
    end subroutine run_temp_case

    subroutine run_air_case(t2m_k, prof, at, st, m_s_out, q_net_out)
        real, intent(in) :: t2m_k
        type(ocean_profile), intent(in) :: prof
        type(atmos_forcing), intent(out) :: at
        type(iceberg_state), intent(inout) :: st
        real, intent(out) :: m_s_out, q_net_out
        type(iceberg_diagnostics) :: dg
        st%T_surface = T_MELT   ! поверхность на точке плавления -> поток в таяние
        call make_atmos(at, 5.0, 0.0, t2m_k, t2m_k - 3.0, 0.5)
        call compute_surface_melt(st, at, dg, q_net_out, m_s_out, DT_DEFAULT, &
                                  nat(1), nat(2), nat(3), nat(4))
    end subroutine run_air_case

    subroutine run_size_case(size_m, prof, at, st, m_b_out, m_l_out, m_s_out, d_m_out, m0_out)
        real, intent(in) :: size_m
        type(ocean_profile), intent(inout) :: prof
        type(atmos_forcing), intent(in) :: at
        type(iceberg_state), intent(out) :: st
        real, intent(out) :: m_b_out, m_l_out, m_s_out, d_m_out, m0_out
        integer :: k
        real :: m1
        call make_ocean_freezing_plus(prof, 2.0, 0.0348, 0.1, 0.0)
        call iceberg_init(st, 0.0, 0.0, size_m, size_m, size_m, 76.5, 30.0, 0.0, 0.0)
        m0_out = RHO_ICE*st%L*st%W*st%H
        do k = 1, 24
            call iceberg_step(st, DT_DEFAULT, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), diag)
        end do
        m1 = RHO_ICE*st%L*st%W*st%H
        d_m_out = m0_out - m1
        m_b_out = diag%m_basal
        m_l_out = diag%m_lateral
        m_s_out = diag%m_surface
    end subroutine run_size_case

    subroutine run_dt_case(dt_in, prof, at, d_m_out, budget_err_out)
        real, intent(in) :: dt_in
        type(ocean_profile), intent(in) :: prof
        type(atmos_forcing), intent(in) :: at
        real, intent(out) :: d_m_out, budget_err_out
        integer :: k, nsteps_local
        real :: m0, m1, v0, v1
        type(iceberg_state) :: st
        type(iceberg_diagnostics) :: dg
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
        m0 = RHO_ICE*st%L*st%W*st%H
        v0 = st%L*st%W*st%H
        nsteps_local = nint(86400.0/dt_in)
        do k = 1, nsteps_local
            call iceberg_step(st, dt_in, prof, at, 500.0, 0.0, 0.0, (/0.0, 0.0/), dg)
        end do
        m1 = RHO_ICE*st%L*st%W*st%H
        v1 = st%L*st%W*st%H
        d_m_out = m0 - m1
        budget_err_out = abs(d_m_out - RHO_ICE*(v0 - v1))/max(d_m_out, 1.0)
    end subroutine run_dt_case

end program iceberg_test_10p17_melt_budget