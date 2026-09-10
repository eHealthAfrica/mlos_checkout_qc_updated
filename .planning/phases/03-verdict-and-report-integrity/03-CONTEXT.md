# Phase 3: Verdict and Report Integrity - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the verdict, the weighted score, the downloadable Excel report and the
emailed summary describe every layer that ran, so a failing file can never be reported as
clean and a withheld table can never raise a score.

Concretely: the report gains coverage of all five layers with its cover verdict derived from
all of them; a layer that ran zero checks earns no score credit and is shown as not run; issue
row totals count distinct rows rather than rule-row pairs, consistently on screen, in the
report and in the email; the email reports the Settlement layer; boundary order is proven
B0, B1, B2, B3 (B4, B5 after Phase 2) in every table and export; and raw-data sheets are
written without per-cell styling.

It delivers **no new checks and no changed detection**. Rule logic, identifiers, the absence
predicate, column normalisation and the snapshot cache are Phase 1 and Phase 2 work and are
not touched here except where a detail frame's row identity must be preserved for counting
(D-11). Advisory severity is Phase 6 (ADVIS-01), so every check still reads PASS or FAIL and
"not run" is a property of a layer, never a status of a check. Email recipients stay
hard-coded until M2 (DEPLOY-03).

Requirements closed: VERDICT-01, VERDICT-02, VERDICT-03, VERDICT-04, VERDICT-05, VERDICT-06,
ENGINE-08. Defects closed: F1, F6, F8, F11, F12, F14.

</domain>

<decisions>
## Implementation Decisions

### Score When a Layer Did Not Run (VERDICT-05)

- **D-01:** A layer that ran zero checks earns **no credit**: its weighted contribution is 0
  and the overall score is the plain sum of the layers that ran, so a perfect four-layer file
  scores 80.0%. The total is **displayed against the achievable maximum** — `72.0% of 80.0%
  achievable` — wherever the weighted score appears (top metric bar, Tab 2 score panel,
  report cover, email). Today `_layer_pass_rate` at `app.py:821-825` returns `1.0` for an
  empty checks list, which is F6.

  *Recorded deviation:* a bare capped total (`72.0%`, out of 100) was recommended and **not**
  chosen. The user wants the dropped ceiling visible next to the number. Renormalising the
  weights over the layers that ran was offered, flagged as reopening F6, and not chosen.

- **D-02:** In the Tab 2 score breakdown table, the row for a layer that did not run shows
  **Layer Pass Rate `n/a` and Weighted Contribution `0`** (a number, not `n/a`), with the
  weight column unchanged at its normal percentage. The Total row carries the achievable
  maximum.

  *Recorded deviation:* `n/a` in both cells was recommended; the user chose a literal 0 for
  the contribution so the column still sums visibly to the total.

- **D-03:** The score **colour bands stay absolute** (green at 80 and above, amber at 60 and
  above, red below), driven by the capped score out of 100, not by the score relative to
  the achievable maximum. `72.0% of 80.0% achievable` is amber. A missing layer costs colour
  as well as points, and a colour means the same thing on every file.

- **D-04:** When every check that ran passed but a layer did not run, the verdict is still
  **CLEAN, with the gap named** in the same sentence: `CLEAN — Takeoffpoint layer not checked
  (no Takeoffpoint data supplied)`. This wording is used identically by the on-screen banner
  (`app.py:848-858`), the Generate Report tab verdict (`app.py:1223-1231`), the report cover
  (`app.py:387-392`) and the email verdict line (`app.py:267`). The verdict stays two-state
  (CLEAN / FAILING); an `INCOMPLETE` third state was offered and not chosen. —
  **Reversibility:** costly — the sentence is printed in emailed and filed reports, so a later
  wording change leaves two vocabularies in circulation.

