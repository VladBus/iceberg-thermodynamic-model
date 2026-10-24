! ==============================================================================
! test_advection_boundary.f90 — T3-CORRECTIVE (T-29) regression
!
! Verifies that the horizontal FCT advection kernels preserve the T/S boundary
! row/column (i=is1, j=js1) instead of overwriting it with the unwritten `cd`.
!
! Setup: all cells wet (kt1=18), uniform S=0.035 / T=5 degC, zero velocity,
! zero FCT flows. Advection with zero velocity must change nothing anywhere.
! Before the T-29 fix, `s2 = cd` / `t2 = cd` zeroed the boundary (cd is only
! computed on 1..is,1..js), so the boundary check failed.
!
! JSON: data/validation/advection_boundary_result.json
! Exit: 0 = PASS; 1 = FAIL.
! ==============================================================================
program test_advection_boundary
    use param
    use advection_3d_s, only: advs
    use advection_3d_t, only: advt
    implicit none

    integer :: i, j, k, n_bad_int, n_bad_bnd
    real :: s_init, t_init, dtloc, c2loc
    character(len=1), parameter :: qt = achar(34)
    integer :: unit

    s_init = 0.035
    t_init = 5.0
    dtloc = 3600.0
    c2loc = 0.0

    kt1 = 18
    s2 = s_init; s1 = s_init
    t2 = t_init; t1 = t_init
    u2 = 0.0; v2 = 0.0; u1 = 0.0; v1 = 0.0
    w = 0.0
    dz1 = 50000.0
    adx = 1.0; ady = 1.0
    apx = 0.0; apy = 0.0; apz = 0.0
    cd = 0.0

    call advs(dtloc, c2loc)
    call advt(dtloc, c2loc)

    n_bad_int = 0
    n_bad_bnd = 0
    do k = 1, ks
        do j = 1, js
            do i = 1, is
                if (abs(s2(i, j, k) - s_init) > 1.0e-6 .or. &
                    abs(t2(i, j, k) - t_init) > 1.0e-6) n_bad_int = n_bad_int + 1
            end do
        end do
        do j = 1, js
            if (abs(s2(is1, j, k) - s_init) > 1.0e-6 .or. &
                abs(t2(is1, j, k) - t_init) > 1.0e-6) n_bad_bnd = n_bad_bnd + 1
        end do
        do i = 1, is1
            if (abs(s2(i, js1, k) - s_init) > 1.0e-6 .or. &
                abs(t2(i, js1, k) - t_init) > 1.0e-6) n_bad_bnd = n_bad_bnd + 1
        end do
    end do

    print '(A,I0)', 'interior violations: ', n_bad_int
    print '(A,I0)', 'boundary violations: ', n_bad_bnd

    unit = 91
    open (unit, file='data/validation/advection_boundary_result.json', &
          status='replace', action='write')
    write (unit, '(A)') '{'
    write (unit, '(A)') '  '//qt//'test'//qt//': '//qt//'advection_boundary'//qt//','
    write (unit, '(A)') '  '//qt//'setup'//qt//': '//qt//'uniform S=0.035/T=5, zero velocity, all wet'//qt//','
    write (unit, '(A,I0,A)') '  '//qt//'interior_violations'//qt//': ', n_bad_int, ','
    write (unit, '(A,I0,A)') '  '//qt//'boundary_violations'//qt//': ', n_bad_bnd, ','
    if (n_bad_int == 0 .and. n_bad_bnd == 0) then
        write (unit, '(A)') '  '//qt//'status'//qt//': '//qt//'PASS'//qt
    else
        write (unit, '(A)') '  '//qt//'status'//qt//': '//qt//'FAIL'//qt
    end if
    write (unit, '(A)') '}'
    close (unit)

    if (n_bad_int /= 0 .or. n_bad_bnd /= 0) then
        print *, 'RESULT: FAIL (T-29 boundary not preserved)'
        error stop 1
    end if
    print *, 'RESULT: PASS (interior and boundary preserved)'
    stop 0

end program test_advection_boundary