---
phase: 03-verdict-and-report-integrity
plan: 02
subsystem: reporting
tags: [openpyxl, workbook, verdict, report, streamlit-free]

requires:
  - phase: 03-verdict-and-report-integrity
    provides: "qc/report.py's QcSummary/LayerSummary dataclasses and build_summary() (plan 01) --
      the single shared verdict/score/count computation this plan's workbook reads instead of
      recomputing"
provides:
  - "qc.report.build_workbook(summary, mlos_raw, takeoff_df, column_renames=None) -> bytes --
    the relocated, Streamlit-free report workbook builder, importable and unit-testable without
    a Streamlit runtime"
  - "qc.report.summary_rows(summary) -> list[dict] -- the combined QC Summary sheet's row
    builder, Layer column sourced from qc.results.get_rule, canonical order, D-07 placeholder
    rows for unrun layers"
  - "qc.report.SHEET_NAMES -- the unconditional nine-sheet order (D-06)"
affects: [03-03-email-summary, 03-04-verdict-agreement-and-order]

actuals:
  tokens: 12271
  tasks: 3
  commits: 6
  plan_head_before: 0b93897ed348422f49eed30654ffc6d57d629990

tech-stack:
  added: []
  patterns:
    - "Relocated business logic out of app.py into a Streamlit-free qc/ module (same precedent
      Phase 1 D-06/D-08 established), so tests/test_no_streamlit_in_qc.py's existing AST scan
      covers the report builder for free with zero additional guard code"
    - "The cover, the combined summary sheet and every detail/raw sheet all read the same
      QcSummary object built in plan 01 -- no second derivation of a verdict, a failing count
      or a Layer lookup anywhere in the workbook builder (closes F1's structural root cause on
      the one site that still had it)"
    - "Plain bulk ws.append(row.tolist()) for body rows on sheets that grow with the
      submission (raw + detail); the cover and combined summary sheet, both bounded in size,
      keep full per-cell styling"

key-files:
  created:
    - tests/test_report_workbook_shape.py
    - tests/test_no_per_cell_styling.py
  modified:
    - qc/report.py
    - app.py
    - tests/test_one_snapshot_guard.py

key-decisions:
  - "Cover verdict cell holds summary.verdict_text verbatim, with no tick/cross glyph prefix --
    diverges from the plan's <action> prose (\"prefixed by the existing tick or cross glyph\")
    but matches the plan's own <behavior>/<acceptance_criteria>, which assert the cell's value
    starts with the bare string 'FAILING (' and equals the bare CLEAN-with-gap sentence
    exactly, with no emoji anywhere in either literal. Followed the literal, machine-checked
    spec over the descriptive prose -- see Deviations."
  - "Placeholder row's Status and Rule# columns use the em dash '—' (not literally specified by
    D-07, which only pins the three numeric columns to the string 'n/a') as the 'not
    applicable' marker, consistent with the n/a convention D-07 does specify."
  - "Schema's detail sheet is titled 'Schema Table — Missing Columns' rather than reusing the
    other four layers' '...Detailed Issue Rows' wording, since Schema's rows are missing
    columns, not source rows -- the same distinction D-13 already draws for Schema having no
    distinct-row line."

requirements-completed: [VERDICT-01, VERDICT-02, ENGINE-08]

