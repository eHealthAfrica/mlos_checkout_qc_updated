import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import os
import re
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import qc
from qc.domain import VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS

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
TAKEOFF_VIEW = "mlos_takeoffpoint_view"

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

def get_uploaded_data(uploaded_file, progress=None):
    cache_key = (uploaded_file.name, getattr(uploaded_file, "size", None))
    if st.session_state.get("uploaded_cache_key") == cache_key:
        if progress is not None:
            progress.progress(100)
        return st.session_state["mlos_df"], st.session_state["takeoff_df"]

    if progress is not None:
        progress.progress(10)

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()

    if ext in ("xlsx", "xls"):
        if progress is not None:
            progress.progress(35)
        mlos_df, takeoff_df = load_xlsx(uploaded_file)
        if progress is not None:
            progress.progress(90)
    elif ext == "csv":
        if progress is not None:
            progress.progress(35)
        mlos_df, takeoff_df = load_csv(uploaded_file)
        if progress is not None:
            progress.progress(90)
    else:
        conn, tmp_path = load_sqlite(uploaded_file)
        try:
            if progress is not None:
                progress.progress(35)
            mlos_df    = load_view(conn, MLOS_VIEW)
            if progress is not None:
                progress.progress(65)
            takeoff_df = load_view(conn, TAKEOFF_VIEW)
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
    st.session_state["takeoff_df"] = takeoff_df
    if progress is not None:
        progress.progress(100)
    return mlos_df, takeoff_df


# ─── Schema QC ───────────────────────────────────────────────────────────────────
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
            failing_idx = set(mlos_detail.loc[mlos_detail["Rule#"] == rn].index)
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
BOUNDARY_BBOX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ward_boundary_bbox.csv")

@st.cache_data(show_spinner=False)
def load_boundary_refs():
    """Load ward code reference and bounding box lookup tables."""
    # keep_default_na=False prevents pandas from converting the string "NA"
    # (the state_code for Nasarawa) into NaN, which would break state filtering.
    ref_df  = pd.read_csv(BOUNDARY_REF_PATH,  dtype=str, keep_default_na=False) if os.path.exists(BOUNDARY_REF_PATH)  else pd.DataFrame()
    bbox_df = pd.read_csv(BOUNDARY_BBOX_PATH, dtype=str, keep_default_na=False) if os.path.exists(BOUNDARY_BBOX_PATH) else pd.DataFrame()
    for col in ["min_lon","min_lat","max_lon","max_lat"]:
        if col in bbox_df.columns:
            bbox_df[col] = pd.to_numeric(bbox_df[col], errors="coerce")
    return ref_df, bbox_df

# ─── Email Sender ─────────────────────────────────────────────────────────────────
def send_qc_email(filename: str, all_checks: list, mlos_fail_rows: int,
                  tp_fail_rows: int, schema_detail: pd.DataFrame,
                  boundary_fail_rows: int):
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
Takeoffpoint Issue Rows: {tp_fail_rows:,}
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


# ─── Excel Report Builder ─────────────────────────────────────────────────────────
def build_excel_report(filename, mlos_checks, mlos_detail, tp_checks, tp_detail,
                        mlos_df, takeoff_df):
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

    total_fail = (sum(1 for c in mlos_checks if "FAIL" in c["Status"]) +
                  sum(1 for c in tp_checks   if "FAIL" in c["Status"]))

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
        ("Takeoffpoint Rows",      len(takeoff_df)),
        ("MLoS Checks Run",        len(mlos_checks)),
        ("MLoS Checks Failing",    sum(1 for c in mlos_checks if "FAIL" in c["Status"])),
        ("TP Checks Run",          len(tp_checks)),
        ("TP Checks Failing",      sum(1 for c in tp_checks   if "FAIL" in c["Status"])),
        ("Total MLoS Issue Rows",  len(mlos_detail)),
        ("Total TP Issue Rows",    len(tp_detail)),
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
    write_summary(wb.create_sheet("Takeoffpoint QC Summary"),"Takeoffpoint Table — QC Check Summary",   tp_checks)
    write_detail (wb.create_sheet("Takeoffpoint Issue Detail"),"Takeoffpoint Table — Detailed Issues",  tp_detail)
    write_raw    (wb.create_sheet("Raw MLoS Data"),          mlos_df)
    write_raw    (wb.create_sheet("Raw Takeoffpoint Data"),  takeoff_df)

    wb.save(out)
    return out.getvalue()


