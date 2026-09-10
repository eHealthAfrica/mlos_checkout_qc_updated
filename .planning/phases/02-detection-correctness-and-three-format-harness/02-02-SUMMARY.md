---
phase: 02-detection-correctness-and-three-format-harness
plan: 02
subsystem: qc-engine
tags: [pandas, cross-table-validation, absence-predicate, tdd, integ-02]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "qc.predicates.vec_is_absent (plan 01, D-04/D-05), qc.results.register/canonical_order"
provides:
  - "qc.mlos.run_mlos_qc's R2/R3/R4 rebuilt to exclude absent source cells from the match mask and absent target values from the valid-target set"
  - "qc.takeoff.run_takeoff_qc's TP2/TP3/TP4 mirrored the same way"
  - "Six new registered identifiers: 2.missing, 3.missing, 4.missing, TP2.missing, TP3.missing, TP4.missing (D-01/D-02)"
  - "tests/fixtures.py::build_mlos_fixture_with_blanks / build_takeoff_fixture_with_blanks — reusable blank-cell fixtures for future plans"
affects: [02-03, 02-04, 02-05, 02-06]

actuals:
  tokens: 6627
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Cross-table match mask excludes an absent source cell via vec_is_absent, and the valid-target set is built from non-absent target values only (a .loc restriction, not .dropna(), since an empty string survives .dropna()) — both halves required or one blank cell produces four failing checks instead of D-03's three"
    - "A .missing identifier fires on the bare absence mask, declared immediately after its numeric/TP-prefixed sibling in the register() call sequence, so canonical_order() emission order reads 2, 2.missing, 3, 3.missing, ... unconditionally on the MLoS side (D-07) and nested inside the Takeoffpoint-side column guard on the TP side"
    - "Sidebar reference table rows for a new identifier land in the same commit as its registration, keeping tests/test_rules_reference_matches_registry.py green by construction rather than by follow-up fix"

key-files:
  created:
    - tests/test_missing_cross_table.py
  modified:
    - qc/mlos.py
    - qc/takeoff.py
    - app.py
    - tests/fixtures.py

key-decisions:
  - "Human-readable check names for the six new identifiers ('Takeoffpoint Name Missing', 'Wardcode Missing', etc.) were authored fresh, distinct from every existing check name in the same file, since tests/test_extraction_parity.py pairs MLoS checks by name and duplicate names would break that pairing."
  - "The blank-cell fixture's mismatched-non-blank row (row 2 on both sides) uses ward codes/takeoffpoint values that are simply different strings, not necessarily absent from the real boundary reference — this plan's scope is cross-table match correctness, not boundary-reference realism."

requirements-completed: [INTEG-02]

coverage:
  - id: D1
    description: "A blank on either side of R2/R3/R4/TP2/TP3/TP4 is reported as a failure under its own .missing identifier and never as a match; a blank facing a blank across a join no longer matches"
    requirement: "INTEG-02"
    verification:
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_blank_facing_blank_no_longer_reads_as_a_match"
        status: pass
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_mlos_side_match_and_missing_counts_are_exactly_one_of_three"
        status: pass
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_takeoff_side_match_and_missing_counts_are_exactly_one_of_three"
        status: pass
    human_judgment: false
  - id: D2
    description: "One blank cell produces exactly the checks D-03 specifies (three for a blank ward_code: Rule 1, 4.missing, B0) and never four — no row is counted by both a match rule and its .missing sibling"
    requirement: "INTEG-02"
    verification:
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_no_row_is_counted_by_both_a_match_rule_and_its_missing_sibling_mlos_side"
        status: pass
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_no_row_is_counted_by_both_a_match_rule_and_its_missing_sibling_takeoff_side"
        status: pass
    human_judgment: false
  - id: D3
    description: "The MLoS-side .missing trio (2.missing/3.missing/4.missing) emits unconditionally even with no Takeoffpoint table supplied; the Takeoffpoint-side trio stays silent when there is no table"
    requirement: "INTEG-02"
    verification:
      - kind: unit
        ref: "tests/test_missing_cross_table.py#test_mlos_side_missing_checks_emit_unconditionally_with_no_takeoffpoint_table"
        status: pass
    human_judgment: false
  - id: D4
    description: "The frozen-baseline values of 2/3/4/TP2/TP3/TP4 are unchanged for the shared 10-row fixture; sidebar reference documents all six new identifiers; full suite green at or above 44 passing"
    verification:
      - kind: unit
        ref: "python3 -m pytest tests/ -q (61 passed) + tests/test_rules_reference_matches_registry.py -q (2 passed) + git status --porcelain tests/baseline/ tests/test_extraction_parity.py (empty)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 2: Blank-Side Cross-Table Match Detection Summary

