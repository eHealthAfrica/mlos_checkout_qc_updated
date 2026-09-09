---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 06
subsystem: infra
tags: [python, package-extraction, rule-registry, determinism, pytest, subprocess-testing]

# Dependency graph
requires:
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 03)
    provides: "qc/results.py registry, qc/domain.py's YN_NA_COLS ordered tuple, qc/__init__.py facade with sort_by_registry"
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 04)
    provides: "qc/mlos.py registering the 25 MLoS identifiers (including the 11 field-named splits) this plan's sidebar reference and identifier-coverage tests assert against"
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 05)
    provides: "qc/settlement.py, qc/takeoff.py, qc/boundary.py — the last three layers this plan's cross-process determinism and coverage tests run against, and app.py's five sort_by_registry-piped call sites this plan's autocorrect call-site rewire matches in shape"
provides:
  - "qc/autocorrect.py — auto_correct_mlos relocated verbatim from app.py, its two known defects (F4 cache divergence, F5 non-deterministic GUID regeneration) untouched per D-09; registers no rule identifiers"
  - "qc/__init__.py imports all six submodules (schema, mlos, settlement, takeoff, boundary, autocorrect) and explicitly records that the facade does not gain a run_all() wrapper, per CONTEXT.md's Claude's Discretion note"
  - "app.py contains none of the six relocated QC/autocorrection functions and none of the three relocated predicates; both auto_correct_mlos call sites now call qc.autocorrect.auto_correct_mlos; the now-dead FLAG_COLS/pct/vec_is_uuid/vec_is_editor re-imports are removed"
  - "The MLoS sidebar reference table lists all 25 registered MLoS identifiers (11.urban/11.rural/11.scattered/11a/11b instead of one bare '11' row, 12.highrisk through 12.fulani instead of one bare '12' row), closing T-01-20"
  - "tests/test_rules_reference_matches_registry.py — parses the five Rule/Check-headed sidebar tables out of app.py and asserts their identifier union equals qc.canonical_order() exactly, in both directions"
  - "tests/test_deterministic_order.py — subprocess-based proof (three explicit, differing PYTHONHASHSEED values, byte-level stdout comparison) that both the raw pre-sort emission order and the registry-sorted order are stable across process restarts, closing ENGINE-09/F10"
  - "tests/test_registry_covers_emitted_ids.py — the registry-emits identity invariant: every identifier any layer emits is registered, and every registered identifier is emitted by the full fixture"
  - "Fixed a pre-existing test-isolation leak in tests/test_results_registry.py that this plan's new exact-set-equality test exposed: two duplicate-id tests registered throwaway identifiers into the real, process-global qc.results registry and never removed them"
affects: ["Phase 2 (ENGINE-03/ENGINE-04) inherits qc/autocorrect.py's two known defects unchanged, exactly as D-09 records", "Phase 3 (VERDICT-06) inherits the registry's B0-B3 ordering and the now-complete sidebar reference as the mechanism boundary checks and their documentation will read consistently from", "Any future phase adding a rule inherits tests/test_registry_covers_emitted_ids.py and tests/test_rules_reference_matches_registry.py as standing gates against re-opening either identity drift"]

# Actuals (#2632)
actuals:
  tokens: 7721
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess-based cross-process determinism test: PYTHONHASHSEED cannot be varied within one interpreter, so proving order-stability requires forking real subprocesses with an explicit, differing seed per run and comparing raw stdout bytes (never decoded text, since check descriptions carry non-ASCII characters) — a same-process test with two function calls would pass whether or not the underlying defect was fixed, per 01-RESEARCH.md Pitfall 2."
    - "Markdown-table-as-data parser scoped by header shape, not by a blanket pipe-delimited-line match: tests/test_rules_reference_matches_registry.py's parser matches only the exact two-column 'Rule'/'Check' header, which is what excludes the differently-shaped Auto Correct table (three columns, correction numbers not rule identifiers) from being pulled in as if it were a sixth rule table."

key-files:
  created:
    - qc/autocorrect.py
    - tests/test_rules_reference_matches_registry.py
    - tests/test_deterministic_order.py
    - tests/test_registry_covers_emitted_ids.py
  modified:
    - qc/__init__.py
    - app.py
    - tests/test_results_registry.py

