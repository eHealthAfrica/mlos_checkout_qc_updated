"""Tests for qc.report.build_workbook, the relocated report-workbook builder (03-02).

Task 1 (this file's first section) proves the cover reads the one shared ``QcSummary`` object
instead of recomputing its own two-layer failing count (VERDICT-01/VERDICT-02, F1) -- the exact
case that downloads a Boundary-only failure as CLEAN today. Task 2 extends this file with the
combined-summary-sheet and per-layer-detail-sheet assertions (D-06/D-07); task 3's per-cell-
styling proof lives in its own file, tests/test_no_per_cell_styling.py.

Synthetic ``QcSummary`` objects are built the same way tests/test_layer_pass_rate.py does --
small checks lists carrying the real Status/Rule#/QC Check/... shape -- so this file needs no
boundary reference CSVs, no Streamlit runtime, and no real QC engine run.
"""

import io
from pathlib import Path

import openpyxl
import pandas as pd

import qc
import qc.report as report

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def _passing(rule_ids):
    return [
        {"Status": "✅ PASS", "Rule#": r, "QC Check": f"Check {r}", "Description": "d",
         "Failing Rows": 0, "Total Rows": 10, "Fail %": "0.0%"}
        for r in rule_ids
    ]


def _failing(rule_ids, total=10):
    return [
        {"Status": "❌ FAIL", "Rule#": r, "QC Check": f"Check {r}", "Description": "d",
         "Failing Rows": 1, "Total Rows": total, "Fail %": "10.0%"}
        for r in rule_ids
    ]


def _summary_only_boundary_failing():
    """Every layer passes except Boundary, which has exactly one failing check -- the case
    that files a false CLEAN today because the old cover only summed MLoS+Takeoffpoint."""
    layers = {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (
            _failing(["B1"]),
            pd.DataFrame({"Rule#": ["B1"], "Rule": ["Ward Code — Boundary Reference"],
                          "ward_code": ["00000"]}),
        ),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def _summary_all_passing_empty_takeoffpoint():
    """All checks that ran passed; Takeoffpoint ran zero checks (D-05's "did not run")."""
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": ([], pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=0)


def _mlos_raw():
    return pd.DataFrame({"settlement_name": ["Alpha", "Bravo"], "ward_code": ["81110", "00000"]})


def _takeoff_df(empty=False):
    if empty:
        return pd.DataFrame()
    return pd.DataFrame({"name": ["TP-A"], "code": ["TPC-A"], "wardcode": ["81110"]})


def _cover_sheet(summary, mlos_raw=None, takeoff_df=None, column_renames=None):
    out = report.build_workbook(
        summary,
        mlos_raw if mlos_raw is not None else _mlos_raw(),
        takeoff_df if takeoff_df is not None else _takeoff_df(),
        column_renames=column_renames,
    )
    wb = openpyxl.load_workbook(io.BytesIO(out))
    return wb, wb["QC Report Cover"]


def _cover_values(ws):
    return [cell.value for row in ws.iter_rows() for cell in row if cell.value is not None]


# ── Task 1: end-to-end bytes + five-layer cover verdict ─────────────────────────────────────

def test_build_workbook_returns_bytes_openpyxl_can_load():
    summary = _summary_all_passing_empty_takeoffpoint()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df(empty=True))
    assert isinstance(out, bytes)
    wb = openpyxl.load_workbook(io.BytesIO(out))
    assert "QC Report Cover" in wb.sheetnames


def test_cover_reads_failing_when_only_boundary_fails():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary)
    values = _cover_values(ws)
    assert any(isinstance(v, str) and v.startswith("FAILING (") for v in values), values


def test_cover_reads_clean_with_gap_clause_when_takeoffpoint_did_not_run():
    summary = _summary_all_passing_empty_takeoffpoint()
    _, ws = _cover_sheet(summary, takeoff_df=_takeoff_df(empty=True))
    values = _cover_values(ws)
    assert "CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)" in values


def test_cover_carries_score_display_ending_with_achievable():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary)
    values = _cover_values(ws)
    assert summary.score_display in values
    assert summary.score_display.endswith("achievable")


