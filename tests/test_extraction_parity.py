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
