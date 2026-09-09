# Testing Patterns

**Analysis Date:** 2026-09-09

## Current Testing Status

**Framework:** Not detected

**Summary:** 
This project has **no automated tests, no test framework, and no test infrastructure**. The application is a monolithic Streamlit web app (`app.py`) with no separation of logic that would support unit testing. All QC validation logic is embedded in the main application file without test-oriented design patterns.

## Test File Organization

**Location:** Not applicable — no test files present

**Naming:** N/A

**Structure:** N/A

## Why Testing Is Absent

### 1. Streamlit Application Design
The application is built as a Streamlit interactive web app, which makes traditional unit testing difficult:
- Streamlit code relies on global state and session state management (`st.session_state`)
- Functions tightly coupled to Streamlit UI components (`st.error()`, `st.warning()`, `st.progress()`)
- Page execution model reruns entire script on interaction

**Examples of Streamlit coupling:**
- Lines 1330-1334: `with st.spinner("Loading file…"): try: ... except Exception as e: st.error(...)`
- Lines 1364-1426: Status updates via `st.progress()`, `st.status()`, `st.write()`
- Lines 1173-1198: Sidebar UI definition tightly integrated with file upload logic

### 2. Single-File Monolithic Structure
- All logic in one file (`app.py`, 1961 lines)
- No separation of concerns into testable modules
- No reusable business logic layer
- QC validation functions are defined in the same file as UI code

### 3. Heavy DataFrame Dependencies
- Core validation logic operates on pandas DataFrames
- Logic requires full data context to test (e.g., `run_mlos_qc(mlos: pd.DataFrame, takeoff: pd.DataFrame)`)
- No repository or data access layer abstraction
- File I/O operations (SQLite, CSV, Excel) embedded in main code path

## Validation and QC Logic (Not Tests)

While there are no automated tests, the application contains extensive data validation rules executed at runtime:

### QC Engine Functions (Self-Contained Validators)

**Pattern:** Functions return `(checks, details)` tuples for inspection

| Function | Lines | Purpose | Testable Logic |
|----------|-------|---------|----------------|
| `run_schema_qc()` | 232-278 | Validates required columns present | Yes — deterministic input/output |
| `run_mlos_qc()` | 805-965 | 14 data quality rules (NOT NULL, format, value domain) | Yes — deterministic |
| `run_settlement_qc()` | 539-633 | 5 location/uniqueness rules (duplicates, coordinates, distance) | Yes — deterministic |
| `run_takeoff_qc()` | 969-1012 | 4 cross-table rules | Yes — deterministic |
| `run_ward_boundary_qc()` | 383-536 | 4 geospatial rules (ward codes, coordinates in bounds) | Yes — deterministic |

**Example QC Logic Pattern (lines 826-857, Rule 1 from `run_mlos_qc()`):**
```python
# R1 — All schema NOT NULL fields must not be null
_NOT_NULL_COLS = [c for c in [
    "state_code", "state_name", "lga_code", ..., "settlementarea_globalid",
] if c in mlos.columns]
if _NOT_NULL_COLS:
    _null_mask = mlos[_NOT_NULL_COLS].isnull().any(axis=1)
    _n1 = int(_null_mask.sum())
    checks.append({
        "Rule#": "1", "QC Check": "Required Fields — Not Null",
        "Description": "All schema NOT NULL fields must not be empty: ...",
        "Failing Rows": _n1, "Total Rows": total,
        "Fail %": pct(_n1, total),
        "Status": "❌ FAIL" if _n1 else "✅ PASS",
    })
```

**Input/Output:** 
- **Input:** Pandas DataFrame with actual data
- **Output:** List of check dicts + detail DataFrame
- **Deterministic:** Yes — same data produces same results every time
- **Testable:** Could be tested with fixture DataFrames, but requires extracting from UI

## What Needs Testing

### High-Priority Validation Logic (Should Have Tests)

**1. Schema QC (`run_schema_qc`)**
- Required: Validate that all 43 MLoS columns and 4 Takeoffpoint columns are detected
- Test cases needed:
  - DataFrame with all required columns → `Status: ✅ PASS`
  - DataFrame missing 1+ required columns → `Status: ❌ FAIL` + detail rows
  - Empty DataFrame → appropriate fail status

**2. MLoS Rules (14 rules in `run_mlos_qc`)**
Most critical for data quality:
- **Rule 1:** Null checks on NOT NULL fields
- **Rule 2-4:** Cross-table validation (takeoffpoint name, code, ward code match)
- **Rule 5-8:** Enum validation (Y/N, accessibility status, habitational status)
- **Rule 9-10:** Numeric range checks (target ≤ population)
- **Rule 11:** Urban/rural/scattered logic (no conflicts)
- **Rule 12:** Profile flags validation
- **Rule 13:** Editor format validation (firstname.surname)
- **Rule 14:** UUID validation

**3. Settlement QC (`run_settlement_qc`)**
- **SQ1:** Duplicate settlement names within ward → should flag rows
- **SQ2/SQ2b:** Null/zero coordinate checks → should flag rows
- **SQ3:** Stacked coordinates (identical lat/lon) → should flag all duplicates
- **SQ4:** Distance check (30m minimum) → Haversine calculation correctness critical

