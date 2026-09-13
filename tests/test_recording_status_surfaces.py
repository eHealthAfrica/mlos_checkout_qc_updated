"""Tests for the three quiet officer-facing states (D-09), the persistent unconfigured banner
(D-10), and the one pure wording function both read from, new for AUDIT-05 (05-03 Task 1).

Two independent proofs, mirroring 05-02's ``tests/test_no_fire_on_cached_rerun.py`` idiom:

- Direct calls into ``qc.submission_record.status_line`` prove the wording contract (every
  ``<behavior>`` bullet about the four states) without any Streamlit runtime.
- An AST parent-chain walk over ``app.py`` proves the two render sites exist exactly once, sit on
  the correct side of the tabs call, and never assign to ``summary`` or a checks/detail name --
  the render sites observe the run, they do not participate in it.

Landmark note: ``app.py`` contains **two** ``st.tabs(`` calls -- the main eight-tab call this
plan's banner/status-line ordering is about, and a second, pre-existing, unrelated nested call
(``rt1, rt2 = st.tabs([...])`` inside the MLoS/Takeoffpoint raw-data view) that predates this
phase. The plan's own worked verify snippet assumes exactly one ``st.tabs(`` call exists; this
file instead locates the *first* (lowest line number) ``st.tabs(`` call as the landmark -- the
main tabs call is always first in source order, and both the banner and the status line still
sit on the correct side of every ``st.tabs(`` call in the file (proven directly below), so the
weaker, order-based check captures the same guarantee without assuming a count the codebase does
not have.
"""

import ast
from pathlib import Path

import qc.submission_record as r

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
SUBMISSION_LOG_PATH = Path(__file__).resolve().parent.parent / "submission_log.py"

# The names a render site must never assign to -- the shared summary object and the ten
# checks/detail pairs the five QC layers populate. An assignment to any of these from either
# render site would mean the status surfaces are participating in the run, not just observing it.
_FORBIDDEN_ASSIGN_TARGETS = {
    "summary",
    "schema_checks", "schema_detail",
    "mlos_checks", "mlos_detail",
    "settlement_checks", "settlement_detail",
    "tp_checks", "tp_detail",
    "boundary_checks", "boundary_detail",
}


# ─── status_line: the pure wording contract (D-09) ────────────────────────────────

def test_status_values_is_a_four_tuple_of_the_named_constants():
    """A STATUS_VALUES that dropped or renamed a member would silently desynchronise from
    submission_log.py's _set_status vocabulary -- pin the exact tuple."""
    assert r.STATUS_VALUES == (
        r.STATUS_PENDING, r.STATUS_RECORDED, r.STATUS_FAILED, r.STATUS_UNCONFIGURED,
    )
    assert len(r.STATUS_VALUES) == 4


def test_pending_status_is_quiet_and_non_empty():
    severity, text = r.status_line(r.STATUS_PENDING, "20260912T101530Z_abc")
    assert severity == "quiet"
    assert isinstance(text, str) and text.strip()
    assert "saved" in text.lower()


def test_recorded_status_is_quiet_and_names_the_id():
    """A recorded sentence that dropped the id would leave the officer unable to trace their
    report back to a specific log entry (D-11's whole point)."""
    rid = "20260912T101530Z_abc"
    severity, text = r.status_line(r.STATUS_RECORDED, rid)
    assert severity == "quiet"
    assert rid in text


def test_failed_status_is_warn_and_states_verdict_unaffected():
    """D-09 requires this exact phrase, not a paraphrase -- an officer reading 'could not save'
    alone might reasonably worry the verdict itself is compromised."""
    severity, text = r.status_line(r.STATUS_FAILED, "some-id")
    assert severity == "warn"
    assert "your verdict is unaffected" in text


def test_unconfigured_status_is_warn_and_says_nothing_was_recorded():
    severity, text = r.status_line(r.STATUS_UNCONFIGURED, "some-id")
    assert severity == "warn"
    assert "nothing was recorded" in text


def test_unrecognised_status_degrades_to_pending_rather_than_raising():
    """An officer must never meet a traceback because a future change introduced a fifth status
    string upstream that this function was never taught about."""
    rid = "some-id"
    assert r.status_line("something else entirely", rid) == r.status_line(r.STATUS_PENDING, rid)


def test_recorded_status_with_no_id_contains_no_none_substring():
    """A falsy record_id must be omitted from the sentence entirely, never interpolated as the
    literal string 'None' -- that would read as a bug on the officer's own page."""
    _severity, text = r.status_line(r.STATUS_RECORDED, None)
    assert "None" not in text


def test_the_four_sentences_are_all_distinct():
    rid = "some-id"
    texts = {
        r.status_line(r.STATUS_PENDING, rid)[1],
        r.status_line(r.STATUS_RECORDED, rid)[1],
        r.status_line(r.STATUS_FAILED, rid)[1],
        r.status_line(r.STATUS_UNCONFIGURED, rid)[1],
    }
    assert len(texts) == 4


