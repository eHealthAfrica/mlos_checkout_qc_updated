"""Pure, Streamlit-free file parsing, relocated out of app.py.

Phase 1's D-08 parked this extraction for this phase, on the grounds that separating pure
parsing from the session-state caching wrapper is real work, and that Phase 2 changes loader
behaviour anyway (INTEG-01, INTEG-03). Everything below is pure: it takes a file-like object and
returns DataFrames, with no reference to ``st.session_state`` or any other Streamlit surface —
``tests/test_no_streamlit_in_qc.py`` enforces that boundary for every module under ``qc/``. The
caching wrapper (``get_uploaded_data`` in app.py) stays in app.py, because caching is a
session-scoped UI concern, not a parsing concern; it delegates all parsing here.

``keep_default_na=False`` and ``dtype=str`` are load-bearing on every read below and stay: they
are what lets the domain value "NA" (Nasarawa's state_code, and a valid flag-column value)
survive as a string instead of being silently coerced to NaN by pandas' default NA-sniffing.
INTEG-01 (a CSV/XLSX blank arriving as "" rather than NaN) is a consequence of that correct
choice to be handled by ``qc.predicates.vec_is_absent``, not a reason to reverse it.
"""

import os
import sqlite3
import tempfile

import pandas as pd

MLOS_VIEW    = "master_list_settlement_update_view"
TAKEOFF_VIEW = "mlos_takeoffpoint_view"


def load_sqlite(uploaded_file):
    """Write an uploaded .sqlite/.db file's bytes to a temp file and open a connection to it.

    Returns (connection, temp_path); the caller is responsible for closing the connection and
    unlinking the temp file — see load_submission's try/finally below.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    tmp.write(uploaded_file.read())
    tmp.close()
    return sqlite3.connect(tmp.name), tmp.name


def load_view(conn, view_name):
    """Read a named SQLite view into a DataFrame, resolving its columns through PRAGMA
    table_info rather than a bare SELECT * — this drops BLOB/POINT/GEOMETRY-typed columns, which
    pandas cannot represent usefully, and is why a base table alone is not enough for a caller
    that only creates the base table and forgets the view: PRAGMA table_info here is queried
    against ``view_name`` specifically.
    """
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{view_name}")')
    cols_info = cur.fetchall()
    safe = [c[1] for c in cols_info
            if c[2] is None or not any(k in str(c[2]).upper()
                                       for k in ("BLOB", "POINT", "GEOMETRY"))]
    col_str = ", ".join(f'"{c}"' for c in safe)
    return pd.read_sql_query(f'SELECT {col_str} FROM "{view_name}"', conn)


def load_csv(uploaded_file):
    """Load a CSV file as the MLoS table. Returns (mlos_df, empty takeoff_df)."""
    uploaded_file.seek(0)
    # keep_default_na=False prevents pandas from silently converting the valid
    # domain value "NA" (used in flag columns like highrisk, slums, etc.) to NaN.
    # Only truly empty cells remain as NaN.
    mlos_df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
    takeoff_df = pd.DataFrame()
    return mlos_df, takeoff_df


def load_xlsx(uploaded_file):
    """Load an XLSX/XLS file. Expects two sheets: mlos (sheet 1) and takeoffpoint (sheet 2).
    Sheet names may match the view names or simplified aliases."""
    uploaded_file.seek(0)
    xl = pd.ExcelFile(uploaded_file)
    sheet_names = xl.sheet_names

    # Resolve mlos sheet — prefer view name, then 'mlos', then first sheet
    mlos_aliases = {MLOS_VIEW.lower(), "mlos", "master_list", "settlements"}
    mlos_sheet = next(
        (s for s in sheet_names if s.lower() in mlos_aliases),
        sheet_names[0]
    )

    # Resolve takeoff sheet — prefer view name, then 'takeoffpoint', then second sheet
    takeoff_aliases = {TAKEOFF_VIEW.lower(), "takeoffpoint", "takeoff", "takeoff_point"}
    takeoff_sheet = next(
        (s for s in sheet_names if s.lower() in takeoff_aliases and s != mlos_sheet),
        sheet_names[1] if len(sheet_names) > 1 else None
    )

    # keep_default_na=False prevents pandas from converting the valid domain value
    # "NA" (used in flag columns) to NaN. Only truly empty cells remain as NaN.
    mlos_df    = xl.parse(mlos_sheet,   dtype=str, keep_default_na=False)
    takeoff_df = xl.parse(takeoff_sheet, dtype=str, keep_default_na=False) if takeoff_sheet else pd.DataFrame()
    return mlos_df, takeoff_df


def load_takeoffpoint_file(tp_file) -> pd.DataFrame:
    """Parse a separately uploaded takeoffpoint CSV or Excel file."""
    ext = tp_file.name.rsplit(".", 1)[-1].lower()
    tp_file.seek(0)
    if ext == "csv":
        return pd.read_csv(tp_file, dtype=str, keep_default_na=False)
    xl = pd.ExcelFile(tp_file)
    tp_aliases = {TAKEOFF_VIEW.lower(), "takeoffpoint", "takeoff", "takeoff_point"}
    tp_sheet = next(
        (s for s in xl.sheet_names if s.lower() in tp_aliases),
        xl.sheet_names[0],
    )
    return xl.parse(tp_sheet, dtype=str, keep_default_na=False)


def load_submission(file_like, filename, on_progress=None):
    """Pure extension-dispatch parsing, extracted out of app.py's get_uploaded_data — everything
    that function did except the st.session_state cache read/write, which stays in app.py.

    ``filename`` is passed explicitly rather than read off ``file_like.name`` so this function
    depends only on the file-like protocol (read/seek), never on a Streamlit UploadedFile
    attribute. ``on_progress``, if given, is called with one integer at the same four points and
    with the same values app.py's caching wrapper pushed directly to its progress bar before this
    extraction — 10, 35, 65, 90 — so wiring app.py to forward a callable here (rather than a
    progress object) leaves the on-screen progress bar's behaviour unchanged. Returns
    (mlos_df, takeoff_df).
    """
    if on_progress is not None:
        on_progress(10)

    ext = filename.rsplit(".", 1)[-1].lower()

    if ext in ("xlsx", "xls"):
        if on_progress is not None:
            on_progress(35)
        mlos_df, takeoff_df = load_xlsx(file_like)
        if on_progress is not None:
            on_progress(90)
    elif ext == "csv":
        if on_progress is not None:
            on_progress(35)
        mlos_df, takeoff_df = load_csv(file_like)
        if on_progress is not None:
            on_progress(90)
    else:
        conn, tmp_path = load_sqlite(file_like)
        try:
            if on_progress is not None:
                on_progress(35)
            mlos_df    = load_view(conn, MLOS_VIEW)
            if on_progress is not None:
                on_progress(65)
            takeoff_df = load_view(conn, TAKEOFF_VIEW)
            if on_progress is not None:
                on_progress(90)
        finally:
            conn.close()
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return mlos_df, takeoff_df
