# MLoS Checkout QC

## What This Is

A quality-control tool for Master List of Settlements (MLoS) checkout files. State-level
data officers upload a settlement submission — as `.sqlite`, `.csv` or `.xlsx` — and the
tool runs it against schema, data-integrity, cross-table and administrative-boundary rules,
returning a pass/fail verdict, a weighted score, and a per-rule Excel report they can act on.

Today it runs locally for one person. The target is a single central deployment that officers
in every state reach directly, with more QC layers than it has now.

## Core Value

**A file this tool calls clean is clean.**

Everything else — the score, the dashboard, the drilldowns, the email — is subordinate to the
verdict being trustworthy. When a tradeoff arises, correctness of the reported verdict wins
over features, speed, or presentation.

## Requirements

### Validated

Shipped capabilities inferred from the existing codebase. Note that these are validated as
*present and relied upon*, not as *defect-free* — the September 2026 audit found correctness
defects inside several of them, and M1 corrects those without removing the capability.

- ✓ Loads MLoS and Takeoffpoint data from SQLite views, Excel workbooks (sheet-name aliasing) and CSV — existing
- ✓ Accepts a separately uploaded Takeoffpoint file to enable cross-table checks for CSV submissions — existing
- ✓ Runs QC rules across five layers: Schema (S1–S2), MLoS (1–14), Settlement (SQ1–SQ4 incl. SQ2b), Takeoffpoint (TP2–TP5), Boundary (B0–B3) — existing
  (29 distinct identifiers pre-M1, not the 27 stated at initialization; 40 after Phase 1 split Rules 11 and 12 into field-named checks)
- ✓ Auto-corrects five field patterns before QC and logs what it changed — existing
- ✓ Validates ward codes, coordinates and state names against a 9,410-ward admin boundary reference — existing
- ✓ Produces a weighted QC score across the five layers — existing
- ✓ Per-rule issue drilldown on screen with downloadable Excel exports per layer — existing
- ✓ One-row-per-settlement longitudinal issue export with a column per rule — existing
- ✓ Downloadable auto-corrected MLoS file for re-submission — existing
- ✓ Emails a QC summary to the data team over SMTP — existing

**Shipped by M1:**

- ✓ Every check carries a rule identifier naming exactly one check; the 11 checks that shared Rules 11 and 12 now carry field-named identifiers (`11.urban`, `12.fulani`, …) and the other 29 are frozen (F3) — Phase 1
- ✓ Duplicate rule identifiers fail at import of the `qc/` registry, named in the error, asserted by a standing test (F3) — Phase 1
- ✓ Report row order reproducible across app restarts, proven by a subprocess test comparing raw bytes under three differing `PYTHONHASHSEED` values (F10) — Phase 1
- ✓ All five QC layers extracted to a `qc/` package that imports with Streamlit absent, enforced by a test — Phase 1
- ✓ Dependencies pinned with upper bounds; `pandas==3.0.5` exact and `numpy` explicitly declared — Phase 1
- ✓ Rule 1 detects missing values identically across SQLite, CSV and Excel — one `vec_is_absent` predicate with a uniform sentinel list, `"NA"` exempted case-sensitively (F2) — Phase 2
- ✓ One frame of record: `mlos_raw` / `mlos_corrected` held under distinct session keys, every consumer reads the corrected snapshot, guarded by a standing AST test (F4) — Phase 2
- ✓ Auto-correction runs exactly once per submission, keyed by a sha256 of the uploaded bytes; generated `eha_guid` values are session-scoped `uuid4` reused for every render and the download (F5) — Phase 2
- ✓ Column names normalised once at load by one typographic helper on all three officer-supplied paths; renames shown on screen and in a Columns Renamed report sheet; header collisions fail a new `S3` check (F7) — Phase 2
- ✓ Blank values cannot satisfy cross-table match rules; six `.missing` findings report the blank side separately (F9) — Phase 2
- ✓ Boundary reference fallback and absence are reported as failing checks `B4` and `B5`; canonical boundary order is B0 to B5 (F13) — Phase 2
- ✓ pytest suite (108 tests) with a byte-level `.sqlite`/`.csv`/`.xlsx` golden fixture asserting identical check summaries across formats — Phase 2
- ✓ Downloaded QC report covers all five layers: one combined QC Summary sheet with placeholder rows for unrun layers, a detail sheet per layer, and a cover verdict derived from all five via one shared `QcSummary` (F1) — Phase 3
- ✓ Weighted score never rises because data was withheld: an unrun layer contributes 0 and the total is shown against its achievable maximum, e.g. `72.0% of 80.0% achievable` (F6) — Phase 3
- ✓ Issue-row counts report distinct source rows per layer, shown with share of rows and the findings count, identical on screen, in the report and in the email (F8) — Phase 3
- ✓ Email summary carries five layer blocks including Settlement, every check under layer headings, and the verdict in the subject, built by a pure function in `qc/report.py` (F11) — Phase 3
- ✓ Raw-data and detail report sheets written as plain values with a styled header row only, proven by a `Cell.has_style` test (F12) — Phase 3
- ✓ Boundary checks appear B0 to B5 in canonical order at every summary table and export, proven by a PYTHONHASHSEED-varied standing test; a four-site agreement test keeps verdict, score and headline identical everywhere (F14) — Phase 3

