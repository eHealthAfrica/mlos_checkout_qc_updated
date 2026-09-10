---
phase: 02-detection-correctness-and-three-format-harness
plan: 06
subsystem: qc-engine
tags: [streamlit, session-state, hashlib, ast-guard, engine-03, engine-04, f4, f5]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "qc.columns.normalize_columns at load (plan 04) and B4/B5 boundary reporting (plan 05), both of which this plan's mlos_corrected repointing had to preserve without touching"
provides:
  - "A sha256 content identity (D-13) replacing the filename-and-size tuple at all three key sites: get_uploaded_data's cache key, the Run QC button's submitted_key, and the main body's current-key comparison / qc_cache_key. One helper (_file_sha256) is the only call site of getvalue() on an uploaded file; _submission_identity composes the MLoS and optional Takeoffpoint digests."
  - "mlos_raw and mlos_corrected as two distinct session-state frames (D-14): mlos_raw is written once by get_uploaded_data (post-normalisation, pre-auto-correct); mlos_corrected and autocorrect_log are written once by the QC cache-miss branch and read back on every cache hit, closing F4."
  - "The second auto_correct_mlos call in the Auto Correct tab is deleted (ENGINE-04/F5) -- the tab and its corrected-file download now read the cached mlos_corrected/autocorrect_log instead of regenerating eha_guid values."
  - "Every consumer repointed to mlos_corrected: all five run_*_qc call sites, build_corrected_excel, both longitudinal helpers, the Raw Data tab and its filters, the loaded-file success line, and the report tab's on-screen summary. Only build_excel_report (renamed mlos_as_submitted parameter) still reads mlos_raw, for the as-submitted sheet."
  - "tests/test_one_snapshot_guard.py -- a standing AST guard (9 tests) over app.py asserting no bare mlos_df name survives at module scope, all five QC calls and both longitudinal helpers receive mlos_corrected at their real call sites, the mlos_raw-consumer set is exactly {auto_correct_mlos, build_excel_report}, auto-correction is called exactly once, mlos_corrected/autocorrect_log are both written and read in session state, no run_all() facade exists, and a defensive scanned-count floor."
affects: [03-verdict-and-report-integrity]

actuals:
  tokens: 7862
  tasks: 3
  commits: 4
  plan_head_before: 208e38e

tech-stack:
  added: []
  patterns:
    - "Content-identity cache keys: hashlib.sha256(file_obj.getvalue()).hexdigest() computed by one helper (_file_sha256), composed into a submission-identity tuple (_submission_identity) reused at every site that previously built its own (name, size) tuple. Filename-and-size collisions across officers/submissions are structurally impossible now."
    - "Two-named-frame session-state model: mlos_raw (as-submitted, post-normalisation) and mlos_corrected (post-auto-correct) are cached and read back together, never independently, so a QC cache hit can never serve one frame's rows against the other frame's checks."
    - "AST-over-app.py structural guards, module-scope-filtered: tests/test_one_snapshot_guard.py extends Phase 1's tests/test_no_streamlit_in_qc.py idiom, adding a _module_scope_calls helper that excludes a pure helper's internal delegation to another pure helper from consumer-repointing assertions -- only the real call site in the main script body is checked."

key-files:
  created:
    - tests/test_one_snapshot_guard.py
  modified:
    - app.py

key-decisions:
  - "D-12 confirmed as written (Task 1 checkpoint, developer replied CONFIRMED in-session): a generated eha_guid is a uuid4() computed once per submission and cached for the session, not derived from content. Session-scoped-only identifier stability (not cross-session) is the accepted, one-way consequence -- see 'D-12 Confirmation' below."
  - "build_excel_report's MLoS parameter renamed mlos_df -> mlos_as_submitted (planner clarification): makes the as-submitted intent legible in the function's own signature and gives the AST guard an unambiguous name to check, since D-15's guard treats the producer (auto_correct_mlos) and the report builder as the only two legitimate consumers of the raw frame."
  - "get_uploaded_data's internal parse-then-normalise local was deliberately NOT named mlos_raw (it is named _mlos_parsed) even though it is later written to st.session_state['mlos_raw'] -- the mlos_raw-consumer AST assertion walks the whole file regardless of scope, and a same-named function-local would be indistinguishable from the module-scope mlos_raw the guard exists to isolate."
  - "Dropped the corrected_df/correction_log local aliases introduced in Task 2's first pass through the Auto Correct tab, in favour of reading mlos_corrected/autocorrect_log directly (Rule 1 deviation, see below) -- an alias was functionally correct but defeated Task 3's static guard and weakened auditability of which cached frame the download actually consumes."

