! ==============================================================================
! Модуль: stage1022_diagnostics
! Назначение: Stage 10.22 «Ocean Density–Thermal-Wind & Block-200 Stability
!             Audit» — диагностическая изоляция первой физически невозможной
!             океанской ячейки в цепочке
!               EN4 T/S → EOS/RO → плотностные градиенты → thermal-wind /
!               baroclinic интегралы → Block 200 → Block 210/Thomas →
!               порча T/S → расхождение RO → NaN/zombie (KNOWN_ISSUES T-03).
!             См. docs/validation/stage10.22_ocean_density_thermal_wind_block200_audit.md.
!
! Переключатели (env STAGE1022_*, задаются в main.f90; все OFF → бит-идентично
! предыдущим стадиям, legacy md5 92a873ad78a31fefb0e127cfd373dcc3):
!   STAGE1022_DIAG=true                 — пробы/бюджеты (read-only, CSV).
!   STAGE1022_FREEZE_RO=true            — A1: conv_adj не пересчитывает RO.
!   STAGE1022_FREEZE_THERMAL_WIND=true  — A2: B200 без бароклинных интегралов.
!   STAGE1022_FREEZE_TS=true            — A3: T/S статичны (heat+adv+CA off).
!   STAGE1022_FREEZE_RO_DOWNSTREAM=true — A4: B200 видит ro_ref (сэндвич).
!
! Диагностика (активна только при s22_diag):
!   s22_probe — 6 точек шага: NaN/Inf/финитные + min/max/mean/RMS + oob
!               (T∈[-2.6,10], S∈[0.029,0.037], RO∈[0.004,0.011], |U|>500 см/с).
!   s22_block200_budget — пересчёт бароклинного интеграла B200 из u1 (pre-B200)
!               + доминирующий член ускорения (baroclinic vs DPX vs Laplacian)
!               + амплификация max|U2|/max|U1|.
!   s22_b210_* — накопители обусловленности системы Томаса (pivot/НУ/дно).
!
! Пробы читают массивы param (u1/v1/u2/v2/t2/s2/ro по влажным T-ячейкам
! kt1>0, как daily_diagnostics; бюджет — по U-ячейкам kk1>0, как Block 200)
! и НИЧЕГО не изменяют. Единицы как в модели: U/V [см/с], T [°C],
! S [массовая доля], RO [г/см³].
! ==============================================================================

module stage1022_diagnostics

    use param
    use, intrinsic :: iso_fortran_env, only: real64
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite, ieee_is_nan

    implicit none

    private
    public :: s22_diag, s22_freeze_ro, s22_freeze_tw, s22_freeze_ts, &
              s22_freeze_ro_downstream
    public :: s22_capture_ro_ref, s22_sandwich_start, s22_sandwich_end, &
              s22_probe, s22_block200_budget, &
              s22_b210_reset, s22_b210_rr_update, s22_b210_pivot_update, &
              s22_b210_rhs_update, s22_b210_bottom_update, s22_b210_flush

    ! --- Переключатели Stage 10.22 (управляются из main.f90; все OFF) ---
    logical, save :: s22_diag = .false.
    logical, save :: s22_freeze_ro = .false.
    logical, save :: s22_freeze_tw = .false.
    logical, save :: s22_freeze_ts = .false.
    logical, save :: s22_freeze_ro_downstream = .false.

    ! --- Ссылочное поле плотности (A4): начальный RO, который видит Block 200 ---
    real, save :: s22_ro_ref(is1, js1, ks) = 0.0
    real, save :: s22_ro_saved(is1, js1, ks) = 0.0

    ! --- Накопители обусловленности Block 210 (Thomas), сброс каждый шаг ---
    real(8), save :: s22_rr_min, s22_rr_max            ! диапазон NU [см²/с]
    real(8), save :: s22_piv_min, s22_piv_neg, s22_piv_cnt  ! |pivot|, pivot<=0
    real(8), save :: s22_rhs_max                       ! max|unu|
    real(8), save :: s22_den_min, s22_den_neg          ! дно: |1-bb*uc|, <=0

    ! --- Логические блоки CSV (77=daily diag, 82=CA guard — заняты) ---
    integer, parameter :: s22_unit_probe = 83
    integer, parameter :: s22_unit_b200 = 84
    integer, parameter :: s22_unit_b210 = 85

    ! Мягкие (диагностические) границы «физически правдоподобного» состояния.
    ! T/S: зимне-весенний Баренцев шельф; RO: диапазон EOS-документации 0.0038-0.0124.
    real, parameter :: s22_t_lo = -2.6, s22_t_hi = 10.0
    real, parameter :: s22_s_lo = 0.029, s22_s_hi = 0.037
    real, parameter :: s22_ro_lo = 0.004, s22_ro_hi = 0.011
    real, parameter :: s22_uv_spike = 500.0   ! [см/с] аномальный всплеск скорости

