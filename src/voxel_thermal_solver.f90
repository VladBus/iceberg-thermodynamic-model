! ==============================================================================
! Модуль: voxel_thermal_solver (Stage 12.4, PART A)
! Назначение: теплопроводность воксельного айсберга.
!   * Crank-Nicolson (theta-схема, ICEBERG_THETA, default 0.5) + PCG(Якоби),
!     tol 1e-10, тёплый старт T^n; theta=1 → обратный Эйлер (Rannacher).
!   * Явная схема 12.3 сохранена (VOXEL_THERMAL_SCHEME=explicit) с субшагами.
!   * Граничные условия В МАТРИЦЕ (Transition doc 6.2 п.4):
!       - погружённая грань: Дирихле T_b=Tf(S,P) через G_b=2kA/h_norm
!         (Tf — существующая ocean_freezing_point: S масс.доля, depth [м],
!          внутри ×1000 → PSU и P=rho*g*d/1e4 дбар; PDF eq 8.1);
!       - открытая грань: Робин q=h_s(T_air-T)+Q_net, h_s*A полностью неявно,
!         A*Q_net явно. Ga-линеаризация НЕ добавляется: Q_net (=diag%q_net_surface)
!         уже содержит net LW/SW/latent из баланса Stage 10 → иначе двойной счёт.
!         (Ограничение: если Q_net будет считаться локально от T_s вокселя —
!          добавить линеаризацию PDF §11.1.)
!   * m >= 0 (spec assumption A5; аккреция не моделируется).
!   * TEST-ONLY Dirichlet faces (dir_face_a/b, dir_T_a/b) — недостижимы из
!     production-вызовов; для A-T5 (стационарный профиль) и фазовых тестов.
! Единицы: SI, real(8) внутри; константы — iceberg_types (без хардкода).
! ==============================================================================
module voxel_thermal_solver
    use iceberg_types, only: RHO_ICE, RHO_WATER, GRAVITY, C_ICE, K_ICE, LATENT_HEAT, &
                             CD_AIR, RHO_AIR, CP_AIR, &
                             ocean_freezing_point, ocean_heat_transfer_coeff
    implicit none

    private
    public :: solve_heat_conduction, apply_boundary_fluxes, solve_cn
    public :: face_h, voxel_face_dphi, face_area

    real(8), parameter :: EPS_PHI = 1.0d-12
    real(8), parameter :: WIND_MIN = 0.1_8

