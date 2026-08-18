! ==============================================================================
! Модуль: convective_adjustment
! Назначение: Восстановление исторической схемы конвективного перемешивания
!             океанской толщи (блок "density calculation" оригинальной модели).
! Физика: Для каждого столбца (I,J) вычисляется плотность RR по уравнению
!         состояния Эккарта. Если плотностная инверсия превышает порог
!         0.9E-7 г/см3 (RR(K)-RR(K1) > 0.9E-7), соседние уровни K и K1
!         полностью перемешиваются: T и S осредняются с объёмным весом по
!         толщинам полуслоёв DZ1(K), DZ1(K1), после чего обоим уровням
!         присваивается одинаковое значение (сохранение интеграла T*DZ1, S*DZ1).
!         Проход по столбцу повторяется, пока за полный проход не было ни
!         одного перемешивания (фиксированная точка).
! Единицы: T [°C], S [массовая доля], DZ1 [см], RO [г/см3].
! Зависимости: param (поля T2/S2/RO, толщины DZ1, маска KT1),
!              equation_of_state (density_anomaly).
! Источник: Nesterov_last.txt:2041-2083, Dmitriev.txt:2112-2154,
!           Nesterov_copy1.txt:2241-2283, model/Coupl1.f90:818-855 (идентичны).
! ==============================================================================

module convective_adjustment
    use param
    use equation_of_state, only: density_anomaly
    implicit none

    private
    public :: conv_adj, convect_column, ca_reset, ca_stats, ca_probe_inversions

    ! Порог плотностной инверсии [г/см3] - историческое значение.
    real, parameter :: eps_density = 0.9e-7

    ! Диагностические счётчики convective adjustment (этап 4.2, мониторинг).
    ! НЕ меняют алгоритм перемешивания - только фиксируют статистику для отчёта.
    integer, save :: ca_total_nmix = 0      ! суммарное число перемешиваний
    integer, save :: ca_max_iter = 0        ! максимальное число итераций в столбце
    integer, save :: ca_guard_hits = 0      ! число столбцов с iter_count > 1000
    integer, save :: ca_affected_cols = 0   ! число столбцов, где было перемешивание

    ! --- Мониторинг срабатывания guard (этап 4.3, ТОЛЬКО диагностика) ---
    ! Стратегия ограничения объёма вывода: журналируем не более
    ! ca_guard_evt_cap событий за сутки (первые N). Для каждого события
    ! пишем одну строку в convective_guard_events.csv с координатами,
    ! счётчиками, проблемным интерфейсом, сохранностью T/S и состоянием
    ! интерфейса до/после guard. Полные профили не пишем - они восстанавливаются
    ! из суточных NetCDF-срезов results_day_XX.nc средствами Python.
    integer, parameter :: ca_guard_evt_cap = 100    ! событий/сутки в CSV
    integer, save :: ca_evt_written = 0             ! записано за сутки
    logical, save :: ca_evt_header = .false.        ! заголовок CSV написан
    integer, parameter :: ca_diag_unit = 82         ! логический блок CSV

