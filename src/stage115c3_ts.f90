! ==============================================================================
! Модуль: stage115c3_ts
! Назначение: Stage 11.5C.3 — чистый T/S-held контроль + B200 input/gain
!             регрессия + temporal sequence tracking.
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C3_FREEZE_TS=true       — заморозка ТОЛЬКО t1/s1 (3D, все k):
!       снапшот на первом gate-fire суток, restore на каждом gate entry.
!       Лёд (hice/hsnow/an1/ans/u/v/txic) эволюционирует СВОБОДНО — чистый
!       тест advectand-ноги (11.5C.2 FREEZE_HEAT морозил и лёд тоже).
!   STAGE115C3_B200_REGRESSION=true — B200 before/after аудит seed-ячеек
!       (112,17,9) [N24-событие] и (112,18,9) [freeze-событие]:
!       U,V,RO,ΔRO(vs day-start RO),dRO/dx,dRO/dy,TW-proxy,DPX,DPY,txic,
!       tyic,ans,UP2,VP2 → gain,cell-ΔE. Два CSV (по ячейке, колонки ТОЧНО
!       по спеке). TW-proxy = c1·H·|∇h RO| (c1=981, H=map1, dx=1.389e6 —
!       литералы из param/main с provenance ниже) — НЕ истинный бароклинный
!       интеграл B200 (он внутренний), задокументированный прокси.
!   STAGE115C3_TEMPORAL_SEQ=true    — на КАЖДОМ checkpoint (8 точек
!       сабстепа): |U|,|ΔRO|,TW-proxy,last-B200-gain обеих ячеек →
!       temporal_sequence_112_17_9.csv + _112_18_9.csv (колонки по спеке).
!       B200_gain = carry-forward последнего завершённого B200 (0.0 если
!       B200 ещё не отработал в прогоне).
! gain-классификация как в 11.5C.2 (denom<1e-6 → 0; non-finite → -1).
! Provenance литералов: dx=1389000 см (param.f90:30); c1=g/roc=981/1
! (main.f90: c1=g/roc, g=981.0, roc=1.0).
! ==============================================================================
module stage115c3_ts
    use param
    implicit none

    real, parameter :: T115C3_DX = 1389000.0
    real, parameter :: T115C3_C1 = 981.0

    logical, save :: t115c3_freeze_ts = .false.
    logical, save :: t115c3_regress = .false.
    logical, save :: t115c3_seq = .false.
    integer, save :: t115c3_substep = 0
    integer, save :: t115c3_prev_iii = -1
    integer, save :: reg1_unit = 92, reg2_unit = 93
    integer, save :: seq1_unit = 94, seq2_unit = 95
    logical, save :: files_open = .false.

    ! FREEZE_TS снапшоты (только t1/s1)
    real, save, allocatable :: f_t1(:, :, :), f_s1(:, :, :)
    ! RO day-start (для ΔRO)
    real, save :: ro0_c1 = 0.0, ro0_c2 = 0.0
    logical, save :: ro0_set = .false.

    ! B200 before-состояние
    real, save :: r_ub1, r_vb1, r_ro1, r_ub2, r_vb2, r_ro2
    integer, save :: r_day = -1, r_iii = -1, r_sub = -1
    logical, save :: r_armed = .false.
    ! last B200 gain (carry-forward для temporal seq)
    real, save :: last_gain_c1 = 0.0, last_gain_c2 = 0.0

    integer, parameter :: C1_I = 112, C1_J = 17, C1_K = 9
    integer, parameter :: C2_I = 112, C2_J = 18, C2_K = 9

