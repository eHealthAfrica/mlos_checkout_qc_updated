# Roadmap: MLoS Checkout QC

## Overview

The tool already runs 27 QC rules and produces a verdict — but a September 2026 audit found
14 defects, two of which let a failing file download as CLEAN. So the journey starts by making
the existing verdict trustworthy rather than by adding anything: first a structural seam (one
rule registry with unique identity and stable ordering, one pure `qc/` package, one pinned
dependency set), then detection semantics that
no longer depend on upload format, then aggregation and reporting that describe every layer that
ran. Only once "a file this tool calls clean is clean" actually holds does the tool leave one
laptop for a private Hugging Face Space that officers in every state reach and sign into, with
every run recorded append-only. Growth comes last: a tiering-and-thresholds contract, and then
three new QC layers — real ward polygons, population plausibility, and team-day coverage — built
against the test harness and reporting at an Advisory severity that cannot move the verdict.

**Structure: horizontal layers.** Phases are technical layers that complete before assembly, not
end-to-end vertical slices. The accepted tradeoff: individual defect fixes are not separately
shippable. F1's report-coverage fix, for example, spans the registry (Phase 1) and the report
builder (Phase 3) and only becomes observable when Phase 3 closes. In exchange, each layer is
fixed once, in one place, rather than repeatedly per feature.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: QC Engine Seam and Pinned Environment** - Unique rule identity, stable rule order, one pure `qc/` package, one known dependency set
- [ ] **Phase 2: Detection Correctness and Three-Format Harness** - Same data, same findings, whatever format it arrived in
- [ ] **Phase 3: Verdict and Report Integrity** - Verdict, score, report and email describe every layer that ran
- [ ] **Phase 4: Central Deployment and Officer Identity** - One private Space URL, signed-in officers, no committed credentials
- [ ] **Phase 5: Submission Record** - Append-only log of who checked what, when, with what verdict
- [ ] **Phase 6: Threshold Configuration and Advisory Severity** - The tunable-threshold and severity-tier contract new layers plug into
- [ ] **Phase 7: Geometry, Population and Coverage Layers** - Real ward polygons, population ratios, team-day coherence

## Sequencing Notes

Established during research; recorded here so a future reader knows which orderings are forced
and which were chosen.

**Hard technical gates:**

- **Phases 1–3 (all of M1) gate Phases 6–7 (M3).** Growing to 35+ rules without the registry
  and the test suite reopens the duplicate-rule-number defect at larger scale.
- **ENGINE-01/02 and ENGINE-05 are one change, not three.** The duplicate-rule-number defect
  (F3) is caused by an `add()` closure copy-pasted across five `run_*_qc()` functions, keying
  results to a bare `"Rule#"` string. The fix is a shared Rule/RuleResult registry in
  `qc/results.py` — which is the same edit as extracting the layers to `qc/`. They must not be
  split across phases.
- **ENGINE-07 (pin `pandas==3.0.5`, declare `numpy`) lands in Phase 1, not as cleanup.** The
  environment currently resolves an unpinned pandas 3.x, so without this every subsequent fix is
  tested against whatever resolved that day. Pandas 3.0's Copy-on-Write-by-default is the same
  bug class as the ENGINE-03 (F4) defect being fixed.
- **Phase 6 gates Phase 7.** CONFIG-01/02/03 must exist before POP-01, POP-02 and TEAM-01 are
  written, so those layers are not retrofitted with validation later. ADVIS-01–04 change report
  and scoring *structure*, not just rule logic — settling the advisory tier first is what keeps
  the new layers out of the wrong severity tier, which would erode Core Value.
- **One geodesic distance utility, built once.** GEO-04 (settlement-to-takeoffpoint distance)
  and TEAM-01 (team+day geographic coherence) share it. Both sit in Phase 7 specifically so two
  implementations cannot diverge.

**Product preference, not a technical gate:**

- **M2 (Phases 4–5) ships before M3 (Phases 6–7) by choice.** After M1 completes, M2 and M3 are
  technically independent and could run in parallel. The user chose M2 first so officers get a
  trustworthy tool sooner. Reordering these is a product decision available at any time, not a
  constraint to be broken.

**M2 launch gates** — pre-rollout requirements, not nice-to-haves: AUDIT-03's concurrent-write
test, AUTH-03's OIDC verification at the real deployed Space URL, DEPLOY-03's git-history scrub
scoped separately from moving current secrets, plus a named data-governance sign-off (an Open
Item in REQUIREMENTS.md).

## Phase Details

### Phase 1: QC Engine Seam and Pinned Environment

