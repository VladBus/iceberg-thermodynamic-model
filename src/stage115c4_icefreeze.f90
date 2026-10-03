! ==============================================================================
! Модуль: stage115c4_icefreeze
! Назначение: Stage 11.5C.4 — single-field ice-state freeze forensics
!             (изоляция phase-1 growth компонента).
!             ПОЛНОСТЬЮ ДИАГНОСТИЧЕСКИЙ — не меняет физику модели.
!
! Включается env (default OFF → мгновенный возврат, бит-идентично legacy):
!   STAGE115C4_FREEZE = OFF|UV|HICE|ANS|HSNOW|UV_HICE
!     UV      — freeze u_ice, v_ice (is1,js1)
!     HICE    — freeze hice (is1,js1,ngr), hices (is1,js1)
!     ANS     — freeze ans (is1,js1), an1 (is1,js1,ngr1)
!     HSNOW   — freeze hsnow (is1,js1,ngr), wices (is1,js1)
!     UV_HICE — freeze u,v + hice,hices (комбинация B+C)
! Снапшот на первом gate-fire суток, restore на каждом gate entry
! (океан видит day-start значения; ice/heat между сабстепами
! пересчитывают свободно). txic/tyic НЕ трогаем (exp 11.5C.1).
! t1/s1 НЕ трогаем (11.5C.3 показал no-op).
! Плюс seed-cell ice-state CSV (проверка заморозки + диагностика):
!   seed_ice_state.csv: day,iii,sub,cell,hices,ans,txic,tyic,u_ice,v_ice,
!   hice_sum (сумма категорий) — пишется на каждом gate entry ПОСЛЕ
!   restore (плоские линии = freeze работает).
! ==============================================================================
module stage115c4_icefreeze
    use param
    implicit none

    integer, parameter :: F_OFF = 0, F_UV = 1, F_HICE = 2, F_ANS = 3
    integer, parameter :: F_HSNOW = 4, F_UV_HICE = 5

    integer, save :: t115c4_mode = F_OFF
    ! Canary против скрытой порчи BSS legacy-кодом (см. отчёт 11.5C.4):
    ! если magic или mode вне диапазона — перечитать env (repair) и
    ! напечатать предупреждение (detection). Без repair freeze молча не
    ! срабатывает при порче mode (счётчик+seed при этом выглядят живо).
    integer, save :: t115c4_magic = 0
    integer, parameter :: T115C4_MAGIC_OK = 123456789
    integer, save :: t115c4_substep = 0
    integer, save :: t115c4_prev_iii = -1
    integer, save :: seed_unit = 96
    logical, save :: seed_open = .false.

    real, save, allocatable :: g4_u(:, :), g4_v(:, :)
    real, save, allocatable :: g4_hice(:, :, :), g4_hices(:, :)
    real, save, allocatable :: g4_ans(:, :), g4_an1(:, :, :)
    real, save, allocatable :: g4_hsnow(:, :, :), g4_wices(:, :)

    integer, parameter :: C1_I = 112, C1_J = 17
    integer, parameter :: C2_I = 112, C2_J = 18

