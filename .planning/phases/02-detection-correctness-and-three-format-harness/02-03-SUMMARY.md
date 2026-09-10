---
phase: 02-detection-correctness-and-three-format-harness
plan: 03
subsystem: qc-engine
tags: [pandas, column-normalisation, schema-alignment, tdd, integ-03]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "qc.results.register/canonical_order (plan 01), the qc/ Streamlit-free seam (Phase 1)"
provides:
  - "qc.columns.normalize_name / qc.columns.normalize_columns — purely typographic column-name normalisation with collision detection run against the proposed rename map before any rename is applied (D-08/D-09/D-10)"
  - "qc.schema.run_schema_qc's new S3 'Column Name Collision' check, registered immediately after S2, with a keyword-only collisions parameter defaulting to an empty tuple"
  - "qc.schema.run_schema_qc's S1/S2 now compare against the frame's columns as given, removing the schema layer's own second, diverging lower-cased view of the column set (F7's root cause)"
  - "tests/test_readme_columns_match_domain.py — standing structural backstop for D-20, asserting README.md's 43+4 required-column tables match qc.domain exactly"
affects: [02-04, 02-05, 02-06]

actuals:
  tokens: 8478
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Collision-before-rename ordering: normalize_columns walks the original header list once, groups every header by its normalised form, and only builds/applies a rename map for headers that never joined a multi-member group — so DataFrame.rename can never be handed a mapping that produces duplicate target labels"
    - "Non-row denominator for a run-level Schema check: S3's Total Rows is the MLoS column count, not len(mlos), following S1/S2's own precedent rather than defaulting to a row count out of habit"
    - "Keyword-only optional parameter with an empty-tuple default so every existing lower-arity caller keeps working and the new check emits PASS for them by construction, not by editing every call site"

key-files:
  created:
    - qc/columns.py
    - tests/test_column_collision.py
    - tests/test_readme_columns_match_domain.py
  modified:
    - qc/schema.py
    - app.py

key-decisions:
  - "qc/columns.py carries zero relative sibling imports: normalize_name/normalize_columns perform no canonical-set lookup and no semantic aliasing at all (D-08/D-09 explicitly forbid it), so there is nothing in qc.domain, qc.predicates or qc.results for this module to legitimately import. The plan's own acceptance criterion assuming a relative import exists is a discrepancy, documented below rather than satisfied with a dead import added solely to pass a grep count."
  - "S3's collision-group shape is a list of dicts {'normalized': str, 'originals': list[str]}, one dict per colliding group (not per pair) — chosen so a three-way collision on one normalised name produces one group naming all three members, matching the plan's explicit non-negotiable requirement."
  - "S1/S2's comparison changed from `mlos.columns.str.strip().str.lower()` to the frame's raw `mlos.columns`/`takeoff.columns` — this is the literal F7 fix INTEG-03 targets (the schema check's own second, diverging view of the column set), proven behaviour-neutral for the shared fixture by an explicit unchanged-values test, since its headers are already canonical."
  - "Both D-10 planner-clarification sub-cases (neither collision member already canonical vs. one member already spelled exactly as canonical) are each covered by their own named test, per the plan's instruction to record which sub-case a test exercises in its docstring."

requirements-completed: [INTEG-03]

coverage:
  - id: D1
    description: "normalize_name is purely typographic (trim/lowercase/whitespace-hyphen-to-underscore/collapse repeated underscores), idempotent, and never raises on empty or whitespace-only input"
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_column_collision.py#test_normalize_name_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_normalize_name_empty_and_whitespace_only_return_empty_string"
        status: pass
    human_judgment: false
  - id: D2
    description: "normalize_columns detects a colliding rename BEFORE applying any rename, leaves the colliding group's original headers un-normalised, and never produces a duplicate column label — proven both structurally and by the concrete crash D-10 exists to prevent (selecting an original colliding header still returns a Series)"
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_column_collision.py#test_normalize_columns_colliding_pair_left_unnormalised_with_no_duplicate_labels"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_normalize_columns_colliding_pair_selecting_original_header_still_returns_a_series"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_normalize_columns_three_way_collision_reports_one_group_not_two_pairwise"
        status: pass
    human_judgment: false
  - id: D3
    description: "S3 registers immediately after S2, emits PASS with a column-count denominator when nothing collided (including for every pre-existing two-argument caller) and FAIL naming every original header in each colliding group when something did; S1/S2 are unaffected"
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_column_collision.py#test_s3_position_in_canonical_order_is_immediately_after_s2"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_s3_emits_pass_with_column_count_denominator_when_called_two_argument"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_s3_reports_a_one_group_collision_naming_both_original_headers"
        status: pass
      - kind: unit
        ref: "tests/test_column_collision.py#test_s3_does_not_affect_s1_or_s2_values_for_the_shared_fixture"
        status: pass
    human_judgment: false
  - id: D4
    description: "README.md's 43 MLoS + 4 Takeoffpoint required-column tables match qc.domain.MLOS_REQUIRED_COLS/TAKEOFF_REQUIRED_COLS exactly, giving D-20's canonical-vocabulary directive a standing structural backstop"
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_readme_columns_match_domain.py (3 tests, all passing)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full suite at or above 53 passing (87 actual); frozen baseline trio untouched; S3 documented in the sidebar in the same commit as its registration"
    verification:
      - kind: unit
        ref: "python3 -m pytest tests/ -q (87 passed) + git status --porcelain tests/baseline/ tests/test_extraction_parity.py tests/fixtures.py tests/conftest.py (empty) + grep -c '^| S3 |' app.py (1)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 3: Column Normalisation and the S3 Collision Check Summary

