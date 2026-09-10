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


def build_sqlite_bytes(rows: "list[dict]", cols: "list[str]") -> bytes:
    """Write `rows` into a real SQLite file (base tables plus the two named views
    qc.loaders.load_view resolves against) and return its bytes. The blank marker becomes a
    genuine Python None in the executemany parameters, so SQLite stores a real SQL NULL — not an
    empty-string cell — for the blank cell."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    tmp.close()
    try:
        conn = sqlite3.connect(tmp.name)
        try:
            col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
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


def build_csv_bytes(rows: "list[dict]", cols: "list[str]") -> bytes:
    """CSV encoding of `rows`: the blank marker becomes an empty-string cell, the blank
    convention `keep_default_na=False` contracts for on every loader."""
    df = _rows_to_dataframe(rows, cols, blank_value="")
    return df.to_csv(index=False).encode("utf-8")


def build_xlsx_bytes(rows: "list[dict]", cols: "list[str]") -> bytes:
    """XLSX encoding of `rows`: two sheets, named from qc.loaders' own alias sets ("mlos",
    "takeoffpoint") so load_xlsx's alias resolution finds them. The blank marker becomes an
    empty-string cell, same as the CSV writer."""
    mlos_df = _rows_to_dataframe(rows, cols, blank_value="")
    takeoff_df = pd.DataFrame({"_placeholder": []})  # no TAKEOFF_REQUIRED_COLS name — see module docstring
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        mlos_df.to_excel(writer, index=False, sheet_name="mlos")
        takeoff_df.to_excel(writer, index=False, sheet_name="takeoffpoint")
    return out.getvalue()
