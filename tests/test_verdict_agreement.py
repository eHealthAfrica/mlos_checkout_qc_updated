"""The four sites agree, and every layer the registry knows appears at every presentation site.

F1 was one wrong derivation among four independent ones: the banner, the report cover, the
Generate Report tab and the emailed summary each computed their own verdict, and the cover's
computation happened to be wrong (it summed only two of the five layers). The fix (plans 01-03
of this phase) was not "patch the cover" -- it was one shared computation (``qc.report.QcSummary``)
that every site reads instead of deriving its own answer. This file is what stops a fifth reader
from reintroducing that divergence.

Two of the four sites live in ``app.py``, which cannot be imported outside a Streamlit runtime
(the established convention in this codebase -- see ``tests/test_one_snapshot_guard.py``'s
docstring). Those two are asserted structurally, following the AST-scan idiom
``tests/test_no_streamlit_in_qc.py`` established: parse the file, collect offenders into a list,
assert the offender set is empty, and separately assert the scan examined a non-zero number of
nodes so a mis-resolved parse cannot green the test by accident. The workbook and email halves
are asserted on real bytes and real text -- the summary's own verdict/score/headline properties,
run through the real builders, must appear verbatim.

A second, independent test proves the assumption-delta companion invariant from 03-01-PLAN.md:
every layer name the registry knows appears at every presentation site, so a future sixth layer
cannot be silently absent from one of them the way Settlement was absent from the email (F11).
"""

import ast
from io import BytesIO
from pathlib import Path

import openpyxl
import pandas as pd

import qc
import qc.report
from fixtures import FIXTURE_WARD_CODE, MLOS_REQUIRED_COLS, load_boundary_fixtures

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PY_PATH = REPO_ROOT / "app.py"


# ─── The one fixture that exercises F1, D-01, D-04 and D-07 together ───────────────────────
#
# A summary whose only failing checks belong to the Boundary layer, and whose Takeoffpoint
# layer ran nothing: Schema, MLoS and Settlement all pass every check on both rows; row 0's
# ward_code is real (81110, bundled in the reference) so its Boundary checks all pass; row 1's
# ward_code ("00000") does not exist in the reference, so B1 -- and only B1 -- fails. This is
# exactly the shape the old two-layer cover sum (F1) reported as CLEAN.

_VALID_ROW = {
    "state_code": "ZA", "state_name": "Zamfara", "lga_code": "811", "lga_name": "Shinkafi",
    "ward_name": "Shinkafi South", "ward_code": FIXTURE_WARD_CODE,
    "takeoffpoint": "TP-A", "takeoffpoint_code": "TPC-A",
    "settlement_name": "OnlyBoundaryFails-Pass",
    "primarysettlement_name": "", "alternate_name": "",
    "latitude": "13.06", "longitude": "6.51",
    "security_compromised": "N", "accessibility_status": "Fully Accessible",
    "reasons_for_inaccessibility": "NA", "habitational_status": "Inhabited",
    "set_population": "100", "set_target": "50", "number_of_household": "40",
    "noncompliant_household": "0", "team_code": "T1", "day_of_activity": "1",
    "urban": "Y", "rural": "N", "highrisk": "N", "slums": "N", "densely_populated": "N",
    "hard2reach": "N", "border": "N", "nomadic": "N", "scattered": "N", "riverine": "N",
    "fulani": "N", "timestamp": "2024-01-01T00:00:00", "source": "IE",
    "last_updated": "2024-01-01T00:00:00", "editor": "jane.doe",
    "validation_status": "validated", "master_id": "M-P001", "mlos_id": "ML-P001",
    "eha_guid": "c1111111-1111-1111-1111-111111111111",
    "settlementarea_globalid": "sga-p001",
}


