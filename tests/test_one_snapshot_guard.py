"""Standing structural guard for the one-snapshot / content-identity model (D-14, D-15,
ENGINE-03, ENGINE-04). Parses app.py with ``ast`` -- app.py cannot be imported outside a
Streamlit runtime, since its module body calls st.set_page_config / st.markdown at import time
-- and fails the moment any consumer reads the wrong frame, a second auto-correction call
appears, the bare frame name returns at module scope, or a run_all() facade is introduced.

Reading of D-15's "mlos_raw appears at exactly one call site" (the report's as-submitted
sheet): read literally against the code, mlos_raw is an argument to two calls --
auto_correct_mlos, which is the sole producer of mlos_corrected, and build_workbook (03-02:
relocated from app.py's own build_excel_report into qc.report, called as
qc.report.build_workbook(...) -- this guard's _call_name helper resolves an attribute call to
its final attr name, "build_workbook"), which writes the as-submitted sheet. The producer is
not a *consumer* of the raw frame for display or for checking, which is the class D-15's
sentence is actually about. This guard therefore asserts the set of called-function names
receiving mlos_raw as an argument is exactly {"auto_correct_mlos", "build_workbook"} --
precise, checkable, and it asserts exactly what D-15 protects: that no QC layer, no on-screen
table and no download reads the uncorrected frame. Do not "fix" this guard toward the literal
sentence by removing auto_correct_mlos from the expected set -- that narrows the guard and
breaks it (see 02-06-PLAN.md's planner clarification).
"""

import ast
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"

RUNNER_NAMES = {
    "run_schema_qc",
    "run_mlos_qc",
    "run_settlement_qc",
    "run_takeoff_qc",
    "run_ward_boundary_qc",
}


def _call_name(call: ast.Call) -> str:
    """Return a call's function name whether the call target is a bare name or an attribute
    access (e.g. ``run_mlos_qc(...)`` vs ``qc.mlos.run_mlos_qc(...)``)."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return getattr(func, "id", "")


def _parse_app() -> ast.Module:
    return ast.parse(APP_PATH.read_text(), filename=str(APP_PATH))


def _collect_calls(tree: ast.Module) -> list:
    """Return every call anywhere in the tree as (name, [arg source strings]) pairs, with
    positional and keyword argument source text collected together."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            args = [ast.unparse(a) for a in node.args] + [
                ast.unparse(kw.value) for kw in node.keywords
            ]
            calls.append((_call_name(node), args))
    return calls


def _module_scope_statements(tree: ast.Module) -> list:
    """Return the statements that live directly at module scope -- outside any function or
    class definition."""
    return list(tree.body)


def _module_scope_calls(tree: ast.Module) -> list:
    """Return every call as (name, [arg source strings]) pairs, restricted to calls that live
    inside a module-scope statement -- outside any function or class definition. This is the
    scope that matters for the consumer-repointing assertions: a pure helper's own internal
    delegation to another pure helper (e.g. build_longitudinal_mlos calling make_longitudinal_df
    with its own parameter) is unrelated to which session-state frame the *script* passed in,
    and must not be conflated with the real call site in the main body."""
    calls = []
    for stmt in _module_scope_statements(tree):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                args = [ast.unparse(a) for a in node.args] + [
                    ast.unparse(kw.value) for kw in node.keywords
                ]
                calls.append((_call_name(node), args))
    return calls


def _module_scope_bare_name_occurrences(tree: ast.Module, name: str) -> list:
    """Return the line numbers where a bare identifier named `name` occurs -- read or bound --
    anywhere inside a module-scope statement, without descending into nested function or class
    bodies (those are out of this guard's scope per the plan's planner clarification)."""
    lines = []
    for stmt in _module_scope_statements(tree):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and node.id == name:
                lines.append(node.lineno)
    return lines


def test_bare_frame_name_absent_at_module_scope():
    """No module-scope statement may read or bind the old bare 'mlos_df' name (D-14/D-15).
    Function parameters and locals inside def bodies are out of scope for this rule."""
    tree = _parse_app()
    lines = _module_scope_bare_name_occurrences(tree, "mlos_df")
    assert not lines, (
        f"found {len(lines)} occurrence(s) of the bare 'mlos_df' name at module scope, on "
        f"line(s) {lines} -- repoint each to mlos_raw or mlos_corrected per D-14"
    )


