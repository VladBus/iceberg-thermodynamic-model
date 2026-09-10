! ==============================================================================
! Модуль: iceberg_types
! Назначение: Базовые типы и константы для модели индивидуального лагранжевого
!             айсберга (Stage 9.1 §6, §23). Выделен в отдельный модуль для
!             разрыва циклических зависимостей между iceberg.f90,
!             iceberg_geometry.f90, iceberg_forcing.f90, iceberg_thermodynamics.f90,
!             iceberg_dynamics.f90.
!
! Физическая модель: Аисберг представляется как прямоугольный параллелепипед
! с размерами L (длина) × W (ширина) × H (высота), плавающий в океане.
! Движение описывается уравнением импульса точки массы. Термодинамика включает
! базальное, боковое и поверхностное плавление. Форсинг: OFFLINE/PRESCRIBED
! (ERA5 атмосфера, EN4 океан T/S, IBCAO батиметрия). Двусторонней связи нет.
!
! Единицы измерения: ВСЕ внутренние вычисления в СИ (м, с, кг, Па, Вт, Дж, К/°C).
!                    Преобразование единиц только на границе с форсингом.
!                    Океаническая модель (param.f90) работает в CGS (см, с, г/см³),
!                    конвертация происходит в iceberg_forcing.f90.
!
! Точность: default real (float32) для совместимости с остальной моделью.
!           Константы определены как real, parameter (compile-time).
!
! Версия: Stage 10.5 (EOS-80 точка замерзания Tf = f(S,p) + диагностика
!                      термического задействования на осадке)
! ==============================================================================

