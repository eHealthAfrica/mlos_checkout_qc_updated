---
phase: 01-qc-engine-seam-and-pinned-environment
verified: 2026-09-09T21:24:14Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
flagged_prohibitions:
  - statement: "This phase must not quietly repair the defects inside the code it relocates (auto_correct_mlos's F4/F5 defects must survive the move untouched)."
    plan: "01-06"
    verification: judgment
    disposition: "Reviewed directly against qc/autocorrect.py — non-authoritative LLM-judge verdict: satisfied. Flagged per protocol for human confirmation, not silently passed."
adjudication:
  frozen_identifier_count:
    ruling: "29 is correct. D-04 (01-CONTEXT.md) and the plan/roadmap text's stated '27' are a miscount."
    evidence: "canonical_order() on the fully-relocated qc/ package returns 40 entries, all distinct, run directly in this verification session. 40 = 29 frozen + 11 new (11.urban/11.rural/11.scattered + the eight 12.<field> identifiers). The 29-entry FROZEN_IDENTIFIERS list in tests/test_rule_identifiers.py enumerates: MLoS 1-10, 11a, 11b, 13, 14 (14) + Schema S1, S2 (2) + Settlement SQ1, SQ2, SQ2b, SQ3, SQ4 (5) + Takeoffpoint TP2-TP5 (4) + Boundary B0-B3 (4) = 29. Independently corroborated by the frozen pre-extraction baseline (tests/baseline/qc_baseline.json, captured directly from the original app.py before any code moved): tests/test_baseline_records_the_duplicate_ids.py asserts 40 total pre-fix emitted checks and 31 distinct pre-fix identifiers (29 frozen + bare '11' + bare '12' = 31), matching exactly. D-04's '27' undercounts Settlement (4 stated vs the real 5 — SQ2b was missed). This is not a phase-goal gap: the test suite (tests/test_rule_identifiers.py's FROZEN_IDENTIFIERS) protects all 29 real pre-existing identifiers, a superset of the 27 D-04 promised, so the freeze guarantee actually delivered is stronger than what was specified, not weaker. The discrepancy was self-disclosed transparently in the test module docstring and in 01-04-SUMMARY.md's key-decisions, not hidden."
    action_required: "D-04 in 01-CONTEXT.md and any ROADMAP/plan prose repeating '27' should be corrected to '29' for future-phase accuracy (e.g. Phase 2/3 planners reading D-04 verbatim would inherit the wrong count). This is a documentation correction, not a code gap — no gap recorded."
---

# Phase 1: QC Engine Seam and Pinned Environment Verification Report

