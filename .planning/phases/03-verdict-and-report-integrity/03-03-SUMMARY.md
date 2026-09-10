---
phase: 03-verdict-and-report-integrity
plan: 03
subsystem: reporting
tags: [email, smtp, verdict, report, streamlit-free]

requires:
  - phase: 03-verdict-and-report-integrity
    provides: "qc/report.py's QcSummary/LayerSummary dataclasses and build_summary() (plan 01),
      plus summary_rows()/build_workbook() (plan 02) -- the shared computation and row builder
      this plan's email body and Generate Report tab read instead of recomputing"
provides:
  - "qc.report.build_email_subject_and_body(summary) -> (subject, body) -- the pure,
    Streamlit-free email subject/body builder, unit-testable without an SMTP mock"
  - "qc.report.EMAIL_SUBJECT_PREFIX -- the fixed 'MLoS QC:' subject prefix"
  - "app.py's send_qc_email(summary) -- reduced to a one-parameter SMTP sender"
  - "app.py's Generate Report tab -- five-layer metadata card and one combined check-breakdown
    table sourced from qc.report.summary_rows(summary)"
affects: [03-04-verdict-agreement-and-order]

actuals:
  tokens: 7024
  tasks: 3
  commits: 5
  plan_head_before: 90781bbfbdfa81b897d721aa9f96b0a9325b4e77

tech-stack:
  added: []
  patterns:
    - "Pure builder behind a thin sender: qc.report.build_email_subject_and_body(summary) reads
      only the shared summary and returns (subject, body); app.py's send_qc_email keeps the
      hard-coded recipients and the existing st.secrets/smtplib code but no longer derives any
      verdict, count or body text itself"
    - "Layer blocks built by iterating LAYER_ORDER, never by naming a layer one at a time -- the
      same discipline plan 01/02 established, applied here to close F11 (Settlement's absence
      from today's email body)"
    - "Screen and export share one row builder: the Generate Report tab's combined breakdown
      table and the downloaded workbook's QC Summary sheet both read qc.report.summary_rows(),
      so they cannot show different rows"

key-files:
  created:
    - tests/test_email_body.py
  modified:
    - qc/report.py
    - app.py

key-decisions:
  - "Layer Summary section opens with the literal heading 'Layer Summary' (not fixed by any
    CONTEXT.md decision) specifically so a test string like 'MLoS' -- which already appears in
    the body's title line ('MLoS QC Report — {filename}') -- can be searched for unambiguously
    starting after that marker, rather than colliding with the header block's own text."
  - "Generate Report tab's combined breakdown table colors only the Status column (by index)
    rather than the first column, since the first column is now Layer, not Status -- preserves
    the original highlight's visual intent (color the status text) rather than literally
    reusing 'style the first column', which would now color the wrong cell."

requirements-completed: [VERDICT-03]

