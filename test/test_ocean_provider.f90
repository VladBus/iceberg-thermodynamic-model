! ==============================================================================
! Тест: test_ocean_provider (Stage 12.2)
! source=1 (reanalysis): init/get/close против reader-якорей. SKIP без данных.
! source=2 (model): get обязан вернуть ok=.false. (legacy-код вызывается напрямую).
! ==============================================================================
program test_ocean_provider
    use ocean_provider
    implicit none

    character(len=*), parameter :: DAILY = &
        'data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc'
    character(len=*), parameter :: STATIC = &
        'data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc'

    real(8), parameter :: TIME_JAN15 = 1579046400.0d0
    real(8), parameter :: T_JAN15 = -1.481643d0
    real(8), parameter :: S_JAN15 = 34.888760d0/1000.0d0

    type(ocean_provider_type) :: prov
    real(8) :: T, S, u, v, zos, siconc, sithick
    logical :: ok, fexists
    integer :: n_errors, n_checks

    n_errors = 0
    n_checks = 0
    print *, '=================================================='
    print *, '  STAGE 12.2 — OCEAN PROVIDER TEST'
    print *, '=================================================='

    inquire (file=DAILY, exist=fexists)
    if (.not. fexists) then
        print *, 'SKIP: GLORYS12 daily file absent (gitignored)'
        stop 0
    end if

    ! Check 1: source=2 (model) → get ok=.false. (provider не предоставляет значения)
    call ocean_provider_init(prov, SRC_MODEL)
    if (prov%source_type /= SRC_MODEL) then
        print *, '  ERROR: source_type != SRC_MODEL'; n_errors = n_errors + 1
    end if
    call ocean_provider_get(prov, TIME_JAN15, 75.0d0, 20.0d0, 10.0d0, &
                            T, S, u, v, zos, siconc, sithick, ok)
    if (ok) then
        print *, '  ERROR: model source get() returned ok=.true.'
        n_errors = n_errors + 1
    else
        print *, '  OK: model source get() → ok=.false. (legacy path)'
    end if
    call ocean_provider_close(prov)
    n_checks = n_checks + 1

    ! Check 2: source=1 (reanalysis) init
    call ocean_provider_init(prov, SRC_REANALYSIS, DAILY, STATIC)
    if (.not. prov%ready) then
        print *, '  ERROR: reanalysis provider init failed'
        stop 1
    end if
    n_checks = n_checks + 1

    ! Check 3: get в известной океанской точке
    call ocean_provider_get(prov, TIME_JAN15, 75.0d0, 20.0d0, 10.0d0, &
                            T, S, u, v, zos, siconc, sithick, ok)
    if (.not. ok) then
        print *, '  ERROR: reanalysis get() failed at ocean point'
        n_errors = n_errors + 1
    else if (abs(T - T_JAN15) > 1.0d-2 .or. abs(S - S_JAN15) > 1.0d-3) then
        print '(a,f10.5,a,f10.6)', '  ERROR: provider values off: T=', T, ' S=', S
        n_errors = n_errors + 1
    else
        print '(a,f10.5,a,f10.6)', '  OK: provider T=', T, ' S=', S
    end if
    n_checks = n_checks + 1

    ! Check 4: get над сушей → ok=.false.
    call ocean_provider_get(prov, TIME_JAN15, 63.0d0, 7.167d0, 10.0d0, &
                            T, S, u, v, zos, siconc, sithick, ok)
    if (ok) then
        print *, '  ERROR: land point returned ok'; n_errors = n_errors + 1
    else
        print *, '  OK: land point → ok=.false.'
    end if
    n_checks = n_checks + 1

    call ocean_provider_close(prov)

    print *, '=================================================='
    print *, 'Total checks: ', n_checks, ' errors: ', n_errors
    if (n_errors == 0) then
        print *, 'SUCCESS: OCEAN PROVIDER TEST PASSED'
        stop 0
    else
        print *, 'FAILURE: OCEAN PROVIDER TEST FAILED'
        stop 1
    end if
end program test_ocean_provider
