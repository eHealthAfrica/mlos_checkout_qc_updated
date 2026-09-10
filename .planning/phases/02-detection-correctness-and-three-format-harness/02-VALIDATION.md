---
phase: "2"
slug: "detection-correctness-and-three-format-harness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
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
| INTEG-02 | A blank cannot satisfy R2/R3/R4/TP2/TP3/TP4 | unit | `python3 -m pytest tests/test_extraction_parity.py -q` (rewritten per Priority 2) | ❌ W0 (rewrite + fixture rows) |
| INTEG-03 | Normalisation once at load, `S3` collision, rename reporting | unit | `python3 -m pytest tests/test_column_collision.py -q` | ❌ W0 (new) |
| INTEG-04 | `B4` / `B5` make the fallback and the absent reference visible | unit | `python3 -m pytest tests/test_extraction_parity.py -q` (rewritten) + dedicated fallback-trigger test | ❌ W0 (rewrite + new) |
| ENGINE-03 | Displayed rows and computed checks describe one frame | unit (AST over `app.py`) | `python3 -m pytest tests/test_one_snapshot_guard.py -q` | ❌ W0 (new) |
| ENGINE-04 | Auto-correction runs exactly once; `eha_guid` stable per submission | unit (AST, shared guard) | `python3 -m pytest tests/test_one_snapshot_guard.py -q` | ❌ W0 (new, shared with ENGINE-03) |
| ENGINE-06 | Golden fixture: three formats, identical check summaries | integration | `python3 -m pytest tests/test_golden_three_format_parity.py -q` | ❌ W0 (new) |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *pending* | — | — | — | — | — | — | — | — | ⬜ pending |

*Populated after PLAN.md files are written. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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
      checks would run without ever being proven to detect a blank. Update its row-by-row
      docstring map too.
- [ ] Extend `tests/test_registry_covers_emitted_ids.py` — a second scenario for `B5`, which only
      emits when the boundary reference is absent, a state the shared fixture never reaches
- [ ] Rewrite five per-layer functions in `tests/test_extraction_parity.py` — they fail on a bare
      length mismatch the moment the nine new identifiers register
- [ ] Update `app.py`'s sidebar rules-reference tables — required by
      `tests/test_rules_reference_matches_registry.py`

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] No verify command depends on `.venv/`
- [ ] Full suite ≥ 34 passing (the pre-phase baseline)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
