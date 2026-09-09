<!-- GSD:project-start source:PROJECT.md -->

## Project

**MLoS Checkout QC**

A quality-control tool for Master List of Settlements (MLoS) checkout files. State-level
data officers upload a settlement submission — as `.sqlite`, `.csv` or `.xlsx` — and the
tool runs it against schema, data-integrity, cross-table and administrative-boundary rules,
returning a pass/fail verdict, a weighted score, and a per-rule Excel report they can act on.

Today it runs locally for one person. The target is a single central deployment that officers
in every state reach directly, with more QC layers than it has now.

**Core Value:** **A file this tool calls clean is clean.**

Everything else — the score, the dashboard, the drilldowns, the email — is subordinate to the
verdict being trustworthy. When a tradeoff arises, correctness of the reported verdict wins
over features, speed, or presentation.

### Constraints

- **Tech stack**: Python 3 + Streamlit — Keeping both. No audited defect is framework-caused, and a rewrite would discard working rule logic.
- **Hosting**: Free tier only, on Hugging Face Spaces — Chosen over Streamlit Community Cloud because the free CPU tier offers roughly 16 GB RAM against ~1 GB. SQ4 is quadratic and the Excel report builder is memory-hungry, so the headroom is load-bearing, not luxury.
- **Storage**: A Space's filesystem is ephemeral — Anything that must survive a rebuild or idle restart goes to a private HF Dataset repo. A local SQLite of accounts or logs would be silently wiped.
- **Security**: No passwords stored by this application — Identity comes from an OIDC provider. SMTP credentials and the recipient list live in Space secrets and are never committed.
- **Privacy**: Settlement coordinates and population figures — The Space must be private. This is why hosting choice is a governance question and not only a technical one.
- **Configuration**: Plausibility and coverage thresholds are rules of thumb, not a published standard — They must live in configuration and be tunable without a code change, so a wrong threshold is a settings edit rather than a deploy.
- **Compatibility**: A verdict must not depend on upload format — `.sqlite`, `.csv` and `.xlsx` exports of the same data must produce identical check summaries. Three audited defects currently violate this.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.x - Core application language for all QC logic and data processing

## Runtime

- Python 3 (version unspecified in requirements.txt)
- pip
- Lockfile: `requirements.txt` (present, pinned to minimum versions with `>=`)

## Frameworks

- Streamlit 1.32.0+ - Web application framework for interactive QC dashboard and UI
- pandas 2.0.0+ - Data manipulation, CSV/Excel loading, DataFrame operations
- openpyxl 3.1.0+ - Excel workbook generation and styling (report export, corrected file output)
- xlrd 2.0.1+ - XLS file reading support (legacy Excel format compatibility)
- None detected

## Key Dependencies

- pandas 2.0.0+ - Powers all data loading, validation, filtering, and export operations
- Streamlit 1.32.0+ - Provides interactive UI, session state management, and file upload handling
- openpyxl 3.1.0+ - Generates formatted Excel reports with styling (borders, fills, fonts, alignment)
- numpy - Imported conditionally in spatial distance calculations (`SQ4` proximity check)
- sqlite3 - Standard library; used for loading `.sqlite` / `.db` files containing MLoS and Takeoffpoint views
- smtplib - Standard library; used for sending QC summary emails via SMTP
- email.mime - Standard library; formats email messages (multipart with HTML/plain text)
- tempfile - Standard library; handles temporary file creation for SQLite uploads
- re - Standard library; regex validation (UUID format, editor username format)
- datetime - Standard library; timestamp recording
- io.BytesIO - Standard library; in-memory binary stream for file operations
- os - Standard library; file path operations and environment interaction

## Configuration

- **Streamlit Secrets (`.streamlit/secrets.toml` or environment variables):** Provides SMTP credentials for email functionality
- No build configuration detected (pure Python, no compilation step)

## Platform Requirements

- Python 3.x
- pip
- No virtual environment configuration detected (.venv/ not in repo)
- Streamlit runtime (local server or cloud deployment like Streamlit Cloud, Docker)
- SMTP server access for email notifications (optional)
- Input data files: `.sqlite`, `.db`, `.csv`, `.xlsx`, or `.xls` files

## Data Files (Bundled)

- `ward_boundary_ref.csv` - 9,410 ward records with state, LGA, ward name, ward code metadata (loaded at `app.py` line 367)
- `ward_boundary_bbox.csv` - Bounding box coordinates (min/max latitude/longitude) per ward code (loaded at `app.py` line 368)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Single entry point: `app.py`
- Lowercase with underscores for any additional files
- Example: `app.py`
- snake_case for all function names
- Descriptive and action-oriented
- Examples: `load_sqlite()`, `run_schema_qc()`, `run_mlos_qc()`, `auto_correct_mlos()`, `build_excel_report()`
- Helper functions prefixed with descriptive words: `vec_is_uuid()`, `add()` (nested helpers within QC functions)
- Private/nested functions use same convention as public functions
- snake_case for all variables
- Descriptive names that indicate purpose or content
- Examples: `mlos_df`, `takeoff_df`, `uploaded_file`, `boundary_ref`, `schema_checks`
- Short variable names in comprehensions and loops acceptable: `c`, `n`, `i`
- Tuple unpacking common: `mlos_df, takeoff_df = load_xlsx(uploaded_file)`
- UPPERCASE with underscores
- Located at module level, typically near top of file after imports
- Examples from `app.py`:

