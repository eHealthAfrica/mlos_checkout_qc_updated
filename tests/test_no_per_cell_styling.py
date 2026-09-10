"""Tests proving the raw and detail sheets carry no per-cell styling after a save/reload
round trip (ENGINE-08/D-09), while the cover and combined QC Summary sheet keep theirs.

``Cell.has_style`` returns ``False`` until a style attribute has actually been assigned to that
cell, and survives a full ``save()``/``load_workbook()`` round trip (03-RESEARCH.md's Code
Examples section, empirically verified against openpyxl 3.1.5) -- so this file asserts the
plain-body-row property the way it is actually consumed downstream: on the bytes
``build_workbook`` returns, reloaded from a fresh ``BytesIO``.
"""

import io

import openpyxl
import pandas as pd

import qc.report as report

DETAIL_SHEETS = (
    "Schema Issue Detail", "MLoS Issue Detail", "Settlement Issue Detail",
    "Takeoffpoint Issue Detail", "Boundary Issue Detail",
)
RAW_SHEETS = ("Raw MLoS Data", "Raw Takeoffpoint Data")


def _failing(rule_ids, total=10):
    return [
        {"Status": "❌ FAIL", "Rule#": r, "QC Check": f"Check {r}", "Description": "d",
         "Failing Rows": 2, "Total Rows": total, "Fail %": "20.0%"}
        for r in rule_ids
    ]


def _summary_for_styling():
    """Every layer has one failing check with a two-row detail frame, so the first and last
    body row of every detail sheet are distinguishable rows, not the same row twice."""
    schema_detail = pd.DataFrame({
        "Rule#": ["S1", "S1"], "Rule": ["MLoS Schema Alignment"] * 2,
        "Table": ["MLoS", "MLoS"], "Missing Column": ["urban", "rural"],
        "Impact": ["QC rule(s) skipped", "QC rule(s) skipped"],
    })
    mlos_detail = pd.DataFrame({
        "Rule#": ["2", "2"], "Rule": ["Takeoffpoint Name Match"] * 2,
        "settlement_name": ["Bravo", "Charlie"],
    })
    settlement_detail = pd.DataFrame({
        "Rule#": ["SQ1", "SQ1"], "Rule": ["Duplicate Settlement Name in Ward"] * 2,
        "settlement_name": ["Alpha", "Alpha"],
    })
    tp_detail = pd.DataFrame({
        "Rule#": ["TP2", "TP2"], "Rule": ["Name matches MLoS takeoffpoint"] * 2,
        "name": ["Orphan-TP", "Orphan-TP2"],
    })
    boundary_detail = pd.DataFrame({
        "Rule#": ["B1", "B1"], "Rule": ["Ward Code — Boundary Reference"] * 2,
        "ward_code": ["00000", "00001"],
    })
    layers = {
        "Schema": (_failing(["S1"]), schema_detail),
        "MLoS": (_failing(["2"]), mlos_detail),
        "Settlement": (_failing(["SQ1"]), settlement_detail),
        "Takeoffpoint": (_failing(["TP2"]), tp_detail),
        "Boundary": (_failing(["B1"]), boundary_detail),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def _mlos_raw():
    return pd.DataFrame({"settlement_name": ["Alpha", "Bravo", "Charlie"],
                          "ward_code": ["81110", "00000", "00001"]})


def _takeoff_df():
    return pd.DataFrame({"name": ["TP-A", "Orphan-TP"], "code": ["TPC-A", "ORPHAN"],
                          "wardcode": ["81110", "99999"]})


def _load_workbook():
    summary = _summary_for_styling()
    out = report.build_workbook(summary, _mlos_raw(), _takeoff_df())
    return summary, openpyxl.load_workbook(io.BytesIO(out))


def test_raw_and_detail_sheets_header_styled_body_plain_both_directions():
    """Both directions asserted (has_style True on the header, False on first AND last body
    row) so a workbook with no styling anywhere also fails this test -- not just a workbook
    that styled everything."""
    _, wb = _load_workbook()
    for name in DETAIL_SHEETS + RAW_SHEETS:
        ws = wb[name]
        header_row = 2 if name in DETAIL_SHEETS else 1
        first_body_row = header_row + 1
        last_body_row = ws.max_row
        assert last_body_row > first_body_row, (
            f"{name}: expected at least two body rows to distinguish first from last"
        )
        assert ws.cell(row=header_row, column=1).has_style is True, (
            f"{name}: header row should keep its styling"
        )
        assert ws.cell(row=first_body_row, column=1).has_style is False, (
            f"{name}: first body cell must carry no per-cell style"
        )
        assert ws.cell(row=last_body_row, column=1).has_style is False, (
            f"{name}: last body cell must carry no per-cell style"
        )


def test_cover_and_summary_sheets_keep_their_styling():
    _, wb = _load_workbook()
    cover = wb["QC Report Cover"]
    summary_ws = wb["QC Summary"]
    assert cover.cell(row=3, column=1).has_style is True
    assert summary_ws.cell(row=3, column=1).has_style is True


def test_row_counts_unchanged_by_the_styling_removal():
    summary, wb = _load_workbook()
    for name in DETAIL_SHEETS:
        layer = name.replace(" Issue Detail", "")
        ws = wb[name]
        assert ws.max_row - 2 == summary.layers[layer].findings
    assert wb["Raw MLoS Data"].max_row - 1 == 3
    assert wb["Raw Takeoffpoint Data"].max_row - 1 == 2


def test_column_widths_still_set_on_raw_and_detail_sheets():
    _, wb = _load_workbook()
    assert wb["Raw MLoS Data"].column_dimensions["A"].width is not None
    assert wb["MLoS Issue Detail"].column_dimensions["A"].width is not None
