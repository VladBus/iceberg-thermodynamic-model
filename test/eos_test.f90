! ==============================================================================
! Тестовая программа: проверка исторического уравнения состояния Эккарта.
! Проверяет точность density_anomaly на контрольных точках и физические
! диапазоны при типовых значениях T/S модели.
! ==============================================================================

program eos_test
    use equation_of_state
    implicit none

    integer :: n_errors, n_checks
    real :: val, expected, tol

    n_errors = 0
    n_checks = 0
    tol = 1.0e-6

    print *, "=================================================="
    print *, "  Running EOS (Eckart) Validation Suite"
    print *, "=================================================="

    ! 1. Контрольные точки из этапа 2 (sanity check, python)
    call check_eos(15.0, 0.033, 0.00444205, "T=15, S=0.033")
    call check_eos(0.0, 0.033, 0.00654273, "T=0, S=0.033")
    call check_eos(25.0, 0.035, 0.00355798, "T=25, S=0.035")

    ! 2. Физические диапазоны для типового диапазона модели
    !    (T от 2 до 23°C, S от 0.033 до 0.035) - см. initial_conditions.
    print *, "--- Physical range checks ---"
    val = density_anomaly(2.0, 0.033)
    call check_range(val, "T=2, S=0.033", 0.0, 0.01)
    val = density_anomaly(15.0, 0.034)
    call check_range(val, "T=15, S=0.034", 0.0, 0.01)
    val = density_anomaly(23.0, 0.035)
    call check_range(val, "T=23, S=0.035", 0.0, 0.01)

    ! 3. Монотонность по солености: при фиксированной T плотность
    !    должна расти с соленостью.
    print *, "--- Monotonicity in S ---"
    if (density_anomaly(10.0, 0.033) .ge. density_anomaly(10.0, 0.035)) then
        print *, "ERROR: density should increase with salinity"
        n_errors = n_errors + 1
    else
        n_checks = n_checks + 1
    end if

    print *, "=================================================="
    print *, "Total checks: ", n_checks + n_errors, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: All EOS checks PASSED cleanly!"
        stop 0
    else
        print *, "FAILURE: EOS validation errors: ", n_errors
        stop 1
    end if

contains

    subroutine check_eos(t, s, expected, label)
        real, intent(in) :: t, s, expected
        character(len=*), intent(in) :: label
        real :: val
        val = density_anomaly(t, s)
        n_checks = n_checks + 1
        if (abs(val - expected) .gt. tol) then
            print '(A,A,F12.6,A,F12.6,A)', "ERROR: ", label, &
                " got=", val, " expected=", expected
            n_errors = n_errors + 1
        else
            print '(A,A,F12.6)', "OK: ", label, val
        end if
    end subroutine check_eos

    subroutine check_range(val, label, lo, hi)
        real, intent(in) :: val, lo, hi
        character(len=*), intent(in) :: label
        n_checks = n_checks + 1
        if (val .lt. lo .or. val .gt. hi) then
            print '(A,A,F12.6,A,F12.6,A,F12.6)', "ERROR: ", label, &
                " value=", val, " not in [", lo, ",", hi, "]"
            n_errors = n_errors + 1
        else
            print '(A,A,F12.6)', "OK: ", label, val
        end if
    end subroutine check_range

end program eos_test