<!-- refreshed: 2026-09-09 -->
# Architecture

**Analysis Date:** 2026-09-09

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Sidebar: Upload Files → Run QC Button                │  │
│  │ 8 Tabs: AutoCorrect, Summary, Issues, Report         │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Data Loading & Format Detection Layer               │
│  `get_uploaded_data()` → Dispatch to format-specific loaders│
│  - SQLite: `load_sqlite()` → `load_view()`                  │
│  - Excel: `load_xlsx()` → Sheet name resolution             │
│  - CSV: `load_csv()` → Direct parse with `keep_default_na`  │
│  Result: mlos_df, takeoff_df                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Auto Correct Pre-Processing                      │
│  `auto_correct_mlos()` — 5 correction types                 │
│  - Flag columns: NULL → NA                                  │
│  - Scattered: NULL/NA → N                                   │
│  - Reason for Inaccessibility: NULL → NA (conditional)      │
│  - Source: NULL/empty → IE                                  │
│  - eha_guid: Strip braces, regenerate invalid UUIDs         │
│  Output: Corrected DataFrame + correction log               │
└────────────────────────┬────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼                ▼                    ▼
┌─────────┐          ┌─────────┐          ┌──────────┐      ┌──────────┐        ┌──────────┐
│ Schema  │          │ MLoS    │          │Settlement│      │Takeoff   │        │Boundary  │
│   QC    │          │ Table   │          │   QC     │      │   QC     │        │   QC     │
│  (2)    │          │  (14)   │          │  (4)     │      │  (4)     │        │  (4)     │
│         │          │         │          │          │      │          │        │          │
│Lines    │          │Lines    │          │Lines     │      │Lines     │        │Lines     │
│232-278  │          │805-965  │          │539-633   │      │969-1012  │        │383-536   │
└─────────┘          └─────────┘          └──────────┘      └──────────┘        └──────────┘
    │                    │                    │                  │                   │
    └────────────────────┴────────────────────┴──────────────────┴───────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │   Session State Caching     │
                    │   (Performance optimization)│
                    │   Checks + Details stored   │
                    └─────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            ┌──────────────────┐      ┌──────────────────────┐
            │  Excel Report    │      │   UI Display Layer   │
            │   Generation     │      │   (8 Streamlit Tabs) │
            │ `build_excel_    │      │                      │
            │  report()`, etc. │      │ Tab 1: Auto Correct  │
            │                  │      │ Tab 2: QC Summary    │
            │Lines 1015-1154   │      │ Tab 3: MLoS Issues   │
            │                  │      │ Tab 4: Settlement QC │
            │Styling with      │      │ Tab 5: Takeoff Issues│
            │openpyxl          │      │ Tab 6: Boundary      │
            │                  │      │ Tab 7: Raw Data      │
            └──────────────────┘      │ Tab 8: Generate Rpt  │
                    │                 └──────────────────────┘
                    ▼
            ┌──────────────────┐
            │  Email Sender    │
            │`send_qc_email()` │
            │  (Optional)      │
            │  Lines 636-692   │
            └──────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Data Loader | Format detection and file parsing (SQLite/Excel/CSV) | `app.py:104-204` |
| Auto Correct | Pre-QC data cleaning and standardization | `app.py:700-784` |
| Schema QC | Verify all required columns present (2 checks) | `app.py:232-278` |
| MLoS QC | 14 data integrity rules on MLoS table | `app.py:805-965` |
| Settlement QC | 4 spatial integrity checks (duplicates, coordinates, proximity) | `app.py:539-633` |
| Takeoffpoint QC | 4 cross-table consistency checks | `app.py:969-1012` |
| Boundary QC | 4 reference validation checks against 9,410-ward database | `app.py:383-536` |
| Report Builder | Generate styled Excel workbooks with multiple sheets | `app.py:1015-1154` |
| Email Sender | SMTP-based QC summary distribution | `app.py:636-692` |
| Streamlit UI | 8-tab dashboard for results visualization and file download | `app.py:1172-1962` |

## Pattern Overview

**Overall:** Sequential Quality Control Pipeline with Caching

