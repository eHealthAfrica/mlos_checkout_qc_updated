---
phase: 02-detection-correctness-and-three-format-harness
verified: 2026-09-10T00:00:00Z
status: passed
score: 5/5 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-01-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-01-SUMMARY.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-02-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-02-SUMMARY.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-03-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-03-SUMMARY.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-04-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-04-SUMMARY.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-05-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-05-SUMMARY.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-06-PLAN.md", ".planning/phases/02-detection-correctness-and-three-format-harness/02-06-SUMMARY.md", "README.md", "app.py", "qc/boundary.py", "qc/columns.py", "qc/domain.py", "qc/loaders.py", "qc/mlos.py", "qc/predicates.py", "qc/schema.py", "qc/takeoff.py", "tests/fixtures.py", "tests/golden_fixture.py", "tests/test_absent_sentinel_guard.py", "tests/test_boundary_reference_states.py", "tests/test_column_collision.py", "tests/test_deterministic_order.py", "tests/test_extraction_parity.py", "tests/test_golden_three_format_parity.py", "tests/test_missing_cross_table.py", "tests/test_normalisation_at_load.py", "tests/test_one_snapshot_guard.py", "tests/test_readme_columns_match_domain.py", "tests/test_registry_covers_emitted_ids.py"]
covered_digest: "v1:sha256:1210f3704ee932c14f1ed41985274697baac3280abc403ec1d2df439daa0e922"
behavior_unverified: 1
overrides_applied: 0
human_verification:

  - test: "Upload an MLoS file containing at least one row whose eha_guid is not a valid UUID. Click Run QC, open the Auto Correct tab, note the generated identifier and the rows-fixed count. Trigger a rerun by interacting with any widget (e.g. change the State filter on the Raw Data tab). Then download the auto-corrected Excel file. Finally, re-upload the identical file and click Run QC again in the same session."
    expected: "The generated eha_guid and the rows-fixed count are unchanged after the rerun; the downloaded corrected file carries the same identifier the screen showed; re-uploading the byte-identical file in the same session reproduces the same identifier."
    why_human: "app.py cannot be imported outside a live Streamlit runtime, so no pytest test can drive an actual widget-triggered rerun or open a downloaded workbook. The structural guarantee — that mlos_corrected/autocorrect_log are cached under a sha256 content key and read back unchanged on a cache hit, and that auto_correct_mlos runs exactly once — is proven by tests/test_one_snapshot_guard.py (9/9 passing) and by static/AST inspection of app.py. But ENGINE-04's actual claim is a state-transition/persistence property across a live rerun and a real download, which is exactly the class of truth presence-and-wiring checks cannot see. This is 02-06 Plan's own Task 3 <human-check>, explicitly deferred to end-of-phase UAT per workflow.human_verify_mode: end-of-phase, and it is the one item in this phase's SUMMARYs not yet confirmed by a developer reply (unlike 02-04 Task 3 and 02-06 Task 1, both already confirmed in-session)."
---

# Phase 2: Detection Correctness and Three-Format Harness Verification Report

