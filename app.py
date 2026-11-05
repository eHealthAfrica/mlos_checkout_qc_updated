import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import shapely
import tempfile
import os
import re
import difflib
import zlib
import uuid
import hashlib
import hmac
import time
import altair as alt
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape
from datetime import datetime, timedelta, timezone
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MLOS Checkout QC",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── WHITE THEME CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

  /* Force white background */
  .stApp { background-color: #ffffff !important; color: #1e293b !important; }
  section[data-testid="stSidebar"] { background-color: #f8fafc !important; border-right: 1px solid #e2e8f0; }
  [data-testid="stSidebar"] * { color: #1e293b !important; }

  /* Header */
  .app-header {
    background: #1d4ed8;
    border-radius: 10px; padding: 22px 28px; margin-bottom: 22px;
  }
  .app-header h1 { font-size: 1.8rem; font-weight: 700; color: #ffffff; margin: 0 0 4px 0; }
  .app-header p  { font-size: 0.88rem; color: #bfdbfe; margin: 0; }

  /* Verdict banners */
  .banner-pass {
    background: #f0fdf4; border: 1px solid #86efac;
    border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;
    color: #15803d; font-weight: 600; font-size: 0.95rem;
  }
  .banner-fail {
    background: #fff7ed; border: 1px solid #fdba74;
    border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;
    color: #c2410c; font-weight: 600; font-size: 0.95rem;
  }

  /* Section titles */
  .sec-title {
    font-size: 1rem; font-weight: 700; color: #1e40af;
    border-bottom: 2px solid #dbeafe; padding-bottom: 8px; margin-bottom: 14px;
  }

  /* Report verdict */
  .report-verdict-pass {
    background: #f0fdf4; border: 2px solid #86efac;
    border-radius: 10px; padding: 22px; text-align: center;
    color: #15803d; font-size: 1.25rem; font-weight: 700; margin-bottom: 20px;
  }
  .report-verdict-fail {
    background: #fff1f2; border: 2px solid #fca5a5;
    border-radius: 10px; padding: 22px; text-align: center;
    color: #be123c; font-size: 1.25rem; font-weight: 700; margin-bottom: 20px;
  }

  /* Report metadata rows */
  .report-card {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 20px 24px; margin-bottom: 20px;
  }
  .report-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.88rem;
  }
  .report-row .lbl { color: #64748b; }
  .report-row .val { color: #1e293b; font-weight: 600; }
  .report-row .val-pass { color: #15803d; font-weight: 700; }
  .report-row .val-fail { color: #dc2626; font-weight: 700; }
  .report-row .val-div { color: #e2e8f0; }

  /* Metric cards */
  [data-testid="stMetric"] {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 18px;
    min-height: 118px;
  }
  [data-testid="stMetricLabel"] p {
    color: #64748b !important; font-size: 0.78rem !important; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.03em;
  }
  [data-testid="stMetricValue"] { color: #1e293b; font-size: 1.65rem; font-weight: 700; }

  /* Page switch at the top of the sidebar, drawn as a segmented control */
  section[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex; flex-wrap: nowrap; gap: 4px; padding: 4px; width: 100%; box-sizing: border-box;
    background: #e2e8f0; border-radius: 10px;
  }
  section[data-testid="stSidebar"] div:has(> [data-testid="stRadio"]),
  section[data-testid="stSidebar"] [data-testid="stRadio"],
  section[data-testid="stSidebar"] [data-testid="stRadio"] > div { width: 100% !important; }
  section[data-testid="stSidebar"] div[role="radiogroup"] label p { white-space: nowrap; }
  section[data-testid="stSidebar"] div[role="radiogroup"] > div,
  section[data-testid="stSidebar"] div[role="radiogroup"] > label { flex: 1; }
  section[data-testid="stSidebar"] div[role="radiogroup"] label {
    width: 100%; justify-content: center; margin: 0 !important; padding: 7px 6px;
    border-radius: 8px; cursor: pointer;
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] label > div { justify-content: center; }
  /* hide the radio circle, keep the text */
  section[data-testid="stSidebar"] div[role="radiogroup"] label
    div:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])) { display: none; }
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #ffffff; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
    color: #1d4ed8 !important; font-weight: 600;
  }

  /* Admin header variant and signed-in badge */
  .app-header.admin { background: #0f172a; }
  .app-header.admin p { color: #cbd5e1; }
  .admin-badge {
    display: inline-block; background: #f0fdf4; color: #15803d; border: 1px solid #86efac;
    border-radius: 999px; padding: 4px 12px; font-size: 0.8rem; font-weight: 600;
  }
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────────
MLOS_VIEW    = "master_list_settlement_update_view"

VALID_DAY   = {"1","1_2","1_2_3","1_2_3_4","2","2_3","2_3_4","3","3_4","4","NA"}
VALID_YN_NA = {"Y","N","NA"}
VALID_YN    = {"Y","N"}
VALID_ACC   = {"Fully Accessible","Partially Accessible","Inaccessible"}
VALID_HAB   = {"Abandoned","Migrated","Inhabited","Partially Inhabited"}
UUID_RE     = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
EDITOR_RE   = re.compile(r'^[a-z]+\.[a-z]+$')
# Nullable MLoS fields (can be null — not subject to null checks):
# primarysettlement_name, alternate_name, reasons_for_inaccessibility
YN_NA_COLS  = {"highrisk","slums","densely_populated","hard2reach","border",
               "nomadic","riverine","fulani"}
INHABITED     = {"Inhabited", "Partially Inhabited"}
NOT_INHABITED = {"Abandoned", "Migrated"}
HH_SIZE_MIN, HH_SIZE_MAX = 2, 15          # plausible people per household (Rule 18)
NAME_MATCH_CUTOFF = 0.85                  # similarity needed for LGA/ward names to match (B4, B5)
NO_REASON   = {"", "NA", "N/A", "NONE", "NIL", "NULL"}   # "no reason given" spellings (Rule 21)
PLACEHOLDER_NAMES = {"test", "testing", "sample", "unknown", "unk", "nil", "null", "none", "na", "n a",
                     "no name", "noname", "not available", "settlement", "new settlement",
                     "abc", "xyz"}         # junk settlement names (SQ7)

def _txt(series):
    """Column as stripped text, blanks as ''."""
    return series.fillna("").astype(str).str.strip()

def _num(series):
    """Column as numbers; blanks and non-numbers become NaN."""
    return pd.to_numeric(_txt(series).where(lambda s: s.ne("")), errors="coerce")

def _name_key(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower().replace("&", " and ")).strip()

def names_match(a, b, cutoff=NAME_MATCH_CUTOFF):
    """True if two place names match, ignoring case, punctuation, spacing and small spelling differences."""
    a, b = _name_key(a), _name_key(b)
    return (a == b or a.replace(" ", "") == b.replace(" ", "")
            or difflib.SequenceMatcher(None, a, b).ratio() >= cutoff)

# ─── Helpers ─────────────────────────────────────────────────────────────────────
def load_sqlite(uploaded_file):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    tmp.write(uploaded_file.read())
    tmp.close()
    return sqlite3.connect(tmp.name), tmp.name

def load_view(conn, view_name):
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{view_name}")')
    cols_info = cur.fetchall()
    safe = [c[1] for c in cols_info
            if c[2] is None or not any(k in str(c[2]).upper()
                                       for k in ("BLOB","POINT","GEOMETRY"))]
    col_str = ", ".join(f'"{c}"' for c in safe)
    return pd.read_sql_query(f'SELECT {col_str} FROM "{view_name}"', conn)

def load_csv(uploaded_file):
    """Load a CSV file as the MLoS table."""
    uploaded_file.seek(0)
    # keep_default_na=False prevents pandas from silently converting the valid
    # domain value "NA" (used in flag columns like highrisk, slums, etc.) to NaN.
    # Only truly empty cells remain as NaN.
    return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)

def load_xlsx(uploaded_file):
    """Load an XLSX/XLS file. Uses the sheet named after the MLoS view (or an alias),
    falling back to the first sheet."""
    uploaded_file.seek(0)
    xl = pd.ExcelFile(uploaded_file)
    sheet_names = xl.sheet_names

    # Resolve mlos sheet — prefer view name, then 'mlos', then first sheet
    mlos_aliases = {MLOS_VIEW.lower(), "mlos", "master_list", "settlements"}
    mlos_sheet = next(
        (s for s in sheet_names if s.lower() in mlos_aliases),
        sheet_names[0]
    )

    # keep_default_na=False prevents pandas from converting the valid domain value
    # "NA" (used in flag columns) to NaN. Only truly empty cells remain as NaN.
    return xl.parse(mlos_sheet, dtype=str, keep_default_na=False)

def upload_key(uploaded_file):
    """Identify an upload by name, size and a hash of its contents, so a corrected file
    re-uploaded under the same name and size is not mistaken for the previous one.
    The hash is memoised per upload (file_id) so it is computed once, not on every rerun."""
    fid  = getattr(uploaded_file, "file_id", None)
    memo = st.session_state.get("_upload_key_memo")
    if fid is not None and memo and memo[0] == fid:
        return memo[1]
    key = (uploaded_file.name, getattr(uploaded_file, "size", None),
           hashlib.sha256(uploaded_file.getvalue()).hexdigest())
    if fid is not None:
        st.session_state["_upload_key_memo"] = (fid, key)
    return key

def get_uploaded_data(uploaded_file, progress=None):
    cache_key = upload_key(uploaded_file)
    if st.session_state.get("uploaded_cache_key") == cache_key:
        if progress is not None:
            progress.progress(100)
        return st.session_state["mlos_df"]

    if progress is not None:
        progress.progress(10)

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()

    if ext in ("xlsx", "xls"):
        if progress is not None:
            progress.progress(35)
        mlos_df = load_xlsx(uploaded_file)
        if progress is not None:
            progress.progress(90)
    elif ext == "csv":
        if progress is not None:
            progress.progress(35)
        mlos_df = load_csv(uploaded_file)
        if progress is not None:
            progress.progress(90)
    else:
        conn, tmp_path = load_sqlite(uploaded_file)
        try:
            if progress is not None:
                progress.progress(35)
            mlos_df = load_view(conn, MLOS_VIEW)
            if progress is not None:
                progress.progress(90)
        finally:
            conn.close()
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    st.session_state["uploaded_cache_key"] = cache_key
    st.session_state["mlos_df"] = mlos_df
    if progress is not None:
        progress.progress(100)
    return mlos_df


def pct(v, t): return f"{v/t*100:.1f}%" if t else "0%"

# Vectorized regex checks — avoid per-row Python function calls
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)

def vec_is_editor(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(EDITOR_RE.pattern, na=False)

# ─── Schema QC ───────────────────────────────────────────────────────────────────
MLOS_REQUIRED_COLS = {
    "state_code", "state_name", "lga_code", "lga_name", "ward_name", "ward_code",
    "takeoffpoint", "takeoffpoint_code", "settlement_name", "primarysettlement_name",
    "alternate_name", "latitude", "longitude", "security_compromised",
    "accessibility_status", "reasons_for_inaccessibility", "habitational_status",
    "set_population", "set_target", "number_of_household", "noncompliant_household",
    "team_code", "day_of_activity", "urban", "rural", "highrisk", "slums",
    "densely_populated", "hard2reach", "border", "nomadic", "scattered",
    "riverine", "fulani", "timestamp", "source", "last_updated", "editor",
    "validation_status", "master_id", "mlos_id", "eha_guid", "settlementarea_globalid",
}

def run_schema_qc(mlos: pd.DataFrame):
    """
    Schema alignment QC — checks required columns are present.
    Returns check entries (same format as run_mlos_qc) and a detail DataFrame.
    Does NOT stop the QC process.
    """
    checks, details = [], []

    mlos_cols    = set(mlos.columns.str.strip().str.lower())
    missing_mlos = sorted(MLOS_REQUIRED_COLS - mlos_cols)
    n_mlos_total = len(MLOS_REQUIRED_COLS)
    n_mlos_miss  = len(missing_mlos)
    checks.append({
        "Rule#": "S1", "QC Check": "MLoS Schema Alignment",
        "Description": f"{n_mlos_total - n_mlos_miss}/{n_mlos_total} required MLoS columns present",
        "Failing Rows": n_mlos_miss, "Total Rows": n_mlos_total,
        "Fail %": pct(n_mlos_miss, n_mlos_total),
        "Status": "❌ FAIL" if n_mlos_miss else "✅ PASS",
    })
    if missing_mlos:
        details.append(pd.DataFrame([{
            "Rule#": "S1", "Rule": "MLoS Schema Alignment",
            "Table": "MLoS", "Missing Column": col,
            "Impact": "QC rule(s) referencing this column will be skipped or may return incorrect results",
        } for col in missing_mlos]))

    schema_detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return checks, schema_detail

def build_schema_report_xlsx(schema_detail: pd.DataFrame) -> bytes:
    """Produce a downloadable Excel report listing schema mismatches."""
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        schema_detail.to_excel(writer, index=False, sheet_name="Schema Issues")
        ws = writer.sheets["Schema Issues"]
        header_fill = PatternFill("solid", fgColor="1D4ED8")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill      = header_fill
            cell.font      = header_font
            cell.alignment = Alignment(horizontal="center")
        for col_cells in ws.columns:
            length = max(len(str(c.value or "")) for c in col_cells) + 4
            ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(length, 60)
    return out.getvalue()

# ─── Longitudinal MLoS Report ────────────────────────────────────────────────────
def make_longitudinal_df(mlos_df: pd.DataFrame,
                          mlos_checks: list,
                          mlos_detail: pd.DataFrame) -> pd.DataFrame:
    """
    Build a wide/longitudinal DataFrame where:
    - Each row is a unique settlement (appears once only)
    - Each QC rule adds a boolean column: True = error, False = no error
    - Only rows with at least one True are returned
    """
    result = mlos_df.copy()
    result["_orig_idx"] = mlos_df.index

    rule_cols = []
    for check in mlos_checks:
        rn       = check["Rule#"]
        col_name = f"Rule_{rn} | {check['QC Check']}"
        rule_cols.append(col_name)
        if "FAIL" in check["Status"] and not mlos_detail.empty:
            # Rules 11 and 12 reuse one Rule# for several columns, so match on the rule name too
            failing_idx = set(mlos_detail.loc[(mlos_detail["Rule#"] == rn) &
                                              (mlos_detail["Rule"] == check["QC Check"])].index)
            result[col_name] = result["_orig_idx"].isin(failing_idx)
        else:
            result[col_name] = False

    result = result.drop(columns=["_orig_idx"])
    error_mask = result[rule_cols].any(axis=1)
    return result[error_mask].reset_index(drop=True)


def build_longitudinal_mlos(mlos_df: pd.DataFrame,
                             mlos_checks: list,
                             mlos_detail: pd.DataFrame) -> bytes:
    """Write the longitudinal DataFrame to a styled Excel file and return bytes."""
    error_df = make_longitudinal_df(mlos_df, mlos_checks, mlos_detail)

    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        error_df.to_excel(writer, index=False, sheet_name="MLoS Issues — Longitudinal")
        ws          = writer.sheets["MLoS Issues — Longitudinal"]
        hdr_fill    = PatternFill("solid", fgColor="1D4ED8")
        err_fill    = PatternFill("solid", fgColor="FEE2E2")
        ok_fill     = PatternFill("solid", fgColor="F0FDF4")
        hdr_font    = Font(bold=True, color="FFFFFF")
        body_font   = Font(size=10)
        center      = Alignment(horizontal="center")

        rule_col_indices = {
            i + 1 for i, h in enumerate(error_df.columns)
            if str(h).startswith("Rule_")
        }

        for ci, cell in enumerate(ws[1], 1):
            cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = center

        for ri in range(2, len(error_df) + 2):
            for ci in range(1, len(error_df.columns) + 1):
                cell = ws.cell(row=ri, column=ci)
                cell.font = body_font
                if ci in rule_col_indices:
                    cell.alignment = center
                    cell.fill = err_fill if cell.value else ok_fill

        for ci, col_name in enumerate(error_df.columns, 1):
            ws.column_dimensions[get_column_letter(ci)].width = (
                36 if str(col_name).startswith("Rule_") else 18
            )

    return out.getvalue()

# ─── Boundary Reference Loading ──────────────────────────────────────────────────
BOUNDARY_REF_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ward_boundary_ref.csv")
BOUNDARY_GEOM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ward_boundary_geom.csv.gz")

@st.cache_data(show_spinner=False)
def load_boundary_refs():
    """Load ward code reference lookup table."""
    # keep_default_na=False prevents pandas from converting the string "NA"
    # (the state_code for Nasarawa) into NaN, which would break state filtering.
    return pd.read_csv(BOUNDARY_REF_PATH, dtype=str, keep_default_na=False) if os.path.exists(BOUNDARY_REF_PATH) else pd.DataFrame()

@st.cache_resource(show_spinner=False)
def load_ward_geoms():
    """Load ward boundary polygons (WGS84) as ward_code + shapely geometry."""
    if not os.path.exists(BOUNDARY_GEOM_PATH):
        return pd.DataFrame(columns=["ward_code", "geometry"])
    geom_df = pd.read_csv(BOUNDARY_GEOM_PATH, dtype=str, keep_default_na=False)
    geom_df["geometry"] = shapely.from_wkb(geom_df.pop("wkb").values)
    shapely.prepare(geom_df["geometry"].values)
    return geom_df

# ─── Settlement Extent Reference (GRID3 v4.1) ──────────────────────────────────
# GRID3 Nigeria settlement extents rasterised to a 25 m Web Mercator grid, stored as
# zlib-compressed 256×256 tiles (2 bits per cell). Cell values index EXTENT_TYPES.
SETTLEMENT_EXTENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settlement_extent_mask.npz")
EXTENT_TYPES = np.array(["", "Hamlet", "Small Settlement Area", "Built-up Area"])
EXTENT_BUFFER_M = 50     # a settlement must be on, or within this distance of, an extent
EXTENT_SEARCH_M = 500    # how far to look when reporting the nearest extent for failures

class SettlementExtentMask:
    def __init__(self, path):
        z = np.load(path)
        self.x0, self.y1, self.res, tile, self.tx, self.ty = z["meta"]
        self.tile = int(tile)
        self.tx, self.ty = int(self.tx), int(self.ty)
        offsets = z["offsets"]
        self.index = {int(k): (offsets[i], offsets[i + 1]) for i, k in enumerate(z["keys"])}
        self.data  = z["data"].tobytes()
        self.cache = {}

    def _tile(self, key):
        if key not in self.cache:
            if key not in self.index:
                self.cache[key] = None
            else:
                a, b = self.index[key]
                p = np.frombuffer(zlib.decompress(self.data[a:b]), dtype=np.uint8)
                p = p.reshape(self.tile, self.tile // 4)
                self.cache[key] = np.stack([(p >> s) & 3 for s in (0, 2, 4, 6)], axis=-1
                                           ).reshape(self.tile, self.tile)
        return self.cache[key]

    def cells(self, lat, lon):
        """Grid row/column of each WGS84 point."""
        R = 6378137.0
        x = R * np.radians(lon)
        y = R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        return (np.floor((self.y1 - y) / self.res).astype(np.int64),
                np.floor((x - self.x0) / self.res).astype(np.int64))

    def lookup(self, rows, cols):
        """Extent type code (0–3) at each grid cell; 0 outside the grid."""
        out = np.zeros(rows.shape, dtype=np.uint8)
        T = self.tile
        inside = (rows >= 0) & (cols >= 0) & (rows < self.ty * T) & (cols < self.tx * T)
        r, c = rows[inside], cols[inside]
        key = (r // T) * self.tx + c // T
        vals = np.zeros(len(r), dtype=np.uint8)
        order = np.argsort(key, kind="stable")
        uk, starts = np.unique(key[order], return_index=True)
        for k, idx in zip(uk, np.split(order, starts[1:])):
            t = self._tile(int(k))
            if t is not None:
                vals[idx] = t[r[idx] % T, c[idx] % T]
        out[inside] = vals
        return out

    def nearest(self, lat, lon, radius_m):
        """Distance (m, cell precision) to and type of the nearest extent cell within
        radius_m of each point; inf / 0 where none."""
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        best_d = np.full(len(lat), np.inf)
        best_t = np.zeros(len(lat), dtype=np.uint8)
        # Only search from points on or near the grid. A typo latitude (e.g. 90 or 100)
        # would otherwise size the search window from cos(lat) ≈ 0 or < 0, either
        # exhausting memory or leaving the window empty so every point fails. Points
        # outside the grid cannot be on an extent, so they keep inf / 0.
        ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 85) & (np.abs(lon) <= 180)
        with np.errstate(invalid="ignore", divide="ignore"):
            rows, cols = self.cells(np.where(ok, lat, 0.0), np.where(ok, lon, 0.0))
        T = self.tile
        margin = int(np.ceil(radius_m / (self.res * np.cos(np.radians(85)))))
        ok &= ((rows >= -margin) & (cols >= -margin) &
               (rows < self.ty * T + margin) & (cols < self.tx * T + margin))
        todo = np.flatnonzero(ok)
        if not len(todo):
            return best_d, best_t
        scale = self.res * np.cos(np.radians(lat))          # ground metres per cell
        n = int(np.ceil(radius_m / scale[todo].min()))
        dy, dx = np.mgrid[-n:n + 1, -n:n + 1]
        dy, dx = dy.ravel(), dx.ravel()
        cell_d = np.hypot(dy, dx)
        order = np.argsort(cell_d, kind="stable")
        dy, dx, cell_d = dy[order], dx[order], cell_d[order]
        for oy, ox, cd in zip(dy, dx, cell_d):
            if not len(todo):
                break
            d = cd * scale[todo]
            within = d <= radius_m
            todo = todo[within]
            if not len(todo):
                continue
            t = self.lookup(rows[todo] + oy, cols[todo] + ox)
            hit = t > 0
            best_d[todo[hit]] = cd * scale[todo[hit]]
            best_t[todo[hit]] = t[hit]
            todo = todo[~hit]
        return best_d, best_t

@st.cache_resource(show_spinner=False)
def load_settlement_extents():
    return SettlementExtentMask(SETTLEMENT_EXTENT_PATH) if os.path.exists(SETTLEMENT_EXTENT_PATH) else None

# ─── Health Facility Reference (takeoffpoints) ──────────────────────────────────
HEALTH_FACILITY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_facility_ref.csv.gz")

# Facility-type abbreviations expanded before comparison, and generic facility-type
# words ignored, so "PHC Ojede" and "Ojede Primary Health Center" compare equal.
HF_ABBREV = {"phc": "primary health centre", "phcc": "primary health centre",
             "bhc": "basic health centre", "chc": "comprehensive health centre",
             "hc": "health centre", "hp": "health post", "gh": "general hospital",
             "mch": "maternal child health", "fmc": "federal medical centre",
             "pry": "primary", "primry": "primary", "dispensari": "dispensary"}
HF_GENERIC = {"primary", "health", "centre", "center", "centerc", "care", "clinic", "clinics",
              "post", "basic", "comprehensive", "general", "hospital", "dispensary", "model",
              "cottage", "maternity", "maternal", "child", "and", "of", "the", "ward",
              "federal", "medical", "specialist", "facility"}
HF_NUMERAL = re.compile(r"^(\d+|i{1,3}|iv|v|vi{1,3}|ix|x)$")
HF_FUZZY_THRESHOLD = 0.8

def facility_key(name):
    """Distinctive part of a facility name: (sorted place-name words, numerals like II/IV)."""
    words = []
    for w in re.sub(r"[^a-z0-9 ]", " ", str(name).lower()).split():
        words.extend(HF_ABBREV.get(w, w).split())
    core = [w for w in words if w not in HF_GENERIC]
    nums = frozenset(w for w in core if HF_NUMERAL.match(w))
    return " ".join(sorted(w for w in core if not HF_NUMERAL.match(w))), nums

def same_facility(a, b):
    """Place-name words equal or near-identical (spelling variants); numerals must match exactly."""
    (ta, na), (tb, nb) = a, b
    if not ta or not tb or na != nb:
        return False
    return ta == tb or difflib.SequenceMatcher(None, ta, tb).ratio() >= HF_FUZZY_THRESHOLD

@st.cache_resource(show_spinner=False)
def load_health_facilities():
    """ward_code -> list of (facility_key, facility name), from primary and alternate names."""
    if not os.path.exists(HEALTH_FACILITY_PATH):
        return {}
    hf = pd.read_csv(HEALTH_FACILITY_PATH, dtype=str, keep_default_na=False)
    by_ward = {}
    for col in ["primary_name", "alternate_name"]:
        for wc, name in hf.loc[hf[col].str.strip() != "", ["ward_code", col]].values:
            by_ward.setdefault(wc.strip(), []).append((facility_key(name), name.strip()))
    return by_ward

def match_takeoffpoint(ward_code, takeoffpoint, hf_by_ward):
    """Return (matched, note); note names the closest facilities in the ward when unmatched."""
    if not takeoffpoint:
        return False, "No takeoffpoint given"
    facilities = hf_by_ward.get(ward_code, [])
    key = facility_key(takeoffpoint)
    if any(same_facility(key, k) for k, _ in facilities):
        return True, ""
    if not facilities:
        return False, "No health facility in this ward"
    ranked = sorted(facilities, key=lambda f: -difflib.SequenceMatcher(None, key[0], f[0][0]).ratio())
    return False, "; ".join(list(dict.fromkeys(n for _, n in ranked))[:3])

# ─── QC Engine — Ward Boundary ───────────────────────────────────────────────────
def run_ward_boundary_qc(mlos: pd.DataFrame, ref_df: pd.DataFrame, geom_df: pd.DataFrame):
    checks, details = [], []
    total = len(mlos)

    if "ward_code" not in mlos.columns:
        checks.append({
            "Rule#": "B0", "QC Check": "Ward Code — Not Available on Data",
            "Description": "ward_code column is missing from the uploaded data — all boundary checks skipped",
            "Failing Rows": total, "Total Rows": total,
            "Fail %": "100.0%",
            "Status": "❌ FAIL",
        })
        return checks, pd.DataFrame()

    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code","settlement_name"] if c in mlos.columns]

    def add(num, rule, desc, mask, extra=None):
        n    = int(mask.sum())
        cols = BASE + [c for c in (extra or []) if c in mlos.columns and c not in BASE]
        checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                        "Failing Rows": n, "Total Rows": total,
                        "Fail %": pct(n, total),
                        "Status": "❌ FAIL" if n else "✅ PASS"})
        if n:
            sub = mlos[mask][cols].copy()
            sub.insert(0, "Rule#", num)
            sub.insert(1, "Rule", rule)
            details.append(sub)

    # ── Filter boundary reference by state_name (case-insensitive).
    # state_name ("Nasarawa", "Kano", etc.) is a plain readable string shared
    # by both the MLoS data and the boundary reference — no format ambiguity.
    # This replaces state_code filtering which caused false positives because
    # "NA" (Nasarawa's code) is silently converted to NaN by pandas.
    filtered_ref  = ref_df.copy()  if not ref_df.empty  else ref_df

    if (not ref_df.empty
            and "state_name" in mlos.columns
            and "state_name" in ref_df.columns):
        mlos_state_names = set(
            mlos["state_name"].dropna().astype(str).str.strip().str.lower()
        )
        ref_sn_norm  = ref_df["state_name"].astype(str).str.strip().str.lower()
        filtered_ref = filtered_ref[ref_sn_norm.isin(mlos_state_names)]

    # Fallback to full reference if state_name filtering yields nothing
    if filtered_ref.empty and not ref_df.empty:
        filtered_ref  = ref_df.copy()

    # B0 — ward_code must not be null or empty in the uploaded data
    null_wc_mask = mlos["ward_code"].isna() | mlos["ward_code"].astype(str).str.strip().eq("")
    add("B0", "Ward Code — Not Available on Data",
        "ward_code is null or empty on the uploaded data",
        null_wc_mask, ["ward_code"])

    # B1 — non-null ward_codes must exist in the state-name-filtered boundary reference
    if not filtered_ref.empty and "ward_code" in filtered_ref.columns:
        valid_wards   = set(filtered_ref["ward_code"].dropna().astype(str).str.strip())
        has_wc        = ~null_wc_mask   # only check rows that actually have a ward_code
        not_in_ref    = ~mlos["ward_code"].astype(str).str.strip().isin(valid_wards)
        add("B1", "Ward Code — Boundary Reference",
            "ward_code must exist in the admin ward boundary reference for the file's state(s)",
            has_wc & not_in_ref,
            ["ward_code"])

    # B3 — state_name in MLoS must match the state_name the boundary reference
    # assigns to the same ward_code (catches ward codes registered to a different state)
    if (not ref_df.empty
            and "ward_code" in ref_df.columns
            and "state_name" in ref_df.columns
            and "state_name" in mlos.columns
            and "ward_code" in mlos.columns):
        ref_sn_map = (
            ref_df[["ward_code", "state_name"]]
            .drop_duplicates("ward_code")
            .rename(columns={"state_name": "_ref_state_name"})
        )
        chk_sn = pd.DataFrame({
            "ward_code":  mlos["ward_code"].astype(str).str.strip().values,
            "_mlos_sn":   mlos["state_name"].astype(str).str.strip().str.lower().values,
        }, index=mlos.index)
        merged_sn = chk_sn.merge(ref_sn_map, on="ward_code", how="left")
        merged_sn.index = mlos.index
        merged_sn["_ref_sn_lower"] = merged_sn["_ref_state_name"].astype(str).str.strip().str.lower()
        # Only flag rows where the ward_code IS found in the reference but the state_name differs
        ward_found  = merged_sn["_ref_state_name"].notna()
        sn_mismatch = merged_sn["_mlos_sn"] != merged_sn["_ref_sn_lower"]
        mask_b3 = ward_found & sn_mismatch
        add("B3", "State Name — Boundary Reference Match",
            "state_name in MLoS must match the state_name assigned to the ward_code in the boundary reference",
            mask_b3, ["ward_code", "state_name"])

    # B4 / B5 / B6 — LGA, ward name and state code must agree with the reference for the ward_code.
    # Only rows whose ward_code is in the reference are compared (unknown codes are B1's job).
    if not ref_df.empty and {"ward_code", "lga_code", "lga_name", "ward_name", "state_code"} <= set(ref_df.columns):
        ref_by_wc = ref_df.drop_duplicates("ward_code").set_index("ward_code")
        wc_s  = _txt(mlos["ward_code"])
        found = wc_s.isin(ref_by_wc.index)
        ref   = lambda c: wc_s.map(ref_by_wc[c]).fillna("")

        def name_mismatch(col, ref_col):
            got, want = _txt(mlos[col]), ref(ref_col)
            pairs = {p: names_match(*p) for p in set(zip(got, want))}
            return found & got.ne("") & ~pd.Series([pairs[p] for p in zip(got, want)], index=mlos.index)

        def add_with_ref(num, rule, desc, mask, extra, ref_cols):
            add(num, rule, desc, mask, extra)
            if mask.any():
                for label, c in ref_cols:
                    details[-1][label] = ref(c)[mask].values

        if "lga_code" in mlos.columns or "lga_name" in mlos.columns:
            bad = pd.Series(False, index=mlos.index)
            if "lga_code" in mlos.columns:
                got = _txt(mlos["lga_code"]).str.upper()
                bad |= found & got.ne("") & got.ne(ref("lga_code").str.upper())
            if "lga_name" in mlos.columns:
                bad |= name_mismatch("lga_name", "lga_name")
            add_with_ref("B4", "LGA — Boundary Reference Match",
                         "lga_code and lga_name must match the LGA the ward_code belongs to in the boundary "
                         "reference (names compared ignoring case, punctuation and small spelling differences)",
                         bad, ["ward_code", "lga_code", "lga_name"],
                         [("Ref LGA Code", "lga_code"), ("Ref LGA Name", "lga_name")])

        if "ward_name" in mlos.columns:
            add_with_ref("B5", "Ward Name — Boundary Reference Match",
                         "ward_name must match the boundary reference name for the ward_code "
                         "(case, punctuation and small spelling differences ignored)",
                         name_mismatch("ward_name", "ward_name"), ["ward_code", "ward_name"],
                         [("Ref Ward Name", "ward_name")])

        if "state_code" in mlos.columns:
            got = _txt(mlos["state_code"]).str.upper()
            add_with_ref("B6", "State Code — Boundary Reference Match",
                         "state_code must match the state_code of the ward_code in the boundary reference",
                         found & got.ne("") & got.ne(ref("state_code").str.upper()),
                         ["ward_code", "state_code"], [("Ref State Code", "state_code")])

    # B2 — spatial join: the ward_code of the boundary polygon each point falls in
    # must equal the ward_code on the settlement. Rows are skipped only when the
    # point falls in no ward AND the declared ward has no polygon to compare against.
    if not geom_df.empty and "latitude" in mlos.columns and "longitude" in mlos.columns:
        wc  = mlos["ward_code"].astype(str).str.strip().values
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce").values
        lon = pd.to_numeric(mlos["longitude"], errors="coerce").values

        check_pos = np.flatnonzero(~np.isnan(lat) & ~np.isnan(lon) & (lat != 0) & (lon != 0))
        points    = shapely.points(lon[check_pos], lat[check_pos])
        tree      = shapely.STRtree(geom_df["geometry"].values)
        pt_idx, ward_idx = tree.query(points, predicate="intersects")
        codes = geom_df["ward_code"].values
        hits  = {}
        for pi, wi in zip(pt_idx, ward_idx):
            hits.setdefault(pi, []).append(codes[wi])

        has_polygon = set(codes)
        fail   = np.zeros(len(mlos), dtype=bool)
        joined = {}
        for i, pos in enumerate(check_pos):
            found = hits.get(i, [])
            if wc[pos] in found or (not found and wc[pos] not in has_polygon):
                continue
            fail[pos]   = True
            joined[pos] = found

        mask_b2 = pd.Series(fail, index=mlos.index)
        add("B2", "Ward Code — Boundary Spatial Match",
            "ward_code must match the ward_code of the ward boundary polygon the latitude/longitude falls in",
            mask_b2, ["ward_code","latitude","longitude"])

        if mask_b2.any() and details:
            ward_names = (dict(zip(ref_df["ward_code"], ref_df["ward_name"]))
                          if {"ward_code","ward_name"} <= set(ref_df.columns) else {})
            found_lists = [joined[pos] for pos in np.flatnonzero(fail)]
            details[-1]["Boundary Ward Code"] = [
                ", ".join(f[:5]) if f else "No ward found at coordinates" for f in found_lists
            ]
            details[-1]["Boundary Ward Name"] = [
                ", ".join(ward_names.get(c, "") for c in f[:5]) for f in found_lists
            ]

    detail_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return checks, detail_df

# ─── QC Engine — Settlement ──────────────────────────────────────────────────────
def run_settlement_qc(mlos: pd.DataFrame, extents=None):
    import numpy as np
    checks, details = [], []
    total  = len(mlos)
    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code","settlement_name"]
              if c in mlos.columns]

    def add(num, rule, desc, mask, extra=None):
        n    = int(mask.sum())
        cols = BASE + [c for c in (extra or []) if c in mlos.columns and c not in BASE]
        checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                       "Failing Rows": n, "Total Rows": total,
                       "Fail %": pct(n, total),
                       "Status": "❌ FAIL" if n else "✅ PASS"})
        if n:
            sub = mlos[mask][cols].copy()
            sub.insert(0, "Rule#", num)
            sub.insert(1, "Rule", rule)
            details.append(sub)

    # SQ1 — settlement_name must be unique within each ward_code. Names are compared
    # ignoring case and extra whitespace; blank names are left to Rule 1 (NOT NULL).
    if "settlement_name" in mlos.columns and "ward_code" in mlos.columns:
        sn_norm = (mlos["settlement_name"].fillna("").astype(str)
                   .str.strip().str.lower().str.replace(r"\s+", " ", regex=True))
        wc_norm = mlos["ward_code"].fillna("").astype(str).str.strip()
        dup = pd.DataFrame({"wc": wc_norm, "sn": sn_norm}).duplicated(keep=False) & sn_norm.ne("")
        add("SQ1", "Duplicate Settlement Name in Ward",
            "settlement_name must be unique within each ward_code (case and extra spaces ignored)",
            dup, ["ward_code", "settlement_name"])

    # SQ2 — latitude and longitude must not be null
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        add("SQ2", "Latitude/Longitude — Not Null",
            "latitude and longitude must not be null or missing",
            lat.isna() | lon.isna(),
            ["latitude", "longitude"])

    # SQ2b — latitude and longitude must not be "0" or blank
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        add("SQ2b", "Latitude/Longitude — settlement with \"0\" or blanks",
            "latitude and longitude must not be 0 or blank",
            lat.isna() | lon.isna() | (lat == 0) | (lon == 0),
            ["latitude", "longitude"])

    # SQ3 — no two settlements may share identical coordinates (stacked)
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        valid = lat.notna() & lon.notna() & (lat != 0) & (lon != 0)
        coord_df   = pd.DataFrame({"_lat": lat, "_lon": lon})
        stacked    = coord_df[valid].duplicated(keep=False)
        mask_sq3   = pd.Series(False, index=mlos.index)
        mask_sq3[stacked[stacked].index] = True
        add("SQ3", "Stacked Coordinates",
            "no two settlements may share identical latitude/longitude coordinates",
            mask_sq3, ["latitude", "longitude"])

    # SQ4 / SQ5 — settlement proximity clusters. Each settlement is banded by the
    # distance to its nearest other settlement: SQ4 < 20 m, SQ5 20–30 m.
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat   = pd.to_numeric(mlos["latitude"],  errors="coerce").values
        lon   = pd.to_numeric(mlos["longitude"], errors="coerce").values
        valid = np.flatnonzero(~np.isnan(lat) & ~np.isnan(lon) & (lat != 0) & (lon != 0))

        nearest_d = np.full(len(mlos), np.inf)
        nearest_j = np.full(len(mlos), -1)
        cluster   = np.full(len(mlos), -1)

        if len(valid) > 1:
            R  = 6371000.0           # Earth radius in metres
            la = np.radians(lat[valid])
            lo = np.radians(lon[valid])
            # Candidate pairs from a local metric projection (35 m search covers
            # projection error), then exact Haversine distance on each pair.
            pts  = shapely.points(R * lo * np.cos(la), R * la)
            i, j = shapely.STRtree(pts).query(pts, predicate="dwithin", distance=35)
            keep = i < j
            i, j = i[keep], j[keep]
            a = (np.sin((la[i] - la[j]) / 2) ** 2 +
                 np.cos(la[i]) * np.cos(la[j]) * np.sin((lo[i] - lo[j]) / 2) ** 2)
            d = 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
            close = d < 30
            i, j, d = valid[i[close]], valid[j[close]], d[close]

            for a_, b_, d_ in zip(i, j, d):
                if d_ < nearest_d[a_]: nearest_d[a_], nearest_j[a_] = d_, b_
                if d_ < nearest_d[b_]: nearest_d[b_], nearest_j[b_] = d_, a_

            # Cluster = connected group of settlements linked by < 30 m pairs
            parent = {}
            def find(x):
                while parent.get(x, x) != x:
                    parent[x] = parent.get(parent[x], parent[x])
                    x = parent[x]
                return x
            for a_, b_ in zip(i, j):
                ra, rb = find(a_), find(b_)
                if ra != rb: parent[max(ra, rb)] = min(ra, rb)
            members = np.unique(np.concatenate([i, j])) if len(i) else np.array([], dtype=int)
            roots   = {}
            for m in members:
                cluster[m] = roots.setdefault(find(m), len(roots) + 1)

        cluster_size = pd.Series(cluster).map(pd.Series(cluster[cluster > 0]).value_counts()).values
        names = (mlos["settlement_name"].astype(str).values
                 if "settlement_name" in mlos.columns else np.array([""] * len(mlos)))

        def add_proximity(num, rule, desc, fail):
            add(num, rule, desc, pd.Series(fail, index=mlos.index),
                ["ward_code", "settlement_name", "latitude", "longitude"])
            if fail.any():
                pos = np.flatnonzero(fail)
                details[-1]["Cluster ID"]                = [f"C{cluster[p]}" for p in pos]
                details[-1]["Cluster Size"]              = cluster_size[pos].astype(int)
                details[-1]["Nearest Settlement"]        = names[nearest_j[pos]]
                details[-1]["Nearest Distance (m)"]      = nearest_d[pos].round(1)

        add_proximity("SQ4", "Settlements Too Close (< 20 m)",
            "nearest other settlement is less than 20 metres away",
            nearest_d < 20)
        add_proximity("SQ5", "Settlements Too Close (20–30 m)",
            "nearest other settlement is between 20 and 30 metres away",
            (nearest_d >= 20) & (nearest_d < 30))

    # SQ6 — settlement must sit on, or within EXTENT_BUFFER_M of, a GRID3 settlement
    # extent. Points off any extent are likely misplaced or in empty land.
    if extents is not None and "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat   = pd.to_numeric(mlos["latitude"],  errors="coerce").values
        lon   = pd.to_numeric(mlos["longitude"], errors="coerce").values
        valid = np.flatnonzero(~np.isnan(lat) & ~np.isnan(lon) & (lat != 0) & (lon != 0))
        ext_d, _ = extents.nearest(lat[valid], lon[valid], EXTENT_BUFFER_M)
        fail = np.zeros(len(mlos), dtype=bool)
        fail[valid[np.isinf(ext_d)]] = True
        add("SQ6", f"Not on Settlement Extent (> {EXTENT_BUFFER_M} m)",
            f"settlement point is more than {EXTENT_BUFFER_M} metres from any GRID3 settlement extent",
            pd.Series(fail, index=mlos.index),
            ["ward_code", "settlement_name", "latitude", "longitude"])
        if fail.any():
            pos = np.flatnonzero(fail)
            far_d, far_t = extents.nearest(lat[pos], lon[pos], EXTENT_SEARCH_M)
            details[-1]["Nearest Extent (m)"] = [f"> {EXTENT_SEARCH_M}" if np.isinf(d) else str(int(round(d, -1)))
                                                 for d in far_d]
            details[-1]["Nearest Extent Type"] = EXTENT_TYPES[far_t]

    # SQ7 — settlement_name must be a real name, not a placeholder (blank names are left to Rule 1)
    if "settlement_name" in mlos.columns:
        sn  = _txt(mlos["settlement_name"])
        key = sn.map(_name_key)
        junk = sn.ne("") & (
            ~sn.str.contains(r"[^\W\d_]", regex=True)            # no letters at all, e.g. "123", "--"
            | key.str.replace(" ", "", regex=False).str.len().le(2)   # 1–2 characters
            | key.isin(PLACEHOLDER_NAMES)                          # "test", "unknown", "nil", ...
            | key.str.replace(" ", "", regex=False).str.fullmatch(r"(.)\1+")  # "xxx", "aaaa"
        )
        add("SQ7", "Settlement Name — Not a Placeholder",
            "settlement_name must be a real name: not only numbers or symbols, not 1–2 characters, "
            "and not a placeholder such as test, unknown, nil or xxx",
            junk.fillna(False), ["settlement_name"])

    return checks, pd.concat(details) if details else pd.DataFrame()

# ─── Usage Tracking Database (SQLite) ──────────────────────────────────────────────
# Every QC run is logged to a local SQLite database so usage and results from all
# states and users can be compared in State Results. Tables:
#   usage_log      one row per run: file, states, LGAs, format, checks, score, issue rows
#   state_runs     one row per (run, state): score, layer pass rates, issue counts
#   rule_results   one row per (run, state, rule): failing rows and status
#   fail_rows      failing rows from each state's most recent run (replaced each run)
# On Streamlit Community Cloud the file is lost when the app restarts or sleeps.
WAT = timezone(timedelta(hours=1))
USAGE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage_log.db")
USAGE_LOG_COLS = ["run_id", "timestamp", "uploaded_by", "filename", "state_name", "lga_names",
                  "file_format", "mlos_rows", "total_checks", "checks_passing", "checks_failing",
                  "weighted_score", "qc_layers", "issue_rows"]
RESULTS_RUNS_COLS  = ["run_id", "timestamp", "state", "uploaded_by", "filename", "rows",
                      "weighted_score", "schema_pass_pct", "mlos_pass_pct",
                      "settlement_pass_pct", "boundary_pass_pct", "failing_checks", "issue_rows"]
RESULTS_RULES_COLS = ["run_id", "timestamp", "state", "layer", "rule", "check",
                      "failing_rows", "total_rows", "status"]
RESULTS_FAIL_COLS  = ["run_id", "layer", "rule", "check", "lga_name", "ward_code",
                      "settlement_name", "latitude", "longitude", "detail"]
USAGE_TABLES = {"usage_log": USAGE_LOG_COLS, "state_runs": RESULTS_RUNS_COLS,
                "rule_results": RESULTS_RULES_COLS, "fail_rows": ["state"] + RESULTS_FAIL_COLS}

def _usage_db():
    return sqlite3.connect(USAGE_DB_PATH, timeout=30)

def init_usage_db():
    """Create the usage tracking tables if they don't exist."""
    with _usage_db() as conn:
        for table, cols in USAGE_TABLES.items():
            conn.execute(f'CREATE TABLE IF NOT EXISTS {table} ({", ".join(f"{c!r} TEXT" for c in cols)})')
        conn.execute("CREATE INDEX IF NOT EXISTS fail_rows_state ON fail_rows (state)")

def _cell(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (np.integer, np.floating)):
        v = v.item()
    return v if isinstance(v, (int, float)) else str(v)

def resolve_states(df, ref_df, default="Unknown"):
    """State per row, spelled as in the boundary reference (case-insensitive).
    Blank or unknown state names fall back to the state of the row's ward_code,
    then to `default`."""
    col = lambda c: (df[c].fillna("").astype(str).str.strip() if c in df.columns
                     else pd.Series("", index=df.index))
    canon, by_ward = {}, {}
    if not ref_df.empty:
        canon   = {n.lower(): n for n in ref_df["state_name"].unique()}
        by_ward = dict(zip(ref_df["ward_code"], ref_df["state_name"]))
    state = col("state_name").str.lower().map(canon)
    state = state.fillna(col("ward_code").map(by_ward))
    return state.fillna(col("state_name").replace("", np.nan)).fillna(default)

def build_state_results(run_id, timestamp, uploaded_by, filename, mlos_df, layers, ref_df):
    """Split one QC run into per-state run rows, rule rows and failing rows.

    layers: [(layer_name, weight, checks, detail_df_or_None)]. A layer with no
    detail (schema) applies to every state as reported for the whole file.
    Rows with no identifiable state go to the file's state when it has only one.
    """
    states = resolve_states(mlos_df, ref_df, default="")
    known = states[states != ""].unique()
    default = known[0] if len(known) == 1 else "Unknown"
    states = states.replace("", default)
    run_rows, rule_rows, fail_rows = [], [], {}
    for state in sorted(states.unique()):
        n_state = int((states == state).sum())
        pass_rates, failing_checks, issue_rows, frames = {}, 0, 0, []
        for layer, weight, checks, detail in layers:
            by_state = (detail is not None and not detail.empty and "state_name" in detail.columns)
            if by_state:
                d = detail[resolve_states(detail, ref_df, default) == state]
                # Rule numbers can repeat across checks (Rule 9), so count by number + name
                counts = d.groupby([d["Rule#"].astype(str), d["Rule"]]).size()
            n_pass = 0
            for c in checks:
                if detail is None:
                    n_fail, total = int(c["Failing Rows"]), c["Total Rows"]
                elif by_state:
                    n_fail, total = int(counts.get((str(c["Rule#"]), c["QC Check"]), 0)), n_state
                else:
                    n_fail, total = int(c["Failing Rows"]), n_state
                status = "FAIL" if n_fail else "PASS"
                n_pass += status == "PASS"
                failing_checks += status == "FAIL"
                rule_rows.append([run_id, timestamp, state, layer, str(c["Rule#"]), c["QC Check"],
                                  n_fail, int(total), status])
            pass_rates[layer] = (n_pass / len(checks)) if checks else 1.0
            if by_state and not d.empty:
                issue_rows += len(d)
                base = ["Rule#", "Rule", "state_name", "lga_name", "ward_code",
                        "settlement_name", "latitude", "longitude"]
                extra = [c for c in d.columns if c not in base and c != d.columns[2]]
                out = pd.DataFrame({"run_id": run_id, "layer": layer,
                                    "rule": d["Rule#"].astype(str), "check": d["Rule"]})
                for c in ["lga_name", "ward_code", "settlement_name", "latitude", "longitude"]:
                    out[c] = d[c] if c in d.columns else ""
                out["detail"] = [
                    "; ".join(f"{k}: {v}" for k, v in zip(extra, vals)
                              if str(v) not in ("", "nan", "None", "<NA>"))
                    for vals in d[extra].itertuples(index=False, name=None)
                ] if extra else ""
                frames.append(out)
        score = sum(pass_rates[l] * w * 100 for l, w, _, _ in layers)
        run_rows.append([run_id, timestamp, state, uploaded_by, filename, n_state, round(score, 1)]
                        + [round(pass_rates[l] * 100, 1) for l, _, _, _ in layers]
                        + [failing_checks, issue_rows])
        fail_rows[state] = pd.concat(frames) if frames else pd.DataFrame(columns=RESULTS_FAIL_COLS)
    return run_rows, rule_rows, fail_rows

def save_state_results(usage_row, run_rows, rule_rows, fail_rows):
    """Log one run: append usage/run/rule rows and replace each state's failing rows."""
    def insert(conn, table, rows):
        cols = USAGE_TABLES[table]
        conn.executemany(f'INSERT INTO {table} VALUES ({", ".join("?" * len(cols))})',
                         [[None if v == "" else str(v) for v in map(_cell, r)] for r in rows])
    with _usage_db() as conn:
        insert(conn, "usage_log", [usage_row])
        insert(conn, "state_runs", run_rows)
        insert(conn, "rule_results", rule_rows)
        for state, df in fail_rows.items():
            conn.execute("DELETE FROM fail_rows WHERE state = ?", (state,))
            insert(conn, "fail_rows", ([state] + list(r) for r in
                                       df[RESULTS_FAIL_COLS].itertuples(index=False, name=None)))

def load_results_table(table, state=None):
    """Read a usage table (optionally one state's failing rows) as strings."""
    with _usage_db() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table}" + (" WHERE state = ?" if state else ""),
                               conn, params=(state,) if state else None)
    return df.fillna("").astype(str)

def build_state_results_xlsx(latest, runs, rules, usage):
    """Workbook of the shared results: latest run per state, run history, rule results, usage log."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in [("Latest by State", latest), ("Run History", runs.sort_values("timestamp", ascending=False)),
                         ("Rule Results", rules), ("Usage Log", usage.sort_values("timestamp", ascending=False))]:
            df.drop(columns=["run_id"], errors="ignore").to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for i, col in enumerate(df.drop(columns=["run_id"], errors="ignore").columns, 1):
                ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(col)) + 2, 12), 40)
            ws.freeze_panes = "A2"
    return buf.getvalue()

def render_state_results():
    st.markdown('<div class="sec-title">🌍 State Results — all users</div>', unsafe_allow_html=True)
    try:
        runs = load_results_table("state_runs")
    except Exception as e:
        st.error(f"❌ Could not read shared results: {e}")
        return
    if runs.empty:
        st.info("No QC runs have been saved yet.")
        return

    for c in ["rows", "weighted_score", "schema_pass_pct", "mlos_pass_pct", "settlement_pass_pct",
              "boundary_pass_pct", "failing_checks", "issue_rows"]:
        runs[c] = pd.to_numeric(runs[c], errors="coerce")
    runs = runs.sort_values("timestamp")
    latest = runs.drop_duplicates("state", keep="last").sort_values("state")

    m1, m2, m3 = st.columns(3)
    m1.metric("States reporting", f"{latest['state'].nunique()}")
    m2.metric("Runs saved", f"{runs['run_id'].nunique()}")
    m3.metric("Average latest score", f"{latest['weighted_score'].mean():.1f}%")

    st.markdown("**Latest run per state**")
    show = latest[["state", "timestamp", "uploaded_by", "filename", "rows", "weighted_score",
                   "failing_checks", "issue_rows"]].rename(columns={
        "state": "State", "timestamp": "Last Run (WAT)", "uploaded_by": "Uploaded By",
        "filename": "File", "rows": "Rows", "weighted_score": "Score %",
        "failing_checks": "Failing Checks", "issue_rows": "Issue Rows"})
    def score_colour(v):
        if pd.isna(v): return ""
        return ("background-color:#f0fdf4; color:#15803d" if v >= 80 else
                "background-color:#fffbeb; color:#b45309" if v >= 60 else
                "background-color:#fff1f2; color:#be123c")
    st.dataframe(show.style.map(score_colour, subset=["Score %"]).format({"Score %": "{:.1f}"}),
                 hide_index=True, use_container_width=True)

    if runs.groupby("state").size().max() > 1:
        st.markdown("**Score over time**")
        trend = runs.assign(when=pd.to_datetime(runs["timestamp"], errors="coerce")).dropna(subset=["when"])
        st.altair_chart(alt.Chart(trend).mark_line(point=True).encode(
            x=alt.X("when:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
            y=alt.Y("weighted_score:Q", title="Score %", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("state:N", title="State"),
            tooltip=[alt.Tooltip("state:N", title="State"), alt.Tooltip("timestamp:N", title="Run (WAT)"),
                     alt.Tooltip("weighted_score:Q", title="Score %", format=".1f"),
                     alt.Tooltip("filename:N", title="File")],
        ).properties(height=300), use_container_width=True)

    rules_all = load_results_table("rule_results")
    st.download_button(
        "⬇️ Download all state results (Excel)",
        build_state_results_xlsx(latest, runs, rules_all, load_results_table("usage_log")),
        file_name=f"MLoS_State_Results_{datetime.now(WAT):%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="sr_dl_all", help="Latest run per state, run history, rule results for every run, and the usage log")

    st.markdown("---")
    state = st.selectbox("State", latest["state"].tolist(), key="sr_state")
    run = latest[latest["state"] == state].iloc[0]
    st.caption(f"Latest run {run['timestamp']} by {run['uploaded_by'] or '—'} · {run['filename']} · "
               f"{int(run['rows']):,} rows · score {run['weighted_score']:.1f}%")

    rules = load_results_table("rule_results")
    if not rules.empty:
        r = rules[(rules["run_id"] == run["run_id"]) & (rules["state"] == state)].copy()
        r["failing_rows"] = pd.to_numeric(r["failing_rows"], errors="coerce").astype("Int64")
        st.dataframe(r[["layer", "rule", "check", "failing_rows", "total_rows", "status"]].rename(columns={
            "layer": "Layer", "rule": "Rule#", "check": "QC Check", "failing_rows": "Failing Rows",
            "total_rows": "Total Rows", "status": "Status"}),
            hide_index=True, use_container_width=True)

    fails = load_results_table("fail_rows", state).drop(columns=["state"])
    if fails.empty:
        st.success("No failing rows saved for this state's latest run.")
        return
    f1, f2 = st.columns(2)
    lgas  = f1.multiselect("LGA", sorted(fails["lga_name"].unique()), key="sr_lga")
    rsel  = f2.multiselect("Rule", sorted(fails["rule"].unique()), key="sr_rule")
    view = fails
    if lgas: view = view[view["lga_name"].isin(lgas)]
    if rsel: view = view[view["rule"].isin(rsel)]
    st.caption(f"{len(view):,} of {len(fails):,} failing rows")
    st.dataframe(view.drop(columns=["run_id"]), hide_index=True, use_container_width=True)
    st.download_button("⬇️ Download failing rows (CSV)", view.to_csv(index=False).encode(),
                       file_name=f"{state}_failing_rows.csv", mime="text/csv", key="sr_dl")

# ─── Admin Panel ──────────────────────────────────────────────────────────────────
# Password-protected platform usage tracking: every QC run logged to the usage
# database, for the data team lead. Opened from the "🔐 Admin Panel" choice at the
# top of the sidebar. The password is read from Streamlit secrets (`admin_password`);
# when it is not set, admin access is switched off.
NAV_QC, NAV_ADMIN = "🏠 QC Tool", "🔐 Admin Panel"
BRAND_BLUE = "#1d4ed8"
SCORE_SCALE = alt.Scale(type="threshold", domain=[60, 80], range=["#e11d48", "#f59e0b", "#16a34a"])
ADMIN_FILTER_KEYS = ["adm_state", "adm_format", "adm_person", "adm_dates"]

def _admin_password():
    try:
        return str(st.secrets.get("admin_password", "") or "")
    except Exception:
        return ""

def _split_states(value):
    return [s.strip() for s in str(value).split(",") if s.strip()]

def _score_rating(v):
    if pd.isna(v): return "—"
    return "🟢 Good" if v >= 80 else "🟡 Fair" if v >= 60 else "🔴 Poor"

def _reset_admin_filters():
    for k in ADMIN_FILTER_KEYS:
        st.session_state.pop(k, None)

def _runs_per_day_chart(view):
    """Bars of QC runs per day on a real date axis, so quiet days show as gaps."""
    d = view.dropna(subset=["when"])[["when", "run_id"]]
    return alt.Chart(d).mark_bar(color=BRAND_BLUE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3,
                                 width=alt.RelativeBandSize(0.8)).encode(
        x=alt.X("yearmonthdate(when):T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("count():Q", title="QC runs", axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip("yearmonthdate(when):T", title="Day", format="%d %b %Y"),
                 alt.Tooltip("count():Q", title="QC runs")],
    ).properties(height=260)

def _score_per_day_chart(view):
    """Average weighted score per day, on a fixed 0–100 axis with the 80% 'good' line."""
    d = view.dropna(subset=["when", "weighted_score"])[["when", "weighted_score"]]
    line = alt.Chart(d).mark_line(color=BRAND_BLUE, point=alt.OverlayMarkDef(color=BRAND_BLUE, size=50)).encode(
        x=alt.X("yearmonthdate(when):T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("mean(weighted_score):Q", title="Avg score %", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("yearmonthdate(when):T", title="Day", format="%d %b %Y"),
                 alt.Tooltip("mean(weighted_score):Q", title="Avg score %", format=".1f"),
                 alt.Tooltip("count():Q", title="QC runs")],
    )
    good = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(color="#16a34a", strokeDash=[4, 4]).encode(y="y:Q")
    return (good + line).properties(height=260)

def _breakdown_charts(df, key, label):
    """Side-by-side bars for one grouping: QC runs (left) and average score (right), largest first."""
    g = (df.groupby(key).agg(runs=("run_id", "nunique"), score=("weighted_score", "mean"))
           .reset_index().rename(columns={key: label, "runs": "QC runs", "score": "Avg score %"}))
    height = max(140, 34 * len(g))
    y = alt.Y(f"{label}:N", sort=alt.EncodingSortField("QC runs", order="descending"), title=None)
    base = alt.Chart(g).encode(y=y, tooltip=[label, "QC runs", alt.Tooltip("Avg score %:Q", format=".1f")])
    runs = (base.mark_bar(color=BRAND_BLUE, cornerRadiusEnd=3)
                .encode(x=alt.X("QC runs:Q", axis=alt.Axis(tickMinStep=1)))
            + base.mark_text(align="left", dx=4, color="#334155").encode(x="QC runs:Q", text="QC runs:Q"))
    score = (base.mark_bar(cornerRadiusEnd=3)
                 .encode(x=alt.X("Avg score %:Q", scale=alt.Scale(domain=[0, 100])),
                         color=alt.Color("Avg score %:Q", scale=SCORE_SCALE, legend=None))
             + base.mark_text(align="left", dx=4, color="#334155")
                   .encode(x="Avg score %:Q", text=alt.Text("Avg score %:Q", format=".1f")))
    c1, c2 = st.columns(2)
    c1.markdown(f"**QC runs per {label.lower()}**")
    c1.altair_chart(runs.properties(height=height), use_container_width=True)
    c2.markdown(f"**Average score per {label.lower()}**")
    c2.altair_chart(score.properties(height=height), use_container_width=True)

def render_admin_page():
    """Admin page: sign-in card, then the usage tracking panel with a Logout button."""
    expected = _admin_password()
    if not expected:
        st.info("Admin access is off. Set `admin_password` in Streamlit secrets to turn it on.")
        return
    if not st.session_state.get("is_admin"):
        _, col, _ = st.columns([1, 1.3, 1])
        with col, st.container(border=True):
            st.markdown("#### 🔐 Admin sign-in")
            st.caption("Enter the admin password to see every QC run the team has shared.")
            with st.form("admin_login_form", clear_on_submit=True, border=False):
                pw = st.text_input("Admin password", type="password", key="admin_pw")
                submitted = st.form_submit_button("🔓 Login", type="primary", use_container_width=True)
            if submitted:
                if hmac.compare_digest(pw.encode(), expected.encode()):
                    st.session_state["is_admin"] = True
                    st.rerun()
                else:
                    time.sleep(1)   # slows down password guessing
                    st.error("Incorrect password.")
        return
    top_l, top_r = st.columns([5, 1], vertical_alignment="center")
    top_l.markdown('<span class="admin-badge">● Signed in as admin</span>', unsafe_allow_html=True)
    if top_r.button("🔒 Logout", key="admin_logout", use_container_width=True):
        st.session_state["is_admin"] = False
        st.rerun()
    render_admin_panel()

def render_admin_panel():
    """Usage overview, filters, charts, the full usage log, run details and Excel export."""
    try:
        usage = load_results_table("usage_log")
        runs  = load_results_table("state_runs")
        rules = load_results_table("rule_results")
    except Exception as e:
        st.error(f"❌ Could not read the usage database: {e}")
        return
    if usage.empty:
        st.info("No QC runs have been logged yet. Runs appear here once someone runs QC "
                "with **Share results with team** ticked.")
        return

    for c in ["mlos_rows", "total_checks", "checks_passing", "checks_failing", "weighted_score", "issue_rows"]:
        usage[c] = pd.to_numeric(usage[c], errors="coerce")
    runs["weighted_score"] = pd.to_numeric(runs["weighted_score"], errors="coerce")
    usage["when"] = pd.to_datetime(usage["timestamp"], errors="coerce")
    usage["uploaded_by"] = usage["uploaded_by"].replace("", "(name not given)")
    usage = usage.sort_values("when", ascending=False, na_position="last")
    all_states = sorted({s for v in usage["state_name"] for s in _split_states(v)})

    # ── Usage Overview (all logged runs) ──
    st.markdown('<div class="sec-title">📊 Usage Overview</div>', unsafe_allow_html=True)
    week_ago = pd.Timestamp(datetime.now(WAT).replace(tzinfo=None)) - pd.Timedelta(days=7)
    this_week = int((usage["when"] >= week_ago).sum())
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total QC Runs", f"{len(usage):,}", delta=f"+{this_week} in last 7 days" if this_week else None)
    m2.metric("Unique Files", f"{usage['filename'].nunique():,}")
    m3.metric("Unique States", f"{len(all_states):,}")
    m4.metric("Avg Score", f"{usage['weighted_score'].mean():.1f}%" if usage["weighted_score"].notna().any() else "—")
    m5.metric("Total Rows Checked", f"{int(usage['mlos_rows'].fillna(0).sum()):,}")
    last = usage.iloc[0]
    st.caption(f"Last run logged {last['timestamp']} (WAT) by {last['uploaded_by']} · {last['filename']}")

    # ── Filter Logs ──
    st.markdown('<div class="sec-title">🔍 Filter Logs</div>', unsafe_allow_html=True)
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns(4)
        state  = f1.selectbox("State", ["All"] + all_states, key="adm_state")
        fmt    = f2.selectbox("File Format", ["All"] + sorted(usage["file_format"].unique()), key="adm_format")
        person = f3.selectbox("Team Member", ["All"] + sorted(usage["uploaded_by"].unique()), key="adm_person")
        dates  = f4.date_input("Date Range", value=(), key="adm_dates", format="YYYY/MM/DD")

        view = usage
        if state != "All":
            view = view[view["state_name"].map(lambda v: state in _split_states(v))]
        if fmt != "All":
            view = view[view["file_format"] == fmt]
        if person != "All":
            view = view[view["uploaded_by"] == person]
        if isinstance(dates, (list, tuple)) and len(dates) == 2:
            lo, hi = pd.Timestamp(dates[0]), pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
            view = view[(view["when"] >= lo) & (view["when"] < hi)]

        s1, s2 = st.columns([5, 1], vertical_alignment="center")
        s1.markdown(f"Showing **{len(view):,}** of {len(usage):,} runs")
        s2.button("↺ Reset filters", key="adm_reset", on_click=_reset_admin_filters, use_container_width=True)
    if view.empty:
        st.info("No runs match these filters.")
        return

    # ── Charts ──
    st.markdown('<div class="sec-title">📈 Trends</div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["📈 Over Time", "🗺️ By State", "📁 By Format", "👤 By Team Member"])
    with t1:
        c1, c2 = st.columns(2)
        c1.markdown("**QC runs per day**")
        c1.altair_chart(_runs_per_day_chart(view), use_container_width=True)
        c2.markdown("**Average score per day**")
        c2.altair_chart(_score_per_day_chart(view), use_container_width=True)
        st.caption("Dashed green line = 80%, the 'good' score threshold.")
    with t2:
        per_state = runs[runs["run_id"].isin(view["run_id"])][["run_id", "state", "weighted_score"]]
        if per_state.empty:   # older runs without per-state rows: fall back to the run's state list
            per_state = view.assign(state=view["state_name"].map(lambda v: _split_states(v) or ["Unknown"]))
            per_state = per_state.explode("state")[["run_id", "state", "weighted_score"]]
        _breakdown_charts(per_state, "state", "State")
        st.caption("A run covering several states counts once for each state, with that state's own score.")
    with t3:
        _breakdown_charts(view, "file_format", "Format")
    with t4:
        _breakdown_charts(view, "uploaded_by", "Team Member")
        st.caption("Team members are the names picked (or typed under ➕ Other) in the sidebar's **Your name** box.")

    # ── Full Usage Log ──
    log_tbl = view[["timestamp", "uploaded_by", "filename", "state_name", "file_format", "mlos_rows",
                    "total_checks", "checks_passing", "checks_failing", "weighted_score", "issue_rows",
                    "qc_layers"]].rename(columns={
        "timestamp": "Timestamp", "uploaded_by": "Team Member", "filename": "File", "state_name": "State(s)",
        "file_format": "Format", "mlos_rows": "MLoS Rows", "total_checks": "Checks", "checks_passing": "Pass",
        "checks_failing": "Fail", "weighted_score": "Score %", "issue_rows": "Issue Rows",
        "qc_layers": "QC Layers"})
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in [("Usage Log", log_tbl),
                         ("Rule Results", rules[rules["run_id"].isin(view["run_id"])].drop(columns=["run_id"]))]:
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for i, col in enumerate(df.columns, 1):
                ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(col)) + 2, 12), 40)
            ws.freeze_panes = "A2"

    h1, h2 = st.columns([4, 1], vertical_alignment="bottom")
    h1.markdown('<div class="sec-title">📋 Full Usage Log</div>', unsafe_allow_html=True)
    h2.download_button("⬇️ Download (Excel)", buf.getvalue(),
                       file_name=f"MLoS_Usage_Log_{datetime.now(WAT):%Y%m%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="adm_dl", use_container_width=True)
    shown = log_tbl.assign(Timestamp=view["when"], Rating=view["weighted_score"].map(_score_rating))
    shown = shown[["Timestamp", "Team Member", "File", "State(s)", "Format", "Score %", "Rating", "MLoS Rows",
                   "Checks", "Pass", "Fail", "Issue Rows", "QC Layers"]]
    st.dataframe(shown, hide_index=True, use_container_width=True, height=380, column_config={
        "Timestamp": st.column_config.DatetimeColumn("Timestamp (WAT)", format="D MMM YYYY, HH:mm"),
        "Score %": st.column_config.ProgressColumn("Score %", min_value=0, max_value=100, format="%.1f%%"),
        "MLoS Rows": st.column_config.NumberColumn(format="%d"),
        "Issue Rows": st.column_config.NumberColumn(format="%d"),
    })
    st.caption("Rating: 🟢 Good ≥ 80% · 🟡 Fair 60–80% · 🔴 Poor < 60%. Runs where **Share results with team** "
               "was unticked are not logged, so they do not appear here.")

    # ── Run Details ──
    st.markdown('<div class="sec-title">🔎 Run Details</div>', unsafe_allow_html=True)
    with st.container(border=True):
        labels = {r.run_id: f"{r.timestamp} · {r.uploaded_by} · {r.filename} · score {r.weighted_score:.1f}%"
                  for r in view.itertuples()}
        sel = st.selectbox("Choose a run", list(labels), format_func=labels.get, key="adm_run")
        run = view[view["run_id"] == sel].iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Score", f"{run['weighted_score']:.1f}%" if pd.notna(run["weighted_score"]) else "—")
        d2.metric("Rows checked", f"{int(run['mlos_rows']):,}" if pd.notna(run["mlos_rows"]) else "—")
        d3.metric("Checks failing", f"{int(run['checks_failing']):,}" if pd.notna(run["checks_failing"]) else "—")
        d4.metric("Issue rows", f"{int(run['issue_rows']):,}" if pd.notna(run["issue_rows"]) else "—")

        per_state_runs = runs[runs["run_id"] == sel]
        if not per_state_runs.empty:
            st.markdown("**Score by state**")
            pct = st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%")
            tbl = per_state_runs[["state", "rows", "weighted_score", "schema_pass_pct", "mlos_pass_pct",
                                  "settlement_pass_pct", "boundary_pass_pct", "failing_checks", "issue_rows"]].copy()
            for c in tbl.columns[1:]:
                tbl[c] = pd.to_numeric(tbl[c], errors="coerce")
            st.dataframe(tbl.rename(columns={
                "state": "State", "rows": "Rows", "weighted_score": "Score %", "schema_pass_pct": "Schema %",
                "mlos_pass_pct": "MLoS %", "settlement_pass_pct": "Settlement %", "boundary_pass_pct": "Boundary %",
                "failing_checks": "Failing Checks", "issue_rows": "Issue Rows"}),
                hide_index=True, use_container_width=True, column_config={
                    "Score %": pct, "Schema %": pct, "MLoS %": pct, "Settlement %": pct, "Boundary %": pct})
        run_rules = rules[rules["run_id"] == sel].copy()
        if not run_rules.empty:
            r1, r2 = st.columns([3, 1], vertical_alignment="bottom")
            r1.markdown("**Rule results**")
            if r2.toggle("Failing checks only", value=True, key="adm_only_fail"):
                run_rules = run_rules[run_rules["status"] == "FAIL"]
            run_rules["status"] = run_rules["status"].map({"PASS": "✅ PASS", "FAIL": "❌ FAIL"}).fillna(run_rules["status"])
            for c in ["failing_rows", "total_rows"]:
                run_rules[c] = pd.to_numeric(run_rules[c], errors="coerce")
            if run_rules.empty:
                st.success("Every check passed in this run.")
            else:
                st.dataframe(run_rules[["state", "layer", "rule", "check", "failing_rows", "total_rows", "status"]]
                             .rename(columns={"state": "State", "layer": "Layer", "rule": "Rule#", "check": "QC Check",
                                              "failing_rows": "Failing Rows", "total_rows": "Total Rows",
                                              "status": "Status"}),
                             hide_index=True, use_container_width=True)
        st.caption("Failing rows are kept only for each state's latest run. See them on the 🌍 State Results "
                   "section of the QC Tool page.")

init_usage_db()

# ─── Team members (the sidebar's "Your name" dropdown) ──────────────────────────────
TEAM_MEMBERS = sorted([
    "Adanna Alex", "Babatunde Oladipupo", "Oluwadamilare Akindipe", "Victoria Akinyemi", "Peter Okeke",
    "Wonderful Oladipupo", "Adedo Lukmon", "Abubakar Abubakar Sani", "Muhammad Abubakar Mbawaya",
    "Enyinnaya Nwaiwu", "Abatcha Abdulkarim", "Jaiye Oyetoro", "Fashoto Oluwatosin Busayo", "Nasiru Umar",
    "Olusayo Alabi", "Oluwatosin Ilesanmi", "Racheal Olarewaju",
])
OTHER_NAME = "➕ Other (type a new name)"

def team_member_options():
    """The team list, plus new names already logged through "Other", then the "Other" choice."""
    try:
        logged = set(load_results_table("usage_log")["uploaded_by"].str.strip())
    except Exception:
        logged = set()
    known = {n.casefold() for n in TEAM_MEMBERS}
    extra = sorted((n for n in logged if n and n.casefold() not in known), key=str.casefold)
    return TEAM_MEMBERS + extra + [OTHER_NAME]

def clean_new_name(name, options):
    """Tidy a typed name; reuse the existing spelling if it matches a listed name."""
    name = " ".join(str(name).split())
    for opt in options:
        if opt.casefold() == name.casefold():
            return opt
    return name

# ─── Email Sender ─────────────────────────────────────────────────────────────────
def send_qc_email(filename: str, all_checks: list, mlos_fail_rows: int,
                  schema_detail: pd.DataFrame, boundary_fail_rows: int):
    """Send QC summary email using SMTP credentials stored in st.secrets."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    TO  = ["adanna.alex@ehealthnigeria.org"]
    CC  = ["fashoto.busayo@ehealthnigeria.org",
           "victor.idakwo@ehealthnigeria.org",
           "oluwadamilare.akindipe@ehealthnigeria.org"]

    n_fail  = sum(1 for c in all_checks if "FAIL" in c["Status"])
    n_pass  = len(all_checks) - n_fail
    verdict = "CLEAN ✅" if n_fail == 0 else f"FAILING ❌ ({n_fail} check(s))"

    schema_lines = ""
    if not schema_detail.empty:
        missing = schema_detail[["Table","Missing Column"]].to_string(index=False)
        schema_lines = f"\nMissing Columns:\n{missing}\n"

    body = f"""MLoS QC Report — {filename}
{"="*60}
Overall Verdict   : {verdict}
Checks Run        : {len(all_checks)}
Checks Passing    : {n_pass}
Checks Failing    : {n_fail}

MLoS Issue Rows       : {mlos_fail_rows:,}
Boundary Issue Rows   : {boundary_fail_rows:,}
{schema_lines}
Check-by-Check Summary:
{"-"*60}
"""
    for c in all_checks:
        body += f"[{c['Status']}] Rule {c['Rule#']}: {c['QC Check']} — {c['Failing Rows']} failing / {c['Total Rows']} ({c['Fail %']})\n"

    body += f"\n{'='*60}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    msg = MIMEMultipart()
    msg["From"]    = st.secrets.get("smtp_user", "")
    msg["To"]      = ", ".join(TO)
    msg["Cc"]      = ", ".join(CC)
    msg["Subject"] = f"MLoS QC checks for {filename}"
    msg.attach(MIMEText(body, "plain"))

    smtp_host = st.secrets.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(st.secrets.get("smtp_port", 587))
    smtp_user = st.secrets.get("smtp_user", "")
    smtp_pass = st.secrets.get("smtp_pass", "")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, TO + CC, msg.as_string())

