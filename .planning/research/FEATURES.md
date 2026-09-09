# Feature Research

**Domain:** Settlement / master-list QC and microplanning data-quality tooling (geospatial, public health)
**Researched:** 2026-09-09
**Confidence:** MEDIUM — verdict/drilldown UX and point-in-polygon QA patterns are corroborated across
multiple independent sources (DHIS2, GRID3). Numeric thresholds (household size, team workload,
target/population ratio) have no single published standard in this domain — every source that
gives a number frames it as a local/contextual planning parameter, not a constant. Treat the
*existence* of a check as HIGH confidence and the *threshold value* as LOW confidence throughout
this document; that split is called out per row, not just here.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single pass/fail verdict banner, computed from *all* active layers | DHIS2's Data Quality app shows exactly this: "Validation passed successfully" or a violation list — one verdict, not a per-layer patchwork the officer has to reconcile themselves. This app already does it (`report-verdict-pass`/`-fail` banner); M3 must extend the same verdict computation to the three new layers, not bolt on a second banner. | LOW (extend existing) | Already implemented for 5 layers under M1 (F1). M3 must register new layers into the same weighted-score/verdict computation, not a parallel one. |
| Per-rule drilldown from the verdict to the offending rows/values | DHIS2: clicking "show details" on a violated rule reveals the specific data elements and values involved, not just a count. This app already does this per layer/per rule with Excel export. | LOW (extend existing) | Point-in-polygon, population-plausibility and coverage findings need to show *which settlement, which value, which neighboring value/expected range* — a bare rule-failed-count is not enough for a field officer to act on it. |
| Point-in-polygon settlement-to-ward validation using real polygons | This is the standard method in every geospatial settlement QA workflow found (GRID3's own QA scripts check that a point's *recorded* ward attribute matches the ward it is *spatially* inside — literally this check). A bounding-box approximation (current B2) is a known-weaker substitute, not an accepted end state. | MEDIUM | Ward polygons already confirmed available (GeoJSON/shapefile per PROJECT.md) — this replaces B2, it does not add a parallel check. Needs `shapely`/`geopandas`-class point-in-polygon, which is a new dependency the current stack doesn't have (pandas/numpy only). |
| Population field internal-consistency checks (target ≤ population, households ≤ population) | Already implemented as Rules 9–10. Domain sources agree these are the two non-negotiable ordering constraints — GPEI guidance explicitly frames target population as bounded by (not exceeding) the administrative/census population. | LOW (existing) | Baseline for M3's "beyond the ordering that rules 9 and 10 already enforce" population layer — the new layer sits on top of this, doesn't replace it. |
| Household-size sanity check (population ÷ households falls in a configurable plausible range) | Self-evidently sound as a *check* — dividing population by household count and flagging an implausible ratio (e.g., 40 people/household, or 0.5) is basic arithmetic sanity, not a domain-specific claim. Every settlement-QC-adjacent source treats "does this ratio make sense" as baseline hygiene. | LOW-MEDIUM | **Needs a standard for the range, not for the check.** Nigeria average household size varies 3.5–8.15 persons across states (NBS/DHS-class sources), so a single hardcoded range is wrong; the range must be config, ideally per-state, matching the project's existing constraint that thresholds live in `config.json`. |
| Team/day not-null + internal format validity for `team_code`, `day_of_activity` | Already covered by Rule 1 (NOT NULL) across all fields per F2's fix. Table stakes, already validated infra. | LOW (existing) | This is the floor the new "coverable" layer sits above — M3's job is to check whether populated fields describe a *workable* plan, not whether they're populated. |
| Weighted score never silently improves when a layer is skipped/absent | Already an audited defect (F6) being fixed in M1. Every hosted multi-layer QC tool this research found treats "missing data can't look like a pass" as a correctness baseline, not a nice-to-have. | LOW (existing, M1) | M3's new layers must plug into the same "absent layer cannot raise the score" contract from day one — don't reintroduce F6 for population/coverage/geometry. |
| Excel/downloadable per-layer report covering new layers | Existing per-layer Excel export pattern (already table stakes per the Validated section). Field officers work offline/asynchronously from a downloaded artifact, consistent with every campaign-microplanning source describing paper/Excel-based team plans as the working document. | LOW (extend existing) | New layers need their own sheet(s) in the same report structure used for Schema/MLoS/Settlement/TP/Boundary. |
| Login gate before any QC run, once hosted centrally | Every hosted multi-user tool assumption in the research (Streamlit-in-Snowflake audit patterns, Databricks Streamlit write-back+audit pattern) treats "who is this" as a precondition for any write/log action, not an add-on. This app plans OIDC (M2) already. | MEDIUM (M2, already planned) | Streamlit itself has **no native user-identity or audit layer** — confirmed by research; identity must come from the OIDC/HF-OAuth layer, not anything Streamlit provides out of the box. |
| Per-submission attribution row (who ran it, when, verdict/score) | This is the one thing every hosted multi-user QC/audit pattern found does differently from a single-user local tool: it always records *who* triggered *what result*, appended, not just the result. Already scoped for M2 ("Submission log ... appended to a private HF Dataset repo"). | LOW-MEDIUM (M2, already planned) | Table stakes the moment the tool stops being single-user — this is not a differentiator, it's the price of admission for a shared deployment holding governance-sensitive data (settlement coordinates, population). |
| Append-only history (no edit/delete of past submission-log rows) | Standard audit-trail expectation (Wikipedia's audit-trail definition and every audit-log pattern found agree: an audit log that can be edited by the thing it's auditing isn't an audit log). Matches the project's own framing of the HF Dataset repo as "append-only." | LOW | This is a *discipline*, not a feature to build extra UI for — the risk is an accidental "edit log entry" affordance creeping in later, not a missing capability now. |

### Differentiators (Competitive Advantage)

Features that set the product apart from a generic checklist tool. Not required, but valuable
given this app's Core Value ("a file this tool calls clean is clean").

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Settlement-size outlier detection against ward/LGA neighbors | Goes beyond a fixed global range: flags a settlement whose population is wildly out of line with its *local* peers (same ward/LGA), which is the standard spatial-outlier technique (compare a value to the mean/IQR of its spatial neighbors — Tukey-fence-style). No comparable tool in this exact domain (DHIS2, GRID3, GPEI docs) does this specifically for settlement population, so implementing it well is a genuine differentiator over "table stakes range check." | MEDIUM-HIGH | Needs a neighbor definition (same ward, or same LGA if ward is too small a sample) and a robust-statistics threshold (median + IQR, not mean + stdev, since population distributions are right-skewed). Threshold is still a rule of thumb — belongs in config — but the *method* (compare-to-local-neighbors rather than one global constant) is itself the differentiator, and is self-evidently sound regardless of the exact multiplier chosen. |
| Team+day geographic coherence check (settlements assigned to the same team/day cluster spatially) | This directly answers "is the microplan coverable" rather than "is the field populated" — the stated goal of this layer. A team assigned settlements scattered across non-adjacent wards on the same day is not coverable regardless of population math. No comparable *automated* check for this was found in DHIS2/GRID3/GPEI tooling; GPEI's own best-practice guidance says microplans must be field-validated because coverage data alone doesn't verify a plan, which is exactly the gap this closes computationally. | MEDIUM | Needs pairwise or centroid distance between settlements sharing a `team_code`+`day_of_activity`, using the coordinates already loaded. Reuses the same geodesic-distance utility that the already-planned "settlement-to-takeoffpoint distance sanity check" needs — build once, use twice. |
| Team workload plausibility (settlements-per-team-day, population-per-team, against a configurable local norm) | Literature confirms per-team-day workload is treated as a locally-set planning parameter (examples range 5–80 person-contacts/team-day depending on campaign type and terrain), not a global constant — so a tool that lets the state officer tune this per context, rather than hardcoding a number that fits nowhere, is a real advantage over any "one-size" checklist. | MEDIUM | Depends on the config-driven threshold mechanism already required by PROJECT.md constraints. Should probably support (a) a simple settlements/team/day cap and (b) an optional population/team/day cap, both overridable, rather than one fused metric. |
| One integrated verdict across geometry + demographic + coverage layers, not three separate tools | Comparable ecosystems (DHIS2 validation rules, GRID3 polygon QA, ODK constraints) each solve *one* of these problems in isolation — no single tool found does administrative-boundary geometry, population plausibility, *and* team-coverage feasibility under one verdict for the same settlement master list. That integration, on top of the existing schema/MLoS/cross-table layers, is the product's actual differentiation versus assembling GRID3 scripts + a spreadsheet + manual GPEI-style field review. | LOW (architecture, not new logic) | This is realized "for free" if each new layer plugs into the existing weighted-score/verdict seam rather than becoming a separate report — reinforces the table-stakes row above rather than adding new surface area. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems, given this project's stated constraints (stateless
engine, free-tier hosting, no published thresholds, "verdict correctness over everything").

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Auto-correcting population/coverage/geometry findings the way the app already auto-corrects 5 format fields | The app already auto-corrects flag columns, GUIDs, etc., so it's a natural-feeling extension: "why not also auto-fix an implausible household count?" | The existing auto-corrections are deterministic *format* fixes (NULL→NA, strip braces) with one obviously-correct output. A population/coverage/geometry finding is a judgment call — a genuinely small settlement, a genuinely long walking route, a genuinely edge-of-ward point are not defects, just facts the officer must confirm. Auto-"correcting" these would silently alter real data and directly violates the Core Value ("a file this tool calls clean is clean" — an auto-fixed file that changes population figures is not more trustworthy, it's less auditable). | Flag only. These three new layers should never mutate submission data — they add rows to the issue report, full stop. |
| Hardcoding one national household-size / team-workload / target-ratio constant | It looks like the obviously-right shortcut: "just put 5 people/household in the code and move on." | Research confirms this is actively wrong for Nigeria specifically — household size ranges from ~3.5 (Ekiti) to ~8.15 (Jigawa) persons, and team-day workload literature shows 5–80 person-contacts/team-day depending on setting. A single constant will either falsely flag entire states as implausible or let real errors through everywhere else. | Config-driven thresholds, ideally overridable per state, exactly as PROJECT.md already mandates ("Plausibility and coverage thresholds are rules of thumb ... They must live in configuration"). This research reinforces that constraint rather than adding a new one. |
| Point-of-entry validation / becoming a form-builder (ODK/Kobo-style blocking constraints) | ODK/XLSForm constraints are the most visible "data quality" pattern in this exact domain, so it's tempting to make the tool prevent bad data at entry instead of just reporting it after the fact. | This app validates *already-collected* files (`.sqlite`/`.csv`/`.xlsx`) uploaded after fieldwork — it has no relationship to the data-collection tool officers actually used. Building entry-time constraints means building and maintaining a second, competing collection surface, which is out of scope per PROJECT.md ("Real-time or API-based ingestion" is explicitly out; "file upload matches how officers actually work"). | Keep the batch, after-the-fact QC model. If entry-time prevention is ever wanted, it belongs in whatever ODK/Kobo/other tool collects the MLoS data, not here. |
| Cross-state / national rollup analytics dashboard over the submission log | Once a hosted, multi-user, append-only log exists, "let's chart pass rates across all states over time" is an obvious next ask, and it feels like a small extension of the log that's already being built for M2. | This requires *querying and aggregating retained history* — the exact capability the project explicitly deferred by keeping the QC engine stateless and scoping the log as an append-only record rather than a queryable store. PROJECT.md already flags this: an external managed database is "revisit only if a queryable national dashboard is wanted, which would also reopen the longitudinal layer." It belongs in the same bucket as the deferred longitudinal-comparison layer, for the same reason — both require turning an append-only log into a queryable historical database. | Defer alongside longitudinal comparison, to the same "v2, revisit after M3" decision point. Do not let it sneak in piecemeal as "just one summary chart" during M2 or M3. |
| Role-based / per-state visibility restrictions on who can see whose submissions | Feels like a natural governance feature once multiple states share one hosted tool — "officer in State A shouldn't see State B's data." | PROJECT.md scopes identity only as far as OIDC login + attribution ("no passwords stored," "who checked what") — it does not currently require access *segregation*, and building RBAC pulls in a second identity concern (authorization, not just authentication) that has real design cost (who administers roles? what happens when a state officer moves states?) for a capability nobody has asked for yet. | Ship attribution without access segregation for M2/M3. Revisit only if a specific governance requirement for cross-state confidentiality is raised — treat it as a new, explicitly-scoped decision, not an assumed default. |
| Live/real-time collaborative editing of the uploaded file inside the tool | Once the tool shows per-row issues, "let me just fix this cell right here" feels like an efficiency win over download-fix-reupload. | Breaks the "one frame of record" principle the project is actively fixing under M1 (F4) — a QC verdict must describe one immutable snapshot of an uploaded file. In-tool editing reopens exactly the class of defect M1 exists to close (displayed data and computed checks describing different versions of the file), and duplicates the download-corrected-file-for-resubmission flow that already exists and is simpler to reason about. | Keep download → officer corrects in their own system → re-upload → re-run QC. This is also consistent with the file-upload-not-real-time-ingestion constraint already in PROJECT.md. |