key-decisions:
  - "Followed the plan's explicit, narrow cleanup scope for app.py's dead imports: removed FLAG_COLS, pct, vec_is_uuid and vec_is_editor (all four confirmed unused once auto_correct_mlos moved out — pct and vec_is_editor were, in fact, already fully unused leftovers from plans 03-05's earlier relocations). Left VALID_ACC/VALID_HAB/VALID_YN/VALID_YN_NA/YN_NA_COLS untouched even though a grep shows they are also currently unused in app.py — the plan's action text names only the four, and expanding the cleanup beyond what was asked would be unrequested scope creep into a different plan's declared boundary."
  - "Committed Task 2 (tdd=\"true\") as a genuine RED-then-GREEN pair rather than the single-commit shape prior plans in this phase used for their parity tests. Unlike plans 03-05's parity tests (which tested already-correct relocated code), this task's test requires a real production-code change — the MLoS sidebar table — to turn green. Verified RED by isolating the app.py table hunk via a patch file, committing only the test, confirming failure (naming both the '11'/'12' omissions and all eleven field-named additions), then reapplying the table hunk as a separate GREEN commit."
  - "Fixed the tests/test_results_registry.py registry-leak as part of Task 2 rather than deferring it: the new exact-set-equality test is only meaningful if canonical_order() reflects real, permanent registrations, and two throwaway test identifiers left in the shared process-global registry by an earlier plan's test would otherwise make the new test fail depending on pytest's collection order — a flake, not a real defect. Rule 1 (bug) auto-fix: added a `_unregister` helper the two offending tests now call in a `finally` block."

patterns-established:
  - "Registry cleanup for throwaway test identifiers (`_unregister` in tests/test_results_registry.py): any future test that calls `register()` with a disposable identifier to exercise the duplicate-id guard must remove it afterward (in a finally block) — the registry is real, process-global, shared state for the whole pytest session, not per-test scratch space."

requirements-completed: [ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-09]

coverage:
  - id: D1
    description: "qc/autocorrect.py exists with auto_correct_mlos relocated verbatim (all five corrections, the local uuid import, the defensive copy) and registers no rule identifiers; qc/__init__.py imports the autocorrect submodule and gains no run_all() wrapper; app.py defines none of the six relocated QC/autocorrection functions or the three relocated predicates, both auto_correct_mlos call sites now go through qc.autocorrect, and the four now-dead re-imports (FLAG_COLS, pct, vec_is_uuid, vec_is_editor) are removed"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"...qc.autocorrect.auto_correct_mlos(fixture)...\" -> 10 rows, ['Braces removed (0 rows); UUID regenerated (1 rows)']"
        status: pass
      - kind: other
        ref: "python3 -c \"import ast...\" -> app.py's top-level function names contain none of the nine relocated function/predicate names"
        status: pass
      - kind: other
        ref: "grep -c 'from qc' app.py -> 1"
        status: pass
      - kind: other
        ref: "cat qc/*.py | grep -v comment | grep -c 'dtype ==' -> 0; chained-assignment scan -> 0 (re-run pandas-3.0 risk-pattern scans across the finished package)"
        status: pass
      - kind: integration
        ref: "python3 -m pytest tests/ -q -> 28 passed (immediately after Task 1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The MLoS sidebar reference table documents all 25 registered MLoS identifiers (three 11.* rows, two 11a/11b rows, eight 12.* rows, replacing the two bare '11'/'12' rows); the union of all five reference tables' identifiers equals qc.canonical_order() exactly (40), asserted in both directions by a standing test that also proves its own parser found exactly five tables"
    requirement: "ENGINE-01"
    verification:
      - kind: unit
        ref: "tests/test_rules_reference_matches_registry.py#test_reference_table_parser_found_all_five_tables"
        status: pass
      - kind: unit
        ref: "tests/test_rules_reference_matches_registry.py#test_reference_tables_and_registry_list_the_same_identifiers"
        status: pass
      - kind: other
        ref: "manual mutate-and-revert: deleted the '14' row from the MLoS table -> test failed naming 'emitted by the engine but not documented in the reference: [\"14\"]'; reverted -> 2 passed"
        status: pass
    human_judgment: true
    rationale: "The test proves parse-level set equality; whether the five expanders actually render as legible markdown tables inside a Streamlit sidebar (rather than literal pipe characters) is the task's own <human-check> and cannot be verified by source parsing."
  - id: D3
    description: "Two runs over identical data in three separate processes, started with three different explicit string-hash seeds, emit checks in byte-identical order — both the raw pre-sort emission order (proving the ordered-tuple half of the fix) and the registry-sorted order (proving the registry half independently, and equal to canonical_order())"
    requirement: "ENGINE-09"
    verification:
      - kind: unit
        ref: "tests/test_deterministic_order.py#test_raw_emission_order_is_stable_across_hash_seeds"
        status: pass
      - kind: unit
        ref: "tests/test_deterministic_order.py#test_registry_sorted_order_is_stable_across_hash_seeds"
        status: pass
      - kind: other
        ref: "manual mutate-and-revert: reverted qc/domain.py's YN_NA_COLS to a set literal -> test_raw_emission_order_is_stable_across_hash_seeds failed (byte mismatch across the 3 seeds, diverging on the eight 12.* identifiers' relative order), while test_registry_sorted_order_is_stable_across_hash_seeds still passed (registry backstop holds independently); reverted -> 34 passed, diff against qc/domain.py at HEAD empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every identifier any of the five QC layers emits against the full fixture resolves to exactly one registered rule, and every registered rule is emitted by the fixture — the registry and the engine describe the same 40-identifier rule set, asserted in both directions with the offending identifiers named on failure"
    requirement: "ENGINE-02"
    verification:
      - kind: unit
        ref: "tests/test_registry_covers_emitted_ids.py#test_every_emitted_identifier_is_registered"
        status: pass
      - kind: unit
        ref: "tests/test_registry_covers_emitted_ids.py#test_every_registered_identifier_is_emitted_by_the_fixture"
        status: pass
      - kind: other
        ref: "python3 -c \"import qc; o=qc.canonical_order(); print(len(o), len(set(o))==len(o), o[:2], o[-4:])\" -> 40 True ['S1','S2'] ['B0','B1','B2','B3']"
        status: pass
    human_judgment: false
  - id: D5
    description: "Fixed a pre-existing test-isolation leak in tests/test_results_registry.py (two duplicate-id tests left throwaway identifiers permanently registered in the shared process-global registry) that this plan's new exact-set-equality test exposed; every module under qc/ (including the new qc/autocorrect.py) still imports with no UI-framework dependency"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py (re-run, now covering 6 modules under qc/)"
        status: pass
      - kind: other
        ref: "python3 -m pytest tests/test_results_registry.py tests/test_rules_reference_matches_registry.py -q, run twice consecutively in the same invocation to force worst-case pollution ordering -> 5 passed both times, post-fix"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min (wall clock; includes an executor stall mid-Task-3 — see Issues Encountered)
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 06: Auto-Correction Relocation and Rule-Identity Closure Summary

