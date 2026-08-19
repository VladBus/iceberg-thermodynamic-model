! ==============================================================================
! Модуль: initial_conditions
! Назначение: Формирование детерминированного синтетического состояния океана.
! Физика: Задает тестовые T, S и 3D-течения до подключения начальных полей ERA5.
! Единицы: T [degC], S [массовая доля], U/V [см/с], глубина/уровень [см].
! ==============================================================================

module initial_conditions
    use param
    implicit none

contains

    subroutine init_ocean()
        integer :: i, j, k
        real :: depth_ratio

        print *, ">>> Initializing synthetic ocean conditions..."

        ! Обнуляем и активные, и ghost-узлы: транспорт читает i+1/j+1.
        t1 = 0.0
        t2 = 0.0
        s1 = 0.0
        s2 = 0.0
        u1 = 0.0
        u2 = 0.0
        v1 = 0.0
        v2 = 0.0
        w = 0.0
        ro = 0.0
        up1 = 0.0
        up2 = 0.0
        vp1 = 0.0
        vp2 = 0.0
        y1 = 0.0
        y2 = 0.0
        ym1 = 0.0
        ym2 = 0.0

        ! --- ЦИКЛ ПО ВЕРТИКАЛЬНЫМ УРОВНЯМ (K = 1..KS) ---
        do k = 1, ks
            ! Коэффициент глубины: от 0.0 (поверхность) до 1.0 (самое дно)
            depth_ratio = real(k - 1)/max(1.0, real(ks - 1))

            do j = 1, js
                do i = 1, is
                    ! Проверяем, что это вода, а не суша
                    if (kt1(i, j) .gt. 0 .and. k .le. kt1(i, j)) then
                        ! 1. Температура: падает от 15°C на поверхности до 2°C на дне
                        t2(i, j, k) = 15.0 - 13.0*depth_ratio
                        t1(i, j, k) = t2(i, j, k)

                        ! 2. Соленость [доля]: 0.033 соответствует 33 PSU.
                        s2(i, j, k) = 0.033 + 0.002*depth_ratio
                        s1(i, j, k) = s2(i, j, k)

                        ! 3. Аномалия: создаем 3D "горячее пятно" в центре (с 50 по 80 ячейку)
                  if (i .gt. 50 .and. i .lt. 80 .and. j .gt. 40 .and. j .lt. 60 .and. k .le. 5) then
                            t2(i, j, k) = t2(i, j, k) + 8.0  ! Нагреваем на 8 градусов
                            t1(i, j, k) = t2(i, j, k)
                        end if

                        ! 4. Фоновое течение [см/с]: 0.20 по X и 0.10 по Y.
                        u2(i, j, k) = 0.20
                        v2(i, j, k) = 0.10
                        u1(i, j, k) = u2(i, j, k)
                        v1(i, j, k) = v2(i, j, k)
                    else
                        ! Если суша, ставим нули
                        t2(i, j, k) = 0.0
                        s2(i, j, k) = 0.0
                        u2(i, j, k) = 0.0
                        v2(i, j, k) = 0.0
                    end if
                end do
            end do
        end do

    end subroutine init_ocean

end module initial_conditions