- **D-05:** "Did not run" means **the layer's checks list is empty**. Today only Takeoffpoint
  can be empty (the `takeoff_df.empty` branch at `app.py:764-767`). After Phase 2, Boundary
  always emits at least B0 and B5 and Schema always emits S1 and S3, so neither can be n/a;
  S2 being skipped inside Schema is a partial layer, not an unrun one. The implementation
  must nonetheless be generic across all five layers so a future layer cannot reintroduce F6.

### Report Workbook Shape (VERDICT-01, VERDICT-02, ENGINE-08)

- **D-06:** The workbook becomes **one combined `QC Summary` sheet plus one detail sheet per
  layer**: Cover · QC Summary · Schema Issue Detail · MLoS Issue Detail · Settlement Issue
  Detail · Takeoffpoint Issue Detail · Boundary Issue Detail · Raw MLoS Data · Raw
  Takeoffpoint Data · Columns Renamed (conditional, per Phase 2 D-11). The summary sheet has
  a `Layer` column and lists every check in registry canonical order (`qc.sort_by_registry`),
  which is also what makes VERDICT-06 hold in the export. Detail frames keep their own
  layer's identifying columns and are **not** merged across layers — Takeoffpoint keys on its
  own table and Schema keys on columns, so a union would be mostly blanks. —
  **Reversibility:** costly — the existing `MLoS QC Summary` and `Takeoffpoint QC Summary`
  sheet names disappear, so anything the data team has built against those sheet names
  breaks once and would break again on a second rename.

  *Recorded deviation:* one summary-plus-detail pair per layer (14 sheets, existing sheet
  names preserved) was recommended and **not** chosen.

- **D-07:** On the combined summary sheet, a layer that ran zero checks appears as **one
  placeholder row in its canonical position**, reading e.g. `Takeoffpoint — not run: no
  Takeoffpoint data supplied`, with `n/a` in Failing Rows, Total Rows and Fail %. The sheet
  alone must never look like a four-layer tool.

- **D-08:** The **cover carries the verdict and the weighted score only** (plus the existing
  file metadata: filename, generated-at, MLoS rows, Takeoffpoint rows). The verdict is the
  D-04 sentence, derived from all five layers — today's `total_fail` at `app.py:355-356` sums
  MLoS and Takeoffpoint checks only, which is F1. Per-layer counts live on the summary sheet,
  not the cover.

  *Recorded deviation:* a per-layer table on the cover (checks run, failing, distinct issue
  rows, pass rate) was recommended and **not** chosen.

- **D-09:** Per-cell styling is removed from **both the raw-data sheets and the five detail
  sheets**: rows are written as plain values with a styled header row and column widths
  only. No per-cell `Font`, `Border`, `Alignment` or zebra `PatternFill`. This goes beyond
  ENGINE-08's letter (raw sheets) deliberately: detail sheets grow with failures exactly as
  raw sheets grow with rows, and the free-tier memory constraint in PROJECT.md applies to
  both. The summary sheet and cover keep their styling; they are bounded in size. The
  `write_detail` and `write_raw` helpers at `app.py:413-449` are the sites.

### What One Issue Row Means (VERDICT-04)

- **D-10:** The headline **Issue Rows** figure (top metric `c5` at `app.py:842`, the failing
  banner at `app.py:852-857`, the Generate Report tab at `app.py:1229`, the email) is the
  **sum of the per-layer distinct row counts**. Each layer counts each source row once no
  matter how many of its rules fired on it; the four layer counts are then added. A
  settlement with findings in both MLoS and Boundary counts twice in the headline and once
  in each layer. Today every one of these sites uses `len(<layer>_detail)`, which counts
  rule-row pairs — F8.

  *Recorded deviation:* two cross-layer distinct figures (distinct settlements across MLoS,
  Settlement and Boundary, plus distinct takeoffpoints) was recommended and **not** chosen.
  The user prefers a headline that is exactly the sum of the per-layer lines beneath it.