**Six new `.missing` findings (`2.missing`, `3.missing`, `4.missing`, `TP2.missing`, `TP3.missing`, `TP4.missing`) plus rebuilt R2/R3/R4/TP2/TP3/TP4 masks so a blank cell can no longer satisfy a cross-table match — closing INTEG-02 (F9).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-10T12:47:50Z (STATE.md, prior session marker)
- **Completed:** 2026-09-10T12:57:05Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Closed INTEG-02 (F9): `qc.mlos.run_mlos_qc`'s R2/R3/R4 and `qc.takeoff.run_takeoff_qc`'s TP2/TP3/TP4 valid-target sets are now built from non-absent target values only (`vec_is_absent`-restricted `.loc` selection, not `.dropna()`, which cannot remove an empty string under `keep_default_na=False`), **and** each match mask separately excludes rows whose own source cell is absent — the second half of the fix D-03 requires, without which one blank cell would produce four failing checks instead of three.
- Registered six new identifiers — `2.missing`, `3.missing`, `4.missing` (MLoS layer) and `TP2.missing`, `TP3.missing`, `TP4.missing` (Takeoffpoint layer) — each declared immediately after its numeric/TP-prefixed sibling, preserving `qc.canonical_order()`'s registration-order contract.
- `2.missing`/`3.missing`/`4.missing` emit unconditionally whenever their MLoS-side column exists, including with no Takeoffpoint table supplied at all (D-07); the Takeoffpoint-side trio still requires the Takeoffpoint-side column to exist, and the existing empty-frame early return in `run_takeoff_qc` is untouched.
- Updated both sidebar rule-reference tables in `app.py` (MLoS Table Rules, Takeoffpoint Rules) in the same commit as the registrations, keeping `tests/test_rules_reference_matches_registry.py` green.
- Added two new fixture builders (`build_mlos_fixture_with_blanks`, `build_takeoff_fixture_with_blanks`) carrying three deliberately different absence forms — empty string, whitespace-only, and the case-insensitive sentinel `N/A` — per column under test, plus `tests/test_missing_cross_table.py` (9 tests) proving the exact `(1, 3)` failing/total counts, the structural no-double-counted-row disjointness invariant, the D-06 subject-table-only column check, the D-07 unconditional-emission check, and the literal blank-facing-blank F9 regression.
- Full suite: 61 passed (baseline was 52 entering this plan), frozen `tests/baseline/` trio and `tests/test_extraction_parity.py` untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild the six cross-table masks and register the six .missing findings** - `69d0fc7` `feat(02-02): register six .missing findings and exclude absent cells from cross-table match masks (INTEG-02)`
2. **Task 2: Prove a blank is actually detected — blank-cell fixture builders and the INTEG-02 test** - `62dfb0c` `test(02-02): prove blank cross-table cells are actually detected (INTEG-02)`

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `qc/mlos.py` - R2/R3/R4 rebuilt on `vec_is_absent`-restricted valid-target sets plus a source-absence exclusion; `2.missing`/`3.missing`/`4.missing` registered and emitted
- `qc/takeoff.py` - TP2/TP3/TP4 mirrored the same way; `TP2.missing`/`TP3.missing`/`TP4.missing` registered and emitted; `vec_is_absent` added to the predicates import
- `app.py` - MLoS Table Rules and Takeoffpoint Rules sidebar reference tables each gained three new rows documenting the `.missing` identifiers
- `tests/fixtures.py` (new builders only) - `build_mlos_fixture_with_blanks`, `build_takeoff_fixture_with_blanks`; existing builders, `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`, `_BASE_ROW`, `_row` and `load_boundary_fixtures` untouched
- `tests/test_missing_cross_table.py` (new) - 9 tests covering exact counts, disjointness, D-06/D-07 and the F9 blank-facing-blank regression

