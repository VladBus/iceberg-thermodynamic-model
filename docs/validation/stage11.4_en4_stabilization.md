# Stage 11.4: EN4 Initial-Condition Stabilization (D-21) — AUDIT IN PROGRESS

**Status**: AUDIT (docs-first, D-21). No physics change, no regeneration, no `fpm` execution in this step.
**Date / baseline**: 2026-09-28; HEAD `4e99fc2`; working tree clean except this report.
**Classification**: B (physics status — see `docs/model/model_physics_status.md` for the authoritative block table).

## 1. Objective (D-21)

Establish the exact origin of the Stage 11.1 `ro_min = -20.07` Day-0 value for Apr/Jul/Oct 2020 (vs Jan `0.0`), then prepare a minimal RULES-compliant fix. Scope is the EN4 pipeline only: `python/ocean/build_initial_ts.py` → `data/input/processed/ocean/initial_ts_*.nc` → `src/initial_ocean_reader.f90` → Fortran `T2/S2/RO` → Day-0 diagnostic. EOS, CA, DT/DT1, Block 200/210/280, ERA5, grid, bathymetry and thermodynamics are OUT of scope for edits in this step.

## 2. Audit findings — pipeline chain (`python/ocean/build_initial_ts.py`, full file read)

- Raw input (`main()`, L230-232): `temperature` (K), `salinity` (PSU assumed), `depth` (`d_en4`, units taken from file; code assumes cm — see below), `lat`/`lon`.
- Units (`main()`, L235-236): `t_c = (t_k - 273.15).astype(float32)`; `s_f = (s_p / 1000.0).astype(float32)`. Single conversion before interpolation — order correct.
- Horizontal NN: `en4_wet` first defined T&S-finite (L241) for the initial tree (L247-254), then **redefined T-only** (L342-343) with rebuilt tree for the default `nearest` path. The default path therefore ignores S-availability when selecting columns; per-depth protection only inside `vertical_regrid` via `mf = finite(tv) & finite(sv)`.
- `vertical_regrid` (L151-201): flags L155-159 (`0` interp / `1` shallowest-finite / `2` deepest-finite / `3` product-land → output left `0`, L175-177). `zm = Z_M[k] * 100.0` (L183) assumes `d_en4` in cm; same assumption in the bilinear branch (L318 `en4_depth = d_en4 / 100.0`, L321 `searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`).
- `Z_M` shadowing (DEFECT, documented not fixed): global L73 `Z_M = Z_CM / 100.0` = `[2.5, 5, 10, …, 600]` m is used by `vertical_regrid`; `main()` redefines a local L261 `Z_M = [2.5, 5.0, 7.5, 12.5, …, 550]` m used for stats/NetCDF `z_model_m` and output coordinates. Mapping vs stored coordinate differ.
- `eckart_ro` (L121-128): float32, `ro = rho - 1.02` g/cm³, formula matches the Fortran Eckart path (cross-check of `src/equation_of_state.f90` pending — next step).
- Sentinel arithmetic (verified by direct float32 evaluation, same formula): `ro(0°C, 0)` = **-0.0200709 g/cm³**; `×1000` = **-20.0709**. `ro(T, 0)` ≈ -0.02 g/cm³ for any T (S=0 dominates). No physical (T,S) from these files yields `ro = -20.07 g/cm³` (checked: S-as-PSU gives ≈ -3.0; K-without-conversion gives ≈ +0.25).

## 3. Audit findings — built products (direct read, not report quotes)

- `data/input/processed/ocean/`: `initial_ts_2020-{01-01,04-01,07-01,10-01}.nc` all present (Jan 2026-08-30; Apr/Jul/Oct 2026-09-25 23:23-25) plus Jan `Tclamp` variants.
- `data/output/diagnostics/stage7.7/stage7.7_statistics{,_apr,_jul,_oct}.json`: all `result: PASS`, `n_nan_inf_ro/output: 0`, `product_land_column: 0` everywhere; RO ranges physical (Jan 0.00748–0.00819; Apr 0.00367–0.00819; Jul 0.00275–0.00819; Oct 0.00345–0.00820 g/cm³). Apr/Jul/Oct differ from Jan only in `deepest_finite` (128382 vs 0) — seasonal EN4 depth coverage, values physical.
- Direct `.nc` read (133×105×18, `need` mask = 143176 cells each file): **zero** `S==0` cells, **zero** `(T==0 & S==0)` cells in-mask for all four files; stored `density_anomaly_gcm3` minima 0.0027–0.0075 (physical).
- Current `data/runs/stage11.1_{jan7,apr7}/output/nc/results_day_00.nc`: `density_anomaly` units **kg m-3**; minima 0.0 (land cells); maxima match the report (Jan 8.186, Apr 8.244 ≈ report 8.42/8.28); **neither file contains -20.07**. Report u_max values (Apr 0.28 cm/s) do not match current dumps (4.99 cm/s) — outputs were overwritten after the report.

