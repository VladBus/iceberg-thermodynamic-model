! ==============================================================================
! Модуль: netcdf_output
! Назначение: Самодостаточный экспорт диагностических полей модели в NetCDF.
! Физика: Сохраняет T [K], S [массовая доля], 3D-течения U/V/W [м/с],
!         геометрию Z-сетки, маску воды и диагностические поля атмосферного
!         форсинга (ветер, напряжения, градиенты давления, температура воздуха).
! Единицы: Внешний интерфейс - канонические единицы СИ (см. Stage5.5b):
!   T/air_temp [K] (внутренние degC + 273.15), U/V/W/wind_x/wind_y [m/s]
!   (внутренние cm/s * 0.01), tau [Pa] (dyn/cm2 * 0.1), dp [Pa/m] (hPa/km * 0.1),
!   air_press [Pa] (hPa * 100), density_anomaly [kg/m3] (g/cm3 * 1000),
!   salinity_mass_fraction [-], humidity/cloud [-], era5_snowfall_rate [m/s].
! Внутреннее состояние модели НЕ изменяется - конверсия только на границе вывода.
! Ответственность: Формирует метаданные в стандарте CF-1.10.
!
! Соглашение об осях (модельная B-сетка Аракавы):
!   Индексы массивов: (i, j, k). Первый индекс i - первый размер массива.
!   Модельная ось X <-> индекс j <-> u-компонента; ось Y <-> индекс i <-> v-компонента.
!   В NetCDF размерности объявляются как (/x, y, depth/): переменные записываются
!   напрямую из (i,j)-массивов, поэтому NetCDF-ось x <-> индекс i, ось y <-> индекс j.
!   Точная география задается 2D-координатами latitude/longitude (fi(i,j)/dl(i,j)),
!   поэтому для визуализации имена осей x/y не критичны.
! ==============================================================================

module netcdf_output
    use param
    use netcdf
    implicit none