**Phase Goal:** The same submission produces the same findings whatever format it arrived in, and no check passes merely because a value was absent.
**Verified:** 2026-09-10
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Phase 2 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A pytest suite covers every registered rule, and a golden fixture asserts that the same data exported as `.sqlite`, `.csv` and `.xlsx` produces identical check summaries — including Rule 1's missing-value findings | ✓ VERIFIED | `tests/test_golden_three_format_parity.py::test_three_formats_report_an_identical_check_summary` passes independently re-run; `qc/loaders.py` extracted Streamlit-free (`tests/test_no_streamlit_in_qc.py` green); `vec_is_absent` verified directly: `[None, "", "  ", "null", "None", "NaN", "n/a", "N/A", "-"]` all read absent, `["NA", "na", "N", "0", "Gidan Ali"]` all read present, matching D-04/D-05 exactly |
| 2 | A blank value on either side of a cross-table match (R2, R3, R4, TP2, TP3, TP4) is reported as a failure, never as a match | ✓ VERIFIED | `tests/test_missing_cross_table.py` (9/9 independently re-run) proves exact `(1,3)` failing/total counts for all six `.missing` identifiers, the blank-facing-blank F9 regression, and the D-03 no-double-counted-row disjointness invariant; `qc.canonical_order()` independently confirms exactly 6 `.missing` identifiers registered |
| 3 | Column names resolve from one normalisation performed at load, and the officer is shown which columns were renamed | ✓ VERIFIED | `qc.columns.normalize_columns` called at exactly 3 officer-supplied sites in `app.py` (grep-confirmed at lines 151, 152, 713); `column_renames`/`column_collisions` written and read from session state at 20+ sites; on-screen expander and `build_excel_report`'s conditional "Columns Renamed" sheet both wired to the same session-state map; `S3` registered immediately after `S2` in `qc.canonical_order()` (independently confirmed: `['S1','S2','S3','1','2']`); 02-04 Task 3's four-check live-session verification (panel lists exactly the two changed headers, clean file shows no panel, report sheet matches and is absent for the clean file, score unchanged) was already confirmed pass/pass/pass/pass by the developer in-session, recorded in 02-04-SUMMARY.md |
| 4 | The findings on screen describe the same version of the submission as the downloadable auto-corrected file, and a generated `eha_guid` is identical on first render and on every rerun | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | The structural half is verified: `tests/test_one_snapshot_guard.py` (9/9 independently re-run) proves `auto_correct_mlos` is called exactly once in `app.py`, no bare `mlos_df` name survives at module scope, all five QC call sites and both longitudinal helpers receive `mlos_corrected`, and `mlos_raw` reaches only `{auto_correct_mlos, build_excel_report}`; sha256 content identity (`_file_sha256`/`_submission_identity`) independently confirmed as the sole cache-key mechanism. But the runtime claim — that a generated identifier is *actually* identical after a live Streamlit rerun and matches the downloaded file — is a state-persistence property no pytest test exercises (app.py cannot be imported outside a Streamlit runtime). See Human Verification below. |
| 5 | A boundary-reference fallback to the full national set appears to the officer as a warning rather than silently widening B1 | ✓ VERIFIED | `tests/test_boundary_reference_states.py` (independently re-run, part of the 60/60 passing in the combined re-run) proves all three reference states by exact set-equality: state-matched emits `{B0,B1,B2,B3,B4}` with B4 PASS; widened emits the same five with B4 FAIL naming both B1 and B2; unavailable emits exactly `{B0,B5}`. `qc.canonical_order()` independently confirmed boundary order `['B0','B1','B2','B3','B4','B5']`; sidebar (`grep -c "^| B4 |" app.py` = 1, same for B5) and `README.md` (B4/B5 each appear 3+ times) both documented |

