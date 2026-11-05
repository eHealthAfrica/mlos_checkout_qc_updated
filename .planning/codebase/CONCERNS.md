# Codebase Concerns

**Analysis Date:** 2026-11-05

Scope: full repository on branch `mlos_checkin`. The application is a single Streamlit file, `app.py` (2,202 lines), plus reference data files and build scripts. There is no test suite on this branch (no `test*` files are tracked). Line numbers refer to `app.py` unless stated otherwise.

## Access Control and Exposure (highest priority)

**No login or access control on this branch:**
- Issue: The app has no authentication of any kind. Anyone who has the URL can upload files, run QC, read every shared run, download the full shared results workbook, and trigger the QC summary email. No auth code exists in `app.py` (no `auth` import, no login, no allow-list).
- Files: `app.py` (entire UI; `init_usage_db()` at line 1024; `render_state_results()` at lines 945-1021; send-email button at about line 2191), `README.md` section "Streamlit Cloud" (deployment instructions do not mention access restriction).
- Impact: Shared State Results and the usage log are readable and downloadable by anyone with the link. This includes uploader-entered names, file names, LGA names, per-state scores, and failing-row detail (see next item). Any visitor can also send email to the data team.
- Status of the planned fix: A Google sign-in gate exists only in `origin/feature/qc-rules` (`auth.py`, imported at that branch's `app.py` line 23). That branch is not merged into `mlos_checkin`, `HEAD`, or `origin/main`. The gate is not a fix for this branch until it is merged or ported.
- Fix approach: Before sharing the link more widely, either merge the auth work or put the deployment behind platform access control (for example Streamlit Community Cloud's viewer restriction or a reverse proxy with SSO). Treat the usage database as sensitive until then.

**Shared failing-row data contains location and security-relevant fields:**
- Issue: The `fail_rows` table stores, for each state's latest run, the settlement name, latitude, longitude, and a `detail` string built from all extra columns of the failing row. Rule 1 failing rows carry the full NOT NULL column set, which includes `security_compromised`, so that flag can appear in the shared table.
- Files: `app.py` `build_state_results()` (lines 853-908, the `base`/`extra` logic around lines 880-900), `save_state_results()` (lines 910-922), Rule 1 detail construction (around lines 1240-1250, `_cols1` built from `_NOT_NULL_COLS`).
- Impact: Settlement coordinates and security flags from conflict-affected or sensitive areas are stored in a shared, unauthenticated store and exported as CSV/Excel.
- Fix approach: Limit `fail_rows` detail to the identifiers needed for correction. Drop `security_compromised` and free-text detail from the shared store, or make the sharing opt-in per file.

**Sharing is on by default:**
- Issue: The "Share results with team" checkbox defaults to `True`, so every run is written to the shared database unless the uploader unticks it.
- Files: `app.py` line 1511 (`st.checkbox(..., value=True, key="share_results")`).
- Impact: Test runs and sensitive uploads are logged without an explicit decision by the uploader.
- Fix approach: Default to `False`, or require an explicit confirmation before logging.

**Uploader identity is unverified:**
- Issue: "Your name" is a free-text field. Any value can be entered, and it is stored as `uploaded_by` in every shared table.
- Files: `app.py` line 1512 (`st.text_input("Your name", ...)`), `_usage_row` at lines 1757-1763.
- Impact: Run attribution can be spoofed or left blank. Audit trails in the shared workbook are not reliable.
- Fix approach: Derive identity from the authentication layer (see first item). Until then, label the field as self-reported.

**Hardcoded email recipients, no guard on sending:**
- Issue: The To and Cc recipients of the QC summary are hardcoded as four addresses in `send_qc_email()`. Recipient changes require a code change and redeploy. The send button has no confirmation, rate limit, or duplicate-send guard, so repeated clicks send repeated emails.
- Files: `app.py` lines 1034-1037 (`TO` and `CC` lists inside `send_qc_email()`), send call and button at lines 2191-2199.
- Impact: Anyone with the link can email the same people repeatedly. Recipient list is not configurable without editing the code.
- Fix approach: Move recipients to Streamlit secrets (for example `qc_email_to` and `qc_email_cc`). Add a per-session or per-file send guard, and record who sent what.

**SMTP connection does not verify the server certificate:**
- Issue: `server.starttls()` is called without an SSL context. In CPython, `smtplib` then falls back to `ssl._create_stdlib_context()`, which does not verify the server certificate. SMTP username and password are sent over that connection.
- Files: `app.py` line 1079 (`server.starttls()`), login at line 1080.
- Impact: A network attacker could intercept the SMTP credentials.
- Fix approach: Use `server.starttls(context=ssl.create_default_context())` and add `import ssl`.

**Spreadsheet formula injection in exports:**
- Issue: Values taken from uploaded files are written unchanged into Excel and CSV. openpyxl treats any string beginning with `=` as a formula (verified: `ws["A1"] = "=1+1"` gives `data_type == "f"`). A crafted cell such as `=HYPERLINK(...)` in an uploaded file would become a live formula in the downloaded workbook. CSV exports have the same issue when opened in spreadsheet software.
- Files: Excel writers `build_state_results_xlsx()` (around lines 932-944), `build_excel_report()` (around line 1357), `build_corrected_excel()` (lines 1176-1186), `build_schema_report_xlsx()` (lines 249-264); CSV export at line 1021 (`view.to_csv`).
- Impact: Users who open exports can be exposed to formula-based data exfiltration or misleading values. Shared exports are the highest-risk case because many users download them.
- Fix approach: Sanitize string cells that start with `=`, `+`, `-`, `@`, tab, or carriage return (prefix with an apostrophe or write them as text with an explicit data type).

**Unsafe HTML interpolation:**
- Issue: Several blocks use `st.markdown(..., unsafe_allow_html=True)` with f-strings. The report summary (around lines 2097-2141) builds HTML that is then rendered as raw HTML. File names and uploader names reach some of these strings.
- Files: `app.py` lines 1585-1600 (CSS block, static), 2097-2141 (report card), 1789-1796 and 1827 (verdict banners).
- Impact: If any user-controlled string is placed in these HTML fragments without escaping, a crafted file name or uploader name could inject markup. Scope needs confirmation per fragment.
- Fix approach: Pass user-controlled values through `html.escape()` before interpolation.

**Development container disables XSRF and CORS protection:**
- Issue: The dev container starts Streamlit with `--server.enableCORS false --server.enableXsrfProtection false`.
- Files: `.devcontainer/devcontainer.json` (`postAttachCommand`).
- Impact: Protections are off for anyone who runs the dev container in a shared or forwarded environment (forwarded port 8501).
- Fix approach: Remove the two flags, or restrict the forwarded port to the owner.

**Google Fonts loaded from a third party:**
- Issue: The CSS imports Inter from `fonts.googleapis.com`, so every visitor's browser contacts Google.
- Files: `app.py` line 29.
- Impact: Minor privacy exposure; the app also depends on that external request for correct styling.
- Fix approach: Self-host the font or accept the trade-off explicitly.

## Data Integrity and Silent Passes (high priority)

**Missing reference files produce a clean result:**
- Issue: If a reference file is absent, the checks that depend on it are dropped silently rather than reported as failing. A layer with no checks gets full credit. Result: the file can score 100% and show CLEAN with no warning.
- Files:
  - `load_boundary_refs()` returns an empty DataFrame when `ward_boundary_ref.csv` is missing (lines 341-346). Rules B1 and B3 are only added when `ref_df` is non-empty (lines 548-600).
  - `load_ward_geoms()` returns an empty frame when the geometry file is missing (lines 348-356). Rule B2 is skipped (line 600 guard).
  - `load_health_facilities()` returns `{}` when the facility file is missing (lines 480-489). Rule 2 is skipped (`and hf_by_ward` guard in `run_mlos_qc`, around line 1218).
  - `load_settlement_extents()` returns `None` when the mask is missing (lines 443-445). Rule SQ6 is skipped (`extents is not None` guard, line ~767).
  - `_layer_pass_rate()` returns `1.0` when a layer has no checks (lines 1736-1744).
- Impact: A deployment with a missing data file, or a bad path after a redeploy, reports a clean file. Nothing in the UI says a check did not run.
- Fix approach: When a reference is missing, add an explicit FAIL check (for example "Reference data unavailable") and count it in the score. Surface a visible warning in the header.

**Rules are silently skipped when columns are missing:**
- Issue: Every rule after schema is wrapped in `if col in mlos.columns`. A file missing a column loses that rule without a FAIL entry. Schema alignment (S1) is only 10% of the weighted score, so a file with many missing columns can still score high.
- Files: `run_mlos_qc()` (lines 1194-1356; for example R3 at about line 1248, R9 at about line 1277, R10 at about line 1294, R11 at about line 1300, R12 at about line 1305); `run_settlement_qc()` (lines 646-797); `run_ward_boundary_qc()` (lines 506-645).
- Impact: The weighted score overstates quality for incomplete files.
- Fix approach: Record a FAIL (or a distinct SKIPPED state that counts against the score) for every rule whose input columns are absent.

**Auto Correct runs before QC and hides some rule failures:**
- Issue: `auto_correct_mlos()` runs first (line ~1645), then `run_mlos_qc()` runs on the corrected data. The corrections make these rules structurally unable to fail:
  - Rule 12 (`eha_guid` is a UUID) never fails. Invalid GUIDs are replaced with a fresh UUID4 in Auto Correct (lines 1157-1170) before R12 runs (around line 1305).
  - Rule 1 (not null) never fails for `eha_guid`, because empty values are replaced by generated UUIDs.
  - Rule 1 never fails for the flag columns (`highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `scattered`, `riverine`, `fulani`). Auto Correct fills their blanks first (lines 1089-1111). These columns are also in the Rule 1 NOT NULL list.
  - Auto Correct also fills `source` with `IE` and `reasons_for_inaccessibility` with `NA` for Fully Accessible rows.
- Files: `app.py` lines 1085-1174 (`auto_correct_mlos`), lines 1645-1650 (order of calls), rules R1 and R12 at lines ~1220-1240 and ~1305.
- Impact: The QC report says a rule passed when the underlying data was missing or invalid. The corrected workbook, which the UI says is "Ready for re-upload or submission", contains fabricated values.
- Fix approach: Run the rule checks on the raw data, then apply corrections as a separate, reviewed step. Alternatively, have Auto Correct log the original value for every change and keep the failing count from the raw data.

**Auto-generated GUIDs are non-deterministic:**
- Issue: Each invalid `eha_guid` is replaced with `uuid.uuid4()`. Running Auto Correct again on the same file yields different identifiers. Cached results mask this within a session, but re-uploads and new sessions do not match.
- Files: `app.py` lines 1162-1170.
- Impact: Records cannot be traced across runs, and the corrected export may duplicate or orphan records in the source system.
- Fix approach: Derive a deterministic identifier from stable fields (for example a UUID5 over `mlos_id` and `ward_code`), or flag the record for manual correction instead of generating one.

**Score measures rule count, not row impact:**
- Issue: `_layer_pass_rate()` counts passing rules divided by total rules. One failing row and ten thousand failing rows lower the score equally.
- Files: `app.py` lines 1736-1744, weights at lines 1729-1734.
- Impact: The headline "Weighted QC Score" is not a measure of data quality for a large file, and it is hard to compare across files of different sizes.
- Fix approach: Document this clearly in the UI, or add a row-based score alongside the rule-based score.

**Boundary fallback accepts ward codes from any state:**
- Issue: If filtering the boundary reference by the file's state names returns nothing, the full national reference is used.
- Files: `app.py` lines 548-560 (`filtered_ref` fallback).
- Impact: A ward code from the wrong state can pass Rule B1 when state filtering fails. Rule B3 partly compensates.
- Fix approach: Treat an empty state filter as a FAIL for B1, not a reason to widen the reference.

**Rule 11 editor format rejects valid names:**
- Issue: `EDITOR_RE = ^[a-z]+\.[a-z]+$` allows only lowercase letters with one dot. Hyphenated or apostrophed names, multi-part surnames, and names with digits fail.
- Files: `app.py` line 101 (`EDITOR_RE`), line ~1300 (R11), `vec_is_editor()` at lines 203-205.
- Impact: False failures on legitimate editor names, which trains users to ignore Rule 11.
- Fix approach: Relax the pattern to match the convention the team actually uses, and document the exception list.

**Row identifier fallback uses the first column:**
- Issue: When `ogc_fid` is absent, `id_col` falls back to `mlos.columns[0]`, whatever that column is.
- Files: `app.py` lines 521 (boundary), 1199 (MLoS), and the equivalent line in `run_settlement_qc()` (around line 653).
- Impact: Failing-row reports identify records by an arbitrary column for CSV and Excel uploads.
- Fix approach: Use an explicit identifier (for example `eha_guid` or `mlos_id`) and fail the upload if none is present.

**Takeoffpoint matching is heuristic:**
- Issue: Rule 2 uses fuzzy matching with a 0.8 similarity threshold, abbreviation expansion, and generic-word removal (lines 452-505).
- Files: `app.py` lines 452-505 (`HF_ABBREV`, `HF_GENERIC`, `HF_FUZZY_THRESHOLD`, `same_facility()`, `match_takeoffpoint()`).
- Impact: Some true mismatches may pass, and some near-identical names may be wrongly rejected. The tolerance is not documented for users.
- Fix approach: Add a fixtures-based test table of accepted and rejected names, and tune the threshold against it.

## Known Bugs

**Rule 12 and Rule 1 `eha_guid` checks cannot fail on upload:**
- Symptoms: The check always reports PASS for `eha_guid` format and nullability on any file.
- Files: `app.py` lines 1157-1170 and 1305, as described above.
- Trigger: Any upload with bad or blank `eha_guid` values.
- Workaround: Check `eha_guid` in the source data directly.

**Session-scoped logging and cache keys can duplicate or stale results:**
- Symptoms: The same file can be logged to State Results more than once. A different file with the same name and byte size reuses cached results.
- Files: The dedupe guard `results_saved_key` (lines 1753-1767) only lasts for one session. The cache keys use `(uploaded.name, size)` in `get_uploaded_data()` (lines 150-155) and `qc_cache_key` (line 1634).
- Trigger: Re-uploading a file in a new browser session or after an app restart; uploading a different file whose name and size match.
- Workaround: Include a content hash in the cache key, and dedupe log rows by file hash plus uploader within a time window.

**Usage database connections are not closed:**
- Symptoms: Connections accumulate until garbage collection.
- Files: `app.py` `_usage_db()` (lines 822-823). Each `with _usage_db() as conn:` commits on exit but does not close the connection.
- Trigger: Every rerun of the app (each sidebar change calls `init_usage_db()` and `render_state_results()`).
- Workaround: Wrap the call in `contextlib.closing(...)`.

**Rule-number collisions:**
- Symptoms: Multiple checks share a Rule# (for example `9` for urban, rural, and scattered; `9a`, `9b`; and `10` for all profile flags). Downstream logic has to match on Rule# plus check name.
- Files: `app.py` `make_longitudinal_df()` (lines 267-294), `build_state_results()` (lines 853-908, the `(Rule#, Rule)` grouping), `run_mlos_qc()` R9 and R10 loops.
- Trigger: Any consumer that matches on Rule# alone.
- Workaround: Always match on the pair (Rule#, QC Check).

## Security Considerations

Also covered above (access control, SMTP certificate verification, formula injection, unsafe HTML, dev container flags). Additional items:

**Uploaded files are read fully into memory:**
- Risk: `load_sqlite()` calls `uploaded_file.read()` and writes the whole file to a temporary SQLite file. CSV and Excel loads are also fully materialised as `dtype=str` DataFrames.
- Files: `app.py` lines 108-112 (`load_sqlite`), 124-130 (`load_csv`), 132-148 (`load_xlsx`).
- Current mitigation: Streamlit's default upload size limit. No limit is set in the repository.
- Recommendations: Set `server.maxUploadSize` explicitly in `.streamlit/config.toml`, and validate the file signature before opening a file as SQLite.

**Secrets handling is sound, with one gap:**
- Current mitigation: SMTP settings are read only from `st.secrets` (lines 1067-1076). `.gitignore` excludes `.streamlit/secrets.toml`, `*.db`, and `*.sqlite`, so the usage database is not committed.
- Recommendations: Confirm `usage_log.db` has never been committed (`git log --all -- '*.db' '*.sqlite'` returns no history in any branch). The default SMTP host `smtp.gmail.com` (line 1073) is a fallback that may not match the team's mail provider; make it explicit in secrets.

## Performance Bottlenecks

**Downloads are rebuilt on every rerun:**
- Problem: Streamlit reruns the whole script on each widget interaction. Workbooks are built eagerly before the download buttons render, whether or not the user clicks them.
- Files: `app.py` `build_corrected_excel()` at line 1914 (full dataset); `build_excel_report()` at line 2169; longitudinal workbook at lines 1948-1957; State Results workbook at lines 987-992 (also reads `usage_log` and `rule_results` on every rerun).
- Cause: Download `data=` arguments are evaluated eagerly.
- Improvement path: Cache the bytes with `@st.cache_data` keyed on the cache key, or generate them in an `on_click` callback.

**Settlement extent lookup is a Python loop over search cells:**
- Problem: `SettlementExtentMask.nearest()` iterates over every cell within the search radius in Python (about 2,209 offsets for the 500 m failure search at Nigerian latitudes), and each iteration calls `lookup()` over the remaining points.
- Files: `app.py` lines 414-441 (`nearest`), 389-412 (`lookup`).
- Cause: Vectorised over points, but not over offsets.
- Improvement path: Precompute a distance transform on the tile mask, or use a KD-tree over extent cell centres (`scipy.spatial.cKDTree` if added, or `shapely.STRtree` over extent points).

**Unbounded tile cache:**
- Problem: `SettlementExtentMask.cache` keeps every decoded tile for the life of the process. A full decode is about 35,500 tiles of 64 KB each, roughly 2.3 GB at most (non-empty tiles are fewer, but the cache has no bound).
- Files: `app.py` lines 366-387 (`__init__` and `_tile`), `load_settlement_extents()` at lines 443-445 (`st.cache_resource`).
- Improvement path: Use an LRU cache with a fixed size (for example `functools.lru_cache` on `_tile`).

**Per-state recomputation in the usage log:**
- Problem: `resolve_states(detail, ...)` runs over the whole detail frame once per state, so cost is states multiplied by failing rows.
- Files: `app.py` `build_state_results()` lines 853-908 (the `for state in ...` loop and `d = detail[resolve_states(detail, ref_df, default) == state]`).
- Improvement path: Resolve states once per layer before the state loop and group.

**Row-wise Python loops:**
- Problem: Rule 1 builds its "Null Fields" column with `DataFrame.apply(..., axis=1)`. `match_takeoffpoint()` runs `difflib.SequenceMatcher` for every unique (ward, takeoffpoint) pair against all facilities in the ward.
- Files: `app.py` around line 1245 (R1 `apply`), lines 492-503 (`match_takeoffpoint`), and the `iterrows()` loops in `build_excel_report()` at about lines 1458 and 1473.
- Improvement path: Vectorise the null-field label with a join over boolean columns; cache facility keys per ward.

**Session memory:**
- Problem: Full DataFrames (`mlos_df`, `mlos_df_corrected`, all detail frames) are held in `st.session_state` for every browser session with no eviction.
- Files: `app.py` lines 189-190 (`mlos_df`), 1705-1715 (QC results).
- Improvement path: Store only the detail frames needed for display, or clear session state when a new file is uploaded.

## Fragile Areas

**`app.py` is a single 2,202-line module:**
- Files: `app.py` (UI, QC engine, usage database, Excel building, email, and styling all in one file).
- Why fragile: Changes to one rule or export can break unrelated parts. Import-time side effects (`init_usage_db()` at line 1024, `st.set_page_config` at line 19) run on every rerun.
- Safe modification: Make changes in a branch, run the app against all four supported formats, and check each download. Keep rule functions pure (DataFrame in, checks and details out).
- Test coverage: None on this branch. The unmerged branch `origin/feature/qc-rules` contains a separate `qc` package and tests; those are not present here.

**Usage database schema:**
- Files: `app.py` lines 807-830 (`USAGE_TABLES`, `init_usage_db()`).
- Why fragile: All columns are created as `TEXT` with no types, keys, or uniqueness constraints. Numbers round-trip as strings and are re-parsed with `pd.to_numeric` in the UI. `CREATE TABLE IF NOT EXISTS` does not migrate existing tables, so any column change silently breaks inserts for a deployed database.
- Safe modification: Add a schema version table and a migration step before changing `USAGE_TABLES`.

**Shared State Results depends on column names:**
- Files: `app.py` `build_state_results()` (lines 853-908) and `render_state_results()` (lines 945-1021) reference `state_name`, `ward_code`, `lga_name`, `settlement_name`, `latitude`, `longitude`, and `Rule#`.
- Why fragile: Renaming a column in the source MLoS view silently moves rows to `Unknown` state or drops them from the detail.
- Safe modification: Keep these names in a single constants block and validate them at upload.

**Reference data is a snapshot with no refresh metadata:**
- Files: `ward_boundary_ref.csv`, `ward_boundary_geom.csv.gz`, `health_facility_ref.csv.gz`, `settlement_extent_mask.npz`; regeneration scripts in `scripts/build_*.py`.
- Why fragile: The app does not record which source version (for example the September 2026 boundary release named in `README.md`) produced each file. The build scripts take paths to external sqlite and gpkg files that are not in the repository.
- Safe modification: Store a manifest with source name, date, and checksum next to each reference file, and display it in the UI.

**Excel sheet-name and width logic:**
- Files: `app.py` lines 1989-1994 and 2057-2062 (`f"Rule {rn}"[:31]`).
- Why fragile: Sheet names are truncated to 31 characters without a uniqueness check, so two rule numbers that collide after truncation would overwrite each other. Rule numbers are not unique (see Known Bugs).
- Safe modification: Generate sheet names from a deduplicated index.

## Dependencies at Risk

**Unpinned dependencies and no lockfile:**
- Risk: `requirements.txt` sets only lower bounds (`streamlit>=1.32.0`, `pandas>=2.0.0`, `openpyxl>=3.1.0`, `xlrd>=2.0.1`, `shapely>=2.0.0`, `numpy>=1.24.0`). Builds are not reproducible across machines or deployments.
- Impact: A new major release can change behaviour (Streamlit API, pandas indexing) without a code change.
- Migration plan: Generate a lockfile (for example `pip-compile` output or `uv lock`) and pin the Python version (the dev container uses Python 3.11, `.devcontainer/devcontainer.json`).

**Requirement floor is below features in use:**
- Risk: `app.py` line 978 uses `Styler.map`, which requires pandas 2.1 or later. The declared floor is `pandas>=2.0.0`.
- Impact: A fresh install at the floor version fails when the State Results table renders.
- Migration plan: Raise the pandas floor to `>=2.1` or use `Styler.applymap` on 2.0.

**Deprecated Streamlit argument in many places:**
- Risk: `use_container_width=True` is passed to `st.dataframe` and `st.download_button` in roughly twenty places (for example lines 979, 1007, 1020, 1837, 1846, 2153).
- Impact: Newer Streamlit releases deprecate this argument in favour of width-based parameters, so a future upgrade will produce warnings and eventually break.
- Migration plan: Replace with the width parameter from the Streamlit release the team pins.

**`xlrd` for legacy `.xls`:**
- Risk: `xlrd` is maintained only for `.xls` reading. The app accepts `.xls` in the uploader (`app.py` line 1496).
- Impact: Limited, but the package receives little maintenance.
- Migration plan: Convert legacy files on upload, or drop `.xls` support.

## Missing Critical Features

**No test suite:**
- Problem: No automated tests exist on this branch. Every rule (S1, R1-R12, SQ1-SQ6, B0-B3), the auto-correct logic, and the usage-database logic are verified only by running the app.
- Blocks: Safe refactoring of `app.py`; confident changes to rule logic; regression checks for the issues in this document.

**No audit trail for sent emails or deleted data:**
- Problem: Emails are sent without a record of who sent them. There is no way to delete or correct a shared run.
- Blocks: Accountability for the data team's email; removing an erroneous or test run from State Results.

**No data retention policy in the app:**
- Problem: Shared fail rows and uploader names are kept indefinitely in a database that the README warns can be erased on restart.
- Blocks: A defensible position on how long settlement-level data is held.

## Test Coverage Gaps

**Rule logic:**
- What's not tested: Every QC rule and its boundary conditions, including the Rule 12 and Rule 1 interaction with Auto Correct.
- Files: `app.py` lines 646-797 (settlement), 1194-1356 (MLoS), 506-645 (boundary), 1085-1174 (auto correct).
- Risk: Silent passes (see Data Integrity) go unnoticed.
- Priority: High.

**Missing-reference behaviour:**
- What's not tested: The result when `ward_boundary_ref.csv`, `ward_boundary_geom.csv.gz`, `health_facility_ref.csv.gz`, or `settlement_extent_mask.npz` is absent.
- Files: `app.py` lines 341-356, 443-445, 480-489.
- Risk: A deployment with a missing file reports CLEAN.
- Priority: High.

**Three-format parity:**
- What's not tested: That the same logical MLoS data gives the same results from `.sqlite`, `.csv`, and `.xlsx` inputs (for example `dtype=str` and `keep_default_na=False` handling of the value `NA`).
- Files: `app.py` lines 108-148 (loaders).
- Risk: Format-specific false failures, especially for the `NA` value.
- Priority: Medium.

**Usage database and exports:**
- What's not tested: Logging with multi-state files, the `Unknown` state fallback, and the formula-injection behaviour of exports.
- Files: `app.py` lines 853-1021, 932-944.
- Risk: Incorrect state attribution; spreadsheet formula execution.
- Priority: Medium.

---

*Concerns audit: 2026-11-05*
