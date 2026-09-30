# Stage 11.3C.3 — Historical Loop-Bound Closure (Dmitriev.txt forensic search)

Frozen 2026-09-30. TEXT SEARCH ONLY — no code, no experiments. Method:
filesystem-wide filename search + full-text search over `docs/` for loop-bound
evidence (`DO 333`, `333 CONTINUE`, Coupl1 loop structure).

## 1. Search results (absence proof)

- `find /home/vlad -iname "*dmitr*"` → zero hits. No `Dmitriev.txt`,
  `Nesterov_last.txt`, or `Coupl1.f90` exists anywhere accessible.
- `grep -rn "333 CONTINUE|DO 333"` over `docs/` → zero hits.
- Six wiki docs cite Coupl1/Nesterov only as line-number references for
  BLOCK internals (B200/B210/B280 formulas, Stage 3.3 mapping/validation,
  Stage 3.4 coupling, Stage 4.4, Stage 5.1, Stage 7.5) — none quotes loop
  bounds, daily-cycle iteration counts, or subcycling structure.
- Closest recovered facts (Stage 3.3 mapping): Coupl1 daily order
  W → [GO TO 888] → B200 → B210 → `shal()` → B280; advS/advT/conv_adj at
  Coupl1:779–846; "U1=U2 at each baroclinic step" (Coupl1:365–366).

## 2. Operator classification vs Dmitriev.txt loop

| # | Operator | Dmitriev.txt position |
|---|---|---|
| 1 | ADVS | NOT FOUND (source absent) |
| 2 | ADVT | NOT FOUND (source absent) |
| 3 | CONV_ADJ | NOT FOUND (source absent) |
| 4 | Block 200 | NOT FOUND (source absent) |
| 5 | Block 210 | NOT FOUND (source absent) |
| 6 | SHAL | NOT FOUND (source absent) |
| 7 | Block 280 | NOT FOUND (source absent) |
| 8 | HEAT | NOT FOUND (source absent) |
| 9 | Ice dynamics | NOT FOUND (source absent) |
| 10 | ADV2D | NOT FOUND (source absent) |
| 11 | W continuity | NOT FOUND (source absent) |

III-loop location (`DO 333` / `333 CONTINUE` line numbers): UNRECOVERABLE —
the file does not exist in any accessible location.

## 3. Verdict: D — UNRESOLVED

Historical ocean-vs-ice loop placement REMAINS UNKNOWN from available text.
The 11.3C.2 Option C (B-leaning) classification stands unchanged. Closure
requires: (a) recovering Coupl1.f90/Nesterov sources from the authors, or
(b) author consultation — both outside this stage.

## 4. Implications

- No reinterpretation of the 11.3C/11.3C.1 matrix beyond 11.3C.2 §5.
- Stage 11.4 (EOS-80) proceeds at reference cadence A regardless (loop
  placement does not affect the density-EOS experiment design).
- If sources surface later, reopen as 11.3C.4; do not block the roadmap.
