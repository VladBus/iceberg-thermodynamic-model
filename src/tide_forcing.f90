module tide_forcing
    use param
    implicit none

contains

    subroutine datte()
        ! Локальные переменные
        real :: god, den, hour, gk
        integer :: mes, mu, i, mi, si, nv
        real :: q1, q2, q3, q4, ras, sm, dn, h, st, presh, r
        real :: su, an, bn, cn, dov, doz, dv1, a1n, b1n, c1n, uu1, u3, u4

        ! Перенос параметров из глобального массива NAT
        god = real(nat(1))
        mes = nat(2)
        den = real(nat(3))
        hour = real(nat(4))

        ! Константы приливных гармоник
        q1 = 28.9841042
        q2 = 30.0
        q3 = 15.041069
        q4 = 13.943036
        ras = 57.29578

        ! Расчет количества високосных дней
        gk = god - 1901.0
        sm = 0.0
        mu = mes - 1

        do i = 1, mu
            sm = sm + real(mmm(i))
        end do

        if (mu .eq. 0) sm = 0.0

        mi = int(gk/4.0)
        si = mi*4

        if (abs((gk - real(si)) - 3.0) .lt. 1e-8 .and. mes .gt. 2) then
            sm = sm + 1.0
        end if

        ! Общее время в сутках
        dn = god*365.0 + real(mi) + sm + den - 0.5

        h = 279.696678 + 0.9856473354*dn
        st = 270.434164 + 13.1763965268*dn
        presh = 334.329556 + 0.1114040803*dn
        r = presh/ras

        ! Расчет фаз прилива (с выделением дробной части угла)
        v00(1) = (2.0*h - 2.0*st + q1*hour)/360.0
        nv = int(v00(1))
        v00(1) = (v00(1) - real(nv))*360.0

        v00(2) = q2*hour

        v00(3) = (h + 90.0 + q3*hour)/360.0
        nv = int(v00(3))
        v00(3) = (v00(3) - real(nv))*360.0

        v00(4) = (h - 2.0*st + 270.0 + q4*hour)/360.0
        nv = int(v00(4))
        v00(4) = (v00(4) - real(nv))*360.0

        ! Астрономические поправки
        su = (259.183275 - 0.0529539222*dn)/ras
        an = sin(su)
        bn = sin(2.0*su)
        cn = sin(3.0*su)

        dov = 12.94*an - 1.34*bn + 0.19*cn
        doz = (11.87*an - 1.34*bn + 0.19*cn)*2.0
        dv1 = 8.86*an - 0.68*bn + 0.07*cn

        a1n = cos(su)
        b1n = cos(2.0*su)
        c1n = cos(3.0*su)

        uu1 = doz - 2.0*dov
        u3 = -dv1
        u4 = doz - dov

        ! Амплитудные множители
        fff(1) = 1.00035 - 0.03733*a1n + 0.00017*b1n + 0.00001*c1n
        fff(2) = 1.0       ! Инициализация для безопасности
        fff(3) = 1.006 + 0.116*a1n - 0.0088*b1n + 0.0006*c1n
        fff(4) = 1.0089 + 0.1871*a1n - 0.0147*b1n + 0.0014*c1n

        ! Приведение фаз к диапазону 0-360 и добавление поправок
        if (v00(1) .le. 0.0) v00(1) = v00(1) + 360.0
        if (v00(3) .le. 0.0) v00(3) = v00(3) + 360.0
        if (v00(4) .le. 0.0) v00(4) = v00(4) + 360.0

        v00(1) = v00(1) + uu1
        v00(3) = v00(3) + u3
        v00(4) = v00(4) + u4

    end subroutine datte

end module tide_forcing
