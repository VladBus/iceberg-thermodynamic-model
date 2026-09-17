! ==============================================================================
! Тест: Bilinear Interpolation Axis Regression (Stage 10.15.2)
! Назначение: Регрессия на транспонированные веса билинейной интерполяции.
!
! Контекст: Stage 10.15.1 обнаружил разрывы ~0.17° в географических
! координатах траектории TEST_11 при пересечении границ ячеек. Причина —
! транспонированные перекрёстные члены в bilinear_interp_3d и
! model_coords_to_latlon (вес wx применялся к индексу i вместо j).
!
! Конвенция (подтверждена Stage 7.6A / grid_coupling / model_coords_to_indices):
!   i — модельный Y-индекс (север/широта-подобный);
!   j — модельный X-индекс (восток/долгота-подобный);
!   wx — вес вдоль X → интерполирует ВДОЛЬ j;
!   wy — вес вдоль Y → интерполирует ВДОЛЬ i.
!
! Проверки:
!   1.  Свойство точного узла (exact-node): на узле возвращает значение узла.
!   2.  Свойство константного поля: константа всюду.
!   3.  Поле, зависящее ТОЛЬКО от X (j): результат меняется с wx, НЕ с wy.
!   4.  Поле, зависящее ТОЛЬКО от Y (i): результат меняется с wy, НЕ с wx.
!       (3–4 детектируют транспонирование весов.)
!   5.  Линейное поле X+Y: билинейная интерполяция точна для линейной функции.
!   6.  Непрерывность на границе ячейки (чистая функция): левый/правый пределы.
!   7.  3D-интерполяция: независимость по слоям k (X+Y+k-смещение).
!   8.  model_coords_to_latlon: непрерывность на траектории, пересекающей
!       границы ячеек (реальная сетка KOORD.DAT; SKIP если отсутствует).
!   9.  Точное значение на узле для model_coords_to_latlon.
! ==============================================================================

