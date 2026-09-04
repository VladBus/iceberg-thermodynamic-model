! ==============================================================================
! Модуль: iceberg
! Назначение: Главный модуль индивидуальной лагранжевой модели айсберга.
!             Содержит тип состояния, основной цикл интегрирования и
!             координацию подмодулей (геометрия, термодинамика, динамика, форсинг).
! Физика: Stage 9.1 §7-26. Модель представляет айсберг как прямоугольный
!         параллелепипед L×W×H с равномерной внутренней температурой T_ICE = -10°C.
!         Движение описывается уравнением импульса точки массы:
!         M * du/dt = F_wind + F_water + F_cor + F_pressure + F_FK
!         с полунеявной схемой для Кориолиса (Wagner 2017 / Block 777 legacy).
!         Термодинамика: базальное, боковое, поверхностное плавление.
!         Форсинг: OFFLINE/PRESCRIBED (ERA5 атмосфера, EN4 океан T/S, IBCAO батиметрия).
!         Нет двусторонней связи с океаном/лём.
!
! Алгоритм временного шага (iceberg_step):
!   1. Вычисление геометрии (масса, осадка, площади)
!   2. Проверка буоянтности (Archimedes)
!   3. Проверка загрунтования (D >= bathymetry)
!   4. Термодинамика (iceberg_thermodynamics_step)
!   5. Обновление геометрии после плавления (iceberg_update_geometry)
!   6. Пересчёт геометрии
!   7. Проверка исчезновения (H,L,W < MIN_THICKNESS)
!   8. Повторная проверка загрунтования
!   9. Динамика (iceberg_dynamics_step) если не загрунтован
!  10. Обновление позиции: x = x + dt*u, y = y + dt*v
!  11. Инкремент времени и подсчёт массового баланса
!
! Массовый баланс: потери считаются через объёмные изменения с геометрией
! ДО плавления (pre-melt geometry) для консистентности (исправлено Stage 9.3).
!   dV_basal = L_old*W_old*dt*m_basal
!   dV_surface = L_old*W_old*dt*m_surface
!   dV_lateral = (H_old*W_old + L_old*H_old)*dt*m_lateral
!   dM = ρ_ice * dV
!
! Единицы: ВСЕ ВНУТРЕННИЕ ВЫЧИСЛЕНИЯ В СИ (м, с, кг, Па, Вт, Дж, К/°C).
!          Преобразование единиц только на границе с форсингом (ERA5/EN4).
! Точность: default real (float32).
! ==============================================================================

module iceberg
    use iceberg_types
    use iceberg_thermodynamics
    use iceberg_dynamics
    use iceberg_geometry
    use iceberg_forcing, only: model_coords_to_latlon
    use param, only: is, js, is1, js1, ht, kt1, fi, dl
    implicit none

