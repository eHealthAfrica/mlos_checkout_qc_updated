"""Standing guard: no tracked file carries an organisational-domain email address, and no
tracked Python source carries a generic address literal or a secret-shaped string constant
(DEPLOY-02/DEPLOY-03 regression guard, T-04-10/T-04-11).

Two independent scans, mirroring ``tests/test_no_streamlit_in_qc.py``'s AST-walk idiom and
``tests/test_no_password_storage.py``'s ``git ls-files``-scoped ``(offenders, scanned)`` shape:

- ``scan_tracked_files()`` walks every git-tracked file (the widest scope: any tracked file --
  docs, planning artifacts, fixtures -- could carry a recipient address) for ``ORG_ADDRESS_RE``,
  the organisational-domain address pattern.
- ``scan_tracked_python()`` walks ``ast.Constant`` string nodes in tracked ``.py`` files only for
  ``GENERIC_ADDRESS_RE`` (any address shape, not just the organisational domain) and
  ``looks_like_a_secret`` (an entropy-calibrated heuristic for a pasted credential).

The asymmetry is deliberate: DEPLOY-02's subject is the organisational recipient list, which
must be absent from every tracked file; a generic address in a planning document is prose (an
example, a contact mention), whereas a generic address in shipped Python is a hard-coded
recipient waiting to happen, so that narrower, harsher check applies to ``.py`` files only.

``ORG_ADDRESS_RE`` is built from ``qc.auth_domain.ALLOWED_DOMAIN`` rather than a retyped literal
domain -- after plan 04-02, the organisational domain is spelled in exactly one file in this
repository (``qc/auth_domain.py``), so this guard cannot drift from the thing it guards, and it
needs no self-exemption despite matching on the same domain string ``auth_domain`` also uses.

A plain length test is not enough for the secret heuristic: this project's fixtures are full of
36-character UUID literals (excluded via ``uuid.UUID``) and its loaders name a 34-character
database view, ``master_list_settlement_update_view`` (``qc/loaders.py``), whose character-entropy
(~3.57 bits/char) sits just ABOVE this guard's own 3.5 bit/char floor -- so entropy alone would
still flag it. Excluding it requires a second, independent signal: it is a syntactically valid,
all-lowercase Python identifier, the shape a hand-written view/table/module name takes and a
random high-entropy token essentially never does. A literal ``str.isidentifier()`` check (with no
further restriction) was tried first and rejected: ``secrets.token_urlsafe(48)``/
``secrets.token_hex(32)`` values collide with Python identifier syntax often enough (~30% and
~36% of random draws respectively, measured empirically) to make the "must flag a real generated
token" acceptance test flaky, because both alphabets are built entirely from identifier-legal
characters (``[A-Za-z0-9_-]``) minus only the hyphen. Restricting the identifier exclusion to
values that are ALSO purely lowercase letters/underscores (``^[a-z_]+$`` -- what every constant of
this shape in this codebase actually looks like) removes that collision: a 64-character
``token_hex`` string drawing from a 16-symbol hex alphabet has a vanishingly small chance of
containing zero digits, and a ``token_urlsafe`` string drawing from a 64-symbol base64url
alphabet has a vanishingly small chance of containing only the 27 lowercase-letter-or-underscore
symbols. This is documented here as a deviation from the plan's literal "not a valid Python
identifier" wording, not a departure from its purpose.
"""

import ast
import math
import re
import subprocess
import uuid
from pathlib import Path

import qc.auth_domain as auth_domain

REPO_ROOT = Path(__file__).resolve().parent.parent

# Built via chr(64), never a literal "@" string constant, so this guard's own source contains no
# string constant carrying "@" -- this file is itself tracked Python source, and the acceptance
# check for this task's Task 2 asserts exactly that (an AST walk over this file's own string
# constants must find none containing "@").
_AT = chr(64)
ORG_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+" + _AT + re.escape(auth_domain.ALLOWED_DOMAIN))
GENERIC_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+" + _AT + r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_SHAPE_RE = re.compile(r"^[A-Za-z0-9_\-]{32,}$")
_LOWER_SNAKE_CASE_RE = re.compile(r"^[a-z_]+$")


