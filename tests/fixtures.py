"""Plain-function fixture builders shared by pytest and the golden-baseline capture script.

Deliberately plain functions rather than pytest fixtures: ``tests/baseline/capture_baseline.py``
imports these directly and must not depend on pytest being installed or on a pytest session
being active.

Column names are hard-coded here rather than imported from ``app.py`` — importing ``app.py``
would execute its Streamlit UI module body (``st.set_page_config``, ``st.markdown``, ...), which
fails outside a Streamlit runtime. This module stays import-safe in any plain Python process.

The MLoS fixture returned by ``build_mlos_fixture()`` carries 10 rows, each a Python ``str``
value in every cell (mirroring what ``load_csv``/``load_xlsx``/``load_sqlite`` produce with
``keep_default_na=False``), except row index 1's ``timestamp`` cell, which is a deliberate
``None`` — the one cell in the whole fixture that must trip the real null check
(``mlos[cols].isnull()``) rather than the empty-string coercion path that several other checks
use (``pd.to_numeric(..., errors="coerce")``, ``.str.strip().eq("")``). Every rule in every one
of the five QC layers has at least one row that fails it and at least one row that does not:

- Row 0 ("Alpha")    — the fully-passing anchor row, anchored on the real ward 81110.
- Row 1 ("Alpha")    — duplicate settlement_name+ward_code with row 0 (SQ1); None timestamp (rule 1).
- Row 2 ("Bravo")    — unmatched takeoffpoint/code/ward_code (rules 2, 3, 4); ward_code absent
                        from the boundary reference (B1); blank lat/lon (SQ2).
- Row 3 ("Charlie")  — invalid security_compromised (rule 5), accessibility_status (rule 6),
                        habitational_status (rule 8); lat/lon both zero (SQ2b).
- Row 4 ("Delta")    — Partially Accessible with a blank reason (rule 7); set_target exceeds
                        set_population (rule 9); number_of_household exceeds set_population (rule 10).
- Row 5 ("Echo")     — urban/rural/scattered each invalid (rule 11's three checks); all eight
                        profile flags invalid (rule 12's eight checks); bad editor (rule 13);
                        invalid eha_guid (rule 14).
- Row 6 ("Foxtrot")  — urban=rural=scattered=Y (rules 11a and 11b); state_name disagrees with
                        the boundary reference's state for ward 81110 (B3).
- Row 7 ("Golf")     — coordinates far outside ward 81110's bounding box (B2); first half of the
                        identical-coordinate pair for SQ3.
- Row 8 ("Hotel")     — identical coordinates to row 7 (SQ3); also outside the bbox (B2).
- Row 9 ("India")    — coordinates ~10 metres from rows 7/8 — inside SQ4's 30 metre threshold,
                        but not identical to either (so it does not itself pair for SQ3); also
                        outside the bbox (B2).
"""

from pathlib import Path

import pandas as pd

# Ward 81110 is real, present in both bundled reference CSVs: state Zamfara, LGA Shinkafi,
# ward "Shinkafi South", state_code ZA, lga_code 811. Its bounding box runs roughly
# longitude 6.488515 to 6.53619, latitude 13.045596 to 13.074176.
FIXTURE_WARD_CODE = "81110"

MLOS_REQUIRED_COLS = [
    "state_code", "state_name", "lga_code", "lga_name", "ward_name", "ward_code",
    "takeoffpoint", "takeoffpoint_code", "settlement_name", "primarysettlement_name",
    "alternate_name", "latitude", "longitude", "security_compromised",
    "accessibility_status", "reasons_for_inaccessibility", "habitational_status",
    "set_population", "set_target", "number_of_household", "noncompliant_household",
    "team_code", "day_of_activity", "urban", "rural", "highrisk", "slums",
    "densely_populated", "hard2reach", "border", "nomadic", "scattered",
    "riverine", "fulani", "timestamp", "source", "last_updated", "editor",
    "validation_status", "master_id", "mlos_id", "eha_guid", "settlementarea_globalid",
]

TAKEOFF_REQUIRED_COLS = ["name", "code", "wardcode", "globalid"]