coverage:
  - id: D1
    description: "qc.report.build_email_subject_and_body(summary) -> (subject, body): pure,
      reads no secrets, imports no transport. Subject carries the compact verdict (D-16);
      header carries the D-04 verdict sentence verbatim, the D-01 score display and the
      headline issue line. app.py's send_qc_email reduced to a one-parameter SMTP sender."
    requirement: "VERDICT-03"
    verification:
      - kind: unit
        ref: "tests/test_email_body.py (Task 1 section, 7 tests)"
        status: pass
      - kind: unit
        ref: "AST checks: send_qc_email's argument list is exactly ['summary']; exactly one
          qc.report.build_email_subject_and_body( call site in app.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five layer blocks in canonical order (Settlement among them -- the direct
      VERDICT-03/F11 fix), each with Checks Run/Failing and the D-13 issue_line (Schema
      exempt); the existing Schema missing-columns block preserved; a grouped check-by-check
      list showing every check that ran, passing and failing, in registry canonical order
      (D-15); no detail-frame cell value (settlement name, coordinate, population figure)
      enters the body."
    requirement: "VERDICT-03"
    verification:
      - kind: unit
        ref: "tests/test_email_body.py (Task 2 section, 11 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Generate Report tab's metadata card lists all five layers (D-13 counts, gap
      named for an unrun layer) and its check breakdown is one combined table built from
      qc.report.summary_rows(summary) -- the same rows the workbook's QC Summary sheet uses --
      replacing the old three-column MLoS/Settlement/Takeoffpoint-only layout."
    verification:
      - kind: unit
        ref: "AST checks: no st.columns(3) survives in the tab; qc.report.LAYER_ORDER and
          qc.report.summary_rows( each present; 'Takeoffpoint Check Breakdown' literal absent;
          compileall and full pytest suite green"
        status: pass
    human_judgment: true
    rationale: "app.py cannot be imported or executed outside a live Streamlit runtime (this
      codebase's established convention, per tests/test_one_snapshot_guard.py's docstring and
      03-01-SUMMARY.md's D6 rationale), so the actual on-screen rendering of the five-layer
      metadata card and the combined table is proven here only by static AST/compile checks.
      The task's own <human-check> (upload a .csv MLoS export with no separate Takeoffpoint
      file; confirm all five layers on the card and the combined table matches the downloaded
      workbook's QC Summary sheet row for row) is deferred to end-of-phase UAT harvesting per
      workflow.human_verify_mode: end-of-phase."

duration: 15min
completed: 2026-09-10
status: complete
---

# Phase 3 Plan 3: Five-Layer Email Summary and Report Tab Summary

**The emailed QC summary now carries a verdict-bearing subject, all five layer blocks
(Settlement among them, closing F11), and a grouped check-by-check list built by a pure
function `qc.report.build_email_subject_and_body`; the Generate Report tab's three-layer
breakdown is replaced with a five-layer metadata card and one combined table sourced from the
same row builder the downloaded workbook uses.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-10T20:37:00+01:00
- **Completed:** 2026-09-10T20:52:36+01:00
- **Tasks:** 3 (Task 1 `type="tracer" tdd="true"`, Task 2 `type="auto" tdd="true"`, Task 3
  `type="auto"`)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `qc.report.build_email_subject_and_body(summary) -> (subject, body)`: pure, no `st.secrets`,
  no `smtplib` import, unit-testable without a Streamlit runtime or an SMTP mock.
  `EMAIL_SUBJECT_PREFIX = "MLoS QC:"`. Subject is `MLoS QC: FAILING (12 checks) —
  kano_checkout.xlsx` / `MLoS QC: CLEAN — kano_checkout.xlsx` (D-16, using `verdict_short` —
  the full sentence would put two em-dash separators in one subject line). Body's header
  carries `summary.verdict_text` verbatim (D-04, no glyph decoration — the same sentence the
  banner, the Generate Report tab and the report cover print), `summary.score_display`, checks
  run/passing/failing and `summary.headline_issue_line`.
- Five layer blocks in `LAYER_ORDER`, built by iterating the registry order rather than naming
  a layer at a time (the exact shape that left Settlement out of today's body — F11/VERDICT-03).
  Each running layer carries Checks Run, Checks Failing and (except Schema, per D-13) an Issue
  Rows line reading `layer.issue_line` verbatim; an unrun layer's block is exactly its
  `issue_line` (`not run: no Takeoffpoint data supplied`). The existing Schema missing-columns
  block is preserved, now reading `summary.layers["Schema"].detail` directly rather than a
  separate argument, and emits nothing when that frame is empty.
- Check-by-Check Summary section replaces the old flat loop: grouped under layer headings in
  `LAYER_ORDER` order, each layer's own checks piped through `sort_by_registry` — every check
  that ran, passing and failing (D-15), so a CLEAN email still shows exactly what was checked.
- `app.py`'s `send_qc_email` reduced to `send_qc_email(summary)`: recipients and the existing
  secrets/SMTP-send code unchanged; subject and body now come from the builder. Single call
  site behind the send button updated to pass only `summary`.
- Generate Report tab's metadata card replaced its hard-coded MLoS/Settlement/Takeoffpoint
  block with a loop over `qc.report.LAYER_ORDER`: all five layers now appear with the D-13
  issue lines, and a layer that did not run names the gap instead of showing zeros. The
  three-column check breakdown is replaced with one combined table built from
  `qc.report.summary_rows(summary)` — the same rows, same order, the downloaded workbook's `QC
  Summary` sheet uses, so the screen and the export cannot drift apart.

## Task Commits

Each TDD task followed the RED → GREEN cycle (task 1 additionally ran the tracer feedback gate
before task 2's expansion — all four automated `<verify>` commands re-ran clean, no checkpoint
needed per `workflow.human_verify_mode: end-of-phase`):

1. **Task 1: End-to-end email — pure subject/body builder behind a thin sender** —
   `809ae98` test, `0299014` feat
2. **Task 2: Five layer blocks and a grouped check list in the body** —
   `bea72ab` test, `7f77302` feat
3. **Task 3: Five layers on the Generate Report tab** — `9d49047` feat (not TDD; `type="auto"`
   only)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

No `refactor(03-03):` commits — no REFACTOR phase was needed for either TDD task.

## Files Created/Modified

- `qc/report.py` — `EMAIL_SUBJECT_PREFIX`, `build_email_subject_and_body` added (header block
  in task 1; Layer Summary section, Schema missing-columns block and grouped check-by-check
  list added in task 2)
- `app.py` — `send_qc_email` reduced to a one-parameter SMTP sender; its call site updated;
  Generate Report tab's metadata card and check breakdown rebuilt for five layers
- `tests/test_email_body.py` — new, 18 tests (task 1: seam/subject/header, 7; task 2: layer
  blocks/missing-columns/grouped list, 11)

## Decisions Made

- The Layer Summary section opens with the literal heading `Layer Summary`, chosen so tests
  (and any future reader) can search for a layer name like `MLoS` starting after that marker
  without colliding with the body's own title line, which already contains the substring
  `MLoS` (`MLoS QC Report — {filename}`). No CONTEXT.md decision pins this heading's wording
  (D-14 fixes block contents, not labels — the same discretion 03-01/03-02 record for
  layer-block label vocabulary).
- The Generate Report tab's combined breakdown table colors the `Status` column specifically
  (by index), not literally "the first column" as the old three-column tables did — because the
  first column is now `Layer`, and coloring it would move the color off the status text the
  highlight was always meant to convey.

## Deviations from Plan

None — plan executed exactly as written. All `must_haves` truths and prohibitions verified by
the tests above; no Rule 1-4 auto-fixes or architectural questions arose.

## Issues Encountered

- Two self-inflicted AST-count false positives during implementation, both fixed before
  committing: (1) task 1's `send_qc_email` docstring mentioned
  `qc.report.build_email_subject_and_body(summary)` in prose, pushing
  `src.count("qc.report.build_email_subject_and_body(")` to 2 against the plan's exactly-one
  acceptance criterion — reworded the docstring to describe the function without repeating its
  call-shaped literal. (2) the same pattern recurred in task 3's inline comment referencing
  `qc.report.summary_rows(summary)` against the exactly-one acceptance criterion for
  `qc.report.summary_rows(` — reworded similarly. Neither is a production-code deviation; both
  are comment/docstring wording caught by the plan's own machine-checked acceptance criteria
  before commit.
- `gsd-tools check tdd-red-evidence`'s TAP-format parser does not match this project's
  `pytest -q` output shape (documented in 03-02-SUMMARY.md; unchanged in this plan). Both RED
  phases were verified manually against the same fail-fast criteria the tool encodes: task 1's
  7 RED tests failed on a genuine `AttributeError` for the missing `build_email_subject_and_body`
  symbol; task 2's 9 RED tests failed on genuine `AssertionError`/`ValueError` for missing
  planned content (the `Layer Summary` marker, layer headings, check lines) — never a
  collection error, an import failure, or an unrelated failure. Full `pytest -q` output for
  each RED commit is captured in this session's tool-call history and summarized in each
  `test(03-03):` commit message.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `qc.report.build_email_subject_and_body` is the seam plan 04 (verdict-agreement/order tests)
  can read: the email verdict line now holds `summary.verdict_text` verbatim with no glyph
  decoration, matching the banner, the Generate Report tab and the report cover — the exact
  four-site agreement plan 04's standing test needs to prove.
- `app.py` confirmed still CRLF-terminated after every edit in this plan (verified after each
  task); `qc/report.py` and `tests/test_email_body.py` remain LF.
- Task 3's `<human-check>` (upload a `.csv` MLoS export with no separate Takeoffpoint file;
  confirm the Generate Report tab's five-layer card and combined table against the downloaded
  workbook) is deferred to end-of-phase UAT harvesting, not exercised in this plan.

---
*Phase: 03-verdict-and-report-integrity*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All created/modified files found on disk: `qc/report.py`, `app.py`,
  `tests/test_email_body.py`, this SUMMARY.
- All 5 task commits found in git history: `809ae98`, `0299014`, `bea72ab`, `7f77302`,
  `9d49047`.
- Full suite green: `python3 -m pytest tests/ -q` — 178 passed (160 phase-baseline + 18 new).
- `python3 -m compileall -q qc app.py tests` — clean (exit 0).
- All plan-level `<verification>` commands re-run clean: `test_email_body.py` (18 passed), full
  suite (178 passed), compileall (exit 0), and all AST checks (`send_qc_email` argument list is
  exactly `["summary"]`; exactly one `qc.report.build_email_subject_and_body(` call site;
  exactly one `qc.report.summary_rows(` call site; `qc.report.LAYER_ORDER` present;
  `"Takeoffpoint Check Breakdown"` absent; `issue_line` appears 8+ times).
- `app.py` confirmed still CRLF-terminated (0 LF-only lines) after every edit in this plan;
  `qc/report.py` and `tests/test_email_body.py` remain LF.
- `commits: 5` measured via `git rev-list --count 90781bb..HEAD` against the persisted
  `plan_head_before` ledger — matches the five commits listed above exactly.
