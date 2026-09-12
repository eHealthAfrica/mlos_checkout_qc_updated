---
title: MLOS Checkout QC
emoji: 🗺️
colorFrom: blue
colorTo: indigo
sdk: streamlit
python_version: "3.11"
app_file: app.py
pinned: false
short_description: Automated QC checks for Master List of Settlements checkout files
---

# MLOS Checkout QC

A Streamlit app for running automated Quality Control (QC) checks on MLOS (Master List of Settlements) checkout files across **5 QC layers**: schema alignment, MLoS data integrity, settlement spatial checks, takeoffpoint cross-checks, and admin boundary validation.

---

## Features

- Upload `.sqlite`, `.csv`, `.xlsx`, or `.xls` checkout files
- Optional **separate Takeoffpoint file** upload (`.csv` or `.xlsx`) — overrides the built-in sheet
- **▶️ Run QC button** — QC only starts after explicit submission
- **🔧 Auto Correct** runs before every QC — fixes common data issues and exports a corrected file
- **Step-by-step progress bar** displayed during QC run
- **5 QC Layers** run automatically on submission:
  - 🔎 **Schema Alignment** — verifies all required columns are present
  - 🏘️ **MLoS Rules** — data integrity and cross-table checks (Rules 1–14)
  - 📐 **Settlement QC** — duplicate, coordinate, stacking, and proximity checks
  - 📍 **Takeoffpoint Rules** — 4 cross-table consistency checks
  - 🗺️ **Boundary Checks** — null ward code detection, ward code existence, coordinate, and state name validation against 9,410-ward admin boundary reference
- **Pass Rate %, Fail Rate %, and 🏆 Weighted QC Score** displayed on the dashboard
- Per-rule issue drilldown with expandable row-level detail tables
- **MLoS Issues — Longitudinal View** — one row per settlement, Yes/No per rule column, downloadable
- **Boundary Issues** — includes reference ward code, ward name, LGA, and state columns for comparison
- **Generate Report tab** — full QC verdict (CLEAN / FAILING) + downloadable Excel report
- **Send QC Email** — sends summary to the data team on demand

---

## Supported File Formats

| Format | MLoS Data | Takeoffpoint Data |
|--------|-----------|-------------------|
| `.sqlite` / `.db` | `master_list_settlement_update_view` | `mlos_takeoffpoint_view` |
| `.xlsx` / `.xls` | Sheet 1 (or sheet named `mlos`) | Sheet 2 (or sheet named `takeoffpoint`) |
| `.csv` | Entire CSV file | Not available — upload a separate Takeoffpoint file |

> For full QC coverage including takeoffpoint and boundary checks, use `.sqlite` or `.xlsx`.

---

## Tab Overview

| Tab | Contents |
|-----|----------|
| 🔧 Auto Correct | Correction log + full corrected MLoS download (always available) |
| 📊 QC Summary | Weighted QC Score breakdown, pass/fail per rule, failing row counts, Pass Rate %, Fail Rate % |
| 🏘️ MLoS Issues | Row-level drilldown per failing rule + Longitudinal View (Yes/No per rule) |
| 📐 Settlement QC | Row-level drilldown for each failing settlement check (duplicates, coordinates, proximity) + download |
| 📍 Takeoffpoint Issues | Row-level drilldown for each failing takeoffpoint rule + download |
| 🗺️ Boundary Issues | Null/missing ward codes (B0), unmatched ward codes (B1), out-of-boundary coordinates (B2), state name mismatches (B3), with boundary reference comparison columns |
| 🔍 Raw Data | Filterable view of the full MLoS and Takeoffpoint datasets |
| 📄 Generate Report | Full QC verdict, Excel report download, and Send Email button |

---

## Process & Procedure

### 1. Upload Your File

Use the **sidebar uploader** to upload your MLOS checkout file. The tool accepts `.sqlite`, `.db`, `.csv`, `.xlsx`, and `.xls` files.