**Goal**: The rule set has one place to live, one identity scheme, one stable emission order, and one known dependency set — so every later fix is testable and neither the duplicate-numbering nor the unstable-ordering defect can silently reopen.
**Depends on**: Nothing (first phase)
**Requirements**: ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-07, ENGINE-09
**Success Criteria** (what must be TRUE):

  1. Every check reports a rule identifier that names exactly one check — no two checks share a number anywhere on screen or in an export (down from 11 checks sharing 2 numbers)
  2. Importing the rule registry with a duplicated identifier fails immediately with a message naming the collision, and a standing test asserts this
  3. `import qc` succeeds in an interpreter with Streamlit uninstalled, and a test asserts no module under `qc/` imports streamlit
  4. A clean `pip install -r requirements.txt` resolves reproducibly to `pandas==3.0.5` with `numpy` explicitly declared and upper-bounded
  5. Two runs over identical data in separate processes emit checks in byte-identical order — the eight Rule 12 profile-flag checks included — so two reports can be diffed row-for-row

**Plans**: 5/6 plans executed

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Pin the dependency set (pandas 3.0.5, numpy declared and bounded) and stand up the pytest harness

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Build the fixture corpus and capture the frozen pre-extraction behaviour baseline

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Tracer: the qc/ registry seam proven end to end through the Schema layer

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-04-PLAN.md — Relocate the MLoS layer and split the two overloaded identifiers into eleven field-named ones

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-05-PLAN.md — Relocate the Settlement, Takeoffpoint and Boundary layers

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 01-06-PLAN.md — Relocate auto-correction, align the in-app rules reference, and prove cross-process order stability

**Notes**: **ENGINE-09 (F10) sits here, not in the report layer, and the code supports it.** The observable symptom is report reproducibility, but the cause is `YN_NA_COLS` being a set literal at `app.py:100`, iterated at `app.py:946` to emit eight checks. Python randomises string hashing per process, so the emission order differs every restart — confirmed by running the literal in three processes and getting three different orders. Two further points make Phase 1 the right home. First, that loop emits all eight checks as `add("12", ...)`, so the very same eight rows are both non-uniquely-identified (ENGINE-01/F3) and randomly ordered (ENGINE-09/F10); fixing identity without fixing order would be half a fix on one line of code. Second, one registry in `qc/results.py` can enforce uniqueness and ordering with a single mechanism, where the report layer could only re-sort after the fact. Checked for siblings while here: `TAKEOFF_REQUIRED_COLS` (`app.py:230`) is already consumed via `sorted()` at line 260, and the `VALID_*` sets are membership tests only — so the ordering fix is expected to be narrow, not a sweep.

### Phase 2: Detection Correctness and Three-Format Harness

**Goal**: The same submission produces the same findings whatever format it arrived in, and no check passes merely because a value was absent.
**Depends on**: Phase 1 (rules must have unique identity and live in `qc/` before a suite can address them individually)
**Requirements**: INTEG-01, INTEG-02, INTEG-03, INTEG-04, ENGINE-03, ENGINE-04, ENGINE-06
**Success Criteria** (what must be TRUE):

  1. A pytest suite covers every registered rule, and a golden fixture asserts that the same data exported as `.sqlite`, `.csv` and `.xlsx` produces identical check summaries — including Rule 1's missing-value findings
  2. A blank value on either side of a cross-table match (R2, R3, R4, TP2, TP3, TP4) is reported as a failure, never as a match
  3. Column names resolve from one normalisation performed at load, and the officer is shown which columns were renamed
  4. The findings on screen describe the same version of the submission as the downloadable auto-corrected file, and a generated `eha_guid` is identical on first render and on every rerun
  5. A boundary-reference fallback to the full national set appears to the officer as a warning rather than silently widening B1

**Plans**: TBD

**Notes**: `"NA"` is a valid domain value in the flag columns *and* Nasarawa's state code, which is why every loader passes `keep_default_na=False`. That decision is correct — INTEG-01 (F2) and INTEG-02 (F9) are unhandled consequences of it, not reasons to reverse it. Research flag: run the golden fixture explicitly against pandas 3.0.5; the Copy-on-Write and string-dtype migrations are subtle.

### Phase 3: Verdict and Report Integrity

**Goal**: The verdict, score, report and email all describe every layer that ran, so a failing file can never be reported as clean.
**Depends on**: Phase 2 (a layer must run correct checks before a summary of it can be honest; Phase 1 transitively, for rule identity and ordering)
**Requirements**: VERDICT-01, VERDICT-02, VERDICT-03, VERDICT-04, VERDICT-05, VERDICT-06, ENGINE-08
**Success Criteria** (what must be TRUE):

  1. The downloaded report contains summary and detail sheets for all five layers, and its cover verdict reads FAILING whenever any layer holds a failing check
  2. A layer that ran zero checks displays as "n/a" and earns no score credit — withholding a file can no longer raise the weighted score
  3. Issue-row totals agree on screen, in the report and in the email, and count distinct settlement rows rather than rule-row pairs
  4. The emailed summary reports Settlement layer counts alongside the other four layers
  5. Boundary checks appear as B0, B1, B2, B3 in that order in every summary table and export, and raw-data sheets are written without per-cell font or border assignment

