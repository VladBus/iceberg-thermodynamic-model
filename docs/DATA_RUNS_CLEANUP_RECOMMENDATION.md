# data/runs Cleanup Recommendation
**Status:** RECOMMENDATION ONLY — no files deleted, moved, compressed, or archived.
**Date:** 2026-10-26
**Base:** `531bbfa` (Stage 11 closed)

## Summary

Total size: **82.583 GB / 289 runs**.  
Potential savings: **37.327 GB** (45.2% reduction).

| Class | Count | Size | Action |
|---|---:|---:|---|
| CRITICAL | 83 | 31.734 GB | Keep as-is |
| ARCHIVE | 153 | 40.563 GB | tar + gzip (~3x) |
| TEMPORARY | 47 | 8.629 GB | Delete after review |
| DUPLICATES | 6 | 1.656 GB | Keep newest only |

Archive estimated compressed size: **13.521 GB**.

## Recommendations (NOT executed)

### ARCHIVE (153 runs, 40.563 GB)

Compress with tar + gzip after verifying the archive. Example (do not run until approved):

```bash
tar -czf runs_archive_YYYY-MM-DD.tar.gz --files-from=archive_run_list.txt
```

Full list:

```
e2_fatal_test
e2_synth_test
e2_synthpresent_test
stage11.1_apr7
stage11.1_frozen_jan7
stage11.1_jan7
stage11.1_jul7
stage11.1_oct7
stage11.2_cfl_test
stage11.3C1_AprA
stage11.3C1_AprB
stage11.3C1_AprC
stage11.3C1_AprD
stage11.3C1_AprE
stage11.3C1_jan7off
stage11.3C_AprA
stage11.3C_AprB
stage11.3C_AprC
stage11.3C_AprD
stage11.3C_AprE
stage11.4_d24_apr7ev
stage11.4_d32_apr7fix
stage11.4_d32_jan7fix
stage11.4_d32_jul7fix
stage11.4_d32_oct7fix
stage11.4_d33_apr30
stage11.4_d33_jan30
stage11.4_d33_jul30
stage11.4_d33_oct30
stage11.4_eosApr
stage11.4_eosJan
stage11.4_eosJul
stage11.4_eosOct
stage11.4_legApr
stage11.4_legJan
stage11.4_legJul
stage11.4_legOct
stage11.5B_AprA
stage11.5B_AprB
stage11.5B_AprC
stage11.5B_AprD
stage11.5B_AprE
stage11.5B_AprF
stage11.5B_AprG
stage11.5B_AprH
stage11.5B_AprI
stage11.5C1_AprN1trace
stage11.5C1_AprN24freeze
stage11.5C1_AprN24trace
stage11.5C1_janOFF2
stage11.5C2_AprA_gain
stage11.5C2_AprB_cplfreeze
stage11.5C2_AprC_heatfreeze
stage11.5C2_janOFF
stage11.5C3_AprA_ctrl
stage11.5C3_AprB_tsfreeze
stage11.5C3_AprC_reg
stage11.5C3_janOFF
stage11.5C4_AprA_ctrl
stage11.5C4_Apr_ANS
stage11.5C4_Apr_HICE
stage11.5C4_Apr_HSNOW
stage11.5C4_Apr_UV
stage11.5C4_Apr_UV_HICE
stage11.5C4_janOFF
stage11.5C5_AprN1
stage11.5C5_AprN24
stage11.5C5_janOFF
stage11.5C6R_AprN24
stage11.5C6R_janOFF
stage11.5C6_AprN24
stage11.5C6_fast
stage11.5C7_janOFF
stage11.5C7_terms
stage11.5C7_track
stage11.5C81_AprN24
stage11.5C81_janOFF
stage11.5C82_AprN24
stage11.5C82_janOFF
stage11.5C8_AprN24
stage11.5C8_janOFF
stage11.5C_AprA
stage11.5C_AprB
stage11.5C_AprC
stage11.5C_AprD
stage11.5C_AprE
stage11.5C_janOFF
stage11.5D1_AprLegacy
stage11.5D1_AprN1
stage11.5D1_AprN12
stage11.5D1_AprN2
stage11.5D1_AprN24
stage11.5D1_AprN4
stage11.5D1_AprN6
stage11.5D1_JanN1
stage11.5D1_JanN24
stage11.5D2_ExpB
stage11.5D2_ExpC
stage11.5D2_ExpD
stage11.5D2_janOFF
stage11.5D3_JanDT150
stage11.5D3_JanN1
stage11.5D3_dt150full
stage11.5D3_dt1800
stage11.5D3_dt225
stage11.5D3_dt225full
stage11.5D3_dt450
stage11.5D3_dt450full
stage11.5D3_dt450x
stage11.5D3_dt900
stage11.5E_JanDT150
stage11.5E_JanDT225
stage11.5E_JanN1
stage11.5F_F3
stage11.5F_JanDT150
stage11.5F_JanN1
stage11.5G_B150SKZ
stage11.5G_JanDT150
stage11.5G_JanN1
stage11.5HRC_JanN1
stage11.5HRC_Smoke
stage11.5H_JanN1
stage11.5H_JanProd
stage11.5H_LegApr
stage11.5H_ProdApr
stage11.6_A
stage11.6_B
stage11.6_C
stage11.6_D
stage11.6_JA
stage11.6_JB
stage11.6_JC
stage11.6_JD
stage11.7B1_JanN1
stage11.7B2_JanN1
stage11.7B3_JanN1
stage11.7B_JanN1
stage11.7C_AprN1
stage11.7C_JanN1
stage11.7D.1_JanN1
stage11.7D2_JanN1
stage11.7D_AprN1
stage11.7D_JanN1
stage11.7E_APROFF
stage11.7E_APRON
stage11.7E_JANOFF
stage11.7E_JANON
stage117e1cp_evidence
stage117e2_APROFF
stage117e2_APRON
stage117e2_JANOFF
stage117e2_JANON
stage117e2_evidence
```

