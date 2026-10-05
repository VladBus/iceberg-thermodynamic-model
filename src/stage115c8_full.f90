! ==============================================================================
! Модуль: stage115c8_full
! Назначение: Stage 11.5C.8 — full-field per-cell dE aggregates:
!             на границах B200/B210/B280 считает dE=2U·dU+2V·dV по ВСЕМ
!             wet-ячейкам и пишет ТОЛЬКО агрегаты (без huge-CSV).
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — только чтение + свои буферы.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C8_FULLFIELD=true
! Вызывать: op_before (snap U2/V2) / op_after (счёт+строка) для
! op ∈ {B200,B210,B280} — 6 вызовов/сабстеп.
! `fullfield_energy_aggregates.csv` (flush/row; +2 колонки ninv/allwet
! сверх спеки — задокументировано; E_k_* — 18 уровней ks=18, не 17 —
! задокументировано: ks=18 per param.f90):
!   day,iii,sub,op,sum_pos,sum_neg,net,npos,nneg,
!   maxpos,i,j,k,maxneg,i,j,k,ninv,nwet,
!   Ek_1..Ek_18   (dE_total ЭТОГО оператора по уровням)
! Сабстеп-счётчик: только на B200_before (первый вызов сабстепа) с
! iii-rollover (урок 11.5C.5 — не считать на каждом вызове).
! Day-1 spatial map: D_E(i,j,k) += dE_total(op,sum) каждого сабстепа
! (аккумулятор day-1); на первом B200_before дня 2 — дамп top-1000
! положительных ячеек (min-heap на 1000, O(n)) →
! `spatial_top1000_d1.csv` (i,j,k,D_E_day1). ВМЕСТО NetCDF из спеки:
! диагностический модуль не тянет netCDF-зависимость; top-1000 +
! depth-профиль покрывают вопрос "где" (задокументированное отклонение).
! NaN/Inf: ячейки с non-finite в before ИЛИ after пропускаются в суммах,
! считаются в ninv (не заражают агрегаты).
! ==============================================================================
module stage115c8_full
    use param
    implicit none

    logical, save :: t115c8_on = .false.
    integer, save :: t115c8_substep = 0
    integer, save :: t115c8_prev_iii = -1
    integer, save :: agg_unit = 178
    integer, save :: map_unit = 179
    logical, save :: agg_open = .false.

    real, save, allocatable :: su(:, :, :), sv(:, :, :)
    logical, save :: snap_ok = .false.

    ! Day-1 spatial accumulator (dE_total per op summed) + dump flag
    real, save, allocatable :: dacc(:, :, :)
    logical, save :: dacc_alloc = .false.
    logical, save :: map_dumped = .false.
    integer, parameter :: TOPN = 1000

