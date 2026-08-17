! ==============================================================================
! Модуль: wind_forcing (wind1)
! Назначение: Чтение и интерполяция метеорологических данных (форсинга).
! Физика: Преобразует поля атмосферного давления в градиенты для вычисления
!         скорости геострофического ветра. Вычисляет поверхностные касательные
!         напряжения (tx1, ty1) по квадратичному закону аэродинамического трения.
! Ответственность: Ассимиляция внешних данных, пространственная интерполяция
!                  метеополей на узлы гидродинамической сетки.
! ==============================================================================

module wind_forcing
    use param
    use smooth_filter    ! Подключаем модуль сглаживания
    use netcdf_input, only: era5_find_time_index, era5_bilinear2d, &
                            era5_u10, era5_v10, era5_t2m, era5_msl, &
                            era5_d2m, era5_tcc, era5_snowfall, era5_is_open
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

        ! По умолчанию отсутствующий внешний форсинг означает нулевое поле.
        fi1 = 0.0
        dl1 = 0.0
        pp1 = 0.0
        wind = 0.0
        alf = 0.0
        dpx1 = 0.0
        dpy1 = 0.0
        windx1 = 0.0
        windy1 = 0.0
        tx1 = 0.0
        ty1 = 0.0

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

                    ccc = 0.0
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
                    dpx1(i, j) = px*1.e3/dxx
                    dpy1(i, j) = py*1.e3/dxx
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
                windx1(i, j) = v_wind*a
                windy1(i, j) = v_wind*b

                cof = (1.1 + 0.04*v_wind*1.e-2)*v_wind*v_wind*1.29e-6
                ty1(i, j) = cof*b
                tx1(i, j) = cof*a
            end do
        end do

        ! Краевые условия
        wind(:, js1) = wind(:, js)
        wind(is1, :) = wind(is, :)
        dpx1(:, js1) = dpx1(:, js)
        dpy1(:, js1) = dpy1(:, js)
        windx1(:, js1) = windx1(:, js)
        windy1(:, js1) = windy1(:, js)
        tx1(:, js1) = tx1(:, js)
        ty1(:, js1) = ty1(:, js)
        dpx1(is1, :) = dpx1(is, :)
        dpy1(is1, :) = dpy1(is, :)
        windx1(is1, :) = windx1(is, :)
        windy1(is1, :) = windy1(is, :)
        tx1(is1, :) = tx1(is, :)
        ty1(is1, :) = ty1(is, :)

        call surfw()

        ! Маскирование суши (в оригинале 8888. - суша)
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) wind(i, j) = 1.70141e38
            end do
        end do

    end subroutine wind1

    ! ==========================================================================
    ! ERA5-ветвь форсинга: заполняет модельные массивы полями, интерполированными
    ! с регулярной ERA5-сетки билинейно в точках FI(i,j)/DL(i,j).
    ! Условные секунды itime_sec используются для выбора временного среза
    ! (nearest-time, документированное допущение первого этапа).
    !
    ! Единицы (СГС/смешанная система модели):
    !   ERA5 u10/v10 [m/s] -> windx1/windy1 [cm/s]  (x100)
    !   wind             [m/s] (модуль, для heat)
    !   tx1/ty1          [г/см/с2 = дин/см2] по квадратичному закону,
    !                    идентичному legacy (cof), НО по фактическому u10/v10,
    !                    а не по геострофическому ветру.
    !   msl  [Pa] -> p1 [гПа] (x0.01); dpx1/dpy1 [гПа/км] — независимая ветвь.
    !   t2m  [K]  -> tatm [degC] (минус 273.15)
    !   msl  [Pa] -> patm [гПа] (x0.01) для термодинамики.
    ! ==========================================================================
    subroutine era5_wind(itime_sec)
        real(8), intent(in) :: itime_sec
        integer :: i, j, tidx
        integer :: nbad
        real(8) :: lat, lon, u10v, v10v, t2mv, mslv, d2mv, tccv, snowfallv
        real(8) :: spd, cof8, u_cm, v_cm
        real, parameter :: dxx = 13.89e5 ! Горизонтальный шаг сетки (см)
        logical :: ok

        if (.not. era5_is_open) then
            print *, "ERA5 WIND: ERA5 dataset is not open; using zeros."
            windx1 = 0.0
            windy1 = 0.0
            wind = 0.0
            tx1 = 0.0
            ty1 = 0.0
            p1 = 0.0
            dpx1 = 0.0
            dpy1 = 0.0
            tatm = 0.0
            patm = 0.0
            humid = 0.0
            cloud = 0.0
            return
        end if

        call era5_find_time_index(itime_sec, tidx)
        nbad = 0
        print *, "ERA5 WIND: tidx=", tidx, " sec=", itime_sec

        ! Интерполяция во ВСЕ узлы модельной сетки. Точки суши затем
        ! маскируются ниже (wind=1.70141e38), как в legacy.
        do j = 1, js1
            do i = 1, is1
                lat = real(fi(i, j), 8)
                lon = real(dl(i, j), 8)

                ok = era5_bilinear2d(era5_u10(:, :, tidx), lat, lon, u10v)
                if (.not. ok) then
                    nbad = nbad + 1
                    cycle
                end if
                ok = era5_bilinear2d(era5_v10(:, :, tidx), lat, lon, v10v)
                ok = era5_bilinear2d(era5_t2m(:, :, tidx), lat, lon, t2mv)
                ok = era5_bilinear2d(era5_msl(:, :, tidx), lat, lon, mslv)
                ok = era5_bilinear2d(era5_d2m(:, :, tidx), lat, lon, d2mv)
                ok = era5_bilinear2d(era5_tcc(:, :, tidx), lat, lon, tccv)
                ok = era5_bilinear2d(era5_snowfall(:, :, tidx), lat, lon, snowfallv)
                ! Точка росы: e_vap = hhum * e_sat(tta)
                ! по определению: e_vap = e_sat(d2m), hhum = e_sat(d2m)/e_sat(t2m)
                ! относительная влажность: RH = e_sat(d2m)/e_sat(t2m)
                humid(i, j) = (610.78 * 10.0**((8.61503*(d2mv - 273.15))/d2mv)) / &
                       (610.78 * 10.0**((8.61503*(t2mv - 273.15))/t2mv))
                ! Облачность: ERA5 tcc [0,1] -> model cloud [0,1]
                cloud(i, j) = tccv
                u_cm = u10v*100.0_8
                v_cm = v10v*100.0_8
                spd = sqrt(u_cm*u_cm + v_cm*v_cm)

                ! Квадратичный закон сопротивления (идентичен legacy-wind1):
                !   cof = (1.1 + 0.04*V_cm*1e-2) * V_cm^2 * 1.29e-6   [дин/см2 при V в см/с]
                ! Направление берётся из фактического ветра (u/v), а не из угла.
                if (spd .gt. 1.0e-6) then
                    cof8 = (1.1_8 + 0.04_8*(spd*1.0e-2_8))*spd*spd*1.29e-6_8
                    tx1(i, j) = real(cof8*(u_cm/spd), 4)
                    ty1(i, j) = real(cof8*(v_cm/spd), 4)
                else
                    tx1(i, j) = 0.0
                    ty1(i, j) = 0.0
                end if

                windx1(i, j) = real(u_cm, 4)
                windy1(i, j) = real(v_cm, 4)
                wind(i, j) = real(spd*1.0e-2, 4)          ! м/с

                p1(i, j) = real(mslv*0.01, 4)             ! гПа
                tatm(i, j) = real(t2mv - 273.15_8, 4)     ! degC
                patm(i, j) = real(mslv*0.01, 4)           ! гПа
            end do
        end do

        if (nbad .gt. 0) then
            print *, "ERA5 WIND WARNING: ", nbad, &
                " model points outside ERA5 latitude range (zeroed)."
        end if

        ! Градиент атмосферного давления (независимая ветвь от ветра).
        ! Та же формула, что в legacy: px = p1(i,j+1)-p1(i,j); py = p1(i,j)-p1(i+1,j)
        ! dpx1 = px*1e3/dxx  -> единицы гПа/км.
        do j = 1, js
            do i = 1, is
                dpx1(i, j) = (p1(i, j + 1) - p1(i, j))*1.e3/dxx
                dpy1(i, j) = (p1(i, j) - p1(i + 1, j))*1.e3/dxx
            end do
        end do

        ! Краевые условия (как в legacy-wind1).
        wind(:, js1) = wind(:, js)
        wind(is1, :) = wind(is, :)
        dpx1(:, js1) = dpx1(:, js)
        dpy1(:, js1) = dpy1(:, js)
        windx1(:, js1) = windx1(:, js)
        windy1(:, js1) = windy1(:, js)
        tx1(:, js1) = tx1(:, js)
        ty1(:, js1) = ty1(:, js)
        dpx1(is1, :) = dpx1(is, :)
        dpy1(is1, :) = dpy1(is, :)
        windx1(is1, :) = windx1(is, :)
        windy1(is1, :) = windy1(is, :)
        tx1(is1, :) = tx1(is, :)
        ty1(is1, :) = ty1(is, :)

        ! Маскирование суши (в оригинале 8888. - суша)
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) wind(i, j) = 1.70141e38
            end do
        end do
        print *, "ERA5 WIND ranges: windx[", minval(windx1), ",", maxval(windx1), &
            "] p1[", minval(p1), ",", maxval(p1), "] tx[", minval(tx1), &
            ",", maxval(tx1), "] dpx[", minval(dpx1), ",", maxval(dpx1), "]"
    end subroutine era5_wind

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
