! ==============================================================================
! Модуль: stage114_d31_trace (Stage 11.4-D31)
! Назначение: (1) Декомпозиция операндов dhic1 в heat() для (2,96,k=1) —
!   поиск невалидного входа поверхностного таяния; (2) темпоральные
!   чекпоинты POST_HEAT(iii=1) / PRE_DYN(iii<=2) / POST_DYN(iii<=2) для
!   установления первенства: heat(iii=2) vs более ранняя порча.
!   Часы d31_set_clock ставит main (PRE_HEAT); ловушка dhic1 срабатывает
!   только при часах (1,2) и только на первый невалидный dhic1/hicp.
!   За воротами env STAGE114_D31_TRACE (default OFF).
! Физика: не меняет ничего — только чтение + print; вызовы закрыты дешёвыми
!   целочисленными пре-гардами; результаты бит-идентичны.
!   NO guards, NO clamps, NO изменений уравнений/инициализаций.
! ==============================================================================

module stage114_d31_trace
    implicit none
    logical, save :: d31_armed = .false.
    logical, save :: d31_env_read = .false.
    integer, save :: d31_day = -1
    integer, save :: d31_iii = -1
    logical, save :: d31_fired = .false.

contains

    subroutine d31_read_env()
        character(len=256) :: env_str
        if (.not. d31_env_read) then
            call get_environment_variable('STAGE114_D31_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d31_armed = .true.
            end if
            d31_env_read = .true.
        end if
    end subroutine d31_read_env

    subroutine d31_set_clock(nday1, iii)
        integer, intent(in) :: nday1, iii
        call d31_read_env()
        if (.not. d31_armed) return
        d31_day = nday1
        d31_iii = iii
    end subroutine d31_set_clock

    logical function d31_bad(x)
        real, intent(in) :: x
        d31_bad = (x /= x .or. abs(x) > huge(1.0)*0.5)
    end function d31_bad

    ! Ловушка операндов dhic1 (только (2,96,k=1), только часы (1,2)).
    subroutine d31_dhic1(hbefore, hafter, dhic1v, tta, twa, tts, tfr, &
                         hhum, a3c, elc, shc, swc, wlc, a1c, bc)
        real, intent(in) :: hbefore, hafter, dhic1v, tta, twa, tts, tfr
        real, intent(in) :: hhum, a3c, elc, shc, swc, wlc, a1c, bc
        call d31_read_env()
        if (.not. d31_armed) return
        if (d31_day .ne. 1 .or. d31_iii .ne. 2) return
        if (d31_fired) return
        if (.not. (d31_bad(dhic1v) .or. d31_bad(hafter))) return
        d31_fired = .true.
        print *, 'D31_DHIC1 day1 iii=2 k=1'
        print *, '  hicp_before=', hbefore, 'hicp_after=', hafter, 'dhic1=', dhic1v
        print *, '  tta=', tta, 'twa=', twa, 'tts=', tts, 'tfr=', tfr
        print *, '  hhum=', hhum, 'a3=', a3c, 'el=', elc, 'sh=', shc
        print *, '  sw=', swc, 'wl=', wlc, 'a1=', a1c, 'b=', bc
    end subroutine d31_dhic1

    ! Темпоральный чекпоинт: полные категории (2,96) + hices + u/v льда.
    subroutine d31_cell(tag, nday1, iii, an5, w5, hicesv, uiv, viv)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: nday1, iii
        real, intent(in) :: an5(5), w5(5), hicesv, uiv, viv
        integer :: k
        logical :: bad
        call d31_read_env()
        if (.not. d31_armed) return
        if (nday1 .ne. 1 .or. iii .gt. 2) return
        bad = .false.
        do k = 1, 5
            if (an5(k) /= an5(k) .or. w5(k) /= w5(k)) bad = .true.
        end do
        if (hicesv /= hicesv .or. uiv /= uiv .or. viv /= viv) bad = .true.
        if (bad) then
            print *, 'D31_GHOSTCELL ', trim(tag), 'day1 iii=', iii
        else
            print *, 'D31_CELL ', trim(tag), 'day1 iii=', iii
        end if
        print *, '  an1(2,96,2:6)=', an5
        print *, '  wice1(2,96,1:5)=', w5
        print *, '  hices=', hicesv, ' u_ice=', uiv, ' v_ice=', viv
    end subroutine d31_cell

end module stage114_d31_trace
