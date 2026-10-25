! ==============================================================================
! Stage 11.8.0 T3-CORRECTIVE-3 (E6 fallback): boundary sponge.
! Rayleigh damping of 3-D momentum and barotropic transports in a boundary band.
! Default OFF (STAGE118_BOUNDARY_SPONGE=true selects it); legacy bit-identical.
! This is an amplifier mitigation, not the CA/density root fix.
! ==============================================================================
module stage118_boundary_sponge
    use param
    implicit none

contains

    subroutine apply_boundary_sponge(dt_step)
        real, intent(in) :: dt_step
        integer :: i, j, k, ki, dist, width
        real :: ramp, fac, tau

        width = 8
        tau = 86400.0  ! 1-day nominal damping at the wall
        do j = 2, js
            do i = 2, is
                dist = min(i - 1, is - i, j - 1, js - j)
                if (dist .gt. width) cycle
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                ramp = real(width - dist + 1)/real(width)
                fac = exp(-dt_step*ramp/tau)
                do k = 1, ki
                    u2(i, j, k) = u2(i, j, k)*fac
                    v2(i, j, k) = v2(i, j, k)*fac
                end do
                up2(i, j) = up2(i, j)*fac
                vp2(i, j) = vp2(i, j)*fac
            end do
        end do
    end subroutine apply_boundary_sponge

end module stage118_boundary_sponge