**4. Boundary QC (`run_ward_boundary_qc`)**
- **B0-B3:** Ward code existence, coordinate bounds, state name match
- Requires reference data (ward_boundary_ref.csv, ward_boundary_bbox.csv)
- Most failure-prone due to external data dependency

**5. Data Transformations**
- `auto_correct_mlos()` — applies 5 automatic corrections; needs verification that corrections are lossless and correct
- `load_xlsx()`, `load_csv()`, `load_sqlite()` — file loading with keep_default_na=False; needs to verify "NA" is preserved

### Test-Unfriendly Areas

**Hard to Test Without Refactoring:**
- File upload handling (Streamlit UploadedFile objects)
- Email sending (`send_qc_email()` requires SMTP credentials from secrets)
- Excel report generation (needs openpyxl style verification)
- Streamlit session state management
- Progress bar updates during QC

## Recommended Testing Approach

### Phase 1: Extract Core QC Logic (Refactoring)
Create a `qc_engine.py` module with pure functions that accept DataFrames and return results:

```python
# qc_engine.py
def validate_schema(mlos_df: pd.DataFrame, takeoff_df: pd.DataFrame) -> Tuple[List[Dict], pd.DataFrame]:
    """Pure function — no Streamlit dependencies."""
    checks, details = [], []
    # ... validation logic from run_schema_qc() ...
    return checks, details

def validate_mlos(mlos_df: pd.DataFrame, takeoff_df: pd.DataFrame) -> Tuple[List[Dict], pd.DataFrame]:
    """Pure function — no Streamlit dependencies."""
    checks, details = [], []
    # ... validation logic from run_mlos_qc() ...
    return checks, details
```

### Phase 2: Add pytest Tests
Create `tests/test_qc_engine.py`:

```python
# tests/test_qc_engine.py
import pytest
import pandas as pd
from qc_engine import validate_mlos, validate_schema

def test_validate_mlos_null_check():
    """Rule 1: Null fields should be flagged."""
    mlos_df = pd.DataFrame({
        "state_code": [None, "NA"],  # First row has NULL
        "state_name": ["Nasarawa", "Kano"],
        # ... other required columns ...
    })
    takeoff_df = pd.DataFrame()
    
    checks, details = validate_mlos(mlos_df, takeoff_df)
    rule_1 = [c for c in checks if c["Rule#"] == "1"][0]
    assert rule_1["Failing Rows"] == 1
    assert "FAIL" in rule_1["Status"]

def test_validate_schema_missing_column():
    """Schema check should flag missing required columns."""
    mlos_df = pd.DataFrame({
        "state_code": ["NA"],
        # Missing many required columns
    })
    takeoff_df = pd.DataFrame()
    
    checks, details = validate_schema(mlos_df, takeoff_df)
    schema_check = [c for c in checks if c["Rule#"] == "S1"][0]
    assert "FAIL" in schema_check["Status"]
    assert schema_check["Failing Rows"] > 0
```

### Phase 3: Add Fixtures for Common Test Data
Create `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
import pandas as pd

@pytest.fixture
def valid_mlos_df():
    """Minimal valid MLoS DataFrame."""
    return pd.DataFrame({
        "state_code": ["NA"],
        "state_name": ["Nasarawa"],
        "lga_code": ["LGA1"],
        "lga_name": ["Test LGA"],
        # ... all 43 required columns with valid data ...
    })

@pytest.fixture
def invalid_mlos_df_nulls():
    """MLoS DataFrame with NULL violations."""
    return pd.DataFrame({
        "state_code": [None],
        "state_name": [None],
        # ... other columns with NULLs ...
    })

@pytest.fixture
def takeoff_df():
    """Valid Takeoffpoint DataFrame."""
    return pd.DataFrame({
        "name": ["Point A"],
        "code": ["P001"],
        "wardcode": ["W001"],
        "globalid": ["550e8400-e29b-41d4-a716-446655440000"],
    })
```

## Coverage Targets

**Recommended Coverage Goals:**
- `run_schema_qc()`: 100% — deterministic, critical
- `run_mlos_qc()`: 100% — 14 rules, deterministic, critical
- `run_settlement_qc()`: 100% — 5 rules, deterministic, critical
- `run_takeoff_qc()`: 100% — 4 rules, deterministic, critical
- `run_ward_boundary_qc()`: 80%+ (harder due to external reference data)
- Data loaders (`load_csv`, `load_xlsx`, `load_sqlite`): 80%+ (file I/O testing)
- Auto-correct (`auto_correct_mlos`): 100% — data transformation verification critical
- Report builders: 50%+ — style verification less critical than logic

**View Coverage:**
```bash
# Proposed command (after refactoring)
pytest tests/ --cov=qc_engine --cov-report=html
```

## Integration Testing (Manual, No Framework)

**Current Manual Testing Approach:**
Users upload files via UI and observe:
1. File loads successfully
2. Auto-correct report shows what was fixed
3. QC checks run and display results in tabs
4. Excel reports download and match displayed data
5. Email sends (when SMTP configured)

**Recommended Test Files:**
- `test_data/valid_mlos.csv` — 10-row clean dataset
- `test_data/invalid_mlos.csv` — 10-row dataset with all rule violations
- `test_data/test_mlos.sqlite` — SQLite with MLoS + Takeoffpoint views
- `test_data/test_mlos.xlsx` — Excel with sheets for MLoS and Takeoffpoint

---

*Testing analysis: 2026-09-09*