**A purely typographic `qc.columns.normalize_columns` helper that detects header collisions before renaming, plus a new `S3` Schema-layer check that fails naming every colliding header instead of letting `pandas` silently produce a duplicate column label.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-10T12:46:00Z
- **Completed:** 2026-09-10T13:11:20Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- Closed the engine half of INTEG-03 (F7): `qc/columns.py`'s `normalize_name` is a purely typographic transform (trim, lowercase, whitespace/hyphen runs to underscore, collapse repeated underscores) with no semantic aliasing and no canonical-set lookup, and `normalize_columns` detects same-normalised-name collisions against the *proposed* rename map before applying any rename — so a colliding pair is left exactly as it arrived and `DataFrame.rename` can never be handed a mapping that would produce a duplicate column label (the empirically-verified crash: `frame["x"]` returning a `DataFrame` instead of a `Series`, and the next `.str` accessor raising `AttributeError`).
- Registered `S3` "Column Name Collision" in `qc.schema` immediately after `S2`, reading its collision groups from a new keyword-only `collisions` parameter defaulting to an empty tuple, so every existing two-argument call in the suite keeps working and `S3` emits PASS for them.
- Removed the schema layer's own second, diverging view of the column set — `S1`/`S2` now compare against `mlos.columns`/`takeoff.columns` as given, not a defensively lower-cased projection — proven behaviour-neutral for the shared 43/4-column fixture by an explicit unchanged-values test.
- Documented `S3` in `app.py`'s Schema Alignment Rules sidebar table in the same commit as its registration, and wired the `run_schema_qc` call site to read `st.session_state["column_collisions"]` (empty-tuple default), so this task is green before and stays green after a later plan populates that key at load.
- Added `tests/test_readme_columns_match_domain.py`, giving D-20's "README.md is the canonical column vocabulary" directive a standing structural backstop: three tests asserting `README.md`'s two required-column tables match `qc.domain.MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS` exactly, with a defensive floor pinning the parser to the expected 43/4 counts.
- Full suite: 87 passed (baseline was 78 entering task 2, 61 entering the plan), frozen `tests/baseline/` trio and `tests/test_extraction_parity.py` untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: The typographic normalisation helper, with collision detected before any rename** (tdd="true")
   - `2c10d8a` `test(02-03): add typographic column normalisation with collision-before-rename ordering`
2. **Task 2: Register and emit S3, and document it in the sidebar reference** (tdd="true")
   - `f954681` `feat(02-03): register S3 column-collision check and README-vs-domain structural backstop`

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `qc/columns.py` (new) - `normalize_name` and `normalize_columns`, pure and Streamlit-free, no sibling imports (see Deviations)
- `qc/schema.py` - registers `S3` immediately after `S2`; `run_schema_qc` gains `collisions=()`; `S1`/`S2` compare raw columns instead of a lower-cased projection
- `app.py` - `S3` row added to the Schema Alignment Rules sidebar table; `run_schema_qc` call site passes `st.session_state.get("column_collisions", ())`
- `tests/test_column_collision.py` (new in task 1, extended in task 2) - 23 tests covering the transform, both collision sub-cases, the three-way-collision single-group requirement, the empty/single-column edges, and S3's registration, position, PASS/FAIL emission, detail-row shape, and unchanged S1/S2 values
- `tests/test_readme_columns_match_domain.py` (new) - 3 tests giving D-20 a structural backstop

## Decisions Made

