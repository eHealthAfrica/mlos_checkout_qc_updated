---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 05
subsystem: infra
tags: [python, package-extraction, rule-registry, haversine, pytest]

# Dependency graph
requires:
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 03)
    provides: "qc/results.py registry, qc/__init__.py facade with sort_by_registry, tests/test_extraction_parity.py's normalize_checks/normalize_detail helpers"
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 04)
    provides: "qc/mlos.py as the second relocated layer, and the qc/__init__.py import-order convention (schema, then mlos) this plan extends"
provides:
  - "qc/settlement.py — run_settlement_qc relocated verbatim, registering SQ1/SQ2/SQ2b/SQ3/SQ4; the SQ4 haversine numpy import stays function-local, unchanged"
  - "qc/takeoff.py — run_takeoff_qc relocated verbatim, registering TP2/TP3/TP4/TP5; preserves the empty-frame early return"
  - "qc/boundary.py — run_ward_boundary_qc relocated verbatim, registering B0/B1/B2/B3 last so they land at the end of canonical_order(); reads no files of its own"
  - "app.py's Settlement/Takeoffpoint/Boundary call sites now call qc.settlement/qc.takeoff/qc.boundary, each piped through qc.sort_by_registry, matching the Schema/MLoS call sites' shape; app.py defines none of the five run_*_qc functions any more"
  - "tests/test_extraction_parity.py — five new tests (three baseline-parity, two edge-case) proving all thirteen previously-unique identifiers in these layers are unchanged, plus a reusable _nan_safe application for detail frames whose pd.concat column-union produces NaN cells"
affects: [01-qc-engine-seam-and-pinned-environment (plan 06 of this phase, which relocates auto_correct_mlos through the same route), "Phase 2 (INTEG-03 partial-file degradation) inherits qc/settlement.py, qc/takeoff.py and qc/boundary.py's column-presence guards unchanged", "Phase 3 (VERDICT-06) inherits B0-B3's registration order as the mechanism that will deliver boundary checks reading in that order in every summary table and export"]

# Actuals (#2632)
actuals:
  tokens: 11600
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_nan_safe extended beyond MLoS: Settlement, Takeoffpoint and Boundary detail frames all needed the same NaN-cell normalisation the MLoS parity test introduced in plan 04 — not because any of their fixture rows carry a genuine null cell, but because pd.concat's column union across per-rule sub-frames with differing 'extra' columns (e.g. a Settlement SQ1 detail row picking up a NaN 'latitude'/'longitude' cell it never populated) produces the same float-NaN-never-equals-itself problem. This confirms the pattern is a property of the concat-based detail-frame construction, not of any one layer's data."

key-files:
  created:
    - qc/settlement.py
    - qc/takeoff.py
    - qc/boundary.py
  modified:
    - qc/__init__.py
    - app.py
    - tests/test_extraction_parity.py

key-decisions:
  - "Applied _nan_safe to all three new parity comparisons (settlement, takeoff, boundary), not just where a fixture cell is deliberately null. First run without it failed on settlement and boundary (takeoff happened to have no NaN cells in this fixture) with 'float(nan) != float(nan)' — reusing the plan 04-established sentinel-substitution pattern rather than re-deriving a new one, per that plan's own Next Phase Readiness note anticipating this."
  - "Left the raw (pre-sort_by_registry) emission order of run_ward_boundary_qc's checks list as B0, B1, B3, B2 — the same order the pre-extraction app.py already produced (B3's block appears before B2's block in the source) — rather than reordering the add() calls to force B0/B1/B2/B3 directly out of the function. Reordering the calls would be an unauthorised behaviour change under this phase's 'relocate, don't rewrite' scope; the plan's own acceptance criteria only require canonical_order() (and, downstream, the sort_by_registry-piped call site) to read B0/B1/B2/B3, which they do."

requirements-completed: []  # ENGINE-01/ENGINE-05 also declared by plan 06 (shared-ID gate, #2388) — not marked complete until every declaring plan finishes.

