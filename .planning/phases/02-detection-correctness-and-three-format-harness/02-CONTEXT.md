# Phase 2: Detection Correctness and Three-Format Harness - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers detection that does not depend on how the submission arrived, and does
not pass because a value was absent — plus the test harness that proves both.

Concretely: one absence predicate shared by every rule, so `.sqlite`, `.csv` and `.xlsx`
exports of the same data produce identical findings; blanks that can no longer satisfy a
cross-table match; column names resolved once at load against the canonical schema, with
renames shown to the officer; one corrected snapshot that the screen, the checks and the
download all describe; and a boundary-reference fallback the officer can see.

It delivers **no report-structure or verdict-coverage changes**. The report's five-layer
sheet coverage, the cover verdict derivation, distinct issue-row counting, the zero-check
scoring rule and boundary rule ordering in exports are all Phase 3 (VERDICT-01 to VERDICT-06,
ENGINE-08). Advisory severity is Phase 6 (ADVIS-01), which is why nothing in this phase may
rely on a third severity tier — every new check must read PASS or FAIL.

Requirements closed: INTEG-01, INTEG-02, INTEG-03, INTEG-04, ENGINE-03, ENGINE-04, ENGINE-06.

</domain>

<decisions>
## Implementation Decisions

### Absence Predicate (INTEG-01, shared with INTEG-02)

- **D-04:** A value is **absent** when it is pandas NA / `None` / NaN, the empty string,
  whitespace-only, **or** one of the case-insensitive sentinels `null`, `none`, `n/a`, `nan`,
  `-`. This is the single predicate Rule 1 and the cross-table rules both use. It closes
  INTEG-01 because `keep_default_na=False` (correctly) leaves CSV/XLSX blanks as `""`, which
  `isnull()` at `qc/mlos.py:92` reports as present, so today Rule 1 only detects nulls from
  `.sqlite`. — **Reversibility:** costly — the predicate decides every null-ness verdict in
  the rule set; widening or narrowing it later moves the failing-row count on Rule 1, six
  `.missing` findings and B0 simultaneously, so any report already filed against the old
  definition disagrees with a rerun.

  *Recorded deviation:* the narrower three-state predicate (null / empty / whitespace only,
  no content inspection) was recommended and **not** chosen. The user selected the sentinel
  list deliberately. The planner must not quietly narrow it back.

- **D-05:** The sentinel list applies **uniformly to every column**, with the exact literal
  `"NA"` exempted case-sensitively. Restricting sentinel matching on the flag columns and
  `state_code` was recommended and not chosen. — **Reversibility:** one-way for real data —
  `"NA"` is simultaneously a valid flag value in eight profile columns and Nasarawa's
  `state_code`. The single case-sensitive exemption is the only thing keeping a genuine
  Nasarawa submission from having its state code read as missing. There is no migration for
  a Nasarawa file already scored under a broken exemption.

  **Consequence the planner must accept and pin:** `highrisk = "N/A"` now reads as *absent*
  rather than reaching Rule 12, which would otherwise have flagged it as an invalid flag
  value. This is the known cost of the uniform list.

  **Required guard:** the sentinel list and the `"NA"` exemption must be a named,
  version-controlled constant in `qc/domain.py` (alongside `VALID_YN_NA` and `FLAG_COLS`),
  with a standing test asserting that `"NA"` survives as present in every flag column **and**
  as `state_code`, and that lowercase `"na"` is likewise not swept up. Phase 1's D-12 set the
  precedent: the structural guarantee is the half a standing test can assert cheaply.

### Blank-Side Cross-Table Matches (INTEG-02)

- **D-01:** A blank becomes its **own registered finding**, separate from a failed match.
  Six new checks distinguish "nothing to match on" from "no match found", because they are
  different problems for the officer — a data-entry gap versus a reconciliation failure.
  The underlying bug is that `set(takeoff["name"].dropna().str.strip())` at `qc/mlos.py:114`
  cannot drop `""` (`keep_default_na=False`), so `""` enters the valid set and a blank matches
  a blank.
