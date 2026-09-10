"""Standing three-state invariant for the boundary reference (INTEG-04, D-16 through D-19).

The boundary reference's *scope* is now a reported fact rather than a silent branch: a run is
either state-matched, nationally widened (the fallback fired), or the reference is unavailable
entirely. Each state emits a different, exact boundary check set — `B0..B4` with `B4` PASS,
the same five with `B4` FAIL, or exactly `B0, B5`. This test asserts each set with an equality
check rather than membership, because the exactness is the whole point: a membership check
would keep passing while silent widening was reintroduced alongside `B4` (assumption-delta
companion invariant, 02-CONTEXT.md).
"""

import pandas as pd

import qc
from fixtures import build_mlos_fixture, load_boundary_fixtures


def _run(mlos, ref, bbox):
    return qc.boundary.run_ward_boundary_qc(mlos, ref, bbox)


def test_state_matched_emits_exactly_b0_through_b4_with_b4_pass():
    """State one: the reference exists and the file's states match it."""
    mlos = build_mlos_fixture()
    ref, bbox = load_boundary_fixtures()

    checks, _ = _run(mlos, ref, bbox)
    ids = sorted({c["Rule#"] for c in checks})
    assert ids == ["B0", "B1", "B2", "B3", "B4"], ids

    by_id = {c["Rule#"]: c for c in checks}
    # frozen baseline values must not move — this change is additive, not a behaviour change
    assert (by_id["B0"]["Failing Rows"], by_id["B0"]["Total Rows"]) == (0, 10), by_id["B0"]
    assert (by_id["B1"]["Failing Rows"], by_id["B1"]["Total Rows"]) == (1, 10), by_id["B1"]
    assert (by_id["B2"]["Failing Rows"], by_id["B2"]["Total Rows"]) == (3, 10), by_id["B2"]
    assert (by_id["B3"]["Failing Rows"], by_id["B3"]["Total Rows"]) == (1, 10), by_id["B3"]

    b4 = by_id["B4"]
    assert "PASS" in b4["Status"], b4
    assert (b4["Failing Rows"], b4["Total Rows"]) == (0, 1), b4

    # The ward count named in B4's PASS description is computed from the reference at test
    # time, never hard-coded, so this assertion survives a future change to the bundled CSVs.
    states = set(mlos["state_name"].dropna().astype(str).str.strip().str.lower())
    ref_norm = ref["state_name"].astype(str).str.strip().str.lower()
    expected = ref[ref_norm.isin(states)]["ward_code"].dropna().astype(str).str.strip().nunique()
    assert str(expected) in b4["Description"], b4["Description"]


def test_widened_fallback_emits_b4_fail_naming_b1_and_b2():
    """State two: the reference exists but the file's state matches nothing in it."""
    mlos = build_mlos_fixture().copy()
    mlos["state_name"] = "Atlantis"
    ref, bbox = load_boundary_fixtures()

    # Defensive floor: the substituted state name must genuinely empty the state filter, or
    # this test could green because "Atlantis" happened to exist in the reference.
    ref_norm = ref["state_name"].astype(str).str.strip().str.lower()
    assert not ref_norm.eq("atlantis").any(), "substituted state name unexpectedly matches the reference"

    checks, _ = _run(mlos, ref, bbox)
    ids = sorted({c["Rule#"] for c in checks})
    assert ids == ["B0", "B1", "B2", "B3", "B4"], ids

    by_id = {c["Rule#"]: c for c in checks}
    b4 = by_id["B4"]
    assert "FAIL" in b4["Status"], b4
    assert (b4["Failing Rows"], b4["Total Rows"]) == (1, 1), b4
    assert "B1" in b4["Description"] and "B2" in b4["Description"], b4["Description"]

    # B1 still runs and reports a real count -- a ward code absent from even the national
    # reference is still a true finding worth reporting (D-16).
    assert by_id["B1"]["Total Rows"] == 10, by_id["B1"]


