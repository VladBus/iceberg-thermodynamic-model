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
    use iceberg_thermodynamics, only: voxel_geometry_active, voxel_geometry_mass, &
                                      voxel_geometry_draft, voxel_geometry_layer_areas, &
                                      voxel_geometry_drag_geometry
    use wave_forcing, only: stokes_drift_enabled, get_wave_forcing, wave_forcing_epoch
    implicit none

    real, save :: cd_air_form_dyn = CD_AIR_FORM
    real, save :: cd_water_form_dyn = CD_WATER_FORM
    real, save :: cd_air_skin_dyn = CD_AIR_SKIN
    real, save :: cd_water_skin_dyn = CD_WATER_SKIN
    logical, save :: cd_dyn_checked = .false.

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
        real :: u_old, v_old
        real :: u_water, v_water, rel_a, rel_w, k_air, k_water, k_drag
        real :: d_imp, g_imp, rhs_u, rhs_v, det_imp
        real, allocatable :: u_prof_d(:), v_prof_d(:), z_layers_d(:)
        integer :: n_layers_d
        real :: u_avg_d, v_avg_d, draft

        if (voxel_geometry_active()) then
            mass = voxel_geometry_mass()          ! Stage 12.5: voxel geometry drives drift
        else
            mass = RHO_ICE*state%L*state%W*state%H
        end if
        diag%mass = mass

        ! 1. Ветровая сила
        call compute_wind_force(state, atmos, f_wind_x, f_wind_y)
        diag%f_wind_x = f_wind_x
        diag%f_wind_y = f_wind_y

        ! 2. Водная сила (Method A — слой-за-слоем)
        call compute_water_force(state, ocean_prof, f_water_x, f_water_y)
        diag%f_water_x = f_water_x
        diag%f_water_y = f_water_y

        ! 3. Сила Кориолиса: F = M * f * (-v, u), reported at the old state.
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

        ! 6. Semi-implicit linearized drag + Coriolis (Stage 12.17).
        ! With the literature form drag, explicit drag at dt=3600 s is unstable.
        ! Linearize each quadratic drag force about the old relative velocity:
        !   F_drag ~ K*(u_fluid - u),  K = |F_old|/|u_rel_old|.
        ! The 2x2 system below is unconditionally stable for K>=0 and reduces
        ! exactly to the Stage 9 semi-implicit Coriolis update when K=0.
        u_old = state%u
        v_old = state%v
        u_water = u_old
        v_water = v_old
        if (voxel_geometry_active()) then
            draft = voxel_geometry_draft()
        else
            draft = state%H*RHO_ICE/RHO_WATER
        end if
        call depth_integrated_currents(ocean_prof, draft, u_avg_d, v_avg_d, &
                                       u_prof_d, v_prof_d, z_layers_d, n_layers_d)
        if (n_layers_d > 0) then
            u_water = u_avg_d
            v_water = v_avg_d
        end if
        rel_a = sqrt((atmos%u10 - u_old)**2 + (atmos%v10 - v_old)**2)
        rel_w = sqrt((u_water - u_old)**2 + (v_water - v_old)**2)
        k_air = 0.0
        k_water = 0.0
        if (rel_a > 1.0e-6) k_air = sqrt(f_wind_x**2 + f_wind_y**2)/rel_a
        if (rel_w > 1.0e-6) k_water = sqrt(f_water_x**2 + f_water_y**2)/rel_w
        k_drag = k_air + k_water
        d_imp = 1.0 + dt*k_drag/mass
        g_imp = dt*f_coriolis
        rhs_u = u_old + dt*(k_air*atmos%u10 + k_water*u_water + f_pres_x + fk_x)/mass
        rhs_v = v_old + dt*(k_air*atmos%v10 + k_water*v_water + f_pres_y + fk_y)/mass
        det_imp = d_imp*d_imp + g_imp*g_imp
        state%u = (d_imp*rhs_u + g_imp*rhs_v)/det_imp
        state%v = (d_imp*rhs_v - g_imp*rhs_u)/det_imp

        ! Report the linearized drag and Coriolis forces at the new state so
        ! that the force budget closes against M*du/dt for the implicit step.
        diag%f_wind_x = k_air*(atmos%u10 - state%u)
        diag%f_wind_y = k_air*(atmos%v10 - state%v)
        diag%f_water_x = k_water*(u_water - state%u)
        diag%f_water_y = k_water*(v_water - state%v)
        diag%f_cor_x = mass*f_coriolis*state%v
        diag%f_cor_y = -mass*f_coriolis*state%u
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
        real :: a_form, a_top, a_sub_dummy, a_bottom_dummy
        real :: draft, freeboard, cs, sn
        real(8) :: asub8, asail8, atop8, abot8

        call init_drag_coefficients()
        u_rel = atmos%u10 - state%u
        v_rel = atmos%v10 - state%v
        speed_rel = sqrt(u_rel**2 + v_rel**2)
        if (speed_rel > 1.0e-12) then
            cs = u_rel/speed_rel; sn = v_rel/speed_rel
        else
            cs = 0.0; sn = 0.0
        end if

        if (voxel_geometry_active()) then
            call voxel_geometry_drag_geometry(atan2(v_rel, u_rel), asub8, asail8, atop8, abot8)
            a_form = real(asail8, 4)
            a_top = real(atop8, 4)
        else
            draft = state%H*RHO_ICE/RHO_WATER
            freeboard = state%H - draft
            a_form = (abs(cs)*state%W + abs(sn)*state%L)*freeboard
            a_top = state%L*state%W
        end if

        fx = 0.5*RHO_AIR*(cd_air_form_dyn*a_form + cd_air_skin_dyn*a_top)*speed_rel*u_rel
        fy = 0.5*RHO_AIR*(cd_air_form_dyn*a_form + cd_air_skin_dyn*a_top)*speed_rel*v_rel
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
    subroutine compute_water_force(state, ocean_prof, fx, fy, u_water_out, v_water_out)
        type(iceberg_state), intent(in) :: state
        type(ocean_profile), intent(in) :: ocean_prof
        real, intent(out) :: fx, fy
        real, intent(out), optional :: u_water_out, v_water_out

        real :: draft
        real, allocatable :: u_prof(:), v_prof(:), z_layers(:)
        integer :: n_layers
        real :: u_avg, v_avg
        integer :: k
        real :: dz_layer, z_top, z_bot
        real :: du, dv, speed_rel
        real :: side_area_x, side_area_y
        real :: a_sub, a_bottom, a_sail_dummy, a_top_dummy
        integer :: nz, kz
        real(8), allocatable :: z_v(:), axp(:), axn(:), ayp(:), ayn(:)
        real(8) :: uz, vz, du8, dv8, speed8, ax8, ay8, fx8, fy8
        real(8) :: asub8, asail8, atop8, abot8, dua8, dva8, speeda8

        call init_drag_coefficients()
        if (voxel_geometry_active()) then
            draft = voxel_geometry_draft()
        else
            draft = state%H*RHO_ICE/RHO_WATER
        end if

        call depth_integrated_currents(ocean_prof, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            if (present(u_water_out)) u_water_out = 0.0
            if (present(v_water_out)) v_water_out = 0.0
            return
        end if

        call add_stokes_drift(state, u_avg, v_avg, u_prof, v_prof)
        if (present(u_water_out)) u_water_out = u_avg
        if (present(v_water_out)) v_water_out = v_avg

        if (voxel_geometry_active()) then
            ! Stage 12.17: form drag on layer-resolved vertical projections,
            ! plus skin drag on the horizontal bottom area.
            dua8 = real(u_avg - state%u, 8)
            dva8 = real(v_avg - state%v, 8)
            speeda8 = sqrt(dua8**2 + dva8**2)
            call voxel_geometry_drag_geometry(real(atan2(dva8, dua8), 4), asub8, asail8, atop8, abot8)
            call voxel_geometry_layer_areas(nz, z_v, axp, axn, ayp, ayn)
            if (nz > 0) then
                fx8 = 0.0_8; fy8 = 0.0_8
                do kz = 1, nz
                    if (axp(kz) + axn(kz) + ayp(kz) + ayn(kz) <= 0.0_8) cycle
                    call interp_current_z(z_v(kz), z_layers, u_prof, v_prof, n_layers, uz, vz)
                    du8 = uz - real(state%u, 8)
                    dv8 = vz - real(state%v, 8)
                    speed8 = sqrt(du8**2 + dv8**2)
                    ax8 = merge(axp(kz), axn(kz), du8 >= 0.0_8)
                    ay8 = merge(ayp(kz), ayn(kz), dv8 >= 0.0_8)
                    fx8 = fx8 + 0.5_8*real(RHO_WATER, 8)*real(cd_water_form_dyn, 8)* &
                        ax8*speed8*du8
                    fy8 = fy8 + 0.5_8*real(RHO_WATER, 8)*real(cd_water_form_dyn, 8)* &
                        ay8*speed8*dv8
                end do
                if (abot8 > 0.0_8) then
                    fx8 = fx8 + 0.5_8*real(RHO_WATER, 8)*real(cd_water_skin_dyn, 8)* &
                        abot8*speeda8*dua8
                    fy8 = fy8 + 0.5_8*real(RHO_WATER, 8)*real(cd_water_skin_dyn, 8)* &
                        abot8*speeda8*dva8
                end if
                fx = real(fx8, 4); fy = real(fy8, 4)
                return
            end if
            ! Fallback for an empty layer set.
            du = u_avg - state%u
            dv = v_avg - state%v
            speed_rel = sqrt(du**2 + dv**2)
            a_sub = real(asub8, 4); a_bottom = real(abot8, 4)
            fx = 0.5*RHO_WATER*(cd_water_form_dyn*a_sub + cd_water_skin_dyn*a_bottom)* &
                speed_rel*du
            fy = 0.5*RHO_WATER*(cd_water_form_dyn*a_sub + cd_water_skin_dyn*a_bottom)* &
                speed_rel*dv
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

            fx = fx + 0.5*RHO_WATER*cd_water_form_dyn*side_area_x*speed_rel*du
            fy = fy + 0.5*RHO_WATER*cd_water_form_dyn*side_area_y*speed_rel*dv
        end do

        ! Skin drag on the horizontal bottom surface.
        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)
        a_bottom = state%L*state%W
        fx = fx + 0.5*RHO_WATER*cd_water_skin_dyn*a_bottom*speed_rel*du
        fy = fy + 0.5*RHO_WATER*cd_water_skin_dyn*a_bottom*speed_rel*dv
    end subroutine compute_water_force

    ! ========================================================================
    !   Stage 12.16: linear interpolation of u/v from the ocean profile to a
    !   voxel layer centre. Values outside the profile are clamped to the nearest
    !   valid level (the profile itself is built down to the iceberg draft).
    ! ========================================================================
    subroutine interp_current_z(z, z_layers, u_prof, v_prof, n, uz, vz)
        real(8), intent(in) :: z
        real, intent(in) :: z_layers(:), u_prof(:), v_prof(:)
        integer, intent(in) :: n
        real(8), intent(out) :: uz, vz
        integer :: kk
        real(8) :: z0, z1, w

        uz = 0.0_8; vz = 0.0_8
        if (n < 1) return
        if (z <= real(z_layers(1), 8)) then
            uz = real(u_prof(1), 8); vz = real(v_prof(1), 8)
            return
        end if
        if (z >= real(z_layers(n), 8)) then
            uz = real(u_prof(n), 8); vz = real(v_prof(n), 8)
            return
        end if
        do kk = 1, n - 1
            z0 = real(z_layers(kk), 8); z1 = real(z_layers(kk + 1), 8)
            if (z >= z0 .and. z <= z1 .and. z1 > z0) then
                w = (z - z0)/(z1 - z0)
                uz = (1.0_8 - w)*real(u_prof(kk), 8) + w*real(u_prof(kk + 1), 8)
                vz = (1.0_8 - w)*real(v_prof(kk), 8) + w*real(v_prof(kk + 1), 8)
                return
            end if
        end do
        uz = real(u_prof(n), 8); vz = real(v_prof(n), 8)
    end subroutine interp_current_z

    ! ========================================================================
    !   Stage 12.17: dynamic drag coefficients. Defaults are literature
    !   constants; environment overrides are provided only for the documented
    !   +/-30% sensitivity experiments.
    ! ========================================================================
    subroutine init_drag_coefficients()
        if (cd_dyn_checked) return
        call read_env_real('ICEBERG_CD_AIR_FORM', cd_air_form_dyn)
        call read_env_real('ICEBERG_CD_WATER_FORM', cd_water_form_dyn)
        call read_env_real('ICEBERG_CD_AIR_SKIN', cd_air_skin_dyn)
        call read_env_real('ICEBERG_CD_WATER_SKIN', cd_water_skin_dyn)
        cd_dyn_checked = .true.
    end subroutine init_drag_coefficients

    subroutine read_env_real(name, value)
        character(len=*), intent(in) :: name
        real, intent(inout) :: value
        character(len=64) :: text
        integer :: ios, n
        text = ''
        call get_environment_variable(name, text, length=n)
        if (n > 0) then
            read (text, *, iostat=ios) value
            if (ios /= 0) value = value
        end if
    end subroutine read_env_real

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
        real :: a_sub, a_sail_dummy, a_bottom, a_top_dummy
        real(8) :: asub8, asail8, atop8, abot8

        if (voxel_geometry_active()) then
            draft = voxel_geometry_draft()
        else
            draft = state%H*RHO_ICE/RHO_WATER
        end if

        call depth_integrated_currents(ocean_prof, draft, u_avg, v_avg, &
                                       u_prof, v_prof, z_layers, n_layers)

        if (n_layers .eq. 0) then
            fx = 0.0
            fy = 0.0
            return
        end if

        call add_stokes_drift(state, u_avg, v_avg, u_prof, v_prof)
        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)
        if (voxel_geometry_active()) then
            call voxel_geometry_drag_geometry(atan2(dv, du), asub8, asail8, atop8, abot8)
            fx = 0.5*RHO_WATER*(cd_water_form_dyn*real(asub8, 4) + &
                 cd_water_skin_dyn*real(abot8, 4))*speed_rel*du
            fy = 0.5*RHO_WATER*(cd_water_form_dyn*real(asub8, 4) + &
                 cd_water_skin_dyn*real(abot8, 4))*speed_rel*dv
            return
        end if

        a_wet = 2.0*(state%L + state%W)*draft

        du = u_avg - state%u
        dv = v_avg - state%v
        speed_rel = sqrt(du**2 + dv**2)

        fx = 0.5*RHO_WATER*cd_water_form_dyn*a_wet*speed_rel*du
        fy = 0.5*RHO_WATER*cd_water_form_dyn*a_wet*speed_rel*dv
        a_bottom = state%L*state%W
        fx = fx + 0.5*RHO_WATER*cd_water_skin_dyn*a_bottom*speed_rel*du
        fy = fy + 0.5*RHO_WATER*cd_water_skin_dyn*a_bottom*speed_rel*dv
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



    ! ========================================================================
    !   STAGE 12.6b: STOKES DRIFT (default OFF; ICEBERG_STOKES_DRIFT=true)
    ! ========================================================================
    subroutine add_stokes_drift(state, u_avg, v_avg, u_prof, v_prof)
        type(iceberg_state), intent(in) :: state
        real, intent(inout) :: u_avg, v_avg
        real, intent(inout) :: u_prof(:), v_prof(:)
        real(8) :: hs, tp, dirw, ust, vs
        logical :: ok

        if (.not. stokes_drift_enabled()) return
        call get_wave_forcing(state%latitude, state%longitude, &
                              state%time + wave_forcing_epoch(), &
                              hs, tp, dirw, ust, vs, ok)
        if (.not. ok) return
        u_avg = u_avg + real(ust, 4)
        v_avg = v_avg + real(vs, 4)
        u_prof = u_prof + real(ust, 4)
        v_prof = v_prof + real(vs, 4)
    end subroutine add_stokes_drift

end module iceberg_dynamics
