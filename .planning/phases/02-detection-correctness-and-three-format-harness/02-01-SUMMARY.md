---
phase: 02-detection-correctness-and-three-format-harness
plan: 01
subsystem: qc-engine
tags: [pandas, sqlite, streamlit-seam, tdd, golden-fixture, absence-predicate]

requires:
  - phase: 01-qc-engine-seam-and-pinned-environment
    provides: qc/ package seam (schema.py, mlos.py, settlement.py, takeoff.py, boundary.py, results.py registry), tests/fixtures.py, tests/baseline/ frozen JSON
provides:
  - qc.domain.ABSENCE_SENTINELS — the five-token case-insensitive absence sentinel set (D-04/D-05)
  - qc.predicates.vec_is_absent — vectorised absence predicate, exact-literal "NA" exempted case-sensitively
  - qc/loaders.py — pure, Streamlit-free MLOS_VIEW/TAKEOFF_VIEW, load_sqlite, load_view, load_csv, load_xlsx, load_takeoffpoint_file, load_submission
  - qc.mlos.run_mlos_qc's Rule 1 rebuilt on vec_is_absent (closes INTEG-01/F2)
  - tests/golden_fixture.py + tests/test_golden_three_format_parity.py — the ENGINE-06 three-format harness
  - tests/test_absent_sentinel_guard.py — D-05's required standing guard
  - app.py's get_uploaded_data reduced to a caching wrapper over qc.loaders.load_submission; session-state key mlos_raw (D-14 producer half)
affects: [02-02, 02-03, 02-04, 02-05, 02-06]

actuals:
  tokens: 11900
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Vectorised absence predicate (isna() | stripped-empty | sentinel-membership minus a case-sensitive exemption), never .apply, mirroring vec_is_uuid/vec_is_editor's existing shape"
    - "One boolean frame built once via pd.concat(keys=...) and reused for both a rule's failing-row mask and its detail column, so the two can never disagree"
    - "Pure parsing module (qc/loaders.py) behind a progress callback, so the Streamlit-free qc/ package never imports the UI framework while app.py's progress bar still updates at the same four points"
    - "Golden fixture: one shared row list, three format-specific byte writers, round-tripped through the real loaders — never synthesised frames directly"
    - "Baseline-scoped parity comparison (tests/test_extraction_parity.py): split live checks into 'in the frozen baseline' (compared field-by-field, with a MOVED_CHECKS override table) and 'new since the baseline' (must merely be registered in qc.canonical_order()) — so later plans can add rule identifiers without editing this file again"

key-files:
  created:
    - qc/loaders.py
    - tests/golden_fixture.py
    - tests/test_golden_three_format_parity.py
    - tests/test_absent_sentinel_guard.py
  modified:
    - qc/domain.py
    - qc/predicates.py
    - qc/mlos.py
    - tests/test_extraction_parity.py
    - app.py

key-decisions:
  - "D-05 confirmed as written at the Task 1 checkpoint: one uniform absence sentinel list for every column, with the exact literal NA exempted case-sensitively (not the narrower three-state predicate, not a per-column carve-out)."
  - "Golden fixture's Takeoffpoint sheet/view deliberately carries no TAKEOFF_REQUIRED_COLS-named column, so R2/R3/R4 stay silent uniformly across all three formats — CSV structurally can never carry embedded Takeoffpoint data, and giving sqlite/xlsx real cross-table columns would have broken the golden test's own 'identical check summary across formats' property. R2-R4's correctness is Plan 02's INTEG-02 scope, not this plan's."
  - "tests/test_extraction_parity.py's baseline comparison is now scoped to the intersection of live and frozen-baseline identifiers (planner decision 4), with a MOVED_CHECKS override table (one entry: Rule 1's Failing Rows 1->2, Fail % 10.0%->20.0%) and an explicit hand-derived assertion for Rule 1's two expected detail rows, keyed by eha_guid (master_id is not one of Rule 1's BASE/_NOT_NULL_COLS columns, so it is absent from Rule 1's own detail rows)."