Optionally upload a separate **Takeoffpoint file** (`.csv` or `.xlsx`). This overrides the built-in Takeoffpoint sheet for Excel/SQLite files, and enables takeoffpoint cross-checks for CSV uploads.

Click **▶️ Run QC** in the sidebar to start. QC does not run until the button is clicked.

Once submitted, the app:
1. Runs **Auto Correct** on the MLoS data (pre-step before QC)
2. Runs all 5 QC layers on the corrected data in sequence

A **labelled progress bar** tracks each step:

| Step | Progress | Layer |
|------|----------|-------|
| Pre-step | — | 🔧 Auto Correct |
| Step 1 / 5 | 5% → 20% | 🔎 Schema Alignment |
| Step 2 / 5 | 21% → 40% | 🏘️ MLoS Rules |
| Step 3 / 5 | 41% → 60% | 📐 Settlement QC |
| Step 4 / 5 | 61% → 80% | 📍 Takeoffpoint Rules |
| Step 5 / 5 | 81% → 100% | 🗺️ Boundary Checks |

---

### 2. Auto Correct (Pre-step)

Auto Correct runs automatically **before** every QC. The corrected MLoS data is used for all 5 QC layers.

| # | Field(s) | Correction |
|---|----------|------------|
| 1 | `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani` | NULL → `NA` |
| 2 | `scattered` | NULL or `NA` → `N` |
| 3 | `reasons_for_inaccessibility` | NULL → `NA` where `accessibility_status` is `Fully Accessible` |
| 4 | `source` | NULL or empty → `IE` |
| 5 | `eha_guid` | All `{` `}` stripped; any still-invalid UUID replaced with a fresh generated UUID |

The **🔧 Auto Correct tab** shows the correction log and a **⬇️ Download Full MLoS — Auto Corrected (Excel)** button (always visible).

---

### 3. Schema Alignment (Rules S1–S2)

Checks whether the uploaded file contains all required columns. Schema failures are reported without stopping the remaining checks.

#### Required MLoS Columns (43)

| Column | Description | Used In |
|--------|-------------|---------|
| `state_code` | 2-letter state code (e.g. `NA`) | Base identifier, Rule 1 |
| `state_name` | Full state name (e.g. `Nasarawa`) | Base identifier, Rule 1, B1, B3 |
| `lga_code` | LGA numeric code | Base identifier, Rule 1 |
| `lga_name` | LGA name | Base identifier, Rule 1 |
| `ward_name` | Ward name | Base identifier, Rule 1 |
| `ward_code` | Ward code | Rules 1, 4, B0, B1, B2, B3 |
| `takeoffpoint` | Takeoffpoint name | Rules 2, TP2 |
| `takeoffpoint_code` | Takeoffpoint code | Rules 3, TP3 |
| `settlement_name` | Settlement name | Base identifier, Rule 1 |
| `primarysettlement_name` | Primary settlement name | Nullable (can be null) |
| `alternate_name` | Alternate settlement name | Nullable (can be null) |
| `latitude` | GPS latitude | Rules 1, SQ2, SQ2b, SQ3, SQ4, B2 |
| `longitude` | GPS longitude | Rules 1, SQ2, SQ2b, SQ3, SQ4, B2 |
| `security_compromised` | Y or N | Rules 1, 5 |
| `accessibility_status` | Fully Accessible / Partially Accessible / Inaccessible | Rules 1, 6, 7 |
| `reasons_for_inaccessibility` | Reason text | Rule 7, Auto Correct (Nullable — can be null for Fully Accessible settlements) |
| `habitational_status` | Abandoned / Migrated / Inhabited / Partially Inhabited | Rule 8 (Nullable) |
| `set_population` | Total settlement population | Rules 1, 9, 10 |
| `set_target` | Target count | Rules 1, 9 |
| `number_of_household` | Household count | Rules 1, 10 |
| `noncompliant_household` | Non-compliant household count | Base field (Nullable) |
| `team_code` | Team code (varchar) | Base field (Nullable) |
| `day_of_activity` | Day of activity | Base field (Nullable) |
| `urban` | Y or N | Rules 1, 11 |
| `rural` | Y or N | Rules 1, 11 |
| `scattered` | Y or N | Rules 1, 11, Auto Correct |
| `highrisk` | Y, N, or NA | Rules 1, 12 |
| `slums` | Y, N, or NA | Rules 1, 12 |
| `densely_populated` | Y, N, or NA | Rules 1, 12 |
| `hard2reach` | Y, N, or NA | Rules 1, 12 |
| `border` | Y, N, or NA | Rules 1, 12 |
| `nomadic` | Y, N, or NA | Rules 1, 12 |
| `riverine` | Y, N, or NA | Rules 1, 12 |
| `fulani` | Y, N, or NA | Rules 1, 12 |
| `timestamp` | Record timestamp | Metadata, Rule 1 |
| `last_updated` | Last update timestamp | Metadata (Nullable) |
| `source` | Data source | Auto Correct (→ `IE` if empty) (Nullable) |
| `editor` | Editor username | Rule 13 (Nullable) |
| `validation_status` | Validation status | Base field (Nullable) |
| `master_id` | Master record ID | Base field (Nullable) |
| `mlos_id` | MLoS record ID | Base field (Nullable) |
| `eha_guid` | Record UUID | Rules 1, 14, Auto Correct |
| `settlementarea_globalid` | Settlement area UUID | Rule 1 |

