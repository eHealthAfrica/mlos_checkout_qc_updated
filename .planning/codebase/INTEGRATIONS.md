# External Integrations

**Analysis Date:** 2026-09-09

## APIs & External Services

**Email Notification:**
- SMTP Server (e.g., Gmail) - Sends QC summary email reports to data team
  - SDK/Client: `smtplib` (Python standard library) via `email.mime` 
  - Configuration: Streamlit secrets (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`)
  - Used in: `send_qc_email()` function (`app.py` lines 636-692)
  - Default SMTP host: `smtp.gmail.com` on port `587` (STARTTLS)
  - Requires: Valid SMTP credentials stored in Streamlit secrets configuration

**Web Fonts:**
- Google Fonts (CSS) - Inter font family loaded via `@import url()`
  - Used for: Application UI typography (line 24 in app.py)
  - Source: `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap`
  - Non-critical (graceful fallback to system fonts)

## Data Storage

**Databases:**
- SQLite 3 (local file-based)
  - Connection: Via Python `sqlite3` standard library
  - Use case: Loading MLoS and Takeoffpoint views from `.sqlite` or `.db` files uploaded by users
  - Views queried: `master_list_settlement_update_view`, `mlos_takeoffpoint_view`
  - Schema introspection: Uses `PRAGMA table_info()` to safely load supported column types (excludes BLOB, POINT, GEOMETRY)

**File Storage:**
- Local filesystem only
  - Temporary storage: `tempfile.NamedTemporaryFile()` for uploaded SQLite files (deleted after processing)
  - Output storage: Downloads generated via Streamlit (`st.download_button()`) — files not persisted server-side
  - Reference data: `ward_boundary_ref.csv`, `ward_boundary_bbox.csv` (bundled in repo, read-only)

**Caching:**
- Streamlit session state - Per-user in-memory caching
  - Keys: `uploaded_cache_key`, `mlos_df`, `takeoff_df`, `qc_cache_key`, QC check results
  - Scope: Single user session
  - Lifetime: Duration of browser session
  - No server-side persistence

## Authentication & Identity

**Auth Provider:**
- Custom (application-level only)
  - No user login/authentication required
  - SMTP credentials stored in Streamlit secrets (not user-specific)
  - Optional field validation: `editor` field (format: `firstname.surname` lowercase, Rule 13)

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Streamlit console output (development mode) and `st.write()`, `st.error()`, `st.info()`, `st.success()` for user-facing messages
- Application state tracked via session variables for debugging

## CI/CD & Deployment

**Hosting:**
- Local development: `streamlit run app.py`
- Cloud deployment: Compatible with Streamlit Cloud, Docker, or any Python WSGI server
- No containerization files detected (no `Dockerfile` in repo)

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- Not environment-based; configuration stored in **Streamlit secrets** (`.streamlit/secrets.toml`):
  - `smtp_host` - SMTP server hostname (default: `smtp.gmail.com`)
  - `smtp_port` - SMTP server port (default: `587`)
  - `smtp_user` - SMTP authentication username/email
  - `smtp_pass` - SMTP authentication password

**Optional env vars:**
- None detected

**Secrets location:**
- Streamlit secrets file: `.streamlit/secrets.toml` (local development) or environment variables (cloud deployment)
- Accessed via `st.secrets.get()` (app.py lines 678, 684-687)
- File not present in repo (secrets managed externally per deployment)

## Webhooks & Callbacks

**Incoming:**
- None detected (application is data import/QC tool, not API server)

**Outgoing:**
- Email notifications only (SMTP `sendmail()` call to recipients)
  - Triggered manually: User clicks "📤 Send QC Email" button (app.py line 1953)
  - Recipients: `TO` list (QC data team) + `CC` list (defined in email function)
  - Content: Plain text + HTML summary of QC results

## Input Data Sources

**File Upload Formats:**
- `.sqlite` / `.db` - SQLite database with two views: `master_list_settlement_update_view` (MLoS), `mlos_takeoffpoint_view` (Takeoffpoint)
- `.xlsx` / `.xls` - Excel workbooks: Sheet 1 = MLoS data, Sheet 2 = Takeoffpoint data (sheet names flexible)
- `.csv` - CSV files: MLoS data only (Takeoffpoint cross-checks skipped unless separate Takeoffpoint file uploaded)

**Reference Data (Bundled):**
- `ward_boundary_ref.csv` - 9,410 ward records for boundary validation (B0, B1, B3 checks)
- `ward_boundary_bbox.csv` - Ward bounding boxes for coordinate validation (B2 check)

## Output Data Streams

**Downloadable Reports:**
- **Auto Corrected MLoS (Excel)** - Corrected dataset after preprocessing
- **Schema Error Report (Excel)** - Schema alignment failures (if any)
- **MLoS Issues (Excel)** - Row-level detail per failing rule + longitudinal view
- **Settlement QC Issues (Excel)** - Spatial check failures
- **Takeoffpoint Issues (Excel)** - Cross-table validation failures
- **Boundary Issues (Excel)** - Ward/coordinate validation failures with reference comparison
- **Full QC Report (Excel)** - Overall verdict + all layers

All Excel exports use `openpyxl` with formatted headers, fills, borders, and alignment (app.py lines 10, 1553, 1621, 1666, etc.).

---

*Integration audit: 2026-09-09*
