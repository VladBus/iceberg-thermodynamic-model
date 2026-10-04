! ==============================================================================
! Модуль: stage115c6_terms
! Назначение: Stage 11.5C.6 — term-level декомпозиция B200/B280
!             (thermal-wind vs pressure-gradient vs Coriolis vs Laplacian
!             vs ice) для seed-ячеек + quiet-контроля, N=1 vs N=24.
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — физику не меняет, формулы НЕ
!             переписывает: recompute-зеркала ИДЕНТИЧНЫ коду main.f90
!             (B200: main:1134-1191, B280: main:1434-1463), только чтение.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C6_B200_TERMS=true — до/после B200: снапшот входов
!       (u1/v1 stencil, RO-столбец, dpx/dpy, fku), recompute sum/sum1
!       ТОЙ ЖЕ рекуррентой (c8·dz, s22_freeze_tw через use-association),
!       слапласианы, auu/avv по бакетам; сверка residual≈0.
!   STAGE115C6_B280_TERMS=true — до/после B280: снапшот u2-столбца + up2,
!       recompute sum/sum1 ТОЙ ЖЕ логикой dzz (включая нижний уровень).
! Бакеты B200 (числитель/asa; solve-довесок отдельно):
!   TW:  dt·(−c1·sum + asa1·(−c1·sum1))/asa  [и V-аналог с −asa1·Fu]
!   DPX/DPY: dt·(−dpx + asa1·(−dpy))/asa
!   Cor: [asa1·vij + asa1·(vij−asa1·uij)]/asa  [V: (−asa1·uij −asa1²·vij)/asa]
!   Lap: dt·(c3·slapu + asa1·c3·slapv)/asa
!   ice: ≡ 0.0 (в B200 НЕТ ice-членов — ice приходит только через u1/RO
!        между проходами; задокументировано как finding, не допущение)
!   solve: uij/asa − uij (неявный довесок 2×2) [V: (vij−asa1·uij)/asa − vij]
!   other=residual: total − Σбакетов (≈1e-15 при точном зеркале).
! Бакеты B280 (поправка sum ОДИНАКОВА для всех k):
!   barotropic: +0.5·(UP2+UP2_nbr)/hht; baroclinic: −∫U2·dzz/hht;
!   projection ≡ 0.0 (у B280 ровно два слагаемых — projection тождественно
!   ноль BY CONSTRUCTION, задокументировано); other=residual.
! Ячейки: (112,17,9), (112,18,9), quiet (50,50,9) — пишется вслепую
! (суша/дно → flag=2/1, см. ниже).
! CSV: b200_terms_112_17_9.csv, _112_18_9.csv, _quiet.csv,
!      b280_terms_112_17_9.csv, _112_18_9.csv, _quiet.csv.
! Колонки B200 (спеке + flag в конце — задокументировано):
!   day,iii,sub,U_before,V_before,
!   dU_TW,dU_DPX,dU_Cor,dU_Lap,dU_ice,dU_other,
!   dV_TW,dV_DPY,dV_Cor,dV_Lap,dV_ice,dV_other,
!   U_after,V_after,dU_total,dV_total,resU,resV,flag
! Колонки B280 (аналогично): ...,dU_btp,dU_bcl,dU_prj,dU_other,
!   dV_btp,dV_bcl,dV_prj,dV_other,...,flag.
! flag: 0=ok, 1=bottomed (B200 дно: u2=v2=0, бакеты посчитаны но отброшены
! кодом — residual это покажет), 2=land/сухая (ki=0 или hht=8888).
! subuiden: sub = iii (для N24 ostep=1 → iii ЕСТЬ сабстеп; N1: один fire
! на iii=24). Литералы: C1=981.0 (g/roc), C3=7.5e6/1389000² (ah/dx²),
! C8=0.25/1389000 (c8), DT_USED=3600.0 (dt в B200: N1 dt=DT=3600,
! N24 dt_ocean=3600 — верно IFF DT=3600/MM2=24, что выполнено в матрице
! 11.5C.x и проверяется по принту STAGE115C; задокументировано).
! ==============================================================================
module stage115c6_terms
    use param
    use stage1022_diagnostics, only: s22_freeze_tw
    implicit none

    real, parameter :: T115C6_DX = 1389000.0
    real, parameter :: T115C6_C1 = 981.0
    real, parameter :: T115C6_C3 = 7.5e6/(1389000.0*1389000.0)
    real, parameter :: T115C6_C8 = 0.25/1389000.0
    real, parameter :: T115C6_DT = 3600.0

    logical, save :: t115c6_b200 = .false.
    logical, save :: t115c6_b280 = .false.
    ! Unit-номера 171–176: верхняя область, коллизий нет (заняты 1,3,17,
    ! 77,81,82,86,87,89–99; 11.5C.6R: было 81–86 → коллизия с s112/CA,
    ! чужеродные строки в CSV; исправлено).
    integer, save :: u200_1 = 171, u200_2 = 172, u200_3 = 173
    integer, save :: u280_1 = 174, u280_2 = 175, u280_3 = 176
    logical, save :: f200_open = .false., f280_open = .false.

    ! B200 before-снапшот (3 ячейки: 2 seed + quiet)
    real, save :: b_uij(3), b_vij(3), b_slapu(3), b_slapv(3)
    real, save :: b_sum(3), b_sum1(3), b_asa1(3), b_asa(3)
    real, save :: b_dpx(3), b_dpy(3)
    integer, save :: b_day = -1, b_iii = -1, b_flag(3)
    logical, save :: b_armed = .false.
    ! B280 before-снапшот
    real, save :: s_u2(3), s_v2(3), s_btp_u(3), s_btp_v(3), s_bcl_u(3), s_bcl_v(3)
    real, save :: s_hht(3)
    integer, save :: s_day = -1, s_iii = -1, s_flag(3)
    logical, save :: s_armed = .false.

    ! Stage 11.5C.7: override трёх слотов через env STAGE115C6_CELLS =
    ! "i,j,k;i,j,k;i,j,k" (ровно 3 тройки, иначе default). Имена файлов НЕ
    ! меняются (b200_terms_112_17_9.csv и т.д. — слот 1/2/3 ↔ override
    ! ячейка 1/2/3; соответствие фиксируется в отчёте прогона).
    ! Диагностический, default OFF-поведение (без env) — как раньше.
    integer, save :: ov_i(3) = (/-1, -1, -1/), ov_j(3) = (/-1, -1, -1/), ov_k(3) = (/-1, -1, -1/)
    logical, save :: ov_on = .false.
    integer, parameter :: Q_I = 50, Q_J = 50, Q_K = 9

