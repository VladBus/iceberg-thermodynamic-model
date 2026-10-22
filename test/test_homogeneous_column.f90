! ==============================================================================
! test_homogeneous_column.f90 — T2 SMOKE TEST: homogeneous column CA control
!
! PURPOSE: Verify that the production convective adjustment (convect_column)
! does NOT modify a physically stable, homogeneous water column, and that the
! test FAILS (non-zero exit) if the invariant is violated.
!
! TEST: T = 4.0 °C, S = 35.0 PSU (0.035 mass fraction) at all 18 levels —
! statically stable by construction (identical T/S; deeper in-situ density is
! monotonically larger under EOS-80 pressure dependence).
! Call convective_adjustment::convect_column (production core).
! Invariant: output T and S IDENTICAL to input (|dT| <= 1e-6, |dS| <= 1e-6).
!
! NOTE (Stage 11.8.0.0.1 correction): this is a SMOKE / no-spurious-mixing
! control test, NOT a red test. A homogeneous column is stable under both
! EOS modes, so PASS is the expected outcome; the CA defect target is the
! weak-inversion test (test_weak_inversion.f90, T2 core).
!
! EOS MODE: selected by the EOS_MODE environment variable (LEGACY default,
! EOS80 opt-in) via equation_of_state::eos80_configure().
!
! EXIT CODE: 0 = PASS (invariant holds); 1 = FAIL (invariant violated, written
! to JSON first) or execution error. The process exit code therefore GENUINELY
! fails CI when the physics regression appears.
! ==============================================================================
program test_homogeneous_column
    use param, only: z
    use equation_of_state, only: eos80_configure, get_active_eos_mode
    use convective_adjustment, only: convect_column, ca_reset
    implicit none

    integer, parameter :: nlev = 18
    real, dimension(nlev) :: t_before, t_after, s_before, s_after
    real, dimension(nlev) :: half_layer_cm
    integer :: k, ki, nmix, iter_count, k_problem, ios, json_unit
    integer :: exit_code
    logical :: guard_hit, test_failed
    real :: resid_inv
    real :: delta_t_max, delta_s_max
    character(len=16) :: eos_mode
    character(len=256) :: json_file
    character(len=1), parameter :: q = achar(34)

    write (*, '(A)') "=== Homogeneous Column CA Smoke Test ==="
    write (*, '(A)') "T = 4.0 degC, S = 35.0 PSU (0.035 mass fraction), all levels"

    ! Select EOS mode from the environment (LEGACY default).
    call eos80_configure()
    eos_mode = trim(get_active_eos_mode())
    json_file = "data/validation/homogeneous_column_fortran_" // trim(eos_mode) // ".json"
    call ca_reset()

    ! Initialize the homogeneous column; z = layer centre depth [cm]
    ! (25 m spacing: 25..450 m); uniform half-layer thickness 500 m = 50000 cm.
    ki = nlev
    do k = 1, nlev
        t_before(k) = 4.0
        s_before(k) = 0.035
        t_after(k) = t_before(k)
        s_after(k) = s_before(k)
        half_layer_cm(k) = 50000.0
        z(k) = real(k) * 2500.0
    end do

    nmix = 0
    iter_count = 0
    guard_hit = .false.
    k_problem = 0
    resid_inv = 0.0

    ! Run the PRODUCTION convective adjustment core on this column.
    call convect_column(t_after, s_after, half_layer_cm, ki, nmix, &
                        iter_count, guard_hit, k_problem, resid_inv)

    ! Measure actual changes; violation => genuine FAIL.
    delta_t_max = 0.0
    delta_s_max = 0.0
    do k = 1, nlev
        delta_t_max = max(delta_t_max, abs(t_after(k) - t_before(k)))
        delta_s_max = max(delta_s_max, abs(s_after(k) - s_before(k)))
    end do
    test_failed = (delta_t_max > 1.0e-6) .or. (delta_s_max > 1.0e-6)

    write (*, '(A,A)')      "EOS_MODE: ", trim(eos_mode)
    write (*, '(A,I0)')     "CA iterations: ", iter_count
    write (*, '(A,L1)')     "Guard hit: ", guard_hit
    write (*, '(A,ES12.4)') "max |dT|: ", delta_t_max
    write (*, '(A,ES12.4)') "max |dS|: ", delta_s_max
    write (*, '(A,I0)')     "Number of mixings (nmix): ", nmix
    if (test_failed) then
        write (*, '(A)') "RESULT: FAIL - convective adjustment modified a homogeneous column"
    else
        write (*, '(A)') "RESULT: PASS - homogeneous column unchanged"
    end if

    ! Write machine-readable JSON (achar(34) for quotes; relative paths only).
    open (newunit=json_unit, file=trim(json_file), status="replace", &
          action="write", iostat=ios)
    if (ios /= 0) then
        write (*, '(A,A)') "ERROR: cannot open ", trim(json_file)
        error stop 1
    end if

    write (json_unit, '(A)') "{"
    write (json_unit, '(A,A,A,A,A)') "  ", q, "eos_mode", q, ": " // q // trim(eos_mode) // q // ","
    write (json_unit, '(A,A)', advance="no") "  ", q // "T_before" // q // ": ["
    call write_reals(json_unit, t_before)
    write (json_unit, '(A)') "],"
    write (json_unit, '(A,A)', advance="no") "  ", q // "T_after" // q // ": ["
    call write_reals(json_unit, t_after)
    write (json_unit, '(A)') "],"
    write (json_unit, '(A,A)', advance="no") "  ", q // "S_before" // q // ": ["
    call write_reals(json_unit, s_before)
    write (json_unit, '(A)') "],"
    write (json_unit, '(A,A)', advance="no") "  ", q // "S_after" // q // ": ["
    call write_reals(json_unit, s_after)
    write (json_unit, '(A)') "],"
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "delta_T_max" // q // ": ", delta_t_max, ","
    write (json_unit, '(A,A,ES18.10,A)') "  ", q // "delta_S_max" // q // ": ", delta_s_max, ","
    write (json_unit, '(A,A,I0,A)') "  ", q // "iterations" // q // ": ", iter_count, ","
    if (guard_hit) then
        write (json_unit, '(A,A,A)') "  ", q // "guard_hit" // q // ": ", "true" // ","
    else
        write (json_unit, '(A,A,A)') "  ", q // "guard_hit" // q // ": ", "false" // ","
    end if
    write (json_unit, '(A,A,I0,A)') "  ", q // "nmix" // q // ": ", nmix, ","
    if (test_failed) then
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "FAIL" // q, ","
        exit_code = 1
    else
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "PASS" // q, ","
        exit_code = 0
    end if
    write (json_unit, '(A,A,A,A)') "  ", q // "test_kind" // q // ": ", q // "smoke_control" // q, ","
    write (json_unit, '(A,A,I0)') "  ", q // "exit_code" // q // ": ", exit_code
    write (json_unit, '(A)') "}"
    close (json_unit)

    write (*, '(A,A)') "Results written to ", trim(json_file)
    write (*, '(A)') "=== Test Complete ==="

    if (test_failed) error stop 1
    stop 0

contains

    subroutine write_reals(unit, values)
        integer, intent(in) :: unit
        real, intent(in) :: values(:)
        integer :: n, i
        n = size(values)
        do i = 1, n
            write (unit, '(ES18.10)', advance="no") values(i)
            if (i < n) write (unit, '(A)', advance="no") ", "
        end do
    end subroutine write_reals

end program test_homogeneous_column