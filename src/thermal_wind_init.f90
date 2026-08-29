! ==============================================================================
! Модуль: thermal_wind_init (Stage 7.9)
! Назначение: Инициализация 3D-скоростей u2/v2 и SSH (y2) из термодинамического
!             баланса (thermal wind) с заданным reference level.
! Физика: Использует thermal-wind relation:
!           f * ∂v/∂z = (g/ρ₀) · ∂ρ/∂x
!           f * ∂u/∂z = -(g/ρ₀) · ∂ρ/∂y
!         интегрированную от reference level (k_ref) вверх/вниз.
!         SSH (y2) инициализируется из dynamic height:
!           D(x,y) = -∫_{z_ref}^{0} (ρ'/ρ₀) dz  [m]
!           y2 = D - mean(D)
!
! Режимы (переменная окружения ICEBERG_OCEAN_VELOCITY_INIT):
!   zero          — u=v=0
!   synthetic     — canonical drift 0.20/0.10 cm/s
!   reference_level — thermal wind с u=v=0 на k_ref (по умолчанию 600m)
!   realistic_ref  — thermal wind с u_ref, v_ref на k_ref (из env vars)
!   dynamic_height — reference_level + SSH из dynamic height
!
! Единицы: U/V [см/с], RO [г/см³], DZ [см], SSH [см]
! Сетка: U-точки (i,j), B-сетка Аракавы. Y инвертирована (j=1 — север).
! ==============================================================================

module thermal_wind_init
    use param
    use iso_fortran_env, only: real64
    implicit none

    ! --- Режимы инициализации ---
    integer, parameter :: INIT_ZERO = 0
    integer, parameter :: INIT_SYNTHETIC = 1
    integer, parameter :: INIT_REFERENCE_LEVEL = 2
    integer, parameter :: INIT_REALISTIC_REF = 3
    integer, parameter :: INIT_DYNAMIC_HEIGHT = 4

    ! Глубины reference level [см]
    real, parameter :: REF_SURFACE_CM = 0.0
    real, parameter :: REF_100M_CM = 10000.0
    real, parameter :: REF_200M_CM = 20000.0
    real, parameter :: REF_400M_CM = 40000.0
    real, parameter :: REF_600M_CM = 60000.0

contains

    ! ==========================================================================
    ! Главная подпрограмма: инициализация 3D-скоростей и SSH
    ! ==========================================================================
    subroutine init_thermal_wind()
        integer :: init_mode
        real :: ref_depth_cm
        real :: u_ref_val, v_ref_val
        logical :: use_dynamic_height
        character(len=64) :: env_str
        integer :: i, j, k, ki, ref_level_k
        real :: ref_depth_target

        print *, ">>> Initializing thermal-wind balanced velocity (Stage 7.9)..."

        ! --- Определение режима из переменной окружения ---
        call get_environment_variable('ICEBERG_OCEAN_VELOCITY_INIT', env_str)
        if (len_trim(env_str) .eq. 0) env_str = 'reference_level'

        select case (trim(adjustl(env_str)))
        case ('zero')
            init_mode = INIT_ZERO
        case ('synthetic')
            init_mode = INIT_SYNTHETIC
        case ('reference_level')
            init_mode = INIT_REFERENCE_LEVEL
            ref_depth_cm = REF_600M_CM
            u_ref_val = 0.0
            v_ref_val = 0.0
            use_dynamic_height = .false.
        case ('reference_level_100m')
            init_mode = INIT_REFERENCE_LEVEL
            ref_depth_cm = REF_100M_CM
            u_ref_val = 0.0
            v_ref_val = 0.0
            use_dynamic_height = .false.
        case ('reference_level_200m')
            init_mode = INIT_REFERENCE_LEVEL
            ref_depth_cm = REF_200M_CM
            u_ref_val = 0.0
            v_ref_val = 0.0
            use_dynamic_height = .false.
        case ('reference_level_400m')
            init_mode = INIT_REFERENCE_LEVEL
            ref_depth_cm = REF_400M_CM
            u_ref_val = 0.0
            v_ref_val = 0.0
            use_dynamic_height = .false.
        case ('realistic_ref')
            init_mode = INIT_REALISTIC_REF
            ref_depth_cm = REF_600M_CM
            call get_environment_variable('ICEBERG_OCEAN_U_REF', env_str)
            if (len_trim(env_str) .gt. 0) read (env_str, *) u_ref_val
            call get_environment_variable('ICEBERG_OCEAN_V_REF', env_str)
            if (len_trim(env_str) .gt. 0) read (env_str, *) v_ref_val
            use_dynamic_height = .false.
        case ('dynamic_height')
            init_mode = INIT_DYNAMIC_HEIGHT
            ref_depth_cm = REF_600M_CM
            u_ref_val = 0.0
            v_ref_val = 0.0
            use_dynamic_height = .true.
        case default
            print *, "WARNING: Unknown ICEBERG_OCEAN_VELOCITY_INIT = ", trim(env_str)
            print *, "         Falling back to synthetic drift"
            init_mode = INIT_SYNTHETIC
        end select

        ! --- Обнуление полей ---
        u2 = 0.0
        v2 = 0.0
        u1 = 0.0
        v1 = 0.0
        y2 = 0.0

        select case (init_mode)
        case (INIT_ZERO)
            print *, ">>> Zero velocity initialization"

        case (INIT_SYNTHETIC)
            call init_synthetic_drift()
            return

        case (INIT_REFERENCE_LEVEL, INIT_REALISTIC_REF, INIT_DYNAMIC_HEIGHT)
            ! Определение k_ref по глубине
            ref_level_k = 18
            do k = 1, 18
                if (z(k) .gt. ref_depth_cm) then
                    ref_level_k = k - 1
                    exit
                end if
            end do
            if (ref_level_k .lt. 1) ref_level_k = 1

            print *, ">>> Thermal-wind initialization with reference level k = ", ref_level_k, " (", ref_depth_cm/100.0, " m)"
            if (init_mode .eq. INIT_REALISTIC_REF) then
         print *, "    Reference velocity: u_ref = ", u_ref_val, " m/s, v_ref = ", v_ref_val, " m/s"
            end if
            if (use_dynamic_height) then
                print *, "    Dynamic height SSH initialization enabled"
            end if

            ! Вычисление thermal wind с reference level
            call compute_thermal_wind(ref_level_k, u_ref_val, v_ref_val)

            ! Инициализация SSH из dynamic height
            if (use_dynamic_height) then
                call compute_dynamic_height_ssh()
            end if

            ! Инициализация баротропных потоков UP2/VP2
            call init_barotropic_transports()

        end select

        ! Инициализация u1/v1 = u2/v2
        u1 = u2
        v1 = v2

        print *, ">>> Thermal-wind initialization complete. Mode: ", trim(env_str)
    end subroutine init_thermal_wind

    ! ==========================================================================
    ! Вычисление thermal wind с заданным reference level
    ! ==========================================================================
    subroutine compute_thermal_wind(ref_level_k, u_ref, v_ref)
        integer, intent(in) :: ref_level_k
        real, intent(in) :: u_ref, v_ref  ! [м/с]

        integer :: i, j, k, ki, ref_k
        real :: f_val
        real, dimension(18) :: dzs
        real :: integral_x, integral_y
        real :: g_si, rho0_si, f_safe, c8, g_m
        integer :: k_start, k_end, step

        g_si = 9.81
        rho0_si = 1025.0  ! кг/м³
        c8 = 0.25/(1389000.0)  ! 1/cm
        g_m = 9.81
        ref_k = ref_level_k  ! 1-based

        ! --- Цикл по U-точкам (i=2..IS, j=2..JS) ---
        do j = 2, JS
            do i = 2, IS
                ki = KK1(i, j)
                if (ki .eq. 0) cycle  ! суша

                f_val = FKU(i, j)
                if (abs(f_val) .lt. 1e-12) then
                    ! У экватора — ставим reference velocity
                    do k = 1, ki
                        U2(i, j, k) = u_ref*100.0  ! см/с
                        V2(i, j, k) = v_ref*100.0
                    end do
                    do k = ki + 1, KS
                        U2(i, j, k) = 0.0
                        V2(i, j, k) = 0.0
                    end do
                    cycle
                end if

                f_safe = f_val

                ! --- Накопленные интегралы от reference level ---
                ! Сначала вверх от reference level (k < ref_k)
                integral_x = 0.0
                integral_y = 0.0
                do k = ref_k - 1, 1, -1
                    if (k .gt. ki) cycle
                    ! grad_x, grad_y на U-точке (4-точечный stencil как в Block 200)
                    integral_x = integral_x + C8*Dz(k)* &
                             (RO(i - 1, j, k) + RO(i, j, k) - RO(i - 1, j - 1, k) - RO(i, j - 1, k))
                    integral_y = integral_y + C8*Dz(k)* &
                             (RO(i - 1, j - 1, k) + RO(i - 1, j, k) - RO(i, j - 1, k) - RO(i, j, k))

                    f_safe = FKU(i, j)
                    if (abs(f_safe) .gt. 1e-12) then
                        V2(i, j, k) = v_ref*100.0 - (g_m/(RHO0_SI*f_safe))*integral_x*100.0
                        U2(i, j, k) = u_ref*100.0 + (g_m/(RHO0_SI*f_safe))*integral_y*100.0
                    else
                        U2(i, j, k) = u_ref*100.0
                        V2(i, j, k) = v_ref*100.0
                    end if
                end do

                ! На уровне reference level
                if (ref_k .le. ki) then
                    U2(i, j, ref_k) = u_ref*100.0
                    V2(i, j, ref_k) = v_ref*100.0
                end if

                ! Вниз от reference level (k > ref_k)
                integral_x = 0.0
                integral_y = 0.0
                do k = ref_k + 1, ki
                    integral_x = integral_x + C8*Dz(k - 1)* &
             (RO(i - 1, j, k - 1) + RO(i, j, k - 1) - RO(i - 1, j - 1, k - 1) - RO(i, j - 1, k - 1))
                    integral_y = integral_y + C8*Dz(k - 1)* &
             (RO(i - 1, j - 1, k - 1) + RO(i - 1, j, k - 1) - RO(i, j - 1, k - 1) - RO(i, j, k - 1))

                    f_safe = FKU(i, j)
                    if (abs(f_safe) .gt. 1e-12) then
                        V2(i, j, k) = v_ref*100.0 + (g_m/(RHO0_SI*f_safe))*integral_x*100.0
                        U2(i, j, k) = u_ref*100.0 - (g_m/(RHO0_SI*f_safe))*integral_y*100.0
                    else
                        U2(i, j, k) = u_ref*100.0
                        V2(i, j, k) = v_ref*100.0
                    end if
                end do

                ! Ниже дна — ноль
                do k = ki + 1, KS
                    U2(i, j, k) = 0.0
                    V2(i, j, k) = 0.0
                end do
            end do
        end do

        ! --- Граничные условия для U2/V2 ---
        call apply_velocity_bc(U2, V2)

        ! Диагностика
        call diagnose_thermal_wind()
    end subroutine compute_thermal_wind

    ! ==========================================================================
    ! Вычисление SSH из dynamic height
    ! ==========================================================================
    subroutine compute_dynamic_height_ssh()
        integer :: i, j, k, ki, n_wet
        real :: D_anomaly
        real, dimension(133, 105) :: D_field
        real :: D_mean

        print *, ">>> Computing dynamic height SSH..."

        ! D(x,y) = -∫_{z_ref}^{0} (ρ'/ρ₀) dz
        ! ρ' = RO [г/см³], ρ₀ = 1.02 г/см³
        D_field = 0.0
        do j = 2, JS
            do i = 2, IS
                ki = KT1(i, j)
                if (ki .eq. 0) cycle

                D_anomaly = 0.0
                do k = 18, 1, -1  ! от дна к поверхности (k=18..1)
                    if (k .gt. KT1(i, j)) cycle
                    D_anomaly = D_anomaly - RO(i, j, k)/1.02*Dz(k)/100.0  ! m
                end do
                D_field(i, j) = D_anomaly
            end do
        end do

        ! Убираем пространственное среднее
        D_mean = 0.0
        n_wet = 0
        do j = 2, JS
            do i = 2, IS
                if (KT1(i, j) .gt. 0 .and. abs(MAP1(i, j) - 8888.0) .gt. 1e-8) then
                    D_mean = D_mean + D_field(i, j)
                    n_wet = n_wet + 1
                end if
            end do
        end do
        if (n_wet .gt. 0) D_mean = D_mean/real(n_wet)

        ! Инициализация y2 (SSH) в см
        Y2 = 0.0
        do j = 2, JS
            do i = 2, IS
                if (KT1(i, j) .gt. 0 .and. abs(MAP1(i, j) - 8888.0) .gt. 1e-8) then
                    Y2(i, j) = (D_field(i, j) - D_mean)*100.0  ! см
                else
                    Y2(i, j) = 0.0
                end if
            end do
        end do

        ! Граничные условия для Y2
        Y2(:, 1) = Y2(:, 2)
        Y2(:, JS1) = Y2(:, JS)
        Y2(1, :) = Y2(2, :)
        Y2(IS1, :) = Y2(IS, :)

        ! Инициализация YM2 = Y2 (для Block 280)
        YM2 = Y2

        print *, ">>> Dynamic height SSH initialized. Mean removed: ", D_mean, " m"
    end subroutine compute_dynamic_height_ssh

    ! ==========================================================================
    ! Инициализация баротропных потоков UP2/VP2 из 3D скоростей
    ! ==========================================================================
    subroutine init_barotropic_transports()
        integer :: i, j, k, ki
        real :: dzz, u_sum, v_sum, hht

        UP2 = 0.0
        VP2 = 0.0

        do j = 2, JS
            do i = 2, IS
                ki = KK1(i, j)
                if (ki .eq. 0) cycle
                hht = MAP1(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle

                u_sum = 0.0
                v_sum = 0.0
                do k = 1, ki
                    if (k .eq. ki) then
                        if (ki .ne. 1) then
                            dzz = MAP1(i, j) - 0.5*(z(ki) + z(ki - 1))
                        else
                            dzz = MAP1(i, j)
                        end if
                    else
                        dzz = dz1(k)
                    end if
                    u_sum = u_sum + U2(i, j, k)*dzz
                    v_sum = v_sum + V2(i, j, k)*dzz
                end do

                UP2(i, j) = u_sum
                VP2(i, j) = v_sum
            end do
        end do

        ! Граничные условия
        UP2(:, 1) = UP2(:, 2)
        UP2(:, JS1) = UP2(:, JS)
        UP2(1, :) = UP2(2, :)
        UP2(IS1, :) = UP2(IS, :)
        VP2(:, 1) = VP2(:, 2)
        VP2(:, JS1) = VP2(:, JS)
        VP2(1, :) = VP2(2, :)
        VP2(IS1, :) = VP2(IS, :)

        UP1 = UP2
        VP1 = VP2

        print *, ">>> Barotropic transports initialized from 3D velocity"
    end subroutine init_barotropic_transports

    ! ==========================================================================
    ! Канонический синтетический дрейф
    ! ==========================================================================
    subroutine init_synthetic_drift()
        integer :: i, j, k
        do k = 1, KS
            do j = 1, JS1
                do i = 1, IS1
                    if (KT1(i, j) .gt. 0 .and. k .le. KT1(i, j)) then
                        U2(i, j, k) = 0.20
                        V2(i, j, k) = 0.10
                    else
                        U2(i, j, k) = 0.0
                        V2(i, j, k) = 0.0
                    end if
                end do
            end do
        end do
        print *, ">>> Synthetic drift: u=0.20, v=0.10 cm/s"
    end subroutine init_synthetic_drift

    ! ==========================================================================
    ! Граничные условия для 3D скоростей
    ! ==========================================================================
    subroutine apply_velocity_bc(u_arr, v_arr)
        real, intent(inout) :: u_arr(:, :, :), v_arr(:, :, :)

        u_arr(:, 1, :) = u_arr(:, 2, :)
        u_arr(:, JS1, :) = u_arr(:, JS, :)
        v_arr(1, :, :) = v_arr(2, :, :)
        v_arr(IS1, :, :) = v_arr(IS, :, :)
        u_arr(1, :, :) = u_arr(2, :, :)
        u_arr(IS1, :, :) = u_arr(IS, :, :)
        v_arr(:, 1, :) = v_arr(:, 2, :)
        v_arr(:, JS1, :) = v_arr(:, JS, :)
    end subroutine apply_velocity_bc

    ! ==========================================================================
    ! Диагностика thermal-wind инициализации
    ! ==========================================================================
    subroutine diagnose_thermal_wind()
        integer :: i, j, k, ki
        real :: u_max, v_max, speed_max

        u_max = -huge(0.0)
        v_max = -huge(0.0)
        speed_max = -huge(0.0)

        do j = 2, JS
            do i = 2, IS
                ki = KK1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    u_max = max(u_max, U2(i, j, k))
                    u_max = max(u_max, -U2(i, j, k))
                    v_max = max(v_max, V2(i, j, k))
                    v_max = max(v_max, -V2(i, j, k))
                    speed_max = max(speed_max, sqrt(U2(i, j, k)**2 + V2(i, j, k)**2))
                end do
            end do
        end do

        print *, '>>> Thermal wind init: U_max=', u_max/100.0, ' V_max=', v_max/100.0, ' speed_max=', speed_max/100.0, ' m/s'
    end subroutine diagnose_thermal_wind

end module thermal_wind_init
