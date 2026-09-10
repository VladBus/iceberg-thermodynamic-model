! ==============================================================================
! Модуль: iceberg_thermodynamics
! Назначение: Термодинамика айсберга — базальное, боковое и поверхностное плавление.
! Физика: Stage 9.1 §10-15 + Stage 10.1-10.4.
!   Базальное (дно):     m_b = C_BASAL * max(0, T(D) - Tf(D))                [м/с]
!   Боковое (стороны):   m_l = C_LATERAL * ⟨max(0, T - Tf)⟩_D                 [м/с]
!                         где ⟨...⟩_D = (1/D) ∫₀ᴰ max(0, T(z) - Tf(z)) dz
!   Поверхностное (верх): Stage 10.4.1 разделяет процессы (corrective):
!     m_vapor = ρ_air * C_E * U * (q_air - q_sat_ice)  [кг/(м²·с)] — сублимация/осаждение
!     Q_LH = m_vapor * L_S                               [Вт/м²] — латентный тепловой поток
!     Q_nonlatent = SW_abs + LW_down + LW_up + SH        [Вт/м²] — нефлагентная энергия
!     Q_surface = Q_nonlatent + Q_LH                     [Вт/м²] — полная поверхностная энергия
!     Q_melt = max(Q_surface, 0) при T_surface = T_melt  [Вт/м²] — энергия для плавления
!     m_surface = Q_melt / (ρ_ice * L_f)                 [м/с] — скорость плавления
!   Tf = -54.0 * S  [°C], где S — массовая доля [кг/кг] (S=0.035 → Tf=-1.89°C)
!   (Stage 10.5: заменено на EOS-80 Tf = f(S,p), см. ocean_freezing_point)
!   Подпись: m_vapor < 0 -> сублимация (Q_LH < 0, потеря энергии)
!            m_vapor > 0 -> осаждение (Q_LH > 0, источник энергии)
!
! Исправления Stage 9.3:
!   - C_BASAL, C_LATERAL: были 1e-4 [м/с] с делением на (ρᵢ·L_f),
!     стало 1e-6 [м/(с·К)] с формулой m = C * ΔT (без деления).
!   - Физический смысл: γ_T = h/(ρᵢ·L_f), где h ≈ 300 Вт/(м²·К) → γ_T ≈ 1e-6.
!
! Исправления Stage 10.4.1:
!   - Предыдущая формула Q_net_non_melt включала LH, а потом вычитала LH -> ошибка
!   - Правильная: Q_nonlatent (без LH) + Q_LH = Q_surface
!   - Sublimation (Q_LH < 0) уменьшает доступную энергию для плавления
!   - Deposition (Q_LH > 0) увеличивает доступную энергию для плавления
!
! Единицы: SI (м, с, кг, К/°C, Вт/м²).
! Точность: default real (float32).
! ==============================================================================

module iceberg_thermodynamics
    use iceberg_types
    use iceberg_forcing, only: interp_at_draft, depth_averaged_thermal_forcing
    use param, only: nat
    implicit none

    ! ========================================================================
    !   КОНСТАНТЫ ДЛЯ ПОВЕРХНОСТНОГО ТЕПЛОВОГО БАЛАНСА (адаптированы из legacy HEAT)
    ! ========================================================================
    real, parameter :: SOLAR_CONSTANT = 1353.0     ! Солнечная постоянная [Вт/м²]
    real, parameter :: CLOUD_COEFF = 0.6        ! Коэффициент затухания от облаков (legacy)
    real, parameter :: LW_EMISS = 5.4999e-8  ! Эффективная эмиссивность атмосферы [Вт/(м²·К⁴)]
    real, parameter :: LW_CLOUD_FACTOR = 0.275      ! Фактор облачности для LW
    real, parameter :: LW_HUMID_COEFF = 0.261      ! Коэффициент влажности для LW
    real, parameter :: LW_HUMID_EXP = 7.77e-4    ! Показатель влажности для LW

    ! Legacy-коэффициенты SH/LH (модель HEAT) — сохранены для справки/совместимости
    ! SH_COEFF = 1.7068  (ведёт себя как число Стэнтона, безразмерный)
    ! LH_COEFF = 0.6650735  (~443× стандартного bulk C_E ≈ 0.0015)
    ! LATENT_VAP = 2.5e6  (теплота парообразования; использовалась в legacy для обмена лед-пар)
    ! SAT_VAPOR_0 = 610.78, TETENS_A = 8.61503  (насыщение по Тетенсу для воды)
    ! T_ICE = -10.0°C (фиксированная температура поверхности, без обратной связи)
    ! Формула насыщения по воде на поверхности льда -> ошибка q_sat 5-18% при T < 0°C
    ! L_v вместо L_s -> ошибка энергии -13% для сублимации/осаждения
    ! Суммарный legacy LH = 327-403× стандартной bulk-формулы

    ! Современные bulk-коэффициенты (Stage 10.3) — используются в compute_surface_melt
    ! Теоретическая нейтральная bulk-форма: C_H = C_E = kappa^2 / ln(z/z0)^2
    !   kappa = 0.4, z = 10 м, z0 = 1e-4 м -> теоретическое C ≈ 1.21e-3
    ! В производстве используются фиксированные нейтральные bulk-коэффициенты:
    !   C_H = C_E = 1.5e-3  (документированный параметр модели)
    !   НЕ выводятся из kappa^2/ln(z/z0)^2 при z0 = 1e-4 м
    ! CP_AIR = 1004.0 Дж/(кг·К), L_S = 2.835e6 Дж/кг (сублимация при 0°C)
    ! Насыщение над льдом: формула Мерфи и Купа (2005)
    ! Знаки: Q_SH > 0 = атмосфера нагревает айсберг
    !        Q_LH > 0 = поток пара отдаёт энергию поверхности
    ! Stage 10.3: Q_LH — ТОЛЬКО ЭНЕРГЕТИЧЕСКИЙ ПОТОК; изменения массы от сублимации/осаждения нет

    real, parameter :: SH_COEFF = 1.7068     ! Legacy: Stanton number (dimensionless)
    real, parameter :: LH_COEFF = 0.6650735  ! Legacy: Dalton number (dimensionless)
    real, parameter :: LATENT_VAP = 2.5e6      ! Legacy: latent heat of vaporization [Дж/кг]
    real, parameter :: GAS_CONST_AIR = 287.0      ! Газовая постоянная сухого воздуха [Дж/(кг·К)]
    real, parameter :: SAT_VAPOR_0 = 610.78     ! Насыщенное парциальное давление при 0°C [Па]
    real, parameter :: TETENS_A = 8.61503    ! Константа Тетенса для e_sat
    real, parameter :: WATER_ALBEDO = 0.06       ! Альбедо воды
    real, parameter :: WATER_EMISS = 0.97       ! Эмиссивность воды

    ! ========================================================================
    !   АТМОСФЕРНАЯ ПРОПУСКАЮЩАЯ СПОСОБНОСТЬ КОРОТКОВОЛНОВОЙ РАДИАЦИИ (Stage 10.1.2)
    ! ========================================================================
    ! Широкополосная параметризация по входным данным ERA5 (tcc, t2m, d2m, msl).
    ! Основана на простых физических приближениях (Релей, водяной пар, аэрозоли).
    ! Пропускание облаков: линейно по tcc.
    ! НЕ используются ERA5 SSRD/STRD — только офлайн-параметризация.
    ! Коэффициенты документированы ниже; legacy-эмпирические значения отмечены.
    ! ========================================================================
    real, parameter :: TAU_RAYLEIGH_0 = 0.09        ! Оптическая толщина Релея на уровне моря (p=1013.25 hPa)
    real, parameter :: AEROSOL_TRANS_ARCTIC = 0.93  ! Атмосферная прозрачность от аэрозолей (Arctic background, legacy empirical)
    real, parameter :: CLOUD_TRANS_COEFF = 0.75     ! Коэффициент облачной пропускания: T_cloud = 1 - C*tcc (overcast ~25% of clear)
    real, parameter :: WV_ABSORP_COEFF = 0.077      ! Коэффициент поглощения водяным паром (Lacis & Hansen 1974 approx)
    real, parameter :: WV_ABSORP_EXP = 0.3          ! Показатель для водяного пара (Lacis & Hansen 1974)
    real, parameter :: PRECIP_WATER_SCALE = 0.1     ! Масштаб для оценки выпадаемой воды из e_vap [cm/(hPa)] (empirical)

    ! ========================================================================
    !   АСТРОНОМИЧЕСКИЕ КОНСТАНТЫ (Stage 10.1.1)
    ! ========================================================================
    real, parameter :: DEG2RAD = 0.017453292519943295  ! π/180
    real, parameter :: RAD2DEG = 57.29577951308232     ! 180/π
    real, parameter :: SECONDS_PER_DAY = 86400.0
    real, parameter :: HOURS_PER_DAY = 24.0
    real, parameter :: DEG_PER_HOUR = 15.0             ! 360°/24h

