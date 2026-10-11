! ==============================================================================
! Тестовая программа: независимая сверка UNESCO EOS-80 (Stage 11.6, Phase 1).
! Два уровня эталонов:
!   (A) ОПУБЛИКОВАННЫЕ якори Fofonoff & Millard (1983), UNESCO Tech. Pap. 44:
!       rho(0,5,0) = 999.9668 кг/м³ (чистая вода, точное);
!       rho(35,5,0) = 1027.6755 кг/м³ (стандартный океан);
!       Tf(35,0) = -1.9223 °C.
!   (B) НЕЗАВИСИМАЯ транскрипция полинома UNESCO (наивная форма, отдельный
!       кодировщик, Python float64; модуль — Horner real64): таблица ниже.
!       Ловит опечатки коэффициентов (главный класс риска — ср. 11.4, где
!       i/j/m-серии правились по памяти); структурные ошибки ловят якори (A)
!       и физические инварианты (знаки, монотонность, сжимаемость).
! Допуски (11.6): плотность ≤1e-6 отн. к UNESCO; Tf ≤1e-4 °C к якорю;
! производные ≤1% отн. Ошибка → stop 1 (конвенция репозитория).
! Физика модели НЕ меняется (чистый тест).
! ==============================================================================

program eos80_reference
    use eos80_unesco
    use equation_of_state, only: eos80_density_anomaly
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    integer :: n_errors, n_checks

    n_errors = 0
    n_checks = 0

    ! --- A. Опубликованные якори ---
    call check_rho(0.0_real64, 5.0_real64, 0.0_real64, 999.9668_real64, 1.0e-3_real64, 'anchor pure water')
    call check_rho(35.0_real64, 5.0_real64, 0.0_real64, 1027.6755_real64, 1.0e-3_real64, 'anchor std ocean')
    call check_tf(35.0_real64, 0.0_real64, -1.9223_real64, 1.0e-4_real64, 'anchor Tf(35,0)')

    ! --- B. Независимая транскрипция: 6 условий ТЗ + границы ---
    call check_rho(0.0_real64, 5.0_real64, 0.0_real64, 999.966751_real64, 1.0e-6_real64, 'T surface fresh')
    call check_rho(35.0_real64, 5.0_real64, 0.0_real64, 1027.675465_real64, 1.0e-6_real64, 'T surface std')
    call check_rho(35.0_real64, 20.0_real64, 0.0_real64, 1024.763005_real64, 1.0e-6_real64, 'T surface warm')
    call check_rho(35.0_real64, 2.0_real64, 3000.0_real64, 1041.649076_real64, 1.0e-6_real64, 'T deep cold')
    call check_rho(35.0_real64, 10.0_real64, 3000.0_real64, 1040.113870_real64, 1.0e-6_real64, 'T deep warm')
    call check_rho(0.0_real64, 0.0_real64, 0.0_real64, 999.842594_real64, 1.0e-6_real64, 'T fresh 0C (=A0)')
    call check_rho(40.0_real64, 0.0_real64, 0.0_real64, 1032.147101_real64, 1.0e-6_real64, 'T hypersaline')
    call check_rho(35.0_real64, -2.0_real64, 0.0_real64, 1028.186757_real64, 1.0e-6_real64, 'BND cold -2C')
    call check_rho(35.0_real64, 30.0_real64, 0.0_real64, 1021.728639_real64, 1.0e-6_real64, 'BND warm +30C')
    call check_rho(40.0_real64, 30.0_real64, 5000.0_real64, 1045.697617_real64, 1.0e-6_real64, 'BND deep hyper')

    ! --- Tf таблица (S=0/35/40 × P=0/1000/3000) ---
    call check_tf(0.0_real64, 0.0_real64, 0.0_real64, 1.0e-12_real64, 'Tf(0,0)')
    call check_tf(35.0_real64, 0.0_real64, -1.9223013411_real64, 1.0e-9_real64, 'Tf(35,0)')
    call check_tf(40.0_real64, 0.0_real64, -2.2120674664_real64, 1.0e-9_real64, 'Tf(40,0)')
    call check_tf(35.0_real64, 1000.0_real64, -2.6753013411_real64, 1.0e-9_real64, 'Tf(35,1000)')
    call check_tf(35.0_real64, 3000.0_real64, -4.1813013411_real64, 1.0e-9_real64, 'Tf(35,3000)')
    call check_tf(40.0_real64, 3000.0_real64, -4.4710674664_real64, 1.0e-9_real64, 'Tf(40,3000)')

    ! --- alpha/beta при (35,5,0) vs транскрипция (допуск 1%) ---
    call check_rel(-unesco_drho_dT(35.0_real64, 5.0_real64, 0.0_real64)/ &
                   unesco_rho(35.0_real64, 5.0_real64, 0.0_real64), &
                   1.136096e-04_real64, 0.01_real64, 'alpha(35,5,0)')
    call check_rel(unesco_drho_dS(35.0_real64, 5.0_real64, 0.0_real64)/ &
                   unesco_rho(35.0_real64, 5.0_real64, 0.0_real64), &
                   7.716871e-04_real64, 0.01_real64, 'beta(35,5,0)')

    ! --- Физические инварианты (независимы от реализации) ---
    call check_signs()
    call check_monotone()

    ! --- Конвенция аномалии модели ---
    block
        real(real64) :: val, expected
        val = eos80_density_anomaly(5.0_real64, 0.035_real64, 0.0_real64)
        expected = 1027.675465_real64/1000.0_real64 - 1.02_real64
        n_checks = n_checks + 1
        if (abs(val - expected) .gt. 1.0e-9_real64) then
            print *, 'FAIL anomaly convention: ', val, ' expected ', expected
            n_errors = n_errors + 1
        end if
    end block

    print *, 'eos80_reference: ', n_checks - n_errors, '/', n_checks, ' checks passed'
    if (n_errors .gt. 0) then
        print *, 'EOS80 REFERENCE FAILED'
        stop 1
    else
        print *, 'EOS80 REFERENCE PASSED'
        stop 0
    end if

