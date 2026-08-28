! ==============================================================================
! Модуль: geostrophic_init (Stage 7.7C)
! Назначение: Инициализация 3D-скоростей u2/v2 из геострофического баланса,
!             вычисленного по полю плотности RO (EN4 реалистичные T/S).
! Физика: Использует ТОЧНУЮ дискретную формулировку Block 200 main.f90:
!           sum_x(k) = C8_LOCAL * Σ_{m=1..k} DZ(m) * ΔRO_x(m)
!           sum_y(k) = C8_LOCAL * Σ_{m=1..k} DZ(m) * ΔRO_y(m)
!         где ΔRO_x = RO(i-1,j) + RO(i,j) - RO(i-1,j-1) - RO(i,j-1)
!               ΔRO_y = RO(i-1,j-1) + RO(i-1,j) - RO(i,j-1) - RO(i,j)
!
!         Геострофический баланс (устойчивое состояние полунеявного Кориолиса):
!           f * V_geo(k) = 2 * C1_LOCAL * sum_x(k)
!           f * U_geo(k) = -2 * C1_LOCAL * sum_y(k)
!
!         Это обеспечивает, что начальные u2/v2 удовлетворяют уравнению импульса
!         без ускорения (кроме вязкости и ветра).
!
! Режимы (через переменную окружения ICEBERG_OCEAN_VELOCITY_INIT):
!   synthetic  — канонический дрейф 0.20/0.10 см/с (по умолчанию)
!   zero       — нулевая скорость
!   geostrophic — полный 3D геострофический профиль (по умолчанию для реалистичного T/S)
!   geostrophic_H50  — интеграция до 50 м
!   geostrophic_H100 — интеграция до 100 м
!   geostrophic_H200 — интеграция до 200 м
!   geostrophic_H400 — интеграция до 400 м
!   baroclinic_only  — только barokлинная составляющая (убрать глубинное среднее)
!
! Единицы: U/V [см/с], RO [г/см³], DZ [см], C1_LOCAL=981, C8_LOCAL=0.25/DX
! Сетка: U-точки (i=2..IS, j=2..JS), B-сетка Аракавы.
! ==============================================================================

module geostrophic_init
    use param
    use iso_fortran_env, only: real64
    implicit none

    ! Типы режимов инициализации
    integer, parameter :: INIT_SYNTHETIC = 0
    integer, parameter :: INIT_ZERO = 1
    integer, parameter :: INIT_GEOSTROPHIC = 2
    integer, parameter :: INIT_GEOSTROPHIC_H50 = 3
    integer, parameter :: INIT_GEOSTROPHIC_H100 = 4
    integer, parameter :: INIT_GEOSTROPHIC_H200 = 5
    integer, parameter :: INIT_GEOSTROPHIC_H400 = 6
    integer, parameter :: INIT_BAROCLINIC_ONLY = 7

    ! Глубины интеграции для каждого режима [см]
    real, parameter :: H50_CM = 5000.0
    real, parameter :: H100_CM = 10000.0
    real, parameter :: H200_CM = 20000.0
    real, parameter :: H400_CM = 40000.0
    real, parameter :: H600_CM = 60000.0

    ! Локальные константы (как в main.f90)
    real, parameter :: C1_LOCAL = 981.0  ! g/rho0
    real, parameter :: C8_LOCAL = 0.25/1389000.0  ! 1/cm

