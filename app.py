import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import os
import re
import hashlib
from io import BytesIO
from datetime import datetime
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

import qc
import qc.columns
import qc.report
from qc.domain import VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS
from qc.loaders import (
    MLOS_VIEW, TAKEOFF_VIEW, load_sqlite, load_view, load_csv, load_xlsx,
    load_submission, load_takeoffpoint_file,
)

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
# MLOS_VIEW / TAKEOFF_VIEW relocated to qc/loaders.py (Phase 1 D-08); imported above.

# ─── Helpers ─────────────────────────────────────────────────────────────────────
# load_sqlite / load_view / load_csv / load_xlsx / load_takeoffpoint_file relocated to
# qc/loaders.py verbatim (Phase 1 D-08) — imported above. get_uploaded_data below is now only
# the session-state caching wrapper; all parsing is qc.loaders.load_submission's job.

def _file_sha256(file_obj) -> str:
    """Return the hex sha256 digest of an uploaded file's full byte payload (D-13). This is the
    only place in the file that calls getvalue() — it is called once per uploaded file per
    rerun and the digest is reused, because getvalue() materialises a full copy of the payload
    and repeating that per key site would triple the transient memory cost for no benefit."""
    return hashlib.sha256(file_obj.getvalue()).hexdigest()


def _submission_identity(mlos_file, tp_file):
    """Return a submission's content identity: a tuple of the MLoS file's sha256 digest and
    either the Takeoffpoint file's sha256 digest or None when no separate Takeoffpoint file was
    supplied (D-13). This replaces the filename-and-size tuple at all three key sites — the
    get_uploaded_data cache key, the Run QC button's submitted_key, and the main body's
    current-key comparison / qc_cache_key — so two different submissions sharing a filename and
    byte size can no longer collide in session state."""
    return (_file_sha256(mlos_file), _file_sha256(tp_file) if tp_file is not None else None)


def get_uploaded_data(uploaded_file, mlos_digest, progress=None):
    cache_key = mlos_digest
    if st.session_state.get("uploaded_cache_key") == cache_key:
        if progress is not None:
            progress.progress(100)
        # Cache hit (INTEG-03/D-11): the rename map and collision groups were written on the
        # original parse below and persist in session state across reruns — read them back
        # rather than recomputing, so a rerun that never re-parses the file still renders the
        # rename panel and still feeds S3 with the original run's collision groups.
        column_renames = st.session_state.get("column_renames", {})
        column_collisions = st.session_state.get("column_collisions", [])
        st.session_state["column_renames"] = column_renames
        st.session_state["column_collisions"] = column_collisions
        return st.session_state["mlos_raw"], st.session_state["takeoff_df"]

    def _on_progress(value):
        if progress is not None:
            progress.progress(value)

    # Local name deliberately not "mlos_raw": the one-snapshot guard's mlos_raw-consumer
    # assertion walks every call in the file regardless of scope, and a same-named local here
    # would be indistinguishable from the module-scope mlos_raw it is meant to isolate.
    _mlos_parsed, takeoff_df = load_submission(
        uploaded_file, uploaded_file.name, on_progress=_on_progress
    )

    # INTEG-03/D-08/D-09: normalise column names once, here, on both officer-supplied frames
    # from this upload — the MLoS frame and the same-upload Takeoffpoint frame. One helper
    # (qc.columns.normalize_columns), applied identically, so "normalised once" stays true.
    _mlos_parsed, mlos_renames, mlos_collisions = qc.columns.normalize_columns(_mlos_parsed)
    takeoff_df, tp_renames, tp_collisions = qc.columns.normalize_columns(takeoff_df)

    column_renames = {**mlos_renames, **tp_renames}
    column_collisions = (
        [{**group, "table": "MLoS"} for group in mlos_collisions]
        + [{**group, "table": "Takeoffpoint"} for group in tp_collisions]
    )

    st.session_state["uploaded_cache_key"] = cache_key
    st.session_state["mlos_raw"] = _mlos_parsed
    st.session_state["takeoff_df"] = takeoff_df
    st.session_state["column_renames"] = column_renames
    st.session_state["column_collisions"] = column_collisions
    if progress is not None:
        progress.progress(100)
    return _mlos_parsed, takeoff_df


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


