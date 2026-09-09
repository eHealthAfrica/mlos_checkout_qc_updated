---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 02
subsystem: testing
tags: [pytest, fixtures, pandas, ast, golden-baseline, regression-guard]

# Dependency graph
requires:
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 01)
    provides: "Pinned pandas 3.0.5 / numpy>=2.0.0,<3.0.0 environment and pytest.ini harness this plan's tests run against"
provides:
  - "tests/fixtures.py — plain builders (build_mlos_fixture, build_takeoff_fixture, load_boundary_fixtures) exercising every one of the 40 checks across all five QC layers"
  - "tests/conftest.py — mlos_df/takeoff_df/boundary_refs pytest fixtures wrapping those builders"
  - "tests/baseline/qc_baseline.json — frozen pre-extraction record of all six relocating functions' output"
  - "tests/baseline/capture_baseline.py — AST-based, streamlit-free re-capture script (not to be re-run against the frozen JSON after any extraction)"
  - "tests/test_baseline_records_the_duplicate_ids.py — standing guard pinning the baseline's coverage and the exact size of the F3 identifier collision"
affects: [01-qc-engine-seam-and-pinned-environment (plans 03-06 of this phase, which extract the six functions and must diff their own output against qc_baseline.json)]

# Actuals (#2632)
actuals:
  tokens: 9600
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plain-function fixture builders in tests/fixtures.py, wrapped by thin pytest fixtures in tests/conftest.py, so both pytest tests and the standalone capture script share one definition of the data"
    - "AST-based extraction (ast.parse + node lineno/end_lineno slicing) instead of hard-coded line-number slicing, so the capture script keeps working as later plans move code around"
    - "Golden-baseline JSON with sort_keys=True + explicit checks/detail sort by (QC Check, Description) and by every detail column — makes a set-literal-driven emission order (YN_NA_COLS) byte-stable across interpreter runs despite Python's per-process hash randomization"

key-files:
  created:
    - tests/fixtures.py
    - tests/conftest.py
    - tests/baseline/capture_baseline.py
    - tests/baseline/qc_baseline.json
    - tests/test_baseline_records_the_duplicate_ids.py
  modified: []

key-decisions:
  - "Row 1's timestamp cell is a deliberate Python None, not a string — the one exception to 'every cell is a string'. app.py's rule-1 null check uses pandas .isnull() directly, which does not catch empty strings (confirmed empirically); only a real null triggers it. An all-string fixture could not have exercised rule 1 at all."
  - "Reordered tests/fixtures.py's Takeoffpoint columns to put globalid first, not name — app.py's run_takeoff_qc always includes literal name/wardcode/code in its base column list plus columns[0] as the row-id column; a first column named 'name' produces a duplicate-column DataFrame that pandas.concat rejects with InvalidIndexError the moment two failing rows are collected. This is a real app.py behavior, not something introduced by extraction; the fixture's column order is an implementation choice, not something the plan's acceptance criteria pins."
  - "eha_guid/globalid test values are fixed hex strings (e.g. '11111111-1111-1111-1111-111111111111'), not uuid.uuid4() output — keeps every fixture-construction call deterministic, which matters because the same builders feed both pytest fixtures and the once-only baseline capture."

patterns-established:
  - "Frozen-artifact regression tests: assert facts about a JSON file that is never regenerated after the code it describes changes, with a module docstring warning against 'fixing' the tests when the described behavior is intentionally corrected elsewhere."

requirements-completed: [ENGINE-01, ENGINE-05, ENGINE-09]

