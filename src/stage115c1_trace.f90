! ==============================================================================
! Модуль: stage115c1_trace
! Назначение: Stage 11.5C.1 — форензик-аудит нестабильности океанского
!             сабстеппинга (N=24 first-invalid trace + frozen-coupling control).
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C1_TRACE=true            — per-substep checkpoint trace
!   STAGE115C1_FREEZE_COUPLING=true  — заморозка txic/tyic/ans на первые
!                                      суточные значения (разрыв ice→ocean
!                                      feedback внутри суток)
!
! Checkpoint-последовательность (вызывается из gated ocean tail в main.f90):
!   START → AFTER_advs → AFTER_advt → AFTER_CA → AFTER_B200 → AFTER_B210 →
!   AFTER_shal → AFTER_B280
! На каждом checkpoint: min/max T2,S2,RO,U2,V2,W + статистика coupling
! (txic/tyic/ans/skz/hices) в CSV; поиск первого NaN/Inf (порядок S1,T1,T2,
! S2,RO,U2,V2,W — как s112); при событии — дамп локального стенсила
! (текущие + предыдущие значения = before/after).
! ==============================================================================
module stage115c1_trace
    use param
    implicit none

    logical, save :: t115c1_trace = .false.
    logical, save :: t115c1_freeze = .false.
    integer, save :: t115c1_substep = 0
    integer, save :: t115c1_prev_iii = -1
    integer, save :: t115c1_event_day = -1
    integer, save :: t115c1_event_sub = -1
    character(len=32), save :: t115c1_event_label = 'none'
    logical, save :: t115c1_event_seen = .false.
    integer, save :: t115c1_unit = 89
    logical, save :: t115c1_open = .false.
    logical, save :: t115c1_prev_alloc = .false.

    ! Freeze-снапшоты coupling (суточные значения первого сабстепа)
    real, save, allocatable :: txic_frz(:, :), tyic_frz(:, :), ans_frz(:, :)

    ! Копии полей предыдущего checkpoint (before-значения при событии)
    real, save, allocatable :: t2p(:, :, :), s2p(:, :, :), rop(:, :, :)
    real, save, allocatable :: u2p(:, :, :), v2p(:, :, :), wp(:, :, :)
    character(len=32), save :: t115c1_prev_label = 'INIT'

