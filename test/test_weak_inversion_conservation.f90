! ==============================================================================
! test_weak_inversion_conservation.f90 — T2 Phase 2
!
! Column (2 levels, dz1 = 50000 cm, z = 25 / 35 m so that compressibility
! does not dominate at this separation):
!   GENUINE INVERSION (dense over light):
!     level 1: T = 1.5 degC, S = 0.0346   (cold + salty -> denser)
!     level 2: T = 2.0 degC, S = 0.0345   (warm + fresh -> lighter)
!   STABLE CONTROL (the literal pair from the stage text, which is actually
!   STABLE because the lower level is colder AND saltier):
!     level 1: T = 2.0, S = 0.0345 ; level 2: T = 1.5, S = 0.0346
!
! Pipeline:
!   1. production float32 CA   (convect_column)
!   2. production float64-core (convect_column_f64; state arrays stay f32)
!   3. test-local EXACT float64 reference implementing the SAME published
!      algorithm (volume-weighted adjacent mixing, eps = 0.9e-7, 1000-iter
!      guard) with real64 state arrays.
!
! The exact reference proves the algorithm conserves heat and salt; the
! production paths are expected to conserve only to float32 storage
! (~1e-7 relative) because convect_column_f64 writes T/S back to REAL(4).
!
! JSON: data/validation/weak_inversion_conservation_fortran_<MODE>.json
! Exit: 0 = all expected behaviours observed; 1 = violation.
! ==============================================================================
program test_weak_inversion_conservation
    use, intrinsic :: iso_fortran_env, only: real64
    use param, only: z
    use equation_of_state, only: eos80_configure, get_active_eos_mode, eos_density_f64
    use convective_adjustment, only: convect_column, convect_column_f64, ca_reset
    implicit none

    integer, parameter :: NL = 2
    real, parameter :: eps = 0.9e-7
    real(8), parameter :: dz1v = 50000.0_real64

    real :: t32(NL), s32(NL), dz32(NL)
    real(8) :: t64(NL), s64(NL)
    integer :: k, ki, nmix, it, kp, nmix64, it64, kp64, nmix_ref, it_ref
    integer :: nmix_stable, it_stable
    logical :: guard, guard64, guard_ref
    real :: resid
    real :: resid64
    real(8) :: resid_ref
    real(8) :: hb32, ha32, sb32, sa32, hb64, ha64, sb64, sa64
    real(8) :: hbR, haR, sbR, saR
    real(8) :: heat_rel32, salt_rel32, heat_rel64, salt_rel64
    real(8) :: heat_relR, salt_relR
    character(len=16) :: mode
    character(len=256) :: path
    character(len=8) :: st_ref, st_prod, st_stable, overall
    integer :: unit, ios

    call eos80_configure()
    mode = trim(get_active_eos_mode())
    path = 'data/validation/weak_inversion_conservation_fortran_' // trim(mode) // '.json'

    ! ---- genuine inversion setup -------------------------------------------
    dz32 = real(dz1v, 4)
    z(1) = 2500.0; z(2) = 3500.0     ! 25 m and 35 m (10 dbar separation)

    t32 = (/1.5, 2.0/); s32 = (/0.0346, 0.0345/)
    call heat_salt32(t32, s32, dz32, hb32, sb32)
    ki = NL; nmix = 0; it = 0; guard = .false.; kp = 0; resid = 0.0
    call ca_reset()
    call convect_column(t32, s32, dz32, ki, nmix, it, guard, kp, resid)
    call heat_salt32(t32, s32, dz32, ha32, sa32)
    call rel_errors(hb32, ha32, sb32, sa32, heat_rel32, salt_rel32)

    t32 = (/1.5, 2.0/); s32 = (/0.0346, 0.0345/)
    nmix64 = 0; it64 = 0; guard64 = .false.; kp64 = 0; resid64 = 0.0
    call convect_column_f64(t32, s32, dz32, ki, nmix64, it64, guard64, kp64, resid64)
    call heat_salt32(t32, s32, dz32, hb64, sa32)   ! hb64 = after sum (reuse)
    call heat_salt32((/1.5, 2.0/), (/0.0346, 0.0345/), dz32, hb32, sb32)  ! before
    call rel_errors(hb32, hb64, sb32, sa32, heat_rel64, salt_rel64)

    ! ---- exact float64 reference -------------------------------------------
    t64 = (/1.5_real64, 2.0_real64/); s64 = (/0.0346_real64, 0.0345_real64/)
    call heat_salt64(t64, s64, hbR, sbR)
    call ca_exact_f64(t64, s64, nmix_ref, it_ref, guard_ref, resid_ref)
    call heat_salt64(t64, s64, haR, saR)
    call rel_errors(hbR, haR, sbR, saR, heat_relR, salt_relR)

    ! ---- stable control (literal stage pair; actually stable) --------------
    t32 = (/2.0, 1.5/); s32 = (/0.0345, 0.0346/)
    nmix_stable = 0; it_stable = 0; guard = .false.
    call convect_column(t32, s32, dz32, ki, nmix_stable, it_stable, guard, kp, resid)

    ! ---- verdicts ----------------------------------------------------------
    st_ref = 'FAIL    '
    if (heat_relR < 1.0e-12_real64 .and. salt_relR < 1.0e-12_real64 .and. &
        nmix_ref >= 1 .and. .not. guard_ref) st_ref = 'PASS    '
    st_prod = 'FAIL    '
    if (nmix >= 1 .and. nmix64 >= 1 .and. heat_rel32 < 1.0e-6_real64 .and. &
        salt_rel32 < 1.0e-6_real64 .and. heat_rel64 < 1.0e-6_real64) st_prod = 'PASS    '
    st_stable = 'FAIL    '
    if (nmix_stable == 0) st_stable = 'PASS    '

    overall = 'PASS    '
    if (trim(st_ref) /= 'PASS' .or. trim(st_prod) /= 'PASS' .or. &
        trim(st_stable) /= 'PASS') overall = 'FAIL    '

    unit = 81
    open (unit, file=trim(path), status='replace', action='write')
    write (unit, '(A)') '{'
    call js_str(unit, 'test', 'weak_inversion_conservation')
    call js_str(unit, 'eos_mode', trim(mode))
    call js_str(unit, 'inversion_setup', 'L1 T=1.5 S=0.0346 over L2 T=2.0 S=0.0345; dz1=50000 cm; z=25/35 m')
    call js_int(unit, 'nmix_production_f32', nmix)
    call js_real(unit, 'heat_rel_err_production_f32', heat_rel32)
    call js_real(unit, 'salt_rel_err_production_f32', salt_rel32)
    call js_int(unit, 'nmix_production_f64core', nmix64)
    call js_real(unit, 'heat_rel_err_production_f64core', heat_rel64)
    call js_real(unit, 'salt_rel_err_production_f64core', salt_rel64)
    call js_int(unit, 'nmix_exact_reference', nmix_ref)
    call js_int(unit, 'iterations_exact_reference', it_ref)
    call js_real(unit, 'heat_rel_err_exact_reference', heat_relR)
    call js_real(unit, 'salt_rel_err_exact_reference', salt_relR)
    call js_int(unit, 'nmix_stable_control', nmix_stable)
    call js_str(unit, 'reference_status', trim(st_ref))
    call js_str(unit, 'production_status', trim(st_prod))
    call js_str(unit, 'stable_control_status', trim(st_stable))
    call js_str(unit, 'note', 'convect_column_f64 computes in f64 but stores T/S in REAL(4); production conservation is therefore float32-limited (~1e-7 rel), while the exact f64 algorithm conserves to 1e-12+')
    call js_last_str(unit, 'status', trim(overall))
    write (unit, '(A)') '}'
    close (unit)

    print '(A,A)', 'EOS_MODE: ', trim(mode)
    print '(A,I0,A,ES12.4,A,ES12.4)', ' prod f32 : nmix=', nmix, &
          ' heat_rel=', heat_rel32, ' salt_rel=', salt_rel32
    print '(A,I0,A,ES12.4,A,ES12.4)', ' prod f64 : nmix=', nmix64, &
          ' heat_rel=', heat_rel64, ' salt_rel=', salt_rel64
    print '(A,I0,A,ES12.4,A,ES12.4)', ' exact f64: nmix=', nmix_ref, &
          ' heat_rel=', heat_relR, ' salt_rel=', salt_relR
    print '(A,I0)', ' stable control nmix=', nmix_stable
    print '(A,A)', ' OVERALL: ', trim(overall)

    if (trim(overall) /= 'PASS') error stop 1
    stop 0