**`auto_correct_mlos` now lives in `qc/autocorrect.py`; the MLoS sidebar reference documents all 25 registered identifiers instead of two bare numbers; and three new standing tests prove — by subprocess, not by convention — that emission order survives a process restart and that the registry and the engine describe exactly the same 40-rule set.**

## Performance

- **Duration:** ~40 min (wall clock, including one interruption)
- **Started:** 2026-09-09T21:24:59+01:00 (approx., following plan 05's final commit)
- **Completed:** 2026-09-09T22:13:26+01:00
- **Tasks:** 3 of 3 completed
- **Files modified:** 7 (4 new, 3 modified)

## Accomplishments
- `qc/autocorrect.py` relocates `auto_correct_mlos` verbatim — all five corrections, the local `uuid` import, the defensive input copy — with its two known defects (F4 cache divergence, F5 non-deterministic GUID regeneration) deliberately untouched per D-09; the function registers no rule identifiers, since it is a data transform, not a check.
- `app.py` now defines none of the six relocated QC/autocorrection functions and none of the three relocated predicates. Both `auto_correct_mlos` call sites (the pre-step QC orchestration and the Auto Correct tab's download builder) now call `qc.autocorrect.auto_correct_mlos`, and the four now-dead re-imports (`FLAG_COLS`, `pct`, `vec_is_uuid`, `vec_is_editor`) are removed. `qc/__init__.py` imports all six submodules and explicitly records — in its own docstring — that the facade does not gain a `run_all()` wrapper, closing the "Claude's Discretion" question CONTEXT.md left open.
- The MLoS sidebar reference table went from two rows that lied by omission (`11` covering three checks, `12` covering eight, and the two `11a`/`11b` conflict rules never documented at all) to 25 rows, one per registered MLoS identifier — closing T-01-20. `tests/test_rules_reference_matches_registry.py` proves the union of all five reference tables' identifiers equals `qc.canonical_order()` exactly, 40 both ways.
- `tests/test_deterministic_order.py` forks three real subprocesses per test, each with an explicit, differing `PYTHONHASHSEED`, and compares captured stdout as raw bytes. Both the pre-sort raw emission order and the post-`sort_by_registry` order are proven byte-identical across all three seeds — closing ENGINE-09/F10 with a test that (mutate-and-revert confirmed) would have failed against the pre-plan-03 set-literal `YN_NA_COLS`, while the registry-sorted test independently confirms the registry alone is a sufficient backstop even without the tuple fix.
- `tests/test_registry_covers_emitted_ids.py` closes the identity loop both directions: every identifier the full fixture's five layers emit is registered, and every registered identifier is emitted by the fixture — 40 identifiers, no drift either way.
- Fixed a genuine pre-existing test-isolation bug in `tests/test_results_registry.py`, exposed by the new exact-set-equality assertion: two tests registered throwaway identifiers into the real, shared, process-global registry and never cleaned up, which would otherwise make `test_reference_tables_and_registry_list_the_same_identifiers` fail (or pass) depending on pytest's collection order rather than on anything real.
- Full suite: 34 passed (28 from prior plans + 2 from Task 2 + 4 from Task 3).

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate auto-correction and settle the package surface** - `d357d43` (feat)
2. **Task 2: Make the in-app rules reference agree with the registry** - `d4587a3` (test, RED) + `2009dbe` (feat, GREEN)
3. **Task 3: Prove emission order is stable across processes and the registry matches the engine** - `4797cff` (test)

**Plan metadata:** committed alongside this summary

_Note: Task 2 carried `tdd="true"` and, unlike every prior parity-test task in this phase, involved a genuine RED-then-GREEN cycle: the test was verified failing against the still-bare `11`/`12` MLoS table (naming both differences) before the table's expansion was applied as a separate commit. Task 3 also carried `tdd="true"`, but as with plans 03-05's parity tests, the "implementation" under test (all five already-relocated QC layers) already existed and was already correct — detection power was verified via the mutate-and-revert cycles described below instead._

## Files Created/Modified
- `qc/autocorrect.py` - new; `auto_correct_mlos` relocated verbatim, no `register()` calls
- `qc/__init__.py` - modified; imports the new `autocorrect` submodule, docstring records no `run_all()` wrapper
- `app.py` - modified; `auto_correct_mlos` definition removed (86 lines), both call sites rewired to `qc.autocorrect.auto_correct_mlos`, four dead re-imports removed, MLoS sidebar reference table expanded from 2 to 13 net new rows (25 total)
- `tests/test_rules_reference_matches_registry.py` - new; header-shape-scoped markdown table parser plus two tests (parser sanity, exact set equality)
- `tests/test_deterministic_order.py` - new; three-seed subprocess harness plus two tests (raw order, registry-sorted order)
- `tests/test_registry_covers_emitted_ids.py` - new; two set-comparison tests against the full fixture
- `tests/test_results_registry.py` - modified; added `_unregister` cleanup helper, called from both duplicate-id tests' `finally` blocks

## Decisions Made
- **Followed the plan's narrow, explicit dead-import cleanup scope** (`FLAG_COLS`, `pct`, `vec_is_uuid`, `vec_is_editor` only), leaving other already-unused `qc.domain` imports (`VALID_ACC`, `VALID_HAB`, `VALID_YN`, `VALID_YN_NA`, `YN_NA_COLS`) in `app.py` untouched — not this plan's declared scope to remove.
- **Split Task 2 into a real RED/GREEN commit pair**, since (unlike this phase's earlier parity tests) it required an actual production-code change to pass. See Deviations for how RED was verified.
- **Fixed the `tests/test_results_registry.py` registry leak in-scope** rather than deferring it, since the new exact-set-equality test's correctness depends on it. See Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/test_results_registry.py`'s duplicate-id tests leaked throwaway identifiers into the shared, process-global registry**
- **Found during:** Task 2, first run of the new `tests/test_rules_reference_matches_registry.py::test_reference_tables_and_registry_list_the_same_identifiers` alongside the rest of the suite
- **Issue:** `test_duplicate_rule_id_raises_at_registration` and `test_duplicate_is_rejected_across_different_layers` (added in plan 03) call `register()` with throwaway identifiers (`__test_dup_same_layer__`, `__test_dup_cross_layer__`) and never remove them from `qc.results`'s module-level `_REGISTRY`/`_ORDER`. Since pytest runs the whole session in one process, any test running afterward that calls `qc.canonical_order()` sees those two phantom identifiers permanently present — which made the new exact-set-equality test fail, naming them as "emitted by the engine but not documented in the reference" (they are neither emitted by any real layer nor documented anywhere, since they are test scaffolding, not real rules).
- **Fix:** Added a `_unregister(rule_id)` helper to `tests/test_results_registry.py` that pops the throwaway id from both `_REGISTRY` and `_ORDER`, called in a `finally` block from both affected tests so cleanup runs even if an assertion fails.
- **Files modified:** `tests/test_results_registry.py`
- **Verification:** Full suite green (34 passed); re-ran `test_results_registry.py` followed immediately by `test_rules_reference_matches_registry.py` in the same invocation (worst-case pollution ordering) twice consecutively — 5 passed both times.
- **Committed in:** `d4587a3` (RED commit for Task 2, alongside the new test file, since both address the same test-isolation concern)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test-isolation bug, not a check-behavior change)
**Impact on plan:** No scope creep, no changed verdicts. The fix is confined to test scaffolding cleanup and does not touch any QC rule's logic, any relocated function, or any registered identifier.

## Issues Encountered

**Executor stall mid-Task-3.** After writing `tests/test_deterministic_order.py` and `tests/test_registry_covers_emitted_ids.py` to disk, this execution stalled before running them (a tool-availability interruption, not a test or code failure) and was resumed by the orchestrator. Before resuming, the orchestrator independently verified: (a) the two files were present and uncommitted, (b) `python3 -m pytest tests/ -q` passed 34/34 including both new files, and (c) `test_deterministic_order.py` is not vacuous — it forks real subprocesses with explicit differing `PYTHONHASHSEED` values and compares raw stdout bytes, per Research Pitfall 2. On resume, this execution re-verified all of the above independently (re-ran the full suite, re-ran the plan's specific `<verify>` commands, and additionally performed both tasks' mutate-and-revert acceptance checks, neither of which the orchestrator's interim verification had covered) before committing. No code was redone; only the commit and close-out steps that were pending at the stall were completed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

This is the last plan in Phase 1. All five `run_*_qc()` functions and `auto_correct_mlos` now live under `qc/`, `app.py` is orchestration and presentation only (load → call into `qc/` → score → render → export), `qc.canonical_order()` returns 40 distinct identifiers ending `B0, B1, B2, B3`, the sidebar reference and the registry list the same 40 identifiers, and three subprocess-based standing tests prove emission order survives a process restart at both the raw and registry-sorted levels. Full suite: 34 passed. `ENGINE-01`, `ENGINE-02`, `ENGINE-05` and `ENGINE-09` are all declared exclusively by this plan (the shared-ID gate's other declaring plans, 04 and 05, only declared `ENGINE-01`/`ENGINE-05`/`ENGINE-09` and have already finished) — this plan's completion is what makes all four ready to mark complete in `REQUIREMENTS.md`. `ENGINE-07` (pandas/numpy pinning) was already marked complete in plan 01/02. Phase 2 (Detection Correctness and Three-Format Harness) can begin: it will edit `qc/autocorrect.py` next (ENGINE-03/ENGINE-04, the two defects this plan deliberately left untouched per D-09) and `app.py`'s loaders (INTEG-01/INTEG-03), neither of which this phase touched.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All four created files verified on disk (`qc/autocorrect.py`, `tests/test_rules_reference_matches_registry.py`, `tests/test_deterministic_order.py`, `tests/test_registry_covers_emitted_ids.py`, plus this SUMMARY). All four task commits (`d357d43`, `d4587a3`, `2009dbe`, `4797cff`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean on resume: `python3 -m pytest tests/ -q` → 34 passed; `qc.canonical_order()` → 40 entries, all distinct, Schema→MLoS→Settlement→Takeoffpoint→Boundary order, ending `B0, B1, B2, B3`; AST inspection of `app.py`'s top-level function names confirmed none of the six relocated QC/autocorrection functions or three relocated predicates remain. Both tasks' mutate-and-revert acceptance criteria were re-verified during this resumed execution (deleting the MLoS table's `14` row; reverting `qc/domain.py`'s `YN_NA_COLS` to a set literal) and both left the working tree clean on revert (`git diff` against HEAD empty for both files after reverting).
