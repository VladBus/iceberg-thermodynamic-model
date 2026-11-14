#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.19/stage4/replacement_screen5"
d="$OUT/D4"; mkdir -p "$d"
start=$(date +%s); echo "START D4 60d $(date -Is)"
VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
"$BIN" 77.0 40.0 100 100 100 60 3600 "$d/run.nc" \
  data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc \
  data/input/static/glorys_static_barents.nc \
  data/input/reanalysis/era5/2020/era5_2020_daily.nc \
  --strict-ocean --stop-on-grounding --epoch 1577836800 --start-date 20200101 \
  --voxel-snapshot-days 0 > "$d/run.log" 2>&1
rc=$?; end=$(date +%s)
if grep -q "STOP: iceberg grounded" "$d/run.log"; then status=GROUNDED
elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then status=STRICT_OCEAN
else status=OK; fi
echo "DONE D4 rc=$rc wall=$((end-start))s $status $(date -Is)" | tee "$d/status.log"
