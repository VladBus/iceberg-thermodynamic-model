! ==============================================================================
! Модуль: iceberg_forcing
! Назначение: Интерфейс форсинга для айсберга — горизонтальная (билинейная) и
!             вертикальная интерполяция океанских и атмосферных профилей
!             на позицию айсберга.
! Физика: Использует существующую инфраструктуру ERA5 (netcdf_input) и
!         модельную сетку (param/grid_coupling) для интерполяции.
!         Вертикальная интерполяция по Z-уровням модели к слоям осадки айсберга.
!         Экстраполяция ниже максимального моделируемого уровня (45м) до
!         осадки (~88м) постоянными значениями T/S и нулевой скоростью.
!
! Архитектура:
!   1. get_ocean_profile - основная рутина:
!      - Горизонтальная билинейная интерполяция на модельной сетке (CGS→SI)
!      - Вертикальная интерполяция/экстраполяция к осадке
!   2. get_atmos_forcing - билинейная интерполяция ERA5 на lat/lon
!   3. interp_at_draft - вертикальная интерполяция T/S на глубине осадки
!   4. depth_averaged_thermal_forcing - глубинно-усреднённое ΔT для бокового плавления
!   5. depth_integrated_currents - глубинно-интегрированные течения (Method A)
!
! Единицы:
!   Вход: CGS для океана (u2/v2 [см/с], z/dz [см]), SI для атмосферы
!   Выход: SI (u/v [м/с], z/dz [м], temp [°C], salt [кг/кг])
!
! Точность: default real (float32). ERA5 билинейная интерполяция в real(8).
! ==============================================================================

module iceberg_forcing
    use iceberg_types
    use param, only: is, js, ks, is1, js1, kt1, fi, dl, z, dz, dz1, &
                     t2, s2, u2, v2, fku, ht, map1
    use netcdf_input, only: era5_bilinear2d, era5_find_time_index, &
                            era5_u10, era5_v10, era5_t2m, era5_d2m, &
                            era5_tcc, era5_msl, era5_snowfall, era5_is_open, &
                            era5_time, era5_lat, era5_lon
    implicit none

    ! ========================================================================
    !   КОНСТАНТЫ ИНТЕРПОЛЯЦИИ
    ! ========================================================================
    real, parameter :: LAND_MASK_VAL = 8888.0   ! Значение land mask в ht/kt1
    real, parameter :: EPS_LAND = 1.0e-8        ! Эпсилон для сравнения с land mask
    real, parameter :: CM_TO_M = 0.01           ! Перевод см → м
    real, parameter :: M_TO_CM = 100.0          ! Перевод м → см

