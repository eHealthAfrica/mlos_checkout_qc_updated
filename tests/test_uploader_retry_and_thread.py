"""RED-then-GREEN proof for submission_log.py's bounded retry, daemon-thread containment and
D-12 failure log line (05-02 Task 1). Extends 05-01's recording-double idiom
(tests/test_smtp_recipients.py's AST-extraction style; tests/test_submission_record_end_to_end.py's
``RecordingHfApi``) with a parameterised failing double and a recording clock.

No real ``time.sleep`` is ever taken. Every schedule/attempt-count/failure-handling assertion
calls ``submission_log._upload_with_bounded_retry`` directly with an injected ``sleep`` and
``api_factory`` -- a synchronous call needing no thread. The one daemon-thread test goes through
the real, public ``fire_upload()`` entry point instead (so a regression at the thread-construction
call site itself would be caught) and injects the same recording clock by overriding
``_upload_with_bounded_retry``'s own bound default via ``__defaults__`` -- ``fire_upload`` itself
passes neither ``sleep`` nor ``api_factory`` to the retry function (production behaviour is
unchanged), so this is the only way to keep that one test from taking a real ~60 seconds.

Each test's docstring says what would silently pass without its assertion, following
``tests/test_environment_pins.py``'s discipline.
"""

import ast
from pathlib import Path

import httpx
import pytest
from huggingface_hub.errors import HfHubHTTPError

import submission_log

SUBMISSION_LOG_PY = Path(__file__).resolve().parent.parent / "submission_log.py"


def _hf_hub_http_error(message="boom"):
    """A real ``HfHubHTTPError`` instance (not a synthetic stand-in), so the retry loop's own
    ``except HfHubHTTPError`` clause is genuinely exercised."""
    request = httpx.Request("POST", "https://huggingface.co/api/datasets/x/commit/main")
    response = httpx.Response(500, request=request)
    return HfHubHTTPError(message, response=response)


class RecordingSleep:
    """Callable clock double: records every delay it is asked to sleep for, never actually
    sleeps. Recording the exact argument list (not just a call count) is what catches a loop that
    retried the right number of times with the wrong -- or no -- backoff."""

    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


def _make_failing_factory(fail_times, calls, exc_factory=_hf_hub_http_error):
    """Return an ``api_factory`` whose constructed instances fail ``upload_file`` exactly
    ``fail_times`` times (raising ``exc_factory()``) before succeeding, or forever when
    ``fail_times`` is ``None``. ``_upload_with_bounded_retry`` constructs a fresh instance on
    every attempt (``factory(token=token)``), so the failure count lives in a closure-shared
    dict, not on any one instance -- otherwise a fresh instance every attempt would silently
    reset an instance-level counter and every attempt would fail."""
    state = {"n": 0}

    class _Api:
        def __init__(self, token=None):
            calls.append(("construct", token))

        def upload_file(self, **kwargs):
            calls.append(("upload", kwargs))
            if fail_times is None or state["n"] < fail_times:
                state["n"] += 1
                raise exc_factory()

    return _Api


def _make_raising_constructor_factory(calls):
    """A factory whose constructor itself always raises -- ``upload_file`` must never be
    reached, proving the retry loop's try/except wraps construction too, not only the upload
    call."""

    class _Api:
        def __init__(self, token=None):
            calls.append(("construct", token))
            raise RuntimeError("constructor boom")

        def upload_file(self, **kwargs):  # pragma: no cover -- must never be reached
            calls.append(("upload", kwargs))

    return _Api


RECORD = {
    "record_schema": 1,
    "record_id": "rid-1",
    "officer_email": "officer@example.com",
    "file": {"sha256": "deadbeef" * 8},
}


# ─── RETRY_DELAYS / MAX_ATTEMPTS contract ────────────────────────────────────────────────────

def test_retry_delays_sum_and_length_and_max_attempts():
    """Without a floor on both the sum and the length, a single 60-second delay -- or five
    1-second ones -- would satisfy a looser check while not actually being D-07's 'a few bounded
    retries with backoff'."""
    assert 55 <= sum(submission_log.RETRY_DELAYS) <= 65
    assert len(submission_log.RETRY_DELAYS) >= 3
    assert submission_log.MAX_ATTEMPTS == len(submission_log.RETRY_DELAYS) + 1


