---
phase: "3"
slug: "verdict-and-report-integrity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-10"
updated: "2026-09-10"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed and pinned; no install needed) |
| **Config file** | `pytest.ini` — `testpaths = tests`, `python_files = test_*.py` |
| **Quick run command** | `python3 -m pytest tests/test_<file>.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Build command** | `python3 -m compileall -q qc app.py tests` |
| **Estimated runtime** | ~25 seconds full suite (91 tests at the pre-Phase-3 baseline, plus the three-hash-seed subprocess proof in plan 04 at ~3 s) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_<the task's own file>.py -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite green plus `python3 -m compileall -q qc app.py tests`
- **Max feedback latency:** ~25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | VERDICT-05 | T-03-02 / T-03-04 | A layer that ran zero checks has no pass rate and contributes 0.0, so withholding a table cannot raise the score; the summary is built once, outside both cache arms | unit + AST | `python3 -m pytest tests/test_layer_pass_rate.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-01-02 | 01 | 1 | VERDICT-04 | T-03-05 | Each layer counts a failing source row once; counts come from the layer's own detail frame, never from a display-only merge | unit | `python3 -m pytest tests/test_distinct_row_counting.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-01-03 | 01 | 1 | VERDICT-04, VERDICT-05 | T-03-01 | One verdict sentence, two states, gap named in both; no on-screen site recomputes a failing count | unit + AST | `python3 -m pytest tests/test_verdict_sentence.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-02-01 | 02 | 2 | VERDICT-02 | T-03-06 | Cover verdict derived from all five layers; a Boundary-only failure files as FAILING | unit (openpyxl round trip) | `python3 -m pytest tests/test_report_workbook_shape.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-02-02 | 02 | 2 | VERDICT-01 | T-03-07 / T-03-08 | Every layer has a detail sheet; an unrun layer shows a placeholder row with `n/a`; the `Layer` column comes from the registry and disagreement raises | unit (openpyxl round trip) | `python3 -m pytest tests/test_report_workbook_shape.py -q` | ✅ (extended by this task) | ⬜ pending |
| 03-02-03 | 02 | 2 | ENGINE-08 | T-03-10 | Raw and detail sheet body cells carry no per-cell style after a save-and-reload round trip; no row is dropped | unit (`Cell.has_style`) | `python3 -m pytest tests/test_no_per_cell_styling.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-03-01 | 03 | 3 | VERDICT-03 | T-03-12 / T-03-13 | Subject and body built by a pure function that reads no secrets; the sender takes one parameter | unit | `python3 -m pytest tests/test_email_body.py -q` | ❌ W0 (created in-task, RED first) | ⬜ pending |
| 03-03-02 | 03 | 3 | VERDICT-03 | T-03-11 | Five layer blocks including Settlement; counts and percentages only, no detail-row value in the body | unit | `python3 -m pytest tests/test_email_body.py -q` | ✅ (extended by this task) | ⬜ pending |
| 03-03-03 | 03 | 3 | VERDICT-03, VERDICT-04 | T-03-15 | The report tab's breakdown is built from the same rows as the export, so screen and workbook cannot diverge | AST + build | `python3 -m compileall -q qc app.py tests` | ✅ | ⬜ pending |
| 03-04-01 | 04 | 4 | VERDICT-06 | T-03-16 / T-03-19 | Canonical order at all four ordered outputs, reproducible across three process restarts with differing hash seeds; expected order read from the registry | unit + subprocess + AST | `python3 -m pytest tests/test_summary_sheet_order.py -q` | ❌ W0 (created in-task) | ⬜ pending |
| 03-04-02 | 04 | 4 | VERDICT-06 | T-03-17 | Verdict, score and headline character-identical at all four sites; every registry layer present at every site | unit + AST scan | `python3 -m pytest tests/test_verdict_agreement.py -q` | ❌ W0 (created in-task) | ⬜ pending |
| 03-04-03 | 04 | 4 | VERDICT-01, VERDICT-05 | T-03-18 | The manual states the shipped scoring rule, sheet set and email shape; the deleted rule is absent | doc assertion + existing README guards | `python3 -m pytest tests/test_readme_columns_match_domain.py tests/test_rules_reference_matches_registry.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity:** every one of the eleven tasks carries at least one runnable
`<automated>` command, so there is no run of three consecutive tasks without automated
feedback. Nyquist satisfied.

---

## Wave 0 Requirements

No separate Wave 0 plan is needed. pytest, `pytest.ini`, `tests/conftest.py`,
`tests/fixtures.py` and `tests/golden_fixture.py` already exist and cover the framework and
fixture needs of every task in this phase; openpyxl is already pinned and installed.

Each of the seven new test files is created by the task that needs it, as that task's first
move — the eight tasks marked `tdd="true"` write the test RED before any production code, so
the task's own `<automated>` command is runnable by the time the task closes. The files:

- [ ] `tests/test_layer_pass_rate.py` — VERDICT-05, D-01, D-02, D-05 (plan 01 task 1)
- [ ] `tests/test_distinct_row_counting.py` — VERDICT-04, D-10 to D-13 (plan 01 task 2)
- [ ] `tests/test_verdict_sentence.py` — D-04 both states, D-16's compact form (plan 01 task 3)
- [ ] `tests/test_report_workbook_shape.py` — VERDICT-01, VERDICT-02, D-06, D-07, D-08 (plan 02 tasks 1 and 2)
- [ ] `tests/test_no_per_cell_styling.py` — ENGINE-08, D-09 (plan 02 task 3)
- [ ] `tests/test_email_body.py` — VERDICT-03, D-14, D-15, D-16 (plan 03 tasks 1 and 2)
- [ ] `tests/test_summary_sheet_order.py` — VERDICT-06 (plan 04 task 1)
- [ ] `tests/test_verdict_agreement.py` — the four-sites guard and the layer-completeness invariant (plan 04 task 2)
- [x] Framework install — none required

**Shared fixture for this phase:** the existing MLoS fixture paired with an empty Takeoffpoint
frame. That one pairing exercises D-01 (no score credit), D-04 (the gap clause in both states),
D-07 (the placeholder row) and F1 (the cover must show the Boundary failure) together, and
mirrors the existing empty-Takeoffpoint pattern in `tests/test_extraction_parity.py`.

**Tests extended rather than replaced:** `tests/test_extraction_parity.py` and
`tests/test_golden_three_format_parity.py` must keep passing **unedited** through plan 01
task 2's index-preservation change — they compare detail frames by record, never by index, so
the change is invisible to them. An edit to either file to make plan 01 green is a signal that
the change went further than D-11 allows.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The Generate Report tab renders five layers and the breakdown table matches the workbook row for row | VERDICT-03, VERDICT-04 | `app.py` cannot be imported outside a Streamlit runtime, so the rendered card and table have no automated assertion; the underlying row builder is unit-tested and the wiring is AST-asserted | Upload a `.csv` MLoS export with no separate Takeoffpoint file, open the Generate Report tab, confirm the metadata card lists all five layers with the Takeoffpoint row reading `not run: no Takeoffpoint data supplied`, download the workbook and compare its `QC Summary` sheet rows against the on-screen breakdown |

Everything else has automated verification. `human_verify_mode` is `end-of-phase`, so this is
a `<verify><human-check>` on plan 03 task 3 rather than a blocking checkpoint task.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (each new test file is created by its own task)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