**Score:** 5/5 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `qc/domain.py` | `ABSENCE_SENTINELS` constant | ✓ VERIFIED | exists, used by `vec_is_absent` |
| `qc/predicates.py` | `vec_is_absent` | ✓ VERIFIED | exact behavior confirmed independently |
| `qc/loaders.py` | pure, Streamlit-free loaders + `load_submission` | ✓ VERIFIED | exists; `test_no_streamlit_in_qc.py` green |
| `qc/mlos.py` | Rule 1 rebuilt, R2/R3/R4 + `.missing` siblings | ✓ VERIFIED | confirmed via registry and test re-run |
| `qc/takeoff.py` | TP2/TP3/TP4 + `.missing` siblings | ✓ VERIFIED | confirmed via registry and test re-run |
| `qc/columns.py` | `normalize_name`/`normalize_columns` | ✓ VERIFIED | exists, wired at 3 load sites |
| `qc/schema.py` | `S3` registered | ✓ VERIFIED | `canonical_order()[:3] == ['S1','S2','S3']` |
| `qc/boundary.py` | `B4`/`B5` registered | ✓ VERIFIED | confirmed via registry and 3-state test |
| `tests/golden_fixture.py` | 3-format byte builders | ✓ VERIFIED | exists, exercised by parity test |
| `tests/test_golden_three_format_parity.py` | ENGINE-06 harness | ✓ VERIFIED | 1/1 passing |
| `tests/test_absent_sentinel_guard.py` | D-05 standing guard | ✓ VERIFIED | passing (part of combined re-run) |
| `tests/test_missing_cross_table.py` | INTEG-02 proof | ✓ VERIFIED | 9/9 passing |
| `tests/test_column_collision.py` | INTEG-03 engine proof | ✓ VERIFIED | passing (part of combined re-run) |
| `tests/test_readme_columns_match_domain.py` | D-20 backstop | ✓ VERIFIED | exists, part of full suite |
| `tests/test_normalisation_at_load.py` | F7 contrast test | ✓ VERIFIED | passing (part of combined re-run) |
| `tests/test_boundary_reference_states.py` | INTEG-04 3-state proof | ✓ VERIFIED | passing (part of combined re-run) |
| `tests/test_one_snapshot_guard.py` | D-15 structural guard | ✓ VERIFIED | 9/9 passing |
| `README.md` | B4/B5 documented, State filtering rewritten | ✓ VERIFIED | grep-confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `qc/domain.py ABSENCE_SENTINELS` | `qc/predicates.py vec_is_absent` | `qc/mlos.py` Rule 1 mask | ✓ WIRED | `Rule1` failing rows 2/10 confirmed against unmodified fixture in prior plan evidence; predicate values independently reproduced |
| `qc.loaders.load_submission` | three format writers | `tests/golden_fixture.py` | ✓ WIRED | golden parity test passes round-tripping real bytes |
| `app.py get_uploaded_data` | `qc.loaders.load_submission` | caching wrapper delegation | ✓ WIRED | `test_no_streamlit_in_qc.py` + AST checks confirm no loader defs remain in `app.py` |
| `qc.columns.normalize_columns` | `st.session_state['column_renames'/'column_collisions']` | 3 load sites | ✓ WIRED | grep-confirmed at lines 151, 152, 713; session keys written/read 20+ times |
| `st.session_state['column_collisions']` | `run_schema_qc(collisions=...)` | `S3` | ✓ WIRED | line 770 confirmed |
| `qc/boundary.py` fallback flag | `B4` check dict | pre-reassignment capture | ✓ WIRED | 3-state test confirms exact emitted sets |
| `st.session_state['mlos_corrected'/'autocorrect_log']` | 5 QC call sites, longitudinal helpers, download | `test_one_snapshot_guard.py` | ✓ WIRED | 9/9 guard tests independently re-run passing |
| `_submission_identity` (sha256) | `get_uploaded_data` cache key, `qc_cache_key`, `submitted_key` | content-identity | ✓ WIRED | `_file_sha256`/`_submission_identity` confirmed as sole `getvalue()` call sites |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `python3 -m pytest tests/ -q` | 108 passed | ✓ PASS |
| vec_is_absent exact contract | inline `python3 -c` per plan's own acceptance criterion | matches `[T,T,T,T,T,T,T,T,T,F,F,F,F,F]` | ✓ PASS |
| Registry size and boundary order | `qc.canonical_order()` | 49 identifiers, `B0..B5` in order | ✓ PASS |
| `.missing` identifier count | `qc.canonical_order()` | 6 | ✓ PASS |
| Combined targeted re-run (boundary/one-snapshot/collision/normalisation/sentinel) | `pytest tests/test_boundary_reference_states.py tests/test_one_snapshot_guard.py tests/test_column_collision.py tests/test_normalisation_at_load.py tests/test_absent_sentinel_guard.py -q` | 60 passed | ✓ PASS |
| Debt-marker scan | `grep -n -E "TBD\|FIXME\|XXX"` across all phase-2-touched `qc/` files and `app.py` | no matches | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; verification is via pytest and static/AST inspection only.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| INTEG-01 | 02-01 | Rule 1 identical across `.sqlite`/`.csv`/`.xlsx` | ✓ SATISFIED | golden parity test + `vec_is_absent` verified |
| INTEG-02 | 02-02 | Blank cannot satisfy cross-table match | ✓ SATISFIED | 9/9 `test_missing_cross_table.py` |
| INTEG-03 | 02-03, 02-04 | Column names normalised once at load; renames reported | ✓ SATISFIED | wiring + registry + confirmed live-session checks (02-04 Task 3) |
| INTEG-04 | 02-05 | Boundary-reference fallback visible, not silent | ✓ SATISFIED | 3-state test, sidebar + README docs |
| ENGINE-03 | 02-06 | Screen/checks/download describe same version | ⚠️ PARTIAL (structural VERIFIED, runtime behavior human_needed) | AST guard proves wiring; live rerun/download identity unconfirmed |
| ENGINE-04 | 02-06 | Auto-correct runs exactly once; `eha_guid` stable | ⚠️ PARTIAL (structural VERIFIED, runtime behavior human_needed) | same as above; D-12 confirmed by developer at Task 1 checkpoint |
| ENGINE-06 | 02-01, 02-05 | pytest suite covers every rule + golden fixture | ✓ SATISFIED | golden parity test + registry-coverage guard reaching all 49 identifiers including B5 |

