"""Proves qc.columns.normalize_name/normalize_columns implement D-08/D-09/D-10 exactly:
purely typographic renaming, with collision detection running against the proposed
rename map before any rename is applied, so a duplicate column label is never produced.

Constructs frames inline with ``pandas.DataFrame`` and explicit header names — there is
no existing test that builds a bare non-fixture frame, and a colliding header set cannot
be expressed through ``tests/fixtures.py``'s row-dict shape at all (02-PATTERNS.md's "No
Analog Found" entry for this file).

S3 assertions (added in task 2) exercise ``qc.schema.run_schema_qc``'s ``collisions``
argument directly against small inline frames, in the same style as the rest of this
file, rather than through the 43-column shared fixture.
"""

import pandas as pd

import qc
from qc.columns import normalize_name, normalize_columns


# ─── normalize_name ────────────────────────────────────────────────────────────────

def test_normalize_name_strips_surrounding_whitespace():
    assert normalize_name(" ward_code ") == "ward_code", "surrounding spaces must be trimmed"


def test_normalize_name_lowercases_upper_and_mixed_case():
    assert normalize_name("SET_POPULATION") == "set_population", "all-upper header must lower-case"
    assert normalize_name("Ward_Code") == "ward_code", "mixed-case header must lower-case"


def test_normalize_name_collapses_whitespace_and_hyphen_runs_to_single_underscore():
    cases = {
        "Ward Code": "ward_code",           # single space
        "Field  Notes": "field_notes",      # several consecutive spaces
        "day-of-activity": "day_of_activity",  # single hyphen, multiple positions
        "a - b": "a_b",                     # run of mixed spaces and hyphens
        "a\tb": "a_b",                      # tab
    }
    for raw, expected in cases.items():
        assert normalize_name(raw) == expected, f"{raw!r} -> expected {expected!r}, got {normalize_name(raw)!r}"


def test_normalize_name_collapses_repeated_underscores():
    assert normalize_name("ward__code") == "ward_code", "repeated underscores must collapse to one"
    assert normalize_name("a___b") == "a_b", "a longer underscore run must also collapse to one"


def test_normalize_name_is_idempotent():
    """Applying the transform twice must equal applying it once, for every case above plus
    an already-canonical header."""
    cases = [" Ward Code ", "SET_POPULATION", "Field  Notes", "day-of-activity",
             "a - b", "ward__code", "ward_code", "already_canonical"]
    for raw in cases:
        once = normalize_name(raw)
        twice = normalize_name(once)
        assert twice == once, f"normalize_name is not idempotent for {raw!r}: once={once!r} twice={twice!r}"


def test_normalize_name_already_canonical_snake_case_is_returned_unchanged():
    assert normalize_name("ward_code") == "ward_code"
    assert normalize_name("set_population") == "set_population"


def test_normalize_name_empty_and_whitespace_only_return_empty_string():
    assert normalize_name("") == "", "empty string must normalise to empty string, not raise"
    assert normalize_name("   ") == "", "whitespace-only string must normalise to empty string, not raise"


# ─── normalize_columns: clean frames (no collisions) ───────────────────────────────

def test_normalize_columns_all_canonical_returns_equal_frame_and_empty_maps():
    df = pd.DataFrame({"ward_code": ["a"], "set_population": ["1"]})
    out, rename_map, collisions = normalize_columns(df)
    assert list(out.columns) == list(df.columns), "an all-canonical frame's columns must be unchanged"
    assert rename_map == {}, f"an all-canonical frame must yield an empty rename map, got {rename_map!r}"
    assert collisions == [], f"an all-canonical frame must yield no collisions, got {collisions!r}"


def test_normalize_columns_two_clean_headers_rename_and_populate_map():
    df = pd.DataFrame({"Ward Code": ["a"], "SET_POPULATION": ["1"]})
    out, rename_map, collisions = normalize_columns(df)
    assert list(out.columns) == ["ward_code", "set_population"], list(out.columns)
    assert rename_map == {"Ward Code": "ward_code", "SET_POPULATION": "set_population"}, rename_map
    assert collisions == []


def test_normalize_columns_renames_header_no_rule_reads():
    """D-09 has no canonical-set membership test: a header no rule reads still renames."""
    df = pd.DataFrame({"Field Notes": ["x"]})
    out, rename_map, collisions = normalize_columns(df)
    assert list(out.columns) == ["field_notes"], list(out.columns)
    assert rename_map == {"Field Notes": "field_notes"}, rename_map
    assert collisions == []


def test_normalize_columns_rename_map_contains_only_changed_headers():
    df = pd.DataFrame({"ward_code": ["a"], "Set Population": ["1"]})
    out, rename_map, collisions = normalize_columns(df)
    assert rename_map == {"Set Population": "set_population"}, (
        f"rename_map must exclude ward_code, since it did not change: {rename_map!r}"
    )


# ─── normalize_columns: collisions ─────────────────────────────────────────────────

