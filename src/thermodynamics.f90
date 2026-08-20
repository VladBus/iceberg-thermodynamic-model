! ==============================================================================
! Модуль: thermodynamics (heat)
! Назначение: Расчет теплового баланса на границах раздела и фазовых переходов.
! Физика: Вычисляет потоки коротковолновой и длинноволновой радиации, явного и
!         скрытого тепла. Температура поверхности находится итерационным методом
!         Ньютона-Рафсона. Рассчитывает скорости нарастания и таяния льда
!         (базируется на термодинамических постулатах Зубова и Стефана).
!         Включает блок разрушения айсбергов волновой и конвективной эрозией.
!         Уравнения: Q_sw = SW·(1-α); Q_lw = ε·σ·T⁴; Q_sh = ρ_a·c_p·C_h·V·(T_a-T_s);
!         Q_lh = ρ_a·L·C_e·V·(q_a-q_s); T_f = -54·S (точка замерзания).
!         Скрытая теплота: L_f = 3.34e5 Дж/кг; ρ_i·L_f = 302e6 Дж/м³ (лед);
!         ρ_s·L_f = 110e6 Дж/м³ (снег).
! Единицы: T [degC или K], S [массовая доля], dt [с], h [м], A [доли единицы].
! Ответственность: Энергетический баланс системы, изменение толщины и сплошности
!                  ледяного покрова за счет тепловых процессов.
! ==============================================================================

module thermodynamics
    use param
    implicit none

