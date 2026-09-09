# MLoS Checkout QC — Research Summary

**Project:** Master List of Settlements (MLoS) Checkout Quality Control Tool  
**Domain:** Geospatial settlement-data QC for public-health microplanning, hosted Streamlit + Hugging Face Spaces deployment  
**Researched:** 2026-09-09  
**Confidence:** MEDIUM overall — stack and architecture HIGH (verified via official docs and codebase read), features MEDIUM (table-stakes checks HIGH, threshold *values* LOW—no published standards), pitfalls MEDIUM (geometry semantics HIGH, HF hosting patterns MEDIUM)

## Executive Summary

The MLoS Checkout QC tool validates settlement microplanning submissions against administrative boundary, data-integrity, and plausibility rules. The research confirms that the path forward—M1 verdict-fix + qc/ package extraction, M2 central deployment with OIDC and audit logging, M3 point-in-polygon + population + coverage layers—is architecturally sound and grounded in well-established patterns from DHIS2, GRID3, and geospatial-data-quality workflows. The tool's core value ("a file this tool calls clean is clean") is defensible only if three architectural principles hold: (1) the QC engine stays pure and testable (qc/ package never imports Streamlit or auth logic), (2) new plausibility/coverage rules are presented as advisory flags, not hard failures, so officers retain trust in the verdict, and (3) the submission log serializes writes to prevent race conditions under concurrent officer use.

Research uncovered two design conflicts embedded in the four research files and one critical open item. First, geopandas is not a runtime dependency per STACK.md, so the polygon cache must be shapely-backed (an STRtree spatial index), not a full GeoDataFrame—resolved by using st.cache_resource for the expensive STRtree structure, matching ARCHITECTURE.md's caching strategy. Second, plausibility and coverage rules must integrate into the weighted-score pipeline per FEATURES.md but must not contribute equally to pass/fail per PITFALLS.md—resolved by giving new layers a `severity: "ADVISORY"` attribute, lowering their weight or excluding them from the binary verdict while keeping them in the report and score. Third, the submission log must avoid races under concurrent submissions—resolved by one JSON file per submission in a git-backed folder watched by CommitScheduler, rather than appending to one shared log file.

The biggest risk is deploying M2 without resolving three prerequisites: (1) a concurrent-submission test, demonstrating two simultaneous officer QC runs both log correctly, (2) OIDC tested at the actual deployed Space URL (not just localhost), and (3) explicit data-governance sign-off that private HF Space + private Dataset repo satisfies the programme's data-handling policy, with a git-history scrub separate from moving current secrets. These are not implementation details—they are prerequisites to launching a tool that officers trust to validate settlement data at the state level.

## Key Findings

### Recommended Stack

**Core technologies:**

- **shapely** `>=2.1.2,<3.0.0`: Point-in-polygon (B2 replacement) and distance geometry. Vectorized ufuncs and bundled STRtree are sufficient; **geopandas is NOT a runtime dependency** (dev-time only for one-off polygon conversion from shapefiles/GeoJSON). This keeps cold-start weight and build-image size down on the free-tier Space.
- **pandas** `==3.0.5` (pin exact version, cap major at `<4.0.0`): Currently undeclared upper bound allows drift. Pandas 3.0 introduces string-dtype-by-default and Copy-on-Write-by-default—the Copy-on-Write semantics are the same bug class as defect F4 (one frame of record). Recommend running the M1 golden-fixture pytest suite explicitly against pandas 3.0.5 as part of the "dependencies pinned" M1 item.
- **numpy** `>=2.0.0,<3.0.0`: Must be declared explicitly (currently imported but never in requirements.txt). Pandas 3.x requires numpy >=1.26; capping at <3.0 avoids opting into numpy 3.x.
- **huggingface_hub** `>=1.30.0,<2.0.0`: CommitScheduler for append-only submission log. Pattern is documented for exactly this use case (watched folder, batched commits on interval).
- **HF Spaces native OAuth** (via `hf_oauth: true` Space metadata): Preferred OIDC path. Zero external IdP registration, flat env-var secrets that match HF Space secrets natively, avoiding the nested-TOML config friction of `st.login()` fallback path.

### Expected Features

