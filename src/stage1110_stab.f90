! Stage 11.10.3 — high-speed momentum drag and boundary clip.
! Selected as the low-risk alternative to a full Smagorinsky rewrite.
module stage1110_stab
    use param
    implicit none
    logical, save :: stab_active = .false.
    logical, save :: drag_enabled = .true.
    real, parameter :: SPEED_THRESHOLD = 200.0   ! cm/s (2 m/s)
    real, parameter :: SPEED_CLIP = 500.0        ! cm/s (5 m/s)
contains
    subroutine s1110_stab_init(nsub)
        integer, intent(in) :: nsub
        character(len=32) :: env = ''
        call get_environment_variable('STAGE1110_HIGH_SPEED_DRAG', env)
        if (len_trim(env) .gt. 0) then
            drag_enabled = .not. (trim(env) .eq. 'false' .or. trim(env) .eq. '0' .or. trim(env) .eq. 'OFF')
        end if
        stab_active = (nsub .gt. 1) .and. drag_enabled
        if (stab_active) print *, '>>> Stage 11.10.3: high-speed momentum drag ACTIVE (threshold 2 m/s, clip 5 m/s)'
    end subroutine s1110_stab_init

    subroutine s1110_apply_momentum(dt_step)
        real, intent(in) :: dt_step
        integer :: i, j, k
        real :: sp, fac
        if (.not. stab_active) return
        do j = 1, js1
            do i = 1, is1
                if (kt1(i, j) .le. 0) cycle
                do k = 1, kt1(i, j)
                    sp = sqrt(u2(i, j, k)**2 + v2(i, j, k)**2)
                    if (sp .gt. SPEED_THRESHOLD .and. sp .gt. 0.0) then
                        fac = 1.0/(1.0 + 5.0e-4*dt_step*max(0.0, sp - SPEED_THRESHOLD)/100.0)
                        u2(i, j, k) = u2(i, j, k)*fac
                        v2(i, j, k) = v2(i, j, k)*fac
                        sp = sp*fac
                    end if
                    if ((i .le. 3 .or. i .ge. is - 2 .or. j .le. 3 .or. j .ge. js - 2) .and. sp .gt. SPEED_CLIP) then
                        u2(i, j, k) = u2(i, j, k)*SPEED_CLIP/sp
                        v2(i, j, k) = v2(i, j, k)*SPEED_CLIP/sp
                    end if
                end do
            end do
        end do
    end subroutine s1110_apply_momentum
end module stage1110_stab