- **D-11:** Within a layer, **one row is identified by its original row position in the
  checked frame** (the index of the corrected MLoS frame, or of the Takeoffpoint frame). Every
  detail frame must therefore carry that position through to the counting site. MLoS
  (`qc/mlos.py:268`) and Settlement (`qc/settlement.py:121`) already preserve it because they
  concatenate without `ignore_index`; Takeoffpoint (`qc/takeoff.py:99`) and Boundary
  (`qc/boundary.py:188`) pass `ignore_index=True` and must stop discarding it. Keying on the
  `id_col` already in the detail rows (`ogc_fid`, else the first column) was offered and
  rejected: a CSV without `ogc_fid` may put a non-unique column first and undercount.

- **D-12:** The old rule-row pair count **stays visible, labelled as findings**, beside the
  distinct count: `312 issue rows across 1,040 findings`. The findings number is what the
  per-rule expanders and detail sheets add up to, so an officer can reconcile the two.

- **D-13:** Each layer's distinct count is shown **with its share of the checked table's
  rows**: `312 issue rows (6.2% of 5,000) across 1,040 findings`. The denominator is the
  layer's source table (MLoS row count for MLoS, Settlement and Boundary; Takeoffpoint row
  count for Takeoffpoint). Schema's "rows" are columns and it reports missing-column counts
  as today; it has no distinct-row line.

### Email Content (VERDICT-03, VERDICT-04)

- **D-14:** The email body is restructured as **one block per layer, then the check list**,
  and stays plain text: the D-04 verdict sentence; the D-01 weighted score with achievable
  maximum; five layer blocks in canonical layer order, each with checks run, checks failing,
  and the D-13 line (or `not run: no Takeoffpoint data supplied` for a skipped layer); then
  the check-by-check list grouped under layer headings. The existing missing-columns block
  for Schema stays. Today's body (`app.py:274-292`) has no Settlement line at all — F11.
- **D-15:** The check-by-check list includes **every check that ran**, passing and failing, in
  canonical order. A CLEAN email still shows exactly what was checked.
- **D-16:** The **subject line carries the verdict**: `MLoS QC: FAILING (12 checks) —
  kano_checkout.xlsx` or `MLoS QC: CLEAN — kano_checkout.xlsx`. Today it is the static
  `MLoS QC checks for {filename}` at `app.py:297`.
- Columns Renamed is **not** added to the email. Phase 2 D-11 fixed its two reporting places
  (on-screen expander and the report sheet) and that decision stands.

### Claude's Discretion

- **Where the verdict, score, counting, report and email-body code lives.** VERDICT-01 and
  VERDICT-02 need a test that builds the workbook and asserts its sheets and cover verdict,
  and VERDICT-04 needs a test over the distinct counts, so this logic must be importable
  **without Streamlit**. Today all of it sits in `app.py` module scope or in functions that
  read `st.secrets` (`send_qc_email`, `app.py:252`). Phase 1 D-06 kept
  `build_schema_report_xlsx` in `app.py` because it is a report builder, not a QC engine —
  that reasoning was about the scope of the `qc/` extraction, not a ban on a Streamlit-free
  report module. The planner chooses the module and its name (`qc/report.py`, a top-level
  `report.py`, or similar); the firm requirement is that `tests/test_no_streamlit_in_qc.py`'s
  boundary still holds and the builders are unit-testable. `send_qc_email` should split into a
  pure body-and-subject builder and a thin sender that reads secrets.
- **One derivation, four presentations.** F1 exists because the cover computed its own
  verdict. The banner, cover, Generate Report tab and email must all read one shared
  computation of verdict text, weighted score, achievable maximum, per-layer distinct counts
  and findings counts. How that is packaged (a dataclass, a dict, a small module) is the
  planner's call; a standing test asserting the four sites agree is strongly recommended,
  following the AST-over-`app.py` idiom Phase 1 and Phase 2 established.
