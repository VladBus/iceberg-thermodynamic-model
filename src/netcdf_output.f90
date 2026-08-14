! ==============================================================================
! Модуль: netcdf_output
! Назначение: Самодостаточный экспорт диагностических полей модели в NetCDF.
! Физика: Сохраняет T [degC], S [массовая доля], геометрию Z-сетки и маску воды.
! Ответственность: Формирует метаданные, необходимые для анализа и визуализации.
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

        status = nf90_put_att(ncid, nf90_global, 'title', 'AARI iceberg thermodynamic model output')
        if (.not. nc_ok(status, 'write global title')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, nf90_global, 'Conventions', 'CF-1.10')
        if (.not. nc_ok(status, 'write global conventions')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_def_dim(ncid, 'x', is1, x_dimid)
        if (.not. nc_ok(status, 'define x dimension')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_dim(ncid, 'y', js1, y_dimid)
        if (.not. nc_ok(status, 'define y dimension')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_dim(ncid, 'depth', ks, z_dimid)
        if (.not. nc_ok(status, 'define depth dimension')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_def_var(ncid, 'x', nf90_real, (/x_dimid/), x_varid)
        if (.not. nc_ok(status, 'define x coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_var(ncid, 'y', nf90_real, (/y_dimid/), y_varid)
        if (.not. nc_ok(status, 'define y coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_var(ncid, 'depth', nf90_real, (/z_dimid/), z_varid)
        if (.not. nc_ok(status, 'define depth coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_var(ncid, 'water_column_levels', nf90_int, (/x_dimid, y_dimid/), level_varid)
        if (.not. nc_ok(status, 'define water mask')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_var(ncid, 'temperature', nf90_real, (/x_dimid, y_dimid, z_dimid/), temp_varid)
        if (.not. nc_ok(status, 'define temperature')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_def_var(ncid, 'salinity', nf90_real, (/x_dimid, y_dimid, z_dimid/), salt_varid)
        if (.not. nc_ok(status, 'define salinity')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_put_att(ncid, x_varid, 'units', 'km')
        if (.not. nc_ok(status, 'write x units')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, y_varid, 'units', 'km')
        if (.not. nc_ok(status, 'write y units')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, z_varid, 'units', 'm')
        if (.not. nc_ok(status, 'write depth units')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, temp_varid, 'units', 'degree_Celsius')
        if (.not. nc_ok(status, 'write temperature units')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, salt_varid, 'units', '1')
        if (.not. nc_ok(status, 'write salinity units')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_att(ncid, salt_varid, 'comment', 'mass fraction; 0.033 is approximately 33 PSU')
        if (.not. nc_ok(status, 'write salinity comment')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_enddef(ncid)
        if (.not. nc_ok(status, 'end define mode')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_put_var(ncid, x_varid, x_coord)
        if (.not. nc_ok(status, 'write x coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_var(ncid, y_varid, y_coord)
        if (.not. nc_ok(status, 'write y coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_var(ncid, z_varid, depth)
        if (.not. nc_ok(status, 'write depth coordinate')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_var(ncid, level_varid, kt1)
        if (.not. nc_ok(status, 'write water mask')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_var(ncid, temp_varid, t2)
        if (.not. nc_ok(status, 'write temperature')) then
            status = nf90_close(ncid)
            return
        end if
        status = nf90_put_var(ncid, salt_varid, s2)
        if (.not. nc_ok(status, 'write salinity')) then
            status = nf90_close(ncid)
            return
        end if

        status = nf90_close(ncid)
        if (.not. nc_ok(status, 'close '//trim(filename))) return
        print *, '>>> Successfully wrote NetCDF file: ', trim(filename)
    end subroutine write_nc

    logical function nc_ok(status, operation)
        integer, intent(in) :: status
        character(len=*), intent(in) :: operation

        nc_ok = status .eq. nf90_noerr
        if (.not. nc_ok) print *, 'NetCDF error in ', trim(operation), ': ', trim(nf90_strerror(status))
    end function nc_ok

end module netcdf_output