coverage:
  - id: D1
    description: "qc/settlement.py and qc/takeoff.py exist, each with its function relocated verbatim (SQ4's local numpy import unchanged; the Takeoffpoint empty-frame early return unchanged) plus their five and four register() calls respectively, using all thirteen frozen identifiers unchanged"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"...qc.settlement.run_settlement_qc(fixture)...qc.takeoff.run_takeoff_qc(...)...\" -> ['SQ1','SQ2','SQ2b','SQ3','SQ4'] and ['TP2','TP3','TP4','TP5']"
        status: pass
      - kind: other
        ref: "python3 -c \"qc.takeoff.run_takeoff_qc(pd.DataFrame(), pd.DataFrame())\" -> 0 checks, empty detail"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_settlement_layer_matches_baseline"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_takeoff_layer_matches_baseline"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_takeoff_layer_returns_nothing_for_an_empty_frame"
        status: pass
    human_judgment: false
  - id: D2
    description: "qc/boundary.py exists with run_ward_boundary_qc relocated verbatim (both B0 emission paths preserved: the missing-column early return and the normal add()-closure path), registering B0/B1/B2/B3 last so canonical_order() ends with them in that order; the layer reads no file of its own — ref_df/bbox_df stay parameters, and BOUNDARY_REF_PATH/BOUNDARY_BBOX_PATH/load_boundary_refs all stay in app.py"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"...qc.boundary.run_ward_boundary_qc(fixture, ref, bbox)...\" -> checks include B0-B3; qc.canonical_order()[-4:] == ['B0','B1','B2','B3']"
        status: pass
      - kind: other
        ref: "python3 -c \"...dropped ward_code column...\" -> 1 check, Rule# 'B0', empty detail"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_boundary_layer_matches_baseline"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_boundary_layer_reports_a_missing_ward_code_column"
        status: pass
      - kind: other
        ref: "grep -c 'read_csv' qc/boundary.py -> 0; grep for BOUNDARY_REF_PATH/BOUNDARY_BBOX_PATH/load_boundary_refs in qc/boundary.py -> none found"
        status: pass
    human_judgment: false
  - id: D3
    description: "app.py no longer defines run_settlement_qc, run_takeoff_qc or run_ward_boundary_qc; all five QC layer call sites (Schema, MLoS, Settlement, Takeoffpoint, Boundary) now call through the qc package and pipe their result through qc.sort_by_registry; load_boundary_refs and auto_correct_mlos remain in app.py untouched"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"import ast...\" -> app.py's top-level function names contain none of run_settlement_qc/run_takeoff_qc/run_ward_boundary_qc, still contain load_boundary_refs and auto_correct_mlos"
        status: pass
      - kind: other
        ref: "grep -c 'sort_by_registry' app.py -> 5"
        status: pass
      - kind: integration
        ref: "python3 -m pytest tests/test_extraction_parity.py -q -> 7 passed"
        status: pass
      - kind: integration
        ref: "python3 -m pytest tests/ -q -> 28 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "canonical_order() now returns 40 distinct identifiers total (2 Schema + 25 MLoS + 5 Settlement + 4 Takeoffpoint + 4 Boundary), ending B0, B1, B2, B3, and every module under qc/ still imports with no UI-framework dependency"
    requirement: "ENGINE-05"
    verification:
      - kind: other
        ref: "python3 -c \"import qc; o=qc.canonical_order(); print(len(o), len(set(o))==len(o), o[-4:])\" -> 40 True ['B0','B1','B2','B3']"
        status: pass
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py (re-run, now covering qc/settlement.py, qc/takeoff.py, qc/boundary.py)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The detection power of the three new parity tests is real, not vacuous: mutating qc/settlement.py's SQ4 distance threshold makes test_settlement_layer_matches_baseline fail on the diverging field, and the change is fully reverted afterward"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "manual mutate-and-revert: first tried raising the threshold (d < 30 -> d < 3000), which did NOT trip the test (all 8 valid rows were already flagged at 30m — the check was already saturated at 8/8); lowering it instead (d < 30 -> d < 1) correctly failed naming 'Failing Rows' (actual=7, expected=8); reverted -> 28 passed, diff against qc/settlement.py at HEAD is empty"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 05: Settlement, Takeoffpoint and Boundary Relocation Summary

