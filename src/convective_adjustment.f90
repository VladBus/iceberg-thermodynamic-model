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
    public :: conv_adj, convect_column, ca_reset, ca_stats

    ! Порог плотностной инверсии [г/см3] - историческое значение.
    real, parameter :: eps_density = 0.9e-7

    ! Диагностические счётчики convective adjustment (этап 4.2, мониторинг).
    ! НЕ меняют алгоритм перемешивания - только фиксируют статистику для отчёта.
    integer, save :: ca_total_nmix = 0      ! суммарное число перемешиваний
    integer, save :: ca_max_iter = 0        ! максимальное число итераций в столбце
    integer, save :: ca_guard_hits = 0      ! число столбцов с iter_count > 1000
    integer, save :: ca_affected_cols = 0   ! число столбцов, где было перемешивание

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
    !              Эти выходы используются только для мониторинга (этап 4.2)
    !              и не влияют на алгоритм.
    ! ==========================================================================
    subroutine convect_column(ct, cs, cdz1, ki, nmix, o_iter_count, o_guard_hit)
        real, intent(inout) :: ct(:), cs(:)
        real, intent(in) :: cdz1(:)
        integer, intent(in) :: ki
        integer, intent(out) :: nmix
        integer, intent(out), optional :: o_iter_count
        logical, intent(out), optional :: o_guard_hit
        real :: cr(ks)
        real :: dzz, dzz1, dz1z, a
        integer :: k, k1, ki2, a1
        integer :: iter_count

        nmix = 0
        if (present(o_iter_count)) o_iter_count = 0
        if (present(o_guard_hit)) o_guard_hit = .false.
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
    end subroutine convect_column

    ! ==========================================================================
    ! conv_adj: применение convective adjustment ко всем водным колонкам поля.
    ! Обновляет T2/S2 и пересчитывает RO. Не затрагивает уравнения движения
    ! (RO в momentum не используется на этапах 3.1-3.2).
    ! ==========================================================================
    subroutine conv_adj()
        integer :: i, j, k, ki, nmix
        integer :: iter_count
        logical :: guard_hit
        real :: ct(ks), cs(ks), cdz1(ks)

        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    ct(k) = t2(i, j, k)
                    cs(k) = s2(i, j, k)
                end do
                cdz1(1:ki) = dz1(1:ki)
                call convect_column(ct, cs, cdz1, ki, nmix, iter_count, guard_hit)
                ca_total_nmix = ca_total_nmix + nmix
                if (nmix .gt. 0) ca_affected_cols = ca_affected_cols + 1
                if (guard_hit) ca_guard_hits = ca_guard_hits + 1
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
    ! ca_reset: обнуление диагностических счётчиков (вызывается раз в сутки).
    ! ==========================================================================
    subroutine ca_reset()
        ca_total_nmix = 0
        ca_max_iter = 0
        ca_guard_hits = 0
        ca_affected_cols = 0
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
