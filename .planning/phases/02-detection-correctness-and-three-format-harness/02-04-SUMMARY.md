---
phase: 02-detection-correctness-and-three-format-harness
plan: 04
subsystem: qc-engine
tags: [pandas, column-normalisation, streamlit, excel-report, integ-03, f7]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "qc.columns.normalize_columns and run_schema_qc's S3 collision check (plan 03), which nothing called from a real load path until this plan"
provides:
  - "qc.columns.normalize_columns invoked at all three officer-supplied load paths: the MLoS frame and same-upload Takeoffpoint frame inside get_uploaded_data's caching wrapper, and the separately uploaded Takeoffpoint override"
  - "st.session_state['column_renames'] / ['column_collisions'] — one rename map and one collision list per run, merged (not replaced) across all three load sites, read back unchanged on a cache hit"
  - "An on-screen 'Columns renamed at load' expander in Tab 1 (Auto Correct), rendered only when a rename occurred, with a caption that a rename carries no Pass/Fail and no score effect, plus a pointer to S3 when a collision also occurred"
  - "A conditional 'Columns Renamed' worksheet in the downloaded QC report via a new build_excel_report(..., column_renames=None) keyword parameter, styled like the other summary sheets, present only when a rename occurred"
  - "tests/test_normalisation_at_load.py — the F7 before/after contrast, a three-format (.sqlite/.csv/.xlsx) column-set equality test, a collision-propagation-to-S3 test, and a defensive floor asserting the non-canonical fixture genuinely differs from the canonical one"
  - "tests/golden_fixture.py — a non-canonical-header variant builder plus per-format writers reusing the existing three writers, alongside the unmodified canonical builder"
affects: [02-05, 02-06, 03-verdict-and-report-integrity]

actuals:
  tokens: 6194
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One helper, three call sites: qc.columns.normalize_columns is invoked identically at the cache-miss wrapper path (MLoS + same-upload Takeoffpoint), and again at the separately-uploaded Takeoffpoint override — merging rename maps and collision lists into the same two session-state keys rather than replacing them, so no path can silently diverge from another (the exact shape F7 was)."
    - "Read-then-write-under-one-key session-state convention, already used for the cached frames themselves, extended unchanged to column_renames/column_collisions: a cache hit reads the same two keys back instead of recomputing, so a rerun without a re-parse still renders the panel and still feeds S3."
    - "Collision groups tagged with their source table ('MLoS' / 'Takeoffpoint') at the point of merge, so S3's description can name which table a collision came from without a second lookup."
    - "Rename/collision reporting is structurally excluded from scoring: the on-screen panel and the report sheet both read the same session-state rename map (no independently recomputed second list), and an AST-level acceptance check asserts 'rename' and 'column_renames' never appear in the all_checks assignment or near LAYER_WEIGHTS."

key-files:
  created:
    - tests/test_normalisation_at_load.py
  modified:
    - app.py
    - tests/golden_fixture.py

key-decisions:
  - "Collision groups are tagged with their source table ('MLoS' or 'Takeoffpoint') when merged into st.session_state['column_collisions'], reusing plan 03's per-group dict shape rather than inventing a second shape — S3's description can name the table without a separate lookup."
  - "The separately-uploaded Takeoffpoint override (which runs after get_uploaded_data, outside the caching wrapper) merges its rename/collision entries into the existing session-state keys via dict/list concatenation rather than overwriting them, since its headers are exactly as officer-supplied as the wrapper's two frames and dropping the wrapper's entries would silently lose the earlier renames from the panel and the report."
  - "The collision-pointer caption ('see S3') was added as a third line inside the same expander, not a third report location — it carries no rename detail, no status, and no count, existing only to tell the officer where a collision is scored, per the plan's own 'Claude's Discretion' framing for exactly this addition."
  - "build_excel_report's new column_renames parameter defaults to None (not an empty dict) so existing callers passing no argument at all still work, and the conditional sheet is skipped for both None and an empty mapping."

patterns-established:
  - "Pattern: officer-supplied-header load paths are normalised, repo-controlled reference data is not — normalize_columns is called on every path an officer's file reaches, and deliberately not on the two bundled ward-boundary CSVs, which stay covered instead by a structural AST assertion that load_boundary_refs never calls it."

requirements-completed: [INTEG-03]

