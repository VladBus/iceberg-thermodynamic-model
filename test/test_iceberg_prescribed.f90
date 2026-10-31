! ==============================================================================
! test_iceberg_prescribed (Stage 12.7a, D-59) — CI-safe synthetic test.
! Prescribed-position step: no drift, thermodynamics + mass budget active.
! ==============================================================================
program test_iceberg_prescribed
    use iceberg_types, only: iceberg_state, iceberg_diagnostics, ocean_profile, &
                             atmos_forcing, RHO_ICE
    use iceberg, only: iceberg_init, iceberg_step_prescribed
    implicit none

    type(iceberg_state) :: st
    type(iceberg_diagnostics) :: diag
    type(ocean_profile) :: prof
    type(atmos_forcing) :: atmos
    integer :: nerr

    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.7a — PRESCRIBED TRAJECTORY STEP'
    print *, '===================================================='

    call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 74.0, 17.0)
    st%T_ice = -10.0d0
    allocate (prof%z(1), prof%dz(1), prof%temp(1), prof%salt(1), &
              prof%u(1), prof%v(1), prof%u_rel(1))
    prof%nlevels = 1
    prof%z(1) = 0.0; prof%dz(1) = 10.0
    prof%temp(1) = 2.0; prof%salt(1) = 0.035
    prof%u(1) = 0.0; prof%v(1) = 0.0; prof%u_rel(1) = 0.0
    prof%siconc = 0.0
    atmos%u10 = 0.0; atmos%v10 = 0.0
    atmos%t2m = 253.15; atmos%d2m = 253.15
    atmos%tcc = 0.5; atmos%msl = 101325.0; atmos%snowfall = 0.0

    call iceberg_step_prescribed(st, 3600.0, prof, atmos, 74.0d0, 17.0d0, diag)

    if (abs(st%latitude - 74.0d0) > 1.0d-12 .or. abs(st%longitude - 17.0d0) > 1.0d-12) then
        print *, ' FAIL: position changed'; nerr = nerr + 1
    end if
    if (abs(st%u) > 1.0d-15 .or. abs(st%v) > 1.0d-15) then
        print *, ' FAIL: velocity not zero'; nerr = nerr + 1
    end if
    if (abs(st%time - 3600.0d0) > 1.0d-9 .or. st%nstep /= 1) then
        print *, ' FAIL: time/nstep not advanced'; nerr = nerr + 1
    end if
    if (st%volume >= 1.0d6) then
        print *, ' FAIL: volume did not decrease'; nerr = nerr + 1
    end if
    print '(a,4(1x,es13.5),1x,f12.2)', ' components B/L/S/V/a=', diag%basal_mass_loss, &
        diag%lateral_mass_loss, diag%surface_mass_loss, diag%vapor_mass_loss, diag%a_wet
    if (diag%total_mass_loss <= 0.0 .or. diag%lateral_mass_loss <= 0.0 .or. diag%a_wet <= 0.0) then
        print *, ' FAIL: mass-budget diagnostics not populated'; nerr = nerr + 1
    end if
    if (.not. st%active) then
        print *, ' FAIL: state unexpectedly inactive'; nerr = nerr + 1
    end if

    print '(a,f12.3,a,es12.4,a,f12.1)', ' volume=', st%volume, ' dM=', &
        diag%total_mass_loss, ' a_wet=', diag%a_wet
    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: PRESCRIBED TRAJECTORY STEP PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: errors=', nerr
        stop 1
    end if
end program test_iceberg_prescribed
