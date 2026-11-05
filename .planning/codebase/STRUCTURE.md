# Codebase Structure

**Analysis Date:** 2026-11-05

## Directory Layout

```
mlos_checkout_qc_updated/
├── app.py                          # Entire Streamlit application (2,202 lines)
├── README.md                       # User and developer documentation
├── requirements.txt                # Python dependencies
├── ward_boundary_ref.csv           # Ward lookup (state, LGA, ward), 9,406 rows
├── ward_boundary_geom.csv.gz       # Ward polygons, WKB hex, EPSG:4326
├── health_facility_ref.csv.gz      # Health facilities by ward code (Rule 2)
├── settlement_extent_mask.npz      # GRID3 settlement extents, tiled 25 m raster (SQ6)
├── mlos_checkout_QC list.txt       # Source rule notes for MLoS and takeoffpoint checks
├── scripts/                        # Offline builders for the reference data
│   ├── build_ward_ref.py
│   ├── build_ward_geom.py
│   ├── build_hf_ref.py
│   └── build_extent_mask.py
├── .devcontainer/
│   └── devcontainer.json           # Codespaces / VS Code dev container
├── .claude/
│   └── settings.local.json         # Local Claude Code settings (MCP enablement)
├── .planning/
│   └── codebase/                   # Generated codebase analysis documents
├── .gitignore                      # Ignores __pycache__, *.db, *.sqlite, .venv, secrets
└── .git/                           # Git metadata
```

Runtime-only files (created by the app, git-ignored, not present in the repo):
- `usage_log.db` - created next to `app.py` by `init_usage_db()`.
- `.streamlit/secrets.toml` - optional; holds SMTP settings for email.

## Directory Purposes

**Project root:**
- Purpose: holds the app, its data assets, and its docs. The app loads its reference files relative to `app.py` (`os.path.dirname(os.path.abspath(__file__))`), so these files must stay at the root.
- Contains: one Python module, reference data, README, requirements.
- Key files: `app.py`, `requirements.txt`, the four reference files above.

**`scripts/`:**
- Purpose: build-time generators that turn source releases (SpatiaLite, SQLite, GeoPackage) into the bundled reference files.
- Contains: four standalone scripts with a usage docstring at the top of each.
- Key files: `scripts/build_ward_ref.py` (needs the existing `ward_boundary_ref.csv` for state codes), `scripts/build_extent_mask.py` (needs `rasterio`, `pyogrio`).
- Not imported by `app.py`. Run manually from the repo root.

**`.devcontainer/`:**
- Purpose: reproducible Python 3.11 environment with auto-install and auto-run of the app on port 8501.
- Key files: `.devcontainer/devcontainer.json`.

**`.planning/codebase/`:**
- Purpose: analysis documents produced by the codebase mapper for planning and execution agents.
- Generated: Yes (by the GSD codebase mapper).
- Committed: Intended to be committed with the project.

**`.claude/`:**
- Purpose: Claude Code project settings only.
- Key files: `.claude/settings.local.json`.

## Key File Locations

**Entry Points:**
- `app.py`: the Streamlit script. Run with `streamlit run app.py`.

**Configuration:**
- `requirements.txt`: Python dependencies.
- `.devcontainer/devcontainer.json`: dev container image, install, and run commands.
- `.gitignore`: ignores `*.db`, `*.sqlite`, virtualenvs, `.streamlit/secrets.toml`.
- Constants inside `app.py`: `MLOS_VIEW` (line 93), valid value sets (lines 95-99), `UUID_RE` and `EDITOR_RE` (lines 100-101), `LAYER_WEIGHTS` (line 1729), `USAGE_DB_PATH` (line 808), `EXTENT_BUFFER_M` and `EXTENT_SEARCH_M` (lines 363-364), `HF_ABBREV`, `HF_GENERIC`, `HF_FUZZY_THRESHOLD` (lines 452-462).

**Core Logic (all in `app.py`):**
- Ingestion: lines 108-196 (`load_sqlite`, `load_view`, `load_csv`, `load_xlsx`, `get_uploaded_data`).
- Schema QC: lines 208-246 (`MLOS_REQUIRED_COLS`, `run_schema_qc`).
- Reference loaders: lines 336-504 (boundary, extents, health facilities).
- Boundary QC (B0-B3): lines 506-645 (`run_ward_boundary_qc`).
- Settlement QC (SQ1-SQ6): lines 646-806 (`run_settlement_qc`).
- Usage database and state results: lines 800-1026.
- Email: lines 1027-1083 (`send_qc_email`).
- Auto Correct: lines 1084-1193 (`FLAG_COLS`, `auto_correct_mlos`, `build_corrected_excel`).
- MLoS QC (Rules 1-12): lines 1194-1356 (`run_mlos_qc`).
- Excel report: lines 1357-1489 (`build_excel_report`).
- Sidebar: lines 1490-1578.
- Pipeline and scoring: lines 1634-1770.
- Tabs: lines 1799 onward (`st.tabs` with eight tabs).

