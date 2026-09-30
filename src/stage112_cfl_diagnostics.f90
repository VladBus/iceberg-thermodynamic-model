! ==============================================================================
! Модуль: stage112_cfl_diagnostics
! Назначение: Диагностика CFL и численной устойчивости для Stage 11.2.
! Физика: Вычисляет числа Куранта для всех явных операторов модели,
!         отслеживает экстремальные значения скоростей, плотности,
!         термодинамических полей и фиксирует первое NaN/Inf событие.
!         ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
! ==============================================================================
module stage112_cfl_diagnostics
    use param
    use iso_c_binding
    implicit none

    ! --- ПЕРЕКЛЮЧАТЕЛИ (env-gated, default OFF) ---
    logical, save :: s112_enabled = .false.
    logical, save :: s112_first_invalid_tracking = .false.
    integer, save :: s112_output_interval = 1  ! каждый baroclinic step

    ! --- СТРУКТУРЫ ДАННЫХ ДЛЯ СОХРАНЕНИЯ МАКСИМУМОВ ---
    type cfl_max_info
        real :: value
        integer :: i, j, k
        real :: u, v, w, dx, dy, dz
    end type cfl_max_info

    type invalid_event_info
        logical :: found = .false.
        integer :: step_day, step_iii, step_jjj
        integer :: var_id  ! 1=U, 2=V, 3=W, 4=T, 5=S, 6=RO, 7=ETA
        integer :: i, j, k
        real :: value
        real :: prev_value
        real :: neighbor_avg
        real :: dt, dt1, dx, dy, dz
        real :: u, v, w, t, s, ro
        character(len=64) :: operator_name
    end type invalid_event_info

    ! --- НАКОПИТЕЛИ ДЛЯ ТЕКУЩЕГО ШАГА ---
    type(cfl_max_info), save :: cx_max, cy_max, cz_max, ch_max, cwave_max, ccor_max
    type(cfl_max_info), save :: diff_h_max, diff_v_max
    real, save :: u_max_abs, v_max_abs, w_max_abs
    real, save :: t_min, t_max, s_min, s_max, ro_min, ro_max
    real, save :: thermal_wind_max
    real, save :: rho_anomaly_max

    type(invalid_event_info), save :: first_invalid

    ! --- ФАЙЛЫ ВЫВОДА ---
    integer, save :: cfl_unit = 81
    integer, save :: events_unit = 86  ! 11.4-D24: было 82, конфликт с ca_diag_unit=82 (convective_adjustment.f90:88): CA открывает/закрывает 82 под convective_guard_events.csv, из-за чего строки s112 уходили в fort.82
    ! Stage 11.3C.1: распределение CFL (диагностика, открывается вместе с остальными)
    integer, save :: dist_unit = 87
    logical, save :: files_opened = .false.

    contains

    ! =========================================================================
    ! ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
    ! =========================================================================
    subroutine s112_init()
        character(len=256) :: env_str
        integer :: ios

        call get_environment_variable('STAGE112_CFL_DIAG', env_str)
        if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
            s112_enabled = .true.
        end if

        call get_environment_variable('STAGE112_FIRST_INVALID', env_str)
        if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
            s112_first_invalid_tracking = .true.
        end if

        if (.not. s112_enabled) return

        print *, ">>> STAGE 11.2 CFL DIAGNOSTICS ENABLED"

        ! Открыть файлы вывода
        open (cfl_unit, file='stage112_cfl_timeseries.csv', status='replace', iostat=ios)
        if (ios .eq. 0) then
            write (cfl_unit, '(A)') "day,iii,jjj,time_sec,cx_max,cy_max,ch_max,cz_max,cwave_max,ccor_max,diff_h_max,diff_v_max,u_max_abs,v_max_abs,w_max_abs,t_min,t_max,s_min,s_max,ro_min,ro_max,thermal_wind_max,rho_anomaly_max,cx_i,cx_j,cx_k,cy_i,cy_j,cy_k,cz_i,cz_j,cz_k,cwave_i,cwave_j,cwave_k"
        end if

        open (events_unit, file='stage112_stability_events.csv', status='replace', iostat=ios)
        if (ios .eq. 0) then
            write (events_unit, '(A)') "day,iii,jjj,time_sec,event_type,var_id,i,j,k,value,dt,dt1,dx,dy,dz,u,v,w,t,s,ro,operator"
        end if

        ! Stage 11.3C.1: гистограммные процентили CFL (P50/P90/P95/P99/max +
        ! доли >1/>0.5 + локация max Cz + |w| на ней). Только при ENABLED.
        open (dist_unit, file='cfl_distribution.csv', status='replace', iostat=ios)
        if (ios .eq. 0) then
            write (dist_unit, '(A)') "day,iii,cx_p50,cx_p90,cx_p95,cx_p99,cx_max,cx_fgt1,cx_fgt05," // &
                "cy_p50,cy_p90,cy_p95,cy_p99,cy_max,cy_fgt1,cy_fgt05," // &
                "cz_p50,cz_p90,cz_p95,cz_p99,cz_max,cz_fgt1,cz_fgt05,cz_mi,cz_mj,cz_mk,w_at_czmax"
        end if

        files_opened = .true.

        ! Сброс накопленных максимумов
        call s112_reset_maxima()
    end subroutine s112_init

    ! =========================================================================
    ! СБРОС МАКСИМУМОВ НА НАЧАЛО КАЖДОГО BAROCLINIC STEP
    ! =========================================================================
    subroutine s112_reset_maxima()
        cx_max%value = 0.0;  cx_max%i = 0;  cx_max%j = 0;  cx_max%k = 0
        cy_max%value = 0.0;  cy_max%i = 0;  cy_max%j = 0;  cy_max%k = 0
        cz_max%value = 0.0;  cz_max%i = 0;  cz_max%j = 0;  cz_max%k = 0
        ch_max%value = 0.0;  ch_max%i = 0;  ch_max%j = 0;  ch_max%k = 0
        cwave_max%value = 0.0;  cwave_max%i = 0;  cwave_max%j = 0;  cwave_max%k = 0
        ccor_max%value = 0.0;  ccor_max%i = 0;  ccor_max%j = 0;  ccor_max%k = 0
        diff_h_max%value = 0.0;  diff_h_max%i = 0;  diff_h_max%j = 0;  diff_h_max%k = 0
        diff_v_max%value = 0.0;  diff_v_max%i = 0;  diff_v_max%j = 0;  diff_v_max%k = 0

        u_max_abs = 0.0
        v_max_abs = 0.0
        w_max_abs = 0.0
        t_min = huge(1.0); t_max = -huge(1.0)
        s_min = huge(1.0); s_max = -huge(1.0)
        ro_min = huge(1.0); ro_max = -huge(1.0)
        thermal_wind_max = 0.0
        rho_anomaly_max = 0.0

        if (s112_first_invalid_tracking) then
            first_invalid%found = .false.
        end if
    end subroutine s112_reset_maxima

    ! =========================================================================
    ! ВЫЧИСЛЕНИЕ ГОРИЗОНТАЛЬНОГО CFL (ADVECTION CFL)
    ! cx = |U|*dt/dx, cy = |V|*dt/dy, ch = cx + cy
    ! Вызывается ПОСЛЕ Block 210 (u2/v2 обновлены) и ПЕРЕД advs/advt
    ! =========================================================================
    subroutine s112_compute_advection_cfl(dt_used, stage_name)
        real, intent(in) :: dt_used
        character(len=*), intent(in) :: stage_name
        integer :: i, j, k, ki
        real :: cx, cy, ch, u_local, v_local, dx_local, dy_local

        if (.not. s112_enabled) return

        dx_local = 1389000.0  ! dx = dy в модели
        dy_local = 1389000.0

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    u_local = abs(u2(i, j, k))
                    v_local = abs(v2(i, j, k))
                    cx = u_local * dt_used / dx_local
                    cy = v_local * dt_used / dy_local
                    ch = cx + cy

                    if (cx .gt. cx_max%value) then
                        cx_max%value = cx
                        cx_max%i = i; cx_max%j = j; cx_max%k = k
                        cx_max%u = u2(i, j, k); cx_max%v = v2(i, j, k)
                        cx_max%dx = dx_local; cx_max%dy = dy_local
                    end if
                    if (cy .gt. cy_max%value) then
                        cy_max%value = cy
                        cy_max%i = i; cy_max%j = j; cy_max%k = k
                        cy_max%u = u2(i, j, k); cy_max%v = v2(i, j, k)
                        cy_max%dx = dx_local; cy_max%dy = dy_local
                    end if
                    if (ch .gt. ch_max%value) then
                        ch_max%value = ch
                        ch_max%i = i; ch_max%j = j; ch_max%k = k
                        ch_max%u = u2(i, j, k); ch_max%v = v2(i, j, k)
                        ch_max%dx = dx_local; ch_max%dy = dy_local
                    end if

                    ! Максимальные |U|, |V|
                    if (u_local .gt. u_max_abs) u_max_abs = u_local
                    if (v_local .gt. v_max_abs) v_max_abs = v_local
                end do
            end do
        end do

        if (s112_first_invalid_tracking .and. .not. first_invalid%found) then
            if (cx_max%value .gt. 10.0 .or. cy_max%value .gt. 10.0 .or. ch_max%value .gt. 20.0) then
                call s112_record_event(stage_name, 'CFL_EXCESSIVE', 0, &
                    cx_max%i, cx_max%j, cx_max%k, ch_max%value, &
                    dt_used, 120.0, 1389000.0, 1389000.0, 0.0, &
                    cx_max%u, cy_max%u, 0.0, 0.0, 0.0, 0.0, 'advection_cfl')
            end if
        end if
    end subroutine s112_compute_advection_cfl

    ! =========================================================================
    ! ВЕРТИКАЛЬНЫЙ CFL: Cz = |W|*dt/dz
    ! W вычисляется в main.f90 перед advs/advt
    ! =========================================================================
    subroutine s112_compute_vertical_cfl(dt_used, stage_name)
        real, intent(in) :: dt_used
        character(len=*), intent(in) :: stage_name
        integer :: i, j, k, ki
        real :: cz, w_local, dz_local

        if (.not. s112_enabled) return

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    w_local = abs(w(i, j, k))
                    dz_local = dz(k)
                    if (dz_local .gt. 0.0) then
                        cz = w_local * dt_used / dz_local
                        if (cz .gt. cz_max%value) then
                            cz_max%value = cz
                            cz_max%i = i; cz_max%j = j; cz_max%k = k
                            cz_max%w = w(i, j, k); cz_max%dz = dz_local
                        end if
                        if (w_local .gt. w_max_abs) w_max_abs = w_local
                    end if
                end do
            end do
        end do

        if (s112_first_invalid_tracking .and. .not. first_invalid%found) then
            if (cz_max%value .gt. 1.0) then
                call s112_record_event(stage_name, 'VERTICAL_CFL_EXCESSIVE', 0, &
                    cz_max%i, cz_max%j, cz_max%k, cz_max%value, &
                    dt_used, 120.0, 1389000.0, 1389000.0, cz_max%dz, &
                    0.0, 0.0, cz_max%w, 0.0, 0.0, 0.0, 'vertical_cfl')
            end if
        end if
    end subroutine s112_compute_vertical_cfl

    ! =========================================================================
    ! BAROTROPIC GRAVITY WAVE CFL: Cwave = sqrt(g*H)*dt1/dx
    ! Вызывается в shallow_water или перед вызовом shal()
    ! =========================================================================
    subroutine s112_compute_barotropic_cfl(dt1_used, stage_name)
        real, intent(in) :: dt1_used
        character(len=*), intent(in) :: stage_name
        integer :: i, j
        real :: cwave, h_local, dx_local, g_local

        if (.not. s112_enabled) return

        dx_local = 1389000.0
        g_local = 981.0

        do j = 2, js
            do i = 2, is
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle
                h_local = max(ht(i, j), 50.0)  ! H_min = 50 см как в shallow_water
                cwave = sqrt(g_local * h_local) * dt1_used / dx_local
                if (cwave .gt. cwave_max%value) then
                    cwave_max%value = cwave
                    cwave_max%i = i; cwave_max%j = j; cwave_max%k = 0
                end if
            end do
        end do

        if (s112_first_invalid_tracking .and. .not. first_invalid%found) then
            if (cwave_max%value .gt. 1.0) then
                call s112_record_event(stage_name, 'BAROTROPIC_CFL_EXCESSIVE', 0, &
                    cwave_max%i, cwave_max%j, 0, cwave_max%value, &
                    3600.0, dt1_used, 1389000.0, 1389000.0, 0.0, &
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 'barotropic_cfl')
            end if
        end if
    end subroutine s112_compute_barotropic_cfl

    ! =========================================================================
    ! CORIOLIS STABILITY: f*dt
    ! Для semi-implicit Coriolis: устойчивость требует f*dt < 2
    ! =========================================================================
    subroutine s112_compute_coriolis_cfl(dt_used, stage_name)
        real, intent(in) :: dt_used
        character(len=*), intent(in) :: stage_name
        integer :: i, j
        real :: ccor, f_local

        if (.not. s112_enabled) return

        do j = 2, js
            do i = 2, is
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle
                f_local = abs(fku(i, j))
                ccor = f_local * dt_used
                if (ccor .gt. ccor_max%value) then
                    ccor_max%value = ccor
                    ccor_max%i = i; ccor_max%j = j; ccor_max%k = 0
                end if
            end do
        end do

        if (s112_first_invalid_tracking .and. .not. first_invalid%found) then
            if (ccor_max%value .gt. 2.0) then
                call s112_record_event(stage_name, 'CORIOLIS_CFL_EXCESSIVE', 0, &
                    ccor_max%i, ccor_max%j, 0, ccor_max%value, &
                    dt_used, 120.0, 1389000.0, 1389000.0, 0.0, &
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 'coriolis_cfl')
            end if
        end if
    end subroutine s112_compute_coriolis_cfl

    ! =========================================================================
    ! DIFFUSION STABILITY: D = K*dt/dx^2 (explicit)
    ! Горизонтальная: K_h = 7.5e6 cm^2/s
    ! Вертикальная: K_v = rr(k) — но решается неявно через Thomas
    ! =========================================================================
    subroutine s112_compute_diffusion_stability(dt_used, stage_name)
        real, intent(in) :: dt_used
        character(len=*), intent(in) :: stage_name
        real :: kh, dx_local, dh, dv
        integer :: i, j, k, ki

        if (.not. s112_enabled) return

        kh = 7.5e6  ! cm^2/s
        dx_local = 1389000.0

        ! Горизонтальная диффузия (явная часть FCT)
        dh = kh * dt_used / (dx_local * dx_local)
        diff_h_max%value = dh
        diff_h_max%dx = dx_local

        ! Вертикальная: проверяем rr(k) но НЕ как explicit CFL
        ! rr(k) хранится в param::rr
        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    if (rr(k) .gt. 0.0 .and. dz(k) .gt. 0.0) then
                        dv = rr(k) * dt_used / (dz(k) * dz(k))
                        if (dv .gt. diff_v_max%value) then
                            diff_v_max%value = dv
                            diff_v_max%i = i; diff_v_max%j = j; diff_v_max%k = k
                            diff_v_max%dz = dz(k)
                        end if
                    end if
                end do
            end do
        end do
    end subroutine s112_compute_diffusion_stability

    ! =========================================================================
    ! ТЕРМИЧЕСКИЙ ВЕТЕР И ПЛОТНОСТЬ
    ! =========================================================================
    subroutine s112_compute_thermal_wind_diagnostics(stage_name)
        character(len=*), intent(in) :: stage_name
        integer :: i, j, k, ki
        real :: drho_dx, drho_dy, tw_local, ro_local

        if (.not. s112_enabled) return

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    ro_local = ro(i, j, k)
                    if (abs(ro_local) .gt. rho_anomaly_max) rho_anomaly_max = abs(ro_local)
                    if (ro_local .lt. ro_min) ro_min = ro_local
                    if (ro_local .gt. ro_max) ro_max = ro_local

                    if (k .lt. ki) then
                        drho_dx = abs(ro(i-1, j, k) - ro(i, j, k)) / 1389000.0
                        drho_dy = abs(ro(i, j-1, k) - ro(i, j, k)) / 1389000.0
                        ! Приближение thermal wind: f*dU/dz = -g/rho0 * drho/dy
                        ! tw ~ g/rho0 * |drho/dy| * dz / f
                        ! Здесь просто флаг роста градиента плотности
                        tw_local = 981.0 * max(drho_dx, drho_dy) * dz(k) / max(abs(fku(i,j)), 1e-12)
                        if (tw_local .gt. thermal_wind_max) then
                            thermal_wind_max = tw_local
                        end if
                    end if
                end do
            end do
        end do

        ! T/S min/max
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    if (t2(i, j, k) .lt. t_min) t_min = t2(i, j, k)
                    if (t2(i, j, k) .gt. t_max) t_max = t2(i, j, k)
                    if (s2(i, j, k) .lt. s_min) s_min = s2(i, j, k)
                    if (s2(i, j, k) .gt. s_max) s_max = s2(i, j, k)
                end do
            end do
        end do
    end subroutine s112_compute_thermal_wind_diagnostics

    ! =========================================================================
    ! ПРОВЕРКА НА NaN/Inf — ПЕРВОЕ СОБЫТИЕ
    ! =========================================================================
    subroutine s112_check_first_invalid(var_id, var_name, i, j, k, val, stage_name, o_day, o_iii, o_time)
        integer, intent(in) :: var_id
        character(len=*), intent(in) :: var_name
        integer, intent(in) :: i, j, k
        real, intent(in) :: val
        character(len=*), intent(in) :: stage_name
        integer, intent(in), optional :: o_day, o_iii
        real, intent(in), optional :: o_time
        real :: neighbor_sum
        integer :: n_count, ki

        if (.not. s112_enabled .or. .not. s112_first_invalid_tracking) return
        if (first_invalid%found) return

        ! Проверка на NaN или Inf
        if (val .ne. val .or. abs(val) .gt. huge(1.0)*0.5) then
            first_invalid%found = .true.
            if (present(o_day)) first_invalid%step_day = o_day
            if (present(o_iii)) first_invalid%step_iii = o_iii
            first_invalid%var_id = var_id
            first_invalid%i = i
            first_invalid%j = j
            first_invalid%k = k
            first_invalid%value = val
            first_invalid%dt = 3600.0
            first_invalid%dt1 = 120.0
            first_invalid%dx = 1389000.0
            first_invalid%dy = 1389000.0
            first_invalid%dz = dz(k)
            first_invalid%u = u2(i, j, k)
            first_invalid%v = v2(i, j, k)
            first_invalid%w = w(i, j, k)
            first_invalid%t = t2(i, j, k)
            first_invalid%s = s2(i, j, k)
            first_invalid%ro = ro(i, j, k)
            first_invalid%operator_name = stage_name

            ! Соседние значения
            neighbor_sum = 0.0
            n_count = 0
            if (i .gt. 2 .and. i .lt. is) then
                neighbor_sum = neighbor_sum + u2(i-1, j, k) + u2(i+1, j, k)
                n_count = n_count + 2
            end if
            if (j .gt. 2 .and. j .lt. js) then
                neighbor_sum = neighbor_sum + u2(i, j-1, k) + u2(i, j+1, k)
                n_count = n_count + 2
            end if
            if (k .gt. 1 .and. k .lt. ki) then
                neighbor_sum = neighbor_sum + u2(i, j, k-1) + u2(i, j, k+1)
                n_count = n_count + 2
            end if
            if (n_count .gt. 0) first_invalid%neighbor_avg = neighbor_sum / n_count

            if (present(o_day) .and. present(o_iii) .and. present(o_time)) then
                call s112_record_event(stage_name, 'FIRST_INVALID', var_id, i, j, k, val, &
                    3600.0, 120.0, 1389000.0, 1389000.0, dz(k), &
                    u2(i, j, k), v2(i, j, k), w(i, j, k), t2(i, j, k), s2(i, j, k), ro(i, j, k), stage_name, &
                    o_day=o_day, o_iii=o_iii, o_time=o_time)
            else
                call s112_record_event(stage_name, 'FIRST_INVALID', var_id, i, j, k, val, &
                    3600.0, 120.0, 1389000.0, 1389000.0, dz(k), &
                    u2(i, j, k), v2(i, j, k), w(i, j, k), t2(i, j, k), s2(i, j, k), ro(i, j, k), stage_name)
            end if
        end if
    end subroutine s112_check_first_invalid

    ! =========================================================================
    ! СКАНИРОВАНИЕ СОСТОЯНИЯ ОКЕАНА — первое невалидное значение (11.4-D24)
    !
    ! Диагностический сканер первого невалидного (NaN/Inf) состояния.
    ! Проверяет wet-ячейки (kt1>0, k<=kt1 — та же маска, что daily_diagnostics
    ! в main.f90) в порядке входов операторов: S1, T1 (входы advs/advt, пишет heat),
    ! затем T, S, RO, U, V, W — чтобы различить A (EOS генерирует NaN из конечных
    ! входов: T,S конечны, RO=NaN), B (EOS получает невалидные входы: T или S уже
    ! NaN), E (импульс первым: U/V NaN при конечных T/S/RO) и H (heat пишет NaN в
    ! S1/T1: S1/T1 невалидны при конечных S2/T2). var_id: 1=U,2=V,3=W,4=T,5=S,6=RO,
    ! 7=ETA, 8=S1, 9=T1.
    ! операторов (AFTER_conv_adj, AFTER_block200, AFTER_block210, END_step).
    ! При выключенных STAGE112_CFL_DIAG / STAGE112_FIRST_INVALID — мгновенный
    ! возврат, поведение модели бит-идентично legacy. После фиксации первого
    ! события — возврат без сканирования (сохраняется ПЕРВОЕ событие).
    ! Физику не меняет: только чтение состояния + запись в events CSV.
    ! =========================================================================
    logical function s112_is_invalid(val)
        real, intent(in) :: val
        s112_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function s112_is_invalid

    subroutine s112_scan_ocean_state(day, iii, time_sec, stage_name)
        integer, intent(in) :: day, iii
        real, intent(in) :: time_sec
        character(len=*), intent(in) :: stage_name
        integer :: i, j, k, ki

        if (.not. s112_enabled .or. .not. s112_first_invalid_tracking) return
        if (first_invalid%found) return
        if (.not. files_opened) return

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    if (s112_is_invalid(s1(i, j, k))) then
                        call s112_check_first_invalid(8, 'S1', i, j, k, s1(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(t1(i, j, k))) then
                        call s112_check_first_invalid(9, 'T1', i, j, k, t1(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(t2(i, j, k))) then
                        call s112_check_first_invalid(4, 'T', i, j, k, t2(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(s2(i, j, k))) then
                        call s112_check_first_invalid(5, 'S', i, j, k, s2(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(ro(i, j, k))) then
                        call s112_check_first_invalid(6, 'RO', i, j, k, ro(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(u2(i, j, k))) then
                        call s112_check_first_invalid(1, 'U', i, j, k, u2(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(v2(i, j, k))) then
                        call s112_check_first_invalid(2, 'V', i, j, k, v2(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                    if (s112_is_invalid(w(i, j, k))) then
                        call s112_check_first_invalid(3, 'W', i, j, k, w(i, j, k), stage_name, &
                            o_day=day, o_iii=iii, o_time=time_sec)
                        return
                    end if
                end do
            end do
        end do
    end subroutine s112_scan_ocean_state

    ! =========================================================================
    ! ЗАПИСЬ СОБЫТИЯ В CSV
    ! =========================================================================
    subroutine s112_record_event(stage_name, event_type, var_id, i, j, k, val, &
                                  dt, dt1, dx, dy, dz, u, v, w, t, s, ro, operator_name, &
                                  o_day, o_iii, o_time)
        character(len=*), intent(in) :: stage_name, event_type, operator_name
        integer, intent(in) :: var_id, i, j, k
        real, intent(in) :: val, dt, dt1, dx, dy, dz, u, v, w, t, s, ro
        integer, intent(in), optional :: o_day, o_iii
        real, intent(in), optional :: o_time
        integer :: w_day, w_iii
        real :: w_time

        if (.not. files_opened) return

        w_day = 0; w_iii = 0; w_time = 0.0
        if (present(o_day)) w_day = o_day
        if (present(o_iii)) w_iii = o_iii
        if (present(o_time)) w_time = o_time

        write (events_unit, '(I3,",",I3,",",I3,",",F12.1,",",A,",",I1,",",I4,",",I4,",",I2,",",E15.6,",",F8.1,",",F8.1,",",F12.1,",",F12.1,",",F8.1,",",E15.6,",",E15.6,",",E15.6,",",E15.6,",",E15.6,",",E15.6,",",A)') &
            w_day, w_iii, 0, w_time, trim(event_type), var_id, i, j, k, val, &
            dt, dt1, dx, dy, dz, u, v, w, t, s, ro, trim(operator_name)
    end subroutine s112_record_event

    ! =========================================================================
    ! Stage 11.3C.1: ПРОЦЕНТИЛЬ ИЗ ГИСТОГРАММЫ (вспомогательная)
    ! =========================================================================
    subroutine s112_pct(hist, nbins, maxv, n, p50, p90, p95, p99)
        integer, intent(in) :: nbins, n
        integer, intent(in) :: hist(nbins)
        real, intent(in) :: maxv
        real, intent(out) :: p50, p90, p95, p99
        integer :: b, acc
        integer :: t50, t90, t95, t99
        p50 = 0.0; p90 = 0.0; p95 = 0.0; p99 = 0.0
        if (n .le. 0 .or. maxv .le. 0.0) return
        t50 = int(0.50*n) + 1; t90 = int(0.90*n) + 1
        t95 = int(0.95*n) + 1; t99 = int(0.99*n) + 1
        acc = 0
        do b = 1, nbins
            acc = acc + hist(b)
            if (p50 .eq. 0.0 .and. acc .ge. t50) p50 = (real(b) - 0.5)/real(nbins)*maxv
            if (p90 .eq. 0.0 .and. acc .ge. t90) p90 = (real(b) - 0.5)/real(nbins)*maxv
            if (p95 .eq. 0.0 .and. acc .ge. t95) p95 = (real(b) - 0.5)/real(nbins)*maxv
            if (p99 .eq. 0.0 .and. acc .ge. t99) p99 = (real(b) - 0.5)/real(nbins)*maxv
        end do
    end subroutine s112_pct

    ! =========================================================================
    ! Stage 11.3C.1: РАСПРЕДЕЛЕНИЕ CFL (процентили + доли + локация max Cz)
    ! Два прохода по мокрым клеткам: (1) максимумы/счётчики, (2) гистограммы
    ! 2000 бинов. NaN пропускаются (в счёт n не входят). Только при ENABLED.
    ! =========================================================================
    subroutine s112_cfl_dist(dt_used, day, iii)
        real, intent(in) :: dt_used
        integer, intent(in) :: day, iii
        integer, parameter :: NB = 2000
        integer :: i, j, k, ki, b
        real :: cx, cy, cz, dxl, dzl, wl
        real :: mxx, mxy, mxz, wloc
        integer :: lxi, lxj, lxk, lyi, lyj, lyk, lzi, lzj, lzk
        integer :: hx(NB), hy(NB), hz(NB)
        integer :: nx, ny, nz, n1x, n1y, n1z, n05x, n05y, n05z
        real :: p50x, p90x, p95x, p99x, p50y, p90y, p95y, p99y, p50z, p90z, p95z, p99z
        real :: f1x, f05x, f1y, f05y, f1z, f05z

        if (.not. s112_enabled .or. .not. files_opened) return
        dxl = 1389000.0
        hx = 0; hy = 0; hz = 0
        mxx = 0.0; mxy = 0.0; mxz = 0.0
        lxi = 0; lxj = 0; lxk = 0; lyi = 0; lyj = 0; lyk = 0; lzi = 0; lzj = 0; lzk = 0
        wloc = 0.0
        nx = 0; ny = 0; nz = 0
        n1x = 0; n1y = 0; n1z = 0; n05x = 0; n05y = 0; n05z = 0

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    cx = abs(u2(i, j, k))*dt_used/dxl
                    if (cx .eq. cx) then
                        nx = nx + 1
                        if (cx .gt. 1.0) n1x = n1x + 1
                        if (cx .gt. 0.5) n05x = n05x + 1
                        if (cx .gt. mxx) then
                            mxx = cx; lxi = i; lxj = j; lxk = k
                        end if
                    end if
                    cy = abs(v2(i, j, k))*dt_used/dxl
                    if (cy .eq. cy) then
                        ny = ny + 1
                        if (cy .gt. 1.0) n1y = n1y + 1
                        if (cy .gt. 0.5) n05y = n05y + 1
                        if (cy .gt. mxy) then
                            mxy = cy; lyi = i; lyj = j; lyk = k
                        end if
                    end if
                    dzl = dz(k)
                    if (dzl .gt. 0.0) then
                        wl = abs(w(i, j, k))
                        cz = wl*dt_used/dzl
                        if (cz .eq. cz) then
                            nz = nz + 1
                            if (cz .gt. 1.0) n1z = n1z + 1
                            if (cz .gt. 0.5) n05z = n05z + 1
                            if (cz .gt. mxz) then
                                mxz = cz; lzi = i; lzj = j; lzk = k; wloc = w(i, j, k)
                            end if
                        end if
                    end if
                end do
            end do
        end do

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    cx = abs(u2(i, j, k))*dt_used/dxl
                    if (cx .eq. cx .and. mxx .gt. 0.0) then
                        b = min(NB, int(cx/mxx*real(NB)) + 1)
                        hx(max(1, b)) = hx(max(1, b)) + 1
                    end if
                    cy = abs(v2(i, j, k))*dt_used/dxl
                    if (cy .eq. cy .and. mxy .gt. 0.0) then
                        b = min(NB, int(cy/mxy*real(NB)) + 1)
                        hy(max(1, b)) = hy(max(1, b)) + 1
                    end if
                    dzl = dz(k)
                    if (dzl .gt. 0.0) then
                        cz = abs(w(i, j, k))*dt_used/dzl
                        if (cz .eq. cz .and. mxz .gt. 0.0) then
                            b = min(NB, int(cz/mxz*real(NB)) + 1)
                            hz(max(1, b)) = hz(max(1, b)) + 1
                        end if
                    end if
                end do
            end do
        end do

        call s112_pct(hx, NB, mxx, nx, p50x, p90x, p95x, p99x)
        call s112_pct(hy, NB, mxy, ny, p50y, p90y, p95y, p99y)
        call s112_pct(hz, NB, mxz, nz, p50z, p90z, p95z, p99z)
        f1x = real(n1x)/real(max(nx, 1)); f05x = real(n05x)/real(max(nx, 1))
        f1y = real(n1y)/real(max(ny, 1)); f05y = real(n05y)/real(max(ny, 1))
        f1z = real(n1z)/real(max(nz, 1)); f05z = real(n05z)/real(max(nz, 1))

        write (dist_unit, '(I0,",",I0,21(",",ES12.4E2),3(",",I0),",",ES12.4E2)') &
            day, iii, &
            p50x, p90x, p95x, p99x, mxx, f1x, f05x, &
            p50y, p90y, p95y, p99y, mxy, f1y, f05y, &
            p50z, p90z, p95z, p99z, mxz, f1z, f05z, &
            lzi, lzj, lzk, wloc
    end subroutine s112_cfl_dist

    ! =========================================================================
    ! ЗАПИСЬ ТАЙМСЕРИИ CFL (каждый baroclinic step)
    ! =========================================================================
    subroutine s112_write_timeseries(day, iii, jjj, time_sec)
        integer, intent(in) :: day, iii, jjj
        real, intent(in) :: time_sec

        if (.not. s112_enabled .or. .not. files_opened) return
        if (mod(iii, s112_output_interval) .ne. 0) return

        ! Write CSV line using advance='no' for each field
        write (cfl_unit, '(I0)', advance='no') day
        write (cfl_unit, '(",",I0)', advance='no') iii
        write (cfl_unit, '(",",I0)', advance='no') jjj
        write (cfl_unit, '(",",F12.1)', advance='no') time_sec
        
        write (cfl_unit, '(",",ES12.4E2)', advance='no') cx_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') cy_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') ch_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') cz_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') cwave_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') ccor_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') diff_h_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') diff_v_max%value
        write (cfl_unit, '(",",ES12.4E2)', advance='no') u_max_abs
        write (cfl_unit, '(",",ES12.4E2)', advance='no') v_max_abs
        write (cfl_unit, '(",",ES12.4E2)', advance='no') w_max_abs
        write (cfl_unit, '(",",ES12.4E2)', advance='no') t_min
        write (cfl_unit, '(",",ES12.4E2)', advance='no') t_max
        write (cfl_unit, '(",",ES12.4E2)', advance='no') s_min
        write (cfl_unit, '(",",ES12.4E2)', advance='no') s_max
        write (cfl_unit, '(",",ES12.4E2)', advance='no') ro_min
        write (cfl_unit, '(",",ES12.4E2)', advance='no') ro_max
        write (cfl_unit, '(",",ES12.4E2)', advance='no') thermal_wind_max
        write (cfl_unit, '(",",ES12.4E2)', advance='no') rho_anomaly_max
        
        write (cfl_unit, '(",",I0)', advance='no') cx_max%i
        write (cfl_unit, '(",",I0)', advance='no') cx_max%j
        write (cfl_unit, '(",",I0)', advance='no') cx_max%k
        write (cfl_unit, '(",",I0)', advance='no') cy_max%i
        write (cfl_unit, '(",",I0)', advance='no') cy_max%j
        write (cfl_unit, '(",",I0)', advance='no') cy_max%k
        write (cfl_unit, '(",",I0)', advance='no') cz_max%i
        write (cfl_unit, '(",",I0)', advance='no') cz_max%j
        write (cfl_unit, '(",",I0)', advance='no') cz_max%k
        write (cfl_unit, '(",",I0)', advance='no') cwave_max%i
        write (cfl_unit, '(",",I0)', advance='no') cwave_max%j
        write (cfl_unit, '( ",",I0)') cwave_max%k  ! Last field with newline
    end subroutine s112_write_timeseries

    ! =========================================================================
    ! ФИНАЛИЗАЦИЯ
    ! =========================================================================
    subroutine s112_finalize()
        if (.not. s112_enabled) return
        if (files_opened) then
            close (cfl_unit)
            close (events_unit)
            files_opened = .false.
        end if

        ! Summary в консоль
        print *, "=== STAGE 11.2 CFL SUMMARY ==="
        print '(A,E12.4,A,I4,A,I4,A,I2,A)', "Max Cx = ", cx_max%value, " at (", cx_max%i, ",", cx_max%j, ",", cx_max%k, ")"
        print '(A,E12.4,A,I4,A,I4,A,I2,A)', "Max Cy = ", cy_max%value, " at (", cy_max%i, ",", cy_max%j, ",", cy_max%k, ")"
        print '(A,E12.4,A,I4,A,I4,A,I2,A)', "Max Ch = ", ch_max%value, " at (", ch_max%i, ",", ch_max%j, ",", ch_max%k, ")"
        print '(A,E12.4,A,I4,A,I4,A,I2,A)', "Max Cz = ", cz_max%value, " at (", cz_max%i, ",", cz_max%j, ",", cz_max%k, ")"
        print '(A,E12.4,A,I4,A,I4,A)', "Max Cwave = ", cwave_max%value, " at (", cwave_max%i, ",", cwave_max%j, ")"
        print '(A,E12.4,A,I4,A,I4,A)', "Max f*dt = ", ccor_max%value, " at (", ccor_max%i, ",", ccor_max%j, ")"
        print '(A,E12.4)', "Max Dh = ", diff_h_max%value
        print '(A,E12.4)', "Max Dv = ", diff_v_max%value
        print '(A,E12.4)', "Max |U| = ", u_max_abs
        print '(A,E12.4)', "Max |V| = ", v_max_abs
        print '(A,E12.4)', "Max |W| = ", w_max_abs
        print '(A,E12.4,A,E12.4,A)', "T range = [", t_min, ",", t_max, "]"
        print '(A,E12.4,A,E12.4,A)', "S range = [", s_min, ",", s_max, "]"
        print '(A,E12.4,A,E12.4,A)', "RO range = [", ro_min, ",", ro_max, "]"
        print '(A,E12.4)', "Max |RO| = ", rho_anomaly_max
        print '(A,E12.4)', "Max thermal wind ~ ", thermal_wind_max
        if (first_invalid%found) then
            print *, "FIRST INVALID EVENT DETECTED:"
            print '(A,I4,A,I3)', "  day=", first_invalid%step_day, " iii=", first_invalid%step_iii
            print '(A,I1,A,I4,A,I4,A,I2)', "  var_id=", first_invalid%var_id, &
                " i=", first_invalid%i, " j=", first_invalid%j, " k=", first_invalid%k
            print '(A,E15.6)', "  value=", first_invalid%value
            print '(A,A)', "  operator=", trim(first_invalid%operator_name)
        else
            print *, "No NaN/Inf detected during run."
        end if
        print *, "==============================="
    end subroutine s112_finalize

end module stage112_cfl_diagnostics