#### Required Takeoffpoint Columns (4)

| Column | Description | Used In |
|--------|-------------|---------|
| `name` | Takeoffpoint name | Rule TP2 |
| `code` | Takeoffpoint code | Rule TP3 |
| `wardcode` | Ward code | Rule TP4 |
| `globalid` | Record UUID | Rule TP5 |

---

### 4. MLoS QC Checks (Rules 1–14)

Data integrity rules applied to the MLoS table. Rules are numbered sequentially 1–14.

| Rule | Check | Description |
|------|-------|-------------|
| 1 | Required Fields — Not Null | All 28 schema `NOT NULL` columns must not be empty. The detail table includes a **Null Fields** column listing exactly which column(s) are null for each failing row. Covered fields: `state_code`, `state_name`, `lga_code`, `lga_name`, `ward_name`, `ward_code`, `settlement_name`, `latitude`, `longitude`, `security_compromised`, `accessibility_status`, `set_population`, `set_target`, `number_of_household`, `urban`, `rural`, `scattered`, `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani`, `timestamp`, `eha_guid`, `settlementarea_globalid` |
| 2 | Takeoffpoint Name Match | `takeoffpoint` must match `name` in the Takeoffpoint table |
| 3 | Takeoffpoint Code Match | `takeoffpoint_code` must match `code` in the Takeoffpoint table |
| 4 | Ward Code Match | `ward_code` must match `wardcode` in the Takeoffpoint table |
| 5 | Security Compromised Y/N | `security_compromised` must be `Y` or `N` |
| 6 | Accessibility Status Valid | Must be: `Fully Accessible`, `Partially Accessible`, or `Inaccessible` |
| 7 | Reason for Inaccessibility Required | Partially/Inaccessible settlements must have a reason |
| 8 | Habitational Status Valid | Must be: `Abandoned`, `Migrated`, `Inhabited`, or `Partially Inhabited` |
| 9 | set_target ≤ set_population | `set_target` must not exceed `set_population` |
| 10 | number_of_household ≤ set_population | `number_of_household` must not exceed `set_population` |
| 11 | Urban / Rural / Scattered Y/N | Each must be `Y` or `N`; cannot be both Urban and Rural (11a), or Urban and Scattered (11b) |
| 12 | Profile Flags Y/N/NA | `highrisk`, `slums`, `densely_populated`, `hard2reach`, `border`, `nomadic`, `riverine`, `fulani` must be `Y`, `N`, or `NA` |
| 13 | Editor Format | `editor` must follow the format `firstname.surname` (all lowercase) |
| 14 | eha_guid is UUID | `eha_guid` must be a valid UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |

