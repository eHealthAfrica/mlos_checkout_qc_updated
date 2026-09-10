"""Parity harness: prove an extracted qc/ layer produces exactly what the frozen pre-extraction
baseline recorded (tests/baseline/qc_baseline.json) — for the identifiers the baseline itself
knew about. From Phase 2 onward the baseline is a **partial**, not total, oracle: it was captured
before D-04's absence predicate existed and before this phase's nine new rule identifiers were
registered, so a live layer is allowed to disagree with it in two declared ways without that
being a regression — see ``MOVED_CHECKS`` and ``_assert_new_identifiers_are_registered`` below.

Exposes normalisation helpers plans 04, 05 and 06 reuse as they add their own layers' parity
tests: ``normalize_checks`` (sorts a checks list the same way capture_baseline.py's ``_layer()``
did — by the pair of check name and description), ``normalize_detail`` (sorts a detail
DataFrame's records with column order preserved), and ``_nan_safe`` (replaces float NaN cells
with a fixed sentinel on both sides of a detail comparison — needed by any layer whose detail
rows carry a genuine null cell, or whose concatenated per-rule detail frames pick up NaN from
column-union across rules with different ``extra`` columns; Settlement, Takeoffpoint and
Boundary all hit the latter case). This file adds one test function per extracted layer; do not
build a parameterised table over layers that do not exist yet in qc/, which would either skip or
fail for layers still living in app.py.

Per planner decision 4 (02-01-PLAN.md), this is the only plan that edits this file. Plans 02
through 05 register new rule identifiers of their own (the six ``.missing`` checks, ``S3``,
``B4``, ``B5``) and assert them in their own new test files — never here. What makes that
possible is ``_assert_checks_match_baseline``'s scoping: it compares a layer's live checks against
the baseline only for identifiers the baseline itself carries, and merely asserts that any live
identifier the baseline does not carry is at least a registered rule (``qc.canonical_order()``),
so a stray *unregistered* check still fails here even though a *new, registered* one does not.
"""

import json
from pathlib import Path

import pandas as pd

import qc

BASELINE_PATH = Path(__file__).resolve().parent / "baseline" / "qc_baseline.json"
BASELINE = json.loads(BASELINE_PATH.read_text())

# Every field participating in a check-record comparison — never a subset.
CHECK_FIELDS = ["Rule#", "QC Check", "Description", "Failing Rows", "Total Rows", "Fail %", "Status"]


def normalize_checks(checks: list) -> list:
    """Sort a checks list the same way capture_baseline.py's _layer() sorted it: by the pair of
    check name and description. Returns a new list; does not mutate the input."""
    return sorted(checks, key=lambda c: (c.get("QC Check", ""), c.get("Description", "")))


def normalize_detail(detail: "pd.DataFrame") -> list:
    """Normalise a detail DataFrame to sorted record dicts, column order preserved — mirrors
    capture_baseline.py's _sorted_detail_records()."""
    if detail is None or detail.empty:
        return []
    records = detail.to_dict(orient="records")
    columns = list(detail.columns)
    return sorted(records, key=lambda r: tuple(str(r[c]) for c in columns))


def _split_by_baseline_ids(actual_checks: list, baseline_checks: list) -> "tuple[list, list]":
    """Split a live layer's checks into those whose Rule# the frozen baseline carries, and those
    registered since — both groups keep their original relative order."""
    baseline_ids = {c["Rule#"] for c in baseline_checks}
    in_baseline = [c for c in actual_checks if c["Rule#"] in baseline_ids]
    new_since_baseline = [c for c in actual_checks if c["Rule#"] not in baseline_ids]
    return in_baseline, new_since_baseline


def _assert_new_identifiers_are_registered(layer_name: str, new_checks: list):
    """A live identifier the baseline never carried is only exempt from the field-by-field
    baseline comparison, not from existing at all: it must still be a registered rule identifier,
    so a check emitted under a stray, unregistered ``Rule#`` still fails here."""
    canonical = set(qc.canonical_order())
    for c in new_checks:
        assert c["Rule#"] in canonical, (
            f"{layer_name}: check {c.get('QC Check')!r} emitted under identifier "
            f"{c['Rule#']!r}, which is absent from the frozen baseline AND not in "
            f"qc.canonical_order() — a Phase 2+ addition must be a registered rule identifier, "
            f"not merely undocumented in the baseline"
        )


