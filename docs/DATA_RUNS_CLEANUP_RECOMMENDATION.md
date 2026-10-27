# data/runs Cleanup — EXECUTED (Stage 11.10)

**Status:** **EXECUTED 2026-10-27** — not a recommendation any more.
**Base:** `ae6260e`
**Policy:** keep final matrix/90-day/11.8B evidence; retain first/last NetCDF,
`config.env`, logs, and CSV; remove all other run directories and intermediate
NetCDF.

## Result

| Metric | Before | After |
|---|---:|---:|
| `data/runs/` size | **82.583 GB** | **0.510 GB** |
| Top-level run directories | 289 | **26** |
| Original run directories removed | | **263** (plus 8 regenerated test artifacts) |

No data outside `data/runs/` was touched. No archive was retained; the action
was deletion as authorized by Stage 11.10. The exact keep manifest is
`data/runs/KEEP_MANIFEST.json`.

## Kept categories

- 8 final N=1 matrix cells (`matrix_{jan,apr,jul,oct}_{legacy,eos80}_n1`)
- 6 90-day crash/limitation runs (`t5_90day*`, `t5c*_90day*`)
- 11.8B default/explicit/legacy/verification runs (`default_eos80_verify`,
  `explicit_eos80_verify`, `legacy_fallback_verify`, `repro_*`)
- Final T3/T4/T5/T6 evidence (`t3c4_dt1800_ah10000`, `t4_wind_forcing`,
  `t5_30day_apr30`, `t6s_jul_legacy`, `t6s_oct_legacy`,
  `t6s_jan_production`)

For every kept run, only `config.env`, `*.log`, `*.csv`, the first
`results_day_00.nc`, and the last `results_day_final.nc` (or last daily file)
remain.

## New disk budget policy

- Keep `data/runs/` **below 5 GB**; current 0.510 GB.
- Never retain full daily NetCDF for forensic runs; keep first/last + CSV.
- New experiments must use a unique run ID and be removed or trimmed after
  extracting metrics.
- Do not delete `data/validation/` evidence or closure documents.

## Evidence

- `data/runs/KEEP_MANIFEST.json`
- `data/validation/n4_n24_audit.json`
- `data/validation/runs_inventory_final.json` (pre-cleanup inventory)