requirements-completed: [INTEG-01, ENGINE-06]

coverage:
  - id: D1
    description: "Rule 1 reports identically across .sqlite, .csv and .xlsx encodings of one shared row list, including a row whose only defect is a logically blank required cell"
    requirement: "INTEG-01"
    verification:
      - kind: unit
        ref: "tests/test_golden_three_format_parity.py#test_three_formats_report_an_identical_check_summary"
        status: pass
    human_judgment: false
  - id: D2
    description: "vec_is_absent implements D-04/D-05's predicate exactly: sentinels absent in every case, exact NA present everywhere including FLAG_COLS and state_code, lowercase na present"
    requirement: "INTEG-01"
    verification:
      - kind: unit
        ref: "tests/test_absent_sentinel_guard.py (17 parametrised cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pure loaders relocated to qc/loaders.py with no Streamlit import; app.py delegates all parsing to qc.loaders.load_submission"
    requirement: "ENGINE-06"
    verification:
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py"
        status: pass
      - kind: unit
        ref: "AST check: app.py holds no load_sqlite/load_view/load_csv/load_xlsx/load_takeoffpoint_file definitions"
        status: pass
    human_judgment: false
  - id: D4
    description: "Frozen tests/baseline/ trio untouched; full suite at or above 38 passing"
    verification:
      - kind: unit
        ref: "git status --porcelain tests/baseline/ (empty) + python3 -m pytest tests/ -q (52 passed)"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 1: Absence Predicate, Pure Loaders, and the Three-Format Golden Harness Summary

**One `vec_is_absent` predicate now drives Rule 1 across `.sqlite`/`.csv`/`.xlsx`, backed by a real byte-level golden fixture, with parsing extracted into a Streamlit-free `qc/loaders.py`.**

## Performance