coverage:
  - id: D1
    description: "qc.report.build_workbook relocated from app.py's build_excel_report,
      Streamlit-free and importable without a runtime; the cover's verdict and score derive
      from the one shared QcSummary object instead of a two-layer failing-count sum -- a
      submission failing only its Boundary checks now downloads with a FAILING cover (closes
      F1/VERDICT-02, the case that filed a false CLEAN today)"
    requirement: "VERDICT-02"
    verification:
      - kind: unit
        ref: "tests/test_report_workbook_shape.py (task 1 section, 6 tests)"
        status: pass
      - kind: unit
        ref: "tests/test_no_streamlit_in_qc.py (4 tests, re-run after qc.report gained an
          openpyxl import)"
        status: pass
    human_judgment: false
  - id: D2
    description: "One combined QC Summary sheet (Layer column sourced from the rule registry,
      canonical order, one placeholder row per unrun layer in canonical position with the
      literal string n/a in its three numeric columns) plus one detail sheet per layer,
      never merged across layers; the sheet set is identical for a clean and a failing
      submission (D-06/D-07/VERDICT-01)"
    requirement: "VERDICT-01"
    verification:
      - kind: unit
        ref: "tests/test_report_workbook_shape.py (task 2 section, 13 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Raw and detail sheet body rows carry no per-cell styling after a
      save/reload round trip (both directions asserted: header styled, first AND last body
      row plain); the cover and combined summary sheet keep their styling; no row is dropped
      by the change (ENGINE-08/D-09)"
    requirement: "ENGINE-08"
    verification:
      - kind: unit
        ref: "tests/test_no_per_cell_styling.py (4 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "app.py's single call site rewired to qc.report.build_workbook(summary, ...);
      the old build_excel_report deleted along with its now-unused openpyxl/Border/Side
      imports; the download caption lists the new nine sheet names and drops the old
      per-layer summary sheet names"
    verification:
      - kind: unit
        ref: "python3 -c 'import ast; ...' AST relocation check (plan <verify>); caption
          assertions in tests/test_report_workbook_shape.py"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-10
status: complete
---

# Phase 3 Plan 2: Report Workbook Coverage and Verdict Integrity Summary

**The downloaded QC report now covers all five layers in one combined `QC Summary` sheet plus
per-layer detail sheets, with its cover verdict and score read from the one shared `QcSummary`
object instead of a two-layer sum -- so a submission failing only its Boundary checks downloads
FAILING, not CLEAN.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-10T19:15:00Z
- **Completed:** 2026-09-10T20:00:00Z
- **Tasks:** 3 (all `tdd="true"`, task 1 `type="tracer"`)
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `qc.report.build_workbook(summary, mlos_raw, takeoff_df, column_renames=None)` relocated from
  `app.py`'s `build_excel_report`, Streamlit-free and importable without a runtime. The cover
  deletes its own two-layer failing-count sum and reads `summary.verdict_text` and
  `summary.score_display` instead (closes F1/VERDICT-02). The cover carries exactly five
  metadata rows (File, Generated At, MLoS Rows, Takeoffpoint Rows, Weighted Score) and no
  per-layer counts (D-08); the verdict row index is computed from the metadata block's own
  length, never hard-coded.
- `qc.report.SHEET_NAMES`: the D-06 unconditional nine-sheet order (Cover, QC Summary, one
  `{Layer} Issue Detail` per layer, two raw sheets). `Columns Renamed` is appended only when a
  rename occurred (Phase 2 D-11) -- the sheet set is otherwise identical for a clean and a
  failing submission.
- `qc.report.summary_rows(summary)`: one row per check that ran, `Layer` sourced from
  `qc.results.get_rule` (never a second hand-kept lookup), sorted via `sort_by_registry` inside
  the function. Raises `ValueError` naming the identifier and both layer names when a check's
  registry layer disagrees with the layer it arrived in. A layer that ran zero checks
  contributes exactly one placeholder row in canonical position, with the literal string `n/a`
  (not `None`) in its three numeric columns (D-07).
- `write_summary` rewritten for the combined sheet (eight columns starting with `Layer`;
  placeholder rows get the light-grey fill, neither pass nor fail). The four old
  summary/detail sheet-creation calls are replaced with one `QC Summary` sheet plus one detail
  sheet per layer, iterated over `LAYER_ORDER` -- detail frames are never concatenated across
  layers.
- `write_detail` and `write_raw`'s per-cell body loops replaced with a plain
  `ws.append(row.tolist())` per row -- no font, border, alignment or zebra fill on any body
  cell. The styled title row, styled header row and both helpers' column-width loops are
  unchanged; the cover and `QC Summary` sheet keep full styling (ENGINE-08/D-09).
