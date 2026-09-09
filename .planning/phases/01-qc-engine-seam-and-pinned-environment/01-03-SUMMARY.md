---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 03
subsystem: infra
tags: [python, package-extraction, rule-registry, ast, pytest, streamlit-boundary]

# Dependency graph
requires:
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 01)
    provides: "Pinned pandas 3.0.5 / numpy>=2.0.0,<3.0.0 environment and pytest.ini harness this plan's tests run against"
  - phase: 01-qc-engine-seam-and-pinned-environment (plan 02)
    provides: "tests/fixtures.py, tests/conftest.py, tests/baseline/qc_baseline.json — the fixture corpus and frozen pre-extraction baseline this plan's parity test diffs against"
provides:
  - "qc/ package with a rule-identity registry (Rule dataclass, register(), canonical_order()) that rejects duplicate identifiers at import time"
  - "qc/domain.py, qc/predicates.py — relocated domain constants and predicate helpers, importable with no UI-framework dependency"
  - "qc/schema.py — the Schema QC layer (S1/S2), relocated and registered at import time; app.py now calls qc.schema.run_schema_qc and pipes results through qc.sort_by_registry"
  - "qc/__init__.py facade — sort_by_registry(), the canonical re-sort every layer's call site will use"
  - "tests/test_results_registry.py, tests/test_no_streamlit_in_qc.py, tests/test_extraction_parity.py — three standing guards plans 04-06 build on directly"
affects: [01-qc-engine-seam-and-pinned-environment (plans 04-06 of this phase, which relocate the remaining four QC layers through the same seam and add their own parity/registration tests)]

# Actuals (#2632)
actuals:
  tokens: 16500
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Import-time rule registration: each qc/<layer>.py module calls register() at module scope, so importing qc (which imports every layer submodule via __init__.py) populates the registry as a side effect of import alone"
    - "Package facade as the only cross-layer importer: qc/__init__.py imports schema and re-exports the registry surface; sibling modules (predicates -> domain) import each other directly, never through the package's own __init__, avoiding circular-import partial-initialization"
    - "AST-based import-boundary guard: parse every .py file under qc/ with ast.parse, walk Import/ImportFrom nodes, and match the first dotted component exactly (submodule imports of the UI framework are offenders; unrelated packages sharing a name prefix are not)"
    - "Runtime import-boundary proof via subprocess + sys.meta_path.find_spec: a meta_path finder implementing find_spec (not the CPython-3.13-defunct find_module) raises ImportError for the blocked framework in a fresh interpreter, then imports qc and asserts a success token on stdout"

key-files:
  created:
    - qc/__init__.py
    - qc/results.py
    - qc/domain.py
    - qc/predicates.py
    - qc/schema.py
    - tests/test_results_registry.py
    - tests/test_no_streamlit_in_qc.py
    - tests/test_extraction_parity.py
  modified:
    - app.py

key-decisions:
  - "sys.meta_path finders in this environment (CPython 3.13.1) must implement find_spec, not the legacy find_module — the latter is silently ignored by the import system. Verified empirically before writing the subprocess-blocking test in tests/test_no_streamlit_in_qc.py; the research's Code Examples section did not specify which finder protocol to use."
  - "Used pytest's mlos_df/takeoff_df fixtures (from tests/conftest.py, wrapping tests/fixtures.py's builders) in tests/test_extraction_parity.py rather than calling the plain builders directly, for consistency with the fixture-sharing pattern plan 02 established."

patterns-established:
  - "Frozen-baseline parity test: normalize_checks/normalize_detail helpers in tests/test_extraction_parity.py reproduce capture_baseline.py's own sort keys exactly, so a later plan's layer-specific parity test can import and reuse both helpers unchanged rather than re-deriving the normalization."

requirements-completed: [ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-09]

