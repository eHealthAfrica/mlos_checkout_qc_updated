---
phase: 03-verdict-and-report-integrity
verified: 2026-09-10T00:00:00Z
status: passed
score: 15/15 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/03-verdict-and-report-integrity/03-01-PLAN.md", ".planning/phases/03-verdict-and-report-integrity/03-01-SUMMARY.md", ".planning/phases/03-verdict-and-report-integrity/03-02-PLAN.md", ".planning/phases/03-verdict-and-report-integrity/03-02-SUMMARY.md", ".planning/phases/03-verdict-and-report-integrity/03-03-PLAN.md", ".planning/phases/03-verdict-and-report-integrity/03-03-SUMMARY.md", ".planning/phases/03-verdict-and-report-integrity/03-04-PLAN.md", ".planning/phases/03-verdict-and-report-integrity/03-04-SUMMARY.md", "README.md", "app.py", "qc/boundary.py", "qc/mlos.py", "qc/report.py", "qc/results.py", "qc/schema.py", "qc/settlement.py", "qc/takeoff.py"]
covered_digest: "v1:sha256:e5f384034dca5f674b5550fafd17e0318896552d6fc6704f9e311fd93764d5bb"
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Upload a real submission (any format) and visually confirm the on-screen metric bar, verdict banner, Tab 2 score breakdown table and colour bands render as qc/report.py computes them (summary.verdict_text, summary.score_display, summary.score_band, per-layer n/a rows)."
    expected: "Metric bar shows checks_run/n_pass/n_fail/headline_distinct/pct_pass/weighted_score; banner shows the D-04 verdict sentence; Tab 2's score table shows n/a Layer Pass Rate and a numeric 0.0% Weighted Contribution for any unrun layer; colour band matches the capped score."
    why_human: "app.py cannot be imported or executed outside a live Streamlit runtime (established codebase convention per tests/test_one_snapshot_guard.py), so rendering is proven here only by static AST/structural checks, not by literally running the dashboard."
  - test: "Upload a .csv MLoS export with no separate Takeoffpoint file, open the Generate Report tab, and confirm the five-layer metadata card names the Takeoffpoint gap (`not run: no Takeoffpoint data supplied`) and that the combined check-breakdown table's rows match the downloaded workbook's QC Summary sheet row for row."
    expected: "All five layers appear on the card; Takeoffpoint shows the not-run reason instead of counts; the on-screen combined table and the workbook's QC Summary sheet agree row for row."
    why_human: "Same Streamlit-runtime limitation; this is plan 03-03's own deferred <human-check>, harvested per workflow.human_verify_mode: end-of-phase."
  - test: "Skim the rewritten README §8 (Weighted QC Score), §10 (Generate & Download Report) and §11 (Send QC Email) for readability and tone."
    expected: "Sections read clearly to an officer and accurately describe the shipped behaviour."
    why_human: "Prose readability and tone is a judgment call no automated string-presence check can make; the literal strings and absence of the stale full-credit claim are already proven programmatically."
---

# Phase 3: Verdict and Report Integrity Verification Report