def _assert_checks_match_baseline(layer_name: str, actual_checks: list, expected_checks: list):
    """Compare a layer's live checks against the baseline, scoped to the intersection of
    identifiers the baseline itself carries (planner decision 4): only those are compared
    field-by-field; anything registered since must merely be a real registered identifier (see
    ``_assert_new_identifiers_are_registered``). Field-by-field divergence messages name which
    field of which check diverged — the value of this assertion is entirely in how fast it
    points at the cause."""
    in_baseline, new_since_baseline = _split_by_baseline_ids(actual_checks, expected_checks)

    assert len(in_baseline) == len(expected_checks), (
        f"{layer_name}: expected {len(expected_checks)} in-baseline checks, "
        f"got {len(in_baseline)} from the extracted layer"
    )
    for i, (actual, expected) in enumerate(zip(in_baseline, expected_checks)):
        for field in CHECK_FIELDS:
            assert actual.get(field) == expected.get(field), (
                f"{layer_name} check #{i} ({actual.get('QC Check')!r}): field {field!r} "
                f"diverged from baseline — actual={actual.get(field)!r} "
                f"expected={expected.get(field)!r}"
            )
    _assert_new_identifiers_are_registered(layer_name, new_since_baseline)


def test_schema_layer_matches_baseline(mlos_df, takeoff_df):
    """qc.schema.run_schema_qc, run against the fixture, must produce — after normalisation —
    a checks list identical to the baseline's schema entry on every field including Rule#
    (S1/S2 are frozen by D-04 and must not have changed), and a detail record set identical to
    the baseline's."""
    checks, detail = qc.schema.run_schema_qc(mlos_df, takeoff_df)

    actual_checks = normalize_checks(checks)
    actual_detail = normalize_detail(detail)

    expected_checks = BASELINE["schema"]["checks"]
    expected_detail = BASELINE["schema"]["detail"]

    _assert_checks_match_baseline("schema", actual_checks, expected_checks)
    assert actual_detail == expected_detail, (
        f"schema detail records diverged from baseline: actual={actual_detail!r} "
        f"expected={expected_detail!r}"
    )


# Explicit mapping from check name (the "QC Check" field, unchanged by the rename and unique
# across all 25 MLoS checks) to the new field-named identifier this plan assigns it. Asserted
# against directly, rather than merely checking the identifier differs from the pre-fix "11" or
# "12" — a test that only asserted "changed" would pass even if the rename produced the wrong
# field name.
RENAMED_IDENTIFIERS = {
    "urban is Y or N": "11.urban",
    "rural is Y or N": "11.rural",
    "scattered is Y or N": "11.scattered",
    "highrisk = Y/N/NA": "12.highrisk",
    "slums = Y/N/NA": "12.slums",
    "densely_populated = Y/N/NA": "12.densely_populated",
    "hard2reach = Y/N/NA": "12.hard2reach",
    "border = Y/N/NA": "12.border",
    "nomadic = Y/N/NA": "12.nomadic",
    "riverine = Y/N/NA": "12.riverine",
    "fulani = Y/N/NA": "12.fulani",
}

# The pre-extraction baseline recorded these same eleven checks under the bare identifier "11"
# or "12" (whichever loop produced them) — used to normalise the actual detail rows' Rule#
# column back to what the baseline recorded, so the two can be compared row for row.
_OLD_ID_BY_NAME = {
    name: ("11" if new_id.startswith("11.") else "12")
    for name, new_id in RENAMED_IDENTIFIERS.items()
}

# Planner decision 4: identifiers whose baseline field values Phase 2 deliberately moves,
# declared once with the requirement and decision that moved them. Applied as an override onto
# the expected baseline record before comparison, rather than requiring a second frozen JSON.
# The single entry this task creates: D-04's absence predicate (qc.predicates.vec_is_absent) now
# also catches the CSV/XLSX-style blank cell (empty string, whitespace-only) that ``.isnull()``
# alone missed, so the unmodified 10-row fixture's row 2 (master_id M-0003, Bravo, blank
# latitude/longitude) now also fails Rule 1 alongside row 1 (master_id M-0002, Alpha, null
# timestamp) — Failing Rows moves from the baseline's 1 to 2, and Fail % from "10.0%" to "20.0%".
MOVED_CHECKS = {
    "Required Fields — Not Null": {
        "fields": {"Failing Rows": 2, "Fail %": "20.0%"},
        "requirement": "INTEG-01",
        "decision": "D-04",
    },
}


def _nan_safe(records: list) -> list:
    """Replace every float NaN cell with a fixed sentinel string. MLoS's detail rows carry real
    null cells (e.g. row 1's deliberately-None timestamp), and Python's NaN never equals itself
    (``float('nan') != float('nan')``) — both in a freshly-built DataFrame and in the baseline
    JSON, whose NaN cells round-trip through ``json.dumps``/``json.loads`` as the bare (non-
    standard but Python-accepted) ``NaN`` token, back into ``float('nan')``. Without this, a
    dict-equality comparison over rows containing NaN would fail even when every field is
    identical."""
    def _clean(value):
        return "<NaN>" if isinstance(value, float) and value != value else value

    return [{k: _clean(v) for k, v in record.items()} for record in records]


