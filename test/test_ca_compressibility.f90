! ==============================================================================
! test_ca_compressibility.f90 — T2 Phase 3 (Sonnet A-1)
!
! Does convective adjustment compare IN-SITU density at each level's own
! pressure, or POTENTIAL density (referenced to the surface)?
!
! Column (2 levels; z = 25 m and 75 m -> 50 dbar separation; dz1 = 50000 cm):
!   level 1: T = 3.0 degC, S = 0.0345
!   level 2: T = 3.6 degC, S = 0.0345   (warmer -> lighter at equal pressure)
!
! Under EOS-80:
!   sigma_0(1) > sigma_0(2)      -> POTENTIAL DENSITY IS UNSTABLE
!                                   (dense over light -> real convection)
!   rho_in_situ(2) > rho_in_situ(1) -> IN-SITU DENSITY IS STABLE
!                                   (compression over 50 dbar ~ 2.3e-4 g/cm3
!                                    exceeds the thermal contrast ~1.2e-4)
! Under LEGACY (no pressure dependence) the column is plainly unstable.
!
! Expected production behaviour (diagnostic, NOT fixed in T2):
!   LEGACY : CA mixes (control) -> nmix >= 1
!   EOS80  : CA uses eos_density(..., p=z*0.01 dbar) (in-situ) and therefore
!            sees the column as stable -> nmix = 0  => CRITICAL false
!            stability (A-1 confirmed).
!
! JSON: data/validation/ca_compressibility_fortran_<MODE>.json
! Exit: 0 = behaviour matches the expected per-mode outcome (finding
!       recorded); 1 = construction invalid or unexpected behaviour.
! ==============================================================================
program test_ca_compressibility
    use, intrinsic :: iso_fortran_env, only: real64
    use param, only: z
    use equation_of_state, only: eos80_configure, get_active_eos_mode, eos_density_f64
    use convective_adjustment, only: convect_column, convect_column_f64, ca_reset
    implicit none

    integer, parameter :: NL = 2
    real, parameter :: dzv = 50000.0

    real :: t32(NL), s32(NL), dz32(NL)
    integer :: ki, nmix32, it32, kp, nmix64, it64, kp64
    logical :: g32, g64
    real :: r32
    real :: r64
    real(8) :: sig0(NL), rho(NL), comp, therm
    character(len=16) :: mode
    character(len=256) :: path
    character(len=24) :: status
    logical :: valid_construction
    integer :: unit

    call eos80_configure()
    mode = trim(get_active_eos_mode())
    path = 'data/validation/ca_compressibility_fortran_' // trim(mode) // '.json'

    dz32 = real(dzv, 4)
    z(1) = 2500.0      ! 25 m
    z(2) = 7500.0      ! 75 m

    ! potential density (p=0) and in-situ density at each level's depth
    sig0(1) = eos_density_f64(3.0_real64, 0.0345_real64, 0.0_real64)
    sig0(2) = eos_density_f64(3.6_real64, 0.0345_real64, 0.0_real64)
    rho(1) = eos_density_f64(3.0_real64, 0.0345_real64, real(z(1)*0.01, real64))
    rho(2) = eos_density_f64(3.6_real64, 0.0345_real64, real(z(2)*0.01, real64))

    valid_construction = (sig0(1) > sig0(2)) .and. (rho(2) > rho(1))
    comp = rho(2) - eos_density_f64(3.6_real64, 0.0345_real64, real(z(1)*0.01, real64))
    therm = sig0(1) - sig0(2)

    ! ---- production CA (f32 and f64-core) on this column -------------------
    t32 = (/3.0, 3.6/); s32 = (/0.0345, 0.0345/)
    ki = NL; nmix32 = 0; it32 = 0; g32 = .false.; kp = 0; r32 = 0.0
    call ca_reset()
    call convect_column(t32, s32, dz32, ki, nmix32, it32, g32, kp, r32)

    t32 = (/3.0, 3.6/); s32 = (/0.0345, 0.0345/)
    nmix64 = 0; it64 = 0; g64 = .false.; kp64 = 0; r64 = 0.0
    call convect_column_f64(t32, s32, dz32, ki, nmix64, it64, g64, kp64, r64)

    ! ---- verdicts ----------------------------------------------------------
    if (mode == 'LEGACY') then
        ! control: no pressure dependence -> the column is plainly unstable
        if (nmix32 >= 1 .and. nmix64 >= 1) then
            status = 'CONTROL_PASS'
        else
            status = 'UNEXPECTED'
        end if
    else if (.not. valid_construction) then
        status = 'CONSTRUCTION_INVALID'
    else
        ! EOS-80: potential-unstable but in-situ-stable -> CA must NOT mix
        ! (false stability, A-1). If it mixes, the criterion is potential.
        if (nmix32 == 0 .and. nmix64 == 0) then
            status = 'CRITICAL_CONFIRMED'
        else if (nmix32 >= 1 .or. nmix64 >= 1) then
            status = 'NOT_CONFIRMED_CA_MIXED'
        else
            status = 'UNEXPECTED'
        end if
    end if

    unit = 82
    open (unit, file=trim(path), status='replace', action='write')
    write (unit, '(A)') '{'
    call js_str(unit, 'test', 'ca_compressibility')
    call js_str(unit, 'eos_mode', trim(mode))
    call js_str(unit, 'setup', 'L1 T=3.0 S=0.0345 z=25m over L2 T=3.6 S=0.0345 z=75m; dz1=50000cm')
    call js_str(unit, 'density_criterion_source', 'src/convective_adjustment.f90: cr(k)=eos_density(ct(k),cs(k),z(k)*0.01) (IN-SITU at local depth)')
    call js_real(unit, 'sigma0_level1', sig0(1))
    call js_real(unit, 'sigma0_level2', sig0(2))
    call js_real(unit, 'rho_in_situ_level1', rho(1))
    call js_real(unit, 'rho_in_situ_level2', rho(2))
    call js_real(unit, 'compression_gain_50dbar', comp)
    call js_real(unit, 'thermal_destabilisation', therm)
    call js_bool(unit, 'potential_unstable', sig0(1) > sig0(2))
    call js_bool(unit, 'in_situ_stable', rho(2) > rho(1))
    call js_bool(unit, 'construction_valid', valid_construction)
    call js_int(unit, 'nmix_production_f32', nmix32)
    call js_int(unit, 'nmix_production_f64core', nmix64)
    call js_str(unit, 'status', trim(status))
    call js_last_str(unit, 'finding', &
        'CA compares IN-SITU density at each level pressure (no potential-density criterion). Under EOS-80, compressibility over 50 dbar can exceed the thermal contrast, so a genuinely convective (potential-density-unstable) column is falsely declared stable and left unmixed. Not fixed in T2.')
    write (unit, '(A)') '}'
    close (unit)

    print '(A,A)', 'EOS_MODE: ', trim(mode)
    print '(A,ES16.8,A,ES16.8)', ' sigma0 L1/L2: ', sig0(1), ' / ', sig0(2)
    print '(A,ES16.8,A,ES16.8)', ' rho_in_situ L1/L2: ', rho(1), ' / ', rho(2)
    print '(A,L1,A,L1)', ' potential_unstable=', sig0(1) > sig0(2), &
          ' in_situ_stable=', rho(2) > rho(1)
    print '(A,I0,A,I0)', ' nmix f32/f64: ', nmix32, ' / ', nmix64
    print '(A,A)', ' STATUS: ', trim(status)

    if (status == 'CONSTRUCTION_INVALID' .or. status == 'UNEXPECTED' .or. &
        status == 'NOT_CONFIRMED_CA_MIXED') error stop 1
    stop 0

contains

    pure function qq() result(s)
        character(len=1) :: s
        s = achar(34)
    end function qq

    subroutine js_str(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()//','
    end subroutine js_str

    subroutine js_real(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        real(8), intent(in) :: val
        write (unit, '(A,ES18.10,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_real

    subroutine js_last_str(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key, val
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//qq()//trim(val)//qq()
    end subroutine js_last_str

    subroutine js_int(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        integer, intent(in) :: val
        write (unit, '(A,I0,A)') '  '//qq()//trim(key)//qq()//': ', val, ','
    end subroutine js_int

    subroutine js_bool(unit, key, val)
        integer, intent(in) :: unit
        character(len=*), intent(in) :: key
        logical, intent(in) :: val
        character(len=5) :: s
        s = 'false'
        if (val) s = 'true '
        write (unit, '(A)') '  '//qq()//trim(key)//qq()//': '//s//','
    end subroutine js_bool

end program test_ca_compressibility