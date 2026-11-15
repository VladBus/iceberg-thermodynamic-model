#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/final"
for entry in "NZ_A_2024 75.0 53.583" "NZ_B_2024 78.833 56.167"; do
  read -r tag lat lon <<< "$entry"; d="$OUT/$tag"; mkdir -p "$d"; start=$(date +%s)
  echo "START $tag fallback $(date -Is)"
  VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
  VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
  "$BIN" "$lat" "$lon" 100 100 100 365 3600 "$d/run.nc" \
    data/input/reanalysis/glorys/2024/glorys12_barents_2024_daily.nc \
    data/input/static/glorys_static_barents.nc \
    data/input/reanalysis/era5/2024/era5_2024_daily.nc \
    --strict-ocean --stop-on-grounding --epoch 1704067200 --start-date 20240101 \
    --voxel-snapshot-days 10 > "$d/run.log" 2>&1
  rc=$?; end=$(date +%s)
  if grep -q "STOP: iceberg grounded" "$d/run.log"; then st=GROUNDED
  elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then st=STRICT
  elif grep -q "melted away" "$d/run.log"; then st=MELTED
  else st=END; fi
  echo "DONE $tag rc=$rc wall=$((end-start))s $st $(date -Is)" | tee "$d/status.log"
done
echo ALLDONE > "$OUT/master_fallbacks.log"
