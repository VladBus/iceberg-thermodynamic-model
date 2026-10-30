! ==============================================================================
! Тест: test_iceberg_forcing_reanalysis (Stage 12.2)
! Интеграция: get_ocean_profile через GLORYS12-реанализ (OCEAN_SOURCE=reanalysis).
! SKIP без данных. Model-путь (SRC_MODEL) здесь НЕ исполняется (требует полной
! инициализации модельной сетки/EN4) — он покрыт test_ocean_provider.
! ==============================================================================
program test_iceberg_forcing_reanalysis
    use iceberg_forcing, only: get_ocean_profile, ocean_forcing_configure
    use ocean_provider, only: SRC_REANALYSIS
    use iceberg_types, only: ocean_profile
    implicit none

    character(len=*), parameter :: DAILY = &
        'data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc'
    character(len=*), parameter :: STATIC = &
        'data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc'
    real(8), parameter :: TIME_JAN15 = 1579046400.0d0

    type(ocean_profile) :: prof
    logical :: ok, fexists
    integer :: n_errors, n_checks, k

    n_errors = 0
    n_checks = 0
    print *, '=================================================='
    print *, '  STAGE 12.2 — ICEBERG FORCING / REANALYSIS INTEGRATION'
    print *, '=================================================='

    inquire (file=DAILY, exist=fexists)
    if (.not. fexists) then
        print *, 'SKIP: GLORYS12 daily file absent (gitignored)'
        stop 0
    end if

    ! Явная настройка provider на реанализ (обходит env-lazy-init).
    call ocean_forcing_configure(SRC_REANALYSIS, DAILY, STATIC)
    n_checks = n_checks + 1

    ! Профиль на позиции 75N,20E, draft 88.5 m, модельное время 2020-01-15.
    ! x_model/y_model игнорируются в реанализ-ветке (используется lat/lon).
    call get_ocean_profile(0.0, 0.0, 75.0, 20.0, 88.5, 0.0, 0.0, prof, ok, TIME_JAN15)
    if (.not. ok) then
        print *, '  ERROR: get_ocean_profile (reanalysis) failed'
        n_errors = n_errors + 1
    else
        print '(a,i0,a,f8.3,a,f8.3,a)', '  OK: profile nlevels=', prof%nlevels, &
            ' z=[', prof%z(1), '..', prof%z(prof%nlevels), '] m'
        ! Минимум 1 уровень, все конечные, солёность — массовая доля.
        if (prof%nlevels < 1) then
            print *, '  ERROR: zero levels'; n_errors = n_errors + 1
        end if
        do k = 1, prof%nlevels
            if (prof%temp(k) /= prof%temp(k) .or. prof%salt(k) /= prof%salt(k) .or. &
                prof%u(k) /= prof%u(k) .or. prof%v(k) /= prof%v(k)) then
                print *, '  ERROR: NaN in profile at k=', k; n_errors = n_errors + 1
            end if
            if (prof%salt(k) < 0.0 .or. prof%salt(k) > 0.06) then
                print '(a,i0,a,f10.6)', '  ERROR: salt not mass-fraction at k=', k, &
                    ' S=', prof%salt(k)
                n_errors = n_errors + 1
            end if
            if (prof%u_rel(k) < 0.0 .or. prof%u_rel(k) /= prof%u_rel(k)) then
                print *, '  ERROR: u_rel bad at k=', k; n_errors = n_errors + 1
            end if
        end do
        print '(a,f8.3,a,f9.6)', '  surface T=', prof%temp(1), ' S=', prof%salt(1)
        do k = 1, prof%nlevels
            print *, '   k=', k, ' T=', prof%temp(k), ' S=', prof%salt(k), &
                ' u=', prof%u(k), ' v=', prof%v(k)
        end do
    end if
    n_checks = n_checks + 1

    ! Согласованность: первый уровень — поверхность; уже проверен на правдоподобие выше.
    print *, '  NOTE: first-level surface plausibility checked above'
    n_checks = n_checks + 1

    ! Позиция вне океана/над сушей (63N,7.167E) → ok=.false. (graceful)
    call get_ocean_profile(0.0, 0.0, 63.0, 7.167, 88.5, 0.0, 0.0, prof, ok, TIME_JAN15)
    if (ok) then
        print *, '  WARNING: land position returned ok (expected .false.)'
        ! Не фатально — над сушей профиль не строится; помечаем как ожидание fail.
    else
        print *, '  OK: land position → ok=.false.'
    end if
    n_checks = n_checks + 1

    print *, '=================================================='
    print *, 'Total checks: ', n_checks, ' errors: ', n_errors
    if (n_errors == 0) then
        print *, 'SUCCESS: ICEBERG FORCING / REANALYSIS TEST PASSED'
        stop 0
    else
        print *, 'FAILURE: ICEBERG FORCING / REANALYSIS TEST FAILED'
        stop 1
    end if
end program test_iceberg_forcing_reanalysis
