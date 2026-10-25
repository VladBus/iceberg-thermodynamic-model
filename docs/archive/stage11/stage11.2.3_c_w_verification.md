# 11.2.3 C — W Verification (Post `end if` Fix, `main.f90` ~868)

**Status**: Source fix verified (`end if` at `main.f90` line ~872, replacing erroneous `end do`); numerical verification PARTIAL (90-day `STAGE112_CFL_DIAG` baseline confirms `W` safe; event-step measurement PENDING — requires `STAGE112_FIRST_INVALID=true` production/prognostic capture). **No production physics change.**

---

## Source-level verification (post-fix inspection)

File: `app/main.f90`, W-computation block (verified by `sed -n '856,870p'` after edit at `02e54dc`):

- `w(i, j, 1) = a`
- `ym1(i, j) = ymm`
- `if (ki .ge. 2) then` ... `w(i, j, k) = a` (loop `k = 2, ki`) ... `end if`
- The `end if` (line ~872) correctly closes the `ki .ge. 2` condition; the `end do` (line ~873) closes the `do` loop.
- Formula preserved: `W(k) = W(k-1) - C9·DZ1(k-1)·(TT(k-1) + SS(k-1))` with `TT = ∂U/∂x`, `SS = ∂V/∂y`.
- No physics change: same formula, same coefficients (`C9`, `DZ1`, `TT`, `SS`), same vertical levels (`k = 2..ki`).

---

## Numerical verification (11.2 diagnostic baseline)

From `docs/validation/stage11.2_cfl_numerical_audit.md` (§4 results, §3 vertical CFL definition):

| Metric | 90-day baseline | Near-divergence (preliminary, Day 4-5) | Assessment at event |
| --- | --- | --- | --- |
| `max |W|` | 0.168 cm/s (§4, line 109) | < 0.2 cm/s (no spike detected) | Very low |
| `max Cz = |W|·DT/dz` | 0.105 (§4, line 101) | < 0.15 (preliminary) | **SAFE (< 1)** |
| Finite/non-finite | All finite (90-day offline; no `STAGE112_FIRST_INVALID` trigger) | Unknown at exact divergence cell/time | **PENDING** — requires `STAGE112_FIRST_INVALID=true` production-coupled capture |
| Temporal ordering | No abnormal `W` before divergence (low magnitude throughout) | `W` remains low; divergence originates in density/CA (`Day 4 s1` ρ-flip; `Day 5 s6` `CA_after ro_nan=198`) — consistent with 10.22 audit chain | `W` NOT divergence trigger |

---

## Critical gap (per 11.2.3 Section C requirements)

To fully close `C` with event-level evidence (per 11.2.3 §7: `STAGE112_FIRST_INVALID=true` production/prognostic capture):

- Exact `(i, j, k)` and `III` (baroclinic step) where `W` first becomes abnormal/non-finite concurrent with divergence.
- `min(W)`, `max(W)`, `max(|W|)` at `III = 5` and `III = 6` of Day 5 (step where `CA_after ro_nan = 198` occurs at `F_after_conv` per 10.22 audit §5).
- `Cz` specifically at divergence cell (`i, j`) and step (`III = 6`, Day 5).
- Confirmation that `W` remains finite at exact instant when `ro` first becomes NaN (`CA_after ro_nan=198`, `U/V/T/S` clean — per 10.20 audit §4).

Without `STAGE112_FIRST_INVALID=true` executed in a production/prognostic January run reaching Day-5 divergence, these event-step measurements cannot be confirmed. The 90-day offline baseline supports the preliminary conclusion (`W` safe, `Cz` < 1) but does not provide the event-level measurement.

---

## Next: D — `wind_max`

Status: deferred; requires tracing source variable in `main.f90` / diagnostic module; per 11.2.3 Section 4: do NOT interpret from variable name alone; must establish formula, source, units, temporal scope.
