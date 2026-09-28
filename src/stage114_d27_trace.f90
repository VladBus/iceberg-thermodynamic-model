! ==============================================================================
! Модуль: stage114_d27_trace (Stage 11.4-D27)
! Назначение: Forensic-поиск "Patient Zero" — первой ячейки/операции,
!   записывающей NaN/Inf в общие scratch tpar(6)/spar(6) в heat().
!   Проверки стоят после всех четырёх writer-сайтов индекса 6
!   (site 1 = spar melt, 2 = tpar melt, 3 = spar growth, 4 = tpar growth).
!   Первое срабатывание фиксируется защёлкой (d27_reported) — один отчёт.
!   За воротами env STAGE114_D27_TRACE (default OFF).
!   Отдельный флаг STAGE114_D27_INIT включает контролируемый эксперимент:
!   детерминированную инициализацию tpar(6)/spar(6) фоном ячейки (twa/a).
! Физика: не меняет ничего при выключенных флагах — только чтения локальных
!   копий и возвраты из subroutine; численные результаты бит-идентичны.
!   NO MAX-гуардов, NO NaN-клампов, NO изменений уравнений.
! ==============================================================================

module stage114_d27_trace
    implicit none
    logical, save :: d27_armed = .false.
    logical, save :: d27_env_read = .false.
    logical, save :: d27_reported = .false.
    logical, save :: d27_init_on = .false.
    logical, save :: d27_init_read = .false.

contains

    subroutine d27_read_env()
        character(len=256) :: env_str
        if (.not. d27_env_read) then
            call get_environment_variable('STAGE114_D27_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d27_armed = .true.
            end if
            d27_env_read = .true.
        end if
        if (.not. d27_init_read) then
            call get_environment_variable('STAGE114_D27_INIT', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d27_init_on = .true.
            end if
            d27_init_read = .true.
        end if
    end subroutine d27_read_env

    logical function d27_use_init()
        call d27_read_env()
        d27_use_init = d27_init_on
    end function d27_use_init

    ! Проверка после writer-сайта индекса 6: стал ли tpar(6)/spar(6) невалидным.
    ! old_t/old_s — значения ДО присваивания (различает "создано здесь"
    ! от "унаследовано"). Печатает только первое срабатывание (защёлка).
    subroutine d27_poison_check(nday, i, j, k, site, old_t, old_s, &
                               anp, hicp, hsnp, sicst, tpar, spar)
        integer, intent(in) :: nday, i, j, k, site
        real, intent(in) :: old_t, old_s
        real, intent(in) :: anp(:), hicp(:), hsnp(:), sicst(:)
        real, intent(in) :: tpar(:), spar(:)
        real :: new_t, new_s
        logical :: new_bad, old_bad

        call d27_read_env()
        if (.not. d27_armed) return
        if (d27_reported) return
        new_t = tpar(6)
        new_s = spar(6)
        new_bad = (new_t /= new_t .or. new_s /= new_s .or. &
                   abs(new_t) > huge(1.0)*0.5 .or. abs(new_s) > huge(1.0)*0.5)
        if (.not. new_bad) return
        d27_reported = .true.
        old_bad = (old_t /= old_t .or. old_s /= old_s .or. &
                   abs(old_t) > huge(1.0)*0.5 .or. abs(old_s) > huge(1.0)*0.5)
        if (old_bad) then
            print *, 'D27_INHERITED_FIRST_SEEN day=', nday, 'i=', i, 'j=', j, 'k=', k, 'site=', site
        else
            print *, 'D27_PATIENT_ZERO day=', nday, 'i=', i, 'j=', j, 'k=', k, 'site=', site
        end if
        print *, '  old_tpar6=', old_t, 'old_spar6=', old_s
        print *, '  new_tpar6=', new_t, 'new_spar6=', new_s
        print *, '  anp(k)=', anp(k), 'hicp(k)=', hicp(k), 'hsnp(k)=', hsnp(k), 'sicst(k)=', sicst(k)
        print *, '  anp=', anp
        print *, '  tpar=', tpar
        print *, '  spar=', spar
    end subroutine d27_poison_check

end module stage114_d27_trace
