! ==============================================================================
! Модуль: grid_coupling (coup1)
! Назначение: Формирование трехмерной батиметрии и метрики расчетной сетки.
! Физика: Отображает непрерывный рельеф дна на дискретные Z-уровни модели.
!         Вычисляет глубины в центрах ячеек (скаляры) и на гранях (векторы),
!         генерирует трехмерные маски мокрых точек. Рассчитывает параметр
!         Кориолиса для учета сил вращения Земли в геострофическом балансе.
! Ответственность: Подготовка геометрического базиса. Защита алгоритма от
!                  вычислений в фиктивных ячейках суши.
! ==============================================================================

module grid_coupling
    use param
    implicit none

contains

    subroutine coup1()
        ! Локальные переменные
        integer :: i, j, k, kuu, j1, j2, i1, i2, jjj
        integer :: ix1, ix2, iy1, iy2, valid_count
        integer :: ios
        real :: sss, hht, h11, h22, hhij1, hhi1j, hhi1j1
        real :: omega
        logical :: valid_flag

        ! Открытие файла маски суши/моря с автогенерацией тестового бассейна
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
            ! Создаем искусственный мир: по краям суша (8), в центре — глубокий океан (ks)
            kt1(:, :) = 8
            kt1(10:120, 10:90) = ks
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

        do j = 1, js1
            do i = 1, is1
                sss = s2(i, j, 1)
                if (sss .le. 0.0) ht(i, j) = 8888.0
            end do
        end do

        ! Модификация глубин
        do j = 1, js1
            do i = 1, is1
                if (ht(i, j) .le. 10.0 .and. ht(i, j) .gt. 5.0) then
                    s2(i, j, 3) = s2(i, j, 2)
                    t2(i, j, 3) = t2(i, j, 2)
                    ht(i, j) = 10.0
                end if
                if (ht(i, j) .le. 3.0 .and. abs(ht(i, j) - 8888.0) .gt. 1e-8) ht(i, j) = 3.0
                if (abs(ht(i, j) - 8888.0) .gt. 1e-8) ht(i, j) = ht(i, j)*100.0
            end do
        end do

        ! Корректировка HT с учетом вертикальных уровней Z
        do j = 1, js1
            do i = 1, is1
                kuu = 0
                hht = ht(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle

                do k = 1, ks
                    if (hht .lt. z(k)) exit
                    kuu = k
                end do

                do k = 1, kuu
                    if (s2(i, j, k) .le. 0.0) then
                        ht(i, j) = z(max(1, k - 1))
                        exit
                    end if
                end do
            end do
        end do

        ! Расчет глубин на гранях U и V (HU, HV)
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

        ! Расчет массива KT1
        do j = 1, js1
            do i = 1, is1
                if (abs(ht(i, j) - 8888.0) .gt. 1e-8) then
                    kt1(i, j) = 1
                else
                    kt1(i, j) = 8
                end if
            end do
        end do

        ! Сглаживание HT по соседним мокрым точкам
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

        ! Расчет массива map1 (осредненная глубина для ячеек)
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

        ! Расчет массивов DZ, DZ1 (вертикальные шаги)
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

        ! Заполнение KT1 индексами дна
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

        ! Расчет массивов IDX, IDY
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

        ! Модификация KK1
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

        ! Идентификатор IT для адвекции льда
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

        ! Вычисление параметров Кориолиса
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

        ! Расчет идентификаторов KUSH, KVSH
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

        ! Инициализация ADX, ADY
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