**`run_settlement_qc`, `run_takeoff_qc` and `run_ward_boundary_qc` now live in `qc/`, registering the thirteen previously-unique SQ/TP/B identifiers unchanged, and every one of the five QC layers is now called from `app.py` through the package, piped through `qc.sort_by_registry`.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-09T20:10:17Z
- **Completed:** 2026-09-09T20:22:00Z
- **Tasks:** 3 of 3 completed
- **Files modified:** 6 (3 new modules, 3 modified)

## Accomplishments
- `qc/settlement.py` and `qc/takeoff.py` relocate `run_settlement_qc`/`run_takeoff_qc` verbatim — SQ4's function-local `numpy` import and the Takeoffpoint layer's empty-frame early return both survive unchanged — registering nine frozen identifiers (SQ1, SQ2, SQ2b, SQ3, SQ4, TP2, TP3, TP4, TP5) between them.
- `qc/boundary.py` relocates the phase's second-largest function (154 lines) verbatim, registering B0-B3 last so `canonical_order()` ends with them in registration order — the mechanism Phase 3's VERDICT-06 will depend on for boundary checks to read in that order everywhere. Both B0 emission paths (missing-column early return, and the normal `add()`-closure path) survive.
- `app.py` calls all five QC layers — Schema, MLoS, Settlement, Takeoffpoint, Boundary — through the `qc` package, each piped through `qc.sort_by_registry`, and no longer defines any of the five `run_*_qc` functions itself. `load_boundary_refs` and its two path constants stay in `app.py`; no file path handling crosses into `qc/`.
- `tests/test_extraction_parity.py` gains five new tests: three baseline-parity tests (settlement, takeoff, boundary) asserting every field including the identifier is unchanged from the frozen pre-extraction record, and two edge-case tests (Takeoffpoint's empty-frame skip, Boundary's missing-column early return). All three new parity tests needed the `_nan_safe` sentinel substitution plan 04 introduced for MLoS, extending it to a case that plan didn't anticipate: NaN cells arising from `pd.concat`'s column union across per-rule detail frames, not just from a genuinely-null fixture cell.
- `qc.canonical_order()` now holds 40 distinct identifiers across all five layers; the full suite is 28 passed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate the Settlement and Takeoffpoint layers** - `8b52c95` (feat)
2. **Task 2: Relocate the Boundary layer** - `8c1ce17` (feat)
3. **Task 3: Rewire app.py for all three layers and prove nothing changed** - `3cd8a91` (test)

**Plan metadata:** committed alongside this summary

_Note: Task 3 carried `tdd="true"`, but as with every prior plan in this phase, the "implementation" under test (the three relocated layers, already produced by Tasks 1-2) already existed and was already correct by the time the parity tests were written — there was no separate GREEN-phase production code to write against a failing test. Detection power was verified via a manual mutate-and-revert cycle on `qc/settlement.py`'s SQ4 threshold instead, per the task's own acceptance criterion (see Deviations below for a nuance found during that check)._

## Files Created/Modified
- `qc/settlement.py` - new; `run_settlement_qc` relocated verbatim, 5 `register()` calls (SQ1/SQ2/SQ2b/SQ3/SQ4), function-local `numpy` import unchanged
- `qc/takeoff.py` - new; `run_takeoff_qc` relocated verbatim, 4 `register()` calls (TP2/TP3/TP4/TP5), empty-frame early return unchanged
- `qc/boundary.py` - new; `run_ward_boundary_qc` relocated verbatim, 4 `register()` calls (B0/B1/B2/B3, registered last), both B0 emission paths preserved, no file reading
- `qc/__init__.py` - modified; imports `settlement`, `takeoff`, then `boundary`, in that order after `mlos`
- `app.py` - modified; three `run_*_qc` definitions deleted (310 lines net removed); the three call sites now call `qc.settlement.run_settlement_qc` / `qc.takeoff.run_takeoff_qc` / `qc.boundary.run_ward_boundary_qc`, each piped through `qc.sort_by_registry`
- `tests/test_extraction_parity.py` - modified; added `test_settlement_layer_matches_baseline`, `test_takeoff_layer_matches_baseline`, `test_boundary_layer_matches_baseline`, `test_takeoff_layer_returns_nothing_for_an_empty_frame`, `test_boundary_layer_reports_a_missing_ward_code_column`; applied `_nan_safe` to all three new detail comparisons