### Active

**M1 — Trustworthy verdict.** All 14 audited defects are closed (Phases 1 to 3); M1 awaits milestone close-out. Full audit: https://claude.ai/code/artifact/683128cf-bca1-4b57-9f73-81e171be893e


**M2 — Central deployment.** Get it into officers' hands before growing the rule set.

- [ ] Deployed as a single access-controlled Hugging Face Space, public at the platform level, gated by app-level Google sign-in, reachable by officers in every state
- [ ] OIDC login for identity — no passwords stored by this application
- [ ] Submission log (who checked what, when, with what verdict) appended to a private Hugging Face Dataset repo
- [ ] SMTP credentials and recipient list moved out of the repository into Space secrets

**M3 — New QC layers.** Three new layers, built against the M1 test harness.

- [ ] Point-in-polygon geometry layer using real ward polygons, replacing the bounding-box-only B2 test
- [ ] Settlement-to-takeoffpoint distance sanity checks
- [ ] Population plausibility layer over `set_population`, `set_target` and `number_of_household`, beyond the ordering that rules 9 and 10 already enforce
- [ ] Team and activity coverage layer over `team_code` and `day_of_activity` — whether the microplan is coverable, not just populated
- [ ] Plausibility and coverage thresholds read from configuration, tunable without a code change

### Out of Scope

- **Longitudinal comparison against a ward's previous submission** — deferred to v2, not rejected. It is the only proposed layer requiring retained submission history beyond an append-only log, and dropping it keeps the QC engine stateless. Revisit after M3.
- **Storing officer passwords** — OIDC supplies identity; holding credentials adds real governance burden for no capability gain.
- **An external managed database (Neon, Supabase)** — a private HF Dataset repo covers an append-only log on the same platform as the app. Revisit only if a queryable national dashboard is wanted, which would also reopen the longitudinal layer.
- **Rewriting off Streamlit** — the framework is not the cause of any audited defect. All 14 sit in aggregation, caching, identity and export logic.
- **Real-time or API-based ingestion** — file upload matches how officers actually work.
- **Paid hosting** — free tier is a stated constraint.

## Context

**Brownfield.** A single-file Streamlit application, `app.py`, 1,961 lines, with no tests and
no test framework. All QC logic lives in the same file as the UI, though the five `run_*_qc()`
functions and `auto_correct_mlos()` are already pure DataFrame-in, results-out — which is why
extraction to `qc/` is tractable rather than a rewrite.

**Codebase map** at `.planning/codebase/` (7 documents, 2026-09-09). Two of its `CONCERNS.md`
entries are stale and were corrected during the audit: SQ4 is not a nested Python loop (it is
a single loop with a vectorised numpy inner step), and email sending does have error handling
at the call site. The real email defect is the omitted Settlement layer.

**Audit, 2026-09-09.** All 1,961 lines reviewed; 14 defects found — 2 critical, 5 high,
7 medium. Two allow a failing file to be reported as clean. Three make the same file score
differently depending on upload format, which is the property a QC tool cannot have. F2 and
F10 were confirmed by running the described cases against pandas 3.0.2.

**Data.** Ward boundary reference ships as two CSVs in the repo root totalling ~821 KB
(`ward_boundary_ref.csv`, `ward_boundary_bbox.csv`), covering 9,410 wards. Ward **polygons**
are available as GeoJSON or shapefile — confirmed during questioning, which unblocks M3's
geometry layer.

**Environment drift.** `requirements.txt` declares `pandas>=2.0.0` with no upper bound; the
environment resolves to 3.0.2. `numpy` is imported but never declared.

**Domain note.** `"NA"` is a valid domain value in the flag columns *and* Nasarawa's state
code, which is why every loader passes `keep_default_na=False`. That decision is correct;
F2 and F9 are unhandled consequences of it, not reasons to reverse it.

## Constraints