contains

    subroutine heat(dt, nday, lll)
        real, intent(in) :: dt          ! Временной шаг термодинамики [с]
        integer, intent(in) :: nday     ! Номер дня в месяце (1..31)
        integer, intent(in) :: lll      ! Номер месяца (1..12) - для альбедо и sfal

        ! Локальные переменные
        integer :: i, j, k, k1, n_iter
        ! Метеорология и океан
        real :: dzz, dtz, ttac, tta, ppatm, ratm, twac, twa, hhum, ww, cclo
        ! Рабочие переменные для итераций и баланса
        real :: a, a1, a2, a3, b, b1, b2, b3, b4, cz, e_vap, sw, wl
        real :: hfirst, ann1, ann2, sh1, el1, aaa, qn, dhsn, dhic1, dhic
        real :: tts, el, hhic1, err, err1, sh, dtts, tti, tfr, fw, tfr_new
        real :: a_tmp, b_tmp, a3_tmp, b3_tmp, a_tmp2, ansum, hour, rad_b1, rad_b2

        ! Предварительные расчеты (вынесены из циклов для скорости)
        ! dzz - толщина верхнего полуслоя в метрах (dz1[см] -> м)
        dzz = dz1(1)/100.0
        ! dtz - коэффициент теплового баланса: dt/(dzz * rho_w * Cp_w)
        ! rho_w = 1028 кг/м³, Cp_w = 4186.8 Дж/кг/К -> 4.19e6 Дж/м³/К
        dtz = dt/(dzz*4.19e6)
        hour = 12.0 ! Условный полдень для солнечной радиации (из комментариев оригинала)

        ! --- ЦИКЛ ПО ГОРИЗОНТАЛЬНОЙ СЕТКЕ (I, J) ---
        do j = 1, js
            do i = 1, is
                ! Пропуск суши и замаскированных ячеек (ans=9.0 = суша)
                if (kt1(i, j) .eq. 0 .or. abs(ans(i, j) - 9.0) .lt. 1e-8) cycle

                ! --- ПОДГОТОВКА МЕТЕОРОЛОГИИ И ОКЕАНА ---
                ttac = tatm(i, j)           ! Температура воздуха [°C]
                tta = ttac + 273.15         ! Температура воздуха [K]
                ppatm = patm(i, j)*100.0    ! Атмосферное давление [Па] (гПа -> Па)
                ratm = ppatm/(287.0*tta)    ! Плотность воздуха [кг/м³] по идеальному газу
                twac = t1(i, j, 1)          ! Температура воды на поверхности [°C]
                twa = twac + 273.15         ! Температура воды [K]
                hhum = humid(i, j)          ! Относительная влажность [доли единицы]
                ww = wind(i, j)             ! Скорость геострофического ветра [м/с]
                cclo = cloud(i, j)          ! Облачность [доли единицы]
                a = s1(i, j, 1)             ! Соленость поверхностного слоя [массовая доля]

                ! --- ПОДГОТОВКА МАССИВОВ ЛЬДА ---
                ! Копируем в рабочие массивы для изменения внутри heat()
                do k = 1, ngr
                    anp(k) = an1(i, j, k + 1)      ! Площадь категории k
                    if (abs(anp(k)) .gt. 1e-8) then
                        hicp(k) = wice1(i, j, k)/anp(k)  ! Толщина льда = объем/площадь [м]
                        hsnp(k) = hsnow(i, j, k)       ! Толщина снега [м]
                    else
                        hicp(k) = 0.0
                        hsnp(k) = 0.0
                    end if
                    spar(k) = a                          ! Соленость внутри льда
                    tpar(k) = twa                        ! Температура внутри льда (K)
                end do

                ansum = ans(i, j)              ! Общая сплошность льда
                tfr = -54.0*spar(1)            ! Точка замерзания [°C] по формуле Зубова
                ! skt [м²/с], dz [см]: переводим толщину первого слоя в метры.
                ! fw [Вт/м²] - турбулентный поток тепла между водой и льдом.
                fw = 1028.0*4.1868e3*skt(i, j)*(t1(i, j, 1) - tfr)/(dz(1)*1.0e-2)
                if (fw .le. 0.0) fw = 0.0
                tfr = tfr + 273.15             ! Точка замерзания [K]

                ! --- СОЛНЕЧНАЯ РАДИАЦИЯ ---
                ! Солнечная высота и азимут для широты fi(i,j) и дня nday
                a1 = fi(i, j)/57.3
                a2 = sin(a1)
                b2 = cos(a1)
                b = 23.44*cos((172.0 - nday)/57.3)/57.3  ! Склонение Солнца
                a3 = sin(b)
                b3 = cos(b)

                ! Косинус зенитного угла (cz)
                cz = max(0.0, a2*a3 + b2*b3*cos((12.0 - hour)*0.2617994))

                ! Коротковолновая радиация на поверхности [Вт/м²]
                a1 = 1353.0*cz*cz*(1.0 - 0.6*cclo**3)
                rad_b1 = (cz + 2.7)*1.0e-5
                rad_b2 = 1.085*cz + 0.1
                ! Парциальное давление водяного пара
                e_vap = hhum*610.78*10.0**(8.61503*(tta - 273.15)/tta)
                sw = a1/(rad_b1*e_vap + rad_b2)
                ! Коэффициенты турбулентного обмена
                b3 = ratm*1.7068*ww
                a3 = 0.6650735*ratm/ppatm*ww
                ! Длинноволновая радиация (излучение атмосферы) [Вт/м²]
            wl = 5.4999e-8*tta**4*(1.0 - 0.261*exp(-7.77e-4*((273.15 - tta)**2)))*(1.0 + 0.275*cclo)

                ! --- ПОТОКИ И ОБРАЗОВАНИЕ ЛЬДА (ЧИСТАЯ ВОДА, КАТЕГОРИЯ 0) ---
                hfirst = 0.0
                ann1 = an1(i, j, 1)  ! Площадь открытой воды

                if (abs(ann1) .gt. 1e-8) then
                    ! Явное тепло [Вт/м²]
                    sh1 = b3*(tta - twa)
                    ! Скрытое тепло [Вт/м²]
           el1 = a3*2.5e6*(hhum*10.0**(7.63*ttac/(241.9 + ttac)) - 10.0**(7.63*twac/(241.9 + twac)))
                    ! Излучение воды [Вт/м²]
                    aaa = -0.97*5.67e-8*(twa**4)
                    ! Чистый тепловой баланс открытой воды [Вт/м²]
                    qn = sh1 + el1 + 0.97*wl + 0.9*sw + aaa

                    if (qn .gt. 0.0) then
                        ! Нагревание водой (qn>0 -> тепло идет в воду)
                        tpar(1) = tpar(1) + dtz*ann1*qn
                    else
                        ! Охлаждение воды
                        tpar(1) = tpar(1) + dtz*qn
                    end if

                    ! Проверка замерзания
                    if (tpar(1) .ge. tfr) then
                        if (tpar(1) .gt. tta .and. qn .gt. 0.0) tpar(1) = tta
                    else
                        tpar(1) = tfr
                        hfirst = 0.01  ! Начальная толщина нового льда [м]
                    end if
                end if

                ! --- ТЕРМОДИНАМИКА ЛЬДА (ЦИКЛ ПО КАТЕГОРИЯМ ТОЛЩИН) ---
                do k = 1, ngr
                    k1 = k + 1
                    if (anp(k) .lt. 0.001) cycle  ! Пропуск пустых категорий

                    dhsn = 0.0       ! Приращение снега [м]
                    dhic1 = 0.0      ! Приращение льда сверху [м]
                    tts = 0.5*(tta + twa)  ! Начальная оценка температуры поверхности [K]
                    ! Скрытое тепло для льда/снега [Вт/м²]
    el = a3*2.834e6*(hhum*10.0**(9.5*ttac/(265.5 + ttac)) - 10.0**(9.5*(tts - 273.15)/(tts - 7.65)))
                    hhic1 = 1.0/max(hicp(k), 1.0e-6) ! Защита от деления на ноль

                    if (abs(hsnp(k)) .lt. 1e-8) then
                        ! === ЛЕД БЕЗ СНЕГА ===
                        ! Теплопроводность льда: b = 2.04/hicp [Вт/м²/К]
                        b = 2.04*hhic1
                        err = 100.0
                        err1 = 100.0
                        n_iter = 0
                        ! Итерационное решение уравнения теплового баланса (Ньютон-Рафсон)
                        do while (err .ge. 0.25 .and. n_iter .lt. 100)
                            n_iter = n_iter + 1
                            sh = b3*(tta - tts)              ! Явное тепло
                            a = 5.4999e-8*tts**3             ! d(εσT⁴)/dT
                            a1 = sh + el + 0.466*sw + 0.97*wl  ! Сумма потоков без длинноволновки льда
                            dtts = (a1 - a*tts + b*(tfr - tts))/(4.0*a + b)
                            a_tmp = tts + dtts
                            err1 = err
                            err = abs(dtts)
                            if (err .ge. err1) exit
                            tts = a_tmp
                        end do
                        if (err .ge. err1 .or. n_iter .eq. 100) tts = tta

                        if (tts .le. 273.15) then
                            ! Нарастание снега: локальный ERA5 снегопад
                            dhsn = dt*era5_snowfall_rate(i, j)
                            hsnp(k) = dhsn
                        else
                            ! Таяние: температура поверхности = 273.15 K
                            tts = 273.15
                            ! dhic1 = -dt/ρL * (потоки) [м]
                            dhic1 = -dt/302.e6*(a1 - 5.4999e-8*tts**4 + b*(tfr - tts))
                            hicp(k) = hicp(k) + dhic1
                            if (hicp(k) .lt. 0.01) hicp(k) = 0.0
                        end if

                        ! Нарастание/таяние снизу (водный поток fw)
                        dhic = -dt/302.e6*(fw - b*(tfr - tts))
                        hicp(k) = hicp(k) + dhic
                        if (hicp(k) .lt. 0.01) then
                            hicp(k) = 0.0
                            hsnp(k) = 0.0
                        end if

                    else
                        ! === ЛЕД СО СНЕГОМ ===
                        ! Комбинированная теплопроводность снега + льда
                        b1 = 0.31*hicp(k)   ! Вклад льда
                        b2 = 2.04*hsnp(k)   ! Вклад снега
                        b4 = b1 + b2
                        b = 0.6324/b4       ! Эффективная теплопроводность
                        err = 100.0
                        err1 = 100.0
                        n_iter = 0
                        do while (err .ge. 0.25 .and. n_iter .lt. 100)
                            n_iter = n_iter + 1
                            sh = b3*(tta - tts)
                            a = 5.6133e-8*tts**3  ! Стефана-Больцмана для снега
                            a1 = sh + el + (1.0 - alsn(lll))*sw + 0.99*wl  ! Альбедо снега!
                            dtts = (a1 - a*tts + b*(tfr - tts))/(4.0*a + b)
                            a_tmp = tts + dtts
                            err1 = err
                            err = abs(dtts)
                            if (err .ge. err1) exit
                            tts = a_tmp
                        end do
                        if (err .ge. err1 .or. n_iter .eq. 100) tts = tta

                        if (tts .le. 273.15) then
                            ! Нарастание снега на существующем снеге: локальный ERA5 снегопад
                            dhsn = era5_snowfall_rate(i, j)*dt
                            ! Температура границы лед-снег
                            tti = (b1*tts + b2*tfr)/b4
                        else
                            tts = 273.15
                            tti = (b1*273.15 + b2*tfr)/b4
                            ! Таяние снега: скрытая теплота снега 110e6 Дж/м³
                            dhsn = -dt/110.e6*(a1 - 5.6133e-8*tts**4 + 0.31/hsnp(k)*(tti - tts))
                        end if

                        ! Изменение толщины льда (водный поток + теплопроводность)
                        dhic = dt/302.e6*(2.04*(tfr - tti)/hicp(k) - fw)
                        hicp(k) = hicp(k) + dhic
                        if (hicp(k) .ge. 0.01) then
                            ! Ограничение толщины снега: hsnow <= 0.1 * hice
                            a_tmp = 0.1*hicp(k)
                            hsnp(k) = hsnp(k) + dhsn
                            if (hsnp(k) .gt. a_tmp) hsnp(k) = a_tmp
                            if (hsnp(k) .lt. 0.0) hsnp(k) = 0.0
                        else
                            hicp(k) = 0.0
                            hsnp(k) = 0.0
                        end if
                    end if

                    ! --- НОВАЯ ТЕМПЕРАТУРА И СОЛЕНОСТЬ ПОСЛЕ ФАЗОВЫХ ПЕРЕХОДОВ ---
                    a_tmp = 0.88*dhic
                    b_tmp = dzz - a_tmp
                    if (dhic .lt. 0.0) then
                        ! Таяние: отбрасывается соль, температура замерзания
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
                        ! Нарастание: соль замораживается в лед
                        spar(k1) = (spar(k1)*dzz - sicst(k)*a_tmp)/b_tmp
                        tfr_new = -54.0*spar(k1) + 273.15
                        tpar(k1) = tfr_new
                    end if

                    ! Обновление глобальных массивов
                    hsnow(i, j, k) = hsnp(k)
                    hice(i, j, k) = hicp(k)
                    if (abs(hicp(k)) .lt. 1e-8) then
                        ann1 = ann1 + anp(k)
                        an1(i, j, k1) = 0.0
                        anp(k) = 0.0
                    end if
                end do ! Конец цикла по NGR

                ! --- ТАЯНИЕ В РАЗВОДЬЯХ ---
                ! Если есть открытая вода и положительный тепловой баланс
                if (ann1 .gt. 0.0 .and. ann1 .lt. 1.0 .and. qn .gt. 0.0) then
                    a_tmp = ann1*qn*dt
                    b_tmp = 0.0
                    a3_tmp = 0.0
                    b3_tmp = 0.0
                    do k = 1, ngr
                        if (abs(hicp(k)) .gt. 1e-8) then
                            k1 = k + 1
                            ! Площадь не может стать отрицательной за один шаг таяния.
                            danp(k) = min(anp(k), anp(k)*a_tmp/(302.e6*hicp(k) + 110.e6*hsnp(k)))
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
