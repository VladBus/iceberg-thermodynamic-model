program test_obc_flather
    use stage1110_obc, only: flather_transport
    implicit none
    real :: q0, q1, q2
    integer :: errs
    errs = 0
    q0 = flather_transport(0.0, 500.0)
    q1 = flather_transport(100.0, 500.0)
    q2 = flather_transport(100.0, 500.0)
    if (abs(q0) .gt. 1e-9) errs = errs + 1
    if (abs(q1 + 100.0*sqrt(981.0*500.0)) .gt. 1e-3) errs = errs + 1
    if (abs(q1 - q2) .gt. 1e-9) errs = errs + 1
    print '(A,3ES14.5)', 'flather q0/q1/q2=', q0, q1, q2
    if (errs .eq. 0) then
        print *, 'OBC FLATHER: PASS'
        stop 0
    else
        print *, 'OBC FLATHER: FAIL', errs
        stop 1
    end if
end program test_obc_flather