patterns-established:
  - "Pattern: one hashing helper, called once per uploaded file per rerun, its result held in a local and threaded through every cache-key site -- never recomputed ad hoc at each site. Prevents both cache-key drift and redundant full-payload byte copies on a memory-constrained free-tier host."

requirements-completed: [ENGINE-03, ENGINE-04]

coverage:
  - id: D1
    description: "Submission identity is a sha256 over the uploaded bytes (both files when a separate Takeoffpoint is supplied), replacing the filename-and-size tuple at all three key sites (D-13)."
    requirement: "ENGINE-03"
    verification:
      - kind: unit
        ref: "tests/test_one_snapshot_guard.py (full suite, 9/9) plus manual regex/AST checks confirming no getattr(uploaded[_tp], \"size\") key remains and hashlib is imported"
        status: pass
    human_judgment: false
  - id: D2
    description: "Session state holds mlos_raw and mlos_corrected under distinct names; the on-screen table, all five QC layers and the auto-corrected download always read mlos_corrected; only the report's as-submitted sheet reads mlos_raw (D-14)."
    requirement: "ENGINE-03"
    verification:
      - kind: unit
        ref: "tests/test_one_snapshot_guard.py::test_five_qc_call_sites_all_receive_the_corrected_frame, ::test_build_corrected_excel_receives_the_corrected_frame, ::test_both_longitudinal_helpers_receive_the_corrected_frame, ::test_raw_frame_reaches_only_the_producer_and_the_report_builder"
        status: pass
    human_judgment: false
  - id: D3
    description: "Auto-correction runs exactly once per submission; the second auto_correct_mlos call (F5) is deleted and the download reads the cached corrected snapshot (ENGINE-04)."
    requirement: "ENGINE-04"
    verification:
      - kind: unit
        ref: "tests/test_one_snapshot_guard.py::test_auto_correct_called_exactly_once, ::test_corrected_frame_and_log_are_both_written_and_read_in_session_state"
        status: pass
    human_judgment: false
  - id: D4
    description: "A generated eha_guid is identical on first render, after a rerun, and in the downloaded corrected file within one live Streamlit session (ENGINE-04's rerun-stability property)."
    requirement: "ENGINE-04"
    verification: []
    human_judgment: true
    rationale: "This property can only be observed by driving a live Streamlit session through an actual rerun and download -- exactly the class of check workflow.human_verify_mode: end-of-phase (config.json, confirmed default) is designed to defer to end-of-phase UAT harvesting rather than an inline browser session mid-plan. The design guarantee is proven by code review and the structural guard: mlos_corrected is cached in st.session_state and re-read unchanged whenever qc_cache_key matches, and qc_cache_key is derived from a deterministic sha256 of the same UploadedFile object's bytes across reruns, so no code path can regenerate eha_guid within a session. Live confirmation is deferred to the phase-level UAT step per the plan's own <human-check> block."
  - id: D5
    description: "D-12 confirmed: a generated eha_guid is a uuid4() computed once per submission and cached, not derived from content."
    verification:
      - kind: manual_procedural
        ref: "Task 1 checkpoint reply, this session: developer replied CONFIRMED"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 6: One Corrected Snapshot, Identified by Content Summary

**Closed ENGINE-03/ENGINE-04 (F4, F5): a sha256 content identity replaces the filename-and-size
cache key everywhere, `mlos_raw`/`mlos_corrected` are two distinct cached frames every consumer
reads correctly, the second auto-correct call is gone, and a 9-test AST guard over `app.py`
keeps it that way.**

## D-12 Confirmation

**Task 1 checkpoint** (`checkpoint:decision`, `gate="blocking-human"`) was presented to the
developer earlier in this session. The developer replied **`CONFIRMED`**.

