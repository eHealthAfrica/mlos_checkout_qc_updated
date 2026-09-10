---
gsd_state_version: "1.0"
current_phase: 03
current_phase_name: Verdict and Report Integrity
status: verifying
stopped_at: Completed 03-04-PLAN.md
last_updated: "2026-09-10T20:49:22.673Z"
last_activity: 2026-09-10
last_activity_desc: Phase 03 execution started
state_head: 908d76f237b712bf4511c69c0ca901b331a040e3
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 16
  completed_plans: 16
  percent: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-10)

**Core value:** A file this tool calls clean is clean.
**Current focus:** Phase 03 — Verdict and Report Integrity

## Current Position

Phase: 03 (Verdict and Report Integrity) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Last activity: 2026-09-10 — Phase 03 execution started

Progress: [█░░░░░░░░░] 14%

## Performance Metrics

**Velocity:**

- Total plans completed: 12
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |
| 02 | 6 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 25 min | 2 tasks | 4 files |
| Phase 01 P02 | 17min | 3 tasks | 5 files |
| Phase 01 P03 | 15min | 3 tasks | 9 files |
| Phase 01 P04 | 15min | 3 tasks | 5 files |
| Phase 01 P05 | 12min | 3 tasks | 6 files |
| Phase 01 P06 | 40min | 3 tasks | 7 files |
| Phase 02 P01 | 42min | 3 tasks | 9 files |
| Phase 02 P02 | 15min | 2 tasks | 5 files |
| Phase 02 P03 | 25min | 2 tasks | 5 files |
| Phase 02 P04 | 3h 37m | 3 tasks | 3 files |
| Phase 02 P05 | 45min | 2 tasks | 6 files |
| Phase 02 P06 | 50 min | 3 tasks | 2 files |
| Phase 03 P01 | 55min | 3 tasks | 9 files |
| Phase 03 P02 | 45min | 3 tasks | 5 files |
| Phase 03 P03 | 15min | 3 tasks | 3 files |
| Phase 03 P04 | 55min | 3 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Horizontal layers over vertical MVP — layers complete before assembly. Accepted tradeoff: individual defect fixes are not separately shippable.
- Roadmap: ENGINE-01/02 and ENGINE-05 kept in one phase — the F3 registry fix and the `qc/` extraction are the same edit.
- Roadmap: ENGINE-07 (pin `pandas==3.0.5`) placed in Phase 1, not as end-of-milestone cleanup — otherwise every later fix is tested against whatever pandas resolved.
- Roadmap: ENGINE-09 (F10, deterministic rule order) mapped to Phase 1, not the report layer. Verified in code: the `YN_NA_COLS` set literal at `app.py:100` is iterated at `app.py:946` to emit eight checks, all as `add("12", ...)` — so the same eight rows carry both the F3 identity defect and the F10 ordering defect. One registry fixes both.
- PROJECT.md: Fix the 14 audited defects before adding any new layer.
- PROJECT.md: Ship M2 (deployment) before M3 (new layers) — product choice, not a technical gate.
- [Phase 01]: Package-legitimacy checkpoint (pandas 3.0.5, numpy>=2.0.0,<3.0.0, pytest>=8.0.0,<10.0.0) approved-with-evidence; all three SUS verdicts confirmed as PyPI metadata false positives (each publishes a real GitHub repository).
- [Phase 01]: Created a project-local .venv (already gitignored) to work around macOS Homebrew's PEP 668 externally-managed-environment pip restriction; not a shipped project convention, just a local install path.
- [Phase 01]: Row 1's timestamp cell is a deliberate Python None, not a string, since app.py's rule-1 null check only catches real NaN/None via .isnull(), not empty strings. — Documented as the sole exception to 'every cell is a string' in tests/fixtures.py's module docstring.
- [Phase 01]: Reordered tests/fixtures.py's Takeoffpoint columns to put globalid first, not name, to avoid a pre-existing app.py column-duplication bug in run_takeoff_qc's BASE list construction. — Real app.py behavior unrelated to TP2-TP5 rules under test; fixture column order isn't pinned by acceptance criteria (set match only).
- [Phase 01]: sys.meta_path finders must implement find_spec, not find_module, under CPython 3.13 — verified empirically before writing the qc/ import-boundary subprocess test.
- [Phase 01]: qc/ package cut through the Schema layer as the phase's tracer slice: registry (qc/results.py), relocated constants/predicates/schema, and app.py now calls qc.schema.run_schema_qc + qc.sort_by_registry at the real call site.
- [Phase 01]: [Phase 01] Unrolled R11's loop into three explicit per-column add() calls (urban/rural/scattered) so the literal identifier appears in both the register() call and the emission path, satisfying the plan's grep-based acceptance criterion; R12's loop over YN_NA_COLS stays a genuine loop per the plan's key_links.
- [Phase 01]: [Phase 01] FROZEN_IDENTIFIERS in tests/test_rule_identifiers.py holds 29 entries, not the 27 CONTEXT.md's D-04 states -- verified directly against every add()/register() call site (Settlement has 5 checks not 4, Boundary has 4); completeness of the freeze guarantee kept over matching the stated total.
- [Phase 01]: Applied _nan_safe to all three new Settlement/Takeoffpoint/Boundary parity comparisons, extending plan 04's pattern to cover NaN cells arising from pd.concat column-union across per-rule detail frames, not only from a genuinely-null fixture cell.
- [Phase 01]: Left run_ward_boundary_qc's raw checks-list emission order as B0, B1, B3, B2 (matching pre-extraction app.py exactly) rather than reordering add() calls to force B0/B1/B2/B3 directly; canonical_order() and the sort_by_registry-piped call site already deliver the required order.
- [Phase 01]: [Phase 01] Fixed a pre-existing test-isolation leak in tests/test_results_registry.py's duplicate-id tests (throwaway identifiers left registered in the shared process-global registry), exposed by plan 06's new exact-set-equality rules-reference/registry test.
- [Phase 01]: [Phase 01] Plan 06 Task 2 committed as a genuine RED-then-GREEN pair (unlike this phase's earlier parity tests): the test required a real production-code change (expanding the MLoS sidebar reference table) to turn green, verified failing first.
- [Phase 01]: [Phase 01] Plan 06 followed the plan's narrow dead-import cleanup scope in app.py (FLAG_COLS, pct, vec_is_uuid, vec_is_editor only), leaving other already-unused qc.domain imports untouched as out of the plan's declared scope.
- [Phase 02]: D-05 confirmed as written: uniform absence sentinel list for every column, exact literal NA exempted case-sensitively
- [Phase 02]: Golden fixture's Takeoffpoint table carries no TAKEOFF_REQUIRED_COLS-named column so R2/R3/R4 stay silent uniformly across all three formats (Plan 02's INTEG-02 scope)
- [Phase 02]: test_extraction_parity.py rescoped to a baseline-intersection comparison (planner decision 4) so plans 02/03/05 can register new rule identifiers without editing it again
- [Phase 02]: Phase 02 Plan 02: rebuilt R2/R3/R4 and TP2/TP3/TP4 cross-table match masks to exclude absent source cells and registered six new .missing identifiers, closing INTEG-02 (F9). — A blank source cell must fail its own .missing check and be excluded from the match rule, or D-03's exactly-three-checks invariant breaks into four.
- [Phase 02]: [Phase 02] qc/columns.py carries zero relative sibling imports by design — normalize_name/normalize_columns perform no canonical-set lookup or aliasing (D-08/D-09), so the plan's from-dot-import acceptance criterion is a documented, unsatisfiable-by-design discrepancy rather than a forced dead import.
- [Phase 02]: [Phase 02] Plan 03: S1/S2's column-set comparison changed from a lower-cased projection to the frame's raw columns, removing qc/schema.py's own second, diverging view of the column set (F7's root cause), proven behaviour-neutral for the shared fixture.
- [Phase 02]: [Phase 02] Plan 04: qc.columns.normalize_columns is now called at all three officer-supplied load paths (MLoS frame, same-upload Takeoffpoint frame, separately-uploaded Takeoffpoint override), closing F7 -- a non-canonically spelled header no longer satisfies S1 while silently skipping its rules. — Collision groups are tagged with their source table and merged (not overwritten) across all three load sites into two session-state keys, so the on-screen rename panel and the Columns Renamed report sheet always read the same single source of truth -- the exact two-sources-of-truth shape F7 was.
- [Phase 02]: [Phase 02] Plan 04: Column renames are reported to the officer in exactly two places -- an on-screen expander in Tab 1 and a conditional Columns Renamed sheet in the downloaded report -- with no Pass/Fail and no score weight, verified live per D-11 (Task 3 checkpoint, all four verdicts pass). — build_excel_report's new column_renames keyword parameter defaults to None so existing callers keep working, and an AST-level acceptance check confirms the rename record never enters all_checks or LAYER_WEIGHTS.
- [Phase 02]: [Phase 02] Plan 05: B4/B5 report the boundary reference's national-fallback widening and unavailability as failing checks instead of silent branches, closing INTEG-04; canonical boundary order extended to B0-B5 (49 identifiers total). — D-16 through D-19 promote reference scope and availability to first-class reported facts; B4's FAIL description deliberately names both B1 and B2 since the fallback reassigns both frames.
- [Phase 02]: [Phase 02] Plan 05: Fixed test_deterministic_order.py's full-registry equality assertion (Rule 1), broken the instant B5 was registered, since that test's fixture always carries a real reference and can never emit a reference-absence-only check. — B5's real coverage proof lives in test_registry_covers_emitted_ids.py's dedicated reference-absent scenario (Task 2); excluding B5 from the deterministic-order comparison keeps that test's real purpose (cross-process order stability) intact.
- [Phase 02]: D-12 confirmed as written: generated eha_guid is a session-scoped uuid4(), not derived from content
- [Phase 02]: Phase 02: build_excel_report's MLoS parameter renamed mlos_df -> mlos_as_submitted to make the as-submitted intent legible and let the AST guard check an unambiguous name
- [Phase 02]: Phase 02: get_uploaded_data's internal parse-and-normalise local deliberately named _mlos_parsed (not mlos_raw) so the whole-file mlos_raw-consumer AST guard stays unambiguous
- [Phase 03]: 03-01: One shared QcSummary/LayerSummary computation replaces four independent app.py derivations of the verdict/score/row-count (closes F1's structural root cause, F6, F8)
- [Phase 03]: 03-01: Documented discrepancy -- plan's Task 1 acceptance criteria claim "100.0% of 80.0% achievable" for a fully-passing four-layer run; implementation follows D-01's own worked example ("a perfect four-layer file scores 80.0%") instead, since renormalising would reopen F6
- [Phase 03]: 03-02: Cover verdict cell holds summary.verdict_text verbatim, no glyph prefix -- follows the plan's literal behavior/acceptance criteria (exact-string match) over its action prose
- [Phase 03]: 03-02: Report workbook reshaped to one combined QC Summary sheet (registry-sourced Layer column, D-07 placeholder rows) plus one detail sheet per layer, replacing the old two-summary-sheet shape
- [Phase 03]: 03-03: qc.report.build_email_subject_and_body(summary) is a pure email builder (no secrets, no smtplib); send_qc_email reduced to a one-parameter thin SMTP sender — Closes F11/VERDICT-03 -- today's email body had no Settlement layer line at all
- [Phase 03]: 03-03: Generate Report tab's three-column MLoS/Settlement/Takeoffpoint breakdown replaced with a five-layer metadata card and one combined table built from qc.report.summary_rows(summary) — Screen and downloaded workbook now read the same row builder so they cannot drift apart
- [Phase 03]: [Phase 03] 03-04: Standing proof of canonical rule order at all four ordered outputs (summary object, summary_rows, workbook QC Summary sheet, email check list), read from qc.canonical_order() at test time, never a literal identifier list -- closes VERDICT-06/F14
- [Phase 03]: [Phase 03] 03-04: Standing proof that the verdict sentence/score/headline are character-identical at the workbook cover and email body, and every registry layer appears at every presentation site (assumption-delta companion invariant); found and fixed two real offenders app.py's own local FAIL-counting and a per-layer-name-keyed label dict, both relocated to qc/report.py
- [Phase 03]: [Phase 03] 03-04: README.md sections 8, 10, 11 rewritten to match D-01 to D-16's shipped scoring/report/email behaviour; no remaining claim that a skipped layer scores as though it passed

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4] Open item — OIDC provider choice (native HF OAuth vs external IdP). Blocks AUTH-01, AUTH-02. Does not block architecture; both meet at the `auth.py` boundary.
- [Phase 4] Open item — data-governance sign-off for hosting settlement coordinates and population figures on a third-party free tier. Named decision required before DEPLOY-01 rollout.
- [Phase 6] Open item — threshold values (household size range, target/population fraction, team-day distance). Blocks CONFIG-03, and Phase 7's POP-01, POP-02, TEAM-01, GEO-04. No published standard exists; must be supplied locally.
- [Phase 6] Open item — whether a boundary-vintage failure counts toward the weighted score. Blocks ADVIS-01, GEO-03.
- [Phase 03] Phase 3 was planned while Phase 2 plans 05/06 were still unexecuted; 03-01's precondition (B4/B5 registered, `mlos_corrected` snapshot in session state) is now satisfied. Plan line anchors into `app.py` may have shifted — executors must read the file, not trust the numbers.
- [Phase 03] `app.py` is CRLF-terminated by design (restored in 90999a6 after edit tooling normalised it to LF). Executors editing it must preserve CRLF or a ~130-line change reads as a whole-file rewrite.
- [v2 / HIST-01] Generated `eha_guid` values are session-scoped (D-12): churn detection in a future history layer will see re-generation as churn. Accepted at a one-way gate; not a defect.
- [Phase 02] Codebase map (`.planning/codebase/`) is stale by four top-level files (README.md, pytest.ini, requirements-dev.txt, `mlos_checkout_QC list.txt`); advisory only, refresh with `/gsd-map-codebase`.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-10T20:49:22.619Z
Stopped at: Completed 03-04-PLAN.md
Resume file: None
