! ==============================================================================
! Модуль: iceberg_geometry
! Назначение: Геометрические вычисления для айсберга — объемы, площади,
!             буoyantность, загрунтование, массовый баланс.
! Физика: Прямоугольный параллелепипед L×W×H с архимедовой осадкой.
!         Масса диагностическая: M = rho_ice * L * W * H.
!         Осадка: D = H * rho_ice / rho_water.
! Единицы: SI (м, кг, с).
! Точность: default real (float32).
! ==============================================================================

module iceberg_geometry
    use iceberg_types
    implicit none

contains

    ! ========================================================================
    !   ПОЛНЫЙ РАСЧЁТ ГЕОМЕТРИИ И ДИАГНОСТИК
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
    !   МАССОВЫЙ БАЛАНС (для верификации TEST_10)
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
    !   ОБЪЕМНЫЕ ИЗМЕНЕНИЯ ИЗ ПЛАВЛЕНИЯ
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
