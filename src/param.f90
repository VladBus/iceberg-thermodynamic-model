module param
    implicit none

    ! Параметры сетки
    integer, parameter :: is = 132, js = 104, ks = 18, is1 = 133, js1 = 105, ks1 = 19
    integer, parameter :: is2 = 131, js2 = 103, ks2 = 17
    integer, parameter :: is3 = 134, js3 = 106, ngr = 5, ngr1 = 6, ngr2 = 4
    integer, parameter :: is4 = 135, js4 = 107
    integer, parameter :: li = 4, lj = 35

    ! Массивы океанского блока
    real :: map1(is1, js1), z(ks), dz(ks1), dz1(ks), &
            u1(is1, js1, ks), u2(is1, js1, ks), v1(is1, js1, ks), v2(is1, js1, ks), &
            fku(is1, js1), drx(is1, js1), dry(is1, js1), skz(is1, js1)

    double precision :: uca(ks1), unu(ks1), vca(ks1), vnu(ks1)

    real :: hu(is1, js1), hv(is1, js1), y1(is1, js1), y2(is1, js1), &
            up1(is1, js1), up2(is1, js1), vp1(is1, js1), vp2(is1, js1), &
            fi(is1, js1), dl(is1, js1), fu(is1, js1), fv(is1, js1), &
            ym1(is1, js1), ym2(is1, js1), adx(is1, js1, ks1), ady(is1, js1, ks1), &
            amp(li, lj), faz(li, lj), qq(li), q(li), yyv(5000), v00(li), &
            amp1(133, 4), amp2(105, 4), amp3(133, 4), &
            uf1(5000), vf1(5000), uf2(5000), vf2(5000), uuf(5000), vvf(5000), &
            apn(5000, ngr1), wiu(5000), wiv(5000)

    real :: t1(is1, js1, ks), t2(is1, js1, ks), s1(is1, js1, ks), s2(is1, js1, ks)

    real :: ht(is1, js1), ro(is1, js1, ks), &
            w(is1, js1, ks1), tt(ks1), ss(ks1), rr(ks1), skt(is1, js1), &
            cd(is1, js1, ks), apx(is1, js1, ks), apy(is1, js1, ks), apz(is1, js1, ks1)

    integer :: kk1(is1, js1), kt1(is1, js1), idx(is1, js1), idy(is1, js1), &
               it(is1, js1), kush(is1, js1), kvsh(is1, js1), iku(is1, js1), ikv(is1, js1), &
               iip(is1, js1)

    ! Массивы ледового блока
    real :: u0(is1, js1), v0(is1, js1), u(is1, js1), v(is1, js1), &
            wice1(is1, js1, ngr), an1(is1, js1, ngr1), hice(is1, js1, ngr), &
            an3(is1, js1), wices(is1, js1), hices(is1, js1), ans(is1, js1), &
            cd2(is1, js1), txic(is1, js1), tyic(is1, js1), &
            apx2(is1, js1), apy2(is1, js1), exx(is1, js1), eyy(is1, js1), &
            exy(is1, js1), epr(is3, js3), sxx(is1, js1), syy(is1, js1), sxy(is1, js1), &
            hsnow(is1, js1, ngr), tpar(ngr1), spar(ngr1), &
            anp(ngr), danp(ngr), hsnp(ngr), hicp(ngr), &
            sicst(ngr), hst(ngr), hmax(ngr), alsn(12)

    ! Массивы метеорологических данных
    real :: tx(is1, js1), ty(is1, js1), dpx(is1, js1), dpy(is1, js1), &
            tx1(is1, js1), ty1(is1, js1), dpx1(is1, js1), dpy1(is1, js1), &
            tatm1(is1, js1, 12), tatm(is1, js1), cloud1(is1, js1, 12), &
            cloud(is1, js1), humid(is1, js1), patm(is1, js1), wind(is1, js1), &
            wmonth(12), sfal(12), &
            windx1(is1, js1), windy1(is1, js1), windx(is1, js1), &
            windy(is1, js1), &
            p(1420, 100), pp(1420), x01(1330), y01(1330), &
            tc1(is1, ks), sc1(is1, ks), &
            tc2(js1, ks), sc2(js1, ks), &
            tc3(15, ks), sc3(15, ks), &
            tc4(3, ks), sc4(3, ks)

    integer :: np(is4, js4), np1(1330, 4), nat(li)
    character(len=20) :: vix1, vix2, nam

    ! Прочие переменные из блоков (сведены вместе для удобства)
    real :: mapp, anpr(5), wicpr(5), hpr(5)
    real :: ccc(4), bbb(4), om(4), faz1(is1, li), faz2(js1, li), faz3(is1, li)
    real :: fi1(is4, js4), dl1(is4, js4), tauu(is1, js1), &
            alf(is1, js1), pp1(is4, js4), zzz(is1, js1), p1(is1, js1)
    character(len=10) :: ewin, ep, evet
    real :: pp2(is4, js4)
    real :: fff(li)
    integer :: mmm(12)

    ! Инициализация данных (блок DATA)
    data z/250., 500., 1000., 1500., 2000., 2500., 3000., 4000., &
        5000., 7500., 10000., 15000., 20000., 25000., &
        30000., 40000., 50000., 60000./
    data hst/0.2, 0.5, 0.95, 1.6, 2.5/
    data hmax/0.3, 0.7, 1.20, 2.0, 50./
    data sicst/10.e-3, 6.e-3, 5.e-3, 4.5e-3, 4.e-3/
    data alsn/0.85, 0.85, 0.83, 0.81, 0.82, 0.78, 0.64, 0.69, 0.84, &
        0.85, 0.85, 0.85/
    data mmm/31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31/

end module param
