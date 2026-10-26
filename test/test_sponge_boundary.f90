! T5-CORRECTIVE-3: boundary sponge test.
program test_sponge_boundary
    use param
    use stage118_boundary_sponge, only: apply_sponge_boundary
    use stage118_physics_switches, only: s118_sponge_boundary, s118_sponge_alpha
    implicit none
    real :: b_before, b_after, i_before, i_after, dtloc
    integer :: unit

    s118_sponge_boundary = .true.
    s118_sponge_alpha = 1.0
    kt1 = 18; kk1 = 18
    u2 = 0.0; v2 = 0.0; up2 = 0.0; vp2 = 0.0
    u2(2, 2, 1) = 1.0       ! boundary sponge cell (dist=1)
    u2(60, 60, 1) = 1.0     ! interior (outside 5-cell band)
    b_before = u2(2, 2, 1); i_before = u2(60, 60, 1)
    dtloc = 3600.0
    call apply_sponge_boundary(dtloc)
    b_after = u2(2, 2, 1); i_after = u2(60, 60, 1)
    unit = 93
    open (unit, file='data/validation/t5c3_sponge_test.json', status='replace', action='write')
    write (unit, '(A)') '{'
    write (unit, '(A,ES12.4,A)') '  "boundary_before": ', b_before, ','
    write (unit, '(A,ES12.4,A)') '  "boundary_after": ', b_after, ','
    write (unit, '(A,ES12.4,A)') '  "interior_before": ', i_before, ','
    write (unit, '(A,ES12.4,A)') '  "interior_after": ', i_after, ','
    if (b_after < b_before .and. abs(i_after - i_before) < 1.0e-9) then
        write (unit, '(A)') '  "status": "PASS"'
    else
        write (unit, '(A)') '  "status": "FAIL"'
    end if
    write (unit, '(A)') '}'
    close (unit)
    print '(A,2ES12.4)', 'boundary/interior after: ', b_after, i_after
    if (.not. (b_after < b_before .and. abs(i_after - i_before) < 1.0e-9)) error stop 1
    print *, 'RESULT: PASS (boundary damped; interior unchanged)'
end program test_sponge_boundary
