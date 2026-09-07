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
! Версия: Stage 10.4 (после добавления фазового разделения поверхностного таяния)
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

    ! Коэффициенты лобового сопротивления (drag coefficients) [безразм.]
    ! Stage 9.1 §18-19, Bigg et al. 1997, Martin & Adcroft 2010
    real, parameter :: CD_AIR = 1.3e-3      ! Коэффициент аэродинамического сопротивления (воздух-лёд)
    real, parameter :: CD_WATER = 2.0e-3      ! Коэффициент гидродинамического сопротивления (вода-лёд)

    ! Коэффициенты плавления [м/(с·К)]
    ! Исправлены в Stage 9.3: были 1e-4 [м/с] с делением на (ρᵢ·L_f),
    ! стало 1e-6 [м/(с·К)] с формулой m = C * ΔT (без деления на ρᵢ·L_f).
    ! Физический смысл: γ_T = h/(ρᵢ·L_f), где h ≈ 300 Вт/(м²·К) → γ_T ≈ 1e-6.
    real, parameter :: C_BASAL = 1.0e-6     ! Базальный коэффициент плавления
    real, parameter :: C_LATERAL = 1.0e-6     ! Боковой коэффициент плавления

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
    !   MODERN TURBULENT HEAT/MOISTURE EXCHANGE (Stage 10.3)
    ! ========================================================================
    ! Sensible heat:
    !   Q_SH = rho_air * CP_AIR * C_H * U * (T_air - T_surface)
    ! Latent heat (vapor exchange):
    !   Q_LH = rho_air * L_S * C_E * U * (q_air - q_sat_ice)
    !
    ! Neutral bulk coefficients (theoretical logarithmic formulation):
    !   C_H = C_E = kappa^2 / [ln(z/z0)]^2
    !   kappa = 0.4 (von Karman constant)
    !   z = 10 m (measurement height)
    !   z0 = 1e-4 m (roughness length for smooth ice, Andreas et al. 2010)
    !   Theoretical value: C = 0.4^2 / ln(10/1e-4)^2 ≈ 1.21e-3
    !
    ! Actual production coefficient (Stage 10.3):
    !   C_H = C_E = 1.5e-3  -- fixed neutral bulk transfer coefficient
    !   This value is a documented model parameter for the neutral bulk
    !   formulation. It is NOT the direct result of kappa^2/ln(z/z0)^2
    !   with z0=1e-4 m (which gives ~1.21e-3). The logarithmic relation
    !   is retained only as theoretical context. No stability correction
    !   is implemented in Stage 10.3.
    !
    ! Legacy values (from HEAT model):
    !   SH_COEFF = 1.7068  -> behaves like Stanton number (dimensionless)
    !   LH_COEFF = 0.6650735 -> ~443x standard C_E (0.0015)
    !   L_v = 2.5e6 (vaporization) used for ice-vapor exchange
    !   Water saturation formula at ice surface (5-18% error at T < 0°C)
    !
    ! Modern formulation uses:
    !   CP_AIR = 1004.0 J/(kg·K)  -- specific heat of dry air
    !   L_S = 2.835e6 J/kg        -- latent heat of sublimation at 0°C
    !   C_H = C_E = 1.5e-3        -- fixed neutral bulk transfer coefficients
    !   q_sat_ice = saturation vapor pressure over ice (Murphy & Koop 2005)
    !   Sign convention: Q_SH > 0 = atmosphere heats iceberg
    !                    Q_LH > 0 = vapor flux supplies energy to surface
    !   Stage 10.3: Q_LH is ENERGY FLUX ONLY; no mass change from sublimation/deposition
!   Stage 10.4: Q_LH partitioned into vapor mass flux (m_vapor = rho_air * C_E * U * (q_air - q_sat_ice))
!               and melt energy (Q_melt = max(Q_net_non_melt - Q_LH, 0))

    real, parameter :: CP_AIR = 1004.0         ! Удельная теплоёмкость сухого воздуха [Дж/(кг·К)]
    real, parameter :: L_S = 2.835e6           ! Удельная теплота сублимации льда [Дж/кг] (при 0°C)
    real, parameter :: VON_KARMAN = 0.4        ! Константа Кармана [безразм.]
    real, parameter :: Z0_ICE = 1.0e-4         ! Длина шероховатости для гладкого льда [м] (Andreas et al. 2010)
    real, parameter :: Z_REF = 10.0            ! Высота измерения ветра [м] (ERA5 u10/v10)
    ! Neutral bulk transfer coefficient (theoretical: kappa^2/ln(z/z0)^2 ≈ 1.21e-3;
    ! production uses fixed value 1.5e-3 as documented model parameter)
    real, parameter :: C_H_NEUTRAL = 1.5e-3    ! Neutral bulk transfer coeff for sensible heat [безразм.]
    real, parameter :: C_E_NEUTRAL = 1.5e-3    ! Neutral bulk transfer coeff for latent heat [безразм.]

    ! Saturation vapor pressure over ice (Murphy & Koop 2005)
    ! Valid range: 50-273 K; used for 180-273 K (Arctic)
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
        real :: q_net_surface ! Чистый тепловой поток на поверхности [Вт/м²]
        real :: t_surface    ! Температура поверхности [°C] (Stage 10.2)

        ! Океан на глубине осадки
        real :: t_draft      ! Температура на глубине осадки [°C]
        real :: s_draft      ! Соленость на глубине осадки [кг/кг]
        real :: tf_draft     ! Точка замерзания на глубине осадки [°C]

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
    public :: OMEGA
    public :: ocean_profile, atmos_forcing, iceberg_diagnostics, iceberg_state

end module iceberg_types
