! ==============================================================================
! Тестовая программа: convective adjustment (этап 3.2).
! Проверяет исторический алгоритм конвективного перемешивания:
!   1. искусственная неустойчивая двухслойная колонка перемешивается;
!   2. плотностная инверсия уменьшается ниже порога 0.9E-7;
!   3. интеграл T*DZ1 сохраняется;
!   4. интеграл S*DZ1 сохраняется;
!   5. уже устойчивая колонка не изменяется.
! ==============================================================================

program conv_test
    use equation_of_state, only: density_anomaly
    use convective_adjustment, only: convect_column
    implicit none

    integer, parameter :: ks = 18
    real, parameter :: eps_density = 0.9e-7

    integer :: n_errors, n_checks
    integer :: ki, nmix, k
    real :: t_in(ks), s_in(ks), t_out(ks), s_out(ks), dz1c(ks)
    real :: int_t, int_s, r1, r2, max_inv

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  Running Convective Adjustment Validation Suite"
    print *, "=================================================="

    ! Толщины полуслоёв: монотонно растущие (аналог реальной сетки z)
    do k = 1, ks
        dz1c(k) = 500.0 + 250.0*real(k - 1)
    end do

    ! --- 1-2. Неустойчивая двухслойная колонка ---
    ! Тёплый солёный лёгкий уровень снизу, холодный плотный сверху.
    ki = 2
    t_in(1) = 2.0;  s_in(1) = 0.035   ! плотный сверху
    t_in(2) = 15.0; s_in(2) = 0.033   ! лёгкий снизу
    t_out = t_in
    s_out = s_in
    r1 = density_anomaly(t_in(1), s_in(1))
    r2 = density_anomaly(t_in(2), s_in(2))
    n_checks = n_checks + 1
    if (r1 - r2 .le. eps_density) then
        print '(A,F12.8,A,F12.8)', "ERROR: initial column not unstable: ", r1, " ", r2
        n_errors = n_errors + 1
    else
        print '(A,F12.8,A,F12.8)', "OK: initial inversion present: ", r1, " ", r2
    end if

    call convect_column(t_out, s_out, dz1c, ki, nmix)
    n_checks = n_checks + 1
    if (nmix .le. 0) then
        print *, "ERROR: no mixing performed on unstable column"
        n_errors = n_errors + 1
    else
        print '(A,I0)', "OK: mixing performed (nmix=", nmix, ")"
    end if

    ! Инверсия после перемешивания должна быть <= порога
    r1 = density_anomaly(t_out(1), s_out(1))
    r2 = density_anomaly(t_out(2), s_out(2))
    n_checks = n_checks + 1
    if (r1 - r2 .gt. eps_density) then
        print '(A,F12.8,A,F12.8)', "ERROR: inversion not removed: ", r1, " ", r2
        n_errors = n_errors + 1
    else
        print '(A,F12.8,A,F12.8)', "OK: inversion removed: ", r1, " ", r2
    end if

    ! --- 3-4. Сохранение интегралов T*DZ1 и S*DZ1 ---
    int_t = 0.0
    int_s = 0.0
    do k = 1, ki
        int_t = int_t + t_in(k)*dz1c(k)
        int_s = int_s + s_in(k)*dz1c(k)
    end do
    ! После: оба уровня одинаковы (T_out(1)=T_out(2)), сумма толщин DZ1(1)+DZ1(2)
    call check_cons(t_out(1)*(dz1c(1) + dz1c(2)), int_t, "integral T*DZ1")
    call check_cons(s_out(1)*(dz1c(1) + dz1c(2)), int_s, "integral S*DZ1")

    ! --- 3-4b. Трёхслойная колонка: инверсия между 1-2 и 2-3,
    !           интегралы по всем уровням ---
    ki = 3
    t_in(1) = 2.0;  s_in(1) = 0.035
    t_in(2) = 12.0; s_in(2) = 0.034
    t_in(3) = 18.0; s_in(3) = 0.033
    t_out = t_in
    s_out = s_in
    int_t = 0.0
    int_s = 0.0
    do k = 1, ki
        int_t = int_t + t_in(k)*dz1c(k)
        int_s = int_s + s_in(k)*dz1c(k)
    end do
    call convect_column(t_out, s_out, dz1c, ki, nmix)
    call check_cons(int_t, sum_dz1_t(3, t_out, dz1c), "integral T*DZ1 (3-layer)")
    call check_cons(int_s, sum_dz1_s(3, s_out, dz1c), "integral S*DZ1 (3-layer)")

    ! Плотность после: монотонно невозрастающая сверху вниз (отсутствие инверсии)
    max_inv = 0.0
    do k = 1, ki - 1
        r1 = density_anomaly(t_out(k), s_out(k))
        r2 = density_anomaly(t_out(k + 1), s_out(k + 1))
        max_inv = max(max_inv, r1 - r2)
    end do
    n_checks = n_checks + 1
    if (max_inv .gt. eps_density) then
        print '(A,F12.8)', "ERROR: 3-layer column still unstable: ", max_inv
        n_errors = n_errors + 1
    else
        print '(A,F12.8)', "OK: 3-layer column stable (max_inv=", max_inv, ")"
    end if

    ! --- 5. Устойчивая колонка не изменяется ---
    ki = 3
    t_in(1) = 18.0; s_in(1) = 0.033   ! лёгкая сверху
    t_in(2) = 10.0; s_in(2) = 0.034
    t_in(3) = 2.0;  s_in(3) = 0.035   ! плотная снизу
    t_out = t_in
    s_out = s_in
    call convect_column(t_out, s_out, dz1c, ki, nmix)
    n_checks = n_checks + 1
    if (nmix .ne. 0) then
        print *, "ERROR: stable column was mixed (nmix=", nmix, ")"
        n_errors = n_errors + 1
    else
        print *, "OK: stable column untouched"
    end if
    call check_cons(t_in(1), t_out(1), "stable T1")
    call check_cons(t_in(2), t_out(2), "stable T2")
    call check_cons(t_in(3), t_out(3), "stable T3")
    call check_cons(s_in(1), s_out(1), "stable S1")
    call check_cons(s_in(2), s_out(2), "stable S2")
    call check_cons(s_in(3), s_out(3), "stable S3")

    print *, "=================================================="
    print *, "Total checks: ", n_checks + n_errors, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: All convective adjustment checks PASSED cleanly!"
        stop 0
    else
        print *, "FAILURE: convective adjustment validation errors: ", n_errors
        stop 1
    end if

