# Coding Conventions

**Analysis Date:** 2026-11-05

## Naming Patterns

**Files:**
- Python modules are `snake_case.py`: `app.py` (the whole Streamlit app), `scripts/build_ward_ref.py`, `scripts/build_extent_mask.py`.
- Reference data is `snake_case` with an extension, optionally `.gz`: `ward_boundary_ref.csv`, `ward_boundary_geom.csv.gz`, `health_facility_ref.csv.gz`, `settlement_extent_mask.npz`.
- Avoid spaces and mixed case in new filenames. The existing `mlos_checkout_QC list.txt` is an exception and should not be copied.

**Functions:**
- `snake_case` with a verb prefix that states the role:
  - `load_*`: input and reference loading (`load_sqlite`, `load_view`, `load_csv`, `load_xlsx`, `load_boundary_refs`, `load_ward_geoms`, `load_settlement_extents`, `load_health_facilities`) in `app.py`.
  - `run_*_qc`: QC layers that return `(checks, detail)` (`run_schema_qc` at `app.py:220`, `run_mlos_qc` at `app.py:1194`, `run_settlement_qc` at `app.py:646`, `run_ward_boundary_qc` at `app.py:506`).
  - `build_*`: file outputs that return `bytes` (`build_schema_report_xlsx` at `app.py:249`, `build_longitudinal_mlos` at `app.py:297`, `build_corrected_excel` at `app.py:1176`, `build_excel_report` at `app.py:1357`).
  - `render_*`: Streamlit section renderers (`render_state_results` at `app.py:945`).
  - `vec_*`: vectorised pandas predicates that take a Series and return a boolean Series (`vec_is_uuid` at `app.py:199`, `vec_is_editor` at `app.py:203`).
  - `save_*`, `init_*`, `_usage_db`: usage-database helpers (`app.py:822-925`). A leading underscore marks a private helper (`_usage_db`, `_cell`, `_layer_pass_rate`, `_current_key`).
- Helper predicates use `same_*` or `vec_*`: `same_facility` at `app.py:473`.

**Variables:**
- `snake_case` for locals and DataFrames: `mlos_df`, `boundary_ref`, `hf_by_ward`, `mlos_checks`, `mlos_detail`.
- Prefix `_` for throwaway or intermediate names inside long blocks: `_is_null`, `_null_mask`, `_n1`, `_cols1`, `_usage_row`, `_ts`, `_run_id`, `_layers`.
- Keep the `mlos` short name in QC helpers (`def run_mlos_qc(mlos: pd.DataFrame, ...)`). Use the longer `mlos_df` for loaded DataFrames in the main flow.
- The `total`, `checks`, `details`, `n`, and `mask` names are the conventional locals inside each QC function.

**Constants:**
- Module-level `UPPER_SNAKE_CASE`: `MLOS_VIEW` (`app.py:93`), `VALID_YN_NA`, `VALID_ACC`, `VALID_HAB`, `UUID_RE`, `EDITOR_RE`, `YN_NA_COLS`, `MLOS_REQUIRED_COLS` (`app.py:208`), `FLAG_COLS` (`app.py:1084`), `LAYER_WEIGHTS` (`app.py:1729`), `USAGE_DB_PATH` (`app.py:808`), `EXTENT_BUFFER_M` and `EXTENT_SEARCH_M` (`app.py:363-364`), `HF_FUZZY_THRESHOLD` (`app.py:462`).
- Valid-value sets are Python `set` literals of strings, for example `VALID_DAY = {"1","1_2",...,"NA"}`.
- Compiled regexes use the `*_RE` suffix and are stored as module constants (`UUID_RE`, `EDITOR_RE`, `HF_NUMERAL`).
- Path constants are built from the app's own directory so that the app runs from any working directory:
  ```python
  BOUNDARY_REF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ward_boundary_ref.csv")
  ```
  Follow this form for any new data file (`app.py:339-361`).

**Classes:**
- `PascalCase`: `SettlementExtentMask` (`app.py:366`).

