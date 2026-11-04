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
from io import BytesIO
from datetime import datetime
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

def get_uploaded_data(uploaded_file, progress=None):
    cache_key = (uploaded_file.name, getattr(uploaded_file, "size", None))
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
        rows, cols = self.cells(lat, lon)
        scale = self.res * np.cos(np.radians(lat))          # ground metres per cell
        n = int(np.ceil(radius_m / scale.min())) if len(lat) else 0
        dy, dx = np.mgrid[-n:n + 1, -n:n + 1]
        dy, dx = dy.ravel(), dx.ravel()
        cell_d = np.hypot(dy, dx)
        order = np.argsort(cell_d, kind="stable")
        dy, dx, cell_d = dy[order], dx[order], cell_d[order]
        best_d = np.full(len(lat), np.inf)
        best_t = np.zeros(len(lat), dtype=np.uint8)
        todo = np.arange(len(lat))
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

    # SQ2b — latitude and longitude must not be zero (where non-null)
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        has_value = lat.notna() & lon.notna()
        add("SQ2b", "Latitude/Longitude — Not Zero",
            "latitude and longitude must not be zero",
            has_value & ((lat == 0) | (lon == 0)),
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
            details[-1]["Nearest Extent (m)"] = [f"> {EXTENT_SEARCH_M}" if np.isinf(d) else int(round(d, -1))
                                                 for d in far_d]
            details[-1]["Nearest Extent Type"] = EXTENT_TYPES[far_t]

    return checks, pd.concat(details) if details else pd.DataFrame()

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

    # Keep original mlos_df indices so make_longitudinal_df can match failing rows correctly
    return checks, pd.concat(details) if details else pd.DataFrame()


# ─── Excel Report Builder ─────────────────────────────────────────────────────────
def build_excel_report(filename, mlos_checks, mlos_detail, mlos_df):
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

    total_fail = sum(1 for c in mlos_checks if "FAIL" in c["Status"])

    # ── Sheet 1: Cover ──
    ws = wb.active; ws.title = "QC Report Cover"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 52
    ws.merge_cells("A1:B1")
    ws["A1"].value = "MLOS CHECKOUT — QUALITY CONTROL REPORT"
    ws["A1"].font  = Font(bold=True, size=15, color=WHT, name="Calibri")
    ws["A1"].fill  = PatternFill("solid", fgColor=BLU)
    ws["A1"].alignment = ctr
    ws.row_dimensions[1].height = 38

    meta = [
        ("File",                   filename),
        ("Generated At",           datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("MLoS Rows",              len(mlos_df)),
        ("MLoS Checks Run",        len(mlos_checks)),
        ("MLoS Checks Failing",    sum(1 for c in mlos_checks if "FAIL" in c["Status"])),
        ("Total MLoS Issue Rows",  len(mlos_detail)),
    ]
    for ri, (k, v) in enumerate(meta, 3):
        ka = ws.cell(row=ri, column=1, value=k); ka.font=bold_font; ka.border=bdr
        vb = ws.cell(row=ri, column=2, value=v); vb.font=body_font; vb.border=bdr; vb.alignment=lft
        if ri % 2 == 0: ka.fill=lgry_fill; vb.fill=lgry_fill

    ws.merge_cells("A14:B14")
    vd = ws["A14"]
    vd.value     = "✅  ALL CHECKS PASSED — File is CLEAN" if total_fail == 0 \
                   else f"❌  {total_fail} CHECK(S) FAILING — Review issue sheets"
    vd.fill      = PatternFill("solid", fgColor=GRN if total_fail==0 else RED)
    vd.font      = Font(bold=True, size=12, color=WHT, name="Calibri")
    vd.alignment = ctr
    ws.row_dimensions[14].height = 30

    # helper to write a QC summary sheet
    def write_summary(ws_s, title, checks_list):
        ws_s.sheet_view.showGridLines = False
        ws_s.merge_cells("A1:G1")
        ws_s["A1"].value     = title
        ws_s["A1"].font      = Font(bold=True, size=13, color=WHT, name="Calibri")
        ws_s["A1"].fill      = PatternFill("solid", fgColor=BLU)
        ws_s["A1"].alignment = ctr
        ws_s.row_dimensions[1].height = 30
        cols = ["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]
        hdr_row(ws_s, 2, cols)
        for ri, row in enumerate(checks_list, 3):
            is_fail = "FAIL" in row["Status"]
            for ci, key in enumerate(cols, 1):
                c = ws_s.cell(row=ri, column=ci, value=row[key])
                c.font=body_font; c.border=bdr
                c.alignment = ctr if ci in (1,2,5,6,7) else lft
                c.fill = fail_fill if is_fail else pass_fill
        for i, w in enumerate([14,8,32,65,14,12,9], 1):
            ws_s.column_dimensions[get_column_letter(i)].width = w

    # helper to write issue detail sheet
    def write_detail(ws_d, title, detail_df):
        ws_d.sheet_view.showGridLines = False
        if detail_df.empty:
            ws_d["A1"].value     = f"✅ No issues — {title} passed all checks"
            ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
            ws_d["A1"].fill      = PatternFill("solid", fgColor=GRN)
            ws_d["A1"].alignment = ctr
            return
        nc = len(detail_df.columns)
        ws_d.merge_cells(f"A1:{get_column_letter(nc)}1")
        ws_d["A1"].value     = title
        ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
        ws_d["A1"].fill      = PatternFill("solid", fgColor=RED)
        ws_d["A1"].alignment = ctr
        ws_d.row_dimensions[1].height = 26
        hdr_row(ws_d, 2, list(detail_df.columns))
        for ri, (_, row) in enumerate(detail_df.iterrows(), 3):
            for ci, v in enumerate(row.values, 1):
                c = ws_d.cell(row=ri, column=ci, value=v)
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = PatternFill("solid", fgColor="FFF5F5")
        for ci in range(1, nc+1):
            mx = max(len(str(detail_df.columns[ci-1])),
                     max((len(str(v)) for v in detail_df.iloc[:, ci-1].astype(str)), default=0))
            ws_d.column_dimensions[get_column_letter(ci)].width = min(max(mx+3, 12), 42)

    # helper to write raw data sheet
    def write_raw(ws_r, df):
        ws_r.sheet_view.showGridLines = False
        if df.empty: return
        hdr_row(ws_r, 1, list(df.columns))
        for ri, (_, row) in enumerate(df.iterrows(), 2):
            for ci, v in enumerate(row.values, 1):
                c = ws_r.cell(row=ri, column=ci, value=v)
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = lgry_fill
        for ci in range(1, len(df.columns)+1):
            ws_r.column_dimensions[get_column_letter(ci)].width = 18

    write_summary(wb.create_sheet("MLoS QC Summary"),       "MLoS Table — QC Check Summary",          mlos_checks)
    write_detail (wb.create_sheet("MLoS Issue Detail"),      "MLoS Table — Detailed Issue Rows",        mlos_detail)
    write_raw    (wb.create_sheet("Raw MLoS Data"),          mlos_df)

    wb.save(out)
    return out.getvalue()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
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
        st.session_state["submitted_key"] = (uploaded.name, getattr(uploaded, "size", None))
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
        """)
    with st.expander("📐 Settlement QC Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| SQ1 | settlement_name must be unique within each ward_code (case/extra spaces ignored) |
| SQ2 | latitude and longitude must not be null or missing |
| SQ2b | latitude and longitude must not be zero |
| SQ3 | No two settlements may share identical coordinates (stacked) |
| SQ4 | Nearest other settlement must not be < 20 m away (proximity cluster) |
| SQ5 | Nearest other settlement must not be 20–30 m away (proximity cluster) |
| SQ6 | Settlement must be on, or within 50 m of, a GRID3 settlement extent |
        """)
    with st.expander("🗺️ Boundary Check Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| B0 | ward_code is not null/empty on the uploaded data |
| B1 | ward_code exists in admin ward boundary reference (9,406 wards) |
| B2 | ward_code matches the ward boundary polygon the latitude/longitude falls in |
| B3 | state_name in MLoS matches the state_name assigned to that ward_code in the boundary reference |
        """)
    st.markdown("---")
    st.caption("eHealth Africa · MLOS QC Tool · v1.1")


# ─── HEADER ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🗺️ MLOS CHECKOUT QC</h1>
  <p>Master List of Settlements — Quality Control Dashboard &nbsp;|&nbsp; Upload your files and click ▶️ Run QC to begin</p>
</div>
""", unsafe_allow_html=True)

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
- 🏘️ **MLoS Rules** (1–12) — data integrity checks, including takeoffpoint vs. health facility
- 📐 **Settlement QC** (SQ1–SQ6) — duplicate, coordinate, stacking, proximity, and settlement extent checks
- 🗺️ **Boundary Checks** (B0–B3) — ward code, spatial ward match, and state name validation against admin boundary reference

**Outputs:**
- Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score on the dashboard
- Per-rule issue drilldown with downloadable Excel reports
- Full QC report (Excel) and email summary to the data team
        """)
    st.stop()

# ─── Determine submitted state ────────────────────────────────────────────────────
_current_key = (uploaded.name, getattr(uploaded, "size", None))
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔧 Auto Correct",
    "📊 QC Summary",
    "🏘️ MLoS Issues",
    "📐 Settlement QC",
    "🗺️ Boundary Issues",
    "🔍 Raw Data",
    "📄 Generate Report",
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
            f'{mlos_fail_rows + settlement_fail_rows + boundary_fail_rows} total issue rows. Fix before submission.</div>',
            unsafe_allow_html=True)

    # Metadata card
    gen_time      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mlos_n_fail   = sum(1 for c in mlos_checks       if "FAIL" in c["Status"])
    mlos_n_pass   = len(mlos_checks)   - mlos_n_fail
    sq_n_fail     = sum(1 for c in settlement_checks if "FAIL" in c["Status"])
    sq_n_pass     = len(settlement_checks) - sq_n_fail

    def rrow(lbl, val, cls="val"):
        return (f'<div class="report-row">'
                f'<span class="lbl">{lbl}</span>'
                f'<span class="{cls}">{val}</span>'
                f'</div>')

    html = "".join([
        rrow("📁 File",                    filename),
        rrow("🕐 Generated At",            gen_time),
        rrow("━" * 36,                     "", "val-div"),
        rrow("MLoS Rows",                  f"{len(mlos_df):,}"),
        rrow("━" * 36,                     "", "val-div"),
        rrow("MLoS Checks Run",            str(len(mlos_checks))),
        rrow("MLoS Checks ✅ Passing",     str(mlos_n_pass),  "val-pass"),
        rrow("MLoS Checks ❌ Failing",     str(mlos_n_fail),  "val-fail" if mlos_n_fail else "val-pass"),
        rrow("MLoS Issue Rows",            f"{mlos_fail_rows:,}",
                                            "val-fail" if mlos_fail_rows else "val-pass"),
        rrow("━" * 36,                     "", "val-div"),
        rrow("Settlement Checks Run",      str(len(settlement_checks))),
        rrow("Settlement Checks ✅ Passing", str(sq_n_pass),  "val-pass"),
        rrow("Settlement Checks ❌ Failing", str(sq_n_fail),  "val-fail" if sq_n_fail else "val-pass"),
        rrow("Settlement Issue Rows",      f"{settlement_fail_rows:,}",
                                            "val-fail" if settlement_fail_rows else "val-pass"),
    ])
    st.markdown(f'<div class="report-card">{html}</div>', unsafe_allow_html=True)

    # Two-column check breakdown
    col_a, col_b = st.columns(2)
    def hl(row):
        return (["color:#be123c; font-weight:700"] + [""]*4 if "FAIL" in str(row.get("Status",""))
                else ["color:#15803d; font-weight:700"] + [""]*4)
    with col_a:
        st.markdown("**🏘️ MLoS Check Breakdown**")
        tbl_m = pd.DataFrame([{"Status": c["Status"], "Rule#": c["Rule#"],
                                "QC Check": c["QC Check"], "Failing": c["Failing Rows"],
                                "Fail %": c["Fail %"]} for c in mlos_checks])
        st.dataframe(tbl_m.style.apply(hl, axis=1), use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("**📐 Settlement Check Breakdown**")
        tbl_sq = pd.DataFrame([{"Status": c["Status"], "Rule#": c["Rule#"],
                                 "QC Check": c["QC Check"], "Failing": c["Failing Rows"],
                                 "Fail %": c["Fail %"]} for c in settlement_checks])
        st.dataframe(tbl_sq.style.apply(hl, axis=1), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Download
    st.markdown("**📥 Download Full QC Report**")
    st.caption("4-sheet Excel report: Cover Page · MLoS QC Summary · MLoS Issue Detail · Raw MLoS Data")

    with st.spinner("Building Excel report…"):
        report_bytes = build_excel_report(filename, mlos_checks, mlos_detail, mlos_df)

    report_file = filename.replace(".sqlite","").replace(".db","") + "_QC_Report.xlsx"
    st.download_button(
        label   = "⬇️  Download Full QC Report (Excel)",
        data    = report_bytes,
        file_name = report_file,
        mime    = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type    = "primary",
    )

    if n_fail == 0:
        st.success("✅ File is CLEAN — all checks passed.")
    else:
        st.warning(f"⚠️ {n_fail} check(s) failing with "
                   f"{mlos_fail_rows + settlement_fail_rows + boundary_fail_rows} issue rows. "
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
