#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/final"; mkdir -p "$OUT"
POINTS=("FJL_A 80.5 45.0" "NZ_A 75.5 57.0" "NZ_B 78.0 55.0")
for yr in 2020 2024; do
  if [ "$yr" = 2020 ]; then ep=1577836800; sd=20200101; else ep=1704067200; sd=20240101; fi
  for entry in "${POINTS[@]}"; do
    read -r tag lat lon <<< "$entry"
    d="$OUT/${tag}_${yr}"; mkdir -p "$d"; start=$(date +%s)
    echo "START $tag $yr $(date -Is)"
    VOXEL_ENABLED=true VOXEL_NX=100 VOXEL_NY=100 VOXEL_NZ=100 VOXEL_DX=1 VOXEL_DY=1 VOXEL_DZ=1 \
    VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
    "$BIN" "$lat" "$lon" 100 100 100 365 3600 "$d/run.nc" \
      data/input/reanalysis/glorys/$yr/glorys12_barents_${yr}_daily.nc \
      data/input/static/glorys_static_barents.nc \
      data/input/reanalysis/era5/$yr/era5_${yr}_daily.nc \
      --strict-ocean --stop-on-grounding --epoch "$ep" --start-date "$sd" \
      --voxel-snapshot-days 10 > "$d/run.log" 2>&1
    rc=$?; end=$(date +%s)
    if grep -q "STOP: iceberg grounded" "$d/run.log"; then st=GROUNDED
    elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then st=STRICT
    elif grep -q "melted away" "$d/run.log"; then st=MELTED
    else st=END; fi
    echo "DONE $tag $yr rc=$rc wall=$((end-start))s $st $(date -Is)" | tee "$d/status.log"
  done
done
echo ALLDONE > "$OUT/master.log"