contains

    ! ========================================================================
    !   СОЛНЕЧНАЯ ГЕОМЕТРИЯ (Stage 10.1.1)
    ! ========================================================================
    ! Вычисляет солнечную геометрию для заданного времени и позиции.
    ! Использует формулу Спенсера (1971) для склонения Солнца.
    !
    ! Аргументы:
    !   year, month, day, hour  - референс-дата (UTC) начала моделирования
    !   model_time_sec          - модельное время [с] от референс-даты
    !   latitude_deg, longitude_deg - географическая позиция [°]
    !   cos_zenith              - cos(солнечный зенитный угол) (выход)
    !   declination_rad         - солнечное склонение [рад] (выход, optional)
    !   hour_angle_rad          - часовой угол [рад] (выход, optional)
    ! ========================================================================
    subroutine solar_geometry(year, month, day, hour, &
                              model_time_sec, &
                              latitude_deg, longitude_deg, &
                              cos_zenith, &
                              declination_rad, hour_angle_rad)
        integer, intent(in) :: year, month, day, hour
        real, intent(in) :: model_time_sec
        real, intent(in) :: latitude_deg, longitude_deg
        real, intent(out) :: cos_zenith
        real, intent(out), optional :: declination_rad, hour_angle_rad

        real :: current_time_sec
        integer :: day_of_year
        real :: gamma, decl_rad, eq_time_min
        real :: utc_hour, local_solar_time, hour_angle_deg, hour_angle_rad_local
        real :: lat_rad
        integer :: days_in_month(12)
        integer :: m_local, d_local
        real :: total_days

        ! Дни в месяцах (невисокосный год, корректировка для високосных ниже)
        days_in_month = (/31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31/)

        ! Текущее абсолютное время в секундах от начала референс-дня
        current_time_sec = real(hour)*3600.0 + model_time_sec

        ! Вычисление дня года (1-365/366)
        ! Учитываем полные дни, прошедшие от референс-даты
        total_days = current_time_sec/SECONDS_PER_DAY
        day_of_year = day + int(total_days)

        ! Корректировка для високосного года
        if (mod(year, 4) .eq. 0 .and. (mod(year, 100) .ne. 0 .or. mod(year, 400) .eq. 0)) then
            days_in_month(2) = 29
        end if

        ! Нормализация day_of_year в диапазон 1..365(366)
        do while (day_of_year .gt. 365 + (days_in_month(2) - 28))
            day_of_year = day_of_year - 365 - (days_in_month(2) - 28)
        end do
        do while (day_of_year .lt. 1)
            day_of_year = day_of_year + 365 + (days_in_month(2) - 28)
        end do

        ! Угол Γ = 2π * (day_of_year - 1) / 365
        gamma = 2.0*3.141592653589793*real(day_of_year - 1)/365.0

        ! Склонение Солнца по Спенсеру (1971) [рад]
        decl_rad = 0.006918 - 0.399912*cos(gamma) + 0.070257*sin(gamma) &
                   - 0.006758*cos(2.0*gamma) + 0.000907*sin(2.0*gamma) &
                   - 0.002697*cos(3.0*gamma) + 0.00148*sin(3.0*gamma)

        ! Уравнение времени (минуты) - приближение Спенсера
        eq_time_min = 229.18*(0.000075 + 0.001868*cos(gamma) - 0.032077*sin(gamma) &
                              - 0.014615*cos(2.0*gamma) - 0.040849*sin(2.0*gamma))

        ! UTC час с дробной частью
        utc_hour = real(hour) + mod(current_time_sec, SECONDS_PER_DAY)/3600.0

        ! Местное солнечное время = UTC + longitude/15 + eq_time/60
        ! longitude > 0 на востоке
        local_solar_time = utc_hour + longitude_deg/DEG_PER_HOUR + eq_time_min/60.0

        ! Часовой угол H = 15° * (local_solar_time - 12) [градусы]
        hour_angle_deg = DEG_PER_HOUR*(local_solar_time - 12.0)

        ! Нормализация часового угла в [-180, 180]
        do while (hour_angle_deg .gt. 180.0)
            hour_angle_deg = hour_angle_deg - 360.0
        end do
        do while (hour_angle_deg .lt. -180.0)
            hour_angle_deg = hour_angle_deg + 360.0
        end do

        hour_angle_rad_local = hour_angle_deg*DEG2RAD
        lat_rad = latitude_deg*DEG2RAD

        ! cos(zenith) = sin(φ)sin(δ) + cos(φ)cos(δ)cos(H)
      cos_zenith = sin(lat_rad)*sin(decl_rad) + cos(lat_rad)*cos(decl_rad)*cos(hour_angle_rad_local)

        ! Ограничение диапазона [-1, 1] для числовой стабильности
        cos_zenith = max(-1.0, min(1.0, cos_zenith))

        ! Опциональные выходы
        if (present(declination_rad)) declination_rad = decl_rad
        if (present(hour_angle_rad)) hour_angle_rad = hour_angle_rad_local
    end subroutine solar_geometry

    ! ========================================================================
    !   ГЛАВНАЯ ПОДПРОГРАММА ТЕРМОДИНАМИКИ
    ! ========================================================================
    ! Вызывает три компонента плавления и сохраняет результаты в diag.
    !
    ! Аргументы:
    !   state       - состояние айсберга (intent(inout), T_surface обновляется)
    !   dt          - шаг по времени [с] (intent(in))
    !   ocean_prof  - профиль океана (intent(in))
    !   atmos       - атмосферный форсинг (intent(in))
    !   diag        - диагностики (intent(inout), обновляются m_*, q_net, t_surface)
    ! ========================================================================
    subroutine iceberg_thermodynamics_step(state, dt, ocean_prof, atmos, diag)
        type(iceberg_state), intent(inout) :: state
        real, intent(in) :: dt
        type(ocean_profile), intent(in) :: ocean_prof
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag

        real :: t_draft, s_draft, tf_draft
        real :: delta_t_basal, delta_t_lateral_avg
        real :: m_basal, m_lateral, m_surface
        real :: q_net

        ! 1. Базальное плавление
        ! Характерная длина для базального плавления = L (длина в направлении X)
        call compute_basal_melt(ocean_prof, diag%draft, state%L, state%u, state%v, &
                                t_draft, s_draft, tf_draft, &
                                delta_t_basal, m_basal, &
                                diag%t_interface, diag%s_interface)

        diag%t_draft = t_draft
        diag%s_draft = s_draft
        diag%tf_draft = tf_draft
        diag%delta_t_ocean = t_draft - tf_draft
        diag%m_basal = m_basal

        ! 2. Боковое плавление
        call compute_lateral_melt(ocean_prof, diag%draft, &
                                  delta_t_lateral_avg, m_lateral)

        diag%m_lateral = m_lateral

        ! 3. Поверхностное плавление
        call compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                                  nat(1), nat(2), nat(3), nat(4))

        diag%q_net_surface = q_net
        diag%m_surface = m_surface
    end subroutine iceberg_thermodynamics_step

    ! ========================================================================
    !   БАЗАЛЬНОЕ ПЛАВЛЕНИЕ (Stage 10.6 — физически обоснованное, bulk formulation)
    ! ========================================================================
    ! Использует bulk-формулировку теплообмена (Weeks & Campbell 1973;
    ! Eckert & Drake 1959; Martin & Adcroft 2010) с относительной скоростью
    ! на глубине осадки:
    !
    !   U_rel = sqrt((u_water(D) - u_ice)^2 + (v_water(D) - v_ice)^2)
    !   Re = U_rel * L_char / ν
    !   Nu = 0.037 * Re^0.8 * Pr^(1/3)   (турбулентный режим, Re > Re_crit)
    !   Nu = 0.664 * Re^0.5 * Pr^(1/3)   (ламинарный режим, Re <= Re_crit)
    !   γ_T = Nu * k / L_char          [Вт/(м²·К)]
    !   Q_basal = γ_T * (T(D) - Tf(D)) [Вт/м²]
    !   m_basal = Q_basal / (ρ_ice * L_f) [м/с]
    !
    ! Где:
    !   k = THERMAL_CONDUCTIVITY [Вт/(м·К)]
    !   Pr = PRANDTL_NUMBER [безразм.]
    !   ν = KINEMATIC_VISCOSITY [м²/с]
    !   Tf = EOS-80 freezing point (Stage 10.5)
    !   L_char = характеристическая длина для Re (передаётся как аргумент)
    !
    ! ВАЖНЫЕ ОГРАНИЧЕНИЯ (Stage 10.6):
    ! 1. L_char для базального плавления должен быть streamwise length —
    !    длина айсберга в напрвлении U_rel. Модель НЕ имеет ориентации,
    !    state%L всегда вдоль X. Вызывающий код передаёт state%L,
    !    что верно ТОЛЬКО если U_rel || X. Для общего случая — приближение.
    ! 2. При U_rel = 0 возвращает m_basal = 0 (нет турбулентного теплообмена).
    !    Натуральная конвекция/проводимость не реализована (Stage 10.7+).
    ! 3. Three-equation формулировка (H&J99, J10) даёт γ_T в ~5 раз больше
    !    (FitzMaurice & Stern 2018). Bulk подходит для L < радиуса деформации (~15 км).
    ! 4. Переход ламинарный/турбулентный при Re_crit = 5e5 (flat plate).
    !
    ! Аргументы:
    !   prof        - профиль океана (intent(in)), содержит u_rel на глубине D
    !   draft       - осадка [м] (intent(in))
    !   l_char      - характерная длина для Re (L для базального) [м] (intent(in))
    !   u_ice, v_ice - скорость айсберга [м/с] (intent(in))
    !   t_draft     - температура на осадке [°C] (выход)
    !   s_draft     - соленость на осадке [кг/кг] (выход)
    !   tf_draft    - точка замерзания на осадке [°C] (выход)
    !   delta_t     - T - Tf [°C] (выход)
    !   m_basal     - базальная скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine compute_basal_melt(prof, draft, l_char, u_ice, v_ice, &
                                  t_draft, s_draft, tf_draft, delta_t, m_basal, &
                                  t_interface, s_interface)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real, intent(in) :: l_char
        real, intent(in) :: u_ice, v_ice
        real, intent(out) :: t_draft, s_draft, tf_draft
        real, intent(out) :: delta_t, m_basal
        real, intent(out), optional :: t_interface, s_interface

        real :: u_rel_draft, gamma_t, q_basal
        real :: u_draft, v_draft
        real :: gamma_t_vel, gamma_s_vel
        real :: t_iface, s_iface

        t_draft = interp_at_draft(prof, draft, "temp")
        s_draft = interp_at_draft(prof, draft, "salt")

        tf_draft = ocean_freezing_point(s_draft, draft)

        delta_t = t_draft - tf_draft

        if (basal_melt_scheme .eq. BASAL_MELT_SCHEME_THREE_EQUATION) then
            ! ================================================================
            !   THREE-EQUATION CLOSURE (Stage 10.10, Holland & Jenkins 1999;
            !   Jenkins et al. 2010). Базовый baseline-путь НЕ меняется.
            ! ================================================================
            if (delta_t .gt. 0.0) then
                ! Относительная скорость на глубине осадки (как в baseline)
                if (allocated(prof%u_rel)) then
                    u_rel_draft = interp_at_draft(prof, draft, "u_rel")
                else
                    u_draft = interp_at_draft(prof, draft, "u")
                    v_draft = interp_at_draft(prof, draft, "v")
                    u_rel_draft = sqrt((u_draft - u_ice)**2 + (v_draft - v_ice)**2)
                end if

                ! U-представление трансферных скоростей (J2010 Table 2):
                !   gamma_T = K_T * U_rel  [м/с],  gamma_S = K_S * U_rel  [м/с]
                gamma_t_vel = THREE_EQ_KT*u_rel_draft
                gamma_s_vel = THREE_EQ_KS*u_rel_draft

                call solve_three_equation_interface(t_draft, s_draft, draft, &
                                                    u_rel_draft, &
                                                    gamma_t_vel, gamma_s_vel, &
                                                    T_ICE, .true., &
                                                    t_iface, s_iface, m_basal)

                ! Защита от числового шума (как в baseline)
                if (m_basal .lt. MELT_RATE_MIN) then
                    m_basal = 0.0
                    t_iface = tf_draft
                    s_iface = s_draft
                end if
            else
                m_basal = 0.0
                delta_t = 0.0
                t_iface = tf_draft
                s_iface = s_draft
            end if
        else
            ! ================================================================
            !   BASELINE BULK CLOSURE (Stage 10.6) — БЕЗ ИЗМЕНЕНИЙ
            ! ================================================================
            if (delta_t .gt. 0.0) then
                ! Относительная скорость на глубине осадки
                ! Если профиль содержит u_rel, используем его, иначе вычисляем из u,v
                if (allocated(prof%u_rel)) then
                    u_rel_draft = interp_at_draft(prof, draft, "u_rel")
                else
                    ! Вычисляем из u и v на глубине осадки
                    u_draft = interp_at_draft(prof, draft, "u")
                    v_draft = interp_at_draft(prof, draft, "v")
                    u_rel_draft = sqrt((u_draft - u_ice)**2 + (v_draft - v_ice)**2)
                end if

                ! Теплообменный коэффициент через bulk-формулировку
                call ocean_heat_transfer_coeff(u_rel_draft, l_char, gamma_t)

                ! Тепловой флюс через основание
                q_basal = gamma_t*delta_t

                ! Скорость плавления [м/с]
                m_basal = q_basal/(RHO_ICE*LATENT_HEAT)

                ! Защита от числового шума
                if (m_basal .lt. MELT_RATE_MIN) m_basal = 0.0

                ! Диагностика границы (bulk: интерфейс = дальнее поле)
                t_iface = t_draft
                s_iface = s_draft
            else
                m_basal = 0.0
                delta_t = 0.0
                t_iface = tf_draft
                s_iface = s_draft
            end if
        end if

        if (present(t_interface)) t_interface = t_iface
        if (present(s_interface)) s_interface = s_iface
    end subroutine compute_basal_melt

    ! ========================================================================
    !   ТРЁХЧЛЕННОЕ ЗАМЫКАНИЕ ИНТЕРФЕЙСА ЛЁД-ОКЕАН (Stage 10.10)
    ! ========================================================================
    ! Физика: три уравнения интерфейса (Holland & Jenkins 1999; Jenkins et al. 2010):
    !   (I)   T_B = Tf(S_B, P)                       — точка замерзания на границе (EOS-80)
    !   (II)  ρ_w c_w γ_T (T_w − T_B) = m (ρ_i L_f + ρ_i c_i (T_B − T_i))
    !                                          — баланс тепла: океанский поток =
    !                                            скрытое тепло + теплопроводность в лёд
    !   (III) ρ_w γ_S (S_w − S_B) = ρ_i·m·S_B       — баланс соли (S_i=0; Stage 10.10.1)
    !
    ! Переменные: m — скорость плавления [м/с] (лёд-кадр: dH/dt = −m), T_B — температура
    ! интерфейса [°C], S_B — соленость интерфейса [кг/кг].
    ! Трансферные скорости γ_T, γ_S [м/с] ПЕРЕДАЮТСЯ ВЫЗЫВАЮЩИМ (производственные:
    ! γ_T = K_T·U_rel, γ_S = K_S·U_rel по J2010 Table 2; тесты могут подавать
    ! канонические значения H&J99 Table 1). Скрытое и кондуктивное слагаемые —
    ! в лёд-кадре (ρ_i): ρ_i=910, L_f=3.34e5, c_i=2009.0 (H&J99 c_i).
    !
    ! Stage 10.10.1 (коррекция): скорость таяния m определена ВО ЛЬДУ-КАДРЕ, поэтому
    ! плотность льда входит в баланс соли ТАК ЖЕ, как в баланс тепла:
    !     ρ_w γ_S (S_w − S_B) = ρ_i·m·S_B   (см. MOM6 mom_ice_shelf, PISM ocean-th,
    !     MITgcm shelfice, H&J99 Eq.4 — независимые источники).
    ! Делением на ρ_w: γ_S (S_w − S_B) = (ρ_i/ρ_w)·m·S_B = F_fw·S_B,
    ! где F_fw = (ρ_i/ρ_w)·m — объёмный поток талой воды в океанском кадре.
    !
    ! Редукция: из (III) S_B = γ_S S_w/[γ_S + (ρ_i/ρ_w)·m] — аналитически; подстановка в
    ! (II) даёт уравнение F(m) = ρ_w c_w γ_T (T_w − T_B(m)) − m·[ρ_i L_f + ρ_i c_i(T_B(m)−T_i)] = 0.
    ! F(0) = ρ_w c_w γ_T (T_w − Tf(S_w)) ≥ 0 (иначе melting нет), F(m)→−∞ при m→∞,
    ! F строго убывает (ρ_i·L_f слагаемое доминирует) → единственный корень, бисекция.
    !
    ! Крайние случаи:
    !   u_rel ≤ 0 или γ_T ≤ 0            → m=0, S_B=S_w, T_B=Tf(S_w,P) (нет потока;
    !                                       натуральная конвекция не реализована — limitation)
    !   T_w ≤ Tf(S_w, P)                 → m=0, S_B=S_w, T_B=Tf(S_w,P)
    !   S_w ≤ 0 (пресная)                → солевой поток нулевой; тепло-уравнение с S_B=0
    !   γ_S ≤ 0                          → S_B=S_w, тепло-уравнение без фрезерования
    !
    ! Параметры констант: ρ_w=RHO_WATER=1028, c_w=CP_SEAWATER=3974.0 (H&J99/J2010),
    ! ρ_i=RHO_ICE=910, L_f=LATENT_HEAT=3.34e5, c_i=CP_ICE_3EQ=2009.0, T_i=T_ICE=−10°C
    ! (модельно-выбранная постоянная внутренней температуры льда; H&J99 учли бы явную
    ! теплопроводность в толще шельфа, здесь — фиксированная внутренняя температура).
    ! Кондуктивное слагаемое можно отключить (use_conduction=.false.) для тестов.
    !
    ! Аргументы:
    !   t_w, s_w        - дальнее поле на осадке [°C, кг/кг] (intent(in))
    !   depth_m         - глубина осадки [м] — для давления в Tf (intent(in))
    !   u_rel           - относительная скорость [м/с] (intent(in), только для краёв)
    !   gamma_t,gamma_s - скорости обмена [м/с] (intent(in))
    !   t_ice           - температура внутри льда [°C] (intent(in))
    !   use_conduction  - включать ли линеаризованную теплопроводность (intent(in))
    !   t_interface     - T_B [°C] (выход)
    !   s_interface     - S_B [кг/кг] (выход)
    !   m_basal         - скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine solve_three_equation_interface(t_w, s_w, depth_m, u_rel, &
                                              gamma_t, gamma_s, t_ice, use_conduction, &
                                              t_interface, s_interface, m_basal)
        real, intent(in) :: t_w
        real, intent(in) :: s_w
        real, intent(in) :: depth_m
        real, intent(in) :: u_rel
        real, intent(in) :: gamma_t
        real, intent(in) :: gamma_s
        real, intent(in) :: t_ice
        logical, intent(in) :: use_conduction
        real, intent(out) :: t_interface
        real, intent(out) :: s_interface
        real, intent(out) :: m_basal

        real :: tf_w, l_heat, ocean_flux_coeff
        real :: s_b, t_b, f_val, m_lo, m_hi, m_mid, m_est
        integer :: iter

        tf_w = ocean_freezing_point(s_w, depth_m)

        ! ---- Края: нет потока → m = 0, интерфейс = замерзание дальнего поля ----
        if (u_rel .le. 0.0 .or. gamma_t .le. 0.0 .or. t_w .le. tf_w) then
            m_basal = 0.0
            s_interface = s_w
            t_interface = tf_w
            return
        end if

        ! ---- Край: пресная вода (S_w ≤ 0): солевой поток нулевой, тепло-уравнение ----
        if (s_w .le. 0.0) then
            s_interface = 0.0
            t_interface = ocean_freezing_point(0.0, depth_m)
            l_heat = RHO_ICE*LATENT_HEAT
            if (use_conduction) l_heat = l_heat + RHO_ICE*CP_ICE_3EQ*max(t_interface - t_ice, 0.0)
            ocean_flux_coeff = RHO_WATER*CP_SEAWATER*gamma_t*(t_w - t_interface)
            if (ocean_flux_coeff .gt. 0.0 .and. l_heat .gt. 0.0) then
                m_basal = ocean_flux_coeff/l_heat
            else
                m_basal = 0.0
            end if
            return
        end if

        ! ---- Край: γ_S ≤ 0: нет фрезерования, тепло-уравнение с S_B = S_w ----
        if (gamma_s .le. 0.0) then
            s_interface = s_w
            t_interface = tf_w
            l_heat = RHO_ICE*LATENT_HEAT
            if (use_conduction) l_heat = l_heat + RHO_ICE*CP_ICE_3EQ*max(tf_w - t_ice, 0.0)
            ocean_flux_coeff = RHO_WATER*CP_SEAWATER*gamma_t*(t_w - tf_w)
            if (ocean_flux_coeff .gt. 0.0 .and. l_heat .gt. 0.0) then
                m_basal = ocean_flux_coeff/l_heat
            else
                m_basal = 0.0
            end if
            return
        end if

        ! ---- Основной случай: бисекция по m ∈ [0, m_hi] ----
        ! F(0) = ρ_w c_w γ_T (T_w − Tf(S_w)) > 0 (гарантировано t_w > tf_w выше)
        m_lo = 0.0
        m_est = RHO_WATER*CP_SEAWATER*gamma_t*(t_w - tf_w)/(RHO_ICE*LATENT_HEAT)
        m_hi = max(m_est, 1.0e-9)

        ! Расширение верхней границы, пока F(m_hi) > 0
        iter = 0
        do while (.true.)
            s_b = gamma_s*s_w/(gamma_s + RHO_ICE_WATER_RATIO*m_hi)
            t_b = ocean_freezing_point(s_b, depth_m)
            l_heat = RHO_ICE*LATENT_HEAT
            if (use_conduction) l_heat = l_heat + RHO_ICE*CP_ICE_3EQ*max(t_b - t_ice, 0.0)
            f_val = RHO_WATER*CP_SEAWATER*gamma_t*(t_w - t_b) - m_hi*l_heat
            if (f_val .le. 0.0 .or. iter .ge. 60) exit
            m_hi = m_hi*2.0
            iter = iter + 1
        end do

        ! Бисекция (60 итераций достаточно для float32-конвергенции)
        do iter = 1, 60
            m_mid = 0.5*(m_lo + m_hi)
            s_b = gamma_s*s_w/(gamma_s + RHO_ICE_WATER_RATIO*m_mid)
            t_b = ocean_freezing_point(s_b, depth_m)
            l_heat = RHO_ICE*LATENT_HEAT
            if (use_conduction) l_heat = l_heat + RHO_ICE*CP_ICE_3EQ*max(t_b - t_ice, 0.0)
            f_val = RHO_WATER*CP_SEAWATER*gamma_t*(t_w - t_b) - m_mid*l_heat
            if (f_val .gt. 0.0) then
                m_lo = m_mid
            else
                m_hi = m_mid
            end if
        end do

        m_basal = 0.5*(m_lo + m_hi)
        s_interface = gamma_s*s_w/(gamma_s + RHO_ICE_WATER_RATIO*m_basal)
        t_interface = ocean_freezing_point(s_interface, depth_m)
    end subroutine solve_three_equation_interface

    ! ========================================================================
    !   БОКОВОЕ ПЛАВЛЕНИЕ (Stage 9.1 §14, Method A — legacy formula)
    ! ========================================================================
    ! m_l = C_LATERAL * ⟨max(0, T - Tf)⟩_D
    ! Глубинно-усреднённое термическое задействование вычисляется через
    ! depth_averaged_thermal_forcing (интеграл по осадке с экстраполяцией).
    ! Stage 10.7: будет заменено на физически обоснованную параметризацию
    ! с использованием U_rel(z) и bulk-формулировки теплообмена.
    ! По Weeks & Campbell (1973) для бокового плавления L_char = D (черновик).
    !
    ! Аргументы:
    !   prof            - профиль океана (intent(in))
    !   draft           - осадка [м] (intent(in))
    !   delta_t_avg     - ⟨ΔT⟩_D [°C] (выход)
    !   m_lateral       - боковая скорость плавления [м/с] (выход)
    ! ========================================================================
    subroutine compute_lateral_melt(prof, draft, delta_t_avg, m_lateral)
        type(ocean_profile), intent(in) :: prof
        real, intent(in) :: draft
        real, intent(out) :: delta_t_avg, m_lateral

        delta_t_avg = depth_averaged_thermal_forcing(prof, draft)

        if (delta_t_avg .gt. 0.0) then
            m_lateral = C_LATERAL*delta_t_avg
        else
            m_lateral = 0.0
            delta_t_avg = 0.0
        end if
    end subroutine compute_lateral_melt

    ! ========================================================================
    !   ПОВЕРХНОСТНОЕ ПЛАВЛЕНИЕ С ПРОГНОСТИЧЕСКОЙ ТЕМПЕРАТУРОЙ (Stage 10.2 + 10.4.1)
    ! ========================================================================
    ! Stage 10.4.1 КОРРЕКТНОЕ РАСПРЕДЕЛЕНИЕ ЭНЕРГИИ:
    ! Q_nonlatent = SW_abs + LW_down + LW_up + SH       (без LH)
    ! Q_LH = m_vapor * L_S                               [Вт/м²]
    ! Q_surface = Q_nonlatent + Q_LH                     [полная энергия поверхности]
    ! C_eff dT_surface/dt = Q_surface   (T_surface < T_melt)
    !
    ! Логика фазового перехода (корректная):
    !   если T_surface < T_melt:
    !       dT = Q_surface * dt / C_eff
    !       T_surface_new = T_surface + dT
    !       если T_surface_new >= T_melt:
    !           excess_energy = Q_surface - C_eff * (T_melt - T_surface) / dt
    !           Q_melt = max(excess_energy, 0)  ! остаток после достижения T_melt
    !           m_surface = Q_melt / (rho_ice * L_f)
    !           T_surface = T_melt
    !       иначе:
    !           m_surface = 0
    !   иначе:  ! T_surface >= T_melt
    !       T_surface = T_melt
    !       Q_melt = max(Q_surface, 0)  ! вся Q_surface доступна для плавления
    !       m_surface = Q_melt / (rho_ice * L_f)
    !
    ! Массовый поток пара (Stage 10.4):
    !   m_vapor = rho_air * C_E * U * (q_air - q_sat_ice)  [кг/(м²·с)]
    !   Q_LH = m_vapor * L_S
    !   Знак: m_vapor < 0 -> сублимация (потеря массы, Q_LH < 0 — сток энергии)
    !         m_vapor > 0 -> осаждение (прирост массы, Q_LH > 0 — источник энергии)
    !
    ! Компоненты:
    !   SW_abs = SW_down * (1 - albedo)
    !   LW_down = LW_EMISS * t_air^4 * (1 + LW_CLOUD_FACTOR*tcc) * ...
    !   LW_up = -ε_ice * σ * t_surf^4
    !   SH = rho_air * CP_AIR * C_H * |V| * (t_air - t_surf)
    !   LH = rho_air * L_S * C_E * |V| * (q_air - q_sat_ice)
    !   t_surf = state%T_surface [°C], для радиации переводится в К
    !
    ! Аргументы:
    !   state       - состояние айсберга с T_surface [°C] (intent(inout), обновляется)
    !   atmos       - атмосферный форсинг
    !   diag        - диагностики (обновляются q_net_surface, t_surface, m_vapor)
    !   q_net       - суммарный тепловой поток [Вт/м²] (выход, остаток после плавления)
    !   m_surface   - скорость поверхностного таяния [м/с] (выход)
    !   year, month, day, hour - референс-дата (UTC)
    ! ========================================================================
    subroutine compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, &
                                    year, month, day, hour)
        type(iceberg_state), intent(inout) :: state
        type(atmos_forcing), intent(in) :: atmos
        type(iceberg_diagnostics), intent(inout) :: diag
        real, intent(out) :: q_net, m_surface
        real, intent(in) :: dt
        integer, intent(in) :: year, month, day, hour

        real :: t_air_k, t_surf_k, t_dew_k
        real :: p_atm, rho_air_local, q_air, q_sat
        real :: wind_speed
        real :: sw_down, lw_down, lw_up, sh_flux, lh_flux
        real :: cos_zenith
        real :: albedo
        real :: e_sat_air, e_sat_dew, rh, e_vap
        real :: sw_absorbed
        ! --- Stage 10.1.2: диагностика ослабления SW в атмосфере ---
        real :: sw_toa
        real :: air_mass, tau_rayleigh
        real :: t_rayleigh, t_water_vap, t_aerosol, t_clear, t_cloud
        real :: precipitable_water_cm
        ! --- Stage 10.2: прогностическая температура поверхности ---
        real :: c_eff, excess_energy
        real :: t_surf_new
        ! --- Stage 10.4: массовый поток пара и распределение энергии ---
        real :: m_vapor, q_melt
        real :: q_nonlatent, q_lh, q_surface

        ! Входные параметры
        t_air_k = atmos%t2m
        t_dew_k = atmos%d2m

        p_atm = atmos%msl
        rho_air_local = p_atm/(GAS_CONST_AIR*t_air_k)  ! ρ_air = p/(R*T) [кг/м³]

        wind_speed = sqrt(atmos%u10**2 + atmos%v10**2)

        ! Эффективная теплоёмкость поверхностного слоя
        c_eff = RHO_ICE*C_ICE*H_EFF  ! Дж/(м² К)

        ! === КОРОТКОВОЛНОВАЯ РАДИАЦИЯ (Shortwave) ===
        ! Солнечная геометрия (Stage 10.1.1): астрономическая формула
        call solar_geometry(year, month, day, hour, &
                            state%time, &
                            state%latitude, state%longitude, &
                            cos_zenith)

        ! === ДАВЛЕНИЕ ВОДЯНОГО ПАРА В АТМОСФЕРЕ (нужно всегда для LH, не зависит от солнечной геометрии) ===
        ! Вычисляем e_vap, rh, q_air до ветвления по SW, чтобы они были валидны днём и ночью
        e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
        e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
        rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))  ! относительная влажность [0-1]
        e_vap = rh*e_sat_air  ! [Па]
        q_air = 0.622*e_vap/p_atm

        ! Полярная ночь/день: cos_zenith <= 0 -> солнечной радиации нет
        if (cos_zenith .le. 0.0) then
            sw_down = 0.0
            sw_toa = 0.0
            t_clear = 0.0
            t_cloud = 0.0
        else
            ! === ОСЛАБЛЕНИЕ В АТМОСФЕРЕ (Stage 10.1.2) ===
            ! Широкополосная параметризация: SW_down = S0 * cos_zenith * T_clear * T_cloud
            ! где:
            !   S0 * cos_zenith       = поток солнечной радиации на горизонтальную поверхность
            !   T_clear               = пропускание атмосферы при ясном небе
            !   T_cloud               = пропускание облаков (функция от tcc)
            !
            ! Компоненты пропускания при ясном небе:
            !   T_rayleigh  = exp(-tau_rayleigh * air_mass)  ! релеевское рассеяние
            !   T_water_vap = 1 - WV_ABSORP_COEFF * w^WV_ABSORP_EXP  ! поглощение водяным паром
            !   T_aerosol   = AEROSOL_TRANS_ARCTIC  ! фоновый аэрозоль (эмпирический)
            !   T_clear = T_rayleigh * T_water_vap * T_aerosol
            !
            ! Пропускание облаков:
            !   T_cloud = 1 - CLOUD_TRANS_COEFF * tcc
            !   сплошная облачность (tcc=1) -> ~25% от потока при ясном небе
            !
            ! Все пропускания ограничены [0, 1].
            ! Итоговый SW_down ограничен <= потоку на верхней границе атмосферы.

            ! Поток солнечной радиации на верхней границе атмосферы
            ! на горизонтальную поверхность
            sw_toa = SOLAR_CONSTANT*cos_zenith

            ! Воздушная масса (аппроксимация Kasten & Young 1989 для больших зенитных углов)
            ! m = 1 / (cos_zenith + 0.50572 * (96.07995 - zenith_deg)^-1.6364)
            ! Для простоты используем m = 1/cos_zenith с ограничением 40 (зенит ~88.5°)
            air_mass = 1.0/cos_zenith
            if (air_mass .gt. 40.0) air_mass = 40.0

            ! Пропускание релеевского рассеяния
            ! tau_rayleigh масштабируется по приземному давлению
            tau_rayleigh = TAU_RAYLEIGH_0*(p_atm/101325.0)
            t_rayleigh = exp(-tau_rayleigh*air_mass)
            t_rayleigh = max(0.0, min(1.0, t_rayleigh))

            ! Поглощение водяным паром (широкополосная аппроксимация Lacis & Hansen 1974)
            ! Содержание осаждаемой воды w [см] оценивается по приземному
            ! давлению водяного пара
            ! w = PRECIP_WATER_SCALE * (e_vap / 100.0) * (101325.0 / p_atm)
            ! где e_vap [Па] -> гПа через /100
            precipitable_water_cm = PRECIP_WATER_SCALE*(e_vap/100.0)*(101325.0/p_atm)
            precipitable_water_cm = max(0.0, precipitable_water_cm)

            ! T_water_vap = 1 - WV_ABSORP_COEFF * w^WV_ABSORP_EXP
            t_water_vap = 1.0 - WV_ABSORP_COEFF*(precipitable_water_cm**WV_ABSORP_EXP)
            t_water_vap = max(0.0, min(1.0, t_water_vap))

            ! Пропускание аэрозоля (арктический фон, эмпирическое)
            t_aerosol = AEROSOL_TRANS_ARCTIC

            ! Пропускание при ясном небе
            t_clear = t_rayleigh*t_water_vap*t_aerosol
            t_clear = max(0.0, min(1.0, t_clear))

            ! Пропускание облаков: линейно по tcc
            t_cloud = 1.0 - CLOUD_TRANS_COEFF*atmos%tcc
            t_cloud = max(0.0, min(1.0, t_cloud))

            ! Итоговая нисходящая SW у поверхности
            sw_down = sw_toa*t_clear*t_cloud

            ! Проверка ограничения: SW_down не может превышать поток на TOA
            sw_down = min(sw_down, sw_toa)
            sw_down = max(0.0, sw_down)
        end if

        albedo = ALBEDO_ICE
        sw_absorbed = sw_down*(1.0 - albedo)  ! поглощённая SW

        ! Текущая температура поверхности в Кельвинах для расчёта радиации
        t_surf_k = state%T_surface + 273.15

        ! === ДЛИННОВОЛНОВАЯ РАДИАЦИЯ (Longwave) ===
        ! Входящая LW: эмпирическая формула (legacy HEAT)
        lw_down = LW_EMISS*t_air_k**4* &
                  (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
                  (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

        ! Исходящая LW: чёрное тело с эмиссивностью льда
        lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4

        ! === ЯВНОЕ ТЕПЛО (Sensible Heat) ===
        ! Stage 10.3: современная bulk-формулировка
        ! Q_SH = rho_air * CP_AIR * C_H * U * (T_air - T_surface)
        ! C_H = C_H_NEUTRAL = 1.5e-3 (Andreas et al. 2010, арктический морской лед)
        ! Знак: Q_SH > 0 -> атмосфера нагревает айсберг
        sh_flux = rho_air_local*CP_AIR*C_H_NEUTRAL*wind_speed*(t_air_k - t_surf_k)

        ! === СКРЫТОЕ ТЕПЛО (Latent Heat) ===
        ! Stage 10.3: современная bulk-формулировка с насыщением над льдом
        ! Q_LH = rho_air * L_S * C_E * U * (q_air - q_sat_ice)
        ! C_E = C_E_NEUTRAL = 1.5e-3
        ! L_S = 2.835e6 Дж/кг (теплота сублимации при 0°C)
        ! q_sat_ice = удельная влажность насыщения над ЛЬДОМ (Murphy & Koop 2005)
        ! q_air = 0.622 * e_vap / p_atm (из ERA5 d2m/t2m, вычислено до ветвления по солнцу)
        ! Знак: Q_LH > 0 -> поток пара отдаёт энергию поверхности (конденсация/осаждение)
        !       Q_LH < 0 -> поток пара забирает энергию поверхности (сублимация)
        ! Stage 10.4: Q_LH разделяется на массовый поток пара и энергию плавления
        q_sat = saturation_vapor_pressure_ice(t_surf_k)/p_atm*0.622
        lh_flux = rho_air_local*L_S*C_E_NEUTRAL*wind_speed*(q_air - q_sat)

        ! === МАССОВЫЙ ПОТОК ПАРА (Stage 10.4) ===
        ! m_vapor = rho_air * C_E * U * (q_air - q_sat_ice)  [кг/(м²·с)]
        ! Знак: m_vapor < 0 -> сублимация (потеря массы)
        !       m_vapor > 0 -> осаждение (прирост массы)
        ! Q_LH = m_vapor * L_S
        m_vapor = rho_air_local*C_E_NEUTRAL*wind_speed*(q_air - q_sat)

        ! === РАСПРЕДЕЛЕНИЕ ЭНЕРГИИ (Stage 10.4.1 corrective) ===
        ! Q_nonlatent = SW_abs + LW_down + LW_up + SH   (без LH)
        ! Q_LH = m_vapor * L_S  [Вт/м²]
        ! Q_surface = Q_nonlatent + Q_LH  [полная энергия, доступная на поверхности]
        !
        ! Соглашение о знаках:
        !   m_vapor < 0 -> сублимация -> Q_LH < 0 -> сток энергии
        !   m_vapor > 0 -> осаждение  -> Q_LH > 0 -> источник энергии
        !
        ! T_surface < T_melt:  Q_surface идёт на чувствительное нагревание
        ! T_surface пересекает T_melt: энергия делится на чувствительную + остаточную
        ! T_surface = T_melt:  Q_melt = max(Q_surface, 0)
        !
        ! Это заменяет прежнюю неверную схему:
        !   Q_net_non_melt = SW + LW + SH + LH
        !   Q_melt = max(Q_net_non_melt - Q_LH, 0)  -- ОШИБКА: LH сокращался, неверный знак

        q_nonlatent = sw_absorbed + lw_down + lw_up + sh_flux
        q_lh = lh_flux
        q_surface = q_nonlatent + q_lh

        ! === ПРОГНОСТИЧЕСКАЯ ТЕМПЕРАТУРА ПОВЕРХНОСТИ С КОРРЕКТНЫМ РАСПРЕДЕЛЕНИЕМ ЭНЕРГИИ ===
        if (state%T_surface .lt. T_MELT) then
            ! Поверхность ниже точки плавления: эволюция температуры с полной Q_surface
            t_surf_new = state%T_surface + q_surface*dt/c_eff

            if (t_surf_new .ge. T_MELT) then
                ! Пересечение точки плавления в пределах шага
                ! Энергия, израсходованная на чувствительный прогрев до T_melt
                ! Остаточная энергия доступна для плавления
                excess_energy = q_surface - c_eff*(T_MELT - state%T_surface)/dt
                state%T_surface = T_MELT
                ! Энергия плавления = max(остаток, 0)
                q_melt = max(excess_energy, 0.0)
                if (q_melt .gt. 0.0) then
                    m_surface = q_melt/(RHO_ICE*LATENT_HEAT)
                else
                    m_surface = 0.0
                end if
            else
                ! Всё ещё ниже точки плавления
                state%T_surface = t_surf_new
                m_surface = 0.0
            end if
        else
            ! Поверхность на точке плавления или выше
            ! T_surface = T_melt, вся Q_surface доступна для плавления
            q_melt = max(q_surface, 0.0)
            if (q_melt .gt. 0.0) then
                ! Положительная энергия -> плавление, поверхность остаётся на T_MELT
                state%T_surface = T_MELT
                m_surface = q_melt/(RHO_ICE*LATENT_HEAT)
            else
                ! Отрицательная энергия -> поверхность остывает ниже T_MELT
                t_surf_new = state%T_surface + q_surface*dt/c_eff
                state%T_surface = min(T_MELT, t_surf_new)
                m_surface = 0.0
            end if
        end if

        ! Суммарный чистый поток для диагностики (включает энергию плавления)
        q_net = q_surface - m_surface*RHO_ICE*LATENT_HEAT/dt

        ! Сохраняем массовый поток пара в диагностиках
        diag%m_vapor = m_vapor
        diag%t_surface = state%T_surface
        ! Только диагностическая выдача производственных поверхностных потоков (Stage 10.4.2.1):
        ! q_surface = Q_nonlatent + Q_LH  [полная энергия, доступная на поверхности]
        ! q_lh      = m_vapor * L_S       [латентный тепловой поток]
        ! Это те значения, с которыми производились расчёты таяния/массового бюджета.
        diag%q_surface = q_surface
        diag%q_lh = q_lh
    end subroutine compute_surface_melt

    ! ========================================================================
    !   НАСЫЩЕННОЕ ПАРЦИАЛЬНОЕ ДАВЛЕНИЕ НАД ЛЁДОМ (Murphy & Koop 2005)
    ! ========================================================================
    ! Формула Мерфи и Купа (2005) для насыщенного парциального давления
    ! водяного пара над плоским интерфейсом лед-воздух.
    ! Диапазон применимости: 50–273 K (для Арктики: 180–273 K).
    ! Источник: Murphy D.M., Koop T. (2005) "Review of the vapour pressures
    ! of ice and supercooled water for atmospheric applications"
    ! QJRMS, 131, 1539-1565. Equation (10).
    !
    ! ln(e_sat_ice) = A - B/T + C*ln(T) - D*T
    ! где:
    !   A = 9.550426
    !   B = 5723.265
    !   C = 3.53068
    !   D = 0.00728332
    ! e_sat в [Па], T в [К]
    !
    ! Аргументы:
    !   T_k - температура [К] (intent(in))
    !   e_sat_ice - насыщенное парциальное давление над льдом [Па] (выход)
    ! ========================================================================
    pure real function saturation_vapor_pressure_ice(T_k) result(e_sat_ice)
        real, intent(in) :: T_k

        e_sat_ice = exp(MURPHY_KOOP_A - MURPHY_KOOP_B/T_k &
                        + MURPHY_KOOP_C*log(T_k) - MURPHY_KOOP_D*T_k)
    end function saturation_vapor_pressure_ice

    ! ========================================================================
    !   ТОЧКА ЗАМЕРЗАНИЯ (обёртка для обратной совместимости)
    ! ========================================================================
    ! Stage 10.5: делегирует канонической EOS-80 формуле
    ! ocean_freezing_point(S, p=0) на поверхности моря (глубина = 0).
    ! Историческая legacy формула Tf = -54.0*S даёт на ~0.03°C более тёплую
    ! точку замерзания (для S=0.035: -1.89°C против -1.92°C по EOS-80).
    !
    ! Аргументы:
    !   salinity - соленость [кг/кг]
    !   tf       - точка замерзания на поверхности [°C]
    ! ========================================================================
    pure real function freezing_point(salinity) result(tf)
        real, intent(in) :: salinity
        tf = ocean_freezing_point(salinity, 0.0)
    end function freezing_point

end module iceberg_thermodynamics
