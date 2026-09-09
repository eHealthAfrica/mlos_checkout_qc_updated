"""Standing guard for the qc/ -> UI layer import boundary (ENGINE-05).

Two independent proofs: a static AST scan of every module under qc/ (this file), and a runtime
proof that qc imports successfully in an interpreter where importing the UI framework raises
(the subprocess test below) — the framework is a declared runtime dependency and is installed in
this environment, so only a subprocess-level import interception can exercise that path.
"""

import ast
import subprocess
import sys
from pathlib import Path

QC_DIR = Path(__file__).resolve().parent.parent / "qc"
UI_FRAMEWORK = "streamlit"


def _find_ui_framework_imports(tree: ast.AST, framework: str = UI_FRAMEWORK) -> list[str]:
    """Walk a parsed module and return every imported module name whose first dotted component
    exactly matches ``framework``. A submodule import (``streamlit.components.v1``) matches; a
    third-party package that merely starts with the same letters (``streamlitx``) does not,
    because the comparison is against the full first dotted component, not a prefix test."""
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == framework:
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == framework:
                offenders.append(node.module)
    return offenders


def _scan_qc_directory() -> "tuple[list[str], int]":
    """Parse every .py file under qc/ and return (sorted offending paths, files scanned)."""
    offending_paths = []
    scanned = 0
    for path in sorted(QC_DIR.rglob("*.py")):
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        if _find_ui_framework_imports(tree):
            offending_paths.append(str(path))
    return sorted(offending_paths), scanned


def test_no_module_under_qc_imports_the_ui_framework():
    offenders, _scanned = _scan_qc_directory()
    assert not offenders, f"{UI_FRAMEWORK} imported in: {offenders}"


def test_guard_scanned_a_nonzero_number_of_files():
    """A guard that greens because it resolved an empty or mis-resolved directory reports
    confidence it never earned — assert a real minimum count of examined files."""
    _offenders, scanned = _scan_qc_directory()
    assert scanned >= 5, f"expected at least 5 files scanned under {QC_DIR}, found {scanned}"


def test_guard_matches_the_first_dotted_component_exactly():
    """Applied to synthetic in-memory source, the helper flags a submodule import of the UI
    framework and does not flag an import of a differently-named third-party package that
    happens to share a prefix."""
    flagged_source = "import streamlit.components.v1 as stc\n"
    not_flagged_source = "import streamlitx\nfrom streamlit_extras import metric_cards\n"

    flagged_tree = ast.parse(flagged_source, filename="<synthetic-flagged>")
    not_flagged_tree = ast.parse(not_flagged_source, filename="<synthetic-not-flagged>")

    assert _find_ui_framework_imports(flagged_tree) == ["streamlit.components.v1"]
    assert _find_ui_framework_imports(not_flagged_tree) == []


def test_qc_imports_when_the_ui_framework_is_unavailable():
    """Runtime half of ENGINE-05: spawn a subprocess that installs a sys.meta_path finder
    raising ImportError for any module whose first dotted component is the UI framework, then
    import qc and print a success token. This holds even though the framework is installed in
    this environment as a declared runtime dependency."""
    script = (
        "import sys\n"
        "class _BlockUIFramework:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        f"        if name.split('.')[0] == {UI_FRAMEWORK!r}:\n"
        "            raise ImportError(f'{name} is blocked in this interpreter')\n"
        "        return None\n"
        "sys.meta_path.insert(0, _BlockUIFramework())\n"
        "import qc\n"
        "print('QC_IMPORT_OK')\n"
    )
    repo_root = str(Path(__file__).resolve().parent.parent)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, cwd=repo_root,
    )
    assert result.returncode == 0, (
        f"subprocess failed (exit {result.returncode})\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "QC_IMPORT_OK" in result.stdout, (
        f"expected success token in subprocess stdout, got: {result.stdout!r}"
    )