def test_reference_unavailable_emits_exactly_b0_and_b5():
    """State three: the reference is unavailable (both frames empty)."""
    mlos = build_mlos_fixture()
    checks, detail = _run(mlos, pd.DataFrame(), pd.DataFrame())

    ids = sorted({c["Rule#"] for c in checks})
    assert ids == ["B0", "B5"], ids

    by_id = {c["Rule#"]: c for c in checks}
    b5 = by_id["B5"]
    assert "FAIL" in b5["Status"], b5
    assert (b5["Failing Rows"], b5["Total Rows"]) == (1, 1), b5
    assert detail.empty


def test_one_matching_ward_threshold_is_pass():
    """Threshold edge: exactly one matching ward in the state filter is still non-empty, so
    B4 must PASS -- the trigger is emptiness of the filter result, not a size comparison
    against the national reference."""
    mlos = build_mlos_fixture()
    ref = pd.DataFrame([
        {"ward_code": "81110", "state_name": "Zamfara",
         "lga_code": "811", "lga_name": "Shinkafi", "ward_name": "Shinkafi South"},
        {"ward_code": "99999", "state_name": "Lagos",
         "lga_code": "999", "lga_name": "Somewhere", "ward_name": "Elsewhere"},
    ])
    bbox = pd.DataFrame([
        {"ward_code": "81110", "min_lon": 6.0, "min_lat": 13.0, "max_lon": 7.0, "max_lat": 14.0},
        {"ward_code": "99999", "min_lon": 3.0, "min_lat": 6.0, "max_lon": 4.0, "max_lat": 7.0},
    ])

    checks, _ = _run(mlos, ref, bbox)
    by_id = {c["Rule#"]: c for c in checks}
    assert "B4" in by_id, sorted(by_id)
    assert "PASS" in by_id["B4"]["Status"], by_id["B4"]


def test_filter_selecting_every_national_row_is_still_pass():
    """Adjacency edge: a state filter that happens to select every row of the national
    reference is still a non-empty filter result, so B4 must PASS -- the flag is set by
    emptiness, not by set equality between the filtered and national references."""
    mlos = build_mlos_fixture().copy()
    mlos["state_name"] = "Zamfara"
    ref = pd.DataFrame([
        {"ward_code": "81110", "state_name": "Zamfara",
         "lga_code": "811", "lga_name": "Shinkafi", "ward_name": "Shinkafi South"},
    ])
    bbox = pd.DataFrame([
        {"ward_code": "81110", "min_lon": 6.0, "min_lat": 13.0, "max_lon": 7.0, "max_lat": 14.0},
    ])

    checks, _ = _run(mlos, ref, bbox)
    by_id = {c["Rule#"]: c for c in checks}
    assert "B4" in by_id, sorted(by_id)
    assert "PASS" in by_id["B4"]["Status"], by_id["B4"]


def test_sentinel_ward_code_fails_b0():
    """A sentinel `n/a` ward code must fail B0 via the shared vec_is_absent predicate (D-04),
    the same predicate every other absence check uses -- so a sentinel ward code cannot
    report PASS on B0 while firing Rule 1 and 4.missing elsewhere (D-03)."""
    mlos = build_mlos_fixture().copy()
    mlos.loc[mlos.index[0], "ward_code"] = "n/a"
    ref, bbox = load_boundary_fixtures()

    checks, _ = _run(mlos, ref, bbox)
    by_id = {c["Rule#"]: c for c in checks}
    assert by_id["B0"]["Failing Rows"] == 1, by_id["B0"]


def test_boundary_order_is_b0_through_b5():
    """Canonical boundary order reads B0, B1, B2, B3, B4, B5 in that relative order, which
    keeps Phase 3's VERDICT-06 satisfiable."""
    order = qc.canonical_order()
    for rule_id in ["B0", "B1", "B2", "B3", "B4", "B5"]:
        assert rule_id in order, f"{rule_id} not registered in canonical_order(): {order}"
    positions = [order.index(rule_id) for rule_id in ["B0", "B1", "B2", "B3", "B4", "B5"]]
    assert positions == sorted(positions), positions
