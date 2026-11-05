# Testing Patterns

**Analysis Date:** 2026-11-05

## Current State

**No automated tests exist in the working tree.** There is no test framework dependency, no test directory, no `test_*.py` or `*_test.py` files, no `conftest.py`, no `pytest.ini`, `tox.ini`, `setup.cfg`, or `pyproject.toml`, and no CI workflow. `requirements.txt` lists only runtime dependencies (`streamlit`, `pandas`, `openpyxl`, `xlrd`, `shapely`, `numpy`).

Verification today is manual: upload a file in the running app and read the QC results, the Excel report, and the State Results tab. Treat any change to a QC rule as untested until it has been checked this way.

## Test Framework

**Runner:**
- Not configured. Recommended runner is `pytest`, which is not yet listed in `requirements.txt`.
- Config: none. Add a `pytest.ini` or `pyproject.toml` section when tests are introduced.

**Assertion Library:**
- Not applicable yet. Use plain `assert` with pytest.

**Run Commands (once pytest is added):**
```bash
pip install pytest                      # one-time, dev only
python -m pytest -q                     # Run all tests
python -m pytest tests/test_mlos_qc.py::test_rule_1 -q   # Run one test
python -m pytest --cov=. --cov-report=term-missing       # Coverage (requires pytest-cov)
```

**Manual verification commands (available now):**
```bash
streamlit run app.py                    # Open http://localhost:8501 and upload a file
python -m pyflakes app.py               # Lightweight static check, if pyflakes is installed
```

## Why `app.py` Is Hard to Import in Tests

`app.py` runs Streamlit calls at import time. Importing it executes, in order:
- `st.set_page_config(...)` and `st.markdown(<style>...)` (`app.py:19-90`),
- the sidebar and file uploader (`app.py` sidebar block starting at `app.py:1490`),
- `st.stop()` calls when no file is uploaded (`app.py:1613`, `app.py:1621`),
- `init_usage_db()` at module level (`app.py:1024`), which creates `usage_log.db` next to the app.

Any test that does `import app` will therefore fail outside a Streamlit runtime or will touch the usage database. Two ways to handle this:

1. **Test through Streamlit's `AppTest` harness (no refactor needed).** `streamlit.testing.v1.AppTest` runs the script headlessly and exposes widgets and rendered elements:
   ```python
   from streamlit.testing.v1 import AppTest

   def test_app_renders_without_upload():
       at = AppTest.from_file("app.py", default_timeout=30).run()
       assert not at.exception
       assert any("Upload your MLoS file" in m.value for m in at.info)
   ```
   Use this for smoke tests of the page. Setting an uploaded file in `AppTest` is not supported directly, so end-to-end upload tests need a different approach.

2. **Move the pure QC functions into an importable module (recommended for rule tests).** The QC functions take DataFrames and return `(checks, details)`, so they do not need Streamlit. The clean split is to move the non-UI helpers (`pct`, `vec_is_uuid`, `vec_is_editor`, `run_schema_qc`, `make_longitudinal_df`, `facility_key`, `same_facility`, `match_takeoffpoint`, `run_mlos_qc`, `run_settlement_qc`, `run_ward_boundary_qc`, `auto_correct_mlos`, `SettlementExtentMask`) into a module such as `qc_rules.py` at the repository root, and have `app.py` import from it. Keep the reference files at the root, and keep the `*_PATH` constants relative to the module that loads them.

   Until that split exists, a quick local workaround for experiments is to stub Streamlit before import, but do not commit that approach.

## Test File Organization

**Location (recommended):**
- Separate `tests/` directory at the repository root, not co-located, because `app.py` and the QC modules sit at the root and the reference data is loaded relative to them.

**Naming (recommended):**
- `tests/test_<area>.py`, with one file per QC layer:
  - `tests/test_schema_qc.py` for `run_schema_qc` (`S1`).
  - `tests/test_mlos_qc.py` for `run_mlos_qc` (Rules `1` to `12`).
  - `tests/test_settlement_qc.py` for `run_settlement_qc` (`SQ1` to `SQ6`).
  - `tests/test_boundary_qc.py` for `run_ward_boundary_qc` (`B0` to `B3`).
  - `tests/test_auto_correct.py` for `auto_correct_mlos` and `build_corrected_excel`.
  - `tests/test_usage_log.py` for `build_state_results` and the usage-database helpers.

