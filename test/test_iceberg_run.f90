! ==============================================================================
! Тест: test_iceberg_run (Stage 12.6a) — CI-safe (без .nc).
! Лаг/лон аналитика, real(8) энергобаланс, lat/lon-режим iceberg_step,
! линейность временного шага, и SKIP для полного reanalysis-прогона.
! ==============================================================================
program test_iceberg_run
    use iceberg, only: iceberg_init, iceberg_step, iceberg_set_latlon_mode, &
                       geographic_increment
    use iceberg_types
    implicit none

    real(8), parameter :: PI = 3.141592653589793d0, R_EARTH = 6371.0d3
    integer :: nerr

    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.6a — LAT/LON + REAL(8) TESTS'
    print *, '===================================================='

    call test_geographic_increment()
    call test_energy_real8()
    call test_latlon_mode()
    call test_time_linearity()
    call test_reanalysis_skip()

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: LAT/LON + REAL(8) TESTS PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: LAT/LON + REAL(8) TESTS FAILED, errors=', nerr
        stop 1
    end if

contains

    ! --- Test 1: analytic dlon for u=0.1 m/s at 75N over 1 day ---------------
    subroutine test_geographic_increment()
        real(8) :: lat, lon, dlat, dlon, expected
        lat = 75.0d0; lon = 30.0d0
        call geographic_increment(lat, lon, 0.1d0, 0.0d0, 86400.0d0, dlat, dlon)
        expected = (0.1d0*86400.0d0/(R_EARTH*cos(lat*PI/180.0d0)))*(180.0d0/PI)
        print '(a,f14.10,a,f14.10)', ' T1 dlon=', dlon, ' expected=', expected
        if (abs(dlon - expected) > 1.0d-12 .or. abs(dlat) > 1.0d-12) then
            print *, '  FAIL: geographic increment mismatch'; nerr = nerr + 1
        else
            print *, '  OK: dlon = u*dt/(R cos lat) (analytic)'
        end if
    end subroutine test_geographic_increment

    ! --- Test 2: real(8) mass/energy conservation (100 steps) ---------------
    subroutine test_energy_real8()
        type(iceberg_state) :: st
        type(iceberg_diagnostics) :: diag
        type(ocean_profile) :: prof
        type(atmos_forcing) :: atmos
        real(8) :: e0, e1, drift, t0, tf, zc
        integer :: i, k
        logical :: ok

        call iceberg_set_latlon_mode(.true.)
        call set_thermal_evolution(.false.)          ! hold T_ice (energy audit)
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 75.0, 30.0, 0.0, 0.0)
        st%T_ice = -10.0d0

        prof%nlevels = 5
        allocate (prof%z(5), prof%dz(5), prof%temp(5), prof%salt(5), prof%u(5), prof%v(5), &
                  prof%u_rel(5))
        prof%z = (/ 1.0, 10.0, 50.0, 100.0, 300.0 /)
        prof%dz = 10.0
        do k = 1, 5
            prof%temp(k) = ocean_freezing_point(0.035, real(prof%z(k)))
        end do
        prof%salt = 0.035
        prof%u = 0.0; prof%v = 0.0; prof%u_rel = 0.0
        atmos%u10 = 0.0; atmos%v10 = 0.0; atmos%t2m = 243.15; atmos%d2m = 243.15
        atmos%tcc = 0.0; atmos%msl = 101325.0; atmos%snowfall = 0.0

        e0 = st%mass*(C_ICE*st%T_ice + LATENT_HEAT)
        do i = 1, 100
            call iceberg_step(st, 600.0, prof, atmos, 800.0, diag=diag)
            if (.not. st%active) exit
        end do
        e1 = st%mass*(C_ICE*st%T_ice + LATENT_HEAT)
        drift = abs(e1 - e0)/abs(e0)
        print '(a,es14.6,a,es14.6)', ' T2 E0=', e0, ' E1=', e1
        print '(a,es12.4)', '    relative drift = ', drift
        if (drift > 1.0d-8) then
            print *, '  FAIL: energy drift > 1e-8'; nerr = nerr + 1
        else
            print *, '  OK: real(8) energy conserved (<1e-8 over 100 steps)'
        end if
        if (storage_size(st%mass) /= 64 .or. storage_size(st%volume) /= 64) then
            print *, '  FAIL: mass/volume not real(8)'; nerr = nerr + 1
        else
            print *, '  OK: state mass/volume are 64-bit'
        end if
        deallocate (prof%z, prof%dz, prof%temp, prof%salt, prof%u, prof%v, prof%u_rel)
    end subroutine test_energy_real8

    ! --- Test 3: latlon mode makes lat/lon primary (x unchanged) ------------
    subroutine test_latlon_mode()
        type(iceberg_state) :: st
        type(iceberg_diagnostics) :: diag
        type(ocean_profile) :: prof
        type(atmos_forcing) :: atmos
        real(8) :: lon0
        integer :: k
        call iceberg_set_latlon_mode(.true.)
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 75.0, 30.0, 0.1, 0.0)
        lon0 = st%longitude
        prof%nlevels = 1
        allocate (prof%z(1), prof%dz(1), prof%temp(1), prof%salt(1), prof%u(1), prof%v(1), &
                  prof%u_rel(1))
        prof%z = 5.0; prof%dz = 10.0; prof%temp = 2.0; prof%salt = 0.035
        prof%u = 0.1; prof%v = 0.0; prof%u_rel = 0.1
        atmos%u10 = 0.0; atmos%v10 = 0.0; atmos%t2m = 253.15; atmos%d2m = 253.15
        atmos%tcc = 0.5; atmos%msl = 101325.0; atmos%snowfall = 0.0
        call iceberg_step(st, 3600.0, prof, atmos, 800.0, diag=diag)
        print '(a,es14.6,a,es14.6)', ' T3 x=', st%x, ' lon0->', st%longitude
        if (abs(st%x) > 1.0d-12) then
            print *, '  FAIL: x changed in latlon mode'; nerr = nerr + 1
        else if (abs(st%longitude - lon0) < 1.0d-12) then
            print *, '  FAIL: longitude did not advance'; nerr = nerr + 1
        else
            print *, '  OK: lat/lon primary, x untouched'
        end if
        deallocate (prof%z, prof%dz, prof%temp, prof%salt, prof%u, prof%v, prof%u_rel)
    end subroutine test_latlon_mode

    ! --- Test 4: temporal linearity (constant u) ---------------------------
    subroutine test_time_linearity()
        real(8) :: d1, d2, lat, lon, a, b
        lat = 75.0d0; lon = 30.0d0
        call geographic_increment(lat, lon, 0.1d0, 0.0d0, 3600.0d0, a, d1)
        call geographic_increment(lat, lon, 0.1d0, 0.0d0, 1800.0d0, b, d2)
        print '(a,f14.10,a,f14.10)', ' T4 dlon(3600)=', d1, ' 2*dlon(1800)=', 2.0d0*d2
        if (abs(d1 - 2.0d0*d2) > 1.0d-13) then
            print *, '  FAIL: time step not linear'; nerr = nerr + 1
        else
            print *, '  OK: position linear in time'
        end if
    end subroutine test_time_linearity

    ! --- Test 5: full reanalysis run requires .nc; SKIP if absent ----------
    subroutine test_reanalysis_skip()
        logical :: ex
        inquire (file='data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc', &
                 exist=ex)
        if (.not. ex) then
            print *, ' T5 SKIP: GLORYS .nc absent (full iceberg_run test requires data)'
        else
            print *, ' T5 NOTE: GLORYS .nc present; full run exercised via iceberg_run'
        end if
    end subroutine test_reanalysis_skip

end program test_iceberg_run