coverage:
  - id: D1
    description: "Column names are normalised exactly once, at load, by qc.columns.normalize_columns, on the MLoS frame, the same-upload Takeoffpoint frame, and the separately uploaded Takeoffpoint file — not on the two bundled boundary reference CSVs — so the schema check and every rule's column-presence guard resolve the same names (INTEG-03, D-08)."
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_normalisation_at_load.py#test_three_format_column_sets_match_and_cover_all_43_canonical_names (name approximate; selected via -k)"
        status: pass
      - kind: unit
        ref: "tests/test_normalisation_at_load.py -k f7 (F7 contrast, both halves)"
        status: pass
      - kind: other
        ref: "grep -v '^ *#' app.py | grep -c qc.columns.normalize_columns  ->  3"
        status: pass
      - kind: other
        ref: "python3 -c AST check confirming load_boundary_refs never calls normalize_columns  ->  'boundary refs left alone'"
        status: pass
    human_judgment: false
  - id: D2
    description: "A header spelled non-canonically (e.g. Takeoffpoint, Ward Code, SET_POPULATION) no longer satisfies S1 while silently skipping every rule that needs that column; after normalisation the corresponding rule identifiers emit where before they did not (INTEG-03, defect F7)."
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "tests/test_normalisation_at_load.py -k f7"
        status: pass
      - kind: integration
        ref: "tests/test_column_collision.py, tests/test_golden_three_format_parity.py (unaffected, still green)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Renames are shown to the officer in exactly two places — an on-screen expander near the auto-correct summary listing only changed headers, and a Columns Renamed sheet in the downloadable QC report — with no Pass/Fail and no score weight, and a clean/canonical submission shows neither (D-11)."
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "python3 -c AST check: 'rename'/'column_renames' absent from the all_checks assignment  ->  'score untouched'"
        status: pass
      - kind: unit
        ref: "python3 -c regex check: conditional st.session_state.get('column_renames') guard present  ->  'panel guarded'"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 live-session checkpoint, four per-check verdicts (see Task 3 Verification below)"
        status: pass
    human_judgment: true
    rationale: "app.py cannot be imported outside a Streamlit runtime and the Excel workbook's rendered sheet list is not observable from a unit test; the panel's actual on-screen appearance and the report's actual sheet presence/absence/order were confirmed once in a live streamlit run per 02-VALIDATION.md's Manual-Only Verifications table, not re-derivable from an automated re-run."
  - id: D4
    description: "The weighted QC score is unaffected by a column rename — a rename never enters all_checks or LAYER_WEIGHTS."
    requirement: "INTEG-03"
    verification:
      - kind: unit
        ref: "python3 -c AST check on the all_checks assignment and LAYER_WEIGHTS block presence  ->  'score untouched' / 'LAYER_WEIGHTS block unchanged: True'"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 checkpoint Check 4 (weighted score unchanged by the rename)"
        status: pass
    human_judgment: true
    rationale: "The AST checks prove the rename record never enters the scoring assembly by construction; confirming the *displayed number* is unchanged for a real upload still required one live comparison, recorded in Task 3's checkpoint."

duration: 3h 37m (2 min of task execution across two commits at 14:24-14:27 WAT; remainder was the Task 3 checkpoint wait and this close-out session)
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 4: Normalise Column Names Once at Load, and Report Renames to the Officer Summary

**Column normalisation now runs once, at load, on every officer-supplied header path — closing F7 — and the officer sees exactly which headers changed, on screen and in the downloaded report, with zero effect on Pass/Fail or the weighted score.**

## Performance

- **Duration:** 3h 37m wall-clock across the resumed session; the two production-code task commits landed 2 minutes apart (14:24:55 -> 14:26:54 WAT); the remainder of the elapsed time was the Task 3 human-verification checkpoint plus this close-out.
- **Started:** 2026-09-10T13:24:47Z (first task commit)
- **Completed:** 2026-09-10T17:01:40Z (this close-out)
- **Tasks:** 3 (2 code tasks + 1 checkpoint, all complete)
- **Files modified:** 3 (`app.py`, `tests/golden_fixture.py`, `tests/test_normalisation_at_load.py` created)

## Accomplishments