def test_cover_labels_are_exactly_the_five_metadata_rows_no_per_layer_counts():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary)
    meta_labels = {"File", "Generated At", "MLoS Rows", "Takeoffpoint Rows", "Weighted Score"}
    all_col_a = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    found_meta = [v for v in all_col_a if v in meta_labels]
    assert found_meta == ["File", "Generated At", "MLoS Rows", "Takeoffpoint Rows", "Weighted Score"]
    assert not any(isinstance(v, str) and "Checks" in v for v in all_col_a)


def test_verdict_row_is_below_the_metadata_block():
    summary = _summary_only_boundary_failing()
    _, ws = _cover_sheet(summary)
    meta_labels = {"File", "Generated At", "MLoS Rows", "Takeoffpoint Rows", "Weighted Score"}
    meta_rows = [r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value in meta_labels]
    verdict_rows = [
        r for r in range(1, ws.max_row + 1)
        if isinstance(ws.cell(row=r, column=1).value, str)
        and (ws.cell(row=r, column=1).value.startswith("FAILING (")
             or ws.cell(row=r, column=1).value.startswith("CLEAN"))
    ]
    assert meta_rows and verdict_rows
    assert max(meta_rows) < min(verdict_rows)


# ── Task 2: one combined summary sheet plus a detail sheet per layer (D-06/D-07) ────────────

EXPECTED_SHEET_NAMES = (
    "QC Report Cover", "QC Summary", "Schema Issue Detail", "MLoS Issue Detail",
    "Settlement Issue Detail", "Takeoffpoint Issue Detail", "Boundary Issue Detail",
    "Raw MLoS Data", "Raw Takeoffpoint Data",
)


def _summary_for_sheet_shape():
    """Every layer runs; MLoS and Boundary each carry one failing check with its own
    distinctive detail column, so the two detail sheets can be proven un-merged."""
    layers = {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (
            _passing(["1"]) + _failing(["2"]),
            pd.DataFrame({"Rule#": ["2"], "Rule": ["Takeoffpoint Name Match"],
                          "settlement_name": ["Bravo"]}),
        ),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (
            _passing(["B0"]) + _failing(["B1"]),
            pd.DataFrame({"Rule#": ["B1"], "Rule": ["Ward Code — Boundary Reference"],
                          "ward_code": ["00000"]}),
        ),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def test_sheet_names_constant_matches_d06_order():
    assert report.SHEET_NAMES == EXPECTED_SHEET_NAMES


def test_sheet_names_are_exactly_the_d06_order_with_no_renames():
    summary = _summary_for_sheet_shape()
    wb, _ = _cover_sheet(summary)
    assert wb.sheetnames == list(EXPECTED_SHEET_NAMES)


def test_sheet_names_append_columns_renamed_when_a_rename_occurred():
    summary = _summary_for_sheet_shape()
    wb, _ = _cover_sheet(summary, column_renames={"Old Header": "new_header"})
    assert wb.sheetnames == list(EXPECTED_SHEET_NAMES) + ["Columns Renamed"]


def test_sheet_names_identical_for_an_all_passing_all_empty_submission():
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    summary = report.build_summary("f.xlsx", layers, mlos_row_count=5, takeoff_row_count=5)
    wb, _ = _cover_sheet(summary)
    assert wb.sheetnames == list(EXPECTED_SHEET_NAMES)


def test_summary_sheet_header_row_is_the_eight_columns():
    summary = _summary_for_sheet_shape()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    ws = wb["QC Summary"]
    header = [ws.cell(row=2, column=c).value for c in range(1, 9)]
    assert header == ["Layer", "Status", "Rule#", "QC Check", "Description",
                       "Failing Rows", "Total Rows", "Fail %"]


def _summary_sheet_rows(wb):
    ws = wb["QC Summary"]
    rows = []
    for r in range(3, ws.max_row + 1):
        rows.append({
            "Layer": ws.cell(row=r, column=1).value,
            "Status": ws.cell(row=r, column=2).value,
            "Rule#": ws.cell(row=r, column=3).value,
            "QC Check": ws.cell(row=r, column=4).value,
            "Failing Rows": ws.cell(row=r, column=6).value,
            "Total Rows": ws.cell(row=r, column=7).value,
            "Fail %": ws.cell(row=r, column=8).value,
        })
    return rows


def test_summary_sheet_rule_column_matches_canonical_order_of_ran_identifiers():
    summary = _summary_for_sheet_shape()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    rows = _summary_sheet_rows(wb)
    ran_ids = {"S1", "S2", "S3", "1", "2", "SQ1", "TP2", "B0", "B1"}
    actual_ids = [r["Rule#"] for r in rows if r["Rule#"] != "—"]
    expected_ids = [r for r in qc.canonical_order() if r in ran_ids]
    assert actual_ids == expected_ids


def test_summary_sheet_layer_column_first_appearance_order_matches_layer_order():
    summary = _summary_for_sheet_shape()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    ws = wb["QC Summary"]
    seen = []
    for r in range(3, ws.max_row + 1):
        layer = ws.cell(row=r, column=1).value
        if layer and layer not in seen:
            seen.append(layer)
    assert seen == list(report.LAYER_ORDER)


def test_a_layer_that_ran_one_check_yields_exactly_one_row_for_that_layer():
    summary = _summary_for_sheet_shape()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    rows = _summary_sheet_rows(wb)
    settlement_rows = [r for r in rows if r["Layer"] == "Settlement"]
    assert len(settlement_rows) == 1
    assert settlement_rows[0]["Rule#"] == "SQ1"


def test_empty_takeoffpoint_yields_one_placeholder_row_with_na_cells_between_settlement_and_boundary():
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": ([], pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    summary = report.build_summary("f.xlsx", layers, mlos_row_count=5, takeoff_row_count=0)
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df(empty=True))
    wb = openpyxl.load_workbook(io.BytesIO(out))
    rows = _summary_sheet_rows(wb)
    tp_rows = [r for r in rows if r["QC Check"] == "Takeoffpoint — not run: no Takeoffpoint data supplied"]
    assert len(tp_rows) == 1
    tp_row = tp_rows[0]
    assert tp_row["Failing Rows"] == "n/a"
    assert tp_row["Total Rows"] == "n/a"
    assert tp_row["Fail %"] == "n/a"
    idx = rows.index(tp_row)
    assert rows[idx - 1]["Layer"] == "Settlement"
    assert rows[idx + 1]["Layer"] == "Boundary"