def test_normalize_columns_colliding_pair_left_unnormalised_with_no_duplicate_labels():
    """Sub-case per 02-CONTEXT.md's planner_clarification: neither `Ward-Code` nor
    `Ward Code` is already spelled exactly as the canonical `ward_code`, so both are
    genuinely absent post-normalisation and left exactly as they arrived."""
    df = pd.DataFrame({"Ward-Code": ["a"], "Ward Code": ["b"]})
    out, rename_map, collisions = normalize_columns(df)

    assert list(out.columns) == ["Ward-Code", "Ward Code"], (
        f"a colliding pair must be left un-normalised, got {list(out.columns)!r}"
    )
    assert len(set(out.columns)) == len(out.columns), (
        f"duplicate column labels created: {list(out.columns)}"
    )
    assert len(collisions) == 1, collisions
    assert set(collisions[0]["originals"]) == {"Ward-Code", "Ward Code"}, collisions
    assert collisions[0]["normalized"] == "ward_code", collisions


def test_normalize_columns_colliding_pair_selecting_original_header_still_returns_a_series():
    """The concrete crash D-10 exists to prevent: with a duplicate label, `frame[col]`
    returns a DataFrame and `.astype(str).str.strip()` raises AttributeError. Proves the
    fix keeps both original headers independently selectable as a Series."""
    df = pd.DataFrame({"Ward-Code": ["a"], "Ward Code": ["b"]})
    out, _, _ = normalize_columns(df)

    left = out["Ward-Code"]
    right = out["Ward Code"]
    assert isinstance(left, pd.Series), f"expected a Series, got {type(left)}"
    assert isinstance(right, pd.Series), f"expected a Series, got {type(right)}"
    assert left.astype(str).str.strip().iloc[0] == "a"
    assert right.astype(str).str.strip().iloc[0] == "b"


def test_normalize_columns_three_way_collision_reports_one_group_not_two_pairwise():
    df = pd.DataFrame({"Ward Code": ["a"], "Ward-Code": ["b"], "ward  code": ["c"]})
    out, rename_map, collisions = normalize_columns(df)

    assert len(collisions) == 1, (
        f"three headers colliding on one normalised name must produce one group, not {len(collisions)}: {collisions}"
    )
    assert set(collisions[0]["originals"]) == {"Ward Code", "Ward-Code", "ward  code"}, collisions
    assert len(set(out.columns)) == len(out.columns), list(out.columns)
    assert rename_map == {}, "every header in a three-way collision is un-normalised, so the rename map is empty"


def test_normalize_columns_defensive_floor_colliding_case_actually_produces_a_collision_group():
    """A test that only asserted 'the frame has no duplicate labels' could pass against an
    implementation that never detects any collision at all. This pins that the fixture
    used above genuinely does collide."""
    df = pd.DataFrame({"Ward-Code": ["a"], "Ward Code": ["b"]})
    _, _, collisions = normalize_columns(df)
    assert len(collisions) >= 1, "the colliding-case fixture must produce at least one collision group"


# ─── normalize_columns: edges ───────────────────────────────────────────────────────

def test_normalize_columns_empty_frame_has_no_rename_map_or_collisions():
    df = pd.DataFrame()
    out, rename_map, collisions = normalize_columns(df)
    assert list(out.columns) == []
    assert rename_map == {}
    assert collisions == []


def test_normalize_columns_single_column_frame_can_never_collide():
    df = pd.DataFrame({"Ward Code": ["a"]})
    out, rename_map, collisions = normalize_columns(df)
    assert list(out.columns) == ["ward_code"]
    assert rename_map == {"Ward Code": "ward_code"}
    assert collisions == []


# ─── S3 "Column Name Collision" (qc.schema.run_schema_qc) ──────────────────────────

def test_s3_position_in_canonical_order_is_immediately_after_s2():
    """Keeps Phase 3's export ordering satisfiable: the Schema layer trio must read
    S1, S2, S3 in registration order."""
    order = qc.canonical_order()
    assert order[order.index("S2") + 1] == "S3", order[:6]


def test_s3_emits_pass_with_column_count_denominator_when_called_two_argument():
    """The two-argument call every existing caller in the suite already makes must keep
    working, with S3 emitting PASS and a Total Rows equal to the MLoS column count."""
    mlos = pd.DataFrame({"ward_code": ["a"], "set_population": ["1"], "state_code": ["ZA"]})
    checks, _ = qc.schema.run_schema_qc(mlos, pd.DataFrame())
    s3 = next(c for c in checks if c["Rule#"] == "S3")
    assert s3["Failing Rows"] == 0, s3
    assert s3["Total Rows"] == len(mlos.columns), s3
    assert "PASS" in s3["Status"], s3
    assert "no" in s3["Description"].lower() or "0" in s3["Description"], s3


