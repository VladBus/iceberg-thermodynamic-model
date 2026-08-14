! ==============================================================================
! Модуль: advection_3d_s
! Назначение: Пространственная адвекция скалярных субстанций (соли) в 3D.
! Физика: Решает уравнение конвекции-диффузии. Для предотвращения численной
!         дисперсии и осцилляций используется алгоритм Flux-Corrected Transport (FCT).
! Ответственность: Транспортировка субстанций течениями с гарантиями сохранения
!                  строгой положительности концентрации и массы. Исключает
!                  возникновение нефизичных отрицательных значений толщины льда.
! ==============================================================================

module advection_3d_s
    use param
    implicit none

contains

    subroutine advs(dt, c2)
        real, intent(in) :: dt, c2

        ! Локальные переменные
        integer :: i, j, k, i1, i2, j1, j2, ki, k1
        real :: cc, ci1, ci2, cj1, cj2, up, uu, vp, vv, a, b
        real :: cdx, cdy, flxp, flyp, a1, b1
        real :: ck1, ck2, ww1, ww2, ww

        ! Обнуление массивов потоков
        apz(:, :, :) = 0.0
        apx(:, :, :) = 0.0
        apy(:, :, :) = 0.0

        ! --- ОСНОВНОЙ ЦИКЛ ПЕРЕНОСА ---
        do j = 1, js
            j1 = j + 1
            j2 = max(1, j - 1)
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle

                i1 = i + 1
                i2 = max(1, i - 1)

                ! Горизонтальный перенос
                do k = 1, ki
                    cc = s2(i, j, k)
                    ci1 = s2(i1, j, k)
                    ci2 = s2(i2, j, k)
                    cj1 = s2(i, j1, k)
                    cj2 = s2(i, j2, k)

                    up = u2(i, j1, k)
                    uu = 0.5*(up + u2(i, j, k))
                    vp = v2(i1, j, k)
                    vv = 0.5*(vp + v2(i, j, k))

                    a = abs(uu)
                    cdx = 0.5*(uu + a)*adx(i, j, k)*(cc - cj2) &
                          + 0.5*(uu - a)*adx(i, j1, k)*(cj1 - cc)

                    a = abs(vv)
                    cdy = 0.5*(vv + a)*ady(i1, j, k)*(cc - ci1) &
                          + 0.5*(vv - a)*ady(i, j, k)*(ci2 - cc)

                    tt(k) = s1(i, j, k) - c2*(cdx + cdy)

                    a = abs(up)
                    flxp = 0.5*(up + a)*cc + 0.5*(up - a)*cj1
                    apx(i, j1, k) = adx(i, j1, k)*(up*0.5*(cc + cj1) - flxp)*c2

                    a = abs(vp)
                    flyp = 0.5*(vp + a)*cc + 0.5*(vp - a)*ci1
                    apy(i1, j, k) = ady(i1, j, k)*(vp*0.5*(cc + ci1) - flyp)*c2
                end do

                ! Вертикальный перенос
                ck2 = s2(i, j, 1)
                cc = ck2
                ww1 = w(i, j, 1)

                do k = 1, ki - 1
                    k1 = k + 1
                    ww2 = w(i, j, k1)
                    ww = 0.5*(ww1 + ww2)
                    a = abs(ww)
                    ck1 = s2(i, j, k1)
                    cd(i, j, k) = tt(k) - dt* &
                                  (0.5*(ww + a)*(cc - ck2)/dz(k) + 0.5*(ww - a)*(ck1 - cc)/dz(k1))
                    ck2 = cc
                    cc = ck1
                    ww1 = ww2
                end do

                cd(i, j, ki) = tt(ki)
                cc = s2(i, j, 1)

                do k = 2, ki
                    ck1 = s2(i, j, k)
                    ww = w(i, j, k)
                    a = abs(ww)
                    apz(i, j, k) = 0.5*ww*(cc + ck1) - 0.5*(ww + a)*cc + 0.5*(ww - a)*ck1
                    cc = ck1
                end do
            end do
        end do

        ! --- КОРРЕКЦИЯ ПОТОКОВ FCT (X-COORDINATE) ---
        do j = 1, js
            do i = 1, is
                ki = idx(i, j)
                if (ki .eq. 0) cycle
                j1 = j + 1
                j2 = max(1, j - 1)

                do k = 1, ki
                    a1 = adx(i, j1, k)*(cd(i, j1, k) - cd(i, j, k))
                    b1 = adx(i, j2, k)*(cd(i, j2, k) - cd(i, max(1, j - 2), k))
                    a = apx(i, j, k)
                    b = sign(1.0, a)
                    apx(i, j, k) = b*max(0.0, min(abs(a), b*a1, b*b1))
                end do
            end do
        end do

        do j = 1, js
            j1 = j + 1
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    cd(i, j, k) = cd(i, j, k) - (apx(i, j1, k) - apx(i, j, k))
                end do
            end do
        end do

        ! --- КОРРЕКЦИЯ ПОТОКОВ FCT (Y-COORDINATE) ---
        do j = 1, js
            do i = 1, is
                i1 = i + 1
                i2 = max(1, i - 1)
                ki = idy(i, j)
                if (ki .eq. 0) cycle

                do k = 1, ki
                    a1 = ady(i1, j, k)*(cd(i, j, k) - cd(i1, j, k))
                    b1 = ady(i2, j, k)*(cd(max(1, i - 2), j, k) - cd(i2, j, k))
                    a = apy(i, j, k)
                    b = sign(1.0, a)
                    apy(i, j, k) = b*max(0.0, min(abs(a), b*a1, b*b1))
                end do
            end do
        end do

        do j = 1, js
            do i = 1, is
                i1 = i + 1
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    cd(i, j, k) = cd(i, j, k) - (apy(i, j, k) - apy(i1, j, k))
                end do
            end do
        end do

        ! --- КОРРЕКЦИЯ ПОТОКОВ FCT (Z-COORDINATE) ---
        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle

                if (ki .ge. 3) then
                    b1 = (cd(i, j, 3) - cd(i, j, 2))*dz1(2)/dt
                    a = apz(i, j, 2)
                    b = sign(1.0, a)
                    apz(i, j, 2) = b*max(0.0, min(abs(a), b*b1))

                    do k = 3, ki - 1
                        a1 = (cd(i, j, k - 1) - cd(i, j, k - 2))*dz1(k - 1)/dt
                        b1 = (cd(i, j, k + 1) - cd(i, j, k))*dz1(k)/dt
                        a = apz(i, j, k)
                        b = sign(1.0, a)
                        apz(i, j, k) = b*max(0.0, min(abs(a), b*a1, b*b1))
                    end do
                end if

                if (ki .ge. 2) then
                    a1 = (cd(i, j, ki - 1) - cd(i, j, max(1, ki - 2)))*dz1(ki - 1)/dt
                    a = apz(i, j, ki)
                    b = sign(1.0, a)
                    apz(i, j, ki) = b*max(0.0, min(abs(a), b*a1))
                end if
            end do
        end do

        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 2, ki - 1
                    cd(i, j, k) = cd(i, j, k) - (apz(i, j, k + 1) - apz(i, j, k))*dt/dz1(k)
                end do
            end do
        end do

        ! Финальное обновление массива солености
        s2(:, :, :) = cd(:, :, :)

    end subroutine advs

end module advection_3d_s
