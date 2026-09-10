---
phase: "2"
slug: "detection-correctness-and-three-format-harness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-10"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase` from `02-RESEARCH.md` § Validation Architecture.
> The Per-Task Verification Map is filled once PLAN.md files exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (satisfies the `>=8.0.0,<10.0.0` pin in `requirements-dev.txt`) |
| **Config file** | `pytest.ini` — `testpaths = tests`, `python_files = test_*.py` |
| **Quick run command** | `python3 -m pytest tests/ -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` — the suite is small enough that quick and full are the same command |
| **Estimated runtime** | ~2 seconds (34 tests, verified 2026-09-10) |
| **Interpreter** | System `python3` (3.13.1) with `pandas==3.0.5` |

**Interpreter note (deliberate, do not "correct"):** `02-RESEARCH.md` prefixes its commands with
`.venv/bin/python`. **Use plain `python3 -m pytest` instead.** The pinned dependency set was
installed into the system interpreter by explicit user decision, all 20 of Phase 1's proven
verify commands use bare `python3`, and the suite is green there. A stray `.venv/` exists (created
during research, gitignored) and must not be depended on by any verify command.

**Baseline established before this phase's work begins:** `34 passed`. Phase 1's
`tests/test_environment_pins.py::test_pandas_installed_version_matches_the_pin` was failing at the
start of this planning run (installed 3.0.2 vs pinned 3.0.5) and was fixed by installing the pin.
Any task in this phase that leaves the suite below 34 passing has regressed something.

---

## Sampling Rate

- **After every task commit:** `python3 -m pytest tests/ -q`
- **After every plan wave:** `python3 -m pytest tests/ -q` (full suite — ~2s, no reason to sample a subset)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Requirement → Test Map

Requirement-level map carried from `02-RESEARCH.md`. Task IDs are added once plans exist.

| Requirement | Behaviour | Test Type | Automated Command | File Exists |
|-------------|-----------|-----------|-------------------|-------------|
| INTEG-01 | Rule 1 detects missing values identically across `.sqlite` / `.csv` / `.xlsx` | unit + golden | `python3 -m pytest tests/test_absent_sentinel_guard.py tests/test_golden_three_format_parity.py -q` | ❌ W0 (both new) |
| INTEG-02 | A blank cannot satisfy R2/R3/R4/TP2/TP3/TP4, and a blank facing a blank is not a match | unit | `python3 -m pytest tests/test_missing_cross_table.py -q` | ❌ W0 (new; separate blank-cell builders in `tests/fixtures.py`) |
| INTEG-03 | Normalisation once at load, `S3` collision, rename reporting, `README.md` agrees with `qc/domain.py` | unit + integration | `python3 -m pytest tests/test_column_collision.py tests/test_normalisation_at_load.py tests/test_readme_columns_match_domain.py -q` | ❌ W0 (all three new) |
| INTEG-04 | `B4` / `B5` make the fallback and the absent reference visible, with the exact emitted set asserted per reference state | unit | `python3 -m pytest tests/test_boundary_reference_states.py tests/test_registry_covers_emitted_ids.py -q` | ❌ W0 (one new, one extended) |
| ENGINE-03 | Displayed rows and computed checks describe one frame | unit (AST over `app.py`) | `python3 -m pytest tests/test_one_snapshot_guard.py -q` | ❌ W0 (new) |
| ENGINE-04 | Auto-correction runs exactly once; `eha_guid` stable per submission | unit (AST, shared guard) | `python3 -m pytest tests/test_one_snapshot_guard.py -q` | ❌ W0 (new, shared with ENGINE-03) |
| ENGINE-06 | Golden fixture: three formats, identical check summaries | integration | `python3 -m pytest tests/test_golden_three_format_parity.py -q` | ❌ W0 (new) |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 02-01 | 1 | INTEG-01 | — | `checkpoint:decision`, D-05 one-way gate — no automated verify by design | checkpoint | *n/a — `gate="blocking-human"`* | n/a | ⬜ pending |
| 01-T2 | 02-01 | 1 | INTEG-01, ENGINE-06 | T-02-01, T-02-02 | Rule 1 detects an absent required field identically across the three formats; sentinel strings cannot mask a missing field | tracer / integration | `python3 -m pytest tests/test_golden_three_format_parity.py tests/test_extraction_parity.py -q` | ❌ W0 (both new/rewritten) | ⬜ pending |
| 01-T3 | 02-01 | 1 | INTEG-01 | T-02-02 | The exact literal `NA` survives as present in every flag column and as a `state_code`; `qc/loaders.py` crossed the seam without a Streamlit import | unit + AST | `python3 -m pytest tests/test_absent_sentinel_guard.py tests/test_no_streamlit_in_qc.py -q` | ❌ W0 (guard is new) | ⬜ pending |
| 02-T1 | 02-02 | 2 | INTEG-02 | T-02-06, T-02-07 | A blank cannot satisfy a cross-table match, and one blank cell produces exactly three checks rather than four | unit | `python3 -m pytest tests/test_rules_reference_matches_registry.py tests/test_registry_covers_emitted_ids.py -q` | ✅ exists | ⬜ pending |
| 02-T2 | 02-02 | 2 | INTEG-02 | T-02-06 | Each of the six `.missing` checks detects a blank in three different absence forms; no row is counted by both a match rule and its sibling | unit | `python3 -m pytest tests/test_missing_cross_table.py -q` | ❌ W0 (new) | ⬜ pending |
| 03-T1 | 02-03 | 3 | INTEG-03 | T-02-09, T-02-11 | A colliding header set produces a named finding instead of a duplicate column label and a crashing `.str` accessor | unit | `python3 -m pytest tests/test_column_collision.py -q` | ❌ W0 (new) | ⬜ pending |
| 03-T2 | 02-03 | 3 | INTEG-03 | T-02-10, T-02-12 | `S3` is registered and emitted with a non-row denominator; `S1` and `S2` no longer hold a second view of the column set; `README.md` and `qc/domain.py` are asserted to agree | unit | `python3 -m pytest tests/test_column_collision.py tests/test_readme_columns_match_domain.py -q` | ❌ W0 (both new) | ⬜ pending |
| 04-T1 | 02-04 | 4 | INTEG-03 | T-02-13, T-02-14 | A non-canonically spelled header resolves to its rule instead of satisfying the schema check and vanishing | integration | `python3 -m pytest tests/test_normalisation_at_load.py -q` | ❌ W0 (new) | ⬜ pending |
| 04-T2 | 02-04 | 4 | INTEG-03 | T-02-15, T-02-16 | The rename panel and the report sheet read one session-state entry, so screen and file cannot disagree; the record carries no score weight | AST over `app.py` | `python3 -m pytest tests/ -q` plus the `build_excel_report` and `all_checks` AST assertions in the task's verify block | ✅ exists (suite) | ⬜ pending |
| 04-T3 | 02-04 | 4 | INTEG-03 | T-02-15 | The panel renders, lists only changed headers, is absent for a canonical-header file, and does not move the weighted score | manual | *n/a — `checkpoint:human-verify`, `gate="blocking-human"`; rows 1 and 2 of the Manual-Only table below* | n/a | ⬜ pending |
| 05-T1 | 02-05 | 5 | INTEG-04 | T-02-17, T-02-18, T-02-19, T-02-20 | The widening and the unavailable reference are each a named failing check; the emitted set for each of the three reference states is exact | unit | `python3 -m pytest tests/test_boundary_reference_states.py -q` | ❌ W0 (new) | ⬜ pending |
| 05-T2 | 02-05 | 5 | ENGINE-06 | T-02-21 | Every registered identifier is proven emittable, including `B5`, which needs a second reference-absent scenario | unit | `python3 -m pytest tests/test_registry_covers_emitted_ids.py -q` | ✅ exists (extended) | ⬜ pending |
| 06-T1 | 02-06 | 6 | ENGINE-04 | T-02-24 | `checkpoint:decision`, D-12 one-way gate — no automated verify by design | checkpoint | *n/a — `gate="blocking-human"`* | n/a | ⬜ pending |
| 06-T2 | 02-06 | 6 | ENGINE-03, ENGINE-04 | T-02-22, T-02-23, T-02-25, T-02-26 | One content-identified snapshot per submission; a filename-and-size collision can no longer serve one officer another's data; one transient payload copy per rerun | AST over `app.py` | `python3 -m pytest tests/ -q` plus the four AST assertion blocks in the task's verify block | ✅ exists (suite) | ⬜ pending |
| 06-T3 | 02-06 | 6 | ENGINE-03, ENGINE-04 | T-02-27 | The structural guard fails the moment any consumer reads the wrong frame, a second auto-correct call appears, the bare frame name returns at module scope, or a `run_all` facade is introduced | unit (AST) | `python3 -m pytest tests/test_one_snapshot_guard.py -q` | ❌ W0 (new) | ⬜ pending |
| 06-T3-manual | 02-06 | 6 | ENGINE-04 | T-02-23 | A generated `eha_guid` survives a rerun and matches the downloaded corrected file | manual | *n/a — `<verify><human-check>` inside 06-T3; row 3 of the Manual-Only table below* | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Wave structure:** six plans, six waves, strictly serial. Every plan that registers a new rule
identifier must also add that identifier's row to `app.py`'s sidebar reference table **in the same
commit**, because `tests/test_rules_reference_matches_registry.py` asserts the sidebar and the
registry agree in both directions and turns red the moment a registration lands undocumented. That
makes `app.py` a shared file across plans 02, 03, 04, 05 and 06, and GSD's wave rule requires
same-wave plans to have zero `files_modified` overlap. Serialisation here is a correctness
consequence, not a planning oversight. A registry-driven sidebar would remove the coupling and is
recorded as a possible future improvement, not adopted — it would replace curated officer-facing
prose (Rule 1's table row enumerates all 28 NOT-NULL columns) with registry descriptions, a UI
regression no requirement asks for.

---

## Wave 0 Requirements

Every requirement in this phase depends on test files that do not yet exist, so Wave 0 is
substantial. Carried from `02-RESEARCH.md` § Wave 0 Gaps:

- [ ] `tests/golden_fixture.py` — three-format byte builders. Must write a real SQL `NULL` for a
      logical blank in `.sqlite` but `""` in `.csv`/`.xlsx`, or the fixture cannot reproduce
      INTEG-01 at all. Must `CREATE VIEW master_list_settlement_update_view` and
      `mlos_takeoffpoint_view`, since `load_view()` reads named views, not tables.
- [ ] `tests/test_golden_three_format_parity.py` — ENGINE-06's assertion
- [ ] `tests/test_absent_sentinel_guard.py` — D-05's required standing test: `"NA"` survives as
      present in every flag column **and** as `state_code`; lowercase `"na"` is not swept up
- [ ] `tests/test_column_collision.py` — `S3` detection. Colliding headers cannot be expressed
      through the row-dict fixture, so this needs direct DataFrame construction
- [ ] `tests/test_one_snapshot_guard.py` — D-15's AST guard over `app.py`
- [ ] Extend `tests/fixtures.py` — the existing 10-row fixture has **no genuinely blank
      cross-table cell** (row 2 "Bravo" is mismatched-but-non-blank), so the six `.missing`
      checks would run without ever being proven to detect a blank.
      **Method changed during planning (plan 01, planner decision 5):** the fix is two *new*
      builders, `build_mlos_fixture_with_blanks` and `build_takeoff_fixture_with_blanks`, each with
      its own row-by-row docstring map. The existing 10-row builders are **not** modified. Adding
      rows to the shared fixture would change `Total Rows` for every check in every layer and
      invalidate the frozen baseline wholesale. Pitfall 2's substance is satisfied; its suggested
      method is not, deliberately.
- [ ] Extend `tests/test_registry_covers_emitted_ids.py` — a second scenario for `B5`, which only
      emits when the boundary reference is absent, a state the shared fixture never reaches
- [ ] Rewrite `tests/test_extraction_parity.py` — its five per-layer functions fail on a bare
      length mismatch the moment the nine new identifiers register.
      **Method settled during planning (plan 01, planner decision 4):** rescope the comparison to
      the *intersection* of the frozen baseline's identifiers and the live registry; require any
      identifier the engine emits but the baseline lacks to be registered, so a stray unregistered
      check still fails; and declare each identifier whose value Phase 2 deliberately moves in one
      table with its requirement and decision reference (populated with Rule 1's corrected
      `Failing Rows` of 2 and `Fail %` of `20.0%`, both measured during planning). **Plan 01 is the
      only plan that edits this file** — plans 02 through 06 assert their new identifiers in their
      own new test files. Without that scoping the file would be shared across four plans.
- [ ] Update `app.py`'s sidebar rules-reference tables — required by
      `tests/test_rules_reference_matches_registry.py`. **Split across plans by design:** each
      plan that registers an identifier adds that identifier's sidebar row *in the same commit*,
      because the guard asserts the sidebar and the registry agree in both directions. Plan 02
      adds the six `.missing` rows, plan 03 adds `S3`, plan 05 adds `B4` and `B5` plus the About
      blurb's boundary range.
- [ ] `tests/test_normalisation_at_load.py` — new (plan 04). Proves the F7 contrast: a header
      spelled `Takeoffpoint` satisfies `S1` and skips its rules before normalisation, and resolves
      to them after. Not in `02-RESEARCH.md`'s original Wave 0 list; added because `qc/loaders.py`'s
      extraction makes the load path testable for the first time.
- [ ] `tests/test_boundary_reference_states.py` — new (plan 05). The assumption-delta companion
      invariant: exact emitted check set per reference state.
- [ ] `tests/test_readme_columns_match_domain.py` — new (plan 03). D-20's structural backstop,
      adopted rather than left as `02-RESEARCH.md` Priority 5's "optional cheap addition".
- [ ] `qc/loaders.py` — new (plan 01). Not a test artifact, but a Wave 0 dependency for ENGINE-06:
      without the pure loaders extracted out of `app.py`, the golden fixture cannot round-trip real
      bytes through the real loaders, because `app.py` cannot be imported outside a Streamlit
      runtime. Phase 1's D-08 parked this extraction for this phase.

**Do NOT touch:** `tests/baseline/qc_baseline.json`, `tests/baseline/capture_baseline.py`,
`tests/test_baseline_records_the_duplicate_ids.py`. All three carry explicit docstring language
forbidding regeneration. They are the permanent numeric record of Phase 1's F3 defect (40 emitted
checks, 31 distinct identifiers) and keep passing unchanged because they assert facts about the
frozen JSON, not about live `qc/` code.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The on-screen "Columns renamed at load" panel renders and lists only changed headers | INTEG-03 (D-11) | Streamlit UI render; `qc/` is import-guarded against Streamlit so this cannot be asserted in a unit test | Upload an `.xlsx` whose headers include `Ward Code` and `SET_POPULATION`; confirm the expander appears listing exactly those two resolutions, and that a canonical-header file shows no panel |
| The "Columns Renamed" sheet appears in the downloaded QC report | INTEG-03 (D-11) | Requires opening a generated workbook | Download the report for the same file; confirm the sheet exists and matches the on-screen panel |
| A generated `eha_guid` is identical on first render and after a rerun | ENGINE-04 (D-12) | Requires a live Streamlit session and a rerun interaction | Upload a file with an invalid `eha_guid`; note the value on screen; trigger a rerun (widget interaction); confirm the value is unchanged and matches the downloaded corrected file |

The AST guard (`test_one_snapshot_guard.py`) covers the *structural* half of ENGINE-03/04 —
that every consumer reads `mlos_corrected` — but cannot observe an actual rerun, which is why the
third row above stays manual.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — the three checkpoint tasks are exempt by type; every `auto` and `tracer` task carries at least three runnable `<automated>` commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — the longest gap is one checkpoint task
- [x] Wave 0 covers all MISSING references — all nine Wave 0 items are owned by a named task; see the Wave 0 Requirements section above, cross-referenced in the map
- [x] No watch-mode flags — every command is a single-shot `pytest -q` or `python3 -c` / heredoc
- [x] Feedback latency < 5s — full suite measured at ~2s for 34 tests; the phase roughly doubles the count, so ~4s worst case
- [x] No verify command depends on `.venv/` — asserted mechanically across all six plans; zero occurrences inside any `<automated>` body
- [x] Full suite ≥ 34 passing — every plan's suite command carries a floor, rising 34 → 38 → 44 → 53 → 57 → 65 → 74 across the six plans
- [x] Every runnable `<automated>` has a `<fails_when>` sibling — verified mechanically: 58 commands, 58 paired, zero unpaired
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** seeded by `/gsd-plan-phase`; awaiting `/gsd-validate-phase` to set `status: validated`