contains

    subroutine s115c8_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C8_FULLFIELD', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c8_on = .true.
            print *, 'STAGE115C8: fullfield= T'
        end if
    end subroutine s115c8_init

    logical function t115c8_is_invalid(val)
        real, intent(in) :: val
        t115c8_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c8_is_invalid

    subroutine s115c8_open()
        if (agg_open) return
        open (unit=agg_unit, file='fullfield_energy_aggregates.csv', status='replace', action='write')
        write (agg_unit, '(A)') 'day,iii,sub,op,sum_pos,sum_neg,net,npos,nneg,' // &
            'maxpos,i,j,k,maxneg,i,j,k,ninv,nwet,' // &
            'Ek_1,Ek_2,Ek_3,Ek_4,Ek_5,Ek_6,Ek_7,Ek_8,Ek_9,Ek_10,' // &
            'Ek_11,Ek_12,Ek_13,Ek_14,Ek_15,Ek_16,Ek_17,Ek_18'
        agg_open = .true.
    end subroutine s115c8_open

    subroutine s115c8_alloc()
        if (allocated(su)) return
        allocate (su(is1, js1, ks1), sv(is1, js1, ks1))
        su = 0.0; sv = 0.0
    end subroutine s115c8_alloc

    ! phase=0: snap (+rollover/счётчик только для B200); phase=1: счёт+строка.
    subroutine s115c8_op(day, iii, op, phase)
        integer, intent(in) :: day, iii, phase
        character(len=*), intent(in) :: op
        if (.not. t115c8_on) return
        call s115c8_open()
        call s115c8_alloc()
        if (phase .eq. 0) then
            if (op .eq. 'B200') then
                if (iii .le. t115c8_prev_iii) then
                    ! Новый день: дамп top-1000 за day-1 ОДИН раз (на входе в день 2)
                    if (day .eq. 2 .and. .not. map_dumped) call s115c8_dump_map(day)
                    t115c8_substep = 0
                end if
                t115c8_prev_iii = iii
                t115c8_substep = t115c8_substep + 1
            end if
            su(:, :, :) = u2(:, :, :)
            sv(:, :, :) = v2(:, :, :)
            snap_ok = .true.
        else
            if (.not. snap_ok) return
            call s115c8_compute(day, iii, op)
        end if
    end subroutine s115c8_op

    subroutine s115c8_compute(day, iii, op)
        integer, intent(in) :: day, iii
        character(len=*), intent(in) :: op
        integer :: i, j, k, ki, ninv, nwet, npos, nneg
        integer :: pi, pj, pk, qi, qj, qk
        real :: ub, vb, ua, va, du, dv, dE, Ek(ks)
        real :: spos, sneg, mp, mn
        nwet = 0; ninv = 0; npos = 0; nneg = 0
        spos = 0.0; sneg = 0.0
        mp = -huge(1.0); mn = huge(1.0)
        pi = -1; pj = -1; pk = -1; qi = -1; qj = -1; qk = -1
        Ek(:) = 0.0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    nwet = nwet + 1
                    ub = su(i, j, k); vb = sv(i, j, k)
                    ua = u2(i, j, k); va = v2(i, j, k)
                    if (t115c8_is_invalid(ub) .or. t115c8_is_invalid(vb) .or. &
                        t115c8_is_invalid(ua) .or. t115c8_is_invalid(va)) then
                        ninv = ninv + 1
                        cycle
                    end if
                    du = ua - ub; dv = va - vb
                    ! EXACT dE (11.5C.8R fix): first-order 2U·dU misses the
                    ! +dU² spin-up fill (dominant from rest) → net was
                    ! first-order-biased negative. Exact: Δ(U²+V²).
                    dE = (ua*ua + va*va) - (ub*ub + vb*vb)
                    Ek(k) = Ek(k) + dE
                    if (dE .gt. 0.0) then
                        spos = spos + dE; npos = npos + 1
                        if (dE .gt. mp) then
                            mp = dE; pi = i; pj = j; pk = k
                        end if
                    else if (dE .lt. 0.0) then
                        sneg = sneg + dE; nneg = nneg + 1
                        if (dE .lt. mn) then
                            mn = dE; qi = i; qj = j; qk = k
                        end if
                    end if
                    ! Day-1 spatial accumulation (dE_total per op summed;
                    ! отдельный аккумулятор — см. s115c8_dump_map)
                    if (day .eq. 1 .and. .not. map_dumped) then
                        if (.not. dacc_alloc) then
                            allocate (dacc(is1, js1, ks1))
                            dacc(:, :, :) = 0.0
                            dacc_alloc = .true.
                        end if
                        dacc(i, j, k) = dacc(i, j, k) + dE
                    end if
                end do
            end do
        end do
        if (mp .eq. -huge(1.0)) mp = 0.0
        if (mn .eq. huge(1.0)) mn = 0.0
        write (agg_unit, '(I4,2(",",I3),",",A,",",3(E15.7,","),2(I8,","),E15.7,",",3(I4,","),E15.7,",",3(I4,","),2(I8,","),17(E15.7,","),E15.7)') &
            day, iii, t115c8_substep, trim(op), spos, sneg, spos + sneg, &
            npos, nneg, mp, pi, pj, pk, mn, qi, qj, qk, ninv, nwet, &
            (Ek(k), k=1, ks-1), Ek(ks)
        flush (agg_unit)
    end subroutine s115c8_compute

    subroutine s115c8_dump_map(day)
        integer, intent(in) :: day
        integer :: i, j, k, ki, t, pos, cnt
        real :: hv(TOPN), v
        integer :: hi(TOPN), hj(TOPN), hk(TOPN)
        ! day — уже день 2 (триггер); дампим накопленное за day-1.
        if (map_dumped) return
        map_dumped = .true.
        if (.not. dacc_alloc) return
        open (unit=map_unit, file='spatial_top1000_d1.csv', status='replace', action='write')
        write (map_unit, '(A)') 'i,j,k,D_E_day1'
        hv(:) = -huge(1.0)
        hi(:) = -1
        cnt = 0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    v = dacc(i, j, k)
                    if (v .le. 0.0) cycle
                    cnt = cnt + 1
                    ! min-heap вставка (линейный поиск минимума — TOPN=1000 дёшево)
                    pos = 1
                    do t = 2, TOPN
                        if (hv(t) .lt. hv(pos)) pos = t
                    end do
                    if (v .gt. hv(pos)) then
                        hv(pos) = v; hi(pos) = i; hj(pos) = j; hk(pos) = k
                    end if
                end do
            end do
        end do
        do t = 1, TOPN
            if (hi(t) .lt. 0) cycle
            write (map_unit, '(3(I4,","),E15.7)') hi(t), hj(t), hk(t), hv(t)
        end do
        flush (map_unit)
        close (map_unit)
        print *, 'STAGE115C8: spatial top-1000 day-1 dumped, positive cells scanned =', cnt
    end subroutine s115c8_dump_map

end module stage115c8_full
