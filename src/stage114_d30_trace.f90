! ==============================================================================
! Модуль: stage114_d30_trace (Stage 11.4-D30)
! Назначение: Покатегорийная декомпозиция hices(2,96) — поиск первой категории
!   и первого чекпоинта с NaN. Точки: INIT/PRE_HEAT/POST_ADV/POST_REDIS
!   (все 5 категорий AN1/WICE1 + HICES), внутри-adv2d покатегорийно (AN1/WICE1
!   текущей k сразу после её адвекции), внутри-REDIS перед суммированием
!   (anpr/wicpr/a1/b1). Только день 1, iii<=2 (INIT iii=0).
!   За воротами env STAGE114_D30_TRACE (default OFF).
! Физика: не меняет ничего — только чтение + print; вызовы закрыты дешёвыми
!   целочисленными пре-гардами; результаты бит-идентичны.
!   NO guards, NO clamps, NO изменений схем/уравнений/инициализаций.
! ==============================================================================

module stage114_d30_trace
    implicit none
    logical, save :: d30_armed = .false.
    logical, save :: d30_env_read = .false.
    integer, save :: d30_day = -1
    integer, save :: d30_iii = -1

contains

    subroutine d30_read_env()
        character(len=256) :: env_str
        if (.not. d30_env_read) then
            call get_environment_variable('STAGE114_D30_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d30_armed = .true.
            end if
            d30_env_read = .true.
        end if
    end subroutine d30_read_env

    ! Часы: main сообщает текущий день/субстеп перед вызовами redis.
    subroutine d30_set_clock(nday1, iii)
        integer, intent(in) :: nday1, iii
        call d30_read_env()
        if (.not. d30_armed) return
        d30_day = nday1
        d30_iii = iii
    end subroutine d30_set_clock

    logical function d30_active()
        call d30_read_env()
        d30_active = (d30_armed .and. d30_day .eq. 1 .and. d30_iii .le. 2)
    end function d30_active

    ! Полный покатегорийный снимок (2,96) из main.
    subroutine d30_cell(tag, an5, w5, hicesv)
        character(len=*), intent(in) :: tag
        real, intent(in) :: an5(5), w5(5), hicesv
        integer :: k
        logical :: bad
        if (.not. d30_active()) return
        bad = .false.
        do k = 1, 5
            if (an5(k) /= an5(k) .or. w5(k) /= w5(k)) bad = .true.
        end do
        if (hicesv /= hicesv) bad = .true.
        if (bad) then
            print *, 'D30_GHOSTCELL ', trim(tag), 'day1 iii=', d30_iii
        else
            print *, 'D30_CELL ', trim(tag), 'day1 iii=', d30_iii
        end if
        print *, '  an1(2,96,2:6)=', an5
        print *, '  wice1(2,96,1:5)=', w5
        print *, '  hices(2,96)=', hicesv
    end subroutine d30_cell

    ! Внутри-adv2d: состояние текущей категории k сразу после её адвекции.
    subroutine d30_advk(k, an1v, wice1v)
        integer, intent(in) :: k
        real, intent(in) :: an1v, wice1v
        if (.not. d30_active()) return
        if (an1v /= an1v .or. wice1v /= wice1v) then
            print *, 'D30_ADVK_NAN day1 iii=', d30_iii, 'k=', k, 'an1=', an1v, 'wice1=', wice1v
        else
            print *, 'D30_ADVK day1 iii=', d30_iii, 'k=', k, 'an1=', an1v, 'wice1=', wice1v
        end if
    end subroutine d30_advk

    ! Внутри-REDIS (этап 6): рабочие категории + бегущие суммы для (2,96).
    subroutine d30_redis_cell(i, j, anpr, wicpr, a1, b1)
        integer, intent(in) :: i, j
        real, intent(in) :: anpr(:), wicpr(:), a1, b1
        integer :: k
        logical :: bad
        if (.not. d30_active()) return
        if (i .ne. 2 .or. j .ne. 96) return
        bad = .false.
        do k = 1, 5
            if (anpr(k) /= anpr(k) .or. wicpr(k) /= wicpr(k)) bad = .true.
        end do
        if (a1 /= a1 .or. b1 /= b1) bad = .true.
        if (bad) then
            print *, 'D30_REDIS_NAN day1 iii=', d30_iii, ' a1=', a1, ' b1=', b1
        else
            print *, 'D30_REDIS day1 iii=', d30_iii, ' a1=', a1, ' b1=', b1
        end if
        print *, '  anpr=', anpr
        print *, '  wicpr=', wicpr
    end subroutine d30_redis_cell

    ! Внутри-heat: состояние категории k после фазовых переходов (2,96).
    ! Печать первого невалидного hicp/tpar/spar (защёлка).
    subroutine d30_heatk(nday, k, anpk, hicpk, hsnpk, dhicv, dhsnv, tpk, spk, twa)
        integer, intent(in) :: nday, k
        real, intent(in) :: anpk, hicpk, hsnpk, dhicv, dhsnv, tpk, spk, twa
        logical, save :: fired = .false.
        call d30_read_env()
        if (.not. d30_armed) return
        if (nday .ne. 1 .or. d30_iii .gt. 2) return
        if (fired) return
        if (.not. (hicpk /= hicpk .or. tpk /= tpk .or. spk /= spk)) return
        fired = .true.
        print *, 'D30_HEATK day1 iii=', d30_iii, 'k=', k
        print *, '  anp=', anpk, 'hicp=', hicpk, 'hsnp=', hsnpk
        print *, '  dhic=', dhicv, 'dhsn=', dhsnv, 'twa=', twa
        print *, '  tpar(k1)=', tpk, 'spar(k1)=', spk
    end subroutine d30_heatk

end module stage114_d30_trace
