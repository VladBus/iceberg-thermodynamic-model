! ==============================================================================
! Модуль: provenance
! Назначение: Единый источник правды о профайлинге инициализации.
! Физика: Записывает ФАКТИЧЕСКОЕ состояние инициализации океана,
!         а не перечитывает переменные окружения.
! ==============================================================================
module provenance
    implicit none
    private
    public :: prov_set_initialization, prov_get_initialization
    public :: prov_initialization_source, prov_initialization_file
    public :: prov_initialization_attempted_file
    public :: prov_initialization_mode_actual
    public :: get_prov_initialization_source
    public :: get_prov_initialization_file
    public :: get_prov_initialization_attempted_file
    public :: get_prov_initialization_mode_actual
    ! Sea-ice provenance (Stage 11.7E.4.1)
    public :: prov_set_seaice
    public :: get_prov_seaice_reader_mode
    public :: get_prov_seaice_source_file
    public :: get_prov_seaice_manifest_version
    public :: get_prov_seaice_manifest_checksum

    ! Состояние инициализации (устанавливается в init_ocean)
    character(len=16), save :: prov_initialization_source = 'UNSET'
    character(len=512), save :: prov_initialization_file = 'NONE'
    character(len=512), save :: prov_initialization_attempted_file = 'NONE'
    character(len=32), save :: prov_initialization_mode_actual = 'UNSET'
    ! Sea-ice provenance (Stage 11.7E.4.1)
    character(len=16), save :: prov_seaice_reader_mode = 'UNSET'
    character(len=512), save :: prov_seaice_source_file = 'NONE'
    character(len=64), save :: prov_seaice_manifest_version = 'UNSET'
    character(len=128), save :: prov_seaice_manifest_checksum = 'UNSET'

contains

    subroutine prov_set_initialization(source, actual_file, attempted_file, mode_actual)
        character(len=*), intent(in) :: source
        character(len=*), intent(in) :: actual_file
        character(len=*), intent(in) :: attempted_file
        character(len=*), intent(in) :: mode_actual
        prov_initialization_source = source
        prov_initialization_file = actual_file
        prov_initialization_attempted_file = attempted_file
        prov_initialization_mode_actual = mode_actual
    end subroutine prov_set_initialization

    subroutine prov_get_initialization(source, actual_file, attempted_file, mode_actual)
        character(len=*), intent(out) :: source
        character(len=*), intent(out) :: actual_file
        character(len=*), intent(out) :: attempted_file
        character(len=*), intent(out) :: mode_actual
        source = prov_initialization_source
        actual_file = prov_initialization_file
        attempted_file = prov_initialization_attempted_file
        mode_actual = prov_initialization_mode_actual
    end subroutine prov_get_initialization

    ! Геттеры для прямого использования в netcdf_output
    pure function get_prov_initialization_source() result(res)
        character(len=16) :: res
        res = prov_initialization_source
    end function get_prov_initialization_source

    pure function get_prov_initialization_file() result(res)
        character(len=512) :: res
        res = prov_initialization_file
    end function get_prov_initialization_file

    pure function get_prov_initialization_attempted_file() result(res)
        character(len=512) :: res
        res = prov_initialization_attempted_file
    end function get_prov_initialization_attempted_file

    pure function get_prov_initialization_mode_actual() result(res)
        character(len=32) :: res
        res = prov_initialization_mode_actual
    end function get_prov_initialization_mode_actual

    ! Sea-ice provenance setters/getters (Stage 11.7E.4.1)
    subroutine prov_set_seaice(reader_mode, source_file, manifest_version, manifest_checksum)
        character(len=*), intent(in) :: reader_mode
        character(len=*), intent(in) :: source_file
        character(len=*), intent(in) :: manifest_version
        character(len=*), intent(in) :: manifest_checksum
        prov_seaice_reader_mode = reader_mode
        prov_seaice_source_file = source_file
        prov_seaice_manifest_version = manifest_version
        prov_seaice_manifest_checksum = manifest_checksum
    end subroutine prov_set_seaice

    pure function get_prov_seaice_reader_mode() result(res)
        character(len=16) :: res
        res = prov_seaice_reader_mode
    end function get_prov_seaice_reader_mode

    pure function get_prov_seaice_source_file() result(res)
        character(len=512) :: res
        res = prov_seaice_source_file
    end function get_prov_seaice_source_file

    pure function get_prov_seaice_manifest_version() result(res)
        character(len=64) :: res
        res = prov_seaice_manifest_version
    end function get_prov_seaice_manifest_version

    pure function get_prov_seaice_manifest_checksum() result(res)
        character(len=128) :: res
        res = prov_seaice_manifest_checksum
    end function get_prov_seaice_manifest_checksum

end module provenance