contains

    ! ==========================================================================
    ! Главная подпрограмма: инициализация 3D-скоростей
    ! ==========================================================================
    subroutine init_geostrophic_velocity()
        integer :: init_mode
        real :: max_depth_cm
        logical :: baroclinic_only
        character(len=64) :: env_str

        print *, ">>> Initializing geostrophic velocity (Stage 7.7C)..."

        ! Определение режима из переменной окружения
        call get_environment_variable('ICEBERG_OCEAN_VELOCITY_INIT', env_str)
        if (len_trim(env_str) .eq. 0) then
            ! По умолчанию: если реалистичные T/S загружены — geostrophic, иначе synthetic
            ! Проверяем: если T2 имеет не-синтетические значения (не 15→2°C профиль)
            ! Для простоты: если ro не везде одинаковое — geostrophic
            ! В будущем можно добавить флаг realistic_ok из init_ocean
            env_str = 'geostrophic'
        end if

        select case (trim(adjustl(env_str)))
        case ('synthetic')
            init_mode = INIT_SYNTHETIC
        case ('zero')
            init_mode = INIT_ZERO
        case ('geostrophic')
            init_mode = INIT_GEOSTROPHIC
            max_depth_cm = H600_CM
            baroclinic_only = .false.
        case ('geostrophic_h50')
            init_mode = INIT_GEOSTROPHIC_H50
            max_depth_cm = H50_CM
            baroclinic_only = .false.
        case ('geostrophic_h100')
            init_mode = INIT_GEOSTROPHIC_H100
            max_depth_cm = H100_CM
            baroclinic_only = .false.
        case ('geostrophic_h200')
            init_mode = INIT_GEOSTROPHIC_H200
            max_depth_cm = H200_CM
            baroclinic_only = .false.
        case ('geostrophic_h400')
            init_mode = INIT_GEOSTROPHIC_H400
            max_depth_cm = H400_CM
            baroclinic_only = .false.
        case ('baroclinic_only')
            init_mode = INIT_BAROCLINIC_ONLY
            max_depth_cm = H600_CM
            baroclinic_only = .true.
        case default
            print *, "WARNING: Unknown ICEBERG_OCEAN_VELOCITY_INIT = ", trim(env_str)
            print *, "         Falling back to synthetic drift"
            init_mode = INIT_SYNTHETIC
        end select

        select case (init_mode)
        case (INIT_SYNTHETIC)
            call init_synthetic_drift()
        case (INIT_ZERO)
            call init_zero_velocity()
        case (INIT_GEOSTROPHIC, INIT_GEOSTROPHIC_H50, INIT_GEOSTROPHIC_H100, &
              INIT_GEOSTROPHIC_H200, INIT_GEOSTROPHIC_H400)
            call init_geostrophic_3d(max_depth_cm, baroclinic_only)
        case (INIT_BAROCLINIC_ONLY)
            call init_geostrophic_3d(max_depth_cm, baroclinic_only)
        end select

        ! Инициализируем также u1/v1 = u2/v2 (как в init_ocean)
        u1 = u2
        v1 = v2

        ! Инициализируем баротропные потоки UP2/VP2 согласованно
        ! UP2 = Σ U2 * DZ1, VP2 = Σ V2 * DZ1
        call init_barotropic_transports()

        print *, ">>> Geostrophic initialization complete. Mode: ", trim(env_str)
    end subroutine init_geostrophic_velocity

    ! ==========================================================================
    ! Канонический синтетический дрейф (как в init_ocean)
    ! ==========================================================================
    subroutine init_synthetic_drift()
        integer :: i, j, k
        do k = 1, ks
            do j = 1, js1
                do i = 1, is1
                    if (kt1(i, j) .gt. 0 .and. k .le. kt1(i, j)) then
                        u2(i, j, k) = 0.20
                        v2(i, j, k) = 0.10
                    else
                        u2(i, j, k) = 0.0
                        v2(i, j, k) = 0.0
                    end if
                end do
            end do
        end do
        print *, ">>> Synthetic drift: u=0.20, v=0.10 cm/s"
    end subroutine init_synthetic_drift

    ! ==========================================================================
    ! Нулевая скорость
    ! ==========================================================================
    subroutine init_zero_velocity()
        u2 = 0.0
        v2 = 0.0
        print *, ">>> Zero velocity initialization"
    end subroutine init_zero_velocity

    ! ==========================================================================
    ! 3D Геострофическая инициализация
    ! ==========================================================================
    subroutine init_geostrophic_3d(max_depth_cm, baroclinic_only)
        real, intent(in) :: max_depth_cm
        logical, intent(in) :: baroclinic_only

        integer :: i, j, k, m, ki
        real :: sum_x, sum_y
        real :: f_val
        real, dimension(ks) :: sum_x_cum, sum_y_cum
        real :: depth_cm
        integer :: kmax

        print *, ">>> Computing 3D geostrophic velocity..."
        if (baroclinic_only) then
            print *, "    Mode: baroclinic only (depth-mean removed)"
        else
            print *, "    Integration depth: ", max_depth_cm/100.0, " m"
        end if

        ! Определяем максимальный уровень для интеграции
        kmax = ks
        do k = 1, ks
            if (z(k) .gt. max_depth_cm) then
                kmax = k - 1
                exit
            end if
        end do
        if (kmax .lt. 1) kmax = 1

        ! Цикл по внутренним U-точкам (i=2..IS, j=2..JS)
        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle  ! суша

                ! Ограничиваем интеграцию min(ki, kmax)
                ki = min(ki, kmax)

                ! Королис в U-точке
                f_val = fku(i, j)
                if (abs(f_val) .lt. 1e-12) then
                    ! У экватора — ставим дрейф
                    do k = 1, ki
                        u2(i, j, k) = 0.20
                        v2(i, j, k) = 0.10
                    end do
                    do k = ki + 1, ks
                        u2(i, j, k) = 0.0
                        v2(i, j, k) = 0.0
                    end do
                    cycle
                end if

                ! Накопленные интегралы сум_x, сум_y для каждого уровня
                sum_x = 0.0
                sum_y = 0.0
                do m = 1, ki
                    ! ΔRO_x(m) = RO(i-1,j,m) + RO(i,j,m) - RO(i-1,j-1,m) - RO(i,j-1,m)
                    sum_x = sum_x + C8_LOCAL*Dz(m)* &
                            (ro(i - 1, j, m) + ro(i, j, m) - ro(i - 1, j - 1, m) - ro(i, j - 1, m))
                    ! ΔRO_y(m) = RO(i-1,j-1,m) + RO(i-1,j,m) - RO(i,j-1,m) - RO(i,j,m)
                    sum_y = sum_y + C8_LOCAL*Dz(m)* &
                            (ro(i - 1, j - 1, m) + ro(i - 1, j, m) - ro(i, j - 1, m) - ro(i, j, m))
                    sum_x_cum(m) = sum_x
                    sum_y_cum(m) = sum_y
                end do

                ! Геострофическая скорость на каждом уровне
                ! f * V = 2 * C1_LOCAL * sum_x
                ! f * U = -2 * C1_LOCAL * sum_y
                do k = 1, ki
                    v2(i, j, k) = 2.0*C1_LOCAL*sum_x_cum(k)/f_val
                    u2(i, j, k) = -2.0*C1_LOCAL*sum_y_cum(k)/f_val
                end do

                ! Ниже дна — ноль
                do k = ki + 1, ks
                    u2(i, j, k) = 0.0
                    v2(i, j, k) = 0.0
                end do
            end do
        end do

        ! Граничные условия: u2/v2 на краях = соседние внутренние
        call apply_velocity_bc(u2, v2)

        ! Если baroclinic_only — убираем глубинное среднее
        if (baroclinic_only) then
            call remove_depth_mean()
        end if

        ! Диагностика
        call diagnose_geostrophic()
    end subroutine init_geostrophic_3d

    ! ==========================================================================
    ! Инициализация баротропных потоков UP2/VP2 из 3D скоростей
    ! UP2 = Σ U2(k) * DZ1(k), VP2 = Σ V2(k) * DZ1(k)
    ! ==========================================================================
    subroutine init_barotropic_transports()
        integer :: i, j, k, ki
        real :: dzz, u_sum, v_sum

        up2 = 0.0
        vp2 = 0.0

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle

                u_sum = 0.0
                v_sum = 0.0
                do k = 1, ki
                    if (k .eq. ki) then
                        if (ki .ne. 1) then
                            dzz = map1(i, j) - 0.5*(z(ki) + z(ki - 1))
                        else
                            dzz = map1(i, j)
                        end if
                    else
                        dzz = dz1(k)
                    end if
                    u_sum = u_sum + u2(i, j, k)*dzz
                    v_sum = v_sum + v2(i, j, k)*dzz
                end do

                ! UP2 на U-точке, VP2 на V-точке
                ! UP2(i,j) — поток через U- Грань (i,j)
                ! VP2(i,j) — поток через V- Грань (i,j)
                up2(i, j) = u_sum
                vp2(i, j) = v_sum
            end do
        end do

        ! Граничные условия для UP2/VP2
        up2(:, 1) = up2(:, 2)
        up2(:, js1) = up2(:, js)
        up2(1, :) = up2(2, :)
        up2(is1, :) = up2(is, :)
        vp2(:, 1) = vp2(:, 2)
        vp2(:, js1) = vp2(:, js)
        vp2(1, :) = vp2(2, :)
        vp2(is1, :) = vp2(is, :)

        ! Инициализируем up1/vp1 = up2/vp2
        up1 = up2
        vp1 = vp2

        print *, ">>> Barotropic transports initialized from 3D velocity"
    end subroutine init_barotropic_transports

    ! ==========================================================================
    ! Убрать глубинное среднее (baroclinic_only режим)
    ! U_bc(k) = U(k) - U_bar, где U_bar = (Σ U(k) DZ1(k)) / H
    ! ==========================================================================
    subroutine remove_depth_mean()
        integer :: i, j, k, ki
        real :: dzz, hht, u_bar, v_bar, u_sum, v_sum

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle

                hht = map1(i, j)
                if (abs(hht - 8888.0) .lt. 1e-8) cycle

                u_sum = 0.0
                v_sum = 0.0
                do k = 1, ki
                    if (k .eq. ki) then
                        if (ki .ne. 1) then
                            dzz = hht - 0.5*(z(ki) + z(ki - 1))
                        else
                            dzz = hht
                        end if
                    else
                        dzz = dz1(k)
                    end if
                    u_sum = u_sum + u2(i, j, k)*dzz
                    v_sum = v_sum + v2(i, j, k)*dzz
                end do

                u_bar = u_sum/hht
                v_bar = v_sum/hht

                do k = 1, ki
                    u2(i, j, k) = u2(i, j, k) - u_bar
                    v2(i, j, k) = v2(i, j, k) - v_bar
                end do
            end do
        end do

        ! Пересчитываем UP2/VP2 (должны стать ≈ 0)
        call init_barotropic_transports()

        print *, ">>> Depth-mean removed (baroclinic only)"
    end subroutine remove_depth_mean

    ! ==========================================================================
    ! Граничные условия для 3D скоростей
    ! ==========================================================================
    subroutine apply_velocity_bc(u_arr, v_arr)
        real, intent(inout) :: u_arr(:, :, :), v_arr(:, :, :)

        ! U-точки: j=1 (север) и j=JS1 (юг)
        u_arr(:, 1, :) = u_arr(:, 2, :)
        u_arr(:, js1, :) = u_arr(:, js, :)

        ! V-точки: i=1 (запад) и i=IS1 (восток)
        v_arr(1, :, :) = v_arr(2, :, :)
        v_arr(is1, :, :) = v_arr(is, :, :)

        ! Углы
        u_arr(1, :, :) = u_arr(2, :, :)
        u_arr(is1, :, :) = u_arr(is, :, :)
        v_arr(:, 1, :) = v_arr(:, 2, :)
        v_arr(:, js1, :) = v_arr(:, js, :)
    end subroutine apply_velocity_bc

    ! ==========================================================================
    ! Диагностика геострофической инициализации
    ! ==========================================================================
    subroutine diagnose_geostrophic()
        integer :: i, j, k, ki
        real :: u_max, v_max, speed_max, u_min, v_min

        u_max = -huge(0.0)
        v_max = -huge(0.0)
        speed_max = -huge(0.0)
        u_min = huge(0.0)
        v_min = huge(0.0)

        do j = 2, js
            do i = 2, is
                ki = kk1(i, j)
                if (ki .eq. 0) cycle
                do k = 1, ki
                    u_max = max(u_max, u2(i, j, k))
                    u_min = min(u_min, u2(i, j, k))
                    v_max = max(v_max, v2(i, j, k))
                    v_min = min(v_min, v2(i, j, k))
                    speed_max = max(speed_max, sqrt(u2(i, j, k)**2 + v2(i, j, k)**2))
                end do
            end do
        end do

print *, '>>> Geostrophic init: U_min=', u_min, ' U_max=', u_max, ' V_min=', v_min, ' V_max=', v_max
        print *, '>>> Max speed=', speed_max, ' cm/s =', speed_max/100.0, ' m/s'
    end subroutine diagnose_geostrophic

end module geostrophic_init
