# Requirements: MLoS Checkout QC

**Defined:** 2026-09-09
**Core Value:** A file this tool calls clean is clean.

Requirement IDs are grouped by category. Milestone assignment (M1/M2/M3) is noted per
category; exact phase mapping is filled in during roadmap creation.

## v1 Requirements

### Verdict Integrity (M1)

The report and score must describe every layer that ran. Four of these close audited defects
that let a failing file be reported as clean.

- [ ] **VERDICT-01**: The downloaded QC report contains summary and detail sheets for all five layers (Schema, MLoS, Settlement, Takeoffpoint, Boundary) — closes F1
- [ ] **VERDICT-02**: The report cover verdict reads FAILING whenever any layer has a failing check, not only MLoS or Takeoffpoint — closes F1
- [ ] **VERDICT-03**: The emailed summary reports Settlement layer counts alongside the other four layers — closes F11
- [ ] **VERDICT-04**: Issue-row totals on screen, in the report and in the email count distinct settlement rows, not rule-row pairs — closes F8
- [ ] **VERDICT-05**: The weighted score awards no credit for a layer that ran zero checks, and displays that layer as "n/a" rather than 100% — closes F6
- [ ] **VERDICT-06**: Boundary checks appear in rule order B0, B1, B2, B3 in every summary table and export — closes F14

### Detection Correctness (M1)

A verdict must not depend on upload format, and a check must not pass because a value is absent.

- [x] **INTEG-01**: Rule 1 flags missing required fields identically whether the submission arrives as `.sqlite`, `.csv` or `.xlsx` — closes F2
- [x] **INTEG-02**: A blank value cannot satisfy a cross-table match rule (R2, R3, R4, TP2, TP3, TP4) — closes F9
- [ ] **INTEG-03**: Column names are normalised once at load so schema alignment and the rules resolve the same columns; renames are reported to the officer — closes F7
- [ ] **INTEG-04**: When state-name filtering yields no boundary reference and the check falls back to the full national set, that fallback appears as a visible warning rather than silently widening B1 — closes F13

### QC Engine (M1)

Rule identity, state handling and the structural seam the new layers will be built against.

