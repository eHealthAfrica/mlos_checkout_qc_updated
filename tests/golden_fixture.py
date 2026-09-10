"""Three-format golden fixture (ENGINE-06): byte builders for .sqlite, .csv and .xlsx encodings
of one shared MLoS row list, round-tripped through the real ``qc.loaders`` functions rather than
synthesised as frames directly — a fixture that skipped the real loaders could not catch
INTEG-01, since the whole defect lives in what each loader produces for an empty cell.

Deliberately plain functions, no pytest import — importable from any plain Python process,
matching ``tests/fixtures.py``'s own contract.

At least one row of the shared MLoS row list carries the module-level ``BLANK`` marker in a
column that is a member of ``qc.mlos``'s ``_NOT_NULL_COLS``. Do not "clean this up" by making
every row fully populated: without a genuinely blank required cell, this fixture cannot reproduce
INTEG-01 (a CSV/XLSX blank arrives as "" while a .sqlite blank arrives as NULL/NaN) at all, and
the parity test built on top of it would pass while proving nothing.

The sqlite writer's Takeoffpoint view/table exists to satisfy ``qc.loaders.load_submission``'s
unconditional two-view load (it always calls ``load_view`` for both MLOS_VIEW and TAKEOFF_VIEW)
and to prove ``load_view`` resolves columns through PRAGMA table_info against a named view, not a
base table — a view must exist under both names or the load raises. It deliberately carries no
column named "name", "code" or "wardcode" (qc.domain.TAKEOFF_REQUIRED_COLS), so
``qc.mlos.run_mlos_qc``'s R2/R3/R4 cross-table guards (``"name" in takeoff.columns``, etc.) stay
false for every format. CSV structurally can never carry a second, embedded Takeoffpoint table at
all (``qc.loaders.load_csv`` always returns an empty takeoff frame) — giving the sqlite/xlsx
Takeoffpoint table real R2/R3/R4-triggering columns would make those checks appear for two
formats and not the third, breaking the very "identical check summary across formats" property
this fixture exists to prove. R2/R3/R4's own cross-table-match correctness is Plan 02's INTEG-02
scope, not this plan's.
"""

import os
import sqlite3
import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd

from fixtures import _BASE_ROW, _row, MLOS_REQUIRED_COLS  # noqa: F401 (MLOS_REQUIRED_COLS re-exported)
from qc.loaders import MLOS_VIEW, TAKEOFF_VIEW


class _BlankMarker:
    """Singleton sentinel standing in for 'this cell is logically blank', translated to each
    format's own blank representation by that format's writer: Python None for .sqlite (a real
    SQL NULL), the empty string for .csv and .xlsx (the blank convention keep_default_na=False
    itself contracts for)."""

    def __repr__(self):
        return "<BLANK>"


BLANK = _BlankMarker()

# INTEG-03/F7 non-canonical header spellings, for tests/test_normalisation_at_load.py's F7
# contrast test. Exactly three required MLoS columns, deliberately misspelled: 'takeoffpoint'
# (guards R2/2.missing), 'ward_code' (guards R4/4.missing, B0-B3), and 'set_population' (guards
# R9/R10). These spellings ARE the point of the test and must never be "corrected" — the whole
# purpose is to prove qc.columns.normalize_columns resolves them back to canonical form and that
# the rules which silently skipped them (because their column-presence guards test the raw frame)
# now fire. Applied only via the `header_map` parameter below — the canonical builders and
# writers stay byte-for-byte unchanged for every existing caller that omits it.
NONCANONICAL_HEADER_MAP = {
    "takeoffpoint": "Takeoffpoint",
    "ward_code": "Ward Code",
    "set_population": "SET_POPULATION",
}


class FakeUploadedFile(BytesIO):
    """Minimal stand-in for Streamlit's UploadedFile. Streamlit's real UploadedFile is itself an
    io.BytesIO subclass carrying a .name and a .size attribute (verified by reading the installed
    streamlit package source) — this is not a divergent shim, just the same surface without the
    Streamlit runtime behind it."""

    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def build_shared_mlos_rows() -> "list[dict]":
    """Two rows sharing tests/fixtures.py's _BASE_ROW/_row shape: one fully-populated anchor row,
    and one row carrying BLANK in `timestamp` — a `_NOT_NULL_COLS` member — so Rule 1 has
    something format-dependent to disagree about before the fix, and something to agree about
    identically after it."""
    return [
        _row({
            "settlement_name": "GoldenAlpha",
            "master_id": "G-0001", "mlos_id": "GML-0001",
            "eha_guid": "b1111111-1111-1111-1111-111111111111",
            "settlementarea_globalid": "gsga-0001",
        }),
        _row({
            "settlement_name": "GoldenBravo",
            "timestamp": BLANK,
            "master_id": "G-0002", "mlos_id": "GML-0002",
            "eha_guid": "b2222222-2222-2222-2222-222222222222",
            "settlementarea_globalid": "gsga-0002",
        }),
    ]


def _translate(value, blank_value):
    return blank_value if value is BLANK else value


def _rows_to_dataframe(rows: "list[dict]", cols: "list[str]", blank_value) -> pd.DataFrame:
    translated = [{c: _translate(row[c], blank_value) for c in cols} for row in rows]
    return pd.DataFrame(translated, columns=cols)