def test_five_qc_call_sites_all_receive_the_corrected_frame():
    """Exactly five QC call sites exist, one per layer, and every one receives mlos_corrected.
    A call site that disappears fails here rather than silently reducing coverage."""
    tree = _parse_app()
    found = {}
    for name, args in _module_scope_calls(tree):
        if name in RUNNER_NAMES:
            found[name] = args
    assert set(found) == RUNNER_NAMES, (
        f"expected exactly the five QC layer call sites {sorted(RUNNER_NAMES)}, found "
        f"{sorted(found)}"
    )
    bad = {k: v for k, v in found.items() if "mlos_corrected" not in v}
    assert not bad, f"these QC calls do not receive mlos_corrected: {bad}"


def test_build_corrected_excel_receives_the_corrected_frame():
    tree = _parse_app()
    found = [args for name, args in _module_scope_calls(tree) if name == "build_corrected_excel"]
    assert found, "build_corrected_excel is never called"
    assert all("mlos_corrected" in args for args in found), (
        f"build_corrected_excel called without mlos_corrected: {found}"
    )


def test_both_longitudinal_helpers_receive_the_corrected_frame():
    """Checked at the real call site in the main body only. build_longitudinal_mlos's own
    internal delegation to make_longitudinal_df (using its own parameter name) is a separate,
    pure-helper-to-pure-helper call and is out of scope for this assertion."""
    tree = _parse_app()
    for helper in ("make_longitudinal_df", "build_longitudinal_mlos"):
        found = [args for name, args in _module_scope_calls(tree) if name == helper]
        assert found, f"{helper} is never called at module scope"
        assert all("mlos_corrected" in args for args in found), (
            f"{helper} called at module scope without mlos_corrected: {found}"
        )


def test_raw_frame_reaches_only_the_producer_and_the_report_builder():
    """The set of called-function names that receive mlos_raw as an argument is exactly the
    producer (auto_correct_mlos) and the report builder (build_workbook, relocated 03-02), and
    nothing else -- see this module's docstring for why the producer belongs in that set."""
    tree = _parse_app()
    consumers = {name for name, args in _module_scope_calls(tree) if "mlos_raw" in args}
    assert consumers == {"auto_correct_mlos", "build_workbook"}, (
        f"mlos_raw reaches {sorted(consumers)}, expected exactly "
        f"{{'auto_correct_mlos', 'build_workbook'}}"
    )


def test_auto_correct_called_exactly_once():
    tree = _parse_app()
    calls = [args for name, args in _module_scope_calls(tree) if name == "auto_correct_mlos"]
    assert len(calls) == 1, f"auto-correction called {len(calls)} time(s), expected exactly 1"


def test_corrected_frame_and_log_are_both_written_and_read_in_session_state():
    """The corrected frame and the correction log are each both written to and read from
    session state, so the cache-hit branch cannot have been left without them (F4)."""
    src = APP_PATH.read_text()
    for key in ("mlos_corrected", "autocorrect_log"):
        n = src.count(f'st.session_state["{key}"]')
        assert n >= 2, (
            f'st.session_state["{key}"] appears {n} time(s) in app.py, expected at least 2 '
            f"(a write in the cache-miss branch and a read in the cache-hit branch)"
        )


def test_no_run_all_facade_is_called():
    """D-15 declines a qc.run_all() facade; this is the cheap standing assertion that keeps
    that decision declined."""
    tree = _parse_app()
    calls = [name for name, _args in _collect_calls(tree) if name == "run_all"]
    assert not calls, f"a run_all() facade is called {len(calls)} time(s) in app.py"
    module_calls = [name for name, _args in _module_scope_calls(tree) if name == "run_all"]
    assert not module_calls, (
        f"a run_all() facade is called {len(module_calls)} time(s) at module scope in app.py"
    )


def test_guard_scanned_a_substantial_number_of_calls_and_module_scope_statements():
    """A guard that greens because it parsed nothing, or resolved the wrong path, reports
    confidence it never earned -- assert real minimum counts, following the precedent of
    tests/test_no_streamlit_in_qc.py's scanned-count test."""
    tree = _parse_app()
    calls = _collect_calls(tree)
    module_stmts = _module_scope_statements(tree)
    assert len(calls) >= 50, f"expected at least 50 calls parsed from app.py, found {len(calls)}"
    assert len(module_stmts) >= 20, (
        f"expected at least 20 module-scope statements in app.py, found {len(module_stmts)}"
    )
