! ==============================================================================
! Модуль: main (Главная программа)
! Назначение: Главный оркестратор гидродинамической и термодинамической модели.
! Физика: Реализует метод расщепления (splitting method). Управляет вложенными
!         циклами по времени: межгодовыми, сезонными, бароклинными (медленными, dt)
!         и баротропными (быстрыми, dt1). Синхронизирует передачу импульса, тепла
!         и солености на границах раздела фаз "океан-лед-атмосфера".
! Ответственность: Инициализация полей, контроль временных шагов, вызов
!                  вспомогательных модулей в строгой физической последовательности,
!                  управление процессами ввода (ERA5) и вывода (NetCDF) данных.
! ==============================================================================

program main
    use param
    use advection_2d
    use thermodynamics
    use wind_forcing
    use ice_stress
    use grid_masks
    use ice_deform
    use ice_redis
    use smooth_filter
    use advection_3d_s
    use advection_3d_t
    use tide_forcing
    use shallow_water, only: shal, jjq, euu
    use grid_coupling
    use netcdf_output
    use initial_conditions
    use netcdf_input
    use equation_of_state
    use convective_adjustment

    implicit none

    ! --- Локальные переменные ---
    real :: god, mes, den, hour
    integer :: kl1, nom, mm1, mm2, mm3, mm4, mm5, kkb
    real :: dt1, dt, dx, ah, aht, ahs, g, roc, cp
    real :: c1, c2, c3, c4, c5, c8, c9, c10, c11, c12, c15, c16, c17
    real :: sas, a, b, a1, b1, a2, b2, a3, b3, a4, b4, cc_val
    real :: hht, uij, vij, fix, fiy, aa, au, av, sl, du, ff, ff1
    real :: dzz, dzzz, dzz1, dz1z, bb, sum, sum1, asa1, asa, ymm, hh1, hh2
    real :: tt0, ss0, tt1, ss1, tt2, ss2, tt3, ss3, tt4, ss4, yyy, uu, vv
    real :: ri2j, rij, ri2j2, rij2, slapu, slapv, auu, avv
    real :: ck1, ck2, ww1, ww2, ww

    integer :: mmmm, lll, kkk, iii, jjj
    integer :: i, j, k, i1, i2, j1, j2, k1, k2, ki, kk, ki1, ki2
    integer :: ix1, ix2, iy1, iy2
    integer :: nday, nday1, ikkk, ios

    real :: ecc = 0.0, ess = 0.0
    character(len=20) :: nam_file
    character(len=64) :: day_file
    real(8) :: start_sec
    integer :: nperday

    print *, "================================================="
    print *, "   AARI Iceberg Thermodynamic & Dynamics Model   "
    print *, "================================================="

    ! --- Инициализация времени и параметров ---
    god = 1998.0        ! Начальный год моделирования (Гринвич)
    mes = 4.0           ! Начальный месяц моделирования (апрель)
    den = 16.0          ! Начальный день месяца
    hour = 0.0          ! Начальный час суток

    nat(1) = int(god)
    nat(2) = int(mes)
    nat(3) = int(den)
    nat(4) = int(hour)

    kl1 = 0             ! Флаг чтения климатических данных (0 - нет, 1 - да)
    nom = 1             ! Идентификатор чтения начальных данных
    ! Временный переключатель для отладки ERA5 input (этап 2/3).
    forcing_mode = forcing_mode_era5

    ! --- Временные и пространственные шаги сетки ---
    dt1 = 120.0         ! Шаг баротропной моды (сек)
    dt = 3600.0         ! Шаг бароклинной моды и термодинамики (сек)
    mm1 = 60            ! Количество циклов моделирования в месяце (дни)
    mm2 = 12            ! Количество шагов с термодинамическим шагом (DT) за сутки
    mm3 = 30            ! Количество баротропных микрошагов за бароклинный шаг (DT/DT1)
    mm4 = 1             ! Количество расчетных месяцев
    mm5 = 1             ! Количество расчетных лет
    dx = 1389000.0      ! Пространственный шаг сетки (см), ~13.8 км
    kkb = 1             ! Начальный индекс метеоданных
    ikkk = 0            ! Счетчик диагностических записей
    nday = 0            ! Счетчик дней внутри месяца
    nday1 = 0           ! Общий счетчик дней модельного времени

    ! --- Физические константы модели ---
    ah = 7.5e6          ! Коэффициент горизонтальной турбулентной диффузии импульса
    aht = 7.5e6         ! Коэффициент горизонтальной диффузии тепла
    ahs = 7.5e6         ! Коэффициент горизонтальной диффузии солености
    g = 981.0           ! Ускорение силы тяжести (см/с²)
    roc = 1.0           ! Характерная плотность воды (г/см³)
    cp = 0.958          ! Удельная теплоемкость / эмпирический коэффициент

    ! --- Расчетные вспомогательные константы ---
    c1 = g/roc
    c2 = dt/dx
    c3 = ah/(dx*dx)
    c4 = aht/(dx*dx)*dt
    c5 = ahs/(dx*dx)*dt
    c8 = 0.25/dx
    c9 = 0.5/dx
    c10 = dt1/dx
    c11 = g/dx*0.005
    c12 = 1.0/dx
    c15 = cos(15.0/57.3)
    c16 = sin(15.0/57.3)
    c17 = 0.0055*1000.0/910.0

    ! --- Чтение приливных гармоник (с защитой iostat) ---
    amp1 = 0.0
    amp2 = 0.0
    amp3 = 0.0
    faz1 = 0.0
    faz2 = 0.0
    faz3 = 0.0
    open (3, file='GRM2', status='old', iostat=ios)
    if (ios .eq. 0) then
        read (3, *) (amp1(i, 1), i=1, 133)
        read (3, *) (faz1(i, 1), i=1, 133)
        read (3, *) (amp2(i, 1), i=1, 105)
        read (3, *) (faz2(i, 1), i=1, 105)
        read (3, *) (amp3(i, 1), i=1, 133)
        read (3, *) (faz3(i, 1), i=1, 133)
        close (3)
    else
        print *, "WARNING: GRM2 missing, using defaults"
    end if

    ! Инициализация частот приливных гармоник (M2, S2, K1, O1)
    qq(1) = 28.9841042
    qq(2) = 30.0
    qq(3) = 15.041069
    qq(4) = 13.943036

    call datte()

    q(1:4) = qq(1:4)*dt1/3600.0/57.2958

    ! --- Вызов модулей инициализации сетки и геометрии ---
    print *, "Calling grid_coupling..."
    call coup1()

    print *, "Calling grid_masks (IKUV)..."
    call ikuv()

    ! --- Чтение метеоданных и стартовых полей льда ---
    p = 0.0
    open (1, file='DAV4_5.98', status='old', iostat=ios)
    if (ios .eq. 0) then
        read (1, *) mm1
        do j = 1, mm1 + 1
            read (1, *)
            do i = 1, 1420
                read (1, *) a, a, a, p(i, j)
            end do
        end do
        close (1)
    end if

    ! Чтение начальных толщин категорий льда
    an1 = 0.0
    wice1 = 0.0
    hsnow = 0.0
    u = 0.0
    v = 0.0
    u0 = 0.0
    v0 = 0.0
    exx = 0.0
    eyy = 0.0
    exy = 0.0
    epr = 0.0
    sxx = 0.0
    syy = 0.0
    sxy = 0.0
    do k = 2, 6
        write (nam_file, '(A,I1,A)') '1_', k - 1, '.ice'
        open (1, file=trim(nam_file), status='old', iostat=ios)
        if (ios .eq. 0) then
            do i = 1, is1
                read (1, *) (an1(i, j, k), j=1, js1)
            end do
            close (1)
        end if
    end do

    ! Первичная очистка и нормировка ледовых массивов
    do j = 1, js1
        do i = 1, is1
            sas = 0.0
            do k = 2, ngr1
                if (abs(an1(i, j, k) - 9.99) .lt. 1e-8) an1(i, j, k) = 0.0
                if (an1(i, j, k) .ge. 1.0) an1(i, j, k) = 1.0
                sas = sas + an1(i, j, k)
            end do
            ! Безопасное сравнение вещественного числа с нулем устраняет предупреждение -Wcompare-reals
            if (abs(sas) .lt. 1e-8) an1(i, j, 1) = 1.0

            wice1(i, j, 1) = 0.20*an1(i, j, 2)
            wice1(i, j, 2) = 0.40*an1(i, j, 3)
            wice1(i, j, 3) = 0.95*an1(i, j, 4)
            wice1(i, j, 4) = 1.60*an1(i, j, 5)
            wice1(i, j, 5) = 2.50*an1(i, j, 6)
        end do
    end do

    call redis()

    ! --- Инициализация синтетических полей ---
    call init_ocean()

    ! Диагностика уравнения состояния (этап 3.1): расчет RO из T2/S2
    ! в диагностическом режиме. Пока НЕ используется в уравнениях движения.
    call eos_diag()

    ! Записываем состояние океана ДО начала расчета (День 0)
    call write_nc('data/output/results_day_00.nc')

    ! ====================================================================
    !              ЧТЕНИЕ АТМОСФЕРНОГО ФОРСИНГА ERA5 (NetCDF)
    ! ====================================================================
    ! Этап 2/3: чтение и диагностика. Открываем файл полного месяца (январь
    ! 2020). Пока это только проверка канала ввода; подключение к физике
    ! (wind/tx/ty/dpx/dpy/tatm/patm) выполняется на следующих этапах.
    ! При ошибке чтения модель продолжает работу в legacy-режиме (без ERA5).
    if (forcing_mode .eq. forcing_mode_era5) then
        call era5_open('data/input/raw/era5/era5_2020_01.nc', ios)
        if (ios .eq. 0) then
            call era5_diag()

            ! Временной интерфейс: модельные сутки привязываются к первому
            ! ERA5-срезу (nearest-time, документированное допущение первого
            ! этапа). start_sec = время первого среза в секундах с эпохи.
            start_sec = era5_time(1)

            ! Ограничиваем прогон числом суток, покрытых ERA5-данными,
            ! чтобы модель не выходила за пределы входных данных.
            nperday = nint(86400.0_8/max(era5_time(2) - era5_time(1), 1.0_8))
            mm1 = min(mm1, (era5_ntime - 1)/max(nperday, 1))
            print *, "ERA5: run limited to ", mm1, " days (", era5_ntime, &
                " time steps, ", nperday, " steps/day)"
        else
            print *, "WARNING: ERA5 input failed, falling back to legacy forcing."
            forcing_mode = forcing_mode_legacy
        end if
    end if

    ! ====================================================================
    !                    ГЛАВНЫЙ ЦИКЛ ПО ВРЕМЕНИ
    ! ====================================================================
    print *, "Starting Main Integration Loop..."

    pp(:) = p(:, kkb)
    if (forcing_mode .eq. forcing_mode_era5) then
        call era5_wind(start_sec)
    else
        call wind1()
    end if

    do mmmm = 1, mm5
        nday = 0
        do lll = 1, mm4
            do kkk = kkb, mm1
                nday = nday + 1
                nday1 = nday1 + 1

                if (nday1 .eq. 42) exit

                ess = euu - ecc
                print *, "Day:", kkk, " Month:", lll, " Kin.Energy(EUU)=", euu
                ecc = euu
                euu = 0.0

                ! Сброс суточных счётчиков convective adjustment (этап 4.2).
                call ca_reset()

                dpx(:, :) = dpx1(:, :)
                dpy(:, :) = dpy1(:, :)
                windx(:, :) = windx1(:, :)
                windy(:, :) = windy1(:, :)
                tx(:, :) = tx1(:, :)
                ty(:, :) = ty1(:, :)

                pp(:) = p(:, kkk + 1)
                if (forcing_mode .eq. forcing_mode_era5) then
                    call era5_wind(start_sec + real(kkk, 8)*86400.0_8)
                else
                    call wind1()
                end if

                do iii = 1, mm2
                    ! 1. Временная интерполяция ветровых напряжений
                    if (iii .ne. 1) then
                        b = real(mm2 - iii + 2)
                        tx = tx + (tx1 - tx)/b
                        ty = ty + (ty1 - ty)/b
                        dpx = dpx + (dpx1 - dpx)/b
                        dpy = dpy + (dpy1 - dpy)/b
                        windx = windx + (windx1 - windx)/b
                        windy = windy + (windy1 - windy)/b
                    end if

                    ! windx/windy хранят см/с, а heat использует модуль скорости в м/с.
                    wind = sqrt(windx*windx + windy*windy)*1.0e-2

                    t1 = t2
                    s1 = s2
                    v1 = v2
                    u1 = u2

                    ! Термодинамика должна идти с тем же шагом, что и океан.
                    ! Без ERA5-полей (kl1=0) вызов дал бы деление на patm=0.
                    if (kl1 .eq. 1) then
                        call heat(dt, nday, lll)
                        ! heat меняет категории; динамике льда нужны новые A и h.
                        call redis()
                    end if

                    ! 3. Динамика льда (баротропные подциклы)
                    do jjj = 1, mm3
                        u0 = u
                        v0 = v
                        txic = 0.0
                        tyic = 0.0

                        call stress()

                        do j = 2, js
                            j1 = j + 1
                            j2 = j - 1
                            do i = 2, is
                                i1 = i + 1
                                i2 = i - 1
                                if (kk1(i, j) .eq. 0) cycle

                              hht = 0.25*(hices(i, j) + hices(i, j2) + hices(i2, j) + hices(i2, j2))
                                if (hht .lt. 0.01) then
                                    u(i, j) = 0.0
                                    v(i, j) = 0.0
                                    cycle
                                end if

                                uij = u0(i, j)
                                vij = v0(i, j)
                                a1 = u2(i, j, 1)/100.0
                                b1 = v2(i, j, 1)/100.0
                                a = a1 - uij
                                b = b1 - vij
                                a = c17*sqrt(b*b + a*a)/hht

                                txic(i, j) = a*(a1*c15 - b1*c16)
                                tyic(i, j) = a*(b1*c15 + a1*c16)

                                a3 = 0.25*(ans(i, j) + ans(i, j2) + ans(i2, j) + ans(i2, j2))
                                if (a3 .gt. 2.0) cycle

                                a4 = sxy(i2, j) - sxy(i, j2)
                                b4 = sxy(i, j) - sxy(i2, j2)
                             fix = (sxx(i2, j) + sxx(i, j) - sxx(i2, j2) - sxx(i, j2) + a4 - b4)*c12
                             fiy = (syy(i2, j2) + syy(i2, j) - syy(i, j2) - syy(i, j) + a4 + b4)*c12

                                b3 = hht*9100.0
                                a2 = uij + dt1*(tx(i, j)/b3 + txic(i, j)*a3 + fku(i, j)*vij - &
                                c11*(ym2(i2, j) - ym2(i2, j2) + ym2(i, j) - ym2(i, j2)) + fix/910.0)
                                b2 = vij + dt1*(ty(i, j)/b3 + tyic(i, j)*a3 - fku(i, j)*uij - &
                                c11*(ym2(i2, j2) - ym2(i, j2) + ym2(i2, j) - ym2(i, j)) + fiy/910.0)

                                b1 = dt1*a*c16
                                a1 = 1.0 + dt1*a*c15
                                aa = a1*a1 + b1*b1
                                u(i, j) = (a1*a2 + b1*b2)/aa
                                v(i, j) = (a1*b2 - b1*a2)/aa

                                if (jjj .eq. mm3) then
                                    b3 = hht*9100.0
                                    txic(i, j) = -(txic(i, j) - a*(u(i, j)*c15 - v(i, j)*c16))*b3
                                    tyic(i, j) = -(tyic(i, j) - a*(v(i, j)*c15 + u(i, j)*c16))*b3
                                end if
                            end do
                        end do

                        ! Граничные условия ледового блока
                        u(:, 1) = u(:, 2)
                        v(:, 1) = v(:, 2)
                        u(:, js1) = u(:, js)
                        v(:, js1) = v(:, js)
                        u(1, :) = u(2, :)
                        v(1, :) = v(2, :)
                    end do

                    ! 4. Адвекция сплошности и массы льда

                    ! 4. Адвекция сплошности и массы льда
                    do k = 1, ngr
                        k1 = k + 1
                        an3(:, :) = an1(:, :, k1)
                        call adv2d(dt, dx, c2)
                        an3(:, js) = an1(:, js, k1)
                        an3(1, :) = an1(1, :, k1)
                        an1(:, :, k1) = an3(:, :)

                        an3(:, :) = wice1(:, :, k)
                        call adv2d(dt, dx, c2)
                        an3(:, js) = wice1(:, js, k)
                        an3(1, :) = wice1(1, :, k)
                        wice1(:, :, k) = an3(:, :)
                    end do
                    call redis()

                    ! 5. Расчет вертикальной составляющей скорости течений (W)
                    do j = 2, js
                        j1 = j + 1
                        j2 = j - 1
                        do i = 2, is
                            i1 = i + 1
                            i2 = i - 1
                            ix1 = idx(i, j)
                            ix2 = idx(i, j1)
                            ki = kt1(i, j)
                            if (ki .eq. 0) cycle

                            iy1 = idy(i, j)
                            iy2 = idy(i1, j)

                            do k = 1, ki
                                a = u1(i, j, k) + u1(i1, j, k)
                                aa = u1(i, j1, k) + u1(i1, j1, k)
                                if (k .eq. 1) au = a + aa
                                if (ix1 .lt. k .or. ix2 .lt. k) then
                                    tt(k) = 0.0
                                else
                                    tt(k) = aa - a
                                end if

                                b = v1(i, j, k) + v1(i, j1, k)
                                bb = v1(i1, j, k) + v1(i1, j1, k)
                                if (k .eq. 1) av = b + bb
                                if (iy1 .lt. k .or. iy2 .lt. k) then
                                    ss(k) = 0.0
                                else
                                    ss(k) = b - bb
                                end if
                            end do

                            ymm = ym2(i, j)
                            if (ix1 .eq. 0 .and. ix2 .ne. 0) then
                                hh1 = ymm - ym2(i, j2)
                            else if (ix1 .ne. 0 .and. ix2 .eq. 0) then
                                hh1 = ym2(i, j1) - ymm
                            else if (ix1 .ne. 0 .and. ix2 .ne. 0) then
                                hh1 = 0.5*(ym2(i, j1) - ym2(i, j2))
                            else
                                hh1 = 0.0
                            end if

                            if (iy1 .eq. 0 .and. iy2 .ne. 0) then
                                hh2 = ymm - ym2(i1, j)
                            else if (iy1 .ne. 0 .and. iy2 .eq. 0) then
                                hh2 = ym2(i2, j) - ymm
                            else if (iy1 .ne. 0 .and. iy2 .ne. 0) then
                                hh2 = 0.5*(ym2(i2, j) - ym2(i1, j))
                            else
                                hh2 = 0.0
                            end if

                            a = -(ymm - ym1(i, j))/dt - (hh1*au + hh2*av)*c8
                            w(i, j, 1) = a
                            ym1(i, j) = ymm

                            if (ki .ge. 2) then
                                do k = 2, ki
                                    k2 = k - 1
                                    a = a - (tt(k2) + ss(k2))*dz1(k2)*c9
                                    w(i, j, k) = a
                                end do
                            end if
                        end do
                    end do

                    ! 6. Адвекция солености и температуры в океане
                    call advs(dt, c2)
                    call advt(dt, c2)

                    ! Конвективная коррекция плотностной стратификации (этап 3.2):
                    ! историческая схема перемешивания при RR(K)-RR(K1) > 0.9E-7.
                    ! RO пока НЕ используется в уравнениях движения (этапы 3.1-3.2).
                    call conv_adj()

                    ! 6b. 3D-импульс (этап 3.3): исторический block 200.
                    !    U2/V2 из U1/V1 (предыдущий бароклинный шаг) с учётом:
                    !    - Coriolis (FKU);
                    !    - баротропно-баротроклинного интеграла плотности SUM/SUM1;
                    !    - градиента атмосферного давления DPX/DPY;
                    !    - горизонтальной диффузии импульса (SLAPU/SLAPV).
                    !    Источник: Coupl1.f90:880-940 (идентичен Nesterov_last).
                    !    Единицы: U2/V2 [см/с], RO [г/см3], DPX/DPY [см/с2].
                    do j = 2, js
                        do i = 2, is
                            ki = kk1(i, j)
                            if (ki .eq. 0) cycle
                            i1 = i + 1
                            i2 = i - 1
                            j1 = j + 1
                            j2 = j - 1
                            hht = map1(i, j)
                            if (abs(hht - 8888.0) .lt. 1e-8) cycle
                            sum = 0.0
                            sum1 = 0.0
                            asa1 = fku(i, j)*0.5*dt
                            asa = 1.0 + asa1*asa1
                            ri2j = ro(i2, j, 1)
                            rij = ro(i, j, 1)
                            ri2j2 = ro(i2, j2, 1)
                            rij2 = ro(i, j2, 1)
                            a = ri2j + rij - ri2j2 - rij2
                            b = ri2j2 + ri2j - rij2 - rij
                            dzz = dz(1)
                            do k = 1, ki
                                if (abs(hht - z(k)) .lt. 1e-6) then
                                    u2(i, j, k) = 0.0
                                    v2(i, j, k) = 0.0
                                    cycle
                                end if
                                k1 = k + 1
                                dzz1 = dz(k1)
                                uij = u1(i, j, k)
                                vij = v1(i, j, k)
                                ri2j = ro(i2, j, k)
                                rij2 = ro(i, j2, k)
                                rij = ro(i, j, k)
                                ri2j2 = ro(i2, j2, k)
                                a1 = ri2j + rij - ri2j2 - rij2
                                b1 = ri2j2 + ri2j - rij2 - rij
                                cc_val = c8*dzz
                                sum = sum + (a + a1)*cc_val
                                sum1 = sum1 + (b + b1)*cc_val
                         slapu = u1(i, j2, k) + u1(i, j1, k) + u1(i2, j, k) + u1(i1, j, k) - 4.0*uij
                         slapv = v1(i1, j, k) + v1(i2, j, k) + v1(i, j1, k) + v1(i, j2, k) - 4.0*vij
                                auu = uij + asa1*vij + dt*(-c1*sum - dpx(i, j) + c3*slapu)
                                avv = vij - asa1*uij + dt*(-c1*sum1 - dpy(i, j) + c3*slapv)
                                u2(i, j, k) = (auu + avv*asa1)/asa
                                v2(i, j, k) = (avv - auu*asa1)/asa
                                a = a1
                                b = b1
                                dzz = dzz1
                            end do
                        end do
                    end do

                    ! 6c. Вертикальная вязкость (этап 3.3): исторический block 210.
                    !    Коэффициенты NU = L*L*|dU/dz|, решение трёхдиагональной
                    !    системы (прямой/обратный ход Томаса). Поверхностное
                    !    условие: (1-A1)*TX + A1*TXIC (взвешивание по сплочённости).
                    !    Источник: Coupl1.f90:942-1020 (идентичен Nesterov_last).
                    do j = 2, js
                        do i = 2, is
                            ki = kk1(i, j)
                            if (ki .eq. 0) cycle
                            i2 = i - 1
                            j2 = j - 1
                            hht = map1(i, j)
                            if (abs(hht - 8888.0) .lt. 1e-8) cycle
                            ki1 = ki + 1
                            ki2 = ki - 1
                            yyy = 0.25*(ym2(i2, j2) + ym2(i, j2) + ym2(i2, j) + ym2(i, j))
                            uij = u2(i, j, 1)
                            vij = v2(i, j, 1)
                            aa = sqrt(uij*uij + vij*vij)
                            do k = 1, ki
                                k1 = min(k + 1, ks)
                                uij = u2(i, j, k1)
                                vij = v2(i, j, k1)
                                bb = sqrt(uij*uij + vij*vij)
                                ff = hht - z(k) + 2.0
                                ff1 = z(k) - yyy - 2.0
                               sl = 0.4/hht*ff*ff1*(1.0 - 1.2*ff*ff1/hht/hht)/(4.0*ff1/5000.0 + 1.0)
                                if (k .ne. ki) then
                                    rr(k) = sl*sl*abs(bb - aa)/dz(k1)
                                else
                                    rr(k) = sl*sl*abs(bb - aa)/(hht - z(ki) + 50.0)
                                end if
                                aa = bb
                            end do
                            skz(i, j) = rr(1)
                            if (ki .ne. 1) then
                                dzz = dz1(1)
                                dzzz = dz(2)
                            else
                                dzz = hht
                                dzzz = hht - z(1) + 50.0
                            end if
                            b = dt/dzz/dzzz*rr(1)
                            a = 1.0 + b
                            uca(1) = b/a
                            a1 = 0.25*(ans(i, j) + ans(i, j2) + ans(i2, j) + ans(i2, j2))
                            unu(1) = (u2(i, j, 1) + dt/dzz*((1.0 - a1)*tx(i, j) + a1*txic(i, j)))/a
                            vca(1) = uca(1)
                            vnu(1) = (v2(i, j, 1) + dt/dzz*((1.0 - a1)*ty(i, j) + a1*tyic(i, j)))/a
                            if (ki .eq. 1) then
                                u2(i, j, ki) = uca(ki)*u2(i, j, ki1) + unu(ki)
                                v2(i, j, ki) = vca(ki)*v2(i, j, ki1) + vnu(ki)
                            else if (ki .ge. 2) then
                                if (ki .ge. 3) then
                                    do k = 2, ki2
                                        k2 = k - 1
                                        aa = dt/dz1(k)
                                        a = -aa/dz(k)*rr(k2)
                                        b = -aa/dz(k + 1)*rr(k)
                                        a1 = -1.0 + a + b
                                        aa = a1 - uca(k2)*a
                                        uca(k) = b/aa
                                        unu(k) = (a*unu(k2) - u2(i, j, k))/aa
                                        aa = a1 - vca(k2)*a
                                        vca(k) = b/aa
                                        vnu(k) = (a*vnu(k2) - v2(i, j, k))/aa
                                    end do
                                end if
                                dzz = hht - 0.5*(z(ki) + z(ki2))
                                dzzz = hht - z(ki) + 50.0
                                b = dt/dzz/dz(ki)*rr(ki2)
                                a = 1.0 + b + dt/dzz/dzzz*rr(ki)
                                bb = b/a
                                u2(i, j, ki) = (u2(i, j, ki)/a + bb*unu(ki2))/(1.0 - bb*uca(ki2))
                                v2(i, j, ki) = (v2(i, j, ki)/a + bb*vnu(ki2))/(1.0 - bb*vca(ki2))
                                do k = 1, ki2
                                    kk = ki - k
                                    k1 = kk + 1
                                    u2(i, j, kk) = uca(kk)*u2(i, j, k1) + unu(kk)
                                    v2(i, j, kk) = vca(kk)*v2(i, j, k1) + vnu(kk)
                                end do
                            end if
                        end do
                    end do

                    ! 7. Баротропный расчет мелкой воды и уровня моря
                    call shal()

                    ! 8. Возврат баротропной компоненты в 3D-поле скоростей
                    !    (этап 3.3): исторический block 280.
                    !    Обнуляет вертикальное среднее баротроклинной части U':
                    !    SUM = -SUM_U2*DZZ/HHT + 0.5*(UP2+UP2)/HHT,
                    !    U2 = U2 + SUM. Источник: Coupl1.f90:1031-1058.
                    do j = 2, js
                        do i = 2, is
                            ki = kk1(i, j)
                            if (ki .eq. 0) cycle
                            i2 = i - 1
                            j2 = j - 1
                            hht = map1(i, j)
                            if (abs(hht - 8888.0) .lt. 1e-8) cycle
                            sum = 0.0
                            sum1 = 0.0
                            do k = 1, ki
                                k1 = k + 1
                                if (k .eq. ki) then
                                    if (ki .ne. 1) then
                                        dzz = hht - 0.5*(z(ki) + z(ki - 1))
                                    else
                                        dzz = hht
                                    end if
                                else
                                    dzz = dz1(k)
                                end if
                                sum = u2(i, j, k)*dzz + sum
                                sum1 = v2(i, j, k)*dzz + sum1
                            end do
                            sum = (-sum + 0.5*(up2(i, j) + up2(i2, j)))/hht
                            sum1 = (-sum1 + 0.5*(vp2(i, j) + vp2(i, j2)))/hht
                            do k = 1, ki
                                u2(i, j, k) = u2(i, j, k) + sum
                                v2(i, j, k) = v2(i, j, k) + sum1
                            end do
                        end do
                    end do

                    ! Диагностика 3D-скоростей (этап 3.3): min/max U2,V2 после всех блоков
                    if (kkk .le. 2) then
                        uu = 0.0
                        vv = 0.0
                        aa = 0.0
                        do j = 2, js
                            do i = 2, is
                                if (kk1(i, j) .eq. 0) cycle
                                do k = 1, kt1(i, j)
                                    if (u2(i, j, k) .ne. u2(i, j, k)) aa = 1.0
                                    if (v2(i, j, k) .ne. v2(i, j, k)) aa = 1.0
                                    uu = max(uu, abs(u2(i, j, k)))
                                    vv = max(vv, abs(v2(i, j, k)))
                                end do
                            end do
                        end do
                        print '(A,I1,A,I3,A,E12.4,A,E12.4,A,E12.4)', &
                            "B3.3 d=", kkk, " III=", iii, " maxU2=", uu, &
                            " maxV2=", vv, " NaNflag=", aa
                    end if

                end do ! Конец суточного цикла III

                ! --- Суточный диагностический вывод (этап 4.2) ---
                ! Пишем NetCDF-срез за сутки kkk и строку CSV со статистиками
                ! (U/V/W/T/S/RO min/max/mean, ветер, напряжения, градиенты,
                !  кинетическая энергия EUU, счётчики convective adjustment).
                write (day_file, '(A,I2.2,A)') 'data/output/results_day_', kkk, '.nc'
                call write_nc(trim(day_file))
                call write_daily_diagnostics(kkk, lll)
            end do ! Конец цикла дней KKK
        end do ! Конец цикла месяцев LLL
    end do ! Конец цикла лет MMMM

    print *, "Integration completed successfully!"

    ! Диагностика уравнения состояния после 5 дней (этап 3.1)
    call eos_diag()

    ! Записываем финальное состояние океана после интеграции.
    ! Суточные срезы записаны внутри цикла как results_day_01.nc...30.nc,
    ! поэтому финальный файл назван отдельно и не затирает суточный срез.
    call write_nc('data/output/results_day_final.nc')

