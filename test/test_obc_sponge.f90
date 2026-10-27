program test_obc_sponge
    use stage1110_obc, only: sponge_weight
    implicit none
    real :: w0, w5, wi
    integer :: errs
    errs = 0
    w0 = sponge_weight(0.0, 5.0, 1.0/86400.0, 3600.0)
    w5 = sponge_weight(5.0, 5.0, 1.0/86400.0, 3600.0)
    wi = sponge_weight(6.0, 5.0, 1.0/86400.0, 3600.0)
    if (w0 .le. w5) errs = errs + 1
    if (wi .ne. 0.0) errs = errs + 1
    if (w0 .gt. 1.0) errs = errs + 1
    print '(A,3ES14.5)', 'sponge w0/w5/wi=', w0, w5, wi
    if (errs .eq. 0) then
        print *, 'OBC SPONGE: PASS'
        stop 0
    else
        print *, 'OBC SPONGE: FAIL', errs
        stop 1
    end if
end program test_obc_sponge