contains

    subroutine s115c4_init()
        character(len=32) :: env_str
        call get_environment_variable('STAGE115C4_FREEZE', env_str)
        if (len_trim(env_str) .gt. 0) then
            if (env_str .eq. 'UV') t115c4_mode = F_UV
            if (env_str .eq. 'HICE') t115c4_mode = F_HICE
            if (env_str .eq. 'ANS') t115c4_mode = F_ANS
            if (env_str .eq. 'HSNOW') t115c4_mode = F_HSNOW
            if (env_str .eq. 'UV_HICE') t115c4_mode = F_UV_HICE
        end if
        if (t115c4_mode .ne. F_OFF) then
            t115c4_magic = T115C4_MAGIC_OK
            print *, 'STAGE115C4: freeze mode=', t115c4_mode, ' (1=UV,2=HICE,3=ANS,4=HSNOW,5=UV_HICE)'
        end if
    end subroutine s115c4_init

    subroutine s115c4_alloc(mode)
        integer, intent(in) :: mode
        if (mode .eq. F_UV .or. mode .eq. F_UV_HICE) then
            if (.not. allocated(g4_u)) allocate (g4_u(is1, js1), g4_v(is1, js1))
        end if
        if (mode .eq. F_HICE .or. mode .eq. F_UV_HICE) then
            if (.not. allocated(g4_hice)) allocate (g4_hice(is1, js1, ngr), g4_hices(is1, js1))
        end if
        if (mode .eq. F_ANS) then
            if (.not. allocated(g4_ans)) allocate (g4_ans(is1, js1), g4_an1(is1, js1, ngr1))
        end if
        if (mode .eq. F_HSNOW) then
            if (.not. allocated(g4_hsnow)) allocate (g4_hsnow(is1, js1, ngr), g4_wices(is1, js1))
        end if
    end subroutine s115c4_alloc

    subroutine s115c4_snap(mode)
        integer, intent(in) :: mode
        if (mode .eq. F_UV .or. mode .eq. F_UV_HICE) then
            g4_u(:, :) = u(:, :); g4_v(:, :) = v(:, :)
        end if
        if (mode .eq. F_HICE .or. mode .eq. F_UV_HICE) then
            g4_hice(:, :, :) = hice(:, :, :); g4_hices(:, :) = hices(:, :)
        end if
        if (mode .eq. F_ANS) then
            g4_ans(:, :) = ans(:, :); g4_an1(:, :, :) = an1(:, :, :)
        end if
        if (mode .eq. F_HSNOW) then
            g4_hsnow(:, :, :) = hsnow(:, :, :); g4_wices(:, :) = wices(:, :)
        end if
    end subroutine s115c4_snap

    subroutine s115c4_restore(mode)
        integer, intent(in) :: mode
        if (mode .eq. F_UV .or. mode .eq. F_UV_HICE) then
            u(:, :) = g4_u(:, :); v(:, :) = g4_v(:, :)
        end if
        if (mode .eq. F_HICE .or. mode .eq. F_UV_HICE) then
            hice(:, :, :) = g4_hice(:, :, :); hices(:, :) = g4_hices(:, :)
        end if
        if (mode .eq. F_ANS) then
            ans(:, :) = g4_ans(:, :); an1(:, :, :) = g4_an1(:, :, :)
        end if
        if (mode .eq. F_HSNOW) then
            hsnow(:, :, :) = g4_hsnow(:, :, :); wices(:, :) = g4_wices(:, :)
        end if
    end subroutine s115c4_restore

    ! Вход в gated ocean tail: счёт + snapshot/restore + seed CSV.
    subroutine s115c4_gate_entry(iii, day)
        integer, intent(in) :: iii, day
        if (t115c4_mode .eq. F_OFF) return
        ! Self-check: порча mode/magic после init → repair (перечитать env).
        ! Печатаем при каждом срабатывании (видно в логе; дёшево).
        if (t115c4_magic .ne. T115C4_MAGIC_OK .or. t115c4_mode .lt. F_OFF .or. &
            t115c4_mode .gt. F_UV_HICE) then
            print *, 'STAGE115C4 WARNING: state corrupted (mode=', t115c4_mode, &
                     ' magic=', t115c4_magic, ') at day=', day, ' iii=', iii, ' — re-reading env'
            call s115c4_init()
            if (t115c4_mode .eq. F_OFF) return
        end if
        if (iii .le. t115c4_prev_iii) t115c4_substep = 0
        t115c4_prev_iii = iii
        t115c4_substep = t115c4_substep + 1
        call s115c4_alloc(t115c4_mode)
        if (t115c4_substep .eq. 1) then
            call s115c4_snap(t115c4_mode)
        else
            call s115c4_restore(t115c4_mode)
        end if
        call s115c4_seed_write(day, iii)
    end subroutine s115c4_gate_entry

    subroutine s115c4_seed_write(day, iii)
        integer, intent(in) :: day, iii
        real :: hs1, hs2
        integer :: k
        if (.not. seed_open) then
            open (unit=seed_unit, file='seed_ice_state.csv', status='replace', action='write')
            write (seed_unit, '(A)') 'day,iii,sub,cell,hices,ans,txic,tyic,u_ice,v_ice,hice_sum'
            seed_open = .true.
        end if
        hs1 = 0.0; hs2 = 0.0
        do k = 1, ngr
            hs1 = hs1 + hice(C1_I, C1_J, k)
            hs2 = hs2 + hice(C2_I, C2_J, k)
        end do
        write (seed_unit, '(I4,2(",",I3),",",A,",",6(E15.7,","),E15.7)') &
            day, iii, t115c4_substep, '112_17', hices(C1_I, C1_J), ans(C1_I, C1_J), &
            txic(C1_I, C1_J), tyic(C1_I, C1_J), u(C1_I, C1_J), v(C1_I, C1_J), hs1
        write (seed_unit, '(I4,2(",",I3),",",A,",",6(E15.7,","),E15.7)') &
            day, iii, t115c4_substep, '112_18', hices(C2_I, C2_J), ans(C2_I, C2_J), &
            txic(C2_I, C2_J), tyic(C2_I, C2_J), u(C2_I, C2_J), v(C2_I, C2_J), hs2
        flush (seed_unit)
    end subroutine s115c4_seed_write

end module stage115c4_icefreeze