**Phase Goal:** The rule set has one place to live, one identity scheme, one stable emission order, and one known dependency set — so every later fix is testable and neither the duplicate-numbering nor the unstable-ordering defect can silently reopen.
**Verified:** 2026-09-09T21:24:14Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every check reports a rule identifier that names exactly one check — no two checks share a number (down from 11 checks sharing 2 numbers) | ✓ VERIFIED | `qc.canonical_order()` run directly in this session returns 40 entries, all distinct (`len(order) == len(set(order))`). `qc/mlos.py`'s R11 loop now calls `add(f"11.{col}", ...)` per column (urban/rural/scattered) and R12's loop calls `add(f"12.{col}", ...)` per `YN_NA_COLS` member — no call site anywhere in `qc/` still passes the bare literal `"11"` or `"12"`. `tests/test_rule_identifiers.py::test_no_bare_11_or_12_identifier_remains` and `test_every_registered_identifier_is_distinct` pass. |
| 2 | Importing the rule registry with a duplicated identifier fails immediately with a message naming the collision, and a standing test asserts this | ✓ VERIFIED | `qc/results.py::register()` raises `ValueError(f"Duplicate rule id {id!r}: already registered for layer {existing.layer!r} ({existing.name!r})")` — names the id, the existing layer and the existing name. `tests/test_results_registry.py::test_duplicate_rule_id_raises_at_registration` and `test_duplicate_is_rejected_across_different_layers` (cross-layer case) both pass, run independently in this session. |
| 3 | `import qc` succeeds in an interpreter with Streamlit uninstalled, and a test asserts no module under `qc/` imports streamlit | ✓ VERIFIED | `grep -rn streamlit qc/*.py` returns nothing. `tests/test_no_streamlit_in_qc.py` has both an AST static scan (`test_no_module_under_qc_imports_the_ui_framework`, asserting ≥5 files scanned) and a real subprocess proof that blocks `streamlit` via `sys.meta_path` and imports `qc` successfully (`test_qc_imports_when_the_ui_framework_is_unavailable`). All 4 tests in this file pass, run independently in this session. |
| 4 | A clean `pip install -r requirements.txt` resolves reproducibly to `pandas==3.0.5` with `numpy` explicitly declared and upper-bounded | ✓ VERIFIED | `requirements.txt` contains the exact line `pandas==3.0.5` and `numpy>=2.0.0,<3.0.0`. Installed environment confirmed directly: `python -c "import pandas,numpy; print(pandas.__version__, numpy.__version__)"` → `3.0.5 2.5.3` (numpy within its declared bounds). `tests/test_environment_pins.py`'s 4 tests (exact-pin string match, installed-version match, both-bounds check, every-line-bounded check) all pass. |
| 5 | Two runs over identical data in separate processes emit checks in byte-identical order — the eight Rule 12 profile-flag checks included | ✓ VERIFIED | `qc/domain.py::YN_NA_COLS` is now an ordered tuple (was a set literal). `tests/test_deterministic_order.py` forks three real subprocesses with `PYTHONHASHSEED` explicitly set to `"0"`, `"1"`, `"42"`, runs all five QC layers, and compares raw (undecoded) stdout bytes — both for the raw pre-sort emission (`test_raw_emission_order_is_stable_across_hash_seeds`) and the registry-sorted order (`test_registry_sorted_order_is_stable_across_hash_seeds`). Both pass, run independently in this session. This is the only test shape capable of detecting the original defect (same-process tests cannot vary `PYTHONHASHSEED`), and it was confirmed to be a genuine subprocess fork, not an in-process stand-in. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Plan-Level must_haves (Sampled Across All 6 Plans)

Beyond the five roadmap criteria, each plan's frontmatter `must_haves.truths` were spot-checked against source and test evidence; no divergence found. Representative examples actually verified by reading source, not by trusting SUMMARY.md:

- `qc/__init__.py` imports all six submodules (`schema, mlos, settlement, takeoff, boundary, autocorrect`) so `import qc` alone populates the registry — confirmed by reading the file.
- `app.py` contains zero `def run_*_qc` / `def auto_correct_mlos` definitions — confirmed via `grep -n "def run_\|def auto_correct_mlos" app.py` (no matches); all five QC call sites in `app.py` call `qc.<layer>.run_*_qc(...)` piped through `qc.sort_by_registry(...)` — confirmed by line-level grep.
- Boundary identifiers occupy positions B0-B3 last in `canonical_order()` — confirmed directly: the printed order ends `..., 'B0', 'B1', 'B2', 'B3'`.
- The Takeoffpoint empty-frame early return and the Boundary missing-ward-code early return both survive the move — confirmed by reading `qc/takeoff.py:25-26` and `qc/boundary.py:40-48`, and by `tests/test_extraction_parity.py::test_takeoff_layer_returns_nothing_for_an_empty_frame` / `test_boundary_layer_reports_a_missing_ward_code_column` passing.
- The in-app sidebar rules reference (5 markdown tables in `app.py`) lists the 11 new field-named identifiers and no bare `11`/`12` — confirmed via `grep -n` against `app.py:607-619` and `tests/test_rules_reference_matches_registry.py` (both-direction set-equality against `canonical_order()`) passing.

### must_haves.prohibitions (All 6 Plans)

