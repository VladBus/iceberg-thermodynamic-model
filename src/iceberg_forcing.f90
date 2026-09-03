! ==============================================================================
! Модуль: iceberg_forcing
! Назначение: Интерфейс форсинга для айсберга — горизонтальная и вертикальная
!             интерполяция океанских и атмосферных профилей на позицию айсберга.
! Физика: Использует существующую инфраструктуру ERA5 (netcdf_input) и
!         модельную сетку (param/grid_coupling) для билинейной интерполяции.
!         Вертикальная интерполяция по Z-уровням модели к слоям осадки айсберга.
! Единицы: Входные поля в единицах модели (CGS для океана, SI для атмосферы).
!          На выходе — профили в SI (м, °C, массовая доля, м/с).
! Точность: default real (float32).
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
    real, parameter :: LAND_MASK_VAL = 8888.0
    real, parameter :: EPS_LAND = 1.0e-8
    real, parameter :: CM_TO_M = 0.01
    real, parameter :: M_TO_CM = 100.0

contains

    ! ========================================================================
    !   ОСНОВНАЯ ФУНКЦИЯ: ПОЛУЧЕНИЕ ОКЕАНСКОГО ПРОФИЛЯ НА ПОЗИЦИИ АЙСБЕРГА
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

        ! 1. Найти индексы сетки
        call model_coords_to_indices(x_model, y_model, i_idx, j_idx, in_domain)
        if (.not. in_domain) then
            print *, "FORCING ERROR: Iceberg position outside model domain"
            return
        end if

        ! 2. Проверить соседние ячейки
        i1 = i_idx; i2 = i_idx + 1
        j1 = j_idx; j2 = j_idx + 1

        if (i2 .gt. is1 .or. j2 .gt. js1) then
            print *, "FORCING ERROR: Iceberg at domain boundary"
            return
        end if

        if (abs(ht(i1, j1) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i2, j1) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i1, j2) - LAND_MASK_VAL) .lt. EPS_LAND .or. &
            abs(ht(i2, j2) - LAND_MASK_VAL) .lt. EPS_LAND) then
            print *, "FORCING WARNING: Iceberg near land"
        end if

        ! 3. Веса билинейной интерполяции
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

        ! 5. Выделить память
        prof%nlevels = kt
        allocate (prof%z(kt), prof%dz(kt), prof%temp(kt), prof%salt(kt), &
                  prof%u(kt), prof%v(kt))

        ! 6. Заполнить профиль
        do k = 1, kt
            prof%z(k) = real(z(k))*CM_TO_M
            prof%dz(k) = real(dz(k))*CM_TO_M

            prof%temp(k) = bilinear_interp_3d(t2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
            prof%salt(k) = bilinear_interp_3d(s2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)
            prof%u(k) = bilinear_interp_3d(u2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)*CM_TO_M
            prof%v(k) = bilinear_interp_3d(v2, i1, i2, j1, j2, k, wx, wy, wx1, wy1)*CM_TO_M
        end do

        ok = .true.
    end subroutine get_ocean_profile

    ! ========================================================================
    !   БИЛИНЕЙНАЯ ИНТЕРПОЛЯЦИЯ 3D ПОЛЯ
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
    !   ПОЛУЧЕНИЕ АТМОСФЕРНОГО ФОРСИНГА ERA5
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
    function interp_at_draft(prof, draft, field_name) result(val)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        character(len=*), intent(in) :: field_name
        real :: val

        integer :: k, k1
        real :: z1, z2, w

        if (draft .le. prof%z(1)) then
            select case (field_name)
            case ("temp"); val = prof%temp(1)
            case ("salt"); val = prof%salt(1)
            case default; val = 0.0
            end select
            return
        end if

        if (draft .ge. prof%z(prof%nlevels)) then
            ! Extrapolate constant below deepest model level
            select case (field_name)
            case ("temp"); val = prof%temp(prof%nlevels)
            case ("salt"); val = prof%salt(prof%nlevels)
            case default; val = 0.0
            end select
            return
        end if

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

        ! Integrate over model levels
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

        ! Extrapolate below max model level to draft
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

        n_layers = 0
        do k = 1, prof%nlevels
            z_top = prof%z(k) - 0.5*prof%dz(k)
            z_bot = prof%z(k) + 0.5*prof%dz(k)
            if (z_top .lt. draft) n_layers = n_layers + 1
            if (z_bot .ge. draft) exit
        end do

        ! Add layer for extrapolation below max model level
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
                z_top = prof%z(k) - 0.5*prof%dz(k)
                z_bot = prof%z(k) + 0.5*prof%dz(k)
                if (z_bot .gt. draft) z_bot = draft
                dz_layer = z_bot - z_top

                z_layers(k) = 0.5*(z_top + z_bot)
                u_profile(k) = prof%u(k)
                v_profile(k) = prof%v(k)
            else
                ! Extrapolation layer below max model level: zero velocity
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
