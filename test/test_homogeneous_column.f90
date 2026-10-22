! ==============================================================================
! test_homogeneous_column.f90 — RED TEST: Homogeneous Column Convective Adjustment
!
! PURPOSE: Verify that convective adjustment does NOT modify a physically
! stable, homogeneous water column.
!
! TEST: Initialize T = 4.0 °C, S = 35.0 PSU (0.035 mass fraction) at all levels.
! Call convective_adjustment::convect_column (production code).
! Check: output T and S should be IDENTICAL to input (dT <= 1e-6, dS <= 1e-6).
! If they differ: status = FAIL, proving CA introduces spurious mixing.
!
! EOS MODE: selected by the EOS_MODE environment variable (LEGACY default,
! EOS80 opt-in) via equation_of_state::eos80_configure(). Run this executable
! twice (EOS_MODE=LEGACY and EOS_MODE=EOS80) to exercise both modes.
!
! EXIT CODE: 0 = test executed and wrote results (regardless of PASS/FAIL);
!            1 = execution error.
! The PASS/FAIL verdict is recorded in the JSON `status` field, because this
! is a RED test whose FAIL is the expected defect evidence.
!
! USAGE: EOS_MODE=LEGACY fpm run --flag "-I/usr/include" -- homogeneous_column
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
    logical :: guard_hit
    real :: resid_inv
    real :: delta_t_max, delta_s_max
    character(len=16) :: eos_mode
    character(len=256) :: json_file
    character(len=1), parameter :: q = achar(34)


    write (*, '(A)') "=== Homogeneous Column Convective Adjustment Test ==="
    write (*, '(A)') "T = 4.0 degC, S = 35.0 PSU (0.035 mass fraction), all levels"

    ! Select EOS mode from the environment (LEGACY default).
    call eos80_configure()
    eos_mode = trim(get_active_eos_mode())
    json_file = "data/validation/homogeneous_column_fortran_" // trim(eos_mode) // ".json"
    call ca_reset()

    ! Initialize the homogeneous column and realistic depth/pressure levels.
    ! half_layer thickness = 500 m = 50000 cm (uniform).
    ! z = layer centre depth [cm]; 18 levels, 25 m spacing => 25..450 m.
    ki = nlev
    do k = 1, nlev
        t_before(k) = 4.0
        s_before(k) = 0.035
        t_after(k) = t_before(k)
        s_after(k) = s_before(k)
        half_layer_cm(k) = 50000.0
        z(k) = real(k) * 2500.0   ! 25 m, 50 m, ... 450 m in cm
    end do

    nmix = 0
    iter_count = 0
    guard_hit = .false.
    k_problem = 0
    resid_inv = 0.0

    ! Run the PRODUCTION convective adjustment core on this column.
    call convect_column(t_after, s_after, half_layer_cm, ki, nmix, &
                        iter_count, guard_hit, k_problem, resid_inv)

    ! Measure actual changes.
    delta_t_max = 0.0
    delta_s_max = 0.0
    do k = 1, nlev
        delta_t_max = max(delta_t_max, abs(t_after(k) - t_before(k)))
        delta_s_max = max(delta_s_max, abs(s_after(k) - s_before(k)))
    end do

    write (*, '(A,A)')  "EOS_MODE: ", trim(eos_mode)
    write (*, '(A,I0)') "CA iterations: ", iter_count
    write (*, '(A,L1)') "Guard hit: ", guard_hit
    write (*, '(A,ES12.4)') "max |dT|: ", delta_t_max
    write (*, '(A,ES12.4)') "max |dS|: ", delta_s_max
    write (*, '(A,I0)') "Number of mixings (nmix): ", nmix
    write (*, '(A,I0)') "Residual inversion: ", k_problem

    if (delta_t_max > 1.0e-6 .or. delta_s_max > 1.0e-6) then
        write (*, '(A)') "RESULT: FAIL - convective adjustment modified a homogeneous column"
    else
        write (*, '(A)') "RESULT: PASS - homogeneous column unchanged"
    end if

    ! Write machine-readable JSON (Fortran has no backslash escapes; use achar(34)).
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
    if (delta_t_max > 1.0e-6 .or. delta_s_max > 1.0e-6) then
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "FAIL" // q, ","
    else
        write (json_unit, '(A,A,A,A)') "  ", q // "status" // q // ": ", q // "PASS" // q, ","
    end if
    write (json_unit, '(A,A,I0)') "  ", q // "exit_code" // q // ": ", 0
    write (json_unit, '(A)') "}"
    close (json_unit)

    write (*, '(A,A)') "Results written to ", trim(json_file)
    write (*, '(A)') "=== Test Complete ==="

    ! Exit 0: execution completed; verdict is in JSON `status`.
    stop 0

contains

    subroutine write_reals(unit, values)
        integer, intent(in) :: unit
        real, intent(in) :: values(:)
        integer :: n
        n = size(values)
        do k = 1, n
            write (unit, '(ES18.10)', advance="no") values(k)
            if (k < n) write (unit, '(A)', advance="no") ", "
        end do
    end subroutine write_reals

end program test_homogeneous_column