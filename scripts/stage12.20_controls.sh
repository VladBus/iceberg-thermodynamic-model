#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/controls"
mkdir -p "$OUT"
for entry in "FJL2_2020 81.0 55.0 2020" "FJL2_2024 81.0 55.0 2024"; do
  read -r tag lat lon year <<< "$entry"
  if [ "$year" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
  d="$OUT/${tag}_phi030"; mkdir -p "$d"
  start=$(date +%s); echo "START $tag phi_conn=0.3 $(date -Is)"
  VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
  VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
  "$BIN" "$lat" "$lon" 50 50 50 366 3600 "$d/run.nc" \
    data/input/reanalysis/glorys/$year/glorys12_barents_${year}_daily.nc \
    data/input/static/glorys_static_barents.nc \
    data/input/reanalysis/era5/$year/era5_${year}_daily.nc \
    --strict-ocean --grounded-in-place --epoch "$ep" --start-date "$sd" \
    --voxel-snapshot-days 10 > "$d/run.log" 2>&1
  rc=$?; end=$(date +%s)
  if grep -q "STOP: iceberg grounded" "$d/run.log"; then status=GROUNDED
  elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then status=STRICT_OCEAN
  elif grep -q "melted away" "$d/run.log"; then status=MELTED
  else status=END; fi
  echo "DONE $tag rc=$rc wall=$((end-start))s $status $(date -Is)" | tee "$d/status.log"
done
echo ALLDONE > "$OUT/master.log"
