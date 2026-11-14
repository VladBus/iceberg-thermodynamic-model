#!/usr/bin/env bash
set -u
cd /home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model
TAG=${1:?tag}; LAT=${2:?lat}; LON=${3:?lon}; YEAR=${4:?year}
OUT=data/validation/stage12.19/${TAG}_fixed_N6
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
mkdir -p "$OUT"
if [ "$YEAR" = 2020 ]; then EP=1577836800; SD=20200101; else EP=1704067200; SD=20240101; fi
VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
VOXEL_CONNECTIVITY_HOURS=6 \
"$BIN" "$LAT" "$LON" 50 50 50 366 3600 "$OUT/run.nc" \
 data/input/reanalysis/glorys/$YEAR/glorys12_barents_${YEAR}_daily.nc \
 data/input/static/glorys_static_barents.nc \
 data/input/reanalysis/era5/$YEAR/era5_${YEAR}_daily.nc \
 --strict-ocean --grounded-in-place --epoch "$EP" --start-date "$SD" \
 --voxel-snapshot-days 10 > "$OUT/run.log" 2>&1
echo "DONE rc=$? $(date -Is)" > "$OUT/master.log"
