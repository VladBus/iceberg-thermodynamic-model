module initial_conditions
    use param
    implicit none

contains

    subroutine init_ocean()
        integer :: i, j, k
        real :: depth_ratio

        print *, ">>> Initializing synthetic ocean conditions..."

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

                        ! 2. Соленость: растет от 33 до 35 промилле ко дну
                        s2(i, j, k) = 33.0 + 2.0*depth_ratio
                        s1(i, j, k) = s2(i, j, k)

                        ! 3. Аномалия: создаем 3D "горячее пятно" в центре (с 50 по 80 ячейку)
                  if (i .gt. 50 .and. i .lt. 80 .and. j .gt. 40 .and. j .lt. 60 .and. k .le. 5) then
                            t2(i, j, k) = t2(i, j, k) + 8.0  ! Нагреваем на 8 градусов
                            t1(i, j, k) = t2(i, j, k)
                        end if

                        ! 4. Задаем фоновое течение (например, 20 см/с по X и 10 см/с по Y)
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
