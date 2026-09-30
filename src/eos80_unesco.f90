! ==============================================================================
! Модуль: eos80_unesco (Stage 11.4)
! Назначение: Международное уравнение состояния морской воды EOS-80
!   (UNESCO 1983; Fofonoff & Millard, UNESCO Tech. Papers Mar. Sci. 44).
! Физика: плотность in-situ rho(S, T, p) [кг/м³]:
!   rho(S,T,p) = rho(S,T,0) / (1 - p_bar/K(S,T,p)),
!   где p_bar = p_dbar * 0.1, K — секущий модуль объёмного сжатия [бар].
!   S — практическая солёность [PSU], T — температура [°C] (IPTS-68
!   аппроксимируется входными °C модели), p — давление [дбар].
!   Коэффициенты сверены с первоисточником через независимую выборку
!   (таблица K(S,T,p): e/f/g/h/i/j/m-серии; см. отчёт 11.4 §1).
!   Плюс: точка замерзания UNESCO Tf(S,p) [°C] и конечно-разностные
!   производные drho/dT [кг/м³/K], drho/dS [кг/м³/PSU] (центральные разности,
!   h_T = h_S = 1e-3; диагностические, в динамику модели не входят).
! Точность: всё real64 внутри; вызывающие приводят к своей точности.
! Pure functions — безопасны для вызова из convective_adjustment.
! В модель НЕ вшито: подключение через диспетчер equation_of_state
! (eos_density/eos_density_f64) за флагом EOS_MODE (default LEGACY).
! ==============================================================================

module eos80_unesco
    use, intrinsic :: iso_fortran_env, only: real64
    implicit none

    ! --- Плотность при атмосферном давлении rho(S,T,0): коэффициенты ---
    real(real64), parameter :: EOS80_A0 = 999.842594_real64
    real(real64), parameter :: EOS80_A1 = 6.793952e-2_real64
    real(real64), parameter :: EOS80_A2 = -9.095290e-3_real64
    real(real64), parameter :: EOS80_A3 = 1.001685e-4_real64
    real(real64), parameter :: EOS80_A4 = -1.120083e-6_real64
    real(real64), parameter :: EOS80_A5 = 6.536332e-9_real64
    real(real64), parameter :: EOS80_B0 = 0.824493_real64
    real(real64), parameter :: EOS80_B1 = -4.0899e-3_real64
    real(real64), parameter :: EOS80_B2 = 7.6438e-5_real64
    real(real64), parameter :: EOS80_B3 = -8.2467e-7_real64
    real(real64), parameter :: EOS80_B4 = 5.3875e-9_real64
    real(real64), parameter :: EOS80_C0 = -5.72466e-3_real64
    real(real64), parameter :: EOS80_C1 = 1.0227e-4_real64
    real(real64), parameter :: EOS80_C2 = -1.6546e-6_real64
    real(real64), parameter :: EOS80_D0 = 4.8314e-4_real64

    ! --- Секущий модуль K(S,T,0): e/f/g-серии [бар] ---
    real(real64), parameter :: EOS80_E0 = 19652.21_real64
    real(real64), parameter :: EOS80_E1 = 148.4206_real64
    real(real64), parameter :: EOS80_E2 = -2.327105_real64
    real(real64), parameter :: EOS80_E3 = 1.360477e-2_real64
    real(real64), parameter :: EOS80_E4 = -5.155288e-5_real64
    real(real64), parameter :: EOS80_F0 = 54.6746_real64
    real(real64), parameter :: EOS80_F1 = -0.603459_real64
    real(real64), parameter :: EOS80_F2 = 1.09987e-2_real64
    real(real64), parameter :: EOS80_F3 = -6.1670e-5_real64
    real(real64), parameter :: EOS80_G0 = 7.944e-2_real64
    real(real64), parameter :: EOS80_G1 = 1.6483e-2_real64
    real(real64), parameter :: EOS80_G2 = -5.3009e-4_real64

    ! --- Члены A (×p) модуля K: h-серия + S·(i) + S^1.5·(j, константа) ---
    real(real64), parameter :: EOS80_H0 = 3.239908_real64
    real(real64), parameter :: EOS80_H1 = 1.43713e-3_real64
    real(real64), parameter :: EOS80_H2 = 1.16092e-4_real64
    real(real64), parameter :: EOS80_H3 = -5.77905e-7_real64
    real(real64), parameter :: EOS80_I0 = 2.2838e-3_real64
    real(real64), parameter :: EOS80_I1 = -1.0981e-5_real64
    real(real64), parameter :: EOS80_I2 = -1.6078e-6_real64
    real(real64), parameter :: EOS80_J0 = 1.91075e-4_real64

    ! --- Члены B (×p²) модуля K: k-серия + S·(m-серия) ---
    real(real64), parameter :: EOS80_K0 = 8.50935e-5_real64
    real(real64), parameter :: EOS80_K1 = -6.12293e-6_real64
    real(real64), parameter :: EOS80_K2 = 5.2787e-8_real64
    real(real64), parameter :: EOS80_M0 = -9.9348e-7_real64
    real(real64), parameter :: EOS80_M1 = 2.0816e-8_real64
    real(real64), parameter :: EOS80_M2 = 9.1697e-10_real64

