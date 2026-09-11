"""Standing tests for qc.auth_domain's pure identity-domain extraction and access decision
(AUTH-01/D-04).

Fixture domains/emails are built by concatenating onto ``auth_domain.ALLOWED_DOMAIN`` rather
than typing an address literal — plan 04-02 installs a repository-wide scan that fails on any
address on that domain in any tracked file, and this file is tracked.
"""

from types import SimpleNamespace

import pytest

import qc.auth_domain as auth_domain

ALLOWED = auth_domain.ALLOWED_DOMAIN
IN_DOMAIN_EMAIL = "officer" + "@" + ALLOWED
OUT_OF_DOMAIN_EMAIL = "someone@example.com"


# ─── extract_domain ──────────────────────────────────────────────────────────────

def test_extract_domain_prefers_the_hd_claim_when_present():
    user = SimpleNamespace(hd=ALLOWED, email=OUT_OF_DOMAIN_EMAIL)
    assert auth_domain.extract_domain(user) == ALLOWED


def test_extract_domain_falls_back_to_email_domain_when_hd_is_none():
    user = SimpleNamespace(hd=None, email=IN_DOMAIN_EMAIL)
    assert auth_domain.extract_domain(user) == ALLOWED


def test_extract_domain_returns_empty_string_when_neither_claim_yields_a_domain():
    user = SimpleNamespace(hd=None, email="")
    assert auth_domain.extract_domain(user) == ""

    user_no_at = SimpleNamespace(hd=None, email="not-an-email")
    assert auth_domain.extract_domain(user_no_at) == ""


def test_extract_domain_accepts_a_mapping_as_well_as_an_attribute_object():
    """st.user is dict-like; extract_domain must work identically for a plain dict."""
    mapping_user = {"hd": None, "email": IN_DOMAIN_EMAIL}
    assert auth_domain.extract_domain(mapping_user) == ALLOWED


def test_extract_domain_lowercases_and_strips_the_result():
    user = SimpleNamespace(hd=f"  {ALLOWED.upper()}  ", email="")
    assert auth_domain.extract_domain(user) == ALLOWED


# ─── is_authorized_domain ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "domain,expected",
    [
        (ALLOWED, True),
        (ALLOWED.upper(), True),
        ("sub." + ALLOWED, False),
        ("not" + ALLOWED, False),
        (ALLOWED + ".evil.com", False),
        ("", False),
    ],
)
def test_is_authorized_domain_exact_case_folded_match_only(domain, expected):
    """A subdomain, a domain that merely ends with the allowed domain, and a domain that merely
    starts with it must all be refused -- only exact (case-folded) equality is True."""
    assert auth_domain.is_authorized_domain(domain) is expected


# ─── bypass_requested ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("True", True),
        ("YES", True),
        ("yes", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("   ", False),
    ],
)
def test_bypass_requested_accepted_and_rejected_values(value, expected):
    assert auth_domain.bypass_requested({"MLOS_AUTH_DISABLED": value}) is expected


def test_bypass_requested_false_when_variable_absent():
    assert auth_domain.bypass_requested({}) is False


# ─── decide_access ────────────────────────────────────────────────────────────────

def test_decide_access_unconfigured():
    decision = auth_domain.decide_access(
        configured=False, bypass=False, logged_in=False, domain=""
    )
    assert decision.outcome == "unconfigured"
    assert decision.flag_ignored is False


def test_decide_access_bypass():
    decision = auth_domain.decide_access(
        configured=False, bypass=True, logged_in=False, domain=""
    )
    assert decision.outcome == "bypass"
    assert decision.flag_ignored is False


def test_decide_access_signin_when_not_logged_in():
    decision = auth_domain.decide_access(
        configured=True, bypass=False, logged_in=False, domain=""
    )
    assert decision.outcome == "signin"
    assert decision.flag_ignored is False


def test_decide_access_refused_when_out_of_domain():
    decision = auth_domain.decide_access(
        configured=True, bypass=False, logged_in=True, domain="example.com"
    )
    assert decision.outcome == "refused"
    assert decision.flag_ignored is False


def test_decide_access_allowed_when_in_domain():
    decision = auth_domain.decide_access(
        configured=True, bypass=False, logged_in=True, domain=ALLOWED
    )
    assert decision.outcome == "allowed"
    assert decision.flag_ignored is False


def test_decide_access_flag_ignored_true_only_when_configured_and_bypass_both_true():
    """Configured + bypass never reaches the bypass outcome -- it only raises flag_ignored,
    which the gate surfaces as a warning (D-03, RESEARCH Pitfall 4)."""
    decision = auth_domain.decide_access(
        configured=True, bypass=True, logged_in=True, domain=ALLOWED
    )
    assert decision.outcome == "allowed"
    assert decision.flag_ignored is True

    decision2 = auth_domain.decide_access(
        configured=True, bypass=True, logged_in=False, domain=""
    )
    assert decision2.outcome == "signin"
    assert decision2.flag_ignored is True


@pytest.mark.parametrize("configured", [True, False])
@pytest.mark.parametrize("bypass", [True, False])
@pytest.mark.parametrize("logged_in", [True, False])
@pytest.mark.parametrize("domain", [ALLOWED, "example.com", ""])
def test_decide_access_reproduces_the_full_table_and_flag_ignored_formula(
    configured, bypass, logged_in, domain
):
    """Exhaustive over the three booleans and an in/out/empty domain value -- every combination
    must land on one of the five documented OUTCOMES, and flag_ignored must always equal
    configured and bypass."""
    decision = auth_domain.decide_access(
        configured=configured, bypass=bypass, logged_in=logged_in, domain=domain
    )
    assert decision.outcome in auth_domain.OUTCOMES
    assert decision.flag_ignored == (configured and bypass)

    if not configured:
        assert decision.outcome == ("bypass" if bypass else "unconfigured")
    elif not logged_in:
        assert decision.outcome == "signin"
    elif domain == ALLOWED:
        assert decision.outcome == "allowed"
    else:
        assert decision.outcome == "refused"
