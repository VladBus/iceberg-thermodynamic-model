! ==============================================================================
! Модуль: stage115c81_attr
! Назначение: Stage 11.5C.8.1 — full-field term attribution: на границах
!             B200/B210/B280 считает per-term first-order dE по ВСЕМ
!             wet-ячейкам, аккумулирует за day-1, на входе в day-2 ранжирует
!             top-1000/100/20 + all-positive и пишет 4 строки-агрегата.
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — только чтение + свои буферы.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C81_ATTR=true
! Вызывать: op_before (snap U2/V2) / op_after (счёт+аккумуляция) для
! op ∈ {B200,B210,B280} — 6 вызовов/сабстеп.
! Бакеты B200 — ТО ЖЕ зеркало, что C6 (sum/sum1 рекуррента c8·dz +
! s22_freeze_tw; auu/avv-разложение; ice≡0; solve-довесок):
!   dU_TW, dU_DPX, dU_Cor, dU_Lap, dU_solve (+V-аналоги; DPY в V).
! Бакеты B280 — ТО ЖЕ зеркало C6: btp=0.5·(UP2+UP2nbr)/hht,
! bcl=−∫U2·dzz/hht (recompute из pre-B280 столбца).
! B210 — только exact total (нейтрален по 11.5C.8; term-сплит не нужен).
! First-order E: dE_term = 2·Ubef·dU_term + 2·Vbef·dV_term (SHARES суммируются
! в first-order total; рядом пишется exact-total для контекста quadratic
! fill; см. 11.5C.8R-fix — first-order alone НЕ бюджет).
! Аккумуляторы day-1 (8 полей × wet): aTW,aCor,aDPX,aLap,aSol (B200),
! aBtp,aBcl (B280), aB210 (exact). На первом B200_before дня 2: ранжир по
! cell-total (Σ8) → top-1000/100/20 + all-positive (total>0) → суммирование
! по множествам → `term_attribution_aggregates.csv` (flush; 4 строки):
!   subset,ncells,sum_B200_TW,sum_B200_Cor,sum_B200_DPX,sum_B200_Lap,
!   sum_B200_solve,sum_B280_btp,sum_B280_bcl,sum_B210,total_firstorder,total_exact
! total_exact: Σ exact-dE(B200+B210+B280) по тем же ячейкам (считается
! параллельно: eX arrays? НЕТ — exact-total = Σ first-order + quadratic;
! quadratic per-cell: q = dU²+dV² per op — аккумулируем 9-м полем aQ.
! total_exact = Σ(a* + aQ) по множеству.) Итого 9 аккумуляторов (~9 МБ).
! NaN/Inf в любых входах ячейки → пропуск ячейки в этом сабстепе (счёт ninv
! в лог один раз/день; не заражает суммы).
! Сабстеп-счётчик: только на B200_before с iii-rollover (урок 11.5C.5/8).
! Литералы — те же provenance, что C6: C1=981, C3=7.5e6/1389000²,
! C8=0.25/1389000, DT=3600 (верно IFF DT=3600/MM2=24 — матрица 11.5C.x).
! ==============================================================================
module stage115c81_attr
    use param
    use stage1022_diagnostics, only: s22_freeze_tw
    implicit none

    real, parameter :: T81_DX = 1389000.0
    real, parameter :: T81_C1 = 981.0
    real, parameter :: T81_C3 = 7.5e6/(1389000.0*1389000.0)
    real, parameter :: T81_C8 = 0.25/1389000.0
    real, parameter :: T81_DT = 3600.0

    logical, save :: t81_on = .false.
    integer, save :: t81_substep = 0
    integer, save :: t81_prev_iii = -1
    integer, save :: attr_unit = 180
    logical, save :: attr_open = .false.
    logical, save :: dumped = .false.

    real, save, allocatable :: su(:, :, :), sv(:, :, :)
    ! 9 аккумуляторов day-1: TW,Cor,DPX,Lap,Sol,Btp,Bcl,B210,Q
    real, save, allocatable :: aTW(:, :, :), aCor(:, :, :), aDPX(:, :, :)
    real, save, allocatable :: aLap(:, :, :), aSol(:, :, :)
    real, save, allocatable :: aBtp(:, :, :), aBcl(:, :, :)
    real, save, allocatable :: aB10(:, :, :), aQ(:, :, :)
    logical, save :: acc_alloc = .false.
    integer, save :: ninv_total = 0