## Decisions Made
- **Applied `_nan_safe` to all three new parity comparisons**, not only where a fixture is known to carry a deliberate null cell. See Deviations below.
- **Left `run_ward_boundary_qc`'s raw checks-list emission order as B0, B1, B3, B2** (matching the pre-extraction source exactly), rather than reordering the `add()` calls to force B0/B1/B2/B3 directly out of the function. This is the same order the code already produced before this plan touched it; only `canonical_order()` — and, after Task 3, the `sort_by_registry`-piped call site in `app.py` — is required to read B0/B1/B2/B3, and both do. Reordering the `add()` calls themselves would be a rewrite, not a relocation, and out of this phase's declared scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_nan_safe` normalisation needed for Settlement's and Boundary's parity-test detail-row comparisons, not anticipated by the plan's own text**
- **Found during:** Task 3, first run of `test_settlement_layer_matches_baseline` and `test_boundary_layer_matches_baseline`
- **Issue:** A direct `==` comparison between the actual and expected detail records failed even though every visible field printed identically, because `pd.concat`'s column union across per-rule sub-frames with different `extra` columns (e.g. an SQ1 detail row, whose own `extra` is `["ward_code", "settlement_name"]`, ending up with a `latitude`/`longitude` column contributed by a sibling rule's sub-frame) fills the unpopulated cells with `NaN` — and `float('nan') != float('nan')` under normal equality, on both the freshly-built actual side and the baseline JSON's round-tripped `NaN` token. Plan 04's `Next Phase Readiness` note anticipated this only for "a layer whose fixture does produce null detail cells"; Settlement's and Boundary's fixtures don't carry a deliberately-null cell, but their detail frames hit the same NaN-producing mechanism through column union rather than through a genuinely null input cell.
- **Fix:** Applied the existing `_nan_safe()` helper (introduced in plan 04) to both sides of all three new detail comparisons (settlement, takeoff, boundary) rather than deriving a new normalisation, and updated the module docstring to describe the broader trigger condition for future plans.
- **Files modified:** `tests/test_extraction_parity.py`
- **Verification:** All three new baseline-parity tests pass; the mutate-and-revert check (below) confirms `_nan_safe` did not mask a real divergence.
- **Committed in:** `3cd8a91`

**2. [Rule 1 - Bug, planning-artifact] Task 2's `<verify>` command's literal expectation of `['B0', 'B1', 'B2', 'B3']` for the raw (pre-sort) checks list contradicts the plan's own "move it whole, change nothing but its location" directive**
- **Found during:** Task 2, running the acceptance-criteria verification loop
- **Issue:** Task 2's `<verify>` block prints `[x['Rule#'] for x in c]` from calling `qc.boundary.run_ward_boundary_qc` directly (no `sort_by_registry`) and states `fails_when` that list is not exactly `['B0', 'B1', 'B2', 'B3']`. The pre-extraction `app.py` already emitted B3's check before B2's (the B3 code block appears before the B2 block in the source, unchanged since before this phase), so a verbatim relocation reproduces `['B0', 'B1', 'B3', 'B2']`, not the ordered list the verify text names. Reordering the `add()` calls to force the literal order would violate the task's own action text ("move it whole and change nothing but its location") and the phase's no-changed-verdicts scope, for no functional gain — the actually-required guarantee (`canonical_order()` ends `B0, B1, B2, B3`, and the `sort_by_registry`-piped call site delivers that order to the application) already holds, and is exactly what Task 2's own `<acceptance_criteria>` (as opposed to its `<verify>` prose) requires.
- **Fix:** Treated the acceptance_criteria (not the verify block's over-specific prose) as authoritative, per this project's precedent from plan 03/04 for planning-artifact inconsistencies. Left the raw emission order unchanged and verbatim.
- **Files modified:** None — no code change; a verification-only finding.
- **Verification:** `qc.canonical_order()[-4:]` reports `['B0', 'B1', 'B2', 'B3']`; every one of Task 2's `<acceptance_criteria>` bullets passes as written; the full suite is green.
- **Committed in:** N/A (no code change; documented here per Rule 1's "shared process" for tracking, even though nothing was fixed in code)

**3. [Rule 1 - Bug, planning-artifact] Task 2's `qc/boundary.py` docstring initially named the path constants and loader function it explicitly must not reference**
- **Found during:** Task 2, checking the acceptance criterion "`qc/boundary.py` contains no reference to `BOUNDARY_REF_PATH`, `BOUNDARY_BBOX_PATH` or `load_boundary_refs`"
- **Issue:** The first draft of `qc/boundary.py`'s module docstring explained (accurately) that those three names stay in `app.py`, but doing so by name meant the literal strings appeared in the file — satisfying the acceptance criterion's intent (no code reference) but not its letter (no reference at all), which a naive `grep` would flag.
- **Fix:** Reworded the docstring to describe the constants and loader by role ("the path constants and the Streamlit-cached loader that reads them") rather than by name.
- **Files modified:** `qc/boundary.py`
- **Verification:** `grep -n 'BOUNDARY_REF_PATH\|BOUNDARY_BBOX_PATH\|load_boundary_refs' qc/boundary.py` reports no matches.
- **Committed in:** `8c1ce17`

---

**Total deviations:** 3 (2 Rule 1 test/doc-correctness fixes, 1 Rule 1 planning-artifact finding requiring no code change)
**Impact on plan:** No scope creep. All three are corrections to how this plan's own tests, docstrings and verify-command prose hold together internally; none touch a check's actual behavior, and all three relocated layers are proven identical to the pre-extraction baseline on every field including the previously-unique identifiers.

## Issues Encountered

None beyond the three deviations documented above, all resolved within this plan's own scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`qc/settlement.py`, `qc/takeoff.py` and `qc/boundary.py` join `qc/schema.py` and `qc/mlos.py` as the third, fourth and fifth relocated layers — all five QC layers now live under `qc/`, and `app.py` calls every one of them through the package, piped through `qc.sort_by_registry`. `qc.canonical_order()` returns 40 distinct entries, ending `B0, B1, B2, B3` — the order Phase 3's VERDICT-06 will depend on. `app.py` still defines `auto_correct_mlos` and `load_boundary_refs`; plan 06 relocates `auto_correct_mlos` (the last remaining QC-adjacent function) through the same route this plan and plans 03-04 proved: a new `qc/<layer>.py` module, import-time `register()` calls (if any — `auto_correct_mlos` registers no rule identifiers, it is a transform not a check), and a call-site rewire in `app.py`. `tests/test_extraction_parity.py`'s `normalize_checks`/`normalize_detail`/`_nan_safe` helpers are all proven against three different layers now and are ready for plan 06's `auto_correct_mlos` parity test if one is needed. `ENGINE-01`/`ENGINE-05` are not yet marked complete in `REQUIREMENTS.md` — both are also declared by plan 06 (the shared-ID gate, #2388) and will flip once that plan's SUMMARY exists. `.planning/WINDOWS.md` entry #1 (the `VALID_ACC` grep count) remains resolved since plan 04; no new entries were added by this plan.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All three created files verified on disk (`qc/settlement.py`, `qc/takeoff.py`, `qc/boundary.py`, plus this SUMMARY). All three task commits (`8b52c95`, `8c1ce17`, `3cd8a91`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean: `python3 -m pytest tests/ -q` → 28 passed; `qc.canonical_order()` → 40 entries, all distinct, ending `B0, B1, B2, B3`; AST inspection of `app.py`'s top-level function names confirmed none of `run_settlement_qc`, `run_takeoff_qc`, `run_ward_boundary_qc` remain. The Task 3 acceptance criterion's mutate-and-revert check (SQ4 distance threshold) was re-verified during task execution and left the working tree clean on revert (`diff qc/settlement.py <(git show HEAD:qc/settlement.py)` reports no difference).
