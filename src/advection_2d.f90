module advection_2d
    use param
    implicit none

contains

    subroutine adv2d(dt, dx, c2)
        real, intent(in) :: dt, dx, c2

        integer :: i, j, i1, j1, i2, j2, i3, j3
        integer :: ix1, ix2, iy1, iy2, ki
        real :: up, um, uu, vp, vm, vv
        real :: cc, ci1, ci2, ci3, cj1, cj2, cj3
        real :: cdx, cdy, flxp, flyp, a1, b1, a, b

        ! Обнуление массивов
        apx2(:, :) = 0.0
        apy2(:, :) = 0.0

        ! --- X-COORDINATE ---

        ! Цикл 11 (Перенос субстанции)
        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0 .or. it(i, j) .ne. 0) cycle

                i1 = min(is1, i + 1)
                j1 = min(js1, j + 1)
                i2 = max(1, i - 1)
                j2 = max(1, j - 1)

                up = 50.0*(u(i, j1) + u(i1, j1))
                um = 50.0*(u(i, j) + u(i1, j))
                uu = 0.5*(up + um)
                vp = 50.0*(v(i1, j) + v(i1, j1))
                vm = 50.0*(v(i, j) + v(i, j1))
                vv = 0.5*(vp + vm)
                iy1 = idy(i1, j)
                ix1 = idx(i, j1)

                cc = an3(i, j)

                if (iy1 .eq. 0) then
                    ci1 = 0.0
                    i3 = i1
                else
                    ci1 = an3(i1, j)
                    i3 = min(is1, i + 2)
                end if

                if (idy(i, j) .eq. 0) then
                    ci2 = 0.0
                else
                    ci2 = an3(i2, j)
                end if

                if (ix1 .eq. 0) then
                    cj1 = 0.0
                    j3 = j1
                else
                    cj1 = an3(i, j1)
                    j3 = min(js1, j + 2)
                end if

                if (idx(i, j) .eq. 0) then
                    cj2 = 0.0
                else
                    cj2 = an3(i, j2)
                end if

                ! Расчет потока по X
                cdx = 0.0
                if (uu .gt. 0.0) then
                    cdx = (cc - cj2)*uu
                else
                    cdx = (cj1 - cc)*uu
                end if

                ! Эквивалент GOTO 201
                if (abs(cdx) .lt. 1e-8) then
                    if (um .gt. 0.0) cdx = (cc - cj2)*um
                    if (up .lt. 0.0) cdx = (cj1 - cc)*up
                end if

                cdx = cdx + cc*(up - um)*0.5

                ! Расчет потока по Y
                cdy = 0.0
                if (vv .gt. 0.0) then
                    cdy = (cc - ci1)*vv
                else
                    cdy = (ci2 - cc)*vv
                end if

                ! Эквивалент GOTO 202
                if (abs(cdy) .lt. 1e-8) then
                    if (vp .gt. 0.0) cdy = (cc - ci1)*vp
                    if (vm .lt. 0.0) cdy = (ci2 - cc)*vm
                end if

                cdy = cdy + cc*(vm - vp)*0.5

                ! Обновление CD2
                cd2(i, j) = cc - dt*(cdx + cdy)/dx

                ! Коррекция потоков
                if (ix1 .ne. 0) then
                    if (up .lt. 0.0) then
                        flxp = cj1*up
                    else
                        flxp = cc*up
                    end if

                    cj3 = 0.0
                    if (j .ne. js) then
                        j3 = min(js1, j + 2)
                        if (idx(i, j3) .ne. 0) cj3 = an3(i, j3)
                    end if
                    apx2(i, j1) = (up*(7.0*(cc + cj1) - (cj2 + cj3))/12.0 - flxp)*c2
                end if

                if (iy1 .ne. 0) then
                    if (vp .lt. 0.0) then
                        flyp = cc*vp
                    else
                        flyp = ci1*vp
                    end if

                    ci3 = 0.0
                    if (i .ne. is) then
                        i3 = min(is1, i + 2)
                        if (idy(i3, j) .ne. 0) ci3 = an3(i3, j)
                    end if
                    apy2(i1, j) = (vp*(7.0*(cc + ci1) - (ci2 + ci3))/12.0 - flyp)*c2
                end if
            end do
        end do

        ! Цикл 91 (Ограничитель потоков FCT - коррекция по X)
        do j = 1, js
            do i = 1, is
                if (idx(i, j) .eq. 0) cycle

                j1 = min(js1, j + 1)
                j2 = max(1, j - 1)
                ix1 = idx(i, j1)
                ix2 = idx(i, j2)

                if (ix1 .eq. 0) then
                    a1 = 0.0
                else
                    a1 = cd2(i, j1) - cd2(i, j)
                end if

                if (ix2 .eq. 0) then
                    b1 = 0.0
                else
                    b1 = cd2(i, j2) - cd2(i, max(1, j - 2))
                end if

                a = apx2(i, j)
                b = sign(1.0, a)
                apx2(i, j) = b*max(0.0, min(abs(a), b*a1, b*b1))
            end do
        end do

        ! Цикл 191 (Обновление значений по X)
        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0 .or. it(i, j) .ne. 0) cycle
                j1 = min(js1, j + 1)
                cd2(i, j) = cd2(i, j) - (apx2(i, j1) - apx2(i, j))
            end do
        end do

        ! --- Y-COORDINATE ---

        ! Цикл 391 (Ограничитель потоков для Y)
        do j = 1, js
            do i = 1, is
                if (idy(i, j) .eq. 0) cycle

                i1 = min(is1, i + 1)
                i2 = max(1, i - 1)
                iy1 = idy(i1, j)
                iy2 = idy(i2, j)

                if (iy1 .eq. 0) then
                    a1 = 0.0
                else
                    a1 = cd2(i, j) - cd2(i1, j)
                end if

                if (iy2 .eq. 0) then
                    b1 = 0.0
                else
                    b1 = cd2(max(1, i - 2), j) - cd2(i2, j)
                end if

                a = apy2(i, j)
                b = sign(1.0, a)
                apy2(i, j) = b*max(0.0, min(abs(a), b*a1, b*b1))
            end do
        end do

        ! Цикл 392 (Обновление значений по Y)
        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0 .or. it(i, j) .ne. 0) cycle
                i1 = min(is1, i + 1)
                an3(i, j) = cd2(i, j) - (apy2(i, j) - apy2(i1, j))
            end do
        end do

        ! Цикл 400 (Финальное сглаживание / обработка)
        do j = 1, js
            do i = 1, is
                ki = it(i, j)
                if (ki .eq. 0 .or. ki .eq. 9) cycle

                i1 = min(is1, i + 1)
                j1 = min(js1, j + 1)
                i2 = max(1, i - 1)
                j2 = max(1, j - 1)

                if (ki .eq. 1) an3(i, j) = 0.5*(an3(i, j1) + an3(i1, j))
                if (ki .eq. 2) an3(i, j) = 0.5*(an3(i, j2) + an3(i1, j))
                if (ki .eq. 3) an3(i, j) = 0.5*(an3(i, j2) + an3(i2, j))
                if (ki .eq. 4) an3(i, j) = 0.5*(an3(i, j1) + an3(i2, j))
            end do
        end do

    end subroutine adv2d

end module advection_2d