## Code Style

- No explicit formatter configured (.black, .autopep8)
- Implicit style guide based on observed patterns:
- No `.pylintrc`, `.flake8`, or `pyproject.toml` configuration present
- No linting tool integrated into CI/CD
- Code follows general PEP 8 conventions implicitly

## Import Organization

- None used; single-file application eliminates need for aliases

## Code Organization

- ASCII comment blocks using em-dashes (─) for visual section separation
- Pattern: `# ─── Section Name ────────────────────────────────────────────`
- Examples:
- Helper/utility functions grouped near top: `load_sqlite()`, `load_csv()`, `load_xlsx()`, `get_uploaded_data()`, `pct()`
- Vectorized utility functions together: `vec_is_uuid()`, `vec_is_editor()`
- QC engine functions grouped by domain: `run_schema_qc()`, `run_mlos_qc()`, `run_settlement_qc()`, `run_takeoff_qc()`, `run_ward_boundary_qc()`
- Report builders grouped: `build_excel_report()`, `build_schema_report_xlsx()`, `build_longitudinal_mlos()`, `build_corrected_excel()`
- UI code (Streamlit) in main execution body at bottom of file starting around line 1172

## Error Handling

- Try-except blocks with user-facing error messages via `st.error()`, `st.warning()`
- Examples:
- File handling uses try-finally for resource cleanup (lines 182-197):
- Validation errors return early with `st.stop()` to halt execution
- Explicit null checks using `pd.isna()`, `.isna()`, `.isnull()`
- Empty string checks with `.str.strip().eq("")`
- `keep_default_na=False` used in all CSV/Excel loaders to preserve domain value "NA" (Nasarawa state code)
- `.fillna()` for safe default value assignment

## Comments

- Algorithm logic that's non-obvious (e.g., Haversine distance calculation in SQ4)
- Explain WHY not WHAT: "keep_default_na=False prevents pandas from silently converting the valid domain value 'NA' to NaN"
- Mark critical data handling decisions (lines 98-101 explaining nullable fields)
- Explain filter/merge operations that may appear magical without context (lines 413-418)
- Docstrings on public/exported functions
- Format: triple-quoted strings immediately after function definition
- Include return type and brief description
- Example (lines 120-125):
- Example (lines 130-132):

## Function Design

- Functions typically 10-50 lines, with some reaching 100+ lines
- Larger functions are QC validation engines that process dataframes
- Example: `run_mlos_qc()` spans lines 805-965 (160 lines) — validates 14 rules on MLoS data
- Inner `add()` helper function pattern used to reduce repetition in validation rules
- Functions accept DataFrames and optional parameters
- Required parameters come first, optional with `=None` defaults
- Example: `def get_uploaded_data(uploaded_file, progress=None)` (lines 157-204)
- Example: `def add(num, rule, desc, mask, extra=None)` (nested helper at line 400)
- QC functions return tuples: `(checks_list, detail_dataframe)`
- Data loaders return tuples: `(mlos_df, takeoff_df)`
- Excel builders return bytes: `return out.getvalue()`
- Example (line 965): `return checks, pd.concat(details) if details else pd.DataFrame()`

## Module Design

- Single-file application; all functions are implicitly "exported"
- Streamlit app functions (UI code) at bottom of file after all helper/engine functions
- Clear separation between:

## Data Validation & Transformation

- Vectorized operations preferred over per-row Python functions for performance
- Pandas operations for filtering and masking
- Type coercion with `pd.to_numeric(..., errors="coerce")` for safe numeric conversion
- String normalization: `.astype(str).str.strip().str.lower()` pattern repeated throughout

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- **Single-file monolith** — All logic in `app.py` (1962 lines)
- **Functional QC engines** — Pure functions that take DataFrame, return (checks list, detail DataFrame)
- **Session state caching** — Results cached per file upload to avoid re-running QC
- **Pandas-based processing** — Vectorized operations with NumPy for performance (e.g., Haversine distance)
- **Format-agnostic input** — Detects file type and loads data into consistent DataFrame schema
- **Multi-layer redundancy** — Same data validated across 5 independent QC layers
- **Weighted scoring** — Each layer contributes proportionally to overall QC score

## Layers

