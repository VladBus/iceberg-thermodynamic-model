! ==============================================================================
! Модуль: voxel_iceberg (Stage 12.3)
! Назначение: воксельное представление айсберга — 3-D сетка с температурой T и
!             долей льда phi; вывод массы/осадки/площадей по Архимеду; шаг
!             теплопроводности + приграничных потоков + геометрической эрозии
!             (удаление ячеек phi<phi_min) + динамический ватерлейн. One-way:
!             океан/атмосфера заданы извне (D-51).
! Единицы: SI. Спека: docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf.
! Open items см. voxel_thermal_solver (turbulent γ_S, cavity/spray, u_rel, Tf·p).
! ==============================================================================
module voxel_iceberg
    use iceberg_types, only: RHO_ICE, RHO_WATER, C_ICE, K_ICE, LATENT_HEAT
    use voxel_thermal_solver, only: solve_heat_conduction, apply_boundary_fluxes
    implicit none

    private
    public :: voxel_iceberg_type, voxel_iceberg_init
    public :: voxel_iceberg_step, voxel_iceberg_get_mass
    public :: voxel_iceberg_get_draft, voxel_iceberg_get_areas
    public :: voxel_iceberg_get_melt, voxel_iceberg_compute_state

    real(8), parameter :: EPS_PHI = 1.0d-12
    real(8), parameter :: DEFAULT_PHI_MIN = 0.01d0

    type :: voxel_iceberg_type
        integer :: nx = 0, ny = 0, nz = 0
        real(8) :: dx = 0.0_8, dy = 0.0_8, dz = 0.0_8
        real(8) :: phi_min = DEFAULT_PHI_MIN
        real(8), allocatable :: T(:,:,:)
        real(8), allocatable :: phi(:,:,:)
        logical, allocatable :: submerged_mask(:,:,:)
        logical, allocatable :: exposed_mask(:,:,:)
        real(8) :: total_mass = 0.0_8
        real(8) :: draft = 0.0_8
        real(8) :: freeboard = 0.0_8
        real(8) :: waterline_area = 0.0_8
        real(8) :: submerged_area = 0.0_8
        real(8) :: exposed_area = 0.0_8
        real(8) :: basal_melt_rate = 0.0_8
        real(8) :: lateral_melt_rate = 0.0_8
        real(8) :: surface_melt_rate = 0.0_8
    end type voxel_iceberg_type

