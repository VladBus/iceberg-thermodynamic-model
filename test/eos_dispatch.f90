! ==============================================================================
! Тестовая программа: диспетчер плотности eos_diag × 4 комбинации
! переключателей (Stage 11.6.1, Phase 2).
! Матрица: {eos80_mode} × {eos_f64_mode} → ro() обязан следовать ВЫБРАННОМУ
! уравнению состояния (явное правило D-30: EOS80 выбирает формулу и
! подразумевает f64 в eos_diag; eos_f64_mode — точность ТОЛЬКО legacy).
! Проверяет:
!   - выбранное УС действительно используется (отличие от альтернативы
!     > 1e-6 — селекция доказана, а не только консистентность);
!   - согласие с диспетчером (tol 1e-12);
!   - давление уровней входит при EOS80 (p=z×0.01) и игнорируется legacy;
!   - legacy-комбинации бит-идентичны прямым legacy-вызовам.
! Комбинация EOS80+f64 — регрессия на фикс 11.6.1 (до фикса давала legacy).
! Физика модели НЕ меняется (чистый тест). Ошибка → stop 1.
! ==============================================================================

program eos_dispatch
    use param
    use equation_of_state, only: eos80_mode, eos_f64_mode, eos_diag, &
                                 density_anomaly, density_anomaly_f64, &
                                 eos_density, eos_density_f64, &
                                 eos80_density_anomaly
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    integer :: n_errors, n_checks
    integer, parameter :: CI = 50, CJ = 50
    real :: t_in, s_in
    real :: legacy_f32, legacy_f64, eos80_p10, eos80_p30, eos80_p0

    n_errors = 0
    n_checks = 0

    ! --- Стенд: одна мокрая клетка, 2 уровня; давление через z ---
    kt1(:, :) = 0
    kt1(CI, CJ) = 2
    t2(:, :, :) = 0.0
    s2(:, :, :) = 0.0
    t_in = 2.0
    s_in = 0.035
    t2(CI, CJ, 1) = t_in
    s2(CI, CJ, 1) = s_in
    t2(CI, CJ, 2) = t_in
    s2(CI, CJ, 2) = s_in
    z(:) = 0.0
    z(1) = 1000.0   ! p = 10 дбар
    z(2) = 3000.0   ! p = 30 дбар

    ! Эталоны (прямые вызовы; legacy-конвенция + UNESCO):
    legacy_f32 = density_anomaly(t_in, s_in)
    legacy_f64 = real(density_anomaly_f64(real(t_in, real64), &
                                          real(s_in, real64)), kind(1.0))
    eos80_p10 = real(eos80_density_anomaly(real(t_in, real64), &
                                           real(s_in, real64), 10.0_real64), kind(1.0))
    eos80_p30 = real(eos80_density_anomaly(real(t_in, real64), &
                                           real(s_in, real64), 30.0_real64), kind(1.0))
    eos80_p0 = real(eos80_density_anomaly(real(t_in, real64), &
                                          real(s_in, real64), 0.0_real64), kind(1.0))

    ! --- Комбинация 1: legacy + f32 ---
    eos80_mode = .false.
    eos_f64_mode = .false.
    call eos_diag()
    call check_eq(ro(CI, CJ, 1), legacy_f32, 0.0, 'leg+f32 k1 bit-identical')
    call check_eq(ro(CI, CJ, 2), legacy_f32, 0.0, 'leg+f32 k2 bit-identical')
    call check_eq(ro(CI, CJ, 1), eos_density(t_in, s_in, 10.0), 1.0e-12, &
                  'leg+f32 dispatcher agreement')

    ! --- Комбинация 2: legacy + f64 ---
    eos80_mode = .false.
    eos_f64_mode = .true.
    call eos_diag()
    call check_eq(ro(CI, CJ, 1), legacy_f64, 1.0e-12, 'leg+f64 k1')
    call check_eq(ro(CI, CJ, 2), legacy_f64, 1.0e-12, 'leg+f64 k2')
    call check_eq(ro(CI, CJ, 1), legacy_f32, 1.0e-8, 'leg+f64 vs f32 rounding scale')

    ! --- Комбинация 3: EOS80 + f32 ---
    eos80_mode = .true.
    eos_f64_mode = .false.
    call eos_diag()
    call check_eq(ro(CI, CJ, 1), eos80_p10, 1.0e-9, 'eos80+f32 k1')
    call check_eq(ro(CI, CJ, 2), eos80_p30, 1.0e-9, 'eos80+f32 k2 pressure level')
    call check_neq(ro(CI, CJ, 1), legacy_f32, 1.0e-6, 'eos80+f32 selection vs legacy')
    call check_neq(eos80_p10, eos80_p0, 1.0e-6, 'eos80 pressure enters (p10 vs p0)')

    ! --- Комбинация 4: EOS80 + f64 (РЕГРЕССИЯ на фикс 11.6.1) ---
    eos80_mode = .true.
    eos_f64_mode = .true.
    call eos_diag()
    call check_eq(ro(CI, CJ, 1), eos80_p10, 1.0e-9, 'eos80+f64 k1 (fix)')
    call check_eq(ro(CI, CJ, 2), eos80_p30, 1.0e-9, 'eos80+f64 k2 (fix)')
    call check_neq(ro(CI, CJ, 1), legacy_f64, 1.0e-6, 'eos80+f64 selection vs legacy-f64')
    call check_eq(ro(CI, CJ, 1), real(eos_density_f64(real(t_in, real64), &
        real(s_in, real64), 10.0_real64), kind(1.0)), 1.0e-12, 'eos80+f64 dispatcher agreement')

    print *, 'eos_dispatch: ', n_checks - n_errors, '/', n_checks, ' checks passed'
    if (n_errors .gt. 0) then
        print *, 'EOS DISPATCH FAILED'
        stop 1
    else
        print *, 'EOS DISPATCH PASSED'
        stop 0
    end if

contains

    subroutine check_eq(val, expected, tol, label)
        real, intent(in) :: val, expected, tol
        character(len=*), intent(in) :: label
        n_checks = n_checks + 1
        if (.not. (val .eq. val .and. expected .eq. expected) .or. &
            abs(val - expected) .gt. tol) then
            print *, 'FAIL ', trim(label), ': ', val, ' expected ', expected
            n_errors = n_errors + 1
        end if
    end subroutine check_eq

    subroutine check_neq(val, other, minsep, label)
        real, intent(in) :: val, other, minsep
        character(len=*), intent(in) :: label
        n_checks = n_checks + 1
        if (.not. (val .eq. val .and. other .eq. other) .or. &
            abs(val - other) .lt. minsep) then
            print *, 'FAIL ', trim(label), ': ', val, ' vs ', other
            n_errors = n_errors + 1
        end if
    end subroutine check_neq

end program eos_dispatch
