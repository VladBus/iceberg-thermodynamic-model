! ==============================================================================
! Модуль: equation_of_state
! Назначение: Историческое уравнение состояния Эккарта (модификация,
!             применявшаяся в оригинальной модели Дмитриева-Нестерова).
! Физика: Вычисляет аномалию плотности морской воды RO = rho - 1.02 [г/см3]
!         как функцию температуры T [°C] и солености S [массовая доля].
!
!         Формула Эккарта (Nesterov_last.txt:2046, Coupl1.f90:816):
!           RO = 1 / (0.698 + aa/bb) - 1.02
!         где:
!           aa = 1779.5 + (11.25 - 0.0745·T)·T - (3800.0 + 10.0·T)·S
!           bb = 5891.0 + 3000.0·S + (38.0 - 0.375·T)·T
!
!         Физический смысл коэффициентов (массовая доля S):
!           3800 = 3.8 / (0.01) — приведение S из доли к промилле-подобной шкале
!           3000 = 3.0 / (0.01) — аналогично
!           1779.5 — эмпирический коэффициент уравнения состояния
!           0.698 — обратная плотность (1/ρ₀ ≈ 1/1.43 ≈ 0.698)
!           1.02 — базовая плотность [г/см³] (вода ~1.025, anomal = ρ-1.02)
!
!         Численные свойства (Stage 4.3 + Stage 10.21):
!           - Вычисления в single precision (real = float32).
!           - В производственном домене (T ∈ [-2, 5] °C, S ∈ [0.033, 0.035]):
!             X = 0.698 + aa/bb ∈ [0.972462, 0.974607] (НЕ [1, 2) — значения
!             заголовка исправлены, Stage 10.21), следовательно
!             1/X ≈ 1.027 ∈ [1, 2) — binade с ULP = 2^-23 ≈ 1.19e-7.
!           - Аномалия RO = 1/X - 1.02 ∈ [0.006055, 0.008318] (типичная ~0.007,
!             НЕ ≈ 0.025 — исправлено). max |RO_f64 - RO_f32| = 1.39e-7 ≈ 2^-23
!             (квантизация float32; см. docs/validation/stage10.21_*).
!           - Порог конвективной неустойчивости 0.9e-7 < 2^-23 — сходимость
!             convective_adjustment в float32 недостижима; Stage 10.21:
!             f64-путь (STAGE1021_CA_F64) или порог 1.5e-7/2.4e-7
!             (STAGE1021_CA_EPS) за env-переключателями, default OFF
!             → legacy бит-идентичен.
! Единицы: T [°C], S [массовая доля, ~0.033-0.035], RO [г/см³] (аномалия).
! Зависимости: param (только для диагностической подпрограммы eos_diag).
! ==============================================================================

