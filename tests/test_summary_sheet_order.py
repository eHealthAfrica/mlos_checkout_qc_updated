"""Standing proof of canonical rule order at every place an officer can read an ordered list
(VERDICT-06, closes F14).

VERDICT-06's symptom is a report row order; its cause is rule identity, closed by ENGINE-09 in
Phase 1 (the registry, ``qc.sort_by_registry``, ``qc.canonical_order()``). This file's job is not
to build new ordering machinery — 03-RESEARCH.md confirmed every one of the five QC-layer call
sites in ``app.py`` already pipes its checks through ``qc.sort_by_registry`` before storing them,
and every downstream reader (the combined ``QC Summary`` sheet, the emailed check-by-check list,
the per-rule Excel exports) reads that already-sorted list. The job is to prove the guarantee
holds at every one of those four ordered outputs today, and to keep holding it once a future
phase registers new rules — which is why the expected order below is read from
``qc.canonical_order()`` at test time, never pinned as a literal identifier list. A literal list
is a second source of truth for order, and would go stale the first time a phase registers a rule
(exactly the class of divergence INTEG-03/F7 already closed once for column names).

Four ordered outputs are asserted for two scenarios (a full five-layer run, and a run with an
empty Takeoffpoint frame so a not-run layer's ordering is also exercised):

1. ``QcSummary.all_checks`` — the summary object's own combined, sorted list.
2. ``qc.report.summary_rows(summary)`` — the combined summary-sheet row builder.
3. The downloaded workbook's ``QC Summary`` sheet, read back via a round trip through openpyxl.
4. The emailed check-by-check list, parsed out of the plain-text body.

Plus a same-process stability/empty-input unit pair, and a cross-process byte-identical proof
(the three-hash-seed subprocess idiom from ``tests/test_deterministic_order.py``) that repeats
outputs 2 and 4 across three process restarts — the only proof that can detect a hash-order
regression at all, since a same-process test's hash seed is already fixed before the first call
runs (that file's own docstring explains why).
"""

import ast
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import openpyxl
import pandas as pd

import qc
import qc.report
from fixtures import build_mlos_fixture, build_takeoff_fixture, load_boundary_fixtures

REPO_ROOT = Path(__file__).resolve().parent.parent
QC_DIR = REPO_ROOT / "qc"
HASH_SEEDS = ("0", "1", "42")

PLACEHOLDER_RULE_MARK = "—"


# ─── Shared summary builders ────────────────────────────────────────────────────────────────

def _run_layers(mlos_df, takeoff_df, ref_df, bbox_df) -> dict:
    """Mirror app.py's five call sites exactly: run each QC layer, then pipe its checks
    through qc.sort_by_registry before handing them to build_summary -- the same shape every
    real call site follows (app.py:584, 594, 604, 618, 628)."""
    schema_checks, schema_detail = qc.schema.run_schema_qc(mlos_df, takeoff_df)
    schema_checks = qc.sort_by_registry(schema_checks)

    mlos_checks, mlos_detail = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
    mlos_checks = qc.sort_by_registry(mlos_checks)

    settlement_checks, settlement_detail = qc.settlement.run_settlement_qc(mlos_df)
    settlement_checks = qc.sort_by_registry(settlement_checks)

    if takeoff_df.empty:
        tp_checks, tp_detail = [], pd.DataFrame()
    else:
        tp_checks, tp_detail = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df)
        tp_checks = qc.sort_by_registry(tp_checks)

    boundary_checks, boundary_detail = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df)
    boundary_checks = qc.sort_by_registry(boundary_checks)

    return {
        "Schema": (schema_checks, schema_detail),
        "MLoS": (mlos_checks, mlos_detail),
        "Settlement": (settlement_checks, settlement_detail),
        "Takeoffpoint": (tp_checks, tp_detail),
        "Boundary": (boundary_checks, boundary_detail),
    }


def _build_summary(takeoff_empty: bool) -> "tuple[qc.report.QcSummary, pd.DataFrame, pd.DataFrame]":
    """Build one QcSummary from the shared fixtures, piping every layer's checks through the
    registry re-sort exactly as app.py's call sites do. Returns the summary plus the two raw
    frames build_workbook needs."""
    mlos_df = build_mlos_fixture()
    takeoff_df = pd.DataFrame() if takeoff_empty else build_takeoff_fixture()
    ref_df, bbox_df = load_boundary_fixtures()
    layer_results = _run_layers(mlos_df, takeoff_df, ref_df, bbox_df)
    summary = qc.report.build_summary(
        "order_fixture.xlsx", layer_results,
        mlos_row_count=len(mlos_df), takeoff_row_count=len(takeoff_df),
    )
    return summary, mlos_df, takeoff_df