**Nullable fields** (schema allows NULL — not subject to Rule 1): `primarysettlement_name`, `alternate_name`, `reasons_for_inaccessibility`, `habitational_status`, `noncompliant_household`, `team_code`, `day_of_activity`, `source`, `last_updated`, `editor`, `validation_status`, `master_id`, `mlos_id`.

> Previously removed rules: Day of Activity (was R12), team_code numeric (was R14t) — `team_code` is varchar; Source = MLoS (was R15) — handled by Auto Correct (`source` NULL → `IE`).

---

### 5. Settlement QC Checks (Rules SQ1–SQ4)

Spatial integrity checks applied to the MLoS settlement records.

| Rule | Check | Description |
|------|-------|-------------|
| SQ1 | Duplicate Settlement Name in Ward | `settlement_name` must not repeat within the same `ward_code` |
| SQ2 | Latitude/Longitude — Not Null | `latitude` and `longitude` must not be null or missing |
| SQ2b | Latitude/Longitude — Not Zero | `latitude` and `longitude` must not be zero (checked only on non-null rows) |
| SQ3 | Stacked Coordinates | No two settlements may share identical `latitude`/`longitude` coordinates |
| SQ4 | Settlements Too Close (< 30 m) | Every settlement must be more than 30 metres from all other settlements (Haversine distance) |

---

### 6. Takeoffpoint QC Checks (Rules TP2–TP5)

Cross-table consistency checks between the Takeoffpoint and MLoS tables.

| Rule | Check | Description |
|------|-------|-------------|
| TP2 | Name matches MLoS | `name` must match `takeoffpoint` in the MLoS table |
| TP3 | Code matches MLoS | `code` must match `takeoffpoint_code` in the MLoS table |
| TP4 | Ward Code matches MLoS | `wardcode` must match `ward_code` in the MLoS table |
| TP5 | GlobalID is UUID | `globalid` must be a valid UUID |

> If a CSV file is uploaded without a separate Takeoffpoint file, rules TP2–TP5 are skipped with a warning.

---

### 7. Boundary Checks (Rules B0–B5)

Spatial and reference validation against the admin ward boundary dataset (9,410 wards).

| Rule | Check | Description |
|------|-------|-------------|
| B0 | Ward Code — Not Available on Data | `ward_code` is null or empty in the uploaded data |
| B1 | Ward Code — Boundary Reference | `ward_code` must exist in the boundary reference for the file's state(s) (only checked for rows with a non-null ward_code) |
| B2 | Coordinates — Within Ward Boundary | `latitude`/`longitude` must fall within the bounding box of the declared `ward_code` |
| B3 | State Name — Boundary Reference Match | `state_name` in MLoS must match the `state_name` the boundary reference assigns to the same `ward_code` |
| B4 | Boundary Reference Fallback | Reports whether B1/B2 validated against the file's own state(s) or, on a fallback, against the full national reference |
| B5 | Boundary Reference Unavailable | Reports when no boundary reference was found at all, so B1, B2, B3 and B4 could not run |

**State filtering:** The boundary reference is pre-filtered by `state_name` (e.g. "Nasarawa", "Kano") matched case-insensitively against the uploaded file's `state_name` column. The fallback to the full 9,410-ward reference still happens when no match is found, but it is no longer silent: it is reported as the `B4` check, which fails and names both `B1` and `B2` because the widening reassigns the state-filtered frames both rules read — B1's ward-code lookup and B2's bounding-box lookup alike. When the bundled reference files are unavailable entirely, `B1`, `B2`, `B3` and `B4` are all suppressed and a separate `B5` check reports the unavailability instead.