**Testing:**
- Not present. No `tests/` directory, no `test_*.py`, no `pytest.ini`.

**Reference data:**
- `ward_boundary_ref.csv`: used by B1, B2, B3, and state resolution.
- `ward_boundary_geom.csv.gz`: used by B2.
- `health_facility_ref.csv.gz`: used by MLoS Rule 2.
- `settlement_extent_mask.npz`: used by SQ6.

**Documentation:**
- `README.md`: rule definitions (sections for each layer), reference data table, rebuild instructions.
- `mlos_checkout_QC list.txt`: original business rule notes for MLoS and takeoffpoint tables.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (`build_ward_ref.py`).
- Reference data: `snake_case` with an extension and optional `.gz` (`ward_boundary_geom.csv.gz`).
- Note: `mlos_checkout_QC list.txt` contains spaces and mixed case; avoid this pattern for new files.

**Functions:**
- `snake_case` with a verb prefix: `load_*` for input and reference loading, `run_*_qc` for QC layers, `build_*` for output files, `render_*` for Streamlit sections, `vec_*` for vectorised predicates, `_layer_pass_rate` for private helpers.

**Constants:**
- `UPPER_SNAKE_CASE` at module level: `MLOS_VIEW`, `LAYER_WEIGHTS`, `USAGE_DB_PATH`.

**Rule identifiers:**
- Schema: `S1`. MLoS: `1` to `12`. Settlement: `SQ1` to `SQ6` (with `SQ2b`). Boundary: `B0` to `B3`.
- These are the `Rule#` values in every check record. Use them in new messages and reports.

**Streamlit section markers:**
- Comment banners of the form `# ─── NAME ────` separate sections in `app.py`. Follow this when adding a section.

## Where to Add New Code

**New QC rule in an existing layer:**
- Add the check inside the matching `run_*_qc` function in `app.py` using its local `add(num, rule, desc, mask, extra)` helper (for example `run_mlos_qc` at line 1194 and its `add` at line 1202).
- Update the README rule table, and the "Rules 1-12" or "Rules SQ1-SQ6" text.
- Update the rule reference expander in the sidebar (`app.py` around lines 1520-1578) if the rule is user-facing.
- Tests: none exist. Add a `tests/` directory at the root and import pure functions from `app.py` only after moving them out of the Streamlit module (see ARCHITECTURE.md Anti-Patterns).

**New QC layer:**
- Implement `run_<layer>_qc(mlos_df, ...)` returning `(checks, detail)` in `app.py`, next to the other layers.
- Add its weight to `LAYER_WEIGHTS` so the weights still sum to 1.0.
- Add it to the progress steps in the Run QC block (`app.py` around lines 1647-1703), to `all_checks`, to `_layers` in the logging block (`app.py` around line 1738), and to the QC Summary tab.

**New reference data file:**
- Place the file at the repo root, next to `app.py`, and load it with `os.path.join(os.path.dirname(os.path.abspath(__file__)), "<file>")`.
- Add a builder script in `scripts/` that documents its source and usage, following the existing docstring pattern.
- Load it through `@st.cache_data` (for DataFrames) or `@st.cache_resource` (for objects that should not be copied).
- Document it in the README "Reference Data" table.

**New tab:**
- Add the label to the `st.tabs([...])` call (`app.py` around line 1799), unpack one more variable, and put the content in a `with tabN:` block after the existing tabs.

**New output (download or report):**
- Add a `build_*` function that returns `bytes` (like `build_excel_report`, `build_corrected_excel`) and pass it to `st.download_button`.

**New usage-database table:**
- Add a column list to `USAGE_TABLES` (`app.py` around line 819), and write and read with `save_state_results` and `load_results_table`. Keep the `run_id` column in every table so rows can be joined.

**Utilities:**
- Shared helpers: `app.py` "Helpers" block (around line 90), for example `pct` (line 196) and `_cell` (line 832).
- No `utils/` module exists. Do not create one unless `app.py` is split.

**Scripts:**
- Build-time only: `scripts/`. Do not import them from `app.py`.

## Special Directories

**`.planning/codebase/`:**
- Purpose: generated analysis documents (STACK, INTEGRATIONS, ARCHITECTURE, STRUCTURE, and the quality and concerns documents when generated).
- Generated: Yes.
- Committed: Yes (intended).

**`.devcontainer/`:**
- Purpose: development container definition.
- Generated: No.
- Committed: Yes.

**`.git/`:**
- Purpose: version control metadata.
- Generated: Yes (by git).
- Committed: Not applicable.

**Runtime files (not in the repo):**
- `usage_log.db`: created at startup beside `app.py`; ignored by `.gitignore` (`*.db`). Do not commit.
- `__pycache__/`: ignored by `.gitignore`.

---

*Structure analysis: 2026-11-05*