module iceberg_types
    implicit none

    ! ========================================================================
    !   ФИЗИЧЕСКИЕ КОНСТАНТЫ (Stage 9.1 §6, §23)
    ! ========================================================================
    ! Плотности [кг/м³]
    real, parameter :: RHO_ICE = 910.0      ! Плотность льда (стандартное значение)
    real, parameter :: RHO_WATER = 1028.0     ! Плотность морской воды (С ≈ 34.8 PSU, T ≈ 0°C)
    real, parameter :: RHO_AIR = 1.225      ! Плотность воздуха при нормальных условиях (15°C, 1013.25 ГПа)

    ! Термодинамические константы
    real, parameter :: LATENT_HEAT = 334000.0 ! Удельная теплота плавления льда [Дж/кг]
    real, parameter :: CP_WATER = 4186.8   ! Удельная теплоёмкость воды [Дж/(кг·К)]

    ! Прогностическая температура поверхности (Stage 10.2)
    real, parameter :: C_ICE = 2100.0        ! Удельная теплоёмкость льда [Дж/(кг·К)]
    real, parameter :: H_EFF = 0.5           ! Эффективная толщина поверхностного слоя [м]
    real, parameter :: T_MELT = 0.0          ! Температура плавления [°C]

    ! Гравитация
    real, parameter :: GRAVITY = 9.80665      ! Ускорение свободного падения [м/с²]

    ! Коэффициенты точки замерзания морской воды (Stage 10.5, EOS-80 / UNESCO 1983)
    ! Компактная форма: TF = (EOS_FP_A0 + EOS_FP_A1*sqrt(S) - EOS_FP_A2*S)*S + EOS_FP_BP*P
    !   S — практическая солёность [PSU (PSS-78)], P — гидростатическое давление [дбар].
    ! Источник: Fofonoff & Millard 1983 (UNESCO TPMS 44, §5); Gill 1982 (Eq. 3.5.2).
    ! Контрольное значение: TF = -2.588567°C при S=40 PSU, P=500 дбар.
    real, parameter :: EOS_FP_A0 = -0.0575        ! Линейный член [°C/PSU]
    real, parameter :: EOS_FP_A1 = 1.710523e-3    ! Член S^(3/2) [°C/PSU^(3/2)]
    real, parameter :: EOS_FP_A2 = 2.154996e-4    ! Член S^2 [°C/PSU^2]
    real, parameter :: EOS_FP_BP = -7.53e-4       ! Коэффициент давления [°C/дбар]

    ! Коэффициенты лобового сопротивления (drag coefficients) [безразм.]
    ! Stage 9.1 §18-19, Bigg et al. 1997, Martin & Adcroft 2010
    real, parameter :: CD_AIR = 1.3e-3      ! Коэффициент аэродинамического сопротивления (воздух-лёд)
    real, parameter :: CD_WATER = 2.0e-3      ! Коэффициент гидродинамического сопротивления (вода-лёд)

    ! ========================================================================
    !   ОКЕАНИЧЕСКАЯ СТОРОНА ТЕПЛООБМЕНА (Stage 10.6)
    ! ========================================================================
    ! Bulk formulation параметры для базального и бокового плавления.
    ! Источники:
    !   - Weeks & Campbell (1973) J. Glaciol. 12, 207-233 — original bulk parameterization
    !   - Eckert & Drake (1959) "Analysis of Heat and Mass Transfer" — Nu = 0.037 Re^0.8 Pr^1/3
    !   - FitzMaurice & Stern (2018) Ocean Modelling 131, 54-69 — comparison with three-equation
    !   - Martin & Adcroft (2010) J. Geophys. Res. 115, C08016 — implementation in climate models
    !
    ! Для айсбергов масштаба L ~ 100-1000 м (малые по сравнению с радиусом
    ! деформации ~15 км) применима bulk-формулировка по Re = U*L/ν (FitzMaurice & Stern 2018).
    ! Heat transfer coefficient: γ_T = 0.037 * k * Pr^(1/3) * U^0.8 * ν^-0.8 * L^(-0.2)  [W/(m²·K)]
    ! Melt rate: m = γ_T * (T - Tf) / (ρ_ice * L_f)  [m/s]
    ! Stanton number: St = γ_T / U
    !
    ! ВАЖНО: Характерная длина L_char для базального плавления — это длина айсберга
    ! в НАПРАВЛЕНИИ ПОТОКА (streamwise length). Текущая модель НЕ имеет прогностической
    ! ориентации айсберга (state%L всегда вдоль X, state%W вдоль Y).
    ! Поэтому L_char = state%L использует X-размер как приближение.
    ! Это ограничение: для потока не вдоль X физическая корректность не гарантирована.
    ! Для бокового плавления Weeks & Campbell (1973) предлагают L_char = D (черновик).
    !
    ! Константы bulk-формулировки:
    !   Pr (Prandtl number) seawater: ~13.8 at 0°C
    !   ν (kinematic viscosity) seawater: ~1.82e-6 m²/s at 0°C, S=34.8
    !   k (thermal conductivity) seawater: ~0.56 W/(m·K) at 0°C
    !   Sc (Schmidt number) seawater: ~2400 (not used in bulk, for reference)
    !   Re_crit (laminar-turbulent transition): ~5e5 (flat plate)
    !   Three-equation constants (H&J99, J10) — НЕ ИСПОЛЬЗУЮТСЯ в текущей реализации,
    !     сохранены только для документации возможного будущего перехода:
    !     C_d (drag): 0.0015-0.0097, Γ_T: 0.011, Γ_S: 3.1e-4
    ! ========================================================================

    ! Prandtl number for seawater (ratio of viscosity to thermal diffusivity)
    ! Pr = ν / κ_T ≈ 1.8e-6 / 1.3e-7 ≈ 13.8 at 0°C, S=34.8
    ! Источник: стандартные таблицы свойств морской воды
    real, parameter :: PRANDTL_NUMBER = 13.8

    ! Kinematic viscosity of seawater [m²/s] at 0°C, S=34.8
    ! Источник: UNESCO 1983 / Fofonoff & Millard
    real, parameter :: KINEMATIC_VISCOSITY = 1.82e-6

    ! Thermal conductivity of seawater [W/(m·K)] at 0°C
    ! Источник: стандартные таблицы свойств морской воды
    real, parameter :: THERMAL_CONDUCTIVITY = 0.56

    ! Schmidt number for seawater (ratio of viscosity to salt diffusivity)
    ! Sc = ν / κ_S ≈ 1.8e-6 / 7.5e-10 ≈ 2400
    ! Not directly used in bulk formulation but for reference
    real, parameter :: SCHMIDT_NUMBER = 2400.0

    ! Critical Reynolds number for laminar-turbulent transition on flat plate
    ! Re_crit ≈ 5e5 (standard value, Eckert & Drake 1959)
    real, parameter :: REYNOLDS_CRITICAL = 5.0e5

    ! Characteristic length scale for basal melt Reynolds number
    ! For basal: L_char = iceberg length in flow direction (state%L, but see limitation above)
    ! For lateral: L_char = draft (D) - from Weeks & Campbell (1973)
    ! These are set per-call based on geometry, not compile-time constants

    ! Coefficients плавления [м/(с·К)] — LEGACY (Stage 9.3, retained for reference)
    ! Исправлены в Stage 9.3: были 1e-4 [м/с] с делением на (ρᵢ·L_f),
    ! стало 1e-6 [м/(с·К)] с формулой m = C * ΔT (без деления на ρᵢ·L_f).
    ! Физический смысл: γ_T = h/(ρᵢ·L_f), где h ≈ 300 Вт/(м²·К) → γ_T ≈ 1e-6.
    ! Stage 10.6: заменяются на физически обоснованную формулу в compute_basal_melt
    real, parameter :: C_BASAL = 1.0e-6     ! Legacy базальный коэффициент плавления
    real, parameter :: C_LATERAL = 1.0e-6     ! Legacy боковой коэффициент плавления

    ! Порог скорости плавления для предотвращения числового шума [м/с]
    real, parameter :: MELT_RATE_MIN = 1.0e-12

    ! ========================================================================
    !   THREE-EQUATION ICE-OCEAN INTERFACE (Stage 10.10)
    ! ========================================================================
    ! Переключатель схемы базального плавления (runtime, через set_basal_melt_scheme):
    !   BASAL_MELT_SCHEME_FORCED_CONVECTION = 0  -- bulk-формулировка Stage 10.6 (baseline)
    !   BASAL_MELT_SCHEME_THREE_EQUATION   = 1  -- трёхчленное замыкание (H&J99/J2010)
    ! ПО УМОЛЧАНИЮ = 0: production-поведение НЕ меняется до явного переключения.
    integer, parameter :: BASAL_MELT_SCHEME_FORCED_CONVECTION = 0
    integer, parameter :: BASAL_MELT_SCHEME_THREE_EQUATION = 1
    integer, save :: basal_melt_scheme = BASAL_MELT_SCHEME_FORCED_CONVECTION

    ! Трансферные коэффициенты three-equation в U-представлении (J2010, Table 2):
    !   K_T = sqrt(C_d) * Gamma_T = 0.0011   (термический)
    !   K_S = sqrt(C_d) * Gamma_S = 3.1e-5   (галинный)
    ! Observationally constrained are только ПРОИЗВЕДЕНИЯ sqrt(C_d)*Gamma;
    ! сами C_d и Gamma по отдельности плохо ограничены (J2010 §6).
    ! U-представление: gamma_T = K_T * U_rel [м/с], gamma_S = K_S * U_rel [м/с].
    real, parameter :: THREE_EQ_KT = 1.1e-3     ! [безразм.] (J2010 Table 2)
    real, parameter :: THREE_EQ_KS = 3.1e-5     ! [безразм.] (J2010 Table 2)

    ! Теплоёмкость морской воды для океанского теплового потока (H&J99/J2010 c_w).
    ! Отдельно от CP_WATER=4186.8 (пресная вода, поверхностный бюджет Stage 10.2).
    real, parameter :: CP_SEAWATER = 3974.0    ! [Дж/(кг·К)] (H&J99 c_w)

    ! Теплоёмкость льда для линеаризованной теплопроводности вглубь льда
    ! (H&J99 c_i; отдельно от C_ICE=2100 — lumped поверхностный слой Stage 10.2).
    real, parameter :: CP_ICE_3EQ = 2009.0     ! [Дж/(кг·К)] (H&J99 c_i)

    ! Радиационные свойства льда
    real, parameter :: ALBEDO_ICE = 0.7      ! Альбедо льда [безразм.]
    real, parameter :: EMISSIVITY = 0.97     ! Эмиссивность льда [безразм.]
    real, parameter :: STEFAN_BOLTZ = 5.670374419e-8 ! Постоянная Стефана-Больцмана [Вт/(м²·К⁴)]

    ! Внутренняя температура льда (lumped capacitance)
    real, parameter :: T_ICE = -10.0          ! Температура внутри айсберга [°C]

    ! Минимальная толщина для активного айсберга [м]
    real, parameter :: MIN_THICKNESS = 1.0

    ! Угловая скорость вращения Земли [рад/с]
    real, parameter :: OMEGA = 7.2921150e-5

    ! ========================================================================
    !   СОВРЕМЕННЫЙ ТУРБУЛЕНТНЫЙ ОБМЕН ТЕПЛОМ/ВЛАГОЙ (Stage 10.3)
    ! ========================================================================
    ! Явное тепло:
    !   Q_SH = rho_air * CP_AIR * C_H * U * (T_air - T_surface)
    ! Скрытое тепло (обмен паром):
    !   Q_LH = rho_air * L_S * C_E * U * (q_air - q_sat_ice)
    !
    ! Нейтральные bulk-коэффициенты (теоретическая логарифмическая формула):
    !   C_H = C_E = kappa^2 / [ln(z/z0)]^2
    !   kappa = 0.4 (постоянная фон Кармана)
    !   z = 10 м (высота измерений)
    !   z0 = 1e-4 м (длина шероховатости для гладкого льда, Andreas et al. 2010)
    !   Теоретическое значение: C = 0.4^2 / ln(10/1e-4)^2 ≈ 1.21e-3
    !
    ! Действующий производственный коэффициент (Stage 10.3):
    !   C_H = C_E = 1.5e-3  -- фиксированный нейтральный bulk-коэффициент
    !   Это документированный параметр модели для нейтральной bulk-формулировки.
    !   Это НЕ прямой результат kappa^2/ln(z/z0)^2 при z0 = 1e-4 м
    !   (который даёт ~1.21e-3). Логарифмическое соотношение сохраняется
    !   только как теоретический контекст. Поправка на устойчивость
    !   в Stage 10.3 не реализована.
    !
    ! Legacy-значения (из модели HEAT):
    !   SH_COEFF = 1.7068  -> ведёт себя как число Стэнтона (безразмерное)
    !   LH_COEFF = 0.6650735 -> ~443× стандартного C_E (0.0015)
    !   L_v = 2.5e6 (парообразование) для обмена лед-пар
    !   Формула насыщения по воде на поверхности льда (ошибка 5-18% при T < 0°C)
    !
    ! Современная формулировка использует:
    !   CP_AIR = 1004.0 Дж/(кг·К)  -- удельная теплоёмкость сухого воздуха
    !   L_S = 2.835e6 Дж/кг        -- теплота сублимации при 0°C
    !   C_H = C_E = 1.5e-3         -- фиксированные нейтральные bulk-коэффициенты
    !   q_sat_ice = насыщенное парциальное давление над льдом (Murphy & Koop 2005)
    !   Соглашение о знаках: Q_SH > 0 = атмосфера нагревает айсберг
    !                        Q_LH > 0 = поток пара отдаёт энергию поверхности
    !   Stage 10.3: Q_LH — ТОЛЬКО ЭНЕРГЕТИЧЕСКИЙ ПОТОК; изменения массы от сублимации/осаждения нет
    !   Stage 10.4: Q_LH разделяется на массовый поток пара (m_vapor = rho_air * C_E * U * (q_air - q_sat_ice))
    !   и энергию плавления (Q_melt = max(Q_net_non_melt - Q_LH, 0))

    real, parameter :: CP_AIR = 1004.0         ! Удельная теплоёмкость сухого воздуха [Дж/(кг·К)]
    real, parameter :: L_S = 2.835e6           ! Удельная теплота сублимации льда [Дж/кг] (при 0°C)
    real, parameter :: VON_KARMAN = 0.4        ! Константа Кармана [безразм.]
    real, parameter :: Z0_ICE = 1.0e-4         ! Длина шероховатости для гладкого льда [м] (Andreas et al. 2010)
    real, parameter :: Z_REF = 10.0            ! Высота измерения ветра [м] (ERA5 u10/v10)
    ! Нейтральный bulk-коэффициент переноса (теоретический: kappa^2/ln(z/z0)^2 ≈ 1.21e-3;
    ! в производстве используется фиксированное значение 1.5e-3 как документированный параметр)
    real, parameter :: C_H_NEUTRAL = 1.5e-3    ! Нейтральный bulk-коэффициент для явного тепла [безразм.]
    real, parameter :: C_E_NEUTRAL = 1.5e-3    ! Нейтральный bulk-коэффициент для скрытого тепла [безразм.]

    ! Насыщенное парциальное давление над льдом (Murphy & Koop 2005)
    ! Диапазон применимости: 50-273 К; используется для 180-273 К (Арктика)
    real, parameter :: MURPHY_KOOP_A = 9.550426
    real, parameter :: MURPHY_KOOP_B = 5723.265
    real, parameter :: MURPHY_KOOP_C = 3.53068
    real, parameter :: MURPHY_KOOP_D = 0.00728332

    ! ========================================================================
    !   ТИПЫ СОСТОЯНИЯ
    ! ========================================================================

    ! Профиль океана на позиции айсберга (после интерполяции)
    type :: ocean_profile
        integer :: nlevels                 ! Число вертикальных уровней
        real, allocatable :: z(:)          ! Глубины центров слоёв [м], размер (nlevels)
        real, allocatable :: dz(:)         ! Толщины слоёв [м], размер (nlevels)
        real, allocatable :: temp(:)       ! Температура [°C], размер (nlevels)
        real, allocatable :: salt(:)       ! Соленость [массовая доля, кг/кг], размер (nlevels)
        real, allocatable :: u(:)          ! Скорость по X [м/с], размер (nlevels)
        real, allocatable :: v(:)          ! Скорость по Y [м/с], размер (nlevels)
        real, allocatable :: u_rel(:)      ! Относительная скорость [м/с], размер (nlevels)
    end type ocean_profile

    ! Атмосферный форсинг от ERA5 (на позиции айсберга)
    type :: atmos_forcing
        real :: u10    ! Скорость ветра по X на 10 м [м/с]
        real :: v10    ! Скорость ветра по Y на 10 м [м/с]
        real :: t2m    ! Температура воздуха на 2 м [К]
        real :: d2m    ! Точка росы на 2 м [К]
        real :: tcc    ! Общая облачность [доля 0-1]
        real :: msl    ! Давление на уровне моря [Па]
        real :: snowfall ! Интенсивность снегопада [м/с] (экв. воды)
    end type atmos_forcing

    ! Диагностические величины (вычисляются на каждом шаге)
    type :: iceberg_diagnostics
        ! Геометрия
        real :: mass         ! Масса айсберга [кг]
        real :: draft        ! Осадка [м]
        real :: freeboard    ! Надводная часть [м]
        real :: a_waterline  ! Площадь водной линии (L×W) [м²]
        real :: a_wet        ! Оромочённая площадь (дно + боковые до осадки) [м²]
        real :: a_sail       ! Парусная площадь (верх + боковые над водой) [м²]

        ! Скорости плавления [м/с]
        real :: m_basal      ! Базальная скорость плавления
        real :: m_lateral    ! Боковая скорость плавления
        real :: m_surface    ! Поверхностная скорость плавления (melting)
        real :: m_vapor      ! Скорость массы паровой фазы (сублимация/осаждение) [кг/(м²·с)]
        real :: q_net_surface ! Чистый тепловой поток на поверхности после плавления [Вт/м²]
        real :: q_surface    ! Полный тепловой поток на поверхности Q_nonlatent+Q_LH [Вт/м²] (Stage 10.4.2.1)
        real :: q_lh         ! Скрытый тепловой поток Q_LH=m_vapor·L_S [Вт/м²] (Stage 10.4.2.1)
        real :: t_surface    ! Температура поверхности [°C] (Stage 10.2)

        ! Океан на глубине осадки
        real :: t_draft      ! Температура на глубине осадки [°C]
        real :: s_draft      ! Соленость на глубине осадки [кг/кг]
        real :: tf_draft     ! Точка замерзания на глубине осадки [°C]
        real :: delta_t_ocean ! Термическое задействование на осадке T - Tf [°C]
        ! (необрезанное, может быть ≤ 0; Stage 10.5)
        ! Граница лёд-океан (Stage 10.10, трёхчленное замыкание; = T_w/S_w для bulk)
        real :: t_interface   ! Температура на границе T_B [°C]
        real :: s_interface   ! Соленость на границе S_B [кг/кг]

        ! Силы [Н]
        real :: f_wind_x     ! Ветровая сила по X
        real :: f_wind_y     ! Ветровая сила по Y
        real :: f_water_x    ! Водная сила по X
        real :: f_water_y    ! Водная сила по Y
        real :: f_cor_x      ! Сила Кориолиса по X
        real :: f_cor_y      ! Сила Кориолиса по Y
        real :: f_pressure_x ! Сила градиента давления по X
        real :: f_pressure_y ! Сила градиента давления по Y
        real :: f_fk_x       ! Фруде-Крилов сила по X
        real :: f_fk_y       ! Фруде-Крилов сила по Y

        ! Загрунтование
        logical :: grounded  ! Флаг загрунтования
        real :: bathymetry   ! Глубина моря на позиции [м]

        ! Массовый баланс [кг]
        real :: basal_mass_loss    ! Потеря массы базальным плавлением за шаг
        real :: lateral_mass_loss  ! Потеря массы боковым плавлением за шаг
        real :: surface_mass_loss  ! Потеря массы поверхностным плавлением (melting) за шаг
        real :: vapor_mass_loss    ! Изменение массы сублимацией/осаждением за шаг (отриц. = сублимация, полож. = осад)
        real :: total_mass_loss    ! Суммарное изменение массы за шаг (с учётом vapor)

        ! Форсинг / границы домена
        logical :: forcing_valid   ! .TRUE. если позиция внутри домена форсинга
    end type iceberg_diagnostics

    ! Прогностическое состояние айсберга (8 переменных)
    type :: iceberg_state
        ! Позиция в модельных координатах [м]
        ! X ось → j (восток), Y ось → i (север, инвертирована)
        real :: x                 ! Координата X [м]
        real :: y                 ! Координата Y [м]

        ! Скорость дрейфа [м/с]
        real :: u                 ! Скорость по X
        real :: v                 ! Скорость по Y

        ! Геометрия [м]
        real :: L                 ! Длина (вдоль X)
        real :: W                 ! Ширина (вдоль Y)
        real :: H                 ! Высота (вертикально)

        ! Географическая позиция [°]
        ! ВНИМАНИЕ: не обновляется в time stepping (Stage 9.3 limitation)
        real :: latitude          ! Широта [°]
        real :: longitude         ! Долгота [°]

        ! Прогностическая температура поверхности [°C] (Stage 10.2)
        real :: T_surface         ! Температура поверхности льда

        ! Счетчики
        integer :: nstep          ! Номер шага интегрирования
        real :: time              ! Модельное время [с]

        ! Флаги
        logical :: active         ! .TRUE. если айсберг существует
        logical :: grounded       ! .TRUE. если загрунтован
    end type iceberg_state

    ! ========================================================================
    !   PUBLIC СИМВОЛЫ
    ! ========================================================================
    public :: RHO_ICE, RHO_WATER, RHO_AIR, LATENT_HEAT, CP_WATER, GRAVITY
    public :: CD_AIR, CD_WATER
    public :: C_BASAL, C_LATERAL
    public :: ALBEDO_ICE, EMISSIVITY, STEFAN_BOLTZ
    public :: T_ICE, MIN_THICKNESS
    public :: C_ICE, H_EFF, T_MELT
    public :: CP_AIR, L_S, VON_KARMAN, Z0_ICE, Z_REF, C_H_NEUTRAL, C_E_NEUTRAL
    public :: MURPHY_KOOP_A, MURPHY_KOOP_B, MURPHY_KOOP_C, MURPHY_KOOP_D
    public :: EOS_FP_A0, EOS_FP_A1, EOS_FP_A2, EOS_FP_BP
    public :: OMEGA
    ! Stage 10.6 ocean-side heat transfer constants (bulk formulation)
    public :: PRANDTL_NUMBER, KINEMATIC_VISCOSITY, THERMAL_CONDUCTIVITY
    public :: SCHMIDT_NUMBER, REYNOLDS_CRITICAL, MELT_RATE_MIN
    ! Stage 10.10 three-equation interface
    public :: BASAL_MELT_SCHEME_FORCED_CONVECTION, BASAL_MELT_SCHEME_THREE_EQUATION
    public :: basal_melt_scheme, set_basal_melt_scheme
    public :: THREE_EQ_KT, THREE_EQ_KS, CP_SEAWATER, CP_ICE_3EQ
    public :: ocean_profile, atmos_forcing, iceberg_diagnostics, iceberg_state
    public :: ocean_freezing_point
    public :: ocean_heat_transfer_coeff