### TEMPORARY (47 runs, 8.629 GB)

Review each run; delete only after confirming no active analysis reads it. Example (not executed):

```bash
rm -rf <reviewed-run-directory>
```

Full list:

```
default_eos_smoke
eos_default_legacy_md5
eos_default_legacy_md5_2
matrix_apr_eos80_n1_29d_prelim
matrix_apr_eos80_n1_30d_4step_prelim
matrix_apr_legacy_n1_29d_prelim
matrix_apr_legacy_n1_30d_4step_prelim
matrix_default_check
phase1a_default_check
phase2_default_check
scripts
stage11.5C4_probe_HICE
t3_smoke_legacy
t3c3_probe_e1
t3c4_default_check
t3c_smoke
t41_default_check
t4prep_default_check
t5c3_default_check
t5c4_default_check
t6s_default_check
test_ocean_init
test_ocean_init_allowed
test_ocean_init_en4
test_ocean_init_force
test_ocean_init_force2
test_prov_allowed
test_prov_allowed2
test_prov_allowed3
test_prov_attr_1_default_strict
test_prov_attr_2_override_strict
test_prov_attr_3_force_synthetic
test_prov_attr_4_eos80
test_prov_attr_5_legacy
test_prov_en4
test_prov_final
test_prov_force
test_prov_invalid
test_prov_off2
test_prov_on2
test_prov_strict
test_provenance
test_provenance_off
test_run
test_run_on
test_seaice_prov_off
test_seaice_prov_on
```

### DUPLICATES (6 runs, 1.656 GB)

These are rerun candidates; keep the newest copy and remove the older copy after approval.

| Candidate | Supersedes | Size |
|---|---|---:|
| `stage11.5C1_janOFF3` | `stage11.5C1_janOFF2` | 0.314 GB |
| `stage11.5C2_AprA_gain2` | `stage11.5C2_AprA_gain` | 0.307 GB |
| `stage11.5C2_AprB_cplfreeze2` | `stage11.5C2_AprB_cplfreeze` | 0.307 GB |
| `stage11.5C2_AprC_heatfreeze2` | `stage11.5C2_AprC_heatfreeze` | 0.307 GB |
| `stage11.5C2_janOFF2` | `stage11.5C2_janOFF` | 0.314 GB |
| `stage11.5C6R_AprN24b` | `stage11.5C6R_AprN24` | 0.109 GB |

### CRITICAL (83 runs, 31.734 GB)

Keep as-is; active Stage 11 validation and release evidence.

Full list:

```
default_eos80_verify
explicit_eos80_verify
legacy_fallback_verify
matrix_apr_eos80_n1
matrix_apr_legacy_n1
matrix_jan_eos80_n1
matrix_jan_eos80_prod
matrix_jan_legacy_n1
matrix_jan_legacy_prod
matrix_jul_eos80_n1
matrix_jul_legacy_n1
matrix_oct_eos80_n1
matrix_oct_legacy_n1
repro_apr_eos80
repro_jul_legacy
repro_oct_eos80
stage11.7E4_A
stage11.7E4_A7
stage11.7E4_B
stage11.7E4_B7
stage11.7E4_C
stage11.7E4_C7
t3_eos80_canonical
t3_legacy_canonical
t3_legacy_rebuild
t3_with_fixes
t3c2_ctl_30
t3c2_dt1800
t3c2_dt7200
t3c2_eos80_ro_30
t3c2_eos80_ts_30
t3c2_freeze_ro
t3c2_freeze_ro_ds
t3c2_freeze_ts
t3c2_freeze_tw
t3c2_ro_30
t3c2_ts_30
t3c2_tw_30
t3c3_all
t3c3_all_sponge
t3c3_all_sponge2
t3c3_all_sponge3
t3c3_balanced
t3c3_default_1d
t3c3_default_1d_v2
t3c3_default_final
t3c3_e1
t3c3_e2
t3c3_e3
t3c3_e3_sponge
t3c3_eos80_all
t3c3_fix_1d
t3c3_noca
t3c3_thr0
t3c4_dt1800
t3c4_dt1800_ah10000
t3c4_dt1800_ah20000
t3c4_dt1800_ah5000
t3c4_dt900
t3c_eos80_canonical
t3c_legacy_canonical
t4_wind_forcing
t4prep_rot_off
t4prep_rot_on
t5_30day_apr
t5_30day_apr30
t5_90day_jan
t5c2_config1_detailed
t5c3_90day
t5c3_90day_range
t5c3_90day_tcap
t5c3_april
t5c4_90day
t5c4_90day_postca
t5c4_april
t5c_config1
t5c_config2
t5c_config3
t5c_config4
t6s_jan_prod_eos80
t6s_jan_production
t6s_jul_legacy
t6s_oct_legacy
```

## Approval Required

This cleanup requires explicit user approval before execution. No action has been taken.

## Rollback Plan

- ARCHIVE: restore with `tar -xzf runs_archive_YYYY-MM-DD.tar.gz`; verify before deleting originals.
- TEMPORARY/DUPLICATES: cannot be recovered unless a backup/archive exists; verify first.
- CRITICAL: never include in deletion/compression.

## Evidence

- `data/validation/runs_inventory_final.json`
- `docs/validation/stage11.8B_runs_inventory.md`