# ─── Schedule / attempt-count assertions (direct, synchronous call) ──────────────────────────

def test_always_failing_double_drives_exactly_max_attempts_calls_and_fails():
    """Without asserting the exact call count against MAX_ATTEMPTS (rather than 'at least one
    call'), a loop that gave up after a single attempt -- or retried forever -- would both
    silently pass."""
    calls = []
    factory = _make_failing_factory(fail_times=None, calls=calls)
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-1.json", "rid-1", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )

    upload_calls = [c for c in calls if c[0] == "upload"]
    assert len(upload_calls) == submission_log.MAX_ATTEMPTS
    assert submission_log.get_status("rid-1") == "failed"


def test_recorded_sleep_schedule_equals_retry_delays_in_always_failing_case():
    """Without comparing the exact recorded list to ``list(RETRY_DELAYS)`` (rather than 'some
    sleeps happened'), a loop that retried the right number of times with no backoff at all --
    sleeping 0 seconds every time -- would still pass a weaker assertion."""
    calls = []
    factory = _make_failing_factory(fail_times=None, calls=calls)
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-2.json", "rid-2", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )

    assert sleeper.calls == list(submission_log.RETRY_DELAYS)


def test_first_attempt_is_immediate_no_sleep_before_it():
    """Without this, a loop that slept before its very first attempt would still pass a test that
    only checked the total sleep count rather than the boundary condition."""
    calls = []
    factory = _make_failing_factory(fail_times=1, calls=calls)
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-3.json", "rid-3", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )

    upload_calls = [c for c in calls if c[0] == "upload"]
    assert len(upload_calls) == 2
    assert len(sleeper.calls) == 1
    assert sleeper.calls[0] == submission_log.RETRY_DELAYS[0]


def test_succeed_on_third_attempt_makes_exactly_three_calls_and_two_sleeps():
    """Without asserting the exact attempt count (3) and sleep count (2), a loop that kept
    retrying past a successful attempt -- wasting time and Hub quota -- would still pass a test
    that only checked the final status."""
    calls = []
    factory = _make_failing_factory(fail_times=2, calls=calls)
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-4.json", "rid-4", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )

    upload_calls = [c for c in calls if c[0] == "upload"]
    assert len(upload_calls) == 3
    assert len(sleeper.calls) == 2
    assert submission_log.get_status("rid-4") == "recorded"


def test_plain_runtime_error_still_sets_failed_and_raises_nothing():
    """Without this, catching only the Hub's own error hierarchy would leave a plain, non-Hub
    exception (a network-layer failure, say) to propagate out of the worker -- the silent-failure
    shape (the status holder never updates, so the officer's status line sits at 'in progress'
    forever) this phase exists to remove."""
    calls = []
    factory = _make_failing_factory(
        fail_times=None, calls=calls, exc_factory=lambda: RuntimeError("boom"),
    )
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-5.json", "rid-5", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )  # must not raise

    assert submission_log.get_status("rid-5") == "failed"


def test_raising_constructor_still_sets_failed_and_raises_nothing():
    """Without this, a factory/constructor failure -- distinct code from the upload try/except --
    would be an uncovered path; this proves the whole attempt (construction and upload alike) is
    wrapped so nothing can exit without setting a terminal status."""
    calls = []
    factory = _make_raising_constructor_factory(calls)
    sleeper = RecordingSleep()

    submission_log._upload_with_bounded_retry(
        RECORD, "records/2026/09/rid-6.json", "rid-6", "tok", "org/repo",
        sleep=sleeper, api_factory=factory,
    )  # must not raise

    assert submission_log.get_status("rid-6") == "failed"
    upload_calls = [c for c in calls if c[0] == "upload"]
    assert not upload_calls, "upload_file must never be reached when the constructor itself raises"


# ─── Failure log line (D-12) ──────────────────────────────────────────────────────────────────

