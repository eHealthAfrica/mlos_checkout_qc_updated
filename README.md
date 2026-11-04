# MLOS Checkout QC

A Streamlit app for running automated Quality Control (QC) checks on MLOS (Master List of Settlements) checkout files across **4 QC layers**: schema alignment, MLoS data integrity (including takeoffpoint vs. health facility), settlement spatial checks, and admin boundary validation.

---

## Features

- Upload `.sqlite`, `.csv`, `.xlsx`, or `.xls` checkout files
- **Takeoffpoints checked against the bundled health facility reference** — no takeoffpoint table or separate upload needed
- **▶️ Run QC button** — QC only starts after explicit submission
- **🔧 Auto Correct** runs before every QC — fixes common data issues and exports a corrected file
- **Step-by-step progress bar** displayed during QC run
- **4 QC Layers** run automatically on submission:
  - 🔎 **Schema Alignment** — verifies all required columns are present
  - 🏘️ **MLoS Rules** — data integrity checks, including takeoffpoint vs. health facility (Rules 1–12)
  - 📐 **Settlement QC** — duplicate, coordinate, stacking, proximity, and settlement extent checks
  - 🗺️ **Boundary Checks** — null ward code detection, ward code existence, ward code vs. ward boundary polygon (spatial join), and state name validation against the 9,406-ward admin boundary reference (Sept 2026)
- **Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score** displayed on the dashboard
- Per-rule issue drilldown with expandable row-level detail tables
- **MLoS Issues — Longitudinal View** — one row per settlement, Yes/No per rule column, downloadable
- **Boundary Issues** — includes reference ward code, ward name, LGA, and state columns for comparison, plus the ward each settlement actually falls in
- **Proximity clusters** — settlements under 20 m and 20–30 m from their nearest neighbour, grouped by cluster
- **Generate Report tab** — full QC verdict (CLEAN / FAILING) + downloadable Excel report
- **Send QC Email** — sends summary to the data team on demand

---

## Supported File Formats

| Format | MLoS Data |
|--------|-----------|
| `.sqlite` / `.db` | `master_list_settlement_update_view` |
| `.xlsx` / `.xls` | Sheet named `mlos` / `master_list_settlement_update_view` (or the first sheet) |
| `.csv` | Entire CSV file |

All formats get the same full set of checks.

---

## Tab Overview

| Tab | Contents |
|-----|----------|
| 🔧 Auto Correct | Correction log + full corrected MLoS download (always available) |
| 📊 QC Summary | Weighted QC Score breakdown, pass/fail per rule, failing row counts, Pass Rate %, Fail Rate % |
| 🏘️ MLoS Issues | Row-level drilldown per failing rule + Longitudinal View (Yes/No per rule) |
| 📐 Settlement QC | Row-level drilldown for each failing settlement check (duplicates, coordinates, proximity, settlement extent) + download |
| 🗺️ Boundary Issues | Null/missing ward codes (B0), unmatched ward codes (B1), ward code vs. spatially-joined boundary ward mismatches (B2), state name mismatches (B3), with boundary reference comparison columns |
| 🔍 Raw Data | Filterable view of the full MLoS dataset |
| 📄 Generate Report | Full QC verdict, Excel report download, and Send Email button |

---

## Process & Procedure

### 1. Upload Your File

Use the **sidebar uploader** to upload your MLOS checkout file. The tool accepts `.sqlite`, `.db`, `.csv`, `.xlsx`, and `.xls` files.

Click **▶️ Run QC** in the sidebar to start. QC does not run until the button is clicked.

Once submitted, the app:
1. Runs **Auto Correct** on the MLoS data (pre-step before QC)
2. Runs all 4 QC layers on the corrected data in sequence

A **labelled progress bar** tracks each step:

| Step | Progress | Layer |
|------|----------|-------|
| Pre-step | — | 🔧 Auto Correct |
| Step 1 / 4 | 5% → 25% | 🔎 Schema Alignment |
| Step 2 / 4 | 26% → 50% | 🏘️ MLoS Rules |
| Step 3 / 4 | 51% → 75% | 📐 Settlement QC |
| Step 4 / 4 | 76% → 100% | 🗺️ Boundary Checks |

---

