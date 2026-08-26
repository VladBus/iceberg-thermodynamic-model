! ==============================================================================
! Диагностическая тестовая программа (этап 4.3b): проверка IEEE-754 / точности
! float32 в историческом уравнении состояния Эккарта.
!
! НЕ является частью физики модели. Только диагностика:
!   1. Фактический REAL kind / storage / precision / range (без предположений
!      по тексту исходника).
!   2. Точное воспроизведение производственной формулы
!      RO = 1/(0.698 + aa/bb) - 1.02 (те же kinds, тот же порядок операций).
!   3. Spacing-тест: spacing(X), spacing(RO), nearest для представительных
!      T/S; сравнение с 2^-23, 2^-24, 2^-31, 2^-32.
!   4. Bit-level тест через TRANSFER: соседние представимые X и RO,
!      разности между соседними RO.
!   5. Сравнение float32 (производственный REAL) vs float64 (диагностика
!      только): RO32/RO64 и residual inversions.
!   6. Проверка достижимости порога 0.9e-7 в float32.
!
! Физика/код не изменяются; это отдельная standalone-программа.
! ==============================================================================

program eos_precision_test
    implicit none

    integer, parameter :: sp = kind(1.0)          ! производственный REAL
    integer, parameter :: dp = kind(1.0d0)        ! диагностический REAL64
    integer :: i
    real(sp) :: t, s
    real(sp) :: x, ro
    real(sp) :: aa, bb
    real(sp) :: x_next, ro_next
    real(sp) :: spacing_x, spacing_ro
    real(dp) :: aa64, bb64, x64, ro64
    integer(sp) :: ix, iro, ixn, iron
    integer :: n_fail

    n_fail = 0

    print *, "======================================================"
    print *, "  Stage 4.3b: IEEE-754 EOS precision verification"
    print *, "======================================================"

    ! --- 1. REAL kinds ---
    ! Определяем фактическую точность и диапазон производственного типа REAL
    print *, "--- 1. REAL kind / storage ---"
    print '(A,I2,A,I4,A)', 'default REAL: kind=', sp, &
        ' storage_size=', storage_size(1.0_sp), ' bits'
    print '(A,I2,A)', 'REAL64     : kind=', dp
    print '(A,I2)', 'precision(default real)=', precision(1.0_sp)
    print '(A,I3)', 'range(default real)     =', range(1.0_sp)
    print '(A,F10.6)', 'epsilon(default real)   =', epsilon(1.0_sp)
    print '(A,ES11.4)', 'tiny(default real)      =', tiny(1.0_sp)
    print '(A,ES11.4)', 'huge(default real)      =', huge(1.0_sp)

    ! Порог из convective_adjustment.f90 (исторический).
    print '(A,ES11.4)', 'threshold eps_density (0.9e-7 real32) = ', &
        0.9e-7_sp

    ! --- 2. Reproduction of production EOS for representative T/S ---
    ! Точное воспроизведение формулы RO = 1/(0.698+aa/bb) - 1.02 в float32.
    ! Коэффициенты: 1779.5, 11.25, 0.0745, 3800.0, 10.0, 5891.0, 3000.0, 38.0, 0.375
    ! Промежуточный X = 1/(0.698+aa/bb) ∈ [~0.998, ~1.006] — диапазон для типовых T/S.
    ! spacing(X) ≈ 2^-23 ≈ 1.19e-7 — расстояние между соседними representable float32.
    print *, "--- 2. EOS reproduction (production real32 formula) ---"
    do i = 1, 4
        select case (i)
        case (1); t = 15.0_sp; s = 0.033_sp
        case (2); t = 10.0_sp; s = 0.034_sp
        case (3); t = 0.0_sp; s = 0.033_sp
        case (4); t = 25.0_sp; s = 0.035_sp
        end select
        aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
        bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
        x = 1.0/(0.698 + aa/bb)
        ro = x - 1.02

        ! Spacing of the intermediate X and of the stored RO.
        spacing_x = spacing(x)
        spacing_ro = spacing(ro)
        x_next = nearest(x, +1.0_sp)
        ro_next = nearest(ro, +1.0_sp)

        print '(A,I1,A,F5.1,A,F6.3,A)', 'T/S case ', i, ': T=', t, ' S=', s
        print '(A,ES16.9,A,ES16.9)', '  aa     = ', aa, '  bb     = ', bb
        print '(A,ES16.9,A,ES16.9)', '  X      = ', x, '  RO     = ', ro
        print '(A,ES11.4,A,ES11.4)', '  spacing(X) = ', spacing_x, &
            '  spacing(RO) = ', spacing_ro
        print '(A,ES11.4,A,ES11.4)', '  nearest(X,+1) = ', x_next, &
            '  nearest(RO,+1) = ', ro_next
        print '(A,ES11.4,A,ES11.4)', '  nearest-X - X  = ', x_next - x, &
            '  nearest-RO - RO = ', ro_next - ro
    end do

    ! --- 3. Spacing vs 2^-23 / 2^-24 / 2^-31 / 2^-32 ---
    print *, "--- 3. Spacing comparison with powers of two ---"
    do i = 1, 4
        select case (i)
        case (1); t = 15.0_sp; s = 0.033_sp
        case (2); t = 10.0_sp; s = 0.034_sp
        case (3); t = 0.0_sp; s = 0.033_sp
        case (4); t = 25.0_sp; s = 0.035_sp
        end select
        aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
        bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
        x = 1.0/(0.698 + aa/bb)
        ro = x - 1.02
        spacing_x = spacing(x)
        spacing_ro = spacing(ro)
        print '(A,I1,A,F5.1,A,F6.3,A)', 'T/S case ', i, ': T=', t, ' S=', s
        print '(A,ES11.4,A,ES11.4)', '  spacing(X)  = ', spacing_x, &
            '  spacing(RO) = ', spacing_ro
        print '(A,ES11.4,A,ES11.4)', '  2^-23 = ', 2.0_sp**(-23), &
            '  2^-24 = ', 2.0_sp**(-24)
        print '(A,ES11.4,A,ES11.4)', '  2^-31 = ', 2.0_sp**(-31), &
            '  2^-32 = ', 2.0_sp**(-32)
    end do

    ! --- 4. Bit-level via TRANSFER ---
    print *, "--- 4. Bit-level (TRANSFER to integer) ---"
    do i = 1, 4
        select case (i)
        case (1); t = 15.0_sp; s = 0.033_sp
        case (2); t = 10.0_sp; s = 0.034_sp
        case (3); t = 0.0_sp; s = 0.033_sp
        case (4); t = 25.0_sp; s = 0.035_sp
        end select
        aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
        bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
        x = 1.0/(0.698 + aa/bb)
        ro = x - 1.02
        x_next = nearest(x, +1.0_sp)
        ro_next = nearest(ro, +1.0_sp)
        ix = transfer(x, 1_sp)
        ixn = transfer(x_next, 1_sp)
        iro = transfer(ro, 1_sp)
        iron = transfer(ro_next, 1_sp)
        print '(A,I1,A,F5.1,A,F6.3)', 'T/S case ', i, ': T=', t, ' S=', s
        print '(A,Z8.8,A,Z8.8)', '  X   bits = 0x', ix, '   X+1 bits = 0x', ixn
        print '(A,Z8.8,A,Z8.8)', '  RO  bits = 0x', iro, '  RO+1 bits = 0x', iron
        print '(A,I10,A,I10)', '  X ulps   = ', ixn - ix, &
            '  RO ulps  = ', iron - iro
        print '(A,ES11.4)', '  RO+1 - RO (adjacent RO difference) = ', &
            ro_next - ro
    end do

    ! --- 5. float32 vs float64 (diagnostic ONLY) ---
    print *, "--- 5. float32 vs float64 EOS (diagnostic) ---"
    do i = 1, 4
        select case (i)
        case (1); t = 15.0_sp; s = 0.033_sp
        case (2); t = 10.0_sp; s = 0.034_sp
        case (3); t = 0.0_sp; s = 0.033_sp
        case (4); t = 25.0_sp; s = 0.035_sp
        end select
        aa64 = 1779.5d0 + (11.25d0 - 0.0745d0*dble(t))*dble(t) &
               - (3800.0d0 + 10.0d0*dble(t))*dble(s)
        bb64 = 5891.0d0 + 3000.0d0*dble(s) + (38.0d0 - 0.375d0*dble(t))*dble(t)
        x64 = 1.0d0/(0.698d0 + aa64/bb64)
        ro64 = x64 - 1.02d0
        aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
        bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
        x = 1.0/(0.698 + aa/bb)
        ro = x - 1.02
        print '(A,I1,A,F5.1,A,F6.3)', 'T/S case ', i, ': T=', t, ' S=', s
        print '(A,ES18.10,A,ES18.10)', '  X64   = ', x64, '  X32   = ', x
        print '(A,ES18.10,A,ES18.10)', '  RO64  = ', ro64, '  RO32  = ', ro
        print '(A,ES11.4)', '  RO64 - RO32 = ', ro64 - ro
    end do

    ! --- 6. Threshold reachability in float32 ---
    ! Проверяет, достижим ли порог eps_density = 0.9e-7 в float32.
    ! Гипотеза Stage 4.3: порог 0.9e-7 < 2^-23 (≈1.19e-7), поэтому
    ! конечная разность RO не может попасть между 0 и порогом,
    ! и convective adjustment永远不会 "остановиться" на ненулевой, но нижепороговой разности.
    print *, "--- 6. Threshold 0.9e-7 reachability ---"
    ! Минимальная ненулевая разность двух RO, которую можно получить из
    ! двух отличающихся наборов T/S (поиск перебором по физической сетке).
    call threshold_reachability(n_fail)

    ! --- 7. Dense enumeration: min nonzero |RO32 diff| over the physical grid ---
    print *, "--- 7. Dense enumeration over physical T/S grid ---"
    call dense_enumeration(n_fail)

    ! --- 8. float64 reachability: is 0.9e-7 reachable in REAL64? ---
    print *, "--- 8. Threshold reachability in REAL64 (diagnostic only) ---"
    call fp64_reachability(n_fail)

    print *, "======================================================"
    if (n_fail .eq. 0) then
        print *, "SUCCESS: All EOS precision diagnostic checks PASSED cleanly!"
        stop 0
    else
        print *, "FAILURE: EOS precision diagnostic found ", n_fail, " problem(s)"
        stop 1
    end if