contains

    subroutine s115c6_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C6_B200_TERMS', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c6_b200 = .true.
        end if
        call get_environment_variable('STAGE115C6_B280_TERMS', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c6_b280 = .true.
        end if
        if (t115c6_b200 .or. t115c6_b280) then
            print *, 'STAGE115C6: b200_terms=', t115c6_b200, ' b280_terms=', t115c6_b280
        end if
        call s115c6_parse_cells()
    end subroutine s115c6_init

    ! Парсинг STAGE115C6_CELLS = "i,j,k;i,j,k;i,j,k" (ровно 3 тройки).
    ! Невалидно/отсутствует → default (ov_on=.false.).
    subroutine s115c6_parse_cells()
        character(len=128) :: cs
        integer :: p1, p2, ios, a, b, c
        call get_environment_variable('STAGE115C6_CELLS', cs)
        if (len_trim(cs) .eq. 0) return
        p1 = index(cs, ';')
        if (p1 .le. 1) return
        p2 = index(cs(p1+1:), ';')
        if (p2 .le. 1) return
        p2 = p1 + p2
        read (cs(1:p1-1), *, iostat=ios) a, b, c
        if (ios .ne. 0) return
        ov_i(1) = a; ov_j(1) = b; ov_k(1) = c
        read (cs(p1+1:p2-1), *, iostat=ios) a, b, c
        if (ios .ne. 0) return
        ov_i(2) = a; ov_j(2) = b; ov_k(2) = c
        read (cs(p2+1:), *, iostat=ios) a, b, c
        if (ios .ne. 0) return
        ov_i(3) = a; ov_j(3) = b; ov_k(3) = c
        ov_on = .true.
        print *, 'STAGE115C6: cell override ON:', ov_i(1), ov_j(1), ov_k(1), '|', &
                 ov_i(2), ov_j(2), ov_k(2), '|', ov_i(3), ov_j(3), ov_k(3)
    end subroutine s115c6_parse_cells

    subroutine s115c6_cell_ij(n, i0, j0, k0)
        integer, intent(in) :: n
        integer, intent(out) :: i0, j0, k0
        if (ov_on .and. n .ge. 1 .and. n .le. 3) then
            i0 = ov_i(n); j0 = ov_j(n); k0 = ov_k(n)
            return
        end if
        if (n .eq. 1) then
            i0 = 112; j0 = 17; k0 = 9
        else if (n .eq. 2) then
            i0 = 112; j0 = 18; k0 = 9
        else
            i0 = Q_I; j0 = Q_J; k0 = Q_K
        end if
    end subroutine s115c6_cell_ij

    subroutine s115c6_open200()
        if (f200_open) return
        open (unit=u200_1, file='b200_terms_112_17_9.csv', status='replace', action='write')
        open (unit=u200_2, file='b200_terms_112_18_9.csv', status='replace', action='write')
        open (unit=u200_3, file='b200_terms_quiet.csv', status='replace', action='write')
        write (u200_1, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_TW,dU_DPX,dU_Cor,dU_Lap,dU_ice,dU_other,' // &
            'dV_TW,dV_DPY,dV_Cor,dV_Lap,dV_ice,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
        write (u200_2, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_TW,dU_DPX,dU_Cor,dU_Lap,dU_ice,dU_other,' // &
            'dV_TW,dV_DPY,dV_Cor,dV_Lap,dV_ice,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
        write (u200_3, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_TW,dU_DPX,dU_Cor,dU_Lap,dU_ice,dU_other,' // &
            'dV_TW,dV_DPY,dV_Cor,dV_Lap,dV_ice,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
        f200_open = .true.
    end subroutine s115c6_open200

    subroutine s115c6_open280()
        if (f280_open) return
        open (unit=u280_1, file='b280_terms_112_17_9.csv', status='replace', action='write')
        open (unit=u280_2, file='b280_terms_112_18_9.csv', status='replace', action='write')
        open (unit=u280_3, file='b280_terms_quiet.csv', status='replace', action='write')
        write (u280_1, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_btp,dU_bcl,dU_prj,dU_other,dV_btp,dV_bcl,dV_prj,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
            write (u280_2, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_btp,dU_bcl,dU_prj,dU_other,dV_btp,dV_bcl,dV_prj,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
        write (u280_3, '(A)') 'day,iii,sub,U_before,V_before,' // &
            'dU_btp,dU_bcl,dU_prj,dU_other,dV_btp,dV_bcl,dV_prj,dV_other,' // &
            'U_after,V_after,dU_total,dV_total,resU,resV,flag'
        f280_open = .true.
    end subroutine s115c6_open280

    ! B200 before: снапшот входов + recompute sum/sum1/slap той же логикой.
    subroutine s115c6_b200_before(day, iii)
        integer, intent(in) :: day, iii
        integer :: n, i0, j0, k0, i1, i2, j1, j2, k, k1, ki
        real :: hht, a, b, a1, b1, dzz, dzz1, cc, s, s1, uij, vij
        real :: ri2j, rij, ri2j2, rij2
        if (.not. t115c6_b200) return
        call s115c6_open200()
        do n = 1, 3
            call s115c6_cell_ij(n, i0, j0, k0)
            b_flag(n) = 0
            i1 = i0 + 1; i2 = i0 - 1; j1 = j0 + 1; j2 = j0 - 1
            ki = kk1(i0, j0)
            hht = map1(i0, j0)
            if (ki .eq. 0 .or. abs(hht - 8888.0) .lt. 1e-8 .or. k0 .gt. ki .or. k0 .lt. 1) then
                b_flag(n) = 2
                b_uij(n) = 0.0; b_vij(n) = 0.0; b_slapu(n) = 0.0; b_slapv(n) = 0.0
                b_sum(n) = 0.0; b_sum1(n) = 0.0
                b_asa1(n) = 0.0; b_asa(n) = 1.0; b_dpx(n) = 0.0; b_dpy(n) = 0.0
                cycle
            end if
            if (abs(hht - z(k0)) .lt. 1e-6) b_flag(n) = 1
            uij = u1(i0, j0, k0); vij = v1(i0, j0, k0)
            b_uij(n) = uij; b_vij(n) = vij
            b_slapu(n) = u1(i0, j2, k0) + u1(i0, j1, k0) + u1(i2, j0, k0) + u1(i1, j0, k0) - 4.0*uij
            b_slapv(n) = v1(i1, j0, k0) + v1(i2, j0, k0) + v1(i0, j1, k0) + v1(i0, j2, k0) - 4.0*vij
            ! sum/sum1 рекуррентой main:1134-1178 (уровень 0 + k=1..k0)
            ri2j = ro(i2, j0, 1); rij = ro(i0, j0, 1)
            ri2j2 = ro(i2, j2, 1); rij2 = ro(i0, j2, 1)
            a = ri2j + rij - ri2j2 - rij2
            b = ri2j2 + ri2j - rij2 - rij
            dzz = dz(1)
            s = 0.0; s1 = 0.0
            do k = 1, k0
                k1 = k + 1
                dzz1 = dz(k1)
                ri2j = ro(i2, j0, k); rij2 = ro(i0, j2, k)
                rij = ro(i0, j0, k); ri2j2 = ro(i2, j2, k)
                a1 = ri2j + rij - ri2j2 - rij2
                b1 = ri2j2 + ri2j - rij2 - rij
                cc = T115C6_C8*dzz
                s = s + (a + a1)*cc
                s1 = s1 + (b + b1)*cc
                if (s22_freeze_tw) then
                    s = 0.0
                    s1 = 0.0
                end if
                a = a1
                b = b1
                dzz = dzz1
            end do
            b_sum(n) = s; b_sum1(n) = s1
            b_asa1(n) = fku(i0, j0)*0.5*T115C6_DT
            b_asa(n) = 1.0 + b_asa1(n)*b_asa1(n)
            b_dpx(n) = dpx(i0, j0); b_dpy(n) = dpy(i0, j0)
        end do
        b_day = day; b_iii = iii
        b_armed = .true.
    end subroutine s115c6_b200_before

    ! B200 after: бакеты из снапшота + сверка с фактом.
    subroutine s115c6_b200_after(day, iii)
        integer, intent(in) :: day, iii
        integer :: n, i0, j0, k0, unt
        real :: asa1, asa, uij, vij, sm, sm1, dp, dp1, sl, sl1
        real :: fu_tw, fu_pg, fu_lp, fv_tw, fv_pg, fv_lp
        real :: du_tw, du_pg, du_co, du_lp, du_sv
        real :: dv_tw, dv_pg, dv_co, dv_lp, dv_sv
        real :: ua, va, dtu, dtv, rsu, rsv
        if (.not. t115c6_b200) return
        if (.not. b_armed) return
        b_armed = .false.
        do n = 1, 3
            call s115c6_cell_ij(n, i0, j0, k0)
            if (n .eq. 1) unt = u200_1
            if (n .eq. 2) unt = u200_2
            if (n .eq. 3) unt = u200_3
            asa1 = b_asa1(n); asa = b_asa(n)
            uij = b_uij(n); vij = b_vij(n)
            sm = b_sum(n); sm1 = b_sum1(n)
            dp = b_dpx(n); dp1 = b_dpy(n)
            sl = b_slapu(n); sl1 = b_slapv(n)
            ! Бакеты числителя (auu = uij + asa1·vij + dt·F; avv = vij − asa1·uij + dt·F)
            fu_tw = -T115C6_C1*sm; fu_pg = -dp; fu_lp = T115C6_C3*sl
            fv_tw = -T115C6_C1*sm1; fv_pg = -dp1; fv_lp = T115C6_C3*sl1
            du_tw = T115C6_DT*(fu_tw + asa1*fv_tw)/asa
            du_pg = T115C6_DT*(fu_pg + asa1*fv_pg)/asa
            du_lp = T115C6_DT*(fu_lp + asa1*fv_lp)/asa
            du_co = (asa1*vij + asa1*(vij - asa1*uij))/asa
            du_sv = uij/asa - uij
            dv_tw = T115C6_DT*(fv_tw - asa1*fu_tw)/asa
            dv_pg = T115C6_DT*(fv_pg - asa1*fu_pg)/asa
            dv_lp = T115C6_DT*(fv_lp - asa1*fu_lp)/asa
            dv_co = (-asa1*uij - asa1*asa1*vij)/asa
            dv_sv = (vij - asa1*uij)/asa - vij
            ua = u2(i0, j0, k0); va = v2(i0, j0, k0)
            dtu = ua - uij; dtv = va - vij
            rsu = dtu - (du_tw + du_pg + du_co + du_lp + du_sv)
            rsv = dtv - (dv_tw + dv_pg + dv_co + dv_lp + dv_sv)
            write (unt, '(I4,2(",",I3),",",19(E15.7,","),E15.7,",",I2)') &
                b_day, b_iii, b_iii, uij, vij, &
                du_tw, du_pg, du_co, du_lp, 0.0, du_sv, &
                dv_tw, dv_pg, dv_co, dv_lp, 0.0, dv_sv, &
                ua, va, dtu, dtv, rsu, rsv, b_flag(n)
            flush (unt)
        end do
    end subroutine s115c6_b200_after

    ! B280 before: снапшот u2-столбца + up2.
    subroutine s115c6_b280_before(day, iii)
        integer, intent(in) :: day, iii
        integer :: n, i0, j0, k0, i2, j2, k, k1, ki
        real :: hht, dzz, s, s1
        if (.not. t115c6_b280) return
        call s115c6_open280()
        do n = 1, 3
            call s115c6_cell_ij(n, i0, j0, k0)
            s_flag(n) = 0
            i2 = i0 - 1; j2 = j0 - 1
            ki = kk1(i0, j0)
            hht = map1(i0, j0)
            s_hht(n) = hht
            if (ki .eq. 0 .or. abs(hht - 8888.0) .lt. 1e-8 .or. k0 .gt. ki .or. k0 .lt. 1) then
                s_flag(n) = 2
                s_u2(n) = 0.0; s_v2(n) = 0.0
                s_btp_u(n) = 0.0; s_btp_v(n) = 0.0
                s_bcl_u(n) = 0.0; s_bcl_v(n) = 0.0
                cycle
            end if
            s_u2(n) = u2(i0, j0, k0); s_v2(n) = v2(i0, j0, k0)
            ! recompute ТОЙ ЖЕ логикой main:1437-1457
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
                s = u2(i0, j0, k)*dzz + s
                s1 = v2(i0, j0, k)*dzz + s1
            end do
            s_btp_u(n) = 0.5*(up2(i0, j0) + up2(i2, j0))/hht
            s_btp_v(n) = 0.5*(vp2(i0, j0) + vp2(i0, j2))/hht
            s_bcl_u(n) = -s/hht
            s_bcl_v(n) = -s1/hht
        end do
        s_day = day; s_iii = iii
        s_armed = .true.
    end subroutine s115c6_b280_before

    ! B280 after: сверка с фактом.
    subroutine s115c6_b280_after(day, iii)
        integer, intent(in) :: day, iii
        integer :: n, i0, j0, k0, unt
        real :: ua, va, dtu, dtv, rsu, rsv
        if (.not. t115c6_b280) return
        if (.not. s_armed) return
        s_armed = .false.
        do n = 1, 3
            call s115c6_cell_ij(n, i0, j0, k0)
            if (n .eq. 1) unt = u280_1
            if (n .eq. 2) unt = u280_2
            if (n .eq. 3) unt = u280_3
            ua = u2(i0, j0, k0); va = v2(i0, j0, k0)
            dtu = ua - s_u2(n); dtv = va - s_v2(n)
            rsu = dtu - (s_btp_u(n) + s_bcl_u(n) + 0.0)
            rsv = dtv - (s_btp_v(n) + s_bcl_v(n) + 0.0)
            write (unt, '(I4,2(",",I3),",",2(E15.7,","),4(E15.7,","),4(E15.7,","),5(E15.7,","),E15.7,",",I2)') &
                s_day, s_iii, s_iii, s_u2(n), s_v2(n), &
                s_btp_u(n), s_bcl_u(n), 0.0, 0.0, &
                s_btp_v(n), s_bcl_v(n), 0.0, 0.0, &
                ua, va, dtu, dtv, rsu, rsv, s_flag(n)
            flush (unt)
        end do
    end subroutine s115c6_b280_after

end module stage115c6_terms
