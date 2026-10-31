! ==============================================================================
! Тест: test_wave_erosion (Stage 12.6b, D-58) — CI-safe, синтетика, без .nc.
! Проверяет: Douglas sea state, формулу Bigg (NEMO-совместимую), gating
! волновой эрозии, потерю массы/геометрию L,W и Stokes drift в водной силе.
!
! ВАЖНО: в ТЗ Stage 12.6b Test-2 знаки [1+cos(pi c^3)] были перепутаны
! (c=0 -> 1, c=1 -> 2). NEMO release-4.0 icbthm.F90 даёт обратное:
! c=0 -> фактор 2 (открытая вода), c=1 -> 0 (сплошной лёд). Здесь проверяется
! физически верный/NEMO-вариант; это задокументированное исправление.
! ==============================================================================
program test_wave_erosion
    use iceberg_types, only: iceberg_state, iceberg_diagnostics, ocean_profile, &
                             atmos_forcing, RHO_ICE
    use iceberg, only: iceberg_init
    use iceberg_thermodynamics, only: iceberg_thermodynamics_step
    use iceberg_dynamics, only: compute_water_force
    use wave_forcing, only: hs_to_sea_state, bigg_wave_melt, &
                            wave_forcing_set_constant, wave_forcing_clear_constant, &
                            wave_forcing_set_erosion_enabled, wave_forcing_set_stokes_enabled
    implicit none

    integer :: nerr

    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.6b — WAVE EROSION / STOKES TESTS'
    print *, '===================================================='

    call test_douglas()
    call test_bigg()
    call test_erosion_gate_off()
    call test_erosion_on()
    call test_stokes()

    call wave_forcing_set_erosion_enabled(.false.)
    call wave_forcing_set_stokes_enabled(.false.)
    call wave_forcing_clear_constant()

    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: WAVE EROSION / STOKES TESTS PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: WAVE EROSION / STOKES TESTS FAILED, errors=', nerr
        stop 1
    end if