## 4. Provenance conflict (RULES.md §Conflict resolution — recorded, not resolved silently)

- `docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md` mtime 2026-09-25 19:36, committed `a091e37` 20:51. Its Day-0 tables (`ro range (g/cm³)`: Apr/Jul/Oct `-20.07`, Jan `0.000`) **predate** the current Apr/Jul/Oct `.nc` builds (23:23-25) and the current `jan7/apr7` runs (23:58/00:04). The `-20.07` values are therefore **not verifiable against any current artifact** — they describe overwritten runs/files.
- Commit `0b673ff` (2026-09-26 23:16, after all runs) changed three candidate mechanisms: (a) `vertical_regrid` `zm = Z_M[k]` → `Z_M[k]*100.0`; (b) `en4_wet` T-only → T&S; (c) `initial_ocean_reader.f90` new S==0 post-replacement; plus `grid_coupling.f90` KT1/land-marker fix (`8888.0`→`888800.0` for HT in cm).
- `src/initial_ocean_reader.f90` (full read): loads `k<=kt` from file arrays; land/deep → `0.0`; S==0 post-replacement for `k>=2` only (exact `== 0.0` comparison) copies S from above but leaves T=0; Day-0 Fortran diagnostic (`app/main.f90`, ~L1475-1491) takes `ro_min` over wet-only (`kt1>0`, `kw=1..ki_col`), land excluded.
- Stage 11.1 tables are consistent with NetCDF Day-0 dumps as source (T in K, S frac, density in kg m-3): maxima match; the `ro` column unit label (`g/cm³`) is inconsistent with the values (kg m-3 scale). Under that reading, `-20.07` ≡ sentinel `(T,S)=(0,0)` cell rendered in kg/m³, and `S min 0.0000` (all cases incl. Jan) marks zero-salinity wet cells in the dump.

## 5. Classification (per requested CONFIRMED / SUPPORTED / UNKNOWN scheme)

- `ro(0°C,0)×1000 ≡ -20.07` numeric identity: **CONFIRMED** (direct float32 evaluation, same `eckart_ro` formula).
- Current `.nc` files clean (no flag-3, no in-mask sentinel, physical RO): **CONFIRMED** (direct read of all four files + four JSONs).
- Current Day-0 dumps contain no `-20.07`: **CONFIRMED** (`jan7`/`apr7` `results_day_00.nc` minima 0.0 = land).
- Report `-20.07` provenance (overwritten pre-23:23 runs/files): **SUPPORTED** (mtime/commit ordering + value/table mismatch vs current artifacts; direct pre-image unavailable).
- `vertical_regrid` surface-layer bug as the `-20.07` cause: **UNKNOWN** (prior hypothesis; current evidence points instead to sentinel+units/mask handling and the pre-`0b673ff` code state; `Z_M`-shadowing and `d_en4`-units assumption are documented defects but not proven causal for `-20.07`).
- `shallowest_finite` mishandling as cause: **UNKNOWN** (JSON `shallowest_finite` counts are 0 in all four current files; no supporting evidence in current artifacts).
- Fortran-side `(0,0)` wet-cell path (`kt` vs `kk1` mismatch, k=1 S==0 survivor): **SUPPORTED as mechanism class, UNKNOWN as historical cause** (code paths verified in reader L~150-200; no current `.nc`/dump exhibits it).

## 6. What this changes for the fix plan

- Do NOT fix `vertical_regrid` blindly for `-20.07`: current products do not exhibit the value, and the three `0b673ff` changes postdate the evidence. Any fix must first reproduce the historical `(0,0)` wet cell (or prove the `kt`/`kk1`/k=1 path) — otherwise we would be fixing a mechanism with no failing artifact.
- Candidate minimal fix class (NOT implemented): guard the reader/pipeline boundary so `(T,S)=(0,0)` can never enter a wet `RO` computation (e.g. extend the S==0 replacement to k=1 / reject zero-salinity wet cells with a reported flag), plus a units-label correction for the Day-0 `ro` diagnostic (kg m-3 vs g/cm³). Requires: historical-algorithm note, equation (`eckart_ro`), provenance (`EN4.2.2 g10` + script args per month), OFF-by-default switch with bit-identical baseline, independent tests, limitation statement — per RULES.md §Physics-change rules.
- Blocked diagnostics before any fix: (a) EN4 raw `depth` units header check (`ncdump -h`, header only); (b) Fortran `density_anomaly` formula/units cross-check (`src/equation_of_state.f90`); (c) `kt` (Fortran grid) vs `kk1` (Python `load_model_grid`) comparison for k=1 wet cells.

