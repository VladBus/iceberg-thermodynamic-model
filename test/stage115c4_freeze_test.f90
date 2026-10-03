! ==============================================================================
! Тест: stage115c4_icefreeze — snapshot/restore логика (Stage 11.5C.4).
! Проверяет БЕЗ модели: snap на substep 1, restore на substep 2+ держит
! значения; счётчик субстепов; canary-repair при порче mode.
! Env: STAGE115C4_FREEZE=UV. Ошибка → stop 1.
! ПРЕДУПРЕЖДЕНИЕ: пишет seed_ice_state.csv в CWD (побочный продукт).
! ==============================================================================
program stage115c4_freeze_test
    use param
    use stage115c4_icefreeze
    implicit none

    integer :: n_errors, n_checks

    n_errors = 0
    n_checks = 0

    call s115c4_init()
    ! Без env (батарея fpm test): режим OFF — проверяем no-op и PASS.
    ! С STAGE115C4_FREEZE=UV: полные проверки freeze-логики.
    if (t115c4_mode .eq. 0) then
        print *, 'INFO: no env (OFF mode) — checking no-op behavior'
        u(:, :) = 1.0
        call s115c4_gate_entry(1, 1)
        call s115c4_gate_entry(2, 1)
        n_checks = n_checks + 1
        if (abs(u(10, 10) - 1.0) .gt. 1e-9) then
            print *, 'FAIL: OFF mode modified state'
            n_errors = n_errors + 1
        else
            print *, 'PASS: OFF mode is no-op'
        end if
        n_checks = n_checks + 1
        if (t115c4_substep .ne. 0) then
            print *, 'FAIL: OFF mode counted substeps'
            n_errors = n_errors + 1
        else
            print *, 'PASS: OFF mode does not count'
        end if
        print '(A,I0,A,I0,A)', 'CHECKS: ', n_checks, ', ERRORS: ', n_errors
        if (n_errors .ne. 0) stop 1
        print *, 'SUCCESS: stage115c4 OFF/no-op validated (set STAGE115C4_FREEZE=UV for full checks)!'
        stop 0
    end if

    n_checks = n_checks + 1
    if (t115c4_mode .ne. 1) then
        print *, 'FAIL: mode not UV(1), got', t115c4_mode
        n_errors = n_errors + 1
    else
        print *, 'PASS: mode=UV'
    end if

    ! substep 1: snap u=1.0
    u(:, :) = 1.0
    hices(:, :) = 0.5
    call s115c4_gate_entry(1, 1)
    ! "evolve": u=2.0
    u(:, :) = 2.0
    hices(:, :) = 0.9
    ! substep 2: restore → u must be 1.0 (UV mode); hices NOT frozen → 0.9
    call s115c4_gate_entry(2, 1)

    n_checks = n_checks + 1
    if (abs(u(10, 10) - 1.0) .gt. 1e-9) then
        print *, 'FAIL: u not restored, got', u(10, 10)
        n_errors = n_errors + 1
    else
        print *, 'PASS: u restored to snapshot'
    end if

    n_checks = n_checks + 1
    if (abs(hices(10, 10) - 0.9) .gt. 1e-9) then
        print *, 'FAIL: hices wrongly frozen, got', hices(10, 10)
        n_errors = n_errors + 1
    else
        print *, 'PASS: hices (not in UV set) evolves'
    end if

    n_checks = n_checks + 1
    if (t115c4_substep .ne. 2) then
        print *, 'FAIL: substep counter =', t115c4_substep
        n_errors = n_errors + 1
    else
        print *, 'PASS: substep counter=2'
    end if

    ! Rollover: gate(24) restores first (u→1.0), then iii=1 new day → substep
    ! 1 → snap (u stays 1.0). Correct expectation: sub=1 AND u=1.0.
    u(:, :) = 7.0
    call s115c4_gate_entry(24, 1)   ! substep 3 → restore → u back to 1.0
    n_checks = n_checks + 1
    if (abs(u(10, 10) - 1.0) .gt. 1e-9) then
        print *, 'FAIL: pre-rollover restore wrong, u=', u(10, 10)
        n_errors = n_errors + 1
    else
        print *, 'PASS: pre-rollover restore'
    end if
    call s115c4_gate_entry(1, 2)    ! new day → substep 1 → snap (u stays 1.0)
    n_checks = n_checks + 1
    if (t115c4_substep .ne. 1 .or. abs(u(10, 10) - 1.0) .gt. 1e-9) then
        print *, 'FAIL: rollover broken, sub=', t115c4_substep, ' u=', u(10, 10)
        n_errors = n_errors + 1
    else
        print *, 'PASS: day rollover re-snaps'
    end if

    ! Canary: corrupt mode → gate_entry must repair via env re-read.
    ! Snapshot is 1.0 (from rollover snap) → after repair+restore u=1.0.
    t115c4_mode = 99
    u(:, :) = 3.0
    call s115c4_gate_entry(2, 2)   ! repair → mode=1 → restore → u back to 1.0
    n_checks = n_checks + 1
    if (t115c4_mode .ne. 1) then
        print *, 'FAIL: canary repair did not restore mode, got', t115c4_mode
        n_errors = n_errors + 1
    else if (abs(u(10, 10) - 1.0) .gt. 1e-9) then
        print *, 'FAIL: post-repair restore wrong, u=', u(10, 10)
        n_errors = n_errors + 1
    else
        print *, 'PASS: canary repair re-engages freeze'
    end if

    print '(A,I0,A,I0,A)', 'CHECKS: ', n_checks, ', ERRORS: ', n_errors
    if (n_errors .ne. 0) stop 1
    print *, 'SUCCESS: stage115c4 freeze logic validated!'
end program stage115c4_freeze_test
