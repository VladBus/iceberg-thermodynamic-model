! ==============================================================================
! Stage 11.10.1 — Open Boundary Conditions (OBC)
!
! Switchable, OFF-by-default OBC components:
!   STAGE1110_FLATHER_OBC   — barotropic Flather (external eta/U = 0)
!   STAGE1110_SPONGE_LAYER  — T/S relaxation in a 5-cell coastal sponge
!   STAGE1110_RADIATION_OBC — barotropic radiation condition
!   STAGE1110_SPONGE_ALPHA  — relaxation rate [1/s], default 1/day
!
! This module does NOT alter EOS formulas or the scheduler.  It is called at
! every barotropic step from shal() (Flather/radiation) and after CA (sponge).
! ==============================================================================
module stage1110_obc
    use param
    implicit none

    logical, save :: s1110_flather = .false.
    logical, save :: s1110_sponge = .false.
    logical, save :: s1110_radiation = .false.
    real, save :: s1110_sponge_alpha = 1.0/86400.0
    real, save :: s1110_sponge_width = 5.0
    real, allocatable, save :: t_clim(:, :, :), s_clim(:, :, :)
    logical, save :: clim_ready = .false.
    real, parameter :: G_CGS = 981.0
    real, parameter :: OBC_DX = 1389000.0

contains

    subroutine s1110_init()
        character(len=64) :: env
        integer :: ios
        call get_environment_variable('STAGE1110_FLATHER_OBC', env)
        if (len_trim(env) .gt. 0) s1110_flather = truthy(env)
        call get_environment_variable('STAGE1110_SPONGE_LAYER', env)
        if (len_trim(env) .gt. 0) s1110_sponge = truthy(env)
        call get_environment_variable('STAGE1110_RADIATION_OBC', env)
        if (len_trim(env) .gt. 0) s1110_radiation = truthy(env)
        call get_environment_variable('STAGE1110_SPONGE_ALPHA', env)
        if (len_trim(env) .gt. 0) read (env, *, iostat=ios) s1110_sponge_alpha
        if (s1110_sponge_alpha .le. 0.0) s1110_sponge_alpha = 1.0/86400.0
        call get_environment_variable('STAGE1110_SPONGE_WIDTH', env)
        if (len_trim(env) .gt. 0) read (env, *, iostat=ios) s1110_sponge_width
        if (s1110_sponge_width .lt. 1.0) s1110_sponge_width = 5.0
        if (.not. allocated(t_clim)) then
            allocate (t_clim(is1, js1, ks), s_clim(is1, js1, ks))
        end if
        t_clim = t2
        s_clim = s2
        clim_ready = .true.
        print '(A,L1,A,L1,A,L1,A,ES10.3,A,F5.1)', &
            '>>> Stage 11.10.1 OBC: FLATHER=', s1110_flather, &
            ' SPONGE=', s1110_sponge, ' RADIATION=', s1110_radiation, &
            ' ALPHA=', s1110_sponge_alpha, ' WIDTH=', s1110_sponge_width
    end subroutine s1110_init

    logical function truthy(v)
        character(len=*), intent(in) :: v
        truthy = (trim(v) .eq. 'true' .or. trim(v) .eq. 'TRUE' .or. &
                  trim(v) .eq. '1' .or. trim(v) .eq. 'ON' .or. trim(v) .eq. 'on')
    end function truthy

    ! Flather with zero external state: q = -eta * sqrt(gH) [cm2/s].
    pure real function flather_transport(eta_cm, h_cm) result(q)
        real, intent(in) :: eta_cm, h_cm
        q = -eta_cm*sqrt(G_CGS*max(h_cm, 50.0))
    end function flather_transport

    ! Radiation update for a boundary transport.
    pure real function radiation_update(phi_b, phi_i, h_cm, dt, dx) result(out)
        real, intent(in) :: phi_b, phi_i, h_cm, dt, dx
        real :: c
        c = sqrt(G_CGS*max(h_cm, 50.0))
        out = phi_b - c*dt/dx*(phi_b - phi_i)
    end function radiation_update

    ! Exponential sponge weight, clipped to [0,1].
    pure real function sponge_weight(dist, width, alpha, dt) result(w)
        real, intent(in) :: dist, width, alpha, dt
        if (dist .lt. 0.0 .or. dist .gt. width) then
            w = 0.0
        else
            w = min(1.0, alpha*dt*exp(-dist/max(width, 1.0)))
        end if
    end function sponge_weight

    subroutine s1110_barotropic_boundary()
        integer :: i, j
        real :: h, c
        if (.not. (s1110_flather .or. s1110_radiation)) return

        ! North boundary (j=1, U) and south boundary (j=js, U)
        do i = 1, is1
            if (kt1(i, 1) .gt. 0) then
                h = hu(i, 1)
                if (s1110_flather) up2(i, 1) = flather_transport(y2(i, 1), h)
                if (s1110_radiation) up2(i, 1) = radiation_update(up1(i, 1), up1(i, 2), h, 120.0, OBC_DX)
            end if
            if (kt1(i, js) .gt. 0) then
                h = hu(i, js)
                if (s1110_flather) up2(i, js) = flather_transport(y2(i, js), h)
                if (s1110_radiation) up2(i, js) = radiation_update(up1(i, js), up1(i, js - 1), h, 120.0, OBC_DX)
            end if
        end do

        ! West boundary (i=1, V) and east boundary (i=is, V)
        do j = 1, js1
            if (kt1(1, j) .gt. 0) then
                h = hv(1, j)
                if (s1110_flather) vp2(1, j) = -flather_transport(y2(1, j), h)
                if (s1110_radiation) vp2(1, j) = radiation_update(vp1(1, j), vp1(2, j), h, 120.0, OBC_DX)
            end if
            if (kt1(is, j) .gt. 0) then
                h = hv(is, j)
                if (s1110_flather) vp2(is, j) = -flather_transport(y2(is, j), h)
                if (s1110_radiation) vp2(is, j) = radiation_update(vp1(is, j), vp1(is - 1, j), h, 120.0, OBC_DX)
            end if
        end do
    end subroutine s1110_barotropic_boundary

    subroutine s1110_apply_sponge(dt_step)
        real, intent(in) :: dt_step
        integer :: i, j, k, dist
        real :: w
        if (.not. s1110_sponge) return
        if (.not. clim_ready) then
            if (.not. allocated(t_clim)) allocate (t_clim(is1, js1, ks), s_clim(is1, js1, ks))
            t_clim = t2
            s_clim = s2
            clim_ready = .true.
        end if
        do j = 1, js1
            do i = 1, is1
                if (kt1(i, j) .le. 0) cycle
                dist = min(min(i - 1, is1 - i), min(j - 1, js1 - j))
                if (dist .gt. int(s1110_sponge_width)) cycle
                w = sponge_weight(real(dist), s1110_sponge_width, s1110_sponge_alpha, dt_step)
                do k = 1, kt1(i, j)
                    t2(i, j, k) = t2(i, j, k) - w*(t2(i, j, k) - t_clim(i, j, k))
                    s2(i, j, k) = s2(i, j, k) - w*(s2(i, j, k) - s_clim(i, j, k))
                end do
            end do
        end do
    end subroutine s1110_apply_sponge

end module stage1110_obc
