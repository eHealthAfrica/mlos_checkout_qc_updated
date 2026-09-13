"""Thin network-facing wiring for the submission log, new for AUDIT-02/AUDIT-05 (D-05 to D-12).

Owns nothing but the network-facing wiring: record building and id minting live in
``qc/submission_record.py``. This is the only module in the repository permitted to import
``huggingface_hub``. The worker function (``_upload_with_bounded_retry``) must reach neither the
UI framework nor ``auth`` -- a fire-and-forget thread outliving the script run is exactly the
case Streamlit's own documentation says is unsupported for threads calling its APIs, so the
worker performs pure network I/O only and hands its outcome back through a plain, thread-safe
holder that the next rerun's main thread reads.
"""

import json
import threading

from huggingface_hub import HfApi

import auth

LOG_TOKEN_VAR = "MLOS_LOG_TOKEN"
LOG_REPO_VAR = "MLOS_LOG_REPO"
STATUS_CAP = 500

# D-07: a few bounded retries with backoff, about a minute total. This task's failure branch is
# a single attempt (no retry yet); 05-02 expands this schedule and the retry loop that reads it.
RETRY_DELAYS = ()

_STATUS = {}
_STATUS_LOCK = threading.Lock()


def _set_status(record_id, value):
    """Write ``value`` for ``record_id`` under the lock. When the holder exceeds ``STATUS_CAP``,
    drop the oldest half by insertion order -- the app process is long-lived and an unbounded
    holder is a slow leak."""
    with _STATUS_LOCK:
        _STATUS[record_id] = value
        if len(_STATUS) > STATUS_CAP:
            for key in list(_STATUS)[: len(_STATUS) // 2]:
                _STATUS.pop(key, None)


def get_status(record_id):
    """Return the stored status for ``record_id``, defaulting to ``"pending"`` for an id never
    seen. The four values this module ever stores: ``"pending"``, ``"recorded"``, ``"failed"``
    and ``"unconfigured"``."""
    with _STATUS_LOCK:
        return _STATUS.get(record_id, "pending")


def unconfigured_reason():
    """Return ``None`` when both ``MLOS_LOG_TOKEN`` and ``MLOS_LOG_REPO`` resolve to non-empty
    values through ``auth.secret``, else one sentence naming the missing variable(s) and stating
    that QC still runs and nothing is recorded (D-10) -- a feature that silently does nothing is
    the failure D-10 exists to prevent."""
    token = (auth.secret(LOG_TOKEN_VAR) or "").strip()
    repo_id = (auth.secret(LOG_REPO_VAR) or "").strip()
    missing = []
    if not token:
        missing.append(LOG_TOKEN_VAR)
    if not repo_id:
        missing.append(LOG_REPO_VAR)
    if not missing:
        return None
    return (
        f"Submission recording is not configured ({' and '.join(missing)} not set) -- "
        "QC still runs and nothing is recorded."
    )


def fire_upload(record, path_in_repo, record_id):
    """D-05/D-06: call this ONLY from the fresh-run branch, exactly once per QC run.

    Returns the spawned daemon ``Thread`` -- a testability affordance only; no caller in
    ``app.py`` may join it -- or ``None`` when recording is unconfigured (no thread spawned, no
    network call attempted).
    """
    reason = unconfigured_reason()
    if reason is not None:
        _set_status(record_id, "unconfigured")
        return None

    # Resolved here, on the calling (main script) thread -- never inside the worker.
    token = auth.secret(LOG_TOKEN_VAR)
    repo_id = auth.secret(LOG_REPO_VAR)

    _set_status(record_id, "pending")
    thread = threading.Thread(
        target=_upload_with_bounded_retry,
        args=(record, path_in_repo, record_id, token, repo_id),
        daemon=True,
    )
    thread.start()
    return thread


def _upload_with_bounded_retry(record, path_in_repo, record_id, token, repo_id):
    """Worker: serialise ``record`` and upload it via ``HfApi``. Must reference neither the UI
    framework nor ``auth`` -- ``token``/``repo_id`` are resolved by the caller and passed in
    explicitly. This task's failure branch is a single attempt that sets ``"failed"``; 05-02
    expands it into D-07's bounded retry schedule."""
    payload = json.dumps(record).encode("utf-8")
    try:
        HfApi(token=token).upload_file(
            path_or_fileobj=payload,
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"submission record {record_id}",
            # Deliberately no parent-commit keyword: each record's path has never existed, and
            # supplying a stale value would manufacture 412 rejections between two unrelated
            # concurrent submissions (RESEARCH ## Concurrency Semantics).
        )
        _set_status(record_id, "recorded")
    except Exception as e:
        # D-12: only the record id and error class are logged server-side, never the record's
        # own contents.
        print(f"submission_log: upload failed for {record_id}: {type(e).__name__}")
        _set_status(record_id, "failed")