# ─── submission_log.py's _set_status vocabulary stays inside STATUS_VALUES ────────

def test_every_set_status_string_constant_is_a_member_of_status_values():
    """A future edit to submission_log.py that introduced a fifth status string (or a typo'd
    existing one) would silently desynchronise the writer from the wording function's
    vocabulary -- this walk is the standing proof that can never happen unnoticed."""
    tree = ast.parse(SUBMISSION_LOG_PATH.read_text(), filename=str(SUBMISSION_LOG_PATH))
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func).startswith("_set_status"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    values.add(arg.value)
    assert values, "expected at least one string constant passed to _set_status(...)"
    assert values <= set(r.STATUS_VALUES), values


# ─── app.py render sites: AST proofs ───────────────────────────────────────────────

def _parse_app():
    return ast.parse(APP_PATH.read_text(), filename=str(APP_PATH))


def _calls_starting_with(tree, prefix):
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node).startswith(prefix)
    ]


def _build_parent_map(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_if(node, parents):
    """Walk the parent chain from node up to the nearest ast.If, or None if none exists."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.If):
            return current
        current = parents.get(current)
    return None


def test_app_py_has_exactly_one_unconfigured_reason_call_and_one_get_status_call():
    tree = _parse_app()
    u = _calls_starting_with(tree, "submission_log.unconfigured_reason(")
    g = _calls_starting_with(tree, "submission_log.get_status(")
    assert len(u) == 1, u
    assert len(g) == 1, g


def test_unconfigured_reason_sits_above_the_tabs_call_and_get_status_sits_below_it():
    """The banner must be visible above every tab (D-10); the status line must sit with the
    verdict, below the tabs call, inside the Generate Report tab (D-09). See module docstring
    for why the *first* st.tabs( call, not a bare count of 1, is the landmark used here."""
    tree = _parse_app()
    u = _calls_starting_with(tree, "submission_log.unconfigured_reason(")
    g = _calls_starting_with(tree, "submission_log.get_status(")
    tb = _calls_starting_with(tree, "st.tabs(")
    assert tb, "expected at least one st.tabs( call in app.py"
    first_tabs_lineno = min(node.lineno for node in tb)
    assert u[0].lineno < first_tabs_lineno, (u[0].lineno, first_tabs_lineno)
    assert g[0].lineno > first_tabs_lineno, (g[0].lineno, first_tabs_lineno)


def test_neither_render_site_assigns_to_summary_or_a_checks_or_detail_name():
    """A render site that assigned to summary or a checks/detail name would be participating in
    the run rather than merely observing it -- exactly the coupling D-06/D-11's 'the record
    observes the run, it does not participate in it' principle forbids."""
    tree = _parse_app()
    parents = _build_parent_map(tree)

    u_calls = _calls_starting_with(tree, "submission_log.unconfigured_reason(")
    g_calls = _calls_starting_with(tree, "submission_log.get_status(")
    assert len(u_calls) == 1 and len(g_calls) == 1

    # The banner's assignment statement (`_recording_unconfigured_reason = ...`) and the If block
    # that follows it are the "banner render site". The get_status call's nearest enclosing If is
    # the "status line render site".
    banner_assign = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.value is u_calls[0]:
            banner_assign = node
            break
    assert banner_assign is not None, "could not locate the banner's own assignment statement"

    banner_if = None
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and ast.unparse(node.test) == "_recording_unconfigured_reason is not None":
            banner_if = node
            break
    assert banner_if is not None, "could not locate the banner's If block"

    status_if = _enclosing_if(g_calls[0], parents)
    assert status_if is not None, "could not locate the status line's enclosing If block"

    forbidden_hits = []
    for subtree in (banner_assign, banner_if, status_if):
        for node in ast.walk(subtree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in _FORBIDDEN_ASSIGN_TARGETS:
                        forbidden_hits.append(target.id)
    assert not forbidden_hits, forbidden_hits

    # Neither render site may call fire_upload -- the record observes the run, it does not
    # participate in it (05-CONTEXT.md D-06).
    fire_calls = []
    for subtree in (banner_assign, banner_if, status_if):
        for node in ast.walk(subtree):
            if isinstance(node, ast.Call) and "fire_upload" in ast.unparse(node.func):
                fire_calls.append(ast.unparse(node))
    assert not fire_calls, fire_calls


def test_app_py_is_still_crlf_terminated():
    """app.py is CRLF-terminated by design (CLAUDE.md); edit tooling that normalises it to LF
    turns a small diff into a whole-file rewrite."""
    raw = APP_PATH.read_bytes()
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")  # no bare LF survives outside CRLF pairs