def _build_boundary_only_failure_summary() -> "tuple[qc.report.QcSummary, pd.DataFrame, pd.DataFrame]":
    row0 = dict(_VALID_ROW)
    row1 = dict(_VALID_ROW)
    row1.update({
        "settlement_name": "OnlyBoundaryFails-Fail",
        "ward_code": "00000",  # absent from the bundled reference -> B1 fails, nothing else
        "latitude": "1.0", "longitude": "1.0",
        "master_id": "M-P002", "mlos_id": "ML-P002",
        "eha_guid": "c2222222-2222-2222-2222-222222222222",
        "settlementarea_globalid": "sga-p002",
    })
    mlos_df = pd.DataFrame([row0, row1], columns=MLOS_REQUIRED_COLS)
    takeoff_df = pd.DataFrame()  # Takeoffpoint did not run at all
    ref_df, bbox_df = load_boundary_fixtures()

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
        "kano_checkout.xlsx",
        {
            "Schema": (schema_checks, schema_detail),
            "MLoS": (mlos_checks, mlos_detail),
            "Settlement": (settlement_checks, settlement_detail),
            "Takeoffpoint": (tp_checks, tp_detail),
            "Boundary": (boundary_checks, boundary_detail),
        },
        mlos_row_count=len(mlos_df), takeoff_row_count=len(takeoff_df),
    )
    return summary, mlos_df, takeoff_df


def _fixture_asserts_only_boundary_fails(summary: "qc.report.QcSummary") -> None:
    """Guard the fixture itself, so a future edit that breaks the "only Boundary fails" shape
    fails loudly here rather than silently weakening every assertion below."""
    assert summary.layers["Schema"].n_fail == 0
    assert summary.layers["MLoS"].n_fail == 0
    assert summary.layers["Settlement"].n_fail == 0
    assert not summary.layers["Takeoffpoint"].ran
    assert summary.layers["Boundary"].n_fail >= 1
    assert summary.n_fail == summary.layers["Boundary"].n_fail


# ─── Real-output half: workbook bytes and email text ────────────────────────────────────────

def _cover_verdict_cell_value(summary: "qc.report.QcSummary", mlos_df: pd.DataFrame, takeoff_df: pd.DataFrame) -> str:
    wb_bytes = qc.report.build_workbook(summary, mlos_df, takeoff_df)
    wb = openpyxl.load_workbook(BytesIO(wb_bytes))
    ws = wb["QC Report Cover"]
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith(("CLEAN", "FAILING")):
                return cell.value
    raise AssertionError("no verdict-shaped cell found on the QC Report Cover sheet")


def test_verdict_sentence_appears_verbatim_in_the_workbook_cover_and_the_email_body():
    summary, mlos_df, takeoff_df = _build_boundary_only_failure_summary()
    _fixture_asserts_only_boundary_fails(summary)

    cover_value = _cover_verdict_cell_value(summary, mlos_df, takeoff_df)
    _subject, body = qc.report.build_email_subject_and_body(summary)

    assert cover_value == summary.verdict_text
    assert summary.verdict_text in body
    assert cover_value.startswith("FAILING ("), (
        f"cover verdict for a Boundary-only failure should start with the failing prefix, got: "
        f"{cover_value!r}"
    )


def test_score_display_appears_verbatim_in_the_workbook_cover_and_the_email_body():
    summary, mlos_df, takeoff_df = _build_boundary_only_failure_summary()

    wb_bytes = qc.report.build_workbook(summary, mlos_df, takeoff_df)
    wb = openpyxl.load_workbook(BytesIO(wb_bytes))
    ws = wb["QC Report Cover"]
    cover_text = "\n".join(
        str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None
    )
    _subject, body = qc.report.build_email_subject_and_body(summary)

    assert summary.score_display in cover_text
    assert summary.score_display in body


def test_headline_issue_line_appears_verbatim_in_the_email_body():
    summary, _mlos_df, _takeoff_df = _build_boundary_only_failure_summary()
    _subject, body = qc.report.build_email_subject_and_body(summary)
    assert summary.headline_issue_line in body


# ─── Structural half over app.py ────────────────────────────────────────────────────────────

def _app_src() -> str:
    return APP_PY_PATH.read_text()


def _region(src: str, start_marker: str, end_marker: "str | None" = None, max_lines: int = 60) -> str:
    """Return the slice of ``src`` from ``start_marker`` to ``end_marker`` (or ``max_lines``
    lines, whichever comes first) -- bounded by named markers rather than line numbers, since
    plan line anchors go stale the moment an earlier plan touches the file."""
    start = src.index(start_marker)
    if end_marker is not None:
        end = src.index(end_marker, start)
        return src[start:end]
    lines = src[start:].splitlines()
    return "\n".join(lines[:max_lines])


def test_verdict_text_is_read_at_the_banner_and_the_generate_report_tab():
    src = _app_src()
    banner_region = _region(src, "VERDICT BANNER", "TABS ")
    report_tab_region = _region(
        src, "Verdict — the same shared summary.verdict_text every other site reads"
    )
    assert "summary.verdict_text" in banner_region, "banner does not read summary.verdict_text"
    assert "summary.verdict_text" in report_tab_region, (
        "Generate Report tab verdict does not read summary.verdict_text"
    )


