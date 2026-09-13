---
phase: 05-submission-record
plan: 02
subsystem: audit-log
tags: [huggingface_hub, threading, ast-guard, tdd, submission-record, append-only]

requires:
  - phase: 05-submission-record
    provides: "05-01's submission_log.py worker (fire_upload/_upload_with_bounded_retry/get_status),
      qc/submission_record.py's build_record/mint_record_id_and_path, and app.py's fresh-run-only
      wiring (_fresh_qc_run, the one fire_upload( call site, the cached branch's id/path read-back)"
provides:
  - "submission_log.py: RETRY_DELAYS=(1,4,15,40)/MAX_ATTEMPTS=5 bounded-retry-with-backoff loop
    inside _upload_with_bounded_retry, with injectable sleep=/api_factory= keyword parameters
    (fire_upload passes neither -- production behaviour unchanged); catches
    huggingface_hub.errors.HfHubHTTPError plus a broader Exception so a constructor failure or a
    non-Hub error also leaves a terminal status; the D-12 failure log line stays exactly
    {record id, exception class name} (D-07, D-12, AUDIT-05)"
  - "tests/test_uploader_retry_and_thread.py: 12 tests proving the bounded schedule, exception
    containment, the daemon-thread-through-fire_upload() no-propagation case, the D-12 log-line
    absence assertions and STATUS_CAP, all without a real sleep or a live Hub call"
  - "tests/test_no_fire_on_cached_rerun.py: 9 tests proving app.py's one fire_upload( call site
    is guarded by if _fresh_qc_run:, the cached branch calls nothing in submission_log/
    qc.submission_record and reads submission_record_id back, and the guard itself is proven
    capable of failing on a synthetic hoisted-call source (D-06)"
  - "tests/test_no_delete_in_submission_log.py: 10 tests -- scan_tracked_python(),
    delete_shaped_calls(), overwrite_shaped_uploads(), GUARD_OWN_PATH -- a standing AST guard
    proving zero tracked source calls a delete-shaped or overwrite-shaped operation (D-16,
    AUDIT-04), proven capable of failing on four synthetic delete shapes plus a literal-path
    upload"
affects: [05-03-status-line-and-report-threading, 05-04-live-repo-and-audit03]

actuals:
  tokens: 10850
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Injectable clock/factory keyword parameters (sleep=time.sleep, api_factory=None) on the
      one function that needs a test-controllable retry schedule, defaulted to the real
      implementations so the production call site (fire_upload) is unchanged -- extends 05-01's
      dependency-injection discipline (token/repo_id resolved by the caller, never ambient) to
      the retry loop itself"
    - "AST parent-chain walk (_build_parent_map + _enclosing_ifs) to prove a call site's *nesting*
      inside a specific guard, not merely its presence in the module -- a stronger structural
      proof than the existing call-count-only guards in this codebase, used because D-06's
      requirement is specifically about which branch a call is reachable from"

key-files:
  created:
    - tests/test_uploader_retry_and_thread.py
    - tests/test_no_fire_on_cached_rerun.py
    - tests/test_no_delete_in_submission_log.py
  modified:
    - submission_log.py

key-decisions:
  - "submission_log._upload_with_bounded_retry gained injectable sleep=/api_factory= keyword
    params so RETRY_DELAYS=(1,4,15,40)/MAX_ATTEMPTS=5's bounded-retry schedule, exception
    containment (Hub error hierarchy plus a broader catch for constructor/network failures) and
    D-12's id-and-class-only failure log line are proven without a live Hub call or real sleep;
    fire_upload passes neither kwarg so production behaviour is unchanged."
  - "The one daemon-thread test that must go through the real, public fire_upload() entry point
    (to catch a regression at the thread-construction call site itself) injects the same
    recording clock by overriding _upload_with_bounded_retry's own bound default via
    __defaults__ -- the only way to keep that test from taking a real ~60 seconds, since
    fire_upload's own call site never passes sleep=/api_factory= explicitly."
  - "Tasks 2 and 3 required zero app.py/submission_log.py production changes beyond Task 1's
    retry loop -- app.py's cache/fresh-run split and submission_log.py's create-only upload call
    already satisfied D-06's single-guarded-fire-site and D-16's append-only shape exactly as
    wired in 05-01. Verified by parsing app.py's real AST directly before writing any test."

patterns-established:
  - "Pattern: proving a call site's structural nesting (not just its existence) via an AST
    parent-chain walk -- reusable for any future guard that needs 'this call must be reachable
    only from branch X', as distinct from the existing call-count-only guards in this codebase."

requirements-completed: []

coverage:
  - id: D1
    description: "A failed or slow upload retries on a bounded schedule (RETRY_DELAYS=(1,4,15,40),
      MAX_ATTEMPTS=5, summing to ~60s) then gives up, proven with an injected clock so no test
      spends real wall time waiting"
    requirement: AUDIT-05
    verification:
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_always_failing_double_drives_exactly_max_attempts_calls_and_fails"
        status: pass
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_recorded_sleep_schedule_equals_retry_delays_in_always_failing_case"
        status: pass
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_succeed_on_third_attempt_makes_exactly_three_calls_and_two_sleeps"
        status: pass
    human_judgment: false
  - id: D2
    description: "No exception -- Hub-specific or a plain RuntimeError or a constructor failure --
      ever escapes the worker thread; a terminal status is always set"
    requirement: AUDIT-05
    verification:
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_plain_runtime_error_still_sets_failed_and_raises_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_raising_constructor_still_sets_failed_and_raises_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_fire_upload_daemon_thread_not_alive_after_join_in_always_failing_case"
        status: pass
    human_judgment: false
  - id: D3
    description: "The failure log line names only the record id and the exception's class name --
      never the token, the repo id, the officer email, or the record's file sha256"
    requirement: AUDIT-05
    verification:
      - kind: unit
        ref: "tests/test_uploader_retry_and_thread.py::test_failure_log_line_names_the_record_id_and_error_class_and_nothing_else"
        status: pass
    human_judgment: false
  - id: D4
    description: "The single fire_upload( call site in app.py is guarded by if _fresh_qc_run:; the
      cached-replay branch calls nothing in submission_log or qc.submission_record and still reads
      the record id back from session state -- a rerun or tab switch never writes a duplicate record"
    requirement: AUDIT-04
    verification:
      - kind: unit
        ref: "tests/test_no_fire_on_cached_rerun.py::test_fire_call_is_guarded_by_fresh_qc_run_flag"
        status: pass
      - kind: unit
        ref: "tests/test_no_fire_on_cached_rerun.py::test_cached_branch_calls_nothing_in_submission_log_or_submission_record"
        status: pass
      - kind: unit
        ref: "tests/test_no_fire_on_cached_rerun.py::test_cached_branch_reads_back_the_record_id_from_session_state"
        status: pass
    human_judgment: false
  - id: D5
    description: "A standing AST guard fails the suite if any tracked application source gains a
      delete-shaped call (delete_file/delete_folder/delete_repo/a *Delete commit operation) or an
      overwrite-shaped upload (a literal path_in_repo); the guard scans at least 20 tracked files
      and is proven capable of failing on synthetic offenders"
    requirement: AUDIT-04
    verification:
      - kind: unit
        ref: "tests/test_no_delete_in_submission_log.py::test_scan_tracked_python_reports_zero_offenders"
        status: pass
      - kind: unit
        ref: "tests/test_no_delete_in_submission_log.py::test_delete_shaped_calls_flags_repo_file_deletion"
        status: pass
      - kind: unit
        ref: "tests/test_no_delete_in_submission_log.py::test_overwrite_shaped_uploads_reports_zero_offenders_over_tracked_application_source"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-13
status: complete
---

# Phase 5 Plan 2: Bounded Retry and Append-Only Guards Summary

**submission_log.py's failure branch grew into D-07's bounded retry-with-backoff loop
(RETRY_DELAYS=(1,4,15,40), 60s across 5 attempts) with full exception containment, plus two new
standing AST guards proving app.py fires exactly once per fresh run and that no tracked source
can delete or overwrite a submission record.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-13
- **Completed:** 2026-09-13
- **Tasks:** 3
- **Files modified:** 4 (1 modified, 3 created)

## Accomplishments

- `submission_log._upload_with_bounded_retry` replaced its single-attempt failure branch with
  D-07's bounded retry: `RETRY_DELAYS = (1, 4, 15, 40)` (sums to 60s), `MAX_ATTEMPTS = 5`. Two
  injectable keyword parameters (`sleep=time.sleep`, `api_factory=None`) default to the real
  implementations; `fire_upload` passes neither, so production call behaviour is byte-identical
  to before. Catches `huggingface_hub.errors.HfHubHTTPError` and, in a second broader
  `except Exception`, every other failure (a plain `RuntimeError`, a constructor failure) so no
  path can exit the retry loop without setting a terminal status. The D-12 failure log line stays
  exactly `submission_log: upload failed for {record_id}: {type(exc).__name__}` — asserted via
  `capsys` to exclude the token, repo id, officer email and file sha256 by value, not by
  substring.
- `tests/test_uploader_retry_and_thread.py` (12 tests, new): a `FailingHfApi`-style closure
  factory parameterised by how many attempts fail before success, a `RecordingSleep` clock
  double, and a raising-constructor factory drive every `<behavior>` bullet — exact attempt
  counts, the exact recorded sleep schedule, the immediate-first-attempt boundary, both
  non-Hub-error paths, the log-line content/absence assertions, `STATUS_CAP`, and an AST check
  that the retry loop contains no disk-write call. The one daemon-thread test goes through the
  real, public `fire_upload()` entry point (not just the private retry function) and injects the
  same recording clock by overriding `_upload_with_bounded_retry`'s own bound default via
  `__defaults__`, since `fire_upload` never passes `sleep=`/`api_factory=` explicitly. Full file
  runs in 0.17s — no real sleep is ever taken.
- `tests/test_no_fire_on_cached_rerun.py` (9 tests, new): parses `app.py`'s real AST and, via a
  generic parent-chain walk (`_build_parent_map`/`_enclosing_ifs`), proves the one
  `submission_log.fire_upload(` call site is nested inside `if _fresh_qc_run:` rather than merely
  counting call sites; proves the cache-hit `If` node's body calls nothing in `submission_log` or
  `qc.submission_record` while still reading `submission_record_id` back from session state;
  proves `_fresh_qc_run` is assigned exactly twice (`False`/`True`), with `True` only inside the
  cache `If`'s `orelse`. The guard's own capability to fail is proven on a synthetic source with
  the fire call hoisted above the cache split (05-RESEARCH.md Pitfall 5's exact defect), plus an
  accept-case companion. **No `app.py` changes were needed** — 05-01's wiring already satisfied
  every assertion exactly as written.
- `tests/test_no_delete_in_submission_log.py` (10 tests, new): `scan_tracked_python()` (the
  `tests/test_no_upload_persistence.py` idiom — `git ls-files`-scoped, `(offenders, scanned)`
  shape) combines `delete_shaped_calls()` (matches `delete_file`/`delete_folder`/`delete_repo` or
  any `*Delete`-suffixed commit-operation construction, on the callable's final attribute/name so
  an import alias cannot slip past) and `overwrite_shaped_uploads()` (an `upload_file` call whose
  `path_in_repo` keyword is a plain string literal) over every non-excluded tracked `.py` file.
  The exclusion set — `GUARD_OWN_PATH` and the not-yet-created `tests/test_audit03_concurrent_writes.py`
  (05-04) — is pinned to exactly two members by its own test. Proven capable of failing on four
  synthetic delete shapes and a literal-path upload; proven NOT to flag the shipped, freshly-minted-path
  upload call. 65 tracked `.py` files scanned clean, zero offenders.
- Full suite grew from 391 to 422 passing tests (31 new, 0 removed), all green in ~6.5s.

## Task Commits

Each task was committed atomically, RED-then-GREEN for Task 1's TDD-marked retry loop:

1. **Task 1: Bounded retry, a daemon that cannot leak an exception, and a failure line that says
   nothing** (`tdd="true"`):
   - RED: `7ab3291` — `test(05-02): add failing test for bounded retry, daemon thread and D-12 log line`
     (12 tests written; 8 failed for the right reason — `TypeError: unexpected keyword argument
     'sleep'`/`'api_factory'` against the not-yet-existing parameters, plus the `RETRY_DELAYS`
     contract assertion failing against the empty-tuple stub; 4 passed, one of them — the
     daemon-thread test — vacuously true against `RETRY_DELAYS = ()`, expected and resolved by
     GREEN)
   - GREEN: `072713c` — `feat(05-02): bounded retry with backoff, exception containment, D-12 log line`
     (all 12 tests pass; full suite 403/403)
   - No REFACTOR commit: the GREEN implementation needed no further cleanup.
2. **Task 2: A rerun is not a submission — the cached branch stays empty, provably** (`type="auto"`):
   `f4e0296` — `test(05-02): guard proves the cached branch fires nothing and reads the id back`
   (9 tests, all pass against app.py unmodified; full suite 412/412)
3. **Task 3: The append-only guard — no tracked source can remove or overwrite a record**
   (`type="auto"`): `34813c6` — `test(05-02): append-only guard over every tracked source file
   (D-16, AUDIT-04)` (10 tests, zero offenders over 65 scanned files; full suite 422/422)

**Plan metadata:** commit follows this SUMMARY.

## Files Created/Modified

- `submission_log.py` — `RETRY_DELAYS`/`MAX_ATTEMPTS` module constants; `_upload_with_bounded_retry`
  rewritten as a bounded retry loop with injectable `sleep=`/`api_factory=` parameters, catching
  `HfHubHTTPError` plus a broader `Exception`, emitting the D-12 log line on every failed attempt
- `tests/test_uploader_retry_and_thread.py` — bounded-retry schedule, exception containment,
  daemon-thread-through-`fire_upload()`, D-12 log-line, `STATUS_CAP`, and no-disk-write proofs
- `tests/test_no_fire_on_cached_rerun.py` — the single guarded fire site and the empty cached
  branch, proven via a real AST parent-chain walk over `app.py`
- `tests/test_no_delete_in_submission_log.py` — the standing append-only guard over every
  tracked `.py` file (D-16, AUDIT-04)

## Decisions Made

**`_upload_with_bounded_retry` gained injectable `sleep=`/`api_factory=` keyword parameters,
defaulted to the real implementations.** This is what lets the test suite prove the exact retry
schedule and drive a constructor-raises case without a live Hub call or a real minute of sleeping,
while `fire_upload`'s own call site passes neither kwarg, so production behaviour is unchanged
(the plan's own stated design).

**The one test that must exercise the real, public `fire_upload()` entry point — proving the
daemon flag and no-propagation at the actual thread-construction call site, not just the private
retry function — injects the same recording clock by overriding `_upload_with_bounded_retry`'s
own bound default via `__defaults__`.** Since `fire_upload` never passes `sleep=`/`api_factory=`
explicitly, this is the only way to keep that specific test from taking a real ~60 seconds while
still exercising the actual production entry point rather than only the private function
underneath it. `monkeypatch.setattr` on a function's `__defaults__` attribute is a standard,
automatically-restored technique for this exact situation (injecting a test double behind a
call site that itself takes no test-only parameters).

**Tasks 2 and 3 required zero production changes beyond Task 1's retry loop.** Both new test
files were written directly against 05-01's already-shipped `app.py` wiring and
`submission_log.py` upload call — verified by parsing `app.py`'s real AST before writing a single
assertion, confirming the one `fire_upload(` call site already sits inside `if _fresh_qc_run:`
and the cached branch already reads `submission_record_id` back from session state with zero
calls into either new-phase module. This is a legitimate outcome the plan itself anticipated (its
own action text for Task 2: "Do not modify `app.py` in this task... the correct response is to
fix `app.py`'s structure... not to weaken the assertion") — the structure needed no fixing.

## Deviations from Plan

None — plan executed exactly as written. Task 2 and Task 3 producing zero production-code changes
was the plan's own anticipated (and here, confirmed) outcome for wiring already laid down in
05-01, not a deviation.

## Issues Encountered

One test-authoring correction, made before any test run was evaluated as a RED or GREEN gate
result (not a deviation from planned production behaviour): an initial synthetic-source test for
`delete_shaped_calls`' alias-resilience used `from huggingface_hub import CommitOperationDelete as
_Op; _Op(...)` — a bare-name import alias, which the callable-final-component matcher cannot
resolve back to the original `CommitOperationDelete` name (that would require import-alias
resolution the plan never asked for). The matcher's actual, intended resilience is against
*attribute*-access aliasing (`import huggingface_hub as hf; hf.CommitOperationDelete(...)`, where
the final attribute name is unaffected by the module alias) — the test fixture was corrected to
that shape, and passes.

## Known Stubs

None. Every behavior bullet in all three tasks is exercised by a passing test; no placeholder
values or unwired data paths were introduced.

## User Setup Required

None — no external service configuration required in this plan. `MLOS_LOG_TOKEN`/`MLOS_LOG_REPO`
remain unset until 05-04's human checkpoints create the Dataset repo and its secrets; this plan's
own tests never touch a live Hub.

## Next Phase Readiness

- `submission_log.py`'s retry/containment/logging behaviour is complete and fully tested; 05-03
  can build the three-state status line and the workbook/email `record_id` threading on top of
  `get_status()` without touching this plan's code.
- 05-04's live AUDIT-03 concurrency test and the Dataset repo/secrets checkpoints are unblocked;
  when `tests/test_audit03_concurrent_writes.py` is added, its own disposable-repo
  create/delete lifecycle is already accounted for in this plan's exclusion set
  (`AUDIT03_TEST_PATH`), so it will not need to touch `test_no_delete_in_submission_log.py` again.
- AUDIT-04 and AUDIT-05 are NOT yet marked complete in REQUIREMENTS.md — both are declared by
  sibling plans still in flight (05-03 for AUDIT-05, 05-04 for AUDIT-04); `requirements.ready-ids`
  reports 0/2 ready, correctly deferring the mark-complete step to whichever plan finishes last.
- No blockers. Full suite green at 422/422; `app.py` unmodified and confirmed still
  CRLF-terminated.

## Self-Check: PASSED

- `submission_log.py` — FOUND (modified)
- `tests/test_uploader_retry_and_thread.py` — FOUND
- `tests/test_no_fire_on_cached_rerun.py` — FOUND
- `tests/test_no_delete_in_submission_log.py` — FOUND
- Commit `7ab3291` — FOUND in `git log --oneline --all`
- Commit `072713c` — FOUND in `git log --oneline --all`
- Commit `f4e0296` — FOUND in `git log --oneline --all`
- Commit `34813c6` — FOUND in `git log --oneline --all`
- `python3 -m pytest tests/ -q` — 422 passed
- `app.py` — CRLF line terminators confirmed via `file app.py`; byte-identical to before this plan

---
*Phase: 05-submission-record*
*Completed: 2026-09-13*