**Boundary Issues tab** includes reference comparison columns:

| Extra Column | Meaning |
|-------------|---------|
| `Ref Ward Code` | Ward code as it appears in the boundary reference |
| `Ref Ward Name` | Ward name from the reference |
| `Ref LGA Code` / `Ref LGA Name` | LGA from the reference |
| `Ref State Code` | State from the reference |
| `In Boundary Reference` | `Yes` or `No — not found in reference` |

Reference files bundled in the repo:
- `ward_boundary_ref.csv` — 9,410 ward codes with state, LGA, and ward metadata
- `ward_boundary_bbox.csv` — bounding box (min/max lon/lat) per ward code

---

### 8. Weighted QC Score

After all 5 layers run, the app calculates a **Weighted QC Score** that reflects the relative importance of each layer:

| QC Layer | Weight |
|----------|--------|
| 🔎 Schema Alignment | 10% |
| 🏘️ MLoS Rules | 40% |
| 📐 Settlement QC | 20% |
| 📍 Takeoffpoint Rules | 20% |
| 🗺️ Boundary Checks | 10% |

**How it's calculated:**

For each layer, the *layer pass rate* = number of passing checks ÷ total checks in that layer. A layer that ran **zero checks** has **no pass rate at all** — it contributes nothing to the score. The overall score is the plain sum of the contributions of the layers that ran, **never renormalised** across them, so a withheld table costs points as well as ceiling:

```
Weighted Score       = Σ (Layer Pass Rate × Layer Weight × 100), summed only over layers that ran
Achievable Maximum   = Σ (Layer Weight × 100), summed only over layers that ran
```

The total is always shown **against the achievable maximum**, wherever the weighted score appears (top metric bar, 📊 QC Summary tab, report cover, email): a submission with no Takeoffpoint table reads `72.0% of 80.0% achievable`, not a bare percentage, because the achievable ceiling itself drops by Takeoffpoint's 20% weight. A missing layer costs points and ceiling together — it is never scored as if it passed.

In the breakdown table on the **📊 QC Summary** tab, a layer that did not run shows **Layer Pass Rate `n/a`** and **Weighted Contribution `0`** (a number, not `n/a`, so the column still sums visibly to the total); its **Weight** column is unchanged. The Total row's contribution carries the achievable-maximum figure, e.g. `72.0% of 80.0% achievable`.

The colour bands below are read from the **score out of 100**, never from the score relative to the achievable maximum — `72.0% of 80.0% achievable` is **amber**, not green. A missing layer costs colour as well as points, and a colour means the same thing on every file.

| Score Range | Interpretation |
|-------------|---------------|
| 80% – 100% | Green — file is in good shape |
| 60% – 79% | Amber — notable issues to review |
| 0% – 59% | Red — significant data quality problems |

**"Did not run"** means the layer produced **zero checks at all**; today only the Takeoffpoint layer can be in that state (no separate Takeoffpoint file supplied, and none present in the uploaded SQLite/workbook). When that happens, the verdict names the gap in the same sentence as the verdict itself — after **either** state:

- `CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)` — every check that ran passed
- `FAILING (12 checks) — Takeoffpoint layer not checked (no Takeoffpoint data supplied)` — a check also failed elsewhere

The verdict stays two-state (CLEAN / FAILING); there is no third "incomplete" state. No skipped layer is ever scored as though it passed.

---

### 9. MLoS Issues — Longitudinal View

The **MLoS Issues** tab includes a longitudinal (wide-format) view of all settlement rows that failed at least one rule:

- Each row represents one settlement
- Each QC rule appears as a column (e.g. `Rule_5 | Security Compromised Y/N`)
- **Yes** = error present on that row for that rule
- **No** = no error on that rule for that row
- Click **Download MLoS Issues — Longitudinal (Excel)** to export the workbook

---

### 10. Generate & Download Report

