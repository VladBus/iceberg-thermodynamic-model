module grid_masks
    use param
    implicit none

contains

    subroutine ikuv()
        ! Локальные переменные
        integer :: i, j, isum
        real :: gu1, gu2, gu3, gu4

        ! Первичная инициализация масок
        iku(:, :) = 4
        ikv(:, :) = 4

        ! --- Расчет маски IKU (для U-компоненты скорости) ---
        do j = 2, js1
            do i = 1, is1 - 1
                ! Пропуск ячеек суши
                if (abs(hu(i, j) - 8888.0) .lt. 1e-8) cycle

                gu1 = hv(i, j - 1)
                gu2 = hv(i, j)
                gu3 = hv(i + 1, j)
                gu4 = hv(i + 1, j - 1)

                isum = 4
                if (abs(gu1 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu2 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu3 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu4 - 8888.0) .lt. 1e-8) isum = isum - 1

                if (isum .eq. 0) isum = 1
                iku(i, j) = isum
            end do
        end do

        ! --- Расчет маски IKV (для V-компоненты скорости) ---
        do j = 1, js1 - 1
            do i = 2, is1
                ! Пропуск ячеек суши
                if (abs(hv(i, j) - 8888.0) .lt. 1e-8) cycle

                gu1 = hu(i - 1, j)
                gu2 = hu(i - 1, j + 1)
                gu3 = hu(i, j + 1)
                gu4 = hu(i, j)

                isum = 4
                if (abs(gu1 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu2 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu3 - 8888.0) .lt. 1e-8) isum = isum - 1
                if (abs(gu4 - 8888.0) .lt. 1e-8) isum = isum - 1

                if (isum .eq. 0) isum = 1
                ikv(i, j) = isum
            end do
        end do

        ! Диагностический вывод (закомментирован, так как в FPM файловый вывод
        ! лучше настраивать централизованно, а unit 2 пока не открыт)
        ! write(2, '(105I1)') ((iku(i, j), j=1, js1), i=1, is1)
        ! write(2, '(105I1)') ((ikv(i, j), j=1, js1), i=1, is1)

    end subroutine ikuv

end module grid_masks
