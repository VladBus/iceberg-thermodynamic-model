! ==============================================================================
! Модуль: stage114_d28_trace (Stage 11.4-D28)
! Назначение: Forensic-прослеживание происхождения "Ghost Ice"
!   (an1>0 при wice1=0) в ячейке (2,95), категория 5 (an1-индекс 6).
!   Контрольные точки в main.f90: INIT (после стартового redis),
!   PRE_HEAT (перед heat), POST_ADV (после adv2d льда), POST_REDIS.
!   Только день 1 (nday1==1), только одна ячейка/категория — десятки строк.
!   За воротами env STAGE114_D28_TRACE (default OFF).
! Физика: не меняет ничего — только чтение + print при выключенном флаге
!   лишь проверки env; численные результаты бит-идентичны.
!   NO guards, NO clamps, NO изменений схем/уравнений/начальных условий.
! ==============================================================================

module stage114_d28_trace
    implicit none
    logical, save :: d28_armed = .false.
    logical, save :: d28_env_read = .false.

contains

    subroutine d28_read_env()
        character(len=256) :: env_str
        if (.not. d28_env_read) then
            call get_environment_variable('STAGE114_D28_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d28_armed = .true.
            end if
            d28_env_read = .true.
        end if
    end subroutine d28_read_env

    subroutine d28_check(tag, nday1, iii, an1v, wice1v, hicev, hsnowv)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: nday1, iii
        real, intent(in) :: an1v, wice1v, hicev, hsnowv
        logical :: ghost
        call d28_read_env()
        if (.not. d28_armed) return
        if (nday1 .ne. 1) return
        ghost = (an1v .gt. 0.001 .and. .not. (wice1v .gt. 1.0e-8))
        if (ghost) then
            print *, 'D28_GHOST ', trim(tag), 'day1 iii=', iii, &
                     'an1=', an1v, 'wice1=', wice1v, 'hice=', hicev, 'hsnow=', hsnowv
        else
            print *, 'D28_STATE ', trim(tag), 'day1 iii=', iii, &
                     'an1=', an1v, 'wice1=', wice1v, 'hice=', hicev, 'hsnow=', hsnowv
        end if
    end subroutine d28_check

    ! Окрестность (2,95) для адвективного аудита: какие соседи/скорости
    ! несут NaN на POST_ADV. Печать только в день 1, iii<=2 (граница инфекции).
    subroutine d28_hood(tag, nday1, iii, an1c, wice1c, uc, vc, uoc, voc)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: nday1, iii
        real, intent(in) :: an1c(3, 3), wice1c(3, 3), uc(2, 2), vc(2, 2)
        real, intent(in) :: uoc(2, 2), voc(2, 2)
        call d28_read_env()
        if (.not. d28_armed) return
        if (nday1 .ne. 1 .or. iii .gt. 2) return
        print *, 'D28_HOOD ', trim(tag), 'day1 iii=', iii
        print *, '  an1(1:3,94:96,6)=', an1c
        print *, '  wice1(1:3,94:96,5)=', wice1c
        print *, '  u(2:3,95:96)=', uc, ' v(2:3,95:96)=', vc
        print *, '  u2(2:3,95:96,1)=', uoc, ' v2(2:3,95:96,1)=', voc
    end subroutine d28_hood

end module stage114_d28_trace