- **`qc/columns.py` carries zero relative sibling imports.** `normalize_name`/`normalize_columns` perform no canonical-set lookup and no semantic aliasing at all — D-08 and D-09 explicitly forbid both — so there is nothing in `qc.domain`, `qc.predicates` or `qc.results` for this module to legitimately import. See Deviations below.
- **S3's collision-group shape** is a list of dicts `{"normalized": str, "originals": list[str]}`, one dict per colliding group rather than per pair, so a three-way collision on one normalised name produces one group naming all three members — matching the plan's explicit non-negotiable requirement and consumed directly by `qc.schema`'s description/detail-row construction.
- **S1/S2's comparison changed from a lower-cased projection to the frame's raw columns** — this is the literal F7 fix INTEG-03 targets. Proven behaviour-neutral for the shared fixture (its headers are already canonical snake_case) by an explicit test asserting unchanged `Failing Rows`/`Total Rows` for both checks.
- **Both of D-10's planner-clarification sub-cases are each covered by their own named test** (`test_s3_reports_a_one_group_collision_naming_both_original_headers` for the case where neither colliding member is already canonical, `test_s3_already_canonical_member_of_a_colliding_pair_is_not_forced_missing` for the case where one member is), per the plan's instruction to record which sub-case a test exercises so the distinction survives.

## Deviations from Plan

### Auto-fixed Issues

None — no bug, missing critical functionality, or blocking issue was discovered during either task that required an unplanned fix.

### Acceptance-Criterion Discrepancy (documented, not auto-fixed)

Task 1's acceptance criteria include: `grep -c "from \." qc/columns.py` reports at least 1 (paired with `grep -c "^from qc" qc/columns.py` reporting 0), intended to prove the module uses relative sibling imports rather than a package round-trip through `qc/__init__.py` (Pitfall 5).

As implemented, `qc/columns.py` contains **zero** `from .` import lines — `grep -c "from \." qc/columns.py` reports 0, not "at least 1". This is not an oversight: the plan's own `<behavior>` and `must_haves.truths` sections state, in the same document, that normalisation is "purely typographic ... No semantic aliasing, and no name is inferred from another name (D-08)" and that `normalize_columns` "performs no canonical-set lookup and no aliasing" — meaning neither function has any legitimate reason to import `qc.domain`'s `MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS`, `qc.predicates`' `pct`, or anything from `qc.results`. 02-PATTERNS.md's own "Core pattern" code block for this exact file (the literal snippet the plan cites as the shape to lift) likewise contains only `import re` and zero relative imports — the "Imports pattern" block shown just above it in the same document (mirroring `qc/schema.py`'s `from .domain import ...` / `from .predicates import ...` / `from .results import register`) is presented as a general style convention, not as code this specific module actually exercises, since none of those three names are referenced anywhere in the accompanying implementation.

Adding an import purely to satisfy this grep count — e.g. `from .domain import MLOS_REQUIRED_COLS` without ever using it — would be a dead import: strictly worse code quality than the honest zero, and arguably a violation of the module's own explicit "no canonical-set lookup" requirement in spirit (an unused import of the canonical set list is exactly the kind of accidental coupling D-08 warns against). Following this project's own precedent for exactly this situation (02-01-SUMMARY.md's and 02-02-SUMMARY.md's "Acceptance-Criterion Discrepancy (documented, not auto-fixed)" sections), this is documented here rather than forced.

Every other acceptance criterion for both tasks passes as written, including the paired `grep -c "^from qc" qc/columns.py` reporting 0 (still true — there is no package-round-trip import to avoid, because there is no import at all).

---

**Total deviations:** 0 auto-fixed. 1 documented acceptance-criterion discrepancy (assumes a relative sibling import this module has no legitimate reason to contain, given D-08/D-09's explicit no-aliasing/no-canonical-lookup requirements for the same two functions).
**Impact on plan:** None on correctness — `qc/columns.py` fully implements `normalize_name`/`normalize_columns` per every behavioural truth in the plan, every `<verify>` command passes, and every other acceptance criterion (API surface, no-Streamlit, idempotence/duplicate-detection test discoverability, frozen-file untouched) passes as written.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 (the app.py load-path wiring for column normalisation, populating `session_state["column_collisions"]` and the on-screen/"Columns Renamed" sheet reporting per D-11) can build directly on `qc.columns.normalize_columns` and `qc.schema.run_schema_qc`'s `collisions` parameter without re-deriving either.
- The `run_schema_qc` call site in `app.py` already reads `column_collisions` with a safe empty-tuple default, so plan 04 only needs to *populate* that session-state key at load — no further call-site change required at this layer.
- No blockers. Full suite: 87 passed, 0 failed; frozen baseline trio and `tests/test_extraction_parity.py` untouched.

## Self-Check: PASSED

All 5 key files found on disk; both task commits (`2c10d8a`, `f954681`) found in git log.

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*
