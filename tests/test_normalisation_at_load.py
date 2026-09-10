"""Standing test for INTEG-03/F7 (plan 04, phase 02): proves that a header spelled differently
from its canonical form (D-08/D-09/D-20) no longer satisfies the schema check while silently
skipping every rule that needs it, once ``qc.columns.normalize_columns`` runs once at load.

Everything here calls ``qc.columns.normalize_columns`` directly rather than importing
``app.py`` — ``app.py`` cannot be imported outside a Streamlit runtime (its module body calls
``st.set_page_config``), so this file proves the same behaviour the production caching wrapper
(``get_uploaded_data`` in ``app.py``) delegates to, following the AST/behaviour-composition idiom
Phase 1 and plan 01/03 already established for verifying ``app.py`` edits.
"""

import pandas as pd

import golden_fixture as gf
from fixtures import build_takeoff_fixture
from qc.columns import normalize_columns
from qc.loaders import load_submission
from qc.mlos import run_mlos_qc
from qc.schema import run_schema_qc

_CROSS_TABLE_IDS = {"2", "2.missing", "4", "4.missing"}


def test_f7_contrast_takeoffpoint_ward_code_headers_resolve_after_normalization():
    """F7 / INTEG-03, in two labelled halves.

    BEFORE ``qc.columns.normalize_columns`` runs: a frame whose headers are the canonical 43
    except that ``takeoffpoint`` is spelled ``Takeoffpoint`` and ``ward_code`` is spelled
    ``Ward Code`` (see ``golden_fixture.NONCANONICAL_HEADER_MAP``) makes
    ``qc.mlos.run_mlos_qc``'s own column-presence guards (``if "takeoffpoint" in mlos.columns``,
    ``if "ward_code" in mlos.columns``) fail silently — none of 2 / 2.missing / 4 / 4.missing
    emit at all, because those guards test the raw frame rather than a normalised view. This
    reproduces defect F7 exactly; this half deliberately asserts the still-broken behaviour so a
    future reader can see what changed.

    AFTER ``qc.columns.normalize_columns`` runs: the two misspelled headers resolve to their
    canonical form, the guards pass, and all four identifiers emit.

    (Note: unlike the pre-plan-03 codebase, ``S1`` already correctly reports these headers as
    missing *before* normalisation too — plan 03 closed the schema layer's half of F7 by making
    S1 compare raw columns instead of a defensively lower-cased projection. The half of F7 this
    plan closes is that the *rules* silently skip the same misspelled headers instead of ever
    seeing them; that is what this test proves.)
    """
    rows = gf.build_shared_mlos_rows()
    cols = gf.MLOS_REQUIRED_COLS
    payload = gf.build_xlsx_bytes_noncanonical(rows, cols)
    uploaded = gf.FakeUploadedFile(payload, "noncanonical.xlsx")
    mlos_raw, _inert_takeoff = load_submission(uploaded, "noncanonical.xlsx")

    # A real Takeoffpoint table (not golden_fixture's deliberately inert default — see its
    # module docstring) so "2" and "4", which additionally require "name"/"wardcode" present on
    # the Takeoffpoint side, are actually capable of emitting once the MLoS-side guard passes.
    # Its takeoffpoint/code/wardcode values already match golden_fixture's shared row list (both
    # derive from tests/fixtures.py's shared _BASE_ROW), so after normalisation both checks read
    # PASS rather than FAIL — this test cares that the identifier emits, not its verdict.
    takeoff_df = build_takeoff_fixture()

    # ---- BEFORE: defect F7 is live ----
    schema_checks_before, _ = run_schema_qc(mlos_raw, pd.DataFrame())
    s1_before = next(c for c in schema_checks_before if c["Rule#"] == "S1")
    assert s1_before["Failing Rows"] > 0, (
        "S1 should already report the misspelled headers as missing before normalisation "
        "(plan 03's raw-column fix) — this is not the part of F7 this plan closes"
    )

    mlos_checks_before, _ = run_mlos_qc(mlos_raw, takeoff_df)
    ids_before = {c["Rule#"] for c in mlos_checks_before}
    assert not (ids_before & _CROSS_TABLE_IDS), (
        f"defect F7 should reproduce before normalisation — none of {_CROSS_TABLE_IDS} should "
        f"emit while 'takeoffpoint'/'ward_code' are misspelled, but found "
        f"{ids_before & _CROSS_TABLE_IDS}"
    )

    # ---- AFTER: qc.columns.normalize_columns resolves the headers ----
    mlos_norm, rename_map, collisions = normalize_columns(mlos_raw)
    assert not collisions, f"the two misspelled headers must not collide with anything: {collisions}"
    assert rename_map, "normalize_columns must report at least the two renamed headers"
    assert set(rename_map.values()) >= {"takeoffpoint", "ward_code"}, rename_map

    schema_checks_after, _ = run_schema_qc(mlos_norm, pd.DataFrame())
    s1_after = next(c for c in schema_checks_after if c["Rule#"] == "S1")
    assert s1_after["Failing Rows"] == 0, (
        f"S1 must read clean once the headers are normalised, got {s1_after}"
    )

    mlos_checks_after, _ = run_mlos_qc(mlos_norm, takeoff_df)
    ids_after = {c["Rule#"] for c in mlos_checks_after}
    still_missing = _CROSS_TABLE_IDS - ids_after
    assert not still_missing, (
        f"all of {_CROSS_TABLE_IDS} must emit after normalisation, but {still_missing} did not "
        f"(ids emitted: {sorted(ids_after)})"
    )


