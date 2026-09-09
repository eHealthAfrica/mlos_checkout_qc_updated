"""Parity harness: prove an extracted qc/ layer produces exactly what the frozen pre-extraction
baseline recorded (tests/baseline/qc_baseline.json).

Exposes two normalisation helpers plans 04, 05 and 06 will reuse as they add their own layers'
parity tests: ``normalize_checks`` (sorts a checks list the same way capture_baseline.py's
``_layer()`` did — by the pair of check name and description) and ``normalize_detail`` (sorts a
detail DataFrame's records with column order preserved). This file adds one test function per
extracted layer; do not build a parameterised table over layers that do not exist yet in qc/,
which would either skip or fail for the four layers still living in app.py.
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


def _assert_checks_match_baseline(layer_name: str, actual_checks: list, expected_checks: list):
    """Compare two normalised checks lists field-by-field, naming which field of which check
    diverged — the value of this assertion is entirely in how fast it points at the cause."""
    assert len(actual_checks) == len(expected_checks), (
        f"{layer_name}: expected {len(expected_checks)} checks in the baseline, "
        f"got {len(actual_checks)} from the extracted layer"
    )
    for i, (actual, expected) in enumerate(zip(actual_checks, expected_checks)):
        for field in CHECK_FIELDS:
            assert actual.get(field) == expected.get(field), (
                f"{layer_name} check #{i} ({actual.get('QC Check')!r}): field {field!r} "
                f"diverged from baseline — actual={actual.get(field)!r} "
                f"expected={expected.get(field)!r}"
            )


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

    assert set(actual_by_name) == set(expected_by_name), (
        f"mlos: check-name sets diverged from baseline — "
        f"actual-only={set(actual_by_name) - set(expected_by_name)!r} "
        f"expected-only={set(expected_by_name) - set(actual_by_name)!r}"
    )

    for name, expected in expected_by_name.items():
        actual = actual_by_name[name]
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

    actual_detail = _nan_safe(_actual_mlos_detail_with_baseline_ids(detail))
    expected_detail = _nan_safe(BASELINE["mlos"]["detail"])
    assert actual_detail == expected_detail, (
        f"mlos detail records diverged from baseline (after normalising the eleven renamed "
        f"checks' Rule# back to the baseline's bare identifier): "
        f"actual={actual_detail!r} expected={expected_detail!r}"
    )
