"""Proves qc.columns.normalize_name/normalize_columns implement D-08/D-09/D-10 exactly:
purely typographic renaming, with collision detection running against the proposed
rename map before any rename is applied, so a duplicate column label is never produced.

Constructs frames inline with ``pandas.DataFrame`` and explicit header names — there is
no existing test that builds a bare non-fixture frame, and a colliding header set cannot
be expressed through ``tests/fixtures.py``'s row-dict shape at all (02-PATTERNS.md's "No
Analog Found" entry for this file).

S3 assertions land in this same file in a later commit (task 2) — this commit covers
only the transform and the collision-detection ordering.
"""

import pandas as pd

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
