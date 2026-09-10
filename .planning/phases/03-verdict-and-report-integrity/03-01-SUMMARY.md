---
phase: 03-verdict-and-report-integrity
plan: 01
subsystem: qc-engine
tags: [verdict, weighted-score, distinct-row-counting, dataclass, pandas, streamlit-free]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "B4/B5 registered in qc/boundary.py; app.py's mlos_raw/mlos_corrected two-frame
      session-state cache branch keyed by a sha256 of the uploaded bytes"
provides:
  - "qc/report.py: LayerSummary/QcSummary dataclasses and build_summary(), the single shared
    verdict/score/count computation every presentation site in app.py now reads"
  - "qc.get_rule(id) registry accessor"
  - "Index-preserving detail frames in qc/takeoff.py and qc/boundary.py (D-11), enabling
    distinct-row counting"
affects: [03-02-report-workbook, 03-03-email-summary, 03-04-verdict-agreement-and-order]

actuals:
  tokens: 12222
  tasks: 3
  commits: 7
  plan_head_before: de4d4c67d71b40dda8aba75ccff548a29f1cf5a4

tech-stack:
  added: []
  patterns:
    - "One shared computation, many readers: QcSummary/LayerSummary built exactly once outside
      the session-state cache if/else, every on-screen site reads it instead of deriving its
      own verdict/score/count (closes F1's structural root cause)"
    - "Two separate properties for 'did not run': pass_rate is None, weighted_contribution is
      always a float 0.0 -- never collapsed into one value (closes F6)"
    - "Row identity for distinct counting is the detail frame's own preserved index, never an
      id column or a post-merge derivative (D-11)"

key-files:
  created:
    - qc/report.py
    - tests/test_layer_pass_rate.py
    - tests/test_distinct_row_counting.py
    - tests/test_verdict_sentence.py
  modified:
    - qc/results.py
    - qc/__init__.py
    - qc/takeoff.py
    - qc/boundary.py
    - app.py

key-decisions:
  - "Task 1's RED phase created qc/report.py as a docstring-only stub (no LAYER_ORDER, no
    classes) so the test file's import succeeds and every test fails on a genuine AttributeError
    inside its own test function, never a collection-time ImportError -- required for
    gsd-tools check tdd-red-evidence's INVALID_RED guard (#3770) to certify RED_EVIDENCE_OK on a
    brand-new module."
  - "Followed D-01's explicit worked example (\"a perfect four-layer file scores 80.0%\") over
    two literal acceptance-criteria strings that claimed \"100.0% of 80.0% achievable\" for that
    same scenario -- see Deviations."

requirements-completed: [VERDICT-04, VERDICT-05]

