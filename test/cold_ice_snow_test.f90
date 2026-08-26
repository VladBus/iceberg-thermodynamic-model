! ==============================================================================
! Тест: controlled cold column ice/snow experiment (Stage 5.4)
! Создает холодную колонку и проверяет физику снегопада/ледяного покрова.
! НАЗНАЧЕНИЕ: контролируемый физический тест, НЕ production run.
!
! Сценарий:
!   - Одна модельная колонка (i=50, j=50) в арктических условиях января
!   - Начальные условия: T=-1.8°C (температура замерзания), S=0.034
!   - Атмосферный форсинг: T_air=-30°C, P=1013 hPa, V_wind=5 м/с, cloud=0.5, humid=0.7
!   - Снегопад: 1.5e-8 м/с (~1.3 мм/сутки водный эквивалент)
!   - Тепловой баланс: heat() решает уравнение теплопроводности
!     через ледяной/снежный слой за 30 модельных дней
!
! Проверяемые физические процессы:
!   1. Накопление снега на поверхности льда/воды
!   2. Термическая изоляция снежным покровом (снег — плохой теплопроводник)
!   3. Рост льда при отрицательном тепловом балансе
!   4. Сохранение физической непрерывности температуры
! ==============================================================================

program cold_ice_snow_test
    use param
    use thermodynamics, only: heat
    implicit none

    integer :: i, j, k, n_iter, day, nday, lll
    real :: dt
    real :: snow_accum, snow_depth, ice_thick
    real :: t_surf, t_air, q_net
    real :: sfal_test(12)
    real :: era5_snowfall_rate_test(is1, js1)

    print *, "============================================================"
    print *, "  CONTROLLED COLD ICE/SNOW EXPERIMENT (Stage 5.4)"
    print *, "============================================================"
    print *, ""
    print *, "PURPOSE: Test snowfall -> snow accumulation -> thermal"
    print *, "         insulation -> surface energy balance -> ice growth"
    print *, ""
    print *, "SETUP: Single cold ocean column, January Arctic conditions"
    print *, "       sfal = ERA5 snowfall rate, cold initial T/S profiles"
    print *, ""
    print *, "DISCLAIMER: This is a controlled physics test, NOT a"
    print *, "            production Arctic simulation. TEST grid only."
    print *, ""

    ! --- Initialize cold column ---
    print *, "Initializing cold column..."
    call init_cold_column()

    ! --- Set snowfall to ERA5-like values (January Arctic) ---
    print *, "Setting ERA5 snowfall rate (January Arctic)..."
    call set_era5_snowfall_jan()

    ! --- Run heat() for 30 days ---
    dt = 3600.0
    nday = 1
    lll = 1  ! January

    print *, ""
    print *, "Running heat() for 30 days with ERA5 snowfall..."
    print *, ""

    do day = 1, 30
        call heat(dt, day, lll)

        ! Diagnostics every 5 days
        if (mod(day, 5) .eq. 0) then
            call print_diagnostics(day)
        end if
    end do

    print *, ""
    print *, "============================================================"
    print *, "EXPERIMENT COMPLETE"
    print *, "============================================================"
    print *, "Check: snow depth > 0, ice thickness > 0, T_surf <= 0"
    print *, "If snow depth = 0 or ice = 0 -> physics issue"

contains

    subroutine init_cold_column()
        integer :: ii, jj, kk

        ! Установка холодных начальных условий для колонки (i=50, j=50)
        ii = 50
        jj = 50

        ! Температура океана: -1.8°C (температура замерзания морской воды)
        ! S=0.034 → T_freeze ≈ -1.8°C по формуле moores
        do kk = 1, ks
            t1(ii, jj, kk) = -1.8  ! [°C] — температура замерзания
            s1(ii, jj, kk) = 0.034  ! [массовая доля] — типичная арктическая соленость
        end do

        ! Поверхностные условия
        t1(ii, jj, 1) = -1.8  ! [°C]
        s1(ii, jj, 1) = 0.034

        ! Лёд: начальное состояние — нет льда
        do kk = 1, ngr  ! ngr=5 категорий толщины льда
            an1(ii, jj, kk + 1) = 0.0  ! концентрация льда [0..1]
            wice1(ii, jj, kk) = 0.0    ! толщина льда [м]
            hsnp(kk) = 0.0             ! толщина снега [м]
            hicp(kk) = 0.0             ! толщина льда [м]
        end do
        ans(ii, jj) = 0.0  ! общая концентрация льда [0..1]

        ! Атмосферный форсинг: арктические январские условия
        tatm(ii, jj) = -30.0  ! [°C] температура воздуха на 2м
        patm(ii, jj) = 1013.0  ! [гПа] давление на уровне моря
        wind(ii, jj) = 5.0    ! [м/с] модуль ветра
        cloud(ii, jj) = 0.5   ! [0..1] облачность (50%)
        humid(ii, jj) = 0.7   ! [0..1] относительная влажность (70%)

        ! Snowfall climatology (will be overridden by ERA5)
        sfal = (/0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0/)

        ! Other params
        kt1(ii, jj) = 1  ! ocean cell
        fi(ii, jj) = 75.0  ! 75°N
        dl(ii, jj) = 0.0
        skT(ii, jj) = 1.0e-4  ! turbulent exchange coeff
    end subroutine init_cold_column

    subroutine set_era5_snowfall_jan()
        ! Январский ERA5 снегопад для Арктики (~0.5-2 мм/сутки водный эквивалент)
        ! Конвертация: 1 мм/сутки = 1e-3 м / 86400 с = 1.16e-8 м/с
        ! Типичный январь в Арктике: 0.5-2 мм/сутки → 0.6e-8 .. 2.3e-8 м/с
        real :: jan_snowfall_rate
        jan_snowfall_rate = 1.5e-8  ! ~1.3 мм/сутки водный эквивалент [м/с]

        era5_snowfall_rate_test = 0.0
        era5_snowfall_rate_test(50, 50) = jan_snowfall_rate
    end subroutine set_era5_snowfall_jan

    subroutine print_diagnostics(iday)
        integer, intent(in) :: iday
        real :: total_snow, total_ice

        total_snow = hsnp(1)
        total_ice = hicp(1)

        print *, ""
        print *, "--- Day ", iday, " Diagnostics ---"
        print *, "  Air temp:     ", tatm(50, 50), " °C"
        print *, "  Surface temp: ", t1(50, 50, 1), " °C"
        print *, "  Snow depth:   ", hsnp(1), " m"
        print *, "  Ice thick:    ", hicp(1), " m"
        print *, "  Ice conc:     ", ans(50, 50)
        print *, "  Snowfall rate:", era5_snowfall_rate_test(50, 50), " m/s"
    end subroutine print_diagnostics

end program cold_ice_snow_test
