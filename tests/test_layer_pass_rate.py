"""RED-phase tests for qc/report.py's weighted-score computation (03-01 task 1).

Written before qc/report.py carries any behaviour: at RED time the module exists only as an
empty stub (import succeeds) so a missing symbol fails inside the specific test function as a
genuine ``AttributeError``, never as a collection-time import error (#3770's INVALID_RED
guard). ``qc.get_rule`` is exercised the same way against the already-importable ``qc`` package.

Covers VERDICT-05 / D-01, D-02, D-03, D-05: a layer that ran zero checks earns no score credit
and reports ``pass_rate is None`` (never the old F6 full-credit ``1.0``), the achievable maximum
excludes layers that did not run, and the colour band is driven by the capped score out of 100.
"""

import pandas as pd

import qc
import qc.report as report


def _layer(name="MLoS", checks=None, weight=0.40, source_row_count=10):
    return report.LayerSummary(
        name=name,
        checks=list(checks) if checks is not None else [],
        detail=pd.DataFrame(),
        weight=weight,
        source_row_count=source_row_count,
    )


def _passing(rule_ids):
    return [{"Rule#": r, "Status": "✅ PASS"} for r in rule_ids]


def test_layer_with_empty_checks_reports_not_run_with_no_score_credit():
    layer = _layer(checks=[])
    assert layer.ran is False
    assert layer.pass_rate is None
    assert layer.weighted_contribution == 0.0
    assert isinstance(layer.weighted_contribution, float)


def test_layer_with_one_of_four_failing_reports_partial_pass_rate_and_contribution():
    checks = _passing(["1", "2", "3"]) + [{"Rule#": "4", "Status": "❌ FAIL"}]
    layer = _layer(checks=checks, weight=0.40)
    assert layer.ran is True
    assert layer.pass_rate == 0.75
    assert layer.weighted_contribution == 0.75 * 0.40 * 100


def test_layer_with_one_passing_check_contributes_its_full_weight():
    layer = _layer(checks=_passing(["1"]), weight=0.20)
    assert layer.pass_rate == 1.0
    assert layer.weighted_contribution == 0.20 * 100


def _all_five_layers_passing():
    return {
        "Schema": (_passing(["S1", "S2", "S3"]), pd.DataFrame()),
        "MLoS": (_passing(["1", "2"]), pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": (_passing(["TP2"]), pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }


def test_five_layers_all_passing_renders_full_achievable_score():
    summary = report.build_summary(
        "kano_checkout.xlsx", _all_five_layers_passing(),
        mlos_row_count=10, takeoff_row_count=5,
    )
    assert summary.score_display == "100.0% of 100.0% achievable"


def test_takeoffpoint_empty_renders_achievable_max_80_and_amber_band_at_72():
    # Schema/Settlement/Boundary pass in full (10 + 20 + 10 = 40); MLoS has 4 of 5 checks
    # passing (pass_rate 0.8 -> 0.8 * 40 = 32); total weighted score 72 of an 80 achievable
    # maximum (Takeoffpoint did not run) -- the exact "72.0% of 80.0% achievable" string
    # the user approved (03-CONTEXT.md <specifics>).
    mlos_checks = _passing(["1", "2", "3", "4"]) + [{"Rule#": "5", "Status": "❌ FAIL"}]
    layers = {
        "Schema": (_passing(["S1"]), pd.DataFrame()),
        "MLoS": (mlos_checks, pd.DataFrame()),
        "Settlement": (_passing(["SQ1"]), pd.DataFrame()),
        "Takeoffpoint": ([], pd.DataFrame()),
        "Boundary": (_passing(["B0"]), pd.DataFrame()),
    }
    summary = report.build_summary(
        "kano_checkout.xlsx", layers, mlos_row_count=10, takeoff_row_count=0,
    )
    assert summary.achievable_max == 80.0
    assert summary.score_display == "72.0% of 80.0% achievable"
    assert summary.score_band == "amber"


def _single_layer_summary(pass_rate_numerator, pass_rate_denominator):
    n_fail = pass_rate_denominator - pass_rate_numerator
    checks = _passing([str(i) for i in range(pass_rate_numerator)]) + [
        {"Rule#": f"f{i}", "Status": "❌ FAIL"} for i in range(n_fail)
    ]
    layer = report.LayerSummary(
        name="MLoS", checks=checks, detail=pd.DataFrame(), weight=1.0, source_row_count=10,
    )
    return report.QcSummary(filename="f.xlsx", layers={"MLoS": layer})


def test_score_band_is_green_at_exactly_80():
    summary = _single_layer_summary(800, 1000)
    assert summary.weighted_score == 80.0
    assert summary.score_band == "green"


def test_score_band_is_amber_at_exactly_60():
    summary = _single_layer_summary(600, 1000)
    assert summary.weighted_score == 60.0
    assert summary.score_band == "amber"


def test_score_band_is_red_just_below_60():
    summary = _single_layer_summary(599, 1000)
    assert summary.weighted_score == 59.9
    assert summary.score_band == "red"


def test_build_summary_raises_naming_unknown_layer_key():
    layers = dict(_all_five_layers_passing())
    layers["NotALayer"] = ([], pd.DataFrame())
    try:
        report.build_summary("f.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)
        assert False, "expected KeyError for an unknown layer key"
    except KeyError as e:
        assert "NotALayer" in str(e)


def test_build_summary_raises_naming_missing_registry_layer():
    layers = dict(_all_five_layers_passing())
    del layers["Settlement"]
    try:
        report.build_summary("f.xlsx", layers, mlos_row_count=10, takeoff_row_count=5)
        assert False, "expected KeyError naming the missing layer"
    except KeyError as e:
        assert "Settlement" in str(e)


def test_get_rule_returns_the_registered_boundary_rule():
    assert qc.get_rule("B0").layer == "Boundary"


def test_get_rule_raises_for_an_unregistered_id():
    try:
        qc.get_rule("nope-not-registered")
        assert False, "expected KeyError for an unregistered rule id"
    except KeyError:
        pass
