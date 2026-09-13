---
phase: 05-submission-record
plan: 01
subsystem: audit-log
tags: [huggingface_hub, threading, streamlit, submission-record, dataset-repo, tdd]

requires:
  - phase: 04-central-deployment-and-officer-identity
    provides: auth.current_officer() (identity accessor), auth.secret() (secrets surface)
  - phase: 03-verdict-and-report-integrity
    provides: qc.report.QcSummary / LayerSummary, the one shared verdict/score/layer computation
provides:
  - "qc/version.py: the single VERSION constant every record's app_version reads from (D-04)"
  - "qc/submission_record.py: pure, network-free record builder (build_record) and record-id/path
    minting (mint_record_id_and_path), projecting QcSummary/officer identity verbatim (D-02..D-04, D-14)"
  - "submission_log.py: the only module importing huggingface_hub -- unconfigured_reason(),
    fire_upload() (daemon thread, no join), get_status() cross-thread status holder (D-05..D-12)"
  - "app.py wiring: the one fire site inside the fresh-run branch only, guarded by _fresh_qc_run
    (D-06); the cached branch reads submission_record_id/path back from session state"
  - "huggingface_hub>=1.30.0,<2.0.0 pinned, package-legitimacy checkpoint approved with evidence"
affects: [05-02-retry-and-guards, 05-03-status-line-and-report-threading, 05-04-live-repo-and-audit03]

actuals:
  tokens: 12784
  tasks: 3
  commits: 3

tech-stack:
  added: ["huggingface_hub>=1.30.0,<2.0.0"]
  patterns:
    - "Pure record builder / thin network uploader split, extending the qc/ + auth.py precedent
      (qc/mail_config.py's purity discipline copied verbatim for qc/submission_record.py)"
    - "Record id/repo path minted synchronously before any network call, threaded through as a
      three-tuple (record_id, repo_path, ts) so the record's own timestamp can never disagree
      with the month folder it sits in"
    - "Daemon background thread with zero st.*/auth calls in the worker; token/repo_id resolved
      on the calling (main script) thread and passed in explicitly, never left to ambient
      HF_TOKEN discovery"
    - "Fire-decision flag (_fresh_qc_run) set only inside the branch that ran the five QC layers,
      read at a single call site immediately after the shared summary is built -- never inside
      the cached branch"

key-files:
  created:
    - qc/version.py
    - qc/submission_record.py
    - submission_log.py
    - tests/test_submission_record_end_to_end.py
    - tests/test_submission_record_builder.py
    - tests/test_submission_record_path.py
  modified:
    - app.py
    - requirements.txt
    - tests/test_environment_pins.py

key-decisions:
  - "Package-legitimacy checkpoint (huggingface_hub>=1.30.0,<2.0.0) approved-with-evidence by the
    human on 2026-09-13: 321 releases across ~7 years, ~333M downloads/month per pypistats,
    source github.com/huggingface/huggingface_hub by Hugging Face Inc., a clean network-free
    import proven in a throwaway venv, and the pin range containing the current 1.31.0 release
    with no yanked version selected -- the SUS verdict (too-new, unknown-downloads) disposed of
    as a PyPI metadata false positive, the same disposition Phase 1 recorded for pandas/numpy/pytest."
  - "Task 3's 29 contract tests (builder + path) all passed against the Task 2 implementation
    with zero qc/submission_record.py changes needed -- the tracer's happy-path implementation
    already satisfied the full field-by-field contract; Task 3's value was pinning that contract
    with exact-value assertions (boundary checks_failing cases, JSON round-trip stability, the
    officer-identity exclusion, month-boundary partitioning) rather than discovering new defects."
  - "Test fixtures use example.com (RFC 2606 reserved) instead of ehealthnigeria.org for officer
    email/domain values -- the real org domain tripped tests/test_no_committed_secrets.py's
    organisational-address guard when used as a literal test fixture string."
  - "Tracer feedback gate (05-01 Task 2 -> Task 3): HUMAN_VERIFY_MODE=end-of-phase (config
    default), auto_advance=false, and Task 2's <verify> carries only <automated> entries (no
    <human-check>) -- per checkpoints.md's precedence row 3, the verify commands were re-run,
    confirmed passing, and execution proceeded directly to Task 3 with no checkpoint synthesized."

