! ==============================================================================
! Модуль: stage114_d26_trace (Stage 11.4-D26)
! Назначение: Точечная forensic-диагностика NaN в s1/t1 (только heat()).
!   Срабатывает ТОЛЬКО для ячейки (i,j)=(2,2), уровень 1, и ТОЛЬКО когда
!   свежеприсвоенные s1/t1 уже NaN/Inf. Печатает все операнды обоих
!   s1/t1-присваиваний heat(). За воротами env STAGE114_D26_TRACE (default OFF).
! Физика: не меняет ничего — только чтение + print. При выключенном флаге
!   единственный эффект — сравнения (i==2, j==2) и проверки NaN на s1/t1
!   в одной ячейке за вызов (пренебрежимо; численные результаты бит-идентичны).
! ==============================================================================

module stage114_d26_trace
    implicit none
    logical, save :: d26_armed = .false.
    logical, save :: d26_env_read = .false.

contains

    subroutine d26_heat_trap(nday, i, j, branch, ann1, ann2, b_tmp, qn, a_tmp, &
                             danp, hicp, hsnp, sicst, tpar1, spar1, a1, b1, a2, b2, &
                             a3_tmp, b3_tmp, dzz, s1v, t1v, anp, tpar, spar)
        integer, intent(in) :: nday, i, j, branch
        real, intent(in) :: ann1, ann2, b_tmp, qn, a_tmp
        real, intent(in) :: danp(:), hicp(:), hsnp(:), sicst(:)
        real, intent(in) :: anp(:), tpar(:), spar(:)
        real, intent(in) :: tpar1, spar1, a1, b1, a2, b2, a3_tmp, b3_tmp, dzz, s1v, t1v
        character(len=256) :: env_str

        if (.not. d26_env_read) then
            call get_environment_variable('STAGE114_D26_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d26_armed = .true.
            end if
            d26_env_read = .true.
        end if
        if (.not. d26_armed) return
        print *, 'D26_HEAT_NAN day=', nday, 'i=', i, 'j=', j, 'branch=', branch
        print *, '  ann1=', ann1, 'ann2=', ann2, 'b_tmp=', b_tmp, 'qn=', qn, 'a_tmp=', a_tmp
        print *, '  danp=', danp
        print *, '  hicp=', hicp
        print *, '  hsnp=', hsnp
        print *, '  sicst=', sicst
        print *, '  tpar1=', tpar1, 'spar1=', spar1, 'a1=', a1, 'b1=', b1
        print *, '  a2=', a2, 'b2=', b2, 'a3_tmp=', a3_tmp, 'b3_tmp=', b3_tmp, 'dzz=', dzz
        print *, '  s1=', s1v, 't1=', t1v
        print *, '  anp=', anp
        print *, '  tpar=', tpar
        print *, '  spar=', spar
    end subroutine d26_heat_trap

    ! D26 entry-snapshot: вызывается в начале обработки ячейки в heat(),
    ! только если tpar(6)/spar(6) уже NaN/Inf на входе (унаследованное состояние
    ! общих модульных массивов). Отличает "создано в ячейке" от "унаследовано".
    subroutine d26_heat_entry(nday, i, j, ann1, tpar, spar)
        integer, intent(in) :: nday, i, j
        real, intent(in) :: ann1
        real, intent(in) :: tpar(:), spar(:)
        character(len=256) :: env_str2
        if (.not. d26_env_read) then
            call get_environment_variable('STAGE114_D26_TRACE', env_str2)
            if (len_trim(env_str2) .gt. 0 .and. (env_str2 .eq. 'true' .or. env_str2 .eq. '1')) then
                d26_armed = .true.
            end if
            d26_env_read = .true.
        end if
        if (.not. d26_armed) return
        print *, 'D26_HEAT_ENTRY day=', nday, 'i=', i, 'j=', j, 'ann1=', ann1
        print *, '  tpar=', tpar
        print *, '  spar=', spar
    end subroutine d26_heat_entry

end module stage114_d26_trace
