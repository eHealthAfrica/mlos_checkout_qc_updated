# Technology Stack

**Analysis Date:** 2026-09-09

## Languages

**Primary:**
- Python 3.x - Core application language for all QC logic and data processing

## Runtime

**Environment:**
- Python 3 (version unspecified in requirements.txt)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (present, pinned to minimum versions with `>=`)

## Frameworks

**Core:**
- Streamlit 1.32.0+ - Web application framework for interactive QC dashboard and UI

**Data Processing:**
- pandas 2.0.0+ - Data manipulation, CSV/Excel loading, DataFrame operations

**File Handling:**
- openpyxl 3.1.0+ - Excel workbook generation and styling (report export, corrected file output)
- xlrd 2.0.1+ - XLS file reading support (legacy Excel format compatibility)

**Build/Dev:**
- None detected

## Key Dependencies

**Critical:**
- pandas 2.0.0+ - Powers all data loading, validation, filtering, and export operations
- Streamlit 1.32.0+ - Provides interactive UI, session state management, and file upload handling
- openpyxl 3.1.0+ - Generates formatted Excel reports with styling (borders, fills, fonts, alignment)

**Conditional/Standard Library:**
- numpy - Imported conditionally in spatial distance calculations (`SQ4` proximity check)
- sqlite3 - Standard library; used for loading `.sqlite` / `.db` files containing MLoS and Takeoffpoint views
- smtplib - Standard library; used for sending QC summary emails via SMTP
- email.mime - Standard library; formats email messages (multipart with HTML/plain text)
- tempfile - Standard library; handles temporary file creation for SQLite uploads
- re - Standard library; regex validation (UUID format, editor username format)
- datetime - Standard library; timestamp recording
- io.BytesIO - Standard library; in-memory binary stream for file operations
- os - Standard library; file path operations and environment interaction

## Configuration

**Environment:**
- **Streamlit Secrets (`.streamlit/secrets.toml` or environment variables):** Provides SMTP credentials for email functionality
  - `smtp_host` (default: `smtp.gmail.com`)
  - `smtp_port` (default: `587`)
  - `smtp_user` - Email address/username for SMTP authentication
  - `smtp_pass` - Password or app-specific password for SMTP authentication

**Build:**
- No build configuration detected (pure Python, no compilation step)

## Platform Requirements

**Development:**
- Python 3.x
- pip
- No virtual environment configuration detected (.venv/ not in repo)

**Production:**
- Streamlit runtime (local server or cloud deployment like Streamlit Cloud, Docker)
- SMTP server access for email notifications (optional)
- Input data files: `.sqlite`, `.db`, `.csv`, `.xlsx`, or `.xls` files

## Data Files (Bundled)

**Reference Data:**
- `ward_boundary_ref.csv` - 9,410 ward records with state, LGA, ward name, ward code metadata (loaded at `app.py` line 367)
- `ward_boundary_bbox.csv` - Bounding box coordinates (min/max latitude/longitude) per ward code (loaded at `app.py` line 368)

Both CSV files are required for boundary validation checks (Rules B0-B3) and are loaded with `keep_default_na=False` to preserve domain value "NA".

---

*Stack analysis: 2026-09-09*