coverage:
  - id: D1
    description: "LayerSummary/QcSummary/build_summary compute the weighted score, achievable
      maximum, score display and colour band from one dict-keyed input; a layer that ran zero
      checks earns pass_rate None and weighted_contribution 0.0 (never F6's full-credit 1.0)"
    requirement: "VERDICT-05"
    verification:
      - kind: unit
        ref: "tests/test_layer_pass_rate.py (12 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "qc.get_rule(id) registry accessor, fail-loud on an unregistered id"
    verification:
      - kind: unit
        ref: "tests/test_layer_pass_rate.py::test_get_rule_returns_the_registered_boundary_rule, ::test_get_rule_raises_for_an_unregistered_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "qc/takeoff.py and qc/boundary.py detail frames preserve the source row's own
      position (D-11); qc/schema.py is unchanged"
    requirement: "VERDICT-04"
    verification:
      - kind: unit
        ref: "tests/test_distinct_row_counting.py::test_takeoff_detail_index_is_a_subset_of_the_input_frame, ::test_boundary_detail_index_is_a_subset_of_the_input_frame, ::test_mlos_and_settlement_detail_index_already_preserved_regression_guard"
        status: pass
      - kind: integration
        ref: "tests/test_extraction_parity.py, tests/test_golden_three_format_parity.py, tests/test_missing_cross_table.py (unmodified, still green)"
        status: pass
    human_judgment: false
  - id: D4
    description: "LayerSummary.distinct_issue_rows/findings/issue_line and QcSummary.headline_distinct/headline_findings/headline_issue_line -- the headline is the plain sum of the four non-Schema layers' distinct counts (D-10), with the findings count kept visible (D-12) and the per-layer share line (D-13)"
    requirement: "VERDICT-04"
    verification:
      - kind: unit
        ref: "tests/test_distinct_row_counting.py (9 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "QcSummary.verdict_text/verdict_short/gap_clause -- the two-state verdict with
      the unrun-layer gap named in the same position after both CLEAN and FAILING (D-04, amended
      2026-09-10)"
    requirement: "VERDICT-05"
    verification:
      - kind: unit
        ref: "tests/test_verdict_sentence.py (8 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "app.py's metric bar, verdict banner, Tab 2 score panel/breakdown table, Tabs
      3-6 issue headers, Tab 8's verdict block/metadata card/warning and the send_qc_email call
      all read the one summary object -- no site recomputes a failing count, pass rate, weighted
      score or row count"
    verification:
      - kind: unit
        ref: "AST checks: single qc.report.build_summary(...) call outside the cache if/else and outside any If body; no module-level _layer_pass_rate/LAYER_WEIGHTS/len(<layer>_detail) survive; summary.verdict_text read at 7 sites; qc/__init__.py does not import qc.report"
        status: pass
    human_judgment: true
    rationale: "app.py cannot be imported or executed outside a live Streamlit runtime (the
      established convention in this codebase, see tests/test_one_snapshot_guard.py's
      docstring), so the actual on-screen rendering of the metric bar, banner and score table is
      proven here only by static AST structural checks, not by literally running the dashboard.
      A human should visually confirm against a real upload before this phase ships."

duration: 55min
completed: 2026-09-10
status: complete
---

# Phase 3 Plan 1: Shared Verdict, Score and Distinct-Row Computation Summary

**`qc/report.py`'s `QcSummary`/`LayerSummary` dataclasses replace four independent app.py
derivations of the verdict, weighted score and issue-row counts with one computation every
on-screen site reads — closing F6 (a withheld layer earning full credit) and F8 (issue-row
totals counting rule-row pairs instead of distinct rows).**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-10T18:11:00Z
- **Completed:** 2026-09-10T19:06:17Z
- **Tasks:** 3 (all `tdd="true"`, task 1 `type="tracer"`)
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- `qc/report.py`: `LayerSummary`/`QcSummary` `@dataclass(frozen=True)` pair and
  `build_summary(filename, layer_results, mlos_row_count, takeoff_row_count)`. A layer with an
  empty checks list reports `pass_rate is None` and `weighted_contribution == 0.0` (a float,
  never `None`) — the F6 fix. `achievable_max` sums only the layers that ran, never renormalised
  (D-01); `score_band` is driven by the capped score out of 100, never by the score relative to
  the achievable maximum (D-03).
- `qc.get_rule(id)` registry accessor added to `qc/results.py`, re-exported from `qc/__init__.py`
  alongside `canonical_order`.
- `qc/takeoff.py` and `qc/boundary.py` no longer pass `ignore_index=True` to their detail-frame
  `pd.concat`, so both layers' detail frames carry the source row's own position through to the
  counting site (D-11) — matching `qc/mlos.py` and `qc/settlement.py`, which already did.
  `qc/schema.py` is unchanged (its detail rows name missing columns, not source rows).
