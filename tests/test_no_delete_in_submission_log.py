"""Standing append-only guard (D-16, AUDIT-04): no tracked Python source may call a repo-file,
repo-folder or repo deletion, construct a commit-delete operation, or upload to a hand-written
literal path. Follows the exact idiom of ``tests/test_no_upload_persistence.py`` and
``tests/test_no_committed_secrets.py``: ``git ls-files``-scoped file resolution, an
``(offenders, scanned)`` return shape, a known-exception list asserted to be exactly what it
claims, and a non-vacuity self-check.

AUDIT-04 says the application offers no path to edit or delete a past record, and a token
scoped to write-only (D-15) is the second line of defence, not the first -- a token's
permissions are not visible to the test suite and can be changed in a web console by anyone with
access to the Space. This guard is the first line: create-only calls with unique paths, proven at
test time rather than merely hoped for at token-configuration time.

Each test's docstring says what would silently pass without its assertion, following
``tests/test_environment_pins.py``'s discipline.
"""

import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# This guard's own file necessarily names the forbidden call spellings (`delete_file`,
# `delete_folder`, `delete_repo`, a `*Delete` commit-operation construction) -- they are its
# subject matter, appearing in synthetic source strings and set literals below, not as calls this
# file itself makes.
GUARD_OWN_PATH = "tests/test_no_delete_in_submission_log.py"

# tests/test_audit03_concurrent_writes.py (created in plan 05-04) legitimately creates and then
# removes its OWN disposable Dataset repo as its test lifecycle -- that is the test's cleanup of
# a repo it made for itself, not an application path. D-16's requirement is about what the
# *application* can do to a record, not about a test tearing down its own throwaway fixture repo.
AUDIT03_TEST_PATH = "tests/test_audit03_concurrent_writes.py"

_EXCLUDED_PATHS = {GUARD_OWN_PATH, AUDIT03_TEST_PATH}

DELETE_CALL_NAMES = {"delete_file", "delete_folder", "delete_repo"}


def _tracked_python_files():
    """Every tracked ``.py`` path, resolved via ``git ls-files`` so the scan scope is exactly
    tracked source and cannot drift silently as files are added or removed -- the same idiom
    ``tests/test_no_upload_persistence.py`` and ``tests/test_no_committed_secrets.py`` use."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return [REPO_ROOT / p for p in result.stdout.splitlines() if p.strip()]


def _call_name(node: ast.Call):
    """Return a call's function name whether the call target is a bare name (``delete_repo(...)``)
    or an attribute access (``api.delete_repo(...)``) -- matching on the final component only, so
    an aliased import (``from huggingface_hub import delete_repo as remove_repo``) cannot slip
    past a dotted-path-only match."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def delete_shaped_calls(tree: ast.AST) -> list:
    """Every ``Call`` node whose function name matches a repo-file, repo-folder or repo deletion,
    or whose name ends in ``Delete`` (a commit-delete-operation construction, e.g.
    ``CommitOperationDelete(...)``)."""
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        if name in DELETE_CALL_NAMES or name.endswith("Delete"):
            offenders.append(node)
    return offenders


def overwrite_shaped_uploads(tree: ast.AST) -> list:
    """Every ``upload_file(...)`` call whose ``path_in_repo`` keyword is a plain string constant
    -- the only shape in which a caller could name a path that already exists. The shipped call
    passes a name bound from ``mint_record_id_and_path``, which returns a path containing a fresh
    ``uuid4`` and therefore has never existed."""
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "upload_file":
            continue
        for kw in node.keywords:
            if kw.arg == "path_in_repo" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                offenders.append(node)
    return offenders


def scan_tracked_python() -> "tuple[list[str], int]":
    """Return ``(offenders, scanned)``: offenders is a sorted list of
    ``"<relative path>: <unparsed call>"`` entries for every delete-shaped or overwrite-shaped
    call found in non-excluded tracked source, and scanned is the number of tracked ``.py`` files
    actually examined (excluding the two known exceptions). A guard that greened because it
    resolved an empty or mis-resolved file list would report confidence it never earned -- see
    ``test_guard_scanned_at_least_20_files`` for the assertion this function's own return value
    cannot fake."""
    offenders = []
    scanned = 0
    for path in sorted(_tracked_python_files()):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _EXCLUDED_PATHS:
            continue
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in delete_shaped_calls(tree) + overwrite_shaped_uploads(tree):
            offenders.append(f"{rel}: {ast.unparse(node)}")
    return sorted(offenders), scanned