**Plans**: TBD
**UI hint**: yes

**Notes**: F10 ("report row order reproducible across app restarts") shows its symptom in this layer but is **not** closed here — it is closed by ENGINE-09 in Phase 1, where the cause lives. See the Phase 1 notes for the evidence. What this layer inherits is the guarantee: because rule order is already stable by Phase 1, the report and summary tables here can be diffed row-for-row without re-sorting. F10 was one of two defects confirmed by running the described case against pandas 3.0.2.

### Phase 4: Central Deployment and Officer Identity

**Goal**: Officers in every state reach one trustworthy URL and must sign in before running a check, with no credential anywhere in the repository or its history.
**Depends on**: Phase 3 (M1 complete — the point of deploying is to put a *trustworthy* verdict in officers' hands)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):

  1. An officer in any state opens one private `*.hf.space` URL directly — not the `huggingface.co/spaces/...` embed — and reaches the tool with login cookies intact
  2. No QC check can be run before signing in, and the application stores no password of its own
  3. Sign-in is verified working against the deployed Space URL, not only localhost
  4. SMTP credentials and the recipient list are read from Space secrets, appear nowhere in the working tree, and the addresses previously committed at `app.py:644-647` are absent from full git history

**Plans**: TBD

**Notes**: **Open items blocking this phase** — (a) *OIDC provider choice*: native Hugging Face OAuth (`hf_oauth: true`) or an external IdP. Research recommends HF native, since `st.login` needs a nested `[auth]` TOML block that flat Space environment variables cannot supply (Streamlit issue #10543). Both integrate identically at the `auth.py` boundary, so this does not block architecture — but it must be answered before AUTH-01/AUTH-02 are planned. (b) *Data-governance sign-off* for hosting settlement coordinates and population figures on a third-party free tier — a named decision, not a technical one, required before DEPLOY-01 rollout. Do not invent either answer. Treat DEPLOY-03 (history scrub) as separately scoped from DEPLOY-02 (moving current secrets); "removed from the working tree" is not "removed from history".

### Phase 5: Submission Record

**Goal**: Every completed check leaves an append-only record of who ran it, on what, and with what verdict — without ever slowing the officer down.
**Depends on**: Phase 4 (a record naming the officer requires resolved identity)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05
**Success Criteria** (what must be TRUE):

  1. After a check completes, a record exists naming the officer, the timestamp, the file, and the resulting verdict and score
  2. Records land as one JSON file per submission in a private Hugging Face Dataset repo
  3. Two officers submitting simultaneously both have their runs recorded with neither overwritten, demonstrated by a concurrent-submission test
  4. The application offers no path to edit or delete a past record
  5. A failure or delay writing the record leaves the officer's verdict unaffected and on time

**Plans**: TBD

**Notes**: One JSON file per submission (UUID + timestamp) in a folder watched by `CommitScheduler` — not appends to one shared log file. Git commits from independent Streamlit sessions are not automatically serialised, and concurrent file *creates* are handled far better by git than concurrent modifications to one file. A Space filesystem is ephemeral, so anything that must survive a rebuild or idle restart goes to the Dataset repo. Criterion 3 is a launch gate: it "works" locally and fails subtly under real concurrency.

### Phase 6: Threshold Configuration and Advisory Severity

**Goal**: The tunable-threshold and severity-tier contract that the three new layers plug into exists and is settled before any new rule code is written.
**Depends on**: Phase 3 technically (needs the registry, the test harness and the "absent layer cannot improve the score" contract). Sequenced after Phase 5 by product choice, not technical need — see Sequencing Notes.
**Requirements**: CONFIG-01, CONFIG-02, CONFIG-03, ADVIS-01, ADVIS-02, ADVIS-03, ADVIS-04
**Success Criteria** (what must be TRUE):

  1. Every threshold is read from a version-controlled config file recording each value's provenance and rationale, not only its number
  2. Starting the app with an invalid config value produces a message naming the offending key, and shipped defaults are visibly marked as placeholders awaiting the data team's real values
  3. A finding at Advisory severity is visibly distinct from a Pass/Fail finding both on screen and in the Excel export, and never changes the clean/not-clean verdict
  4. Advisory layers appear in the same verdict banner, weighted score and per-rule Excel drilldown as the existing five — not in a parallel report
  5. No advisory layer mutates submission data; it only adds findings, asserted by a test

**Plans**: TBD
**UI hint**: yes

**Notes**: This is the requirement set that protects Core Value as the rule set grows. Research found that folding rule-of-thumb checks into hard Pass/Fail erodes the guarantee M1 exists to establish: officers start disputing the verdict when a rule of thumb fires on a legitimate outlier. **Open items blocking this phase** — (a) *Threshold values* (household size range, target/population fraction, team-day distance) block CONFIG-03. No published domain standard exists; research found household size ~3.5 (Ekiti) to ~8.15 (Jigawa) persons by state and workload 5–80 person-contacts per team-day, which confirms these must be supplied locally rather than lifted from a source. Ship placeholders marked as such; do not invent numbers. (b) *Whether a boundary-vintage failure counts toward the weighted score* blocks ADVIS-01 — exclude entirely, or include at reduced weight. GRID3's Nigeria ward boundaries are documented as "operational, not yet fully validated by government authorities." Also worth not foreclosing at config-schema design time: the per-state versus per-LGA scope question, which is deferred with the v1.x POP-04 requirement.

### Phase 7: Geometry, Population and Coverage Layers

**Goal**: Three new QC layers run — real ward polygons, population plausibility, team-day coherence — all reporting through the Phase 6 advisory contract, with one shared distance utility.
**Depends on**: Phase 6 (thresholds must be configurable and validated, and the advisory tier settled, before any of these rules is written)
**Requirements**: GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, POP-01, POP-02, TEAM-01
**Success Criteria** (what must be TRUE):

  1. A settlement's coordinates are tested against its declared ward's actual polygon rather than a bounding box, and a settlement sitting exactly on the boundary is reported as on-boundary — neither inside nor outside
  2. Every boundary finding names the boundary dataset and version that produced it, so a disagreement between sources reads as a source disagreement rather than as a settlement error
  3. Ward polygons load once per session as a cached spatial index; a script rerun does not rebuild it
  4. Settlement-to-takeoffpoint distance and team-day settlement spread are both checked against configured maxima using one shared geodesic distance utility
  5. A settlement is flagged when population ÷ number of households, or target ÷ population, falls outside its configured plausible range

**Plans**: TBD

**Notes**: Ward polygons are available as GeoJSON or shapefile — confirmed during questioning, which is what unblocks this layer. `geopandas` stays a dev-only tool for one-time shapefile→GeoJSON conversion; the runtime uses shapely alone with an `STRtree` index cached via `st.cache_resource` (expensive, not-trivially-copyable), never `st.cache_data` (which copies on every rerun). Criterion 1 hinges on using `covers()`/`intersects()` rather than `contains()`, which silently excludes on-boundary points — this happens constantly with real data because boundaries run along roads and rivers where settlements cluster. Before wiring polygons into B2, reconcile the polygon source's ward codes against `ward_boundary_ref.csv` (9,410 wards). **Open item blocking this phase**: threshold values gate POP-01, POP-02, TEAM-01 and GEO-04's configurable maximum. Research flag: distance formula choice (Haversine versus geodesic) — document error bounds, and run real submissions through before finalising thresholds.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. QC Engine Seam and Pinned Environment | 5/6 | In Progress|  |
| 2. Detection Correctness and Three-Format Harness | 0/TBD | Not started | - |
| 3. Verdict and Report Integrity | 0/TBD | Not started | - |
| 4. Central Deployment and Officer Identity | 0/TBD | Not started | - |
| 5. Submission Record | 0/TBD | Not started | - |
| 6. Threshold Configuration and Advisory Severity | 0/TBD | Not started | - |
| 7. Geometry, Population and Coverage Layers | 0/TBD | Not started | - |

## Coverage

All 46 v1 requirements map to exactly one phase. No orphans, no duplicates.

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 | ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-07, ENGINE-09 | 5 |
| 2 | INTEG-01, INTEG-02, INTEG-03, INTEG-04, ENGINE-03, ENGINE-04, ENGINE-06 | 7 |
| 3 | VERDICT-01, VERDICT-02, VERDICT-03, VERDICT-04, VERDICT-05, VERDICT-06, ENGINE-08 | 7 |
| 4 | DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, AUTH-01, AUTH-02, AUTH-03 | 7 |
| 5 | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05 | 5 |
| 6 | CONFIG-01, CONFIG-02, CONFIG-03, ADVIS-01, ADVIS-02, ADVIS-03, ADVIS-04 | 7 |
| 7 | GEO-01, GEO-02, GEO-03, GEO-04, GEO-05, POP-01, POP-02, TEAM-01 | 8 |
| | **Total** | **46** |

**Deliberately not in this roadmap:**

- v1.x — POP-03, POP-04, TEAM-02, TEAM-03. Held back until the v1 layers have run against real
  state submissions and there is a baseline flag rate to calibrate against.
- v2 — HIST-01, HIST-02, ACL-01. The first two share one blocker: turning the append-only log
  into a queryable historical store, which reopens the "no external managed database" decision.

---
*Roadmap created: 2026-09-09*
