! ==============================================================================
! Модуль: shallow_water (shal)
! Назначение: Обновление поля возвышения свободной поверхности.
! Физика: Использует полученные дивергенции интегральных потоков для обновления
!         поля возвышения свободной поверхности, которое затем передается обратно
!         в баротропные уравнения генерации градиентов гидростатического давления.
!         Данный цикл обеспечивает консервативность массы всей системы.
! Ответственность: Вычисление полного переноса масс воды с малым шагом по времени.
! ==============================================================================

module shallow_water
    use param
    use barotropic_dynamics
    implicit none

    ! Глобальные переменные, сохраняющие состояние между вызовами
    integer, save, public :: jjq = 0
    real, save, public :: euu = 0.0

contains

    subroutine shal()
        ! Локальные переменные
        integer :: i, j, k, i1, i2, j1, j2, ki, jjj, ij, uuk
        real :: hht, a, b, a1, a2, b2, vs, us, uij, vij, uu1, uu2, vv1, vv2
        real :: yy1, yy2, hh1, h1, h2, uup

        ! Константы (перенесены из старого глобального файла)
        real :: dt1, dx, c1, c3, c9, c10, aa1, aa2, aa3
        integer :: mm3

        dt1 = 120.0
        dx = 1389000.0
        mm3 = 30
        c1 = 981.0/1.0
        c3 = 7.5e6/(dx*dx)
        c9 = 0.5/dx
        c10 = dt1/dx
        aa1 = 981.0/dx
        aa2 = 0.0026*dt1
        aa3 = 0.0055*dt1

        ym2(:, :) = 0.0

        ! Блок расчета градиентов DRX и DRY был аппаратно отключен
        ! в оригинальном коде через безусловный переход GOTO 900.
        ! Оставляем его выключенным для обратной совместимости.
        if (.false.) then
            do j = 2, js2
                do i = 2, is2
                    hht = hu(i, j)
                    if (abs(hht - 8888.0) .lt. 1e-8) cycle
                    j2 = j - 1
                    a = 0.0
                    b = 0.0
                    a1 = 0.0
                    a2 = 0.0
                    ki = min(kt1(i, j), kt1(i, j2))
                    do k = 1, ki
                        if (k .eq. ki) then
                            b2 = hht - a2
                        else
                            b2 = dz1(k)
                            a2 = a2 + b2
                        end if
                        b = b + (ro(i, j, k) - ro(i, j2, k))*b2*c9
                        a1 = a1 + (a + b)*b2*0.5
                        a = b
                    end do
                    drx(i, j) = c1*a1
                end do
            end do

            do j = 2, js2
                do i = 2, is2
                    hht = hv(i, j)
                    if (abs(hht - 8888.0) .lt. 1e-8) cycle
                    i2 = i - 1
                    a = 0.0
                    b = 0.0
                    a1 = 0.0
                    a2 = 0.0
                    ki = min(kt1(i, j), kt1(i2, j))
                    do k = 1, ki
                        if (k .eq. ki) then
                            b2 = hht - a2
                        else
                            b2 = dz1(k)
                            a2 = a2 + b2
                        end if
                        b = b + (ro(i2, j, k) - ro(i, j, k))*b2*c9
                        a1 = a1 + (a + b)*b2*0.5
                        a = b
                    end do
                    dry(i, j) = c1*a1
                end do
            end do
        end if

        ! --- ОСНОВНОЙ БАРОТРОПНЫЙ ЦИКЛ ---
        do jjj = 1, mm3
            jjq = jjq + 1
            om(1:4) = q(1:4)*real(jjq)

            up1(:, :) = up2(:, :)
            vp1(:, :) = vp2(:, :)

            ! Расчет уровня моря Y
            do j = 2, js
                do i = 2, is
                    if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle
                   y2(i, j) = y2(i, j) - c10*(up1(i, j + 1) - up1(i, j) + vp1(i, j) - vp1(i + 1, j))
                end do
            end do

            ! --- ПРИЛИВЫ НА ГРАНИЦАХ ---
            do i = 1, 133
                y2(i, 1) = amp1(i, 1)*cos(om(1) + (v00(1) - faz1(i, 1))/57.3) + &
                           amp1(i, 2)*cos(om(2) + (v00(2) - faz1(i, 2))/57.3) + &
                           amp1(i, 3)*cos(om(3) + (v00(3) - faz1(i, 3))/57.3) + &
                           amp1(i, 4)*cos(om(4) + (v00(4) - faz1(i, 4))/57.3)
            end do

            do i = 1, 105
                y2(1, i) = amp2(i, 1)*cos(om(1) + (v00(1) - faz2(i, 1))/57.3) + &
                           amp2(i, 2)*cos(om(2) + (v00(2) - faz2(i, 2))/57.3) + &
                           amp2(i, 3)*cos(om(3) + (v00(3) - faz2(i, 3))/57.3) + &
                           amp2(i, 4)*cos(om(4) + (v00(4) - faz2(i, 4))/57.3)
            end do

            do i = 1, 133
                y2(i, js) = amp3(i, 1)*cos(om(1) + (v00(1) - faz3(i, 1))/57.3) + &
                            amp3(i, 2)*cos(om(2) + (v00(2) - faz3(i, 2))/57.3) + &
                            amp3(i, 3)*cos(om(3) + (v00(3) - faz3(i, 3))/57.3) + &
                            amp3(i, 4)*cos(om(4) + (v00(4) - faz3(i, 4))/57.3)
            end do

            ym2(:, :) = ym2(:, :) + y2(:, :)

            ! --- РАСЧЕТ U-КОМПОНЕНТЫ ---
            do j = 2, js
                j1 = j + 1
                j2 = j - 1
                do i = 2, is
                    hht = hu(i, j)
                    if (abs(hht - 8888.0) .lt. 1e-8) cycle

                    uuk = iku(i, j)
                    i1 = i + 1
                    i2 = i - 1

                    bbb(1) = hv(i, j2)
                    bbb(2) = hv(i, j)
                    bbb(3) = hv(i1, j2)
                    bbb(4) = hv(i1, j)
                    ccc(1) = vp1(i, j2)
                    ccc(2) = vp1(i, j)
                    ccc(3) = vp1(i1, j2)
                    ccc(4) = vp1(i1, j)

                    vs = 0.0
                    do ij = 1, 4
                        if (abs(bbb(ij) - 8888.0) .lt. 1e-8) cycle
                        a = ccc(ij)/bbb(ij)
                        vs = vs + (bbb(ij) + hht)*a
                    end do

                    uij = up1(i, j)

                    if (i .eq. is .or. abs(hu(i1, j) - 8888.0) .lt. 1e-8) then
                        uu1 = uij
                    else
                        uu1 = up1(i1, j)
                    end if

                    if (i .eq. 1 .or. abs(hu(i2, j) - 8888.0) .lt. 1e-8) then
                        uu2 = uij
                    else
                        uu2 = up1(i2, j)
                    end if

                    a = (ccc(1) + ccc(2) + ccc(3) + ccc(4))/real(uuk)

                    ! Восстановление закомментированной ранее физики (открытая вода)
                    a1 = 0.5*(ans(i, j) + ans(i, j2))

                    yy1 = y2(i, j)
                    yy2 = y2(i, j2)
                    hh1 = hht + (yy1 + yy2)*0.5
                    if (hh1 .le. 50.0) hh1 = 50.0

                    h1 = aa1*hh1
                    h2 = aa2/(hh1*hh1)

                    uup = (uij + dt1*(-(yy1 - yy2)*h1 &
                                      - hh1*0.5*(dpx(i, j) + dpx(i1, j)) &
                                      + 0.125*fu(i, j)*vs &
                                      + (1.0 - a1)*0.5*(tx(i, j) + tx(i1, j)) &
                                      + c3*(uu1 + uu2 + up1(i, j1) + up1(i, j2) - 4.0*uij))) &
                          /(1.0 + h2*sqrt(uij*uij + a*a))

                    euu = euu + uup*uup
                    up2(i, j) = uup
                end do
            end do

            ! --- ГРАНИЧНЫЕ УСЛОВИЯ ДЛЯ U ---
            do i = 1, is
                hht = hu(i, 2)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle
                up2(i, 1) = -y2(i, 1)*sqrt(981.0*hht)
                ! Оригинальный код Нестерова перезаписывал значение (для совместимости оставляем):
                up2(i, 1) = up2(i, 2)
            end do

            do i = 1, 15
                hht = ht(i, 94)
                up2(i, 95) = y2(i, 94)*sqrt(981.0*hht)
                up2(i, 95) = up2(i, 94)
            end do

            ! --- РАСЧЕТ V-КОМПОНЕНТЫ ---
            do j = 2, js
                j1 = j + 1
                j2 = j - 1
                do i = 2, is
                    hht = hv(i, j)
                    if (abs(hht - 8888.0) .lt. 1e-8) cycle

                    uuk = ikv(i, j)
                    i1 = i + 1
                    i2 = i - 1

                    bbb(1) = hu(i, j)
                    bbb(2) = hu(i2, j)
                    bbb(3) = hu(i2, j1)
                    bbb(4) = hu(i, j1)
                    ccc(1) = up2(i, j)
                    ccc(2) = up2(i2, j)
                    ccc(3) = up2(i2, j1)
                    ccc(4) = up2(i, j1)

                    us = 0.0
                    do ij = 1, 4
                        if (abs(bbb(ij) - 8888.0) .lt. 1e-8) cycle
                        a = ccc(ij)/bbb(ij)
                        us = us + (bbb(ij) + hht)*a
                    end do

                    vij = vp1(i, j)

                    if (j .eq. js .or. abs(hv(i, j1) - 8888.0) .lt. 1e-8) then
                        vv1 = vij
                    else
                        vv1 = vp1(i, j1)
                    end if

                    if (j .eq. 1 .or. abs(hv(i, j2) - 8888.0) .lt. 1e-8) then
                        vv2 = vij
                    else
                        vv2 = vp1(i, j2)
                    end if

                    a = (ccc(1) + ccc(2) + ccc(3) + ccc(4))/real(uuk)

                    ! Восстановление закомментированной ранее физики (открытая вода)
                    a1 = 0.5*(ans(i, j) + ans(i2, j))

                    yy1 = y2(i2, j)
                    yy2 = y2(i, j)
                    hh1 = hht + (yy1 + yy2)*0.5
                    if (hh1 .le. 50.0) hh1 = 50.0

                    h1 = aa1*hh1
                    h2 = aa2/(hh1*hh1)

                    uup = (vij + dt1*((yy2 - yy1)*h1 &
                                      - hh1*0.5*(dpy(i, j) + dpy(i, j1)) &
                                      - 0.125*fv(i, j)*us &
                                      + (1.0 - a1)*0.5*(ty(i, j) + ty(i, j1)) &
                                      + c3*(vv1 + vv2 + vp1(i1, j) + vp1(i2, j) - 4.0*vij))) &
                          /(1.0 + h2*sqrt(vij*vij + a*a))

                    euu = euu + uup*uup
                    vp2(i, j) = uup
                end do
            end do

            ! --- ГРАНИЧНЫЕ УСЛОВИЯ ДЛЯ V ---
            do j = 1, js
                hht = hv(2, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle
                vp2(1, j) = y2(1, j)*sqrt(981.0*hht)
                vp2(1, j) = vp2(2, j)
            end do

            do j = 91, 93
                vp2(73, j) = y2(73, j)*sqrt(981.0*ht(73, j))
                vp2(73, j) = vp2(74, j)
            end do

            ! Шаг баротропного расчета течений
            call advsh(dt1)

        end do

        ! Осреднение по времени
        ym2(:, :) = ym2(:, :)/real(mm3)

    end subroutine shal

end module shallow_water
