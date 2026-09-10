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

import openpyxl
import pandas as pd

import qc.report as report


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
