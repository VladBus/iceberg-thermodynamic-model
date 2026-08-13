module wind_forcing
    use param
    use smooth_filter    ! Подключаем модуль сглаживания
    implicit none

contains

    subroutine wind1()
        ! Локальные переменные
        integer :: i, j, k, k2, nom
        real :: bll, x0, y0, fii, dll, dx_int, dy_int, ab
        real :: an1_wind, an2_wind, an3_wind, an4_wind
        real :: px, py, vx, vy, v_wind, q_wind, au, u_wind, cof, a, b
        real, parameter :: dxx = 13.89e5 ! Горизонтальный шаг сетки (см) из описания
        integer :: ios ! Для проверки существования файлов

        ! Временное задание имен файлов для вывода (чтобы избежать вылетов)
        ep = 'ep.dat'
        evet = 'evet.dat'
        ewin = 'ewin.dat'

        ! Чтение старых файлов сетки (если они есть в папке)
        open (1, file='FI1DL1.DAT', status='old', iostat=ios)
        if (ios .eq. 0) then
            do i = 1, 135
                read (1, '(107F6.2)') (fi1(i, j), j=1, 107)
            end do
            do i = 1, 135
                read (1, '(107F6.2)') (dl1(i, j), j=1, 107)
            end do
            close (1)
        else
            print *, "WARNING: FI1DL1.DAT not found, using default zeros for grid."
        end if

        bll = 37.96

        ! Интерполяция методом конечных элементов
        do j = 1, 107
            do i = 1, 135
                nom = np(i, j)
                if (nom .gt. 0 .and. nom .le. 1330) then
                    x0 = x01(nom)
                    y0 = y01(nom)
                    fii = fi1(i, j)
                    dll = dl1(i, j)
                    dx_int = (dll - x0)/2.5
                    dy_int = (fii - y0)/2.5

                    do k = 1, 4
                        k2 = np1(nom, k)
                        if (k2 .gt. 0) ccc(k) = pp(k2)
                    end do

                    ab = 0.25
                    an1_wind = ab*(1.0 - dx_int)*(1.0 - dy_int)
                    an2_wind = ab*(1.0 + dx_int)*(1.0 - dy_int)
                    an3_wind = ab*(1.0 + dx_int)*(1.0 + dy_int)
                    an4_wind = ab*(1.0 - dx_int)*(1.0 + dy_int)
                   pp1(i, j) = ccc(1)*an1_wind + ccc(2)*an2_wind + ccc(3)*an3_wind + ccc(4)*an4_wind
                end if
            end do
        end do

        ! Активируем сглаживание поля давления
        call gladw()

        do j = 1, js1
            do i = 1, is1
                p1(i, j) = pp1(i + 1, j + 1)
            end do
        end do

        ! Расчет градиентов и скоростей ветра
        do j = 1, js
            do i = 1, is
                px = p1(i, j + 1) - p1(i, j)
                py = p1(i, j) - p1(i + 1, j)

                if (abs(px) .lt. 1e-8 .and. abs(py) .lt. 1e-8) then
                    v_wind = 0.0
                    u_wind = 0.0
                    vx = 0.0
                    vy = 0.0
                else
                    vx = -py*bll
                    vy = px*bll
                    dpx(i, j) = px*1.e3/dxx
                    dpy(i, j) = py*1.e3/dxx
                    v_wind = sqrt(vx*vx + vy*vy)

                    q_wind = 0.8
                    if (v_wind .gt. 30.0) q_wind = 1.0

                    au = 30.0 - 0.8333*v_wind
                    if (v_wind .gt. 30.0) au = 5.0

                    u_wind = atan2(vx, vy)*57.3 - au
                    v_wind = v_wind*q_wind*100.0
                    wind(i, j) = v_wind/100.0

                    if (u_wind .gt. 360.0) u_wind = u_wind - 360.0
                    if (u_wind .le. 0.0) u_wind = u_wind + 360.0
                end if

                alf(i, j) = u_wind
                a = sin(u_wind/57.3)
                b = cos(u_wind/57.3)
                windx(i, j) = v_wind*a
                windy(i, j) = v_wind*b

                cof = (1.1 + 0.04*v_wind*1.e-2)*v_wind*v_wind*1.29e-6
                ty(i, j) = cof*b
                tx(i, j) = cof*a
            end do
        end do

        ! Краевые условия
        wind(:, js1) = wind(:, js)
        wind(is1, :) = wind(is, :)

        call surfw()

        ! Маскирование суши (в оригинале 8888. - суша)
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) wind(i, j) = 1.70141e38
            end do
        end do

    end subroutine wind1

    ! Внутренняя подпрограмма (была вынесена отдельно, теперь живет внутри модуля)
    subroutine surfw()
        integer :: i, j, nc, ni, i1, j1, nnn
        real :: ft, umax, y11, ppp, pi1, x1, sa, x2, y22, x3, y3, x4, y4
        integer :: ios

        nc = 5
        ft = 0.5
        ni = is1
        umax = 0.0
        i1 = -nc + 1
        nnn = 5

        open (17, file=ewin, status='replace', iostat=ios)
        if (ios .ne. 0) return

        do i = 1, is1, nc
            i1 = i1 + nc
            j1 = -nc + 1
            y11 = ni + 1 - i1
            do j = 1, js1, nc
                j1 = j1 + nc
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle

                ppp = wind(i, j)
                if (ppp .gt. umax) umax = ppp
                pi1 = alf(i, j)/57.3
                x1 = j1
                sa = ppp/4.0*ft
                x2 = ppp*sin(pi1)*ft + x1
                y22 = ppp*cos(pi1)*ft + y11
                x3 = x2 + sa*sin(pi1 + 165.0/57.3)
                y3 = y22 + sa*cos(pi1 + 165.0/57.3)
                x4 = x2 + sa*sin(pi1 + 195.0/57.3)
                y4 = y22 + sa*cos(pi1 + 195.0/57.3)

                write (17, '(I6)') nnn
                write (17, '(2F7.2)') x1, y11
                write (17, '(2F7.2)') x2, y22
                write (17, '(2F7.2)') x3, y3
                write (17, '(2F7.2)') x2, y22
                write (17, '(2F7.2)') x4, y4
            end do
        end do
        close (17)

    end subroutine surfw

end module wind_forcing
