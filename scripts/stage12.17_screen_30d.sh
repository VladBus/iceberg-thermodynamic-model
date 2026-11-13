#!/usr/bin/env bash
set -u
cd /home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model
BIN=build/gfortran_3C457547962445A0/app/iceberg_run
OUT=/tmp/opencode/stage1217/screen100_30d
mkdir -p "$OUT"
for entry in "NZ 78.0 55.0" "SV 76.5 22.75" "FJL 80.0 45.0"; do
 read -r tag lat lon <<< "$entry"
 for yr in 2020 2024; do
  if [ "$yr" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
  echo "START $tag $yr $(date -Is)"
  VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
  "$BIN" "$lat" "$lon" 100 100 100 30 3600 "$OUT/${tag}_${yr}.nc" \
   "data/input/reanalysis/glorys/$yr/glorys12_barents_${yr}_daily.nc" \
   "data/input/static/glorys_static_barents.nc" \
   "data/input/reanalysis/era5/$yr/era5_${yr}_daily.nc" \
   --strict-ocean --stop-on-grounding --epoch "$ep" --start-date "$sd" > "$OUT/${tag}_${yr}.log" 2>&1
  echo "DONE $tag $yr rc=$? $(date -Is)"
  grep -E "STOP|final lat" "$OUT/${tag}_${yr}.log" | tail -2
 done
done
echo ALLDONE
