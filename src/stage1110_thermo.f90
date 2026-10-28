! Stage 11.10.4 — thermodynamic hardening / implicit vertical diffusion.
! All switches are OFF for N=1; the module can be enabled for N>1.
module stage1110_thermo
    use param
    implicit none
    logical, save :: hard_limits = .false.
    logical, save :: flux_clip = .false.
    logical, save :: ca_smooth = .false.
    logical, save :: implicit_vdiff = .false.
    logical, save :: physical_limits = .false.
    real, save :: kv_diff = 1.0e-4   ! m2/s
contains
    subroutine s1110_thermo_init(nsub)
        integer, intent(in) :: nsub
        character(len=32) :: env = ''
        hard_limits = nsub .gt. 1
        flux_clip = nsub .gt. 1
        ca_smooth = nsub .gt. 1
        implicit_vdiff = nsub .gt. 1
        physical_limits = nsub .gt. 1
        call get_environment_variable('STAGE1110_HARD_LIMITS', env)
        if (len_trim(env) .gt. 0) hard_limits = truthy(env)
        call get_environment_variable('STAGE1110_FLUX_CLIPPING', env)
        if (len_trim(env) .gt. 0) flux_clip = truthy(env)
        call get_environment_variable('STAGE1110_CA_SMOOTHING', env)
        if (len_trim(env) .gt. 0) ca_smooth = truthy(env)
        call get_environment_variable('STAGE1110_IMPLICIT_VDIFF', env)
        if (len_trim(env) .gt. 0) implicit_vdiff = truthy(env)
        call get_environment_variable('STAGE1110_PHYSICAL_LIMITS', env)
        if (len_trim(env) .gt. 0) physical_limits = truthy(env)
        print '(A,L1,A,L1,A,L1,A,L1,A,L1)', '>>> Stage 11.10.4 thermo: HARD=', hard_limits, &
            ' CLIP=', flux_clip, ' CA_SMOOTH=', ca_smooth, ' IMPLICIT_VDIFF=', implicit_vdiff, &
            ' PHYSICAL=', physical_limits
    end subroutine s1110_thermo_init

    logical function truthy(v)
        character(len=*), intent(in) :: v
        truthy = (trim(v).eq.'true' .or. trim(v).eq.'TRUE' .or. trim(v).eq.'1' .or. trim(v).eq.'ON')
    end function truthy

    pure real function s1110_clip_heat_flux(q) result(out)
        real, intent(in) :: q
        out = max(-500.0, min(500.0, q))
    end function s1110_clip_heat_flux

    subroutine s1110_hard_limits()
        integer :: i, j, k
        real :: tf, spsu
        if (.not. hard_limits) return
        do j = 1, js1
            do i = 1, is1
                if (kt1(i, j) .le. 0) cycle
                do k = 1, kt1(i, j)
                    spsu = max(0.0, min(40.0, s2(i, j, k)*1000.0))
                    s2(i, j, k) = spsu/1000.0
                    tf = -0.0575*spsu + 1.710523e-3*spsu*sqrt(max(spsu,0.0)) &
                         - 2.154996e-4*spsu*spsu
                    t2(i, j, k) = max(tf, min(30.0, t2(i, j, k)))
                    if (physical_limits) then
                        if (spsu .lt. 0.1 .and. t2(i, j, k) .lt. 0.0) t2(i, j, k) = 0.0
                        if (t2(i, j, k) .lt. 0.0) s2(i, j, k) = max(s2(i, j, k), 0.0001)
                    end if
                end do
            end do
        end do
    end subroutine s1110_hard_limits

    subroutine s1110_ca_smoothing()
        integer :: i, j, k, ki
        real :: tm, sm
        if (.not. ca_smooth) return
        do j = 1, js1
            do i = 1, is1
                ki = kt1(i, j)
                if (ki .lt. 3) cycle
                do k = 2, ki - 1
                    tm = 0.25*t2(i, j, k - 1) + 0.5*t2(i, j, k) + 0.25*t2(i, j, k + 1)
                    sm = 0.25*s2(i, j, k - 1) + 0.5*s2(i, j, k) + 0.25*s2(i, j, k + 1)
                    t2(i, j, k) = tm
                    s2(i, j, k) = sm
                end do
            end do
        end do
    end subroutine s1110_ca_smoothing

    ! Backward-Euler vertical diffusion on each wet column; Thomas solve.
    subroutine s1110_implicit_vdiff(dt_step)
        real, intent(in) :: dt_step
        integer :: i, j, k, ki
        real :: dzm, alpha, a(ks), b(ks), c(ks), d(ks), cp(ks), dp(ks), x(ks), tt(ks), ss(ks)
        if (.not. implicit_vdiff) return
        do j = 1, js1
            do i = 1, is1
                ki = kt1(i, j)
                if (ki .lt. 2) cycle
                dzm = 10.0
                alpha = kv_diff*dt_step/(dzm*dzm)
                do k = 1, ki
                    a(k) = -alpha
                    b(k) = 1.0 + 2.0*alpha
                    c(k) = -alpha
                    d(k) = t2(i, j, k)
                    tt(k) = t2(i, j, k)
                    ss(k) = s2(i, j, k)
                end do
                a(1) = 0.0; c(ki) = 0.0
                b(1) = 1.0 + alpha; b(ki) = 1.0 + alpha
                ! Thomas for T
                cp(1) = c(1)/b(1); dp(1) = d(1)/b(1)
                do k = 2, ki
                    cp(k) = c(k)/(b(k) - a(k)*cp(k - 1))
                    dp(k) = (d(k) - a(k)*dp(k - 1))/(b(k) - a(k)*cp(k - 1))
                end do
                x(ki) = dp(ki)
                do k = ki - 1, 1, -1
                    x(k) = dp(k) - cp(k)*x(k + 1)
                end do
                do k = 1, ki
                    t2(i, j, k) = x(k)
                    d(k) = ss(k)
                end do
                cp(1) = c(1)/b(1); dp(1) = d(1)/b(1)
                do k = 2, ki
                    cp(k) = c(k)/(b(k) - a(k)*cp(k - 1))
                    dp(k) = (d(k) - a(k)*dp(k - 1))/(b(k) - a(k)*cp(k - 1))
                end do
                x(ki) = dp(ki)
                do k = ki - 1, 1, -1
                    x(k) = dp(k) - cp(k)*x(k + 1)
                end do
                do k = 1, ki
                    s2(i, j, k) = x(k)
                end do
            end do
        end do
    end subroutine s1110_implicit_vdiff
end module stage1110_thermo
