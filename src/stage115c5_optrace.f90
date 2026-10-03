! ==============================================================================
! Модуль: stage115c5_optrace
! Назначение: Stage 11.5C.5 — same-cell operator-level trace phase-1
!             (N=1 vs N=24): на КАЖДОМ из 9 checkpoint сабстепа пишет
!             состояние seed-ячеек ДО/ПОСЛЕ (текущее + предыдущая точка)
!             + глобальную энергию E=Σ(U²+V²).
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C5_OPERATOR_TRACE=true
! CSV (flush на каждой строке — прогоны 11.5C.5 убиваются на 3-й день!):
!   operator_trace_112_17_9.csv / _112_18_9.csv:
!     day,iii,sub,checkpoint,U_before,V_before,U_after,V_after,dU,dV,
!     E_before,E_after,dE,RO_before,RO_after,dRO,TW_before,TW_after,
!     DPX_before,DPX_after,dDPX,DPY_before,DPY_after,dDPY,txic,tyic,ans
!     (первая строка прогона: before=after, d=0 — честный маркер старта).
!   energy_trace_global.csv:
!     day,iii,sub,checkpoint,Eg_before,Eg_after,dEg,ninv_before,ninv_after
! TW-proxy = c1·H·|∇h RO| (c1=981, H=map1, dx=1.389e6; калиброван в 11.5C.3:
! TW×dt ≈ per-pass ΔU; land/край/non-finite → -1 сентинел).
! Глобальная E: сумма по wet (kt1) без non-finite + их счёт.
! ==============================================================================
module stage115c5_optrace
    use param
    implicit none

    real, parameter :: T115C5_DX = 1389000.0
    real, parameter :: T115C5_C1 = 981.0

    logical, save :: t115c5_on = .false.
    integer, save :: t115c5_substep = 0
    integer, save :: t115c5_prev_iii = -1
    integer, save :: tr1_unit = 97, tr2_unit = 98, eg_unit = 99
    logical, save :: files_open = .false.
    logical, save :: have_prev = .false.

    ! Предыдущая checkpoint-точка (before для текущей)
    real, save :: p_u1, p_v1, p_ro1, p_tw1, p_dpx1, p_dpy1
    real, save :: p_u2, p_v2, p_ro2, p_tw2, p_dpx2, p_dpy2
    real, save :: p_Eg
    integer, save :: p_ninv
    integer, save :: p_day = -1, p_iii = -1, p_sub = -1
    character(len=16), save :: p_label = 'NONE'

    integer, parameter :: C1_I = 112, C1_J = 17, C1_K = 9
    integer, parameter :: C2_I = 112, C2_J = 18, C2_K = 9

