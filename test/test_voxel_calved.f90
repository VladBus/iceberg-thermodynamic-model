! ==============================================================================
! Stage 12.19: calved-component removal and main-body hydrostatics.
! ==============================================================================
program test_voxel_calved
    use voxel_iceberg, only: voxel_iceberg_type, voxel_iceberg_init, &
                             voxel_iceberg_compute_state, voxel_iceberg_remove_calved, &
                             voxel_iceberg_get_mass, voxel_iceberg_get_draft, &
                             voxel_iceberg_get_freeboard, voxel_iceberg_get_calved, &
                             voxel_iceberg_set_phi_conn
    use iceberg_types, only: RHO_ICE, C_ICE, LATENT_HEAT
    implicit none

    type(voxel_iceberg_type) :: vox
    integer :: nerr, i, j
    real(8) :: mass0, mass1, calved, calved_e, eexp, draft, free
    integer :: nev

    nerr = 0
    call voxel_iceberg_init(vox, 10, 10, 10, 1.0d0, 1.0d0, 1.0d0, -5.0d0, 1.0d0)
    vox%phi = 0.0d0
    vox%T = -5.0d0
    vox%phi(:, :, 1:5) = 1.0d0          ! main body
    vox%phi(:, :, 8:9) = 1.0d0          ! disconnected plate
    vox%main_mask = vox%phi > 1.0d-12
    call voxel_iceberg_compute_state(vox)
    mass0 = vox%total_mass
    vox%step_count = 1
    vox%connectivity_hours = 1.0d0
    call voxel_iceberg_remove_calved(vox, 3600.0d0)
    call voxel_iceberg_compute_state(vox)
    mass1 = vox%total_mass
    call voxel_iceberg_get_calved(vox, calved, calved_e, nev)
    call voxel_iceberg_get_draft(vox, draft)
    call voxel_iceberg_get_freeboard(vox, free)
    eexp = calved*(real(C_ICE, 8)*5.0d0 + real(LATENT_HEAT, 8))

    print '(a,es12.4,a,es12.4)', ' mass before/after = ', mass0, ' / ', mass1
    print '(a,es12.4,a,i0)', ' calved mass = ', calved, ' events=', nev
    print '(a,es12.4,a,es12.4)', ' calved energy / expected = ', calved_e, ' / ', eexp
    print '(a,2f10.4)', ' draft/freeboard = ', draft, free

    if (abs(calved - 2.0d0*100.0d0*real(RHO_ICE, 8)) > 1.0d-6*calved) nerr = nerr + 1
    if (abs(mass1 - 5.0d0*100.0d0*real(RHO_ICE, 8)) > 1.0d-6*mass1) nerr = nerr + 1
    if (nev /= 1) nerr = nerr + 1
    if (abs(calved_e - eexp) > 1.0d-6*eexp) nerr = nerr + 1
    if (draft <= 0.0d0 .or. free <= 0.0d0) nerr = nerr + 1
    if (any(vox%phi(:, :, 8:9) > 0.0d0)) nerr = nerr + 1

    ! Stage 12.20: a low-phi bridge must not keep a high-phi plate attached.
    call voxel_iceberg_init(vox, 10, 10, 10, 1.0d0, 1.0d0, 1.0d0, -5.0d0, 1.0d0)
    vox%phi = 0.0d0; vox%T = -5.0d0
    vox%phi(:, :, 1:5) = 1.0d0
    vox%phi(:, :, 8:9) = 1.0d0
    vox%phi(5, 5, 6:7) = 0.2d0   ! sub-threshold bridge
    call voxel_iceberg_set_phi_conn(0.3d0)
    vox%main_mask = vox%phi > 1.0d-12
    vox%step_count = 1; vox%connectivity_hours = 1.0d0
    call voxel_iceberg_remove_calved(vox, 3600.0d0)
    call voxel_iceberg_get_calved(vox, calved, calved_e, nev)
    if (abs(calved - 2.0d0*100.0d0*real(RHO_ICE, 8)) > 1.0d-6*calved) nerr = nerr + 1
    if (any(vox%phi(:, :, 8:9) > 0.0d0)) nerr = nerr + 1

    if (nerr == 0) then
        print *, 'SUCCESS: calved plate removed and hydrostatics use main body'
        stop 0
    else
        print '(a,i0)', 'FAILURE: calved test errors=', nerr
        stop 1
    end if
end program test_voxel_calved