contains

    ! ========================================================================
    !   ТОЧКА ЗАМЕРЗАНИЯ МОРСКОЙ ВОДЫ Tf = f(S, p) (Stage 10.5)
    ! ========================================================================
    ! Каноническое уравнение состояния (EOS-80 / UNESCO 1983):
    !   Tf = (A0 + A1*sqrt(S) - A2*S)*S + BP*P     [°C]
    !   A0 = -0.0575, A1 = 1.710523e-3, A2 = 2.154996e-4   (S в PSS-78 [PSU])
    !   BP = -7.53e-4 [°C/дбар], P — гидростатическое давление [дбар]
    ! Источник: Fofonoff, N.P. & Millard, R.C. (1983). UNESCO TPMS 44, §5.
    !           Gill, A.E. (1982). Atmosphere-Ocean Dynamics, Eq. 3.5.2.
    ! Контрольное значение: Tf = -2.588567°C при S=40 PSU, P=500 дбар.
    !
    ! Давление пересчитывается из глубины гидростатически:
    !   p [дбар] = rho_w * g * depth / 1e4  (≈ 1.008·depth при RHO_WATER=1028)
    !
    ! Аргументы:
    !   salinity_mass - соленость МАССОВОЙ долей [кг/кг] (конвертируется в PSU ×1000)
    !   depth_m       - глубина [м]
    !   tf            - точка замерзания [°C]
    ! ========================================================================
    pure real function ocean_freezing_point(salinity_mass, depth_m) result(tf)
        real, intent(in) :: salinity_mass
        real, intent(in) :: depth_m

        real :: s_psu, p_dbar

        s_psu = salinity_mass*1000.0
        p_dbar = RHO_WATER*GRAVITY*depth_m/1.0e4

        tf = (EOS_FP_A0 + EOS_FP_A1*sqrt(s_psu) - EOS_FP_A2*s_psu)*s_psu &
             + EOS_FP_BP*p_dbar
    end function ocean_freezing_point

    ! ========================================================================
    !   ТЕПЛООБМЕННЫЙ КОЭФФИЦИЕНТ ОКЕАН-СТОРОНЫ (Stage 10.6)
    ! ========================================================================
    ! Вычисляет теплообменный коэффициент γ_T [W/(m²·K)] для базального/бокового плавления
    ! на основе bulk-формулировки (Weeks & Campbell 1973; Eckert & Drake 1959;
    ! Martin & Adcroft 2010):
    !
    !   γ_T = Nu * k / L_char
    !   Nu = 0.037 * Re^0.8 * Pr^(1/3)          (турбулентный режим, Re > Re_crit)
    !   Nu = 0.664 * Re^0.5 * Pr^(1/3)          (ламинарный режим, Re <= Re_crit)
    !   Re = U_rel * L_char / ν
    !
    ! где:
    !   k        = THERMAL_CONDUCTIVITY [W/(m·K)]
    !   Pr       = PRANDTL_NUMBER [dimensionless]
    !   U_rel    = относительная скорость вода-лёд [m/s]
    !   ν        = KINEMATIC_VISCOSITY [m²/s]
    !   L_char   = характерная длина [m]
    !             (базальное: L — длина в направлении потока, см. ограничение ниже)
    !             (боковое: D — черновик, по Weeks & Campbell 1973)
    !
    ! ОГРАНИЧЕНИЯ:
    ! 1. Характерная длина L_char для базального плавления — это streamwise length
    !    (длина айсберга в направлении относительного течения). Текущая модель
    !    НЕ имеет прогностической ориентации (state%L всегда вдоль X, state%W — вдоль Y).
    !    Вызывающий код передаёт state%L как L_char, что корректно ТОЛЬКО если
    !    U_rel направлен вдоль X. Для общего случая это аппроксимация.
    ! 2. При U_rel = 0 возвращает γ_T = 0 (нет турбулентного теплообмена).
    !    Физически при U_rel = 0 должен быть натуральный конвективный/проводимый
    !    теплообмен, но он не реализован (known limitation, Stage 10.7+).
    ! 3. Переход ламинарный/турбулентный при Re_crit = 5e5 (flat plate).
    !    Для Re < Re_crit используется ламинарная корреляция.
    !
    ! Аргументы:
    !   u_rel       - относительная скорость [м/с] (intent(in))
    !   l_char      - характерная длина [м] (intent(in))
    !   gamma_t     - теплообменный коэффициент [Вт/(м²·К)] (выход)
    ! ========================================================================
    pure subroutine ocean_heat_transfer_coeff(u_rel, l_char, gamma_t)
        real, intent(in) :: u_rel
        real, intent(in) :: l_char
        real, intent(out) :: gamma_t

        real :: reynolds, nusselt

        if (u_rel .le. 0.0 .or. l_char .le. 0.0) then
            gamma_t = 0.0
            return
        end if

        ! Reynolds number: Re = U * L / ν
        reynolds = u_rel*l_char/KINEMATIC_VISCOSITY

        ! Nusselt number: laminar/turbulent regime per Eckert & Drake (1959)
        ! Transition at Re_crit = 5e5 (flat plate). Use turbulent for Re >= Re_crit.
        if (reynolds .ge. REYNOLDS_CRITICAL) then
            ! Turbulent regime: Nu = 0.037 * Re^0.8 * Pr^(1/3)
            nusselt = 0.037*(reynolds**0.8)*(PRANDTL_NUMBER**(1.0/3.0))
        else
            ! Laminar regime: Nu = 0.664 * Re^0.5 * Pr^(1/3)
            nusselt = 0.664*sqrt(reynolds)*(PRANDTL_NUMBER**(1.0/3.0))
        end if

        ! Heat transfer coefficient: γ_T = Nu * k / L
        gamma_t = nusselt*THERMAL_CONDUCTIVITY/l_char
    end subroutine ocean_heat_transfer_coeff

    ! ========================================================================
    !   УСТАНОВКА СХЕМЫ БАЗАЛЬНОГО ПЛАВЛЕНИЯ (Stage 10.10)
    ! ========================================================================
    ! Runtime-переключатель замыкания базального потока.
    !   scheme = BASAL_MELT_SCHEME_FORCED_CONVECTION (0)  -> bulk Stage 10.6 (baseline)
    !   scheme = BASAL_MELT_SCHEME_THREE_EQUATION   (1)  -> H&J99/J2010 three-equation
    ! Неизвестная схема -> аварийная остановка (STOP 1), чтобы не было тихого
    ! падения к default при ошибке вызова (тесты вызывают валидные значения).
    ! ========================================================================
    subroutine set_basal_melt_scheme(scheme)
        integer, intent(in) :: scheme

        if (scheme .eq. BASAL_MELT_SCHEME_FORCED_CONVECTION .or. &
            scheme .eq. BASAL_MELT_SCHEME_THREE_EQUATION) then
            basal_melt_scheme = scheme
        else
            print *, "ERROR: set_basal_melt_scheme: unknown scheme=", scheme
            print *, "  valid: 0 = FORCED_CONVECTION (baseline), 1 = THREE_EQUATION"
            stop 1
        end if
    end subroutine set_basal_melt_scheme

end module iceberg_types