def test_three_formats_produce_identical_column_sets_and_rename_maps_for_noncanonical_headers():
    """ENGINE-06 extended to INTEG-03: the same non-canonical header spellings, round-tripped
    through the real ``qc.loaders.load_submission`` for ``.sqlite``, ``.csv`` and ``.xlsx``, then
    through ``qc.columns.normalize_columns``, must all yield the same column set (containing all
    43 canonical MLoS names) and an identical, non-empty rename map."""
    rows = gf.build_shared_mlos_rows()
    cols = gf.MLOS_REQUIRED_COLS
    writers = {
        "sqlite": ("golden.sqlite", gf.build_sqlite_bytes_noncanonical),
        "csv": ("golden.csv", gf.build_csv_bytes_noncanonical),
        "xlsx": ("golden.xlsx", gf.build_xlsx_bytes_noncanonical),
    }

    column_sets = {}
    rename_maps = {}
    for fmt, (filename, builder) in writers.items():
        payload = builder(rows, cols)
        uploaded = gf.FakeUploadedFile(payload, filename)
        mlos_raw, _takeoff = load_submission(uploaded, filename)
        mlos_norm, rename_map, collisions = normalize_columns(mlos_raw)
        assert not collisions, f"{fmt}: unexpected collision {collisions}"
        column_sets[fmt] = frozenset(mlos_norm.columns)
        rename_maps[fmt] = rename_map

    assert len(set(column_sets.values())) == 1, (
        f"column sets diverged across formats: {column_sets}"
    )
    assert set(cols) <= column_sets["sqlite"], (
        "the normalised column set must contain all 43 canonical MLoS names"
    )

    assert rename_maps["sqlite"], "the rename map must be non-empty for the noncanonical fixture"
    assert rename_maps["sqlite"] == rename_maps["csv"] == rename_maps["xlsx"], (
        f"rename maps diverged across formats: {rename_maps}"
    )


def test_column_collision_propagates_to_s3_failure():
    """A frame carrying two headers that normalise to the same name yields a non-empty
    collision list from ``normalize_columns``, and passing that list to ``run_schema_qc``'s
    ``collisions`` argument makes ``S3`` fail — the load-to-check wiring INTEG-03/D-10
    depends on."""
    rows = gf.build_shared_mlos_rows()
    cols = gf.MLOS_REQUIRED_COLS
    payload = gf.build_csv_bytes(rows, cols)
    uploaded = gf.FakeUploadedFile(payload, "golden.csv")
    mlos_df, _takeoff = load_submission(uploaded, "golden.csv")

    # 'ward-code' and 'Ward Code' both normalise to 'ward_code' — a genuine collision, distinct
    # from the F7 test's single (non-colliding) rename above.
    colliding = mlos_df.rename(columns={"ward_code": "Ward Code", "lga_code": "ward-code"})

    mlos_norm, rename_map, collisions = normalize_columns(colliding)
    assert collisions, "normalize_columns must report the ward_code/lga_code collision"

    schema_checks, _ = run_schema_qc(mlos_norm, pd.DataFrame(), collisions=collisions)
    s3 = next(c for c in schema_checks if c["Rule#"] == "S3")
    assert "FAIL" in s3["Status"], f"S3 must fail on a genuine collision, got {s3}"
    assert s3["Failing Rows"] == len(collisions)


def test_noncanonical_fixture_genuinely_differs_from_canonical_in_at_least_three_headers():
    """Defensive floor: if ``golden_fixture.NONCANONICAL_HEADER_MAP``'s spellings ever converged
    with the canonical ones, every test above would pass while proving nothing. Assert the
    contrast is real, directly off the written bytes rather than through any loader."""
    rows = gf.build_shared_mlos_rows()
    cols = gf.MLOS_REQUIRED_COLS

    canonical_payload = gf.build_csv_bytes(rows, cols)
    noncanonical_payload = gf.build_csv_bytes_noncanonical(rows, cols)

    canonical_headers = canonical_payload.decode("utf-8").splitlines()[0].split(",")
    noncanonical_headers = noncanonical_payload.decode("utf-8").splitlines()[0].split(",")

    assert len(canonical_headers) == len(noncanonical_headers)
    differing = sum(1 for a, b in zip(canonical_headers, noncanonical_headers) if a != b)
    assert differing >= 3, (
        f"expected at least 3 differing header spellings, found {differing}: "
        f"canonical={canonical_headers} noncanonical={noncanonical_headers}"
    )
