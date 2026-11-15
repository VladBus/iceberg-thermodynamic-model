#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BIN=$(find build -path '*/app/iceberg_run' -type f | head -1)
OUT="data/validation/stage12.20/screen50_30d"; mkdir -p "$OUT"
python3 - <<'PY' > "$OUT/list.txt"
import pandas as pd
d=pd.read_csv('data/validation/stage12.20/candidates.csv')
for _,r in d.iterrows(): print(f"{r.source}_{r.lat:.3f}_{r.lon:.3f} {r.lat} {r.lon} 2020")
PY
while read tag lat lon yr; do
 d="$OUT/$tag"; mkdir -p "$d"; start=$(date +%s)
 VOXEL_ENABLED=true VOXEL_NX=50 VOXEL_NY=50 VOXEL_NZ=50 VOXEL_DX=2 VOXEL_DY=2 VOXEL_DZ=2 \
 VOXEL_CONNECTIVITY_HOURS=6 VOXEL_PHI_CONN=0.3 \
 "$BIN" "$lat" "$lon" 100 100 100 30 3600 "$d/run.nc" \
  data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc \
  data/input/static/glorys_static_barents.nc \
  data/input/reanalysis/era5/2020/era5_2020_daily.nc \
  --strict-ocean --stop-on-grounding --epoch 1577836800 --start-date 20200101 > "$d/run.log" 2>&1
 rc=$?; end=$(date +%s)
 if grep -q "STOP: iceberg grounded" "$d/run.log"; then st=GROUNDED
 elif grep -q "STOP: primary ocean profile unavailable" "$d/run.log"; then st=STRICT
 else st=OK; fi
 echo "$tag $lat $lon $yr $((end-start)) $st" >> "$OUT/results.txt"
 echo "$tag $st $((end-start))s"
done < "$OUT/list.txt"
echo DONE > "$OUT/done"