## 7. Files changed in this step

- None (audit + this report only). No `src/`, `python/`, data, or config edits. No `fpm` execution. No commit (awaiting explicit permission per instructions).

## 8. Known limitations / risks

- The historical `-20.07` runs/files are overwritten; classification of its exact cell-level path stays at SUPPORTED/UNKNOWN until (b)-(c) above close it.
- `d_en4` units still assumed from code comments, not verified against the raw header.
- `Z_M` global-vs-local mismatch verified in source but its quantitative effect on the four built files is unmeasured.

## 9. Next (single lightweight step proposed)

Raw header check only: `ncdump -h` depth units for `EN.4.2.2.f.analysis.g10.202001.nc` + `src/equation_of_state.f90` `density_anomaly` formula/units grep. No model run, no regeneration.

## 10. Unit/provenance verification (2026-09-28, executed — audit only, no edits)

- Raw EN4 header (`ncdump -h`, `data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc`): `depth.units = "metres"`, `positive = down`; `temperature.units = kelvin` (potential temperature, `_FillValue -32768`, `add_offset 273.15`); `salinity.units = "1"` (practical salinity). Depth values (`ncdump -v depth`): 5.02, 15.08, …, 5350.27 — metres, 42 levels.
- Consequence for `build_initial_ts.py`: the code assumes `d_en4` in cm in two places — `vertical_regrid` L183 (`zm = Z_M[k] * 100.0  # to match d_en4 (cm)`) and the bilinear branch L318 (`en4_depth = d_en4 / 100.0  # convert to meters`) + L321 (`searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`). Against metre-valued `d_en4`, the `*100` mapping is wrong by 100× (model 2.5 m → EN4 250 m; model 550 m → beyond EN4 bottom → deepest-finite).
- Critical ordering fact: this `*100` was introduced by commit `0b673ff` (2026-09-26 23:16; diff `zm = Z_M[k]` → `Z_M[k] * 100.0`). All current `.nc` products (Jan 2026-08-30; Apr/Jul/Oct 2026-09-25 23:23-25) were built with the pre-`0b673ff` metre-consistent code — which is why they are clean. The current working-tree script would mis-register depths if rerun. No rebuild was performed in this step.
- Fortran EOS (`src/equation_of_state.f90`, L85-98 `density_anomaly`, L116-124 `density_anomaly_f64`): formula coefficient-identical to Python `eckart_ro` (`build_initial_ts.py` L121-128); documented units `t` [°C], `s` [mass fraction], `ro = rho - 1.02` [g/cm³] (L5-12 header, L94-97 comments). Python↔Fortran EOS consistency: CONFIRMED (modulo float32/f64 precision variants, documented L100-115).
- NetCDF boundary (per AGENTS.md §Unit Systems): output `density_anomaly` in kg m-3; model-internal RO in g/cm³. This 1000× boundary, combined with the `(T,S)=(0,0)` sentinel (`ro = -0.0200709` g/cm³, verified by direct float32 evaluation), fully accounts for the reported `-20.07` magnitude without any physical inversion.
- Classification update: `d_en4`-in-metres vs code-assumes-cm → CONFIRMED defect in working-tree script (not yet executed — no product impact to date); Python↔Fortran EOS match → CONFIRMED; `Z_M` global-vs-local shadowing (L73 vs L261) → CONFIRMED defect (unmeasured quantitative effect; pre-`0b673ff` builds used global `Z_M` in `vertical_regrid` with metre-consistent `zm`, so mapping was correct despite the shadowing).

## 11. Applied fixes in working tree (2026-09-28, NOT committed, seasonal `.nc` NOT regenerated)

### A. Confirmed code defects (with correction)

A1. `d_en4` units assumption (CONFIRMED, fixed): `vertical_regrid` L183 used `zm = Z_M[k] * 100.0  # to match d_en4 (cm)`; bilinear branch L318 `en4_depth = d_en4 / 100.0` and L321 `searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`. Raw header proves `depth.units = "metres"` with metre values (5.02…5350.27). Correction: metre-consistent mapping (`zm = Z_M[k]`; `en4_depth = d_en4`; `searchsorted(d_en4, z_target)`). Historical note: the `*100` was introduced by commit `0b673ff`; all shipped `.nc` products were built with the pre-`0b673ff` metre-consistent code, so the fix restores consistency with existing products instead of changing them.