**Must have (table stakes):**
- Single pass/fail verdict computed from *all* active layers (not per-layer patchwork)—M1 fixes this; M3 must register new layers into the same weighted-score/verdict computation.
- Per-rule drilldown from verdict to offending rows/values with downloadable Excel export.
- Point-in-polygon ward validation using real ward polygons, replacing bounding-box B2. This is the stated M3 goal and matches GRID3's own QA workflows.
- Population internal-consistency checks (target ≤ population, households ≤ population) via existing Rules 9–10 (baseline for M3's population-plausibility layer).
- Weighted score never rises when a layer is skipped/absent (F6 fix in M1)—M3's new layers must plug into this "absent layer cannot improve score" contract from day one.
- OIDC login gate before any QC run (M2, already planned).
- Per-submission attribution row appended to a private HF Dataset repo (M2, already planned).
- Append-only history (no edit/delete of past submission-log rows)—a discipline, not extra UI.

**Should have (differentiators):**
- Settlement-size outlier detection against ward/LGA neighbors (compare value to local peers' IQR, not one global range). This is a genuine geographic-outlier technique not found in comparable tools.
- Team+day geographic coherence check (settlements assigned to same team/day are within configurable distance). Reuses the distance utility M3 needs for takeoffpoint checks anyway.
- Team workload plausibility (settlements-per-team-day, population-per-team against local tunable norms). Officers set thresholds per state/campaign context, not fixed nationally.

**Defer to v2+:**
- Longitudinal comparison against a ward's prior submission (already deferred in PROJECT.md).
- Cross-state national rollup dashboard over the submission log (conflicts with stateless-engine design; same deferral bucket as longitudinal).
- Role-based access segregation by state (no current requirement; would require separate authorization layer, not just authentication).

**Critical Open Item from Research:** Should outlier/workload checks be scoped per-state or per-LGA? This affects threshold configuration and aggregation logic. Must be supplied by user during M3 planning.

### Architecture Approach

Extract the QC engine to a pure `qc/` package (no `import streamlit` anywhere) with eight modules (schema, mlos, settlement, takeoff, boundary, geometry, plausibility, coverage) and a shared `results.py` registry fixing the F3 duplicate-rule-number defect. Use a static rule registry (borrowed from Great Expectations' identity-as-first-class idea, but staying with ordinary pandas functions, not a DSL). Wrap the package in thin edge adapters for identity (`auth.py`, reads `st.user` only) and audit (`audit/submission_log.py`, writes to HF Dataset repo via CommitScheduler). Cache the ward polygon STRtree via `st.cache_resource` (expensive, not-trivially-copyable resource), not `st.cache_data` (which copies on every rerun). Validate plausibility/coverage thresholds from `config/thresholds.json` at startup using a typed config object (Pydantic or dataclasses + hand-written validation). Treat the app.py as orchestration only—load, call qc.run_all(), score, then independently call report builder and audit logger.

**Major components:**
1. **qc/** — Pure QC functions (8 layers, 35+ rules) with a shared Rule registry, no Streamlit dependencies. Tested against golden-fixture pytest suite covering all three upload formats (SQLite, CSV, Excel).
2. **auth.py** — Thin OIDC wrapper; resolves `st.user` once per session. HF Spaces native `hf_oauth: true` preferred.
3. **audit/submission_log.py** — Appends one record per completed run to a private HF Dataset repo via CommitScheduler, using one JSON file per submission to avoid concurrent-write races.
4. **report/** — Excel builder and SMTP emailer, inherits from existing pattern, no logic change.
5. **config/thresholds.json** — Version-controlled, git-blame-able, with inline documentation of provenance/rationale for every threshold (not just numeric values).

### Critical Pitfalls

1. **Point-in-polygon using `contains()` silently excludes settlements exactly on ward boundaries** — use `covers()` or `intersects()` instead, and surface "on boundary" as its own state distinct from "inside" and "outside," using `polygon.boundary.distance(point) < epsilon`. This happens constantly with real data because boundaries run along roads/rivers where settlements cluster.

2. **Two ward-code-matched boundary datasets don't agree on the same ward's shape** — GRID3 publishes multiple versions; NPC/state GIS units maintain their own. Before wiring polygons into B2, reconcile the polygon source's ward codes against `ward_boundary_ref.csv`; record boundary dataset source+version+vintage explicitly so a "wrong ward" flag can be traced to "which boundary snapshot said so."

3. **Plausibility and coverage rules flagged with the same visual weight as hard data-integrity failures erodes trust** — officers start disputing the verdict when a rule of thumb fires on a legitimate outlier. Prevent by giving these layers a distinct "Review" or "Advisory" status (visibly different from Pass/Fail) in both the UI and Excel export.

4. **Concurrent officer submissions race on the append-only HF Dataset log** — git commits from independent Streamlit sessions are not automatically serialized. Use one JSON file per submission (UUID + timestamp) in a folder watched by CommitScheduler. Always test two simultaneous submissions before rollout.

5. **OIDC redirect URI misconfiguration breaks silently between local dev and hosted Space** — HF Spaces' native `hf_oauth: true` removes this whole class of error. If using external IdP, test the actual OIDC flow against the deployed Space URL before M2 is done.

## Implications for Roadmap

### Phase 1: M1 — Trustworthy Verdict (Prerequisite)

**Rationale:** Close the 14 audited defects and extract the QC engine to qc/ with a rule registry fixing F3. This is the seam all future layers attach to.

**Delivers:**
- Pure qc/ package with 8 modules, rule registry, pytest golden-fixture suite covering all three upload formats
- F1–F14 defects closed
- Dependencies pinned: pandas==3.0.5, numpy >=2.0

**Research Flag:** Run golden-fixture pytest explicitly against pandas 3.0.5; Copy-on-Write and string-dtype migrations are subtle.

---

### Phase 2: M2 — Central Deployment (Officer Value)

**Rationale:** Get a trustworthy tool into officers' hands before adding layers.

**Delivers:**
- Private Hugging Face Space + OIDC (recommend native `hf_oauth`)
- Submission log: one JSON file per QC run (CommitScheduler-watched folder)
- SMTP credentials to Space secrets

**Pre-launch Gates (NOT skip-able):**
1. Concurrent-submission test: two simultaneous officer QC runs both log correctly
2. OIDC flow tested at actual deployed Space URL (not localhost)
3. Data-governance sign-off in PROJECT.md
4. Git-history scrub (previously-committed emails/credentials removed from full history)

**Research Flag:** Concurrent-write testing and OIDC redirect validation are highest-risk; both "work" locally and fail subtly at scale.

---

### Phase 3: M3 — New QC Layers (Feature Completeness)

**Rationale:** Officers have a working tool from M2. M3 adds geometry, population, and coverage validation strictly *after* M1's qc/ package exists.

**Delivers:**
- Point-in-polygon (replaces B2): uses `covers()`/`intersects()` with boundary-state handling
- Household-size ratio check (state-tuned range)
- Target-to-population ratio check
- Team+day geographic coherence check
- Config-driven thresholds with schema validation
- New layers in verdict/report with "Advisory" severity tier (not same weight as hard-integrity rules)
- v1.x: Settlement-size outlier, team workload plausibility

**Critical Decision:** Confirm plausibility/coverage rules are distinct "Advisory" status (not folded into Pass/Fail) before rule code is written.

**Research Flag:** Distance formula choice (Haversine vs. geodesic) and threshold calibration. Document error bounds; run real submissions through before finalizing.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified on PyPI; APIs verified against official docs. Pandas 3.0 migration risk is HIGH-confidence, mitigated by explicit testing. |
| Features | MEDIUM | Checks are HIGH-confidence (domain sources). Threshold *values* are LOW-confidence—no published standard exists. Table-stakes set is HIGH. |
| Architecture | HIGH | Codebase read line-by-line; patterns grounded in documented Streamlit and geospatial QA. |
| Pitfalls | MEDIUM | Geometry semantics HIGH (shapely docs). HF hosting/concurrency MEDIUM (community + GitHub issues). |

### Gaps to Address

1. **Threshold values:** No published standard. Research found ranges (household 3.5–8.15 persons by state; workload 5–80 contacts/day), but rules of thumb. User supplies during M3; recalibrate after real submissions.
2. **Outlier/workload scoping:** Per-state or per-LGA? Recommend per-state (larger sample), migrate to per-LGA in v1.x if needed.
3. **OIDC provider choice:** HF native or external IdP? Recommend HF native unless policy mandates corporate identity. Must decide before M2 planning.
4. **Data governance sign-off:** Prerequisite to M2 rollout. Programme must confirm private HF Space + Dataset repo satisfies data-handling policy.
5. **Git-history scrub:** Scope separately from "move current secrets." Remove previously-committed emails/credentials from full history.

## Conflict Resolutions

### Conflict 1: GEOMETRY LIBRARY vs CACHING OBJECT
Both hold. Geopandas is dev-time only (one-off conversion). Runtime uses shapely STRtree spatial index, cached via `st.cache_resource` (expensive, not-trivially-copyable resource). Same pattern; shapely-native implementation.

### Conflict 2: NEW LAYERS vs THE VERDICT
Both hold. New layers integrate structurally (same pipeline, registry, report builder) but with distinct `severity: "ADVISORY"`. Hard-integrity rules contribute to Pass/Fail; advisory rules are lower-weight or excluded from binary verdict with visual distinction. Preserves "clean means clean."

### Conflict 3: SUBMISSION LOG WRITE SHAPE
Both hold. CommitScheduler watches a folder; each submission writes to uniquely-named file (UUID + timestamp). Concurrent file creates handled better by git than concurrent modifications to one file. Folder aggregation is acceptable for audit log.

### Conflict 4: M3 SEQUENCING STRICTNESS
Both hold. M2 and M3 technically independent (after M1). But M1 is hard prerequisite (qc/ package, pytest, registry). PROJECT.md's "ship M2 before M3" is product decision. Concrete: M1 must finish; then M2 and M3 parallel technically, but product-decided M2 first.

---

*Research completed: 2026-09-09*  
*Ready for roadmap: yes*