# ─── The four ordered-output readers ────────────────────────────────────────────────────────

def _summary_object_ids(summary: "qc.report.QcSummary") -> "list[str]":
    return [c["Rule#"] for c in summary.all_checks]


def _summary_rows_ids(summary: "qc.report.QcSummary") -> "list[str]":
    return [r["Rule#"] for r in qc.report.summary_rows(summary) if r["Rule#"] != PLACEHOLDER_RULE_MARK]


def _workbook_ids(summary: "qc.report.QcSummary", mlos_df: pd.DataFrame, takeoff_df: pd.DataFrame) -> "list[str]":
    wb_bytes = qc.report.build_workbook(summary, mlos_df, takeoff_df)
    wb = openpyxl.load_workbook(BytesIO(wb_bytes))
    ws = wb["QC Summary"]
    header = [c.value for c in ws[2]]
    rule_col = header.index("Rule#")
    ids = []
    for row in ws.iter_rows(min_row=3):
        val = row[rule_col].value
        if val not in (None, PLACEHOLDER_RULE_MARK):
            ids.append(val)
    return ids


def _email_ids(summary: "qc.report.QcSummary") -> "list[str]":
    _subject, body = qc.report.build_email_subject_and_body(summary)
    marker = "Check-by-Check Summary"
    section = body[body.index(marker):]
    ids = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("[") and "] Rule " in line:
            after = line.split("] Rule ", 1)[1]
            ids.append(after.split(":", 1)[0].strip())
    return ids


READERS = {
    "summary object (all_checks)": lambda summary, mlos_df, takeoff_df: _summary_object_ids(summary),
    "summary_rows()": lambda summary, mlos_df, takeoff_df: _summary_rows_ids(summary),
    "workbook QC Summary sheet": _workbook_ids,
    "email check-by-check list": lambda summary, mlos_df, takeoff_df: _email_ids(summary),
}


def _expected_order(ids: "list[str]") -> "list[str]":
    """The registry's canonical order, filtered to the identifiers that actually ran -- never a
    literal list. ``ids`` supplies the set of identifiers that ran for this particular summary;
    canonical_order() supplies the order."""
    present = set(ids)
    return [rule_id for rule_id in qc.canonical_order() if rule_id in present]


def _assert_boundary_positions_increasing(ids: "list[str]", site: str) -> None:
    """The requirement's own Boundary-specific property: every registered Boundary identifier
    present in ``ids`` appears in strictly increasing registry order, and the first Boundary
    position is greater than the last non-Boundary position -- Boundary is last among the five
    layer blocks."""
    boundary_ids_in_order = [rid for rid in ids if qc.get_rule(rid).layer == "Boundary"]
    boundary_canonical = [rid for rid in qc.canonical_order() if rid in set(boundary_ids_in_order)]
    assert boundary_ids_in_order == boundary_canonical, (
        f"[{site}] Boundary identifiers are not in strictly increasing registry order: "
        f"got {boundary_ids_in_order!r}, expected {boundary_canonical!r}"
    )

    boundary_positions = [i for i, rid in enumerate(ids) if qc.get_rule(rid).layer == "Boundary"]
    non_boundary_positions = [i for i, rid in enumerate(ids) if qc.get_rule(rid).layer != "Boundary"]
    if boundary_positions and non_boundary_positions:
        assert boundary_positions[0] > non_boundary_positions[-1], (
            f"[{site}] a Boundary identifier appears before a non-Boundary identifier: "
            f"first Boundary position {boundary_positions[0]}, "
            f"last non-Boundary position {non_boundary_positions[-1]}"
        )


# ─── The four-outputs-times-two-scenarios matrix ────────────────────────────────────────────

