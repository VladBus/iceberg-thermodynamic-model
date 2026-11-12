#!/usr/bin/env bash
set -u
cd /home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model
BIN=build/gfortran_3C457547962445A0/app/iceberg_run
OUT=data/validation/stage12.16/energy_100_30d
mkdir -p "$OUT"
VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 \
VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
"$BIN" 78 30 100 100 100 30 3600 "$OUT/run.nc" \
  data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc \
  data/input/static/glorys_static_barents.nc \
  data/input/reanalysis/era5/2020/era5_2020_daily.nc \
  --strict-ocean --stop-on-grounding --epoch 1577836800 --start-date 20200101 \
  > "$OUT/run.log" 2>&1
echo "DONE rc=$? $(date -Is)" >> "$OUT/master.log"