contains

    ! ==========================================================================
    ! convect_column: ядро convective adjustment для одного столбца (чистое,
    !                 зависит только от переданных массивов - используется
    !                 в unit/regression tests).
    ! Вход:    cdz1(:) - толщины полуслоёв DZ1 [см], ki - число уровней.
    ! Вход/выход: ct(:), cs(:) - температура и соленость уровней (изменяются).
    ! Выход:   nmix - суммарное число выполненных перемешиваний.
    ! Опционально: o_iter_count - число проходов (итераций) по столбцу,
    !              o_guard_hit - сработал ли сторожевой предел iter_count > 1000.
    !              o_k_problem - номер интерфейса с максимальной остаточной
    !                            инверсией на выходе (0 = инверсий нет).
    !              o_resid_inv - величина этой остаточной инверсии [г/см3].
    !              Эти выходы используются только для мониторинга (этап 4.3)
    !              и не влияют на алгоритм.
    ! ==========================================================================
    subroutine convect_column(ct, cs, cdz1, ki, nmix, o_iter_count, o_guard_hit, &
                              o_k_problem, o_resid_inv)
        real, intent(inout) :: ct(:), cs(:)
        real, intent(in) :: cdz1(:)
        integer, intent(in) :: ki
        integer, intent(out) :: nmix
        integer, intent(out), optional :: o_iter_count
        logical, intent(out), optional :: o_guard_hit
        integer, intent(out), optional :: o_k_problem
        real, intent(out), optional :: o_resid_inv
        real :: cr(ks)
        real :: dzz, dzz1, dz1z, a
        real :: resid, rmax_inv
        integer :: k, k1, ki2, a1
        integer :: iter_count

        nmix = 0
        if (present(o_iter_count)) o_iter_count = 0
        if (present(o_guard_hit)) o_guard_hit = .false.
        if (present(o_k_problem)) o_k_problem = 0
        if (present(o_resid_inv)) o_resid_inv = 0.0
        if (ki .le. 0) return

        ! Плотность до перемешивания
        do k = 1, ki
            cr(k) = density_anomaly(ct(k), cs(k))
        end do

        if (ki .eq. 1) return

        ! Внешний проход: повторяется, пока было хотя бы одно смешивание.
        iter_count = 0
        do
            iter_count = iter_count + 1
            dzz = cdz1(1)
            ki2 = ki - 1
            a1 = 0
            do k = 1, ki2
                k1 = k + 1
                dzz1 = cdz1(k1)
                dz1z = dzz + dzz1
                a = cr(k) - cr(k1)
                if (a .le. eps_density) then
                    dzz = dzz1
                    cycle
                end if
                a1 = a1 + 1
                ! Объёмно-взвешенное осреднение по толщинам полуслоёв DZZ/DZZ1.
                ct(k) = (ct(k)*dzz + ct(k1)*dzz1)/dz1z
                cs(k) = (cs(k)*dzz + cs(k1)*dzz1)/dz1z
                ct(k1) = ct(k)
                cs(k1) = cs(k)
                ! Пересчет плотности перемешанных уровней.
                cr(k) = density_anomaly(ct(k), cs(k))
                cr(k1) = cr(k)
                dzz = dzz1
            end do
            nmix = nmix + a1
            if (a1 .eq. 0) exit
            ! Защита от бесконечного цикла: исторический алгоритм должен
            ! сходиться за ~20 итераций. >1000 = баг/несходимость.
            if (iter_count .gt. 1000) then
                if (present(o_guard_hit)) o_guard_hit = .true.
                exit
            end if
        end do
        if (present(o_iter_count)) o_iter_count = iter_count

        ! Остаточная инверсия на выходе: max(RO(k)-RO(k+1)) по интерфейсам.
        ! Диагностика этапа 4.3 - не влияет на алгоритм.
        if (present(o_k_problem) .or. present(o_resid_inv)) then
            rmax_inv = -huge(1.0)
            resid = 0.0
            do k = 1, ki - 1
                resid = cr(k) - cr(k + 1)
                if (resid .gt. rmax_inv) then
                    rmax_inv = resid
                    k1 = k
                end if
            end do
            if (present(o_k_problem)) then
                if (rmax_inv .gt. eps_density) then
                    o_k_problem = k1
                else
                    o_k_problem = 0
                end if
            end if
            if (present(o_resid_inv)) then
                if (rmax_inv .gt. eps_density) then
                    o_resid_inv = rmax_inv
                else
                    o_resid_inv = 0.0
                end if
            end if
        end if
    end subroutine convect_column

    ! ==========================================================================
    ! conv_adj: применение convective adjustment ко всем водным колонкам поля.
    ! Обновляет T2/S2 и пересчитывает RO. Не затрагивает уравнения движения
    ! (RO в momentum не используется на этапах 3.1-3.2).
    ! Вход (диагностика этапа 4.3, опционально): day, step - модельные сутки и
    ! бароклинный шаг III внутри суток, для привязки журнала guard-событий.
    ! ==========================================================================
    subroutine conv_adj(day, step)
        integer, intent(in), optional :: day, step
        integer :: i, j, k, ki, nmix
        integer :: iter_count, k_problem
        logical :: guard_hit
        real :: resid_inv
        real :: ct(ks), cs(ks), cdz1(ks)
        real :: t_before(ks), s_before(ks)

        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    ct(k) = t2(i, j, k)
                    cs(k) = s2(i, j, k)
                end do
                cdz1(1:ki) = dz1(1:ki)
                call convect_column(ct, cs, cdz1, ki, nmix, iter_count, guard_hit, &
                                    k_problem, resid_inv)
                ca_total_nmix = ca_total_nmix + nmix
                if (nmix .gt. 0) ca_affected_cols = ca_affected_cols + 1
                if (guard_hit) then
                    ca_guard_hits = ca_guard_hits + 1
                    ! Журналирование события (этап 4.3, ТОЛЬКО диагностика):
                    ! до вызова convect_column в t_before/s_before лежит входной
                    ! профиль, после - состояние на выходе (после guard).
                    if (present(day) .and. ca_evt_written .lt. ca_guard_evt_cap) then
                        do k = 1, ki
                            t_before(k) = t2(i, j, k)
                            s_before(k) = s2(i, j, k)
                        end do
                        call ca_log_guard_event(day, step, i, j, ki, iter_count, &
                                                nmix, k_problem, resid_inv, &
                                                t_before, s_before, ct, cs, cdz1)
                    end if
                end if
                ca_max_iter = max(ca_max_iter, iter_count)
                do k = 1, ki
                    t2(i, j, k) = ct(k)
                    s2(i, j, k) = cs(k)
                    ro(i, j, k) = density_anomaly(ct(k), cs(k))
                end do
            end do
        end do
    end subroutine conv_adj

    ! ==========================================================================
    ! ca_log_guard_event: запись одной строки в data/output/convective_guard_events.csv
    ! для срабатывания guard в столбце (i,j). Строка содержит: сутки, шаг III,
    ! координаты, KI, iter_count, nmix, проблемный интерфейс и его остаточную
    ! инверсию, а также сохранность интегралов T*DZ1/S*DZ1 (абсолютная и
    ! относительная ошибка до/после guard). ТОЛЬКО диагностика.
    ! ==========================================================================
    subroutine ca_log_guard_event(day, step, i, j, ki, iter_count, nmix, &
                                  k_problem, resid_inv, t_before, s_before, &
                                  t_after, s_after, cdz1)
        integer, intent(in) :: day, step, i, j, ki, iter_count, nmix, k_problem
        real, intent(in) :: resid_inv
        real, intent(in) :: t_before(:), s_before(:), t_after(:), s_after(:), cdz1(:)
        real :: tdz_before, tdz_after, sdz_before, sdz_after
        real :: dtdz, dsdz, rel_t, rel_s
        integer :: k

        tdz_before = 0.0; tdz_after = 0.0
        sdz_before = 0.0; sdz_after = 0.0
        do k = 1, ki
            tdz_before = tdz_before + t_before(k)*cdz1(k)
            sdz_before = sdz_before + s_before(k)*cdz1(k)
            tdz_after = tdz_after + t_after(k)*cdz1(k)
            sdz_after = sdz_after + s_after(k)*cdz1(k)
        end do
        dtdz = tdz_after - tdz_before
        dsdz = sdz_after - sdz_before
        if (abs(tdz_before) .gt. 1e-30) then
            rel_t = abs(dtdz)/abs(tdz_before)
        else
            rel_t = 0.0
        end if
        if (abs(sdz_before) .gt. 1e-30) then
            rel_s = abs(dsdz)/abs(sdz_before)
        else
            rel_s = 0.0
        end if

        if (.not. ca_evt_header) then
            open (ca_diag_unit, file=trim(run_csv_dir)//'/convective_guard_events.csv', &
                  status='replace')
            write (ca_diag_unit, '(A)') &
                "day,step,i,j,ki,iter_count,nmix,k_problem,resid_inv,"// &
                "tdz_before,tdz_after,dtdz,rel_t,sdz_before,sdz_after,dsdz,rel_s"
            ca_evt_header = .true.
        else
            open (ca_diag_unit, file=trim(run_csv_dir)//'/convective_guard_events.csv', &
                  position='append')
        end if
        write (ca_diag_unit, '(I4,A,I3,A,I4,A,I4,A,I3,A,I5,A,I8,A,I3,A,ES12.4,'// &
               'A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5)') &
            day, ',', step, ',', i, ',', j, ',', ki, ',', iter_count, ',', nmix, ',', &
            k_problem, ',', resid_inv, ',', &
            tdz_before, ',', tdz_after, ',', dtdz, ',', rel_t, ',', &
            sdz_before, ',', sdz_after, ',', dsdz, ',', rel_s
        close (ca_diag_unit)
        ca_evt_written = ca_evt_written + 1
    end subroutine ca_log_guard_event

    ! ==========================================================================
    ! ca_probe_inversions: диагностика всего поля (этап 4.3, ТОЛЬКО чтение).
    ! Сканирует текущие T2/S2 и считает: число активных колонок, число колонок
    ! хотя бы с одной плотностной инверсией > eps, максимальную инверсию и её
    ! координаты, гистограмму глубин проблемных интерфейсов. Ничего не меняет.
    ! Результат выводится строкой на stdout для сопоставления с журналом событий.
    ! ==========================================================================
    subroutine ca_probe_inversions(tag, day, step)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: day, step
        integer :: i, j, k, ki, n_cols, n_inv, k_max
        real :: ro_k, ro_k1, inv, inv_max
        integer :: hist(ks)
        logical :: col_inv

        n_cols = 0
        n_inv = 0
        inv_max = 0.0
        k_max = 0
        hist(:) = 0

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                n_cols = n_cols + 1
                col_inv = .false.
                do k = 1, ki - 1
                    ro_k = density_anomaly(t2(i, j, k), s2(i, j, k))
                    ro_k1 = density_anomaly(t2(i, j, k + 1), s2(i, j, k + 1))
                    inv = ro_k - ro_k1
                    if (inv .gt. eps_density) then
                        col_inv = .true.
                        if (inv .gt. inv_max) then
                            inv_max = inv
                            k_max = k
                        end if
                        hist(k) = hist(k) + 1
                    end if
                end do
                if (col_inv) n_inv = n_inv + 1
            end do
        end do

        print '(A,A,A,I4,A,I3,A,I5,A,I5,A,ES12.4,A,I3)', &
            "CA-PROBE [", trim(tag), "] day=", day, " step=", step, &
            " cols=", n_cols, " inv_cols=", n_inv, " max_inv=", inv_max, &
            " k_max=", k_max
        print '(A,18(I7,1X))', "CA-PROBE hist(k)=", hist(1:18)
    end subroutine ca_probe_inversions

    ! ==========================================================================
    ! ca_reset: обнуление диагностических счётчиков (вызывается раз в сутки).
    ! Заголовок CSV (ca_evt_header) сбрасывать нельзя - иначе ежедневная
    ! перезапись файла уничтожит события предыдущих суток. Счётчик ca_evt_written
    ! обнуляется, чтобы каждый день начинать журнал с первых N событий.
    ! ==========================================================================
    subroutine ca_reset()
        ca_total_nmix = 0
        ca_max_iter = 0
        ca_guard_hits = 0
        ca_affected_cols = 0
        ca_evt_written = 0
    end subroutine ca_reset

    ! ==========================================================================
    ! ca_stats: возврат накопленных за сутки счётчиков.
    ! ==========================================================================
    subroutine ca_stats(total_nmix, max_iter, guard_hits, affected_cols)
        integer, intent(out) :: total_nmix, max_iter, guard_hits, affected_cols
        total_nmix = ca_total_nmix
        max_iter = ca_max_iter
        guard_hits = ca_guard_hits
        affected_cols = ca_affected_cols
    end subroutine ca_stats

end module convective_adjustment
