# Phase 5: Submission Record - Research

**Researched:** 2026-09-12
**Domain:** `huggingface_hub` Dataset-repo writes from a Streamlit app, background-thread patterns in Streamlit, git-commit concurrency semantics
**Confidence:** MEDIUM-HIGH overall (HIGH on package version/API signatures — verified this session against the actual installed 1.31.0 source; MEDIUM on Streamlit background-thread safety and undocumented Hub commit rate limits, both flagged explicitly below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Record Contents (AUDIT-01)**

- **D-01:** The officer is identified by **Workspace email only**, read through
  `auth.current_officer()["email"]` (the accessor Phase 4 built for this log; nothing else may
  read `st.user`).
- **D-02:** Beyond the verdict, each record carries a **per-layer summary read from the shared
  `QcSummary`**: the verdict sentence (`verdict_text`), the weighted score, the achievable
  maximum, and for each of the five layers its checks run, checks failing and distinct issue
  rows (null where the layer has no source row count, as Schema does; a layer that did not run
  appears with zero checks). The record **never recomputes** anything the summary already
  derives. Reversibility: costly — the log is append-only.
- **D-03:** The file is identified by its **uploaded filename, the sha256 Phase 2 already
  computes over the uploaded bytes (`_file_sha256`), the MLoS row count, the Takeoffpoint row
  count, and, when a separate Takeoffpoint file was uploaded, that file's filename and sha256**
  (null otherwise).
- **D-04:** Every record carries a **`record_schema` integer (starting at 1) and the app version
  that produced it**, read from a `VERSION` constant in the repository — the Space exposes no
  git sha. Records also carry their UTC timestamp in ISO 8601.

**Write Path and Timing (AUDIT-02, AUDIT-03, AUDIT-05)**

- **D-05:** Each record is **uploaded directly as its own commit from a background thread** the
  moment the QC run completes, using `huggingface_hub`. Nothing is buffered on the Space's
  ephemeral disk. *Recorded deviation:* `CommitScheduler` was suggested by ROADMAP.md Notes and
  **not chosen** — records sitting in its local buffer are lost on rebuild/kill, and at tens of
  runs/day the per-commit cost it saves is negligible. The planner must not revert to it.
- **D-06:** A record **fires exactly once per fresh QC run**, inside the branch of `app.py` that
  actually runs the five layers and populates session state, and **never in the cached branch**.
- **D-07:** On a failed or slow upload the writer makes **a few bounded retries with backoff,
  about a minute in total, then gives up**: logs server-side (D-12) and stops. No on-disk retry
  queue, no unbounded thread, no exception ever reaches the officer's page. The thread must be a
  daemon so it cannot hold the process.
- **D-08:** AUDIT-03 is a **launch gate**, proven by a pytest test that **skips when no write
  token is present**, spawns many concurrent writers against a **disposable private Dataset
  repo**, then lists the repo and asserts every record landed with a distinct path. Run live once
  at a `checkpoint:human-action` (`blocking-human`); output recorded in the plan summary.
  Network-free unit tests cover record building and filename uniqueness. The disposable repo is
  the test's to create and remove; the **application** code must still contain no delete path
  (D-16).

**Officer-Facing Feedback (AUDIT-05)**

- **D-09:** The officer sees a **quiet three-state status line** near the verdict banner:
  recording in progress, recorded, or could not be saved with "your verdict is unaffected."
  Because the write is in a background thread, the line updates **on the officer's next
  interaction rather than live**. Never blocks, never changes the verdict/score/report.
- **D-10:** When the write token or repo id is **not configured**, the app shows a **persistent
  visible banner** that submission recording is not configured, **QC still runs, nothing is
  recorded** — mirrors Phase 4 D-03.
- **D-11:** The **record id (the JSON filename stem, D-14) is printed on the workbook cover
  beside the generated-at line and in the QC email footer**. The id is minted **before the
  upload starts**, so it is always known regardless of the upload's outcome. Both surfaces
  already read from the shared summary path Phase 3 built; thread the id through that path
  rather than adding a second one.
- **D-12:** When the writer gives up, **only the Space's server-side log learns of it**: the
  record id and the error class, never the record's contents. No line in the QC email.

**Dataset Repo Layout (AUDIT-02, AUDIT-04)**

- **D-13:** The log lives in a **private Dataset repo owned by an eHealth Africa organisation**,
  not a personal account. **A human creates the repo** at a `checkpoint:human-action`
  (`blocking-human`); no task may create it, name it in code, or fabricate its id. Reversibility:
  costly.
- **D-14:** Records are stored at **`records/YYYY/MM/<UTC compact timestamp>_<uuid4>.json`**,
  e.g. `records/2026/09/20260912T101530Z_3f2a….json`. The filename stem is the record id (D-11).
  Reversibility: costly — records already written keep their paths.
- **D-15:** The app receives a **fine-grained Hugging Face token with write access to that one
  Dataset repo only, plus the repo id, as two Space secrets**, read through the same `auth.secret`
  surface as every other credential and never committed. Secret names are the planner's choice
  (e.g. `MLOS_LOG_TOKEN`, `MLOS_LOG_REPO`) and must be added to README §Hugging Face Spaces and
  to the no-committed-secrets guard's awareness.

### Claude's Discretion

- **D-16 (append-only guard, AUDIT-04).** No path to edit or delete a record. Strongly
  recommended: the uploader is create-only with unique names, and a standing AST test in the
  Phases 1–4 idiom asserts tracked source contains no delete call (`delete_file`, `delete_folder`,
  `delete_repo`, delete operations inside `create_commit`, or an upload to an existing path).
  Token scope (D-15) is the second line of defence, not the first.
- **Module boundary.** A pure, Streamlit-free record builder (record dict, record id, repo path)
  unit-tested without a network, and a thin uploader that is the only module importing
  `huggingface_hub`. Whether the uploader lives in `auth.py`'s sibling or its own thin module is
  the planner's call. The record must be built from the `QcSummary` object and
  `auth.current_officer()`, not session state scraps.
- **New dependency.** `huggingface_hub>=1.30.0,<2.0.0`, pinned with an upper bound, with the
  Phase 1 package-legitimacy checkpoint precedent applied.
- **Exact JSON key names, status-line wording, banner wording, the `VERSION` constant's location
  and maintenance, the retry schedule, and the thread implementation.**
- **The no-upload-persistence guard.** The record writer uploads from memory (D-05) and must stay
  inside `tests/test_no_upload_persistence.py`'s scope.
- **Whether the Dataset repo carries a README** describing the record schema. Recommended.
- **An officer navigating away while the upload is in flight.** The daemon thread completes on
  its own; nothing further required.

### Deferred Ideas (OUT OF SCOPE)

- Querying or charting the log inside the app (v2, needs a queryable store).
- `CommitScheduler` batched pushes — the fallback if per-run commit cost ever matters.
- A "submission record: saved / not saved" line in the QC email — revisit if the data team
  cannot read Space logs.
- Officer display name or domain in the record — additive with a `record_schema` bump.
- Per-state folders in the repo — the state is not reliably known at record time.
- Stopping the app when recording is unconfigured — D-10 prefers the banner.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-01 | Each completed QC run records who ran it, when, which file, and the verdict/score | See "Code Examples: Pure Record Builder" and the exact `QcSummary`/`auth.current_officer()` field anchors in "Existing Code Insights" |
| AUDIT-02 | Records written one JSON file per submission to a private HF Dataset repo | See "Standard Stack", "Code Examples: Uploader" — `HfApi.upload_file` with in-memory `bytes`, verified signature |
| AUDIT-03 | Two officers submitting simultaneously both recorded, neither overwritten | See "Concurrency Semantics" — `parent_commit` behavior verified from source; this is the section the AUDIT-03 test must be built against |
| AUDIT-04 | No path to edit or delete a past record | See "Don't Hand-Roll" and "Common Pitfalls: Pitfall 6" — AST guard idiom, token-scope second line of defence |
| AUDIT-05 | A failure or delay writing the record never blocks or slows the verdict | See "Common Pitfalls: Pitfall 1, 2" — Streamlit background-thread constraints, retry-is-not-automatic finding |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Tech stack stays Python 3 + Streamlit; no rewrite.
- Hosting: free tier, Hugging Face Spaces (16GB RAM headroom load-bearing for SQ4/Excel builder —
  unaffected by this phase, which adds one small network call, not a memory-heavy one).
- Storage: Space filesystem is ephemeral — this is exactly why the log goes to a Dataset repo,
  not a local file (D-05).
- Security: no passwords stored; SMTP/other credentials live in Space secrets, never committed —
  the new `MLOS_LOG_TOKEN`/`MLOS_LOG_REPO` secrets must follow the same pattern (D-15).
- Configuration: values that must be tunable without a deploy live in config/secrets — the record
  schema version and retry counts are code, not config, per D-16's discretion list; the two new
  secrets follow the existing `auth.secret()` surface.
- Compatibility: a verdict must not depend on upload format — out of scope for this phase (the
  record is built from the already-format-agnostic `QcSummary`, so no new format-dependence is
  introduced).
- `app.py` is CRLF-terminated by design — any edit to it in this phase must preserve CRLF line
  endings or risk a whole-file-rewrite diff.

## Summary

This phase has one genuinely novel technical risk area (concurrent commits to a Hub Dataset
repo from independent background threads) and one process-integration risk area (running a
background thread safely from inside a Streamlit script run). Both are now grounded in source,
not assumption.

**Concurrency (AUDIT-03):** `HfApi.upload_file()`/`create_commit()` accept an optional
`parent_commit` parameter used purely as an optimistic-concurrency guard — if you pass it and the
branch has moved past that commit, the server rejects with `412`
[VERIFIED: `huggingface_hub` 1.31.0 source, `_commit_api.py`, and the library's own
`test_create_commit_conflict` test]. **If you never pass `parent_commit` — which is D-05's exact
shape — no such check happens**: each call commits against whatever the branch's HEAD is at
request time, and the Hub's own git backend is what serializes the two concurrent POSTs into two
sequential commits, one becoming the parent of the other. Because D-14 gives every record its own
never-before-existing path, there is no file-content conflict for either commit to reject —
this is the mechanism that makes "one file per submission, no `parent_commit`" the correct
concurrency-safe shape, not merely a convenient one. This reasoning is `[CITED]` from the library's
own documented `parent_commit` contract, not independently load-tested against the real Hub this
session — AUDIT-03's live pytest run is exactly the empirical proof this design still needs, and
D-08 already gates it correctly as a `blocking-human` launch gate rather than something research
can certify.

**Retries are not automatic (D-07's necessity, not redundancy):** reading `_commit_api.py`
directly shows the actual commit POST is issued with `retry_on_error=False` by default, and that
flag is **never** passed `True` from `create_commit`'s / `upload_file`'s public call path — it is
only used internally by an unrelated bucket-metadata call
[VERIFIED: `huggingface_hub` 1.31.0 source, `_commit_api.py:1021-1062`]. A transient `429`/`500`/
`503` therefore surfaces immediately as a raised `HfHubHTTPError`, not something the library
retries for you. D-07's bounded-retry-with-backoff is load-bearing, not a belt-and-suspenders
extra.

**Background threading (AUDIT-05, D-05/D-09):** Streamlit's own docs state plainly that attaching
a `ScriptRunContext` to a worker thread (`add_script_run_ctx`) so it can call Streamlit APIs "is
not officially supported and may change in a future version," and separately instruct "ensure
custom threads do not outlive the script thread"
[CITED: docs.streamlit.io/develop/concepts/design/multithreading, fetched this session]. D-05's
daemon thread is explicitly meant to outlive the current script run (that is the whole point of
"fire and forget"), and D-09 needs the status to update "on the officer's next interaction," not
live from inside the thread. **The safe shape is: the uploader thread makes zero `st.*` calls and
never touches `st.session_state` directly.** It only performs the HTTP upload and records its
outcome into a plain, thread-safe, process-global structure keyed by the D-14 record id (already
known before the thread starts, per D-11). The next rerun's main script thread — which has a
valid `ScriptRunContext` — reads that structure and mirrors the outcome into
`st.session_state`, which the status line renders normally. This sidesteps the "not officially
supported" pattern entirely, because that warning is specifically about a thread calling Streamlit
APIs, not one doing pure network I/O.

**Primary recommendation:** build the uploader exactly per D-05 through D-16 with two changes to
verify against research: (1) never pass `parent_commit` for the per-record write path — it is
unnecessary optimistic-concurrency machinery this design does not need and would actively
reintroduce false 412 conflicts between two unrelated concurrent submissions if used incorrectly;
(2) do not let the worker thread call any Streamlit API — hand results back through a plain
thread-safe holder, not `add_script_run_ctx` + direct `session_state` writes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Record building (project `QcSummary`/officer identity into a plain dict) | API/Backend (pure function, no I/O) | — | Same tier as `qc/report.py`'s existing pure builders; must stay Streamlit- and network-free so it is unit-testable exactly like `build_summary` |
| Record id / repo path minting (D-14) | API/Backend | — | Pure string/uuid computation, no I/O; must be synchronous so D-11's cover/email threading works even before the upload resolves |
| Upload transport (network POST to the Hub) | API/Backend (background worker within the same process) | Database/Storage (the Dataset repo receiving the commit) | The only tier boundary the whole phase adds — everything else already exists |
| Thread-safe status holder (D-09's cross-thread handoff) | API/Backend (in-process, not session-scoped) | Frontend Server (the next rerun reads and renders it) | Must NOT be `st.session_state` written from the worker thread — see Summary |
| Officer identity attachment | Frontend Server (`auth.current_officer()`, already resolved by Phase 4) | — | No new identity logic; this phase only consumes the Phase 4 accessor |
| Secrets (`MLOS_LOG_TOKEN`, `MLOS_LOG_REPO`) | Frontend Server (`auth.secret()` surface) | Database/Storage (HF Space secrets store) | Identical tier shape to the existing SMTP/OAuth secrets D-07/D-15 of Phase 4 |
| Append-only enforcement (D-16) | API/Backend (uploader's own call shape) + a standing static-analysis guard | — | Enforced twice: create-only calls at runtime, AST guard at test time; token scope is the human-controlled third layer, not code |
| Dataset repo itself | Database/Storage | — | Git-backed, human-created (D-13), the actual durable store |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `huggingface_hub` | PyPI | 321 releases since `0.0.1`; ~7 years of continuous releases; latest `1.31.0` published 2026-09-10 [VERIFIED: PyPI registry `pypi.org/pypi/huggingface_hub/json`, queried this session] | 332,924,511 / month, 52,177,555 / week [VERIFIED: pypistats.org API, queried this session] | `github.com/huggingface/huggingface_hub`, maintained by "Hugging Face, Inc." [VERIFIED: PyPI registry `info.author`/`project_urls`] | seam returned `SUS` (see below) | **Approved — SUS confirmed as a metadata false positive** |

**Seam output (`gsd_run query package-legitimacy check`):** an `--ecosystem npm` run correctly
returned `SLOP`/`does-not-exist` (this is a PyPI-only package — cross-ecosystem confusion check
passed as expected). An `--ecosystem pypi` run returned `SUS` with reasons `["too-new",
"unknown-downloads"]`. Both signals are false positives for the same reason Phase 1's pandas/
numpy/pytest SUS verdicts were: the seam's "too-new" signal fires on the **latest micro-release's**
publish date (a new patch every few days is normal cadence for an actively-maintained package,
not evidence of the package itself being new), and "unknown-downloads" reflects the seam's PyPI
query not surfacing a download count it does have from pypistats.org (independently queried above:
332M/month). Cross-checked this session: `pip index versions huggingface_hub` lists 200+
historical version strings back to `0.0.1` [VERIFIED: registry query], and the package was
successfully installed and imported this session (see "Environment Availability"). Per the Phase 1
precedent recorded in STATE.md ("all three SUS verdicts confirmed as PyPI metadata false
positives... each publishes a real GitHub repository"), this SUS is disposed of as **Approved with
evidence**, not silently overridden.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `huggingface_hub` — disposed of above with independent
evidence; the planner does not need to add a `checkpoint:human-verify` for it specifically, but
should cite this table's evidence in the plan the same way Phase 1 did.

**Postinstall-script check:** not applicable in the npm sense — `huggingface_hub` ships as a pure
Python wheel with no native extension and no arbitrary install-time script execution comparable to
npm's `postinstall` hook.

**Installation:**
```bash
pip install "huggingface_hub>=1.30.0,<2.0.0"
```

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `huggingface_hub` | `>=1.30.0,<2.0.0` (1.31.0 current on PyPI, released 2026-09-10, `requires_python>=3.10.0`) [VERIFIED: PyPI registry, queried this session] | `HfApi.upload_file` for the per-record write; `create_repo`/`delete_repo`/`list_repo_files` for the AUDIT-03 test | The official, HF-maintained client; no viable alternative exists for talking to a private HF Dataset repo. Compatible with the project's Python 3.11 floor (pandas 3.0.5's own requirement) since `huggingface_hub` only requires `>=3.10.0` |

### Supporting
None — no other new runtime dependency is needed. The retry/backoff loop, the thread, and the
JSON serialization are all trivial enough to hand-write with the stdlib (`time.sleep`,
`threading.Thread`, `json.dumps`, `uuid.uuid4`, `datetime.now(timezone.utc)`) — see "Don't
Hand-Roll" for why adding a retry library here would be over-engineering, not a gap.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct `HfApi.upload_file()` per record, no `parent_commit` | `CommitScheduler` watching a local folder | Rejected by D-05 — records buffered in `CommitScheduler`'s watched folder are lost on Space rebuild/kill; remains documented here only as the fallback if per-commit cost ever becomes a real constraint at much higher submission volume |
| `HfApi.upload_file()` (single-file commit) | `create_commit()` with a list of `CommitOperationAdd` | Only relevant if a future phase batches multiple files per commit; this phase writes exactly one file per call, so the simpler `upload_file` wrapper is the right level of abstraction — it calls `create_commit` internally with a single operation |
| A hand-rolled retry loop (stdlib `time.sleep` + exception catch) | `tenacity` or `backoff` (new dependency) | The retry policy is trivial (D-16 leaves the exact schedule to the planner; D-07 only requires "a few bounded retries... about a minute total") — pulling in a dependency for a ~15-line loop is the kind of over-engineering this project's own Anti-Patterns section already warns against elsewhere |
| A process-global thread-safe dict keyed by record id | A real task queue (Celery, RQ) | Massive overkill for a single-process Streamlit app with dozens of submissions/day; would also require a broker (Redis) this project has no other use for |

## Architecture Patterns

### System Architecture Diagram

```
Officer clicks "Run QC" (fresh-run branch, app.py:590-676)
      |
      v
Five QC layers run -> session_state populated (app.py:664-676, unchanged by this phase)
      |
      v
summary = qc.report.build_summary(...)          (app.py:682-693, unchanged call site)
      |
      +------------------------------------------------------------+
      |                                                             |
      v                                                             v
record = submission_log.build_record(              (existing) verdict banner, workbook,
    summary, auth.current_officer(),                              email render as today,
    file_identity, record_schema=1, version=VERSION)               PLUS the record id (D-11)
      |            (pure, network-free, unit-testable)             threaded through
      v
record_id, repo_path minted synchronously (D-14) -- known immediately,
before any network call is attempted
      |
      v
submission_log.fire_upload(record, record_id, repo_path)   -- spawns a daemon thread
      |                                                     -- (D-05, D-06: only in the
      |                                                        fresh-run branch)
      v
[background thread -- zero st.* calls]
  HfApi(token=auth.secret("MLOS_LOG_TOKEN")).upload_file(
      path_or_fileobj=json.dumps(record).encode(),
      path_in_repo=repo_path, repo_id=auth.secret("MLOS_LOG_REPO"),
      repo_type="dataset")
  -- bounded retry w/ backoff on HfHubHTTPError (D-07) --
  writes outcome ("recorded" | "failed: <class>") into a thread-safe
  holder keyed by record_id -- NEVER writes st.session_state directly
      |
      v
[next rerun, main script thread -- has a real ScriptRunContext]
  status line (D-09) reads the holder by record_id, mirrors outcome
  into st.session_state, renders one of three states
```

A reader can trace the primary path end to end: QC completes -> a pure record is built from
`QcSummary`+identity -> an id is minted before any network happens -> a daemon thread performs the
one HTTP commit with its own bounded retry -> the thread hands its outcome back through a
plain in-process structure, never through Streamlit's own session API -> the next page render
picks that outcome up.

### Recommended Project Structure

```
qc/
├── submission_record.py     # NEW, pure: build_record(), mint_record_id_and_path()
│                             #   no `import streamlit`, no `import huggingface_hub`
submission_log.py             # NEW, thin: the ONLY module importing huggingface_hub;
                              #   fire_upload() (spawns the daemon thread), the retry loop,
                              #   and the thread-safe outcome holder
tests/
├── test_submission_record_builder.py     # AUDIT-01/D-01..D-04, network-free
├── test_submission_record_path.py         # D-14 path/filename shape + uniqueness
├── test_no_delete_in_submission_log.py    # D-16 AST guard (create-only calls)
├── test_submission_record_id_threading.py # D-11: cover/email carry the id
└── test_audit03_concurrent_writes.py       # D-08: skips if no live token; creates/
                                             #   deletes its OWN disposable repo
```

### Pattern 1: Pure Record Builder, Thin Network Uploader (extends the `qc/`+`auth.py` precedent)

**What:** `qc/submission_record.py` takes only `QcSummary`, the officer dict from
`auth.current_officer()`, and the file-identity tuple, and returns a plain, JSON-serializable
`dict` plus a `(record_id, repo_path)` pair — no Streamlit, no network, no `huggingface_hub`
import. `submission_log.py` is the only module that imports `huggingface_hub`; it takes the
already-built record and id/path, and performs the upload in a daemon thread.

**When to use:** This is the same "identity and audit as edge adapters, QC as the core" pattern
`.planning/research/ARCHITECTURE.md` already recommended project-wide — this phase's write is
itself an edge adapter around the pure `QcSummary`, not a new core concern.

**Example — building the record (verbatim field names from `qc/report.py`, read this session):**
```python
# qc/submission_record.py
# Fields below are read from qc/report.py's QcSummary/LayerSummary, verified at
# qc/report.py:168-277 (QcSummary) and qc/report.py:98-164 (LayerSummary) this session.
import uuid
from datetime import datetime, timezone

RECORD_SCHEMA = 1

def build_record(summary, officer, file_identity, version):
    """officer: dict from auth.current_officer() (or None if unconfigured/bypassed --
    the caller must not fire an upload in that case, per D-10's own scope).
    file_identity: {"filename", "sha256", "mlos_rows", "takeoff_rows",
                     "tp_file": {"filename", "sha256"} | None}
    """
    return {
        "record_schema": RECORD_SCHEMA,
        "app_version": version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "officer_email": officer["email"] if officer else None,
        "file": file_identity,
        "verdict_text": summary.verdict_text,        # qc/report.py:270-277
        "weighted_score": summary.weighted_score,     # qc/report.py:206-207
        "achievable_max": summary.achievable_max,     # qc/report.py:210-212
        "layers": {
            name: {
                "checks_run": len(layer.checks),      # qc/report.py:100 (checks field)
                "n_fail": layer.n_fail,                # qc/report.py:112-113
                "distinct_issue_rows": (
                    layer.distinct_issue_rows if layer.ran else None
                ),                                      # qc/report.py:140-144, 106-109
            }
            for name, layer in summary.layers.items()
        },
    }

def mint_record_id_and_path(ts: "datetime | None" = None):
    """D-14: records/YYYY/MM/<UTC compact timestamp>_<uuid4>.json. ts injectable for tests."""
    ts = ts or datetime.now(timezone.utc)
    stem = f"{ts.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex}"
    path = f"records/{ts.strftime('%Y')}/{ts.strftime('%m')}/{stem}.json"
    return stem, path  # stem is the record id (D-11); path is path_in_repo
```

**Example — the uploader (thin, only module importing `huggingface_hub`):**
```python
# submission_log.py
import json
import threading
import time

from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError

import auth

_STATUS = {}          # record_id -> "pending" | "recorded" | "failed"
_STATUS_LOCK = threading.Lock()

def _set_status(record_id, value):
    with _STATUS_LOCK:
        _STATUS[record_id] = value
        # D-09/memory-bound note: cap the holder so a long-lived process doesn't grow forever.
        if len(_STATUS) > 500:
            for k in list(_STATUS)[:250]:
                _STATUS.pop(k, None)

def get_status(record_id):
    with _STATUS_LOCK:
        return _STATUS.get(record_id, "pending")

def _upload_with_bounded_retry(record: dict, path_in_repo: str, record_id: str):
    token = auth.secret("MLOS_LOG_TOKEN")
    repo_id = auth.secret("MLOS_LOG_REPO")
    if not token or not repo_id:
        _set_status(record_id, "failed")   # D-10 already showed the unconfigured banner
        return
    payload = json.dumps(record).encode("utf-8")
    # D-07: a few bounded retries, ~1 minute total, no on-disk queue. Explicit token= on every
    # call -- never rely on ambient HF_TOKEN/~/.cache auto-discovery (D-15).
    delays = [1, 4, 15, 40]   # sums to ~60s across 4 attempts
    last_exc = None
    for attempt, delay in enumerate([0] + delays):
        if delay:
            time.sleep(delay)
        try:
            HfApi(token=token).upload_file(
                path_or_fileobj=payload,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"submission record {record_id}",
                # NOTE: deliberately no parent_commit -- see Concurrency Semantics.
            )
            _set_status(record_id, "recorded")
            return
        except HfHubHTTPError as e:
            last_exc = e
            # D-12: only the class/id is logged server-side, never record contents.
            print(f"submission_log: upload failed for {record_id}: {type(e).__name__}")
    _set_status(record_id, "failed")

def fire_upload(record: dict, path_in_repo: str, record_id: str):
    """D-05/D-06: call this ONLY from the fresh-run branch, exactly once per QC run."""
    _set_status(record_id, "pending")
    t = threading.Thread(
        target=_upload_with_bounded_retry,
        args=(record, path_in_repo, record_id),
        daemon=True,   # D-07: must not hold the process open
    )
    t.start()
```

### Anti-Patterns to Avoid
- **Passing `parent_commit` on the per-record upload:** unnecessary for this design (each path is
  unique) and would reintroduce spurious `412` rejections between two genuinely unrelated
  concurrent submissions if the value passed ever goes stale between read and write.
- **Calling any `st.*` API, or writing `st.session_state` directly, from inside the upload
  thread:** Streamlit's own docs call the context-attachment pattern that would make this "work"
  unsupported and warn against a thread outliving the script run — exactly this thread's job.
- **Relying on `huggingface_hub`'s internal retry for the commit call:** verified this session
  that the commit POST path defaults to no retry; D-07's own retry loop is not redundant.
- **Reading the token via ambient `HF_TOKEN`/`~/.cache/huggingface/token`:** always pass
  `token=auth.secret("MLOS_LOG_TOKEN")` explicitly so a developer's own cached CLI login can never
  silently substitute for the configured secret (D-15's intent).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git commit creation / low-level Hub HTTP protocol | A custom `requests`/`httpx` client hitting `/api/datasets/{repo}/commit/{rev}` directly | `HfApi.upload_file()` | The library already handles ndjson payload construction, auth headers, LFS/Xet content routing, and structured error classes (`HfHubHTTPError` hierarchy) — reimplementing this is exactly the "well-documented, purpose-built tool" case 04-RESEARCH.md already established for OIDC/git-filter-repo |
| Concurrency serialization across independent submissions | An app-level lock/queue/single-writer process to serialize Hub commits | One-file-per-submission with no `parent_commit` (D-05/D-14's existing shape) | The Hub's own git backend already serializes concurrent commit POSTs into sequential commits; building a custom serializer duplicates work the server already does and adds a new single point of failure this Streamlit app has no good place to host |
| Retry/backoff for transient HTTP errors | A retry library (`tenacity`, `backoff`) | A ~15-line stdlib loop (`time.sleep` + `except HfHubHTTPError`) | D-07's own retry policy is intentionally small (a handful of attempts, ~1 minute total) — a dependency for this is the "over-engineering for a trivial problem" pattern the project's existing "Don't Hand-Roll" reasoning (SMTP recipient parsing, 04-RESEARCH.md) already flags |
| Cross-thread status handoff | A custom pub/sub or file-based IPC mechanism | A plain `dict` guarded by a `threading.Lock`, keyed by record id | Single-process, single-machine, low-volume — anything heavier is solving a scaling problem this app does not have |

**Key insight:** everything hard here (Hub commit semantics, HTTP error classification, thread
context rules) already has an authoritative answer either in `huggingface_hub` itself or in
Streamlit's own documented limitations — the actual engineering work is respecting those
documented boundaries (no `parent_commit` misuse, no Streamlit calls from the worker thread), not
building new abstractions.

## Common Pitfalls

### Pitfall 1: Assuming `upload_file`/`create_commit` retries transient errors automatically
**What goes wrong:** A `429`/`500`/`503` from the Hub during a burst of concurrent submissions (or
just ordinary transient network flakiness) propagates immediately as a raised `HfHubHTTPError`,
and if the uploader has no retry loop of its own, D-07's "give up after bounded retries" behavior
never actually retries — it just fails once, immediately.
**Why it happens:** `huggingface_hub`'s own rate-limit docs mention "smart rate limit handling...
version 1.2.0+," which sounds like it covers this call. Reading the source shows that smart
handling applies to file *downloads* (Resolvers) and paginated Hub API calls — not the commit POST
path, which is issued with `retry_on_error=False` by default and never overridden by `create_commit`
or `upload_file`.
**How to avoid:** Implement D-07's retry loop explicitly around the `upload_file` call, catching
`HfHubHTTPError` (and its `RequestException`/network-error siblings) — see "Code Examples" above.
**Warning signs:** The AUDIT-03 concurrency test showing occasional single-shot failures under
load with no retry attempt visible in logs.

### Pitfall 2: Writing to `st.session_state` from the upload thread
**What goes wrong:** Either a `NoSessionContext`/"missing ScriptRunContext" warning (if the thread
is unattached), or — if `add_script_run_ctx` is used to silence it — behavior Streamlit's own docs
say is unsupported and may break in a future release, especially for a thread that (by design,
per D-05/D-07) is meant to keep running after the current script run returns.
**Why it happens:** `add_script_run_ctx` is the answer every search for "call Streamlit from a
thread" turns up, without the caveat that it's meant for threads the *script run itself* waits on,
not for a fire-and-forget background writer.
**How to avoid:** Keep the upload thread Streamlit-free entirely; hand its outcome back through a
plain thread-safe structure (module-level dict + lock) keyed by the record id, and let the next
rerun's main thread read it and set `st.session_state` itself.
**Warning signs:** Console warnings mentioning `ScriptRunContext` during or after a QC run.

### Pitfall 3: Reusing the production `MLOS_LOG_TOKEN` for the AUDIT-03 test's disposable repo
**What goes wrong:** D-15's production token is fine-grained and scoped to write on the one
already-existing Dataset repo — it likely cannot also create and delete a brand-new disposable
repo (repo creation is generally an account/org-level permission, not a per-repo one, since the
repo doesn't exist yet to scope a fine-grained token to). Using it for AUDIT-03 either fails
outright or, worse, is granted broader scope than D-15 intends "just to make the test work."
**Why it happens:** It's the only HF token already in Space secrets, so it's the path of least
resistance to reach for.
**How to avoid:** Use a **separate** secret (e.g. `MLOS_TEST_HF_TOKEN`) with broader "create/delete
repos" permission, scoped to whichever personal or org namespace the test's disposable repos live
under; skip the AUDIT-03 test cleanly (`pytest.mark.skipif`) when that secret is absent, matching
D-08's own "skips when no write token is present" requirement — the requirement was never that it
reuse `MLOS_LOG_TOKEN`.
**Warning signs:** AUDIT-03's own `create_repo` call raising a `403`/permission error even though
`MLOS_LOG_TOKEN` is present and works fine for the production upload path.

### Pitfall 4: Minting the record id only after the upload succeeds
**What goes wrong:** D-11 requires the id on the workbook cover and email footer regardless of the
upload's outcome, and those are rendered synchronously while the upload is still in flight (or has
already failed) in the background thread. If id-minting is placed inside the upload function
instead of before it, the cover/email render before an id exists.
**Why it happens:** It feels natural to generate an id "when you save something," but here saving
is asynchronous and reporting is not.
**How to avoid:** `mint_record_id_and_path()` runs synchronously in the main script thread,
immediately after `summary` is built and before `fire_upload()` is called — exactly as shown in
the Architecture Diagram above.

### Pitfall 5: Firing the upload from the cached branch too
**What goes wrong:** A rerun that hits the `qc_cache_key` cache-hit branch (app.py:573-589) would
fire a second upload for the same submission if the record-fire call is placed above the
if/cached-else split rather than strictly inside the fresh-run `else` branch.
**Why it happens:** The natural-looking insertion point is right after `summary` is built
(app.py:682), which is shared by both branches — but D-06 requires firing exactly once, only on a
genuinely fresh run.
**How to avoid:** Call `fire_upload()` inside the `else:` block that populates session state
(app.py:590-676), not after the shared `summary = qc.report.build_summary(...)` call at line 682.

### Pitfall 6: Treating token scope alone as the append-only guarantee
**What goes wrong:** Relying solely on D-15's write-only fine-grained token to satisfy AUDIT-04,
without a code-level guard, means a future change that calls `delete_file`/an overwrite-shaped
`create_commit` would only be caught if the token happened to lack permission for it — which is
fragile and untestable in CI.
**How to avoid:** D-16's own guidance: the uploader is create-only by construction (unique paths,
D-14), and a standing AST test (the Phases 1–4 idiom, e.g. modeled on
`tests/test_no_committed_secrets.py`'s scan shape) asserts no tracked source calls
`delete_file`/`delete_folder`/`delete_repo`, or constructs a `CommitOperationDelete`, or reuses an
existing path in an `upload_file`/`CommitOperationAdd` call. Token scope is the second line of
defence, exactly as D-16 states.

## Concurrency Semantics (the core of AUDIT-03)

**Verified this session, from `huggingface_hub` 1.31.0's own source and test suite:**

- `create_commit(..., parent_commit=None)` (the default, and what `upload_file` uses unless a
  caller overrides it) sends no `parentCommit` field in the commit payload
  [VERIFIED: `_commit_api.py`'s `_prepare_commit_payload`, read this session — the `parentCommit`
  header key is only set `if parent_commit is not None`].
- When `parent_commit` **is** supplied and the branch has moved since it was read, the server
  rejects with HTTP `412` and the message "The branch was updated since you opened this page.
  Please refresh and try again."
  [VERIFIED: `huggingface_hub`'s own `test_create_commit_conflict` test, read via Context7 this
  session].
- The `parent_commit` docstring itself frames this as *opt-in* protection "especially useful if
  the repo is updated / committed to concurrently" [VERIFIED: docstring text, read this session]
  — implying the *without* case (this design) is not expected to reject concurrent commits for
  drift reasons; it is expected to simply queue/serialize them at the git level.

**What this means for AUDIT-03's test:** two (or twenty) concurrent `upload_file` calls, each to
its own never-before-existing `path_in_repo`, with no `parent_commit`, should each succeed as
independent sequential commits — none should raise `412`, because `412` is only possible when
`parent_commit` is supplied and stale. The realistic failure modes under concurrency are instead:
transient `429`/`503` from the Hub's own request-handling capacity under a sudden burst (handled
by D-07's retry loop, not a design change), or two writers coincidentally minting the identical
`(timestamp, uuid4)` stem — cryptographically negligible given `uuid4`'s 122 bits of randomness.

**What is not independently verified this session:** the exact behavior of the Hub's server-side
git backend under a true simultaneous burst (e.g., whether 20 near-simultaneous POSTs are
processed strictly sequentially, in small batches, or with some the client must retry due to
transient queue contention) was not load-tested against the real Hub in this session — this is
exactly why D-08 correctly requires AUDIT-03 as a **live, blocking-human-gated** pytest run against
a real disposable repo, not something research can certify from documentation alone. The test
should assert two things: (1) every one of N concurrent `upload_file` calls either succeeds or is
retried to success within D-07's bounded window, and (2) `list_repo_files()` afterward shows
exactly N distinct paths under `records/`, with none missing.

## Code Examples

### AUDIT-03 test skeleton (skips cleanly without a live token)
```python
# tests/test_audit03_concurrent_writes.py
import concurrent.futures
import os
import uuid

import pytest

TEST_TOKEN_VAR = "MLOS_TEST_HF_TOKEN"   # separate from the production MLOS_LOG_TOKEN -- see Pitfall 3
TEST_NAMESPACE = os.environ.get("MLOS_TEST_HF_NAMESPACE")  # e.g. "eHealthAfrica" or a personal user

pytestmark = pytest.mark.skipif(
    not os.environ.get(TEST_TOKEN_VAR) or not TEST_NAMESPACE,
    reason=f"{TEST_TOKEN_VAR}/namespace not configured -- AUDIT-03 needs a live Hub token",
)


def test_twenty_concurrent_uploads_all_land_at_distinct_paths():
    from huggingface_hub import HfApi

    token = os.environ[TEST_TOKEN_VAR]
    api = HfApi(token=token)
    repo_id = f"{TEST_NAMESPACE}/mlos-audit03-{uuid.uuid4().hex[:8]}"
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True)
    try:
        paths = [f"records/test/{uuid.uuid4().hex}.json" for _ in range(20)]

        def upload_one(path):
            return api.upload_file(
                path_or_fileobj=b'{"marker": true}',
                path_in_repo=path,
                repo_id=repo_id,
                repo_type="dataset",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            list(pool.map(upload_one, paths))  # raises if any future raised

        landed = set(api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
        for p in paths:
            assert p in landed, f"missing {p}"
    finally:
        api.delete_repo(repo_id=repo_id, repo_type="dataset")
```

### D-11: threading the record id through the workbook cover and email
```python
# qc/report.py -- build_workbook gains a defaulted keyword, exactly as column_renames did (Phase 2)
def build_workbook(summary, mlos_raw, takeoff_df, column_renames=None, record_id=None):
    ...
    meta = [
        ("File",              summary.filename),
        ("Generated At",      datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Record ID",         record_id or "not recorded"),   # NEW row, beside Generated At (D-11)
        ("MLoS Rows",         len(mlos_raw)),
        ("Takeoffpoint Rows", len(takeoff_df)),
        ("Weighted Score",    summary.score_display),
    ]
    # last_meta_row computed from len(meta) as today (app.py:433) -- no hard-coded row index breaks

def build_email_subject_and_body(summary, record_id=None):
    ...
    lines.append(f"Record ID: {record_id or 'not recorded'}")   # beside the existing Generated line
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `CommitScheduler` watching a local buffered folder (ROADMAP.md Notes' original suggestion) | Direct per-record `upload_file`, no local buffer | D-05 (this phase's CONTEXT.md) | Nothing is lost to a Space rebuild/kill between writes; slightly more commits, negligible at this volume |
| `requests`-based HTTP transport inside `huggingface_hub` | `httpx`-based transport | Noted in the library's own migration docs, current as of 1.31.0 | Irrelevant to app code (same public API), but relevant if any test mocks HTTP at the `requests` layer instead of at the `HfApi` method boundary — mock `HfApi.upload_file`/`create_commit` directly, not `requests.post` |
| Assuming automatic retry on 429/500 for any Hub call | Automatic retry documented only for downloads/paginated list calls; commit/upload calls default to `retry_on_error=False` | Confirmed by direct source read this session (1.31.0) | The app's own D-07 retry loop is necessary, not redundant |

**Deprecated/outdated:** none specific to this phase beyond the `CommitScheduler` supersession
already recorded by D-05.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact fine-grained-token permission checkbox needed to let a token create/delete a brand-new repo (for the AUDIT-03 test's disposable repo) was not confirmed against the live token-creation UI this session — only the three coarse roles (`read`/`write`/`fine-grained`) were confirmed from docs text | Common Pitfalls: Pitfall 3 | If the assumed "repos" permission checkbox doesn't exist or is named differently, the human setting up `MLOS_TEST_HF_TOKEN` may need a plain classic `write` token instead of a fine-grained one — a checkpoint:human-action detail, not a design risk |
| A2 | The Hub's server-side git backend serializes truly simultaneous (sub-second) concurrent commit POSTs into sequential commits without rejecting any of them, for distinct never-before-existing paths and no `parent_commit` | Concurrency Semantics | If wrong — e.g. if the server does reject some concurrent commits for an unrelated reason (queue capacity, a per-second commit cap) — AUDIT-03's live test will surface it directly, and D-07's retry loop is the designed mitigation either way; this is exactly why D-08 requires the live proof rather than trusting this reasoning alone |
| A3 | A daemon thread that is mid-upload when the HF Space container is killed/restarted simply loses that one upload (same failure class as any other network error) rather than leaving the Dataset repo in a partially-committed state | Summary / Pitfall discussion | If wrong (e.g., a partially-streamed multipart request somehow left orphaned server-side state), it would be a Hub-side concern outside this app's control either way — no code-level mitigation exists beyond D-07's bounded retry on the next submission |

**If this table is empty:** N/A — three assumptions above. A1 and A2 resolve empirically at the human `checkpoint:human-action` steps already gated by D-08/D-13 (see § Open Questions Q1 and Q2, and `05-04-PLAN.md` Tasks 2 and 3, which record the answers in the plan summary). A3 is a Hub-side behaviour with no code-level mitigation available to this application either way, so it is carried rather than resolved — D-07's bounded retry on the next submission is the designed response whichever way it falls. None blocks writing the plan.

## Open Questions (RESOLVED)

Both questions below are resolved by **assignment to a gate**, not by an answer written here. Each
has an owner, a resolution mechanism, and a named acceptance point at which the answer is produced
and recorded. That is what resolution means for a question whose answer can only come from a live
credential or the live Hub: it is settled when it is handed to the gate that produces the evidence,
and the gate's output — not this section — carries the answer. Neither question blocks planning or
execution; neither is answered yet; both are answered in `05-04-SUMMARY.md`.

1. **Exact fine-grained token checkbox set for repo creation/deletion (AUDIT-03's test token).**
   — **RESOLVED: deferred to `05-04-PLAN.md` Task 2** (`checkpoint:human-action`,
   `blocking-human`), step 7. *Mechanism:* the human minting `MLOS_TEST_HF_TOKEN` reads the live
   token-creation UI and reports which token form was actually required. *Acceptance point:* that
   task's `<verification>` records the answer in `05-04-SUMMARY.md`. *Why the answer changes
   nothing structural:* either way the production token stays fine-grained and scoped to the one
   log repo (D-15) and the test credential stays separate (Pitfall 3) — the open question is which
   form the *test* credential takes, not whether it is separate. Tracked as assumption A1.
   - What we know: coarse roles are `read`/`write`/`fine-grained` [CITED:
     huggingface.co/docs/hub/security-tokens].
   - What is unclear until that gate runs: whether a fine-grained token can be granted "create
     repos" at all, or whether the test must use a plain `write`-role classic token for its own
     disposable-repo lifecycle while the *production* app continues to use a fine-grained,
     single-repo-scoped token per D-15.

2. **Hub's actual behavior under a true sub-second burst of 10-20 concurrent commits to one
   repo (transient 429/503 rate, any queue-capacity rejection distinct from the documented
   `parent_commit`/`412` mechanism).**
   — **RESOLVED: deferred to `05-04-PLAN.md` Task 3** (`checkpoint:human-action`,
   `blocking-human`). *Mechanism:* the live AUDIT-03 pytest run against the real Hub — twenty
   concurrent writers against a disposable private Dataset repo, executed once. *Acceptance point:*
   that task's `<verification>` pastes the run's complete output verbatim into `05-04-SUMMARY.md`
   and calls out whether any writer was throttled, queued, retried or rejected; a failing run
   answers the question as validly as a passing one and is recorded as the answer either way.
   *Why it cannot be answered here:* the per-second commit behaviour is explicitly undocumented and
   stated to change over time, so reasoning about it produces a guess rather than an answer.
   Tracked as assumption A2; D-08 requires this live run for exactly this reason.
   - What we know: no `parent_commit`-based rejection is possible without `parent_commit`
     [VERIFIED, this session]; the general Hub API rate-limit bucket for a Free-tier account is
     1,000 requests/5-minute window [CITED: huggingface.co/docs/hub/rate-limits]; "granular user
     action" limits (repo commits specifically) are explicitly undocumented and stated to change
     over time.
   - What is unclear until that gate runs: whether 20 near-simultaneous commit POSTs to the
     disposable test repo hit any undocumented per-second commit throttle.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `huggingface_hub` | AUDIT-02, AUDIT-03 | Not yet installed in the project's environment; confirmed installable and clean-importing in an isolated venv this session [VERIFIED: installed 1.31.0 in a throwaway venv, imported with `socket.socket.connect` monkey-patched to raise on any real network attempt — import and `HfApi()` instantiation both succeeded with zero connection attempts] | `1.31.0` current on PyPI | None needed — standard `pip install` |
| A live, reachable private HF Dataset repo (production) | AUDIT-02, D-13 | Not yet created — a human creates it at D-13's `checkpoint:human-action` | — | None — this is the deliverable itself |
| `MLOS_LOG_TOKEN` / `MLOS_LOG_REPO` Space secrets | AUDIT-02, D-15 | Not yet set — populated at the same human checkpoint as D-13 | — | None — D-10's unconfigured banner is the designed fallback until they exist |
| A broader-scoped test token (`MLOS_TEST_HF_TOKEN`) + namespace, for AUDIT-03's disposable repo | AUDIT-03 | Not yet created | — | D-08 explicitly requires the pytest to skip cleanly when absent — not a blocker for writing/executing the rest of the plan |

**Missing dependencies with no fallback:**
- The production Dataset repo and its two secrets (D-13/D-15) — expected; this phase's own human
  checkpoints create them.
- The AUDIT-03 test's own token/namespace — expected; D-08 already designs the test to skip
  cleanly without it, deferring the live proof to its own `checkpoint:human-action`.

**Missing dependencies with fallback:**
- `huggingface_hub` itself — trivially installed; confirmed clean import this session.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`pytest>=8.0.0,<10.0.0` per Phase 1 pin, already installed) |
| Config file | `pytest.ini` — `testpaths = tests`, `python_files = test_*.py` |
| Quick run command | `python3 -m pytest tests/test_submission_record_builder.py tests/test_submission_record_path.py tests/test_no_delete_in_submission_log.py tests/test_submission_record_id_threading.py -q` |
| Full suite command | `python3 -m pytest tests/ -q` (346 tests as of Phase 4; this phase adds new files, does not remove existing ones) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-01 (D-01..D-04) | `build_record()` projects exactly the specified fields from a fake `QcSummary`/officer dict, never recomputing | unit, network-free | `pytest tests/test_submission_record_builder.py -x` | ❌ Wave 0 |
| AUDIT-02 (D-14) | `mint_record_id_and_path()` produces `records/YYYY/MM/<stamp>_<uuid4>.json`; two calls in the same second never collide | unit, network-free | `pytest tests/test_submission_record_path.py -x` | ❌ Wave 0 |
| AUDIT-03 | N concurrent `upload_file` calls to a disposable repo all land at distinct paths | **live** — requires a real Hub token; skips cleanly otherwise | `pytest tests/test_audit03_concurrent_writes.py -x` | ❌ Wave 0, run live once at the `checkpoint:human-action` (D-08) |
| AUDIT-04 (D-16) | No tracked source calls a delete-shaped Hub operation | standing AST/grep guard | `pytest tests/test_no_delete_in_submission_log.py -x` | ❌ Wave 0 |
| AUDIT-05 (D-05..D-07, D-09) | Upload runs in a daemon thread; a forced failure leaves `st.session_state` unaffected for the verdict/score, only the status line changes; retry loop makes bounded attempts within ~60s | unit (fake `HfApi`/monkeypatched `upload_file` raising, timing asserted with a mocked clock, not real `sleep`) | `pytest tests/test_uploader_retry_and_thread.py -x` | ❌ Wave 0 |
| D-06 | The cached branch (`qc_cache_key` hit) never calls `fire_upload` | unit (asserts `fire_upload` mock not called on a simulated rerun with matching cache key) | `pytest tests/test_no_fire_on_cached_rerun.py -x` | ❌ Wave 0 |
| D-11 | `build_workbook`/`build_email_subject_and_body` include the record id when passed, and a placeholder string when `None` | unit | `pytest tests/test_submission_record_id_threading.py -x` | ❌ Wave 0 |
| D-10 | Missing `MLOS_LOG_TOKEN`/`MLOS_LOG_REPO` renders the persistent unconfigured banner and never calls `fire_upload` | unit | `pytest tests/test_recording_unconfigured_banner.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command above.
- **Per wave merge:** `python3 -m pytest tests/ -q` (full suite).
- **Phase gate:** full suite green, plus AUDIT-03's live run executed once at its
  `checkpoint:human-action` and its output pasted into the plan summary (D-08).

### Wave 0 Gaps
- [ ] `tests/test_submission_record_builder.py` — covers AUDIT-01/D-01..D-04
- [ ] `tests/test_submission_record_path.py` — covers AUDIT-02/D-14
- [ ] `tests/test_audit03_concurrent_writes.py` — covers AUDIT-03 (live, skip-clean)
- [ ] `tests/test_no_delete_in_submission_log.py` — covers AUDIT-04/D-16
- [ ] `tests/test_uploader_retry_and_thread.py` — covers AUDIT-05/D-05..D-07
- [ ] `tests/test_no_fire_on_cached_rerun.py` — covers D-06
- [ ] `tests/test_submission_record_id_threading.py` — covers D-11
- [ ] `tests/test_recording_unconfigured_banner.py` — covers D-10
- [ ] Framework install: none needed — pytest already present and configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (new surface) | This phase consumes Phase 4's already-resolved identity; it adds no new authentication surface |
| V3 Session Management | no | No new session concept introduced |
| V4 Access Control | yes | The Dataset repo's own write-scope is enforced by the fine-grained `MLOS_LOG_TOKEN` (D-15); the AST guard (D-16) is a second, code-level control against accidental delete/overwrite calls |
| V5 Input Validation | yes | The record is built entirely from already-validated internal objects (`QcSummary`, `auth.current_officer()`, `_file_sha256`) — no new officer-controlled free-text enters the record; `json.dumps` on a plain dict of str/int/float/bool/None needs no additional escaping |
| V6 Cryptography | no new surface | No new cryptographic primitive; the sha256 file-identity hash is Phase 2's existing, unchanged mechanism |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A leaked `MLOS_LOG_TOKEN` granting broader access than intended | Elevation of Privilege | Use a fine-grained token scoped to write on exactly the one Dataset repo (D-15) — never a classic `write`-role token that grants access to every repo the account owns |
| Ambient `HF_TOKEN`/cached CLI login substituting for the configured secret | Spoofing (wrong identity used for the commit) | Always pass `token=` explicitly to `HfApi(...)`/`upload_file(...)` — never rely on `huggingface_hub`'s own environment/`~/.cache` auto-discovery |
| A code path that could edit or delete a past record (AUDIT-04's core threat) | Tampering / Repudiation | Create-only uploader calls with unique paths (D-14) + a standing AST guard (D-16) asserting no delete-shaped call exists anywhere in tracked source, as the second line of defence behind token scope |
| Record contents (settlement/population-adjacent metadata) leaking into a server log on failure | Information Disclosure | D-12 already scopes the server-side failure log to the record id and error class only — never the record's own fields; the uploader's `print`/logging call must not include the `record` dict itself |
| A daemon thread accidentally exposing an unhandled exception to the officer's page | Denial of Service (of the officer's own verdict view) | The retry loop must catch `HfHubHTTPError` (and network exceptions) inside the thread target, never let one propagate out of the thread — an uncaught exception in a `threading.Thread` target does not crash the process, but it does mean the failure would silently never update the status holder unless caught explicitly |

## Sources

### Primary (HIGH confidence)
- `huggingface_hub` 1.31.0 source, installed and read directly this session in an isolated venv:
  `hf_api.py` (`upload_file`, `create_commit`, `create_repo`, `delete_repo`, `list_repo_files`,
  `list_repo_tree` signatures), `_commit_api.py` (`_prepare_commit_payload`, the commit POST's
  `retry_on_error=False` default), `utils/_http.py` (`hf_raise_for_status`'s 429/403/400 branches,
  `http_backoff`'s retry-on-status-codes default), `errors.py` (the full exception class hierarchy).
- PyPI registry (`pypi.org/pypi/huggingface_hub/json`), queried directly this session — version
  `1.31.0`, `requires_python>=3.10.0`, 321 releases, author "Hugging Face, Inc.",
  `github.com/huggingface/huggingface_hub`.
- pypistats.org API, queried directly this session — 332,924,511 downloads/month.
- `pip index versions huggingface_hub`, run this session — full historical version list back to
  `0.0.1`.
- A live falsification test run this session: installed `huggingface_hub` 1.31.0 in a throwaway
  venv, monkey-patched `socket.socket.connect` to raise on any real connection attempt, then
  successfully imported the package and instantiated `HfApi()` with zero connection attempts —
  confirms clean, network-free import.
- Direct codebase reads this session: `app.py:95-134` (`_file_sha256`/`_submission_identity`),
  `app.py:370-693` (sidebar upload, fresh-run vs cached-run branch, `summary` build site),
  `qc/report.py:1-320` (`LayerSummary`, `QcSummary`, `build_summary`), `qc/report.py:365-560`
  (`build_workbook`'s cover metadata block), `qc/report.py:562-649`
  (`build_email_subject_and_body`), `auth.py` (`secret()`, `current_officer()`, `require_login()`),
  `tests/test_no_upload_persistence.py`, `tests/test_no_streamlit_in_qc.py`,
  `tests/test_no_committed_secrets.py`, `requirements.txt`, `README.md:389-437`,
  `.planning/config.json` (`nyquist_validation: true`, `security_enforcement: true`).

### Secondary (MEDIUM confidence)
- `https://huggingface.co/docs/hub/rate-limits` (WebFetch this session) — rate-limit tiers, the
  `RateLimit`/`RateLimit-Policy` headers, the explicit statement that per-action limits (repo
  commits included) are undocumented and change over time.
- `https://huggingface.co/docs/hub/en/security-tokens` (WebFetch this session) — the three token
  roles (`read`/`write`/`fine-grained`); exact fine-grained permission-checkbox granularity for
  repo creation was not captured in the fetched markdown (client-rendered UI detail) — flagged as
  Open Question 1.
- `https://docs.streamlit.io/develop/concepts/design/multithreading` (WebFetch this session) —
  `add_script_run_ctx` pattern explicitly marked "not officially supported," and the instruction
  that custom threads must not outlive the script thread.
- Context7 `/huggingface/huggingface_hub` — `parent_commit` docstring and the library's own
  `test_create_commit_conflict` test demonstrating 412 behavior; `list_repo_tree` signature;
  the HTTPX migration note.
- GitHub issue `huggingface/huggingface_hub#3071` (WebFetch this session) — real-world 429/503
  reports during heavy commit activity, corroborating the "no automatic retry on commit" finding.

### Tertiary (LOW confidence / flagged for validation)
- The exact server-side git-backend behavior under a true sub-second burst of concurrent commits
  (Open Question 2) — reasoned from documented `parent_commit` semantics, not independently
  load-tested against the real Hub this session; AUDIT-03's live pytest run is the actual proof.
- The precise fine-grained-token checkbox set for granting repo-creation permission
  (Open Question 1 / Assumption A1).

## Metadata

**Confidence breakdown:**
- Package version/API signatures (`upload_file`, `create_commit`, error classes): HIGH — read
  directly from the installed 1.31.0 source this session, cross-checked against Context7's
  official-docs mirror.
- Concurrency semantics (no-`parent_commit` behavior under concurrent writers): MEDIUM-HIGH — the
  mechanism is documented and source-confirmed, but the real-Hub outcome under a true burst is not
  independently load-tested this session; this is exactly what D-08's live AUDIT-03 gate is for.
- Streamlit background-threading safety: MEDIUM — official docs explicitly flag the relevant
  pattern as unsupported, which is a strong signal, but no live Streamlit session was exercised
  this session to confirm the recommended alternative (plain thread-safe holder, no `st.*` calls)
  behaves as expected under Streamlit's actual rerun model.
- Package legitimacy: HIGH — PyPI registry, pypistats, and a live clean-import test all
  independently confirm the seam's SUS verdict is a false positive, matching the Phase 1 precedent.
- Hub rate limits specific to commit operations: LOW/undocumented by HF's own admission — treated
  as an open item the live AUDIT-03 test resolves empirically, not something research can certify.

**Research date:** 2026-09-12
**Valid until:** ~14 days (huggingface_hub releases new versions every few days per its own PyPI
history; re-verify signatures if this research goes stale before execution).