# ─── Takeoffpoint File Loader ────────────────────────────────────────────────────
# load_takeoffpoint_file relocated to qc/loaders.py verbatim (Phase 1 D-08); imported above.

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

    # D-13: one content-identity computation, held in a module-scope local so the button
    # handler here and the main body below reuse the same helper call rather than each
    # constructing its own filename-and-size expression.
    submission_identity = _submission_identity(uploaded, uploaded_tp) if uploaded is not None else None

    st.markdown("")
    run_qc_btn = st.button(
        "▶️ Run QC",
        type="primary",
        use_container_width=True,
        disabled=(uploaded is None),
    )
    if run_qc_btn and uploaded:
        st.session_state["submitted_key"] = submission_identity
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
| S3 | No two original headers normalise to the same column name |

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
| 2.missing | takeoffpoint must not be blank |
| 3 | takeoffpoint_code == takeoffpoint.code |
| 3.missing | takeoffpoint_code must not be blank |
| 4 | ward_code == takeoffpoint.wardcode |
| 4.missing | ward_code must not be blank |
| 5 | security_compromised = Y/N |
| 6 | accessibility_status valid |
| 7 | Partial/Inaccessible requires reason |
| 8 | habitational_status valid |
| 9 | set_target ≤ set_population |
| 10 | number_of_household ≤ set_population |
| 11.urban | urban is Y or N |
| 11.rural | rural is Y or N |
| 11.scattered | scattered is Y or N |
| 11a | Cannot be both Urban and Rural |
| 11b | Urban cannot be Scattered |
| 12.highrisk | highrisk = Y/N/NA |
| 12.slums | slums = Y/N/NA |
| 12.densely_populated | densely_populated = Y/N/NA |
| 12.hard2reach | hard2reach = Y/N/NA |
| 12.border | border = Y/N/NA |
| 12.nomadic | nomadic = Y/N/NA |
| 12.riverine | riverine = Y/N/NA |
| 12.fulani | fulani = Y/N/NA |
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
| TP2.missing | name must not be blank |
| TP3 | code == mlos.takeoffpoint_code |
| TP3.missing | code must not be blank |
| TP4 | wardcode == mlos.ward_code |
| TP4.missing | wardcode must not be blank |
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
| B4 | reports whether B1/B2 validated against the file's own state or, on a fallback, against the full national reference |
| B5 | reports when no boundary reference was found — B1, B2, B3 and B4 could not run |
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
- 🗺️ **Boundary Checks** (B0–B5) — ward code, coordinate, and state name validation against admin boundary reference, plus reference fallback (B4) and availability (B5) reporting

