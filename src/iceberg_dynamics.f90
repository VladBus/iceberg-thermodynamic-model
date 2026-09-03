! ==============================================================================
! Модуль: iceberg_dynamics
! Назначение: Динамика айсберга — ветровое и водное трение, Кориолис,
!             градиент давления, Фруде-Крилов, полунеявный решатель импульса.
! Физика: Stage 9.1 §16-23.
!   Уравнение: M * du/dt = F_wind + F_water + F_cor + F_pressure + F_FK
!   Кориолис решается полунеявно (legacy Block 777 / Wagner 2017):
!     A = 1 + (dt * f)^2
!     u_new = (u_old + dt*Fx_noncor/M + dt*f*v_old) / A
!     v_new = (v_old + dt*Fy_noncor/M - dt*f*u_old) / A
!   Водное трение Method A: интеграл по слоям осадки
!   Ветровое трение: парусная площадь A_sail
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
    !   ГЛАВНАЯ ПОДПРОГРАММА ДИНАМИКИ (переименована для избежания конфликта)
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

        ! 2. Водная сила (Method A)
        call compute_water_force(state, ocean_prof, f_water_x, f_water_y)
        diag%f_water_x = f_water_x
        diag%f_water_y = f_water_y

        ! 3. Сила Кориолиса
        f_cor_x = mass*f_coriolis*state%v
        f_cor_y = -mass*f_coriolis*state%u
        diag%f_cor_x = f_cor_x
        diag%f_cor_y = f_cor_y

        ! 4. Градиент давления
        f_pres_x = -mass/RHO_WATER*grad_eta_x
        f_pres_y = -mass/RHO_WATER*grad_eta_y
        diag%f_pressure_x = f_pres_x
        diag%f_pressure_y = f_pres_y

        ! 5. Фруде-Крилов
        diag%f_fk_x = fk_x
        diag%f_fk_y = fk_y

        ! 6. Полунеявная схема для Кориолиса
        fx_noncor = f_wind_x + f_water_x + f_pres_x + fk_x
        fy_noncor = f_wind_y + f_water_y + f_pres_y + fk_y

        u_old = state%u
        v_old = state%v

        A_mat = 1.0 + (dt*f_coriolis)**2

        state%u = (u_old + dt*fx_noncor/mass + dt*f_coriolis*v_old)/A_mat
        state%v = (v_old + dt*fy_noncor/mass - dt*f_coriolis*u_old)/A_mat
    end subroutine iceberg_dynamics_step

    ! ========================================================================
    !   ВЕТРОВАЯ СИЛА (Stage 9.1 §19)
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

            side_area_x = state%W*dz_layer
            side_area_y = state%L*dz_layer

            du = u_prof(k) - state%u
            dv = v_prof(k) - state%v
            speed_rel = sqrt(du**2 + dv**2)

            fx = fx + 0.5*RHO_WATER*CD_WATER*side_area_x*speed_rel*du
            fy = fy + 0.5*RHO_WATER*CD_WATER*side_area_y*speed_rel*dv
        end do
    end subroutine compute_water_force

    ! ========================================================================
    !   Method B — глубинно-усреднённое течение (для TEST_4)
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
    function inertial_period(latitude) result(T_inertial)
        real, intent(in) :: latitude
        real :: T_inertial
        real :: f

        f = 2.0*OMEGA*sin(latitude/57.2957795)
        T_inertial = 2.0*3.141592653589793/abs(f)
    end function inertial_period

end module iceberg_dynamics
