! ==============================================================================
! Модуль: voxel_thermal_solver (Stage 12.3)
! Назначение: конечно-объёмное решение теплопроводности и фазовых переходов в
!             воксельном айсберге + приграничные тепловые потоки (океан по
!             Стефану/forced convection, атмосфера — энергетический баланс).
!             Реализация спеки docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf
!             (МОДЕЛЬНАЯ СПЕЦИФИКАЦИЯ, не обсервационная калибровка).
! Единицы: SI. T [°C], phi [-] (0..1, доля льда), dx/dy/dz [м], dt [с],
!          k_ice [Вт/(м·К)], rho_ice [кг/м³], c_ice [Дж/(кг·К)], L_fusion [Дж/кг].
!
! Open items (перенесены из Stage 12.0/спецы, остаются видимыми в реализации):
!   * gamma_T из forced-convection корреляции (ocean_heat_transfer_coeff,
!     Eckert&Drake); gamma_S/солёный баланс НЕ решается явно → Stage 12.4.
!   * cavity exchange, spray/waterline zone — НЕ моделируются.
!   * One-way: океан/атмосфера заданы (reanalysis/ERA5); u_rel = |ocean u,v|
!     (без вычета скорости айсберга) — упрощение, уточнение в 12.4+.
!   * Tf = ocean_freezing_point(S, 0) (без поправки давления по глубине) → 12.4.
! netCDF/case-insensitive: избегаем имени "dt" для массивов (dt=шаг).
! ==============================================================================
module voxel_thermal_solver
    use iceberg_types, only: ocean_freezing_point, ocean_heat_transfer_coeff, &
                             CD_AIR, RHO_AIR, CP_AIR
    implicit none

    private
    public :: solve_heat_conduction, apply_boundary_fluxes

    real(8), parameter :: WIND_MIN = 0.1_8
    real(8), parameter :: EPS_PHI = 1.0d-12

