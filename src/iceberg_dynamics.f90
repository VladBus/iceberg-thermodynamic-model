! ==============================================================================
! Модуль: iceberg_dynamics
! Назначение: Динамика айсберга — ветровое и водное трение, Кориолис,
!             градиент давления, Фруде-Крилов, полунеявный решатель импульса.
! Физика: Stage 9.1 §16-23.
!   Уравнение движения (2D, горизонтальная плоскость):
!     M * du/dt = F_wind + F_water + F_cor + F_pressure + F_FK
!   где M = ρ_ice * L * W * H  [кг] — масса айсберга.
!
!   Сила Кориолиса (semi-implicit, Wagner 2017 / legacy Block 777):
!     A = 1 + (dt * f)²
!     u_new = (u_old + dt*Fx_noncor/M + dt*f*v_old) / A
!     v_new = (v_old + dt*Fy_noncor/M - dt*f*u_old) / A
!   f = 2Ω sin(φ) — параметр Кориолиса [1/с].
!   Полунеявная схема безусловно устойчива для линейного Кориолиса,
!   но вводит числовое демпфирование (ошибка периода ~8% при dt=3600с).
!
!   Водное трение — два метода:
!     Method A (основной): слой-за-слоем интеграл по осадке
!       F_water = Σ ½ ρ_w C_Dw (W Δz_k) |u_k - u| (u_k - u)
!     Method B (тестовый): глубинно-усреднённое течение, полная оромочённая площадь
!       F_water = ½ ρ_w C_Dw A_wet |u_avg - u| (u_avg - u)
!
!   Ветровое трение:
!     F_wind = ½ ρ_a C_Da A_sail |V_10 - u| (V_10 - u)
!
!   Градиент давления (optional):
!     F_pressure = -M/ρ_water * ∇η
!
!   Фруде-Крилов (optional, для будущего расширения):
!     F_FK = -ρ_water * V_sub * ∇p_water  (в offline режиме = 0)
!
! Единицы: SI (Н, кг, м/с, Па).
! Точность: default real (float32).
! ==============================================================================

module iceberg_dynamics
    use iceberg_types
    use iceberg_forcing, only: depth_integrated_currents
    use iceberg_geometry, only: compute_full_geometry
    implicit none