contains

    ! ==========================================================================
    ! s22_capture_ro_ref: сохранить начальное поле RO (после eos_diag на init)
    ! как ссылку для A4 (Block 200 с замороженной плотностью).
    ! ==========================================================================
    subroutine s22_capture_ro_ref()
        s22_ro_ref = ro
    end subroutine s22_capture_ro_ref

    ! ==========================================================================
    ! s22_sandwich_start / s22_sandwich_end: «мьютекс-сэндвич» A4.
    ! Перед Block 200: сохранить эволюционировавшее RO и подставить ro_ref.
    ! После Block 200: восстановить эволюционировавшее RO. Сам Block 200
    ! не редактируется — физика блока остаётся нетронутой.
    ! ==========================================================================
    subroutine s22_sandwich_start()
        s22_ro_saved = ro        ! эволюционировавшее RO
        ro = s22_ro_ref          ! Block 200 видит ссылочное (начальное) RO
    end subroutine s22_sandwich_start

    subroutine s22_sandwich_end()
        ro = s22_ro_saved        ! восстановить эволюционировавшее RO
    end subroutine s22_sandwich_end

    ! ==========================================================================
    ! s22_probe: снимок состояния в точке шага. Только чтение.
    ! Для label=='INIT' поля u1/v1 не опрашиваются (ещё не инициализированы).
    ! ==========================================================================
    subroutine s22_probe(label, day, step)
        character(len=*), intent(in) :: label
        integer, intent(in) :: day, step

        integer :: nan_u1, inf_u1, n_u1, oob_u1
        integer :: nan_v1, inf_v1, n_v1, oob_v1
        integer :: nan_u2, inf_u2, n_u2, oob_u2
        integer :: nan_v2, inf_v2, n_v2, oob_v2
        integer :: nan_t, inf_t, n_t, oob_t
        integer :: nan_s, inf_s, n_s, oob_s
        integer :: nan_ro, inf_ro, n_ro, oob_ro
        integer :: nan_tot, inf_tot
        real :: min_u1, max_u1, mean_u1, rms_u1
        real :: min_v1, max_v1, mean_v1, rms_v1
        real :: min_u2, max_u2, mean_u2, rms_u2
        real :: min_v2, max_v2, mean_v2, rms_v2
        real :: min_t, max_t, mean_t, rms_t
        real :: min_s, max_s, mean_s, rms_s
        real :: min_ro, max_ro, mean_ro, rms_ro
        logical :: first

        ! label=='INIT': u1/v1 ещё не инициализированы и не опрашиваются —
        ! их статистика пишется нулями, а не мусором из неинициализированных локальных.
        min_u1 = 0.0; max_u1 = 0.0; mean_u1 = 0.0; rms_u1 = 0.0
        min_v1 = 0.0; max_v1 = 0.0; mean_v1 = 0.0; rms_v1 = 0.0

        nan_u1 = 0; inf_u1 = 0; n_u1 = 0; oob_u1 = 0
        nan_v1 = 0; inf_v1 = 0; n_v1 = 0; oob_v1 = 0
        nan_u2 = 0; inf_u2 = 0; n_u2 = 0; oob_u2 = 0
        nan_v2 = 0; inf_v2 = 0; n_v2 = 0; oob_v2 = 0
        nan_t = 0; inf_t = 0; n_t = 0; oob_t = 0
        nan_s = 0; inf_s = 0; n_s = 0; oob_s = 0
        nan_ro = 0; inf_ro = 0; n_ro = 0; oob_ro = 0

        if (label .ne. 'INIT') then
            call field_stats_spike(u1, s22_uv_spike, nan_u1, inf_u1, n_u1, &
                                   min_u1, max_u1, mean_u1, rms_u1, oob_u1)
            call field_stats_spike(v1, s22_uv_spike, nan_v1, inf_v1, n_v1, &
                                   min_v1, max_v1, mean_v1, rms_v1, oob_v1)
        end if
        call field_stats_spike(u2, s22_uv_spike, nan_u2, inf_u2, n_u2, &
                               min_u2, max_u2, mean_u2, rms_u2, oob_u2)
        call field_stats_spike(v2, s22_uv_spike, nan_v2, inf_v2, n_v2, &
                               min_v2, max_v2, mean_v2, rms_v2, oob_v2)
        call field_stats_band(t2, s22_t_lo, s22_t_hi, nan_t, inf_t, n_t, &
                              min_t, max_t, mean_t, rms_t, oob_t)
        call field_stats_band(s2, s22_s_lo, s22_s_hi, nan_s, inf_s, n_s, &
                              min_s, max_s, mean_s, rms_s, oob_s)
        call field_stats_band(ro, s22_ro_lo, s22_ro_hi, nan_ro, inf_ro, n_ro, &
                              min_ro, max_ro, mean_ro, rms_ro, oob_ro)

        nan_tot = nan_u1 + nan_v1 + nan_u2 + nan_v2 + nan_t + nan_s + nan_ro
        inf_tot = inf_u1 + inf_v1 + inf_u2 + inf_v2 + inf_t + inf_s + inf_ro
        if (nan_tot .gt. 0 .or. inf_tot .gt. 0) then
            print *, "STAGE 10.22 probe ", trim(label), " day=", day, " step=", step, &
                " NaN_total=", nan_tot, " Inf_total=", inf_tot
        end if

        ! Запись строки в stage1022_probes.csv (заголовок — только при создании).
        inquire (file=trim(run_csv_dir)//'/stage1022_probes.csv', exist=first)
        first = .not. first
        open (s22_unit_probe, file=trim(run_csv_dir)//'/stage1022_probes.csv', &
              position='append')
        if (first) then
            write (s22_unit_probe, '(A)') &
                "label,day,step,"// &
                "u1_nan,u1_inf,u1_n,u1_min,u1_max,u1_mean,u1_rms,u1_spike,"// &
                "v1_nan,v1_inf,v1_n,v1_min,v1_max,v1_mean,v1_rms,v1_spike,"// &
                "u2_nan,u2_inf,u2_n,u2_min,u2_max,u2_mean,u2_rms,u2_spike,"// &
                "v2_nan,v2_inf,v2_n,v2_min,v2_max,v2_mean,v2_rms,v2_spike,"// &
                "t_nan,t_inf,t_n,t_min,t_max,t_mean,t_rms,t_oob,"// &
                "s_nan,s_inf,s_n,s_min,s_max,s_mean,s_rms,s_oob,"// &
                "ro_nan,ro_inf,ro_n,ro_min,ro_max,ro_mean,ro_rms,ro_oob"
        end if
        write (s22_unit_probe, '(A,A1,I4,A1,I3,56(A1,ES16.5E2))') &
            trim(label), ',', day, ',', step, ',', &
            real(nan_u1), ',', real(inf_u1), ',', real(n_u1), ',', &
            min_u1, ',', max_u1, ',', mean_u1, ',', rms_u1, ',', real(oob_u1), ',', &
            real(nan_v1), ',', real(inf_v1), ',', real(n_v1), ',', &
            min_v1, ',', max_v1, ',', mean_v1, ',', rms_v1, ',', real(oob_v1), ',', &
            real(nan_u2), ',', real(inf_u2), ',', real(n_u2), ',', &
            min_u2, ',', max_u2, ',', mean_u2, ',', rms_u2, ',', real(oob_u2), ',', &
            real(nan_v2), ',', real(inf_v2), ',', real(n_v2), ',', &
            min_v2, ',', max_v2, ',', mean_v2, ',', rms_v2, ',', real(oob_v2), ',', &
            real(nan_t), ',', real(inf_t), ',', real(n_t), ',', &
            min_t, ',', max_t, ',', mean_t, ',', rms_t, ',', real(oob_t), ',', &
            real(nan_s), ',', real(inf_s), ',', real(n_s), ',', &
            min_s, ',', max_s, ',', mean_s, ',', rms_s, ',', real(oob_s), ',', &
            real(nan_ro), ',', real(inf_ro), ',', real(n_ro), ',', &
            min_ro, ',', max_ro, ',', mean_ro, ',', rms_ro, ',', real(oob_ro)
        close (s22_unit_probe)
    end subroutine s22_probe

    ! ==========================================================================
    ! s22_block200_budget: пересчёт бароклинного интеграла Block 200 и
    ! доминирующего члена ускорения. Точная копия стенсила B200 (ro-терма),
    ! но из u1 (pre-B200, не тронут блоком) и ro_used (в A4 — ro_ref).
    ! Амплификация max|U2|/max|U1| — рост скорости за шаг.
    ! Только чтение; вызывается в точке B200_after.
    ! ==========================================================================
    subroutine s22_block200_budget(day, step, dt, c1, c3, c8)
        integer, intent(in) :: day, step
        real, intent(in) :: dt, c1, c3, c8

        integer :: i, j, k, ki, i1, i2, j1, j2, k1, nlev
        real :: hht, ri2j, rij, ri2j2, rij2, a, b, a1, b1
        real :: cc_val, dzz, dzz1, uij, vij, slapu, slapv
        real :: sum_x, sum_y
        real :: max_sum, max_sum1, max_slap_u, max_slap_v
        real :: max_dp_u, max_dp_v, max_u1, max_v1, max_u2, max_v2
        real :: acc_bar_u, acc_bar_v, acc_dp_u, acc_dp_v, acc_lap_u, acc_lap_v
        real :: dp_ratio_u, dp_ratio_v, amp_u, amp_v
        real(8) :: ro_min, ro_max, ro_sum, ro_n
        real :: ro_mean
        logical :: use_ref, first
        real, parameter :: tiny1 = 1.0e-30

        use_ref = s22_freeze_ro_downstream
        max_sum = 0.0; max_sum1 = 0.0; max_slap_u = 0.0; max_slap_v = 0.0
        max_dp_u = 0.0; max_dp_v = 0.0
        max_u1 = 0.0; max_v1 = 0.0; max_u2 = 0.0; max_v2 = 0.0
        ro_min = huge(1.0_8); ro_max = -huge(1.0_8); ro_sum = 0.0_8; ro_n = 0.0_8

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                i1 = i + 1
                i2 = i - 1
                j1 = j + 1
                j2 = j - 1
                hht = map1(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle

                sum_x = 0.0
                sum_y = 0.0
                ! Начальные RO-значения для предыдущего уровня (уровень 0)
                if (use_ref) then
                    ri2j = s22_ro_ref(i2, j, 1)
                    rij = s22_ro_ref(i, j, 1)
                    ri2j2 = s22_ro_ref(i2, j2, 1)
                    rij2 = s22_ro_ref(i, j2, 1)
                else
                    ri2j = ro(i2, j, 1)
                    rij = ro(i, j, 1)
                    ri2j2 = ro(i2, j2, 1)
                    rij2 = ro(i, j2, 1)
                end if
                a = ri2j + rij - ri2j2 - rij2   ! ΔRO по X (уровень 0)
                b = ri2j2 + ri2j - rij2 - rij   ! ΔRO по Y (уровень 0)
                dzz = dz(1)

                do k = 1, ki
                    ! Если уровень совпадает с дном — B200 обнуляет скорость
                    ! (cycle, как в B200: накопление для этого уровня пропускается,
                    ! a/b/dzz остаются от предыдущего уровня)
                    if (abs(hht - z(k)) .lt. 1e-6) cycle
                    k1 = k + 1
                    dzz1 = dz(k1)
                    uij = u1(i, j, k)
                    vij = v1(i, j, k)
                    if (use_ref) then
                        ri2j = s22_ro_ref(i2, j, k)
                        rij2 = s22_ro_ref(i, j2, k)
                        rij = s22_ro_ref(i, j, k)
                        ri2j2 = s22_ro_ref(i2, j2, k)
                    else
                        ri2j = ro(i2, j, k)
                        rij2 = ro(i, j2, k)
                        rij = ro(i, j, k)
                        ri2j2 = ro(i2, j2, k)
                    end if
                    a1 = ri2j + rij - ri2j2 - rij2  ! ΔRO по X (уровень k)
                    b1 = ri2j2 + ri2j - rij2 - rij  ! ΔRO по Y (уровень k)

                    cc_val = c8*dzz
                    sum_x = sum_x + (a + a1)*cc_val
                    sum_y = sum_y + (b + b1)*cc_val
                    max_u1 = max(max_u1, abs(uij))
                    max_v1 = max(max_v1, abs(vij))
                    max_u2 = max(max_u2, abs(u2(i, j, k)))
                    max_v2 = max(max_v2, abs(v2(i, j, k)))

                    ! Поверхностный Лапласиан — для раскладки доминирующего члена
                    if (k .eq. 1) then
                        slapu = u1(i, j2, k) + u1(i, j1, k) + u1(i2, j, k) + &
                                u1(i1, j, k) - 4.0*uij
                        slapv = v1(i1, j, k) + v1(i2, j, k) + v1(i, j1, k) + &
                                v1(i, j2, k) - 4.0*vij
                        max_slap_u = max(max_slap_u, abs(slapu))
                        max_slap_v = max(max_slap_v, abs(slapv))
                    end if

                    ! Статистика RO, реально использованного в интеграле
                    if (use_ref) then
                        rij = s22_ro_ref(i, j, k)
                    else
                        rij = ro(i, j, k)
                    end if
                    ro_min = min(ro_min, real(rij, real64))
                    ro_max = max(ro_max, real(rij, real64))
                    ro_sum = ro_sum + real(rij, real64)
                    ro_n = ro_n + 1.0_8

                    a = a1
                    b = b1
                    dzz = dzz1
                end do

                max_sum = max(max_sum, abs(sum_x))
                max_sum1 = max(max_sum1, abs(sum_y))
                max_dp_u = max(max_dp_u, abs(dpx(i, j)))
                max_dp_v = max(max_dp_v, abs(dpy(i, j)))
            end do
        end do

        ! Доминирующий член ускорения за шаг dt [см/с]:
        !   baroclinic: dt·c1·|SUM| ; DPX: dt·|dpx| ; Laplacian: dt·c3·|SLAP|
        acc_bar_u = dt*c1*max_sum
        acc_bar_v = dt*c1*max_sum1
        acc_dp_u = dt*max_dp_u
        acc_dp_v = dt*max_dp_v
        acc_lap_u = dt*c3*max_slap_u
        acc_lap_v = dt*c3*max_slap_v
        dp_ratio_u = acc_bar_u/max(acc_dp_u, tiny1)
        dp_ratio_v = acc_bar_v/max(acc_dp_v, tiny1)
        amp_u = max_u2/max(max_u1, tiny1)
        amp_v = max_v2/max(max_v1, tiny1)
        if (ro_n .gt. 0.0_8) then
            ro_mean = real(ro_sum/ro_n)
        else
            ro_mean = 0.0
        end if

        inquire (file=trim(run_csv_dir)//'/stage1022_block200.csv', exist=first)
        first = .not. first
        open (s22_unit_b200, file=trim(run_csv_dir)//'/stage1022_block200.csv', &
              position='append')
        if (first) then
            write (s22_unit_b200, '(A)') &
                "day,step,ro_min,ro_max,ro_mean,sum_max,sum1_max,"// &
                "acc_bar_u,acc_bar_v,acc_dp_u,acc_dp_v,acc_lap_u,acc_lap_v,"// &
                "dp_ratio_u,dp_ratio_v,max_u1,max_v1,max_u2,max_v2,amp_u,amp_v"
        end if
        write (s22_unit_b200, '(I4,A1,I3,19(A1,ES16.5E2))') day, ',', step, ',', &
            real(ro_min), ',', real(ro_max), ',', ro_mean, ',', &
            max_sum, ',', max_sum1, ',', &
            acc_bar_u, ',', acc_bar_v, ',', acc_dp_u, ',', acc_dp_v, ',', &
            acc_lap_u, ',', acc_lap_v, ',', &
            dp_ratio_u, ',', dp_ratio_v, ',', &
            max_u1, ',', max_v1, ',', max_u2, ',', max_v2, ',', &
            amp_u, ',', amp_v
        close (s22_unit_b200)
    end subroutine s22_block200_budget

    ! ==========================================================================
    ! Накопители обусловленности Block 210 (Thomas). Вызываются из main.f90
    ! ВНУТРИ исторических циклов только под guard'ом s22_diag — при OFF
    ! вычисления не выполняются, сольвер не изменяется.
    ! ==========================================================================
    subroutine s22_b210_reset()
        s22_rr_min = huge(1.0_8)
        s22_rr_max = 0.0_8
        s22_piv_min = huge(1.0_8)
        s22_piv_neg = 0.0_8
        s22_piv_cnt = 0.0_8
        s22_rhs_max = 0.0_8
        s22_den_min = huge(1.0_8)
        s22_den_neg = 0.0_8
    end subroutine s22_b210_reset

    subroutine s22_b210_rr_update(v)
        real, intent(in) :: v
        if (real(v, real64) .lt. s22_rr_min) s22_rr_min = real(v, real64)
        if (real(v, real64) .gt. s22_rr_max) s22_rr_max = real(v, real64)
    end subroutine s22_b210_rr_update

    subroutine s22_b210_pivot_update(v)
        real, intent(in) :: v
        s22_piv_cnt = s22_piv_cnt + 1.0_8
        if (abs(real(v, real64)) .lt. s22_piv_min) s22_piv_min = abs(real(v, real64))
        if (v .le. 0.0) s22_piv_neg = s22_piv_neg + 1.0_8
    end subroutine s22_b210_pivot_update

    subroutine s22_b210_rhs_update(v)
        real(8), intent(in) :: v
        if (abs(v) .gt. s22_rhs_max) s22_rhs_max = abs(v)
    end subroutine s22_b210_rhs_update

    subroutine s22_b210_bottom_update(v)
        real(8), intent(in) :: v
        if (abs(v) .lt. s22_den_min) s22_den_min = abs(v)
        if (v .le. 0.0_8) s22_den_neg = s22_den_neg + 1.0_8
    end subroutine s22_b210_bottom_update

    subroutine s22_b210_flush(day, step)
        integer, intent(in) :: day, step
        logical :: first

        inquire (file=trim(run_csv_dir)//'/stage1022_block210.csv', exist=first)
        first = .not. first
        open (s22_unit_b210, file=trim(run_csv_dir)//'/stage1022_block210.csv', &
              position='append')
        if (first) then
            write (s22_unit_b210, '(A)') &
                "day,step,rr_min,rr_max,piv_min,piv_neg,piv_cnt,rhs_max,den_min,den_neg"
        end if
        write (s22_unit_b210, '(I4,A1,I3,8(A1,ES16.5E2))') day, ',', step, ',', &
            s22_rr_min, ',', s22_rr_max, ',', s22_piv_min, ',', s22_piv_neg, ',', &
            s22_piv_cnt, ',', s22_rhs_max, ',', s22_den_min, ',', s22_den_neg
        close (s22_unit_b210)
        call s22_b210_reset()
    end subroutine s22_b210_flush

    ! ==========================================================================
    ! Внутренние помощники: статистика одного 3D-поля по влажным T-ячейкам.
    ! NaN/Inf исключаются из min/max/mean/RMS; счётчики идут отдельно.
    ! ==========================================================================
    subroutine field_stats_spike(arr, threshold, nan_n, inf_n, nfin, &
                                 fmin, fmax, fmean, frms, nspike)
        real, intent(in) :: arr(:, :, :)
        real, intent(in) :: threshold
        integer, intent(out) :: nan_n, inf_n, nfin, nspike
        real, intent(out) :: fmin, fmax, fmean, frms

        integer :: i, j, k, ki_col
        real(8) :: ssum, ssq
        real :: x

        nan_n = 0
        inf_n = 0
        nfin = 0
        nspike = 0
        fmin = huge(1.0)
        fmax = -huge(1.0)
        ssum = 0.0_8
        ssq = 0.0_8
        do j = 2, js
            do i = 2, is
                ki_col = kt1(i, j)
                if (ki_col .eq. 0) cycle
                do k = 1, ki_col
                    x = arr(i, j, k)
                    if (ieee_is_nan(x)) then
                        nan_n = nan_n + 1
                    else if (.not. ieee_is_finite(x)) then
                        inf_n = inf_n + 1
                    else
                        nfin = nfin + 1
                        if (x .lt. fmin) fmin = x
                        if (x .gt. fmax) fmax = x
                        ssum = ssum + real(x, real64)
                        ssq = ssq + real(x, real64)**2
                        if (abs(x) .gt. threshold) nspike = nspike + 1
                    end if
                end do
            end do
        end do
        if (nfin .gt. 0) then
            fmean = real(ssum/real(nfin, real64))
            frms = real(sqrt(ssq/real(nfin, real64)))
        else
            fmin = 0.0
            fmax = 0.0
            fmean = 0.0
            frms = 0.0
        end if
    end subroutine field_stats_spike

    subroutine field_stats_band(arr, lo, hi, nan_n, inf_n, nfin, &
                                fmin, fmax, fmean, frms, noob)
        real, intent(in) :: arr(:, :, :)
        real, intent(in) :: lo, hi
        integer, intent(out) :: nan_n, inf_n, nfin, noob
        real, intent(out) :: fmin, fmax, fmean, frms

        integer :: i, j, k, ki_col
        real(8) :: ssum, ssq
        real :: x

        nan_n = 0
        inf_n = 0
        nfin = 0
        noob = 0
        fmin = huge(1.0)
        fmax = -huge(1.0)
        ssum = 0.0_8
        ssq = 0.0_8
        do j = 2, js
            do i = 2, is
                ki_col = kt1(i, j)
                if (ki_col .eq. 0) cycle
                do k = 1, ki_col
                    x = arr(i, j, k)
                    if (ieee_is_nan(x)) then
                        nan_n = nan_n + 1
                    else if (.not. ieee_is_finite(x)) then
                        inf_n = inf_n + 1
                    else
                        nfin = nfin + 1
                        if (x .lt. fmin) fmin = x
                        if (x .gt. fmax) fmax = x
                        ssum = ssum + real(x, real64)
                        ssq = ssq + real(x, real64)**2
                        if (x .lt. lo .or. x .gt. hi) noob = noob + 1
                    end if
                end do
            end do
        end do
        if (nfin .gt. 0) then
            fmean = real(ssum/real(nfin, real64))
            frms = real(sqrt(ssq/real(nfin, real64)))
        else
            fmin = 0.0
            fmax = 0.0
            fmean = 0.0
            frms = 0.0
        end if
    end subroutine field_stats_band

end module stage1022_diagnostics