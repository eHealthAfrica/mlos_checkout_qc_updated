"""Standing structural guard: a rerun that hits the cached branch is not a submission (D-06,
AUDIT-04's idempotency edge). Parses ``app.py`` with ``ast`` -- app.py cannot be imported outside
a Streamlit runtime, since its module body calls ``st.set_page_config``/``st.markdown`` at import
time (matching ``tests/test_one_snapshot_guard.py``'s own rationale for reading app.py
structurally rather than executing it).

The guard's own capability to fail is proven on a synthetic source (05-RESEARCH.md Pitfall 5's
exact shape: a fire call hoisted above the fresh-run/cached-run split), following the
self-test convention ``tests/test_no_streamlit_in_qc.py::test_guard_matches_the_first_dotted_component_exactly``
already established. Each test's docstring says what would silently pass without its assertion.
"""

import ast
from pathlib import Path

APP_PY = Path(__file__).resolve().parent.parent / "app.py"

# A synthetic source in which the fire call sits above the fresh-run/cached-run split entirely --
# not inside the `if _fresh_qc_run:` guard at all -- the exact defect Pitfall 5 describes: a fire
# call hoisted above the cache branch would record a second submission on every tab switch.
SYNTHETIC_HOISTED_SOURCE = """
submission_log.fire_upload(_record, _record_path, _record_id)

if st.session_state.get("qc_cache_key") == qc_cache_key:
    _fresh_qc_run = False
    _record_id = st.session_state.get("submission_record_id")
else:
    _fresh_qc_run = True
    if _fresh_qc_run:
        pass
"""


def _parse_app() -> ast.Module:
    return ast.parse(APP_PY.read_text(), filename=str(APP_PY))


def _module_scope_statements(tree: ast.Module) -> list:
    """Top-level module statements, mirroring tests/test_one_snapshot_guard.py's own
    `_module_scope_statements` convention."""
    return list(tree.body)


def _build_parent_map(tree: ast.AST) -> dict:
    """Map every node to its direct parent, so a call's enclosing `if` chain can be walked
    upward regardless of nesting depth -- this is what lets the same helper correctly classify
    both the real, correctly-guarded call site and a synthetic, hoisted-above-the-guard one."""
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_ifs(node: ast.AST, parents: dict):
    """Yield every `ast.If` ancestor of `node`, innermost first."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.If):
            yield current
        current = parents.get(current)


def _fire_upload_calls(tree: ast.Module) -> list:
    """Every `Call` node anywhere in `tree` whose unparsed form starts with
    `submission_log.fire_upload(`."""
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node).startswith("submission_log.fire_upload(")
    ]


def _is_guarded_by_fresh_flag(call: ast.Call, parents: dict) -> bool:
    """True when `call` has an enclosing `if` whose test is the bare name `_fresh_qc_run`."""
    return any(
        isinstance(if_node.test, ast.Name) and if_node.test.id == "_fresh_qc_run"
        for if_node in _enclosing_ifs(call, parents)
    )


def find_unguarded_fire_calls(tree: ast.Module) -> list:
    """Every `submission_log.fire_upload(` call NOT nested inside an `if _fresh_qc_run:` guard --
    empty for a correctly-wired app.py, non-empty for the synthetic hoisted-call source below."""
    parents = _build_parent_map(tree)
    return [call for call in _fire_upload_calls(tree) if not _is_guarded_by_fresh_flag(call, parents)]


def _find_cache_if(tree: ast.Module) -> ast.If:
    """The one `If` node whose test compares a session-state read against `qc_cache_key` -- the
    cache-hit/fresh-run split itself."""
    candidates = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and "qc_cache_key" in ast.unparse(node.test)
        and "session_state" in ast.unparse(node.test)
    ]
    assert len(candidates) == 1, f"expected exactly one cache If node, found {len(candidates)}"
    return candidates[0]


def _calls_in(stmts: list) -> list:
    """Every call's unparsed source text found anywhere inside the given statement list."""
    calls = []
    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                calls.append(ast.unparse(node))
    return calls


def _fresh_qc_run_assignments(tree: ast.Module) -> list:
    """Every assignment to the bare name `_fresh_qc_run` inside a module-scope statement
    (function/class bodies excluded, matching test_one_snapshot_guard.py's module-scope
    convention -- there are none here, but the exclusion keeps the search scope honest)."""
    results = []
    for stmt in _module_scope_statements(tree):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_fresh_qc_run"
            ):
                results.append(node)
    return results


def _node_in_stmts(node: ast.AST, stmts: list) -> bool:
    return any(n is node for stmt in stmts for n in ast.walk(stmt))


# ─── Real app.py: exactly one fire site, correctly guarded ───────────────────────────────────

def test_exactly_one_fire_upload_call_site():
    """Without this, a second fire_upload call site (accidentally added anywhere) could record a
    QC run twice, violating D-06 -- the whole point of a single, guarded fire site."""
    tree = _parse_app()
    assert len(_fire_upload_calls(tree)) == 1


