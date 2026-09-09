# Codebase Concerns

<!-- refreshed: 2026-09-09 -->

**Analysis Date:** 2026-09-09

## Tech Debt

**Auto-Correction Modifies Data Before QC:**
- Issue: `auto_correct_mlos()` (`app.py:700-784`) modifies the MLoS DataFrame before running QC checks, changing nulls to "NA", "N", or generating UUIDs. These changes are not reversible and obscure the original data quality issues.
- Files: `app.py:1369, 1604`
- Impact: Users cannot see the original data problems in their files. The QC report shows corrected data passing checks, but the underlying issues remain in production. Users may falsely believe data quality is better than it actually is.
- Fix approach: Either (1) run QC on original data and report issues separately from corrections, or (2) clearly label all corrected rows in the QC output and require user confirmation before corrections are applied.

**Hardcoded Email Recipients:**
- Issue: The `send_qc_email()` function (`app.py:636-692`) has hardcoded TO and CC email addresses for a specific organization.
- Files: `app.py:644-647`
- Impact: Cannot reuse this app for other organizations without code changes. Recipients are not configurable via secrets or environment variables.
- Fix approach: Move email addresses to `st.secrets`, add a configuration section in README for email setup.

**Boundary Reference Files Hardcoded and Required:**
- Issue: The app requires two CSV files (`ward_boundary_ref.csv` and `ward_boundary_bbox.csv`) to exist in the project root directory. If missing, boundary checks silently skip with fallback logic (`app.py:437-439`).
- Files: `app.py:371-380, 1349`
- Impact: (1) App cannot be deployed to new environments without copying these large CSVs (427KB + 394KB). (2) Boundary checks may fail silently if files are corrupted or outdated. (3) No version control or audit trail for when boundary data was last updated.
- Fix approach: (1) Document required boundary reference files explicitly. (2) Add startup validation to warn if boundary files are missing/outdated. (3) Consider loading from a database or versioned data service instead of loose CSV files.

**SQLite View Names Assumed to Exist:**
- Issue: The `get_uploaded_data()` function (`app.py:182-189`) assumes specific SQLite view names (`master_list_settlement_update_view`, `mlos_takeoffpoint_view`) exist without validation.
- Files: `app.py:88-89, 186-189`
- Impact: If a SQLite file is uploaded without these exact view names, the app crashes without a helpful error message (caught only in the try/except at line 1330-1334).
- Fix approach: Add a validation step to query available views and suggest alternatives if expected views don't exist.

**Scattered Column Dual Treatment:**
- Issue: The `scattered` column appears in both `FLAG_COLS` (line 697) and gets special-case handling (line 721-733) where it's corrected from NULL/"NA" to "N", separate from other flag columns which are corrected to "NA".
- Files: `app.py:695-733`
- Impact: Inconsistent auto-correction logic that could confuse users and make the auto-correct rules harder to document or maintain.
- Fix approach: Clarify if `scattered` should follow the same NULL → "NA" pattern as other flags, or if it genuinely should default to "N". Document this decision in README.

## Known Bugs

**Potential Data Loss in SQ4 (30m Proximity) on Large Datasets:**
- Symptoms: When checking settlements closer than 30m apart, the algorithm uses nested loops (O(n²) complexity, lines 614-627) which becomes slow for datasets with >1000 valid coordinates. May cause Streamlit to timeout or hang.
- Files: `app.py:599-631`
- Trigger: Upload a file with >1000 settlements that have valid coordinates. The proximity check will scan all pairs and may time out.
- Workaround: None currently. Users must split large files into smaller batches.

**B3 State Name Mismatch Uses drop_duplicates (Loses Information):**
- Symptoms: The boundary reference lookup for B3 (`app.py:464-482`) uses `drop_duplicates("ward_code")` which silently keeps only the first occurrence if a ward code maps to multiple state names. If the boundary reference has conflicting data, one mapping is silently discarded.
- Files: `app.py:466`
- Trigger: Boundary reference CSV has duplicate ward codes with different state names (data quality issue in the reference file itself).
- Workaround: Ensure the boundary reference has unique ward codes. If duplicates exist, manually clean the CSV.

