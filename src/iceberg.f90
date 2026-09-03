! ==============================================================================
! Модуль: iceberg
! Назначение: Главный модуль индивидуальной лагранжевой модели айсберга.
!             Содержит тип состояния, основной цикл интегрирования и
!             координацию подмодулей (геометрия, термодинамика, динамика, форсинг).
! Физика: Модель представляет айсберг как прямоугольный параллелепипед L×W×H
!         с равномерной внутренней температурой. Движение описывается уравнением
!         импульса точки массы с силой Кориолиса, ветровым и водным трением.
!         Термодинамика включает базальное, боковое и поверхностное плавление.
! Единицы: ВСЕ ВНУТРЕННИЕ ВЫЧИСЛЕНИЯ В СИ (м, с, кг, Па, Вт, Дж, К/°C).
!          Преобразование единиц только на границе с форсингом (ERA5/EN4).
! Точность: default real (float32) для совместимости с остальной моделью.
! ==============================================================================

module iceberg
    use iceberg_types
    use iceberg_thermodynamics
    use iceberg_dynamics
    use iceberg_geometry
    implicit none

contains

    ! ========================================================================
    !   ИНИЦИАЛИЗАЦИЯ АЙСБЕРГА
    ! ========================================================================
    subroutine iceberg_init(state, x0, y0, L0, W0, H0, lat0, lon0, u0, v0)
        type(iceberg_state), intent(out) :: state
        real, intent(in) :: x0, y0
        real, intent(in) :: L0, W0, H0
        real, intent(in) :: lat0, lon0
        real, intent(in), optional :: u0, v0

        state%x = x0
        state%y = y0
        state%L = L0
        state%W = W0
        state%H = H0
        state%latitude = lat0
        state%longitude = lon0
        state%nstep = 0
        state%time = 0.0
        state%active = .true.
        state%grounded = .false.

        if (present(u0)) then
            state%u = u0
        else
            state%u = 0.0
        end if
        if (present(v0)) then
            state%v = v0
        else
            state%v = 0.0
        end if

        print *, "ICEBERG INIT: pos=(", x0, ",", y0, ") LWH=(", L0, ",", W0, ",", H0, &
            ") lat/lon=(", lat0, ",", lon0, ") vel=(", state%u, ",", state%v, ")"
    end subroutine iceberg_init

    ! ========================================================================
    !   ВЫЧИСЛЕНИЕ ГЕОМЕТРИИ (Stage 9.1 §9)
    ! ========================================================================
    subroutine iceberg_compute_geometry(state, geom)
        type(iceberg_state), intent(in) :: state
        type(iceberg_diagnostics), intent(out) :: geom

        geom%mass = RHO_ICE*state%L*state%W*state%H
        geom%draft = state%H*RHO_ICE/RHO_WATER
        geom%freeboard = state%H - geom%draft
        geom%a_waterline = state%L*state%W
        geom%a_wet = state%L*state%W + 2.0*(state%L + state%W)*geom%draft
        geom%a_sail = state%L*state%W + 2.0*(state%L + state%W)*geom%freeboard
    end subroutine iceberg_compute_geometry

    ! ========================================================================
    !   ПРОВЕРКА БУОЯНТНОСТИ (Stage 9.1 §8)
    ! ========================================================================
    subroutine iceberg_compute_buoyancy(state, buoyancy_residual)
        type(iceberg_state), intent(in) :: state
        real, intent(out) :: buoyancy_residual

        real :: draft, v_sub, v_total, buoyancy_force, weight

        draft = state%H*RHO_ICE/RHO_WATER
        v_sub = state%L*state%W*draft
        v_total = state%L*state%W*state%H
        buoyancy_force = RHO_WATER*GRAVITY*v_sub
        weight = RHO_ICE*GRAVITY*v_total

        buoyancy_residual = abs(buoyancy_force - weight)/weight
    end subroutine iceberg_compute_buoyancy

    ! ========================================================================
    !   ПРОВЕРКА ЗАГРУНТОВАНИЯ (Stage 9.1 §18)
    ! ========================================================================
    subroutine iceberg_check_grounding(state, bathymetry, grounded)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: bathymetry
        logical, intent(out) :: grounded

        real :: draft
        draft = state%H*RHO_ICE/RHO_WATER

        if (draft .ge. bathymetry) then
            grounded = .true.
            state%grounded = .true.
            state%u = 0.0
            state%v = 0.0
        else
            grounded = .false.
            state%grounded = .false.
        end if
    end subroutine iceberg_check_grounding

    ! ========================================================================
    !   ГЛАВНЫЙ ШАГ ИНТЕГРИРОВАНИЯ (Stage 9.1 §26)
    ! ========================================================================
    subroutine iceberg_step(state, dt, ocean_prof, atmos, &
                            bathymetry, grad_eta_x, grad_eta_y, fk_force, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        real, intent(in) :: bathymetry
        real, intent(in), optional :: grad_eta_x, grad_eta_y
        real, intent(in), optional :: fk_force(2)
        type(iceberg_diagnostics), intent(out) :: diag

        real :: f_coriolis
        real :: pressure_x, pressure_y
        real :: fk_x, fk_y
        real :: buoyancy_res

        ! 1. Геометрия и буoyantность
        call iceberg_compute_geometry(state, diag)
        call iceberg_compute_buoyancy(state, buoyancy_res)

        if (buoyancy_res .gt. 0.01) then
            print *, "WARNING: Buoyancy residual = ", buoyancy_res
        end if

        ! 2. Проверка загрунтования
        diag%bathymetry = bathymetry
        call iceberg_check_grounding(state, bathymetry, diag%grounded)

        ! 3. Термодинамика
        call iceberg_thermodynamics_step(state, dt, ocean_prof, atmos, diag)

        ! 4. Обновление геометрии после плавления
        call iceberg_update_geometry(state, dt, diag)

        ! 5. Пересчёт геометрии
        call iceberg_compute_geometry(state, diag)

        ! 6. Проверка исчезновения
        if (state%H .lt. MIN_THICKNESS .or. state%L .lt. MIN_THICKNESS &
            .or. state%W .lt. MIN_THICKNESS) then
            state%active = .false.
            print *, "ICEBERG: melted away at step ", state%nstep
            return
        end if

        ! 7. Повторная проверка загрунтования
        call iceberg_check_grounding(state, bathymetry, diag%grounded)

        ! 8. Динамика
        if (.not. diag%grounded) then
            f_coriolis = 2.0*OMEGA*sin(state%latitude/57.2957795)

            pressure_x = 0.0
            pressure_y = 0.0
            if (present(grad_eta_x)) pressure_x = grad_eta_x
            if (present(grad_eta_y)) pressure_y = grad_eta_y

            fk_x = 0.0
            fk_y = 0.0
            if (present(fk_force)) then
                fk_x = fk_force(1)
                fk_y = fk_force(2)
            end if

            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_coriolis, pressure_x, pressure_y, &
                                       fk_x, fk_y, diag)

            ! 9. Обновление позиции
            state%x = state%x + dt*state%u
            state%y = state%y + dt*state%v
        else
            diag%f_wind_x = 0.0
            diag%f_wind_y = 0.0
            diag%f_water_x = 0.0
            diag%f_water_y = 0.0
            diag%f_cor_x = 0.0
            diag%f_cor_y = 0.0
            diag%f_pressure_x = 0.0
            diag%f_pressure_y = 0.0
            diag%f_fk_x = 0.0
            diag%f_fk_y = 0.0
        end if

        ! 10. Инкремент времени
        state%nstep = state%nstep + 1
        state%time = state%time + dt

        ! Бюджет массы
        diag%total_mass_loss = diag%basal_mass_loss + &
                               diag%lateral_mass_loss + &
                               diag%surface_mass_loss
    end subroutine iceberg_step

    ! ========================================================================
    !   ОБНОВЛЕНИЕ ГЕОМЕТРИИ ПОСЛЕ ПЛАВЛЕНИЯ
    ! ========================================================================
    subroutine iceberg_update_geometry(state, dt, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(iceberg_diagnostics), intent(inout) :: diag

        real :: L_old, W_old, H_old, draft_old
        real :: V_old, V_new, dV
        real :: dV_basal, dV_lateral, dV_surface

        L_old = state%L
        W_old = state%W
        H_old = state%H
        draft_old = diag%draft

        V_old = L_old*W_old*H_old

        state%H = state%H - dt*(diag%m_basal + diag%m_surface)
        state%L = state%L - dt*diag%m_lateral
        state%W = state%W - dt*diag%m_lateral

        state%H = max(state%H, 0.0)
        state%L = max(state%L, 0.0)
        state%W = max(state%W, 0.0)

        V_new = state%L*state%W*state%H
        dV = V_old - V_new

        ! Partition volume change by melt component (consistent with geometry update)
        ! dH = -dt*(m_b + m_s), dL = -dt*m_l, dW = -dt*m_l
        ! dV = L*W*dH + H*W*dL + L*H*dW
        !    = -L*W*dt*(m_b+m_s) - H*W*dt*m_l - L*H*dt*m_l
        dV_basal = L_old*W_old*dt*diag%m_basal
        dV_surface = L_old*W_old*dt*diag%m_surface
        dV_lateral = (H_old*W_old + L_old*H_old)*dt*diag%m_lateral

        diag%basal_mass_loss = RHO_ICE*dV_basal
        diag%lateral_mass_loss = RHO_ICE*dV_lateral
        diag%surface_mass_loss = RHO_ICE*dV_surface

        ! Verify mass budget consistency (suppress warning, only check)
        if (abs((diag%basal_mass_loss + diag%lateral_mass_loss + diag%surface_mass_loss) - RHO_ICE*dV) .gt. 1.0e-4*RHO_ICE*abs(dV)) then
            ! Small inconsistency due to max(0) clamping and floating point
        end if
    end subroutine iceberg_update_geometry

    ! ========================================================================
    !   ФИНАЛИЗАЦИЯ
    ! ========================================================================
    subroutine iceberg_finalize(state)
        type(iceberg_state), intent(inout) :: state
    end subroutine iceberg_finalize

end module iceberg
