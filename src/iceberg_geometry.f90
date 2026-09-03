! ==============================================================================
! Модуль: iceberg_geometry
! Назначение: Геометрические вычисления для айсберга — объемы, площади,
!             буoyantность, загрунтование, массовый баланс, объёмные скорости.
! Физика: Stage 9.1 §8-18. Прямоугольный параллелепипед L×W×H с архимедовой осадкой.
!         Масса диагностическая: M = ρ_ice * L * W * H                   [кг]
!         Осадка (Archimedes): D = H * ρ_ice / ρ_water                   [м]
!         Надводная часть: F = H - D                                     [м]
!         Площадь водной линии: A_wl = L * W                             [м²]
!         Оромочённая площадь (дно + боковые до осадки):
!           A_wet = L*W + 2*(L+W)*D                                      [м²]
!         Парусная площадь (верх + боковые над водой):
!           A_sail = L*W + 2*(L+W)*F                                     [м²]
!         Проверка буоянтности: ρ_w*g*V_sub = ρ_ice*g*V_total
!         Загрунтование: D >= bathymetry (глубина моря > 0)
!
! Единицы: SI (м, кг, с, Па).
! Точность: default real (float32).
! ==============================================================================

module iceberg_geometry
    use iceberg_types
    implicit none

contains

    ! ========================================================================
    !   ПОЛНЫЙ РАСЧЁТ ГЕОМЕТРИИ И ДИАГНОСТИК
    ! ========================================================================
    ! Вычисляет все геометрические характеристики из состояния.
    !
    ! Аргументы:
    !   state - входное состояние айсберга (intent(in))
    !   geom  - выходная структура диагностик (intent(out))
    !
    ! Формулы:
    !   V_total = L * W * H
    !   M = ρ_ice * V_total
    !   D = H * ρ_ice / ρ_water
    !   F = H - D
    !   V_sub = L * W * D
    !   A_wl = L * W
    !   A_wet = L*W + 2*(L+W)*D
    !   A_sail = L*W + 2*(L+W)*F
    !   verify_buoyancy(V_total, V_sub, M)
    ! ========================================================================
    subroutine compute_full_geometry(state, geom)
        type(iceberg_state), intent(in) :: state
        type(iceberg_diagnostics), intent(out) :: geom

        real :: draft, freeboard
        real :: v_total, v_sub

        v_total = state%L*state%W*state%H
        geom%mass = RHO_ICE*v_total

        draft = state%H*RHO_ICE/RHO_WATER
        geom%draft = draft

        freeboard = state%H - draft
        geom%freeboard = freeboard

        v_sub = state%L*state%W*draft

        geom%a_waterline = state%L*state%W
        geom%a_wet = state%L*state%W + 2.0*(state%L + state%W)*draft
        geom%a_sail = state%L*state%W + 2.0*(state%L + state%W)*freeboard

        call verify_buoyancy(v_total, v_sub, geom%mass)
    end subroutine compute_full_geometry

    ! ========================================================================
    !   ПРОВЕРКА АРХИМЕДОВОЙ СИЛЫ
    ! ========================================================================
    ! Архимедов закон: F_buoyancy = ρ_water * g * V_sub
    ! Weight = M * g = ρ_ice * V_total * g
    ! Должно выполняться: ρ_water * V_sub = ρ_ice * V_total
    ! (по определению D = H*ρ_ice/ρ_water → V_sub = L*W*H*ρ_ice/ρ_water)
    !
    ! Аргументы:
    !   v_total - общий объём [м³]
    !   v_sub   - подводный объём [м³]
    !   mass    - масса [кг]
    ! ========================================================================
    subroutine verify_buoyancy(v_total, v_sub, mass)
        real, intent(in) :: v_total, v_sub, mass
        real :: buoyancy_force, weight, residual

        buoyancy_force = RHO_WATER*GRAVITY*v_sub
        weight = mass*GRAVITY
        residual = abs(buoyancy_force - weight)/weight

        if (residual .gt. 1.0e-6) then
            print *, "GEOM WARNING: Buoyancy imbalance: ", residual
        end if
    end subroutine verify_buoyancy

    ! ========================================================================
    !   ПРОВЕРКА ЗАГРУНТОВАНИЯ С ДЕТАЛЬНОЙ ДИАГНОСТИКОЙ
    ! ========================================================================
    ! Условие загрунтования: осадка D >= батиметрия (глубина моря).
    ! grounded_fraction = min(1.0, D / max(bathymetry, 1.0))
    ! Используется для диагностики, основная логика в iceberg_check_grounding.
    !
    ! Аргументы:
    !   state              - входное состояние
    !   bathymetry         - глубина моря [м]
    !   grounded           - флаг загрунтования (выход)
    !   draft              - осадка [м] (выход)
    !   grounded_fraction  - доля загрунтования [0-1] (выход)
    ! ========================================================================
    subroutine check_grounding_detailed(state, bathymetry, grounded, &
                                        draft, grounded_fraction)
        type(iceberg_state), intent(in) :: state
        real, intent(in) :: bathymetry
        logical, intent(out) :: grounded
        real, intent(out) :: draft
        real, intent(out) :: grounded_fraction

        draft = state%H*RHO_ICE/RHO_WATER

        if (draft .ge. bathymetry) then
            grounded = .true.
            grounded_fraction = min(1.0, draft/max(bathymetry, 1.0))
        else
            grounded = .false.
            grounded_fraction = 0.0
        end if
    end subroutine check_grounding_detailed

    ! ========================================================================
    !   МАССОВЫЙ БАЛАНС ЗА ШАГ (для верификации TEST_10)
    ! ========================================================================
    ! Вычисляет потери массы за временной шаг dt из скоростей плавления
    ! и текущей геометрии. Используется для проверки сходимости баланса.
    !
    ! Формулы:
    !   D = H * ρ_ice / ρ_water
    !   A_base = L * W
    !   A_lateral = 2*(L+W)*D
    !   A_top = L * W
    !   basal_loss    = ρ_ice * m_basal * A_base * dt
    !   lateral_loss  = ρ_ice * m_lateral * A_lateral * dt
    !   surface_loss  = ρ_ice * m_surface * A_top * dt
    !   total_loss = basal + lateral + surface
    !
    ! Аргументы:
    !   state          - состояние (геометрия для площадей)
    !   dt             - шаг по времени [с]
    !   m_basal        - базальная скорость плавления [м/с]
    !   m_lateral      - боковая скорость плавления [м/с]
    !   m_surface      - поверхностная скорость плавления [м/с]
    !   basal_loss     - потеря массы базальным плавлением [кг] (выход)
    !   lateral_loss   - потеря массы боковым плавлением [кг] (выход)
    !   surface_loss   - потеря массы поверхностным плавлением [кг] (выход)
    !   total_loss     - суммарная потеря массы [кг] (выход)
    ! ========================================================================
    subroutine compute_mass_budget(state, dt, m_basal, m_lateral, m_surface, &
                                   basal_loss, lateral_loss, surface_loss, total_loss)
        type(iceberg_state), intent(in) :: state
        real, intent(in) :: dt
        real, intent(in) :: m_basal, m_lateral, m_surface
        real, intent(out) :: basal_loss, lateral_loss, surface_loss, total_loss

        real :: draft, a_base, a_lateral, a_top

        draft = state%H*RHO_ICE/RHO_WATER
        a_base = state%L*state%W
        a_lateral = 2.0*(state%L + state%W)*draft
        a_top = state%L*state%W

        basal_loss = RHO_ICE*m_basal*a_base*dt
        lateral_loss = RHO_ICE*m_lateral*a_lateral*dt
        surface_loss = RHO_ICE*m_surface*a_top*dt
        total_loss = basal_loss + lateral_loss + surface_loss
    end subroutine compute_mass_budget

    ! ========================================================================
    !   ОБЪЁМНЫЕ СКОРОСТИ ИЗМЕНЕНИЯ ИЗ ПЛАВЛЕНИЯ
    ! ========================================================================
    ! Вычисляет объёмные скорости (м³/с) для каждого компонента плавления.
    ! Используется в iceberg_update_geometry для расчёта dV.
    !
    ! Формулы:
    !   D = H * ρ_ice / ρ_water
    !   A_base = L * W
    !   A_lateral = 2*(L+W)*D
    !   A_top = L * W
    !   dV_basal/dt   = m_basal * A_base
    !   dV_lateral/dt = m_lateral * A_lateral
    !   dV_surface/dt = m_surface * A_top
    !
    ! Аргументы:
    !   m_basal, m_lateral, m_surface - скорости плавления [м/с]
    !   state                         - состояние (геометрия)
    !   dV_basal, dV_lateral, dV_surface - объёмные скорости [м³/с] (выход)
    ! ========================================================================
    subroutine melt_volume_rates(m_basal, m_lateral, m_surface, &
                                 state, dV_basal, dV_lateral, dV_surface)
        real, intent(in) :: m_basal, m_lateral, m_surface
        type(iceberg_state), intent(in) :: state
        real, intent(out) :: dV_basal, dV_lateral, dV_surface

        real :: draft, a_base, a_lateral, a_top

        draft = state%H*RHO_ICE/RHO_WATER
        a_base = state%L*state%W
        a_lateral = 2.0*(state%L + state%W)*draft
        a_top = state%L*state%W

        dV_basal = m_basal*a_base
        dV_lateral = m_lateral*a_lateral
        dV_surface = m_surface*a_top
    end subroutine melt_volume_rates

end module iceberg_geometry
