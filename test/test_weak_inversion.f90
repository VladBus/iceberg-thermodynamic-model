! ==============================================================================
! test_weak_inversion.f90 — T2 CORE TEST: weak density inversion convection
!
! PURPOSE: Exercise the production convective adjustment core
! (convective_adjustment::convect_column) on a column containing ONE localized
! weak thermal inversion, and verify the physical invariants:
!   1. HEAT conservation:   sum(T*dz1) preserved to < 1e-5 relative
!   2. SALT conservation:   sum(S*dz1) preserved to < 1e-9 absolute
!   3. final profile stable: residual inversion <= 0 reported, guard not hit
!   4. NO spurious mixing:  changes confined to the unstable interface
!
! Column (18 levels, uniform half-layer 500 m, depth 25..450 m, S = 35 PSU):
!   T = [4.3, 3.9, 4.0, 3.8, 3.8, ... ]
! Interface 2/3 (3.9 dense over 4.0 light) is the ONLY potential-density
! inversion; interfaces 1/2 and 3/4 are stable.
!
! MODE-SPECIFIC expectations (documented physics, Stage 11.8.0.0.1):
!   LEGACY (Eckart, no pressure dependence):
!     CA must detect the inversion and mix levels 2-3 to 3.95; all other
!     levels unchanged; convergence without guard hit.
!   EOS80 (UNESCO in-situ density):
!     the ~1e-4 g/cm^3 per 25 m pressure-densification exceeds the ~1e-5
!     thermal contrast, so the in-situ criterion sees the profile as stable
!     and CA performs NO mixing. This mode-dependent masking is the REAL
!     audit finding for the T2 tier (criterion on potential density, not
!     in-situ, is an 11.8 candidate fix). A spurious nonzero nmix here or any
!     change to a profile the criterion itself declares stable is a FAILURE.
!
! EXIT CODE: 0 = PASS; 1 = FAIL (JSON written first). The test GENUINELY
! fails CI on invariant violation.
! ==============================================================================
program test_weak_inversion
    use param, only: z
    use equation_of_state, only: eos80_configure, get_active_eos_mode
    use convective_adjustment, only: convect_column, ca_reset
    implicit none

    integer, parameter :: nlev = 18
    real, dimension(nlev) :: t_before, t_after, s_before, s_after
    real, dimension(nlev) :: half_layer_cm
    integer :: k, ki, nmix, iter_count, k_problem, ios, json_unit
    integer :: exit_code, n_changed
    integer, dimension(nlev) :: changed
    logical :: guard_hit, test_failed
    real :: resid_inv
    real :: heat_before, heat_after, salt_before, salt_after
    real :: heat_rel, salt_abs
    character(len=16) :: eos_mode
    character(len=256) :: json_file
    character(len=1), parameter :: q = achar(34)

    write (*, '(A)') "=== Weak-Inversion T2 Core Test (production convect_column) ==="
    write (*, '(A)') "T = [4.3, 3.9, 4.0, 3.8 x15], S = 35 PSU; inversion at interface 2/3"

    call eos80_configure()
    eos_mode = trim(get_active_eos_mode())
    json_file = "data/validation/weak_inversion_fortran_" // trim(eos_mode) // ".json"
    call ca_reset()

    ki = nlev
    do k = 1, nlev
        s_before(k) = 0.035
        s_after(k) = s_before(k)
        half_layer_cm(k) = 50000.0
        z(k) = real(k) * 2500.0
    end do
    t_before(1) = 4.3
    t_before(2) = 3.9
    t_before(3) = 4.0
    t_before(4:nlev) = 3.8
    t_after = t_before

    nmix = 0
    iter_count = 0
    guard_hit = .false.
    k_problem = 0
    resid_inv = 0.0

    ! Run the PRODUCTION convective adjustment core.
    call convect_column(t_after, s_after, half_layer_cm, ki, nmix, &
                        iter_count, guard_hit, k_problem, resid_inv)

    ! ---- invariants (both modes) ----
    heat_before = sum(t_before*half_layer_cm)
    heat_after = sum(t_after*half_layer_cm)
    salt_before = sum(s_before*half_layer_cm)
    salt_after = sum(s_after*half_layer_cm)
    heat_rel = abs(heat_after - heat_before)/abs(heat_before)
    salt_abs = abs(salt_after - salt_before)
    n_changed = 0
    changed = 0
    do k = 1, nlev
        if (abs(t_after(k) - t_before(k)) .gt. 1.0e-6) then
            n_changed = n_changed + 1
            changed(n_changed) = k
        end if
    end do

    test_failed = .false.
    if (heat_rel .gt. 1.0e-5) test_failed = .true.   ! heat must be conserved
    if (salt_abs .gt. 1.0e-9) test_failed = .true.  ! salt must be conserved
    if (guard_hit) test_failed = .true.             ! must converge
    if (resid_inv .gt. 0.0) test_failed = .true.    ! final profile stable

    ! ---- mode-specific expectations ----
    if (eos_mode .eq. 'LEGACY') then
        if (nmix .lt. 1) test_failed = .true.       ! inversion must be mixed
        if (n_changed .ne. 2) test_failed = .true.  ! confined to levels 2,3
        if (n_changed .eq. 2) then
            if ((changed(1) .ne. 2) .or. (changed(2) .ne. 3)) test_failed = .true.
            if (abs(t_after(2) - 3.95) .gt. 1.0e-5) test_failed = .true.
            if (abs(t_after(3) - t_after(2)) .gt. 1.0e-9) test_failed = .true.
        end if
    else if (eos_mode .eq. 'EOS80') then
        ! in-situ density sees the profile as stable => CA must do NOTHING
        ! (mixing would violate its own stability criterion).
        if (nmix .ne. 0) test_failed = .true.
        if (n_changed .ne. 0) test_failed = .true.
    else
        test_failed = .true.                        ! unknown mode
    end if

    write (*, '(A,A)')      "EOS_MODE: ", trim(eos_mode)
    write (*, '(A,I0)')     "nmix: ", nmix
    write (*, '(A,I0)')     "iterations: ", iter_count
    write (*, '(A,L1)')     "guard_hit: ", guard_hit
    write (*, '(A,ES12.4)') "residual inversion: ", resid_inv
    write (*, '(A,ES12.4)') "heat_rel_err: ", heat_rel
    write (*, '(A,ES12.4)') "salt_abs_err: ", salt_abs
    write (*, '(A,I0)')     "changed levels: ", n_changed
    if (test_failed) then
        write (*, '(A)') "RESULT: FAIL - convective adjustment invariant violated"
    else
        write (*, '(A)') "RESULT: PASS - inversion handled per mode; heat/salt conserved; stable; no spurious mixing"
    end if

    open (newunit=json_unit, file=trim(json_file), status="replace", &
          action="write", iostat=ios)
    if (ios /= 0) then
        write (*, '(A,A)') "ERROR: cannot open ", trim(json_file)
        error stop 1
    end if

    write (json_unit, '(A)') "{"
    write (json_unit, '(A,A,A,A,A)') "  ", q, "eos_mode", q, ": " // q // trim(eos_mode) // q // ","
    write (json_unit, '(A,A,I0,A)') "  ", q // "nmix" // q // ": ", nmix, ","
    write (json_unit, '(A,A,I0,A)') "  ", q // "iterations" // q // ": ", iter_count, ","
    if (guard_hit) then
        write (json_unit, '(A,A,A)') "  ", q // "guard_hit" // q // ": ", "true" // ","
    else
        write (json_unit, '(A,A,A)') "  ", q // "guard_hit" // q // ": ", "false" // ","
    end if
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "resid_inv" // q // ": ", resid_inv, ","
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "heat_before" // q // ": ", heat_before, ","
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "heat_after" // q // ": ", heat_after, ","
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "heat_rel_err" // q // ": ", heat_rel, ","
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "salt_abs_err" // q // ": ", salt_abs, ","
    write (json_unit, '(A,A,I0,A)') "  ", q // "n_changed_levels" // q // ": ", n_changed, ","
    write (json_unit, '(A,A)', advance="no") "  ", q // "changed_levels" // q // ": ["
    do k = 1, n_changed
        write (json_unit, '(I0)', advance="no") changed(k)
        if (k < n_changed) write (json_unit, '(A)', advance="no") ", "
    end do
    write (json_unit, '(A)') "],"
    write (json_unit, '(A,A)', advance="no") "  ", q // "T_after" // q // ": ["
    do k = 1, nlev
        write (json_unit, '(ES18.10)', advance="no") t_after(k)
        if (k < nlev) write (json_unit, '(A)', advance="no") ", "
    end do
    write (json_unit, '(A)') "],"
    if (test_failed) then
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "FAIL" // q, ","
        exit_code = 1
    else
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "PASS" // q, ","
        exit_code = 0
    end if
    if (eos_mode .eq. 'LEGACY') then
        write (json_unit, '(A,A,A,A)') "  ", q // "note" // q // ": ", &
            q // "Eckart: inversion mixed at levels 2-3" // q, ","
    else
        write (json_unit, '(A,A,A,A)') "  ", q // "note" // q // ": ", &
            q // "EOS-80 in-situ density masks the inversion: no mixing (11.8 finding)" // q, ","
    end if
    write (json_unit, '(A,A,I0)') "  ", q // "exit_code" // q // ": ", exit_code
    write (json_unit, '(A)') "}"
    close (json_unit)

    write (*, '(A,A)') "Results written to ", trim(json_file)
    write (*, '(A)') "=== Test Complete ==="

    if (test_failed) error stop 1
    stop 0

end program test_weak_inversion