**Rule identifiers:**
- Every check record has a `Rule#` string. The families are:
  - Schema: `S1` (`app.py:220`).
  - MLoS: `"1"` to `"12"` as strings, including the `"2"` takeoffpoint rule. Rules 11 and 12 reuse one `Rule#` for several columns, so match on `Rule` as well (see `make_longitudinal_df`, `app.py:267`).
  - Settlement: `SQ1`, `SQ2`, `SQ2b`, `SQ3` to `SQ6`.
  - Boundary: `B0` to `B3`.
- Use these identifiers in new messages, detail rows, and reports. Do not invent a new prefix.

**Streamlit keys:**
- Widget keys are `snake_case` strings and are unique per widget: `key="sqlite_upload"`, `key="uploader_name"`, `key="share_results"`, `key="send_email_btn"`.
- Session-state keys are `snake_case` strings: `"uploaded_cache_key"`, `"mlos_df"`, `"submitted_key"`, `"results_saved_key"`.

**Types:**
- Type hints are used on public helpers, mostly on signatures that take or return DataFrames: `def run_schema_qc(mlos: pd.DataFrame):`, `def auto_correct_mlos(mlos: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:`, `def make_longitudinal_df(mlos_df: pd.DataFrame, mlos_checks: list, mlos_detail: pd.DataFrame) -> pd.DataFrame:`.
- Hints are optional. About half of the functions in `app.py` have none, and the QC functions usually return untyped tuples. New code should add hints to new signatures, as the newer helpers do.
- Quoted annotations are used for pandas types in older helpers: `def vec_is_uuid(series: "pd.Series") -> "pd.Series":`. Either form is acceptable.

## Code Style

**Formatting:**
- No formatter is configured. There is no `pyproject.toml`, `setup.cfg`, `.editorconfig`, `black`, `ruff`, or `yapf` config in the repository.
- Indentation is 4 spaces.
- Double quotes are the default for strings, with single quotes used occasionally. Keep the surrounding file's choice.
- Lines are long. In `app.py`, 144 lines are over 100 characters and 74 are over 120. Keep new lines under about 120 characters and wrap long calls with the opening parenthesis on the first line.
- Visual alignment of dict literals and assignments is common (`"Rule#": num, "QC Check": rule, ...`). Do not reformat existing blocks unless you are editing them.
- Use the `pct(v, t)` helper for percentages: `pct(n, total)` returns `"12.3%"` or `"0%"` when the total is zero (`app.py:196`).

**Linting:**
- No linter is configured and no CI runs one. Write code that passes `python -m pyflakes app.py` without new warnings.
- Do not leave unused imports. Note that `app.py` imports `shapely`, `zlib`, `difflib`, and `tempfile` at the top, and some functions re-import `numpy` or `uuid` locally (`run_settlement_qc` imports `numpy as np` at `app.py:647`; `auto_correct_mlos` imports `uuid as _uuid` at `app.py:1092`). Prefer the module-level import when adding new code.

**Section banners:**
- Top-level sections are separated by comment banners of the form `# ─── NAME ───...`. Examples: `# ─── Page Config ───`, `# ─── Constants ───`, `# ─── Schema QC ───`, `# ─── Auto Correction ───`, `# ─── LOAD DATA ───`, `# ─── RUN QC ───`, `# ─── FILE INFO + METRICS ───`, `# ─── TABS ───`.
- Within a function, rules are introduced with a comment of the form `# R1 — ...`, `# SQ2b — ...`, `# ── Correction 1: ... ───`. Use the same em-dash style.

## Import Organization

**Order (as used in `app.py:1-16`):**
1. Third-party UI and data libraries: `import streamlit as st`, `import pandas as pd`, `import numpy as np`, `import shapely`, `import openpyxl`.
2. Standard library: `sqlite3`, `tempfile`, `os`, `re`, `difflib`, `zlib`, `uuid`, `io.BytesIO`, `datetime`.
3. Specific names from third-party modules: `from openpyxl.styles import PatternFill, Font, Alignment, Border, Side` and `from openpyxl.utils import get_column_letter`.

The imports are not separated into groups by blank lines, and standard library and third-party imports are interleaved. Keep new imports at the top of the file in the same block.

**Lazy imports:**
- Heavy or optional modules are imported inside the function that needs them: `smtplib` and `email.mime.*` inside `send_qc_email` (`app.py:1028-1031`), `numpy` inside `run_settlement_qc`, `uuid` inside `auto_correct_mlos`. Keep this pattern for the SMTP and optional-dependency code paths.