## Decisions Made

- Human-readable check names for the six new identifiers were authored fresh and kept distinct from every existing check name in the same file (`tests/test_extraction_parity.py` pairs MLoS checks by name, so a collision would have broken that pairing).
- The blank-cell fixture's mismatched-non-blank rows use arbitrary distinct strings for ward code / takeoffpoint values rather than values chosen for boundary-reference realism — this plan's scope is cross-table match correctness (INTEG-02), not the boundary layer.

## Deviations from Plan

### Auto-fixed Issues

None — the implementation followed the plan's action text directly; no bugs, missing critical functionality, or blocking issues were discovered during Task 1 or Task 2 that required an unplanned fix.

### Acceptance/Verify Criterion Discrepancy (documented, not auto-fixed)

Task 1's third `<verify><automated>` command asserts, against the **unmodified shared 10-row fixture** with only `m.loc[m.index[0], "ward_code"]` set to `""`:

```
fired = {x["Rule#"] for x in mc + bc if "FAIL" in x["Status"]}
assert "1" in fired and "4.missing" in fired and "B0" in fired
assert "B1" not in fired
```

This command fails as literally written: `"B1"` **is** present in `fired`. This is not a defect introduced by this plan's changes — it is a pre-existing, unrelated condition already present in `tests/fixtures.py::build_mlos_fixture()` since Phase 1. Row index 2 ("Bravo") already carries `ward_code = "00000"`, a value absent from the real boundary reference, which independently fails B1 regardless of any mutation to row 0. Verified directly:

```
$ python3 -c '... bd[bd["Rule#"]=="B1"][["settlement_name","ward_code"]] ...'
  settlement_name ward_code
1           Bravo     00000
```

The plan's own environment_notes forbid modifying `build_mlos_fixture()`'s row count or content, so this pre-existing row 2 failure cannot be removed to satisfy the command as written. The underlying D-03 invariant this command intends to prove — that the *specific blanked row* fires Rule 1, `4.missing` and B0, and does **not** fire B1 for that row — was verified directly and holds exactly:

```
row0 in Rule1:      True
row0 in 4.missing:  True
row0 in B0:         True
row0 in B1:         False
```

B1's only failing row in this run is Bravo (row index 2), entirely independent of the row-0 mutation this command performs. No production code change is possible that would make this literal set-membership assertion pass without either modifying the frozen shared fixture (forbidden) or changing B1's own logic to stop reporting Bravo's genuine, unrelated ward-code mismatch (out of this plan's INTEG-02 scope and would itself be a regression). Documented per the same precedent as Plan 01's Task 3 acceptance-criterion discrepancy.

---

**Total deviations:** 0 auto-fixed. 1 documented verify-command discrepancy (pre-existing fixture condition, not a code defect; underlying invariant independently confirmed correct).
**Impact on plan:** None on correctness — the D-03 invariant this command exists to prove is verified true at the row level; the literal command's set-membership framing does not account for the shared fixture's own pre-existing, unrelated B1 failure.

## Issues Encountered

None beyond the verify-command discrepancy documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 (column normalisation, INTEG-03) can proceed independently — this plan touched no column-name-resolution code.
- The two new blank-cell fixture builders in `tests/fixtures.py` are reusable if a later plan in this phase needs its own blank-cell scenario (e.g. plan 05's B4/B5 boundary-fallback work uses a different kind of fixture and is unaffected).
- No blockers. Full suite: 61 passed, 0 failed; frozen baseline trio and `tests/test_extraction_parity.py` untouched.

## Self-Check: PASSED

All 5 key files found on disk; both task commits (`69d0fc7`, `62dfb0c`) found in git log.

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*
