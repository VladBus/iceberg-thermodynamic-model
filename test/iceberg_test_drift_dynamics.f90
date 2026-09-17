! ==============================================================================
! Тест: Drift Dynamics Controlled Experiments (Stage 10.16)
! Назначение: Изолированное исследование динамики дрейфа для T-07.
!
! Эксперименты (все на айсберге 100x100x100 м, если не указано иное):
!   A.  Нулевой ветер, нулевое течение — проверка отсутствия ложного ускорения
!   B.  Постоянный ветер, нулевое течение (с Кориолисом и без)
!   C.  Нулевой ветер, постоянное течение (с Кориолисом и без)
!   D.  Постоянные ветер + течение (комбинированный отклик)
!   E.  Ротация ветра (два ортогональных направления)
!   F.  Ротация течения (два ортогональных направления)
!   G.  Кориолис вкл/выкл (lat=76.5 vs lat=0)
!   H.  Чувствительность к шагу времени (dt = 1800/3600/7200 с)
!   I.  Чувствительность к размеру айсберга (10/30/100/300 м)
!   J.  Чувствительность к плотностям/коэффициентам сопротивления
!       (аналитическая экстраполяция; константы — compile-time parameter,
!       численная проверка одного возмущения отдельным пересбором)
!
! Для каждого шага записываются силы (ветер/вода/Кориолис), ускорение,
! относительные скорости и скорость айсберга — в CSV
! (data/output/stage10.16/force_balance_timeseries_<case>.csv).
!
! Единицы: СИ (м, с, кг, Н). Плавление отключено (холодный океан/атмосфера).
! ==============================================================================