contains

    subroutine s115c81_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C81_ATTR', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t81_on = .true.
            print *, 'STAGE115C81: attr= T'
        end if
    end subroutine s115c81_init

    logical function t81_is_invalid(val)
        real, intent(in) :: val
        t81_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t81_is_invalid

    subroutine s115c81_open()
        if (attr_open) return
        open (unit=attr_unit, file='term_attribution_aggregates.csv', status='replace', action='write')
        write (attr_unit, '(A)') 'subset,ncells,' // &
            'sum_B200_TW,sum_B200_Cor,sum_B200_DPX,sum_B200_Lap,sum_B200_solve,' // &
            'sum_B280_btp,sum_B280_bcl,sum_B210,total_firstorder,total_exact'
        attr_open = .true.
    end subroutine s115c81_open

    subroutine s115c81_alloc()
        if (allocated(su)) return
        allocate (su(is1, js1, ks1), sv(is1, js1, ks1))
        su = 0.0; sv = 0.0
    end subroutine s115c81_alloc

    subroutine s115c81_acc_alloc()
        if (acc_alloc) return
        allocate (aTW(is1, js1, ks1), aCor(is1, js1, ks1), aDPX(is1, js1, ks1))
        allocate (aLap(is1, js1, ks1), aSol(is1, js1, ks1))
        allocate (aBtp(is1, js1, ks1), aBcl(is1, js1, ks1))
        allocate (aB10(is1, js1, ks1), aQ(is1, js1, ks1))
        aTW = 0.0; aCor = 0.0; aDPX = 0.0; aLap = 0.0; aSol = 0.0
        aBtp = 0.0; aBcl = 0.0; aB10 = 0.0; aQ = 0.0
        acc_alloc = .true.
    end subroutine s115c81_acc_alloc

    ! phase=0: snap (+счётчик/дамп только на B200); phase=1: счёт.
    subroutine s115c81_op(day, iii, op, phase)
        integer, intent(in) :: day, iii, phase
        character(len=*), intent(in) :: op
        if (.not. t81_on) return
        call s115c81_open()
        call s115c81_alloc()
        call s115c81_acc_alloc()
        if (phase .eq. 0) then
            if (op .eq. 'B200') then
                if (iii .le. t81_prev_iii) then
                    if (day .eq. 2 .and. .not. dumped) call s115c81_dump()
                    t81_substep = 0
                end if
                t81_prev_iii = iii
                t81_substep = t81_substep + 1
            end if
            su(:, :, :) = u2(:, :, :)
            sv(:, :, :) = v2(:, :, :)
        else
            if (day .gt. 1 .or. dumped) return
            if (op .eq. 'B200') call s115c81_b200()
            if (op .eq. 'B210') call s115c81_b210()
            if (op .eq. 'B280') call s115c81_b280()
        end if
    end subroutine s115c81_op

    ! B200: recompute-зеркало по всем wet + first-order E в аккумуляторы.
    subroutine s115c81_b200()
        integer :: i, j, k, ki, i1, i2, j1, j2, k1, kk
        real :: hht, a, b, a1, b1, dzz, dzz1, cc, s, s1, uij, vij
        real :: ri2j, rij, ri2j2, rij2, asa1, asa, slapu, slapv
        real :: fu_tw, fu_pg, fu_lp, fv_tw, fv_pg, fv_lp
        real :: du_tw, du_pg, du_co, du_lp, du_sv
        real :: dv_tw, dv_pg, dv_co, dv_lp, dv_sv
        real :: ub, vb, ua, va, q
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                i1 = i + 1; i2 = i - 1; j1 = j + 1; j2 = j - 1
                hht = map1(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle
                asa1 = fku(i, j)*0.5*T81_DT
                asa = 1.0 + asa1*asa1
                ri2j = ro(i2, j, 1); rij = ro(i, j, 1)
                ri2j2 = ro(i2, j2, 1); rij2 = ro(i, j2, 1)
                a = ri2j + rij - ri2j2 - rij2
                b = ri2j2 + ri2j - rij2 - rij
                dzz = dz(1)
                s = 0.0; s1 = 0.0
                do k = 1, ki
                    k1 = k + 1
                    dzz1 = dz(k1)
                    uij = u1(i, j, k); vij = v1(i, j, k)
                    ri2j = ro(i2, j, k); rij2 = ro(i, j2, k)
                    rij = ro(i, j, k); ri2j2 = ro(i2, j2, k)
                    a1 = ri2j + rij - ri2j2 - rij2
                    b1 = ri2j2 + ri2j - rij2 - rij
                    cc = T81_C8*dzz
                    s = s + (a + a1)*cc
                    s1 = s1 + (b + b1)*cc
                    if (s22_freeze_tw) then
                        s = 0.0
                        s1 = 0.0
                    end if
                    if (abs(hht - z(k)) .lt. 1e-6) then
                        ! Дно: код пишет 0 (cycle) — пропускаем ячейку
                        ! (вклад нулевой и в production).
                        a = a1; b = b1; dzz = dzz1
                        cycle
                    end if
                    slapu = u1(i, j2, k) + u1(i, j1, k) + u1(i2, j, k) + u1(i1, j, k) - 4.0*uij
                    slapv = v1(i1, j, k) + v1(i2, j, k) + v1(i, j1, k) + v1(i, j2, k) - 4.0*vij
                    fu_tw = -T81_C1*s; fu_pg = -dpx(i, j); fu_lp = T81_C3*slapu
                    fv_tw = -T81_C1*s1; fv_pg = -dpy(i, j); fv_lp = T81_C3*slapv
                    du_tw = T81_DT*(fu_tw + asa1*fv_tw)/asa
                    du_pg = T81_DT*(fu_pg + asa1*fv_pg)/asa
                    du_lp = T81_DT*(fu_lp + asa1*fv_lp)/asa
                    du_co = (asa1*vij + asa1*(vij - asa1*uij))/asa
                    du_sv = uij/asa - uij
                    dv_tw = T81_DT*(fv_tw - asa1*fu_tw)/asa
                    dv_pg = T81_DT*(fv_pg - asa1*fu_pg)/asa
                    dv_lp = T81_DT*(fv_lp - asa1*fu_lp)/asa
                    dv_co = (-asa1*uij - asa1*asa1*vij)/asa
                    dv_sv = (vij - asa1*uij)/asa - vij
                    ub = su(i, j, k); vb = sv(i, j, k)
                    ua = u2(i, j, k); va = v2(i, j, k)
                    if (t81_is_invalid(ub) .or. t81_is_invalid(vb) .or. &
                        t81_is_invalid(ua) .or. t81_is_invalid(va) .or. &
                        t81_is_invalid(du_tw + du_pg + du_co + du_lp + du_sv)) then
                        ninv_total = ninv_total + 1
                    else
                        aTW(i, j, k) = aTW(i, j, k) + 2.0*ub*du_tw + 2.0*vb*dv_tw
                        aCor(i, j, k) = aCor(i, j, k) + 2.0*ub*du_co + 2.0*vb*dv_co
                        aDPX(i, j, k) = aDPX(i, j, k) + 2.0*ub*du_pg + 2.0*vb*dv_pg
                        aLap(i, j, k) = aLap(i, j, k) + 2.0*ub*du_lp + 2.0*vb*dv_lp
                        aSol(i, j, k) = aSol(i, j, k) + 2.0*ub*du_sv + 2.0*vb*dv_sv
                        q = (ua*ua + va*va) - (ub*ub + vb*vb)
                        aQ(i, j, k) = aQ(i, j, k) + q - &
                            (2.0*ub*(du_tw + du_pg + du_co + du_lp + du_sv) + &
                             2.0*vb*(dv_tw + dv_pg + dv_co + dv_lp + dv_sv))
                    end if
                    a = a1
                    b = b1
                    dzz = dzz1
                end do
            end do
        end do
    end subroutine s115c81_b200

    ! B210: только exact total per cell (нейтрален; сплита не надо).
    subroutine s115c81_b210()
        integer :: i, j, k, ki
        real :: ub, vb, ua, va
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                if (abs(map1(i, j) - 8888.0) .lt. 1e-8) cycle
                do k = 1, ki
                    ub = su(i, j, k); vb = sv(i, j, k)
                    ua = u2(i, j, k); va = v2(i, j, k)
                    if (t81_is_invalid(ub) .or. t81_is_invalid(vb) .or. &
                        t81_is_invalid(ua) .or. t81_is_invalid(va)) then
                        ninv_total = ninv_total + 1
                        cycle
                    end if
                    aB10(i, j, k) = aB10(i, j, k) + 2.0*ub*(ua - ub) + 2.0*vb*(va - vb)
                    aQ(i, j, k) = aQ(i, j, k) + ((ua - ub)*(ua - ub) + (va - vb)*(va - vb))
                end do
            end do
        end do
    end subroutine s115c81_b210

    ! B280: recompute-зеркало (btp/bcl) + first-order E.
    subroutine s115c81_b280()
        integer :: i, j, k, ki, i2, j2, k1
        real :: hht, dzz, s, s1, btp_u, btp_v, bcl_u, bcl_v
        real :: ub, vb, ua, va
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                i2 = i - 1; j2 = j - 1
                hht = map1(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle
                s = 0.0; s1 = 0.0
                do k = 1, ki
                    k1 = k + 1
                    if (k .eq. ki) then
                        if (ki .ne. 1) then
                            dzz = hht - 0.5*(z(ki) + z(ki - 1))
                        else
                            dzz = hht
                        end if
                    else
                        dzz = dz1(k)
                    end if
                    s = su(i, j, k)*dzz + s
                    s1 = sv(i, j, k)*dzz + s1
                end do
                ! NOTE: интеграл по PRE-B280 столбцу: su/sv — снапшот до B280?
                ! snap сделан в s115c81_op(before) — да, su=pre-B280 u2. Верно.
                btp_u = 0.5*(up2(i, j) + up2(i2, j))/hht
                btp_v = 0.5*(vp2(i, j) + vp2(i, j2))/hht
                bcl_u = -s/hht
                bcl_v = -s1/hht
                do k = 1, ki
                    ub = su(i, j, k); vb = sv(i, j, k)
                    ua = u2(i, j, k); va = v2(i, j, k)
                    if (t81_is_invalid(ub) .or. t81_is_invalid(vb) .or. &
                        t81_is_invalid(ua) .or. t81_is_invalid(va) .or. &
                        t81_is_invalid(btp_u + bcl_u)) then
                        ninv_total = ninv_total + 1
                        cycle
                    end if
                    aBtp(i, j, k) = aBtp(i, j, k) + 2.0*ub*btp_u + 2.0*vb*btp_v
                    aBcl(i, j, k) = aBcl(i, j, k) + 2.0*ub*bcl_u + 2.0*vb*bcl_v
                    aQ(i, j, k) = aQ(i, j, k) + ((ua - ub)*(ua - ub) + (va - vb)*(va - vb))
                end do
            end do
        end do
    end subroutine s115c81_b280

    ! Дамп top-1000/100/20 + all-positive по cell-total day-1.
    subroutine s115c81_dump()
        integer :: i, j, k, ki, t, pos, cnt
        real :: tot
        integer, parameter :: HPSZ = 1000
        real :: hv(HPSZ)
        integer :: hi(HPSZ), hj(HPSZ), hk(HPSZ)
        integer :: si(HPSZ), sj(HPSZ), sk(HPSZ)
        real :: stw(HPSZ), sco(HPSZ), sdp(HPSZ), sla(HPSZ), sso(HPSZ)
        real :: sbt(HPSZ), sbc(HPSZ), sb1(HPSZ), stt(HPSZ), seq(HPSZ)
        integer :: n
        if (dumped) return
        dumped = .true.
        hv(:) = -huge(1.0)
        hi(:) = -1
        cnt = 0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    tot = aTW(i, j, k) + aCor(i, j, k) + aDPX(i, j, k) + &
                          aLap(i, j, k) + aSol(i, j, k) + &
                          aBtp(i, j, k) + aBcl(i, j, k) + aB10(i, j, k)
                    if (tot .le. 0.0) cycle
                    cnt = cnt + 1
                    pos = 1
                    do t = 2, HPSZ
                        if (hv(t) .lt. hv(pos)) pos = t
                    end do
                    if (tot .gt. hv(pos)) then
                        hv(pos) = tot
                        hi(pos) = i; hj(pos) = j; hk(pos) = k
                    end if
                end do
            end do
        end do
        ! Собрать top-1000 массивы для подмножеств (сортировка не нужна:
        ! top-100/20 = пересчёт heap minima? проще: взять все 1000 и
        ! просуммировать top-100/20 повторным min-heap — делаем напрямую:
        ! копируем heap, дважды урезаем. Для простоты: считаем суммы по
        ! всему heap (top-1000), затем top-100 и top-20 выбором максимумов.)
        n = 0
        do t = 1, HPSZ
            if (hi(t) .lt. 0) cycle
            n = n + 1
            si(n) = hi(t); sj(n) = hj(t); sk(n) = hk(t)
            stw(n) = aTW(hi(t), hj(t), hk(t)); sco(n) = aCor(hi(t), hj(t), hk(t))
            sdp(n) = aDPX(hi(t), hj(t), hk(t)); sla(n) = aLap(hi(t), hj(t), hk(t))
            sso(n) = aSol(hi(t), hj(t), hk(t))
            sbt(n) = aBtp(hi(t), hj(t), hk(t)); sbc(n) = aBcl(hi(t), hj(t), hk(t))
            sb1(n) = aB10(hi(t), hj(t), hk(t))
            stt(n) = hv(t)
            seq(n) = stt(n) + aQ(hi(t), hj(t), hk(t))
        end do
        call s115c81_writerow('top-1000', n, stw, sco, sdp, sla, sso, sbt, sbc, sb1, stt, seq)
        call s115c81_subset('top-100', n, si, sj, sk, stw, sco, sdp, sla, sso, sbt, sbc, sb1, stt, seq, 100)
        call s115c81_subset('top-20', n, si, sj, sk, stw, sco, sdp, sla, sso, sbt, sbc, sb1, stt, seq, 20)
        ! all-positive: все ячейки с total>0 (полный проход, без heap)
        call s115c81_allpos()
        print *, 'STAGE115C81: attribution dumped, top-cells =', n, ' ninv_total =', ninv_total
    end subroutine s115c81_dump

    subroutine s115c81_subset(name, n, si, sj, sk, stw, sco, sdp, sla, sso, sbt, sbc, sb1, stt, seq, m)
        character(len=*), intent(in) :: name
        integer, intent(in) :: n, m, si(n), sj(n), sk(n)
        real, intent(in) :: stw(n), sco(n), sdp(n), sla(n), sso(n)
        real, intent(in) :: sbt(n), sbc(n), sb1(n), stt(n), seq(n)
        integer :: t, u, cnt, mm
        real :: order(1000)
        integer :: idx(1000)
        real :: tmp
        if (n .le. 0) return
        ! Выбор top-m по stt (сортировка выбором на n≤1000 — дёшево)
        do t = 1, n
            order(t) = stt(t)
            idx(t) = t
        end do
        mm = min(m, n)
        do t = 1, mm
            u = t
            do cnt = t + 1, n
                if (order(cnt) .gt. order(u)) u = cnt
            end do
            ! swap t <-> u
            tmp = order(t); order(t) = order(u); order(u) = tmp
            cnt = idx(t); idx(t) = idx(u); idx(u) = cnt
        end do
        call s115c81_writerow(name, mm, &
            packsel(stw, idx, cnt), packsel(sco, idx, cnt), packsel(sdp, idx, cnt), &
            packsel(sla, idx, cnt), packsel(sso, idx, cnt), packsel(sbt, idx, cnt), &
            packsel(sbc, idx, cnt), packsel(sb1, idx, cnt), packsel(stt, idx, cnt), &
            packsel(seq, idx, cnt))
    end subroutine s115c81_subset

    function packsel(a, idx, cnt) result(r)
        real, intent(in) :: a(*)
        integer, intent(in) :: idx(*), cnt
        real :: r(cnt)
        integer :: t
        do t = 1, cnt
            r(t) = a(idx(t))
        end do
    end function packsel

    subroutine s115c81_writerow(name, n, stw, sco, sdp, sla, sso, sbt, sbc, sb1, stt, seq)
        character(len=*), intent(in) :: name
        integer, intent(in) :: n
        real, intent(in) :: stw(n), sco(n), sdp(n), sla(n), sso(n)
        real, intent(in) :: sbt(n), sbc(n), sb1(n), stt(n), seq(n)
        real :: s1, s2, s3, s4, s5, s6, s7, s8, s9, s10
        s1 = sum(stw(1:n)); s2 = sum(sco(1:n)); s3 = sum(sdp(1:n)); s4 = sum(sla(1:n))
        s5 = sum(sso(1:n)); s6 = sum(sbt(1:n)); s7 = sum(sbc(1:n)); s8 = sum(sb1(1:n))
        s9 = sum(stt(1:n)); s10 = sum(seq(1:n))
        write (attr_unit, '(A,",",I6,",",9(E15.7,","),E15.7)') &
            trim(name), n, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10
        flush (attr_unit)
    end subroutine s115c81_writerow

    subroutine s115c81_allpos()
        integer :: i, j, k, ki, cnt
        real :: s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, tot
        cnt = 0
        s1 = 0.0; s2 = 0.0; s3 = 0.0; s4 = 0.0; s5 = 0.0
        s6 = 0.0; s7 = 0.0; s8 = 0.0; s9 = 0.0; s10 = 0.0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    tot = aTW(i, j, k) + aCor(i, j, k) + aDPX(i, j, k) + &
                          aLap(i, j, k) + aSol(i, j, k) + &
                          aBtp(i, j, k) + aBcl(i, j, k) + aB10(i, j, k)
                    if (tot .le. 0.0) cycle
                    cnt = cnt + 1
                    s1 = s1 + aTW(i, j, k); s2 = s2 + aCor(i, j, k)
                    s3 = s3 + aDPX(i, j, k); s4 = s4 + aLap(i, j, k)
                    s5 = s5 + aSol(i, j, k)
                    s6 = s6 + aBtp(i, j, k); s7 = s7 + aBcl(i, j, k)
                    s8 = s8 + aB10(i, j, k); s9 = s9 + tot
                    s10 = s10 + tot + aQ(i, j, k)
                end do
            end do
        end do
        write (attr_unit, '(A,",",I6,",",9(E15.7,","),E15.7)') &
            'all-positive', cnt, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10
        flush (attr_unit)
    end subroutine s115c81_allpos

end module stage115c81_attr
