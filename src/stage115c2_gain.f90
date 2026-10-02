! ==============================================================================
! Модуль: stage115c2_gain
! Назначение: Stage 11.5C.2 — форензик связей океанского сабстеппинга:
!             heat-freeze контроль + per-cell operator gain audit.
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C2_FREEZE_HEAT=true    — заморозка термо/ледового состояния на
!       первые суточные значения (t1,s1,hice,hsnow,an1,ans,wices,hices,u,v):
!       снапшот на первом gate-fire суток, restore на каждом gate entry —
!       океан всегда видит day-start thermo/ice state (разрыв
!       heat/ice-evolution пути; heat/redis/dynamics между сабстепами
!       пересчитывают свободно — трогаем только входы океана).
!       txic/tyic НЕ трогаем (это exp B из 11.5C.1, не C).
!   STAGE115C2_OPERATOR_GAIN=true   — per-cell gain audit seed-ячеек
!       (112,17,9) [первое non-finite N=24] и (112,18,9) [freeze-событие]
!       + глобальная энергия E=Σ(U²+V²) до/после B200, B210, shal, B280.
!       CSV: operator_gain_112_17_9.csv (колонка cell различает ячейки —
!       единственное отклонение от спеки, задокументировано),
!       energy_checkpoint.csv (+ ninv_before/ninv_after — нужно для
!       zombie-фазы, задокументировано).
! gain = |V_after|/|V_before| ячейки; знаменатель < 1e-6 → 0;
! non-finite в паре → -1 (сентинел).
! ==============================================================================
module stage115c2_gain
    use param
    implicit none

    logical, save :: t115c2_freeze_heat = .false.
    logical, save :: t115c2_gain = .false.
    integer, save :: t115c2_substep = 0
    integer, save :: t115c2_prev_iii = -1
    integer, save :: gain_unit = 90
    integer, save :: energy_unit = 91
    logical, save :: files_open = .false.

    ! Freeze-снапшоты thermo/ice состояния (первые суточные значения)
    real, save, allocatable :: f_t1(:, :, :), f_s1(:, :, :)
    real, save, allocatable :: f_hice(:, :, :), f_hsnow(:, :, :)
    real, save, allocatable :: f_an1(:, :, :)
    real, save, allocatable :: f_ans(:, :), f_wices(:, :), f_hices(:, :)
    real, save, allocatable :: f_u(:, :), f_v(:, :)

    ! Before-состояние оператора (ячейки + энергия)
    real, save :: b_u1, b_v1, b_u2, b_v2, b_E
    integer, save :: b_ninv
    character(len=16), save :: b_op = 'none'
    integer, save :: b_day = -1, b_iii = -1, b_sub = -1
    logical, save :: b_armed = .false.

    ! Seed-ячейки: 11.5C.1 события (N24: 112,17,9; freeze: 112,18,9)
    integer, parameter :: C1_I = 112, C1_J = 17, C1_K = 9
    integer, parameter :: C2_I = 112, C2_J = 18, C2_K = 9