Go to the **Generate Report** tab to:

1. See the overall QC verdict and weighted score for all five layers
2. Click **Generate Report** to produce a detailed Excel workbook
3. Download and share with the data team or programme leads

The report file is named: `{filename}_QC_Report.xlsx`

The workbook always contains the same sheets, in this order, whether the submission is clean or failing:

1. **QC Report Cover** — the verdict and the weighted score (with its achievable maximum), plus file metadata: filename, generated-at timestamp, MLoS row count, Takeoffpoint row count. Per-layer counts live on the summary sheet below, not the cover.
2. **QC Summary** — one combined sheet listing every check that ran, in registry rule order, with a `Layer` column. A layer that ran zero checks appears here as a single placeholder row naming the gap — e.g. `Takeoffpoint — not run: no Takeoffpoint data supplied` — with `n/a` in its Failing Rows, Total Rows and Fail % columns, so the sheet alone can never read as a four-layer tool.
3. **Schema Issue Detail**
4. **MLoS Issue Detail**
5. **Settlement Issue Detail**
6. **Takeoffpoint Issue Detail**
7. **Boundary Issue Detail**
8. **Raw MLoS Data**
9. **Raw Takeoffpoint Data**
10. **Columns Renamed** — present only when a header was renamed at load (see §2); a clean-header submission gets no sheet at all, not an empty one.

The two per-layer summary sheets this report used to produce (`MLoS QC Summary`, `Takeoffpoint QC Summary`) are gone — replaced by the one combined **QC Summary** sheet above. Automation pointed at the old sheet names will need updating.

The detail and raw-data sheets are written as plain values with a styled header row and column widths only — no per-cell colour or border — to keep the workbook within the hosting memory budget.

---

### 11. Send QC Email

Click **Send QC Email** in the Generate Report tab to notify the data team.

The primary and copy recipients are read from the `SMTP_TO` and `SMTP_CC` Space secrets —
[recipient address removed - DEPLOY-02] no address is committed in this repository, and both
lists are editable in the Space UI without a deploy. Send is disabled, with a visible reason
next to the button, while `SMTP_TO` is unset or empty.

| Field | Value |
|-------|-------|
| **Subject** | Carries the verdict: `MLoS QC: FAILING (12 checks) — kano_checkout.xlsx` or `MLoS QC: CLEAN — kano_checkout.xlsx` |
| **Body** | Plain text: the verdict sentence; the weighted score with its achievable maximum; the headline issue-rows figure; one block per layer (in canonical order) with checks run, checks failing and its issue-rows line — or `not run: no Takeoffpoint data supplied` for a layer that did not run; the existing missing-columns block; then a check-by-check list grouped under layer headings, in rule order |

A clean email still lists **every check that ran**, passing and failing, so the reader can see exactly what was verified. The renamed-columns report (§2) is not part of the email — it stays in the on-screen expander and the report's Columns Renamed sheet only.

Recipients and SMTP credentials are configured as Space secrets — see the Deployment section
below for the full list (rewritten for Hugging Face Spaces). On a local
`.streamlit/secrets.toml` (dev only), the same SMTP credential keys apply:

```toml
smtp_host = "smtp.office365.com"   # or smtp.gmail.com for Gmail
smtp_port = 587
smtp_user = "<smtp-account-user>"
smtp_pass = "your-app-password"
```

On Hugging Face Spaces these keys — plus `SMTP_TO`/`SMTP_CC` — arrive as flat environment
variables, not a TOML file the officer edits.

> `smtp_host` must be the mail server hostname — **not** an email address.

---

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Running locally with no sign-in configuration set requires the `MLOS_AUTH_DISABLED` opt-out
variable; without it, and without a complete `[auth]` configuration, the app stops at startup
and names the missing environment variable(s) rather than running open.

## Hugging Face Spaces

This repository is deployed as a single Hugging Face Space. The front matter at the top of this
file (`sdk: streamlit`, `python_version: "3.11"`, `app_file: app.py`) is what the platform reads
to build and launch it.

