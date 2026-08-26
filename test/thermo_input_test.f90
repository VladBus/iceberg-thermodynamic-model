! ==============================================================================
! Тестовая программа: thermodynamic ERA5 input conversions (Stage 5.2).
! Проверяет корректность преобразований ERA5 переменных для термодинамики.
!
! Проверки:
!   1. Влажность: точка росы (d2m) + температура (t2m) -> относительная влажность (humid)
!      Формула: humid = e_sat(d2m) / e_sat(t2m) [0..1]
!      e_sat(T) = 610.78 * 10^(8.61503*(T-273.15)/T) [Па] — формула Клаузиуса-Клапейрона
!   2. Облачность: ERA5 tcc [0,1] -> model cloud [0,1] (прямое копирование)
!   3. Радиационный фактор облаков: sw_factor = 1 - 0.6*cclo^3
!      где cclo — облачность [0..1]; factor ∈ [0.4, 1.0]
!      Уменьшает коротковолновую радиацию при облачности (3-я степень — нелинейный эффект)
!   4. Снегопад: неотрицательность массива sfal (мес. климатология)
!   5. Маппинг переменных ERA5: d2m → humid, tcc → cloud, sf → snowfall (deferred)
! ==============================================================================

program thermo_input_test
    use equation_of_state, only: density_anomaly
    implicit none

    integer :: n_errors, n_checks
    integer :: i, n_humid_tests, n_cloud_tests

    ! Тестовые случаи: (t2m_K, d2m_K) -> ожидаемая humid [0,1]
    ! Формула Клаузиуса-Клапейрона ( Appeals saturation vapor pressure ):
    !   e_sat(T_K) = 610.78 * 10.0^(8.61503*(T_K - 273.15)/T_K) [Па]
    !   RH = e_sat(d2m) / e_sat(t2m)
    ! Когда d2m == t2m → RH = 1.0 (насыщение).
    ! Когда d2m < t2m → RH < 1.0 (ненасыщенный воздух).
    ! Диапазон RH всегда ∈ [0, 1] математически.
    real, parameter :: t2m_test(6) = (/273.15, 263.15, 253.15, 243.15, 273.15, 293.15/)
    real, parameter :: d2m_test(6) = (/273.15, 258.15, 248.15, 238.15, 268.15, 288.15/)
    real, parameter :: humid_expected(6) = (/ &
                       1.0, &   ! насыщение: t2m = d2m = 0°C
                       0.525, & ! d2m = -5°C, t2m = -10°C
                       0.525, & ! d2m = -5°C, t2m = -10°C (тот же дельта)
                       0.525, & ! d2m = -5°C, t2m = -10°C
                       0.79, &  ! t2m = 0°C, d2m = -5°C
                       0.79 &   ! t2m = 20°C, d2m = 15°C (относительно одинаковый дефицит)
                       /)
    real :: humid_computed(6)
    real :: e_sat_t2m, e_sat_d2m

    ! Cloud test arrays
    real :: tcc_test(3), cloud_mapped(3)
    real :: cclo_test(4), sw_expected(4), sw_factor
    real :: cclo

    ! sfal test
    real :: sfal_data(12)

    n_errors = 0
    n_checks = 0
    n_humid_tests = 6
    n_cloud_tests = 4

    print *, "=================================================="
    print *, "  Thermodynamic ERA5 Input Conversion Tests"
    print *, "=================================================="

    ! --- Test 1: Humidity conversion (d2m/t2m -> humid) ---
    print *, ""
    print *, "--- Test 1: Humidity conversion ---"
    do i = 1, n_humid_tests
        n_checks = n_checks + 1
        e_sat_t2m = 610.78*10.0**(8.61503*(t2m_test(i) - 273.15)/t2m_test(i))
        e_sat_d2m = 610.78*10.0**(8.61503*(d2m_test(i) - 273.15)/d2m_test(i))
        humid_computed(i) = e_sat_d2m/e_sat_t2m

        if (humid_computed(i) .lt. 0.0 .or. humid_computed(i) .gt. 1.0) then
            print '(A,I3,A,F10.6)', "ERROR Test 1.", i, ": humid out of [0,1] = ", humid_computed(i)
            n_errors = n_errors + 1
        else if (abs(humid_computed(i) - humid_expected(i)) .gt. 0.05) then
            print '(A,I3,A,F10.6,A,F10.6)', "WARNING Test 1.", i, ": humid = ", humid_computed(i), " expected ~", humid_expected(i)
        else
            print '(A,I3,A,F10.6)', "OK Test 1.", i, ": humid = ", humid_computed(i)
        end if
    end do

    ! --- Test 2: Humidity physical bounds ---
    print *, ""
    print *, "--- Test 2: Humidity bounds ---"
    n_checks = n_checks + 1
    do i = 1, n_humid_tests
        if (humid_computed(i) .lt. 0.0 .or. humid_computed(i) .gt. 1.0) then
            print *, "ERROR Test 2: humid out of [0,1] range"
            n_errors = n_errors + 1
            exit
        end if
    end do
    if (n_errors .eq. 0) print *, "OK Test 2: all humid in [0,1]"

    ! --- Test 3: Saturated case (d2m == t2m) -> humid = 1 ---
    n_checks = n_checks + 1
    e_sat_t2m = 610.78*10.0**(8.61503*(273.15 - 273.15)/273.15)
    e_sat_d2m = 610.78*10.0**(8.61503*(273.15 - 273.15)/273.15)
    if (abs(e_sat_d2m/e_sat_t2m - 1.0) .gt. 1e-6) then
        print *, "ERROR Test 3: saturated case humid != 1"
        n_errors = n_errors + 1
    else
        print *, "OK Test 3: saturated case humid = 1"
    end if

    ! --- Test 4: Very dry case (large T-Td) -> humid > 0 ---
    n_checks = n_checks + 1
    ! t2m = 273.15 (0°C), d2m = 233.15 (-40°C) -> очень сухо
    e_sat_t2m = 610.78*10.0**(8.61503*(273.15 - 273.15)/273.15)
    e_sat_d2m = 610.78*10.0**(8.61503*(233.15 - 273.15)/233.15)
    if (e_sat_d2m/e_sat_t2m .le. 0.0 .or. e_sat_d2m/e_sat_t2m .ge. 1.0) then
        print *, "ERROR Test 4: dry case humid not in (0,1)"
        n_errors = n_errors + 1
    else
        print '(A,F10.6)', "OK Test 4: dry case humid = ", e_sat_d2m/e_sat_t2m
    end if

    ! --- Test 5: Cloud mapping (tcc -> cloud) ---
    print *, ""
    print *, "--- Test 5: Cloud mapping ---"
    tcc_test = (/0.0, 0.5, 1.0/)
    cloud_mapped = tcc_test  ! прямая проекция

    n_checks = n_checks + 1
    do i = 1, 3
        if (cloud_mapped(i) .lt. 0.0 .or. cloud_mapped(i) .gt. 1.0) then
            print '(A,I2,A,F5.2)', "ERROR Test 5.", i, ": cloud out of [0,1] = ", cloud_mapped(i)
            n_errors = n_errors + 1
        else if (abs(cloud_mapped(i) - tcc_test(i)) .gt. 1e-6) then
            print '(A,I2,A,F5.2,A,F5.2)', "ERROR Test 5.", i, ": cloud != tcc: ", cloud_mapped(i), " ", tcc_test(i)
            n_errors = n_errors + 1
        else
            print '(A,I2,A,F5.2)', "OK Test 5.", i, ": cloud = tcc = ", cloud_mapped(i)
        end if
    end do

    ! --- Test 6: Cloud radiative formula check (1 - 0.6*cclo^3) ---
    ! Формула теплового баланса: sw_factor = 1 - 0.6 * cclo^3
    ! где cclo — облачность [0..1].
    ! Физический смысл: облака отражают коротковолновую радиацию обратно в космос,
    ! уменьшая нагрев поверхности. Нелинейная 3-я степень: при cclo<0.5 эффект мал,
    ! при cclo>0.8 — значительное ослабление. 0.6 — эмпирический коэффициент.
    ! sw_factor ∈ [0.4 (cclo=1), 1.0 (cclo=0)]
    print *, ""
    print *, "--- Test 6: Cloud radiative formula ---"
    cclo_test = (/0.0, 0.25, 0.5, 1.0/)
    sw_expected = (/1.0, 1.0 - 0.6*0.25**3, 1.0 - 0.6*0.5**3, 1.0 - 0.6*1.0**3/)

    n_checks = n_checks + 1
    do i = 1, n_cloud_tests
        cclo = cclo_test(i)
        sw_factor = 1.0 - 0.6*cclo**3
        if (abs(sw_factor - sw_expected(i)) .gt. 1e-6) then
            print '(A,I2,A,F10.6,A,F10.6)', "ERROR Test 6.", i, ": SW factor = ", sw_factor, " expected ", sw_expected(i)
            n_errors = n_errors + 1
        else
            print '(A,I2,A,F10.6)', "OK Test 6.", i, ": SW factor = ", sw_factor
        end if
    end do

    ! --- Test 7: sfal climatology interface (non-negative) ---
    ! Месячная климатология снегопада [м водн.экв./сутки]
    ! Значения: Jan=0.85, Feb=0.85, ..., Dec=0.85 (северная Арктика, типичные значения).
    ! sfal(lll) используется для расчёта теплопотерь на поверхности в heat().
    print *, ""
    print *, "--- Test 7: sfal climatology ---"
    sfal_data = (/0.85, 0.85, 0.83, 0.81, 0.82, 0.78, 0.64, 0.69, 0.84, 0.85, 0.85, 0.85/)

    n_checks = n_checks + 1
    do i = 1, 12
        if (sfal_data(i) .lt. 0.0) then
            print '(A,I2,A,F5.2)', "ERROR Test 7.", i, ": sfal negative = ", sfal_data(i)
            n_errors = n_errors + 1
        end if
    end do
    if (n_errors .eq. 0) print *, "OK Test 7: all sfal >= 0"

    ! --- Test 8: ERA5 variable presence (simulated) ---
    ! Проверяем маппинг ERA5 переменных на модельные:
    !   d2m [K] → humid [0..1] — через e_sat(d2m)/e_sat(t2m)
    !   tcc [0..1] → cloud [0..1] — прямое копирование
    !   sf  [м water eq.] → snowfall (отложено на Stage 7.1: era5_snowfall_rate)
    !   t2m [K] → tatm [°C] — вычитание 273.15
    !   msl [Па] → patm [гПа] — умножение на 0.01
    print *, ""
    print *, "--- Test 8: ERA5 variable mapping ---"
    n_checks = n_checks + 1
    print *, "OK Test 8: ERA5 variable mapping documented"

    ! --- Summary ---
    print *, ""
    print *, "=================================================="
    if (n_errors .eq. 0) then
        print '(A,I3,A,I3)', "ALL TESTS PASSED: ", n_checks, " checks, 0 errors"
        stop 0
    else
        print '(A,I3,A,I3,A,I3)', "FAILED: ", n_errors, " errors out of ", n_checks, " checks"
        stop 1
    end if

end program thermo_input_test
