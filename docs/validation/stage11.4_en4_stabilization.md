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

## 12. Seasonal rebuild validation, TEMP only (2026-09-28, authorized step (a))

Rebuilt all four months with the fixed working-tree script to `/tmp/stage114_check/` (raw untouched; shipped `.nc` untouched; no model run; no physics change). Commands: `python3 python/ocean/build_initial_ts.py --raw data/input/raw/ocean/EN.4.2.2.f.analysis.g10.{202001,202004,202007,202010}.nc --out /tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc --json /tmp/stage114_check/stats_*_rebuild.json`.

| Month | dims eq | `z_model_m` canonical | Wet `S==0` | Wet `(0,0)` | NaN/Inf | RO min/max (g/cm³, in-mask) | Flags interp/shallow/deepest/land | JSON result | `ro_min` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jan | True | True (`[2.5..600]`) | 0 | 0 | 0/0 | +0.00438 / +0.01001 | 228722 / 22133 / 515 / 0 | PASS | physical, positive |
| Apr | True | True | 0 | 0 | 0/0 | -0.00096 / +0.00842 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |
| Jul | True | True | 0 | 0 | 0/0 | -0.00386 / +0.00819 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |
| Oct | True | True | 0 | 0 | 0/0 | -0.00127 / +0.00828 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |

- NO CHANGE (all months): dims `(133, 105, 18)`; `wet_mask` + `water_column_levels` identical to shipped; zero NaN/Inf in outputs and RO; `product_land_column: 0`; zero wet `S==0` / `(0,0)` cells (sentinel only on land); `result: PASS`.
- EXPECTED (fix consequences): canonical `z_model_m`; flag mix `interp/shallowest/deepest` (level 1–2 above the 5.02 m EN4 surface sample → flag 1 per spec; 515 cells below EN4 column bottoms → flag 2) instead of shipped patterns. Shipped Apr/Jul/Oct show `deepest_finite` 128382 — the signature of the pre-fix `×100` mapping (model metres read against centimetre scale pushes mid/deep levels below EN4 bottoms); the fixed mapping restores metre-consistent registration. Value shifts follow from correct depth registration plus the pre-existing (`0b673ff`) `en4_wet` T&S column-selection mask.
- PROVENANCE (build-method difference, not fix effect): shipped Jan (all-zero flags, no zeros even on land, local `z_model_m` `[2.5..550]`) carries the `--method bilinear` signature (land pre-filled, flags never assigned), while all rebuilds use the default nearest path. Shipped-vs-rebuild Jan deltas therefore mix method + coordinate effects; shipped products stay untouched and valid.
- UNEXPECTED, noted without action: rebuild surface T minima below freezing (Jan -3.28, Apr -2.17, Oct -2.44 °C) and S maxima up to 0.0374 — raw EN4 nearest-column values exposed by correct surface registration (within the reader `-10..40 °C` acceptance band; no code artifact introduced — nearest selection, no smoothing, unlike bilinear fill). Analyst awareness note for any future production adoption; not a defect of this fix.
- `ro_min` verdict: **no `-20.07` in any rebuild, any shipped `.nc`, or any current Day-0 dump**. Rebuild minima are physical-scale (Jan positive; Apr/Jul/Oct small 1e-3 negative inversions — ordinary static instability for CA to process, not sentinel pathology). Historical `-20.07` remains a provenance conflict of overwritten runs (see §4), numerically identical to sentinel `(0,0)×1000` under a kg m-3/`g/cm³` label slip.

## 13. Stage 11.4-D22 stability test on TEMP initial conditions (2026-09-28, runs only, no physics change)

Four diagnostic runs with TEMP rebuilds (`/tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc` via `ICEBERG_OCEAN_INIT_FILE`), shipped ERA5 forcing per Stage 11.1 report table (`era5_2020_01_fullcoverage_merged.nc`, `era5_2020_04/07/10_merged.nc`), fresh run IDs `stage11.4_d22_{jan7,apr7,jul7,oct7}` (Stage 11.1 outputs untouched). No source edits; no switches beyond init-file override; no commit.

