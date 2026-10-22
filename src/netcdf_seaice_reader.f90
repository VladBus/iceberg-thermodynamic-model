module netcdf_seaice_reader
    use netcdf
    use param, only: is1, js1, ngr, an1
    use provenance, only: prov_set_seaice
    implicit none
    private
    public :: s117e_seaice_init, s117e_seaice_active, s117e_read_seaice

    logical :: active = .false.
    character(len=*), parameter :: seaice_path = &
        'data/input/processed/ice/seaice_initial.nc'

contains

    subroutine s117e_seaice_init()
        character(len=32) :: env
        integer :: length
        character(len=64) :: manifest_version
        character(len=128) :: manifest_checksum
        character(len=16) :: reader_mode
        character(len=512) :: source_file

        call get_environment_variable('STAGE117E_NETCDF_SEAICE', env, &
                                      length=length)
        active = .false.
        if (length > 0) then
            if (trim(env) == '1' .or. trim(env) == 'true' .or. &
                trim(env) == 'TRUE' .or. trim(env) == 'ON') then
                active = .true.
            else if (trim(env) == '0' .or. trim(env) == 'false' .or. &
                     trim(env) == 'FALSE' .or. trim(env) == 'OFF' .or. &
                     trim(env) == 'LEGACY') then
                active = .false.
            else
                print *, 'FATAL: netcdf_seaice_reader: unknown value for STAGE117E_NETCDF_SEAICE: "', trim(env), '"'
                print *, 'Valid values: OFF, 0, FALSE, LEGACY (legacy 1_*.ice files)'
                print *, '              ON, 1, TRUE (NetCDF seaice_initial.nc)'
                error stop 1
            end if
        end if

        if (active) then
            print *, 'STAGE117E_NETCDF_SEAICE: ON (', trim(seaice_path), ')'
        else
            print *, 'STAGE117E_NETCDF_SEAICE: OFF (legacy 1_*.ice)'
        end if

        ! Set sea-ice provenance (Stage 11.8.0.0): ACTUAL source, not hardcoded.
        ! ON: provisional netcdf/path; s117e_read_seaice() replaces the manifest
        !     fields with the values read from the actual NetCDF file.
        ! OFF: legacy text files; no manifest applies.
        if (active) then
            reader_mode = 'netcdf'
            source_file = seaice_path
            manifest_version = 'PENDING'
            manifest_checksum = 'PENDING'
        else
            reader_mode = 'legacy'
            source_file = 'legacy_1_*.ice'
            manifest_version = 'NONE'
            manifest_checksum = 'NONE'
        end if
        call prov_set_seaice(reader_mode, source_file, manifest_version, manifest_checksum)
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