- `qc.columns.normalize_columns` is now called on all three officer-supplied load paths — the MLoS frame, the same-upload Takeoffpoint frame (both inside `get_uploaded_data`'s caching wrapper), and the separately uploaded Takeoffpoint file — closing the gap plan 03 left open (the helper existed, nothing called it).
- The F7 defect is proven fixed by a committed contrast test: a frame with `Takeoffpoint`/`Ward Code`/`SET_POPULATION` spelled non-canonically now resolves those columns to their rules after normalisation, where before normalisation the rules were silently skipped and `S1` reported clean regardless.
- `st.session_state['column_renames']` and `['column_collisions']` are populated once per run, merged (not overwritten) across all three load sites, and survive a cache hit by being read back rather than recomputed.
- The officer sees renames in exactly two places: a collapsed "Columns renamed at load" expander in Tab 1, and a conditional "Columns Renamed" worksheet in the downloaded report — both absent entirely for a canonical-header submission, and neither carrying a Pass/Fail status or score weight.
- Live-session verification (Task 3) confirmed all four required behaviors: the panel lists exactly the changed headers, a clean file shows no panel, the report sheet matches the panel and is absent for the clean file, and the weighted score is unaffected by the rename.

## Task Commits

Each task was committed atomically:

1. **Task 1: Normalise once at load on all three officer-supplied paths** - `b6d1251` (test), `ccf3d76` (feat)
2. **Task 2: Report the renames to the officer, on screen and in the downloaded report** - `469669e` (feat)
3. **Task 3: Verify the rename panel and the report sheet in a live session** - checkpoint only, no code commit (verified via live `streamlit run app.py` session; see Task 3 Verification below)

**Plan metadata:** commit created by this close-out step (see completion report for hash)

_Note: Task 1 was TDD (`tdd="true"`); its RED evidence is `b6d1251` (test-only commit adding the non-canonical golden fixture builders and the F7 contrast suite) followed by the GREEN wiring in `ccf3d76`._

## Files Created/Modified

- `app.py` — `get_uploaded_data` now calls `qc.columns.normalize_columns` on both frames it produces and writes/reads `column_renames`/`column_collisions` in session state; the Takeoffpoint override applies the same helper and merges into the same two keys; Tab 1 gains a conditional rename expander; `build_excel_report` gains a `column_renames` keyword parameter and a conditional "Columns Renamed" sheet; the download caption now describes that sheet as conditional.
- `tests/golden_fixture.py` — new non-canonical-header variant builder and per-format writers reusing the three existing writers; the canonical builder and its writers are unchanged.
- `tests/test_normalisation_at_load.py` — new: the F7 before/after contrast (two labelled halves), the three-format column-set equality test, the collision-propagation-to-`S3` test, and the non-canonical-vs-canonical header-set difference floor.

## Decisions Made

- Collision groups are tagged with their source table (`MLoS` / `Takeoffpoint`) at merge time, reusing plan 03's per-group dict shape rather than a new one, so `S3`'s description can name the table without a second lookup.
- The separately-uploaded Takeoffpoint override merges into the existing `column_renames`/`column_collisions` session-state entries (dict/list concatenation) instead of overwriting them, because it runs after the wrapper and its headers are just as officer-supplied as the wrapper's two frames.
- The `S3` collision-pointer caption is a third *line* inside the rename expander, not a third *report* — it carries no status, count, or collision detail, and exists only to route the officer to `S3`, matching the plan's own "Claude's Discretion" framing for this exact addition.
- `build_excel_report`'s new `column_renames` parameter defaults to `None` rather than an empty dict, so pre-existing callers that omit the argument entirely keep working, and both `None` and an empty mapping suppress the sheet.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria for Tasks 1 and 2 were re-verified against the current tree during this close-out and hold unchanged; no fix-forward was required.

## Issues Encountered

None during this close-out. One process note: several unrelated Phase 3 planning commits (`06d0f52` through `0012111`) landed on this branch between Task 2's commit (`469669e`) and this close-out session, because Phase 3 discussion/planning proceeded before this plan's Task 3 checkpoint was resolved. This does not affect Plan 02-04's own commits or verification — `actuals.commits` above is measured against the last Plan 02-04 task commit (`469669e`), not against `HEAD` at SUMMARY-write time, specifically to avoid attributing those unrelated commits to this plan's cost.

## Task 3 Verification (Checkpoint, `gate="blocking-human"`)

Live session at `http://localhost:8501` (`python3 -m streamlit run app.py`), using two `.xlsx` files built from `tests/fixtures.py` builders: one with the two non-canonical headers `Ward Code` and `SET_POPULATION`, one with all 43 canonical headers.

| Check | Verdict | Observed |
|---|---|---|
| 1 — panel lists exactly the two changed headers | pass | Panel showed 2 rows: `Ward Code` -> `ward_code`, `SET_POPULATION` -> `set_population` |
| 2 — canonical-header file shows no panel at all | pass | No panel rendered for the clean file |
| 3 — Columns Renamed sheet present, matching, absent for the clean file | pass | Sheet showed the same 2 rows in the same order for the renamed file; sheet absent for the clean file |
| 4 — weighted score unchanged by the rename | pass | Score identical between the renamed and canonical-header files |

All four verdicts read `pass`. Per the task's acceptance criteria, the observed row counts (2 for both check 1 and check 3) are recorded above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- INTEG-03 is closed: normalisation runs once at every officer-supplied load path, F7 is proven fixed by a committed contrast test, and renames are reported to the officer in exactly the two places D-11 specifies.
- The full suite stands at 91 passed (plan required >= 57), with `tests/test_normalisation_at_load.py` green (4 passed) and no regressions in `tests/test_golden_three_format_parity.py` or `tests/test_column_collision.py` (24 passed together).
- Phase 2's wave 4 is complete; wave 5 (02-05) is next per ROADMAP.md.
- No blockers introduced by this plan.

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: app.py
- FOUND: tests/golden_fixture.py
- FOUND: tests/test_normalisation_at_load.py
- FOUND: b6d1251 (test commit)
- FOUND: ccf3d76 (feat commit)
- FOUND: 469669e (feat commit)
