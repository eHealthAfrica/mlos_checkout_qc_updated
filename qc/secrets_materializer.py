"""Pure rendering of the nested [auth] TOML table from a flat environment mapping, new for
AUTH-01/D-01.

This module does NOT read the live environment (no ``os.environ`` access anywhere below), does
NOT import Streamlit, and does NOT perform any file I/O — the environment is always injected as
a plain mapping argument, matching ``qc/columns.py``'s avoidance of ambient state. It exists
because Streamlit loads ``secrets.toml`` lazily on first access, and that first access can be
triggered by an unrelated earlier ``st.*`` call, so a materialiser that runs late is a
materialiser that never ran in time (D-01, Streamlit issue #10543). This module only answers
"what should the rendered file contain"; ``auth.py`` owns "when to write it and whether it
changed".
"""

import json

# Order matters: this is the order the four inputs are emitted into the rendered table, and it
# is what `missing_auth_env_keys` walks to build its sorted result.
AUTH_ENV_KEYS = ("REDIRECT_URI", "COOKIE_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")

GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Fixed declared order for the rendered [auth] table's five keys. Fixed order is load bearing:
# it is what makes the render deterministic (same env -> byte-identical TOML twice) regardless
# of the input mapping's own iteration order, which is what makes the change-detecting write in
# auth.materialize_auth_secrets correct — that comparison only works if two calls with the same
# input always produce the same string.
_TOML_KEY_ORDER = (
    ("redirect_uri", "REDIRECT_URI"),
    ("cookie_secret", "COOKIE_SECRET"),
    ("client_id", "GOOGLE_CLIENT_ID"),
    ("client_secret", "GOOGLE_CLIENT_SECRET"),
)


def missing_auth_env_keys(env):
    """Return the sorted subset of ``AUTH_ENV_KEYS`` whose value in ``env`` is absent, ``None``,
    or whitespace-only. A key present but blank counts as missing — a Space secret UI that lets
    an officer save an empty field must not silently pass as "configured"."""
    missing = [key for key in AUTH_ENV_KEYS if not str(env.get(key) or "").strip()]
    return sorted(missing)


def auth_env_is_complete(env):
    """True iff every key in ``AUTH_ENV_KEYS`` is present and non-blank in ``env``."""
    return not missing_auth_env_keys(env)


def build_secrets_toml(env):
    """Render a single-table TOML string (``[auth]``) from a flat environment mapping.

    Returns ``None`` when the environment is incomplete (dev/pytest path — nothing to render).
    Otherwise returns a string carrying exactly ``redirect_uri``, ``cookie_secret``,
    ``client_id``, ``client_secret``, ``server_metadata_url``, in that fixed declared order,
    each value escaped with ``json.dumps`` — TOML basic strings and JSON strings share escaping
    for the characters that can appear in these values, and a raw f-string interpolation would
    break on a secret containing a quote or backslash.

    ``build_secrets_toml(full_env) == build_secrets_toml(full_env)`` byte for byte: the key
    order is fixed above and never depends on ``env``'s own iteration order.
    """
    if not auth_env_is_complete(env):
        return None

    lines = ["[auth]"]
    for toml_key, env_key in _TOML_KEY_ORDER:
        lines.append(f"{toml_key} = {json.dumps(str(env[env_key]))}")
    lines.append(f"server_metadata_url = {json.dumps(GOOGLE_METADATA_URL)}")
    return "\n".join(lines) + "\n"