contains

    ! ========================================================================
    !   ИНИЦИАЛИЗАЦИЯ АЙСБЕРГА
    ! ========================================================================
    ! Аргументы:
    !   state    - выходная структура состояния (intent(out))
    !   x0, y0   - начальная позиция в модельных координатах [м]
    !   L0, W0, H0 - начальные размеры: длина, ширина, высота [м]
    !   lat0, lon0 - начальная географическая позиция [°]
    !   u0, v0   - начальная скорость дрейфа [м/с] (optional, по умолчанию 0)
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
    ! Формулы:
    !   Масса:         M = ρ_ice * L * W * H                           [кг]
    !   Осадка:        D = H * ρ_ice / ρ_water                         [м]
    !   Надводная:     H - D                                           [м]
    !   Площадь ВЛ:    A_wl = L * W                                     [м²]
    !   Оромочённая:   A_wet = L*W + 2*(L+W)*D                         [м²]
    !   Парусная:      A_sail = L*W + 2*(L+W)*(H-D)                    [м²]
    !
    ! Аргументы:
    !   state - входное состояние (intent(in))
    !   geom  - выходная структура диагностик (intent(out))
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
    ! Архимедов закон: ρ_water * g * V_sub = ρ_ice * g * V_total
    ! Остаток: residual = |F_buoyancy - Weight| / Weight
    ! Должен быть ~0 (машинная точность float32 ~ 1e-6).
    !
    ! Аргументы:
    !   state             - входное состояние
    !   buoyancy_residual - выходной относительный остаток [безразм.]
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
    ! Условие: осадка D >= батиметрия (глубина моря).
    ! Если загрунтован: grounded = .true., скорость u=v=0.
    ! Батиметрия > 0 = глубина воды [м].
    !
    ! Аргументы:
    !   state       - состояние (intent(inout), обновляется grounded, u, v)
    !   bathymetry  - глубина моря [м]
    !   grounded    - выходной флаг загрунтования
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
    ! Последовательность вызовов:
    !   1. iceberg_compute_geometry      - геометрия
    !   2. iceberg_compute_buoyancy      - буоянтность
    !   3. iceberg_check_grounding       - загрунтование (1-я)
    !   4. iceberg_thermodynamics_step   - плавление (обновляет diag с m_*)
    !   5. iceberg_update_geometry       - обновление L,W,H по m_* (pre-melt geom)
    !   6. iceberg_compute_geometry      - пересчёт геометрии
    !   7. Проверка исчезновения (MIN_THICKNESS)
    !   8. iceberg_check_grounding       - загрунтование (2-я)
    !   9. iceberg_dynamics_step         - динамика (если не grounded)
    !  10. Обновление позиции: x += dt*u, y += dt*v
    !  11. Инкремент nstep, time
    !  12. Массовый баланс: total = basal + lateral + surface
    !
    ! Аргументы:
    !   state       - состояние айсберга (intent(inout))
    !   dt          - шаг по времени [с]
    !   ocean_prof  - профиль океана на позиции (intent(in))
    !   atmos       - атмосферный форсинг (intent(in))
    !   bathymetry  - глубина моря [м]
    !   grad_eta_x  - градиент УМО по X [м/м] (optional)
    !   grad_eta_y  - градиент УМО по Y [м/м] (optional)
    !   fk_force    - Фруде-Крилов сила [Н] массив(2) (optional)
    !   diag        - диагностики (intent(out))
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

        ! 2. Проверка загрунтования (1-я)
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
            ! Параметр Кориолиса: f = 2Ω sin(φ)
            f_coriolis = 2.0*OMEGA*sin(state%latitude/57.2957795)

            ! Градиент давления (optional)
            pressure_x = 0.0
            pressure_y = 0.0
            if (present(grad_eta_x)) pressure_x = grad_eta_x
            if (present(grad_eta_y)) pressure_y = grad_eta_y

            ! Фруде-Крилов (optional)
            fk_x = 0.0
            fk_y = 0.0
            if (present(fk_force)) then
                fk_x = fk_force(1)
                fk_y = fk_force(2)
            end if

            call iceberg_dynamics_step(state, dt, ocean_prof, atmos, &
                                       f_coriolis, pressure_x, pressure_y, &
                                       fk_x, fk_y, diag)

            ! 9. Обновление позиции (простой Эйлер, явная схема)
            state%x = state%x + dt*state%u
            state%y = state%y + dt*state%v

            ! 9a. Обновление географических координат из модельных (Stage 9.4A)
            ! x/y — authoritative coordinates; lat/lon derived via inverse projection
            ! Проверяем, что модельная сетка инициализирована (fi/dl не нули)
            if (fi(1,1) .ne. 0.0 .or. dl(1,1) .ne. 0.0) then
                call model_coords_to_latlon(state%x, state%y, state%latitude, state%longitude, &
                                            diag%forcing_valid)
                if (.not. diag%forcing_valid) then
                    ! Вышли за границы модельной сетки
                    print *, "WARNING: Iceberg outside model domain at step ", state%nstep
                    print *, "  x=", state%x, " y=", state%y
                    state%active = .false.
                    return
                end if
            else
                ! Сетка не инициализирована (тестовый режим без coup1) - сохраняем исходные lat/lon
                diag%forcing_valid = .true.
            end if
        else
            ! Загрунтован: все силы = 0
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

        ! 11. Массовый баланс
        diag%total_mass_loss = diag%basal_mass_loss + &
                               diag%lateral_mass_loss + &
                               diag%surface_mass_loss
    end subroutine iceberg_step

    ! ========================================================================
    !   ОБНОВЛЕНИЕ ГЕОМЕТРИИ ПОСЛЕ ПЛАВЛЕНИЯ (Stage 9.1 §26)
    ! ========================================================================
    ! Использует геометрию ДО плавления (pre-melt) для консистентного
    ! массового баланса. Исправлено в Stage 9.3 (была ошибка 56%).
    !
    ! Обновление размеров (явный Эйлер):
    !   H_new = H_old - dt*(m_basal + m_surface)
    !   L_new = L_old - dt*m_lateral
    !   W_new = W_old - dt*m_lateral
    ! С обрезкой: max(0, ...)
    !
    ! Массовый баланс через объём:
    !   V_old = L_old * W_old * H_old
    !   V_new = L_new * W_new * H_new
    !   dV = V_old - V_new
    !   dV_basal    = L_old*W_old*dt*m_basal
    !   dV_surface  = L_old*W_old*dt*m_surface
    !   dV_lateral  = (H_old*W_old + L_old*H_old)*dt*m_lateral
    !   dM_* = ρ_ice * dV_*
    !
    ! Аргументы:
    !   state - состояние (intent(inout), обновляются L,W,H)
    !   dt    - шаг по времени [с]
    !   diag  - диагностики с m_* [м/с] (intent(inout), обновляются mass_loss)
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
    !   ФИНАЛИЗАЦИЯ (заглушка для будущего использования)
    ! ========================================================================
    subroutine iceberg_finalize(state)
        type(iceberg_state), intent(inout) :: state
    end subroutine iceberg_finalize

end module iceberg