**Email Sending Has No Error Handling:**
- Symptoms: If SMTP credentials are missing or invalid, the app crashes with an uncaught exception when "Send QC Email" button is clicked.
- Files: `app.py:689-692`
- Trigger: Click "Send QC Email" without valid `st.secrets` containing `smtp_host`, `smtp_user`, `smtp_pass`, `smtp_port`.
- Workaround: Ensure Streamlit secrets are configured before deploying.

**Fallback Boundary Reference Filter Could Bypass Intended Filtering:**
- Symptoms: Lines 437-439 fall back to the full (unfiltered) reference if state_name filtering returns no results. This could accidentally include ward codes from unintended states.
- Files: `app.py:437-439`
- Trigger: Upload MLoS data with a state_name that doesn't appear in the boundary reference CSV, or state names with spelling variations (e.g., "Kano" vs "KANO").
- Workaround: Ensure state names in MLoS data exactly match the boundary reference CSV (case-sensitive comparison on line 425).

## Security Considerations

**Hardcoded Email Recipients in Source Code:**
- Risk: If this repository is made public, organization email addresses are exposed. If the app is forked or modified, emails could be sent to unintended recipients.
- Files: `app.py:644-647`
- Current mitigation: None — email addresses are plaintext in the code.
- Recommendations: Move all email configuration to `st.secrets` file (which should be .gitignored). Add a startup check to validate email config exists before enabling the "Send QC Email" button.

**SQLite File Handling:**
- Risk: The `load_sqlite()` function (`app.py:104-108`) writes uploaded SQLite files to a temporary file. If the cleanup on line 195 fails, the file persists on disk.
- Files: `app.py:104-108, 194-197`
- Current mitigation: Try/except block attempts cleanup, but silently ignores errors.
- Recommendations: Implement proper context manager pattern or use `TemporaryDirectory` to ensure cleanup. Consider scanning uploaded files for SQL injection or malicious queries before execution.