contains

    subroutine heat_salt32(t, s, dz, heat, salt)
        real, intent(in) :: t(:), s(:), dz(:)
        real(8), intent(out) :: heat, salt
        integer :: kk
        heat = 0.0_real64; salt = 0.0_real64
        do kk = 1, size(t)
            heat = heat + real(t(kk), real64)*real(dz(kk), real64)
            salt = salt + real(s(kk), real64)*real(dz(kk), real64)
        end do
    end subroutine heat_salt32

    subroutine heat_salt64(t, s, heat, salt)
        real(8), intent(in) :: t(:), s(:)
        real(8), intent(out) :: heat, salt
        integer :: kk
        heat = 0.0_real64; salt = 0.0_real64
        do kk = 1, size(t)
            heat = heat + t(kk)*dz1v
            salt = salt + s(kk)*dz1v
        end do
    end subroutine heat_salt64

    subroutine rel_errors(hb, ha, sb, sa, hr, sr)
        real(8), intent(in) :: hb, ha, sb, sa
        real(8), intent(out) :: hr, sr
        hr = abs(ha - hb)/max(abs(hb), tiny(1.0_real64))
        sr = abs(sa - sb)/max(abs(sb), tiny(1.0_real64))
    end subroutine rel_errors

    ! Production algorithm mirrored with real64 state arrays (test-local).
    subroutine ca_exact_f64(ct, cs, nmix, iters, guard_hit, resid_out)
        real(8), intent(inout) :: ct(:), cs(:)
        integer, intent(out) :: nmix, iters
        logical, intent(out) :: guard_hit
        real(8), intent(out) :: resid_out
        real(8) :: cr(NL), dzz, dzz1, dz1z, a
        integer :: kk, k1, a1, its

        nmix = 0; guard_hit = .false.; iters = 0
        do kk = 1, NL
            cr(kk) = eos_density_f64(ct(kk), cs(kk), real(z(kk)*0.01, real64))
        end do
        its = 0
        do
            its = its + 1
            dzz = dz1v
            a1 = 0
            do kk = 1, NL - 1
                k1 = kk + 1
                dzz1 = dz1v
                dz1z = dzz + dzz1
                a = cr(kk) - cr(k1)
                if (a <= real(eps, real64)) then
                    dzz = dzz1
                    cycle
                end if
                a1 = a1 + 1
                ct(kk) = (ct(kk)*dzz + ct(k1)*dzz1)/dz1z
                cs(kk) = (cs(kk)*dzz + cs(k1)*dzz1)/dz1z
                ct(k1) = ct(kk)
                cs(k1) = cs(kk)
                cr(kk) = eos_density_f64(ct(kk), cs(kk), real(z(kk)*0.01, real64))
                cr(k1) = cr(kk)
                dzz = dzz1
            end do
            nmix = nmix + a1
            if (a1 == 0) exit
            if (its > 1000) then
                guard_hit = .true.
                exit
            end if
        end do
        iters = its
        resid_out = 0.0_real64
        do kk = 1, NL - 1
            resid_out = max(resid_out, cr(kk) - cr(kk + 1))
        end do
    end subroutine ca_exact_f64

    pure function qq() result(s)
        character(len=1) :: s
        s = achar(34)
    end function qq

    subroutine js_str(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()//','
    end subroutine js_str

    subroutine js_last_str(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()
    end subroutine js_last_str

    subroutine js_real(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        real(8), intent(in) :: val
        write (unit, '(A,ES18.10,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_real

    subroutine js_int(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        integer, intent(in) :: val
        write (unit, '(A,I0,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_int

end program test_weak_inversion_conservation