coverage:
  - id: D1
    description: "tests/fixtures.py + tests/conftest.py provide a 10-row MLoS fixture (all 43 required columns), a 3-row Takeoffpoint fixture (all 4 required columns) and the 9,410-row boundary reference, exercising every one of the 40 checks emitted by the five QC layers with at least one failing and one passing row each"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "manual pytest fixture smoke test (mlos_df/takeoff_df/boundary_refs shapes) — not retained in the tree"
        status: pass
      - kind: other
        ref: "python3 -c \"...build_mlos_fixture()...\" -> mlos (10, 43) takeoff (3, 4) ref (9410, 6) bbox (9411, 5)"
        status: pass
    human_judgment: false
  - id: D2
    description: "tests/baseline/capture_baseline.py extracts the 11 constants and 9 functions by AST node name (no hard-coded app.py line numbers) into a streamlit-free module, and tests/baseline/qc_baseline.json records 40 emitted checks across 31 distinct identifiers — 3 numbered 11, 8 numbered 12 — reproduced byte-identical across 5 separate interpreter runs"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 tests/baseline/capture_baseline.py (x5, separate processes) -> identical md5 531ea704cfc44b09cad3fa96cd991b7b each time"
        status: pass
      - kind: other
        ref: "json.load(qc_baseline.json) -> 6 top-level keys, 40 total checks, 31 distinct Rule# values, autocorrect.log has no generated eha_guid value"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_baseline_records_the_duplicate_ids.py pins the F3 defect's exact size (3 checks numbered 11, 8 numbered 12, 40 emitted vs 31 distinct) against the frozen baseline, so a later identifier fix is measured against a written pre-state"
    requirement: "ENGINE-09"
    verification:
      - kind: unit
        ref: "tests/test_baseline_records_the_duplicate_ids.py#test_baseline_covers_every_layer"
        status: pass
      - kind: unit
        ref: "tests/test_baseline_records_the_duplicate_ids.py#test_baseline_records_three_checks_numbered_11"
        status: pass
      - kind: unit
        ref: "tests/test_baseline_records_the_duplicate_ids.py#test_baseline_records_eight_checks_numbered_12"
        status: pass
      - kind: unit
        ref: "tests/test_baseline_records_the_duplicate_ids.py#test_baseline_has_more_emitted_checks_than_distinct_identifiers"
        status: pass
      - kind: other
        ref: "python3 -m pytest tests/ -q -> 8 passed"
        status: pass
    human_judgment: false

# Metrics
duration: 17min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 02: Fixture Corpus and Pre-Extraction Golden Baseline Summary

**A 10-row MLoS fixture drives all 40 checks across five QC layers, and a frozen, byte-reproducible JSON captures app.py's current output — including the F3 defect's exact shape (3 checks numbered 11, 8 numbered 12) — before any of the six relocating functions move.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-09-09T19:21:26Z
- **Completed:** 2026-09-09T19:38:05Z
- **Tasks:** 3 of 3 completed
- **Files modified:** 5 created, 0 modified (beyond a within-plan fixture correction, see Deviations)

## Accomplishments
- `tests/fixtures.py` and `tests/conftest.py` give every later plan in this phase a single, shared, pytest-independent definition of the MLoS/Takeoffpoint/boundary-reference input data, rich enough that every one of the five QC layers' 40 checks has a failing row and a passing row.
- `tests/baseline/capture_baseline.py` extracts the six relocating functions (plus three helpers and eleven constants) from app.py by AST node name — not line number — so it keeps working as plans 03-06 move this code into a `qc/` package.
- `tests/baseline/qc_baseline.json` is a frozen, byte-stable record of app.py's actual behavior today: 40 emitted checks across 31 distinct identifiers, with the F3 collision (three checks sharing "11", eight sharing "12") recorded as a written fact.
- `tests/test_baseline_records_the_duplicate_ids.py` pins that fact with four tests that will keep passing after the identifier fix lands, because the baseline they check is never regenerated.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fixture corpus that exercises every rule in every layer** - `3a6b0e3` (feat)
2. **Task 2: Capture the pre-extraction golden baseline from the current app.py** - `59b44eb` (feat)
3. **Task 3: Standing guard that the baseline still describes the pre-fix state** - `cda85af` (test)

**Plan metadata:** committed alongside this summary

_Note: Task 3 carried `tdd="true"`, but as with Wave 1's Task 2, the "implementation" under test (`qc_baseline.json`) was already produced and frozen by Task 2 — there was no separate GREEN-phase production code to write against a failing test. The tests were authored against the already-correct frozen artifact and passed immediately (4/4), matching the file's own stated intent: pin a known-correct fact, not drive new implementation._

