program main
    use param
    use advection_2d
    use thermodynamics
    use wind_forcing
    use barotropic_dynamics
    use ice_stress
    use grid_masks
    use ice_deform
    use ice_redis
    use smooth_filter
    use advection_3d_s
    use advection_3d_t
    implicit none

    print *, "Iceberg Thermodynamic Model - Started!"
    print *, "Grid size IS=", is, " JS=", js, " KS=", ks
    print *, "Module advection_2d is successfully linked!"
    print *, "Module thermodynamics is successfully linked!"
    print *, "Module wind_forcing is successfully linked!"
    print *, "Module barotropic_dynamics is successfully linked!"
    print *, "Module ice_stress is successfully linked!"
    print *, "Module grid_masks is successfully linked!"
    print *, "Module ice_deform is successfully linked!"
    print *, "Module ice_redis is successfully linked!"
    print *, "Module smooth_filter is successfully linked!"
    print *, "Module advection_3d_s is successfully linked!"
    print *, "Module advection_3d_t is successfully linked!"

end program main
