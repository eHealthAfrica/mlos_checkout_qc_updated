"""Standing tests for auth.py's login gate: the complete decide_access truth table, the three
stopping branches (unconfigured/bypass/refused), current_officer, and the two structural
assertions on require_login's shape (AUTH-01/D-03/D-05).

The Streamlit surface auth.py uses is replaced wholesale by a recording double (FakeSt),
monkeypatched onto ``auth.st`` — this is how these branches get covered without a live
Streamlit session. Fixture emails/domains are built by concatenating onto
``auth_domain.ALLOWED_DOMAIN`` rather than typing an address literal on that domain (plan
04-02's repository-wide address scan applies to every tracked file, including this one).
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

import auth
import qc.auth_domain as auth_domain

AUTH_PY = Path(__file__).resolve().parent.parent / "auth.py"

IN_DOMAIN = auth_domain.ALLOWED_DOMAIN
OUT_OF_DOMAIN = "example.com"
IN_DOMAIN_EMAIL = "officer" + "@" + IN_DOMAIN
OUT_OF_DOMAIN_EMAIL = "someone@" + OUT_OF_DOMAIN

FULL_AUTH_ENV = {
    "REDIRECT_URI": "https://example.hf.space/oauth2callback",
    "COOKIE_SECRET": "a-strong-random-secret",
    "GOOGLE_CLIENT_ID": "cid",
    "GOOGLE_CLIENT_SECRET": "csec",
}


class FakeSt:
    """Recording double for the Streamlit surface auth.py uses. Every call is appended to
    ``self.calls`` as ``(method_name, args, kwargs)`` — nothing here talks to a real Streamlit
    session."""

    def __init__(self, user=None):
        self.calls = []
        self.user = user if user is not None else SimpleNamespace(is_logged_in=False)

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def warning(self, *a, **k):
        self._record("warning", *a, **k)

    def error(self, *a, **k):
        self._record("error", *a, **k)

    def header(self, *a, **k):
        self._record("header", *a, **k)

    def write(self, *a, **k):
        self._record("write", *a, **k)

    def markdown(self, *a, **k):
        self._record("markdown", *a, **k)

    def button(self, *a, **k):
        self._record("button", *a, **k)
        return False

    def file_uploader(self, *a, **k):
        self._record("file_uploader", *a, **k)

    def login(self, *a, **k):
        self._record("login", *a, **k)

    def logout(self, *a, **k):
        self._record("logout", *a, **k)

    def stop(self, *a, **k):
        self._record("stop", *a, **k)


def _texts_for(fake, method):
    """Flatten every string arg/kwarg-value recorded for `method` into one search haystack."""
    parts = []
    for name, args, kwargs in fake.calls:
        if name != method:
            continue
        for a in args:
            if isinstance(a, str):
                parts.append(a)
        for v in kwargs.values():
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


def _no_file_uploader(fake):
    return not any(name == "file_uploader" for name, _args, _kwargs in fake.calls)


def _clear_auth_env(monkeypatch):
    for key in (
        "REDIRECT_URI", "COOKIE_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
        "MLOS_AUTH_DISABLED", "DATA_TEAM_CONTACT",
    ):
        monkeypatch.delenv(key, raising=False)


def _configure_full_auth_env(monkeypatch):
    for k, v in FULL_AUTH_ENV.items():
        monkeypatch.setenv(k, v)


# ─── decide_access truth table: 16 combinations + 2 empty-domain rows ───────────

@pytest.mark.parametrize("configured", [True, False])
@pytest.mark.parametrize("bypass", [True, False])
@pytest.mark.parametrize("logged_in", [True, False])
@pytest.mark.parametrize("domain", [IN_DOMAIN, OUT_OF_DOMAIN])
def test_decide_access_truth_table_sixteen_combinations(configured, bypass, logged_in, domain):
    decision = auth_domain.decide_access(
        configured=configured, bypass=bypass, logged_in=logged_in, domain=domain
    )
    assert decision.outcome in auth_domain.OUTCOMES
    assert decision.flag_ignored == (configured and bypass)


def test_decide_access_empty_domain_unconfigured_row():
    decision = auth_domain.decide_access(configured=False, bypass=False, logged_in=False, domain="")
    assert decision.outcome == "unconfigured"
    assert decision.flag_ignored is False


def test_decide_access_empty_domain_refused_row():
    decision = auth_domain.decide_access(configured=True, bypass=False, logged_in=True, domain="")
    assert decision.outcome == "refused"
    assert decision.flag_ignored is False


# ─── bypass_requested value table ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("Yes", True),
        ("0", False), ("false", False), ("", False), ("   ", False),
    ],
)
def test_bypass_requested_value_table(value, expected):
    assert auth_domain.bypass_requested({"MLOS_AUTH_DISABLED": value}) is expected


def test_bypass_requested_absent_key_is_false():
    assert auth_domain.bypass_requested({}) is False


# ─── current_officer ──────────────────────────────────────────────────────────────

def test_current_officer_signed_out_fake_returns_none(monkeypatch):
    monkeypatch.setattr(auth, "st", FakeSt(user=SimpleNamespace(is_logged_in=False)))
    assert auth.current_officer() is None


def test_current_officer_signed_in_fake_returns_three_key_dict(monkeypatch):
    user = SimpleNamespace(
        is_logged_in=True, email=IN_DOMAIN_EMAIL, name="Officer Name", hd=IN_DOMAIN,
    )
    monkeypatch.setattr(auth, "st", FakeSt(user=user))
    officer = auth.current_officer()
    assert set(officer.keys()) == {"email", "name", "domain"}
    assert officer["domain"] == IN_DOMAIN


# ─── require_login branches ──────────────────────────────────────────────────────

def test_unconfigured_branch_names_missing_vars_and_bypass_var(monkeypatch):
    _clear_auth_env(monkeypatch)
    fake = FakeSt(user=SimpleNamespace(is_logged_in=False))
    monkeypatch.setattr(auth, "st", fake)

    result = auth.require_login()

    assert result is None
    error_text = _texts_for(fake, "error")
    for key in auth.secrets_materializer.missing_auth_env_keys({}):
        assert key in error_text, f"expected {key!r} in unconfigured error text: {error_text!r}"
    assert auth.BYPASS_ENV_VAR in error_text
    assert _no_file_uploader(fake)


def test_bypass_branch_records_a_warning_naming_the_variable(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("MLOS_AUTH_DISABLED", "1")
    fake = FakeSt(user=SimpleNamespace(is_logged_in=False))
    monkeypatch.setattr(auth, "st", fake)

    result = auth.require_login()

    assert result is None
    warning_text = _texts_for(fake, "warning")
    assert auth.BYPASS_ENV_VAR in warning_text
    assert _no_file_uploader(fake)


def test_refused_branch_records_the_contact_from_environment(monkeypatch):
    _configure_full_auth_env(monkeypatch)
    monkeypatch.setenv("DATA_TEAM_CONTACT", "data-team-contact-address")
    user = SimpleNamespace(is_logged_in=True, email=OUT_OF_DOMAIN_EMAIL, hd=None)
    fake = FakeSt(user=user)
    monkeypatch.setattr(auth, "st", fake)

    result = auth.require_login()

    assert result is None
    write_text = _texts_for(fake, "write")
    assert "data-team-contact-address" in write_text
    assert _no_file_uploader(fake)


def test_refused_branch_fallback_sentence_when_contact_unset(monkeypatch):
    """The fallback CONTACT sentence specifically must carry neither 'None' nor an '@' — not
    the whole refusal page, which legitimately echoes the signed-in visitor's own email (and
    therefore an '@') in its opening statement."""
    _configure_full_auth_env(monkeypatch)
    monkeypatch.delenv("DATA_TEAM_CONTACT", raising=False)
    user = SimpleNamespace(is_logged_in=True, email=OUT_OF_DOMAIN_EMAIL, hd=None)
    fake = FakeSt(user=user)
    monkeypatch.setattr(auth, "st", fake)

    auth.require_login()

    write_calls = [c for c in fake.calls if c[0] == "write"]
    assert len(write_calls) >= 2, write_calls
    contact_sentence = write_calls[-1][1][0]
    assert "None" not in contact_sentence
    assert "@" not in contact_sentence


def test_signin_branch_renders_signin_screen_and_no_file_uploader(monkeypatch):
    _configure_full_auth_env(monkeypatch)
    fake = FakeSt(user=SimpleNamespace(is_logged_in=False))
    monkeypatch.setattr(auth, "st", fake)

    result = auth.require_login()

    assert result is None
    assert any(name == "header" for name, _a, _k in fake.calls)
    assert _no_file_uploader(fake)


def test_allowed_branch_returns_officer_and_renders_no_error(monkeypatch):
    _configure_full_auth_env(monkeypatch)
    user = SimpleNamespace(is_logged_in=True, email=IN_DOMAIN_EMAIL, hd=IN_DOMAIN, name="Officer")
    fake = FakeSt(user=user)
    monkeypatch.setattr(auth, "st", fake)

    officer = auth.require_login()

    assert officer is not None
    assert officer["domain"] == IN_DOMAIN
    assert not any(name == "error" for name, _a, _k in fake.calls)
    assert _no_file_uploader(fake)


# ─── Structural assertions (regression guard) ────────────────────────────────────

def _require_login_funcdef():
    tree = ast.parse(AUTH_PY.read_text())
    return next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "require_login"
    )


def test_require_login_has_exactly_two_return_statements():
    func = _require_login_funcdef()
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 2, len(returns)


def test_require_login_ends_in_a_bare_st_stop_call():
    func = _require_login_funcdef()
    last = func.body[-1]
    assert isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
    assert getattr(last.value.func, "attr", None) == "stop"