_BASE_ROW = {
    "state_code": "ZA",
    "state_name": "Zamfara",
    "lga_code": "811",
    "lga_name": "Shinkafi",
    "ward_name": "Shinkafi South",
    "ward_code": FIXTURE_WARD_CODE,
    "takeoffpoint": "TP-A",
    "takeoffpoint_code": "TPC-A",
    "settlement_name": "Alpha",
    "primarysettlement_name": "",
    "alternate_name": "",
    "latitude": "13.06",
    "longitude": "6.51",
    "security_compromised": "N",
    "accessibility_status": "Fully Accessible",
    "reasons_for_inaccessibility": "NA",
    "habitational_status": "Inhabited",
    "set_population": "100",
    "set_target": "50",
    "number_of_household": "40",
    "noncompliant_household": "0",
    "team_code": "T1",
    "day_of_activity": "1",
    "urban": "Y",
    "rural": "N",
    "highrisk": "N",
    "slums": "N",
    "densely_populated": "N",
    "hard2reach": "N",
    "border": "N",
    "nomadic": "N",
    "scattered": "N",
    "riverine": "N",
    "fulani": "N",
    "timestamp": "2024-01-01T00:00:00",
    "source": "IE",
    "last_updated": "2024-01-01T00:00:00",
    "editor": "jane.doe",
    "validation_status": "validated",
    "master_id": "M-0000",
    "mlos_id": "ML-0000",
    "eha_guid": "11111111-1111-1111-1111-111111111111",
    "settlementarea_globalid": "sga-0000",
}


def _row(overrides: dict) -> dict:
    row = dict(_BASE_ROW)
    row.update(overrides)
    return row


def build_mlos_fixture() -> pd.DataFrame:
    """Return a 10-row MLoS DataFrame carrying all 43 required columns as Python strings.

    Every check in every one of the five QC layers has at least one failing row and at least
    one passing row (see the module docstring for the row-by-row map). Row 1's ``timestamp``
    is the sole intentional exception to "every cell is a string" — a real ``None`` is what
    the app's rule-1 null check (``.isnull()``) actually catches; an empty string would not.
    """
    rows = [
        _row({
            "settlement_name": "Alpha",
            "master_id": "M-0001", "mlos_id": "ML-0001",
            "eha_guid": "11111111-1111-1111-1111-111111111111",
            "settlementarea_globalid": "sga-0001",
        }),
        _row({
            "settlement_name": "Alpha",  # duplicate name+ward_code with row 0 -> SQ1
            "timestamp": None,           # deliberate real null -> rule 1
            "master_id": "M-0002", "mlos_id": "ML-0002",
            "eha_guid": "22222222-2222-2222-2222-222222222222",
            "settlementarea_globalid": "sga-0002",
        }),
        _row({
            "settlement_name": "Bravo",
            "ward_code": "00000",             # absent from boundary reference -> B1
            "takeoffpoint": "Ghost-TP",        # unmatched -> rule 2
            "takeoffpoint_code": "GHOST-CODE",  # unmatched -> rule 3 (ward mismatch above -> rule 4)
            "latitude": "", "longitude": "",  # blank -> SQ2
            "master_id": "M-0003", "mlos_id": "ML-0003",
            "eha_guid": "33333333-3333-3333-3333-333333333333",
            "settlementarea_globalid": "sga-0003",
        }),
        _row({
            "settlement_name": "Charlie",
            "security_compromised": "Unknown",     # invalid -> rule 5
            "accessibility_status": "Sometimes",    # invalid -> rule 6
            "habitational_status": "Deserted",      # invalid -> rule 8
            "latitude": "0", "longitude": "0",      # both zero -> SQ2b
            "master_id": "M-0004", "mlos_id": "ML-0004",
            "eha_guid": "44444444-4444-4444-4444-444444444444",
            "settlementarea_globalid": "sga-0004",
        }),
        _row({
            "settlement_name": "Delta",
            "accessibility_status": "Partially Accessible",
            "reasons_for_inaccessibility": "",   # blank reason -> rule 7
            "set_population": "100",
            "set_target": "200",                 # exceeds set_population -> rule 9
            "number_of_household": "150",        # exceeds set_population -> rule 10
            "master_id": "M-0005", "mlos_id": "ML-0005",
            "eha_guid": "55555555-5555-5555-5555-555555555555",
            "settlementarea_globalid": "sga-0005",
        }),
        _row({
            "settlement_name": "Echo",
            "urban": "Maybe", "rural": "Perhaps", "scattered": "Unsure",  # rule 11's 3 checks
            "highrisk": "Bad", "slums": "Bad", "densely_populated": "Bad",
            "hard2reach": "Bad", "border": "Bad", "nomadic": "Bad",
            "riverine": "Bad", "fulani": "Bad",                          # rule 12's 8 checks
            "editor": "JohnSmith",                                        # invalid -> rule 13
            "eha_guid": "not-a-valid-uuid",                                # invalid -> rule 14
            "master_id": "M-0006", "mlos_id": "ML-0006",
            "settlementarea_globalid": "sga-0006",
        }),
        _row({
            "settlement_name": "Foxtrot",
            "urban": "Y", "rural": "Y", "scattered": "Y",  # 11a and 11b
            "state_name": "Kano",  # disagrees with ward 81110's real state -> B3
            "master_id": "M-0007", "mlos_id": "ML-0007",
            "eha_guid": "77777777-7777-7777-7777-777777777777",
            "settlementarea_globalid": "sga-0007",
        }),
        _row({
            "settlement_name": "Golf",
            "latitude": "1.0", "longitude": "1.0",  # far outside ward 81110's bbox -> B2
            "master_id": "M-0008", "mlos_id": "ML-0008",
            "eha_guid": "88888888-8888-8888-8888-888888888888",
            "settlementarea_globalid": "sga-0008",
        }),
        _row({
            "settlement_name": "Hotel",
            "latitude": "1.0", "longitude": "1.0",  # identical to row 7 -> SQ3; also -> B2
            "master_id": "M-0009", "mlos_id": "ML-0009",
            "eha_guid": "99999999-9999-9999-9999-999999999999",
            "settlementarea_globalid": "sga-0009",
        }),
        _row({
            "settlement_name": "India",
            "latitude": "1.00009", "longitude": "1.0",  # ~10m from rows 7/8 -> SQ4; also -> B2
            "master_id": "M-0010", "mlos_id": "ML-0010",
            "eha_guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "settlementarea_globalid": "sga-0010",
        }),
    ]
    df = pd.DataFrame(rows, columns=MLOS_REQUIRED_COLS)
    return df


