! T5-CORRECTIVE-3: monotone/positive salinity advection test.
program test_monotone_advection
    use param
    use advection_3d_s, only: advs
    use stage118_physics_switches, only: s118_monotone_advection
    implicit none
    integer :: i, j, k, unit
    real :: smax0, smin1, smax1, dtloc, c2loc
    integer :: n_neg

    s118_monotone_advection = .true.
    kt1 = 18; idx = 18; idy = 18
    adx = 1.0; ady = 1.0
    s2 = 0.035; s1 = 0.035
    do k = 1, ks
        do j = 1, js1
            do i = 1, is1
                if (j > 66) s2(i, j, k) = 0.0
            end do
        end do
    end do
    s1 = s2
    smax0 = maxval(s2)
    u2 = 0.0; v2 = 0.0; w = 0.0
    u2(:, :, :) = 10000.0   ! uniform X (j) advection [cm/s]
    up2 = 0.0; vp2 = 0.0
    apx = 0.0; apy = 0.0; apz = 0.0; cd = 0.0; tt = 0.0
    dtloc = 3600.0
    c2loc = dtloc/1389000.0
    call advs(dtloc, c2loc)

    smin1 = minval(s2(:, 1:js, :))
    smax1 = maxval(s2(:, 1:js, :))
    n_neg = count(s2(:, 1:js, :) < 0.0)
    unit = 92
    open (unit, file='data/validation/t5c3_monotone_test.json', status='replace', action='write')
    write (unit, '(A)') '{'
    write (unit, '(A,ES12.4,A)') '  "s_min": ', smin1, ','
    write (unit, '(A,ES12.4,A)') '  "s_max": ', smax1, ','
    write (unit, '(A,ES12.4,A)') '  "s_max_initial": ', smax0, ','
    write (unit, '(A,I0,A)') '  "negative_cells": ', n_neg, ','
    if (smin1 >= -1.0e-9 .and. smax1 <= smax0 + 1.0e-9 .and. n_neg == 0) then
        write (unit, '(A)') '  "status": "PASS"'
        smin1 = 0.0
    else
        write (unit, '(A)') '  "status": "FAIL"'
    end if
    write (unit, '(A)') '}'
    close (unit)
    print '(A,ES12.4,A,ES12.4,A,I0)', 'S min/max/neg: ', smin1, ' / ', smax1, ' / ', n_neg
    if (smin1 < -1.0e-9 .or. smax1 > smax0 + 1.0e-9 .or. n_neg /= 0) error stop 1
    print *, 'RESULT: PASS (no new extrema, S >= 0)'
end program test_monotone_advection