- **Tech stack**: Python 3 + Streamlit — Keeping both. No audited defect is framework-caused, and a rewrite would discard working rule logic.
- **Hosting**: Free tier only, on Hugging Face Spaces — Chosen over Streamlit Community Cloud because the free CPU tier offers roughly 16 GB RAM against ~1 GB. SQ4 is quadratic and the Excel report builder is memory-hungry, so the headroom is load-bearing, not luxury.
- **Storage**: A Space's filesystem is ephemeral — Anything that must survive a rebuild or idle restart goes to a private HF Dataset repo. A local SQLite of accounts or logs would be silently wiped.
- **Security**: No passwords stored by this application — Identity comes from an OIDC provider. SMTP credentials and the recipient list live in Space secrets and are never committed.
- **Privacy**: Settlement coordinates and population figures — What protects them is the application's sign-in and domain gate, not the platform's visibility flag. This is why hosting choice is a governance question and not only a technical one.
- **Configuration**: Plausibility and coverage thresholds are rules of thumb, not a published standard — They must live in configuration and be tunable without a code change, so a wrong threshold is a settings edit rather than a deploy.
- **Compatibility**: A verdict must not depend on upload format — `.sqlite`, `.csv` and `.xlsx` exports of the same data must produce identical check summaries. Three audited defects currently violate this.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix the audited defects before adding any new layer | Two defects let a failing file report as CLEAN. Adding rules on top of an untrustworthy verdict multiplies the problem instead of adding value. | — Pending |
| Hugging Face Spaces over Streamlit Community Cloud | Free tier gives ~16 GB RAM versus ~1 GB. Given a quadratic proximity check and a memory-hungry Excel builder, a 1 GB cap risks OOM mid-QC on a large state file. | — Pending |
| OIDC login; no passwords stored | Reduces the governance surface from "we hold state officers' credentials" to "we hold a list of who ran a check." | — Pending |
| Private HF Dataset repo for the submission log | Keeps the whole deployment on one platform with one credential set, and gives git-versioned history for free. No external database to operate or monitor for idle-pausing. | — Pending |
| Longitudinal layer deferred to v2 | The only proposed layer requiring retained submission history. Deferring it keeps the QC engine stateless, which is the largest available simplification. | — Pending |
| Extract to `qc/` + pytest inside M1, not M3 | Three new layers means substantial new rule code. There is currently no seam to add it against and nothing to catch a regression. | Done — Phase 1. Five layers behind `qc/`, 310 lines out of `app.py`, 34 standing tests, every relocation checked against a frozen pre-extraction baseline. |
| Uniform absence sentinel list (`null`, `none`, `n/a`, `nan`, `-`, blanks, whitespace) applied to every column, exact `"NA"` exempted | `keep_default_na=False` is correct but leaves CSV/XLSX blanks as `""`, which `isnull()` reports as present; one predicate for every rule keeps detection format-independent. Costly to change later: it moves the failing-row count on Rule 1, six `.missing` findings and B0 at once. | Done — Phase 2 (D-04/D-05) |
| Blank cells become their own `.missing` findings rather than being suppressed from match rules | A data-entry gap and a reconciliation failure are different problems for the officer; layers report overlap independently and Phase 3 fixes the row double-count instead. | Done — Phase 2 (D-01, D-03) |
| Generated `eha_guid` is a session-scoped `uuid4`, not content-derived | Satisfies "identical on first render and every rerun" with the simplest implementation. One-way: identifiers are not reproducible across sessions, so a cited ID cannot be regenerated. Confirmed at a blocking-human gate. | Done — Phase 2 (D-12) |
| Submission identity is a sha256 over uploaded bytes; two frames (`mlos_raw`, `mlos_corrected`) kept, one guard | Filename-plus-size collides for templated monthly exports, a correctness defect under Core Value. The user wanted an as-submitted audit sheet in the report, accepting doubled peak memory. | Done — Phase 2 (D-13/D-14/D-15) |
| Silent boundary-reference widening and absence become checks `B4` and `B5` | A check that appears only on failure carries no information by its absence; riding the checks list means screen, report and email pick it up with no signature change. | Done — Phase 2 (D-16 to D-19) |
| One shared `QcSummary` computation (`qc/report.py`) read by banner, workbook, email and Generate Report tab | F1 was a second, divergent verdict derivation on the report cover; making all four presentation sites read one object, guarded by a four-site agreement test, removes the class of defect rather than the instance. | Done — Phase 3 (Pattern 1) |
| Unrun layer earns 0 and the score is shown against its achievable maximum (`72.0% of 80.0% achievable`) | Renormalising weights would let withholding a file raise the score (F6). The user chose the visible ceiling over a bare capped number so the drop is explained where it appears. | Done — Phase 3 (D-01/D-02) |
| One combined QC Summary sheet with placeholder rows, plus a detail sheet per layer | The user preferred a single ordered sheet over five summary pairs; the placeholder row keeps an unrun layer visible. Costly: the old `MLoS QC Summary` / `Takeoffpoint QC Summary` sheet names are gone. | Done — Phase 3 (D-06/D-07) |
| Headline issue rows are the sum of per-layer distinct counts, shown with findings and share of rows | The user wanted a headline that reconciles by eye with the per-layer lines beneath it, over a cross-layer distinct count. | Done — Phase 3 (D-10 to D-13) |
| Ship M2 (deployment) before M3 (new layers) | Officers get a trustworthy tool sooner. Holding deployment back for more rules delays the value M1 creates. | — Pending |

## Open Items

Recorded rather than resolved. Neither blocks planning M1.

- **Threshold values** for population plausibility and team coverage — to be supplied by the user, destined for `config.json`. Needed before M3 is planned.
- **Python 3.11 floor** — `pandas==3.0.5` declares `requires-python: >=3.11`. Recorded in `requirements.txt` and not enforced beyond that; the Hugging Face Space must meet it. An M2 (Phase 4) deployment concern, discovered in Phase 1.
- **OIDC provider choice** — Spaces support native Hugging Face OAuth (`hf_oauth: true` in Space metadata), which avoids registering Google Cloud OAuth credentials and managing a redirect URI. Whether officers signing in with HF accounts is acceptable is an M2 planning question. Both paths remain open.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-10 after Phase 3*