**Structure (recommended):**
```
repository root
├── app.py
├── qc_rules.py            # proposed split of the pure QC functions
├── tests/
│   ├── conftest.py        # shared DataFrame fixtures and reference loaders
│   ├── test_schema_qc.py
│   ├── test_mlos_qc.py
│   ├── test_settlement_qc.py
│   ├── test_boundary_qc.py
│   ├── test_auto_correct.py
│   └── test_usage_log.py
```

## Test Structure

**Suite Organization (recommended pattern, matches how the QC functions are written):**
```python
import pandas as pd
import pytest

from qc_rules import run_mlos_qc


def _base_row(**overrides):
    row = {
        "ogc_fid": "1", "state_code": "NG-01", "state_name": "Example", "lga_code": "L1",
        "lga_name": "Example LGA", "ward_name": "W1", "ward_code": "W001",
        "settlement_name": "Settlement A", "takeoffpoint": "Clinic A",
        "latitude": "9.1", "longitude": "7.4", "security_compromised": "N",
        "accessibility_status": "Fully Accessible", "reasons_for_inaccessibility": "NA",
        "habitational_status": "Inhabited", "set_population": "100", "set_target": "20",
        "number_of_household": "20", "noncompliant_household": "0",
        "urban": "Y", "rural": "N", "scattered": "N", "highrisk": "NA", "slums": "NA",
        "densely_populated": "NA", "hard2reach": "NA", "border": "NA", "nomadic": "NA",
        "riverine": "NA", "fulani": "NA", "timestamp": "2026-01-01 10:00",
        "eha_guid": "00000000-0000-0000-0000-000000000000",
        "settlementarea_globalid": "00000000-0000-0000-0000-000000000001",
    }
    row.update(overrides)
    return row


def _status(checks, rule):
    return next(c["Status"] for c in checks if c["Rule#"] == rule)


def test_rule_1_flags_blank_required_field():
    df = pd.DataFrame([_base_row(state_name="")], dtype=str)
    checks, _ = run_mlos_qc(df, hf_by_ward={})
    assert "FAIL" in _status(checks, "1")
```

**Patterns:**
- Build inputs as DataFrames with `dtype=str` and `keep_default_na=False` semantics, to match the loaders. A blank cell is `""`, and `"NA"` is a valid value. Do not build fixtures with `None` for flag columns unless the test is about NULL handling.
- Assert on the check record, not on the detail text. Each check is a dict with `Rule#`, `QC Check`, `Failing Rows`, `Total Rows`, `Fail %`, and `Status` (`"❌ FAIL"` or `"✅ PASS"`). Test `"FAIL" in status` or `"PASS" in status`, as `_layer_pass_rate` does.
- For the detail output, assert on the `Rule#` and row identifiers in the DataFrame returned in `details`.
- Use one behaviour per test and name it after the rule: `test_rule_2_takeoffpoint_must_match_ward_facility`.
- Use `@pytest.mark.parametrize` for the valid-value sets (`VALID_DAY`, `VALID_YN_NA`, `VALID_ACC`, `VALID_HAB`) and for name normalisation cases in `SQ1`.

**Setup and teardown:**
- Use pytest fixtures for shared inputs, not `setUp`/`tearDown`. Put reference loaders in `tests/conftest.py` as session-scoped fixtures, because the geometry and extent files are large (`ward_boundary_geom.csv.gz` is about 8 MB, `settlement_extent_mask.npz` about 19 MB).
- For usage-database tests, use `tmp_path` and point `USAGE_DB_PATH` at a temporary file with `monkeypatch.setattr`. Never write to the real `usage_log.db` from a test.
- For `SQLite` input tests, use `tmp_path` and create a small database with the view name `master_list_settlement_update_view` (`MLOS_VIEW`).

## Mocking

**Framework:** None in use. `unittest.mock` (standard library) is available and is the default choice.

