# Coding Conventions

**Analysis Date:** 2026-09-09

## Naming Patterns

**Files:**
- Single entry point: `app.py`
- Lowercase with underscores for any additional files
- Example: `app.py`

**Functions:**
- snake_case for all function names
- Descriptive and action-oriented
- Examples: `load_sqlite()`, `run_schema_qc()`, `run_mlos_qc()`, `auto_correct_mlos()`, `build_excel_report()`
- Helper functions prefixed with descriptive words: `vec_is_uuid()`, `add()` (nested helpers within QC functions)
- Private/nested functions use same convention as public functions

**Variables:**
- snake_case for all variables
- Descriptive names that indicate purpose or content
- Examples: `mlos_df`, `takeoff_df`, `uploaded_file`, `boundary_ref`, `schema_checks`
- Short variable names in comprehensions and loops acceptable: `c`, `n`, `i`
- Tuple unpacking common: `mlos_df, takeoff_df = load_xlsx(uploaded_file)`

**Constants:**
- UPPERCASE with underscores
- Located at module level, typically near top of file after imports
- Examples from `app.py`:
  - `MLOS_VIEW = "master_list_settlement_update_view"`
  - `VALID_DAY = {"1","1_2","1_2_3","1_2_3_4",...}`
  - `VALID_YN = {"Y","N"}`
  - `UUID_RE = re.compile(...)`
  - `LAYER_WEIGHTS = {"schema": 0.10, "mlos": 0.40, ...}`
  - `FLAG_COLS = ["highrisk", "slums", "densely_populated", ...]`

## Code Style

**Formatting:**
- No explicit formatter configured (.black, .autopep8)
- Implicit style guide based on observed patterns:
  - 4-space indentation (Python standard)
  - Line continuations use natural wrapping in function calls
  - Multi-line function definitions indent arguments
  - String literals use double quotes predominantly
  - f-strings used for formatted output

**Linting:**
- No `.pylintrc`, `.flake8`, or `pyproject.toml` configuration present
- No linting tool integrated into CI/CD
- Code follows general PEP 8 conventions implicitly

## Import Organization

**Order:**
1. Standard library imports (`streamlit`, `sqlite3`, `pandas`, `tempfile`, `os`, `re`, `io`, `datetime`)
2. Third-party library imports (`openpyxl`, `smtplib`, `email.mime`)
3. No relative imports or local module imports (single-file application)

**Path Aliases:**
- None used; single-file application eliminates need for aliases

**Example from app.py (lines 1-11):**
```python
import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import os
import re
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
```

## Code Organization

**Section Markers:**
- ASCII comment blocks using em-dashes (─) for visual section separation
- Pattern: `# ─── Section Name ────────────────────────────────────────────`
- Examples:
  - `# ─── Page Config ────`
  - `# ─── Constants ───────`
  - `# ─── Helpers ────────`
  - `# ─── Schema QC ──────`
  - `# ─── QC Engine — MLoS ────`

**Function Grouping:**
- Helper/utility functions grouped near top: `load_sqlite()`, `load_csv()`, `load_xlsx()`, `get_uploaded_data()`, `pct()`
- Vectorized utility functions together: `vec_is_uuid()`, `vec_is_editor()`
- QC engine functions grouped by domain: `run_schema_qc()`, `run_mlos_qc()`, `run_settlement_qc()`, `run_takeoff_qc()`, `run_ward_boundary_qc()`
- Report builders grouped: `build_excel_report()`, `build_schema_report_xlsx()`, `build_longitudinal_mlos()`, `build_corrected_excel()`
- UI code (Streamlit) in main execution body at bottom of file starting around line 1172

## Error Handling

**Patterns:**
- Try-except blocks with user-facing error messages via `st.error()`, `st.warning()`
- Examples:
  - `try: ... except Exception as e: st.error(f"Failed to load file: {e}")`
  - `try: ... except OSError: pass` (silent failure for cleanup operations)