contains

    subroutine voxel_iceberg_init(vox, nx, ny, nz, dx, dy, dz, T_init, phi_init, phi_min)
        type(voxel_iceberg_type), intent(out) :: vox
        integer, intent(in) :: nx, ny, nz
        real(8), intent(in) :: dx, dy, dz
        real(8), intent(in) :: T_init, phi_init
        real(8), intent(in), optional :: phi_min

        vox%nx = nx; vox%ny = ny; vox%nz = nz
        vox%dx = dx; vox%dy = dy; vox%dz = dz
        vox%phi_min = DEFAULT_PHI_MIN
        if (present(phi_min)) vox%phi_min = phi_min

        allocate (vox%T(nx, ny, nz), vox%phi(nx, ny, nz))
        allocate (vox%submerged_mask(nx, ny, nz), vox%exposed_mask(nx, ny, nz))
        vox%T = T_init
        vox%phi = min(max(phi_init, 0.0_8), 1.0_8)
        vox%basal_melt_rate = 0.0_8
        vox%lateral_melt_rate = 0.0_8
        vox%surface_melt_rate = 0.0_8
        call voxel_iceberg_compute_state(vox)
    end subroutine voxel_iceberg_init

    ! ==========================================================================
    ! Производные: mass, waterline (Архимед), маски, площади.
    ! ==========================================================================
    subroutine voxel_iceberg_compute_state(vox)
        type(voxel_iceberg_type), intent(inout) :: vox
        integer :: i, j, k
        real(8) :: cell_vol, solid_vol, v_sub, zw, cnt_wl, s_area, e_area

        cell_vol = vox%dx*vox%dy*vox%dz
        vox%total_mass = 0.0_8
        solid_vol = 0.0_8
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI) then
                        vox%total_mass = vox%total_mass + vox%phi(i, j, k)*real(RHO_ICE, 8)*cell_vol
                        solid_vol = solid_vol + cell_vol
                    end if
                end do
            end do
        end do

        if (vox%total_mass <= 0.0_8 .or. solid_vol <= 0.0_8) then
            vox%draft = 0.0_8; vox%freeboard = 0.0_8
            vox%waterline_area = 0.0_8; vox%submerged_area = 0.0_8; vox%exposed_area = 0.0_8
            vox%submerged_mask = .false.; vox%exposed_mask = .false.
            return
        end if

        v_sub = vox%total_mass/real(RHO_WATER, 8)
        zw = solid_height_for_submerged_vol(vox, v_sub, cell_vol)
        vox%draft = min(zw, vox%dz*real(vox%nz, 8))
        vox%freeboard = max(0.0_8, vox%dz*real(vox%nz, 8) - vox%draft)

        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) then
                        vox%submerged_mask(i, j, k) = .false.
                        vox%exposed_mask(i, j, k) = .false.
                    else if ((real(k, 8) - 0.5_8)*vox%dz < vox%draft) then
                        vox%submerged_mask(i, j, k) = .true.
                        vox%exposed_mask(i, j, k) = .false.
                    else
                        vox%submerged_mask(i, j, k) = .false.
                        vox%exposed_mask(i, j, k) = .true.
                    end if
                end do
            end do
        end do

        cnt_wl = 0.0_8
        do k = 1, vox%nz
            if ((real(k, 8) - 1.0_8)*vox%dz < vox%draft .and. real(k, 8)*vox%dz > vox%draft) then
                do j = 1, vox%ny
                    do i = 1, vox%nx
                        if (vox%phi(i, j, k) > EPS_PHI) cnt_wl = cnt_wl + 1.0_8
                    end do
                end do
            end if
        end do
        if (cnt_wl <= 0.0_8) cnt_wl = 1.0_8
        vox%waterline_area = cnt_wl*vox%dx*vox%dy

        s_area = 0.0_8; e_area = 0.0_8
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    if (vox%submerged_mask(i, j, k)) then
                        s_area = s_area + boundary_face_area(vox, i, j, k)
                    else
                        e_area = e_area + boundary_face_area(vox, i, j, k)
                    end if
                end do
            end do
        end do
        vox%submerged_area = s_area
        vox%exposed_area = e_area
    end subroutine voxel_iceberg_compute_state

    real(8) function boundary_face_area(vox, i, j, k) result(a)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(in) :: i, j, k
        integer :: d, di(6), dj(6), dk(6)
        real(8) :: fa(6)
        di = (/ 1, -1, 0, 0, 0, 0 /)
        dj = (/ 0, 0, 1, -1, 0, 0 /)
        dk = (/ 0, 0, 0, 0, 1, -1 /)
        fa(1) = vox%dy*vox%dz; fa(2) = vox%dy*vox%dz
        fa(3) = vox%dx*vox%dz; fa(4) = vox%dx*vox%dz
        fa(5) = vox%dx*vox%dy; fa(6) = vox%dx*vox%dy
        a = 0.0_8
        do d = 1, 6
            if (empty_or_outside(vox, i + di(d), j + dj(d), k + dk(d))) a = a + fa(d)
        end do
    end function boundary_face_area

    pure logical function empty_or_outside(vox, i, j, k)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(in) :: i, j, k
        if (i < 1 .or. j < 1 .or. k < 1 .or. &
            i > vox%nx .or. j > vox%ny .or. k > vox%nz) then
            empty_or_outside = .true.
        else
            empty_or_outside = (vox%phi(i, j, k) <= EPS_PHI)
        end if
    end function empty_or_outside

    real(8) function solid_height_for_submerged_vol(vox, v_sub, cell_vol) result(zw)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(in) :: v_sub, cell_vol
        integer :: i, j, k
        real(8) :: cum, level_vol, nlev
        zw = 0.0_8; cum = 0.0_8
        do k = 1, vox%nz
            nlev = 0.0_8
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI) nlev = nlev + 1.0_8
                end do
            end do
            level_vol = nlev*cell_vol
            if (cum + level_vol >= v_sub .and. level_vol > 0.0_8) then
                zw = (real(k, 8) - 1.0_8 + (v_sub - cum)/level_vol)*vox%dz
                return
            end if
            cum = cum + level_vol
        end do
        zw = real(vox%nz, 8)*vox%dz
    end function solid_height_for_submerged_vol

    ! ==========================================================================
    ! Один шаг: диффузия → приграничные потоки → удаление → пересчёт.
    ! ==========================================================================
    subroutine voxel_iceberg_step(vox, dt, ocean_T, ocean_S, ocean_u, ocean_v, &
                                  atmos_T, atmos_Q, atmos_wind, &
                                  basal_melt, lateral_melt, surface_melt)
        type(voxel_iceberg_type), intent(inout) :: vox
        real(8), intent(in) :: dt
        real(8), intent(in) :: ocean_T, ocean_S, ocean_u, ocean_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        real(8), intent(out) :: basal_melt, lateral_melt, surface_melt
        integer :: i, j, k
        real(8), allocatable :: Tn(:,:,:), pn(:,:,:)
        real(8) :: rho_ice8, c_ice8, k_ice8, l_fus8

        basal_melt = 0.0_8; lateral_melt = 0.0_8; surface_melt = 0.0_8
        if (.not. allocated(vox%T)) return
        rho_ice8 = real(RHO_ICE, 8); c_ice8 = real(C_ICE, 8)
        k_ice8 = real(K_ICE, 8); l_fus8 = real(LATENT_HEAT, 8)
        allocate (Tn(vox%nx, vox%ny, vox%nz), pn(vox%nx, vox%ny, vox%nz))

        call solve_heat_conduction(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, &
                                   k_ice8, rho_ice8, c_ice8, l_fus8, Tn, pn)
        vox%T = Tn; vox%phi = pn

        call apply_boundary_fluxes(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, &
                                   ocean_T, ocean_S, ocean_u, ocean_v, &
                                   atmos_T, atmos_Q, atmos_wind, &
                                   vox%submerged_mask, vox%exposed_mask, &
                                   basal_melt, lateral_melt, surface_melt)

        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) < vox%phi_min) vox%phi(i, j, k) = 0.0_8
                end do
            end do
        end do
        deallocate (Tn, pn)

        call voxel_iceberg_compute_state(vox)
        vox%basal_melt_rate = basal_melt
        vox%lateral_melt_rate = lateral_melt
        vox%surface_melt_rate = surface_melt
    end subroutine voxel_iceberg_step

    subroutine voxel_iceberg_get_mass(vox, mass)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: mass
        mass = vox%total_mass
    end subroutine voxel_iceberg_get_mass

    subroutine voxel_iceberg_get_draft(vox, draft)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: draft
        draft = vox%draft
    end subroutine voxel_iceberg_get_draft

    subroutine voxel_iceberg_get_areas(vox, waterline_area, submerged_area, exposed_area)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: waterline_area, submerged_area, exposed_area
        waterline_area = vox%waterline_area
        submerged_area = vox%submerged_area
        exposed_area = vox%exposed_area
    end subroutine voxel_iceberg_get_areas

    subroutine voxel_iceberg_get_melt(vox, basal, lateral, surface)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: basal, lateral, surface
        basal = vox%basal_melt_rate
        lateral = vox%lateral_melt_rate
        surface = vox%surface_melt_rate
    end subroutine voxel_iceberg_get_melt

end module voxel_iceberg