def test_fire_call_is_guarded_by_fresh_qc_run_flag():
    """Without this, the one fire call could sit outside the `if _fresh_qc_run:` guard entirely
    (e.g. immediately after the shared `summary` build, which both branches reach) and still pass
    a test that only counted call sites."""
    tree = _parse_app()
    assert find_unguarded_fire_calls(tree) == []


# ─── The cached branch calls nothing in this phase's modules, but reads the id back ──────────

def test_cached_branch_calls_nothing_in_submission_log_or_submission_record():
    """Without this, a future edit could add a second, redundant fire or build call inside the
    cache-hit branch -- exactly the double-submission-on-tab-switch defect D-06 forbids -- and no
    other test would notice, since the AST-level fire-site count only checks the whole module."""
    tree = _parse_app()
    cache_if = _find_cache_if(tree)
    cached_calls = _calls_in(cache_if.body)
    submission_log_calls = [c for c in cached_calls if c.startswith("submission_log.")]
    submission_record_calls = [c for c in cached_calls if c.startswith("qc.submission_record.")]
    assert submission_log_calls == [], submission_log_calls
    assert submission_record_calls == [], submission_record_calls


def test_cached_branch_reads_back_the_record_id_from_session_state():
    """Without this, a cached branch that lost the record id would print 'not recorded' on a
    report cover for a run that was in fact recorded perfectly well the first time."""
    tree = _parse_app()
    cache_if = _find_cache_if(tree)
    cached_src = "\n".join(ast.unparse(stmt) for stmt in cache_if.body)
    assert "submission_record_id" in cached_src
    assert "session_state" in cached_src


# ─── _fresh_qc_run: exactly two assignments, True only in the fresh-run branch ───────────────

def test_fresh_qc_run_assigned_exactly_twice_false_then_true():
    """Without pinning the exact count and the exact boolean pair, a third assignment slipped in
    elsewhere (e.g. a default at module top) could silently change which branch 'wins' on ties,
    or hide a second True assignment reachable from a code path this guard never checks."""
    tree = _parse_app()
    assignments = _fresh_qc_run_assignments(tree)
    assert len(assignments) == 2, f"expected exactly 2 assignments, found {len(assignments)}"
    values = sorted(ast.literal_eval(node.value) for node in assignments)
    assert values == [False, True]


def test_true_assignment_lies_inside_the_cache_ifs_orelse():
    """Without this, `_fresh_qc_run = True` could live in some other branch entirely (a nested
    function, an unrelated if) and still satisfy a weaker 'exists somewhere' check, while never
    actually being the fresh-run branch's own flag."""
    tree = _parse_app()
    cache_if = _find_cache_if(tree)
    true_assignment = next(
        node for node in _fresh_qc_run_assignments(tree)
        if ast.literal_eval(node.value) is True
    )
    assert _node_in_stmts(true_assignment, cache_if.orelse), (
        "the _fresh_qc_run = True assignment must lie inside the cache If node's orelse "
        "(the fresh-run branch), not merely somewhere in the module"
    )


# ─── Guard self-test: proven capable of failing ──────────────────────────────────────────────

def test_guard_detects_a_fire_call_hoisted_above_the_cache_split_as_an_offender():
    """The self-test that stops this guard from being one that would pass against any source at
    all: a fire call hoisted above the fresh-run/cached-run split (Pitfall 5's exact defect --
    it would fire on every tab switch, not just fresh runs) must be reported as unguarded."""
    tree = ast.parse(SYNTHETIC_HOISTED_SOURCE)
    offenders = find_unguarded_fire_calls(tree)
    assert len(offenders) == 1, (
        f"expected the synthetic hoisted-above-the-guard fire call to be reported as an "
        f"offender, found {len(offenders)}"
    )


def test_guard_does_not_flag_a_correctly_nested_synthetic_fire_call():
    """The accept-case companion to the previous test: a fire call genuinely nested inside
    `if _fresh_qc_run:` must NOT be flagged, so this guard is proven to distinguish the two
    shapes rather than simply flagging every fire call it sees."""
    correctly_nested_source = """
if st.session_state.get("qc_cache_key") == qc_cache_key:
    _fresh_qc_run = False
    _record_id = st.session_state.get("submission_record_id")
else:
    _fresh_qc_run = True

if _fresh_qc_run:
    submission_log.fire_upload(_record, _record_path, _record_id)
"""
    tree = ast.parse(correctly_nested_source)
    assert find_unguarded_fire_calls(tree) == []


# ─── Non-vacuity floor ────────────────────────────────────────────────────────────────────────

def test_guard_parsed_a_substantial_number_of_top_level_statements():
    """A guard that greened because app.py failed to parse into anything -- or resolved the
    wrong path -- would otherwise report confidence it never earned."""
    tree = _parse_app()
    module_stmts = _module_scope_statements(tree)
    assert len(module_stmts) >= 40, (
        f"expected at least 40 top-level statements in app.py, found {len(module_stmts)}"
    )