**Outputs:**
- Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score on the dashboard
- Per-rule issue drilldown with downloadable Excel reports
- Full QC report (Excel) and email summary to the data team
        """)
    st.stop()

# ─── Determine submitted state ────────────────────────────────────────────────────
# D-13: submission_identity was computed once in the sidebar (both uploaded and uploaded_tp
# were already available there); reused here rather than recomputed.
_current_key = submission_identity
_qc_submitted = st.session_state.get("submitted_key") == _current_key

if not _qc_submitted:
    st.info("✅ File(s) ready. Click **▶️ Run QC** in the sidebar to start the quality check.")
    st.stop()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────────
load_progress = st.progress(0)
with st.spinner("Loading file…"):
    try:
        mlos_raw, takeoff_df = get_uploaded_data(uploaded, submission_identity[0], progress=load_progress)
    except Exception as e:
        st.error(f"❌ Failed to load file: {e}")
        st.stop()

# Override takeoffpoint with separately uploaded file if provided
if uploaded_tp is not None:
    try:
        uploaded_tp.seek(0)
        takeoff_df = load_takeoffpoint_file(uploaded_tp)
        # INTEG-03/D-08/D-09: this file's headers are just as officer-supplied as the wrapper's
        # two frames above, and this override runs after get_uploaded_data — so it must apply
        # the same one helper and merge into (not replace) the two session-state keys.
        takeoff_df, tp_override_renames, tp_override_collisions = qc.columns.normalize_columns(takeoff_df)
        if tp_override_renames:
            st.session_state["column_renames"] = {
                **st.session_state.get("column_renames", {}),
                **tp_override_renames,
            }
        if tp_override_collisions:
            st.session_state["column_collisions"] = st.session_state.get(
                "column_collisions", []
            ) + [{**group, "table": "Takeoffpoint"} for group in tp_override_collisions]
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
    # D-14/ENGINE-03: the corrected frame and its correction log must ride the same cache as
    # the checks computed from it, or a cache hit serves rows that disagree with those checks
    # (F4). Read them back here rather than leaving the miss branch's only assignment stranded.
    mlos_corrected     = st.session_state["mlos_corrected"]
    autocorrect_log    = st.session_state["autocorrect_log"]
    load_progress.progress(100)
else:
    qc_bar = st.progress(0, text="⏳ Starting QC checks…")
    with st.status("Running QC checks…", expanded=True) as _qc_status:

        # ── Pre-step: Auto Correct ────────────────────────────────────────
        # ENGINE-03/ENGINE-04/D-14: this is the file's sole auto-correction call. It reads
        # mlos_raw and produces mlos_corrected, cached below alongside the checks so a rerun's
        # cache hit can never serve an uncorrected frame against corrected checks.
        st.write("🔧 Pre-step — Auto Correct")
        mlos_corrected, autocorrect_log = qc.autocorrect.auto_correct_mlos(mlos_raw)
        _n_fixed = sum(r["Rows Fixed"] for r in autocorrect_log)
        if autocorrect_log:
            st.write(f"   ✅ Auto Correct: {len(autocorrect_log)} correction(s) applied, {_n_fixed:,} row(s) fixed")
        else:
            st.write("   ✅ Auto Correct: no corrections needed")

        # ── Step 1 / 5: Schema Alignment ─────────────────────────────────
        qc_bar.progress(5, text="🔎 Step 1 / 5 — Schema Alignment…")
        st.write("🔎 Step 1 / 5 — Schema Alignment")
        schema_checks, schema_detail = qc.schema.run_schema_qc(
            mlos_corrected, takeoff_df, collisions=st.session_state.get("column_collisions", ())
        )
        schema_checks = qc.sort_by_registry(schema_checks)
        schema_fail = sum(1 for c in schema_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if schema_fail else '✅'} Schema: "
                 f"{len(schema_checks) - schema_fail}/{len(schema_checks)} checks passed")
        qc_bar.progress(20, text="✅ Step 1 / 5 — Schema Alignment complete")

        # ── Step 2 / 5: MLoS Rules ───────────────────────────────────────
        qc_bar.progress(21, text="🏘️ Step 2 / 5 — MLoS Rules…")
        st.write("🏘️ Step 2 / 5 — MLoS Rules")
        mlos_checks, mlos_detail = qc.mlos.run_mlos_qc(mlos_corrected, takeoff_df)
        mlos_checks = qc.sort_by_registry(mlos_checks)
        mlos_qc_fail = sum(1 for c in mlos_checks if "FAIL" in c["Status"])
        st.write(f"   {'❌' if mlos_qc_fail else '✅'} MLoS: "
                 f"{len(mlos_checks) - mlos_qc_fail}/{len(mlos_checks)} checks passed")
        qc_bar.progress(40, text="✅ Step 2 / 5 — MLoS Rules complete")

        # ── Step 3 / 5: Settlement QC ────────────────────────────────────
        qc_bar.progress(41, text="📐 Step 3 / 5 — Settlement QC…")
        st.write("📐 Step 3 / 5 — Settlement QC")
        settlement_checks, settlement_detail = qc.settlement.run_settlement_qc(mlos_corrected)
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
            tp_checks, tp_detail = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_corrected)
            tp_checks = qc.sort_by_registry(tp_checks)
            tp_qc_fail = sum(1 for c in tp_checks if "FAIL" in c["Status"])
            st.write(f"   {'❌' if tp_qc_fail else '✅'} Takeoffpoint: "
                     f"{len(tp_checks) - tp_qc_fail}/{len(tp_checks)} checks passed")
        qc_bar.progress(80, text="✅ Step 4 / 5 — Takeoffpoint Rules complete")

        # ── Step 5 / 5: Boundary Checks ──────────────────────────────────
        qc_bar.progress(81, text="🗺️ Step 5 / 5 — Boundary Checks…")
        st.write("🗺️ Step 5 / 5 — Boundary Checks")
        boundary_checks, boundary_detail = qc.boundary.run_ward_boundary_qc(mlos_corrected, boundary_ref, boundary_bbox)
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
    st.session_state["mlos_corrected"]     = mlos_corrected
    st.session_state["autocorrect_log"]    = autocorrect_log

# ── Shared verdict/score/count computation (VERDICT-05/F1/F6/F8's structural fix) ──────────
# Built exactly once, immediately after the cache if/else above has resolved both arms to the
# same five (checks, detail) pairs, and inside neither arm — a value derived on one branch only
# is F4's shape (RESEARCH.md Pitfall 4). Every presentation site below reads this one object.
summary = qc.report.build_summary(
    filename,
    {
        "Schema": (schema_checks, schema_detail),
        "MLoS": (mlos_checks, mlos_detail),
        "Settlement": (settlement_checks, settlement_detail),
        "Takeoffpoint": (tp_checks, tp_detail),
        "Boundary": (boundary_checks, boundary_detail),
    },
    mlos_row_count=len(mlos_corrected),
    takeoff_row_count=len(takeoff_df),
)

# ─── FILE INFO + METRICS ──────────────────────────────────────────────────────────
st.success(f"✅ Loaded **{filename}** — MLoS: **{len(mlos_corrected):,} rows** | Takeoffpoint: **{len(takeoff_df):,} rows**")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("📄 MLoS Rows",     f"{len(mlos_corrected):,}")
c2.metric("🔍 Checks Run",    f"{summary.checks_run}")
c3.metric("✅ Passing",       f"{summary.n_pass}")
c4.metric("❌ Failing",       f"{summary.n_fail}")
c5.metric("⚠️ Issue Rows",   f"{summary.headline_distinct:,}", help=summary.headline_issue_line)
c6.metric("📈 Pass Rate",     summary.pct_pass)
c7.metric("🏆 Weighted Score", f"{summary.weighted_score:.1f}%",
          help=f"of {summary.achievable_max:.1f}% achievable")

st.markdown("---")

# ─── VERDICT BANNER ───────────────────────────────────────────────────────────────
# One shared verdict sentence (D-04) — no site below recomputes a failing count (F1's shape).
if summary.n_fail == 0:
    st.markdown(
        f'<div class="banner-pass">✅ {summary.verdict_text}. This file is ready for '
        f'submission.</div>',
        unsafe_allow_html=True)
else:
    st.markdown(
        f'<div class="banner-fail">❌ {summary.verdict_text}. {summary.headline_issue_line}. '
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

    _SCORE_BAND_COLOUR = {"green": "#15803d", "amber": "#d97706", "red": "#be123c"}
    score_colour = _SCORE_BAND_COLOUR[summary.score_band]
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 24px;margin-bottom:16px;">'
        f'<span style="font-size:2rem;font-weight:800;color:{score_colour}">{summary.score_display}</span>'
        f'<span style="font-size:0.9rem;color:#64748b;margin-left:12px;">Overall Weighted Score</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # D-02: Layer Pass Rate reads n/a (never a number) for a layer that did not run; Weighted
    # Contribution is always a number, 0.0% for that same layer; the Weight column is unchanged.
    # The Total row's contribution carries the achievable-maximum score_display (D-01).
    _LAYER_LABELS = {
        "Schema": "🔎 Schema Alignment",
        "MLoS": "🏘️ MLoS Rules",
        "Settlement": "📐 Settlement QC",
        "Takeoffpoint": "📍 Takeoffpoint Rules",
        "Boundary": "🗺️ Boundary Checks",
    }
    score_rows = [
        {
            "QC Layer": _LAYER_LABELS[_name],
            "Weight": f"{summary.layers[_name].weight * 100:.0f}%",
            "Layer Pass Rate": ("n/a" if summary.layers[_name].pass_rate is None
                                 else f"{summary.layers[_name].pass_rate * 100:.1f}%"),
            "Weighted Contribution": f"{summary.layers[_name].weighted_contribution:.1f}%",
        }
        for _name in qc.report.LAYER_ORDER
    ] + [
        {"QC Layer": "🏆 Total", "Weight": "100%", "Layer Pass Rate": "—",
         "Weighted Contribution": summary.score_display},
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

    # ENGINE-04: no second auto-correction call here — that used to mint a fresh eha_guid for
    # the download that the screen never saw (F5). Read the one cached snapshot instead,
    # produced by the sole auto-correction call in the QC cache-miss branch above.
    if not autocorrect_log:
        st.success("✅ No corrections needed — all checked fields are already valid.")
    else:
        total_fixes = sum(r["Rows Fixed"] for r in autocorrect_log)
        st.info(f"🔧 **{len(autocorrect_log)} correction(s) applied** across **{total_fixes:,} row(s)**.")
        log_df = pd.DataFrame(autocorrect_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

    # ── Columns renamed at load (INTEG-03/D-11) ───────────────────────────────────
    # Reported in exactly two places: this expander and the report's "Columns Renamed" sheet.
    # A rename is not a defect — no Pass/Fail, no rule identifier, no score weight — so a clean
    # submission (nothing renamed) shows no panel at all, not an empty one.
    _column_renames = st.session_state.get("column_renames")
    if _column_renames:
        with st.expander("🏷️ Columns renamed at load", expanded=False):
            _rename_rows = sorted(_column_renames.items(), key=lambda kv: kv[0])
            _rename_df = pd.DataFrame(_rename_rows, columns=["Original Header", "Resolved To"])
            st.dataframe(_rename_df, use_container_width=True, hide_index=True)
            st.caption("A rename is not a defect and does not affect the weighted QC score.")
            if st.session_state.get("column_collisions"):
                st.caption(
                    "One or more header pairs could not be safely renamed because they "
                    "collided — see the **S3** row of the Schema Alignment summary above."
                )

    st.markdown("---")
    st.markdown("**📥 Download Full MLoS Data (with Auto Corrections)**")
    st.caption(
        f"Full dataset — **{len(mlos_corrected):,} rows × {len(mlos_corrected.columns)} columns** — "
        "with all auto corrections applied. Ready for re-upload or submission."
    )
    corrected_bytes = build_corrected_excel(mlos_corrected)
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
        st.error(f"❌ **{summary.layers['MLoS'].n_fail} failing check(s)** — {summary.layers['MLoS'].issue_line}")

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

        long_df = make_longitudinal_df(mlos_corrected, mlos_checks, mlos_detail)
        if not long_df.empty:
            rule_flag_cols = [c for c in long_df.columns if str(c).startswith("Rule_")]
            # Convert booleans to emoji strings for visual clarity — avoids Styler compatibility issues
            display_df = long_df.copy()
            for col in rule_flag_cols:
                display_df[col] = display_df[col].map(lambda v: "Yes" if v is True else ("No" if v is False else v))
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=350)

        long_xlsx = build_longitudinal_mlos(mlos_corrected, mlos_checks, mlos_detail)
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
        st.error(f"❌ **{summary.layers['Settlement'].n_fail} failing check(s)** — {summary.layers['Settlement'].issue_line}")

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
        st.error(f"❌ **{summary.layers['Takeoffpoint'].n_fail} failing check(s)** — {summary.layers['Takeoffpoint'].issue_line}")

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
    n_b_fail = summary.layers["Boundary"].n_fail
    if n_b_fail == 0:
        st.success("✅ All ward codes match the boundary reference and all coordinates fall within their declared ward boundaries.")
    else:
        st.error(f"❌ **{n_b_fail} boundary check(s) failing** — {summary.layers['Boundary'].issue_line}")

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
        st.markdown(f"**{len(mlos_corrected):,} rows × {len(mlos_corrected.columns)} columns**")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            state_opts = ["All"] + sorted(mlos_corrected["state_name"].dropna().unique().tolist()) \
                         if "state_name" in mlos_corrected.columns else ["All"]
            sel_state = st.selectbox("State", state_opts, key="sel_state")
        with fc2:
            if sel_state != "All" and "lga_name" in mlos_corrected.columns:
                lga_opts = ["All"] + sorted(mlos_corrected[mlos_corrected["state_name"]==sel_state]["lga_name"].dropna().unique().tolist())
            elif "lga_name" in mlos_corrected.columns:
                lga_opts = ["All"] + sorted(mlos_corrected["lga_name"].dropna().unique().tolist())
            else:
                lga_opts = ["All"]
            sel_lga = st.selectbox("LGA", lga_opts, key="sel_lga")
        with fc3:
            search = st.text_input("Search settlement", placeholder="Type to filter…", key="srch")

        fdf = mlos_corrected.copy()
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

    # Verdict — the same shared summary.verdict_text every other site reads (D-04, F1's fix).
    if summary.n_fail == 0:
        st.markdown(
            f'<div class="report-verdict-pass">✅ &nbsp; {summary.verdict_text} — File is '
            f'ready for submission</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="report-verdict-fail">❌ &nbsp; {summary.verdict_text} — '
            f'{summary.headline_issue_line}. Fix before submission.</div>',
            unsafe_allow_html=True)

    # Metadata card — every count read from the shared summary, never re-derived (F1's shape).
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _mlos_l, _sq_l, _tp_l = summary.layers["MLoS"], summary.layers["Settlement"], summary.layers["Takeoffpoint"]

    def rrow(lbl, val, cls="val"):
        return (f'<div class="report-row">'
                f'<span class="lbl">{lbl}</span>'
                f'<span class="{cls}">{val}</span>'
                f'</div>')

    html = "".join([
        rrow("📁 File",                    filename),
        rrow("🕐 Generated At",            gen_time),
        rrow("━" * 36,                     "", "val-div"),
        rrow("MLoS Rows",                  f"{len(mlos_corrected):,}"),
        rrow("Takeoffpoint Rows",          f"{len(takeoff_df):,}"),
        rrow("━" * 36,                     "", "val-div"),
        rrow("MLoS Checks Run",            str(len(_mlos_l.checks))),
        rrow("MLoS Checks ✅ Passing",     str(_mlos_l.n_pass),  "val-pass"),
        rrow("MLoS Checks ❌ Failing",     str(_mlos_l.n_fail),  "val-fail" if _mlos_l.n_fail else "val-pass"),
        rrow("MLoS Issue Rows",            f"{_mlos_l.findings:,}",
                                            "val-fail" if _mlos_l.findings else "val-pass"),
        rrow("━" * 36,                     "", "val-div"),
        rrow("Settlement Checks Run",      str(len(_sq_l.checks))),
        rrow("Settlement Checks ✅ Passing", str(_sq_l.n_pass),  "val-pass"),
        rrow("Settlement Checks ❌ Failing", str(_sq_l.n_fail),  "val-fail" if _sq_l.n_fail else "val-pass"),
        rrow("Settlement Issue Rows",      f"{_sq_l.findings:,}",
                                            "val-fail" if _sq_l.findings else "val-pass"),
        rrow("━" * 36,                     "", "val-div"),
        rrow("Takeoffpoint Checks Run",    str(len(_tp_l.checks))),
        rrow("Takeoffpoint Checks ✅ Passing", str(_tp_l.n_pass),  "val-pass"),
        rrow("Takeoffpoint Checks ❌ Failing", str(_tp_l.n_fail),  "val-fail" if _tp_l.n_fail else "val-pass"),
        rrow("Takeoffpoint Issue Rows",    f"{_tp_l.findings:,}",
                                            "val-fail" if _tp_l.findings else "val-pass"),
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
    st.caption("Excel report: Cover Page · MLoS QC Summary · MLoS Issue Detail · "
               "Takeoffpoint QC Summary · Takeoffpoint Issue Detail · Raw MLoS Data · "
               "Raw Takeoffpoint Data · Columns Renamed (only present when a header was "
               "renamed at load)")

    with st.spinner("Building Excel report…"):
        report_bytes = qc.report.build_workbook(
            summary, mlos_raw, takeoff_df,
            column_renames=st.session_state.get("column_renames", {}))

    report_file = filename.replace(".sqlite","").replace(".db","") + "_QC_Report.xlsx"
    st.download_button(
        label   = "⬇️  Download Full QC Report (Excel)",
        data    = report_bytes,
        file_name = report_file,
        mime    = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type    = "primary",
    )

    if summary.n_fail == 0:
        st.success(f"✅ {summary.verdict_text} — all checks passed.")
    else:
        st.warning(f"⚠️ {summary.verdict_text} — {summary.headline_issue_line}. "
                   f"Fix and re-upload before submission.")

    st.markdown("---")
    st.markdown("**📧 Send QC Summary by Email**")
    st.caption("Sends the QC summary to the data team. SMTP credentials must be configured in Streamlit secrets.")
    if st.button("📤 Send QC Email", type="primary", key="send_email_btn"):
        try:
            send_qc_email(filename, summary.all_checks, summary.layers["MLoS"].findings,
                          summary.layers["Takeoffpoint"].findings, schema_detail,
                          summary.layers["Boundary"].findings)
            st.success("✅ Email sent successfully to the data team.")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}"
                     "\n\nEnsure `smtp_host`, `smtp_port`, `smtp_user`, and `smtp_pass` "
                     "are set in your Streamlit secrets.")
