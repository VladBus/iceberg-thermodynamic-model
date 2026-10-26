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
    logical, save, public :: s118_lap_visc = .false.
    real, save, public :: s118_ah_m2s = 10000.0
    logical, save, public :: s118_wind_rotation = .false.
    logical, save, public :: s118_lon_clamp = .false.
    logical, save, public :: s118_monotone_advection = .false.
    logical, save, public :: s118_sponge_boundary = .false.
    real, save, public :: s118_sponge_alpha = 1.0

contains

    subroutine s118_init()
        character(len=64) :: env
        integer :: ios

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

        call get_environment_variable('STAGE118_WIND_ROTATION', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_wind_rotation = .true.

        call get_environment_variable('STAGE118_LON_CLAMP', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_lon_clamp = .true.

        call get_environment_variable('STAGE118_MONOTONE_ADVECTION', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_monotone_advection = .true.

        call get_environment_variable('STAGE118_SPONGE_BOUNDARY', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_sponge_boundary = .true.
        call get_environment_variable('STAGE118_SPONGE_ALPHA', env)
        if (len_trim(env) .gt. 0) then
            read (env, *, iostat=ios) s118_sponge_alpha
            if (ios .ne. 0 .or. s118_sponge_alpha .le. 0.0) s118_sponge_alpha = 1.0
        end if

        call get_environment_variable('STAGE118_LAPLACIAN_VISC', env)
        if (len_trim(env) .gt. 0 .and. (trim(env) .eq. 'true' .or. &
            trim(env) .eq. '1' .or. trim(env) .eq. 'TRUE')) s118_lap_visc = .true.
        call get_environment_variable('STAGE118_AH', env)
        if (len_trim(env) .gt. 0) then
            read (env, *, iostat=ios) s118_ah_m2s
            if (ios .ne. 0) s118_ah_m2s = 10000.0
        end if

        if (s118_ro_prognostic .or. s118_ca_potential .or. s118_ca_f64_n2 .or. &
            s118_boundary_sponge .or. s118_t3_keep_tw .or. s118_lap_visc .or. &
            s118_wind_rotation .or. s118_lon_clamp .or. s118_monotone_advection .or. &
            s118_sponge_boundary) then
            print *, '>>> STAGE 11.8.0 T3-CORRECTIVE-3 physics branch: ', &
                'RO_PROGNOSTIC=', s118_ro_prognostic, &
                ' CA_POTENTIAL=', s118_ca_potential, &
                ' CA_F64_N2=', s118_ca_f64_n2, &
                ' SPONGE=', s118_boundary_sponge, ' KEEP_TW=', s118_t3_keep_tw, &
                ' LAP_VISC=', s118_lap_visc, ' AH=', s118_ah_m2s, &
                ' WIND_ROT=', s118_wind_rotation, ' LON_CLAMP=', s118_lon_clamp, &
                ' MONOTONE=', s118_monotone_advection, ' SPONGE_BND=', s118_sponge_boundary, &
                ' ALPHA=', s118_sponge_alpha
        else
            print *, '>>> STAGE 11.8.0 T3-CORRECTIVE-3 physics branch: LEGACY-FROZEN (all switches OFF)'
        end if
    end subroutine s118_init

end module stage118_physics_switches