contains

    ! ========================================================================
    !   ГЛАВНАЯ ПОДПРОГРАММА ДИНАМИКИ
    ! ========================================================================
    ! Последовательность:
    !   1. Масса M = ρ_ice * L * W * H
    !   2. Ветровая сила (compute_wind_force)
    !   3. Водная сила Method A (compute_water_force)
    !   4. Сила Кориолиса: F_cor = M * f * (-v, u)
    !   5. Градиент давления (optional): F_pres = -M/ρ_w * ∇η
    !   6. Фруде-Крилов (optional)
    !   7. Полунеявный решатель для Кориолиса
    !   8. Сохранение сил в diag для диагностики
    !
    ! Аргументы:
    !   state       - состояние (intent(inout), обновляются u, v)
    !   dt          - шаг по времени [с]
    !   ocean_prof  - профиль океана
    !   atmos       - атмосферный форсинг
    !   f_coriolis  - параметр Кориолиса f = 2Ω sin(φ) [1/с]
    !   grad_eta_x  - градиент УМО по X [м/м]
    !   grad_eta_y  - градиент УМО по Y [м/м]
    !   fk_x, fk_y  - Фруде-Крилов сила [Н]
    !   diag        - диагностики (обновляются все силы)
    ! ========================================================================
    subroutine iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                     f_coriolis, grad_eta_x, grad_eta_y, &
                                     fk_x, fk_y, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        real, intent(in) :: f_coriolis
        real, intent(in) :: grad_eta_x, grad_eta_y
        real, intent(in) :: fk_x, fk_y
        type(iceberg_diagnostics), intent(inout) :: diag

        real :: mass
        real :: f_wind_x, f_wind_y
        real :: f_water_x, f_water_y
        real :: f_cor_x, f_cor_y
        real :: f_pres_x, f_pres_y
        real :: A_mat
        real :: u_old, v_old
        real :: fx_noncor, fy_noncor

        mass = RHO_ICE*state%L*state%W*state%H
        diag%mass = mass

        ! 1. Ветровая сила
        call compute_wind_force(state, atmos, f_wind_x, f_wind_y)
        diag%f_wind_x = f_wind_x
        diag%f_wind_y = f_wind_y

        ! 2. Водная сила (Method A — слой-за-слоем)
        call compute_water_force(state, ocean_prof, f_water_x, f_water_y)
        diag%f_water_x = f_water_x
        diag%f_water_y = f_water_y

        ! 3. Сила Кориолиса: F = M * f * (-v, u)
        f_cor_x = mass*f_coriolis*state%v
        f_cor_y = -mass*f_coriolis*state%u
        diag%f_cor_x = f_cor_x
        diag%f_cor_y = f_cor_y

        ! 4. Градиент давления: F = -M/ρ_water * ∇η
        f_pres_x = -mass/RHO_WATER*grad_eta_x
        f_pres_y = -mass/RHO_WATER*grad_eta_y
        diag%f_pressure_x = f_pres_x
        diag%f_pressure_y = f_pres_y

        ! 5. Фруде-Крилов (offline = 0)
        diag%f_fk_x = fk_x
        diag%f_fk_y = fk_y

        ! 6. Полунеявная схема для Кориолиса
        ! Разделяем силы на Кориолис и не-Кориолис
        fx_noncor = f_wind_x + f_water_x + f_pres_x + fk_x
        fy_noncor = f_wind_y + f_water_y + f_pres_y + fk_y

        u_old = state%u
        v_old = state%v

        ! A = 1 + (f*dt)²
        A_mat = 1.0 + (dt*f_coriolis)**2

        ! Полунеявное решение:
        ! u_new = (u_old + dt*Fx_noncor/M + f*dt*v_old) / A
        ! v_new = (v_old + dt*Fy_noncor/M - f*dt*u_old) / A
        state%u = (u_old + dt*fx_noncor/mass + dt*f_coriolis*v_old)/A_mat
        state%v = (v_old + dt*fy_noncor/mass - dt*f_coriolis*u_old)/A_mat
    end subroutine iceberg_dynamics_step

    ! ========================================================================
    !   ВЕТРОВАЯ СИЛА (Stage 9.1 §19)
    ! ========================================================================
    ! F_wind = ½ * ρ_air * C_Da * A_sail * |V_rel| * V_rel
    ! где V_rel = V_10m - u_ice
    ! A_sail = L*W + 2*(L+W)*freeboard  (верх + боковые над водой)
    ! freeboard = H - draft = H*(1 - ρ_ice/ρ_water)
    !
    ! Аргументы:
    !   state - состояние айсберга
    !   atmos - атмосферный форсинг (u10, v10)
    !   fx, fy - силы по X и Y [Н] (выход)
    ! ========================================================================
    subroutine compute_wind_force(state, atmos, fx, fy)
        type(iceberg_state), intent(in) :: state
        type(atmos_forcing), intent(in) :: atmos
        real, intent(out) :: fx, fy

        real :: u_rel, v_rel, speed_rel
        real :: a_sail
        real :: draft, freeboard

        draft = state%H*RHO_ICE/RHO_WATER
        freeboard = state%H - draft
        a_sail = state%L*state%W + 2.0*(state%L + state%W)*freeboard

        u_rel = atmos%u10 - state%u
        v_rel = atmos%v10 - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)

        fx = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*u_rel
        fy = 0.5*RHO_AIR*CD_AIR*a_sail*speed_rel*v_rel
    end subroutine compute_wind_force

    ! ========================================================================
    !   ВОДНАЯ СИЛА — Method A (Stage 9.1 §18)
    ! ========================================================================
    ! Слой-за-слоем интеграл по осадке D:
    !   F_water = Σₖ ½ ρ_w C_Dw (W*Δz_k) |u_k - u| (u_k - u)  по X
    !           = Σₖ ½ ρ_w C_Dw (L*Δz_k) |v_k - v| (v_k - v)  по Y
    ! где u_k, v_k — скорость воды на глубине слоя k.
    ! Δz_k — толщина слоя интегрирования.
    ! Использует depth_integrated_currents для получения профиля u(z), v(z).
    !
    ! Ниже максимального модельного уровня (45м) скорость = 0 (экстраполяция).
    !
    ! Аргументы:
    !   state      - состояние
    !   ocean_prof - профиль океана
    !   fx, fy     - силы [Н] (выход)
    ! ========================================================================
    subroutine compute_water_force(state, ocean_prof, fx, fy)
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(out) :: fx, fy

        real :: draft
        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        integer :: k
        real :: dz_layer, z_top, z_bot
        real :: du, dv, speed_rel
        real :: side_area_x, side_area_y

        draft = state%H*RHO_ICE/RHO_WATER

        call depth_integrated_currents(ocean_prof, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            return
        end if

        fx = 0.0
        fy = 0.0

        do k = 1, n_layers
            ! Определить границы слоя k
            if (k .eq. 1) then
                z_top = 0.0
            else
                z_top = z_layers(k - 1) + 0.5*(z_layers(k) - z_layers(k - 1))
            end if
            if (k .eq. n_layers) then
                z_bot = draft
            else
                z_bot = z_layers(k) + 0.5*(z_layers(k + 1) - z_layers(k))
            end if
            z_bot = min(z_bot, draft)
            dz_layer = z_bot - z_top
            if (dz_layer .le. 0.0) cycle

            ! Площадь боковой грани для слоя: W*Δz (по X), L*Δz (по Y)
            side_area_x = state%W*dz_layer
            side_area_y = state%L*dz_layer

            du = u_prof(k) - state%u
            dv = v_prof(k) - state%v
            speed_rel = sqrt(du**2 + dv**2)

            ! Квадратичное трение: ½ ρ C_d A |V_rel| V_rel
            fx = fx + 0.5*RHO_WATER*CD_WATER*side_area_x*speed_rel*du
            fy = fy + 0.5*RHO_WATER*CD_WATER*side_area_y*speed_rel*dv
        end do
    end subroutine compute_water_force

    ! ========================================================================
    !   Method B — ГЛУБИННО-УСРЕДНЁННОЕ ТЕЧЕНИЕ (для TEST_4 сравнения)
    ! ========================================================================
    ! F_water = ½ ρ_w C_Dw A_wet |U_avg - u| (U_avg - u)
    ! где A_wet = L*W + 2*(L+W)*D — полная оромочённая площадь
    ! U_avg = (1/D) ∫₀ᴰ u(z) dz — глубинно-усреднённое течение
    ! Используется только в TEST_4 для сравнения Method A vs B.
    !
    ! Аргументы:
    !   state      - состояние
    !   ocean_prof - профиль океана
    !   fx, fy     - силы [Н] (выход)
    ! ========================================================================
    subroutine compute_water_force_method_b(state, ocean_prof, fx, fy)
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(out) :: fx, fy

        real :: draft
        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        real :: a_wet, du, dv, speed_rel

        draft = state%H*RHO_ICE/RHO_WATER

        call depth_integrated_currents(ocean_prof, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            return
        end if

        a_wet = state%L*state%W + 2.0*(state%L + state%W)*draft

        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)

        fx = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*du
        fy = 0.5*RHO_WATER*CD_WATER*a_wet*speed_rel*dv
    end subroutine compute_water_force_method_b

    ! ========================================================================
    !   ИНЕРЦИАЛЬНЫЙ ПЕРИОД (для TEST_9)
    ! ========================================================================
    ! T_inertial = 2π / |f|, где f = 2Ω sin(φ)
    ! При φ = 76.5°: f ≈ 1.415e-4 1/с, T ≈ 12.33 ч.
    ! Полунеявная схема даёт T ≈ 13.3 ч (ошибка 8% от демпфирования).
    !
    ! Аргументы:
    !   latitude - широта [°] (intent(in))
    !   T_inertial - инерциальный период [с] (выход)
    ! ========================================================================
    function inertial_period(latitude) result(T_inertial)
        real, intent(in) :: latitude
        real :: T_inertial
        real :: f

        f = 2.0*OMEGA*sin(latitude/57.2957795)
        T_inertial = 2.0*3.141592653589793/abs(f)
    end function inertial_period

end module iceberg_dynamics
