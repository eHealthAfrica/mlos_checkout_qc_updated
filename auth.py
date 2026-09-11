"""Thin Streamlit-touching login gate for AUTH-01/AUTH-02, new for D-01/D-03/D-04/D-05/D-09.

Thin gate only: this module materialises the ``[auth]`` secrets table, reads the four
environment-driven inputs a Streamlit session can observe, and renders whichever outcome
``qc.auth_domain.decide_access`` already computed. All decision logic — the domain comparison,
the opt-out flag's semantics, the five-outcome table — lives in ``qc.auth_domain``; all TOML
rendering lives in ``qc.secrets_materializer``. This module owns nothing but the
Streamlit-facing wiring, matching ``send_qc_email``'s own "thin sender only" framing
(``app.py``'s Email Sender section).
"""

import os
from pathlib import Path

import streamlit as st

import qc.auth_domain as auth_domain
import qc.secrets_materializer as secrets_materializer

# ─── Constants ──────────────────────────────────────────────────────────────────
SECRETS_PATH = Path(".streamlit") / "secrets.toml"
BYPASS_ENV_VAR = "MLOS_AUTH_DISABLED"
CONTACT_ENV_VAR = "DATA_TEAM_CONTACT"


# ─── Secrets Read ───────────────────────────────────────────────────────────────
def secret(key, default=""):
    """Read ``key`` from the environment first (as given, then upper-cased), then fall back to
    ``st.secrets`` inside a ``try/except`` so a missing or unreadable secrets file falls back to
    ``default`` instead of raising. Hugging Face Spaces injects flat environment variables that
    ``st.secrets`` does not see (RESEARCH assumption A2); this keeps existing lower-case keys
    such as ``smtp_host`` resolving from a local ``.streamlit/secrets.toml`` unchanged.
    """
    value = os.environ.get(key)
    if value is None:
        value = os.environ.get(key.upper())
    if value is not None:
        return value
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# ─── Secrets Materialisation ────────────────────────────────────────────────────
def materialize_auth_secrets(env=None):
    """Render ``.streamlit/secrets.toml``'s ``[auth]`` table from ``env`` (defaults to
    ``os.environ``).

    Returns ``False`` immediately when ``qc.secrets_materializer.build_secrets_toml`` returns
    ``None`` (incomplete environment — the dev/pytest path). Otherwise creates ``.streamlit/``
    if needed, writes only when the rendered text differs from the file's current content, and
    returns ``True``. The comparison is not an optimisation: this function runs at module scope
    on every Streamlit rerun, and an unconditional write changes the file's mtime, which
    Streamlit's own secrets file watcher observes and turns into another rerun.
    """
    if env is None:
        env = os.environ
    rendered = secrets_materializer.build_secrets_toml(env)
    if rendered is None:
        return False
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRETS_PATH.exists() and SECRETS_PATH.read_text() == rendered:
        return True
    SECRETS_PATH.write_text(rendered)
    return True


def auth_is_configured(env=None):
    """Delegates to ``qc.secrets_materializer.auth_env_is_complete``."""
    if env is None:
        env = os.environ
    return secrets_materializer.auth_env_is_complete(env)


# ─── Screens ─────────────────────────────────────────────────────────────────────
def render_signin_screen():
    """AUTH-01/D-01: the only content a signed-out visitor ever sees."""
    st.header("Sign in required")
    st.write(
        "Sign in with your eHealth Africa organisational Google account to run a QC check. "
        "Open this tool at its direct address — the page ending in `.hf.space` — rather than "
        "through the Hugging Face Spaces embed page: the embed's iframe can silently drop the "
        "sign-in cookie and make a successful sign-in look signed out."
    )
    st.button("Sign in with Google", on_click=st.login)


def render_refusal_page(domain):
    """D-05/D-09: an authenticated, out-of-domain visitor. Renders no uploader, no tabs and no
    reference tables — only a refusal statement, the data-team contact (read from the secrets
    surface, never a literal address in source), and a sign-out control."""
    st.header("Access not authorised")
    email = ""
    try:
        email = getattr(st.user, "email", "") or ""
    except Exception:
        email = ""
    st.write(
        f"The signed-in account{f' ({email})' if email else ''} is not authorised for this "
        f"tool. Sign-in is restricted to the {auth_domain.ALLOWED_DOMAIN} organisational "
        "Google Workspace."
    )
    contact = secret(CONTACT_ENV_VAR)
    if contact:
        st.write(f"Contact the data team at {contact} for access.")
    else:
        st.write("Contact the data team for access.")
    st.button("Sign out", on_click=st.logout)


def render_bypass_banner():
    """D-03/T-04-03: visible only when configuration is absent AND the opt-out flag is set.
    Must be unmissable — RESEARCH Pitfall 4 makes this banner's visibility on a deployed Space
    the tell that the flag was left set there, where it must never be seen."""
    st.warning(
        f"Authentication is DISABLED for this session because {BYPASS_ENV_VAR} is set. This "
        f"must never be set on the deployed Space — {BYPASS_ENV_VAR} is a local/dev opt-out "
        "only."
    )


# ─── Gate ───────────────────────────────────────────────────────────────────────
def require_login():
    """Resolve the visitor into exactly one of the five ``qc.auth_domain.OUTCOMES`` and render
    that outcome. Exactly two ``return`` statements — ``allowed`` and ``bypass`` — and the last
    statement of the function body is a bare ``st.stop()``, reached by the three remaining
    outcomes (``unconfigured``, ``signin``, ``refused``), so no branch can fall through to the
    caller's uploader/sidebar code.
    """
    configured = auth_is_configured()
    bypass = auth_domain.bypass_requested(os.environ)
    try:
        logged_in = bool(getattr(st.user, "is_logged_in", False))
    except Exception:
        logged_in = False
    try:
        domain = auth_domain.extract_domain(st.user)
    except Exception:
        domain = ""

    decision = auth_domain.decide_access(
        configured=configured, bypass=bypass, logged_in=logged_in, domain=domain
    )

    if decision.flag_ignored:
        st.warning(
            f"{BYPASS_ENV_VAR} is set but ignored: sign-in is configured, so the opt-out flag "
            "has no effect."
        )

    if decision.outcome == "allowed":
        return current_officer()

    if decision.outcome == "bypass":
        render_bypass_banner()
        return None

    if decision.outcome == "unconfigured":
        missing = secrets_materializer.missing_auth_env_keys(os.environ)
        st.error(
            "This tool cannot run without sign-in configuration. Missing environment "
            f"variable(s): {', '.join(missing)}. Set {BYPASS_ENV_VAR} to enable an "
            "unauthenticated local/dev session explicitly — this must never be set on the "
            "deployed Space."
        )
    elif decision.outcome == "signin":
        render_signin_screen()
    elif decision.outcome == "refused":
        render_refusal_page(domain)

    st.stop()


def current_officer():
    """Returns ``None`` when not signed in, else a plain dict with keys ``email``, ``name`` and
    ``domain`` read off ``st.user``. This is the accessor Phase 5's submission log consumes;
    nothing else in the codebase may reach into ``st.user`` directly."""
    try:
        if not bool(getattr(st.user, "is_logged_in", False)):
            return None
    except Exception:
        return None
    return {
        "email": getattr(st.user, "email", None),
        "name": getattr(st.user, "name", None),
        "domain": auth_domain.extract_domain(st.user),
    }