def test_order_matches_registry_at_every_ordered_output_full_run():
    """A full five-layer run: every one of the four ordered outputs equals
    canonical_order() filtered to the identifiers that ran, and Boundary's own ordering
    property holds at each."""
    summary, mlos_df, takeoff_df = _build_summary(takeoff_empty=False)
    for site, reader in READERS.items():
        ids = reader(summary, mlos_df, takeoff_df)
        expected = _expected_order(ids)
        assert ids == expected, f"[{site}] order diverges from canonical_order(): {ids!r} != {expected!r}"
        _assert_boundary_positions_increasing(ids, site)


def test_order_matches_registry_at_every_ordered_output_with_an_unrun_layer():
    """The same four-outputs proof, but with Takeoffpoint empty -- exercising the not-run-layer
    branch at every site (the summary sheet's placeholder row, the email's gap line) without
    disturbing the order of the checks that did run."""
    summary, mlos_df, takeoff_df = _build_summary(takeoff_empty=True)
    assert not summary.layers["Takeoffpoint"].ran
    for site, reader in READERS.items():
        ids = reader(summary, mlos_df, takeoff_df)
        expected = _expected_order(ids)
        assert ids == expected, f"[{site}] order diverges from canonical_order(): {ids!r} != {expected!r}"
        assert not any(rid.startswith("TP") for rid in ids), (
            f"[{site}] a Takeoffpoint identifier was emitted despite the layer not running: {ids!r}"
        )
        _assert_boundary_positions_increasing(ids, site)


def test_unrun_layer_yields_exactly_one_placeholder_row_no_check_lines():
    """The empty case at the summary-sheet and email sites specifically: a layer that ran zero
    checks produces its ordered section with no check lines and no exception -- never a missing
    section, never a crash."""
    summary, _mlos_df, _takeoff_df = _build_summary(takeoff_empty=True)

    rows = qc.report.summary_rows(summary)
    tp_rows = [r for r in rows if r["Layer"] == "Takeoffpoint"]
    assert len(tp_rows) == 1, f"expected exactly one placeholder row for Takeoffpoint, got {tp_rows!r}"
    assert tp_rows[0]["Rule#"] == PLACEHOLDER_RULE_MARK

    _subject, body = qc.report.build_email_subject_and_body(summary)
    assert "Takeoffpoint" in body
    assert "not run" in body


# ─── Stability and empty-input unit cases ───────────────────────────────────────────────────

def test_empty_checks_list_sorts_to_an_empty_list():
    assert qc.sort_by_registry([]) == []


def test_stable_sort_preserves_relative_order_for_shared_identifiers():
    """Two check dicts carrying the same identifier survive the re-sort in their original
    relative order -- ``sorted`` is stable, and ordering here compares integer positions taken
    from canonical_order(), never identifier strings numerically, so no collation or
    numeric-parsing behaviour can ever affect this."""
    checks = [
        {"Rule#": "1", "Status": "PASS", "_seq": "first"},
        {"Rule#": "2", "Status": "PASS", "_seq": "only"},
        {"Rule#": "1", "Status": "PASS", "_seq": "second"},
    ]
    resorted = qc.sort_by_registry(checks)
    ones = [c["_seq"] for c in resorted if c["Rule#"] == "1"]
    assert ones == ["first", "second"]


# ─── Cross-process determinism (reuses tests/test_deterministic_order.py's idiom) ───────────

_SUBPROCESS_SNIPPET = """
import sys
sys.path.insert(0, "tests")
import json
import pandas as pd
import fixtures as f
import qc
import qc.report

mlos_df = f.build_mlos_fixture()
takeoff_df = pd.DataFrame()
ref_df, bbox_df = f.load_boundary_fixtures()

schema_checks, schema_detail = qc.schema.run_schema_qc(mlos_df, takeoff_df)
schema_checks = qc.sort_by_registry(schema_checks)
mlos_checks, mlos_detail = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
mlos_checks = qc.sort_by_registry(mlos_checks)
settlement_checks, settlement_detail = qc.settlement.run_settlement_qc(mlos_df)
settlement_checks = qc.sort_by_registry(settlement_checks)
tp_checks, tp_detail = [], pd.DataFrame()
boundary_checks, boundary_detail = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df)
boundary_checks = qc.sort_by_registry(boundary_checks)

summary = qc.report.build_summary(
    "order_fixture.xlsx",
    {
        "Schema": (schema_checks, schema_detail),
        "MLoS": (mlos_checks, mlos_detail),
        "Settlement": (settlement_checks, settlement_detail),
        "Takeoffpoint": (tp_checks, tp_detail),
        "Boundary": (boundary_checks, boundary_detail),
    },
    mlos_row_count=len(mlos_df), takeoff_row_count=len(takeoff_df),
)

summary_ids = [r["Rule#"] for r in qc.report.summary_rows(summary) if r["Rule#"] != "\\u2014"]

_subject, body = qc.report.build_email_subject_and_body(summary)
section = body[body.index("Check-by-Check Summary"):]
email_ids = []
for line in section.splitlines():
    line = line.strip()
    if line.startswith("[") and "] Rule " in line:
        after = line.split("] Rule ", 1)[1]
        email_ids.append(after.split(":", 1)[0].strip())

print(json.dumps({"summary_ids": summary_ids, "email_ids": email_ids}, sort_keys=True))
"""


