#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="build/gfortran_3C457547962445A0/app/iceberg_run"
OUT="data/validation/stage12.17/final"
mkdir -p "$OUT"
POINTS=(
  "NZ 78.0 55.0"
  "SV 76.5 22.75"
  "FJL 80.5 45.0"
)
for entry in "${POINTS[@]}"; do
  read -r tag lat lon <<< "$entry"
  for yr in 2020 2024; do
    if [ "$yr" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
    d="$OUT/${tag}_${yr}"
    mkdir -p "$d"
    if [ -s "$d/run.nc" ] && grep -q "iceberg_run: wrote" "$d/run.log" 2>/dev/null; then
      echo "SKIP $tag $yr (already complete)"
      continue
    fi
    start=$(date +%s)
    echo "START $tag $yr $lat $lon $(date -Is)"
    VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 \
    VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
    "$BIN" "$lat" "$lon" 100 100 100 366 3600 "$d/run.nc" \
      "data/input/reanalysis/glorys/$yr/glorys12_barents_${yr}_daily.nc" \
      "data/input/static/glorys_static_barents.nc" \
      "data/input/reanalysis/era5/$yr/era5_${yr}_daily.nc" \
      --strict-ocean --stop-on-grounding --epoch "$ep" --start-date "$sd" \
      --voxel-snapshot-days 10 > "$d/run.log" 2>&1
    rc=$?
    end=$(date +%s)
    echo "DONE $tag $yr rc=$rc wall=$((end-start))s"
    tail -4 "$d/run.log" || true
  done
done
echo "ALL DONE $(date -Is)"