def _tracked_paths(pattern=None):
    """Every git-tracked path (optionally filtered by a pathspec pattern like ``*.py``),
    resolved via ``git ls-files`` so scope tracks the repository rather than a hard-coded list."""
    cmd = ["git", "ls-files"]
    if pattern:
        cmd.append(pattern)
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [REPO_ROOT / p for p in result.stdout.splitlines() if p.strip()]


# RFC 2606 (example.com/.net/.org/.edu) and RFC 6761 (test/invalid/localhost) reserve these
# domains/TLDs so they can never resolve to a real mailbox. Plan 04-01's tests/test_auth_domain.py
# already fixtures "someone" + _AT + "example.com", and this plan's own tests/test_smtp_recipients.py
# fixtures addresses on "x.test" -- both are exactly the kind of address a test file should use
# precisely because they cannot be a real hard-coded recipient. A generic-address scan that
# flagged these would make every test file that exercises address-parsing logic an automatic,
# permanent offender; excluding the reserved set keeps the guard's real subject (an address that
# COULD receive real mail, hard-coded into shipped Python) rather than any string shaped like one.
_RESERVED_EXAMPLE_DOMAINS = frozenset({"example.com", "example.net", "example.org", "example.edu"})
_RESERVED_TLDS = frozenset({"test", "invalid", "localhost", "example"})


def _is_reserved_example_domain(domain):
    domain = domain.lower()
    if domain in _RESERVED_EXAMPLE_DOMAINS:
        return True
    return domain.rsplit(".", 1)[-1] in _RESERVED_TLDS


def _has_offending_generic_address(value):
    """True when ``value`` contains a generic-address-shaped match whose domain is NOT one of
    the reserved example/test domains above."""
    for match in GENERIC_ADDRESS_RE.finditer(value):
        domain = match.group(0).split(_AT, 1)[-1]
        if not _is_reserved_example_domain(domain):
            return True
    return False


def _shannon_entropy(value):
    """Shannon entropy (bits per character) over ``value``'s character distribution."""
    if not value:
        return 0.0
    counts = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(value)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def looks_like_a_secret(value):
    """True only when ``value``: matches ``SECRET_SHAPE_RE`` (32+ chars, identifier-legal
    alphabet plus hyphen); does not parse as a UUID; is not an all-lowercase, underscore-only
    Python identifier (the shape a hand-written view/table/module name takes in this codebase --
    see module docstring for why this is narrower than a bare ``str.isidentifier()`` check); and
    has a Shannon entropy of at least 3.5 bits per character.
    """
    if not isinstance(value, str):
        return False
    if not SECRET_SHAPE_RE.match(value):
        return False
    try:
        uuid.UUID(value)
        return False
    except (ValueError, AttributeError, TypeError):
        pass
    if value.isidentifier() and _LOWER_SNAKE_CASE_RE.match(value):
        return False
    if _shannon_entropy(value) < 3.5:
        return False
    return True


def scan_tracked_files():
    """Return ``(offenders, scanned)``: offenders is a sorted list of tracked file paths
    containing an ``ORG_ADDRESS_RE`` match; scanned is the number of tracked files actually
    examined as text (a path whose bytes do not decode as UTF-8 is skipped, not crashed on --
    the two ward-boundary CSVs decode fine, but a future binary asset must not break the guard)."""
    offenders = []
    scanned = 0
    for path in sorted(_tracked_paths()):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        if ORG_ADDRESS_RE.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    return sorted(offenders), scanned


