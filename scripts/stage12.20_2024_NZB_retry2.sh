#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/final/NZ_B_2024"; mkdir -p "$OUT"; start=$(date +%s)
VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
"$BIN" 73.083 59.167 100 100 100 365 3600 "$OUT/run.nc" \
 data/input/reanalysis/glorys/2024/glorys12_barents_2024_daily.nc \
 data/input/static/glorys_static_barents.nc \
 data/input/reanalysis/era5/2024/era5_2024_daily.nc \
 --strict-ocean --stop-on-grounding --epoch 1704067200 --start-date 20240101 \
 --voxel-snapshot-days 10 > "$OUT/run.log" 2>&1
rc=$?; echo "DONE rc=$rc wall=$(( $(date +%s)-start ))s $(date -Is)" | tee "$OUT/status.log"