**Decision recorded:** D-12 stands as written in `02-CONTEXT.md` — a generated `eha_guid` is a
`uuid4()` computed once per submission and cached for the session, not derived from the
submission's content. The accepted, one-way consequence: identifiers are stable within a
session but not across sessions (a Space restart, an idle timeout, or the same file uploaded by
a colleague next month mints different identifiers). No code was written before this
confirmation was recorded, per the checkpoint's own acceptance criteria.

## Performance

- **Duration:** ~50 min
- **Started:** 2026-09-10T17:21:00Z (approx, per STATE.md's prior session timestamp)
- **Completed:** 2026-09-10T18:11:02Z
- **Tasks:** 3 (Task 1 checkpoint confirmation, Task 2 implementation, Task 3 standing guard)
- **Files modified:** 2 (app.py modified, tests/test_one_snapshot_guard.py created)

## Accomplishments

- Content identity (D-13): `_file_sha256` (the sole `.getvalue()` call site on an uploaded file)
  and `_submission_identity` (composing the MLoS and optional Takeoffpoint digests) replace the
  `(name, size)` tuple at all three key sites — `get_uploaded_data`'s cache key, the Run QC
  button's `submitted_key`, and the main body's `_current_key`/`qc_cache_key`.
- Two named frames (D-14): `mlos_raw` (written once by `get_uploaded_data`) and `mlos_corrected`
  + `autocorrect_log` (written once by the QC cache-miss branch, read back on every cache hit).
  This closes F4 — a rerun's cache hit can no longer serve uncorrected rows against corrected
  checks, because both now ride the same cache entry.
- ENGINE-04/F5 closed: the second `auto_correct_mlos` call in the Auto Correct tab is deleted;
  the tab and the corrected-file download now read the one cached snapshot.
- Every real consumer repointed to `mlos_corrected`: the five `run_*_qc` call sites,
  `build_corrected_excel`, both longitudinal helpers, the Raw Data tab and its three filters, the
  loaded-file success line and metrics, and the report tab's on-screen summary rows. Only
  `build_excel_report` (parameter renamed `mlos_df` → `mlos_as_submitted`) still reads
  `mlos_raw`, for the as-submitted sheet.
- No bare `mlos_df` name survives at module scope; no `run_all()` facade was introduced (D-15
  reaffirmed).
- `tests/test_one_snapshot_guard.py`: 9 tests, all passing, structurally guarding the above.

## Task Commits

Each task was committed atomically. Task 1 (checkpoint confirmation) produced no code commit —
the confirmation itself is recorded above.

1. **Task 2: One corrected snapshot per submission, identified by content** — `a4198d0` (fix)
2. **Task 2 follow-up: drop local aliases exposed by Task 3's guard** — `dac37f2` (fix, deviation, see below)
3. **Task 3: The standing one-snapshot guard over app.py** — `f0cc2d9` (test)
4. **Line-ending regression fix** — `90999a6` (style, deviation, see below)

**Plan metadata:** committed separately after this SUMMARY (see below).

## Files Created/Modified

- `app.py` — sha256 content identity, two-frame session-state model, deleted second
  auto-correct call, every consumer repointed, `build_excel_report` parameter renamed.
- `tests/test_one_snapshot_guard.py` — new standing AST guard (9 tests).

## Decisions Made

See `key-decisions` in frontmatter. Summary: D-12 confirmed as written; `build_excel_report`'s
MLoS parameter renamed to `mlos_as_submitted`; `get_uploaded_data`'s internal parse-and-normalise
local deliberately named `_mlos_parsed` (not `mlos_raw`) to keep the AST guard's whole-file
`mlos_raw`-consumer scan unambiguous; local aliases in the Auto Correct tab dropped in favour of
reading the cached names directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dropped `corrected_df`/`correction_log` local aliases in the Auto Correct tab**
- **Found during:** Task 3, while writing the AST guard's `build_corrected_excel`-receives-`mlos_corrected` assertion
- **Issue:** Task 2's first pass read `mlos_corrected`/`autocorrect_log` into local aliases
  (`corrected_df`, `correction_log`) before using them in the Auto Correct tab. This was
  functionally correct — the values were identical — but it meant the tab's actual call,
  `build_corrected_excel(corrected_df)`, no longer named the frame D-14 assigns it in its own
  source text. A guard that checks source-level argument names (as D-15 requires, since app.py
  cannot be imported and value-level tracing is unavailable) cannot see through an alias, so this
  weakened the exact auditability property D-15's structural guard exists to provide.
- **Fix:** Removed the aliases; the tab now reads `mlos_corrected` and `autocorrect_log` directly
  everywhere they are used (the correction-log dataframe, the row/column-count caption, and the
  `build_corrected_excel` call).
- **Files modified:** app.py
- **Verification:** `tests/test_one_snapshot_guard.py` (9/9), full suite (108 passed)
- **Committed in:** `dac37f2`

**2. [Rule 1 - Bug] Restored CRLF line endings in app.py**
- **Found during:** Post-Task-3 review, while computing the plan's realized diff size for the
  `actuals` metric
- **Issue:** `app.py` was committed with CRLF line endings prior to this plan (confirmed: every
  other module in the repo uses plain LF; only app.py is CRLF). The Edit/Write tool operations
  used across Tasks 2 and 3 silently normalised the entire file to LF on first write, so the
  Task 2 commit (`a4198d0`) showed as a ~2,700-line whole-file rewrite in `git diff` against the
  prior commit, even though the actual semantic change was ~130 lines. This directly contradicts
  the plan's own "one file, one coherent, reviewable change" requirement and would make future
  `git blame`/review on this file far harder than necessary.
- **Fix:** Converted the working-tree `app.py` back to CRLF (verified byte-for-byte against the
  pre-plan file with `diff`: only the ~130 genuinely changed lines differ). No behavioural
  change — Python does not care about line-ending style.
- **Files modified:** app.py
- **Verification:** `git diff 208e38e..HEAD -- app.py tests/test_one_snapshot_guard.py` now
  reports 130 + 201 lines changed (the real diff), not a whole-file rewrite; full suite still
  108 passed; `python3 -m compileall -q qc app.py tests` succeeds.
- **Committed in:** `90999a6`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — bug/correctness of the diff and of the guard's
auditability, not of runtime behavior).
**Impact on plan:** Both fixes are necessary corrections surfaced by building the plan's own
standing guard and by preparing this SUMMARY; neither changes behavior beyond what Tasks 2/3
already specified. No scope creep — no rule logic, sidebar reference tables, `LAYER_WEIGHTS`, or
prior-plan code was touched.

