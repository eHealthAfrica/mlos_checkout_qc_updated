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

### Active

**M1 — Trustworthy verdict.** Close the 14 audited defects, then build the seam that lets the
rule set grow safely. Full audit: https://claude.ai/code/artifact/683128cf-bca1-4b57-9f73-81e171be893e

- [ ] Downloaded QC report covers all five layers, with its cover verdict derived from all of them (F1 — currently 2 of 5, so a failing file can download as "CLEAN")
- [ ] Rule 1 detects missing values identically across SQLite, CSV and Excel (F2 — currently cannot fail on CSV or Excel)
- [ ] One frame of record: displayed data and computed checks never describe different versions of the file (F4)
- [ ] Auto-correction runs once, deterministically — no regenerated GUIDs between QC and download (F5)
- [ ] Weighted score never rises because data was withheld (F6 — absent layers currently score 100%)
- [ ] Column names normalised once at load, so schema alignment and the rules agree on what a column is called (F7)
- [ ] Issue-row counts report distinct rows, not rule-row pairs (F8)
- [ ] Blank values cannot satisfy cross-table match rules (F9 — affects R2/R3/R4 and TP2/TP3/TP4)
- [ ] Email summary covers all five layers, including Settlement (F11)
- [ ] Raw-data report sheets written without per-cell styling (F12)
- [ ] Boundary reference fallback surfaces as a visible warning instead of silently widening to all states (F13)
- [ ] Boundary checks emitted in rule order B0, B1, B2, B3 (F14)
- [ ] pytest suite covering all rules, with a three-format golden fixture (`qc/` package and harness landed in Phase 1; rule-complete coverage and the .sqlite/.csv/.xlsx fixture remain)

**M2 — Central deployment.** Get it into officers' hands before growing the rule set.

- [ ] Deployed as a single private Hugging Face Space reachable by officers in every state
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
- **Privacy**: Settlement coordinates and population figures — The Space must be private. This is why hosting choice is a governance question and not only a technical one.
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
*Last updated: 2026-09-10 after Phase 1*
