! ==============================================================================
! Модуль: voxel_iceberg (Stage 12.4, PART A)
! Назначение: воксельный айсберг — сетка T/phi; Архимедова ватерлиния; шаг:
!   (1) состояние; (2) граничные величины из T^n; (3) CN-проводимость
!   (theta-схема, PCG) или явная схема; (4) ОДИН энтальпийный clamp;
!   (5) приграничное таяние с cap (VOXEL_MELT_CAP); (6) эрозия+flush
!   (перенос чувствительного тепла соседям, PDF 9.3); (7) пересчёт.
!   Rannacher: 2 шага backward Euler после изменения геометрии.
! m >= 0 (spec A5). real(8) внутри. VOXEL_ENABLED default OFF (см.
! iceberg_thermodynamics).
! ==============================================================================
module voxel_iceberg
    use iceberg_types, only: RHO_ICE, RHO_WATER, C_ICE, K_ICE, LATENT_HEAT, &
                             ocean_freezing_point, ocean_heat_transfer_coeff, &
                             ocean_profile, THREE_EQ_KT, THREE_EQ_KS
    use voxel_thermal_solver, only: solve_heat_conduction, apply_boundary_fluxes, &
                                    solve_cn, face_h, face_area, voxel_face_dphi, &
                                    three_equation_melt, profile_at, voxel_kt_scale
    implicit none

    private
    public :: voxel_iceberg_type, voxel_iceberg_init
    public :: voxel_iceberg_step, voxel_iceberg_get_mass
    public :: voxel_iceberg_get_draft, voxel_iceberg_get_areas
    public :: voxel_iceberg_get_melt, voxel_iceberg_compute_state
    public :: voxel_iceberg_get_flush, voxel_iceberg_get_solver
    public :: voxel_iceberg_get_clamp_mass
    public :: voxel_iceberg_step_profile, voxel_iceberg_get_stefan
    public :: voxel_iceberg_get_frontal_area, voxel_iceberg_get_stability
    public :: voxel_iceberg_get_layer_areas
    public :: voxel_iceberg_get_grid, voxel_iceberg_get_fields
    public :: voxel_iceberg_get_energy, voxel_iceberg_get_freeboard
    public :: voxel_iceberg_get_boundary_energy, voxel_iceberg_get_melt_sensible_energy
    public :: voxel_iceberg_get_top_height, voxel_iceberg_get_cumulative_losses
    public :: voxel_iceberg_set_c_ice, voxel_iceberg_compact_vertical

    real(8), parameter :: EPS_PHI = 1.0d-12
    real(8), save :: c_ice_override = real(C_ICE, 8)
    real(8), parameter :: DEFAULT_PHI_MIN = 0.01d0
    logical, save :: dbg_melt = .false., dbg_checked = .false., dbg_face_done = .false., dbg_total_done = .false.

    type :: voxel_iceberg_type
        integer :: nx = 0, ny = 0, nz = 0
        real(8) :: dx = 0.0_8, dy = 0.0_8, dz = 0.0_8
        real(8) :: phi_min = DEFAULT_PHI_MIN
        real(8), allocatable :: T(:,:,:)
        real(8), allocatable :: phi(:,:,:)
        logical, allocatable :: submerged_mask(:,:,:)
        logical, allocatable :: exposed_mask(:,:,:)
        ! Empty cells connected to the exterior (6-neighbour flood fill).
        logical, allocatable :: open_mask(:,:,:)
        ! Per solid voxel/face: face is adjacent to an exterior empty cell.
        logical, allocatable :: open_face(:,:,:,:)
        ! Per solid voxel/face: local three-equation interface temperature.
        real(8), allocatable :: tb_face(:,:,:,:)
        ! Per solid voxel/face and voxel mean: interface salinity.
        real(8), allocatable :: sb_face(:,:,:,:)
        real(8), allocatable :: sb_vox(:,:,:)

        ! конфигурация (env задаётся в iceberg_thermodynamics)
        integer :: scheme = 1          ! 1=cn, 2=explicit (12.3 legacy)
        real(8) :: theta = 0.5_8
        real(8) :: cg_tol = 1.0d-10
        integer :: cg_maxit = 1000
        real(8) :: melt_cap = 0.20_8
        integer :: rannacher_left = 0

        ! TEST-ONLY Dirichlet faces (недостижимы из production)
        integer :: test_dir_face_a = 0, test_dir_face_b = 0
        real(8) :: test_dir_T_a = 0.0_8, test_dir_T_b = 0.0_8

        ! производные
        real(8) :: total_mass = 0.0_8
        real(8) :: draft = 0.0_8
        real(8) :: waterline_height = 0.0_8
        real(8) :: top_height = 0.0_8
        real(8) :: freeboard = 0.0_8
        real(8) :: waterline_area = 0.0_8
        real(8) :: submerged_area = 0.0_8
        real(8) :: exposed_area = 0.0_8

        ! диагностика/бюджеты последнего шага
        real(8) :: basal_melt_rate = 0.0_8
        real(8) :: lateral_melt_rate = 0.0_8
        real(8) :: surface_melt_rate = 0.0_8
        integer :: cg_iters = 0
        real(8) :: cg_resid = 0.0_8
        integer :: clip_events = 0
        real(8) :: flushed_mass = 0.0_8
        real(8) :: flushed_energy = 0.0_8
        real(8) :: cum_boundary_sub_energy = 0.0_8
        real(8) :: cum_boundary_air_energy = 0.0_8
        real(8) :: cum_boundary_test_energy = 0.0_8
        real(8) :: cum_melt_sensible_energy = 0.0_8
        real(8) :: clamp_melt_mass = 0.0_8
        real(8) :: cum_basal_mass = 0.0_8
        real(8) :: cum_lateral_mass = 0.0_8
        real(8) :: cum_surface_mass = 0.0_8
        real(8) :: cum_flush_mass = 0.0_8
        ! Part B diagnostics
        real(8) :: stefan_mean_tb = 0.0_8, stefan_mean_sb = 0.0_8, stefan_mean_urel = 0.0_8
        real(8) :: stefan_deep_tb = 0.0_8, stefan_wl_tb = 0.0_8
        integer :: stefan_faces = 0
        logical :: stefan_conv = .false.
    end type voxel_iceberg_type