contains

    subroutine s115c2_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C2_FREEZE_HEAT', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c2_freeze_heat = .true.
        end if
        call get_environment_variable('STAGE115C2_OPERATOR_GAIN', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c2_gain = .true.
        end if
        if (t115c2_freeze_heat .or. t115c2_gain) then
            print *, 'STAGE115C2: freeze_heat=', t115c2_freeze_heat, ' operator_gain=', t115c2_gain
        end if
    end subroutine s115c2_init

    logical function t115c2_is_invalid(val)
        real, intent(in) :: val
        t115c2_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c2_is_invalid

    subroutine s115c2_alloc()
        if (allocated(f_t1)) return
        allocate (f_t1(is1, js1, ks1), f_s1(is1, js1, ks1))
        allocate (f_hice(is1, js1, ngr), f_hsnow(is1, js1, ngr))
        allocate (f_an1(is1, js1, ngr1))
        allocate (f_ans(is1, js1), f_wices(is1, js1), f_hices(is1, js1))
        allocate (f_u(is1, js1), f_v(is1, js1))
    end subroutine s115c2_alloc

    ! Вход в gated ocean tail: счёт сабстепов + heat-freeze snapshot/restore.
    subroutine s115c2_gate_entry(iii)
        integer, intent(in) :: iii
        if (.not. t115c2_freeze_heat .and. .not. t115c2_gain) return
        if (iii .le. t115c2_prev_iii) t115c2_substep = 0
        t115c2_prev_iii = iii
        t115c2_substep = t115c2_substep + 1
        if (t115c2_freeze_heat) then
            call s115c2_alloc()
            if (t115c2_substep .eq. 1) then
                f_t1(:, :, :) = t1(:, :, :); f_s1(:, :, :) = s1(:, :, :)
                f_hice(:, :, :) = hice(:, :, :); f_hsnow(:, :, :) = hsnow(:, :, :)
                f_an1(:, :, :) = an1(:, :, :)
                f_ans(:, :) = ans(:, :); f_wices(:, :) = wices(:, :); f_hices(:, :) = hices(:, :)
                f_u(:, :) = u(:, :); f_v(:, :) = v(:, :)
            else
                t1(:, :, :) = f_t1(:, :, :); s1(:, :, :) = f_s1(:, :, :)
                hice(:, :, :) = f_hice(:, :, :); hsnow(:, :, :) = f_hsnow(:, :, :)
                an1(:, :, :) = f_an1(:, :, :)
                ans(:, :) = f_ans(:, :); wices(:, :) = f_wices(:, :); hices(:, :) = f_hices(:, :)
                u(:, :) = f_u(:, :); v(:, :) = f_v(:, :)
            end if
        end if
    end subroutine s115c2_gate_entry

    subroutine s115c2_open_files()
        if (files_open) return
        open (unit=gain_unit, file='operator_gain_112_17_9.csv', status='replace', action='write')
        write (gain_unit, '(A)') 'day,iii,substep,cell,operator,' // &
            'U_before,V_before,U_after,V_after,dU,dV,gain'
        open (unit=energy_unit, file='energy_checkpoint.csv', status='replace', action='write')
        write (energy_unit, '(A)') 'day,iii,substep,checkpoint,' // &
            'E_before,E_after,dE,ninv_before,ninv_after'
        files_open = .true.
    end subroutine s115c2_open_files

    subroutine s115c2_global_energy(E, ninv)
        real, intent(out) :: E
        integer, intent(out) :: ninv
        integer :: i, j, k, ki
        real :: a, b
        E = 0.0; ninv = 0
        do j = 2, js
            do i = 2, is
                ki = kt1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    a = u2(i, j, k); b = v2(i, j, k)
                    if (t115c2_is_invalid(a) .or. t115c2_is_invalid(b)) then
                        ninv = ninv + 1
                    else
                        E = E + a*a + b*b
                    end if
                end do
            end do
        end do
    end subroutine s115c2_global_energy

    ! phase=0 (before): запомнить; phase=1 (after): посчитать и записать.
    subroutine s115c2_op(day, iii, opname, phase)
        integer, intent(in) :: day, iii, phase
        character(len=*), intent(in) :: opname
        real :: E, aE
        integer :: ninv, a_ninv
        if (.not. t115c2_gain) return
        call s115c2_open_files()
        if (phase .eq. 0) then
            b_u1 = u2(C1_I, C1_J, C1_K); b_v1 = v2(C1_I, C1_J, C1_K)
            b_u2 = u2(C2_I, C2_J, C2_K); b_v2 = v2(C2_I, C2_J, C2_K)
            call s115c2_global_energy(b_E, b_ninv)
            b_op = opname; b_day = day; b_iii = iii; b_sub = t115c2_substep
            b_armed = .true.
        else
            if (.not. b_armed) return
            b_armed = .false.
            call s115c2_write_cell('112_17_9', b_u1, b_v1, u2(C1_I, C1_J, C1_K), v2(C1_I, C1_J, C1_K))
            call s115c2_write_cell('112_18_9', b_u2, b_v2, u2(C2_I, C2_J, C2_K), v2(C2_I, C2_J, C2_K))
            call s115c2_global_energy(E, ninv)
            aE = E; a_ninv = ninv
            write (energy_unit, '(I4,2(",",I3),",",A,",",E15.7,",",E15.7,",",E15.7,",",I8,",",I8)') &
                b_day, b_iii, b_sub, trim(b_op), b_E, aE, aE - b_E, b_ninv, a_ninv
            flush (energy_unit)
        end if
    end subroutine s115c2_op

    subroutine s115c2_write_cell(cell, ub, vb, ua, va)
        character(len=*), intent(in) :: cell
        real, intent(in) :: ub, vb, ua, va
        real :: denom, gain, du, dv
        logical :: bad
        bad = t115c2_is_invalid(ub) .or. t115c2_is_invalid(vb) .or. &
              t115c2_is_invalid(ua) .or. t115c2_is_invalid(va)
        du = ua - ub; dv = va - vb
        if (bad) then
            gain = -1.0
        else
            denom = sqrt(ub*ub + vb*vb)
            if (denom .lt. 1e-6) then
                gain = 0.0
            else
                gain = sqrt(ua*ua + va*va)/denom
            end if
        end if
        write (gain_unit, '(I4,2(",",I3),",",A,",",A,",",6(E15.7,","),E15.7)') &
            b_day, b_iii, b_sub, trim(cell), trim(b_op), ub, vb, ua, va, du, dv, gain
        flush (gain_unit)
    end subroutine s115c2_write_cell

end module stage115c2_gain