- File handling uses try-finally for resource cleanup (lines 182-197):
  ```python
  try:
      # operations
  finally:
      conn.close()
      try:
          os.unlink(tmp_path)
      except OSError:
          pass
  ```
- Validation errors return early with `st.stop()` to halt execution

**Null/Empty Handling:**
- Explicit null checks using `pd.isna()`, `.isna()`, `.isnull()`
- Empty string checks with `.str.strip().eq("")`
- `keep_default_na=False` used in all CSV/Excel loaders to preserve domain value "NA" (Nasarawa state code)
- `.fillna()` for safe default value assignment

## Comments

**When to Comment:**
- Algorithm logic that's non-obvious (e.g., Haversine distance calculation in SQ4)
- Explain WHY not WHAT: "keep_default_na=False prevents pandas from silently converting the valid domain value 'NA' to NaN"
- Mark critical data handling decisions (lines 98-101 explaining nullable fields)
- Explain filter/merge operations that may appear magical without context (lines 413-418)

**JSDoc/TSDoc:**
- Docstrings on public/exported functions
- Format: triple-quoted strings immediately after function definition
- Include return type and brief description
- Example (lines 120-125):
  ```python
  def load_csv(uploaded_file):
      """Load a CSV file as the MLoS table. Returns (mlos_df, empty takeoff_df)."""
  ```
- Example (lines 130-132):
  ```python
  def load_xlsx(uploaded_file):
      """Load an XLSX/XLS file. Expects two sheets: mlos (sheet 1) and takeoffpoint (sheet 2).
      Sheet names may match the view names or simplified aliases."""
  ```

## Function Design

**Size:**
- Functions typically 10-50 lines, with some reaching 100+ lines
- Larger functions are QC validation engines that process dataframes
- Example: `run_mlos_qc()` spans lines 805-965 (160 lines) — validates 14 rules on MLoS data
- Inner `add()` helper function pattern used to reduce repetition in validation rules

**Parameters:**
- Functions accept DataFrames and optional parameters
- Required parameters come first, optional with `=None` defaults
- Example: `def get_uploaded_data(uploaded_file, progress=None)` (lines 157-204)
- Example: `def add(num, rule, desc, mask, extra=None)` (nested helper at line 400)

**Return Values:**
- QC functions return tuples: `(checks_list, detail_dataframe)`
  - `checks_list`: list of dictionaries with rule metadata
  - `detail_dataframe`: pandas DataFrame with failing row details
- Data loaders return tuples: `(mlos_df, takeoff_df)`
- Excel builders return bytes: `return out.getvalue()`
- Example (line 965): `return checks, pd.concat(details) if details else pd.DataFrame()`

## Module Design

**Exports:**
- Single-file application; all functions are implicitly "exported"
- Streamlit app functions (UI code) at bottom of file after all helper/engine functions

**Barrier Pattern:**
- Clear separation between:
  - Helper functions (lines 103-204)
  - Constants and validation sets (lines 87-101)
  - QC engine functions (lines 218-1012)
  - Report builders (lines 280-1170)
  - UI/Streamlit code (lines 1172+)

## Data Validation & Transformation

**Common Patterns:**
- Vectorized operations preferred over per-row Python functions for performance
  - `vec_is_uuid()` uses pandas `.str.match()` instead of row-wise regex checks
  - `vec_is_editor()` uses same vectorized pattern
- Pandas operations for filtering and masking
  - Example: `mask = df["column"].isin(valid_set)` (used throughout QC rules)
  - Example: `null_mask = mlos[columns].isnull().any(axis=1)` (Rule 1, line 839)
- Type coercion with `pd.to_numeric(..., errors="coerce")` for safe numeric conversion
- String normalization: `.astype(str).str.strip().str.lower()` pattern repeated throughout

---

*Convention analysis: 2026-09-09*
