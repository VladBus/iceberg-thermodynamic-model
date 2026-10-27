module netcdf_seaice_reader
    use netcdf
    use param, only: is1, js1, ngr, an1
    use provenance, only: prov_set_seaice
    implicit none
    private
    public :: s117e_seaice_init, s117e_seaice_active, s117e_read_seaice

    logical :: active = .true.
    character(len=*), parameter :: seaice_path = &
        'data/input/processed/ice/seaice_initial.nc'

contains

    subroutine s117e_seaice_init()
        active = .true.
        print *, 'Stage 11.10: NetCDF sea-ice input DEFAULT (', trim(seaice_path), ')'
        call prov_set_seaice('netcdf', seaice_path, 'PENDING', 'PENDING')
    end subroutine s117e_seaice_init

    logical function s117e_seaice_active()
        s117e_seaice_active = active
    end function s117e_seaice_active

    subroutine s117e_read_seaice()
        integer :: ncid, varid, stat, att_stat
        real(kind=4), allocatable :: buf(:, :, :)
        character(len=64) :: version
        character(len=128) :: checksum

        if (.not. active) return

        stat = nf90_open(trim(seaice_path), NF90_NOWRITE, ncid)
        if (stat /= NF90_NOERR) call fatal('cannot open '//trim(seaice_path))

        call check_dim(ncid, 'i', is1)
        call check_dim(ncid, 'j', js1)
        call check_dim(ncid, 'cat', ngr)

        ! Stage 11.8.0.0: read ACTUAL provenance from the file, not hardcoded.
        version = 'NONE'
        checksum = 'NONE'
        att_stat = nf90_get_att(ncid, NF90_GLOBAL, 'manifest_version', version)
        if (att_stat /= NF90_NOERR) then
            att_stat = nf90_get_att(ncid, NF90_GLOBAL, 'dataset_version', version)
            if (att_stat /= NF90_NOERR) version = 'NONE'
        end if
        att_stat = nf90_get_att(ncid, NF90_GLOBAL, 'source_manifest_checksum', checksum)
        if (att_stat /= NF90_NOERR) checksum = 'NONE'
        call prov_set_seaice('netcdf', seaice_path, trim(version), trim(checksum))

        allocate (buf(is1, js1, ngr))
        stat = nf90_inq_varid(ncid, 'sic', varid)
        if (stat /= NF90_NOERR) call fatal("missing variable 'sic'")
        stat = nf90_get_var(ncid, varid, buf)
        if (stat /= NF90_NOERR) call fatal("cannot read 'sic'")

        an1(:, :, 2:ngr + 1) = buf
        deallocate (buf)

        stat = nf90_close(ncid)
        if (stat /= NF90_NOERR) call fatal('cannot close '//trim(seaice_path))

        print *, 'STAGE117E_NETCDF_SEAICE: read sic from ', trim(seaice_path)
    end subroutine s117e_read_seaice

    subroutine check_dim(ncid, name, expected)
        integer, intent(in) :: ncid, expected
        character(len=*), intent(in) :: name
        integer :: dimid, length, stat

        stat = nf90_inq_dimid(ncid, name, dimid)
        if (stat /= NF90_NOERR) call fatal("missing dimension '"//trim(name)//"'")
        stat = nf90_inquire_dimension(ncid, dimid, len=length)
        if (stat /= NF90_NOERR) call fatal("cannot read dimension '"//trim(name)//"'")
        if (length /= expected) then
            print *, 'FATAL: netcdf_seaice_reader: dimension ', trim(name), &
                ' = ', length, ', expected ', expected
            error stop 1
        end if
    end subroutine check_dim

    subroutine fatal(message)
        character(len=*), intent(in) :: message
        print *, 'FATAL: netcdf_seaice_reader: ', trim(message)
        error stop 1
    end subroutine fatal

end module netcdf_seaice_reader