- **Duration:** 42 min (Task 1's checkpoint confirmed by the user earlier in this session; this continuation executed Tasks 2-3)
- **Started:** 2026-09-10T10:08:58Z (STATE.md, pre-Task-1-checkpoint)
- **Completed:** 2026-09-10T10:50:37Z
- **Tasks:** 3 (1 checkpoint:decision, confirmed; 2 executed)
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- Closed INTEG-01 (F2): Rule 1 (`qc.mlos.run_mlos_qc`) now flags a CSV/XLSX blank (`""`) exactly the same way it flags a `.sqlite` NULL, via `qc.predicates.vec_is_absent` built on `qc.domain.ABSENCE_SENTINELS`.
- Stood up ENGINE-06's golden three-format harness: `tests/golden_fixture.py` builds one shared row list into three real byte payloads, round-tripped through the actual loaders, and `tests/test_golden_three_format_parity.py` proves `run_schema_qc`/`run_mlos_qc`/`run_settlement_qc` report an identical Rule#-keyed summary, identical Total Rows, a non-vacuous Rule 1 failure, and canonical emission order — for all three formats.
- Extracted `qc/loaders.py`: `MLOS_VIEW`, `TAKEOFF_VIEW`, `load_sqlite`, `load_view`, `load_csv`, `load_xlsx`, `load_takeoffpoint_file` relocated verbatim, plus new `load_submission(file_like, filename, on_progress=None)` carrying the extension-dispatch logic that used to live inline in `app.py`'s `get_uploaded_data` (Phase 1 D-08).
- Wired `app.py` to the extraction: `get_uploaded_data` is now only the session-state caching wrapper, delegating all parsing to `qc.loaders.load_submission` via a progress callback; its session-state key and local variable renamed `mlos_df` -> `mlos_raw` (D-14's producer half).
- Added D-05's required standing guard (`tests/test_absent_sentinel_guard.py`): the exact literal `NA` survives as present in every `FLAG_COLS` column and as `state_code`; lowercase `na` survives for the unrelated reason of not being a sentinel member; every `ABSENCE_SENTINELS` token reads absent in three casings; the sentinel set is defensively pinned to exactly five members excluding `NA`.
- Rescoped `tests/test_extraction_parity.py` per planner decision 4 so no later plan in this phase needs to edit it again: baseline comparison is now split into "identifiers the frozen baseline carries" (compared field-by-field, with a `MOVED_CHECKS` override table) and "identifiers registered since" (must merely exist in `qc.canonical_order()`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Confirm D-05 (checkpoint:decision)** - no commit (decision-only gate; confirmed `CONFIRMED` by the user in the prior session)
2. **Task 2: Tracer — one absence predicate, from bytes in three formats through the pure loaders to Rule 1** (tdd="true")
   - `672c6a4` `test(02-01): add golden three-format fixture and rescope extraction parity for D-04` (RED)
   - `548542b` `feat(02-01): uniform absence predicate, pure loaders, and Rule 1 fix (INTEG-01, D-04, D-05)` (GREEN)
3. **Task 3: Wire app.py to the extracted loaders and add D-05's standing sentinel guard** - `c99062c` `feat(02-01): wire app.py to qc.loaders and add D-05's standing sentinel guard`

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `qc/domain.py` - added `ABSENCE_SENTINELS` (frozenset of 5 case-insensitive tokens), adjacent to `VALID_YN_NA`
- `qc/predicates.py` - added `vec_is_absent(series)`, vectorised, built on `isna()` / empty-stripped / sentinel-membership minus a case-sensitive `"NA"` exemption
- `qc/mlos.py` - Rule 1 rebuilt on one shared boolean frame from `vec_is_absent`, reused for both the failing-row mask and the `Null Fields` detail column
- `qc/loaders.py` (new) - pure, Streamlit-free parsing module; `load_submission` is the new extension-dispatch entry point
- `tests/golden_fixture.py` (new) - plain-function byte builders (`.sqlite`/`.csv`/`.xlsx`) for a shared 2-row MLoS fixture with one deliberately blank `timestamp` cell
- `tests/test_golden_three_format_parity.py` (new) - ENGINE-06's cross-format check-summary parity test
- `tests/test_absent_sentinel_guard.py` (new) - D-05's required standing guard, 17 parametrised assertions
- `tests/test_extraction_parity.py` - rescoped to a baseline-intersection comparison with a `MOVED_CHECKS` override table and an explicit hand-derived Rule 1 detail assertion
- `app.py` - removed the five relocated loader definitions and the `MLOS_VIEW`/`TAKEOFF_VIEW` constants (now imported from `qc.loaders`); `get_uploaded_data` reduced to a caching wrapper; session-state key renamed `mlos_df` -> `mlos_raw`

## Decisions Made

- **D-05 confirmed as written** at the Task 1 checkpoint (`CONFIRMED`): one uniform absence sentinel list applies to every column, with the exact literal `NA` exempted case-sensitively. Neither declined alternative (the narrower three-state predicate, or a per-column carve-out) was implemented.
- **Golden fixture's Takeoffpoint table carries no `TAKEOFF_REQUIRED_COLS`-named column** (Claude's discretion during implementation, consistent with the plan's own out-of-scope note that R2-R4's cross-table correctness is Plan 02's work): CSV structurally can never carry embedded Takeoffpoint data through `load_submission`, so giving the `.sqlite`/`.xlsx` Takeoffpoint table real `name`/`code`/`wardcode` columns would have made R2/R3/R4 appear for two formats and not the third — breaking exactly the "identical check summary across all three formats" property this golden test exists to prove. The sqlite/xlsx Takeoffpoint table/sheet still exists (satisfying `load_submission`'s unconditional two-view load and the "two sheets" instruction) but is inert by construction.
- **`tests/test_extraction_parity.py`'s baseline comparison is scoped to the baseline's own identifier set** (planner decision 4, implemented via `_split_by_baseline_ids` / `_assert_new_identifiers_are_registered`), with a `MOVED_CHECKS` override table holding the single entry this task creates (Rule 1: Failing Rows 1->2, Fail % `"10.0%"` -> `"20.0%"`), and Rule 1's own detail rows excluded from the generic diff in favour of one explicit hand-derived assertion keyed by `eha_guid` (Rule 1's detail sub-frame never carries `master_id` — it is outside both `BASE` and `_NOT_NULL_COLS` — so `eha_guid`, which is in `_NOT_NULL_COLS`, is the safe unique key here instead).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `master_id` is not a column of Rule 1's detail sub-frame**
- **Found during:** Task 2, writing `tests/test_extraction_parity.py`'s hand-derived Rule 1 detail assertion
- **Issue:** The plan's own action text for `tests/test_extraction_parity.py` describes "one explicit hand-derived assertion on the two expected rows' `master_id` and Null Fields values", but Rule 1's `BASE` column list (`state_code`, `state_name`, `lga_name`, `ward_code`, `settlement_name`, `takeoffpoint`, `takeoffpoint_code`) plus `_NOT_NULL_COLS` never includes `master_id` — running the test against `master_id` raised `KeyError: 'master_id'`.
- **Fix:** Used `eha_guid` (a member of `_NOT_NULL_COLS`, unique per fixture row, and present in Rule 1's detail sub-frame) as the identifying key instead, mapping to the same two expected `Null Fields` values (`"timestamp"` for M-0002/Alpha, `"latitude, longitude"` for M-0003/Bravo).
- **Files modified:** `tests/test_extraction_parity.py`
- **Verification:** `python3 -m pytest tests/test_extraction_parity.py -q` — 7 passed
- **Committed in:** `672c6a4` (Task 2 RED commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix, Rule 1)
**Impact on plan:** Cosmetic correction to one test's identifying key; no behavioural change to what is being proven. No scope creep.

### Acceptance-Criterion Discrepancy (documented, not auto-fixed)

Task 3's acceptance criteria include: `python3 -c 'import re; s = open("app.py").read(); print(len(re.findall(r"progress\.progress\(", s)))'` should "report a count no lower than it did before this task." The count dropped from 12 (pre-task) to 5 (post-task).

This is a direct, unavoidable consequence of the same task's own prescribed design: `qc.loaders.load_submission`'s `on_progress` callback (mandated by Task 2's action text: "`on_progress` is an optional callable taking one integer, invoked at the same four points... passing a callable keeps `qc/` free of any Streamlit reference") consolidates what used to be six inline `progress.progress(35)`/`progress.progress(90)`/`progress.progress(65)` call sites (one per format branch in the old `get_uploaded_data`) into a single `_on_progress` closure in `app.py`, invoked multiple times at runtime by code that now lives in `qc/loaders.py`. The literal source-text occurrence count in `app.py` necessarily drops because the per-branch dispatch logic moved out of `app.py` entirely — that is the whole point of the extraction.

Verified functionally instead of via the grep proxy: calling `load_submission` with a value-recording callback confirms the same four progress values still fire at the same points, in order — `[10, 35, 90]` for CSV/XLSX, `[10, 35, 65, 90]` for `.sqlite` — exactly matching the pre-extraction behaviour's four progress-bar updates before the final `progress(100)`. The user-visible progress bar is unchanged; only the source-text shape of the mechanism moved, as this plan required.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (blank-side cross-table matches, INTEG-02) can now build directly on `vec_is_absent` and `qc/loaders.py` without re-deriving either.
- `tests/test_extraction_parity.py`'s baseline-intersection scoping means plans 02, 03 and 05 can register their own new rule identifiers (`2.missing` etc., `S3`, `B4`, `B5`) without editing this file — only `_assert_new_identifiers_are_registered`'s registration check applies to them.
- The golden three-format harness (`tests/golden_fixture.py`) is reusable scaffolding: later plans needing their own format-parity proof can extend `build_shared_mlos_rows()` or add new writer variants rather than building a fixture from scratch.
- No blockers. Full suite: 52 passed, 0 failed; frozen baseline trio untouched.

## Self-Check: PASSED

All 9 key files found on disk; all 3 task commits (`672c6a4`, `548542b`, `c99062c`) found in git log.

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*
