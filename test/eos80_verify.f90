! ==============================================================================
! Тестовая программа: проверка UNESCO EOS-80 (Stage 11.4).
! Сверяет unesco_rho / unesco_freezing_point / производные с эталонными
! значениями Fofonoff & Millard (1983):
!   rho(0, 5, 0)    = 999.9668  кг/м³ (чистая вода; точное)
!   rho(35, 5, 0)   = 1027.6755 кг/м³ (допуск 0.02: память + float64)
!   Tf(35, 0)       = -1.9223   °C    (допуск 0.005; прямое вычисление формулы)
!   4.0 < rho(35,5,1000)-rho(35,5,0) < 5.5 кг/м³ (сжимаемость, диапазон)
!   drho/dT < 0, drho/dS > 0 при (35, 5, 0) (знаки)
!   FD-сходимость производных: шаг/2 меняет результат < 5%
!   Конвенция аномалии: eos80_density_anomaly = rho/1000 - 1.02 [г/см³]
! Ошибка → stop 1 (как в eos_test.f90).
! ==============================================================================

program eos80_verify
    use eos80_unesco
    use equation_of_state, only: eos80_density_anomaly
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    integer :: n_errors, n_checks
    real(real64) :: val, expected, tol

    n_errors = 0
    n_checks = 0

    ! 1. Чистая вода (5°C, 0 дбар)
    val = unesco_rho(0.0_real64, 5.0_real64, 0.0_real64)
    expected = 999.9668_real64
    tol = 0.01_real64
    n_checks = n_checks + 1
    if (abs(val - expected) .gt. tol) then
        print *, 'FAIL pure water: ', val, ' expected ', expected
        n_errors = n_errors + 1
    end if

    ! 2. Стандартный океан (35 PSU, 5°C, 0 дбар)
    val = unesco_rho(35.0_real64, 5.0_real64, 0.0_real64)
    expected = 1027.6755_real64
    tol = 0.02_real64
    n_checks = n_checks + 1
    if (abs(val - expected) .gt. tol) then
        print *, 'FAIL std ocean: ', val, ' expected ', expected
        n_errors = n_errors + 1
    end if

    ! 3. Сжимаемость: +1000 дбар даёт +4..5.5 кг/м³
    val = unesco_rho(35.0_real64, 5.0_real64, 1000.0_real64) &
        - unesco_rho(35.0_real64, 5.0_real64, 0.0_real64)
    n_checks = n_checks + 1
    if (val .lt. 4.0_real64 .or. val .gt. 5.5_real64) then
        print *, 'FAIL compressibility: dRho = ', val
        n_errors = n_errors + 1
    end if

    ! 4. Точка замерзания (35 PSU, 0 дбар)
    val = unesco_freezing_point(35.0_real64, 0.0_real64)
    expected = -1.9223_real64
    tol = 0.005_real64
    n_checks = n_checks + 1
    if (abs(val - expected) .gt. tol) then
        print *, 'FAIL freezing point: ', val, ' expected ', expected
        n_errors = n_errors + 1
    end if

    ! 5. Знаки производных при (35, 5, 0)
    n_checks = n_checks + 1
    if (.not. (unesco_drho_dT(35.0_real64, 5.0_real64, 0.0_real64) .lt. 0.0_real64)) then
        print *, 'FAIL drho/dT sign'
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    if (.not. (unesco_drho_dS(35.0_real64, 5.0_real64, 0.0_real64) .gt. 0.0_real64)) then
        print *, 'FAIL drho/dS sign'
        n_errors = n_errors + 1
    end if

    ! 6. FD-сходимость drho/dT (шаг/2 → <5% изменения)
    block
        real(real64) :: d1, d2, h
        h = 1.0e-3_real64
        d1 = (unesco_rho(35.0_real64, 5.0_real64 + h, 0.0_real64) - &
              unesco_rho(35.0_real64, 5.0_real64 - h, 0.0_real64))/(2.0_real64*h)
        h = 0.5e-3_real64
        d2 = (unesco_rho(35.0_real64, 5.0_real64 + h, 0.0_real64) - &
              unesco_rho(35.0_real64, 5.0_real64 - h, 0.0_real64))/(2.0_real64*h)
        n_checks = n_checks + 1
        if (abs(d1 - d2)/max(abs(d1), tiny(1.0_real64)) .gt. 0.05_real64) then
            print *, 'FAIL FD convergence: ', d1, d2
            n_errors = n_errors + 1
        end if
    end block

    ! 7. Конвенция аномалии модели: rho/1000 - 1.02 [г/см³]
    val = eos80_density_anomaly(5.0_real64, 0.035_real64, 0.0_real64)
    expected = (1027.6755_real64/1000.0_real64) - 1.02_real64
    tol = 2.0e-5_real64
    n_checks = n_checks + 1
    if (abs(val - expected) .gt. tol) then
        print *, 'FAIL anomaly convention: ', val, ' expected ', expected
        n_errors = n_errors + 1
    end if

    print *, 'eos80_verify: ', n_checks - n_errors, '/', n_checks, ' checks passed'
    if (n_errors .gt. 0) then
        print *, 'EOS80 VERIFICATION FAILED'
        stop 1
    else
        print *, 'EOS80 VERIFICATION PASSED'
        stop 0
    end if
end program eos80_verify