- `app.py`'s single call site rewired to `qc.report.build_workbook(summary, mlos_raw,
  takeoff_df, column_renames=...)`; `build_excel_report` deleted along with its now-unused
  `import openpyxl` and `Border`/`Side` style imports; the download caption lists the new nine
  sheet names.

## Task Commits

Each task followed the RED → GREEN cycle (task 1 additionally ran the tracer feedback gate
before task 2's expansion -- all four automated `<verify>` commands re-ran clean, no checkpoint
needed per `workflow.human_verify_mode: end-of-phase`):

1. **Task 1: End-to-end report bytes with a five-layer cover verdict** --
   `198c575` test, `5c53ad6` feat
2. **Task 2: One combined summary sheet plus a detail sheet per layer** --
   `2d1fdcf` test, `9afdb59` feat
3. **Task 3: Plain-value body rows on the raw and detail sheets** --
   `93de018` test, `dd25b73` feat

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

No `refactor(03-02):` commits -- no REFACTOR phase was needed for any of the three tasks.

## Files Created/Modified

- `qc/report.py` -- `build_workbook`, `summary_rows`, `SHEET_NAMES`, `_DETAIL_TITLES` added;
  `write_summary`/`write_detail`/`write_raw` helpers relocated and reshaped
- `app.py` -- `build_excel_report` deleted; single call site rewired to
  `qc.report.build_workbook`; download caption updated; unused `openpyxl`/`Border`/`Side`
  imports removed
- `tests/test_report_workbook_shape.py` -- new, 19 tests (task 1: cover/verdict/score, 6; task
  2: sheet names/summary sheet/detail sheets/placeholder row, 13)
- `tests/test_no_per_cell_styling.py` -- new, 4 tests (header-styled/body-plain both
  directions, cover/summary keep styling, row counts unchanged, column widths kept)
- `tests/test_one_snapshot_guard.py` -- updated its `mlos_raw`-consumer guard to name the
  renamed call site (`build_workbook`, not `build_excel_report`) -- see Deviations

## Decisions Made

- Followed the plan's literal `<behavior>`/`<acceptance_criteria>` (exact-string and
  starts-with assertions with no emoji) over its `<action>` prose's glyph-prefix instruction
  for the cover verdict cell -- see Deviations for the full discrepancy and reasoning.
- Placeholder row's `Status`/`Rule#` use `—` (an em dash), matching the existing em-dash
  convention this codebase already uses for "not applicable" (Phase 2's `B4`/`B5` descriptions
  and Phase 1's registry docstring both use it), since D-07 only pins the three *numeric*
  columns to `n/a`.
- Schema's detail sheet title reads "Schema Table — Missing Columns" (its rows are missing
  columns, not source rows), distinct from the other four layers' "...Detailed Issue Rows"
  wording -- the plan's action text flagged this distinction without pinning exact wording.

## Deviations from Plan

### Not Fixed — Documented Discrepancy (plan text vs. its own tested behavior)

**Task 1's `<action>` text instructs:** *"Set the verdict cell's value to `summary.verdict_text`
prefixed by the existing tick or cross glyph chosen on `summary.n_fail`..."* This is
inconsistent with the same task's own `<behavior>` and `<acceptance_criteria>`, which assert:

- *"the cover sheet contains a cell whose value **starts with** `FAILING (`"* -- a glyph prefix
  (`"❌  FAILING (1 check)..."`) would NOT start with the bare string `FAILING (`; it would start
  with the glyph character.