contains

    ! ========================================================================
    !   ОСНОВНАЯ ФУНКЦИЯ: ПОЛУЧЕНИЕ ОКЕАНСКОГО ПРОФИЛЯ НА ПОЗИЦИИ АЙСБЕРГА
    ! ========================================================================
    ! Последовательность:
    !   1. Найти индексы 4 соседних T-точек (i1,i2,j1,j2) через model_coords_to_indices
    !   2. Проверить land mask на 4-х углах (LAND_MASK_VAL ± EPS_LAND)
    !   3. Вычислить веса билинейной интерполяции (wx, wy, wx1, wy1)
    !   4. Определить число активных вертикальных уровней kt = min(kt1 4-х ячеек)
    !   5. Выделить память под профиль (nlevels = kt)
    !   6. Заполнить профиль: горизонтальная билинейная интерполяция + вертикальные z/dz
    !   7. Конвертация CGS→SI: u/v × CM_TO_M, z/dz × CM_TO_M
    !
    ! Аргументы:
    !   x_model, y_model - позиция в модельных координатах [м] (intent(in))
    !   lat, lon         - географическая позиция [°] (intent(in))
    !   draft            - осадка айсберга [м] (intent(in))
    !   prof             - выходной профиль океана (intent(out))
    !   ok               - флаг успеха (intent(out))
    ! ========================================================================
    subroutine get_ocean_profile(x_model, y_model, lat, lon, draft, prof, ok)
        real, intent(in) :: x_model, y_model
        real, intent(in) :: lat, lon
        real, intent(in) :: draft
        type(ocean_profile), intent(out) :: prof
        logical, intent(out) :: ok

        integer :: i_idx, j_idx
        integer :: i1, i2, j1, j2
        integer :: k, kt
        real :: wx, wy, wx1, wy1
        logical :: in_domain
        real :: x_j1, x_j2, y_i1, y_i2
        real :: ocean_depth, effective_draft

        ok = .false.

        ! 1. Найти индексы сетки (перевод модельных координат в индексы)
        call model_coords_to_indices(x_model, y_model, i_idx, j_idx, in_domain)
        if (.not. in_domain) then
            print *, "FORCING ERROR: Iceberg position outside model domain"
            return
        end if

        ! 2. Проверить соседние ячейки (4 угла для билинейной интерполяции)
        i1 = i_idx; i2 = i_idx + 1
        j1 = j_idx; j2 = j_idx + 1

        if (i2 .gt. is1 .or. j2 .gt. js1) then
            print *, "FORCING ERROR: Iceberg at domain boundary"
            return
        end if

        ! Land mask check: 8888.0 — суша, используем epsilon сравнение
        if (abs(ht(i1, j1) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i2, j1) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i1, j2) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i2, j2) - LAND_MASK_VAL) .lt. EPS_LAND) then
            print *, "FORCING WARNING: Iceberg near land"
        end if

        ! 3. Веса билинейной интерполяции
        ! Модельная сетка: равномерная dx = 13890 м
        x_j1 = real(j1 - 1)*13890.0
        x_j2 = real(j2 - 1)*13890.0
        y_i1 = real(i1 - 1)*13890.0
        y_i2 = real(i2 - 1)*13890.0

        if (abs(x_j2 - x_j1) .lt. 1.0 .or. abs(y_i2 - y_i1) .lt. 1.0) then
            print *, "FORCING ERROR: Degenerate grid spacing"
            return
        end if

        wx = (x_model - x_j1)/(x_j2 - x_j1)
        wy = (y_model - y_i1)/(y_i2 - y_i1)
        wx1 = 1.0 - wx
        wy1 = 1.0 - wy

        ! Клиппинг весов в [0,1]
        wx = max(0.0, min(1.0, wx))
        wy = max(0.0, min(1.0, wy))
        wx1 = 1.0 - wx
        wy1 = 1.0 - wy

        ! 4. Активные вертикальные уровни
        kt = min(kt1(i1, j1), kt1(i2, j1), kt1(i1, j2), kt1(i2, j2))
        if (kt .eq. 0) then
            print *, "FORCING ERROR: All surrounding cells are land"
            return
        end if

        ocean_depth = real(ht(i1, j1))*CM_TO_M
        effective_draft = min(draft, ocean_depth*0.99)

        ! 5. Выделить память под профиль
        prof%nlevels = kt
        allocate (prof%z(kt), prof%dz(kt), prof%temp(kt), prof%salt(kt), &
                  prof%u(kt), prof%v(kt))

        ! 6. Заполнить профиль
        do k = 1, kt
            prof%z(k) = real(z(k))*CM_TO_M
            prof%dz(k) = real(dz(k))*CM_TO_M

            prof%temp(k) = bilinear_interp_3d(t2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
            prof%salt(k) = bilinear_interp_3d(s2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
            ! u2/v2 в CGS [см/с] → SI [м/с]: × CM_TO_M
            prof%u(k) = bilinear_interp_3d(u2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)*CM_TO_M
            prof%v(k) = bilinear_interp_3d(v2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)*CM_TO_M
        end do

        ok = .true.
    end subroutine get_ocean_profile

    ! ========================================================================
    !   БИЛИНЕЙНАЯ ИНТЕРПОЛЯЦИЯ 3D ПОЛЯ (pure function)
    ! ========================================================================
    ! Формула: f = (1-wx)(1-wy)*f(i1,j1) + wx(1-wy)*f(i2,j1)
    !                    + (1-wx)wy*f(i1,j2) + wx*wy*f(i2,j2)
    ! Используется для t2, s2, u2, v2 на каждом вертикальном уровне k.
    !
    ! Аргументы:
    !   arr   - 3D массив (i1:is1, j1:js1, k) (intent(in))
    !   i1,i2,j1,j2,k - индексы 4 углов и уровень
    !   wx,wy,wx1,wy1 - веса билинейной интерполяции
    !   val   - результат интерполяции
    ! ========================================================================
    pure real function bilinear_interp_3d(arr, i1, i2, j1, j2, k, wx, wy, wx1, wy1) &
        result(val)
        real, intent(in) :: arr(:, :, :)
        integer, intent(in) :: i1, i2, j1, j2, k
        real, intent(in) :: wx, wy, wx1, wy1

        val = wx1*wy1*arr(i1, j1, k) + &
              wx*wy1*arr(i2, j1, k) + &
              wx1*wy*arr(i1, j2, k) + &
              wx*wy*arr(i2, j2, k)
    end function bilinear_interp_3d

    ! ========================================================================
    !   ПРЕОБРАЗОВАНИЕ МОДЕЛЬНЫХ КООРДИНАТ В ИНДЕКСЫ СЕТКИ
    ! ========================================================================
    ! Модельная сетка: равномерная dx = 13890 м
    !   j_idx (X-индекс) = int(x_model/13890) + 1  (1-based)
    !   i_idx (Y-индекс) = int(y_model/13890) + 1
    ! in_domain = .TRUE. если 1 ≤ i_idx < is1 и 1 ≤ j_idx < js1
    ! (нужно 4 соседние ячейки для билинейной интерполяции)
    !
    ! Аргументы:
    !   x_model, y_model - позиция [м]
    !   i_idx, j_idx     - индексы (выход)
    !   in_domain        - флаг внутри домена (выход)
    ! ========================================================================
    subroutine model_coords_to_indices(x_model, y_model, i_idx, j_idx, in_domain)
        real, intent(in) :: x_model, y_model
        integer, intent(out) :: i_idx, j_idx
        logical, intent(out) :: in_domain

        real :: dx_model
        dx_model = 13890.0

        j_idx = int(x_model/dx_model) + 1
        i_idx = int(y_model/dx_model) + 1

        if (i_idx .lt. 1 .or. i_idx .ge. is1 .or. j_idx .lt. 1 .or. j_idx .ge. js1) then
            in_domain = .false.
        else
            in_domain = .true.
        end if
    end subroutine model_coords_to_indices

    ! ========================================================================
    !   ОБРАТНАЯ ПРОЕКЦИЯ: МОДЕЛЬНЫЕ КООРДИНАТЫ → ШИРОТА/ДОЛГОТА
    ! ========================================================================
    ! Билинейная интерполяция массивов FI/DL (из KOORD.DAT) на позиции
    ! айсберга в модельных координатах (x_model, y_model).
    ! Использует те же 4 соседние T-точки, что и get_ocean_profile.
    !
    ! Формула: то же, что bilinear_interp_3d, но для 2D полей fi, dl.
    !
    ! Аргументы:
    !   x_model, y_model - позиция в модельных координатах [м]
    !   lat, lon         - географическая позиция [°] (выход)
    !   ok               - флаг успеха (выход)
    ! ========================================================================
    subroutine model_coords_to_latlon(x_model, y_model, lat, lon, ok)
        real, intent(in) :: x_model, y_model
        real, intent(out) :: lat, lon
        logical, intent(out) :: ok

        integer :: i_idx, j_idx
        integer :: i1, i2, j1, j2
        real :: wx, wy, wx1, wy1
        logical :: in_domain
        real :: x_j1, x_j2, y_i1, y_i2

        ok = .false.

        ! 1. Найти индексы сетки (то же, что в get_ocean_profile)
        call model_coords_to_indices(x_model, y_model, i_idx, j_idx, in_domain)
        if (.not. in_domain) then
            return
        end if

        ! 2. Индексы 4 углов для билинейной интерполяции
        i1 = i_idx; i2 = i_idx + 1
        j1 = j_idx; j2 = j_idx + 1

        ! 3. Координаты узлов сетки
        x_j1 = real(j1 - 1)*13890.0
        x_j2 = real(j2 - 1)*13890.0
        y_i1 = real(i1 - 1)*13890.0
        y_i2 = real(i2 - 1)*13890.0

        if (abs(x_j2 - x_j1) .lt. 1.0 .or. abs(y_i2 - y_i1) .lt. 1.0) then
            return
        end if

        ! 4. Веса билинейной интерполяции
        wx = (x_model - x_j1)/(x_j2 - x_j1)
        wy = (y_model - y_i1)/(y_i2 - y_i1)
        wx1 = 1.0 - wx
        wy1 = 1.0 - wy

        ! Клиппинг весов в [0,1]
        wx = max(0.0, min(1.0, wx))
        wy = max(0.0, min(1.0, wy))
        wx1 = 1.0 - wx
        wy1 = 1.0 - wy

        ! 5. Билинейная интерполяция FI (широта) и DL (долгота)
        lat = wx1*wy1*fi(i1, j1) + &
              wx*wy1*fi(i2, j1) + &
              wx1*wy*fi(i1, j2) + &
              wx*wy*fi(i2, j2)

        lon = wx1*wy1*dl(i1, j1) + &
              wx*wy1*dl(i2, j1) + &
              wx1*wy*dl(i1, j2) + &
              wx*wy*dl(i2, j2)

        ! 6. Нормализация долготы в [-180, 180] для консистентности с ERA5
        ! (ERA5 использует 0..360, но эта функция возвращает [-180,180])
        if (lon .gt. 180.0) lon = lon - 360.0
        if (lon .lt. -180.0) lon = lon + 360.0

        ok = .true.
    end subroutine model_coords_to_latlon

    ! ========================================================================
    !   ПРЯМАЯ ПРОЕКЦИЯ: ШИРОТА/ДОЛГОТА → МОДЕЛЬНЫЕ КООРДИНАТЫ
    ! ========================================================================
    ! Поиск ближайшей точки на модельной сетке по заданной lat/lon.
    ! Использует билинейный поиск по массивам FI/DL.
    ! ВАЖНО: эта функция ищет индексы i,j такие, что fi(i,j)≈lat, dl(i,j)≈lon.
    ! Так как сетка не является регулярной в lat/lon (полярная стереографическая
    ! проекция EPSG:3996), используем простой поиск по 2D массиву.
    !
    ! Аргументы:
    !   lat, lon         - географическая позиция [°]
    !   x_model, y_model - позиция в модельных координатах [м] (выход)
    !   ok               - флаг успеха (выход)
    ! ========================================================================
    subroutine latlon_to_model_coords(lat, lon, x_model, y_model, ok)
        real, intent(in) :: lat, lon
        real, intent(out) :: x_model, y_model
        logical, intent(out) :: ok

        integer :: i, j, i_best, j_best
        real :: min_dist2, dist2
        real :: lon_normalized

        ok = .false.

        ! Нормализовать долготу к диапазону модели (DL в KOORD.DAT обычно 0..360 или -180..180)
        ! Определим диапазон DL в массиве модели
        lon_normalized = lon
        ! Если DL в модели положительные (0..360), приведём lon к тому же диапазону
        if (dl(1, 1) .ge. 0.0 .and. lon_normalized .lt. 0.0) then
            lon_normalized = lon_normalized + 360.0
        else if (dl(1, 1) .lt. 0.0 .and. lon_normalized .ge. 180.0) then
            lon_normalized = lon_normalized - 360.0
        end if

        ! Простой поиск ближайшей точки по евклидову расстоянию в lat/lon
        ! (не идеально для полярной проекции, но достаточно для инициализации)
        min_dist2 = 1.0e20
        i_best = 1
        j_best = 1

        do i = 1, is1
            do j = 1, js1
                ! Пропустить сушу (ht = 8888)
                if (abs(ht(i, j) - 8888.0) .lt. 1e-8) cycle

                dist2 = (fi(i, j) - lat)**2 + (dl(i, j) - lon_normalized)**2
                if (dist2 .lt. min_dist2) then
                    min_dist2 = dist2
                    i_best = i
                    j_best = j
                end if
            end do
        end do

        if (min_dist2 .gt. 1.0) then
            ! Слишком далеко от любой точки сетки (>1 deg ~ 100 km)
            return
        end if

        ! Перевести индексы в модельные координаты
        x_model = real(j_best - 1)*13890.0
        y_model = real(i_best - 1)*13890.0

        ok = .true.
    end subroutine latlon_to_model_coords

    ! ========================================================================
    !   ПОЛУЧЕНИЕ АТМОСФЕРНОГО ФОРСИНГА ERA5
    ! ========================================================================
    ! Билинейная интерполяция ERA5 полей на lat/lon позиции айсберга.
    ! Временной индекс через era5_find_time_index (real(8) время).
    ! Все поля интерполируются через era5_bilinear2d (real(8) точность).
    !
    ! Переменные ERA5:
    !   u10, v10  - ветер 10м [м/с]
    !   t2m, d2m  - температура и точка росы 2м [К]
    !   tcc       - общая облачность [0-1]
    !   msl       - давление на уровне моря [Па]
    !   snowfall  - снегопад [м/с] (экв. воды)
    !
    ! Аргументы:
    !   lat, lon         - позиция [°]
    !   model_time_sec   - модельное время [с] с эпохи
    !   atmos            - выходная структура форсинга
    !   ok               - флаг успеха
    ! ========================================================================
    subroutine get_atmos_forcing(lat, lon, model_time_sec, atmos, ok)
        real, intent(in) :: lat, lon
        real, intent(in) :: model_time_sec
        type(atmos_forcing), intent(out) :: atmos
        logical, intent(out) :: ok

        integer :: tidx
        real(8) :: val8, lat8, lon8, time_sec8
        logical :: interp_ok

        ok = .false.

        if (.not. era5_is_open) then
            print *, "FORCING ERROR: ERA5 dataset not open"
            return
        end if

        time_sec8 = model_time_sec
        call era5_find_time_index(time_sec8, tidx)

        lat8 = lat
        lon8 = lon

        interp_ok = era5_bilinear2d(era5_u10(:, :, tidx), lat8, lon8, val8)
        if (.not. interp_ok) then
            print *, "FORCING WARNING: u10 interpolation failed at ", lat, lon
            return
        end if
        atmos%u10 = val8

        interp_ok = era5_bilinear2d(era5_v10(:, :, tidx), lat8, lon8, val8)
        atmos%v10 = val8

        interp_ok = era5_bilinear2d(era5_t2m(:, :, tidx), lat8, lon8, val8)
        atmos%t2m = val8

        interp_ok = era5_bilinear2d(era5_d2m(:, :, tidx), lat8, lon8, val8)
        atmos%d2m = val8

        interp_ok = era5_bilinear2d(era5_tcc(:, :, tidx), lat8, lon8, val8)
        atmos%tcc = val8

        interp_ok = era5_bilinear2d(era5_msl(:, :, tidx), lat8, lon8, val8)
        atmos%msl = val8

        interp_ok = era5_bilinear2d(era5_snowfall(:, :, tidx), lat8, lon8, val8)
        atmos%snowfall = val8

        ok = .true.
    end subroutine get_atmos_forcing

    ! ========================================================================
    !   ВЕРТИКАЛЬНАЯ ИНТЕРПОЛЯЦИЯ: T, S НА ГЛУБИНЕ ОСАДКИ
    ! ========================================================================
    ! Линейная интерполяция по вертикали между уровнями модели.
    ! Экстраполяция ниже максимального уровня (prof%z(nlevels)) —
    ! постоянные значения T/S от глубжайшего уровня (Stage 9.3 fix).
    !
    ! Аргументы:
    !   prof       - профиль океана (intent(in))
    !   draft      - глубина осадки [м] (intent(in))
    !   field_name - "temp" или "salt" (intent(in))
    !   val        - интерполированное значение (выход)
    ! ========================================================================
    function interp_at_draft(prof, draft, field_name) result(val)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        character(len=*), intent(in) :: field_name
        real :: val

        integer :: k, k1
        real :: z1, z2, w

        ! Выше первого уровня — значение на поверхности
        if (draft .le. prof%z(1)) then
            select case (field_name)
            case ("temp"); val = prof%temp(1)
            case ("salt"); val = prof%salt(1)
            case default; val = 0.0
            end select
            return
        end if

        ! Ниже последнего уровня модели — экстраполяция константой (Stage 9.3 fix)
        if (draft .ge. prof%z(prof%nlevels)) then
            select case (field_name)
            case ("temp"); val = prof%temp(prof%nlevels)
            case ("salt"); val = prof%salt(prof%nlevels)
            case default; val = 0.0
            end select
            return
        end if

        ! Внутри профиля — линейная интерполяция
        do k = 1, prof%nlevels - 1
            if (prof%z(k) .le. draft .and. draft .lt. prof%z(k + 1)) then
                k1 = k
                exit
            end if
        end do

        z1 = prof%z(k1)
        z2 = prof%z(k1 + 1)
        w = (draft - z1)/(z2 - z1)
        w = max(0.0, min(1.0, w))

        select case (field_name)
        case ("temp")
            val = (1.0 - w)*prof%temp(k1) + w*prof%temp(k1 + 1)
        case ("salt")
            val = (1.0 - w)*prof%salt(k1) + w*prof%salt(k1 + 1)
        case default
            val = 0.0
        end select
    end function interp_at_draft

    ! ========================================================================
    !   ГЛУБИННО-СРЕДНИЙ ТЕРМИЧЕСКИЙ ФОРСИНГ (для бокового плавления)
    ! ========================================================================
    ! Stage 9.1 §14, Method A:
    !   ⟨ΔT⟩_D = (1/D) ∫₀ᴰ max(0, T(z) - Tf(z)) dz
    ! где Tf(z) = -54.0 * S(z) [°C], S — массовая доля.
    ! Интеграл берётся по вертикали от поверхности до осадки D.
    ! Если D > max(model z) — экстраполяция постоянными T/S от глубжайшего уровня.
    !
    ! Аргументы:
    !   prof        - профиль океана
    !   draft       - осадка [м]
    !   delta_t_avg - глубинно-усреднённое ΔT [°C] (выход)
    ! ========================================================================
    function depth_averaged_thermal_forcing(prof, draft) result(delta_t_avg)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real :: delta_t_avg

        integer :: k
        real :: z_top, z_bot, dz_layer, tf, delta_t
        real :: integral, total_depth
        real :: max_z, temp_deep, salt_deep, tf_deep

        integral = 0.0
        total_depth = 0.0

        max_z = prof%z(prof%nlevels)
        temp_deep = prof%temp(prof%nlevels)
        salt_deep = prof%salt(prof%nlevels)
        tf_deep = -54.0*salt_deep

        ! Интеграл по модельным уровням
        do k = 1, prof%nlevels
            z_top = prof%z(k) - 0.5*prof%dz(k)
            z_bot = prof%z(k) + 0.5*prof%dz(k)

            if (z_top .ge. draft) exit
            if (z_bot .gt. draft) z_bot = draft

            dz_layer = z_bot - z_top
            if (dz_layer .le. 0.0) cycle

            tf = -54.0*prof%salt(k)
            delta_t = prof%temp(k) - tf
            if (delta_t .gt. 0.0) then
                integral = integral + delta_t*dz_layer
            end if

            total_depth = total_depth + dz_layer
        end do

        ! Экстраполяция ниже максимального модельного уровня до осадки
        if (draft .gt. max_z) then
            dz_layer = draft - max_z
            delta_t = temp_deep - tf_deep
            if (delta_t .gt. 0.0) then
                integral = integral + delta_t*dz_layer
            end if
            total_depth = total_depth + dz_layer
        end if

        if (total_depth .gt. 0.0) then
            delta_t_avg = integral/total_depth
        else
            delta_t_avg = 0.0
        end if
    end function depth_averaged_thermal_forcing

    ! ========================================================================
    !   ГЛУБИННО-ИНТЕГРИРОВАННЫЕ ТЕЧЕНИЯ (Method A)
    ! ========================================================================
    ! Stage 9.1 §18, Method A — слой-за-слоем интеграл:
    !   u_avg = (1/D) ∫₀ᴰ u(z) dz  ≈ Σ u_k * Δz_k / D
    !   v_avg = (1/D) ∫₀ᴰ v(z) dz  ≈ Σ v_k * Δz_k / D
    ! Используется для водного трения Method A (слой-за-слоем).
    ! Возвращает также профили u(z), v(z), z_layers для расчёта сил по слоям.
    !
    ! Ниже максимального моделируемого уровня (45м) — экстраполяция
    ! нулевой скоростью (Stage 9.3 fix).
    !
    ! Аргументы:
    !   prof           - профиль океана (intent(in))
    !   draft          - осадка [м] (intent(in))
    !   u_avg, v_avg   - глубинно-усреднённые скорости [м/с] (выход)
    !   u_profile      - профиль U по слоям [м/с] (выход, allocatable)
    !   v_profile      - профиль V по слоям [м/с] (выход, allocatable)
    !   z_layers       - глубины центров слоёв [м] (выход, allocatable)
    !   n_layers       - число слоёв интегрирования (выход)
    ! ========================================================================
    subroutine depth_integrated_currents(prof, draft, u_avg, v_avg, &
                                         u_profile, v_profile, z_layers, n_layers)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real, intent(out) :: u_avg, v_avg
        real, intent(out), allocatable :: u_profile(:), v_profile(:), z_layers(:)
        integer, intent(out) :: n_layers

        integer :: k
        real :: z_top, z_bot, dz_layer
        real :: u_int, v_int, total_dz
        real :: max_z

        max_z = prof%z(prof%nlevels)

        ! Подсчёт числа слоёв для интегрирования
        n_layers = 0
        do k = 1, prof%nlevels
            z_top = prof%z(k) - 0.5*prof%dz(k)
            z_bot = prof%z(k) + 0.5*prof%dz(k)
            if (z_top .lt. draft) n_layers = n_layers + 1
            if (z_bot .ge. draft) exit
        end do

        ! Добавить слой для экстраполяции ниже max модели
        if (draft .gt. max_z) then
            n_layers = n_layers + 1
        end if

        if (n_layers .eq. 0) then
            u_avg = 0.0
            v_avg = 0.0
            allocate (u_profile(0), v_profile(0), z_layers(0))
            return
        end if

        allocate (u_profile(n_layers), v_profile(n_layers), z_layers(n_layers))

        u_int = 0.0
        v_int = 0.0
        total_dz = 0.0

        do k = 1, n_layers
            if (k .le. prof%nlevels) then
                ! Внутри профиля модели
                z_top = prof%z(k) - 0.5*prof%dz(k)
                z_bot = prof%z(k) + 0.5*prof%dz(k)
                if (z_bot .gt. draft) z_bot = draft
                dz_layer = z_bot - z_top

                z_layers(k) = 0.5*(z_top + z_bot)
                u_profile(k) = prof%u(k)
                v_profile(k) = prof%v(k)
            else
                ! Экстраполяция ниже max модели: нулевая скорость
                z_top = max_z
                z_bot = draft
                dz_layer = z_bot - z_top

                z_layers(k) = 0.5*(z_top + z_bot)
                u_profile(k) = 0.0
                v_profile(k) = 0.0
            end if

            u_int = u_int + u_profile(k)*dz_layer
            v_int = v_int + v_profile(k)*dz_layer
            total_dz = total_dz + dz_layer
        end do

        if (total_dz .gt. 0.0) then
            u_avg = u_int/total_dz
            v_avg = v_int/total_dz
        else
            u_avg = 0.0
            v_avg = 0.0
        end if
    end subroutine depth_integrated_currents

end module iceberg_forcing