def _run_snippet(seed: str) -> bytes:
    """Fork a real subprocess with PYTHONHASHSEED explicitly set to seed, and return its raw
    stdout bytes, undecoded -- a same-process test's hash seed is already fixed for the whole
    session before the first call runs, so it can never detect this defect."""
    env = {**os.environ, "PYTHONHASHSEED": seed}
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SNIPPET],
        env=env, cwd=str(REPO_ROOT), capture_output=True,
    )
    assert result.returncode == 0, (
        f"subprocess with PYTHONHASHSEED={seed!r} failed (exit {result.returncode})\n"
        f"stderr: {result.stderr.decode('utf-8', errors='replace')}"
    )
    return result.stdout


def test_summary_sheet_and_email_order_is_stable_across_hash_seeds():
    """Three subprocesses, each launched with a different explicit PYTHONHASHSEED, build the
    same summary and print the summary-sheet and email identifier sequences. The three raw
    stdout payloads are byte-identical, and the decoded sequence matches canonical_order()
    filtered to the identifiers that ran -- collected in-process via qc.canonical_order()."""
    outputs = [_run_snippet(seed) for seed in HASH_SEEDS]
    assert outputs[0] == outputs[1] == outputs[2], (
        f"summary/email order differs across hash seeds {HASH_SEEDS!r}"
    )

    payload = json.loads(outputs[0].decode("utf-8"))
    expected = _expected_order(payload["summary_ids"])
    assert payload["summary_ids"] == expected, (
        f"subprocess summary_ids diverge from canonical_order(): "
        f"{payload['summary_ids']!r} != {expected!r}"
    )
    assert payload["email_ids"] == expected, (
        f"subprocess email_ids diverge from canonical_order(): "
        f"{payload['email_ids']!r} != {expected!r}"
    )


# ─── Structural half: every layer sorted at its own call site, no layer sorts internally ───

def test_call_sites_pass_exactly_the_five_per_layer_checks_names():
    """AST-parse app.py (it cannot be imported outside a Streamlit runtime) and collect the
    argument name of every ``qc.sort_by_registry(...)`` call. The set must be exactly the five
    per-layer checks names -- one call site per layer, no layer sorted twice, no layer skipped."""
    tree = ast.parse((REPO_ROOT / "app.py").read_text())
    names = set()
    call_count = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "sort_by_registry" and node.args
                and isinstance(node.args[0], ast.Name)):
            call_count += 1
            names.add(node.args[0].id)
    want = {"schema_checks", "mlos_checks", "settlement_checks", "tp_checks", "boundary_checks"}
    assert names == want, f"sort_by_registry call-site argument names: {names!r} != {want!r}"
    assert call_count == 5, f"expected exactly 5 sort_by_registry call sites in app.py, found {call_count}"


def test_no_qc_layer_module_sorts_internally():
    """No module under qc/ other than the package facade (__init__.py) and the report
    aggregation module (report.py, which is not a QC layer -- it is the site every layer's
    already-sorted output is combined at) references sort_by_registry. A QC layer re-sorting
    its own output is exactly what 03-CONTEXT.md's Claude's Discretion note forbids: Phase 1
    deliberately left raw emission order alone inside qc/boundary.py and relies on the call
    site instead."""
    offenders = [
        str(p) for p in sorted(QC_DIR.glob("*.py"))
        if p.name != "__init__.py" and "sort_by_registry" in p.read_text()
    ]
    assert offenders == [] or all("report.py" in offender for offender in offenders), (
        f"sort_by_registry referenced inside a QC layer module: {offenders!r}"
    )
