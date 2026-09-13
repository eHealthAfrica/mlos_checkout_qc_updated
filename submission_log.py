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
import time

from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError

import auth

LOG_TOKEN_VAR = "MLOS_LOG_TOKEN"
LOG_REPO_VAR = "MLOS_LOG_REPO"
STATUS_CAP = 500

# D-07: a few bounded retries with backoff, about a minute total across five attempts (1 + 4 +
# 15 + 40 = 60s of sleeping between the five tries). D-07 explicitly rejects an on-disk retry
# queue -- that would reintroduce the buffer D-05 already rejected -- so the whole schedule lives
# in this in-memory tuple and nothing here ever touches a filesystem path. A retry library
# (tenacity, backoff) was considered and rejected: this is a fifteen-line loop, not a case that
# needs a dependency (05-RESEARCH.md ## Don't Hand-Roll).
RETRY_DELAYS = (1, 4, 15, 40)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1

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


def _upload_with_bounded_retry(record, path_in_repo, record_id, token, repo_id,
                                sleep=time.sleep, api_factory=None):
    """Worker: serialise ``record`` and upload it via ``HfApi``, retrying on a bounded schedule
    (D-07). Must reference neither the UI framework nor ``auth`` -- ``token``/``repo_id`` are
    resolved by the caller and passed in explicitly.

    ``sleep`` and ``api_factory`` default to the real implementations (the stdlib clock, and the
    module-level ``HfApi``) and exist purely so the test suite can prove the retry schedule and
    drive a constructor-raises case without spending a minute of wall time or a live Hub call;
    ``fire_upload`` passes neither, so production behaviour is unchanged.

    The loop attempts the upload immediately, then on each failure sleeps the next value from
    ``RETRY_DELAYS`` and retries, until either an attempt succeeds (status ``"recorded"``,
    return) or the delays are exhausted (status ``"failed"``, return). The whole body -- Hub
    error hierarchy, and a second, broader catch for every other failure including a
    network-layer error or a constructor failure -- is wrapped so that no path can exit without
    setting a terminal status: an exception escaping a ``threading.Thread`` target does not crash
    the process, but it does mean the status holder is never updated, leaving the officer's
    status line at "in progress" forever -- the silent-failure shape this phase exists to
    remove."""
    factory = api_factory if api_factory is not None else HfApi
    payload = json.dumps(record).encode("utf-8")
    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            sleep(RETRY_DELAYS[attempt - 1])
        try:
            factory(token=token).upload_file(
                path_or_fileobj=payload,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"submission record {record_id}",
                # Deliberately no parent-commit keyword: each record's path has never existed,
                # and supplying a stale value would manufacture 412 rejections between two
                # unrelated concurrent submissions (RESEARCH ## Concurrency Semantics).
            )
            _set_status(record_id, "recorded")
            return
        except HfHubHTTPError as e:
            # D-12: only the record id and error class are logged server-side, never the
            # record's own contents, the token or the repo id.
            print(f"submission_log: upload failed for {record_id}: {type(e).__name__}")
        except Exception as e:
            # Broader catch, deliberate: a network-layer error or a constructor failure must
            # also leave a terminal status rather than escape this thread's target function.
            print(f"submission_log: upload failed for {record_id}: {type(e).__name__}")
    _set_status(record_id, "failed")
