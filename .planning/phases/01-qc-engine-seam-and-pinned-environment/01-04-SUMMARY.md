---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 04
subsystem: infra
tags: [python, package-extraction, rule-registry, rule-identifiers, pytest]

# Dependency graph
requires:
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 03)
    provides: "qc/results.py registry, qc/domain.py (YN_NA_COLS as an ordered tuple), qc/predicates.py, qc/schema.py, qc/__init__.py facade with sort_by_registry, and the normalize_checks/normalize_detail parity helpers this plan reuses directly"
provides:
  - "qc/mlos.py — run_mlos_qc relocated from app.py, 25 import-time register() calls, and the F3 fix: the three checks that shared identifier 11 now carry 11.urban/11.rural/11.scattered, and the eight that shared 12 now carry 12.<field> for each of highrisk, slums, densely_populated, hard2reach, border, nomadic, riverine, fulani"
  - "app.py's MLoS call site now calls qc.mlos.run_mlos_qc(...) piped through qc.sort_by_registry(...), matching the Schema call site's shape"
  - "tests/test_rule_identifiers.py — five standing tests pinning the frozen-27 (29, see Deviations), the 11 new identifiers, no bare 11/12, global distinctness, and the Excel sheet-name budget"
  - "tests/test_extraction_parity.py's test_mlos_layer_matches_baseline — proves the extracted MLoS layer matches the frozen baseline on every field except the eleven intended identifier renames"
affects: [01-qc-engine-seam-and-pinned-environment (plans 05-06 of this phase, which relocate the remaining three QC layers through the same seam), "Phase 2 (INTEG-03 partial-file degradation, F4/F5 auto_correct_mlos defects) inherits qc/mlos.py's column-presence guards unchanged"]

