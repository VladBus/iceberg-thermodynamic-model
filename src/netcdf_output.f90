module netcdf_output
    use param
    use netcdf      ! Подключаем стандартную библиотеку NetCDF
    implicit none

contains

    subroutine write_nc(filename)
        character(len=*), intent(in) :: filename
        integer :: ncid, x_dimid, y_dimid, z_dimid
        integer :: temp_varid, salt_varid
        integer :: status

        ! 1. Создание нового файла (NF90_CLOBBER перезапишет файл, если он уже есть)
        status = nf90_create(trim(filename), NF90_CLOBBER, ncid)
        if (status .ne. nf90_noerr) then
            print *, "NetCDF Error: ", trim(nf90_strerror(status))
            return
        end if

        ! 2. Определение размерностей сетки
        ! Мы используем глобальные константы is1, js1, ks из модуля param
        status = nf90_def_dim(ncid, "x", is1, x_dimid)
        status = nf90_def_dim(ncid, "y", js1, y_dimid)
        status = nf90_def_dim(ncid, "depth", ks, z_dimid)

        ! 3. Определение переменных (3D массивы)
        ! Порядок осей в Фортране (x, y, z) совпадает с нашей архитектурой T2(is1, js1, ks)
    status = nf90_def_var(ncid, "temperature", NF90_REAL, (/x_dimid, y_dimid, z_dimid/), temp_varid)
       status = nf90_def_var(ncid, "salinity", NF90_REAL, (/x_dimid, y_dimid, z_dimid/), salt_varid)

        ! 4. Завершение режима определения (переход к записи данных)
        status = nf90_enddef(ncid)

        ! 5. Прямая запись массивов из памяти в файл
        status = nf90_put_var(ncid, temp_varid, t2)
        status = nf90_put_var(ncid, salt_varid, s2)

        ! 6. Закрытие файла и сохранение на диск
        status = nf90_close(ncid)

        print *, ">>> Successfully wrote NetCDF file: ", trim(filename)

    end subroutine write_nc

end module netcdf_output