def test_score_display_is_read_where_the_score_is_rendered():
    src = _app_src()
    score_region = _region(src, "Weighted Score Breakdown")
    assert "summary.score_display" in score_region


def test_no_offender_recomputes_a_failing_count_or_a_detail_frame_length():
    """The offender-set assertion: no call in app.py sums over a check-status membership test
    (the exact shape F1/F6/F8 all took -- a local re-derivation of a count the summary object
    already exposes), and no name is assigned the length of a detail frame. Both offender lists
    are collected in full (never short-circuited) so a failure names every offending line."""
    src = _app_src()
    tree = ast.parse(src)

    sum_offenders = []
    len_detail_offenders = []
    call_nodes_examined = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_nodes_examined += 1
            if isinstance(node.func, ast.Name) and node.func.id == "sum":
                dumped = ast.dump(node)
                if "FAIL" in dumped and "Status" in dumped:
                    sum_offenders.append(node.lineno)
            if isinstance(node.func, ast.Name) and node.func.id == "len" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id.endswith("_detail"):
                    len_detail_offenders.append(node.lineno)

    assert call_nodes_examined > 0, "AST scan examined zero Call nodes -- the parse is broken"
    assert sum_offenders == [], (
        f"app.py sums over a check-status membership test at line(s) {sum_offenders} -- "
        f"every failing count must come from the shared summary object"
    )
    assert len_detail_offenders == [], (
        f"app.py assigns len(<name>_detail) at line(s) {len_detail_offenders} -- "
        f"every row count must come from the shared summary object"
    )


# ─── Assumption-delta companion invariant: every layer appears at every site ────────────────

def test_registry_layer_names_equal_report_layer_order():
    registry_layers = {qc.get_rule(rule_id).layer for rule_id in qc.canonical_order()}
    assert registry_layers == set(qc.report.LAYER_ORDER)


def test_every_registry_layer_appears_in_the_summary_sheet_and_the_email_body():
    summary, _mlos_df, _takeoff_df = _build_boundary_only_failure_summary()
    registry_layers = {qc.get_rule(rule_id).layer for rule_id in qc.canonical_order()}

    rows = qc.report.summary_rows(summary)
    layer_column_values = {row["Layer"] for row in rows}
    assert registry_layers <= layer_column_values, (
        f"layer(s) missing from the combined summary sheet's Layer column: "
        f"{registry_layers - layer_column_values}"
    )

    _subject, body = qc.report.build_email_subject_and_body(summary)
    missing_from_email = [name for name in registry_layers if name not in body]
    assert missing_from_email == [], (
        f"layer(s) missing from the email body: {missing_from_email}"
    )


def test_score_table_metadata_card_and_breakdown_iterate_layer_order_not_named_dict_keys():
    """The construction-site half of the companion invariant: the Tab 2 score table and the
    Tab 8 metadata card / combined breakdown must be built by iterating
    qc.report.LAYER_ORDER, never by hard-coding a dict literal keyed on 2+ layer names --
    which is exactly the "named three layers instead of iterating all five" shape that left
    Schema and Boundary off the old metadata card, and Settlement off the old email (F11)."""
    src = _app_src()
    tree = ast.parse(src)
    layer_names = set(qc.report.LAYER_ORDER)

    with_blocks_scanned = 0
    dict_offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Name) and ctx.id in ("tab2", "tab8"):
                    with_blocks_scanned += 1
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Dict):
                            keys = [
                                k.value for k in sub.keys
                                if isinstance(k, ast.Constant) and isinstance(k.value, str)
                            ]
                            overlap = layer_names & set(keys)
                            if len(overlap) >= 2:
                                dict_offenders.append((sub.lineno, sorted(overlap)))

    assert with_blocks_scanned == 2, (
        f"expected to scan the tab2 and tab8 With blocks, found {with_blocks_scanned}"
    )
    assert dict_offenders == [], (
        f"a dict literal keyed on 2+ layer names was found inside tab2/tab8: {dict_offenders} -- "
        f"iterate qc.report.LAYER_ORDER instead of naming layers as dict keys"
    )

    assert "qc.report.LAYER_ORDER" in src