# Actuals (#2632)
actuals:
  tokens: 8935
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unrolled per-column add() calls for a fixed, short, non-domain-constant column list (R11's urban/rural/scattered): each column's identifier is a literal string appearing in both the register() call and the add() call, rather than an f-string built inside a loop, so a plain grep for a given identifier finds both the registration and the emission site. R12's eight columns stay a genuine loop over YN_NA_COLS — that iteration is a key_link this plan's frontmatter requires literally, and 8 unrolled blocks would be worse to maintain than the domain-constant loop it replaces."
    - "NaN-safe detail-row comparison in a parity test (_nan_safe): a detail DataFrame carrying a genuine null cell serializes through JSON as the literal (non-standard but Python-accepted) NaN token, which parses back into float('nan') — and float('nan') != float('nan') under Python's normal equality, so a dict-equality assertion over such rows always fails without an explicit sentinel substitution on both sides."

key-files:
  created:
    - qc/mlos.py
    - tests/test_rule_identifiers.py
  modified:
    - qc/__init__.py
    - app.py
    - tests/test_extraction_parity.py

key-decisions:
  - "Unrolled the R11 loop (urban/rural/scattered) into three explicit add() calls instead of keeping a for-loop with an f-string identifier, to satisfy the plan's own acceptance criterion (grep -c '11\\.urban' reports at least 2 — the registration and the emission path). An f-string-built identifier inside a loop never puts the literal substring '11.urban' in the source twice; explicit per-column calls do, with identical runtime behavior and order."
  - "Kept R12's loop over YN_NA_COLS exactly as the plan's action and key_links require — that loop is the mechanism proving the ordered-tuple fix (plan 03) actually drives emission order, and unrolling it would remove the one place that dependency is exercised."
  - "FROZEN_IDENTIFIERS in tests/test_rule_identifiers.py holds 29 entries, not the 27 that CONTEXT.md's D-04 and this plan's own must_haves state. Enumerated directly against every add()/register() call site in the pre-extraction app.py rather than trusting the stated count: Settlement contributes 5 (SQ1, SQ2, SQ2b, SQ3, SQ4), not 4, and Boundary contributes 4 (B0-B3). Completeness of the freeze guarantee — protecting every identifier a filed report could cite — matters more than matching a miscounted total; dropping two real, still-frozen identifiers to hit '27' would have silently removed them from this test's protection."

patterns-established:
  - "Explicit rename-mapping assertion in a parity test: RENAMED_IDENTIFIERS in tests/test_extraction_parity.py maps each renamed check's stable name to its new identifier and is asserted against directly, not merely checked for inequality with the old value — plans 05/06 have no renamed identifiers of their own, but this shape is the template if a future phase ever needs one."

requirements-completed: []  # ENGINE-01/ENGINE-05/ENGINE-09 also declared by plans 05/06 (shared-ID gate, #2388) — not marked complete until every declaring plan finishes.

coverage:
  - id: D1
    description: "qc/mlos.py exists with run_mlos_qc relocated verbatim (behavior unchanged) plus 25 module-level register() calls; the three R11 checks and eight R12 checks that used to share bare identifiers 11/12 now each carry a distinct field-named identifier (11.urban, 11.rural, 11.scattered, 12.highrisk, 12.slums, 12.densely_populated, 12.hard2reach, 12.border, 12.nomadic, 12.riverine, 12.fulani), and the eight R12 checks emit in the same fixed order on every process because YN_NA_COLS is an ordered tuple"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"...qc.mlos.run_mlos_qc(fixture)...\" -> 25 checks, 25 distinct identifiers"
        status: pass
      - kind: other
        ref: "qc.canonical_order() contains 11.urban, 11.rural, 11.scattered, 11a, 11b, 12.highrisk...12.fulani in that order, and no bare '11' or '12'"
        status: pass
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_mlos_layer_matches_baseline"
        status: pass
      - kind: other
        ref: "ran the R12-order check twice in separate interpreter processes -> identical eight-identifier order both times"
        status: pass
    human_judgment: false
  - id: D2
    description: "app.py no longer defines run_mlos_qc; the MLoS call site calls qc.mlos.run_mlos_qc(...) and pipes the result through qc.sort_by_registry(...), matching the Schema call site's shape, and qc/__init__.py imports mlos after schema"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"import ast...\" -> app.py's top-level function names contain no run_mlos_qc"
        status: pass
      - kind: other
        ref: "qc/__init__.py source inspection: 'from . import mlos' follows 'from . import schema'"
        status: pass
      - kind: other
        ref: "python3 -c \"import qc\" -> no exception"
        status: pass
    human_judgment: false
  - id: D3
    description: "The identifier contract is pinned on every suite run: FROZEN_IDENTIFIERS' entries belonging to a relocated layer are all still registered, the 11 new identifiers are all registered, no bare 11/12 remains, every registered identifier is globally distinct, and every derived Excel sheet name (Rule + identifier, truncated at 31 chars) fits and stays distinct"
    requirement: "ENGINE-01"
    verification:
      - kind: unit
        ref: "tests/test_rule_identifiers.py#test_frozen_identifiers_are_all_still_registered"
        status: pass
      - kind: unit
        ref: "tests/test_rule_identifiers.py#test_the_eleven_new_identifiers_are_registered"
        status: pass
      - kind: unit
        ref: "tests/test_rule_identifiers.py#test_no_bare_11_or_12_identifier_remains"
        status: pass
      - kind: unit
        ref: "tests/test_rule_identifiers.py#test_every_registered_identifier_is_distinct"
        status: pass
      - kind: unit
        ref: "tests/test_rule_identifiers.py#test_excel_sheet_names_fit_and_stay_distinct"
        status: pass
      - kind: other
        ref: "manual mutate-and-revert: renamed 11a to 11c in qc/mlos.py -> test_frozen_identifiers_are_all_still_registered failed naming '11a'; reverted -> 5 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "The extracted MLoS layer's output is field-identical to the frozen pre-extraction baseline for all 25 checks — every field for the 14 frozen-identifier checks, every field except the identifier for the 11 renamed checks, whose new identifier matches an explicit expected mapping — and detail rows match once the renamed checks' identifier is normalised back to the baseline's bare value"
    requirement: "ENGINE-01"
    verification:
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_mlos_layer_matches_baseline"
        status: pass
      - kind: other
        ref: "manual mutate-and-revert: inverted R8's isin() comparison in qc/mlos.py -> test failed naming check 'Habitational Status Valid' and field 'Failing Rows'; reverted -> 2 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "The MLoS layer imports with no UI-framework dependency, consistent with plan 03's ENGINE-05 guard, which already scans every module under qc/ including this plan's new qc/mlos.py"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py#test_no_module_under_qc_imports_the_ui_framework (re-run, now covering qc/mlos.py)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The eight R12 profile-flag checks emit in the same fixed order on every process, consuming plan 03's ordered-tuple fix for the first time on a real, previously-nondeterministic loop"
    requirement: "ENGINE-09"
    verification:
      - kind: other
        ref: "ran qc.mlos.run_mlos_qc twice in separate interpreter invocations -> identical ['12.highrisk','12.slums','12.densely_populated','12.hard2reach','12.border','12.nomadic','12.riverine','12.fulani'] both times"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 04: MLoS Relocation and the Eleven-Identifier Split Summary

**`run_mlos_qc` now lives in `qc/mlos.py` behind 25 import-time registrations; the three checks that used to all report "11" and the eight that used to all report "12" now carry field-named identifiers, and every other field of every check is proven unchanged against the frozen baseline.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-09T19:53:00Z
- **Completed:** 2026-09-09T20:08:00Z
- **Tasks:** 3 of 3 completed
- **Files modified:** 5 (2 modified beyond the new module, 2 new test additions)

## Accomplishments
- `qc/mlos.py` relocates `run_mlos_qc` verbatim (identical `add()` closure, identical column-presence guards, identical vectorised checks) apart from the two identifier fixes the phase exists to make: R11's three field checks and R12's eight profile-flag checks each now carry a distinct, field-named identifier instead of sharing a bare number.
- `app.py` calls `qc.mlos.run_mlos_qc(...)` piped through `qc.sort_by_registry(...)` at the real MLoS call site — the same shape plan 03 established for Schema — and no longer defines `run_mlos_qc` itself.
- `tests/test_rule_identifiers.py` pins the whole identifier contract on every suite run: the frozen set survives, the 11 new identifiers are present, no bare `11`/`12` remains, every identifier is globally distinct, and every derived Excel sheet name fits the 31-character limit without colliding.
- `tests/test_extraction_parity.py::test_mlos_layer_matches_baseline` proves, field by field and pairing by check name (not list position, since the baseline recorded R12's checks in an arbitrary set-iteration order), that nothing about the MLoS layer's behavior changed except the eleven intended identifiers.
- Resolves `.planning/WINDOWS.md` entry #1: `grep -c VALID_ACC app.py` now reports 1 (the import line only), since `run_mlos_qc`'s usage line moved out with the function.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate the MLoS layer and split the two overloaded identifiers** - `7c6c55d` (feat)
2. **Task 2: Pin the identifier contract** - `1c500d2` (test)
3. **Task 3: Prove the MLoS relocation changed no verdict** - `f0e1139` (test)

**Plan metadata:** committed alongside this summary

_Note: both Task 2 and Task 3 carried `tdd="true"`, but as with every prior plan in this phase, the "implementation" under test (the relocated `qc/mlos.py`) already existed and was already correct by the time each test file was written — there was no separate GREEN-phase production code to write against a failing test. Each task's detection power was verified via a manual mutate-and-revert cycle instead, per each task's own acceptance criteria (see below)._

## Files Created/Modified
- `qc/mlos.py` - new; `run_mlos_qc` relocated, 25 `register()` calls, R11 unrolled to three explicit per-column `add()` calls (identifier fix), R12 still a loop over `YN_NA_COLS` (identifier fix, order fix inherited from plan 03)
- `qc/__init__.py` - modified; imports the new `mlos` submodule immediately after `schema`
- `app.py` - modified; `run_mlos_qc` definition deleted (166 lines removed); MLoS call site now calls `qc.mlos.run_mlos_qc` + `qc.sort_by_registry`
- `tests/test_rule_identifiers.py` - new; `FROZEN_IDENTIFIERS` (29 entries — see Deviations) plus 5 tests defending the identifier contract
- `tests/test_extraction_parity.py` - modified; added `test_mlos_layer_matches_baseline`, `RENAMED_IDENTIFIERS`, `_OLD_ID_BY_NAME`, `_actual_mlos_detail_with_baseline_ids`, `_nan_safe`

## Decisions Made
- **Unrolled R11's loop into three explicit `add()` calls.** The plan's own acceptance criterion for Task 1 requires `grep -v '^ *#' qc/mlos.py | grep -c '11\.urban'` to report at least 2 (the registration and the emission path). An `f"11.{col}"` built inside a `for col in ("urban", "rural", "scattered")` loop — the form both `01-PATTERNS.md`'s verbatim example and the task's own `<action>` prose describe — never puts the literal substring `11.urban` in the source a second time, so the grep-based criterion and the loop-based action text are in tension. Chose to satisfy the acceptance criterion (a HARD GATE per the execution protocol) since the unrolled form is behaviorally identical — same three columns, same order, same masks — and does not touch R12's loop, which the plan's `key_links` explicitly require to iterate `YN_NA_COLS`.
- **`FROZEN_IDENTIFIERS` holds 29 entries, not 27.** See Deviations below.
- **NaN-safe comparison (`_nan_safe`) added to the parity test**, not present in plan 03's schema parity test, because MLoS's fixture and baseline both carry a genuine null cell (row 1's deliberate `None` timestamp) that Schema's detail rows never do — `float('nan') != float('nan')` broke a direct dict-equality assertion until this normalisation was added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `grep -c '11\.urban'` acceptance criterion unsatisfiable with the loop-based R11 implementation the plan's own action/pattern text describes**
- **Found during:** Task 1, running the acceptance-criteria verification loop
- **Issue:** The task's `<action>` prose and `01-PATTERNS.md`'s verbatim example both show R11 as `for col in ("urban", "rural", "scattered"): add(f"11.{col}", ...)`. Under that form, the literal string `11.urban` appears exactly once in `qc/mlos.py` (the `register()` call) — the emission path only ever holds the *template* `f"11.{col}"`, never the literal text, so `grep -c '11\.urban'` reports 1, not the "at least 2" the acceptance criterion requires.
- **Fix:** Unrolled the three-iteration loop into three explicit `if col in mlos.columns: add("11.urban", ...)` blocks (one per column), which is behaviorally identical (same columns, same order, same masks, same descriptions) and makes the literal identifier appear in both the registration and the emission call.
- **Files modified:** `qc/mlos.py`
- **Verification:** `grep -v '^ *#' qc/mlos.py | grep -c '11\.urban'` reports 2; `qc.mlos.run_mlos_qc` still emits 25 checks/25 distinct identifiers in the same order; full suite green (23 passed).
- **Committed in:** `7c6c55d`

**2. [Rule 1 - Bug] `_nan_safe` normalisation needed for the MLoS parity test's detail-row comparison, absent from plan 03's schema parity test**
- **Found during:** Task 3, first run of `test_mlos_layer_matches_baseline`
- **Issue:** A direct `==` comparison between the actual detail records and the baseline's detail records failed even though every visible field printed identically, because both sides' null cells are Python `float('nan')` (the actual DataFrame's real null, and the baseline JSON's `NaN` token round-tripped through `json.loads`) — and `float('nan') != float('nan')` under normal equality, so the dict comparison always failed on any row containing a null cell.
- **Fix:** Added `_nan_safe()`, replacing any float NaN cell with a fixed sentinel string on both the actual and expected sides immediately before the final assertion.
- **Files modified:** `tests/test_extraction_parity.py`
- **Verification:** `test_mlos_layer_matches_baseline` passes; the mutate-and-revert check (inverting R8's `isin()` comparison) still fails with a clear diverging-field message, confirming `_nan_safe` did not mask real divergences.
- **Committed in:** `f0e1139`

**3. [Rule 1 - Bug, planning-artifact] `FROZEN_IDENTIFIERS`'s correct count is 29, not the 27 CONTEXT.md's D-04 and this plan's own `must_haves` state**
- **Found during:** Task 2, while enumerating D-04's identifier list against the actual pre-extraction `app.py`
- **Issue:** D-04 (and this plan's must_haves truth "All 27 previously-unique identifiers keep their exact strings") both state 27. Enumerating the identifiers D-04 itself lists — `1`-`10` (10), `11a`/`11b` (2), `13`/`14` (2), `S1`/`S2` (2), `SQ1`/`SQ2`/`SQ2b`/`SQ3`/`SQ4` (5), `TP2`-`TP5` (4), `B0`-`B3` (4) — sums to 29, verified directly against every `add()`/`register()`-equivalent call site in the pre-extraction `app.py` (Settlement genuinely has 5 checks, not 4; Boundary genuinely has 4).
- **Fix:** `FROZEN_IDENTIFIERS` in `tests/test_rule_identifiers.py` lists all 29 real identifiers, with a module-docstring "Count note" explaining the discrepancy rather than silently matching "27" by dropping two real, still-frozen identifiers out of the freeze guarantee.
- **Files modified:** `tests/test_rule_identifiers.py`
- **Verification:** `len(FROZEN_IDENTIFIERS) == 29`, confirmed by direct interpreter check; `test_frozen_identifiers_are_all_still_registered` asserts at least 16 checked identifiers (Schema's 2 + MLoS's 14 frozen ones) and passes.
- **Committed in:** `1c500d2`

---

**Total deviations:** 3 auto-fixed (3 Rule 1 — one implementation-shape bug forced by a plan self-inconsistency, one test-correctness bug, one planning-artifact miscount corrected rather than propagated)
**Impact on plan:** No scope creep. All three fixes are corrections to how this plan's own tests and acceptance criteria hold together internally; none touch a check's actual behavior, and the MLoS layer's output is proven byte-identical to the pre-extraction baseline except the eleven intended identifier changes.

## Issues Encountered

None beyond the three deviations documented above, all resolved within this plan's own scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`qc/mlos.py` joins `qc/schema.py` as the second relocated layer, registering 25 of the phase's eventual full identifier set and proving the F3/F10 fixes on the largest, highest-risk function this phase touches. `qc.canonical_order()` now returns 27 entries (2 Schema + 25 MLoS), all distinct, with no bare `11`/`12` remaining. Plans 05 and 06 can relocate `run_settlement_qc`/`run_takeoff_qc`/`run_ward_boundary_qc`/`auto_correct_mlos` through the exact same route this plan and plan 03 both proved: a new `qc/<layer>.py` module, import-time `register()` calls reproducing the frozen identifiers, and a call-site rewire in `app.py` piping through `qc.sort_by_registry`. `tests/test_extraction_parity.py`'s `normalize_checks`/`normalize_detail` helpers remain available for layers whose detail rows carry no NaN cells (Settlement, Takeoffpoint, Boundary); a layer whose fixture does produce null detail cells should reuse the `_nan_safe` pattern this plan introduced rather than re-deriving it. `ENGINE-01`/`ENGINE-05`/`ENGINE-09` are not yet marked complete in `REQUIREMENTS.md` — they are also declared by plans 05 and/or 06 (the shared-ID gate, #2388), and will flip once the last plan declaring them finishes. `.planning/WINDOWS.md` is back to zero open entries.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All created files verified on disk (`qc/mlos.py`, `tests/test_rule_identifiers.py`, plus this SUMMARY). All three task commits (`7c6c55d`, `1c500d2`, `f0e1139`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean: `python3 -m pytest tests/ -q` → 23 passed; `qc.canonical_order()` → 27 entries, all distinct, no bare `11` or `12`. Both parity/identifier acceptance criteria's mutate-and-revert checks (renaming `11a`→`11c`; inverting R8's `isin()` comparison) were re-verified during task execution and left the working tree clean on revert.
