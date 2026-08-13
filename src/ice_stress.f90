module ice_stress
    use param
    use ice_deform
    implicit none

contains

    subroutine stress()
        integer :: i, j, i1, j1, k, k_crit
        real :: a, b, a1, a2, b1, b2, sor, cor, ssxx, ssyy, ssxy
        real :: scrit, angl
        real, parameter :: dx_val = 1389000.0
        real, parameter :: dt1_val = 120.0

        ! --- БЛОК ПОДГОТОВКИ ПОЛЕЙ С ВЫЗОВОМ DEFORM ---

        do j = 1, js
            do i = 1, is
                i1 = i + 1
                epr(i1, j + 1) = exx(i, j)
            end do
        end do

        call deform(1, dx_val, dt1_val)

        do j = 1, js
            j1 = j + 1
            do i = 1, is
                i1 = i + 1
                exx(i, j) = epr(i1, j1)
                epr(i1, j1) = eyy(i, j)
            end do
        end do

        call deform(2, dx_val, dt1_val)

        do j = 1, js
            j1 = j + 1
            do i = 1, is
                i1 = i + 1
                eyy(i, j) = epr(i1, j1)
                epr(i1, j1) = exy(i, j)
            end do
        end do

        call deform(3, dx_val, dt1_val)

        do j = 1, js
            do i = 1, is
                i1 = i + 1
                exy(i, j) = epr(i1, j + 1)
            end do
        end do

        ! --- ОСНОВНОЙ ЦИКЛ РАСЧЕТА НАПРЯЖЕНИЙ ---
        do j = 1, js
            do i = 1, is
                if (kt1(i, j) .eq. 0) cycle

                if (ans(i, j) .lt. 0.95) then
                    exx(i, j) = 0.0; eyy(i, j) = 0.0; exy(i, j) = 0.0
                    sxx(i, j) = 0.0; syy(i, j) = 0.0; sxy(i, j) = 0.0
                    cycle
                end if

                a = exx(i, j) + eyy(i, j)
                b = (sxx(i, j) + syy(i, j))*0.5

                if (a .gt. 0.0 .and. b .ge. 0.0) then
                    exx(i, j) = 0.0; eyy(i, j) = 0.0; exy(i, j) = 0.0
                    sxx(i, j) = 0.0; syy(i, j) = 0.0; sxy(i, j) = 0.0
                    cycle
                end if

                ssxx = exx(i, j)*1.e7
                ssyy = eyy(i, j)*1.e7
                ssxy = exy(i, j)*1.e7

                a = (ssxx + ssyy)*0.5
                b1 = (ssxx - ssyy)*0.5
                b2 = sqrt(b1*b1 + ssxy*ssxy)
                a1 = a + b2
                a2 = a - b2

                k_crit = 2
                do k = 2, ngr
                    if (an1(i, j, k + 1) .gt. 0.05) then
                        k_crit = k
                        exit
                    end if
                end do

                scrit = -0.43e5*hst(k_crit)**2

                if (a2 .gt. scrit .and. a1 .lt. 0.0) then
                    sxx(i, j) = ssxx; syy(i, j) = ssyy; sxy(i, j) = ssxy
                    cycle
                end if

                if (a2 .lt. scrit) a2 = scrit
                if (a1 .lt. scrit) a1 = scrit
                if (a1 .gt. 0.0) a1 = 0.0
                if (a2 .gt. 0.0) a2 = 0.0

                angl = atan2(ssxy, b1)*0.5
                cor = cos(-angl)
                sor = sin(-angl)

                sxx(i, j) = a1*cor*cor + a2*sor*sor
                syy(i, j) = a1*sor*sor + a2*cor*cor
                sxy(i, j) = -(a1 - a2)*cor*sor

                exx(i, j) = sxx(i, j)*1.e-7
                eyy(i, j) = syy(i, j)*1.e-7
                exy(i, j) = sxy(i, j)*1.e-7
            end do
        end do

    end subroutine stress

end module ice_stress
