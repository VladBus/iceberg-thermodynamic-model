! ==============================================================================
! Module: stage118_physics_switches
! Stage 11.8.0 T3-CORRECTIVE-3 — D-33 physics-branch switches.
!
! All switches default OFF -> legacy-frozen branch bit-identical.
! The stage11-physics branch is selected explicitly:
!   STAGE118_RO_PROGNOSTIC=true  (E1) recompute RO from T/S after CA,
!                                     before Block 200; CA does not write RO.
!   STAGE118_CA_POTENTIAL=true   (E2) CA compares both levels at the same
!                                     reference pressure (potential density).
!   STAGE118_CA_F64_N2=true      (E3) CA density differences in real64 and
!                                     N^2 < -1e-6 s^-2 instability criterion.
! ==============================================================================
module stage118_physics_switches
    implicit none

    logical, save, public :: s118_ro_prognostic = .false.
    logical, save, public :: s118_ca_potential = .false.
    logical, save, public :: s118_ca_f64_n2 = .false.
    logical, save, public :: s118_boundary_sponge = .false.
    logical, save, public :: s118_t3_keep_tw = .false.

contains

    subroutine s118_init()
        character(len=64) :: env

        call get_environment_variable('STAGE118_RO_PROGNOSTIC', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_ro_prognostic = .true.

        call get_environment_variable('STAGE118_CA_POTENTIAL', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_ca_potential = .true.

        call get_environment_variable('STAGE118_CA_F64_N2', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_ca_f64_n2 = .true.

        call get_environment_variable('STAGE118_BOUNDARY_SPONGE', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_boundary_sponge = .true.

        call get_environment_variable('STAGE118_T3_KEEP_TW', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_t3_keep_tw = .true.

        if (s118_ro_prognostic .or. s118_ca_potential .or. s118_ca_f64_n2 .or. &
            s118_boundary_sponge .or. s118_t3_keep_tw) then
            print *, '>>> STAGE 11.8.0 T3-CORRECTIVE-3 physics branch: ', &
                'RO_PROGNOSTIC=', s118_ro_prognostic, &
                ' CA_POTENTIAL=', s118_ca_potential, &
                ' CA_F64_N2=', s118_ca_f64_n2, &
                ' SPONGE=', s118_boundary_sponge, ' KEEP_TW=', s118_t3_keep_tw
        else
            print *, '>>> STAGE 11.8.0 T3-CORRECTIVE-3 physics branch: LEGACY-FROZEN (all switches OFF)'
        end if
    end subroutine s118_init

end module stage118_physics_switches