All seven requirement IDs declared in PLAN frontmatter (INTEG-01–04, ENGINE-03, ENGINE-04, ENGINE-06) are present in `.planning/REQUIREMENTS.md`, each marked `Complete` and mapped to `Phase 2`. No orphaned requirements found — cross-referencing REQUIREMENTS.md's traceability table against Phase 2's declared set shows exact agreement (no additional Phase-2-mapped IDs exist beyond these seven).

### Anti-Patterns Found

None. Scanned all `qc/` modules touched this phase (`domain.py`, `predicates.py`, `loaders.py`, `mlos.py`, `takeoff.py`, `schema.py`, `columns.py`, `boundary.py`) and `app.py` for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero matches.

### Human Verification Required

#### 1. ENGINE-04 rerun-stability of a generated `eha_guid`, and its identity in the downloaded corrected file

**Test:** Upload an MLoS file containing at least one row whose `eha_guid` is not a valid UUID. Click Run QC, open the Auto Correct tab, and note the generated identifier and rows-fixed count. Trigger a rerun by interacting with any widget (e.g. change the State filter on the Raw Data tab). Then download the auto-corrected Excel file and confirm the same row carries the same identifier. Finally, re-upload the identical file and click Run QC again in the same session.

**Expected:** The identifier and rows-fixed count are unchanged after the rerun; the downloaded file's identifier matches what the screen showed; re-uploading the byte-identical file reproduces the same identifier (via D-13's content hash).

**Why human:** `app.py` cannot be imported outside a live Streamlit runtime (its module body calls `st.set_page_config`), so no pytest test can drive an actual widget-triggered rerun, inspect a live session's rendered table, or open a downloaded `.xlsx` workbook. `tests/test_one_snapshot_guard.py`'s 9 tests prove the *structural* guarantee by parsing `app.py`'s source (single `auto_correct_mlos` call, `mlos_corrected`/`autocorrect_log` both written and read, no bare `mlos_df` at module scope) — but ENGINE-04's actual claim is a runtime state-persistence property across a real rerun and a real file download, which presence-and-wiring checks cannot observe. This is exactly 02-06-PLAN.md's own Task 3 `<human-check>` block, explicitly deferred to end-of-phase UAT per this project's `workflow.human_verify_mode: end-of-phase` policy (02-06-SUMMARY.md records this deferral explicitly under "Next Phase Readiness"). It is the one verification item among this phase's several checkpoint/human-check gates that has *not* yet received a developer confirmation reply — unlike 02-04 Task 3's four-check live-session verification (confirmed pass/pass/pass/pass, recorded in 02-04-SUMMARY.md) and 02-06 Task 1's D-12 decision gate (confirmed `CONFIRMED`, recorded in 02-06-SUMMARY.md), both of which are treated as resolved.

### Gaps Summary

No gaps. All five ROADMAP.md Phase 2 success criteria are supported by artifacts that exist, are substantive, are wired, and (where the criterion is a static/structural claim) pass an independently re-run automated test. All seven declared requirements are marked Complete in REQUIREMENTS.md with no orphans. The full test suite (108 tests) passes on independent re-run, matching every SUMMARY's claimed count. No debt markers, stub patterns, or anti-patterns were found in any file this phase touched.

The one open item is not a gap in what was built — it is a runtime behavior (ENGINE-04's rerun-stability and download-identity guarantee for a generated `eha_guid`) that by its nature cannot be exercised by a static test against a Streamlit app whose module body cannot be imported outside a live server. The phase's own plans correctly identified this and deferred it to end-of-phase UAT rather than skipping it silently. Per this project's `workflow.human_verify_mode: end-of-phase` policy, this is the designed point at which that confirmation should be obtained before the phase is considered fully closed out — it is surfaced here rather than assumed.

---

*Verified: 2026-09-10*
*Verifier: Claude (gsd-verifier)*
