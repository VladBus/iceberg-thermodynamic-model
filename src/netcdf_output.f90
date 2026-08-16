! ==============================================================================
! Модуль: netcdf_output
! Назначение: Самодостаточный экспорт диагностических полей модели в NetCDF.
! Физика: Сохраняет T [degC], S [массовая доля], геометрию Z-сетки, маску воды
!         и диагностические поля атмосферного форсинга (ветер, напряжения,
!         градиенты давления, температура воздуха).
! Ответственность: Формирует метаданные в стандарте CF-1.10.
! ==============================================================================

module netcdf_output
    use param
    use netcdf
    implicit none

contains

    subroutine write_nc(filename)
        character(len=*), intent(in) :: filename
        integer :: ncid, x_dimid, y_dimid, z_dimid
        integer :: x_varid, y_varid, z_varid, level_varid, temp_varid, salt_varid
        integer :: lat_varid, lon_varid
        integer :: wind_varid, windx_varid, windy_varid
        integer :: tx_varid, ty_varid
        integer :: dpx_varid, dpy_varid
        integer :: tatm_varid, patm_varid
        integer :: status, i
        real :: x_coord(is1), y_coord(js1), depth(ks)

        ! x/y - индексы регулярной сетки в км; dx в модели задан в сантиметрах.
        do i = 1, is1
            x_coord(i) = real(i - 1)*13.89
        end do
        do i = 1, js1
            y_coord(i) = real(i - 1)*13.89
        end do
        depth = z*1.0e-2 ! z [см] -> глубина центра уровня [м].

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
       status = nf90_def_var(ncid, 'salinity', nf90_real, (/x_dimid, y_dimid, z_dimid/), salt_varid)
        if (.not. nc_ok(status, 'define salinity')) then
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

        ! Атрибуты переменных
        call set_att(ncid, x_varid, 'units', 'km')
        call set_att(ncid, x_varid, 'standard_name', 'projection_x_coordinate')

        call set_att(ncid, y_varid, 'units', 'km')
        call set_att(ncid, y_varid, 'standard_name', 'projection_y_coordinate')

        call set_att(ncid, z_varid, 'units', 'm')
        call set_att(ncid, z_varid, 'standard_name', 'depth')
        call set_att(ncid, z_varid, 'positive', 'down')

        call set_att(ncid, lat_varid, 'units', 'degrees_north')
        call set_att(ncid, lat_varid, 'standard_name', 'latitude')

        call set_att(ncid, lon_varid, 'units', 'degrees_east')
        call set_att(ncid, lon_varid, 'standard_name', 'longitude')

        call set_att(ncid, level_varid, 'long_name', 'number of active water levels')
        call set_att(ncid, level_varid, 'units', '1')

        call set_att(ncid, temp_varid, 'units', 'degree_Celsius')
        call set_att(ncid, temp_varid, 'standard_name', 'sea_water_temperature')

        call set_att(ncid, salt_varid, 'units', '1')
        call set_att(ncid, salt_varid, 'standard_name', 'sea_water_salinity')
        call set_att(ncid, salt_varid, 'comment', 'mass fraction; 0.033 is approximately 33 PSU')

        call set_att(ncid, wind_varid, 'units', 'm s-1')
        call set_att(ncid, wind_varid, 'standard_name', 'wind_speed')

        call set_att(ncid, windx_varid, 'units', 'cm s-1')
        call set_att(ncid, windx_varid, 'long_name', 'x-component of wind velocity')

        call set_att(ncid, windy_varid, 'units', 'cm s-1')
        call set_att(ncid, windy_varid, 'long_name', 'y-component of wind velocity')

        call set_att(ncid, tx_varid, 'units', 'dyn cm-2')
        call set_att(ncid, tx_varid, 'long_name', 'x-component of surface wind stress')

        call set_att(ncid, ty_varid, 'units', 'dyn cm-2')
        call set_att(ncid, ty_varid, 'long_name', 'y-component of surface wind stress')

        call set_att(ncid, dpx_varid, 'units', 'hPa km-1')
        call set_att(ncid, dpx_varid, 'long_name', 'x-component of sea level pressure gradient')

        call set_att(ncid, dpy_varid, 'units', 'hPa km-1')
        call set_att(ncid, dpy_varid, 'long_name', 'y-component of sea level pressure gradient')

        call set_att(ncid, tatm_varid, 'units', 'degree_Celsius')
        call set_att(ncid, tatm_varid, 'standard_name', 'air_temperature')

        call set_att(ncid, patm_varid, 'units', 'hPa')
        call set_att(ncid, patm_varid, 'standard_name', 'air_pressure')

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
        status = nf90_put_var(ncid, temp_varid, t2)
        if (.not. nc_ok(status, 'write temperature')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, salt_varid, s2)
        if (.not. nc_ok(status, 'write salinity')) then
            status = nf90_close(ncid); return
        end if

        ! Запись полей форсинга
        status = nf90_put_var(ncid, wind_varid, wind)
        if (.not. nc_ok(status, 'write wind_speed')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, windx_varid, windx)
        if (.not. nc_ok(status, 'write wind_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, windy_varid, windy)
        if (.not. nc_ok(status, 'write wind_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, tx_varid, tx)
        if (.not. nc_ok(status, 'write tau_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, ty_varid, ty)
        if (.not. nc_ok(status, 'write tau_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, dpx_varid, dpx)
        if (.not. nc_ok(status, 'write dp_x')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, dpy_varid, dpy)
        if (.not. nc_ok(status, 'write dp_y')) then
            status = nf90_close(ncid); return
        end if

        status = nf90_put_var(ncid, tatm_varid, tatm)
        if (.not. nc_ok(status, 'write air_temp')) then
            status = nf90_close(ncid); return
        end if
        status = nf90_put_var(ncid, patm_varid, patm)
        if (.not. nc_ok(status, 'write air_press')) then
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
