program test_obc_radiation
    use stage1110_obc, only: radiation_update
    implicit none
    real :: a, b, c
    integer :: errs
    errs = 0
    a = radiation_update(2.0, 2.0, 500.0, 120.0, 1389000.0)
    b = radiation_update(3.0, 1.0, 500.0, 120.0, 1389000.0)
    c = radiation_update(1.0, 3.0, 500.0, 120.0, 1389000.0)
    if (abs(a - 2.0) .gt. 1e-5) errs = errs + 1
    if (abs(b - 3.0) .lt. 1e-6) errs = errs + 1
    if (abs(c - 1.0) .lt. 1e-6) errs = errs + 1
    print '(A,3ES14.5)', 'radiation a/b/c=', a, b, c
    if (errs .eq. 0) then
        print *, 'OBC RADIATION: PASS'
        stop 0
    else
        print *, 'OBC RADIATION: FAIL', errs
        stop 1
    end if
end program test_obc_radiation
