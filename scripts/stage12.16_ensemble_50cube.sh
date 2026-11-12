#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="build/gfortran_3C457547962445A0/app/iceberg_run"
GLORY="data/input/reanalysis/glorys/2024/glorys12_barents_2024_daily.nc"
STATIC="data/input/static/glorys_static_barents.nc"
ERA5="data/input/reanalysis/era5/2024/era5_2024_daily.nc"
OUT="data/validation/stage12.16/ensemble_2024_50cube"
mkdir -p "$OUT"
POINTS=(
  "P01 78.0 30.0"
  "P02 78.0 40.0"
  "P03 78.0 50.0"
  "P04 78.0 55.0"
  "P05 79.0 35.0"
  "P06 79.0 45.0"
  "P07 79.0 55.0"
  "P08 80.0 30.0"
  "P09 80.0 40.0"
  "P10 80.0 50.0"
  "P11 81.0 20.0"
  "P12 81.0 55.0"
)
for entry in "${POINTS[@]}"; do
  read -r tag lat lon <<< "$entry"
  d="$OUT/$tag"
  mkdir -p "$d"
  if [ -s "$d/run.nc" ] && grep -q "iceberg_run: wrote" "$d/run.log" 2>/dev/null; then
    echo "SKIP $tag (already complete)"
    continue
  fi
  start=$(date +%s)
  echo "START $tag $lat $lon $(date -Is)"
  VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 \
  VOXEL_DX=2 VOXEL_DY=2 VOXEL_DZ=2 \
  "$BIN" "$lat" "$lon" 100 100 100 366 3600 "$d/run.nc" \
    "$GLORY" "$STATIC" "$ERA5" --strict-ocean --stop-on-grounding \
    --epoch 1704067200 --start-date 20240101 > "$d/run.log" 2>&1
  rc=$?
  end=$(date +%s)
  wall=$((end-start))
  echo "DONE $tag rc=$rc wall=${wall}s"
  tail -4 "$d/run.log" || true
done
echo "ALL DONE $(date -Is)"