### 2. Auto Correct (Pre-step)

Auto Correct runs automatically **before** every QC. The corrected MLoS data is used for all 4 QC layers.

| # | Field(s) | Correction |
|---|----------|------------|
| 1 | `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani` | NULL → `NA` |
| 2 | `scattered` | NULL or `NA` → `N` |
| 3 | `reasons_for_inaccessibility` | NULL → `NA` where `accessibility_status` is `Fully Accessible` |
| 4 | `source` | NULL or empty → `IE` |
| 5 | `eha_guid` | All `{` `}` stripped; any still-invalid UUID replaced with a fresh generated UUID |

The **🔧 Auto Correct tab** shows the correction log and a **⬇️ Download Full MLoS — Auto Corrected (Excel)** button (always visible).

---

### 3. Schema Alignment (Rule S1)

Checks whether the uploaded file contains all required columns. Schema failures are reported without stopping the remaining checks.

#### Required MLoS Columns (43)

| Column | Description | Used In |
|--------|-------------|---------|
| `state_code` | 2-letter state code (e.g. `NA`) | Base identifier, Rule 1 |
| `state_name` | Full state name (e.g. `Nasarawa`) | Base identifier, Rules 1, B1, B3 |
| `lga_code` | LGA code (e.g. `ABSEZA`) | Base identifier, Rule 1 |
| `lga_name` | LGA name | Base identifier, Rule 1 |
| `ward_name` | Ward name | Base identifier, Rule 1 |
| `ward_code` | Ward code | Rules 1, 2, B0, B1, B2, B3 |
| `takeoffpoint` | Takeoffpoint (health facility) name | Rule 2 |
| `takeoffpoint_code` | Takeoffpoint code | Schema only (not validated) |
| `settlement_name` | Settlement name | Base identifier, Rule 1 |
| `primarysettlement_name` | Primary settlement name | Nullable (can be null) |
| `alternate_name` | Alternate settlement name | Nullable (can be null) |
| `latitude` | GPS latitude | Rules 1, SQ2, SQ2b, SQ3, SQ4, SQ5, SQ6, B2 |
| `longitude` | GPS longitude | Rules 1, SQ2, SQ2b, SQ3, SQ4, SQ5, SQ6, B2 |
| `security_compromised` | Y or N | Rules 1, 3 |
| `accessibility_status` | Fully Accessible / Partially Accessible / Inaccessible | Rules 1, 4, 5 |
| `reasons_for_inaccessibility` | Reason text | Rule 5, Auto Correct (Nullable — can be null for Fully Accessible settlements) |
| `habitational_status` | Abandoned / Migrated / Inhabited / Partially Inhabited | Rule 6 (Nullable) |
| `set_population` | Total settlement population | Rules 1, 7, 8 |
| `set_target` | Target count | Rules 1, 7 |
| `number_of_household` | Household count | Rules 1, 8 |
| `noncompliant_household` | Non-compliant household count | Base field (Nullable) |
| `team_code` | Team code (varchar) | Base field (Nullable) |
| `day_of_activity` | Day of activity | Base field (Nullable) |
| `urban` | Y or N | Rules 1, 9 |
| `rural` | Y or N | Rules 1, 9 |
| `scattered` | Y or N | Rules 1, 9, Auto Correct |
| `highrisk` | Y, N, or NA | Rules 1, 10 |
| `slums` | Y, N, or NA | Rules 1, 10 |
| `densely_populated` | Y, N, or NA | Rules 1, 10 |
| `hard2reach` | Y, N, or NA | Rules 1, 10 |
| `border` | Y, N, or NA | Rules 1, 10 |
| `nomadic` | Y, N, or NA | Rules 1, 10 |
| `riverine` | Y, N, or NA | Rules 1, 10 |
| `fulani` | Y, N, or NA | Rules 1, 10 |
| `timestamp` | Record timestamp | Metadata, Rule 1 |
| `last_updated` | Last update timestamp | Metadata (Nullable) |
| `source` | Data source | Auto Correct (→ `IE` if empty) (Nullable) |
| `editor` | Editor username | Rule 11 (Nullable) |
| `validation_status` | Validation status | Base field (Nullable) |
| `master_id` | Master record ID | Base field (Nullable) |
| `mlos_id` | MLoS record ID | Base field (Nullable) |
| `eha_guid` | Record UUID | Rules 1, 12, Auto Correct |
| `settlementarea_globalid` | Settlement area UUID | Rule 1 |