- **D-02:** The six identifiers are **`2.missing`, `3.missing`, `4.missing`, `TP2.missing`,
  `TP3.missing`, `TP4.missing`**. `missing` was chosen over `blank` because it matches the
  vocabulary already in the rule set — Rule 1 is "Required Fields — Not Null", B0 is "Ward
  Code — Not Available on Data", and INTEG-01 speaks of "missing required fields". One word
  for one concept. The dotted-suffix shape follows Phase 1's D-01/D-02. — **Reversibility:**
  costly — identical rationale to Phase 1's D-01: the identifier is the join key between
  check records and detail rows and is printed in every summary table, per-rule Excel sheet
  name, emailed summary and sidebar reference table.
  Longest sheet name check: `Rule TP2.missing` is 16 characters, well inside Excel's 31-char
  limit.
- **D-06:** Each `.missing` finding reports blanks in **its own subject table only** —
  `2.missing` reports MLoS rows with a blank `takeoffpoint`; `TP2.missing` reports
  Takeoffpoint rows with a blank `name`. Both sides of every join are covered by the pair,
  not by either rule alone. This preserves the existing invariant that a detail frame comes
  from one table with that table's identifying columns, which the per-rule drilldown, the
  longitudinal view and the Excel sheet builder all assume.
- **D-07:** `2.missing`, `3.missing` and `4.missing` **emit unconditionally**, including when
  no Takeoffpoint table was supplied. They test MLoS's own columns and need no second table.
  Today R2/R3/R4 are guarded on `"name" in takeoff.columns` (`qc/mlos.py:113`), so a CSV
  submission with no separate Takeoffpoint file gets no signal at all on a blank
  `takeoffpoint` — the exact silence INTEG-02 exists to remove. The Takeoffpoint-side trio
  still runs only when that table exists, because zero rows must never report PASS.
- **D-03:** Layers **report overlap independently**. A blank `ward_code` fires Rule 1
  (it is in `_NOT_NULL_COLS`), `4.missing` and B0 — three failing checks for one cell, and
  that is correct. Suppressing the duplicates would make a check's outcome depend on whether
  another layer ran, which is the coupling Phase 1's seam exists to prevent, and would make
  `4.missing` read PASS for a row that has no ward code at all. Phase 3's VERDICT-04 already
  fixes the row-total double-counting, which is the part that actually misleads.

### Column Normalisation (INTEG-03)

- **D-08:** Normalisation is **purely typographic**: trim, lowercase, convert runs of
  whitespace and hyphens to a single underscore, collapse repeated underscores. No semantic
  aliasing. The defect is that `qc/schema.py:25` computes
  `set(mlos.columns.str.strip().str.lower())` to decide whether a required column is present,
  while every rule tests the raw frame (`if "takeoffpoint" in mlos.columns`,
  `qc/mlos.py:113`) — so a header of `Takeoffpoint` satisfies S1 and then silently skips
  every rule that needs it.
- **D-20 (user directive):** **`README.md` is the canonical column vocabulary.** Its
  "Required MLoS Columns (43)" and "Required Takeoffpoint Columns (4)" tables define the
  authoritative names, and normalisation resolves incoming headers toward them.
  *Verified during discussion:* those 47 names match `qc/domain.py`'s `MLOS_REQUIRED_COLS`
  and `TAKEOFF_REQUIRED_COLS` exactly — zero drift in either direction, all already
  lowercase snake_case. No reconciliation work is needed first, but the planner must treat
  a future divergence between `README.md` and `qc/domain.py` as a defect. (The `Ref Ward
  Code` / `In Boundary Reference` names further down README are output columns the Boundary
  Issues tab adds, not inputs.)
- **D-09:** **Every header is renamed** to its normalised form, with no canonical-set
  membership test — `Field Notes` becomes `field_notes` even though no rule reads it. The
  whole frame ends up in consistent snake_case. Renaming only headers that land in the
  canonical 47 was recommended and not chosen.
- **D-10:** When two headers normalise to the same label, a new registered Schema-layer check
  **`S3` "Column Name Collision"** fails, naming both original headers, and **that colliding
  pair is left un-normalised** so no duplicate label is ever created. Rules needing that
  column skip exactly as they do for a missing one, and S1 reports it missing. Every other
  rule runs normally. This must be handled rather than left to chance: with duplicate labels
  `mlos["ward_code"]` returns a DataFrame, not a Series, and the next
  `.astype(str).str.strip()` or `.isna()` raises instead of producing a mask — it would also
  break `mlos[mask][cols]` in every `add()` closure and the raw-sheet writer.
  `S3` is free; the Schema layer holds only `S1` and `S2`.
