! ==============================================================================
! Stage 11.8.0 T5-CORRECTIVE-4: minimal density repair.
! If EOS(T,S,p) gives RO<0, adjust the more efficient tracer (T or S) by the
! minimum amount needed to make RO>=0. Default OFF (D-33).
! ==============================================================================
module stage118_density_repair
    use param
    use equation_of_state, only: eos_density_f64
    use stage118_physics_switches, only: s118_density_repair
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none
    private
    public :: repair_density

contains

    subroutine repair_density()
        integer :: i, j, k, ki, iter
        real(real64) :: ro, dT, dS, need, candT, candS, epsT, epsS, p
        real(real64) :: t0, s0
        integer :: nrep

        if (.not. s118_density_repair) return
        epsT = 1.0e-2_real64
        epsS = 1.0e-5_real64
        nrep = 0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    p = real(z(k)*0.01, real64)  ! dbar
                    ro = eos_density_f64(real(t2(i,j,k), real64), &
                                         real(s2(i,j,k), real64), p)
                    if (ro .ge. 0.0_real64) cycle
                    do iter = 1, 3
                        ro = eos_density_f64(real(t2(i,j,k), real64), &
                                             real(s2(i,j,k), real64), p)
                        if (ro .ge. 0.0_real64) exit
                        t0 = real(t2(i,j,k), real64)
                        s0 = real(s2(i,j,k), real64)
                        dT = (eos_density_f64(t0+epsT, s0, p) - &
                              eos_density_f64(t0-epsT, s0, p))/(2.0_real64*epsT)
                        dS = (eos_density_f64(t0, s0+epsS, p) - &
                              eos_density_f64(t0, s0-epsS, p))/(2.0_real64*epsS)
                        need = -ro + 1.0e-6_real64  ! g/cm3 target margin
                        ! compare in kg/m3 units: |dT|*1000 vs |dS| (per PSU)
                        if (abs(dT)*1000.0_real64 .gt. abs(dS)) then
                            if (abs(dT) .lt. 1.0e-12_real64) cycle
                            t2(i,j,k) = real(t0 + need/dT, kind(1.0))
                        else
                            if (abs(dS) .lt. 1.0e-12_real64) cycle
                            s2(i,j,k) = real(s0 + need/dS, kind(1.0))
                        end if
                        nrep = nrep + 1
                    end do
                end do
            end do
        end do
        if (nrep .gt. 0) print *, 'STAGE118 DENSITY REPAIR: adjusted ', nrep, ' cells'
    end subroutine repair_density

end module stage118_density_repair