**Path aliases:**
- Not applicable. There is no module aliasing beyond `import pandas as pd`, `import numpy as np`, `import streamlit as st`.

## Pandas and Data Conventions

**Read everything as text:**
- All loaders read values as strings and keep `"NA"` as a value, not as NaN:
  ```python
  return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
  return xl.parse(mlos_sheet, dtype=str, keep_default_na=False)
  ```
  The loaders are at `app.py:124-148`. Only truly empty cells become `""` (or NaN if they are truly missing). Do not add a loader that drops `keep_default_na=False`.
- Numeric checks convert explicitly with `pd.to_numeric(series, errors="coerce")` before comparison (`run_settlement_qc`, `app.py:680`).

**Null handling:**
- Treat a value as null with both checks, because loaders can produce either NaN or an empty string:
  ```python
  mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
  ```
  This pattern is used in Rule 1 (`app.py:1229`) and Auto Correction (`app.py:1102`).
- Normalise text before comparing: `.fillna("").astype(str).str.strip()`, and `.str.lower().str.replace(r"\s+", " ", regex=True)` for name matching (`app.py:670-671`).

**Vectorised checks:**
- Write checks as boolean masks over the full DataFrame. The comment in `app.py:198` states the rule: "Vectorized regex checks — avoid per-row Python function calls". Avoid `df.apply(lambda ...)` on large frames. The existing exceptions are for building the human-readable detail text (`_sub1["Null Fields"] = ... apply(...)` at `app.py:1245`).
- Use `Series.str.match(pattern, na=False)` for regex masks (`app.py:201-206`).

**Check record shape:**
- Every QC check appends one dict to `checks`, and each failing set appends one DataFrame to `details`. Use the `add(num, rule, desc, mask, extra=None)` closure that `run_mlos_qc` and `run_settlement_qc` define:
  ```python
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
  ```
  The keys `Rule#`, `QC Check`, `Description`, `Failing Rows`, `Total Rows`, `Fail %`, and `Status` are the contract that the report, the email, and the state-results logger all read. Do not rename them. A status is `"❌ FAIL"` or `"✅ PASS"`, and the code tests for the substring `"FAIL"`.
- Guard a rule on column presence. Each rule starts with `if "col" in mlos.columns:` so that a missing column skips the rule instead of crashing. The schema layer (`S1`) reports the missing column.
- `id_col` selection uses `"ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]`, and the `BASE` list of identifying columns is built with a list comprehension over the columns present (`app.py:1197-1198`).

**Layer scoring:**
- A layer passes at the check level, and the weighted score is computed from the pass fraction per layer:
  ```python
  def _layer_pass_rate(checks):
      if not checks:
          return 1.0   # no checks → full credit (layer not applicable)
      passing = sum(1 for c in checks if "FAIL" not in c["Status"])
      return passing / len(checks)
  ```
  The weights are in `LAYER_WEIGHTS` (`app.py:1729`) and sum to 1.0.

## Streamlit Conventions

**Page flow:**
- `st.set_page_config(...)` is the first Streamlit call (`app.py:19`). Put any new Streamlit call after it.
- The whole script runs top to bottom on every interaction. Use `st.stop()` to end the run early, for example when no file is uploaded (`app.py:1613`) or when loading fails.
- The page is styled with one `st.markdown("""<style>...</style>""", unsafe_allow_html=True)` block (`app.py:22-87`). Use the existing CSS classes (`banner-pass`, `banner-fail`, `sec-title`, `report-card`, `report-row`, `report-verdict-pass`, `report-verdict-fail`) for new status or section markup rather than writing new inline styles.
- Colours in the stylesheet and in Excel fills are the same palette: header blue `#1d4ed8` (Excel `1D4ED8`), error fill `FEE2E2`, success fill `F0FDF4`. Reuse these for new report styling.

**Caching:**
- Reference data is cached with the Streamlit decorators, with `show_spinner=False`:
  - `@st.cache_data(show_spinner=False)` for immutable DataFrames (`load_boundary_refs`, `app.py:341`).
  - `@st.cache_resource(show_spinner=False)` for objects that should not be copied, such as the geometry frame, the settlement extent mask, and the facility index (`app.py:348`, `app.py:443`, `app.py:480`).