## Feature Dependencies

```
Point-in-polygon geometry layer (replaces B2)
    └──requires──> Ward polygon data (already confirmed available)
    └──requires──> Point-in-polygon geometry library (new dependency — shapely/geopandas class)

Household-size plausibility check
    └──requires──> Config-driven threshold mechanism (config.json, per PROJECT.md constraint)
    └──enhances──> Existing Rules 9–10 (target ≤ population, households ≤ population)

Target/population ratio plausibility check
    └──requires──> Config-driven threshold mechanism
    └──builds-on──> Existing Rule 9

Settlement-size outlier detection (differentiator)
    └──requires──> Ward/LGA grouping of settlements (already available via ward_code)
    └──requires──> Config-driven threshold mechanism
    └──enhances──> Household-size plausibility check (same "is this number believable" family)

Team+day geographic coherence check
    └──requires──> Geodesic distance utility over settlement lat/long (already loaded)
    └──shares-utility-with──> Settlement-to-takeoffpoint distance sanity check (already scoped for M3)

Team workload plausibility check
    └──requires──> Config-driven threshold mechanism
    └──enhances──> Team+day geographic coherence check (both describe "coverable")

New-layer verdict integration
    └──requires──> Existing weighted-score/verdict computation (post-M1 fix, F1/F6)
    └──requires──> qc/ package + pytest harness (M1, so new layers are tested like existing ones)

Per-submitter attribution
    └──requires──> OIDC login (M2)
    └──requires──> Private HF Dataset repo for append-only log (M2, already decided)

Cross-state rollup dashboard (anti-feature, noted for contrast)
    └──requires──> Queryable historical store (NOT the append-only log as currently scoped)
    └──conflicts-with──> Stateless-QC-engine decision (same conflict as longitudinal comparison)
```