## Files Created/Modified
- `tests/fixtures.py` - new; `build_mlos_fixture()` (10 rows, all 43 columns), `build_takeoff_fixture()` (3 rows, all 4 columns), `load_boundary_fixtures()` (9,410-row ref + bbox), `FIXTURE_WARD_CODE = "81110"`
- `tests/conftest.py` - new; `mlos_df`/`takeoff_df` (function-scoped) and `boundary_refs` (session-scoped) pytest fixtures wrapping the builders
- `tests/baseline/capture_baseline.py` - new; `extract_pure_regions()` (AST-based extraction) and `build_baseline()` (runs all 5 QC layers + auto_correct_mlos's log against the raw fixture)
- `tests/baseline/qc_baseline.json` - new; frozen golden record, 47,386 bytes, six top-level layer keys
- `tests/test_baseline_records_the_duplicate_ids.py` - new; 4 tests pinning baseline coverage and the F3 collision's exact size

## Decisions Made
- **Row 1's `timestamp` is a real `None`, not a string.** app.py's rule-1 check uses `.isnull()` directly on columns loaded with `keep_default_na=False`; empirically confirmed that an empty string does not trip `.isnull()` under pandas 3.0.5's string dtype, only a genuine null does. Documented as the sole exception to "every cell is a string" in `tests/fixtures.py`'s module docstring, since without it rule 1 could never have a failing row in this fixture.
- **Takeoffpoint fixture column order is `globalid, name, code, wardcode`, not `name` first** — see Deviations below.
- **Fixed hex-string UUIDs, not `uuid.uuid4()`, for every eha_guid/globalid test value** — keeps `build_mlos_fixture()`/`build_takeoff_fixture()` deterministic across calls, which matters because the same functions back both the pytest fixtures (called once per test) and the baseline capture (whose reproducibility is explicitly verified).
- **One MLoS row combines up to 11 independent rule failures** (e.g. row 5 fails rule 11's three checks, rule 12's eight checks, rule 13 and rule 14 all at once) to keep the fixture at 10 rows rather than 20+, per the plan's "roughly 8 to 10 rows" guidance — verified no unintended cross-rule interaction (e.g. `accessibility_status="Sometimes"` on row 3 does not accidentally satisfy rule 7's `needs` condition, since "Sometimes" isn't in `{"Partially Accessible","Inaccessible"}`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Takeoffpoint fixture's default column order collided with `run_takeoff_qc`'s BASE list**
- **Found during:** Task 2, first run of `capture_baseline.py`
- **Issue:** `build_takeoff_fixture()` originally listed columns in required-set order (`name, code, wardcode, globalid`). Since the fixture has no `ogc_fid` column, app.py's `run_takeoff_qc` falls back to `takeoff.columns[0]` as its row-id column — which was `"name"` — while its `BASE` list *also* unconditionally includes the literal string `"name"`. The resulting column-selection (`takeoff[mask][cols]`) produced a DataFrame with two `"name"` columns, and `pandas.concat` raised `InvalidIndexError: Reindexing only valid with uniquely valued Index objects` the moment two failing takeoff rows (the orphan row and normal rows) were collected into one detail frame.
- **Fix:** Reordered the constructed DataFrame's columns to `globalid, name, code, wardcode` (`globalid` first, since it isn't one of the three literal names `run_takeoff_qc`'s BASE list always includes). This is a real, pre-existing behavior of app.py's `run_takeoff_qc`, unrelated to the TP2-TP5 rules under test — no validation code was changed, only the fixture's column order, which Task 1's acceptance criteria specifies as a column *set* match, not an order match.
- **Files modified:** `tests/fixtures.py`
- **Verification:** `capture_baseline.py` ran to completion after the reorder; `set(takeoff_df.columns) == set(TAKEOFF_REQUIRED_COLS)` still holds; 5 repeated runs of `capture_baseline.py` produced byte-identical `qc_baseline.json` (md5 `531ea704cfc44b09cad3fa96cd991b7b` every time).
- **Committed in:** `59b44eb` (part of Task 2's commit, since the issue surfaced while building Task 2's artifact)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 — blocking issue, surfaced by Task 2 in a Task-1-created file)
**Impact on plan:** No scope creep and no validation-code change. The fix is a fixture-construction detail (column order) that avoids an unrelated, pre-existing app.py collision; it does not touch any of the six relocating functions or change any check's logic.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`tests/fixtures.py`, `tests/conftest.py`, `tests/baseline/qc_baseline.json` and the standing guard test are in place and green (8/8 across the whole suite). Plans 03-06 of this phase — the `qc/` package extraction and the F3/F10 registry fix — can now run their own extracted functions against the same fixtures and diff the result against `tests/baseline/qc_baseline.json` field-by-field (everything except `Rule#`, which is expected to change for the 11 renamed checks). No blockers for the next plan in this phase. Reminder carried forward from this plan's own docstrings: `tests/baseline/qc_baseline.json` must never be regenerated after the extraction — `capture_baseline.py` is for reference/verification only from this point on.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All five created files verified on disk (`tests/fixtures.py`, `tests/conftest.py`, `tests/baseline/capture_baseline.py`, `tests/baseline/qc_baseline.json`, `tests/test_baseline_records_the_duplicate_ids.py`, plus this SUMMARY). All three task commits (`3a6b0e3`, `59b44eb`, `cda85af`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean: `python3 -m pytest tests/ -q` → 8 passed; `capture_baseline.py` run twice in direct succession produced byte-identical `qc_baseline.json` (`diff -q` reported no difference); the baseline records 40 emitted checks across 31 distinct identifiers, confirmed via direct JSON inspection.
