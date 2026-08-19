! ==============================================================================
! Модуль: run_config
! Назначение: Конфигурация изолированного прогона (Stage 6.2). Вычисляет пути
!             выходных каталогов data/runs/<run_id>/output/{nc,csv,txt,logs,figures},
!             создаёт их и настраивает пути ERA5 input в параметрическом модуле param.
! Физика: Никакой физики. Чистый слой организации файловой системы научного прогона.
! Единицы: Не применимо.
! Зависимости: param (run_id, run_*_dir, era5_input_file).
! Ответственность: Инициализация run_id и каталогов прогона ДО начала моделирования;
!                  используется main и convective_adjustment (guard events CSV).
! ==============================================================================

module run_config
    use param
    implicit none

    private
    public :: setup_run_dirs

contains

    ! ==========================================================================
    ! setup_run_dirs: устанавливает run_id, строит пути output-каталогов,
    ! создаёт дерево data/runs/<run_id>/output/{nc,csv,txt,logs,figures}
    ! и фиксирует путь ERA5 input. Вызывается один раз в начале main.
    ! Параметр era5_file - путь к processed ERA5 файлу (или '' для умолчания).
    ! ==========================================================================
    subroutine setup_run_dirs(run_id_arg, era5_file)
        character(len=*), intent(in) :: run_id_arg
        character(len=*), intent(in), optional :: era5_file

        integer :: cmdstat
        character(len=512) :: cmd

        ! Установка идентификатора прогона
        run_id = trim(run_id_arg)

        ! Построение путей выходных каталогов (структура Stage 6.2)
        ! data/runs/<run_id>/output/{nc,csv,txt,logs,figures}
        run_output_dir = 'data/runs/'//trim(run_id)//'/output'
        run_nc_dir = trim(run_output_dir)//'/nc'      ! NetCDF файлы результатов
        run_csv_dir = trim(run_output_dir)//'/csv'    ! CSV диагностики (daily_diagnostics.csv)
        run_txt_dir = trim(run_output_dir)//'/txt'    ! Текстовые отчеты
        run_log_dir = trim(run_output_dir)//'/logs'   ! Логи запуска
        run_fig_dir = trim(run_output_dir)//'/figures'! Графики/фигуры

        ! Переопределение ERA5 input файла, если передан аргументом
        if (present(era5_file)) then
            if (len_trim(era5_file) .gt. 0) era5_input_file = trim(era5_file)
        end if

        ! Создание дерева каталогов прогона (mkdir -p, идемпотентно).
        ! Используем execute_command_line для вызова shell команды.
        write (cmd, '(A)') 'mkdir -p '//trim(run_nc_dir)//' '// &
            trim(run_csv_dir)//' '//trim(run_txt_dir)//' '// &
            trim(run_log_dir)//' '//trim(run_fig_dir)
        call execute_command_line(trim(cmd), cmdstat=cmdstat)
        if (cmdstat .ne. 0) then
            print *, "WARNING: failed to create run directories for run_id=", trim(run_id)
        end if

        ! Вывод конфигурации для диагностики
        print *, "RUN CONFIG: run_id        = ", trim(run_id)
        print *, "RUN CONFIG: output dir    = ", trim(run_output_dir)
        print *, "RUN CONFIG: nc dir        = ", trim(run_nc_dir)
        print *, "RUN CONFIG: csv dir       = ", trim(run_csv_dir)
        print *, "RUN CONFIG: txt dir       = ", trim(run_txt_dir)
        print *, "RUN CONFIG: log dir       = ", trim(run_log_dir)
        print *, "RUN CONFIG: figures dir   = ", trim(run_fig_dir)
        print *, "RUN CONFIG: era5 input    = ", trim(era5_input_file)
    end subroutine setup_run_dirs

end module run_config