### Dependency Notes

- **Point-in-polygon requires a new geometry dependency:** the current stack is pandas/numpy only
  (per STACK.md); `shapely` (or `geopandas`, heavier) is new. This is a phase-ordering signal —
  it should land with its own dependency-pinning step, consistent with the "dependencies pinned"
  M1 item, not slip in unpinned.
- **All three plausibility/coverage checks share one config mechanism:** household size, target
  ratio, settlement outlier multiplier, and team workload cap are all "rules of thumb the user
  supplies." Building the config-loading mechanism once, then adding four threshold entries to
  it, is cheaper and safer than four bespoke config paths — this is a strong argument for
  sequencing "config-driven thresholds" as its own small piece of work before the checks that
  consume it.
- **Team-coherence and takeoffpoint-distance checks want the same distance utility:** M3 already
  separately scopes "Settlement-to-takeoffpoint distance sanity checks" and this milestone's
  "team/activity coverage layer." Both are fundamentally "distance between two lat/long points
  from the same table, compared to a threshold." One shared helper avoids two subtly different
  distance implementations disagreeing with each other later (the exact class of bug M1 is
  cleaning up elsewhere in this codebase).
- **Cross-state dashboard conflicts with the stateless-engine decision:** it is not merely
  deferred like the longitudinal layer, it is the *same* deferral — both need the append-only
  log turned into a queryable store, which is explicitly the trigger PROJECT.md names for
  revisiting the "no external database" decision. They should be revisited together, not treated
  as two separate future asks.

