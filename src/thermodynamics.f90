module thermodynamics
    use param
    implicit none

contains

    subroutine heat(dt, nday, lll)
        real, intent(in) :: dt
        integer, intent(in) :: nday, lll

        ! Локальные переменные
        integer :: i, j, k, k1
        real :: dzz, dtz, ttac, tta, ppatm, ratm, twac, twa, hhum, ww, cclo
        real :: a, a1, a2, a3, b, b1, b2, b3, b4, cz, e_vap, sw, wl
        real :: hfirst, ann1, ann2, sh1, el1, aaa, qn, dhsn, dhic1, dhic
        real :: tts, el, hhic1, err, err1, sh, dtts, tti, tfr, fw, tfr_new
        real :: a_tmp, b_tmp, a3_tmp, b3_tmp, a_tmp2, ansum, hour, rad_b1, rad_b2

        ! Предварительные расчеты (вынесены из циклов для скорости)
        dzz = dz1(1)/100.0
        dtz = dt/(dzz*4.19e6)
        hour = 12.0 ! Условный полдень для солнечной радиации (из комментариев оригинала)

        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0 .or. abs(ans(i, j) - 9.0) .lt. 1e-8) cycle

                ! Метеорология и океан
                ttac = tatm(i, j)           ! Температура воздуха (C)
                tta = ttac + 273.15         ! Температура воздуха (K)
                ppatm = patm(i, j)*100.0    ! Атмосферное давление (Паскали)
                ratm = ppatm/(287.0*tta)    ! Плотность воздуха (кг/м3)
                twac = t1(i, j, 1)          ! Температура воды (C)
                twa = twac + 273.15         ! Температура воды (K)
                hhum = humid(i, j)          ! Влажность (доли единицы)
                ww = wind(i, j)             ! Скорость геострофического ветра (м/с)
                cclo = cloud(i, j)          ! Облачность
                a = s1(i, j, 1)             ! Соленость поверхностного слоя

                ! Подготовка массивов льда
                do k = 1, ngr
                    anp(k) = an1(i, j, k + 1)
                    if (abs(anp(k)) .gt. 1e-8) then
                        hicp(k) = wice1(i, j, k)/anp(k)
                        hsnp(k) = hsnow(i, j, k)
                    else
                        hicp(k) = 0.0
                        hsnp(k) = 0.0
                    end if
                    spar(k) = a
                    tpar(k) = twa
                end do

                ansum = ans(i, j)
                tfr = -54.0*spar(1)
                fw = 1028.0*4.1868e3*skt(i, j)*(t1(i, j, 1) - tfr)/dz(1)
                if (fw .le. 0.0) fw = 0.0
                tfr = tfr + 273.15

                ! Солнечная радиация
                a1 = fi(i, j)/57.3
                a2 = sin(a1)
                b2 = cos(a1)
                b = 23.44*cos((172.0 - nday)/57.3)/57.3
                a3 = sin(b)
                b3 = cos(b)

                cz = max(0.0, a2*a3 + b2*b3*cos((12.0 - hour)*0.2617994))

                a1 = 1353.0*cz*cz*(1.0 - 0.6*cclo**3)
                rad_b1 = (cz + 2.7)*1.0e-5
                rad_b2 = 1.085*cz + 0.1
                e_vap = hhum*610.78*10.0**(8.61503*(tta - 273.15)/tta)
                sw = a1/(rad_b1*e_vap + rad_b2)
                b3 = ratm*1.7068*ww
                a3 = 0.6650735*ratm/ppatm*ww
            wl = 5.4999e-8*tta**4*(1.0 - 0.261*exp(-7.77e-4*((273.15 - tta)**2)))*(1.0 + 0.275*cclo)

                ! Потоки и образование льда (чистая вода)
                hfirst = 0.0
                ann1 = an1(i, j, 1)

                if (abs(ann1) .gt. 1e-8) then
                    sh1 = b3*(tta - twa)
           el1 = a3*2.5e6*(hhum*10.0**(7.63*ttac/(241.9 + ttac)) - 10.0**(7.63*twac/(241.9 + twac)))
                    aaa = -0.97*5.67e-8*(twa**4)
                    qn = sh1 + el1 + 0.97*wl + 0.9*sw + aaa

                    if (qn .gt. 0.0) then
                        tpar(1) = tpar(1) + dtz*ann1*qn
                    else
                        tpar(1) = tpar(1) + dtz*qn
                    end if

                    if (tpar(1) .ge. tfr) then
                        if (tpar(1) .gt. tta .and. qn .gt. 0.0) tpar(1) = tta
                    else
                        tpar(1) = tfr
                        hfirst = 0.01
                    end if
                end if

                ! Термодинамика льда (цикл по категориям толщин)
                do k = 1, ngr
                    k1 = k + 1
                    if (anp(k) .lt. 0.001) cycle

                    dhsn = 0.0
                    dhic1 = 0.0
                    tts = 0.5*(tta + twa)
    el = a3*2.834e6*(hhum*10.0**(9.5*ttac/(265.5 + ttac)) - 10.0**(9.5*(tts - 273.15)/(tts - 7.65)))
                    hhic1 = 1.0/max(hicp(k), 1.0e-6) ! Защита от деления на ноль

                    if (abs(hsnp(k)) .lt. 1e-8) then
                        ! --- ЛЕД БЕЗ СНЕГА ---
                        b = 2.04*hhic1
                        err = 100.0
                        err1 = 100.0
                        do while (err .ge. 0.25)
                            sh = b3*(tta - tts)
                            a = 5.4999e-8*tts**3
                            a1 = sh + el + 0.466*sw + 0.97*wl
                            dtts = (a1 - a*tts + b*(tfr - tts))/(4.0*a + b)
                            a_tmp = tts + dtts
                            err1 = err
                            err = abs(dtts)
                            if (err .ge. err1) exit
                            tts = a_tmp
                        end do
                        if (err .ge. err1) tts = tta

                        if (tts .le. 273.15) then
                            dhsn = dt*sfal(lll)
                            hsnp(k) = dhsn
                        else
                            tts = 273.15
                            dhic1 = -dt/302.e6*(a1 - 5.4999e-8*tts**4 + b*(tfr - tts))
                            hicp(k) = hicp(k) + dhic1
                            if (hicp(k) .lt. 0.01) hicp(k) = 0.0
                        end if

                        dhic = -dt/302.e6*(fw - b*(tfr - tts))
                        hicp(k) = hicp(k) + dhic + dhic1
                        if (hicp(k) .lt. 0.01) then
                            hicp(k) = 0.0
                            hsnp(k) = 0.0
                        end if

                    else
                        ! --- ЛЕД СО СНЕГОМ ---
                        b1 = 0.31*hicp(k)
                        b2 = 2.04*hsnp(k)
                        b4 = b1 + b2
                        b = 0.6324/b4
                        err = 100.0
                        err1 = 100.0
                        do while (err .ge. 0.25)
                            sh = b3*(tta - tts)
                            a = 5.6133e-8*tts**3
                            a1 = sh + el + (1.0 - alsn(lll))*sw + 0.99*wl
                            dtts = (a1 - a*tts + b*(tfr - tts))/(4.0*a + b)
                            a_tmp = tts + dtts
                            err1 = err
                            err = abs(dtts)
                            if (err .ge. err1) exit
                            tts = a_tmp
                        end do
                        if (err .ge. err1) tts = tta

                        if (tts .le. 273.15) then
                            dhsn = sfal(lll)*dt
                            tti = (b1*tts + b2*tfr)/b4
                        else
                            tts = 273.15
                            tti = (b1*273.15 + b2*tfr)/b4
                            dhsn = -dt/110.e6*(a1 - 5.6133e-8*tts**4 + 0.31/hsnp(k)*(tti - tts))
                        end if

                        dhic = dt/302.e6*(2.04*(tfr - tti)/hicp(k) - fw)
                        hicp(k) = hicp(k) + dhic
                        if (hicp(k) .ge. 0.01) then
                            a_tmp = 0.1*hicp(k)
                            hsnp(k) = hsnp(k) + dhsn
                            if (hsnp(k) .gt. a_tmp) hsnp(k) = a_tmp
                            if (hsnp(k) .lt. 0.0) hsnp(k) = 0.0
                        else
                            hicp(k) = 0.0
                            hsnp(k) = 0.0
                        end if
                    end if

                    ! Новая температура и соленость
                    a_tmp = 0.88*dhic
                    b_tmp = dzz - a_tmp
                    if (dhic .lt. 0.0) then
                        if (dhsn .lt. 0.0) then
                            a1 = 0.3*dhsn
                            b_tmp = b_tmp - a1
                            b1 = 273.15*a1
                        else
                            b1 = 0.0
                            a1 = 0.0
                        end if
                        spar(k1) = (spar(k1)*(dzz + a_tmp + a1) - sicst(k)*a_tmp)/dzz
                        tfr_new = -54.0*spar(k1) + 273.15
                        tpar(k1) = (tfr_new*dzz - b1)/(dzz - a1)
                    else
                        spar(k1) = (spar(k1)*dzz - sicst(k)*a_tmp)/b_tmp
                        tfr_new = -54.0*spar(k1) + 273.15
                        tpar(k1) = tfr_new
                    end if

                    hsnow(i, j, k) = hsnp(k)
                    hice(i, j, k) = hicp(k)
                    if (abs(hicp(k)) .lt. 1e-8) then
                        ann1 = ann1 + anp(k)
                        an1(i, j, k1) = 0.0
                        anp(k) = 0.0
                    end if
                end do ! Конец цикла по NGR

                ! Таяние в разводьях
                if (ann1 .gt. 0.0 .and. ann1 .lt. 1.0 .and. qn .gt. 0.0) then
                    a_tmp = ann1*qn*dt
                    b_tmp = 0.0
                    a3_tmp = 0.0
                    b3_tmp = 0.0
                    do k = 1, ngr
                        if (abs(hicp(k)) .gt. 1e-8) then
                            k1 = k + 1
                            danp(k) = anp(k)*a_tmp/(302.e6*hicp(k) + 110.e6*hsnp(k))
                            anp(k) = anp(k) - danp(k)
                            b_tmp = b_tmp + danp(k)
                            a3_tmp = a3_tmp + anp(k)*tpar(k1)
                            b3_tmp = b3_tmp + anp(k)*spar(k1)
                        else
                            danp(k) = 0.0
                        end if
                    end do

                    ann2 = ann1 + b_tmp
                    a2 = 0.0
                    b2 = 0.0
                    do k = 1, ngr
                        k1 = k + 1
                        tfr_new = -54.0*sicst(k) + 273.15
                        a_tmp2 = 0.88*hicp(k)
                        a1 = danp(k)/(a_tmp2 + dzz)
                        a2 = a2 + (tpar(k1)*dzz + tfr_new*a_tmp2)*a1
                        b2 = b2 + (spar(k1)*dzz + sicst(k)*a_tmp2)*a1
                    end do

                    tpar(1) = (tpar(1)*ann1 + a2)/ann2
                    spar(1) = (spar(1)*ann1 + b2)/ann2
                    an1(i, j, 1) = ann2
                    t1(i, j, 1) = ann2*tpar(1) + a3_tmp - 273.15
                    s1(i, j, 1) = ann2*spar(1) + b3_tmp
                else
                    a1 = ann1*tpar(1)
                    b1 = ann1*spar(1)
                    do k = 1, ngr
                        k1 = k + 1
                        a1 = a1 + anp(k)*tpar(k1)
                        b1 = b1 + anp(k)*spar(k1)
                    end do
                    t1(i, j, 1) = a1 - 273.15
                    s1(i, j, 1) = b1

                    if (hfirst .gt. 0.0) then
                        a2 = an1(i, j, 2)
                        a1 = ann1 + a2
                        if (a1 .gt. 0.0) hicp(1) = (0.01*ann1 + hicp(1)*a2)/a1
                        an1(i, j, 1) = 0.0
                        anp(1) = a1
                    end if
                end if

                ! Обновление массивов
                do k = 1, ngr
                    hice(i, j, k) = hicp(k)
                    hsnow(i, j, k) = hsnp(k)
                    an1(i, j, k + 1) = anp(k)
                    if (abs(anp(k)) .gt. 1e-8) then
                        wice1(i, j, k) = hice(i, j, k)*anp(k)
                    else
                        wice1(i, j, k) = 0.0
                    end if
                end do

            end do
        end do

    end subroutine heat

end module thermodynamics
