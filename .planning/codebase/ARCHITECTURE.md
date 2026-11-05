<!-- refreshed: 2026-11-05 -->
# Architecture

**Analysis Date:** 2026-11-05

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                 Streamlit UI (single script: app.py)                  │
│  Sidebar: uploader · Run QC · name · share checkbox · rule reference  │
│  Tabs: Auto Correct · QC Summary · MLoS Issues · Settlement QC ·      │
│        Boundary Issues · Raw Data · Generate Report · State Results   │
└───────┬───────────────────────┬──────────────────────┬───────────────┘
        │                       │                      │
        ▼                       ▼                      ▼
┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ Input loaders    │  │ QC engine (4 layers) │  │ Output builders      │
│ `app.py` 108-196 │  │ `app.py` 220, 506,   │  │ Excel report 1357    │
│ sqlite/csv/xlsx  │  │ 646, 1194 + auto     │  │ corrected xlsx 1176  │
│ get_uploaded_data│  │ correct 1089         │  │ schema xlsx 249      │
└────────┬─────────┘  └──────────┬───────────┘  │ email 1027           │
         │                       │              └──────────────────────┘
         ▼                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Bundled reference data (loaded once, cached with st.cache_*)         │
│ ward_boundary_ref.csv · ward_boundary_geom.csv.gz ·                  │
│ health_facility_ref.csv.gz · settlement_extent_mask.npz              │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Persistence: usage_log.db (SQLite, next to app.py)                   │
│ usage_log · state_runs · rule_results · fail_rows                    │
│ written by save_state_results (910), read by render_state_results    │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Page config and theme | Sets page title, layout, and injects the white-theme CSS | `app.py` (lines 1-90) |
| Constants and domain sets | Valid value sets (`VALID_ACC`, `VALID_HAB`, `VALID_DAY`), regexes (`UUID_RE`, `EDITOR_RE`), column sets | `app.py` (lines 92-106, 208-218) |
| Input loaders | Convert uploaded SQLite/CSV/XLSX into a string DataFrame | `app.py` (lines 108-196) |
| Schema QC (S1) | Checks required MLoS columns exist | `app.py` `run_schema_qc` (line 220) |
| Auto Correct | Pre-step that fixes nulls, GUID braces, and invalid UUIDs; returns a log | `app.py` `auto_correct_mlos` (line 1089) |
| MLoS rules (1-12) | Row-level integrity checks; Rule 2 matches takeoffpoints to health facilities | `app.py` `run_mlos_qc` (line 1194) |
| Settlement QC (SQ1-SQ6) | Duplicates, coordinate validity, stacking, proximity clusters, extent check | `app.py` `run_settlement_qc` (line 646) |
| Boundary QC (B0-B3) | Ward-code null/reference checks, spatial join to ward polygons, state name match | `app.py` `run_ward_boundary_qc` (line 506) |
| Extent mask | Tiled 2-bit raster lookup of GRID3 settlement extents, nearest-extent search | `app.py` `SettlementExtentMask` (line 366) |
| Health facility matcher | Normalises and fuzzy-compares facility names within a ward | `app.py` `facility_key`, `same_facility`, `match_takeoffpoint` (lines 464-504) |
| Scoring | Layer pass rates times weights (10/60/20/10) | `app.py` (lines 1726-1760) |
| State results logging | Splits one run into per-state rows and saves to SQLite | `app.py` `build_state_results` (853), `save_state_results` (910) |
| State results viewer | Latest-per-state table, trend chart, drill-down, downloads | `app.py` `render_state_results` (945) |
| Report and email | Excel report, corrected-data export, SMTP email | `app.py` (1357, 1176, 1027) |
| Build scripts | Regenerate reference data from source releases; not run by the app | `scripts/*.py` |

## Pattern Overview

**Overall:** Single-file Streamlit script with a linear top-down flow. Pure QC functions take a DataFrame and return `(checks, detail)`. Streamlit re-runs the whole script on every interaction and relies on `st.session_state` plus cache keys to avoid repeating work.

**Key Characteristics:**
- One Python module (`app.py`, 2,202 lines). There is no package structure, no `src/`, and no separation between UI and logic beyond function boundaries.
- Each QC layer returns a uniform check record: `{"Rule#", "QC Check", "Description", "Failing Rows", "Total Rows", "Fail %", "Status"}` plus a detail DataFrame of failing rows. The same shape is consumed by the UI, the Excel report, the email, and state results.
- All input columns are handled as strings to preserve the domain value `NA` and leading zeros. Numeric work converts on demand.
- Vectorised pandas/numpy/shapely operations are preferred over per-row Python (see comment in `vec_is_uuid`, `app.py` line 198).
- Reference data is loaded once per server process via `st.cache_data` / `st.cache_resource`.
- Gating: the script stops early (`st.stop()`) until a file is uploaded and "Run QC" has been clicked for that exact file (`submitted_key`, `app.py` lines 1615-1621).

## Layers

