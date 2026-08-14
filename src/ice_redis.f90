! ==============================================================================
! Модуль: ice_redis (redis)
! Назначение: Перераспределение массы льда по категориям толщины.
! Физика: Реализует эволюцию функции распределения толщины льда 
!         (Ice Thickness Distribution), предложенную Торндайком. Термодинамика смещает 
!         лед между категориями толщины, в то время как динамическая конвергенция 
!         (торошение) трансформирует площади тонких льдов в меньшие площади толстых 
!         торосов, строго сохраняя общий объем льда в ячейке.
! Ответственность: Формирование сил сопротивления сжатию и сдвигу, передача 
!                  информации о торошении в модуль перераспределения массы.
! ==============================================================================

module ice_redis
    use param
    implicit none

contains

    subroutine redis()
        integer :: i, j, k, k1, k2
        real :: a, b, a1, a2, a3, b1, b2, b3, dd

        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0) cycle

                ! 1. Подготовка категорий
                do k = 1, ngr
                    hice(i, j, k) = 0.0
                    wicpr(k) = wice1(i, j, k)
                    anpr(k) = an1(i, j, k + 1)
                    hsnp(k) = hsnow(i, j, k)

                    if (wicpr(k) .le. 0.0 .or. anpr(k) .le. 0.0) then
                        wicpr(k) = 0.0
                        anpr(k) = 0.0
                        hsnp(k) = 0.0
                    end if
                end do

                ! 2. Перенос льда в более толстые категории
                do k = 1, ngr2
                    k1 = k + 1
                    if (abs(wicpr(k)) .gt. 1e-8) then
                        if (abs(anpr(k)) .lt. 1e-8) anpr(k) = wicpr(k)/hst(k)
                        if (wicpr(k)/anpr(k) .gt. hmax(k)) then
                            anpr(k1) = anpr(k1) + anpr(k)
                            wicpr(k1) = wicpr(k1) + wicpr(k)
                            hsnp(k1) = hsnp(k1) + hsnp(k)
                            wicpr(k) = 0.0
                            anpr(k) = 0.0
                            hsnp(k) = 0.0
                        end if
                    end if
                end do

                ! 3. Перенос льда в более тонкие категории
                do k = ngr, 2, -1
                    if (wicpr(k) .gt. 0.0) then
                        k2 = k - 1
                        if (wicpr(k)/anpr(k) .lt. hmax(k2)) then
                            wicpr(k2) = wicpr(k2) + wicpr(k)
                            anpr(k2) = anpr(k2) + anpr(k)
                            wicpr(k) = 0.0
                            anpr(k) = 0.0
                        end if
                    end if
                end do

                ! 4. Расчет средних толщин (HPR)
                do k = 1, ngr
                    if (abs(anpr(k)) .gt. 1e-8) then
                        hpr(k) = wicpr(k)/anpr(k)
                    else
                        hpr(k) = 0.0
                    end if
                end do

                ! 5. Контроль максимальной площади (сплошности) льда
                redistribution_loop: do
                    a1 = 0.0
                    do k = 1, ngr
                        a1 = a1 + anpr(k)
                    end do

                    ! Если сплошность <= 1.0, выходим из цикла балансировки (эквивалент GOTO 315)
                    if (a1 .le. 1.0) exit redistribution_loop

                    dd = a1 - 1.0
                    a3 = wicpr(1)
                    b3 = 1.0

                    do k = 2, ngr
                        b3 = b3 - anpr(k)
                    end do

                    inner_loop: do k = 1, ngr2
                        k1 = k + 1
                        a3 = a3 + wicpr(k1)
                        b3 = b3 + anpr(k1)

                        if (abs(anpr(k)) .lt. 1e-8) cycle inner_loop

                        if (abs(anpr(k1)) .lt. 1e-8) then
                            if (dd .lt. anpr(k)) then
                                anpr(k) = anpr(k) - dd
                                exit redistribution_loop
                            else
                                wicpr(k1) = wicpr(k)
                                anpr(k1) = wicpr(k)/hst(k1)
                                hpr(k1) = wicpr(k1)/anpr(k1)
                                wicpr(k) = 0.0
                                anpr(k) = 0.0
                                hpr(k) = 0.0
                            end if
                            ! Пересчет сначала (эквивалент GOTO 319)
                            cycle redistribution_loop
                        end if

                        a = hpr(k) - hpr(k1)
                        if (abs(a) .gt. 1e-8) then
                            b2 = (a3 - hpr(k1)*b3)/a
                            a2 = (hpr(k)*b3 - a3)/a
                        else
                            b2 = -1.0
                            a2 = -1.0
                        end if

                        if (b2 .lt. 0.0 .or. a2 .lt. 0.0) then
                            anpr(k) = 0.0
                        else
                            anpr(k) = b2
                            anpr(k1) = a2
                            exit redistribution_loop
                        end if
                    end do inner_loop

                    ! Если цикл дошел до конца
                    anpr(ngr) = 1.0
                    wicpr(ngr) = a3
                    exit redistribution_loop
                end do redistribution_loop

                ! 6. Финальное обновление глобальных массивов
                a1 = 0.0
                b1 = 0.0
                do k = 1, ngr
                    if (abs(anpr(k)) .lt. 1e-8) wicpr(k) = 0.0
                    a1 = a1 + anpr(k)
                    b1 = b1 + wicpr(k)
                    an1(i, j, k + 1) = anpr(k)
                    wice1(i, j, k) = wicpr(k)
                    hsnow(i, j, k) = hsnp(k)
                    if (abs(anpr(k)) .gt. 1e-8) hice(i, j, k) = wicpr(k)/anpr(k)
                end do

                do k = ngr, 2, -1
                    k2 = k - 1
                    if (hice(i, j, k) .lt. hmax(k2)) then
                        k1 = k + 1
                        a = an1(i, j, k) + an1(i, j, k1)
                        an1(i, j, k) = a
                        b = wice1(i, j, k2) + wice1(i, j, k)
                        wice1(i, j, k2) = b
                        if (abs(a) .gt. 1e-8) hice(i, j, k2) = b/a
                        an1(i, j, k1) = 0.0
                        wice1(i, j, k) = 0.0
                        hice(i, j, k) = 0.0
                    end if
                end do

                ans(i, j) = a1
                wices(i, j) = b1

                if (a1 .ge. 0.005) then
                    hices(i, j) = b1/a1
                else
                    ans(i, j) = 0.0
                    hices(i, j) = 0.0
                    wices(i, j) = 0.0
                end if
                an1(i, j, 1) = 1.0 - a1

            end do
        end do

    end subroutine redis

end module ice_redis
