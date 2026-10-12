! ==============================================================================
! Тестовая программа: ground-truth дамп сетки из coup1() (Stage 11.7B.1).
! Вызывает production coup1() и пишет массивы в build/grid_dump_*.dat
! (build/ gitignored; корень остаётся чистым — 11.7B.2).
! внутри строки значения i=1..is1; real — E25.17 для точного round-trip).
! Плюс регрессионные якоря сетки (wet cols, sum kt1, map1/kk1 wet counts).
! Файлы *.dat игнорируются git (см. .gitignore) — артефакты для
! python/tests/test_grid_bathymetry_nc.py (сравнение builder vs Fortran).
! Порядок запуска: fpm test grid_dump && python test_grid_bathymetry_nc.py.
! Физику НЕ меняет (только вызывает coup1 и пишет файлы).
! Ошибка якорей → stop 1.
! ==============================================================================

program grid_dump
    use param
    use grid_coupling, only: coup1
    implicit none

    integer :: i, j, n_errors
    integer :: nwet, sumkt, nmap1, nkk1
    logical :: bdir_exists, fexists

    ! CI-конвенция репозитория (как ocean_init_test): без входных файлов —
    ! SKIP (stop 0), НЕ failure. data/* gitignored, в CI их нет.
    inquire (file='KOORD.DAT', exist=fexists)
    if (.not. fexists) then
        print *, "SKIP: KOORD.DAT not present (gitignored; real-grid inputs needed)"
        stop 0
    end if
    inquire (file='hhh.bar', exist=fexists)
    if (.not. fexists) then
        print *, "SKIP: hhh.bar not present (gitignored; real-grid inputs needed)"
        stop 0
    end if

    ! Артефакты — в build/ (gitignored), НЕ в корень (11.7B.2).
    inquire (file='build', exist=bdir_exists)
    if (.not. bdir_exists) call execute_command_line('mkdir -p build')

    call coup1()

    open (11, file='build/grid_dump_kt1.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, *) (kt1(i, j), i=1, is1)
    end do
    close (11)

    open (11, file='build/grid_dump_ht.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, '(133(E25.17,1X))') (ht(i, j), i=1, is1)
    end do
    close (11)

    open (11, file='build/grid_dump_map1.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, '(133(E25.17,1X))') (map1(i, j), i=1, is1)
    end do
    close (11)

    open (11, file='build/grid_dump_kk1.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, *) (kk1(i, j), i=1, is1)
    end do
    close (11)

    open (11, file='build/grid_dump_fi.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, '(133(E25.17,1X))') (fi(i, j), i=1, is1)
    end do
    close (11)

    open (11, file='build/grid_dump_dl.dat', status='replace', action='write')
    write (11, *) is1, js1
    do j = 1, js1
        write (11, '(133(E25.17,1X))') (dl(i, j), i=1, is1)
    end do
    close (11)

    ! Регрессионные якоря сетки (валидированы ocean_init_test + EN4):
    nwet = 0
    sumkt = 0
    nmap1 = 0
    nkk1 = 0
    do j = 1, js1
        do i = 1, is1
            if (kt1(i, j) .gt. 0) then
                nwet = nwet + 1
                sumkt = sumkt + kt1(i, j)
            end if
            if (abs(map1(i, j) - 8888.0) .gt. 1e-8) nmap1 = nmap1 + 1
            if (kk1(i, j) .gt. 0) nkk1 = nkk1 + 1
        end do
    end do
    print *, 'grid_dump: wet cols=', nwet, ' sumkt=', sumkt, &
             ' map1wet=', nmap1, ' kk1pos=', nkk1

    n_errors = 0
    if (nwet .ne. 11067) then
        print *, 'FAIL wet cols: ', nwet, ' expected 11067'
        n_errors = n_errors + 1
    end if
    if (sumkt .ne. 143422) then
        print *, 'FAIL sumkt: ', sumkt, ' expected 143422'
        n_errors = n_errors + 1
    end if
    if (n_errors .gt. 0) then
        print *, 'GRID DUMP ANCHORS FAILED'
        stop 1
    else
        print *, 'GRID DUMP OK'
        stop 0
    end if
end program grid_dump
