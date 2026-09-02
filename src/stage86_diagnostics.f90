! ==============================================================================
! Модуль: stage86_diagnostics
! Назначение: Диагностика Stage 8.6 — отслеживание первой дивергенции
!             в цепочке термодинамика-динамика.
! Вызывается на каждом этапе временного шага для захвата:
!   U_max, V_max, W_max, NaN fraction, T/S/RO min/max, KE, momentum
! ==============================================================================

module stage86_diagnostics
    use param
    implicit none

    ! --- Режим диагностики ---
    integer, parameter :: DIAG_OFF = 0
    integer, parameter :: DIAG_BASIC = 1
    integer, parameter :: DIAG_VERBOSE = 2
    integer :: diag_level = DIAG_OFF

    ! --- Инициализация из переменной окружения ---
    logical :: diag_initialized = .false.

contains

    ! ==========================================================================
    ! Инициализация уровня диагностики
    ! ==========================================================================
    subroutine init_stage86_diagnostics()
        character(len=64) :: env_str
        if (diag_initialized) return
        call get_environment_variable('ICEBERG_STAGE86_DIAG', env_str)
        if (len_trim(env_str) .gt. 0) then
            select case (trim(adjustl(env_str)))
            case ('basic')
                diag_level = DIAG_BASIC
            case ('verbose')
                diag_level = DIAG_VERBOSE
            case default
                diag_level = DIAG_OFF
            end select
        end if
        diag_initialized = .true.
        if (diag_level .gt. DIAG_OFF) then
            print *, ">>> Stage 8.6 diagnostics ENABLED: level = ", diag_level
        end if
    end subroutine init_stage86_diagnostics

    ! ==========================================================================
    ! Захват снимка состояния 3D полей
    ! ==========================================================================
    subroutine capture_state(tag, kkk, iii, u_arr, v_arr, w_arr, t_arr, s_arr, ro_arr)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: kkk, iii
        real, intent(in) :: u_arr(:, :, :), v_arr(:, :, :), w_arr(:, :, :)
        real, intent(in) :: t_arr(:, :, :), s_arr(:, :, :), ro_arr(:, :, :)

        integer :: i, j, k, ki, n_wet, n_nan_u, n_nan_v, n_nan_w
        integer :: n_nan_t, n_nan_s, n_nan_ro
        real :: u_max, v_max, w_max, u_min, v_min, w_min
        real :: t_max, t_min, s_max, s_min, ro_max, ro_min
        real :: ke, mom_x, mom_y
        real :: speed_max

        ! Ensure initialization happens first
        call init_stage86_diagnostics()
        if (diag_level .eq. DIAG_OFF) return

        u_max = -huge(0.0); v_max = -huge(0.0); w_max = -huge(0.0)
        u_min = huge(0.0);  v_min = huge(0.0);  w_min = huge(0.0)
        t_max = -huge(0.0); t_min = huge(0.0)
        s_max = -huge(0.0); s_min = huge(0.0)
        ro_max = -huge(0.0); ro_min = huge(0.0)
        speed_max = -huge(0.0)
        ke = 0.0; mom_x = 0.0; mom_y = 0.0
        n_wet = 0; n_nan_u = 0; n_nan_v = 0; n_nan_w = 0
        n_nan_t = 0; n_nan_s = 0; n_nan_ro = 0

        do j = 2, JS
            do i = 2, IS
                ki = KT1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    n_wet = n_wet + 1

                    ! U
                    if (u_arr(i, j, k) .ne. u_arr(i, j, k)) then
                        n_nan_u = n_nan_u + 1
                    else
                        u_max = max(u_max, u_arr(i, j, k))
                        u_min = min(u_min, u_arr(i, j, k))
                        mom_x = mom_x + u_arr(i, j, k)
                        ke = ke + u_arr(i, j, k)**2
                    end if

                    ! V
                    if (v_arr(i, j, k) .ne. v_arr(i, j, k)) then
                        n_nan_v = n_nan_v + 1
                    else
                        v_max = max(v_max, v_arr(i, j, k))
                        v_min = min(v_min, v_arr(i, j, k))
                        mom_y = mom_y + v_arr(i, j, k)
                        ke = ke + v_arr(i, j, k)**2
                    end if

                    ! W
                    if (w_arr(i, j, k) .ne. w_arr(i, j, k)) then
                        n_nan_w = n_nan_w + 1
                    else
                        w_max = max(w_max, w_arr(i, j, k))
                        w_min = min(w_min, w_arr(i, j, k))
                    end if

                    ! T
                    if (t_arr(i, j, k) .ne. t_arr(i, j, k)) then
                        n_nan_t = n_nan_t + 1
                    else
                        t_max = max(t_max, t_arr(i, j, k))
                        t_min = min(t_min, t_arr(i, j, k))
                    end if

                    ! S
                    if (s_arr(i, j, k) .ne. s_arr(i, j, k)) then
                        n_nan_s = n_nan_s + 1
                    else
                        s_max = max(s_max, s_arr(i, j, k))
                        s_min = min(s_min, s_arr(i, j, k))
                    end if

                    ! RO
                    if (ro_arr(i, j, k) .ne. ro_arr(i, j, k)) then
                        n_nan_ro = n_nan_ro + 1
                    else
                        ro_max = max(ro_max, ro_arr(i, j, k))
                        ro_min = min(ro_min, ro_arr(i, j, k))
                    end if

                    ! Speed
                    if (u_arr(i, j, k) .eq. u_arr(i, j, k) .and. &
                        v_arr(i, j, k) .eq. v_arr(i, j, k)) then
                        speed_max = max(speed_max, sqrt(u_arr(i, j, k)**2 + v_arr(i, j, k)**2))
                    end if
                end do
            end do
        end do

        if (n_wet .gt. 0) then
            ke = 0.5 * ke / real(n_wet)
        end if

        print *, "STAGE86 [" // trim(tag) // "] d=", kkk, " III=", iii, &
            " n_wet=", n_wet, &
            " U=[", u_min/100.0, ",", u_max/100.0, "] m/s", &
            " V=[", v_min/100.0, ",", v_max/100.0, "] m/s", &
            " W=[", w_min/100.0, ",", w_max/100.0, "] cm/s", &
            " speed_max=", speed_max/100.0, " m/s", &
            " NaN_U=", n_nan_u, " NaN_V=", n_nan_v, " NaN_W=", n_nan_w, &
            " NaN_T=", n_nan_t, " NaN_S=", n_nan_s, " NaN_RO=", n_nan_ro, &
            " T=[", t_min, ",", t_max, "] C", &
            " S=[", s_min, ",", s_max, "]", &
            " RO=[", ro_min, ",", ro_max, "] g/cm3", &
            " KE=", ke, " mom=[", mom_x/100.0, ",", mom_y/100.0, "] m/s"

        ! Detailed verbose output
        if (diag_level .eq. DIAG_VERBOSE .and. n_wet .gt. 0) then
            print *, "  NaN fractions: U=", real(n_nan_u)/real(n_wet)*100.0, &
                "% V=", real(n_nan_v)/real(n_wet)*100.0, "% W=", real(n_nan_w)/real(n_wet)*100.0, "%"
            print *, "  T NaN=", real(n_nan_t)/real(n_wet)*100.0, "% S NaN=", &
                real(n_nan_s)/real(n_wet)*100.0, "% RO NaN=", real(n_nan_ro)/real(n_wet)*100.0, "%"
        end if
    end subroutine capture_state

    ! ==========================================================================
    ! Захват снимка только 3D скоростей (для переходов между блоками)
    ! ==========================================================================
    subroutine capture_velocity_state(tag, kkk, iii, u_arr, v_arr)
        character(len=*), intent(in) :: tag
        integer, intent(in) :: kkk, iii
        real, intent(in) :: u_arr(:, :, :), v_arr(:, :, :)

        integer :: i, j, k, ki, n_wet, n_nan_u, n_nan_v
        real :: u_max, v_max, u_min, v_min
        real :: speed_max, ke, mom_x, mom_y

        call init_stage86_diagnostics()
        if (diag_level .eq. DIAG_OFF) return

        u_max = -huge(0.0); v_max = -huge(0.0)
        u_min = huge(0.0);  v_min = huge(0.0)
        speed_max = -huge(0.0)
        ke = 0.0; mom_x = 0.0; mom_y = 0.0
        n_wet = 0; n_nan_u = 0; n_nan_v = 0

        do j = 2, JS
            do i = 2, IS
                ki = KT1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    n_wet = n_wet + 1

                    if (u_arr(i, j, k) .ne. u_arr(i, j, k)) then
                        n_nan_u = n_nan_u + 1
                    else
                        u_max = max(u_max, u_arr(i, j, k))
                        u_min = min(u_min, u_arr(i, j, k))
                        mom_x = mom_x + u_arr(i, j, k)
                        ke = ke + u_arr(i, j, k)**2
                    end if

                    if (v_arr(i, j, k) .ne. v_arr(i, j, k)) then
                        n_nan_v = n_nan_v + 1
                    else
                        v_max = max(v_max, v_arr(i, j, k))
                        v_min = min(v_min, v_arr(i, j, k))
                        mom_y = mom_y + v_arr(i, j, k)
                        ke = ke + v_arr(i, j, k)**2
                    end if

                    if (u_arr(i, j, k) .eq. u_arr(i, j, k) .and. &
                        v_arr(i, j, k) .eq. v_arr(i, j, k)) then
                        speed_max = max(speed_max, sqrt(u_arr(i, j, k)**2 + v_arr(i, j, k)**2))
                    end if
                end do
            end do
        end do

        if (n_wet .gt. 0) ke = 0.5 * ke / real(n_wet)

        print *, "STAGE86_VEL [" // trim(tag) // "] d=", kkk, " III=", iii, &
            " n_wet=", n_wet, &
            " U=[", u_min/100.0, ",", u_max/100.0, "] m/s", &
            " V=[", v_min/100.0, ",", v_max/100.0, "] m/s", &
            " speed_max=", speed_max/100.0, " m/s", &
            " NaN_U=", n_nan_u, " NaN_V=", n_nan_v, &
            " KE=", ke, " mom=[", mom_x/100.0, ",", mom_y/100.0, "] m/s"
    end subroutine capture_velocity_state

end module stage86_diagnostics