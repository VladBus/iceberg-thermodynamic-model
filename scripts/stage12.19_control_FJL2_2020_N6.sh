#!/usr/bin/env bash
set -u
cd /home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model
OUT=data/validation/stage12.19/FJL2_2020_fixed_N6
mkdir -p "$OUT"
VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
VOXEL_CONNECTIVITY_HOURS=6 \
./build/gfortran_3C457547962445A0/app/iceberg_run 81.0 55.0 50 50 50 366 3600 "$OUT/run.nc" \
 data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc \
 data/input/static/glorys_static_barents.nc \
 data/input/reanalysis/era5/2020/era5_2020_daily.nc \
 --strict-ocean --grounded-in-place --epoch 1577836800 --start-date 20200101 \
 --voxel-snapshot-days 10 > "$OUT/run.log" 2>&1
echo "DONE rc=$? $(date -Is)" > "$OUT/master.log"
