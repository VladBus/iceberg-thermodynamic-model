#!/usr/bin/env bash
set -u
cd /home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model
BIN=build/gfortran_3C457547962445A0/app/iceberg_run
OUT=data/validation/stage12.18
POINTS=(
  "NZ1 75.5 57.0"
  "NZ2 76.5 58.0"
  "SV1 76.5 20.5"
  "SV2 77.58 19.0"
  "FJL1 80.9167 52.0"
  "FJL2 81.0 55.0"
)
for entry in "${POINTS[@]}"; do
 read -r tag lat lon <<< "$entry"
 for yr in 2020 2024; do
  if [ "$yr" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
  d="$OUT/${tag}_${yr}"
  mkdir -p "$d"
  if [ -s "$d/run.nc" ] && grep -q "iceberg_run: wrote" "$d/run.log" 2>/dev/null; then
   echo "SKIP $tag $yr"
   continue
  fi
  start=$(date +%s)
  echo "START $tag $yr $(date -Is)"
  VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
  "$BIN" "$lat" "$lon" 50 50 50 366 3600 "$d/run.nc" \
   "data/input/reanalysis/glorys/$yr/glorys12_barents_${yr}_daily.nc" \
   "data/input/static/glorys_static_barents.nc" \
   "data/input/reanalysis/era5/$yr/era5_${yr}_daily.nc" \
   --strict-ocean --grounded-in-place --epoch "$ep" --start-date "$sd" \
   --voxel-snapshot-days 10 > "$d/run.log" 2>&1
  rc=$?
  echo "DONE $tag $yr rc=$rc wall=$(( $(date +%s) - start ))s"
  grep -E "GROUNDED_IN_PLACE|STOP|melted away|final lat" "$d/run.log" | tail -4
 done
done
echo ALLDONE