# ─── Auto Correction ─────────────────────────────────────────────────────────────
FLAG_COLS = [
    "highrisk", "slums", "densely_populated", "hard2reach",
    "border", "nomadic", "scattered", "riverine", "fulani",
]

def auto_correct_mlos(mlos: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Apply auto-corrections to the MLoS DataFrame.
    Returns a corrected copy and a log of changes made.
    """
    import uuid as _uuid
    df  = mlos.copy()
    log = []   # list of {Column, Correction, Rows Fixed}

    # ── Correction 1: Flag columns NULL → "NA" ───────────────────────────────
    for col in FLAG_COLS:
        if col not in df.columns:
            continue
        mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        n = int(mask.sum())
        if n:
            df.loc[mask, col] = "NA"
            log.append({"Column": col,
                        "Correction": "NULL → NA",
                        "Rows Fixed": n})

    # ── Correction 1b: scattered NULL or "NA" → "N" ─────────────────────────
    if "scattered" in df.columns:
        mask = (
            df["scattered"].isna() |
            df["scattered"].astype(str).str.strip().eq("") |
            df["scattered"].astype(str).str.strip().eq("NA")
        )
        n = int(mask.sum())
        if n:
            df.loc[mask, "scattered"] = "N"
            log.append({"Column": "scattered",
                        "Correction": "NULL / NA → N",
                        "Rows Fixed": n})

    # ── Correction 2: Fully Accessible + NULL reason → "NA" ──────────────────
    if "accessibility_status" in df.columns and "reasons_for_inaccessibility" in df.columns:
        mask = (
            df["accessibility_status"].astype(str).str.strip().eq("Fully Accessible") &
            (df["reasons_for_inaccessibility"].isna() |
             df["reasons_for_inaccessibility"].astype(str).str.strip().eq(""))
        )
        n = int(mask.sum())
        if n:
            df.loc[mask, "reasons_for_inaccessibility"] = "NA"
            log.append({"Column": "reasons_for_inaccessibility",
                        "Correction": "NULL → NA (Fully Accessible rows)",
                        "Rows Fixed": n})

    # ── Correction 3: source NULL / empty → "IE" ─────────────────────────────
    if "source" in df.columns:
        mask = df["source"].isna() | df["source"].astype(str).str.strip().eq("")
        n = int(mask.sum())
        if n:
            df.loc[mask, "source"] = "IE"
            log.append({"Column": "source",
                        "Correction": "NULL / empty → IE",
                        "Rows Fixed": n})

    # ── Correction 4: eha_guid — strip braces then regenerate invalid UUIDs ──
    if "eha_guid" in df.columns:
        # Step 1: strip any { } characters
        has_braces = df["eha_guid"].astype(str).str.contains(r"[\{\}]", na=False)
        n_brace = int(has_braces.sum())
        if n_brace:
            df.loc[has_braces, "eha_guid"] = (
                df.loc[has_braces, "eha_guid"]
                  .astype(str).str.replace(r"[\{\}]", "", regex=True).str.strip()
            )

        # Step 2: generate a fresh UUID for any value still not a valid UUID
        invalid_mask = ~vec_is_uuid(df["eha_guid"])
        n_gen = int(invalid_mask.sum())
        if n_gen:
            df.loc[invalid_mask, "eha_guid"] = [
                str(_uuid.uuid4()) for _ in range(n_gen)
            ]

        total_fixed = n_brace + n_gen
        if total_fixed:
            log.append({"Column": "eha_guid",
                        "Correction": f"Braces removed ({n_brace} rows); UUID regenerated ({n_gen} rows)",
                        "Rows Fixed": total_fixed})

    return df, log


def build_corrected_excel(df: pd.DataFrame) -> bytes:
    """Write the corrected MLoS DataFrame to an Excel file and return bytes."""
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="MLoS Corrected")
        ws       = writer.sheets["MLoS Corrected"]
        hdr_fill = PatternFill("solid", fgColor="1D4ED8")
        hdr_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
        for ci, col in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(ci)].width = max(
                len(str(col)) + 4, 14)
    return out.getvalue()


# ─── QC Engine — MLoS ────────────────────────────────────────────────────────────
def run_mlos_qc(mlos: pd.DataFrame, hf_by_ward: dict):
    checks, details = [], []
    total  = len(mlos)
    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code",
                           "settlement_name","takeoffpoint"]
              if c in mlos.columns]

    def add(num, rule, desc, mask, extra=None):
        n    = int(mask.sum())
        cols = BASE + [c for c in (extra or []) if c in mlos.columns and c not in BASE]
        checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                       "Failing Rows": n, "Total Rows": total,
                       "Fail %": pct(n, total),
                       "Status": "❌ FAIL" if n else "✅ PASS"})
        if n:
            sub = mlos[mask][cols].copy()
            sub.insert(0, "Rule#", num)
            sub.insert(1, "Rule", rule)
            details.append(sub)

    # R1 — All schema NOT NULL fields must not be null
    # Full list of 28 NOT NULL columns from the PostgreSQL schema.
    _NOT_NULL_COLS = [c for c in [
        "state_code", "state_name", "lga_code", "lga_name", "ward_name", "ward_code",
        "settlement_name", "latitude", "longitude",
        "security_compromised", "accessibility_status",
        "set_population", "set_target", "number_of_household",
        "urban", "rural", "scattered",
        "highrisk", "slums", "densely_populated", "hard2reach",
        "border", "nomadic", "riverine", "fulani",
        "timestamp", "eha_guid", "settlementarea_globalid",
    ] if c in mlos.columns]
    if _NOT_NULL_COLS:
        # Loaders use keep_default_na=False, so blank cells arrive as "" rather than NaN
        _is_null = mlos[_NOT_NULL_COLS].isna() | mlos[_NOT_NULL_COLS].apply(
            lambda s: s.astype(str).str.strip().eq(""))
        _null_mask = _is_null.any(axis=1)
        _n1 = int(_null_mask.sum())
        checks.append({
            "Rule#": "1", "QC Check": "Required Fields — Not Null",
            "Description": "All schema NOT NULL fields must not be empty: " + ", ".join(_NOT_NULL_COLS),
            "Failing Rows": _n1, "Total Rows": total,
            "Fail %": pct(_n1, total),
            "Status": "❌ FAIL" if _n1 else "✅ PASS",
        })
        if _n1:
            _cols1 = BASE + [c for c in _NOT_NULL_COLS if c not in BASE]
            _sub1 = mlos[_null_mask][_cols1].copy()
            _sub1.insert(0, "Rule#", "1")
            _sub1.insert(1, "Rule", "Required Fields — Not Null")
            _sub1["Null Fields"] = _is_null[_null_mask].apply(
                lambda row: ", ".join(col for col in _NOT_NULL_COLS if row[col]),
                axis=1,
            )
            details.append(_sub1)

    # R2 — takeoffpoint must be a health facility in the settlement's own ward
    # (names compared via facility_key / same_facility; blank takeoffpoint fails)
    if "takeoffpoint" in mlos.columns and "ward_code" in mlos.columns and hf_by_ward:
        tp = mlos["takeoffpoint"].fillna("").astype(str).str.strip()
        wc = mlos["ward_code"].fillna("").astype(str).str.strip()
        results = {pair: match_takeoffpoint(pair[0], pair[1], hf_by_ward)
                   for pair in set(zip(wc, tp))}
        matched = pd.Series([results[pair][0] for pair in zip(wc, tp)], index=mlos.index)
        add("2", "Takeoffpoint — Health Facility Match",
            "takeoffpoint must be a health facility in the settlement's ward_code "
            "(case, word order, abbreviations like PHC/BHC/HP and minor spelling differences ignored)",
            ~matched, ["takeoffpoint"])
        if (~matched).any():
            details[-1]["Closest Health Facilities in Ward"] = [
                results[pair][1] for pair, ok in zip(zip(wc, tp), matched) if not ok
            ]

    # R3 — Security Compromised Y/N
    if "security_compromised" in mlos.columns:
        add("3", "Security Compromised Y/N",
            "security_compromised must be Y or N",
            ~mlos["security_compromised"].astype(str).str.strip().isin({"Y", "N"}),
            ["security_compromised"])

    # R4 — Accessibility Status Valid
    if "accessibility_status" in mlos.columns:
        add("4", "Accessibility Status Valid",
            "accessibility_status must be: Fully Accessible, Partially Accessible, or Inaccessible",
            ~mlos["accessibility_status"].astype(str).str.strip().isin(VALID_ACC),
            ["accessibility_status"])

    # R5 — Reason for Inaccessibility Required
    if "accessibility_status" in mlos.columns and "reasons_for_inaccessibility" in mlos.columns:
        needs     = mlos["accessibility_status"].isin(["Partially Accessible", "Inaccessible"])
        no_reason = (mlos["reasons_for_inaccessibility"].isna() |
                     mlos["reasons_for_inaccessibility"].astype(str).str.strip().eq(""))
        add("5", "Reason for Inaccessibility Required",
            "Partially Accessible & Inaccessible settlements must have reasons_for_inaccessibility",
            needs & no_reason, ["accessibility_status", "reasons_for_inaccessibility"])

    # R6 — Habitational Status Valid
    if "habitational_status" in mlos.columns:
        add("6", "Habitational Status Valid",
            "habitational_status must be: Abandoned, Migrated, Inhabited, or Partially Inhabited",
            ~mlos["habitational_status"].astype(str).str.strip().isin(VALID_HAB),
            ["habitational_status"])

    # R7 — set_target must not exceed set_population
    if "set_target" in mlos.columns and "set_population" in mlos.columns:
        mask = (pd.to_numeric(mlos["set_target"], errors="coerce") >
                pd.to_numeric(mlos["set_population"], errors="coerce")).fillna(False)
        add("7", "set_target ≤ set_population",
            "set_target must not exceed set_population",
            mask, ["set_target", "set_population"])

    # R8 — number_of_household must not exceed set_population
    if "number_of_household" in mlos.columns and "set_population" in mlos.columns:
        mask = (pd.to_numeric(mlos["number_of_household"], errors="coerce") >
                pd.to_numeric(mlos["set_population"], errors="coerce")).fillna(False)
        add("8", "number_of_household ≤ set_population",
            "number_of_household must not exceed set_population",
            mask, ["number_of_household", "set_population"])

    # R9 — Urban / Rural / Scattered must be Y or N
    for col in ["urban", "rural", "scattered"]:
        if col in mlos.columns:
            add("9", f"{col} is Y or N",
                f"{col} must be Y or N and must not be null",
                ~mlos[col].astype(str).str.strip().isin(VALID_YN), [col])

    if "urban" in mlos.columns and "rural" in mlos.columns:
        mask = ((mlos["urban"].astype(str).str.strip() == "Y") &
                (mlos["rural"].astype(str).str.strip() == "Y"))
        add("9a", "Cannot be both Urban and Rural",
            "A settlement cannot be both urban=Y and rural=Y", mask, ["urban", "rural"])

    if "urban" in mlos.columns and "scattered" in mlos.columns:
        mask = ((mlos["urban"].astype(str).str.strip() == "Y") &
                (mlos["scattered"].astype(str).str.strip() == "Y"))
        add("9b", "Urban cannot be Scattered",
            "Urban settlements cannot be categorised as scattered", mask, ["urban", "scattered"])

    # R10 — Profile Flags must be Y / N / NA
    for col in YN_NA_COLS:
        if col in mlos.columns:
            add("10", f"{col} = Y/N/NA",
                f"{col} must be Y, N, or NA",
                ~mlos[col].astype(str).str.strip().isin(VALID_YN_NA), [col])

    # R11 — Editor must follow firstname.surname format
    if "editor" in mlos.columns:
        add("11", "Editor Format (firstname.surname)",
            "editor must be in format: firstname.surname (all lowercase)",
            ~vec_is_editor(mlos["editor"]), ["editor"])

    # R12 — eha_guid must be a valid UUID
    if "eha_guid" in mlos.columns:
        add("12", "eha_guid is UUID",
            "eha_guid must be a valid UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
            ~vec_is_uuid(mlos["eha_guid"]), ["eha_guid"])

    # R13 — day_of_activity must be a valid day code, or NA if not available (not blank)
    if "day_of_activity" in mlos.columns:
        day = _txt(mlos["day_of_activity"]).str.replace(r"\.0$", "", regex=True)
        add("13", "Day of Activity Valid",
            "day_of_activity must be 1, 1_2, 1_2_3, 1_2_3_4, 2, 2_3, 2_3_4, 3, 3_4, 4, or NA (not blank)",
            ~day.isin(VALID_DAY), ["day_of_activity"])

    # R14 — non-compliant households cannot outnumber households
    if "noncompliant_household" in mlos.columns and "number_of_household" in mlos.columns:
        mask = (_num(mlos["noncompliant_household"]) > _num(mlos["number_of_household"])).fillna(False)
        add("14", "noncompliant_household ≤ number_of_household",
            "noncompliant_household must not exceed number_of_household",
            mask, ["noncompliant_household", "number_of_household"])

    # R15 — counts must be whole numbers ≥ 0 (blank cells are left to Rule 1)
    for col in ["set_population", "set_target", "number_of_household", "noncompliant_household"]:
        if col in mlos.columns:
            v = _num(mlos[col])
            filled = _txt(mlos[col]).ne("")
            add("15", f"{col} is a whole number ≥ 0",
                f"{col} must be a whole number of 0 or more (no text, decimals or negatives)",
                filled & ~(v.notna() & (v >= 0) & (v == v.round())), [col])

    # R16 / R17 — population must agree with habitational_status
    if "habitational_status" in mlos.columns and "set_population" in mlos.columns:
        hab = _txt(mlos["habitational_status"])
        pop = _num(mlos["set_population"])
        add("16", "Inhabited Settlement Has Population",
            "Inhabited and Partially Inhabited settlements must have set_population above 0",
            hab.isin(INHABITED) & (pop <= 0).fillna(False),
            ["habitational_status", "set_population"])
        tgt = _num(mlos["set_target"]) if "set_target" in mlos.columns else pd.Series(np.nan, index=mlos.index)
        add("17", "Abandoned/Migrated Has No Population",
            "Abandoned and Migrated settlements must have set_population and set_target of 0 or blank",
            hab.isin(NOT_INHABITED) & ((pop > 0) | (tgt > 0)).fillna(False),
            ["habitational_status", "set_population", "set_target"])

    # R18 — people per household must be plausible
    if "set_population" in mlos.columns and "number_of_household" in mlos.columns:
        pop = _num(mlos["set_population"])
        hh  = _num(mlos["number_of_household"])
        size = (pop / hh).where((pop > 0) & (hh > 0))
        mask = ((size < HH_SIZE_MIN) | (size > HH_SIZE_MAX)).fillna(False)
        add("18", "Household Size Plausible",
            f"set_population ÷ number_of_household must be between {HH_SIZE_MIN} and {HH_SIZE_MAX} people per household",
            mask, ["set_population", "number_of_household"])
        if mask.any():
            details[-1]["People per Household"] = size[mask].round(1).values

    # R19 — dates must be real dates, not in the future, and last_updated not before timestamp
    _dates = {}
    _latest_ok = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)   # 1-day allowance for time zones
    for col in ["timestamp", "last_updated"]:
        if col in mlos.columns:
            raw = _txt(mlos[col])
            dt  = pd.to_datetime(raw.where(raw.ne("")), errors="coerce", utc=True, format="mixed")
            _dates[col] = dt
            add("19", f"{col} is a Valid Date",
                f"{col} must be a real date and not in the future",
                raw.ne("") & (dt.isna() | (dt > _latest_ok)), [col])
    if len(_dates) == 2:
        add("19a", "last_updated Not Before timestamp",
            "last_updated must not be earlier than timestamp",
            (_dates["last_updated"] < _dates["timestamp"]).fillna(False), ["timestamp", "last_updated"])

    # R20 — IDs must be unique within the file
    for col in ["eha_guid", "mlos_id", "settlementarea_globalid"]:
        if col in mlos.columns:
            v = _txt(mlos[col]).str.lower()
            filled = ~v.isin({"", "na", "null", "none"})
            add("20", f"{col} is Unique",
                f"{col} must not be repeated on more than one row",
                filled & v.duplicated(keep=False), [col])

    # R21 — Fully Accessible settlements should not give a reason for inaccessibility
    if "accessibility_status" in mlos.columns and "reasons_for_inaccessibility" in mlos.columns:
        add("21", "Fully Accessible Has No Inaccessibility Reason",
            "Fully Accessible settlements must have reasons_for_inaccessibility blank or NA",
            _txt(mlos["accessibility_status"]).eq("Fully Accessible")
            & ~_txt(mlos["reasons_for_inaccessibility"]).str.upper().isin(NO_REASON),
            ["accessibility_status", "reasons_for_inaccessibility"])

    # R22 — team_code must be filled in (NA allowed when not available)
    if "team_code" in mlos.columns:
        add("22", "Team Code — Not Blank",
            "team_code must be filled in (use NA if not available)",
            _txt(mlos["team_code"]).eq(""), ["team_code"])

    # Keep original mlos_df indices so make_longitudinal_df can match failing rows correctly
    return checks, pd.concat(details) if details else pd.DataFrame()


# ─── Excel Report Builder ─────────────────────────────────────────────────────────
# ─── QC Report (Excel + PDF), organised by QC category ────────────────────────────
# Category order follows the report's breakdown order: MLoS, Settlement, Boundary, Schema.
REPORT_LAYERS = [("mlos", "MLoS", "🏘️"), ("settlement", "Settlement", "📐"),
                 ("boundary", "Boundary", "🗺️"), ("schema", "Schema", "🔎")]

def build_report_categories(checks, details, weights):
    """One summary dict per QC category: its checks, issue rows, pass rate and weighted contribution."""
    cats = []
    for key, name, icon in REPORT_LAYERS:
        cl = checks.get(key) or []
        n_fail = sum(1 for c in cl if "FAIL" in c["Status"])
        rate = (len(cl) - n_fail) / len(cl) if cl else 1.0
        det = details.get(key)
        cats.append({
            "key": key, "name": name, "icon": icon, "weight": weights[key], "checks": cl,
            "detail": det if det is not None else pd.DataFrame(),
            "n_checks": len(cl), "n_pass": len(cl) - n_fail, "n_fail": n_fail,
            # Schema's detail lists missing columns, not data rows, so it has no issue-row count
            "issue_rows": None if key == "schema" else (0 if det is None else len(det)),
            "pass_rate": rate * 100, "contribution": rate * weights[key] * 100,
        })
    return cats

def build_excel_report(filename, categories, mlos_df, weighted_score, generated_at):
    """Excel QC report: cover with a per-category summary, then a Breakdown and an Issues sheet
    for each category (MLoS, Settlement, Boundary, Schema), then the raw MLoS data."""
    out = BytesIO()
    wb  = openpyxl.Workbook()

    BLU   = "1D4ED8"
    GRN   = "15803D"; LGN = "F0FDF4"
    RED   = "DC2626"; LRD = "FFF1F2"
    LGY   = "F8FAFC"
    WHT   = "FFFFFF"

    hdr_fill  = PatternFill("solid", fgColor=BLU)
    hdr_font  = Font(bold=True, color=WHT, size=10, name="Calibri")
    pass_fill = PatternFill("solid", fgColor=LGN)
    fail_fill = PatternFill("solid", fgColor=LRD)
    lgry_fill = PatternFill("solid", fgColor=LGY)
    body_font = Font(size=10, name="Calibri")
    bold_font = Font(bold=True, size=10, name="Calibri")
    ctr       = Alignment(horizontal="center", vertical="center", wrap_text=True)
    lft       = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    thin      = Side(style="thin", color="D1D5DB")
    bdr       = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hdr_row(ws, row, cols):
        for ci, col in enumerate(cols, 1):
            c = ws.cell(row=row, column=ci, value=col)
            c.fill=hdr_fill; c.font=hdr_font; c.alignment=ctr; c.border=bdr

    def title_bar(ws, cell_range, text, colour=BLU, size=13, height=30):
        ws.merge_cells(cell_range)
        c = ws[cell_range.split(":")[0]]
        c.value = text; c.font = Font(bold=True, size=size, color=WHT, name="Calibri")
        c.fill = PatternFill("solid", fgColor=colour); c.alignment = ctr
        ws.row_dimensions[c.row].height = height

    total_fail  = sum(c["n_fail"] for c in categories)
    total_issue = sum(c["issue_rows"] or 0 for c in categories)

    # ── Sheet 1: Cover ──
    ws = wb.active; ws.title = "QC Report Cover"
    ws.sheet_view.showGridLines = False
    title_bar(ws, "A1:G1", "MLOS CHECKOUT — QUALITY CONTROL REPORT", size=15, height=38)
    meta = [
        ("File",                 filename),
        ("Generated At (WAT)",   generated_at),
        ("MLoS Rows",            len(mlos_df)),
        ("Checks Run",           sum(c["n_checks"] for c in categories)),
        ("Checks Failing",       total_fail),
        ("Total Issue Rows",     total_issue),
        ("Weighted QC Score",    f"{weighted_score:.1f}%"),
    ]
    for ri, (k, v) in enumerate(meta, 3):
        ws.merge_cells(start_row=ri, start_column=2, end_row=ri, end_column=7)
        ka = ws.cell(row=ri, column=1, value=k); ka.font=bold_font; ka.border=bdr
        vb = ws.cell(row=ri, column=2, value=v); vb.font=body_font; vb.border=bdr; vb.alignment=lft
        if ri % 2 == 0: ka.fill=lgry_fill; vb.fill=lgry_fill
    vrow = 3 + len(meta) + 1
    title_bar(ws, f"A{vrow}:G{vrow}",
              "✅  ALL CHECKS PASSED — File is CLEAN" if total_fail == 0
              else f"❌  {total_fail} CHECK(S) FAILING — Review the Breakdown and Issues sheets",
              colour=GRN if total_fail == 0 else RED, size=12)

    srow = vrow + 2
    title_bar(ws, f"A{srow}:G{srow}", "Summary by Category", size=12, height=26)
    cols = ["Category", "Weight", "Checks Run", "Passing", "Failing", "Issue Rows", "Pass Rate"]
    hdr_row(ws, srow + 1, cols)
    for ri, cat in enumerate(categories, srow + 2):
        vals = [f"{cat['name']} Checks", f"{cat['weight']*100:.0f}%", cat["n_checks"], cat["n_pass"],
                cat["n_fail"], "—" if cat["issue_rows"] is None else cat["issue_rows"], f"{cat['pass_rate']:.1f}%"]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            c.font = bold_font if ci == 1 else body_font; c.border = bdr
            c.alignment = lft if ci == 1 else ctr
            c.fill = fail_fill if cat["n_fail"] else pass_fill
    for i, w in enumerate([28, 22, 13, 11, 11, 13, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # helper to write a category's check breakdown sheet
    def write_summary(ws_s, title, checks_list):
        ws_s.sheet_view.showGridLines = False
        title_bar(ws_s, "A1:G1", title)
        cols = ["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]
        hdr_row(ws_s, 2, cols)
        if not checks_list:
            ws_s.cell(row=3, column=1, value="No checks were run for this category.").font = body_font
        for ri, row in enumerate(checks_list, 3):
            is_fail = "FAIL" in row["Status"]
            for ci, key in enumerate(cols, 1):
                c = ws_s.cell(row=ri, column=ci, value=row[key])
                c.font=body_font; c.border=bdr
                c.alignment = ctr if ci in (1,2,5,6,7) else lft
                c.fill = fail_fill if is_fail else pass_fill
        for i, w in enumerate([14,8,32,65,14,12,9], 1):
            ws_s.column_dimensions[get_column_letter(i)].width = w
        ws_s.freeze_panes = "A3"

    # helper to write a category's issue detail sheet
    def write_detail(ws_d, title, detail_df):
        ws_d.sheet_view.showGridLines = False
        if detail_df.empty:
            ws_d["A1"].value     = f"✅ No issues — {title} passed all checks"
            ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
            ws_d["A1"].fill      = PatternFill("solid", fgColor=GRN)
            ws_d["A1"].alignment = ctr
            ws_d.column_dimensions["A"].width = 60
            return
        nc = len(detail_df.columns)
        if nc > 1:
            ws_d.merge_cells(f"A1:{get_column_letter(nc)}1")
        ws_d["A1"].value     = f"{title} — Detailed Issue Rows"
        ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
        ws_d["A1"].fill      = PatternFill("solid", fgColor=RED)
        ws_d["A1"].alignment = ctr
        ws_d.row_dimensions[1].height = 26
        hdr_row(ws_d, 2, list(detail_df.columns))
        for ri, row in enumerate(detail_df.itertuples(index=False), 3):
            for ci, v in enumerate(row, 1):
                c = ws_d.cell(row=ri, column=ci, value=_cell(v))
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = PatternFill("solid", fgColor="FFF5F5")
        for ci in range(1, nc+1):
            mx = max(len(str(detail_df.columns[ci-1])),
                     max((len(str(v)) for v in detail_df.iloc[:200, ci-1].astype(str)), default=0))
            ws_d.column_dimensions[get_column_letter(ci)].width = min(max(mx+3, 12), 42)
        ws_d.freeze_panes = "A3"

    # helper to write raw data sheet
    def write_raw(ws_r, df):
        ws_r.sheet_view.showGridLines = False
        if df.empty: return
        hdr_row(ws_r, 1, list(df.columns))
        for ri, row in enumerate(df.itertuples(index=False), 2):
            for ci, v in enumerate(row, 1):
                c = ws_r.cell(row=ri, column=ci, value=_cell(v))
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = lgry_fill
        for ci in range(1, len(df.columns)+1):
            ws_r.column_dimensions[get_column_letter(ci)].width = 18
        ws_r.freeze_panes = "A2"

    for cat in categories:
        write_summary(wb.create_sheet(f"{cat['name']} Breakdown"), f"{cat['name']} Check Breakdown", cat["checks"])
        write_detail (wb.create_sheet(f"{cat['name']} Issues"),    f"{cat['name']} Checks", cat["detail"])
    write_raw(wb.create_sheet("Raw MLoS Data"), mlos_df)

    wb.save(out)
    return out.getvalue()

_PDF_SUBS = {"≤": "<=", "≥": ">=", "→": "->", "←": "<-", "×": "x", "✅": "", "❌": "", "⚠️": "", "⚠": ""}

def _pdf_text(v):
    """Text safe for the PDF's built-in Helvetica font (Windows-1252): symbols spelled out, emoji dropped."""
    s = str(v)
    for a, b in _PDF_SUBS.items():
        s = s.replace(a, b)
    return xml_escape(s.encode("cp1252", "ignore").decode("cp1252").strip())

def build_pdf_report(filename, categories, n_rows, weighted_score, generated_at):
    """PDF QC report: cover summary, a summary-by-category table, then one check breakdown per
    category (MLoS, Settlement, Boundary, Schema). Row-level issues stay in the Excel report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    BLUE, DARK, MUTED = colors.HexColor("#1d4ed8"), colors.HexColor("#1e293b"), colors.HexColor("#64748b")
    GREEN, RED, AMBER = colors.HexColor("#15803d"), colors.HexColor("#be123c"), colors.HexColor("#b45309")
    PASS_BG, FAIL_BG = colors.HexColor("#f0fdf4"), colors.HexColor("#fff1f2")
    GRID, LIGHT = colors.HexColor("#d1d5db"), colors.HexColor("#f8fafc")

    body  = ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, leading=11, textColor=DARK)
    bold  = ParagraphStyle("bold", parent=body, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=MUTED)
    h1    = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.white)
    h1sub = ParagraphStyle("h1sub", fontName="Helvetica", fontSize=9.5, leading=12,
                           textColor=colors.HexColor("#bfdbfe"))
    h2    = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BLUE,
                           spaceBefore=6, spaceAfter=2)
    hdr   = ParagraphStyle("hdr", parent=body, fontName="Helvetica-Bold", textColor=colors.white)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm, topMargin=14*mm,
                            bottomMargin=16*mm, title=f"MLoS QC Report — {filename}",
                            author="eHealth Africa · MLOS QC Tool")
    W = doc.width

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5); canvas.setFillColor(MUTED)
        canvas.drawString(d.leftMargin, 9*mm,
                          f"MLoS Checkout QC Report · {filename}".encode("cp1252", "ignore").decode("cp1252"))
        canvas.drawRightString(d.leftMargin + d.width, 9*mm, f"Page {d.page}")
        canvas.restoreState()

    def table(rows, widths, row_bgs=None, header_bg=BLUE):
        t = Table(rows, colWidths=widths, repeatRows=1)
        style = [("BACKGROUND", (0, 0), (-1, 0), header_bg),
                 ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                 ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
        for i, bg in enumerate(row_bgs or [], 1):
            style.append(("BACKGROUND", (0, i), (-1, i), bg))
        t.setStyle(TableStyle(style))
        return t

    P  = lambda v, s=body: Paragraph(_pdf_text(v), s)
    Pc = lambda v, s=body: Paragraph(_pdf_text(v), ParagraphStyle("c", parent=s, alignment=1))
    total_fail  = sum(c["n_fail"] for c in categories)
    total_issue = sum(c["issue_rows"] or 0 for c in categories)
    score_col   = GREEN if weighted_score >= 80 else AMBER if weighted_score >= 60 else RED
    story = []

    # Title band
    band = Table([[Paragraph("MLOS CHECKOUT — QUALITY CONTROL REPORT", h1)],
                  [Paragraph("Master List of Settlements · eHealth Africa", h1sub)]], colWidths=[W])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BLUE),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, 0), 12),
                              ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
    story += [band, Spacer(1, 10)]

    # File details + score
    meta = [("File", filename), ("Generated At (WAT)", generated_at), ("MLoS Rows", f"{n_rows:,}"),
            ("Checks Run", str(sum(c["n_checks"] for c in categories))),
            ("Checks Failing", str(total_fail)), ("Total Issue Rows", f"{total_issue:,}")]
    mt = Table([[P(k, bold), P(v)] for k, v in meta], colWidths=[W*0.22, W*0.48])
    mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT])]))
    score_style = ParagraphStyle("score", fontName="Helvetica-Bold", fontSize=26, leading=30,
                                 textColor=score_col, alignment=1)
    st_ = Table([[Paragraph(f"{weighted_score:.1f}%", score_style)],
                 [Pc("Weighted QC Score", small)]], colWidths=[W*0.26])
    st_.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, GRID), ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                             ("TOPPADDING", (0, 0), (-1, 0), 12), ("BOTTOMPADDING", (0, -1), (-1, -1), 10)]))
    side = Table([[mt, st_]], colWidths=[W*0.72, W*0.28])
    side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (0, 0), 8)]))
    story += [side, Spacer(1, 10)]

    verdict_text = ("ALL CHECKS PASSED — File is CLEAN and ready for submission" if total_fail == 0 else
                    f"{total_fail} CHECK(S) FAILING — {total_issue:,} issue row{'' if total_issue == 1 else 's'}. Fix before submission.")
    vt = Table([[Paragraph(_pdf_text(verdict_text), ParagraphStyle(
        "v", fontName="Helvetica-Bold", fontSize=10.5, leading=13, alignment=1,
        textColor=GREEN if total_fail == 0 else RED))]], colWidths=[W])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PASS_BG if total_fail == 0 else FAIL_BG),
                            ("BOX", (0, 0), (-1, -1), 0.8, GREEN if total_fail == 0 else RED),
                            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [vt, Spacer(1, 12)]

    # Summary by category
    story.append(Paragraph("Summary by Category", h2))
    rows = [[Paragraph(h, hdr) for h in ["Category", "Weight", "Checks", "Passing", "Failing",
                                          "Issue Rows", "Pass Rate", "Contribution"]]]
    for c in categories:
        rows.append([P(f"{c['name']} Checks", bold), Pc(f"{c['weight']*100:.0f}%"), Pc(c["n_checks"]),
                     Pc(c["n_pass"]), Pc(c["n_fail"]),
                     Pc("—" if c["issue_rows"] is None else f"{c['issue_rows']:,}"),
                     Pc(f"{c['pass_rate']:.1f}%"), Pc(f"{c['contribution']:.1f}%")])
    rows.append([P("Total", bold), Pc("100%", bold), Pc(sum(c["n_checks"] for c in categories), bold),
                 Pc(sum(c["n_pass"] for c in categories), bold), Pc(total_fail, bold),
                 Pc(f"{total_issue:,}", bold), Pc(""), Pc(f"{weighted_score:.1f}%", bold)])
    w = [0.22, 0.09, 0.09, 0.10, 0.09, 0.13, 0.12, 0.16]
    story.append(table(rows, [W*x for x in w],
                       [FAIL_BG if c["n_fail"] else PASS_BG for c in categories] + [LIGHT]))
    story.append(Paragraph("Schema issues are missing columns, not data rows, so they have no issue-row count. "
                           "Contribution = pass rate x weight; the contributions add up to the weighted score.",
                           small))

    # One breakdown per category
    w = [0.09, 0.07, 0.22, 0.38, 0.08, 0.08, 0.08]
    for c in categories:
        head = [Paragraph(_pdf_text(f"{c['name']} Check Breakdown"), h2),
                Paragraph(_pdf_text(f"{c['n_pass']} of {c['n_checks']} checks passing · weight "
                                    f"{c['weight']*100:.0f}% · pass rate {c['pass_rate']:.1f}%"
                                    + ("" if c["issue_rows"] is None else f" · {c['issue_rows']:,} issue row{'' if c['issue_rows'] == 1 else 's'}")),
                          small), Spacer(1, 4)]
        if not c["checks"]:
            story.append(KeepTogether(head + [P("No checks were run for this category.")]))
            continue
        rows = [[Paragraph(h, hdr) for h in ["Status", "Rule#", "QC Check", "Description", "Failing",
                                              "Total", "Fail %"]]]
        bgs = []
        for chk in c["checks"]:
            fail = "FAIL" in chk["Status"]
            stat = ParagraphStyle("s", parent=bold, alignment=1, textColor=RED if fail else GREEN)
            rows.append([Paragraph("FAIL" if fail else "PASS", stat), Pc(chk["Rule#"], bold), P(chk["QC Check"]),
                         P(chk["Description"]), Pc(f"{int(chk['Failing Rows']):,}"),
                         Pc(f"{int(chk['Total Rows']):,}"), Pc(chk["Fail %"])])
            bgs.append(FAIL_BG if fail else PASS_BG)
        t = table(rows, [W*x for x in w], bgs)
        story += [Spacer(1, 6), KeepTogether(head + [t]) if len(rows) <= 14 else head[0]]
        if len(rows) > 14:
            story += head[1:] + [t]
    story += [Spacer(1, 10), Paragraph("Row-level issues for every rule are in the Excel report "
                                        "(one Issues sheet per category).", small)]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    page = st.radio("Page", [NAV_QC, NAV_ADMIN], horizontal=True,
                    key="nav_page", label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### 📁 Upload Files")

    st.markdown("**MLoS Checkout File**")
    uploaded = st.file_uploader(
        "Upload MLoS file",
        type=["sqlite", "db", "sqlite3", "csv", "xlsx", "xls"],
        key="sqlite_upload", label_visibility="collapsed",
    )
    st.caption("`.sqlite` · `.csv` · `.xlsx` · `.xls`")

    st.markdown("")
    run_qc_btn = st.button(
        "▶️ Run QC",
        type="primary",
        use_container_width=True,
        disabled=(uploaded is None),
    )
    if run_qc_btn and uploaded:
        st.session_state["submitted_key"] = upload_key(uploaded)
    _name_options = team_member_options()
    _picked = st.selectbox("Your name", _name_options, index=None, key="uploader_pick",
                           placeholder="Select your name",
                           help="Pick your name so the run is credited to you. Not listed? Choose ➕ Other.")
    if _picked == OTHER_NAME:
        uploader_name = clean_new_name(
            st.text_input("New name", key="uploader_new", placeholder="Firstname Surname"), _name_options)
    else:
        uploader_name = _picked or ""
    share_results = st.checkbox("Share results with team", value=True, key="share_results",
                                help="Log this run to the usage database shown in State Results")
    if share_results and not uploader_name.strip():
        st.caption("⚠️ No name picked yet. Runs are logged as *(name not given)*.")
    st.markdown("---")
    st.markdown("#### 📋 QC Rules Reference")
    with st.expander("🔧 Auto Correct Rules", expanded=False):
        st.markdown("""
| # | Field | Correction Applied |
|---|-------|--------------------|
| 1 | `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani` | NULL → `NA` |
| 1b | `scattered` | NULL or `NA` → `N` |
| 2 | `reasons_for_inaccessibility` | NULL → `NA` where `accessibility_status = Fully Accessible` |
| 3 | `source` | NULL / empty → `IE` |
| 4 | `eha_guid` | `{` `}` stripped; invalid UUID → new generated UUID |

> Auto Correct runs automatically **before** QC checks on every upload.
        """)
    with st.expander("🔎 Schema Alignment Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| S1 | All 43 required MLoS columns present |

**MLoS required columns:**
`state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `takeoffpoint`, `takeoffpoint_code`, `settlement_name`, `primarysettlement_name`, `alternate_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `reasons_for_inaccessibility`, `habitational_status`, `set_population`, `set_target`, `number_of_household`, `noncompliant_household`, `team_code`, `day_of_activity`, `urban`, `rural`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `scattered`, `riverine`, `fulani`, `timestamp`, `source`, `last_updated`, `editor`, `validation_status`, `master_id`, `mlos_id`, `eha_guid`, `settlementarea_globalid`

        """)
    with st.expander("🏘️ MLoS Table Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| 1 | All schema NOT NULL fields must not be null (`state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `settlement_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `set_population`, `set_target`, `number_of_household`, `urban`, `rural`, `scattered`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani`, `timestamp`, `eha_guid`, `settlementarea_globalid`) |
| 2 | takeoffpoint is a health facility in the settlement's ward (abbreviations/spelling variants allowed) |
| 3 | security_compromised = Y/N |
| 4 | accessibility_status valid |
| 5 | Partial/Inaccessible requires reason |
| 6 | habitational_status valid |
| 7 | set_target ≤ set_population |
| 8 | number_of_household ≤ set_population |
| 9 | urban/rural/scattered = Y/N (no conflict) |
| 10 | Profile flags = Y/N/NA (highrisk, slums, densely_populated, hard2reach, border, nomadic, riverine, fulani) |
| 11 | editor = firstname.surname (lowercase) |
| 12 | eha_guid = valid UUID |
| 13 | day_of_activity = 1, 1_2, 1_2_3, 1_2_3_4, 2, 2_3, 2_3_4, 3, 3_4, 4 or NA (not blank) |
| 14 | noncompliant_household ≤ number_of_household |
| 15 | set_population, set_target, number_of_household, noncompliant_household are whole numbers ≥ 0 |
| 16 | Inhabited / Partially Inhabited → set_population > 0 |
| 17 | Abandoned / Migrated → set_population and set_target are 0 or blank |
| 18 | People per household (set_population ÷ number_of_household) between 2 and 15 |
| 19 | timestamp and last_updated are real dates, not in the future |
| 19a | last_updated is not earlier than timestamp |
| 20 | eha_guid, mlos_id and settlementarea_globalid are not repeated |
| 21 | Fully Accessible → reasons_for_inaccessibility is blank or NA |
| 22 | team_code is filled in (NA if not available) |
        """)
    with st.expander("📐 Settlement QC Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| SQ1 | settlement_name must be unique within each ward_code (case/extra spaces ignored) |
| SQ2 | latitude and longitude must not be null or missing |
| SQ2b | latitude and longitude must not be 0 or blank |
| SQ3 | No two settlements may share identical coordinates (stacked) |
| SQ4 | Nearest other settlement must not be < 20 m away (proximity cluster) |
| SQ5 | Nearest other settlement must not be 20–30 m away (proximity cluster) |
| SQ6 | Settlement must be on, or within 50 m of, a GRID3 settlement extent |
| SQ7 | settlement_name is a real name: not only numbers/symbols, not 1–2 characters, not a placeholder (test, unknown, nil, xxx…) |
        """)
    with st.expander("🗺️ Boundary Check Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| B0 | ward_code is not null/empty on the uploaded data |
| B1 | ward_code exists in admin ward boundary reference (9,406 wards) |
| B2 | ward_code matches the ward boundary polygon the latitude/longitude falls in |
| B3 | state_name in MLoS matches the state_name assigned to that ward_code in the boundary reference |
| B4 | lga_code and lga_name match the LGA of that ward_code in the boundary reference |
| B5 | ward_name matches the boundary reference name for that ward_code (small spelling differences allowed) |
| B6 | state_code matches the state_code of that ward_code in the boundary reference |
        """)
    st.markdown("---")
    st.caption("eHealth Africa · MLOS QC Tool · v1.1")


# ─── HEADER ───────────────────────────────────────────────────────────────────────
if page == NAV_ADMIN:
    st.markdown("""
<div class="app-header admin">
  <h1>🔐 ADMIN PANEL</h1>
  <p>MLOS Checkout QC &nbsp;|&nbsp; Platform usage tracking for every QC run the team has shared</p>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div class="app-header">
  <h1>🗺️ MLOS CHECKOUT QC</h1>
  <p>Master List of Settlements — Quality Control Dashboard &nbsp;|&nbsp; Upload your files and click ▶️ Run QC to begin</p>
</div>
""", unsafe_allow_html=True)

# ─── ADMIN PAGE (chosen at the top of the sidebar) ────────────────────────────────
if page == NAV_ADMIN:
    render_admin_page()
    st.stop()

if not uploaded:
    st.info("👈 **Upload your MLoS file** using the sidebar, then click **▶️ Run QC**.")
    with st.expander("ℹ️ About this tool", expanded=True):
        st.markdown("""
This tool runs automated Quality Control on MLOS checkout files across **4 QC layers**.

**Supported formats:**
- **SQLite** (`.sqlite`, `.db`) — reads the MLoS view directly
- **Excel** (`.xlsx`, `.xls`) — MLoS sheet (or the first sheet)
- **CSV** (`.csv`) — MLoS data

Takeoffpoints are checked against the bundled health facility reference — no separate file is needed.

**QC Layers:**
- 🔎 **Schema Alignment** (S1) — verifies all required columns are present
- 🏘️ **MLoS Rules** (1–22) — data integrity checks, including takeoffpoint vs. health facility, population, dates and unique IDs
- 📐 **Settlement QC** (SQ1–SQ7) — duplicate, coordinate, stacking, proximity, settlement extent and name checks
- 🗺️ **Boundary Checks** (B0–B6) — ward code, spatial ward match, and state, LGA and ward name validation against admin boundary reference

**Outputs:**
- Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score on the dashboard
- Per-rule issue drilldown with downloadable Excel reports
- Full QC report (Excel) and email summary to the data team
        """)
    st.markdown("---")
    render_state_results()
    st.stop()

# ─── Determine submitted state ────────────────────────────────────────────────────
_current_key = upload_key(uploaded)
_qc_submitted = st.session_state.get("submitted_key") == _current_key

if not _qc_submitted:
    st.info("✅ File(s) ready. Click **▶️ Run QC** in the sidebar to start the quality check.")
    st.stop()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────────
load_progress = st.progress(0)
with st.spinner("Loading file…"):
    try:
        mlos_df = get_uploaded_data(uploaded, progress=load_progress)
    except Exception as e:
        st.error(f"❌ Failed to load file: {e}")
        st.stop()

filename = uploaded.name

# ─── RUN QC ───────────────────────────────────────────────────────────────────────
qc_cache_key = _current_key
boundary_ref = load_boundary_refs()
boundary_geom = load_ward_geoms()
hf_by_ward = load_health_facilities()
settlement_extents = load_settlement_extents()

if (st.session_state.get("qc_cache_key") == qc_cache_key
        and "mlos_df_corrected" in st.session_state):
    schema_checks      = st.session_state["schema_checks"]
    schema_detail      = st.session_state["schema_detail"]
    mlos_checks        = st.session_state["mlos_checks"]
    mlos_detail        = st.session_state["mlos_detail"]
    settlement_checks  = st.session_state["settlement_checks"]
    settlement_detail  = st.session_state["settlement_detail"]
    boundary_checks    = st.session_state["boundary_checks"]
    boundary_detail    = st.session_state["boundary_detail"]
    mlos_df            = st.session_state["mlos_df_corrected"]
    _ac_log            = st.session_state["ac_log"]
    load_progress.progress(100)
else:
    qc_bar = st.progress(0, text="⏳ Starting QC checks…")
    with st.status("Running QC checks…", expanded=True) as _qc_status:

        # ── Pre-step: Auto Correct ────────────────────────────────────────
        st.write("🔧 Pre-step — Auto Correct")
        mlos_df, _ac_log = auto_correct_mlos(mlos_df)
        _n_fixed = sum(r["Rows Fixed"] for r in _ac_log)
        if _ac_log:
            st.write(f"   ✅ Auto Correct: {len(_ac_log)} correction(s) applied, {_n_fixed:,} row(s) fixed")
        else:
            st.write("   ✅ Auto Correct: no corrections needed")

        # ── Step 1 / 4: Schema Alignment ─────────────────────────────────
        qc_bar.progress(5, text="🔎 Step 1 / 4 — Schema Alignment…")
        st.write("🔎 Step 1 / 4 — Schema Alignment")
        schema_checks, schema_detail = run_schema_qc(mlos_df)
        schema_fail = sum(1 for c in schema_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if schema_fail else '✅'} Schema: "
                 f"{len(schema_checks) - schema_fail}/{len(schema_checks)} checks passed")
        qc_bar.progress(25, text="✅ Step 1 / 4 — Schema Alignment complete")

        # ── Step 2 / 4: MLoS Rules ───────────────────────────────────────
        qc_bar.progress(26, text="🏘️ Step 2 / 4 — MLoS Rules…")
        st.write("🏘️ Step 2 / 4 — MLoS Rules")
        mlos_checks, mlos_detail = run_mlos_qc(mlos_df, hf_by_ward)
        mlos_qc_fail = sum(1 for c in mlos_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if mlos_qc_fail else '✅'} MLoS: "
                 f"{len(mlos_checks) - mlos_qc_fail}/{len(mlos_checks)} checks passed")
        qc_bar.progress(50, text="✅ Step 2 / 4 — MLoS Rules complete")

        # ── Step 3 / 4: Settlement QC ────────────────────────────────────
        qc_bar.progress(51, text="📐 Step 3 / 4 — Settlement QC…")
        st.write("📐 Step 3 / 4 — Settlement QC")
        settlement_checks, settlement_detail = run_settlement_qc(mlos_df, settlement_extents)
        sq_fail = sum(1 for c in settlement_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if sq_fail else '✅'} Settlement: "
                 f"{len(settlement_checks) - sq_fail}/{len(settlement_checks)} checks passed")
        qc_bar.progress(75, text="✅ Step 3 / 4 — Settlement QC complete")

        # ── Step 4 / 4: Boundary Checks ──────────────────────────────────
        qc_bar.progress(76, text="🗺️ Step 4 / 4 — Boundary Checks…")
        st.write("🗺️ Step 4 / 4 — Boundary Checks")
        boundary_checks, boundary_detail = run_ward_boundary_qc(mlos_df, boundary_ref, boundary_geom)
        b_fail = sum(1 for c in boundary_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if b_fail else '✅'} Boundary: "
                 f"{len(boundary_checks) - b_fail}/{len(boundary_checks)} checks passed")
        qc_bar.progress(100, text="✅ All QC checks complete!")

        load_progress.progress(100)
        _qc_status.update(label="QC checks complete!", state="complete", expanded=False)
    st.session_state["qc_cache_key"]       = qc_cache_key
    st.session_state["schema_checks"]      = schema_checks
    st.session_state["schema_detail"]      = schema_detail
    st.session_state["mlos_checks"]        = mlos_checks
    st.session_state["mlos_detail"]        = mlos_detail
    st.session_state["settlement_checks"]  = settlement_checks
    st.session_state["settlement_detail"]  = settlement_detail
    st.session_state["boundary_checks"]    = boundary_checks
    st.session_state["boundary_detail"]    = boundary_detail
    st.session_state["mlos_df_corrected"]  = mlos_df
    st.session_state["ac_log"]             = _ac_log

all_checks         = schema_checks + mlos_checks + settlement_checks + boundary_checks
n_fail             = sum(1 for c in all_checks if "FAIL" in c["Status"])
n_pass             = len(all_checks) - n_fail
pct_pass           = f"{n_pass / len(all_checks) * 100:.1f}%" if all_checks else "0%"
pct_fail           = f"{n_fail / len(all_checks) * 100:.1f}%" if all_checks else "0%"
mlos_fail_rows     = len(mlos_detail)
settlement_fail_rows = len(settlement_detail)
boundary_fail_rows = len(boundary_detail)

# ── Weighted Score ───────────────────────────────────────────────────────────────
# Schema 10% | MLoS 60% | Settlement 20% | Boundary 10%
# (MLoS absorbed the former Takeoffpoint layer's 20% — takeoffpoint is now MLoS Rule 2)
LAYER_WEIGHTS = {
    "schema":     0.10,
    "mlos":       0.60,
    "settlement": 0.20,
    "boundary":   0.10,
}

def _layer_pass_rate(checks):
    if not checks:
        return 1.0   # no checks → full credit (layer not applicable)
    passing = sum(1 for c in checks if "FAIL" not in c["Status"])
    return passing / len(checks)

schema_score     = _layer_pass_rate(schema_checks)     * LAYER_WEIGHTS["schema"]     * 100
mlos_score       = _layer_pass_rate(mlos_checks)     * LAYER_WEIGHTS["mlos"]       * 100
settlement_score = _layer_pass_rate(settlement_checks) * LAYER_WEIGHTS["settlement"] * 100
boundary_score   = _layer_pass_rate(boundary_checks) * LAYER_WEIGHTS["boundary"]   * 100
weighted_score   = schema_score + mlos_score + settlement_score + boundary_score

# ── Log to the usage database (once per QC run) ─────────────────────────────────────
if share_results and st.session_state.get("results_saved_key") != qc_cache_key:
    _ts     = datetime.now(WAT).strftime("%Y-%m-%d %H:%M")
    _run_id = uuid.uuid4().hex[:12]
    _layers = [("Schema",     LAYER_WEIGHTS["schema"],     schema_checks,     None),
               ("MLoS",       LAYER_WEIGHTS["mlos"],       mlos_checks,       mlos_detail),
               ("Settlement", LAYER_WEIGHTS["settlement"], settlement_checks, settlement_detail),
               ("Boundary",   LAYER_WEIGHTS["boundary"],   boundary_checks,   boundary_detail)]
    _states = sorted(set(resolve_states(mlos_df, boundary_ref, "")) - {""})
    _lgas   = (sorted(set(mlos_df["lga_name"].fillna("").astype(str).str.strip()) - {""})
               if "lga_name" in mlos_df.columns else [])
    _usage_row = [_run_id, _ts, uploader_name.strip(), filename, ", ".join(_states), ", ".join(_lgas),
                  filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown",
                  len(mlos_df), len(all_checks), n_pass, n_fail, round(weighted_score, 1),
                  ", ".join(l for l, _, c, _ in _layers if c),
                  mlos_fail_rows + settlement_fail_rows + boundary_fail_rows]
    try:
        save_state_results(_usage_row, *build_state_results(
            _run_id, _ts, uploader_name.strip(), filename, mlos_df, _layers, boundary_ref))
        st.session_state["results_saved_key"] = qc_cache_key
        st.toast("✅ Run logged to State Results")
    except Exception as e:
        st.warning(f"⚠️ This run could not be logged to the usage database: {e}")

# ─── FILE INFO + METRICS ──────────────────────────────────────────────────────────
st.success(f"✅ Loaded **{filename}** — MLoS: **{len(mlos_df):,} rows**")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("📄 MLoS Rows",     f"{len(mlos_df):,}")
c2.metric("🔍 Checks Run",    f"{len(all_checks)}")
c3.metric("✅ Passing",       f"{n_pass}")
c4.metric("❌ Failing",       f"{n_fail}")
c5.metric("⚠️ Issue Rows",   f"{mlos_fail_rows + settlement_fail_rows + boundary_fail_rows:,}")
c6.metric("📈 Pass Rate",     pct_pass)
c7.metric("🏆 Weighted Score", f"{weighted_score:.1f}%")

st.markdown("---")

# ─── VERDICT BANNER ───────────────────────────────────────────────────────────────
if n_fail == 0:
    st.markdown('<div class="banner-pass">✅ ALL QC CHECKS PASSED — This file is clean and ready for submission.</div>',
                unsafe_allow_html=True)
else:
    st.markdown(
        f'<div class="banner-fail">❌ {n_fail} QC CHECK(S) FAILING — '
        f'{mlos_fail_rows} MLoS rows, {settlement_fail_rows} Settlement rows, '
        f'and {boundary_fail_rows} Boundary rows have issues. '
        f'Review details below before submission.</div>',
        unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔧 Auto Correct",
    "📊 QC Summary",
    "🏘️ MLoS Issues",
    "📐 Settlement QC",
    "🗺️ Boundary Issues",
    "🔍 Raw Data",
    "📄 Generate Report",
    "🌍 State Results",
])

# ── Tab 2: QC Summary ─────────────────────────────────────────────────────────────
with tab2:
    def colour_rows(row):
        if "FAIL" in str(row.get("Status","")):
            return ["background-color:#fff1f2; color:#be123c"] * len(row)
        return ["background-color:#f0fdf4; color:#15803d"] * len(row)

    # ── Weighted Score Breakdown ──────────────────────────────────────────────────
    st.markdown('<div class="sec-title">🏆 Weighted QC Score</div>', unsafe_allow_html=True)

    score_colour = "#15803d" if weighted_score >= 80 else ("#d97706" if weighted_score >= 60 else "#be123c")
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 24px;margin-bottom:16px;">'
        f'<span style="font-size:2rem;font-weight:800;color:{score_colour}">{weighted_score:.1f}%</span>'
        f'<span style="font-size:0.9rem;color:#64748b;margin-left:12px;">Overall Weighted Score</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    score_rows = [
        {"QC Layer": "🔎 Schema Alignment",  "Weight": "10%", "Layer Pass Rate": f"{_layer_pass_rate(schema_checks)*100:.1f}%",     "Weighted Contribution": f"{schema_score:.1f}%"},
        {"QC Layer": "🏘️ MLoS Rules",        "Weight": "60%", "Layer Pass Rate": f"{_layer_pass_rate(mlos_checks)*100:.1f}%",       "Weighted Contribution": f"{mlos_score:.1f}%"},
        {"QC Layer": "📐 Settlement QC",      "Weight": "20%", "Layer Pass Rate": f"{_layer_pass_rate(settlement_checks)*100:.1f}%", "Weighted Contribution": f"{settlement_score:.1f}%"},
        {"QC Layer": "🗺️ Boundary Checks",   "Weight": "10%", "Layer Pass Rate": f"{_layer_pass_rate(boundary_checks)*100:.1f}%",   "Weighted Contribution": f"{boundary_score:.1f}%"},
        {"QC Layer": "🏆 Total",              "Weight": "100%","Layer Pass Rate": "—",                                               "Weighted Contribution": f"{weighted_score:.1f}%"},
    ]
    st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Schema Alignment ─────────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">🔎 Schema Alignment — QC Results</div>', unsafe_allow_html=True)
    if schema_checks:
        df_s = pd.DataFrame(schema_checks)[["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]]
        df_s = df_s.rename(columns={"Failing Rows": "Missing Columns", "Total Rows": "Expected Columns"})
        st.dataframe(df_s.style.apply(colour_rows, axis=1), use_container_width=True, hide_index=True)
    if not schema_detail.empty:
        with st.expander("🔍 View Missing Column Details", expanded=False):
            st.dataframe(schema_detail.drop(columns=["Rule#","Rule"], errors="ignore"),
                         use_container_width=True, hide_index=True)
        st.download_button(
            label="⬇️ Download Schema Error Report (.xlsx)",
            data=build_schema_report_xlsx(schema_detail),
            file_name=filename.rsplit(".",1)[0] + "_schema_errors.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="schema_dl_tab1",
        )
    else:
        st.success("✅ Schema aligned — all required columns are present.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MLoS QC ──────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">🏘️ MLoS Table — QC Results</div>', unsafe_allow_html=True)
    if mlos_checks:
        df_m = pd.DataFrame(mlos_checks)[["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]]
        st.dataframe(df_m.style.apply(colour_rows, axis=1), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">📐 Settlement QC — Results</div>', unsafe_allow_html=True)
    if settlement_checks:
        df_sq = pd.DataFrame(settlement_checks)[["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]]
        st.dataframe(df_sq.style.apply(colour_rows, axis=1), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">🗺️ Boundary Checks — QC Results</div>', unsafe_allow_html=True)
    if boundary_checks:
        df_b = pd.DataFrame(boundary_checks)[["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]]
        st.dataframe(df_b.style.apply(colour_rows, axis=1), use_container_width=True, hide_index=True)

# ── Tab 1: Auto Correct ───────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="sec-title">🔧 Auto Correct — MLoS Data Fixes</div>', unsafe_allow_html=True)
    st.caption(
        "The following corrections are applied automatically to the uploaded MLoS data:\n\n"
        "1. **Flag columns** (`highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, "
        "`nomadic`, `riverine`, `fulani`) — NULL values filled with `NA`\n"
        "2. **Scattered** — NULL or `NA` values filled with `N`\n"
        "3. **Reason for Inaccessibility** — filled with `NA` where `accessibility_status` is "
        "`Fully Accessible` and the reason is NULL\n"
        "4. **Source** — NULL or empty values replaced with `IE`\n"
        "5. **eha_guid** — all `{` and `}` characters stripped; any still-invalid UUID is "
        "replaced with a freshly generated UUID"
    )
    st.markdown("---")

    # mlos_df is already auto-corrected (pre-step); reuse its log instead of correcting twice
    corrected_df, correction_log = mlos_df, _ac_log

    if not correction_log:
        st.success("✅ No corrections needed — all checked fields are already valid.")
    else:
        total_fixes = sum(r["Rows Fixed"] for r in correction_log)
        st.info(f"🔧 **{len(correction_log)} correction(s) applied** across **{total_fixes:,} row(s)**.")
        log_df = pd.DataFrame(correction_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**📥 Download Full MLoS Data (with Auto Corrections)**")
    st.caption(
        f"Full dataset — **{len(corrected_df):,} rows × {len(corrected_df.columns)} columns** — "
        "with all auto corrections applied. Ready for re-upload or submission."
    )
    corrected_bytes = build_corrected_excel(corrected_df)
    corrected_name  = filename.rsplit(".", 1)[0] + "_autocorrected.xlsx"
    st.download_button(
        label     = "⬇️ Download Full MLoS — Auto Corrected (Excel)",
        data      = corrected_bytes,
        file_name = corrected_name,
        mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type      = "primary",
        key       = "download_autocorrected",
    )


# ── Tab 3: MLoS Issues ────────────────────────────────────────────────────────────
with tab3:
    if mlos_detail.empty:
        st.success("✅ No issues found in the MLoS table — all checks passed!")
    else:
        n_failing_checks = sum(1 for c in mlos_checks if "FAIL" in c["Status"])
        st.error(f"❌ **{mlos_fail_rows:,} issue row(s)** across **{n_failing_checks} failing check(s)**")

        for check in mlos_checks:
            if "FAIL" not in check["Status"]: continue
            rn     = check["Rule#"]
            subset = mlos_detail[(mlos_detail["Rule#"] == rn) &
                                 (mlos_detail["Rule"] == check["QC Check"])].drop(columns=["Rule#","Rule"], errors="ignore")
            n      = len(subset)
            with st.expander(f"❌  Rule {rn} — {check['QC Check']}  ({n:,} row{'s' if n!=1 else ''})", expanded=False):
                st.caption(f"📌 {check['Description']}")
                st.dataframe(subset, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**📋 MLoS Issue Rows — Longitudinal View**")
        st.caption("One row per settlement. Each QC rule appears as a column: **Yes** = rule error present, **No** = no error.")

        long_df = make_longitudinal_df(mlos_df, mlos_checks, mlos_detail)
        if not long_df.empty:
            rule_flag_cols = [c for c in long_df.columns if str(c).startswith("Rule_")]
            # Convert booleans to emoji strings for visual clarity — avoids Styler compatibility issues
            display_df = long_df.copy()
            for col in rule_flag_cols:
                display_df[col] = display_df[col].map(lambda v: "Yes" if v is True else ("No" if v is False else v))
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=350)

        long_xlsx = build_longitudinal_mlos(mlos_df, mlos_checks, mlos_detail)
        st.download_button(
            "⬇️ Download MLoS Issues — Longitudinal (Excel)",
            data=long_xlsx,
            file_name=filename.rsplit(".", 1)[0] + "_mlos_issues_longitudinal.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ── Tab 4: Settlement QC Issues ───────────────────────────────────────────────────
with tab4:
    if settlement_detail.empty:
        st.success("✅ No Settlement QC issues found — all checks passed!")
    else:
        n_failing_sq = sum(1 for c in settlement_checks if "FAIL" in c["Status"])
        st.error(f"❌ **{settlement_fail_rows:,} issue row(s)** across **{n_failing_sq} failing check(s)**")

        for check in settlement_checks:
            if "FAIL" not in check["Status"]: continue
            rn     = check["Rule#"]
            subset = settlement_detail[settlement_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
            n      = len(subset)
            with st.expander(f"❌  Rule {rn} — {check['QC Check']}  ({n:,} row{'s' if n!=1 else ''})", expanded=False):
                st.caption(f"📌 {check['Description']}")
                st.dataframe(subset, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**📋 All Settlement QC Issue Rows (combined)**")
        st.dataframe(settlement_detail.drop(columns=["Rule#","Rule"], errors="ignore"),
                     use_container_width=True, hide_index=True, height=350)

        buf_sq = BytesIO()
        with pd.ExcelWriter(buf_sq, engine="openpyxl") as xw:
            settlement_detail.to_excel(xw, sheet_name="All Settlement Issues", index=False)
            for check in settlement_checks:
                if "FAIL" not in check["Status"]: continue
                rn  = check["Rule#"]
                sub = settlement_detail[settlement_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
                sub.to_excel(xw, sheet_name=f"Rule {rn}"[:31], index=False)
        st.download_button("⬇️ Download Settlement QC Issues (Excel)", data=buf_sq.getvalue(),
                           file_name=filename.rsplit(".",1)[0] + "_settlement_issues.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Tab 5: Boundary Issues ────────────────────────────────────────────────────────
with tab5:
    n_b_fail = sum(1 for c in boundary_checks if "FAIL" in c["Status"])
    if n_b_fail == 0:
        st.success("✅ All ward codes match the boundary reference and all coordinates fall within their declared ward boundaries.")
    else:
        st.error(f"❌ **{n_b_fail} boundary check(s) failing** — {boundary_fail_rows:,} issue row(s)")

        for check in boundary_checks:
            if "FAIL" not in check["Status"]: continue
            rn = check["Rule#"]
            has_detail = (not boundary_detail.empty and "Rule#" in boundary_detail.columns)
            subset = (boundary_detail[boundary_detail["Rule#"] == rn]
                      .drop(columns=["Rule#","Rule"], errors="ignore")
                      if has_detail else pd.DataFrame())
            n = len(subset)
            with st.expander(f"❌  Rule {rn} — {check['QC Check']}  ({n:,} row{'s' if n!=1 else ''})", expanded=False):
                st.caption(f"📌 {check['Description']}")
                if subset.empty:
                    st.info("ℹ️ No row-level detail available for this check.")
                else:
                    st.dataframe(subset, use_container_width=True, hide_index=True)

        if boundary_detail.empty:
            st.info("ℹ️ No row-level detail available for the failing boundary check(s) above.")
        else:
            st.markdown("---")
            st.markdown("**📋 All Boundary Issue Rows (combined)**")
            st.caption("Includes `ward_code` from the uploaded file and the matched value from the boundary reference for comparison.")

            # Enrich boundary detail with boundary reference ward_code for comparison
            enriched_detail = boundary_detail.copy()
            if not boundary_ref.empty and "ward_code" in boundary_ref.columns:
                ref_lookup = (
                    boundary_ref[["ward_code","ward_name","lga_code","lga_name","state_code"]]
                    .drop_duplicates("ward_code")
                    .rename(columns={
                        "ward_code":  "Ref Ward Code",
                        "ward_name":  "Ref Ward Name",
                        "lga_code":   "Ref LGA Code",
                        "lga_name":   "Ref LGA Name",
                        "state_code": "Ref State Code",
                    })
                )
                if "ward_code" in enriched_detail.columns:
                    enriched_detail = enriched_detail.merge(
                        ref_lookup,
                        left_on="ward_code", right_on="Ref Ward Code",
                        how="left"
                    )
                    enriched_detail["In Boundary Reference"] = enriched_detail["Ref Ward Code"].notna().map(
                        {True: "Yes", False: "No — not found in reference"}
                    )

            st.dataframe(enriched_detail, use_container_width=True, hide_index=True, height=350)

            buf_b = BytesIO()
            with pd.ExcelWriter(buf_b, engine="openpyxl") as xw:
                enriched_detail.to_excel(xw, sheet_name="All Boundary Issues", index=False)
                for check in boundary_checks:
                    if "FAIL" not in check["Status"]: continue
                    rn  = check["Rule#"]
                    sub = enriched_detail[enriched_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
                    sub.to_excel(xw, sheet_name=f"Rule {rn}"[:31], index=False)
            st.download_button("⬇️ Download Boundary Issues (Excel)", data=buf_b.getvalue(),
                               file_name=filename.rsplit(".",1)[0] + "_boundary_issues.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Tab 6: Raw Data ───────────────────────────────────────────────────────────────
with tab6:
    st.markdown(f"**{len(mlos_df):,} rows × {len(mlos_df.columns)} columns**")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        state_opts = ["All"] + sorted(mlos_df["state_name"].dropna().unique().tolist()) \
                     if "state_name" in mlos_df.columns else ["All"]
        sel_state = st.selectbox("State", state_opts, key="sel_state")
    with fc2:
        if sel_state != "All" and "lga_name" in mlos_df.columns:
            lga_opts = ["All"] + sorted(mlos_df[mlos_df["state_name"]==sel_state]["lga_name"].dropna().unique().tolist())
        elif "lga_name" in mlos_df.columns:
            lga_opts = ["All"] + sorted(mlos_df["lga_name"].dropna().unique().tolist())
        else:
            lga_opts = ["All"]
        sel_lga = st.selectbox("LGA", lga_opts, key="sel_lga")
    with fc3:
        search = st.text_input("Search settlement", placeholder="Type to filter…", key="srch")

    fdf = mlos_df.copy()
    if sel_state != "All" and "state_name" in fdf.columns:
        fdf = fdf[fdf["state_name"] == sel_state]
    if sel_lga != "All" and "lga_name" in fdf.columns:
        fdf = fdf[fdf["lga_name"] == sel_lga]
    if search and "settlement_name" in fdf.columns:
        fdf = fdf[fdf["settlement_name"].astype(str).str.contains(search, case=False, na=False)]
    st.dataframe(fdf, use_container_width=True, hide_index=True, height=420)

# ── Tab 7: Generate Report ────────────────────────────────────────────────────────
with tab7:
    st.markdown('<div class="sec-title">📄 QC Report — Summary &amp; Download</div>', unsafe_allow_html=True)

    # Verdict
    if n_fail == 0:
        st.markdown(
            '<div class="report-verdict-pass">✅ &nbsp; ALL CHECKS PASSED — File is CLEAN and ready for submission</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="report-verdict-fail">❌ &nbsp; {n_fail} CHECK(S) FAILING — '
            f'{mlos_fail_rows + settlement_fail_rows + boundary_fail_rows:,} total issue rows. Fix before submission.</div>',
            unsafe_allow_html=True)

    report_cats = build_report_categories(
        {"schema": schema_checks, "mlos": mlos_checks, "settlement": settlement_checks, "boundary": boundary_checks},
        {"schema": schema_detail, "mlos": mlos_detail, "settlement": settlement_detail, "boundary": boundary_detail},
        LAYER_WEIGHTS)

    # Build both reports once per QC run (not on every click), so the generated time stays fixed
    _rep = st.session_state.get("qc_report")
    if not _rep or _rep["key"] != qc_cache_key:
        with st.spinner("Building Excel and PDF reports…"):
            _gen = datetime.now(WAT).strftime("%Y-%m-%d %H:%M")
            _rep = {"key": qc_cache_key, "generated": _gen,
                    "xlsx": build_excel_report(filename, report_cats, mlos_df, weighted_score, _gen)}
            try:
                _rep["pdf"], _rep["pdf_error"] = build_pdf_report(
                    filename, report_cats, len(mlos_df), weighted_score, _gen), None
            except Exception as e:
                _rep["pdf"], _rep["pdf_error"] = None, str(e)
        st.session_state["qc_report"] = _rep

    # Metadata card
    def rrow(lbl, val, cls="val"):
        return (f'<div class="report-row">'
                f'<span class="lbl">{lbl}</span>'
                f'<span class="{cls}">{val}</span>'
                f'</div>')
    score_cls = "val-pass" if weighted_score >= 80 else "val-fail"
    st.markdown('<div class="report-card">' + "".join([
        rrow("📁 File",                filename),
        rrow("🕐 Generated At (WAT)",  _rep["generated"]),
        rrow("📄 MLoS Rows",           f"{len(mlos_df):,}"),
        rrow("🔍 Checks Run",          f"{len(all_checks)} ({n_pass} passing · {n_fail} failing)"),
        rrow("🏆 Weighted QC Score",   f"{weighted_score:.1f}%", score_cls),
    ]) + '</div>', unsafe_allow_html=True)

    # Summary by category
    st.markdown("**📊 Summary by Category**")
    st.dataframe(pd.DataFrame([{
        "Category": f"{c['icon']} {c['name']} Checks", "Weight": f"{c['weight']*100:.0f}%",
        "Checks Run": c["n_checks"], "Passing": c["n_pass"], "Failing": c["n_fail"],
        "Issue Rows": "—" if c["issue_rows"] is None else f"{c['issue_rows']:,}",
        "Pass Rate": c["pass_rate"]} for c in report_cats]),
        hide_index=True, use_container_width=True, column_config={
            "Pass Rate": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")})
    st.caption("Schema issues are missing columns, not data rows, so they have no issue-row count.")

    # One check breakdown per category
    def hl(row):
        colour = "color:#be123c; font-weight:700" if "FAIL" in str(row.get("Status", "")) \
                 else "color:#15803d; font-weight:700"
        return [colour] + [""] * (len(row) - 1)
    for c in report_cats:
        with st.container(border=True):
            st.markdown(f"**{c['icon']} {c['name']} Check Breakdown**")
            st.caption(f"{c['n_pass']} of {c['n_checks']} checks passing · weight {c['weight']*100:.0f}% · "
                       f"pass rate {c['pass_rate']:.1f}%"
                       + ("" if c["issue_rows"] is None else f" · {c['issue_rows']:,} issue row{'' if c['issue_rows'] == 1 else 's'}"))
            if not c["checks"]:
                st.info("No checks were run for this category.")
                continue
            tbl = pd.DataFrame([{"Status": k["Status"], "Rule#": k["Rule#"], "QC Check": k["QC Check"],
                                 "Description": k["Description"], "Failing": k["Failing Rows"],
                                 "Total": k["Total Rows"], "Fail %": k["Fail %"]} for k in c["checks"]])
            st.dataframe(tbl.style.apply(hl, axis=1), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Download
    st.markdown("**📥 Download Full QC Report**")
    st.caption("Both reports are organised by category: MLoS, Settlement, Boundary and Schema. "
               "The **PDF** has the summary and each category's check breakdown. The **Excel** file adds "
               "an Issues sheet per category with the failing rows, plus the raw MLoS data.")
    report_base = re.sub(r"\.(sqlite3?|db|csv|xlsx|xls)$", "", filename, flags=re.I) + "_QC_Report"
    d1, d2 = st.columns(2)
    d1.download_button(
        label     = "⬇️  Download QC Report (Excel)",
        data      = _rep["xlsx"],
        file_name = report_base + ".xlsx",
        mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type      = "primary", use_container_width=True, key="report_xlsx",
    )
    if _rep["pdf"]:
        d2.download_button(
            label     = "⬇️  Download QC Report (PDF)",
            data      = _rep["pdf"],
            file_name = report_base + ".pdf",
            mime      = "application/pdf",
            type      = "primary", use_container_width=True, key="report_pdf",
        )
    else:
        d2.error(f"❌ The PDF report could not be built: {_rep['pdf_error']}")

    if n_fail == 0:
        st.success("✅ File is CLEAN — all checks passed.")
    else:
        st.warning(f"⚠️ {n_fail} check(s) failing with "
                   f"{mlos_fail_rows + settlement_fail_rows + boundary_fail_rows:,} issue rows. "
                   f"Fix and re-upload before submission.")

    st.markdown("---")
    st.markdown("**📧 Send QC Summary by Email**")
    st.caption("Sends the QC summary to the data team. SMTP credentials must be configured in Streamlit secrets.")
    if st.button("📤 Send QC Email", type="primary", key="send_email_btn"):
        try:
            send_qc_email(filename, all_checks, mlos_fail_rows,
                          schema_detail, boundary_fail_rows)
            st.success("✅ Email sent successfully to the data team.")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}"
                     "\n\nEnsure `smtp_host`, `smtp_port`, `smtp_user`, and `smtp_pass` "
                     "are set in your Streamlit secrets.")

# ── Tab 8: State Results ──────────────────────────────────────────────────────────
with tab8:
    render_state_results()
