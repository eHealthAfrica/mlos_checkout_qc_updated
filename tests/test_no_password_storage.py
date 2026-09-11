"""Standing guard: no tracked ``.py`` file ever renders a password-typed input field, and the
one SMTP credential the app handles (``smtp_pass``) is confined to ``send_qc_email``'s own body
(AUTH-02).

A guard that only grepped for the word "password" would pass a file that stored the value under
any other name — this asserts on the AST call-keyword shape (``type="password"``) across every
tracked file, and on the credential identifier's lexical scope in ``app.py``, rather than on a
word.
"""

import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PY = REPO_ROOT / "app.py"


def _tracked_python_files():
    """Every tracked ``.py`` path, resolved via ``git ls-files`` so the scope is exactly tracked
    source and cannot drift silently as files are added or removed."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return [REPO_ROOT / p for p in result.stdout.splitlines() if p.strip()]


def _password_type_offenders(tree) -> list:
    """Any ast.Call carrying a keyword argument literally named `type` whose constant string
    value is "password" (case-insensitive) — this is what proves the application never accepts
    a masked credential field, which is the substance of "stores no passwords"."""
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "type":
                continue
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                if kw.value.value.strip().lower() == "password":
                    offenders.append(ast.dump(node)[:120])
    return offenders


def scan_tracked_python() -> "tuple[list[str], int]":
    """Return (offenders, scanned): offenders is a sorted list of tracked file paths rendering a
    password-typed input; scanned is the number of tracked .py files actually examined."""
    offenders = []
    scanned = 0
    for path in sorted(_tracked_python_files()):
        if not path.is_file():
            continue
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        if _password_type_offenders(tree):
            offenders.append(str(path))
    return sorted(offenders), scanned


def _smtp_pass_name_nodes_outside_send_qc_email() -> "list[int]":
    """Every ast.Name node named smtp_pass in app.py must lie within send_qc_email's own
    lineno..end_lineno range. A reference anywhere else — a session-state assignment, a report
    cell, an email body — is an offender."""
    tree = ast.parse(APP_PY.read_text())
    func = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "send_qc_email"
    )
    lo, hi = func.lineno, func.end_lineno
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "smtp_pass":
            if not (lo <= node.lineno <= hi):
                offenders.append(node.lineno)
    return offenders


def test_no_tracked_file_renders_a_password_type_input():
    offenders, _scanned = scan_tracked_python()
    assert not offenders, f"password-typed input rendered in: {offenders}"


def test_guard_scanned_a_nonzero_number_of_files():
    """A guard that greens because it resolved an empty or mis-resolved file list reports
    confidence it never earned — assert a real minimum count of examined files."""
    _offenders, scanned = scan_tracked_python()
    assert scanned >= 20, f"expected at least 20 tracked .py files scanned, found {scanned}"


def test_smtp_pass_is_scoped_to_send_qc_email():
    offenders = _smtp_pass_name_nodes_outside_send_qc_email()
    assert not offenders, f"smtp_pass referenced outside send_qc_email at line(s): {offenders}"
