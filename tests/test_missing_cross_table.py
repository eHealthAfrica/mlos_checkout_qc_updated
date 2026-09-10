"""Proves INTEG-02's six new ``.missing`` findings actually detect a blank cross-table cell,
rather than merely being registered and reading zero forever (Pitfall 2, 02-RESEARCH.md).

The shared 10-row fixture (``tests/fixtures.py::build_mlos_fixture``/``build_takeoff_fixture``)
has no genuinely blank cross-table cell, so it cannot exercise the failing branch of any of
``2.missing``, ``3.missing``, ``4.missing``, ``TP2.missing``, ``TP3.missing`` or ``TP4.missing``.
This file uses the two purpose-built blank-cell fixtures instead
(``build_mlos_fixture_with_blanks`` / ``build_takeoff_fixture_with_blanks``), which carry three
deliberately different absence forms across the two frames — empty string, whitespace-only, and
a case-insensitive sentinel — so a fix that only recognises one of the three forms cannot pass
here.
"""

import qc
from fixtures import build_mlos_fixture, build_mlos_fixture_with_blanks
from fixtures import build_takeoff_fixture_with_blanks
from qc.predicates import vec_is_absent

# The six cross-table columns under test, paired (MLoS column, Takeoffpoint column).
_MLOS_ABSENCE_COLS = ("takeoffpoint", "takeoffpoint_code", "ward_code")
_TAKEOFF_ABSENCE_COLS = ("name", "code", "wardcode")

_MLOS_COUNTS = ("2", "3", "4", "2.missing", "3.missing", "4.missing")
_TAKEOFF_COUNTS = ("TP2", "TP3", "TP4", "TP2.missing", "TP3.missing", "TP4.missing")

# Each match rule's dotted `.missing` sibling, paired for the disjointness assertion.
_MLOS_PAIRS = (("2", "2.missing"), ("3", "3.missing"), ("4", "4.missing"))
_TAKEOFF_PAIRS = (("TP2", "TP2.missing"), ("TP3", "TP3.missing"), ("TP4", "TP4.missing"))


def _mlos_checks_by_id(checks):
    return {c["Rule#"]: (c["Failing Rows"], c["Total Rows"]) for c in checks}


def _rows_for(detail, rule_id):
    if detail.empty:
        return set()
    return set(detail[detail["Rule#"] == rule_id].index)


def test_blank_fixtures_actually_contain_the_absences_they_claim_to():
    """Defensive floor (plan Task 2): without this, a future edit that accidentally fills the
    blank cells would leave every other assertion in this file reading zero and passing for the
    wrong reason."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()
    for col in _MLOS_ABSENCE_COLS:
        assert int(vec_is_absent(mlos[col]).sum()) == 1, (
            f"expected exactly one absent cell in mlos['{col}'], "
            f"got {int(vec_is_absent(mlos[col]).sum())}"
        )
    for col in _TAKEOFF_ABSENCE_COLS:
        assert int(vec_is_absent(takeoff[col]).sum()) == 1, (
            f"expected exactly one absent cell in takeoff['{col}'], "
            f"got {int(vec_is_absent(takeoff[col]).sum())}"
        )


def test_mlos_side_match_and_missing_counts_are_exactly_one_of_three():
    """Row 2 ('Blank2') is the only mismatched-but-non-blank row -> fails 2/3/4.
    Row 1 ('Blank1') is the only absent-source row -> fails 2.missing/3.missing/4.missing.
    Row 0 ('Blank0') passes everything."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()
    checks, _ = qc.mlos.run_mlos_qc(mlos, takeoff)
    counts = _mlos_checks_by_id(checks)
    for rule_id in _MLOS_COUNTS:
        assert counts.get(rule_id) == (1, 3), (
            f"{rule_id}: expected (Failing Rows, Total Rows) == (1, 3), got {counts.get(rule_id)}"
        )


def test_takeoff_side_match_and_missing_counts_are_exactly_one_of_three():
    """Mirrors the MLoS-side test: takeoff row 2 (orphan) fails TP2/TP3/TP4; takeoff row 1
    (three absence forms) fails TP2.missing/TP3.missing/TP4.missing; row 0 passes everything."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()
    checks, _ = qc.takeoff.run_takeoff_qc(takeoff, mlos)
    counts = _mlos_checks_by_id(checks)
    for rule_id in _TAKEOFF_COUNTS:
        assert counts.get(rule_id) == (1, 3), (
            f"{rule_id}: expected (Failing Rows, Total Rows) == (1, 3), got {counts.get(rule_id)}"
        )


def test_no_row_is_counted_by_both_a_match_rule_and_its_missing_sibling_mlos_side():
    """Structural proof of D-03's exactly-three-checks count: the detail rows under a match
    rule and its `.missing` sibling must never intersect. If they did, the absent-source
    exclusion in the match mask (Pattern 2 of 02-RESEARCH.md) would not actually be in effect,
    and a single blank cell would produce four failing checks instead of three."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()
    _, detail = qc.mlos.run_mlos_qc(mlos, takeoff)
    for match_id, missing_id in _MLOS_PAIRS:
        overlap = _rows_for(detail, match_id) & _rows_for(detail, missing_id)
        assert not overlap, f"{match_id} and {missing_id} both counted row(s) {overlap}"