- [x] **ENGINE-01**: Every check carries a rule identifier that is unique across all layers — closes F3
- [x] **ENGINE-02**: Rule identifier uniqueness is enforced when the rule registry is imported, and is covered by a standing test so the defect cannot reopen as the rule set grows
- [ ] **ENGINE-03**: Displayed data and computed checks always describe the same version of the submission, on the first render and on every subsequent rerun — closes F4
- [ ] **ENGINE-04**: Auto-correction runs exactly once per submission and produces the same output each time it is displayed, including generated `eha_guid` values — closes F5
- [x] **ENGINE-05**: All QC layers live in a `qc/` package containing no `import streamlit`, enforced by a test
- [x] **ENGINE-06**: A pytest suite covers every rule, including a golden fixture asserting that the same data exported as `.sqlite`, `.csv` and `.xlsx` produces identical check summaries
- [x] **ENGINE-07**: Dependencies are pinned with an upper bound, including `pandas==3.0.5` and an explicit `numpy` declaration
- [ ] **ENGINE-08**: Raw-data report sheets are written without per-cell font and border assignment — closes F12
- [x] **ENGINE-09**: Rule emission order is deterministic across application restarts, so two reports over identical data can be diffed row-for-row — closes F10 (`YN_NA_COLS` is a set literal at `app.py:100` and Python randomises string hashing per process, so Rule 12's eight checks currently appear in a different order every restart)

### Deployment (M2)

- [ ] **DEPLOY-01**: The app runs as a single private Hugging Face Space that officers in every state reach at one URL
- [ ] **DEPLOY-02**: SMTP credentials and the email recipient list are read from Space secrets and appear nowhere in the repository
- [ ] **DEPLOY-03**: Organisational email addresses currently committed at `app.py:644-647` are removed from git history, not only from the working tree
- [ ] **DEPLOY-04**: Officers are given the direct `*.hf.space` URL rather than the `huggingface.co/spaces/...` embed, so login cookies are not blocked by the iframe

### Authentication (M2)

- [ ] **AUTH-01**: An officer must sign in before running a QC check
- [ ] **AUTH-02**: The application stores no passwords; identity is supplied entirely by the OIDC provider
- [ ] **AUTH-03**: Login is verified against the deployed Space URL, not only localhost, before M2 is called done

### Submission Record (M2)

- [ ] **AUDIT-01**: Each completed QC run records who ran it, when, which file, and the resulting verdict and score
- [ ] **AUDIT-02**: Records are written one JSON file per submission to a private Hugging Face Dataset repo
- [ ] **AUDIT-03**: Two officers submitting simultaneously both have their runs recorded, with neither overwritten
- [ ] **AUDIT-04**: The log is append-only — the application offers no way to edit or delete a past record
- [ ] **AUDIT-05**: A failure or delay writing the submission record never blocks or slows the officer's verdict

### Threshold Configuration (M3)

Blocks every plausibility and coverage check below, so it lands first.

- [ ] **CONFIG-01**: Every new threshold is read from a version-controlled config file that documents each value's provenance and rationale, not just its number
- [ ] **CONFIG-02**: Configuration is validated at startup, and an invalid value produces a message naming the offending key
- [ ] **CONFIG-03**: Shipped defaults are placeholders, clearly marked as requiring the data team's real values

### Boundary Geometry (M3)

- [ ] **GEO-01**: Coordinates are validated by point-in-polygon test against the declared ward's actual polygon, replacing the bounding-box approximation in B2
- [ ] **GEO-02**: A settlement sitting exactly on a ward boundary is reported as on-boundary, not as outside the ward
- [ ] **GEO-03**: Every boundary finding records which boundary dataset and version produced it, so a disagreement between sources is legible rather than reported as a settlement error
- [ ] **GEO-04**: Settlement-to-takeoffpoint distance is checked against a configurable maximum, using one shared geodesic distance utility
- [ ] **GEO-05**: Ward polygons load once per session as a cached spatial index, not per script rerun

### Population Plausibility (M3)

- [ ] **POP-01**: A settlement is flagged when population ÷ number of households falls outside the configured plausible range
- [ ] **POP-02**: A settlement is flagged when target ÷ population falls outside the configured plausible fraction

### Team Coverage (M3)

- [ ] **TEAM-01**: Settlements sharing a `team_code` and `day_of_activity` are flagged when they are not within a configured distance of one another, using the same distance utility as GEO-04

### Advisory Severity (M3)

Cross-cutting, and the requirement that protects Core Value as the rule set grows. Research
found that folding rule-of-thumb checks into hard Pass/Fail would erode the guarantee M1 exists
to establish.

- [ ] **ADVIS-01**: Plausibility, coverage and boundary-vintage findings are reported at an Advisory severity, distinct from the Pass/Fail tier used by data-integrity rules
- [ ] **ADVIS-02**: An Advisory finding never changes the clean/not-clean verdict
- [ ] **ADVIS-03**: The three new layers never mutate submission data — they add findings to the report and nothing else
- [ ] **ADVIS-04**: The new layers appear in the same verdict banner, weighted score and per-rule Excel drilldown as the existing five, not in a parallel report

## v1.x Requirements

Deliberately held back until the v1 layers have run against real state submissions and there is
a baseline flag rate to calibrate against. Launching these untuned alongside their v1
counterparts would make it impossible to tell which threshold is wrong when either fires.

### Population Plausibility

- **POP-03**: A settlement is flagged when its population is a statistical outlier against its ward or LGA neighbours, using median and IQR rather than mean and standard deviation
- **POP-04**: Outlier scope (per-state versus per-LGA) is configurable

### Team Coverage

- **TEAM-02**: A team-day is flagged when its settlement count exceeds a configured cap
- **TEAM-03**: A team-day is flagged when its assigned population exceeds a configured cap

## v2 Requirements

Tracked, not in the current roadmap. The first two share a single blocker: each requires turning
the append-only submission log into a queryable historical store, which reopens the "no external
managed database" decision recorded in PROJECT.md.

### History

- **HIST-01**: A submission is compared against the same ward's previous submission, flagging vanished settlements, population jumps and `eha_guid` churn
- **HIST-02**: Pass rates and issue trends are reported across states and over time

### Access Control

- **ACL-01**: An officer sees only their own state's submissions

## Out of Scope

Explicitly excluded, with reasoning, to prevent re-adding.

| Feature | Reason |
|---------|--------|
| Auto-correcting population, coverage or geometry findings | The existing five auto-corrections are deterministic format fixes with one obviously-correct output. These findings are judgment calls — a genuinely small settlement or an edge-of-ward point is a fact to confirm, not a defect. Auto-fixing would silently alter real data and make the file less auditable, directly against Core Value. |
| A single hardcoded national threshold for household size, target ratio or workload | Actively wrong for Nigeria: household size ranges ~3.5 (Ekiti) to ~8.15 (Jigawa) persons by state, and team-day workload in the literature spans 5–80 person-contacts depending on campaign and terrain. One constant either floods whole states with false flags or misses real errors everywhere else. |
| Entry-time validation or form building (ODK/XLSForm-style blocking constraints) | This tool validates already-collected files uploaded after fieldwork. Entry-time prevention means building and maintaining a second collection surface competing with whatever officers actually collect with. |
| Cross-state or national rollup dashboard | Requires querying and aggregating retained history — the capability deliberately deferred by keeping the engine stateless. Deferred to v2 alongside longitudinal comparison, for the same reason. Must not arrive piecemeal as "just one summary chart" during M2. |
| Role-based access segregation across states | No governance requirement drives it. Adds authorization on top of authentication, with real design cost (who administers roles, what happens when an officer changes state) for a capability nobody has asked for. Deferred to v2 as ACL-01 rather than assumed. |
| In-tool editing of the uploaded file | Reopens the exact defect class M1 closes (F4): a verdict must describe one immutable snapshot. The download-correct-reupload flow already exists and is simpler to reason about. |
| Real-time or API-based ingestion | File upload matches how officers work. |
| Paid hosting | Free tier is a stated constraint. |
| Storing officer passwords | OIDC supplies identity; holding credentials adds governance burden for no capability gain. |
| An external managed database (Neon, Supabase) | A private HF Dataset repo covers an append-only log on the same platform as the app. Revisit only together with HIST-01 and HIST-02. |
| Great Expectations, soda-core or a rule DSL | Suite stores and YAML rule languages are over-engineering for ~35 rules in one repo. The borrowable idea is centrally-validated rule identity (ENGINE-02), not the framework around it. |
| geopandas as a runtime dependency | The B2 replacement is a row-aligned point-versus-declared-ward lookup, which vectorises in shapely alone. geopandas would add GDAL and pyproj cold-start weight for no gain. It stays a dev-only tool for one-time shapefile→GeoJSON conversion. |

## Traceability

Every v1 requirement maps to exactly one phase in `.planning/ROADMAP.md`.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VERDICT-01 | Phase 3 | Pending |
| VERDICT-02 | Phase 3 | Pending |
| VERDICT-03 | Phase 3 | Pending |
| VERDICT-04 | Phase 3 | Pending |
| VERDICT-05 | Phase 3 | Pending |
| VERDICT-06 | Phase 3 | Pending |
| INTEG-01 | Phase 2 | Complete |
| INTEG-02 | Phase 2 | Complete |
| INTEG-03 | Phase 2 | Pending |
| INTEG-04 | Phase 2 | Pending |
| ENGINE-01 | Phase 1 | Complete |
| ENGINE-02 | Phase 1 | Complete |
| ENGINE-03 | Phase 2 | Pending |
| ENGINE-04 | Phase 2 | Pending |
| ENGINE-05 | Phase 1 | Complete |
| ENGINE-06 | Phase 2 | Complete |
| ENGINE-07 | Phase 1 | Complete |
| ENGINE-08 | Phase 3 | Pending |
| ENGINE-09 | Phase 1 | Complete |
| DEPLOY-01 | Phase 4 | Pending |
| DEPLOY-02 | Phase 4 | Pending |
| DEPLOY-03 | Phase 4 | Pending |
| DEPLOY-04 | Phase 4 | Pending |
| AUTH-01 | Phase 4 | Pending |
| AUTH-02 | Phase 4 | Pending |
| AUTH-03 | Phase 4 | Pending |
| AUDIT-01 | Phase 5 | Pending |
| AUDIT-02 | Phase 5 | Pending |
| AUDIT-03 | Phase 5 | Pending |
| AUDIT-04 | Phase 5 | Pending |
| AUDIT-05 | Phase 5 | Pending |
| CONFIG-01 | Phase 6 | Pending |
| CONFIG-02 | Phase 6 | Pending |
| CONFIG-03 | Phase 6 | Pending |
| GEO-01 | Phase 7 | Pending |
| GEO-02 | Phase 7 | Pending |
| GEO-03 | Phase 7 | Pending |
| GEO-04 | Phase 7 | Pending |
| GEO-05 | Phase 7 | Pending |
| POP-01 | Phase 7 | Pending |
| POP-02 | Phase 7 | Pending |
| TEAM-01 | Phase 7 | Pending |
| ADVIS-01 | Phase 6 | Pending |
| ADVIS-02 | Phase 6 | Pending |
| ADVIS-03 | Phase 6 | Pending |
| ADVIS-04 | Phase 6 | Pending |

**Phase summary:**

| Phase | Name | Requirements |
|-------|------|--------------|
| 1 | QC Engine Seam and Pinned Environment | 5 |
| 2 | Detection Correctness and Three-Format Harness | 7 |
| 3 | Verdict and Report Integrity | 7 |
| 4 | Central Deployment and Officer Identity | 7 |
| 5 | Submission Record | 5 |
| 6 | Threshold Configuration and Advisory Severity | 7 |
| 7 | Geometry, Population and Coverage Layers | 8 |

**Coverage:**

- v1 requirements: 46 total
- Mapped to phases: 46 ✓
- Unmapped: 0
- Duplicated across phases: 0

Not mapped by design: v1.x (POP-03, POP-04, TEAM-02, TEAM-03) and v2 (HIST-01, HIST-02, ACL-01).

**Audited defect coverage:** all 14 defects from the 2026-09-09 audit (F1–F14) now have at least
one closing requirement, and no defect is split across phases. F10 was the last gap, closed by
ENGINE-09 and mapped to Phase 1 — the report-ordering symptom surfaces in the report layer, but
the cause is a set literal in the rule definitions, so it is fixed by the same registry that
enforces ENGINE-01/ENGINE-02.

Thirteen defects map one-to-one. The exception is **F1, which has two closing requirements** —
VERDICT-01 (the report contains sheets for all five layers) and VERDICT-02 (the cover verdict
derives from all five). These are two separable properties of one defect, both in Phase 3, so the
split costs nothing. Every *requirement* still belongs to exactly one phase.

## Open Items

Confirmed rather than resolved by research. Each needs an answer before the requirement it
blocks can be planned.

| Item | Blocks | Notes |
|------|--------|-------|
| Threshold values (household size range, target/population fraction, team-day distance) | CONFIG-03, POP-01, POP-02, TEAM-01 | No published domain standard exists. Research found household size ~3.5–8.15 persons by state and workload 5–80 person-contacts/team-day, which confirms these must be supplied locally rather than lifted from a source. |
| Outlier and workload scope: per-state or per-LGA | POP-04 | Within-country variance is wide enough that one national default is risky. Per-state gives a larger sample; per-LGA is finer but noisier. A product decision, not a research one. Deferred with the v1.x requirements. |
| OIDC provider: native Hugging Face OAuth or an external IdP | AUTH-01, AUTH-02 | Native HF OAuth is recommended — `st.login` needs a nested `[auth]` TOML block that flat Space environment variables cannot supply (Streamlit issue #10543), requiring a startup step to materialise `secrets.toml`. Both integrate identically at the `auth.py` boundary, so this does not block architecture. |
| Data governance sign-off for hosting settlement coordinates and population figures on a third-party free tier | DEPLOY-01 | A named decision, not a technical one. Required before M2 rollout. |
| Whether a boundary-vintage failure counts toward the weighted score | GEO-03, ADVIS-01 | GRID3's Nigeria ward boundaries are documented as "operational, not yet fully validated by government authorities." A phase-planning decision: exclude from the score entirely, or include at reduced weight. |

---
*Requirements defined: 2026-09-09*
*Last updated: 2026-09-09 after initial definition*