def _actual_mlos_detail_with_baseline_ids(detail: "pd.DataFrame") -> list:
    """Like normalize_detail, but first rewrites the Rule# of every renamed check's detail rows
    back to the bare "11"/"12" the baseline recorded — keyed off the "Rule" column, which holds
    the check name and is unchanged by the rename. Detail rows for the fourteen frozen-identifier
    checks pass through untouched."""
    if detail is None or detail.empty:
        return []
    records = detail.to_dict(orient="records")
    columns = list(detail.columns)
    adjusted = []
    for record in records:
        record = dict(record)
        old_id = _OLD_ID_BY_NAME.get(record.get("Rule"))
        if old_id is not None:
            record["Rule#"] = old_id
        adjusted.append(record)
    return sorted(adjusted, key=lambda r: tuple(str(r[c]) for c in columns))


def test_mlos_layer_matches_baseline(mlos_df, takeoff_df):
    """qc.mlos.run_mlos_qc, run against the fixture, must match the frozen baseline's mlos entry
    on every field for the fourteen checks whose identifier is frozen, and on every field except
    the identifier for the eleven renamed checks — whose new identifier must equal the explicit
    mapping in RENAMED_IDENTIFIERS, not merely differ from the old shared one.

    Checks are paired by the "QC Check" field rather than by list position: the baseline was
    captured while YN_NA_COLS was still a set literal, so the eight profile-flag checks sit in an
    arbitrary order inside it, and a positional comparison would produce a spurious failure that
    looks exactly like a real regression. "QC Check" is unchanged by the rename and unique across
    all 25 checks, which is what makes it a safe join key here.
    """
    checks, detail = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)

    expected_checks = BASELINE["mlos"]["checks"]
    expected_by_name = {c["QC Check"]: c for c in expected_checks}
    actual_by_name = {c["QC Check"]: c for c in checks}

    # Decision 4's in-baseline scoping, by name rather than by Rule# (mlos's check names are
    # unaffected by the R11/R12 rename and are unique, unlike a bare identifier a later plan might
    # reuse in a different layer): every baseline name must still be emitted; a name the baseline
    # never carried is exempt from the field comparison below but must still be a registered
    # identifier, so plans 02-05 can add mlos identifiers without this file needing another edit.
    missing_from_actual = set(expected_by_name) - set(actual_by_name)
    assert not missing_from_actual, (
        f"mlos: baseline check name(s) no longer emitted by the live layer: "
        f"{sorted(missing_from_actual)!r}"
    )
    new_since_baseline = [c for c in checks if c["QC Check"] not in expected_by_name]
    _assert_new_identifiers_are_registered("mlos", new_since_baseline)

    for name, expected in expected_by_name.items():
        actual = actual_by_name[name]
        expected = dict(expected)
        if name in MOVED_CHECKS:
            expected.update(MOVED_CHECKS[name]["fields"])
        if name in RENAMED_IDENTIFIERS:
            expected_new_id = RENAMED_IDENTIFIERS[name]
            assert actual["Rule#"] == expected_new_id, (
                f"mlos check {name!r}: field 'Rule#' diverged — "
                f"actual={actual['Rule#']!r} expected={expected_new_id!r}"
            )
            fields_to_compare = [f for f in CHECK_FIELDS if f != "Rule#"]
        else:
            fields_to_compare = CHECK_FIELDS
        for field in fields_to_compare:
            assert actual.get(field) == expected.get(field), (
                f"mlos check {name!r}: field {field!r} diverged from baseline — "
                f"actual={actual.get(field)!r} expected={expected.get(field)!r}"
            )

    # Decision 4: the same in-baseline filter applied to both sides of the detail comparison, and
    # Rule 1's own detail rows excluded from it entirely — its row count and content moved under
    # D-04 by construction, so a generic diff against the frozen baseline would only ever fail.
    # Rule 1 gets one explicit hand-derived assertion instead, immediately below.
    baseline_check_ids = {c["Rule#"] for c in expected_checks}  # baseline's own (old) identifiers
    detail_id_scope = baseline_check_ids - {"1"}
    adjusted_actual_detail = _actual_mlos_detail_with_baseline_ids(detail)
    actual_detail = _nan_safe([r for r in adjusted_actual_detail if r["Rule#"] in detail_id_scope])
    expected_detail = _nan_safe(
        [r for r in BASELINE["mlos"]["detail"] if r.get("Rule#") in detail_id_scope]
    )
    assert actual_detail == expected_detail, (
        f"mlos detail records diverged from baseline (after normalising the eleven renamed "
        f"checks' Rule# back to the baseline's bare identifier, and excluding Rule 1's own rows): "
        f"actual={actual_detail!r} expected={expected_detail!r}"
    )

    # Rule 1's BASE column set (state_code, state_name, lga_name, ward_code, settlement_name,
    # takeoffpoint, takeoffpoint_code) plus _NOT_NULL_COLS never includes master_id, so eha_guid
    # — unique per fixture row and present via _NOT_NULL_COLS — is the identifying key here.
    rule1_detail = detail[detail["Rule#"] == "1"] if not detail.empty else detail
    rule1_by_eha_guid = {row["eha_guid"]: row["Null Fields"] for _, row in rule1_detail.iterrows()}
    expected_rule1 = {
        "22222222-2222-2222-2222-222222222222": "timestamp",           # M-0002, Alpha
        "33333333-3333-3333-3333-333333333333": "latitude, longitude",  # M-0003, Bravo
    }
    assert rule1_by_eha_guid == expected_rule1, (
        f"Rule 1 detail rows diverged from the hand-derived INTEG-01/D-04 expectation: "
        f"actual={rule1_by_eha_guid!r} expected={expected_rule1!r}"
    )