module equation_of_state
    use param
    use eos80_unesco, only: unesco_rho
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    ! ==========================================================================
    ! Stage 10.21: селектор точности EOS (runtime, по умолчанию OFF).
    !
    !   eos_f64_mode = .true.  → eos_diag вычисляет RO в double precision
    !                            (scope=all варианта EXP-C: массив ro получает
    !                            значения с f64-точностью вычисления).
    !   eos_f64_mode = .false. → поведение бит-идентично предыдущим стадиям
    !                            (RO в float32, density_anomaly).
    !
    ! Управляется из main.f90 через eos_configure (env STAGE1021_CA_F64_SCOPE).
    ! Не влияет на density_anomaly (legacy f32) и density_anomaly_f64.
    logical, save :: eos_f64_mode = .false.

    ! ==========================================================================
    ! Stage 11.4: селектор EOS-80 (runtime, по умолчанию LEGACY = OFF).
    !
    !   eos80_mode = .true.  → диспетчеры eos_density/eos_density_f64 считают
    !                            плотность по UNESCO EOS-80 (давление-зависимо).
    !   eos80_mode = .false. → бит-идентичный legacy Эккарт (тот же вызов).
    !
    !   Управляется из main.f90 через eos80_configure() (env EOS_MODE:
    !   'EOS80'/'eos80'/'true'/'1' → ON; всё остальное/пусто → OFF/LEGACY).
    !   Конвенция выхода сохранена: аномалия rho-1.02 [г/см³]; S модели
    !   (массовая доля) ×1000 → PSU; p [дбар] передаётся вызывающим
    !   (глубина уровня в метрах: z[см]×0.01).
    ! ==========================================================================
    logical, save :: eos80_mode = .false.

    contains

    subroutine eos80_configure()
        character(len=256) :: env_str
        call get_environment_variable('EOS_MODE', env_str)
        if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'EOS80' .or. &
            env_str .eq. 'eos80' .or. env_str .eq. 'true' .or. env_str .eq. '1')) then
            eos80_mode = .true.
            print *, '>>> Stage 11.4: EOS_MODE=EOS80 (UNESCO 1983 density)'
        else
            print *, '>>> Stage 11.4: EOS_MODE=LEGACY (Eckart, bit-identical)'
        end if
    end subroutine eos80_configure

    ! Аномалия EOS-80 в конвенции модели: rho[кг/м³]/1000 − 1.02 [г/см³].
    pure real(real64) function eos80_density_anomaly(t_frac, s_frac, p_dbar) result(ro_anom)
        real(real64), intent(in) :: t_frac, s_frac, p_dbar
        ro_anom = unesco_rho(s_frac*1000.0_real64, t_frac, p_dbar)/1000.0_real64 &
                  - 1.02_real64
    end function eos80_density_anomaly

    ! Диспетчер f32: OFF → тот же вызов legacy (бит-идентично).
    pure real function eos_density(t, s, p) result(ro_anom)
        real, intent(in) :: t, s, p
        if (eos80_mode) then
            ro_anom = real(eos80_density_anomaly(real(t, real64), real(s, real64), &
                                                 real(p, real64)))
        else
            ro_anom = density_anomaly(t, s)
        end if
    end function eos_density

    ! Диспетчер f64: OFF → тот же вызов legacy (бит-идентично).
    pure real(real64) function eos_density_f64(t, s, p) result(ro_anom)
        real(real64), intent(in) :: t, s, p
        if (eos80_mode) then
            ro_anom = eos80_density_anomaly(t, s, p)
        else
            ro_anom = density_anomaly_f64(t, s)
        end if
    end function eos_density_f64

    ! ==========================================================================
    ! eos_configure: включение/выключение f64-режима eos_diag (Stage 10.21).
    ! Вызывается из main.f90 в блоке инициализации до первого использования.
    ! ==========================================================================
    subroutine eos_configure(f64_mode)
        logical, intent(in) :: f64_mode
        eos_f64_mode = f64_mode
    end subroutine eos_configure

    ! ==========================================================================
    ! density_anomaly: точная историческая формула Эккарта.
    !
    ! Вход:  t [°C], s [массовая доля, 0.033-0.035].
    ! Выход: ro_anom [г/см³] — аномалия плотности (rho - 1.02).
    !
    ! Формула (pure function — безопасна для вызова из convective_adjustment):
    !   RO = 1/(0.698 + aa/bb) - 1.02
    !   aa = 1779.5 + (11.25 - 0.0745·T)·T - (3800.0 + 10.0·T)·S
    !   bb = 5891.0 + 3000.0·S + (38.0 - 0.375·T)·T
    !
    ! Физические ограничения:
    !   T ∈ [-2, 4] °C — типичный диапазон полярных вод.
    !   S ∈ [0.030, 0.040] — морская соль.
    !   RO ∈ [0.0038, +0.0124] — разброс плотности определяет бароклинность.
    !   Точность: ~1e-6 г/см³ (float32).
    ! ==========================================================================
    pure real function density_anomaly(t, s) result(ro_anom)
        real, intent(in) :: t, s
        real :: aa, bb

        ! aa: числитель дроби, содержит линейные и квадратичные члены T,
        !     а также конкуренцию T и S (термогалинное взаимодействие).
        aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
        ! bb: знаменатель дроби, определяет основную структуру зависимости ρ(T,S).
        bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
        ! ro_anom: аномалия = обратная величина - базовая плотность.
        !   0.698 = обратная плотность淡水: 1/ρ₀.
        !   1.020 = базовая плотность морской воды [г/см³].
        ro_anom = 1.0/(0.698 + aa/bb) - 1.02
    end function density_anomaly

    ! ==========================================================================
    ! density_anomaly_f64: тот же исторический Эккарт, вычисленный в double
    ! precision (Stage 10.21, EXP-A/C/D).
    !
    ! Та же формула, те же коэффициенты, но все аргументы и промежуточные
    ! величины — real64. float32-версия (density_anomaly) квантизует RO на
    ! решётку 2^-23 ≈ 1.19e-7; f64 версия устраняет эту дискретизацию:
    ! остаточная инверсия после перемешивания становится достижима ниже
    ! порога 0.9e-7 (см. docs/validation/stage10.21_*).
    !
    ! Вход:  t [°C], s [массовая доля, 0.033-0.035] (real64).
    ! Выход: ro_anom [г/см³] — аномалия плотности (rho - 1.02), real64.
    !
    ! Не используется в legacy-пути convective_adjustment; вызывается только
    ! из convect_column_f64 и из eos_diag при eos_f64_mode=.true.
    ! ==========================================================================
    pure real(real64) function density_anomaly_f64(t, s) result(ro_anom)
        real(real64), intent(in) :: t, s
        real(real64) :: aa, bb

        aa = 1779.5_real64 + (11.25_real64 - 0.0745_real64*t)*t &
             - (3800.0_real64 + 10.0_real64*t)*s
        bb = 5891.0_real64 + 3000.0_real64*s + (38.0_real64 - 0.375_real64*t)*t
        ro_anom = 1.0_real64/(0.698_real64 + aa/bb) - 1.02_real64
    end function density_anomaly_f64

    ! ==========================================================================
    ! eos_diag: диагностический расчёт RO по текущим T2/S2 (этап 3.1).
    !
    ! Заполняет ro(i,j,k) только в активных водных ячейках (kt1>0, k≤kt1)
    ! и выводит статистику min/max/mean по всему полю.
    ! Водная ячейка: kt1(i,j) = число мокрых уровней (0 = суша).
    !
    ! НЕ используется в уравнениях движения на этом этапе (RO в momentum
    ! не применяется до этапа 3.3). Вызывается в main.f90 для мониторинга.
    ! ==========================================================================
    subroutine eos_diag()
        integer :: i, j, k, n
        real :: rmin, rmax, rsum, rmean

        n = 0
        rmin = huge(1.0)    ! Начальное значение = max(float32)
        rmax = -huge(1.0)   ! Начальное значение = min(float32)
        rsum = 0.0

        ! Цикл по всем внутренним ячейкам (i=2..is, j=2..js),
        ! пропуская береговые (kt1=0) и ниже дна (k>kt1).
        do k = 1, ks
            do j = 2, js
                do i = 2, is
                    if (kt1(i, j) .eq. 0) cycle  ! Суша — пропуск
                    if (k .gt. kt1(i, j)) cycle   ! Ниже дна — пропуск
                    if (eos_f64_mode) then
                        ! Stage 10.21 (scope=all, EXP-C): RO с f64-точностью.
                        ro(i, j, k) = real(density_anomaly_f64( &
                            real(t2(i, j, k), real64), real(s2(i, j, k), real64)), &
                            kind(1.0))
                    else if (eos80_mode) then
                        ! Stage 11.4: EOS-80, давление уровня p = z[см]×0.01 [дбар].
                        ro(i, j, k) = real(eos_density_f64( &
                            real(t2(i, j, k), real64), real(s2(i, j, k), real64), &
                            real(z(k)*0.01, real64)), kind(1.0))
                    else
                        ro(i, j, k) = density_anomaly(t2(i, j, k), s2(i, j, k))
                    end if
                    rmin = min(rmin, ro(i, j, k))
                    rmax = max(rmax, ro(i, j, k))
                    rsum = rsum + ro(i, j, k)
                    n = n + 1
                end do
            end do
        end do

        if (n .gt. 0) then
            rmean = rsum/real(n)  ! Средняя аномалия плотности [г/см³]
        else
            rmin = 0.0
            rmax = 0.0
            rmean = 0.0
        end if

        ! Вывод: типичные значения RO ≈ [0.0038, +0.0124] для полярных вод.
        print '(A,F14.8,A,F14.8,A,F14.8,A,I8)', &
            'EOS [g/cm3] min=', rmin, ' max=', rmax, ' mean=', rmean, ' n=', n
    end subroutine eos_diag

end module equation_of_state
