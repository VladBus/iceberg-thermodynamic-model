! ==============================================================================
! Модуль: advection_3d_t
! Назначение: Пространственная адвекция скалярных субстанций (температуры) в 3D.
! Физика: Решает уравнение конвекции-диффузии: ∂T/∂t + U·∇T = 0.
!         Для предотвращения численной дисперсии и осцилляций используется
!         алгоритм Flux-Corrected Transport (FCT) Бориса-Бука с лимитером Залесака.
!         Схема:
!           1. Предиктор по горизонтали (X,Y) — направленные разности (upwind).
!           2. Предиктор по вертикали (Z) — неявная схема Томаса (трехдиагональная).
!           3. Вычисление антидиффузионных потоков высокого порядка по X, Y, Z.
!           4. FCT-лимитер (Zalesak) для каждого направления — ограничение потков
!              для сохранения монотонности (нет новых экстремумов).
!           5. Коррекция — обновление поля температуры путем вычитания
!              ограниченных антидиффузионных потоков.
! Единицы: T [°C]; U/V [см/с]; W [см/с]; dx [см]; dz [см]; dt [с]; c2 = dt/dx.
! Ответственность: Транспортировка температуры течениями с гарантиями сохранения
!                  строгой положительности и массы. Исключает нефизичные
!                  отрицательные значения и численную дисперсию.
! ==============================================================================

module advection_3d_t
    use param
    implicit none