contains

    subroutine s115c3_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C3_FREEZE_TS', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c3_freeze_ts = .true.
        end if
        call get_environment_variable('STAGE115C3_B200_REGRESSION', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c3_regress = .true.
        end if
        call get_environment_variable('STAGE115C3_TEMPORAL_SEQ', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            t115c3_seq = .true.
        end if
        if (t115c3_freeze_ts .or. t115c3_regress .or. t115c3_seq) then
            print *, 'STAGE115C3: freeze_ts=', t115c3_freeze_ts, ' regress=', t115c3_regress, &
                     ' temporal_seq=', t115c3_seq
        end if
    end subroutine s115c3_init

    logical function t115c3_is_invalid(val)
        real, intent(in) :: val
        t115c3_is_invalid = (val /= val .or. abs(val) > huge(1.0)*0.5)
    end function t115c3_is_invalid

    subroutine s115c3_open_files()
        if (files_open) return
        if (t115c3_regress) then
            open (unit=reg1_unit, file='b200_regression_112_17_9.csv', status='replace', action='write')
            write (reg1_unit, '(A)') 'day,iii,substep,U_before,V_before,RO,dRO,' // &
                'dRO_dx,dRO_dy,DPX,DPY,txic,tyic,ans,UP2,VP2,U_after,V_after,dU,dV,gain,dE'
            open (unit=reg2_unit, file='b200_regression_112_18_9.csv', status='replace', action='write')
            write (reg2_unit, '(A)') 'day,iii,substep,U_before,V_before,RO,dRO,' // &
                'dRO_dx,dRO_dy,DPX,DPY,txic,tyic,ans,UP2,VP2,U_after,V_after,dU,dV,gain,dE'
        end if
        if (t115c3_seq) then
            open (unit=seq1_unit, file='temporal_sequence_112_17_9.csv', status='replace', action='write')
            write (seq1_unit, '(A)') 'day,iii,substep,checkpoint,U_abs,dRO_abs,TW_abs,B200_gain'
            open (unit=seq2_unit, file='temporal_sequence_112_18_9.csv', status='replace', action='write')
            write (seq2_unit, '(A)') 'day,iii,substep,checkpoint,U_abs,dRO_abs,TW_abs,B200_gain'
        end if
        files_open = .true.
    end subroutine s115c3_open_files

    ! Вход в gated ocean tail: счёт + FREEZE_TS + RO day-start.
    subroutine s115c3_gate_entry(iii)
        integer, intent(in) :: iii
        if (.not. t115c3_freeze_ts .and. .not. t115c3_regress .and. .not. t115c3_seq) return
        if (iii .le. t115c3_prev_iii) t115c3_substep = 0
        t115c3_prev_iii = iii
        t115c3_substep = t115c3_substep + 1
        if (t115c3_substep .eq. 1) then
            ! Day-start RO seed-ячеек (база ΔRO). Читаем ПОСЛЕ iii=1
            ! heat/ice (конвенция 11.5C.1/11.5C.2, задокументировано).
            ro0_c1 = ro(C1_I, C1_J, C1_K)
            ro0_c2 = ro(C2_I, C2_J, C2_K)
            ro0_set = .true.
        end if
        if (t115c3_freeze_ts) then
            if (.not. allocated(f_t1)) allocate (f_t1(is1, js1, ks1), f_s1(is1, js1, ks1))
            if (t115c3_substep .eq. 1) then
                f_t1(:, :, :) = t1(:, :, :)
                f_s1(:, :, :) = s1(:, :, :)
            else
                t1(:, :, :) = f_t1(:, :, :)
                s1(:, :, :) = f_s1(:, :, :)
            end if
        end if
    end subroutine s115c3_gate_entry

    real function t115c3_tw(i0, j0, k0)
        integer, intent(in) :: i0, j0, k0
        real :: gx, gy, h
        ! Центральные разности RO (X↔j, Y↔i); land/край → -1 сентинел.
        if (i0 < 3 .or. i0 > is - 1 .or. j0 < 3 .or. j0 > js - 1) then
            t115c3_tw = -1.0
            return
        end if
        if (t115c3_is_invalid(ro(i0, j0+1, k0)) .or. t115c3_is_invalid(ro(i0, j0-1, k0)) .or. &
            t115c3_is_invalid(ro(i0+1, j0, k0)) .or. t115c3_is_invalid(ro(i0-1, j0, k0)) .or. &
            t115c3_is_invalid(ro(i0, j0, k0))) then
            t115c3_tw = -1.0
            return
        end if
        gx = (ro(i0, j0+1, k0) - ro(i0, j0-1, k0))/(2.0*T115C3_DX)
        gy = (ro(i0+1, j0, k0) - ro(i0-1, j0, k0))/(2.0*T115C3_DX)
        h = map1(i0, j0)
        if (abs(h - 8888.0) .lt. 1e-8) then
            t115c3_tw = -1.0
            return
        end if
        t115c3_tw = T115C3_C1*abs(h)*sqrt(gx*gx + gy*gy)
    end function t115c3_tw

    subroutine s115c3_dROdxdy(i0, j0, k0, gx, gy)
        integer, intent(in) :: i0, j0, k0
        real, intent(out) :: gx, gy
        gx = -1.0; gy = -1.0
        if (i0 < 3 .or. i0 > is - 1 .or. j0 < 3 .or. j0 > js - 1) return
        if (t115c3_is_invalid(ro(i0, j0+1, k0)) .or. t115c3_is_invalid(ro(i0, j0-1, k0)) .or. &
            t115c3_is_invalid(ro(i0+1, j0, k0)) .or. t115c3_is_invalid(ro(i0-1, j0, k0))) return
        gx = (ro(i0, j0+1, k0) - ro(i0, j0-1, k0))/(2.0*T115C3_DX)
        gy = (ro(i0+1, j0, k0) - ro(i0-1, j0, k0))/(2.0*T115C3_DX)
    end subroutine s115c3_dROdxdy

    real function t115c3_gain(ub, vb, ua, va)
        real, intent(in) :: ub, vb, ua, va
        real :: denom
        if (t115c3_is_invalid(ub) .or. t115c3_is_invalid(vb) .or. &
            t115c3_is_invalid(ua) .or. t115c3_is_invalid(va)) then
            t115c3_gain = -1.0
            return
        end if
        denom = sqrt(ub*ub + vb*vb)
        if (denom .lt. 1e-6) then
            t115c3_gain = 0.0
        else
            t115c3_gain = sqrt(ua*ua + va*va)/denom
        end if
    end function t115c3_gain

    ! phase=0 (до B200): запомнить; phase=1 (после): посчитать и записать.
    subroutine s115c3_b200(day, iii, phase)
        integer, intent(in) :: day, iii, phase
        if (.not. t115c3_regress) return
        call s115c3_open_files()
        if (phase .eq. 0) then
            r_ub1 = u2(C1_I, C1_J, C1_K); r_vb1 = v2(C1_I, C1_J, C1_K); r_ro1 = ro(C1_I, C1_J, C1_K)
            r_ub2 = u2(C2_I, C2_J, C2_K); r_vb2 = v2(C2_I, C2_J, C2_K); r_ro2 = ro(C2_I, C2_J, C2_K)
            r_day = day; r_iii = iii; r_sub = t115c3_substep
            r_armed = .true.
        else
            if (.not. r_armed) return
            r_armed = .false.
            call s115c3_write_reg(reg1_unit, C1_I, C1_J, C1_K, r_ub1, r_vb1, r_ro1, ro0_c1, &
                                  u2(C1_I, C1_J, C1_K), v2(C1_I, C1_J, C1_K))
            call s115c3_write_reg(reg2_unit, C2_I, C2_J, C2_K, r_ub2, r_vb2, r_ro2, ro0_c2, &
                                  u2(C2_I, C2_J, C2_K), v2(C2_I, C2_J, C2_K))
            last_gain_c1 = t115c3_gain(r_ub1, r_vb1, u2(C1_I, C1_J, C1_K), v2(C1_I, C1_J, C1_K))
            last_gain_c2 = t115c3_gain(r_ub2, r_vb2, u2(C2_I, C2_J, C2_K), v2(C2_I, C2_J, C2_K))
        end if
    end subroutine s115c3_b200

    subroutine s115c3_write_reg(unit, i0, j0, k0, ub, vb, rbef, ro0, ua, va)
        integer, intent(in) :: unit, i0, j0, k0
        real, intent(in) :: ub, vb, rbef, ro0, ua, va
        real :: gx, gy, dro, rnow, gain, du, dv, dE, eb, ea
        logical :: bad
        call s115c3_dROdxdy(i0, j0, k0, gx, gy)
        rnow = ro(i0, j0, k0)
        if (t115c3_is_invalid(rnow) .or. t115c3_is_invalid(ro0)) then
            dro = -1.0
        else
            dro = rnow - ro0
        end if
        gain = t115c3_gain(ub, vb, ua, va)
        du = ua - ub; dv = va - vb
        bad = t115c3_is_invalid(ub) .or. t115c3_is_invalid(vb) .or. &
              t115c3_is_invalid(ua) .or. t115c3_is_invalid(va)
        if (bad) then
            dE = -1.0
        else
            eb = ub*ub + vb*vb; ea = ua*ua + va*va
            dE = ea - eb
        end if
        write (unit, '(I4,2(",",I3),",",18(E15.7,","),E15.7)') &
            r_day, r_iii, r_sub, ub, vb, rbef, dro, gx, gy, &
            dpx(i0, j0), dpy(i0, j0), txic(i0, j0), tyic(i0, j0), ans(i0, j0), &
            up2(i0, j0), vp2(i0, j0), ua, va, du, dv, gain, dE
        flush (unit)
    end subroutine s115c3_write_reg

    ! Temporal checkpoint: вызывать ПОСЛЕ каждого из 8 s115c1-checkpoint.
    subroutine s115c3_seq(day, iii, label)
        integer, intent(in) :: day, iii
        character(len=*), intent(in) :: label
        real :: u1, v1, u2v, v2v, r1, r2, tw1, tw2, a1, a2
        if (.not. t115c3_seq) return
        call s115c3_open_files()
        u1 = u2(C1_I, C1_J, C1_K); v1 = v2(C1_I, C1_J, C1_K)
        u2v = u2(C2_I, C2_J, C2_K); v2v = v2(C2_I, C2_J, C2_K)
        r1 = ro(C1_I, C1_J, C1_K); r2 = ro(C2_I, C2_J, C2_K)
        if (t115c3_is_invalid(u1) .or. t115c3_is_invalid(v1)) then
            a1 = -1.0
        else
            a1 = sqrt(u1*u1 + v1*v1)
        end if
        if (t115c3_is_invalid(u2v) .or. t115c3_is_invalid(v2v)) then
            a2 = -1.0
        else
            a2 = sqrt(u2v*u2v + v2v*v2v)
        end if
        tw1 = t115c3_tw(C1_I, C1_J, C1_K)
        tw2 = t115c3_tw(C2_I, C2_J, C2_K)
        write (seq1_unit, '(I4,2(",",I3),",",A,",",E15.7,",",E15.7,",",E15.7,",",E15.7)') &
            day, iii, t115c3_substep, trim(label), a1, abs_dro(r1, ro0_c1), tw1, last_gain_c1
        write (seq2_unit, '(I4,2(",",I3),",",A,",",E15.7,",",E15.7,",",E15.7,",",E15.7)') &
            day, iii, t115c3_substep, trim(label), a2, abs_dro(r2, ro0_c2), tw2, last_gain_c2
        flush (seq1_unit)
        flush (seq2_unit)
    end subroutine s115c3_seq

    real function abs_dro(rnow, ro0)
        real, intent(in) :: rnow, ro0
        if (t115c3_is_invalid(rnow) .or. t115c3_is_invalid(ro0)) then
            abs_dro = -1.0
        else
            abs_dro = abs(rnow - ro0)
        end if
    end function abs_dro

end module stage115c3_ts