contains

    ! Перебор физической сетки T/S: ищем минимальную положительную разность
    ! двух РАЗНЫХ RO32 (несмежных), и проверяем достижим ли порог 0.9e-7.
    ! Это прямо отвечает на вопрос: может ли float32 произвести residual
    ! inversion МЕЖДУ 0 и 0.9e-7 (что позволило бы конвергенции остановиться
    ! при НЕНУЛЕВОЙ, но нижепороговой разности).
    subroutine threshold_reachability(nfail_arg)
        integer, intent(inout) :: nfail_arg
        integer :: istep
        real(sp) :: t1x, s1x, ro1x
        real(sp) :: t2x, s2x, ro2x
        real(sp) :: d, dmin
        real(sp), parameter :: thresh = 0.9e-7_sp
        logical :: nonzero_below_thresh

        dmin = huge(1.0_sp)
        nonzero_below_thresh = .false.

        ! Сканируем соседние значения T (шаг 0.01°C) при фиксированной S.
        ! Физический диапазон модели: T 0..25, S 0.033..0.035.
        do istep = 0, 2500
            t1x = 0.0_sp + real(istep, sp)*0.01_sp
            t2x = t1x + 0.01_sp
            s1x = 0.034_sp
            s2x = 0.034_sp
            ro1x = eos32(t1x, s1x)
            ro2x = eos32(t2x, s2x)
            d = abs(ro1x - ro2x)
            if (d .gt. 0.0_sp .and. d .lt. dmin) dmin = d
            if (d .gt. 0.0_sp .and. d .lt. thresh) nonzero_below_thresh = .true.
        end do

        print '(A,ES11.4)', '  min positive |RO32(t) - RO32(t+0.01)| = ', dmin
        print '(A,ES11.4)', '  threshold 0.9e-7 = ', thresh
        print '(A,L1)', '  nonzero RO32 difference below threshold found: ', &
            nonzero_below_thresh
        print '(A,ES11.4)', '  2^-23 = ', 2.0_sp**(-23)

        if (nonzero_below_thresh) then
            print *, "ERROR: a nonzero float32 RO difference below 0.9e-7 exists"
            nfail_arg = nfail_arg + 1
        else if (dmin .ge. 2.0_sp**(-23)) then
            print *, "OK: min nonzero RO32 diff >= 2^-23 (grid spacing)"
        else
            print *, "WARNING: min nonzero RO32 diff < 2^-23"
        end if
    end subroutine threshold_reachability

    ! Точная копия производственной формулы (equation_of_state.f90:25-32).
    pure function eos32(tv, sv) result(ro_out)
        real(sp), intent(in) :: tv, sv
        real(sp) :: aa32, bb32, ro_out
        aa32 = 1779.5 + (11.25 - 0.0745*tv)*tv - (3800.0 + 10.0*tv)*sv
        bb32 = 5891.0 + 3000.0*sv + (38.0 - 0.375*tv)*tv
        ro_out = 1.0/(0.698 + aa32/bb32) - 1.02
    end function eos32

    ! Полный перебор представимых RO32 по физической сетке T/S:
    ! собираем ВСЕ достижимые значения RO, сортируем их и находим
    ! минимальную ненулевую разность между двумя разными значениями.
    ! Это доказывает/опровергает утверждение "порог 0.9e-7 недостижим":
    ! если min nonzero |ROa - ROb| > 0.9e-7, порог математически
    ! недостижим; если существует пара с 0 < |ROa-ROb| <= 0.9e-7 -
    ! порог достижим и гипотеза Stage 4.3 опровергнута.
    subroutine dense_enumeration(nfail_arg)
        integer, intent(inout) :: nfail_arg
        integer, parameter :: nscan_t = 2801   ! T: -2..26 шаг 0.01
        integer, parameter :: nscan_s = 21     ! S: 0.033..0.035 шаг 0.0001
        integer, parameter :: nmax = nscan_t*nscan_s
        real(sp) :: vals(nmax)
        integer :: nt, ns, idx, nval
        real(sp) :: t_d, s_d, ro_d
        real(sp) :: dmin, d
        real(sp), parameter :: thresh = 0.9e-7_sp
        logical :: nonzero_below_thresh
        real(sp) :: x_min, x_max, x_loc

        idx = 0
        x_min = huge(1.0_sp)
        x_max = -huge(1.0_sp)
        do nt = 0, nscan_t - 1
            t_d = -2.0_sp + real(nt, sp)*0.01_sp
            do ns = 0, nscan_s - 1
                s_d = 0.033_sp + real(ns, sp)*0.0001_sp
                ro_d = eos32(t_d, s_d)
                ! Также отслеживаем диапазон промежуточного X.
                call eos_x(t_d, s_d, x_loc)
                x_min = min(x_min, x_loc)
                x_max = max(x_max, x_loc)
                idx = idx + 1
                vals(idx) = ro_d
            end do
        end do
        nval = idx

        call sort32(vals, nval)

        dmin = huge(1.0_sp)
        nonzero_below_thresh = .false.
        do idx = 2, nval
            d = vals(idx) - vals(idx - 1)
            if (d .gt. 0.0_sp) then
                dmin = min(dmin, d)
                if (d .le. thresh) nonzero_below_thresh = .true.
            end if
        end do

        print '(A,I7)', '  distinct RO32 values enumerated: ', nval
        print '(A,ES12.5,A,ES12.5)', '  X range over grid: [', x_min, ', ', x_max, ']'
        print '(A,ES11.4)', '  min nonzero |ROa - ROb| (sorted grid) = ', dmin
        print '(A,ES11.4)', '  threshold 0.9e-7 = ', thresh
        print '(A,ES11.4)', '  2^-23 = ', 2.0_sp**(-23)
        print '(A,L1)', '  exists pair with 0 < diff <= 0.9e-7: ', &
            nonzero_below_thresh

        if (nonzero_below_thresh) then
            print *, "ERROR: threshold 0.9e-7 IS reachable in float32"
            nfail_arg = nfail_arg + 1
        else if (dmin .ge. 2.0_sp**(-23)) then
            print *, "OK: min nonzero RO32 diff >= 2^-23, threshold unreachable"
        else
            print *, "WARNING: min nonzero RO32 diff < 2^-23"
        end if
    end subroutine dense_enumeration

    ! Промежуточный X = 1/(0.698 + aa/bb) (та же формула, тот же kind).
    pure subroutine eos_x(tv, sv, xout)
        real(sp), intent(in) :: tv, sv
        real(sp), intent(out) :: xout
        real(sp) :: aa_x, bb_x
        aa_x = 1779.5 + (11.25 - 0.0745*tv)*tv - (3800.0 + 10.0*tv)*sv
        bb_x = 5891.0 + 3000.0*sv + (38.0 - 0.375*tv)*tv
        xout = 1.0/(0.698 + aa_x/bb_x)
    end subroutine eos_x

    ! Точная копия производственной формулы, но в REAL64 (ТОЛЬКО диагностика).
    ! Проверяет: достижим ли порог 0.9e-7 в двойной точности. Если да -
    ! это прямо подтверждает, что недостижимость порога - свойство float32.
    pure function eos64(tv, sv) result(ro64_out)
        real(dp), intent(in) :: tv, sv
        real(dp) :: aa64f, bb64f, ro64_out
        aa64f = 1779.5d0 + (11.25d0 - 0.0745d0*tv)*tv - (3800.0d0 + 10.0d0*tv)*sv
        bb64f = 5891.0d0 + 3000.0d0*sv + (38.0d0 - 0.375d0*tv)*tv
        ro64_out = 1.0d0/(0.698d0 + aa64f/bb64f) - 1.02d0
    end function eos64

    subroutine fp64_reachability(nfail_arg)
        integer, intent(inout) :: nfail_arg
        integer, parameter :: nscan_t = 2801   ! T: -2..26 шаг 0.01
        integer, parameter :: nscan_s = 21     ! S: 0.033..0.035 шаг 0.0001
        integer, parameter :: nmax = nscan_t*nscan_s
        real(dp) :: vals(nmax)
        integer :: nt, ns, idx, nval
        real(dp) :: t64, s64, ro64v
        real(dp) :: dmin, d
        real(dp), parameter :: thresh = 0.9d-7
        logical :: nonzero_below_thresh

        idx = 0
        do nt = 0, nscan_t - 1
            t64 = -2.0d0 + real(nt, dp)*0.01d0
            do ns = 0, nscan_s - 1
                s64 = 0.033d0 + real(ns, dp)*0.0001d0
                ro64v = eos64(t64, s64)
                idx = idx + 1
                vals(idx) = ro64v
            end do
        end do
        nval = idx

        call sort64(vals, nval)

        dmin = huge(1.0d0)
        nonzero_below_thresh = .false.
        do idx = 2, nval
            d = vals(idx) - vals(idx - 1)
            if (d .gt. 0.0d0) then
                dmin = min(dmin, d)
                if (d .le. thresh) nonzero_below_thresh = .true.
            end if
        end do

        print '(A,ES11.4)', '  min nonzero |RO64a - RO64b| (sorted grid) = ', dmin
        print '(A,L1)', '  exists REAL64 pair with 0 < diff <= 0.9e-7: ', &
            nonzero_below_thresh
        if (.not. nonzero_below_thresh) then
            print *, "WARNING: 0.9e-7 not reached in this coarse REAL64 scan"
            nfail_arg = nfail_arg + 1
        else
            print *, "OK: 0.9e-7 IS reachable in REAL64 (float32 is the cause)"
        end if
    end subroutine fp64_reachability

    subroutine sort64(vals, n)
        integer, intent(in) :: n
        real(dp), intent(inout) :: vals(n)
        integer :: ii, llast
        do ii = n/2, 1, -1
            call sift64(vals, ii, n)
        end do
        do llast = n, 2, -1
            vals(1) = vals(llast)
            call sift64(vals, 1, llast - 1)
        end do
    end subroutine sort64

    subroutine sift64(vals, start, n)
        integer, intent(in) :: start, n
        real(dp), intent(inout) :: vals(n)
        integer :: root, child
        real(dp) :: tmp
        root = start
        do
            child = 2*root
            if (child .gt. n) exit
            if (child .lt. n) then
                if (vals(child + 1) .gt. vals(child)) child = child + 1
            end if
            if (vals(root) .ge. vals(child)) exit
            tmp = vals(root); vals(root) = vals(child); vals(child) = tmp
            root = child
        end do
    end subroutine sift64

    ! Heapsort (O(n log n)) - достаточно для ~52k значений.
    subroutine sort32(vals, n)
        integer, intent(in) :: n
        real(sp), intent(inout) :: vals(n)
        real(sp) :: tmp
        integer :: ii, llast

        ! Построение кучи.
        do ii = n/2, 1, -1
            call sift_down(vals, ii, n)
        end do
        ! Извлечение корня.
        do llast = n, 2, -1
            tmp = vals(1); vals(1) = vals(llast); vals(llast) = tmp
            call sift_down(vals, 1, llast - 1)
        end do
    end subroutine sort32

    subroutine sift_down(vals, start, n)
        integer, intent(in) :: start, n
        real(sp), intent(inout) :: vals(n)
        integer :: root, child
        real(sp) :: tmp
        root = start
        do
            child = 2*root
            if (child .gt. n) exit
            if (child .lt. n) then
                if (vals(child + 1) .gt. vals(child)) child = child + 1
            end if
            if (vals(root) .ge. vals(child)) exit
            tmp = vals(root); vals(root) = vals(child); vals(child) = tmp
            root = child
        end do
    end subroutine sift_down

end program eos_precision_test