def test_settlement_layer_matches_baseline(mlos_df):
    """qc.settlement.run_settlement_qc, run against the fixture, must produce — after
    normalisation — a checks list identical to the baseline's settlement entry on every field
    including Rule# (SQ1/SQ2/SQ2b/SQ3/SQ4 are frozen by D-04 and were never renamed), and a
    detail record set identical to the baseline's."""
    checks, detail = qc.settlement.run_settlement_qc(mlos_df)

    actual_checks = normalize_checks(checks)
    actual_detail = _nan_safe(normalize_detail(detail))

    expected_checks = BASELINE["settlement"]["checks"]
    expected_detail = _nan_safe(BASELINE["settlement"]["detail"])

    _assert_checks_match_baseline("settlement", actual_checks, expected_checks)
    assert actual_detail == expected_detail, (
        f"settlement detail records diverged from baseline: actual={actual_detail!r} "
        f"expected={expected_detail!r}"
    )


def test_takeoff_layer_matches_baseline(takeoff_df, mlos_df):
    """qc.takeoff.run_takeoff_qc, run against the fixture, must produce — after normalisation —
    a checks list identical to the baseline's takeoff entry on every field including Rule#
    (TP2/TP3/TP4/TP5 are frozen by D-04 and were never renamed), and a detail record set
    identical to the baseline's."""
    checks, detail = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df)

    actual_checks = normalize_checks(checks)
    actual_detail = _nan_safe(normalize_detail(detail))

    expected_checks = BASELINE["takeoff"]["checks"]
    expected_detail = _nan_safe(BASELINE["takeoff"]["detail"])

    _assert_checks_match_baseline("takeoff", actual_checks, expected_checks)
    assert actual_detail == expected_detail, (
        f"takeoff detail records diverged from baseline: actual={actual_detail!r} "
        f"expected={expected_detail!r}"
    )


def test_boundary_layer_matches_baseline(mlos_df, boundary_refs):
    """qc.boundary.run_ward_boundary_qc, run against the fixture and the real bundled boundary
    reference, must produce — after normalisation — a checks list identical to the baseline's
    boundary entry on every field including Rule# (B0/B1/B2/B3 are frozen by D-04 and were never
    renamed), and a detail record set identical to the baseline's."""
    ref_df, bbox_df = boundary_refs
    checks, detail = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df)

    actual_checks = normalize_checks(checks)
    actual_detail = _nan_safe(normalize_detail(detail))

    expected_checks = BASELINE["boundary"]["checks"]
    expected_detail = _nan_safe(BASELINE["boundary"]["detail"])

    _assert_checks_match_baseline("boundary", actual_checks, expected_checks)
    assert actual_detail == expected_detail, (
        f"boundary detail records diverged from baseline: actual={actual_detail!r} "
        f"expected={expected_detail!r}"
    )


def test_takeoff_layer_returns_nothing_for_an_empty_frame():
    """The relocated Takeoffpoint layer must preserve its pre-extraction skip path: an empty
    takeoff frame produces an empty check list and an empty detail frame, rather than a
    fabricated pass — this is the condition Phase 3's VERDICT-02 will score as not-applicable."""
    checks, detail = qc.takeoff.run_takeoff_qc(pd.DataFrame(), pd.DataFrame())
    assert checks == []
    assert detail.empty


def test_boundary_layer_reports_a_missing_ward_code_column(mlos_df, boundary_refs):
    """With the ward_code column dropped, the relocated Boundary layer must return exactly one
    check, identifier B0, and an empty detail frame — the early-return path that keeps a file
    missing that column from crashing the run."""
    ref_df, bbox_df = boundary_refs
    dropped = mlos_df.drop(columns=["ward_code"])
    checks, detail = qc.boundary.run_ward_boundary_qc(dropped, ref_df, bbox_df)
    assert len(checks) == 1
    assert checks[0]["Rule#"] == "B0"
    assert detail.empty
