# Phase 5: Submission Record - Pattern Map

**Mapped:** 2026-09-12
**Files analyzed:** 11 (new/modified)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `qc/submission_record.py` (NEW) | model/utility (pure builder) | transform | `qc/mail_config.py` | exact — pure, Streamlit- and network-free, string/dict transform module |
| `submission_log.py` (NEW, repo root, sibling of `auth.py`) | service (thin network adapter) | event-driven / request-response (fire-and-forget upload) | `auth.py` (`secret()`, thin Streamlit-facing wiring) | role-match — thin wiring module, single external-system boundary |
| `app.py` edits: fresh-run branch (fire the upload) | controller (orchestration) | event-driven | `app.py` lines 590-676 (existing fresh-run `else` branch) | exact — same file, same branch |
| `app.py` edits: verdict banner region (status line + unconfigured banner) | component (UI render) | request-response | `app.py` lines 1187-1206 (verdict banner / email status blocks) | exact |
| `qc/report.py` edits: `build_workbook(..., record_id=None)` | service (report builder) | transform | `qc/report.py` `build_workbook` (existing `column_renames=None` param, Phase 2 precedent) | exact |
| `qc/report.py` edits: `build_email_subject_and_body(..., record_id=None)` | service (report builder) | transform | `qc/report.py` `build_email_subject_and_body` (lines 562-602) | exact |
| `tests/test_submission_record_builder.py` (NEW) | test | transform | `tests/test_smtp_recipients.py` (table-driven pure-function tests) | role-match |
| `tests/test_submission_record_path.py` (NEW) | test | transform | `tests/test_smtp_recipients.py` | role-match |
| `tests/test_no_delete_in_submission_log.py` (NEW) | test (standing AST guard) | transform | `tests/test_no_committed_secrets.py`, `tests/test_no_upload_persistence.py` | exact — same AST-walk-over-tracked-files idiom |
| `tests/test_uploader_retry_and_thread.py` / `tests/test_no_fire_on_cached_rerun.py` / `tests/test_recording_unconfigured_banner.py` (NEW) | test | event-driven | `tests/test_smtp_recipients.py` (extracts app.py functions via AST, execs in isolated namespace) | role-match |
| `tests/test_audit03_concurrent_writes.py` (NEW, live/skip-clean) | test (integration, live) | batch / concurrent | `tests/test_space_probe_logic.py` (network-adjacent test with clean skip/guard idiom) | role-match |
| `requirements.txt` (pin addition) | config | — | the `Authlib>=1.3.2,<2.0.0` line + its explanatory comment (line 8-9) | exact |
| `README.md` §Hugging Face Spaces secrets table | config/docs | — | `SMTP_TO`/`SMTP_CC` rows (lines 423-424) | exact |

## Pattern Assignments

### `qc/submission_record.py` (pure record builder)

**Analog:** `qc/mail_config.py`

**Module docstring / purity discipline pattern** (`qc/mail_config.py` lines 1-9):
```python
"""Recipient-list parsing for the QC summary email, new for DEPLOY-02/D-07.

Pure module: no ``import streamlit``, no environment access (``os.environ``) and no address
validation beyond emptiness -- ``app.py::get_recipients`` reads the two comma-separated secrets
(``SMTP_TO``/``SMTP_CC``) through ``auth.secret`` and passes the raw strings in here; this module
only turns those raw strings into recipient lists and the message that explains why Send is
disabled, which is why it is unit-testable with plain string arguments and no live session --
matching ``qc/columns.py``'s purity discipline (no env access, no Streamlit import inside the
pure functions).
"""
```
Copy this exact framing for `qc/submission_record.py`'s module docstring: no `import streamlit`,
no `import huggingface_hub`, no `os.environ` access — it must take only `QcSummary`, the officer
dict, and the file-identity tuple, and hand back a plain dict + `(record_id, repo_path)`. This
module is what `tests/test_no_streamlit_in_qc.py`'s `_scan_qc_directory()` will additionally scan
once it lands under `qc/` — **it must import cleanly with the UI framework blocked**, exactly
like every other file under `qc/`.