- `LayerSummary.distinct_issue_rows`/`findings`/`issue_line` and
  `QcSummary.headline_distinct`/`headline_findings`/`headline_issue_line` (D-10 to D-13): the
  headline Issue Rows figure is the plain sum of the four non-Schema layers' distinct counts, the
  rule-row-pair count stays visible as "findings", and each layer's line reads e.g. `312 issue
  rows (6.2% of 5,000) across 1,040 findings`.
- `QcSummary.verdict_text`/`verdict_short`/`gap_clause` (D-04, amended 2026-09-10): the verdict
  stays two-state, with the unrun-layer gap named in the same clause and position after both
  `CLEAN` and `FAILING (n check(s))`.
- `app.py` builds `summary = qc.report.build_summary(...)` exactly once, immediately after the
  session-state cache `if`/`else` resolves both arms — never inside either arm. Every
  presentation site (metric bar, verdict banner, Tab 2's score panel and breakdown table, Tabs
  3-6's issue headers, Tab 8's verdict block/metadata card/warning, the `send_qc_email` call)
  reads `summary` instead of a locally re-derived value. The old `LAYER_WEIGHTS` dict,
  `_layer_pass_rate()` helper, and every `len(<layer>_detail)`/`"FAIL" in c["Status"]`-summing
  local at those sites are gone.

## Task Commits

Each task followed the RED → GREEN cycle (task 1 additionally ran the tracer feedback gate
before task 2's expansion — both automated `<verify>` re-runs passed, no checkpoint needed per
`workflow.human_verify_mode: end-of-phase`):

1. **Task 1: End-to-end weighted score** —
   `8db4b39` test, `1538e54` feat
2. **Task 2: Distinct rows, findings and shares** —
   `fd03bbe` test, `a0bf86c` feat
3. **Task 3: The verdict sentence** —
   `40eef7d` test, `7e22b24` feat
4. **Follow-up consistency fix** (Rule 2 — plan-level success criterion "no site computes its
   own failing count") — `31dc229` fix

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

No `refactor(03-01):` commits — no REFACTOR phase was needed for any of the three tasks.

## Files Created/Modified

- `qc/report.py` — new: `LAYER_ORDER`, `LAYER_WEIGHTS`, `NOT_RUN_REASON`, `LayerSummary`,
  `QcSummary`, `build_summary`
- `qc/results.py` — `get_rule(id)` added
- `qc/__init__.py` — re-exports `get_rule`
- `qc/takeoff.py`, `qc/boundary.py` — drop `ignore_index=True` from the detail-frame concat
- `app.py` — `import qc.report`; single `build_summary` call site; every presentation site wired
  to `summary`; dead locals removed
- `tests/test_layer_pass_rate.py`, `tests/test_distinct_row_counting.py`,
  `tests/test_verdict_sentence.py` — new, 29 tests total

## Decisions Made

- **RED-phase stub module.** For a brand-new module with no prior behaviour, `gsd-tools check
  tdd-red-evidence`'s `#3770` guard classifies a plain `ModuleNotFoundError`/collection failure
  as `INVALID_RED` (`zero_tests_discovered`), not a valid RED. Created `qc/report.py` as a
  docstring-only file in the RED commit so `import qc.report` succeeds and every test instead
  fails on a real `AttributeError` for the missing symbol it exercises — genuine `RED_EVIDENCE_OK`
  verdicts for all three tasks (confirmed via the tool, not asserted).
- **Followed D-01's own worked example over two literal acceptance-criteria strings.** See
  Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — missing critical] Remaining per-layer failing-count locals still self-derived**
- **Found during:** Task 3 final consistency pass
- **Issue:** After Task 3's GREEN commit, `app.py`'s Tab 8 metadata card and the Tabs 3-6 issue
  headers still computed `sum(1 for c in <layer>_checks if "FAIL" in c["Status"])` locally —
  the exact number `LayerSummary.n_fail`/`n_pass` already expose. This violates the plan's own
  plan-level success criterion ("No on-screen site computes its own failing count, pass rate,
  weighted score or row count").
- **Fix:** Replaced every remaining local sum with the matching `summary.layers[...].n_fail` /
  `.n_pass` / `.checks`. No rendered value changed.
- **Files modified:** `app.py`
- **Verification:** Full suite green (137 tests); AST checks re-run clean
- **Commit:** `31dc229`

**2. [Rule 3 — blocking] Test authoring bug: unregistered synthetic Rule# ids**
- **Found during:** Task 3 GREEN verification
- **Issue:** `tests/test_verdict_sentence.py`'s 12-failing-checks test used synthetic ids
  `"0".."11"`, which `sort_by_registry`'s `order_index[c["Rule#"]]` lookup raises `KeyError` on
  (they were never registered) — an unrelated failure mode, not the `AttributeError` the RED
  phase was written to prove.
- **Fix:** Replaced the synthetic ids with 12 real MLoS-registered identifiers
  (`"1", "2", "2.missing", ...`). The RED evidence already certified (genuine `AttributeError`
  failures on the target properties) was unaffected by this fixture-data correction.
- **Files modified:** `tests/test_verdict_sentence.py`
- **Verification:** All 8 tests pass after the production code lands
- **Committed in:** `7e22b24` (bundled with the GREEN commit; documented in that commit message)

---

**Total deviations:** 2 auto-fixed (1 missing-critical, 1 blocking test-authoring bug).
**Impact on plan:** Both fixes are necessary for correctness; neither expands scope beyond the
plan's own stated intent (the success criterion the first fix satisfies is the plan's own).