- **VERDICT-06 is mostly a proof, not a rebuild.** Every call site already pipes its checks
  through `qc.sort_by_registry` (`app.py:733`, `:743`, `:753`, `:769`, `:781`), so B0, B1, B2,
  B3 (B4, B5) already come out in order on screen, in the combined summary and in the
  Boundary tab's per-rule export, which iterates the sorted list. The phase should deliver a
  standing test that asserts order on every summary table and export path, and fix any site
  that is found not to be sorted, rather than re-sorting inside the boundary layer (Phase 1
  deliberately left the raw emission order alone).
- **Generate Report tab layout.** The three-column breakdown at `app.py:1275-1297` shows MLoS,
  Settlement and Takeoffpoint only. Whether it becomes five columns, one combined table
  mirroring the summary sheet, or is replaced by the layer blocks from D-14 is the planner's
  call; it must show all five layers and use the D-13 counts.
- **Whether `of 80.0% achievable` appears in the top metric bar or only in Tab 2 and the
  cover.** `st.metric` has limited room; a delta or caption is acceptable.
- **Placeholder-row denominators and the `Fail %` column** for a not-run layer on the summary
  sheet: `n/a` throughout, per D-07; exact cell values are the planner's choice.
- **README §8 "Weighted QC Score"** (`README.md:247-275`) documents full credit for a skipped
  layer at `:269` and must be rewritten to match D-01 to D-05. §10 and §11 should reflect the
  new sheet list and email shape. This is required, not optional.
- **The longitudinal export** (`make_longitudinal_df`, `app.py:167`) is already one row per
  settlement and is unaffected by D-10 to D-13; leave it alone unless a test shows otherwise.
- **Baseline and parity tests.** Preserving the row index in Takeoffpoint and Boundary detail
  frames (D-11) changes frame shape, not findings, but `tests/test_extraction_parity.py` and
  the golden three-format fixture compare detail frames; the planner should check how they
  compare indices and adjust deliberately, not silently.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 3 section: goal, five success criteria, `Depends on: Phase 2`,
  and the Notes paragraph explaining that F10 is closed by ENGINE-09 in Phase 1, not here
- `.planning/REQUIREMENTS.md` — VERDICT-01 to VERDICT-06 and ENGINE-08 (the seven this phase
  closes), the F-number mapping, and the note that F1 is the one defect with two closing
  requirements
- `.planning/PROJECT.md` — Core Value ("a file this tool calls clean is clean"), the free-tier
  memory constraint bearing on D-09, and the Compatibility constraint
- `.planning/STATE.md` — accumulated decisions and per-phase blockers
- `.planning/phases/01-qc-engine-seam-and-pinned-environment/01-CONTEXT.md` — **required
  reading.** D-04 freezes identifiers; D-06 scopes what went into `qc/` and why
  `build_schema_report_xlsx` stayed behind; the Claude's Discretion note on registry sort
  semantics is what already satisfies VERDICT-06
- `.planning/phases/02-detection-correctness-and-three-format-harness/02-CONTEXT.md` —
  **required reading.** D-03 (layers report overlap independently; VERDICT-04 fixes the
  double count), D-11 (Columns Renamed sheet: two places, no score weight), D-12 to D-15
  (the `mlos_raw` / `mlos_corrected` two-frame model and the report's as-submitted sheet,
  which ENGINE-08 restyles), D-16 to D-19 (B4 and B5, canonical order B0 to B5)
- `.planning/phases/02-detection-correctness-and-three-format-harness/02-05-PLAN.md` and
  `02-06-PLAN.md` — frontmatter only: these two plans are not yet executed and will change
  `qc/boundary.py` and the `app.py` cache branch before Phase 3 starts. Phase 3 plans against
  their `must_haves`, not against today's `app.py` line numbers

### Domain documentation
- `README.md` §8 "Weighted QC Score" (`:247-275`) — documents the current formula and, at
  `:269`, the full-credit rule this phase removes; must be rewritten
- `README.md` §10 "Generate & Download Report" (`:293-301`) and §11 "Send QC Email"
  (`:305-325`) — describe the sheet list and email; must be updated to D-06 and D-14

