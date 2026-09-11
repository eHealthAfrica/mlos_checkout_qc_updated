"""Pure identity-domain extraction and the five-outcome access decision, new for AUTH-01/D-04.

A domain allow-list and an explicit email allow-list were both offered during discussion and
NOT chosen (D-04): sign-in is accepted only for the exact ``ehealthnigeria.org`` domain, checked
with case-folded string equality and nothing else. A later contributor must not "simplify" that
into an ``endswith``/``in``/membership test — that is precisely the shape D-04 rejected, because
a subdomain or a suffix/prefix look-alike must be refused, not admitted.

No ``import streamlit`` anywhere in this module — enforced by
``tests/test_no_streamlit_in_qc.py``.
"""

from dataclasses import dataclass

ALLOWED_DOMAIN = "ehealthnigeria.org"

OUTCOMES = ("unconfigured", "bypass", "signin", "refused", "allowed")


@dataclass(frozen=True)
class AccessDecision:
    outcome: str
    flag_ignored: bool


def _read_claim(user, name):
    """Read ``name`` off ``user``, trying mapping subscription first, then attribute access, so
    a plain dict, a ``SimpleNamespace`` and ``st.user`` (which is dict-like) all work
    identically."""
    try:
        return user[name]
    except (TypeError, KeyError, IndexError):
        return getattr(user, name, None)


def extract_domain(user):
    """Return the identity domain for ``user``: the hosted-domain claim (``hd``) if present,
    else the text after the last ``@`` in ``email``, lower-cased and stripped. Returns ``""``
    when neither claim yields a usable domain. ``user`` may be a plain object, a mapping, or
    ``st.user`` itself (dict-like) — never assumed to be one specific type."""
    hd = _read_claim(user, "hd")
    if hd and str(hd).strip():
        return str(hd).strip().lower()

    email = str(_read_claim(user, "email") or "")
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def is_authorized_domain(domain, allowed=ALLOWED_DOMAIN):
    """Exact case-folded equality only — no ``endswith``, no ``in``, no suffix logic. That is
    the whole point (D-04): a subdomain of the allowed domain, a domain that merely ends with
    it, and a domain that merely starts with it are all refused; only the exact domain, in any
    letter case, is authorized."""
    return str(domain).strip().lower() == str(allowed).strip().lower()


def bypass_requested(env):
    """True only when ``env``'s ``MLOS_AUTH_DISABLED`` value, stripped and lower-cased, is one
    of ``1``, ``true``, ``yes``. The empty string, whitespace, ``0``, ``false`` and an absent
    key are all False."""
    value = env.get("MLOS_AUTH_DISABLED")
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes")


def decide_access(*, configured, bypass, logged_in, domain, allowed=ALLOWED_DOMAIN):
    """Keyword-only five-outcome access decision.

    ``flag_ignored`` is ``True`` exactly when ``configured and bypass`` — a deployed Space that
    has real ``[auth]`` configuration can never be opened by someone setting the opt-out
    variable; it only raises ``flag_ignored``, which the gate surfaces as a warning (D-03; the
    structural answer to RESEARCH Pitfall 4).

    | configured | bypass | logged_in | domain vs allowed | outcome       |
    |------------|--------|-----------|--------------------|---------------|
    | False      | False  | any       | any                | unconfigured  |
    | False      | True   | any       | any                | bypass        |
    | True       | any    | False     | any                | signin        |
    | True       | any    | True      | not equal          | refused       |
    | True       | any    | True      | equal              | allowed       |
    """
    flag_ignored = bool(configured and bypass)

    if not configured:
        outcome = "bypass" if bypass else "unconfigured"
    elif not logged_in:
        outcome = "signin"
    elif is_authorized_domain(domain, allowed):
        outcome = "allowed"
    else:
        outcome = "refused"

    return AccessDecision(outcome=outcome, flag_ignored=flag_ignored)