contains

    subroutine write_nc(filename)
        character(len=*), intent(in) :: filename
        integer :: ncid, x_dimid, y_dimid, z_dimid, zw_dimid
        integer :: x_varid, y_varid, z_varid, zw_varid, level_varid, temp_varid, salt_varid
        integer :: u_varid, v_varid, w_varid
        integer :: lat_varid, lon_varid
        integer :: wind_varid, windx_varid, windy_varid
        integer :: tx_varid, ty_varid
        integer :: dpx_varid, dpy_varid
        integer :: tatm_varid, patm_varid
        integer :: humid_varid, cloud_varid, era5_snowfall_rate_varid
        integer :: status, i, k
        integer :: ro_varid
        real :: x_coord(is1), y_coord(js1), depth(ks), depth_w(ks1)
        ! Буферы канонических единиц СИ (только на границе вывода; внутренние
        ! массивы param не изменяются). Stage 5.5b.
        real :: t_k(is1, js1, ks), ro_kgm3(is1, js1, ks)
        real :: u_ms(is1, js1, ks), v_ms(is1, js1, ks), w_ms(is1, js1, ks1)
        real :: windx_ms(is1, js1), windy_ms(is1, js1)
        real :: tau_pa(is1, js1), tauy_pa(is1, js1)
        real :: dpx_pam(is1, js1), dpy_pam(is1, js1)
        real :: tatm_k(is1, js1), patm_pa(is1, js1)

        ! x/y - индексы регулярной сетки в км; dx в модели задан в сантиметрах.
        do i = 1, is1
            x_coord(i) = real(i - 1)*13.89
        end do
        do i = 1, js1
            y_coord(i) = real(i - 1)*13.89
        end do
        ! depth = центры Z-уровней (реальный массив z из param.f90) [см] -> [м].
        depth = z*1.0e-2
        ! depth_w = границы Z-уровней (для W на ks1 узлах): поверхность 0,
        ! середина между соседними центрами z, дно - экстраполяция нижней границы.
        depth_w(1) = 0.0
        do k = 2, ks
            depth_w(k) = 0.5*(z(k - 1) + z(k))*1.0e-2
        end do
        depth_w(ks1) = z(ks)*1.0e-2 + 0.5*(z(ks) - z(ks - 1))*1.0e-2

        status = nf90_create(trim(filename), nf90_clobber, ncid)
        if (.not. nc_ok(status, 'create '//trim(filename))) return

        ! Глобальные атрибуты CF-1.10
        status = nf90_put_att(ncid, nf90_global, 'title', 'AARI iceberg thermodynamic model output')
        if (.not. nc_ok(status, 'write global title')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_att(ncid, nf90_global, 'Conventions', 'CF-1.10')
        if (.not. nc_ok(status, 'write global conventions')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_att(ncid, nf90_global, 'unit_system', 'SI (canonical external units, Stage 5.5b)')
        if (.not. nc_ok(status, 'write global unit_system')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_att(ncid, nf90_global, 'source', 'AARI Iceberg Thermodynamic Model (Fortran 2018 modernization)')
        if (.not. nc_ok(status, 'write global source')) then
            status = nf90_close(ncid); return
        end if

        ! Измерения
        status = nf90_def_dim(ncid, 'x', is1, x_dimid)
        if (.not. nc_ok(status, 'define x dimension')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_dim(ncid, 'y', js1, y_dimid)
        if (.not. nc_ok(status, 'define y dimension')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_dim(ncid, 'depth', ks, z_dimid)
        if (.not. nc_ok(status, 'define depth dimension')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_dim(ncid, 'depth_w', ks1, zw_dimid)
        if (.not. nc_ok(status, 'define depth_w dimension')) then
            status = nf90_close(ncid); return
        end if

        ! Координатные переменные
        status = nf90_def_var(ncid, 'x', nf90_real, (/x_dimid/), x_varid)
        if (.not. nc_ok(status, 'define x coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'y', nf90_real, (/y_dimid/), y_varid)
        if (.not. nc_ok(status, 'define y coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'depth', nf90_real, (/z_dimid/), z_varid)
        if (.not. nc_ok(status, 'define depth coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'depth_w', nf90_real, (/zw_dimid/), zw_varid)
        if (.not. nc_ok(status, 'define depth_w coordinate')) then
            status = nf90_close(ncid); return
        end if

        ! Географические координаты сетки
        status = nf90_def_var(ncid, 'latitude', nf90_real, (/x_dimid, y_dimid/), lat_varid)
        if (.not. nc_ok(status, 'define latitude')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'longitude', nf90_real, (/x_dimid, y_dimid/), lon_varid)
        if (.not. nc_ok(status, 'define longitude')) then
            status = nf90_close(ncid); return
        end if

        ! Океанические переменные
     status = nf90_def_var(ncid, 'water_column_levels', nf90_int, (/x_dimid, y_dimid/), level_varid)
        if (.not. nc_ok(status, 'define water mask')) then
            status = nf90_close(ncid); return
        end if
    status = nf90_def_var(ncid, 'temperature', nf90_real, (/x_dimid, y_dimid, z_dimid/), temp_varid)
        if (.not. nc_ok(status, 'define temperature')) then
            status = nf90_close(ncid); return
        end if
       status = nf90_def_var(ncid, 'salinity_mass_fraction', nf90_real, (/x_dimid, y_dimid, z_dimid/), salt_varid)
        if (.not. nc_ok(status, 'define salinity')) then
            status = nf90_close(ncid); return
        end if

        ! Плотность RO [г/см3] - диагностика этапа 3.1 (EOS), для Python-анализа
        ! Python НЕ пересчитывает EOS, а читает RO из вывода модели.
        status = nf90_def_var(ncid, 'density_anomaly', nf90_real, (/x_dimid, y_dimid, z_dimid/), ro_varid)
        if (.not. nc_ok(status, 'define density')) then
            status = nf90_close(ncid); return
        end if

        ! 3D-течения океана [см/с]
        status = nf90_def_var(ncid, 'u_velocity', nf90_real, (/x_dimid, y_dimid, z_dimid/), u_varid)
        if (.not. nc_ok(status, 'define u_velocity')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'v_velocity', nf90_real, (/x_dimid, y_dimid, z_dimid/), v_varid)
        if (.not. nc_ok(status, 'define v_velocity')) then
            status = nf90_close(ncid); return
        end if
       status = nf90_def_var(ncid, 'w_velocity', nf90_real, (/x_dimid, y_dimid, zw_dimid/), w_varid)
        if (.not. nc_ok(status, 'define w_velocity')) then
            status = nf90_close(ncid); return
        end if

        ! Диагностические поля форсинга
        status = nf90_def_var(ncid, 'wind_speed', nf90_real, (/x_dimid, y_dimid/), wind_varid)
        if (.not. nc_ok(status, 'define wind_speed')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'wind_x', nf90_real, (/x_dimid, y_dimid/), windx_varid)
        if (.not. nc_ok(status, 'define wind_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'wind_y', nf90_real, (/x_dimid, y_dimid/), windy_varid)
        if (.not. nc_ok(status, 'define wind_y')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'tau_x', nf90_real, (/x_dimid, y_dimid/), tx_varid)
        if (.not. nc_ok(status, 'define tau_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'tau_y', nf90_real, (/x_dimid, y_dimid/), ty_varid)
        if (.not. nc_ok(status, 'define tau_y')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'dp_x', nf90_real, (/x_dimid, y_dimid/), dpx_varid)
        if (.not. nc_ok(status, 'define dp_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'dp_y', nf90_real, (/x_dimid, y_dimid/), dpy_varid)
        if (.not. nc_ok(status, 'define dp_y')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'air_temp', nf90_real, (/x_dimid, y_dimid/), tatm_varid)
        if (.not. nc_ok(status, 'define air_temp')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'air_press', nf90_real, (/x_dimid, y_dimid/), patm_varid)
        if (.not. nc_ok(status, 'define air_press')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'humidity', nf90_real, (/x_dimid, y_dimid/), humid_varid)
        if (.not. nc_ok(status, 'define humidity')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'cloud', nf90_real, (/x_dimid, y_dimid/), cloud_varid)
        if (.not. nc_ok(status, 'define cloud')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_def_var(ncid, 'era5_snowfall_rate', nf90_real, (/x_dimid, y_dimid/), era5_snowfall_rate_varid)
        if (.not. nc_ok(status, 'define era5_snowfall_rate')) then
            status = nf90_close(ncid); return
        end if

        ! Атрибуты переменных
        call set_att(ncid, x_varid, 'units', 'km')
        call set_att(ncid, x_varid, 'standard_name', 'projection_x_coordinate')

        call set_att(ncid, y_varid, 'units', 'km')
        call set_att(ncid, y_varid, 'standard_name', 'projection_y_coordinate')

        call set_att(ncid, z_varid, 'units', 'm')
        call set_att(ncid, z_varid, 'standard_name', 'depth')
        call set_att(ncid, z_varid, 'positive', 'down')

        call set_att(ncid, zw_varid, 'units', 'm')
        call set_att(ncid, zw_varid, 'long_name', 'depth of W-level boundaries')
        call set_att(ncid, zw_varid, 'positive', 'down')

        call set_att(ncid, lat_varid, 'units', 'degrees_north')
        call set_att(ncid, lat_varid, 'standard_name', 'latitude')

        call set_att(ncid, lon_varid, 'units', 'degrees_east')
        call set_att(ncid, lon_varid, 'standard_name', 'longitude')

        call set_att(ncid, level_varid, 'long_name', 'number of active water levels')
        call set_att(ncid, level_varid, 'units', '1')

        call set_att(ncid, temp_varid, 'units', 'K')
        call set_att(ncid, temp_varid, 'standard_name', 'sea_water_temperature')
        call set_att(ncid, temp_varid, 'comment', 'canonical SI unit K; internal model unit is degC')

        call set_att(ncid, salt_varid, 'units', '1')
        call set_att(ncid, salt_varid, 'standard_name', 'sea_water_salinity')
        call set_att(ncid, salt_varid, 'comment', 'mass fraction (kg/kg), NOT PSU; 0.033 is approximately 33 g/kg')

        call set_att(ncid, ro_varid, 'units', 'kg m-3')
        call set_att(ncid, ro_varid, 'long_name', 'seawater density anomaly')
        call set_att(ncid, ro_varid, 'comment', 'computed by Fortran Eckart EOS (Stage 3.1); Python must not recompute. '// &
                     'Value is density ANOMALY (rho - 1.02 g/cm3) in kg m-3 (internal g cm-3 * 1000)')

        call set_att(ncid, u_varid, 'units', 'm s-1')
        call set_att(ncid, u_varid, 'long_name', 'x-component of ocean velocity (along model X axis = j index)')
        call set_att(ncid, u_varid, 'comment', 'Model-grid component, NOT geographic eastward. '// &
                     'NetCDF y-axis <-> model j <-> u; NetCDF x-axis <-> model i <-> v. '// &
                     'Canonical SI unit m s-1 (internal cm s-1 * 0.01)')

        call set_att(ncid, v_varid, 'units', 'm s-1')
        call set_att(ncid, v_varid, 'long_name', 'y-component of ocean velocity (along model Y axis = i index)')
       call set_att(ncid, v_varid, 'comment', 'Model-grid component, NOT geographic northward. '// &
                     'NetCDF y-axis <-> model j <-> u; NetCDF x-axis <-> model i <-> v. '// &
                     'Canonical SI unit m s-1 (internal cm s-1 * 0.01)')

        call set_att(ncid, w_varid, 'units', 'm s-1')
        call set_att(ncid, w_varid, 'standard_name', 'upward_sea_water_velocity')
        call set_att(ncid, w_varid, 'long_name', 'vertical ocean velocity')
        call set_att(ncid, w_varid, 'comment', 'canonical SI unit m s-1 (internal cm s-1 * 0.01)')

        call set_att(ncid, wind_varid, 'units', 'm s-1')
        call set_att(ncid, wind_varid, 'standard_name', 'wind_speed')

        call set_att(ncid, windx_varid, 'units', 'm s-1')
        call set_att(ncid, windx_varid, 'long_name', 'x-component of wind velocity')
        call set_att(ncid, windx_varid, 'comment', 'canonical SI unit m s-1 (internal cm s-1 * 0.01)')

        call set_att(ncid, windy_varid, 'units', 'm s-1')
        call set_att(ncid, windy_varid, 'long_name', 'y-component of wind velocity')
        call set_att(ncid, windy_varid, 'comment', 'canonical SI unit m s-1 (internal cm s-1 * 0.01)')

        call set_att(ncid, tx_varid, 'units', 'Pa')
        call set_att(ncid, tx_varid, 'long_name', 'x-component of surface wind stress')
        call set_att(ncid, tx_varid, 'comment', 'canonical SI unit Pa (internal dyn cm-2 * 0.1)')

        call set_att(ncid, ty_varid, 'units', 'Pa')
        call set_att(ncid, ty_varid, 'long_name', 'y-component of surface wind stress')
        call set_att(ncid, ty_varid, 'comment', 'canonical SI unit Pa (internal dyn cm-2 * 0.1)')

        call set_att(ncid, dpx_varid, 'units', 'Pa m-1')
        call set_att(ncid, dpx_varid, 'long_name', 'x-component of sea level pressure gradient')
        call set_att(ncid, dpx_varid, 'comment', 'canonical SI unit Pa m-1 (internal hPa km-1 * 0.1)')

        call set_att(ncid, dpy_varid, 'units', 'Pa m-1')
        call set_att(ncid, dpy_varid, 'long_name', 'y-component of sea level pressure gradient')
        call set_att(ncid, dpy_varid, 'comment', 'canonical SI unit Pa m-1 (internal hPa km-1 * 0.1)')

        call set_att(ncid, tatm_varid, 'units', 'K')
        call set_att(ncid, tatm_varid, 'standard_name', 'air_temperature')
        call set_att(ncid, tatm_varid, 'comment', 'canonical SI unit K; internal model unit is degC')

        call set_att(ncid, patm_varid, 'units', 'Pa')
        call set_att(ncid, patm_varid, 'standard_name', 'air_pressure')
        call set_att(ncid, patm_varid, 'comment', 'canonical SI unit Pa (internal hPa * 100)')

        call set_att(ncid, humid_varid, 'units', '1')
        call set_att(ncid, humid_varid, 'standard_name', 'relative_humidity')
        call set_att(ncid, humid_varid, 'long_name', 'relative humidity from ERA5 dew point')

        call set_att(ncid, cloud_varid, 'units', '1')
        call set_att(ncid, cloud_varid, 'standard_name', 'cloud_area_fraction')
        call set_att(ncid, cloud_varid, 'long_name', 'total cloud cover from ERA5')

        call set_att(ncid, era5_snowfall_rate_varid, 'units', 'm s-1')
        call set_att(ncid, era5_snowfall_rate_varid, 'standard_name', 'snowfall_flux')
        call set_att(ncid, era5_snowfall_rate_varid, 'long_name', 'ERA5 snowfall rate (interpolated from 12-hourly accumulated sf)')

        status = nf90_enddef(ncid)
        if (.not. nc_ok(status, 'end define mode')) then
            status = nf90_close(ncid); return
        end if

        ! Запись данных
        status = nf90_put_var(ncid, x_varid, x_coord)
        if (.not. nc_ok(status, 'write x coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, y_varid, y_coord)
        if (.not. nc_ok(status, 'write y coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, z_varid, depth)
        if (.not. nc_ok(status, 'write depth coordinate')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, zw_varid, depth_w)
        if (.not. nc_ok(status, 'write depth_w coordinate')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, lat_varid, fi)
        if (.not. nc_ok(status, 'write latitude')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, lon_varid, dl)
        if (.not. nc_ok(status, 'write longitude')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, level_varid, kt1)
        if (.not. nc_ok(status, 'write water mask')) then
            status = nf90_close(ncid); return
        end if

        ! Конверсия во внешние канонические единицы СИ (только на границе вывода;
        ! внутренние массивы param не изменяются). Stage 5.5b.
        t_k = t2 + 273.15
        ro_kgm3 = ro*1000.0
        u_ms = u2*0.01
        v_ms = v2*0.01
        w_ms = w*0.01
        windx_ms = windx*0.01
        windy_ms = windy*0.01
        tau_pa = tx*0.1
        tauy_pa = ty*0.1
        dpx_pam = dpx*0.1
        dpy_pam = dpy*0.1
        tatm_k = tatm + 273.15
        patm_pa = patm*100.0

        status = nf90_put_var(ncid, temp_varid, t_k)
        if (.not. nc_ok(status, 'write temperature')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, salt_varid, s2)
        if (.not. nc_ok(status, 'write salinity')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, ro_varid, ro_kgm3)
        if (.not. nc_ok(status, 'write density')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, u_varid, u_ms)
        if (.not. nc_ok(status, 'write u_velocity')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, v_varid, v_ms)
        if (.not. nc_ok(status, 'write v_velocity')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, w_varid, w_ms)
        if (.not. nc_ok(status, 'write w_velocity')) then
            status = nf90_close(ncid); return
        end if

        ! Запись полей форсинга
        status = nf90_put_var(ncid, wind_varid, wind)
        if (.not. nc_ok(status, 'write wind_speed')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, windx_varid, windx_ms)
        if (.not. nc_ok(status, 'write wind_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, windy_varid, windy_ms)
        if (.not. nc_ok(status, 'write wind_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, tx_varid, tau_pa)
        if (.not. nc_ok(status, 'write tau_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, ty_varid, tauy_pa)
        if (.not. nc_ok(status, 'write tau_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, dpx_varid, dpx_pam)
        if (.not. nc_ok(status, 'write dp_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, dpy_varid, dpy_pam)
        if (.not. nc_ok(status, 'write dp_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, tatm_varid, tatm_k)
        if (.not. nc_ok(status, 'write air_temp')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, patm_varid, patm_pa)
        if (.not. nc_ok(status, 'write air_press')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, humid_varid, humid)
        if (.not. nc_ok(status, 'write humidity')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, cloud_varid, cloud)
        if (.not. nc_ok(status, 'write cloud')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, era5_snowfall_rate_varid, era5_snowfall_rate)
        if (.not. nc_ok(status, 'write era5_snowfall_rate')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_close(ncid)
        if (.not. nc_ok(status, 'close '//trim(filename))) return
        print *, '>>> Successfully wrote NetCDF file: ', trim(filename)
    end subroutine write_nc

    subroutine set_att(ncid, varid, name, val)
        integer, intent(in) :: ncid, varid
        character(len=*), intent(in) :: name, val
        integer :: st
        st = nf90_put_att(ncid, varid, name, trim(val))
        if (.not. nc_ok(st, 'write att '//trim(name))) return
    end subroutine set_att

    logical function nc_ok(status, operation)
        integer, intent(in) :: status
        character(len=*), intent(in) :: operation

        nc_ok = status .eq. nf90_noerr
    if (.not. nc_ok) print *, 'NetCDF error in ', trim(operation), ': ', trim(nf90_strerror(status))
    end function nc_ok

end module netcdf_output
