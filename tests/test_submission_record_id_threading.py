"""Tests proving the record id (D-11) reaches the workbook cover and the QC email footer through
the existing report builders -- no second path to either surface, new for 05-03 Task 2.

Reuses ``tests/test_report_workbook_shape.py``'s ``_cover_sheet``/``_cover_values`` helpers by
importing them rather than copying, so the two files cannot drift in how they read a cover (this
plan's own instruction). Reuses ``tests/test_smtp_recipients.py``'s ``_load_app_functions`` for
the ``send_qc_email`` forwarding proof, for the same reason ``test_smtp_recipients.py`` itself
uses it: ``app.py`` cannot be imported directly (top-level UI code assumes a live session), so the
named function definitions are extracted from its real AST and exec'd in an isolated namespace.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

import qc.report as report
from test_report_workbook_shape import (
    _cover_sheet,
    _cover_values,
    _mlos_raw,
    _summary_only_boundary_failing,
    _takeoff_df,
)
from test_smtp_recipients import _load_app_functions

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


# ─── build_workbook: the cover carries the id or the stated placeholder (D-11) ─────

def test_build_workbook_with_no_record_id_returns_bytes_and_shows_not_recorded():
    summary = _summary_only_boundary_failing()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    assert isinstance(out, bytes)
    _, ws = _cover_sheet(summary)
    assert "not recorded" in _cover_values(ws)


def test_build_workbook_with_a_record_id_shows_the_exact_string():
    summary = _summary_only_boundary_failing()
    rid = "20260912T101530Z_abc"
    _, ws = _cover_sheet(summary, record_id=rid)
    assert rid in _cover_values(ws)


def test_cover_metadata_labels_are_exactly_the_six_in_order_record_id_third():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary, record_id="some-id")
    expected = ["File", "Generated At", "Record ID", "MLoS Rows", "Takeoffpoint Rows", "Weighted Score"]
    meta_labels = set(expected)
    all_col_a = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    found_meta = [v for v in all_col_a if v in meta_labels]
    assert found_meta == expected


def test_verdict_row_is_still_below_the_six_row_metadata_block():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary, record_id="some-id")
    meta_labels = {"File", "Generated At", "Record ID", "MLoS Rows", "Takeoffpoint Rows", "Weighted Score"}
    meta_rows = [r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value in meta_labels]
    verdict_rows = [
        r for r in range(1, ws.max_row + 1)
        if isinstance(ws.cell(row=r, column=1).value, str)
        and (ws.cell(row=r, column=1).value.startswith("FAILING (")
             or ws.cell(row=r, column=1).value.startswith("CLEAN"))
    ]
    assert meta_rows and verdict_rows
    assert max(meta_rows) < min(verdict_rows)


def test_report_py_never_hard_codes_a_metadata_row_index():
    """last_meta_row must stay derived from len(meta) -- a literal row index here is exactly
    what a sixth row (Record ID) would silently break."""
    src = (Path(__file__).resolve().parent.parent / "qc" / "report.py").read_text()
    assert "last_meta_row = 2 + len(meta)" in src


# ─── build_email_subject_and_body: the footer carries the id or the placeholder ────

def test_email_body_with_no_record_id_shows_not_recorded():
    summary = _summary_only_boundary_failing()
    _, body = report.build_email_subject_and_body(summary)
    assert "Record ID: not recorded" in body


def test_email_body_with_a_record_id_shows_the_exact_string():
    summary = _summary_only_boundary_failing()
    _, body = report.build_email_subject_and_body(summary, record_id="R1")
    assert "Record ID: R1" in body


def test_email_body_record_id_line_is_adjacent_to_the_generated_line():
    summary = _summary_only_boundary_failing()
    _, body = report.build_email_subject_and_body(summary, record_id="R1")
    lines = body.splitlines()
    record_idx = next(i for i, line in enumerate(lines) if line.startswith("Record ID:"))
    generated_idx = next(i for i, line in enumerate(lines) if line.startswith("Generated:"))
    assert generated_idx == record_idx + 1


def test_email_subject_is_byte_identical_with_and_without_a_record_id():
    """The id is a traceability handle, not a subject-line decision input -- putting it in the
    subject would make every email's subject unique and unsortable (D-11's own reasoning)."""
    summary = _summary_only_boundary_failing()
    subject_without, _ = report.build_email_subject_and_body(summary)
    subject_with, _ = report.build_email_subject_and_body(summary, record_id="R1")
    assert subject_without == subject_with


# ─── send_qc_email forwards record_id to the pure composer (app.py) ───────────────

class _RecordingComposer:
    """Stands in for qc.report.build_email_subject_and_body -- records the record_id it was
    called with, proving send_qc_email forwards it rather than dropping or re-deriving it."""

    calls = []

    @staticmethod
    def build(summary, record_id=None):
        _RecordingComposer.calls.append(record_id)
        return "subject", "body"


class _RecordingSMTP:
    """A no-op SMTP double -- proves send_qc_email reaches the transport step without touching a
    real network connection."""

    instances = []

    def __init__(self, *args, **kwargs):
        _RecordingSMTP.instances.append((args, kwargs))

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self):
        pass

    def login(self, *args, **kwargs):
        pass

    def sendmail(self, *args, **kwargs):
        pass


@pytest.fixture
def app_functions():
    return _load_app_functions("get_recipients", "send_qc_email")


def test_send_qc_email_forwards_record_id_to_the_composer(monkeypatch, app_functions):
    monkeypatch.setenv("SMTP_TO", "a@x.test")
    monkeypatch.delenv("SMTP_CC", raising=False)
    monkeypatch.setenv("smtp_user", "sender@x.test")
    monkeypatch.setenv("smtp_host", "smtp.x.test")
    monkeypatch.setenv("smtp_port", "587")
    monkeypatch.setenv("smtp_pass", "unused")

    _RecordingComposer.calls.clear()
    _RecordingSMTP.instances.clear()
    monkeypatch.setattr("qc.report.build_email_subject_and_body", _RecordingComposer.build)
    monkeypatch.setattr("smtplib.SMTP", _RecordingSMTP)

    app_functions["send_qc_email"](summary=None, record_id="R-threaded")

    assert _RecordingComposer.calls == ["R-threaded"]
    assert len(_RecordingSMTP.instances) == 1


# ─── app.py wiring: both call sites carry record_id=_record_id ────────────────────

def test_app_py_build_workbook_and_send_qc_email_calls_carry_record_id_bound_to__record_id():
    tree = ast.parse(APP_PATH.read_text(), filename=str(APP_PATH))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            unparsed = ast.unparse(node)
            if unparsed.startswith("qc.report.build_workbook(") or unparsed.startswith("send_qc_email("):
                for kw in node.keywords:
                    if kw.arg == "record_id":
                        hits.append(ast.unparse(kw.value))
    assert hits.count("_record_id") == 2, hits