A2. `Z_M` global/local shadowing (CONFIRMED, fixed): module-global L73 `Z_M = Z_CM / 100.0` (`[2.5, 5, 10, …, 600]`, consistent with `src/param.f90` and with `kk1 = searchsorted(Z_CM, ht_cm)`) was shadowed by a local `main()` redefinition (`[2.5, 5.0, 7.5, …, 550]`) used for stats labels, NetCDF `z_model_m` and the bilinear `z_target`, while `vertical_regrid` used the global. Correction: local redefinition removed; single canonical `Z_M` everywhere. Data values from `vertical_regrid` unchanged (it already used the global); only output coordinates/labels and the (non-default) bilinear mapping become consistent.

### B. Historical `-20.07` provenance conflict (unchanged)

Report tables (Stage 11.1, committed `a091e37`) predate current `.nc` builds and runs; current artifacts contain no `-20.07` (direct `.nc` + Day-0 dump reads). Numeric identity `ro(0,0)×1000 = -20.0709` plus NetCDF kg m-3 vs `g/cm³` label explains the magnitude as a sentinel/unit/mask artifact of overwritten runs, not a physical inversion. Conflict recorded per RULES.md; not silently resolved.

### C. Unresolved S=0 provenance (narrowed, still UNKNOWN as historical cause)

Diagnostic 2026-09-28: Fortran `kt` ≡ Python `kk1` exactly (11067/11067 wet columns, 0 mismatch, Jan+Apr); at k=1, zero wet cells with `S==0` in current dumps — `S=0` exists only on land (`kt=0`, invalid marker), never as a wet value. The `S==0` post-replacement in `initial_ocean_reader.f90` (k>=2 only, exact `==`) therefore has no wet target at k=1 in current artifacts. Per instruction, no `(0,0)` guard added; historical cell-level path of `-20.07` stays UNKNOWN (overwritten pre-23:23 runs).

### D. Tests required after fix (independent checks done / required)

- `python3 -m py_compile python/ocean/build_initial_ts.py` — DONE (COMPILE-OK, this step).
- Synthetic `vertical_regrid` probe (metre `d_en4`, 7-level column): k=1 (2.5 m) → surface value flag 1; bottom level → deepest value flag 2; flags {0,1,2} as specified — DONE.
- Canonical-level check: global `Z_M == Z_CM/100` elementwise — DONE (True).
- REQUIRED before any regeneration: rebuild ONE month to a temp `--out`/`--json` path and compare flag_counts/RO ranges against shipped stats (expect interp-dominated distribution, physical RO; only coordinate labels differ by the `Z_M` alignment); full `fpm test` battery on any Fortran touch (none in this step — Python only).
- Seasonal `.nc` regeneration explicitly NOT performed in this step.

## 12. January rebuild-to-temp comparison (2026-09-28, authorized step (a) only)

Command: `python3 python/ocean/build_initial_ts.py --raw data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc --out /tmp/stage114_check/initial_ts_2020-01-01_rebuild.nc --json /tmp/stage114_check/stage7.7_statistics_rebuild.json` (fixed working-tree code; raw untouched; shipped `.nc` untouched). Result `PASS`, `n_nan_inf_ro/output: 0`.

- NO CHANGE: dims `(133, 105, 18)`; `wet_mask` and `water_column_levels` identical; zero NaN/Inf; `product_land_column: 0`; zero wet cells with `S==0` in-mask (sentinel `(0,0)` appears only on land, as invalid marker); `result: PASS`.
- EXPECTED (fix consequences): `z_model_m` labels now canonical global `[2.5, 5, 10, …, 600]` (was local `[2.5, 5.0, 7.5, …, 550]`); flag mix `interp 228722 / shallowest 22133 / deepest 515` instead of all-`interp` (metre-consistent mapping puts level 1, 2.5 m, above the shallowest EN4 sample 5.02 m → flag 1 per spec); value shifts from level-coordinate realignment plus the pre-existing (commit `0b673ff`) `en4_wet` T&S column-selection mask.
- UNEXPECTED-relative-to-nearest-assumption (explained, no action): shipped Jan differs more than level realignment alone explains (T maxabsdiff 7.65, flag pattern all-zero, no zeros anywhere including land) — evidence indicates shipped Jan was built with `--method bilinear` (which fills land and never assigns flags 1/2/3) or a branchless ancestor, not with the default nearest path. Shipped Apr/Jul/Oct show nearest-path signatures (`deepest_finite` 128382). This is a build-method provenance note, not a defect in either file: all shipped products remain untouched and physically valid.
- New-sentinel check: NO new `(0,0)`/S==0 wet effect introduced by the fix (zero wet S==0 cells in rebuild; RO physical 0.0044–0.0100 in-mask).
- `ro_min` question: rebuild January wet RO min 0.0044 g/cm³ (physical); no `-20.07` anywhere in current products, dumps, or rebuild. Historical `-20.07` stays a provenance conflict of overwritten runs (see §4), numerically identical to sentinel `(0,0)×1000` with a kg m-3/`g/cm³` label slip.