## MVP Definition

Framed against this milestone's four additions specifically (M3's three new layers + M2's
attribution, which the question set spans).

### Launch With (v1 of this milestone)

Minimum viable for "the microplan is validated on geometry, plausibility, and coverage, and the
tool knows who ran it":

- [ ] Point-in-polygon ward check replacing bounding-box B2 — the stated M3 goal, and the only
      of the four additions with an unambiguous "correct" implementation (a point either is or
      isn't inside the recorded ward's polygon).
- [ ] Household-size ratio check (population ÷ households vs. configurable range) — self-evident
      arithmetic, immediately useful, and the natural extension of existing Rules 9–10.
- [ ] Target/population ratio check (configurable, e.g. flag targets that are an implausibly high
      or low fraction of population) — builds directly on Rule 9's existing ordering check.
- [ ] Team+day geographic coherence check (settlements sharing a team/day are within a
      configurable distance of each other) — the most direct answer to "coverable, not just
      populated," and reuses the distance utility M3 needs anyway for takeoffpoint checks.
- [ ] Config file (or config section) holding every new threshold, with sane placeholder defaults
      clearly marked as needing the user's real values — required by PROJECT.md's own constraint,
      and blocks all four checks above until it exists.
- [ ] OIDC login gate + per-run attribution row appended to the HF Dataset log — already scoped
      for M2, listed here because the question set treats it as part of this milestone's shape.