contains

    ! Плотность in-situ [кг/м³]. S [PSU] ≥ 0, T [°C], p [дбар].
    pure real(real64) function unesco_rho(s_psu, t_c, p_dbar) result(rho)
        real(real64), intent(in) :: s_psu, t_c, p_dbar
        real(real64) :: sr, t2, t3, t4, r0, k0, ka, kb, pbar

        sr = sqrt(max(s_psu, 0.0_real64))
        t2 = t_c*t_c
        t3 = t2*t_c
        t4 = t3*t_c
        pbar = 0.1_real64*p_dbar  ! дбар → бар

        r0 = EOS80_A0 + (EOS80_A1 + (EOS80_A2 + (EOS80_A3 + &
             (EOS80_A4 + EOS80_A5*t_c)*t_c)*t_c)*t_c)*t_c &
           + (EOS80_B0 + (EOS80_B1 + (EOS80_B2 + (EOS80_B3 + &
             EOS80_B4*t_c)*t_c)*t_c)*t_c)*s_psu &
           + (EOS80_C0 + (EOS80_C1 + EOS80_C2*t_c)*t_c)*s_psu*sr &
           + EOS80_D0*s_psu*s_psu

        k0 = EOS80_E0 + (EOS80_E1 + (EOS80_E2 + (EOS80_E3 + &
             EOS80_E4*t_c)*t_c)*t_c)*t_c &
           + (EOS80_F0 + (EOS80_F1 + (EOS80_F2 + &
             EOS80_F3*t_c)*t_c)*t_c)*s_psu &
           + (EOS80_G0 + (EOS80_G1 + EOS80_G2*t_c)*t_c)*s_psu*sr

        ka = EOS80_H0 + (EOS80_H1 + (EOS80_H2 + &
             EOS80_H3*t_c)*t_c)*t_c &
           + (EOS80_I0 + (EOS80_I1 + EOS80_I2*t_c)*t_c)*s_psu &
           + EOS80_J0*s_psu*sr

        kb = EOS80_K0 + (EOS80_K1 + EOS80_K2*t_c)*t_c &
           + (EOS80_M0 + (EOS80_M1 + EOS80_M2*t_c)*t_c)*s_psu

        rho = r0/(1.0_real64 - pbar/(k0 + pbar*(ka + pbar*kb)))
    end function unesco_rho

    ! Точка замерзания UNESCO [°C]. S [PSU], p [дбар].
    pure real(real64) function unesco_freezing_point(s_psu, p_dbar) result(tf)
        real(real64), intent(in) :: s_psu, p_dbar
        tf = -0.0575_real64*s_psu + 1.710523e-3_real64*s_psu*sqrt(max(s_psu, 0.0_real64)) &
             - 2.154996e-4_real64*s_psu*s_psu - 7.53e-4_real64*p_dbar
    end function unesco_freezing_point

    ! Конечно-разностные производные (центральные, h=1e-3; диагностические).
    pure real(real64) function unesco_drho_dT(s_psu, t_c, p_dbar) result(drdt)
        real(real64), intent(in) :: s_psu, t_c, p_dbar
        real(real64), parameter :: H_T = 1.0e-3_real64
        drdt = (unesco_rho(s_psu, t_c + H_T, p_dbar) - &
                unesco_rho(s_psu, t_c - H_T, p_dbar))/(2.0_real64*H_T)
    end function unesco_drho_dT

    pure real(real64) function unesco_drho_dS(s_psu, t_c, p_dbar) result(drds)
        real(real64), intent(in) :: s_psu, t_c, p_dbar
        real(real64), parameter :: H_S = 1.0e-3_real64
        drds = (unesco_rho(s_psu + H_S, t_c, p_dbar) - &
                unesco_rho(max(s_psu - H_S, 0.0_real64), t_c, p_dbar))/(2.0_real64*H_S)
    end function unesco_drho_dS

end module eos80_unesco
