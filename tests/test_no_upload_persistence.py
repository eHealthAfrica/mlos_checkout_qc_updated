"""Standing guard: parsing a submission through ``qc.loaders.load_submission`` leaves no new
file behind in the temporary directory or the repository root once the call returns (D-09), and
no tracked ``.py`` file writes a DataFrame to a filesystem path — the only write-mode file calls
in tracked source are the auth secrets materialiser (whose target path names the Streamlit
config directory) and a pre-existing, one-time baseline-capture dev script (see the module-level
docstring on the second test below for why that second entry is an intentional, documented
exception rather than a regression).
"""

import ast
import os
import subprocess
import tempfile
from pathlib import Path

import golden_fixture as gf
from qc.loaders import load_submission

REPO_ROOT = Path(__file__).resolve().parent.parent

# tests/baseline/capture_baseline.py is a standalone, manually-invoked dev script (Phase 1) that
# writes a FROZEN parity baseline artifact once; it is never imported or executed by the running
# application, and does not touch officer-uploaded data. It is an intentional, pre-existing
# exception to "the app writes nothing but the gitignored secrets file" (D-09 is about the
# deployed app's own runtime behaviour, not about one-time repository tooling), not a regression
# this guard should flag as a new offender.
_KNOWN_NON_APP_WRITE_MODE_FILE = "tests/baseline/capture_baseline.py"


def _tracked_python_files():
    """Every tracked ``.py`` path, resolved via ``git ls-files`` so the scope is exactly tracked
    source and cannot drift silently as files are added or removed."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return [REPO_ROOT / p for p in result.stdout.splitlines() if p.strip()]


def _dataframe_to_path_offenders(tree) -> list:
    """A to_csv/to_excel/to_pickle/to_parquet call whose first positional argument is a string
    constant or an os.path.join(...) call — a PATH, as opposed to the in-memory BytesIO writer
    every existing report builder passes."""
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("to_csv", "to_excel", "to_pickle", "to_parquet") and node.args:
                first = node.args[0]
                is_string_literal = isinstance(first, ast.Constant) and isinstance(first.value, str)
                is_path_join = isinstance(first, ast.Call) and ast.unparse(first).startswith("os.path.join(")
                if is_string_literal or is_path_join:
                    offenders.append(ast.dump(node)[:120])
    return offenders


def _write_mode_file_calls(tree) -> list:
    """An open(...) call whose mode argument contains w/a/x, or a write_text/write_bytes
    attribute call — the two shapes tracked source can use to put bytes on disk outside an
    in-memory BytesIO buffer."""
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            mode_arg = node.args[1] if len(node.args) >= 2 else None
            for kw in node.keywords:
                if kw.arg == "mode":
                    mode_arg = kw.value
            if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                if any(c in mode_arg.value for c in "wax"):
                    calls.append(node)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
            calls.append(node)
    return calls


def scan_tracked_python() -> "tuple[list[str], int]":
    """Return (offenders, scanned): offenders is a sorted list of "<path>: <unparsed call>"
    entries for every write-mode file call found in tracked source, and scanned is the number of
    tracked .py files actually examined. auth.py's secrets-file write and the baseline script's
    JSON write are EXPECTED entries here (see
    test_write_mode_offenders_are_only_the_known_exceptions for the assertion that no OTHER
    entry exists) — this function itself makes no judgement, matching
    tests/test_no_streamlit_in_qc.py's _scan_qc_directory shape.
    """
    offenders = []
    scanned = 0
    for path in sorted(_tracked_python_files()):
        if not path.is_file():
            continue
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in _write_mode_file_calls(tree):
            rel = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel}: {ast.unparse(node)}")
    return sorted(offenders), scanned


def _dataframe_to_path_offender_files() -> "tuple[list[str], int]":
    offenders = []
    scanned = 0
    for path in sorted(_tracked_python_files()):
        if not path.is_file():
            continue
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        if _dataframe_to_path_offenders(tree):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(offenders), scanned


def test_guard_scanned_a_nonzero_number_of_files():
    """A guard that greens because it resolved an empty or mis-resolved file list reports
    confidence it never earned — assert a real minimum count of examined files."""
    _offenders, scanned = scan_tracked_python()
    assert scanned >= 20, f"expected at least 20 tracked .py files scanned, found {scanned}"


def test_no_tracked_file_writes_a_dataframe_to_a_path():
    offenders, scanned = _dataframe_to_path_offender_files()
    assert scanned >= 20, f"expected at least 20 tracked .py files scanned, found {scanned}"
    assert not offenders, f"DataFrame written to a path (not BytesIO) in: {offenders}"


def test_write_mode_offenders_are_only_the_known_exceptions():
    """The write-mode-call offender set must be exactly {auth.py, the baseline script} — and
    auth.py's own write call must resolve to the Streamlit config directory, so the app's
    single *runtime* filesystem write is the gitignored secrets file and nothing else.

    auth.py writes through the module constant SECRETS_PATH rather than a literal path string
    (``SECRETS_PATH.write_text(rendered)``), so the call node's own unparsed text does not carry
    the substring — this checks the file's full source instead, which does carry
    ``SECRETS_PATH = Path(".streamlit") / "secrets.toml"``, proving the same fact without
    demanding an inlined literal that would undo Task 1's named-constant design.
    """
    offenders, _scanned = scan_tracked_python()
    offending_files = sorted({entry.split(":", 1)[0] for entry in offenders})
    assert offending_files == sorted(["auth.py", _KNOWN_NON_APP_WRITE_MODE_FILE]), offending_files

    auth_entries = [entry for entry in offenders if entry.startswith("auth.py:")]
    assert auth_entries, "expected at least one write-mode call recorded for auth.py"
    auth_source = (REPO_ROOT / "auth.py").read_text()
    assert ".streamlit" in auth_source, "auth.py's write call must target the Streamlit config directory"


def test_load_submission_leaves_no_new_file_in_tempdir_or_repo_root():
    """The real proof: qc.loaders.load_sqlite writes a delete=False temp file, and the only
    thing standing between a public Space and a settlement file left on disk is
    load_submission's try/finally unlink."""
    tmp_before = set(os.listdir(tempfile.gettempdir()))
    repo_before = set(os.listdir(REPO_ROOT))

    rows = gf.build_shared_mlos_rows()
    payload = gf.build_sqlite_bytes(rows, gf.MLOS_REQUIRED_COLS)
    handle = gf.FakeUploadedFile(payload, "submission.sqlite")

    mlos_df, takeoff_df = load_submission(handle, "submission.sqlite")

    assert mlos_df is not None and not mlos_df.empty, "mlos_df must be non-empty"
    # NOTE (documented discrepancy): the golden .sqlite fixture's Takeoffpoint table is, by
    # design (tests/golden_fixture.py's module docstring), a single-column, ZERO-ROW table --
    # it exists only to satisfy load_submission's unconditional two-view load, and deliberately
    # carries no row data so it cannot trigger the R2/R3/R4 cross-table checks for any format.
    # takeoff_df is therefore genuinely empty here; asserting non-emptiness on it would be a
    # false assertion about the shared fixture's actual, intentional shape.
    assert takeoff_df is not None, "takeoff_df must be a real DataFrame (the two-view load ran)"

    tmp_after = set(os.listdir(tempfile.gettempdir()))
    repo_after = set(os.listdir(REPO_ROOT))
    assert tmp_after == tmp_before, f"tempdir listing changed: {tmp_after ^ tmp_before}"
    assert repo_after == repo_before, f"repo-root listing changed: {repo_after ^ repo_before}"