contains

    ! ==========================================================================
    ! Нормальный размер вокселя для грани d (A5 geometry fix):
    !   d=1,2 (x) → dx;  d=3,4 (y) → dy;  d=5,6 (z) → dz.
    ! ==========================================================================
    pure real(8) function face_h(d, dx, dy, dz) result(h)
        integer, intent(in) :: d
        real(8), intent(in) :: dx, dy, dz
        select case (d)
        case (1, 2); h = dx
        case (3, 4); h = dy
        case (5, 6); h = dz
        case default; h = dz
        end select
    end function face_h

    ! Изменение доли льда от грани d при скорости отступания m [м/с] (A5).
    pure real(8) function voxel_face_dphi(m, dt, d, dx, dy, dz) result(dphi)
        real(8), intent(in) :: m, dt, dx, dy, dz
        integer, intent(in) :: d
        dphi = m*dt/face_h(d, dx, dy, dz)
    end function voxel_face_dphi

    ! ==========================================================================
    ! ЯВНАЯ схема (12.3, сохранена для VOXEL_THERMAL_SCHEME=explicit).
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
            T_new = T; phi_new = phi; deallocate (Tb, pb); return
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
                        lap = face_x(Tb, pb, i, j, k, nx, 1) + face_x(Tb, pb, i, j, k, nx, -1) + &
                              face_y(Tb, pb, i, j, k, ny, 1) + face_y(Tb, pb, i, j, k, ny, -1) + &
                              face_z(Tb, pb, i, j, k, nz, 1) + face_z(Tb, pb, i, j, k, nz, -1)
                        Tb(i, j, k) = Tb(i, j, k) + &
                            dta*alpha*(lap(1)/(dx*dx) + lap(2)/(dy*dy) + lap(3)/(dz*dz))
                    end do
                end do
            end do
        end do

        t_freeze = 0.0_8
        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    w = pb(i, j, k)
                    if (Tb(i, j, k) > t_freeze .and. w > EPS_PHI) then
                        dphi = w*c_ice*(Tb(i, j, k) - t_freeze)/L_fusion   ! energy-consistent (phi factor)
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

    ! ==========================================================================
    ! ЯВНЫЕ приграничные потоки (12.3) — исправлена геометрия (A5) и m>=0.
    ! draft optional: если передан, Tf считается по давлению на глубине грани.
    ! ==========================================================================
    subroutine apply_boundary_fluxes(T, phi, dx, dy, dz, dt, &
                                     ocean_T, ocean_S, ocean_u, ocean_v, &
                                     atmos_T, atmos_Q, atmos_wind, &
                                     submerged_mask, exposed_mask, &
                                     basal_melt, lateral_melt, surface_melt, draft)
        real(8), intent(inout) :: T(:,:,:), phi(:,:,:)
        real(8), intent(in) :: dx, dy, dz, dt
        real(8), intent(in) :: ocean_T, ocean_S, ocean_u, ocean_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        logical, intent(in) :: submerged_mask(:,:,:), exposed_mask(:,:,:)
        real(8), intent(out) :: basal_melt, lateral_melt, surface_melt
        real(8), intent(in), optional :: draft

        integer :: nx, ny, nz, i, j, k, d
        integer :: di(6), dj(6), dk(6)
        real(8) :: gamma_t, u_rel, l_char, tf, melt_v, area, mr, hn, zf, dface
        real(8) :: h_sens, q_atm, dphi, w0
        real :: gt_r, tf4
        real(8), allocatable :: Tin(:,:,:), pin(:,:,:)
        real(8), allocatable :: heat(:,:,:), pmelt(:,:,:)

        nx = size(T, 1); ny = size(T, 2); nz = size(T, 3)
        allocate (Tin(nx, ny, nz), pin(nx, ny, nz), heat(nx, ny, nz), pmelt(nx, ny, nz))
        Tin = T; pin = phi; heat = 0.0d0; pmelt = 0.0d0
        basal_melt = 0.0d0; lateral_melt = 0.0d0; surface_melt = 0.0d0

        di = (/ 1, -1, 0, 0, 0, 0 /); dj = (/ 0, 0, 1, -1, 0, 0 /); dk = (/ 0, 0, 0, 0, 1, -1 /)
        u_rel = sqrt(ocean_u*ocean_u + ocean_v*ocean_v)
        l_char = max(nx*dx, ny*dy)
        gt_r = 0.0
        call ocean_heat_transfer_coeff(real(u_rel), real(l_char), gt_r)
        gamma_t = max(real(gt_r, 8), 0.0d0)
        h_sens = real(CD_AIR, 8)*real(RHO_AIR, 8)*real(CP_AIR, 8)*max(atmos_wind, WIND_MIN)

        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    if (pin(i, j, k) <= EPS_PHI) cycle
                    if (.not. (submerged_mask(i, j, k) .or. exposed_mask(i, j, k))) cycle
                    zf = (real(k, 8) - 0.5_8)*dz
                    if (present(draft)) then
                        dface = max(0.0_8, draft - zf)
                    else
                        dface = 0.0_8
                    end if
                    tf4 = ocean_freezing_point(real(ocean_S), real(dface))
                    tf = real(tf4, 8)
                    melt_v = max(0.0_8, gamma_t*(ocean_T - tf)/ &
                                 (real(RHO_ICE, 8)*real(LATENT_HEAT, 8)))   ! m>=0 (A5)
                    do d = 1, 6
                        if (.not. neighbour_empty(pin, i + di(d), j + dj(d), k + dk(d))) cycle
                        hn = face_h(d, dx, dy, dz)
                        area = face_area(d, dx, dy, dz)
                        if (submerged_mask(i, j, k)) then
                            mr = real(RHO_ICE, 8)*area*melt_v
                            if (d >= 5) then
                                basal_melt = basal_melt + mr
                            else
                                lateral_melt = lateral_melt + mr
                            end if
                            pmelt(i, j, k) = pmelt(i, j, k) - melt_v*dt/hn   ! A5: h_norm
                            heat(i, j, k) = max(heat(i, j, k), 0.0d0)
                        else
                            q_atm = atmos_Q + h_sens*(atmos_T - Tin(i, j, k))
                            mr = real(RHO_ICE, 8)*area*max(q_atm, 0.0_8)/ &
                                 (real(RHO_ICE, 8)*real(LATENT_HEAT, 8))
                            surface_melt = surface_melt + mr
                            heat(i, j, k) = heat(i, j, k) + &
                                            q_atm*dt/(real(RHO_ICE, 8)*real(C_ICE, 8)*hn)
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
                        dphi = real(C_ICE, 8)*T(i, j, k)/real(LATENT_HEAT, 8)
                        if (dphi >= w0) then
                            w0 = 0.0d0
                        else
                            w0 = w0 - dphi
                        end if
                        T(i, j, k) = 0.0d0
                    end if
                    phi(i, j, k) = min(max(w0, 0.0d0), 1.0_8)
                end do
            end do
        end do
        deallocate (Tin, pin, heat, pmelt)
    end subroutine apply_boundary_fluxes

    ! ==========================================================================
    ! CRANK-NICOLSON + PCG(Якоби). SPD 7-диагональная система.
    ! theta=0.5 (default), theta=1.0 → backward Euler (Rannacher).
    ! TEST-ONLY dir_face_a/b (1..6) + dir_T_a/b: половинная проводимость
    ! G=2kA/h_norm к фиксированной T на указанной грани (не production).
    ! ==========================================================================
    subroutine solve_cn(T, phi, dx, dy, dz, dt, k_ice, rho_ice, c_ice, theta, &
                        cg_tol, cg_maxit, draft, ocean_T, ocean_S, ocean_u, ocean_v, &
                        atmos_T, atmos_Q, atmos_wind, submerged_mask, exposed_mask, &
                        Tnew, iters, resid, converged, &
                        dir_face_a, dir_T_a, dir_face_b, dir_T_b)
        real(8), intent(in) :: T(:,:,:), phi(:,:,:)
        real(8), intent(in) :: dx, dy, dz, dt, k_ice, rho_ice, c_ice, theta
        real(8), intent(in) :: cg_tol
        integer, intent(in) :: cg_maxit
        real(8), intent(in) :: draft, ocean_T, ocean_S, ocean_u, ocean_v
        real(8), intent(in) :: atmos_T, atmos_Q, atmos_wind
        logical, intent(in) :: submerged_mask(:,:,:), exposed_mask(:,:,:)
        real(8), intent(out) :: Tnew(:,:,:)
        integer, intent(out) :: iters
        real(8), intent(out) :: resid
        logical, intent(out) :: converged
        integer, intent(in), optional :: dir_face_a, dir_face_b
        real(8), intent(in), optional :: dir_T_a, dir_T_b

        integer :: nx, ny, nz, i, j, k, d, it, mx
        integer :: di(6), dj(6), dk(6), ii, jj, kk, fa, fb
        real(8) :: V, A, hn, Ci, G, Gb, hA, hs, wind, zf, dface
        real(8) :: tf, Told, Tair, rhs_scale, bnorm, rz, rz2, alpha, pAp, rr
        real(8) :: tda, tdb
        real(8), allocatable :: diag(:,:,:), rhs(:,:,:), off(:,:,:,:)
        real(8), allocatable :: x(:,:,:), r(:,:,:), z(:,:,:), p(:,:,:), ap(:,:,:)
        logical :: have_a, have_b

        nx = size(T, 1); ny = size(T, 2); nz = size(T, 3)
        V = dx*dy*dz
        di = (/ 1, -1, 0, 0, 0, 0 /); dj = (/ 0, 0, 1, -1, 0, 0 /); dk = (/ 0, 0, 0, 0, 1, -1 /)

        have_a = present(dir_face_a) .and. present(dir_T_a)
        have_b = present(dir_face_b) .and. present(dir_T_b)
        fa = 0; fb = 0; tda = 0.0_8; tdb = 0.0_8
        if (have_a) then
            fa = dir_face_a; tda = dir_T_a
            have_a = (fa >= 1 .and. fa <= 6)
        end if
        if (have_b) then
            fb = dir_face_b; tdb = dir_T_b
            have_b = (fb >= 1 .and. fb <= 6)
        end if

        wind = max(atmos_wind, WIND_MIN)
        hs = real(CD_AIR, 8)*real(RHO_AIR, 8)*real(CP_AIR, 8)*wind
        Tair = atmos_T

        allocate (diag(nx, ny, nz), rhs(nx, ny, nz), off(nx, ny, nz, 6))
        allocate (x(nx, ny, nz), r(nx, ny, nz), z(nx, ny, nz), p(nx, ny, nz), ap(nx, ny, nz))

        ! --- сборка ---
        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    if (phi(i, j, k) <= EPS_PHI) then
                        diag(i, j, k) = 1.0_8; rhs(i, j, k) = T(i, j, k); off(i, j, k, :) = 0.0_8
                        cycle
                    end if
                    Told = T(i, j, k)
                    Ci = phi(i, j, k)*rho_ice*c_ice*V
                    diag(i, j, k) = Ci/dt
                    rhs(i, j, k) = (Ci/dt)*Told
                    off(i, j, k, :) = 0.0_8
                    zf = (real(k, 8) - 0.5_8)*dz
                    dface = max(0.0_8, draft - zf)
                    tf = real(ocean_freezing_point(real(ocean_S), real(dface)), 8)
                    do d = 1, 6
                        ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
                        A = face_area(d, dx, dy, dz); hn = face_h(d, dx, dy, dz)
                        if (ii >= 1 .and. ii <= nx .and. jj >= 1 .and. jj <= ny .and. &
                            kk >= 1 .and. kk <= nz .and. phi(ii, jj, kk) > EPS_PHI) then
                            G = k_ice*A/hn*min(phi(i, j, k), phi(ii, jj, kk))
                            diag(i, j, k) = diag(i, j, k) + theta*G
                            rhs(i, j, k) = rhs(i, j, k) + (1.0_8 - theta)*G*(T(ii, jj, kk) - Told)
                            off(i, j, k, d) = -theta*G
                        else
                            if (submerged_mask(i, j, k)) then
                                Gb = 2.0_8*k_ice*A/hn
                                diag(i, j, k) = diag(i, j, k) + theta*Gb
                                rhs(i, j, k) = rhs(i, j, k) + Gb*tf - (1.0_8 - theta)*Gb*Told
                            end if
                            if (exposed_mask(i, j, k)) then
                                hA = hs*A
                                diag(i, j, k) = diag(i, j, k) + hA
                                rhs(i, j, k) = rhs(i, j, k) + hA*Tair + A*atmos_Q
                            end if
                        end if
                    end do
                    ! TEST-ONLY Dirichlet faces (half-cell conductance)
                    if (have_a .and. on_face(i, j, k, nx, ny, nz, fa)) then
                        hn = face_h(fa, dx, dy, dz); A = face_area(fa, dx, dy, dz)
                        Gb = 2.0_8*k_ice*A/hn
                        diag(i, j, k) = diag(i, j, k) + theta*Gb
                        rhs(i, j, k) = rhs(i, j, k) + Gb*tda - (1.0_8 - theta)*Gb*Told
                    end if
                    if (have_b .and. on_face(i, j, k, nx, ny, nz, fb)) then
                        hn = face_h(fb, dx, dy, dz); A = face_area(fb, dx, dy, dz)
                        Gb = 2.0_8*k_ice*A/hn
                        diag(i, j, k) = diag(i, j, k) + theta*Gb
                        rhs(i, j, k) = rhs(i, j, k) + Gb*tdb - (1.0_8 - theta)*Gb*Told
                    end if
                end do
            end do
        end do

        ! --- PCG(Якоби), warm start T^n ---
        x = T
        call matvec_cn(x, diag, off, nx, ny, nz, ap)
        r = rhs - ap
        z = r/diag
        p = z
        bnorm = sqrt(sum(rhs*rhs))
        rz = sum(r*z)
        mx = max(cg_maxit, 10)
        iters = 0; resid = 1.0_8; converged = .false.
        if (bnorm <= 1.0d-300) then
            Tnew = x; resid = 0.0_8; converged = .true.; deallocate (diag, rhs, off, x, r, z, p, ap); return
        end if
        resid = sqrt(sum(r*r))/bnorm
        if (resid < cg_tol) then
            Tnew = x; converged = .true.; deallocate (diag, rhs, off, x, r, z, p, ap); return
        end if
        do it = 1, mx
            iters = it
            call matvec_cn(p, diag, off, nx, ny, nz, ap)
            pAp = sum(p*ap)
            if (pAp <= 0.0_8) exit
            alpha = rz/pAp
            x = x + alpha*p
            r = r - alpha*ap
            rr = sqrt(sum(r*r))/bnorm
            resid = rr
            if (rr < cg_tol) then
                converged = .true.
                exit
            end if
            z = r/diag
            rz2 = sum(r*z)
            if (abs(rz) <= 1.0d-300) exit
            p = z + (rz2/rz)*p
            rz = rz2
        end do
        Tnew = x
        deallocate (diag, rhs, off, x, r, z, p, ap)
    end subroutine solve_cn

    subroutine matvec_cn(v, diag, off, nx, ny, nz, av)
        real(8), intent(in) :: v(:,:,:), diag(:,:,:), off(:,:,:,:)
        integer, intent(in) :: nx, ny, nz
        real(8), intent(out) :: av(:,:,:)
        integer :: i, j, k, d, ii, jj, kk
        integer :: di(6), dj(6), dk(6)
        di = (/ 1, -1, 0, 0, 0, 0 /); dj = (/ 0, 0, 1, -1, 0, 0 /); dk = (/ 0, 0, 0, 0, 1, -1 /)
        do k = 1, nz
            do j = 1, ny
                do i = 1, nx
                    av(i, j, k) = diag(i, j, k)*v(i, j, k)
                    do d = 1, 6
                        if (off(i, j, k, d) == 0.0_8) cycle
                        ii = i + di(d); jj = j + dj(d); kk = k + dk(d)
                        av(i, j, k) = av(i, j, k) + off(i, j, k, d)*v(ii, jj, kk)
                    end do
                end do
            end do
        end do
    end subroutine matvec_cn

    pure logical function on_face(i, j, k, nx, ny, nz, f)
        integer, intent(in) :: i, j, k, nx, ny, nz, f
        on_face = .false.
        select case (f)
        case (1); on_face = (i == nx)
        case (2); on_face = (i == 1)
        case (3); on_face = (j == ny)
        case (4); on_face = (j == 1)
        case (5); on_face = (k == nz)
        case (6); on_face = (k == 1)
        end select
    end function on_face

    pure function face_x(T, p, i, j, k, nx, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, nx, dir
        real(8) :: r(3); integer :: ii
        r = 0.0_8; ii = i + dir
        if (ii < 1 .or. ii > nx) return
        if (p(ii, j, k) <= EPS_PHI) return
        r(1) = min(p(i, j, k), p(ii, j, k))*(T(ii, j, k) - T(i, j, k))
    end function face_x

    pure function face_y(T, p, i, j, k, ny, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, ny, dir
        real(8) :: r(3); integer :: jj
        r = 0.0_8; jj = j + dir
        if (jj < 1 .or. jj > ny) return
        if (p(i, jj, k) <= EPS_PHI) return
        r(2) = min(p(i, j, k), p(i, jj, k))*(T(i, jj, k) - T(i, j, k))
    end function face_y

    pure function face_z(T, p, i, j, k, nz, dir) result(r)
        real(8), intent(in) :: T(:,:,:), p(:,:,:)
        integer, intent(in) :: i, j, k, nz, dir
        real(8) :: r(3); integer :: kk
        r = 0.0_8; kk = k + dir
        if (kk < 1 .or. kk > nz) return
        if (p(i, j, kk) <= EPS_PHI) return
        r(3) = min(p(i, j, k), p(i, j, kk))*(T(i, j, kk) - T(i, j, k))
    end function face_z

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
