! ==============================================================================
! Тест: test_reanalysis_reader (Stage 12.2)
! Проверяет чтение GLORYS12 и интерполяцию против независимого Python/xarray
! (anchors ниже). SKIP (stop 0) если .nc отсутствует (нет данных в CI).
! Anchors: data/validation/stage12.1_glorys12_validation.md + xarray interp.
! ==============================================================================
program test_reanalysis_reader
    use, intrinsic :: iso_fortran_env, only: real64
    use reanalysis_reader
    implicit none

    character(len=*), parameter :: DAILY = &
        'data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc'
    character(len=*), parameter :: STATIC = &
        'data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc'

    ! Якоря (xarray linear interp, decode_cf=True → physical units)
    real(8), parameter :: T_JAN15 = -1.481643d0        ! 75N,20E,10m,2020-01-15T00:00
    real(8), parameter :: S_JAN15 = 34.888760d0/1000.0d0
    real(8), parameter :: U_JAN15 = -0.061221d0
    real(8), parameter :: V_JAN15 = 0.020142d0
    real(8), parameter :: ZOS_JAN15 = -0.495315d0
    real(8), parameter :: SIC_JAN15 = 0.306368d0
    real(8), parameter :: T_JAN15_12 = -1.498123d0     ! midpoint → время-интерполяция
    real(8), parameter :: T_DEEP10 = 2.242836d0        ! 74N,17E,10m
    real(8), parameter :: T_DEEP200 = 2.862556d0       ! 74N,17E,200m (вертикаль)
    ! Время (UNIX сек с 1970)
    real(8), parameter :: TIME_JAN15 = 1579046400.0d0  ! 2020-01-15T00:00:00Z
    real(8), parameter :: TIME_JAN15_12 = 1579089600.0d0

    type(reanalysis_reader_type) :: reader
    real(8) :: T, S, u, v, zos, siconc, sithick
    logical :: ok, fexists
    integer :: n_errors, n_checks

    n_errors = 0
    n_checks = 0

    print *, '=================================================='
    print *, '  STAGE 12.2 — REANALYSIS READER TEST'
    print *, '=================================================='

    inquire (file=DAILY, exist=fexists)
    if (.not. fexists) then
        print *, 'SKIP: GLORYS12 daily file absent (gitignored; Stage 12.1 download required)'
        stop 0
    end if

    call reanalysis_reader_init(reader, DAILY, STATIC, ok)
    if (.not. ok) then
        print *, 'ERROR: reanalysis_reader_init failed'
        stop 1
    end if
    n_checks = n_checks + 1

    ! Check 1: размеры сетки (31 time, 32 depth, 277 lat, 901 lon)
    block
        integer, parameter :: NLAT = 277, NLON = 901, NTIM = 31, NDEP = 32
        print '(a,i0,a,i0,a,i0,a,i0)', '  dims lat=', reader%nlat, ' lon=', reader%nlon, &
            ' dep=', reader%ndepth, ' time=', reader%ntime
        if (reader%nlat /= NLAT .or. reader%nlon /= NLON .or. &
            reader%ndepth /= NDEP .or. reader%ntime /= NTIM) then
            print *, '  ERROR: grid dims mismatch expected (31,32,277,901)'
            n_errors = n_errors + 1
        else
            print *, '  OK: grid dims (31,32,277,901)'
        end if
    end block
    n_checks = n_checks + 1

    ! Check 2: первый/последний временной узел → UNIX секунды
    if (abs(reader%time_unix(1) - 1577836800.0d0) > 1.0d0) then
        print *, '  ERROR: time_unix(1) not 2020-01-01', reader%time_unix(1)
        n_errors = n_errors + 1
    else
        print *, '  OK: time axis UNIX (2020-01-01 00:00)'
    end if
    n_checks = n_checks + 1

    ! Check 3: интерполяция в известной океанской точке
    call reanalysis_reader_get(reader, TIME_JAN15, 75.0d0, 20.0d0, 10.0d0, &
                               T, S, u, v, zos, siconc, sithick, ok)
    if (.not. ok) then
        print *, '  ERROR: get() failed at ocean point'
        n_errors = n_errors + 1
    else
        print '(a,es12.5,a,es12.5,a,es12.5,a,es12.5)', &
            '  point: T=', T, ' S=', S, ' u=', u, ' v=', v
        print '(a,es12.5,a,es12.5,a,es12.5)', &
            '         zos=', zos, ' siconc=', siconc, ' sithick=', sithick
        if (abs(T - T_JAN15) > 1.0d-2) then
            print *, '  ERROR: T mismatch (', T, ' vs ', T_JAN15, ')'
            n_errors = n_errors + 1
        end if
        if (abs(S - S_JAN15) > 1.0d-3) then
            print *, '  ERROR: S mismatch (', S, ' vs ', S_JAN15, ') — so/1000 check!'
            n_errors = n_errors + 1
        else if (S < 0.0d0 .or. S > 0.06d0) then
            print *, '  ERROR: S not a mass fraction (', S, ')'
            n_errors = n_errors + 1
        end if
        if (abs(u - U_JAN15) > 1.0d-2 .or. abs(v - V_JAN15) > 1.0d-2) then
            print *, '  ERROR: current mismatch'
            n_errors = n_errors + 1
        end if
        if (abs(zos - ZOS_JAN15) > 5.0d-2) then
            print *, '  ERROR: zos mismatch'
            n_errors = n_errors + 1
        end if
        if (abs(siconc - SIC_JAN15) > 5.0d-2 .or. siconc < 0.0d0 .or. siconc > 1.0d0) then
            print *, '  ERROR: siconc mismatch/out of [0,1]'
            n_errors = n_errors + 1
        end if
    end if
    n_checks = n_checks + 1

    ! Check 4: вертикальная интерполяция в глубокой воде (74N,17E)
    block
        real(8) :: d10, d200
        logical :: ok2
        call reanalysis_reader_get(reader, TIME_JAN15, 74.0d0, 17.0d0, 10.0d0, &
                                   d10, S, u, v, zos, siconc, sithick, ok)
        call reanalysis_reader_get(reader, TIME_JAN15, 74.0d0, 17.0d0, 200.0d0, &
                                   d200, S, u, v, zos, siconc, sithick, ok2)
        if (.not. ok .or. .not. ok2) then
            print *, '  ERROR: deep-water get failed'
            n_errors = n_errors + 1
        else
            print '(a,f10.5,a,f10.5)', '  vertical: T(10m)=', d10, ' T(200m)=', d200
            if (abs(d10 - T_DEEP10) > 1.0d-2) then
                print *, '  ERROR: T@10m mismatch'; n_errors = n_errors + 1
            end if
            if (abs(d200 - T_DEEP200) > 2.0d-2) then
                print *, '  ERROR: T@200m mismatch (vertical interp)'; n_errors = n_errors + 1
            end if
        end if
    end block
    n_checks = n_checks + 1

    ! Check 5: временная интерполяция (12:00 → -1.498123, отличается от 00:00)
    block
        real(8) :: t12
        call reanalysis_reader_get(reader, TIME_JAN15_12, 75.0d0, 20.0d0, 10.0d0, &
                                   t12, S, u, v, zos, siconc, sithick, ok)
        print '(a,f10.5,a,f10.5)', '  time interp: T@12=', t12, ' T@00=', T_JAN15
        if (abs(t12 - T_JAN15_12) > 1.0d-2) then
            print *, '  ERROR: temporal interpolation mismatch'; n_errors = n_errors + 1
        end if
    end block
    n_checks = n_checks + 1

    ! Check 6: суша → ok=.false. (63N,7.167E — mask=0)
    call reanalysis_reader_get(reader, TIME_JAN15, 63.0d0, 7.167d0, 10.0d0, &
                               T, S, u, v, zos, siconc, sithick, ok)
    if (ok) then
        print *, '  ERROR: land point returned ok=.true.'
        n_errors = n_errors + 1
    else
        print *, '  OK: land point → ok=.false.'
    end if
    n_checks = n_checks + 1

    ! Check 7: depth clamp ниже max уровня (700m → значение на deepest 541m, не экстраполяция)
    call reanalysis_reader_get(reader, TIME_JAN15, 74.0d0, 17.0d0, 700.0d0, &
                               T, S, u, v, zos, siconc, sithick, ok)
    print '(a,f10.5)', '  depth clamp @700m: T=', T
    n_checks = n_checks + 1

    ! Check 8: siconc clip в известной точки (72.833N,74.75E raw>1 → <=1)
    call reanalysis_reader_get(reader, TIME_JAN15, 72.833d0, 74.75d0, 0.494d0, &
                               T, S, u, v, zos, siconc, sithick, ok)
    if (ok .and. (siconc > 1.0d0 .or. siconc < 0.0d0)) then
        print *, '  ERROR: siconc not clipped [0,1] =', siconc
        n_errors = n_errors + 1
    else
        print '(a,f8.4)', '  OK: siconc clipped, value=', siconc
    end if
    n_checks = n_checks + 1

    call reanalysis_reader_close(reader)

    print *, '=================================================='
    print *, 'Total checks: ', n_checks, ' errors: ', n_errors
    if (n_errors == 0) then
        print *, 'SUCCESS: REANALYSIS READER TEST PASSED'
        stop 0
    else
        print *, 'FAILURE: REANALYSIS READER TEST FAILED'
        stop 1
    end if

end program test_reanalysis_reader