def test_no_row_is_counted_by_both_a_match_rule_and_its_missing_sibling_takeoff_side():
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()
    _, detail = qc.takeoff.run_takeoff_qc(takeoff, mlos)
    for match_id, missing_id in _TAKEOFF_PAIRS:
        overlap = _rows_for(detail, match_id) & _rows_for(detail, missing_id)
        assert not overlap, f"{match_id} and {missing_id} both counted row(s) {overlap}"


def test_blank_facing_blank_no_longer_reads_as_a_match():
    """The literal content of defect F9: MLoS blanks row 1's whitespace-only `takeoffpoint`
    faces Takeoffpoint blanks row 1's empty-string `name` across the join. Under the pre-fix
    code, `""` entered the valid-target set (``.dropna()`` cannot remove an empty string under
    ``keep_default_na=False``), so a blank matched a blank and this pair silently read as a
    successful reconciliation. Post-fix, this pair must appear in `2.missing` and `TP2.missing`
    and in neither `2` nor `TP2`."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()

    _, mlos_detail = qc.mlos.run_mlos_qc(mlos, takeoff)
    _, takeoff_detail = qc.takeoff.run_takeoff_qc(takeoff, mlos)

    blank_row_index = mlos.index[1]  # 'Blank1' — whitespace-only takeoffpoint
    assert blank_row_index in _rows_for(mlos_detail, "2.missing")
    assert blank_row_index not in _rows_for(mlos_detail, "2")

    tp_blank_row_index = takeoff.index[1]  # empty-string name
    assert tp_blank_row_index in _rows_for(takeoff_detail, "TP2.missing")
    assert tp_blank_row_index not in _rows_for(takeoff_detail, "TP2")


def test_missing_detail_frames_carry_only_their_own_subject_tables_columns():
    """D-06: each `.missing` finding reports blanks in its own subject table only — a
    Takeoffpoint-side `.missing` detail frame must never carry an MLoS identifying column
    (e.g. `settlement_name`), and vice versa."""
    mlos = build_mlos_fixture_with_blanks()
    takeoff = build_takeoff_fixture_with_blanks()

    _, mlos_detail = qc.mlos.run_mlos_qc(mlos, takeoff)
    mlos_missing_cols = set(mlos_detail[mlos_detail["Rule#"] == "4.missing"].columns)
    assert "ward_code" in mlos_missing_cols
    assert "wardcode" not in mlos_missing_cols

    _, takeoff_detail = qc.takeoff.run_takeoff_qc(takeoff, mlos)
    takeoff_missing_cols = set(takeoff_detail[takeoff_detail["Rule#"] == "TP4.missing"].columns)
    assert "wardcode" in takeoff_missing_cols
    assert "settlement_name" not in takeoff_missing_cols


def test_mlos_side_missing_checks_emit_unconditionally_with_no_takeoffpoint_table():
    """D-07: 2.missing/3.missing/4.missing test MLoS's own columns and must emit even when no
    Takeoffpoint table was supplied at all — while 2/3/4 themselves must not emit, since they
    require the Takeoffpoint-side column to exist."""
    import pandas as pd

    mlos = build_mlos_fixture_with_blanks()
    checks, _ = qc.mlos.run_mlos_qc(mlos, pd.DataFrame())
    counts = _mlos_checks_by_id(checks)

    for rule_id in ("2.missing", "3.missing", "4.missing"):
        assert counts.get(rule_id) == (1, 3), (
            f"{rule_id}: expected (1, 3) even with an empty Takeoffpoint table, got {counts.get(rule_id)}"
        )
    for rule_id in ("2", "3", "4"):
        assert rule_id not in counts, f"{rule_id} must not emit with no Takeoffpoint table present"


def test_shared_fixture_is_untouched_by_this_plan():
    """Sanity check per this plan's environment_notes: the frozen shared 10-row fixture's row
    count and content must not have been modified while adding the blank-cell builders above."""
    mlos = build_mlos_fixture()
    assert len(mlos) == 10
    assert mlos.at[mlos.index[0], "ward_code"] == "81110"