**Presentation (Streamlit UI):**
- Purpose: sidebar controls, progress display, metrics, tabs, downloads.
- Location: `app.py` lines 1490-2202 (sidebar block at 1490, tab blocks from 1799).
- Contains: `st.*` calls, HTML banners, styled DataFrames.
- Depends on: QC engine outputs, output builders, `render_state_results`.
- Used by: end users via the browser.

**Ingestion:**
- Purpose: turn an uploaded file into `mlos_df` (all strings).
- Location: `app.py` lines 108-196.
- Contains: `load_sqlite`, `load_view`, `load_csv`, `load_xlsx`, `get_uploaded_data`.
- Depends on: `sqlite3`, `pandas`, `tempfile`.
- Used by: the load step at `app.py` line 1623 onward.

**Normalisation (Auto Correct):**
- Purpose: deterministic fixes applied before any rule runs.
- Location: `app.py` lines 1084-1193 (`FLAG_COLS`, `auto_correct_mlos`, `build_corrected_excel`).
- Depends on: pandas, uuid.
- Used by: the "Run QC" pipeline; its output (`mlos_df_corrected`) feeds all four QC layers.

**QC engine:**
- Purpose: produce check results and failing-row details.
- Location: `app.py` lines 220-246 (schema), 1194-1356 (MLoS), 646-806 (settlement), 506-645 (boundary).
- Depends on: reference data objects passed as arguments (`hf_by_ward`, `extents`, `ref_df`, `geom_df`).
- Used by: pipeline at `app.py` lines 1634-1724.

**Scoring and aggregation:**
- Purpose: weighted score, pass rate, verdict.
- Location: `app.py` lines 1726-1760.
- Depends on: check records from all layers.
- Used by: metrics bar, verdict banner, QC Summary tab, usage logging.

**Persistence (usage database):**
- Purpose: shared history of runs across users.
- Location: `app.py` lines 800-1026.
- Depends on: `sqlite3`, the output of `build_state_results`.
- Used by: `render_state_results` and the logging block at `app.py` lines 1738-1770.

## Data Flow

### Primary Request Path (QC run)

1. User uploads a file in the sidebar and clicks "Run QC" (`app.py` 1495-1512). The click stores `submitted_key` in session state.
2. Script reruns. The header and gating (`app.py` 1579-1621) check that the file was submitted; otherwise it stops.
3. Reference data is loaded from cache (`app.py` 1636-1639).
4. `get_uploaded_data()` reads the file into `mlos_df` and caches it in session state (`app.py` 108-196, 1632).
5. If the QC cache key matches, stored results are reused. Otherwise the four stages run in order, each updating a progress bar inside `st.status` (`app.py` 1647-1703):
   1. `auto_correct_mlos` (`app.py` 1660)
   2. `run_schema_qc` (`app.py` 1670)
   3. `run_mlos_qc` (`app.py` 1679)
   4. `run_settlement_qc` (`app.py` 1688)
   5. `run_ward_boundary_qc` (`app.py` 1697)
6. Results are stored in session state keyed by `qc_cache_key` (`app.py` 1705-1715).
7. Scores and metrics are computed (`app.py` 1726-1760).
8. If "Share results with team" is ticked and this run has not been logged yet (`results_saved_key`), the run is split per state and written to `usage_log.db` (`app.py` 1738-1770).
9. Tabs render the stored check and detail frames.

### Secondary Flow: Start page (no file)

1. `render_state_results()` is called before any upload (`app.py` line 1612, inside the `if not uploaded` block).
2. It reads `state_runs`, `rule_results`, `fail_rows`, `usage_log` from `usage_log.db` and displays them.

### Secondary Flow: Email

1. "Send QC Email" button in the Generate Report tab (`app.py` 2185-2200).
2. `send_qc_email()` builds a plain-text body from `all_checks` and sends via SMTP using Streamlit secrets.

**State Management:**
- Per-browser-session: `st.session_state` keys `submitted_key`, `uploaded_cache_key`, `mlos_df`, `qc_cache_key`, `mlos_df_corrected`, `*_checks`, `*_detail`, `ac_log`, `results_saved_key`, plus widget keys.
- Per-process: `st.cache_data` for `ward_boundary_ref.csv`; `st.cache_resource` for the geometry, health facility dictionary, and extent mask.
- Persistent (on disk): `usage_log.db`.

## Key Abstractions

**Check record:**
- Purpose: a single QC rule's outcome.
- Examples: built by `add(...)` helpers inside `run_mlos_qc` (`app.py` 1202), `run_settlement_qc` (`app.py` 654), `run_ward_boundary_qc` (`app.py` 523), and `run_schema_qc` (`app.py` 220).
- Pattern: plain dicts with fixed keys. `Status` is the string `"❌ FAIL"` or `"✅ PASS"`; code tests with `"FAIL" in c["Status"]`.

**Detail frame:**
- Purpose: failing rows for one layer, with rule number, rule name, and identifying columns.
- Pattern: pandas DataFrame with `Rule#` and `Rule` as the first columns. `state_name` is included when available so per-state splitting can work (`build_state_results`, `app.py` 853).