### 1. Creating the Space

Create a **Streamlit-SDK** Space (not Docker) whose repository is this repository, so the front
matter above is what the platform supervisor reads.

The Space is **public at the platform level, and this is deliberate.** The platform's private-Space
visibility control admits only the Space owner and named collaborators — an officer holding an
`ehealthnigeria.org` Google Workspace account and no Hugging Face account would receive a
not-found response before the sign-in screen ever rendered. The access control here is the
application's own Google-domain sign-in gate (see `require_login()` in `auth.py`), not the
platform's visibility flag. **Do not flip this Space to private** — doing so locks out every
officer who has no Hugging Face account, without adding any real protection: the app-level gate
already refuses every signed-in user outside `ehealthnigeria.org`, and an unauthenticated
visitor at the public URL reaches only the sign-in screen — no uploader, no tabs, no cached data.

### 2. The secrets the Space needs

Set these as Space secrets (Settings → Variables and secrets). All of them arrive as flat
environment variables — this is why the app renders its own `.streamlit/secrets.toml` `[auth]`
configuration file at startup, before any other Streamlit call runs.

| Secret | Purpose | Where it comes from |
|--------|---------|----------------------|
| `GOOGLE_CLIENT_ID` | OAuth client id | The existing Google OAuth client (already created — see step 3 for the one addition it still needs) |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | The same existing Google OAuth client |
| `COOKIE_SECRET` | Signs the sign-in session cookie | **Must be strong and randomly generated by a human** — the application never defaults or generates one, and a guessable value is a session-forgery hole. Generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `REDIRECT_URI` | OAuth callback URL | The Space's direct `*.hf.space` host plus the OAuth callback path — see step 4 |
| `DATA_TEAM_CONTACT` | Contact address shown on the refusal page to an authenticated, out-of-domain visitor | The data team |
| `SMTP_TO` | Comma-separated primary recipients for the QC summary email | The data team |
| `SMTP_CC` | Comma-separated copy recipients for the QC summary email | The data team |
| `smtp_host` | Mail server hostname (not an email address) | Your mail provider |
| `smtp_port` | Mail server port | Your mail provider |
| `smtp_user` | SMTP account username | Your mail provider |
| `smtp_pass` | SMTP account password / app password | Your mail provider |

### 3. The variable that must never be set here

`MLOS_AUTH_DISABLED` is a local/dev-only opt-out that bypasses the sign-in gate when no `[auth]`
configuration is present. It must **never** be set on the deployed Space. The tell that it was
set anyway is the visible "authentication disabled" banner appearing on the live `.hf.space`
address — the app ignores the flag whenever real sign-in configuration is present, so the banner
showing up in production means the configuration itself is incomplete, not that the flag is
harmless there.

### 4. The redirect URI

`REDIRECT_URI` must be the Space's direct host followed by the OAuth callback path, e.g.
`https://<your-space>.hf.space/oauth2callback`. This exact value must be added to the existing
Google OAuth client's authorised redirect URI list before sign-in can work at all — the client
already exists (see step 2); only the Space's own redirect URI is new.

### 5. The address to give officers

Give officers the **direct Space address** — the `https://<your-space>.hf.space` host — never
the `huggingface.co/spaces/<org>/<space>` project page. The project page embeds the app inside a
cross-origin `<iframe>`, and browsers' third-party-cookie restrictions drop the sign-in cookie set
inside it, so an officer who uses that address appears to sign in and then appears signed out
again on every subsequent click. Distributing only the direct `.hf.space` address is the whole
fix for this.

### 6. Idle sleep

A free Space sleeps after roughly 48 hours idle and cold-starts on the next visit, so a slow first
load after a quiet weekend is expected behaviour, not a fault. Paid always-on hosting is out of
scope by constraint.

---

## Built By
eHealth Africa