**Key Characteristics:**
- **Single-file monolith** — All logic in `app.py` (1962 lines)
- **Functional QC engines** — Pure functions that take DataFrame, return (checks list, detail DataFrame)
- **Session state caching** — Results cached per file upload to avoid re-running QC
- **Pandas-based processing** — Vectorized operations with NumPy for performance (e.g., Haversine distance)
- **Format-agnostic input** — Detects file type and loads data into consistent DataFrame schema
- **Multi-layer redundancy** — Same data validated across 5 independent QC layers
- **Weighted scoring** — Each layer contributes proportionally to overall QC score

## Layers

**Data Input Layer:**
- Purpose: Accept files in 3 formats and normalize to DataFrame
- Location: `app.py:104-204` (load functions)
- Contains: `get_uploaded_data()`, `load_sqlite()`, `load_xlsx()`, `load_csv()`, `load_takeoffpoint_file()`
- Depends on: `streamlit`, `pandas`, `sqlite3`, `openpyxl`
- Used by: Main QC orchestration (line 1328-1343)

**Pre-Processing Layer:**
- Purpose: Auto-correct common data issues before QC validation
- Location: `app.py:700-784`
- Contains: `auto_correct_mlos()` (5 correction types)
- Depends on: `pandas`, `uuid`
- Used by: Line 1369 (pre-step before all QC)

**QC Engine Layer:**
- Purpose: Run 5 independent data validation layers sequentially
- Location: `app.py:232-1012` (5 functions)
- Contains:
  - `run_schema_qc()` — 2 schema checks
  - `run_mlos_qc()` — 14 data integrity rules
  - `run_settlement_qc()` — 4 spatial checks
  - `run_takeoff_qc()` — 4 cross-table checks
  - `run_ward_boundary_qc()` — 4 reference validation checks
- Depends on: `pandas`, `numpy` (for Haversine), boundary reference CSVs
- Output: Tuple of (checks list, detail DataFrame)

**Report & Export Layer:**
- Purpose: Generate downloadable Excel reports and email summaries
- Location: `app.py:280-296` (schema), `326-364` (longitudinal), `1015-1154` (full report), `636-692` (email)
- Contains:
  - `build_schema_report_xlsx()` — Schema error report
  - `build_longitudinal_mlos()` — Wide-format MLoS issues
  - `build_excel_report()` — 7-sheet comprehensive report
  - `send_qc_email()` — SMTP-based email notification
  - `build_corrected_excel()` — Auto-corrected data download
- Depends on: `openpyxl`, `smtplib`, `streamlit.secrets`
- Styling: PatternFill, Font, Alignment, Border via openpyxl

**UI/Presentation Layer:**
- Purpose: Display results and enable file downloads
- Location: `app.py:1172-1962`
- Contains:
  - Sidebar: File upload, Run QC button, rule reference
  - Header: Title and status
  - Metrics: 7-column metric row (rows, checks, pass/fail counts, scores)
  - Verdict banner: CLEAN or FAILING status
  - 8 tabs with dataframe displays and download buttons
- Depends on: `streamlit`, `pandas`

## Data Flow

### Primary Request Path

1. **User Interaction** — Upload file(s) and click "Run QC" (`app.py:1177-1203`)
2. **File Loading** — `get_uploaded_data()` detects format and parses to mlos_df, takeoff_df (`app.py:1328-1343`)
3. **Auto Correct** — `auto_correct_mlos()` cleans data; result stored in mlos_df (`app.py:1369-1374`)
4. **Schema Alignment** — `run_schema_qc()` checks for required columns (`app.py:1379-1383`)
5. **MLoS Validation** — `run_mlos_qc()` runs 14 data integrity rules (`app.py:1388-1392`)
6. **Settlement Checks** — `run_settlement_qc()` validates spatial integrity (`app.py:1397-1401`)
7. **Takeoffpoint Cross-checks** — `run_takeoff_qc()` if data available (`app.py:1410-1413`)
8. **Boundary Validation** — `run_ward_boundary_qc()` against 9,410-ward reference (`app.py:1419-1422`)
9. **Scoring** — Calculate layer pass rates and weighted score (`app.py:1449-1470`)
10. **Caching** — Store results in st.session_state for performance (`app.py:1427-1437`)
11. **Display** — Render tabs with results and download options (`app.py:1499-1962`)

### QC Engine Execution Pattern

Each QC engine (Schema, MLoS, Settlement, Takeoffpoint, Boundary) follows the same pattern:

```python
def run_XYZ_qc(data_df):
    checks = []      # List of check result dicts
    details = []     # List of failing row DataFrames
    total = len(data_df)
    
    # Helper function to standardize check recording
    def add(rule_num, rule_name, description, mask, extra_cols):
        n = int(mask.sum())
        checks.append({
            "Rule#": rule_num, "QC Check": rule_name,
            "Description": description, "Failing Rows": n,
            "Total Rows": total, "Fail %": pct(n, total),
            "Status": "❌ FAIL" if n else "✅ PASS"
        })
        if n:  # Only detail rows with failures
            details.append(failing_rows_df)
    
    # Apply individual rules
    add("R1", "Check Name", "Description", mask_expr, extra_cols)
    add("R2", "Check Name", "Description", mask_expr, extra_cols)
    
    return checks, pd.concat(details) if details else pd.DataFrame()
```

**State Management:**
- Session state (`st.session_state`) caches QC results per file upload
- Cache key: `(filename, file_size, takeoff_file_key)`
- Avoids re-running expensive 5-layer QC when switching tabs
- Progress bar tracks 5 steps (Pre + 5 layers)

### Secondary Flow: Report Generation & Email

1. User navigates to "Generate Report" tab
2. Click "Generate Report" → `build_excel_report()` creates 7-sheet workbook
3. (Optional) Click "Send QC Email" → `send_qc_email()` sends SMTP email
4. Results downloaded or emailed to data team

## Key Abstractions

**Check Dictionary:**
- Purpose: Standardized format for QC rule results
- Example: `{"Rule#": "1", "QC Check": "Required Fields", "Description": "...", "Failing Rows": 25, "Total Rows": 1000, "Fail %": "2.5%", "Status": "❌ FAIL"}`
- Used by: All QC engines, report builders, UI display

**Detail DataFrame:**
- Purpose: Row-level issue records for failed rules
- Columns: Always starts with `Rule#` and `Rule`, followed by relevant data columns + identifying columns (state, LGA, ward, settlement)
- Used by: Issue tabs, report generation, longitudinal view

**Boundary Reference Lookup:**
- Purpose: Fast O(1) ward code validation
- Data: `ward_boundary_ref.csv` (9,410 rows) + `ward_boundary_bbox.csv` (bounding boxes)
- Caching: `@st.cache_data` decorator on `load_boundary_refs()`
- Used by: `run_ward_boundary_qc()` (rules B0-B3)

**Haversine Distance Calculation:**
- Purpose: Detect settlements within 30m
- Pattern: Vectorized NumPy computation (radius = 6,371,000 m)
- Location: `app.py:614-627`
- Used by: Settlement QC Rule SQ4

**Weighted Score Formula:**
```
Schema × 10% + MLoS × 40% + Settlement × 20% + Takeoffpoint × 20% + Boundary × 10%
```
- If a layer has no checks (e.g., Takeoffpoint skipped), it receives 100% credit
- Result: Score from 0–100%

## Entry Points

**Web Entry Point:**
- Location: `app.py:1-20` (page config)
- Triggers: File upload via Streamlit uploader
- Responsibilities: Display sidebar, accept files, launch QC on button click

**Main Control Flow:**
- Location: `app.py:1282-1962`
- Conditions:
  - No upload → Show info and stop (`app.py:1290-1316`)
  - Upload but not submitted → Show "ready" message and stop (`app.py:1323-1325`)
  - Upload + submitted → Load, run QC, display results (`app.py:1328+`)

**Auto Correct Pre-Step:**
- Location: `app.py:1367-1374`
- Always runs before the 5 QC layers
- Results used by all downstream QC functions

**QC Layer Orchestration:**
- Location: `app.py:1364-1426`
- Runs 5 functions sequentially with progress tracking
- Caches results in session state
- Handles empty Takeoffpoint data gracefully (skips rules TP2-TP5)

## Architectural Constraints

