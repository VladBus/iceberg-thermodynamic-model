! ==============================================================================
! Модуль: stage115g_skzfreeze
! Назначение: Stage 11.5G — финальная проверка механизма связи (B150-SKZ:
!             dt=150, skz заморожен на суточном стартовом значении,
!             T/S/CA/txic/tyic/ans свежие).
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115G_FREEZE_SKZ=true — заморозка skz на суточном стартовом значении.
!
! Точки вызова (из gated ocean tail в main.f90):
!   s115g_gate_entry(iii) — СРАЗУ после dt-swap, до операторов: подсчёт
!                           сабстепов дня; на первом фаере суток — снапшот skz
!                           (pre-tail = значение конца прошлых суток).
!   s115g_gate_exit()     — в КОНЦЕ фаера гейта (после ss_d2-цикла, у restore
!                           dt): возврат skz к снапшоту КАЖДЫЙ фаер (включая
!                           первый — хвост пересчитал skz в B210).
!
! Аудит изоляции (11.5G): skz пишется ТОЛЬКО в B210 (main:1425) и НЕ читается
! НИКАКОЙ физикой (только диагностика 11.5C.1) — заморозка skz затрагивает
! только диагностическое поле. B210 Thomas использует rr(1) напрямую
! (не skz) — вязкость untouched. T2/S2/CA/txic/tyic/ans свежие.
! (Не путать с skt: heat() fw читает skt (thermo:117), а skt в production
! нигде не пишется — см. отчёт 11.5G.)
! u1-ролловер-теорема (11.5F §1) не нарушена: skz никуда не роллится.
! ==============================================================================
module stage115g_skzfreeze
    use param
    implicit none

    logical, save :: s115g_freeze = .false.
    integer, save :: s115g_substep = 0
    integer, save :: s115g_prev_iii = -1

    ! Freeze-снапшот skz (суточное стартовое значение первого фаера)
    real, save, allocatable :: skz_frz(:, :)

contains

    subroutine s115g_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115G_FREEZE_SKZ', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            s115g_freeze = .true.
        end if
        if (s115g_freeze) then
            print *, 'STAGE115G: freeze_skz=', s115g_freeze
        end if
    end subroutine s115g_init

    ! Вход в gated ocean tail: счёт сабстепов + снапшот на первом фаере суток.
    ! Вызывать СРАЗУ после dt-swap, до любых операторов (рядом с s115c1_gate_entry).
    subroutine s115g_gate_entry(iii)
        integer, intent(in) :: iii
        if (.not. s115g_freeze) return
        ! Новый день: детект через iii <= prev (как в 11.5C.1).
        if (iii .le. s115g_prev_iii) s115g_substep = 0
        s115g_prev_iii = iii
        s115g_substep = s115g_substep + 1
        if (.not. allocated(skz_frz)) then
            allocate (skz_frz(is1, js1))
        end if
        if (s115g_substep .eq. 1) then
            ! Снапшот skz первого фаера суток (pre-tail = конец прошлых суток =
            ! суточное стартовое значение).
            skz_frz(:, :) = skz(:, :)
        end if
    end subroutine s115g_gate_entry

    ! Выход из gated ocean tail: возврат skz к снапшоту КАЖДЫЙ фаер.
    ! Вызывать в конце фаера гейта (после ss_d2-цикла, у restore dt).
    subroutine s115g_gate_exit()
        if (.not. s115g_freeze) return
        if (.not. allocated(skz_frz)) return
        ! B210 внутри хвоста пересчитал skz из свежего сдвига — возвращаем
        ! суточное стартовое значение. T/S/CA/u2/v2/txic/ans остаются свежими.
        skz(:, :) = skz_frz(:, :)
    end subroutine s115g_gate_exit

end module stage115g_skzfreeze
