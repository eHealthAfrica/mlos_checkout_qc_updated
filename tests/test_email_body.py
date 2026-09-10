"""Tests for qc.report.build_email_subject_and_body, the pure email subject/body builder (03-03).

Task 1 (this file's first section) proves the seam: a pure function taking only the shared
``QcSummary``, reading no secrets, returning a ``(subject, body)`` tuple whose header block
carries the same verdict/score/headline strings every other on-screen and report site prints.
Task 2 extends this file with the per-layer blocks, the missing-columns block and the grouped
check-by-check list (D-14/D-15/VERDICT-03, closing F11 -- the Settlement layer's absence from
today's email body).

Synthetic ``QcSummary`` objects are built the same way tests/test_report_workbook_shape.py and
tests/test_layer_pass_rate.py do -- small checks lists carrying the real Status/Rule#/QC
Check/... shape, using real MLoS/Boundary/Settlement/Schema/Takeoffpoint registered identifiers
so ``sort_by_registry``/``get_rule`` resolve them -- so this file needs no boundary reference
CSVs, no Streamlit runtime, and no real QC engine run.
"""

import pandas as pd

import qc.report as report

# A distinctive marker embedded in a synthetic MLoS detail frame's settlement_name column --
# never used anywhere else in this file -- so task 2's "no detail-row value leaks" assertion has
# an unambiguous string to search for.
_SECRET_SETTLEMENT = "Zzq_Secret_Settlement_9137"


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


def _summary_twelve_failing():
    """Twelve failing checks, all in MLoS, using twelve real MLoS-registered identifiers (the
    same convention 03-01's test_verdict_sentence.py used) -- every other layer passes."""
    layers = {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (
            _failing(["1", "2", "2.missing", "3", "3.missing", "4", "4.missing",
                      "5", "6", "7", "8", "9"]),
            pd.DataFrame(),
        ),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def _summary_clean_with_gap():
    """Every check that ran passed; Takeoffpoint ran zero checks (D-05's "did not run") -- the
    CLEAN-with-gap-clause scenario D-16 says must NOT enter the subject."""
    layers = {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": ([], pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=0)


def _mlos_detail_with_settlement_name():
    return pd.DataFrame(
        {"settlement_name": [_SECRET_SETTLEMENT], "ward_code": ["81110"],
         "latitude": [13.05], "longitude": [6.50], "set_population": [1200]}
    )


def _summary_five_layers_settlement_failing():
    """All five layers ran; Settlement has a failing check with a detail frame carrying a
    settlement name -- the direct proof of VERDICT-03/F11 (Settlement must appear in the body)
    and of the no-detail-row-leak assertion."""
    layers = {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (_failing(["1"]), _mlos_detail_with_settlement_name()),
        "Settlement": (
            _failing(["SQ1"]),
            pd.DataFrame({"settlement_name": [_SECRET_SETTLEMENT], "ward_code": ["81110"]}),
        ),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def _summary_takeoffpoint_unrun():
    """Takeoffpoint ran zero checks -- its block must read exactly the not-run sentence and
    carry no checks-run number."""
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": ([], pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=0)


def _summary_schema_missing_columns():
    """Schema's detail frame is non-empty (missing columns) -- the missing-columns block must
    appear, naming each missing column."""
    layers = {
        "Schema": (
            _failing(["S1"]),
            pd.DataFrame({"Table": ["MLoS", "MLoS"],
                          "Missing Column": ["set_target", "editor"]}),
        ),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


def _summary_schema_no_missing_columns():
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (_passing(["1"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    return report.build_summary("kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)


# ─── Task 1: seam, subject, header block ──────────────────────────────────────────


def test_returns_a_two_tuple_of_str():
    result = report.build_email_subject_and_body(_summary_clean_with_gap())
    assert isinstance(result, tuple)
    assert len(result) == 2
    subject, body = result
    assert isinstance(subject, str)
    assert isinstance(body, str)


def test_subject_for_twelve_failing_checks():
    subject, _ = report.build_email_subject_and_body(_summary_twelve_failing())
    assert subject == "MLoS QC: FAILING (12 checks) — kano_checkout.xlsx"


def test_subject_for_clean_summary_with_unrun_layer_has_no_gap_clause():
    subject, _ = report.build_email_subject_and_body(_summary_clean_with_gap())
    assert subject == "MLoS QC: CLEAN — kano_checkout.xlsx"


def test_body_contains_verdict_text_verbatim_including_gap_clause():
    summary = _summary_clean_with_gap()
    _, body = report.build_email_subject_and_body(summary)
    assert summary.verdict_text in body
    assert "Takeoffpoint layer not checked (no Takeoffpoint data supplied)" in summary.verdict_text


def test_body_contains_score_display_verbatim():
    summary = _summary_twelve_failing()
    _, body = report.build_email_subject_and_body(summary)
    assert summary.score_display in body


def test_body_contains_headline_issue_line_verbatim():
    summary = _summary_twelve_failing()
    _, body = report.build_email_subject_and_body(summary)
    assert summary.headline_issue_line in body


def test_body_contains_filename_and_generated_at_timestamp():
    summary = _summary_twelve_failing()
    _, body = report.build_email_subject_and_body(summary)
    assert summary.filename in body
    assert "Generated:" in body