- **Single file** — Monolithic design limits modularity and unit testing
- **Global state via session_state** — Caching tied to Streamlit session, not easily testable in isolation
- **Boundary reference files must exist** — `ward_boundary_ref.csv` and `ward_boundary_bbox.csv` must be in same directory as `app.py`; hard-coded paths (`app.py:367-368`)
- **Pandas dtype handling** — Uses `dtype=str` for all file loads + `keep_default_na=False` to preserve "NA" as string (not NaN)
- **Vectorized operations** — Some checks use pandas Series operations; Haversine distance uses NumPy loops
- **SMTP credentials in secrets** — Email requires `st.secrets` config (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`)

## Anti-Patterns

### Monolithic File

**What happens:** All code (1962 lines) in single file `app.py`

**Why it's wrong:** 
- Difficult to unit test individual QC functions
- Hard to reuse QC logic outside Streamlit context
- Single point of failure if app.py is corrupted
- Difficult to track responsibility boundaries

**Do this instead:** 
- Extract QC engines to `qc_engines.py` — Pure functions for each layer
- Extract report builders to `report_builders.py` — Decoupled from UI
- Extract loaders to `data_loaders.py` — Format-specific logic
- Import modules in `app.py` — Keep UI layer thin, orchestration only

### Redundant QC Check Pattern

**What happens:** Multiple QC engines use similar `add()` helper pattern repeated 5 times (lines 232, 805, 539, 969, 383)

**Why it's wrong:** 
- Copy-paste increases bug risk
- Changes to pattern require editing 5 functions
- No single source of truth for check structure

**Do this instead:** 
Create a shared `QCResult` dataclass or factory function:
```python
@dataclass
class QCResult:
    rule_num: str
    rule_name: str
    description: str
    failing_rows: int
    total_rows: int
    
    @property
    def fail_percent(self) -> str:
        return f"{self.failing_rows/self.total_rows*100:.1f}%"
    
    @property
    def status(self) -> str:
        return "❌ FAIL" if self.failing_rows else "✅ PASS"
```

### Hard-Coded Email Recipients

**What happens:** Email recipients (`TO`, `CC`) are hard-coded in `send_qc_email()` (`app.py:644-647`)

**Why it's wrong:**
- Cannot customize recipients without editing code
- Difficult to support multiple environments (dev/staging/prod)
- No audit trail of who receives emails

**Do this instead:** 
Store recipients in `st.secrets`:
```python
recipients = st.secrets.get("email_recipients", {})
TO = recipients.get("to", ["default@example.com"])
CC = recipients.get("cc", [])
```

### Boundary Reference File Paths Hard-Coded

**What happens:** Paths hard-coded at module level (`app.py:367-368`)

**Why it's wrong:**
- Fails if files moved or deployed differently
- No validation that files exist at startup
- Tests cannot mock file paths easily

**Do this instead:** 
Accept file paths as configuration:
```python
BOUNDARY_REF_PATH = os.path.join(
    os.environ.get("BOUNDARY_DATA_DIR", os.path.dirname(__file__)),
    "ward_boundary_ref.csv"
)
```

### Missing Null Coercion in Some Checks

**What happens:** Some rules use `.isin()` on string-converted values without consistent strip/lower (`app.py:884-892`)

**Why it's wrong:**
- Inconsistent error detection due to whitespace or case sensitivity
- Some rules strip before comparison, others don't
- May miss real errors

**Do this instead:** 
Create helper function:
```python
def normalize_string(series):
    return series.astype(str).str.strip().str.lower()
```
Apply consistently in all checks.

## Error Handling

**Strategy:** Graceful degradation at UI level

**Patterns:**
- File load errors → Display error message, don't stop QC (`app.py:1330-1334`)
- Takeoffpoint load failures → Skip TP rules with warning, continue QC (`app.py:1337-1343`)
- Missing boundary files → Boundary checks return empty (pre-checked with `os.path.exists`)
- SMTP failures → Display error with configuration guidance (`app.py:1954-1961`)
- Empty DataFrames → QC functions return empty results, UI handles gracefully

**No exceptions propagated to user** — All errors caught and converted to UI messages.

## Cross-Cutting Concerns

**Logging:** 
- Uses `st.write()` for progress logging during QC run (`app.py:1368+`)
- Progress bar updates for each of 5 QC layers
- Correction log printed as DataFrame

**Validation:**
- Schema validation (S1, S2) — Checks required columns
- Data validation (Rules 1-14, SQ1-SQ4, TP2-TP5, B0-B3) — 28 total rules
- Format validation — Regex for UUID, editor, date_of_activity

**Authentication:**
- No authentication layer
- SMTP credentials stored in Streamlit secrets (user responsibility)
- Email destinations hard-coded (requires code edit to change)

---

*Architecture analysis: 2026-09-09*