def test_s3_reports_a_one_group_collision_naming_both_original_headers():
    """Sub-case per 02-CONTEXT.md's planner_clarification: neither `Ward-Code` nor
    `Ward Code` is already spelled exactly as the canonical `ward_code`, so both are
    genuinely absent after being left un-normalised, and S1 independently reports
    ward_code missing — this test only asserts S3's own reporting of the collision."""
    df = pd.DataFrame({"Ward-Code": ["a"], "Ward Code": ["b"], "state_code": ["ZA"]})
    _, _, collisions = normalize_columns(df)
    checks, detail = qc.schema.run_schema_qc(df, pd.DataFrame(), collisions=collisions)

    s3 = next(c for c in checks if c["Rule#"] == "S3")
    assert s3["Failing Rows"] == 1, s3
    assert "FAIL" in s3["Status"], s3
    assert "Ward-Code" in s3["Description"] and "Ward Code" in s3["Description"], s3
    assert not detail.empty, "a colliding group must produce at least one detail row"
    assert (detail["Rule#"] == "S3").any(), detail


def test_s3_already_canonical_member_of_a_colliding_pair_is_not_forced_missing():
    """The second sub-case 02-CONTEXT.md's planner_clarification describes: one member
    of the colliding pair (`ward_code`) is already spelled exactly as the canonical
    name, alongside `Ward Code`. Left un-normalised (per D-10's literal mechanism),
    `ward_code` stays present and resolvable — S1 must NOT report it missing — while S3
    still fails and names both headers, so the officer is told the header set is
    ambiguous even though the canonical column itself is not lost."""
    df = pd.DataFrame({
        "ward_code": ["a"], "Ward Code": ["b"], "state_code": ["ZA"],
        "state_name": ["Zamfara"], "lga_code": ["1"], "lga_name": ["x"],
        "ward_name": ["y"], "takeoffpoint": ["t"], "takeoffpoint_code": ["tc"],
        "settlement_name": ["s"], "primarysettlement_name": [""], "alternate_name": [""],
        "latitude": ["1"], "longitude": ["1"], "security_compromised": ["N"],
        "accessibility_status": ["Fully Accessible"], "reasons_for_inaccessibility": ["NA"],
        "habitational_status": ["Inhabited"], "set_population": ["1"], "set_target": ["1"],
        "number_of_household": ["1"], "noncompliant_household": ["0"], "team_code": ["T1"],
        "day_of_activity": ["1"], "urban": ["Y"], "rural": ["N"], "highrisk": ["N"],
        "slums": ["N"], "densely_populated": ["N"], "hard2reach": ["N"], "border": ["N"],
        "nomadic": ["N"], "scattered": ["N"], "riverine": ["N"], "fulani": ["N"],
        "timestamp": ["2024-01-01"], "source": ["IE"], "last_updated": ["2024-01-01"],
        "editor": ["jane.doe"], "validation_status": ["validated"], "master_id": ["M-1"],
        "mlos_id": ["ML-1"], "eha_guid": ["11111111-1111-1111-1111-111111111111"],
        "settlementarea_globalid": ["sga-1"],
    })
    renamed, _, collisions = normalize_columns(df)
    checks, _ = qc.schema.run_schema_qc(renamed, pd.DataFrame(), collisions=collisions)

    s1 = next(c for c in checks if c["Rule#"] == "S1")
    s3 = next(c for c in checks if c["Rule#"] == "S3")
    assert s1["Failing Rows"] == 0, (
        f"ward_code is still present and resolvable via its own literal spelling, so S1 "
        f"must not report it missing: {s1}"
    )
    assert "FAIL" in s3["Status"], "S3 must still flag the ambiguous header set"


def test_s3_three_way_collision_reports_a_failing_rows_count_of_three():
    df = pd.DataFrame({
        "Ward Code": ["a"], "Ward-Code": ["b"], "ward  code": ["c"], "state_code": ["ZA"],
    })
    _, _, collisions_1 = normalize_columns(df)
    df2 = pd.DataFrame({
        "Ward Code": ["a"], "Ward-Code": ["b"], "ward  code": ["c"],
        "Set Population": ["1"], "Set-Population": ["2"], "set  population": ["3"],
        "Team Code": ["t"], "Team-Code": ["u"], "team  code": ["v"],
        "state_code": ["ZA"],
    })
    _, _, collisions_3 = normalize_columns(df2)
    assert len(collisions_1) == 1
    assert len(collisions_3) == 3, collisions_3

    checks, _ = qc.schema.run_schema_qc(df2, pd.DataFrame(), collisions=collisions_3)
    s3 = next(c for c in checks if c["Rule#"] == "S3")
    assert s3["Failing Rows"] == 3, s3
    assert "FAIL" in s3["Status"], s3


def test_s3_does_not_affect_s1_or_s2_values_for_the_shared_fixture(mlos_df, takeoff_df):
    """The shared 43/4-column fixture's headers are already canonical, so it never
    collides — S1 and S2 must report exactly the same values as before S3 existed."""
    checks, _ = qc.schema.run_schema_qc(mlos_df, takeoff_df)
    s1 = next(c for c in checks if c["Rule#"] == "S1")
    s2 = next(c for c in checks if c["Rule#"] == "S2")
    s3 = next(c for c in checks if c["Rule#"] == "S3")

    assert s1["Failing Rows"] == 0 and s1["Total Rows"] == 43, s1
    assert s2["Failing Rows"] == 0 and s2["Total Rows"] == 4, s2
    assert s3["Failing Rows"] == 0 and "PASS" in s3["Status"], s3
