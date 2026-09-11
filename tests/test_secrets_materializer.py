"""Standing tests for qc.secrets_materializer's pure [auth] TOML rendering (AUTH-01/D-01).

Each test's docstring states what would silently pass without this specific assertion —
following tests/test_environment_pins.py's docstring discipline.
"""

import tomllib

import qc.secrets_materializer as sm

_FULL_ENV = {
    "REDIRECT_URI": "https://example.hf.space/oauth2callback",
    "COOKIE_SECRET": "a-strong-random-cookie-secret",
    "GOOGLE_CLIENT_ID": "client-id-value",
    "GOOGLE_CLIENT_SECRET": "client-secret-value",
}


def test_build_secrets_toml_is_none_for_an_empty_environment():
    """A substring-matching assertion could pass on a stray empty string; asserting the exact
    Python value None is what proves the dev/pytest no-op path never renders a table at all."""
    assert sm.build_secrets_toml({}) is None


def test_build_secrets_toml_renders_a_single_auth_table_in_fixed_order():
    """Without parsing the rendered text as real TOML (tomllib.loads), a test could pass on
    output that merely contains the right substrings in the wrong order or shape — this parses
    the string as TOML and asserts on the parsed structure, not on raw text."""
    rendered = sm.build_secrets_toml(_FULL_ENV)
    assert rendered is not None
    parsed = tomllib.loads(rendered)
    assert list(parsed.keys()) == ["auth"]
    assert list(parsed["auth"].keys()) == [
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    ]
    assert parsed["auth"]["redirect_uri"] == _FULL_ENV["REDIRECT_URI"]
    assert parsed["auth"]["cookie_secret"] == _FULL_ENV["COOKIE_SECRET"]
    assert parsed["auth"]["client_id"] == _FULL_ENV["GOOGLE_CLIENT_ID"]
    assert parsed["auth"]["client_secret"] == _FULL_ENV["GOOGLE_CLIENT_SECRET"]
    assert parsed["auth"]["server_metadata_url"] == sm.GOOGLE_METADATA_URL


def test_build_secrets_toml_is_deterministic_regardless_of_input_dict_order():
    """A render that depended on dict iteration order would still pass a same-object comparison
    (the exact same dict, iterated the same way twice) — this builds two dicts with the SAME
    keys inserted in a DIFFERENT order to prove the fixed _TOML_KEY_ORDER, not input order,
    controls the output."""
    reordered_env = dict(reversed(list(_FULL_ENV.items())))
    assert sm.build_secrets_toml(_FULL_ENV) == sm.build_secrets_toml(reordered_env)
    # And calling twice with the identical input is also byte-for-byte equal.
    assert sm.build_secrets_toml(_FULL_ENV) == sm.build_secrets_toml(_FULL_ENV)


def test_build_secrets_toml_escapes_quotes_and_backslashes_safely():
    """A raw f-string interpolation would produce invalid or silently-wrong TOML on a secret
    containing a double quote or backslash; this proves the rendered text still round-trips
    through tomllib.loads and recovers the exact original value."""
    env = dict(_FULL_ENV)
    env["COOKIE_SECRET"] = 'weird"secret\\with\\backslashes'
    rendered = sm.build_secrets_toml(env)
    parsed = tomllib.loads(rendered)
    assert parsed["auth"]["cookie_secret"] == env["COOKIE_SECRET"]


def test_missing_auth_env_keys_reports_all_four_sorted_for_an_empty_environment():
    """A test asserting only length or set-equality would miss an ordering regression — sorting
    is an explicit contract downstream messages rely on."""
    assert sm.missing_auth_env_keys({}) == sorted(sm.AUTH_ENV_KEYS)


def test_missing_auth_env_keys_is_empty_for_a_complete_environment():
    assert sm.missing_auth_env_keys(_FULL_ENV) == []


def test_missing_auth_env_keys_treats_whitespace_only_value_as_missing():
    """A naive `if key not in env` check would treat a saved-but-blank Space secret field as
    present; this proves whitespace-only counts as missing too."""
    env = dict(_FULL_ENV)
    env["COOKIE_SECRET"] = "   "
    assert sm.missing_auth_env_keys(env) == ["COOKIE_SECRET"]


def test_auth_env_is_complete_matches_missing_keys_being_empty():
    assert sm.auth_env_is_complete({}) is False
    assert sm.auth_env_is_complete(_FULL_ENV) is True


def test_auth_env_keys_tuple_has_the_four_expected_names_in_declared_order():
    """Pins the exact tuple contents and order the plan specifies -- a later refactor that
    silently reorders or renames a key would be caught here rather than downstream."""
    assert sm.AUTH_ENV_KEYS == (
        "REDIRECT_URI",
        "COOKIE_SECRET",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    )
