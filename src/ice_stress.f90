module ice_stress
    use param
    implicit none

contains

    subroutine stress()
        integer :: i, j, i1, j1, k, k_crit
        real :: a, b, a1, a2, b1, b2, sor, cor, ssxx, ssyy, ssxy
        real :: scrit, angl

        ! --- БЛОК ПОДГОТОВКИ ПОЛЕЙ ---
        ! Здесь мы перебрасываем массивы напряжений через массив EPR.
        ! Вызовы call deform() закомментированы до создания соответствующего модуля.

        do j = 1, js
            do i = 1, is
                i1 = i + 1
                epr(i1, j + 1) = exx(i, j)
            end do
        end do

        ! call deform() ! TODO: Раскомментировать после создания модуля deform

        do j = 1, js
            j1 = j + 1
            do i = 1, is
                i1 = i + 1
                exx(i, j) = epr(i1, j1)
                epr(i1, j1) = eyy(i, j)
            end do
        end do

        ! call deform() ! TODO: Раскомментировать после создания модуля deform

        do j = 1, js
            j1 = j + 1
            do i = 1, is
                i1 = i + 1
                eyy(i, j) = epr(i1, j1)
                epr(i1, j1) = exy(i, j)
            end do
        end do

        ! call deform() ! TODO: Раскомментировать после создания модуля deform

        do j = 1, js
            do i = 1, is
                i1 = i + 1
                exy(i, j) = epr(i1, j + 1)
            end do
        end do

        ! --- ОСНОВНОЙ ЦИКЛ РАСЧЕТА НАПРЯЖЕНИЙ ---

        do j = 1, js
            do i = 1, is
                ! Пропуск суши
                if (kt1(i, j) .eq. 0) cycle

                ! Если сплошность льда меньше 95%, напряжения обнуляются (лед дрейфует свободно)
                if (ans(i, j) .lt. 0.95) then
                    exx(i, j) = 0.0
                    eyy(i, j) = 0.0
                    exy(i, j) = 0.0
                    sxx(i, j) = 0.0
                    syy(i, j) = 0.0
                    sxy(i, j) = 0.0
                    cycle
                end if

                a = exx(i, j) + eyy(i, j)
                b = (sxx(i, j) + syy(i, j))*0.5

                ! Проверка на растяжение/расхождение льда
                if (a .gt. 0.0 .and. b .ge. 0.0) then
                    exx(i, j) = 0.0
                    eyy(i, j) = 0.0
                    exy(i, j) = 0.0
                    sxx(i, j) = 0.0
                    syy(i, j) = 0.0
                    sxy(i, j) = 0.0
                    cycle
                end if

                ! Расчет компонент тензора напряжений
                ssxx = exx(i, j)*1.e7
                ssyy = eyy(i, j)*1.e7
                ssxy = exy(i, j)*1.e7

                a = (ssxx + ssyy)*0.5
                b1 = (ssxx - ssyy)*0.5
                b2 = sqrt(b1*b1 + ssxy*ssxy)

                a1 = a + b2
                a2 = a - b2

                ! Поиск критической категории толщины льда
                k_crit = 2
                do k = 2, ngr
                    if (an1(i, j, k + 1) .gt. 0.05) then
                        k_crit = k
                        exit
                    end if
                end do

                ! Вычисление предела прочности
                scrit = -0.43e5*hst(k_crit)**2

                ! Проверка условия пластичности / хрупкого разрушения
                if (a2 .gt. scrit .and. a1 .lt. 0.0) then
                    ! Эквивалент GOTO 4 из старого кода (сохранение текущих напряжений)
                    sxx(i, j) = ssxx
                    syy(i, j) = ssyy
                    sxy(i, j) = ssxy
                    cycle
                end if

                ! Корректировка главных напряжений
                if (a2 .lt. scrit) a2 = scrit
                if (a1 .lt. scrit) a1 = scrit
                if (a1 .gt. 0.0) a1 = 0.0
                if (a2 .gt. 0.0) a2 = 0.0

                ! Расчет угла внутреннего трения и функций от него
                angl = atan2(ssxy, b1)*0.5
                cor = cos(-angl)
                sor = sin(-angl)

                ! Финальный пересчет тензоров
                sxx(i, j) = a1*cor*cor + a2*sor*sor
                syy(i, j) = a1*sor*sor + a2*cor*cor
                sxy(i, j) = -(a1 - a2)*cor*sor

                exx(i, j) = sxx(i, j)*1.e-7
                eyy(i, j) = syy(i, j)*1.e-7
                exy(i, j) = sxy(i, j)*1.e-7

            end do
        end do

    end subroutine stress

end module ice_stress