**Core transform pattern — reading `QcSummary`/`LayerSummary` fields** (verified this session at
`qc/report.py` lines 98-164, 168-280, `280-320`):
```python
# qc/report.py — the fields the record projects, verbatim names/line anchors:
class LayerSummary:
    checks: list                       # report.py:100
    source_row_count: "int | None"     # report.py:103 — None for Schema (D-13/D-02 parallel)
    @property
    def ran(self): return len(self.checks) > 0          # report.py:108-109
    @property
    def n_fail(self): return count_failing(self.checks) # report.py:112-113
    @property
    def distinct_issue_rows(self): ...                  # report.py:140

class QcSummary:
    @property
    def verdict_text(self): ...          # report.py:270-277
    @property
    def weighted_score(self): ...        # report.py:206-207
    @property
    def achievable_max(self): ...        # report.py:210-212
    layers: dict[str, LayerSummary]      # keyed "Schema"/"MLoS"/"Settlement"/"Takeoffpoint"/"Boundary"
```
D-02 requires "checks run, checks failing and distinct issue rows (null where the layer has no
source row count)" — build this as `len(layer.checks)`, `layer.n_fail`,
`layer.distinct_issue_rows if layer.source_row_count is not None else None` (note: use
`source_row_count is not None`, not `layer.ran`, to match D-02's literal "null where the layer has
no source row count" wording — Schema's `source_row_count` is always `None` per `report.py:103`,
independent of whether it ran).

**Officer identity pattern** (`auth.py` lines 175-188, `current_officer()`):
```python
def current_officer():
    """Returns ``None`` when not signed in, else a plain dict with keys ``email``, ``name`` and
    ``domain`` read off ``st.user``. This is the accessor Phase 5's submission log consumes;
    nothing else in the codebase may reach into ``st.user`` directly."""
    ...
```
`build_record()` must accept exactly this dict shape (or `None`) and read only `officer["email"]`
per D-01 — never `officer["name"]` or `["domain"]`.

**File identity pattern** (`app.py` lines 109-124, `_file_sha256` / `_submission_identity`):
```python
def _file_sha256(file_obj) -> str:
    ...

def _submission_identity(mlos_file, tp_file):
    """... — so two different submissions sharing a filename and current-key comparison /
    qc_cache_key ..."""
    return (_file_sha256(mlos_file), _file_sha256(tp_file) if tp_file is not None else None)
```
`app.py` already computes both sha256 digests at upload time (line 381:
`submission_identity = _submission_identity(uploaded, uploaded_tp) if uploaded is not None else None`).
Reuse these values directly for D-03's file-identity block; do not recompute a hash inside
`qc/submission_record.py` — pass the already-computed sha256 strings, filename(s), and row
counts in as plain arguments, matching D-02's "never recomputes" discipline applied to file
identity too.

**Record id / path minting (D-14):** no existing analog in this codebase mints a timestamped,
uuid-suffixed partitioned path — this is genuinely new. Follow RESEARCH.md's
`mint_record_id_and_path()` code example verbatim (stdlib `uuid.uuid4()` +
`datetime.now(timezone.utc)`, ts injectable for tests).

---

### `submission_log.py` (thin uploader, only module importing `huggingface_hub`)

**Analog:** `auth.py`'s `secret()` and its "thin gate only" framing (lines 1-9, 27-41).

**Module docstring pattern to copy** (`auth.py` lines 1-9):
```python
"""Thin Streamlit-touching login gate for AUTH-01/AUTH-02, new for D-01/D-03/D-04/D-05/D-09.

Thin gate only: this module materialises the ``[auth]`` secrets table, reads the four
environment-driven inputs a Streamlit session can observe, and renders whichever outcome
``qc.auth_domain.decide_access`` already computed. All decision logic ... lives in
``qc.auth_domain``; ... This module owns nothing but the Streamlit-facing wiring, matching
``send_qc_email``'s own "thin sender only" framing (``app.py``'s Email Sender section)."""
```
Adapt directly: `submission_log.py` owns nothing but the network-facing wiring — record building
and id minting live in `qc/submission_record.py`; this module's only job is to take an
already-built record + id/path and perform the upload, exactly mirroring the auth.py /
auth_domain.py split (decision logic elsewhere, thin wiring here) and `send_qc_email`'s
"thin sender only" precedent (`app.py`).