**What to mock (recommended):**
- `st.secrets` and SMTP in `send_qc_email`: patch `smtplib.SMTP` and provide secrets through a monkeypatched `st.secrets`. The function reads `smtp_user`, `smtp_pass`, `smtp_host`, and `smtp_port` with `.get`, so a plain dict is enough for a test double.
- `datetime.now` when a test asserts on the generated timestamp in the email body or usage row.
- `uuid.uuid4` when a test asserts on run IDs (`run_id` is `uuid.uuid4().hex[:12]`).
- File uploads: pass a `BytesIO` with a `.name` attribute, since `get_uploaded_data` reads `uploaded_file.name` and `uploaded_file.size`. A small helper class is enough:
  ```python
  from io import BytesIO

  class FakeUpload(BytesIO):
      def __init__(self, data: bytes, name: str):
          super().__init__(data)
          self.name = name
          self.size = len(data)
  ```

**What NOT to mock:**
- pandas and numpy. The QC logic is vectorised pandas code, and the value of a test comes from running it on real frames.
- `shapely` geometry for the boundary checks. Use a few real polygons (WKB or shapely objects) so that the point-in-polygon and `dwithin` behaviour is tested.
- The Excel builders. Read the bytes back with `openpyxl.load_workbook(BytesIO(data))` to assert on sheet names, header fill, and column count.

## Fixtures and Factories

**Test Data (recommended):**
- Build a minimal MLoS frame with a `_base_row(**overrides)` factory like the example above. Keep the set of columns in step with `MLOS_REQUIRED_COLS` (`app.py:208`). If that set changes, update the factory.
- Keep one known-good row that passes every rule, and derive each failing case by overriding one field. This makes each test's cause obvious.
- For the reference data, use small hand-written frames with the same columns as the bundled files:
  - `ward_boundary_ref.csv`: `state_code, state_name, lga_code, lga_name, ward_code, ward_name`.
  - `health_facility_ref.csv.gz`: facility name and ward code columns, read through `load_health_facilities`.

**Location:**
- Put shared fixtures in `tests/conftest.py`.
- Put large fixtures in `tests/data/` only if they are small (under about 50 KB). The repository already ships the full reference files at the root, so tests should load those by path rather than copying them.

**Reference data in tests:**
- Use the real `ward_boundary_ref.csv` for `resolve_states` and state-name tests, since the state spelling rules depend on it.
- Use `run_settlement_qc(mlos, extents=None)` for SQ1 to SQ5 and pass a real `SettlementExtentMask` only for SQ6.

## Coverage

**Requirements:** None enforced. There is no coverage threshold and no coverage tool configured.

**View Coverage (once pytest-cov is added):**
```bash
python -m pytest --cov=. --cov-report=term-missing
```

**Priority for first tests (highest QC impact first):**
1. `run_mlos_qc` Rules `1` to `12`. The MLoS layer carries 60% of the weighted score (`LAYER_WEIGHTS["mlos"]`, `app.py:1729`).
2. `auto_correct_mlos` (`app.py:1089`). It changes the data that is exported and must be exact.
3. `run_settlement_qc` SQ1 to SQ6 (20% of the score).
4. `run_ward_boundary_qc` B0 to B3 (10%).
5. `run_schema_qc` S1 (10%).
6. Usage-database writes and `build_state_results` (`app.py:853`), which feed the shared State Results tab.

## Test Types

**Unit Tests (recommended scope):**
- One QC rule per test, using in-memory DataFrames. Include a passing row and a failing row for every rule, plus one NULL or blank case and one `"NA"` case for the flag columns.
- Pure helpers: `pct`, `vec_is_uuid`, `vec_is_editor`, `facility_key`, `same_facility`, `_layer_pass_rate`, and `make_longitudinal_df`.

**Integration Tests (recommended scope):**
- Run the full pipeline on a small sample file: `run_schema_qc` followed by `run_mlos_qc`, `run_settlement_qc`, `run_ward_boundary_qc`, and the score calculation, then check the weighted score and the number of PASS and FAIL checks.
- Round-trip the Excel outputs: build with `build_excel_report`, `build_corrected_excel`, and `build_longitudinal_mlos`, then read them back with `openpyxl`.
- `AppTest` smoke test that the page renders with no file and with a small uploaded file once the upload helper is available.

