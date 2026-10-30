! ==============================================================================
! Модуль: ocean_provider (Stage 12.2)
! Назначение: Абстрактный интерфейс источника океанского состояния для
!             форсинга айсберга. Прячет разницу между GLORYS12-реанализом
!             (offline/prescribed) и прогностическим океаном Stage 11.
!             Односторонняя связь: океан НЕ чувствует айсберг (D-51).
!
! source_type:  1 = reanalysis (reader активен)
!               2 = model      (прогностический океан Stage 11; provider НЕ
!                               используется — legacy-код читает t2/s2/u2/v2
!                               напрямую; get возвращает ok=.false. как сигнал)
! ==============================================================================
module ocean_provider
    use reanalysis_reader
    implicit none

    private
    public :: ocean_provider_type, ocean_provider_init
    public :: ocean_provider_get, ocean_provider_close
    public :: SRC_REANALYSIS, SRC_MODEL

    integer, parameter :: SRC_REANALYSIS = 1
    integer, parameter :: SRC_MODEL = 2

    type :: ocean_provider_type
        integer :: source_type = SRC_MODEL   ! 1=reanalysis, 2=model
        type(reanalysis_reader_type) :: reader
        logical :: ready = .false.
    end type ocean_provider_type

contains

    subroutine ocean_provider_init(provider, source_type, reanalysis_path, static_path)
        type(ocean_provider_type), intent(out) :: provider
        integer, intent(in) :: source_type
        character(len=*), intent(in), optional :: reanalysis_path, static_path

        character(len=*), parameter :: DEF_DAILY = &
            'data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc'
        character(len=*), parameter :: DEF_STATIC = &
            'data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc'
        character(len=512) :: dpath, spath
        logical :: ok

        provider%source_type = source_type
        provider%ready = .false.

        if (source_type == SRC_REANALYSIS) then
            dpath = DEF_DAILY
            spath = DEF_STATIC
            if (present(reanalysis_path)) then
                if (len_trim(reanalysis_path) > 0) dpath = reanalysis_path
            end if
            if (present(static_path)) then
                if (len_trim(static_path) > 0) spath = static_path
            end if
            call reanalysis_reader_init(provider%reader, trim(dpath), trim(spath), ok)
            provider%ready = ok
            if (.not. ok) then
                print *, 'ocean_provider: reanalysis init FAILED (no data?)'
            end if
        else if (source_type == SRC_MODEL) then
            ! Legacy-путь: provider не используется; get вернёт ok=.false.
            provider%ready = .true.
        else
            provider%source_type = SRC_MODEL
            provider%ready = .false.
        end if
    end subroutine ocean_provider_init

    subroutine ocean_provider_get(provider, time, lat, lon, depth, &
                                  T, S, u, v, zos, siconc, sithick, ok)
        type(ocean_provider_type), intent(inout) :: provider
        real(8), intent(in) :: time, lat, lon, depth
        real(8), intent(out) :: T, S, u, v, zos, siconc, sithick
        logical, intent(out) :: ok

        T = 0.0_8; S = 0.0_8; u = 0.0_8; v = 0.0_8
        zos = 0.0_8; siconc = 0.0_8; sithick = 0.0_8
        ok = .false.

        if (provider%source_type == SRC_REANALYSIS) then
            if (.not. provider%ready) return
            call reanalysis_reader_get(provider%reader, time, lat, lon, depth, &
                                       T, S, u, v, zos, siconc, sithick, ok)
        else
            ! SRC_MODEL: прогностический океан читается legacy-кодом напрямую;
            ! через provider значения НЕ предоставляются.
            ok = .false.
        end if
    end subroutine ocean_provider_get

    subroutine ocean_provider_close(provider)
        type(ocean_provider_type), intent(inout) :: provider
        if (provider%source_type == SRC_REANALYSIS) then
            call reanalysis_reader_close(provider%reader)
        end if
        provider%ready = .false.
    end subroutine ocean_provider_close

end module ocean_provider