# ─── The real, shipped source is clean ────────────────────────────────────────────────────────

def test_scan_tracked_python_reports_zero_offenders():
    """The core AUDIT-04 assertion: nothing in tracked application source calls a delete-shaped
    or overwrite-shaped operation."""
    offenders, _scanned = scan_tracked_python()
    assert offenders == [], offenders


def test_scan_tracked_python_scanned_at_least_20_files():
    """A guard that greens because it resolved an empty or mis-resolved file list reports
    confidence it never earned -- assert a real minimum count of examined files."""
    _offenders, scanned = scan_tracked_python()
    assert scanned >= 20, f"expected at least 20 tracked .py files scanned, found {scanned}"


def test_exclusion_set_has_exactly_two_members_and_both_are_test_paths():
    """Without pinning the exact size, a future contributor could quietly widen the exclusion set
    to smuggle a real offender past this guard under the cover of 'just another test fixture'."""
    assert len(_EXCLUDED_PATHS) == 2, _EXCLUDED_PATHS
    assert _EXCLUDED_PATHS == {GUARD_OWN_PATH, AUDIT03_TEST_PATH}
    assert all(p.startswith("tests/") for p in _EXCLUDED_PATHS), _EXCLUDED_PATHS


# ─── Guard self-test: proven capable of failing on four synthetic delete shapes ──────────────

def test_delete_shaped_calls_flags_repo_file_deletion():
    """Without this synthetic-source proof, a helper that unconditionally returned an empty list
    would still green forever -- this is what makes the guard credible rather than decorative."""
    tree = ast.parse('api.delete_file(path_in_repo="records/2026/09/x.json", repo_id=r)')
    assert len(delete_shaped_calls(tree)) == 1


def test_delete_shaped_calls_flags_repo_folder_deletion():
    tree = ast.parse('api.delete_folder(path_in_repo="records/2026/09", repo_id=r)')
    assert len(delete_shaped_calls(tree)) == 1


def test_delete_shaped_calls_flags_repo_deletion():
    tree = ast.parse('api.delete_repo(repo_id=r, repo_type="dataset")')
    assert len(delete_shaped_calls(tree)) == 1


def test_delete_shaped_calls_flags_commit_delete_operation_construction():
    """Matches on the callable's final attribute name only (not a hard-coded, fully-dotted
    ``huggingface_hub.CommitOperationDelete`` literal), so a call reached through any module
    alias (``import huggingface_hub as hf; hf.CommitOperationDelete(...)``) still cannot slip
    past this check the way a dotted-path-string match would if the alias name differed."""
    tree = ast.parse(
        "import huggingface_hub as hf\n"
        'op = hf.CommitOperationDelete(path_in_repo="records/2026/09/x.json")'
    )
    assert len(delete_shaped_calls(tree)) == 1


# ─── Accept case: the ordinary, shipped upload shape is not flagged by either helper ──────────

def test_ordinary_upload_is_not_flagged_by_either_helper():
    """The guard must not simply flag everything -- the shipped call shape (a fresh, minted path
    bound to a name, never a literal) must pass clean through both helpers."""
    tree = ast.parse(
        "path_in_repo = repo_path\n"
        "api.upload_file(path_or_fileobj=payload, path_in_repo=path_in_repo, "
        'repo_id=repo_id, repo_type="dataset")'
    )
    assert delete_shaped_calls(tree) == []
    assert overwrite_shaped_uploads(tree) == []


# ─── overwrite_shaped_uploads: proven capable of failing, and clean over real source ──────────

def test_overwrite_shaped_uploads_flags_a_literal_path_in_repo_string():
    """Without this synthetic-source proof, a helper that unconditionally returned an empty list
    would green even against a hand-written, reusable path literal."""
    tree = ast.parse(
        'api.upload_file(path_or_fileobj=payload, path_in_repo="records/fixed.json", '
        'repo_id=repo_id, repo_type="dataset")'
    )
    assert len(overwrite_shaped_uploads(tree)) == 1


def test_overwrite_shaped_uploads_reports_zero_offenders_over_tracked_application_source():
    """Every ``upload_file`` call found anywhere in tracked application source must pass
    ``path_in_repo`` as a name bound from a freshly minted path, never a string literal -- so no
    call can target a path chosen by hand."""
    offenders = []
    for path in sorted(_tracked_python_files()):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _EXCLUDED_PATHS or not path.is_file():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        offenders.extend(overwrite_shaped_uploads(tree))
    assert offenders == [], [ast.unparse(o) for o in offenders]