- [ ] New layers integrated into the existing single verdict banner, weighted score, and per-rule
      Excel drilldown — not a second UI paradigm.

### Add After Validation (v1.x)

Add once the launch set has run against real state files and the officer/user has a feel for
whether the thresholds and checks are actually catching real problems without excessive noise:

- [ ] Settlement-size outlier detection against ward/LGA neighbors — genuinely more valuable once
      there's a baseline of "normal" flagging volume to compare it against; risk of threshold
      noise is higher for a technique nobody in this domain has validated yet.
- [ ] Team workload plausibility (settlements/team/day, population/team/day caps) — needs the
      geographic coherence check's real-world flag rate as a sanity check first, since both
      describe the same "coverable" concept and launching both untuned at once makes it hard to
      tell which threshold is wrong when either fires.

### Future Consideration (v2+)

Explicitly out of this milestone's scope, consistent with PROJECT.md's Out of Scope section:

- [ ] Longitudinal comparison against a ward's prior submission — already deferred to v2 in
      PROJECT.md; this research does not surface a reason to reconsider that.
- [ ] Cross-state / national rollup dashboard over the submission log — belongs in the same
      deferral bucket as longitudinal comparison (see Anti-Features and Dependency Notes above);
      both require turning the append-only log into a queryable historical store.
- [ ] Role-based access segregation across states — no current requirement drives it; revisit only
      if a specific governance need is raised.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Point-in-polygon ward check (replaces B2) | HIGH | MEDIUM | P1 |
| Config-driven threshold mechanism | HIGH (blocks 4 other rows) | LOW | P1 |
| Household-size ratio check | HIGH | LOW | P1 |
| Target/population ratio check | MEDIUM-HIGH | LOW | P1 |
| Team+day geographic coherence check | HIGH | MEDIUM | P1 |
| OIDC login + per-run attribution log | HIGH (governance-required, M2) | MEDIUM | P1 |
| New layers into existing verdict/score/report | HIGH (prevents a second UI paradigm) | LOW | P1 |
| Settlement-size outlier vs. neighbors | MEDIUM | MEDIUM-HIGH | P2 |
| Team workload plausibility (settlements or population per team/day cap) | MEDIUM | MEDIUM | P2 |
| Cross-state rollup dashboard | LOW (no current requirement) | HIGH (needs queryable store) | P3 |
| Role-based access segregation | LOW (no current requirement) | MEDIUM | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add once P1 checks are validated against real files
- P3: Nice to have, future consideration — tied to the same "queryable history" decision as the
  already-deferred longitudinal layer

## Competitor Feature Analysis

"Competitors" here are comparable QC/QA workflows in the same domain family, not direct
commercial rivals — none of them do everything this tool aims to do under one verdict.