contains

    subroutine test_douglas()
        integer :: s
        integer, parameter :: hs_in(9) = (/0, 1, 2, 3, 4, 5, 6, 7, 8/)
        real(8), parameter :: hs(9) = (/0.05d0, 0.3d0, 1.0d0, 2.0d0, 3.0d0, &
                                        5.0d0, 8.0d0, 10.0d0, 20.0d0/)
        integer :: i
        print *, ' T1: Douglas sea state from Hs'
        do i = 1, 9
            s = hs_to_sea_state(hs(i))
            if (s /= hs_in(i)) then
                print '(a,f6.2,a,i0,a,i0)', '  FAIL Hs=', hs(i), ' got ', s, ' expected ', hs_in(i)
                nerr = nerr + 1
            end if
        end do
        if (nerr == 0) print *, '  OK: 9 Douglas bins'
    end subroutine test_douglas

    subroutine test_bigg()
        real(8), parameter :: m0 = 2.0d0/86400.0d0   ! Ss=3, T=2, c=0
        real(8) :: m, m_half
        print *, ' T2: Bigg 1997 / NEMO formula'
        m = bigg_wave_melt(3.0d0, 0.0d0, 2.0d0)
        if (abs(m - m0) > 1.0d-12) then
            print '(a,es15.6,a,es15.6)', '  FAIL c=0 m=', m, ' expected ', m0
            nerr = nerr + 1
        end if
        ! c=1: (1+cos(pi)) = 0 -> zero erosion under full cover
        m = bigg_wave_melt(3.0d0, 1.0d0, 2.0d0)
        if (abs(m) > 1.0d-15) then
            print '(a,es15.6)', '  FAIL c=1 m=', m
            nerr = nerr + 1
        end if
        ! c=0.5: factor 1+cos(pi/8) = 1.9238795325
        m_half = bigg_wave_melt(3.0d0, 0.5d0, 2.0d0)
        if (abs(m_half - 1.9238795325d0/86400.0d0) > 1.0d-12) then
            print '(a,es15.6)', '  FAIL c=0.5 m=', m_half
            nerr = nerr + 1
        end if
        ! T=-10: (T+2)<0 -> max(...,0) = 0
        m = bigg_wave_melt(3.0d0, 0.0d0, -10.0d0)
        if (abs(m) > 1.0d-15) then
            print '(a,es15.6)', '  FAIL T=-10 m=', m
            nerr = nerr + 1
        end if
        if (nerr == 0) print *, '  OK: c=0 max, c=1 zero, c=0.5 analytic, T<0 zero'
    end subroutine test_bigg

    subroutine make_profile(prof)
        type(ocean_profile), intent(out) :: prof
        allocate (prof%z(1), prof%dz(1), prof%temp(1), prof%salt(1), &
                  prof%u(1), prof%v(1), prof%u_rel(1))
        prof%nlevels = 1
        prof%z(1) = 0.0; prof%dz(1) = 10.0
        prof%temp(1) = 2.0; prof%salt(1) = 0.035
        prof%u(1) = 0.0; prof%v(1) = 0.0; prof%u_rel(1) = 0.0
        prof%siconc = 0.0
    end subroutine make_profile

    subroutine make_atmos(atmos)
        type(atmos_forcing), intent(out) :: atmos
        atmos%u10 = 0.0; atmos%v10 = 0.0
        atmos%t2m = 253.15; atmos%d2m = 253.15
        atmos%tcc = 0.5; atmos%msl = 101325.0; atmos%snowfall = 0.0
    end subroutine make_atmos

    subroutine test_erosion_gate_off()
        type(iceberg_state) :: st
        type(iceberg_diagnostics) :: diag
        type(ocean_profile) :: prof
        type(atmos_forcing) :: atmos
        real(8) :: l0
        print *, ' T3: wave erosion default OFF -> L/W unchanged'
        call wave_forcing_set_constant(2.0d0, 8.0d0, 0.0d0, 0.0d0, 0.0d0)
        call wave_forcing_set_erosion_enabled(.false.)
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 74.0, 17.0)
        st%T_ice = -10.0d0
        call make_profile(prof); call make_atmos(atmos)
        l0 = st%L
        call iceberg_thermodynamics_step(st, 3600.0, prof, atmos, diag)
        if (abs(st%L - l0) > 1.0d-10 .or. abs(st%W - 100.0d0) > 1.0d-10) then
            print '(a,f12.6,a,f12.6)', '  FAIL L/W changed with gate OFF: ', st%L, ' / ', st%W
            nerr = nerr + 1
        end if
        if (abs(diag%m_wave) > 1.0d-15 .or. diag%wave_mass_loss /= 0.0) then
            print *, '  FAIL wave diagnostics nonzero with gate OFF'
            nerr = nerr + 1
        end if
        if (nerr == 0) print *, '  OK: L/W and wave diag inert when OFF'
    end subroutine test_erosion_gate_off

    subroutine test_erosion_on()
        type(iceberg_state) :: st
        type(iceberg_diagnostics) :: diag
        type(ocean_profile) :: prof
        type(atmos_forcing) :: atmos
        real(8), parameter :: mw = 2.0d0/86400.0d0, dt = 3600.0d0
        real(8) :: expect, expect_mass
        print *, ' T4: wave erosion ON (Hs=2 -> Ss=3, T=2, c=0)'
        call wave_forcing_set_constant(2.0d0, 8.0d0, 0.0d0, 0.0d0, 0.0d0)
        call wave_forcing_set_erosion_enabled(.true.)
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 74.0, 17.0)
        st%T_ice = -10.0d0
        call make_profile(prof); call make_atmos(atmos)
        call iceberg_thermodynamics_step(st, real(dt, 4), prof, atmos, diag)

        expect = 100.0d0 - mw*dt
        if (abs(st%L - expect) > 1.0d-6 .or. abs(st%W - expect) > 1.0d-6) then
            print '(a,f12.6,a,f12.6,a,f12.6)', '  FAIL L/W=', st%L, '/', st%W, ' expected ', expect
            nerr = nerr + 1
        end if
        if (abs(real(diag%m_wave, 8) - mw) > 1.0d-10) then
            print '(a,es15.6,a,es15.6)', '  FAIL m_wave=', real(diag%m_wave, 8), ' expected ', mw
            nerr = nerr + 1
        end if
        expect_mass = real(RHO_ICE, 8)*(100.0d0**2 - expect**2)*100.0d0
        if (abs(real(diag%wave_mass_loss, 8) - expect_mass) > 1.0d-3*expect_mass) then
            print '(a,es15.6,a,es15.6)', '  FAIL wave_mass_loss=', real(diag%wave_mass_loss, 8), &
                ' expected ', expect_mass
            nerr = nerr + 1
        end if
        if (diag%wave_mass_loss <= 0.0) then
            print *, '  FAIL wave_mass_loss not positive'
            nerr = nerr + 1
        end if
        if (nerr == 0) print *, '  OK: L/W recession, m_wave, wave mass loss'
    end subroutine test_erosion_on

    subroutine test_stokes()
        type(iceberg_state) :: st
        type(ocean_profile) :: prof
        real :: fx, fy
        print *, ' T5: Stokes drift in water drag (gated)'
        call wave_forcing_set_constant(0.0d0, 0.0d0, 0.0d0, 0.05d0, 0.0d0)
        call wave_forcing_set_stokes_enabled(.false.)
        call iceberg_init(st, 0.0, 0.0, 100.0, 100.0, 100.0, 74.0, 17.0)
        call make_profile(prof)
        call compute_water_force(st, prof, fx, fy)
        if (abs(fx) > 1.0d-12 .or. abs(fy) > 1.0d-12) then
            print '(a,es12.3,a,es12.3)', '  FAIL Stokes OFF force=', fx, '/', fy
            nerr = nerr + 1
        end if
        call wave_forcing_set_stokes_enabled(.true.)
        call compute_water_force(st, prof, fx, fy)
        if (fx <= 0.0 .or. abs(fy) > 1.0d-6) then
            print '(a,es12.3,a,es12.3)', '  FAIL Stokes ON force=', fx, '/', fy
            nerr = nerr + 1
        end if
        if (nerr == 0) print *, '  OK: Stokes OFF zero, ON positive x-force'
    end subroutine test_stokes

end program test_wave_erosion
