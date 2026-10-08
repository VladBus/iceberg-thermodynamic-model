! ==============================================================================
! Модуль: stage115h_production
! Назначение: Stage 11.5H — production temporal architecture
!             (OCEAN_DT=150, 24 fires/day × 24 passes, shal 1×/day,
!             STALE ice→ocean coupling: day-start txic/tyic/ans).
!             Диагностический каркас вокруг НЕИЗМЕННОЙ физики: операторы,
!             схемы, коэффициенты, shal(), EOS, CA untouched.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115H_PRODUCTION_MODE=true — production scheduler:
!     - конфиг форсируется в override main.f90 (forensic env 115C/D/F/G
!       НЕ опрашивается на production-пути);
!     - STALE ice→ocean: снапшот txic/tyic/ans первого фаера суток,
!       restore на поздних фаерах (семантика = 11.5F F3, но production-owned);
!     - forensic hooks (115C/115G) пропускаются в main через
!       s115h_prod_active() guard;
!     - T/S/CA/u2/v2 свежие каждый сабстеп; B210 Thomas на rr(1) untouched.
!
! Точки вызова в main.f90:
!   s115h_init()         — ПЕРЕД 115C parse-блоком (флаг нужен override).
!   s115h_prod_active()  — logical function для guard/if.
!   s115h_gate_entry(iii)— в gate entry cluster (STALE snapshot/restore).
!   s115h_warn_ignored() — в production override: предупреждение о
!                          проигнорированных конфликтующих env (11.5H-RC:
!                          self-contained scheduler, без silent fallback).
! ==============================================================================
module stage115h_production
    use param
    implicit none

    logical, save :: s115h_prod = .false.
    integer, save :: s115h_substep = 0
    integer, save :: s115h_prev_iii = -1

    ! STALE-снапшоты ice→ocean (суточные стартовые значения первого фаера)
    real, save, allocatable :: txic_s(:, :), tyic_s(:, :), ans_s(:, :)

contains

    subroutine s115h_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115H_PRODUCTION_MODE', env_str)
        if (len_trim(env_str) .gt. 0 .and. &
            (env_str .eq. 'true' .or. env_str .eq. 'TRUE' .or. env_str .eq. '1')) then
            s115h_prod = .true.
        end if
        if (s115h_prod) then
            print *, 'STAGE115H production mode: OCEAN_DT=150 STALE coupling'
        end if
    end subroutine s115h_init

    logical function s115h_prod_active()
        s115h_prod_active = s115h_prod
    end function s115h_prod_active

    ! Предупреждение о проигнорированной конфликтующей env-переменной.
    ! Только на production-пути (11.5H-RC self-containment: production
    ! форсирует собственный конфиг и НЕ читает forensic env).
    subroutine s115h_warn_ignored(env_name)
        character(len=*), intent(in) :: env_name
        character(len=32) :: env_str
        if (.not. s115h_prod) return
        call get_environment_variable(env_name, env_str)
        if (len_trim(env_str) .gt. 0) then
            print *, 'STAGE115H WARNING: ', trim(env_name), '="', &
                     trim(env_str), '" ignored (production forces its own config)'
        end if
    end subroutine s115h_warn_ignored

    ! STALE ice→ocean: snapshot day-start, restore на поздних фаерах суток.
    ! Вызывать в gate entry cluster. При OFF — мгновенный возврат.
    subroutine s115h_gate_entry(iii)
        integer, intent(in) :: iii
        if (.not. s115h_prod) return
        ! Новый день: детект через iii <= prev (как в 11.5C.1/11.5G).
        if (iii .le. s115h_prev_iii) s115h_substep = 0
        s115h_prev_iii = iii
        s115h_substep = s115h_substep + 1
        if (.not. allocated(txic_s)) then
            allocate (txic_s(is1, js1), tyic_s(is1, js1), ans_s(is1, js1))
        end if
        if (s115h_substep .eq. 1) then
            ! Снапшот ice→ocean первого фаера суток (pre-tail).
            txic_s(:, :) = txic(:, :)
            tyic_s(:, :) = tyic(:, :)
            ans_s(:, :) = ans(:, :)
        else
            ! STALE: океанские сабстепы видят стартовое состояние льда суток
            ! (ледовая модель между фаерами пересчитывается свободно —
            ! трогаем только входы океана; семантика = 11.5F F3).
            txic(:, :) = txic_s(:, :)
            tyic(:, :) = tyic_s(:, :)
            ans(:, :) = ans_s(:, :)
        end if
    end subroutine s115h_gate_entry

end module stage115h_production