### Not Fixed — Documented Discrepancy (plan text vs. locked decision)

**The plan's Task 1 acceptance criteria and the plan-level `<success_criteria>` both state:**
*"A four-layer run (Takeoffpoint empty, all else passing) renders `score_display` exactly
`100.0% of 80.0% achievable`"* — this is inconsistent with D-01's own explicit worked example:
*"the overall score is the plain sum of the layers that ran, so **a perfect four-layer file
scores 80.0%**."* It is also inconsistent with the plan's own `must_haves` truth statement and
CONTEXT.md's approved literal example, both of which use `72.0% of 80.0% achievable` for a
comparable (partial-fail) four-layer scenario — never `100.0%`.

Verified directly: a fully-passing four-layer run (Schema/MLoS/Settlement/Boundary all passing,
Takeoffpoint empty) renders `score_display == "80.0% of 80.0% achievable"` under this
implementation — matching D-01's worked example precisely. Rendering `100.0%` instead would
require renormalising the weighted score to the achievable maximum, which D-01 explicitly
records as offered and **rejected** ("flagged as reopening F6, and not chosen"). Changing the
implementation to satisfy the literal `100.0%` string would reopen F6 — the exact defect
VERDICT-05 exists to close — so the implementation follows D-01, the `must_haves`, and
CONTEXT.md's specifics instead of the two `100.0%` occurrences, which I read as a drafting
error carried from an earlier (rejected) renormalisation draft. Flagging for confirmation rather
than silently resolving, per the plan's own "surfaced, not silently resolved" convention for
flagged assumptions.

Task 1's actual acceptance criteria that exercise this shape (the `72.0`/`80.0` scenario, the
`n/a`/`0.0%`/`amber`-at-72.0 assertions) all pass as written and are covered by
`tests/test_layer_pass_rate.py`.

## Issues Encountered

None beyond the two auto-fixed deviations and the one documented discrepancy above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `qc/report.py`'s `QcSummary`/`LayerSummary` and `build_summary` are the seam plans 02
  (report workbook), 03 (email) and 04 (verdict-agreement/order tests) are written to read
  rather than recompute.
- **Flag for the phase verifier / next plan author:** confirm whether the `100.0% of 80.0%
  achievable` strings in 03-01-PLAN.md's Task 1 acceptance criteria and the plan-level success
  criteria should be corrected to `80.0%` (matching D-01's own worked example), since plans 02-04
  may cite the same scenario.
- `app.py` remains CRLF-terminated (verified after every edit in this plan); all touched
  `qc/*.py` and `tests/*.py` files remain LF.

---
*Phase: 03-verdict-and-report-integrity*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All created files found on disk: `qc/report.py`, `tests/test_layer_pass_rate.py`,
  `tests/test_distinct_row_counting.py`, `tests/test_verdict_sentence.py`, this SUMMARY.
- All 7 task/fix commits found in git history: `8db4b39`, `1538e54`, `fd03bbe`, `a0bf86c`,
  `40eef7d`, `7e22b24`, `31dc229`.
- Full suite green: `python3 -m pytest tests/ -q` — 137 passed (108 baseline + 29 new).
- `python3 -m compileall -q qc app.py tests` — clean.
- `app.py` confirmed still CRLF-terminated; all touched `qc/*.py`/`tests/*.py` files LF.
- Plan-level `<verification>` block re-run: full suite, compileall, streamlit-boundary test,
  and the AST one-summary-call/no-If-nesting check all pass.
