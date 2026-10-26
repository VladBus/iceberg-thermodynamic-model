! T5-CORRECTIVE-4: minimal density repair test.
program test_density_repair
    use param
    use equation_of_state, only: eos_density_f64
    use stage118_density_repair, only: repair_density
    use stage118_physics_switches, only: s118_density_repair
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none
    integer :: i, j, k, unit
    real(real64) :: ro0, ro1
    real :: s0, t0

    s118_density_repair = .true.
    kt1 = 18; kk1 = 18
    t2 = 30.0; s2 = 0.0
    t1 = t2; s1 = s2
    ro0 = eos_density_f64(30.0_real64, 0.0_real64, real(z(1)*0.01, real64))
    t0 = t2(2, 2, 1); s0 = s2(2, 2, 1)
    call repair_density()
    ro1 = eos_density_f64(real(t2(2,2,1),real64), real(s2(2,2,1),real64), real(z(1)*0.01,real64))
    unit = 94
    open (unit, file='data/validation/t5c4_density_repair_test.json', status='replace', action='write')
    write (unit, '(A)') '{'
    write (unit, '(A,ES12.4,A)') '  "ro_before": ', ro0, ','
    write (unit, '(A,ES12.4,A)') '  "ro_after": ', ro1, ','
    write (unit, '(A,ES12.4,A)') '  "t_before": ', t0, ','
    write (unit, '(A,ES12.4,A)') '  "s_before": ', s0, ','
    write (unit, '(A,ES12.4,A)') '  "t_after": ', t2(2,2,1), ','
    write (unit, '(A,ES12.4,A)') '  "s_after": ', s2(2,2,1), ','
    if (ro1 >= 0.0_real64) then
        write (unit, '(A)') '  "status": "PASS"'
    else
        write (unit, '(A)') '  "status": "FAIL"'
    end if
    write (unit, '(A)') '}'
    close (unit)
    print '(A,2ES12.4)', 'RO before/after: ', ro0, ro1
    if (ro1 < 0.0_real64) error stop 1
    print *, 'RESULT: PASS (RO >= 0 after minimal repair)'
end program test_density_repair
