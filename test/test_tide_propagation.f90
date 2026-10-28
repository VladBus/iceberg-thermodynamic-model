program test_tide_propagation
    use netcdf
    implicit none
    integer :: ncid, vid, st
    real :: amp(133,105,4), pha(133,105,4)
    real :: celerity
    st = nf90_open('data/input/processed/tides/tides.nc', nf90_nowrite, ncid)
    if (st /= nf90_noerr) then; print *, 'TIDE TEST: SKIP missing tides.nc'; stop 0; end if
    st = nf90_inq_varid(ncid, 'amplitude', vid); st = nf90_get_var(ncid, vid, amp)
    st = nf90_inq_varid(ncid, 'phase', vid); st = nf90_get_var(ncid, vid, pha)
    st = nf90_close(ncid)
    celerity = sqrt(981.0*50000.0)  ! cm/s for 500 m
    print '(A,2F9.4,A,2F9.4)', 'M2 amp max/min=', maxval(amp(:,:,1)), minval(amp(:,:,1)), ' phase range=', minval(pha(:,:,1)), maxval(pha(:,:,1))
    print '(A,F10.3,A)', 'sqrt(gH)=', celerity, ' cm/s'
    if (abs(maxval(amp(:,:,1))-0.5) .gt. 1e-4) then; print *, 'TIDE TEST: FAIL amplitude'; stop 1; end if
    if (maxval(pha(:,:,1)) .le. minval(pha(:,:,1))) then; print *, 'TIDE TEST: FAIL phase'; stop 1; end if
    print *, 'TIDE TEST: PASS synthetic M2 schema'
    stop 0
end program test_tide_propagation