contains

    subroutine check_rho(s, t, p, expected, tol, label)
        real(real64), intent(in) :: s, t, p, expected, tol
        character(len=*), intent(in) :: label
        real(real64) :: val
        val = unesco_rho(s, t, p)
        n_checks = n_checks + 1
        if (.not. (val .eq. val) .or. abs(val - expected) .gt. tol) then
            print *, 'FAIL rho ', trim(label), ': ', val, ' expected ', expected
            n_errors = n_errors + 1
        end if
    end subroutine check_rho

    subroutine check_tf(s, p, expected, tol, label)
        real(real64), intent(in) :: s, p, expected, tol
        character(len=*), intent(in) :: label
        real(real64) :: val
        val = unesco_freezing_point(s, p)
        n_checks = n_checks + 1
        if (.not. (val .eq. val) .or. abs(val - expected) .gt. tol) then
            print *, 'FAIL Tf ', trim(label), ': ', val, ' expected ', expected
            n_errors = n_errors + 1
        end if
    end subroutine check_tf

    subroutine check_rel(val, expected, reltol, label)
        real(real64), intent(in) :: val, expected, reltol
        character(len=*), intent(in) :: label
        n_checks = n_checks + 1
        if (.not. (val .eq. val) .or. abs(val - expected)/abs(expected) .gt. reltol) then
            print *, 'FAIL ', trim(label), ': ', val, ' expected ', expected
            n_errors = n_errors + 1
        end if
    end subroutine check_rel

    subroutine check_signs()
        ! drho/dT<0 (выше T_max), drho/dS>0, drho/dP>0 — при (35,5,0).
        n_checks = n_checks + 1
        if (.not. (unesco_drho_dT(35.0_real64, 5.0_real64, 0.0_real64) .lt. 0.0_real64)) then
            print *, 'FAIL drho/dT sign'; n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (.not. (unesco_drho_dS(35.0_real64, 5.0_real64, 0.0_real64) .gt. 0.0_real64)) then
            print *, 'FAIL drho/dS sign'; n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (.not. (unesco_rho(35.0_real64, 5.0_real64, 1000.0_real64) .gt. &
                   unesco_rho(35.0_real64, 5.0_real64, 0.0_real64))) then
            print *, 'FAIL drho/dP sign'; n_errors = n_errors + 1
        end if
    end subroutine check_signs

    subroutine check_monotone()
        ! Монотонность: соль и давление растят плотность; холод (до замерзания) — тоже.
        n_checks = n_checks + 1
        if (.not. (unesco_rho(35.0_real64, 5.0_real64, 0.0_real64) .gt. &
                   unesco_rho(0.0_real64, 5.0_real64, 0.0_real64))) then
            print *, 'FAIL salt monotone'; n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (.not. (unesco_rho(35.0_real64, -2.0_real64, 0.0_real64) .gt. &
                   unesco_rho(35.0_real64, 5.0_real64, 0.0_real64))) then
            print *, 'FAIL cold monotone'; n_errors = n_errors + 1
        end if
        n_checks = n_checks + 1
        if (.not. (unesco_freezing_point(40.0_real64, 0.0_real64) .lt. &
                   unesco_freezing_point(35.0_real64, 0.0_real64))) then
            print *, 'FAIL Tf salt monotone'; n_errors = n_errors + 1
        end if
    end subroutine check_monotone

end program eos80_reference
