"""RED-phase tests for the shared verdict sentence (03-01 task 3).

Covers VERDICT-02 / D-04, D-05, D-16: the verdict stays two-state (CLEAN / FAILING), and when a
layer did not run the same gap clause, in the same position, is appended after both states —
``CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)`` and
``FAILING (12 checks) — Takeoffpoint layer not checked (no Takeoffpoint data supplied)`` (D-04,
amended 2026-09-10). ``verdict_short`` drops the gap clause for the D-16 email subject template.

``QcSummary`` already exists (task 1, GREEN); ``verdict_text``, ``verdict_short`` and
``gap_clause`` do not yet, so every reference below fails on a genuine ``AttributeError``.
"""

import pandas as pd

import qc.report as report


def _passing(rule_ids):
    return [{"Rule#": r, "Status": "✅ PASS"} for r in rule_ids]


def _failing(rule_ids):
    return [{"Rule#": r, "Status": "❌ FAIL"} for r in rule_ids]


def _summary(mlos_checks, takeoff_ran=True):
    layers = {
        "Schema": report.LayerSummary("Schema", _passing(["S1"]), pd.DataFrame(), 0.10, None),
        "MLoS": report.LayerSummary("MLoS", mlos_checks, pd.DataFrame(), 0.40, 10),
        "Settlement": report.LayerSummary("Settlement", _passing(["SQ1"]), pd.DataFrame(), 0.20, 10),
        "Takeoffpoint": report.LayerSummary(
            "Takeoffpoint", _passing(["TP2"]) if takeoff_ran else [], pd.DataFrame(), 0.20,
            5 if takeoff_ran else 0,
        ),
        "Boundary": report.LayerSummary("Boundary", _passing(["B0"]), pd.DataFrame(), 0.10, 10),
    }
    return report.QcSummary(filename="f.xlsx", layers=layers)


def test_all_layers_ran_nothing_failing_is_clean():
    summary = _summary(_passing(["1"]))
    assert summary.verdict_text == "CLEAN"


TWELVE_REGISTERED_MLOS_IDS = [
    "1", "2", "2.missing", "3", "3.missing", "4", "4.missing", "5", "6", "7", "8", "9",
]


def test_all_layers_ran_twelve_failing_reads_plural_checks():
    summary = _summary(_failing(TWELVE_REGISTERED_MLOS_IDS))
    assert summary.verdict_text == "FAILING (12 checks)"


def test_one_failing_check_reads_singular_check():
    summary = _summary(_failing(["1"]))
    assert summary.verdict_text == "FAILING (1 check)"


def test_clean_with_takeoffpoint_not_checked_names_the_gap_in_the_same_sentence():
    summary = _summary(_passing(["1"]), takeoff_ran=False)
    assert summary.verdict_text == (
        "CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)"
    )


def test_failing_with_takeoffpoint_not_checked_appends_the_same_gap_clause():
    summary = _summary(_failing(TWELVE_REGISTERED_MLOS_IDS), takeoff_ran=False)
    assert summary.verdict_text == (
        "FAILING (12 checks) — Takeoffpoint layer not checked (no Takeoffpoint data supplied)"
    )


def test_verdict_short_drops_the_gap_clause_in_both_states():
    clean = _summary(_passing(["1"]), takeoff_ran=False)
    failing = _summary(_failing(TWELVE_REGISTERED_MLOS_IDS), takeoff_ran=False)
    assert clean.verdict_short == "CLEAN"
    assert failing.verdict_short == "FAILING (12 checks)"


def test_two_unrun_layers_join_their_clauses_with_semicolon():
    layers = {
        "Schema": report.LayerSummary("Schema", [], pd.DataFrame(), 0.10, None),
        "MLoS": report.LayerSummary("MLoS", _passing(["1"]), pd.DataFrame(), 0.40, 10),
        "Settlement": report.LayerSummary("Settlement", _passing(["SQ1"]), pd.DataFrame(), 0.20, 10),
        "Takeoffpoint": report.LayerSummary("Takeoffpoint", [], pd.DataFrame(), 0.20, 0),
        "Boundary": report.LayerSummary("Boundary", _passing(["B0"]), pd.DataFrame(), 0.10, 10),
    }
    summary = report.QcSummary(filename="f.xlsx", layers=layers)
    assert "; " in summary.gap_clause
    assert "Schema" in summary.gap_clause
    assert "Takeoffpoint" in summary.gap_clause


def test_verdict_text_is_always_one_of_exactly_two_prefixes():
    for summary in (
        _summary(_passing(["1"])),
        _summary(_failing(["1"])),
        _summary(_passing(["1"]), takeoff_ran=False),
    ):
        assert summary.verdict_text.startswith("CLEAN") or summary.verdict_text.startswith("FAILING")