### Subject code
- `app.py` — `send_qc_email` at `:252-308` (hard-coded recipients `:261-264` stay until M2;
  verdict line `:267`; body `:274-292`; subject `:297`); `build_excel_report` at `:328-490`
  (`total_fail` from two layers `:355-356`; cover verdict `:387-392`; `write_summary` `:396`;
  `write_detail` `:413`; `write_raw` `:440`; sheet creation `:451-456`; Columns Renamed
  `:458-480`); the Takeoffpoint skip branch `:764-767`; `all_checks` and `n_fail` `:797-799`;
  `len(<layer>_detail)` row counts `:802-805`; `LAYER_WEIGHTS` `:811-819`; `_layer_pass_rate`
  `:821-825`; metrics bar `:836-843`; verdict banner `:848-858`; Tab 2 score panel and
  `score_rows` `:872-896`; Tab 8 verdict, metadata card and three-column breakdown
  `:1218-1297`; download caption listing sheets `:1302-1305`; email button `:1325-1333`
- `qc/__init__.py` — `sort_by_registry`, the canonical re-sort every call site uses
- `qc/results.py` — `canonical_order()`, the source of layer and rule order for the combined
  summary sheet and the VERDICT-06 test
- `qc/mlos.py` — `BASE` and `add()` at `:65-79`; `pd.concat(details)` without `ignore_index`
  at `:268` (index preserved)
- `qc/settlement.py` — same shape; concat at `:121` (index preserved)
- `qc/takeoff.py` — `BASE` at `:33`; `pd.concat(details, ignore_index=True)` at `:99` (index
  discarded — D-11 site)
- `qc/boundary.py` — `BASE` at `:51`; `pd.concat(details, ignore_index=True)` at `:188` (index
  discarded — D-11 site); registrations B0 to B3 at `:25-34`, B4 and B5 arrive with plan 02-05
- `qc/schema.py` — S1, S2, S3 and their column-count denominators, the precedent D-13 follows
  for Schema having no distinct-row line

### Test scaffolding
- `tests/test_no_streamlit_in_qc.py` — the import-boundary guard any new report module must
  satisfy, and the AST-over-`app.py` idiom for structural standing tests
- `tests/test_deterministic_order.py`, `tests/test_registry_covers_emitted_ids.py` — the
  ordering and coverage guards the VERDICT-06 test extends
- `tests/fixtures.py`, `tests/golden_fixture.py` — the builders a report-building test should
  reuse (a fixture with a failing Boundary check and an empty Takeoffpoint table exercises
  D-01, D-04, D-07 and F1 together)
- `tests/test_extraction_parity.py`, `tests/baseline/qc_baseline.json` — compare detail frames;
  see the Claude's Discretion note on D-11's index change

**No external ADRs or specs exist** for this project — no `/gsd-spec-phase` run, no ingested
ADRs. `README.md` is the only non-`.planning/` document with canonical authority (Phase 2
D-20), and here it is a consumer of this phase's decisions rather than a source.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Three of the four verdict sites are already right.** The banner (`app.py:848`), the email
  (`app.py:265-267`) and the Generate Report tab (`app.py:1223`) all derive from `all_checks`
  across five layers. Only the report cover diverges. F1 is one wrong derivation, and the
  fix is to make all four read one shared computation rather than to patch the cover.
- **`qc.sort_by_registry` and `canonical_order()`** already give the layer-then-declaration
  order the combined summary sheet needs; the `Layer` column is `Rule.layer` from the
  registry, so no new ordering machinery is required.
- **Detail frames already carry identifying columns** (`BASE` in each layer) and, in MLoS and
  Settlement, the original index. Distinct counting needs the index preserved in the other
  two layers, not a new key.
- **`write_summary` / `write_detail` / `write_raw`** in `build_excel_report` are already
  helpers taking a worksheet and a frame; D-06 and D-09 are changes to what they write, not
  new builders.
- **Phase 1 and Phase 2's standing-test idiom** — AST parse of `app.py`, exact-set equality
  against the registry — is the right shape for "four sites agree" and "every export is in
  canonical order".