---

### 4. MLoS QC Checks (Rules 1–12)

Data integrity rules applied to the MLoS table. Rules are numbered sequentially 1–12.

| Rule | Check | Description |
|------|-------|-------------|
| 1 | Required Fields — Not Null | All 28 schema `NOT NULL` columns must not be empty. The detail table includes a **Null Fields** column listing exactly which column(s) are null for each failing row. Covered fields: `state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `settlement_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `set_population`, `set_target`, `number_of_household`, `urban`, `rural`, `scattered`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani`, `timestamp`, `eha_guid`, `settlementarea_globalid` |
| 2 | Takeoffpoint — Health Facility Match | `takeoffpoint` must be a health facility in the settlement's own `ward_code` (see below). Blank takeoffpoints fail |
| 3 | Security Compromised Y/N | `security_compromised` must be `Y` or `N` |
| 4 | Accessibility Status Valid | Must be: `Fully Accessible`, `Partially Accessible`, or `Inaccessible` |
| 5 | Reason for Inaccessibility Required | Partially/Inaccessible settlements must have a reason |
| 6 | Habitational Status Valid | Must be: `Abandoned`, `Migrated`, `Inhabited`, or `Partially Inhabited` |
| 7 | set_target ≤ set_population | `set_target` must not exceed `set_population` |
| 8 | number_of_household ≤ set_population | `number_of_household` must not exceed `set_population` |
| 9 | Urban / Rural / Scattered Y/N | Each must be `Y` or `N`; cannot be both Urban and Rural (9a), or Urban and Scattered (9b) |
| 10 | Profile Flags Y/N/NA | `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani` must be `Y`, `N`, or `NA` |
| 11 | Editor Format | `editor` must follow the format `firstname.surname` (all lowercase) |
| 12 | eha_guid is UUID | `eha_guid` must be a valid UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |

**Nullable fields** (schema allows NULL — not subject to Rule 1): `primarysettlement_name`, `alternate_name`, `reasons_for_inaccessibility`, `habitational_status`, `noncompliant_household`, `team_code`, `day_of_activity`, `source`, `last_updated`, `editor`, `validation_status`, `master_id`, `mlos_id`.

> Previously removed rules: Day of Activity (was R12), team_code numeric (was R14t) — `team_code` is varchar; Source = MLoS (was R15) — handled by Auto Correct (`source` NULL → `IE`); Takeoffpoint Code Match and Ward Code vs. Takeoffpoint table (were Rules 3 and 4) — removed with the takeoffpoint table.

#### Rule 2 — how takeoffpoints are matched to health facilities

Each settlement's `takeoffpoint` is compared with the `primary_name` and `alternate_name` of every health facility in the **same `ward_code`** (`health_facility_ref.csv.gz`). Names are compared on their distinctive place-name words:

1. Lower-cased, punctuation removed, word order ignored
2. Abbreviations expanded — `PHC`, `PHCC`, `BHC`, `CHC`, `HC`, `HP`, `GH`, `MCH`, `FMC`
3. Generic facility words ignored — *primary, health, centre/center, care, clinic, post, basic, comprehensive, general, hospital, dispensary, model, cottage, maternity, …*
4. Small spelling differences accepted (≥ 80% similar, e.g. `Gwagarab` / `Gwagarap`), but numerals must match exactly (`Ankpa I` ≠ `Ankpa II`)

So `PHC Ojede` matches `Ojede Primary Health Center`. Failing rows get a **Closest Health Facilities in Ward** column with up to 3 suggestions, or `No takeoffpoint given` / `No health facility in this ward`.

---

### 5. Settlement QC Checks (Rules SQ1–SQ6)

Spatial integrity checks applied to the MLoS settlement records.

| Rule | Check | Description |
|------|-------|-------------|
| SQ1 | Duplicate Settlement Name in Ward | `settlement_name` must be unique within each `ward_code` — compared ignoring case and extra spaces; blank names are left to Rule 1 |
| SQ2 | Latitude/Longitude — Not Null | `latitude` and `longitude` must not be null or missing |
| SQ2b | Latitude/Longitude — Not Zero | `latitude` and `longitude` must not be zero (checked only on non-null rows) |
| SQ3 | Stacked Coordinates | No two settlements may share identical `latitude`/`longitude` coordinates |
| SQ4 | Settlements Too Close (< 20 m) | Nearest other settlement is less than 20 metres away (Haversine distance) |
| SQ5 | Settlements Too Close (20–30 m) | Nearest other settlement is 20–30 metres away (Haversine distance) |
| SQ6 | Not on Settlement Extent (> 50 m) | Settlement point must be on, or within 50 metres of, a GRID3 settlement extent |

SQ4 and SQ5 rows are banded by each settlement's nearest neighbour, so a row appears in only one of them. Their detail rows include `Cluster ID` / `Cluster Size` (settlements linked by < 30 m pairs), `Nearest Settlement` and `Nearest Distance (m)`.

SQ6 flags points that sit away from any mapped buildings, which usually means a misplaced coordinate or a point captured off-site. It uses the GRID3 Nigeria settlement extents v4.1 (Built-up Area, Small Settlement Area, Hamlet) rasterised to a 25 m grid, so distances are accurate to about one cell (the grid is slightly lenient: a cell counts if any part of an extent touches it). SQ6 detail rows add `Nearest Extent (m)` — distance to the nearest extent within 500 m, or `> 500` — and `Nearest Extent Type`. Rows without valid coordinates are left to SQ2/SQ2b.

---

### 6. Boundary Checks (Rules B0–B3)

Spatial and reference validation against the admin ward boundary dataset (9,406 wards, Sept 2026 release).

| Rule | Check | Description |
|------|-------|-------------|
| B0 | Ward Code — Not Available on Data | `ward_code` is null or empty in the uploaded data |
| B1 | Ward Code — Boundary Reference | `ward_code` must exist in the boundary reference for the file's state(s) (only checked for rows with a non-null ward_code) |
| B2 | Ward Code — Boundary Spatial Match | Each point is spatially joined to the ward boundary polygons; the `ward_code` on the settlement must equal the ward code of the polygon it falls in. Failing rows show `Boundary Ward Code` / `Boundary Ward Name` (or "No ward found at coordinates"). Skipped only when the point is in no ward and the declared ward has no polygon |
| B3 | State Name — Boundary Reference Match | `state_name` in MLoS must match the `state_name` the boundary reference assigns to the same `ward_code` |

**State filtering (B1):** The boundary reference is pre-filtered by `state_name` (e.g. "Nasarawa", "Kano") matched case-insensitively against the uploaded file's `state_name` column. Fallback to the full 9,406-ward reference if no match is found.

**Spatial join (B2):** Points are matched against all ward polygons nationwide (not just the file's states), so a settlement placed in the wrong state still reports the ward it actually falls in. A point on a ward boundary line counts as inside that ward. 103 wards (mostly status `Invalid`) have no polygon in the source data; they remain in the reference for B1/B3 but cannot be spatially verified.

**Boundary Issues tab** includes reference comparison columns:

| Extra Column | Meaning |
|-------------|---------|
| `Ref Ward Code` | Ward code as it appears in the boundary reference |
| `Ref Ward Name` | Ward name from the reference |
| `Ref LGA Code` / `Ref LGA Name` | LGA from the reference |
| `Ref State Code` | State from the reference |
| `In Boundary Reference` | `Yes` or `No — not found in reference` |
| `Boundary Ward Code` (B2 only) | Ward code(s) of the polygon the coordinates fall in, or `No ward found at coordinates` |
| `Boundary Ward Name` (B2 only) | Ward name(s) for the `Boundary Ward Code` |

Reference files bundled in the repo:
- `health_facility_ref.csv.gz` — 51,201 health facilities (`ward_code`, `primary_name`, `alternate_name`, `globalid`) across 8,912 wards, from `health_facilities.sqlite` — used by MLoS Rule 2
- `ward_boundary_ref.csv` — 9,406 ward codes with state, LGA, and ward metadata (source: `ward_boundary_sept.sqlite`, Sept 2026)
- `ward_boundary_geom.csv.gz` — 9,305 ward boundary polygons (WKB hex, EPSG:4326) per ward code, used for the B2 spatial join
- `settlement_extent_mask.npz` — GRID3 Nigeria settlement extents v4.1 (2.55 M blocks, from `settlement_extent.gpkg`) rasterised to a 25 m EPSG:3857 grid by `scripts/build_extent_mask.py` (build-time only; needs `rasterio` and `pyogrio`); cell values 0 none, 1 Hamlet, 2 Small Settlement Area, 3 Built-up Area, stored as zlib-compressed 256×256 tiles (2 bits per cell, empty tiles dropped) — used by SQ6

The two ward files are generated from the `ward_boundary_sept` table in `ward_boundary_sept.sqlite` (SpatiaLite). In the Sept 2026 release, ward codes for the northern states moved from numeric (e.g. `10101`) to alphanumeric (e.g. `BASALK01`), and some LGA codes changed along with their ward codes — so an LGA code does not always match the first 6 characters of its ward codes. Wards of every status (including `Invalid`) are included; duplicate ward codes are merged into one entry.

---

### 7. Weighted QC Score

After all 4 layers run, the app calculates a **Weighted QC Score** that reflects the relative importance of each layer:

| QC Layer | Weight |
|----------|--------|
| 🔎 Schema Alignment | 10% |
| 🏘️ MLoS Rules | 60% |
| 📐 Settlement QC | 20% |
| 🗺️ Boundary Checks | 10% |

> MLoS Rules absorbed the former Takeoffpoint layer's 20% when the takeoffpoint check moved into MLoS Rule 2.

**How it's calculated:**

For each layer, the *layer pass rate* = number of passing rules ÷ total rules in that layer. The weighted contribution = layer pass rate × layer weight × 100.

```
Weighted Score = (Schema Pass Rate × 10%) + (MLoS Pass Rate × 60%)
               + (Settlement Pass Rate × 20%) + (Boundary Pass Rate × 10%)
