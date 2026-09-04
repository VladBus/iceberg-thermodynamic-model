! ==============================================================================
! Тест: Artificial Forcing Interpolation Test
! Назначение: Проверка билинейной интерполяции на аналитической функции
!             F(lat, lon) = a*lat + b*lon, где точное значение известно
! ==============================================================================

program iceberg_test_artificial_forcing
    use iceberg_forcing, only: bilinear_interp_3d
    use param, only: is, js, is1, js1
    implicit none

    integer :: n_errors, n_checks
    integer :: i, j
    real, allocatable :: test_field(:, :, :)
    real :: exact_val, interp_val
    real :: a, b
    real :: lat, lon
    real :: x_model, y_model
    integer :: i1, i2, j1, j2, k
    real :: wx, wy, wx1, wy1

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  ARTIFICIAL FORCING INTERPOLATION TEST"
    print *, "=================================================="

    ! 1. Создаем аналитическое поле на модельной сетке
    ! F(i,j) = a*fi(i,j) + b*dl(i,j)
    ! Но нам нужно поле в 3D (i,j,k) для bilinear_interp_3d
    ! Используем k=1 слой

    allocate (test_field(is1, js1, 1))

    ! Константы для линейной функции
    a = 0.5
    b = -0.3

    ! Заполняем поле значением a*lat + b*lon в каждой точке
    ! Но у нас нет fi/dl в этом тесте (требует coup1)
    ! Поэтому создадим синтетическую регулярную сетку

    ! Синтетическая регулярная сетка: lat = 70 + i*0.1, lon = 20 + j*0.1
    do k = 1, 1
        do j = 1, js1
            do i = 1, is1
                lat = 70.0 + real(i - 1)*0.1
                lon = 20.0 + real(j - 1)*0.1
                test_field(i, j, k) = a*lat + b*lon
            end do
        end do
    end do

    ! 2. Тест интерполяции в нескольких точках
    print *, "Testing bilinear interpolation of F(lat,lon) = ", a, "*lat + ", b, "*lon"

    ! Тест 1: Точка в узле сетки (должна дать точное значение)
    i1 = 50; i2 = 51; j1 = 30; j2 = 31; k = 1
    lat = 70.0 + real(i1 - 1)*0.1
    lon = 20.0 + real(j1 - 1)*0.1
    exact_val = a*lat + b*lon
    interp_val = bilinear_interp_3d(test_field, i1, i2, j1, j2, k, 0.0, 0.0, 1.0, 1.0)
    print *, "Test 1: At grid node (wx=0,wy=0)"
    print *, "  Exact: ", exact_val, " Interp: ", interp_val
    if (abs(interp_val - exact_val) .lt. 1.0e-6) then
        print *, "  OK: Exact match at grid node"
    else
        print *, "  ERROR: Mismatch at grid node"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! Тест 2: Центр ячейки (wx=0.5, wy=0.5)
    lat = 70.0 + real(i1 - 1)*0.1 + 0.05
    lon = 20.0 + real(j1 - 1)*0.1 + 0.05
    exact_val = a*lat + b*lon
    interp_val = bilinear_interp_3d(test_field, i1, i2, j1, j2, k, 0.5, 0.5, 0.5, 0.5)
    print *, "Test 2: At cell center (wx=0.5, wy=0.5)"
    print *, "  Exact: ", exact_val, " Interp: ", interp_val
    ! Билинейная интерполяция линейной функции должна быть точной (до ошибок округления)
    if (abs(interp_val - exact_val) .lt. 1.0e-5) then
        print *, "  OK: Exact match at cell center (bilinear = exact for linear)"
    else
        print *, "  ERROR: Mismatch at cell center"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! Тест 3: Произвольная точка внутри ячейки
    wx = 0.3
    wy = 0.7
    wx1 = 1.0 - wx
    wy1 = 1.0 - wy
    lat = 70.0 + real(i1 - 1)*0.1 + wx*0.1
    lon = 20.0 + real(j1 - 1)*0.1 + wy*0.1
    exact_val = a*lat + b*lon
    interp_val = bilinear_interp_3d(test_field, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
    print *, "Test 3: At arbitrary point (wx=0.3, wy=0.7)"
    print *, "  Exact: ", exact_val, " Interp: ", interp_val
    if (abs(interp_val - exact_val) .lt. 1.0e-6) then
        print *, "  OK: Exact match for bilinear = linear function"
    else
        print *, "  ERROR: Mismatch at arbitrary point"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! Тест 4: Проверка на краях ячейки (wx=0, wy=0.5)
    wx = 0.0
    wy = 0.5
    wx1 = 1.0
    wy1 = 0.5
    lat = 70.0 + real(i1 - 1)*0.1
    lon = 20.0 + real(j1 - 1)*0.1 + wy*0.1
    exact_val = a*lat + b*lon
    interp_val = bilinear_interp_3d(test_field, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
    print *, "Test 4: At edge (wx=0, wy=0.5)"
    print *, "  Exact: ", exact_val, " Interp: ", interp_val
    if (abs(interp_val - exact_val) .lt. 1.0e-6) then
        print *, "  OK: Exact match at edge"
    else
        print *, "  ERROR: Mismatch at edge"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    ! Тест 5: Другой слой k (3D интерполяция работает покомпонентно)
    deallocate (test_field)
    allocate (test_field(is1, js1, 3))
    do k = 1, 3
        do j = 1, js1
            do i = 1, is1
                lat = 70.0 + real(i - 1)*0.1
                lon = 20.0 + real(j - 1)*0.1
                test_field(i, j, k) = a*lat + b*lon + real(k)*10.0  ! смещение по слоям
            end do
        end do
    end do

    k = 2
    i1 = 10; i2 = 11; j1 = 20; j2 = 21
    wx = 0.25; wy = 0.75
    wx1 = 0.75; wy1 = 0.25
    lat = 70.0 + real(i1 - 1)*0.1 + wx*0.1
    lon = 20.0 + real(j1 - 1)*0.1 + wy*0.1
    exact_val = a*lat + b*lon + real(k)*10.0
    interp_val = bilinear_interp_3d(test_field, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
    print *, "Test 5: 3D field at layer k=2"
    print *, "  Exact: ", exact_val, " Interp: ", interp_val
    ! 3D интерполяция работает покомпонентно по k, поэтому должна быть точной для линейной ф-ции
    if (abs(interp_val - exact_val) .lt. 1.0e-5) then
        print *, "  OK: 3D interpolation works per layer"
    else
        print *, "  ERROR: 3D interpolation mismatch"
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1

    deallocate (test_field)

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: ARTIFICIAL FORCING INTERPOLATION TEST PASSED"
        stop 0
    else
        print *, "FAILURE: ARTIFICIAL FORCING INTERPOLATION TEST FAILED"
        stop 1
    end if

end program iceberg_test_artificial_forcing