coverage:
  - id: D1
    description: "qc/ package exists with a rule registry that rejects duplicate identifiers at import time (ValueError naming both the offending id and the layer/name already holding it), and canonical_order() returns registration-order identifiers, empty-list-safe"
    requirement: "ENGINE-02"
    verification:
      - kind: unit
        ref: "tests/test_results_registry.py#test_duplicate_rule_id_raises_at_registration"
        status: pass
      - kind: unit
        ref: "tests/test_results_registry.py#test_duplicate_is_rejected_across_different_layers"
        status: pass
      - kind: unit
        ref: "tests/test_results_registry.py#test_current_ruleset_has_no_duplicates"
        status: pass
      - kind: unit
        ref: "tests/test_results_registry.py#test_canonical_order_of_an_empty_registry_is_an_empty_list"
        status: pass
      - kind: other
        ref: "python3 -c \"import qc; print(qc.canonical_order())\" -> ['S1', 'S2']"
        status: pass
    human_judgment: false
  - id: D2
    description: "qc/ imports with no UI-framework dependency at all — statically (AST scan of every module under qc/) and at runtime (subprocess proof that `import qc` succeeds when the UI framework is blocked via sys.meta_path)"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py#test_no_module_under_qc_imports_the_ui_framework"
        status: pass
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py#test_guard_scanned_a_nonzero_number_of_files"
        status: pass
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py#test_guard_matches_the_first_dotted_component_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py#test_qc_imports_when_the_ui_framework_is_unavailable"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Schema QC layer is relocated into qc/schema.py, registered as S1/S2 at import time, and app.py calls qc.schema.run_schema_qc(...) then qc.sort_by_registry(...) at the Schema call site — no top-level run_schema_qc/pct/vec_is_uuid/vec_is_editor remain in app.py, and no application behavior changed"
    requirement: "ENGINE-01"
    verification:
      - kind: other
        ref: "python3 -c \"...import ast...\" -> app.py's top-level function set contains neither run_schema_qc, pct, vec_is_uuid nor vec_is_editor"
        status: pass
      - kind: other
        ref: "python3 -m pytest tests/ -q -> 17 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "The extracted Schema layer's output is byte-identical to the frozen pre-extraction baseline's schema entry, field for field (Rule#, QC Check, Description, Failing Rows, Total Rows, Fail %, Status), and this parity test's failure message names the diverging field when one exists"
    requirement: "ENGINE-01"
    verification:
      - kind: unit
        ref: "tests/test_extraction_parity.py#test_schema_layer_matches_baseline"
        status: pass
      - kind: other
        ref: "manual mutate-and-revert: inverted qc/schema.py's Status comparison -> test failed naming field 'Status'; reverted -> 1 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "YN_NA_COLS is now an ordered tuple (highrisk, slums, densely_populated, hard2reach, border, nomadic, riverine, fulani) in qc/domain.py, matching the FLAG_COLS convention, with the registry's canonical_order() as the structural backstop against a future unordered collection reopening the same defect"
    requirement: "ENGINE-09"
    verification:
      - kind: other
        ref: "qc/domain.py source inspection: YN_NA_COLS declared as a tuple literal in the exact D-01 order"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 03: The qc/ Seam, Proven End to End Through the Schema Layer Summary

**A rule registry that rejects duplicate identifiers at import time, a `qc/` package that imports with zero UI-framework dependency (statically and at runtime), and an `app.py` calling across that boundary with the canonical re-sort already wired into the Schema layer's real call path.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-09T19:39:57Z
- **Completed:** 2026-09-09T19:51:15Z
- **Tasks:** 3 of 3 completed
- **Files modified:** 9 (1 modified, 8 created)

## Accomplishments
- `qc/results.py` establishes the one genuinely new mechanism this phase introduces: a frozen-dataclass `Rule` registry that raises `ValueError` — naming both the colliding identifier and the layer/name that already own it — the instant a second `register()` call reuses an identifier, whether from the same layer or a different one.
- `qc/domain.py`, `qc/predicates.py` and `qc/schema.py` relocate the constants, predicate helpers and Schema QC layer verbatim (per D-07), with `YN_NA_COLS` converted from a `set` to an ordered `tuple` per D-10/D-11 — closing the non-deterministic-iteration half of the F10 defect at its source, with the registry's `canonical_order()` as the structural backstop (D-12).
- `app.py` calls `qc.schema.run_schema_qc(...)` and pipes the result through `qc.sort_by_registry(...)` at the real Schema call site — this is what makes the cut a tracer rather than a file move: the ordering mechanism is exercised on the production call path from the first commit, not just in a test.
- Three standing test files (`test_results_registry.py`, `test_no_streamlit_in_qc.py`, `test_extraction_parity.py`) prove the registry, the import boundary and the parity claim, and expose reusable helpers (`normalize_checks`, `normalize_detail`) plans 04-06 will import directly rather than re-deriving.

## Task Commits

Each task was committed atomically:

1. **Task 1: The qc/ seam, proven end to end through the Schema layer** - `2157237` (feat)
2. **Task 2: Standing guards for rule identity and the import boundary** - `e361292` (test)
3. **Task 3: Parity harness comparing the extracted layer against the frozen baseline** - `c46dabd` (test)

**Plan metadata:** committed alongside this summary

_Note: Tasks 2 and 3 carried `tdd="true"`, but as with Wave 1 and Wave 2's TDD tasks, the "implementation" under test (the registry and the Schema layer, both produced by Task 1) already existed and was already correct — there was no separate GREEN-phase production code to write against a failing test. Each set of tests was authored against already-correct code and passed immediately, then had its detection power verified separately: Task 2's subprocess-blocking mechanism was proven against a live interpreter (the naive `find_module`-based approach was tried first and found NOT to be honored by CPython 3.13, then corrected to `find_spec` before being written into the test file — see Deviations), and Task 3's parity assertion was proven via a manual mutate-and-revert cycle on `qc/schema.py`'s Status comparison, per the task's own acceptance criterion."_

## Files Created/Modified
- `qc/results.py` - new; `Rule` frozen dataclass, `register()`, `canonical_order()`, `_REGISTRY`/`_ORDER`
- `qc/domain.py` - new; relocated constants, `YN_NA_COLS` as an ordered tuple, `FLAG_COLS`, `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`
- `qc/predicates.py` - new; relocated `pct`, `vec_is_uuid`, `vec_is_editor`
- `qc/schema.py` - new; relocated `run_schema_qc` plus its S1/S2 `register()` calls
- `qc/__init__.py` - new; imports `schema` (triggering registration), re-exports `Rule`/`register`/`canonical_order`, defines `sort_by_registry`
- `app.py` - modified; removed the relocated constants/functions, re-imports the six symbols still needed by the four QC functions and `auto_correct_mlos` that remain, and calls `qc.schema.run_schema_qc` + `qc.sort_by_registry` at the Schema call site
- `tests/test_results_registry.py` - new; 4 tests defending rule-identity uniqueness
- `tests/test_no_streamlit_in_qc.py` - new; 4 tests defending the `qc/` import boundary, statically and at runtime
- `tests/test_extraction_parity.py` - new; 1 test plus two reusable normalisation helpers proving the extracted Schema layer matches the frozen baseline

## Decisions Made
- **`find_spec`, not `find_module`, for the `sys.meta_path` blocking finder.** Verified empirically in this environment (CPython 3.13.1) that a finder implementing only `find_module` is silently never consulted — the import succeeds anyway, which would have made `test_qc_imports_when_the_ui_framework_is_unavailable` a false-positive pass proving nothing. Switched to `find_spec(name, path=None, target=None)` and confirmed the block actually takes effect before writing it into the subprocess script.
- **Used the `mlos_df`/`takeoff_df` pytest fixtures (not the plain `fixtures.py` builders directly) in `test_extraction_parity.py`**, matching the fixture-sharing convention plan 02 established via `tests/conftest.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `find_module`-based `sys.meta_path` finder silently not honored under CPython 3.13**
- **Found during:** Task 2, while writing `test_qc_imports_when_the_ui_framework_is_unavailable`
- **Issue:** The research's reference shape for the runtime import-boundary proof did not specify which meta-path-finder protocol method to implement. A `find_module`-based finder (the older, pre-PEP-451 protocol) was tried first; empirically, `import streamlit` still succeeded through it — CPython 3.13's import system no longer consults `find_module` on meta-path finders at all, so the test would have passed vacuously (never actually blocking the import it claims to block).
- **Fix:** Rewrote the finder to implement `find_spec(name, path=None, target=None)` (the current meta-path finder protocol), confirmed manually that it does raise `ImportError` for the blocked framework, then wrote it into the subprocess script.
- **Files modified:** `tests/test_no_streamlit_in_qc.py`
- **Verification:** Direct interpreter check confirmed `find_module` silently ignored, `find_spec` correctly blocked; `test_qc_imports_when_the_ui_framework_is_unavailable` passes with the corrected finder, and fails to import `streamlit` as intended when exercised standalone.
- **Committed in:** `e361292` (Task 2's own commit — the bug was caught and fixed before the task's tests were ever committed in a false-positive state)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — bug in an in-progress test file, caught before commit)
**Impact on plan:** No scope creep. The fix corrected a test's own blocking mechanism before it was committed; it does not touch any relocated QC logic or change any check result.

## Issues Encountered

**Acceptance criterion `grep -c 'VALID_ACC' app.py` reports 1 — not satisfied, and not satisfiable within this plan's own declared scope.** The plan's Task 1 acceptance criteria list this exact command with an expected count of 1 ("the single re-import line, not a definition"). The actual, correct result is 2: the re-import line this plan adds (`from qc.domain import VALID_ACC, ...`) plus the pre-existing usage line inside `run_mlos_qc`'s rule-6 check (`app.py`, unchanged by this plan). This is not a regression — `git show HEAD~3:app.py | grep -c VALID_ACC` (the pre-refactor state) already reported 2 for the same reason (one definition line, one usage line). The plan's own `<action>` text is explicit that `run_mlos_qc` "remain[s] in `app.py` until plans 04, 05 and 06 relocate them," so a second, non-import reference to `VALID_ACC` inside `app.py` is an expected, in-scope fact at this point in the phase, not a defect this plan introduced or could resolve without relocating `run_mlos_qc` early (out of this plan's scope, and Rule 4 territory if attempted). Logged as `deviation` entry #1 in `.planning/WINDOWS.md` rather than silently ignored. Every other acceptance criterion in Task 1, and both plan-level `<verify>` commands, pass as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`qc/results.py`, `qc/domain.py`, `qc/predicates.py`, `qc/schema.py` and `qc/__init__.py` are in place and green, alongside three standing test files (17 passed across the whole suite). Plans 04, 05 and 06 of this phase can now relocate `run_mlos_qc`, `run_settlement_qc`, `run_takeoff_qc`, `run_ward_boundary_qc` and `auto_correct_mlos` through the exact same route this plan proved: a new `qc/<layer>.py` module, import-time `register()` calls reproducing the frozen identifiers (including the F3 fix for rules 11 and 12, per `01-PATTERNS.md`), and a call-site rewire in `app.py` piping through `qc.sort_by_registry`. `tests/test_extraction_parity.py`'s `normalize_checks`/`normalize_detail` helpers are ready to be imported by each new layer's own parity test without modification. One open item carried forward, not a blocker: `.planning/WINDOWS.md` entry #1 documents the unsatisfiable `grep -c VALID_ACC` acceptance criterion above — it will resolve itself once plan 04 relocates `run_mlos_qc` and its `VALID_ACC` usage out of `app.py`.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All eight created files verified on disk (`qc/__init__.py`, `qc/results.py`, `qc/domain.py`, `qc/predicates.py`, `qc/schema.py`, `tests/test_results_registry.py`, `tests/test_no_streamlit_in_qc.py`, `tests/test_extraction_parity.py`, plus this SUMMARY). All three task commits (`2157237`, `e361292`, `c46dabd`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean: `python3 -m pytest tests/ -q` → 17 passed; `python3 -c "import qc; print(qc.canonical_order())"` → `['S1', 'S2']`; AST inspection of `app.py`'s top-level function names confirmed none of `run_schema_qc`, `pct`, `vec_is_uuid`, `vec_is_editor` remain; `tests/test_extraction_parity.py::test_schema_layer_matches_baseline` passed, confirmed to have real detection power via mutate-and-revert.
