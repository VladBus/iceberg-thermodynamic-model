#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/pilots"; mkdir -p "$OUT"
POINTS=(
  "SV_2020 76.416664 21.75 2020"
  "FJL_2024 82.5 53.5 2024"
  "NZ_2024 77.5 59.0 2024"
  "SV_2024 76.5 21.416666 2024"
)
for entry in "${POINTS[@]}"; do
 read -r tag lat lon yr <<< "$entry"
 if [ "$yr" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
 d="$OUT/$tag"; mkdir -p "$d"; start=$(date +%s)
 echo "START $tag 30d $(date -Is)"
 VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
 VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
 "$BIN" "$lat" "$lon" 100 100 100 30 3600 "$d/run.nc" \
   data/input/reanalysis/glorys/$yr/glorys12_barents_${yr}_daily.nc \
   data/input/static/glorys_static_barents.nc \
   data/input/reanalysis/era5/$yr/era5_${yr}_daily.nc \
   --strict-ocean --stop-on-grounding --epoch "$ep" --start-date "$sd" \
   --voxel-snapshot-days 0 > "$d/run.log" 2>&1
 rc=$?; end=$(date +%s)
 if grep -q "STOP: iceberg grounded" "$d/run.log"; then status=GROUNDED
 elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then status=STRICT_OCEAN
 else status=OK; fi
 echo "DONE $tag rc=$rc wall=$((end-start))s $status $(date -Is)" | tee "$d/status.log"
done
echo ALLDONE > "$OUT/master.log"