contains

    subroutine s115c5_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C5_OPERATOR_TRACE', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c5_on = .true.
            print *, 'STAGE115C5: operator_trace= T'
        end if
    end subroutine s115c5_init

    logical function t115c5_is_invalid(val)
        real, intent(in) :: val
        t115c5_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c5_is_invalid

    subroutine s115c5_open_files()
        if (files_open) return
        open (unit=tr1_unit, file='operator_trace_112_17_9.csv', status='replace', action='write')
        write (tr1_unit, '(A)') 'day,iii,sub,checkpoint,' // &
            'U_before,V_before,U_after,V_after,dU,dV,E_before,E_after,dE,' // &
            'RO_before,RO_after,dRO,TW_before,TW_after,DPX_before,DPX_after,' // &
            'dDPX,DPY_before,DPY_after,dDPY,txic,tyic,ans'
        open (unit=tr2_unit, file='operator_trace_112_18_9.csv', status='replace', action='write')
        write (tr2_unit, '(A)') 'day,iii,sub,checkpoint,' // &
            'U_before,V_before,U_after,V_after,dU,dV,E_before,E_after,dE,' // &
            'RO_before,RO_after,dRO,TW_before,TW_after,DPX_before,DPX_after,' // &
            'dDPX,DPY_before,DPY_after,dDPY,txic,tyic,ans'
        open (unit=eg_unit, file='energy_trace_global.csv', status='replace', action='write')
        write (eg_unit, '(A)') 'day,iii,sub,checkpoint,Eg_before,Eg_after,dEg,ninv_before,ninv_after'
        files_open = .true.
    end subroutine s115c5_open_files

    real function t115c5_tw(i0, j0, k0)
        integer, intent(in) :: i0, j0, k0
        real :: gx, gy, h
        if (i0 < 3 .or. i0 > is - 1 .or. j0 < 3 .or. j0 > js - 1) then
            t115c5_tw = -1.0
            return
        end if
        if (t115c5_is_invalid(ro(i0, j0+1, k0)) .or. t115c5_is_invalid(ro(i0, j0-1, k0)) .or. &
            t115c5_is_invalid(ro(i0+1, j0, k0)) .or. t115c5_is_invalid(ro(i0-1, j0, k0)) .or. &
            t115c5_is_invalid(ro(i0, j0, k0))) then
            t115c5_tw = -1.0
            return
        end if
        gx = (ro(i0, j0+1, k0) - ro(i0, j0-1, k0))/(2.0*T115C5_DX)
        gy = (ro(i0+1, j0, k0) - ro(i0-1, j0, k0))/(2.0*T115C5_DX)
        h = map1(i0, j0)
        if (abs(h - 8888.0) .lt. 1e-8) then
            t115c5_tw = -1.0
            return
        end if
        t115c5_tw = T115C5_C1*abs(h)*sqrt(gx*gx + gy*gy)
    end function t115c5_tw

    subroutine s115c5_global_energy(E, ninv)
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
                    if (t115c5_is_invalid(a) .or. t115c5_is_invalid(b)) then
                        ninv = ninv + 1
                    else
                        E = E + a*a + b*b
                    end if
                end do
            end do
        end do
    end subroutine s115c5_global_energy

    ! Вызывать ПОСЛЕ каждого из 9 checkpoint (START + 8 after-op).
    ! Пишет строку: before = предыдущая точка, after = текущая.
    subroutine s115c5_trace(day, iii, label)
        integer, intent(in) :: day, iii
        character(len=*), intent(in) :: label
        real :: c_u1, c_v1, c_ro1, c_tw1, c_u2, c_v2, c_ro2, c_tw2, Eg
        integer :: ninv
        if (.not. t115c5_on) return
        call s115c5_open_files()
        if (iii .le. t115c5_prev_iii) t115c5_substep = 0
        t115c5_prev_iii = iii
        t115c5_substep = t115c5_substep + 1
        c_u1 = u2(C1_I, C1_J, C1_K); c_v1 = v2(C1_I, C1_J, C1_K)
        c_ro1 = ro(C1_I, C1_J, C1_K); c_tw1 = t115c5_tw(C1_I, C1_J, C1_K)
        c_u2 = u2(C2_I, C2_J, C2_K); c_v2 = v2(C2_I, C2_J, C2_K)
        c_ro2 = ro(C2_I, C2_J, C2_K); c_tw2 = t115c5_tw(C2_I, C2_J, C2_K)
        call s115c5_global_energy(Eg, ninv)
        if (.not. have_prev) then
            ! Первая строка: before=after, d=0.
            call s115c5_write_cell(tr1_unit, day, iii, label, &
                c_u1, c_v1, c_u1, c_v1, c_ro1, c_ro1, c_tw1, c_tw1, C1_I, C1_J)
            call s115c5_write_cell(tr2_unit, day, iii, label, &
                c_u2, c_v2, c_u2, c_v2, c_ro2, c_ro2, c_tw2, c_tw2, C2_I, C2_J)
            write (eg_unit, '(I4,2(",",I3),",",A,",",E15.7,",",E15.7,",",E15.7,",",I8,",",I8)') &
                day, iii, t115c5_substep, trim(label), Eg, Eg, 0.0, ninv, ninv
            flush (eg_unit)
        else
            call s115c5_write_cell(tr1_unit, day, iii, label, &
                p_u1, p_v1, c_u1, c_v1, p_ro1, c_ro1, p_tw1, c_tw1, C1_I, C1_J)
            call s115c5_write_cell(tr2_unit, day, iii, label, &
                p_u2, p_v2, c_u2, c_v2, p_ro2, c_ro2, p_tw2, c_tw2, C2_I, C2_J)
            write (eg_unit, '(I4,2(",",I3),",",A,",",E15.7,",",E15.7,",",E15.7,",",I8,",",I8)') &
                day, iii, t115c5_substep, trim(label), p_Eg, Eg, Eg - p_Eg, p_ninv, ninv
            flush (eg_unit)
        end if
        p_u1 = c_u1; p_v1 = c_v1; p_ro1 = c_ro1; p_tw1 = c_tw1
        p_dpx1 = dpx(C1_I, C1_J); p_dpy1 = dpy(C1_I, C1_J)
        p_u2 = c_u2; p_v2 = c_v2; p_ro2 = c_ro2; p_tw2 = c_tw2
        p_dpx2 = dpx(C2_I, C2_J); p_dpy2 = dpy(C2_I, C2_J)
        p_Eg = Eg; p_ninv = ninv
        p_day = day; p_iii = iii; p_sub = t115c5_substep; p_label = label
        have_prev = .true.
    end subroutine s115c5_trace

    subroutine s115c5_write_cell(unit, day, iii, label, ub, vb, ua, va, rbef, raft, twbef, twaft, i0, j0)
        integer, intent(in) :: unit, day, iii, i0, j0
        character(len=*), intent(in) :: label
        real, intent(in) :: ub, vb, ua, va, rbef, raft, twbef, twaft
        real :: du, dv, eb, ea, dro, dpxb, dpxa, dpyb, dpya
        du = ua - ub; dv = va - vb
        eb = ub*ub + vb*vb; ea = ua*ua + va*va
        dro = raft - rbef
        if (have_prev) then
            if (i0 .eq. C1_I .and. j0 .eq. C1_J) then
                dpxb = p_dpx1; dpyb = p_dpy1
            else
                dpxb = p_dpx2; dpyb = p_dpy2
            end if
        else
            dpxb = dpx(i0, j0); dpyb = dpy(i0, j0)
        end if
        dpxa = dpx(i0, j0); dpya = dpy(i0, j0)
        write (unit, '(I4,2(",",I3),",",A,",",22(E15.7,","),E15.7)') &
            day, iii, t115c5_substep, trim(label), ub, vb, ua, va, du, dv, eb, ea, ea - eb, &
            rbef, raft, dro, twbef, twaft, dpxb, dpxa, dpxa - dpxb, dpyb, dpya, dpya - dpyb, &
            txic(i0, j0), tyic(i0, j0), ans(i0, j0)
        flush (unit)
    end subroutine s115c5_write_cell

end module stage115c5_optrace