contains

    subroutine check_cons(actual, expected, label)
        real, intent(in) :: actual, expected
        character(len=*), intent(in) :: label
        real :: rtol
        ! Относительный допуск float32: 1e-4 от величины (погрешность
        ! накопления интегральных сумм и округления single precision).
        rtol = 1.0e-4*max(1.0, abs(expected))
        n_checks = n_checks + 1
        if (abs(actual - expected) .gt. rtol) then
            print '(A,A,A,E14.6,A,E14.6)', "ERROR: ", label, &
                " got=", actual, " expected=", expected
            n_errors = n_errors + 1
        else
            print '(A,A,E14.6)', "OK: ", label, actual
        end if
    end subroutine check_cons

    real function sum_dz1_t(n, arr, dz1c)
        integer, intent(in) :: n
        real, intent(in) :: arr(:), dz1c(:)
        integer :: k
        sum_dz1_t = 0.0
        do k = 1, n
            sum_dz1_t = sum_dz1_t + arr(k)*dz1c(k)
        end do
    end function sum_dz1_t

    real function sum_dz1_s(n, arr, dz1c)
        integer, intent(in) :: n
        real, intent(in) :: arr(:), dz1c(:)
        integer :: k
        sum_dz1_s = 0.0
        do k = 1, n
            sum_dz1_s = sum_dz1_s + arr(k)*dz1c(k)
        end do
    end function sum_dz1_s

end program conv_test