**Phase Goal:** The verdict, score, report and email all describe every layer that ran, so a failing file can never be reported as clean.
**Verified:** 2026-09-10
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The downloaded report contains summary and detail sheets for all five layers, and its cover verdict reads FAILING whenever any layer holds a failing check (SC1, VERDICT-01/02) | ✓ VERIFIED | `qc/report.SHEET_NAMES` includes a `{layer} Issue Detail` sheet for all five layers plus one combined `QC Summary` sheet; `build_workbook`'s cover verdict cell reads `summary.verdict_text`, derived from `QcSummary.n_fail` across all five layers' `all_checks` (qc/report.py:404-441, 519-527). `tests/test_report_workbook_shape.py` (19 tests) and `tests/test_verdict_agreement.py` assert this on real workbook bytes; both pass. |
| 2 | A layer that ran zero checks displays as "n/a" and earns no score credit — withholding a file can no longer raise the weighted score (SC2, VERDICT-05) | ✓ VERIFIED | `LayerSummary.pass_rate` returns `None` (never `1.0`) when `not self.ran`; `weighted_contribution` returns `0.0`; `QcSummary.achievable_max` excludes unrun layers from the denominator (qc/report.py:119-133, 209-212). Tab 2 renders `n/a` for pass rate and a numeric `0.0%` contribution (app.py:729-741). `tests/test_layer_pass_rate.py` passes, including the `80.0% of 80.0% achievable` perfect-four-layer case (matches D-01's worked example, not the plan-text `100.0%` drafting error — documented discrepancy, correctly resolved in code's favour). |
| 3 | Issue-row totals agree on screen, in the report and in the email, and count distinct settlement rows rather than rule-row pairs (SC3, VERDICT-04) | ✓ VERIFIED | `LayerSummary.distinct_issue_rows` counts `detail.index.nunique()`; `qc/takeoff.py` and `qc/boundary.py` no longer pass `ignore_index=True` on their `pd.concat` (grep confirms only `qc/schema.py` retains it, correctly, per D-11's Schema exemption). `QcSummary.headline_distinct` sums the four non-Schema layers' distinct counts. All three surfaces (metric bar `c5` at app.py:674, workbook `summary_rows`, email `build_email_subject_and_body`) read the same `LayerSummary`/`QcSummary` object. `tests/test_distinct_row_counting.py`, `tests/test_verdict_agreement.py` pass. |
| 4 | The emailed summary reports Settlement layer counts alongside the other four layers (SC4, VERDICT-03) | ✓ VERIFIED | `build_email_subject_and_body` iterates `LAYER_ORDER` (Schema, MLoS, Settlement, Takeoffpoint, Boundary) unconditionally for both the Layer Summary block and the Check-by-Check block (qc/report.py:602-643) — Settlement can no longer be omitted by construction. `tests/test_email_body.py` passes. |
| 5 | Boundary checks appear as B0, B1, B2, B3 (B4, B5) in that order in every summary table and export, and raw-data sheets are written without per-cell font or border assignment (SC5, VERDICT-06/ENGINE-08) | ✓ VERIFIED | `qc/boundary.py` registers B0-B5 in that order (lines 25-38). `tests/test_summary_sheet_order.py` proves canonical order via a 3-subprocess `PYTHONHASHSEED`-varied comparison (the only proof that can detect ENGINE-09-class hash-order defects) across the on-screen tables, the combined summary sheet, and the email check list. `write_detail`/`write_raw` in `qc/report.py` append rows via `ws.append(row.tolist())` with no per-cell `Font`/`Border`/`Alignment`/fill (lines 489-514); `tests/test_no_per_cell_styling.py` (4 tests) asserts `has_style` both directions on header vs. body, post save/reload round-trip. |
| 6 | One shared computation produces the verdict/score/counts and every on-screen site reads it, never re-deriving its own (D-04 structural fix, four-site-agreement guard) | ✓ VERIFIED | `summary = qc.report.build_summary(...)` is called exactly once in app.py (line 654), outside the session-state cache if/else. `tests/test_verdict_agreement.py` (plan 04) is a standing AST-based guard plus real-bytes comparison across banner, Tab 2, Generate Report tab, workbook and email. All four remaining local `sum(1 for c in checks if "FAIL"...)` derivations found during the plan-01 auto-fix pass were replaced with `qc.report.count_failing`/`summary.layers[...].n_fail` (documented deviation, correctly fixed). |
| 7 | README §8, §10, §11 describe the shipped behaviour, with no remaining claim that a skipped layer scores as if it passed | ✓ VERIFIED | §8 (README.md:249-283) documents `None` pass rate, 0 contribution, achievable-maximum display, absolute colour bands and the two-state verdict with gap clause — no full-credit claim remains. §10 lists the exact 10-sheet order (D-06/D-08). §11 describes the D-14 body shape and D-16 subject. `tests/test_readme_columns_match_domain.py` and README string-presence checks (03-04 plan `<verify>`) pass. |

**Score:** 7/7 roadmap success criteria verified (all evidenced by passing standing tests, not presence alone). Plan-level must-haves: 15/15 substantively verified across all four plans' `must_haves.truths` (see per-plan detail below); 0 behavior-unverified.

### Per-Plan Must-Have Highlights (beyond the roadmap-level truths above)

- **D-05 genericity:** "did not run" is decided by one dict-keyed computation (`LayerSummary.ran`) applied uniformly to all five layers via `LAYER_ORDER`/`NOT_RUN_REASON`, not a per-layer special case — confirmed by reading `qc/report.py:106-137`.
- **D-12 findings reconciliation:** `LayerSummary.findings` (`len(self.detail)`, the old rule-row-pair count) stays visible beside `distinct_issue_rows` in `issue_line` — confirmed at qc/report.py:146-164.
- **D-13 share clause and zero-row edge:** `issue_line` omits the share clause when `source_row_count` is falsy, avoiding division by zero — confirmed at qc/report.py:161-164; exercised by `tests/test_layer_pass_rate.py`/`test_distinct_row_counting.py`.
- **D-09 cover/summary retain styling; raw/detail sheets do not:** confirmed structurally in `build_workbook` — `write_summary`/cover cells set `.font`/`.fill`/`.border`/`.alignment`; `write_detail`/`write_raw` body rows use bare `ws.append(...)`.
- **D-16 subject / D-04 body verdict:** `EMAIL_SUBJECT_PREFIX` + `verdict_short` (no gap clause) in the subject; `verdict_text` (full D-04 sentence) in the body — matches the plan's key-link note on why the two must differ.
- **Recorded discrepancies (both correctly resolved in the codebase, per orchestrator-supplied facts, cross-checked against 03-01-SUMMARY.md and 03-02-SUMMARY.md):**
  - D-01: perfect four-layer run renders `80.0% of 80.0% achievable` (not the plan-text's contradictory `100.0%`, which conflicted with D-01's own worked example and CONTEXT.md's specifics).
  - D-04: the workbook cover verdict cell holds `summary.verdict_text` verbatim, no glyph prefix (the plan's `<action>` prose suggested a glyph, but the same task's own `<behavior>`/`<acceptance_criteria>` require the bare sentence via exact-string and starts-with assertions).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `qc/report.py` | New Streamlit-free module: LAYER_ORDER/WEIGHTS/LABELS/NOT_RUN_REASON, LayerSummary, QcSummary, build_summary, summary_rows, build_workbook, build_email_subject_and_body | ✓ VERIFIED | 649 lines; not imported by `qc/__init__.py` (no cycle); imports only `openpyxl`/`pandas`/stdlib — no `streamlit` import (confirmed by `tests/test_no_streamlit_in_qc.py` passing). |
| `qc/results.py` `get_rule` | Registry accessor used by `summary_rows` to source the `Layer` column | ✓ VERIFIED | Referenced and exercised at qc/report.py:25, 345. |
| `qc/takeoff.py`, `qc/boundary.py` | Drop `ignore_index=True` to preserve row identity (D-11) | ✓ VERIFIED | grep confirms no `ignore_index` remains in either file's `pd.concat`; `qc/schema.py` retains it correctly (Schema has no distinct-row line). |
| `app.py` | Wire the shared computation into all on-screen sites; thin `send_qc_email`; five-layer Generate Report tab | ✓ VERIFIED | `summary = qc.report.build_summary(...)` called once outside cache branch (line 654); metric bar, banner, Tab 2, Tab 8, `send_qc_email` all read `summary.*`. |
| `tests/test_layer_pass_rate.py`, `test_distinct_row_counting.py`, `test_verdict_sentence.py`, `test_report_workbook_shape.py`, `test_no_per_cell_styling.py`, `test_email_body.py`, `test_summary_sheet_order.py`, `test_verdict_agreement.py` | New standing tests | ✓ VERIFIED | All present, all pass (87/87 in this subset; 195/195 full suite). |
| `README.md` §8/§10/§11 | Rewritten to match D-01–D-16 | ✓ VERIFIED | Confirmed by direct reading; no stale full-credit claim remains. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| app.py cache branch | `qc.report.build_summary` | Called exactly once, after both cache-hit/miss arms resolve | ✓ WIRED | Confirmed at app.py:654 — sits after the `if/else` block closes, not inside either arm (guards against F4-class staleness). |
| `qc.report.build_workbook` | `summary.verdict_text` | Cover verdict cell reads the shared object, not a local sum | ✓ WIRED | qc/report.py:437; no second `total_fail`-style derivation found in `build_workbook`. |
| `qc.report.build_email_subject_and_body` | `summary.verdict_text` / `summary.score_display` | Email verdict/score lines read the shared object | ✓ WIRED | qc/report.py:585-586. |
| `qc/report.summary_rows` | `qc.results.get_rule` | Layer column sourced from the registry, not a second hand-kept dict, with a raising cross-check | ✓ WIRED | qc/report.py:345-351 raises `ValueError` on a mismatch. |
| `app.py` Tab 8 | `qc.report.summary_rows(summary)` | On-screen combined table reads the same rows the workbook uses | ✓ WIRED | app.py:1132. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| Metric bar (`c2`-`c7`) | `summary.checks_run`/`n_pass`/`n_fail`/`headline_distinct`/`pct_pass`/`weighted_score` | `QcSummary` built from live `(checks, detail)` pairs from the five QC engines run against the uploaded file | Yes | ✓ FLOWING |
| Workbook `QC Summary` sheet rows | `summary_rows(summary)` | Live `LayerSummary.checks`/`detail` per layer | Yes | ✓ FLOWING |
| Email body layer blocks | `summary.layers[name]` | Same `QcSummary` object built once per run | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `.venv/bin/python -m pytest tests/ -q` | `195 passed in 5.24s` | ✓ PASS |
| Phase-3 test files only | `pytest tests/test_summary_sheet_order.py tests/test_verdict_agreement.py tests/test_layer_pass_rate.py tests/test_distinct_row_counting.py tests/test_verdict_sentence.py tests/test_email_body.py tests/test_report_workbook_shape.py tests/test_no_per_cell_styling.py -q` | `87 passed in 2.28s` | ✓ PASS |
| Prior-phase regression files (extraction parity, no-streamlit-in-qc, registry coverage, deterministic order) | `pytest tests/test_extraction_parity.py tests/test_no_streamlit_in_qc.py tests/test_registry_covers_emitted_ids.py tests/test_deterministic_order.py -q` | `16 passed in 2.66s` | ✓ PASS |
| `app.py` line-ending convention | `file app.py` | `CRLF line terminators` (by design, per orchestrator-supplied fact) | ✓ PASS (expected) |
| Boundary registry order | `grep register.*B[0-9] qc/boundary.py` | B0, B1, B2, B3, B4, B5 in that order | ✓ PASS |
| Hash-seed order proof | Inspected `tests/test_summary_sheet_order.py` | 3-subprocess `PYTHONHASHSEED`-varied comparison implemented (lines 296-330) | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; verification relied on the pytest suite above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| VERDICT-01 | 03-02 | Report contains summary+detail sheets for all five layers | ✓ SATISFIED | `SHEET_NAMES`, `write_detail` loop over `LAYER_ORDER` |
| VERDICT-02 | 03-02 | Cover verdict reads FAILING for any layer's failing check | ✓ SATISFIED | `verdict_text` derived from `all_checks` across five layers |
| VERDICT-03 | 03-03 | Email reports Settlement layer alongside others | ✓ SATISFIED | `build_email_subject_and_body` iterates `LAYER_ORDER` unconditionally |
| VERDICT-04 | 03-01 | Issue-row totals count distinct rows, not rule-row pairs | ✓ SATISFIED | `distinct_issue_rows`, index-preserving concat in takeoff/boundary |
| VERDICT-05 | 03-01 | No score credit for a zero-check layer; displays n/a | ✓ SATISFIED | `pass_rate is None`, `weighted_contribution == 0.0`, `achievable_max` excludes unrun layers |
| VERDICT-06 | 03-04 | Boundary order B0-B3(-B5) in every table/export | ✓ SATISFIED | Registry order + subprocess hash-seed standing proof |
| ENGINE-08 | 03-02 | Raw-data sheets written without per-cell styling | ✓ SATISFIED | `write_raw`/`write_detail` bare `ws.append`; `test_no_per_cell_styling.py` |

No orphaned requirements — REQUIREMENTS.md maps exactly these seven IDs to Phase 3, and all seven appear across the four plans' `requirements-completed` fields (03-01: VERDICT-04/05; 03-02: VERDICT-01/02/ENGINE-08; 03-03: VERDICT-03; 03-04: VERDICT-06) and are marked `[x] Complete` in REQUIREMENTS.md.

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|not yet implemented|coming soon` across `qc/report.py`, `qc/takeoff.py`, `qc/boundary.py`, `app.py` returned no matches.

### Human Verification Required

### 1. On-screen rendering of the shared computation

**Test:** Upload a real submission and visually confirm the metric bar, verdict banner, Tab 2 score breakdown table (n/a rows, colour bands) render as `qc/report.py` computes them.
**Expected:** Matches `summary.verdict_text`, `summary.score_display`, `summary.score_band`, and per-layer n/a rows exactly.
**Why human:** `app.py` cannot be imported or executed outside a live Streamlit runtime; this codebase's established convention (per `tests/test_one_snapshot_guard.py`) is that on-screen rendering is proven only by static AST/structural checks, not literal execution.

### 2. Five-layer Generate Report tab against a CSV-without-Takeoffpoint upload

**Test:** Upload a `.csv` MLoS export with no separate Takeoffpoint file; open the Generate Report tab.
**Expected:** All five layers appear on the metadata card; Takeoffpoint reads `not run: no Takeoffpoint data supplied`; the combined breakdown table matches the downloaded workbook's `QC Summary` sheet row for row.
**Why human:** Same Streamlit-runtime limitation. This is plan 03-03's own deferred `<human-check>`, harvested per `workflow.human_verify_mode: end-of-phase`.

### 3. README §8/§10/§11 readability skim

**Test:** Read the rewritten sections as an officer would.
**Expected:** Clear, accurate description of shipped behaviour.
**Why human:** Prose quality is a judgment call; the literal strings are already proven programmatically (03-04-SUMMARY.md's own `human_judgment: true` rationale).

### Gaps Summary

No gaps found. All 7 roadmap success criteria and all 7 requirement IDs are backed by passing standing tests and direct code inspection, including the two subtlest guarantees this phase exists to deliver: the subprocess hash-seed order proof (VERDICT-06, the only test shape that can detect an ENGINE-09-class ordering regression) and the four-site verdict-agreement test (the standing guard against F1 recurring). Two recorded plan-text-vs-locked-decision discrepancies (D-01's `80.0%` vs. a contradictory plan-text `100.0%`; D-04's bare verdict text vs. plan-text's glyph-prefix suggestion) were independently re-derived from CONTEXT.md and confirmed correct in the shipped code, matching the orchestrator-supplied facts. The only open items are three human-judgment checks (on-screen rendering, a live five-layer CSV walkthrough, and README readability) that no static check can close — routing this phase to `human_needed` rather than `passed`, per the decision tree's requirement that any non-empty human-verification list precludes a `passed` status even when every other truth is verified.

---

_Verified: 2026-09-10_
_Verifier: Claude (gsd-verifier)_
