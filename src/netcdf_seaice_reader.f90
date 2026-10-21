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

        ! Set sea-ice provenance (Stage 11.7E.4.1)
        reader_mode = merge('netcdf', 'legacy', active)
        source_file = seaice_path
        manifest_version = 'from python/ice/seaice_source_manifest.json'
        manifest_checksum = 'md5:python/ice/seaice_source_manifest.json'
        call prov_set_seaice(reader_mode, source_file, manifest_version, manifest_checksum)
    end subroutine s117e_seaice_init

    logical function s117e_seaice_active()
        s117e_seaice_active = active
    end function s117e_seaice_active

    subroutine s117e_read_seaice()
        integer :: ncid, varid, stat
        real(kind=4), allocatable :: buf(:, :, :)

        if (.not. active) return

        stat = nf90_open(trim(seaice_path), NF90_NOWRITE, ncid)
        if (stat /= NF90_NOERR) call fatal('cannot open '//trim(seaice_path))

        call check_dim(ncid, 'i', is1)
        call check_dim(ncid, 'j', js1)
        call check_dim(ncid, 'cat', ngr)

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