| Plan | Prohibition | Tier | Disposition |
|------|-------------|------|-------------|
| 01-02 | Relocating a QC function must not silently change any verdict it produces | test | ✓ Enforced — `tests/test_extraction_parity.py` diffs every relocated layer against the frozen pre-extraction baseline field-by-field; passing. |
| 01-03 | The import-boundary guard must not report a passing boundary it never examined | test | ✓ Enforced — `test_no_streamlit_in_qc.py::test_guard_scanned_a_nonzero_number_of_files` asserts a minimum of 5 files scanned; passing. |
| 01-04 | A frozen identifier must not be silently repointed at a different check | test | ✓ Enforced — `test_rule_identifiers.py::test_frozen_identifiers_are_all_still_registered` + `test_extraction_parity.py`'s MLoS baseline diff; passing. |
| 01-06 | The registry must not become a second source of truth that drifts from what the layers actually emit | test | ✓ Enforced — `test_registry_covers_emitted_ids.py` asserts both directions (emitted⊆registered, registered⊆emitted); passing. |
| 01-06 | This phase must not quietly repair the defects it relocates (auto_correct_mlos's F4/F5 must survive untouched) | **judgment** | Reviewed directly against `qc/autocorrect.py`: the `uuid.uuid4()` regeneration on every invalid `eha_guid` row is unchanged and un-cached (F5), and no cache-coherence guard was added (F4). Non-authoritative LLM-judge verdict: **satisfied**. Flagged here for human confirmation per protocol — not silently passed. This matches the orchestrator's declared known-deliberate-non-fix (D-09); Phase 2 owns fixing it. |
| 01-06 | The in-app rules reference must not tell an officer that an identifier means something the engine no longer emits under that identifier | test | ✓ Enforced — `test_rules_reference_matches_registry.py`; passing. |

All test-tier prohibitions have real, currently-passing wired enforcement (confirmed by running the specific tests in this session, not by reading SUMMARY.md). The one judgment-tier prohibition is flagged above per the escalation protocol rather than silently counted as a pass.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | Pinned runtime deps, `pandas==3.0.5` | ✓ VERIFIED | Exact line present; installed env matches. |
| `qc/results.py` | Rule registry, `register()`, `canonical_order()` | ✓ VERIFIED | Present, raises `ValueError` on duplicate, 55 lines. |
| `qc/__init__.py` | Package facade importing all 6 layers, `sort_by_registry` | ✓ VERIFIED | Present, 33 lines, no `run_all()` (per CONTEXT.md discretion note). |
| `qc/domain.py` | Relocated constants, `YN_NA_COLS` as tuple | ✓ VERIFIED | Confirmed tuple, ordered per `FLAG_COLS` convention. |
| `qc/predicates.py` | `pct`, `vec_is_uuid`, `vec_is_editor` | ✓ VERIFIED | Present, imports `domain` directly (not via package `__init__`), avoiding circular import. |
| `qc/schema.py`, `qc/mlos.py`, `qc/settlement.py`, `qc/takeoff.py`, `qc/boundary.py`, `qc/autocorrect.py` | Relocated QC layers + registrations | ✓ VERIFIED | All present, all register expected identifiers, no `import streamlit` anywhere. |
| `tests/test_rule_identifiers.py`, `test_results_registry.py`, `test_no_streamlit_in_qc.py`, `test_deterministic_order.py`, `test_environment_pins.py`, `test_extraction_parity.py`, `test_registry_covers_emitted_ids.py`, `test_rules_reference_matches_registry.py`, `test_baseline_records_the_duplicate_ids.py` | Standing regression guards | ✓ VERIFIED | All present, all read in full, all pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app.py` (5 call sites) | `qc.<layer>.run_*_qc` | direct call, piped through `qc.sort_by_registry` | ✓ WIRED | Confirmed by grep at `app.py:752-797`. |
| `qc/mlos.py`, `qc/settlement.py`, `qc/takeoff.py`, `qc/boundary.py`, `qc/schema.py` | `qc/results.py::register()` | module-level `register(...)` calls at import time | ✓ WIRED | Confirmed by reading every layer file; `import qc` alone populates all 40 registrations. |
| `qc/mlos.py` R12 loop | `qc/domain.py::YN_NA_COLS` | `for col in YN_NA_COLS:` | ✓ WIRED | Ordered tuple, iterated in fixed order; confirmed by reading `qc/mlos.py:206`. |
| `app.py` sidebar reference tables | `qc.canonical_order()` | manually authored markdown, checked by test (not live-rendered from the registry) | ✓ WIRED (test-enforced parity, not live binding) | `test_rules_reference_matches_registry.py` proves set-equality; the tables themselves are still static markdown, so a future rule addition needs both the registration and a manual table edit — this is a maintained-parity design, not a stub, and is explicitly test-gated. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| ENGINE-01 | 02, 03, 04, 05, 06 | Every check carries a rule identifier unique across all layers | ✓ SATISFIED | `canonical_order()` = 40 distinct identifiers; `test_no_bare_11_or_12_identifier_remains`, `test_every_registered_identifier_is_distinct` pass. |
| ENGINE-02 | 03, 06 | Uniqueness enforced at import, standing test asserts it | ✓ SATISFIED | `register()` raises `ValueError` naming the collision; `test_duplicate_rule_id_raises_at_registration`, `test_duplicate_is_rejected_across_different_layers` pass. |
| ENGINE-05 | 02, 03, 04, 05, 06 | All QC layers live in `qc/` with no `import streamlit`, enforced by test | ✓ SATISFIED | `grep -rn streamlit qc/*.py` empty; `test_no_streamlit_in_qc.py` (static + subprocess) passes. |
| ENGINE-07 | 01 | Dependencies pinned with upper bound, `pandas==3.0.5` + explicit bounded `numpy` | ✓ SATISFIED | `requirements.txt` verified; `test_environment_pins.py` passes; live install confirmed `pandas 3.0.5`. |
| ENGINE-09 | 02, 03, 04, 06 | Rule emission order deterministic across restarts | ✓ SATISFIED | `YN_NA_COLS` tuple + registry re-sort; `test_deterministic_order.py`'s 3-seed subprocess byte-comparison passes for both raw and sorted order. |

Cross-referenced against `.planning/REQUIREMENTS.md`: all five requirements are marked `[x]` and mapped "Phase 1 | Complete" with no contradicting or orphaned Phase-1 requirement IDs found (ENGINE-03, ENGINE-04, ENGINE-06 are explicitly `[ ]`/Phase 2, correctly out of scope here).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 14 | `VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS` imported from `qc.domain` but unused anywhere in `app.py` (confirmed via grep — only the import line references them) | ℹ️ Info | Dead import, not a stub or defect. Explicitly acknowledged in `01-06-SUMMARY.md`'s key-decisions as an intentional scope boundary (cleanup of these five names was not named in that plan's action text; removing them would be unrequested scope creep). Does not affect any success criterion. |

No `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or `PLACEHOLDER` markers found in any file modified by this phase (`qc/*.py`, `app.py`, `tests/*.py`). No empty-implementation or hardcoded-stub patterns found; the two `return [], pd.DataFrame()` / `return checks, pd.DataFrame()` early-return matches are legitimate, pre-existing, intentionally-preserved degradation paths (empty Takeoffpoint file, missing `ward_code` column), each covered by its own parity test.

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `.venv/bin/python -m pytest tests/ -q` | `34 passed in 2.46s` | ✓ PASS (run independently in this verification session, once) |
| Targeted re-run of the four load-bearing files (identifiers, registry, no-streamlit, determinism) | `.venv/bin/python -m pytest tests/test_deterministic_order.py tests/test_results_registry.py tests/test_rule_identifiers.py tests/test_no_streamlit_in_qc.py -q` | `15 passed in 2.28s` | ✓ PASS (run independently) |
| Registry composition and order | `python -c "import qc; print(qc.canonical_order())"` | 40 identifiers, all distinct, in the order Schema → MLoS (with 11/12 splits) → Settlement → Takeoffpoint → Boundary | ✓ PASS |
| Installed dependency versions | `python -c "import pandas, numpy; print(pandas.__version__, numpy.__version__)"` | `3.0.5 2.5.3` | ✓ PASS |
| `qc.autocorrect` defects intentionally intact | Read `qc/autocorrect.py` directly | `uuid.uuid4()` regenerated per invalid row, uncached — F4/F5 present as expected | ✓ PASS (confirms D-09 was honored, not silently "fixed") |

The determinism test's subprocess-fork shape (three explicit, differing `PYTHONHASHSEED` values, raw undecoded byte comparison) was read in full and confirmed to be a genuine cross-process proof, not an in-process stand-in that Research Pitfall 2 warns cannot detect this defect.

### Discrepancy Adjudication: 27 vs. 29 Frozen Identifiers

**Ruling: 29 is correct.** `01-CONTEXT.md`'s D-04 and the plan/roadmap prose repeating "27" are a miscount.

Evidence (re-derived independently in this session, not taken from any plan/summary claim):
- `qc.canonical_order()` on the fully-relocated package returns exactly 40 identifiers, all distinct.
- `tests/test_rule_identifiers.py::FROZEN_IDENTIFIERS` enumerates 29 entries: MLoS contributes 14 (`1`-`10`, `11a`, `11b`, `13`, `14`), Schema 2 (`S1`, `S2`), **Settlement 5** (`SQ1`, `SQ2`, `SQ2b`, `SQ3`, `SQ4`), Takeoffpoint 4 (`TP2`-`TP5`), Boundary 4 (`B0`-`B3`). 14+2+5+4+4 = 29.
- 40 (total registered) − 29 (frozen) = 11, matching exactly the 11 new field-named identifiers (`11.urban`, `11.rural`, `11.scattered` + 8 `12.<field>` identifiers).
- Independently corroborated by the frozen pre-extraction baseline captured before any code moved (`tests/baseline/qc_baseline.json`): `tests/test_baseline_records_the_duplicate_ids.py` asserts 40 total pre-fix emitted checks and exactly 31 distinct pre-fix identifiers (29 frozen + bare `"11"` + bare `"12"` = 31) — a second, independently-captured data source agreeing with the 29 count.

D-04's "27" undercounts Settlement by one (it apparently assumed 4 Settlement checks, missing `SQ2b`). This is **not a phase-goal-blocking gap**: the actual test suite protects all 29 real pre-existing identifiers — a superset of the 27 D-04 promised — so the freeze guarantee delivered is stronger than specified, not weaker. The discrepancy was self-disclosed transparently in `tests/test_rule_identifiers.py`'s module docstring and in `01-04-SUMMARY.md`'s key-decisions, and logged as a deviation rather than silently patched over.

**Recommended follow-up (documentation only, not a code gap):** correct D-04 in `01-CONTEXT.md` and any repeated "27" in `ROADMAP.md`/plan prose to "29", so a future phase planner reading D-04 verbatim does not inherit the wrong count.

### Human Verification Required

None. All five roadmap success criteria and all sampled plan-level must_haves have direct, independently-reproduced evidence (source reading + live test execution in this session). The one judgment-tier prohibition (auto_correct_mlos's defects left deliberately intact) is flagged above for awareness per the escalation protocol, but is corroborated by direct code reading and matches the orchestrator's own declared known-deliberate-non-fix list — it does not block phase completion.

### Gaps Summary

No gaps found. All five ROADMAP success criteria are verified against source and passing tests, all five phase requirements (ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-07, ENGINE-09) are satisfied with test evidence, the sole prior deviation (`WINDOWS.md` entry #1, the `VALID_ACC` grep-count acceptance criterion) is confirmed genuinely resolved (`grep -c VALID_ACC app.py` now reports exactly 1, matching the fixed status recorded), and the 27-vs-29 identifier-count discrepancy is adjudicated above as a documentation-only miscount that does not weaken the delivered guarantee.

---

_Verified: 2026-09-09T21:24:14Z_
_Verifier: Claude (gsd-verifier)_