contains

    ! ==========================================================================
    ! Явная теплопроводность (forward Euler) + локальный фазовый переход.
    ! dT/dt = alpha·∇²T, alpha=k/(rho·c). Проводимость грани ∝ min(phi_self,
    ! phi_nb) — пустые/талые ячейки изолируют (нулевой поток). Устойчивость
    ! явной схемы обеспечивается субшагами: nsub=ceil(dt/dt_max).
    ! ==========================================================================
    subroutine solve_heat_conduction(T, phi, dx, dy, dz, dt, &
                                     k_ice, rho_ice, c_ice, L_fusion, T_new, phi_new)
        real(8), intent(in) :: T(:,:,:), phi(:,:,:)
        real(8), intent(in) :: dx, dy, dz, dt
        real(8), intent(in) :: k_ice, rho_ice, c_ice, L_fusion
        real(8), intent(out) :: T_new(:,:,:), phi_new(:,:,:)

        integer :: nx, ny, nz, i, j, k, is, nsub
        real(8) :: alpha, dta, t_freeze, w, dphi, max_dt
        real(8) :: lap(3)
        real(8), allocatable :: Tb(:,:,:), pb(:,:,:)

        nx = size(T, 1); ny = size(T, 2); nz = size(T, 3)
        allocate (Tb(nx, ny, nz), pb(nx, ny, nz))
        Tb = T; pb = phi

        alpha = k_ice/max(rho_ice*c_ice, 1.0d-30)
        if (alpha <= 0.0_8) then
            T_new = T; phi_new = phi
            deallocate (Tb, pb); return
        end if
        max_dt = 1.0d0/(2.0d0*alpha*(1.0d0/(dx*dx) + 1.0d0/(dy*dy) + 1.0d0/(dz*dz)))
        nsub = 1
        if (dt > max_dt) nsub = int(dt/max_dt) + 1
        dta = dt/real(nsub, 8)

        do is = 1, nsub
            do k = 1, nz
                do j = 1, ny
                    do i = 1, nx
                        if (pb(i, j, k) <= EPS_PHI) cycle
                        lap = face_x(Tb, pb, i, j, k, nx, 1) + &
                              face_x(Tb, pb, i, j, k, nx, -1) + &
                              face_y(Tb, pb, i, j, k, ny, 1) + &
                              face_y(Tb, pb, i, j, k, ny, -1) + &
                              face_z(Tb, pb, i, j, k, nz, 1) + &
                              face_z(Tb, pb, i, j, k, nz, -1)
                        Tb(i, j, k) = Tb(i, j, k) + &
                            dta*alpha*(lap(1)/(dx*dx) + lap(2)/(dy*dy) + lap(3)/(dz*dz))
                    end do
                end do
            end do
        end do

        ! Фазовый переход (enthalpy): выше 0 °C плавит лёд (dphi=c·ΔT/L); ниже —
        ! без кристаллизации (открытая система, нет свободной воды; open item).
        t_freeze = 0.0_8
        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    w = pb(i, j, k)
                    if (Tb(i, j, k) > t_freeze .and. w > EPS_PHI) then
                        dphi = c_ice*(Tb(i, j, k) - t_freeze)/L_fusion
                        if (dphi >= w) then
                            w = 0.0_8
                        else
                            w = w - dphi
                        end if
                        Tb(i, j, k) = t_freeze
                    end if
                    Tb(i, j, k) = max(Tb(i, j, k), -273.15_8)
                    pb(i, j, k) = min(max(w, 0.0_8), 1.0_8)
                end do
            end do
        end do

        T_new = Tb; phi_new = pb
        deallocate (Tb, pb)
    end subroutine solve_heat_conduction

    pure function face_x(T, p, i, j, k, nx, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, nx, dir
        real(8) :: r(3)
        integer :: ii
        r = 0.0_8
        ii = i + dir
        if (ii < 1 .or. ii > nx) return
        if (p(ii, j, k) <= EPS_PHI) return
        r(1) = min(p(i, j, k), p(ii, j, k))*(T(ii, j, k) - T(i, j, k))
    end function face_x

    pure function face_y(T, p, i, j, k, ny, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, ny, dir
        real(8) :: r(3)
        integer :: jj
        r = 0.0_8
        jj = j + dir
        if (jj < 1 .or. jj > ny) return
        if (p(i, jj, k) <= EPS_PHI) return
        r(2) = min(p(i, j, k), p(i, jj, k))*(T(i, jj, k) - T(i, j, k))
    end function face_y

    pure function face_z(T, p, i, j, k, nz, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, nz, dir
        real(8) :: r(3)
        integer :: kk
        r = 0.0_8
        kk = k + dir
        if (kk < 1 .or. kk > nz) return
        if (p(i, j, kk) <= EPS_PHI) return
        r(3) = min(p(i, j, k), p(i, j, kk))*(T(i, j, kk) - T(i, j, k))
    end function face_z

    ! ==========================================================================
    ! Приграничные потоки: океаническое плавление (Стефан) на погружённых гранях
    ! (basal=нормаль z, lateral=боковые) и атмосферный баланс на открытых.
    ! [кг/с], + = melt. Изменяет T, phi in-place (дельты по входному состоянию).
    ! ==========================================================================
    subroutine apply_boundary_fluxes(T, phi, dx, dy, dz, dt, &
                                     ocean_T, ocean_S, ocean_u, ocean_v, &
                                     atmos_T, atmos_Q, atmos_wind, &
                                     submerged_mask, exposed_mask, &
                                     basal_melt, lateral_melt, surface_melt)
        real(8), intent(inout) :: T(:,:,:), phi(:,:,:)
        real(8), intent(in) :: dx, dy, dz, dt
        real(8), intent(in) :: ocean_T, ocean_S, ocean_u, ocean_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        logical, intent(in) :: submerged_mask(:,:,:), exposed_mask(:,:,:)
        real(8), intent(out) :: basal_melt, lateral_melt, surface_melt

        real(8), parameter :: rho_ice8 = 910.0d0, c_ice8 = 2100.0d0
        real(8), parameter :: L_fus8 = 334000.0d0
        integer :: nx, ny, nz, i, j, k, d
        integer :: di(6), dj(6), dk(6)
        real(8) :: gamma_t, u_rel, l_char, tf, melt_v, area, mr
        real(8) :: h_sens, q_atm, dphi, w0
        real :: gt_r, tf4
        real(8), allocatable :: Tin(:,:,:), pin(:,:,:)
        real(8), allocatable :: heat(:,:,:), pmelt(:,:,:)

        nx = size(T, 1); ny = size(T, 2); nz = size(T, 3)
        allocate (Tin(nx, ny, nz), pin(nx, ny, nz), heat(nx, ny, nz), pmelt(nx, ny, nz))
        Tin = T; pin = phi; heat = 0.0d0; pmelt = 0.0d0
        basal_melt = 0.0d0; lateral_melt = 0.0d0; surface_melt = 0.0d0

        di = (/ 1, -1, 0, 0, 0, 0 /)
        dj = (/ 0, 0, 1, -1, 0, 0 /)
        dk = (/ 0, 0, 0, 0, 1, -1 /)

        u_rel = sqrt(ocean_u*ocean_u + ocean_v*ocean_v)
        l_char = max(nx*dx, ny*dy)
        tf4 = ocean_freezing_point(real(ocean_S), 0.0)
        tf = real(tf4, 8)
        gt_r = 0.0
        call ocean_heat_transfer_coeff(real(u_rel), real(l_char), gt_r)
        gamma_t = max(real(gt_r, 8), 0.0d0)
        melt_v = gamma_t*(ocean_T - tf)/(rho_ice8*L_fus8)          ! м/с
        h_sens = real(CD_AIR, 8)*real(RHO_AIR, 8)*real(CP_AIR, 8)* &
                 max(real(atmos_wind, 8), WIND_MIN)                ! Вт/(м²·К)

        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    if (pin(i, j, k) <= EPS_PHI) cycle
                    if (.not. (submerged_mask(i, j, k) .or. exposed_mask(i, j, k))) cycle
                    do d = 1, 6
                        if (.not. neighbour_empty(pin, i + di(d), j + dj(d), k + dk(d))) cycle
                        area = face_area(d, dx, dy, dz)
                        if (submerged_mask(i, j, k)) then
                            mr = rho_ice8*area*melt_v
                            if (d >= 5) then
                                basal_melt = basal_melt + mr
                            else
                                lateral_melt = lateral_melt + mr
                            end if
                            pmelt(i, j, k) = pmelt(i, j, k) - melt_v*dt/dz
                            heat(i, j, k) = max(heat(i, j, k), 0.0d0)
                        else if (exposed_mask(i, j, k)) then
                            q_atm = atmos_Q + h_sens*(atmos_T - Tin(i, j, k))
                            mr = rho_ice8*area*max(q_atm, 0.0d0)/(rho_ice8*L_fus8)
                            surface_melt = surface_melt + mr
                            heat(i, j, k) = heat(i, j, k) + &
                                q_atm*dt/(rho_ice8*c_ice8*dz)
                        end if
                    end do
                end do
            end do
        end do

        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    w0 = min(max(pin(i, j, k) + pmelt(i, j, k), 0.0d0), 1.0d0)
                    T(i, j, k) = Tin(i, j, k) + heat(i, j, k)
                    if (T(i, j, k) > 0.0d0 .and. w0 > EPS_PHI) then
                        dphi = c_ice8*T(i, j, k)/L_fus8
                        if (dphi >= w0) then
                            w0 = 0.0d0
                        else
                            w0 = w0 - dphi
                        end if
                        T(i, j, k) = 0.0d0
                    end if
                    phi(i, j, k) = min(max(w0, 0.0d0), 1.0d0)
                end do
            end do
        end do

        deallocate (Tin, pin, heat, pmelt)
    end subroutine apply_boundary_fluxes

    pure logical function neighbour_empty(phi, i, j, k)
        real(8), intent(in) :: phi(:,:,:)
        integer, intent(in) :: i, j, k
        if (i < 1 .or. j < 1 .or. k < 1 .or. &
            i > size(phi, 1) .or. j > size(phi, 2) .or. k > size(phi, 3)) then
            neighbour_empty = .true.
        else
            neighbour_empty = (phi(i, j, k) <= EPS_PHI)
        end if
    end function neighbour_empty

    pure function face_area(d, dx, dy, dz) result(a)
        integer, intent(in) :: d
        real(8), intent(in) :: dx, dy, dz
        real(8) :: a
        select case (d)
        case (1, 2); a = dy*dz
        case (3, 4); a = dx*dz
        case (5, 6); a = dx*dy
        case default; a = 0.0_8
        end select
    end function face_area

end module voxel_thermal_solver
