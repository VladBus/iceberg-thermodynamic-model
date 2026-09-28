! ==============================================================================
! Модуль: stage114_d29_trace (Stage 11.4-D29)
! Назначение: Внутридинамический forensic-снапшот первого NaN/Inf в блоке
!   динамики льда для ячеек (2,96),(3,96) в день 1, iii=2.
!   Три точки: guardA (hht+hices+вердикт guard), guardB (a3+ans+вердикт),
!   solve (все промежуточные решателя + итог u/v).
!   Печать ТОЛЬКО при наличии невалидного значения; защёлка на точку/ячейку
!   (макс. 6 блоков). За воротами env STAGE114_D29_TRACE (default OFF).
! Физика: не меняет ничего — только чтение + print; при выключенном флаге
!   вызовы дополнительно закрыты целочисленным пре-гардом в main
!   (накладные расходы пренебрежимы); результаты бит-идентичны.
!   NO guards, NO clamps, NO изменений уравнений/условий guard.
! ==============================================================================

module stage114_d29_trace
    implicit none
    logical, save :: d29_armed = .false.
    logical, save :: d29_env_read = .false.
    logical, save :: d29_done(2, 3) = .false.

contains

    subroutine d29_read_env()
        character(len=256) :: env_str
        if (.not. d29_env_read) then
            call get_environment_variable('STAGE114_D29_TRACE', env_str)
            if (len_trim(env_str) .gt. 0 .and. (env_str .eq. 'true' .or. env_str .eq. '1')) then
                d29_armed = .true.
            end if
            d29_env_read = .true.
        end if
    end subroutine d29_read_env

    logical function d29_bad(x)
        real, intent(in) :: x
        d29_bad = (x /= x .or. abs(x) > huge(1.0)*0.5)
    end function d29_bad

    ! Индекс ячейки: 1=(2,96), 2=(3,96); 0 = не отслеживается.
    integer function d29_cell(i, j)
        integer, intent(in) :: i, j
        if (i .eq. 2 .and. j .eq. 96) then
            d29_cell = 1
        else if (i .eq. 3 .and. j .eq. 96) then
            d29_cell = 2
        else
            d29_cell = 0
        end if
    end function d29_cell

    subroutine d29_guardA(nday1, iii, jjj, i, j, hc1, hc2, hc3, hc4, hht)
        integer, intent(in) :: nday1, iii, jjj, i, j
        real, intent(in) :: hc1, hc2, hc3, hc4, hht
        integer :: c
        logical :: g1
        call d29_read_env()
        if (.not. d29_armed) return
        if (nday1 .ne. 1 .or. iii .ne. 2) return
        c = d29_cell(i, j)
        if (c .eq. 0 .or. d29_done(c, 1)) return
        if (.not. (d29_bad(hc1) .or. d29_bad(hc2) .or. d29_bad(hc3) .or. &
                   d29_bad(hc4) .or. d29_bad(hht))) return
        d29_done(c, 1) = .true.
        g1 = (hht .lt. 0.01)
        print *, 'D29_GUARDA day1 iii=2 jjj=', jjj, 'i=', i, 'j=', j
        print *, '  hices=', hc1, hc2, hc3, hc4, ' hht=', hht, ' guard(hht<0.01)=', g1
    end subroutine d29_guardA

    subroutine d29_guardB(nday1, iii, jjj, i, j, an1, an2, an3, an4, a3)
        integer, intent(in) :: nday1, iii, jjj, i, j
        real, intent(in) :: an1, an2, an3, an4, a3
        integer :: c
        logical :: g2
        call d29_read_env()
        if (.not. d29_armed) return
        if (nday1 .ne. 1 .or. iii .ne. 2) return
        c = d29_cell(i, j)
        if (c .eq. 0 .or. d29_done(c, 2)) return
        if (.not. (d29_bad(an1) .or. d29_bad(an2) .or. d29_bad(an3) .or. &
                   d29_bad(an4) .or. d29_bad(a3))) return
        d29_done(c, 2) = .true.
        g2 = (a3 .gt. 2.0)
        print *, 'D29_GUARDB day1 iii=2 jjj=', jjj, 'i=', i, 'j=', j
        print *, '  ans=', an1, an2, an3, an4, ' a3=', a3, ' guard(a3>2.0)=', g2
    end subroutine d29_guardB

    subroutine d29_solve(nday1, iii, jjj, i, j, uij, vij, wu, wv, txv, tyv, fkuv, &
                         ym1, ym2, ym3, ym4, &
                         sxx1, sxx2, sxx3, sxx4, syy1, syy2, syy3, syy4, &
                         sxy1, sxy2, sxy3, sxy4, fixv, fiyv, av, bv, b3v, &
                         fa1, fb1, fa2, fb2, aav, unew, vnew)
        integer, intent(in) :: nday1, iii, jjj, i, j
        real, intent(in) :: uij, vij, wu, wv, txv, tyv, fkuv
        real, intent(in) :: ym1, ym2, ym3, ym4
        real, intent(in) :: sxx1, sxx2, sxx3, sxx4, syy1, syy2, syy3, syy4
        real, intent(in) :: sxy1, sxy2, sxy3, sxy4, fixv, fiyv, av, bv, b3v
        real, intent(in) :: fa1, fb1, fa2, fb2, aav, unew, vnew
        integer :: c
        call d29_read_env()
        if (.not. d29_armed) return
        if (nday1 .ne. 1 .or. iii .ne. 2) return
        c = d29_cell(i, j)
        if (c .eq. 0 .or. d29_done(c, 3)) return
        if (.not. (d29_bad(uij) .or. d29_bad(vij) .or. d29_bad(wu) .or. d29_bad(wv) .or. &
                   d29_bad(txv) .or. d29_bad(tyv) .or. d29_bad(fkuv) .or. &
                   d29_bad(ym1) .or. d29_bad(ym2) .or. d29_bad(ym3) .or. d29_bad(ym4) .or. &
                   d29_bad(sxx1) .or. d29_bad(sxx2) .or. d29_bad(sxx3) .or. d29_bad(sxx4) .or. &
                   d29_bad(syy1) .or. d29_bad(syy2) .or. d29_bad(syy3) .or. d29_bad(syy4) .or. &
                   d29_bad(sxy1) .or. d29_bad(sxy2) .or. d29_bad(sxy3) .or. d29_bad(sxy4) .or. &
                   d29_bad(fixv) .or. d29_bad(fiyv) .or. d29_bad(av) .or. d29_bad(bv) .or. &
                   d29_bad(b3v) .or. d29_bad(fa1) .or. d29_bad(fb1) .or. d29_bad(fa2) .or. &
                   d29_bad(fb2) .or. d29_bad(aav) .or. d29_bad(unew) .or. d29_bad(vnew))) return
        d29_done(c, 3) = .true.
        print *, 'D29_SOLVE day1 iii=2 jjj=', jjj, 'i=', i, 'j=', j
        print *, '  uij=', uij, 'vij=', vij, ' wu=', wu, 'wv=', wv
        print *, '  tx=', txv, 'ty=', tyv, 'fku=', fkuv
        print *, '  ym2=', ym1, ym2, ym3, ym4
        print *, '  sxx=', sxx1, sxx2, sxx3, sxx4
        print *, '  syy=', syy1, syy2, syy3, syy4
        print *, '  sxy=', sxy1, sxy2, sxy3, sxy4
        print *, '  fix=', fixv, 'fiy=', fiyv, ' a=', av, 'b=', bv, 'b3=', b3v
        print *, '  fa1=', fa1, 'fb1=', fb1, 'fa2=', fa2, 'fb2=', fb2, 'aa=', aav
        print *, '  unew=', unew, 'vnew=', vnew
    end subroutine d29_solve

end module stage114_d29_trace