def test_detail_sheets_keep_their_own_layers_columns_not_merged():
    summary = _summary_for_sheet_shape()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    mlos_header = [c.value for c in wb["MLoS Issue Detail"][2]]
    boundary_header = [c.value for c in wb["Boundary Issue Detail"][2]]
    assert "settlement_name" in mlos_header
    assert "ward_code" not in mlos_header
    assert "ward_code" in boundary_header
    assert "settlement_name" not in boundary_header


def test_detail_sheet_body_row_counts_match_findings_and_raw_sheet_matches_input_rows():
    summary = _summary_for_sheet_shape()
    mlos_raw_df = _mlos_raw()
    out = report.build_workbook(summary, mlos_raw_df, _takeoff_df())
    wb = openpyxl.load_workbook(io.BytesIO(out))
    mlos_ws = wb["MLoS Issue Detail"]
    assert mlos_ws.max_row - 2 == summary.layers["MLoS"].findings
    boundary_ws = wb["Boundary Issue Detail"]
    assert boundary_ws.max_row - 2 == summary.layers["Boundary"].findings
    raw_ws = wb["Raw MLoS Data"]
    assert raw_ws.max_row - 1 == len(mlos_raw_df)


def test_summary_rows_raises_naming_the_identifier_when_a_check_is_misfiled_under_the_wrong_layer():
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["B0"]), pd.DataFrame()),  # B0 is registered under Boundary, not MLoS
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    summary = report.build_summary("f.xlsx", layers, mlos_row_count=5, takeoff_row_count=5)
    try:
        report.summary_rows(summary)
        assert False, "expected ValueError for a misfiled rule id"
    except ValueError as e:
        assert "B0" in str(e)
        assert "MLoS" in str(e)
        assert "Boundary" in str(e)


def test_app_caption_names_the_new_sheets_and_drops_the_old_mlos_summary_name():
    src = APP_PATH.read_text(encoding="utf-8")
    assert "Boundary Issue Detail" in src
    assert "MLoS QC Summary" not in src
