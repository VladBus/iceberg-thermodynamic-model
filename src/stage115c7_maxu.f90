! ==============================================================================
! Модуль: stage115c7_maxu
! Назначение: Stage 11.5C.7 — top-K max-|U| spatial tracking на границах
!             операторов (B200/B210/B280) + seed-контроль.
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — только чтение.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C7_MAXU_TRACK=true
! На каждом вызове: скан всего wet-домена (kt1), top-10 по |U2|
! (U2/V2, все k) + принудительно seed (112,17,9),(112,18,9) →
! `maxu_cells_tracking.csv` (flush/row, kill-safe):
!   day,iii,sub,op,phase,i,j,k,U,V,Uabs
! op ∈ {B200,B210,B280}, phase ∈ {0=before,1=after}.
! Вызывать: B200_before, B200_after (=B210_before), B210_after,
! B280_before, B280_after. dU/dE per operator — офлайн-join по (i,j,k)
! consecutive-фаз (кандидатные множества пересекаются через top-12+seeds;
! seeds гарантированы всегда). sub: честный счётчик gate-entry (модуль
! считает сам по iii-rollover — вызывается 5×/сабстеп, поэтому счётчик
! тикает только на phase==0&&op==B200 (первый вызов сабстепа);
! задокументировано).
! Term-декопозиция top-ячеек: НЕ здесь — через STAGE115C6_CELLS override
! (см. stage115c6_terms.f90) вторым прогоном. Разделение сознательное:
! top-множество неизвестно до прогона-трекера.
! ==============================================================================
module stage115c7_maxu
    use param
    implicit none

    logical, save :: t115c7_on = .false.
    integer, save :: t115c7_substep = 0
    integer, save :: t115c7_prev_iii = -1
    integer, save :: trk_unit = 177
    logical, save :: trk_open = .false.

    integer, parameter :: TK = 10

contains

    subroutine s115c7_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C7_MAXU_TRACK', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c7_on = .true.
            print *, 'STAGE115C7: maxu_track= T'
        end if
    end subroutine s115c7_init

    logical function t115c7_is_invalid(val)
        real, intent(in) :: val
        t115c7_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c7_is_invalid

    subroutine s115c7_open()
        if (trk_open) return
        open (unit=trk_unit, file='maxu_cells_tracking.csv', status='replace', action='write')
        write (trk_unit, '(A)') 'day,iii,sub,op,phase,i,j,k,U,V,Uabs'
        trk_open = .true.
    end subroutine s115c7_open

    ! op: 'B200'/'B210'/'B280'; phase: 0=before, 1=after.
    subroutine s115c7_track(day, iii, op, phase)
        integer, intent(in) :: day, iii, phase
        character(len=*), intent(in) :: op
        integer :: i, j, k, ki, m, t
        real :: a, best(TK)
        integer :: bi(TK), bj(TK), bk(TK)
        logical :: dup
        if (.not. t115c7_on) return
        call s115c7_open()
        ! Счётчик сабстепов: только первый вызов сабстепа (B200,before).
        if (phase .eq. 0 .and. op .eq. 'B200') then
            if (iii .le. t115c7_prev_iii) t115c7_substep = 0
            t115c7_prev_iii = iii
            t115c7_substep = t115c7_substep + 1
        end if
        best(:) = -1.0
        bi(:) = -1
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    if (t115c7_is_invalid(u2(i, j, k)) .or. t115c7_is_invalid(v2(i, j, k))) cycle
                    a = sqrt(u2(i, j, k)*u2(i, j, k) + v2(i, j, k)*v2(i, j, k))
                    ! Вставка в top-K (минимум вытесняется)
                    m = 1
                    do t = 2, TK
                        if (best(t) .lt. best(m)) m = t
                    end do
                    if (a .gt. best(m)) then
                        best(m) = a; bi(m) = i; bj(m) = j; bk(m) = k
                    end if
                end do
            end do
        end do
        do m = 1, TK
            if (bi(m) .lt. 0) cycle
            ! Дедup: одна строка на ячейку (top-K может содержать дубли? нет —
            ! каждая (i,j,k) уникальна в скане; seeds ниже проверяем отдельно).
            write (trk_unit, '(I4,2(",",I3),",",A,",",I1,3(",",I4),",",2(E15.7,","),E15.7)') &
                day, iii, t115c7_substep, trim(op), phase, &
                bi(m), bj(m), bk(m), &
                u2(bi(m), bj(m), bk(m)), v2(bi(m), bj(m), bk(m)), best(m)
        end do
        ! Seeds принудительно (гарантия continuity + dedup через bj/bk):
        call s115c7_seedrow(day, iii, op, phase, 112, 17, 9, bi, bj, bk)
        call s115c7_seedrow(day, iii, op, phase, 112, 18, 9, bi, bj, bk)
        flush (trk_unit)
    end subroutine s115c7_track

    subroutine s115c7_seedrow(day, iii, op, phase, i0, j0, k0, bi, bj, bk)
        integer, intent(in) :: day, iii, phase, i0, j0, k0
        integer, intent(in) :: bi(TK), bj(TK), bk(TK)
        character(len=*), intent(in) :: op
        integer :: t
        real :: a
        ! Пропустить если ячейка уже в top-K (избегаем дублей строк)
        do t = 1, TK
            if (bi(t) .eq. i0 .and. bj(t) .eq. j0 .and. bk(t) .eq. k0) return
        end do
        if (t115c7_is_invalid(u2(i0, j0, k0)) .or. t115c7_is_invalid(v2(i0, j0, k0))) return
        a = sqrt(u2(i0, j0, k0)*u2(i0, j0, k0) + v2(i0, j0, k0)*v2(i0, j0, k0))
        write (trk_unit, '(I4,2(",",I3),",",A,",",I1,3(",",I4),",",2(E15.7,","),E15.7)') &
            day, iii, t115c7_substep, trim(op), phase, i0, j0, k0, &
            u2(i0, j0, k0), v2(i0, j0, k0), a
    end subroutine s115c7_seedrow

end module stage115c7_maxu