- Purpose: Accept files in 3 formats and normalize to DataFrame
- Location: `app.py:104-204` (load functions)
- Contains: `get_uploaded_data()`, `load_sqlite()`, `load_xlsx()`, `load_csv()`, `load_takeoffpoint_file()`
- Depends on: `streamlit`, `pandas`, `sqlite3`, `openpyxl`
- Used by: Main QC orchestration (line 1328-1343)
- Purpose: Auto-correct common data issues before QC validation
- Location: `app.py:700-784`
- Contains: `auto_correct_mlos()` (5 correction types)
- Depends on: `pandas`, `uuid`
- Used by: Line 1369 (pre-step before all QC)
- Purpose: Run 5 independent data validation layers sequentially
- Location: `app.py:232-1012` (5 functions)
- Contains:
- Depends on: `pandas`, `numpy` (for Haversine), boundary reference CSVs
- Output: Tuple of (checks list, detail DataFrame)
- Purpose: Generate downloadable Excel reports and email summaries
- Location: `app.py:280-296` (schema), `326-364` (longitudinal), `1015-1154` (full report), `636-692` (email)
- Contains:
- Depends on: `openpyxl`, `smtplib`, `streamlit.secrets`
- Styling: PatternFill, Font, Alignment, Border via openpyxl
- Purpose: Display results and enable file downloads
- Location: `app.py:1172-1962`
- Contains:
- Depends on: `streamlit`, `pandas`

## Data Flow

### Primary Request Path

### QC Engine Execution Pattern

```python

```

- Session state (`st.session_state`) caches QC results per file upload
- Cache key: `(filename, file_size, takeoff_file_key)`
- Avoids re-running expensive 5-layer QC when switching tabs
- Progress bar tracks 5 steps (Pre + 5 layers)

### Secondary Flow: Report Generation & Email

## Key Abstractions

- Purpose: Standardized format for QC rule results
- Example: `{"Rule#": "1", "QC Check": "Required Fields", "Description": "...", "Failing Rows": 25, "Total Rows": 1000, "Fail %": "2.5%", "Status": "❌ FAIL"}`
- Used by: All QC engines, report builders, UI display
- Purpose: Row-level issue records for failed rules
- Columns: Always starts with `Rule#` and `Rule`, followed by relevant data columns + identifying columns (state, LGA, ward, settlement)
- Used by: Issue tabs, report generation, longitudinal view
- Purpose: Fast O(1) ward code validation
- Data: `ward_boundary_ref.csv` (9,410 rows) + `ward_boundary_bbox.csv` (bounding boxes)
- Caching: `@st.cache_data` decorator on `load_boundary_refs()`
- Used by: `run_ward_boundary_qc()` (rules B0-B3)
- Purpose: Detect settlements within 30m
- Pattern: Vectorized NumPy computation (radius = 6,371,000 m)
- Location: `app.py:614-627`
- Used by: Settlement QC Rule SQ4

```

```

- If a layer has no checks (e.g., Takeoffpoint skipped), it receives 100% credit
- Result: Score from 0–100%

## Entry Points

- Location: `app.py:1-20` (page config)
- Triggers: File upload via Streamlit uploader
- Responsibilities: Display sidebar, accept files, launch QC on button click
- Location: `app.py:1282-1962`
- Conditions:
- Location: `app.py:1367-1374`
- Always runs before the 5 QC layers
- Results used by all downstream QC functions
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

- Difficult to unit test individual QC functions
- Hard to reuse QC logic outside Streamlit context
- Single point of failure if app.py is corrupted
- Difficult to track responsibility boundaries
- Extract QC engines to `qc_engines.py` — Pure functions for each layer
- Extract report builders to `report_builders.py` — Decoupled from UI
- Extract loaders to `data_loaders.py` — Format-specific logic
- Import modules in `app.py` — Keep UI layer thin, orchestration only

### Redundant QC Check Pattern

- Copy-paste increases bug risk
- Changes to pattern require editing 5 functions
- No single source of truth for check structure

```python

```

### Hard-Coded Email Recipients

- Cannot customize recipients without editing code
- Difficult to support multiple environments (dev/staging/prod)
- No audit trail of who receives emails

```python

```

### Boundary Reference File Paths Hard-Coded

- Fails if files moved or deployed differently
- No validation that files exist at startup
- Tests cannot mock file paths easily

```python

```

### Missing Null Coercion in Some Checks

- Inconsistent error detection due to whitespace or case sensitivity
- Some rules strip before comparison, others don't
- May miss real errors

```python

```

## Error Handling

- File load errors → Display error message, don't stop QC (`app.py:1330-1334`)
- Takeoffpoint load failures → Skip TP rules with warning, continue QC (`app.py:1337-1343`)
- Missing boundary files → Boundary checks return empty (pre-checked with `os.path.exists`)
- SMTP failures → Display error with configuration guidance (`app.py:1954-1961`)
- Empty DataFrames → QC functions return empty results, UI handles gracefully

## Cross-Cutting Concerns

- Uses `st.write()` for progress logging during QC run (`app.py:1368+`)
- Progress bar updates for each of 5 QC layers
- Correction log printed as DataFrame
- Schema validation (S1, S2) — Checks required columns
- Data validation (Rules 1-14, SQ1-SQ4, TP2-TP5, B0-B3) — 28 total rules
- Format validation — Regex for UUID, editor, date_of_activity
- No authentication layer
- SMTP credentials stored in Streamlit secrets (user responsibility)
- Email destinations hard-coded (requires code edit to change)

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