def test_failure_log_line_names_the_record_id_and_error_class_and_nothing_else(capsys):
    """Without asserting absence (not just presence), a log line that additionally printed the
    token, repo id or record contents on failure would still pass a test that only checked the id
    and class name were present."""
    calls = []
    factory = _make_failing_factory(fail_times=None, calls=calls)
    sleeper = RecordingSleep()
    secret_token = "hf_super_secret_token_value"
    secret_repo = "eHealthAfrica/mlos-submission-log"
    file_sha = "f" * 64
    record = {
        "record_schema": 1, "record_id": "rid-7", "officer_email": "officer@example.com",
        "file": {"sha256": file_sha},
    }

    submission_log._upload_with_bounded_retry(
        record, "records/2026/09/rid-7.json", "rid-7", secret_token, secret_repo,
        sleep=sleeper, api_factory=factory,
    )

    out = capsys.readouterr().out
    assert "rid-7" in out
    assert "HfHubHTTPError" in out
    assert secret_token not in out
    assert secret_repo not in out
    assert "officer@example.com" not in out
    assert file_sha not in out


# ─── get_status default / STATUS_CAP ──────────────────────────────────────────────────────────

def test_get_status_defaults_to_pending_for_an_unseen_id():
    """Without this, an id the holder has never seen could raise a KeyError instead of reporting
    the documented 'pending' default."""
    assert submission_log.get_status("never-seen-id-xyz") == "pending"


def test_status_holder_stays_capped_and_keeps_the_newest_id():
    """Without this, a long-lived process's status holder would grow without bound -- a slow
    memory leak -- while a test only checking 'the newest id is present' would miss it entirely."""
    newest = None
    for i in range(submission_log.STATUS_CAP + 50):
        newest = f"cap-test-id-{i}"
        submission_log._set_status(newest, "pending")
    assert len(submission_log._STATUS) <= submission_log.STATUS_CAP
    assert submission_log.get_status(newest) == "pending"


# ─── AST: no disk writes anywhere in the retry loop ───────────────────────────────────────────

def test_no_disk_write_calls_inside_the_retry_loop():
    """Without this, a well-intentioned 'write the pending record to disk before retrying'
    addition would reintroduce the on-disk retry queue D-05/D-07 explicitly reject, and no other
    test in this suite would notice, since every double above is purely in-memory."""
    tree = ast.parse(SUBMISSION_LOG_PY.read_text())
    fn = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_upload_with_bounded_retry"
    ][0]
    bad = [
        ast.unparse(node) for node in ast.walk(fn)
        if isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "open")
            or (isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"))
        )
    ]
    assert not bad, f"disk-write call(s) found inside the retry loop: {bad}"


# ─── Daemon thread + no-propagation, through the real fire_upload() entry point ───────────────

def test_fire_upload_daemon_thread_not_alive_after_join_in_always_failing_case(monkeypatch):
    """Without going through the real ``fire_upload()`` entry point (not just the private retry
    function), a daemon-flag regression at the thread-construction call site itself would go
    undetected. The clock is injected here too -- by overriding ``_upload_with_bounded_retry``'s
    own bound default, since ``fire_upload`` itself passes neither ``sleep`` nor ``api_factory``
    (D-07's own point: production behaviour is unchanged by adding these parameters) -- so this
    test still completes without a real ~60-second wait, proving the daemon thread terminates on
    its own bounded schedule rather than merely 'eventually'."""
    monkeypatch.setenv("MLOS_LOG_TOKEN", "test-token")
    monkeypatch.setenv("MLOS_LOG_REPO", "org/mlos-log")
    calls = []
    factory = _make_failing_factory(fail_times=None, calls=calls)
    sleeper = RecordingSleep()
    monkeypatch.setattr(
        submission_log._upload_with_bounded_retry, "__defaults__", (sleeper, factory)
    )

    thread = submission_log.fire_upload(
        {"record_schema": 1, "record_id": "rid-daemon"},
        "records/2026/09/rid-daemon.json", "rid-daemon",
    )

    assert thread is not None
    assert thread.daemon is True
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert sleeper.calls == list(submission_log.RETRY_DELAYS)
    assert submission_log.get_status("rid-daemon") == "failed"
