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
    use equation_of_state, only: density_anomaly, density_anomaly_f64
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    private
    public :: conv_adj, convect_column, convect_column_f64, ca_configure, &
              ca_reset, ca_stats, ca_probe_inversions

    ! ========================================================================
    ! STAGE 10.21: селекторы точности convective adjustment (runtime, OFF).
    !
    ! Экспериментальная матрица (см. docs/validation/stage10.21_*):
    !   A0 = полный float32 (legacy), eps 0.9e-7          — базовый вариант.
    !   EXP-A = f64 EOS eval + f64 residual, f32 mixing    — контроль атрибуции.
    !   EXP-C = f64 EOS + f64 residual + f64 mixing        — основной кандидат.
    !   EXP-B = f32 + повышенный порог (1.5e-7 / 2.4e-7)   — f32-альтернатива.
    !   EXP-D = f64 только ВНУТРИ conv_adj; все внешние
    !           потребители RO (eos_diag, writeback) — f32 (гибридный).
    !
    ! Управление — из main.f90 через ca_configure (env STAGE1021_CA_*).
    ! По умолчанию ВСЕ выключатели FALSE, eps_density = 0.9e-7:
    ! поведение conv_adj бит-идентично предыдущим стадиям (legacy).
    ! ========================================================================
    logical, save :: ca_f64_mode = .false.   ! f64 EOS+residual в ядре столбца
    logical, save :: ca_f64_mix = .false.    ! f64 арифметика перемешивания T/S
    logical, save :: ca_f64_scope = .false.  ! scope=all: RO writeback тоже f64
    ! ========================================================================

    ! ========================================================================
    ! ПОРОГ ПЛОТНОСТНОЙ НЕУСТОЙЧИВОСТИ
    ! ========================================================================
    ! eps_density = 0.9e-7 [г/см³] — историческое значение из Nesterov_last.txt.
    !
    ! Физический смысл: если RO(k) - RO(k+1) > eps_density, то более тяжёлая
    ! вода находится выше более лёгкой — неустойчивая стратификация.
    ! Адекватная инверсия для морской воды: ~1e-3..1e-2 г/см³ (это огромно).
    ! 0.9e-7 — предельно малое значение (~1e-7), что ведёт к численным проблемам:
    !   Числовая точность float32: 2^-23 ≈ 1.19e-7 (epsilon для X ∈ [1,2)).
    !   Порог 0.9e-7 < 2^-23, поэтому RO(k)==RO(k+1) требует точного равенства
    !   с точностью до 1 ULP (unit in the last place).
    !   Результат: convective adjustment может не сходиться за конечное число итераций.
    !   Решение: защитный предел iter_count > 1000 (Stage 4.3).
    ! Stage 10.21: параметр стал runtime (save), значение по умолчанию НЕ
    ! менялось (0.9e-7). Переопределение — только через ca_configure
    ! (env STAGE1021_CA_EPS) для контролируемых экспериментов EXP-B.
    ! Исторический запрет сохраняется для production-значения.
    real, save :: eps_density = 0.9e-7

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
    ! ca_configure: настройка режимов точности convective adjustment (Stage 10.21).
    !
    ! Вызывается из main.f90 в блоке инициализации ДО первого conv_adj.
    ! По умолчанию (без вызова) все f64-выключатели FALSE и eps_density = 0.9e-7
    ! — поведение бит-идентично предыдущим стадиям.
    !
    ! Вход:
    !   f64_mode  — включать f64 EOS+residual в ядре convect_column_f64 (EXP-A/C/D).
    !   f64_mix   — f64 арифметика перемешивания T/S (EXP-C); при FALSE —
    !               перемешивание остаётся float32 как в legacy (EXP-A атрибуция).
    !   f64_scope — scope=all (EXP-C): RO writeback из conv_adj тоже f64;
    !               при FALSE (EXP-D) writeback RO остаётся float32,
    !               как и все внешние потребители.
    !   eps_value — порог плотностной неустойчивости [г/см³] (EXP-B).
    !               Значение по умолчанию 0.9e-7 — историческое, НЕ менять.
    ! ==========================================================================
    subroutine ca_configure(f64_mode, f64_mix, f64_scope, eps_value)
        logical, intent(in) :: f64_mode, f64_mix, f64_scope
        real, intent(in) :: eps_value
        ca_f64_mode = f64_mode
        ca_f64_mix = f64_mix
        ca_f64_scope = f64_scope
        eps_density = eps_value
    end subroutine ca_configure

    ! ==========================================================================
    ! convect_column: ядро convective adjustment для ОДНОГО столбца.
    !
    ! Алгоритм (исторический, Coupl1.f90:818-855):
    !   1. Вычислить RO(k) = density_anomaly(T(k), S(k)) для всех уровней.
    !   2. Сканировать столбец снизу вверх (k=1..ki-1):
    !      Если RO(k) - RO(k+1) > eps_density (инверсия):
    !        a) Объёмно-взвешенное осреднение:
    !           T(k) = T(k1) = [T(k)·DZ1(k) + T(k1)·DZ1(k+1)] / [DZ1(k)+DZ1(k+1)]
    !           S(k) = S(k1) = аналогично
    !           (сохранение интегралов ∫T·DZ1 и ∫S·DZ1 — закон сохранения тепла/соли)
    !        b) Пересчитать RO(k) = RO(k1) = density_anomaly(новое T, S).
    !   3. Повторять шаг 2, пока за проход было хотя бы одно перемешивание.
    !   4. Защита: iter_count > 1000 → выход (Stage 4.3).
    !
    ! Вход:    cdz1(:) — толщины полуслоёв DZ1 [см], ki — число уровней столбца.
    ! Вход/выход: ct(:), cs(:) — температура [°C] и соленость [массовая доля].
    ! Выход:   nmix — суммарное число выполненных перемешиваний.
    ! Опционально: o_iter_count, o_guard_hit, o_k_problem, o_resid_inv
    !   — диагностические выходы этапа 4.3 (не влияют на алгоритм).
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

        ! Начальная инициализация выходов
        nmix = 0
        if (present(o_iter_count)) o_iter_count = 0
        if (present(o_guard_hit)) o_guard_hit = .false.
        if (present(o_k_problem)) o_k_problem = 0
        if (present(o_resid_inv)) o_resid_inv = 0.0
        if (ki .le. 0) return  ! Пустой столбец (суша)

        ! Шаг 1: Вычисление плотности до перемешивания [г/см³].
        do k = 1, ki
            cr(k) = density_anomaly(ct(k), cs(k))
        end do

        if (ki .eq. 1) return  ! Один уровень — перемешивать нечего

        ! Шаг 2-4: Внешний проход — повторяется, пока было хотя бы одно перемешивание.
        ! Это итерационный метод (fixed-point iteration), который должен сходиться
        ! за ~20 итераций в нормальных условиях.
        iter_count = 0
        do
            iter_count = iter_count + 1
            dzz = cdz1(1)     ! Толщина полуслоя текущего уровня [см]
            ki2 = ki - 1      ! Последний интерфейс (k, k+1), k+1 = ki
            a1 = 0            ! Счётчик перемешиваний в текущем проходе
            do k = 1, ki2
                k1 = k + 1
                dzz1 = cdz1(k1)        ! Толщина полуслоя уровня k+1 [см]
                dz1z = dzz + dzz1       ! Суммарная толщина полуслоёв [см]
                a = cr(k) - cr(k1)      ! Плотностная инверсия [г/см³]
                if (a .le. eps_density) then
                    dzz = dzz1  ! Нет инверсии — переходим к следующему интерфейсу
                    cycle
                end if
                a1 = a1 + 1
                ! Объёмно-взвешенное осреднение T и S (закон сохранения).
                ! Пропорция весов: DZ1(k) : DZ1(k+1) — объёмы полуслоёв.
                ct(k) = (ct(k)*dzz + ct(k1)*dzz1)/dz1z
                cs(k) = (cs(k)*dzz + cs(k1)*dzz1)/dz1z
                ct(k1) = ct(k)  ! Оба уровня получают одинаковые T и S
                cs(k1) = cs(k)
                ! Пересчёт плотности перемешанных уровней.
                cr(k) = density_anomaly(ct(k), cs(k))
                cr(k1) = cr(k)
                dzz = dzz1
            end do
            nmix = nmix + a1          ! Накопление общего числа перемешиваний
            if (a1 .eq. 0) exit      ! Фиксированная точка достигнута
            ! Защита от бесконечного цикла: исторический алгоритм должен
            ! сходиться за ~20 итераций. >1000 = баг/несходимость (Stage 4.3).
            if (iter_count .gt. 1000) then
                if (present(o_guard_hit)) o_guard_hit = .true.
                exit
            end if
        end do
        if (present(o_iter_count)) o_iter_count = iter_count

        ! Остаточная инверсия на выходе: max[RO(k) - RO(k+1)] по интерфейсам.
        ! Диагностика этапа 4.3 — НЕ влияет на алгоритм.
        ! Если guard_hit = .true., то остаточная инверсия > eps_density ожидаема
        ! (столбец не сошёлся за 1000 итераций из-за float32 квантизации EOS).
        if (present(o_k_problem) .or. present(o_resid_inv)) then
            rmax_inv = -huge(1.0)
            resid = 0.0
            do k = 1, ki - 1
                resid = cr(k) - cr(k + 1)  ! Инверсия на интерфейсе k/k+1
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
    ! convect_column_f64: ядро convective adjustment для ОДНОГО столбца в
    ! double precision (Stage 10.21, варианты EXP-A/C/D).
    !
    ! Алгоритм ИДЕНТИЧЕН convect_column (исторический, Coupl1.f90:818-855):
    !   1. RO(k) = density_anomaly_f64(T(k), S(k)) для всех уровней.
    !   2. Сканирование снизу вверх (k=1..ki-1): если RO(k)-RO(k+1) > eps_density
    !      — объёмно-взвешенное осреднение T/S, пересчёт RO перемешанных уровней.
    !   3. Повтор до фиксированной точки (ни одного перемешивания за проход).
    !   4. Защита: iter_count > 1000 → выход (как в legacy, Stage 4.3).
    !
    ! Отличия от legacy convect_column (runtime-переключатели ca_f64_*):
    !   - RO вычисляется плотностью density_anomaly_f64 (real64) — устраняется
    !     float32-квантизация 2^-23 ≈ 1.19e-7, из-за которой остаточная инверсия
    !     не опускалась ниже порога 0.9e-7 (см. docs/validation/stage10.21_*).
    !   - Если ca_f64_mix = .true. (EXP-C), арифметика перемешивания T/S также
    !     в real64; иначе (EXP-A) — точно legacy float32 (контроль атрибуции).
    !   - Перемешивание по-прежнему сохраняет интегралы Σ T·DZ1, Σ S·DZ1
    !     (объёмное взвешивание по толщинам полуслоёв) — законы сохранения.
    !
    ! Вход:    cdz1(:) — толщины полуслоёв DZ1 [см], ki — число уровней столбца.
    ! Вход/выход: ct(:), cs(:) — температура [°C] и соленость [массовая доля].
    ! Выход:   nmix — суммарное число выполненных перемешиваний.
    ! Опционально: o_iter_count, o_guard_hit, o_k_problem, o_resid_inv
    !   — те же диагностические выходы, что и в convect_column (этап 4.3).
    ! ==========================================================================
    subroutine convect_column_f64(ct, cs, cdz1, ki, nmix, o_iter_count, o_guard_hit, &
                                  o_k_problem, o_resid_inv)
        real, intent(inout) :: ct(:), cs(:)
        real, intent(in) :: cdz1(:)
        integer, intent(in) :: ki
        integer, intent(out) :: nmix
        integer, intent(out), optional :: o_iter_count
        logical, intent(out), optional :: o_guard_hit
        integer, intent(out), optional :: o_k_problem
        real, intent(out), optional :: o_resid_inv
        real(real64) :: cr(ks)
        real(real64) :: dzz, dzz1, dz1z, a
        real(real64) :: resid, rmax_inv
        real(real64) :: t_new, s_new
        integer :: k, k1, ki2, a1
        integer :: iter_count

        ! Начальная инициализация выходов
        nmix = 0
        if (present(o_iter_count)) o_iter_count = 0
        if (present(o_guard_hit)) o_guard_hit = .false.
        if (present(o_k_problem)) o_k_problem = 0
        if (present(o_resid_inv)) o_resid_inv = 0.0
        if (ki .le. 0) return  ! Пустой столбец (суша)

        ! Шаг 1: Вычисление плотности в double precision до перемешивания.
        do k = 1, ki
            cr(k) = density_anomaly_f64(real(ct(k), real64), real(cs(k), real64))
        end do

        if (ki .eq. 1) return  ! Один уровень — перемешивать нечего

        ! Шаг 2-4: Внешний проход — повторяется, пока было хотя бы одно перемешивание.
        iter_count = 0
        do
            iter_count = iter_count + 1
            dzz = real(cdz1(1), real64)  ! Толщина полуслоя текущего уровня [см]
            ki2 = ki - 1      ! Последний интерфейс (k, k+1), k+1 = ki
            a1 = 0            ! Счётчик перемешиваний в текущем проходе
            do k = 1, ki2
                k1 = k + 1
                dzz1 = real(cdz1(k1), real64)   ! Толщина полуслоя уровня k+1 [см]
                dz1z = dzz + dzz1              ! Суммарная толщина полуслоёв [см]
                a = cr(k) - cr(k1)             ! Плотностная инверсия [г/см³]
                if (a .le. real(eps_density, real64)) then
                    dzz = dzz1  ! Нет инверсии — переходим к следующему интерфейсу
                    cycle
                end if
                a1 = a1 + 1
                ! Объёмно-взвешенное осреднение T и S (закон сохранения).
                if (ca_f64_mix) then
                    ! EXP-C: арифметика осреднения в real64, округление
                    ! к float32 только при записи в ct/cs.
                    t_new = (real(ct(k), real64)*dzz + real(ct(k1), real64)*dzz1)/dz1z
                    s_new = (real(cs(k), real64)*dzz + real(cs(k1), real64)*dzz1)/dz1z
                    ct(k) = real(t_new, kind(1.0))
                    cs(k) = real(s_new, kind(1.0))
                else
                    ! EXP-A: точно legacy float32-арифметика (контроль атрибуции).
                    ct(k) = (ct(k)*real(dzz, kind(1.0)) + &
                             ct(k1)*real(dzz1, kind(1.0)))/real(dz1z, kind(1.0))
                    cs(k) = (cs(k)*real(dzz, kind(1.0)) + &
                             cs(k1)*real(dzz1, kind(1.0)))/real(dz1z, kind(1.0))
                end if
                ct(k1) = ct(k)  ! Оба уровня получают одинаковые T и S
                cs(k1) = cs(k)
                ! Пересчёт плотности перемешанных уровней (f64).
                cr(k) = density_anomaly_f64(real(ct(k), real64), real(cs(k), real64))
                cr(k1) = cr(k)
                dzz = dzz1
            end do
            nmix = nmix + a1          ! Накопление общего числа перемешиваний
            if (a1 .eq. 0) exit      ! Фиксированная точка достигнута
            ! Защита от бесконечного цикла (как в legacy, Stage 4.3).
            if (iter_count .gt. 1000) then
                if (present(o_guard_hit)) o_guard_hit = .true.
                exit
            end if
        end do
        if (present(o_iter_count)) o_iter_count = iter_count

        ! Остаточная инверсия на выходе: max[RO(k) - RO(k+1)] по интерфейсам
        ! (в f64; диагностика этапа 4.3 — НЕ влияет на алгоритм). В f64-пути
        ! сходимость реальна (resid < 0.9e-7 достижимо), поэтому guard_hit
        ! ожидаемо всегда FALSE, а resid_inv — не нулевой, но ниже порога.
        if (present(o_k_problem) .or. present(o_resid_inv)) then
            rmax_inv = -huge(0.0_real64)
            resid = 0.0_real64
            do k = 1, ki - 1
                resid = cr(k) - cr(k + 1)  ! Инверсия на интерфейсе k/k+1
                if (resid .gt. rmax_inv) then
                    rmax_inv = resid
                    k1 = k
                end if
            end do
            if (present(o_k_problem)) then
                if (rmax_inv .gt. real(eps_density, real64)) then
                    o_k_problem = k1
                else
                    o_k_problem = 0
                end if
            end if
            if (present(o_resid_inv)) then
                if (rmax_inv .gt. real(eps_density, real64)) then
                    o_resid_inv = real(rmax_inv, kind(1.0))
                else
                    o_resid_inv = 0.0
                end if
            end if
        end if
    end subroutine convect_column_f64

    ! ==========================================================================
    ! conv_adj: применение convective adjustment ко всем водным колонкам поля.
    !
    ! Для каждой ячейки (i,j) с kt1>0:
    !   1. Копирует T2(i,j,1:ki) и S2(i,j,1:ki) в локальные ct/cs.
    !   2. Вызывает convect_column(ct, cs, dz1, ki, nmix, ...).
    !   3. Записывает результат обратно в T2/S2 и пересчитывает RO.
    !
    ! Не затрагивает уравнения движения — RO в momentum не используется
    ! на этапах 3.1-3.2 ( используется только блок 200 этапа 3.3).
    ! Накапливает диагностические счётчики (ca_total_nmix и т.д.).
    !
    ! Вход (диагностика, опционально): day, step — модельные сутки и
    !   бароклинный шаг III для журнала guard-событий.
    ! ==========================================================================
    subroutine conv_adj(day, step)
        integer, intent(in), optional :: day, step
        integer :: i, j, k, ki, nmix
        integer :: iter_count, k_problem
        logical :: guard_hit
        real :: resid_inv
        real :: ct(ks), cs(ks), cdz1(ks)
        real :: t_before(ks), s_before(ks)

        ! Цикл по всем ячейкам поля (включая ghost, но kt1=0 пропускается)
        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)     ! Число мокрых уровней в столбце (0 = суша)
                if (ki .eq. 0) cycle
                ! Копирование T2/S2 в локальные массивы (convect_column изменяет их)
                do k = 1, ki
                    ct(k) = t2(i, j, k)
                    cs(k) = s2(i, j, k)
                end do
                cdz1(1:ki) = dz1(1:ki)  ! Толщины полуслоёв [см]
                ! Вызов ядра convective adjustment для этого столбца.
                ! Stage 10.21: при ca_f64_mode ядро работает в double precision
                ! (convect_column_f64), иначе — исторический float32 путь
                ! (convect_column, бит-идентичен предыдущим стадиям).
                if (ca_f64_mode) then
                    call convect_column_f64(ct, cs, cdz1, ki, nmix, iter_count, &
                                            guard_hit, k_problem, resid_inv)
                else
                    call convect_column(ct, cs, cdz1, ki, nmix, iter_count, guard_hit, &
                                        k_problem, resid_inv)
                end if
                ! Накопление диагностических счётчиков (этап 4.2)
                ca_total_nmix = ca_total_nmix + nmix
                if (nmix .gt. 0) ca_affected_cols = ca_affected_cols + 1
                if (guard_hit) then
                    ca_guard_hits = ca_guard_hits + 1
                    ! Журналирование guard-события в CSV (ТОЛЬКО диагностика).
                    ! t_before/s_before содержат профиль ДО convect_column,
                    ! ct/cs — после (когда guard сработал, инверсия сохраняется).
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
                ! Запись результата обратно в глобальные массивы
                do k = 1, ki
                    t2(i, j, k) = ct(k)
                    s2(i, j, k) = cs(k)
                    if (ca_f64_mode .and. ca_f64_scope) then
                        ! Stage 10.21 scope=all (EXP-C): RO через f64-плотность —
                        ! единая последовательность вычислений с ядром столбца.
                        ro(i, j, k) = real(density_anomaly_f64( &
                            real(ct(k), real64), real(cs(k), real64)), kind(1.0))
                    else
                        ! Legacy float32 (в т.ч. EXP-D: writeback остаётся f32).
                        ro(i, j, k) = density_anomaly(ct(k), cs(k))  ! Пересчёт RO
                    end if
                end do
            end do
        end do
    end subroutine conv_adj

    ! ==========================================================================
    ! ca_log_guard_event: запись одной строки в convective_guard_events.csv.
    !
    ! Строка содержит:
    !   day, step, i, j — модельные сутки, бароклинный шаг, координаты ячейки.
    !   ki — число мокрых уровней столбца.
    !   iter_count — число итераций (>1000 = guard сработал).
    !   nmix — суммарное число перемешиваний за все итерации.
    !   k_problem — интерфейс с максимальной остаточной инверсией (0 = нет).
    !   resid_inv — величина этой инверсии [г/см³].
    !   tdz_before/tdz_after — интеграл T·DZ1 до/после (для проверки сохранения).
    !   dtdz, rel_t — абсолютная и относительная ошибка сохранения тепла.
    !   sdz_before/sdz_after, dsdz, rel_s — аналогично для соли.
    !
    ! Записывается не более ca_guard_evt_cap=100 событий в сутки (ограничение
    ! объёма вывода). Полные профили восстанавливаются из NetCDF суточных срезов.
    ! ТОЛЬКО диагностика — не влияет на физику.
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

        ! Расчёт интегралов T·DZ1 и S·DZ1 до/после convect_column
        ! для проверки сохранения тепла и соли (законы сохранения).
        tdz_before = 0.0; tdz_after = 0.0
        sdz_before = 0.0; sdz_after = 0.0
        do k = 1, ki
            tdz_before = tdz_before + t_before(k)*cdz1(k)  ! [°C·см]
            sdz_before = sdz_before + s_before(k)*cdz1(k)  ! [доли·см]
            tdz_after = tdz_after + t_after(k)*cdz1(k)
            sdz_after = sdz_after + s_after(k)*cdz1(k)
        end do
        dtdz = tdz_after - tdz_before  ! Абсолютная ошибка сохранения тепла [°C·см]
        dsdz = sdz_after - sdz_before  ! Абсолютная ошибка сохранения соли [доли·см]
        ! Относительная ошибка (безразм.), защищена от деления на ноль
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
               'A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,A,ES13.5,'// &
               'A,ES13.5)') &
            day, ',', step, ',', i, ',', j, ',', ki, ',', iter_count, ',', nmix, ',', &
            k_problem, ',', resid_inv, ',', &
            tdz_before, ',', tdz_after, ',', dtdz, ',', rel_t, ',', &
            sdz_before, ',', sdz_after, ',', dsdz, ',', rel_s
        close (ca_diag_unit)
        ca_evt_written = ca_evt_written + 1
    end subroutine ca_log_guard_event

    ! ==========================================================================
    ! ca_probe_inversions: диагностика всего поля (этап 4.3, ТОЛЬКО чтение).
    !
    ! Сканирует текущие T2/S2 и считает:
    !   n_cols — число активных водных столбцов (kt1 > 0).
    !   n_inv — число столбцов хотя бы с одной плотностной инверсией > eps.
    !   inv_max — максимальная инверсия [г/см³] и её уровень k_max.
    !   hist(k) — гистограмма: сколько интерфейсов с инверсией на уровне k.
    ! Ничего не меняет — чисто диагностический вызов.
    ! Вызывается в main.f90 как точка A (после адвекции) и точка D (после conv_adj).
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
                    if (ca_f64_mode .and. ca_f64_scope) then
                        ! Stage 10.21 scope=all (EXP-C): плотность через f64,
                        ! чтобы диагностика совпадала с фактическим полем RO.
                        ro_k = real(density_anomaly_f64( &
                            real(t2(i, j, k), real64), real(s2(i, j, k), real64)), kind(1.0))
                        ro_k1 = real(density_anomaly_f64( &
                            real(t2(i, j, k + 1), real64), &
                            real(s2(i, j, k + 1), real64)), kind(1.0))
                    else
                        ro_k = density_anomaly(t2(i, j, k), s2(i, j, k))
                        ro_k1 = density_anomaly(t2(i, j, k + 1), s2(i, j, k + 1))
                    end if
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
    ! ca_reset: обнуление суточных счётчиков (вызывается раз в сутки в main.f90).
    ! Сбрасывает: ca_total_nmix, ca_max_iter, ca_guard_hits, ca_affected_cols,
    !   ca_evt_written.
    ! НЕ сбрасывает ca_evt_header (заголовок CSV) — иначе ежедневная перезапись
    ! файла уничтожит события предыдущих суток.
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
    !   total_nmix — суммарное число перемешиваний за все столбцы за сутки.
    !   max_iter — максимальное число итераций в одном столбце.
    !   guard_hits — число столбцов, где iter_count > 1000.
    !   affected_cols — число столбцов, где было хотя бы одно перемешивание.
    ! ==========================================================================
    subroutine ca_stats(total_nmix, max_iter, guard_hits, affected_cols)
        integer, intent(out) :: total_nmix, max_iter, guard_hits, affected_cols
        total_nmix = ca_total_nmix
        max_iter = ca_max_iter
        guard_hits = ca_guard_hits
        affected_cols = ca_affected_cols
    end subroutine ca_stats

end module convective_adjustment