- **D-11:** Renames are reported to the officer in **two places**: an on-screen expander near
  the auto-correct summary listing only headers that actually changed, and a
  **"Columns Renamed" sheet** in the downloadable QC report so the record travels with the
  file. It carries **no Pass/Fail and no score weight** — a rename is not a defect, and
  Advisory severity (ADVIS-01) is not available until Phase 6. A clean submission shows
  nothing.

### One Snapshot and Generated Identifiers (ENGINE-03, ENGINE-04)

The defect is two calls to `auto_correct_mlos`. At `app.py:742`, inside the cache-miss
branch, `mlos_df, _ac_log = auto_correct_mlos(mlos_df)` rebinds the local name while
`st.session_state["mlos_df"]` (set at `app.py:191`) still holds the **uncorrected** frame. On
a rerun the cache hits at `app.py:724`, the branch is skipped, correction never runs — so the
displayed rows are uncorrected while the cached checks came from the corrected frame. Then
`app.py:982` calls it a **second** time for the download, minting fresh `uuid4()` values at
`qc/autocorrect.py:98`. That single line is both F4 and F5.

- **D-12:** A generated `eha_guid` is a **`uuid4()` computed once per submission and cached**,
  reused for every render and the download. A deterministic content-derived UUIDv5 was
  recommended and **not** chosen. — **Reversibility:** one-way — once officers have filed
  reports citing generated IDs, changing the derivation re-mints every one of them and there
  is no migration for a filed or emailed report. This is the same class of constraint as
  Phase 1's D-04.

  **Accepted consequence:** IDs are stable within a session but not across sessions. The same
  file uploaded next month, or by a colleague, or after a Space restart or idle timeout,
  mints different IDs, so an ID cited in a filed report cannot be regenerated. The user chose
  this knowing it satisfies success criterion 4 as written ("identical on first render and on
  every rerun") without claiming more. It also means v2's HIST-01 `eha_guid`-churn detection
  will see churn from re-generation as well as from real change — noted for that phase, not
  this one.

- **D-13:** Submission identity is a **sha256 over the uploaded bytes** (both files when a
  separate Takeoffpoint is supplied), replacing `(uploaded.name, size, tp_key)` at
  `app.py:693` and its reuse as `qc_cache_key` at `app.py:722`. Filename-plus-size collides
  for templated monthly exports — two different states both submitting `mlos_checkout.xlsx`
  at the same byte size would share a cache entry, and the second officer would see the
  first one's GUIDs, verdict and score. Given Core Value, a cache-key collision is a
  correctness defect, not a performance detail. Side benefit: re-uploading byte-identical
  data within a session now hits the same snapshot, so D-12's drift is confined to across
  sessions.

- **D-14:** Session state holds **both frames under distinct keys** — `mlos_raw` as uploaded
  and `mlos_corrected` after auto-correction — with one rule: the on-screen table, all five
  QC layers and the auto-corrected download always read `mlos_corrected`; only the report's
  as-submitted sheet reads `mlos_raw`. A single corrected snapshot was recommended and not
  chosen; the user wanted the as-submitted audit record inside the report.
  **Accepted cost:** two versions coexist — the condition F4 arose from — and peak memory
  for the frame doubles on a free-tier Space where SQ4 is already quadratic and the report
  builder is memory-hungry.

- **D-15:** Because D-14 keeps two frames, the guard against F4 recurring is **structural, not
  conventional**: distinct names (`mlos_raw` / `mlos_corrected`, with no bare `mlos_df`
  surviving) plus a standing test that parses `app.py` and asserts every one of the five
  `run_*_qc` calls, the on-screen table and `build_corrected_excel` receive
  `mlos_corrected`, and that `mlos_raw` appears at exactly one call site — the report's
  as-submitted sheet. This reuses the AST-over-`app.py` pattern Phase 1 already established
  (its plan-03/04/05 verify commands used `ast.parse(open('app.py').read())`, and
  `tests/test_no_streamlit_in_qc.py` enforces the import boundary the same way).

  A `qc.run_all(snapshot, on_step=...)` façade was offered as the stronger structural
  alternative and not chosen. Phase 1 explicitly declined a `run_all()` wrapper
  (`qc/__init__.py:10`) because the five call sites are interleaved with per-step progress
  bars, status lines and per-layer pass counts. **That decision stands** — the planner must
  not introduce `run_all()` as an "improvement".

- The second `auto_correct_mlos` call at `app.py:982` is **deleted**, reading the cached
  corrected frame instead. That is what closes ENGINE-04's "runs exactly once per
  submission".

### Boundary Reference Fallback (INTEG-04)

The site is `qc/boundary.py:89-91`: when `state_name` filtering yields nothing, `filtered_ref`
and `filtered_bbox` are both reassigned to the full national set, and B1 validates against all
9,410 wards instead of the state's subset — silently. `run_ward_boundary_qc` returns only
`(checks, details)`, so there is no warning channel today.

- **D-16:** A new registered **`B4` "Boundary Reference Fallback"** fails whenever the
  widening fired, with a description stating that the check ran against the national
  reference rather than the file's state. **B1 keeps running**, because a ward code absent
  from even the national reference is still a true finding worth reporting. Riding the
  existing checks list means no signature change and every consumer — screen, report, email —
  picks it up for free.
  **The description must name B2 as well as B1:** the fallback reassigns `filtered_bbox` too
  (`qc/boundary.py:91`), so B2's scope widens with B1's. INTEG-04's text names only B1; this
  is wider than the requirement's wording and deliberately so.
  **Blind-spot note:** B3 independently catches the cross-state case B1's widening misses —
  it maps each `ward_code` to the state the reference assigns it and compares against the
  file's `state_name` (`qc/boundary.py:113-135`). The fallback is therefore a trust problem,
  not a total detection hole.
- **D-17:** B4 **emits on every run where a reference exists** — PASS naming the state's ward
  count, FAIL naming the widening. A check that appears only on failure carries no
  information by its absence, and every other rule in the codebase emits either PASS or FAIL
  through its `add()` closure.
- **D-18:** A **separate `B5` "Boundary Reference Unavailable"** reports a missing reference,
  distinct from the widening. With the reference files absent, `load_boundary_refs`
  (`app.py:290-299`) returns empty frames and the guards mean **B1, B2 and B3 all silently
  fail to emit** — only B0 runs. One check per condition.
- **D-19:** In that same run, **B4 emits nothing**. With no reference there is no scope for
  B4 to describe, and D-17's "always emit" would otherwise make B4 state something false
  (PASS, "validated against N wards", when there are no wards). B5 carries the whole story;
  the summary has exactly one row explaining the situation. This follows B0's existing
  early-return precedent at `qc/boundary.py:42-50`, where the layer emits a single check and
  returns.

- Canonical boundary order becomes **B0, B1, B2, B3, B4, B5**, which keeps Phase 3's
  VERDICT-06 (boundary checks in rule order in every summary and export) satisfiable.

### Claude's Discretion

- **Which load paths normalisation covers.** INTEG-03 says names are normalised "once at
  load", and there are four paths: the MLoS frame, the Takeoffpoint frame from the same
  upload, the separately uploaded Takeoffpoint file (`load_takeoffpoint_file`, `app.py:520`),
  and the two bundled boundary reference CSVs (`load_boundary_refs`, `app.py:290`). The MLoS
  and both Takeoffpoint paths clearly need it. The bundled reference CSVs are repo-controlled
  files whose headers are already canonical, so normalising them is defensive rather than
  required. Planner's call — but it must be the **same single helper** wherever applied, or
  INTEG-03's "normalised once" is not actually true.
- **`Failing Rows` / `Total Rows` for `S3`, `B4` and `B5`.** These are run-level conditions,
  not row-level ones. `S1` and `S2` already set the precedent for a non-row denominator
  (columns present out of columns required), so the planner should follow whatever reads
  honestly rather than forcing a row count.
- **Where the absence predicate lives.** `qc/predicates.py` already holds `vec_is_uuid`,
  `vec_is_editor` and `pct`, and is the natural home for a vectorised `vec_is_absent`; the
  sentinel constant itself belongs in `qc/domain.py` with the other domain vocabularies.
  Names are the planner's choice.
- **Golden fixture construction (ENGINE-06).** Not discussed — the requirement text largely
  settles it ("a golden fixture asserting that the same data exported as `.sqlite`, `.csv`
  and `.xlsx` produces identical check summaries"). Two implementation choices are open:
  whether the test writes real files to disk and loads them back through the actual
  `load_sqlite` / `load_csv` / `load_xlsx` functions, and how "identical" is compared.
  **Strong recommendation:** round-trip through the real loaders — a fixture that synthesises
  frames directly cannot catch INTEG-01, since the whole defect lives in what each loader
  produces for an empty cell. Note the baseline in `tests/baseline/qc_baseline.json` and
  `tests/test_baseline_records_the_duplicate_ids.py` describes the pre-fix state and will
  need updating as this phase changes findings; `tests/test_extraction_parity.py` compares
  against it.
- **`_NOT_NULL_COLS` membership is not up for revision.** `takeoffpoint` and
  `takeoffpoint_code` are absent from Rule 1's list (`qc/mlos.py:80-88`) because the
  PostgreSQL schema defines that set. Adding them would change Rule 1's meaning and is out
  of scope; the `.missing` findings cover those columns instead.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 2 section: goal, the five numbered success criteria, the
  `Depends on: Phase 1` note, and the Notes paragraph carrying the `keep_default_na=False`
  rationale and the explicit research flag on pandas 3.0.5
- `.planning/REQUIREMENTS.md` — INTEG-01 to INTEG-04, ENGINE-03, ENGINE-04, ENGINE-06 (the
  seven this phase closes), plus the F-number defect mapping and the "Audited defect
  coverage" note
- `.planning/PROJECT.md` — Core Value, the Compatibility constraint ("a verdict must not
  depend on upload format — three audited defects currently violate this"), and the free-tier
  memory constraint bearing on D-14
- `.planning/STATE.md` — accumulated decisions and per-phase blockers
- `.planning/phases/01-qc-engine-seam-and-pinned-environment/01-CONTEXT.md` — **required
  reading.** D-08 parks loader extraction in this phase; D-09 expects this phase to edit
  `qc/autocorrect.py`; D-01/D-02/D-04 set the identifier convention the `.missing` names
  follow; D-12 sets the standing-test-as-structural-backstop precedent

### Canonical schema
- `README.md` §"Required MLoS Columns (43)" and §"Required Takeoffpoint Columns (4)" — the
  authoritative column vocabulary per D-20. Verified to match `qc/domain.py` exactly at the
  time of this discussion
- `README.md` §"Rule 1" — the 28 `NOT NULL` columns, matching `_NOT_NULL_COLS`
- `README.md` §"State filtering" — documents the existing fallback behaviour INTEG-04 changes,
  and will need updating

### Technical grounding
- `.planning/research/STACK.md` — the `pandas==3.0.5` pin and the 3.0 breaking changes that
  bear directly on this phase: default `str` dtype, stricter `setitem` typing, Copy-on-Write
  by default. Copy-on-Write matters for D-14's two-frame model and for `df.loc[mask, col] = ...`
  in `qc/autocorrect.py`
- `.planning/research/ARCHITECTURE.md` — the rule registry pattern and the
  no-`import streamlit`-in-`qc/` rule, which constrains where the normalisation helper and the
  snapshot cache can live
- `.planning/codebase/CONVENTIONS.md` — UPPERCASE module-level constants, lowercase snake_case
  files

### Subject code
- `qc/mlos.py` — Rule 1's `isnull()` at `:92` (INTEG-01); R2/R3/R4 valid-set construction at
  `:113-131` (INTEG-02); `_NOT_NULL_COLS` at `:80-88`; the `add()` closure at `:66`; Rule 14
  at `:220`
- `qc/takeoff.py` — TP2/TP3/TP4 valid-set construction at `:46-61` (INTEG-02)
- `qc/schema.py` — the normalised-vs-raw divergence at `:25` and `:44` (INTEG-03); `S1`/`S2`
  as the precedent for a non-row denominator
- `qc/boundary.py` — the fallback at `:89-91` (INTEG-04); B0's early-return at `:42-50`;
  B1 at `:100-108`; B3's ward-to-state map at `:113-135`; B2's `filtered_bbox` dependence and
  its `in_reference` exclusion at `:137-165`
- `qc/autocorrect.py` — `uuid4()` at `:98` (ENGINE-04); the module docstring already names
  both defects as Phase 2 work
- `qc/domain.py` — `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`, `YN_NA_COLS`, `FLAG_COLS`,
  `VALID_YN_NA`; home for the new sentinel constant
- `qc/predicates.py` — `vec_is_uuid`, `vec_is_editor`, `pct`; natural home for `vec_is_absent`
- `qc/results.py` — `register` / `canonical_order`; every new identifier (`2.missing` …
  `TP4.missing`, `S3`, `B4`, `B5`) registers here
- `qc/__init__.py` — the façade, and at `:10` Phase 1's explicit reasoning for **not** adding
  `run_all()`. D-15 keeps that decision
- `app.py` — loaders at `:95-146`; `get_uploaded_data` and its session-state writes at
  `:148-195`; `load_boundary_refs` at `:290-299`; `load_takeoffpoint_file` at `:520`; the
  submission key at `:693`; the QC cache branch at `:722-820`; the first auto-correct call at
  `:742`; the raw-sheet write at `:512`; the second auto-correct call and the corrected
  download at `:982-1006`; sidebar rules-reference tables that must gain the new identifiers

### Test scaffolding (from Phase 1)
- `tests/fixtures.py` — `build_mlos_fixture`, `build_takeoff_fixture`,
  `load_boundary_fixtures`; the builders both pytest and the baseline capture script import
- `tests/conftest.py` — the thin pytest wrappers and their scoping rationale
- `tests/baseline/qc_baseline.json` + `tests/baseline/capture_baseline.py` — the frozen
  pre-fix baseline. **This phase changes findings, so the baseline and
  `tests/test_baseline_records_the_duplicate_ids.py` need deliberate updating, not silent
  drift**
- `tests/test_extraction_parity.py` — compares live output against that baseline
- `tests/test_results_registry.py`, `tests/test_rule_identifiers.py`,
  `tests/test_registry_covers_emitted_ids.py`, `tests/test_deterministic_order.py` — the
  identifier and ordering guards every new identifier must satisfy
- `tests/test_rules_reference_matches_registry.py` — asserts the sidebar reference agrees with
  the registry, so it will fail until the new identifiers are documented there
- `tests/test_no_streamlit_in_qc.py` — the import-boundary guard, and the AST-assertion
  pattern D-15 reuses

**No external ADRs or specs exist** for this project — no `/gsd-spec-phase` run, no ingested
ADRs. `README.md` is the only non-`.planning/` document with canonical authority, per D-20.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`qc/predicates.py` already establishes the vectorised-predicate pattern** —
  `vec_is_uuid` and `vec_is_editor` both take a Series and return a boolean Series using
  `str.match` rather than per-row `apply`. The absence predicate (D-04) drops straight into
  that shape, and every rule already consumes predicates this way.
- **`qc/results.py`'s `register()` + `canonical_order()`** is exactly the mechanism the ten
  new identifiers need. Phase 1 built it so identity is enforced at import time — adding
  `2.missing`, `S3`, `B4`, `B5` needs no new machinery, just registration in the right layer
  order.
- **`tests/fixtures.py` builders are import-safe without pytest**, deliberately, so the
  three-format golden fixture can write `.sqlite` / `.csv` / `.xlsx` from the same builder
  the unit tests use.
- **`add()` closures already carry a `extra` column list**, so the `.missing` findings can
  surface the offending column in their detail rows with no new plumbing.
- **`S1`/`S2` already report a non-row denominator** (columns present out of required), which
  is the precedent for `S3`, `B4` and `B5`.

### Established Patterns
- Every rule is guarded on column presence (`if col in mlos.columns`) so a partial file
  degrades rather than crashes. INTEG-03 changes *which* names those guards see; it must not
  remove the guards.
- Regex and set membership are vectorised throughout. Keep them that way — the absence
  predicate must be a Series operation, not `apply`.
- `keep_default_na=False` on every loader is load-bearing and correct. INTEG-01 and INTEG-02
  are consequences to handle, not reasons to reverse it.
- Standing tests as structural backstops, asserted cheaply — Phase 1's D-12, and the
  AST-over-`app.py` idiom in its verify commands.
- `st.session_state` caching is keyed and read/written in two separate places
  (`get_uploaded_data`, and the QC block at `:722`). Both keys become the sha256 under D-13.

### Integration Points
- `qc/` must stay Streamlit-free (ENGINE-05, enforced by test). The normalisation helper and
  the absence predicate belong under `qc/`; the snapshot **cache** is `st.session_state` and
  therefore stays in `app.py`. Phase 1's D-08 parked loader extraction here, so splitting
  pure parsing from the caching wrapper is this phase's work.
- The rule identifier is the join key between `checks` and `detail`. Three consumers read it
  and all must accept the ten new identifiers: `make_longitudinal_df` at `app.py:217`, the
  per-rule drilldown expanders, and per-rule Excel sheet naming (`f"Rule {rn}"[:31]`).
- The sidebar rules-reference tables document identifiers as static markdown, and
  `tests/test_rules_reference_matches_registry.py` asserts they agree with the registry — so
  that test fails until they are updated.
- `.planning/codebase/TESTING.md` is **stale**: it states the project has "no automated tests,
  no test framework, and no test infrastructure", which Phase 1 made false. Twelve test files,
  fixture builders and a frozen baseline now exist. Do not plan from that document.

</code_context>

<specifics>
## Specific Ideas

- **`README.md` is the source of truth for column names**, stated directly by the user:
  "change all the column name to match the preloaded column in the readme.md". Incoming
  headers resolve toward README's documented 43 + 4 names rather than toward an ad-hoc list.
- Vocabulary should be consistent across the rule set — `missing` was chosen over `blank`
  specifically because Rule 1 and B0 already say "Not Null" and "Not Available".
- The as-submitted version of the file should be recoverable from the report itself (D-14),
  not only from the officer's own disk.
- Where a new check would have to state something untrue, it should emit nothing instead
  (D-19). The user consistently preferred silence over a false PASS.

</specifics>

<deferred>
## Deferred Ideas

- **Nearest non-matching candidate on cross-table mismatch detail rows** — suggesting the
  closest unmatched `takeoffpoint` value to help an officer reconcile. A fuzzy-matching
  reconciliation aid, not a detection-correctness fix, and it would need its own accuracy
  discussion. Its own phase.
- **Known-alias column map** (`wardcd` → `ward_code`, `lat` → `latitude`, `guid` →
  `eha_guid`). Rejected for this phase because it infers intent from a name, and a wrong
  guess routes real data into the wrong rule — directly against Core Value. Revisit only with
  evidence of which aliases officers actually submit.
- **Content-derived `eha_guid` (UUIDv5 over row identity)** — would make IDs stable across
  sessions, machines and re-uploads, and reproducible by anyone. Not chosen (D-12). Worth
  revisiting alongside v2's HIST-01, which wants to flag `eha_guid` churn and would benefit
  from churn meaning "the data changed" rather than "the session ended". A cheap middle
  option also exists: seeding the generator from D-13's content hash, which keeps the uuid4
  shape while making it reproducible.
- **Telling the officer that generated `eha_guid` values are session-scoped** — a consequence
  of D-12 worth surfacing in the auto-correct panel, since an officer who files a report
  citing those IDs cannot regenerate them. Raised and not taken up.
- **B2's unmatched-bounding-box silent pass** — `in_reference = merged["min_lon"].notna()`
  (`qc/boundary.py:155`) excludes rows whose ward has no bbox, so a settlement with an
  unmatched ward code passes B2 silently. Same defect family, but the fix belongs with
  Phase 7's GEO-01 (point-in-polygon replacing the bounding-box approximation) and GEO-03
  (recording which boundary dataset produced a finding).
- **Missing-boundary-reference scoring.** D-18's `B5` makes an unavailable reference
  *visible*; making it *not score as a pass* is Phase 3's VERDICT-05 ("no credit for a layer
  that ran zero checks", displayed as n/a).
- **`qc.run_all()` façade.** Offered as D-15's alternative and declined, consistent with
  Phase 1's documented reasoning in `qc/__init__.py:10`. If a later phase needs one-frame-in
  orchestration, the progress-reporting callback design sketched during this discussion is
  the starting point.

</deferred>

---

*Phase: 2-Detection Correctness and Three-Format Harness*
*Context gathered: 2026-09-10*