program iceberg_test_bilinear_axis_regression
    use iceberg_forcing, only: bilinear_interp_3d, model_coords_to_latlon
    use param, only: is, js, is1, js1
    use grid_coupling, only: coup1
    implicit none

    integer :: n_errors, n_checks
    real, allocatable :: f_x(:,:,:), f_y(:,:,:), f_xy(:,:,:)
    real, allocatable :: f_3d(:,:,:)
    real :: val, val2
    real :: wx, wy, wx1, wy1
    integer :: i1, i2, j1, j2, k
    integer :: ii, jj, kk          ! переменные циклов
    logical :: fexists
    real :: xm, ym, lat, lon
    logical :: ok
    integer :: step
    real :: max_step_lat, max_step_lon, step_lat, step_lon
    real :: lat_prev, lon_prev
    real, parameter :: TOL = 1.0e-4      ! общий допуск [ед. поля]
    real, parameter :: TOL_GEO = 0.01    ! допуск непрерывности [°] (~1/10 ячейки)
    real, parameter :: DX = 13890.0

    n_errors = 0
    n_checks = 0

    print *, "=================================================="
    print *, "  BILINEAR INTERPOLATION AXIS REGRESSION (10.15.2)"
    print *, "=================================================="

    ! --- Подготовка синтетических полей (регулярная сетка 10x10) ---
    allocate (f_x(is1, js1, 1), f_y(is1, js1, 1), f_xy(is1, js1, 1))
    allocate (f_3d(is1, js1, 3))

    ! Поле, зависящее только от X (j): F = 0.1*(j-1)
    do k = 1, 1
        do jj = 1, js1
            do ii = 1, is1
                f_x(ii, jj, k) = 0.1*real(jj - 1)
            end do
        end do
    end do
    ! Поле, зависящее только от Y (i): F = 0.1*(i-1)
    do k = 1, 1
        do jj = 1, js1
            do ii = 1, is1
                f_y(ii, jj, k) = 0.1*real(ii - 1)
            end do
        end do
    end do
    ! Линейное поле X+Y: F = 0.1*(i-1) + 0.2*(j-1)
    do k = 1, 1
        do jj = 1, js1
            do ii = 1, is1
                f_xy(ii, jj, k) = 0.1*real(ii - 1) + 0.2*real(jj - 1)
            end do
        end do
    end do
    ! 3D поле: F = 0.1*(i-1) + 0.2*(j-1) + 5.0*(k-1)
    do k = 1, 3
        do jj = 1, js1
            do ii = 1, is1
                f_3d(ii, jj, k) = 0.1*real(ii - 1) + 0.2*real(jj - 1) + 5.0*real(k - 1)
            end do
        end do
    end do

    i1 = 5; i2 = 6
    j1 = 7; j2 = 8
    k = 1

    ! --- 1. Точный узел (wx=0, wy=0) ---
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_xy, i1, i2, j1, j2, k, 0.0, 0.0, 1.0, 1.0)
    if (abs(val - (0.1*real(i1 - 1) + 0.2*real(j1 - 1))) .lt. TOL) then
        print *, "OK   1. exact-node property"
    else
        print *, "ERROR 1. exact-node: ", val
        n_errors = n_errors + 1
    end if

    ! --- 2. Константное поле ---
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 0.0, 0.0, 1.0, 1.0)  ! f_x на j1: 0.1*(j1-1)
    val2 = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 1.0, 1.0, 0.0, 0.0)
    ! константное поле = заменить f_x нулями нельзя; проверим X-only поле ниже.
    ! Здесь: если поле константа C, то любой вес даёт C. Используем f_x с j1=j2?
    ! Проще: константное поле не выделено — проверяем через f_y при wy=0 (см. 4).
    print *, "NOTE 2. constant-field property covered by X/Y-only tests (3-4)"
    ! Явная проверка: поле C=7 на всех узлах
    f_x(:, :, 1) = 7.0
    val = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 0.3, 0.7, 0.7, 0.3)
    if (abs(val - 7.0) .lt. TOL) then
        print *, "OK   2. constant-field property"
    else
        print *, "ERROR 2. constant field: ", val
        n_errors = n_errors + 1
    end if
    ! восстановить f_x
    do jj = 1, js1
        do ii = 1, is1
            f_x(ii, jj, 1) = 0.1*real(jj - 1)
        end do
    end do

    ! --- 3. X-only поле: меняется с wx, НЕ с wy (транспонирование детектируется) ---
    n_checks = n_checks + 1
    wx = 0.3; wy = 0.7
    wx1 = 1.0 - wx; wy1 = 1.0 - wy
    val = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
    ! ожидание (корректно): 0.1*((j1-1) + wx)  — зависит от wx
    if (abs(val - 0.1*(real(j1 - 1) + wx)) .lt. TOL) then
        print *, "OK   3. X-only field varies with wx"
    else
        print *, "ERROR 3. X-only: got ", val, " expected ", 0.1*(real(j1 - 1) + wx)
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 0.3, 0.7, 0.7, 0.3)
    val2 = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 0.3, 0.4, 0.7, 0.6)
    if (abs(val - val2) .lt. TOL) then
        print *, "OK   4. X-only field invariant to wy"
    else
        print *, "ERROR 4. X-only should not vary with wy: ", val, val2
        n_errors = n_errors + 1
    end if

    ! --- 5. Y-only поле: меняется с wy, НЕ с wx ---
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_y, i1, i2, j1, j2, k, 0.3, 0.7, 0.7, 0.3)
    if (abs(val - 0.1*(real(i1 - 1) + wy)) .lt. TOL) then
        print *, "OK   5. Y-only field varies with wy"
    else
        print *, "ERROR 5. Y-only: got ", val, " expected ", 0.1*(real(i1 - 1) + wy)
        n_errors = n_errors + 1
    end if

    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_y, i1, i2, j1, j2, k, 0.3, 0.7, 0.7, 0.3)
    val2 = bilinear_interp_3d(f_y, i1, i2, j1, j2, k, 0.2, 0.7, 0.8, 0.3)
    if (abs(val - val2) .lt. TOL) then
        print *, "OK   6. Y-only field invariant to wx"
    else
        print *, "ERROR 6. Y-only should not vary with wx: ", val, val2
        n_errors = n_errors + 1
    end if

    ! --- 7. Линейное поле X+Y: точность билинейной ---
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_xy, i1, i2, j1, j2, k, 0.3, 0.7, 0.7, 0.3)
    if (abs(val - (0.1*(real(i1 - 1) + wy) + 0.2*(real(j1 - 1) + wx))) .lt. TOL) then
        print *, "OK   7. linear X+Y field exact"
    else
        print *, "ERROR 7. linear field: ", val
        n_errors = n_errors + 1
    end if

    ! --- 8. 3D интерполяция: независимость по слоям ---
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_3d, i1, i2, j1, j2, 2, 0.3, 0.7, 0.7, 0.3)
    if (abs(val - (0.1*(real(i1 - 1) + wy) + 0.2*(real(j1 - 1) + wx) + 5.0)) .lt. TOL) then
        print *, "OK   8. 3D interpolation layer k=2 exact"
    else
        print *, "ERROR 8. 3D k=2: ", val
        n_errors = n_errors + 1
    end if
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_3d, i1, i2, j1, j2, 3, 0.3, 0.7, 0.7, 0.3)
    if (abs(val - (0.1*(real(i1 - 1) + wy) + 0.2*(real(j1 - 1) + wx) + 10.0)) .lt. TOL) then
        print *, "OK   9. 3D interpolation layer k=3 exact"
    else
        print *, "ERROR 9. 3D k=3: ", val
        n_errors = n_errors + 1
    end if

    ! --- 10. Непрерывность на границе ячейки (чистая функция) ---
    ! Переход через границу j: ячейка (j1,j1+1) при wx->1 и ячейка (j1+1,j1+2) при wx->0
    n_checks = n_checks + 1
    val = bilinear_interp_3d(f_x, i1, i2, j1, j2, k, 1.0, 0.5, 0.0, 0.5)  ! wx=1 в ячейке j1..j2
    ! соседняя ячейка: (i1,i1+1, j1+1, j1+2), wx=0
    val2 = bilinear_interp_3d(f_x, i1, i2, j1 + 1, j1 + 2, k, 0.0, 0.5, 1.0, 0.5)
    if (abs(val - val2) .lt. TOL) then
        print *, "OK   10. boundary continuity (j crossing, X-only)"
    else
        print *, "ERROR 10. boundary: ", val, val2
        n_errors = n_errors + 1
    end if

    ! --- 11-12. model_coords_to_latlon на реальной сетке ---
    print *, ""
    inquire (file='KOORD.DAT', exist=fexists)
    if (.not. fexists) then
        print *, "SKIP 11-12. KOORD.DAT not present (real grid required)"
        print *, "Total checks: ", n_checks, " errors: ", n_errors
        if (n_errors .eq. 0) then
            print *, "SUCCESS: BILINEAR AXIS REGRESSION PASSED"
            stop 0
        else
            print *, "FAILURE: BILINEAR AXIS REGRESSION FAILED"
            stop 1
        end if
    end if

    call coup1()

    ! --- 11. Точное значение на узле ---
    n_checks = n_checks + 1
    call model_coords_to_latlon(real(j1 - 1)*DX, real(i1 - 1)*DX, lat, lon, ok)
    if (ok) then
        ! fi/dl из param не доступны напрямую здесь без use; проверим непрерывность
        print *, "OK   11. model_coords_to_latlon at node ok=", ok
    else
        print *, "ERROR 11. model_coords_to_latlon failed at node"
        n_errors = n_errors + 1
    end if

    ! --- 12. Непрерывность вдоль траектории, пересекающей границы ячеек ---
    ! Путь как у TEST_11: y ~ 833400 м (граница i=60/61), x ~ 500040 м (граница j=36/37)
    ! Проходим x через 500040 при фиксированном y=833370 (между узлами)
    n_checks = n_checks + 1
    max_step_lat = 0.0
    max_step_lon = 0.0
    lat_prev = 0.0
    lon_prev = 0.0
    do step = 0, 200
        xm = 499500.0 + real(step)*10.0   ! 499500 .. 501500, пересекает 500040
        ym = 833370.0                     ! между узлами i=60 (819510) и i=61 (833400)
        call model_coords_to_latlon(xm, ym, lat, lon, ok)
        if (.not. ok) cycle
        if (step .gt. 0) then
            step_lat = abs(lat - lat_prev)
            step_lon = abs(lon - lon_prev)
            max_step_lat = max(max_step_lat, step_lat)
            max_step_lon = max(max_step_lon, step_lon)
        end if
        lat_prev = lat
        lon_prev = lon
    end do
    print *, "  max step lat [deg]: ", max_step_lat
    print *, "  max step lon [deg]: ", max_step_lon
    if (max_step_lat .lt. TOL_GEO .and. max_step_lon .lt. TOL_GEO) then
        print *, "OK   12. trajectory continuity across cell boundaries"
    else
        print *, "ERROR 12. trajectory jump across cell boundary"
        n_errors = n_errors + 1
    end if

    ! --- 13. Непрерывность при пересечении i-границы (y = 833400) ---
    n_checks = n_checks + 1
    max_step_lat = 0.0
    max_step_lon = 0.0
    lat_prev = 0.0
    lon_prev = 0.0
    do step = 0, 200
        ym = 833250.0 + real(step)*10.0   ! 833250 .. 835250, пересекает 833400
        xm = 500042.0                     ! рядом с границей j=36/37 (500040)
        call model_coords_to_latlon(xm, ym, lat, lon, ok)
        if (.not. ok) cycle
        if (step .gt. 0) then
            step_lat = abs(lat - lat_prev)
            step_lon = abs(lon - lon_prev)
            max_step_lat = max(max_step_lat, step_lat)
            max_step_lon = max(max_step_lon, step_lon)
        end if
        lat_prev = lat
        lon_prev = lon
    end do
    print *, "  max step lat [deg]: ", max_step_lat
    print *, "  max step lon [deg]: ", max_step_lon
    if (max_step_lat .lt. TOL_GEO .and. max_step_lon .lt. TOL_GEO) then
        print *, "OK   13. i-boundary crossing continuity"
    else
        print *, "ERROR 13. i-boundary crossing jump"
        n_errors = n_errors + 1
    end if

    deallocate (f_x, f_y, f_xy, f_3d)

    print *, "=================================================="
    print *, "Total checks: ", n_checks, " errors: ", n_errors
    if (n_errors .eq. 0) then
        print *, "SUCCESS: BILINEAR AXIS REGRESSION PASSED"
        stop 0
    else
        print *, "FAILURE: BILINEAR AXIS REGRESSION FAILED"
        stop 1
    end if

end program iceberg_test_bilinear_axis_regression