**Secrets read pattern** (`auth.py` lines 27-41, `secret()`):
```python
def secret(key, default=""):
    """Read ``key`` from the environment first (as given, then upper-cased), then fall back to
    ``st.secrets`` inside a ``try/except`` so a missing or unreadable secrets file falls back to
    ``default`` instead of raising. ..."""
    value = os.environ.get(key)
    if value is None:
        value = os.environ.get(key.upper())
    if value is not None:
        return value
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default
```
`submission_log.py` reads `MLOS_LOG_TOKEN` / `MLOS_LOG_REPO` through this exact same `auth.secret()`
call (`import auth; auth.secret("MLOS_LOG_TOKEN")`) — do not add a second secrets-reading path.

**Retry/thread/status-holder pattern:** no direct in-repo analog for a background daemon thread;
follow RESEARCH.md's `Code Examples` section verbatim (`_STATUS` dict + `threading.Lock`,
`_upload_with_bounded_retry`, `fire_upload`). The one codebase precedent worth copying is the
**explicit-token-always** discipline already present in `auth.py`'s `secret()` (never rely on
ambient env auto-discovery) — extend that same discipline to `HfApi(token=...)` calls.

---

### `app.py` edits — fire the upload only in the fresh-run branch

**Analog:** `app.py` lines 590-676 (the existing fresh-run `else` branch) vs. lines 573-589
(cached-hit `if` branch).

```python
if st.session_state.get("qc_cache_key") == qc_cache_key:
    # cache hit -- lines 574-588: NO new code goes here (D-06)
    ...
else:
    # fresh run -- lines 591-676: the daemon-thread fire_upload() call goes at the END of
    # this block, immediately after the session_state assignments (line 676), still inside
    # the else, and BEFORE the shared `summary = qc.report.build_summary(...)` call at line 682
    # (which both branches read but neither branch should re-fire from).
    ...
    st.session_state["autocorrect_log"]    = autocorrect_log
    # NEW: mint id/path synchronously, build record from the *just-assembled* checks/detail
    # pairs + auth.current_officer() + submission_identity, then submission_log.fire_upload(...)
```
This is Pitfall 5 in RESEARCH.md, and the plan should cite `app.py:590-676` (else) vs.
`app.py:573-589` (if) by these exact line anchors when writing the task.

### `app.py` edits — verdict banner status line + unconfigured banner

**Analog:** `app.py` lines 1187-1206 (verdict success/warning + email send status).

```python
if summary.n_fail == 0:
    st.success(f"✅ {summary.verdict_text} — all checks passed.")
else:
    st.warning(f"⚠️ {summary.verdict_text} — {summary.headline_issue_line}. ...")
...
if _recipients_reason:
    st.warning(_recipients_reason)
...
try:
    send_qc_email(summary)
    st.success("✅ Email sent successfully to the data team.")
except Exception as e:
    st.error(f"❌ Failed to send email: {e}")
```
Copy this `st.success`/`st.warning`/`st.error` three-state shape directly for D-09's status line
(recording in progress / recorded / could not be saved) and D-10's persistent unconfigured banner
(same `if _recipients_reason: st.warning(...)` shape as the SMTP-unconfigured precedent at line
1199 — that is literally the same "secret not configured, feature disabled, tell the officer why"
pattern D-10 asks for).

---

### `qc/report.py` — `build_workbook(..., record_id=None)`

**Analog:** `build_workbook`'s existing `column_renames=None` parameter (already in the current
signature, `qc/report.py` line 365) and its cover metadata block (lines 365-420).

