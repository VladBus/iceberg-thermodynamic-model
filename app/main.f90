program main
    use param
    use advection_2d
    use thermodynamics
    implicit none

    print *, "Iceberg Thermodynamic Model - Started!"
    print *, "Grid size IS=", is, " JS=", js, " KS=", ks
    print *, "Module advection_2d is successfully linked!"
    print *, "Module thermodynamics is successfully linked!"

end program main