**SMTP Credentials in Secrets:**
- Risk: Streamlit secrets are stored locally or in the cloud. If exposed, the SMTP account can be compromised.
- Files: `app.py:678, 684-687`
- Current mitigation: None (relies on Streamlit's secrets management).
- Recommendations: Use an app password or OAuth2 instead of plaintext password. Rotate SMTP credentials regularly.

## Performance Bottlenecks

**SQ4 Settlement Proximity Check is O(n²):**
- Problem: The haversine distance calculation (lines 614-627) compares every settlement with every other settlement using nested loops. For n=1000, this is ~500K comparisons; for n=10,000 it's ~50M.
- Files: `app.py:599-631`
- Cause: Naive nested loop implementation. No spatial indexing (e.g., quadtree, KD-tree) or distance matrix optimization.
- Improvement path: (1) Use a spatial index library (e.g., `scipy.spatial.KDTree`) to reduce comparisons to O(n log n). (2) Add a progress bar during the calculation. (3) Consider pre-computing distance matrix if the same dataset is checked multiple times.

**Streamlit Full Page Re-renders on Every Button Click:**
- Problem: Streamlit reruns the entire script when any button is clicked. For large datasets (>10K rows), the dataframe display tabs (`tab3`, `tab4`, etc.) may be slow.
- Files: `app.py:1498-1699`
- Cause: Streamlit's reactive model recomputes all visualizations and dataframe displays on every interaction.
- Improvement path: (1) Paginate large detail tables (e.g., show 500 rows per page). (2) Use Streamlit's `@st.cache_data` for expensive computations. (3) Add lazy loading for expandable sections.

**No Pagination for Large QC Detail Tables:**
- Problem: All failing rows are displayed in a single dataframe without pagination. For files with 10K+ failing rows, rendering becomes slow.
- Files: `app.py:1643, 1660, 1689-1690`
- Cause: Direct `st.dataframe()` calls with no pagination or limits.
- Improvement path: Add pagination controls or limit display to first 1000 rows with a warning message for larger result sets.

**All QC Layers Run Sequentially:**
- Problem: Schema, MLoS, Settlement, Takeoffpoint, and Boundary checks run one after another (lines 1376-1422). If one layer is slow, the entire QC is delayed.
- Files: `app.py:1365-1422`
- Cause: Sequential execution in a single `st.status()` block.
- Improvement path: Consider parallel execution for independent QC layers (e.g., run MLoS and Settlement checks in parallel). Would require refactoring to support concurrent execution.

## Fragile Areas

**File Upload Type Detection by Extension:**
- Files: `app.py:167-197`
- Why fragile: The code assumes file extensions are reliable. Files without extensions or with wrong extensions (e.g., .csv file named "data.sqlite") will be mishandled. No MIME type validation.
- Safe modification: Add file type validation before processing (e.g., check file magic bytes or MIME type). Add explicit user feedback on which format was detected.
- Test coverage: No tests for edge cases like missing extensions or mismatched format/extension.

**Data Type String Assumption Across All Columns:**
- Files: `app.py:126, 153-154`
- Why fragile: All columns are read as strings (`dtype=str`), then selectively converted to numeric. If a column is expected to be numeric but contains text, it silently fails to coerce and becomes NaN, potentially hiding data issues.
- Safe modification: Add schema validation after loading to ensure critical columns are actually numeric. Warn users if unexpected data types are detected.
- Test coverage: No tests for mixed data types or unexpected column contents.

**Regex Patterns Not Escaped Properly:**
- Files: `app.py:96-97, 210-216`
- Why fragile: UUID_RE and EDITOR_RE regex patterns are simple but not thoroughly tested. If the pattern is wrong, validation fails silently. No test data for edge cases (e.g., UUIDs with non-canonical case, editors with apostrophes in names).
- Safe modification: Add unit tests for UUID and editor format validation. Consider using a proper UUID validation library instead of regex.
- Test coverage: No unit tests for these regex patterns.

**Ward Code Merging Logic in Boundary Checks:**
- Files: `app.py:464-482, 493-512`
- Why fragile: Multiple merge operations (`merge()` calls on lines 473, 497) with `how="left"` assume row indices remain stable and aligned. If the index is accidentally reset or modified, the mappings break.
- Safe modification: Explicitly verify index alignment after each merge. Add assertions or logging to catch index mismatches.
- Test coverage: No tests for boundary check accuracy with varied ward code formats or missing data.

## Scaling Limits

**Memory Usage with Large Files:**
- Current capacity: Can handle ~100K+ rows comfortably on a typical machine (8GB RAM). DataFrame copies in `auto_correct_mlos()` and multiple QC functions duplicate the dataset in memory.
- Limit: Files with >500K rows may cause Streamlit to crash due to memory exhaustion.
- Scaling path: (1) Implement chunked processing for very large files. (2) Use Apache Parquet or HDF5 format instead of CSV/XLSX for large datasets. (3) Stream data instead of loading the entire file into memory.

**SQLite Temporary File Storage:**
- Current capacity: Temporary files are written to the system's temp directory. On shared systems, this could fill up quickly with multiple concurrent uploads.
- Limit: If many users upload large SQLite files simultaneously, `/tmp` or equivalent fills up and the app crashes.
- Scaling path: (1) Use a dedicated temp directory with size quotas. (2) Implement file cleanup before upload. (3) Add a max file size check before accepting uploads.

**Concurrent QC Runs:**
- Current capacity: Each user has their own Streamlit session, so concurrent QC runs don't directly block each other. However, loading large boundary reference CSVs is repeated per session.
- Limit: With 100+ concurrent users, loading boundary references 100+ times (instead of once globally) wastes I/O and memory.
- Scaling path: Move boundary reference loading to a global cache (e.g., `@st.cache_data`) with proper invalidation strategy.

## Dependencies at Risk

**openpyxl >= 3.1.0 (Excel Generation):**
- Risk: `openpyxl` is used for building Excel reports. Version constraints are loose (`>=3.1.0`). Major version bumps may break API.
- Impact: If openpyxl 4.0 is released with breaking changes, Excel report generation fails.
- Migration plan: Pin openpyxl to `>=3.1.0, <4.0.0` in requirements.txt. Monitor openpyxl changelog for deprecations.

**streamlit >= 1.32.0:**
- Risk: Streamlit has frequent releases with API changes. Version constraints are loose. Session state and caching APIs may change.
- Impact: If Streamlit 2.0 introduces breaking changes to `st.session_state` or `@st.cache_data`, the app breaks.
- Migration plan: Pin Streamlit to `>=1.32.0, <2.0.0`. Test each minor version before deploying.

**pandas >= 2.0.0:**
- Risk: pandas 2.0 introduced breaking changes (e.g., removals of deprecated functions). Future versions may continue this trend.
- Impact: If pandas 3.0 removes `pd.concat()` or changes merge behavior, QC logic breaks.
- Migration plan: Pin pandas to `>=2.0.0, <3.0.0`. Keep unit tests for all data operations.

**xlrd >= 2.0.1 (Legacy Excel Support):**
- Risk: xlrd is not actively maintained for `.xls` (older Excel format) support. Bug fixes are infrequent.
- Impact: `.xls` files may not load correctly if they have non-standard formatting. No alternative library is specified.
- Migration plan: Consider deprecating `.xls` support (xls is legacy; users should use .xlsx). Alternatively, add openpyxl as fallback for reading .xls files.

## Missing Critical Features

**No Data Validation Before QC:**
- Problem: The app loads data with minimal validation. If a CSV has 0 rows, special characters, or unexpected encodings, the QC may produce misleading results.
- Blocks: Cannot ensure data quality assessment is reliable.
- Fix: Add a pre-QC validation step to check file integrity, encoding, and basic structure.

**No Undo for Auto Corrections:**
- Problem: Users cannot see the original data or easily revert auto corrections to compare.
- Blocks: Users cannot verify whether corrections were appropriate for their use case.
- Fix: Provide a download option for the original uncorrected data alongside the corrected version.

**No QC Audit Trail or History:**
- Problem: Each QC run is independent. There's no history of what was checked, when, or how results changed over time.
- Blocks: Cannot track data quality trends or audit compliance.
- Fix: Store QC results in a database with timestamps and file metadata.

**No Data Reconciliation Between Uploads:**
- Problem: If a user uploads the same file twice with minor changes, the app treats them as independent QC runs. No diff or comparison.
- Blocks: Hard to identify what changed between runs.
- Fix: Add a "Compare QC Runs" feature to highlight differences between consecutive uploads.

## Test Coverage Gaps

**No Unit Tests for QC Functions:**
- What's not tested: `run_mlos_qc()`, `run_settlement_qc()`, `run_ward_boundary_qc()` are complex with many branches. Edge cases (empty dataframes, single row, all nulls, special characters) are not tested.
- Files: `app.py:805-965, 539-633, 383-536`
- Risk: Regression bugs in QC logic could be deployed without detection. Rule logic changes could introduce false positives/negatives.
- Priority: High — QC correctness is critical.

**No Tests for File Loading:**
- What's not tested: `load_sqlite()`, `load_xlsx()`, `load_csv()` are untested. Edge cases: malformed files, missing sheets, encoding issues.
- Files: `app.py:104-155`
- Risk: File loading failures are only caught by the broad try/except in the UI, which hides the root cause.
- Priority: High — file loading is the entry point.

**No Tests for Email Sending:**
- What's not tested: `send_qc_email()` is never tested. SMTP connection, credential validation, email formatting are untested.
- Files: `app.py:636-692`
- Risk: Email sending can fail silently if secrets are misconfigured or SMTP server is down.
- Priority: Medium — affects reporting functionality but not core QC.

**No Tests for Auto Correction:**
- What's not tested: `auto_correct_mlos()` has complex logic for handling nulls, NAs, and UUID generation. Edge cases: conflicting corrections, data already corrected, special characters.
- Files: `app.py:700-784`
- Risk: Auto corrections could corrupt data or fail silently if edge cases are encountered.
- Priority: High — auto corrections are applied to user data.

**No Integration Tests:**
- What's not tested: End-to-end workflows (upload file → run QC → download report) are untested.
- Files: Entire `app.py`
- Risk: UI bugs, workflow logic errors, state management issues are not caught.
- Priority: High — integration failures block users completely.

**No Performance/Load Tests:**
- What's not tested: App behavior with large files (>100K rows), concurrent uploads, or long-running QC processes.
- Files: `app.py:599-631` (SQ4 performance-sensitive)
- Risk: App may timeout or crash under load without warning. No baseline for scaling decisions.
- Priority: Medium — affects real-world usage with large datasets.

---

*Concerns audit: 2026-09-09*