## Issues Encountered

None beyond the two deviations above, which were resolved inline.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ENGINE-03 and ENGINE-04 are closed. The full suite is at 108 passed (plan required ≥74).
- **Deferred to end-of-phase UAT** (per `workflow.human_verify_mode: end-of-phase`, the
  project's confirmed default): Task 3's `<human-check>` — live-session confirmation that a
  generated `eha_guid` is unchanged across a Streamlit rerun and matches the downloaded
  corrected file, and that re-uploading an identical file in the same session reuses the same
  identifier. This is the one item this plan could not verify by static analysis or `pytest`;
  it requires a live browser session and is exactly the class of check this project's
  `<verify><human-check>` / end-of-phase harvesting mechanism exists to batch into the phase's
  UAT step rather than pausing mid-plan for. The structural guarantee (cache-hit read-back of
  `mlos_corrected`, deterministic sha256 identity) is proven by `tests/test_one_snapshot_guard.py`
  and code review; only the live-session observation remains open.
- Phase 2 plan 07 (if any remain) or phase close-out can proceed; no blockers introduced.

## Self-Check: PASSED

- `tests/test_one_snapshot_guard.py` exists: FOUND
- `app.py` exists and modified as described: FOUND
- Commit `a4198d0` in history: FOUND
- Commit `dac37f2` in history: FOUND
- Commit `f0cc2d9` in history: FOUND
- Commit `90999a6` in history: FOUND
- `python3 -m pytest tests/ -q`: 108 passed
- `python3 -m pytest tests/test_one_snapshot_guard.py -q`: 9 passed
- `grep -c "auto_correct_mlos" app.py`: 1
- `git status --porcelain qc/autocorrect.py tests/baseline/`: empty

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*
