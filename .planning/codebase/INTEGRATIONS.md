# External Integrations

**Analysis Date:** 2026-11-05

## APIs & External Services

**Email (SMTP):**
- Purpose: sends the QC summary to the data team when the user clicks "Send QC Email" (Generate Report tab, `app.py` around line 2185-2200).
- Implementation: `send_qc_email()` in `app.py` (around lines 1027-1083) opens `smtplib.SMTP(host, port)`, calls `starttls()`, then `login()` and `sendmail()`. Message is plain text (`MIMEText`) inside `MIMEMultipart`.
- SDK/Client: Python standard library `smtplib`, `email.mime`.
- Auth: Streamlit secrets `smtp_user` and `smtp_pass`. Host and port come from `smtp_host` and `smtp_port`.
- Recipients are hardcoded in `send_qc_email()` as the `TO` and `CC` lists. Changing recipients requires a code edit.

**Google Fonts:**
- Purpose: loads the Inter font for the UI.
- Implementation: `@import url('https://fonts.googleapis.com/css2?family=Inter...')` in the CSS block at the top of `app.py`. This is a browser-side request; the app itself does not call Google.

No other third-party APIs, SDKs, or web services are called from the code. The QC engine itself is fully local.

## Data Storage

**Input data (uploaded per session, not stored by the app):**
- SQLite (`.sqlite`, `.db`, `.sqlite3`): read through a temporary file (`load_sqlite` in `app.py`, around line 108). The view `master_list_settlement_update_view` is read by `load_view()`. Geometry/BLOB columns are excluded.
- CSV: `load_csv()` in `app.py` (around line 124).
- Excel (`.xlsx`, `.xls`): `load_xlsx()` in `app.py` (around line 132). Prefers a sheet named `master_list_settlement_update_view`, `mlos`, `master_list`, or `settlements`, otherwise the first sheet.
- Uploaded data is cached in `st.session_state` (`mlos_df`, keyed by file name and size) for the duration of the browser session.

**Bundled reference data (read-only, shipped in repo):**
- `ward_boundary_ref.csv` - loaded by `load_boundary_refs()` (`app.py`, around line 342) with `@st.cache_data`.
- `ward_boundary_geom.csv.gz` - loaded by `load_ward_geoms()` (`app.py`, around line 349) with `@st.cache_resource`; decoded to shapely geometries.
- `health_facility_ref.csv.gz` - loaded by `load_health_facilities()` (`app.py`, around line 481) with `@st.cache_resource`.
- `settlement_extent_mask.npz` - loaded by `load_settlement_extents()` (`app.py`, around line 444) into the `SettlementExtentMask` class.
- Regenerated only by scripts in `scripts/` when upstream releases change (see README "Rebuilding reference data").

**Shared usage database (read/write, local):**
- Type: SQLite file `usage_log.db`, located next to `app.py` (`USAGE_DB_PATH`, `app.py` around line 808).
- Client: `sqlite3` standard library. Connection helper `_usage_db()` (`app.py`, around line 822) uses a 30-second timeout.
- Tables (created by `init_usage_db()` at import time):
  - `usage_log` - one row per run.
  - `state_runs` - one row per run and state.
  - `rule_results` - one row per run, state, and check.
  - `fail_rows` - failing rows for each state's latest run (replaced by `DELETE` then `INSERT` per state).
- Written by `save_state_results()` (`app.py`, around line 910), only when the sidebar checkbox "Share results with team" is ticked.
- Read by `render_state_results()` (`app.py`, around line 945) on the start page and in the State Results tab.
- Persistence: none guaranteed. The README states that Streamlit Community Cloud erases the file on restart, redeploy, or sleep.

**File Storage:**
- Local filesystem only. Temporary SQLite copies are written with `tempfile.NamedTemporaryFile` and deleted after loading.
- Excel and CSV outputs are generated in memory (`BytesIO`) and offered through `st.download_button`. Nothing is written to a shared store.

**Caching:**
- Streamlit in-process caches only (`st.cache_data`, `st.cache_resource`). No Redis or external cache.

## Authentication & Identity

**Auth Provider:**
- None. The app has no login. Anyone who can reach the Streamlit URL can upload files, run QC, and read the shared State Results.
- Attribution is self-reported: the sidebar "Your name" text input (`uploader_name`, `app.py` around line 1515) is stored in `usage_log.uploaded_by`. It is not verified.
- Implication for planning: any new feature that exposes data per user or restricts access needs a new auth layer. Deployment-level access control (for example Streamlit Community Cloud sharing settings) is the only current protection.

## Monitoring & Observability

**Error Tracking:**
- None. Exceptions are caught and shown in the UI (`st.error` / `st.warning`), for example around file loading (`app.py` around line 1632) and usage logging (`app.py` around line 1769).

**Logs:**
- No logging framework. The app uses Streamlit UI messages (`st.write`, `st.status`, `st.toast`) to show progress.

## CI/CD & Deployment

**Hosting:**
- Documented target: Streamlit Community Cloud (README Deployment section, which points to deploy from GitHub).
- Dev container: `.devcontainer/devcontainer.json` (Codespaces/VS Code). Auto-forwards port 8501 and starts the server with CORS and XSRF protection disabled.

**CI Pipeline:**
- None detected. No `.github/workflows/`, no Makefile, no test pipeline.

**Version control:**
- Git repository hosted on GitHub under the `eHealthAfrica` organisation (remote tracking per the merge commits in history). Default branch is `main`.

## Environment Configuration

**Required env vars:**
- None.

**Required Streamlit secrets (only for email):**
- `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`. Without them the email button shows an error; all other features work.

**Secrets location:**
- `.streamlit/secrets.toml` (local) or the Streamlit Community Cloud secrets panel (hosted). The file is git-ignored by `.gitignore`. No secrets file exists in the repository.

## Webhooks & Callbacks

**Incoming:**
- None. The app exposes only the Streamlit web UI.

**Outgoing:**
- SMTP email send only (see above).

---

*Integration audit: 2026-11-05*
