"""Tracer's own proof (05-01 Task 2): a fresh QC run's shared ``QcSummary`` becomes one
submission record, minted at a repo path before any network call, and handed to a daemon
thread that commits it to a private Hugging Face Dataset repo through a recording ``HfApi``
double. AUDIT-01, AUDIT-02 and the non-blocking half of AUDIT-05.

Each test's docstring says what would silently pass without its assertion, following
``tests/test_environment_pins.py``'s discipline. No live network call is made anywhere in this
file -- ``submission_log.HfApi`` is always replaced by ``RecordingHfApi`` before a thread is
started.
"""

import ast
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

import qc.report as report
import qc.submission_record as submission_record
import submission_log

APP_PY = Path(__file__).resolve().parent.parent / "app.py"


# ─── Synthetic QcSummary helper (shape borrowed from tests/test_email_body.py) ────────────────

def _passing(rule_ids):
    return [
        {"Status": "✅ PASS", "Rule#": r, "QC Check": f"Check {r}", "Description": "d",
         "Failing Rows": 0, "Total Rows": 10, "Fail %": "0.0%"}
        for r in rule_ids
    ]


def _summary_five_layers():
    layers = {
        "Schema": (_passing(["S1", "S2"]), pd.DataFrame()),
        "MLoS": (_passing(["1", "2"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


class RecordingHfApi:
    """Test double for ``huggingface_hub.HfApi``. Records the constructor's ``token`` and every
    ``upload_file`` call's keyword arguments; performs no network I/O."""

    calls = []
    constructed_with_token = []

    def __init__(self, token=None):
        RecordingHfApi.constructed_with_token.append(token)

    def upload_file(self, **kwargs):
        RecordingHfApi.calls.append(kwargs)


@pytest.fixture(autouse=True)
def _reset_recording_double():
    RecordingHfApi.calls = []
    RecordingHfApi.constructed_with_token = []
    yield


# ─── mint_record_id_and_path ────────────────────────────────────────────────────────────────

def test_mint_returns_three_tuple_with_utc_datetime():
    """Without this, a caller could not thread ts into build_record and the record's own
    timestamp could disagree with the month folder it sits in (D-14)."""
    record_id, repo_path, ts = submission_record.mint_record_id_and_path()
    assert isinstance(ts, datetime)
    assert ts.tzinfo is not None
    assert ts.utcoffset().total_seconds() == 0


def test_mint_record_id_format():
    """Without this assertion, a record id lacking the compact-timestamp prefix or the uuid4
    suffix would still pass a looser 'is a string' check."""
    ts = datetime(2026, 9, 12, 10, 15, 30, tzinfo=timezone.utc)
    record_id, repo_path, returned_ts = submission_record.mint_record_id_and_path(ts=ts)
    assert record_id.startswith("20260912T101530Z_")
    stem_suffix = record_id.split("_", 1)[1]
    assert len(stem_suffix) == 32
    assert returned_ts == ts


def test_mint_path_shape_for_injected_ts():
    """Without this, the year/month partition could silently derive from wall-clock time instead
    of the injected ts, breaking the boundary-month guarantee (D-14)."""
    ts = datetime(2026, 9, 12, 10, 15, 30, tzinfo=timezone.utc)
    _record_id, repo_path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert repo_path.startswith("records/2026/09/20260912T101530Z_")
    assert repo_path.endswith(".json")


def test_mint_two_calls_same_ts_produce_distinct_ids_and_paths():
    """Without this, two records minted in the same second could collide at one repo path,
    silently overwriting each other (D-14 concurrency guarantee)."""
    ts = datetime(2026, 9, 12, 10, 15, 30, tzinfo=timezone.utc)
    id1, path1, _ = submission_record.mint_record_id_and_path(ts=ts)
    id2, path2, _ = submission_record.mint_record_id_and_path(ts=ts)
    assert id1 != id2
    assert path1 != path2


# ─── build_record ────────────────────────────────────────────────────────────────────────────

def _officer():
    return {"email": "officer@ehealthnigeria.org", "name": "Test Officer", "domain": "ehealthnigeria.org"}


def _file_identity():
    return {"filename": "kano_checkout.xlsx", "sha256": "abc123"}


def test_build_record_schema_and_version():
    """Without this, a record could silently carry the wrong schema number or a hard-coded
    version string instead of reading qc.version.VERSION (D-04)."""
    import qc.version
    summary = _summary_five_layers()
    ts = datetime.now(timezone.utc)
    record = submission_record.build_record(summary, _officer(), _file_identity(), "rid1", ts)
    assert record["record_schema"] == 1
    assert record["app_version"] == qc.version.VERSION
    assert record["record_id"] == "rid1"


def test_build_record_timestamp_iso_format():
    """Without this, timestamp_utc could be naive or lack the +00:00 offset, breaking a reader's
    ability to sort or compare records across timezones (D-04)."""
    summary = _summary_five_layers()
    ts = datetime.now(timezone.utc)
    record = submission_record.build_record(summary, _officer(), _file_identity(), "rid1", ts)
    assert record["timestamp_utc"] == ts.isoformat()
    assert record["timestamp_utc"].endswith("+00:00")


def test_build_record_officer_email_only():
    """Without this, the record could leak the officer's display name or domain, which D-01
    deliberately excludes -- the email is the only identity chosen."""
    summary = _summary_five_layers()
    ts = datetime.now(timezone.utc)
    officer = _officer()
    record = submission_record.build_record(summary, officer, _file_identity(), "rid1", ts)
    assert record["officer_email"] == officer["email"]
    serialized = json.dumps(record)
    assert officer["name"] not in serialized
    assert officer["domain"] not in serialized


def test_build_record_layers_key_order_matches_layer_order():
    """Without this, a layer could silently go missing from the record (the exact defect class
    D-02 names) and a reader would have no way to tell a four-layer record from a five-layer
    one."""
    summary = _summary_five_layers()
    ts = datetime.now(timezone.utc)
    record = submission_record.build_record(summary, _officer(), _file_identity(), "rid1", ts)
    assert list(record["layers"]) == list(report.LAYER_ORDER)


def test_build_record_json_round_trip_preserves_weighted_score():
    """Without this, a formatted-string substitute or a rounding step could silently replace the
    summary's own float, making the record disagree with the verdict banner (D-02)."""
    summary = _summary_five_layers()
    ts = datetime.now(timezone.utc)
    record = submission_record.build_record(summary, _officer(), _file_identity(), "rid1", ts)
    round_tripped = json.loads(json.dumps(record))
    assert round_tripped == record
    assert round_tripped["weighted_score"] == summary.weighted_score


# ─── unconfigured_reason ─────────────────────────────────────────────────────────────────────

def test_unconfigured_reason_none_when_both_secrets_set(monkeypatch):
    """Without this, a configured deployment could still show the unconfigured banner, which
    would confuse an officer into thinking nothing is ever recorded (D-10)."""
    monkeypatch.setenv("MLOS_LOG_TOKEN", "tok")
    monkeypatch.setenv("MLOS_LOG_REPO", "org/repo")
    assert submission_log.unconfigured_reason() is None


def test_unconfigured_reason_names_missing_secret(monkeypatch):
    """Without this, an unset secret could produce a silent no-op instead of a stated reason,
    which is exactly the failure D-10 exists to prevent."""
    monkeypatch.delenv("MLOS_LOG_TOKEN", raising=False)
    monkeypatch.delenv("MLOS_LOG_REPO", raising=False)
    reason = submission_log.unconfigured_reason()
    assert reason is not None
    assert "MLOS_LOG_TOKEN" in reason
    assert "MLOS_LOG_REPO" in reason


# ─── fire_upload / get_status ────────────────────────────────────────────────────────────────

def test_fire_upload_configured_spawns_daemon_thread_and_records(monkeypatch):
    """Without this, the uploader could block the officer's render path, or could silently
    upload to the wrong repo/path/token -- this asserts the exact call shape reaches the double."""
    monkeypatch.setenv("MLOS_LOG_TOKEN", "test-token")
    monkeypatch.setenv("MLOS_LOG_REPO", "org/mlos-log")
    monkeypatch.setattr(submission_log, "HfApi", RecordingHfApi)

    record = {"record_schema": 1, "record_id": "rid-fire-1"}
    thread = submission_log.fire_upload(record, "records/2026/09/rid-fire-1.json", "rid-fire-1")

    assert isinstance(thread, threading.Thread)
    assert thread.daemon is True
    thread.join(timeout=10)
    assert not thread.is_alive()

    assert len(RecordingHfApi.calls) == 1
    call = RecordingHfApi.calls[0]
    assert call["path_in_repo"] == "records/2026/09/rid-fire-1.json"
    assert call["repo_type"] == "dataset"
    assert call["repo_id"] == "org/mlos-log"
    assert RecordingHfApi.constructed_with_token == ["test-token"]
    payload = call["path_or_fileobj"]
    if isinstance(payload, (bytes, bytearray)):
        decoded = json.loads(payload.decode("utf-8"))
    else:
        decoded = json.loads(payload)
    assert decoded == record

    assert submission_log.get_status("rid-fire-1") == "recorded"


def test_fire_upload_unconfigured_returns_none_and_records_zero_calls(monkeypatch):
    """Without this, an unconfigured deployment could still spawn a thread or attempt a network
    call, which is exactly what D-10/T-05-04 forbid."""
    monkeypatch.delenv("MLOS_LOG_TOKEN", raising=False)
    monkeypatch.delenv("MLOS_LOG_REPO", raising=False)
    monkeypatch.setattr(submission_log, "HfApi", RecordingHfApi)

    record = {"record_schema": 1, "record_id": "rid-fire-2"}
    result = submission_log.fire_upload(record, "records/2026/09/rid-fire-2.json", "rid-fire-2")

    assert result is None
    assert RecordingHfApi.calls == []
    assert submission_log.get_status("rid-fire-2") == "unconfigured"


# ─── app.py single fire-site AST check ───────────────────────────────────────────────────────

def test_app_py_has_exactly_one_fire_upload_call_site():
    """Without this, a second fire_upload call site (e.g. accidentally added to the cached
    branch) could record a QC run twice, violating D-06."""
    tree = ast.parse(APP_PY.read_text(), filename=str(APP_PY))
    count = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node).startswith("submission_log.fire_upload(")
    )
    assert count == 1, f"expected exactly one submission_log.fire_upload( call site, found {count}"