contains

    subroutine s115c1_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C1_TRACE', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c1_trace = .true.
        end if
        call get_environment_variable('STAGE115C1_FREEZE_COUPLING', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c1_freeze = .true.
        end if
        if (t115c1_trace .or. t115c1_freeze) then
            print *, 'STAGE115C1: trace=', t115c1_trace, ' freeze_coupling=', t115c1_freeze
        end if
    end subroutine s115c1_init

    logical function t115c1_is_invalid(val)
        real, intent(in) :: val
        t115c1_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c1_is_invalid

    ! Вход в gated ocean tail: счёт сабстепов + freeze snapshot/apply.
    ! Вызывать СРАЗУ после dt-swap, до любых операторов.
    subroutine s115c1_gate_entry(iii)
        integer, intent(in) :: iii
        if (.not. t115c1_trace .and. .not. t115c1_freeze) return
        ! Новый день: iii перезапускается с 1 (для N=1 единственный fire
        ! на iii==mm2; детект через iii <= prev тоже корректен).
        if (iii .le. t115c1_prev_iii) t115c1_substep = 0
        t115c1_prev_iii = iii
        t115c1_substep = t115c1_substep + 1
        if (t115c1_freeze) then
            if (.not. allocated(txic_frz)) then
                allocate (txic_frz(is1, js1), tyic_frz(is1, js1), ans_frz(is1, js1))
            end if
            if (t115c1_substep .eq. 1) then
                ! Снапшот coupling первого сабстепа суток (после iii=1 ice update;
                ! задокументировано как freeze-база; см. отчёт 11.5C.1).
                txic_frz(:, :) = txic(:, :)
                tyic_frz(:, :) = tyic(:, :)
                ans_frz(:, :) = ans(:, :)
            else
                ! Разрыв внутрисуточного ice→ocean feedback: B210 видит
                ! замороженные значения (ice-модель между сабстепами
                ! пересчитывает свободно — трогаем только входы океана).
                txic(:, :) = txic_frz(:, :)
                tyic(:, :) = tyic_frz(:, :)
                ans(:, :) = ans_frz(:, :)
            end if
        end if
    end subroutine s115c1_gate_entry

    subroutine s115c1_open_csv()
        if (t115c1_open) return
        open (unit=t115c1_unit, file='stage115c1_trace.csv', status='replace', action='write')
        write (t115c1_unit, '(A)') 'day,iii,sub,label,Tmin,Tmax,Smin,Smax,' // &
            'ROmin,ROmax,maxU,maxV,maxW,txicmax,tyicmax,ansmax,skzmax,ninvalid,nhices_inv'
        t115c1_open = .true.
    end subroutine s115c1_open_csv

    ! Checkpoint: скан + min/max + CSV + before/after + стенсил при событии.
    subroutine s115c1_checkpoint(day, iii, label)
        integer, intent(in) :: day, iii
        character(len=*), intent(in) :: label
        integer :: i, j, k, ki, ninv
        integer :: ei, ej, ek, evar
        real :: tmin, tmax, smin, smax, romin, romax
        real :: umax, vmax, wmax, txm, tym, ansm, skzm
        integer :: nhice_inv
        real :: v
        character(len=8) :: vname
        character(len=48) :: fulllabel
        logical :: first

        if (.not. t115c1_trace) return
        call s115c1_open_csv()
        if (.not. t115c1_prev_alloc) then
            allocate (t2p(is1, js1, ks1), s2p(is1, js1, ks1), rop(is1, js1, ks1), &
                      u2p(is1, js1, ks1), v2p(is1, js1, ks1), wp(is1, js1, ks1))
            t2p = 0.0; s2p = 0.0; rop = 0.0; u2p = 0.0; v2p = 0.0; wp = 0.0
            t115c1_prev_alloc = .true.
        end if

        ! fulllabel = 'S<nn>_<label>' (substep-префикс для CSV/анализа)
        write (fulllabel, '(A,I2.2,A,A)') 'S', t115c1_substep, '_', trim(label)

        tmin = huge(1.0); tmax = -huge(1.0)
        smin = huge(1.0); smax = -huge(1.0)
        romin = huge(1.0); romax = -huge(1.0)
        umax = 0.0; vmax = 0.0; wmax = 0.0
        ninv = 0; ei = -1; ej = -1; ek = -1; evar = 0; vname = '?'
        first = .true.

        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    ! Порядок как в s112 (S1,T1,T2,S2,RO,U2,V2,W) — первое
                    ! событие совпадёт с официальным FIRST_INVALID.
                    if (t115c1_is_invalid(s1(i, j, k))) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 8; vname = 'S1'; end if
                    end if
                    if (t115c1_is_invalid(t1(i, j, k))) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 9; vname = 'T1'; end if
                    end if
                    v = t2(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 4; vname = 'T2'; end if
                    else
                        tmin = min(tmin, v); tmax = max(tmax, v)
                    end if
                    v = s2(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 5; vname = 'S2'; end if
                    else
                        smin = min(smin, v); smax = max(smax, v)
                    end if
                    v = ro(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 6; vname = 'RO'; end if
                    else
                        romin = min(romin, v); romax = max(romax, v)
                    end if
                    v = u2(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 1; vname = 'U2'; end if
                    else
                        umax = max(umax, abs(v))
                    end if
                    v = v2(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 2; vname = 'V2'; end if
                    else
                        vmax = max(vmax, abs(v))
                    end if
                    v = w(i, j, k)
                    if (t115c1_is_invalid(v)) then
                        ninv = ninv + 1
                        if (first) then; first = .false.; ei = i; ej = j; ek = k; evar = 3; vname = 'W'; end if
                    else
                        wmax = max(wmax, abs(v))
                    end if
                end do
            end do
        end do

        ! Coupling-статистика (T-сетка; land отсекаем по |.|<8887)
        txm = 0.0; tym = 0.0; ansm = -huge(1.0); skzm = 0.0; nhice_inv = 0
        do j = 2, js
            do i = 2, is
                if (kt1(i, j) .eq. 0) cycle
                if (abs(txic(i, j)) .lt. 8887.0) txm = max(txm, abs(txic(i, j)))
                if (abs(tyic(i, j)) .lt. 8887.0) tym = max(tym, abs(tyic(i, j)))
                if (abs(ans(i, j)) .lt. 8887.0 .and. ans(i, j) .lt. 8.0) &
                    ansm = max(ansm, ans(i, j))
                if (abs(skz(i, j)) .lt. 8887.0) skzm = max(skzm, abs(skz(i, j)))
                if (t115c1_is_invalid(hices(i, j))) nhice_inv = nhice_inv + 1
            end do
        end do

        write (t115c1_unit, '(I4,2(",",I3),",",A,",",13(E13.6,","),I8,",",I6)') &
            day, iii, t115c1_substep, trim(fulllabel), &
            tmin, tmax, smin, smax, romin, romax, umax, vmax, wmax, &
            txm, tym, ansm, skzm, ninv, nhice_inv
        flush (t115c1_unit)

        ! Первая фиксация события: before/after + стенсил (один раз за прогон)
        if (ninv .gt. 0 .and. .not. t115c1_event_seen) then
            t115c1_event_seen = .true.
            t115c1_event_day = day
            t115c1_event_sub = t115c1_substep
            t115c1_event_label = fulllabel
            call s115c1_dump_event(day, iii, fulllabel, vname, evar, ei, ej, ek, ninv, &
                                   ansm, skzm)
        end if

        ! Per-substep stdout-сводка на AFTER_B280 (1 строка/сабстеп)
        if (trim(label) .eq. 'AFTER_B280') then
            print '(A,I3,A,I3,A,I3,A,E12.4,A,E12.4,A,E12.4,A,I8)', &
                'STAGE115C1 d=', day, ' iii=', iii, ' sub=', t115c1_substep, &
                ' ROmin=', romin, ' ROmax=', romax, ' maxU=', umax, ' ninv=', ninv
        end if

        ! Сохранить текущее как before для следующего checkpoint
        t2p(:, :, :) = t2(:, :, :)
        s2p(:, :, :) = s2(:, :, :)
        rop(:, :, :) = ro(:, :, :)
        u2p(:, :, :) = u2(:, :, :)
        v2p(:, :, :) = v2(:, :, :)
        wp(:, :, :) = w(:, :, :)
        t115c1_prev_label = fulllabel
    end subroutine s115c1_checkpoint

    subroutine s115c1_dump_event(day, iii, fulllabel, vname, evar, i0, j0, k0, ninv, ansm, skzm)
        integer, intent(in) :: day, iii, evar, i0, j0, k0, ninv
        character(len=*), intent(in) :: fulllabel, vname
        real, intent(in) :: ansm, skzm
        integer :: i, j, k, kk
        real :: cur, bef

        print *, '==============================================================='
        print *, 'STAGE115C1 FIRST TRACE EVENT: day=', day, ' iii=', iii, &
                 ' sub=', t115c1_substep, ' checkpoint=', trim(fulllabel)
        print *, '  first invalid: var=', trim(vname), ' (id=', evar, &
                 ') at i=', i0, ' j=', j0, ' k=', k0, ' ninv_total=', ninv
        print *, '  prev checkpoint: ', trim(t115c1_prev_label)
        print *, '  coupling at (i0,j0): txic=', txic(i0, j0), ' tyic=', tyic(i0, j0), &
                 ' ans=', ans(i0, j0), ' skz=', skz(i0, j0), &
                 ' hices=', hices(i0, j0), ' wices=', wices(i0, j0)
        print *, '  coupling field extrema: ansmax=', ansm, ' skzmax=', skzm
        print *, '  -- stencil AFTER (current) vs BEFORE (prev checkpoint) --'
        do kk = max(1, k0-1), min(ks, k0+1)
            print *, '  k=', kk
            do j = max(2, j0-2), min(js, j0+2)
                do i = max(2, i0-2), min(is, i0+2)
                    select case (evar)
                    case (8); cur = s1(i, j, kk)
                    case (9); cur = t1(i, j, kk)
                    case (4); cur = t2(i, j, kk); bef = t2p(i, j, kk)
                    case (5); cur = s2(i, j, kk); bef = s2p(i, j, kk)
                    case (6); cur = ro(i, j, kk); bef = rop(i, j, kk)
                    case (1); cur = u2(i, j, kk); bef = u2p(i, j, kk)
                    case (2); cur = v2(i, j, kk); bef = v2p(i, j, kk)
                    case (3); cur = w(i, j, kk); bef = wp(i, j, kk)
                    case default; cur = 0.0; bef = 0.0
                    end select
                    if (evar .eq. 8 .or. evar .eq. 9) then
                        print '(A,I4,A,I4,A,E13.6)', '   (', i, ',', j, ') cur=', cur
                    else
                        print '(A,I4,A,I4,A,E13.6,A,E13.6)', '   (', i, ',', j, &
                            ') cur=', cur, ' bef=', bef
                    end if
                end do
            end do
        end do
        ! Операнды: состояние ячейки-события по всем полям (генератор vs жертва)
        print *, '  event-cell operands: T2=', t2(i0, j0, k0), ' S2=', s2(i0, j0, k0), &
                 ' RO=', ro(i0, j0, k0), ' U2=', u2(i0, j0, k0), &
                 ' V2=', v2(i0, j0, k0), ' W=', w(i0, j0, k0)
        print *, '  event-cell before:   T2=', t2p(i0, j0, k0), ' S2=', s2p(i0, j0, k0), &
                 ' RO=', rop(i0, j0, k0), ' U2=', u2p(i0, j0, k0), &
                 ' V2=', v2p(i0, j0, k0), ' W=', wp(i0, j0, k0)
        print *, '==============================================================='
    end subroutine s115c1_dump_event

end module stage115c1_trace