def build_takeoff_fixture() -> pd.DataFrame:
    """Return a 3-row Takeoffpoint DataFrame: two entries matching the MLoS fixture's default
    takeoffpoint, and one orphan entry that matches no MLoS row on name, code or ward_code and
    also carries an invalid globalid — failing TP2, TP3, TP4 and TP5 all from a single row."""
    rows = [
        {"name": "TP-A", "code": "TPC-A", "wardcode": FIXTURE_WARD_CODE,
         "globalid": "c1111111-1111-1111-1111-111111111111"},
        {"name": "Orphan-TP", "code": "ORPHAN-CODE", "wardcode": "99999",
         "globalid": "not-a-uuid"},
        {"name": "TP-A", "code": "TPC-A", "wardcode": FIXTURE_WARD_CODE,
         "globalid": "c2222222-2222-2222-2222-222222222222"},
    ]
    return pd.DataFrame(rows, columns=TAKEOFF_REQUIRED_COLS)


def load_boundary_fixtures() -> "tuple[pd.DataFrame, pd.DataFrame]":
    """Load the two bundled boundary reference CSVs exactly as ``load_boundary_refs`` does at
    ``app.py:371`` — ``dtype=str``, ``keep_default_na=False``, with the four bbox coordinate
    columns coerced numeric. Paths resolve relative to this file's own location, walking up to
    the repository root, never from the process working directory."""
    repo_root = Path(__file__).resolve().parent.parent
    ref_path = repo_root / "ward_boundary_ref.csv"
    bbox_path = repo_root / "ward_boundary_bbox.csv"

    ref_df = pd.read_csv(ref_path, dtype=str, keep_default_na=False)
    bbox_df = pd.read_csv(bbox_path, dtype=str, keep_default_na=False)
    for col in ["min_lon", "min_lat", "max_lon", "max_lat"]:
        if col in bbox_df.columns:
            bbox_df[col] = pd.to_numeric(bbox_df[col], errors="coerce")
    return ref_df, bbox_df