| Run | Day-0 density min (kg m-3, dump) | Matches rebuild RO min | First NaN (day) | B3.3 Day-1 (`maxU2/maxV2`, NaNflag) | Days 1–7 state | Exit | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jan TEMP | +4.38 (physical) | yes (+0.00438 g/cm³) | none (30 d clean) | 42/31 cm/s, flag 0 | T/S/RO stable, EUU ~1–2e15, CA guard active (`maxiter` 1001, guard ~2–4k) but NO divergence | 0, 30 d | **STABLE_7D** (in fact 30 d) |
| Apr TEMP | -0.96 | yes (-0.00096 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 (T/S/RO frozen 273.15/0/0 in dump; CSV all-NaN) | 0, 29 d (zombie) | **EARLY_FAILURE** |
| Jul TEMP | -3.86 | yes (-0.00386 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 (W finite Day 1, rest NaN) | 0 (completed) | **EARLY_FAILURE** |
| Oct TEMP | -1.27 | yes (-0.00127 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 | 0, 30 d (zombie) | **EARLY_FAILURE** |

- Central D22 finding: the preprocessing fix removes the `-20.07` sentinel artifact (Day-0 minima now equal rebuild minima at 1e-3 scale) but does **NOT** prevent Apr/Jul/Oct Day-1 crashes. The early seasonal failures therefore are **not** explained by the sentinel; with only ordinary 1e-3 static inversions present, momentum is already pathological on Day 1 (`maxU2/maxV2 = 0`, NaNflag 1) while Jan (positive RO init) develops finite velocities and survives. This separates two facts that Stage 11.1 conflated: (a) the `-20.07` Day-0 value was a sentinel/unit artifact of overwritten runs (no longer present anywhere); (b) a genuine fast Day-1 divergence mechanism for Apr/Jul/Oct initial+forcing states remains and is outside EN4-preprocessing scope (candidates: stronger seasonal stratification → thermal-wind/B200 response, or seasonal ERA5 forcing differences — NOT investigated here per D22 limits).
- Jan finding: fixed-init January is stable 30/30 days with active CA guard — guard saturation without divergence, confirming (with 10.21) that CA residual is not sufficient for crash.
- Not captured in D22 (honest gaps): per-step thermal-wind values, Block 200/210 intermediates beyond B3.3 flags, event-level CFL (plain config, no `STAGE112_CFL_DIAG`), `wind_max`/`euu` trajectories for crashed runs (CSV all-NaN post-crash; Jan values physical: `wind_max` 13–22 m/s, EUU ~1–2e15). First-invalid exact `(i,j,k,III)` for the Apr/Jul/Oct Day-1 crash was not isolated — out of D22 scope (no new forensic audit per instruction).

## 14. January rebuild detail (single-month precursor, kept for record) (2026-09-28, authorized step (a) only)

Command: `python3 python/ocean/build_initial_ts.py --raw data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc --out /tmp/stage114_check/initial_ts_2020-01-01_rebuild.nc --json /tmp/stage114_check/stage7.7_statistics_rebuild.json` (fixed working-tree code; raw untouched; shipped `.nc` untouched). Result `PASS`, `n_nan_inf_ro/output: 0`.

- NO CHANGE: dims `(133, 105, 18)`; `wet_mask` and `water_column_levels` identical; zero NaN/Inf; `product_land_column: 0`; zero wet cells with `S==0` in-mask (sentinel `(0,0)` appears only on land, as invalid marker); `result: PASS`.
- EXPECTED (fix consequences): `z_model_m` labels now canonical global `[2.5, 5, 10, …, 600]` (was local `[2.5, 5.0, 7.5, …, 550]`); flag mix `interp 228722 / shallowest 22133 / deepest 515` instead of all-`interp` (metre-consistent mapping puts level 1, 2.5 m, above the shallowest EN4 sample 5.02 m → flag 1 per spec); value shifts from level-coordinate realignment plus the pre-existing (commit `0b673ff`) `en4_wet` T&S column-selection mask.
- UNEXPECTED-relative-to-nearest-assumption (explained, no action): shipped Jan differs more than level realignment alone explains (T maxabsdiff 7.65, flag pattern all-zero, no zeros anywhere including land) — evidence indicates shipped Jan was built with `--method bilinear` (which fills land and never assigns flags 1/2/3) or a branchless ancestor, not with the default nearest path. Shipped Apr/Jul/Oct show nearest-path signatures (`deepest_finite` 128382). This is a build-method provenance note, not a defect in either file: all shipped products remain untouched and physically valid.
- New-sentinel check: NO new `(0,0)`/S==0 wet effect introduced by the fix (zero wet S==0 cells in rebuild; RO physical 0.0044–0.0100 in-mask).
- `ro_min` question: rebuild January wet RO min 0.0044 g/cm³ (physical); no `-20.07` anywhere in current products, dumps, or rebuild. Historical `-20.07` stays a provenance conflict of overwritten runs (see §4), numerically identical to sentinel `(0,0)×1000` with a kg m-3/`g/cm³` label slip.

## 15. D22 freeze - seasonal stability experiment on TEMP initial conditions (frozen 2026-09-28)

### 15.1 Objective

Test whether the EN4 preprocessing correction (metre-consistent `d_en4` mapping, single canonical `Z_M`) removes the early seasonal Apr/Jul/Oct failures - without claiming it as the root cause of the whole instability.

### 15.2 Experimental configuration

- Initial conditions: TEMP rebuilds from section 12 (`/tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc` via `ICEBERG_OCEAN_INIT_FILE`); shipped `.nc` untouched.
- Forcing: shipped ERA5 files per Stage 11.1 report table (`era5_2020_01_fullcoverage_merged.nc`, `era5_2020_04/07/10_merged.nc`); no forcing change.
- Run IDs: `stage11.4_d22_{jan7,apr7,jul7,oct7}` (fresh dirs; Stage 11.1 outputs untouched).
- Model code: unmodified production path (no EOS/CA/DT/Block/thermodynamics change; `STAGE112_*`/`STAGE113_*` default OFF; no S==0 guard added).

### 15.3 Four-run result table (frozen values)

| Run | Day-0 density min | Rebuild agreement | First NaN |
| --- | --- | --- | --- |
| Jan TEMP | +4.38 kg/m3 | yes | none; 30 days clean |
| Apr TEMP | -0.96 kg/m3 | yes (-0.00096 g/cm3) | Day 1, 142081 |
| Jul TEMP | -3.86 kg/m3 | yes (-0.00386 g/cm3) | Day 1, 142081 |
| Oct TEMP | -1.27 kg/m3 | yes (-0.00127 g/cm3) | Day 1, 142081 |

Supporting run facts (logs `run_{jan7,apr7,jul7,oct7}.log`, `daily_diagnostics.csv`, `results_day_00/01.nc`): Jan ran 30/30 days exit 0, finite velocities (B3.3 Day-1 maxU2/maxV2 42/31 cm/s, NaNflag 0), stable T/S/RO and EUU ~1-2e15 with CA guard active (`maxiter` 1001); Apr/Jul/Oct show B3.3 Day-1 maxU2/maxV2 = 0.0, NaNflag 1, all-NaN diagnostics from Day 1, runs complete 29-30 days exit 0 in zombie state (142081 NaN cells).

### 15.4 Observed facts

- Day-0 dump minima equal rebuild minima in all four runs (table above).
- No `-20.07` in any TEMP product, shipped product, or current dump.
- January stable 30 days with CA guard active; Apr/Jul/Oct crash Day 1 with only 1e-3-scale initial inversions.

### 15.5 What D22 establishes

- The `d_en4` metre-unit / `Z_M` correction removes the historical `-20.07` Day-0 artifact.
- Day-0 density minima now agree with the rebuilt TEMP products.
- January is stable for 30 days with the CA guard active.

### 15.6 What D22 does NOT establish

- It does NOT establish the preprocessing defect as the root cause of the whole instability.
- Negative initial density in Apr/Jul/Oct is an observed correlation/diagnostic fact, NOT a proven root cause of the Day-1 failure - no such claim is made.
- The exact thermal-wind pointwise mechanism, event-CFL at the failure step, `wind_max`/`euu` for failed runs, and exact `(i,j,k,III)` Day-1 event remain outside D22 scope (known gaps, section 13).

### 15.7 Explicit causal classification (frozen)

- Historical `-20.07` artifact as explanation for seasonal failures: **rejected** (artifact absent; failures persist without it).
- EN4 `d_en4`/`Z_M` preprocessing defect: **corrected and validated** (TEMP rebuilds PASS; canonical levels; metre-consistent mapping verified).
- Negative initial density as root cause: **unproven** (correlation only).
- CA guard as crash mechanism: **rejected** (D22 January: guard active, run stable).
- Common Day-1 dynamic mechanism for Apr/Jul/Oct: **still unresolved**.

### 15.8 Limitations / out-of-scope diagnostics

Per section 13 honest gaps; no per-step thermal-wind, no Block 200/210 intermediates beyond B3.3 flags, no event-level CFL, no `wind_max`/`euu` trajectories for failed runs, no exact Day-1 `(i,j,k,III)` isolation. Gaps are not reopened by this freeze.

### 15.9 Decision for next stage

D22 is complete; no further D22 forensic work. D23 has NOT been started. Any follow-up (e.g. Day-1 divergence mechanism) belongs to a separately authorized stage.

## 16. Stage 11.4-D23 controlled seasonal density experiment (frozen 2026-09-28)

### 16.1 Hypothesis (correlation under test, NOT assumed cause)

Apr/Jul/Oct TEMP initial states contain small negative Day-0 density minima (rebuild wet RO: Apr -0.00096, Jul -0.00386, Oct -0.00127 g/cm3) and crash on Day 1, while Jan (positive RO min +0.00438) survives. D23 tests whether removing ONLY the initial negative-density condition changes the outcome under otherwise identical conditions.

### 16.2 Design (controls vs treatments, TEMP only)

- Controls (existing, unchanged, no rerun): A0 = D22 Jan TEMP (`stage11.4_d22_jan7`); A1 = D22 Apr TEMP; A3 = D22 Jul TEMP; A5 = D22 Oct TEMP.
- Treatments (new diagnostic variants, `/tmp/stage114_d23/initial_ts_YYYY-MM-01_densadj.nc`): A2 = Apr, A4 = Jul, A6 = Oct; run IDs `stage11.4_d23_{apr7t,jul7t,oct7t}`; same ERA5 forcing and model configuration as the paired control.
- Exact transformation (documented rule, TEMP files only): for each wet need-cell with `ro = eckart_ro(T,S) < 0` (float32, same formula as `build_initial_ts.py` L121-128), solve in float64 for the minimal `S_new >= S` with `ro(T,S_new) = +1e-6 g/cm3` (bisection, 60 iterations, bracket expansion from +0.05); store float32; T bit-identical everywhere; salinity differs ONLY in treated cells (verified: equal except flag4); `regrid_flag = 4` marks treated cells (26 Apr, 427 Jul, 80 Oct); `density_anomaly_gcm3` recomputed identically on untreated cells (verified bit-identical); masks/grid/coords/levels unchanged; file attr `diagnostic_treatment` records the rule. NOT in production code; NOT a physics correction; shipped `.nc` untouched.
- Reader acceptance: treatment runs loaded the densadj files (INFO `initial_ocean_reader: using ICEBERG_OCEAN_INIT_FILE = /tmp/stage114_d23/...`, no fallback warnings); S values within the reader `-0.002..0.1` band.

### 16.3 Results table (frozen values, 7-day verdict)

| Pair | Control | Treatment | Treated cells | Day-0 dump (treat) | First NaN (treat) | Treat EUU vs control | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Apr A1/A2 | Day-1 fail (142081) | 26 | clean (max 8.42 matches) | Day 1, 142081 | bit-identical Days 2-8 | **REJECTED** |
| Jul A3/A4 | Day-1 fail (142081) | 427 | clean (max 8.26 matches) | Day 1, 142081 | bit-identical Days 2-8 | **REJECTED** |
| Oct A5/A6 | Day-1 fail (142081) | 80 | clean (max 8.31 matches) | Day 1, 142081 | bit-identical Days 2-8 | **REJECTED** |

Per-run records: B3.3 Day-1 `maxU2/maxV2 = 0.0`, NaNflag 1 in all treatments (same as controls); daily CSV all-NaN from Day 1 (same); CA guard active (`maxiter` 1001) in treatments; exit 0 with completed runs (zombie). Thermal-wind per-step values, event-level CFL (plain config), `wind_max`/`euu` trajectories of crashed runs, and exact `(i,j,k,III)` Day-1 isolation were not captured - same honest gaps as D22 (no new forensic instrumentation per task limits).

### 16.4 Causal interpretation (frozen)

- Negative initial density as cause of the Day-1 failure: **REJECTED** in all three pairs. Removing the entire initial negative-density condition (all affected cells stabilized to +1e-6, verified in-file) changes nothing - not timing, not NaN count, not even rounding-level EUU trajectory.
- This does NOT prove density plays no role later (prognostic evolution untouched by design); it establishes that the INITIAL negative-density condition is not causally necessary for the Day-1 crash.
- CA guard as crash mechanism: remains **rejected** (D22 Jan stable with guard active; D23 treatments fail identically with guard active - guard status does not discriminate outcome).
- No category is called a root cause: the Day-1 Apr/Jul/Oct divergence mechanism stays unresolved; candidates (seasonal stratification response, seasonal forcing differences) were explicitly out of scope.

### 16.5 Limitations

- 7-day verdict only; no 30/90-day extension (per task: do not interpret as long-term stability).
- Controls reused from D22 (no rerun; logs/dumps/CSVs on disk under `data/runs/stage11.4_d22_*`, gitignored per policy).
- Treatment levers S only (T preserved exactly); a T-based stabilization was not tested - the S lever was chosen because haline contraction dominates density sensitivity near freezing, minimizing perturbation size.
- TEMP products live outside the repo (`/tmp/stage114_d23/`); reproducibility rests on the documented rule + fixed script `e735c51` + shipped raw EN4.

### 16.6 Decision for next stage

D23 is complete; no further D23 work. D23 has NOT started any new stage. The Day-1 seasonal divergence mechanism remains an open, separately-authorizable question.

## 17. Stage 11.4-D24 production-coupled Day-1 event capture (frozen 2026-09-28)

### 17.1 Objective

Capture the actual production Day-1 failure event for Apr TEMP (representative failing case) and determine the causal sequence initial-state -> first-invalid -> EOS NaN (142081) propagation. Forensic event capture only; no physics fix, no stabilization attempt.

### 17.2 Baseline

- D21 fix `e735c51`, D22 freeze `5eeccb9`, D23 controlled experiment `b9d3a95`; main clean and pushed at start.
- D23 established: removing all initial negative-density cells changes nothing (bit-identical failures); negative initial density REJECTED as the Day-1 explanation. D22/D23 are NOT reopened.

### 17.3 Diagnostic configuration

- Existing mechanisms used first: `STAGE112_CFL_DIAG`, `STAGE112_FIRST_INVALID`, EOS/CA/B200/B210 diagnostics (`app/main.f90:421` init; module `src/stage112_cfl_diagnostics.f90`).
- Detector audit (source-level, no run needed): `s112_check_first_invalid` (module L391) was dead code - zero callers in `app/`, `src/`, `test/` - so `STAGE112_FIRST_INVALID=true` could never fire; the FIRST_INVALID tracking blocks only recorded CFL-threshold exceedances. Classification: DETECTOR_FAILURE (design/usage gap, confirmed by grep + the D22/D23 `No NaN/Inf detected` output despite 142081 EOS NaNs).
- Minimal added instrumentation (diagnostic-only, env-gated default OFF, no physics change): `s112_is_invalid` + `s112_scan_ocean_state(day,iii,time,stage)` (module L473-526; scans wet `kt1` cells in T,S,RO,U,V,W input order to distinguish EOS-generates (A) vs EOS-receives-invalid (B) vs momentum-first (E)); 8 hook call sites in `app/main.f90` (L589 START_day, L898 BEFORE_advs_advt, L902 BETWEEN_advs_advt, L920 BEFORE_conv_adj, L928 AFTER_conv_adj, L1070 AFTER_block200, L1240 AFTER_block210, L1324 END_step); `s112_record_event` extended with optional day/iii/time (existing 4 CFL call sites unchanged); `s112_finalize` prints day/iii of the event.
- Two latent diagnostic bugs fixed in the same files (diagnostic-only): (1) `s112_record_event` format had 22 items vs 21 descriptors (missing one E15.6; `event_type` never written) - any first-ever call aborted the model (observed exit 2 on first D24 attempt); (2) `events_unit = 82` collided with `ca_diag_unit = 82` (`convective_adjustment.f90:88`) - CA open/close cycles hijacked the unit and event rows vanished into implicit `fort.82`. Fix: correct 22-field format writing `event_type`; `events_unit` 82 -> 86 (verified free: 83/84/85 taken by stage1022).
- No stop-on-event logic added (smaller diff; full runs complete in minutes as proven by D22). No physics, EOS, CA, DT, Block, thermodynamics, ERA5, grid, bathymetry, or S==0-guard change.

### 17.4 Event-capture method

- Apr case: TEMP rebuild `/tmp/stage114_check/initial_ts_2020-04-01_rebuild.nc` via `ICEBERG_OCEAN_INIT_FILE`, shipped `era5_2020_04_merged.nc`, run ID `stage11.4_d24_apr7ev`, env `STAGE112_CFL_DIAG=true STAGE112_FIRST_INVALID=true`; full run to completion (exit 0).
- Jan control: TEMP rebuild + shipped fullcoverage ERA5, run ID `stage11.4_d24_jan7ev`, same env; EUU Days 1-7 bit-identical to D22 Jan baseline (no-diagnostics run) - instrumentation equivalence proven, `No NaN/Inf detected`, exit 0.
- Note on hook cadence (verified from loop nesting: `do iii` L588 closes L871; conv_adj/B200/B210/shal run once per day): hooks fire once per day with stale `iii=13`; resolution is day x operator-boundary, not substep. Sufficient for the Day-1 failure (D22 showed crash within Day 1).

### 17.5 First-invalid event (frozen record)

First invalid event: Day = 1; Step = daily pass (iii stale 13); Substep/operator = BETWEEN_advs_advt (immediately after `advs(dt,c2)`, before `advt`); Variable = S (`var_id=5`); Location = (i,j,k) = (2,2,1) first-found in scan order (NOT proven unique origin cell); Value before = finite (Day-0 dump all finite; START_day and BEFORE_advs_advt scans clean); Value after = NaN; Upstream inputs = `advs` FCT salinity advection operating on finite S2 field; Cell snapshot at event: u=0.0, v=0.0, w=-0.0, t=+5.94 finite, s=NaN, ro=+0.00756 finite, dz=250.0.

### 17.6 Causal sequence (evidence-supported)

Day-0 finite init (dump: no NaN; RO min -0.96 kg/m3 physical-scale) -> Day-1 START_day scan clean -> Day-1 BEFORE_advs_advt scan clean -> `advs()` produces S=NaN at (2,2,1,k=1) with T finite (+5.94) and RO finite (+0.00756) -> `advt`/conv_adj spread (prior run: T+S NaN at AFTER_conv_adj) -> Block 200 transmits (B3.3 Day-1 `maxU2/maxV2 = 0.0`, NaNflag 1; daily CSV all-NaN from Day 1) -> Block 210 amplifies -> 142081 EOS NaN zombie (exit 0, runs complete 29-30 d).

### 17.7 CA/CFL evidence

- CA guard active in all runs including stable Jan (`maxiter` 1001; guard ~2-11k; affected ~10.6-11k columns): guard activity does not discriminate outcome; CA-guard-as-crash-mechanism stays rejected.
- CFL at event: 90-day baseline all << 1 (Cx 0.023, Cy 0.015, Cz 0.105, Cwave 0.66, fDT 0.52); event-run timeseries Day-1 values consistent (no spike). CFL violation stays rejected (preliminary event-level; exact per-step capture at the divergence cell remains a known gap).
- Thermal wind per-step at event: not isolated (plain-config runs; 90-day baseline max ~0.0); known gap, unchanged.
- `wind_max` (Apr D22/D24 daily CSV all-NaN post-crash; forcing itself finite per log ranges) and `euu` trajectories (smooth 2.5e15 -> 9.3e15, no explosion) add no causal signal; same honest gaps as D22.

### 17.8 Classification (frozen, evidence-supported only)

- FIRST_INVALID_PARTIALLY_IDENTIFIED: first invalid variable (S), producing operator (`advs`), boundary (BETWEEN_advs_advt), day (1), first-found cell (2,2,1,k=1), and downstream snapshot established; exact uniqueness of the origin cell and the intra-`advs` mechanism (e.g. FCT limiter edge at the corner surface cell) NOT isolated - no claim beyond the hook boundary.
- EOS as source (hypothesis A): REJECTED for this event (RO finite +0.00756 while S already NaN; EOS had not yet consumed invalid inputs).
- EOS receives invalid (hypothesis B pattern): SUPPORTED as downstream stage (conv_adj/`advt` operate on NaN S afterwards).
- Thermal-wind-first (C): REJECTED for this event (thermal wind derives from RO, which was finite).
- Advection-generated invalid T/S (D): SUPPORTED (S NaN immediately after `advs`, T finite before `advt`).
- Momentum-first (E): REJECTED for this event (U/V/W finite zeros at capture).
- No mechanism is called the root cause: identified is the first invalid operation boundary, not a proven necessary-and-sufficient cause of the whole zombie cascade.

### 17.9 Limitations

- Location (2,2,1) is first-found in scan order (j=2..js, i=2..is, k=1..ki, T-first), not proven unique; other cells may turn NaN in the same operator pass.
- Intra-`advs` mechanism (which flux/limiter term divides by zero at the corner surface cell) not isolated - requires FCT internals audit, explicitly out of D24.
- T-NaN timing (in `advt` vs in `conv_adj` mixing) not isolated between BETWEEN and AFTER_conv_adj hooks; both downstream of the S event.
- Root CSV outputs collide across runs (relative paths); event rows must be harvested immediately after each run (lesson recorded).
- `s112_check_first_invalid` single-value routine remains (now wired via scan); pre-existing CFL-threshold event branches untouched.

### 17.10 Decision

D24 complete as forensic event capture; no further D24 work. D25 NOT started. The Day-1 Apr failure enters `conv_adj` with S already NaN from `advs()`; the remaining open question (why `advs` produces NaN at the corner surface cell on first application) belongs to a separately authorized stage. No physics or shipped-product change resulted from D24.

## 18. Stage 11.4-D25 advs/FCT first-invalid forensic audit (frozen 2026-09-28)

### 18.1 Objective

Determine exactly why `advs()` produces NaN in salinity S during the first Day-1 application for Apr TEMP (D24 boundary: BEFORE_advs clean, BETWEEN S-NaN). No fix, no physics change.

### 18.2 advs source audit (`src/advection_3d_s.f90`, full read)

- Caller: `app/main.f90:900` `call advs(dt, c2)` (after W/advection-CFL, before `advt`).
- Stages: horizontal upwind predictor into `tt(k) = s1 - c2*(cdx+cdy)`; vertical Thomas transport into `cd`; FCT Zalesak limiter passes on X/Y/Z (max/min/sign/mult only - division-free); final `s2 = cd` whole-array.
- Divisions in advs: `/dz(k)`, `/dz(k1)` (positive thicknesses from `src/param.f90` z-data), `/dt` (3600), `/dz1(k)` (positive). No zero-denominator path from finite inputs; FCT limiter cannot generate NaN from finite inputs.
- Exhaustive `s1` writer audit (`grep s1(`): writers are `initial_ocean_reader` (`s1o=s_arr`), `initial_conditions` (`s1=s2` synthetic), and `heat()` (`src/thermodynamics.f90:477` melt branch, `:490` no-melt branch, surface k=1 only); `advs` only READS `s1`.

### 18.3 D24 event reconstruction (extended scan with S1/T1)

- Scan extended with `s1` (var 8) / `t1` (var 9) checks first (module L491-500); rerun Apr TEMP with all hooks: first event now at BEFORE_advs_advt, S1 NaN at (2,2,1,k=1), with S2/T2/RO/U/V/W all finite (snapshot: t=+5.94, s=+0.03504, ro=+0.00756, u=v=w=0).
- START_day scan clean (now S1-aware): S1 became NaN during Day-1 pre-advection processing, i.e. inside `heat()` (the only S1 writer on that path; runs in the Day-1 substep loop before advection).
- Therefore `advs` did NOT generate the NaN arithmetically: `tt(k) = s1 - c2*(cdx+cdy)` propagated a pre-formed S1-NaN operand (with finite fluxes - Day-1 velocities ~0, land-neighbor S=0 contributing only finite 0*finite terms).

### 18.4 Local stencil analysis, cell (2,2,1) (Apr vs Jan Day-0 dumps)

- (2,2,1): wet (`kt1`=18 both months); Apr T=279.09K S=0.03504, Jan T=279.57K S=0.03503 - nearly identical ocean state.
- Neighbors (1,2,1),(2,1,1): land (`kt1`=0), T=273.15K, S=0.0 both months; with ~zero Day-1 velocities their FCT contributions are finite zeros - boundary S=0 is NOT the direct NaN mechanism in `advs`.
- Corner position matters only via the ice state feeding `heat()` (open-water fraction `ann1`, melt heat `qn`), which differs by month/forcing - not via ocean stencil values (structurally same Apr vs Jan).

### 18.5 First-invalid intermediate (frozen finding)

- Intermediate: `s1(2,2,1)` NaN, produced by `heat()` on Day 1 before advection; exact heat-internal expression NOT isolated. Candidates (both read, not executed): open-water averaging division by `ann2` (`thermodynamics.f90` ~L473-474, requires melt branch with `ann2=0`) vs category-loop divisions (`/dzz`, `/(dzz-a1)`, `/b_tmp`, ~L407-418). Distinguishing them needs heat-internal tracing - explicitly out of D25 scope, no new stage started.

### 18.6 Jan vs Apr comparison (structural, per TASK 5)

- Ocean stencil at (2,2,1): equivalent (see 18.4). Masks/boundaries equivalent (same grid; `kt` identical). FCT coefficients: same code path, finite inputs both months.
- Difference must enter via `heat()` inputs (ice state `ann1/anp/hicp/hsnp`, forcing `qn`) which are month-dependent. No initial condition was modified for this comparison.

### 18.7 Hypothesis classification (frozen)

- A (division/zero denominator in advs): REJECTED (no zero-division path from finite inputs; dz/dz1/dt positive; limiter division-free).
- B (invalid input entering advs): CONFIRMED as S1-NaN input with all scanned state finite (mechanism class; exact heat expression UNKNOWN per 18.5).
- C (boundary/ghost-cell problem in advs): REJECTED as direct mechanism (land S=0 contributes finite zeros at ~zero velocity); SUPPORTED as location context (corner cell ice state drives heat path).
- D (FCT limiter invalid coefficient): REJECTED as generator (division-free; operates on already-NaN `cd` downstream).
- E (flux calculation invalid value): REJECTED as generator (fluxes finite: ~zero velocities times finite S).
- F (overflow/underflow): REJECTED (all magnitudes O(1e-2..1e3), no extremes).
- G (precision/rounding): REJECTED (NaN is not a rounding artifact at these scales).
- H (heat writes NaN to S1/T1): SUPPORTED (only S1 writer on path; divisions present; runtime S1-NaN observed with S2 finite). Exact division: UNKNOWN (next-stage question).

### 18.8 Limitations

- (2,2,1) is first-found in scan order, not proven unique origin cell.
- Exact heat-internal division not isolated (two candidate sites, no heat-internal trace executed).
- T1-NaN timing (in `advt` vs `conv_adj` mixing) not separated; both downstream of the S1 event.
- Diagnostic hygiene notes (found while capturing): `s112_record_event` format had 22 items vs 21 descriptors (latent abort on first-ever call - fixed, diagnostic-only); `events_unit=82` collided with `ca_diag_unit=82` (event rows diverted to implicit `fort.82` - fixed to 86, verified free); root-relative diagnostic CSVs collide across runs (harvest immediately).

### 18.9 Decision

D25 complete within its scope (advs mechanics resolved: propagation, not generation). No physics or shipped-product change. D26 NOT started. The remaining open question (which heat division produces S1-NaN at (2,2,1) on Day 1 under April ice/forcing) belongs to a separately authorized stage.

## 19. Stage 11.4-D26 forensic source tracing of S1 NaN at (2,2,1) (frozen 2026-09-28)

### 19.1 Objective

Identify the exact line and operation producing the first S1/T1 NaN before `advs`, using targeted cell-gated tracing only. No fix, no physics change.

### 19.2 Method (diagnostic-only, env-gated `STAGE114_D26_TRACE`, default OFF)

- New module `src/stage114_d26_trace.f90`: `d26_heat_trap` (prints all operands of both heat S1/T1 assignments) + `d26_heat_entry` (entry snapshot distinguishing inherited vs created NaN). New file justified: avoids touching thermodynamics declarations beyond one `use` line + two call sites.
- Trap sites in `src/thermodynamics.f90`: after melt-branch S1/T1 assignments and after else-branch assignments; fire only for (i,j)=(2,2) AND already-NaN/Inf S1/T1 (no log flood: fires only on failure).
- OFF-equivalence: Jan run with all switches OFF gives EUU bit-identical to the D22 baseline Days 1-7, exit 0, zero diagnostic artifacts (no CSVs, no fort.*).

### 19.3 Boundary audit (TASK 2)

- Cell (2,2,1): wet (`kt1`=18 both months); neighbors (1,2,1),(2,1,1) are land (`kt1`=0) with initialized finite values (dump: T=273.15K, S=0.0; full-array NaN count 0). No routine assigns invalid values there.
- `tpar/spar/anp/danp/hicp/hsnp` are module-shared scratch (`src/param.f90:202-208`); per-cell init loop covers indices 1..5 only (`thermodynamics.f90` ~L92-106); index 6 is written solely by the category k=5 body. No writers exist outside `heat()` (exhaustive grep over `src/`, `app/`, `test/`).

### 19.4 Exact invalid assignment (frozen finding)

- File/line: `src/thermodynamics.f90:500` `b1 = b1 + anp(k)*spar(k1)` (and `:499` for T1) in the else-branch averaging, at k=5/k1=6, cell (2,2,1), Day 1.
- Operands (printed): `anp(5)` = 0.0, `spar(6)` = NaN → `0.0*NaN` = NaN → `b1` = NaN → `:504` `s1(i,j,1) = b1` = NaN (same for `t1` via `tpar(6)` = NaN). Pre-state: `ann1` = 1.0 (open water, no ice), `hicp`/`hsnp`/`danp` all 0.0, `tpar(1..5)`/`spar(1..5)` finite.
- `tpar(6)`/`spar(6)` were already NaN at (2,2) heat-entry (`d26_heat_entry` fired from Day 1 on): inherited shared-scratch state, NOT created by (2,2)s own guarded category iterations (all `anp(k)=0` skip). The generating division (candidates: `:327` `b=0.6324/b4` with b4=0; `:366` `0.31/hsnp(k)`; `:373` `/hicp(k)`; `:415` `/(dzz-a1)`; `:418` `/b_tmp`) executed in some earlier-processed ice cell and was NOT isolated to a single line — explicit next-stage question, not claimed here.

### 19.5 Hypothesis classification update (D25 refined)

- H-upstream (heat writes S1-NaN): CONFIRMED as the first invalid assignment in the prognostic chain (exact line + operands printed).
- Exact generating division inside heat category physics: UNKNOWN (narrowed to the k=5 division set above; entry-inheritance proven, in-cell creation excluded for (2,2)).
- A/B/C/D/E/F/G from D25 §18.7 stand unchanged.

### 19.6 Limitations

- (2,2,1) is first-found in scan order, not proven unique origin cell.
- The poisoning cell/division that first wrote `tpar(6)`/`spar(6)` NaN is not identified (requires untargeted tracing or division-guard audit across all cells — explicitly out of D26).
- Jan-vs-Apr ice-state difference at (2,2) (why Jan never poisons shared scratch) not established.

### 19.7 Decision

D26 complete within its charter (exact s1-line + operands + inheritance proof). No physics or shipped-product change. D27 NOT started; the category-division isolation is a separately authorizable question.

## 20. Stage 11.4-D27 scratch-state poisoning forensics (frozen 2026-09-28)

### 20.1 Safe-division pivot: REJECTED before application

- A safe-division (`MAX`-floor) implementation was started, then HALTED and fully reverted (`thermodynamics.f90` restored to `def0cb0`, new module deleted, `build/` cleared; revert verified via empty `git status`).
- Rationale: D26 proved `0.0*NaN`, not a zero-denominator generator; blind floors would alter physics without fixing stale shared-scratch leakage. NO `MAX` guards, NO NaN clamps, NO equation changes were applied in D27.

### 20.2 TASK 1 — scratch lifetime audit (frozen)

| Array | Decl | Per-cell refresh | Skip? | Index 6 valid guaranteed? |
|---|---|---|---|---|
| `tpar/spar(1..5)` | `param.f90:202` module shared | init loop L104-108, unguarded, every cell | No | Yes (fresh `twa`/`a`) |
| `anp/hicp/hsnp(1..5)` | `param.f90:205` module shared | init loop L94-103, unguarded, every cell | No | n/a (fresh) |
| `tpar(6)/spar(6)` | same | NEVER in init loop; only via k=5 writer sites | — | NO |
| `danp(1..5)` | same | only in leads branch L459-472; stale otherwise | Yes | n/a |
| `sicst` | `param.f90:208` DATA const | never written | — | n/a |
- Sole writers of index 6 in the whole codebase (`src/`, `app/`, `test/` grep): `heat()` sites L427 `spar` melt, L434 `tpar` melt, L442 `spar` growth, L442→L449 `tpar` growth — all inside the k-loop behind the L249 `anp(k)<0.001 → cycle` guard. Sole caller of `heat()`: `main.f90:628`. No explicit `(6)` reads/writes exist outside `heat()` except the D26 entry check.
- Q1 (initialized before use for every cell): YES for 1..5/anp/hicp/hsnp; NO for index 6 and `danp`. Q2 (k=5 skippable before k1=6 written): YES via L249. Q3 (index 6 guaranteed valid before else-averaging): NO.
- Secondary unguarded index-6 reads: leads loops L467/L485-486 and else-averaging L510-511 (def0cb0: L499-500).

### 20.3 TASK 2/3 — Patient Zero found (April TRACE, `stage11.4_d27_apr7trace`)

- `D27_PATIENT_ZERO day=1 i=2 j=95 k=5 site=3` — site 3 = `thermodynamics.f90:442` `spar(k1) = (spar(k1)*dzz - sicst(k)*a_tmp)/b_tmp` (growth branch). First-fire latch: exactly one report (no log flood).
- Operands: `anp(5)`=1.0, `hicp(5)`=0.0, `hsnp(5)`=0.0, `sicst(5)`=4e-3 — a ghost-ice cell (full category-5 area, zero thickness). `old_spar6`=-2749.86 (finite stale garbage from earlier cells in scan order), `new_spar6`=NaN.
- Generator mechanism (forced by printed operands): with `hicp(5)`=0, L384 `dhic = dt/302e6*(2.04*(tfr-tti)/0.0 - fw)` = ±Inf → `a_tmp`=±Inf → `b_tmp`=dzz-a_tmp=∓Inf → `(finite∓Inf)/∓Inf` = NaN at L442. First NaN creation in the run; the D26 (2,2) `0*NaN` is downstream carriage via shared scratch (scan order j=1..js: (2,95) poisons scratch used by later cells/substeps).
- Pre-existing finite garbage (`old_tpar6`=148765.4 K, `old_spar6`=-2749.86) shows the scratch channel carries unphysical-but-finite values before the first NaN; writers of that garbage are outside D27 scope (finite, not NaN).

### 20.4 TASK 3 — controlled INIT experiment (April, `stage11.4_d27_apr7init`)

- `STAGE114_D27_INIT=true` sets `tpar(6)=twa`, `spar(6)=a` per cell after the init loop (same background as indices 1..5; diagnostic-only). Effect confirmed: `old_tpar6`=274.30, `old_spar6`=0.0337 (finite, staleness removed).
- Result: NaN REMAINS — same cell/site/operands (`new_spar6`=NaN). Verdict: STRONG EVIDENCE that staleness is the CARRIER (explains (2,2) inheritance) while the in-cell `hicp`=0 division chain is the GENERATOR. INIT is NOT a fix (and is not proposed as one). Downstream trajectory shifts slightly under INIT (B3.3 Day-1 maxU2 27 vs 0.0), as expected for an experiment.

### 20.5 TASK 4 — January comparison

- Jan TRACE (`stage11.4_d27_jan7trace`, 30 days, exit 0): ZERO D27 firings, no FIRST-INVALID event. Index 6 stays finite all run — the ghost-ice + zero-thickness generator path never triggers under January state (thicker/healthier ice; k=5 always has thickness where it has area).
- Jan-vs-Apr difference: April melt produces `anp(5)`≈1/`hicp(5)`=0 cells (area without volume); January does not. The generator precondition is a state property, not a code-path difference.

### 20.6 Validation: OFF bit-identity to `def0cb0`

- Jan OFF (`stage11.4_d27_jan7off`, no env flags): EUU bit-identical to the D22 baseline Days 1-8+; all 32 output `.nc` files md5-MATCH the `def0cb0`-code run (`stage11.4_d26_jan7off`); exit 0; zero diagnostic artifacts (no CSVs, no fort.*).
- New code (module `src/stage114_d27_trace.f90`, 6 hook sites in `thermodynamics.f90`) executes only reads + early-return calls when flags are OFF.

### 20.7 Decision and limitations

- Classification: spar-NaN generator at L442 under `hicp(5)`=0 MATHEMATICALLY ESTABLISHED (finite printed inputs → NaN through that single expression; the ±Inf-vs-0/0 flavor of the L384 intermediate was not printed — minor, unisolated). Stale-scratch carriage CONFIRMED (D26 entry snapshot + D27 old-values). Nothing is called "root cause" beyond this established chain.
- Limitations: patient-zero substep `iii` unrecorded (`heat()` signature untouched — no `iii` param); finite-garbage writers not traced; (2,2,1) is first-found scan-order victim, uniqueness not proven.
- NO production fix applied; NO physics changed (only diagnostic additions, OFF-equivalent). D28 NOT started.

## 21. Stage 11.4-D28 Ghost-Ice provenance forensics (frozen 2026-09-28)

### 21.1 Correction to D27: no finite ghost state exists

- D27 reported `anp(5)`=1.0/`hicp(5)`=0.0 and called it "ghost ice". D28 refines this: the `hicp`/`hsnp`=0.0 in the D27 trap are POST-ZEROING locals (snow-branch `else {hicp=hsnp=0}`, `thermodynamics.f90` snow case), NOT a global state. The true global state at patient zero (same-run interleaved capture, `heat(iii=4)`): `an1(2,95,6)`=1.0, `wice1(2,95,5)`=NaN, `hsnow`=3.45e-6. A finite (`an1`=1, `wice1`=0) state was NEVER observed at any checkpoint in any run.
- Snow-branch dependence confirmed: at `heat(iii=3)` (`hsnow`=0, case 1, finite-denominator melt branch) the identical (1.0, NaN) input passes WITHOUT firing; at `heat(iii=4)` (`hsnow`=3.45e-6, case 2, L384 `/hicp` division) it fires. D27 §20 stands except "ghost-ice cell" phrasing, superseded here.

### 21.2 Pre-HEAT state and decoupling checkpoint (April, `stage11.4_d28_apr7*`)

- INIT (after init `redis`, `main.f90:330`) and all of Day-1 `iii=1`: (2,95,5/6) all zeros. Ice init files (`1_1.ice`..`1_5.ice`, shared symlinks, `wice1`=char-thickness×`an1` by construction `main.f90:321-325`) EXONERATED for this cell; all-5-category patch zeros confirmed by direct file read.
- First anomaly at POST_ADV `iii=2`: `an1`/`wice1`=NaN at (2,95),(3,95),(2,96),(3,96); (1,95),(1,96),(·,94) stay zero. PRE_HEAT `iii=2` was fully clean (zeros incl. neighborhood + ice/ocean velocities).
- POST_REDIS `iii=2` manufactures the signature: `an1`=1.0, `wice1`=NaN — via the stage-5 fallback `src/ice_redis.f90:234-236` (`anpr(ngr)=1.0; wicpr(ngr)=a3` with `a3`=NaN after the NaN-poisoned redistribution loop exhausts). THIS is the exact constraint-breaking code (`WICE1>0 ⟺ AN1>0` violated by construction when inputs are NaN).

### 21.3 Importer, carrier chain, and exonerations

- Importer: `adv2d` (independent FCT advection of AN1/WICE1, `main.f90:753-766`) transports NaN into (2,95) at `iii=2` from NaN ice velocities at (2,96),(3,96) (same checkpoint: ice u/v NaN there, zeros at (2,95),(3,95)). `adv2d` creates nothing — finite inputs give finite outputs.
- Boundary restores (`main.f90` adv2d loop: row `js`/column 1 kept) touch only row `js`/column 1; (2,95) is interior → EXONERATED as direct cause. EN4 ocean init does not touch ice arrays → EXONERATED structurally (ice files identical Jan/Apr anyway).
- Ocean EXONERATED at the infection point: `u2`/`v2`(2:3,95:96,1) all zeros at POST_ADV `iii=2` (same checkpoint). Full chain: ice-dynamics u/v NaN (iii=2) → adv2d import → REDIS fallback (1.0, NaN) → heat site-3 scratch NaN (iii=4) → `advs` → zombie (April day-01: T/S/ro 142081/142081 NaN; `ice_thickness` 249 NaN, 247 in cat 5).

### 21.4 Open micro-question → D29 (intra-dynamics line NOT isolated)

- Ice u/v NaN at (2,96),(3,96) during dynamics `iii=2` with: zero neighborhood ice (all-5-cat patch zeros → `hices`=0 → `hht`=0 → guard `hht<0.01 → u=v=0` SHOULD have fired), finite ocean `u2`/`v2`=0, `aa=a1²+b1²≥1` structurally safe (`main.f90:738-739`). No other ice-u/v writers exist repo-wide (verified: solver/guard/boundary only; `deform`/`stress`/`adv2d`/`heat`/`redis` do not write u/v).
- Candidates (unisolated): NaN `ym2` (sea level) via the `c11·Δym2` term (`main.f90:726-729`), or a memory/guard-path subtlety. Requires direct dynamics-block instrumentation (hht/aa/ym2 trap) — explicitly D29 scope. Nothing here is called "root cause" beyond the established chain.

### 21.5 Jan vs Apr (control: `stage11.4_d28_jan7trace`)

- Jan Day-1: all checkpoints zeros (37 STATE lines, zero GHOST), full run clean; day-01 T/S/ro/`ice_thickness`/`snow_depth` zero NaN vs April fully-NaN ocean + 249 ice NaN.
- Structural difference: identical local patch state (zeros) through `iii=1`; divergence ignites in April dynamics at `iii=2` from outside the patch (April wind/sea-level state or far-field ice stress vs January). Ice init identical by construction.

### 21.6 Validation

- OFF (`stage11.4_d28_jan7off`, no env flags): all 32 output `.nc` md5-MATCH the D27-code run; exit 0; zero diagnostic artifacts. New code (`src/stage114_d28_trace.f90`, 6 call sites in `app/main.f90`) is reads+prints only when armed.
- NO guards, NO clamps, NO equation/scheme/init changes. Forensic only.

## 22. Stage 11.4-D29 ice-dynamics NaN snapshot (frozen 2026-09-28)

### 22.1 First intra-dynamics NaN: `hht`, guard fails per IEEE 754 (CONFIRMED)

- `D29_GUARDA day1 iii=2 jjj=1` fired for (2,96): `hices`=[NaN, 0.01169, 0, 0], `hht`=NaN, `guard(hht<0.01)`=F. Same for (3,96): `hices`=[0, 0, NaN, 0.01169] (its stencil reads the NaN from (2,96)). The guard does NOT fire on NaN (`NaN<0.01`=FALSE) and execution proceeds into drag/stress — IEEE guard-failure hypothesis CONFIRMED at the exact guard line (`main.f90:684`).
- First intra-dynamics NaN variable = `hht` (computed inside the block from outer `hices`; all other solver inputs printed finite: uij/vij=0, water 0/0, tx/ty finite, fku finite, ym2×4=0, sxx/syy/sxy×12=0).

### 22.2 Full propagation chain (printed, `D29_SOLVE` same microstep)

- `hht`=NaN → `a=c17*|Vrel|/hht`=NaN (L700; `b`=0.0 finite) → `txic`/`tyic`=NaN → `b3=hht*9100`=NaN → `a2`/`b2`=NaN (`tx`/`b3`, `c11`-terms) → `fa1`/`fb1`/`fa2`/`fb2`/`aa`=NaN → `unew`/`vnew`=NaN (L739-740). Complete chain in one snapshot; `aa`-division (L738-739) is structurally safe (`aa≥1`) and is a carrier here, not a generator.

### 22.3 `a3` hypothesis: REJECTED (clean)

- No `D29_GUARDB` fire in any run: `ans`/`a3` finite at both cells (`a3`-guard behaved normally). The `a3>2.0` path is NOT a NaN vector on Day 1.

### 22.4 Outer state notes (one hop remains → D30)

- `hices(2,96)`=NaN is pre-existing outer state at dynamics entry (first writer unisolated: heat-Inf→REDIS-NaN vs advected-NaN in cats 1-4, which D28 hoods never printed — blind spot). `hices(2,95)`=`hices(3,95)`=0.01169 finite (thin low-category ice, legitimate).
- Nothing beyond the established chain is called "root cause": the intra-dynamics mechanism (guard failure + propagation) is MATHEMATICALLY ESTABLISHED by printed operands; the `hices(2,96)` first-writer is the explicit D30 question.

### 22.5 Jan vs Apr

- Jan TRACE (`stage11.4_d29_jan7trace`, 30 days, exit 0): ZERO D29 prints — `hht`/`a3`/solver clean all run. April ignites at Day-1 `iii=2` `jjj=1` from outer `hices` state; January never develops it.

### 22.6 Validation

- OFF (`stage11.4_d29_jan7off2`, final source incl. whitespace restoration): all 32 `.nc` md5-MATCH the D28-code run; exit 0; zero artifacts. New code (`src/stage114_d29_trace.f90`, use-line + 2 locals + 4 main.f90 call sites with integer pre-guards) is reads+prints only.
- NO guards, NO clamps, NO equation/guard-condition/init changes. Forensic only.

## 23. Stage 11.4-D30 category decomposition of hices(2,96) (frozen 2026-09-28)

### 23.1 First-NaN category: k=1, transition inside heat(iii=2)

- INIT and PRE_HEAT `iii=1`: (2,96) all 5 categories zero (all ice files read directly: 3×3 patch zeros in every `1_k.ice`).
- `heat(iii=1)` forms legitimate 1 cm new ice (freezing, `hfirst`>0): redis632 `iii=1` shows `anpr(1)`=1.0, `b1`=0.01. POST_ADV `iii=1` (edge advection, finite): cat-1 `an1`=0.25/`wice1`=2.5e-3 (coupled, `hices`=0.01); cats 2-5 zero.
- PRE_HEAT `iii=2` (cat-1: 0.25/2.5e-3/`hices`=0.01, rest zero) → redis632 `iii=2` output (cat-1: `an1`=1.0/`wice1`=NaN; cats 2-5 zero) — `heat()` is the only writer between these checkpoints. FIRST NaN confined to CATEGORY 1 (`D30_REDIS_NAN`: `a1`=1.0, `b1`=NaN, `wicpr` NaN only at k=1).
- Area 0.25→1.0 regrowth carries the new-ice-formation signature (`anp(1)`=`ann1`+`a2`); volume turns NaN in the same call.

### 23.2 Heat-internal narrowing (`D30_HEATK`, same run)

- `D30_HEATK day1 iii=2 k=1`: `anp`=0.25, `hicp`=NaN, `hsnp`=0.0, `dhic`=-4.43e-3 (FINITE bottom term), `dhsn`=0, `twa`=274.30 (finite), `tpar`/`spar` finite.
- By elimination over the finite printed operands (init `hicp`=0.01, finite `dhic`, finite `twa`), the NaN entered via the unprinted surface term `dhic1` (melt-branch energy balance: `a1`/`el`/`tts`/`tfr` chain) — STRONGLY SUPPORTED, expression-level operand (`tfr`-NaN vs `el`-NaN) unisolated → D31. The bottom-term division (D26 candidate L384) is EXONERATED for this event (`dhic` finite).

### 23.3 adv2d / boundary audit

- `D30_ADVK iii=1`: all cats finite post-adv (adv clean when velocities clean). `D30_ADVK_NAN iii=2`: all 5 cats NaN SIMULTANEOUSLY — velocity-driven import (ice u/v already NaN from dynamics), not single-face/boundary corruption. Boundary restores touch only row `js`/column 1 (`main.f90` adv loop); (2,96) interior → NOT culprits. adv2d = importer, confirmed again.

### 23.4 Jan vs Apr

- Jan TRACE: 0 NaN flags in any category/checkpoint; PRE_HEAT `iii=2` (2,96) fully ice-free — January forms NO new ice there in `iii=1` (no freezing), so the thin-ice NaN substrate of heat(`iii=2`) never exists. Structural difference = April freezing at this cell (thermodynamic regime), not code path or init (identical files).

### 23.5 Classification and validation

- MATHEMATICALLY ESTABLISHED: first-NaN category (k=1), transition window (inside `heat(iii=2)`), importer (adv2d), manufacturer (`ice_redis` fallback), intra-dynamics mechanism (D29 guard failure). STRONGLY SUPPORTED: surface-term (`dhic1`) generator. OPEN → D31: exact `dhic1` operand and the physically correct fix design.
- OFF (`stage11.4_d30_jan7off`): 32/32 `.nc` md5-MATCH the D29-code run; exit 0; zero artifacts. NO guards/clamps/equation/scheme/init changes (reads+prints only).

## 24. Stage 11.4-D31 dhic1 operands and temporal causality (frozen 2026-09-29)

### 24.1 Exact NaN operand in dhic1 (`D31_DHIC1`, heat Day-1 iii=2 k=1 at (2,96))

- Printed: `hicp_before`=0.01, `hicp_after`=NaN, `dhic1`=NaN; `tta`=273.15, `twa`=274.30, `tts`=273.15, `tfr`=271.33 (ALL FINITE — ocean T/S clean, Luna-downstream concern REJECTED for this cell); `hhum`=0.0, `a3`=NaN, `el`=NaN, `sh`=-0.0, `sw`=10.92, `wl`=226.26, `a1`=NaN, `b`=204.
- Generator: `a3 = 0.6650735*ratm/ppatm*ww` = NaN (only NaN input; `el` fixed pre-loop NaN) → Newton iter-1 `dtts`=NaN → while-check (`NaN>=0.25`)=FALSE exits after 1 iter → fallback check (`NaN>=100`/n==100)=FALSE keeps `tts`=NaN → branch check (`NaN<=273.15`)=FALSE enters melt branch → `dhic1`=NaN → `hicp`=NaN (zero-guard FALSE). Three IEEE-false comparisons route INTO the melting path.

### 24.2 a3=NaN root input: ERA5-skipped edge cell (ESTABLISHED)

- Cell (2,96) = (64.9578°N, 36.2516°E) from KOORD.DAT; April file `era5_2020_04_merged.nc` latitude axis starts at 65.0°N → bilinear returns ok=false → `cycle` (`wind_forcing.f90:266-270`) → meteo arrays stay at init 0.0 persistently (only u10 `ok` is checked, L267-270; later fields unchecked).
- Corroboration (independent): run log `ERA5 WIND WARNING: 55 model points outside ERA5 latitude range`; exactly 55/13965 model cells have lat<65.0; `p1` min = 0.0; runtime zeros at (2,96): `hhum`=0.0, `patm`=0, `tx`=`ty`=0, `tta`=273.15 (=0.0°C init), `dhsn`=0; `sw`/`wl` finite (computed downstream from `cz`/`tta`).
- Mechanism: `ppatm`=0 → `ratm`=0 → `a3`=(0.665·0)/0·ww = 0/0 = NaN (any `ww`). PRIMARY SOURCE, mathematically and temporally established (no physics claim beyond this chain).

### 24.3 Temporal causality (first NaN inside heat(iii=2))

- POST_HEAT iii=1: cat-1 1.0/0.01 FINITE (open-water `tfr`-fallback forms legitimate new ice despite NaN `qn`: NaN-comparisons route to `tfr`, finite). PRE_DYN/POST_DYN iii=1: finite. PRE_HEAT iii=2: 0.25/2.5e-3 finite.
- `D31_DHIC1` fires during heat(iii=2); PRE_DYN iii=2 already GHOST (1.0/NaN). FIRST NaN is created inside heat(iii=2,k=1) — NOT pre-existing (Luna caution resolved by brackets: pre-heat finite, dhic1-NaN intra-heat, post-heat NaN).
- Downstream (frozen, D25-D30): redis632 → `hices`=NaN → dynamics guard failure → ice u/v NaN → adv2d import → REDIS fallback (1.0,NaN)@(2,95) → heat scratch → `advs` → (2,2) S1-NaN → zombie (April day-01 T/S/ro fully NaN; Jan fully clean).

### 24.4 Jan vs Apr

- Jan TRACE: 0 NaN flags; Jan file latitude starts at 63.0°N → (2,96) covered (no skip warning); Jan forms no new ice at (2,96) (PRE_HEAT iii=2 ice-free). April diverges by (a) out-of-coverage meteo zeros at edge cells AND (b) freezing that creates the executing thin-ice category. Ice init files identical.

### 24.5 Validation

- OFF (`stage11.4_d31_jan7off`): 32/32 `.nc` md5-MATCH the D30-code run; exit 0; zero artifacts. NOTE (env): post-reboot `/tmp` rebuilds regenerated via documented D22 procedure (April values verified identical: T −2.17…6.75). NO guards/clamps/equation/scheme/init changes (reads+prints only).
