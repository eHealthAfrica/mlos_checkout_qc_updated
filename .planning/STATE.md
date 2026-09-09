---
gsd_state_version: 1.0
current_phase: 2
current_phase_name: Detection Correctness and Three-Format Harness
status: planning
stopped_at: Phase 01 complete, ready to plan Phase 2
last_updated: "2026-09-09T23:56:23.631Z"
last_activity: 2026-09-10
last_activity_desc: Phase 01 complete, transitioned to Phase 2
state_head: 215baae439a77e1b08d7523353a9a8f3f4e0d890
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 6
  percent: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-09)

**Core value:** A file this tool calls clean is clean.
**Current focus:** Phase 01 — QC Engine Seam and Pinned Environment

## Current Position

Phase: 2 — Detection Correctness and Three-Format Harness
Plan: Not started
Status: Ready to plan
Last activity: 2026-09-10 — Phase 01 complete, transitioned to Phase 2

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 6
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4] Open item — OIDC provider choice (native HF OAuth vs external IdP). Blocks AUTH-01, AUTH-02. Does not block architecture; both meet at the `auth.py` boundary.
- [Phase 4] Open item — data-governance sign-off for hosting settlement coordinates and population figures on a third-party free tier. Named decision required before DEPLOY-01 rollout.
- [Phase 6] Open item — threshold values (household size range, target/population fraction, team-day distance). Blocks CONFIG-03, and Phase 7's POP-01, POP-02, TEAM-01, GEO-04. No published standard exists; must be supplied locally.
- [Phase 6] Open item — whether a boundary-vintage failure counts toward the weighted score. Blocks ADVIS-01, GEO-03.
- [Phase 01] WINDOWS.md #1 (open, deviation): Task 1's acceptance criterion 'grep -c VALID_ACC app.py reports 1' is unsatisfiable until plan 04 relocates run_mlos_qc out of app.py — VALID_ACC still has a legitimate non-import usage there.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-09T21:17:48.508Z
Stopped at: Phase 01 complete, ready to plan Phase 2
Resume file: None
