! ==============================================================================
! test_voxel_air_balance (Stage 12.7b, D-61)
! Autonomous exposed-face energy balance: analytical component sum (<1%) and
! a 1-voxel CN warming/melt sanity check.
! ==============================================================================
program test_voxel_air_balance
    use iceberg_types, only: ALBEDO_ICE, EMISSIVITY, STEFAN_BOLTZ, CP_AIR, &
                             L_S, C_H_NEUTRAL, C_E_NEUTRAL
    use voxel_thermal_solver, only: voxel_air_flux_components, solve_cn
    implicit none

    integer :: nerr
    nerr = 0
    print *, '===================================================='
    print *, ' STAGE 12.7b — AUTONOMOUS AIR BALANCE'
    print *, '===================================================='
    call test_components()
    call test_cn_warming()
    print *, '===================================================='
    if (nerr == 0) then
        print *, 'SUCCESS: AUTONOMOUS AIR BALANCE PASSED'
        stop 0
    else
        print '(a,i0)', 'FAILURE: errors=', nerr
        stop 1
    end if

contains

    real(8) function qsat_ice(tk, p) result(q)
        real(8), intent(in) :: tk, p
        real(8) :: es
        es = 610.78_8*exp(21.875_8*(tk - 273.15_8)/(tk - 7.66_8))
        q = 0.622_8*es/max(p, 1.0_8)
    end function qsat_ice

    subroutine test_components()
        real(8) :: ts, ta, wind, sw, lw, qa, rho, p
        real(8) :: swa, lwn, sh, lh, dlw, dsh, dlh, qs
        real(8) :: e_sw, e_lw, e_sh, e_lh, total, expected
        ts = -10.0_8; ta = 273.15_8; wind = 5.0_8
        sw = 200.0_8; lw = 300.0_8; qa = 0.003_8; rho = 1.3_8; p = 101325.0_8
        call voxel_air_flux_components(ts, ta, wind, sw, lw, qa, rho, p, 1.0_8, &
                                       swa, lwn, sh, lh, dlw, dsh, dlh, qs)
        e_sw = (1.0_8 - real(ALBEDO_ICE, 8))*sw
        e_lw = real(EMISSIVITY, 8)*real(STEFAN_BOLTZ, 8)*(ta**4 - (ts + 273.15_8)**4) + &
               (1.0_8 - real(EMISSIVITY, 8))*lw
        e_sh = rho*real(CP_AIR, 8)*real(C_H_NEUTRAL, 8)*wind*(ta - (ts + 273.15_8))
        e_lh = rho*real(L_S, 8)*real(C_E_NEUTRAL, 8)*wind*(qa - qsat_ice(ts + 273.15_8, p))
        total = swa + lwn + sh + lh
        expected = e_sw + e_lw + e_sh + e_lh
        print '(a,5(1x,es13.5))', ' Q components=', swa, lwn, sh, lh, total
        print '(a,es13.5)', ' Q expected =', expected
        if (abs(total - expected) > 1.0d-6*max(abs(expected), 1.0d0)) then
            print *, ' FAIL: component sum differs from analytical'; nerr = nerr + 1
        end if
        if (abs(swa - e_sw) > 1.0d-9 .or. abs(lwn - e_lw) > 1.0d-9) then
            print *, ' FAIL: SW/LW mismatch'; nerr = nerr + 1
        end if
        if (abs(sh - e_sh) > 1.0d-9 .or. abs(lh - e_lh) > 1.0d-9) then
            print *, ' FAIL: SH/LH mismatch'; nerr = nerr + 1
        end if
    end subroutine test_components

    subroutine test_cn_warming()
        real(8) :: T(1,1,1), phi(1,1,1), Tn(1,1,1)
        logical :: sub(1,1,1), expo(1,1,1), conv
        integer :: it
        real(8) :: res
        T = -10.0_8; phi = 1.0_8
        sub = .false.; expo = .true.
        call solve_cn(T, phi, 10.0_8, 10.0_8, 10.0_8, 3600.0_8, &
                      2.2_8, 916.7_8, 2100.0_8, 0.5_8, 1.0d-10, 100, 0.0_8, &
                      0.0_8, 0.035_8, 0.0_8, 0.0_8, 0.0_8, 0.0_8, 5.0_8, &
                      sub, expo, Tn, it, res, conv, &
                      autonomous_air=.true., air_sw_down=200.0_8, &
                      air_lw_down=300.0_8, air_t_air=273.15_8, air_q_air=0.003_8, &
                      air_rho_air=1.3_8, air_p_atm=101325.0_8)
        print '(a,f10.4,a,l1,a,i0)', ' Tnew=', Tn(1,1,1), ' converged=', conv, ' iters=', it
        if (.not. conv) then
            print *, ' FAIL: CN did not converge'; nerr = nerr + 1
        end if
        if (Tn(1,1,1) <= -10.0_8) then
            print *, ' FAIL: surface did not warm'; nerr = nerr + 1
        end if
    end subroutine test_cn_warming

end program test_voxel_air_balance