- Upload results are cached manually in `st.session_state` keyed by `(uploaded.name, uploaded.size)` (`get_uploaded_data`, `app.py:150-194`).

**Session state:**
- Read with `.get(key)` and write with item assignment. Use `st.session_state.get("results_saved_key") != qc_cache_key` to make a side effect run once per upload (`app.py:1749-1768`).

**Widgets:**
- Every interactive widget has an explicit `key=`. Keep this rule for new widgets so that reruns keep state.
- Use `use_container_width=True` for full-width buttons and tables, and `hide_index=True` for `st.dataframe` tables (`app.py:1837-1846`).
- Use `st.spinner("...")` around slow builds, and `st.progress` for the loading path (`app.py:1624-1627`).
- Emoji prefixes on labels and messages are the house style: `"▶️ Run QC"`, `"✅ Loaded ..."`, `"❌ Failed to load file: ..."`, `"⚠️ ..."`.

## Error Handling

**Pattern: broad catch at UI boundaries.**
The app catches `Exception` at the edge of a user action, shows the message with `st.error` or `st.warning`, and keeps the session running. Examples:
- File load: `except Exception as e: st.error(f"❌ Failed to load file: {e}"); st.stop()` (`app.py:1626-1630`).
- Usage logging: `except Exception as e: st.warning(f"⚠️ This run could not be logged to the usage database: {e}")` (`app.py:1769-1771`).
- Email send: `except Exception as e: st.error(...)` with a hint about which secrets to set (`app.py:2195-2201`).
- State results rendering: `except Exception as e:` in `render_state_results` at `app.py:949`.

Follow this pattern for new user-triggered actions (uploads, sends, exports). Include the exception text and an actionable hint, as the email handler does.

**Resource cleanup:**
- Use `try/finally` to release SQLite connections and temp files (`app.py:178-186`):
  ```python
  conn, tmp_path = load_sqlite(uploaded_file)
  try:
      ...
  finally:
      conn.close()
      try:
          os.unlink(tmp_path)
      except OSError:
          pass
  ```
- Use `with` for connections and writers: `with _usage_db() as conn:` (`app.py:826`) and `with pd.ExcelWriter(out, engine="openpyxl") as writer:` (`app.py:252`, `app.py:304`), and `with smtplib.SMTP(...) as server:` (`app.py:1078`).
- Silent `except OSError: pass` is acceptable only for temp-file deletion.

**Data QC never raises:**
- QC functions do not stop the run when a rule fails. They append a FAIL record and continue. `run_schema_qc` says so in its docstring: "Does NOT stop the QC process." New rules must report a failure through `add(...)` and must not raise on bad data.
- Blank or invalid input is treated as a check result, not an exception. Coerce with `errors="coerce"` and test `.isna()`.

**Configuration errors:**
- Secrets are read with `st.secrets.get("key", default)`. Missing SMTP settings surface through the email error message, not a startup crash (`send_qc_email`, `app.py:1027`).

## Logging

**Framework:** None. The `logging` module is not used.

**Patterns:**
- The Streamlit UI is the user-visible log: `st.success`, `st.warning`, `st.error`, `st.toast`, and `st.info` (`app.py:1768`, `app.py:1773`).
- Build scripts in `scripts/` write progress with `print(...)`. The main script `scripts/build_ward_ref.py` prints a summary line (`print(len(rows), "source rows ->", len(ref), "wards")`). `scripts/build_extent_mask.py` passes `flush=True` for progress.
- Do not add `print` calls to `app.py`. Use `st.toast` or `st.warning` for run-time messages.

## Comments

**When to Comment:**
- Comment rule intent and data quirks, not the mechanics. Examples in the code:
  - `# keep_default_na=False prevents pandas from silently converting the valid domain value "NA" ... to NaN` (`app.py:126-128`).
  - `# Loaders use keep_default_na=False, so blank cells arrive as "" rather than NaN` (`app.py:1228`).
  - `# Rules 11 and 12 reuse one Rule# for several columns, so match on the rule name too` (`app.py:285`).
