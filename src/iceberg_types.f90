! ==============================================================================
! Модуль: iceberg_types
! Назначение: Базовые типы и константы для модели айсберга.
!             Выделен в отдельный модуль для разрыва циклических зависимостей.
! ==============================================================================

module iceberg_types
    implicit none

    ! ========================================================================
    !   КОНСТАНТЫ (Stage 9.1 §6, §23)
    ! ========================================================================
    real, parameter :: RHO_ICE = 910.0
    real, parameter :: RHO_WATER = 1028.0
    real, parameter :: RHO_AIR = 1.225
    real, parameter :: LATENT_HEAT = 334000.0
    real, parameter :: CP_WATER = 4186.8
    real, parameter :: GRAVITY = 9.80665

    real, parameter :: CD_AIR = 1.3e-3
    real, parameter :: CD_WATER = 2.0e-3

    real, parameter :: C_BASAL = 1.0e-6
    real, parameter :: C_LATERAL = 1.0e-6

    real, parameter :: ALBEDO_ICE = 0.7
    real, parameter :: EMISSIVITY = 0.97
    real, parameter :: STEFAN_BOLTZ = 5.670374419e-8

    real, parameter :: T_ICE = -10.0
    real, parameter :: MIN_THICKNESS = 1.0

    real, parameter :: OMEGA = 7.2921150e-5

    ! ========================================================================
    !   ТИПЫ СОСТОЯНИЯ
    ! ========================================================================

    type :: ocean_profile
        integer :: nlevels
        real, allocatable :: z(:)
        real, allocatable :: dz(:)
        real, allocatable :: temp(:)
        real, allocatable :: salt(:)
        real, allocatable :: u(:)
        real, allocatable :: v(:)
    end type ocean_profile

    type :: atmos_forcing
        real :: u10
        real :: v10
        real :: t2m
        real :: d2m
        real :: tcc
        real :: msl
        real :: snowfall
    end type atmos_forcing

    type :: iceberg_diagnostics
        real :: mass
        real :: draft
        real :: freeboard
        real :: a_waterline
        real :: a_wet
        real :: a_sail

        real :: m_basal
        real :: m_lateral
        real :: m_surface
        real :: q_net_surface
        real :: t_draft
        real :: s_draft
        real :: tf_draft

        real :: f_wind_x
        real :: f_wind_y
        real :: f_water_x
        real :: f_water_y
        real :: f_cor_x
        real :: f_cor_y
        real :: f_pressure_x
        real :: f_pressure_y
        real :: f_fk_x
        real :: f_fk_y

        logical :: grounded
        real :: bathymetry

        real :: basal_mass_loss
        real :: lateral_mass_loss
        real :: surface_mass_loss
        real :: total_mass_loss
    end type iceberg_diagnostics

    type :: iceberg_state
        real :: x
        real :: y
        real :: u
        real :: v
        real :: L
        real :: W
        real :: H

        real :: latitude
        real :: longitude
        integer :: nstep
        real :: time
        logical :: active
        logical :: grounded
    end type iceberg_state

    public :: RHO_ICE, RHO_WATER, RHO_AIR, LATENT_HEAT, CP_WATER, GRAVITY
    public :: CD_AIR, CD_WATER
    public :: C_BASAL, C_LATERAL
    public :: ALBEDO_ICE, EMISSIVITY, STEFAN_BOLTZ
    public :: T_ICE, MIN_THICKNESS
    public :: OMEGA
    public :: ocean_profile, atmos_forcing, iceberg_diagnostics, iceberg_state

end module iceberg_types