def scan_tracked_python():
    """Return ``(offenders, scanned)``: offenders is a sorted list of tracked ``.py`` file paths
    carrying a generic address literal or a secret-shaped string constant; scanned is the number
    of tracked ``.py`` files actually examined."""
    offenders = []
    scanned = 0
    for path in sorted(_tracked_paths("*.py")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        tree = ast.parse(text, filename=str(path))
        offending = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _has_offending_generic_address(node.value) or looks_like_a_secret(node.value):
                    offending = True
                    break
        if offending:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    return sorted(offenders), scanned


# ─── Guard-of-the-guard: scope ───────────────────────────────────────────────────

def test_scan_tracked_files_scanned_a_nonzero_number_of_files():
    """A guard that greens because it resolved an empty or mis-resolved file list reports
    confidence it never earned -- assert a real minimum count of examined files."""
    _offenders, scanned = scan_tracked_files()
    assert scanned >= 100, f"expected at least 100 tracked files scanned, found {scanned}"


def test_scan_tracked_python_scanned_a_nonzero_number_of_files():
    _offenders, scanned = scan_tracked_python()
    assert scanned >= 40, f"expected at least 40 tracked .py files scanned, found {scanned}"


# ─── Guard-of-the-guard: pattern is proven live, not assumed ────────────────────

def test_org_address_pattern_matches_a_synthetic_address_built_from_allowed_domain():
    """Applied to synthetic in-memory text built from ALLOWED_DOMAIN (never a typed literal), the
    pattern must actually match -- a pattern that silently stopped matching (e.g. after a typo'd
    edit) would green the whole guard for the wrong reason."""
    synthetic = "contact" + _AT + auth_domain.ALLOWED_DOMAIN
    assert ORG_ADDRESS_RE.search(synthetic), "ORG_ADDRESS_RE failed to match its own subject domain"


# ─── The real assertions ─────────────────────────────────────────────────────────

def test_no_tracked_file_carries_an_organisational_address():
    offenders, _scanned = scan_tracked_files()
    assert not offenders, f"organisational-domain address found in: {offenders}"


def test_no_tracked_python_file_carries_a_generic_address_or_secret_shaped_literal():
    offenders, _scanned = scan_tracked_python()
    assert not offenders, f"generic address or secret-shaped literal found in: {offenders}"


# ─── looks_like_a_secret truth table ──────────────────────────────────────────────

def test_looks_like_a_secret_true_for_freshly_generated_tokens():
    """Generated fresh at test time (never a literal in this file, which is itself tracked
    Python source scanned by scan_tracked_python above) so no secret-shaped string is ever
    committed by this test's own existence."""
    import secrets

    assert looks_like_a_secret(secrets.token_urlsafe(48)) is True
    assert looks_like_a_secret(secrets.token_hex(32)) is True


def test_looks_like_a_secret_true_for_hyphenated_mixed_case_client_secret_shape():
    """Built by concatenating several short literals rather than one 34-character literal --
    this file is itself tracked Python source scanned by scan_tracked_python above, and no
    individual string constant here may itself be 32+ characters and secret-shaped (that would
    make this guard's own test file a permanent offender against itself)."""
    provider_style = "-" + "AbCdEfGh" + "IjKlMnOp" + "QrStUvWx" + "Yz0123456"
    assert len(provider_style) >= 32
    assert looks_like_a_secret(provider_style) is True


def test_looks_like_a_secret_false_for_a_uuid():
    assert looks_like_a_secret("11111111-1111-1111-1111-111111111111") is False


def test_looks_like_a_secret_false_for_the_real_view_name_constant():
    """The concrete false-positive this project's own tree presents: qc/loaders.py's MLOS_VIEW
    constant is 34 characters and its character-entropy sits just above the 3.5 bit/char floor,
    so this is the case that actually motivates the identifier exclusion, not a hypothetical."""
    assert looks_like_a_secret("master_list_settlement_update_view") is False


def test_looks_like_a_secret_false_for_a_sentence_with_spaces():
    sentence = "a forty character sentence with some spaces"
    assert len(sentence) >= 40
    assert looks_like_a_secret(sentence) is False