contains

    subroutine voxel_iceberg_set_c_ice(value)
        real(8), intent(in) :: value
        if (value > 0.0_8) c_ice_override = value
    end subroutine voxel_iceberg_set_c_ice

    subroutine voxel_iceberg_init(vox, nx, ny, nz, dx, dy, dz, T_init, phi_init, &
                                  phi_min, scheme, theta, cg_tol, cg_maxit, melt_cap, &
                                  test_dir_face_a, test_dir_face_b, test_dir_T_a, test_dir_T_b)
        type(voxel_iceberg_type), intent(out) :: vox
        integer, intent(in) :: nx, ny, nz
        real(8), intent(in) :: dx, dy, dz, T_init, phi_init
        real(8), intent(in), optional :: phi_min, theta, cg_tol, melt_cap
        integer, intent(in), optional :: scheme, cg_maxit, test_dir_face_a, test_dir_face_b
        real(8), intent(in), optional :: test_dir_T_a, test_dir_T_b

        vox%nx = nx; vox%ny = ny; vox%nz = nz
        vox%dx = dx; vox%dy = dy; vox%dz = dz
        vox%phi_min = DEFAULT_PHI_MIN; if (present(phi_min)) vox%phi_min = phi_min
        if (present(scheme)) vox%scheme = scheme
        if (present(theta)) vox%theta = theta
        if (present(cg_tol)) vox%cg_tol = cg_tol
        if (present(cg_maxit)) vox%cg_maxit = cg_maxit
        if (present(melt_cap)) vox%melt_cap = melt_cap
        if (present(test_dir_face_a)) vox%test_dir_face_a = test_dir_face_a
        if (present(test_dir_face_b)) vox%test_dir_face_b = test_dir_face_b
        if (present(test_dir_T_a)) vox%test_dir_T_a = test_dir_T_a
        if (present(test_dir_T_b)) vox%test_dir_T_b = test_dir_T_b

        allocate (vox%T(nx, ny, nz), vox%phi(nx, ny, nz))
        allocate (vox%submerged_mask(nx, ny, nz), vox%exposed_mask(nx, ny, nz))
        allocate (vox%open_mask(nx, ny, nz), vox%open_face(nx, ny, nz, 6))
        allocate (vox%tb_face(nx, ny, nz, 6))
        allocate (vox%sb_face(nx, ny, nz, 6), vox%sb_vox(nx, ny, nz))
        vox%T = T_init
        vox%phi = min(max(phi_init, 0.0_8), 1.0_8)
        vox%open_mask = .false.; vox%open_face = .false.; vox%tb_face = 0.0_8
        vox%sb_face = 0.0_8; vox%sb_vox = 0.0_8
        vox%rannacher_left = 0
        vox%basal_melt_rate = 0.0_8; vox%lateral_melt_rate = 0.0_8; vox%surface_melt_rate = 0.0_8
        vox%cg_iters = 0; vox%cg_resid = 0.0_8; vox%clip_events = 0
        vox%flushed_mass = 0.0_8; vox%flushed_energy = 0.0_8; vox%clamp_melt_mass = 0.0_8
        vox%cum_boundary_sub_energy = 0.0_8; vox%cum_boundary_air_energy = 0.0_8
        vox%cum_boundary_test_energy = 0.0_8
        vox%cum_melt_sensible_energy = 0.0_8
        vox%cum_basal_mass = 0.0_8; vox%cum_lateral_mass = 0.0_8
        vox%cum_surface_mass = 0.0_8; vox%cum_flush_mass = 0.0_8
        call voxel_iceberg_compute_state(vox)
    end subroutine voxel_iceberg_init

    ! ==========================================================================
    subroutine voxel_iceberg_compute_state(vox)
        type(voxel_iceberg_type), intent(inout) :: vox
        integer :: i, j, k
        real(8) :: cell_vol, solid_vol, v_sub, zw, cnt_wl, s_area, e_area, solid_top, bottom_height

        cell_vol = vox%dx*vox%dy*vox%dz
        vox%total_mass = 0.0_8; solid_vol = 0.0_8
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
            vox%draft = 0.0_8; vox%waterline_height = 0.0_8
            vox%top_height = 0.0_8; vox%freeboard = 0.0_8
            vox%waterline_area = 0.0_8; vox%submerged_area = 0.0_8; vox%exposed_area = 0.0_8
            vox%submerged_mask = .false.; vox%exposed_mask = .false.
            if (allocated(vox%open_mask)) vox%open_mask = .false.
            if (allocated(vox%open_face)) vox%open_face = .false.
            return
        end if
        v_sub = vox%total_mass/real(RHO_WATER, 8)
        zw = solid_height_for_submerged_vol(vox, v_sub, cell_vol)
        vox%waterline_height = min(zw, vox%dz*real(vox%nz, 8))
        ! Actual upper and lower solid surfaces.
        solid_top = 0.0_8
        bottom_height = vox%dz*real(vox%nz, 8)
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    ! phi is an ice volume fraction, not a vertical height;
                    ! the cell top remains k*dz while any ice remains in it.
                    solid_top = max(solid_top, real(k, 8)*vox%dz)
                    bottom_height = min(bottom_height, real(k - 1, 8)*vox%dz)
                end do
            end do
        end do
        if (solid_top <= 0.0_8) bottom_height = 0.0_8
        vox%top_height = solid_top
        vox%draft = max(0.0_8, vox%waterline_height - bottom_height)
        vox%freeboard = max(0.0_8, solid_top - vox%waterline_height)

        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) then
                        vox%submerged_mask(i, j, k) = .false.; vox%exposed_mask(i, j, k) = .false.
                    else if ((real(k, 8) - 0.5_8)*vox%dz < vox%waterline_height) then
                        vox%submerged_mask(i, j, k) = .true.; vox%exposed_mask(i, j, k) = .false.
                    else
                        vox%submerged_mask(i, j, k) = .false.; vox%exposed_mask(i, j, k) = .true.
                    end if
                end do
            end do
        end do
        call classify_open_cells(vox)

        cnt_wl = 0.0_8
        do k = 1, vox%nz
            if ((real(k, 8) - 1.0_8)*vox%dz < vox%waterline_height .and. &
                real(k, 8)*vox%dz > vox%waterline_height) then
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

    ! ==========================================================================
    ! Classify empty cells connected to the exterior (six-neighbour BFS), then
    ! mark the solid faces that actually exchange with the exterior. Isolated
    ! internal cavities are not exposed to ocean/atmosphere boundary conditions.
    ! ==========================================================================
    subroutine classify_open_cells(vox)
        type(voxel_iceberg_type), intent(inout) :: vox
        integer :: i, j, k, d, ii, jj, kk, head, tail, ncell
        integer, allocatable :: q(:,:)
        integer :: di(6), dj(6), dk(6)
        di = (/ 1, -1, 0, 0, 0, 0 /); dj = (/ 0, 0, 1, -1, 0, 0 /); dk = (/ 0, 0, 0, 0, 1, -1 /)

        vox%open_mask = .false.
        vox%open_face = .false.
        ncell = vox%nx*vox%ny*vox%nz
        allocate (q(3, ncell))
        head = 1; tail = 0

        ! Seed empty cells on the domain boundary.
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (.not. (i == 1 .or. i == vox%nx .or. j == 1 .or. j == vox%ny .or. &
                               k == 1 .or. k == vox%nz)) cycle
                    if (vox%phi(i, j, k) > EPS_PHI) cycle
                    if (vox%open_mask(i, j, k)) cycle
                    vox%open_mask(i, j, k) = .true.
                    tail = tail + 1
                    q(1, tail) = i; q(2, tail) = j; q(3, tail) = k
                end do
            end do
        end do

        ! Flood-fill through empty cells.
        do while (head <= tail)
            i = q(1, head); j = q(2, head); k = q(3, head)
            do d = 1, 6
                ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
                if (ii < 1 .or. ii > vox%nx .or. jj < 1 .or. jj > vox%ny .or. &
                    kk < 1 .or. kk > vox%nz) cycle
                if (vox%phi(ii, jj, kk) > EPS_PHI) cycle
                if (vox%open_mask(ii, jj, kk)) cycle
                vox%open_mask(ii, jj, kk) = .true.
                tail = tail + 1
                q(1, tail) = ii; q(2, tail) = jj; q(3, tail) = kk
            end do
            head = head + 1
        end do
        deallocate (q)

        ! Solid faces adjacent to an exterior empty cell (or domain boundary).
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    do d = 1, 6
                        ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
                        vox%open_face(i, j, k, d) = open_empty_or_outside(vox, ii, jj, kk)
                    end do
                end do
            end do
        end do
    end subroutine classify_open_cells

    real(8) function boundary_face_area(vox, i, j, k) result(a)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(in) :: i, j, k
        integer :: d
        real(8) :: fa(6)
        fa(1) = vox%dy*vox%dz; fa(2) = vox%dy*vox%dz
        fa(3) = vox%dx*vox%dz; fa(4) = vox%dx*vox%dz
        fa(5) = vox%dx*vox%dy; fa(6) = vox%dx*vox%dy
        a = 0.0_8
        do d = 1, 6
            if (vox%open_face(i, j, k, d)) a = a + fa(d)
        end do
    end function boundary_face_area

    pure logical function open_empty_or_outside(vox, i, j, k)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(in) :: i, j, k
        if (i < 1 .or. j < 1 .or. k < 1 .or. i > vox%nx .or. j > vox%ny .or. k > vox%nz) then
            open_empty_or_outside = .true.
        else if (vox%phi(i, j, k) > EPS_PHI) then
            open_empty_or_outside = .false.
        else if (.not. allocated(vox%open_mask)) then
            open_empty_or_outside = .false.
        else
            open_empty_or_outside = vox%open_mask(i, j, k)
        end if
    end function open_empty_or_outside

    real(8) function solid_height_for_submerged_vol(vox, v_sub, cell_vol) result(zw)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(in) :: v_sub, cell_vol
        integer :: i, j, k
        real(8) :: cum, level_vol
        zw = 0.0_8; cum = 0.0_8
        do k = 1, vox%nz
            ! Use the actual ice volume fraction, not the number of non-empty cells.
            level_vol = 0.0_8
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI) &
                        level_vol = level_vol + vox%phi(i, j, k)*cell_vol
                end do
            end do
            if (cum + level_vol >= v_sub .and. level_vol > 0.0_8) then
                zw = (real(k, 8) - 1.0_8 + (v_sub - cum)/level_vol)*vox%dz
                return
            end if
            cum = cum + level_vol
        end do
        zw = real(vox%nz, 8)*vox%dz
    end function solid_height_for_submerged_vol

    ! ==========================================================================
    ! Граничное таяние Part A: m = max(0, gamma*ΔT/(rho L)) на каждой грани,
    ! T_b=Tf(S,P) на глубине грани; dmelt — суммарная доля льда, потерянная
    ! ячейкой за шаг (с учётом h_norm каждой грани, A5).
    ! ==========================================================================
    subroutine compute_face_melt(vox, ocean_T, ocean_S, ocean_u, ocean_v, dt, &
                                 dmelt, dbasal, dlat)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(in) :: ocean_T, ocean_S, ocean_u, ocean_v, dt
        real(8), intent(out) :: dmelt(:,:,:), dbasal(:,:,:), dlat(:,:,:)
        integer :: i, j, k, d
        real(8) :: u_rel, l_char, gamma, zf, dface, tf, m, hn, A, mr
        real :: gt_r

        dmelt = 0.0_8; dbasal = 0.0_8; dlat = 0.0_8
        u_rel = sqrt(ocean_u*ocean_u + ocean_v*ocean_v)
        if (u_rel <= 0.0d0) return
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (.not. vox%submerged_mask(i, j, k)) cycle
                    zf = (real(k, 8) - 0.5_8)*vox%dz
                    dface = max(0.0_8, vox%waterline_height - zf)
                    tf = real(ocean_freezing_point(real(ocean_S), real(dface)), 8)
                    do d = 1, 6
                        if (.not. vox%open_face(i, j, k, d)) cycle
                        ! per-face characteristic length (12.3 defect #3)
                        if (d >= 5) then
                            l_char = max(real(vox%nx, 8)*vox%dx, real(vox%ny, 8)*vox%dy)
                        else
                            l_char = max(vox%draft, vox%dz)
                        end if
                        gt_r = 0.0
                        call ocean_heat_transfer_coeff(real(u_rel), real(l_char), gt_r)
                        gamma = max(real(gt_r, 8), 0.0d0)
                        m = max(0.0_8, gamma*(ocean_T - tf)/ &
                                (real(RHO_ICE, 8)*real(LATENT_HEAT, 8)))   ! m>=0 (A5)
                        if (m <= 0.0d0) cycle
                        hn = face_h(d, vox%dx, vox%dy, vox%dz)
                        A = face_area(d, vox%dx, vox%dy, vox%dz)
                        dmelt(i, j, k) = dmelt(i, j, k) + m*dt/hn          ! A5 h_norm
                        mr = real(RHO_ICE, 8)*A*m*dt
                        if (d >= 5) then
                            dbasal(i, j, k) = dbasal(i, j, k) + mr
                        else
                            dlat(i, j, k) = dlat(i, j, k) + mr
                        end if
                    end do
                end do
            end do
        end do
    end subroutine compute_face_melt

    ! ==========================================================================
    subroutine voxel_iceberg_step(vox, dt, ocean_T, ocean_S, ocean_u, ocean_v, &
                                  atmos_T, atmos_Q, atmos_wind, &
                                  basal_melt, lateral_melt, surface_melt)
        type(voxel_iceberg_type), intent(inout) :: vox
        real(8), intent(in) :: dt
        real(8), intent(in) :: ocean_T, ocean_S, ocean_u, ocean_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        real(8), intent(out) :: basal_melt, lateral_melt, surface_melt

        integer :: i, j, k, removed
        real(8), allocatable :: Tn(:,:,:), pn(:,:,:), dmelt(:,:,:), dbasal(:,:,:), dlat(:,:,:)
        real(8) :: rho8, c8, k8, lf8, theta_eff, capv, tot, scale, dphi, dm, V
        real(8) :: clamp_mass
        real(8) :: be(3)
        logical :: cn_conv

        basal_melt = 0.0_8; lateral_melt = 0.0_8; surface_melt = 0.0_8
        if (.not. dbg_checked) then
            block
                character(len=64) :: ev
                ev = ''
                call get_environment_variable('VOXEL_DEBUG_MELT', ev)
                dbg_melt = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
                dbg_checked = .true.
            end block
        end if
        if (.not. allocated(vox%T)) return
        rho8 = real(RHO_ICE, 8); c8 = c_ice_override; k8 = real(K_ICE, 8); lf8 = real(LATENT_HEAT, 8)
        V = vox%dx*vox%dy*vox%dz
        call voxel_iceberg_compute_state(vox)

        theta_eff = vox%theta
        if (vox%rannacher_left > 0) theta_eff = 1.0_8     ! Rannacher BE

        if (vox%scheme == 2) then
            ! ---- 12.3 явная схема (legacy) ----
            allocate (Tn(vox%nx, vox%ny, vox%nz), pn(vox%nx, vox%ny, vox%nz))
            call solve_heat_conduction(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, &
                                       k8, rho8, c8, lf8, Tn, pn)
            vox%T = Tn; vox%phi = pn
            call apply_boundary_fluxes(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, &
                                       ocean_T, ocean_S, ocean_u, ocean_v, &
                                       atmos_T, atmos_Q, atmos_wind, &
                                       vox%submerged_mask, vox%exposed_mask, &
                                       basal_melt, lateral_melt, surface_melt, vox%draft, &
                                       open_face=vox%open_face)
            deallocate (Tn, pn)
        else
            ! ---- Crank-Nicolson ----
            allocate (dmelt(vox%nx, vox%ny, vox%nz))
            allocate (dbasal(vox%nx, vox%ny, vox%nz), dlat(vox%nx, vox%ny, vox%nz))
            call compute_face_melt(vox, ocean_T, ocean_S, ocean_u, ocean_v, dt, &
                                   dmelt, dbasal, dlat)
            allocate (Tn(vox%nx, vox%ny, vox%nz))
            call solve_cn(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, k8, rho8, c8, &
                          theta_eff, vox%cg_tol, vox%cg_maxit, vox%draft, &
                          ocean_T, ocean_S, ocean_u, ocean_v, atmos_T, atmos_Q, atmos_wind, &
                          vox%submerged_mask, vox%exposed_mask, Tn, &
                          vox%cg_iters, vox%cg_resid, cn_conv, &
                          vox%test_dir_face_a, vox%test_dir_T_a, &
                          vox%test_dir_face_b, vox%test_dir_T_b, &
                          open_face=vox%open_face, boundary_energy=be)
            vox%T = Tn
            deallocate (Tn)
            vox%cum_boundary_sub_energy = vox%cum_boundary_sub_energy + be(1)
            vox%cum_boundary_air_energy = vox%cum_boundary_air_energy + be(2)
            vox%cum_boundary_test_energy = vox%cum_boundary_test_energy + be(3)

            ! (4) ОДИН энтальпийный clamp
            clamp_mass = 0.0_8
            do k = 1, vox%nz
                do j = 1, vox%ny
                    do i = 1, vox%nx
                        if (vox%T(i, j, k) > 0.0_8 .and. vox%phi(i, j, k) > EPS_PHI) then
                            dphi = vox%phi(i, j, k)*c8*vox%T(i, j, k)/lf8   ! energy-consistent
                            dm = min(dphi, vox%phi(i, j, k))
                            vox%phi(i, j, k) = vox%phi(i, j, k) - dm
                            clamp_mass = clamp_mass + dm*rho8*V
                            vox%T(i, j, k) = 0.0_8
                        end if
                    end do
                end do
            end do
            vox%clamp_melt_mass = clamp_mass
            surface_melt = surface_melt + clamp_mass/dt

            ! (5) приграничное таяние + cap (per-voxel scaling)
            vox%clip_events = 0
            basal_melt = 0.0_8; lateral_melt = 0.0_8
            do k = 1, vox%nz
                do j = 1, vox%ny
                    do i = 1, vox%nx
                        if (vox%phi(i, j, k) <= EPS_PHI) cycle
                        tot = dmelt(i, j, k)
                        if (tot <= 0.0_8) cycle
                        capv = vox%melt_cap*vox%phi(i, j, k)
                        if (tot > capv) then
                            if (capv > 0.0_8) then
                                scale = capv/tot
                                vox%clip_events = vox%clip_events + 1
                                dmelt(i, j, k) = capv
                                dbasal(i, j, k) = dbasal(i, j, k)*scale
                                dlat(i, j, k) = dlat(i, j, k)*scale
                            else
                                dmelt(i, j, k) = 0.0_8
                                dbasal(i, j, k) = 0.0_8
                                dlat(i, j, k) = 0.0_8
                            end if
                        end if
                        basal_melt = basal_melt + dbasal(i, j, k)
                        lateral_melt = lateral_melt + dlat(i, j, k)
                        vox%cum_melt_sensible_energy = vox%cum_melt_sensible_energy + &
                            c8*vox%T(i, j, k)*dmelt(i, j, k)*rho8*V
                        vox%phi(i, j, k) = max(0.0_8, vox%phi(i, j, k) - dmelt(i, j, k))
                    end do
                end do
            end do
            basal_melt = basal_melt/dt
            lateral_melt = lateral_melt/dt
            deallocate (dmelt, dbasal, dlat)
        end if

        ! (6) эрозия + flush (перенос чувствительного тепла соседям)
        removed = 0
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI .and. vox%phi(i, j, k) < vox%phi_min) then
                        call flush_voxel(vox, i, j, k, rho8, c8, lf8, V)
                        removed = removed + 1
                    end if
                end do
            end do
        end do
        if (removed > 0) vox%rannacher_left = 2
        if (vox%rannacher_left > 0 .and. removed == 0) vox%rannacher_left = max(0, vox%rannacher_left - 1)
        call voxel_iceberg_compact_vertical(vox)

        ! (7) пересчёт
        vox%basal_melt_rate = basal_melt
        vox%lateral_melt_rate = lateral_melt
        vox%surface_melt_rate = surface_melt
        vox%cum_basal_mass = vox%cum_basal_mass + basal_melt*dt
        vox%cum_lateral_mass = vox%cum_lateral_mass + lateral_melt*dt
        vox%cum_surface_mass = vox%cum_surface_mass + surface_melt*dt
        call voxel_iceberg_compute_state(vox)
        if (dbg_melt .and. .not. dbg_total_done) then
            block
                real(8) :: lv, wv, av
                lv = real(vox%nx, 8)*vox%dx; wv = real(vox%ny, 8)*vox%dy
                av = lv*wv + 2.0_8*(lv + wv)*vox%draft
                print '(a,10(1x,es14.6))', 'VOXEL_DEBUG_TOTAL', vox%submerged_area, av, &
                    vox%basal_melt_rate, vox%lateral_melt_rate, vox%surface_melt_rate, &
                    vox%draft, lv, wv, real(vox%nz, 8)*vox%dz, vox%total_mass
                print '(a,3(1x,es14.6))', 'VOXEL_DEBUG_MEAN', vox%stefan_mean_urel, &
                    vox%stefan_mean_tb, vox%stefan_mean_sb
            end block
            dbg_total_done = .true.
        end if
    end subroutine voxel_iceberg_step

    ! Перенос остаточной энергии при удалении (PDF 9.3 + сохранение Σ Cc·T).
    subroutine flush_voxel(vox, i, j, k, rho8, c8, lf8, V)
        type(voxel_iceberg_type), intent(inout) :: vox
        integer, intent(in) :: i, j, k
        real(8), intent(in) :: rho8, c8, lf8, V
        integer :: d, ii, jj, kk, cnt
        integer :: di(6), dj(6), dk(6)
        real(8) :: phit, Tt, dV, sens, share, Cnb
        di = (/ 1, -1, 0, 0, 0, 0 /); dj = (/ 0, 0, 1, -1, 0, 0 /); dk = (/ 0, 0, 0, 0, 1, -1 /)
        phit = vox%phi(i, j, k); Tt = vox%T(i, j, k)
        dV = phit*V
        vox%flushed_mass = vox%flushed_mass + dV*rho8
        vox%cum_flush_mass = vox%cum_flush_mass + dV*rho8
        vox%flushed_energy = vox%flushed_energy + dV*rho8*(c8*(0.0_8 - Tt) + lf8)
        sens = dV*rho8*c8*Tt          ! Tt<=0 → sens<=0 (охлаждение соседей)
        cnt = 0
        do d = 1, 6
            ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
            if (ii < 1 .or. ii > vox%nx .or. jj < 1 .or. jj > vox%ny .or. &
                kk < 1 .or. kk > vox%nz) cycle
            if (vox%phi(ii, jj, kk) < vox%phi_min .or. vox%phi(ii, jj, kk) <= EPS_PHI) cycle
            cnt = cnt + 1
        end do
        if (cnt > 0) then
            share = sens/real(cnt, 8)
            do d = 1, 6
                ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
                if (ii < 1 .or. ii > vox%nx .or. jj < 1 .or. jj > vox%ny .or. &
                    kk < 1 .or. kk > vox%nz) cycle
                if (vox%phi(ii, jj, kk) < vox%phi_min .or. vox%phi(ii, jj, kk) <= EPS_PHI) cycle
                Cnb = vox%phi(ii, jj, kk)*rho8*c8*V
                vox%T(ii, jj, kk) = vox%T(ii, jj, kk) + share/Cnb
            end do
        else
            vox%flushed_energy = vox%flushed_energy + sens
        end if
        vox%phi(i, j, k) = 0.0_8
    end subroutine flush_voxel

    ! ==========================================================================
    ! PART B: шаг с трёхуравненным интерфейсом по профилю океана.
    ! Per-face m_f, T_B, S_B на глубине грани; u_rel с учётом скорости айсберга.
    ! T_B поля подаются в CN-матрицу (tb_override).
    ! ==========================================================================
    subroutine voxel_iceberg_step_profile(vox, dt, prof, v_ice_u, v_ice_v, &
                                          atmos_T, atmos_Q, atmos_wind, &
                                          basal_melt, lateral_melt, surface_melt, &
                                          autonomous_air, air_sw_down, air_lw_down, &
                                          air_t_air, air_q_air, air_rho_air, air_p_atm)
        type(voxel_iceberg_type), intent(inout) :: vox
        real(8), intent(in) :: dt
        type(ocean_profile), intent(in) :: prof
        real(8), intent(in) :: v_ice_u, v_ice_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        real(8), intent(out) :: basal_melt, lateral_melt, surface_melt
        logical, intent(in), optional :: autonomous_air
        real(8), intent(in), optional :: air_sw_down, air_lw_down, air_t_air
        real(8), intent(in), optional :: air_q_air, air_rho_air, air_p_atm

        integer :: i, j, k, d, removed
        real(8), allocatable :: Tn(:,:,:), dmelt(:,:,:), dbasal(:,:,:), dlat(:,:,:)
        real(8) :: rho8, c8, k8, lf8, theta_eff, capv, tot, scale, dphi, dm, V
        real(8) :: tw, sw, uw, vw, urel, zf, dface, hn, A, m, tb, sb
        real(8) :: sum_tb, sum_sb, sum_urel, deep_depth, wl_depth
        real(8) :: clamp_mass
        real(8) :: be(3)
        logical :: ok3
        integer :: nface

        basal_melt = 0.0_8; lateral_melt = 0.0_8; surface_melt = 0.0_8
        if (.not. dbg_checked) then
            block
                character(len=64) :: ev
                ev = ''
                call get_environment_variable('VOXEL_DEBUG_MELT', ev)
                dbg_melt = (trim(ev) == 'true' .or. trim(ev) == 'TRUE' .or. trim(ev) == '1')
                dbg_checked = .true.
            end block
        end if
        if (.not. allocated(vox%T)) return
        rho8 = real(RHO_ICE, 8); c8 = c_ice_override; k8 = real(K_ICE, 8); lf8 = real(LATENT_HEAT, 8)
        V = vox%dx*vox%dy*vox%dz
        call voxel_iceberg_compute_state(vox)

        allocate (dmelt(vox%nx, vox%ny, vox%nz), dbasal(vox%nx, vox%ny, vox%nz), &
                  dlat(vox%nx, vox%ny, vox%nz))
        dmelt = 0.0_8; dbasal = 0.0_8; dlat = 0.0_8
        vox%tb_face = 0.0_8
        vox%sb_face = 0.0_8
        vox%sb_vox = 0.0_8
        sum_tb = 0.0_8; sum_sb = 0.0_8; sum_urel = 0.0_8; nface = 0
        deep_depth = -1.0_8; wl_depth = 1.0e30_8

        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (.not. vox%submerged_mask(i, j, k)) cycle
                    do d = 1, 6
                        if (.not. vox%open_face(i, j, k, d)) cycle
                        select case (d)
                        case (5); zf = real(k, 8)*vox%dz
                        case (6); zf = real(k - 1, 8)*vox%dz
                        case default; zf = (real(k, 8) - 0.5_8)*vox%dz
                        end select
                        dface = max(0.0_8, vox%waterline_height - zf)
                        call profile_at(prof, dface, tw, sw, uw, vw)
                        urel = sqrt((uw - v_ice_u)**2 + (vw - v_ice_v)**2)
                        hn = face_h(d, vox%dx, vox%dy, vox%dz)
                        A = face_area(d, vox%dx, vox%dy, vox%dz)
                        ! Local fallback if the three-equation solve is unavailable.
                        vox%tb_face(i, j, k, d) = real(ocean_freezing_point(real(sw), real(dface)), 8)
                        vox%sb_face(i, j, k, d) = sw
                        call three_equation_melt(tw, sw, urel, dface, hn, &
                                                 vox%T(i, j, k), m, tb, sb, ok3)
                        if (.not. ok3) cycle
                        vox%tb_face(i, j, k, d) = tb
                        vox%sb_face(i, j, k, d) = sb
                        if (dbg_melt .and. .not. dbg_face_done .and. d >= 5 .and. &
                            i == vox%nx/2 .and. j == vox%ny/2) then
                            print '(a,10(1x,es14.6))', 'VOXEL_DEBUG_FACE', tw, sw, urel, dface, &
                                real(ocean_freezing_point(real(sw), real(dface)), 8), &
                                real(THREE_EQ_KT, 8)*urel, real(THREE_EQ_KS, 8)*urel, tb, sb, m
                            print '(a,5(1x,es14.6))', 'VOXEL_DEBUG_FACE2', real(THREE_EQ_KT, 8)*urel*voxel_kt_scale(), &
                                real(THREE_EQ_KS, 8)*urel*voxel_kt_scale(), vox%T(i, j, k), hn, real(vox%draft, 8)
                            dbg_face_done = .true.
                        end if
                        dmelt(i, j, k) = dmelt(i, j, k) + m*dt/hn
                        if (d >= 5) then
                            dbasal(i, j, k) = dbasal(i, j, k) + rho8*A*m*dt
                        else
                            dlat(i, j, k) = dlat(i, j, k) + rho8*A*m*dt
                        end if
                        sum_tb = sum_tb + tb; sum_sb = sum_sb + sb; sum_urel = sum_urel + urel
                        nface = nface + 1
                        if (dface > deep_depth) then
                            deep_depth = dface; vox%stefan_deep_tb = tb
                        end if
                        if (dface < wl_depth) then
                            wl_depth = dface; vox%stefan_wl_tb = tb
                        end if
                    end do
                end do
            end do
        end do
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    block
                        real(8) :: ssum
                        integer :: scnt, dd
                        ssum = 0.0_8; scnt = 0
                        do dd = 1, 6
                            if (vox%open_face(i, j, k, dd) .and. vox%sb_face(i, j, k, dd) > 0.0_8) then
                                ssum = ssum + vox%sb_face(i, j, k, dd); scnt = scnt + 1
                            end if
                        end do
                        if (scnt > 0) vox%sb_vox(i, j, k) = ssum/real(scnt, 8)
                    end block
                end do
            end do
        end do
        if (nface > 0) then
            vox%stefan_mean_tb = sum_tb/real(nface, 8)
            vox%stefan_mean_sb = sum_sb/real(nface, 8)
            vox%stefan_mean_urel = sum_urel/real(nface, 8)
        else
            vox%stefan_mean_tb = 0.0_8; vox%stefan_mean_sb = 0.0_8; vox%stefan_mean_urel = 0.0_8
        end if
        vox%stefan_faces = nface

        theta_eff = vox%theta
        if (vox%rannacher_left > 0) theta_eff = 1.0_8
        allocate (Tn(vox%nx, vox%ny, vox%nz))
        call solve_cn(vox%T, vox%phi, vox%dx, vox%dy, vox%dz, dt, k8, rho8, c8, &
                      theta_eff, vox%cg_tol, vox%cg_maxit, vox%draft, &
                      0.0_8, 0.035_8, 0.0_8, 0.0_8, atmos_T, atmos_Q, atmos_wind, &
                      vox%submerged_mask, vox%exposed_mask, Tn, &
                      vox%cg_iters, vox%cg_resid, vox%stefan_conv, &
                      vox%test_dir_face_a, vox%test_dir_T_a, &
                      vox%test_dir_face_b, vox%test_dir_T_b, &
                      tb_face=vox%tb_face, open_face=vox%open_face, &
                      autonomous_air=autonomous_air, air_sw_down=air_sw_down, &
                      air_lw_down=air_lw_down, air_t_air=air_t_air, &
                      air_q_air=air_q_air, air_rho_air=air_rho_air, air_p_atm=air_p_atm, &
                      boundary_energy=be)
        vox%T = Tn
        deallocate (Tn)
        vox%cum_boundary_sub_energy = vox%cum_boundary_sub_energy + be(1)
        vox%cum_boundary_air_energy = vox%cum_boundary_air_energy + be(2)
        vox%cum_boundary_test_energy = vox%cum_boundary_test_energy + be(3)

        ! clamp (energy-consistent phi factor)
        clamp_mass = 0.0_8
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%T(i, j, k) > 0.0_8 .and. vox%phi(i, j, k) > EPS_PHI) then
                        dphi = vox%phi(i, j, k)*c8*vox%T(i, j, k)/lf8
                        dm = min(dphi, vox%phi(i, j, k))
                        vox%phi(i, j, k) = vox%phi(i, j, k) - dm
                        clamp_mass = clamp_mass + dm*rho8*V
                        vox%T(i, j, k) = 0.0_8
                    end if
                end do
            end do
        end do
        vox%clamp_melt_mass = clamp_mass
        surface_melt = clamp_mass/dt

        ! boundary melt + cap
        vox%clip_events = 0
        basal_melt = 0.0_8; lateral_melt = 0.0_8
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    tot = dmelt(i, j, k)
                    if (tot <= 0.0_8) cycle
                    capv = vox%melt_cap*vox%phi(i, j, k)
                    if (tot > capv) then
                        if (capv > 0.0_8) then
                            scale = capv/tot
                            vox%clip_events = vox%clip_events + 1
                            dmelt(i, j, k) = capv
                            dbasal(i, j, k) = dbasal(i, j, k)*scale
                            dlat(i, j, k) = dlat(i, j, k)*scale
                        else
                            dmelt(i, j, k) = 0.0_8; dbasal(i, j, k) = 0.0_8; dlat(i, j, k) = 0.0_8
                        end if
                    end if
                    basal_melt = basal_melt + dbasal(i, j, k)
                    lateral_melt = lateral_melt + dlat(i, j, k)
                    vox%cum_melt_sensible_energy = vox%cum_melt_sensible_energy + &
                        c8*vox%T(i, j, k)*dmelt(i, j, k)*rho8*V
                    vox%phi(i, j, k) = max(0.0_8, vox%phi(i, j, k) - dmelt(i, j, k))
                end do
            end do
        end do
        basal_melt = basal_melt/dt
        lateral_melt = lateral_melt/dt
        deallocate (dmelt, dbasal, dlat)

        ! erosion + flush + Rannacher
        removed = 0
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI .and. vox%phi(i, j, k) < vox%phi_min) then
                        call flush_voxel(vox, i, j, k, rho8, c8, lf8, V)
                        removed = removed + 1
                    end if
                end do
            end do
        end do
        if (removed > 0) vox%rannacher_left = 2
        if (vox%rannacher_left > 0 .and. removed == 0) vox%rannacher_left = max(0, vox%rannacher_left - 1)
        call voxel_iceberg_compact_vertical(vox)

        vox%basal_melt_rate = basal_melt
        vox%lateral_melt_rate = lateral_melt
        vox%surface_melt_rate = surface_melt
        vox%cum_basal_mass = vox%cum_basal_mass + basal_melt*dt
        vox%cum_lateral_mass = vox%cum_lateral_mass + lateral_melt*dt
        vox%cum_surface_mass = vox%cum_surface_mass + surface_melt*dt
        call voxel_iceberg_compute_state(vox)
        if (dbg_melt .and. .not. dbg_total_done) then
            block
                real(8) :: lv, wv, av
                lv = real(vox%nx, 8)*vox%dx; wv = real(vox%ny, 8)*vox%dy
                av = lv*wv + 2.0_8*(lv + wv)*vox%draft
                print '(a,10(1x,es14.6))', 'VOXEL_DEBUG_TOTAL', vox%submerged_area, av, &
                    vox%basal_melt_rate, vox%lateral_melt_rate, vox%surface_melt_rate, &
                    vox%draft, lv, wv, real(vox%nz, 8)*vox%dz, vox%total_mass
                print '(a,3(1x,es14.6))', 'VOXEL_DEBUG_MEAN', vox%stefan_mean_urel, &
                    vox%stefan_mean_tb, vox%stefan_mean_sb
            end block
            dbg_total_done = .true.
        end if
    end subroutine voxel_iceberg_step_profile

    ! Re-index the vertical grid when the lowest occupied layer rises. This
    ! preserves the body-relative draft/freeboard while removing empty bottom
    ! layers; absolute grid position is not a buoyant trajectory.
    subroutine voxel_iceberg_compact_vertical(vox)
        type(voxel_iceberg_type), intent(inout) :: vox
        integer :: i, j, k, kbot, shift
        real(8), allocatable :: Ttmp(:,:,:), phitmp(:,:,:)
        if (.not. allocated(vox%phi)) return
        kbot = vox%nz + 1
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) > EPS_PHI) then
                        kbot = min(kbot, k); exit
                    end if
                end do
                if (kbot <= vox%nz) exit
            end do
            if (kbot <= vox%nz) exit
        end do
        if (kbot <= 1 .or. kbot > vox%nz) return
        shift = kbot - 1
        allocate (Ttmp(vox%nx, vox%ny, vox%nz), phitmp(vox%nx, vox%ny, vox%nz))
        Ttmp = vox%T; phitmp = vox%phi
        do k = 1, vox%nz - shift
            vox%T(:, :, k) = Ttmp(:, :, k + shift)
            vox%phi(:, :, k) = phitmp(:, :, k + shift)
        end do
        do k = vox%nz - shift + 1, vox%nz
            vox%T(:, :, k) = 0.0_8
            vox%phi(:, :, k) = 0.0_8
        end do
        deallocate (Ttmp, phitmp)
        vox%rannacher_left = max(vox%rannacher_left, 2)
        call voxel_iceberg_compute_state(vox)
    end subroutine voxel_iceberg_compact_vertical

    ! ==========================================================================
    ! Проекционная фронтальная площадь (PDF §13.2).
    ! Для каждого твёрдого вокселя: если сосед В НАПРАВЛЕНИИ ПОТОКА пуст/вне
    ! области — вклад phi*A_face. Для произвольного угла:
    !   A_perp = Σ phi*( |cos|*dy*dz [x-грань] + |sin|*dx*dz [y-грань] ).
    ! A_perp — по ВСЕМ твёрдым вокселям; A_sub_proj — только по погружённым
    ! (для водного сопротивления). Приближение: единое направление потока.
    ! ==========================================================================
    subroutine voxel_iceberg_get_frontal_area(vox, flow_angle, A_perp, A_sub_proj)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(in) :: flow_angle
        real(8), intent(out) :: A_perp, A_sub_proj
        integer :: i, j, k, ii, jj
        real(8) :: ca, sa, cs, sn, contrib, ph
        A_perp = 0.0_8; A_sub_proj = 0.0_8
        if (.not. allocated(vox%phi)) return
        cs = cos(flow_angle); sn = sin(flow_angle)
        ca = abs(cs); sa = abs(sn)
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    ph = vox%phi(i, j, k)
                    if (ph <= EPS_PHI) cycle
                    contrib = 0.0_8
                    if (ca > 0.0_8) then
                        if (cs >= 0.0_8) then
                            ii = i + 1
                        else
                            ii = i - 1
                        end if
                        if (open_empty_or_outside(vox, ii, j, k)) &
                            contrib = contrib + ph*vox%dy*vox%dz*ca
                    end if
                    if (sa > 0.0_8) then
                        if (sn >= 0.0_8) then
                            jj = j + 1
                        else
                            jj = j - 1
                        end if
                        if (open_empty_or_outside(vox, i, jj, k)) &
                            contrib = contrib + ph*vox%dx*vox%dz*sa
                    end if
                    A_perp = A_perp + contrib
                    if (vox%submerged_mask(i, j, k)) A_sub_proj = A_sub_proj + contrib
                end do
            end do
        end do
    end subroutine voxel_iceberg_get_frontal_area

    ! ==========================================================================
    ! Stage 12.16: per-layer projected drag areas from phi.
    ! For every submerged layer k, sum the open +x/-x/+y/-y faces:
    !   ax_pos(k) = sum phi*dy*dz over faces whose i+1 neighbour is open/outside
    !   ax_neg(k) = ... i-1 ...
    !   ay_pos(k) = sum phi*dx*dz over faces whose j+1 neighbour is open/outside
    !   ay_neg(k) = ... j-1 ...
    ! For a full cube ax_pos = ax_neg = W*dz and ay_pos = ay_neg = L*dz, so the
    ! layer sum reproduces the prism Method A side areas within one cell.
    ! ==========================================================================
    subroutine voxel_iceberg_get_layer_areas(vox, nz, z_center, ax_pos, ax_neg, ay_pos, ay_neg)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(out) :: nz
        real(8), allocatable, intent(out) :: z_center(:), ax_pos(:), ax_neg(:), ay_pos(:), ay_neg(:)
        integer :: i, j, k
        real(8) :: ph, fx, fy

        nz = max(vox%nz, 0)
        allocate (z_center(nz), ax_pos(nz), ax_neg(nz), ay_pos(nz), ay_neg(nz))
        z_center = 0.0_8; ax_pos = 0.0_8; ax_neg = 0.0_8; ay_pos = 0.0_8; ay_neg = 0.0_8
        if (.not. allocated(vox%phi)) then
            nz = 0
            return
        end if
        if (.not. allocated(vox%submerged_mask)) then
            nz = 0
            return
        end if

        do k = 1, nz
            z_center(k) = (real(k, 8) - 0.5_8)*vox%dz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    ph = vox%phi(i, j, k)
                    if (ph <= EPS_PHI .or. .not. vox%submerged_mask(i, j, k)) cycle
                    fx = ph*vox%dy*vox%dz
                    fy = ph*vox%dx*vox%dz
                    if (open_empty_or_outside(vox, i + 1, j, k)) ax_pos(k) = ax_pos(k) + fx
                    if (open_empty_or_outside(vox, i - 1, j, k)) ax_neg(k) = ax_neg(k) + fx
                    if (open_empty_or_outside(vox, i, j + 1, k)) ay_pos(k) = ay_pos(k) + fy
                    if (open_empty_or_outside(vox, i, j - 1, k)) ay_neg(k) = ay_neg(k) + fy
                end do
            end do
        end do
    end subroutine voxel_iceberg_get_layer_areas

    ! ==========================================================================
    ! Метацентрическая устойчивость (PDF §13.4) — оценочно, без динамики
    ! опрокидывания. I_wp = L_eff*W_eff^3/12 (поперечная ось), V_sub=mass/rho_w,
    ! BM=I_wp/V_sub, BG=z_g-z_b, GM=BM-BG. GM<0 → риск опрокидывания
    ! (документируется, НЕ моделируется).
    ! ==========================================================================
    subroutine voxel_iceberg_get_stability(vox, GM, BM, BG, I_wp, V_sub)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: GM, BM, BG, I_wp, V_sub
        integer :: i, j, k, imin, imax, jmin, jmax
        real(8) :: xext, yext, cellvol, zc, num, den, z_g, z_b
        GM = 0.0_8; BM = 0.0_8; BG = 0.0_8; I_wp = 0.0_8; V_sub = 0.0_8
        if (.not. allocated(vox%phi)) return
        if (vox%total_mass <= 0.0_8) return
        V_sub = vox%total_mass/real(RHO_WATER, 8)
        imin = vox%nx; imax = 1; jmin = vox%ny; jmax = 1
        do k = 1, vox%nz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (.not. vox%submerged_mask(i, j, k)) cycle
                    imin = min(imin, i); imax = max(imax, i)
                    jmin = min(jmin, j); jmax = max(jmax, j)
                end do
            end do
        end do
        xext = real(max(imax - imin + 1, 1), 8)*vox%dx
        yext = real(max(jmax - jmin + 1, 1), 8)*vox%dy
        I_wp = xext*yext**3/12.0_8
        if (V_sub > 0.0_8) BM = I_wp/V_sub
        cellvol = vox%dx*vox%dy*vox%dz
        num = 0.0_8; den = 0.0_8
        do k = 1, vox%nz
            zc = (real(k, 8) - 0.5_8)*vox%dz
            do j = 1, vox%ny
                do i = 1, vox%nx
                    if (vox%phi(i, j, k) <= EPS_PHI) cycle
                    num = num + vox%phi(i, j, k)*zc*cellvol
                    den = den + vox%phi(i, j, k)*cellvol
                end do
            end do
        end do
        if (den > 0.0_8) then
            z_g = num/den
        else
            z_g = 0.0_8
        end if
        z_b = 0.5_8*vox%draft
        BG = z_g - z_b
        GM = BM - BG
    end subroutine voxel_iceberg_get_stability

    subroutine voxel_iceberg_get_stefan(vox, mean_tb, mean_sb, mean_urel, deep_tb, wl_tb, nfaces)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: mean_tb, mean_sb, mean_urel, deep_tb, wl_tb
        integer, intent(out) :: nfaces
        mean_tb = vox%stefan_mean_tb; mean_sb = vox%stefan_mean_sb
        mean_urel = vox%stefan_mean_urel; deep_tb = vox%stefan_deep_tb
        wl_tb = vox%stefan_wl_tb; nfaces = vox%stefan_faces
    end subroutine voxel_iceberg_get_stefan

    ! ==========================================================================
    ! Геттеры
    ! ==========================================================================
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

    subroutine voxel_iceberg_get_cumulative_losses(vox, basal, lateral, surface, flush)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: basal, lateral, surface, flush
        basal = vox%cum_basal_mass
        lateral = vox%cum_lateral_mass
        surface = vox%cum_surface_mass
        flush = vox%cum_flush_mass
    end subroutine voxel_iceberg_get_cumulative_losses

    subroutine voxel_iceberg_get_freeboard(vox, freeboard)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: freeboard
        freeboard = vox%freeboard
    end subroutine voxel_iceberg_get_freeboard

    subroutine voxel_iceberg_get_top_height(vox, top_height)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: top_height
        top_height = vox%top_height
    end subroutine voxel_iceberg_get_top_height

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
        basal = vox%basal_melt_rate; lateral = vox%lateral_melt_rate; surface = vox%surface_melt_rate
    end subroutine voxel_iceberg_get_melt

    subroutine voxel_iceberg_get_flush(vox, flushed_mass, flushed_energy)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: flushed_mass, flushed_energy
        flushed_mass = vox%flushed_mass; flushed_energy = vox%flushed_energy
    end subroutine voxel_iceberg_get_flush

    subroutine voxel_iceberg_get_solver(vox, cg_iters, cg_resid, clip_events, rannacher_left)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(out) :: cg_iters, clip_events, rannacher_left
        real(8), intent(out) :: cg_resid
        cg_iters = vox%cg_iters; cg_resid = vox%cg_resid
        clip_events = vox%clip_events; rannacher_left = vox%rannacher_left
    end subroutine voxel_iceberg_get_solver

    subroutine voxel_iceberg_get_clamp_mass(vox, mass)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: mass
        mass = vox%clamp_melt_mass
    end subroutine voxel_iceberg_get_clamp_mass

    ! Sensible heat content relative to 0 C, plus accumulated flush energy.
    subroutine voxel_iceberg_get_boundary_energy(vox, sub, air, test)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: sub, air, test
        sub = vox%cum_boundary_sub_energy
        air = vox%cum_boundary_air_energy
        test = vox%cum_boundary_test_energy
    end subroutine voxel_iceberg_get_boundary_energy

    subroutine voxel_iceberg_get_melt_sensible_energy(vox, value)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: value
        value = vox%cum_melt_sensible_energy
    end subroutine voxel_iceberg_get_melt_sensible_energy

    subroutine voxel_iceberg_get_energy(vox, sensible, flushed)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), intent(out) :: sensible, flushed
        real(8) :: V
        sensible = 0.0_8
        flushed = vox%flushed_energy
        if (.not. allocated(vox%T)) return
        V = vox%dx*vox%dy*vox%dz
        sensible = sum(vox%phi*real(RHO_ICE, 8)*c_ice_override*vox%T)*V
    end subroutine voxel_iceberg_get_energy

    subroutine voxel_iceberg_get_grid(vox, nx, ny, nz, dx, dy, dz)
        type(voxel_iceberg_type), intent(in) :: vox
        integer, intent(out) :: nx, ny, nz
        real(8), intent(out) :: dx, dy, dz
        nx = vox%nx; ny = vox%ny; nz = vox%nz
        dx = vox%dx; dy = vox%dy; dz = vox%dz
    end subroutine voxel_iceberg_get_grid

    ! Copy the current spatial fields for NetCDF output / diagnostics.
    subroutine voxel_iceberg_get_fields(vox, T, phi, open_mask, tb_face, sb_vox)
        type(voxel_iceberg_type), intent(in) :: vox
        real(8), allocatable, intent(out) :: T(:,:,:), phi(:,:,:)
        logical, allocatable, intent(out) :: open_mask(:,:,:)
        real(8), allocatable, intent(out) :: tb_face(:,:,:,:)
        real(8), allocatable, intent(out), optional :: sb_vox(:,:,:)
        if (.not. allocated(vox%T)) return
        allocate (T(vox%nx, vox%ny, vox%nz), phi(vox%nx, vox%ny, vox%nz))
        allocate (open_mask(vox%nx, vox%ny, vox%nz))
        allocate (tb_face(vox%nx, vox%ny, vox%nz, 6))
        T = vox%T; phi = vox%phi
        open_mask = vox%open_mask
        tb_face = vox%tb_face
        if (present(sb_vox)) then
            allocate (sb_vox(vox%nx, vox%ny, vox%nz)); sb_vox = vox%sb_vox
        end if
    end subroutine voxel_iceberg_get_fields

end module voxel_iceberg