**E2E Tests:**
- Not used. Manual testing in a browser is the current practice (see Current State).

## Common Patterns

**Asserting a rule fails on a bad row:**
```python
def test_rule_x_flags_bad_value():
    df = pd.DataFrame([_base_row(accessibility_status="Unknown")], dtype=str)
    checks, details = run_mlos_qc(df, hf_by_ward={})
    check = next(c for c in checks if c["Rule#"] == "<rule id>")
    assert "FAIL" in check["Status"]
    assert check["Failing Rows"] == 1
```

**Asserting a rule passes on a good row:**
```python
def test_rule_x_passes_on_valid_row():
    df = pd.DataFrame([_base_row()], dtype=str)
    checks, _ = run_mlos_qc(df, hf_by_ward={})
    check = next(c for c in checks if c["Rule#"] == "<rule id>")
    assert "PASS" in check["Status"]
```

**Asserting the NA domain value survives loading:**
```python
def test_loader_keeps_na_as_value():
    csv = BytesIO(b"highrisk\nNA\n")
    csv.name = "x.csv"
    from qc_rules import load_csv   # once split out of app.py
    df = load_csv(csv)
    assert df.loc[0, "highrisk"] == "NA"
```

**Asserting blank cells are caught as NULL, not as a string:**
```python
def test_blank_required_field_is_null():
    df = pd.DataFrame([_base_row(state_name="   ")], dtype=str)
    checks, details = run_mlos_qc(df, hf_by_ward={})
    assert "FAIL" in next(c["Status"] for c in checks if c["Rule#"] == "1")
```

**Asserting a QC function does not raise on bad data:**
```python
def test_rule_layer_does_not_raise_on_missing_coordinates():
    df = pd.DataFrame([_base_row(latitude="", longitude="")], dtype=str)
    checks, _ = run_settlement_qc(df)
    assert any("FAIL" in c["Status"] for c in checks if c["Rule#"] == "SQ2")
```

**Asserting the usage-database write (with a temp file):**
```python
def test_usage_db_init(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "usage_log.db"
    monkeypatch.setattr("qc_rules.USAGE_DB_PATH", str(db))   # adjust module name after the split
    # call init_usage_db(), then:
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"usage_log", "state_runs", "rule_results", "fail_rows"} <= tables
```
Check the exact table names in `USAGE_TABLES` (`app.py:819`) before you write the assertion.

**Error-path test for email:**
```python
def test_send_email_reports_missing_secrets(monkeypatch):
    # send_qc_email reads st.secrets with .get and calls smtplib.SMTP.
    # Patch smtplib.SMTP to raise, then assert the caller shows the error message
    # (the UI path is in app.py, so this is covered by the AppTest smoke test).
    ...
```

## Manual QA Checklist (until tests exist)

Run this checklist after any change to a QC rule, a loader, or an export:

1. `streamlit run app.py`, then upload one `.sqlite`, one `.csv`, and one `.xlsx` file with the same content. Each should produce the same check counts.
2. Confirm the Schema tab lists the expected missing columns for a file with a column removed.
3. Confirm the Auto Correct tab shows the expected rows fixed for `highrisk` NULL values and `eha_guid` UUID repairs.
4. Confirm `NA` values in the flag columns are not reported as blanks.
5. Download the Excel QC report and the longitudinal MLoS report; open them and check the sheet names and the red and green fills on rule columns.
6. Tick **Share results with team** off for test runs so they are not written to the shared usage database. Confirm the State Results tab does not change.
7. For changes that touch the email, send to a test recipient only, since the recipient list is hard-coded in `send_qc_email` (`app.py:1034-1035`).

## Test Data Safety

- Do not put real facility, settlement, or respondent data into test fixtures or committed test files. Use invented names and codes.
- Do not commit `usage_log.db`, which is git-ignored (`.gitignore`, `*.db`). Tests must write to `tmp_path`.
- Do not commit `.streamlit/secrets.toml`. Tests that need SMTP settings must monkeypatch them.

---

*Testing analysis: 2026-11-05*