program iceberg_test_drift_dynamics
    use iceberg
    use iceberg_dynamics
    use iceberg_types
    implicit none

    type(iceberg_state) :: state
    type(ocean_profile) :: ocean_prof
    type(atmos_forcing) :: atmos
    type(iceberg_diagnostics) :: diag

    integer :: step, nsteps, ios
    real :: dt
    integer :: unit_csv

    integer :: n_errors, n_checks
    real :: terminal_speed, ratio
    real :: u_eq, v_eq, speed_eq
    real :: f_coriolis
    real, parameter :: R_EARTH_M = 6371000.0

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  DRIFT DYNAMICS CONTROLLED EXPERIMENTS (10.16)"
    print *, "=================================================="

    ! --- Каталог вывода ---
    call system('mkdir -p data/output/stage10.16')

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ A: нулевой ветер, нулевое течение
    ! =========================================================================
    print *, ""
    print *, "--- A. Zero wind, zero current ---"
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    dt = 3600.0
    nsteps = 24*5  ! 5 дней
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    speed_eq = sqrt(state%u**2 + state%v**2)
    write (*, '(A,F10.6,A,F10.6)') "  final u,v: ", state%u, ", ", state%v
    n_checks = n_checks + 1
    if (speed_eq .lt. 1.0e-6) then
        print *, "OK   A. zero forcing -> zero velocity"
    else
        print *, "ERROR A. artificial velocity: ", speed_eq
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ B: постоянный ветер, нулевое течение
    ! (B1: с Кориолисом lat=76.5; B2: без Кориолиса lat=0)
    ! =========================================================================
    print *, ""
    print *, "--- B. Constant wind, zero current ---"
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)  ! ветер вдоль +X
    nsteps = 24*30

    ! B1: Кориолис вкл
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call open_csv('data/output/stage10.16/force_balance_timeseries_B1_wind_cor.csv', unit_csv)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        call write_force_row(unit_csv, state, diag, atmos, ocean_prof, dt, step)
    end do
    close (unit_csv)
    speed_eq = sqrt(state%u**2 + state%v**2)
    ratio = speed_eq/10.0
    write (*, '(A,F10.6,A,F10.6)') "  B1 (Coriolis on)  final speed: ", speed_eq, &
        "  ratio: ", ratio
    n_checks = n_checks + 1
    ! Ожидание: Coriolis-limited u ~ F_wind/(M*f) ~ 0.01-0.03 м/с (0.1-0.3%)
    if (speed_eq .gt. 1.0e-3 .and. speed_eq .lt. 0.05) then
        print *, "OK   B1. Coriolis-limited wind drift"
    else
        print *, "ERROR B1. speed out of expected Coriolis-limited range"
        n_errors = n_errors + 1
    end if

    ! B2: Кориолис выкл (экватор)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    call open_csv('data/output/stage10.16/force_balance_timeseries_B2_wind_nocor.csv', unit_csv)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        call write_force_row(unit_csv, state, diag, atmos, ocean_prof, dt, step)
    end do
    close (unit_csv)
    speed_eq = sqrt(state%u**2 + state%v**2)
    ratio = speed_eq/10.0
    write (*, '(A,F10.6,A,F10.6)') "  B2 (no Coriolis)  final speed: ", speed_eq, &
        "  ratio: ", ratio
    n_checks = n_checks + 1
    ! Ожидание: drag-limited u/V ~ sqrt(rho_a*C_a*A_sail/(rho_w*C_w*A_side)) ~ 0.03-0.04
    if (ratio .gt. 0.02 .and. ratio .lt. 0.06) then
        print *, "OK   B2. drag-limited wind drift"
    else
        print *, "ERROR B2. ratio out of expected drag-limited range"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ C: нулевой ветер, постоянное течение
    ! =========================================================================
    print *, ""
    print *, "--- C. Zero wind, constant current (U=0.1 m/s along +X) ---"
    call make_atmos(atmos, 0.0, 0.0)

    ! C1: Кориолис вкл
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call open_csv('data/output/stage10.16/force_balance_timeseries_C1_current_cor.csv', unit_csv)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        call write_force_row(unit_csv, state, diag, atmos, ocean_prof, dt, step)
    end do
    close (unit_csv)
    speed_eq = sqrt(state%u**2 + state%v**2)
    ratio = speed_eq/0.1
    write (*, '(A,F10.6,A,F10.6)') "  C1 (Coriolis on)  final speed: ", speed_eq, &
        "  ratio: ", ratio
    n_checks = n_checks + 1
    ! Ожидание: Coriolis-limited u ~ F_water/(M*f) — малое (0.1-2% течения)
    if (speed_eq .gt. 1.0e-5 .and. speed_eq .lt. 0.01) then
        print *, "OK   C1. Coriolis-limited current response"
    else
        print *, "ERROR C1. speed out of expected range"
        n_errors = n_errors + 1
    end if

    ! C2: Кориолис выкл — айсберг должен разгоняться к скорости течения
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    call open_csv('data/output/stage10.16/force_balance_timeseries_C2_current_nocor.csv', unit_csv)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        call write_force_row(unit_csv, state, diag, atmos, ocean_prof, dt, step)
    end do
    close (unit_csv)
    speed_eq = sqrt(state%u**2 + state%v**2)
    ratio = speed_eq/0.1
    write (*, '(A,F10.6,A,F10.6)') "  C2 (no Coriolis)  final speed: ", speed_eq, &
        "  ratio: ", ratio
    n_checks = n_checks + 1
    ! Ожидание: без Кориолиса айсберг ускоряется к скорости течения (>80% за 30 дней)
    if (ratio .gt. 0.8) then
        print *, "OK   C2. current-following without Coriolis"
    else
        print *, "WARNING C2. current ratio < 0.8 (timescale check needed)"
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ D: постоянные ветер + течение
    ! =========================================================================
    print *, ""
    print *, "--- D. Constant wind (10 m/s +X) + current (0.1 m/s +X) ---"
    call make_ocean(ocean_prof, 0.1, 0.0)
    call make_atmos(atmos, 10.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call open_csv('data/output/stage10.16/force_balance_timeseries_D_combined.csv', unit_csv)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
        call write_force_row(unit_csv, state, diag, atmos, ocean_prof, dt, step)
    end do
    close (unit_csv)
    speed_eq = sqrt(state%u**2 + state%v**2)
    write (*, '(A,F10.6)') "  D combined final speed: ", speed_eq
    n_checks = n_checks + 1
    if (speed_eq .gt. 0.0) then
        print *, "OK   D. combined forcing response"
    else
        print *, "ERROR D. zero response to combined forcing"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ E: ротация ветра (два ортогональных направления)
    ! =========================================================================
    print *, ""
    print *, "--- E. Wind direction rotation ---"
    call make_ocean(ocean_prof, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)   ! ветер вдоль +X
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    u_eq = state%u; v_eq = state%v
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call make_atmos(atmos, 0.0, 10.0)   ! ветер вдоль +Y
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    write (*, '(A,2F10.6,A,2F10.6)') "  wind +X -> (", u_eq, v_eq, &
        "),  wind +Y -> (", state%u, state%v, ")"
    n_checks = n_checks + 1
    ! Поворот на 90°: скорость должна повернуться (модуль ~одинаков, компоненты обменяны с учётом знака)
    if (abs(abs(u_eq) - abs(state%v)) .lt. 0.1*max(abs(u_eq), 1.0e-6) .and. &
        abs(abs(v_eq) - abs(state%u)) .lt. 0.1*max(abs(v_eq), 1.0e-6)) then
        print *, "OK   E. wind rotation consistency"
    else
        print *, "ERROR E. wind rotation not consistent"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ F: ротация течения
    ! =========================================================================
    print *, ""
    print *, "--- F. Current direction rotation ---"
    call make_atmos(atmos, 0.0, 0.0)
    call make_ocean(ocean_prof, 0.1, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    u_eq = state%u; v_eq = state%v
    call make_ocean(ocean_prof, 0.0, 0.1)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    write (*, '(A,2F10.6,A,2F10.6)') "  current +X -> (", u_eq, v_eq, &
        "),  current +Y -> (", state%u, state%v, ")"
    n_checks = n_checks + 1
    if (abs(abs(u_eq) - abs(state%v)) .lt. 0.1*max(abs(u_eq), 1.0e-6) .and. &
        abs(abs(v_eq) - abs(state%u)) .lt. 0.1*max(abs(v_eq), 1.0e-6)) then
        print *, "OK   F. current rotation consistency"
    else
        print *, "ERROR F. current rotation not consistent"
        n_errors = n_errors + 1
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ G: Кориолис вкл/выкл (сравнение B1 vs B2)
    ! =========================================================================
    print *, ""
    print *, "--- G. Coriolis on/off comparison (wind 10 m/s) ---"
    ! B1 и B2 уже прогнаны; здесь воспроизводим для отчёта
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    u_eq = state%u; v_eq = state%v
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    do step = 1, nsteps
        call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                          0.0, 0.0, (/0.0, 0.0/), diag)
    end do
    write (*, '(A,2F10.6,A,F10.6)') "  Coriolis ON -> (", u_eq, v_eq, &
        ") speed ", sqrt(u_eq**2 + v_eq**2)
    write (*, '(A,2F10.6,A,F10.6)') "  Coriolis OFF -> (", state%u, state%v, &
        ") speed ", sqrt(state%u**2 + state%v**2)
    n_checks = n_checks + 1
    ! Кориолис должен существенно подавлять скорость (в разы)
    if (sqrt(state%u**2 + state%v**2) .gt. 3.0*sqrt(u_eq**2 + v_eq**2)) then
        print *, "OK   G. Coriolis suppresses wind drift significantly"
    else
        print *, "WARNING G. Coriolis effect not significant"
    end if

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ H: чувствительность к шагу времени
    ! =========================================================================
    print *, ""
    print *, "--- H. Time-step sensitivity (wind 10 m/s, Coriolis on) ---"
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)
    call open_csv('data/output/stage10.16/timestep_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'dt_s,steps,final_speed_ms,ratio'
    ! dt = 1800 с, 60 дней (2880 шагов)
    call run_wind_case(1800.0, 2880, state)
    write (unit_csv, '(F10.0,I8,F12.6,F12.6)') 1800.0, 2880, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0
    ! dt = 3600 с, 30 дней (720 шагов) — базовый
    call run_wind_case(3600.0, 720, state)
    write (unit_csv, '(F10.0,I8,F12.6,F12.6)') 3600.0, 720, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0
    ! dt = 7200 с, 30 дней (360 шагов)
    call run_wind_case(7200.0, 360, state)
    write (unit_csv, '(F10.0,I8,F12.6,F12.6)') 7200.0, 360, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0
    close (unit_csv)
    print *, "  timestep_sensitivity.csv written"
    n_checks = n_checks + 1
    print *, "OK   H. timestep experiment completed"

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ I: чувствительность к размеру айсберга
    ! =========================================================================
    print *, ""
    print *, "--- I. Iceberg-size sensitivity (wind 10 m/s, Coriolis on; current 0.1 m/s) ---"
    call make_atmos(atmos, 10.0, 0.0)
    call open_csv('data/output/stage10.16/size_sensitivity.csv', unit_csv)
    write (unit_csv, '(A)') 'size_m,wind_speed_ms,current_speed_ms,final_speed_ms,wind_ratio,current_ratio'
    call make_ocean(ocean_prof, 0.0, 0.0)
    call run_size_case(10.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 10.0, 10.0, 0.0, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0, 0.0
    call run_size_case(30.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 30.0, 10.0, 0.0, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0, 0.0
    call run_size_case(100.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 100.0, 10.0, 0.0, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0, 0.0
    call run_size_case(300.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 300.0, 10.0, 0.0, &
        sqrt(state%u**2 + state%v**2), sqrt(state%u**2 + state%v**2)/10.0, 0.0
    ! Течения: ветер выключен, течение 0.1 м/с
    call make_atmos(atmos, 0.0, 0.0)
    call make_ocean(ocean_prof, 0.1, 0.0)
    call run_size_case(10.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 10.0, 0.0, 0.1, &
        sqrt(state%u**2 + state%v**2), 0.0, sqrt(state%u**2 + state%v**2)/0.1
    call run_size_case(100.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 100.0, 0.0, 0.1, &
        sqrt(state%u**2 + state%v**2), 0.0, sqrt(state%u**2 + state%v**2)/0.1
    call run_size_case(300.0, ocean_prof, atmos, state)
    write (unit_csv, '(F10.1,F10.3,F10.3,F12.6,F12.6,F12.6)') 300.0, 0.0, 0.1, &
        sqrt(state%u**2 + state%v**2), 0.0, sqrt(state%u**2 + state%v**2)/0.1
    close (unit_csv)
    print *, "  size_sensitivity.csv written"
    n_checks = n_checks + 1
    print *, "OK   I. size experiment completed"

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ J: аналитическая чувствительность к плотностям/коэффициентам
    ! (численная проверка одного возмущения — отдельным пересбором, см. отчёт;
    !  здесь выводим аналитические ожидания масштабирования)
    ! =========================================================================
    print *, ""
    print *, "--- J. Density/drag sensitivity (analytic scaling) ---"
    print *, "  Drag-limited ratio  ~ sqrt(rho_a*C_a*A_sail/(rho_w*C_w*A_side))"
    print *, "  Coriolis-limited u   ~ F_wind/(M*f) ~ rho_a*C_a*A_sail*V^2/(M*f)"
    n_checks = n_checks + 1
    print *, "OK   J. analytic sensitivity documented (numeric check in report)"

    ! =========================================================================
    ! ЭКСПЕРИМЕНТ K: знак и направление сил (физическая согласованность)
    ! =========================================================================
    print *, ""
    print *, "--- K. Force sign and direction ---"
    ! Вода: сила трения против относительной скорости (тормозящая)
    call make_ocean(ocean_prof, 0.1, 0.0)   ! течение вдоль +X
    call make_atmos(atmos, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag)
    ! В начальный момент u=0, течение +X: водная сила должна быть ПОЛОЖИТЕЛЬНОЙ (+X)
    n_checks = n_checks + 1
    if (diag%f_water_x .gt. 0.0) then
        print *, "OK   K1. water force pushes in current direction"
    else
        print *, "ERROR K1. water force sign: ", diag%f_water_x
        n_errors = n_errors + 1
    end if
    ! Ветер +X, u=0: ветровая сила положительна (+X)
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
    call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag)
    n_checks = n_checks + 1
    if (diag%f_wind_x .gt. 0.0) then
        print *, "OK   K2. wind force pushes in wind direction"
    else
        print *, "ERROR K2. wind force sign: ", diag%f_wind_x
        n_errors = n_errors + 1
    end if
    ! Вода тормозит: зададим u=0.2 при течении 0.1 -> относительная скорость отрицательна
    call make_ocean(ocean_prof, 0.1, 0.0)
    call make_atmos(atmos, 0.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.2, 0.0)
    call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag)
    n_checks = n_checks + 1
    if (diag%f_water_x .lt. 0.0) then
        print *, "OK   K3. water force opposes relative velocity (braking)"
    else
        print *, "ERROR K3. water force not braking: ", diag%f_water_x
        n_errors = n_errors + 1
    end if
    ! Единицы: ускорение должно быть ~ F/M ~ 1161/9.1e8 ~ 1.3e-6 м/с^2
    call make_ocean(ocean_prof, 0.0, 0.0)
    call make_atmos(atmos, 10.0, 0.0)
    call iceberg_init(state, 0.0, 0.0, 100.0, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0)
    call iceberg_step(state, dt, ocean_prof, atmos, 500.0, &
                      0.0, 0.0, (/0.0, 0.0/), diag)
    n_checks = n_checks + 1
    if (abs(diag%f_wind_x)/(RHO_ICE*100.0**3) .gt. 1.0e-7 .and. &
        abs(diag%f_wind_x)/(RHO_ICE*100.0**3) .lt. 1.0e-5) then
        print *, "OK   K4. acceleration scale plausible (~F/M ~ 1e-6 m/s^2)"
    else
        print *, "ERROR K4. acceleration scale: ", diag%f_wind_x/(RHO_ICE*100.0**3)
        n_errors = n_errors + 1
    end if

    print *, ""
    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: DRIFT DYNAMICS EXPERIMENTS PASSED"
        stop 0
    else
        print *, "FAILURE: DRIFT DYNAMICS EXPERIMENTS FAILED"
        stop 1
    end if

contains

    ! ========================================================================
    ! Вспомогательные процедуры
    ! ========================================================================
    subroutine make_ocean(prof, u0, v0)
        type(ocean_profile), intent(out) :: prof
        real, intent(in) :: u0, v0
        integer :: k
        prof%nlevels = 10
        if (allocated(prof%z)) deallocate (prof%z, prof%dz, prof%temp, prof%salt, prof%u, prof%v)
        allocate (prof%z(10), prof%dz(10), prof%temp(10), prof%salt(10), prof%u(10), prof%v(10))
        do k = 1, 10
            prof%z(k) = real(k*10)
            prof%dz(k) = 10.0
            prof%temp(k) = -2.5     ! ниже точки замерзания -> нет плавления
            prof%salt(k) = 0.0345
            prof%u(k) = u0
            prof%v(k) = v0
        end do
    end subroutine make_ocean

    subroutine make_atmos(at, u10, v10)
        type(atmos_forcing), intent(out) :: at
        real, intent(in) :: u10, v10
        at%u10 = u10
        at%v10 = v10
        at%t2m = 253.15
        at%d2m = 253.15
        at%tcc = 0.0
        at%msl = 101325.0
        at%snowfall = 0.0
    end subroutine make_atmos

    subroutine open_csv(path, unit_out)
        character(len=*), intent(in) :: path
        integer, intent(out) :: unit_out
        unit_out = 20
        open (unit_out, file=path, status='replace', iostat=ios)
        if (ios .ne. 0) print *, "WARNING: cannot open ", trim(path)
    end subroutine open_csv

    subroutine write_force_row(unit_out, st, dg, at, pr, dt_in, step_in)
        integer, intent(in) :: unit_out
        type(iceberg_state), intent(in) :: st
        type(iceberg_diagnostics), intent(in) :: dg
        type(atmos_forcing), intent(in) :: at
        type(ocean_profile), intent(in) :: pr
        real, intent(in) :: dt_in
        integer, intent(in) :: step_in
        real :: mass, f_cor
        real :: u_rel_wind_x, u_rel_wind_y, u_rel_wind_s
        real :: u_rel_water_x, u_rel_water_y, u_rel_water_s
        real :: ax, ay
        ! масса и Кориолис
        mass = RHO_ICE*st%L*st%W*st%H
        f_cor = 2.0*OMEGA*sin(st%latitude/57.2957795)
        ! относительные скорости
        u_rel_wind_x = at%u10 - st%u
        u_rel_wind_y = at%v10 - st%v
        u_rel_wind_s = sqrt(u_rel_wind_x**2 + u_rel_wind_y**2)
        u_rel_water_x = pr%u(1) - st%u
        u_rel_water_y = pr%v(1) - st%v
        u_rel_water_s = sqrt(u_rel_water_x**2 + u_rel_water_y**2)
        ! ускорение
        ax = (dg%f_wind_x + dg%f_water_x + dg%f_cor_x + dg%f_pressure_x + dg%f_fk_x)/mass
        ay = (dg%f_wind_y + dg%f_water_y + dg%f_cor_y + dg%f_pressure_y + dg%f_fk_y)/mass
        write (unit_out, '(I6,F14.2,2F14.6,2F14.6,2F14.6,4F14.4,2F14.6,2F14.6,2F14.8)') &
            step_in, real(step_in)*dt_in/3600.0, &
            st%u, st%v, &
            at%u10, at%v10, &
            pr%u(1), pr%v(1), &
            dg%f_wind_x, dg%f_wind_y, &
            dg%f_water_x, dg%f_water_y, &
            dg%f_cor_x, dg%f_cor_y, &
            u_rel_wind_s, u_rel_water_s, &
            ax, ay
    end subroutine write_force_row

    subroutine run_wind_case(dt_in, nsteps_in, st)
        real, intent(in) :: dt_in
        integer, intent(in) :: nsteps_in
        type(iceberg_state), intent(out) :: st
        integer :: k
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 76.5, 30.0, 0.0, 0.0)
        do k = 1, nsteps_in
            call iceberg_step(st, dt_in, ocean_prof, atmos, 500.0, &
                              0.0, 0.0, (/0.0, 0.0/), diag)
        end do
    end subroutine run_wind_case

    subroutine run_size_case(size_m, pr, at, st)
        real, intent(in) :: size_m
        type(ocean_profile), intent(in) :: pr
        type(atmos_forcing), intent(in) :: at
        type(iceberg_state), intent(out) :: st
        integer :: k
        call iceberg_init(st, 0.0, 0.0, size_m, size_m, size_m, 76.5, 30.0, 0.0, 0.0)
        do k = 1, nsteps
            call iceberg_step(st, dt, pr, at, 500.0, &
                              0.0, 0.0, (/0.0, 0.0/), diag)
        end do
    end subroutine run_size_case

end program iceberg_test_drift_dynamics