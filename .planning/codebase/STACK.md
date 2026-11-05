# Technology Stack

**Analysis Date:** 2026-11-05

## Languages

**Primary:**
- Python 3.11 (devcontainer image `mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`, see `.devcontainer/devcontainer.json`) - the entire application, in `app.py` (2,202 lines), and the build-time helpers in `scripts/`.

**Secondary:**
- Markdown - user-facing documentation in `README.md`.
- Inline HTML/CSS - the white-theme stylesheet and report cards are injected through `st.markdown(..., unsafe_allow_html=True)` at the top of `app.py`.

## Runtime

**Environment:**
- Python 3.11 (devcontainer). No `.python-version`, `.nvmrc`, or `runtime.txt` is present, so the version is only pinned by the devcontainer image.
- Web server: Streamlit (single process; the app runs as a Streamlit script that re-executes top to bottom on each interaction).

**Package Manager:**
- pip. Dependencies come from `requirements.txt`.
- Lockfile: Missing. `requirements.txt` uses lower-bound constraints only (`>=`), so resolved versions vary between installs.

## Frameworks

**Core:**
- Streamlit `>=1.32.0` - UI, file upload, sidebar, tabs, session state (`st.session_state`), caching (`st.cache_data`, `st.cache_resource`), secrets (`st.secrets`), and downloads (`st.download_button`). Declared in `requirements.txt`.

**Testing:**
- Not detected. No test framework, test directory, or test config exists in the repository.

**Build/Dev:**
- No build step. The app runs directly with `streamlit run app.py`.
- Build-time only scripts in `scripts/` (not needed to run the app):
  - `scripts/build_ward_ref.py` - uses only the standard library and pandas.
  - `scripts/build_ward_geom.py` - needs `geopandas`.
  - `scripts/build_hf_ref.py` - uses standard library and pandas.
  - `scripts/build_extent_mask.py` - needs `rasterio` and `pyogrio`.
- Dev container: `.devcontainer/devcontainer.json` installs `requirements.txt` and `streamlit`, then runs `streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false` on port 8501.

## Key Dependencies

**Critical (declared in `requirements.txt`):**
- `streamlit>=1.32.0` - the whole UI layer.
- `pandas>=2.0.0` - all tabular QC logic. Every input is read as strings (`dtype=str, keep_default_na=False`) so that the valid domain value `NA` is not turned into NaN.
- `numpy>=1.24.0` - vectorised checks, Haversine distances, and the settlement-extent grid lookup in `SettlementExtentMask` (`app.py`).
- `shapely>=2.0.0` - WKB decoding of ward polygons (`shapely.from_wkb`), `shapely.STRtree` for the B2 point-in-polygon join, and `dwithin` proximity queries for SQ4/SQ5 (`app.py`).
- `openpyxl>=3.1.0` - Excel workbook writing for the QC report, corrected MLoS export, schema report, and state-results workbook. Also used directly for cell styling (`PatternFill`, `Font`, `Alignment`, `Border`).
- `xlrd>=2.0.1` - listed for legacy `.xls` reading through pandas `ExcelFile`.

**Standard library used notably:**
- `sqlite3` - input `.sqlite`/`.db` files and the runtime usage database `usage_log.db`.
- `zlib` - decompression of settlement-extent tiles.
- `difflib` - fuzzy health-facility name matching (`SequenceMatcher`).
- `smtplib` / `email.mime` - QC summary email, imported inside `send_qc_email` in `app.py`.
- `uuid` - run IDs and replacement UUIDs in Auto Correct.
- `tempfile` - temporary copy of uploaded SQLite files (deleted after load).

**Infrastructure / data assets shipped in the repo:**
- `ward_boundary_ref.csv` - 9,406-ward lookup (state, LGA, ward metadata).
- `ward_boundary_geom.csv.gz` - ward polygons as WKB hex (EPSG:4326).
- `health_facility_ref.csv.gz` - health facilities keyed by ward code.
- `settlement_extent_mask.npz` - GRID3 settlement extents rasterised to a 25 m EPSG:3857 grid, stored as zlib-compressed 256x256 tiles.
- These are loaded from the app directory with `os.path.dirname(os.path.abspath(__file__))` (constants near `app.py` lines 338-448).

## Configuration

**Environment:**
- No environment variables are read by the app. There is no `.env` file in the repository.
- Secrets are read from Streamlit secrets (`st.secrets`) only in `send_qc_email` (`app.py`, around lines 1027-1083):
  - `smtp_host` (defaults to `smtp.gmail.com`)
  - `smtp_port` (defaults to `587`)
  - `smtp_user`
  - `smtp_pass`
  - Secrets live in `.streamlit/secrets.toml`, which is git-ignored (`.gitignore`). Do not commit that file.
- Runtime state: `usage_log.db` is created next to `app.py` on first start by `init_usage_db()` (`app.py`, around line 825). It is git-ignored (`*.db` in `.gitignore`).

**Build:**
- No build configuration. Streamlit config is not present (`.streamlit/config.toml` not found).
- Devcontainer config: `.devcontainer/devcontainer.json`.
- Editor settings: `.claude/settings.local.json` enables the `perplexity-docs` MCP server for local Claude use only; it does not affect the app.

## Platform Requirements

**Development:**
- Python 3.11 with the packages in `requirements.txt`.
- Run locally with `pip install -r requirements.txt` and then `streamlit run app.py` (see README "How to Run Locally").
- Opens on port 8501 in the devcontainer.

**Production:**
- Documented target is Streamlit Community Cloud (README Deployment section). The README warns that Community Cloud erases the local filesystem on restart, redeploy, or sleep, which wipes `usage_log.db`.
- No Dockerfile, Procfile, or CI workflow exists in the repository.

---

*Stack analysis: 2026-11-05*