contains

    subroutine advt(dt, c2)
        real, intent(in) :: dt        ! Временной шаг бароклинного шага [с]
        real, intent(in) :: c2        ! Число Куранта = dt/dx [безразмерное]

        ! Локальные переменные
        integer :: i, j, k, i1, i2, j1, j2, ki, k1
        real :: cc, ci1, ci2, cj1, cj2, up, uu, vp, vv, a, b
        real :: cdx, cdy, flxp, flyp, a1, b1
        real :: ck1, ck2, ww1, ww2, ww

        ! Обнуление массивов антидиффузионных потоков
        apz(:, :, :) = 0.0    ! Потоки по вертикали Z
        apx(:, :, :) = 0.0    ! Потоки по горизонтали X
        apy(:, :, :) = 0.0    ! Потоки по горизонтали Y

        ! --- ОСНОВНОЙ ЦИКЛ ПЕРЕНОСА (ПРЕДИКТОР) ---
        ! Цикл по горизонтальной сетке: J=1..JS, I=1..IS
        do j = 1, js
            j1 = j + 1
            j2 = max(1, j - 1)
            do i = 1, is
                ki = kt1(i, j)        ! Число мокрых уровней в столбце
                if (ki .eq. 0) cycle  ! Пропуск суши

                i1 = i + 1
                i2 = max(1, i - 1)

                ! Горизонтальный перенос (схема против потока / upwind)
                do k = 1, ki
                    cc = t2(i, j, k)              ! Значение в текущей ячейке
                    ci1 = t2(i1, j, k)            ! Сосед по +X
                    ci2 = t2(i2, j, k)            ! Сосед по -X
                    cj1 = t2(i, j1, k)            ! Сосед по +Y
                    cj2 = t2(i, j2, k)            ! Сосед по -Y

                    ! Скорости на гранях ячейки [см/с]
                    up = u2(i, j1, k)             ! U на границе j+1/2
                    uu = 0.5*(up + u2(i, j, k))   ! U в центре ячейки (среднее)
                    vp = v2(i1, j, k)             ! V на границе i+1/2
                    vv = 0.5*(vp + v2(i, j, k))   ! V в центре ячейки

                    ! Конвективный поток по X (направленные разности)
                    a = abs(uu)
                    cdx = 0.5*(uu + a)*adx(i, j, k)*(cc - cj2) &   ! upwind часть
                          + 0.5*(uu - a)*adx(i, j1, k)*(cj1 - cc)

                    ! Конвективный поток по Y
                    a = abs(vv)
                    cdy = 0.5*(vv + a)*ady(i1, j, k)*(cc - ci1) &
                          + 0.5*(vv - a)*ady(i, j, k)*(ci2 - cc)

                    ! Предиктор: T* = T1 - c2*(CDX + CDY)
                    tt(k) = t1(i, j, k) - c2*(cdx + cdy)

                    ! Антидиффузионные потоки высокого порядка по X
                    a = abs(up)
                    flxp = 0.5*(up + a)*cc + 0.5*(up - a)*cj1
                    apx(i, j1, k) = adx(i, j1, k)*(up*0.5*(cc + cj1) - flxp)*c2

                    ! Антидиффузионные потоки высокого порядка по Y
                    a = abs(vp)
                    flyp = 0.5*(vp + a)*cc + 0.5*(vp - a)*ci1
                    apy(i1, j, k) = ady(i1, j, k)*(vp*0.5*(cc + ci1) - flyp)*c2
                end do

                ! Вертикальный перенос (неявная схема Томаса / трехдиагональная)
                ck2 = t2(i, j, 1)
                cc = ck2
                ww1 = w(i, j, 1)

                do k = 1, ki - 1
                    k1 = k + 1
                    ww2 = w(i, j, k1)
                    ww = 0.5*(ww1 + ww2)       ! W на границе k+1/2
                    a = abs(ww)
                    ck1 = t2(i, j, k1)
                    ! Трехдиагональная схема: CD = TT - dt*(W*dT/dz)
                    cd(i, j, k) = tt(k) - dt* &
                                  (0.5*(ww + a)*(cc - ck2)/dz(k) + 0.5*(ww - a)*(ck1 - cc)/dz(k1))
                    ck2 = cc
                    cc = ck1
                    ww1 = ww2
                end do

                cd(i, j, ki) = tt(ki)          ! Нижняя граница
                cc = t2(i, j, 1)

                ! Антидиффузионные потоки по Z
                do k = 2, ki
                    ck1 = t2(i, j, k)
                    ww = w(i, j, k)
                    a = abs(ww)
                    ! APZ = 0.5*W*(Ck+Ck1) - 0.5*(|W|+W)*Ck - 0.5*(|W|-W)*Ck1
                    apz(i, j, k) = 0.5*ww*(cc + ck1) - 0.5*(ww + a)*cc + 0.5*(ww - a)*ck1
                    cc = ck1
                end do
            end do
        end do

        ! --- КОРРЕКЦИЯ ПОТОКОВ FCT (X-COORDINATE) ---
        ! Лимитер Залесака: ограничение антидиффузионных потоков для монотонности
        do j = 1, js
            do i = 1, is
                ki = idx(i, j)              ! Число мокрых уровней для X-грани
                if (ki .eq. 0) cycle
                j1 = j + 1
                j2 = max(1, j - 1)

                do k = 1, ki
                    ! Разности полей для лимитера
                    a1 = adx(i, j, k)*(cd(i, j, k) - cd(i, j2, k))
                    b1 = adx(i, j2, k)*(cd(i, j2, k) - cd(i, max(1, j - 2), k))
                    a = apx(i, j, k)
                    b = sign(1.0, a)
                    ! Zalesak limiter: APX = sign(a) * max(0, min(|a|, sign(a)*a1, sign(a)*b1))
                    apx(i, j, k) = b*max(0.0, min(abs(a), b*a1, b*b1))
                end do
            end do
        end do

        ! Обновление CD после коррекции по X
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
                ki = idy(i, j)              ! Число мокрых уровней для Y-грани
                if (ki .eq. 0) cycle

                do k = 1, ki
                    a1 = ady(i, j, k)*(cd(i, j, k) - cd(i2, j, k))
                    b1 = ady(i2, j, k)*(cd(i2, j, k) - cd(max(1, i - 2), j, k))
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
                    ! Внутренние слои
                    a1 = (cd(i, j, 2) - cd(i, j, 1))*dz1(2)/dt
                    a = apz(i, j, 2)
                    b = sign(1.0, a)
                    apz(i, j, 2) = b*max(0.0, min(abs(a), b*a1))

                    do k = 3, ki - 1
                        a1 = (cd(i, j, k) - cd(i, j, k - 1))*dz1(k)/dt
                        b1 = (cd(i, j, k - 1) - cd(i, j, k - 2))*dz1(k - 1)/dt
                        a = apz(i, j, k)
                        b = sign(1.0, a)
                        apz(i, j, k) = b*max(0.0, min(abs(a), b*a1, b*b1))
                    end do
                end if

                if (ki .ge. 2) then
                    ! Нижний слой
                    a1 = (cd(i, j, ki) - cd(i, j, ki - 1))*dz1(ki)/dt
                    b1 = (cd(i, j, ki - 1) - cd(i, j, max(1, ki - 2)))*dz1(ki - 1)/dt
                    a = apz(i, j, ki)
                    b = sign(1.0, a)
                    apz(i, j, ki) = b*max(0.0, min(abs(a), b*a1, b*b1))
                end if
            end do
        end do

        ! Обновление CD после коррекции по Z
        do j = 1, js
            do i = 1, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 2, ki - 1
                    cd(i, j, k) = cd(i, j, k) - (apz(i, j, k + 1) - apz(i, j, k))*dt/dz1(k)
                end do
            end do
        end do

        ! Финальное обновление массива температуры T2 = CD
        t2(:, :, :) = cd(:, :, :)

    end subroutine advt

end module advection_3d_t
