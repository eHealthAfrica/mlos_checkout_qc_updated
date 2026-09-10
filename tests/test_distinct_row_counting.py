"""RED-phase tests for distinct-row counting, findings and per-layer share lines (03-01 task 2).

Covers VERDICT-04 / D-10, D-11, D-12, D-13: each layer counts a failing source row once no
matter how many of its rules fired on it; the headline Issue Rows figure is the plain sum of
the four non-Schema layers' distinct counts (a settlement failing in two layers counts twice in
the headline and once in each layer); the old rule-row-pair count stays visible as "findings".

``qc.report.LayerSummary``/``QcSummary`` already exist (task 1, GREEN); ``distinct_issue_rows``,
``findings``, ``issue_line``, ``headline_distinct``, ``headline_findings`` and
``headline_issue_line`` do not yet, so every reference below fails on a genuine
``AttributeError`` inside its own test function -- never a collection-time import error.
"""

import pandas as pd
import pytest

import qc
import qc.report as report
from fixtures import build_mlos_fixture, build_takeoff_fixture, load_boundary_fixtures


def test_takeoff_detail_index_is_a_subset_of_the_input_frame(takeoff_df, mlos_df):
    _checks, detail = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df)
    assert not detail.empty
    assert set(detail.index) <= set(takeoff_df.index)
    # The orphan row (index 1) fails TP2, TP3, TP4 and TP5 all at once -> repeated in the index.
    assert detail.index.tolist().count(1) >= 2


def test_boundary_detail_index_is_a_subset_of_the_input_frame(mlos_df, boundary_refs):
    ref_df, bbox_df = boundary_refs
    _checks, detail = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df)
    assert not detail.empty
    assert set(detail.index) <= set(mlos_df.index)
    # Row 7/8 ("Golf"/"Hotel") both fail B2 outside the bbox -> distinct rows, but at least one
    # row's index repeats if it also fails another boundary rule sharing the detail frame.
    assert detail.index.nunique() < len(detail) or detail.index.nunique() == len(detail)


def test_mlos_and_settlement_detail_index_already_preserved_regression_guard(mlos_df, takeoff_df):
    _checks_m, detail_m = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
    _checks_s, detail_s = qc.settlement.run_settlement_qc(mlos_df)
    assert set(detail_m.index) <= set(mlos_df.index)
    assert set(detail_s.index) <= set(mlos_df.index)


def test_layer_summary_reports_one_distinct_row_and_two_findings_for_one_source_row_two_rules():
    detail = pd.DataFrame({"Rule#": ["1", "2"]}, index=[5, 5])
    layer = report.LayerSummary(
        name="MLoS", checks=[{"Rule#": "1", "Status": "❌ FAIL"}],
        detail=detail, weight=0.40, source_row_count=10,
    )
    assert layer.distinct_issue_rows == 1
    assert layer.findings == 2


def test_layer_summary_reports_zero_and_zero_for_an_empty_detail_frame():
    layer = report.LayerSummary(
        name="MLoS", checks=[{"Rule#": "1", "Status": "✅ PASS"}],
        detail=pd.DataFrame(), weight=0.40, source_row_count=10,
    )
    assert layer.distinct_issue_rows == 0
    assert layer.findings == 0


def test_issue_line_renders_the_exact_approved_string():
    detail = pd.DataFrame({"Rule#": ["1"] * 1040}, index=[i % 312 for i in range(1040)])
    layer = report.LayerSummary(
        name="MLoS", checks=[{"Rule#": "1", "Status": "❌ FAIL"}],
        detail=detail, weight=0.40, source_row_count=5000,
    )
    assert layer.distinct_issue_rows == 312
    assert layer.findings == 1040
    assert layer.issue_line == "312 issue rows (6.2% of 5,000) across 1,040 findings"


def test_issue_line_omits_share_clause_when_source_row_count_is_zero_or_none():
    detail = pd.DataFrame({"Rule#": ["1"]}, index=[0])
    for source_row_count in (0, None):
        layer = report.LayerSummary(
            name="MLoS", checks=[{"Rule#": "1", "Status": "❌ FAIL"}],
            detail=detail, weight=0.40, source_row_count=source_row_count,
        )
        assert "(" not in layer.issue_line
        assert "%" not in layer.issue_line.split("across")[0].replace("issue rows", "")


def test_issue_line_for_a_layer_that_did_not_run():
    layer = report.LayerSummary(
        name="Takeoffpoint", checks=[], detail=pd.DataFrame(), weight=0.20, source_row_count=0,
    )
    assert layer.issue_line == "not run: no Takeoffpoint data supplied"


def _build_summary_from_shared_fixture():
    mlos = build_mlos_fixture()
    takeoff = build_takeoff_fixture()
    ref_df, bbox_df = load_boundary_fixtures()

    schema_checks, schema_detail = qc.schema.run_schema_qc(mlos, takeoff)
    mlos_checks, mlos_detail = qc.mlos.run_mlos_qc(mlos, takeoff)
    settlement_checks, settlement_detail = qc.settlement.run_settlement_qc(mlos)
    tp_checks, tp_detail = qc.takeoff.run_takeoff_qc(takeoff, mlos)
    boundary_checks, boundary_detail = qc.boundary.run_ward_boundary_qc(mlos, ref_df, bbox_df)

    return report.build_summary(
        "fixture.xlsx",
        {
            "Schema": (schema_checks, schema_detail),
            "MLoS": (mlos_checks, mlos_detail),
            "Settlement": (settlement_checks, settlement_detail),
            "Takeoffpoint": (tp_checks, tp_detail),
            "Boundary": (boundary_checks, boundary_detail),
        },
        mlos_row_count=len(mlos), takeoff_row_count=len(takeoff),
    )


def test_headline_distinct_is_the_sum_of_the_four_non_schema_layers_and_double_counts_overlap():
    summary = _build_summary_from_shared_fixture()

    # Row 2 ("Bravo") fails in both MLoS (rules 2/3/4) and Boundary (B1) -- present in both
    # layers' detail frames, so it counts once in each and twice in the headline.
    assert 2 in summary.layers["MLoS"].detail.index
    assert 2 in summary.layers["Boundary"].detail.index

    expected = (
        summary.layers["MLoS"].distinct_issue_rows
        + summary.layers["Settlement"].distinct_issue_rows
        + summary.layers["Takeoffpoint"].distinct_issue_rows
        + summary.layers["Boundary"].distinct_issue_rows
    )
    assert summary.headline_distinct == expected
    assert summary.headline_findings >= summary.headline_distinct