```

> If a layer has no applicable checks, that layer receives **full credit** (100% pass rate) so the score is not unfairly penalised.

The score and a breakdown table are shown in the **📊 QC Summary** tab. The 🏆 score also appears in the top metric bar on the dashboard.

| Score Range | Interpretation |
|-------------|---------------|
| 80% – 100% | Green — file is in good shape |
| 60% – 79% | Amber — notable issues to review |
| 0% – 59% | Red — significant data quality problems |

---

### 8. MLoS Issues — Longitudinal View

The **MLoS Issues** tab includes a longitudinal (wide-format) view of all settlement rows that failed at least one rule:

- Each row represents one settlement
- Each QC rule appears as a column (e.g. `Rule_5 | Security Compromised Y/N`)
- **Yes** = error present on that row for that rule
- **No** = no error on that rule for that row
- Click **Download MLoS Issues — Longitudinal (Excel)** to export the workbook

---

### 9. Generate & Download Report

Go to the **Generate Report** tab to:

1. See the overall QC verdict: `✅ CLEAN` or `❌ FAILING`
2. Download the Excel report (Cover · MLoS QC Summary · MLoS Issue Detail · Raw MLoS Data)
3. Download and share with the data team or programme leads

The report file is named: `{filename}_QC_Report.xlsx`

---

### 10. Send QC Email

Click **Send QC Email** in the Generate Report tab to notify the data team.

| Field | Value |
|-------|-------|
| **To** | adanna.alex@ehealthnigeria.org |
| **CC** | fashoto.busayo@ehealthnigeria.org, victor.idakwo@ehealthnigeria.org, oluwadamilare.akindipe@ehealthnigeria.org |
| **Subject** | MLoS QC checks for `{filename}` |
| **Body** | Full check-by-check summary with verdict, issue counts, and missing columns |

SMTP credentials must be configured in Streamlit secrets:

```toml
smtp_host = "smtp.office365.com"   # or smtp.gmail.com for Gmail
smtp_port = 587
smtp_user = "your@email.com"
smtp_pass = "your-app-password"
```

> `smtp_host` must be the mail server hostname — **not** an email address.

---

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

1. Fork or clone this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Add SMTP credentials under **App secrets**
6. Deploy!

---

## Built By
eHealth Africa
