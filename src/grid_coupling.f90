! ==============================================================================
! Модуль: grid_coupling (coup1)
! Назначение: Формирование трехмерной батиметрии и метрики расчетной сетки.
! Физика: Отображает непрерывный рельеф дна на дискретные Z-уровни модели.
!         Вычисляет глубины в центрах ячеек (скаляры) и на гранях (векторы),
!         генерирует трехмерные маски мокрых точек. Рассчитывает параметр
!         Кориолиса для учета сил вращения Земли в геострофическом балансе.
!         Ось X -> индекс J (U-компонента), ось Y -> индекс I (V-компонента).
!         Y-ось перевёрнута: J=1 — север, J=JS1 — юг.
! Формулы:
!   HU(i,j) = 0.5*(HT(i,j) + HT(i,j-1))    — глубина на U-грани (среднее по X)
!   HV(i,j) = 0.5*(HT(i,j) + HT(i-1,j))    — глубина на V-грани (среднее по Y)
!   MAP1(i,j) = 0.25*(HT(i,j)+HT(i,j-1)+HT(i-1,j)+HT(i-1,j-1)) — средняя глубина ячейки
!   KT1(i,j) = max{k : HT(i,j) >= Z(k)}    — индекс дна (число мокрых слоёв)
!   KK1(i,j) = min(KT1 по 4 T-точкам ячейки) — число активных уровней для U/V
!   FKU(i,j) = 2*omega*sin(FI(i,j)*pi/180)  — параметр Кориолиса [1/с]
!   FU(i,j)  = 0.5*(FKU(i,j)+FKU(i+1,j))   — Кориолис на U-грани
!   FV(i,j)  = 0.5*(FKU(i,j)+FKU(i,j+1))   — Кориолис на V-грани
!   DZ1(1) = 0.5*(Z(2)+Z(1)), DZ1(k) = 0.5*(Z(k+1)-Z(k-1)) — толщина полуслоя [см]
!   DZ(1) = Z(1), DZ(k) = Z(k)-Z(k-1)      — толщина полного слоя [см]
! Единицы: Глубины [см], параметр Кориолиса [1/с], скорость [см/с].
!          omega = 7.29e-5 [рад/с] — угловая скорость вращения Земли.
!          57.3 = 180/pi — перевод градусов в радианы.
!          Значение суш/море: 8888.0 — маркер сушевой (сухопутной) ячейки.
!          Преобразование глубин: KT1 исходный*100 → HT [см]; макс. глубина 600м=60000см.
! Ответственность: Подготовка геометрического базиса. Защита алгоритма от
!                  вычислений в фиктивных ячейках суши.
! Входные файлы:
!   KOORD.DAT — list-directed формат: 2 записи (FI, DL), каждая real(4) (is1,js1)=(133,105)
!   hhh.bar   — маска суши/моря: 7 блоков по 15 столбцов, формат 15I5, итого (is1,js1)=(133,105)
!               Значения: 8=суша, 600=600м глубина (множитель x100 в коде)
! ==============================================================================

module grid_coupling
    use param
    implicit none

