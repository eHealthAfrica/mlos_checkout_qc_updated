"""Table-driven tests for qc.mail_config's recipient parsing and app.py's get_recipients /
send_qc_email (SMTP_TO/SMTP_CC from Space secrets, DEPLOY-02/D-07, plan 04-02 Task 1).

get_recipients and send_qc_email must stay in app.py per this plan's key_links (the Send
button's disabled state is wired at that same call site) -- but app.py is a Streamlit script
with top-level UI code that assumes a live upload and a running ScriptRunContext, so a bare
``import app`` runs past the point these two functions are defined and crashes later in the
script body (there is no guard around the sidebar/uploader section that would let a bare import
stop cleanly). This file extracts only the named function definitions from app.py's AST and
executes them in an isolated namespace bound to the real ``auth``/``qc`` modules, instead of
importing the whole script -- this exercises the same production code (byte-identical AST,
compiled straight from app.py's own source) without needing a live Streamlit session or a fake
uploaded file.
"""

import ast
from pathlib import Path

import pytest

import auth
import qc
import qc.mail_config
import qc.report

APP_PY = Path(__file__).resolve().parent.parent / "app.py"


def _load_app_functions(*names):
    """Extract the named top-level function definitions from app.py's AST and exec them in a
    namespace bound to the real auth/qc modules, without running the rest of the script. Returns
    the requested callables as a dict; asserts every requested name was actually found, so a
    typo'd or since-renamed function name fails loudly instead of returning an empty dict."""
    tree = ast.parse(APP_PY.read_text(), filename=str(APP_PY))
    wanted = set(names)
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    found_names = {n.name for n in body}
    missing = wanted - found_names
    assert not missing, f"function(s) not found at app.py module scope: {missing}"

    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"__name__": "app_under_test", "auth": auth, "qc": qc}
    exec(compile(module, filename=str(APP_PY), mode="exec"), namespace)
    return {name: namespace[name] for name in names}


@pytest.fixture
def app_functions():
    return _load_app_functions("get_recipients", "send_qc_email")


# ─── parse_address_list ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", ["", "   ", ",,", None])
def test_parse_address_list_empty_inputs_return_empty_list(raw):
    """Every one of these inputs names zero addresses; a parser that returned e.g. [''] for an
    empty string would silently create a one-item "recipient" list containing nothing usable."""
    assert qc.mail_config.parse_address_list(raw) == []


def test_parse_address_list_strips_whitespace_and_preserves_order():
    """Asserts the full list with == (not membership) so a parser that reordered the two
    addresses, or that returned three items because it failed to drop the empty inner segment,
    would fail -- both the exact content and the order are under test."""
    assert qc.mail_config.parse_address_list(" a@x.test , b@x.test ") == ["a@x.test", "b@x.test"]


def test_parse_address_list_deduplicates_case_insensitively_keeping_first_spelling():
    """The repeated address differs only in case (A@X.TEST vs a@x.test); asserting the returned
    list keeps exactly the FIRST occurrence's original spelling proves the de-duplication key is
    case-folded while the stored value is not silently re-cased."""
    result = qc.mail_config.parse_address_list("a@x.test, A@X.TEST, b@x.test")
    assert result == ["a@x.test", "b@x.test"]


# ─── split_recipients ────────────────────────────────────────────────────────────

def test_split_recipients_removes_overlap_from_cc_only():
    """b@x.test appears in both lists; asserting the exact pair proves it survives only in TO,
    never doubling delivery to the same address on one message (T-04-14)."""
    result = qc.mail_config.split_recipients("a@x.test,b@x.test", "b@x.test,c@x.test")
    assert result == (["a@x.test", "b@x.test"], ["c@x.test"])


def test_split_recipients_empty_to_does_not_empty_cc():
    """An empty TO list must not be conflated with an empty CC list -- the two lists are
    independent except for the one-directional de-duplication tested above."""
    result = qc.mail_config.split_recipients("", "c@x.test")
    assert result == ([], ["c@x.test"])


# ─── recipients_disabled_reason ──────────────────────────────────────────────────

def test_recipients_disabled_reason_names_smtp_to_when_empty():
    """The message must name SMTP_TO specifically -- "Send is unavailable" with no cause is the
    silent failure D-07 exists to prevent."""
    reason = qc.mail_config.recipients_disabled_reason([])
    assert reason is not None
    assert "SMTP_TO" in reason


def test_recipients_disabled_reason_is_none_when_non_empty():
    assert qc.mail_config.recipients_disabled_reason(["a@x.test"]) is None


# ─── get_recipients (app.py) ─────────────────────────────────────────────────────

def test_get_recipients_reads_smtp_to_and_cc_via_auth_secret(monkeypatch, app_functions):
    """SMTP_TO set, SMTP_CC unset: proves get_recipients reads through auth.secret (env-first)
    rather than st.secrets directly, and that an unset SMTP_CC yields an empty CC list rather
    than raising."""
    monkeypatch.setenv("SMTP_TO", "a@x.test, b@x.test")
    monkeypatch.delenv("SMTP_CC", raising=False)
    to_list, cc_list, reason = app_functions["get_recipients"]()
    assert to_list == ["a@x.test", "b@x.test"]
    assert cc_list == []
    assert reason is None


def test_get_recipients_disabled_reason_when_smtp_to_unset(monkeypatch, app_functions):
    """An absent SMTP_TO must produce a reason naming SMTP_TO -- this is what the Send button
    reads to decide its own disabled state."""
    monkeypatch.delenv("SMTP_TO", raising=False)
    monkeypatch.delenv("SMTP_CC", raising=False)
    to_list, cc_list, reason = app_functions["get_recipients"]()
    assert to_list == []
    assert reason is not None
    assert "SMTP_TO" in reason


# ─── send_qc_email (app.py) ──────────────────────────────────────────────────────

class _RecordingSMTP:
    """Records whether an SMTP connection was ever opened -- proves send_qc_email raises BEFORE
    any smtplib.SMTP construction, not merely that it raises for some other reason."""
    instances = []

    def __init__(self, *args, **kwargs):
        _RecordingSMTP.instances.append((args, kwargs))
        raise AssertionError("smtplib.SMTP must never be constructed when SMTP_TO is empty")


def test_send_qc_email_refuses_when_smtp_to_unset(monkeypatch, app_functions):
    """Proves the disabled Send button is a second line of defence, not the only one (D-07):
    calling send_qc_email directly, bypassing the UI entirely, still refuses to send."""
    monkeypatch.delenv("SMTP_TO", raising=False)
    monkeypatch.delenv("SMTP_CC", raising=False)
    _RecordingSMTP.instances.clear()
    monkeypatch.setattr("smtplib.SMTP", _RecordingSMTP)

    with pytest.raises(RuntimeError, match="SMTP_TO"):
        app_functions["send_qc_email"](summary=None)

    assert _RecordingSMTP.instances == [], (
        "no SMTP connection attempt may occur when SMTP_TO is empty"
    )