- *"the cover contains a cell whose value is **exactly** `CLEAN — Takeoffpoint layer not
  checked (no Takeoffpoint data supplied)`"* -- an exact-equality assertion with no glyph
  anywhere in the literal, and this string is precisely `QcSummary.verdict_text`'s own output
  (verified directly against `qc/report.py`'s existing property from plan 01) with nothing
  prepended.

Both literal test assertions are satisfied only if the verdict cell holds `summary.verdict_text`
**verbatim, with no glyph prefix**. Implemented it that way: `vd.value = summary.verdict_text`.
The fill colour (green/red) still communicates pass/fail visually, matching the plan's own
instruction on that point ("its fill to the existing green or red on the same condition").

Followed the machine-checked, literal spec (`<behavior>`/`<acceptance_criteria>`) over the
descriptive `<action>` prose, per this phase's own established convention (03-01-SUMMARY.md
documented an analogous plan-text-vs-locked-decision discrepancy the same way: verified
directly, flagged for confirmation rather than silently resolved). All acceptance criteria for
task 1 pass as written under this reading; if a future plan or human review determines a glyph
prefix is actually wanted on the cover verdict cell, it is a one-line change to `build_workbook`
with no architectural impact.

**Total deviations:** 0 auto-fixed; 1 documented discrepancy (plan action-prose vs. the plan's
own tested behavior), resolved in favour of the literal, machine-checked spec.
**Impact on plan:** None on requirement closure -- VERDICT-02's actual defect (F1's two-layer
sum) is fixed either way; this discrepancy is purely about whether an emoji glyph precedes the
verdict text on the cover, which no requirement or CONTEXT.md decision specifies either way.

## Issues Encountered

- `gsd-tools check tdd-red-evidence`'s TAP-format parser (`# tests N` / `ok N - <name>` lines)
  does not match this project's `pytest -q` output shape, and no `pytest-tap` plugin is
  installed (nor pinned in `requirements-dev.txt`) to produce TAP output. Rather than add a new
  test-format dependency mid-plan (out of this plan's scope, and this phase's own research
  explicitly confirms "no new external packages" for Phase 3), each RED phase was verified
  manually against the same fail-fast criteria the tool encodes: the target test's own assertion
  failed with a genuine `AttributeError`/`KeyError`/`AssertionError` naming the missing
  production symbol or wrong behaviour -- never a collection-time import error, a zero-test
  discovery, or an unrelated failure. Full `pytest -q` output for each RED commit is captured in
  this session's tool-call history and summarized in each `test(03-02):` commit message.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- `qc.report.build_workbook`, `summary_rows` and `SHEET_NAMES` are the seam plan 03 (email
  body/subject) and plan 04 (verdict-agreement/order tests) can read without touching the
  workbook builder again.
- `app.py`'s Tab 8 three-column check breakdown (MLoS/Settlement/Takeoffpoint only) is
  unchanged by this plan -- 03-CONTEXT.md leaves its five-layer reshape to a later plan's
  discretion; not required by VERDICT-01/02/ENGINE-08.
- `app.py` confirmed still CRLF-terminated after every edit in this plan (0 LF-only lines,
  verified after each task); all touched `qc/*.py`/`tests/*.py` files remain LF.
- Flag for the phase verifier / next plan author: the cover verdict cell now holds
  `summary.verdict_text` with no glyph prefix (see Deviations) -- confirm this reading is
  acceptable, or specify the desired glyph placement, before plan 03/04 build on top of it.

---
*Phase: 03-verdict-and-report-integrity*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All created/modified files found on disk: `qc/report.py`, `app.py`,
  `tests/test_report_workbook_shape.py`, `tests/test_no_per_cell_styling.py`,
  `tests/test_one_snapshot_guard.py`.
- All 6 task commits found in git history: `198c575`, `5c53ad6`, `2d1fdcf`, `9afdb59`,
  `93de018`, `dd25b73`.
- Full suite green: `python3 -m pytest tests/ -q` -- 160 passed (137 baseline-of-phase +
  6 + 13 + 4 new).
- `python3 -m compileall -q qc app.py tests` -- clean.
- `python3 -m pytest tests/test_no_streamlit_in_qc.py -q` -- 4 passed (report module now
  imports openpyxl, still carries no UI-framework import).
- AST relocation check (`build_excel_report` absent from `app.py`'s function set; exactly one
  `qc.report.build_workbook(` call site) -- passes, prints `builder relocated ok`.
- `app.py` confirmed still CRLF-terminated (0 LF-only lines) after every edit in this plan.
- `commits: 6` measured via `git rev-list --count 0b93897..HEAD` against the persisted
  `plan_head_before` ledger -- matches the six commits listed above exactly.