# ─── Takeoffpoint File Loader ────────────────────────────────────────────────────
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

    st.markdown("**Takeoffpoint File** *(optional)*")
    uploaded_tp = st.file_uploader(
        "Upload Takeoffpoint file",
        type=["csv", "xlsx", "xls"],
        key="tp_upload", label_visibility="collapsed",
    )
    st.caption("Upload separately when MLoS file is `.csv`, or to override the built-in takeoffpoint sheet.")

    st.markdown("")
    run_qc_btn = st.button(
        "▶️ Run QC",
        type="primary",
        use_container_width=True,
        disabled=(uploaded is None),
    )
    if run_qc_btn and uploaded:
        tp_key = (uploaded_tp.name, getattr(uploaded_tp, "size", None)) if uploaded_tp else None
        st.session_state["submitted_key"] = (
            uploaded.name, getattr(uploaded, "size", None), tp_key
        )
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
| S2 | All 4 required Takeoffpoint columns present |

**MLoS required columns:**
`state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `takeoffpoint`, `takeoffpoint_code`, `settlement_name`, `primarysettlement_name`, `alternate_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `reasons_for_inaccessibility`, `habitational_status`, `set_population`, `set_target`, `number_of_household`, `noncompliant_household`, `team_code`, `day_of_activity`, `urban`, `rural`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `scattered`, `riverine`, `fulani`, `timestamp`, `source`, `last_updated`, `editor`, `validation_status`, `master_id`, `mlos_id`, `eha_guid`, `settlementarea_globalid`