def _apply_header_map(df: pd.DataFrame, header_map: "dict[str, str] | None") -> pd.DataFrame:
    """Rename ``df``'s columns per ``header_map`` (canonical -> non-canonical spelling), or
    return ``df`` unchanged when ``header_map`` is falsy. Isolated here so every writer applies
    the same rename in the same way."""
    return df.rename(columns=header_map) if header_map else df


def build_sqlite_bytes(rows: "list[dict]", cols: "list[str]", header_map: "dict[str, str] | None" = None) -> bytes:
    """Write `rows` into a real SQLite file (base tables plus the two named views
    qc.loaders.load_view resolves against) and return its bytes. The blank marker becomes a
    genuine Python None in the executemany parameters, so SQLite stores a real SQL NULL — not an
    empty-string cell — for the blank cell.

    ``header_map``, if given, renames the *physical column names written to the table* (and
    therefore the view) from ``cols``' canonical spelling to a non-canonical one — values are
    still looked up from each row dict by the canonical key in ``cols``, only the on-disk header
    text changes. Defaults to ``None``, leaving every existing caller's bytes unchanged."""
    write_cols = [header_map.get(c, c) if header_map else c for c in cols]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    tmp.close()
    try:
        conn = sqlite3.connect(tmp.name)
        try:
            col_defs = ", ".join(f'"{w}" TEXT' for w in write_cols)
            conn.execute(f'CREATE TABLE mlos_base ({col_defs})')
            placeholders = ", ".join("?" for _ in cols)
            params = [
                tuple(_translate(row[c], None) for c in cols)
                for row in rows
            ]
            conn.executemany(f'INSERT INTO mlos_base VALUES ({placeholders})', params)

            # No TAKEOFF_REQUIRED_COLS name here — see module docstring.
            conn.execute('CREATE TABLE takeoff_base ("_placeholder" TEXT)')

            conn.execute(f'CREATE VIEW "{MLOS_VIEW}" AS SELECT * FROM mlos_base')
            conn.execute(f'CREATE VIEW "{TAKEOFF_VIEW}" AS SELECT * FROM takeoff_base')
            conn.commit()
        finally:
            conn.close()
        return Path(tmp.name).read_bytes()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def build_csv_bytes(rows: "list[dict]", cols: "list[str]", header_map: "dict[str, str] | None" = None) -> bytes:
    """CSV encoding of `rows`: the blank marker becomes an empty-string cell, the blank
    convention `keep_default_na=False` contracts for on every loader.

    ``header_map``, if given, renames the written header row from ``cols``' canonical spelling to
    a non-canonical one after the frame is built — values are unaffected. Defaults to ``None``,
    leaving every existing caller's bytes unchanged."""
    df = _rows_to_dataframe(rows, cols, blank_value="")
    df = _apply_header_map(df, header_map)
    return df.to_csv(index=False).encode("utf-8")


def build_xlsx_bytes(rows: "list[dict]", cols: "list[str]", header_map: "dict[str, str] | None" = None) -> bytes:
    """XLSX encoding of `rows`: two sheets, named from qc.loaders' own alias sets ("mlos",
    "takeoffpoint") so load_xlsx's alias resolution finds them. The blank marker becomes an
    empty-string cell, same as the CSV writer.

    ``header_map``, if given, renames the MLoS sheet's written header row from ``cols``'
    canonical spelling to a non-canonical one after the frame is built (the inert Takeoffpoint
    sheet is untouched — it carries no canonical name to begin with). Defaults to ``None``,
    leaving every existing caller's bytes unchanged."""
    mlos_df = _rows_to_dataframe(rows, cols, blank_value="")
    mlos_df = _apply_header_map(mlos_df, header_map)
    takeoff_df = pd.DataFrame({"_placeholder": []})  # no TAKEOFF_REQUIRED_COLS name — see module docstring
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        mlos_df.to_excel(writer, index=False, sheet_name="mlos")
        takeoff_df.to_excel(writer, index=False, sheet_name="takeoffpoint")
    return out.getvalue()


def build_sqlite_bytes_noncanonical(rows: "list[dict]", cols: "list[str]") -> bytes:
    """build_sqlite_bytes with NONCANONICAL_HEADER_MAP applied — the per-format writer
    tests/test_normalisation_at_load.py's three-format round-trip test uses."""
    return build_sqlite_bytes(rows, cols, header_map=NONCANONICAL_HEADER_MAP)


def build_csv_bytes_noncanonical(rows: "list[dict]", cols: "list[str]") -> bytes:
    """build_csv_bytes with NONCANONICAL_HEADER_MAP applied — see build_sqlite_bytes_noncanonical."""
    return build_csv_bytes(rows, cols, header_map=NONCANONICAL_HEADER_MAP)


def build_xlsx_bytes_noncanonical(rows: "list[dict]", cols: "list[str]") -> bytes:
    """build_xlsx_bytes with NONCANONICAL_HEADER_MAP applied — see build_sqlite_bytes_noncanonical."""
    return build_xlsx_bytes(rows, cols, header_map=NONCANONICAL_HEADER_MAP)