contains

    ! ==========================================================================
    ! write_daily_diagnostics: суточная диагностика (этап 4.2).
    ! Считает min/max/mean U/V/W/T/S/RO по водным колонкам, max ветра,
    ! min/max напряжений и градиентов давления, кинетическую энергию EUU
    ! и суточные счётчики convective adjustment. Аппендит одну CSV-строку.
    ! Ничего в физике не меняет - только диагностический вывод.
    ! ==========================================================================
    subroutine write_daily_diagnostics(day, month)
        integer, intent(in) :: day, month

        integer, parameter :: diag_unit = 77
        real :: u_min, u_max, u_sum, v_min, v_max, v_sum
        real :: w_min, w_max, w_sum, t_min, t_max, t_sum
        real :: s_min, s_max, s_sum, ro_min, ro_max, ro_sum
        real :: wind_max, tx_min, tx_max, ty_min, ty_max
        real :: dpx_min, dpx_max, dpy_min, dpy_max
        integer :: n, i, j, k, ki
        integer :: total_nmix, max_iter, guard_hits, affected_cols
        logical :: first, is_open

        u_min = huge(1.0); u_max = -huge(1.0); u_sum = 0.0
        v_min = huge(1.0); v_max = -huge(1.0); v_sum = 0.0
        w_min = huge(1.0); w_max = -huge(1.0); w_sum = 0.0
        t_min = huge(1.0); t_max = -huge(1.0); t_sum = 0.0
        s_min = huge(1.0); s_max = -huge(1.0); s_sum = 0.0
        ro_min = huge(1.0); ro_max = -huge(1.0); ro_sum = 0.0
        wind_max = 0.0
        tx_min = huge(1.0); tx_max = -huge(1.0)
        ty_min = huge(1.0); ty_max = -huge(1.0)
        dpx_min = huge(1.0); dpx_max = -huge(1.0)
        dpy_min = huge(1.0); dpy_max = -huge(1.0)
        n = 0

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                wind_max = max(wind_max, wind(i, j))
                tx_min = min(tx_min, tx(i, j)); tx_max = max(tx_max, tx(i, j))
                ty_min = min(ty_min, ty(i, j)); ty_max = max(ty_max, ty(i, j))
                dpx_min = min(dpx_min, dpx(i, j)); dpx_max = max(dpx_max, dpx(i, j))
                dpy_min = min(dpy_min, dpy(i, j)); dpy_max = max(dpy_max, dpy(i, j))
                do k = 1, ki
                    n = n + 1
                    u_min = min(u_min, u2(i, j, k)); u_max = max(u_max, u2(i, j, k)); u_sum = u_sum + u2(i, j, k)
                    v_min = min(v_min, v2(i, j, k)); v_max = max(v_max, v2(i, j, k)); v_sum = v_sum + v2(i, j, k)
                    w_min = min(w_min, w(i, j, k)); w_max = max(w_max, w(i, j, k)); w_sum = w_sum + w(i, j, k)
                    t_min = min(t_min, t2(i, j, k)); t_max = max(t_max, t2(i, j, k)); t_sum = t_sum + t2(i, j, k)
                    s_min = min(s_min, s2(i, j, k)); s_max = max(s_max, s2(i, j, k)); s_sum = s_sum + s2(i, j, k)
                    ro_min = min(ro_min, ro(i, j, k)); ro_max = max(ro_max, ro(i, j, k)); ro_sum = ro_sum + ro(i, j, k)
                end do
            end do
        end do

        call ca_stats(total_nmix, max_iter, guard_hits, affected_cols)

        ! Заголовок CSV - только если файл создаётся заново.
        inquire (file='data/output/daily_diagnostics.csv', exist=first)
        first = .not. first
        open (diag_unit, file='data/output/daily_diagnostics.csv', position='append')
        if (first) then
            write (diag_unit, '(A)') &
                "day,month,u_min,u_max,u_mean,v_min,v_max,v_mean,w_min,w_max,w_mean,"// &
                "t_min,t_max,t_mean,s_min,s_max,s_mean,ro_min,ro_max,ro_mean,"// &
                "wind_max,tx_min,tx_max,ty_min,ty_max,dpx_min,dpx_max,dpy_min,dpy_max,"// &
                "euu,ca_nmix,ca_max_iter,ca_guard_hits,ca_affected_cols"
        end if
        write (diag_unit, '(I3,A1,I3,34(A1,ES13.5))') &
            day, ',', month, ',', &
            u_min, ',', u_max, ',', u_sum/max(n, 1), ',', &
            v_min, ',', v_max, ',', v_sum/max(n, 1), ',', &
            w_min, ',', w_max, ',', w_sum/max(n, 1), ',', &
            t_min, ',', t_max, ',', t_sum/max(n, 1), ',', &
            s_min, ',', s_max, ',', s_sum/max(n, 1), ',', &
            ro_min, ',', ro_max, ',', ro_sum/max(n, 1), ',', &
            wind_max, ',', tx_min, ',', tx_max, ',', ty_min, ',', ty_max, ',', &
            dpx_min, ',', dpx_max, ',', dpy_min, ',', dpy_max, ',', &
            euu, ',', real(total_nmix), ',', real(max_iter), ',', &
            real(guard_hits), ',', real(affected_cols)
        close (diag_unit)
        print '(A,I3,A,ES12.4,A,I8,A,I5,A,I3,A,I8)', &
            "  daily diag day=", day, " EUU=", euu, &
            " nmix=", total_nmix, " maxiter=", max_iter, &
            " guard=", guard_hits, " cols=", affected_cols
    end subroutine write_daily_diagnostics

end program main