**SettlementExtentMask:**
- Purpose: fast point-in-extent lookup without loading GeoPackage polygons.
- Examples: `app.py` lines 366-442.
- Pattern: tiles of 256x256 cells, each stored as zlib-compressed 2-bit values. `lookup()` groups points by tile key. `nearest()` expands a square neighbourhood of offsets.

**Layer weights:**
- Purpose: one place to change the score.
- Examples: `LAYER_WEIGHTS` in `app.py` line 1729.
- Pattern: dict of weights summing to 1.0; `_layer_pass_rate` applies "no checks means full credit".

## Entry Points

**Streamlit app:**
- Location: `app.py` (module-level script, no `main()`).
- Triggers: `streamlit run app.py` (README "How to Run Locally"), or the devcontainer `postAttachCommand` on port 8501.
- Responsibilities: all of the above. `init_usage_db()` runs at import (`app.py` line 1024), so the database is created on first load.

**Build scripts (offline):**
- Location: `scripts/build_ward_ref.py`, `scripts/build_ward_geom.py`, `scripts/build_hf_ref.py`, `scripts/build_extent_mask.py`.
- Triggers: manual command-line runs at the repo root when a new source release arrives.
- Responsibilities: regenerate the bundled reference files. The app does not import them.

## Architectural Constraints

- **Threading:** Streamlit runs each user session in its own script run. Shared caches (`st.cache_resource`) are process-wide. The usage database is written from script runs and relies on SQLite locking with a 30-second timeout (`_usage_db`, `app.py` line 823).
- **Global state:** Module-level reference objects in `app.py`: `boundary_ref`, `boundary_geom`, `hf_by_ward`, `settlement_extents` (loaded at lines 1636-1639 each run but returned from cache). `USAGE_DB_PATH` and reference paths are computed from `__file__`.
- **Circular imports:** None. There is one module and no internal imports.
- **Single file size:** `app.py` mixes UI, QC logic, persistence, and export code. Any change needs to be placed carefully within the sections listed above.
- **Stateful reruns:** Because the script re-executes on each widget change, expensive QC is guarded by `qc_cache_key` and `results_saved_key`. Any new expensive step should follow the same pattern.
- **Filesystem dependence:** `usage_log.db` and the reference data files must sit beside `app.py`. Ephemeral hosts lose `usage_log.db`.

## Anti-Patterns

### Module-level side effects on import

**What happens:** `init_usage_db()` is called at module level (`app.py` line 1024), and `st.set_page_config` and `st.markdown` CSS run at the top (lines 19-90).
**Why it's wrong:** The script cannot be imported for testing without touching Streamlit and the database. This is why no tests exist for QC logic.
**Do this instead:** Put new pure QC logic in functions that take DataFrames and return `(checks, detail)`, as the existing `run_*_qc` functions do. Keep them free of `st.*` calls so they can be tested. If splitting the file, move the pure functions first.

### Duplicated pipeline steps for display

**What happens:** The "Run QC" block builds `qc_bar` progress text, `st.write` lines, and the same four pass counts (`app.py` 1647-1703), while the summary block recomputes `n_fail`, `n_pass`, and percentages later (`app.py` 1718-1724).
**Why it's wrong:** Adding a fifth layer requires edits in the progress code, the cache-restore branch, the session-state save, the score block, and the logging block.
**Do this instead:** Add the new layer to `all_checks`, `LAYER_WEIGHTS`, and `_layers` together, and keep weights summing to 1.0.

### Hard-coded recipient list

**What happens:** `send_qc_email()` (`app.py` around line 1032) hard-codes the TO and CC lists.
**Why it's wrong:** Changing recipients requires a code change and redeploy.
**Do this instead:** Move recipients into Streamlit secrets next to the SMTP settings, and read them with `st.secrets.get(...)`.

## Error Handling

**Strategy:** Catch at the boundary and show the message in the UI. The app does not raise to the user.

**Patterns:**
- File load failures: `try/except` around `get_uploaded_data` shows `st.error` and calls `st.stop()` (`app.py` around line 1632).
- Logging failures: `try/except` around `save_state_results` shows `st.warning` and does not stop the page (`app.py` around line 1769).
- Email failures: `try/except` shows `st.error` with secret-setup guidance (`app.py` around line 2196).
- Missing columns: schema QC records the failure and downstream rules skip or degrade (`app.py` 220, and README "Schema Alignment").
- Missing reference files: loaders return empty objects (`load_boundary_refs` returns an empty DataFrame, `load_ward_geoms` returns an empty frame, `load_health_facilities` returns `{}`, `load_settlement_extents` returns `None`). Callers check for empty before using them.

## Cross-Cutting Concerns

**Logging:** No logger. Progress and results are shown with `st.write`, `st.status`, `st.toast`, and `st.warning`. The usage database acts as the only audit trail.

**Validation:** Rule-based validation in the QC functions. Auto Correct handles known fixes. Value sets and regexes are constants near the top of `app.py` (lines 92-106).

**Authentication:** None in the app. See `INTEGRATIONS.md`.

---

*Architecture analysis: 2026-11-05*