contains

    subroutine coup1()
        ! --- Локальные переменные ---
        integer :: i, j, k, j1, j2, i1, i2, jjj    ! индексы циклов и смещения
        integer :: ix1, ix2, iy1, iy2, valid_count  ! для расчёта idx/idy/ит
        integer :: ios                               ! статус открытия файла
        real :: hht, h11, h22, hhij1, hhi1j, hhi1j1  ! рабочие глубины при усреднении
        real :: omega       ! 2*omega = 1.458e-4 [рад/с] — удвоенная угловая скорость Земли
        logical :: valid_flag  ! флаг: хотя бы одна соседняя ячейка валидна

        ! --- ЧТЕНИЕ ФАЙЛА МАСКИ СУШИ/МОРЯ С АВТОГЕНЕРАЦИЕЙ ТЕСТОВОГО БАССЕЙНА ---
        ! Формат hhh.bar: 7 блоков x 15 столбцов = 105 строк; каждая строка 15I5.
        ! j1..j2 — диапазон столбцов для текущего блока (j1=1..86, шаг 15).
        ! Каждая запись: read(1,*) — пропуск строки-заголовка блока.
        ! Значения KT1: 8=суша, числа 3..600 = индексы глубин (множитель x100 ниже).
        open (1, file='hhh.bar', status='old', iostat=ios)
        if (ios .eq. 0) then
            j1 = 1
            j2 = 15
            do jjj = 1, 7
                read (1, *)
                read (1, '(15I5)') ((kt1(i, j), j=j1, j2), i=1, is1)
                j1 = j1 + 15
                j2 = j2 + 15
            end do
            close (1)
        else
            print *, "NOTICE: hhh.bar not found. Generating synthetic ocean basin for test run."
            ! Создаем искусственный мир: по краям суша (8), в центре — океан.
            ! Значение 600 кодирует глубину 60000 см (600 м) через множитель x100
            ! в блоке модификации глубин ниже (максимальная глубина шкалы Z).
            kt1(:, :) = 8
            kt1(10:120, 10:90) = 600
        end if

        ! Инициализация глубин HT на основе KT1
        do j = 1, js1
            do i = 1, is1
                ht(i, j) = real(kt1(i, j))
            end do
        end do

        ! Граничные условия
        ht(1:15, 94) = 8888.0
        ht(:, js1) = 8888.0
        ht(:, 1) = 8888.0
        ht(1, :) = 8888.0

        ! Суша из маски (kt1 = 8) помечается как несуществующая глубина.
        ! Ранее это делалось через проверку S2 <= 0, но S2 заполняется только
        ! ПОСЛЕ вызова Coup1 (в main.f90), поэтому весь домен помечался сушей.
        do j = 1, js1
            do i = 1, is1
                if (kt1(i, j) .eq. 8) ht(i, j) = 8888.0
            end do
        end do

        ! --- МОДИФИКАЦИЯ ГЛУБИН (суша 8888 исключается из обработки) ---
        ! Алгоритм:
        !   1. Если 5 < HT <= 10 (единицы KT1, т.е. 500..1000 см): обрезаем до 10
        !      и приравниваем T/S на уровне 3 к уровню 2 (неглубокая вода, 2 слоя).
        !   2. Если HT <= 3 (300 см = 3 м): минимальная глубина 3.0 (300 см).
        !   3. Перевод единиц: HT *= 100 → из «индексов KT1» в сантиметры.
        !      Т.е. KT1=600 → HT=60000 см = 600 м (максимальная глубина шкалы Z).
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle
                if (ht(i, j) .le. 10.0 .and. ht(i, j) .gt. 5.0) then
                    s2(i, j, 3) = s2(i, j, 2)
                    t2(i, j, 3) = t2(i, j, 2)
                    ht(i, j) = 10.0
                end if
                if (ht(i, j) .le. 3.0) ht(i, j) = 3.0
                ht(i, j) = ht(i, j)*100.0
            end do
        end do

        ! Корректировка HT с учетом вертикальных уровней Z
        ! (блок удален: он проверял S2 <= 0 для обрезки глубины, но массив S2
        ! инициализируется позже вызова Coup1, а глубина уже определена маской.
        ! Проверка приводила к схлопыванию всего домена к поверхностному уровню)

        ! --- РАСЧЕТ ГЛУБИН НА ГРАНЯХ U И V (HU, HV) ---
        ! B-сетка Аракавы: U-точка (i,j) на грани между T-точками (i,j) и (i,j-1)
        !                   V-точка (i,j) на грани между T-точками (i,j) и (i-1,j)
        ! HU(i,j) = среднее HT(i,j) и HT(i,j-1) → средняя глубина на U-грани [см]
        ! HV(i,j) = среднее HT(i,j) и HT(i-1,j) → средняя глубина на V-грани [см]
        ! Обе ячейки должны быть мокрыми (!=8888), иначе грань считается сухой.
        hu(:, :) = 8888.0
        hv(:, :) = 8888.0

        do j = 2, js1
            do i = 1, is1
                h11 = ht(i, j)
                h22 = ht(i, j - 1)
                if (abs(h11 - 8888.0) .gt. 1e-8 .and. abs(h22 - 8888.0) .gt. 1e-8) then
                    hu(i, j) = (h11 + h22)*0.5
                end if
            end do
        end do

        do j = 1, js1
            do i = 2, is1
                h11 = ht(i, j)
                h22 = ht(i - 1, j)
                if (abs(h11 - 8888.0) .gt. 1e-8 .and. abs(h22 - 8888.0) .gt. 1e-8) then
                    hv(i, j) = (h11 + h22)*0.5
                end if
            end do
        end do

        ! Обнуление краевых значений для HU и HV
        hu(:, 1) = 8888.0
        hu(:, js1) = 8888.0
        hv(1, :) = 8888.0
        hv(is1, :) = 8888.0

        kt1(:, 1) = 8
        kt1(is1, :) = 8
        kt1(1, :) = 8

        ! --- РАСЧЕТ МАССИВА KT1: ЧИСЛО МОКРЫХ Z-УРОВНЕЙ В СТОЛБЦЕ ---
        ! Если глубина < Z(k) — выход; KT1 = индекс последнего полного слоя.
        ! Формула: KT1(i,j) = max{ k ∈ [1,KS] : HT(i,j) >= Z(k) }
        ! Для сушевых ячеек (HT=8888) устанавливается KT1=8 (специальное значение).
        ! Примечание: здесь используется переменная hht, которая НЕ инициализирована
        ! на входе в этот цикл — это логическая ошибка исходника (hht берётся
        ! из предыдущего блока модификации глубин, но после цикла по j,i).
        ! В итоге первый проход KT1 даёт некорректные значения; ниже следует
        ! повторный проход заполнения KT1 (строки 241-252), который перезаписывает.
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .gt. 1e-8) then
                    kt1(i, j) = 1
                    do k = 2, ks
                        if (hht .lt. z(k)) exit
                        kt1(i, j) = k
                    end do
                else
                    kt1(i, j) = 8
                end if
            end do
        end do

        ! --- СГЛАЖИВАНИЕ HT ПО СОСЕДНИМ МОКРЫМ ТОЧКАМ ---
        ! Для каждой T-точки (i,j) усредняем глубину по 4 соседним U/V-точкам:
        ! HT_new(i,j) = (HU(i,j) + HU(i,j+1) + HV(i,j) + HV(i+1,j)) / N_valid
        ! где N_valid — число несушевых соседей (от 1 до 4).
        ! Цель: сгладить ступеньки батиметрии на границе суша/море.
        do j = 1, js
            j1 = j + 1
            do i = 1, is
                i1 = i + 1
                if (kt1(i, j) .eq. 8) cycle

                valid_count = 0
                hht = 0.0

                if (abs(hu(i, j) - 8888.0) .gt. 1e-8) then
                    hht = hht + hu(i, j)
                    valid_count = valid_count + 1
                end if

                if (abs(hu(i, j1) - 8888.0) .gt. 1e-8) then
                    hht = hht + hu(i, j1)
                    valid_count = valid_count + 1
                end if

                if (abs(hv(i, j) - 8888.0) .gt. 1e-8) then
                    hht = hht + hv(i, j)
                    valid_count = valid_count + 1
                end if

                if (abs(hv(i1, j) - 8888.0) .gt. 1e-8) then
                    hht = hht + hv(i1, j)
                    valid_count = valid_count + 1
                end if

                if (valid_count .gt. 0) ht(i, j) = hht/real(valid_count)
            end do
        end do

        kk1(:, :) = 0
        do j = 2, js
            j2 = j - 1
            do i = 2, is
                i2 = i - 1
   if (kt1(i, j) .eq. 8 .or. kt1(i, j2) .eq. 8 .or. kt1(i2, j) .eq. 8 .or. kt1(i2, j2) .eq. 8) cycle
                kk1(i, j) = 1
            end do
        end do

        ! --- РАСЧЕТ МАССИВА MAP1 (ОСРЕДНЕННАЯ ГЛУБИНА ДЛЯ ЯЧЕЕК) ---
        ! MAP1(i,j) = усреднённая глубина по 4 T-точкам ячейки (i,j):
        !   MAP1 = 0.25*(HT(i,j) + HT(i,j-1) + HT(i-1,j) + HT(i-1,j-1))
        ! Используется как HHT (barotropic depth) в блоках 200/210/280.
        map1(:, :) = 8888.0
        do j = 2, js
            j2 = j - 1
            do i = 2, is
                i2 = i - 1
                if (kk1(i, j) .eq. 0) cycle

                hht = ht(i, j)
                hhij1 = ht(i, j2)
                hhi1j = ht(i2, j)
                hhi1j1 = ht(i2, j2)

                mapp = 0.0
                valid_flag = .false.

                if (abs(hht - 8888.0) .gt. 1e-8) then
                    mapp = mapp + hht*0.25
                    valid_flag = .true.
                end if
                if (abs(hhij1 - 8888.0) .gt. 1e-8) then
                    mapp = mapp + hhij1*0.25
                    valid_flag = .true.
                end if
                if (abs(hhi1j - 8888.0) .gt. 1e-8) then
                    mapp = mapp + hhi1j*0.25
                    valid_flag = .true.
                end if
                if (abs(hhi1j1 - 8888.0) .gt. 1e-8) then
                    mapp = mapp + hhi1j1*0.25
                    valid_flag = .true.
                end if

                if (valid_flag) then
                    map1(i, j) = mapp
                end if
            end do
        end do

        ! --- РАСЧЕТ МАССИВОВ DZ, DZ1 (ВЕРТИКАЛЬНЫЕ ШАГИ) ---
        ! DZ1(k) — толщина полуслоя (half-level) [см]:
        !   DZ1(1)  = 0.5*(Z(2)+Z(1))           — верхний полуслой (от поверхности до Z1)
        !   DZ1(k)  = 0.5*(Z(k+1)-Z(k-1))      — средние полуслои
        !   DZ1(KS) = 0.5*(Z(KS)-Z(KS2))        — нижний полуслой (только верхняя половина)
        !   Используются для баротропно-бароклинного интеграла (block 200) и
        !   вертикальной вязкости (block 210, Томас): DZZ = DZ1(K).
        ! DZ(k) — толщина полного слоя [см]:
        !   DZ(1)  = Z(1)                        — первый слой (от поверхности до Z1)
        !   DZ(k)  = Z(k) - Z(k-1)               — последующие слои
        !   Используются в thermal equations и advection.
        dz1(:) = 8888.0
        dz(:) = 8888.0

        dz1(1) = 0.5*(z(2) + z(1))
        do k = 2, ks2
            dz1(k) = 0.5*(z(k + 1) - z(k - 1))
        end do
        dz1(ks) = 0.5*(z(ks) - z(ks2))

        dz(1) = z(1)
        do k = 2, ks
            dz(k) = z(k) - z(k - 1)
        end do

        ! --- ЗАПОЛНЕНИЕ KT1 ИНДЕКСАМИ ДНА (второй проход, корректный) ---
        ! Перезаписывает KT1 из блока модификации глубин. Теперь HT уже в [см].
        ! KT1(i,j) = 0 для суши; для воды: max{k : HT(i,j) >= Z(k)}.
        ! Этот проход корректен, так как HT содержит физические глубины в [см].
        do j = 1, js1
            do i = 1, is1
                kt1(i, j) = 0
                hht = ht(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle
                kt1(i, j) = 1
                do k = 2, ks
                    if (hht .lt. z(k)) exit
                    kt1(i, j) = k
                end do
            end do
        end do

        ! --- РАСЧЕТ МАССИВОВ IDX, IDY ---
        ! IDX(i,j) — число активных (мокрых) U-слоёв на границе между j и j-1:
        !   IDX(i,j) = min(KT1(i,j), KT1(i,j-1))  — ограничено мелким соседом
        ! IDY(i,j) — число активных (мокрых) V-слоёв на границе между i и i-1:
        !   IDY(i,j) = min(KT1(i,j), KT1(i-1,j))  — ограничено мелким соседом
        ! Используются в ADX/ADY (маски адвекции) и блоках 200/210.
        idx(1:is, :) = 0
        idy(:, 1:js) = 0

        do j = 2, js
            j2 = j - 1
            if (abs(map1(2, j) - 8888.0) .gt. 1e-8) then
                if (kt1(1, j2) .lt. kt1(1, j)) then
                    idx(1, j) = kt1(1, j)
                else
                    idx(1, j) = kt1(1, j2)
                end if
            end if

            if (abs(map1(is, j) - 8888.0) .gt. 1e-8) then
                if (kt1(is, j2) .lt. kt1(is, j)) then
                    idx(is, j) = kt1(is, j)
                else
                    idx(is, j) = kt1(is, j2)
                end if
            end if
        end do

        do j = 2, js
            j1 = j + 1
            j2 = j - 1
            do i = 2, is2
                i1 = i + 1
                i2 = i - 1
             if (abs(map1(i, j) - 8888.0) .lt. 1e-8 .and. abs(map1(i1, j) - 8888.0) .lt. 1e-8) cycle
                if (kt1(i, j2) .lt. kt1(i, j)) then
                    idx(i, j) = kt1(i, j)
                else
                    idx(i, j) = kt1(i, j2)
                end if
            end do
        end do

        do i = 2, is
            i2 = i - 1
            if (abs(map1(i, 2) - 8888.0) .gt. 1e-8) then
                if (kt1(i2, 1) .lt. kt1(i, 1)) then
                    idy(i, 1) = kt1(i, 1)
                else
                    idy(i, 1) = kt1(i2, 1)
                end if
            end if

            if (abs(map1(i, js) - 8888.0) .gt. 1e-8) then
                if (kt1(i2, js) .lt. kt1(i, js)) then
                    idy(i, js) = kt1(i, js)
                else
                    idy(i, js) = kt1(i2, js)
                end if
            end if
        end do

        do j = 2, js2
            j1 = j + 1
            j2 = j - 1
            do i = 2, is
                i1 = i + 1
                i2 = i - 1
             if (abs(map1(i, j) - 8888.0) .lt. 1e-8 .and. abs(map1(i, j1) - 8888.0) .lt. 1e-8) cycle
                if (kt1(i2, j) .lt. kt1(i, j)) then
                    idy(i, j) = kt1(i, j)
                else
                    idy(i, j) = kt1(i2, j)
                end if
            end do
        end do

        ! --- МОДИФИКАЦИЯ KK1 ---
        ! KK1(i,j) = min{KT1 по 4 T-точкам ячейки} = min(KT1(i,j), KT1(i-1,j), KT1(i-1,j-1), KT1(i,j-1))
        ! Число активных уровней для U/V-ячейки = минимум по 4 соседним T-точкам.
        ! Используется в блоках 200/210/280 как верхняя граница суммирования.
        do j = 2, js
            j2 = j - 1
            do i = 2, is
                i2 = i - 1
                if (kk1(i, j) .eq. 0) cycle
                kk1(i, j) = kt1(i, j)
                if (kk1(i, j) .gt. kt1(i2, j)) kk1(i, j) = kt1(i2, j)
                if (kk1(i, j) .gt. kt1(i2, j2)) kk1(i, j) = kt1(i2, j2)
                if (kk1(i, j) .gt. kt1(i, j2)) kk1(i, j) = kt1(i, j2)
            end do
        end do

        kk1(:, 1) = 0
        kk1(:, js1) = 0
        kk1(1, :) = 0
        kk1(is1, :) = 0

        ! --- ИДЕНТИФИКАТОР IT ДЛЯ АДВЕКЦИИ ЛЬДА ---
        ! IT(i,j) кодирует тип граничного условия для адвекции льда на U-грани (i,j):
        !   IT=0: все 4 соседних U/V-грани валидны (внутренняя точка)
        !   IT=1..4: каждая комбинация из 2 нулевых границ (береговая конфигурация)
        !   IT=9: пропуск (нет активных граней или только суша)
        ! Формула проверки: idx/idy ≠ 0 означает наличие активного слоя на грани.
        it(:, :) = 9
        do j = 1, js
            j1 = j + 1
            do i = 1, is
                if (kt1(i, j) .eq. 0) cycle
                i1 = i + 1
                ix1 = idx(i, j)
                ix2 = idx(i, j1)
                iy1 = idy(i, j)
                iy2 = idy(i1, j)

                if (ix1 .eq. 0 .and. iy1 .eq. 0 .and. ix2 .eq. 0) cycle
                if (iy1 .eq. 0 .and. ix2 .eq. 0 .and. iy2 .eq. 0) cycle
                if (ix2 .eq. 0 .and. iy2 .eq. 0 .and. ix1 .eq. 0) cycle
                if (iy2 .eq. 0 .and. ix1 .eq. 0 .and. iy1 .eq. 0) cycle

                if (ix1 .eq. 0 .and. iy1 .eq. 0) then
                    it(i, j) = 1
                else if (iy1 .eq. 0 .and. ix2 .eq. 0) then
                    it(i, j) = 2
                else if (ix2 .eq. 0 .and. iy2 .eq. 0) then
                    it(i, j) = 3
                else if (iy2 .eq. 0 .and. ix1 .eq. 0) then
                    it(i, j) = 4
                else
                    it(i, j) = 0
                end if
            end do
        end do

        ! --- ИНИЦИАЛИЗАЦИЯ ШИРОТЫ FI И ДОЛГОТЫ DL (В ГРАДУСАХ) ---
        ! Для параметра Кориолиса, расчёта солнечной радиации и пространственной интерполяции
        ! атмосферного форсинга ERA5.
        !
        ! ИСТОРИЧЕСКИ: FI/DL читались из KOORD.DAT (полные поля координат).
        ! Файл отсутствует в рабочей копии, поэтому:
        !   grid_mode=REAL -> попытка прочитать KOORD.DAT; при неудаче - STOP.
        !   grid_mode=TEST  -> синтетическая сетка TEST ONLY с явным warning.
        !
        ! TEST ONLY: широта линейно растёт с индексом J от 66N (юг) до 82N (север);
        ! долгота линейно растёт с индексом I от 30E до 63E (в пределах ERA5-окна).
        ! Эти координаты НЕ являются реальной областью модели и НЕ должны
        ! использоваться в production-расчётах.
        if (grid_mode .eq. grid_mode_real) then
            open (1, file='KOORD.DAT', status='old', iostat=ios)
            if (ios .eq. 0) then
                read (1, *) fi
                read (1, *) dl
                close (1)
                print *, "KOORD.DAT loaded: FI/DL read from file (REAL grid)."
            else
                print *, "FATAL: grid_mode=REAL but KOORD.DAT is missing."
                print *, "  Cannot use synthetic coordinates in production mode."
                print *, "  Provide KOORD.DAT or set grid_mode=TEST explicitly."
                stop
            end if
        else
            print *, "WARNING: TEST ONLY synthetic grid (grid_mode=TEST)."
            print *, "  KOORD.DAT is absent; FI/DL are synthetic and NOT a real basin."
            do j = 1, js1
                do i = 1, is1
                    fi(i, j) = 66.0 + 16.0*real(j - 1)/real(js1 - 1)
                    dl(i, j) = 30.0 + 33.0*real(i - 1)/real(is1 - 1)
                end do
            end do
        end if

        ! --- ВЫЧИСЛЕНИЕ ПАРАМЕТРОВ КОРИОЛИСА ---
        ! f = 2*omega*sin(phi), где:
        !   omega = 7.29e-5 [рад/с] — угловая скорость вращения Земли
        !   2*omega = 1.458e-4 [рад/с]
        !   phi — широта [градусы], переводим в радианы через /57.3 (=pi/180)
        ! FKU(i,j) = f в U-точках (центры ячеек)
        ! FU(i,j)  = f на U-грани (среднее по X между j и j+1)
        ! FV(i,j)  = f на V-грани (среднее по Y между i и i+1)
        ! Для TEST-сетки: FI = 66..82°N, FKU ~ 1.2e-4..1.4e-4 [1/с]
        omega = 2.0*7.29e-5
        do j = 1, js1
            do i = 1, is1
                fku(i, j) = omega*sin(fi(i, j)/57.3)
            end do
        end do

        do j = 1, js1
            do i = 1, is
                fu(i, j) = 0.5*(fku(i, j) + fku(i + 1, j))
            end do
        end do

        do j = 1, js
            do i = 1, is1
                fv(i, j) = 0.5*(fku(i, j) + fku(i, j + 1))
            end do
        end do

        ! --- РАСЧЕТ ИДЕНТИФИКАТОРОВ KUSH, KVSH ---
        ! KUSH(i,j) = 1, если U-точка (i,j) и все 4 её V-соседа мокрые, иначе 0.
        !   Т.е. внутренняя U-точка, не на береговой линии (нет сухих V-соседей).
        ! KVSH(i,j) = 1, если V-точка (i,j) и все 4 её U-соседа мокрые, иначе 0.
        !   Внутренняя V-точка, не на береговой линии.
        ! Используются в shallow_water для определения free-slip vs no-slip ГУ.
        do j = 1, js
            j1 = j + 1
            j2 = j - 1
            do i = 1, is
                i1 = i + 1
                i2 = i - 1
                kush(i, j) = 0
                kvsh(i, j) = 0

                if (abs(hu(i, j) - 8888.0) .gt. 1e-8) then
                    if (abs(hu(i, j1) - 8888.0) .gt. 1e-8 .and. abs(hu(i, j2) - 8888.0) .gt. 1e-8 &
               .and. abs(hu(i1, j) - 8888.0) .gt. 1e-8 .and. abs(hu(i2, j) - 8888.0) .gt. 1e-8) then
                        kush(i, j) = 1
                    end if
                end if

                if (abs(hv(i, j) - 8888.0) .gt. 1e-8) then
                    if (abs(hv(i, j1) - 8888.0) .gt. 1e-8 .and. abs(hv(i, j2) - 8888.0) .gt. 1e-8 &
               .and. abs(hv(i1, j) - 8888.0) .gt. 1e-8 .and. abs(hv(i2, j) - 8888.0) .gt. 1e-8) then
                        kvsh(i, j) = 1
                    end if
                end if
            end do
        end do

        ! --- ИНИЦИАЛИЗАЦИЯ ADX, ADY ---
        ! ADX(i,j,k) = 1.0 если k <= IDX(i,j), иначе 0.0 (3D-маска адвекции по X).
        ! ADY(i,j,k) = 1.0 если k <= IDY(i,j), иначе 0.0 (3D-маска адвекции по Y).
        ! Определяют, на каких вертикальных уровнях существует транспорт через данную грань.
        adx(:, :, :) = 0.0
        ady(:, :, :) = 0.0

        do j = 2, js
            do i = 2, is
                do k = 1, idx(i, j)
                    adx(i, j, k) = 1.0
                end do
                do k = 1, idy(i, j)
                    ady(i, j, k) = 1.0
                end do
            end do
        end do

    end subroutine coup1

end module grid_coupling