**Takeoffpoint required columns:**
`name`, `code`, `wardcode`, `globalid`
        """)
    with st.expander("🏘️ MLoS Table Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| 1 | All schema NOT NULL fields must not be null (`state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `settlement_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `set_population`, `set_target`, `number_of_household`, `urban`, `rural`, `scattered`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani`, `timestamp`, `eha_guid`, `settlementarea_globalid`) |
| 2 | takeoffpoint == takeoffpoint.name |
| 3 | takeoffpoint_code == takeoffpoint.code |
| 4 | ward_code == takeoffpoint.wardcode |
| 5 | security_compromised = Y/N |
| 6 | accessibility_status valid |
| 7 | Partial/Inaccessible requires reason |
| 8 | habitational_status valid |
| 9 | set_target ≤ set_population |
| 10 | number_of_household ≤ set_population |
| 11 | urban/rural/scattered = Y/N (no conflict) |
| 12 | Profile flags = Y/N/NA (highrisk, slums, densely_populated, hard2reach, border, nomadic, riverine, fulani) |
| 13 | editor = firstname.surname (lowercase) |
| 14 | eha_guid = valid UUID |
        """)
    with st.expander("📐 Settlement QC Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| SQ1 | settlement_name must be unique within each ward_code |
| SQ2 | latitude and longitude must not be null or missing |
| SQ2b | latitude and longitude must not be zero |
| SQ3 | No two settlements may share identical coordinates (stacked) |
| SQ4 | Every settlement must be > 30 m from every other settlement |
        """)
    with st.expander("📍 Takeoffpoint Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| TP2 | name == mlos.takeoffpoint |
| TP3 | code == mlos.takeoffpoint_code |
| TP4 | wardcode == mlos.ward_code |
| TP5 | globalid = valid UUID |
        """)
    with st.expander("🗺️ Boundary Check Rules", expanded=False):
        st.markdown("""
| Rule | Check |
|------|-------|
| B0 | ward_code is not null/empty on the uploaded data |
| B1 | ward_code exists in admin ward boundary reference (9,410 wards) |
| B2 | latitude/longitude falls within the bounding box of the declared ward_code |
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
    st.info("👈 **Upload your MLoS file** (and optionally a Takeoffpoint file) using the sidebar, then click **▶️ Run QC**.")
    with st.expander("ℹ️ About this tool", expanded=True):
        st.markdown("""
This tool runs automated Quality Control on MLOS checkout files across **4 QC layers**.

**Supported formats:**
- **SQLite** (`.sqlite`, `.db`) — reads MLoS and Takeoffpoint views directly
- **Excel** (`.xlsx`, `.xls`) — Sheet 1 = MLoS, Sheet 2 = Takeoffpoint
- **CSV** (`.csv`) — MLoS data only; upload a separate Takeoffpoint file to enable cross-checks

**Takeoffpoint file (separate upload):**
Upload a `.csv` or `.xlsx` Takeoffpoint file alongside any MLoS format.
It overrides the built-in Takeoffpoint sheet for Excel/SQLite files.

**QC Layers:**
- 🔎 **Schema Alignment** (S1–S2) — verifies all required columns are present
- 🏘️ **MLoS Rules** (2–17) — data integrity checks
- 📍 **Takeoffpoint Rules** (TP2–TP5) — 4 cross-table checks
- 🗺️ **Boundary Checks** (B0–B3) — ward code, coordinate, and state name validation against admin boundary reference

**Outputs:**
- Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score on the dashboard
- Per-rule issue drilldown with downloadable Excel reports
- Full QC report (Excel) and email summary to the data team
        """)
    st.stop()

# ─── Determine submitted state ────────────────────────────────────────────────────
_tp_key = (uploaded_tp.name, getattr(uploaded_tp, "size", None)) if uploaded_tp else None
_current_key = (uploaded.name, getattr(uploaded, "size", None), _tp_key)
_qc_submitted = st.session_state.get("submitted_key") == _current_key

if not _qc_submitted:
    st.info("✅ File(s) ready. Click **▶️ Run QC** in the sidebar to start the quality check.")
    st.stop()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────────
load_progress = st.progress(0)
with st.spinner("Loading file…"):
    try:
        mlos_df, takeoff_df = get_uploaded_data(uploaded, progress=load_progress)
    except Exception as e:
        st.error(f"❌ Failed to load file: {e}")
        st.stop()

# Override takeoffpoint with separately uploaded file if provided
if uploaded_tp is not None:
    try:
        uploaded_tp.seek(0)
        takeoff_df = load_takeoffpoint_file(uploaded_tp)
    except Exception as e:
        st.warning(f"⚠️ Could not load Takeoffpoint file: {e} — takeoffpoint cross-checks will be skipped.")
        takeoff_df = pd.DataFrame()

filename = uploaded.name

# ─── RUN QC ───────────────────────────────────────────────────────────────────────
qc_cache_key = _current_key
boundary_ref, boundary_bbox = load_boundary_refs()

if st.session_state.get("qc_cache_key") == qc_cache_key:
    schema_checks      = st.session_state["schema_checks"]
    schema_detail      = st.session_state["schema_detail"]
    mlos_checks        = st.session_state["mlos_checks"]
    mlos_detail        = st.session_state["mlos_detail"]
    settlement_checks  = st.session_state["settlement_checks"]
    settlement_detail  = st.session_state["settlement_detail"]
    tp_checks          = st.session_state["tp_checks"]
    tp_detail          = st.session_state["tp_detail"]
    boundary_checks    = st.session_state["boundary_checks"]
    boundary_detail    = st.session_state["boundary_detail"]
    load_progress.progress(100)
else:
    qc_bar = st.progress(0, text="⏳ Starting QC checks…")
    with st.status("Running QC checks…", expanded=True) as _qc_status:

        # ── Pre-step: Auto Correct ────────────────────────────────────────
        st.write("🔧 Pre-step — Auto Correct")
        mlos_df, _ac_log = qc.autocorrect.auto_correct_mlos(mlos_df)
        _n_fixed = sum(r["Rows Fixed"] for r in _ac_log)
        if _ac_log:
            st.write(f"   ✅ Auto Correct: {len(_ac_log)} correction(s) applied, {_n_fixed:,} row(s) fixed")
        else:
            st.write("   ✅ Auto Correct: no corrections needed")

        # ── Step 1 / 5: Schema Alignment ─────────────────────────────────
        qc_bar.progress(5, text="🔎 Step 1 / 5 — Schema Alignment…")
        st.write("🔎 Step 1 / 5 — Schema Alignment")
        schema_checks, schema_detail = qc.schema.run_schema_qc(mlos_df, takeoff_df)
        schema_checks = qc.sort_by_registry(schema_checks)
        schema_fail = sum(1 for c in schema_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if schema_fail else '✅'} Schema: "
                 f"{len(schema_checks) - schema_fail}/{len(schema_checks)} checks passed")
        qc_bar.progress(20, text="✅ Step 1 / 5 — Schema Alignment complete")

        # ── Step 2 / 5: MLoS Rules ───────────────────────────────────────
        qc_bar.progress(21, text="🏘️ Step 2 / 5 — MLoS Rules…")
        st.write("🏘️ Step 2 / 5 — MLoS Rules")
        mlos_checks, mlos_detail = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
        mlos_checks = qc.sort_by_registry(mlos_checks)
        mlos_qc_fail = sum(1 for c in mlos_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if mlos_qc_fail else '✅'} MLoS: "
                 f"{len(mlos_checks) - mlos_qc_fail}/{len(mlos_checks)} checks passed")
        qc_bar.progress(40, text="✅ Step 2 / 5 — MLoS Rules complete")

        # ── Step 3 / 5: Settlement QC ────────────────────────────────────
        qc_bar.progress(41, text="📐 Step 3 / 5 — Settlement QC…")
        st.write("📐 Step 3 / 5 — Settlement QC")
        settlement_checks, settlement_detail = qc.settlement.run_settlement_qc(mlos_df)
        settlement_checks = qc.sort_by_registry(settlement_checks)
        sq_fail = sum(1 for c in settlement_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if sq_fail else '✅'} Settlement: "
                 f"{len(settlement_checks) - sq_fail}/{len(settlement_checks)} checks passed")
        qc_bar.progress(60, text="✅ Step 3 / 5 — Settlement QC complete")

        # ── Step 4 / 5: Takeoffpoint Rules ───────────────────────────────
        qc_bar.progress(61, text="📍 Step 4 / 5 — Takeoffpoint Rules…")
        st.write("📍 Step 4 / 5 — Takeoffpoint Rules")
        if takeoff_df.empty:
            tp_checks, tp_detail = [], pd.DataFrame()
            st.write("   ⚠️ Takeoffpoint data not available — skipped")
        else:
            tp_checks, tp_detail = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df)
            tp_checks = qc.sort_by_registry(tp_checks)
            tp_qc_fail = sum(1 for c in tp_checks if "FAIL" in c["Status"])
            st.write(f"   {'❌' if tp_qc_fail else '✅'} Takeoffpoint: "
                     f"{len(tp_checks) - tp_qc_fail}/{len(tp_checks)} checks passed")
        qc_bar.progress(80, text="✅ Step 4 / 5 — Takeoffpoint Rules complete")

        # ── Step 5 / 5: Boundary Checks ──────────────────────────────────
        qc_bar.progress(81, text="🗺️ Step 5 / 5 — Boundary Checks…")
        st.write("🗺️ Step 5 / 5 — Boundary Checks")
        boundary_checks, boundary_detail = qc.boundary.run_ward_boundary_qc(mlos_df, boundary_ref, boundary_bbox)
        boundary_checks = qc.sort_by_registry(boundary_checks)
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
    st.session_state["tp_checks"]          = tp_checks
    st.session_state["tp_detail"]          = tp_detail
    st.session_state["boundary_checks"]    = boundary_checks
    st.session_state["boundary_detail"]    = boundary_detail

all_checks         = schema_checks + mlos_checks + settlement_checks + tp_checks + boundary_checks
n_fail             = sum(1 for c in all_checks if "FAIL" in c["Status"])
n_pass             = len(all_checks) - n_fail
pct_pass           = f"{n_pass / len(all_checks) * 100:.1f}%" if all_checks else "0%"
pct_fail           = f"{n_fail / len(all_checks) * 100:.1f}%" if all_checks else "0%"
mlos_fail_rows     = len(mlos_detail)
settlement_fail_rows = len(settlement_detail)
tp_fail_rows       = len(tp_detail)
boundary_fail_rows = len(boundary_detail)

# ── Weighted Score ───────────────────────────────────────────────────────────────
# Schema 10% | MLoS 40% | Settlement 20% | Takeoffpoint 20% | Boundary 10%
LAYER_WEIGHTS = {
    "schema":     0.10,
    "mlos":       0.40,
    "settlement": 0.20,
    "tp":         0.20,
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
tp_score         = _layer_pass_rate(tp_checks)       * LAYER_WEIGHTS["tp"]         * 100
boundary_score   = _layer_pass_rate(boundary_checks) * LAYER_WEIGHTS["boundary"]   * 100
weighted_score   = schema_score + mlos_score + settlement_score + tp_score + boundary_score

# ─── FILE INFO + METRICS ──────────────────────────────────────────────────────────
st.success(f"✅ Loaded **{filename}** — MLoS: **{len(mlos_df):,} rows** | Takeoffpoint: **{len(takeoff_df):,} rows**")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("📄 MLoS Rows",     f"{len(mlos_df):,}")
c2.metric("🔍 Checks Run",    f"{len(all_checks)}")
c3.metric("✅ Passing",       f"{n_pass}")
c4.metric("❌ Failing",       f"{n_fail}")
c5.metric("⚠️ Issue Rows",   f"{mlos_fail_rows + settlement_fail_rows + tp_fail_rows + boundary_fail_rows:,}")
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
        f'{tp_fail_rows} Takeoffpoint rows, and {boundary_fail_rows} Boundary rows have issues. '
        f'Review details below before submission.</div>',
        unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔧 Auto Correct",
    "📊 QC Summary",
    "🏘️ MLoS Issues",
    "📐 Settlement QC",
    "📍 Takeoffpoint Issues",
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
        {"QC Layer": "🏘️ MLoS Rules",        "Weight": "40%", "Layer Pass Rate": f"{_layer_pass_rate(mlos_checks)*100:.1f}%",       "Weighted Contribution": f"{mlos_score:.1f}%"},
        {"QC Layer": "📐 Settlement QC",      "Weight": "20%", "Layer Pass Rate": f"{_layer_pass_rate(settlement_checks)*100:.1f}%", "Weighted Contribution": f"{settlement_score:.1f}%"},
        {"QC Layer": "📍 Takeoffpoint Rules", "Weight": "20%", "Layer Pass Rate": f"{_layer_pass_rate(tp_checks)*100:.1f}%",         "Weighted Contribution": f"{tp_score:.1f}%"},
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
    st.markdown('<div class="sec-title">📍 Takeoffpoint Table — QC Results</div>', unsafe_allow_html=True)
    if tp_checks:
        df_t = pd.DataFrame(tp_checks)[["Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]]
        st.dataframe(df_t.style.apply(colour_rows, axis=1), use_container_width=True, hide_index=True)

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

    corrected_df, correction_log = qc.autocorrect.auto_correct_mlos(mlos_df)

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
            subset = mlos_detail[mlos_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
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

# ── Tab 5: Takeoffpoint Issues ────────────────────────────────────────────────────
with tab5:
    if tp_detail.empty:
        st.success("✅ No issues found in the Takeoffpoint table — all checks passed!")
    else:
        n_failing_tp = sum(1 for c in tp_checks if "FAIL" in c["Status"])
        st.error(f"❌ **{tp_fail_rows:,} issue row(s)** across **{n_failing_tp} failing check(s)**")

        for check in tp_checks:
            if "FAIL" not in check["Status"]: continue
            rn     = check["Rule#"]
            subset = tp_detail[tp_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
            n      = len(subset)
            with st.expander(f"❌  Rule {rn} — {check['QC Check']}  ({n:,} row{'s' if n!=1 else ''})", expanded=False):
                st.caption(f"📌 {check['Description']}")
                st.dataframe(subset, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**📋 All Takeoffpoint Issue Rows (combined)**")
        st.dataframe(tp_detail, use_container_width=True, hide_index=True, height=350)

        buf2 = BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as xw:
            tp_detail.to_excel(xw, sheet_name="All Issues", index=False)
            for check in tp_checks:
                if "FAIL" not in check["Status"]: continue
                rn  = check["Rule#"]
                sub = tp_detail[tp_detail["Rule#"] == rn].drop(columns=["Rule#","Rule"], errors="ignore")
                sub.to_excel(xw, sheet_name=f"Rule {rn}"[:31], index=False)
        st.download_button("⬇️ Download Takeoffpoint Issues (Excel)", data=buf2.getvalue(),
                           file_name=filename.replace(".sqlite","")+"_tp_issues.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Tab 6: Boundary Issues ────────────────────────────────────────────────────────
with tab6:
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

# ── Tab 7: Raw Data ───────────────────────────────────────────────────────────────
with tab7:
    rt1, rt2 = st.tabs(["🏘️ MLoS View", "📍 Takeoffpoint View"])
    with rt1:
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

    with rt2:
        st.markdown(f"**{len(takeoff_df):,} rows × {len(takeoff_df.columns)} columns**")
        st.dataframe(takeoff_df, use_container_width=True, hide_index=True, height=420)

# ── Tab 8: Generate Report ────────────────────────────────────────────────────────
with tab8:
    st.markdown('<div class="sec-title">📄 QC Report — Summary &amp; Download</div>', unsafe_allow_html=True)

    # Verdict
    if n_fail == 0:
        st.markdown(
            '<div class="report-verdict-pass">✅ &nbsp; ALL CHECKS PASSED — File is CLEAN and ready for submission</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="report-verdict-fail">❌ &nbsp; {n_fail} CHECK(S) FAILING — '
            f'{mlos_fail_rows + settlement_fail_rows + tp_fail_rows + boundary_fail_rows} total issue rows. Fix before submission.</div>',
            unsafe_allow_html=True)

    # Metadata card
    gen_time      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mlos_n_fail   = sum(1 for c in mlos_checks       if "FAIL" in c["Status"])
    mlos_n_pass   = len(mlos_checks)   - mlos_n_fail
    sq_n_fail     = sum(1 for c in settlement_checks if "FAIL" in c["Status"])
    sq_n_pass     = len(settlement_checks) - sq_n_fail
    tp_n_fail     = sum(1 for c in tp_checks         if "FAIL" in c["Status"])
    tp_n_pass     = len(tp_checks)     - tp_n_fail

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
        rrow("Takeoffpoint Rows",          f"{len(takeoff_df):,}"),
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
        rrow("━" * 36,                     "", "val-div"),
        rrow("Takeoffpoint Checks Run",    str(len(tp_checks))),
        rrow("Takeoffpoint Checks ✅ Passing", str(tp_n_pass),  "val-pass"),
        rrow("Takeoffpoint Checks ❌ Failing", str(tp_n_fail),  "val-fail" if tp_n_fail else "val-pass"),
        rrow("Takeoffpoint Issue Rows",    f"{tp_fail_rows:,}",
                                            "val-fail" if tp_fail_rows else "val-pass"),
    ])
    st.markdown(f'<div class="report-card">{html}</div>', unsafe_allow_html=True)

    # Three-column check breakdown
    col_a, col_b, col_c = st.columns(3)
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

    with col_c:
        st.markdown("**📍 Takeoffpoint Check Breakdown**")
        tbl_t = pd.DataFrame([{"Status": c["Status"], "Rule#": c["Rule#"],
                                "QC Check": c["QC Check"], "Failing": c["Failing Rows"],
                                "Fail %": c["Fail %"]} for c in tp_checks])
        st.dataframe(tbl_t.style.apply(hl, axis=1), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Download
    st.markdown("**📥 Download Full QC Report**")
    st.caption("7-sheet Excel report: Cover Page · MLoS QC Summary · MLoS Issue Detail · "
               "Takeoffpoint QC Summary · Takeoffpoint Issue Detail · Raw MLoS Data · Raw Takeoffpoint Data")

    with st.spinner("Building Excel report…"):
        report_bytes = build_excel_report(
            filename, mlos_checks, mlos_detail,
            tp_checks, tp_detail, mlos_df, takeoff_df)

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
                   f"{mlos_fail_rows + settlement_fail_rows + tp_fail_rows + boundary_fail_rows} issue rows. "
                   f"Fix and re-upload before submission.")

    st.markdown("---")
    st.markdown("**📧 Send QC Summary by Email**")
    st.caption("Sends the QC summary to the data team. SMTP credentials must be configured in Streamlit secrets.")
    if st.button("📤 Send QC Email", type="primary", key="send_email_btn"):
        try:
            send_qc_email(filename, all_checks, mlos_fail_rows,
                          tp_fail_rows, schema_detail, boundary_fail_rows)
            st.success("✅ Email sent successfully to the data team.")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}"
                     "\n\nEnsure `smtp_host`, `smtp_port`, `smtp_user`, and `smtp_pass` "
                     "are set in your Streamlit secrets.")