```python
def build_workbook(summary: QcSummary, mlos_raw: "pd.DataFrame", takeoff_df: "pd.DataFrame",
                    column_renames=None) -> bytes:
    ...
    # D-08: exactly five metadata rows -- File, Generated At, MLoS Rows, Takeoffpoint Rows,
    # Weighted Score -- and no per-layer counts.
    meta = [
        ("File",              summary.filename),
        ("Generated At",      datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("MLoS Rows",         len(mlos_raw)),
        ("Takeoffpoint Rows", len(takeoff_df)),
        ("Weighted Score",    summary.score_display),
    ]
    ...
    last_meta_row = 2 + len(meta)   # NEVER hard-coded — derived from len(meta)
```
Add `record_id=None` as a new trailing keyword parameter (exactly as `column_renames` was added),
and one new `meta` row (e.g. `("Record ID", record_id or "not recorded")`) — `last_meta_row` is
already computed from `len(meta)`, so adding a row is safe by construction and needs no other
line-number edit. Existing callers/tests that don't pass `record_id` keep working unchanged.

### `qc/report.py` — `build_email_subject_and_body(..., record_id=None)`

**Analog:** the function's own existing structure, `qc/report.py` lines 562-602 (verified this
session).

```python
def build_email_subject_and_body(summary: QcSummary) -> "tuple[str, str]":
    """... Pure: takes only the shared ``QcSummary``, reads no secrets ... imports no transport
    ... so it is unit-testable without a Streamlit runtime or an SMTP mock."""
    subject = f"{EMAIL_SUBJECT_PREFIX} {summary.verdict_short} — {summary.filename}"
    lines = [
        f"MLoS QC Report — {summary.filename}",
        "=" * 60,
        f"Overall Verdict   : {summary.verdict_text}",
        f"Weighted Score    : {summary.score_display}",
        ...
    ]
```
Add `record_id=None` as a new trailing keyword parameter; append one new footer line (D-11: "beside
the Generated line") using the same `f"..."` string-building style already used throughout this
function — no new import, stays pure.

---

## Shared Patterns

### Pure module discipline (Streamlit- and network-free)
**Source:** `qc/mail_config.py` (module docstring, lines 1-9), enforced by
`tests/test_no_streamlit_in_qc.py`.
**Apply to:** `qc/submission_record.py` only — `submission_log.py` lives outside `qc/` (repo root,
sibling of `auth.py`) specifically because it is the one module allowed to import
`huggingface_hub`, matching the discretion note in CONTEXT.md ("Whether the uploader lives in
`auth.py`'s sibling or its own thin module is the planner's call").

### Secrets access
**Source:** `auth.py` lines 27-41, `secret(key, default="")`.
**Apply to:** `submission_log.py` for `MLOS_LOG_TOKEN` / `MLOS_LOG_REPO` — no new secrets-reading
mechanism; always pass the resolved value explicitly into `HfApi(token=...)`, never rely on
`huggingface_hub`'s own ambient `HF_TOKEN` discovery (RESEARCH.md Anti-Patterns).

### AST standing-guard idiom (for D-16's no-delete guard)
**Source:** `tests/test_no_streamlit_in_qc.py` (`_scan_qc_directory`, `_find_ui_framework_imports`,
"guard scanned a nonzero number of files" self-check) and `tests/test_no_upload_persistence.py`
(`_tracked_python_files()` via `git ls-files`, `_write_mode_file_calls`,
`test_write_mode_offenders_are_only_the_known_exceptions`).
```python
def _tracked_python_files():
    result = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True)
    return [REPO_ROOT / p for p in result.stdout.splitlines() if p.strip()]
```
**Apply to:** `tests/test_no_delete_in_submission_log.py` — walk every tracked `.py` file's AST for
calls to `delete_file`/`delete_folder`/`delete_repo`, any `CommitOperationDelete` construction, and
(if feasible) an `upload_file`/`CommitOperationAdd` call whose `path_in_repo` is not a fresh
literal — mirroring the exact `(offenders, scanned)` return shape and the
"guard scanned a nonzero number of files" self-check both existing guards include.

### app.py function extraction for testing without a live Streamlit session
**Source:** `tests/test_smtp_recipients.py`'s `_load_app_functions()` (AST-extract named
`ast.FunctionDef` nodes from `app.py`, `exec` them in an isolated namespace bound to the real
`auth`/`qc` modules).
**Apply to:** `tests/test_uploader_retry_and_thread.py`, `tests/test_no_fire_on_cached_rerun.py`,
`tests/test_recording_unconfigured_banner.py` — any test that needs to exercise app.py-level
orchestration logic (the fresh-run vs. cached-run fire decision, the banner-render call) without
importing the whole script (which has top-level UI code assuming a live upload).

### Network-adjacent test with clean skip
**Source:** `tests/test_space_probe_logic.py` — pure/synthetic tests plus a documented
non-vacuity self-check; no live network call in the unit-test file itself.
**Apply to:** `tests/test_audit03_concurrent_writes.py` — `pytest.mark.skipif` when
`MLOS_TEST_HF_TOKEN`/namespace env vars are absent (see RESEARCH.md's test skeleton), matching
this codebase's existing convention of keeping live-network tests skip-clean by default.

### New dependency pin with explanatory comment
**Source:** `requirements.txt` lines 8-9:
```
# Authlib is the OIDC client streamlit[auth] pulls in for st.login (AUTH-01/D-01)
Authlib>=1.3.2,<2.0.0
```
**Apply to:** add
```
# huggingface_hub writes the submission log to a private HF Dataset repo (AUDIT-02/D-05)
huggingface_hub>=1.30.0,<2.0.0
```
directly beneath the existing pins, preserving the one-comment-per-pin convention.

### README secrets table row
**Source:** `README.md` lines 423-424:
```
| `SMTP_TO` | Comma-separated primary recipients for the QC summary email | The data team |
| `SMTP_CC` | Comma-separated copy recipients for the QC summary email | The data team |
```
**Apply to:** add two rows in the same three-column (`key` | `purpose` | `value/source`) table
shape for `MLOS_LOG_TOKEN` and `MLOS_LOG_REPO`, in the same §Hugging Face Spaces section
(README.md ~lines 389-424), and extend `tests/test_no_committed_secrets.py`'s awareness list
(it currently derives its organisational-domain pattern from `qc.auth_domain.ALLOWED_DOMAIN` —
confirm the new secret **names** don't need special-casing there since they carry no address or
domain literal, only opaque token/repo-id values).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Record id/path minting logic (`mint_record_id_and_path`) | utility | transform | No existing code mints a UTC-timestamped, uuid-suffixed, year/month-partitioned path; genuinely new (D-14). Use RESEARCH.md's verbatim code example. |
| Background daemon thread + cross-thread status holder | service | event-driven | No existing threading code in the codebase; RESEARCH.md's `_STATUS` dict + `threading.Lock` example is the only concrete pattern available — follow it directly, including the "no `st.*` calls from the worker thread" constraint. |

## Metadata

**Analog search scope:** `qc/`, repo root (`app.py`, `auth.py`, `requirements.txt`, `README.md`),
`tests/`
**Files scanned:** `qc/mail_config.py`, `qc/report.py`, `auth.py`, `app.py` (lines 100-700, 1180-1210),
`requirements.txt`, `README.md` (§Hugging Face Spaces), `tests/test_no_committed_secrets.py`,
`tests/test_no_streamlit_in_qc.py`, `tests/test_no_upload_persistence.py`,
`tests/test_smtp_recipients.py`, `tests/test_space_probe_logic.py`
**Pattern extraction date:** 2026-09-12
**Note:** `app.py` is CRLF-terminated by design (per CLAUDE.md/RESEARCH.md) — any edit there must
preserve CRLF line endings; all line numbers above were read directly from the current file this
session and should be re-confirmed at implementation time since edits shift them.