patterns-established:
  - "Pattern: pure record builder (qc/submission_record.py) + thin network adapter
    (submission_log.py, repo-root sibling of auth.py) -- the only module permitted to import
    huggingface_hub, mirroring auth.py/auth_domain.py's decision-logic-elsewhere split"
  - "Pattern: mint-before-network -- record_id/repo_path/ts are computed synchronously on the
    main thread before fire_upload is ever called, so the id is always known regardless of the
    upload's outcome (D-11's precondition for 05-03's report/email threading)"

requirements-completed: [AUDIT-01, AUDIT-02, AUDIT-05]

coverage:
  - id: D1
    description: "Pure record builder projects QcSummary + officer identity + file identity into
      a plain dict carrying record_schema, app_version, record_id, timestamp_utc, officer_email,
      file identity, verdict_text, weighted_score, achievable_max, and all five layers' checks
      run/failing/distinct-issue-rows in canonical LAYER_ORDER, never recomputing anything"
    requirement: AUDIT-01
    verification:
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py (build_record tests)"
        status: pass
      - kind: unit
        ref: "tests/test_submission_record_builder.py (19 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Record id and Dataset-repo path (records/YYYY/MM/<compact-ts>_<uuid4>.json)
      minted synchronously from one UTC instant before any network call, with the month
      partition and record id provably derived from the same instant and collision-free under
      2,000 same-second concurrent mints"
    requirement: AUDIT-02
    verification:
      - kind: unit
        ref: "tests/test_submission_record_path.py (10 tests)"
        status: pass
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py (mint_record_id_and_path tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The upload runs on a daemon background thread via submission_log.fire_upload,
      fired exactly once per fresh QC run (never from the cached replay branch), the worker
      makes zero st.*/auth calls, the token is always passed explicitly to HfApi (never ambient
      discovery), and no parent_commit keyword is ever supplied"
    requirement: AUDIT-05
    verification:
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py::test_fire_upload_configured_spawns_daemon_thread_and_records"
        status: pass
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py::test_app_py_has_exactly_one_fire_upload_call_site"
        status: pass
      - kind: other
        ref: "python3 -c ast-walk wiring check (no st./auth. attribute access inside _upload_with_bounded_retry; no parent_commit string in submission_log.py)"
        status: pass
    human_judgment: false
  - id: D4
    description: "When MLOS_LOG_TOKEN or MLOS_LOG_REPO is unset, no thread is spawned, no network
      call is attempted, and unconfigured_reason() names the missing secret(s)"
    requirement: AUDIT-05
    verification:
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py::test_fire_upload_unconfigured_returns_none_and_records_zero_calls"
        status: pass
      - kind: unit
        ref: "tests/test_submission_record_end_to_end.py::test_unconfigured_reason_names_missing_secret"
        status: pass
    human_judgment: false
  - id: D5
    description: "huggingface_hub>=1.30.0,<2.0.0 package-legitimacy verdict reviewed and approved
      by a human before installation, on independently-verified evidence"
    verification: []
    human_judgment: true
    rationale: "A package-legitimacy checkpoint is gate=blocking-human by design -- it exists
      specifically because a human, not an automated check, must weigh the SUS verdict's
      evidence and decide whether to trust the dependency before it is installed."

duration: 55min
completed: 2026-09-13
status: complete
---

# Phase 5 Plan 1: Submission Record Summary

**Pure submission-record builder plus a daemon-thread huggingface_hub uploader, wired into
app.py's fresh-run branch only, proven end to end by a tracer and pinned field-by-field by 43
new tests.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-12T20:24:48Z (context gathering) / this execution resumed from Task 1's
  checkpoint on 2026-09-13
- **Completed:** 2026-09-13
- **Tasks:** 3 (Task 1 checkpoint approval, Task 2 tracer, Task 3 contract tests)
- **Files modified:** 9 (6 created, 3 modified)

## Accomplishments

- `qc/version.py` holds the single `VERSION` constant (`"0.5.0"`) every submission record's
  `app_version` field reads from, with no import of any kind.
- `qc/submission_record.py` is a pure, Streamlit- and network-free module exporting
  `RECORD_SCHEMA = 1`, `mint_record_id_and_path()` and `build_record()`. The record projects
  `qc.report.QcSummary`, `auth.current_officer()`'s dict and a file-identity dict into a plain,
  JSON-serialisable dict with exactly the fields D-02/D-03/D-04 specify, never recomputing a
  verdict, score or layer count.
- `submission_log.py` (repo root, sibling of `auth.py`) is the only module in the repository
  permitted to import `huggingface_hub`. `fire_upload()` spawns a daemon thread that uploads the
  record via `HfApi.upload_file`, deliberately omitting the `parent_commit` keyword; the worker
  makes zero `st.*`/`auth` calls, resolving `token`/`repo_id` on the calling thread instead.
  `unconfigured_reason()` names the missing secret(s) when `MLOS_LOG_TOKEN`/`MLOS_LOG_REPO` are
  unset; `get_status()` reads a lock-guarded, capped in-process status holder.
- `app.py` gained exactly one `submission_log.fire_upload(` call site, inside the fresh-run
  branch and guarded by a `_fresh_qc_run` flag set only there; the cached branch reads the
  record id/path back from session state and never fires. CRLF line endings preserved throughout.
- `huggingface_hub>=1.30.0,<2.0.0` is pinned in `requirements.txt` and installed
  (`1.31.0` resolved), following the human's `approve` on Task 1's package-legitimacy checkpoint.
- 43 new tests across three new test files plus two new environment-pin tests: the suite grew
  from 346 to 391 passing tests, with no reduction anywhere.

## Task Commits

Each task was committed atomically, following RED-then-GREEN for the TDD-marked tracer task:

1. **Task 1: Confirm huggingface_hub is the real Hugging Face client** — checkpoint, no
   commit (approval recorded below); package installed into `.venv` after approval.
2. **Task 2: One finished QC run becomes one record on the Hub** (tracer, TDD):
   - RED: `f43afe1` — `test(05-01): add failing test for submission record end-to-end path`
     (14 tests, confirmed failing against stub modules: NotImplementedError / missing app.py
     wiring, no collection errors)
   - GREEN: `a9d28d3` — `feat(05-01): submission record builder and daemon-thread uploader`
     (all 14 tracer tests pass; full suite 362/362)
3. **Task 3: The record's full contract** (TDD): `19e3d77` — `test(05-01): pin the full
   submission record contract with exact-value tests` (29 new tests, all pass against the Task 2
   implementation with zero production-code changes; full suite 391/391)

**Plan metadata:** commit follows this SUMMARY.

_Tracer feedback gate (between Task 2 and Task 3): re-ran Task 2's `<verify>` commands (all
`<automated>`, no `<human-check>`) — all passed, so per checkpoints.md's precedence row 3
(interactive, `end-of-phase`, automated-only verify) execution proceeded directly to Task 3 with
no checkpoint synthesized._

## Files Created/Modified

- `qc/version.py` — the single `VERSION` constant (D-04)
- `qc/submission_record.py` — pure record builder + id/path minting (D-02, D-03, D-04, D-14)
- `submission_log.py` — the only `huggingface_hub`-importing module; daemon-thread uploader,
  status holder, unconfigured-reason detector (D-05 to D-12)
- `app.py` — imports `qc.submission_record`/`submission_log`; the one fire site in the fresh-run
  branch; the cached branch's id/path read-back (CRLF preserved)
- `requirements.txt` — `huggingface_hub>=1.30.0,<2.0.0` pin with explanatory comment
- `tests/test_environment_pins.py` — two new tests: both-bounds declaration + installed-version
  satisfies the pin
- `tests/test_submission_record_end_to_end.py` — the tracer's own 14-test proof
- `tests/test_submission_record_builder.py` — 19 tests pinning `build_record`'s full field
  contract
- `tests/test_submission_record_path.py` — 10 tests pinning `mint_record_id_and_path`'s path/id
  shape and collision-freedom

## Decisions Made

**Package-legitimacy checkpoint (Task 1): approved-with-evidence.**
Verdict: `approved-with-evidence`. Date: 2026-09-13.
Evidence presented and accepted:
- 321 releases since `0.0.1` across roughly seven years of continuous publishing
  [pypi.org/project/huggingface-hub/, PyPI registry `pypi.org/pypi/huggingface_hub/json`].
- 332,924,511 downloads/month, 52,177,555/week [pypistats.org].
- Source repository `github.com/huggingface/huggingface_hub`, published by author
  "Hugging Face, Inc." — not an unfamiliar or personal account.
- The pin range `>=1.30.0,<2.0.0` sits inside the published release range and selects no
  yanked version; `1.31.0` (current) resolved and installed cleanly.
- A clean, network-free import was independently verified in a throwaway venv this research
  session (`socket.socket.connect` monkey-patched to raise on any real connection attempt;
  import and `HfApi()` instantiation both succeeded with zero connection attempts).
The seam's `SUS` verdict (reasons: `too-new`, `unknown-downloads`) is disposed of as a PyPI
metadata false positive — the same disposition STATE.md records for Phase 1's pandas, numpy and
pytest SUS verdicts. Nothing was installed before this approval was given.

**Task 3 produced zero production-code changes.** All 29 new contract tests
(`test_submission_record_builder.py` + `test_submission_record_path.py`) passed against the
Task 2 implementation on first run (after two test-authoring fixes described below) — the
tracer's happy-path implementation already satisfied the full D-02/D-03/D-04/D-14 field
contract. This is a legitimate TDD outcome the plan itself anticipated ("Expect the
implementation to need at most small corrections here"); Task 3's value is in pinning that
contract with boundary and edge-case assertions a single happy-path example cannot exercise
(all-failing layers, zero-row source tables, JSON round-trip stability at both `0.0` and
`achievable_max`, 2,000 same-second concurrent mints, month-boundary partitioning).

**Two test-authoring corrections made during Task 3, before any assertion was accepted as
genuinely red or green:**
1. Initial test fixtures used synthetic, unregistered `Rule#` identifiers (e.g. `"MLoSp0"`).
   `QcSummary.verdict_text` (via `n_fail` → `all_checks` → `sort_by_registry`) requires every
   check's `Rule#` to resolve through the real `qc` registry's `canonical_order()`, so these
   raised `KeyError` unrelated to anything the test was trying to prove. Fixed by drawing
   `Rule#` values from `qc.results.canonical_order()`/`get_rule()`, filtered per layer.
2. Initial officer test fixtures used `ehealthnigeria.org` (the real organisational domain),
   which tripped `tests/test_no_committed_secrets.py`'s organisational-address guard when
   present as a literal string in a tracked test file. Fixed by switching to `example.com`
   (RFC 2606/6761 reserved), matching that guard's own documented exclusion.

## Deviations from Plan

None — plan executed exactly as written. The two test-authoring corrections above were fixes to
this plan's own new test files (never to production code) made during test authoring, before
any test run was evaluated as the RED or GREEN gate result — not deviations from the plan's
specified behavior.

## Issues Encountered

None beyond the two test-authoring corrections documented above under Decisions Made.

## Known Stubs

None. `submission_log.RETRY_DELAYS = ()` and the worker's single-attempt failure branch are
explicitly scoped as this task's intended stopping point per the plan's own action text ("In
this task the failure branch may be a single attempt that sets 'failed'; 05-02 expands it into
D-07's bounded retry schedule") — not a stub standing in for unfinished work, but the plan's
deliberate boundary between this plan and 05-02's expansion.

## User Setup Required

None — no external service configuration required in this plan. `MLOS_LOG_TOKEN` and
`MLOS_LOG_REPO` remain unset until plan 05-04 creates the Dataset repo and its two secrets at a
human checkpoint; until then, `unconfigured_reason()` correctly reports the unconfigured state
and no upload is attempted.

## Next Phase Readiness

- The end-to-end path (build record → mint id/path → fire daemon upload) is proven and fully
  tested; 05-02 can expand the single-attempt failure branch into D-07's bounded retry schedule
  and add the append-only AST guard (D-16) without touching the proven core.
- 05-03 can thread `record_id` into `qc.report.build_workbook`/`build_email_subject_and_body`
  (D-11) and render the three-state status line (D-09) / unconfigured banner (D-10) using
  `submission_log.get_status()` and `unconfigured_reason()`, both already in place.
- 05-04's human checkpoints (Dataset repo creation, D-13; the two Space secrets, D-15; the live
  AUDIT-03 concurrency proof, D-08) are unblocked by this plan and not gated on anything further
  from it.
- No blockers. Full suite green at 391/391; `app.py` still CRLF-terminated and compiles.

## Self-Check: PASSED

- `qc/version.py`, `qc/submission_record.py`, `submission_log.py` — FOUND
- `tests/test_submission_record_end_to_end.py`, `tests/test_submission_record_builder.py`,
  `tests/test_submission_record_path.py` — FOUND
- Commit `f43afe1` — FOUND in `git log --oneline --all`
- Commit `a9d28d3` — FOUND in `git log --oneline --all`
- Commit `19e3d77` — FOUND in `git log --oneline --all`
- `python3 -m pytest tests/ -q` — 391 passed
- `app.py` — CRLF line terminators confirmed via `file app.py`

---
*Phase: 05-submission-record*
*Completed: 2026-09-13*