### Established Patterns
- Every layer's `add()` emits PASS or FAIL through the same closure; there is no third status,
  and Phase 6 owns adding one. "Not run" therefore lives at the layer level (empty checks
  list), never as a check row status.
- `keep_default_na=False`, the two-frame snapshot (Phase 2 D-14) and the sha256 submission key
  (Phase 2 D-13) are load-bearing and untouched here. The report's as-submitted sheet reads
  `mlos_raw`; every other consumer reads `mlos_corrected`.
- Column widths and a styled header row are the accepted amount of styling for a bulk sheet
  (`build_corrected_excel` at `app.py:310-325` already does exactly this); D-09 brings the raw
  and detail sheets to the same convention.
- Module-level constants UPPERCASE; files lowercase snake_case; no linter or formatter.

### Integration Points
- `app.py` stays presentation and orchestration: load → `qc.*` → **one shared
  verdict/score/count computation** → render → export → email. The new computation slots in
  between the five call sites and the metrics bar (`app.py:797-832` today).
- The session-state cache branch (`app.py:706-795`, being reshaped by plan 02-06) is where
  the per-layer checks and details are read back; the shared computation must run on both
  the cache-hit and cache-miss paths or the rerun shows stale numbers — the same class of bug
  as F4.
- `build_excel_report`'s signature currently takes only MLoS and Takeoffpoint checks and
  details plus the two frames; it must receive all five layers (or the shared computation
  object). Its single call site is `app.py:1308-1311`.
- `send_qc_email`'s signature (`app.py:252-254`) likewise takes three layer row counts and
  `schema_detail`; it must receive the shared computation. Its single call site is
  `app.py:1327-1328`.
- The four per-layer issue tabs (Tabs 3 to 6) display `len(subset)` per rule, which is
  already distinct within a rule and unchanged; only their header lines (`{layer}_fail_rows`
  at `app.py:1017`, `:1055`, `:1089`, `:1122`) switch to the D-13 wording.

</code_context>

<specifics>
## Specific Ideas

Exact strings the user approved, to be used verbatim or as the template for all four sites:

- Score: `72.0% of 80.0% achievable`
- Verdict with a skipped layer: `CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data
  supplied)`
- Summary-sheet placeholder row: `Takeoffpoint — not run: no Takeoffpoint data supplied`
- Per-layer issue line: `312 issue rows (6.2% of 5,000) across 1,040 findings`
- Email subject: `MLoS QC: FAILING (12 checks) — kano_checkout.xlsx` /
  `MLoS QC: CLEAN — kano_checkout.xlsx`

The user consistently chose the option that keeps arithmetic reconcilable by eye: the
headline is the sum of the per-layer lines (D-10), the score table sums visibly (D-02), and
the findings count sits next to the distinct count (D-12). Downstream agents should preserve
that property when choosing exact layouts.

</specifics>

<deferred>
## Deferred Ideas

- **Email recipients into Space secrets** — the `TO` / `CC` lists at `app.py:261-264` are
  hard-coded. Moving them is DEPLOY-03 in Phase 4 (M2) and is not touched here.
- **Attaching the Excel report to the email** — a new capability, raised while discussing
  the email body. Not in any requirement; worth a backlog note for M2, when the email will
  be reworked for secrets anyway.
- **Layer weights and colour-band thresholds in configuration** — the 10/40/20/20/10 weights
  and the 80/60 bands are literals in `app.py`. Phase 6's CONFIG requirements cover
  threshold configuration; the weights could join them then.
- **HTML email** — plain text stays for M1. If the per-layer blocks prove hard to read in
  plain text, an HTML alternative is an M2 presentation question.
- **Uniform identifier scheme** — already deferred at Phase 1 D-05; the combined summary
  sheet's `Layer` column makes the mixed scheme easier to read but does not resolve it.

</deferred>

---

*Phase: 3-Verdict and Report Integrity*
*Context gathered: 2026-09-10*