- Each rule has a one-line `# R1 — ...` or `# SQ1 — ...` comment that states the rule in plain words, followed by the mechanics when needed.
- Keep the rule text in `README.md` and `mlos_checkout_QC list.txt` in step with the code. These are the business-rule sources.

**Docstrings:**
- Triple-quoted docstrings on the public helpers, usually one or two lines, in the imperative or descriptive form: `"""Apply auto-corrections to the MLoS DataFrame.` and `"""Build ward_boundary_ref.csv from the ward_boundary_sept SpatiaLite table.`
- Multi-part docstrings name the return value in a block: `"""Returns check entries (same format as run_mlos_qc) and a detail DataFrame."""`
- Scripts in `scripts/` open with a docstring that includes a `Usage:` block with the exact command to run from the repository root.
- JSDoc/TSDoc does not apply.

## Function Design

**Size:**
- QC layers are long single functions, up to about 150 lines (`run_mlos_qc` spans `app.py:1194-1356`, `run_ward_boundary_qc` spans `app.py:506-645`). Each rule is a block with its own comment. Keep a new rule as a block inside the existing layer function, using the `add(...)` closure.
- Put reusable predicates and loaders in their own top-level functions, as with `facility_key`, `same_facility`, and `match_takeoffpoint` (`app.py:464-504`).

**Parameters:**
- Pass DataFrames and reference objects explicitly. Do not read module globals inside QC functions except for the constants listed above.
- Optional reference inputs default to `None` (`run_settlement_qc(mlos, extents=None)`, `app.py:646`).

**Return values:**
- QC layers return a tuple `(checks, details)` where `checks` is a list of dicts and `details` is a list of DataFrames or a single concatenated DataFrame.
- Builders return `bytes` for Streamlit's `st.download_button` (`build_excel_report`, `build_corrected_excel`).
- Auto Correction returns `(corrected_df, log)` where `log` is a list of `{"Column", "Correction", "Rows Fixed"}` dicts (`app.py:1089`).

## Module Design

**Exports:**
- There is one module, `app.py`, with no package structure. There is no `__all__`. Helpers are plain module-level functions.
- Helpers used only inside one function are defined inside it (for example the `add` closure). Keep this for helpers that are only needed by one QC layer.

**Barrel Files:**
- Not used. There are no `__init__.py` files.

**Scripts:**
- Each file in `scripts/` is a standalone command-line script with `sys.argv` arguments. It is not imported by `app.py`. Keep build-time dependencies (`geopandas`, `rasterio`, `pyogrio`) out of `app.py` and inside the script that needs them.

## Security and Data Handling Conventions

- Credentials go in Streamlit secrets (`st.secrets`), read with `.get`. The repository ignores `.streamlit/secrets.toml` (`.gitignore`). Never hard-code credentials.
- The email recipient lists are currently hard-coded as module-local lists inside `send_qc_email` (`app.py:1034-1035`). Treat these as configuration. Move them to `st.secrets` or a constant when you change them, and do not copy the addresses into new documents or code.
- Uploaded files are written to a temp file only for SQLite input, and the temp file is removed in `finally` (`app.py:178-186`).
- Use `dtype=str` on every input read so that codes such as ward codes and UUIDs keep their leading zeros and formatting.
- SQL identifiers that come from data are quoted with double quotes, as in `load_view` (`app.py:114-121`). The view name is a constant (`MLOS_VIEW`). Do not interpolate user-supplied table names.

## Adding New Code: Checklist

1. New QC rule: add a block inside the matching `run_*_qc` function, use the `add(num, rule, desc, mask, extra)` closure, and use the next free identifier in the layer's family.
2. New reference file: place it at the repository root, add a `*_PATH` constant built from `os.path.dirname(os.path.abspath(__file__))`, and load it with a cached loader.
3. New Streamlit section: add a `# ─── NAME ───` banner, give every widget a `key=`, and wrap slow work in `st.spinner`.
4. New user action that can fail: wrap it in `try/except Exception as e` and show `st.error` or `st.warning` with the exception text.
5. New output file: return `bytes` from a `build_*` function, styled with the existing header fill `1D4ED8`.
6. New script: put it in `scripts/`, start it with a docstring that includes a `Usage:` block, and print progress with `print`.

---

*Convention analysis: 2026-11-05*