| Feature | DHIS2 Data Quality App | GRID3 Settlement QA | ODK/Kobo (XLSForm constraints) | GPEI Microplan Practice | Our Approach |
|---------|------------------------|----------------------|----------------------------------|--------------------------|--------------|
| Verdict presentation | Single pass/violation-list banner + click-through detail per rule | No unified verdict UI — script output + manual review | Inline per-field error at entry time (no batch verdict) | No software verdict — manual field validation exercises | Keep the existing single banner + weighted score + per-rule drilldown pattern; extend to new layers rather than introducing a new pattern |
| Geometry validation | Not spatial (facility/aggregate data, not settlement points) | Point-in-polygon ward match, duplicate-ID, invalid-geometry checks via scripts, always paired with manual verification | Not spatial | Field verification of maps/routes, not automated geometry | Automated point-in-polygon against real ward polygons, replacing bounding-box approximation |
| Population/demographic plausibility | Validation-rule expressions between data elements (generic, not settlement-specific) | Not in scope (settlement extents, not demographics) | Per-field constraint (e.g., a single question's numeric range) at entry time | Manual: compare enumerated vs. revalidated household counts in the field | Config-driven ratio/range checks (household size, target/population) plus a neighbor-based outlier check, all flag-only |
| Coverage/team feasibility | Not in scope | Not in scope | Not in scope | Manual team microplans (route, start/end points) validated in the field, explicitly *not* trusted to coverage data alone | Automated geographic-coherence and workload-plausibility checks over `team_code`/`day_of_activity`, as a computable proxy for what GPEI says must otherwise be field-verified |
| Multi-user attribution | N/A (DHIS2 is a platform with its own user/auth system already) | N/A (script-based, run by a GIS analyst, not multi-tenant) | N/A (per-submission metadata, not per-QC-run attribution) | N/A (manual process, not software) | OIDC login + append-only per-run attribution log in a private HF Dataset repo |

## Sources

- [DHIS2 — Learner's Guide to Validation Rules (Use)](https://docs.dhis2.org/en/topics/training-docs/analytics-tools-academy/using-validation-rules/learneraposs-guide-to-validation-rules-use.html)
- [DHIS2 — Data Quality (user guide)](https://docs.dhis2.org/en/use/user-guides/dhis-core-version-241/collecting-data/data-quality.html)
- [DHIS2 — Data Quality and Use](https://docs.dhis2.org/en/implement/health/chis-community-health-information-system/implementation/data-quality-and-use.html)
- [GRID3 — Settlement Mapping and Classifying Settlement Locations (whitepaper)](https://eprints.soton.ac.uk/469540/1/GRID3_Settlement_White_Paper_June2021.pdf)
- [GRID3 — polyCheck (polygon validation tooling)](https://grid3.github.io/polyCheck/)
- [GRID3 — Settlement Mapping solution page](https://grid3.org/solution/settlement-mapping)
- [WHO/GPEI — Best Practices in Microplanning for Polio Eradication](https://polioeradication.org/wp-content/uploads/2018/12/Best-practices-in-mircoplanning-for-polio-eradication.pdf)
- [WHO/GPEI — Best Practices for Planning a Vaccination Campaign for an Entire Population](https://polioeradication.org/wp-content/uploads/2018/12/Best-practices-for-planning-a-vaccination-campaign-for-an-entire-population.pdf)
- [Revised Household-Based Microplanning in Polio SIAs, Kano State, Nigeria 2013–2014 (PMC)](https://ncbi.nlm.nih.gov/pmc/articles/PMC4818558)
- [Tracking Vaccination Teams During Polio Campaigns via GIS, Northern Nigeria 2013–2015 (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4818548/)
- [KoboToolbox — Adding constraints in XLSForm](https://support.kobotoolbox.org/constraints_xls.html)
- [ODK — Form Logic docs](https://docs.getodk.org/form-logic/)
- [Average Household Size in Nigeria (ArcGIS/Esri Hub)](https://hub.arcgis.com/maps/esri::average-household-size-in-nigeria/about)
- [Nigeria Living Standards Survey 2020 (NBS)](https://www.nigerianstat.gov.ng/elibrary/read/1123)
- [Enhancing COVID-19 vaccination coverage in Sierra Leone (PMC, team workload data)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9594546/)
- [A Model for Spatial Outlier Detection Based on Weighted Neighborhood Relationship (arXiv)](https://arxiv.org/pdf/1911.01867)
- [Databricks community — Streamlit app with write-back capability and audit trail display](https://community.databricks.com/t5/warehousing-analytics/databricks-streamlit-app-with-write-back-capability-and-audit/td-p/165538)
- [Streamlit discuss — Multiple Users](https://discuss.streamlit.io/t/multiple-users/44948)
- Project context: `/Users/BusayoFashoto/Desktop/4_april_26/4th_april_2026/git_clone/mlos_checkout_qc/.planning/PROJECT.md`
- Codebase grounding: `app.py` (existing verdict banner at lines ~651, ~1078, ~1846–1850; weighted score at ~1465–1538; Rules 9–10 at ~910–924; schema fields including `set_population`/`set_target`/`number_of_household`/`team_code`/`day_of_activity` at ~224–225, ~1226)

---
*Feature research for: settlement/master-list QC and microplanning data-quality tooling*
*Researched: 2026-09-09*
